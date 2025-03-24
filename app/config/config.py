import os
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv
import json
import logging
import re
import time
import threading
from functools import lru_cache
import secrets
from datetime import datetime

# Load environment variables from .env file if it exists
# This ensures all configuration can be set via environment variables
if os.path.exists('.env'):
    load_dotenv()

# Global variables for OpenAI API state tracking
# These variables are used to cache API availability status to avoid redundant checks
_openai_api_available = False            # Tracks if the OpenAI API is available
_openai_api_last_check = 0               # Timestamp of the last API check
_openai_api_check_lock = threading.Lock() # Lock for thread-safe updates to API status
_CONFIG_VALIDATION_ERRORS = []           # Stores configuration validation errors

class Config:
    """
    Configuration settings for the ThreatInsight-Analyzer application.
    
    This class centralizes all configuration settings and provides methods
    to access and validate them. All settings are loaded from environment
    variables with sensible defaults when not specified.
    """
    
    #######################################################################
    # CORE APPLICATION SETTINGS
    #######################################################################
    
    # Base configuration
    # Controls application-wide behavior and security settings
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'        # Application debug mode
    TESTING = os.getenv('TESTING', 'False').lower() == 'true'    # Test mode flag
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-please-change-in-production")  # Flask secret key
    SEND_FILE_MAX_AGE_DEFAULT = int(os.getenv("SEND_FILE_MAX_AGE_DEFAULT", "0"))  # Static file cache control
    
    # Environment detection
    # Used to apply environment-specific settings
    ENV = os.getenv("FLASK_ENV", "development")  # Current environment (development/production) 
    IS_PRODUCTION = ENV == "production"  # Helper flag for production-specific behavior
    
    # Generate a default secure token for admin features
    # This is used as a fallback when ADMIN_DEBUG_TOKEN is not provided
    DEFAULT_DEBUG_TOKEN = secrets.token_hex(32)
    
    # Admin debug token for secured endpoints
    ADMIN_DEBUG_TOKEN = os.getenv('ADMIN_DEBUG_TOKEN', DEFAULT_DEBUG_TOKEN)
    
    #######################################################################
    # FLASK SERVER SETTINGS
    #######################################################################
    
    # Flask application settings
    # Controls the web server behavior
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")  # Host to bind to (0.0.0.0 = all interfaces)
    FLASK_PORT = int(os.getenv("FLASK_PORT", "8000"))  # Port to listen on
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"  # Flask debug mode (separate from app DEBUG)
    
    #######################################################################
    # DATABASE SETTINGS
    #######################################################################
    
    # Database configuration
    # Defines where and how the application stores data
    DB_PATH = os.getenv("DATABASE_PATH", os.path.join('data', 'article_analysis.db'))
    
    #######################################################################
    # LOGGING SETTINGS
    #######################################################################
    
    # Logging configuration
    # Controls how the application logs messages
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()  # Log verbosity
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # Maximum log file size (10 MB default)
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))  # Number of backup logs to keep
    
    #######################################################################
    # OPENAI API SETTINGS
    #######################################################################
    
    # OpenAI API Configuration
    # Settings for interaction with OpenAI's API
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # API key for authentication
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")  # API endpoint
    OPENAI_API_TIMEOUT = int(os.getenv("OPENAI_API_TIMEOUT", "60"))  # Timeout for API requests in seconds
    DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")  # Default model for analysis
    DEFAULT_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.0"))  # Controls randomness
    MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "1500"))  # Max tokens to generate
    DEFAULT_SEED = int(os.getenv("OPENAI_SEED", "42"))  # Seed for reproducible outputs
    
    #######################################################################
    # HEALTH CHECK SETTINGS
    #######################################################################
    
    # Health check configuration
    # Controls how the application monitors API availability
    HEALTH_CHECK_API = os.getenv("HEALTH_CHECK_API", "true").lower() == "true"  # Enable API health checks
    HEALTH_CHECK_API_INTERVAL = int(os.getenv("HEALTH_CHECK_API_INTERVAL", "3600"))  # Check interval in seconds
    
    #######################################################################
    # APPLICATION CONFIGURATION
    #######################################################################
    
    # Try to parse ALLOWED_EXTENSIONS from environment as a JSON array
    # Falls back to default set if parsing fails
    try:
        ALLOWED_EXTENSIONS = set(json.loads(os.getenv("ALLOWED_EXTENSIONS", '["txt", "pdf", "html", "htm"]')))
    except (json.JSONDecodeError, TypeError):
        ALLOWED_EXTENSIONS = {"txt", "pdf", "html", "htm"}  # Default allowed file types
    
    # Path to blocked domains file (from environment or default)
    BLOCKED_DOMAINS_FILE = os.getenv(
        "BLOCKED_DOMAINS_FILE", 
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'blocked_domains.txt')
    )
    
    #######################################################################
    # UI CONFIGURATION
    #######################################################################
    
    # UI Configuration
    # Controls the appearance and styling of the user interface
    HEADING_FONT = os.getenv("HEADING_FONT", "Rajdhani")  # Font for headings and titles
    
    #######################################################################
    # METHODS FOR ACCESSING CONFIGURATION
    #######################################################################
    
    @staticmethod
    def get_log_level() -> int:
        """
        Convert the string log level from environment to the corresponding
        logging module constant.
        
        Returns:
            The logging level constant (e.g., logging.INFO)
        """
        level_name = Config.LOG_LEVEL
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(level_name, logging.INFO)  # Default to INFO if level not recognized
    
    @staticmethod
    def get_as_dict() -> Dict[str, Any]:
        """
        Get configuration as a dictionary for logging or inspection.
        This method is used to display the current configuration settings.
        It handles special cases like sets which need conversion for JSON serialization.
        
        Returns:
            Dictionary containing all configuration values
        """
        config_dict = {}
        for key in dir(Config):
            # Only include non-private, non-method attributes
            if not key.startswith('_') and not callable(getattr(Config, key)):
                value = getattr(Config, key)
                
                # Convert sets to lists for JSON serialization
                # This ensures sets like ALLOWED_EXTENSIONS can be properly logged/displayed
                if isinstance(value, set):
                    config_dict[key] = list(value)
                else:
                    config_dict[key] = value
                    
        return config_dict
    
    #######################################################################
    # CONFIGURATION VALIDATION
    #######################################################################
    
    @staticmethod
    def validate_configuration() -> List[str]:
        """
        Validate critical configuration settings on application startup.
        This ensures the application has all required settings before running.
        
        Validates:
        - OpenAI API key presence
        - Database directory accessibility
        - Log directory accessibility
        - ALLOWED_EXTENSIONS validity
        
        Returns:
            List of validation errors (empty if all validations pass)
        """
        global _CONFIG_VALIDATION_ERRORS
        errors = []
        
        # Check OpenAI API key
        # This is required for the application to function
        if not Config.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is missing. Set it in .env file or environment.")
            
        # Check database path is writeable
        # Create the directory if it doesn't exist
        db_dir = os.path.dirname(Config.DB_PATH)
        if not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception as e:
                errors.append(f"Database directory {db_dir} cannot be created: {e}")
        else:
            if not os.access(db_dir, os.W_OK):
                errors.append(f"Database directory {db_dir} is not writeable.")
        
        # Check log directory is writeable
        # Create the directory if it doesn't exist
        if not os.path.exists(Config.LOG_DIR):
            try:
                os.makedirs(Config.LOG_DIR, exist_ok=True)
            except Exception as e:
                errors.append(f"Log directory {Config.LOG_DIR} cannot be created: {e}")
        else:
            if not os.access(Config.LOG_DIR, os.W_OK):
                errors.append(f"Log directory {Config.LOG_DIR} is not writeable.")
        
        # Validate ALLOWED_EXTENSIONS
        # Ensure it's a non-empty set
        if not Config.ALLOWED_EXTENSIONS or not isinstance(Config.ALLOWED_EXTENSIONS, set):
            errors.append("ALLOWED_EXTENSIONS is invalid. Check the format in .env file.")
        
        # Store errors for later retrieval
        _CONFIG_VALIDATION_ERRORS = errors
        return errors
    
    @staticmethod
    def get_validation_errors() -> List[str]:
        """
        Get any configuration validation errors that were detected.
        If validation hasn't been run yet, this will trigger validation.
        
        Returns:
            List of validation error messages
        """
        global _CONFIG_VALIDATION_ERRORS
        if not _CONFIG_VALIDATION_ERRORS:
            Config.validate_configuration()
        return _CONFIG_VALIDATION_ERRORS
    
    #######################################################################
    # OPENAI MODEL AND PRICING METHODS
    #######################################################################
    
    @staticmethod
    def get_available_models() -> Dict[str, Dict[str, str]]:
        """
        Get available OpenAI models from environment variables.
        Parses the AVAILABLE_MODELS environment variable if present.
        
        The expected format is a JSON object mapping model IDs to objects with:
        - name: User-friendly name for the model
        - recommended_for: Description of what the model is good for
        
        Returns:
            Dictionary of model configurations
        """
        # Default models if environment variable is not set or invalid
        default_models = {
            "gpt-4o-mini": {
                "name": "GPT-4o mini",
                "recommended_for": "Quick analysis of news articles and blog posts",
            },
            "gpt-4o": {
                "name": "GPT-4o",
                "recommended_for": "Detailed analysis of technical reports and research papers",
            },
            "gpt-4-turbo": {
                "name": "GPT-4.5 Turbo",
                "recommended_for": "In-depth analysis of complex threat reports and intelligence briefs",
            }
        }
        
        try:
            # Attempt to parse AVAILABLE_MODELS from environment
            models_env = os.getenv("AVAILABLE_MODELS")
            return json.loads(models_env) if models_env else default_models
        except (json.JSONDecodeError, NameError):
            # Log warning and use defaults if parsing fails
            from app.utilities.logger import warning
            warning("Failed to parse AVAILABLE_MODELS from environment, using defaults")
            return default_models

    @staticmethod
    def get_default_model() -> str:
        """
        Get the default OpenAI model to use when none is specified.
        This is determined by the OPENAI_MODEL environment variable.
        
        Returns:
            Default model ID (e.g., "gpt-4o")
        """
        return Config.DEFAULT_MODEL
    
    @staticmethod
    def get_model_prices() -> Dict[str, Dict[str, float]]:
        """
        Get pricing information for different OpenAI models.
        Attempts to parse the OPENAI_MODEL_PRICES environment variable if available.
        
        The pricing is used for:
        - Statistics and cost tracking
        - Displaying pricing information to users
        - Calculating estimated costs before running analysis
        
        Returns:
            Dictionary mapping model IDs to pricing information for input, output, and cached tokens
        """
        # Try to parse from environment variable OPENAI_MODEL_PRICES if available
        model_prices_env = os.getenv("OPENAI_MODEL_PRICES")
        if model_prices_env:
            try:
                return json.loads(model_prices_env)
            except (json.JSONDecodeError, TypeError):
                from app.utilities.logger import warning
                warning("Failed to parse OPENAI_MODEL_PRICES from environment, using defaults")
        
        # Default model pricing information (per 1K tokens)
        return {
            "gpt-3.5-turbo": {
                "input": 0.0005,   # Cost for input tokens
                "cached": 0.00025, # Cost for cached tokens (used for cost optimization)
                "output": 0.0015   # Cost for output tokens
            },
            "gpt-4o-mini": {
                "input": 0.15,
                "cached": 0.075,
                "output": 0.6
            },
            "gpt-4o": {
                "input": 0.5,
                "cached": 0.25,
                "output": 1.5
            },
            "gpt-4-turbo": {
                "input": 10.0,
                "cached": 5.0,
                "output": 30.0
            },
            "gpt-4": {
                "input": 0.03,
                "cached": 0.015,
                "output": 0.06
            },
            "gpt-4-32k": {
                "input": 0.06,
                "cached": 0.03,
                "output": 0.12
            },
            "gpt-4o-2024-08-06": {
                "input": 5.0,
                "cached": 0.0,
                "output": 15.0
            }
        }
        
    @staticmethod
    def normalize_model_id(model_id: str) -> str:
        """
        Normalize OpenAI model ID by removing version information.
        This is crucial for matching model IDs with their base models for:
        - Finding pricing information
        - Determining token limits
        - Displaying model information consistently
        
        For example:
        - "gpt-4o-2024-08-06" -> "gpt-4o"
        - "gpt-4-turbo-0125" -> "gpt-4-turbo"
        - "gpt-3.5-turbo" -> "gpt-3.5-turbo"
        
        Returns:
            Normalized model ID (without version information)
        """
        if not model_id:
            return "gpt-3.5-turbo"  # Default model if none specified
            
        # Define model aliases to map specific versions to their base models
        # This handles known model versions explicitly
        model_aliases = {
            # Map any specific versioned models to base models
            "gpt-4o-2024-08-06": "gpt-4o",
            "gpt-4o-mini-2024-07-18": "gpt-4o-mini",
            "gpt-4-turbo-2024-04-09": "gpt-4-turbo",
            "gpt-3.5-turbo": "gpt-3.5-turbo",
            "gpt-3.5-turbo-0125": "gpt-3.5-turbo",
            "gpt-3.5-turbo-1106": "gpt-3.5-turbo",
            "gpt-3.5-turbo-0613": "gpt-3.5-turbo"
        }
        
        # Check if there's a direct alias mapping
        if model_id in model_aliases:
            return model_aliases[model_id]
        
        # For standard versioned models, try to extract the base model
        # Strip out date-based version identifiers like -2024-08-06 or -0125
        base_model = re.sub(r'-(20\d{2}-\d{2}-\d{2}|\d{4})$', '', model_id)
        
        # If we didn't find a specific match, try matching to known base models
        if base_model == model_id:
            known_base_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
            for known_model in known_base_models:
                if known_model in model_id:
                    return known_model
        
        # Add the new model
        if "gpt-4o-2024-08-06" in model_id:
            return "gpt-4o"
        
        return base_model
        
    @staticmethod
    def get_default_temperature() -> float:
        """
        Get the default temperature setting for OpenAI API calls.
        Temperature controls randomness in the model's output:
        - 0.0: Deterministic, focused on most likely completion
        - 1.0: More creative, diverse completions
        
        For threat analysis, lower temperatures (0.0-0.3) are preferred
        for more factual, consistent results.
        
        Returns:
            Default temperature value from OPENAI_TEMPERATURE env var
        """
        return Config.DEFAULT_TEMPERATURE
            
    @staticmethod
    def get_default_seed() -> int:
        """
        Get default seed for reproducible outputs from OpenAI models.
        Using a consistent seed ensures that repeated queries with the
        same input will produce similar results.
        
        Returns:
            Seed value from OPENAI_SEED env var or 42 as default
        """
        return Config.DEFAULT_SEED
    
    #######################################################################
    # API HEALTH CHECK METHODS
    #######################################################################
    
    @staticmethod
    @lru_cache(maxsize=1)
    def check_openai_api() -> Tuple[bool, str]:
        """
        Check if the OpenAI API is available and working.
        
        This method:
        1. Checks if a recent check result is cached to avoid redundant API calls
        2. Makes a lightweight API request to verify connectivity
        3. Caches the result for the configured interval
        
        The @lru_cache decorator helps prevent repeated API checks in a short time.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        global _openai_api_available, _openai_api_last_check, _openai_api_check_lock
        
        # Check if we've already done the check recently
        # This prevents unnecessary API calls and improves performance
        current_time = time.time()
        with _openai_api_check_lock:
            if (_openai_api_last_check > 0 and 
                current_time - _openai_api_last_check < Config.HEALTH_CHECK_API_INTERVAL):
                return _openai_api_available, "Using cached API status"
        
        # Skip actual check if health checks are disabled in configuration
        if not Config.HEALTH_CHECK_API:
            return True, "API check disabled"
            
        # Can't check API without a key
        if not Config.OPENAI_API_KEY:
            _openai_api_available = False
            return False, "OpenAI API key is not configured"
        
        try:
            from app.utilities.logger import info, error
            
            import openai
            from openai import OpenAI
            
            # Create a client with a short timeout for the health check
            # We use a shorter timeout than the main application to ensure checks are quick
            client = OpenAI(
                api_key=Config.OPENAI_API_KEY,
                base_url=Config.OPENAI_BASE_URL,
                timeout=10.0  # Short timeout for health checks
            )
            
            # Use a simple model query to test API connectivity
            # This minimizes token usage while verifying the API works
            start_time = time.time()
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use cheaper model for health checks
                messages=[{"role": "user", "content": "Say hello"}],
                max_tokens=5  # Minimal response to reduce costs
            )
            
            elapsed = time.time() - start_time
            
            # Update cache with successful result
            with _openai_api_check_lock:
                _openai_api_available = True
                _openai_api_last_check = current_time
            
            return True, f"API available (response time: {elapsed:.2f}s)"
            
        except Exception as e:
            error_message = f"OpenAI API check failed: {str(e)}"
            
            # Import error logger only if needed to avoid circular imports
            try:
                from app.utilities.logger import error
                error(error_message)
            except ImportError:
                logging.error(error_message)
            
            # Update cache with failure result
            with _openai_api_check_lock:
                _openai_api_available = False
                _openai_api_last_check = current_time
            
            return False, error_message
    
    #######################################################################
    # DATA ACCESS METHODS
    #######################################################################

    @classmethod
    def get_blocked_domains(cls):
        """
        Load blocked domains from JSON file.
        Blocked domains are used to prevent analysis of known malicious
        or unwanted domains as a security and abuse prevention measure.
        
        Returns:
            List of blocked domain patterns
        """
        try:
            if os.path.exists(cls.BLOCKED_DOMAINS_FILE):
                with open(cls.BLOCKED_DOMAINS_FILE, 'r') as f:
                    return json.load(f)
            return []  # Return empty list if file doesn't exist
        except Exception as e:
            logging.error(f"Error loading blocked domains: {e}")
            return []  # Return empty list on error
    
    #######################################################################
    # TOKEN MANAGEMENT METHODS
    #######################################################################
    
    @staticmethod
    def get_token_limits():
        """
        Get token limits for different OpenAI models.
        Token limits are important for:
        - Ensuring inputs don't exceed model capabilities
        - Optimizing content chunking for long documents
        - Estimating costs accurately
        
        Attempts to load from TOKEN_LIMITS environment variable if available.
        
        Returns:
            Dictionary mapping model IDs to their token limits
        """
        # Try to parse from environment variable TOKEN_LIMITS if available
        token_limits_env = os.getenv("TOKEN_LIMITS")
        if token_limits_env:
            try:
                return json.loads(token_limits_env)
            except (json.JSONDecodeError, TypeError):
                from app.utilities.logger import warning
                warning("Failed to parse TOKEN_LIMITS from environment, using defaults")
                
        # Default token limits for various OpenAI models
        # These values represent the maximum combined tokens (input + output)
        return {
            "gpt-3.5-turbo": 16385,
            "gpt-3.5-turbo-0125": 16385,
            "gpt-3.5-turbo-1106": 16385,
            "gpt-3.5-turbo-16k": 16385,
            "gpt-4": 8192,
            "gpt-4-1106-preview": 128000,
            "gpt-4-0125-preview": 128000,
            "gpt-4-turbo-preview": 128000,
            "gpt-4-turbo": 128000,
            "gpt-4-0314": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-32k-0314": 32768,
            "gpt-4o": 128000,
            "gpt-4o-mini": 32768,
            "gpt-4o-2024-05-13": 128000,
            "gpt-4o-2024-08-06": 128000,
        }
    
    # Use a lock to protect token_limits cache for thread safety
    _token_limits_lock = threading.Lock()
    _token_limits = None
    
    @classmethod
    def get_token_limit(cls, model_id):
        """
        Get the token limit for a specific model.
        Uses thread-safe singleton pattern to cache token limits.
        
        This method:
        1. Normalizes the model ID to handle different versions
        2. Looks up the limit for the normalized model
        3. Returns a reasonable default if model not found
        
        Args:
            model_id: The OpenAI model identifier
            
        Returns:
            Token limit for the model (integer)
        """
        with cls._token_limits_lock:
            # Initialize token limits if not already loaded
            if cls._token_limits is None:
                cls._token_limits = cls.get_token_limits()
            
            # Normalize model ID to handle version suffixes
            # This ensures "gpt-4o-2024-08-06" matches the entry for "gpt-4o"
            normalized_id = cls.normalize_model_id(model_id)
            
            # Return the limit for the normalized model ID or a default if not found
            return cls._token_limits.get(normalized_id, 4096)  # 4096 as conservative default
    
    @classmethod
    def get_model_price(cls, model_id, is_input=True):
        """
        Get the price per 1K tokens for a specific model and token type.
        
        Used for:
        - Calculating costs for completed analyses
        - Estimating costs before analysis
        - Displaying pricing information to users
        
        Args:
            model_id: The OpenAI model identifier
            is_input: True for input token price, False for output token price
            
        Returns:
            Price per 1K tokens (float)
        """
        model_prices = cls.get_model_prices()
        normalized_id = cls.normalize_model_id(model_id)
        
        if normalized_id in model_prices:
            if is_input:
                return model_prices[normalized_id]["input"]
            else:
                return model_prices[normalized_id]["output"]
        
        # Default prices if model not found (conservative estimates)
        if is_input:
            return 0.01  # Default input price per 1K tokens
        else:
            return 0.03  # Default output price per 1K tokens

# Run initial validation on module import
# This ensures configuration is valid before the application starts
Config.validate_configuration() 