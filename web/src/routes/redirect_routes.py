"""
Redirect Routes

Implements intentionally vulnerable redirect endpoints for NGFW testing.
Demonstrates open redirect vulnerabilities.

SECURITY WARNING: This code contains INTENTIONAL vulnerabilities for testing purposes.
NEVER use this code in production environments.

Author: NGFW Test Website
Date: November 10, 2025
"""

from flask import Blueprint, request, jsonify, render_template, redirect
import logging

# Import services
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.logging_service import get_security_logger

logger = logging.getLogger('app')
security_logger = get_security_logger()

# Create Blueprint
redirect_bp = Blueprint('redirect', __name__)


@redirect_bp.route('/redirect', methods=['GET'])
def redirect_page():
    """
    Handle redirect with user-supplied URL
    
    VULNERABILITY: Open Redirect
    - Redirects to user-supplied URL without validation
    - Allows phishing attacks: /redirect?url=http://malicious.com
    
    Returns:
        Redirect to specified URL
    """
    try:
        # Get URL parameter
        url = request.args.get('url', '')
        
        if not url:
            # Show redirect form if no URL provided
            return render_template('redirect.html')
        
        # Log redirect attempt
        logger.warning(f"Redirect attempt to: {url}")
        security_logger.warning(
            f"Open redirect",
            extra={
                'target_url': url,
                'ip_address': request.remote_addr or '10.0.0.1',
                'endpoint': '/redirect',
                'referer': request.headers.get('Referer', 'None')
            }
        )
        
        # VULNERABILITY: Open Redirect
        # No URL validation - redirects to any URL
        # Attacker can use: /redirect?url=http://malicious.com
        
        logger.debug(f"Redirecting to: {url}")
        
        return redirect(url)
    
    except Exception as e:
        logger.error(f"Redirect error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Redirect error: {str(e)}'
        }), 500
