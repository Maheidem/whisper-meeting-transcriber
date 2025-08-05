#!/usr/bin/env python3
"""Direct test with the provided file"""

import requests
import os
import time

file_path = "/Users/maheidem/Downloads/_W Empyrean_ Demo for the team  - 2025_06_12 09_54 CEST - Recording.mp4"

# Check file
if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit(1)

file_size = os.path.getsize(file_path)
print(f"Testing with file: {os.path.basename(file_path)}")
print(f"File size: {file_size:,} bytes ({file_size / (1024*1024):.1f} MB)")

url = "http://localhost:9000/asr"

# Test 1: Minimal request (like curl)
print("\nTest 1: Minimal request (no extra parameters)...")
try:
    with open(file_path, 'rb') as f:
        files = {'audio_file': f}
        
        start_time = time.time()
        print("Sending request...")
        response = requests.post(url, files=files, timeout=600)
        elapsed = time.time() - start_time
        
        print(f"Status: {response.status_code}")
        print(f"Time taken: {elapsed:.1f} seconds")
        
        if response.status_code == 200:
            print(f"Success! Response length: {len(response.text)} chars")
            print(f"First 200 chars: {response.text[:200]}...")
            
            # Save to file
            with open("transcription_result.txt", "w") as out:
                out.write(response.text)
            print("Saved to: transcription_result.txt")
        else:
            print(f"Error response: {response.text}")
            
except Exception as e:
    print(f"Error: {e}")

# Test 2: With explicit filename
print("\n\nTest 2: With explicit filename in multipart...")
try:
    with open(file_path, 'rb') as f:
        filename = os.path.basename(file_path)
        files = {'audio_file': (filename, f)}
        
        start_time = time.time()
        print("Sending request...")
        response = requests.post(url, files=files, timeout=600)
        elapsed = time.time() - start_time
        
        print(f"Status: {response.status_code}")
        print(f"Time taken: {elapsed:.1f} seconds")
        
        if response.status_code == 200:
            print("Success!")
        else:
            print(f"Error: {response.text}")
            
except Exception as e:
    print(f"Error: {e}")