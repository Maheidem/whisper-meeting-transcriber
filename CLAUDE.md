# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Whisper Meeting Transcriber - a comprehensive application that transcribes meeting videos using a Whisper ASR (Automatic Speech Recognition) Docker service with support for speaker diarization (speaker identification). The project now includes three interfaces: GUI (tkinter), CLI, and Web UI.

## Architecture

The application provides three interfaces:

### GUI Application (`main.py`)
- Uses tkinter for the graphical interface
- Communicates with a Whisper ASR service via HTTP API (default: http://localhost:9000)
- Supports multiple output formats (txt, srt, vtt, json, tsv)
- Handles file uploads and transcription results
- Provides auto-save functionality with timestamps
- Includes speaker diarization controls

### CLI Application (`transcribe_cli.py`)
- Command-line interface for batch processing
- Progress bars for audio extraction and transcription
- Full speaker diarization support
- Suitable for automation and scripting

### Web UI Application (`web/`)
- Modern web-based interface using FastAPI backend
- Real-time progress updates via WebSocket
- Drag-and-drop file upload
- Mobile-responsive design with Tailwind CSS
- Task history and management
- No client installation required

## Key Components

### WhisperTranscriber Class
Main application class that manages:
- GUI setup and layout
- File selection and validation
- API communication with Whisper service
- Transcription processing in separate threads
- Result display and file saving

### API Integration
- Endpoint: `/asr` for transcription requests
- Expects multipart form data with audio file
- Parameters: `task` (transcribe) and `output` (format)
- Connection testing via `/docs` endpoint

## Speaker Diarization (Speaker Identification)

The application supports speaker diarization to identify different speakers in meetings and conversations.

### GUI Usage
1. Check the "Enable Speaker Diarization" checkbox
2. Optionally set minimum and maximum expected speakers
3. Select JSON output format to see speaker labels
4. Transcribe as normal

### CLI Usage
```bash
# Basic diarization
python transcribe_cli.py video.mp4 --diarize -f json

# With speaker count hints
python transcribe_cli.py video.mp4 --diarize --min-speakers 2 --max-speakers 4 -f json

# Save to specific file
python transcribe_cli.py video.mp4 --diarize -f json -o meeting_transcript.json
```

### Diarization Output
When using JSON format with diarization enabled, the output includes:
- Speaker labels (SPEAKER_01, SPEAKER_02, etc.)
- Word-level speaker attribution
- Segment-level speaker identification

Example JSON output:
```json
{
  "segments": [
    {
      "start": 0.554,
      "end": 2.437,
      "text": "Hello, everyone.",
      "speaker": "SPEAKER_01",
      "words": [
        {
          "word": "Hello,",
          "start": 0.554,
          "end": 0.955,
          "speaker": "SPEAKER_01"
        }
      ]
    }
  ]
}
```

### Important Notes
- Diarization works best with clear audio and distinct speakers
- The `min_speakers` and `max_speakers` parameters help improve accuracy
- Processing time increases with diarization enabled
- Best results typically with 2-6 speakers

## Development Commands

### Running the Applications

GUI Application:
```bash
python3 main.py
```

CLI Application:
```bash
python3 transcribe_cli.py --help
```

Web UI Application:
```bash
cd web
./run_server.sh
# Or manually:
# python3 -m venv venv
# source venv/bin/activate
# pip install -r requirements.txt
# uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Access the Web UI at: http://localhost:8000

### Dependencies
The application requires:
- Python 3.x with tkinter (usually included)
- `requests` library for HTTP communication
- `ffmpeg` for video to audio conversion

Install dependencies:
```bash
pip install requests
# Install ffmpeg via homebrew on macOS:
brew install ffmpeg
```

### Whisper Service Setup
The application expects a Whisper ASR service running at http://localhost:9000. This is typically provided via Docker:
```bash
docker run -d -p 9000:9000 --name whisper onerahmet/openai-whisper-asr-webservice:latest
```

**Important**: The Whisper service only accepts audio files (WAV format works best). Video files (MP4, AVI, etc.) must be converted to audio first.

## Common Development Tasks

### Testing Connection
Use the "Test Connection" button in the GUI or verify the service is accessible at the configured URL's `/docs` endpoint.

### Adding New Output Formats
Modify the `formats` list in `setup_ui()` method (line 60) to add new transcription output formats supported by the Whisper service.

### Modifying Default Settings
- Default Whisper URL: Line 25 (`http://localhost:9000`)
- Default output format: Line 24 (`txt`)
- Supported file types: Lines 112-115 in `select_file()`

### Error Handling
The application handles:
- Connection errors to Whisper service
- File upload timeouts (3600 seconds)
- Invalid responses from the API
- File I/O errors during saving

## Threading Considerations

Transcription runs in a separate thread to prevent UI freezing. Key thread-safe operations:
- UI updates are performed on the main thread
- Progress indicator runs during processing
- Button states are managed to prevent concurrent operations

## File Organization

The application uses auto-save functionality that:
- Saves transcriptions in the same directory as the source video
- Uses naming format: `{original_name}_transcription_{timestamp}.{format}`
- Timestamp format: YYYYMMDD_HHMMSS

## Known Issues and Solutions

### Video File Transcription
The Whisper service cannot process video files directly. The application now includes automatic audio extraction using ffmpeg for video formats (MP4, AVI, MOV, MKV, WEBM).

### Large Files
For large video files, the application:
1. Extracts audio to a temporary WAV file
2. Sends the audio to Whisper service
3. Cleans up temporary files after transcription

### Progress Tracking
The application includes:
- Progress bar showing extraction and transcription progress
- Real-time status updates during processing
- Ability to stop transcription mid-process

**Note**: The Whisper ASR webservice does not provide real-time progress updates. Progress bars show estimates based on file size and typical processing times. Actual transcription happens server-side without progress callbacks.

### Stopping Transcription
- Click the "Stop" button to cancel ongoing transcription
- The app will terminate FFmpeg processes and close HTTP connections
- If Whisper container is using high CPU (>10%), it will be restarted to cancel processing
- Temporary files are cleaned up automatically

### Resource Cleanup
When closing the application or stopping transcription:
- Active FFmpeg processes are terminated
- HTTP connections are closed
- Temporary audio files are deleted
- Whisper container is restarted if necessary to stop processing