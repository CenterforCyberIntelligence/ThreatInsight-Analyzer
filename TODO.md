# TODO List

This document outlines planned features and improvements for future releases of the Artificial Cyber Intelligence Analyst.

## Planned Features

### Frontend Implementation for Existing Backend Features
- [ ] Frontend for enhanced search capabilities:
  - [ ] Add search interface for finding analyses by reliability level
  - [ ] Create UI for searching by threat actor mentions
  - [ ] Implement critical infrastructure sector impact filtering
  - [ ] Add advanced search combination options (e.g., high reliability + specific threat actor)

- [ ] Threat actor analytics dashboard:
  - [ ] Implement visualization for top threat actors across all analyses
  - [ ] Create threat actor detail pages with associated analyses
  - [ ] Add timeline view of threat actor appearances

- [ ] Database administration tools:
  - [ ] Create admin interface for database migration management
  - [ ] Add database version information to settings page
  - [ ] Implement database backup feature before migrations

- [ ] Optimized UI for denormalized data:
  - [ ] Update templates to utilize new database structure for faster loading
  - [ ] Add filtering capabilities based on optimized fields
  - [ ] Implement real-time analysis sorting by various metrics

### Security Enhancements
- [x] Enhanced URL validation and filtering:
  - [x] Add support for domain blocking
  - [x] Implement proper URL sanitization and validation
  - [x] Add more robust error handling for malformed URLs

- [ ] Enhanced blocked domains management:
  - [ ] Create a database table to store blocked domains
  - [ ] Implement a UI in the settings page for managing blocked domains
  - [ ] Add ability for users to add, remove, and categorize blocked domains
  - [ ] Implement import/export of blocklists from common formats
  - [ ] Add option for automatic blocklist updates from trusted sources
  - [ ] Add option to block TLDs

- [ ] Debug endpoint security:
  - [x] Add authentication for debug endpoints
  - [x] Implement environment-based feature flags to disable debug endpoints in production
  - [ ] Create an admin dashboard for debug tools with proper security controls
  - [ ] Implement comprehensive logging for all debug endpoint usage

### Export Enhancements
- [x] Support for additional export formats:
  - [x] JSON export with proper formatting
  - [ ] HTML export with proper styling and formatting
  - [ ] STIX 2.1 format for threat intelligence sharing
  - [ ] Custom templating options for exports

- [ ] **Critical Priority** - Fix PDF generation implementation:
  - [ ] Replace current placeholder implementation with proper PDF generation
  - [ ] Add WeasyPrint or ReportLab dependency for converting HTML/Markdown to PDF
  - [ ] Create proper PDF templates with headers, footers, and styling
  - [ ] Add metadata support (title, author, creation date, etc.)
  - [ ] Implement proper error handling for PDF generation failures
  - [ ] Add PDF generation progress indicators
  - [ ] Create PDF file size optimization options
  - [ ] Add support for embedding images and charts in PDF exports
  - [ ] Implement templating system for customized PDF layouts

### IOC Analysis
- [ ] Enhanced Indicator of Compromise (IOC) analysis:
  - [ ] Automatic reputation checking of extracted IOCs
  - [ ] Historical tracking of IOCs across multiple articles
  - [ ] Relationship mapping between IOCs
  - [ ] Confidence scoring for extracted IOCs
  - [ ] Automatic enrichment from external sources

### Threat Actor Analysis
- [x] Comprehensive threat actor identification:
  - [x] Threat actor attribution with basic details
  - [x] Improved confidence in threat actor identification
  - [ ] Campaign tracking and correlation
  - [ ] Associated CVE tracking and analysis
  - [ ] TTPs (Tactics, Techniques, and Procedures) mapping
  - [ ] Historical activity timeline generation

### IOC Feed Integration
- [ ] Support for external IOC feeds:
  - [ ] STIX/TAXII feed consumption
  - [ ] CSV feed import
  - [ ] JSON feed import
  - [ ] Automatic feed refreshing on schedule
  - [ ] Feed correlation with analyzed articles
  - [ ] Custom feed creation from analyzed articles

### UI/UX Improvements
- [ ] Dark mode support
- [ ] Custom dashboard layouts
- [x] Saved search functionality (partial)
- [ ] Enhanced Search: Find analyses by reliability level, threat actor, or affected critical sector
- [ ] Database Migration System**: Automatic database schema updates with data preservation
- [ ] Batch analysis of multiple articles
- [ ] Enhanced visualization of article relationships

### CSS Styling Enhancements
- [ ] Complete consolidation of inline and embedded styles:
  - [ ] Refactor JavaScript DOM manipulation styles to use CSS classes
  - [ ] Move remaining embedded styles from templates/settings.html to central stylesheet
  - [ ] Move remaining embedded styles from templates/statistics.html to central stylesheet
  - [ ] Move remaining embedded styles from templates/partials/analysis_loading.html to central stylesheet
  - [ ] Fix toast notification styling to use predefined CSS classes instead of inline styles
  - [ ] Create proper modal styling classes to avoid direct style property manipulation

- [ ] CSS organization and structure improvements:
  - [ ] Implement comprehensive BEM or SMACSS methodology for class naming
  - [ ] Create logical section organization in the stylesheet
  - [ ] Reduce CSS specificity issues with proper selector hierarchy
  - [ ] Add detailed documentation for component styling

