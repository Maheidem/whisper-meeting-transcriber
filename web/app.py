#!/usr/bin/env python3
"""
Whisper Meeting Transcriber Web UI
FastAPI-based web application for transcribing videos/audio using Whisper ASR
"""

import os
import json
import time
import asyncio
import tempfile
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import aiofiles
import requests

# Initialize FastAPI app
app = FastAPI(title="Whisper Meeting Transcriber", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="templates")

# Store active transcription tasks
active_tasks: Dict[str, Dict[str, Any]] = {}

# WebSocket connections for progress updates
websocket_connections: Dict[str, WebSocket] = {}

# Configuration
WHISPER_URL = os.getenv("WHISPER_URL", "http://localhost:9000")
UPLOAD_DIR = Path("uploads")
RESULTS_DIR = Path("results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Model configuration - using container names within docker network
WHISPER_MODELS = {
    "tiny": {"url": "http://whisper-tiny:9000", "name": "Tiny (Fast, Less Accurate)"},
    "base": {"url": "http://whisper-base:9000", "name": "Base (Balanced)"},
    "small": {"url": "http://whisper-small:9000", "name": "Small (Good Quality)"},
    "medium": {"url": "http://whisper-medium:9000", "name": "Medium (Better Quality)"},
    # "large": {"url": "http://whisper-large:9000", "name": "Large (Best Quality)"},
    "tiny-faster": {"url": "http://whisper-tiny-faster:9000", "name": "Tiny Faster (Fastest)"},
    "base-faster": {"url": "http://whisper-base-faster:9000", "name": "Base Faster (Fast & Good)"},
    "tiny-whisperx": {"url": "http://whisper-tiny-whisperx:9000", "name": "Tiny WhisperX (With Diarization)"},
    "base-whisperx": {"url": "http://whisper-base-whisperx:9000", "name": "Base WhisperX (Better Diarization)"},
}


class TranscriptionTask(BaseModel):
    task_id: str
    filename: str
    status: str  # pending, processing, completed, failed, cancelled
    progress: int
    message: str
    result_path: Optional[str] = None
    error: Optional[str] = None
    settings: Dict[str, Any]
    created_at: datetime
    completed_at: Optional[datetime] = None
    # Metrics
    file_size_mb: Optional[float] = None
    file_duration_seconds: Optional[float] = None
    execution_time_seconds: Optional[float] = None
    transcription_speed_ratio: Optional[float] = None
    word_count: Optional[int] = None
    model_used: Optional[str] = None
    speakers_detected: Optional[int] = None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main web interface"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Check connection to Whisper service"""
    try:
        response = requests.get(f"{WHISPER_URL}/docs", timeout=5)
        if response.status_code == 200:
            return {"status": "healthy", "whisper_service": "connected"}
        else:
            return {"status": "unhealthy", "whisper_service": "error", "code": response.status_code}
    except Exception as e:
        return {"status": "unhealthy", "whisper_service": "disconnected", "error": str(e)}


@app.get("/models")
async def get_models():
    """Get available Whisper models and their status"""
    models_status = {}
    
    for model_id, config in WHISPER_MODELS.items():
        try:
            response = requests.get(f"{config['url']}/docs", timeout=2)
            models_status[model_id] = {
                "name": config["name"],
                "url": config["url"],
                "available": response.status_code == 200
            }
        except:
            models_status[model_id] = {
                "name": config["name"],
                "url": config["url"],
                "available": False
            }
    
    return models_status


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    output_format: str = Form("txt"),
    model: str = Form("tiny"),
    diarize: bool = Form(False),
    min_speakers: Optional[int] = Form(None),
    max_speakers: Optional[int] = Form(None)
):
    """Start a new transcription task"""
    # Generate unique task ID
    task_id = str(uuid4())
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate speaker parameters
    if diarize:
        if min_speakers and min_speakers < 1:
            raise HTTPException(status_code=400, detail="Minimum speakers must be at least 1")
        if max_speakers and max_speakers < 1:
            raise HTTPException(status_code=400, detail="Maximum speakers must be at least 1")
        if min_speakers and max_speakers and min_speakers > max_speakers:
            raise HTTPException(status_code=400, detail="Minimum speakers cannot exceed maximum speakers")
    
    # Save uploaded file
    upload_path = UPLOAD_DIR / f"{task_id}_{file.filename}"
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)  # Convert to MB
    
    async with aiofiles.open(upload_path, 'wb') as f:
        await f.write(content)
    
    # Get file duration
    file_duration = await get_file_duration(upload_path)
    
    # Create task entry
    task = TranscriptionTask(
        task_id=task_id,
        filename=file.filename,
        status="pending",
        progress=0,
        message="Task created",
        settings={
            "output_format": output_format,
            "model": model,
            "diarize": diarize,
            "min_speakers": min_speakers,
            "max_speakers": max_speakers
        },
        created_at=datetime.now(),
        file_size_mb=round(file_size_mb, 2),
        file_duration_seconds=file_duration,
        model_used=WHISPER_MODELS[model]["name"]
    )
    
    # Convert to dict with ISO format dates
    task_dict = task.dict()
    task_dict['created_at'] = task.created_at.isoformat()
    active_tasks[task_id] = task_dict
    
    # Start transcription in background
    asyncio.create_task(process_transcription(task_id, upload_path))
    
    return {"task_id": task_id, "status": "started"}


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time progress updates"""
    await websocket.accept()
    websocket_connections[task_id] = websocket
    
    try:
        # Send initial status
        if task_id in active_tasks:
            # Convert to JSON-serializable format
            task_data = active_tasks[task_id].copy()
            if isinstance(task_data.get('created_at'), datetime):
                task_data['created_at'] = task_data['created_at'].isoformat()
            if isinstance(task_data.get('completed_at'), datetime):
                task_data['completed_at'] = task_data['completed_at'].isoformat()
            
            await websocket.send_json(task_data)
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if task_id in websocket_connections:
            del websocket_connections[task_id]


@app.get("/status/{task_id}")
async def get_status(task_id: str):
    """Get the status of a transcription task"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return active_tasks[task_id]


