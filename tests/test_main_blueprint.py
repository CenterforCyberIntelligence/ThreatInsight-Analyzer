import pytest
from unittest.mock import patch, MagicMock
import json

from tests.conftest import captured_templates

def test_index_route(client):
    """Test the index route."""
    with captured_templates(client.application) as templates:
        response = client.get('/')
        
        assert response.status_code == 200
        # Check that the right template was rendered
        assert len(templates) > 0
        template, context = templates[0]
        assert template.name == 'index.html'
        
        # Check that recent analyses were fetched (context should have this data)
        assert 'recent_analyses' in context

def test_about_route(client):
    """Test the about route."""
    with captured_templates(client.application) as templates:
        response = client.get('/about')
        
        assert response.status_code == 200
        # Check that the right template was rendered
        assert len(templates) > 0
        template, context = templates[0]
        assert template.name == 'about.html'
        
        # Check content expectations
        assert b"About" in response.data
        assert b"Artificial Cyber-Intelligence Analyst" in response.data

def test_health_route(client):
    """Test the health check route."""
    # Test when database is healthy
    with patch('app.blueprints.main.db.test_connection', return_value=True):
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['details']['database'] == 'connected'
    
    # Test when database is not healthy
    with patch('app.blueprints.main.db.test_connection', return_value=False):
        response = client.get('/health')
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['status'] == 'unhealthy'
        assert data['details']['database'] == 'disconnected'

def test_sitemap_route(client):
    """Test the sitemap route."""
    with client.application.app_context():
        response = client.get('/sitemap.xml')
        
        assert response.status_code == 200
        assert response.content_type == 'application/xml'
        # Check basic structure of sitemap
        assert b'<?xml version="1.0" encoding="UTF-8"?>' in response.data
        assert b'<urlset' in response.data
        assert b'<url>' in response.data
        # Should include main routes
        assert b'<loc>http://localhost/</loc>' in response.data
        assert b'<loc>http://localhost/about</loc>' in response.data

def test_robots_route(client):
    """Test the robots.txt route."""
    response = client.get('/robots.txt')
    
    assert response.status_code == 200
    assert response.content_type == 'text/plain; charset=utf-8'
    # Check content of robots.txt
    assert b'User-agent: *' in response.data
    assert b'Disallow:' in response.data
    assert b'Sitemap:' in response.data

def test_contact_route(client):
    """Test the contact route."""
    with captured_templates(client.application) as templates:
        response = client.get('/contact')
        
        assert response.status_code == 200
        # Check that the right template was rendered
        assert len(templates) > 0
        template, context = templates[0]
        assert template.name == 'contact.html'
        
        # Check for contact form
        assert b'Contact Us' in response.data
        assert b'<form' in response.data
        assert b'name="email"' in response.data
        assert b'name="subject"' in response.data
        assert b'name="message"' in response.data

def test_contact_form_submission(client):
    """Test contact form submission."""
    # Test successful submission
    with patch('app.blueprints.main.send_contact_email', return_value=True) as mock_send_email:
        form_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': 'This is a test message'
        }
        
        response = client.post('/contact/submit', data=form_data, headers={'HX-Request': 'true'})
        
        assert response.status_code == 200
        assert b'success' in response.data
        assert b'Your message has been sent' in response.data
        
        # Check that the email was sent with correct data
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args[0][0]
        assert call_args['name'] == 'Test User'
        assert call_args['email'] == 'test@example.com'
        assert call_args['subject'] == 'Test Subject'
        assert call_args['message'] == 'This is a test message'
    
    # Test failed submission
    with patch('app.blueprints.main.send_contact_email', return_value=False):
        form_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'Test Subject',
            'message': 'This is a test message'
        }
        
        response = client.post('/contact/submit', data=form_data, headers={'HX-Request': 'true'})
        
        assert response.status_code == 500
        assert b'error' in response.data
        assert b'Failed to send your message' in response.data

def test_contact_form_validation(client):
    """Test contact form validation."""
    # Test with missing name
    form_data = {
        'email': 'test@example.com',
        'subject': 'Test Subject',
        'message': 'This is a test message'
    }
    
    response = client.post('/contact/submit', data=form_data, headers={'HX-Request': 'true'})
    
    assert response.status_code == 400
    assert b'error' in response.data
    assert b'Name is required' in response.data
    
    # Test with invalid email
    form_data = {
        'name': 'Test User',
        'email': 'not-an-email',
        'subject': 'Test Subject',
        'message': 'This is a test message'
    }
    
    response = client.post('/contact/submit', data=form_data, headers={'HX-Request': 'true'})
    
    assert response.status_code == 400
    assert b'error' in response.data
    assert b'Valid email address is required' in response.data
    
    # Test with empty message
    form_data = {
        'name': 'Test User',
        'email': 'test@example.com',
        'subject': 'Test Subject',
        'message': ''
    }
    
    response = client.post('/contact/submit', data=form_data, headers={'HX-Request': 'true'})
    
    assert response.status_code == 400
    assert b'error' in response.data
    assert b'Message is required' in response.data

    # Check that the page title and elements are rendered
    assert b"article" in response.data.lower()
    assert b"analyzer" in response.data.lower()
    assert b"Artificial-Cyber-Intelligence-Analyst" in response.data 