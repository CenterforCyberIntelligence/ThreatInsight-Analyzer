"""
Utility functions for exporting analysis data in different formats.
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
    
    Args:
        domain: Domain name from analyzed URL
        format_type: Export format (json, csv, pdf, markdown)
        
    Returns:
        Sanitized filename with timestamp
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
    
    Args:
        analysis_data: Analysis data dictionary
        domain: Domain name from analyzed URL
        file_path: Optional file path for export
        
    Returns:
        Dictionary with status and file path
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
    
    Args:
        analysis_data: Analysis data dictionary
        domain: Domain name from analyzed URL
        file_path: Optional file path for export
        
    Returns:
        Dictionary with status and file path
    """
    try:
        # Generate filename if not provided
        if not file_path:
            filename = get_export_filename(domain, "csv")
            file_path = os.path.join(tempfile.gettempdir(), filename)
        
        # Prepare rows for CSV
        rows = []
        
        # Add header row
        rows.append(["Category", "Value"])
        
        # Add summary
        if "summary" in analysis_data and analysis_data["summary"]:
            rows.append(["Summary", analysis_data["summary"]])
        
        # Add source evaluation
        if "source_evaluation" in analysis_data and analysis_data["source_evaluation"]:
            source_eval = analysis_data["source_evaluation"]
            
            if "reliability" in source_eval:
                rows.append(["Reliability", source_eval["reliability"]])
            
            if "credibility" in source_eval:
                rows.append(["Credibility", source_eval["credibility"]])
            
            if "source_type" in source_eval:
                rows.append(["Source Type", source_eval["source_type"]])
        
        # Add threat actors
        if "threat_actors" in analysis_data and analysis_data["threat_actors"]:
            for actor in analysis_data["threat_actors"]:
                rows.append(["Threat Actor", actor])
        
        # Add MITRE techniques
        if "mitre_techniques" in analysis_data and analysis_data["mitre_techniques"]:
            techniques = analysis_data["mitre_techniques"]
            
            for technique in techniques:
                if isinstance(technique, dict) and "id" in technique and "name" in technique:
                    technique_display = f"{technique['id']}: {technique['name']}"
                    if "url" in technique:
                        technique_display += f" ({technique['url']})"
                    rows.append(["MITRE Technique", technique_display])
                elif isinstance(technique, str):
                    rows.append(["MITRE Technique", technique])
        
        # Add key insights
        if "key_insights" in analysis_data and analysis_data["key_insights"]:
            for insight in analysis_data["key_insights"]:
                rows.append(["Key Insight", insight])
        
        # Add source bias
        if "source_bias" in analysis_data and analysis_data["source_bias"]:
            rows.append(["Source Bias", analysis_data["source_bias"]])
        
        # Add intelligence gaps
        if "intelligence_gaps" in analysis_data and analysis_data["intelligence_gaps"]:
            for gap in analysis_data["intelligence_gaps"]:
                rows.append(["Intelligence Gap", gap])
        
        # Add critical infrastructure sectors
        if "critical_infrastructure_sectors" in analysis_data and analysis_data["critical_infrastructure_sectors"]:
            sectors = analysis_data["critical_infrastructure_sectors"]
            for sector, score in sectors.items():
                rows.append(["Critical Infrastructure", f"{sector}: {score}/5"])
        
        # Write to CSV file
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
    
    Args:
        analysis_data: Analysis data dictionary
        domain: Domain name from analyzed URL
        file_path: Optional file path for export
        
    Returns:
        Dictionary with status and file path
    """
    try:
        # Generate filename if not provided
        if not file_path:
            filename = get_export_filename(domain, "markdown")
            file_path = os.path.join(tempfile.gettempdir(), filename)
        
        # Build markdown content
        lines = []
        
        # Add title
        lines.append(f"# Threat Intelligence Analysis: {domain or 'Unknown Source'}")
        lines.append("")
        lines.append(f"*Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        
        # Add summary
        if "summary" in analysis_data and analysis_data["summary"]:
            lines.append("## Summary")
            lines.append("")
            lines.append(analysis_data["summary"])
            lines.append("")
        
        # Add source evaluation
        if "source_evaluation" in analysis_data and analysis_data["source_evaluation"]:
            lines.append("## Source Evaluation")
            lines.append("")
            
            source_eval = analysis_data["source_evaluation"]
            
            if "reliability" in source_eval:
                lines.append(f"**Reliability:** {source_eval['reliability']}")
            
            if "credibility" in source_eval:
                lines.append(f"**Credibility:** {source_eval['credibility']}")
            
            if "source_type" in source_eval:
                lines.append(f"**Source Type:** {source_eval['source_type']}")
            
            lines.append("")
        
        # Add threat actors
        if "threat_actors" in analysis_data and analysis_data["threat_actors"]:
            lines.append("## Threat Actors")
            lines.append("")
            
            for actor in analysis_data["threat_actors"]:
                lines.append(f"* {actor}")
            
            lines.append("")
        
        # Add MITRE techniques
        if "mitre_techniques" in analysis_data and analysis_data["mitre_techniques"]:
            lines.append("## MITRE ATT&CK Techniques")
            lines.append("")
            
            techniques = analysis_data["mitre_techniques"]
            
            for technique in techniques:
                if isinstance(technique, dict) and "id" in technique and "name" in technique:
                    if "url" in technique:
                        lines.append(f"* [{technique['id']}: {technique['name']}]({technique['url']})")
                    else:
                        lines.append(f"* {technique['id']}: {technique['name']}")
                elif isinstance(technique, str):
                    lines.append(f"* {technique}")
            
            lines.append("")
        
        # Add key insights
        if "key_insights" in analysis_data and analysis_data["key_insights"]:
            lines.append("## Key Insights")
            lines.append("")
            
            for insight in analysis_data["key_insights"]:
                lines.append(f"* {insight}")
            
            lines.append("")
        
        # Add source bias
        if "source_bias" in analysis_data and analysis_data["source_bias"]:
            lines.append("## Source Bias")
            lines.append("")
            lines.append(analysis_data["source_bias"])
            lines.append("")
        
        # Add intelligence gaps
        if "intelligence_gaps" in analysis_data and analysis_data["intelligence_gaps"]:
            lines.append("## Intelligence Gaps")
            lines.append("")
            
            for gap in analysis_data["intelligence_gaps"]:
                lines.append(f"* {gap}")
            
            lines.append("")
        
        # Add critical infrastructure sectors
        if "critical_infrastructure_sectors" in analysis_data and analysis_data["critical_infrastructure_sectors"]:
            lines.append("## Critical Infrastructure Sectors")
            lines.append("")
            
            sectors = analysis_data["critical_infrastructure_sectors"]
            for sector, score in sectors.items():
                lines.append(f"* {sector}: {score}/5")
            
            lines.append("")
        
        # Write to markdown file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        
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
    
    Args:
        analysis_data: Analysis data dictionary
        domain: Domain name from analyzed URL
        file_path: Optional file path for export
        
    Returns:
        Dictionary with status and file path
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
    This is a placeholder function that would use a library like weasyprint or reportlab.
    
    Args:
        markdown_path: Path to markdown file
        output_path: Output PDF path
        
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