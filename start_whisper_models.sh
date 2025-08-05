#!/bin/bash

echo "🚀 Starting Whisper ASR Model Services..."

# Function to check if container is already running
check_container() {
    docker ps -q -f name=$1
}

# Function to stop and remove existing container
cleanup_container() {
    if [ "$(check_container $1)" ]; then
        echo "Stopping existing $1 container..."
        docker stop $1
        docker rm $1
    fi
}

# Start Tiny model (fastest)
echo "Starting Whisper Tiny model on port 9000..."
cleanup_container whisper-tiny
docker run -d -p 9000:9000 --name whisper-tiny \
    -e ASR_MODEL=tiny \
    -e ASR_ENGINE=openai_whisper \
    onerahmet/openai-whisper-asr-webservice:latest

# Start Base model (balanced)
echo "Starting Whisper Base model on port 9001..."
cleanup_container whisper-base
docker run -d -p 9001:9000 --name whisper-base \
    -e ASR_MODEL=base \
    -e ASR_ENGINE=openai_whisper \
    onerahmet/openai-whisper-asr-webservice:latest

# Uncomment to start additional models as needed
# echo "Starting Whisper Small model on port 9002..."
# cleanup_container whisper-small
# docker run -d -p 9002:9000 --name whisper-small \
#     -e ASR_MODEL=small \
#     -e ASR_ENGINE=openai_whisper \
#     onerahmet/openai-whisper-asr-webservice:latest

# For Faster Whisper (more efficient implementation)
echo "Starting Faster Whisper Tiny model on port 9010..."
cleanup_container whisper-tiny-faster
docker run -d -p 9010:9000 --name whisper-tiny-faster \
    -e ASR_MODEL=tiny \
    -e ASR_ENGINE=faster_whisper \
    onerahmet/openai-whisper-asr-webservice:latest

echo ""
echo "✅ Whisper services started!"
echo ""
echo "Available models:"
echo "  - Tiny (OpenAI):    http://localhost:9000"
echo "  - Base (OpenAI):    http://localhost:9001"
echo "  - Tiny (Faster):    http://localhost:9010"
echo ""
echo "To stop all services, run: ./stop_whisper_models.sh"