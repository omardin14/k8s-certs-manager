"""
Slack Formatter Module

Handles formatting of certificate scan results into Slack message blocks.
"""

import json
import time
from typing import Dict, Any, List
from datetime import datetime


class SlackFormatter:
    """Formats certificate scan results into Slack message blocks."""
    
    @staticmethod
    def parse_certificate_summary(data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse certificate scan data to extract summary information."""
        summary = data.get('summary', {})
        certificates = data.get('certificates', [])
        
        return {
            'total_certificates': summary.get('total_certificates', 0),
            'expired': summary.get('expired', 0),
            'expiring_soon': summary.get('expiring_soon', 0),
            'valid': summary.get('valid', 0),
            'missing': summary.get('missing', 0),
            'cluster_type': data.get('cluster_type', 'unknown'),
            'scan_timestamp': data.get('scan_timestamp', ''),
            'certificates': certificates
        }
    
    @staticmethod
    def create_certificate_blocks(summary: Dict[str, Any], analysis: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Create Slack blocks for certificate report."""
        # Determine overall status
        if summary['expired'] > 0:
            status_emoji = "🔴"
            status_text = "CRITICAL"
            status_color = "#ff0000"
        elif summary['expiring_soon'] > 0:
            status_emoji = "⚠️"
            status_text = "WARNING"
            status_color = "#ff9900"
        else:
            status_emoji = "✅"
            status_text = "HEALTHY"
            status_color = "#36a64f"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} Kubernetes Certificate Health Check",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Status:* {status_text}\n*Cluster Type:* {summary.get('cluster_type', 'Unknown')}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Certificates:*\n`{summary['total_certificates']}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Valid:*\n✅ `{summary['valid']}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Expired:*\n🔴 `{summary['expired']}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Expiring Soon:*\n⚠️ `{summary['expiring_soon']}`"
                    }
                ]
            }
        ]
        
        # Add critical issues section
        if analysis and analysis.get('critical_issues'):
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🔴 Critical Issues:*"
                }
            })
            for issue in analysis['critical_issues'][:5]:  # Show top 5
                cert_name = issue.get('certificate', 'Unknown')
                issue_text = issue.get('issue', '')
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• *{cert_name}*: {issue_text}"
                    }
                })
        
        # Add warnings section
        if analysis and analysis.get('warnings'):
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*⚠️ Warnings:*"
                }
            })
            for warning in analysis['warnings'][:5]:  # Show top 5
                cert_name = warning.get('certificate', 'Unknown')
                warning_text = warning.get('issue', '')
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• *{cert_name}*: {warning_text}"
                    }
                })
        
        # Add certificate details
        if summary.get('certificates'):
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*📋 Certificate Details:*"
                }
            })
            
            for cert in summary['certificates'][:10]:  # Show top 10
                cert_name = cert.get('name', 'Unknown')
                status = cert.get('status', 'unknown')
                days = cert.get('days_until_expiry')
                
                # Choose emoji based on status
                if status == 'expired':
                    emoji = "🔴"
                elif status == 'expiring_soon':
                    emoji = "⚠️"
                else:
                    emoji = "✅"
                
                status_text = f"{emoji} {status.upper()}"
                if days is not None:
                    status_text += f" ({days} days)"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{cert_name}*: {status_text}"
                    }
                })
        
        # Add recommendations if available
        if analysis and analysis.get('recommendations'):
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*💡 Recommendations:*"
                }
            })
            for rec in analysis['recommendations'][:5]:  # Show top 5
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• {rec}"
                    }
                })
        
        # Add timestamp and footer
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"⏰ Scan completed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())} | 📄 Full HTML report attached below"
                }
            ]
        })
        
        return blocks
    
    @staticmethod
    def create_test_blocks() -> List[Dict[str, Any]]:
        """Create blocks for test messages."""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔐 Kubernetes Certificate Health Check Test"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Test Status:*\n✅ Connection Working"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Bot Status:*\n🤖 Ready for certificate scanning"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "This is a *test message* to verify the Kubernetes certificate health check Slack integration is working correctly! 🎉"
                }
            }
        ]
    
    @staticmethod
    def format_json_data(data: Dict[str, Any], title: str = "Data Export") -> List[Dict[str, Any]]:
        """Format structured data as JSON blocks."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```json\n{json.dumps(data, indent=2)}\n```"
                }
            }
        ]
        
        return blocks

