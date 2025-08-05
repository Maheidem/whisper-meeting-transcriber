#!/bin/bash

echo "🛑 Stopping Whisper ASR Model Services..."

# Stop and remove containers
for container in whisper-tiny whisper-base whisper-small whisper-medium whisper-large \
                whisper-tiny-faster whisper-base-faster \
                whisper-tiny-whisperx whisper-base-whisperx; do
    if docker ps -q -f name=$container > /dev/null 2>&1; then
        echo "Stopping $container..."
        docker stop $container 2>/dev/null
        docker rm $container 2>/dev/null
    fi
done

echo "✅ All Whisper services stopped!"