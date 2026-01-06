---
allowed-tools: Bash, Glob, Read
description: Restart the Meeting Transcriber (stop then start)
---

Restart the Meeting Transcriber web application by stopping the existing process and starting a fresh instance.

## Workflow

1. **Stop Existing Server**
   - Find process on port 8000: `netstat -ano | findstr :8000`
   - If found, terminate: `taskkill //PID {PID} //F`
   - If not found, report: "No existing server to stop"

2. **Start Fresh Server**
   - Verify port 8000 is free
   - Launch server: `venv/Scripts/python.exe app.py` (run in background)
   - Wait 2-3 seconds for startup

3. **Verify Restart**
   - Check port 8000 is now occupied
   - Report PID and URL

4. **Report Success**:
   ```
   Meeting Transcriber restarted successfully!
   - URL: http://localhost:8000
   - Process ID: {PID}
   - To stop: /stop-transcriber
   ```

## Error Handling

If stop fails:
- Report: "Failed to stop existing process {PID}"
- Try manual stop: `Stop-Process -Id {PID} -Force` in PowerShell
- STOP execution

If start fails:
- Report: "Failed to start server"
- Check background task output for errors
- Suggest: "Try /start-transcriber for detailed diagnostics"
- STOP execution

If port still occupied after stop:
- Report: "Port 8000 still in use after stop attempt"
- Show remaining PID
- STOP execution

## Notes

- Combines `/stop-transcriber` and `/start-transcriber` workflows
- Uses Windows commands (netstat, taskkill with // flags for Git Bash)
- Assumes venv and dependencies already set up (use /start-transcriber for first-time setup)
