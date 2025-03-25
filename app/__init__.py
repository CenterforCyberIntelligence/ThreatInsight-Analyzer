import os
import time
import signal
import contextlib
import sys
import json
from flask import Flask, render_template, jsonify, request
from app.blueprints import main_bp, analysis_bp, stats_bp, settings_bp, history_bp
from app.utilities.logger import logger, start_phase, end_phase, register_shutdown_handler, log_config_summary
from app.config.config import Config
from app.models.database import init_db, check_db_health

# Global instance tracking
_app_instance = None
_initialization_complete = False
_server_started = False

# Process tracking for Flask debug mode
_is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') != 'true'

def create_app():
    """Create and configure the Flask application."""
    global _app_instance, _initialization_complete
    
    # Return existing instance if already initialized
    if _initialization_complete and _app_instance is not None:
        return _app_instance
    
    # Create Flask app
    app = Flask(__name__, 
                static_folder=os.path.abspath('static'),
                static_url_path='/static',
                template_folder=os.path.abspath('templates'))
    app.config.from_object(Config)
    
    # Configure Flask logging to use our custom logger
    app.logger.handlers = []
    for handler in logger.handlers:
        app.logger.addHandler(handler)
    app.logger.setLevel(logger.level)
    
    # Only perform full initialization in the worker process, not the reloader
    if _is_reloader_process:
        logger.debug("Running in Flask reloader process - skipping full initialization")
        
        # Still register blueprints for routing to work
        app.register_blueprint(main_bp)
        app.register_blueprint(analysis_bp)
        app.register_blueprint(stats_bp)
        app.register_blueprint(settings_bp)
        app.register_blueprint(history_bp)
        
        # Store the app instance globally - minimal config for reloader
        _app_instance = app
        _initialization_complete = True
        
        return app
    
    # Start configuration phase - only in worker process
    start_phase("CONFIGURATION")
    
    # Log configuration summary (sanitized)
    log_config_summary(Config.get_as_dict())
    
    # Complete configuration phase
    end_phase("CONFIGURATION")
    
    # Start services phase
    start_phase("SERVICES")
    
    # Initialize the application
    logger.info("Starting Article Analyzer application")
    
    # Check for configuration validation errors
    validation_errors = Config.get_validation_errors()
    if validation_errors:
        for error in validation_errors:
            logger.warning(f"Configuration validation warning: {error}")
    
    # Check database health before initialization
    logger.info("Performing database health check...")
    db_healthy = check_db_health()
    
    if not db_healthy:
        logger.warning("Database health check failed. Attempting to initialize database anyway.")
    
    # Initialize database
    logger.info("Performing database initialization...")
    init_db()
    
    # Check OpenAI API availability
    logger.info("Checking OpenAI API availability...")
    api_available, api_message = Config.check_openai_api()
    logger.info(f"OpenAI API check result: {api_message}")
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(history_bp)
    
    # Add context processor for UI configuration
    @app.context_processor
    def inject_ui_config():
        """Inject UI configuration variables into the template context."""
        return {
            'heading_font': Config.HEADING_FONT
        }
    
    # Add no-cache headers for CSS files in debug mode
    @app.after_request
    def add_cache_control_headers(response):
        """Add cache control headers to prevent caching of CSS files in debug mode."""
        if app.debug and response.mimetype == 'text/css':
            # Set headers to prevent caching
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response
    
    # Add security headers to all responses - with lowest priority to run last
    @app.after_request
    def add_security_headers(response):
        """Add standard security headers to all responses to enhance application security."""
        # Skip adding security headers for certain content types that might be affected
        if response.mimetype in ('application/json', 'text/css', 'application/javascript'):
            return response
            
        # Set standard security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        
        # More balanced CSP approach with reporting capabilities
        csp_directives = [
            # Base directives - extremely permissive for now
            "default-src 'self' https: data: 'unsafe-inline' 'unsafe-eval'",
            
            # Scripts - allow self, inline, eval, and all required CDNs
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com",
            
            # Styles - allow self, inline, and all style sources
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https:",
            
            # Fonts - allow self and common font sources
            "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
            
            # Images - allow self, data URIs, and any HTTPS source
            "img-src 'self' data: https:",
            
            # Connect - allow self and any HTTPS source (for API calls)
            "connect-src 'self' https:",
            
            # Object - none needed
            "object-src 'none'"
        ]
        
        # Add CSP header
        response.headers['Content-Security-Policy'] = "; ".join(csp_directives)
        
        # Add CSP reporting header - ensure it matches the primary CSP
        response.headers['Content-Security-Policy-Report-Only'] = "; ".join(csp_directives) + "; report-uri /api/csp-report; report-to csp-endpoint"
        
        # Add Report-To header for CSP violation reporting
        report_to = {
            "group": "csp-endpoint",
            "max_age": 10886400,
            "endpoints": [
                {"url": "/api/csp-report"}
            ]
        }
        response.headers['Report-To'] = json.dumps(report_to)
        
        return response
    
    # Register error handlers
    @app.errorhandler(500)
    def handle_500_error(e):
        error_type = type(e).__name__
        error_message = str(e)
        
        if 'OpenAI' in error_type:
            message = f"OpenAI API Error: {error_message}"
        elif 'Database' in error_type:
            message = f"Database Error: {error_message}"
        elif 'Timeout' in error_type:
            message = f"Request Timeout: {error_message}"
        else:
            message = f"Server Error: {error_message}"
        
        logger.error(f"500 Error: {error_type} - {error_message}")
        return render_template('error.html', error=message), 500
    
    # Register graceful shutdown handler
    def graceful_shutdown(*args, **kwargs):
        """Perform cleanup operations before shutdown.
        This function supports being called directly or via signal handlers.
        """
        global _server_started
        
        # If we've already started shutdown, don't duplicate the messages
        if not _server_started and hasattr(graceful_shutdown, '_already_called'):
            return
        
        # Mark that we've been called to prevent duplicates
        graceful_shutdown._already_called = True
        
        logger.info("Application is shutting down...")
        
        # Reset the server started flag
        _server_started = False
        
        # Additional cleanup operations could go here:
        # - Close database connections
        # - Cancel background tasks
        # - Release file handles
        
        logger.info("Shutdown complete")
    
    # Register Flask shutdown handler
    register_shutdown_handler(app, graceful_shutdown)
    
    # Complete services phase
    end_phase("SERVICES")
    
    # Store the app instance globally
    _app_instance = app
    _initialization_complete = True
    
    logger.info("Application initialization complete")
    
    return app

