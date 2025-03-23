import pytest
from unittest.mock import patch, Mock
import requests
from bs4 import BeautifulSoup

from app.utilities.article_extractor import (
    extract_article_content, 
    get_domain_specific_headers, 
    extract_by_containers, 
    extract_by_paragraphs, 
    extract_by_text_density, 
    clean_extracted_text
)

def test_get_domain_specific_headers():
    """Test the domain-specific headers generation."""
    # Test with a common domain
    headers = get_domain_specific_headers("example.com")
    assert headers is not None
    assert isinstance(headers, dict)
    assert "User-Agent" in headers
    
    # Test with a security vendor domain
    vendor_headers = get_domain_specific_headers("mandiant.com")
    assert vendor_headers is not None
    assert isinstance(vendor_headers, dict)
    assert "User-Agent" in vendor_headers
    
    # Test with empty domain
    default_headers = get_domain_specific_headers("")
    assert default_headers is not None
    assert isinstance(default_headers, dict)
    assert "User-Agent" in default_headers

def test_extract_article_content_success(mock_requests_get):
    """Test successful article content extraction."""
    url = "https://example.com/article"
    content = extract_article_content(url, verbose=False)
    
    assert content is not None
    assert isinstance(content, str)
    assert "Cybersecurity Threat Report" in content
    assert "CVE-2023-1234" in content
    assert "192.168.1.100" in content

def test_extract_article_content_http_error():
    """Test article extraction with HTTP error."""
    class MockErrorResponse:
        def __init__(self):
            self.status_code = 404
            
        def raise_for_status(self):
            raise requests.exceptions.HTTPError(f"HTTP Status: {self.status_code}")
    
    with patch('requests.get', return_value=MockErrorResponse()):
        content = extract_article_content("https://example.com/not-found", verbose=False)
        assert content is None

def test_extract_article_content_timeout():
    """Test article extraction with timeout error."""
    with patch('requests.get', side_effect=requests.exceptions.Timeout("Request timed out")):
        content = extract_article_content("https://example.com/timeout", verbose=False)
        assert content is None

def test_extract_article_content_connection_error():
    """Test article extraction with connection error."""
    with patch('requests.get', side_effect=requests.exceptions.ConnectionError("Connection error")):
        content = extract_article_content("https://example.com/connection-error", verbose=False)
        assert content is None

def test_extract_article_content_general_exception():
    """Test article extraction with general exception."""
    with patch('requests.get', side_effect=Exception("General error")):
        content = extract_article_content("https://example.com/error", verbose=False)
        assert content is None

def test_extract_by_containers():
    """Test extraction by containers."""
    # Create a sample HTML with article containers
    html = """
    <html>
        <body>
            <article>
                <h1>Test Article</h1>
                <p>This is a test article content.</p>
            </article>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, 'html.parser')
    content = extract_by_containers(soup, verbose=False)
    
    assert content is not None
    assert "Test Article" in content
    assert "This is a test article content" in content
    
    # Test with main container
    html_main = """
    <html>
        <body>
            <main>
                <h1>Test Main Content</h1>
                <p>This is a test main content.</p>
            </main>
        </body>
    </html>
    """
    soup_main = BeautifulSoup(html_main, 'html.parser')
    content_main = extract_by_containers(soup_main, verbose=False)
    
    assert content_main is not None
    assert "Test Main Content" in content_main
    assert "This is a test main content" in content_main
    
    # Test with no containers
    html_no_containers = """
    <html>
        <body>
            <div>
                <p>This is just regular content without containers.</p>
            </div>
        </body>
    </html>
    """
    soup_no_containers = BeautifulSoup(html_no_containers, 'html.parser')
    content_no_containers = extract_by_containers(soup_no_containers, verbose=False)
    
    assert content_no_containers is None or content_no_containers.strip() == ""

def test_extract_by_paragraphs():
    """Test extraction by paragraphs."""
    # Create a sample HTML with paragraphs
    html = """
    <html>
        <body>
            <p>First paragraph with important content.</p>
            <p>Second paragraph with more information.</p>
            <p>Third paragraph concluding the article.</p>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, 'html.parser')
    content = extract_by_paragraphs(soup, verbose=False)
    
    assert content is not None
    assert "First paragraph" in content
    assert "Second paragraph" in content
    assert "Third paragraph" in content
    
    # Test with no paragraphs
    html_no_paragraphs = """
    <html>
        <body>
            <div>Just some text without paragraph tags.</div>
        </body>
    </html>
    """
    soup_no_paragraphs = BeautifulSoup(html_no_paragraphs, 'html.parser')
    content_no_paragraphs = extract_by_paragraphs(soup_no_paragraphs, verbose=False)
    
    assert content_no_paragraphs is None or content_no_paragraphs.strip() == ""

