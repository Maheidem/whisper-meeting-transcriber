# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Meeting Transcriber - a lean web application that transcribes meeting recordings using faster-whisper with optional speaker diarization. Direct Python integration, no Docker containers for inference.

## Architecture

```
Browser → FastAPI (app.py) → faster-whisper (transcriber.py) → Results
   CLI → (cli.py) ────────────────────┘
```

**Key Design Decisions:**
- Direct Python Whisper calls (no HTTP overhead)
- Models lazy-loaded and cached in memory
- Single process, no microservices
- Optional Docker for deployment (not inference)
- Auto-detection of GPU backend (MLX for Apple Silicon, CUDA for NVIDIA, CPU fallback)

## Key Files

| File | Purpose |
|------|---------|
| `app.py` | FastAPI web server, routes, WebSocket progress |
| `transcriber.py` | Core Whisper logic, audio extraction, formatting |
| `config.py` | All settings in one place |
| `cli.py` | Command-line interface for transcription |
| `logging_config.py` | Centralized structured logging configuration |
| `templates/index.html` | Web UI (gets models from API) |
| `static/app.js` | Frontend JavaScript |

## Development Commands

### Run Locally
```bash
# Install dependencies
pip install -r requirements.txt
brew install ffmpeg  # macOS

# Run server
python app.py
# or with auto-reload:
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### CLI Usage
```bash
# Basic transcription
python cli.py video.mp4

# With options
python cli.py audio.wav -m small -l en -f srt

# With speaker diarization
python cli.py meeting.mp4 --diarize --min-speakers 2 --max-speakers 4

# List available options
python cli.py --list-models
python cli.py --list-languages
```

### Run with Docker
```bash
docker-compose up -d
```

### Access
http://localhost:8000

## Configuration

All settings in `config.py`:
- `DEFAULT_MODEL`: Whisper model (tiny, base, small, medium, large-v3)
- `DEVICE`: auto, cpu, cuda, or mlx
- `GPU_BACKEND`: Auto-detected (mlx for Apple Silicon, cuda for NVIDIA, cpu fallback)
- `HF_TOKEN`: HuggingFace token for speaker diarization
- `COMPUTE_TYPE`: float16 (GPU) or int8 (CPU)

### GPU Auto-Detection

The system automatically detects the best available backend:
- **Apple Silicon (M-series)**: Uses MLX for GPU acceleration
- **NVIDIA GPU**: Uses CUDA
- **No GPU**: Falls back to CPU

Check current status via `/gpu` endpoint.

## Speaker Diarization

Requires:
1. HuggingFace token (set via web UI Settings or `HF_TOKEN` env var)
2. `pip install git+https://github.com/m-bain/whisperX.git`
3. Accept pyannote model terms on HuggingFace

### Speaker Range Parameters

The `/transcribe` endpoint accepts optional speaker hints:
- `min_speakers`: Minimum expected speakers
- `max_speakers`: Maximum expected speakers

## Language Support

40+ supported languages available. Key languages include:
- Auto-detect, English, Spanish, French, German, Italian, Portuguese
- Russian, Japanese, Chinese, Korean, Arabic, Hindi
- Full list: `/languages` endpoint or `python cli.py --list-languages`

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Web UI |
| `/health` | GET | Health check |
| `/gpu` | GET | GPU status and acceleration info |
| `/models` | GET | Available models |
| `/formats` | GET | Output formats |
| `/languages` | GET | Available languages |
| `/transcribe` | POST | Start transcription |
| `/ws/{task_id}` | WS | Progress updates |
| `/status/{task_id}` | GET | Polling fallback |
| `/result/{task_id}` | GET | Download result |
| `/tasks` | GET | List all tasks |
| `/task/{task_id}` | DELETE | Delete a task and its result file |
| `/settings` | GET | Get current settings (token masked) |
| `/settings` | POST | Save HuggingFace token to .env |

## Progress Tracking

Transcription progress includes detailed steps:
- `extracting`: Extracting audio from file
- `loading_model`: Loading Whisper model
- `transcribing`: Running transcription
- `diarizing`: Speaker identification (if enabled)
- `formatting`: Generating output format
- `complete`: Task finished

Progress data includes:
- `audio_duration`: Total audio length
- `current_time`: Current position during transcription
- `segments_processed` / `segments_total`: Segment counts

## Data Flow

1. User uploads file via `/transcribe`
2. File saved to `uploads/`
3. Background task starts transcription
4. Progress sent via WebSocket (with step details)
5. Result saved to `results/`
6. Temp files cleaned up

## Adding New Models

Edit `config.py`:
```python
AVAILABLE_MODELS = {
    "new-model": {
        "name": "Display Name",
        "description": "Description",
        "supports_diarization": True
    }
}
```

Frontend automatically picks up changes from `/models` endpoint.

## Output Formats

- `txt`: Plain text (with speaker labels if diarization enabled)
- `srt`: SubRip subtitles
- `vtt`: WebVTT subtitles
- `json`: Full data with segments, timestamps, speakers
- `tsv`: Tab-separated values

## Logging

Logs written to `logs/transcriber.log` with structured format:
```
[timestamp] [LEVEL] [COMPONENT] message
```

Components: APP, TRANSCRIBER, WEBSOCKET, UVICORN

Use `logging_config.get_logger("component")` for new modules.

## Troubleshooting

### Model Download Slow
Models download on first use (~500MB-3GB). Be patient.

### Out of Memory
Use smaller model (tiny or base) or increase system RAM.

### Diarization Not Working
- Check `HF_TOKEN` is set (via Settings page or .env)
- Verify pyannote terms accepted on HuggingFace
- Install whisperx: `pip install git+https://github.com/m-bain/whisperX.git`

### GPU Not Detected
- Check `/gpu` endpoint for current backend status
- Apple Silicon: Ensure mlx is installed (`pip install mlx`)
- NVIDIA: Ensure CUDA and torch are properly installed
