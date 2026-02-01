import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from app.core.config import settings
import colorama
from colorama import Fore, Style, Back

# Initialize colorama
colorama.init(autoreset=True)

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Log file path
LOG_FILE = os.path.join(LOGS_DIR, "app.log")

# Configure formatter
# Standard formatter for files
FILE_FORMATTER = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

class ColoredFormatter(logging.Formatter):
    """
    Custom formatter to add colors to log messages based on level.
    """
    # Color mapping
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        # Create a copy to not affect other handlers
        # We want to color the levelname and potentially the message
        log_color = self.COLORS.get(record.levelno, Fore.WHITE)
        
        # Save original values
        original_levelname = record.levelname
        original_msg = record.msg
        
        # Colorize
        record.levelname = f"{log_color}{original_levelname}{Style.RESET_ALL}"
        
        # We can also colorize the whole line or just parts. 
        # Typically coloring the level is enough, but coloring the message helps distinction.
        # Let's keep the message color neutral or same as level if preferred.
        # For readability, let's color the whole message line prefix? 
        # Actually, standard practice is usually: TIMESTAMP - NAME - [COLOR]LEVEL[RESET] - MESSAGE
        
        # Let's try to match the format: 
        # %(asctime)s - %(name)s - %(levelname)s - %(message)s
        
        # It's easier to format the whole string manually or inject colors into the args if using a standard formatter structure becomes complex with just attribute modification.
        # But modifying the record attributes is the standard way.
        
        # Let's just create the formatted string manually to ensure control
        # Or simply call super().format(record) after modifying levelname
        
        # Issue: modifying record.levelname affects other handlers if sharing the same record instance?
        # Logging docs say "The record argument is the log record to be formatted."
        # Usually handlers emit sequentially. If we modify record.levelname, it might persist for subsequent handlers if not careful.
        # However, we are creating a specific formatter for the StreamHandler.
        
        # To be safe, we can leave record.levelname alone and use a custom format string in the init
        # or do this:
        
        levelname_color = f"{log_color}{record.levelname}{Style.RESET_ALL}"
        message_color = f"{log_color}{record.msg}{Style.RESET_ALL}" if record.levelno >= logging.ERROR else record.msg
        
        # Construct the log message
        # We need to format the time first
        record.asctime = self.formatTime(record, self.datefmt)
        
        s = f"{record.asctime} - {Fore.MAGENTA}{record.name}{Style.RESET_ALL} - {levelname_color} - {message_color}"
        
        # Note: formatting exception info is separate if we were doing full override, 
        # but let's keep it simple.
        # If there's exception info, format it.
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + record.exc_text
            
        return s

def setup_logger():
    """
    Setup the root logger to write to file and console.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    # Avoid adding handlers multiple times if they already exist
    if not root_logger.handlers:
        # File Handler (writes to file) - Plain text
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(FILE_FORMATTER)
        file_handler.setLevel(settings.LOG_LEVEL)
        root_logger.addHandler(file_handler)

        # Stream Handler (writes to console) - Colored
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(ColoredFormatter())
        stream_handler.setLevel(settings.LOG_LEVEL)
        root_logger.addHandler(stream_handler)

    return logging.getLogger("ai_trader")

# Configure root logger immediately on import
logger = setup_logger()
