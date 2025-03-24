"""
Logging Utilities Module
=======================

This module provides a centralized logging system for the application with the following features:
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Log file rotation to prevent excessive disk usage
- Separate log files for different log levels (info, error, debug)
- Colored console output for easier monitoring during development
- Structured logging capabilities for machine-readable log entries
- Performance monitoring for application startup phases
- Environment-aware logging configuration
- Helper functions for common logging patterns

The logging system is designed to be used throughout the application to provide 
consistent logging behavior and facilitate troubleshooting in development and production.
"""
import os
import sys
import logging
import json
import time
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional, Any, Dict, Union, Callable
import traceback
from flask import Request

# Global dictionary to store startup timings
_startup_phases = {}
_startup_phase_start_times = {}
_startup_current_phase = None

# Check if this is a reloader process (to avoid duplicate console output)
_is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') != 'true'

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
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    max_bytes = 10 * 1024 * 1024  # 10MB
    backup_count = 5

# Create logs directory if it doesn't exist
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Configure the logger
logger = logging.getLogger('article_analyzer')
logger.setLevel(log_level)

# Clear any existing handlers to prevent duplicates
if logger.handlers:
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

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
# In debug mode with reloader, only show console output in the worker process
if not _is_reloader_process:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Create a custom formatter for the console (with colors)
    class ColoredFormatter(logging.Formatter):
        """
        Custom log formatter that adds color codes to log level names in console output.
        
        This makes it easier to visually distinguish between different log levels when
        viewing logs in the console during development.
        """
        COLORS = {
            'DEBUG': '\033[94m',  # Blue
            'INFO': '\033[94m',   # Blue
            'WARNING': '\033[93m', # Yellow
            'ERROR': '\033[91m',  # Red
            'CRITICAL': '\033[91m\033[1m'  # Bold Red
        }
        RESET = '\033[0m'
        
        def format(self, record):
            """
            Format a log record with color codes for the console.
            
            Args:
                record: Log record to format
                
            Returns:
                Formatted log message with color codes
            """
            log_message = super().format(record)
            color = self.COLORS.get(record.levelname, self.RESET)
            return f"{color}{log_message}{self.RESET}"

    console_formatter = ColoredFormatter(log_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

# Log the logger initialization only in the worker process
if not _is_reloader_process:
    logger.info(f"Logger initialized at level {logging.getLevelName(log_level)}")
    logger.info(f"Log files will be stored in {logs_dir}")
else:
    # Minimal logging for reloader process
    logger.debug(f"Reloader process logger initialized at level {logging.getLevelName(log_level)}")

def start_phase(phase_name: str) -> None:
    """
    Start timing a startup phase.
    
    This function marks the beginning of a specific application startup phase
    and logs its start. It's used to track performance metrics during application
    initialization.
    
    Args:
        phase_name: Name of the startup phase to begin timing
    """
    global _startup_current_phase, _startup_phase_start_times
    
    # In reloader process, only log API_SERVER phase at debug level
    if _is_reloader_process:
        if phase_name == "API_SERVER":
            logger.debug(f"=== STARTING PHASE: {phase_name} (reloader process) ===")
        return
    
    _startup_current_phase = phase_name
    _startup_phase_start_times[phase_name] = time.time()
    
    logger.info(f"=== STARTING PHASE: {phase_name} ===")

def end_phase(phase_name: str = None) -> None:
    """
    End timing a startup phase and record the duration.
    
    This function marks the end of a specific application startup phase,
    calculates its duration, and logs the completion. It's used together
    with start_phase() to measure initialization performance.
    
    Args:
        phase_name: Name of the startup phase to end (defaults to the current phase)
    """
    global _startup_current_phase, _startup_phases, _startup_phase_start_times
    
    # Skip timing in reloader process
    if _is_reloader_process:
        return
    
    if phase_name is None:
        phase_name = _startup_current_phase
    
    if phase_name in _startup_phase_start_times:
        duration = time.time() - _startup_phase_start_times[phase_name]
        _startup_phases[phase_name] = duration
        logger.info(f"=== COMPLETED PHASE: {phase_name} in {duration:.2f}s ===")
    else:
        logger.warning(f"Attempted to end unknown phase: {phase_name}")

def get_startup_timings() -> Dict[str, float]:
    """
    Get the timing information for all startup phases.
    
    Retrieves the duration of all completed application startup phases.
    This can be used to analyze performance bottlenecks during initialization.
    
    Returns:
        Dictionary mapping phase names to their durations in seconds
    """
    return _startup_phases

def structured_log(level: str, message: str, **kwargs) -> None:
    """
    Create structured log entry with additional context.
    
    This function creates a JSON-formatted log entry that includes the message
    and any additional context data provided. This is useful for machine-readable
    logs that can be parsed and analyzed by log management systems.
    
    Args:
        level: Log level ('debug', 'info', 'warning', 'error', 'critical')
        message: Main log message
        **kwargs: Additional context data to include in the structured log
    """
    # Add timestamp
    context = {
        'timestamp': datetime.utcnow().isoformat(),
        'message': message
    }
    
    # Add any additional context
    if kwargs:
        context.update(kwargs)
    
    # Create structured message
    if level == 'debug':
        logger.debug(json.dumps(context))
    elif level == 'info':
        logger.info(json.dumps(context))
    elif level == 'warning':
        logger.warning(json.dumps(context))
    elif level == 'error':
        logger.error(json.dumps(context))
    elif level == 'critical':
        logger.critical(json.dumps(context))

def print_status(message: str, is_error: bool = False) -> None:
    """
    Log status messages with timestamps.
    
    A convenience function for logging status messages during application operations,
    automatically choosing the appropriate log level based on whether the message
    represents an error condition.
    
    Args:
        message: The message to log
        is_error: Whether this is an error message (determines log level)
    """
    if is_error:
        logger.error(message)
    else:
        logger.info(message)

# Add dedicated functions for different log levels
def debug(message: str, **kwargs) -> None:
    """
    Log a debug message.
    
    Logs a message at DEBUG level, optionally with structured context data.
    Debug messages are typically used for detailed troubleshooting information.
    
    Args:
        message: The debug message to log
        **kwargs: Optional context data for structured logging
    """
    if kwargs:
        structured_log('debug', message, **kwargs)
    else:
        logger.debug(message)

def info(message: str, **kwargs) -> None:
    """
    Log an info message.
    
    Logs a message at INFO level, optionally with structured context data.
    Info messages are typically used for general operational information.
    
    Args:
        message: The info message to log
        **kwargs: Optional context data for structured logging
    """
    if kwargs:
        structured_log('info', message, **kwargs)
    else:
        logger.info(message)

def warning(message: str, **kwargs) -> None:
    """
    Log a warning message.
    
    Logs a message at WARNING level, optionally with structured context data.
    Warning messages indicate potential issues that don't prevent operation.
    
    Args:
        message: The warning message to log
        **kwargs: Optional context data for structured logging
    """
    if kwargs:
        structured_log('warning', message, **kwargs)
    else:
        logger.warning(message)

def error(message: str, **kwargs) -> None:
    """
    Log an error message.
    
    Logs a message at ERROR level, optionally with structured context data.
    Error messages indicate issues that prevent normal operation.
    
    Args:
        message: The error message to log
        **kwargs: Optional context data for structured logging
    """
    if kwargs:
        structured_log('error', message, **kwargs)
    else:
        logger.error(message)

def critical(message: str, **kwargs) -> None:
    """
    Log a critical message.
    
    Logs a message at CRITICAL level, optionally with structured context data.
    Critical messages indicate severe errors that may cause application failure.
    
    Args:
        message: The critical message to log
        **kwargs: Optional context data for structured logging
    """
    if kwargs:
        structured_log('critical', message, **kwargs)
    else:
        logger.critical(message)

def log_config_summary(config: Dict[str, Any]) -> None:
    """
    Log a sanitized summary of the configuration.
    
    This function logs the application configuration while automatically hiding
    sensitive information like API keys and passwords. It's typically called
    during application startup to record the current configuration.
    
    Args:
        config: Dictionary of configuration values to log
    """
    # Make a copy of the config to avoid modifying the original
    safe_config = config.copy()
    
    # Sanitize sensitive values
    sensitive_keys = ['api_key', 'key', 'password', 'secret', 'token']
    for key in safe_config.keys():
        for sensitive in sensitive_keys:
            if sensitive in key.lower():
                safe_config[key] = '***REDACTED***'
    
    # Log the sanitized config
    info("Configuration summary:", config=safe_config)

_shutdown_handler_registered = False

def register_shutdown_handler(app, callback: Callable) -> None:
    """
    Register a function to be called when the application shuts down.
    
    This function sets up signal handlers to ensure a callback function is
    executed when the application shuts down, regardless of how the shutdown
    is triggered (normal exit, SIGTERM, SIGINT/Ctrl+C). It ensures the handler
    is only registered once.
    
    Args:
        app: Flask application instance
        callback: Function to call on shutdown
    """
    global _shutdown_handler_registered
    
    # Skip if already registered
    if _shutdown_handler_registered:
        return
        
    import atexit
    import signal
    import sys
    
    # Register the function to be called on normal interpreter exit
    atexit.register(callback)
    
    # Special handler for SIGINT (CTRL+C) that forces exit after callback
    def sigint_handler(sig, frame):
        callback(sig, frame)
        # Force exit to prevent hanging in Flask debug mode
        sys.exit(0)
    
    # Register the function to be called on SIGTERM
    signal.signal(signal.SIGTERM, callback)
    
    # On Unix-like systems, register SIGINT handler with special handling
    if hasattr(signal, 'SIGINT'):
        signal.signal(signal.SIGINT, sigint_handler)
        
    # Mark as registered to avoid duplicates
    _shutdown_handler_registered = True

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
    
    This utility function creates and configures a logger with both file and
    console output. It's primarily used for unit tests and isolated components
    that need their own logging configuration.
    
    Args:
        logger_name: Name of the logger to create
        log_file: Path to the log file to write to
        level: Log level (defaults to INFO or environment variable LOG_LEVEL)
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance ready for use
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
    
    This is a convenience function that returns a logger with a standardized
    name format for a specific module. It ensures consistent logger naming
    across the application.
    
    Args:
        module_name: Name of the module requesting a logger
        
    Returns:
        Logger instance specific to the requesting module
    """
    logger_name = f"app.{module_name}"
    return logging.getLogger(logger_name)

def log_request(req: Request) -> None:
    """
    Log an incoming HTTP request.
    
    This function logs information about an HTTP request, including the
    method, path, client IP address, and user agent. It's typically used
    in request middleware or route handlers.
    
    Args:
        req: Flask request object to log
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
    
    This function logs an exception with its full traceback information,
    making it easier to diagnose and fix errors. It's typically used in
    exception handlers throughout the application.
    
    Args:
        exception: Exception object to log
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