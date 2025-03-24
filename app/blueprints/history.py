from flask import Blueprint, render_template
from datetime import datetime
from app.models.database import get_recent_analyses

history_bp = Blueprint('history', __name__)

@history_bp.route('/history')
def history():
    """Render the history page with all analyses."""
    # Get all analyses from the database (use None for no limit)
    analyses = get_recent_analyses(limit=None)
    
    # Convert string dates to datetime objects for proper display
    for analysis in analyses:
        if isinstance(analysis, dict) and 'created_at' in analysis:
            if isinstance(analysis['created_at'], str):
                try:
                    analysis['created_at'] = datetime.fromisoformat(analysis['created_at'].replace('Z', '+00:00'))
                except ValueError:
                    pass
    
    # Add current_time to prevent CSS caching
    current_time = int(datetime.now().timestamp())
    
    return render_template('history.html', analyses=analyses, current_time=current_time) 