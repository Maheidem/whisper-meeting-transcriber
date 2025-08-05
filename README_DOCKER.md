# Whisper Meeting Transcriber - Docker Setup

This project provides a complete containerized solution for transcribing meeting recordings using OpenAI's Whisper ASR with a modern web interface.

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd meeting-transcriber
   ```

2. **Start all services**
   ```bash
   docker-compose up -d
   ```

3. **Access the Web UI**
   - Open your browser to: http://localhost:8000
   - The UI will show which Whisper models are available

## Services

The docker-compose setup includes:

- **Web UI** (port 8000): Modern web interface for uploading and transcribing files
- **Whisper Models**:
  - Tiny (port 9000): Fastest, less accurate
  - Base (port 9001): Balanced speed and accuracy
  - Small (port 9002): Good quality
  - Medium (port 9003): Better quality
  - Tiny Faster (port 9010): Optimized for speed
  - Base Faster (port 9011): Fast with good accuracy
  - Tiny WhisperX (port 9020): With speaker diarization
  - Base WhisperX (port 9021): Better diarization

## Features

- Multiple Whisper model options
- Speaker diarization (WhisperX models)
- Real-time progress updates
- Support for video and audio files
- Multiple output formats (TXT, SRT, VTT, JSON, TSV)
- Automatic audio extraction from video files
- Persistent results storage

## Management Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Check service status
docker-compose ps

# Restart services
docker-compose restart

# Use the management script
./manage_whisper_compose.sh {start|stop|restart|logs|status}
```

## Volume Mappings

- Model cache: `/Users/maheidem/docker/whisper/cache` (shared across all Whisper containers)
- Uploads: `./web/uploads` (temporary storage for uploaded files)
- Results: `./web/results` (transcription results)

## Environment Variables

- `HF_TOKEN`: HuggingFace token for WhisperX models (required for speaker diarization)
- `ASR_MODEL`: Whisper model size (tiny, base, small, medium)
- `ASR_ENGINE`: Engine type (openai_whisper, faster_whisper, whisperx)

## Troubleshooting

1. **Models not available**: Wait a few minutes after starting for models to download
2. **Port conflicts**: Ensure ports 8000, 9000-9003, 9010-9011, 9020-9021 are free
3. **Memory issues**: Start with fewer models if you have limited RAM

## Requirements

- Docker and Docker Compose
- At least 8GB RAM (more for larger models)
- Disk space for model storage (varies by model size)

## Notes

- First startup will take time as models are downloaded
- Models are cached to speed up subsequent starts
- The Web UI automatically detects which models are available
- WhisperX models require a HuggingFace token for speaker diarization features