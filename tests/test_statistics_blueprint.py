import pytest
from unittest.mock import patch, MagicMock
import json
import contextlib
from flask import template_rendered, Flask
import flask

@contextlib.contextmanager
def captured_templates(app):
    """
    Context manager to capture templates rendered during a request.
    """
    recorded = []
    def record(sender, template, context, **extra):
        recorded.append((template, context))
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)

@pytest.fixture
def mock_token_usage_stats():
    return {
        'models': {
            'gpt-4o': {
                'total_input': 3000,
                'total_output': 2000,
                'cached_input': 1000,
                'regular_input': 2000
            }
        },
        'overall': {
            'total_input': 3000,
            'total_output': 2000,
            'cached_input': 1000,
            'regular_input': 2000,
            'total_tokens': 5000,
            'model_count': 1
        }
    }

@pytest.fixture
def mock_recent_analyses():
    return [
        {
            'id': 1,
            'url': 'https://example.com/article1',
            'title': 'Article 1',
            'model_id': 'gpt-4o',
            'content_length': 5000,
            'created_at': '2023-06-01T10:00:00'
        }
    ]

@pytest.fixture
def mock_model_prices():
    return {
        'gpt-4o': {
            'input': 10,
            'output': 30,
            'cached': 3
        },
        'gpt-4o-mini': {
            'input': 5,
            'output': 15,
            'cached': 1
        },
        'gpt-4-turbo': {
            'input': 10,
            'output': 30,
            'cached': 3
        }
    }

def test_statistics_endpoint(client, monkeypatch, mock_token_usage_stats, mock_recent_analyses, mock_model_prices):
    """Test the statistics dashboard endpoint."""
    
    # Patch the necessary functions
    with patch('app.blueprints.statistics.get_token_usage_stats', return_value=mock_token_usage_stats), \
         patch('app.blueprints.statistics.get_recent_analyses', return_value=mock_recent_analyses), \
         patch('app.blueprints.statistics.Config.get_model_prices', return_value=mock_model_prices), \
         patch('app.blueprints.statistics.Config.normalize_model_id', return_value='gpt-4o'):
        
        # Call the endpoint
        response = client.get('/statistics')
        
        # Verify response
        assert response.status_code == 200
        # Validate that the response contains HTML
        assert b'<!DOCTYPE html>' in response.data

def test_refresh_statistics_endpoint(client, monkeypatch, mock_token_usage_stats, mock_recent_analyses, mock_model_prices):
    """Test the statistics refresh endpoint."""
    
    # Patch the necessary functions
    with patch('app.blueprints.statistics.get_token_usage_stats', return_value=mock_token_usage_stats), \
         patch('app.blueprints.statistics.get_recent_analyses', return_value=mock_recent_analyses), \
         patch('app.blueprints.statistics.Config.get_model_prices', return_value=mock_model_prices), \
         patch('app.blueprints.statistics.Config.normalize_model_id', return_value='gpt-4o'):
        
        # Call the endpoint
        response = client.get('/statistics/refresh')
        
        # Verify response
        assert response.status_code == 200
        # Check that it's the partial template (no doctype)
        assert b'<!DOCTYPE html>' not in response.data
        assert b'card-body' in response.data

def test_model_price_normalization(client, monkeypatch, mock_token_usage_stats, mock_model_prices):
    """Test that model prices are properly normalized."""
    
    # Create a custom analyses list with a versioned model ID
    custom_analyses = [
        {
            'id': 1,
            'url': 'https://example.com/article1',
            'title': 'Article 1',
            'model_id': 'gpt-4o-2024-08-06',  # Using a versioned model ID
            'content_length': 5000,
            'created_at': '2023-06-01T10:00:00'
        }
    ]
    
    # Patch the necessary functions
    with patch('app.blueprints.statistics.get_token_usage_stats', return_value=mock_token_usage_stats), \
         patch('app.blueprints.statistics.get_recent_analyses', return_value=custom_analyses), \
         patch('app.blueprints.statistics.Config.get_model_prices', return_value=mock_model_prices), \
         patch('app.blueprints.statistics.Config.normalize_model_id', return_value='gpt-4o'):
        
        # Call the endpoint
        response = client.get('/statistics')
        
        # Verify response
        assert response.status_code == 200
        # Check basic HTML content
        assert b'<!DOCTYPE html>' in response.data

def test_empty_stats(client, monkeypatch):
    """Test statistics endpoints with empty data."""
    
    # Create empty data for testing
    empty_stats = {
        'models': {},
        'overall': {
            'total_input': 0,
            'total_output': 0,
            'cached_input': 0,
            'regular_input': 0,
            'total_tokens': 0,
            'model_count': 0
        }
    }
    empty_analyses = []
    basic_model_prices = {
        'gpt-4o': {
            'input': 10,
            'output': 30,
            'cached': 3
        }
    }
    
    # Patch the necessary functions
    with patch('app.blueprints.statistics.get_token_usage_stats', return_value=empty_stats), \
         patch('app.blueprints.statistics.get_recent_analyses', return_value=empty_analyses), \
         patch('app.blueprints.statistics.Config.get_model_prices', return_value=basic_model_prices), \
         patch('app.blueprints.statistics.Config.normalize_model_id', return_value='gpt-4o'):
        
        # Test statistics page with empty data
        response = client.get('/statistics')
        assert response.status_code == 200
        
        # Test refresh endpoint with empty data
        response = client.get('/statistics/refresh')
        assert response.status_code == 200 