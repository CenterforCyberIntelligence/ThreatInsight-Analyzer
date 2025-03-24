"""
Indicator Extractor Module
==========================

This module specializes in extracting cybersecurity indicators of compromise (IOCs) from article content.
It uses regular expressions and validation rules to identify and extract various types of indicators,
including IP addresses, domains, URLs, file hashes, email addresses, CVEs, and MITRE ATT&CK techniques.

Key features:
- Comprehensive regular expression patterns for different indicator types
- Validation and filtering to reduce false positives
- Support for multiple indicator formats (IPv4, IPv6, MD5, SHA1, SHA256, etc.)
- Exclusion of common false positives and self-references
- Formatting of extracted indicators for display in the UI

This module plays a critical role in the threat intelligence analysis process by automatically
identifying actionable technical indicators that security teams can use for threat hunting
and defensive measures.
"""

import re
from typing import Dict, List, Set, Optional, Any
import ipaddress
from urllib.parse import urlparse

from app.utilities.logger import debug, info, warning

# Common valid TLDs for more accurate domain matching
VALID_TLDS = [
    # Infrastructure TLDs
    "com", "net", "org", "edu", "gov", "mil", "int",
    # Generic TLDs
    "info", "biz", "name", "pro", "mobi", "app", "io", "ai", "dev", "cloud",
    # Country code TLDs (most common)
    "us", "uk", "ca", "au", "de", "fr", "jp", "cn", "ru", "br", "in", "it", "nl", 
    "es", "ch", "se", "no", "fi", "dk", "ie", "at", "be", "nz", "sg", "ae",
    # Security specific
    "security", "secure", "protection", "defense", "cyber", "tech"
]

# Common file extensions to exclude from domain matches
FILE_EXTENSIONS = [
    "exe", "dll", "sys", "bat", "cmd", "vbs", "ps1", "msi", "jar", "py", "js", 
    "docx", "doc", "pdf", "xls", "xlsx", "ppt", "pptx", "txt", "csv", "json", "xml",
    "html", "htm", "css", "jpg", "jpeg", "png", "gif", "bmp", "svg", "mp3", "mp4", 
    "avi", "mov", "wmv", "zip", "rar", "7z", "tar", "gz", "log", "ini", "cfg"
]

# Regular expressions for various indicator types
REGEX_PATTERNS = {
    # IPv4 address pattern
    "ipv4": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
    
    # IPv6 address pattern (simplified)
    "ipv6": r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b|\b(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}\b|\b(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}\b|\b(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}\b|\b(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}\b|\b(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}\b|\b[0-9a-fA-F]{1,4}:(?::[0-9a-fA-F]{1,4}){1,6}\b|\b:(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)\b|\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b",
    
    # Email address pattern
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    
    # Domain pattern
    "domain": r"\b(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+(?:" + "|".join(VALID_TLDS) + r")\b",
    
    # URL pattern
    "url": r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*\??[/\w\.-=&%]*",
    
    # CVE pattern (Common Vulnerabilities and Exposures)
    "cve": r"\bCVE-\d{4}-\d{4,}\b",
    
    # File hash patterns
    "md5": r"\b[a-fA-F0-9]{32}\b",
    "sha1": r"\b[a-fA-F0-9]{40}\b",
    "sha256": r"\b[a-fA-F0-9]{64}\b",
    
    # MITRE ATT&CK Technique pattern
    "mitre_technique": r"\b[Tt](?:actic )?(\d{4})(?:\.(\d{3}))?\b"
}

# Common false positives to filter out (especially for domains and IPs)
FALSE_POSITIVES = {
    "ipv4": [
        "0.0.0.0", "127.0.0.1", "255.255.255.255",
        # Version numbers and other common patterns that match IPv4 format
        "1.0.0.1", "1.1.1.1", "8.8.8.8", "8.8.4.4"
    ],
    "domain": [
        # Common examples used in documentation
        "example.com", "domain.com", "test.com", "company.com",
        # Common placeholder domains
        "yourcompany.com", "attacker.com", "victim.com"
    ],
    "url": [
        # Generic URLs
        "http://example.com", "https://example.com", 
        "http://www.example.com", "https://www.example.com"
    ]
}

