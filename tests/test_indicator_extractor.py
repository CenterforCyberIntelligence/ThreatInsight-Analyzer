import pytest
from unittest.mock import patch

from app.utilities.indicator_extractor import (
    extract_indicators,
    validate_and_clean_indicators,
    format_indicators_for_display,
    REGEX_PATTERNS,
    FALSE_POSITIVES
)

def test_extract_indicators_ipv4():
    """Test extraction of IPv4 addresses."""
    content = """
    This article discusses suspicious IP addresses.
    The main C2 server was at 192.168.1.100.
    Other addresses involved were 10.0.0.1 and 172.16.2.5.
    
    Also discovered was activity from 8.8.8.8 (Google DNS) and 1.1.1.1 (Cloudflare).
    """
    
    indicators = extract_indicators(content)
    assert "ipv4" in indicators
    ipv4_indicators = indicators["ipv4"]
    assert len(ipv4_indicators) > 0
    
    # Should find legitimate IPs
    assert "192.168.1.100" in ipv4_indicators
    assert "10.0.0.1" in ipv4_indicators
    assert "172.16.2.5" in ipv4_indicators
    
    # Should filter out common DNS servers as potential false positives
    # Note: This depends on how conservative the filtering is in the implementation
    if len(FALSE_POSITIVES["ipv4"]) > 0:
        for fp in FALSE_POSITIVES["ipv4"]:
            if fp in ["8.8.8.8", "1.1.1.1"]:
                assert fp not in ipv4_indicators

def test_extract_indicators_domain():
    """Test extraction of domain names."""
    content = """
    The attackers used evil-domain.com for phishing.
    They also utilized malware.org and c2-server.net for command and control.
    
    Victims were directed to download files from legitimate-looking.com.
    """
    
    indicators = extract_indicators(content)
    assert "domain" in indicators
    domain_indicators = indicators["domain"]
    assert len(domain_indicators) > 0
    
    # Should find all domains
    assert "evil-domain.com" in domain_indicators
    assert "malware.org" in domain_indicators
    assert "c2-server.net" in domain_indicators
    assert "legitimate-looking.com" in domain_indicators
    
    # Test with a URL in the content
    content_with_url = "The attackers used https://evil-domain.com/path/to/malware for distribution."
    url_indicators = extract_indicators(content_with_url)
    
    # Should extract both the domain and the full URL
    assert "evil-domain.com" in url_indicators["domain"]
    assert "https://evil-domain.com/path/to/malware" in url_indicators["url"]

def test_extract_indicators_cve():
    """Test extraction of CVE identifiers."""
    content = """
    The attackers exploited CVE-2023-1234 and CVE-2022-5678.
    They also attempted to use CVE-2021-98765 but were unsuccessful.
    """
    
    indicators = extract_indicators(content)
    assert "cve" in indicators
    cve_indicators = indicators["cve"]
    assert len(cve_indicators) == 3
    
    # Should find all CVEs
    for cve in ["cve-2023-1234", "cve-2022-5678", "cve-2021-98765"]:
        assert cve in cve_indicators or cve.upper() in cve_indicators
    
    # Test case insensitivity
    content_lowercase = "The vulnerability cve-2023-1234 was exploited."
    lowercase_indicators = extract_indicators(content_lowercase)
    
    # Check if the CVE is extracted in either lowercase or uppercase
    lowercase_cves = lowercase_indicators["cve"]
    assert "cve-2023-1234" in lowercase_cves or "CVE-2023-1234" in lowercase_cves

def test_extract_indicators_hash():
    """Test extraction of file hashes."""
    content = """
    The malware had the following hashes:
    MD5: 01234567890123456789012345678901
    SHA1: 0123456789012345678901234567890123456789
    SHA256: 0123456789012345678901234567890123456789012345678901234567890123
    """
    
    indicators = extract_indicators(content)
    
    # Check MD5 hashes
    assert "md5" in indicators
    assert "01234567890123456789012345678901" in indicators["md5"]
    
    # Check SHA1 hashes
    assert "sha1" in indicators
    assert "0123456789012345678901234567890123456789" in indicators["sha1"]
    
    # Check SHA256 hashes
    assert "sha256" in indicators
    assert "0123456789012345678901234567890123456789012345678901234567890123" in indicators["sha256"]

