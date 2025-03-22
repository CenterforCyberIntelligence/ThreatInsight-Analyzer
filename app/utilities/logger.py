import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional

# Import configuration (avoid circular imports by importing here)
try:
    from app.config.config import Config
    logs_dir = Config.LOG_DIR
    log_level = Config.get_log_level()
    log_format = Config.LOG_FORMAT
    max_bytes = Config.LOG_MAX_SIZE
    backup_count = Config.LOG_BACKUP_COUNT
except (ImportError, AttributeError):
    # Fallback values if Config is not available
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    log_level = logging.INFO
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    max_bytes = 10 * 1024 * 1024  # 10MB
    backup_count = 5

# Create logs directory if it doesn't exist
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Configure the logger
logger = logging.getLogger('article_analyzer')
logger.setLevel(log_level)

# Create a formatter
formatter = logging.Formatter(log_format)

# Create a file handler for info logs
info_log_path = os.path.join(logs_dir, 'info.log')
info_handler = RotatingFileHandler(info_log_path, maxBytes=max_bytes, backupCount=backup_count)
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(formatter)
logger.addHandler(info_handler)

# Create a file handler for error logs
error_log_path = os.path.join(logs_dir, 'error.log')
error_handler = RotatingFileHandler(error_log_path, maxBytes=max_bytes, backupCount=backup_count)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)
logger.addHandler(error_handler)

# Create a file handler for debug logs if DEBUG level is enabled
if log_level <= logging.DEBUG:
    debug_log_path = os.path.join(logs_dir, 'debug.log')
    debug_handler = RotatingFileHandler(debug_log_path, maxBytes=max_bytes, backupCount=backup_count)
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)
    logger.addHandler(debug_handler)

# Create a stream handler for console output
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(log_level)

# Create a custom formatter for the console (with colors)
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',  # Blue
        'INFO': '\033[94m',   # Blue
        'WARNING': '\033[93m', # Yellow
        'ERROR': '\033[91m',  # Red
        'CRITICAL': '\033[91m\033[1m'  # Bold Red
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_message = super().format(record)
        color = self.COLORS.get(record.levelname, self.RESET)
        return f"{color}{log_message}{self.RESET}"

console_formatter = ColoredFormatter(log_format)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Log the logger initialization
logger.info(f"Logger initialized at level {logging.getLevelName(log_level)}")
logger.info(f"Log files will be stored in {logs_dir}")

def print_status(message: str, is_error: bool = False) -> None:
    """
    Log status messages with timestamps.
    
    Args:
        message: The message to log
        is_error: Whether this is an error message
    """
    if is_error:
        logger.error(message)
    else:
        logger.info(message)

# Add dedicated functions for different log levels
def debug(message: str) -> None:
    """Log a debug message."""
    logger.debug(message)

def info(message: str) -> None:
    """Log an info message."""
    logger.info(message)

def warning(message: str) -> None:
    """Log a warning message."""
    logger.warning(message)

def error(message: str) -> None:
    """Log an error message."""
    logger.error(message)

def critical(message: str) -> None:
    """Log a critical message."""
    logger.critical(message) 