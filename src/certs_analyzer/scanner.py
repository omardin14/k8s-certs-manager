"""
Certificate Scanner Module

Scans Kubernetes cluster for certificates and extracts their information.
"""

import os
import subprocess
import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class CertificateScanner:
    """Scans Kubernetes cluster for certificates."""
    
    # Standard kubeadm certificate paths
    KUBEADM_CERT_PATHS = {
        'apiserver': '/etc/kubernetes/pki/apiserver.crt',
        'apiserver-kubelet-client': '/etc/kubernetes/pki/apiserver-kubelet-client.crt',
        'apiserver-etcd-client': '/etc/kubernetes/pki/apiserver-etcd-client.crt',
        'ca': '/etc/kubernetes/pki/ca.crt',
        'front-proxy-ca': '/etc/kubernetes/pki/front-proxy-ca.crt',
        'front-proxy-client': '/etc/kubernetes/pki/front-proxy-client.crt',
        'etcd-ca': '/etc/kubernetes/pki/etcd/ca.crt',
        'etcd-server': '/etc/kubernetes/pki/etcd/server.crt',
        'etcd-peer': '/etc/kubernetes/pki/etcd/peer.crt',
        'etcd-healthcheck-client': '/etc/kubernetes/pki/etcd/healthcheck-client.crt',
    }
    
    # API server manifest path (kubeadm)
    API_SERVER_MANIFEST = '/etc/kubernetes/manifests/kube-apiserver.yaml'
    
    def __init__(self, cert_base_path: str = '/etc/kubernetes/pki'):
        """
        Initialize the certificate scanner.
        
        Args:
            cert_base_path: Base path for Kubernetes certificates
        """
        self.cert_base_path = Path(cert_base_path)
        self.scan_results = {}
    
    def scan_cluster_certificates(self) -> Dict[str, Any]:
        """
        Scan the Kubernetes cluster for all certificates.
        
        Returns:
            Dictionary containing all certificate information
        """
        logger.info("🔍 Starting Kubernetes certificate scan...")
        
        results = {
            'scan_timestamp': datetime.utcnow().isoformat(),
            'cluster_type': self._detect_cluster_type(),
            'certificates': [],
            'summary': {
                'total_certificates': 0,
                'expired': 0,
                'expiring_soon': 0,
                'valid': 0,
                'missing': 0
            }
        }
        
        # Get certificate list from API server manifest (kubeadm)
        cert_list = self._get_certificates_from_manifest()
        
        # If no manifest found, use standard kubeadm paths
        if not cert_list:
            cert_list = list(self.KUBEADM_CERT_PATHS.keys())
            logger.info("Using standard kubeadm certificate paths")
        
        # Scan each certificate
        for cert_name in cert_list:
            cert_path = self._get_cert_path(cert_name)
            cert_info = self._scan_certificate(cert_name, cert_path)
            
            if cert_info:
                results['certificates'].append(cert_info)
                results['summary']['total_certificates'] += 1
                
                # Update summary
                if cert_info.get('status') == 'expired':
                    results['summary']['expired'] += 1
                elif cert_info.get('status') == 'expiring_soon':
                    results['summary']['expiring_soon'] += 1
                elif cert_info.get('status') == 'valid':
                    results['summary']['valid'] += 1
            else:
                results['summary']['missing'] += 1
        
        self.scan_results = results
        logger.info(f"✅ Certificate scan complete: {results['summary']['total_certificates']} certificates found")
        
        return results
    
    def _detect_cluster_type(self) -> str:
        """
        Detect the type of Kubernetes cluster.
        
        Returns:
            'kubeadm' or 'custom'
        """
        if os.path.exists(self.API_SERVER_MANIFEST):
            return 'kubeadm'
        elif os.path.exists('/etc/kubernetes/pki'):
            return 'kubeadm'  # Likely kubeadm even without manifest
        else:
            return 'custom'
    
    def _get_certificates_from_manifest(self) -> List[str]:
        """
        Extract certificate paths from kube-apiserver manifest.
        
        Returns:
            List of certificate names/paths
        """
        if not os.path.exists(self.API_SERVER_MANIFEST):
            logger.debug(f"API server manifest not found at {self.API_SERVER_MANIFEST}")
            return []
        
        try:
            import yaml
            with open(self.API_SERVER_MANIFEST, 'r') as f:
                manifest = yaml.safe_load(f)
            
            cert_names = []
            containers = manifest.get('spec', {}).get('containers', [])
            for container in containers:
                volume_mounts = container.get('volumeMounts', [])
                for vm in volume_mounts:
                    mount_path = vm.get('mountPath', '')
                    if 'pki' in mount_path or 'cert' in mount_path.lower():
                        # Extract certificate references from command args
                        args = container.get('args', [])
                        for arg in args:
                            if '--' in arg and ('cert' in arg.lower() or 'key' in arg.lower()):
                                # Extract certificate name from argument
                                if '=' in arg:
                                    cert_path = arg.split('=')[1]
                                    cert_name = Path(cert_path).stem.replace('.crt', '').replace('.key', '')
                                    if cert_name and cert_name not in cert_names:
                                        cert_names.append(cert_name)
            
            logger.info(f"Found {len(cert_names)} certificates from manifest")
            return cert_names if cert_names else []
            
        except Exception as e:
            logger.warning(f"Could not parse API server manifest: {e}")
            return []
    
    def _get_cert_path(self, cert_name: str) -> Optional[Path]:
        """
        Get the full path for a certificate.
        
        Args:
            cert_name: Name of the certificate
            
        Returns:
            Path to certificate file or None
        """
        # Check standard kubeadm paths
        if cert_name in self.KUBEADM_CERT_PATHS:
            path = Path(self.KUBEADM_CERT_PATHS[cert_name])
            if path.exists():
                return path
        
        # Try common variations
        variations = [
            self.cert_base_path / f"{cert_name}.crt",
            self.cert_base_path / f"{cert_name}.pem",
            self.cert_base_path / "etcd" / f"{cert_name}.crt",
            self.cert_base_path / "etcd" / f"{cert_name}.pem",
        ]
        
        for path in variations:
            if path.exists():
                return path
        
        return None
    
    def _scan_certificate(self, cert_name: str, cert_path: Optional[Path]) -> Optional[Dict[str, Any]]:
        """
        Scan a single certificate file.
        
        Args:
            cert_name: Name of the certificate
            cert_path: Path to certificate file
            
        Returns:
            Certificate information dictionary or None
        """
        if not cert_path or not cert_path.exists():
            logger.warning(f"Certificate not found: {cert_name}")
            return None
        
        try:
            # Use openssl to extract certificate information
            result = subprocess.run(
                ['openssl', 'x509', '-in', str(cert_path), '-text', '-noout'],
                capture_output=True,
                text=True,
                check=True
            )
            
            cert_text = result.stdout
            cert_info = self._parse_openssl_output(cert_name, cert_path, cert_text)
            
            logger.debug(f"Scanned certificate: {cert_name}")
            return cert_info
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error scanning certificate {cert_name}: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error scanning certificate {cert_name}: {e}")
            return None
    
    def _parse_openssl_output(self, cert_name: str, cert_path: Path, openssl_output: str) -> Dict[str, Any]:
        """
        Parse openssl x509 output into structured data.
        
        Args:
            cert_name: Name of the certificate
            cert_path: Path to certificate file
            openssl_output: Output from openssl x509 command
            
        Returns:
            Structured certificate information
        """
        lines = openssl_output.split('\n')
        
        cert_info = {
            'name': cert_name,
            'path': str(cert_path),
            'subject': {},
            'issuer': {},
            'validity': {},
            'san': {
                'dns_names': [],
                'ip_addresses': []
            },
            'key_info': {},
            'status': 'unknown',
            'days_until_expiry': None,
            'issues': []
        }
        
        current_section = None
        for line in lines:
            line = line.strip()
            
            # Subject
            if line.startswith('Subject:'):
                cert_info['subject'] = self._parse_dn(line.replace('Subject:', '').strip())
            
            # Issuer
            elif line.startswith('Issuer:'):
                cert_info['issuer'] = self._parse_dn(line.replace('Issuer:', '').strip())
            
            # Validity
            elif line.startswith('Not Before:'):
                cert_info['validity']['not_before'] = self._parse_date(line.replace('Not Before:', '').strip())
            elif line.startswith('Not After :') or line.startswith('Not After:'):
                cert_info['validity']['not_after'] = self._parse_date(line.replace('Not After :', '').replace('Not After:', '').strip())
            
            # Subject Alternative Name
            elif 'X509v3 Subject Alternative Name' in line or current_section == 'san':
                current_section = 'san'
                if 'DNS:' in line:
                    dns_names = [d.replace('DNS:', '').strip() for d in line.split(',') if 'DNS:' in d]
                    cert_info['san']['dns_names'].extend(dns_names)
                if 'IP Address:' in line or 'IP:' in line:
                    ip_addrs = [ip.replace('IP Address:', '').replace('IP:', '').strip() 
                               for ip in line.split(',') if 'IP Address:' in ip or 'IP:' in ip]
                    cert_info['san']['ip_addresses'].extend(ip_addrs)
            
            # Key information
            elif 'Public Key Algorithm:' in line:
                cert_info['key_info']['algorithm'] = line.replace('Public Key Algorithm:', '').strip()
            elif 'RSA Public-Key:' in line or 'Public-Key:' in line:
                key_size = line.replace('RSA Public-Key:', '').replace('Public-Key:', '').strip()
                cert_info['key_info']['size'] = key_size
            
            # Reset section if we hit a new major section
            if line and not line.startswith(' ') and ':' in line and current_section == 'san':
                if 'X509v3' not in line:
                    current_section = None
        
        # Determine status
        if cert_info['validity'].get('not_after'):
            not_after = cert_info['validity']['not_after']
            if isinstance(not_after, datetime):
                now = datetime.utcnow()
                days_until = (not_after - now).days
                cert_info['days_until_expiry'] = days_until
                
                if days_until < 0:
                    cert_info['status'] = 'expired'
                    cert_info['issues'].append('Certificate has expired')
                elif days_until < 30:
                    cert_info['status'] = 'expiring_soon'
                    cert_info['issues'].append(f'Certificate expires in {days_until} days')
                else:
                    cert_info['status'] = 'valid'
        
        # Validate against Kubernetes requirements
        validation_issues = self._validate_certificate(cert_info)
        cert_info['issues'].extend(validation_issues)
        
        return cert_info
    
    def _parse_dn(self, dn_string: str) -> Dict[str, str]:
        """
        Parse Distinguished Name string.
        
        Args:
            dn_string: DN string like "CN=kubernetes, O=system:masters"
            
        Returns:
            Dictionary of DN components
        """
        dn = {}
        parts = dn_string.split(',')
        for part in parts:
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                dn[key.strip()] = value.strip()
        return dn
    
    def _parse_date(self, date_string: str) -> Optional[datetime]:
        """
        Parse date string from openssl output.
        
        Args:
            date_string: Date string like "Feb 11 05:39:20 2020 GMT"
            
        Returns:
            datetime object or None
        """
        try:
            # Remove GMT and parse
            date_string = date_string.replace('GMT', '').strip()
            return datetime.strptime(date_string, '%b %d %H:%M:%S %Y')
        except Exception as e:
            logger.warning(f"Could not parse date: {date_string}, {e}")
            return None
    
    def _validate_certificate(self, cert_info: Dict[str, Any]) -> List[str]:
        """
        Validate certificate against Kubernetes requirements.
        
        Args:
            cert_info: Certificate information dictionary
            
        Returns:
            List of validation issues
        """
        issues = []
        cert_name = cert_info.get('name', '')
        
        # API Server certificate validation
        if 'apiserver' in cert_name and 'kubelet-client' not in cert_name and 'etcd-client' not in cert_name:
            # Should have SAN entries for all required names
            required_dns = ['kubernetes', 'kubernetes.default', 'kubernetes.default.svc', 
                          'kubernetes.default.svc.cluster.local']
            dns_names = cert_info.get('san', {}).get('dns_names', [])
            
            for required in required_dns:
                if required not in dns_names:
                    issues.append(f'Missing required DNS name in SAN: {required}')
        
        # Check key size (should be at least 2048 bits)
        key_size = cert_info.get('key_info', {}).get('size', '')
        if key_size:
            try:
                size_num = int(key_size.replace('bit', '').strip())
                if size_num < 2048:
                    issues.append(f'Key size ({size_num} bits) is below recommended 2048 bits')
            except:
                pass
        
        # Check issuer (should be kubernetes CA for cluster certs)
        issuer_cn = cert_info.get('issuer', {}).get('CN', '')
        if 'apiserver' in cert_name and issuer_cn != 'kubernetes':
            issues.append(f'Unexpected issuer: {issuer_cn} (expected: kubernetes)')
        
        return issues
    
    def save_results(self, output_path: str) -> None:
        """
        Save scan results to JSON file.
        
        Args:
            output_path: Path to save JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(self.scan_results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {output_file}")

