"""
Socket.IO Test Route
Test real-time functionality and connection status
"""
from flask import Blueprint, render_template, request, jsonify, session, g, has_app_context
from utils.auth_utils import login_required
from utils.socket_utils import (
    emit_system_notification,
    emit_dashboard_update,
    get_connected_users_count,
    broadcast_system_message
)

socketio_test_bp = Blueprint('socketio_test', __name__, url_prefix='/socketio-test')

@socketio_test_bp.route('/')
@login_required
def test_page():
    """Socket.IO test page"""
    # If running outside of Flask application context (e.g., during tests), return basic string
    if not has_app_context():
        return "Socket.IO test page"
    return render_template('socketio_test.html')

@socketio_test_bp.route('/send-notification', methods=['POST'])
@login_required
def send_test_notification():
    """Send a test notification"""
    try:
        data = request.get_json()
        message = data.get('message', 'Test notification')
        notification_type = data.get('type', 'info')
        
        # Send notification
        emit_system_notification(
            message=message,
            notification_type=notification_type,
            hostel_id=g.user.get('hostel_id') if g.user.get('role') != 'owner' else None
        )
        
        return jsonify({
            'success': True,
            'message': 'Notification sent successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@socketio_test_bp.route('/broadcast-message', methods=['POST'])
@login_required
def send_broadcast():
    """Send a broadcast message (owner only)"""
    if g.user.get('role') != 'owner':
        return jsonify({
            'success': False,
            'error': 'Unauthorized - Owner access required'
        }), 403
    
    try:
        data = request.get_json()
        message = data.get('message', 'Test broadcast')
        
        # Send broadcast
        broadcast_system_message(message, g.user.get('name', 'System'))
        
        return jsonify({
            'success': True,
            'message': 'Broadcast sent successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@socketio_test_bp.route('/connection-status')
@login_required
def get_connection_status():
    """Get Socket.IO connection status"""
    try:
        connected_users = get_connected_users_count()
        
        return jsonify({
            'success': True,
            'connected_users': connected_users,
            'server_status': 'online',
            'user_role': g.user.get('role'),
            'user_hostel': g.user.get('hostel_id')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'server_status': 'error'
        }), 500

@socketio_test_bp.route('/trigger-dashboard-update', methods=['POST'])
@login_required
def trigger_dashboard_update():
    """Trigger a dashboard update"""
    try:
        hostel_id = g.user.get('hostel_id') if g.user.get('role') != 'owner' else None
        
        # Trigger dashboard update
        emit_dashboard_update(hostel_id=hostel_id)
        
        return jsonify({
            'success': True,
            'message': 'Dashboard update triggered'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
