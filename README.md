# 🎙️ Whisper Meeting Transcriber

A powerful, containerized web application for transcribing meeting recordings using OpenAI's Whisper ASR with speaker diarization support. Features a modern web interface and supports multiple Whisper model variants for different speed/accuracy trade-offs.

![Whisper Meeting Transcriber Screenshot](docs/screenshot.png)

## ✨ Features

- **🚀 Web-Based Interface**: Modern, responsive UI built with FastAPI and Tailwind CSS
- **🎯 Multiple Whisper Models**: Choose from 8 different model configurations
- **👥 Speaker Diarization**: Identify and label different speakers (WhisperX models)
- **📹 Video Support**: Automatic audio extraction from video files
- **📊 Real-time Progress**: Live transcription progress updates via WebSocket
- **📁 Multiple Output Formats**: TXT, SRT, VTT, JSON, TSV
- **🐳 Fully Containerized**: Simple deployment with Docker Compose
- **🔒 Network Isolation**: Secure internal communication between services

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- 8GB+ RAM (more for larger models)
- (Optional) HuggingFace account for speaker diarization

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/whisper-meeting-transcriber.git
   cd whisper-meeting-transcriber
   ```

2. **Set up environment variables** (optional, for speaker diarization)
   ```bash
   cp .env.example .env
   # Edit .env and add your HuggingFace token
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   ```
   http://localhost:8000
   ```

## 📦 Available Models

| Model | Speed | Accuracy | Speaker Diarization |
|-------|-------|----------|-------------------|
| Tiny | ⚡⚡⚡⚡⚡ | ⭐⭐ | ❌ |
| Base | ⚡⚡⚡⚡ | ⭐⭐⭐ | ❌ |
| Small | ⚡⚡⚡ | ⭐⭐⭐⭐ | ❌ |
| Medium | ⚡⚡ | ⭐⭐⭐⭐⭐ | ❌ |
| Tiny Faster | ⚡⚡⚡⚡⚡⚡ | ⭐⭐ | ❌ |
| Base Faster | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ | ❌ |
| Tiny WhisperX | ⚡⚡⚡⚡ | ⭐⭐ | ✅ |
| Base WhisperX | ⚡⚡⚡ | ⭐⭐⭐ | ✅ |

## 🎯 Usage

1. **Upload File**: Drag and drop or browse to select your audio/video file
2. **Configure Settings**:
   - Select Whisper model based on your speed/accuracy needs
   - Choose output format
   - Enable speaker diarization (WhisperX models only)
   - Set min/max speakers if known
3. **Start Transcription**: Click "Start Transcription" and monitor progress
4. **Download Results**: Download the transcription in your chosen format

### Supported File Formats

- **Video**: MP4, AVI, MOV, MKV, WEBM
- **Audio**: MP3, WAV, M4A, FLAC, OGG

## 🛠️ Architecture

```
┌─────────────────┐
│   Web Browser   │
└────────┬────────┘
         │ Port 8000
┌────────┴────────┐
│   Web UI        │
│  (FastAPI)      │
└────────┬────────┘
         │ Internal Docker Network
┌────────┴────────────────────────────┐
│          Whisper Services           │
├─────────────┬─────────────┬────────┤
│  Standard   │   Faster    │WhisperX│
│  Models     │   Models    │Models  │
└─────────────┴─────────────┴────────┘
```

## 📝 Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Required for WhisperX speaker diarization
HF_TOKEN=your_huggingface_token_here
```

### Docker Compose Customization

You can modify `docker-compose.yml` to:
- Enable/disable specific models
- Adjust resource limits
- Change volume mappings
- Modify cache directories

## 🔧 Management

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart services
docker-compose restart
```

### Using Management Script

```bash
# Make script executable
chmod +x manage_whisper_compose.sh

# Use the script
./manage_whisper_compose.sh start|stop|restart|logs|status
```

## 🚨 Troubleshooting

### Models Not Available
- Wait a few minutes after first startup for models to download
- Check logs: `docker-compose logs whisper-tiny`

### Out of Memory
- Start with fewer models by commenting them out in `docker-compose.yml`
- Use smaller models (tiny, base) instead of larger ones

### Speaker Diarization Not Working
- Ensure HF_TOKEN is set in `.env`
- Use WhisperX model variants
- Check logs: `docker-compose logs whisper-tiny-whisperx`

## 🏗️ Development

### Local Development

1. **Set up Python environment**
   ```bash
   cd web
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

2. **Run locally**
   ```bash
   # Start Whisper services
   docker-compose up -d whisper-tiny whisper-base

   # Run web UI locally
   cd web
   python app.py
   ```

### Project Structure

```
whisper-meeting-transcriber/
├── web/                    # Web UI application
│   ├── app.py             # FastAPI backend
│   ├── requirements.txt   # Python dependencies
│   ├── Dockerfile         # Web UI container
│   ├── static/            # Frontend assets
│   │   └── js/
│   │       └── app.js     # Frontend JavaScript
│   └── templates/
│       └── index.html     # Main UI template
├── docker-compose.yml     # Service orchestration
├── manage_whisper_compose.sh  # Management script
├── .env.example          # Environment template
└── README.md             # This file
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - The amazing ASR model
- [Whisper ASR Webservice](https://github.com/ahmetoner/whisper-asr-webservice) - Docker container for Whisper
- [WhisperX](https://github.com/m-bain/whisperX) - Speaker diarization support
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/whisper-meeting-transcriber/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/whisper-meeting-transcriber/discussions)

---

Made with ❤️ by the community