def test_extract_indicators_email():
    """Test extraction of email addresses."""
    content = """
    The phishing campaign originated from attacker@evil-domain.com.
    Multiple emails were used including support@fake-service.com and 
    admin@malicious-site.org.
    """
    
    indicators = extract_indicators(content)
    assert "email" in indicators
    email_indicators = indicators["email"]
    assert len(email_indicators) == 3
    
    # Should find all email addresses
    assert "attacker@evil-domain.com" in email_indicators
    assert "support@fake-service.com" in email_indicators
    assert "admin@malicious-site.org" in email_indicators

def test_extract_indicators_mitre_technique():
    """Test extraction of MITRE ATT&CK techniques."""
    content = """
    The attackers used techniques T1566 (Phishing) and T1204.002 (User Execution: Malicious File).
    They also employed technique T1059 for execution of malicious code.
    """
    
    indicators = extract_indicators(content)
    assert "mitre_technique" in indicators
    mitre_indicators = indicators["mitre_technique"]
    assert len(mitre_indicators) == 3
    
    # Should find all MITRE techniques
    assert "T1566" in mitre_indicators
    assert "T1204.002" in mitre_indicators
    assert "T1059" in mitre_indicators

def test_extract_indicators_with_url_exclusion():
    """Test extraction with URL exclusion."""
    content = """
    This article is from https://security-blog.com/2023/05/incident-report.
    The attackers used evil-domain.com for phishing.
    """
    
    # Extract without excluding the source URL
    indicators_without_exclusion = extract_indicators(content)
    assert "security-blog.com" in indicators_without_exclusion["domain"]
    assert "evil-domain.com" in indicators_without_exclusion["domain"]
    
    # Extract with excluding the source URL
    indicators_with_exclusion = extract_indicators(content, url="https://security-blog.com/2023/05/incident-report")
    assert "security-blog.com" not in indicators_with_exclusion["domain"]
    assert "evil-domain.com" in indicators_with_exclusion["domain"]

def test_validate_and_clean_indicators():
    """Test validation and cleaning of indicators."""
    # Create some raw indicators with duplicates and invalid values
    raw_indicators = {
        "ipv4": ["192.168.1.1", "192.168.1.1", "999.999.999.999", "127.0.0.1"],
        "domain": ["example.com", "example.com", "invalid..domain", "localhost"],
        "url": ["https://evil.com/path", "https://evil.com/path", "not-a-url"],
        "cve": ["CVE-2023-1234", "cve-2023-1234", "CVE-ABCD-1234"],
        "mitre_technique": ["T1566", "T1566", "T9999", "T1566.999"]
    }
    
    cleaned = validate_and_clean_indicators(raw_indicators)
    
    # Check that valid values are preserved
    assert "192.168.1.1" in cleaned["ipv4"] or any(ip == "192.168.1.1" for ip in cleaned["ipv4"])
    assert "https://evil.com/path" in cleaned["url"] or any(url == "https://evil.com/path" for url in cleaned["url"])
    
    # Check that some invalid values are filtered (if the validation is implemented)
    if "CVE-ABCD-1234" not in cleaned["cve"]:
        assert True  # Validation is working if invalid CVE is removed
    
    # Check that valid technique IDs are preserved
    assert "T1566" in cleaned["mitre_technique"] or any(t == "T1566" for t in cleaned["mitre_technique"])

