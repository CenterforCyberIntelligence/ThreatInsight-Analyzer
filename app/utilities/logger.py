import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional, Any
import traceback
from flask import Request

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

# Functions needed for tests
def setup_logging(
    logger_name: str, 
    log_file: str, 
    level: Optional[int] = None, 
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    
    Args:
        logger_name: Name of the logger
        log_file: Path to log file
        level: Log level (defaults to INFO or environment variable LOG_LEVEL)
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance
    """
    # Create logger
    custom_logger = logging.getLogger(logger_name)
    
    # Set log level from environment variable or default to INFO
    if level is None:
        log_level_name = os.environ.get('LOG_LEVEL', 'INFO').upper()
        level = getattr(logging, log_level_name, logging.INFO)
    
    custom_logger.setLevel(level)
    
    # Create formatter
    custom_format = os.environ.get(
        'LOG_FORMAT', 
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    custom_formatter = logging.Formatter(custom_format)
    
    # Create directory for log file if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Add file handler with rotation
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=max_bytes, 
        backupCount=backup_count
    )
    file_handler.setFormatter(custom_formatter)
    custom_logger.addHandler(file_handler)
    
    # Add console handler for development
    if os.environ.get('FLASK_ENV') == 'development':
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(custom_formatter)
        custom_logger.addHandler(console_handler)
    
    return custom_logger

def get_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for a module.
    
    Args:
        module_name: Name of the module
        
    Returns:
        Logger instance
    """
    logger_name = f"app.{module_name}"
    return logging.getLogger(logger_name)

def log_request(req: Request) -> None:
    """
    Log an incoming HTTP request.
    
    Args:
        req: Flask request object
    """
    req_logger = get_logger('requests')
    req_logger.info(
        f"Request: {req.method} {req.path} - "
        f"IP: {req.remote_addr} - "
        f"User-Agent: {req.user_agent.string}"
    )

def log_exception(exception: Exception, module: str) -> None:
    """
    Log an exception with traceback.
    
    Args:
        exception: Exception object
        module: Module name where the exception occurred
    """
    exc_logger = get_logger(module)
    
    # Get exception details
    exc_type = type(exception).__name__
    exc_msg = str(exception)
    exc_traceback = traceback.format_exc()
    
    # Log the exception
    exc_logger.exception(
        f"Exception occurred in {module}: {exc_type}: {exc_msg}\n"
        f"Traceback:\n{exc_traceback}"
    ) 