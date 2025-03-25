import pytest
import json
import time
from unittest.mock import patch, Mock, MagicMock
import os

from app.utilities.article_analyzer import (
    analyze_article,
    parse_analysis_response,
    parse_mitre_technique
)

def test_analyze_article_success(mock_openai_completion):
    """Test successful article analysis with structured output."""
    content = "This is a test article about cybersecurity threats. It includes mentions of CVE-2023-1234 vulnerability."
    url = "https://example.com/article"
    
    # Test structured output
    result = analyze_article(content, url, structured=True, verbose=False)
    assert result is not None
    assert isinstance(result, dict)
    assert "text" in result
    assert "structured" in result
    assert "api_details" in result
    
    # Verify structured data
    structured_data = result["structured"]
    assert "summary" in structured_data
    assert "source_evaluation" in structured_data
    assert "threat_actors" in structured_data
    assert "mitre_techniques" in structured_data
    assert "key_insights" in structured_data
    assert "source_bias" in structured_data
    assert "intelligence_gaps" in structured_data
    assert "critical_infrastructure_sectors" in structured_data
    assert "metadata" in structured_data
    
    # Verify API details
    api_details = result["api_details"]
    assert "model" in api_details
    assert "input_tokens" in api_details
    assert "output_tokens" in api_details
    assert "total_tokens" in api_details

def test_analyze_article_api_error():
    """Test article analysis with API error."""
    content = "This is a test article about cybersecurity threats."
    url = "https://example.com/article"
    
    with patch('openai.chat.completions.create', side_effect=Exception("API error")):
        with pytest.raises(Exception) as exc_info:
            analyze_article(content, url, verbose=False)
        assert str(exc_info.value) == "API error"

def test_analyze_article_rate_limit_retry():
    """Test article analysis with rate limit and retry logic."""
    content = "This is a test article about cybersecurity threats."
    url = "https://example.com/article"
    
    # Simulate a rate limit error then success
    responses = [
        MagicMock(side_effect=Exception("Rate limit exceeded")),
        {
            "output_text": json.dumps({
                "summary": "Test summary after retry",
                "source_evaluation": {
                    "reliability": "High",
                    "credibility": "High",
                    "source_type": "Cybersecurity Vendor"
                },
                "threat_actors": [],
                "mitre_techniques": [],
                "key_insights": [],
                "source_bias": "None",
                "intelligence_gaps": [],
                "critical_infrastructure_sectors": {
                    "threat_to_national_security": 1,
                    "chemical_sector": 1,
                    "commercial_facilities_sector": 1,
                    "communications_sector": 1,
                    "critical_manufacturing_sector": 1,
                    "dams_sector": 1,
                    "defense_industrial_base_sector": 1,
                    "emergency_services_sector": 1,
                    "energy_sector": 1,
                    "financial_services_sector": 1,
                    "food_and_agriculture_sector": 1,
                    "government_services_and_facilities_sector": 1,
                    "healthcare_and_public_health_sector": 1,
                    "information_technology_sector": 1,
                    "nuclear_reactors_materials_and_waste_sector": 1,
                    "transportation_systems_sector": 1,
                    "water_and_wastewater_systems_sector": 1
                }
            }),
            "usage": {
                "input_tokens": 100,
                "output_tokens": 100,
                "total_tokens": 200
            }
        }
    ]
    
    with patch('time.sleep', return_value=None), \
         patch('openai.responses.create', side_effect=responses):
        # Should retry and succeed
        result = analyze_article(content, url, max_retries=2, retry_delay=0.1, verbose=False)
        assert result is not None
        assert isinstance(result, dict)
        assert "structured" in result
        assert result["structured"]["summary"] == "Test summary after retry"

def test_analyze_article_content_truncation():
    """Test article analysis with content truncation for long articles."""
    # Create a very long article that would exceed token limits
    long_content = "This is a test sentence. " * 2000  # Approximately 10,000 words
    url = "https://example.com/long-article"
    
    # Mock the OpenAI API response
    mock_response = {
        "output_text": json.dumps({
            "summary": "Summary of truncated content",
            "source_evaluation": {
                "reliability": "High",
                "credibility": "High",
                "source_type": "Cybersecurity Vendor"
            },
            "threat_actors": [],
            "mitre_techniques": [],
            "key_insights": [],
            "source_bias": "None",
            "intelligence_gaps": [],
            "critical_infrastructure_sectors": {
                "threat_to_national_security": 1,
                "chemical_sector": 1,
                "commercial_facilities_sector": 1,
                "communications_sector": 1,
                "critical_manufacturing_sector": 1,
                "dams_sector": 1,
                "defense_industrial_base_sector": 1,
                "emergency_services_sector": 1,
                "energy_sector": 1,
                "financial_services_sector": 1,
                "food_and_agriculture_sector": 1,
                "government_services_and_facilities_sector": 1,
                "healthcare_and_public_health_sector": 1,
                "information_technology_sector": 1,
                "nuclear_reactors_materials_and_waste_sector": 1,
                "transportation_systems_sector": 1,
                "water_and_wastewater_systems_sector": 1
            }
        }),
        "usage": {
            "input_tokens": 100,
            "output_tokens": 100,
            "total_tokens": 200
        }
    }
    
    with patch('openai.responses.create', return_value=mock_response):
        result = analyze_article(long_content, url, verbose=False)
        assert result is not None
        assert isinstance(result, dict)
        assert "structured" in result
        assert result["structured"]["summary"] == "Summary of truncated content"

