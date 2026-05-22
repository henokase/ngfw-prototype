"""
Adaptive NGFW Test Website - Main Application

This is a deliberately vulnerable Flask web application designed to test
the Adaptive NGFW system's detection, inspection, and response capabilities.

WARNING: This application contains intentional security vulnerabilities.
         Never deploy to production or public internet.
         Use only in controlled lab environment.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, jsonify
from config import get_config
from models import db, init_db

# Import middleware
from src.middleware.request_logger import init_request_logger
from src.middleware.security_headers import init_security_headers
from src.middleware.rate_limit import init_rate_limiter

# Import route blueprints
from src.routes.auth_routes import auth_bp
from src.routes.upload_routes import upload_bp
from src.routes.command_routes import cmd_bp
from src.routes.file_routes import file_bp
from src.routes.xss_routes import xss_bp
from src.routes.xml_routes import xml_bp
from src.routes.redirect_routes import redirect_bp
from src.routes.misc_routes import misc_bp

# Initialize Flask application
# Set template and static folders to src/ subdirectories
app = Flask(__name__, 
            template_folder='src/templates',
            static_folder='static')

# Load configuration
config_name = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(get_config(config_name))


def create_directories():
    """
    Create necessary directories for the application
    
    Creates directories for:
    - Database instance
    - Logs
    - File uploads (safe, quarantine, temp)
    """
    directories = [
        'instance',
        'logs',
        app.config['UPLOAD_FOLDER'],
        app.config['QUARANTINE_FOLDER'],
        app.config['TEMP_UPLOAD_FOLDER']
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)


def setup_logging():
    """
    Configure application logging with rotating file handlers
    
    Creates separate log files for general application logs and errors.
    Logs are rotated when they reach 10MB, keeping 5 backup files.
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(app.config['LOG_FILE'])
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set logging level
    log_level = getattr(logging, app.config['LOG_LEVEL'].upper(), logging.INFO)
    app.logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    
    # Application log handler (INFO and above)
    app_handler = RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)
    app.logger.addHandler(app_handler)
    
    # Error log handler (ERROR and above)
    error_handler = RotatingFileHandler(
        app.config['ERROR_LOG_FILE'],
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_BACKUP_COUNT']
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    app.logger.addHandler(error_handler)
    
    # Console handler for development
    if app.config['DEBUG']:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)
    
    app.logger.info('Logging configured successfully')


# Create directories first (before database initialization)
create_directories()

# Setup logging
setup_logging()

# Initialize database (after directories are created)
init_db(app)

# Initialize middleware components
# Order matters: rate_limit -> request_logger -> security_headers
app.logger.info('Initializing middleware components...')

try:
    # Rate limiter (checks before request processing)
    init_rate_limiter(app)
    app.logger.info('[OK] Rate limiter middleware initialized')
except Exception as e:
    app.logger.error(f'Failed to initialize rate limiter: {str(e)}')

try:
    # Request logger (logs all requests and responses)
    init_request_logger(app)
    app.logger.info('[OK] Request logger middleware initialized')
except Exception as e:
    app.logger.error(f'Failed to initialize request logger: {str(e)}')

try:
    # Security headers (adds headers to responses)
    init_security_headers(app)
    app.logger.info('[OK] Security headers middleware initialized')
except Exception as e:
    app.logger.error(f'Failed to initialize security headers: {str(e)}')

app.logger.info('All middleware components initialized successfully')


# ============================================================================
# Route Registration
# ============================================================================
app.logger.info('Registering route blueprints...')

# Register blueprints
app.register_blueprint(misc_bp)  # Misc routes (/, /about, /help, etc.)
app.register_blueprint(auth_bp)  # Authentication routes (/login, /register, etc.)
app.register_blueprint(upload_bp)  # File upload routes (/upload)
app.register_blueprint(cmd_bp)  # Command injection routes (/cmd)
app.register_blueprint(file_bp)  # Path traversal routes (/file)
app.register_blueprint(xss_bp)  # XSS routes (/feedback)
app.register_blueprint(xml_bp)  # XML/XXE routes (/api/xml)
app.register_blueprint(redirect_bp)  # Redirect routes (/redirect)

