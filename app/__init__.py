from flask import Flask, render_template, request, jsonify
from app.config.config import Config
import os
import logging
from datetime import datetime
from app.utilities.logger import logger
import traceback

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__, 
                static_folder=os.path.abspath('static'),
                static_url_path='/static',
                template_folder=os.path.abspath('templates'))
    
    app.config.from_object(config_class)
    
    # Configure Flask logging to use our custom logger
    app.logger.handlers = []
    for handler in logger.handlers:
        app.logger.addHandler(handler)
    app.logger.setLevel(logger.level)
    
    # Log application startup
    app.logger.info("Starting Article Analyzer application")
    
    # Register blueprints
    from app.blueprints import main_bp, analysis_bp, stats_bp, settings_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(settings_bp)
    
    # Initialize database
    from app.models.database import init_db
    init_db()
    
    # Register custom Jinja2 filters
    @app.template_filter('zfill')
    def jinja2_zfill(value, width):
        """
        Custom filter that mimics Python's string.zfill().
        Pads a string on the left with zeros to fill the specified width.
        """
        return str(value).zfill(width)
    
    # Register utility context processors
    @app.context_processor
    def utility_processor():
        def current_time():
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return dict(current_time=current_time)
    
    # Log application initialization complete
    app.logger.info("Application initialization complete")
    
    # Add error handlers for better user experience
    @app.errorhandler(500)
    def internal_server_error(e):
        """Handle 500 errors with a custom template that works with HTMX."""
        error_message = str(e)
        error_details = traceback.format_exc() if app.config.get('DEBUG', False) else None
        
        # Determine if this is an HTMX request
        is_htmx = request.headers.get('HX-Request') == 'true'
        
        # Determine error type based on the error message
        error_type = 'unknown'
        error_title = 'Server Error'
        
        if 'openai' in error_message.lower() or 'api' in error_message.lower():
            error_type = 'openai_api'
            error_title = 'OpenAI API Error'
        elif 'extraction' in error_message.lower() or 'url' in error_message.lower():
            error_type = 'extraction'
            error_title = 'Content Extraction Error'
        elif 'NameError' in error_message:
            error_type = 'openai_api'
            error_title = 'API Configuration Error'
            
        # Get URL and model from request if available
        url = request.args.get('url', '')
        model = request.args.get('model', Config.get_default_model())
        
        # Log the error
        app.logger.error(f"500 error: {error_message}")
        if error_details:
            app.logger.error(f"Traceback: {error_details}")
        
        # For HTMX requests, return just the error partial
        if is_htmx:
            app.logger.info(f"Returning HTMX error response with type={error_type}, title={error_title}")
            app.logger.info(f"Error template variables: url={url}, model={model}")
            return render_template('partials/analysis_error.html',
                                  error=f"Server error: {error_message}",
                                  error_type=error_type,
                                  error_title=error_title,
                                  url=url,
                                  model=model,
                                  details=error_details), 500
        
        # For regular requests, return the full page with error content
        app.logger.info(f"Returning full page error response with type={error_type}, title={error_title}")
        return render_template('index.html',
                              error=f"Server error: {error_message}",
                              error_type=error_type,
                              error_title=error_title,
                              details=error_details), 500
    
    return app 