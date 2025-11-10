"""
Request Logger Middleware

Logs all incoming HTTP requests for traffic analysis and attack detection.
Captures request details and stores them in the database.

Author: NGFW Test Website
Date: November 10, 2025
"""

from flask import request, g
from datetime import datetime
import logging
import json

# Import services
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.database_service import create_log_event
from src.services.utils import truncate_string

logger = logging.getLogger('app')


def init_request_logger(app):
    """
    Initialize request logging middleware
    
    Args:
        app: Flask application instance
    """
    
    @app.before_request
    def log_request_start():
        """
        Log request start time and details before processing
        """
        # Store request start time in Flask's g object
        g.request_start_time = datetime.utcnow()
        
        # Skip logging for static files (optional optimization)
        if request.path.startswith('/static/'):
            return
        
        # Extract request details
        # VM2 only sees VM1's IP (10.0.0.1) - real IPs are handled by VM1
        ip_address = request.remote_addr or '10.0.0.1'
        method = request.method
        endpoint = request.path
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        # Log to console/file
        logger.info(
            f"Request: {method} {endpoint} from {ip_address}",
            extra={
                'ip_address': ip_address,
                'method': method,
                'endpoint': endpoint,
                'user_agent': user_agent
            }
        )
    
    @app.after_request
    def log_request_end(response):
        """
        Log request completion and store in database
        
        Args:
            response: Flask response object
            
        Returns:
            Response object (unchanged)
        """
        # Skip logging for static files
        if request.path.startswith('/static/'):
            return response
        
        try:
            # Extract request details
            # VM2 only sees VM1's IP (10.0.0.1) - real IPs are handled by VM1
            ip_address = request.remote_addr or '10.0.0.1'
            method = request.method
            endpoint = request.path
            user_agent = request.headers.get('User-Agent', 'Unknown')
            status_code = response.status_code
            
            # Capture request payload
            payload = None
            if method in ['POST', 'PUT', 'PATCH']:
                try:
                    # Try to get form data
                    if request.form:
                        payload = json.dumps(dict(request.form))
                    # Try to get JSON data
                    elif request.is_json:
                        payload = json.dumps(request.get_json())
                    # Try to get raw data
                    elif request.data:
                        payload = request.data.decode('utf-8', errors='ignore')
                except Exception as e:
                    logger.warning(f"Could not capture payload: {str(e)}")
                    payload = "[Could not capture payload]"
            
            # Also capture query parameters for GET requests
            if method == 'GET' and request.args:
                payload = json.dumps(dict(request.args))
            
            # Truncate payload if too long (max 1000 chars)
            if payload:
                payload = truncate_string(payload, max_length=1000)
            
            # Calculate request duration
            duration = None
            if hasattr(g, 'request_start_time'):
                duration = (datetime.utcnow() - g.request_start_time).total_seconds()
            
            # Get session ID (for unauthenticated users)
            from flask import session
            session_id = session.get('session_id') if 'session_id' in session else None
            
            # Get username (for authenticated users)
            username = session.get('username') if 'username' in session else None
            
            # Get upload result if this was a file upload
            upload_result = g.get('upload_result') if hasattr(g, 'upload_result') else None
            filename = g.get('upload_filename') if hasattr(g, 'upload_filename') else None
            file_hash = g.get('upload_file_hash') if hasattr(g, 'upload_file_hash') else None
            
            # Store in database
            create_log_event(
                ip_address=ip_address,
                endpoint=endpoint,
                method=method,
                payload=payload,
                user_agent=truncate_string(user_agent, max_length=500),
                status_code=status_code,
                session_id=session_id,
                username=username,
                upload_result=upload_result,
                filename=filename,
                file_hash=file_hash,
                response_time=duration
            )
            
            # Log completion
            logger.info(
                f"Response: {status_code} for {method} {endpoint} "
                f"({duration:.3f}s)" if duration else f"Response: {status_code} for {method} {endpoint}",
                extra={
                    'ip_address': ip_address,
                    'method': method,
                    'endpoint': endpoint,
                    'status_code': status_code,
                    'duration': duration
                }
            )
            
        except Exception as e:
            # Don't let logging errors break the request
            logger.error(f"Error logging request: {str(e)}")
        
        return response


def get_request_stats():
    """
    Get statistics about logged requests
    
    Returns:
        Dictionary with request statistics
    """
    try:
        from models import LogEvent
        
        total_requests = LogEvent.query.count()
        
        # Count by method
        methods = {}
        for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
            count = LogEvent.query.filter_by(method=method).count()
            if count > 0:
                methods[method] = count
        
        # Count by status code range
        status_codes = {
            '2xx': LogEvent.query.filter(LogEvent.status_code >= 200, LogEvent.status_code < 300).count(),
            '3xx': LogEvent.query.filter(LogEvent.status_code >= 300, LogEvent.status_code < 400).count(),
            '4xx': LogEvent.query.filter(LogEvent.status_code >= 400, LogEvent.status_code < 500).count(),
            '5xx': LogEvent.query.filter(LogEvent.status_code >= 500, LogEvent.status_code < 600).count(),
        }
        
        return {
            'total_requests': total_requests,
            'methods': methods,
            'status_codes': status_codes
        }
    except Exception as e:
        logger.error(f"Error getting request stats: {str(e)}")
        return {
            'total_requests': 0,
            'methods': {},
            'status_codes': {},
            'error': str(e)
        }


def get_recent_requests(limit=10):
    """
    Get recent logged requests
    
    Args:
        limit: Maximum number of requests to return
        
    Returns:
        List of recent LogEvent objects
    """
    try:
        from models import LogEvent
        return LogEvent.query.order_by(LogEvent.timestamp.desc()).limit(limit).all()
    except Exception as e:
        logger.error(f"Error getting recent requests: {str(e)}")
        return []
