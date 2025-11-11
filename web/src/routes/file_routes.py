"""
Path Traversal Routes

Implements intentionally vulnerable file reading endpoints for NGFW testing.
Demonstrates path traversal vulnerabilities.

SECURITY WARNING: This code contains INTENTIONAL vulnerabilities for testing purposes.
NEVER use this code in production environments.

Author: NGFW Test Website
Date: November 10, 2025
"""

from flask import Blueprint, request, jsonify, render_template
import logging
import os

# Import services
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.logging_service import get_security_logger

logger = logging.getLogger('app')
security_logger = get_security_logger()

# Create Blueprint
file_bp = Blueprint('file', __name__)


@file_bp.route('/file', methods=['GET'])
def file_viewer_form():
    """
    Display file viewer form
    
    Returns:
        HTML file viewer form
    """
    return render_template('file_viewer.html')


@file_bp.route('/file', methods=['POST'])
def read_file():
    """
    Read and display file contents
    
    VULNERABILITY: Path Traversal
    - Reads files without path sanitization
    - Allows attackers to read arbitrary files: ../../etc/passwd
    
    Returns:
        JSON response with file contents
    """
    try:
        # Get filename parameter
        if request.is_json:
            data = request.get_json()
            filename = data.get('filename', '')
        else:
            filename = request.form.get('filename', '')
        
        if not filename:
            return jsonify({
                'status': 'error',
                'message': 'Filename parameter is required'
            }), 400
        
        # Log file access attempt
        logger.warning(f"File access attempt: {filename}")
        security_logger.warning(
            f"File access",
            extra={
                'filename': filename,
                'ip_address': request.remote_addr or '10.0.0.1',
                'endpoint': '/file'
            }
        )
        
        # VULNERABILITY: Path Traversal
        # No path sanitization - allows reading arbitrary files
        # Attacker can use: ../../etc/passwd
        
        logger.debug(f"Attempting to read file: {filename}")
        
        # Try to read the file
        with open(filename, 'r') as f:
            content = f.read()
        
        logger.info(f"File read successfully: {filename}")
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'content': content,
            'size': len(content)
        }), 200
    
    except FileNotFoundError:
        logger.warning(f"File not found: {filename if 'filename' in locals() else 'unknown'}")
        return jsonify({
            'status': 'error',
            'message': f'File not found: {filename if "filename" in locals() else "unknown"}'
        }), 200  # Return 200 so AJAX can parse JSON
    
    except PermissionError:
        logger.error(f"Permission denied: {filename if 'filename' in locals() else 'unknown'}")
        return jsonify({
            'status': 'error',
            'message': f'Permission denied: {filename if "filename" in locals() else "unknown"}'
        }), 200  # Return 200 so AJAX can parse JSON
    
    except UnicodeDecodeError:
        logger.error(f"Cannot read file (binary or encoding issue): {filename if 'filename' in locals() else 'unknown'}")
        return jsonify({
            'status': 'error',
            'message': 'Cannot read file: File is binary or has encoding issues'
        }), 200  # Return 200 so AJAX can parse JSON
    
    except Exception as e:
        logger.error(f"File read error: {str(e)}")
        security_logger.error(
            f"File read exception",
            extra={
                'error': str(e),
                'filename': filename if 'filename' in locals() else 'unknown'
            }
        )
        
        return jsonify({
            'status': 'error',
            'message': f'File read error: {str(e)}'
        }), 200  # Return 200 so AJAX can parse JSON