app.logger.info('[OK] All route blueprints registered successfully')

# Keep the old homepage as fallback (will be overridden by misc_bp)
@app.route('/old_index')
def old_index():
    """
    Old homepage - kept for reference
    
    Returns:
        HTML: Simple homepage
    """
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Adaptive NGFW Test Website</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .header {
                background-color: #2c3e50;
                color: white;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .warning {
                background-color: #e74c3c;
                color: white;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .status {
                background-color: #27ae60;
                color: white;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .info {
                background-color: #3498db;
                color: white;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🛡️ Adaptive NGFW Test Website</h1>
            <p>Deliberately Vulnerable Web Application for Security Testing</p>
        </div>
        
        <div class="warning">
            <h3>⚠️ WARNING</h3>
            <p>This is an intentionally vulnerable application for research purposes.</p>
            <p><strong>Never deploy to production or public internet!</strong></p>
        </div>
        
        <div class="status">
            <h3>✅ Application Status</h3>
            <p><strong>Phase 4 Complete:</strong> Middleware layer implemented</p>
            <p><strong>Flask:</strong> Running</p>
            <p><strong>Database:</strong> Initialized</p>
            <p><strong>Logging:</strong> Active</p>
            <p><strong>Middleware:</strong> Request Logger, Security Headers, Rate Limiter</p>
        </div>
        
        <div class="info">
            <h3>📋 Implementation Progress</h3>
            <p><strong>Completed:</strong></p>
            <ul>
                <li>✅ Phase 1: Project Foundation & Setup</li>
                <li>✅ Phase 2: Core Application Setup</li>
                <li>✅ Phase 3: Services Layer</li>
                <li>✅ Phase 4: Middleware Components</li>
            </ul>
            <p><strong>Next Steps:</strong></p>
            <ul>
                <li>Phase 5: Vulnerable Route Modules</li>
                <li>Phase 6: Frontend Templates</li>
                <li>Phase 7: Testing & Validation</li>
            </ul>
        </div>
        
        <div class="info">
            <h3>🔧 Configuration</h3>
            <p><strong>Environment:</strong> """ + config_name + """</p>
            <p><strong>Debug Mode:</strong> """ + str(app.config['DEBUG']) + """</p>
            <p><strong>Database:</strong> """ + app.config['SQLALCHEMY_DATABASE_URI'] + """</p>
        </div>
    </body>
    </html>
    """


@app.route('/health')
def health():
    """
    Health check endpoint for monitoring
    
    Returns:
        JSON: Application health status
    """
    return jsonify({
        'status': 'healthy',
        'environment': config_name,
        'debug': app.config['DEBUG'],
        'database': 'connected'
    })


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """
    Handle 404 Not Found errors
    
    Args:
        error: Error object
    
    Returns:
        HTML: 404 error page
    """
    app.logger.warning(f'404 error: {request.url}')
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>404 - Not Found</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; }
            h1 { color: #e74c3c; }
        </style>
    </head>
    <body>
        <h1>404 - Page Not Found</h1>
        <p>The requested page does not exist.</p>
        <a href="/">Return to Homepage</a>
    </body>
    </html>
    """, 404


@app.errorhandler(500)
def internal_error(error):
    """
    Handle 500 Internal Server errors
    
    Args:
        error: Error object
    
    Returns:
        HTML: 500 error page
    """
    app.logger.error(f'500 error: {error}')
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>500 - Internal Server Error</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; }
            h1 { color: #e74c3c; }
        </style>
    </head>
    <body>
        <h1>500 - Internal Server Error</h1>
        <p>Something went wrong on the server.</p>
        <a href="/">Return to Homepage</a>
    </body>
    </html>
    """, 500


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == '__main__':
    app.logger.info('Starting Adaptive NGFW Test Website')
    app.logger.info(f'Environment: {config_name}')
    app.logger.info(f'Debug mode: {app.config["DEBUG"]}')
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )
