"""
Logging Service Module

Provides enhanced logging configuration with structured logging for better
analysis and debugging. Creates separate loggers for different components.

Author: NGFW Test Website
Date: November 10, 2025
"""

import logging
import json
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in JSON format for better parsing
    and analysis by NGFW systems.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string
        
        Args:
            record: LogRecord to format
            
        Returns:
            JSON formatted log string
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        # Add extra context if available
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
        if hasattr(record, 'user'):
            log_data['user'] = record.user
        if hasattr(record, 'endpoint'):
            log_data['endpoint'] = record.endpoint
        if hasattr(record, 'method'):
            log_data['method'] = record.method
            
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


class StandardFormatter(logging.Formatter):
    """Standard text formatter for console output"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


def setup_logger(
    name: str,
    log_file: str,
    level: int = logging.INFO,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    use_json: bool = False
) -> logging.Logger:
    """
    Set up a logger with file and console handlers
    
    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level (default: INFO)
        max_bytes: Max size of log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
        use_json: Use JSON formatting (default: False)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(level)
    
    # Choose formatter
    if use_json:
        file_formatter = StructuredFormatter()
    else:
        file_formatter = StandardFormatter()
    
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler (always use standard format)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(StandardFormatter())
    logger.addHandler(console_handler)
    
    return logger


def get_app_logger() -> logging.Logger:
    """
    Get the main application logger
    
    Returns:
        Application logger instance
    """
    return setup_logger(
        name='app',
        log_file='logs/app.log',
        level=logging.INFO
    )


def get_security_logger() -> logging.Logger:
    """
    Get the security events logger (for attack attempts, suspicious activity)
    
    Returns:
        Security logger instance
    """
    return setup_logger(
        name='security',
        log_file='logs/security.log',
        level=logging.WARNING,
        use_json=True  # Use JSON for easier parsing
    )


def get_malware_logger() -> logging.Logger:
    """
    Get the malware detection logger (for ClamAV scan results)
    
    Returns:
        Malware logger instance
    """
    return setup_logger(
        name='malware',
        log_file='logs/malware.log',
        level=logging.INFO,
        use_json=True  # Use JSON for ML training data
    )


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    message: str,
    ip_address: Optional[str] = None,
    user: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a security event with structured context
    
    Args:
        logger: Logger instance to use
        event_type: Type of security event (e.g., 'sql_injection', 'xss_attempt')
        message: Event description
        ip_address: Client IP address
        user: Username if authenticated
        endpoint: Request endpoint
        method: HTTP method
        extra_data: Additional context data
    """
    # Create log record with extra context
    extra = {
        'event_type': event_type,
        'ip_address': ip_address,
        'user': user,
        'endpoint': endpoint,
        'method': method
    }
    
    if extra_data:
        extra.update(extra_data)
    
    logger.warning(message, extra=extra)


def log_malware_detection(
    filename: str,
    scan_status: str,
    signature: Optional[str] = None,
    ip_address: Optional[str] = None,
    file_size: Optional[int] = None
) -> None:
    """
    Log malware detection event for ML training
    
    Args:
        filename: Name of scanned file
        scan_status: 'clean', 'infected', or 'error'
        signature: Malware signature name if infected
        ip_address: Uploader IP address
        file_size: File size in bytes
    """
    logger = get_malware_logger()
    
    log_data = {
        'filename': filename,
        'scan_status': scan_status,
        'signature': signature,
        'ip_address': ip_address,
        'file_size': file_size,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if scan_status == 'infected':
        logger.warning(f"Malware detected: {filename}", extra=log_data)
    else:
        logger.info(f"File scanned: {filename}", extra=log_data)


def log_request(
    method: str,
    endpoint: str,
    ip_address: str,
    user_agent: Optional[str] = None,
    status_code: Optional[int] = None
) -> None:
    """
    Log HTTP request for traffic analysis
    
    Args:
        method: HTTP method
        endpoint: Request endpoint
        ip_address: Client IP address
        user_agent: User agent string
        status_code: Response status code
    """
    logger = get_app_logger()
    
    log_data = {
        'method': method,
        'endpoint': endpoint,
        'ip_address': ip_address,
        'user_agent': user_agent,
        'status_code': status_code
    }
    
    logger.info(f"{method} {endpoint}", extra=log_data)


# Initialize default loggers on module import
app_logger = get_app_logger()
security_logger = get_security_logger()
malware_logger = get_malware_logger()
