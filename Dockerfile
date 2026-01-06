# Meeting Transcriber - Single Container Deployment
# Replaces 9 containers with 1!

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config.py transcriber.py app.py ./
COPY templates/ ./templates/
COPY static/ ./static/

# Create directories
RUN mkdir -p uploads results models

# Pre-download default model (optional, speeds up first request)
# Uncomment if you want model baked into image:
# RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu')"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
