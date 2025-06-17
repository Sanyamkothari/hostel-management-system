"""
Logging Configuration for Hostel Management System
Production-ready logging setup with structured output
"""
import os
import logging
import logging.config
from datetime import datetime

def setup_logging(app):
    """
    Setup comprehensive logging for the application
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Log level from environment or config
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # Logging configuration
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(levelname)s - %(message)s'
            },
            'json': {
                'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "function": "%(funcName)s", "line": %(lineno)d, "message": "%(message)s"}',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'level': log_level,
                'class': 'logging.StreamHandler',
                'formatter': 'detailed' if app.config.get('DEBUG') else 'json',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'level': log_level,
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'detailed',
                'filename': os.path.join(logs_dir, 'hostel_management.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'error_file': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'detailed',
                'filename': os.path.join(logs_dir, 'errors.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'security_file': {
                'level': 'WARNING',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'detailed',
                'filename': os.path.join(logs_dir, 'security.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 10,
                'encoding': 'utf8'
            }
        },
        'loggers': {
            '': {  # Root logger
                'level': log_level,
                'handlers': ['console', 'file'],
                'propagate': False
            },
            'app': {
                'level': log_level,
                'handlers': ['console', 'file'],
                'propagate': False
            },
            'security': {
                'level': 'WARNING',
                'handlers': ['console', 'security_file'],
                'propagate': False
            },
            'socketio': {
                'level': 'INFO',
                'handlers': ['console', 'file'],
                'propagate': False
            },
            'werkzeug': {
                'level': 'WARNING',
                'handlers': ['console'],
                'propagate': False
            },
            'gunicorn.error': {
                'level': 'INFO',
                'handlers': ['console', 'error_file'],
                'propagate': False
            },
            'gunicorn.access': {
                'level': 'INFO',
                'handlers': ['console', 'file'],
                'propagate': False
            }
        }
    }
    
    # Apply logging configuration
    logging.config.dictConfig(logging_config)
    
    # Create application-specific loggers
    app_logger = logging.getLogger('app')
    security_logger = logging.getLogger('security')
    
    # Log application startup
    app_logger.info(f"Hostel Management System starting up - Environment: {os.environ.get('FLASK_ENV', 'development')}")
    app_logger.info(f"Logging level set to: {log_level}")
    
    # Add request logging for production
    if not app.config.get('DEBUG'):
        @app.before_request
        def log_request_info():
            from flask import request, g
            app_logger.info(f"Request: {request.method} {request.url} - User: {getattr(g, 'user', {}).get('id', 'anonymous')}")
        
        @app.after_request
        def log_response_info(response):
            from flask import request
            app_logger.info(f"Response: {response.status_code} for {request.method} {request.url}")
            return response
    
    # Exception logging
    @app.errorhandler(Exception)
    def log_exception(error):
        from flask import request
        app_logger.error(f"Unhandled exception on {request.method} {request.url}: {str(error)}", exc_info=True)
        # Re-raise the exception so it's handled by other error handlers
        raise error
    
    return app_logger, security_logger

def log_security_event(event_type, details, user_id=None, ip_address=None):
    """
    Log security-related events
    """
    security_logger = logging.getLogger('security')
    
    message = f"Security Event: {event_type}"
    if user_id:
        message += f" - User ID: {user_id}"
    if ip_address:
        message += f" - IP: {ip_address}"
    if details:
        message += f" - Details: {details}"
    
    security_logger.warning(message)

def log_user_action(action, user_id, details=None):
    """
    Log user actions for audit trail
    """
    app_logger = logging.getLogger('app')
    
    message = f"User Action: {action} - User ID: {user_id}"
    if details:
        message += f" - Details: {details}"
    
    app_logger.info(message)

def log_system_event(event_type, details=None):
    """
    Log system events
    """
    app_logger = logging.getLogger('app')
    
    message = f"System Event: {event_type}"
    if details:
        message += f" - Details: {details}"
    
    app_logger.info(message)
