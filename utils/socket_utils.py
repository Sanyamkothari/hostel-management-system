"""
Socket.IO Utility Functions
Centralized functions for emitting Socket.IO events across the application
"""
from datetime import datetime
import json


def get_socketio():
    """Get the socketio instance safely"""
    try:
        from app import socketio
        return socketio
    except ImportError:
        print("Warning: Could not import socketio from app")
        return None


def emit_safe(event_type, data, **kwargs):
    """
    Safely emit a Socket.IO event with error handling
    """
    socketio = get_socketio()
    if not socketio:
        print(f"Warning: Cannot emit {event_type} - SocketIO not available")
        return False
    
    try:
        # Add timestamp to all events
        if isinstance(data, dict):
            data['timestamp'] = datetime.now().isoformat()
        
        # Set default namespace if not provided
        if 'namespace' not in kwargs:
            kwargs['namespace'] = '/updates'
        
        socketio.emit(event_type, data, **kwargs)
        print(f"Emitted {event_type}: {data}")
        return True
        
    except Exception as e:
        print(f"Error emitting {event_type}: {e}")
        return False


def emit_to_hostel(event_type, data, hostel_id):
    """
    Emit event to a specific hostel room
    """
    return emit_safe(event_type, data, to=f'hostel_{hostel_id}')


def emit_to_owners(event_type, data):
    """
    Emit event to all owners
    """
    return emit_safe(event_type, data, to='owners')


def emit_to_all(event_type, data):
    """
    Emit event to all connected clients
    """
    return emit_safe(event_type, data)


# Specific event emission functions for different entity types

def emit_student_event(event_type, student_data, hostel_id=None):
    """Emit student-related events"""
    data = {
        'type': 'student',
        'action': event_type,
        'student': student_data
    }
    
    if hostel_id:
        return emit_to_hostel(f'student_{event_type}', data, hostel_id)
    else:
        return emit_to_all(f'student_{event_type}', data)


def emit_room_event(event_type, room_data, hostel_id=None):
    """Emit room-related events"""
    data = {
        'type': 'room',
        'action': event_type,
        'room': room_data
    }
    
    if hostel_id:
        return emit_to_hostel(f'room_{event_type}', data, hostel_id)
    else:
        return emit_to_all(f'room_{event_type}', data)


def emit_fee_event(event_type, fee_data, hostel_id=None):
    """Emit fee-related events"""
    data = {
        'type': 'fee',
        'action': event_type,
        'fee': fee_data
    }
    
    if hostel_id:
        return emit_to_hostel(f'fee_{event_type}', data, hostel_id)
    else:
        return emit_to_all(f'fee_{event_type}', data)


def emit_complaint_event(event_type, complaint_data, hostel_id=None):
    """Emit complaint-related events"""
    data = {
        'type': 'complaint',
        'action': event_type,
        'complaint': complaint_data
    }
    
    if hostel_id:
        return emit_to_hostel(f'complaint_{event_type}', data, hostel_id)
    else:
        return emit_to_all(f'complaint_{event_type}', data)


def emit_expense_event(event_type, expense_data, hostel_id=None):
    """Emit expense-related events"""
    data = {
        'type': 'expense',
        'action': event_type,
        'expense': expense_data
    }
    
    if hostel_id:
        return emit_to_hostel(f'expense_{event_type}', data, hostel_id)
    else:
        return emit_to_all(f'expense_{event_type}', data)


def emit_dashboard_update(hostel_id=None, stats=None):
    """Emit dashboard statistics update"""
    if not stats:
        try:
            from routes.dashboard import get_dashboard_statistics
            stats = get_dashboard_statistics(hostel_id)
        except Exception as e:
            print(f"Error getting dashboard stats: {e}")
            return False
    
    data = {
        'stats': stats,
        'hostel_id': hostel_id,
        'update_type': 'dashboard'
    }
    
    if hostel_id:
        return emit_to_hostel('dashboard_stats_updated', data, hostel_id)
    else:
        return emit_to_owners('dashboard_stats_updated', data)


def emit_system_notification(message, notification_type='info', hostel_id=None, target='all'):
    """Emit system notifications"""
    data = {
        'message': message,
        'type': notification_type,
        'system': True
    }
    
    if target == 'owners':
        return emit_to_owners('system_notification', data)
    elif target == 'hostel' and hostel_id:
        return emit_to_hostel('system_notification', data, hostel_id)
    else:
        return emit_to_all('system_notification', data)


def emit_user_activity(user_id, activity, hostel_id=None):
    """Emit user activity notifications"""
    data = {
        'user_id': user_id,
        'activity': activity,
        'type': 'user_activity'
    }
    
    if hostel_id:
        return emit_to_hostel('user_activity', data, hostel_id)
    else:
        return emit_to_owners('user_activity', data)


def emit_maintenance_alert(message, priority='normal', hostel_id=None):
    """Emit maintenance alerts"""
    data = {
        'message': message,
        'priority': priority,
        'type': 'maintenance',
        'requires_attention': priority in ['high', 'urgent']
    }
    
    if hostel_id:
        return emit_to_hostel('maintenance_alert', data, hostel_id)
    else:
        return emit_to_owners('maintenance_alert', data)


def emit_financial_alert(message, amount=None, hostel_id=None):
    """Emit financial alerts"""
    data = {
        'message': message,
        'type': 'financial',
        'amount': amount
    }
    
    if hostel_id:
        return emit_to_hostel('financial_alert', data, hostel_id)
    else:
        return emit_to_owners('financial_alert', data)


# Connection status functions

def get_connected_users_count():
    """Get the number of connected users"""
    socketio = get_socketio()
    if not socketio:
        return 0
    
    try:
        # This is a simplified count - in production you might want to track this more precisely
        # Using a placeholder since server.manager.rooms API changed
        return 0  # Placeholder - would need proper connection tracking
    except Exception as e:
        print(f"Error getting connected users count: {e}")
        return 0


def get_hostel_connected_users(hostel_id):
    """Get the number of users connected to a specific hostel room"""
    socketio = get_socketio()
    if not socketio:
        return 0
    
    try:
        # Using placeholder since server.manager.rooms API is not accessible in current Flask-SocketIO version
        # In production, implement proper connection tracking
        return 0  # Placeholder - would need proper connection tracking
    except Exception as e:
        print(f"Error getting hostel connected users: {e}")
        return 0


def broadcast_system_message(message, sender='System'):
    """Broadcast a system message to all connected users"""
    data = {
        'message': message,
        'sender': sender,
        'type': 'system_broadcast',
        'broadcast': True
    }
    
    return emit_to_all('system_broadcast', data)
