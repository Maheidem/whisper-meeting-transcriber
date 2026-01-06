"""
Transcriber - Core Whisper logic with lazy model loading.

Supports multiple backends:
- MLX (Apple Silicon) - fastest on Mac M1/M2/M3
- CUDA (NVIDIA) - fastest on Windows/Linux with GPU
- CPU - fallback for all platforms
"""
import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime
import time

from config import (
    DEVICE, COMPUTE_TYPE, HF_TOKEN, MODELS_DIR, GPU_BACKEND,
    SUPPORTED_VIDEO_EXTENSIONS, RESULTS_DIR
)
from logging_config import get_logger

# Logger for transcriber module
logger = get_logger("transcriber")

# Model cache - loaded on demand, kept in memory
_model_cache = {}
_diarize_pipeline = None
_active_backend = None  # Track which backend is being used


def get_active_backend():
    """Get the currently active transcription backend."""
    global _active_backend
    if _active_backend is None:
        # Determine best backend
        if DEVICE == "mlx" or (DEVICE == "auto" and GPU_BACKEND == "mlx"):
            try:
                import mlx_whisper
                _active_backend = "mlx"
            except ImportError:
                logger.warning("MLX requested but mlx-whisper not installed. Falling back.")
                _active_backend = "faster-whisper"
        else:
            _active_backend = "faster-whisper"
    return _active_backend


def get_model(model_name: str):
    """Lazy load and cache Whisper model using best available backend."""
    backend = get_active_backend()

    cache_key = f"{backend}:{model_name}"
    if cache_key not in _model_cache:
        logger.info(f"Loading model: {model_name} (backend={backend})")
        start_time = time.time()

        if backend == "mlx":
            # MLX backend for Apple Silicon
            _model_cache[cache_key] = _load_mlx_model(model_name)
        else:
            # faster-whisper backend (CUDA or CPU)
            _model_cache[cache_key] = _load_faster_whisper_model(model_name)

        elapsed = time.time() - start_time
        logger.info(f"Model loaded in {elapsed:.2f}s: {model_name} (backend={backend})")
    else:
        logger.debug(f"Using cached model: {model_name}")

    return _model_cache[cache_key]


def _load_mlx_model(model_name: str):
    """Load model using MLX (Apple Silicon optimized)."""
    # MLX-whisper uses a different model naming convention
    mlx_model_map = {
        "tiny": "mlx-community/whisper-tiny-mlx",
        "base": "mlx-community/whisper-base-mlx",
        "small": "mlx-community/whisper-small-mlx",
        "medium": "mlx-community/whisper-medium-mlx",
        "large-v3": "mlx-community/whisper-large-v3-mlx",
    }
    mlx_model = mlx_model_map.get(model_name, f"mlx-community/whisper-{model_name}-mlx")
    logger.info(f"Loading MLX model: {mlx_model}")
    return {"type": "mlx", "model_id": mlx_model, "name": model_name}


def _load_faster_whisper_model(model_name: str):
    """Load model using faster-whisper (CUDA/CPU)."""
    from faster_whisper import WhisperModel

    # Determine device
    if DEVICE == "auto":
        device = "cuda" if GPU_BACKEND == "cuda" else "cpu"
    else:
        device = DEVICE if DEVICE in ("cuda", "cpu") else "cpu"

    compute_type = COMPUTE_TYPE
    logger.debug(f"faster-whisper config: device={device}, compute_type={compute_type}")

    try:
        model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            download_root=str(MODELS_DIR)
        )
        logger.info(f"Model loaded on {device.upper()}")
        return {"type": "faster-whisper", "model": model, "device": device}
    except Exception as e:
        if device == "cuda":
            logger.warning(f"CUDA load failed, falling back to CPU: {e}")
            model = WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8",
                download_root=str(MODELS_DIR)
            )
            logger.info("Model loaded on CPU (fallback)")
            return {"type": "faster-whisper", "model": model, "device": "cpu"}
        raise


