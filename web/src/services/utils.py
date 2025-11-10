"""
Utilities Service Module

Common utility functions used across the application.
Includes path operations, validation, sanitization, and formatting helpers.

Author: NGFW Test Website
Date: November 10, 2025
"""

import os
import re
import hashlib
import mimetypes
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger('app')


def safe_join_path(*paths: str) -> str:
    """
    Safely join path components and normalize the result
    
    Args:
        *paths: Path components to join
        
    Returns:
        Normalized absolute path
    """
    joined = os.path.join(*paths)
    normalized = os.path.normpath(joined)
    absolute = os.path.abspath(normalized)
    return absolute


def is_safe_path(basedir: str, path: str) -> bool:
    """
    Check if a path is within the base directory (prevent path traversal)
    
    Args:
        basedir: Base directory that should contain the path
        path: Path to check
        
    Returns:
        True if path is safe, False otherwise
    """
    basedir = os.path.abspath(basedir)
    path = os.path.abspath(path)
    return path.startswith(basedir)


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename
    
    Args:
        filename: Filename to extract extension from
        
    Returns:
        File extension (lowercase, without dot)
    """
    _, ext = os.path.splitext(filename)
    return ext.lower().lstrip('.')


def is_allowed_file(filename: str, allowed_extensions: set) -> bool:
    """
    Check if file has an allowed extension
    
    Args:
        filename: Filename to check
        allowed_extensions: Set of allowed extensions (without dots)
        
    Returns:
        True if allowed, False otherwise
    """
    ext = get_file_extension(filename)
    return ext in allowed_extensions


def get_mime_type(filename: str) -> Optional[str]:
    """
    Get MIME type for a file
    
    Args:
        filename: Filename to check
        
    Returns:
        MIME type string or None if unknown
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to make it safe for filesystem
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Use werkzeug's secure_filename
    safe_name = secure_filename(filename)
    
    # If empty after sanitization, use a default
    if not safe_name:
        safe_name = 'unnamed_file'
    
    return safe_name


def calculate_file_hash(filepath: str, algorithm: str = 'sha256') -> Optional[str]:
    """
    Calculate hash of a file
    
    Args:
        filepath: Path to file
        algorithm: Hash algorithm (default: sha256)
        
    Returns:
        Hex digest of file hash or None on error
    """
    try:
        hash_obj = hashlib.new(algorithm)
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating file hash: {str(e)}")
        return None


def get_file_size(filepath: str) -> Optional[int]:
    """
    Get file size in bytes
    
    Args:
        filepath: Path to file
        
    Returns:
        File size in bytes or None on error
    """
    try:
        return os.path.getsize(filepath)
    except Exception as e:
        logger.error(f"Error getting file size: {str(e)}")
        return None


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def extract_ip_address(request) -> str:
    """
    Extract client IP address from request, considering proxies
    
    Args:
        request: Flask request object
        
    Returns:
        Client IP address
    """
    # Check for X-Real-IP header (set by nginx)
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    
    # Check for X-Forwarded-For header
    if request.headers.get('X-Forwarded-For'):
        # Get first IP in the chain
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    
    # Fall back to remote_addr
    return request.remote_addr or 'unknown'


def is_valid_ip(ip: str) -> bool:
    """
    Validate IP address format (IPv4)
    
    Args:
        ip: IP address string
        
    Returns:
        True if valid IPv4, False otherwise
    """
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    
    # Check each octet is 0-255
    octets = ip.split('.')
    return all(0 <= int(octet) <= 255 for octet in octets)


