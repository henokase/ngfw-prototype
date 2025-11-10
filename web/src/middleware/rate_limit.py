"""
Rate Limiter Middleware

Simple in-memory rate limiting to prevent abuse and demonstrate traffic control.
Tracks requests per IP address with configurable thresholds.

Author: NGFW Test Website
Date: November 10, 2025
"""

from flask import request, jsonify
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import threading

# Import services
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.services.utils import extract_ip_address
from src.services.logging_service import log_security_event, get_security_logger

logger = logging.getLogger('app')
security_logger = get_security_logger()


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm
    """
    
    def __init__(self, requests_per_minute=100, cleanup_interval=60):
        """
        Initialize rate limiter
        
        Args:
            requests_per_minute: Maximum requests allowed per minute per IP
            cleanup_interval: Interval in seconds to clean up old entries
        """
        self.requests_per_minute = requests_per_minute
        self.cleanup_interval = cleanup_interval
        self.request_log = defaultdict(list)  # {ip: [timestamps]}
        self.lock = threading.Lock()
        self.last_cleanup = datetime.utcnow()
        
        logger.info(f"Rate limiter initialized: {requests_per_minute} requests/minute")
    
    def is_allowed(self, ip_address):
        """
        Check if request from IP is allowed
        
        Args:
            ip_address: Client IP address
            
        Returns:
            Tuple of (allowed: bool, remaining: int, reset_time: datetime)
        """
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=1)
        
        with self.lock:
            # Clean up old entries if needed
            if (now - self.last_cleanup).total_seconds() > self.cleanup_interval:
                self._cleanup_old_entries()
            
            # Get request timestamps for this IP
            timestamps = self.request_log[ip_address]
            
            # Remove timestamps outside the window
            timestamps = [ts for ts in timestamps if ts > window_start]
            self.request_log[ip_address] = timestamps
            
            # Check if limit exceeded
            if len(timestamps) >= self.requests_per_minute:
                # Calculate when the oldest request will expire
                oldest_timestamp = min(timestamps)
                reset_time = oldest_timestamp + timedelta(minutes=1)
                return False, 0, reset_time
            
            # Add current timestamp
            timestamps.append(now)
            remaining = self.requests_per_minute - len(timestamps)
            reset_time = now + timedelta(minutes=1)
            
            return True, remaining, reset_time
    
    def _cleanup_old_entries(self):
        """
        Clean up old entries to prevent memory bloat
        """
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=5)  # Keep 5 minutes of history
        
        # Remove IPs with no recent requests
        ips_to_remove = []
        for ip, timestamps in self.request_log.items():
            # Filter out old timestamps
            recent_timestamps = [ts for ts in timestamps if ts > window_start]
            if recent_timestamps:
                self.request_log[ip] = recent_timestamps
            else:
                ips_to_remove.append(ip)
        
        # Remove empty entries
        for ip in ips_to_remove:
            del self.request_log[ip]
        
        self.last_cleanup = now
        
        if ips_to_remove:
            logger.debug(f"Cleaned up {len(ips_to_remove)} inactive IPs from rate limiter")
    
    def get_stats(self):
        """
        Get rate limiter statistics
        
        Returns:
            Dictionary with statistics
        """
        with self.lock:
            total_ips = len(self.request_log)
            total_requests = sum(len(timestamps) for timestamps in self.request_log.values())
            
            return {
                'requests_per_minute': self.requests_per_minute,
                'tracked_ips': total_ips,
                'total_requests_tracked': total_requests,
                'last_cleanup': self.last_cleanup.isoformat()
            }
    
    def reset_ip(self, ip_address):
        """
        Reset rate limit for a specific IP
        
        Args:
            ip_address: IP address to reset
        """
        with self.lock:
            if ip_address in self.request_log:
                del self.request_log[ip_address]
                logger.info(f"Rate limit reset for IP: {ip_address}")
    
    def reset_all(self):
        """
        Reset all rate limits
        """
        with self.lock:
            self.request_log.clear()
            logger.info("All rate limits reset")


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter(requests_per_minute=100):
    """
    Get or create the global rate limiter instance
    
    Args:
        requests_per_minute: Maximum requests per minute
        
    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)
    
    return _rate_limiter


def init_rate_limiter(app):
    """
    Initialize rate limiting middleware
    
    Args:
        app: Flask application instance
    """
    
    # Get configuration
    enable_rate_limit = app.config.get('ENABLE_RATE_LIMIT', True)
    requests_per_minute = app.config.get('RATE_LIMIT_PER_MINUTE', 100)
    
    if not enable_rate_limit:
        logger.info("Rate limiting middleware disabled")
        return
    
    # Initialize rate limiter
    limiter = get_rate_limiter(requests_per_minute)
    
    @app.before_request
    def check_rate_limit():
        """
        Check rate limit before processing request
        """
        # Skip rate limiting for static files
        if request.path.startswith('/static/'):
            return
        
        # Skip rate limiting for health check (optional)
        if request.path == '/health':
            return
        
        try:
            # Get client IP
            ip_address = extract_ip_address(request)
            
            # Check rate limit
            allowed, remaining, reset_time = limiter.is_allowed(ip_address)
            
            if not allowed:
                # Log rate limit violation
                log_security_event(
                    logger=security_logger,
                    event_type='rate_limit_exceeded',
                    message=f"Rate limit exceeded for IP: {ip_address}",
                    ip_address=ip_address,
                    endpoint=request.path,
                    method=request.method
                )
                
                # Return 429 Too Many Requests
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Maximum {requests_per_minute} requests per minute.',
                    'retry_after': int((reset_time - datetime.utcnow()).total_seconds()),
                    'reset_time': reset_time.isoformat()
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(int((reset_time - datetime.utcnow()).total_seconds()))
                response.headers['X-RateLimit-Limit'] = str(requests_per_minute)
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = reset_time.isoformat()
                
                return response
            
            # Add rate limit headers to response (will be added in after_request)
            request.rate_limit_remaining = remaining
            request.rate_limit_reset = reset_time
            
        except Exception as e:
            # Don't let rate limiting errors break the request
            logger.error(f"Error in rate limiter: {str(e)}")
    
    @app.after_request
    def add_rate_limit_headers(response):
        """
        Add rate limit headers to response
        
        Args:
            response: Flask response object
            
        Returns:
            Response with rate limit headers
        """
        try:
            # Skip for static files
            if request.path.startswith('/static/'):
                return response
            
            # Add rate limit headers if available
            if hasattr(request, 'rate_limit_remaining'):
                response.headers['X-RateLimit-Limit'] = str(requests_per_minute)
                response.headers['X-RateLimit-Remaining'] = str(request.rate_limit_remaining)
                response.headers['X-RateLimit-Reset'] = request.rate_limit_reset.isoformat()
        
        except Exception as e:
            logger.error(f"Error adding rate limit headers: {str(e)}")
        
        return response


def get_rate_limit_stats():
    """
    Get rate limiter statistics
    
    Returns:
        Dictionary with statistics or None if rate limiter not initialized
    """
    limiter = get_rate_limiter()
    if limiter:
        return limiter.get_stats()
    return None


def reset_rate_limit(ip_address=None):
    """
    Reset rate limit for specific IP or all IPs
    
    Args:
        ip_address: IP to reset, or None to reset all
    """
    limiter = get_rate_limiter()
    if limiter:
        if ip_address:
            limiter.reset_ip(ip_address)
        else:
            limiter.reset_all()
