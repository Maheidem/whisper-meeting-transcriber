# Whisper Meeting Transcriber - Web UI

A modern web-based interface for transcribing meeting recordings using Whisper ASR with speaker diarization support.

## Features

- 🎯 **Drag & Drop Upload**: Simple file upload with drag-and-drop support
- 🎤 **Speaker Diarization**: Identify and label different speakers in conversations
- 📊 **Real-time Progress**: WebSocket-based progress updates during transcription
- 📁 **Multiple Formats**: Support for TXT, SRT, VTT, JSON, and TSV output
- 🎬 **Video Support**: Automatic audio extraction from video files
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile devices
- 📜 **Task History**: View and download previous transcriptions
- ❌ **Cancellation**: Stop long-running transcriptions

## Quick Start

1. **Start the Whisper service** (if not already running):
   ```bash
   docker run -d -p 9000:9000 --name whisper onerahmet/openai-whisper-asr-webservice:latest
   ```

2. **Run the web server**:
   ```bash
   cd web
   ./run_server.sh
   ```

3. **Open your browser** at http://localhost:8000

## Installation

### Requirements
- Python 3.8+
- FFmpeg (for video processing)
- Docker (for Whisper service)

### Manual Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

- `GET /` - Web interface
- `GET /health` - Check service health
- `POST /transcribe` - Start transcription
- `GET /ws/{task_id}` - WebSocket for progress
- `GET /status/{task_id}` - Get task status
- `GET /result/{task_id}` - Download result
- `POST /cancel/{task_id}` - Cancel task
- `GET /tasks` - List all tasks

## Configuration

Environment variables:
- `WHISPER_URL` - Whisper service URL (default: http://localhost:9000)

## Usage

### Basic Transcription
1. Upload a video or audio file
2. Select output format
3. Click "Start Transcription"
4. Download the result when complete

### Speaker Diarization
1. Enable "Speaker Diarization"
2. Optionally set min/max speakers
3. Use JSON format to see speaker labels
4. Each speaker will be labeled as SPEAKER_01, SPEAKER_02, etc.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Browser   │────▶│   FastAPI    │────▶│   Whisper   │
│  (Frontend) │◀────│   Backend    │◀────│   Service   │
└─────────────┘     └──────────────┘     └─────────────┘
      │                    │
      │   WebSocket       │
      └───────────────────┘
```

## File Structure

```
web/
├── app.py              # FastAPI backend
├── requirements.txt    # Python dependencies
├── run_server.sh      # Startup script
├── static/
│   └── js/
│       └── app.js     # Frontend JavaScript
├── templates/
│   └── index.html     # Web interface
├── uploads/           # Temporary file storage
└── results/           # Transcription results
```

## Troubleshooting

### Whisper Service Not Connected
- Ensure Docker is running
- Check if Whisper container is active: `docker ps`
- Verify port 9000 is not in use: `lsof -i :9000`

### FFmpeg Not Found
- Install FFmpeg:
  - macOS: `brew install ffmpeg`
  - Ubuntu: `sudo apt-get install ffmpeg`
  - Windows: Download from ffmpeg.org

### Large Files Timeout
- The service has a 1-hour timeout for large files
- Consider splitting very long recordings

## Development

### Running in Development Mode
```bash
uvicorn app:app --reload
```

### Adding New Features
1. Update the API in `app.py`
2. Add UI elements in `index.html`
3. Update frontend logic in `app.js`

## Security Notes

- Files are temporarily stored during processing
- Automatic cleanup after transcription
- No authentication by default (add if needed)
- CORS enabled for development