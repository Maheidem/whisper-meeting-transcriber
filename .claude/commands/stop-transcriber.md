---
allowed-tools: Bash
description: Stop the Meeting Transcriber application running on port 8000
---

Stop the Meeting Transcriber web application by finding and terminating the process on port 8000.

## Workflow

1. **Find Process**: Look for process using port 8000
   - Execute: `netstat -ano | findstr :8000`
   - Parse output to find PID (last column of LISTENING row)
   - Store PID for next step

2. **Validate Process**: Check if process exists
   - If no PID found:
     - Report: "Meeting Transcriber is not running (no process on port 8000)"
     - Status: SUCCESS (nothing to stop)
     - STOP execution
   - If PID found:
     - Report: "Found process {PID} on port 8000"
     - Proceed to termination

3. **Terminate Process**: Kill the process
   - Execute: `taskkill //PID {PID} //F`
   - Note: Use double slashes for taskkill flags in Git Bash

4. **Verify Termination**: Confirm process stopped
   - Check if port 8000 is now free: `netstat -ano | findstr :8000`
   - If port is free (exit code 1 = no match):
     - Report: "Meeting Transcriber stopped successfully"
     - Status: SUCCESS
   - If port still occupied:
     - Report error and PID

5. **Final Report**:
   ```
   Meeting Transcriber stopped
   - Process {PID} terminated
   - Port 8000 is now available
   - To restart: /start-transcriber
   ```

## Error Handling

If multiple PIDs found on port 8000:
- Report: "Multiple processes found on port 8000: {PIDs}"
- Terminate all using taskkill
- Report: "Stopped all processes on port 8000"

If taskkill command fails:
- Report: "Failed to stop process {PID}"
- Suggest: "Try running manually in PowerShell: Stop-Process -Id {PID} -Force"
- Status: FAIL

## Platform Notes

- Uses `netstat -ano` to find process (Windows)
- Uses `taskkill //PID {PID} //F` to terminate (double slashes for Git Bash)
- Tested on Windows 11
