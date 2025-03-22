import sqlite3
import json
import os
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple

from app.utilities.logger import info, debug, error, warning

# Ensure the data directory exists
os.makedirs('data', exist_ok=True)

def init_db() -> None:
    """Initialize the database with required tables."""
    from app.config.config import Config
    debug(f"Initializing database at {Config.DB_PATH}")
    
    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()
    
    # Create articles table
    debug("Creating articles table if it doesn't exist")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        title TEXT,
        content_length INTEGER,
        extraction_time REAL,
        analysis_time REAL,
        model TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create analysis results table
    debug("Creating analysis_results table if it doesn't exist")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS analysis_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER,
        raw_text TEXT,
        structured_data TEXT,
        FOREIGN KEY (article_id) REFERENCES articles (id)
    )
    ''')
    
    # Create token_usage table
    debug("Creating token_usage table if it doesn't exist")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS token_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model TEXT,
        input_tokens INTEGER,
        output_tokens INTEGER,
        cached BOOLEAN,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create indicators table
    debug("Creating indicators table if it doesn't exist")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS indicators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER,
        indicator_type TEXT NOT NULL,
        value TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (article_id) REFERENCES articles (id),
        UNIQUE (article_id, indicator_type, value)
    )
    ''')
    
    conn.commit()
    conn.close()
    info("Database initialization complete")

