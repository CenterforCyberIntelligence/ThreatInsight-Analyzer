# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2025-03-24

### Added
- New sanitize_input utility function for comprehensive input sanitization
- Unit tests for sanitization utilities
- HTTP 200 response check in URL validation process to verify URL accessibility before analysis

### Changed
- Standardized OpenAI API response handling across all models
- Enhanced error handling in analysis routes
- Improved token usage tracking consistency
- Updated test suite to focus on structured output validation

### Removed
- Outdated test cases for non-structured outputs
- Redundant error handling code

### Fixed
- Fixed error in main blueprint where `get_default_model()` method was being called but no longer exists
- Updated all blueprints to use `Config.DEFAULT_MODEL` instead of the removed `get_default_model()` method
- Ensured consistent model selection handling across all routes
- Inconsistent token usage tracking between response formats
- Schema validation issues in structured output handling
- Error recovery in analysis routes
- Test suite alignment with current model support
- Error modal styling issues in client-side validation
- Unified error modal appearance for both server-side and client-side validation errors
- Improved error modal rendering to ensure consistent display across all scenarios

### Security
- Implemented comprehensive input sanitization across all user inputs
- Added protection against XSS attacks via HTML entity encoding
- Improved URL parameter handling with proper decoding and sanitization
- Added NULL byte removal to prevent injection attacks
- Added HTTP security headers for enhanced application security
- Implemented a balanced Content Security Policy (CSP) configuration with monitoring capabilities
- Added CSP violation reporting endpoint to identify blocked resources without breaking functionality

## [1.1.0] - 2025-03-23

### Added
- Historical analysis browsing (partially implemented)
- Enhanced threat actor identification and critical infrastructure sector relevance scoring
- Raw JSON data access with download capability and improved filename generation
- Environment variable configuration support for database, logging, OpenAI parameters, and more
- Improved statistics dashboard for model usage and costs
- Multiple OpenAI model support with selection UI (partially implemented)
- Caching system for previously analyzed URLs with time indicators
- Bootstrap integration for improved UI components:
  - Loading animations and spinners
  - Modal dialogs and toast notifications
  - Responsive layouts and navigation
- Custom scrollbars and consistent navigation structure

### Changed
- Major refactoring to use OpenAI's structured JSON responses
- Enhanced UI for improved intelligence report readability
- Better MITRE ATT&CK techniques display layout
- Improved debugging capabilities with timestamps and detailed reporting
- Refactored Config class to use class attributes and standardized environment variables
- Migrated from custom CSS to Bootstrap 5.3 design system
- Consolidated most CSS styles into the central stylesheet removing inline styles
- Implemented consistent header and footer across all application pages
- Standardized model naming and structured output handling across the application
- Updated Config class to only include models that support structured outputs
- Simplified article analyzer to use only structured outputs
- Updated model selection UI to reflect supported models
- Removed legacy model support and non-structured output handling
- Updated tests to match new structured output format

### Fixed
- Source evaluation metrics calculation
- Error recovery for failed API calls
- History page display when using `limit=None`
- JSON handling improvements:
  - Robust error handling for parsing and formatting
  - Cross-browser clipboard operations (not fully tested)
  - Visual feedback for some operations
- Database configuration and environment variable usage
- Improvements to article extraction reliability for complex pages
- MITRE ATT&CK technique linking and display (known issues still exist with sub-techniques)
- UI issues:
  - Long URL and title display problems
  - Modal functionality
  - Button and badge styling consistency
  - Tab navigation in analysis display
  - Source evaluation data displays
  - Table styling and contrast
  - Template rendering for special cases
- Application stability issues with statistics, imports, and database connections
- Model detection logic for structured output support
- Response handling for different model types
- Test cases for structured output validation

### Security
- Input sanitization for URL parameters in debug endpoints (untested)
- Proper Content-Type headers for downloaded files (untested)
- Authentication and environment checks for debug endpoints
- Protection against SQL injection (untested)
- Domain security with blocklist for malicious sites (partially implemented)
- Protocol validation for URL schemes (untested)

### Technical Debt
- Resolved browser-specific clipboard implementation issues
- Improved error handling and visualization consistency
- Consolidated environment variable loading
- Standardized configuration parameter naming
- Documented remaining styling challenges and code duplication issues
- Eliminated redundant configuration code

## [1.0.0] - 2025-03-22

### Added
- Core functionality for analyzing cybersecurity articles via URL
- Integration with OpenAI API for threat intelligence analysis
- Source evaluation metrics (reliability, credibility)
- MITRE ATT&CK technique identification and linking
- Threat actor identification with confidence ratings
- Critical infrastructure sector relevance scoring
- Google Fonts integration with Rajdhani for headings
- "Support This Project" button in header navbar
- Cyber-themed styling with consistent header and footer
- Initial release
- Basic article analysis functionality
- Model selection interface
- Analysis results display
- History tracking
- Statistics page
- Settings management

### Security
- Input sanitization and validation for URLs and user inputs
- Database protections against SQL injection
- Domain security with blocklist for malicious sites

### Fixed
- Template rendering for MITRE ATT&CK techniques
- Token stats display edge cases
- Application stability issues
- UI improvements for consistent styling

### Changed
- Renamed project from "ThreatInsight Analyzer" to "Artificial Cyber Intelligence Analyst™"
- Updated all references in documentation, templates, and code
- Optimized UI for intelligence report readability
