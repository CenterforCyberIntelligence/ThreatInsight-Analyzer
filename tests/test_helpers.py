import pytest
from unittest.mock import patch, MagicMock
import json
import re
from datetime import datetime
import os

from app.utilities.helpers import (
    format_timestamp, format_seconds, parse_domain_from_url, 
    generate_slug, sanitize_filename, format_json_for_display,
    truncate_text, calculate_percentages, calculate_size_reduction,
    format_currency
)

def test_format_timestamp():
    """Test the format_timestamp function."""
    # Test with a specific timestamp
    timestamp = 1625097600  # Thursday, July 1, 2021
    formatted = format_timestamp(timestamp)
    assert "Jul 01, 2021" in formatted
    
    # Test with the current time
    current_time = datetime.now().timestamp()
    formatted = format_timestamp(current_time)
    # Should contain today's year
    assert str(datetime.now().year) in formatted
    
    # Test with None
    formatted = format_timestamp(None)
    assert formatted == "N/A"
    
    # Test with invalid input
    formatted = format_timestamp("invalid")
    assert formatted == "N/A"

def test_format_seconds():
    """Test the format_seconds function."""
    # Test with various second values
    assert format_seconds(30) == "30 seconds"
    assert format_seconds(60) == "1 minute"
    assert format_seconds(90) == "1 minute 30 seconds"
    assert format_seconds(3600) == "1 hour"
    assert format_seconds(3660) == "1 hour 1 minute"
    assert format_seconds(3690) == "1 hour 1 minute 30 seconds"
    assert format_seconds(7200) == "2 hours"
    assert format_seconds(7290) == "2 hours 1 minute 30 seconds"
    
    # Test with zero or negative values
    assert format_seconds(0) == "0 seconds"
    assert format_seconds(-10) == "0 seconds"  # Should handle negative values gracefully
    
    # Test with None
    assert format_seconds(None) == "N/A"
    
    # Test with invalid input
    assert format_seconds("invalid") == "N/A"

def test_parse_domain_from_url():
    """Test the parse_domain_from_url function."""
    # Test with various URLs
    assert parse_domain_from_url("https://www.example.com/page") == "example.com"
    assert parse_domain_from_url("http://subdomain.example.co.uk/") == "example.co.uk"
    assert parse_domain_from_url("example.org") == "example.org"
    assert parse_domain_from_url("https://blog.example.net/article?id=123") == "example.net"
    
    # Test with IP addresses
    assert parse_domain_from_url("http://192.168.1.1/") == "192.168.1.1"
    assert parse_domain_from_url("https://[2001:db8::1]/path") == "2001:db8::1"
    
    # Test with None or empty string
    assert parse_domain_from_url(None) == ""
    assert parse_domain_from_url("") == ""
    
    # Test with invalid URL
    assert parse_domain_from_url("not_a_url") == "not_a_url"

def test_generate_slug():
    """Test the generate_slug function."""
    # Test with standard text
    assert generate_slug("Hello World") == "hello-world"
    assert generate_slug("This is a Test") == "this-is-a-test"
    
    # Test with special characters
    assert generate_slug("Hello, World!") == "hello-world"
    assert generate_slug("Email: user@example.com") == "email-user-example-com"
    
    # Test with extra spaces and dashes
    assert generate_slug("  Multiple   Spaces  ") == "multiple-spaces"
    assert generate_slug("Already-has-dashes") == "already-has-dashes"
    
    # Test with non-ASCII characters
    assert generate_slug("Café") == "cafe"
    assert generate_slug("über") == "uber"
    
    # Test with empty string
    assert generate_slug("") == ""
    
    # Test with None
    assert generate_slug(None) == ""

def test_sanitize_filename():
    """Test the sanitize_filename function."""
    # Test with standard text
    assert sanitize_filename("Hello World") == "Hello_World"
    assert sanitize_filename("This is a Test") == "This_is_a_Test"
    
    # Test with special characters
    assert sanitize_filename("File: name?with*invalid<chars>") == "File_name_with_invalid_chars"
    assert sanitize_filename("report/2021/06.txt") == "report_2021_06.txt"
    
    # Test with empty string
    assert sanitize_filename("") == ""
    
    # Test with None
    assert sanitize_filename(None) == ""
    
    # Test with file extension
    assert sanitize_filename("document.pdf") == "document.pdf"
    assert sanitize_filename("bad:file.name.txt") == "bad_file.name.txt"

