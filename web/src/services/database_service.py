"""
Database Service Module

Provides database helper functions and utilities for common database operations.
Includes transaction management, query helpers, and error handling.

Author: NGFW Test Website
Date: November 10, 2025
"""

from typing import List, Dict, Any, Optional, Type
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
import logging

from models import db, User, Feedback, UploadedFile, LogEvent

logger = logging.getLogger('app')


@contextmanager
def db_session():
    """
    Context manager for database sessions with automatic commit/rollback
    
    Usage:
        with db_session() as session:
            user = session.query(User).first()
    
    Yields:
        Database session
    """
    session = db.session
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        session.close()


def safe_add(model_instance: db.Model, commit: bool = True) -> bool:
    """
    Safely add a model instance to the database
    
    Args:
        model_instance: SQLAlchemy model instance to add
        commit: Whether to commit immediately (default: True)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        db.session.add(model_instance)
        if commit:
            db.session.commit()
        logger.info(f"Added {model_instance.__class__.__name__} to database")
        return True
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Integrity error adding {model_instance.__class__.__name__}: {str(e)}")
        return False
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error adding {model_instance.__class__.__name__}: {str(e)}")
        return False


def safe_delete(model_instance: db.Model, commit: bool = True) -> bool:
    """
    Safely delete a model instance from the database
    
    Args:
        model_instance: SQLAlchemy model instance to delete
        commit: Whether to commit immediately (default: True)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        db.session.delete(model_instance)
        if commit:
            db.session.commit()
        logger.info(f"Deleted {model_instance.__class__.__name__} from database")
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error deleting {model_instance.__class__.__name__}: {str(e)}")
        return False


def get_user_by_username(username: str) -> Optional[User]:
    """
    Get user by username
    
    Args:
        username: Username to search for
        
    Returns:
        User instance or None if not found
    """
    try:
        return User.query.filter_by(username=username).first()
    except SQLAlchemyError as e:
        logger.error(f"Error fetching user by username: {str(e)}")
        return None


def get_user_by_id(user_id: int) -> Optional[User]:
    """
    Get user by ID
    
    Args:
        user_id: User ID to search for
        
    Returns:
        User instance or None if not found
    """
    try:
        return User.query.get(user_id)
    except SQLAlchemyError as e:
        logger.error(f"Error fetching user by ID: {str(e)}")
        return None


def create_user(username: str, password: str, email: str) -> Optional[User]:
    """
    Create a new user
    
    Args:
        username: Username
        password: Password (stored as plain text for testing)
        email: Email address
        
    Returns:
        User instance if successful, None otherwise
    """
    try:
        user = User(username=username, password=password, email=email)
        if safe_add(user):
            return user
        return None
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return None


def create_feedback(user_id: int, message: str) -> Optional[Feedback]:
    """
    Create a new feedback entry
    
    Args:
        user_id: ID of user submitting feedback
        message: Feedback message (may contain XSS for testing)
        
    Returns:
        Feedback instance if successful, None otherwise
    """
    try:
        feedback = Feedback(user_id=user_id, message=message)
        if safe_add(feedback):
            return feedback
        return None
    except Exception as e:
        logger.error(f"Error creating feedback: {str(e)}")
        return None


def get_all_feedback(limit: int = 100) -> List[Feedback]:
    """
    Get all feedback entries
    
    Args:
        limit: Maximum number of entries to return (default: 100)
        
    Returns:
        List of Feedback instances
    """
    try:
        return Feedback.query.order_by(Feedback.created_at.desc()).limit(limit).all()
    except SQLAlchemyError as e:
        logger.error(f"Error fetching feedback: {str(e)}")
        return []


def create_uploaded_file(
    filename: str,
    filepath: str,
    scan_status: str,
    scan_result: Optional[str] = None,
    signature_name: Optional[str] = None,
    uploader_ip: Optional[str] = None
) -> Optional[UploadedFile]:
    """
    Create a new uploaded file record
    
    Args:
        filename: Original filename
        filepath: Path where file is stored
        scan_status: 'clean', 'infected', or 'error'
        scan_result: Detailed scan result
        signature_name: Malware signature if infected
        uploader_ip: IP address of uploader
        
    Returns:
        UploadedFile instance if successful, None otherwise
    """
    try:
        uploaded_file = UploadedFile(
            filename=filename,
            filepath=filepath,
            scan_status=scan_status,
            scan_result=scan_result,
            signature_name=signature_name,
            uploader_ip=uploader_ip
        )
        if safe_add(uploaded_file):
            return uploaded_file
        return None
    except Exception as e:
        logger.error(f"Error creating uploaded file record: {str(e)}")
        return None


