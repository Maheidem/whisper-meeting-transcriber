"""
Logging Configuration - Structured logging for Meeting Transcriber.

Provides consistent, grep-able log output for debugging with agentic tools.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

# Log directory
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log file path
LOG_FILE = LOG_DIR / "transcriber.log"

# Custom formatter for structured, grep-able output
class StructuredFormatter(logging.Formatter):
    """Format logs as: [timestamp] [LEVEL] [COMPONENT] message"""

    def format(self, record: logging.LogRecord) -> str:
        # Get component from logger name (e.g., "transcriber.model" -> "MODEL")
        component = record.name.upper().replace(".", "_")
        if component == "ROOT":
            component = "MAIN"

        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        # Format the base message
        message = record.getMessage()

        # Add exception info if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            message = f"{message}\n{exc_text}"

        return f"[{timestamp}] [{record.levelname}] [{component}] {message}"


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for a component.

    Args:
        name: Component name (e.g., "transcriber", "app", "websocket")

    Returns:
        Configured logger instance

    Example:
        logger = get_logger("transcriber")
        logger.info("Loading model: base")
        # Output: [2025-12-22 10:15:30] [INFO] [TRANSCRIBER] Loading model: base
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Console handler - INFO and above
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(StructuredFormatter())

        # File handler - DEBUG and above, rotating
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StructuredFormatter())

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        # Prevent propagation to root logger (avoid duplicate logs)
        logger.propagate = False

    return logger


def configure_uvicorn_logging():
    """Configure uvicorn to use our logging format."""
    # Get uvicorn loggers
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_error = logging.getLogger("uvicorn.error")

    formatter = StructuredFormatter()

    for uv_logger in [uvicorn_logger, uvicorn_access, uvicorn_error]:
        uv_logger.handlers = []

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        uv_logger.addHandler(console_handler)

        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        uv_logger.addHandler(file_handler)


# Convenience function for timing operations
class Timer:
    """Context manager for timing operations."""

    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"{self.operation} started")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        if exc_type:
            self.logger.error(f"{self.operation} failed after {duration:.2f}s: {exc_val}")
        else:
            self.logger.info(f"{self.operation} completed in {duration:.2f}s")
        return False
