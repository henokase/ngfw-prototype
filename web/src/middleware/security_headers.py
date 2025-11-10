"""
Security Headers Middleware

Adds basic security headers to HTTP responses.
Intentionally relaxed for testing XSS and other vulnerabilities.

Author: NGFW Test Website
Date: November 10, 2025
"""

from flask import request
import logging

logger = logging.getLogger('app')


def init_security_headers(app):
    """
    Initialize security headers middleware
    
    Args:
        app: Flask application instance
    """
    
    # Get configuration
    enable_headers = app.config.get('ENABLE_SECURITY_HEADERS', True)
    
    if not enable_headers:
        logger.info("Security headers middleware disabled")
        return
    
    @app.after_request
    def add_security_headers(response):
        """
        Add security headers to response
        
        Args:
            response: Flask response object
            
        Returns:
            Response object with added headers
        """
        try:
            # Skip for static files
            if request.path.startswith('/static/'):
                return response
            
            # X-Content-Type-Options: Prevents MIME type sniffing
            response.headers['X-Content-Type-Options'] = 'nosniff'
            
            # X-Frame-Options: Prevents clickjacking
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            
            # Content-Security-Policy: INTENTIONALLY RELAXED for XSS testing
            # In production, this should be much stricter
            # We're allowing unsafe-inline and unsafe-eval to enable XSS attacks
            csp = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; "
                "style-src 'self' 'unsafe-inline' https:; "
                "img-src 'self' data: https:; "
                "font-src 'self' data: https:; "
                "connect-src 'self' https:; "
            )
            response.headers['Content-Security-Policy'] = csp
            
            # X-XSS-Protection: Deprecated but included for comparison
            # Modern browsers ignore this in favor of CSP
            # Setting to 0 to disable browser XSS filtering (for testing)
            response.headers['X-XSS-Protection'] = '0'
            
            # Referrer-Policy: Control referrer information
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Permissions-Policy: Control browser features
            # Relaxed for testing purposes
            response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
            
            # Log that headers were added (only once per session to avoid spam)
            if not hasattr(add_security_headers, 'logged'):
                logger.info("Security headers added to responses (relaxed for testing)")
                add_security_headers.logged = True
            
        except Exception as e:
            # Don't let header errors break the response
            logger.error(f"Error adding security headers: {str(e)}")
        
        return response


def get_security_headers_config():
    """
    Get current security headers configuration
    
    Returns:
        Dictionary with header configuration
    """
    return {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'Content-Security-Policy': 'RELAXED (allows unsafe-inline, unsafe-eval)',
        'X-XSS-Protection': '0 (disabled for testing)',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        'Note': 'Headers are intentionally relaxed to allow XSS and other attacks for NGFW testing'
    }


def validate_response_headers(response):
    """
    Validate that security headers are present in response
    
    Args:
        response: Flask response object
        
    Returns:
        Dictionary with validation results
    """
    expected_headers = [
        'X-Content-Type-Options',
        'X-Frame-Options',
        'Content-Security-Policy',
        'X-XSS-Protection',
        'Referrer-Policy'
    ]
    
    results = {}
    for header in expected_headers:
        results[header] = header in response.headers
    
    return {
        'all_present': all(results.values()),
        'headers': results
    }
