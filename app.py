"""
Meeting Transcriber - Lean FastAPI Application

A simple web app for transcribing meetings using Whisper.
No Docker containers for inference - direct Python calls.
"""
import asyncio
import json
import uuid
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pydantic import BaseModel

import config
from config import is_hf_token_configured, reload_env, ENV_FILE, get_gpu_info, GPU_BACKEND, TASK_META_SUFFIX, RESULTS_DIR
from transcriber import transcribe, format_output, save_result, get_audio_duration, get_active_backend
from logging_config import get_logger, configure_uvicorn_logging

# Loggers for app module
logger = get_logger("app")
ws_logger = get_logger("websocket")

# App setup
app = FastAPI(title="Meeting Transcriber", version="2.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# In-memory task storage
tasks: dict = {}
websocket_connections: dict = {}

logger.info("Meeting Transcriber starting up")
logger.info(f"Upload directory: {config.UPLOAD_DIR}")
logger.info(f"Results directory: {config.RESULTS_DIR}")
logger.info(f"GPU Backend: {GPU_BACKEND} ({get_gpu_info()['name']})")


def load_persisted_tasks():
    """Load task metadata from result files on startup."""
    loaded = 0
    for meta_file in RESULTS_DIR.glob(f"*{TASK_META_SUFFIX}"):
        try:
            # Check if corresponding result file exists
            result_filename = meta_file.name.replace(TASK_META_SUFFIX, "")
            result_path = RESULTS_DIR / result_filename
            if not result_path.exists():
                logger.warning(f"Orphaned meta file (result missing): {meta_file.name}")
                continue

            with open(meta_file, "r", encoding="utf-8") as f:
                task = json.load(f)

            task_id = task.get("task_id")
            if not task_id:
                logger.warning(f"Meta file missing task_id: {meta_file.name}")
                continue

            # Handle duplicate task_ids by preferring newer files
            if task_id in tasks:
                existing_completed = tasks[task_id].get("completed_at", "")
                new_completed = task.get("completed_at", "")
                if new_completed <= existing_completed:
                    continue

            tasks[task_id] = task
            loaded += 1
        except Exception as e:
            logger.warning(f"Failed to load meta file {meta_file.name}: {e}")

    if loaded > 0:
        logger.info(f"Loaded {loaded} persisted task(s) from results directory")


# Load persisted tasks on module load
load_persisted_tasks()


class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: int
    message: str
    filename: Optional[str] = None
    result_path: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    # Metrics
    duration_seconds: Optional[float] = None
    word_count: Optional[int] = None
    speakers_detected: Optional[int] = None
    model_used: Optional[str] = None
    # Enhanced progress data
    step: Optional[str] = None  # extracting, loading_model, transcribing, diarizing, formatting, complete
    step_name: Optional[str] = None  # Human-readable step name
    substep: Optional[str] = None  # Additional detail about current operation
    audio_duration: Optional[float] = None  # For ETA calculation
    current_time: Optional[float] = None  # Current position in audio (during transcription)
    segments_processed: Optional[int] = None
    segments_total: Optional[int] = None
    file_size_mb: Optional[float] = None


# === ROUTES ===

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main page."""
    logger.debug("Serving home page")
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    """Health check endpoint."""
    logger.debug("Health check request")
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/gpu")
async def gpu_status():
    """Return GPU status and acceleration info."""
    gpu_info = get_gpu_info()
    backend = get_active_backend()
    return {
        "gpu": gpu_info,
        "active_backend": backend,
        "speed_estimate": "~30x realtime" if gpu_info["available"] else "~15x realtime (CPU)",
    }


@app.get("/models")
async def get_models():
    """Return available Whisper models."""
    logger.debug("Models list request")
    return {
        "models": [
            {"id": model_id, **model_info}
            for model_id, model_info in config.AVAILABLE_MODELS.items()
        ],
        "default": config.DEFAULT_MODEL
    }


@app.get("/formats")
async def get_formats():
    """Return available output formats."""
    return {"formats": config.OUTPUT_FORMATS, "default": "txt"}


@app.get("/languages")
async def get_languages():
    """Return available languages for transcription."""
    return {
        "languages": [
            {"code": code, "name": name}
            for code, name in config.SUPPORTED_LANGUAGES.items()
        ],
        "default": config.DEFAULT_LANGUAGE
    }


@app.post("/transcribe")
async def create_transcription(
    file: UploadFile = File(...),
    model: str = Form(default="base"),
    output_format: str = Form(default="txt"),
    language: str = Form(default="auto"),
    diarize: bool = Form(default=False),
    min_speakers: Optional[int] = Form(default=None),
    max_speakers: Optional[int] = Form(default=None),
):
    """Start a transcription task."""
    # Log incoming request
    file_size_bytes = 0
    content = await file.read()
    file_size_bytes = len(content)
    file_size_mb = file_size_bytes / (1024 * 1024)

    logger.info(f"Transcription request: file={file.filename}, size={file_size_mb:.2f}MB")
    logger.info(f"Options: model={model}, format={output_format}, lang={language}, diarize={diarize}")

    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in config.SUPPORTED_EXTENSIONS:
        logger.warning(f"Rejected file with unsupported extension: {ext}")
        raise HTTPException(400, f"Unsupported file type: {ext}")

    # Validate model
    if model not in config.AVAILABLE_MODELS:
        logger.warning(f"Rejected request with unknown model: {model}")
        raise HTTPException(400, f"Unknown model: {model}")

    # Validate format
    if output_format not in config.OUTPUT_FORMATS:
        logger.warning(f"Rejected request with unknown format: {output_format}")
        raise HTTPException(400, f"Unknown format: {output_format}")

    # Validate language
    if language not in config.SUPPORTED_LANGUAGES:
        logger.warning(f"Rejected request with unknown language: {language}")
        raise HTTPException(400, f"Unknown language: {language}")

    # Create task
    task_id = str(uuid.uuid4())[:8]
    upload_path = config.UPLOAD_DIR / f"{task_id}_{file.filename}"

    # Save uploaded file
    upload_path.write_bytes(content)
    logger.info(f"Task created: {task_id}, file saved to {upload_path.name}")

    # Get duration and file size
    duration = get_audio_duration(upload_path)
    logger.debug(f"File duration: {duration:.2f}s")

    # Create task record
    tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "message": "Queued for processing",
        "filename": file.filename,
        "upload_path": str(upload_path),
        "result_path": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "settings": {
            "model": model,
            "output_format": output_format,
            "language": language,
            "diarize": diarize,
            "min_speakers": min_speakers,
            "max_speakers": max_speakers,
        },
        "duration_seconds": duration,
        "audio_duration": duration,
        "file_size_mb": file_size_mb,
        "word_count": None,
        "speakers_detected": None,
        "model_used": model,
        # Enhanced progress fields
        "step": "pending",
        "step_name": "Pending",
        "substep": None,
        "current_time": None,
        "segments_processed": None,
        "segments_total": None,
    }

    # Start processing in background
    asyncio.create_task(process_task(task_id))

    return {"task_id": task_id, "status": "pending"}


async def process_task(task_id: str):
    """Background task processor."""
    task = tasks.get(task_id)
    if not task:
        logger.error(f"Task not found in process_task: {task_id}")
        return

    logger.info(f"Processing task: {task_id}")

    try:
        task["status"] = "processing"
        upload_path = Path(task["upload_path"])
        settings = task["settings"]

        async def progress_callback(progress_data: dict):
            """Handle progress updates from transcriber.

            progress_data is a dict with:
                - progress: int (0-100)
                - message: str
                - step: str (extracting, loading_model, transcribing, diarizing, formatting, complete)
                - step_name: str (human-readable)
                - substep: str (optional detail)
                - audio_duration: float
                - current_time: float (optional, during transcription)
                - segments_processed: int (optional)
                - segments_total: int (optional)
                - word_count: int (optional, at completion)
            """
            task["progress"] = progress_data.get("progress", 0)
            task["message"] = progress_data.get("message", "")
            task["step"] = progress_data.get("step", "processing")
            task["step_name"] = progress_data.get("step_name", "Processing")
            task["substep"] = progress_data.get("substep")
            task["audio_duration"] = progress_data.get("audio_duration")
            task["current_time"] = progress_data.get("current_time")
            task["segments_processed"] = progress_data.get("segments_processed")
            task["segments_total"] = progress_data.get("segments_total")
            await notify_websocket(task_id)

        # Run transcription
        result = await transcribe(
            file_path=upload_path,
            model_name=settings["model"],
            output_format=settings["output_format"],
            language=settings["language"],
            diarize=settings["diarize"],
            min_speakers=settings["min_speakers"],
            max_speakers=settings["max_speakers"],
            progress_callback=progress_callback,
        )

        # Save result
        output_path = save_result(
            result,
            task["filename"],
            settings["output_format"]
        )

        # Update task
        task["status"] = "completed"
        task["progress"] = 100
        task["message"] = "Transcription complete"
        task["step"] = "complete"
        task["step_name"] = "Complete"
        task["result_path"] = str(output_path)
        task["completed_at"] = datetime.now().isoformat()
        task["word_count"] = len(result["text"].split())
        task["speakers_detected"] = result.get("speakers", 0)
        task["segments_total"] = len(result.get("segments", []))

        logger.info(f"Task completed: {task_id}, result saved to {output_path.name}")
        logger.info(f"Task metrics: words={task['word_count']}, speakers={task['speakers_detected']}, segments={task['segments_total']}")

        await notify_websocket(task_id)

        # Persist task metadata for server restart recovery
        try:
            meta_path = output_path.parent / f"{output_path.name}{TASK_META_SUFFIX}"
            task_data = {k: v for k, v in task.items() if k != "upload_path"}
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(task_data, f, indent=2)
            logger.debug(f"Task metadata saved: {meta_path.name}")
        except Exception as meta_err:
            logger.warning(f"Failed to save task metadata: {meta_err}")

    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)
        task["message"] = f"Error: {str(e)}"
        task["step"] = "error"
        task["step_name"] = "Error"

        logger.error(f"Task failed: {task_id} - {str(e)}")
        logger.error(f"Stack trace:\n{traceback.format_exc()}")

        await notify_websocket(task_id)

    finally:
        # Cleanup upload
        upload_path = Path(task.get("upload_path", ""))
        if upload_path.exists():
            try:
                upload_path.unlink()
                logger.debug(f"Cleaned up upload file: {upload_path.name}")
            except Exception as e:
                logger.warning(f"Failed to cleanup upload file: {e}")


async def notify_websocket(task_id: str):
    """Send task update to connected WebSocket."""
    ws = websocket_connections.get(task_id)
    if ws:
        try:
            task = tasks.get(task_id, {})
            await ws.send_json({
                "task_id": task_id,
                "status": task.get("status"),
                "progress": task.get("progress"),
                "message": task.get("message"),
                "result_path": task.get("result_path"),
                "error": task.get("error"),
                # Enhanced progress data
                "step": task.get("step"),
                "step_name": task.get("step_name"),
                "substep": task.get("substep"),
                "audio_duration": task.get("audio_duration"),
                "current_time": task.get("current_time"),
                "segments_processed": task.get("segments_processed"),
                "segments_total": task.get("segments_total"),
                "file_size_mb": task.get("file_size_mb"),
                "filename": task.get("filename"),
                "word_count": task.get("word_count"),
                "speakers_detected": task.get("speakers_detected"),
            })
            ws_logger.debug(f"Sent update to WebSocket: task={task_id}, progress={task.get('progress')}")
        except Exception as e:
            ws_logger.warning(f"Failed to send WebSocket update: {task_id} - {e}")


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket for real-time progress updates."""
    await websocket.accept()
    websocket_connections[task_id] = websocket
    ws_logger.info(f"WebSocket connected: {task_id}")

    try:
        # Send current state
        if task_id in tasks:
            await notify_websocket(task_id)

        # Keep connection alive
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                # Send ping to keep alive
                await websocket.send_json({"ping": True})
    except WebSocketDisconnect:
        ws_logger.info(f"WebSocket disconnected: {task_id}")
    except Exception as e:
        ws_logger.error(f"WebSocket error: {task_id} - {e}")
    finally:
        websocket_connections.pop(task_id, None)
        ws_logger.debug(f"WebSocket cleaned up: {task_id}")


@app.get("/status/{task_id}")
async def get_status(task_id: str):
    """Get task status (fallback for non-WebSocket clients)."""
    task = tasks.get(task_id)
    if not task:
        logger.debug(f"Status request for unknown task: {task_id}")
        raise HTTPException(404, "Task not found")
    return task


@app.get("/result/{task_id}")
async def get_result(task_id: str):
    """Download transcription result."""
    task = tasks.get(task_id)
    if not task:
        logger.debug(f"Result request for unknown task: {task_id}")
        raise HTTPException(404, "Task not found")

    if task["status"] != "completed":
        logger.debug(f"Result request for incomplete task: {task_id}")
        raise HTTPException(400, "Task not completed")

    result_path = Path(task["result_path"])
    if not result_path.exists():
        logger.error(f"Result file not found: {result_path}")
        raise HTTPException(404, "Result file not found")

    logger.info(f"Serving result file: {result_path.name}")
    return FileResponse(
        result_path,
        filename=result_path.name,
        media_type="application/octet-stream"
    )


@app.get("/tasks")
async def list_tasks():
    """List all tasks (for task history)."""
    logger.debug(f"Tasks list request, {len(tasks)} tasks in memory")
    return {
        "tasks": [
            {k: v for k, v in task.items() if k != "upload_path"}
            for task in tasks.values()
        ]
    }


@app.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """Delete a task and its result file."""
    task = tasks.get(task_id)
    if not task:
        logger.debug(f"Delete request for unknown task: {task_id}")
        raise HTTPException(404, "Task not found")

    # Delete result file if exists
    if task.get("result_path"):
        result_path = Path(task["result_path"])
        if result_path.exists():
            result_path.unlink()
            logger.info(f"Deleted result file: {result_path.name}")

        # Delete meta file if exists
        meta_path = result_path.parent / f"{result_path.name}{TASK_META_SUFFIX}"
        if meta_path.exists():
            meta_path.unlink()
            logger.debug(f"Deleted meta file: {meta_path.name}")

    # Remove from memory
    del tasks[task_id]
    logger.info(f"Task deleted: {task_id}")

    return {"deleted": task_id}


# === SETTINGS ===

class SettingsUpdate(BaseModel):
    hf_token: str


@app.get("/settings")
async def get_settings():
    """Get current settings (token masked if set)."""
    reload_env()  # Reload to get latest values
    return {
        "hf_token_set": is_hf_token_configured(),
        "hf_token_masked": "****" if is_hf_token_configured() else ""
    }


@app.post("/settings")
async def update_settings(settings: SettingsUpdate):
    """Save settings to .env file."""
    logger.info("Updating settings")
    try:
        # Read existing .env content (if any)
        existing_lines = []
        if ENV_FILE.exists():
            existing_lines = ENV_FILE.read_text().splitlines()

        # Update or add HF_TOKEN
        new_lines = []
        token_updated = False
        for line in existing_lines:
            if line.startswith("HF_TOKEN="):
                new_lines.append(f"HF_TOKEN={settings.hf_token}")
                token_updated = True
            else:
                new_lines.append(line)

        if not token_updated:
            new_lines.append(f"HF_TOKEN={settings.hf_token}")

        # Write back to .env
        ENV_FILE.write_text("\n".join(new_lines) + "\n")

        # Reload configuration
        reload_env()

        logger.info("Settings updated successfully")
        return {
            "success": True,
            "message": "Settings saved successfully",
            "hf_token_set": is_hf_token_configured()
        }
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        raise HTTPException(500, f"Failed to save settings: {str(e)}")


# === MAIN ===

if __name__ == "__main__":
    import uvicorn
    configure_uvicorn_logging()
    logger.info(f"Starting server on {config.HOST}:{config.PORT}")
    uvicorn.run(app, host=config.HOST, port=config.PORT)
