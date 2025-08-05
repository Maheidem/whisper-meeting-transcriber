#!/usr/bin/env python3
"""
Utility to stop any running jobs in the Whisper container
"""

import subprocess
import sys

def stop_whisper_jobs():
    """Stop any running transcription jobs in the Whisper container"""
    try:
        # Get the container ID
        result = subprocess.run(['docker', 'ps', '--filter', 'name=whisper', '-q'], 
                              capture_output=True, text=True)
        container_id = result.stdout.strip()
        
        if not container_id:
            print("Whisper container not found")
            return False
        
        print(f"Found Whisper container: {container_id}")
        
        # Send SIGTERM to all python processes in the container
        # This will gracefully stop any running transcription
        cmd = ['docker', 'exec', container_id, 'pkill', '-TERM', '-f', 'python']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Successfully sent termination signal to Whisper processes")
            return True
        elif result.returncode == 1:
            print("No active Whisper processes found")
            return True
        else:
            print(f"Error stopping Whisper processes: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    stop_whisper_jobs()