def get_diarize_pipeline():
    """Lazy load diarization pipeline (requires HF_TOKEN)."""
    global _diarize_pipeline
    if _diarize_pipeline is None and HF_TOKEN:
        logger.info("Loading diarization pipeline")
        start_time = time.time()

        try:
            # Fix PyTorch serialization security for pyannote models (PyTorch 2.6+)
            # PyTorch's weights_only=True is strict - we need to allowlist pyannote classes
            import torch

            # Allowlist all required classes for pyannote speaker diarization
            safe_classes = []

            # PyTorch internal
            from torch.torch_version import TorchVersion
            safe_classes.append(TorchVersion)

            # pyannote.audio.core.task classes
            from pyannote.audio.core.task import Specifications, Problem, Resolution
            safe_classes.extend([Specifications, Problem, Resolution])

            # pyannote.audio.core.io and model
            try:
                from pyannote.audio.core.io import Audio
                safe_classes.append(Audio)
            except ImportError:
                pass

            try:
                from pyannote.audio.core.model import Model
                safe_classes.append(Model)
            except ImportError:
                pass

            # Add all to safe globals
            torch.serialization.add_safe_globals(safe_classes)
            logger.debug(f"Added {len(safe_classes)} safe globals for PyTorch serialization")

            # WhisperX 3.x: DiarizationPipeline is in whisperx.diarize submodule
            from whisperx.diarize import DiarizationPipeline

            # Determine device for diarization
            diarize_device = DEVICE if DEVICE not in ("auto", "mlx") else "cpu"
            if GPU_BACKEND == "cuda" and DEVICE == "auto":
                diarize_device = "cuda"

            _diarize_pipeline = DiarizationPipeline(
                use_auth_token=HF_TOKEN,
                device=diarize_device
            )
            elapsed = time.time() - start_time
            logger.info(f"Diarization pipeline loaded in {elapsed:.2f}s (device={diarize_device})")
        except Exception as e:
            logger.error(f"Could not load diarization pipeline: {e}", exc_info=True)
            return None
    elif not HF_TOKEN:
        logger.debug("Diarization disabled: HF_TOKEN not set")

    return _diarize_pipeline


async def extract_audio(video_path: Path, progress_callback: Optional[Callable] = None) -> Path:
    """Extract audio from video using ffmpeg."""
    audio_path = video_path.with_suffix(".wav")

    file_size_mb = video_path.stat().st_size / (1024 * 1024)
    logger.info(f"Extracting audio: {video_path.name} ({file_size_mb:.2f} MB)")
    start_time = time.time()

    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(audio_path)
    ]
    logger.debug(f"FFmpeg command: {' '.join(cmd)}")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    await process.wait()

    if process.returncode != 0:
        logger.error(f"FFmpeg failed with code {process.returncode}")
        raise RuntimeError(f"FFmpeg failed with code {process.returncode}")

    elapsed = time.time() - start_time
    audio_size_mb = audio_path.stat().st_size / (1024 * 1024)
    logger.info(f"Audio extracted in {elapsed:.2f}s: {audio_path.name} ({audio_size_mb:.2f} MB)")

    return audio_path


