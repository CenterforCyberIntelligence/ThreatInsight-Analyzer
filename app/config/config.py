import os
from typing import Dict, Any
from dotenv import load_dotenv
import json
import logging

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-please-change-in-production")
    SEND_FILE_MAX_AGE_DEFAULT = 0
    DB_PATH = os.path.join('data', 'article_analysis.db')
    
    # Logging configuration
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 5
    
    @staticmethod
    def get_log_level() -> int:
        """Get the configured log level."""
        level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(level_name, logging.INFO)
    
    # Get model configurations from environment variables
    @staticmethod
    def get_available_models() -> Dict[str, Dict[str, str]]:
        """Get available models from environment variables."""
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
            models_env = os.getenv("AVAILABLE_MODELS")
            return json.loads(models_env) if models_env else default_models
        except (json.JSONDecodeError, NameError):
            from app.utilities.logger import warning
            warning("Failed to parse AVAILABLE_MODELS from environment, using defaults")
            return default_models

    @staticmethod
    def get_default_model() -> str:
        """Get default model from environment variables."""
        return os.getenv("OPENAI_MODEL", "gpt-4o")

    @staticmethod
    def get_model_prices() -> Dict[str, Dict[str, float]]:
        """Get model pricing information."""
        return {
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
            }
        }
        
    @staticmethod
    def get_default_temperature() -> float:
        """Get default temperature from environment variables."""
        try:
            return float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
        except ValueError:
            return 0.1
            
    @staticmethod
    def get_default_seed() -> int:
        """Get default seed for reproducible outputs."""
        return 42  # Fixed seed for consistency 