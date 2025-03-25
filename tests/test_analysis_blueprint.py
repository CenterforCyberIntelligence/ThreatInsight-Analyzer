import pytest
from unittest.mock import patch, MagicMock
import json
import re
from contextlib import contextmanager
from flask import template_rendered
import requests

from app.blueprints.analysis import validate_url
from tests.conftest import captured_templates

def test_validate_url():
    """Test URL validation function."""
    # Valid URLs
    with patch('requests.head') as mock_head:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        assert validate_url("https://example.com")[0] is True
        assert validate_url("https://example.org/blog/article")[0] is True
        assert validate_url("http://test.com/index.html?param=value")[0] is True
    
    # Invalid URLs - missing protocol
    valid, error = validate_url("example.com")
    assert valid is False
    assert "Invalid URL format" in error
    
    # Invalid URLs - unsupported protocol
    valid, error = validate_url("ftp://example.com")
    assert valid is False
    assert "Only HTTP and HTTPS protocols are supported" in error
    
    # Invalid URLs - blocked domain
    # Mock the HTTP check to pass and test domain blocking
    with patch('requests.head') as mock_head:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        with patch('app.blueprints.analysis.BLOCKED_DOMAINS', ['example-malicious-site.com']):
            valid, error = validate_url("https://example-malicious-site.com")
            assert valid is False
            assert "domain is blocked" in error
    
    # Invalid URLs - empty
    valid, error = validate_url("")
    assert valid is False
    assert "URL is required" in error
    
    # Invalid URLs - None
    valid, error = validate_url(None)
    assert valid is False
    assert "URL is required" in error
    
    # Test non-200 response
    with patch('requests.head') as mock_head:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response
        
        valid, error = validate_url("https://example.com/not-found")
        assert valid is False
        assert "non-200 status code" in error
    
    # Test HEAD not supported (405) but GET returns 200
    with patch('requests.head') as mock_head, patch('requests.get') as mock_get:
        mock_head_response = MagicMock()
        mock_head_response.status_code = 405
        mock_head.return_value = mock_head_response
        
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get.return_value = mock_get_response
        
        assert validate_url("https://example.com/head-not-supported")[0] is True
    
    # Test connection error
    with patch('requests.head') as mock_head:
        mock_head.side_effect = requests.exceptions.ConnectionError("Failed to establish connection")
        
        valid, error = validate_url("https://non-existent-site.com")
        assert valid is False
        assert "Failed to connect to URL" in error

def test_analyze_endpoint(client, mock_requests_get, mock_openai_completion):
    """Test the analyze endpoint."""
    # Test with valid URL
    response = client.post('/analyze', data={
        'url': 'https://example.com/article',
        'model': 'gpt-4o'
    }, headers={'HX-Request': 'true'})
    
    assert response.status_code == 200
    # Check that we get the loading template
    assert b'analysis-loading' in response.data
    assert b'url=https://example.com/article' in response.data
    assert b'model=gpt-4o' in response.data
    
    # Test without HX-Request header (should return JSON)
    response = client.post('/analyze', data={
        'url': 'https://example.com/article',
        'model': 'gpt-4o'
    })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'started'
    assert data['url'] == 'https://example.com/article'
    assert data['model'] == 'gpt-4o'
    
    # Test with invalid URL
    response = client.post('/analyze', data={
        'url': 'invalid-url',
        'model': 'gpt-4o'
    }, headers={'HX-Request': 'true'})
    
    assert response.status_code == 400
    assert b'analysis-error' in response.data
    assert b'Invalid URL format' in response.data

def test_analysis_status_endpoint(client):
    """Test the analysis status endpoint."""
    # Test with valid URL and step
    response = client.get('/analysis/status', query_string={
        'url': 'https://example.com/article',
        'step': 'extract',
        'model': 'gpt-4o'
    })
    
    assert response.status_code == 200
    assert b'analysis-loading' in response.data
    assert b'step=extract' in response.data
    
    # Test with invalid URL
    response = client.get('/analysis/status', query_string={
        'url': 'invalid-url',
        'step': 'extract',
        'model': 'gpt-4o'
    })
    
    assert response.status_code == 400
    assert b'analysis-error' in response.data
    assert b'Invalid URL format' in response.data

