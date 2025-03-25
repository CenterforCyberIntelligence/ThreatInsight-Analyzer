import pytest
from app.utilities.sanitizers import sanitize_input

def test_sanitize_input():
    """Test the sanitize_input function."""
    # Test with regular string
    assert sanitize_input("hello world") == "hello world"
    
    # Test with None
    assert sanitize_input(None) is None
    
    # Test with non-string
    assert sanitize_input(123) == 123
    
    # Test with URL-encoded string
    assert sanitize_input("hello%20world") == "hello world"
    
    # Test with HTML content - quotes are converted to entities
    assert sanitize_input("<script>alert('XSS')</script>") == "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;"
    
    # Test with HTML content and allow_html=True
    assert sanitize_input("<b>bold text</b>", allow_html=True) == "<b>bold text</b>"
    
    # Test with NULL bytes
    assert sanitize_input("hello\0world") == "helloworld"
    
    # Test with combined attacks
    assert sanitize_input("<script>alert('XSS')</script>%20\0test") == "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt; test" 