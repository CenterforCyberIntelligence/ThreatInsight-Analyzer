from flask import Blueprint, request, jsonify, render_template
import time
import os
import re
import traceback
from typing import Dict, Any

from app.utilities.logger import print_status
from app.utilities.article_extractor import extract_article_content
from app.utilities.article_analyzer import analyze_article, parse_analysis_response
from app.models.database import store_analysis, update_analysis, get_analysis_by_url, track_token_usage, store_indicators, get_indicators_by_url
from app.config.config import Config

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/analyze', methods=['POST'])
def analyze():
    """
    Endpoint that handles article analysis requests.
    Accepts a URL and model selection.
    With HTMX, returns an HTML fragment for loading status.
    """
    url = request.form.get('url')
    if not url:
        return render_template('partials/analysis_error.html', 
                            error='URL is required'), 400
    
    # Get selected model from form or use default
    selected_model = request.form.get('model', Config.get_default_model())
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
    url = request.args.get('url')
    step = request.args.get('step', 'extract')
    model = request.args.get('model', Config.get_default_model())
    
    print_status(f"Analysis status check: URL={url}, Step={step}, Model={model}")
    
    if not url:
        return render_template('partials/analysis_error.html', 
                              error='URL is required for status check'), 400
    
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
    url = request.args.get('url')
    if not url:
        return render_template('partials/analysis_error.html', 
                              error='URL is required'), 400
    
    model = request.args.get('model', Config.get_default_model())
    print_status(f"Analysis result request: URL={url}, Model={model}")
    
    # Check cache for existing analysis
    existing_analysis = get_analysis_by_url(url)
    if existing_analysis:
        print_status(f"Found existing analysis for {url}, using cached results with model: {existing_analysis['model']}")
        
        # Track token usage for cached result (estimate input tokens)
        estimated_input_tokens = len(existing_analysis['raw_text']) // 4
        track_token_usage(existing_analysis['model'], estimated_input_tokens, 0, cached=True)
        
        # Create dummy API details for cached results
        cached_api_details = {
            "request": {
                "model": existing_analysis['model'],
                "messages": [
                    {"role": "system", "content": "Analysis prompt (cached)"},
                    {"role": "user", "content": f"Article URL: {url}\n\nContent: [Cached Content]"}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "response": {
                "model": existing_analysis['model'],
                "input_tokens": estimated_input_tokens,
                "output_tokens": len(existing_analysis['raw_text']) // 4,
                "total_tokens": estimated_input_tokens + (len(existing_analysis['raw_text']) // 4),
                "first_completion": existing_analysis['raw_text'][:500] + "..." if len(existing_analysis['raw_text']) > 500 else existing_analysis['raw_text']
            }
        }
        
        # Get indicators from database for this URL
        indicators = get_indicators_by_url(url)
        
        # Format indicators for display if they exist
        if indicators and sum(len(ind) for ind in indicators.values()) > 0:
            from app.utilities.indicator_extractor import format_indicators_for_display
            formatted_indicators = format_indicators_for_display(indicators)
            existing_analysis['structured_data']['indicators'] = formatted_indicators
            print_status(f"Retrieved {formatted_indicators['total_count']} indicators from database for URL: {url}")
        
        # Convert ISO timestamp to human-readable format
        analyzed_at = None
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
                                  error='Failed to extract meaningful content from the article. Please check the URL and try again.'), 400
        
        # Analyze content with selected model
        print_status(f"Web request: Starting analysis using model: {model}")
        analysis_start = time.time()
        analysis_result = analyze_article(article_content, url, model=model, verbose=True, structured=True, extract_iocs=True)
        analysis_time = time.time() - analysis_start
        
        if not analysis_result:
            print_status(f"Web request: Analysis failed with model {model}", is_error=True)
            return render_template('partials/analysis_error.html',
                                  error='Analysis failed. The OpenAI API may be experiencing issues.'), 500
        
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
                                  error='Analysis failed to produce valid results.'), 500
        
        # Get API details if available
        api_details = analysis_result.get("api_details", None)
        
        # Verify the model in the API details matches what was requested
        if api_details and api_details.get("request", {}).get("model") != model:
            print_status(f"WARNING: Requested model {model} doesn't match API request model {api_details.get('request', {}).get('model')}", is_error=True)

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
                             api_details=api_details,
                             cached=False)
        
    except Exception as e:
        error_details = traceback.format_exc()
        print_status(f"Web request error with model {model}: {str(e)}", is_error=True)
        print_status(error_details, is_error=True)
        return render_template('partials/analysis_error.html',
                             error=f"An error occurred: {str(e)}",
                             details=error_details if os.getenv('FLASK_DEBUG') == '1' else None), 500

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