def test_format_json_for_display():
    """Test the format_json_for_display function."""
    # Test with a simple dictionary
    data = {"key": "value", "number": 123}
    formatted = format_json_for_display(data)
    assert "key" in formatted
    assert "value" in formatted
    assert "123" in formatted
    
    # Test with nested structure
    data = {"person": {"name": "John", "age": 30}, "active": True}
    formatted = format_json_for_display(data)
    assert "person" in formatted
    assert "name" in formatted
    assert "John" in formatted
    assert "30" in formatted
    assert "active" in formatted
    assert "true" in formatted.lower()
    
    # Test proper indentation
    data = {"level1": {"level2": {"level3": "deep"}}}
    formatted = format_json_for_display(data)
    assert re.search(r'\s+"level2":', formatted)
    assert re.search(r'\s+\s+"level3":', formatted)
    
    # Test with None
    assert format_json_for_display(None) == "null"
    
    # Test with JSON string input
    json_str = '{"test": "value"}'
    # Should convert to dict then format
    formatted = format_json_for_display(json_str)
    assert "test" in formatted
    assert "value" in formatted
    
    # Test with invalid JSON string
    assert format_json_for_display("not json") == "not json"

def test_truncate_text():
    """Test the truncate_text function."""
    # Test with text shorter than max length
    assert truncate_text("Short text", 20) == "Short text"
    
    # Test with text longer than max length
    assert truncate_text("This is a long text that should be truncated", 20) == "This is a long text..."
    
    # Test with text exactly at max length
    text = "Exactly twenty chars"  # 20 characters
    assert truncate_text(text, 20) == text
    
    # Test with different ellipsis
    assert truncate_text("Long text to truncate", 10, "...more") == "Long text...more"
    
    # Test with None
    assert truncate_text(None, 10) == ""
    
    # Test with empty string
    assert truncate_text("", 10) == ""

def test_calculate_percentages():
    """Test the calculate_percentages function."""
    # Test with standard values
    data = {"A": 10, "B": 20, "C": 30}
    percentages = calculate_percentages(data)
    assert percentages["A"] == 16.67  # 10/60 = 0.1667
    assert percentages["B"] == 33.33  # 20/60 = 0.3333
    assert percentages["C"] == 50.0   # 30/60 = 0.5
    
    # Test with zero total
    data = {"A": 0, "B": 0, "C": 0}
    percentages = calculate_percentages(data)
    assert percentages["A"] == 0
    assert percentages["B"] == 0
    assert percentages["C"] == 0
    
    # Test with negative values (should be treated as 0)
    data = {"A": -5, "B": 10, "C": 15}
    percentages = calculate_percentages(data)
    assert percentages["A"] == 0
    assert percentages["B"] == 40.0   # 10/25 = 0.4
    assert percentages["C"] == 60.0   # 15/25 = 0.6
    
    # Test with empty dict
    assert calculate_percentages({}) == {}
    
    # Test with None
    assert calculate_percentages(None) == {}

def test_calculate_size_reduction():
    """Test the calculate_size_reduction function."""
    # Test with standard values
    assert calculate_size_reduction(1000, 800) == 20.0  # 20% reduction
    assert calculate_size_reduction(500, 250) == 50.0   # 50% reduction
    assert calculate_size_reduction(100, 100) == 0.0    # No reduction
    
    # Test with larger new size (should return 0)
    assert calculate_size_reduction(100, 150) == 0.0
    
    # Test with zero original size
    assert calculate_size_reduction(0, 0) == 0.0
    
    # Test with negative values
    assert calculate_size_reduction(-100, -50) == 0.0
    
    # Test with None
    assert calculate_size_reduction(None, 100) == 0.0
    assert calculate_size_reduction(100, None) == 0.0

def test_format_currency():
    """Test the format_currency function."""
    # Test with various values
    assert format_currency(0) == "$0.00"
    assert format_currency(1) == "$1.00"
    assert format_currency(1.5) == "$1.50"
    assert format_currency(1000) == "$1,000.00"
    assert format_currency(1234.56) == "$1,234.56"
    
    # Test with negative values
    assert format_currency(-10) == "-$10.00"
    assert format_currency(-1234.56) == "-$1,234.56"
    
    # Test with different currency symbol
    assert format_currency(100, "€") == "€100.00"
    assert format_currency(1000, "£") == "£1,000.00"
    
    # Test with None
    assert format_currency(None) == "$0.00"
    
    # Test with invalid input
    assert format_currency("invalid") == "$0.00" 