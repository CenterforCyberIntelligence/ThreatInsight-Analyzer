import os
from app import create_app, start_server
from app.config.config import Config

if __name__ == "__main__":
    # Set Flask debug environment variable
    if Config.FLASK_DEBUG:
        os.environ['FLASK_DEBUG'] = '1'
    
    app = create_app()
    start_server(app) 