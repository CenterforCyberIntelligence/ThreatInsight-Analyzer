"""
Article Analyzer Module
Handles the analysis of cybersecurity articles using AI models.
Includes functions for content extraction, analysis, and result parsing.
"""

import os
import json
import re
import traceback
import time
import random
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from openai import OpenAI, RateLimitError, APIError, APITimeoutError

from app.utilities.logger import info, debug, error, warning, print_status
from app.models.database import track_token_usage, store_indicators
from app.utilities.indicator_extractor import extract_indicators, validate_and_clean_indicators, format_indicators_for_display
from app.config.config import Config

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
debug("OpenAI client initialized")

def analyze_article(content, url, model=None, verbose=False, structured=True, extract_iocs=True):
    """
    Analyze an article using the specified AI model with structured JSON responses.
    
    Args:
        content (str): The article content to analyze
        url (str): The URL of the article
        model (str, optional): The OpenAI model to use. Defaults to Config.DEFAULT_MODEL.
        verbose (bool, optional): Whether to print status updates. Defaults to False.
        structured (bool, optional): Whether to use structured output. Defaults to True.
        extract_iocs (bool, optional): Whether to extract indicators of compromise. Defaults to True.
    
    Returns:
        dict: A dictionary containing the analysis results and metadata
    """
    if not content or not url:
        raise ValueError("Content and URL are required")
    
    # Use default model if none specified
    if not model:
        model = Config.DEFAULT_MODEL
    
    # Check if model ID looks like a display name rather than a full model ID
    if model in ["GPT-4o mini", "GPT-4o", "GPT-4.5 Preview"] or not re.match(r'^[\w-]+-\d{4}-\d{2}-\d{2}$', model):
        warning(f"Model ID '{model}' appears to be a display name rather than a full model ID with version. This may cause API errors.")
        
        # Try to find the correct model ID from Config
        display_name_to_model_map = {
            "GPT-4o mini": "gpt-4o-mini-2024-07-18",
            "GPT-4o": "gpt-4o-2024-08-06",
            "GPT-4.5 Preview": "gpt-4-turbo-preview"
        }
        
        if model in display_name_to_model_map:
            corrected_model = display_name_to_model_map[model]
            warning(f"Attempting to use '{corrected_model}' instead of '{model}'")
            model = corrected_model
    
    if verbose:
        print_status(f"Starting analysis of article from {url}")
        print_status(f"Using model: {model}")
    
    try:
        # Prepare the system prompt
        system_prompt = """You are an expert threat intelligence analyst. Analyze the cybersecurity article and create a structured threat intelligence report.

Your analysis must be thorough, technically accurate, and focus on extracting actionable threat intelligence.

Follow this exact structure in your response:
1. Create a summary of the article
2. Evaluate the source reliability (High/Medium/Low), credibility (High/Medium/Low), and source type
3. Identify threat actors with confidence level and description
4. Extract MITRE ATT&CK techniques with proper IDs, names, and descriptions
5. List key threat intelligence insights
6. Note potential source bias concerns
7. Identify intelligence gaps
8. Assess impact on critical infrastructure sectors with scores (1-5) and justifications

Format your response as a valid JSON object following the provided schema exactly."""
        
        # Define the JSON schema for the threat intelligence report
        json_schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "summary": {"type": "string"},
                "source_evaluation": {
                    "type": "object",
                    "properties": {
                        "reliability": {
                            "type": "object",
                            "properties": {
                                "level": {"type": "string", "enum": ["High", "Medium", "Low"]},
                                "justification": {"type": "string"}
                            },
                            "required": ["level", "justification"]
                        },
                        "credibility": {
                            "type": "object",
                            "properties": {
                                "level": {"type": "string", "enum": ["High", "Medium", "Low"]},
                                "justification": {"type": "string"}
                            },
                            "required": ["level", "justification"]
                        },
                        "source_type": {"type": "string"}
                    },
                    "required": ["reliability", "credibility", "source_type"]
                },
                "threat_actors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]},
                            "description": {"type": "string"},
                            "aliases": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["name", "confidence", "description", "aliases"]
                    }
                },
                "mitre_techniques": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "MITRE ATT&CK technique ID (e.g., T1190)"},
                            "name": {"type": "string"},
                            "description": {"type": "string"}
                        },
                        "required": ["id", "name", "description"]
                    }
                },
                "key_insights": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "potential_issues": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "intelligence_gaps": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "critical_sectors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "enum": [
                                    "Threat to National Security",
                                    "Chemical Sector",
                                    "Commercial Facilities Sector",
                                    "Communications Sector",
                                    "Critical Manufacturing Sector",
                                    "Dams Sector",
                                    "Defense Industrial Base Sector",
                                    "Emergency Services Sector",
                                    "Energy Sector",
                                    "Financial Services Sector",
                                    "Food & Agriculture Sector",
                                    "Government Services & Facilities Sector",
                                    "Healthcare & Public Health Sector",
                                    "Information Technology Sector",
                                    "Nuclear Reactors, Materials, and Waste Sector",
                                    "Transportation Systems Sector",
                                    "Water & Wastewater Systems Sector"
                                ]
                            },
                            "score": {
                                "type": "integer",
                                "enum": [1, 2, 3, 4, 5],
                                "description": "Score indicating sector relevance (1-5)"
                            },
                            "justification": {"type": "string"}
                        },
                        "required": ["name", "score", "justification"]
                    }
                }
            },
            "required": [
                "summary", "source_evaluation", "threat_actors", "mitre_techniques", 
                "key_insights", "potential_issues", "intelligence_gaps", "critical_sectors"
            ]
        }
        
        # Make the API call with structured outputs
        debug("=========== OPENAI API REQUEST DETAILS ===========")
        debug(f"Model ID: {model}")
        debug(f"System Prompt: {system_prompt}")
        debug(f"User Content Length: {len(content)}")
        debug(f"URL: {url}")
        debug(f"JSON Schema: {json.dumps(json_schema, indent=2)}")
        debug("================================================")
        
        try:
            debug(f"Sending OpenAI API request with model: {model}")
            try:
                # First try with JSON response format
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Analyze this cybersecurity article from {url} and return the analysis as a JSON object following the exact schema provided:\n\n{content}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
            except Exception as json_error:
                # If JSON format fails, try without specifying response format
                if "response_format" in str(json_error) or "json" in str(json_error).lower():
                    debug(f"JSON response format failed, retrying without format specification: {str(json_error)}")
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Analyze this cybersecurity article from {url} and format your response as a valid JSON object following the exact schema provided. Here's the article:\n\n{content}"}
                        ],
                        temperature=0.2
                    )
                else:
                    # If it's not a JSON format issue, re-raise the original error
                    raise
            
            debug("=========== OPENAI API RESPONSE RECEIVED ===========")
            debug(f"Response Status: Success")
            debug(f"Response Model: {response.model}")
            debug(f"Response Usage: {response.usage}")
            debug("==================================================")
        except Exception as e:
            debug("=========== OPENAI API ERROR DETAILS ===========")
            debug(f"Error Type: {type(e).__name__}")
            debug(f"Error Message: {str(e)}")
            debug(f"Model ID that caused error: {model}")
            error_response = getattr(e, 'response', None)
            if error_response:
                debug(f"Error Response: {error_response}")
                if hasattr(error_response, 'json'):
                    try:
                        error_json = error_response.json()
                        debug(f"Error JSON: {json.dumps(error_json, indent=2)}")
                    except:
                        debug("Could not parse error response as JSON")
            debug("================================================")
            raise
        
        # Parse the response
        try:
            # Try to parse as JSON first
            response_content = response.choices[0].message.content
            debug(f"Response content type: {type(response_content)}")
            debug(f"Response content sample: {response_content[:200]}...")
            
            # Log the full response for debugging
            print("========== FULL API RESPONSE ==========")
            print(response_content)
            print("=======================================")
            
            # Check if the response is valid JSON
            if is_valid_json(response_content):
                parsed_response = json.loads(response_content)
                debug("Successfully parsed response as JSON")
                print("======= PARSED JSON STRUCTURE =======")
                print(json.dumps(parsed_response, indent=2))
                print("====================================")
                
                # Start with a clean result structure that matches template expectations
                result = {
                    "summary": parsed_response.get("summary", "No summary available."),
                    "source_evaluation": {
                        "reliability": {"level": "Medium", "justification": "No justification provided."},
                        "credibility": {"level": "Medium", "justification": "No justification provided."},
                        "source_type": "Unknown"
                    },
                    "threat_actors": [],
                    "mitre_techniques": [],
                    "key_insights": [],
                    "potential_issues": [],
                    "intelligence_gaps": [],
                    "critical_sectors": []
                }
                
                # Handle source_evaluation
                if "source_evaluation" in parsed_response:
                    source_eval = parsed_response["source_evaluation"]
                    if isinstance(source_eval, dict):
                        result["source_evaluation"] = source_eval
                elif all(key in parsed_response for key in ["source_reliability", "source_credibility", "source_type"]):
                    # Handle flat source evaluation fields
                    reliability = parsed_response.get("source_reliability", "Medium")
                    credibility = parsed_response.get("source_credibility", "Medium")
                    source_type = parsed_response.get("source_type", "Unknown")
                    
                    # Convert to structured format
                    result["source_evaluation"] = {
                        "reliability": {
                            "level": reliability,
                            "justification": "Based on source analysis."
                        },
                        "credibility": {
                            "level": credibility,
                            "justification": "Based on source analysis."
                        },
                        "source_type": source_type
                    }
                
                # Handle threat actors
                if "threat_actors" in parsed_response:
                    actors = parsed_response["threat_actors"]
                    if isinstance(actors, list):
                        for actor in actors:
                            if isinstance(actor, dict):
                                # Check if actor has all required fields in correct format
                                actor_name = actor.get("name", "Unknown")
                                actor_confidence = actor.get("confidence", actor.get("confidence_level", "Medium"))
                                actor_description = actor.get("description", "No description available.")
                                actor_aliases = actor.get("aliases", [])
                                
                                result["threat_actors"].append({
                                    "name": actor_name,
                                    "confidence": actor_confidence,
                                    "description": actor_description,
                                    "aliases": actor_aliases
                                })
                            elif isinstance(actor, str):
                                # Handle simple string actors
                                result["threat_actors"].append({
                                    "name": actor,
                                    "confidence": "Medium",
                                    "description": "No description available.",
                                    "aliases": []
                                })
                
                # Handle MITRE techniques
                mitre_key = next((k for k in parsed_response.keys() if "mitre" in k.lower()), None)
                if mitre_key and mitre_key in parsed_response:
                    techniques = parsed_response[mitre_key]
                    if isinstance(techniques, list):
                        for tech in techniques:
                            if isinstance(tech, dict):
                                technique_id = tech.get("id", "Unknown")
                                technique_name = tech.get("name", "Unknown Technique")
                                technique_desc = tech.get("description", "No description available.")
                                
                                result["mitre_techniques"].append({
                                    "id": technique_id,
                                    "name": technique_name,
                                    "description": technique_desc
                                })
                
                # Handle key insights
                insights_key = next((k for k in parsed_response.keys() if "insight" in k.lower() or "intelligence" in k.lower()), None)
                if insights_key and insights_key in parsed_response and insights_key != "intelligence_gaps":
                    insights = parsed_response[insights_key]
                    if isinstance(insights, list):
                        result["key_insights"] = insights
                    elif isinstance(insights, str):
                        result["key_insights"] = [insights]
                
                # Handle potential issues/bias
                bias_key = next((k for k in parsed_response.keys() if "bias" in k.lower() or "issue" in k.lower()), None)
                if bias_key and bias_key in parsed_response:
                    bias = parsed_response[bias_key]
                    if isinstance(bias, list):
                        result["potential_issues"] = bias
                    elif isinstance(bias, str):
                        result["potential_issues"] = [bias]
                
                # Handle intelligence gaps
                if "intelligence_gaps" in parsed_response:
                    gaps = parsed_response["intelligence_gaps"]
                    if isinstance(gaps, list):
                        result["intelligence_gaps"] = gaps
                    elif isinstance(gaps, str):
                        result["intelligence_gaps"] = [gaps]
                
                # Handle critical sectors
                sectors_key = next((k for k in parsed_response.keys() if "sector" in k.lower() or "infrastructure" in k.lower() or "impact" in k.lower()), None)
                if sectors_key and sectors_key in parsed_response:
                    sectors_data = parsed_response[sectors_key]
                    
                    # Handle different formats for sectors
                    if isinstance(sectors_data, dict) and "sectors" in sectors_data and isinstance(sectors_data["sectors"], list):
                        # Handle format with nested sectors array
                        for sector in sectors_data["sectors"]:
                            if isinstance(sector, dict):
                                sector_name = sector.get("sector", "Unknown Sector")
                                sector_score = sector.get("impact_score", 3)
                                sector_justification = sector.get("justification", "No justification provided.")
                                
                                result["critical_sectors"].append({
                                    "name": sector_name,
                                    "score": sector_score,
                                    "justification": sector_justification
                                })
                    elif isinstance(sectors_data, list):
                        # Handle format with direct array of sectors
                        for sector in sectors_data:
                            if isinstance(sector, dict):
                                sector_name = sector.get("name", sector.get("sector", "Unknown Sector"))
                                sector_score = sector.get("score", sector.get("impact_score", 3))
                                sector_justification = sector.get("justification", "No justification provided.")
                                
                                result["critical_sectors"].append({
                                    "name": sector_name,
                                    "score": sector_score,
                                    "justification": sector_justification
                                })
                    elif isinstance(sectors_data, dict):
                        # Check if this is a nested structure with sector names as keys
                        nested_sectors = False
                        
                        # Check if the dict contains sectorial assessment objects
                        for key, value in sectors_data.items():
                            if isinstance(value, dict) and any(k in value for k in ["score", "justification"]):
                                nested_sectors = True
                                
                                # Extract sector info
                                sector_name = key
                                sector_score = value.get("score", 3)
                                sector_justification = value.get("justification", "No justification provided.")
                                
                                # Map sector name to standard format
                                name_mapping = {
                                    "energy": "Energy Sector",
                                    "water": "Water & Wastewater Systems Sector",
                                    "water_and_wastewater": "Water & Wastewater Systems Sector", 
                                    "healthcare": "Healthcare & Public Health Sector",
                                    "government": "Government Services & Facilities Sector",
                                    "transportation": "Transportation Systems Sector",
                                    "finance": "Financial Services Sector",
                                    "chemical": "Chemical Sector",
                                    "communications": "Communications Sector",
                                    "critical_manufacturing": "Critical Manufacturing Sector",
                                    "dams": "Dams Sector",
                                    "defense": "Defense Industrial Base Sector",
                                    "emergency_services": "Emergency Services Sector",
                                    "food_agriculture": "Food & Agriculture Sector",
                                    "information_technology": "Information Technology Sector", 
                                    "nuclear": "Nuclear Reactors, Materials, and Waste Sector",
                                    "telecommunications": "Communications Sector"
                                }
                                
                                sector_name = name_mapping.get(sector_name, sector_name.replace("_", " ").title() + " Sector")
                                
                                # Ensure score is in 1-5 range
                                normalized_score = min(max(int(sector_score), 1), 5)
                                
                                result["critical_sectors"].append({
                                    "name": sector_name, 
                                    "score": normalized_score,
                                    "justification": sector_justification
                                })
                        
                        # If not a nested structure, handle as before
                        if not nested_sectors:
                            # Handle sectors as direct keys with score values
                            justifications = {}
                            common_justification = ""
                            
                            # Check for justifications dict
                            if "justifications" in sectors_data and isinstance(sectors_data["justifications"], dict):
                                justifications = sectors_data["justifications"]
                            
                            # Check for a single justification string
                            if "justification" in sectors_data and isinstance(sectors_data["justification"], str):
                                common_justification = sectors_data["justification"]
                            
                            # Process each sector
                            for sector, value in sectors_data.items():
                                # Skip non-sector keys
                                if sector in ["justifications", "sectors", "overall_impact", "impact_description", "justification"]:
                                    continue
                                    
                                if isinstance(value, (int, float)):
                                    # Get justification if available
                                    justification = justifications.get(sector, common_justification or "No justification provided.")
                                    
                                    # Map sector name to standard format
                                    name_mapping = {
                                        "energy": "Energy Sector",
                                        "water": "Water & Wastewater Systems Sector",
                                        "water_and_wastewater": "Water & Wastewater Systems Sector", 
                                        "healthcare": "Healthcare & Public Health Sector",
                                        "government": "Government Services & Facilities Sector",
                                        "transportation": "Transportation Systems Sector",
                                        "finance": "Financial Services Sector",
                                        "chemical": "Chemical Sector",
                                        "communications": "Communications Sector",
                                        "critical_manufacturing": "Critical Manufacturing Sector",
                                        "dams": "Dams Sector",
                                        "defense": "Defense Industrial Base Sector",
                                        "emergency_services": "Emergency Services Sector",
                                        "food_agriculture": "Food & Agriculture Sector",
                                        "information_technology": "Information Technology Sector", 
                                        "nuclear": "Nuclear Reactors, Materials, and Waste Sector",
                                        "telecommunications": "Communications Sector"
                                    }
                                    
                                    sector_name = name_mapping.get(sector, sector.replace("_", " ").title() + " Sector")
                                    
                                    # Ensure score is in 1-5 range
                                    normalized_score = min(max(int(value), 1), 5)
                                    
                                    result["critical_sectors"].append({
                                        "name": sector_name, 
                                        "score": normalized_score,
                                        "justification": justification
                                    })
                
                debug(f"Final critical sectors count: {len(result['critical_sectors'])}")
                
                # Add metadata
                result["metadata"] = {
                    "model_used": model,
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "1.1.1"
                }
                
                debug("Successfully processed API response to match template format")
            else:
                # If not valid JSON, try to extract JSON from the text
                debug("Response is not valid JSON, attempting to extract JSON")
                json_match = re.search(r'```json\s*(.*?)\s*```', response_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    result = json.loads(json_str)
                    debug("Successfully extracted JSON from code block")
                else:
                    # If no JSON found, fallback to text parsing
                    debug("No JSON found in response, falling back to text parsing")
                    result = parse_analysis_response(response_content)
        except json.JSONDecodeError as e:
            warning(f"Failed to parse response as JSON: {str(e)}")
            result = parse_analysis_response(response.choices[0].message.content)
        
        # Print final structured data for debugging
        print("========== FINAL STRUCTURED DATA RETURNING TO TEMPLATE ==========")
        print(json.dumps(result, indent=2))
        print("================================================================")
        
        # Track token usage
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        if verbose:
            print_status(f"Analysis complete. Tokens used: {input_tokens + output_tokens}")
        
        return {
            "text": json.dumps(result, indent=2),
            "structured": result,
            "api_details": {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }
        }
        
    except Exception as e:
        if verbose:
            print_status(f"Error during analysis: {str(e)}", is_error=True)
        raise

def self_validate_structured_data(data: Dict[str, Any]) -> None:
    """
    Ensure the structured data has all required fields.
    Modifies the data dictionary in place to fix any missing fields.
    
    Args:
        data: The structured data dictionary to validate
    """
    # Ensure top-level fields exist
    if "summary" not in data or not data["summary"]:
        data["summary"] = "No summary available."
    
    # Validate source_evaluation
    if "source_evaluation" not in data or not data["source_evaluation"]:
        data["source_evaluation"] = {
            "reliability": {"level": "Medium", "justification": "No reliability assessment available."},
            "credibility": {"level": "Medium", "justification": "No credibility assessment available."},
            "source_type": "Unknown"
        }
    else:
        source_eval = data["source_evaluation"]
        if "reliability" not in source_eval or not source_eval["reliability"]:
            source_eval["reliability"] = {"level": "Medium", "justification": "No reliability assessment available."}
        else:
            if "level" not in source_eval["reliability"] or not source_eval["reliability"]["level"]:
                source_eval["reliability"]["level"] = "Medium"
            if "justification" not in source_eval["reliability"] or not source_eval["reliability"]["justification"]:
                source_eval["reliability"]["justification"] = "No justification provided."
        
        if "credibility" not in source_eval or not source_eval["credibility"]:
            source_eval["credibility"] = {"level": "Medium", "justification": "No credibility assessment available."}
        else:
            if "level" not in source_eval["credibility"] or not source_eval["credibility"]["level"]:
                source_eval["credibility"]["level"] = "Medium"
            if "justification" not in source_eval["credibility"] or not source_eval["credibility"]["justification"]:
                source_eval["credibility"]["justification"] = "No justification provided."
        
        if "source_type" not in source_eval or not source_eval["source_type"]:
            source_eval["source_type"] = "Unknown"
    
    # Ensure arrays exist
    for field in ["threat_actors", "mitre_techniques", "key_insights", "potential_issues", "intelligence_gaps", "critical_sectors"]:
        if field not in data or not isinstance(data[field], list):
            data[field] = []
    
    # Standard fixes for misformatted data
    # For threat actors, ensure each has required fields
    for actor in data["threat_actors"]:
        if "name" not in actor or not actor["name"]:
            actor["name"] = "Unknown Actor"
        if "description" not in actor or not actor["description"]:
            actor["description"] = "No description available."
        if "confidence" not in actor or not actor["confidence"]:
            actor["confidence"] = "Medium"
        if "aliases" not in actor or not isinstance(actor["aliases"], list):
            actor["aliases"] = []
    
    # For MITRE techniques, ensure each has required fields
    for technique in data["mitre_techniques"]:
        if "id" not in technique or not technique["id"]:
            technique["id"] = "Unknown"
        if "name" not in technique or not technique["name"]:
            technique["name"] = "Unknown Technique"
        if "description" not in technique or not technique["description"]:
            technique["description"] = "No description available."
    
    # For critical sectors, ensure each has required fields
    for sector in data["critical_sectors"]:
        if "name" not in sector or not sector["name"]:
            sector["name"] = "Unknown Sector"
        if "score" not in sector or not isinstance(sector["score"], int):
            sector["score"] = 1
        if "justification" not in sector or not sector["justification"]:
            sector["justification"] = "No justification available."

def parse_analysis_response(text: str) -> Dict[str, Any]:
    """
    Parse the AI response into structured data.
    
    Args:
        text: The raw analysis text to parse
    
    Returns:
        Dictionary containing structured analysis data
    """
    debug("Starting to parse analysis response")
    
    # Initialize the structured data with default values
    structured_data = {
        "summary": "",
        "source_evaluation": {
            "reliability": {"level": "", "justification": ""},
            "credibility": {"level": "", "justification": ""},
            "source_type": ""
        },
        "mitre_techniques": [],
        "key_insights": [],
        "potential_issues": [],
        "relevance": {"score": 0, "justification": ""},
        "critical_sectors": []  # New field for critical sectors assessment
    }
    
    # Clean the text first - remove any markdown formatting that might be present despite instructions
    clean_text = re.sub(r'\*\*|\*', '', text)  # Remove bold/italic markers
    clean_text = re.sub(r'#+\s*', '', clean_text)  # Remove markdown headers
    debug("Cleaned text from markdown formatting")
    
    # Extract the main sections using more flexible delimiters that handle various formats
    debug("Extracting sections from analysis text")
    sections = {
        "summary": re.search(r'(?:#+\s*)?(?:\d+\.?\s*)?Summary(?:\s+of\s+Article)?(?:[\s:]*)(.*?)(?=(?:#+\s*)?(?:\d+\.?\s*)?Source\s+Evaluation|\Z)', clean_text, re.DOTALL | re.IGNORECASE),
        "source_eval": re.search(r'(?:#+\s*)?(?:\d+\.?\s*)?Source\s+Evaluation(?:[\s:]*)(.*?)(?=(?:#+\s*)?(?:\d+\.?\s*)?MITRE\s+ATT&CK|\Z)', clean_text, re.DOTALL | re.IGNORECASE),
        "mitre": re.search(r'(?:#+\s*)?(?:\d+\.?\s*)?MITRE\s+ATT&CK\s+Techniques(?:[\s:]*)(.*?)(?=(?:#+\s*)?(?:\d+\.?\s*)?Key\s+Threat|\Z)', clean_text, re.DOTALL | re.IGNORECASE),
        "insights": re.search(r'(?:#+\s*)?(?:\d+\.?\s*)?Key\s+Threat\s+Intelligence\s+Insights(?:[\s:]*)(.*?)(?=(?:#+\s*)?(?:\d+\.?\s*)?Potential\s+Bias|\Z)', clean_text, re.DOTALL | re.IGNORECASE),
        "issues": re.search(r'(?:#+\s*)?(?:\d+\.?\s*)?Potential\s+Bias(?:[^:]*):?(.*?)(?=(?:#+\s*)?(?:\d+\.?\s*)?Relevance|\Z)', clean_text, re.DOTALL | re.IGNORECASE),
        "relevance": re.search(r'(?:#+\s*)?(?:\d+\.?\s*)?Relevance\s+to\s+U\.S\.\s+Government(?:[^(]*)?(?:\(?Score:?\s*(\d+)(?:[^)]*)\)?)?(?:[\s:]*)(.*?)(?=(?:#+\s*)?(?:\d+\.?\s*)?Critical\s+Infrastructure|\Z)', clean_text, re.DOTALL | re.IGNORECASE),
        "sectors": re.search(r'(?:#+\s*)?(?:\d+\.?\s*)?Critical\s+Infrastructure\s+Sectors\s+Assessment(?:[\s:]*)(.*?)(?=\Z)', clean_text, re.DOTALL | re.IGNORECASE)
    }
    
    # If relevance not found with (Score: X) format, try alternative format
    if not sections["relevance"] or not sections["relevance"].group(1):
        score_match = re.search(r'(?:#+\s*)?(?:\d+\.?\s*)?Relevance\s+to\s+U\.S\.\s+Government(?:[^:]*):?\s*(\d+)(?:/\d+)?', clean_text, re.DOTALL | re.IGNORECASE)
        if score_match:
            score = score_match.group(1)
            # Find the justification text
            justification_match = re.search(r'(?:#+\s*)?(?:\d+\.?\s*)?Relevance\s+to\s+U\.S\.\s+Government(?:[^:]*):?\s*\d+(?:/\d+)?(?:[\s:]*)(.*?)(?=(?:#+\s*)?(?:\d+\.?\s*)?Critical\s+Infrastructure|\Z)', clean_text, re.DOTALL | re.IGNORECASE)
            justification = justification_match.group(1).strip() if justification_match else ""
            # Create a mock match object to use with existing code
            sections["relevance"] = type('obj', (object,), {'group': lambda s, n: score if n == 1 else justification})()
    
    # Process summary section
    if sections["summary"]:
        structured_data["summary"] = sections["summary"].group(1).strip()
        debug("Extracted summary section")
    else:
        warning("Failed to extract summary section")
        # Try with original text as fallback
        summary_fallback = re.search(r'(?:#+\s*)?(?:\d+\.?\s*)?Summary(?:\s+of\s+Article)?(?:[\s:]*)(.*?)(?=(?:#+\s*)?(?:\d+\.?\s*)?Source\s+Evaluation|\Z)', text, re.DOTALL | re.IGNORECASE)
        if summary_fallback:
            structured_data["summary"] = summary_fallback.group(1).strip()
            debug("Extracted summary section from original text")
    
    # Process source evaluation - handle various formats
    if sections["source_eval"]:
        source_text = sections["source_eval"].group(1).strip()
        debug("Extracting source evaluation details")
        
        # Try to extract reliability (multiple patterns to increase chances of success)
        reliability_match = re.search(r'(?:^|\n)[-*]?\s*Reliability:\s*([Hh]igh|[Mm]edium|[Ll]ow)(?:[^-\n]*?)-?\s*(.*?)(?=(?:^|\n)[-*]?\s*Credibility:|Credibility:|\Z)', source_text, re.DOTALL | re.IGNORECASE)
        if not reliability_match:
            reliability_match = re.search(r'Reliability:\s*([Hh]igh|[Mm]edium|[Ll]ow)(?:[^-\n]*?)-?\s*(.*?)(?=Credibility:|\Z)', source_text, re.DOTALL | re.IGNORECASE)
        
        if reliability_match:
            structured_data["source_evaluation"]["reliability"] = {
                "level": reliability_match.group(1).title(),
                "justification": reliability_match.group(2).strip()
            }
            debug(f"Extracted reliability: {reliability_match.group(1).title()}")
        else:
            warning("Failed to extract reliability information")
        
        # Extract credibility (multiple patterns to increase chances of success)
        credibility_match = re.search(r'(?:^|\n)[-*]?\s*Credibility:\s*([Hh]igh|[Mm]edium|[Ll]ow)(?:[^-\n]*?)-?\s*(.*?)(?=(?:^|\n)[-*]?\s*Source Type:|Source Type:|\Z)', source_text, re.DOTALL | re.IGNORECASE)
        if not credibility_match:
            credibility_match = re.search(r'Credibility:\s*([Hh]igh|[Mm]edium|[Ll]ow)(?:[^-\n]*?)-?\s*(.*?)(?=Source Type:|\Z)', source_text, re.DOTALL | re.IGNORECASE)
        
        if credibility_match:
            structured_data["source_evaluation"]["credibility"] = {
                "level": credibility_match.group(1).title(),
                "justification": credibility_match.group(2).strip()
            }
            debug(f"Extracted credibility: {credibility_match.group(1).title()}")
        else:
            warning("Failed to extract credibility information")
        
        # Extract source type (multiple patterns to increase chances of success)
        source_type_match = re.search(r'(?:^|\n)[-*]?\s*Source Type:\s*(.*?)(?=\Z|\n(?:\d+\.|\-))', source_text, re.DOTALL | re.IGNORECASE)
        if not source_type_match:
            source_type_match = re.search(r'Source Type:\s*(.*?)(?=$)', source_text, re.DOTALL | re.IGNORECASE)
        
        if source_type_match:
            structured_data["source_evaluation"]["source_type"] = source_type_match.group(1).strip()
            debug(f"Extracted source type: {source_type_match.group(1).strip()}")
        else:
            warning("Failed to extract source type information")
    else:
        warning("Failed to extract source evaluation section")
        # Try with original text as fallback
        source_eval_fallback = re.search(r'(?:#+\s*)?(?:\d+\.?\s*)?Source\s+Evaluation(?:[\s:]*)(.*?)(?=(?:#+\s*)?(?:\d+\.?\s*)?MITRE\s+ATT&CK|\Z)', text, re.DOTALL | re.IGNORECASE)
        if source_eval_fallback:
            debug("Attempting to extract source evaluation from original text")
            # Continue with similar extraction logic for original text
    
    # Process MITRE ATT&CK Techniques - enhanced to handle various formats
    if sections["mitre"]:
        mitre_text = sections["mitre"].group(1).strip()
        debug("Extracting MITRE ATT&CK techniques")
        
        # Handle both numbered lists and bullet points with flexible formatting
        # First attempt: Look for standard numbered format with technique ID first
        mitre_items = re.findall(r'(?:^|\n)(?:\d+\.)?\s*([Tt]\d+(?:\.\d+)?)\s*(?:-|:|–)\s*([^\.]+?)(?:\.)(.*?)(?=(?:\n(?:\d+\.))|$)', mitre_text, re.DOTALL)
        
        # If that didn't work, try alternative pattern for other formats
        if not mitre_items:
            debug("First MITRE extraction pattern failed, trying alternative pattern")
            mitre_items = re.findall(r'(?:^|\n)(?:\d+\.|-)?\s*(?:\*\*)?([Tt]\d+(?:\.\d+)?)(?:\*\*)?\s*(?:-|:|–)\s*(?:\*\*)?([^\.]+?)(?:\*\*)?\s*\.\s*(.*?)(?=(?:\n(?:\d+\.|-))|$)', mitre_text, re.DOTALL)
        
        # If still no results, try an even more flexible pattern for difficult cases
        if not mitre_items:
            debug("Second MITRE extraction pattern failed, trying final fallback pattern")
            # This pattern prioritizes finding the technique ID and then grabs everything after until next technique
            mitre_ids = re.findall(r'(?:^|\n)(?:\d+\.)?\s*([Tt]\d+(?:\.\d+)?)\s*(?:-|:|–)\s*(.*?)(?=(?:\n\d+\.\s*[Tt]\d+)|$)', mitre_text, re.DOTALL)
            
            for item in mitre_ids:
                technique_id = item[0].strip()
                rest_text = item[1].strip()
                
                # Try to split remaining text into name and description
                name_desc_match = re.match(r'([^\.]+?)(?:\.)(.*)', rest_text, re.DOTALL)
                if name_desc_match:
                    technique_name = name_desc_match.group(1).strip()
                    technique_desc = name_desc_match.group(2).strip()
                else:
                    # If no clear separation, use first 50 chars as name and rest as description
                    technique_name = rest_text[:50] + ('...' if len(rest_text) > 50 else '')
                    technique_desc = rest_text
                
                structured_data["mitre_techniques"].append({
                    "id": technique_id,
                    "name": technique_name,
                    "description": technique_desc
                })
            
            debug(f"Extracted {len(structured_data['mitre_techniques'])} MITRE techniques using fallback pattern")
            
        # Process normal matches if we found them with the first two patterns
        if mitre_items:
            for item in mitre_items:
                technique_id = item[0].strip() if item[0] else ""
                technique_name = item[1].strip() if len(item) > 1 else ""
                technique_desc = item[2].strip() if len(item) > 2 else ""
                
                # Skip empty entries
                if not (technique_id or technique_name):
                    continue
                    
                structured_data["mitre_techniques"].append({
                    "id": technique_id,
                    "name": technique_name,
                    "description": technique_desc
                })
            
            debug(f"Extracted {len(structured_data['mitre_techniques'])} MITRE techniques")
        
    else:
        warning("Failed to extract MITRE ATT&CK Techniques section")
        # Try with original text as fallback
    
    # Process Key Threat Intelligence Insights - enhanced to handle various formats
    if sections["insights"]:
        insights_text = sections["insights"].group(1).strip()
        debug("Extracting key threat intelligence insights")
        
        # Extract both numbered and dash items with more flexible pattern
        insights = re.findall(r'(?:^|\n)(?:\d+\.|\-)\s*(.*?)(?=(?:\n(?:\d+\.|\-))|$)', insights_text, re.DOTALL)
        structured_data["key_insights"] = [insight.strip() for insight in insights if insight.strip()]
        
        debug(f"Extracted {len(structured_data['key_insights'])} key insights")
    else:
        warning("Failed to extract Key Threat Intelligence Insights section")
        # Try with original text as fallback
    
    # Process Potential Bias or Issues - enhanced to handle various formats
    if sections["issues"]:
        issues_text = sections["issues"].group(1).strip()
        debug("Extracting potential bias or issues")
        
        # Extract both numbered and dash items with more flexible pattern
        issues = re.findall(r'(?:^|\n)(?:\d+\.|\-)\s*(.*?)(?=(?:\n(?:\d+\.|\-))|$)', issues_text, re.DOTALL)
        structured_data["potential_issues"] = [issue.strip() for issue in issues if issue.strip()]
        
        debug(f"Extracted {len(structured_data['potential_issues'])} potential issues")
    else:
        warning("Failed to extract Potential Bias or Issues section")
        # Try with original text as fallback
    
    # Process Relevance to U.S. Government - enhanced to handle various formats
    if sections["relevance"]:
        score = sections["relevance"].group(1)
        justification = sections["relevance"].group(2).strip()
        
        # Convert score to integer and validate range
        try:
            score_int = int(score)
            if 1 <= score_int <= 5:
                structured_data["relevance"] = {
                    "score": score_int,
                    "justification": justification
                }
                debug(f"Extracted relevance score: {score_int}")
            else:
                warning(f"Invalid score value: {score_int}, should be between 1 and 5")
        except (ValueError, TypeError):
            warning(f"Could not convert relevance score to integer: {score}")
    else:
        warning("Failed to extract Relevance to U.S. Government section")
        # Try alternative patterns with original text
    
    # Process Critical Infrastructure Sectors Assessment - COMPLETELY REVISED
    if sections["sectors"]:
        sectors_text = sections["sectors"].group(1).strip()
        debug("Extracting critical infrastructure sectors assessment")
        
        # Better pattern to match sectors in various formats:
        # - Both numbered and bulleted lists
        # - With or without asterisks/bold formatting
        # - Various delimiter formats between name, score and justification
        
        # This pattern captures:
        # 1. Sector name
        # 2. Score (1-5)
        # 3. Justification text
        sector_patterns = [
            # Pattern for "1. Name: Score - Justification"
            r'(?:^|\n)(?:\d+\.|\-)\s*(?:\*\*)?([^:]+?)(?:\*\*)?\s*:\s*(?:\*\*)?(\d+)(?:\*\*)?(?:[^-]*?)-\s*(.*?)(?=(?:\n(?:\d+\.|\-))|$)',
            
            # Pattern for "1. Name: Score high/medium/low relevance..."
            r'(?:^|\n)(?:\d+\.|\-)\s*(?:\*\*)?([^:]+?)(?:\*\*)?:\s*(?:\*\*)?(\d+)(?:\*\*)?(?:\s*-\s*|\s+)([Hh]igh|[Mm]edium|[Ll]ow|[Mm]oderate)(?:\s+relevance\s+)(.*?)(?=(?:\n(?:\d+\.|\-))|$)',
            
            # Pattern for nested numbered lists "1. Name: 1. Score - Justification"
            r'(?:^|\n)(?:\d+\.|\-)\s*(?:\*\*)?([^:]+?)(?:\*\*)?:\s*(?:\d+\.)\s*(?:\*\*)?(\d+)(?:\*\*)?(?:[^-]*?)-\s*(.*?)(?=(?:\n(?:\d+\.|\-))|$)'
        ]
        
        # Try each pattern and collect all matches
        all_sectors = []
        for pattern in sector_patterns:
            sectors = re.findall(pattern, sectors_text, re.DOTALL)
            if sectors:
                all_sectors.extend(sectors)
                debug(f"Found {len(sectors)} sectors with pattern {pattern[:30]}...")
        
        # If no sectors found, try a more generic fallback pattern
        if not all_sectors:
            generic_pattern = r'(?:^|\n)(?:\d+\.|\-)\s*(?:\*\*)?([^:]+?)(?:\*\*)?\s*:?\s*(?:\*\*)?(\d+)(?:\*\*)?(?:[^a-zA-Z\n]*)(.*?)(?=(?:\n(?:\d+\.|\-))|$)'
            generic_sectors = re.findall(generic_pattern, sectors_text, re.DOTALL)
            all_sectors.extend(generic_sectors)
            debug(f"Found {len(generic_sectors)} sectors with generic fallback pattern")
        
        # Process all found sectors
        for sector in all_sectors:
            sector_name = sector[0].strip()
            
            # Handle potential missing score (use default of 1)
            try:
                sector_score = int(sector[1])
                # Validate score range
                if sector_score < 1 or sector_score > 5:
                    warning(f"Invalid sector score: {sector_score} for {sector_name}, clamping to range 1-5")
                    sector_score = max(1, min(5, sector_score))
            except (ValueError, IndexError):
                warning(f"Could not parse score for sector {sector_name}, using default score")
                sector_score = 1
            
            # Get justification (3rd element)
            sector_justification = sector[2].strip() if len(sector) > 2 else ""
            
            # Clean up sector name (remove any remaining ** or other formatting)
            sector_name = re.sub(r'\*\*|\*', '', sector_name)
            
            structured_data["critical_sectors"].append({
                "name": sector_name,
                "score": sector_score,
                "justification": sector_justification
            })
        
        debug(f"Extracted {len(structured_data['critical_sectors'])} critical infrastructure sectors")
        
        # If no sectors were found with regex, try a direct approach to parse the text line by line
        if not structured_data["critical_sectors"]:
            warning("No sectors found with regex patterns, attempting line-by-line parsing")
            
            # Split into lines and look for sector patterns
            lines = sectors_text.split('\n')
            current_sector = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for lines that might be sector definitions
                sector_line_match = re.search(r'(?:\d+\.|\-)\s*([^:]+?):\s*(\d+)', line)
                if sector_line_match:
                    sector_name = sector_line_match.group(1).strip()
                    sector_score = int(sector_line_match.group(2))
                    
                    # Extract justification from remainder of line
                    remainder = line[sector_line_match.end():].strip()
                    justification = remainder.lstrip('-').strip()
                    
                    structured_data["critical_sectors"].append({
                        "name": sector_name,
                        "score": sector_score,
                        "justification": justification
                    })
            
            debug(f"Line-by-line parsing found {len(structured_data['critical_sectors'])} sectors")
    else:
        warning("Failed to extract Critical Infrastructure Sectors Assessment section")
        # Try with original text as fallback
        sectors_fallback = re.search(r'(?:#+\s*)?(?:\d+\.?\s*)?Critical\s+Infrastructure\s+Sectors\s+Assessment(?:[\s:]*)(.*?)(?=\Z)', text, re.DOTALL | re.IGNORECASE)
        if sectors_fallback:
            debug("Attempting fallback extraction of critical sectors from original text")
            # Similar extraction logic from above but applied to original text
    
    info("Successfully parsed analysis response into structured data")
    return structured_data

def parse_mitre_technique(text: str) -> Dict[str, str]:
    """
    Parse a MITRE ATT&CK technique string into its components.
    
    Args:
        text: The technique string to parse (e.g., "T1190 - Exploit Public-Facing Application")
    
    Returns:
        Dictionary with id and name components
    """
    debug(f"Parsing MITRE technique string: {text}")
    
    # Extract ID and name using regex
    technique_match = re.match(r'(?:(\w+)\s*-\s*)?(.*)', text)
    
    if technique_match:
        technique_id = technique_match.group(1) or ""
        technique_name = technique_match.group(2) or ""
        
        result = {
            "id": technique_id.strip(),
            "name": technique_name.strip()
        }
        
        debug(f"Parsed MITRE technique: ID={result['id']}, Name={result['name']}")
        return result
    
    warning(f"Could not parse MITRE technique string: {text}")
    return {
        "id": "",
        "name": text.strip()
    }

# Helper function to check if a string is valid JSON
def is_valid_json(json_string):
    try:
        json.loads(json_string)
        return True
    except json.JSONDecodeError:
        return False 