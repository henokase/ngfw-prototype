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

from src.services.logging_service import log_security_event, get_security_logger

logger = logging.getLogger('app')
security_logger = get_security_logger()


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm
    Supports session-based (unauthenticated), account-based (authenticated), and global limits
    """
    
    def __init__(self, requests_per_minute=100, global_requests_per_second=50, cleanup_interval=60):
        """
        Initialize rate limiter
        
        Args:
            requests_per_minute: Maximum requests allowed per minute per session/account
            global_requests_per_second: Maximum total requests per second site-wide
            cleanup_interval: Interval in seconds to clean up old entries
        """
        self.requests_per_minute = requests_per_minute
        self.global_requests_per_second = global_requests_per_second
        self.cleanup_interval = cleanup_interval
        self.request_log = defaultdict(list)  # {identifier: [timestamps]}
        self.global_requests = []  # Global request timestamps
        self.lock = threading.Lock()
        self.last_cleanup = datetime.utcnow()
        
        logger.info(f"Rate limiter initialized: {requests_per_minute} requests/minute per user, {global_requests_per_second} requests/sec global")
    
    def is_allowed(self, identifier, is_global_check=False):
        """
        Check if request from identifier is allowed
        
        Args:
            identifier: Session ID, username, or 'GLOBAL' for site-wide check
            is_global_check: If True, check global rate limit
            
        Returns:
            Tuple of (allowed: bool, remaining: int, reset_time: datetime)
        """
        now = datetime.utcnow()
        
        with self.lock:
            # Clean up old entries if needed
            if (now - self.last_cleanup).total_seconds() > self.cleanup_interval:
                self._cleanup_old_entries()
            
            # Check global rate limit first (requests per second)
            if is_global_check:
                global_window_start = now - timedelta(seconds=1)
                self.global_requests = [ts for ts in self.global_requests if ts > global_window_start]
                
                if len(self.global_requests) >= self.global_requests_per_second:
                    oldest_timestamp = min(self.global_requests)
                    reset_time = oldest_timestamp + timedelta(seconds=1)
                    return False, 0, reset_time
                
                self.global_requests.append(now)
                remaining = self.global_requests_per_second - len(self.global_requests)
                reset_time = now + timedelta(seconds=1)
                return True, remaining, reset_time
            
            # Check per-user rate limit (requests per minute)
            window_start = now - timedelta(minutes=1)
            timestamps = self.request_log[identifier]
            
            # Remove timestamps outside the window
            timestamps = [ts for ts in timestamps if ts > window_start]
            self.request_log[identifier] = timestamps
            
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
        
        # Remove identifiers with no recent requests
        identifiers_to_remove = []
        for identifier, timestamps in self.request_log.items():
            # Filter out old timestamps
            recent_timestamps = [ts for ts in timestamps if ts > window_start]
            if recent_timestamps:
                self.request_log[identifier] = recent_timestamps
            else:
                identifiers_to_remove.append(identifier)
        
        # Remove empty entries
        for identifier in identifiers_to_remove:
            del self.request_log[identifier]
        
        # Clean up global requests
        global_window_start = now - timedelta(minutes=5)
        self.global_requests = [ts for ts in self.global_requests if ts > global_window_start]
        
        self.last_cleanup = now
        
        if identifiers_to_remove:
            logger.debug(f"Cleaned up {len(identifiers_to_remove)} inactive identifiers from rate limiter")
    
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
            from flask import session
            import uuid
            
            # Check global rate limit first (prevent site-wide floods)
            global_allowed, _, global_reset = limiter.is_allowed('GLOBAL', is_global_check=True)
            if not global_allowed:
                logger.warning("Global rate limit exceeded - site under flood")
                response = jsonify({
                    'error': 'Service temporarily unavailable',
                    'message': 'Site is experiencing high traffic. Please try again later.',
                    'retry_after': int((global_reset - datetime.utcnow()).total_seconds())
                })
                response.status_code = 503
                return response
            
            # Determine identifier: username (authenticated) or session_id (unauthenticated)
            identifier = None
            if 'username' in session:
                identifier = f"user:{session['username']}"
            elif 'session_id' in session:
                identifier = f"session:{session['session_id']}"
            else:
                # Create session ID if it doesn't exist
                session['session_id'] = str(uuid.uuid4())
                identifier = f"session:{session['session_id']}"
            
            # Check per-user/session rate limit
            allowed, remaining, reset_time = limiter.is_allowed(identifier)
            
            if not allowed:
                # Log rate limit violation
                # VM2 only sees VM1's IP (10.0.0.1)
                ip_address = request.remote_addr or '10.0.0.1'
                log_security_event(
                    logger=security_logger,
                    event_type='rate_limit_exceeded',
                    message=f"Rate limit exceeded for {identifier}",
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
