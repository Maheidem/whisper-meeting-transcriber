#!/bin/bash

echo "🚀 Starting Whisper Meeting Transcriber Web UI..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check if Whisper service is running
echo "🔍 Checking Whisper service..."
if ! curl -s http://localhost:9000/docs > /dev/null; then
    echo "⚠️  Warning: Whisper service not detected at http://localhost:9000"
    echo "Please start the Whisper service with:"
    echo "docker run -d -p 9000:9000 --name whisper onerahmet/openai-whisper-asr-webservice:latest"
    echo ""
fi

# Start the web server
echo "🌐 Starting web server on http://localhost:8000"
echo "Press Ctrl+C to stop"
uvicorn app:app --reload --host 0.0.0.0 --port 8000