@analysis_bp.route('/analysis/refresh', methods=['GET'])
def refresh_analysis():
    """
    Endpoint to refresh/reanalyze a previously analyzed URL.
    Bypasses cache and forces a new analysis using the latest processing techniques.
    """
    url = request.args.get('url')
    if not url:
        return render_template('partials/analysis_error.html', 
                              error='URL is required for refresh'), 400
    
    model = request.args.get('model', Config.get_default_model())
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
                                  error='Failed to extract meaningful content from the article. Please check the URL and try again.'), 400
        
        # Analyze content with selected model
        print_status(f"Web request: Starting analysis using model: {model}")
        analysis_start = time.time()
        analysis_result = analyze_article(article_content, url, model=model, verbose=True, structured=True, extract_iocs=True)
        analysis_time = time.time() - analysis_start
        
        if not analysis_result:
            print_status(f"Web request: Analysis failed with model {model}", is_error=True)
            return render_template('partials/analysis_error.html',
                                  error='Analysis failed. The OpenAI API may be experiencing issues.'), 500
        
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
                                  error='Analysis failed to produce valid results.'), 500
        
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

        # Log the final result
        print_status(f"Refresh analysis complete: URL={url}, Model={model}, Content Length={len(article_content)}")

        # Update the analysis in database - use update_analysis to overwrite previous data
        if existing_analysis:
            print_status(f"Updating existing analysis in database for URL: {url}")
            store_success = update_analysis(
                url=url,
                title=title,
                content_length=len(article_content),
                extraction_time=extraction_time,
                analysis_time=analysis_time,
                model=model,
                raw_analysis=analysis_result["text"],
                structured_analysis=analysis_result["structured"]
            )
            
            article_id = existing_analysis.get('id')
            if store_success and article_id and 'extracted_indicators' in analysis_result:
                # Store extracted indicators (they will replace existing ones because update_analysis deleted them)
                if analysis_result['extracted_indicators']:
                    print_status(f"Storing new indicators for article_id: {article_id}")
                    store_success = store_indicators(article_id, analysis_result['extracted_indicators'])
                    if store_success:
                        print_status(f"Successfully stored new indicators for article_id: {article_id}")
                    else:
                        print_status(f"Failed to store new indicators for article_id: {article_id}", is_error=True)
        else:
            # If no existing analysis, create a new one
            print_status(f"No existing analysis found, creating new record for URL: {url}")
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
            
            # Get the newly stored article ID and store indicators if successful
            if store_success:
                stored_article = get_analysis_by_url(url)
                if stored_article and 'id' in stored_article and 'extracted_indicators' in analysis_result:
                    article_id = stored_article['id']
                    # Store extracted indicators
                    if analysis_result['extracted_indicators']:
                        print_status(f"Storing extracted indicators for new article_id: {article_id}")
                        store_indicators(article_id, analysis_result['extracted_indicators'])
        
        # Get the updated/refreshed analysis to ensure we have the correct timestamps
        refreshed_analysis = get_analysis_by_url(url)

        # Format the analyzed_at timestamp from the refreshed analysis
        analyzed_at = None
        if refreshed_analysis and refreshed_analysis['created_at']:
            try:
                # Try to parse ISO format timestamp
                from datetime import datetime
                dt = datetime.fromisoformat(refreshed_analysis['created_at'])
                analyzed_at = dt.strftime('%B %d, %Y at %H:%M')
            except:
                # If parsing fails, use the original format
                analyzed_at = refreshed_analysis['created_at']

        # Return the refreshed analysis result with correct timestamps
        return render_template('partials/analysis_result.html',
                             url=url,
                             model=model,
                             analysis=analysis_result["text"],
                             structured_analysis=analysis_result["structured"],
                             content_length=len(article_content),
                             api_details=api_details,
                             cached=True,
                             refreshed=True,
                             analyzed_at=analyzed_at)
        
    except Exception as e:
        error_details = traceback.format_exc()
        print_status(f"Refresh analysis error with model {model}: {str(e)}", is_error=True)
        print_status(error_details, is_error=True)
        return render_template('partials/analysis_error.html',
                             error=f"An error occurred during refresh: {str(e)}",
                             details=error_details if os.getenv('FLASK_DEBUG') == '1' else None), 500 