def extract_indicators(content: str, url: str = None) -> Dict[str, List[str]]:
    """
    Extract indicators of compromise, CVEs, and MITRE ATT&CK techniques from article content.
    
    This function scans the provided text content to identify and extract various types of
    cybersecurity indicators, filtering out common false positives and the source URL itself.
    It uses regex patterns defined in REGEX_PATTERNS to match different indicator types.
    
    Args:
        content: The article text to analyze
        url: The source URL (to exclude from the results to avoid self-references)
        
    Returns:
        Dictionary of extracted indicators by type, with each type mapped to a list of
        unique indicator values
    """
    debug("Starting extraction of indicators from article content")
    
    # Initialize results dictionary
    results = {
        "ipv4": set(),
        "ipv6": set(),
        "email": set(),
        "domain": set(),
        "url": set(),
        "cve": set(),
        "md5": set(),
        "sha1": set(),
        "sha256": set(),
        "mitre_technique": set()
    }
    
    # Extract the article's domain to avoid self-references
    article_domain = None
    if url:
        try:
            parsed_url = urlparse(url)
            article_domain = parsed_url.netloc.lower()
            debug(f"Article domain: {article_domain}")
        except Exception as e:
            warning(f"Could not parse article URL: {url}, error: {e}")
    
    # Extract indicators using regular expressions
    for indicator_type, pattern in REGEX_PATTERNS.items():
        matches = re.findall(pattern, content, re.IGNORECASE)
        debug(f"Found {len(matches)} potential {indicator_type} matches")
        
        # Process MITRE ATT&CK techniques differently since they have groups
        if indicator_type == "mitre_technique":
            for match in matches:
                if isinstance(match, tuple):
                    # For techniques with subtechniques
                    technique_id = f"T{match[0]}"
                    if len(match) > 1 and match[1]:
                        technique_id += f".{match[1]}"
                    results[indicator_type].add(technique_id)
                else:
                    # For simple techniques without subtechniques
                    technique_id = f"T{match}"
                    results[indicator_type].add(technique_id)
            continue
        
        # Process other indicator types
        for match in matches:
            # Skip false positives and article self-references
            if indicator_type in FALSE_POSITIVES and match.lower() in [fp.lower() for fp in FALSE_POSITIVES[indicator_type]]:
                continue
                
            # Additional validation for specific types
            if indicator_type == "ipv4":
                try:
                    ipaddress.IPv4Address(match)
                    results[indicator_type].add(match)
                except ValueError:
                    continue
            elif indicator_type == "ipv6":
                try:
                    ipaddress.IPv6Address(match)
                    results[indicator_type].add(match)
                except ValueError:
                    continue
            elif indicator_type == "domain":
                # Skip if domain is part of the article URL to avoid self-references
                if article_domain and match.lower() in article_domain:
                    continue
                
                # Extra validation to exclude filenames with extensions
                parts = match.split('.')
                if len(parts) > 1 and parts[-1].lower() in FILE_EXTENSIONS:
                    debug(f"Skipping file extension as domain: {match}")
                    continue
                    
                results[indicator_type].add(match)
            elif indicator_type == "url":
                # Skip if URL is the article URL to avoid self-references
                if url and url.lower() == match.lower():
                    continue
                # Skip if URL contains the article domain to avoid self-references
                if article_domain and article_domain in match.lower():
                    continue
                results[indicator_type].add(match)
            else:
                results[indicator_type].add(match)
    
    # Convert sets to lists for JSON serialization
    for indicator_type in results:
        results[indicator_type] = sorted(list(results[indicator_type]))
        debug(f"Extracted {len(results[indicator_type])} {indicator_type} indicators")
    
    info(f"Extraction complete. Found indicators: {sum(len(indicators) for indicators in results.values())}")
    return results

def validate_and_clean_indicators(indicators: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Apply additional validation and cleaning to extracted indicators.
    
    This function performs further validation and standardization of extracted indicators
    to ensure they meet format requirements and filter out additional false positives
    that weren't caught in the initial extraction.
    
    Args:
        indicators: Dictionary of extracted indicators by type
        
    Returns:
        Cleaned dictionary of indicators with standardized formats
    """
    clean_indicators = {}
    
    for indicator_type, values in indicators.items():
        clean_values = []
        
        for value in values:
            # Additional validation based on indicator type
            if indicator_type == "cve":
                # Ensure proper CVE format
                if re.match(r'^CVE-\d{4}-\d{4,}$', value, re.IGNORECASE):
                    clean_values.append(value.upper())  # Standardize format
            elif indicator_type == "mitre_technique":
                # Ensure proper MITRE technique format
                if re.match(r'^T\d{4}(?:\.\d{3})?$', value):
                    clean_values.append(value)
            elif indicator_type in ["md5", "sha1", "sha256"]:
                # Filter out values that look like version numbers
                if not re.match(r'^[0-9\.]+$', value):
                    clean_values.append(value.lower())
            else:
                clean_values.append(value)
        
        clean_indicators[indicator_type] = clean_values
    
    return clean_indicators

def format_indicators_for_display(indicators: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Format extracted indicators for display in the UI.
    
    This function organizes the extracted indicators into categories for better presentation
    in the user interface, adding counts and grouping related indicator types together.
    
    Args:
        indicators: Dictionary of extracted indicators by type
        
    Returns:
        Formatted dictionary with category grouping, indicator values, and counts
        suitable for display in the UI
    """
    formatted = {
        "categories": [
            {
                "name": "Network Indicators",
                "types": [
                    {"type": "IPv4 Addresses", "indicator_values": indicators["ipv4"], "count": len(indicators["ipv4"])},
                    {"type": "IPv6 Addresses", "indicator_values": indicators["ipv6"], "count": len(indicators["ipv6"])},
                    {"type": "Domains", "indicator_values": indicators["domain"], "count": len(indicators["domain"])},
                    {"type": "URLs", "indicator_values": indicators["url"], "count": len(indicators["url"])}
                ]
            },
            {
                "name": "File Indicators",
                "types": [
                    {"type": "MD5 Hashes", "indicator_values": indicators["md5"], "count": len(indicators["md5"])},
                    {"type": "SHA1 Hashes", "indicator_values": indicators["sha1"], "count": len(indicators["sha1"])},
                    {"type": "SHA256 Hashes", "indicator_values": indicators["sha256"], "count": len(indicators["sha256"])}
                ]
            },
            {
                "name": "Other Indicators",
                "types": [
                    {"type": "Email Addresses", "indicator_values": indicators["email"], "count": len(indicators["email"])},
                    {"type": "CVE IDs", "indicator_values": indicators["cve"], "count": len(indicators["cve"])},
                    {"type": "MITRE ATT&CK Techniques", "indicator_values": indicators["mitre_technique"], "count": len(indicators["mitre_technique"])}
                ]
            }
        ],
        "total_count": sum(len(indicators[itype]) for itype in indicators)
    }
    
    return formatted 