def store_analysis(
    url: str, 
    title: str, 
    content_length: int, 
    extraction_time: float, 
    analysis_time: float, 
    model: str, 
    raw_analysis: str, 
    structured_analysis: Dict[str, Any]
) -> bool:
    """Store analysis results in the database."""
    from app.config.config import Config
    info(f"Storing analysis results for URL: {url}")
    debug(f"Analysis details: model={model}, content_length={content_length}, extraction_time={extraction_time:.2f}s, analysis_time={analysis_time:.2f}s")
    
    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Insert article info
        debug(f"Inserting article info: {title}")
        cursor.execute(
            "INSERT INTO articles (url, title, content_length, extraction_time, analysis_time, model, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (url, title, content_length, extraction_time, analysis_time, model, datetime.now().isoformat())
        )
        article_id = cursor.lastrowid
        
        # Insert analysis results
        debug(f"Inserting analysis results for article_id: {article_id}")
        cursor.execute(
            "INSERT INTO analysis_results (article_id, raw_text, structured_data) VALUES (?, ?, ?)",
            (article_id, raw_analysis, json.dumps(structured_analysis))
        )
        
        conn.commit()
        info(f"Analysis results stored successfully for URL: {url}")
        return True
    except sqlite3.IntegrityError:
        # URL already exists
        warning(f"URL already exists in database: {url}")
        conn.rollback()
        return False
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Error storing analysis: {e}")
        error(f"Traceback: {error_details}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_analysis(
    url: str, 
    title: str, 
    content_length: int, 
    extraction_time: float, 
    analysis_time: float, 
    model: str, 
    raw_analysis: str, 
    structured_analysis: Dict[str, Any]
) -> bool:
    """
    Update an existing analysis in the database, completely replacing previous data.
    Used primarily for refreshed reports.
    """
    from app.config.config import Config
    info(f"Updating analysis results for URL: {url}")
    debug(f"Analysis updates: model={model}, content_length={content_length}, extraction_time={extraction_time:.2f}s, analysis_time={analysis_time:.2f}s")
    
    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if article exists and get its ID
        cursor.execute("SELECT id FROM articles WHERE url = ?", (url,))
        result = cursor.fetchone()
        
        if not result:
            error(f"Cannot update analysis: URL not found in database: {url}")
            return False
            
        article_id = result[0]
        debug(f"Found existing article_id: {article_id} for URL: {url}")
        
        # Update article information including created_at timestamp
        current_time = datetime.now().isoformat()
        debug(f"Updating article info: {title}, and setting created_at to current time: {current_time}")
        cursor.execute(
            """
            UPDATE articles 
            SET title = ?, content_length = ?, extraction_time = ?, 
                analysis_time = ?, model = ?, created_at = ?
            WHERE id = ?
            """,
            (title, content_length, extraction_time, analysis_time, model, current_time, article_id)
        )
        
        # Update analysis results
        debug(f"Updating analysis results for article_id: {article_id}")
        cursor.execute(
            """
            UPDATE analysis_results 
            SET raw_text = ?, structured_data = ?
            WHERE article_id = ?
            """,
            (raw_analysis, json.dumps(structured_analysis), article_id)
        )
        
        # Delete existing indicators
        debug(f"Removing existing indicators for article_id: {article_id}")
        cursor.execute("DELETE FROM indicators WHERE article_id = ?", (article_id,))
        
        conn.commit()
        info(f"Analysis results updated successfully for URL: {url}")
        return True
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Error updating analysis: {e}")
        error(f"Traceback: {error_details}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_analysis_by_url(url: str) -> Optional[Dict[str, Any]]:
    """Retrieve analysis results for a specific URL."""
    from app.config.config import Config
    debug(f"Retrieving analysis results for URL: {url}")
    
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT a.id, a.url, a.title, a.content_length, a.model, a.created_at, 
                   r.raw_text, r.structured_data
            FROM articles a
            JOIN analysis_results r ON a.id = r.article_id
            WHERE a.url = ?
        """, (url,))
        
        result = cursor.fetchone()
        
        if result:
            info(f"Found existing analysis for URL: {url}")
            debug(f"Analysis details: id={result['id']}, model={result['model']}, created_at={result['created_at']}")
            return {
                'id': result['id'],
                'url': result['url'],
                'title': result['title'],
                'content_length': result['content_length'],
                'model': result['model'],
                'created_at': result['created_at'],
                'raw_text': result['raw_text'],
                'structured_data': json.loads(result['structured_data'])
            }
        debug(f"No analysis found for URL: {url}")
        return None
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Error retrieving analysis: {e}")
        error(f"Traceback: {error_details}")
        return None
    finally:
        conn.close()

def get_recent_analyses(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve the most recent analyses."""
    from app.config.config import Config
    debug(f"Retrieving {limit} most recent analyses")
    
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT a.id, a.url, a.title, a.content_length, a.model, a.created_at
            FROM articles a
            ORDER BY a.created_at DESC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        
        info(f"Retrieved {len(results)} recent analyses")
        return [{
            'id': row['id'],
            'url': row['url'],
            'title': row['title'],
            'content_length': row['content_length'],
            'model': row['model'],
            'created_at': row['created_at']
        } for row in results]
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Error retrieving recent analyses: {e}")
        error(f"Traceback: {error_details}")
        return []
    finally:
        conn.close()

def track_token_usage(model: str, input_tokens: int, output_tokens: int, cached: bool = False) -> bool:
    """Track token usage for billing purposes."""
    from app.config.config import Config
    debug(f"Tracking token usage: model={model}, input={input_tokens}, output={output_tokens}, cached={cached}")
    
    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Insert usage data
        cursor.execute(
            "INSERT INTO token_usage (model, input_tokens, output_tokens, cached, timestamp) VALUES (?, ?, ?, ?, ?)",
            (model, input_tokens, output_tokens, cached, datetime.now().isoformat())
        )
        
        conn.commit()
        debug(f"Token usage tracked successfully for model: {model}")
        return True
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Error tracking token usage: {e}")
        error(f"Traceback: {error_details}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_token_usage_stats() -> Dict[str, Any]:
    """Get token usage statistics."""
    from app.config.config import Config
    debug("Retrieving token usage statistics")
    
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Get total tokens by model
        cursor.execute("""
            SELECT model, 
                   SUM(input_tokens) as total_input, 
                   SUM(output_tokens) as total_output,
                   SUM(CASE WHEN cached = 1 THEN input_tokens ELSE 0 END) as cached_input
            FROM token_usage
            GROUP BY model
        """)
        
        model_stats = {}
        for row in cursor.fetchall():
            model_stats[row['model']] = {
                'total_input': row['total_input'],
                'total_output': row['total_output'],
                'cached_input': row['cached_input'],
                'regular_input': row['total_input'] - row['cached_input']
            }
        
        # Get overall totals
        cursor.execute("""
            SELECT SUM(input_tokens) as total_input, 
                   SUM(output_tokens) as total_output,
                   SUM(CASE WHEN cached = 1 THEN input_tokens ELSE 0 END) as cached_input,
                   COUNT(DISTINCT model) as model_count
            FROM token_usage
        """)
        
        overall = cursor.fetchone()
        
        stats = {
            'models': model_stats,
            'overall': {
                'total_input': overall['total_input'] or 0,
                'total_output': overall['total_output'] or 0,
                'cached_input': overall['cached_input'] or 0,
                'regular_input': (overall['total_input'] or 0) - (overall['cached_input'] or 0),
                'total_tokens': (overall['total_input'] or 0) + (overall['total_output'] or 0),
                'model_count': overall['model_count'] or 0
            }
        }
        
        info(f"Token usage stats: {stats['overall']['total_tokens']} total tokens across {stats['overall']['model_count']} models")
        return stats
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Error getting token usage stats: {e}")
        error(f"Traceback: {error_details}")
        return {
            'models': {},
            'overall': {
                'total_input': 0,
                'total_output': 0,
                'cached_input': 0,
                'regular_input': 0,
                'total_tokens': 0,
                'model_count': 0
            }
        }
    finally:
        conn.close()

def store_indicators(article_id: int, indicators: Dict[str, List[str]]) -> bool:
    """
    Store extracted indicators in the database.
    
    Args:
        article_id: ID of the article the indicators are associated with
        indicators: Dictionary of indicators by type
        
    Returns:
        True if successful, False otherwise
    """
    from app.config.config import Config
    info(f"Storing indicators for article_id: {article_id}")
    
    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Count the indicators
        total_indicators = sum(len(indicators[itype]) for itype in indicators)
        debug(f"Preparing to store {total_indicators} indicators")
        
        # Insert each indicator
        for indicator_type, values in indicators.items():
            if not values:
                continue
                
            # Use executemany for better performance
            insert_data = [(article_id, indicator_type, value) for value in values]
            
            # Using INSERT OR IGNORE to handle potential duplicates
            cursor.executemany(
                "INSERT OR IGNORE INTO indicators (article_id, indicator_type, value) VALUES (?, ?, ?)",
                insert_data
            )
            
            debug(f"Inserted {len(values)} {indicator_type} indicators")
        
        conn.commit()
        info(f"Successfully stored {total_indicators} indicators for article_id: {article_id}")
        return True
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Error storing indicators: {e}")
        error(f"Traceback: {error_details}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_indicators_by_article_id(article_id: int) -> Dict[str, List[str]]:
    """
    Retrieve indicators for a specific article.
    
    Args:
        article_id: ID of the article to retrieve indicators for
        
    Returns:
        Dictionary of indicators by type
    """
    from app.config.config import Config
    debug(f"Retrieving indicators for article_id: {article_id}")
    
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT indicator_type, value
            FROM indicators
            WHERE article_id = ?
            ORDER BY indicator_type, value
        """, (article_id,))
        
        results = cursor.fetchall()
        
        # Initialize results dictionary
        indicators = {
            "ipv4": [],
            "ipv6": [],
            "email": [],
            "domain": [],
            "url": [],
            "cve": [],
            "md5": [],
            "sha1": [],
            "sha256": [],
            "mitre_technique": []
        }
        
        # Group results by indicator type
        for row in results:
            indicator_type = row['indicator_type']
            value = row['value']
            
            if indicator_type in indicators:
                indicators[indicator_type].append(value)
        
        info(f"Retrieved {sum(len(indicators[itype]) for itype in indicators)} indicators for article_id: {article_id}")
        return indicators
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Error retrieving indicators: {e}")
        error(f"Traceback: {error_details}")
        return {
            "ipv4": [],
            "ipv6": [],
            "email": [],
            "domain": [],
            "url": [],
            "cve": [],
            "md5": [],
            "sha1": [],
            "sha256": [],
            "mitre_technique": []
        }
    finally:
        conn.close()

def get_indicators_by_url(url: str) -> Dict[str, List[str]]:
    """
    Retrieve indicators for a specific article URL.
    
    Args:
        url: URL of the article to retrieve indicators for
        
    Returns:
        Dictionary of indicators by type
    """
    from app.config.config import Config
    debug(f"Retrieving indicators for URL: {url}")
    
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT i.indicator_type, i.value
            FROM indicators i
            JOIN articles a ON i.article_id = a.id
            WHERE a.url = ?
            ORDER BY i.indicator_type, i.value
        """, (url,))
        
        results = cursor.fetchall()
        
        # Initialize results dictionary
        indicators = {
            "ipv4": [],
            "ipv6": [],
            "email": [],
            "domain": [],
            "url": [],
            "cve": [],
            "md5": [],
            "sha1": [],
            "sha256": [],
            "mitre_technique": []
        }
        
        # Group results by indicator type
        for row in results:
            indicator_type = row['indicator_type']
            value = row['value']
            
            if indicator_type in indicators:
                indicators[indicator_type].append(value)
        
        info(f"Retrieved {sum(len(indicators[itype]) for itype in indicators)} indicators for URL: {url}")
        return indicators
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Error retrieving indicators: {e}")
        error(f"Traceback: {error_details}")
        return {
            "ipv4": [],
            "ipv6": [],
            "email": [],
            "domain": [],
            "url": [],
            "cve": [],
            "md5": [],
            "sha1": [],
            "sha256": [],
            "mitre_technique": []
        }
    finally:
        conn.close()

def get_indicator_stats() -> Dict[str, Any]:
    """
    Get statistics about stored indicators.
    
    Returns:
        Dictionary containing indicator statistics
    """
    from app.config.config import Config
    debug("Retrieving indicator statistics")
    
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Get counts by type
        cursor.execute("""
            SELECT indicator_type, COUNT(*) as count
            FROM indicators
            GROUP BY indicator_type
            ORDER BY count DESC
        """)
        
        type_counts = {}
        for row in cursor.fetchall():
            type_counts[row['indicator_type']] = row['count']
        
        # Get total count
        cursor.execute("SELECT COUNT(*) as total FROM indicators")
        total_count = cursor.fetchone()['total']
        
        # Get article count with indicators
        cursor.execute("""
            SELECT COUNT(DISTINCT article_id) as article_count
            FROM indicators
        """)
        article_count = cursor.fetchone()['article_count']
        
        stats = {
            "total_indicators": total_count,
            "articles_with_indicators": article_count,
            "type_counts": type_counts
        }
        
        info(f"Retrieved indicator stats: {total_count} total indicators across {article_count} articles")
        return stats
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Error getting indicator stats: {e}")
        error(f"Traceback: {error_details}")
        return {
            "total_indicators": 0,
            "articles_with_indicators": 0,
            "type_counts": {}
        }
    finally:
        conn.close() 