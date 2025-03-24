"""
Helper Utilities Module
======================

This module provides general-purpose utility functions used throughout the application.
These functions handle common tasks such as:
- Formatting timestamps and durations
- Parsing and manipulating URLs and domains
- Generating slugs and sanitizing filenames
- Formatting and displaying data (JSON, text truncation, etc.)
- Calculating percentages and size reductions
- Formatting currency values

These utilities are designed to be simple, pure functions that don't rely on application state
or external services, making them easily testable and reusable across the application.
"""
import re
from datetime import datetime
import json
from typing import Dict, Any, Optional, Union, List

def format_timestamp(timestamp: Optional[Union[int, float]]) -> str:
    """
    Format a Unix timestamp to a human-readable date string.
    
    Converts a numeric Unix timestamp (seconds since epoch) into a formatted
    date string for display purposes. Handles None values gracefully.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        
    Returns:
        Formatted date string (e.g., 'Jan 01, 2023 12:34') or 'N/A' if invalid
    """
    try:
        if timestamp is None:
            return "N/A"
        dt = datetime.fromtimestamp(float(timestamp))
        return dt.strftime("%b %d, %Y %H:%M")
    except (ValueError, TypeError):
        return "N/A"

def format_seconds(seconds: Optional[Union[int, float]]) -> str:
    """
    Format seconds into a human-readable duration string.
    
    Converts a numeric seconds value into a formatted duration string,
    breaking it down into hours, minutes, and seconds as appropriate.
    Handles None values and negative values gracefully.
    
    Args:
        seconds: Number of seconds
        
    Returns:
        Formatted duration string (e.g., '1 hour 30 minutes 45 seconds') or 'N/A' if invalid
    """
    try:
        if seconds is None:
            return "N/A"
        
        seconds = float(seconds)
        if seconds < 0:
            seconds = 0
            
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if hours > 0:
            parts.append(f"{int(hours)} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{int(minutes)} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or (hours == 0 and minutes == 0):
            parts.append(f"{int(seconds)} second{'s' if seconds != 1 else ''}")
            
        return " ".join(parts)
    except (ValueError, TypeError):
        return "N/A"

def parse_domain_from_url(url: Optional[str]) -> str:
    """
    Extract the domain from a URL.
    
    Parses a URL string to extract just the domain name, handling various
    URL formats, protocols, subdomains, and country-specific TLDs appropriately.
    
    Args:
        url: URL string (e.g., 'https://www.example.com/page?query=value')
        
    Returns:
        Domain name (e.g., 'example.com' from 'https://www.example.com/page')
        or empty string if URL is invalid
    """
    if not url:
        return ""
    
    # Remove protocol
    domain = url.lower()
    if "://" in domain:
        domain = domain.split("://", 1)[1]
    
    # Remove path
    domain = domain.split("/", 1)[0]
    
    # Remove subdomain (keep only second-level domain)
    parts = domain.split(".")
    if len(parts) > 2 and not re.match(r'\d+\.\d+\.\d+\.\d+', domain):
        # Check for country code TLDs (e.g., .co.uk, .com.au)
        if len(parts) > 2 and parts[-2] in ["co", "com", "org", "net", "ac", "gov", "edu"]:
            domain = ".".join(parts[-3:])
        else:
            domain = ".".join(parts[-2:])
    
    return domain

def generate_slug(text: Optional[str]) -> str:
    """
    Generate a URL-friendly slug from text.
    
    Converts a text string into a URL-friendly slug by removing special characters,
    converting to lowercase, and replacing spaces with hyphens.
    
    Args:
        text: Input text to convert to a slug
        
    Returns:
        URL-friendly slug or empty string if input is invalid
    """
    if not text:
        return ""
    
    # Convert to lowercase
    slug = text.lower()
    
    # Replace non-alphanumeric with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    
    return slug

def sanitize_filename(filename: Optional[str]) -> str:
    """
    Sanitize a string to be used as a filename.
    
    Removes invalid filename characters and replaces spaces with underscores
    to create a valid filename for any filesystem.
    
    Args:
        filename: Input filename to sanitize
        
    Returns:
        Sanitized filename or empty string if input is invalid
    """
    if not filename:
        return ""
    
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', filename)
    
    # Replace multiple spaces with a single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    
    return sanitized

def format_json_for_display(data: Any) -> str:
    """
    Format JSON data for display.
    
    Pretty-prints JSON data with proper indentation for display purposes.
    Handles both JSON strings and Python data structures that can be serialized to JSON.
    
    Args:
        data: JSON data (dict, list, or JSON string)
        
    Returns:
        Formatted JSON string with proper indentation
    """
    try:
        # If data is a string, try to parse it as JSON
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return data
        
        # Format the JSON with indentation
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception:
        # If anything goes wrong, return the original data as a string
        return str(data)

def truncate_text(text: Optional[str], max_length: int, ellipsis: str = "...") -> str:
    """
    Truncate text to a maximum length, adding ellipsis if needed.
    
    Ensures text doesn't exceed a specified maximum length by cutting it off
    and adding an ellipsis if necessary.
    
    Args:
        text: Input text to truncate
        max_length: Maximum allowed length of the result including ellipsis
        ellipsis: String to append to truncated text (default: "...")
        
    Returns:
        Truncated text with ellipsis if needed, or the original text if short enough
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(ellipsis)] + ellipsis

def calculate_percentages(data: Optional[Dict[str, Union[int, float]]]) -> Dict[str, float]:
    """
    Calculate percentages for a dictionary of values.
    
    Converts a dictionary of numeric values into a dictionary of percentage values
    based on the sum of all values. Handles negative values by filtering them out.
    
    Args:
        data: Dictionary of values to convert to percentages
        
    Returns:
        Dictionary with the same keys but values converted to percentages (0-100)
    """
    if not data:
        return {}
    
    # Filter out negative values and convert to float
    filtered_data = {k: float(v) for k, v in data.items() if v is not None and float(v) >= 0}
    
    # Calculate total
    total = sum(filtered_data.values())
    
    # Calculate percentages
    if total == 0:
        return {k: 0 for k in filtered_data}
    
    return {k: round(v / total * 100, 2) for k, v in filtered_data.items()}

def calculate_size_reduction(original_size: Optional[Union[int, float]], 
                            new_size: Optional[Union[int, float]]) -> float:
    """
    Calculate percentage reduction in size.
    
    Determines how much smaller a new size is compared to an original size,
    expressed as a percentage reduction. Handles edge cases like zero or negative values.
    
    Args:
        original_size: Original size value
        new_size: New (reduced) size value
        
    Returns:
        Percentage reduction (0-100) or 0 if calculation is invalid
    """
    try:
        if original_size is None or new_size is None:
            return 0.0
        
        original_size = float(original_size)
        new_size = float(new_size)
        
        if original_size <= 0:
            return 0.0
        
        if new_size > original_size:
            return 0.0
        
        reduction = (original_size - new_size) / original_size * 100
        return round(reduction, 2)
    except (ValueError, TypeError):
        return 0.0

def format_currency(amount: Optional[Union[int, float]], currency_symbol: str = "$") -> str:
    """
    Format a number as currency.
    
    Formats a numeric value as a currency string with proper thousands separators
    and decimal places. Handles None values and negative amounts.
    
    Args:
        amount: Amount to format
        currency_symbol: Currency symbol to prepend (default: "$")
        
    Returns:
        Formatted currency string (e.g., "$1,234.56")
    """
    try:
        if amount is None:
            amount = 0
        
        amount = float(amount)
        
        if amount < 0:
            return f"-{currency_symbol}{abs(amount):,.2f}"
        
        return f"{currency_symbol}{amount:,.2f}"
    except (ValueError, TypeError):
        return f"{currency_symbol}0.00" 