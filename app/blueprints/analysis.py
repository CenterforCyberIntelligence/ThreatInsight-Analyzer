from flask import Blueprint, request, jsonify, render_template, send_file, abort, Response, current_app
import time
import os
import re
import traceback
import validators
import html
from typing import Dict, Any, Optional, Tuple, List
from urllib.parse import urlparse
from datetime import datetime

from app.utilities.article_extractor import extract_article_content
from app.utilities.article_analyzer import analyze_article, parse_analysis_response
from app.utilities.indicator_extractor import extract_indicators, format_indicators_for_display
from app.utilities.export import (
    export_analysis_as_json, export_analysis_as_csv, 
    export_analysis_as_markdown, export_analysis_as_pdf
)
from app.utilities.logger import get_logger, print_status, error, warning, info, debug
from app.models.database import store_analysis, update_analysis, get_analysis_by_url, track_token_usage, store_indicators, get_indicators_by_url
from app.config.config import Config

analysis_bp = Blueprint('analysis', __name__)

# List of allowed top-level domains (expand as needed)
ALLOWED_TLDS = [
    'com', 'org', 'net', 'gov', 'edu', 'mil', 'int', 'io', 'co',
    'uk', 'ca', 'au', 'eu', 'de', 'fr', 'jp', 'ru', 'cn', 'in',
    'br', 'mx', 'za', 'ch', 'se', 'no', 'dk', 'fi', 'nl', 'be'
]

def load_blocked_domains():
    """
    Load blocked domains from a text file
    
    Returns:
        List of blocked domain strings
    """
    domains = []
    try:
        blocked_domains_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'blocked_domains.txt')
        with open(blocked_domains_path, 'r') as f:
            for line in f:
                # Skip empty lines and comments
                line = line.strip()
                if line and not line.startswith('#'):
                    domains.append(line)
        return domains
    except Exception as e:
        # Log the error but don't crash - return a default minimal list if file can't be read
        warning(f"Error loading blocked domains: {str(e)}")
        return ['example-malicious-site.com', 'known-phishing-domain.net']

# Load blocked domains from file
BLOCKED_DOMAINS = load_blocked_domains()

