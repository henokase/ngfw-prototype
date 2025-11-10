"""
XML Routes

Implements intentionally vulnerable XML parsing endpoints for NGFW testing.
Demonstrates XXE (XML External Entity) vulnerabilities.

SECURITY WARNING: This code contains INTENTIONAL vulnerabilities for testing purposes.
NEVER use this code in production environments.

Author: NGFW Test Website
Date: November 10, 2025
"""

from flask import Blueprint, request, jsonify, render_template
import logging
from lxml import etree

# Import services
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.logging_service import get_security_logger

logger = logging.getLogger('app')
security_logger = get_security_logger()

# Create Blueprint
xml_bp = Blueprint('xml', __name__)


@xml_bp.route('/api/xml', methods=['GET'])
def xml_form():
    """
    Display XML upload form
    
    Returns:
        HTML XML upload form
    """
    return render_template('xml_api.html')


@xml_bp.route('/api/xml', methods=['POST'])
def parse_xml():
    """
    Parse XML data with external entity processing
    
    VULNERABILITY: XXE (XML External Entity) Attack
    - Parses XML with resolve_entities=True
    - Allows attackers to read arbitrary files via external entities
    
    Returns:
        JSON response with parsed XML data
    """
    try:
        # Get XML data
        if request.content_type == 'application/xml' or request.content_type == 'text/xml':
            xml_data = request.data.decode('utf-8')
        elif request.is_json:
            data = request.get_json()
            xml_data = data.get('xml', '')
        else:
            xml_data = request.form.get('xml', '')
        
        if not xml_data:
            return jsonify({
                'status': 'error',
                'message': 'XML data is required'
            }), 400
        
        # Log XML parsing attempt
        logger.warning(f"XML parsing attempt (length: {len(xml_data)})")
        security_logger.warning(
            f"XML parsing",
            extra={
                'xml_length': len(xml_data),
                'ip_address': request.remote_addr or '10.0.0.1',
                'endpoint': '/api/xml'
            }
        )
        
        # VULNERABILITY: XXE Attack
        # Using resolve_entities=True allows external entity processing
        # Attacker can read files using: <!ENTITY xxe SYSTEM "file:///etc/passwd">
        
        logger.debug(f"Parsing XML with external entity resolution enabled")
        
        # Create parser with vulnerable settings
        parser = etree.XMLParser(
            resolve_entities=True,  # VULNERABLE: Enables XXE
            no_network=False,  # VULNERABLE: Allows network access
            dtd_validation=False
        )
        
        # Parse XML
        root = etree.fromstring(xml_data.encode('utf-8'), parser)
        
        # Extract data from XML
        result = {}
        for element in root.iter():
            if element.text and element.text.strip():
                result[element.tag] = element.text.strip()
        
        logger.info(f"XML parsed successfully")
        
        return jsonify({
            'status': 'success',
            'message': 'XML parsed successfully',
            'data': result,
            'root_tag': root.tag
        }), 200
    
    except etree.XMLSyntaxError as e:
        logger.error(f"XML syntax error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'XML syntax error: {str(e)}'
        }), 400
    
    except Exception as e:
        logger.error(f"XML parsing error: {str(e)}")
        security_logger.error(
            f"XML parsing exception",
            extra={
                'error': str(e),
                'xml_length': len(xml_data) if 'xml_data' in locals() else 0
            }
        )
        
        return jsonify({
            'status': 'error',
            'message': f'XML parsing error: {str(e)}'
        }), 500