def start_server(app=None, host=None, port=None, debug=None):
    """Start the Flask server with the configured app."""
    global _server_started, _app_instance
    
    # In debug mode, only the worker process should fully initialize the server
    if _is_reloader_process and os.environ.get('FLASK_DEBUG') == '1':
        debug_server_start()
        return
    
    if _server_started:
        logger.warning("Server is already running, ignoring duplicate start request")
        return
    
    # Create app if not provided
    if app is None:
        app = _app_instance if _app_instance is not None else create_app()
    
    # Get configuration
    host = host or Config.FLASK_HOST
    port = port or Config.FLASK_PORT
    debug = debug if debug is not None else Config.FLASK_DEBUG
    
    # Start API server phase
    start_phase("API_SERVER")
    
    logger.info(f"Starting server on {host}:{port} (debug={debug})")
    
    _server_started = True
    
    # Run the Flask application with proper exception handling
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        # Handle CTRL+C explicitly to ensure clean shutdown
        logger.debug("KeyboardInterrupt received, shutting down gracefully")
        graceful_shutdown()
    finally:
        # Ensure these are always called
        _server_started = False
        end_phase("API_SERVER")
        logger.info("Server stopped")

def debug_server_start():
    """Special handler for the reloader process in debug mode."""
    logger.debug("Debug reloader process starting the Flask server (minimal initialization)")
    
    # Create a minimal app just for the reloader
    app = get_app()
    
    # Get configuration but skip unnecessary logging
    host = Config.FLASK_HOST
    port = Config.FLASK_PORT
    debug = Config.FLASK_DEBUG
    
    # Minimal logging
    logger.debug(f"Reloader starting server on {host}:{port} (debug={debug})")
    
    # Special handler for the reloader process to prevent duplicate logs on SIGINT
    import signal
    import sys
    
    def reloader_sigint_handler(sig, frame):
        logger.debug("Reloader process received shutdown signal")
        sys.exit(0)
    
    # Register our own handler for SIGINT in the reloader to prevent duplicate logs
    if hasattr(signal, 'SIGINT'):
        signal.signal(signal.SIGINT, reloader_sigint_handler)
    
    # Run the Flask application with debug enabled
    app.run(host=host, port=port, debug=debug)

def get_app():
    """Get or create the Flask app instance."""
    global _app_instance
    if _app_instance is None:
        _app_instance = create_app()
    return _app_instance 