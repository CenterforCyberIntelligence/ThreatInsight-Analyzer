import pytest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
import tempfile
import csv
from io import StringIO

from app.utilities.export import (
    export_analysis_as_json, export_analysis_as_csv, export_analysis_as_pdf,
    export_analysis_as_markdown, get_export_filename
)

def test_get_export_filename():
    """Test the get_export_filename function."""
    # Test with a standard domain and format
    filename = get_export_filename("example.com", "json")
    assert "example.com" in filename
    assert filename.endswith(".json")
    
    # Test with a domain containing special characters
    filename = get_export_filename("special!chars?site.com", "pdf")
    assert "special_chars_site.com" in filename
    assert filename.endswith(".pdf")
    
    # Test with a very long domain name
    long_domain = "extremely" * 20 + ".com"  # Very long domain name
    filename = get_export_filename(long_domain, "csv")
    assert len(filename) < 255  # Ensure filename is not too long for filesystem
    assert filename.endswith(".csv")
    
    # Test with None domain
    filename = get_export_filename(None, "markdown")
    assert "analysis" in filename
    assert filename.endswith(".md")

def test_export_analysis_as_json():
    """Test exporting analysis as JSON."""
    # Sample analysis data
    analysis_data = {
        "summary": "Test summary",
        "source_evaluation": {
            "reliability": "High",
            "credibility": "Medium"
        },
        "threat_actors": ["Actor1", "Actor2"],
        "mitre_techniques": ["T1234", "T5678"]
    }
    
    # Test with file path provided
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Export to the temporary file
        result = export_analysis_as_json(analysis_data, "example.com", temp_path)
        
        # Check result
        assert result["success"] is True
        assert result["file_path"] == temp_path
        
        # Verify file contents
        with open(temp_path, 'r') as f:
            exported_data = json.load(f)
            assert exported_data == analysis_data
    
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    # Test without file path (should create in temp directory)
    with patch('tempfile.gettempdir', return_value='/tmp'), \
         patch('builtins.open', mock_open()) as mock_file:
        
        result = export_analysis_as_json(analysis_data, "example.com")
        
        # Check result
        assert result["success"] is True
        assert "/tmp" in result["file_path"]
        assert "example.com" in result["file_path"]
        
        # Verify file was written
        mock_file.assert_called_once()
        handle = mock_file()
        handle.write.assert_called_once()
        
        # Check JSON content
        written_content = handle.write.call_args[0][0]
        assert "Test summary" in written_content
        assert "Actor1" in written_content
        assert "T1234" in written_content
    
    # Test with error handling
    with patch('builtins.open', side_effect=Exception("Test exception")):
        result = export_analysis_as_json(analysis_data, "example.com")
        
        # Check result
        assert result["success"] is False
        assert "Error" in result["message"]