def get_uploaded_files(status: Optional[str] = None, limit: int = 100) -> List[UploadedFile]:
    """
    Get uploaded files, optionally filtered by status
    
    Args:
        status: Filter by scan status ('clean', 'infected', 'error')
        limit: Maximum number of entries to return (default: 100)
        
    Returns:
        List of UploadedFile instances
    """
    try:
        query = UploadedFile.query
        if status:
            query = query.filter_by(scan_status=status)
        return query.order_by(UploadedFile.uploaded_at.desc()).limit(limit).all()
    except SQLAlchemyError as e:
        logger.error(f"Error fetching uploaded files: {str(e)}")
        return []


def create_log_event(
    ip_address: str,
    endpoint: str,
    method: str,
    payload: Optional[str] = None,
    user_agent: Optional[str] = None,
    status_code: Optional[int] = None,
    session_id: Optional[str] = None,
    username: Optional[str] = None,
    upload_result: Optional[str] = None,
    filename: Optional[str] = None,
    file_hash: Optional[str] = None,
    response_time: Optional[float] = None
) -> Optional[LogEvent]:
    """
    Create a new log event
    
    Args:
        ip_address: Client IP address
        endpoint: Request endpoint
        method: HTTP method
        payload: Request payload/parameters
        user_agent: User agent string
        status_code: Response status code
        session_id: Session ID for unauthenticated users
        username: Username for authenticated users
        upload_result: Upload scan result ('clean', 'infected', 'error')
        filename: Uploaded filename
        file_hash: SHA256 hash of uploaded file
        response_time: Response time in seconds
        
    Returns:
        LogEvent instance if successful, None otherwise
    """
    try:
        log_event = LogEvent(
            ip_address=ip_address,
            endpoint=endpoint,
            method=method,
            payload=payload,
            user_agent=user_agent,
            status_code=status_code,
            session_id=session_id,
            username=username,
            upload_result=upload_result,
            filename=filename,
            file_hash=file_hash,
            response_time=response_time
        )
        if safe_add(log_event):
            return log_event
        return None
    except Exception as e:
        logger.error(f"Error creating log event: {str(e)}")
        return None


def get_log_events(
    ip_address: Optional[str] = None,
    endpoint: Optional[str] = None,
    limit: int = 100
) -> List[LogEvent]:
    """
    Get log events, optionally filtered
    
    Args:
        ip_address: Filter by IP address
        endpoint: Filter by endpoint
        limit: Maximum number of entries to return (default: 100)
        
    Returns:
        List of LogEvent instances
    """
    try:
        query = LogEvent.query
        if ip_address:
            query = query.filter_by(ip_address=ip_address)
        if endpoint:
            query = query.filter_by(endpoint=endpoint)
        return query.order_by(LogEvent.timestamp.desc()).limit(limit).all()
    except SQLAlchemyError as e:
        logger.error(f"Error fetching log events: {str(e)}")
        return []


def get_infected_files_count() -> int:
    """
    Get count of infected files
    
    Returns:
        Number of infected files
    """
    try:
        return UploadedFile.query.filter_by(scan_status='infected').count()
    except SQLAlchemyError as e:
        logger.error(f"Error counting infected files: {str(e)}")
        return 0


def get_recent_attacks(limit: int = 10) -> List[LogEvent]:
    """
    Get recent potential attack attempts (for dashboard)
    
    Args:
        limit: Maximum number of entries to return (default: 10)
        
    Returns:
        List of recent LogEvent instances
    """
    try:
        # Look for common attack patterns in endpoints
        attack_patterns = ['%27', '--', '<script', '../', ';', '|']
        query = LogEvent.query
        
        # Filter for suspicious payloads
        for pattern in attack_patterns:
            query = query.filter(
                (LogEvent.endpoint.contains(pattern)) |
                (LogEvent.payload.contains(pattern))
            )
        
        return query.order_by(LogEvent.timestamp.desc()).limit(limit).all()
    except SQLAlchemyError as e:
        logger.error(f"Error fetching recent attacks: {str(e)}")
        return []


def execute_raw_query(query: str) -> Optional[List[Dict[str, Any]]]:
    """
    Execute a raw SQL query (INTENTIONALLY VULNERABLE for testing)
    
    WARNING: This function is intentionally vulnerable to SQL injection
    for testing purposes. DO NOT use in production!
    
    Args:
        query: SQL query string
        
    Returns:
        List of result dictionaries or None on error
    """
    try:
        result = db.session.execute(query)
        if result.returns_rows:
            return [dict(row) for row in result]
        db.session.commit()
        return []
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error executing raw query: {str(e)}")
        return None
