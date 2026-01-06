# 🎙️ Meeting Transcriber

A lean, fast web application for transcribing meetings using Whisper. Direct Python integration - no Docker overhead for inference.

## ✨ Features

- **🚀 Fast**: Direct Whisper integration - no HTTP overhead
- **🎯 Simple**: One Python app, one optional Docker container
- **👥 Speaker Diarization**: Identify different speakers (requires HF token)
- **📹 Video Support**: Automatic audio extraction from video files
- **📊 Real-time Progress**: Live updates via WebSocket
- **📁 Multiple Formats**: TXT, SRT, VTT, JSON, TSV

## 🚀 Quick Start

### Option 1: Python (Recommended for Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Install ffmpeg (macOS)
brew install ffmpeg

# Run the app
python app.py
```

Open http://localhost:8000

### Option 2: Docker (For Deployment)

```bash
docker-compose up -d
```

Open http://localhost:8000

## 📦 Available Models

| Model | Speed | Accuracy | RAM |
|-------|-------|----------|-----|
| tiny | ⚡⚡⚡⚡⚡ | ⭐⭐ | ~1GB |
| base | ⚡⚡⚡⚡ | ⭐⭐⭐ | ~1GB |
| small | ⚡⚡⚡ | ⭐⭐⭐⭐ | ~2GB |
| medium | ⚡⚡ | ⭐⭐⭐⭐⭐ | ~5GB |
| large-v3 | ⚡ | ⭐⭐⭐⭐⭐⭐ | ~10GB |

Models download automatically on first use.

## 👥 Speaker Diarization

To enable speaker identification:

1. Get a HuggingFace token from https://huggingface.co/settings/tokens
2. Accept terms for pyannote models:
   - https://huggingface.co/pyannote/speaker-diarization
   - https://huggingface.co/pyannote/segmentation
3. Set the token:
   ```bash
   export HF_TOKEN=your_token_here
   # or add to .env file
   ```
4. Install whisperx:
   ```bash
   pip install git+https://github.com/m-bain/whisperX.git
   ```

## 🎯 Usage

### Web UI
1. **Upload**: Drag & drop or select your audio/video file
2. **Configure**: Choose model, language, format, and speaker options
3. **Transcribe**: Click the button and watch progress
4. **Download**: Get your transcription

### CLI
```bash
# Basic transcription
python cli.py video.mp4

# With options
python cli.py meeting.mp4 -m small -l en -f srt

# With speaker diarization
python cli.py call.mp3 --diarize --min-speakers 2 --max-speakers 4

# Save to specific file
python cli.py audio.wav -o transcript.txt

# List available models and languages
python cli.py --list-models
python cli.py --list-languages
```

### Supported Files

- **Video**: MP4, AVI, MOV, MKV, WEBM, M4V
- **Audio**: WAV, MP3, FLAC, OGG, M4A, AAC

## 📁 Project Structure

```
meeting-transcriber/
├── app.py              # FastAPI web server
├── cli.py              # Command-line interface
├── transcriber.py      # Whisper transcription logic
├── config.py           # All configuration
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container build
├── docker-compose.yml  # Easy deployment
├── templates/          # HTML templates
├── static/             # Frontend JS
├── models/             # Cached Whisper models
├── uploads/            # Temporary uploads
└── results/            # Transcription outputs
```

## ⚙️ Configuration

All settings in `config.py` or via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | 0.0.0.0 | Server host |
| `PORT` | 8000 | Server port |
| `DEFAULT_MODEL` | base | Default Whisper model |
| `DEVICE` | auto | cpu, cuda, or auto |
| `HF_TOKEN` | - | HuggingFace token for diarization |

## 🔧 Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## 📄 License

MIT License - see [LICENSE](LICENSE)

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper)
- [faster-whisper](https://github.com/guillaumekln/faster-whisper)
- [WhisperX](https://github.com/m-bain/whisperX)
- [FastAPI](https://fastapi.tiangolo.com/)
