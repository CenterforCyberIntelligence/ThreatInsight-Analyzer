from flask import Flask
from app.config.config import Config
import os
import logging
from datetime import datetime
from app.utilities.logger import logger

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
    
    return app 