def test_export_analysis_as_csv():
    """Test exporting analysis as CSV."""
    # Sample analysis data
    analysis_data = {
        "summary": "Test summary",
        "source_evaluation": {
            "reliability": "High",
            "credibility": "Medium",
            "source_type": "Blog"
        },
        "threat_actors": ["Actor1", "Actor2"],
        "mitre_techniques": [
            {"id": "T1234", "name": "Technique 1", "url": "https://attack.mitre.org/techniques/T1234"},
            {"id": "T5678", "name": "Technique 2", "url": "https://attack.mitre.org/techniques/T5678"}
        ],
        "key_insights": ["Insight 1", "Insight 2"],
        "source_bias": "Low bias",
        "intelligence_gaps": ["Gap 1", "Gap 2"],
        "critical_infrastructure_sectors": {
            "Energy Sector": 4,
            "Financial Services Sector": 2
        }
    }
    
    # Test with file path provided
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Export to the temporary file
        result = export_analysis_as_csv(analysis_data, "example.com", temp_path)
        
        # Check result
        assert result["success"] is True
        assert result["file_path"] == temp_path
        
        # Verify file contents
        with open(temp_path, 'r', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            # Check headers and some content rows
            assert "Category" in rows[0]
            assert "Value" in rows[0]
            
            # Check for key content
            found_items = set()
            for row in rows:
                if len(row) >= 2:
                    if row[0] == "Summary":
                        assert row[1] == "Test summary"
                        found_items.add("summary")
                    elif row[0] == "Reliability":
                        assert row[1] == "High"
                        found_items.add("reliability")
                    elif row[0] == "Threat Actor":
                        if row[1] == "Actor1":
                            found_items.add("actor1")
                        elif row[1] == "Actor2":
                            found_items.add("actor2")
                    elif row[0] == "MITRE Technique":
                        if "T1234" in row[1]:
                            found_items.add("mitre1")
                        elif "T5678" in row[1]:
                            found_items.add("mitre2")
            
            # Check that all expected items were found
            assert "summary" in found_items
            assert "reliability" in found_items
            assert "actor1" in found_items
            assert "actor2" in found_items
            assert "mitre1" in found_items
            assert "mitre2" in found_items
            
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    # Test without file path (should create in temp directory)
    with patch('tempfile.gettempdir', return_value='/tmp'), \
         patch('builtins.open', mock_open()) as mock_file:
        
        result = export_analysis_as_csv(analysis_data, "example.com")
        
        # Check result
        assert result["success"] is True
        assert "/tmp" in result["file_path"]
        assert "example.com" in result["file_path"]
        
        # Verify file was created
        mock_file.assert_called_once()
    
    # Test with error handling
    with patch('builtins.open', side_effect=Exception("Test exception")):
        result = export_analysis_as_csv(analysis_data, "example.com")
        
        # Check result
        assert result["success"] is False
        assert "Error" in result["message"]

def test_export_analysis_as_markdown():
    """Test exporting analysis as Markdown."""
    # Sample analysis data
    analysis_data = {
        "summary": "Test summary",
        "source_evaluation": {
            "reliability": "High",
            "credibility": "Medium",
            "source_type": "Blog"
        },
        "threat_actors": ["Actor1", "Actor2"],
        "mitre_techniques": [
            {"id": "T1234", "name": "Technique 1", "url": "https://attack.mitre.org/techniques/T1234"},
            {"id": "T5678", "name": "Technique 2", "url": "https://attack.mitre.org/techniques/T5678"}
        ],
        "key_insights": ["Insight 1", "Insight 2"],
        "source_bias": "Low bias",
        "intelligence_gaps": ["Gap 1", "Gap 2"],
        "critical_infrastructure_sectors": {
            "Energy Sector": 4,
            "Financial Services Sector": 2
        }
    }
    
    # Test with file path provided
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Export to the temporary file
        result = export_analysis_as_markdown(analysis_data, "example.com", temp_path)
        
        # Check result
        assert result["success"] is True
        assert result["file_path"] == temp_path
        
        # Verify file contents
        with open(temp_path, 'r') as f:
            content = f.read()
            
            # Check for key sections and formatting
            assert "# Threat Intelligence Analysis: example.com" in content
            assert "## Summary" in content
            assert "Test summary" in content
            assert "## Source Evaluation" in content
            assert "**Reliability:** High" in content
            assert "## Threat Actors" in content
            assert "* Actor1" in content
            assert "* Actor2" in content
            assert "## MITRE ATT&CK Techniques" in content
            assert "[T1234: Technique 1](https://attack.mitre.org/techniques/T1234)" in content
            assert "## Critical Infrastructure Sectors" in content
            assert "Energy Sector: 4/5" in content
    
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    # Test without file path (should create in temp directory)
    with patch('tempfile.gettempdir', return_value='/tmp'), \
         patch('builtins.open', mock_open()) as mock_file:
        
        result = export_analysis_as_markdown(analysis_data, "example.com")
        
        # Check result
        assert result["success"] is True
        assert "/tmp" in result["file_path"]
        assert "example.com" in result["file_path"]
        
        # Verify file was created
        mock_file.assert_called_once()
    
    # Test with error handling
    with patch('builtins.open', side_effect=Exception("Test exception")):
        result = export_analysis_as_markdown(analysis_data, "example.com")
        
        # Check result
        assert result["success"] is False
        assert "Error" in result["message"]

@pytest.mark.skip(reason="PDF generation requires external libraries that may not be available in CI")
def test_export_analysis_as_pdf():
    """Test exporting analysis as PDF."""
    # This test is marked to skip by default as PDF generation often requires
    # additional dependencies that might not be available in CI environments.
    # When running locally with all dependencies installed, remove the skip marker.
    
    # Sample analysis data
    analysis_data = {
        "summary": "Test summary",
        "source_evaluation": {
            "reliability": "High",
            "credibility": "Medium",
            "source_type": "Blog"
        },
        "threat_actors": ["Actor1", "Actor2"],
        "mitre_techniques": [
            {"id": "T1234", "name": "Technique 1", "url": "https://attack.mitre.org/techniques/T1234"},
            {"id": "T5678", "name": "Technique 2", "url": "https://attack.mitre.org/techniques/T5678"}
        ],
        "key_insights": ["Insight 1", "Insight 2"]
    }
    
    # Use mock to avoid actually generating PDF
    with patch('app.utilities.export.generate_pdf') as mock_generate_pdf, \
         patch('tempfile.gettempdir', return_value='/tmp'):
        
        # Mock the PDF generation to return a success status
        mock_generate_pdf.return_value = True
        
        result = export_analysis_as_pdf(analysis_data, "example.com")
        
        # Check result
        assert result["success"] is True
        assert "/tmp" in result["file_path"]
        assert "example.com" in result["file_path"]
        
        # Verify PDF generation was attempted
        mock_generate_pdf.assert_called_once()
    
    # Test with error handling
    with patch('app.utilities.export.generate_pdf', side_effect=Exception("Test exception")):
        result = export_analysis_as_pdf(analysis_data, "example.com")
        
        # Check result
        assert result["success"] is False
        assert "Error" in result["message"] 