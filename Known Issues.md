# Known Issues

> This document contains known issues in the codebase identified with the assistance of an AI agent. I'm aware of these issues and plan to address them in future development iterations.

## Active Issues

### Critical Issues

| Issue | File | Description |
|-------|------|-------------|
| 🔴 **XSS Vulnerabilities in Templates** | `templates/partials/analysis_result.html` | Potential cross-site scripting vulnerabilities where unfiltered content is rendered in templates using the `\|safe` filter. This could allow malicious content to be executed in users' browsers. |
| 🔴 **OpenAI API Integration Issues** | Various | Multiple test failures due to `AttributeError: module 'openai.resources.chat.completions' has no attribute 'ChatCompletions'`. Core analysis functionality is broken. |
| 🔴 **Missing Routes** | Various | Route tests failing with 404 errors. Core application navigation is broken. |
| 🔴 **Database Model Changes** | Various | Mismatches in database field names and expected data structures causing test failures. |

### High Priority Issues

| Issue | File | Description |
|-------|------|-------------|
| 🟠 **Potential SQL Injection in Database Operations** | `app/blueprints/settings.py` | The `purge_database()` function uses direct SQL execution without parameterized queries, which could lead to SQL injection vulnerabilities if modified in the future. |
| 🟠 **Synchronous OpenAI API Calls** | `app/utilities/article_analyzer.py` | API calls to OpenAI are made synchronously, blocking the request thread and impacting user experience for longer operations. Asynchronous processing with async/await or a task queue is needed. |
| 🟠 **Inefficient Article Extraction** | `app/utilities/article_extractor.py` | The current article extraction process tries multiple methods sequentially, which is slow and inefficient. Parallel extraction attempts, caching, and refined extraction algorithms would improve performance. |
| 🟠 **SQLite for Production Use** | `app/config/config.py` | Using SQLite for production may not scale well. Consider migrating to a more robust database like PostgreSQL and implementing proper connection pooling. |
| 🟠 **PDF Export Issues** | Export functionality | Users cannot view exported PDF analyses in Adobe Acrobat as the current PDF export implementation creates a text file with a .pdf extension instead of a properly formatted PDF file. |
| 🟠 **Missing Environment Variable Handling** | Settings blueprint | Missing `update_env_file` function in settings blueprint preventing configuration updates through UI. |
| 🟠 **Analysis Workflow Tests Failing** | Analysis blueprint | Multiple failures in the analysis blueprint tests affecting core functionality. |
| 🟠 **Helper Function Inconsistencies** | Various utility functions | Functions like `format_timestamp`, `generate_slug`, `sanitize_filename` returning different values than expected. |

### Medium Priority Issues

