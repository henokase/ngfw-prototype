"""
Configuration Management for Adaptive NGFW Test Website

This module provides centralized configuration for the Flask application,
loading settings from environment variables and providing defaults.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the base directory of the application
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration class with all settings"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'adaptive_ngfw_secret_key_change_in_production'
    FLASK_APP = os.environ.get('FLASK_APP') or 'app.py'
    FLASK_ENV = os.environ.get('FLASK_ENV') or 'development'
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # Database Configuration
    # Use absolute path for SQLite database (required on Windows)
    default_db_path = os.path.join(basedir, 'instance', 'database.db')
    env_db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
    
    # If environment variable is set and is a relative SQLite path, convert to absolute
    if env_db_uri and env_db_uri.startswith('sqlite:///') and not env_db_uri[10:11] in ['/', '\\']:
        # Relative path detected, convert to absolute
        relative_path = env_db_uri.replace('sqlite:///', '')
        absolute_path = os.path.join(basedir, relative_path)
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{absolute_path}'.replace('\\', '/')
    elif env_db_uri:
        SQLALCHEMY_DATABASE_URI = env_db_uri
    else:
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{default_db_path}'.replace('\\', '/')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True for SQL query debugging
    
    # Upload Configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads/safe'
    QUARANTINE_FOLDER = os.environ.get('QUARANTINE_FOLDER') or 'uploads/quarantine'
    TEMP_UPLOAD_FOLDER = os.environ.get('TEMP_UPLOAD_FOLDER') or '/tmp/uploads'
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH') or 16777216)  # 16MB default
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'exe', 'php', 'jsp'}
    
    # ClamAV Configuration
    CLAMAV_HOST = os.environ.get('CLAMAV_HOST') or 'localhost'
    CLAMAV_PORT = int(os.environ.get('CLAMAV_PORT') or 3310)
    CLAMAV_TIMEOUT = 30  # seconds
    
    # VM1 API Configuration (for adaptive blocking)
    VM1_API_URL = os.environ.get('VM1_API_URL') or 'http://10.0.0.1:5000/api/block_ip'
    VM1_API_KEY = os.environ.get('VM1_API_KEY') or 'your_api_key_here'
    VM1_API_TIMEOUT = 5  # seconds
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'logs/app.log'
    ERROR_LOG_FILE = os.environ.get('ERROR_LOG_FILE') or 'logs/error.log'
    LOG_MAX_BYTES = 10485760  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # Security Configuration (intentionally relaxed for testing)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Middleware Configuration
    ENABLE_RATE_LIMIT = True  # Enable rate limiting
    RATE_LIMIT_PER_MINUTE = 100  # Max requests per minute per IP
    ENABLE_SECURITY_HEADERS = True  # Enable security headers
    ENABLE_REQUEST_LOGGING = True  # Enable request logging to database


class DevelopmentConfig(Config):
    """Development-specific configuration"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True  # Show SQL queries in development


class ProductionConfig(Config):
    """Production-specific configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # Require HTTPS in production


class TestingConfig(Config):
    """Testing-specific configuration"""
    TESTING = True
    test_db_path = os.path.join(basedir, 'instance', 'test_database.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{test_db_path}'.replace('\\', '/')
    WTF_CSRF_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """
    Get configuration object based on environment
    
    Args:
        config_name: Configuration name ('development', 'production', 'testing')
                    If None, uses FLASK_ENV environment variable
    
    Returns:
        Configuration class
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    return config.get(config_name, DevelopmentConfig)
