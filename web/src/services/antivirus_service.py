"""
Antivirus Service Module

Integrates with ClamAV for malware scanning of uploaded files.
Handles file scanning, quarantine, and notification to VM1 API.

Author: NGFW Test Website
Date: November 10, 2025
"""

import os
import shutil
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import requests

try:
    import pyclamd
    PYCLAMD_AVAILABLE = True
except ImportError:
    PYCLAMD_AVAILABLE = False
    logging.warning("PyClamd not available - malware scanning will be simulated")

logger = logging.getLogger('malware')


class AntivirusService:
    """
    Service for scanning files with ClamAV and managing infected files
    """
    
    def __init__(
        self,
        clamd_socket: Optional[str] = None,
        clamd_host: str = 'localhost',
        clamd_port: int = 3310,
        temp_folder: str = '/tmp/uploads',
        quarantine_folder: str = 'uploads/quarantine',
        safe_folder: str = 'uploads/safe',
        vm1_api_url: Optional[str] = None
    ):
        """
        Initialize antivirus service
        
        Args:
            clamd_socket: Path to ClamAV socket (Unix systems)
            clamd_host: ClamAV daemon host (default: localhost)
            clamd_port: ClamAV daemon port (default: 3310)
            temp_folder: Temporary upload folder
            quarantine_folder: Folder for infected files
            safe_folder: Folder for clean files
            vm1_api_url: URL for VM1 API notifications
        """
        self.clamd_socket = clamd_socket
        self.clamd_host = clamd_host
        self.clamd_port = clamd_port
        self.temp_folder = temp_folder
        self.quarantine_folder = quarantine_folder
        self.safe_folder = safe_folder
        self.vm1_api_url = vm1_api_url
        
        # Ensure folders exist
        for folder in [temp_folder, quarantine_folder, safe_folder]:
            if not os.path.exists(folder):
                os.makedirs(folder)
        
        # Initialize ClamAV connection
        self.clamd = self._init_clamd()
    
    def _init_clamd(self) -> Optional[Any]:
        """
        Initialize connection to ClamAV daemon
        
        Returns:
            ClamAV connection object or None if unavailable
        """
        if not PYCLAMD_AVAILABLE:
            logger.warning("PyClamd not installed - using simulation mode")
            return None
        
        try:
            # Try Unix socket first (Linux/Mac)
            if self.clamd_socket and os.path.exists(self.clamd_socket):
                cd = pyclamd.ClamdUnixSocket(self.clamd_socket)
                if cd.ping():
                    logger.info(f"Connected to ClamAV via socket: {self.clamd_socket}")
                    return cd
            
            # Try network connection
            cd = pyclamd.ClamdNetworkSocket(self.clamd_host, self.clamd_port)
            if cd.ping():
                logger.info(f"Connected to ClamAV at {self.clamd_host}:{self.clamd_port}")
                return cd
            
            logger.warning("ClamAV daemon not responding - using simulation mode")
            return None
            
        except Exception as e:
            logger.error(f"Failed to connect to ClamAV: {str(e)}")
            return None
    
    def scan_file(self, filepath: str) -> Dict[str, Any]:
        """
        Scan a file for malware
        
        Args:
            filepath: Path to file to scan
            
        Returns:
            Dictionary with scan results:
            {
                'status': 'clean' | 'infected' | 'error',
                'signature': str (malware signature if infected),
                'details': str (detailed scan result),
                'timestamp': str (ISO format timestamp)
            }
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Check if file exists
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return {
                'status': 'error',
                'signature': None,
                'details': 'File not found',
                'timestamp': timestamp
            }
        
        # If ClamAV is not available, simulate scan
        if not self.clamd:
            return self._simulate_scan(filepath, timestamp)
        
        try:
            # Scan file
            scan_result = self.clamd.scan_file(filepath)
            
            if scan_result is None:
                # File is clean
                logger.info(f"File clean: {filepath}")
                return {
                    'status': 'clean',
                    'signature': None,
                    'details': 'No threats detected',
                    'timestamp': timestamp
                }
            
            # File is infected
            filename = os.path.basename(filepath)
            signature = scan_result[filepath][1] if filepath in scan_result else 'Unknown'
            
            logger.warning(f"Malware detected in {filename}: {signature}")
            return {
                'status': 'infected',
                'signature': signature,
                'details': f"Malware detected: {signature}",
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"Error scanning file {filepath}: {str(e)}")
            return {
                'status': 'error',
                'signature': None,
                'details': f"Scan error: {str(e)}",
                'timestamp': timestamp
            }
    
    def _simulate_scan(self, filepath: str, timestamp: str) -> Dict[str, Any]:
        """
        Simulate malware scan when ClamAV is not available
        
        Args:
            filepath: Path to file
            timestamp: Timestamp string
            
        Returns:
            Simulated scan result
        """
        filename = os.path.basename(filepath).lower()
        
        # Check for EICAR test file
        if 'eicar' in filename:
            logger.warning(f"Simulated malware detection: {filename}")
            return {
                'status': 'infected',
                'signature': 'EICAR-Test-File',
                'details': 'Simulated malware detection (EICAR test file)',
                'timestamp': timestamp
            }
        
        # Check for suspicious extensions
        suspicious_extensions = ['.exe', '.bat', '.cmd', '.sh', '.php', '.jsp', '.asp']
        if any(filename.endswith(ext) for ext in suspicious_extensions):
            logger.warning(f"Simulated malware detection: {filename}")
            return {
                'status': 'infected',
                'signature': 'Suspicious-File-Type',
                'details': f'Simulated malware detection (suspicious extension)',
                'timestamp': timestamp
            }
        
        # Default: file is clean
        logger.info(f"Simulated clean scan: {filename}")
        return {
            'status': 'clean',
            'signature': None,
            'details': 'Simulated scan - no threats detected',
            'timestamp': timestamp
        }
    
    def process_upload(
        self,
        source_path: str,
        filename: str,
        uploader_ip: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Process an uploaded file: scan and move to appropriate folder
        
        Args:
            source_path: Path to uploaded file (in temp folder)
            filename: Original filename
            uploader_ip: IP address of uploader
            
        Returns:
            Tuple of (scan_result dict, destination_path)
        """
        # Scan the file
        scan_result = self.scan_file(source_path)
        
        # Determine destination based on scan result
        if scan_result['status'] == 'infected':
            # Move to quarantine
            dest_folder = self.quarantine_folder
            dest_path = os.path.join(dest_folder, filename)
            
            # Notify VM1 API if configured
            if self.vm1_api_url:
                self._notify_vm1(filename, scan_result, uploader_ip)
        else:
            # Move to safe folder
            dest_folder = self.safe_folder
            dest_path = os.path.join(dest_folder, filename)
        
        # Handle filename conflicts
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(dest_path):
                new_filename = f"{base}_{counter}{ext}"
                dest_path = os.path.join(dest_folder, new_filename)
                counter += 1
        
        # Move file
        try:
            shutil.move(source_path, dest_path)
            logger.info(f"Moved file to: {dest_path}")
        except Exception as e:
            logger.error(f"Error moving file: {str(e)}")
            dest_path = source_path
        
        return scan_result, dest_path
    
    def _notify_vm1(
        self,
        filename: str,
        scan_result: Dict[str, Any],
        uploader_ip: Optional[str]
    ) -> bool:
        """
        Notify VM1 API about malware detection
        
        Args:
            filename: Name of infected file
            scan_result: Scan result dictionary
            uploader_ip: IP address of uploader
            
        Returns:
            True if notification successful, False otherwise
        """
        if not self.vm1_api_url:
            return False
        
        try:
            payload = {
                'event_type': 'malware_detected',
                'filename': filename,
                'signature': scan_result.get('signature'),
                'uploader_ip': uploader_ip,
                'timestamp': scan_result.get('timestamp'),
                'details': scan_result.get('details')
            }
            
            response = requests.post(
                f"{self.vm1_api_url}/malware-alert",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"VM1 notified about malware: {filename}")
                return True
            else:
                logger.warning(f"VM1 notification failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error notifying VM1: {str(e)}")
            return False
    
    def get_version(self) -> Optional[str]:
        """
        Get ClamAV version
        
        Returns:
            Version string or None if unavailable
        """
        if not self.clamd:
            return "Simulation mode (ClamAV not available)"
        
        try:
            return self.clamd.version()
        except Exception as e:
            logger.error(f"Error getting ClamAV version: {str(e)}")
            return None
    
    def reload_database(self) -> bool:
        """
        Reload ClamAV virus database
        
        Returns:
            True if successful, False otherwise
        """
        if not self.clamd:
            logger.warning("Cannot reload database - ClamAV not available")
            return False
        
        try:
            self.clamd.reload()
            logger.info("ClamAV database reloaded")
            return True
        except Exception as e:
            logger.error(f"Error reloading ClamAV database: {str(e)}")
            return False


