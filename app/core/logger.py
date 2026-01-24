import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from app.core.config import settings

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Log file path
LOG_FILE = os.path.join(LOGS_DIR, "app.log")

# Configure formatter
FORMATTER = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def setup_logger():
    """
    Setup the root logger to write to file and console.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    # Avoid adding handlers multiple times if they already exist
    if not root_logger.handlers:
        # File Handler (writes to file)
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(FORMATTER)
        file_handler.setLevel(settings.LOG_LEVEL)
        root_logger.addHandler(file_handler)

        # Stream Handler (writes to console)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(FORMATTER)
        stream_handler.setLevel(settings.LOG_LEVEL)
        root_logger.addHandler(stream_handler)

    return logging.getLogger("ai_trader")

# Configure root logger immediately on import
logger = setup_logger()
