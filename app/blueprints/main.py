from flask import Blueprint, render_template, send_from_directory, request, jsonify, current_app
from datetime import datetime
from app.config.config import Config
from app.models.database import get_recent_analyses, get_token_usage_stats
from app.utilities.logger import logger

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Render the index page with recent analyses and model information."""
    try:
        # Get the 5 most recent analyses from the database
        recent_analyses = get_recent_analyses(5)
        
        # Convert string dates to datetime objects for proper display
        for analysis in recent_analyses:
            if isinstance(analysis, dict) and 'created_at' in analysis:
                if isinstance(analysis['created_at'], str):
                    try:
                        analysis['created_at'] = datetime.fromisoformat(analysis['created_at'].replace('Z', '+00:00'))
                    except ValueError:
                        pass
        
        # Get available models from config
        available_models = Config.get_available_models()
        
        # Get default model from config
        default_model = Config.DEFAULT_MODEL
        
        # Get token usage statistics and calculate total correctly
        token_stats = get_token_usage_stats()
        
        # Calculate total tokens by summing input, output, and cached tokens
        if 'overall' in token_stats:
            token_stats['overall']['total_tokens'] = (
                token_stats['overall']['total_input'] +    # Regular input tokens
                token_stats['overall']['total_output'] +   # Output tokens
                token_stats['overall']['cached_input']     # Cached input tokens
            )
        
        return render_template('index.html', 
                             model=default_model, 
                             recent_analyses=recent_analyses,
                             available_models=available_models,
                             token_stats=token_stats)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', recent_analyses=[])

@main_bp.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files from the static folder."""
    return send_from_directory('static', filename)

@main_bp.route('/about')
def about():
    """Render the about page."""
    return render_template('about.html')

@main_bp.route('/contact')
def contact():
    """Render the contact page."""
    return render_template('contact.html')

@main_bp.route('/api/csp-report', methods=['POST'])
def csp_report():
    """Endpoint to receive CSP violation reports."""
    try:
        report = request.get_json() or {}
        
        # Log CSP violation report
        logger.warning(f"CSP Violation: {report}")
        
        # Extract the most useful information
        csp_report = report.get('csp-report', {})
        if csp_report:
            blocked_uri = csp_report.get('blocked-uri', 'unknown')
            violated_directive = csp_report.get('violated-directive', 'unknown')
            document_uri = csp_report.get('document-uri', 'unknown')
            
            logger.warning(
                f"CSP Violation: {blocked_uri} blocked by {violated_directive} on {document_uri}"
            )
        
        return jsonify({"status": "received"}), 200
    except Exception as e:
        logger.error(f"Error processing CSP report: {str(e)}")
        return jsonify({"error": str(e)}), 500 