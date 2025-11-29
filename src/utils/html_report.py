"""
HTML Report Generator Module

Converts certificate scan results into a beautiful HTML report.
"""

import json
import time
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime


class HTMLReportGenerator:
    """Generates HTML reports from certificate scan data."""
    
    @staticmethod
    def generate_certificate_report(scan_data: Dict[str, Any], analysis: Dict[str, Any] = None,
                                   output_path: str = None) -> str:
        """
        Generate a styled HTML report from certificate scan data.
        
        Args:
            scan_data: Certificate scan results
            analysis: Certificate analysis results (optional)
            output_path: Optional path to save the HTML file
            
        Returns:
            HTML content as string
        """
        summary = scan_data.get('summary', {})
        certificates = scan_data.get('certificates', [])
        
        total_certs = summary.get('total_certificates', 0)
        expired = summary.get('expired', 0)
        expiring_soon = summary.get('expiring_soon', 0)
        valid = summary.get('valid', 0)
        
        # Determine overall status
        if expired > 0:
            status = "CRITICAL"
            status_color = "#ef4444"
        elif expiring_soon > 0:
            status = "WARNING"
            status_color = "#f59e0b"
        else:
            status = "HEALTHY"
            status_color = "#10b981"
        
        # Generate HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kubernetes Certificate Health Report - {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header .timestamp {{
            opacity: 0.9;
            font-size: 0.9em;
        }}
        
        .status-banner {{
            background: {status_color};
            color: white;
            padding: 30px;
            text-align: center;
            font-size: 1.8em;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f9fafb;
        }}
        
        .summary-card {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.2s;
        }}
        
        .summary-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        
        .summary-card .number {{
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
        }}
        
        .summary-card .label {{
            color: #6b7280;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .valid {{ color: #10b981; }}
        .expired {{ color: #ef4444; }}
        .expiring {{ color: #f59e0b; }}
        .total {{ color: #3b82f6; }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section h2 {{
            color: #1f2937;
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        
        .certificate {{
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            margin-bottom: 20px;
            overflow: hidden;
            transition: all 0.3s;
        }}
        
        .certificate:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .certificate-header {{
            background: #f9fafb;
            padding: 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #e5e7eb;
        }}
        
        .certificate-header:hover {{
            background: #f3f4f6;
        }}
        
        .certificate-title {{
            font-size: 1.2em;
            font-weight: 600;
            color: #1f2937;
        }}
        
        .certificate-status {{
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9em;
        }}
        
        .status-expired {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        .status-expiring {{
            background: #fef3c7;
            color: #92400e;
        }}
        
        .status-valid {{
            background: #d1fae5;
            color: #065f46;
        }}
        
        .certificate-body {{
            display: none;
            padding: 20px;
        }}
        
        .certificate.expanded .certificate-body {{
            display: block;
        }}
        
        .certificate.expanded .certificate-header {{
            background: #667eea;
            color: white;
        }}
        
        .certificate.expanded .certificate-title {{
            color: white;
        }}
        
        .cert-detail {{
            background: #f9fafb;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }}
        
        .cert-detail strong {{
            color: #1f2937;
            display: block;
            margin-bottom: 5px;
        }}
        
        .cert-detail .value {{
            color: #4b5563;
            font-family: 'Courier New', monospace;
        }}
        
        .issue {{
            background: #fef2f2;
            padding: 12px;
            border-left: 4px solid #ef4444;
            border-radius: 4px;
            margin-top: 10px;
            color: #991b1b;
        }}
        
        .recommendation {{
            background: #eff6ff;
            padding: 12px;
            border-left: 4px solid #3b82f6;
            border-radius: 4px;
            margin-top: 10px;
            color: #1e40af;
        }}
        
        .footer {{
            background: #f9fafb;
            padding: 30px;
            text-align: center;
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
        }}
        
        .btn-expand {{
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            margin: 20px 0;
        }}
        
        .btn-expand:hover {{
            background: #5568d3;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Kubernetes Certificate Health Report</h1>
            <div class="timestamp">{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</div>
        </div>
        
        <div class="status-banner">
            {status}
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="label">Total Certificates</div>
                <div class="number total">{total_certs}</div>
            </div>
            <div class="summary-card">
                <div class="label">Valid</div>
                <div class="number valid">{valid}</div>
            </div>
            <div class="summary-card">
                <div class="label">Expired</div>
                <div class="number expired">{expired}</div>
            </div>
            <div class="summary-card">
                <div class="label">Expiring Soon</div>
                <div class="number expiring">{expiring_soon}</div>
            </div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>📋 Certificate Details</h2>
                <button class="btn-expand" onclick="toggleAll()">Expand/Collapse All</button>
                {HTMLReportGenerator._generate_certificate_list(certificates)}
            </div>
            
            {HTMLReportGenerator._generate_issues_section(analysis) if analysis else ''}
            {HTMLReportGenerator._generate_recommendations_section(analysis) if analysis else ''}
        </div>
        
        <div class="footer">
            <p>Generated by Kubernetes Certificate Health Checker</p>
            <p>Cluster Type: {scan_data.get('cluster_type', 'Unknown')}</p>
        </div>
    </div>
    
    <script>
        function toggleCertificate(element) {{
            element.parentElement.classList.toggle('expanded');
        }}
        
        function toggleAll() {{
            const certificates = document.querySelectorAll('.certificate');
            const allExpanded = Array.from(certificates).every(c => c.classList.contains('expanded'));
            certificates.forEach(c => {{
                if (allExpanded) {{
                    c.classList.remove('expanded');
                }} else {{
                    c.classList.add('expanded');
                }}
            }});
        }}
    </script>
</body>
</html>"""
        
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(html)
        
        return html
    
    @staticmethod
    def _generate_certificate_list(certificates: list) -> str:
        """Generate HTML for certificate list."""
        html = ""
        for cert in certificates:
            name = cert.get('name', 'Unknown')
            status = cert.get('status', 'unknown')
            days = cert.get('days_until_expiry')
            path = cert.get('path', '')
            subject = cert.get('subject', {})
            issuer = cert.get('issuer', {})
            validity = cert.get('validity', {})
            san = cert.get('san', {})
            issues = cert.get('issues', [])
            
            status_class = f"status-{status.replace('_', '-')}"
            status_text = status.upper()
            if days is not None:
                if status == 'expired':
                    status_text += f" (Expired {abs(days)} days ago)"
                elif status == 'expiring_soon':
                    status_text += f" ({days} days remaining)"
                else:
                    status_text += f" ({days} days remaining)"
            
            html += f"""
            <div class="certificate">
                <div class="certificate-header" onclick="toggleCertificate(this)">
                    <div class="certificate-title">{name}</div>
                    <div class="certificate-status {status_class}">{status_text}</div>
                </div>
                <div class="certificate-body">
                    <div class="cert-detail">
                        <strong>Path:</strong>
                        <div class="value">{path}</div>
                    </div>
                    <div class="cert-detail">
                        <strong>Subject:</strong>
                        <div class="value">{json.dumps(subject, indent=2)}</div>
                    </div>
                    <div class="cert-detail">
                        <strong>Issuer:</strong>
                        <div class="value">{json.dumps(issuer, indent=2)}</div>
                    </div>
                    <div class="cert-detail">
                        <strong>Validity:</strong>
                        <div class="value">
                            Not Before: {validity.get('not_before', 'N/A')}<br>
                            Not After: {validity.get('not_after', 'N/A')}
                        </div>
                    </div>
                    {HTMLReportGenerator._generate_san_html(san)}
                    {HTMLReportGenerator._generate_use_case_html(cert.get('use_case'))}
                    {HTMLReportGenerator._generate_issues_html(issues)}
                </div>
            </div>
            """
        return html
    
    @staticmethod
    def _generate_use_case_html(use_case: Optional[str]) -> str:
        """Generate HTML for certificate use case (AI-powered)."""
        if not use_case:
            return ""
        
        # Format the use case text to handle numbered points properly
        import re
        
        # Replace newlines with spaces first to normalize
        text = use_case.replace('\n', ' ').replace('\r', ' ').strip()
        
        # Split by numbered points (pattern: number followed by period and space)
        # This will split: "1. text 2. text 3. text" into parts
        parts = re.split(r'(\d+\.\s+)', text)
        
        formatted_parts = []
        for i, part in enumerate(parts):
            if re.match(r'^\d+\.\s+$', part):
                # This is a numbered point marker (e.g., "1. ")
                if formatted_parts:  # Add line break before new point (except first)
                    formatted_parts.append('<br><br>')
                formatted_parts.append(f'<strong>{part}</strong>')
            elif part.strip():  # Only add non-empty text parts
                formatted_parts.append(part.strip())
        
        formatted_text = ''.join(formatted_parts)
        
        return f"""
                    <div class="cert-detail" style="background: #eff6ff; border-left: 4px solid #3b82f6;">
                        <strong>💡 Use Case (AI-Powered):</strong>
                        <div class="value" style="margin-top: 8px; color: #1e40af; line-height: 1.8;">{formatted_text}</div>
                    </div>
        """
    
    @staticmethod
    def _generate_san_html(san: Dict[str, Any]) -> str:
        """Generate HTML for Subject Alternative Names."""
        dns_names = san.get('dns_names', [])
        ip_addresses = san.get('ip_addresses', [])
        
        if not dns_names and not ip_addresses:
            return ""
        
        html = '<div class="cert-detail"><strong>Subject Alternative Names:</strong>'
        if dns_names:
            html += f'<div class="value">DNS: {", ".join(dns_names)}</div>'
        if ip_addresses:
            html += f'<div class="value">IP: {", ".join(ip_addresses)}</div>'
        html += '</div>'
        return html
    
    @staticmethod
    def _generate_issues_html(issues: list) -> str:
        """Generate HTML for certificate issues."""
        if not issues:
            return ""
        
        html = ""
        for issue in issues:
            html += f'<div class="issue">⚠️ {issue}</div>'
        return html
    
    @staticmethod
    def _generate_issues_section(analysis: Optional[Dict[str, Any]]) -> str:
        """Generate HTML for critical issues section."""
        if not analysis:
            return ""
        
        critical_issues = analysis.get('critical_issues', [])
        warnings = analysis.get('warnings', [])
        
        if not critical_issues and not warnings:
            return ""
        
        html = '<div class="section"><h2>🚨 Issues & Warnings</h2>'
        
        if critical_issues:
            html += '<h3 style="color: #ef4444; margin-top: 20px;">Critical Issues</h3>'
            for issue in critical_issues:
                cert_name = issue.get('certificate', 'Unknown')
                issue_text = issue.get('issue', '')
                html += f'<div class="issue">🔴 <strong>{cert_name}:</strong> {issue_text}</div>'
        
        if warnings:
            html += '<h3 style="color: #f59e0b; margin-top: 20px;">Warnings</h3>'
            for warning in warnings:
                cert_name = warning.get('certificate', 'Unknown')
                warning_text = warning.get('issue', '')
                html += f'<div class="issue" style="background: #fffbeb; border-left-color: #f59e0b; color: #92400e;">⚠️ <strong>{cert_name}:</strong> {warning_text}</div>'
        
        html += '</div>'
        return html
    
    @staticmethod
    def _generate_recommendations_section(analysis: Optional[Dict[str, Any]]) -> str:
        """Generate HTML for recommendations section."""
        if not analysis:
            return ""
        
        recommendations = analysis.get('recommendations', [])
        if not recommendations:
            return ""
        
        html = '<div class="section"><h2>💡 Recommendations</h2>'
        for rec in recommendations:
            html += f'<div class="recommendation">• {rec}</div>'
        html += '</div>'
        return html

