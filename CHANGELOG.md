# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-03-22

### Added
- Minor Update release of Artificial Cyber Intelligence Analyst™ with updates to core functionality:
  - Cybersecurity article analysis with OpenAI API integration
  - IoC and MITRE ATT&CK techniques extraction and identification
  - Database for storing and retrieving analyses
  - Export capabilities backend infrastructure in multiple formats (JSON, CSV, PDF, Markdown)
  - Interactive web interface with HTMX
  - Statistics dashboard for tracking usage
  - Settings management for API configuration
- Robust URL validation system:
  - URL format validation with validators package
  - TLD validation with configurable allowlist
  - Domain blocklist for security
  - Protocol validation (HTTP/HTTPS only)
- Database improvements:
  - Connection context manager for proper resource handling
  - Safe query execution helper function
  - Improved error logging for operations
- Custom Jinja2 filter 'zfill' for zero-padding strings in templates
- Model ID normalization system for different OpenAI model versions
- Comprehensive test suite with pytest
  - Unit tests for all major components
  - Integration tests for key workflows
  - Test fixtures for database, client, and API mocks
  - Code coverage reporting
  - Categorized tests with pytest markers
- Configuration file (pytest.ini) for test settings
- Frontend implementation for exporting analysis results in multiple formats:
  - Export dropdown menu in the analysis results UI
  - Support for JSON, CSV, PDF, and Markdown exports
  - Export routes in the analysis blueprint 
- TODO.md file with roadmap for future features and improvements
- Database Structure documentation in README.md for developers

#### Security Updates
- Input sanitization and validation:
  - URL parameter validation to prevent injection attacks
  - HTML escaping to prevent XSS attacks
  - Model selection and parameter sanitization
- Database protections:
  - Parameterized queries to prevent SQL injection
  - Improved connection management and transaction handling
  - Enhanced error handling and logging
- Domain security:
  - Blocklist to prevent requests to known malicious sites
  - Protocol validation to prevent non-HTTP/HTTPS schemes

### Changed
- Renamed project from "ThreatInsight Analyzer" to "Artificial Cyber Intelligence Analyst™"
- Updated all references in documentation, templates, and code
- Updated UI elements to reflect the new name

### Fixed
- Template rendering issues:
  - MITRE ATT&CK technique display for sub-techniques
  - Token stats display edge cases
- Application stability:
  - Statistics page errors related to model version discrepancies
  - Application crash caused by incorrect module import
  - Database connection and transaction handling
- Test improvements:
  - Statistics blueprint tests with variable name alignment
  - Indicator extractor tests using public API functions
  - Logger module tests for better coverage
  - Hash type expectations in indicator extraction
  - Text extraction whitespace handling
  - CVE identifier case handling