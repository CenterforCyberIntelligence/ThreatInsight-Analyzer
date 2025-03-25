from flask import Blueprint, request, jsonify, render_template, send_file, abort, Response, current_app
import time
import os
import re
import traceback
import validators
import html
import requests
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
from app.utilities.sanitizers import sanitize_input
from app.models.database import store_analysis, update_analysis, get_analysis_by_url, track_token_usage, store_indicators, get_indicators_by_url, get_indicators_by_article_id
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
    
    # Basic sanitization - strip whitespace
    url = url.strip()
    
    # Look for signs of tampering or encoding evasion
    if '%' in url:
        # Check for suspicious double-encoding patterns
        suspicious_patterns = ['%25', '%26', '%3C', '%3E', '%27', '%22', '%00']
        for pattern in suspicious_patterns:
            if pattern in url:
                return False, f"Suspicious URL encoding detected ({pattern})"
    
    # Check for NULL bytes which may indicate tampering
    if '\0' in url:
        return False, "NULL bytes are not allowed in URLs"
    
    # Basic URL validation using validators package
    if not validators.url(url):
        return False, "Invalid URL format. Please provide a valid URL including the protocol (http:// or https://)"
    
    # Parse the URL to get components
    parsed_url = urlparse(url)
    
    # Protocol check - only allow HTTP and HTTPS
    if parsed_url.scheme not in ['http', 'https']:
        return False, "Only HTTP and HTTPS protocols are supported"
    
    # Check if URL returns a 200 response
    try:
        # Make a HEAD request to avoid downloading the entire page content
        response = requests.head(url, timeout=10, allow_redirects=True)
        
        # If HEAD is not supported by the server, try a limited GET request
        if response.status_code >= 400:
            response = requests.get(url, timeout=10, stream=True, allow_redirects=True)
            # Close the connection without downloading the entire content
            if hasattr(response, 'close'):
                response.close()
        
        status_code = response.status_code
        if status_code != 200:
            return False, f"URL returned a non-200 status code: {status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"Failed to connect to URL: {str(e)}"
    
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
    
    # Check for overly complex URLs that might indicate evasion attempts
    if len(url) > 2000:
        return False, "URL exceeds maximum allowed length"
        
    if url.count('?') > 1 or url.count('#') > 1:
        return False, "URL contains multiple query or fragment parts"
    
    # Check for unusual character sequences that might indicate evasion
    unusual_sequences = ['../', '.\\', './\\', '\\\\', '///', '&#']
    for seq in unusual_sequences:
        if seq in url:
            return False, f"URL contains suspicious character sequence: {seq}"
    
    return True, None

