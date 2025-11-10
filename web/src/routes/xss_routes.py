"""
XSS (Cross-Site Scripting) Routes

Implements intentionally vulnerable feedback/comment endpoints for NGFW testing.
Demonstrates stored and reflected XSS vulnerabilities.

SECURITY WARNING: This code contains INTENTIONAL vulnerabilities for testing purposes.
NEVER use this code in production environments.

Author: NGFW Test Website
Date: November 10, 2025
"""

from flask import Blueprint, request, jsonify, render_template, Markup
import logging

# Import services
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.database_service import safe_add
from src.services.logging_service import get_security_logger
from models import db, Feedback

logger = logging.getLogger('app')
security_logger = get_security_logger()

# Create Blueprint
xss_bp = Blueprint('xss', __name__)


@xss_bp.route('/feedback', methods=['GET'])
def feedback_page():
    """
    Display feedback form and all feedback entries
    
    VULNERABILITY: Stored XSS
    - Displays feedback without HTML escaping
    
    Returns:
        HTML feedback page with all entries
    """
    try:
        # Get search parameter for reflected XSS
        search_query = request.args.get('search', '')
        
        # Get all feedback entries
        if search_query:
            # VULNERABILITY: Reflected XSS in search
            feedback_entries = Feedback.query.filter(
                Feedback.message.contains(search_query)
            ).order_by(Feedback.created_at.desc()).all()
        else:
            feedback_entries = Feedback.query.order_by(Feedback.created_at.desc()).all()
        
        # VULNERABILITY: Stored XSS
        # The template will render feedback without escaping using | safe filter
        return render_template(
            'feedback.html',
            feedback_entries=feedback_entries,
            search_query=Markup(search_query)  # VULNERABLE: Reflected XSS
        )
    
    except Exception as e:
        logger.error(f"Error loading feedback page: {str(e)}")
        return render_template('error.html', error=str(e))


@xss_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    """
    Submit new feedback
    
    VULNERABILITY: Stored XSS
    - Stores user input without sanitization
    - Will be displayed without HTML escaping
    
    Returns:
        JSON response or redirect
    """
    try:
        # Get feedback data
        if request.is_json:
            data = request.get_json()
            name = data.get('name', 'Anonymous')
            message = data.get('message', '')
        else:
            name = request.form.get('name', 'Anonymous')
            message = request.form.get('message', '')
        
        if not message:
            return jsonify({
                'status': 'error',
                'message': 'Feedback message is required'
            }), 400
        
        # Log feedback submission
        logger.info(f"Feedback submitted by: {name}")
        security_logger.info(
            f"Feedback submission",
            extra={
                'name': name,
                'message_length': len(message),
                'ip_address': request.remote_addr or '10.0.0.1'
            }
        )
        
        # VULNERABILITY: Stored XSS
        # No sanitization of user input
        # Malicious scripts will be stored and executed when displayed
        feedback = Feedback(
            name=name,
            message=message  # VULNERABLE: No HTML escaping
        )
        
        if safe_add(feedback):
            logger.info(f"Feedback saved to database")
            
            if request.is_json:
                return jsonify({
                    'status': 'success',
                    'message': 'Feedback submitted successfully',
                    'id': feedback.id
                }), 201
            else:
                # Redirect back to feedback page
                return render_template(
                    'success.html',
                    message='Feedback submitted successfully!',
                    redirect_url='/feedback'
                )
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to save feedback'
            }), 500
    
    except Exception as e:
        logger.error(f"Feedback submission error: {str(e)}")
        db.session.rollback()
        
        if request.is_json:
            return jsonify({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }), 500
        else:
            return render_template('error.html', error=str(e))


@xss_bp.route('/feedback/<int:feedback_id>', methods=['GET'])
def view_feedback(feedback_id):
    """
    View single feedback entry
    
    Returns:
        JSON or HTML with feedback details
    """
    try:
        feedback = Feedback.query.get_or_404(feedback_id)
        
        if request.is_json or request.args.get('format') == 'json':
            return jsonify({
                'status': 'success',
                'feedback': feedback.to_dict()
            }), 200
        else:
            return render_template('feedback_detail.html', feedback=feedback)
    
    except Exception as e:
        logger.error(f"Error viewing feedback: {str(e)}")
        
        if request.is_json:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 404
        else:
            return render_template('error.html', error=str(e))


@xss_bp.route('/feedback/<int:feedback_id>', methods=['DELETE'])
def delete_feedback(feedback_id):
    """
    Delete feedback entry
    
    Returns:
        JSON response
    """
    try:
        feedback = Feedback.query.get_or_404(feedback_id)
        
        db.session.delete(feedback)
        db.session.commit()
        
        logger.info(f"Feedback deleted: {feedback_id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Feedback deleted successfully'
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting feedback: {str(e)}")
        db.session.rollback()
        
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
