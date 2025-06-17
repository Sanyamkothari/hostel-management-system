"""
Socket.IO Monitoring and Statistics
Real-time connection monitoring for administrators
"""
from flask import Blueprint, render_template, jsonify, request, g
from utils.auth_utils import login_required
from datetime import datetime, timedelta
import json

socketio_monitor_bp = Blueprint('socketio_monitor', __name__, url_prefix='/admin/socketio')

# In-memory storage for connection statistics (in production, use Redis or database)
connection_stats = {
    'total_connections': 0,
    'current_connections': 0,
    'peak_connections': 0,
    'connection_history': [],
    'event_counts': {},
    'error_counts': 0,
    'last_reset': datetime.now()
}

@socketio_monitor_bp.route('/')
@login_required
def monitor_dashboard():
    """Socket.IO monitoring dashboard (owner only)"""
    if g.user.get('role') != 'owner':
        return "Access denied - Owner only", 403
    
    return render_template('admin/socketio_monitor.html')

@socketio_monitor_bp.route('/stats')
@login_required
def get_stats():
    """Get Socket.IO statistics"""
    if g.user.get('role') != 'owner':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from utils.socket_utils import get_connected_users_count
        
        # Update current connections
        current = get_connected_users_count()
        connection_stats['current_connections'] = current
        
        # Update peak if necessary
        if current > connection_stats['peak_connections']:
            connection_stats['peak_connections'] = current
        
        # Add to history (keep last 100 entries)
        now = datetime.now()
        connection_stats['connection_history'].append({
            'timestamp': now.isoformat(),
            'count': current
        })
        
        # Keep only last 100 entries
        if len(connection_stats['connection_history']) > 100:
            connection_stats['connection_history'] = connection_stats['connection_history'][-100:]
        
        # Calculate uptime
        uptime = now - connection_stats['last_reset']
        
        return jsonify({
            'success': True,
            'stats': {
                **connection_stats,
                'uptime_seconds': int(uptime.total_seconds()),
                'uptime_formatted': str(uptime).split('.')[0],
                'timestamp': now.isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@socketio_monitor_bp.route('/events')
@login_required
def get_event_log():
    """Get recent Socket.IO events"""
    if g.user.get('role') != 'owner':
        return jsonify({'error': 'Access denied'}), 403
    
    # In a real implementation, this would come from a log file or database
    # For now, return sample data
    sample_events = [
        {
            'timestamp': datetime.now().isoformat(),
            'event': 'fee_added',
            'user_id': 'user123',
            'hostel_id': 'hostel1',
            'data': {'amount': 500, 'student_name': 'John Doe'}
        },
        {
            'timestamp': (datetime.now() - timedelta(minutes=2)).isoformat(),
            'event': 'student_added',
            'user_id': 'user456',
            'hostel_id': 'hostel2',
            'data': {'name': 'Jane Smith'}
        }
    ]
    
    return jsonify({
        'success': True,
        'events': sample_events
    })

@socketio_monitor_bp.route('/reset-stats', methods=['POST'])
@login_required
def reset_stats():
    """Reset Socket.IO statistics"""
    if g.user.get('role') != 'owner':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        global connection_stats
        current_connections = connection_stats.get('current_connections', 0)
        
        connection_stats = {
            'total_connections': 0,
            'current_connections': current_connections,
            'peak_connections': current_connections,
            'connection_history': [],
            'event_counts': {},
            'error_counts': 0,
            'last_reset': datetime.now()
        }
        
        return jsonify({
            'success': True,
            'message': 'Statistics reset successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@socketio_monitor_bp.route('/health-check')
@login_required
def health_check():
    """Check Socket.IO server health"""
    if g.user.get('role') != 'owner':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from app import socketio
        
        # Basic health checks
        health_status = {
            'socketio_available': socketio is not None,
            'server_running': True,
            'timestamp': datetime.now().isoformat()
        }
        
        if socketio:
            try:
                # Try to get server info
                health_status['server_info'] = {
                    'async_mode': socketio.async_mode,
                    'logger': socketio.logger,
                    'engineio_logger': socketio.engineio_logger
                }
            except Exception as e:
                health_status['server_error'] = str(e)
        
        return jsonify({
            'success': True,
            'health': health_status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'health': {
                'socketio_available': False,
                'server_running': False,
                'timestamp': datetime.now().isoformat()
            }
        }), 500

def increment_event_count(event_type):
    """Utility function to track event counts"""
    if event_type in connection_stats['event_counts']:
        connection_stats['event_counts'][event_type] += 1
    else:
        connection_stats['event_counts'][event_type] = 1

def increment_connection_count():
    """Utility function to track new connections"""
    connection_stats['total_connections'] += 1

def increment_error_count():
    """Utility function to track errors"""
    connection_stats['error_counts'] += 1
