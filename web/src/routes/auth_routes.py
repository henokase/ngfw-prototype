"""
Authentication Routes

Implements intentionally vulnerable authentication endpoints for NGFW testing.
Demonstrates SQL injection vulnerabilities.

SECURITY WARNING: This code contains INTENTIONAL vulnerabilities for testing purposes.
NEVER use this code in production environments.

Author: NGFW Test Website
Date: November 10, 2025
"""

from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from datetime import datetime
import logging

# Import services
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.database_service import execute_raw_query, get_user_by_username
from src.services.logging_service import get_security_logger
from models import db, User

logger = logging.getLogger('app')
security_logger = get_security_logger()

# Create Blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET'])
def login_form():
    """
    Display login form
    
    Returns:
        HTML login form
    """
    return render_template('login.html')


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Process login request with INTENTIONAL SQL injection vulnerability
    
    VULNERABILITY: SQL Injection
    - Uses raw SQL query without parameterization
    - Allows attackers to bypass authentication with: admin' OR '1'='1'--
    
    Returns:
        JSON response with login status
    """
    try:
        # Get credentials from request
        if request.is_json:
            data = request.get_json()
            username = data.get('username', '')
            password = data.get('password', '')
        else:
            username = request.form.get('username', '')
            password = request.form.get('password', '')
        
        # Log login attempt
        logger.info(f"Login attempt for username: {username}")
        security_logger.warning(
            f"Login attempt",
            extra={
                'username': username,
                'ip_address': request.remote_addr or '10.0.0.1',
                'endpoint': '/login',
                'method': 'POST'
            }
        )
        
        # VULNERABILITY: SQL Injection - Using raw SQL query
        # This allows attacks like: username = "admin' OR '1'='1'--"
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        
        logger.debug(f"Executing SQL query: {query}")
        
        # Execute vulnerable query
        result = execute_raw_query(query)
        
        if result and len(result) > 0:
            # Login successful
            user_data = result[0]
            
            # Set session
            session['username'] = user_data.get('username', username)
            session['user_id'] = user_data.get('id')
            session['logged_in'] = True
            
            logger.info(f"Login successful for user: {username}")
            security_logger.info(
                f"Successful login",
                extra={
                    'username': username,
                    'ip_address': request.remote_addr or '10.0.0.1',
                    'result': 'success'
                }
            )
            
            # Return success response
            if request.is_json:
                return jsonify({
                    'status': 'success',
                    'message': 'Login successful',
                    'username': session['username']
                }), 200
            else:
                return redirect(url_for('misc.index'))
        else:
            # Login failed
            logger.warning(f"Login failed for username: {username}")
            security_logger.warning(
                f"Failed login attempt",
                extra={
                    'username': username,
                    'ip_address': request.remote_addr or '10.0.0.1',
                    'result': 'failed'
                }
            )
            
            if request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid username or password'
                }), 401
            else:
                return render_template('login.html', error='Invalid username or password')
    
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        security_logger.error(
            f"Login exception",
            extra={
                'error': str(e),
                'username': username if 'username' in locals() else 'unknown'
            }
        )
        
        if request.is_json:
            return jsonify({
                'status': 'error',
                'message': f'Login error: {str(e)}'
            }), 500
        else:
            return render_template('login.html', error=f'Error: {str(e)}')


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """
    Logout current user
    
    Returns:
        Redirect to homepage or JSON response
    """
    username = session.get('username', 'unknown')
    
    # Clear session
    session.clear()
    
    logger.info(f"User logged out: {username}")
    
    if request.is_json:
        return jsonify({
            'status': 'success',
            'message': 'Logged out successfully'
        }), 200
    else:
        return redirect(url_for('misc.index'))


@auth_bp.route('/register', methods=['GET'])
def register_form():
    """
    Display registration form
    
    Returns:
        HTML registration form
    """
    return render_template('register.html')


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register new user
    
    Note: This is a basic implementation for testing.
    In a real application, passwords should be hashed.
    
    Returns:
        JSON response with registration status
    """
    try:
        # Get registration data
        if request.is_json:
            data = request.get_json()
            username = data.get('username', '')
            password = data.get('password', '')
            email = data.get('email', '')
        else:
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            email = request.form.get('email', '')
        
        # Validate input
        if not username or not password:
            return jsonify({
                'status': 'error',
                'message': 'Username and password are required'
            }), 400
        
        # Check if user already exists
        existing_user = get_user_by_username(username)
        if existing_user:
            return jsonify({
                'status': 'error',
                'message': 'Username already exists'
            }), 400
        
        # Create new user
        # WARNING: In production, ALWAYS hash passwords!
        new_user = User(
            username=username,
            password=password,  # INSECURE: Storing plain text password for testing
            email=email
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        logger.info(f"New user registered: {username}")
        
        # Auto-login after registration
        session['username'] = username
        session['user_id'] = new_user.id
        session['logged_in'] = True
        
        if request.is_json:
            return jsonify({
                'status': 'success',
                'message': 'Registration successful',
                'username': username
            }), 201
        else:
            return redirect(url_for('misc.index'))
    
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.session.rollback()
        
        if request.is_json:
            return jsonify({
                'status': 'error',
                'message': f'Registration error: {str(e)}'
            }), 500
        else:
            return render_template('register.html', error=f'Error: {str(e)}')


@auth_bp.route('/profile', methods=['GET'])
def profile():
    """
    Display user profile (requires login)
    
    Returns:
        User profile page or error
    """
    if 'logged_in' not in session or not session['logged_in']:
        if request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Not logged in'
            }), 401
        else:
            return redirect(url_for('auth.login'))
    
    username = session.get('username', 'Unknown')
    user_id = session.get('user_id')
    
    if request.is_json:
        return jsonify({
            'status': 'success',
            'username': username,
            'user_id': user_id
        }), 200
    else:
        return render_template('profile.html', username=username, user_id=user_id)
