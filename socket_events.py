"""
Socket.IO Event Handlers for Real-time Updates
Hostel Management System
"""
from flask_socketio import emit, join_room, leave_room, disconnect
from flask import session, g
import json
import uuid
from datetime import datetime
from db_utils import get_db_connection
from routes.auth import login_required

# Simple in-memory connection manager (no Redis dependency)
class SimpleConnectionManager:
    """Simple in-memory connection manager for Socket.IO sessions"""

    def __init__(self):
        self._sessions = {}  # session_id -> user_data
        self._user_sessions = {}  # user_id -> set of session_ids
    
    def add_user_session(self, user_id: int, session_id: str, user_data: dict) -> bool:
        """Add a user session to tracking"""
        try:
            self._sessions[session_id] = user_data
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = set()
            self._user_sessions[user_id].add(session_id)
            return True
        except Exception as e:
            print(f"Error adding user session: {e}")
            return False
    
    def remove_user_session(self, user_id: int, session_id: str) -> bool:
        """Remove a user session from tracking"""
        try:
            if session_id in self._sessions:
                del self._sessions[session_id]
            if user_id in self._user_sessions:
                self._user_sessions[user_id].discard(session_id)
                # Clean up empty user entries
                if not self._user_sessions[user_id]:
                    del self._user_sessions[user_id]
            return True
        except Exception as e:
            print(f"Error removing user session: {e}")
            return False
    
    def get_online_session_count(self) -> int:
        """Get total number of online sessions"""
        return len(self._sessions)
    
    def get_user_sessions(self, user_id: int) -> set:
        """Get all active sessions for a user"""
        return self._user_sessions.get(user_id, set())
    
    def get_session_data(self, session_id: str) -> dict:
        """Get session data for a specific session"""
        return self._sessions.get(session_id, {})

# Global connection manager instance
connection_manager = SimpleConnectionManager()

