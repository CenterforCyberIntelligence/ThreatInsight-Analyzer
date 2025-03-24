"""
Export Utilities Module
======================

This module provides functionality for exporting threat intelligence analysis results
in various file formats for sharing and storage purposes. It supports exporting data as:

- JSON: Raw structured data for machine processing or archiving
- CSV: Tabular data for spreadsheet applications
- Markdown: Human-readable formatted reports
- PDF: Publication-quality documents (placeholder functionality)

The export utilities handle proper formatting, filename generation with timestamps,
and organization of the analysis data for optimal presentation in each format.
These functions are used primarily by the report generation and download features
in the application's user interface.
"""
import os
import json
import csv
import tempfile
from typing import Dict, Any, Optional, List, Union
import datetime
from app.utilities.helpers import sanitize_filename

def get_export_filename(domain: Optional[str], format_type: str) -> str:
    """
    Generate a filename for exported analysis.
    
    Creates a sanitized filename incorporating the domain (if available), 
    current timestamp, and appropriate file extension based on the format type.
    The function ensures the filename is safe for all filesystems and not too long.
    
    Args:
        domain: Domain name from analyzed URL (e.g., 'example.com')
        format_type: Export format ('json', 'csv', 'pdf', or 'markdown')
        
    Returns:
        Sanitized filename with timestamp and appropriate extension
        (e.g., 'example_com_20230101_123045.json')
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not domain:
        base_name = f"analysis_{timestamp}"
    else:
        # Sanitize domain for filename
        safe_domain = sanitize_filename(domain)
        base_name = f"{safe_domain}_{timestamp}"
    
    # Map format to file extension
    extensions = {
        "json": "json",
        "csv": "csv",
        "pdf": "pdf",
        "markdown": "md"
    }
    
    extension = extensions.get(format_type.lower(), "txt")
    
    # Ensure filename isn't too long for filesystem
    max_length = 240  # Allow space for path and extension
    if len(base_name) > max_length:
        base_name = base_name[:max_length]
    
    return f"{base_name}.{extension}"

def export_analysis_as_json(
    analysis_data: Dict[str, Any], 
    domain: Optional[str] = None,
    file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Export analysis data as JSON.
    
    Saves the complete analysis data dictionary to a JSON file with proper
    indentation and Unicode support. This format preserves all the original
    data structure and is suitable for programmatic access or archiving.
    
    Args:
        analysis_data: Analysis data dictionary containing the complete analysis results
        domain: Domain name from analyzed URL (for filename generation if file_path not provided)
        file_path: Optional file path for export (if not provided, generates a temporary file)
        
    Returns:
        Dictionary with status information:
        - success: Boolean indicating if export was successful
        - file_path: Path to the exported file (if successful)
        - message: Human-readable status message
    """
    try:
        # Generate filename if not provided
        if not file_path:
            filename = get_export_filename(domain, "json")
            file_path = os.path.join(tempfile.gettempdir(), filename)
        
        # Write JSON to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "file_path": file_path,
            "message": "Analysis exported successfully as JSON"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error exporting analysis as JSON: {str(e)}"
        }

