"""
Database Models for Adaptive NGFW Test Website

This module defines all database models using SQLAlchemy ORM.
Models track users, feedback, uploaded files, and log events.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy instance
db = SQLAlchemy()


class User(db.Model):
    """
    User model for authentication testing
    
    Note: Passwords are stored in plain text intentionally for SQL injection testing.
    This is a VULNERABLE implementation for testing purposes only.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)  # Plain text - VULNERABLE
    email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to feedback
    feedbacks = db.relationship('Feedback', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Feedback(db.Model):
    """
    Feedback model for XSS testing
    
    Note: Feedback messages are not sanitized, allowing for stored XSS attacks.
    This is intentionally vulnerable for testing purposes.
    """
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Feedback {self.id} by User {self.user_id}>'
    
    def to_dict(self):
        """Convert feedback object to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UploadedFile(db.Model):
    """
    UploadedFile model for tracking file uploads and ClamAV scan results
    
    This model stores information about uploaded files, including:
    - File metadata (name, path)
    - ClamAV scan results (clean/infected/error)
    - Malware signature if detected
    - Uploader IP address for adaptive blocking
    """
    __tablename__ = 'uploaded_files'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    scan_status = db.Column(db.String(20), nullable=False, index=True)  # 'clean', 'infected', 'error'
    scan_result = db.Column(db.Text, nullable=True)  # Detailed scan result from ClamAV
    signature_name = db.Column(db.String(255), nullable=True, index=True)  # Malware signature name
    uploader_ip = db.Column(db.String(45), nullable=True, index=True)  # IPv4 or IPv6 address
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<UploadedFile {self.filename} - {self.scan_status}>'
    
    def to_dict(self):
        """Convert uploaded file object to dictionary"""
        return {
            'id': self.id,
            'filename': self.filename,
            'filepath': self.filepath,
            'scan_status': self.scan_status,
            'scan_result': self.scan_result,
            'signature_name': self.signature_name,
            'uploader_ip': self.uploader_ip,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None
        }


class LogEvent(db.Model):
    """
    LogEvent model for tracking all HTTP requests and events
    
    This model logs all incoming requests for analysis by the NGFW system,
    including IP addresses, endpoints, methods, and payloads.
    """
    __tablename__ = 'log_events'
    
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=True, index=True)  # IPv4 or IPv6
    endpoint = db.Column(db.String(255), nullable=False, index=True)
    method = db.Column(db.String(10), nullable=False)  # GET, POST, PUT, DELETE, etc.
    payload = db.Column(db.Text, nullable=True)  # Request data (form data, JSON, etc.)
    user_agent = db.Column(db.String(512), nullable=True)
    status_code = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<LogEvent {self.method} {self.endpoint} from {self.ip_address}>'
    
    def to_dict(self):
        """Convert log event object to dictionary"""
        return {
            'id': self.id,
            'ip_address': self.ip_address,
            'endpoint': self.endpoint,
            'method': self.method,
            'payload': self.payload,
            'user_agent': self.user_agent,
            'status_code': self.status_code,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


def init_db(app):
    """
    Initialize database with the Flask app
    
    Args:
        app: Flask application instance
    """
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create seed data if database is empty
        if User.query.count() == 0:
            seed_database()


def seed_database():
    """
    Seed the database with initial test data
    
    Creates test users for SQL injection testing.
    Passwords are intentionally stored in plain text.
    """
    test_users = [
        User(username='admin', password='admin123', email='admin@testsite.local'),
        User(username='user', password='password', email='user@testsite.local'),
        User(username='test', password='test123', email='test@testsite.local'),
        User(username='guest', password='guest', email='guest@testsite.local')
    ]
    
    for user in test_users:
        db.session.add(user)
    
    try:
        db.session.commit()
        print("Database seeded successfully with test users")
    except Exception as e:
        db.session.rollback()
        print(f"Error seeding database: {e}")
