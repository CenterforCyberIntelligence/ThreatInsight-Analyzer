import pytest
import json
import time
from unittest.mock import patch
from datetime import datetime

from app.models.database import (
    get_db_connection, 
    execute_query, 
    init_db, 
    store_analysis, 
    update_analysis, 
    get_analysis_by_url, 
    get_recent_analyses, 
    track_token_usage, 
    get_token_usage_stats,
    store_indicators,
    get_indicators_by_article_id,
    get_indicators_by_url,
    get_indicator_stats
)

# Basic database connection and execution tests
def test_get_db_connection(app):
    """Test that database connection can be established and works correctly."""
    with app.app_context():
        with get_db_connection() as (conn, cursor):
            assert conn is not None
            assert cursor is not None
            
            # Test basic query execution
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == 1

def test_execute_query(app):
    """Test the execute_query utility function with different fetch types."""
    with app.app_context():
        # Test with fetch_type=None (write operation)
        result = execute_query("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT)")
        assert result is not None
        
        # Test with fetch_type='one'
        result = execute_query("SELECT 1 as value", (), 'one')
        assert result is not None
        assert result['value'] == 1
        
        # Test with fetch_type='all'
        execute_query("INSERT INTO test_table (name) VALUES (?)", ('test1',))
        execute_query("INSERT INTO test_table (name) VALUES (?)", ('test2',))
        result = execute_query("SELECT * FROM test_table", (), 'all')
        assert result is not None
        assert len(result) == 2
        assert result[0]['name'] == 'test1'
        assert result[1]['name'] == 'test2'
        
        # Test with error handling
        result = execute_query("SELECT * FROM nonexistent_table", (), 'all')
        assert result is None

# Test storing and retrieving analysis
def test_store_analysis(app, sample_article_data):
    """Test storing analysis data in the database."""
    with app.app_context():
        # Store the analysis
        result = store_analysis(
            url=sample_article_data['url'],
            title=sample_article_data['title'],
            content_length=sample_article_data['content_length'],
            extraction_time=sample_article_data['extraction_time'],
            analysis_time=sample_article_data['analysis_time'],
            model=sample_article_data['model'],
            raw_analysis=sample_article_data['raw_analysis'],
            structured_analysis=sample_article_data['structured_analysis']
        )
        assert result is True
        
        # Verify it was stored by retrieving it
        analysis = get_analysis_by_url(sample_article_data['url'])
        assert analysis is not None
        assert analysis['url'] == sample_article_data['url']
        assert analysis['title'] == sample_article_data['title']
        assert analysis['content_length'] == sample_article_data['content_length']
        assert analysis['model'] == sample_article_data['model']
        assert analysis['raw_text'] == sample_article_data['raw_analysis']
        
        # Test duplicate URL handling (should return False)
        result = store_analysis(
            url=sample_article_data['url'],
            title=sample_article_data['title'],
            content_length=sample_article_data['content_length'],
            extraction_time=sample_article_data['extraction_time'],
            analysis_time=sample_article_data['analysis_time'],
            model=sample_article_data['model'],
            raw_analysis=sample_article_data['raw_analysis'],
            structured_analysis=sample_article_data['structured_analysis']
        )
        assert result is False

def test_update_analysis(app, sample_article_data):
    """Test updating an existing analysis in the database."""
    with app.app_context():
        # First store the initial analysis
        store_analysis(
            url=sample_article_data['url'],
            title=sample_article_data['title'],
            content_length=sample_article_data['content_length'],
            extraction_time=sample_article_data['extraction_time'],
            analysis_time=sample_article_data['analysis_time'],
            model=sample_article_data['model'],
            raw_analysis=sample_article_data['raw_analysis'],
            structured_analysis=sample_article_data['structured_analysis']
        )
        
        # Now update with new data
        updated_data = sample_article_data.copy()
        updated_data['title'] = "Updated Title"
        updated_data['model'] = "gpt-4-turbo"
        updated_data['raw_analysis'] = "This is an updated analysis."
        
        result = update_analysis(
            url=updated_data['url'],
            title=updated_data['title'],
            content_length=updated_data['content_length'],
            extraction_time=updated_data['extraction_time'],
            analysis_time=updated_data['analysis_time'],
            model=updated_data['model'],
            raw_analysis=updated_data['raw_analysis'],
            structured_analysis=updated_data['structured_analysis']
        )
        assert result is True
        
        # Verify the update
        analysis = get_analysis_by_url(updated_data['url'])
        assert analysis is not None
        assert analysis['title'] == updated_data['title']
        assert analysis['model'] == updated_data['model']
        assert analysis['raw_text'] == updated_data['raw_analysis']
        
        # Test update for nonexistent URL
        result = update_analysis(
            url="https://nonexistent.example.com",
            title="Nonexistent Title",
            content_length=100,
            extraction_time=0.5,
            analysis_time=1.0,
            model="gpt-4o",
            raw_analysis="This should not be stored.",
            structured_analysis={}
        )
        assert result is False