def test_analysis_result_endpoint(client, sample_article_data):
    """Test the analysis result endpoint."""
    # First store some test data
    with patch('app.blueprints.analysis.get_analysis_by_url') as mock_get_analysis:
        # Mock data returned from the database
        mock_get_analysis.return_value = {
            'id': 1,
            'url': sample_article_data['url'],
            'title': sample_article_data['title'],
            'content_length': sample_article_data['content_length'],
            'model': sample_article_data['model'],
            'raw_text': sample_article_data['raw_analysis'],
            'created_at': '2023-06-01T10:00:00',
            'structured_data': json.dumps(sample_article_data['structured_analysis'])
        }
        
        # Mock the indicators call
        with patch('app.blueprints.analysis.get_indicators_by_url') as mock_get_indicators:
            mock_get_indicators.return_value = {
                'ipv4': ['192.168.1.100'],
                'cve': ['CVE-2023-1234']
            }
            
            # Test with valid URL
            with client.application.app_context():
                with captured_templates(client.application) as templates:
                    response = client.get('/analysis/result', query_string={
                        'url': sample_article_data['url'],
                        'model': sample_article_data['model']
                    })
                    
                    assert response.status_code == 200
                    # Check that the right template was rendered
                    assert len(templates) > 0
                    template, context = templates[0]
                    assert template.name == 'partials/analysis_result.html'
                    # Check context data
                    assert context['url'] == sample_article_data['url']
                    assert context['title'] == sample_article_data['title']
                    assert context['model'] == sample_article_data['model']
                    assert 'analysis' in context
                    assert 'analyzed_at' in context
                    assert 'cached' in context
                    assert context['cached'] is True
    
    # Test with invalid URL
    response = client.get('/analysis/result', query_string={
        'url': 'invalid-url',
        'model': 'gpt-4o'
    })
    
    assert response.status_code == 400
    assert b'analysis-error' in response.data
    assert b'Invalid URL format' in response.data

def test_analysis_refresh_endpoint(client, sample_article_data):
    """Test the analysis refresh endpoint."""
    # Setup mocks for the refresh flow
    with patch('app.blueprints.analysis.get_analysis_by_url') as mock_get_analysis, \
         patch('app.blueprints.analysis.extract_article_content') as mock_extract, \
         patch('app.blueprints.analysis.analyze_article') as mock_analyze, \
         patch('app.blueprints.analysis.update_analysis') as mock_update:
        
        # Mock existing analysis data
        mock_get_analysis.return_value = {
            'id': 1,
            'url': sample_article_data['url'],
            'title': sample_article_data['title'],
            'content_length': sample_article_data['content_length'],
            'model': sample_article_data['model'],
            'raw_text': sample_article_data['raw_analysis'],
            'created_at': '2023-06-01T10:00:00',
            'structured_data': json.dumps(sample_article_data['structured_analysis'])
        }
        
        # Mock the extraction and analysis
        mock_extract.return_value = "Updated article content"
        mock_analyze.return_value = sample_article_data['structured_analysis']
        mock_update.return_value = True
        
        # Test with valid URL
        response = client.get('/analysis/refresh', query_string={
            'url': sample_article_data['url'],
            'model': 'gpt-4o'
        }, headers={'HX-Request': 'true'})
        
        assert response.status_code == 200
        assert b'analysis-loading' in response.data
        
        # Ensure the mocks were called with correct args
        mock_get_analysis.assert_called_once_with(sample_article_data['url'])
        mock_extract.assert_called_once()
        mock_analyze.assert_called_once()
        mock_update.assert_called_once()
    
    # Test with invalid URL
    response = client.get('/analysis/refresh', query_string={
        'url': 'invalid-url',
        'model': 'gpt-4o'
    })
    
    assert response.status_code == 400
    assert b'analysis-error' in response.data
    assert b'Invalid URL format' in response.data

