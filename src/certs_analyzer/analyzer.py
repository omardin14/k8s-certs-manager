"""
Certificate Analyzer Module

Analyzes certificate scan results and provides insights.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class CertificateAnalyzer:
    """Analyzes certificate scan results."""
    
    def __init__(self):
        """Initialize the certificate analyzer."""
        pass
    
    def analyze_results(self, scan_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze certificate scan results and provide insights.
        
        Args:
            scan_results: Certificate scan results dictionary
            
        Returns:
            Analysis results with recommendations
        """
        logger.info("🔍 Analyzing certificate scan results...")
        
        analysis = {
            'overall_status': 'unknown',
            'critical_issues': [],
            'warnings': [],
            'recommendations': [],
            'summary': scan_results.get('summary', {}),
            'certificate_details': []
        }
        
        summary = scan_results.get('summary', {})
        certificates = scan_results.get('certificates', [])
        
        # Determine overall status
        if summary.get('expired', 0) > 0:
            analysis['overall_status'] = 'critical'
        elif summary.get('expiring_soon', 0) > 0:
            analysis['overall_status'] = 'warning'
        elif summary.get('missing', 0) > 0:
            analysis['overall_status'] = 'warning'
        else:
            analysis['overall_status'] = 'healthy'
        
        # Analyze each certificate
        for cert in certificates:
            cert_analysis = self._analyze_certificate(cert)
            analysis['certificate_details'].append(cert_analysis)
            
            # Collect critical issues
            if cert.get('status') == 'expired':
                analysis['critical_issues'].append({
                    'certificate': cert.get('name'),
                    'issue': 'Certificate has expired',
                    'expiry_date': cert.get('validity', {}).get('not_after')
                })
            
            # Collect warnings
            if cert.get('status') == 'expiring_soon':
                days = cert.get('days_until_expiry', 0)
                analysis['warnings'].append({
                    'certificate': cert.get('name'),
                    'issue': f'Certificate expires in {days} days',
                    'expiry_date': cert.get('validity', {}).get('not_after')
                })
            
            # Collect validation issues
            for issue in cert.get('issues', []):
                if 'expired' in issue.lower() or 'missing required' in issue.lower():
                    analysis['critical_issues'].append({
                        'certificate': cert.get('name'),
                        'issue': issue
                    })
                else:
                    analysis['warnings'].append({
                        'certificate': cert.get('name'),
                        'issue': issue
                    })
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        logger.info(f"✅ Analysis complete: {analysis['overall_status']}")
        
        return analysis
    
    def _analyze_certificate(self, cert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single certificate.
        
        Args:
            cert: Certificate information dictionary
            
        Returns:
            Analysis for the certificate
        """
        return {
            'name': cert.get('name'),
            'status': cert.get('status'),
            'days_until_expiry': cert.get('days_until_expiry'),
            'issues': cert.get('issues', []),
            'subject': cert.get('subject', {}),
            'issuer': cert.get('issuer', {})
        }
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on analysis.
        
        Args:
            analysis: Analysis results dictionary
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if analysis['overall_status'] == 'critical':
            recommendations.append('URGENT: Renew expired certificates immediately to prevent cluster failure')
            recommendations.append('Use "kubeadm certs renew all" to renew all certificates (kubeadm clusters)')
        
        if analysis['overall_status'] == 'warning':
            recommendations.append('Schedule certificate renewal before expiration')
            recommendations.append('Set up monitoring alerts for certificate expiration (30 days before)')
        
        expired_count = analysis['summary'].get('expired', 0)
        if expired_count > 0:
            recommendations.append(f'Renew {expired_count} expired certificate(s) using kubeadm certs renew')
        
        expiring_count = analysis['summary'].get('expiring_soon', 0)
        if expiring_count > 0:
            recommendations.append(f'Plan renewal for {expiring_count} certificate(s) expiring within 30 days')
        
        missing_count = analysis['summary'].get('missing', 0)
        if missing_count > 0:
            recommendations.append(f'Investigate {missing_count} missing certificate(s) - may indicate configuration issues')
        
        # General recommendations
        recommendations.append('Regularly monitor certificate expiration dates')
        recommendations.append('Consider automating certificate renewal with kubeadm certs renew')
        recommendations.append('Document certificate renewal procedures for your cluster type')
        
        return recommendations
    
    def create_dummy_data(self) -> Dict[str, Any]:
        """
        Create dummy certificate data for testing.
        
        Returns:
            Dummy certificate scan results
        """
        from datetime import timedelta
        
        now = datetime.utcnow()
        
        return {
            'scan_timestamp': now.isoformat(),
            'cluster_type': 'kubeadm',
            'certificates': [
                {
                    'name': 'apiserver',
                    'path': '/etc/kubernetes/pki/apiserver.crt',
                    'subject': {'CN': 'kube-apiserver'},
                    'issuer': {'CN': 'kubernetes'},
                    'validity': {
                        'not_before': (now - timedelta(days=365)).isoformat(),
                        'not_after': (now + timedelta(days=30)).isoformat()
                    },
                    'san': {
                        'dns_names': ['kubernetes', 'kubernetes.default', 'kubernetes.default.svc'],
                        'ip_addresses': ['10.96.0.1']
                    },
                    'key_info': {'algorithm': 'RSA', 'size': '2048 bit'},
                    'status': 'expiring_soon',
                    'days_until_expiry': 30,
                    'issues': ['Certificate expires in 30 days']
                },
                {
                    'name': 'ca',
                    'path': '/etc/kubernetes/pki/ca.crt',
                    'subject': {'CN': 'kubernetes'},
                    'issuer': {'CN': 'kubernetes'},
                    'validity': {
                        'not_before': (now - timedelta(days=365)).isoformat(),
                        'not_after': (now + timedelta(days=3650)).isoformat()
                    },
                    'san': {'dns_names': [], 'ip_addresses': []},
                    'key_info': {'algorithm': 'RSA', 'size': '2048 bit'},
                    'status': 'valid',
                    'days_until_expiry': 3650,
                    'issues': []
                }
            ],
            'summary': {
                'total_certificates': 2,
                'expired': 0,
                'expiring_soon': 1,
                'valid': 1,
                'missing': 0
            }
        }

