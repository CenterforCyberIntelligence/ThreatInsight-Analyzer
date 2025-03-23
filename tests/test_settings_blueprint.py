import pytest
from unittest.mock import patch, MagicMock
import json
import os

from tests.conftest import captured_templates

def test_settings_page_endpoint(client):
    """Test the settings page endpoint."""
    with client.application.app_context():
        with captured_templates(client.application) as templates:
            response = client.get('/settings')
            
            assert response.status_code == 200
            # Check that the right template was rendered
            assert len(templates) > 0
            template, context = templates[0]
            assert template.name == 'settings.html'

def test_api_settings_endpoint(client):
    """Test the API settings endpoint."""
    # Test with mocked environment values
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-api-key',
        'OPENAI_MODEL': 'gpt-4o',
        'OPENAI_TEMPERATURE': '0.7',
        'OPENAI_MAX_TOKENS': '2000'
    }):
        with client.application.app_context():
            with captured_templates(client.application) as templates:
                response = client.get('/settings/api')
                
                assert response.status_code == 200
                # Check that the right template was rendered
                assert len(templates) > 0
                template, context = templates[0]
                assert template.name == 'partials/api_settings.html'
                
                # Check that sensitive data is masked
                assert context['api_key_set'] is True
                assert 'test-api-key' not in response.data.decode()
                assert b'********' in response.data
                
                # Check that other settings are provided
                assert context['default_model'] == 'gpt-4o'
                assert context['temperature'] == '0.7'
                assert context['max_tokens'] == '2000'
                
                # Check available models
                assert 'available_models' in context
                assert isinstance(context['available_models'], dict)

def test_update_api_settings(client):
    """Test updating API settings."""
    # Test successful update with proper data
    with patch('app.blueprints.settings.update_env_file') as mock_update:
        mock_update.return_value = True
        
        response = client.post('/settings/api/update', data={
            'api_key': 'new-test-api-key',
            'default_model': 'gpt-4o-mini',
            'temperature': '0.5',
            'max_tokens': '1000'
        }, headers={'HX-Request': 'true'})
        
        assert response.status_code == 200
        assert b'success' in response.data
        assert b'API settings updated successfully' in response.data
        
        # Check that update_env_file was called with correct args
        mock_update.assert_called_once()
        args = mock_update.call_args[0][0]
        assert args['OPENAI_API_KEY'] == 'new-test-api-key'
        assert args['OPENAI_MODEL'] == 'gpt-4o-mini'
        assert args['OPENAI_TEMPERATURE'] == '0.5'
        assert args['OPENAI_MAX_TOKENS'] == '1000'
    
    # Test keeping existing API key (masked with asterisks)
    with patch('app.blueprints.settings.update_env_file') as mock_update, \
         patch.dict(os.environ, {'OPENAI_API_KEY': 'existing-key'}):
        mock_update.return_value = True
        
        response = client.post('/settings/api/update', data={
            'api_key': '********',
            'default_model': 'gpt-4o',
            'temperature': '0.7',
            'max_tokens': '2000'
        }, headers={'HX-Request': 'true'})
        
        assert response.status_code == 200
        assert b'success' in response.data
        
        # Check that the API key wasn't changed (not in the args)
        args = mock_update.call_args[0][0]
        assert 'OPENAI_API_KEY' not in args
    
    # Test with update failure
    with patch('app.blueprints.settings.update_env_file') as mock_update:
        mock_update.return_value = False
        
        response = client.post('/settings/api/update', data={
            'api_key': 'test-api-key',
            'default_model': 'gpt-4o',
            'temperature': '0.7',
            'max_tokens': '2000'
        }, headers={'HX-Request': 'true'})
        
        assert response.status_code == 500
        assert b'error' in response.data
        assert b'Failed to update API settings' in response.data

