# ThreatInsight Analyzer 
[![Version: 1.0.0](https://img.shields.io/badge/Version-1.0.0-brightgreen.svg)](https://github.com/yourusername/threatinsight-analyzer)
[![AI Development Project](https://img.shields.io/badge/🤖_AI_Development-Project-blue.svg)](https://github.com/yourusername/threatinsight-analyzer)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC_BY--NC_4.0-lightgrey.svg)](LICENSE.md)

A web-based tool that uses AI to aid in rapid summarization and analysis of cybersecurity articles to generate structured threat intelligence insights.

## Current Status

> **IMPORTANT NOTICE**: This is a ✨ vibe-coding ✨ project I started because I wanted a rapid way to summarize and extract critical intelligence information from articles I read on the internet. Because I am not a developer by trade, and I am heavily relying on AI Agents to support my develoment of this platform, bugs and issues are expected. Use at your own risk and enjoy the process. If you have suggestions on how to improve the project, please let me know!

<div align="center">
  <a href="#features">
    <img src="https://img.shields.io/badge/AI_Powered-Analysis-8B7355?style=for-the-badge" alt="AI Powered" />
  </a>
  &nbsp;&nbsp;
  <a href="#available-models">
    <img src="https://img.shields.io/badge/OpenAI-Integration-5F9EA0?style=for-the-badge" alt="OpenAI Integration" />
  </a>
  &nbsp;&nbsp;
  <a href="#development-status">
    <img src="https://img.shields.io/badge/Status-Active_Development-BC8F8F?style=for-the-badge" alt="Active Development" />
  </a>
</div>

This project is in active development. Features are being implemented incrementally, and the codebase is evolving. Known issues are documented in the [Known Issues](Known%20Issues.md) file.

## Release Information

- **Version:** 1.0.0
- **Release Date:** 2024
- **Developed with:** AI-assisted coding (Claude, GPT-4)

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

## Features

- AI-powered article analysis using OpenAI models
- Automatic extraction of article content from URLs
- Structured analysis including:
  - Article summary
  - Source credibility assessment
  - MITRE ATT&CK technique identification
  - Key threat intelligence insights
  - Bias detection
  - Critical infrastructure sector relevance scoring
- Token usage tracking and cost estimation
- Analysis caching for quick retrieval
- Support for multiple AI models with different capabilities

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

## Development Status

This project is a work-in-progress, and many features are still being refined. The code is shared in its current state to demonstrate the concept and gather feedback. Please review the Known Issues document for a list of identified issues.

## Security Notes

- Never commit `.env` or any files containing API keys
- Review `.gitignore` to ensure sensitive data is excluded
- Monitor token usage and costs
- All analyses should be validated by a qualified analyst

## Disclaimer

This tool uses AI to analyze cybersecurity articles. Results may vary between analyses of the same content. While assessments are generally consistent, specific details, ratings, and identified techniques may differ. All analyses should be reviewed by a qualified analyst before making security decisions.

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).

- You are free to share and adapt this work for non-commercial purposes
- You must provide attribution to the [Center for Cyber Intelligence](https://www.centerforcyberintelligence.org)
- Commercial use is strictly prohibited without prior written consent

See the [LICENSE.md](LICENSE.md) file for full details.

Copyright © 2025 [Center for Cyber Intelligence](https://www.centerforcyberintelligence.org). All rights reserved.