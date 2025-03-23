import pytest
import os
import logging
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
import time

from app.utilities.logger import setup_logging, get_logger, log_request, log_exception
from app.utilities.logger import debug, info, warning, error, critical, print_status

def test_setup_logging():
    """Test the setup_logging function."""
    # Create a temporary directory for log files
    temp_dir = tempfile.mkdtemp()
    log_path = os.path.join(temp_dir, 'test.log')
    
    try:
        # Test with default parameters
        with patch('os.path.exists', return_value=False), \
             patch('os.makedirs') as mock_makedirs, \
             patch('os.environ.get') as mock_env_get:
             
            # Configure mock to return appropriate values based on key
            def mock_env_side_effect(key, default=None):
                if key == 'LOG_LEVEL':
                    return 'INFO'
                elif key == 'LOG_FORMAT':
                    return '%(asctime)s - %(levelname)s - %(message)s'
                elif key == 'FLASK_ENV':
                    return None
                return default
                
            mock_env_get.side_effect = mock_env_side_effect
            
            logger = setup_logging('test_logger', log_path)
            
            # Verify logger configuration
            assert logger.name == 'test_logger'
            assert logger.level == logging.INFO
            
            # Verify directory creation if it doesn't exist
            mock_makedirs.assert_called_once()
        
        # Test with custom log level
        with patch('os.path.exists', return_value=True), \
             patch('os.environ.get') as mock_env_get:
            
            def mock_env_side_effect(key, default=None):
                if key == 'LOG_LEVEL':
                    return 'DEBUG'
                elif key == 'LOG_FORMAT':
                    return '%(asctime)s - %(levelname)s - %(message)s'
                return default
                
            mock_env_get.side_effect = mock_env_side_effect
            
            logger = setup_logging('test_logger_debug', log_path)
            assert logger.level == logging.DEBUG
        
        # Test with rotating file handler
        logger = setup_logging('test_logger_rotating', log_path, max_bytes=1024, backup_count=3)
        # Check that a handler was added
        assert len(logger.handlers) > 0
        
        # Test actual file creation
        logger = setup_logging('test_file_logger', log_path)
        logger.info("Test log message")
        
        # Give the logger a moment to write to the file
        time.sleep(0.1)
        
        # Check if the log file was created and contains the message
        assert os.path.exists(log_path)
        with open(log_path, 'r') as f:
            log_content = f.read()
            assert "Test log message" in log_content
        
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

def test_get_logger():
    """Test the get_logger function."""
    # Test getting the same logger multiple times
    logger1 = get_logger('test_module')
    logger2 = get_logger('test_module')
    
    # Should return the same logger instance
    assert logger1 is logger2
    
    # Test getting different loggers
    logger3 = get_logger('different_module')
    assert logger1 is not logger3
    
    # Verify logger naming
    assert logger1.name == 'app.test_module'
    assert logger3.name == 'app.different_module'

def test_log_request():
    """Test the log_request function."""
    # Create a mock request
    mock_request = MagicMock()
    mock_request.method = "GET"
    mock_request.path = "/test/path"
    mock_request.remote_addr = "127.0.0.1"
    mock_request.user_agent.string = "Test User Agent"
    
    # Test basic request logging
    with patch('app.utilities.logger.get_logger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        log_request(mock_request)
        
        # Verify the logger was called with the correct information
        mock_get_logger.assert_called_once_with('requests')
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        
        # Check log message contains request details
        assert "GET" in log_message
        assert "/test/path" in log_message
        assert "127.0.0.1" in log_message
        assert "Test User Agent" in log_message

def test_log_exception():
    """Test the log_exception function."""
    # Test exception logging
    with patch('app.utilities.logger.get_logger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        try:
            # Raise an exception to log
            raise ValueError("Test exception")
        except Exception as e:
            log_exception(e, "Test module")
        
        # Verify the logger was called with the correct information
        mock_get_logger.assert_called_once_with('Test module')
        mock_logger.exception.assert_called_once()
        
        # Check log message contains exception details
        log_message = mock_logger.exception.call_args[0][0]
        assert "Exception occurred" in log_message
        assert "ValueError" in log_message
        assert "Test exception" in log_message

def test_logger_performance():
    """Test logger performance optimization with isEnabledFor."""
    # Create a test logger
    logger = logging.getLogger('test_performance_logger')
    logger.setLevel(logging.WARNING)
    
    # Add a handler that tracks the logged messages
    test_handler = MagicMock()
    # Set proper level attribute on the mock handler
    test_handler.level = logging.WARNING
    logger.addHandler(test_handler)
    
    # Get the wrapped logger
    with patch('logging.getLogger', return_value=logger):
        app_logger = get_logger('performance_test')
        
        # Test that debug messages aren't logged when level is WARNING
        app_logger.debug("This debug message should not be logged")
        test_handler.handle.assert_not_called()
        
        # Test that warning messages are logged
        app_logger.warning("This warning should be logged")
        test_handler.handle.assert_called_once()
        
        # Reset mock
        test_handler.reset_mock()
        
        # Test isEnabledFor optimization pattern
        if app_logger.isEnabledFor(logging.DEBUG):
            # This code should not execute since level is WARNING
            expensive_computation = "Expensive" + " computation" * 1000
            app_logger.debug(f"Expensive result: {expensive_computation}")
        
        # Verify no logging occurred
        test_handler.handle.assert_not_called()

def test_logging_with_extra_context():
    """Test logging with extra context information."""
    # Setup logger with a mock handler
    logger = logging.getLogger('test_extra_context')
    logger.setLevel(logging.INFO)
    
    # Create a real handler that we'll monkey-patch
    class TestHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records = []
            
        def emit(self, record):
            self.records.append(record)
    
    test_handler = TestHandler()
    test_handler.level = logging.INFO
    logger.addHandler(test_handler)
    
    # Get wrapped logger
    with patch('logging.getLogger', return_value=logger):
        app_logger = get_logger('context_test')
        
        # Log with extra context
        extra_context = {
            'user_id': '12345',
            'request_id': 'abc-123',
            'action': 'test_action'
        }
        
        app_logger.info("Test message with context", extra=extra_context)
        
        # Verify the extra context was included
        assert len(test_handler.records) == 1
        record = test_handler.records[0]
        
        assert hasattr(record, 'user_id')
        assert record.user_id == '12345'
        assert record.request_id == 'abc-123'
        assert record.action == 'test_action'
        assert "Test message with context" in record.getMessage()

def test_dedicated_logging_functions():
    """Test the dedicated logging functions."""
    # Setup a mock for the logger used by these functions
    with patch('app.utilities.logger.logger') as mock_logger:
        # Test each dedicated function
        debug("Debug message")
        mock_logger.debug.assert_called_once_with("Debug message")
        mock_logger.reset_mock()
        
        info("Info message")
        mock_logger.info.assert_called_once_with("Info message")
        mock_logger.reset_mock()
        
        warning("Warning message")
        mock_logger.warning.assert_called_once_with("Warning message")
        mock_logger.reset_mock()
        
        error("Error message")
        mock_logger.error.assert_called_once_with("Error message")
        mock_logger.reset_mock()
        
        critical("Critical message")
        mock_logger.critical.assert_called_once_with("Critical message")
        mock_logger.reset_mock()
        
        # Test print_status with default parameters
        print_status("Status message")
        mock_logger.info.assert_called_once_with("Status message")
        mock_logger.reset_mock()
        
        # Test print_status with is_error=True
        print_status("Error status message", is_error=True)
        mock_logger.error.assert_called_once_with("Error status message") 