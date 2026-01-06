---
allowed-tools: Bash(lsof:*), Bash(kill:*)
description: Stop the Meeting Transcriber application running on port 8000
---

Stop the Meeting Transcriber web application by finding and terminating the process on port 8000.

## Workflow

1. **Find Process**: Look for process using port 8000
   - Execute: `lsof -ti:8000`
   - This returns the PID(s) of processes on port 8000
   - Store PID for next step

2. **Validate Process**: Check if process exists
   - If no PID found:
     - Report: "Meeting Transcriber is not running (no process on port 8000)"
     - Status: SUCCESS (nothing to stop)
     - STOP execution
   - If PID found:
     - Report: "Found process {PID} on port 8000"
     - Proceed to termination

3. **Terminate Process**: Kill the process gracefully
   - Execute: `kill {PID}` (SIGTERM - graceful shutdown)
   - Wait 2 seconds for graceful shutdown

4. **Verify Termination**: Confirm process stopped
   - Check if port 8000 is now free: `lsof -ti:8000`
   - If port is free:
     - Report: "Meeting Transcriber stopped successfully"
     - Status: SUCCESS
   - If port still occupied:
     - Force kill: `kill -9 {PID}` (SIGKILL)
     - Verify again
     - Report: "Meeting Transcriber force-stopped (was unresponsive)"

5. **Final Report**:
   ```
   Meeting Transcriber stopped
   - Process {PID} terminated
   - Port 8000 is now available
   - To restart: /project:start-transcriber
   ```

## Error Handling

If multiple PIDs found on port 8000:
- Report: "Multiple processes found on port 8000: {PIDs}"
- Terminate all: `kill {PID1} {PID2} ...`
- Report: "Stopped all processes on port 8000"

If kill command fails:
- Try force kill: `kill -9 {PID}`
- If still fails:
  - Report: "Failed to stop process {PID}"
  - Suggest: "You may need to stop it manually with: sudo kill -9 {PID}"
  - Status: FAIL

If permission denied:
- Report: "Permission denied when trying to kill process {PID}"
- Suggest: "Try running manually: kill {PID}"
- STOP execution

## Platform Notes

- Uses `lsof` (macOS/Linux standard tool)
- Uses `kill` with SIGTERM (15) then SIGKILL (9) if needed
- Tested on macOS (Darwin)
