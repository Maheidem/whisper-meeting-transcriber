#!/usr/bin/env python3
"""Test minimal transcription request"""

import requests
import sys
import os

def test_transcription(file_path):
    url = "http://localhost:9000/asr"
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    file_size = os.path.getsize(file_path)
    print(f"Testing with file: {file_path}")
    print(f"File size: {file_size:,} bytes")
    
    # Test different parameter combinations
    test_cases = [
        {"task": "transcribe", "output": "txt"},
        {"task": "transcribe"},
        {"output": "txt"},
        {}
    ]
    
    for i, params in enumerate(test_cases):
        print(f"\nTest case {i+1}: {params}")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'audio_file': (os.path.basename(file_path), f)}
                response = requests.post(url, files=files, data=params, timeout=30)
                
                print(f"Status: {response.status_code}")
                if response.status_code != 200:
                    print(f"Response: {response.text[:500]}")
                else:
                    print(f"Success! Response length: {len(response.text)} chars")
                    print(f"First 200 chars: {response.text[:200]}")
                    break
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_transcription(sys.argv[1])
    else:
        print("Usage: python3 test_transcription.py <audio_file>")
        print("\nTrying to create a test audio file...")
        
        # Create a simple test audio file using system sound
        test_file = "test_audio.wav"
        os.system(f"say -o {test_file} 'This is a test audio file'")
        
        if os.path.exists(test_file):
            print(f"Created test file: {test_file}")
            test_transcription(test_file)
        else:
            print("Could not create test audio file")