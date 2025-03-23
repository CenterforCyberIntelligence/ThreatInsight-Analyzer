import os
from typing import Dict, Any
from dotenv import load_dotenv
import json
import logging
import re

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
            "gpt-3.5-turbo": {
                "input": 0.0005,
                "cached": 0.00025,
                "output": 0.0015
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
            }
        }
        
    @staticmethod
    def normalize_model_id(model_id: str) -> str:
        """
        Normalize model ID by removing version information.
        This helps in matching model IDs with different versions to their base models.
        
        For example:
        - "gpt-4o-2024-08-06" -> "gpt-4o"
        - "gpt-4-turbo-0125" -> "gpt-4-turbo"
        - "gpt-3.5-turbo" -> "gpt-3.5-turbo"
        """
        if not model_id:
            return ""
            
        # Define model aliases to map specific versions to their base models
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
        
        # If we didn't find a specific match, try the base model extraction
        if base_model == model_id:
            # Try to match to one of our known base models
            known_base_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
            for known_model in known_base_models:
                if known_model in model_id:
                    return known_model
        
        return base_model
        
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