def test_get_recent_analyses(app, sample_article_data):
    """Test retrieving recent analyses from the database."""
    with app.app_context():
        # Store multiple analyses
        for i in range(5):
            modified_data = sample_article_data.copy()
            modified_data['url'] = f"https://example-security.com/article-{i}"
            modified_data['title'] = f"Article {i}"
            
            store_analysis(
                url=modified_data['url'],
                title=modified_data['title'],
                content_length=modified_data['content_length'],
                extraction_time=modified_data['extraction_time'],
                analysis_time=modified_data['analysis_time'],
                model=modified_data['model'],
                raw_analysis=modified_data['raw_analysis'],
                structured_analysis=modified_data['structured_analysis']
            )
            
            # Add a small delay to ensure different timestamps
            time.sleep(0.01)
        
        # Test retrieving recent analyses with default limit
        recent = get_recent_analyses()
        assert recent is not None
        assert len(recent) == 5
        
        # Test with custom limit
        recent_limited = get_recent_analyses(limit=3)
        assert recent_limited is not None
        assert len(recent_limited) == 3
        
        # Check that order is correct (most recent first)
        assert recent_limited[0]['title'] == "Article 4"
        assert recent_limited[1]['title'] == "Article 3"
        assert recent_limited[2]['title'] == "Article 2"

def test_track_token_usage(app):
    """Test tracking token usage in the database."""
    with app.app_context():
        # Track token usage for different models
        result1 = track_token_usage("gpt-4o", 1000, 500, cached=False)
        assert result1 is True
        
        result2 = track_token_usage("gpt-4o", 800, 400, cached=True)
        assert result2 is True
        
        result3 = track_token_usage("gpt-3.5-turbo", 500, 200, cached=False)
        assert result3 is True
        
        # Test with error simulation
        with patch('app.models.database.execute_query', return_value=None):
            result4 = track_token_usage("gpt-4o", 1000, 500)
            assert result4 is False

def test_get_token_usage_stats(app):
    """Test retrieving token usage statistics from the database."""
    with app.app_context():
        # Track token usage for different models
        track_token_usage("gpt-4o", 1000, 500, cached=False)
        track_token_usage("gpt-4o", 800, 400, cached=True)
        track_token_usage("gpt-3.5-turbo", 500, 200, cached=False)
        
        # Get token usage stats
        stats = get_token_usage_stats()
        assert stats is not None
        
        # Check total stats
        assert stats['total_tokens'] > 0
        assert stats['total_cached_requests'] == 1
        assert stats['total_api_requests'] == 2
        
        # Check model-specific stats
        assert len(stats['models']) >= 2
        assert "gpt-4o" in [model['model'] for model in stats['models']]
        assert "gpt-3.5-turbo" in [model['model'] for model in stats['models']]
        
        for model in stats['models']:
            if model['model'] == "gpt-4o":
                assert model['total_tokens'] == 1000 + 500 + 800 + 400
                assert model['input_tokens'] == 1000 + 800
                assert model['output_tokens'] == 500 + 400
                assert model['cached_requests'] == 1
                assert model['api_requests'] == 1