def test_analyze_article_with_temperature(mock_openai_completion):
    """Test article analysis with custom temperature setting."""
    content = "This is a test article about cybersecurity threats."
    url = "https://example.com/article"
    
    with patch('openai.responses.create') as mock_create:
        mock_create.return_value = {
            "output_text": json.dumps({
                "summary": "Test summary",
                "source_evaluation": {
                    "reliability": "High",
                    "credibility": "High",
                    "source_type": "Cybersecurity Vendor"
                },
                "threat_actors": [],
                "mitre_techniques": [],
                "key_insights": [],
                "source_bias": "None",
                "intelligence_gaps": [],
                "critical_infrastructure_sectors": {
                    "threat_to_national_security": 1,
                    "chemical_sector": 1,
                    "commercial_facilities_sector": 1,
                    "communications_sector": 1,
                    "critical_manufacturing_sector": 1,
                    "dams_sector": 1,
                    "defense_industrial_base_sector": 1,
                    "emergency_services_sector": 1,
                    "energy_sector": 1,
                    "financial_services_sector": 1,
                    "food_and_agriculture_sector": 1,
                    "government_services_and_facilities_sector": 1,
                    "healthcare_and_public_health_sector": 1,
                    "information_technology_sector": 1,
                    "nuclear_reactors_materials_and_waste_sector": 1,
                    "transportation_systems_sector": 1,
                    "water_and_wastewater_systems_sector": 1
                }
            }),
            "usage": {
                "input_tokens": 100,
                "output_tokens": 100,
                "total_tokens": 200
            }
        }
        
        # Call with custom temperature
        analyze_article(content, url, temperature=0.8, verbose=False)
        
        # Extract the temperature from the API call
        args, kwargs = mock_create.call_args
        assert kwargs["temperature"] == 0.8
        
        # Test with environment variable override
        with patch.dict(os.environ, {"OPENAI_TEMPERATURE": "0.5"}):
            analyze_article(content, url, temperature=0.8, verbose=False)
            args, kwargs = mock_create.call_args
            assert kwargs["temperature"] == 0.5

def test_analyze_article_verbose_mode():
    """Test article analysis with verbose mode enabled."""
    content = "This is a test article about cybersecurity threats."
    url = "https://example.com/article"
    
    mock_response = {
        "output_text": json.dumps({
            "summary": "Test summary",
            "source_evaluation": {
                "reliability": "High",
                "credibility": "High",
                "source_type": "Cybersecurity Vendor"
            },
            "threat_actors": [],
            "mitre_techniques": [],
            "key_insights": [],
            "source_bias": "None",
            "intelligence_gaps": [],
            "critical_infrastructure_sectors": {
                "threat_to_national_security": 1,
                "chemical_sector": 1,
                "commercial_facilities_sector": 1,
                "communications_sector": 1,
                "critical_manufacturing_sector": 1,
                "dams_sector": 1,
                "defense_industrial_base_sector": 1,
                "emergency_services_sector": 1,
                "energy_sector": 1,
                "financial_services_sector": 1,
                "food_and_agriculture_sector": 1,
                "government_services_and_facilities_sector": 1,
                "healthcare_and_public_health_sector": 1,
                "information_technology_sector": 1,
                "nuclear_reactors_materials_and_waste_sector": 1,
                "transportation_systems_sector": 1,
                "water_and_wastewater_systems_sector": 1
            }
        }),
        "usage": {
            "input_tokens": 100,
            "output_tokens": 100,
            "total_tokens": 200
        }
    }
    
    with patch('openai.responses.create', return_value=mock_response), \
         patch('app.utilities.article_analyzer.print_status') as mock_print:
        
        analyze_article(content, url, verbose=True)
        
        # Check that print_status was called with verbose updates
        assert mock_print.call_count > 0
        
        # Verify first call contains the expected message
        first_call_args = mock_print.call_args_list[0][0]
        assert "Starting analysis of article" in first_call_args[0]

