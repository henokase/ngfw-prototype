"""
Command Injection Routes

Implements intentionally vulnerable command execution endpoints for NGFW testing.
Demonstrates command injection vulnerabilities.

SECURITY WARNING: This code contains INTENTIONAL vulnerabilities for testing purposes.
NEVER use this code in production environments.

Author: NGFW Test Website
Date: November 10, 2025
"""

from flask import Blueprint, request, jsonify, render_template
import logging
import subprocess
import os

# Import services
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.logging_service import get_security_logger

logger = logging.getLogger('app')
security_logger = get_security_logger()

# Create Blueprint
cmd_bp = Blueprint('cmd', __name__)


@cmd_bp.route('/cmd', methods=['GET'])
def command_form():
    """
    Display command execution form (ping test)
    
    Returns:
        HTML command form
    """
    return render_template('command.html')


@cmd_bp.route('/cmd', methods=['POST'])
def execute_command():
    """
    Execute system command with user input
    
    VULNERABILITY: Command Injection
    - Executes user input directly without sanitization
    - Allows attackers to inject commands: whoami; ls -la
    
    Returns:
        JSON response with command output
    """
    try:
        # Get command parameter (accept any command, not just host/IP)
        if request.is_json:
            data = request.get_json()
            command_input = data.get('command', data.get('host', ''))
        else:
            command_input = request.form.get('command', request.form.get('host', ''))
        
        if not command_input:
            return jsonify({
                'status': 'error',
                'message': 'Command parameter is required'
            }), 400
        
        # Log command attempt
        logger.warning(f"Command execution attempt: {command_input}")
        security_logger.warning(
            f"Command execution",
            extra={
                'command': command_input,
                'ip_address': request.remote_addr or '10.0.0.1',
                'endpoint': '/cmd'
            }
        )
        
        # VULNERABILITY: Command Injection
        # Execute user input directly with shell=True
        # Allows any shell command: whoami, ls, cat, etc.
        command = command_input
        
        logger.debug(f"Executing command: {command}")
        
        # Execute vulnerable command
        result = subprocess.run(
            command,
            shell=True,  # VULNERABLE: Allows command injection
            capture_output=True,
            text=True,
            timeout=10
        )
        
        output = result.stdout + result.stderr
        
        logger.info(f"Command executed successfully")
        
        return jsonify({
            'status': 'success',
            'command': command,
            'output': output,
            'return_code': result.returncode
        }), 200
    
    except subprocess.TimeoutExpired:
        logger.error("Command execution timeout")
        return jsonify({
            'status': 'error',
            'message': 'Command execution timeout (10 seconds)'
        }), 408
    
    except Exception as e:
        logger.error(f"Command execution error: {str(e)}")
        security_logger.error(
            f"Command execution exception",
            extra={
                'error': str(e),
                'host': host if 'host' in locals() else 'unknown'
            }
        )
        
        return jsonify({
            'status': 'error',
            'message': f'Command execution error: {str(e)}'
        }), 500
