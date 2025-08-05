#!/usr/bin/env python3
"""
Check what processes are running in the Whisper container
"""

import subprocess
import sys

def check_whisper_processes():
    """Check running processes in Whisper container"""
    try:
        # Get container ID
        result = subprocess.run(['docker', 'ps', '--filter', 'name=whisper', '-q'], 
                              capture_output=True, text=True)
        container_id = result.stdout.strip()
        
        if not container_id:
            print("Whisper container not found")
            return
        
        print(f"Whisper container ID: {container_id}")
        print("\nRunning processes:")
        print("-" * 80)
        
        # List all processes
        cmd = ['docker', 'exec', container_id, 'ps', 'aux']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"Error: {result.stderr}")
            
        # Check CPU usage
        print("\nTop CPU consuming processes:")
        print("-" * 80)
        cmd = ['docker', 'exec', container_id, 'top', '-b', '-n', '1']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Show first 20 lines of top output
            lines = result.stdout.split('\n')[:20]
            print('\n'.join(lines))
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_whisper_processes()