- [ ] Styling consistency issues:
  - [ ] Standardize all button styles across the application
  - [ ] Create consistent spacing and alignment system
  - [ ] Standardize card styling and hover effects
  - [ ] Implement consistent loading indicator styling
  - [ ] Fix inconsistent modal dialog styling across the application

- [ ] Performance optimizations:
  - [ ] Audit and eliminate unused CSS
  - [ ] Optimize CSS selector performance
  - [ ] Minimize CSS specificity conflicts
  - [ ] Implement CSS minification in production

- [ ] Accessibility improvements:
  - [ ] Ensure proper color contrast for all text elements
  - [ ] Add focus styles for keyboard navigation
  - [ ] Improve responsive design for mobile devices
  - [ ] Fix text sizing and scaling issues

### Code Cleanup and Refactoring
- [ ] Remove duplicate functionality:
  - [ ] **Medium Priority** - Centralize date formatting logic (app/blueprints/main.py:15-21, app/blueprints/statistics.py:58-65)
  - [x] **Medium Priority** - Eliminate duplicate model price normalization (app/blueprints/statistics.py:28-47, 72-91)
  - [ ] **Low Priority** - Standardize loading indicator implementations (templates/statistics.html:167-220, partials/analysis_loading.html:60-68)

- [ ] Address security vulnerabilities:
  - [ ] **High Priority** - Replace direct SQL execution with parameterized queries (app/blueprints/settings.py:113-126)
  - [x] **High Priority** - Review error handling in API interactions (app/utilities/article_analyzer.py:85-108)
  - [x] **Medium Priority** - Audit debug endpoints for production security (app/blueprints/analysis.py:378-432)

- [ ] Improve code maintainability:
  - [ ] **Medium Priority** - Create centralized helper functions for common operations
  - [ ] **Medium Priority** - Replace inline JavaScript DOM style manipulation with CSS classes (analysis_result.html:787-797)
  - [x] **Medium Priority** - Refactor environment variable processing for robustness (app/blueprints/settings.py:76-126)
  - [x] **Medium Priority** - Replace hardcoded default values with configuration options (app/blueprints/analysis.py:51-52)

- [x] Finish OpenAI structured output implementation:
  - [x] **High Priority** - Complete migration to the newer `client.responses.create()` API 
  - [x] **High Priority** - Add robust error handling for content filters, token limits, and refusals
  - [x] **Medium Priority** - Improve schema validation for more consistent output

### Performance & Scalability
- [ ] Implement caching for frequently accessed data
- [ ] Optimize database queries for large datasets
- [ ] Add support for alternative database backends (PostgreSQL, MySQL)
- [ ] Implement proper pagination for large result sets

### API Development
- [ ] RESTful API for programmatic access to:
  - [ ] Submit URLs for analysis
  - [ ] Retrieve analysis results
  - [ ] Export in various formats
  - [ ] Search and filter results
  - [ ] Manage settings and configurations

### Abuse Prevention & API Cost Management
- [ ] Implement rate limiting:
  - [ ] Add per-IP request rate limiting (e.g., 10 requests per hour)
  - [ ] Implement exponential backoff for repeated requests
  - [ ] Add per-domain rate limiting to prevent mass analysis of a single site
  - [ ] Create custom rate limits for different operations (analysis vs. export)

- [ ] Add user authentication:
  - [ ] Implement basic user registration and login system
  - [ ] Create user-specific API usage quotas and limits
  - [ ] Add tiered access levels (free tier with strict limits, paid tiers with higher limits)
  - [ ] Implement OAuth/social login options for ease of use

- [ ] Add CAPTCHA and bot detection:
  - [ ] Implement reCAPTCHA or hCaptcha on the analysis form
  - [ ] Add browser fingerprinting to detect headless browsers and automation
  - [ ] Check for bot-like behavior patterns (rapid requests, unusual access patterns)
  - [ ] Add honeypot fields to detect automated form submission

- [ ] Content and request filtering:
  - [ ] Implement content length caps (to prevent extremely large articles from using excessive tokens)
  - [ ] Add domain whitelisting option for trusted sources only
  - [ ] Create caching policies based on content freshness (recent articles vs. older content)
  - [ ] Implement request deduplication to prevent identical analyses

- [ ] Usage monitoring and alerting:
  - [ ] Create a real-time dashboard for API usage and costs
  - [ ] Set up alerting for unusual usage patterns or cost spikes
  - [ ] Implement automatic temporary lockdown if usage exceeds predefined thresholds
  - [ ] Add detailed logging of all analysis requests for audit purposes

- [ ] Advanced techniques:
  - [ ] Implement token bucket algorithm for more sophisticated rate limiting
  - [ ] Add machine learning-based bot detection
  - [ ] Create a scoring system to prioritize valuable requests vs. potentially abusive ones
  - [ ] Add IP reputation checking against known proxy/VPN/TOR exit nodes

## Development Priorities

1. **Short-term (Next Release)**
   - Complete PDF export functionality
   - Implement HTML export
   - Enhance IOC extraction accuracy

2. **Medium-term**
   - Implement rate limiting and abuse prevention features
   - Complete the blocked domains management system
   - Add user authentication for multi-user support

3. **Long-term**
   - Complete threat intelligence platform features
   - Advanced visualization capabilities
   - Integration with other security tools 