def export_analysis_as_csv(
    analysis_data: Dict[str, Any], 
    domain: Optional[str] = None,
    file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Export analysis data as CSV.
    
    Converts the hierarchical analysis data into a two-column CSV format
    with section headers and related data. This format is suitable for
    importing into spreadsheet applications and basic data analysis.
    
    Args:
        analysis_data: Analysis data dictionary containing the complete analysis results
        domain: Domain name from analyzed URL (for filename generation if file_path not provided)
        file_path: Optional file path for export (if not provided, generates a temporary file)
        
    Returns:
        Dictionary with status information:
        - success: Boolean indicating if export was successful
        - file_path: Path to the exported file (if successful)
        - message: Human-readable status message
    """
    try:
        # Generate filename if not provided
        if not file_path:
            filename = get_export_filename(domain, "csv")
            file_path = os.path.join(tempfile.gettempdir(), filename)
        
        # Extract structured data
        structured = analysis_data.get("structured", {})
        
        # Prepare rows for CSV
        rows = []
        
        # Basic metadata
        rows.append(["URL", analysis_data.get("url", "Not provided")])
        rows.append(["Analysis Date", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        rows.append(["Model Used", analysis_data.get("model", "Unknown")])
        rows.append([])  # Empty row as separator
        
        # Summary
        rows.append(["SUMMARY", structured.get("summary", "")])
        rows.append([])  # Empty row as separator
        
        # Source evaluation
        source_eval = structured.get("source_evaluation", {})
        rows.append(["SOURCE EVALUATION", ""])
        rows.append(["Reliability", 
                    f"{source_eval.get('reliability', {}).get('level', 'Unknown')} - " +
                    f"{source_eval.get('reliability', {}).get('justification', '')}"])
        rows.append(["Credibility", 
                    f"{source_eval.get('credibility', {}).get('level', 'Unknown')} - " +
                    f"{source_eval.get('credibility', {}).get('justification', '')}"])
        rows.append(["Source Type", source_eval.get("source_type", "Unknown")])
        rows.append([])  # Empty row as separator
        
        # Threat Actors
        threat_actors = structured.get("threat_actors", [])
        if threat_actors:
            rows.append(["THREAT ACTORS", ""])
            for idx, actor in enumerate(threat_actors, 1):
                aliases = ", ".join(actor.get("aliases", [])) if "aliases" in actor and actor["aliases"] else "None"
                rows.append([f"Actor {idx}", 
                           f"Name: {actor.get('name', 'Unknown')}, " +
                           f"Confidence: {actor.get('confidence', 'Unknown')}, " +
                           f"Aliases: {aliases}, " +
                           f"Description: {actor.get('description', '')}"])
            rows.append([])  # Empty row as separator
        
        # MITRE ATT&CK techniques
        mitre_techniques = structured.get("mitre_techniques", [])
        if mitre_techniques:
            rows.append(["MITRE ATT&CK TECHNIQUES", ""])
            for idx, technique in enumerate(mitre_techniques, 1):
                rows.append([f"Technique {idx}", 
                           f"ID: {technique.get('id', 'Unknown')}, " +
                           f"Name: {technique.get('name', 'Unknown')}, " +
                           f"Description: {technique.get('description', '')}"])
            rows.append([])  # Empty row as separator
        
        # Key insights
        key_insights = structured.get("key_insights", [])
        if key_insights:
            rows.append(["KEY THREAT INTELLIGENCE INSIGHTS", ""])
            for idx, insight in enumerate(key_insights, 1):
                rows.append([f"Insight {idx}", insight])
            rows.append([])  # Empty row as separator
        
        # Potential issues
        potential_issues = structured.get("potential_issues", [])
        if potential_issues:
            rows.append(["POTENTIAL BIAS OR ISSUES", ""])
            for idx, issue in enumerate(potential_issues, 1):
                rows.append([f"Issue {idx}", issue])
            rows.append([])  # Empty row as separator
            
        # Intelligence Gaps
        intelligence_gaps = structured.get("intelligence_gaps", [])
        if intelligence_gaps:
            rows.append(["INTELLIGENCE GAPS", ""])
            for idx, gap in enumerate(intelligence_gaps, 1):
                rows.append([f"Gap {idx}", gap])
            rows.append([])  # Empty row as separator
        
        # Critical sectors
        critical_sectors = structured.get("critical_sectors", [])
        if critical_sectors:
            rows.append(["CRITICAL INFRASTRUCTURE SECTORS", ""])
            for sector in critical_sectors:
                rows.append([sector.get("name", "Unknown"), 
                           f"Score: {sector.get('score', 0)}/5, " +
                           f"Justification: {sector.get('justification', '')}"])
            rows.append([])  # Empty row as separator
        
        # Indicators (if available)
        indicators = structured.get("indicators", {})
        if indicators and indicators.get("total_count", 0) > 0:
            rows.append(["INDICATORS OF COMPROMISE", f"Total Count: {indicators.get('total_count', 0)}"])
            
            # Add IP addresses
            ip_addresses = indicators.get("ip_addresses", [])
            if ip_addresses:
                rows.append(["IP Addresses", ""])
                for ip in ip_addresses:
                    rows.append(["", ip])
            
            # Add domains
            domains = indicators.get("domains", [])
            if domains:
                rows.append(["Domains", ""])
                for domain_item in domains:
                    rows.append(["", domain_item])
            
            # Add URLs
            urls = indicators.get("urls", [])
            if urls:
                rows.append(["URLs", ""])
                for url_item in urls:
                    rows.append(["", url_item])
            
            # Add file hashes
            file_hashes = indicators.get("file_hashes", [])
            if file_hashes:
                rows.append(["File Hashes", ""])
                for hash_item in file_hashes:
                    rows.append(["", hash_item])
            
            # Add email addresses
            email_addresses = indicators.get("email_addresses", [])
            if email_addresses:
                rows.append(["Email Addresses", ""])
                for email in email_addresses:
                    rows.append(["", email])
        
        # Write CSV file
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        
        return {
            "success": True,
            "file_path": file_path,
            "message": "Analysis exported successfully as CSV"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error exporting analysis as CSV: {str(e)}"
        }

def export_analysis_as_markdown(
    analysis_data: Dict[str, Any], 
    domain: Optional[str] = None,
    file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Export analysis data as Markdown.
    
    Converts the analysis data into a well-formatted Markdown document with
    proper headings, lists, tables, and formatting. This format is suitable
    for sharing reports that can be easily viewed in a variety of platforms
    and converted to other formats.
    
    Args:
        analysis_data: Analysis data dictionary containing the complete analysis results
        domain: Domain name from analyzed URL (for filename generation if file_path not provided)
        file_path: Optional file path for export (if not provided, generates a temporary file)
        
    Returns:
        Dictionary with status information:
        - success: Boolean indicating if export was successful
        - file_path: Path to the exported file (if successful)
        - message: Human-readable status message
    """
    try:
        # Generate filename if not provided
        if not file_path:
            filename = get_export_filename(domain, "markdown")
            file_path = os.path.join(tempfile.gettempdir(), filename)
        
        # Extract structured data
        structured = analysis_data.get("structured", {})
        
        # Start building markdown content
        markdown_lines = []
        
        # Add title and metadata
        url = analysis_data.get("url", "Unknown URL")
        markdown_lines.append(f"# Threat Intelligence Analysis: {url}")
        markdown_lines.append(f"*Analysis Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        markdown_lines.append(f"*Model Used: {analysis_data.get('model', 'Unknown')}*")
        markdown_lines.append("")  # Empty line
        
        # Add summary
        if "summary" in structured and structured["summary"]:
            markdown_lines.append("## Summary")
            markdown_lines.append(structured["summary"])
            markdown_lines.append("")  # Empty line
        
        # Add source evaluation
        if "source_evaluation" in structured and structured["source_evaluation"]:
            source_eval = structured["source_evaluation"]
            markdown_lines.append("## Source Evaluation")
            
            # Format reliability
            if "reliability" in source_eval:
                reliability = source_eval["reliability"]
                level = reliability.get("level", "Unknown")
                justification = reliability.get("justification", "")
                markdown_lines.append(f"**Reliability:** {level}")
                if justification:
                    markdown_lines.append(f"- {justification}")
            
            # Format credibility
            if "credibility" in source_eval:
                credibility = source_eval["credibility"]
                level = credibility.get("level", "Unknown")
                justification = credibility.get("justification", "")
                markdown_lines.append(f"**Credibility:** {level}")
                if justification:
                    markdown_lines.append(f"- {justification}")
            
            # Format source type
            if "source_type" in source_eval:
                markdown_lines.append(f"**Source Type:** {source_eval['source_type']}")
            
            markdown_lines.append("")  # Empty line
        
        # Add threat actors
        if "threat_actors" in structured and structured["threat_actors"]:
            markdown_lines.append("## Threat Actors Identified")
            for actor in structured["threat_actors"]:
                name = actor.get("name", "Unknown Actor")
                description = actor.get("description", "")
                confidence = actor.get("confidence", "Medium")
                
                markdown_lines.append(f"### {name} (Confidence: {confidence})")
                if description:
                    markdown_lines.append(description)
                
                if "aliases" in actor and actor["aliases"]:
                    aliases = ", ".join(actor["aliases"])
                    markdown_lines.append(f"**Aliases:** {aliases}")
                
                markdown_lines.append("")  # Empty line
        
        # Add MITRE ATT&CK techniques
        if "mitre_techniques" in structured and structured["mitre_techniques"]:
            markdown_lines.append("## MITRE ATT&CK Techniques")
            for technique in structured["mitre_techniques"]:
                technique_id = technique.get("id", "Unknown")
                technique_name = technique.get("name", "Unknown Technique")
                technique_desc = technique.get("description", "")
                
                # Create link to MITRE website if ID is present
                if technique_id and technique_id.startswith("T"):
                    if '.' in technique_id:
                        # Handle sub-techniques (e.g., T1134.001)
                        base_id, sub_id = technique_id.split('.')
                        mitre_url = f"https://attack.mitre.org/techniques/{base_id}/{sub_id}/"
                    else:
                        mitre_url = f"https://attack.mitre.org/techniques/{technique_id}/"
                    
                    markdown_lines.append(f"### [{technique_id}: {technique_name}]({mitre_url})")
                else:
                    markdown_lines.append(f"### {technique_name}")
                
                if technique_desc:
                    markdown_lines.append(technique_desc)
                
                markdown_lines.append("")  # Empty line
        
        # Add key insights
        if "key_insights" in structured and structured["key_insights"]:
            markdown_lines.append("## Key Threat Intelligence Insights")
            for insight in structured["key_insights"]:
                markdown_lines.append(f"- {insight}")
            markdown_lines.append("")  # Empty line
        
        # Add potential issues
        if "potential_issues" in structured and structured["potential_issues"]:
            markdown_lines.append("## Potential Bias or Issues")
            for issue in structured["potential_issues"]:
                markdown_lines.append(f"- {issue}")
            markdown_lines.append("")  # Empty line
            
        # Add intelligence gaps
        if "intelligence_gaps" in structured and structured["intelligence_gaps"]:
            markdown_lines.append("## Intelligence Gaps")
            for gap in structured["intelligence_gaps"]:
                markdown_lines.append(f"- {gap}")
            markdown_lines.append("")  # Empty line
        
        # Add critical sectors
        if "critical_sectors" in structured and structured["critical_sectors"]:
            markdown_lines.append("## Critical Infrastructure Sectors")
            markdown_lines.append("| Sector | Relevance | Justification |")
            markdown_lines.append("|--------|-----------|---------------|")
            
            for sector in structured["critical_sectors"]:
                name = sector.get("name", "Unknown")
                score = sector.get("score", "?")
                justification = sector.get("justification", "").replace("\n", " ")
                
                markdown_lines.append(f"| {name} | {score}/5 | {justification} |")
            
            markdown_lines.append("")  # Empty line
        
        # Add indicators of compromise if available
        if "indicators" in structured and structured["indicators"]:
            indicators = structured["indicators"]
            if indicators.get("total_count", 0) > 0:
                markdown_lines.append("## Indicators of Compromise")
                markdown_lines.append(f"*Total: {indicators.get('total_count', 0)} indicators found*")
                
                if "ip_addresses" in indicators and indicators["ip_addresses"]:
                    markdown_lines.append("### IP Addresses")
                    for ip in indicators["ip_addresses"]:
                        markdown_lines.append(f"- `{ip}`")
                    markdown_lines.append("")  # Empty line
                
                if "domains" in indicators and indicators["domains"]:
                    markdown_lines.append("### Domains")
                    for domain_item in indicators["domains"]:
                        markdown_lines.append(f"- `{domain_item}`")
                    markdown_lines.append("")  # Empty line
                
                if "urls" in indicators and indicators["urls"]:
                    markdown_lines.append("### URLs")
                    for url_item in indicators["urls"]:
                        markdown_lines.append(f"- `{url_item}`")
                    markdown_lines.append("")  # Empty line
                
                if "file_hashes" in indicators and indicators["file_hashes"]:
                    markdown_lines.append("### File Hashes")
                    for hash_item in indicators["file_hashes"]:
                        markdown_lines.append(f"- `{hash_item}`")
                    markdown_lines.append("")  # Empty line
                
                if "email_addresses" in indicators and indicators["email_addresses"]:
                    markdown_lines.append("### Email Addresses")
                    for email in indicators["email_addresses"]:
                        markdown_lines.append(f"- `{email}`")
                    markdown_lines.append("")  # Empty line
        
        # Add a footer
        markdown_lines.append("---")
        markdown_lines.append("*Generated by ThreatInsight-Analyzer*")
        
        # Write markdown content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(markdown_lines))
        
        return {
            "success": True,
            "file_path": file_path,
            "message": "Analysis exported successfully as Markdown"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error exporting analysis as Markdown: {str(e)}"
        }

def export_analysis_as_pdf(
    analysis_data: Dict[str, Any], 
    domain: Optional[str] = None,
    file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Export analysis data as PDF.
    
    Creates a PDF document from the analysis data, suitable for formal reporting
    and professional presentation. Currently implemented as a placeholder that
    creates a text file instead of a proper PDF.
    
    Args:
        analysis_data: Analysis data dictionary containing the complete analysis results
        domain: Domain name from analyzed URL (for filename generation if file_path not provided)
        file_path: Optional file path for export (if not provided, generates a temporary file)
        
    Returns:
        Dictionary with status information:
        - success: Boolean indicating if export was successful
        - file_path: Path to the exported file (if successful)
        - message: Human-readable status message
    """
    try:
        # Generate filename if not provided
        if not file_path:
            filename = get_export_filename(domain, "pdf")
            file_path = os.path.join(tempfile.gettempdir(), filename)
        
        # Generate markdown first
        markdown_content = export_analysis_as_markdown(analysis_data, domain)
        
        # Use a function to convert markdown to PDF (placeholder)
        pdf_generated = generate_pdf(markdown_content["file_path"], file_path)
        
        if pdf_generated:
            return {
                "success": True,
                "file_path": file_path,
                "message": "Analysis exported successfully as PDF"
            }
        else:
            return {
                "success": False,
                "message": "Failed to generate PDF from markdown"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error exporting analysis as PDF: {str(e)}"
        }

def generate_pdf(markdown_path: str, output_path: str) -> bool:
    """
    Generate a PDF from markdown content.
    
    This is a placeholder function that would use a library like weasyprint or reportlab
    to convert markdown content to a formatted PDF. Currently, it simply creates a text
    file with a placeholder message and the original markdown content.
    
    Args:
        markdown_path: Path to markdown file to convert
        output_path: Output PDF file path
        
    Returns:
        True if PDF was generated successfully, False otherwise
    """
    try:
        # Implement PDF generation logic here
        # For now, we'll just create a simple text file as a placeholder
        with open(markdown_path, 'r', encoding='utf-8') as md_file:
            content = md_file.read()
        
        with open(output_path, 'w', encoding='utf-8') as pdf_file:
            pdf_file.write("PDF PLACEHOLDER\n\n")
            pdf_file.write(content)
        
        return True
    except Exception:
        return False 