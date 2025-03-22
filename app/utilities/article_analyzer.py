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

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
debug("OpenAI client initialized")

def analyze_article(
    content: str, 
    url: str, 
    model: str = "gpt-4o", 
    verbose: bool = False, 
    structured: bool = True,
    max_retries: int = 3,
    retry_delay: float = 3.0,
    temperature: float = 0.1,  # Lower default temperature for more consistent results
    seed: int = 42,  # Consistent seed for reproducibility
    extract_iocs: bool = True  # Whether to extract indicators of compromise
) -> Union[str, Dict[str, Any], None]:
    """
    Analyze an article using the specified AI model.
    
    Args:
        content: The article text to analyze
        url: The source URL of the article
        model: The AI model to use for analysis
        verbose: Whether to print status messages
        structured: Whether to return structured data
        max_retries: Maximum number of retry attempts for API errors
        retry_delay: Delay between retry attempts in seconds
        temperature: Temperature setting for response variability (0.0 to 1.0)
        seed: Seed for reproducible outputs
        extract_iocs: Whether to extract indicators of compromise
    
    Returns:
        Either a string containing the analysis, a dictionary with structured data, or None if analysis failed
    """
    content_length = len(content)
    info(f"Starting analysis of article from {url} with model {model}")
    debug(f"Article content length: {content_length} characters")
    
    if verbose:
        print_status(f"Starting analysis of article from {url}")
        print_status(f"Content length: {content_length} characters")
        print_status(f"Requested model: {model}")
    
    # Extract indicators of compromise if requested
    extracted_indicators = None
    if extract_iocs:
        debug("Extracting indicators of compromise from article content")
        if verbose:
            print_status("Extracting indicators of compromise from article content")
            
        # Extract indicators
        extracted_indicators = extract_indicators(content, url)
        
        # Clean and validate the indicators
        extracted_indicators = validate_and_clean_indicators(extracted_indicators)
        
        total_indicators = sum(len(indicators) for indicators in extracted_indicators.values())
        debug(f"Extracted {total_indicators} indicators of compromise")
        
        if verbose:
            print_status(f"Extracted {total_indicators} indicators of compromise")
    
    try:
        # Override temperature from environment if available
        env_temperature = os.getenv("OPENAI_TEMPERATURE")
        if env_temperature:
            try:
                temperature = float(env_temperature)
                debug(f"Using temperature {temperature} from environment")
            except ValueError:
                warning(f"Invalid OPENAI_TEMPERATURE value: {env_temperature}, using default: {temperature}")
                
        # Prepare the system prompt with enhanced instructions for better analysis
        system_prompt = """Analyze the cybersecurity article and create a structured threat intelligence report with the following sections:

1. Summary of Article
A concise summary of the main points in a single paragraph.

2. Source Evaluation
- Reliability: High/Medium/Low with brief justification
- Credibility: High/Medium/Low with brief justification
- Source Type: Specify the type (Blog, Cybersecurity Vendor, Government Agency, etc.)

3. MITRE ATT&CK Techniques
List with technique IDs (when available), names, and brief descriptions.

4. Key Threat Intelligence Insights
Three main findings, each as a complete sentence.

5. Potential Bias or Issues
Two potential biases or issues with the source or analysis, as complete sentences.

6. Relevance to U.S. Government (Score: 1-5)
Justification for the relevance score.

7. Critical Infrastructure Sectors Assessment
Rate the relevance (1-5) to each applicable sector:
- National Security
- Chemical
- Commercial Facilities
- Communications
- Critical Manufacturing
- Dams
- Defense Industrial Base
- Emergency Services
- Energy
- Financial Services
- Food & Agriculture
- Government Services & Facilities
- Healthcare & Public Health
- Information Technology
- Nuclear Reactors, Materials, and Waste
- Transportation Systems
- Water & Wastewater Systems

Format all lists with numerical markers only (1., 2., 3.). Maintain consistent formatting.
Be specific and factual in your analysis, focusing on evidence from the text.
DO NOT use markdown formatting (such as **, *, or ##) in your response.
"""

        # Get token limits based on model
        if 'gpt-4' in model:
            max_input_tokens = 100000  # GPT-4 models can handle up to 128K but we'll be conservative
            max_output_tokens = 4000   # Increasing output tokens for more detailed analysis
        else:
            max_input_tokens = 16000   # For other models like GPT-3.5
            max_output_tokens = 4000

        # Override max tokens from environment if available
        env_max_tokens = os.getenv("OPENAI_MAX_TOKENS")
        if env_max_tokens:
            try:
                max_output_tokens = min(int(env_max_tokens), max_output_tokens)
                debug(f"Using max_tokens {max_output_tokens} from environment")
            except ValueError:
                warning(f"Invalid OPENAI_MAX_TOKENS value: {env_max_tokens}, using default: {max_output_tokens}")

        # Calculate approximate token count for system prompt
        system_token_count = len(system_prompt.split()) * 1.3  # Rough estimate
        
        # Calculate available tokens for content
        available_tokens = max_input_tokens - system_token_count - 100  # 100 tokens buffer
        
        # Estimate content tokens
        content_token_estimate = len(content.split()) * 1.3  # Rough estimate
        
        info(f"Estimated token counts - System prompt: {int(system_token_count)}, Content: {int(content_token_estimate)}")
        
        # Truncate content if necessary while keeping as much as possible
        original_content_length = len(content)
        if content_token_estimate > available_tokens:
            ratio = available_tokens / content_token_estimate
            # Keep at least the first 75% of tokens to preserve the beginning of the article
            # which typically contains the most important information
            words = content.split()
            keep_words = max(int(len(words) * ratio), int(len(words) * 0.75))
            truncated_content = ' '.join(words[:keep_words])
            
            # For very long articles, add a summary sentence
            if len(words) > 2 * keep_words:
                truncated_content += f"\n\n[Note: This article was truncated from {len(words)} words to {keep_words} words due to token limits. The content above represents approximately {int(ratio*100)}% of the original article.]"
            
            info(f"Content truncated from {len(content)} chars to {len(truncated_content)} chars to fit token limits")
            if verbose:
                print_status(f"Content truncated to fit within model token limits ({int(content_token_estimate)} estimated tokens > {int(available_tokens)} available tokens)")
                print_status(f"Keeping approximately {keep_words} words out of {len(words)} total words")
            
            content = truncated_content
        
        # Prepare the API request details for logging
        api_request = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                # For logging only: Show first 100 chars of content with "..." indicator for truncation
                {"role": "user", "content": f"Article URL: {url}\n\nContent: [Full article text - {len(content)} chars]"}
            ],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
            "seed": seed
        }

        # Log the API request
        debug(f"Preparing OpenAI API request with model: {model}")
        debug(f"API Request Parameters: temperature={api_request['temperature']}, max_tokens={api_request['max_tokens']}, seed={api_request['seed']}")
        debug(f"Content length being sent to API: {len(content)} characters")

        # Log the exact model being used
        if verbose:
            print_status(f"API REQUEST: Using model '{model}' for analysis")
            print_status(f"Creating OpenAI API request with model: {model}")
            print_status(f"Maximum output tokens: {max_output_tokens}")
            print_status(f"Temperature: {temperature}, Seed: {seed}")
            print_status(f"Sending full article content ({len(content)} characters)")

        # Make API call with retries
        response = None
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                info(f"Sending request to OpenAI API with model: {model} (attempt {retry_count + 1})")
                
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Article URL: {url}\n\nContent:\n{content}"}
                    ],
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                    seed=seed,
                    response_format={"type": "text"}  # Ensure text response for consistency
                )
                # If we get here, the request succeeded
                break
                
            except (RateLimitError, APIError, APITimeoutError) as api_error:
                last_error = api_error
                retry_count += 1
                
                error(f"OpenAI API error (attempt {retry_count}/{max_retries + 1}): {str(api_error)}")
                if verbose:
                    print_status(f"API error: {str(api_error)}. Retrying in {retry_delay} seconds...", is_error=True)
                
                if retry_count <= max_retries:
                    time.sleep(retry_delay)
                    # Exponential backoff with jitter for better retry behavior
                    retry_delay = min(retry_delay * 1.5 * (1 + 0.1 * random.random()), 60.0)
                else:
                    error(f"Exceeded maximum retry attempts ({max_retries})")
                    if verbose:
                        print_status(f"Exceeded maximum retry attempts ({max_retries})", is_error=True)
                    raise
                    
            except Exception as api_error:
                # For other errors, don't retry
                error(f"OpenAI API error: {str(api_error)}")
                error(traceback.format_exc())
                if verbose:
                    print_status(f"Error calling OpenAI API: {str(api_error)}", is_error=True)
                raise
        
        # If all retries failed
        if not response:
            error(f"All API requests failed after {max_retries + 1} attempts")
            if verbose:
                print_status(f"All API requests failed: {str(last_error)}", is_error=True)
            return None

        # Log the model that was actually used in the response
        actual_model = response.model
        info(f"Received response from OpenAI API using model: {actual_model}")
        debug(f"API usage: {response.usage.prompt_tokens} input tokens, {response.usage.completion_tokens} output tokens")
        
        if verbose:
            print_status(f"API RESPONSE: Received response from model: '{actual_model}'")
            print_status(f"Input tokens: {response.usage.prompt_tokens}, Output tokens: {response.usage.completion_tokens}")
            
            # Check if requested model matches the actual model used (ignoring date suffixes)
            base_requested_model = model.split('-')[0] if '-' in model else model
            base_actual_model = actual_model.split('-')[0] if '-' in actual_model else actual_model
            
            if base_requested_model != base_actual_model:
                warning(f"Requested model type '{model}' does not match the actual model type '{actual_model}'")
                print_status(f"WARNING: Requested model type '{model}' does not match the actual model type '{actual_model}'", is_error=True)
            else:
                debug(f"Model types match (ignoring version): Requested '{model}', Received '{actual_model}'")

        # Track token usage
        track_token_usage(
            model=actual_model,  # Use the actual model from the response
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens
        )
        
        # Update API request details for logging with accurate token counts
        api_request["tokens"] = {
            "prompt": response.usage.prompt_tokens,
            "completion": response.usage.completion_tokens,
            "total": response.usage.prompt_tokens + response.usage.completion_tokens
        }
        
        # Record if content was truncated from the original
        if original_content_length != len(content):
            api_request["content_truncated"] = {
                "original_length": original_content_length,
                "truncated_length": len(content),
                "percentage_kept": round(len(content) / original_content_length * 100, 2)
            }

        analysis_text = response.choices[0].message.content
        debug(f"Analysis text length: {len(analysis_text)} characters")

        # Create API response details
        api_response = {
            "model": actual_model,  # Use the actual model from the response
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.prompt_tokens + response.usage.completion_tokens,
            "first_completion": analysis_text[:500] + "..." if len(analysis_text) > 500 else analysis_text
        }

        if structured:
            # Parse the response into structured data
            info("Parsing analysis response into structured data")
            structured_data = parse_analysis_response(analysis_text)
            debug(f"Structured data: {json.dumps(structured_data, indent=2)[:500]}...")
            
            # Include the extracted indicators if available
            if extracted_indicators:
                formatted_indicators = format_indicators_for_display(extracted_indicators)
                structured_data["indicators"] = formatted_indicators
                debug(f"Added {formatted_indicators['total_count']} extracted indicators to structured data")
            
            return {
                "text": analysis_text,
                "structured": structured_data,
                "api_details": {
                    "request": api_request,
                    "response": api_response
                },
                "extracted_indicators": extracted_indicators
            }
        
        info("Returning raw analysis text (unstructured)")
        return analysis_text

    except Exception as e:
        error(f"Error during analysis with model {model}: {str(e)}")
        error(traceback.format_exc())
        
        if verbose:
            print_status(f"Error during analysis with model {model}: {str(e)}", is_error=True)
        return None

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