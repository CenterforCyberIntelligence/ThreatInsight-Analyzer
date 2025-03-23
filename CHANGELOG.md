# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-03-22

### Added
- New fields to threat intelligence analysis:
  - Threat actors identification with confidence levels and aliases
  - Intelligence gaps section to highlight missing information
  - More comprehensive critical infrastructure sector assessment
- Enhanced error handling for API responses:
  - Specific handling for refusals
  - Detection of content filter triggers
  - Better handling of token limit issues
  - Graceful fallbacks for incomplete responses
- Improved user interface for error handling:
  - Detailed error messages with error-specific suggestions
  - Retry option for failed analyses
  - Technical details display for debugging
- Comprehensive error handling for frontend display of backend errors
- Improved error feedback with specific suggestions based on error type
- Retry functionality directly from error screens to improve user experience
- Enhanced debugging in error handlers to better trace issues

### Changed
- Major refactoring to use OpenAI's structured JSON responses:
  - Replaced regex-based parsing with direct JSON structure
  - Updated system prompt to request properly formatted JSON
  - Enhanced response validation and error handling for JSON parsing
  - Improved robustness by adding fallback defaults for missing fields
  - **Upgraded to the newer OpenAI Responses API** with JSON Schema validation
  - Implemented strict schema validation for more consistent outputs
  - Fixed API parameter naming from `max_tokens` to `max_output_tokens`
  - Removed unsupported `seed` parameter from API calls
  - Added required `additionalProperties: false` to JSON schema objects
- Updated display templates to show new analysis fields:
  - Added threat actors table with confidence levels
  - Added intelligence gaps section
  - Reformatted critical sectors display
- Enhanced export functionality:
  - CSV exports now include all structured data fields
  - Markdown exports now use tables for better formatting of sectors and threat actors
- Fixed JSON schema validation by adding 'threat_actors' to the required properties array
- Improved error template with better visuals and more helpful suggestions
- Enhanced error display with types, titles, and user-friendly messages
- Updated retry button to use POST method consistent with the main form
- Fixed JSON schema validation by removing unsupported 'minimum' and 'maximum' properties
- Enhanced HTMX error handling with event handlers to properly display backend errors
- Made error handling consistent across all routes with proper error typing
- Fixed parameter mismatch in store_analysis function call

### Removed
- Legacy text parsing functions no longer needed with structured JSON responses
- Redundant extraction code for MITRE techniques and other fields
- Deprecated `chat.completions.create` API calls in favor of `responses.create`

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

## [Unreleased]

### Added
- Project name changed to "Artificial Cyber Intelligence Analyst"
- Updates to documentation files and UI elements to reflect the new project name 
- Added TODO.md with roadmap for upcoming features and improvements
- Updated Database Structure documentation in the README.md for developers

### Fixed
- Fixed statistics page error when encountering models not defined in the model_prices dictionary
- Added proper error handling for price calculations in templates
- Enhanced model normalization to better handle various model versions
- Added pricing for gpt-3.5-turbo model