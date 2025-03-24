import sqlite3
import json
import os
import traceback
import contextlib
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple, Callable, NoReturn
from contextlib import contextmanager

from app.utilities.logger import info, debug, error, warning, critical

# Global flag to track initialization status
_DB_INITIALIZED = False
_STARTUP_HEALTH_CHECK_COMPLETED = False

# Ensure the data directory exists
os.makedirs('data', exist_ok=True)

@contextmanager
def get_db_connection():
    """
    Context manager for database connections to ensure proper resource handling.
    Usage:
        with get_db_connection() as (conn, cursor):
            cursor.execute(...)
    """
    from app.config.config import Config
    conn = None
    try:
        conn = sqlite3.connect(Config.DB_PATH, timeout=30.0)  # Add timeout for busy database
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        yield conn, cursor
    except Exception as e:
        error(f"Database connection error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def execute_query(query: str, params: tuple = (), fetch_type: str = None) -> Any:
    """
    Execute a SQL query and return the results.
    
    Args:
        query: SQL query string
        params: Parameters for the query
        fetch_type: Type of fetch operation (one, all, None for no fetch)
        
    Returns:
        Query results based on fetch_type
    """
    with get_db_connection() as (conn, cursor):
        try:
            cursor.execute(query, params)
            
            if fetch_type == 'one':
                result = cursor.fetchone()
                return dict(result) if result else None
            elif fetch_type == 'all':
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            conn.rollback()
            error_msg = f"Database error executing query: {e}"
            error(f"{error_msg}\nQuery: {query}\nParams: {params}")
            raise sqlite3.Error(error_msg) from e

def check_db_health(timeout=5.0) -> bool:
    """
    Check database health by running a simple query with timeout.
    
    Args:
        timeout: Maximum time to wait for database response in seconds
        
    Returns:
        True if database is healthy, False otherwise
    """
    global _STARTUP_HEALTH_CHECK_COMPLETED
    
    # Skip if we've already checked
    if _STARTUP_HEALTH_CHECK_COMPLETED:
        return True
        
    start_time = time.time()
    try:
        with get_db_connection() as (conn, cursor):
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
        elapsed = time.time() - start_time
        info(f"Database health check passed in {elapsed:.2f}s")
        _STARTUP_HEALTH_CHECK_COMPLETED = True
        return True
    except Exception as e:
        elapsed = time.time() - start_time
        error(f"Database health check failed after {elapsed:.2f}s: {e}")
        _STARTUP_HEALTH_CHECK_COMPLETED = True
        return False

def get_db_version(conn: sqlite3.Connection) -> int:
    """
    Get the current database version.
    
    Args:
        conn: Database connection
        
    Returns:
        Current database version (integer)
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM db_version ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # If no version found, initialize to version 1
        cursor.execute("INSERT INTO db_version (version) VALUES (1)")
        conn.commit()
        return 1
    except sqlite3.Error as e:
        error(f"Error getting database version: {e}")
        # If db_version table doesn't exist yet, we're at version 0
        return 0
        
def get_latest_db_version() -> int:
    """Get the latest available database version in the codebase."""
    # This should return the latest version number based on available migrations
    return 2  # Update this when adding new migrations

def init_db(force_initialization=False) -> None:
    """
    Initialize the database with required tables if they don't exist.
    
    Args:
        force_initialization: Force initialization even if already done
    """
    global _DB_INITIALIZED
    
    # Skip if already initialized and not forced
    if _DB_INITIALIZED and not force_initialization:
        debug("Database already initialized, skipping")
        return
        
    start_time = time.time()
    
    try:
        with contextlib.ExitStack() as stack:
            conn, cursor = stack.enter_context(get_db_connection())
            
            # Create db_version table to track schema migrations
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS db_version (
                id INTEGER PRIMARY KEY,
                version INTEGER NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Check if we need to initialize version
            cursor.execute("SELECT COUNT(*) FROM db_version")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO db_version (version) VALUES (1)")
                info("Initialized database version tracking (version 1)")
            
            # Create articles table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                content_length INTEGER,
                extraction_time REAL,
                analysis_time REAL,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create analysis_results table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY,
                article_id INTEGER UNIQUE NOT NULL,
                raw_text TEXT,
                structured_data TEXT,
                FOREIGN KEY (article_id) REFERENCES articles (id) ON DELETE CASCADE
            )
            ''')
            
            # Create token_usage table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cached BOOLEAN DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create indicators table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS indicators (
                id INTEGER PRIMARY KEY,
                article_id INTEGER NOT NULL,
                indicator_type TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles (id) ON DELETE CASCADE
            )
            ''')
            
            # Create basic indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_url ON articles (url)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_indicators_article_id ON indicators (article_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_indicators_type ON indicators (indicator_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_indicators_value ON indicators (value)')
            
            conn.commit()
            
            elapsed = time.time() - start_time
            info(f"Database initialized successfully in {elapsed:.2f}s")
            
            # Run migrations if needed
            current_version = get_db_version(conn)
            if current_version < get_latest_db_version():
                migrate_db(conn, current_version)
                
                # After migration, create indexes for the new optimized fields
                # These indexes will only be created if the columns exist after migration
                try:
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_source_reliability ON articles (source_reliability)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_source_credibility ON articles (source_credibility)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_source_type ON articles (source_type)')
                    conn.commit()
                except sqlite3.Error as e:
                    warning(f"Could not create some indexes: {e}")
    
            # Mark as initialized
            _DB_INITIALIZED = True
            
    except sqlite3.Error as e:
        error(f"Database initialization error: {e}")
        raise

def migrate_db(conn: sqlite3.Connection, current_version: int) -> None:
    """
    Perform database migrations to update the schema.
    
    Args:
        conn: Database connection
        current_version: Current database version
    """
    info(f"Starting database migration from version {current_version} to {get_latest_db_version()}")
    
    cursor = conn.cursor()
    
    try:
        # Migration to version 2
        if current_version < 2:
            info("Migrating database to version 2...")
            
            # Check if the optimized columns exist already
            cursor.execute("PRAGMA table_info(articles)")
            columns = {col[1] for col in cursor.fetchall()}
            
            # Add optimized columns if they don't exist
            new_columns = [
                ("summary", "TEXT"),
                ("source_reliability", "TEXT"),
                ("source_credibility", "TEXT"),
                ("source_type", "TEXT"),
                ("threat_actors", "TEXT"),
                ("critical_sectors", "TEXT")
            ]
            
            for col_name, col_type in new_columns:
                if col_name not in columns:
                    cursor.execute(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")
                    info(f"Added column {col_name} to articles table")
            
            # Create indexes for new columns
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_source_reliability ON articles (source_reliability)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_source_credibility ON articles (source_credibility)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_source_type ON articles (source_type)')
            
            # Populate the new columns from existing structured data
            cursor.execute('''
            SELECT a.id, ar.structured_data 
            FROM articles a 
            JOIN analysis_results ar ON a.id = ar.article_id
            WHERE a.summary IS NULL
            ''')
            
            rows = cursor.fetchall()
            info(f"Found {len(rows)} articles to migrate")
            
            for article_id, structured_data in rows:
                try:
                    if structured_data:
                        try:
                            data = json.loads(structured_data) if isinstance(structured_data, str) else structured_data
                        except json.JSONDecodeError:
                            warning(f"Could not parse structured data for article {article_id}, skipping")
                            continue
                        
                        # Extract summary with fallback
                        summary = data.get('summary', '') if isinstance(data, dict) else ''
                        
                        # Extract source evaluation with robust fallbacks
                        source_reliability = 'Medium'
                        source_credibility = 'Medium'
                        source_type = 'Unknown'
                        
                        if isinstance(data, dict):
                            source_eval = data.get('source_evaluation', {})
                            if isinstance(source_eval, dict):
                                # Handle reliability
                                reliability_data = source_eval.get('reliability', {})
                                if isinstance(reliability_data, dict):
                                    source_reliability = reliability_data.get('level', 'Medium')
                                elif isinstance(reliability_data, str):
                                    source_reliability = reliability_data
                                
                                # Handle credibility
                                credibility_data = source_eval.get('credibility', {})
                                if isinstance(credibility_data, dict):
                                    source_credibility = credibility_data.get('level', 'Medium')
                                elif isinstance(credibility_data, str):
                                    source_credibility = credibility_data
                                
                                # Handle source type
                                if 'source_type' in source_eval:
                                    source_type = source_eval.get('source_type', 'Unknown')
                        
                        # Extract threat actors with robust handling
                        threat_actors_str = '[]'
                        if isinstance(data, dict) and 'threat_actors' in data:
                            threat_actors = data.get('threat_actors', [])
                            if isinstance(threat_actors, list):
                                actor_names = []
                                for actor in threat_actors:
                                    if isinstance(actor, dict) and 'name' in actor:
                                        actor_names.append(actor.get('name'))
                                    elif isinstance(actor, str):
                                        actor_names.append(actor)
                                threat_actors_str = json.dumps(actor_names)
                        
                        # Extract critical sectors with robust handling
                        critical_sectors_str = '[]'
                        if isinstance(data, dict) and 'critical_sectors' in data:
                            critical_sectors = data.get('critical_sectors', [])
                            if isinstance(critical_sectors, list):
                                sectors_data = []
                                for sector in critical_sectors:
                                    if isinstance(sector, dict) and 'name' in sector:
                                        # Get score with fallback
                                        score = sector.get('score', 1)
                                        if not isinstance(score, (int, float)):
                                            try:
                                                score = int(score)
                                            except (ValueError, TypeError):
                                                score = 1
                                        
                                        sectors_data.append({
                                            'name': sector['name'],
                                            'score': score
                                        })
                                critical_sectors_str = json.dumps(sectors_data)
                        
                        # Update the article with extracted data
                        cursor.execute('''
                        UPDATE articles 
                        SET summary = ?, 
                            source_reliability = ?, 
                            source_credibility = ?, 
                            source_type = ?,
                            threat_actors = ?,
                            critical_sectors = ?
                        WHERE id = ?
                        ''', (
                            summary, 
                            source_reliability, 
                            source_credibility, 
                            source_type,
                            threat_actors_str,
                            critical_sectors_str,
                            article_id
                        ))
                        
                except (json.JSONDecodeError, KeyError) as e:
                    warning(f"Error migrating article ID {article_id}: {e}")
                    continue
                
            # Update the database version
            cursor.execute("INSERT INTO db_version (version) VALUES (?)", (2,))
            info("Migration to version 2 completed successfully")
            
        # Add future migrations here
        # if current_version < 3:
        #     info("Migrating database to version 3...")
            
        conn.commit()
        info(f"Database migrated successfully to version {get_latest_db_version()}")
        
    except sqlite3.Error as e:
        conn.rollback()
        error(f"Database migration error: {e}")
        raise

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
    info(f"Storing analysis results for URL: {url}")
    debug(f"Analysis details: model={model}, content_length={content_length}, extraction_time={extraction_time:.2f}s, analysis_time={analysis_time:.2f}s")
    
    try:
        with get_db_connection() as (conn, cursor):
            # Extract optimized fields
            summary = structured_analysis.get("summary", "")
            
            # Extract source reliability and credibility
            source_eval = structured_analysis.get("source_evaluation", {})
            reliability = source_eval.get("reliability", {}).get("level", "Medium") if source_eval else "Medium"
            credibility = source_eval.get("credibility", {}).get("level", "Medium") if source_eval else "Medium"
            
            # Extract threat actors
            threat_actors = []
            for actor in structured_analysis.get("threat_actors", []):
                if "name" in actor:
                    threat_actors.append(actor["name"])
            threat_actors_json = json.dumps(threat_actors)
            
            # Extract critical sectors
            critical_sectors = {}
            for sector in structured_analysis.get("critical_sectors", []):
                if "name" in sector and "score" in sector:
                    critical_sectors[sector["name"]] = sector["score"]
            critical_sectors_json = json.dumps(critical_sectors)
            
            # Insert article info with optimized fields
            debug(f"Inserting article info: {title}")
            cursor.execute(
                """
                INSERT INTO articles (
                    url, title, content_length, extraction_time, analysis_time, model, 
                    created_at, summary, source_reliability, source_credibility, 
                    threat_actors, critical_sectors
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    url, title, content_length, extraction_time, analysis_time, model, 
                    datetime.now().isoformat(), summary, reliability, credibility, 
                    threat_actors_json, critical_sectors_json
                )
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
        return False
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Error storing analysis: {e}")
        error(f"Traceback: {error_details}")
        return False

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
    info(f"Updating analysis results for URL: {url}")
    debug(f"Analysis updates: model={model}, content_length={content_length}, extraction_time={extraction_time:.2f}s, analysis_time={analysis_time:.2f}s")
    
    try:
        with get_db_connection() as (conn, cursor):
            # Check if article exists and get its ID
            cursor.execute("SELECT id FROM articles WHERE url = ?", (url,))
            result = cursor.fetchone()
            
            if not result:
                error(f"Cannot update analysis: URL not found in database: {url}")
                return False
                
            article_id = result['id']
            debug(f"Found existing article_id: {article_id} for URL: {url}")
            
            # Extract optimized fields
            summary = structured_analysis.get("summary", "")
            
            # Extract source reliability and credibility
            source_eval = structured_analysis.get("source_evaluation", {})
            reliability = source_eval.get("reliability", {}).get("level", "Medium") if source_eval else "Medium"
            credibility = source_eval.get("credibility", {}).get("level", "Medium") if source_eval else "Medium"
            
            # Extract threat actors
            threat_actors = []
            for actor in structured_analysis.get("threat_actors", []):
                if "name" in actor:
                    threat_actors.append(actor["name"])
            threat_actors_json = json.dumps(threat_actors)
            
            # Extract critical sectors
            critical_sectors = {}
            for sector in structured_analysis.get("critical_sectors", []):
                if "name" in sector and "score" in sector:
                    critical_sectors[sector["name"]] = sector["score"]
            critical_sectors_json = json.dumps(critical_sectors)
            
            # Update article information including created_at timestamp
            current_time = datetime.now().isoformat()
            debug(f"Updating article info: {title}, and setting created_at to current time: {current_time}")
            cursor.execute(
                """
                UPDATE articles 
                SET title = ?, content_length = ?, extraction_time = ?, 
                    analysis_time = ?, model = ?, created_at = ?,
                    summary = ?, source_reliability = ?, source_credibility = ?,
                    threat_actors = ?, critical_sectors = ?
                WHERE id = ?
                """,
                (
                    title, content_length, extraction_time, analysis_time, model, current_time,
                    summary, reliability, credibility, threat_actors_json, critical_sectors_json,
                    article_id
                )
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
        return False

def get_analysis_by_url(url: str) -> Optional[Dict[str, Any]]:
    """Retrieve analysis results for a specific URL."""
    debug(f"Retrieving analysis results for URL: {url}")
    
    try:
        with get_db_connection() as (conn, cursor):
            cursor.execute("""
                SELECT a.id, a.url, a.title, a.content_length, a.model, a.created_at, 
                       a.summary, a.source_reliability, a.source_credibility, a.threat_actors, a.critical_sectors,
                       r.raw_text, r.structured_data
                FROM articles a
                JOIN analysis_results r ON a.id = r.article_id
                WHERE a.url = ?
            """, (url,))
            
            result = cursor.fetchone()
            
            if result:
                info(f"Found existing analysis for URL: {url}")
                debug(f"Analysis details: id={result['id']}, model={result['model']}, created_at={result['created_at']}")
                
                # Parse JSON fields
                try:
                    threat_actors = json.loads(result['threat_actors']) if result['threat_actors'] else []
                except (json.JSONDecodeError, TypeError):
                    threat_actors = []
                    
                try:
                    critical_sectors = json.loads(result['critical_sectors']) if result['critical_sectors'] else {}
                except (json.JSONDecodeError, TypeError):
                    critical_sectors = {}
                
                try:
                    structured_data = json.loads(result['structured_data'])
                except (json.JSONDecodeError, TypeError):
                    structured_data = {}
                
                return {
                    'id': result['id'],
                    'url': result['url'],
                    'title': result['title'],
                    'content_length': result['content_length'],
                    'model': result['model'],
                    'created_at': result['created_at'],
                    'summary': result['summary'],
                    'source_reliability': result['source_reliability'],
                    'source_credibility': result['source_credibility'],
                    'threat_actors': threat_actors,
                    'critical_sectors': critical_sectors,
                    'raw_text': result['raw_text'],
                    'structured_data': structured_data
                }
            debug(f"No analysis found for URL: {url}")
            return None
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Error retrieving analysis: {e}")
        error(f"Traceback: {error_details}")
        return None

def get_recent_analyses(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve the most recent analyses."""
    debug(f"Retrieving {limit} most recent analyses")
    
    try:
        with get_db_connection() as (conn, cursor):
            if limit is None:
                # No limit, retrieve all analyses
                cursor.execute("""
                    SELECT a.id, a.url, a.title, a.content_length, a.model, a.created_at
                    FROM articles a
                    ORDER BY a.created_at DESC
                """)
            else:
                # Apply specified limit
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

def track_token_usage(model: str, input_tokens: int, output_tokens: int, cached: bool = False) -> bool:
    """Track token usage for billing purposes."""
    debug(f"Tracking token usage: model={model}, input={input_tokens}, output={output_tokens}, cached={cached}")
    
    try:
        with get_db_connection() as (conn, cursor):
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
        return False

def get_token_usage_stats() -> Dict[str, Any]:
    """Get token usage statistics."""
    debug("Retrieving token usage statistics")
    
    try:
        with get_db_connection() as (conn, cursor):
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

def store_indicators(article_id: int, indicators: Dict[str, List[str]]) -> bool:
    """
    Store extracted indicators in the database.
    
    Args:
        article_id: ID of the article the indicators are associated with
        indicators: Dictionary of indicators by type
        
    Returns:
        True if successful, False otherwise
    """
    info(f"Storing indicators for article_id: {article_id}")
    
    try:
        with get_db_connection() as (conn, cursor):
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
        return False

def get_indicators_by_article_id(article_id: int) -> Dict[str, List[str]]:
    """
    Retrieve indicators for a specific article.
    
    Args:
        article_id: ID of the article to retrieve indicators for
        
    Returns:
        Dictionary of indicators by type
    """
    debug(f"Retrieving indicators for article_id: {article_id}")
    
    try:
        with get_db_connection() as (conn, cursor):
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

def get_indicators_by_url(url: str) -> Dict[str, List[str]]:
    """
    Retrieve indicators for a specific article URL.
    
    Args:
        url: URL of the article to retrieve indicators for
        
    Returns:
        Dictionary of indicators by type
    """
    debug(f"Retrieving indicators for URL: {url}")
    
    try:
        with get_db_connection() as (conn, cursor):
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

def get_indicator_stats() -> Dict[str, Any]:
    """
    Get statistics about stored indicators.
    
    Returns:
        Dictionary containing indicator statistics
    """
    debug("Retrieving indicator statistics")
    
    try:
        with get_db_connection() as (conn, cursor):
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

def find_analyses_by_reliability(reliability_level: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Find analyses with a specific source reliability level.
    
    Args:
        reliability_level: The reliability level to search for (High, Medium, Low)
        limit: Maximum number of results to return
        
    Returns:
        List of analysis results
    """
    try:
        with contextlib.ExitStack() as stack:
            conn = stack.enter_context(get_db_connection())
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT a.id, a.url, a.title, a.model, a.created_at, 
                   a.summary, a.source_reliability, a.source_credibility, a.source_type
            FROM articles a
            WHERE a.source_reliability = ?
            ORDER BY a.created_at DESC
            LIMIT ?
            ''', (reliability_level, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'url': row['url'],
                    'title': row['title'],
                    'model': row['model'],
                    'created_at': row['created_at'],
                    'summary': row['summary'],
                    'source_reliability': row['source_reliability'],
                    'source_credibility': row['source_credibility'],
                    'source_type': row['source_type']
                })
            
            return results
            
    except sqlite3.Error as e:
        error(f"Error finding analyses by reliability: {e}")
        return []

def find_analyses_by_threat_actor(actor_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Find analyses mentioning a specific threat actor.
    
    Args:
        actor_name: The name of the threat actor to search for
        limit: Maximum number of results to return
        
    Returns:
        List of analysis results
    """
    try:
        with contextlib.ExitStack() as stack:
            conn = stack.enter_context(get_db_connection())
            cursor = conn.cursor()
            
            # Use JSON search with LIKE since we're storing JSON array
            search_pattern = f'%"{actor_name}"%'
            
            cursor.execute('''
            SELECT a.id, a.url, a.title, a.model, a.created_at, 
                   a.summary, a.threat_actors
            FROM articles a
            WHERE a.threat_actors LIKE ?
            ORDER BY a.created_at DESC
            LIMIT ?
            ''', (search_pattern, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'url': row['url'],
                    'title': row['title'],
                    'model': row['model'],
                    'created_at': row['created_at'],
                    'summary': row['summary'],
                    'threat_actors': json.loads(row['threat_actors']) if row['threat_actors'] else []
                })
            
            return results
            
    except sqlite3.Error as e:
        error(f"Error finding analyses by threat actor: {e}")
        return []

def find_analyses_by_critical_sector(sector_name: str, min_score: int = 3, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Find analyses with a specific critical infrastructure sector scored at or above a threshold.
    
    Args:
        sector_name: The name of the sector to search for
        min_score: Minimum score threshold (1-5)
        limit: Maximum number of results to return
        
    Returns:
        List of analysis results
    """
    try:
        with contextlib.ExitStack() as stack:
            conn = stack.enter_context(get_db_connection())
            cursor = conn.cursor()
            
            # Use JSON search with LIKE since we're storing JSON array
            search_pattern = f'%"{sector_name}"%'
            
            cursor.execute('''
            SELECT a.id, a.url, a.title, a.model, a.created_at, 
                   a.summary, a.critical_sectors
            FROM articles a
            WHERE a.critical_sectors LIKE ?
            ORDER BY a.created_at DESC
            LIMIT ?
            ''', (search_pattern, limit))
            
            results = []
            for row in cursor.fetchall():
                sectors = json.loads(row['critical_sectors']) if row['critical_sectors'] else []
                
                # Check if any sector matches the name and meets the minimum score
                matching_sectors = [
                    s for s in sectors 
                    if s.get('name') == sector_name and s.get('score', 0) >= min_score
                ]
                
                if matching_sectors:
                    results.append({
                        'id': row['id'],
                        'url': row['url'],
                        'title': row['title'],
                        'model': row['model'],
                        'created_at': row['created_at'],
                        'summary': row['summary'],
                        'sector_score': max(s.get('score', 0) for s in matching_sectors)
                    })
            
            # Sort by sector score (highest first) then by date
            results.sort(key=lambda x: (-x['sector_score'], x['created_at']), reverse=True)
            return results[:limit]  # Apply limit after filtering and sorting
            
    except sqlite3.Error as e:
        error(f"Error finding analyses by critical sector: {e}")
        return []

def get_top_threat_actors(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get the most frequently mentioned threat actors across all analyses.
    
    Args:
        limit: Maximum number of actors to return
        
    Returns:
        List of threat actors with frequency counts
    """
    debug(f"Getting top {limit} threat actors")
    
    try:
        with get_db_connection() as (conn, cursor):
            cursor.execute("SELECT threat_actors FROM articles WHERE threat_actors IS NOT NULL")
            results = cursor.fetchall()
            
            # Count actor occurrences across all analyses
            actor_counts = {}
            for row in results:
                try:
                    actors = json.loads(row['threat_actors'])
                    for actor in actors:
                        actor_counts[actor] = actor_counts.get(actor, 0) + 1
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # Sort by count (descending) and return top N
            sorted_actors = sorted(actor_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
            
            return [{'name': actor, 'count': count} for actor, count in sorted_actors]
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Error getting top threat actors: {e}")
        error(f"Traceback: {error_details}")
        return [] 