# Test indicator storage and retrieval
def test_store_indicators(app, sample_article_data):
    """Test storing and retrieving indicators of compromise."""
    with app.app_context():
        # First store an article to get an article_id
        store_analysis(
            url=sample_article_data['url'],
            title=sample_article_data['title'],
            content_length=sample_article_data['content_length'],
            extraction_time=sample_article_data['extraction_time'],
            analysis_time=sample_article_data['analysis_time'],
            model=sample_article_data['model'],
            raw_analysis=sample_article_data['raw_analysis'],
            structured_analysis=sample_article_data['structured_analysis']
        )
        
        # Get the article ID
        article = get_analysis_by_url(sample_article_data['url'])
        article_id = article['id']
        
        # Store indicators
        indicators = {
            "ipv4": ["192.168.1.1", "10.0.0.1"],
            "domain": ["evil-domain.com", "malware.org"],
            "cve": ["CVE-2023-1234", "CVE-2023-5678"],
            "mitre_technique": ["T1190", "T1027"]
        }
        
        result = store_indicators(article_id, indicators)
        assert result is True
        
        # Test retrieving indicators by article_id
        retrieved_indicators = get_indicators_by_article_id(article_id)
        assert retrieved_indicators is not None
        assert "ipv4" in retrieved_indicators
        assert "domain" in retrieved_indicators
        assert "cve" in retrieved_indicators
        assert "mitre_technique" in retrieved_indicators
        
        # Check that all our expected indicators are present, but allow for additional ones
        # that might be extracted from the content
        for ip in indicators["ipv4"]:
            assert ip in retrieved_indicators["ipv4"]
        for domain in indicators["domain"]:
            assert domain in retrieved_indicators["domain"]
        for cve in indicators["cve"]:
            assert cve in retrieved_indicators["cve"]
        for technique in indicators["mitre_technique"]:
            assert technique in retrieved_indicators["mitre_technique"]
        
        # Test retrieving indicators by URL
        url_indicators = get_indicators_by_url(sample_article_data['url'])
        assert url_indicators is not None
        assert url_indicators == retrieved_indicators
        
        # Test retrieving indicators for nonexistent article
        nonexistent_indicators = get_indicators_by_article_id(9999)
        assert nonexistent_indicators is not None
        assert all(len(indicators) == 0 for indicators in nonexistent_indicators.values())
        
        nonexistent_url_indicators = get_indicators_by_url("https://nonexistent.example.com")
        assert nonexistent_url_indicators is not None
        assert all(len(indicators) == 0 for indicators in nonexistent_url_indicators.values())

def test_get_indicator_stats(app, sample_article_data):
    """Test retrieving indicator statistics from the database."""
    with app.app_context():
        # First store an article to get an article_id
        store_analysis(
            url=sample_article_data['url'],
            title=sample_article_data['title'],
            content_length=sample_article_data['content_length'],
            extraction_time=sample_article_data['extraction_time'],
            analysis_time=sample_article_data['analysis_time'],
            model=sample_article_data['model'],
            raw_analysis=sample_article_data['raw_analysis'],
            structured_analysis=sample_article_data['structured_analysis']
        )
        
        # Get the article ID
        article = get_analysis_by_url(sample_article_data['url'])
        article_id = article['id']
        
        # Store indicators
        indicators = {
            "ipv4": ["192.168.1.1", "10.0.0.1"],
            "domain": ["evil-domain.com", "malware.org"],
            "cve": ["CVE-2023-1234", "CVE-2023-5678"],
            "mitre_technique": ["T1190", "T1027"]
        }
        
        store_indicators(article_id, indicators)
        
        # Store indicators for a second article
        modified_data = sample_article_data.copy()
        modified_data['url'] = "https://example-security.com/article-2"
        modified_data['title'] = "Article 2"
        
        store_analysis(
            url=modified_data['url'],
            title=modified_data['title'],
            content_length=modified_data['content_length'],
            extraction_time=modified_data['extraction_time'],
            analysis_time=modified_data['analysis_time'],
            model=modified_data['model'],
            raw_analysis=modified_data['raw_analysis'],
            structured_analysis=modified_data['structured_analysis']
        )
        
        article2 = get_analysis_by_url(modified_data['url'])
        article_id2 = article2['id']
        
        indicators2 = {
            "ipv4": ["192.168.1.1", "172.16.0.1"],
            "url": ["https://evil-site.com"],
            "cve": ["CVE-2023-1234"],
            "mitre_technique": ["T1190", "T1059"]
        }
        
        store_indicators(article_id2, indicators2)
        
        # Get indicator stats
        stats = get_indicator_stats()
        assert stats is not None
        
        # Check total counts
        assert stats['total_indicators'] == 11  # Total unique indicators across both articles
        assert stats['total_articles'] == 2
        
        # Check type counts
        assert stats['indicator_counts']['ipv4'] == 3  # 3 unique IPs
        assert stats['indicator_counts']['domain'] == 2
        assert stats['indicator_counts']['url'] == 1
        assert stats['indicator_counts']['cve'] == 2  # 2 unique CVEs
        assert stats['indicator_counts']['mitre_technique'] == 3  # 3 unique techniques
        
        # Check most common indicators
        assert len(stats['most_common_indicators']) > 0
        
        # CVE-2023-1234 and T1190 should be in both articles
        for indicator in stats['most_common_indicators']:
            if indicator['value'] == 'CVE-2023-1234' or indicator['value'] == 'T1190':
                assert indicator['count'] == 2

def test_database_error_handling(app):
    """Test database error handling."""
    with app.app_context():
        # Test with invalid SQL
        result = execute_query("SELECT * FROM nonexistent_table")
        assert result is None
        
        # Test with connection error simulation
        with patch('app.models.database.get_db_connection', side_effect=Exception("Connection error")):
            result = execute_query("SELECT 1")
            assert result is None 