def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL for security and formatting
    
    Args:
        url: The URL to validate
        
    Returns:
        Tuple containing:
            - Boolean indicating if URL is valid
            - Error message if validation failed, None if validation succeeded
    """
    if not url:
        return False, "URL is required"
    
    # Basic sanitization - strip whitespace and encode HTML entities
    url = url.strip()
    
    # Basic URL validation using validators package
    if not validators.url(url):
        return False, "Invalid URL format. Please provide a valid URL including the protocol (http:// or https://)"
    
    # Parse the URL to get components
    parsed_url = urlparse(url)
    
    # Protocol check - only allow HTTP and HTTPS
    if parsed_url.scheme not in ['http', 'https']:
        return False, "Only HTTP and HTTPS protocols are supported"
    
    # Extract domain and TLD
    domain = parsed_url.netloc.lower()
    
    # Remove port number if present
    if ':' in domain:
        domain = domain.split(':')[0]
    
    # Block IP addresses in domain names (including disguised ones)
    ip_pattern = re.compile(r'\d{1,3}[.-]\d{1,3}[.-]\d{1,3}[.-]\d{1,3}')
    if ip_pattern.search(domain) or 'ip-' in domain:
        return False, "IP addresses in domain names are not allowed"
    
    # Check for blocked domains - exact match or subdomain
    for blocked in BLOCKED_DOMAINS:
        if domain == blocked or domain.endswith('.' + blocked):
            return False, "This domain is blocked"
    
    # TLD validation - extract the actual TLD more accurately
    try:
        # Split by periods and get the last part for TLD check
        domain_parts = domain.split('.')
        tld = domain_parts[-1]
        
        # Handle cases with complex TLDs (e.g., co.uk)
        if len(domain_parts) >= 3 and domain_parts[-2] + '.' + domain_parts[-1] in ['co.uk', 'com.au', 'co.jp']:
            tld = domain_parts[-2] + '.' + domain_parts[-1]
        
        # Check if TLD is in allowed list
        if tld not in ALLOWED_TLDS:
            return False, f"Domain TLD '.{tld}' is not in the allowed list"
    except Exception as e:
        warning(f"Error in TLD validation: {str(e)}")
        return False, "Invalid domain format"
    
    return True, None

@analysis_bp.route('/analyze', methods=['POST'])
def analyze():
    """
    Endpoint that handles article analysis requests.
    Accepts a URL and model selection.
    With HTMX, returns an HTML fragment for loading status.
    """
    # Get and sanitize URL
    url = request.form.get('url', '')
    
    # Validate URL
    is_valid, error_message = validate_url(url)
    if not is_valid:
        return render_template('partials/analysis_error.html', 
                            error=error_message,
                            error_type='extraction',
                            error_title='URL Validation Error',
                            url=url,
                            model=html.escape(request.form.get('model', Config.get_default_model()))), 400
    
    # Get selected model from form or use default (sanitize input)
    selected_model = html.escape(request.form.get('model', Config.get_default_model()))
    print_status(f"User selected model: {selected_model}")
    
    # Check if this is an HTMX request 
    is_htmx = request.headers.get('HX-Request') == 'true'
    
    # Return the loading indicator with the first step
    if is_htmx:
        return render_template('partials/analysis_loading.html', 
                              url=url, 
                              model=selected_model,
                              step='extract')
    
    # If not HTMX, use the old JSON response format for backward compatibility
    return jsonify({'status': 'started', 'url': url, 'model': selected_model})

@analysis_bp.route('/analysis/status', methods=['GET'])
def analysis_status():
    """
    Endpoint to check the status of an ongoing analysis.
    Used by HTMX for step-by-step loading updates.
    """
    url = request.args.get('url', '')
    
    # Validate URL
    is_valid, error_message = validate_url(url)
    if not is_valid:
        return render_template('partials/analysis_error.html', 
                              error=error_message,
                              error_type='extraction',
                              error_title='URL Validation Error',
                              url=url,
                              model=html.escape(request.args.get('model', Config.get_default_model()))), 400
    
    step = html.escape(request.args.get('step', 'extract'))
    model = html.escape(request.args.get('model', Config.get_default_model()))
    
    print_status(f"Analysis status check: URL={url}, Step={step}, Model={model}")
    
    # For demo purposes, we're just returning the next loading step
    # In a real implementation, you would check the actual status
    return render_template('partials/analysis_loading.html', 
                          url=url, 
                          model=model,
                          step=step)

@analysis_bp.route('/analysis/result', methods=['GET'])
def analysis_result():
    """
    Endpoint to get the final analysis result.
    Used by HTMX after all loading steps are complete.
    Can also be directly accessed to retrieve cached results.
    """
    url = request.args.get('url', '')
    
    # Validate URL
    is_valid, error_message = validate_url(url)
    if not is_valid:
        return render_template('partials/analysis_error.html', 
                              error=error_message), 400
    
    model = html.escape(request.args.get('model', Config.get_default_model()))
    print_status(f"Analysis result request: URL={url}, Model={model}")
    
    # Check cache for existing analysis
    existing_analysis = get_analysis_by_url(url)
    if existing_analysis:
        print_status(f"Found existing analysis for {url}, using cached results with model: {existing_analysis['model']}")
        
        # Track token usage for cached result (estimate input tokens)
        estimated_input_tokens = len(existing_analysis['raw_text']) // 4
        track_token_usage(existing_analysis['model'], estimated_input_tokens, 0, cached=True)
        
        # Prepare API details for template
        cached_api_details = {
            "request": {
                "model": existing_analysis["model"],
                "tokens": {
                    "prompt": estimated_input_tokens,
                    "completion": 0,
                    "total": estimated_input_tokens
                }
            },
            "response": {
                "model": existing_analysis["model"],
                "cache_hit": True
            }
        }
        
        # Format analyzed_at timestamp
        analyzed_at = "Unknown time"
        if existing_analysis['created_at']:
            try:
                # Try to parse ISO format timestamp
                from datetime import datetime
                dt = datetime.fromisoformat(existing_analysis['created_at'])
                analyzed_at = dt.strftime('%B %d, %Y at %H:%M')
            except:
                # If parsing fails, use the original format
                analyzed_at = existing_analysis['created_at']
        
        return render_template('partials/analysis_result.html',
                              url=url,
                              model=existing_analysis['model'],
                              analysis=existing_analysis['raw_text'],
                              structured_analysis=existing_analysis['structured_data'],
                              content_length=existing_analysis['content_length'],
                              extraction_time=existing_analysis.get('extraction_time', 0),
                              analysis_time=existing_analysis.get('analysis_time', 0),
                              api_details=cached_api_details,
                              cached=True,
                              analyzed_at=analyzed_at)
    
    try:
        # Extract article content
        print_status(f"Starting new analysis flow: URL={url}, Model={model}")
        print_status(f"Web request: Starting extraction from {url}")
        extraction_start = time.time()
        article_content = extract_article_content(url, verbose=True)
        extraction_time = time.time() - extraction_start
        
        if not article_content or len(article_content) < 100:
            print_status(f"Web request: Extraction failed or content too short", is_error=True)
            return render_template('partials/analysis_error.html',
                                  error='Failed to extract meaningful content from the article. Please check the URL and try again.',
                                  error_type='extraction',
                                  error_title='Content Extraction Error',
                                  url=url,
                                  model=model), 400
        
        # Analyze content with selected model
        print_status(f"Web request: Starting analysis using model: {model}")
        analysis_start = time.time()
        analysis_result = analyze_article(article_content, url, model=model, verbose=True, structured=True, extract_iocs=True)
        analysis_time = time.time() - analysis_start
        
        if not analysis_result:
            print_status(f"Web request: Analysis failed with model {model}", is_error=True)
            return render_template('partials/analysis_error.html',
                                  error='Analysis failed. The OpenAI API may be experiencing issues.',
                                  error_type='openai_api',
                                  error_title='OpenAI API Error',
                                  url=url,
                                  model=model), 500
        
        # Get indicators from the result or extract them if missing
        indicators = None
        if "extracted_indicators" in analysis_result and analysis_result["extracted_indicators"]:
            indicators = format_indicators_for_display(analysis_result["extracted_indicators"])
            print_status(f"Web request: {indicators['total_count']} indicators extracted from article")
        
        # Store analysis in database for future retrieval
        store_analysis(
            url=url,
            title=url,  # Using URL as title since we don't have a better title available here
            model=model,
            raw_analysis=analysis_result["text"],
            structured_analysis=analysis_result["structured"],
            content_length=len(article_content),
            extraction_time=extraction_time,
            analysis_time=analysis_time
        )
        
        # Prepare API details for template
        api_details = analysis_result.get("api_details", None)
        
        # Log detailed information about what we're sending to the template
        import json
        info("=========== ANALYSIS DATA SENT TO TEMPLATE ===========")
        info(f"Raw analysis text type: {type(analysis_result['text'])}")
        info(f"Raw analysis text length: {len(analysis_result['text'])}")
        info(f"Raw analysis text sample: {analysis_result['text'][:500]}...")
        info(f"Structured data keys: {list(analysis_result['structured'].keys())}")
        info("=========== END ANALYSIS DATA DETAILS ===========")
        
        # Return the analysis result template
        return render_template('partials/analysis_result.html',
                              url=url,
                              model=model,
                              analysis=analysis_result["text"],
                              structured_analysis=analysis_result["structured"],
                              content_length=len(article_content),
                              extraction_time=extraction_time,
                              analysis_time=analysis_time,
                              api_details=api_details,
                              cached=False,
                              analyzed_at="Just now")
    
    except Exception as e:
        error(f"Error in analysis_result: {str(e)}")
        import traceback
        error(traceback.format_exc())
        
        # Determine error type from exception
        error_type = 'unknown'
        error_title = 'Unexpected Error'
        
        if 'openai' in str(e).lower() or 'api' in str(e).lower():
            error_type = 'openai_api'
            error_title = 'OpenAI API Error'
        elif 'extraction' in str(e).lower() or 'url' in str(e).lower() or 'http' in str(e).lower():
            error_type = 'extraction'
            error_title = 'Content Extraction Error'
        
        return render_template('partials/analysis_error.html',
                              error=f'Error during analysis: {str(e)}',
                              error_type=error_type,
                              error_title=error_title,
                              url=url,
                              model=model,
                              details=traceback.format_exc() if os.getenv('FLASK_DEBUG') == '1' else None), 500

@analysis_bp.route('/recent-analyses', methods=['GET'])
def recent_analyses():
    """
    Endpoint to get recent analyses.
    Used by HTMX to refresh the recent analyses list.
    """
    from app.models.database import get_recent_analyses
    
    # Get the 5 most recent analyses
    recent = get_recent_analyses(5)
    
    return render_template('partials/recent_analyses.html', recent_analyses=recent)

@analysis_bp.route('/analyze-form', methods=['GET'])
def analyze_form():
    """
    Return just the analysis form for closing the report
    This ensures that closing the analysis report doesn't reload the entire page
    """
    # Return an empty div with the same ID as the analysis result container
    # This ensures the container exists when reopening another report
    return '<div id="analysis-result-container"></div>'

@analysis_bp.route('/debug/raw-json', methods=['GET'])
def debug_raw_json():
    """
    Debug endpoint to return the raw JSON for an analysis.
    This helps diagnose JSON formatting issues by viewing the raw data.
    
    This endpoint is protected and only available in development environments.
    """
    from flask import Response, current_app
    import re
    from app.config.config import Config
    
    # Only allow this endpoint in development mode
    if not current_app.config.get('DEBUG', False):
        return jsonify({"error": "This endpoint is only available in development mode"}), 403
    
    # Basic authentication check - in a real implementation, this would use proper authentication
    auth_token = request.args.get('auth_token', '')
    admin_token = Config.ADMIN_DEBUG_TOKEN
    
    if not admin_token or auth_token != admin_token:
        return jsonify({"error": "Authentication required"}), 401
    
    url = request.args.get('url', '')
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    existing_analysis = get_analysis_by_url(url)
    if not existing_analysis:
        return jsonify({"error": "No analysis found for this URL"}), 404
    
    # Log what we're returning
    info(f"DEBUG: Returning raw JSON for URL: {url}")
    info(f"DEBUG: JSON content type: {type(existing_analysis['raw_text'])}")
    info(f"DEBUG: JSON content length: {len(existing_analysis['raw_text'])}")
    
    # Create a meaningful filename from the URL
    # Extract the domain from the URL
    domain = urlparse(url).netloc
    
    # Remove port if present
    if ':' in domain:
        domain = domain.split(':')[0]
    
    # Remove www. if present
    if domain.startswith('www.'):
        domain = domain[4:]
    
    # Replace dots with underscores
    domain = domain.replace('.', '_')
    
    # Add timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create filename: domain_timestamp.json
    filename = f"analysis_{domain}_{timestamp}.json"
    
    # Sanitize filename (remove any invalid characters)
    filename = re.sub(r'[^\w\-\.]', '_', filename)
    
    # Add an audit log entry for security monitoring
    warning(f"Debug endpoint accessed for URL: {url} by client: {request.remote_addr}")
    
    # Return the raw JSON with proper content type
    return Response(
        existing_analysis['raw_text'],
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename={filename}'
        }
    )

@analysis_bp.route('/analysis/refresh', methods=['GET'])
def refresh_analysis():
    """
    Endpoint to refresh/reanalyze a previously analyzed URL.
    Bypasses cache and forces a new analysis using the latest processing techniques.
    """
    url = request.args.get('url', '')
    
    # Validate URL
    is_valid, error_message = validate_url(url)
    if not is_valid:
        return render_template('partials/analysis_error.html', 
                              error=error_message,
                              error_type='extraction',
                              error_title='URL Validation Error',
                              url=url,
                              model=html.escape(request.args.get('model', Config.get_default_model()))), 400
    
    model = html.escape(request.args.get('model', Config.get_default_model()))
    print_status(f"Refreshing analysis for URL={url} with Model={model}")
    
    # Check cache for existing analysis to maintain original creation date
    existing_analysis = get_analysis_by_url(url)
    if not existing_analysis:
        print_status(f"No existing analysis found for {url}, this will be treated as a new analysis")
    else:
        print_status(f"Found existing analysis for {url} from {existing_analysis['created_at']}")
    
    try:
        # Extract article content
        print_status(f"Starting refresh analysis: URL={url}, Model={model}")
        print_status(f"Web request: Starting extraction from {url}")
        extraction_start = time.time()
        article_content = extract_article_content(url, verbose=True)
        extraction_time = time.time() - extraction_start
        
        if not article_content or len(article_content) < 100:
            print_status(f"Web request: Extraction failed or content too short", is_error=True)
            return render_template('partials/analysis_error.html',
                                  error='Failed to extract meaningful content from the article. Please check the URL and try again.',
                                  error_type='extraction',
                                  error_title='Content Extraction Error',
                                  url=url,
                                  model=model), 400
        
        # Analyze content with selected model
        print_status(f"Web request: Starting analysis using model: {model}")
        analysis_start = time.time()
        analysis_result = analyze_article(article_content, url, model=model, verbose=True, structured=True, extract_iocs=True)
        analysis_time = time.time() - analysis_start
        
        if not analysis_result:
            print_status(f"Web request: Analysis failed with model {model}", is_error=True)
            return render_template('partials/analysis_error.html',
                                  error='Analysis failed to produce valid results.',
                                  error_type='openai_api',
                                  error_title='Invalid Response Format',
                                  url=url,
                                  model=model), 500
        
        # Process and validate analysis results
        if not isinstance(analysis_result, dict) or "structured" not in analysis_result:
            print_status(f"Web request: Invalid structured data format from model {model}, falling back to text parsing", is_error=True)
            if isinstance(analysis_result, str):
                structured_data = parse_analysis_response(analysis_result)
                analysis_result = {
                    "text": analysis_result,
                    "structured": structured_data
                }
            else:
                return render_template('partials/analysis_error.html',
                                  error='Analysis failed to produce valid results.',
                                  error_type='openai_api',
                                  error_title='Invalid Response Format',
                                  url=url,
                                  model=model), 500
        
        # Get API details if available
        api_details = analysis_result.get("api_details", None)
        
        # Extract missing summary if needed
        if not analysis_result["structured"]["summary"]:
            print_status(f"Web request: Summary is missing, attempting to extract from raw text", is_error=True)
            summary_match = re.search(r'1\.\s*Summary of Article\s*(.*?)(?=2\.\s*Source Evaluation|\Z)', analysis_result["text"], re.DOTALL)
            if summary_match:
                analysis_result["structured"]["summary"] = summary_match.group(1).strip()

        # Extract missing MITRE techniques if needed
        if not analysis_result["structured"]["mitre_techniques"]:
            print_status(f"Web request: MITRE techniques are missing, attempting to extract from raw text", is_error=True)
            mitre_section = re.search(r'(?:3\.\s*)?MITRE\s+ATT&CK\s+Techniques:?(.*?)(?=(?:4\.\s*)?Key\s+Threat\s+Intelligence|\Z)', analysis_result["text"], re.DOTALL | re.IGNORECASE)
            if mitre_section:
                mitre_text = mitre_section.group(1).strip()
                print_status(f"Found MITRE section text: {mitre_text[:200]}...")
                
                if mitre_text and not any(x in mitre_text.lower() for x in ['n/a', 'none', 'not applicable']):
                    from app.utilities.article_analyzer import parse_mitre_technique
                    
                    # First try numbered list format (most common)
                    mitre_items = re.findall(r'(?:^|\n)\d+\.\s*([Tt]\d+(?:\.\d+)?)\s*(?:-|:)\s*([^:]+?)(?::|(?:\s*-\s*))?\s*(.*?)(?=(?:\n\d+\.)|$)', mitre_text, re.DOTALL)
                    
                    # If no results, try alternative formats
                    if not mitre_items:
                        print_status("First MITRE extraction pattern failed, trying alternative pattern")
                        mitre_items = re.findall(r'(?:^|\n)(?:\d+\.|-)?\s*(?:\*\*)?([Tt]\d+(?:\.\d+)?)(?:\*\*)?\s*(?:-|:|–)\s*(?:\*\*)?([^:\n]+?)(?:\*\*)?(?::|(?:\s*-\s*))?\s*(.*?)(?=(?:\n(?:\d+\.|-))|$)', mitre_text, re.DOTALL)
                    
                    # Log what we found
                    print_status(f"Found {len(mitre_items)} MITRE techniques")
                    
                    for item in mitre_items:
                        technique_id = item[0].strip() if item[0] else ""
                        technique_name = item[1].strip() if len(item) > 1 else ""
                        technique_desc = item[2].strip() if len(item) > 2 else ""
                        
                        print_status(f"MITRE technique parsed: ID={technique_id}, Name={technique_name}")
                        
                        if technique_id:  # Only add if we have at least an ID
                            analysis_result["structured"]["mitre_techniques"].append({
                                "id": technique_id,
                                "name": technique_name,
                                "description": technique_desc
                            })

        # Extract missing key insights if needed
        if not analysis_result["structured"]["key_insights"]:
            print_status(f"Web request: Key insights are missing, attempting to extract from raw text", is_error=True)
            insights_section = re.search(r'4\.\s*Key Threat Intelligence Insights:(.*?)(?=5\.\s*Potential Bias or Issues|\Z)', analysis_result["text"], re.DOTALL)
            if insights_section:
                insights_text = insights_section.group(1).strip()
                # Extract numbered items
                insights = re.findall(r'(?:^|\n)\d+\.\s*(.*?)(?=(?:\n\d+\.)|$)', insights_text, re.DOTALL)
                analysis_result["structured"]["key_insights"] = [insight.strip() for insight in insights if insight.strip()]

        # Extract missing potential issues if needed
        if not analysis_result["structured"]["potential_issues"]:
            print_status(f"Web request: Potential issues are missing, attempting to extract from raw text", is_error=True)
            issues_section = re.search(r'5\.\s*Potential Bias or Issues:(.*?)(?=6\.\s*Relevance to U\.S\. Government|\Z)', analysis_result["text"], re.DOTALL)
            if issues_section:
                issues_text = issues_section.group(1).strip()
                # Extract numbered items
                issues = re.findall(r'(?:^|\n)\d+\.\s*(.*?)(?=(?:\n\d+\.)|$)', issues_text, re.DOTALL)
                analysis_result["structured"]["potential_issues"] = [issue.strip() for issue in issues if issue.strip()]

        # Generate title from summary
        title = url
        if analysis_result["structured"]["summary"]:
            first_sentence = analysis_result["structured"]["summary"].split('.')[0]
            if len(first_sentence) > 10:
                title = first_sentence[:100] + ('...' if len(first_sentence) > 100 else '')

        # Log the final result with model information
        print_status(f"Analysis complete: URL={url}, Model={model}, Content Length={len(article_content)}")

        # Store analysis in database
        store_success = store_analysis(
            url=url,
            title=title,
            content_length=len(article_content),
            extraction_time=extraction_time,
            analysis_time=analysis_time,
            model=model,
            raw_analysis=analysis_result["text"],
            structured_analysis=analysis_result["structured"]
        )
        
        # Get the newly stored article ID
        if store_success:
            stored_article = get_analysis_by_url(url)
            if stored_article and 'id' in stored_article and 'extracted_indicators' in analysis_result:
                article_id = stored_article['id']
                # Store extracted indicators
                if analysis_result['extracted_indicators']:
                    print_status(f"Storing extracted indicators for article_id: {article_id}")
                    store_success = store_indicators(article_id, analysis_result['extracted_indicators'])
                    if store_success:
                        print_status(f"Successfully stored indicators for article_id: {article_id}")
                    else:
                        print_status(f"Failed to store indicators for article_id: {article_id}", is_error=True)

        return render_template('partials/analysis_result.html',
                             url=url,
                             model=model,
                             analysis=analysis_result["text"],
                             structured_analysis=analysis_result["structured"],
                             content_length=len(article_content),
                             extraction_time=extraction_time,
                             analysis_time=analysis_time,
                             api_details=api_details,
                             cached=False)
        
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Web request error with model {model}: {str(e)}")
        error(f"Traceback: {error_details}")
        print_status(f"Web request error with model {model}: {str(e)}", is_error=True)
        print_status(error_details, is_error=True)
        return render_template('partials/analysis_error.html',
                             error=f"An error occurred: {str(e)}",
                             error_type='unknown',
                             error_title='Unexpected Error',
                             url=url,
                             model=model,
                             details=error_details if os.getenv('FLASK_DEBUG') == '1' else None), 500

@analysis_bp.route('/export/<format_type>')
def export_analysis(format_type):
    """
    Export analysis in the specified format.
    Supports JSON, CSV, PDF, and Markdown formats.
    """
    url = request.args.get('url', '')
    
    # Validate URL
    is_valid, error_message = validate_url(url)
    if not is_valid:
        return jsonify({
            "success": False,
            "message": f"Invalid URL: {error_message}"
        }), 400
    
    # Format type from URL parameter
    format_type = format_type.lower()
    
    # Check cache for existing analysis
    existing_analysis = get_analysis_by_url(url)
    if not existing_analysis:
        return jsonify({
            "success": False,
            "message": "No analysis found for this URL"
        }), 404
    
    # Extract domain for filename
    domain = None
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
    except:
        domain = "unknown-domain"
    
    # Choose export function based on format type
    export_functions = {
        'json': export_analysis_as_json,
        'csv': export_analysis_as_csv,
        'markdown': export_analysis_as_markdown, 
        'pdf': export_analysis_as_pdf
    }
    
    if format_type not in export_functions:
        return jsonify({
            "success": False,
            "message": f"Unsupported format: {format_type}. Supported formats are: json, csv, markdown, pdf"
        }), 400
    
    # Prepare data for export
    analysis_data = {
        "summary": existing_analysis.get("structured_data", {}).get("summary", ""),
        "source_evaluation": existing_analysis.get("structured_data", {}).get("source_evaluation", {}),
        "threat_actors": existing_analysis.get("structured_data", {}).get("threat_actors", []),
        "mitre_techniques": existing_analysis.get("structured_data", {}).get("mitre_techniques", []),
        "key_insights": existing_analysis.get("structured_data", {}).get("key_insights", []),
        "source_bias": existing_analysis.get("structured_data", {}).get("potential_issues", []),
        "intelligence_gaps": existing_analysis.get("structured_data", {}).get("intelligence_gaps", []),
        "critical_infrastructure_sectors": existing_analysis.get("structured_data", {}).get("critical_sectors", {})
    }
    
    # Export data in the requested format
    export_function = export_functions[format_type]
    export_result = export_function(analysis_data, domain)
    
    if not export_result.get("success", False):
        return jsonify({
            "success": False,
            "message": export_result.get("message", "Failed to export analysis")
        }), 500
    
    # Return the file for download
    file_path = export_result.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return jsonify({
            "success": False,
            "message": "Failed to generate export file"
        }), 500
    
    # Get filename from path
    filename = os.path.basename(file_path)
    
    # Set proper content type based on format
    content_types = {
        'json': 'application/json',
        'csv': 'text/csv',
        'markdown': 'text/markdown',
        'pdf': 'application/pdf'
    }
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename,
        mimetype=content_types.get(format_type, 'application/octet-stream')
    )

@analysis_bp.route('/api/check_extraction_status/<path:url>', methods=['GET'])
def check_extraction_status(url):
    """
    Endpoint to check if an article has been extracted and analyzed.
    Used by HTMX to trigger backend processes when needed.
    """
    print_status(f"Checking extraction status for URL: {url}")
    
    # URL validation is handled internally in get_analysis_by_url
    existing_analysis = get_analysis_by_url(url)
    
    # This endpoint doesn't need to return any content, it's just used
    # as a trigger for HTMX to potentially perform background operations
    return jsonify({"status": "ok", "exists": existing_analysis is not None}) 