"""
Simplified Room Routes
Basic room management with minimal complexity
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models.simple_room import SimpleRoomModel
from models.hostels import Hostel
from db_utils import get_db_connection

simple_room_bp = Blueprint('simple_room', __name__, url_prefix='/simple-rooms')

def get_user_hostel():
    """Get the hostel for the current user."""
    if g.user.get('role') == 'manager':
        # Managers are assigned to a specific hostel
        return g.user.get('hostel_id'), g.user.get('hostel_name')
    elif g.user.get('role') == 'owner':
        # Owners can select hostel via URL parameter
        hostel_id = request.args.get('hostel_id', type=int)
        if hostel_id:
            hostel = Hostel.get_by_id(hostel_id)
            if hostel:
                return hostel_id, hostel.name
        return None, None
    return None, None

@simple_room_bp.route('/')
def view_rooms():
    """View all rooms."""
    try:
        hostel_id, hostel_name = get_user_hostel()
        
        # Get all hostels for owner selection
        hostels_list = []
        if g.user.get('role') == 'owner':
            hostels_list = Hostel.get_all()
        
        # Get rooms
        rooms = SimpleRoomModel.get_all_rooms(hostel_id=hostel_id)
        
        # Get basic statistics
        stats = SimpleRoomModel.get_room_stats(hostel_id=hostel_id)
        
        return render_template(
            'simple_rooms/view_rooms.html',
            rooms=rooms,
            stats=stats,
            current_hostel_name=hostel_name,
            hostels_list=hostels_list,
            user_role=g.user.get('role')
        )
        
    except Exception as e:
        flash(f'Error loading rooms: {str(e)}', 'error')
        return render_template('simple_rooms/view_rooms.html', rooms=[], stats={})

@simple_room_bp.route('/add', methods=['GET', 'POST'])
def add_room():
    """Add a new room."""
    try:
        hostel_id, hostel_name = get_user_hostel()
        
        # Get all hostels for owner selection
        hostels_list = []
        if g.user.get('role') == 'owner':
            hostels_list = Hostel.get_all()
        
        if request.method == 'POST':
            # Get form data
            room_number = request.form.get('room_number', '').strip()
            capacity = request.form.get('capacity', type=int)
            status = request.form.get('status', SimpleRoomModel.STATUS_AVAILABLE)
            
            # For owners, allow hostel selection
            if g.user.get('role') == 'owner':
                form_hostel_id = request.form.get('hostel_id', type=int)
                if form_hostel_id:
                    hostel_id = form_hostel_id
            
            if not hostel_id:
                flash('Please select a hostel first.', 'error')
                return redirect(url_for('simple_room.view_rooms'))
            
            # Add room
            result = SimpleRoomModel.add_room(room_number, capacity, hostel_id, status)
            
            if result['success']:
                flash(result['message'], 'success')
                return redirect(url_for('simple_room.view_rooms', hostel_id=hostel_id))
            else:
                flash(result['error'], 'error')
        
        return render_template(
            'simple_rooms/add_room.html',
            current_hostel_name=hostel_name,
            hostels_list=hostels_list,
            statuses=SimpleRoomModel.VALID_STATUSES,
            user_role=g.user.get('role')
        )
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('simple_room.view_rooms'))

@simple_room_bp.route('/<int:room_id>/edit', methods=['GET', 'POST'])
def edit_room(room_id):
    """Edit a room."""
    try:
        # Get room details
        room = SimpleRoomModel.get_room_by_id(room_id)
        if not room:
            flash('Room not found!', 'error')
            return redirect(url_for('simple_room.view_rooms'))
        
        # Check permissions
        if g.user.get('role') == 'manager' and g.user.get('hostel_id') != room.get('hostel_id'):
            flash('You do not have permission to edit this room.', 'error')
            return redirect(url_for('simple_room.view_rooms'))
        
        if request.method == 'POST':
            room_number = request.form.get('room_number', '').strip()
            capacity = request.form.get('capacity', type=int)
            status = request.form.get('status', '')
            
            result = SimpleRoomModel.update_room(room_id, room_number, capacity, status)
            
            if result['success']:
                flash(result['message'], 'success')
                return redirect(url_for('simple_room.view_rooms', hostel_id=room['hostel_id']))
            else:
                flash(result['error'], 'error')
        
        return render_template(
            'simple_rooms/edit_room.html',
            room=room,
            statuses=SimpleRoomModel.VALID_STATUSES
        )
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('simple_room.view_rooms'))

@simple_room_bp.route('/<int:room_id>/delete', methods=['POST'])
def delete_room(room_id):
    """Delete a room."""
    try:
        # Get room details for permission check
        room = SimpleRoomModel.get_room_by_id(room_id)
        if not room:
            flash('Room not found!', 'error')
            return redirect(url_for('simple_room.view_rooms'))
        
        # Check permissions
        if g.user.get('role') == 'manager' and g.user.get('hostel_id') != room.get('hostel_id'):
            flash('You do not have permission to delete this room.', 'error')
            return redirect(url_for('simple_room.view_rooms'))
        
        result = SimpleRoomModel.delete_room(room_id)
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['error'], 'error')
        
        return redirect(url_for('simple_room.view_rooms', hostel_id=room['hostel_id']))
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('simple_room.view_rooms'))

@simple_room_bp.route('/<int:room_id>')
def view_room(room_id):
    """View room details."""
    try:
        # Get room details
        room = SimpleRoomModel.get_room_by_id(room_id)
        if not room:
            flash('Room not found!', 'error')
            return redirect(url_for('simple_room.view_rooms'))
        
        # Check permissions
        if g.user.get('role') == 'manager' and g.user.get('hostel_id') != room.get('hostel_id'):
            flash('You do not have permission to view this room.', 'error')
            return redirect(url_for('simple_room.view_rooms'))
        
        # Get room occupants
        occupants = SimpleRoomModel.get_room_occupants(room_id)
        
        # Calculate occupancy percentage
        if room['capacity'] > 0:
            room['occupancy_percentage'] = round((room['current_occupancy'] / room['capacity']) * 100, 1)
        else:
            room['occupancy_percentage'] = 0
        
        return render_template(
            'simple_rooms/room_details.html',
            room=room,
            occupants=occupants
        )
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('simple_room.view_rooms'))

@simple_room_bp.route('/available')
def available_rooms():
    """View available rooms."""
    try:
        hostel_id, hostel_name = get_user_hostel()
        
        # Get available rooms
        rooms = SimpleRoomModel.get_available_rooms(hostel_id=hostel_id)
        
        return render_template(
            'simple_rooms/available_rooms.html',
            rooms=rooms,
            current_hostel_name=hostel_name
        )
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('simple_room.view_rooms'))
