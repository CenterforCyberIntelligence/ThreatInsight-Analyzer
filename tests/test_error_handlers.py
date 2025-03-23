import pytest
from unittest.mock import patch, MagicMock
from flask import template_rendered

from tests.conftest import captured_templates

def test_404_error_handler(client):
    """Test the 404 error handler."""
    # Access a non-existent route to trigger a 404
    with captured_templates(client.application) as templates:
        response = client.get('/non-existent-route')
        
        assert response.status_code == 404
        # Check that the right template was rendered
        assert len(templates) > 0
        template, context = templates[0]
        assert template.name == 'errors/404.html'
        
        # Check response content
        assert b"Page Not Found" in response.data
        assert b"The page you requested could not be found" in response.data

def test_500_error_handler(client):
    """Test the 500 error handler."""
    # Create a route that raises an exception to trigger a 500 error
    @client.application.route('/test-500')
    def trigger_500():
        raise Exception("Test exception")
    
    with captured_templates(client.application) as templates:
        response = client.get('/test-500')
        
        assert response.status_code == 500
        # Check that the right template was rendered
        assert len(templates) > 0
        template, context = templates[0]
        assert template.name == 'errors/500.html'
        
        # Check response content
        assert b"Server Error" in response.data
        assert b"An unexpected error occurred" in response.data

def test_429_error_handler(client):
    """Test the 429 error handler."""
    # Create a route that raises a 429 error
    @client.application.route('/test-429')
    def trigger_429():
        from werkzeug.exceptions import TooManyRequests
        raise TooManyRequests("Too many requests")
    
    with captured_templates(client.application) as templates:
        response = client.get('/test-429')
        
        assert response.status_code == 429
        # Check that the right template was rendered
        assert len(templates) > 0
        template, context = templates[0]
        assert template.name == 'errors/429.html'
        
        # Check response content
        assert b"Rate Limit Exceeded" in response.data
        assert b"You have made too many requests" in response.data

def test_403_error_handler(client):
    """Test the 403 error handler."""
    # Create a route that raises a 403 error
    @client.application.route('/test-403')
    def trigger_403():
        from werkzeug.exceptions import Forbidden
        raise Forbidden("Forbidden")
    
    with captured_templates(client.application) as templates:
        response = client.get('/test-403')
        
        assert response.status_code == 403
        # Check that the right template was rendered
        assert len(templates) > 0
        template, context = templates[0]
        assert template.name == 'errors/403.html'
        
        # Check response content
        assert b"Access Forbidden" in response.data
        assert b"You do not have permission to access" in response.data

def test_400_error_handler(client):
    """Test the 400 error handler."""
    # Create a route that raises a 400 error
    @client.application.route('/test-400')
    def trigger_400():
        from werkzeug.exceptions import BadRequest
        raise BadRequest("Bad request")
    
    with captured_templates(client.application) as templates:
        response = client.get('/test-400')
        
        assert response.status_code == 400
        # Check that the right template was rendered
        assert len(templates) > 0
        template, context = templates[0]
        assert template.name == 'errors/400.html'
        
        # Check response content
        assert b"Bad Request" in response.data
        assert b"The server could not understand your request" in response.data

def test_error_handling_with_htmx(client):
    """Test error handling with HTMX requests."""
    # Test with HX-Request header for 404
    with captured_templates(client.application) as templates:
        response = client.get('/non-existent-route', headers={'HX-Request': 'true'})
        
        assert response.status_code == 404
        # For HTMX requests, check that we still get appropriate error message
        # but not a full HTML page
        assert b"Page Not Found" in response.data
        # Should be a short response, not a full template
        assert len(response.data) < 500
    
    # Create a route that raises an exception for 500 error with HTMX
    @client.application.route('/test-500-htmx')
    def trigger_500_htmx():
        raise Exception("Test exception")
    
    # Test with HX-Request header for 500
    with captured_templates(client.application) as templates:
        response = client.get('/test-500-htmx', headers={'HX-Request': 'true'})
        
        assert response.status_code == 500
        # For HTMX requests, check for appropriate error message
        assert b"Server Error" in response.data
        assert b"An unexpected error occurred" in response.data
        # Should be a short response, not a full template
        assert len(response.data) < 500

def test_custom_error_page_context(client):
    """Test that error pages receive appropriate context data."""
    # Create a route that raises a custom exception with specific attributes
    @client.application.route('/test-custom-error')
    def trigger_custom_error():
        from werkzeug.exceptions import HTTPException
        error = HTTPException("Custom error message")
        error.code = 400
        error.name = "Custom Error"
        error.description = "This is a custom error description"
        raise error
    
    with captured_templates(client.application) as templates:
        response = client.get('/test-custom-error')
        
        assert response.status_code == 400
        # Check that the right template was rendered with proper context
        assert len(templates) > 0
        template, context = templates[0]
        assert template.name == 'errors/400.html'
        
        # Check context data passed to template
        assert context['error'].name == "Custom Error"
        assert context['error'].description == "This is a custom error description"
        
        # Check response content includes custom error
        assert b"Custom Error" in response.data
        assert b"This is a custom error description" in response.data 