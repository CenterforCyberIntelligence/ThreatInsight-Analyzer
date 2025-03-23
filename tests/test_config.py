import pytest
import os
import json
import logging
from unittest.mock import patch

from app.config.config import Config

def test_config_basic_properties():
    """Test basic configuration properties."""
    # Basic configuration values
    assert Config.DB_PATH == os.path.join('data', 'article_analysis.db')
    assert Config.LOG_FORMAT == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    assert Config.LOG_MAX_SIZE == 10 * 1024 * 1024  # 10 MB
    assert Config.LOG_BACKUP_COUNT == 5

def test_get_log_level():
    """Test log level retrieval."""
    # Test default log level (INFO)
    with patch.dict(os.environ, {}, clear=True):
        assert Config.get_log_level() == logging.INFO
    
    # Test setting log level via environment
    with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
        assert Config.get_log_level() == logging.DEBUG
    
    with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
        assert Config.get_log_level() == logging.WARNING
    
    with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
        assert Config.get_log_level() == logging.ERROR
    
    with patch.dict(os.environ, {"LOG_LEVEL": "CRITICAL"}):
        assert Config.get_log_level() == logging.CRITICAL
    
    # Test invalid log level (should default to INFO)
    with patch.dict(os.environ, {"LOG_LEVEL": "INVALID_LEVEL"}):
        assert Config.get_log_level() == logging.INFO

def test_get_available_models():
    """Test model configuration retrieval."""
    # Test default models when environment variable not set
    with patch.dict(os.environ, {}, clear=True):
        models = Config.get_available_models()
        assert isinstance(models, dict)
        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models
        assert models["gpt-4o"]["name"] == "GPT-4o"
    
    # Test custom models from environment
    custom_models = {
        "gpt-5": {
            "name": "GPT-5",
            "recommended_for": "Ultimate performance"
        },
        "custom-model": {
            "name": "Custom Model",
            "recommended_for": "Specialized tasks"
        }
    }
    
    with patch.dict(os.environ, {"AVAILABLE_MODELS": json.dumps(custom_models)}):
        models = Config.get_available_models()
        assert "gpt-5" in models
        assert "custom-model" in models
        assert models["gpt-5"]["name"] == "GPT-5"
        assert models["custom-model"]["recommended_for"] == "Specialized tasks"
    
    # Test invalid JSON in environment variable (should use defaults)
    with patch.dict(os.environ, {"AVAILABLE_MODELS": "not valid json"}):
        with patch('app.utilities.logger.warning') as mock_warning:
            models = Config.get_available_models()
            assert isinstance(models, dict)
            assert "gpt-4o" in models
            assert mock_warning.called

def test_get_default_model():
    """Test default model retrieval."""
    # Test default when environment variable not set
    with patch.dict(os.environ, {}, clear=True):
        assert Config.get_default_model() == "gpt-4o"
    
    # Test with environment variable
    with patch.dict(os.environ, {"OPENAI_MODEL": "gpt-4-turbo"}):
        assert Config.get_default_model() == "gpt-4-turbo"

def test_get_model_prices():
    """Test model pricing information retrieval."""
    prices = Config.get_model_prices()
    assert isinstance(prices, dict)
    
    # Check specific model pricing
    assert "gpt-4o" in prices
    assert "input" in prices["gpt-4o"]
    assert "output" in prices["gpt-4o"]
    assert "cached" in prices["gpt-4o"]
    
    # Check all required models have pricing
    for model in ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"]:
        assert model in prices
        assert all(key in prices[model] for key in ["input", "output", "cached"])

def test_normalize_model_id():
    """Test model ID normalization."""
    # Test direct mapping
    assert Config.normalize_model_id("gpt-4o-2024-08-06") == "gpt-4o"
    assert Config.normalize_model_id("gpt-4o-mini-2024-07-18") == "gpt-4o-mini"
    assert Config.normalize_model_id("gpt-4-turbo-2024-04-09") == "gpt-4-turbo"
    
    # Test pattern-based normalization
    assert Config.normalize_model_id("gpt-4o-2023-12-01") == "gpt-4o"
    assert Config.normalize_model_id("gpt-3.5-turbo-0125") == "gpt-3.5-turbo"
    
    # Test already normalized model IDs
    assert Config.normalize_model_id("gpt-4o") == "gpt-4o"
    assert Config.normalize_model_id("gpt-4-turbo") == "gpt-4-turbo"
    
    # Test unknown model (should return as-is)
    assert Config.normalize_model_id("custom-model") == "custom-model"

def test_get_default_temperature():
    """Test default temperature retrieval."""
    # Test default when environment variable not set
    with patch.dict(os.environ, {}, clear=True):
        assert Config.get_default_temperature() == 0.1
    
    # Test with valid environment variable
    with patch.dict(os.environ, {"OPENAI_TEMPERATURE": "0.7"}):
        assert Config.get_default_temperature() == 0.7
    
    # Test with invalid environment variable (should use default)
    with patch.dict(os.environ, {"OPENAI_TEMPERATURE": "invalid"}):
        assert Config.get_default_temperature() == 0.1

def test_get_default_seed():
    """Test default seed retrieval."""
    # Should always return 42 for deterministic results
    assert Config.get_default_seed() == 42

def test_config_with_app_context(app):
    """Test configuration within app context."""
    with app.app_context():
        # Check that the test app has the overridden configuration
        assert app.config["TESTING"] is True
        assert app.config["SECRET_KEY"] == "test-key"
        assert app.config["DB_PATH"].endswith("test_article_analysis.db")
        
        # The actual Config class should be unchanged by app context
        assert Config.DB_PATH == os.path.join("data", "article_analysis.db") 