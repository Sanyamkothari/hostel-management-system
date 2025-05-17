"""
Room management routes for the Hostel Management System
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.db import RoomModel, StudentModel
from utils.export import ExportUtility
from datetime import datetime
from db_utils import get_db_connection, DatabaseConnection

room_bp = Blueprint('room', __name__, url_prefix='/rooms')

@room_bp.route('/')
def view_rooms():
    """View all rooms with enhanced visualization."""
    # Get room filter parameters
    status_filter = request.args.get('status', '')
    capacity_filter = request.args.get('capacity', type=int, default=0)
    occupancy_filter = request.args.get('occupancy', '')
    
    # Get rooms with their occupancy information
    rooms = RoomModel.get_all_rooms()
    
    # Apply filters if specified
    if status_filter:
        rooms = [r for r in rooms if r['status'] == status_filter]
    if capacity_filter > 0:
        rooms = [r for r in rooms if r['capacity'] == capacity_filter]
    if occupancy_filter:
        if occupancy_filter == 'full':
            rooms = [r for r in rooms if r['current_occupancy'] >= r['capacity']]
        elif occupancy_filter == 'empty':
            rooms = [r for r in rooms if r['current_occupancy'] == 0]
        elif occupancy_filter == 'partial':
            rooms = [r for r in rooms if 0 < r['current_occupancy'] < r['capacity']]
    
    # Determine the view mode (grid or list)
    view_mode = request.args.get('view', 'grid')
    
    # Get unique values for filter dropdowns
    statuses = RoomModel.get_unique_statuses()
    capacities = RoomModel.get_unique_capacities()
    
    return render_template(
        'rooms/view_rooms.html', 
        rooms=rooms, 
        statuses=statuses,
        capacities=capacities,
        filters={
            'status': status_filter,
            'capacity': capacity_filter,
            'occupancy': occupancy_filter
        },
        view_mode=view_mode
    )

@room_bp.route('/add', methods=['GET', 'POST'])
def add_room():
    """Add a new room."""
    if request.method == 'POST':
        room_data = {
            'room_number': request.form.get('room_number'),
            'capacity': request.form.get('capacity', type=int),
            'status': request.form.get('status', 'Available')
        }
        
        # Validate room data
        if not room_data['room_number'] or not room_data['capacity']:
            flash('Room number and capacity are required!', 'error')
            return render_template('rooms/add_room.html')
        
        if room_data['capacity'] <= 0:
            flash('Capacity must be greater than zero!', 'error')
            return render_template('rooms/add_room.html')
        
        try:
            RoomModel.add_room(room_data)
            flash('Room added successfully!', 'success')
            return redirect(url_for('room.view_rooms'))
        except Exception as e:
            flash(f'Error adding room: {str(e)}', 'error')
    
    return render_template('rooms/add_room.html')

@room_bp.route('/<int:room_id>')
def view_room(room_id):
    """View room details and occupants."""
    room = RoomModel.get_room_by_id(room_id)
    if not room:
        flash('Room not found!', 'error')
        return redirect(url_for('room.view_rooms'))
    
    occupants = RoomModel.get_room_occupants(room_id)
    
    return render_template(
        'rooms/room_details.html', 
        room=room, 
        occupants=occupants
    )

@room_bp.route('/<int:room_id>/edit', methods=['GET', 'POST'])
def edit_room(room_id):
    """Edit room details."""
    room = RoomModel.get_room_by_id(room_id)
    if not room:
        flash('Room not found!', 'error')
        return redirect(url_for('room.view_rooms'))
    
    if request.method == 'POST':
        room_data = {
            'room_number': request.form.get('room_number'),
            'capacity': request.form.get('capacity', type=int),
            'status': request.form.get('status')
        }
        
        # Validate room data
        if not room_data['room_number'] or not room_data['capacity']:
            flash('Room number and capacity are required!', 'error')
            return render_template('rooms/edit_room.html', room=room)
        
        if room_data['capacity'] < room['current_occupancy']:
            flash('New capacity cannot be less than current occupancy!', 'error')
            return render_template('rooms/edit_room.html', room=room)
        
        try:
            RoomModel.update_room(room_id, room_data)
            flash('Room updated successfully!', 'success')
            return redirect(url_for('room.view_room', room_id=room_id))
        except Exception as e:
            flash(f'Error updating room: {str(e)}', 'error')
    
    return render_template('rooms/edit_room.html', room=room)

@room_bp.route('/<int:room_id>/delete', methods=['POST'])
def delete_room(room_id):
    """Delete a room."""
    # Check if room has occupants
    occupants = RoomModel.get_room_occupants(room_id)
    if occupants:
        flash('Cannot delete room with occupants. Please reassign students first.', 'error')
        return redirect(url_for('room.view_room', room_id=room_id))
    
    try:
        RoomModel.delete_room(room_id)
        flash('Room deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting room: {str(e)}', 'error')
    
    return redirect(url_for('room.view_rooms'))

@room_bp.route('/export')
def export_rooms():
    """Export rooms data to CSV or PDF."""
    
    # Get all rooms data
    rooms = RoomModel.get_all_rooms_with_occupancy()
    
    # Convert SQLite Row objects to dictionaries
    room_data = []
    for room in rooms:
        room_dict = dict(room)  # Convert SQLite Row to dict
        
        # Calculate occupancy percentage
        occupancy_percentage = (room_dict['current_occupancy'] / room_dict['capacity'] * 100) if room_dict['capacity'] > 0 else 0
        
        room_data.append({
            'Room Number': room_dict['room_number'],
            'Capacity': room_dict['capacity'],
            'Occupancy': f"{room_dict['current_occupancy']}/{room_dict['capacity']} ({occupancy_percentage:.1f}%)",
            'Status': room_dict['status'],
            'Students': room_dict['student_names'] if room_dict['student_names'] else 'None'
        })
    
    # Determine export format
    export_format = request.args.get('format', 'csv').lower()
    
    # Prepare file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if export_format == 'pdf':
        # Column headers
        headers = ['Room Number', 'Capacity', 'Occupancy', 'Status', 'Students']
        
        # Generate PDF
        return ExportUtility.export_to_pdf(
            data=room_data,
            filename=f"rooms_report_{timestamp}.pdf",
            title="Room Occupancy Report",
            description=f"Room occupancy report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            headers=headers
        )
    else:  # Default to CSV
        headers = ['Room Number', 'Capacity', 'Occupancy', 'Status', 'Students']
        return ExportUtility.export_to_csv(
            data=room_data,
            filename=f"rooms_export_{timestamp}.csv",
            headers=headers
        )
