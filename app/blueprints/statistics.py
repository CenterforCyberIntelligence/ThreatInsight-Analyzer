from flask import Blueprint, render_template, jsonify, request
from app.models.database import get_token_usage_stats, get_recent_analyses
from app.config.config import Config
from app.utilities.sanitizers import sanitize_input
from datetime import datetime
import json
from typing import Dict, Any

stats_bp = Blueprint('statistics', __name__)

@stats_bp.route('/statistics')
def statistics():
    """Route to display statistics about the app usage."""
    
    # Get token usage stats from database
    token_usage_stats = get_token_usage_stats()
    
    # Get list of recent analyses from database
    recent_analyses = get_recent_analyses(limit=5)
    
    # Get model prices
    model_prices = Config.get_model_prices()
    
    # Get model from query parameters or use default
    model = sanitize_input(request.args.get('model', Config.DEFAULT_MODEL))
    
    # Create a normalized model prices dictionary for the template
    normalized_model_prices = {}
    for analysis in recent_analyses:
        # Use 'model' key instead of 'model_id' for consistency with database schema
        model_key = analysis.get('model')
        if model_key:
            # Normalize the model ID to handle version differences
            normalized_id = Config.normalize_model_id(model_key)
            # Map the original model ID to its normalized pricing
            if normalized_id in model_prices and model_key not in normalized_model_prices:
                normalized_model_prices[model_key] = model_prices[normalized_id]
            # If no direct match found, check if we can extract the base model
            elif model_key not in normalized_model_prices:
                base_models = list(model_prices.keys())
                for base_model in base_models:
                    if base_model in model_key:
                        normalized_model_prices[model_key] = model_prices[base_model]
                        break
    
    # Merge normalized prices with standard prices
    template_model_prices = {**model_prices, **normalized_model_prices}
    
    return render_template(
        'statistics.html',
        stats=token_usage_stats,
        token_stats=token_usage_stats,  # Add token_stats as well for compatibility with the template
        recent_analyses=recent_analyses,
        model_prices=template_model_prices
    )

@stats_bp.route('/statistics/refresh')
def refresh_statistics():
    """HTMX endpoint to refresh statistics content"""
    # Get token usage stats
    token_usage_stats = get_token_usage_stats()
    
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
    
    # Get model prices
    model_prices = Config.get_model_prices()
    
    # Get model from query parameters or use default
    model = sanitize_input(request.args.get('model', Config.DEFAULT_MODEL))
    
    # Create a normalized model prices dictionary for the template
    normalized_model_prices = {}
    for analysis in recent_analyses:
        # Use 'model' key instead of 'model_id' for consistency with database schema
        model_key = analysis.get('model')
        if model_key:
            # Normalize the model ID to handle version differences
            normalized_id = Config.normalize_model_id(model_key)
            # Map the original model ID to its normalized pricing
            if normalized_id in model_prices and model_key not in normalized_model_prices:
                normalized_model_prices[model_key] = model_prices[normalized_id]
            # If no direct match found, check if we can extract the base model
            elif model_key not in normalized_model_prices:
                base_models = list(model_prices.keys())
                for base_model in base_models:
                    if base_model in model_key:
                        normalized_model_prices[model_key] = model_prices[base_model]
                        break
    
    # Merge normalized prices with standard prices
    template_model_prices = {**model_prices, **normalized_model_prices}
    
    # Render only the stats content without the full page
    return render_template(
        'partials/statistics_content.html',
        stats=token_usage_stats,
        recent_analyses=recent_analyses,
        model_prices=template_model_prices
    ) 