def register_socket_events(socketio):
    """Register all Socket.IO event handlers"""
    
    @socketio.on('connect', namespace='/updates')
    def handle_connect():
        """Handle client connection"""
        # Generate a unique session ID for tracking (since request.sid isn't available in this version)
        current_sid = str(uuid.uuid4())[:12]
        print(f'Client {current_sid} attempting to connect')

        # Check if user is authenticated
        if 'user_id' not in session:
            print(f'Unauthenticated client {current_sid} attempted to connect. Disconnecting.')
            disconnect()
            return False

        # g.user should be loaded by @app.before_request
        if not g.user:
            print(f'Client {current_sid} authenticated with session but g.user not found. Disconnecting.')
            disconnect()
            return False

        # User is authenticated, add to Redis connection tracking
        user_data = {
            'user_id': g.user['id'],
            'name': g.user.get('name', ''),
            'role': g.user.get('role', ''),
            'hostel_id': g.user.get('hostel_id')
        }
        
        connection_manager.add_user_session(g.user['id'], current_sid, user_data)
        online_count = connection_manager.get_online_session_count()
        print(f"User {g.user['id']} (SID: {current_sid}) connected. Total online: {online_count}")

        # Join user to their hostel room if they have one
        if g.user.get('hostel_id'):
            join_room(f"hostel_{g.user['hostel_id']}")
            print(f"User {g.user['id']} joined hostel room {g.user['hostel_id']}")

        # Join owners to owner room for system-wide notifications
        if g.user.get('role') == 'owner':
            join_room('owners')
            print(f"Owner {g.user['id']} joined owners room")

        # Store session ID for later use in disconnect
        session['socket_session_id'] = current_sid

        emit('connected', {
            'message': 'Connected to real-time updates',
            'user_id': g.user['id'],
            'hostel_id': g.user.get('hostel_id'),
            'role': g.user.get('role'),
            'session_id': current_sid
        })

    @socketio.on('disconnect', namespace='/updates')
    def handle_disconnect():
        """Handle client disconnection"""
        # Get session ID from session storage
        current_sid = session.get('socket_session_id', str(uuid.uuid4())[:12])
        
        # Get session data to find user_id
        session_data = connection_manager.get_session_data(current_sid)
        if session_data:
            user_id = session_data.get('user_id')
            if user_id:
                connection_manager.remove_user_session(int(user_id), current_sid)
                online_count = connection_manager.get_online_session_count()
                print(f'User {user_id} (SID: {current_sid}) disconnected. Total online: {online_count}')
        else:
            print(f'Client {current_sid} disconnected (session data not found)')
            # Try to remove from connection tracking anyway
            if 'user_id' in session and g.user:
                connection_manager.remove_user_session(g.user['id'], current_sid)

    @socketio.on('join_hostel_room', namespace='/updates')
    def handle_join_hostel_room(data):
        """Allow users to join specific hostel rooms"""
        if not g.user:
            return
            
        hostel_id = data.get('hostel_id')
        if not hostel_id:
            return
            
        # Check if user has permission to join this hostel room
        if g.user.get('role') == 'owner' or g.user.get('hostel_id') == hostel_id:
            join_room(f"hostel_{hostel_id}")
            emit('joined_room', {'hostel_id': hostel_id})
            print(f"User {g.user['id']} joined hostel room {hostel_id}")

    @socketio.on('leave_hostel_room', namespace='/updates')
    def handle_leave_hostel_room(data):
        """Allow users to leave specific hostel rooms"""
        if not g.user:
            return
            
        hostel_id = data.get('hostel_id')
        if hostel_id:
            leave_room(f"hostel_{hostel_id}")
            emit('left_room', {'hostel_id': hostel_id})
            print(f"User {g.user['id']} left hostel room {hostel_id}")

    @socketio.on('ping', namespace='/updates')
    def handle_ping():
        """Handle ping request for connection health check"""
        emit('pong', {'timestamp': datetime.now().isoformat()})

    @socketio.on('request_dashboard_update', namespace='/updates')
    def handle_dashboard_update_request(data):
        """Handle request for dashboard statistics update"""
        if not g.user:
            return
            
        hostel_id = data.get('hostel_id')
        
        # Get fresh dashboard statistics
        try:
            from routes.dashboard import get_dashboard_statistics
            stats = get_dashboard_statistics(hostel_id)
            
            emit('dashboard_stats_updated', {
                'stats': stats,
                'hostel_id': hostel_id,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error getting dashboard stats: {e}")
            emit('error', {'message': 'Failed to get dashboard statistics'})

    @socketio.on('subscribe_to_notifications', namespace='/updates')
    def handle_notification_subscription(data):
        """Handle subscription to specific notification types"""
        if not g.user:
            return
            
        notification_types = data.get('types', [])
        for notification_type in notification_types:
            # Join rooms for specific notification types
            room_name = f"notifications_{notification_type}"
            join_room(room_name)
            print(f"User {g.user['id']} subscribed to {notification_type} notifications")
        
        emit('subscribed', {'types': notification_types})

    @socketio.on('get_online_users', namespace='/updates')
    def handle_get_online_users():
        """Get list of online users (owner only)"""
        if not g.user or g.user.get('role') != 'owner':
            emit('error', {'message': 'Unauthorized to get online users'})
            return
        
        online_count = connection_manager.get_online_session_count()
        emit('online_users', {
            'count': online_count,
            'message': 'Online user count retrieved'
        })

    @socketio.on('broadcast_message', namespace='/updates')
    def handle_broadcast_message(data):
        """Handle admin broadcast messages (owner only)"""
        if not g.user or g.user.get('role') != 'owner':
            emit('error', {'message': 'Unauthorized'})
            return
            
        message = data.get('message')
        target = data.get('target', 'all')  # 'all', 'hostel', 'managers', 'owners'
        
        if not message:
            emit('error', {'message': 'Message is required'})
            return
            
        broadcast_data = {
            'message': message,
            'sender': g.user.get('name', 'System'),
            'timestamp': datetime.now().isoformat(),
            'type': 'broadcast'
        }
        
        if target == 'all':
            # Emitting to all connected clients in the namespace
            socketio.emit('system_broadcast', broadcast_data, namespace='/updates')

        elif target == 'owners':
            # Emitting to the 'owners' room
            socketio.emit('system_broadcast', broadcast_data, to='owners', namespace='/updates')

        elif target == 'managers':
            # Emitting to the 'managers' room - ensure managers are added to this room on connect
            socketio.emit('system_broadcast', broadcast_data, to='managers', namespace='/updates')
            print("Attempted to broadcast to managers. Ensure they join 'managers' room on connect.")

        elif target.startswith('hostel_'):
            hostel_id_str = target.replace('hostel_', '')
            # It's good practice to ensure hostel_id_str is a valid ID format if possible
            socketio.emit('system_broadcast', broadcast_data, to=f'hostel_{hostel_id_str}', namespace='/updates')

        else:
            emit('error', {'message': f'Invalid broadcast target: {target}'})
            return
            
        emit('broadcast_sent', {'message': 'Message broadcasted successfully', 'target': target})

    # Return the configured socketio instance
    return socketio

# Utility functions for Socket.IO events

def emit_notification(event_type, data, hostel_id=None, target_room=None):
    """
    Utility function to emit notifications with proper room targeting
    """
    try:
        from app import socketio
        
        # Add timestamp to all notifications
        data['timestamp'] = datetime.now().isoformat()
        
        if target_room:
            # Emit to specific room
            socketio.emit(event_type, data, to=target_room, namespace='/updates')
        elif hostel_id:
            # Emit to hostel-specific room
            socketio.emit(event_type, data, to=f'hostel_{hostel_id}', namespace='/updates')
        else:
            # Emit to all connected clients
            socketio.emit(event_type, data, namespace='/updates')
            
        print(f"Emitted {event_type} to {'room: ' + target_room if target_room else 'hostel: ' + str(hostel_id) if hostel_id else 'all clients'}")
        
    except Exception as e:
        print(f"Error emitting notification: {e}")

def emit_dashboard_update(hostel_id=None, update_type='general'):
    """
    Emit dashboard statistics update via Socket.IO
    """
    try:
        from app import socketio
        from routes.dashboard import get_dashboard_statistics
        
        # Get updated statistics
        stats = get_dashboard_statistics(hostel_id)
        
        update_data = {
            'stats': stats,
            'update_type': update_type,
            'timestamp': datetime.now().isoformat(),
            'hostel_id': hostel_id
        }
        
        if hostel_id:
            # Emit to specific hostel room
            socketio.emit('dashboard_update', update_data, to=f'hostel_{hostel_id}', namespace='/updates')
        else:
            # Emit to owners room for system-wide updates
            socketio.emit('dashboard_update', update_data, to='owners', namespace='/updates')
            
        print(f"Emitted dashboard update for hostel {hostel_id if hostel_id else 'system-wide'}")
        
    except Exception as e:
        print(f"Error emitting dashboard update: {e}")

def emit_system_alert(message, alert_type='info', hostel_id=None):
    """
    Emit system-wide alerts
    """
    try:
        from app import socketio
        
        alert_data = {
            'message': message,
            'type': alert_type,
            'timestamp': datetime.now().isoformat()
        }
        
        if hostel_id:
            socketio.emit('system_alert', alert_data, to=f'hostel_{hostel_id}', namespace='/updates')
        else:
            # System-wide alert to all users
            socketio.emit('system_alert', alert_data, namespace='/updates')
            
        print(f"Emitted system alert: {message}")
        
    except Exception as e:
        print(f"Error emitting system alert: {e}")

def emit_user_activity(user_id, activity, hostel_id=None):
    """
    Emit user activity notifications
    """
    try:
        from app import socketio
        
        activity_data = {
            'user_id': user_id,
            'activity': activity,
            'timestamp': datetime.now().isoformat()
        }
        
        room = f'hostel_{hostel_id}' if hostel_id else 'owners'
        socketio.emit('user_activity', activity_data, to=room, namespace='/updates')
        
    except Exception as e:
        print(f"Error emitting user activity: {e}")