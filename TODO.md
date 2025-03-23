# TODO List

This document outlines planned features and improvements for future releases of the Artificial Cyber Intelligence Analyst.

## Planned Features

### Export Enhancements
- [ ] Support for additional export formats:
  - [ ] HTML export with proper styling and formatting
  - [ ] STIX 2.1 format for threat intelligence sharing
  - [ ] Custom templating options for exports

### IOC Analysis
- [ ] Enhanced Indicator of Compromise (IOC) analysis:
  - [ ] Automatic reputation checking of extracted IOCs
  - [ ] Historical tracking of IOCs across multiple articles
  - [ ] Relationship mapping between IOCs
  - [ ] Confidence scoring for extracted IOCs
  - [ ] Automatic enrichment from external sources

### Threat Actor Analysis
- [ ] Comprehensive threat actor profiling:
  - [ ] Threat actor attribution confidence scoring
  - [ ] Associated IOCs tracking per threat actor
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
- [ ] Saved search functionality
- [ ] Batch analysis of multiple articles
- [ ] Enhanced visualization of article relationships

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

## Development Priorities

1. **Short-term (Next Release)**
   - Complete PDF export functionality
   - Implement HTML export
   - Enhance IOC extraction accuracy

2. **Medium-term**
   - Basic threat actor tracking
   - IOC feed integration
   - API framework implementation

3. **Long-term**
   - Complete threat intelligence platform features
   - Advanced visualization capabilities
   - Integration with other security tools 