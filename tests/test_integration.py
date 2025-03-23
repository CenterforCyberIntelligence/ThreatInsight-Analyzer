import pytest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock
import time

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

@pytest.mark.slow
def test_full_analysis_workflow_integration(client, mock_requests_get, mock_openai_completion):
    """Test the full analysis workflow from URL submission to analysis completion."""
    # Configure the mocks
    mock_html_content = """
    <html>
        <head><title>Test Cyber Threat Article</title></head>
        <body>
            <h1>New Threat Actor Discovered</h1>
            <p>Security researchers have discovered a new threat actor called "TestGroup" 
            using the T1566 phishing technique to compromise systems.</p>
            <p>The group has been targeting energy sector companies with spear-phishing emails
            containing malicious attachments.</p>
            <p>Indicators of compromise include the IP address 192.168.1.100 and 
            domain malicious-test-domain.com.</p>
        </body>
    </html>
    """
    
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.text = mock_html_content
    mock_requests_get.return_value.content = mock_html_content.encode('utf-8')
    
    # Mock OpenAI API response for analysis
    mock_analysis_response = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "summary": "Security researchers discovered a new threat actor called TestGroup using phishing techniques to target energy sector companies.",
                    "source_evaluation": {
                        "reliability": "Medium",
                        "credibility": "Medium",
                        "source_type": "Blog"
                    },
                    "threat_actors": ["TestGroup"],
                    "mitre_techniques": [
                        {"id": "T1566", "name": "Phishing", "url": "https://attack.mitre.org/techniques/T1566"}
                    ],
                    "key_insights": ["New threat actor discovered targeting energy sector", "Using phishing as primary attack vector"],
                    "source_bias": "Low bias",
                    "intelligence_gaps": ["Attribution details", "Campaign timeline"],
                    "critical_infrastructure_sectors": {
                        "Energy Sector": 5,
                        "Information Technology Sector": 2,
                        "Financial Services Sector": 1
                    }
                })
            }
        }]
    }
    
    # Set up OpenAI API mock response
    mock_openai_completion.return_value = mock_analysis_response
    
    # Step 1: Submit URL for analysis
    response = client.post('/analyze', data={
        'url': 'https://test-cyber-site.com/article1',
        'model': 'gpt-4o'
    })
    
    # Check redirection to status page
    assert response.status_code == 302
    location = response.headers.get('Location')
    assert '/analysis/status?url=' in location
    
    # Step 2: Check analysis status
    status_url = location
    response = client.get(status_url)
    assert response.status_code == 200
    assert b'Article extraction complete' in response.data
    assert b'Analysis in progress' in response.data
    
    # Step 3: Get analysis results
    result_url = status_url.replace('/status', '/result')
    response = client.get(result_url)
    assert response.status_code == 200
    
    # Check that the analysis data is displayed correctly
    assert b'TestGroup' in response.data
    assert b'T1566: Phishing' in response.data
    assert b'Energy Sector' in response.data
    assert b'Medium' in response.data  # Reliability rating
    
    # Check that extracted indicators are present
    assert b'192.168.1.100' in response.data  # IP address
    assert b'malicious-test-domain.com' in response.data  # Domain
    
    # Step 4: Test export functionality
    # Create a temporary directory for exports
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the tempfile.gettempdir to return our test directory
        with patch('tempfile.gettempdir', return_value=temp_dir):
            # Test JSON export
            response = client.get(f'/analysis/export?url=https://test-cyber-site.com/article1&format=json')
            assert response.status_code == 200
            
            # Verify the response has proper headers for download
            assert 'application/json' in response.headers.get('Content-Type', '')
            assert 'attachment' in response.headers.get('Content-Disposition', '')
            
            # Test we're getting valid JSON
            data = json.loads(response.data)
            assert data['summary'] is not None
            assert 'TestGroup' in data['threat_actors']
            assert len(data['mitre_techniques']) > 0

@pytest.mark.slow
def test_database_persistence_integration():
    """Test that analyses are properly stored and retrieved from the database."""
    from app.utilities.database import (
        connect_db, close_db, get_analysis_by_url, store_analysis,
        get_recent_analyses, update_analysis
    )
    
    # Initialize test DB
    db_path = ':memory:'  # Use in-memory database for testing
    connection = connect_db(db_path)
    
    try:
        # Create necessary tables if they don't exist (connect_db should have done this)
        # Add test data
        test_url = 'https://test-site.com/integration-test'
        test_analysis = {
            'summary': 'Test summary for integration test',
            'source_evaluation': {
                'reliability': 'High',
                'credibility': 'Medium',
                'source_type': 'Cybersecurity Vendor'
            },
            'threat_actors': ['TestActor'],
            'mitre_techniques': [
                {'id': 'T1234', 'name': 'Test Technique', 'url': 'https://attack.mitre.org/techniques/T1234'}
            ],
            'key_insights': ['Test insight 1', 'Test insight 2'],
            'extraction_time': 1.5,
            'analysis_time': 2.5
        }
        
        # Store analysis in DB
        store_result = store_analysis(test_url, 'Sample article text', test_analysis, connection=connection)
        assert store_result is True
        
        # Retrieve analysis by URL
        stored_analysis = get_analysis_by_url(test_url, connection=connection)
        assert stored_analysis is not None
        assert stored_analysis['url'] == test_url
        assert stored_analysis['analysis']['summary'] == 'Test summary for integration test'
        assert 'TestActor' in stored_analysis['analysis']['threat_actors']
        
        # Update analysis
        updated_analysis = test_analysis.copy()
        updated_analysis['summary'] = 'Updated summary'
        update_result = update_analysis(test_url, updated_analysis, connection=connection)
        assert update_result is True
        
        # Verify update
        retrieved_analysis = get_analysis_by_url(test_url, connection=connection)
        assert retrieved_analysis['analysis']['summary'] == 'Updated summary'
        
        # Test get_recent_analyses
        # Add another analysis to test ordering
        store_analysis(
            'https://test-site.com/second-article',
            'Another test article text',
            {**test_analysis, 'summary': 'Second article summary'},
            connection=connection
        )
        
        # Get recent analyses
        recent = get_recent_analyses(limit=2, connection=connection)
        assert len(recent) == 2
        # Most recent should be first
        assert recent[0]['url'] == 'https://test-site.com/second-article'
        assert recent[1]['url'] == test_url
        
    finally:
        # Clean up
        close_db(connection)