@app.get("/result/{task_id}")
async def get_result(task_id: str):
    """Download the transcription result"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = active_tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Task not completed")
    
    if not task.get("result_path") or not Path(task["result_path"]).exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    return FileResponse(
        task["result_path"],
        media_type="application/octet-stream",
        filename=Path(task["result_path"]).name
    )


@app.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a running transcription task"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = active_tasks[task_id]
    if task["status"] in ["completed", "failed", "cancelled"]:
        return {"status": "already_finished"}
    
    task["status"] = "cancelled"
    task["message"] = "Cancelled by user"
    await notify_progress(task_id)
    
    return {"status": "cancelled"}


@app.get("/tasks")
async def list_tasks():
    """List all tasks"""
    # Convert all tasks to JSON-serializable format
    tasks = []
    for task in active_tasks.values():
        task_data = task.copy()
        if isinstance(task_data.get('created_at'), datetime):
            task_data['created_at'] = task_data['created_at'].isoformat()
        if isinstance(task_data.get('completed_at'), datetime):
            task_data['completed_at'] = task_data['completed_at'].isoformat()
        tasks.append(task_data)
    return tasks


async def notify_progress(task_id: str):
    """Send progress update via WebSocket if connected"""
    if task_id in websocket_connections and task_id in active_tasks:
        try:
            # Convert task dict to JSON-serializable format
            task_data = active_tasks[task_id].copy()
            if isinstance(task_data.get('created_at'), datetime):
                task_data['created_at'] = task_data['created_at'].isoformat()
            if isinstance(task_data.get('completed_at'), datetime):
                task_data['completed_at'] = task_data['completed_at'].isoformat()
            
            await websocket_connections[task_id].send_json(task_data)
        except:
            # Connection might be closed
            if task_id in websocket_connections:
                del websocket_connections[task_id]


async def get_file_duration(file_path: Path) -> Optional[float]:
    """Extract duration from audio/video file using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(file_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and stdout:
            duration = float(stdout.decode().strip())
            return duration
        return None
    except Exception as e:
        print(f"Error getting file duration: {e}")
        return None


def count_words(text: str) -> int:
    """Count words in transcription text"""
    # Remove timestamps and speaker labels for accurate word count
    cleaned_text = re.sub(r'\[\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}\]', '', text)
    cleaned_text = re.sub(r'\[SPEAKER_\d+\]:', '', cleaned_text)
    cleaned_text = re.sub(r'\d+ \d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', cleaned_text)
    words = cleaned_text.split()
    return len(words)


def count_speakers_in_text(text: str) -> int:
    """Count unique speakers in transcription"""
    speaker_pattern = r'\[SPEAKER_(\d+)\]'
    speakers = set(re.findall(speaker_pattern, text))
    return len(speakers) if speakers else 1


async def extract_audio(input_file: Path, task_id: str) -> Path:
    """Extract audio from video file"""
    output_file = UPLOAD_DIR / f"{task_id}_audio.wav"
    
    # Update progress
    active_tasks[task_id]["status"] = "processing"
    active_tasks[task_id]["progress"] = 5
    active_tasks[task_id]["message"] = "Extracting audio from video..."
    await notify_progress(task_id)
    
    # Run ffmpeg
    cmd = [
        'ffmpeg', '-i', str(input_file),
        '-vn',  # No video
        '-ac', '1',  # Mono
        '-ar', '16000',  # 16kHz sample rate
        '-f', 'wav',
        '-y',  # Overwrite
        str(output_file)
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise Exception(f"FFmpeg error: {stderr.decode()}")
    
    active_tasks[task_id]["progress"] = 15
    active_tasks[task_id]["message"] = "Audio extraction complete"
    await notify_progress(task_id)
    
    return output_file


async def process_transcription(task_id: str, file_path: Path):
    """Process transcription task"""
    start_time = time.time()  # Track execution time
    
    try:
        task = active_tasks[task_id]
        
        # Check if it's a video file
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        is_video = any(file_path.suffix.lower() == ext for ext in video_extensions)
        
        audio_file = file_path
        if is_video:
            audio_file = await extract_audio(file_path, task_id)
        
        # Update progress
        task["status"] = "processing"
        task["progress"] = 20
        task["message"] = "Uploading to Whisper service..."
        await notify_progress(task_id)
        
        # Prepare request - use the model-specific URL
        model_config = WHISPER_MODELS.get(task["settings"]["model"], WHISPER_MODELS["tiny"])
        url = f"{model_config['url']}/asr"
        
        # Build parameters
        params = {}
        if task["settings"]["output_format"] != "txt":
            params["output"] = task["settings"]["output_format"]
        
        if task["settings"]["diarize"]:
            params["diarize"] = "true"
            if task["settings"]["min_speakers"]:
                params["min_speakers"] = str(task["settings"]["min_speakers"])
            if task["settings"]["max_speakers"]:
                params["max_speakers"] = str(task["settings"]["max_speakers"])
        
        # Simulate progress during transcription
        async def update_progress():
            progress = 20
            while task["status"] == "processing" and progress < 90:
                await asyncio.sleep(2)
                progress = min(progress + 5, 90)
                task["progress"] = progress
                task["message"] = f"Transcribing... {progress}%"
                await notify_progress(task_id)
        
        # Start progress updates
        progress_task = asyncio.create_task(update_progress())
        
        # Make request
        with open(audio_file, 'rb') as f:
            files = {'audio_file': f}
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(url, files=files, params=params, timeout=3600)
            )
        
        # Cancel progress updates
        progress_task.cancel()
        
        if response.status_code == 200:
            # Save result
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_filename = f"{Path(task['filename']).stem}_transcription_{timestamp}.{task['settings']['output_format']}"
            result_path = RESULTS_DIR / result_filename
            
            transcription_text = response.text
            with open(result_path, 'w', encoding='utf-8') as f:
                if task["settings"]["output_format"] == "json":
                    json.dump(response.json(), f, indent=2)
                else:
                    f.write(transcription_text)
            
            # Calculate metrics
            execution_time = time.time() - start_time
            word_count = count_words(transcription_text)
            speakers_detected = count_speakers_in_text(transcription_text) if task["settings"]["diarize"] else None
            
            # Calculate transcription speed ratio
            speed_ratio = None
            if task.get("file_duration_seconds") and task["file_duration_seconds"] > 0:
                speed_ratio = task["file_duration_seconds"] / execution_time
            
            # Update task with metrics
            task["status"] = "completed"
            task["progress"] = 100
            task["message"] = "Transcription completed successfully"
            task["result_path"] = str(result_path)
            task["completed_at"] = datetime.now().isoformat()
            task["execution_time_seconds"] = round(execution_time, 2)
            task["word_count"] = word_count
            task["speakers_detected"] = speakers_detected
            task["transcription_speed_ratio"] = round(speed_ratio, 2) if speed_ratio else None
        else:
            raise Exception(f"Whisper service error: {response.status_code} - {response.text}")
        
    except Exception as e:
        execution_time = time.time() - start_time
        task["status"] = "failed"
        task["progress"] = 0
        task["message"] = "Transcription failed"
        task["error"] = str(e)
        task["completed_at"] = datetime.now().isoformat()
        task["execution_time_seconds"] = round(execution_time, 2)
    
    finally:
        # Clean up temporary files
        if is_video and audio_file != file_path and audio_file.exists():
            audio_file.unlink()
        if file_path.exists():
            file_path.unlink()
        
        await notify_progress(task_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)