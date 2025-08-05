#!/bin/bash

# Test different parameter combinations with curl
echo "Testing Whisper ASR endpoint with different parameters..."

# First, let's see what the API expects
echo -e "\n1. Getting API documentation..."
curl -s http://localhost:9000/openapi.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
asr = data.get('paths', {}).get('/asr', {}).get('post', {})
params = asr.get('requestBody', {}).get('content', {}).get('multipart/form-data', {}).get('schema', {}).get('properties', {})
print('ASR Parameters:')
for name, spec in params.items():
    print(f'  - {name}: {spec}')
"

# Create a small test audio file
echo -e "\n2. Creating test audio file..."
# Use macOS say command to create a test file
say -o test_audio.aiff "This is a test"
ffmpeg -i test_audio.aiff -ac 1 -ar 16000 test_audio.wav -y 2>/dev/null

if [ -f test_audio.wav ]; then
    echo "Test file created: test_audio.wav"
    
    # Test with different engines
    echo -e "\n3. Testing with different parameters..."
    
    # Test 1: Minimal
    echo -e "\nTest 1: Minimal request"
    curl -X POST http://localhost:9000/asr \
      -F "audio_file=@test_audio.wav" \
      -w "\nStatus: %{http_code}\n"
    
    # Test 2: With task parameter
    echo -e "\n\nTest 2: With task=transcribe"
    curl -X POST http://localhost:9000/asr \
      -F "audio_file=@test_audio.wav" \
      -F "task=transcribe" \
      -w "\nStatus: %{http_code}\n"
    
    # Test 3: With engine parameter
    echo -e "\n\nTest 3: With engine=faster_whisper"
    curl -X POST http://localhost:9000/asr \
      -F "audio_file=@test_audio.wav" \
      -F "engine=faster_whisper" \
      -F "task=transcribe" \
      -w "\nStatus: %{http_code}\n"
    
    # Clean up
    rm -f test_audio.aiff test_audio.wav
else
    echo "Failed to create test audio file"
fi