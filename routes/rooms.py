"""
Room management routes for the Hostel Management System
Enhanced with comprehensive room management features
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, current_app
from models.db import RoomModel, StudentModel
from utils.export import ExportUtility
from datetime import datetime
from db_utils import get_db_connection, DatabaseConnection
from models.hostels import Hostel
from utils.socket_utils import emit_room_event
import json

# Dashboard updates integration
try:
    from routes.dashboard import emit_dashboard_update
    DASHBOARD_UPDATES_AVAILABLE = True
except ImportError:
    DASHBOARD_UPDATES_AVAILABLE = False
    def emit_dashboard_update(*args, **kwargs):
        pass

room_bp = Blueprint('room', __name__, url_prefix='/rooms')

def get_hostel_access_control(request_method='GET', hostel_id_param_name='hostel_id'):
    """
    Utility function to handle hostel access control based on user role.
    Returns a dictionary with hostel_id, current_hostel_name, and hostels_list.
    """
    hostel_id = None
    current_hostel_name = None
    hostels_list = []
    selected_hostel_id = None
    
    if hasattr(g, 'user') and g.user:
        if g.user.get('role') == 'manager':
            # Managers are restricted to their assigned hostel
            hostel_id = g.user.get('hostel_id')
            from models.hostels import Hostel
            hostel = Hostel.get_by_id(hostel_id)
            if hostel:
                current_hostel_name = hostel.name
        elif g.user.get('role') == 'owner':
            # Owners need to select a hostel
            from models.hostels import Hostel
            hostels_list = Hostel.get_all_hostels()
            
            # Check if hostel_id is in parameters (selected from dropdown)
            if request_method == 'GET':
                hostel_id_param = request.args.get(hostel_id_param_name)
                if hostel_id_param:
                    selected_hostel_id = int(hostel_id_param)
                    hostel_id = selected_hostel_id
                    hostel = Hostel.get_by_id(hostel_id)
                    if hostel:
                        current_hostel_name = hostel.name
    
    return {
        'hostel_id': hostel_id,
        'current_hostel_name': current_hostel_name,
        'hostels_list': hostels_list,
        'selected_hostel_id': selected_hostel_id
    }

@room_bp.route('/')
def view_rooms():
    """View all rooms with enhanced visualization and filtering."""
    try:
        # Get hostel access control
        access_control = get_hostel_access_control()
        hostel_id = access_control['hostel_id']
        current_hostel_name = access_control['current_hostel_name']
        hostels_list = access_control['hostels_list']
        
        # Get room filter parameters
        status_filter = request.args.get('status', '')
        capacity_filter = request.args.get('capacity', type=int)
        occupancy_filter = request.args.get('occupancy', '')
        search_query = request.args.get('search', '').strip()
        
        # Determine if detailed student information should be included
        include_students = request.args.get('include_students', 'false').lower() == 'true'
        
        # Get rooms with enhanced data
        rooms = RoomModel.get_all_rooms(
            hostel_id=hostel_id, 
            include_students=include_students
        )
        
        # Apply filters if specified
        if search_query:
            rooms = [r for r in rooms if search_query.lower() in r['room_number'].lower()]
        
        if status_filter:
            rooms = [r for r in rooms if r['status'] == status_filter]
            
        if capacity_filter and capacity_filter > 0:
            rooms = [r for r in rooms if r['capacity'] == capacity_filter]
            
        if occupancy_filter:
            if occupancy_filter == 'full':
                rooms = [r for r in rooms if r['current_occupancy'] >= r['capacity']]
            elif occupancy_filter == 'empty':
                rooms = [r for r in rooms if r['current_occupancy'] == 0]
            elif occupancy_filter == 'partial':
                rooms = [r for r in rooms if 0 < r['current_occupancy'] < r['capacity']]
            elif occupancy_filter == 'overbooked':
                rooms = [r for r in rooms if r['current_occupancy'] > r['capacity']]
        
        # Get view mode and sorting options
        view_mode = request.args.get('view', 'grid')
        sort_by = request.args.get('sort', 'room_number')
        sort_order = request.args.get('order', 'asc')
        
        # Sort rooms
        reverse_sort = sort_order == 'desc'
        if sort_by == 'occupancy':
            rooms.sort(key=lambda x: x['occupancy_percentage'], reverse=reverse_sort)
        elif sort_by == 'capacity':
            rooms.sort(key=lambda x: x['capacity'], reverse=reverse_sort)
        elif sort_by == 'status':
            rooms.sort(key=lambda x: x['status'], reverse=reverse_sort)
        else:  # Default to room_number
            rooms.sort(key=lambda x: x['room_number'], reverse=reverse_sort)
        
        # Get unique values for filter dropdowns with counts
        statuses = RoomModel.get_unique_statuses(hostel_id=hostel_id)
        capacities = RoomModel.get_unique_capacities(hostel_id=hostel_id)
          # Get room statistics for dashboard
        statistics = RoomModel.get_room_statistics(hostel_id=hostel_id)
        
        return render_template(
            'rooms/view_rooms.html', 
            rooms=rooms, 
            statuses=statuses,
            capacities=capacities,
            statistics=statistics,
            filters={
                'status': status_filter,
                'capacity': capacity_filter,
                'occupancy': occupancy_filter,
                'search': search_query,
                'include_students': include_students
            },
            sorting={
                'sort_by': sort_by,
                'sort_order': sort_order
            },
            view_mode=view_mode,
            current_hostel_name=current_hostel_name,
            hostels_list=hostels_list
        )
        
    except Exception as e:
        flash(f'Error loading rooms: {str(e)}', 'error')
        # Get access control for error case
        access_control = get_hostel_access_control()
        return render_template(
            'rooms/view_rooms.html',
            rooms=[],
            statuses=[],
            capacities=[],
            statistics={},
            filters={
                'status': '',
                'capacity': None,
                'occupancy': '',
                'search': '',
                'include_students': False
            },
            sorting={
                'sort_by': 'room_number',
                'sort_order': 'asc'
            },
            view_mode='grid',
            current_hostel_name=access_control.get('current_hostel_name'),
            hostels_list=access_control.get('hostels_list', [])
        )

@room_bp.route('/add', methods=['GET', 'POST'])
def add_room():
    """Add a new room with comprehensive validation."""
    try:
        # Get hostel access control
        access_control = get_hostel_access_control()
        hostel_id = access_control['hostel_id']
        current_hostel_name = access_control['current_hostel_name']
        hostels_list = access_control['hostels_list']
        
        # For owners, require hostel selection
        if g.user.get('role') == 'owner' and not hostel_id:
            # Try to get hostel_id from URL parameter
            hostel_id_param = request.args.get('hostel_id')
            if hostel_id_param:
                hostel_id = int(hostel_id_param)
                hostel = Hostel.get_by_id(hostel_id)
                if hostel:
                    current_hostel_name = hostel.name
            else:
                flash('Please select a hostel to add a room.', 'warning')
                return redirect(url_for('room.view_rooms'))
        
        if request.method == 'POST':
            # For owners, get hostel_id from form
            if g.user.get('role') == 'owner':
                form_hostel_id = request.form.get('hostel_id', type=int)
                if form_hostel_id:
                    hostel_id = form_hostel_id
            
            room_data = {
                'room_number': request.form.get('room_number', '').strip(),
                'capacity': request.form.get('capacity', type=int),
                'status': request.form.get('status', RoomModel.STATUS_AVAILABLE),
                'hostel_id': hostel_id,
                'floor': request.form.get('floor', type=int),
                'room_type': request.form.get('room_type', '').strip(),
                'facilities': request.form.get('facilities', '').strip(),
                'description': request.form.get('description', '').strip()
            }
            
            # Use the enhanced validation from RoomModel
            try:
                result = RoomModel.add_room(room_data)
                if result['success']:
                    # Emit Socket.IO event for new room addition
                    try:
                        from app import socketio
                        new_room_id = result.get('room_id')
                        if new_room_id:
                            room_event_data = {
                                'room_id': new_room_id,
                                'room_number': room_data['room_number'],
                                'hostel_id': hostel_id,
                                'hostel_name': current_hostel_name or '',
                                'status': room_data['status'],
                                'capacity': room_data['capacity'],
                                'current_occupancy': 0,
                                'available_spots': room_data['capacity'],
                                'action': 'added',
                                'timestamp': datetime.now().isoformat(),
                                'added_by': g.user.get('username', 'Unknown') if hasattr(g, 'user') and g.user else 'System'
                            }
                            emit_room_event('room_added', room_event_data, hostel_id)
                            
                            # Trigger dashboard update
                            if DASHBOARD_UPDATES_AVAILABLE:
                                emit_dashboard_update(hostel_id=hostel_id, update_type='room_added')
                                
                    except Exception as e:
                        current_app.logger.error(f"Socket.IO room addition event error: {str(e)}")
                    
                    flash(f'Room {room_data["room_number"]} added successfully!', 'success')
                    return redirect(url_for('room.view_rooms', hostel_id=hostel_id))
                else:
                    for error in result.get('errors', ['Unknown error']):
                        flash(f'Error adding room: {error}', 'error')
            except Exception as e:
                flash(f'Unexpected error adding room: {str(e)}', 'error')
        
        # Get available room statuses for the form
        available_statuses = [
            RoomModel.STATUS_AVAILABLE,
            RoomModel.STATUS_MAINTENANCE,
            RoomModel.STATUS_RESERVED
        ]
        
        return render_template(
            'rooms/add_room.html',
            current_hostel_name=current_hostel_name,
            hostels_list=hostels_list,
            available_statuses=available_statuses,
            room_data=request.form if request.method == 'POST' else {}
        )
    except Exception as e:
        flash(f'Error loading add room form: {str(e)}', 'error')
        return redirect(url_for('room.view_rooms'))

@room_bp.route('/<int:room_id>')
def view_room(room_id):
    """View room details with comprehensive information."""
    try:
        # Get room with detailed information including complaints and maintenance
        room = RoomModel.get_room_by_id(room_id, include_full_details=True)
        if not room:
            flash('Room not found!', 'error')
            return redirect(url_for('room.view_rooms'))
        
        # Check hostel access permissions
        access_control = get_hostel_access_control()
        user_hostel_id = access_control['hostel_id']
        
        # For managers, ensure they can only view rooms in their hostel
        if g.user.get('role') == 'manager' and user_hostel_id != room.get('hostel_id'):
            flash('You do not have permission to view this room.', 'error')
            return redirect(url_for('room.view_rooms'))
        
        # Get room occupants with detailed information
        occupants = RoomModel.get_room_occupants(room_id)
        
        # Get available rooms for potential transfers
        available_rooms = []
        if occupants:  # Only if there are occupants to potentially transfer
            available_rooms = RoomModel.get_available_rooms(
                hostel_id=room.get('hostel_id'),
                min_capacity=1
            )
        
        return render_template(
            'rooms/room_details.html', 
            room=room, 
            occupants=occupants,
            available_rooms=available_rooms
        )
    except Exception as e:
        flash(f'Error loading room details: {str(e)}', 'error')
        return redirect(url_for('room.view_rooms'))

@room_bp.route('/<int:room_id>/edit', methods=['GET', 'POST'])
def edit_room(room_id):
    """Edit room details with enhanced validation and error handling."""
    try:
        room = RoomModel.get_room_by_id(room_id)
        if not room:
            flash('Room not found!', 'error')
            return redirect(url_for('room.view_rooms'))
        
        # Check hostel access permissions
        access_control = get_hostel_access_control()
        user_hostel_id = access_control['hostel_id']
        current_hostel_name = access_control['current_hostel_name']
        hostels_list = access_control['hostels_list']
        
        # For managers, ensure they can only edit rooms in their hostel
        if g.user.get('role') == 'manager' and user_hostel_id != room.get('hostel_id'):
            flash('You do not have permission to edit this room.', 'error')
            return redirect(url_for('room.view_rooms'))
        
        if request.method == 'POST':
            room_data = {
                'room_number': request.form.get('room_number', '').strip(),
                'capacity': request.form.get('capacity', type=int),
                'status': request.form.get('status', '').strip(),
                'floor': request.form.get('floor', type=int),
                'room_type': request.form.get('room_type', '').strip(),
                'facilities': request.form.get('facilities', '').strip(),
                'description': request.form.get('description', '').strip()
            }
            
            # For owners, allow hostel_id changes
            if g.user.get('role') == 'owner':
                form_hostel_id = request.form.get('hostel_id', type=int)
                if form_hostel_id:
                    room_data['hostel_id'] = form_hostel_id
            
            # Use the enhanced validation and update from RoomModel
            try:
                result = RoomModel.update_room(room_id, room_data)
                if result['success']:
                    # Emit Socket.IO event for room status change
                    try:
                        from app import socketio
                        updated_room = RoomModel.get_room_by_id(room_id)
                        if updated_room:
                            room_event_data = {
                                'room_id': room_id,
                                'room_number': updated_room['room_number'],
                                'hostel_id': updated_room.get('hostel_id'),
                                'hostel_name': updated_room.get('hostel_name', ''),
                                'status': updated_room['status'],
                                'capacity': updated_room['capacity'],
                                'current_occupancy': updated_room['current_occupancy'],
                                'available_spots': updated_room['capacity'] - updated_room['current_occupancy'],
                                'occupancy_percentage': round((updated_room['current_occupancy'] / updated_room['capacity'] * 100) if updated_room['capacity'] > 0 else 0, 1),
                                'timestamp': datetime.now().isoformat(),
                                'updated_by': g.user.get('username', 'Unknown') if hasattr(g, 'user') and g.user else 'System'
                            }
                            emit_room_event('room_status_changed', room_event_data, updated_room.get('hostel_id'))
                    except Exception as e:
                        current_app.logger.error(f"Socket.IO room update event error: {str(e)}")
                    
                    flash(f'Room updated successfully! {result["message"]}', 'success')
                    return redirect(url_for('room.view_room', room_id=room_id))
                else:
                    for error in result.get('errors', []):
                        flash(error, 'error')
            except Exception as e:
                flash(f'Unexpected error updating room: {str(e)}', 'error')
        
        # Get available room statuses for the form
        available_statuses = RoomModel.VALID_STATUSES
        
        return render_template(
            'rooms/edit_room.html', 
            room=room,
            current_hostel_name=current_hostel_name,
            hostels_list=hostels_list,
            available_statuses=available_statuses,
            room_data=request.form if request.method == 'POST' else room
        )
    except Exception as e:
        flash(f'Error loading edit room form: {str(e)}', 'error')
        return redirect(url_for('room.view_rooms'))

@room_bp.route('/<int:room_id>/delete', methods=['POST'])
def delete_room(room_id):
    """Delete a room with comprehensive validation."""
    try:
        room = RoomModel.get_room_by_id(room_id)
        if not room:
            flash('Room not found!', 'error')
            return redirect(url_for('room.view_rooms'))
        
        # Check hostel access permissions
        access_control = get_hostel_access_control()
        user_hostel_id = access_control['hostel_id']
        
        # For managers, ensure they can only delete rooms in their hostel
        if g.user.get('role') == 'manager' and user_hostel_id != room.get('hostel_id'):
            flash('You do not have permission to delete this room.', 'error')
            return redirect(url_for('room.view_rooms'))
        
        # Use the enhanced deletion method from RoomModel
        result = RoomModel.delete_room(room_id)
        if result['success']:
            # Emit Socket.IO event for room deletion
            try:
                from app import socketio
                room_event_data = {
                    'room_id': room_id,
                    'room_number': room.get('room_number', f'Room {room_id}'),
                    'hostel_id': room.get('hostel_id'),
                    'hostel_name': room.get('hostel_name', ''),
                    'action': 'deleted',
                    'timestamp': datetime.now().isoformat(),
                    'deleted_by': g.user.get('username', 'Unknown') if hasattr(g, 'user') and g.user else 'System'
                }
                emit_room_event('room_deleted', room_event_data, room.get('hostel_id'))
            except Exception as e:
                current_app.logger.error(f"Socket.IO room deletion event error: {str(e)}")
            
            flash(result['message'], 'success')
        else:
            for error in result.get('errors', []):
                flash(error, 'error')
            return redirect(url_for('room.view_room', room_id=room_id))
        
    except Exception as e:
        flash(f'Unexpected error deleting room: {str(e)}', 'error')
    
    return redirect(url_for('room.view_rooms'))

@room_bp.route('/export')
def export_rooms():
    """Export rooms data to CSV or PDF with enhanced information."""
    try:
        # Get hostel access control
        access_control = get_hostel_access_control()
        hostel_id = access_control['hostel_id']
        
        # Get rooms data with enhanced information
        rooms = RoomModel.get_all_rooms(hostel_id=hostel_id, include_students=True)
        
        # Convert to export format
        room_data = []
        for room in rooms:
            # Calculate occupancy percentage
            occupancy_percentage = room.get('occupancy_percentage', 0)
            
            room_data.append({
                'Room Number': room['room_number'],
                'Hostel': room.get('hostel_name', 'N/A'),
                'Capacity': room['capacity'],
                'Current Occupancy': room['current_occupancy'],
                'Occupancy': f"{room['current_occupancy']}/{room['capacity']} ({occupancy_percentage:.1f}%)",
                'Status': room['status'],
                'Students': room.get('student_names', 'None'),
                'Complaints': room.get('complaint_count', 0),
                'Last Complaint': room.get('last_complaint_date', 'None')
            })
        
        # Determine export format
        export_format = request.args.get('format', 'csv').lower()
        
        # Prepare file name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_format == 'pdf':
            # Column headers for PDF
            headers = ['Room Number', 'Hostel', 'Capacity', 'Occupancy', 'Status', 'Students', 'Complaints']
            
            try:
                # Generate PDF
                pdf_response = ExportUtility.export_to_pdf(
                    data=room_data,
                    filename=f"rooms_report_{timestamp}.pdf",
                    title="Room Management Report",
                    description=f"Comprehensive room report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    headers=headers
                )
                
                if pdf_response is None:
                    flash('PDF export is not available. Please install reportlab package.', 'error')
                    return redirect(url_for('room.view_rooms'))
                
                return pdf_response
            except Exception as e:
                flash(f'Error generating PDF: {str(e)}', 'error')
                return redirect(url_for('room.view_rooms'))
        else:  # Default to CSV
            headers = ['Room Number', 'Hostel', 'Capacity', 'Current Occupancy', 'Occupancy', 'Status', 'Students', 'Complaints', 'Last Complaint']
            return ExportUtility.export_to_csv(
                data=room_data,
                filename=f"rooms_export_{timestamp}.csv",
                headers=headers
            )
    except Exception as e:
        flash(f'Error exporting rooms data: {str(e)}', 'error')
        return redirect(url_for('room.view_rooms'))

# New advanced room management routes

@room_bp.route('/statistics')
def statistics():
    """Display comprehensive room statistics dashboard."""
    try:
        # Get hostel access control
        access_control = get_hostel_access_control()
        hostel_id = access_control['hostel_id']
        current_hostel_name = access_control['current_hostel_name']
        hostels_list = access_control['hostels_list']
        
        # Get comprehensive statistics
        statistics = RoomModel.get_room_statistics(hostel_id=hostel_id)
        
        # Get chart data for visualizations
        chart_data = RoomModel.get_room_occupancy_chart_data(hostel_id=hostel_id)
        
        return render_template(
            'rooms/statistics.html',
            statistics=statistics,
            chart_data=chart_data,
            current_hostel_name=current_hostel_name,
            hostels_list=hostels_list
        )
    except Exception as e:
        flash(f'Error loading statistics: {str(e)}', 'error')
        return redirect(url_for('room.view_rooms'))

@room_bp.route('/maintenance-schedule')
def maintenance_schedule():
    """Display rooms needing maintenance attention."""
    try:
        # Get hostel access control
        access_control = get_hostel_access_control()
        hostel_id = access_control['hostel_id']
        current_hostel_name = access_control['current_hostel_name']
        hostels_list = access_control['hostels_list']
        
        # Get maintenance schedule
        days_ahead = request.args.get('days', default=30, type=int)
        maintenance_rooms = RoomModel.get_maintenance_schedule(hostel_id=hostel_id, days_ahead=days_ahead)
        
        return render_template(
            'rooms/maintenance_schedule.html',
            maintenance_rooms=maintenance_rooms,
            days_ahead=days_ahead,
            current_hostel_name=current_hostel_name,
            hostels_list=hostels_list
        )
    except Exception as e:
        flash(f'Error loading maintenance schedule: {str(e)}', 'error')
        return redirect(url_for('room.view_rooms'))

@room_bp.route('/bulk-update', methods=['GET', 'POST'])
def bulk_update():
    """Bulk update room statuses."""
    try:
        # Get hostel access control
        access_control = get_hostel_access_control()
        hostel_id = access_control['hostel_id']
        current_hostel_name = access_control['current_hostel_name']
        hostels_list = access_control['hostels_list']
        
        if request.method == 'POST':
            # Get selected room IDs and new status
            room_ids = request.form.getlist('room_ids')
            new_status = request.form.get('new_status')
            reason = request.form.get('reason', '').strip()
            
            if not room_ids:
                flash('Please select at least one room to update.', 'error')
            elif not new_status:
                flash('Please select a new status.', 'error')
            else:
                # Convert room IDs to integers
                try:
                    room_ids = [int(rid) for rid in room_ids]
                    
                    # Perform bulk update
                    result = RoomModel.bulk_update_status(room_ids, new_status, reason)
                    if result['success']:
                        # Emit Socket.IO event for bulk room status change
                        try:
                            from app import socketio
                            bulk_event_data = {
                                'room_ids': room_ids,
                                'new_status': new_status,
                                'reason': reason or 'No reason provided',
                                'room_count': len(room_ids),
                                'hostel_id': hostel_id,
                                'timestamp': datetime.now().isoformat(),
                                'updated_by': g.user.get('username', 'Unknown') if hasattr(g, 'user') and g.user else 'System'
                            }
                            emit_room_event('rooms_bulk_updated', bulk_event_data, hostel_id)
                        except Exception as e:
                            current_app.logger.error(f"Socket.IO bulk room update event error: {str(e)}")
                        
                        flash(result['message'], 'success')
                        return redirect(url_for('room.view_rooms'))
                    else:
                        for error in result.get('errors', []):
                            flash(error, 'error')
                except ValueError:
                    flash('Invalid room selection.', 'error')
        
        # Get rooms for selection (filtered by hostel access)
        rooms = RoomModel.get_all_rooms(hostel_id=hostel_id, include_students=False)
        available_statuses = RoomModel.VALID_STATUSES
        
        return render_template(
            'rooms/bulk_update.html',
            rooms=rooms,
            available_statuses=available_statuses,
            current_hostel_name=current_hostel_name,
            hostels_list=hostels_list
        )
    except Exception as e:
        flash(f'Error in bulk update: {str(e)}', 'error')
        return redirect(url_for('room.view_rooms'))

@room_bp.route('/api/chart-data')
def api_chart_data():
    """API endpoint for room occupancy chart data."""
    try:
        # Get hostel access control
        access_control = get_hostel_access_control()
        hostel_id = access_control['hostel_id']
        
        # Get chart data
        chart_data = RoomModel.get_room_occupancy_chart_data(hostel_id=hostel_id)
        
        return jsonify({
            'success': True,
            'data': chart_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@room_bp.route('/api/statistics')
def api_statistics():
    """API endpoint for room statistics."""
    try:
        # Get hostel access control
        access_control = get_hostel_access_control()
        hostel_id = access_control['hostel_id']
        
        # Get statistics
        statistics = RoomModel.get_room_statistics(hostel_id=hostel_id)
        
        return jsonify({
            'success': True,
            'statistics': statistics
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@room_bp.route('/available')
def available_rooms():
    """Display available rooms for assignment."""
    try:
        # Get hostel access control
        access_control = get_hostel_access_control()
        hostel_id = access_control['hostel_id']
        current_hostel_name = access_control['current_hostel_name']
        hostels_list = access_control['hostels_list']
        
        # Get filtering parameters
        min_capacity = request.args.get('min_capacity', type=int)
        
        # Get available rooms
        available_rooms = RoomModel.get_available_rooms(
            hostel_id=hostel_id,
            min_capacity=min_capacity
        )
        
        return render_template(
            'rooms/available_rooms.html',
            available_rooms=available_rooms,
            min_capacity=min_capacity,
            current_hostel_name=current_hostel_name,
            hostels_list=hostels_list
        )
    except Exception as e:
        flash(f'Error loading available rooms: {str(e)}', 'error')
        return redirect(url_for('room.view_rooms'))
