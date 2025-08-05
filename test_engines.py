#!/usr/bin/env python3
"""Test different Whisper engines"""

import requests
import os

file_path = "/Users/maheidem/Downloads/_W Empyrean_ Demo for the team  - 2025_06_12 09_54 CEST - Recording.mp4"

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit(1)

url = "http://localhost:9000/asr"

# List of engines to try
engines = [
    "openai_whisper",
    "faster_whisper", 
    "whisperx",
    None  # Default
]

print(f"Testing file: {os.path.basename(file_path)}")
print(f"File size: {os.path.getsize(file_path):,} bytes\n")

for engine in engines:
    print(f"\nTesting engine: {engine if engine else 'default'}")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'audio_file': f}
            data = {}
            
            if engine:
                data['engine'] = engine
            
            print(f"Parameters: {data}")
            response = requests.post(url, files=files, data=data, timeout=300)
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✓ SUCCESS! Response length: {len(response.text)} chars")
                print(f"First 100 chars: {response.text[:100]}...")
                
                # Save successful result
                with open(f"result_{engine or 'default'}.txt", "w") as out:
                    out.write(response.text)
                print(f"Saved to: result_{engine or 'default'}.txt")
                
                # If one works, we can stop
                break
            else:
                print(f"✗ Error: {response.text}")
                
    except requests.exceptions.Timeout:
        print("✗ Request timed out")
    except Exception as e:
        print(f"✗ Error: {e}")