# Global antivirus service instance
_antivirus_service = None


def get_antivirus_service(
    clamd_socket: Optional[str] = None,
    clamd_host: str = 'localhost',
    clamd_port: int = 3310,
    temp_folder: str = '/tmp/uploads',
    quarantine_folder: str = 'uploads/quarantine',
    safe_folder: str = 'uploads/safe',
    vm1_api_url: Optional[str] = None
) -> AntivirusService:
    """
    Get or create the global antivirus service instance
    
    Returns:
        AntivirusService instance
    """
    global _antivirus_service
    
    if _antivirus_service is None:
        _antivirus_service = AntivirusService(
            clamd_socket=clamd_socket,
            clamd_host=clamd_host,
            clamd_port=clamd_port,
            temp_folder=temp_folder,
            quarantine_folder=quarantine_folder,
            safe_folder=safe_folder,
            vm1_api_url=vm1_api_url
        )
    
    return _antivirus_service


def scan_file(filepath: str) -> Dict[str, Any]:
    """
    Convenience function to scan a file
    
    Args:
        filepath: Path to file to scan
        
    Returns:
        Scan result dictionary
    """
    service = get_antivirus_service()
    return service.scan_file(filepath)


def process_upload(
    source_path: str,
    filename: str,
    uploader_ip: Optional[str] = None
) -> Tuple[Dict[str, Any], str]:
    """
    Convenience function to process an uploaded file
    
    Args:
        source_path: Path to uploaded file
        filename: Original filename
        uploader_ip: IP address of uploader
        
    Returns:
        Tuple of (scan_result, destination_path)
    """
    service = get_antivirus_service()
    return service.process_upload(source_path, filename, uploader_ip)
