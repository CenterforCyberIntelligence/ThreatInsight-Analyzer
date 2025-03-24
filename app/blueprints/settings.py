from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
import os
import json
import sqlite3
import subprocess
import sys
import signal
import threading
import time
from typing import Dict, Any
from app.config.config import Config
from app.models.database import get_token_usage_stats
from dotenv import load_dotenv

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
def settings():
    """Render the analyzer settings page."""
    # Get current environment variables for display
    env_vars = {
        "OPENAI_API_KEY": mask_api_key(os.getenv("OPENAI_API_KEY", "")),
        "OPENAI_MODEL": os.getenv("OPENAI_MODEL", ""),
        "OPENAI_TEMPERATURE": os.getenv("OPENAI_TEMPERATURE", ""),
        "OPENAI_MAX_TOKENS": os.getenv("OPENAI_MAX_TOKENS", ""),
        "AVAILABLE_MODELS": os.getenv("AVAILABLE_MODELS", ""),
        "FLASK_HOST": os.getenv("FLASK_HOST", ""),
        "FLASK_PORT": os.getenv("FLASK_PORT", ""),
        "FLASK_DEBUG": os.getenv("FLASK_DEBUG", ""),
        "HEADING_FONT": os.getenv("HEADING_FONT", "Rajdhani")
    }
    
    # Get token usage statistics
    token_stats = get_token_usage_stats()
    
    return render_template('settings.html', 
                          env_vars=env_vars,
                          token_stats=token_stats)

def mask_api_key(api_key: str) -> str:
    """Mask API key for display purposes."""
    if not api_key:
        return ""
    
    # Show only the first 4 and last 4 characters if key is long enough
    if len(api_key) > 8:
        return api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
    
    # Otherwise just return asterisks
    return '*' * len(api_key)

def restart_server():
    """Restart the Flask server."""
    time.sleep(1)  # Small delay to ensure response is sent
    os.execv(sys.executable, [sys.executable] + sys.argv)

@settings_bp.route('/settings/update_env', methods=['POST'])
def update_env():
    """Update environment variables."""
    try:
        # Get form data
        new_env_vars = {
            "OPENAI_API_KEY": request.form.get("OPENAI_API_KEY"),
            "OPENAI_MODEL": request.form.get("OPENAI_MODEL"),
            "OPENAI_TEMPERATURE": request.form.get("OPENAI_TEMPERATURE"),
            "OPENAI_MAX_TOKENS": request.form.get("OPENAI_MAX_TOKENS"),
            "AVAILABLE_MODELS": request.form.get("AVAILABLE_MODELS"),
            "FLASK_HOST": request.form.get("FLASK_HOST"),
            "FLASK_PORT": request.form.get("FLASK_PORT"),
            "FLASK_DEBUG": request.form.get("FLASK_DEBUG"),
            "HEADING_FONT": request.form.get("HEADING_FONT")
        }
        
        # Validate JSON format for AVAILABLE_MODELS
        try:
            if new_env_vars["AVAILABLE_MODELS"]:
                json.loads(new_env_vars["AVAILABLE_MODELS"])
        except json.JSONDecodeError:
            return jsonify({"success": False, "message": "Invalid JSON format for AVAILABLE_MODELS"})
        
        # Special handling for API key - don't overwrite if the field is empty
        # or if it's the masked version of the key
        if new_env_vars["OPENAI_API_KEY"] == mask_api_key(os.getenv("OPENAI_API_KEY", "")):
            new_env_vars["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
        elif not new_env_vars["OPENAI_API_KEY"]:
            new_env_vars["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
        
        # Read current .env file
        with open(".env", "r") as f:
            env_content = f.readlines()
        
        # Update the environment variables in the .env file
        updated_lines = []
        updated_vars = set()
        
        for line in env_content:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                if key in new_env_vars and new_env_vars[key]:
                    updated_lines.append(f"{key}={new_env_vars[key]}")
                    updated_vars.add(key)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Add any new variables that weren't in the file
        for key, value in new_env_vars.items():
            if key not in updated_vars and value:
                updated_lines.append(f"{key}={value}")
        
        # Write back to .env file
        with open(".env", "w") as f:
            f.write('\n'.join(updated_lines))
        
        # Reload environment variables
        load_dotenv(override=True)
        
        # Set restart flag and return success
        should_restart = request.form.get("should_restart", "false").lower() == "true"
        
        if should_restart:
            # Schedule a restart after response is sent
            threading.Thread(target=restart_server).start()
            return jsonify({"success": True, "message": "Environment variables updated. Server is restarting...", "restarting": True})
        
        return jsonify({"success": True, "message": "Environment variables updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error updating environment variables: {str(e)}"})

@settings_bp.route('/settings/purge_database', methods=['POST'])
def purge_database():
    """Purge database records."""
    try:
        confirmation = request.form.get("confirmation")
        if confirmation != "DELETE":
            return jsonify({
                "success": False, 
                "message": "Confirmation text does not match 'DELETE'. Database was not purged."
            })
        
        # Connect to the database
        conn = sqlite3.connect(Config.DB_PATH)
        cursor = conn.cursor()
        
        # Delete all records from all tables
        cursor.execute("DELETE FROM analysis_results")
        cursor.execute("DELETE FROM articles")
        cursor.execute("DELETE FROM token_usage")
        
        # Reset auto-increment counters
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='analysis_results'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='articles'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='token_usage'")
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Database purged successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error purging database: {str(e)}"})

@settings_bp.route('/settings/restart', methods=['POST'])
def restart():
    """Restart the Flask server."""
    try:
        threading.Thread(target=restart_server).start()
        return jsonify({"success": True, "message": "Server is restarting..."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error restarting server: {str(e)}"}) 