@analysis_bp.route('/analyze', methods=['POST'])
def analyze():
    """
    Endpoint for initiating the analysis of a URL.
    Two modes:
    1. HTMX request: Return loading template with progressive updates
    2. Regular request: Return JSON response
    """
    # Get the raw URL from form data
    raw_url = request.form.get('url', '')
    
    # Sanitize the input first
    url = sanitize_input(raw_url)
    
    # Validate URL after sanitization
    is_valid, error_message = validate_url(url)
    if not is_valid:
        if request.headers.get('HX-Request') == 'true':
            return render_template('partials/analysis_error.html', 
                                  error=error_message,
                                  error_type='validation',
                                  error_title='URL Validation Error'), 400
        else:
            return jsonify({'status': 'error', 'error': error_message}), 400
    
    # Check if sanitized URL is different from raw URL (indicates potential tampering)
    if url != raw_url and raw_url.find('%00') >= 0:
        error_message = "Potentially malicious URL detected (contains NULL bytes)"
        if request.headers.get('HX-Request') == 'true':
            return render_template('partials/analysis_error.html', 
                                  error=error_message,
                                  error_type='validation',
                                  error_title='Security Warning'), 400
        else:
            return jsonify({'status': 'error', 'error': error_message}), 400
    
    # Get selected model from form or use default
    selected_model = sanitize_input(request.form.get('model', Config.DEFAULT_MODEL))
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
    # Get the raw URL from query parameters
    raw_url = request.args.get('url', '')
    
    # Sanitize the input first
    url = sanitize_input(raw_url)
    
    # Validate URL after sanitization
    is_valid, error_message = validate_url(url)
    if not is_valid:
        return render_template('partials/analysis_error.html', 
                              error=error_message,
                              error_type='extraction',
                              error_title='URL Validation Error',
                              url=url,
                              model=sanitize_input(request.args.get('model', Config.DEFAULT_MODEL))), 400
    
    # Check if sanitized URL is different from raw URL (indicates potential tampering)
    if url != raw_url and raw_url.find('%00') >= 0:
        error_message = "Potentially malicious URL detected (contains NULL bytes)"
        return render_template('partials/analysis_error.html', 
                              error=error_message,
                              error_type='validation',
                              error_title='Security Warning',
                              url=url,
                              model=sanitize_input(request.args.get('model', Config.DEFAULT_MODEL))), 400
    
    step = sanitize_input(request.args.get('step', 'extract'))
    
    # IMPORTANT: Don't transform the model ID - keep it exactly as received
    model = sanitize_input(request.args.get('model', Config.DEFAULT_MODEL))
    
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
    # Get the raw URL from query parameters
    raw_url = request.args.get('url', '')
    
    # Sanitize the input first
    url = sanitize_input(raw_url)
    
    # Validate URL after sanitization
    is_valid, error_message = validate_url(url)
    if not is_valid:
        return render_template('partials/analysis_error.html', 
                              error=error_message,
                              error_type='validation',
                              error_title='URL Validation Error',
                              url=url), 400
    
    # Check if sanitized URL is different from raw URL (indicates potential tampering)
    if url != raw_url and raw_url.find('%00') >= 0:
        error_message = "Potentially malicious URL detected (contains NULL bytes)"
        return render_template('partials/analysis_error.html', 
                              error=error_message,
                              error_type='validation',
                              error_title='Security Warning',
                              url=url), 400
    
    # IMPORTANT: Don't transform the model ID - keep it exactly as received
    model = sanitize_input(request.args.get('model', Config.DEFAULT_MODEL))
    print_status(f"Analysis result request: URL={url}, Model={model}")
    
    try:
        # Check if we have a cached analysis
        cached_analysis = get_analysis_by_url(url)
        
        if cached_analysis:
            # Return cached results
            print_status(f"Retrieved cached analysis for URL: {url}")
            
            # Extract data needed for indicators
            article_id = cached_analysis.get('id', None)
            
            # Check if the cached analysis has already extracted indicators
            has_indicators = False
            if article_id:
                indicators = get_indicators_by_article_id(article_id)
                has_indicators = any(len(indicators[key]) > 0 for key in indicators)
            
            # Process and extract indicators of compromise if needed
            if not has_indicators and article_id:
                print_status(f"Extracting indicators for article ID: {article_id}")
                article_content = cached_analysis.get('raw_text', '')
                
                if article_content:
                    # Extract and store indicators
                    extracted_indicators = extract_indicators(article_content)
                    store_indicators(article_id, extracted_indicators)
                    
                    # Format for display
                    indicators = format_indicators_for_display(extracted_indicators)
                else:
                    indicators = {}
            elif has_indicators:
                # Format existing indicators for display
                indicators = format_indicators_for_display(indicators)
            else:
                indicators = {}
            
            structured_data = cached_analysis.get('structured_data', {})
            
            # Log final variables being sent to template
            print("========== TEMPLATE VARIABLES ==========")
            print(f"URL: {url}")
            print(f"Model: {model}")
            print(f"Result type: {type(cached_analysis.get('raw_text', ''))}")
            print(f"Structured data type: {type(cached_analysis.get('structured_data', {}))}")
            print("========================================")
            
            return render_template('partials/analysis_result.html',
                                  url=url,
                                  model=cached_analysis.get('model', model),
                                  result=cached_analysis.get('raw_text', ''),
                                  structured_data=structured_data,
                                  indicators=indicators,
                                  created_at=cached_analysis.get('created_at', ''),
                                  is_cached=True)
        else:
            # No cached analysis, start a new one
            print_status(f"Starting new analysis flow: URL={url}, Model={model}")
            
            # Begin extraction process
            print_status(f"Web request: Starting extraction from {url}")
            article_data = extract_article_content(url, verbose=True)
            
            if not article_data:
                return render_template('partials/analysis_error.html',
                                      error="Failed to extract content from the provided URL.",
                                      error_type="extraction"), 500
            
            # Handle different return types from extract_article_content
            if isinstance(article_data, str):
                article_content = article_data
                article_title = url
                extraction_time = 0
            else:
                article_content = article_data.get('content', '')
                article_title = article_data.get('title', '')
                extraction_time = article_data.get('extraction_time', 0)
            
            if not article_content:
                return render_template('partials/analysis_error.html',
                                      error="No content could be extracted from the URL.",
                                      error_type="empty_content"), 500
            
            # Begin analysis process
            print_status(f"Web request: Starting analysis using model: {model}")
            analysis_start = time.time()
            
            try:
                analysis_result = analyze_article(article_content, url, model=model, verbose=True, structured=True, extract_iocs=True)
                analysis_time = time.time() - analysis_start
                
                # Store the results
                store_analysis(
                    url=url,
                    title=article_title,
                    content_length=len(article_content),
                    extraction_time=extraction_time,
                    analysis_time=analysis_time,
                    model=model,
                    raw_analysis=analysis_result.get('text', ''),
                    structured_analysis=analysis_result.get('structured', {})
                )
                
                # Get the article ID
                new_analysis = get_analysis_by_url(url)
                article_id = new_analysis.get('id') if new_analysis else None
                
                # Extract and store indicators if we have an article ID
                indicators = {}
                if article_id:
                    extracted_indicators = extract_indicators(article_content)
                    store_indicators(article_id, extracted_indicators)
                    indicators = format_indicators_for_display(extracted_indicators)
                
                # Log final variables being sent to template
                print("========== TEMPLATE VARIABLES ==========")
                print(f"URL: {url}")
                print(f"Model: {model}")
                print(f"Result type: {type(analysis_result.get('text', ''))}")
                print(f"Structured data type: {type(analysis_result.get('structured', {}))}")
                print(f"API details: {analysis_result.get('api_details', {})}")
                print("========================================")
                
                return render_template('partials/analysis_result.html',
                                      url=url,
                                      model=model,
                                      result=analysis_result.get('text', ''),
                                      structured_data=analysis_result.get('structured', {}),
                                      indicators=indicators,
                                      api_details=analysis_result.get('api_details', {}),
                                      created_at=datetime.utcnow().isoformat(),
                                      is_cached=False)
            
            except Exception as e:
                error_message = str(e)
                print_status(f"Error in analysis_result: {error_message}", is_error=True)
                
                # Log the traceback for debugging
                error(traceback.format_exc())
                
                return render_template('partials/analysis_error.html',
                                      error=error_message,
                                      error_type="analysis",
                                      error_title="Analysis Error"), 500
    
    except Exception as e:
        error_message = str(e)
        print_status(f"Unhandled error in analysis_result: {error_message}", is_error=True)
        
        # Log the traceback for debugging
        error(traceback.format_exc())
        
        return render_template('partials/analysis_error.html',
                              error=error_message,
                              error_type="general",
                              error_title="System Error"), 500

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
    auth_token = sanitize_input(request.args.get('auth_token', ''))
    admin_token = Config.ADMIN_DEBUG_TOKEN
    
    if not admin_token or auth_token != admin_token:
        return jsonify({"error": "Authentication required"}), 401
    
    url = sanitize_input(request.args.get('url', ''))
    
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
    # Get the raw URL from query parameters
    raw_url = request.args.get('url', '')
    
    # Sanitize the input first
    url = sanitize_input(raw_url)
    
    # Validate URL after sanitization
    is_valid, error_message = validate_url(url)
    if not is_valid:
        return render_template('partials/analysis_error.html', 
                              error=error_message,
                              error_type='extraction',
                              error_title='URL Validation Error',
                              url=url,
                              model=sanitize_input(request.args.get('model', Config.DEFAULT_MODEL))), 400
    
    # Check if sanitized URL is different from raw URL (indicates potential tampering)
    if url != raw_url and raw_url.find('%00') >= 0:
        error_message = "Potentially malicious URL detected (contains NULL bytes)"
        return render_template('partials/analysis_error.html', 
                              error=error_message,
                              error_type='validation',
                              error_title='Security Warning',
                              url=url,
                              model=sanitize_input(request.args.get('model', Config.DEFAULT_MODEL))), 400
    
    model = sanitize_input(request.args.get('model', Config.DEFAULT_MODEL))
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
        article_data = extract_article_content(url, verbose=True)
        extraction_time = time.time() - extraction_start
        
        # Handle different return types from extract_article_content
        if isinstance(article_data, str):
            article_content = article_data
        else:
            article_content = article_data.get('content', '') if article_data else ''
        
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

@analysis_bp.route('/export/<format_type>')
def export_analysis(format_type):
    """
    Export analysis in the specified format.
    Supports JSON, CSV, PDF, and Markdown formats.
    """
    url = sanitize_input(request.args.get('url', ''))
    
    # Validate URL
    is_valid, error_message = validate_url(url)
    if not is_valid:
        return jsonify({
            "success": False,
            "message": f"Invalid URL: {error_message}"
        }), 400
    
    # Format type from URL parameter
    format_type = sanitize_input(format_type.lower())
    
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