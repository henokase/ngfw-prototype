"""
File Upload Routes

Implements file upload functionality with ClamAV malware scanning.
Infected files are quarantined locally and logged for the website's own awareness.

SECURITY WARNING: This code contains INTENTIONAL vulnerabilities (no file type validation).
For testing purposes only.

Author: NGFW Test Website
Date: November 10, 2025
"""

from flask import Blueprint, request, jsonify, render_template, g
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
import os
import hashlib

# Import services
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.antivirus_service import scan_file, get_antivirus_service
from src.services.database_service import safe_add
from src.services.logging_service import get_security_logger
from models import db, UploadedFile

logger = logging.getLogger('app')
security_logger = get_security_logger()

# Create Blueprint
upload_bp = Blueprint('upload', __name__)

# Configuration
UPLOAD_ROOT = 'uploads'
TEMP_UPLOAD_FOLDER = '/tmp/uploads'
QUARANTINE_FOLDER = os.path.join(UPLOAD_ROOT, 'quarantine')
SAFE_FOLDER = os.path.join(UPLOAD_ROOT, 'safe')

# Ensure directories exist
os.makedirs(TEMP_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QUARANTINE_FOLDER, exist_ok=True)
os.makedirs(SAFE_FOLDER, exist_ok=True)


def calculate_file_hash(filepath):
    """
    Calculate SHA256 hash of a file
    
    Args:
        filepath: Path to file
        
    Returns:
        SHA256 hash as hex string
    """
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


