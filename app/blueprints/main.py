from flask import Blueprint, render_template, send_from_directory
from datetime import datetime
from app.config.config import Config
from app.models.database import get_recent_analyses, get_token_usage_stats

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Render the index page with recent analyses and model information."""
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
    default_model = Config.get_default_model()
    
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

@main_bp.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files from the static folder."""
    return send_from_directory('static', filename) 