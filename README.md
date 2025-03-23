# Artificial Cyber Intelligence Analyst 
[![Version: 1.0.1](https://img.shields.io/badge/Version-1.0.1-brightgreen.svg)](https://github.com/CenterforCyberIntelligence/ThreatInsight-Analyzer)
[![AI Development Project](https://img.shields.io/badge/🤖_AI_Development-Project-blue.svg)](https://github.com/CenterforCyberIntelligence/ThreatInsight-Analyzer)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC_BY--NC_4.0-lightgrey.svg)](LICENSE.md)

[![Visitors](https://visitor-badge.laobi.icu/badge?page_id=CenterforCyberIntelligence.ThreatInsight-Analyzer)](https://github.com/CenterforCyberIntelligence/ThreatInsight-Analyzer)
[![GitHub Stars](https://img.shields.io/github/stars/CenterforCyberIntelligence/ThreatInsight-Analyzer.svg?style=flat&color=8B7355)](https://github.com/CenterforCyberIntelligence/ThreatInsight-Analyzer/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/CenterforCyberIntelligence/ThreatInsight-Analyzer.svg?style=flat&color=7B886B)](https://github.com/CenterforCyberIntelligence/ThreatInsight-Analyzer/network/members)

A web-based tool that uses AI to aid in rapid summarization and analysis of cybersecurity articles to generate structured threat intelligence insights.

## Table of Contents

- [Current Status](#current-status)
- [Documentation](#documentation)
  - [README.md](README.md) - Project overview and getting started
  - [CHANGELOG.md](CHANGELOG.md) - Version history and updates
  - [Known Issues.md](Known%20Issues.md) - Current and resolved issues
  - [TODO.md](TODO.md) - Future development roadmap
  - [LICENSE.md](LICENSE.md) - License information
- [Technology Overview](#technology-overview)
- [Version](#version)
- [Features](#features)
- [Interface Preview](#interface-preview)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
  - [URL Validation Configuration](#url-validation-configuration)
- [Available Models](#available-models)
- [Running the Application](#running-the-application)
- [Usage](#usage)
- [Development Status](#development-status)
- [Database Structure](#database-structure)
  - [Tables](#tables)
  - [Database Functions](#database-functions)
- [Security Notes](#security-notes)
- [Testing](#testing)
- [Disclaimer](#disclaimer)
- [License](#license)

## Current Status

This project is in active development. Features are being implemented incrementally, and the codebase is evolving. Known issues are documented in the [Known Issues](Known%20Issues.md) file. If you are a fan of this project and want to see it keep growing, consider adding some fuel to the tank. 

<div align="center">
  <a href="https://buymeacoffee.com/centerforcyberintel" target="_blank">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" >
  </a>
  <p>
</div>

> **IMPORTANT NOTICE**: This is a ✨ vibe-coding ✨ project I started because I wanted a rapid way to summarize and extract critical intelligence information from articles I read on the internet. Because I am not a developer by trade, and I am heavily relying on AI Agents to support my develoment of this platform, bugs and issues are expected. Use at your own risk and enjoy the process. If you have suggestions on how to improve the project, please let me know!

## Documentation

- [README.md](README.md) - Project overview and getting started guide
- [CHANGELOG.md](CHANGELOG.md) - History of changes and version updates
- [Known Issues.md](Known%20Issues.md) - Current and resolved issues
- [TODO.md](TODO.md) - Roadmap for future features and improvements
- [LICENSE.md](LICENSE.md) - License information

## Technology Overview
- **Release Date:** March 22, 2025

### Languages
<div align="center">
  <img src="https://img.shields.io/badge/Language-Python-7D6E4A?style=for-the-badge&logo=python" alt="Python" />
  &nbsp;&nbsp;
  <img src="https://img.shields.io/badge/Language-HTML/CSS-8C6F4B?style=for-the-badge&logo=html5" alt="HTML/CSS" />
</div>

### Backend Framework
<div align="center">
  <img src="https://img.shields.io/badge/Framework-Flask-6A8372?style=for-the-badge&logo=flask" alt="Flask" />
</div>

### Frontend Libraries
<div align="center">
  <img src="https://img.shields.io/badge/Library-HTMX-7B886B?style=for-the-badge&logo=html5" alt="HTMX" />
</div>

### Technologies
<div align="center">
  <img src="https://img.shields.io/badge/Database-SQLite-817865?style=for-the-badge&logo=sqlite" alt="SQLite" />
  &nbsp;&nbsp;
  <img src="https://img.shields.io/badge/API-OpenAI-6B8A87?style=for-the-badge&logo=openai" alt="OpenAI API" />
</div>

## Version
Current version: 1.0.1

## Features
- Web-based user interface for submitting and reviewing threat intelligence articles
- Automated OpenAI-powered analysis of cybersecurity articles and reports
- Extraction and standardization of MITRE ATT&CK techniques with proper linking
- Source credibility and reliability assessments
- Threat actor identification and categorization
- Critical infrastructure sector impact analysis
- Database storage for historical analysis and quick retrieval
- Support for multiple OpenAI models with automatic cost calculation
- Model ID normalization system to handle different model versions
- Statistics dashboard with token usage and cost breakdown
- Export analysis results in multiple formats (JSON, CSV, PDF, Markdown) for offline use and sharing

## Interface Preview

<div align="center">
  <img src="static/images/FrontEndExample.png" alt="Artificial Cyber Intelligence Analyst Interface" width="800">
</div>

## Project Structure

```
├── app/                   # Main application package
│   ├── __init__.py        # Application factory
│   ├── blueprints/        # Route blueprints
│   │   ├── main.py        # Main routes
│   │   ├── analysis.py    # Analysis routes
│   │   ├── statistics.py  # Statistics routes
│   │   └── settings.py    # Settings routes
│   ├── config/            # Configuration
│   │   └── config.py      # Config classes
│   ├── models/            # Database models
│   │   └── database.py    # Database operations
│   └── utilities/         # Utility functions
│       ├── logger.py      # Logging utilities
│       ├── article_analyzer.py  # AI analysis logic and parsing
│       ├── article_extractor.py # URL content extraction
│       └── indicator_extractor.py # IOC extraction utilities
├── static/                # Static assets
├── templates/             # Frontend templates
│   ├── index.html         # Main interface
│   ├── statistics.html    # Statistics page
│   └── partials/          # Reusable template components
├── run.py                 # Application entry point
├── requirements.txt       # Python dependencies
├── .env.template          # Configuration template
└── Known Issues.md        # Documentation of known issues
```

## Installation

1. Clone the repository
```bash
git clone [repository-url]
cd [repository-name]
```

2. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.template .env
# Edit .env with your configuration values including your OpenAI API key
```

## Configuration

Required environment variables in `.env`:

```
# OpenAI API Configuration
OPENAI_API_KEY=your_api_key_here

# OpenAI Model Configuration
OPENAI_MODEL=gpt-4o

# Available models with their descriptions (JSON format)
AVAILABLE_MODELS={"gpt-4o-mini":{"name":"GPT-4o mini","recommended_for":"Quick analysis of news articles and blog posts"},"gpt-4o":{"name":"GPT-4o","recommended_for":"Detailed analysis of technical reports and research papers"},"gpt-4-turbo":{"name":"GPT-4.5 Turbo","recommended_for":"In-depth analysis of complex threat reports and intelligence briefs"}}

# Model Parameters
OPENAI_TEMPERATURE=0.1
OPENAI_MAX_TOKENS=4000

# Flask Application Settings
FLASK_HOST=0.0.0.0
FLASK_PORT=8000
FLASK_DEBUG=1
```

### URL Validation Configuration

The application includes a robust URL validation system introduced in version 1.0.1. You can customize the validation rules by editing the following constants in `app/blueprints/analysis.py`:

```python
# List of allowed top-level domains
ALLOWED_TLDS = [
    'com', 'org', 'net', 'gov', 'edu', 'mil', 'int', 'io', 'co',
    'uk', 'ca', 'au', 'eu', 'de', 'fr', 'jp', 'ru', 'cn', 'in',
    'br', 'mx', 'za', 'ch', 'se', 'no', 'dk', 'fi', 'nl', 'be'
]

# List of blocked domains (e.g., known malicious sites)
BLOCKED_DOMAINS = [
    'example-malicious-site.com',
    'known-phishing-domain.net'
    # Add more as needed
]
```

To enhance security:
1. Add known malicious domains to the `BLOCKED_DOMAINS` list
2. Restrict the `ALLOWED_TLDS` list to only necessary top-level domains
3. The validator enforces HTTP/HTTPS protocols only and rejects other schemes

## Available Models

The tool supports three OpenAI models with different price points and capabilities:

- **GPT-4o mini** ($0.15/1M tokens)
  - Quick analysis of news articles
  - Best for basic content analysis

- **GPT-4o** ($0.50/1M input, $1.50/1M output)
  - Detailed technical analysis
  - Good balance of speed and depth

- **GPT-4 Turbo** ($10/1M input, $30/1M output)
  - In-depth analysis of complex reports
  - Best for critical assessments

## Running the Application

Start the Flask server:
```bash
python run.py
```

Open `http://localhost:8000` in your browser

## Usage

1. Enter a URL to analyze
2. Select your preferred OpenAI model
3. View the structured analysis results, including:
   - Article summary
   - Source evaluation
   - MITRE ATT&CK techniques
   - Threat actors identified
   - Critical infrastructure sector relevance
4. Export the analysis in your preferred format (JSON, CSV, PDF, or Markdown) using the download button in the analysis results

## Development Status

This project is a work-in-progress, and many features are still being refined. The code is shared in its current state to demonstrate the concept and gather feedback. Please review the Known Issues document for a list of identified issues. If you like this project, consider buying me a coffee!

<div align="center">
  <div align="center">
    <a href="#development-status">
      <img src="https://img.shields.io/badge/Status-Active_Development-BC8F8F?style=for-the-badge" alt="Active Development" />
    </a>
  </div>
  <p>
  <div align="center">
    <a href="https://buymeacoffee.com/centerforcyberintel" target="_blank">
      <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" >
    </a>
  </div>
</div>

## Database Structure

The application uses SQLite for data storage with the following schema design:

### Tables

1. **articles** - Stores metadata about analyzed articles
   - `id`: INTEGER PRIMARY KEY - Unique identifier
   - `url`: TEXT UNIQUE - The URL of the analyzed article
   - `title`: TEXT - The title of the article
   - `content_length`: INTEGER - Length of the extracted content
   - `extraction_time`: REAL - Time taken to extract content (seconds)
   - `analysis_time`: REAL - Time taken to analyze content (seconds)
   - `model`: TEXT - The OpenAI model used for analysis
   - `created_at`: TIMESTAMP - When the analysis was created

2. **analysis_results** - Stores the actual analysis content
   - `id`: INTEGER PRIMARY KEY - Unique identifier
   - `article_id`: INTEGER - Foreign key to articles table
   - `raw_text`: TEXT - Raw text response from the AI
   - `structured_data`: TEXT - JSON-formatted structured analysis

3. **token_usage** - Tracks OpenAI API token usage
   - `id`: INTEGER PRIMARY KEY - Unique identifier
   - `model`: TEXT - The model used
   - `input_tokens`: INTEGER - Number of input tokens
   - `output_tokens`: INTEGER - Number of output tokens
   - `cached`: BOOLEAN - Whether the result was cached
   - `timestamp`: TIMESTAMP - When the tokens were used

4. **indicators** - Stores extracted indicators of compromise
   - `id`: INTEGER PRIMARY KEY - Unique identifier
   - `article_id`: INTEGER - Foreign key to articles table
   - `indicator_type`: TEXT - Type of indicator (ipv4, domain, etc.)
   - `value`: TEXT - The actual indicator value
   - `created_at`: TIMESTAMP - When the indicator was extracted

### Database Functions

The application includes several helper functions for database operations:

- `get_db_connection()`: Context manager for secure database connections
- `execute_query()`: Safe execution of parameterized SQL queries
- `init_db()`: Initialize the database schema if it doesn't exist
- `store_analysis()`: Store new analysis results
- `update_analysis()`: Update existing analysis results
- `get_analysis_by_url()`: Retrieve analysis by article URL
- `get_recent_analyses()`: Get the most recent analyses
- `track_token_usage()`: Record OpenAI API token usage
- `get_token_usage_stats()`: Retrieve token usage statistics
- `store_indicators()`: Store extracted indicators
- `get_indicators_by_article_id()`: Get indicators for a specific article
- `get_indicators_by_url()`: Get indicators by article URL
- `get_indicator_stats()`: Get statistics about extracted indicators

All database operations use parameterized queries to prevent SQL injection and include proper error handling. The database is automatically initialized when the application starts.

## Security Notes

- Never commit `.env` or any files containing API keys
- Review `.gitignore` to ensure sensitive data is excluded
- Monitor token usage and costs
- All analyses should be validated by a qualified analyst
- Database operations use parameterized queries to prevent SQL injection attacks
- URL validation prevents malicious input and blocks potentially dangerous domains
- User inputs are sanitized to prevent cross-site scripting (XSS) attacks

## Testing

The project includes a comprehensive test suite using pytest. To run the tests:

1. Make sure you have the development dependencies installed:
   ```
   pip install -r requirements-dev.txt
   ```

2. Run the tests with coverage report:
   ```
   pytest
   ```
   
   This will run all tests and generate a coverage report. For more detailed options:
   ```
   # Run with verbose output
   pytest -v
   
   # Run specific test file
   pytest tests/test_article_analyzer.py
   
   # Run tests matching a pattern
   pytest -k "analyzer or extractor"
   
   # Generate HTML coverage report
   pytest --cov=app --cov-report=html
   ```

3. View test coverage:
   After running the tests with coverage, open `htmlcov/index.html` in your browser to see the detailed coverage report.

4. Test categories:
   The tests are organized by categories using pytest markers:
   ```
   # Run only unit tests
   pytest -m unit
   
   # Run only integration tests
   pytest -m integration
   
   # Run only database-related tests
   pytest -m database
   ```

## Disclaimer

This tool uses AI to analyze cybersecurity articles. Results may vary between analyses of the same content. While assessments are generally consistent, specific details, ratings, and identified techniques may differ. All analyses should be reviewed by a qualified analyst before making security decisions.

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).

- You are free to share and adapt this work for non-commercial purposes
- You must provide attribution to the [Center for Cyber Intelligence](https://www.centerforcyberintelligence.org)
- Commercial use is strictly prohibited without prior written consent

See the [LICENSE.md](LICENSE.md) file for full details.

Copyright © 2025 [Center for Cyber Intelligence](https://www.centerforcyberintelligence.org). All rights reserved.