| Issue | File | Description |
|-------|------|-------------|
| 🟡 **Migration Process for Large Databases** | `app/models/database.py` | While the database migration system works well for smaller databases, additional considerations are needed for very large databases, including batch processing, progress indicators, and pause/resume functionality. |
| 🟡 **Backup Before Migration** | `app/models/database.py` | The current migration system doesn't automatically create backups before migration. Implementation of automatic database backup, restore options, and backup verification is needed. |
| 🟡 **Insufficient Error Logging** | `app/utilities/logger.py` | The current logging implementation doesn't consistently capture context or stack traces. Enhancements are needed to include more context, request IDs, and potentially structured logging. |
| 🟡 **Modal Refresh Confirmation Needs Improvement** | `templates/partials/analysis_result.html` | The refresh confirmation modal lacks clear feedback and error handling states. Proper error states, improved loading animations, and timeout handling are needed. |
| 🟡 **Inconsistent UI Element Styling** | `static/css/styles.css` | The CSS has inconsistent naming patterns and potential specificity issues. Standardizing CSS naming conventions, reviewing CSS specificity, and possibly implementing a CSS preprocessor would improve maintainability. |
| 🟡 **Missing Extraction Fallbacks** | `app/utilities/article_extractor.py` | Content extraction fails with "content too short" errors in several cases. More robust fallback mechanisms, support for different website types, and improved error handling are needed. |
| 🟡 **Duplicate Date Formatting Logic** | `app/blueprints/main.py`, `app/blueprints/statistics.py` | Nearly identical code to convert string timestamps to datetime objects exists in multiple files, creating maintenance issues. |
| 🟡 **Duplicate Model Price Normalization Logic** | `app/blueprints/statistics.py` | The same model price normalization logic is duplicated in both the `statistics()` and `refresh_statistics()` functions, increasing the risk of inconsistencies. |
| 🟡 **Complex Environment Variable Processing** | `app/blueprints/settings.py` | The environment variable update function uses a complex approach to update the .env file and lacks comprehensive validation. |
| 🟡 **Hardcoded Default Values** | `app/blueprints/analysis.py` | Default blocked domains are hardcoded when the block list can't be loaded, making maintenance difficult as blocked domains need to be updated. |
| 🟡 **Remaining Embedded Styles** | `templates/partials/analysis_loading.html`, `templates/statistics.html` | Despite efforts to consolidate CSS, there are still embedded styles in these templates, making style maintenance more difficult and inconsistent. |
| 🟡 **Inconsistent Modal Dialog Implementation** | Various template files | Different approaches to modal dialogs across templates make the codebase harder to maintain and result in inconsistent user experience. |
| 🟡 **Direct DOM Style Manipulation** | `templates/partials/analysis_result.html` | JavaScript code directly manipulates DOM element styles instead of toggling CSS classes, creating tight coupling between JS and styling. |
| 🟡 **Indicator Extractor Test Expectations** | Test files | Indicator extractor tests expect a combined 'hash' key for hash indicators, but implementation separates by type (md5, sha1, sha256). |
| 🟡 **Error Handler Tests Failing** | Error handler | Custom error pages not working as expected, leading to poor user experience when errors occur. |
| 🟡 **Export Functionality Partially Implemented** | Export functionality | PDF format exports are not properly formatted and cannot be opened in Adobe Acrobat. |
| 🟡 **View Button for Individual Reports on History Page** | `history.html` | When clicking on the "View" button for any report on the history page, the user is simply redirected back to the home page, rather than being shown the requested report. |

### Low Priority Issues

| Issue | File | Description |
|-------|------|-------------|
| 🟢 **CVE Identifier Case Handling** | Test files | CVE identifier case handling in tests doesn't match implementation behavior. |
| 🟢 **Whitespace Handling in Text Cleaning Function** | Text processing | The `clean_extracted_text` function behavior with whitespace doesn't match test expectations. |
| 🟢 **Contact Form Validation Discrepancies** | Contact form | Tests expect 400 responses for invalid data but receiving 404. |
| 🟢 **Text Truncation Inconsistencies** | Text utilities | Inconsistent truncation behavior with ellipsis causing minor display issues. |
| 🟢 **History Page UI/UX** | `history.html` | Poor page formatting. |

### Partially Resolved Issues

| Issue | File | Current Status | Remaining Work |
|-------|------|----------------|----------------|
| ⚠️ **Insecure Debug Endpoint** | `app/blueprints/analysis.py` | Environment checks, basic token authentication, and audit logging have been added | Implement proper role-based access control, consider removing the endpoint entirely in favor of proper logging, add rate limiting to prevent abuse |
| ⚠️ **Inconsistent Error Handling** | Various | Improved error handling in article_analyzer.py with better retry logic, enhanced error reporting for API operations, added self-validation for structured data, improved database error handling | Create custom exception classes for different error types, implement global error handling middleware |

## Resolved Issues

### Security Issues

