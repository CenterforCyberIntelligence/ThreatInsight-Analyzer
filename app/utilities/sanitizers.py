import html
import re
import urllib.parse
import logging

def sanitize_input(value, allow_html=False):
    """Sanitize user input to prevent injection attacks.
    
    Args:
        value: The input value to sanitize
        allow_html: Whether to allow HTML tags in the input
        
    Returns:
        Sanitized value with potential attacks neutralized
    """
    if value is None:
        return None
        
    if not isinstance(value, str):
        return value
    
    # Store original value for comparison
    original_value = value
        
    # Decode URL encoding
    value = urllib.parse.unquote(value)
    
    # Check for NULL bytes before removing them
    has_null_bytes = '\0' in value
    if has_null_bytes:
        logging.warning(f"NULL byte detected in input: {repr(value)}")
    
    # Remove NULL bytes
    value = value.replace('\0', '')
    
    # Log if value changed due to sanitization (other than NULL byte removal)
    if value != original_value and not has_null_bytes:
        logging.info(f"Input sanitized: {repr(original_value)} -> {repr(value)}")
    
    # Escape HTML unless explicitly allowed
    if not allow_html:
        value = html.escape(value)
    
    return value 