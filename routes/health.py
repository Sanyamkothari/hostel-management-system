"""
Health Check Route
Comprehensive health monitoring for production deployment
"""
from flask import Blueprint, jsonify, request
import os
import time
import psutil
from datetime import datetime, timedelta
from db_utils import get_db_connection
import subprocess

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """Comprehensive health check for production monitoring"""
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {}
    }
    
    overall_status = True
    
    # Check database connectivity
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.fetchone()
            cursor.close()
            conn.close()
            
            health_data['components']['database'] = {
                'status': 'healthy',
                'message': 'Database connection successful'
            }
        else:
            raise Exception("Database connection failed")
    except Exception as e:
        health_data['components']['database'] = {
            'status': 'unhealthy',
            'message': f'Database error: {str(e)}'
        }
        overall_status = False
    
    # Check Redis connectivity (optional)
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        redis_client.ping()
        health_data['components']['redis'] = {
            'status': 'healthy',
            'message': 'Redis connection successful'
        }
    except Exception as e:
        health_data['components']['redis'] = {
            'status': 'warning',
            'message': f'Redis not available (optional): {str(e)}'
        }
    
    # Check file system
    try:
        critical_dirs = ['uploads', 'logs', 'backups']
        fs_status = []
        
        for directory in critical_dirs:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    fs_status.append(f'{directory}: created')
                except Exception as e:
                    fs_status.append(f'{directory}: error - {str(e)}')
                    overall_status = False
            else:
                if os.access(directory, os.W_OK):
                    fs_status.append(f'{directory}: writable')
                else:
                    fs_status.append(f'{directory}: read-only')
                    overall_status = False
        
        health_data['components']['filesystem'] = {
            'status': 'healthy' if overall_status else 'warning',
            'directories': fs_status
        }
    except Exception as e:
        health_data['components']['filesystem'] = {
            'status': 'unhealthy',
            'message': f'Filesystem error: {str(e)}'
        }
        overall_status = False
    
    # Check system resources
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health_data['components']['system'] = {
            'status': 'healthy',
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': disk.percent,
            'load_average': get_load_average()
        }
        
        # Check if resources are critically low
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 95:
            health_data['components']['system']['status'] = 'warning'
            
    except Exception as e:
        health_data['components']['system'] = {
            'status': 'unhealthy',
            'message': f'System monitoring error: {str(e)}'
        }
        overall_status = False
    
    # Set overall status
    health_data['status'] = 'healthy' if overall_status else 'unhealthy'
    
    status_code = 200 if overall_status else 503
    return jsonify(health_data), status_code

@health_bp.route('/health/ready')
def readiness_check():
    """Kubernetes/Docker readiness probe"""
    try:
        # Check database connection
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            conn.close()
        else:
            raise Exception("Database connection failed")
        
        # Simple Redis check (optional)
        try:
            import redis
            redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            redis_client.ping()
        except:
            pass  # Redis is optional
        
        return jsonify({
            'status': 'ready',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@health_bp.route('/health/live')
def liveness_check():
    """Kubernetes/Docker liveness probe"""
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

def get_uptime():
    """Get application uptime"""
    try:
        uptime_seconds = time.time() - psutil.boot_time()
        return str(timedelta(seconds=int(uptime_seconds)))
    except:
        return "unknown"

def get_load_average():
    """Get system load average (Windows compatible)"""
    try:
        # Check if running on Unix-like system
        if os.name == 'posix' and hasattr(os, 'getloadavg'):
            return os.getloadavg()[0]
        else:
            # Windows alternative using CPU percentage
            return psutil.cpu_percent(interval=1) / 100.0
    except (AttributeError, OSError):
        # Fallback to psutil CPU percentage
        try:
            return psutil.cpu_percent(interval=1) / 100.0
        except Exception:
            return 0.0

def get_redis_stats():
    """Get Redis statistics"""
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        redis_client.ping()
        
        # Get basic info
        try:
            info = redis_client.info()
            if isinstance(info, dict):
                return {
                    'status': 'connected',
                    'version': info.get('redis_version', 'unknown'),
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory': info.get('used_memory_human', 'unknown'),
                    'total_commands_processed': info.get('total_commands_processed', 0)
                }
            else:
                return {
                    'status': 'connected',
                    'version': 'unknown',
                    'connected_clients': 'unknown',
                    'used_memory': 'unknown',
                    'total_commands_processed': 'unknown'
                }
        except Exception:
            return {
                'status': 'connected',
                'message': 'Basic connection successful but info unavailable'
            }
    except Exception as e:
        return {
            'status': 'disconnected',
            'error': str(e)
        }

def get_application_stats():
    """Get application-specific statistics"""
    try:
        conn = get_db_connection()
        user_count = 0
        hostel_count = 0
        
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT COUNT(*) FROM users")
                result = cursor.fetchone()
                user_count = result[0] if result else 0
            except:
                user_count = 0
            
            try:
                cursor.execute("SELECT COUNT(*) FROM hostels")
                result = cursor.fetchone()
                hostel_count = result[0] if result else 0
            except:
                hostel_count = 0
            
            cursor.close()
            conn.close()
        
        stats = {
            'user_count': user_count,
            'hostel_count': hostel_count,
            'active_sessions': 0  # Simple fallback value
        }
        
        return stats
    except Exception as e:
        return {
            'error': str(e)
        }
