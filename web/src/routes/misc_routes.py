"""
Miscellaneous Routes

Implements general purpose endpoints (homepage, about, help, etc.)

Author: NGFW Test Website
Date: November 10, 2025
"""

from flask import Blueprint, request, jsonify, render_template
import logging

# Import services
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.database_service import get_recent_log_events
from models import LogEvent, UploadedFile, Feedback, User

logger = logging.getLogger('app')

# Create Blueprint
misc_bp = Blueprint('misc', __name__)


@misc_bp.route('/', methods=['GET'])
def index():
    """
    Homepage with links to all endpoints
    
    Returns:
        HTML homepage
    """
    return render_template('index.html')


@misc_bp.route('/about', methods=['GET'])
def about():
    """
    About page with project description
    
    Returns:
        HTML about page
    """
    return render_template('about.html')


@misc_bp.route('/help', methods=['GET'])
def help_page():
    """
    Help page with usage instructions
    
    Returns:
        HTML help page
    """
    return render_template('help.html')


@misc_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring
    
    Returns:
        JSON with application health status
    """
    try:
        # Check database connectivity
        log_count = LogEvent.query.count()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'log_events': log_count
        }), 200
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@misc_bp.route('/stats', methods=['GET'])
def statistics():
    """
    Display application statistics
    
    Returns:
        JSON or HTML with statistics
    """
    try:
        # Gather statistics
        stats = {
            'total_requests': LogEvent.query.count(),
            'total_uploads': UploadedFile.query.count(),
            'infected_files': UploadedFile.query.filter_by(scan_result='infected').count(),
            'total_feedback': Feedback.query.count(),
            'total_users': User.query.count()
        }
        
        # Get recent activity
        recent_logs = get_recent_log_events(limit=10)
        
        if request.is_json or request.args.get('format') == 'json':
            return jsonify({
                'status': 'success',
                'statistics': stats,
                'recent_activity': [log.to_dict() for log in recent_logs]
            }), 200
        else:
            return render_template('stats.html', stats=stats, recent_logs=recent_logs)
    
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        
        if request.is_json:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
        else:
            return render_template('error.html', error=str(e))


@misc_bp.route('/success', methods=['GET'])
def success():
    """
    Generic success page
    
    Returns:
        HTML success page
    """
    message = request.args.get('message', 'Operation completed successfully')
    redirect_url = request.args.get('redirect', '/')
    
    return render_template('success.html', message=message, redirect_url=redirect_url)


@misc_bp.route('/error', methods=['GET'])
def error():
    """
    Generic error page
    
    Returns:
        HTML error page
    """
    error_message = request.args.get('error', 'An error occurred')
    
    return render_template('error.html', error=error_message)


@misc_bp.errorhandler(404)
def not_found(error):
    """
    404 error handler
    
    Returns:
        JSON or HTML 404 page
    """
    if request.is_json:
        return jsonify({
            'status': 'error',
            'message': 'Resource not found'
        }), 404
    else:
        return render_template('404.html'), 404


@misc_bp.errorhandler(500)
def internal_error(error):
    """
    500 error handler
    
    Returns:
        JSON or HTML 500 page
    """
    logger.error(f"Internal server error: {str(error)}")
    
    if request.is_json:
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500
    else:
        return render_template('500.html'), 500
