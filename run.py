from app import create_app
import os
import argparse
from app.utilities.logger import info, debug

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the Flask application')
    parser.add_argument('--port', type=int, help='Port to run the application on')
    args = parser.parse_args()
    
    debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    # Use command-line port if provided, otherwise use environment variable
    port = args.port if args.port else int(os.getenv('FLASK_PORT', '8000'))
    
    # Log server startup information
    info(f"Starting server in {'DEBUG' if debug_mode else 'PRODUCTION'} mode")
    info(f"Server will be accessible at http://{host}:{port}")
    debug(f"Environment: DEBUG={debug_mode}, HOST={host}, PORT={port}")
    
    # Run the application
    app.run(debug=debug_mode, host=host, port=port) 