def get_audio_duration(file_path: Path) -> float:
    """Get audio/video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)],
            capture_output=True, text=True
        )
        duration = float(result.stdout.strip())
        logger.debug(f"File duration: {duration:.2f}s - {file_path.name}")
        return duration
    except Exception as e:
        logger.warning(f"Could not get duration for {file_path.name}: {e}")
        return 0.0


async def transcribe(
    file_path: Path,
    model_name: str = "base",
    output_format: str = "txt",
    language: str = "auto",
    diarize: bool = False,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
    progress_callback: Optional[Callable] = None,
) -> dict:
    """
    Transcribe audio/video file.

    Args:
        language: ISO 639-1 code (e.g., "en", "es") or "auto" for detection

    Returns dict with:
        - text: Full transcription text
        - segments: List of segments with timestamps
        - language: Detected/specified language
        - duration: File duration in seconds
        - speakers: Number of speakers (if diarization enabled)
    """
    file_path = Path(file_path)
    temp_audio = None

    # Get file size for progress messages
    file_size_mb = file_path.stat().st_size / (1024 * 1024)

    # Get duration upfront for ETA calculations
    audio_duration = get_audio_duration(file_path)

    logger.info(f"Starting transcription: {file_path.name} ({file_size_mb:.2f} MB, {audio_duration:.2f}s)")
    logger.info(f"Options: model={model_name}, format={output_format}, lang={language}, diarize={diarize}")
    transcription_start = time.time()

    try:
        # Extract audio if video
        if file_path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
            if progress_callback:
                await progress_callback({
                    "progress": 5,
                    "message": f"Extracting audio from video ({file_size_mb:.1f} MB)...",
                    "step": "extracting",
                    "step_name": "Extracting Audio",
                    "audio_duration": audio_duration,
                })
            temp_audio = await extract_audio(file_path)
            audio_path = temp_audio
        else:
            audio_path = file_path
            logger.debug(f"Audio file, no extraction needed: {file_path.name}")
            if progress_callback:
                await progress_callback({
                    "progress": 10,
                    "message": "Preparing audio file...",
                    "step": "preparing",
                    "step_name": "Preparing",
                    "audio_duration": audio_duration,
                })

        if progress_callback:
            await progress_callback({
                "progress": 15,
                "message": f"Loading {model_name} model...",
                "step": "loading_model",
                "step_name": "Loading Model",
                "audio_duration": audio_duration,
                "substep": f"Initializing {model_name} weights",
            })

        # Load model
        model = get_model(model_name)

        if progress_callback:
            await progress_callback({
                "progress": 20,
                "message": "Starting transcription...",
                "step": "transcribing",
                "step_name": "Transcribing",
                "audio_duration": audio_duration,
            })

        # Transcribe (language=None means auto-detect)
        lang_param = None if language == "auto" else language
        logger.info(f"Starting Whisper transcription: lang={lang_param or 'auto-detect'}")
        whisper_start = time.time()

        # Run transcription in thread to avoid blocking event loop
        # This allows WebSocket messages to be sent during transcription
        def run_transcription():
            """Transcription runs in separate thread (works with both backends)."""
            model_info = model  # model is actually a dict with backend info

            if model_info["type"] == "mlx":
                # MLX backend (Apple Silicon)
                import mlx_whisper
                result = mlx_whisper.transcribe(
                    str(audio_path),
                    path_or_hf_repo=model_info["model_id"],
                    language=lang_param,
                    word_timestamps=diarize,
                )
                # Convert MLX result format to our standard format
                segments = []
                for seg in result.get("segments", []):
                    seg_dict = {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"].strip(),
                    }
                    if "words" in seg:
                        seg_dict["words"] = [
                            {"word": w["word"], "start": w["start"], "end": w["end"]}
                            for w in seg["words"]
                        ]
                    segments.append(seg_dict)

                # Create info-like object for compatibility
                class Info:
                    language = result.get("language", lang_param or "en")
                return segments, Info()

            else:
                # faster-whisper backend (CUDA/CPU)
                fw_model = model_info["model"]
                segments_gen, info = fw_model.transcribe(
                    str(audio_path),
                    language=lang_param,
                    beam_size=5,
                    word_timestamps=True if diarize else False
                )
                # Convert generator to list (must be done in same thread)
                segments = []
                for segment in segments_gen:
                    seg_dict = {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.strip(),
                    }
                    if hasattr(segment, 'words') and segment.words:
                        seg_dict["words"] = [
                            {"word": w.word, "start": w.start, "end": w.end}
                            for w in segment.words
                        ]
                    segments.append(seg_dict)
                return segments, info

        # Progress monitoring in separate task
        async def monitor_progress():
            """Send progress updates while transcription runs."""
            last_progress_update = 20
            last_progress_log = 0

            while True:
                await asyncio.sleep(2)  # Check every 2 seconds

                # Estimate progress based on elapsed time vs expected duration
                elapsed = time.time() - whisper_start
                # Estimate: ~0.5x realtime on CPU, ~2x on GPU
                estimated_total = audio_duration * 0.5 if DEVICE == "cpu" else audio_duration * 0.3
                if estimated_total > 0:
                    progress_ratio = min(elapsed / estimated_total, 0.95)
                    max_transcribe_pct = 70 if diarize else 85
                    current_progress = int(20 + progress_ratio * (max_transcribe_pct - 20))

                    # Log at 25%, 50%, 75%
                    progress_pct = int(progress_ratio * 100)
                    if progress_pct >= last_progress_log + 25:
                        last_progress_log = (progress_pct // 25) * 25
                        logger.info(f"Transcription progress: {last_progress_log}%")

                    if progress_callback and current_progress >= last_progress_update + 5:
                        last_progress_update = current_progress
                        await progress_callback({
                            "progress": current_progress,
                            "message": f"Transcribing audio ({int(elapsed)}s elapsed)...",
                            "step": "transcribing",
                            "step_name": "Transcribing",
                            "audio_duration": audio_duration,
                            "current_time": elapsed * (2 if DEVICE == "cpu" else 3),
                        })

        # Start progress monitor
        progress_task = asyncio.create_task(monitor_progress())

        try:
            # Run CPU-bound transcription in thread pool
            segments, info = await asyncio.to_thread(run_transcription)
        finally:
            # Stop progress monitor
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

        segment_count = len(segments)

        whisper_elapsed = time.time() - whisper_start
        logger.info(f"Whisper transcription completed in {whisper_elapsed:.2f}s")
        logger.info(f"Detected language: {info.language}, segments: {len(segments)}")

        # Apply diarization if requested
        speakers_detected = 0
        if diarize:
            logger.info(f"Diarization enabled: min_speakers={min_speakers}, max_speakers={max_speakers}")

            if HF_TOKEN:
                if progress_callback:
                    await progress_callback({
                        "progress": 75,
                        "message": "Loading speaker diarization model...",
                        "step": "diarizing",
                        "step_name": "Identifying Speakers",
                        "audio_duration": audio_duration,
                        "substep": "Initializing pyannote pipeline",
                    })

                try:
                    import whisperx
                    diarize_start = time.time()

                    # Load audio for whisperx
                    audio = whisperx.load_audio(str(audio_path))
                    logger.debug("Audio loaded for diarization")

                    if progress_callback:
                        await progress_callback({
                            "progress": 80,
                            "message": "Analyzing speaker patterns...",
                            "step": "diarizing",
                            "step_name": "Identifying Speakers",
                            "audio_duration": audio_duration,
                            "substep": "Running voice activity detection",
                        })

                    # Get diarization
                    pipeline = get_diarize_pipeline()
                    if pipeline:
                        diarize_result = pipeline(
                            audio,
                            min_speakers=min_speakers,
                            max_speakers=max_speakers
                        )

                        if progress_callback:
                            await progress_callback({
                                "progress": 85,
                                "message": "Assigning speakers to segments...",
                                "step": "diarizing",
                                "step_name": "Identifying Speakers",
                                "audio_duration": audio_duration,
                                "substep": "Matching speakers to transcript",
                            })

                        # Assign speakers to segments
                        result_with_speakers = whisperx.assign_word_speakers(
                            diarize_result, {"segments": segments}
                        )
                        segments = result_with_speakers.get("segments", segments)

                        # Count unique speakers
                        speaker_set = set()
                        for seg in segments:
                            if "speaker" in seg:
                                speaker_set.add(seg["speaker"])
                        speakers_detected = len(speaker_set)

                        diarize_elapsed = time.time() - diarize_start
                        logger.info(f"Diarization completed in {diarize_elapsed:.2f}s: {speakers_detected} speakers detected")
                    else:
                        logger.warning("Diarization pipeline not available")
                except Exception as e:
                    logger.error(f"Diarization failed: {e}", exc_info=True)
            else:
                logger.warning("Diarization requested but HF_TOKEN not set")
        else:
            logger.debug("Diarization disabled")

        if progress_callback:
            await progress_callback({
                "progress": 90,
                "message": "Formatting output...",
                "step": "formatting",
                "step_name": "Formatting",
                "audio_duration": audio_duration,
                "segments_total": len(segments),
            })

        # Build result
        full_text = " ".join(seg["text"] for seg in segments)
        duration = audio_duration if audio_duration > 0 else get_audio_duration(file_path)
        word_count = len(full_text.split())

        result = {
            "text": full_text,
            "segments": segments,
            "language": info.language,
            "duration": duration,
            "speakers": speakers_detected,
            "model": model_name,
        }

        total_elapsed = time.time() - transcription_start
        logger.info(f"Transcription complete: {duration:.2f}s audio processed in {total_elapsed:.2f}s")
        logger.info(f"Result: {word_count} words, {len(segments)} segments, {speakers_detected} speakers")

        if progress_callback:
            await progress_callback({
                "progress": 100,
                "message": "Transcription complete!",
                "step": "complete",
                "step_name": "Complete",
                "audio_duration": audio_duration,
                "segments_total": len(segments),
                "word_count": word_count,
            })

        return result

    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        raise

    finally:
        # Cleanup temp audio
        if temp_audio and temp_audio.exists():
            logger.debug(f"Cleaning up temp audio: {temp_audio.name}")
            temp_audio.unlink()


def format_output(result: dict, output_format: str) -> str:
    """Format transcription result to requested format."""
    logger.debug(f"Formatting output as: {output_format}")

    if output_format == "json":
        import json
        return json.dumps(result, indent=2, ensure_ascii=False)

    elif output_format == "txt":
        if result.get("speakers", 0) > 0:
            # Include speaker labels
            lines = []
            for seg in result["segments"]:
                speaker = seg.get("speaker", "")
                text = seg["text"]
                if speaker:
                    lines.append(f"[{speaker}] {text}")
                else:
                    lines.append(text)
            return "\n".join(lines)
        return result["text"]

    elif output_format == "srt":
        lines = []
        for i, seg in enumerate(result["segments"], 1):
            start = _format_timestamp_srt(seg["start"])
            end = _format_timestamp_srt(seg["end"])
            text = seg["text"]
            if seg.get("speaker"):
                text = f"[{seg['speaker']}] {text}"
            lines.append(f"{i}\n{start} --> {end}\n{text}\n")
        return "\n".join(lines)

    elif output_format == "vtt":
        lines = ["WEBVTT\n"]
        for seg in result["segments"]:
            start = _format_timestamp_vtt(seg["start"])
            end = _format_timestamp_vtt(seg["end"])
            text = seg["text"]
            if seg.get("speaker"):
                text = f"[{seg['speaker']}] {text}"
            lines.append(f"{start} --> {end}\n{text}\n")
        return "\n".join(lines)

    elif output_format == "tsv":
        lines = ["start\tend\ttext"]
        for seg in result["segments"]:
            text = seg["text"]
            if seg.get("speaker"):
                text = f"[{seg['speaker']}] {text}"
            lines.append(f"{seg['start']:.3f}\t{seg['end']:.3f}\t{text}")
        return "\n".join(lines)

    return result["text"]


def _format_timestamp_srt(seconds: float) -> str:
    """Format seconds to SRT timestamp (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_timestamp_vtt(seconds: float) -> str:
    """Format seconds to VTT timestamp (HH:MM:SS.mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def save_result(result: dict, original_filename: str, output_format: str) -> Path:
    """Save transcription result to file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = Path(original_filename).stem
    output_filename = f"{stem}_transcription_{timestamp}.{output_format}"
    output_path = RESULTS_DIR / output_filename

    logger.info(f"Saving result: {output_filename}")

    formatted = format_output(result, output_format)
    output_path.write_text(formatted, encoding="utf-8")

    file_size_kb = output_path.stat().st_size / 1024
    logger.info(f"Result saved: {output_path.name} ({file_size_kb:.2f} KB)")

    return output_path
