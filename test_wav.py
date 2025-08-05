#!/usr/bin/env python3
"""Test with extracted WAV file"""

import requests
import os

wav_file = "test_60sec.wav"

if not os.path.exists(wav_file):
    print(f"File not found: {wav_file}")
    exit(1)

file_size = os.path.getsize(wav_file)
print(f"Testing with: {wav_file}")
print(f"File size: {file_size:,} bytes ({file_size / (1024*1024):.1f} MB)")

url = "http://localhost:9000/asr"

print("\nSending request...")
try:
    with open(wav_file, 'rb') as f:
        files = {'audio_file': f}
        response = requests.post(url, files=files, timeout=60)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✓ SUCCESS!")
            print(f"Response length: {len(response.text)} chars")
            print(f"\nTranscription:\n{response.text}")
            
            with open("transcription_result.txt", "w") as out:
                out.write(response.text)
            print("\nSaved to: transcription_result.txt")
        else:
            print(f"✗ Error: {response.text}")
            
except Exception as e:
    print(f"Error: {e}")