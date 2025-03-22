from flask import Blueprint, render_template, jsonify, request
from app.models.database import get_token_usage_stats, get_recent_analyses
from app.config.config import Config
from datetime import datetime
import json

stats_bp = Blueprint('statistics', __name__)

@stats_bp.route('/statistics')
def statistics():
    # Get token usage stats
    token_stats = get_token_usage_stats()
    
    # Get recent analyses
    recent_analyses = get_recent_analyses(limit=None)
    
    # Format dates
    for analysis in recent_analyses:
        if isinstance(analysis['created_at'], str):
            try:
                # Try to parse the date string
                analysis['created_at'] = datetime.fromisoformat(analysis['created_at'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                # If parsing fails, leave as is
                pass
    
    # Get model prices from config
    model_prices = Config.get_model_prices()
    
    return render_template('statistics.html', 
                           token_stats=token_stats, 
                           recent_analyses=recent_analyses,
                           model_prices=model_prices)

@stats_bp.route('/statistics/refresh')
def refresh_statistics():
    """HTMX endpoint to refresh statistics content"""
    # Get token usage stats
    token_stats = get_token_usage_stats()
    
    # Get recent analyses
    recent_analyses = get_recent_analyses(limit=None)
    
    # Format dates
    for analysis in recent_analyses:
        if isinstance(analysis['created_at'], str):
            try:
                # Try to parse the date string
                analysis['created_at'] = datetime.fromisoformat(analysis['created_at'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                # If parsing fails, leave as is
                pass
    
    # Get model prices from config
    model_prices = Config.get_model_prices()
    
    # Render only the stats content without the full page
    return render_template('partials/statistics_content.html', 
                           token_stats=token_stats, 
                           recent_analyses=recent_analyses,
                           model_prices=model_prices) 