def test_recent_analyses_endpoint(client):
    """Test the recent analyses endpoint."""
    # Setup mock for recent analyses
    with patch('app.blueprints.analysis.get_recent_analyses') as mock_get_recent:
        mock_get_recent.return_value = [
            {
                'id': 1,
                'url': 'https://example.com/article1',
                'title': 'Article 1',
                'created_at': '2023-06-01T10:00:00'
            },
            {
                'id': 2,
                'url': 'https://example.com/article2',
                'title': 'Article 2',
                'created_at': '2023-06-02T10:00:00'
            }
        ]
        
        # Test endpoint
        with client.application.app_context():
            with captured_templates(client.application) as templates:
                response = client.get('/recent-analyses')
                
                assert response.status_code == 200
                # Check that the right template was rendered
                assert len(templates) > 0
                template, context = templates[0]
                assert template.name == 'partials/recent_analyses.html'
                assert len(context['analyses']) == 2
                assert context['analyses'][0]['title'] == 'Article 1'
                assert context['analyses'][1]['title'] == 'Article 2'

def test_analyze_form_endpoint(client):
    """Test the analyze form endpoint."""
    with client.application.app_context():
        with captured_templates(client.application) as templates:
            response = client.get('/analyze-form')
            
            assert response.status_code == 200
            # Check that the right template was rendered
            assert len(templates) > 0
            template, context = templates[0]
            assert template.name == 'partials/analyze_form.html'
            assert 'models' in context

def test_full_analysis_workflow(client, mock_requests_get, mock_openai_completion):
    """Test the full analysis workflow from start to finish."""
    with patch('app.blueprints.analysis.store_analysis') as mock_store, \
         patch('app.blueprints.analysis.store_indicators') as mock_store_indicators:
        
        # Mock successful storage
        mock_store.return_value = True
        mock_store_indicators.return_value = True
        
        # Step 1: Start the analysis
        response = client.post('/analyze', data={
            'url': 'https://example.com/workflow-test',
            'model': 'gpt-4o'
        }, headers={'HX-Request': 'true'})
        
        assert response.status_code == 200
        assert b'analysis-loading' in response.data
        assert b'step=extract' in response.data
        
        # Step 2: Check status (extraction complete)
        response = client.get('/analysis/status', query_string={
            'url': 'https://example.com/workflow-test',
            'step': 'extract',
            'model': 'gpt-4o'
        })
        
        assert response.status_code == 200
        assert b'analysis-loading' in response.data
        
        # Step 3: Check status (analysis complete)
        response = client.get('/analysis/status', query_string={
            'url': 'https://example.com/workflow-test',
            'step': 'analyze',
            'model': 'gpt-4o'
        })
        
        assert response.status_code == 200
        assert b'analysis-loading' in response.data
        
        # Step 4: Check result (should attempt to get cached result which doesn't exist yet,
        # then extract and analyze)
        with patch('app.blueprints.analysis.get_analysis_by_url') as mock_get_analysis:
            # First return None (no cached result) then return a result after "analysis"
            mock_get_analysis.side_effect = [
                None,  # First call - no cached result
                {      # Second call - after analysis
                    'id': 999,
                    'url': 'https://example.com/workflow-test',
                    'title': 'Workflow Test Article',
                    'content_length': 500,
                    'model': 'gpt-4o',
                    'raw_text': 'Test analysis result',
                    'created_at': '2023-06-01T10:00:00',
                    'structured_data': json.dumps({
                        'summary': 'Test summary',
                        'source_evaluation': {
                            'reliability': 'Medium',
                            'credibility': 'Medium',
                            'source_type': 'Blog'
                        },
                        'mitre_techniques': [],
                        'key_insights': ['Test insight'],
                        'potential_bias': [],
                        'govt_relevance': {'score': 3, 'justification': 'Test'},
                        'sectors': {'information_technology': 4}
                    })
                }
            ]
            
            # Mock indicators
            with patch('app.blueprints.analysis.get_indicators_by_url') as mock_get_indicators:
                mock_get_indicators.return_value = {
                    'ipv4': [],
                    'domain': [],
                    'url': [],
                    'cve': [],
                    'md5': [],
                    'sha1': [],
                    'sha256': [],
                    'email': [],
                    'mitre_technique': []
                }
                
                response = client.get('/analysis/result', query_string={
                    'url': 'https://example.com/workflow-test',
                    'model': 'gpt-4o'
                })
                
                assert response.status_code == 200
                assert b'Test summary' in response.data or b'Workflow Test Article' in response.data
                
                # Check that store_analysis was called
                mock_store.assert_called_once()
                # Check that store_indicators was called
                mock_store_indicators.assert_called_once() 