@upload_bp.route('/upload', methods=['GET'])
def upload_form():
    """
    Display file upload form
    
    Returns:
        HTML upload form
    """
    return render_template('upload.html')


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Handle file upload with malware scanning
    
    VULNERABILITY: No file type validation (intentional for testing)
    
    Workflow:
    1. Save file to /tmp/uploads
    2. Scan with ClamAV
    3. If CLEAN: Move to /uploads/safe/, create DB record
    4. If INFECTED: Move to /uploads/quarantine/, log security event
    5. Set g.upload_result, g.upload_filename, g.upload_file_hash for logging
    
    Returns:
        JSON response with upload status
    """
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        # Check if filename is empty
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400
        
        # VULNERABILITY: No file type validation (intentional)
        # In a secure application, you would validate file types here
        
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Save to temporary location
        temp_filepath = os.path.join(TEMP_UPLOAD_FOLDER, filename)
        file.save(temp_filepath)
        
        logger.info(f"File uploaded to temp: {filename}")
        
        # Calculate file hash
        file_hash = calculate_file_hash(temp_filepath)
        logger.info(f"File hash: {file_hash}")
        
        # Scan file with ClamAV
        av_service = get_antivirus_service()
        scan_result = av_service.scan_file(temp_filepath)
        
        logger.info(f"Scan result for {filename}: {scan_result['status']}")
        
        if scan_result['status'] == 'clean':
            # File is clean - move to safe folder
            safe_filepath = os.path.join(SAFE_FOLDER, filename)
            
            # Handle duplicate filenames
            counter = 1
            while os.path.exists(safe_filepath):
                name, ext = os.path.splitext(filename)
                safe_filepath = os.path.join(SAFE_FOLDER, f"{name}_{counter}{ext}")
                counter += 1
            
            os.rename(temp_filepath, safe_filepath)
            
            logger.info(f"Clean file moved to: {safe_filepath}")
            
            # Create database record
            uploaded_file = UploadedFile(
                filename=filename,
                filepath=safe_filepath,
                scan_status='clean',
                scan_result=scan_result.get('details', 'No threats detected'),
                signature_name=None,
                uploader_ip=request.remote_addr,
            )
            
            if safe_add(uploaded_file):
                logger.info(f"File record created in database: {filename}")
            
            # Set flask.g for request logger middleware
            g.upload_result = 'clean'
            g.upload_filename = filename
            g.upload_file_hash = file_hash
            
            return jsonify({
                'status': 'success',
                'message': 'File uploaded successfully',
                'filename': filename,
                'file_hash': file_hash,
                'scan_result': 'clean'
            }), 200
        
        elif scan_result['status'] == 'infected':
            # File is infected - move to quarantine
            quarantine_filepath = os.path.join(QUARANTINE_FOLDER, filename)
            
            # Handle duplicate filenames
            counter = 1
            while os.path.exists(quarantine_filepath):
                name, ext = os.path.splitext(filename)
                quarantine_filepath = os.path.join(QUARANTINE_FOLDER, f"{name}_{counter}{ext}")
                counter += 1
            
            os.rename(temp_filepath, quarantine_filepath)
            
            signature = scan_result.get('signature', 'Unknown')
            logger.warning(f"Infected file quarantined: {filename} ({signature})")
            
            # Create database record
            uploaded_file = UploadedFile(
                filename=filename,
                filepath=quarantine_filepath,
                scan_status='infected',
                scan_result=scan_result.get('details', f'Malware detected: {signature}'),
                signature_name=signature,
                uploader_ip=request.remote_addr,
            )
            
            if safe_add(uploaded_file):
                logger.info(f"Infected file record created in database: {filename}")
            
            # Set flask.g for request logger middleware
            g.upload_result = 'infected'
            g.upload_filename = filename
            g.upload_file_hash = file_hash
            
            # Log security event
            security_logger.critical(
                f"Malware upload detected",
                extra={
                    'malware_filename': filename,
                    'malware_file_hash': file_hash,
                    'malware_signature': signature,
                    'quarantined': True,
                }
            )
            
            return jsonify({
                'status': 'error',
                'message': 'File is infected and has been quarantined',
                'filename': filename,
                'file_hash': file_hash,
                'scan_result': 'infected',
                'signature': signature,
            }), 400
        
        else:
            # Scan error
            logger.error(f"Scan error for {filename}: {scan_result.get('error', 'Unknown error')}")
            
            # Remove temp file
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            
            # Set flask.g for request logger middleware
            g.upload_result = 'error'
            g.upload_filename = filename
            g.upload_file_hash = file_hash
            
            return jsonify({
                'status': 'error',
                'message': f"Scan error: {scan_result.get('error', 'Unknown error')}",
                'filename': filename
            }), 500
    
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        
        # Clean up temp file if it exists
        if 'temp_filepath' in locals() and os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except:
                pass
        
        return jsonify({
            'status': 'error',
            'message': f'Upload error: {str(e)}'
        }), 500


@upload_bp.route('/uploads', methods=['GET'])
def list_uploads():
    """
    List all uploaded files
    
    Returns:
        JSON list of uploaded files or HTML page
    """
    try:
        # Query all uploaded files
        files = UploadedFile.query.order_by(UploadedFile.upload_date.desc()).all()
        
        if request.is_json or request.args.get('format') == 'json':
            return jsonify({
                'status': 'success',
                'count': len(files),
                'files': [f.to_dict() for f in files]
            }), 200
        else:
            return render_template('uploads.html', files=files)
    
    except Exception as e:
        logger.error(f"Error listing uploads: {str(e)}")
        
        if request.is_json:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
        else:
            return render_template('error.html', error=str(e))


@upload_bp.route('/upload/stats', methods=['GET'])
def upload_stats():
    """
    Get upload statistics
    
    Returns:
        JSON with upload statistics
    """
    try:
        total_uploads = UploadedFile.query.count()
        clean_uploads = UploadedFile.query.filter_by(scan_status='clean').count()
        infected_uploads = UploadedFile.query.filter_by(scan_status='infected').count()
        
        return jsonify({
            'status': 'success',
            'total_uploads': total_uploads,
            'clean_uploads': clean_uploads,
            'infected_uploads': infected_uploads,
            'infection_rate': round((infected_uploads / total_uploads * 100), 2) if total_uploads > 0 else 0
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting upload stats: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