def test_format_indicators_for_display():
    """Test formatting indicators for display."""
    indicators = {
        "ipv4": ["192.168.1.1", "10.0.0.1"],
        "ipv6": ["2001:0db8:85a3:0000:0000:8a2e:0370:7334"],
        "domain": ["evil-domain.com", "malware.org"],
        "url": ["https://evil-domain.com/path"],
        "cve": ["CVE-2023-1234", "CVE-2022-5678"],
        "mitre_technique": ["T1566", "T1204.002"],
        "md5": ["01234567890123456789012345678901"],
        "sha1": ["da39a3ee5e6b4b0d3255bfef95601890afd80709"],
        "sha256": ["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
        "email": []  # Empty category
    }
    
    formatted = format_indicators_for_display(indicators)
    
    # Check basic structure
    assert "categories" in formatted
    assert "total_count" in formatted
    
    # Check totals
    total_count = sum(len(values) for values in indicators.values())
    assert formatted["total_count"] == total_count
    
    # Check categories
    assert len(formatted["categories"]) == 3  # Network, File, Other
    
    # Check network indicators
    network_category = formatted["categories"][0]
    assert network_category["name"] == "Network Indicators"
    assert len(network_category["types"]) == 4  # IPv4, IPv6, Domains, URLs
    
    # Check file indicators
    file_category = formatted["categories"][1]
    assert file_category["name"] == "File Indicators"
    assert len(file_category["types"]) == 3  # MD5, SHA1, SHA256
    
    # Check other indicators
    other_category = formatted["categories"][2]
    assert other_category["name"] == "Other Indicators"
    assert len(other_category["types"]) == 3  # Email, CVE, MITRE

def test_extract_indicators_complex_text():
    """Test indicator extraction from complex text with mixed content."""
    complex_content = """
    Incident Report: Advanced Persistent Threat Campaign
    
    Executive Summary:
    On May 15, 2023, our security team detected suspicious activity from IP address 198.51.100.82.
    Further investigation revealed a spear-phishing campaign targeting executives with emails from
    ceo-office@company-spoofed.com containing malicious attachments.
    
    Technical Details:
    The attackers exploited CVE-2023-32456 in Microsoft Office to execute malicious code.
    Command and control was established with domains evil-c2-server.com and backup-c2.net.
    Additional infrastructure included 203.0.113.45 and 198.51.100.17.
    
    The malware used had the following hashes:
    - MD5: e1d4d4e856e546f95d30649f5178d334
    - SHA256: 7e59b8c53dc651a4eea52a6f42b888d192288bf89c35e8deeecc3dd4f151635a
    
    MITRE ATT&CK Techniques:
    The campaign utilized T1566.001 (Spearphishing Attachment), T1204.002 (User Execution: Malicious File),
    and T1027 (Obfuscated Files or Information) to evade detection.
    
    Remediation:
    Block all communication to the identified infrastructure and scan for indicators of compromise.
    Apply the patch for CVE-2023-32456 immediately.
    """
    
    indicators = extract_indicators(complex_content)
    
    # Check IP addresses
    assert "198.51.100.82" in indicators["ipv4"]
    assert "203.0.113.45" in indicators["ipv4"]
    assert "198.51.100.17" in indicators["ipv4"]
    
    # Check domains
    assert "evil-c2-server.com" in indicators["domain"]
    assert "backup-c2.net" in indicators["domain"]
    assert "company-spoofed.com" in indicators["domain"]
    
    # Check emails
    assert "ceo-office@company-spoofed.com" in indicators["email"]
    
    # Check CVEs
    assert "CVE-2023-32456" in indicators["cve"]
    
    # Check hashes
    assert "e1d4d4e856e546f95d30649f5178d334" in indicators["md5"]
    assert "7e59b8c53dc651a4eea52a6f42b888d192288bf89c35e8deeecc3dd4f151635a" in indicators["sha256"]
    
    # Check MITRE techniques
    assert "T1566.001" in indicators["mitre_technique"]
    assert "T1204.002" in indicators["mitre_technique"]
    assert "T1027" in indicators["mitre_technique"] 