---
allowed-tools: Bash(python:*), Bash(lsof:*), Bash(source:*), Read
description: Start the Meeting Transcriber web application on localhost:8000
---

Start the Meeting Transcriber FastAPI web application in the background using the project's virtual environment.

## Pre-flight Check

First, verify no process is already running on port 8000:

!lsof -ti:8000

## Workflow

1. **Check Port**: If port 8000 is occupied, report it and STOP
   - Report: "Port 8000 is already in use by process {PID}"
   - Suggest: "Run /project:stop-transcriber first"

2. **Validate Environment**: Confirm project setup
   - Check for existence of app.py in /Users/maheidem/Documents/dev/meeting-transcriber
   - Check for virtual environment (venv directory)
   - If app.py not found, report error and STOP
   - If venv not found, create it: `python -m venv venv`

3. **Install Dependencies** (if venv was just created):
   - Activate venv and install requirements
   - Execute: `source venv/bin/activate && pip install -r requirements.txt`
   - Report: "Dependencies installed"

4. **Start Server**: Launch the FastAPI application
   - Execute: `source /Users/maheidem/Documents/dev/meeting-transcriber/venv/bin/activate && python /Users/maheidem/Documents/dev/meeting-transcriber/app.py`
   - Run in background (set run_in_background: true)
   - This starts the server on http://localhost:8000

5. **Verify Startup**: Wait 2-3 seconds, then check if process is running
   - Check port 8000 is now occupied
   - If running, report success
   - If not running, report failure with suggestion to check logs

6. **Report Success**:
   ```
   Meeting Transcriber started successfully!
   - URL: http://localhost:8000
   - Process ID: {PID}
   - Virtual environment: venv/
   - To stop: /project:stop-transcriber
   ```

## Error Handling

If port check fails:
- Report: "Port 8000 is already occupied by process {PID}"
- Suggest: "Run /project:stop-transcriber to stop existing server"
- STOP execution

If app.py not found:
- Report: "app.py not found in /Users/maheidem/Documents/dev/meeting-transcriber"
- Suggest: "Verify you're in the correct project directory"
- STOP execution

If venv creation fails:
- Report: "Failed to create virtual environment"
- Suggest: "Create manually: python -m venv venv"
- STOP execution

If dependency installation fails:
- Report: "Failed to install dependencies"
- Show error output
- Suggest: "Install manually: source venv/bin/activate && pip install -r requirements.txt"
- STOP execution

If server fails to start:
- Report: "Server failed to start"
- Suggest: "Check logs/transcriber.log for errors or run manually: source venv/bin/activate && python app.py"
- STOP execution

## Requirements

- Project directory: /Users/maheidem/Documents/dev/meeting-transcriber
- Python 3.8+ available
- Port 8000 must be available
- FFmpeg must be installed (brew install ffmpeg)
- Virtual environment will be created automatically if missing