| Issue | File | Resolution | Changelog Reference |
|-------|------|------------|---------------------|
| ✅ **Lack of Input Validation** | `app/blueprints/analysis.py` | Added validators library for URL format validation, implemented allowed domain patterns, TLD validation, domain blocklist capability, protocol validation, and input sanitization. | [1.0.0 Security Updates](CHANGELOG.md#100---2025-02-15) |
| ✅ **Unsafe SQL Queries** | `app/models/database.py` | Created a database connection context manager, standardized parameterized queries, added centralized error handling and logging, implemented proper transaction management, and added a safe query execution utility function. | [1.0.0 Security Updates](CHANGELOG.md#100---2025-02-15) |
| ✅ **URL Validation Logic for Complex Domains** | URL handling | Enhanced URL validation logic to detect IP patterns in domains and improved TLD validation to handle complex domain structures. | [1.0.0 Security Updates](CHANGELOG.md#100---2025-02-15) |

### Performance Issues

| Issue | File | Resolution | Changelog Reference |
|-------|------|------------|---------------------|
| ✅ **Inefficient Token Usage Calculation** | `app/models/database.py` | Optimized database schema, created indexes for performance-critical columns, improved token tracking functionality, enhanced query performance, and implemented proper context manager for database connections. | [1.0.0 Fixed](CHANGELOG.md#100---2025-02-15) |
| ✅ **Duplicate Shutdown Handlers** | `app/__init__.py`, `app/utilities/logger.py` | Fixed duplicate signal handler registrations, ensured the shutdown handler is only registered once, updated the registration function, and eliminated duplicate log messages. | [1.0.0 Fixed](CHANGELOG.md#100---2025-02-15) |
| ✅ **Duplicate Initialization in Debug Mode** | `app/__init__.py`, `app/utilities/logger.py` | Added detection of Flask reloader vs worker processes, implemented skipping full initialization in the reloader process, added special handling for logger initialization, and created a dedicated debug server start function. | [1.0.0 Fixed](CHANGELOG.md#100---2025-02-15) |
| ✅ **CTRL+C Termination Issues** | `app/__init__.py`, `app/utilities/logger.py` | Enhanced signal handling for SIGINT, added special handling for Flask debug mode, implemented mechanisms to prevent duplicate shutdown messages, added proper cleanup in the shutdown sequence, and used appropriate sys.exit() calls. | [1.0.0 Fixed](CHANGELOG.md#100---2025-02-15) |

### Database Issues

| Issue | File | Resolution | Changelog Reference |
|-------|------|------------|---------------------|
| ✅ **Lack of Database Migrations** | Database functionality | Added proper database version tracking table, implemented structured migration system, created migration functions that preserve existing data, added automatic migration during startup, and improved error handling and logging. | [1.0.0 Fixed](CHANGELOG.md#100---2025-02-15) |
| ✅ **Type Mismatch Errors in Database** | `logs/error.log` | Standardized database column types, added proper validation before storing data, fixed queries causing type mismatches, implemented more robust error handling, and added data validation functions. | [1.0.0 Fixed](CHANGELOG.md#100---2025-02-15) |
| ✅ **Database Function Parameter Mismatch** | Database functions | Updated parameter names in function calls to match the expected parameter names in the implementation. | [1.1.0 Fixed](CHANGELOG.md#110---2025-03-23) |
| ✅ **History Page Database Query Issue** | `app/models/database.py` | Fixed get_recent_analyses function to properly handle None values for the limit parameter by modifying the SQL query to not include a LIMIT clause when limit is None. | [1.1.0 Fixed](CHANGELOG.md#110---2025-03-23) |
| ✅ **Frontend UI Issues After Schema Migration** | HTML templates | Updated all HTML templates to reference the new data structure correctly, fixed conditional checks for data existence, improved error message displays, and fixed presentation of various data components. | [1.0.0 Fixed](CHANGELOG.md#100---2025-02-15) |

### Configuration Issues

| Issue | File | Resolution | Changelog Reference |
|-------|------|------------|---------------------|
| ✅ **Inconsistent Environment Variable Usage** | `app/config/config.py` | Reorganized Config class with logical section headers, standardized environment variable naming and usage patterns, added comprehensive documentation, created detailed configuration section in README.md, and improved error handling. | [1.1.0 Changed](CHANGELOG.md#110---2025-03-23) |

### UI/UX Issues

| Issue | File | Resolution | Changelog Reference |
|-------|------|------------|---------------------|
| ✅ **Template Rendering Error in IOC Display** | `templates/partials/analysis_result.html` | Added custom Jinja2 filter 'zfill' to pad strings with zeros, updated template to correctly use the filter for MITRE technique IDs, and fixed rendering issues. | [1.0.0 Fixed](CHANGELOG.md#100---2025-02-15) |
| ✅ **Inconsistent Header and Footer** | `templates/*.html` | Standardized header and footer structure, updated templates to use consistent Bootstrap components and classes, aligned Bootstrap versions, and ensured consistent icon usage. | [1.1.0 Changed](CHANGELOG.md#110---2025-03-23) |
| ✅ **Statistics Page Refresh Error** | `app/blueprints/statistics.py` | Updated the refresh function to handle model field naming correctly, fixed SQL queries, added consistent error handling, and enhanced the UI with proper loading indicators. | [1.1.0 Changed](CHANGELOG.md#110---2025-03-23) |
| ✅ **Inaccessible History Page** | `templates/*.html` | Added History links to navigation menus, ensured consistent navigation structure, activated the History blueprint, and updated all templates to include History in navigation and footer links. | [1.1.0 Changed](CHANGELOG.md#110---2025-03-23) |
| ✅ **Missing Template Variables Error** | `templates/partials/analysis_result.html` | Added null-safety checks to template variables, updated template rendering functions to consistently pass required variables, and fixed template rendering to handle undefined values. | [1.1.0 Fixed](CHANGELOG.md#110---2025-03-23) |
| ✅ **Inconsistent CSS Styling Approach** | Various HTML templates | Moved all inline styles to the central stylesheet, removed embedded style tags, created semantic class names, added CSS best practices guidelines, and improved maintainability through centralized style definitions. | [1.1.0 Changed](CHANGELOG.md#110---2025-03-23) |
| ✅ **Inconsistent Error Display UI** | Error templates | Standardized all error displays to use the same modal popup style for consistent user experience. | [1.1.0 Fixed](CHANGELOG.md#110---2025-03-23) |

### API Integration Issues

| Issue | File | Resolution | Changelog Reference |
|-------|------|------------|---------------------|
| ✅ **Text Parsing Reliability with Complex Formats** | API integration | Implemented OpenAI's structured JSON responses feature, eliminating the need for regex-based parsing. | [1.1.0 Changed](CHANGELOG.md#110---2025-03-23) |
| ✅ **OpenAI Structured Outputs API Parameter Mismatch** | API calls | Updated API calls to use the correct parameter names (max_output_tokens instead of max_tokens). | [1.1.0 Fixed](CHANGELOG.md#110---2025-03-23) |
| ✅ **OpenAI Structured Outputs API Seed Parameter Issue** | API calls | Removed the unsupported seed parameter from API calls. | [1.1.0 Fixed](CHANGELOG.md#110---2025-03-23) |
| ✅ **OpenAI Structured Outputs JSON Schema Issues** | API schema | Added required properties to the JSON schema and fixed syntax errors between JavaScript and Python boolean values. | [1.1.0 Fixed](CHANGELOG.md#110---2025-03-23) |
| ✅ **Backend Error Handling Improvement** | Error handling | Enhanced error handling UI with more detailed error messages, error-specific suggestions, and retry options. | [1.1.0 Fixed](CHANGELOG.md#110---2025-03-23) |
| ✅ **Server Error Display Enhancement** | Error handling | Added a custom Flask error handler for 500 errors that renders a helpful error template with error information and retry options. | [1.1.0 Fixed](CHANGELOG.md#110---2025-03-23) |

## Issue vs. TODO Clarification

This document focuses on **issues** (bugs, vulnerabilities, and problems with existing functionality) while the [TODO.md](TODO.md) document tracks **feature enhancements** and future development plans. Some items may appear similar but serve different purposes:

- **Issues**: Problems with existing code that need to be fixed
- **TODOs**: New features or enhancements that would improve the application

For example, "PDF Export Issues" in this document refers to a bug where the current PDF export feature doesn't work correctly, while the "Fix PDF generation implementation" in TODO.md refers to the enhancement task to implement a fully-featured PDF export capability.