def test_update_api_settings_validation(client):
    """Test validation for API settings updates."""
    # Test with invalid temperature
    response = client.post('/settings/api/update', data={
        'api_key': 'test-api-key',
        'default_model': 'gpt-4o',
        'temperature': 'invalid',
        'max_tokens': '2000'
    }, headers={'HX-Request': 'true'})
    
    assert response.status_code == 400
    assert b'error' in response.data
    assert b'Temperature must be a number between 0 and 1' in response.data
    
    # Test with invalid max tokens
    response = client.post('/settings/api/update', data={
        'api_key': 'test-api-key',
        'default_model': 'gpt-4o',
        'temperature': '0.7',
        'max_tokens': 'invalid'
    }, headers={'HX-Request': 'true'})
    
    assert response.status_code == 400
    assert b'error' in response.data
    assert b'Max tokens must be a positive number' in response.data
    
    # Test with empty API key (when not previously set)
    with patch.dict(os.environ, {}, clear=True):
        response = client.post('/settings/api/update', data={
            'api_key': '',
            'default_model': 'gpt-4o',
            'temperature': '0.7',
            'max_tokens': '2000'
        }, headers={'HX-Request': 'true'})
        
        assert response.status_code == 400
        assert b'error' in response.data
        assert b'API key is required' in response.data

def test_model_settings_endpoint(client):
    """Test the model settings endpoint."""
    with client.application.app_context():
        with captured_templates(client.application) as templates:
            response = client.get('/settings/models')
            
            assert response.status_code == 200
            # Check that the right template was rendered
            assert len(templates) > 0
            template, context = templates[0]
            assert template.name == 'partials/model_settings.html'
            
            # Check that model data is available
            assert 'models' in context
            assert 'model_json' in context  # JSON representation for editing

def test_update_model_settings(client):
    """Test updating model settings."""
    # Test successful update with proper data
    with patch('app.blueprints.settings.update_env_file') as mock_update:
        mock_update.return_value = True
        
        # Valid model configuration JSON
        model_json = json.dumps({
            "gpt-4o": {
                "name": "GPT-4o",
                "recommended_for": "Detailed analysis"
            },
            "gpt-4o-mini": {
                "name": "GPT-4o Mini",
                "recommended_for": "Quick analysis"
            }
        })
        
        response = client.post('/settings/models/update', data={
            'models_json': model_json
        }, headers={'HX-Request': 'true'})
        
        assert response.status_code == 200
        assert b'success' in response.data
        assert b'Model settings updated successfully' in response.data
        
        # Check that update_env_file was called with correct args
        mock_update.assert_called_once()
        args = mock_update.call_args[0][0]
        assert 'AVAILABLE_MODELS' in args
        
        # Parse the JSON to verify it's correctly formatted
        parsed_models = json.loads(args['AVAILABLE_MODELS'])
        assert 'gpt-4o' in parsed_models
        assert 'gpt-4o-mini' in parsed_models
    
    # Test with invalid JSON
    response = client.post('/settings/models/update', data={
        'models_json': 'invalid json'
    }, headers={'HX-Request': 'true'})
    
    assert response.status_code == 400
    assert b'error' in response.data
    assert b'Invalid JSON format' in response.data
    
    # Test with update failure
    with patch('app.blueprints.settings.update_env_file') as mock_update:
        mock_update.return_value = False
        
        response = client.post('/settings/models/update', data={
            'models_json': '{}'
        }, headers={'HX-Request': 'true'})
        
        assert response.status_code == 500
        assert b'error' in response.data
        assert b'Failed to update model settings' in response.data

def test_env_file_operations():
    """Test environment file operations."""
    # Since we don't want to modify actual .env during tests,
    # we'll test the functions with mocked file operations
    
    from app.blueprints.settings import update_env_file, read_env_file
    
    # Test read_env_file with mocked open
    with patch('builtins.open') as mock_open:
        # Mock file content
        mock_open.return_value.__enter__.return_value.readlines.return_value = [
            "OPENAI_API_KEY=test-key\n",
            "OPENAI_MODEL=gpt-4o\n",
            "# This is a comment\n",
            "OPENAI_TEMPERATURE=0.7\n"
        ]
        
        env_vars = read_env_file()
        
        assert env_vars['OPENAI_API_KEY'] == 'test-key'
        assert env_vars['OPENAI_MODEL'] == 'gpt-4o'
        assert env_vars['OPENAI_TEMPERATURE'] == '0.7'
        assert '# This is a comment' not in env_vars
    
    # Test update_env_file with mocked open and os.path.exists
    with patch('builtins.open'), \
         patch('os.path.exists', return_value=True), \
         patch('shutil.copy2'):
        
        # Test updating existing variables
        result = update_env_file({
            'OPENAI_MODEL': 'gpt-4-turbo',
            'OPENAI_TEMPERATURE': '0.5'
        })
        
        assert result is True 