def test_analyze_article_structured_json_response():
    """Test that analyze_article returns properly structured JSON response"""
    # Mock article content
    article_content = """
    A new ransomware group called "CyberThreat" has been targeting critical infrastructure.
    They use techniques like T1059 (Command and Scripting Interpreter) and T1486 (Data Encrypted for Impact).
    The group appears to be state-sponsored and has targeted energy and healthcare sectors.
    """
    
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.output_text = json.dumps({
        "summary": "A new ransomware group targeting critical infrastructure",
        "source_evaluation": {
            "reliability": "High",
            "credibility": "Medium",
            "source_type": "Cybersecurity Vendor"
        },
        "threat_actors": [
            {
                "name": "CyberThreat",
                "description": "State-sponsored ransomware group",
                "attribution_confidence": "High"
            }
        ],
        "mitre_techniques": [
            {
                "id": "T1059",
                "name": "Command and Scripting Interpreter",
                "description": "Used for initial access and execution"
            },
            {
                "id": "T1486",
                "name": "Data Encrypted for Impact",
                "description": "Used for data encryption and ransom demands"
            }
        ],
        "key_insights": [
            "New ransomware group targeting critical infrastructure",
            "Suspected state-sponsored activity"
        ],
        "source_bias": "None identified",
        "intelligence_gaps": [
            "Unknown group's full capabilities",
            "Unclear if other sectors are targeted"
        ],
        "critical_infrastructure_sectors": {
            "threat_to_national_security": 4,
            "chemical_sector": 1,
            "commercial_facilities_sector": 2,
            "communications_sector": 3,
            "critical_manufacturing_sector": 2,
            "dams_sector": 1,
            "defense_industrial_base_sector": 3,
            "emergency_services_sector": 2,
            "energy_sector": 5,
            "financial_services_sector": 2,
            "food_and_agriculture_sector": 1,
            "government_services_and_facilities_sector": 3,
            "healthcare_and_public_health_sector": 5,
            "information_technology_sector": 4,
            "nuclear_reactors_materials_and_waste_sector": 1,
            "transportation_systems_sector": 2,
            "water_and_wastewater_systems_sector": 2
        }
    })
    
    # Mock OpenAI client
    mock_client = MagicMock()
    mock_client.responses.create.return_value = mock_response
    
    # Patch the OpenAI client
    with patch('app.utilities.article_analyzer.get_openai_client', return_value=mock_client):
        # Call analyze_article
        result = analyze_article(article_content)
        
        # Verify the result structure
        assert isinstance(result, dict)
        assert "text" in result
        assert "structured" in result
        assert "api_details" in result
        
        structured_data = result["structured"]
        assert "summary" in structured_data
        assert "source_evaluation" in structured_data
        assert "threat_actors" in structured_data
        assert "mitre_techniques" in structured_data
        assert "key_insights" in structured_data
        assert "source_bias" in structured_data
        assert "intelligence_gaps" in structured_data
        assert "critical_infrastructure_sectors" in structured_data
        assert "metadata" in structured_data
        
        # Verify source evaluation structure
        source_eval = structured_data["source_evaluation"]
        assert source_eval["reliability"] in ["High", "Medium", "Low"]
        assert source_eval["credibility"] in ["High", "Medium", "Low"]
        assert source_eval["source_type"] in ["Blog", "Cybersecurity Vendor", "Government Agency"]
        
        # Verify MITRE techniques structure
        for technique in structured_data["mitre_techniques"]:
            assert "id" in technique
            assert "name" in technique
            assert "description" in technique
            assert technique["id"].startswith("T")
            assert len(technique["id"]) == 5
        
        # Verify critical infrastructure sectors structure
        sectors = structured_data["critical_infrastructure_sectors"]
        for sector, score in sectors.items():
            assert isinstance(score, int)
            assert 1 <= score <= 5
        
        # Verify metadata
        assert "model_used" in structured_data["metadata"]
        assert "timestamp" in structured_data["metadata"]
        assert "version" in structured_data["metadata"]
        
        # Verify API call
        mock_client.responses.create.assert_called_once()
        call_args = mock_client.responses.create.call_args[1]
        assert call_args["model"] == "gpt-4o-mini-2024-07-18"  # Default model
        assert "text" in call_args
        assert "format" in call_args["text"]
        assert call_args["text"]["format"]["type"] == "json_schema"
        assert call_args["text"]["format"]["strict"] is True

def test_analyze_article_error_handling():
    """Test error handling in analyze_article"""
    # Mock article content
    article_content = "Test article content"
    
    # Mock OpenAI client that raises an exception
    mock_client = MagicMock()
    mock_client.responses.create.side_effect = Exception("API Error")
    
    # Patch the OpenAI client
    with patch('app.utilities.article_analyzer.get_openai_client', return_value=mock_client):
        # Verify that the function raises the exception
        with pytest.raises(Exception) as exc_info:
            analyze_article(article_content)
        assert str(exc_info.value) == "API Error" 