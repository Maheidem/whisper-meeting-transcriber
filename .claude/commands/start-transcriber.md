---
allowed-tools: Bash, Glob, Read
description: Start the Meeting Transcriber web application on localhost:8000
---

Start the Meeting Transcriber FastAPI web application in the background using the project's virtual environment.

## Pre-flight Check

Check port 8000: `netstat -ano | findstr :8000`

## Workflow

1. **Check Port**: If port 8000 is occupied, report it and STOP
   - Report: "Port 8000 is already in use by process {PID}"
   - Suggest: "Run /stop-transcriber first"

2. **Validate Environment**: Confirm project setup
   - Check for existence of app.py in project directory
   - Check for virtual environment (venv directory)
   - If venv not found, create it: `python -m venv venv`

3. **Install Dependencies** (if venv was just created):
   - First install tokenizers (avoids Rust compilation): `venv/Scripts/pip.exe install tokenizers>=0.20.0`
   - Install requirements: `venv/Scripts/pip.exe install -r requirements.txt`
   - Install CUDA dependencies for GPU: `venv/Scripts/pip.exe install nvidia-cudnn-cu12 nvidia-cublas-cu12`
   - Install PyTorch with CUDA support:
     - For RTX 50 series (Blackwell/sm_120), use nightly cu128:
       ```
       venv/Scripts/pip.exe uninstall torch torchaudio -y
       venv/Scripts/pip.exe install -U --pre torch torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
       ```
     - For RTX 40 series and earlier:
       ```
       venv/Scripts/pip.exe install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
       ```
   - Copy cuDNN/cuBLAS DLLs to project directory (required for Windows DLL search path):
     ```
     cp venv/Lib/site-packages/nvidia/cudnn/bin/*.dll ./
     cp venv/Lib/site-packages/nvidia/cublas/bin/*.dll ./
     ```
   - Report: "Dependencies installed"

4. **Patch pyannote/speechbrain for torchaudio 2.9+** (required for nightly cu128):
   ```bash
   # Patch pyannote io.py
   sed -i 's/-> torchaudio.AudioMetaData:/-> object:/g' venv/Lib/site-packages/pyannote/audio/core/io.py
   sed -i "s/torchaudio.list_audio_backends()/getattr(torchaudio, 'list_audio_backends', lambda: ['soundfile'])()/g" venv/Lib/site-packages/pyannote/audio/core/io.py
   sed -i 's/info : torchaudio.AudioMetaData/info : object/g' venv/Lib/site-packages/pyannote/audio/core/io.py
   
   # Patch pyannote mixins.py
   sed -i 's/from torchaudio import AudioMetaData/AudioMetaData = object  # Patched for torchaudio 2.9+/g' venv/Lib/site-packages/pyannote/audio/tasks/segmentation/mixins.py
   
   # Patch pyannote protocol.py
   sed -i "s/torchaudio.list_audio_backends()/getattr(torchaudio, 'list_audio_backends', lambda: ['soundfile'])()/g" venv/Lib/site-packages/pyannote/audio/utils/protocol.py
   
   # Patch speechbrain
   sed -i "s/torchaudio.list_audio_backends()/getattr(torchaudio, 'list_audio_backends', lambda: ['soundfile'])()/g" venv/Lib/site-packages/speechbrain/utils/torch_audio_backend.py
   ```

5. **Check FFmpeg**: Verify ffmpeg is available
   - Check if ffmpeg.exe exists in project directory
   - If NOT found, download and install:
     ```
     curl -L -o /tmp/ffmpeg.zip "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
     unzip -o /tmp/ffmpeg.zip -d /tmp/ffmpeg_extract
     cp /tmp/ffmpeg_extract/*/bin/*.exe {project_directory}/
     ```
   - Report: "FFmpeg installed to project directory"

6. **Start Server**: Launch the FastAPI application
   - Execute: `venv/Scripts/python.exe app.py`
   - Run in background (set run_in_background: true)
   - This starts the server on http://localhost:8000

7. **Verify Startup**: Wait 2-3 seconds, then check if process is running
   - Check port 8000 is now occupied: `netstat -ano | findstr :8000`
   - If running, report success
   - If not running, check background task output for errors

8. **Report Success**:
   ```
   Meeting Transcriber started successfully!
   - URL: http://localhost:8000
   - Process ID: {PID}
   - GPU Backend: {backend from server logs}
   - To stop: /stop-transcriber
   ```

## Error Handling

If port check fails:
- Report: "Port 8000 is already occupied by process {PID}"
- Suggest: "Run /stop-transcriber to stop existing server"

If server crashes with CUDA sm_120 error:
- This means RTX 50 series GPU needs PyTorch nightly cu128
- Install: `pip install -U --pre torch torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128`

If pyannote/speechbrain throws AudioMetaData or list_audio_backends errors:
- Apply the patches in step 4 above

## Requirements

- Python 3.8+ available (via pyenv-win)
- Port 8000 must be available
- FFmpeg will be auto-installed if missing
- cuDNN/cuBLAS will be installed for NVIDIA GPU support
- PyTorch nightly cu128 for RTX 50 series (Blackwell architecture)

## Speaker Diarization Setup

For diarization to work, the user must:
1. Set HuggingFace token via web UI Settings page (or HF_TOKEN in .env)
2. Accept pyannote model terms on HuggingFace:
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/segmentation-3.0
