"""
Configuration - Single source of truth for all settings.
"""
import os
import platform
from pathlib import Path

from dotenv import load_dotenv

# Paths
BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR / ".env"

# Load .env file if it exists
load_dotenv(ENV_FILE)
UPLOAD_DIR = BASE_DIR / "uploads"
RESULTS_DIR = BASE_DIR / "results"
MODELS_DIR = BASE_DIR / "models"

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))


# === GPU Detection ===
def detect_gpu_backend():
    """
    Auto-detect best available GPU backend.
    Returns: 'mlx' (Mac), 'cuda' (Windows/Linux), or 'cpu'
    """
    # Check for Mac Apple Silicon → use MLX
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        try:
            import mlx.core
            return "mlx"
        except ImportError:
            pass  # MLX not installed

    # Check for CUDA (Windows/Linux with NVIDIA GPU)
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass

    # Check if faster-whisper CUDA works
    try:
        import ctranslate2
        if "cuda" in ctranslate2.get_supported_compute_types("cuda"):
            return "cuda"
    except:
        pass

    return "cpu"


def get_gpu_info():
    """Get human-readable GPU info for display."""
    backend = detect_gpu_backend()

    if backend == "mlx":
        return {"backend": "mlx", "name": "Apple Silicon (MLX)", "available": True}
    elif backend == "cuda":
        try:
            import torch
            gpu_name = torch.cuda.get_device_name(0)
            return {"backend": "cuda", "name": f"NVIDIA {gpu_name}", "available": True}
        except:
            return {"backend": "cuda", "name": "NVIDIA CUDA", "available": True}
    else:
        return {"backend": "cpu", "name": "CPU (no GPU detected)", "available": False}


# Whisper Settings
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "base")
GPU_BACKEND = detect_gpu_backend()  # Auto-detected: mlx, cuda, or cpu
DEVICE = os.getenv("DEVICE", "auto")  # Override: auto, cpu, cuda, mlx
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "float16" if GPU_BACKEND != "cpu" else "int8")

# HuggingFace token for speaker diarization (WhisperX/PyAnnote)
HF_TOKEN = os.getenv("HF_TOKEN", "")


def is_hf_token_configured() -> bool:
    """Check if HuggingFace token is set."""
    return bool(HF_TOKEN and len(HF_TOKEN) > 0)


def reload_env():
    """Reload .env file to pick up changes."""
    global HF_TOKEN
    load_dotenv(ENV_FILE, override=True)
    HF_TOKEN = os.getenv("HF_TOKEN", "")

# Available models (served via /models endpoint)
AVAILABLE_MODELS = {
    "tiny": {"name": "Tiny", "description": "Fastest, lowest accuracy (~1GB RAM)", "supports_diarization": True},
    "base": {"name": "Base", "description": "Good balance of speed/accuracy (~1GB RAM)", "supports_diarization": True},
    "small": {"name": "Small", "description": "Better accuracy, slower (~2GB RAM)", "supports_diarization": True},
    "medium": {"name": "Medium", "description": "High accuracy, requires more RAM (~5GB RAM)", "supports_diarization": True},
    "large-v3": {"name": "Large V3", "description": "Best accuracy, slow (~10GB RAM)", "supports_diarization": True},
}

# Output formats
OUTPUT_FORMATS = ["txt", "srt", "vtt", "json", "tsv"]

# Supported languages (Whisper supports 99+ languages)
# Using ISO 639-1 codes - "auto" for automatic detection
SUPPORTED_LANGUAGES = {
    "auto": "Auto-detect",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "ru": "Russian",
    "uk": "Ukrainian",
    "ja": "Japanese",
    "zh": "Chinese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "fi": "Finnish",
    "cs": "Czech",
    "sk": "Slovak",
    "ro": "Romanian",
    "hu": "Hungarian",
    "el": "Greek",
    "he": "Hebrew",
    "bg": "Bulgarian",
    "hr": "Croatian",
    "sr": "Serbian",
    "sl": "Slovenian",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "et": "Estonian",
    "ca": "Catalan",
    "gl": "Galician",
    "eu": "Basque",
    "cy": "Welsh",
    "af": "Afrikaans",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "ml": "Malayalam",
    "bn": "Bengali",
    "ur": "Urdu",
    "fa": "Persian",
}
DEFAULT_LANGUAGE = "auto"

# Limits
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "500"))
TRANSCRIPTION_TIMEOUT = int(os.getenv("TRANSCRIPTION_TIMEOUT", "3600"))  # 1 hour

# Supported file types
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}
SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}
SUPPORTED_EXTENSIONS = SUPPORTED_VIDEO_EXTENSIONS | SUPPORTED_AUDIO_EXTENSIONS
