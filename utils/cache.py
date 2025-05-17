"""Cache utilities for the Hostel Management System.

This module provides caching functionality to improve performance.
"""

import time
from functools import wraps

# Simple in-memory cache
_cache = {}

def cached(ttl_seconds=60):
    """Cache decorator for functions with no arguments.
    
    Args:
        ttl_seconds: Time to live in seconds for the cached result
        
    Returns:
        Decorated function with caching
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = func.__name__
            
            # Check if we have a valid cached result
            if cache_key in _cache:
                result, timestamp = _cache[cache_key]
                if time.time() - timestamp < ttl_seconds:
                    return result
                    
            # Compute and cache new result
            result = func(*args, **kwargs)
            _cache[cache_key] = (result, time.time())
            return result
            
        return wrapper
    return decorator

def clear_cache():
    """Clear the entire cache."""
    global _cache
    _cache = {}