def sanitize_input(input_str: str, max_length: int = 1000) -> str:
    """
    Basic input sanitization (for demonstration - intentionally weak)
    
    NOTE: This is intentionally weak for testing purposes.
    In production, use proper validation and escaping.
    
    Args:
        input_str: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    # Truncate to max length
    sanitized = input_str[:max_length]
    
    # Remove null bytes
    sanitized = sanitized.replace('\x00', '')
    
    return sanitized


def escape_html(text: str) -> str:
    """
    Escape HTML special characters
    
    Args:
        text: Text to escape
        
    Returns:
        HTML-escaped text
    """
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&#x27;",
        ">": "&gt;",
        "<": "&lt;",
    }
    return "".join(html_escape_table.get(c, c) for c in text)


def format_timestamp(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format datetime object as string
    
    Args:
        dt: Datetime object
        format_str: Format string (default: YYYY-MM-DD HH:MM:SS)
        
    Returns:
        Formatted datetime string
    """
    return dt.strftime(format_str)


def parse_timestamp(timestamp_str: str, format_str: str = '%Y-%m-%d %H:%M:%S') -> Optional[datetime]:
    """
    Parse timestamp string to datetime object
    
    Args:
        timestamp_str: Timestamp string
        format_str: Format string (default: YYYY-MM-DD HH:MM:SS)
        
    Returns:
        Datetime object or None on error
    """
    try:
        return datetime.strptime(timestamp_str, format_str)
    except ValueError as e:
        logger.error(f"Error parsing timestamp: {str(e)}")
        return None


def create_response(
    success: bool,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    status_code: int = 200
) -> tuple:
    """
    Create standardized JSON response
    
    Args:
        success: Whether operation was successful
        message: Response message
        data: Optional data dictionary
        status_code: HTTP status code
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        'success': success,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if data:
        response['data'] = data
    
    return response, status_code


def truncate_string(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Truncate string to maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def validate_email(email: str) -> bool:
    """
    Validate email address format (basic validation)
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid format, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_username(username: str) -> bool:
    """
    Validate username format
    
    Args:
        username: Username to validate
        
    Returns:
        True if valid, False otherwise
    """
    # 3-20 characters, alphanumeric and underscore only
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return bool(re.match(pattern, username))


def contains_sql_keywords(text: str) -> bool:
    """
    Check if text contains common SQL keywords (for detection, not prevention)
    
    Args:
        text: Text to check
        
    Returns:
        True if SQL keywords found, False otherwise
    """
    sql_keywords = [
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE',
        'ALTER', 'UNION', 'WHERE', 'FROM', 'TABLE', '--', ';',
        'OR 1=1', "' OR '", '" OR "', 'EXEC', 'EXECUTE'
    ]
    
    text_upper = text.upper()
    return any(keyword in text_upper for keyword in sql_keywords)


def contains_xss_patterns(text: str) -> bool:
    """
    Check if text contains common XSS patterns (for detection, not prevention)
    
    Args:
        text: Text to check
        
    Returns:
        True if XSS patterns found, False otherwise
    """
    xss_patterns = [
        '<script', 'javascript:', 'onerror=', 'onload=',
        'onclick=', 'onmouseover=', '<iframe', '<object',
        '<embed', 'eval(', 'alert('
    ]
    
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in xss_patterns)


def contains_command_injection(text: str) -> bool:
    """
    Check if text contains command injection patterns (for detection, not prevention)
    
    Args:
        text: Text to check
        
    Returns:
        True if command injection patterns found, False otherwise
    """
    patterns = [
        ';', '|', '&', '`', '$(',  '&&', '||',
        '\n', '\r', '../', '..\\', '/etc/passwd',
        'cat ', 'ls ', 'rm ', 'wget ', 'curl '
    ]
    
    return any(pattern in text for pattern in patterns)


def log_suspicious_activity(
    activity_type: str,
    details: str,
    ip_address: Optional[str] = None,
    endpoint: Optional[str] = None
) -> None:
    """
    Log suspicious activity for analysis
    
    Args:
        activity_type: Type of suspicious activity
        details: Activity details
        ip_address: Client IP address
        endpoint: Request endpoint
    """
    logger.warning(
        f"Suspicious activity detected: {activity_type}",
        extra={
            'activity_type': activity_type,
            'details': details,
            'ip_address': ip_address,
            'endpoint': endpoint,
            'timestamp': datetime.utcnow().isoformat()
        }
    )
