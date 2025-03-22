#!/usr/bin/env python3
"""
Data migration script for ArticleSummary app
Migrates data from the old flat structure to the new modular structure
"""

import os
import sys
import sqlite3
import json
import shutil
from datetime import datetime

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config.config import Config
from app.models.database import init_db

def migrate_data():
    """Migrate data from old database structure to new one"""
    # Paths
    old_db_path = 'data/article_analysis.db'
    backup_path = 'data/article_analysis.db.bak'
    new_db_path = Config.DB_PATH
    
    # Check if old database exists
    if not os.path.exists(old_db_path):
        print("No old database found. No migration needed.")
        return
    
    # Backup old database
    print(f"Backing up old database to {backup_path}")
    shutil.copy2(old_db_path, backup_path)
    
    # Initialize new database
    print("Initializing new database schema")
    init_db()
    
    # Connect to both databases
    old_conn = sqlite3.connect(old_db_path)
    old_conn.row_factory = sqlite3.Row
    old_cursor = old_conn.cursor()
    
    new_conn = sqlite3.connect(new_db_path)
    new_cursor = new_conn.cursor()
    
    try:
        # Get all articles from old database
        print("Fetching articles from old database")
        old_cursor.execute("""
            SELECT a.id, a.url, a.title, a.content_length, a.extraction_time, a.analysis_time, 
                   a.model, a.created_at, r.raw_text, r.structured_data
            FROM articles a
            JOIN analysis_results r ON a.id = r.article_id
        """)
        
        articles = old_cursor.fetchall()
        print(f"Found {len(articles)} articles to migrate")
        
        # Migrate articles
        for article in articles:
            print(f"Migrating article: {article['url']}")
            
            # Insert into new database
            new_cursor.execute(
                """INSERT INTO articles 
                   (url, title, content_length, extraction_time, analysis_time, model, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    article['url'],
                    article['title'],
                    article['content_length'],
                    article['extraction_time'],
                    article['analysis_time'],
                    article['model'],
                    article['created_at']
                )
            )
            
            article_id = new_cursor.lastrowid
            
            # Insert analysis results
            new_cursor.execute(
                """INSERT INTO analysis_results 
                   (article_id, raw_text, structured_data) 
                   VALUES (?, ?, ?)""",
                (
                    article_id,
                    article['raw_text'],
                    article['structured_data']
                )
            )
        
        # Migrate token usage data if it exists
        print("Checking for token usage data")
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='token_usage'")
        if old_cursor.fetchone():
            print("Migrating token usage data")
            old_cursor.execute("SELECT model, input_tokens, output_tokens, cached, timestamp FROM token_usage")
            token_data = old_cursor.fetchall()
            
            print(f"Found {len(token_data)} token usage records")
            
            for record in token_data:
                new_cursor.execute(
                    """INSERT INTO token_usage 
                       (model, input_tokens, output_tokens, cached, timestamp) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        record['model'],
                        record['input_tokens'],
                        record['output_tokens'],
                        record['cached'],
                        record['timestamp']
                    )
                )
        
        # Commit changes
        new_conn.commit()
        print("Migration completed successfully")
        
    except Exception as e:
        new_conn.rollback()
        print(f"Error during migration: {e}")
        print("Rolling back changes")
    finally:
        old_conn.close()
        new_conn.close()

if __name__ == '__main__':
    # Create scripts directory if it doesn't exist
    os.makedirs('scripts', exist_ok=True)
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    print("Starting data migration")
    migrate_data()
    print("Migration process complete") 