@pytest.mark.slow
def test_article_extraction_to_analysis_integration():
    """Test integration between article extraction and analysis components."""
    from app.utilities.article_extractor import extract_article_content
    from app.utilities.article_analyzer import analyze_article
    
    # Mock the HTML content and requests
    html_content = """
    <html>
        <body>
            <h1>Test Article Title</h1>
            <div class="content">
                <p>This is a test article about a cybersecurity threat.</p>
                <p>A threat actor group named "TestAPT" has been using malware to target organizations.</p>
                <p>They utilize spear phishing (T1566) and command and control (T1105) techniques.</p>
            </div>
        </body>
    </html>
    """
    
    with patch('requests.get') as mock_requests_get, \
         patch('app.utilities.article_analyzer.openai_completion') as mock_openai_completion:
        
        # Configure request mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_content
        mock_response.content = html_content.encode('utf-8')
        mock_requests_get.return_value = mock_response
        
        # Configure OpenAI mock
        mock_openai_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "summary": "Test article about TestAPT threat actor using spear phishing and C2 techniques.",
                        "source_evaluation": {
                            "reliability": "Medium",
                            "credibility": "Medium"
                        },
                        "threat_actors": ["TestAPT"],
                        "mitre_techniques": [
                            {"id": "T1566", "name": "Phishing", "url": "https://attack.mitre.org/techniques/T1566"},
                            {"id": "T1105", "name": "Ingress Tool Transfer", "url": "https://attack.mitre.org/techniques/T1105"}
                        ]
                    })
                }
            }]
        }
        mock_openai_completion.return_value = mock_openai_response
        
        # Test the extraction
        extraction_result = extract_article_content('https://test-site.com/security-article')
        assert extraction_result['success'] is True
        extracted_text = extraction_result['content']
        assert "This is a test article" in extracted_text
        assert "TestAPT" in extracted_text
        
        # Test the analysis with the extracted content
        analysis_result = analyze_article(extracted_text)
        assert analysis_result is not None
        assert "TestAPT" in analysis_result['threat_actors']
        assert len(analysis_result['mitre_techniques']) == 2
        # Verify specific MITRE techniques were identified
        technique_ids = [t['id'] for t in analysis_result['mitre_techniques']]
        assert "T1566" in technique_ids
        assert "T1105" in technique_ids

@pytest.mark.slow
def test_indicator_extraction_integration():
    """Test integration between article extraction and indicator extraction."""
    from app.utilities.article_extractor import extract_article_content
    from app.utilities.indicator_extractor import extract_indicators
    
    # Mock HTML with various indicators
    html_content = """
    <html>
        <body>
            <h1>Test Article Title</h1>
            <div class="content">
                <p>This article contains various indicators of compromise.</p>
                <p>IP addresses: 192.168.1.1, 10.0.0.1, 8.8.8.8</p>
                <p>Domains: evil-domain.com, malware.test.org</p>
                <p>Email: attacker@evil-domain.com</p>
                <p>Hashes: 5f4dcc3b5aa765d61d8327deb882cf99 (MD5),
                   da39a3ee5e6b4b0d3255bfef95601890afd80709 (SHA1)</p>
                <p>CVEs: CVE-2021-44228, cve-2020-1234</p>
            </div>
        </body>
    </html>
    """
    
    with patch('requests.get') as mock_requests_get:
        # Configure request mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_content
        mock_response.content = html_content.encode('utf-8')
        mock_requests_get.return_value = mock_response
        
        # Extract the article content
        extracted_text = extract_article_content('https://test-site.com/indicator-article')
        assert extracted_text is not None
        assert isinstance(extracted_text, str)
        assert len(extracted_text) > 100
        
        # Extract indicators from the content
        indicators = extract_indicators(extracted_text)
        
        # Verify all types of indicators were extracted
        assert len(indicators['ipv4']) >= 2  # The validation may have filtered out one of the IPs
        assert '192.168.1.1' in indicators['ipv4']
        assert '10.0.0.1' in indicators['ipv4']
        
        assert len(indicators['domain']) >= 2
        assert 'evil-domain.com' in indicators['domain']
        assert 'malware.test.org' in indicators['domain']
        
        assert len(indicators['email']) >= 1
        assert 'attacker@evil-domain.com' in indicators['email']
        
        # Check hash values by specific types, not a combined 'hash' key
        assert len(indicators['md5']) >= 1
        assert '5f4dcc3b5aa765d61d8327deb882cf99' in indicators['md5']
        
        assert len(indicators['sha1']) >= 1
        assert 'da39a3ee5e6b4b0d3255bfef95601890afd80709' in indicators['sha1']
        
        assert len(indicators['cve']) >= 2
        assert 'CVE-2021-44228' in indicators['cve']
        # Check for either uppercase or lowercase version
        assert any(cve.upper() == 'CVE-2020-1234' for cve in indicators['cve']) 