def test_extract_by_text_density():
    """Test extraction by text density."""
    # Create a sample HTML with varying text density
    html = """
    <html>
        <body>
            <div id="header">Site Header</div>
            <div id="content">
                <p>This is a high-density text area with lots of content.</p>
                <p>It contains multiple paragraphs with substantial information.</p>
                <p>The text density in this section should be higher than other parts.</p>
                <p>This should be identified as the main article content.</p>
                <p>Adding more content to ensure word count is above 50.</p>
                <p>The quick brown fox jumps over the lazy dog.</p>
                <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
                <p>Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
            </div>
            <div id="sidebar">
                <p>Small sidebar item 1</p>
                <p>Small sidebar item 2</p>
            </div>
            <div id="footer">Copyright 2023</div>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, 'html.parser')
    content = extract_by_text_density(soup, verbose=False)
    
    assert content is not None
    assert "high-density text area" in content
    assert "multiple paragraphs" in content
    assert "main article content" in content
    
    # Test with minimal content
    html_minimal = """
    <html>
        <body>
            <div>Just a tiny bit of text.</div>
        </body>
    </html>
    """
    soup_minimal = BeautifulSoup(html_minimal, 'html.parser')
    content_minimal = extract_by_text_density(soup_minimal, verbose=False)
    
    # The function should return None for minimal content (< 50 words)
    assert content_minimal is None

def test_clean_extracted_text():
    """Test cleaning extracted text."""
    # Test with extra whitespace
    text_with_whitespace = "  This   has   extra   spaces  \n\n  and newlines.  "
    cleaned = clean_extracted_text(text_with_whitespace)
    assert "This" in cleaned
    assert "has" in cleaned
    assert "extra" in cleaned
    assert "spaces" in cleaned
    assert "and newlines" in cleaned
    # Function only trims whitespace at line edges, not between words
    assert "This   has   extra   spaces" in cleaned
    
    # Test with special characters and HTML entities
    text_with_entities = "This &amp; that &lt; these &gt; those"
    cleaned_entities = clean_extracted_text(text_with_entities)
    assert "This" in cleaned_entities
    assert "that" in cleaned_entities
    assert "these" in cleaned_entities
    assert "those" in cleaned_entities
    
    # Test with empty input
    assert clean_extracted_text("") == ""
    assert clean_extracted_text(None) == ""
    
    # Test with repeated newlines and tabs
    text_with_newlines = "Line 1\n\n\n\n\nLine 2\t\tTabbed"
    cleaned_newlines = clean_extracted_text(text_with_newlines)
    assert "Line 1" in cleaned_newlines
    assert "Line 2\t\tTabbed" in cleaned_newlines  # Tabs within lines are preserved
    assert "\n\n\n\n" not in cleaned_newlines  # Excessive newlines are reduced

def test_multiple_extraction_methods(mock_requests_get):
    """Test article extraction with multiple methods."""
    # Override the mock response for this specific test
    mock_html = """
    <html>
        <head><title>Complex Test Article</title></head>
        <body>
            <!-- No article or main tag to test fallback methods -->
            <div id="content">
                <h1>Cybersecurity Report</h1>
                <p>This is the main content with important information.</p>
                <p>Second paragraph with more details about CVE-2023-5678.</p>
                <p>Third paragraph mentioning IP 10.0.0.1 and domain evil.com.</p>
            </div>
            <div id="sidebar">
                <p>Small sidebar item 1</p>
                <p>Small sidebar item 2</p>
            </div>
        </body>
    </html>
    """
    
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        url = "https://example.com/complex-article"
        content = extract_article_content(url, verbose=False)
        
        assert content is not None
        assert isinstance(content, str)
        assert "Cybersecurity Report" in content
        assert "CVE-2023-5678" in content
        assert "10.0.0.1" in content
        assert "evil.com" in content

def test_extraction_all_methods_fail():
    """Test article extraction when all methods fail."""
    # Create a mock response with minimal content that would cause extraction methods to fail
    mock_html = """
    <html>
        <head><title>Empty Article</title></head>
        <body>
            <!-- No meaningful content -->
            <div></div>
        </body>
    </html>
    """
    
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Should use fallback method that gets all text from body
        url = "https://example.com/empty-article"
        content = extract_article_content(url, verbose=False)
        
        # Since there's no real content, we might get None or empty string
        if content:
            assert content.strip() == "" or "Empty Article" in content

def test_extract_article_verbose_mode():
    """Test article extraction with verbose mode enabled."""
    # Use a basic mock to test the verbose path without actually printing
    mock_html = "<html><body><article>Test verbose content</article></body></html>"
    
    with patch('requests.get') as mock_get, \
         patch('app.utilities.article_extractor.print_status') as mock_print:
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        url = "https://example.com/verbose-test"
        extract_article_content(url, verbose=True)
        
        # Check that print_status was called multiple times with verbose updates
        assert mock_print.call_count > 0
        
        # Extract the first call arguments
        first_call_args = mock_print.call_args_list[0][0]
        assert "Starting enhanced extraction" in first_call_args[0] 