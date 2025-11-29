"""
Certificate Scanner Module

Scans Kubernetes cluster for certificates by discovering them from static pod configurations.
"""

import os
import subprocess
import logging
import json
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

try:
    from kubernetes import client, config
    from kubernetes.stream import stream
    from kubernetes.client.rest import ApiException
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("kubernetes library not available. Install with: pip install kubernetes")

logger = logging.getLogger(__name__)


class CertificateScanner:
    """Scans Kubernetes cluster for certificates by discovering them from static pods."""
    
    # Static pod name patterns to look for
    STATIC_POD_PATTERNS = {
        'kube-apiserver': ['kube-apiserver'],
        'etcd': ['etcd'],
        'kube-controller-manager': ['kube-controller-manager'],
        'kube-scheduler': ['kube-scheduler'],
    }
    
    # Certificate argument patterns to extract from pod args
    CERT_ARG_PATTERNS = [
        '--tls-cert-file',
        '--tls-private-key-file',
        '--client-ca-file',
        '--etcd-cafile',
        '--etcd-certfile',
        '--etcd-keyfile',
        '--kubelet-client-certificate',
        '--kubelet-client-key',
        '--service-account-key-file',
        '--proxy-client-cert-file',
        '--proxy-client-key-file',
    ]
    
    def __init__(self, cert_base_path: str = '/etc/kubernetes/pki'):
        """
        Initialize the certificate scanner.
        
        Args:
            cert_base_path: Base path for Kubernetes certificates (fallback only)
        """
        self.cert_base_path = Path(cert_base_path)
        self.scan_results = {}
        self.k8s_client = None
        self.core_v1 = None
        
        # Initialize Kubernetes client if available
        if KUBERNETES_AVAILABLE:
            try:
                # Try in-cluster config first (when running in a pod)
                try:
                    config.load_incluster_config()
                    logger.info("✅ Loaded in-cluster Kubernetes configuration")
                except:
                    # Fall back to kubeconfig (for local testing)
                    try:
                        config.load_kube_config()
                        logger.info("✅ Loaded kubeconfig from default location")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not load Kubernetes config: {e}")
                
                self.k8s_client = client.ApiClient()
                self.core_v1 = client.CoreV1Api()
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize Kubernetes client: {e}")
    
    def scan_cluster_certificates(self) -> Dict[str, Any]:
        """
        Scan the Kubernetes cluster for all certificates by discovering them from static pods.
        
        Returns:
            Dictionary containing all certificate information
        """
        logger.info("🔍 Starting Kubernetes certificate scan...")
        
        results = {
            'scan_timestamp': datetime.utcnow().isoformat(),
            'cluster_type': 'unknown',
            'certificates': [],
            'summary': {
                'total_certificates': 0,
                'expired': 0,
                'expiring_soon': 0,
                'valid': 0,
                'missing': 0
            }
        }
        
        # Try to discover certificates from static pods (primary method)
        discovered_certs = {}
        
        if self.core_v1:
            try:
                discovered_certs = self._discover_certificates_from_static_pods()
                if discovered_certs:
                    results['cluster_type'] = 'kubeadm'
                    logger.info(f"✅ Discovered {len(discovered_certs)} certificate(s) from static pods")
            except Exception as e:
                logger.warning(f"⚠️ Could not discover certificates from static pods: {e}")
        
        # Also try filesystem-based discovery (fallback)
        filesystem_certs = self._discover_certificates_from_filesystem()
        
        # Merge discovered certificates (static pods take precedence)
        all_cert_paths = {**filesystem_certs, **discovered_certs}
        
        if not all_cert_paths:
            logger.warning("⚠️ No certificates discovered. Trying fallback paths...")
            # Fallback to standard kubeadm paths
            all_cert_paths = self._get_fallback_cert_paths()
        
        # Scan each discovered certificate
        for cert_name, cert_path in all_cert_paths.items():
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
    
    def _discover_certificates_from_static_pods(self) -> Dict[str, Path]:
        """
        Discover certificate paths from static pod configurations.
        
        Returns:
            Dictionary mapping certificate names to paths
        """
        discovered = {}
        
        if not self.core_v1:
            return discovered
        
        try:
            # List all pods in kube-system namespace
            pods = self.core_v1.list_namespaced_pod(namespace='kube-system')
            
            for pod in pods.items:
                pod_name = pod.metadata.name
                
                # Check if this is a static pod
                for component, patterns in self.STATIC_POD_PATTERNS.items():
                    if any(pattern in pod_name for pattern in patterns):
                        logger.info(f"📋 Found static pod: {component} ({pod_name})")
                        
                        # Extract certificate paths from this pod
                        certs = self._extract_cert_paths_from_pod(pod, component)
                        discovered.update(certs)
                        break
            
            return discovered
            
        except ApiException as e:
            logger.warning(f"⚠️ Kubernetes API error: {e}")
            return {}
        except Exception as e:
            logger.warning(f"⚠️ Error discovering certificates from static pods: {e}")
            return {}
    
    def _extract_cert_paths_from_pod(self, pod, component: str) -> Dict[str, Path]:
        """
        Extract certificate paths from a static pod's configuration.
        
        Args:
            pod: Kubernetes pod object
            component: Component name (e.g., 'kube-apiserver')
            
        Returns:
            Dictionary mapping certificate names to paths
        """
        cert_paths = {}
        
        if not pod.spec or not pod.spec.containers:
            return cert_paths
        
        # Map volume mounts to paths
        volume_map = {}
        if pod.spec.volumes:
            for vol in pod.spec.volumes:
                if vol.host_path:
                    volume_map[vol.name] = vol.host_path.path
        
        for container in pod.spec.containers:
            # Map volume mounts to mount paths
            mount_map = {}
            if container.volume_mounts:
                for vm in container.volume_mounts:
                    mount_map[vm.name] = vm.mount_path
                    # If volume has hostPath, use that
                    if vm.name in volume_map:
                        mount_map[vm.name] = volume_map[vm.name]
            
            # Extract certificate paths from container arguments
            if container.args:
                for arg in container.args:
                    if '=' in arg:
                        key, value = arg.split('=', 1)
                        
                        # Check if this is a certificate-related argument
                        if any(pattern in key for pattern in self.CERT_ARG_PATTERNS):
                            # Resolve the path
                            cert_path = self._resolve_cert_path(value, mount_map, component)
                            
                            if cert_path and cert_path.exists():
                                # Generate a friendly name
                                cert_name = self._generate_cert_name(key, value, component)
                                cert_paths[cert_name] = cert_path
                                logger.info(f"  ✅ Found certificate: {cert_name} at {cert_path}")
            
            # Also check for certificates in mounted directories (only Kubernetes cert dirs)
            if container.volume_mounts:
                for vm in container.volume_mounts:
                    mount_path = Path(vm.mount_path)
                    # Only scan if it's a Kubernetes certificate directory
                    if self._is_kubernetes_cert_directory(mount_path):
                        # Try to find certificates in this directory
                        dir_certs = self._find_certificates_in_directory(mount_path)
                        cert_paths.update(dir_certs)
        
        return cert_paths
    
    def _resolve_cert_path(self, path_str: str, mount_map: Dict[str, str], component: str) -> Optional[Path]:
        """
        Resolve a certificate path, handling volume mounts and relative paths.
        Tries multiple locations including common minikube paths.
        
        Args:
            path_str: Path string from pod argument
            mount_map: Mapping of volume names to mount paths
            component: Component name
            
        Returns:
            Resolved Path object or None
        """
        path = Path(path_str)
        
        # List of potential base paths to try (only Kubernetes cert directories)
        potential_bases = [
            self.cert_base_path,  # Standard kubeadm path
            Path('/var/lib/minikube/certs'),  # Minikube path
            Path('/etc/kubernetes/pki'),  # Standard kubeadm
        ]
        
        # If absolute path, try it directly and with different bases
        if path.is_absolute():
            # Try the path as-is first, but only if it's a Kubernetes cert directory
            if path.exists() and self._is_kubernetes_cert_directory(path.parent):
                return path
            
            # Try to find it relative to different base paths
            # Extract the relative part (e.g., /var/lib/minikube/certs/apiserver.crt -> apiserver.crt)
            file_name = path.name
            for base in potential_bases:
                try:
                    # Try the full path if it's under this base
                    try:
                        # Python 3.9+ has is_relative_to
                        if hasattr(path, 'is_relative_to') and path.is_relative_to(base):
                            if path.exists():
                                return path
                    except AttributeError:
                        # Fall back to checking if path starts with base
                        try:
                            path_str = str(path)
                            base_str = str(base)
                            if path_str.startswith(base_str):
                                if path.exists():
                                    return path
                        except:
                            pass
                    
                    # Try to find the file by name in the base directory
                    potential_path = base / file_name
                    if potential_path.exists():
                        return potential_path
                    # Also try in subdirectories
                    for subdir in ['etcd', '']:
                        potential_path = base / subdir / file_name if subdir else base / file_name
                        if potential_path.exists():
                            return potential_path
                except (ValueError, AttributeError, OSError):
                    # Path operations failed, continue
                    pass
        
        # Check if path references a volume mount
        for vol_name, mount_path in mount_map.items():
            if vol_name in path_str or path_str.startswith(vol_name):
                resolved = Path(mount_path) / path.name
                if resolved.exists():
                    return resolved
        
        # Try relative to cert_base_path
        if not path.is_absolute():
            resolved = self.cert_base_path / path
            if resolved.exists():
                return resolved
        
        # Last resort: try to find by filename in common locations (only K8s cert dirs)
        file_name = path.name
        for base in potential_bases:
            if base.exists() and self._is_kubernetes_cert_directory(base):
                # Try direct
                potential = base / file_name
                if potential.exists():
                    return potential
                # Try in etcd subdirectory
                potential = base / 'etcd' / file_name
                if potential.exists():
                    return potential
        
        return None
    
    def _generate_cert_name(self, arg_key: str, arg_value: str, component: str) -> str:
        """
        Generate a friendly certificate name from argument key and value.
        
        Args:
            arg_key: Argument key (e.g., '--tls-cert-file')
            arg_value: Argument value (path)
            component: Component name
            
        Returns:
            Friendly certificate name
        """
        # Extract filename
        path = Path(arg_value)
        base_name = path.stem.replace('.crt', '').replace('.pem', '').replace('.key', '')
        
        # Map common patterns to friendly names
        name_map = {
            '--tls-cert-file': f'{component}-server',
            '--client-ca-file': 'ca',
            '--etcd-cafile': 'etcd-ca',
            '--etcd-certfile': f'{component}-etcd-client',
            '--kubelet-client-certificate': f'{component}-kubelet-client',
            '--proxy-client-cert-file': f'{component}-front-proxy-client',
        }
        
        if arg_key in name_map:
            return name_map[arg_key]
        
        # Use component and base name
        if base_name:
            return f'{component}-{base_name}'
        
        return f'{component}-cert'
    
    def _is_kubernetes_cert_directory(self, directory: Path) -> bool:
        """
        Check if a directory is a Kubernetes certificate directory.
        
        Args:
            directory: Directory path to check
            
        Returns:
            True if this is a Kubernetes cert directory, False otherwise
        """
        dir_str = str(directory)
        
        # Kubernetes certificate directories
        k8s_cert_dirs = [
            '/etc/kubernetes/pki',
            '/var/lib/minikube/certs',
            '/etc/kubernetes',
        ]
        
        # System certificate directories to exclude
        system_cert_dirs = [
            '/etc/ssl/certs',
            '/usr/share/ca-certificates',
            '/etc/ca-certificates',
            '/usr/local/share/ca-certificates',
        ]
        
        # Check if it's a system cert directory (exclude)
        for sys_dir in system_cert_dirs:
            if dir_str.startswith(sys_dir):
                return False
        
        # Check if it's a Kubernetes cert directory (include)
        for k8s_dir in k8s_cert_dirs:
            if dir_str.startswith(k8s_dir):
                return True
        
        # If it contains 'pki' or 'kubernetes' in the path, it's likely a K8s cert dir
        if 'pki' in dir_str.lower() or 'kubernetes' in dir_str.lower():
            return True
        
        # If it contains 'minikube' and 'cert', it's likely a K8s cert dir
        if 'minikube' in dir_str.lower() and 'cert' in dir_str.lower():
            return True
        
        return False
    
    def _find_certificates_in_directory(self, directory: Path) -> Dict[str, Path]:
        """
        Find all certificate files in a directory (only Kubernetes certificate directories).
        
        Args:
            directory: Directory path to search
            
        Returns:
            Dictionary mapping certificate names to paths
        """
        certs = {}
        
        if not directory.exists() or not directory.is_dir():
            return certs
        
        # Only scan Kubernetes certificate directories
        if not self._is_kubernetes_cert_directory(directory):
            logger.debug(f"Skipping non-Kubernetes certificate directory: {directory}")
            return certs
        
        try:
            # Look for .crt and .pem files (non-recursive to avoid system certs)
            for ext in ['*.crt', '*.pem']:
                # First check direct files in the directory
                for cert_file in directory.glob(ext):
                    if cert_file.is_file():
                        cert_name = cert_file.stem
                        # Skip key files
                        if 'key' not in cert_name.lower():
                            certs[cert_name] = cert_file
                
                # Also check in etcd subdirectory if it exists
                etcd_dir = directory / 'etcd'
                if etcd_dir.exists() and etcd_dir.is_dir():
                    for cert_file in etcd_dir.glob(ext):
                        if cert_file.is_file():
                            cert_name = cert_file.stem
                            # Skip key files
                            if 'key' not in cert_name.lower():
                                certs[f'etcd-{cert_name}'] = cert_file
        except Exception as e:
            logger.warning(f"⚠️ Error searching directory {directory}: {e}")
        
        return certs
    
    def _discover_certificates_from_filesystem(self) -> Dict[str, Path]:
        """
        Discover certificates from the filesystem (fallback method).
        Only scans Kubernetes certificate directories.
        
        Returns:
            Dictionary mapping certificate names to paths
        """
        discovered = {}
        
        # Only scan known Kubernetes certificate directories
        k8s_cert_dirs = [
            self.cert_base_path,  # /etc/kubernetes/pki
            Path('/var/lib/minikube/certs'),  # Minikube
            Path('/etc/kubernetes/pki'),  # Standard kubeadm
        ]
        
        for cert_dir in k8s_cert_dirs:
            if cert_dir.exists() and self._is_kubernetes_cert_directory(cert_dir):
                logger.info(f"🔍 Searching Kubernetes certificate directory: {cert_dir}")
                dir_certs = self._find_certificates_in_directory(cert_dir)
                discovered.update(dir_certs)
        
        return discovered
    
    def _get_fallback_cert_paths(self) -> Dict[str, Path]:
        """
        Get fallback certificate paths (standard kubeadm locations).
        
        Returns:
            Dictionary mapping certificate names to paths
        """
        fallback = {}
        
        # Standard kubeadm certificate paths
        standard_paths = {
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
        
        for name, path_str in standard_paths.items():
            path = Path(path_str)
            if path.exists():
                fallback[name] = path
        
        return fallback
    
    def _scan_certificate(self, cert_name: str, cert_path: Path) -> Optional[Dict[str, Any]]:
        """
        Scan a single certificate file.
        
        Args:
            cert_name: Name of the certificate
            cert_path: Path to certificate file
            
        Returns:
            Certificate information dictionary or None
        """
        if not cert_path or not cert_path.exists():
            logger.warning(f"Certificate not found: {cert_name} at {cert_path}")
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
