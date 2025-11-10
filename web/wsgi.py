"""
WSGI Entry Point for Production Deployment

This module provides the WSGI application entry point for production
deployment with Gunicorn or other WSGI servers.

Usage with Gunicorn:
    gunicorn --bind 0.0.0.0:5000 wsgi:app
    gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:app
    gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 30 wsgi:app

Usage with uWSGI:
    uwsgi --http 0.0.0.0:5000 --wsgi-file wsgi.py --callable app
"""

import os
import sys

# Add the project directory to the Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Import the Flask application
from app import app

# Expose the application for WSGI servers
application = app

if __name__ == "__main__":
    """
    Run the application directly (for testing)
    
    In production, use a WSGI server like Gunicorn instead.
    """
    app.run(host='0.0.0.0', port=5000)
