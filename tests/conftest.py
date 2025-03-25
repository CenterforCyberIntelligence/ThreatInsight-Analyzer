import os
import sys
import pytest
import tempfile
import shutil
import sqlite3
from flask import Flask, template_rendered
from contextlib import contextmanager

# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models.database import init_db, get_db_connection

@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    # Create a temporary directory for test files
    temp_dir = tempfile.mkdtemp()
    
    # Create a temporary data directory for the test database
    os.makedirs(os.path.join(temp_dir, 'data'), exist_ok=True)
    
    # Set up environment variables for testing
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['SECRET_KEY'] = 'test-key'
    
    # Create the test application
    test_app = create_app()
    
    # Override configuration for testing
    test_app.config.update({
        'TESTING': True,
        'SERVER_NAME': 'localhost.localdomain',
        'DB_PATH': os.path.join(temp_dir, 'data', 'test_article_analysis.db'),
        'SECRET_KEY': 'test-key',
    })
    
    # Establish application context
    with test_app.app_context():
        # Initialize the test database
        init_db()
        
        yield test_app
    
    # Clean up the temporary directory
    shutil.rmtree(temp_dir)

@pytest.fixture
def client(app):
    """Create a test client for the application."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create a test CLI runner for the application."""
    return app.test_cli_runner()

@pytest.fixture
def db(app):
    """Create a database connection for testing."""
    with app.app_context():
        with get_db_connection() as (conn, cursor):
            yield conn, cursor

@contextmanager
def captured_templates(app):
    """Capture templates that were rendered during the request."""
    recorded = []
    
    def record(sender, template, context, **extra):
        recorded.append((template, context))
    
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)

@pytest.fixture
def mock_requests_get(monkeypatch):
    """Mock the requests.get function."""
    class MockResponse:
        def __init__(self, text, status_code):
            self.text = text
            self.status_code = status_code
            
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP Status: {self.status_code}")
    
    def _mock_get(*args, **kwargs):
        # Mock a response for a simple article
        return MockResponse(
            """
            <html>
                <head><title>Test Article</title></head>
                <body>
                    <article>
                        <h1>Cybersecurity Threat Report</h1>
                        <p>This is a test article about cybersecurity threats.</p>
                        <p>It includes mentions of CVE-2023-1234 vulnerability.</p>
                        <p>The threat actor used IP address 192.168.1.100 for attacks.</p>
                        <p>Malware hash: 01234567890123456789012345678901</p>
                    </article>
                </body>
            </html>
            """,
            200
        )
    
    monkeypatch.setattr("requests.get", _mock_get)

@pytest.fixture
def mock_openai_completion(monkeypatch):
    """Mock the OpenAI ChatCompletion API."""
    class MockAsyncChatCompletion:
        @staticmethod
        def acreate(*args, **kwargs):
            return {
                "id": "mock-completion-id",
                "model": kwargs.get("model", "gpt-4o"),
                "choices": [
                    {
                        "message": {
                            "content": """
                            1. Summary of Article
                            This article discusses a recent cybersecurity threat involving CVE-2023-1234 vulnerability exploited by threat actors using IP address 192.168.1.100 and distributing malware with a specific hash value.
                            
                            2. Source Evaluation
                            - Reliability: Medium - Limited technical details provided but comes from a known source
                            - Credibility: Medium - Information aligns with known threat patterns
                            - Source Type: Cybersecurity Vendor
                            
                            3. MITRE ATT&CK Techniques
                            1. T1190 - Exploit Public-Facing Application
                            2. T1027 - Obfuscated Files or Information
                            
                            4. Key Threat Intelligence Insights
                            1. The CVE-2023-1234 vulnerability provides attackers with remote code execution capabilities.
                            2. The threat actor employs sophisticated evasion techniques to avoid detection.
                            3. Multiple critical infrastructure sectors are potentially impacted by this threat.
                            
                            5. Potential Bias or Issues
                            1. The report may overstate the severity of the threat to generate attention.
                            2. Technical details are limited which makes proper validation difficult.
                            
                            6. Relevance to U.S. Government (Score: 4)
                            This threat directly targets government systems and could impact national security infrastructure.
                            
                            7. Critical Infrastructure Sectors Assessment
                            - National Security: 4
                            - Chemical: 2
                            - Commercial Facilities: 3
                            - Communications: 4
                            - Critical Manufacturing: 3
                            - Dams: 1
                            - Defense Industrial Base: 4
                            - Emergency Services: 3
                            - Energy: 3
                            - Financial Services: 3
                            - Food & Agriculture: 1
                            - Government Services & Facilities: 5
                            - Healthcare & Public Health: 2
                            - Information Technology: 5
                            - Nuclear Reactors, Materials, and Waste: 2
                            - Transportation Systems: 2
                            - Water & Wastewater Systems: 2
                            """
                        },
                        "finish_reason": "stop",
                        "index": 0
                    }
                ],
                "usage": {
                    "prompt_tokens": 500,
                    "completion_tokens": 500,
                    "total_tokens": 1000
                }
            }
    
    class MockChatCompletion:
        @staticmethod
        def create(*args, **kwargs):
            return MockAsyncChatCompletion.acreate(*args, **kwargs)
    
    monkeypatch.setattr("openai.chat.completions.create", MockChatCompletion.create)

@pytest.fixture
def sample_article_data():
    """Return sample article data for testing."""
    return {
        "url": "https://example-security.com/threat-report-2023",
        "title": "Cybersecurity Threat Report",
        "content": "This is a test article about cybersecurity threats. It includes mentions of CVE-2023-1234 vulnerability. The threat actor used IP address 192.168.1.100 for attacks. Malware hash: 01234567890123456789012345678901",
        "content_length": 250,
        "extraction_time": 0.5,
        "analysis_time": 1.2,
        "model": "gpt-4o",
        "raw_analysis": "This is a raw analysis of the article.",
        "structured_analysis": {
            "summary": "This article discusses a recent cybersecurity threat.",
            "source_evaluation": {
                "reliability": {"level": "Medium", "justification": "Limited technical details provided but comes from a known source"},
                "credibility": {"level": "Medium", "justification": "Information aligns with known threat patterns"}, 
                "source_type": "Cybersecurity Vendor"
            },
            "mitre_techniques": [
                {"id": "T1190", "name": "Exploit Public-Facing Application"}
            ],
            "key_insights": [
                "The CVE-2023-1234 vulnerability provides attackers with remote code execution capabilities."
            ],
            "potential_bias": [
                "The report may overstate the severity of the threat to generate attention."
            ],
            "sector_relevance": {
                "national_security": 4,
                "government_services": 5,
                "information_technology": 5
            }
        }
    } 