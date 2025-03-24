# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - TBD

### Added
- Comprehensive documentation for all utility modules:
  - Detailed module descriptions explaining purpose and key features
  - Enhanced function docstrings with complete parameter explanations
  - Return value documentation for all functions
  - Improved internal code comments for complex logic
  - Class documentation for custom formatter classes

### Changed
- Standardized docstring format across the codebase
- Clarified parameter and return value descriptions
- Added usage context to function documentation

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
