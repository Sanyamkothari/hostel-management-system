"""
Maintenance and Complaints routes for the Hostel Management System
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app
from datetime import date
import sqlite3
from db_utils import get_db_connection, DatabaseConnection

# Import for Socket.IO real-time updates
try:
    from app import socketio
    from utils.socket_utils import emit_complaint_event
    SOCKETIO_AVAILABLE = True
except ImportError:
    socketio = None
    SOCKETIO_AVAILABLE = False

complaints = Blueprint('complaints', __name__)

# Constants
COMPLAINT_STATUSES = ['Pending', 'In Progress', 'Resolved', 'Closed']
COMPLAINT_PRIORITIES = ['Low', 'Medium', 'High', 'Critical']

@complaints.route('/complaints')
def view_complaints():
    with DatabaseConnection() as conn:
        filter_room_number = request.args.get('filter_room_number', '').strip()
        filter_status = request.args.get('filter_status', '').strip()
        filter_priority = request.args.get('filter_priority', '').strip()

        # Use correct column names and aliases for report_date and resolution_date
        query = """
            SELECT c.id,
                   c.report_date AS reported_date,
                   c.description,
                   c.priority,
                   c.status,
                   c.resolution_date AS resolved_date,
                   s.name AS student_name,
                   s.id AS student_id,
                   r.room_number,
                   r.id AS room_id,
                   h.name AS hostel_name
            FROM complaints c
            LEFT JOIN students s ON c.reported_by_id = s.id
            LEFT JOIN rooms r ON c.room_id = r.id
            LEFT JOIN hostels h ON c.hostel_id = h.id
        """
        conditions = []
        params = []

        # Apply hostel security filter
        if hasattr(g, 'user') and g.user and g.user.get('role') == 'manager':
            conditions.append("c.hostel_id = ?")
            params.append(g.user.get('hostel_id'))
        elif not hasattr(g, 'user') or not g.user:
            # If no user is logged in, or user has no role, deny access or show nothing
            flash('You must be logged in to view complaints.', 'error')
            return redirect(url_for('auth.login'))

        if filter_room_number:
            conditions.append("r.room_number LIKE ?")
            params.append(f"%{filter_room_number}%")
        if filter_status:
            conditions.append("c.status = ?")
            params.append(filter_status)
        if filter_priority:
            conditions.append("c.priority = ?")
            params.append(filter_priority)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY c.report_date DESC, c.priority, c.id DESC"

        complaints_from_db = conn.execute(query, tuple(params)).fetchall()

        processed_complaints = []
        for complaint_row in complaints_from_db:
            complaint = dict(complaint_row)
            if complaint['reported_date']:
                try:
                    complaint['reported_date'] = date.fromisoformat(complaint['reported_date'])
                except (ValueError, TypeError):
                    complaint['reported_date'] = None
            if complaint['resolved_date']:
                try:
                    complaint['resolved_date'] = date.fromisoformat(complaint['resolved_date'])
                except (ValueError, TypeError):
                    complaint['resolved_date'] = None
            processed_complaints.append(complaint)

        # Prepare additional context for template
        current_user_role = g.user.get('role') if hasattr(g, 'user') and g.user else None
        hostels_list = []
        current_hostel_name = None
        selected_hostel_id = request.args.get('hostel_id_filter', type=int)
        if current_user_role == 'owner':
            from models.hostels import Hostel
            hostels_list = Hostel.get_all_hostels()
        elif current_user_role == 'manager':
            from models.hostels import Hostel
            hostel = Hostel.get_by_id(g.user.get('hostel_id'))
            current_hostel_name = hostel.name if hostel else None
        return render_template('complaints/view_complaints.html', 
                               complaints=processed_complaints,
                               complaint_statuses=["Open", "In Progress", "Resolved", "Closed"],
                               complaint_priorities=["Low", "Medium", "High"],
                               current_user_role=current_user_role,
                               hostels_list=hostels_list,
                               selected_hostel_id=selected_hostel_id,
                               current_hostel_name=current_hostel_name,
                               request=request)

@complaints.route('/complaints/add', methods=['GET', 'POST'])
def add_complaint():
    with DatabaseConnection() as conn:
        if request.method == 'POST':
            reported_by_name = request.form.get('reported_by_name', '').strip()
            reported_by_id_str = request.form.get('reported_by_id')
            room_id_str = request.form.get('room_id')
            description = request.form['description'].strip()
            priority = request.form.get('priority', 'Medium')
            status = request.form.get('status', 'Open')

            reported_by_id = int(reported_by_id_str) if reported_by_id_str else None
            room_id = int(room_id_str) if room_id_str else None
            hostel_id = None

            if hasattr(g, 'user') and g.user and g.user.get('role') == 'manager':
                hostel_id = g.user.hostel_id
            elif hasattr(g, 'user') and g.user and g.user.get('role') == 'owner':
                hostel_id = request.form.get('hostel_id', type=int)
                if not hostel_id:
                    flash('Owner must select a hostel for the new complaint.', 'error')
                    # Re-populate form data for owner, including hostel list
                    students = conn.execute("SELECT id, name, contact FROM students ORDER BY name").fetchall() # Needs hostel filtering for manager
                    rooms = conn.execute("SELECT id, room_number FROM rooms ORDER BY room_number").fetchall() # Needs hostel filtering for manager
                    hostels = conn.execute("SELECT id, name FROM hostels ORDER BY name").fetchall()
                    return render_template('complaints/add_complaint.html', 
                                           students=students, rooms=rooms, hostels_list=hostels, 
                                           complaint_statuses=COMPLAINT_STATUSES,
                                           complaint_priorities=COMPLAINT_PRIORITIES,
                                           form_data=request.form, current_user_role=g.user.get('role'))
            else:
                flash('Could not determine hostel for the complaint. Please login.', 'error')
                return redirect(url_for('auth.login'))

            if not description:
                flash('Description is required.', 'error')
                students = conn.execute("SELECT id, name, contact FROM students ORDER BY name").fetchall()
                rooms = conn.execute("SELECT id, room_number FROM rooms ORDER BY room_number").fetchall()
                hostels = conn.execute("SELECT id, name FROM hostels ORDER BY name").fetchall() if hasattr(g, 'user') and g.user and g.user.get('role') == 'owner' else []
                return render_template('complaints/add_complaint.html', 
                                       students=students, rooms=rooms, hostels_list=hostels, 
                                       complaint_statuses=["Open", "In Progress", "Resolved", "Closed"],
                                       complaint_priorities=["Low", "Medium", "High"],
                                       form_data=request.form, current_user_role=g.user.get('role'))
            
            try:
                cursor = conn.execute("""
                    INSERT INTO complaints (reported_by_name, reported_by_id, room_id, description, priority, status, report_date, hostel_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (reported_by_name, reported_by_id, room_id, description, priority, status, date.today().isoformat(), hostel_id))
                
                complaint_id = cursor.lastrowid
                
                # Get additional details for the real-time notification
                room_number = None
                student_name = reported_by_name if reported_by_name else None
                hostel_name = None
                
                if room_id:
                    room_result = conn.execute("SELECT room_number FROM rooms WHERE id = ?", (room_id,)).fetchone()
                    if room_result:
                        room_number = room_result['room_number']
                
                if hostel_id:
                    hostel_result = conn.execute("SELECT name FROM hostels WHERE id = ?", (hostel_id,)).fetchone()
                    if hostel_result:
                        hostel_name = hostel_result['name']
                  # Emit real-time notification for new complaint
                try:
                    emit_complaint_event('new_complaint', {
                        'id': complaint_id,
                        'description': description,
                        'priority': priority,
                        'status': status,
                        'student_name': student_name,
                        'room_number': room_number,
                        'hostel_id': hostel_id,
                        'hostel_name': hostel_name,
                        'report_date': date.today().isoformat(),
                        'message': f'New {priority.lower()} priority complaint: {description[:50]}...' if len(description) > 50 else f'New {priority.lower()} priority complaint: {description}'
                    }, hostel_id)
                except Exception as e:
                    print(f"Socket.IO emission error in add_complaint: {e}")
                
                flash('Complaint/Maintenance request added successfully!', 'success')
                return redirect(url_for('complaints.view_complaints'))
            except Exception as e:
                flash(f'An error occurred: {e}', 'error')
                students = conn.execute("SELECT id, name, contact FROM students ORDER BY name").fetchall()
                rooms = conn.execute("SELECT id, room_number FROM rooms ORDER BY room_number").fetchall()
                hostels = conn.execute("SELECT id, name FROM hostels ORDER BY name").fetchall() if hasattr(g, 'user') and g.user and g.user.get('role') == 'owner' else []
                return render_template('complaints/add_complaint.html', 
                                       students=students, rooms=rooms, hostels_list=hostels,
                                       complaint_statuses=["Open", "In Progress", "Resolved", "Closed"],
                                       complaint_priorities=["Low", "Medium", "High"],
                                       form_data=request.form, current_user_role=g.user.get('role'))

        # GET request
        students_query = "SELECT id, name, contact FROM students"
        rooms_query = "SELECT id, room_number FROM rooms"
        query_params = []

        if hasattr(g, 'user') and g.user and g.user.get('role') == 'manager':
            students_query += " WHERE hostel_id = ? ORDER BY name"
            rooms_query += " WHERE hostel_id = ? ORDER BY room_number"
            query_params.append(g.user.hostel_id)
            students = conn.execute(students_query, tuple(query_params)).fetchall()
            rooms = conn.execute(rooms_query, tuple(query_params)).fetchall()
        elif hasattr(g, 'user') and g.user and g.user.get('role') == 'owner':
            students = conn.execute(students_query + " ORDER BY name").fetchall()
            rooms = conn.execute(rooms_query + " ORDER BY room_number").fetchall()
        else: # Not logged in or no role
            flash('You need to be logged in to add a complaint.', 'error')
            return redirect(url_for('auth.login'))
        
        hostels_list = []
        if hasattr(g, 'user') and g.user and g.user.get('role') == 'owner':
            hostels_list = conn.execute("SELECT id, name FROM hostels ORDER BY name").fetchall()
        current_user_role = g.user.get('role') if hasattr(g, 'user') and g.user else None
        return render_template('complaints/add_complaint.html', 
                               students=students, 
                               rooms=rooms,
                               hostels_list=hostels_list,
                               complaint_statuses=COMPLAINT_STATUSES,
                               complaint_priorities=COMPLAINT_PRIORITIES,
                               current_user_role=current_user_role)

@complaints.route('/complaints/edit/<int:complaint_id>', methods=['GET', 'POST'])
def edit_complaint(complaint_id):
    """Edit a maintenance complaint."""
    # Ensure user has rights to edit this complaint (either owner or manager of the complaint's hostel)
    # This check should be done before fetching/displaying data or processing POST
    with DatabaseConnection() as conn:
        complaint_hostel_id = conn.execute("SELECT hostel_id FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        if not complaint_hostel_id:
            flash('Complaint not found.', 'error')
            return redirect(url_for('complaints.view_complaints'))
        
        complaint_hostel_id = complaint_hostel_id['hostel_id']

        if not (hasattr(g, 'user') and g.user and 
                (g.user.get('role') == 'owner' or 
                 (g.user.get('role') == 'manager' and g.user.get('hostel_id') == complaint_hostel_id))):
            flash('You do not have permission to edit this complaint.', 'error')
            return redirect(url_for('complaints.view_complaints'))

        if request.method == 'POST':
            # Get original complaint data for comparison
            original_complaint = conn.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
            original_status = original_complaint['status'] if original_complaint else None
            original_priority = original_complaint['priority'] if original_complaint else None
            
            room_id = request.form.get('room_id')
            reported_by_id = request.form.get('reported_by_id', None)
            description = request.form.get('description')
            priority = request.form.get('priority')
            status = request.form.get('status')
            resolution_notes = request.form.get('resolution_notes', '')
            resolution_date = request.form.get('resolution_date', None)
            
            # If status is Resolved and no resolution date is provided, set to today
            if status == 'Resolved' and not resolution_date:
                resolution_date = date.today().isoformat()
            
            try:
                conn.execute('BEGIN TRANSACTION')
                conn.execute('''
                    UPDATE complaints 
                    SET room_id = ?, reported_by_id = ?, description = ?, priority = ?, 
                        status = ?, resolution_notes = ?, resolution_date = ?
                    WHERE id = ?
                ''', (room_id, reported_by_id, description, priority, status, 
                      resolution_notes, resolution_date, complaint_id))
                conn.commit()
                
                # Emit real-time notification for complaint update
                try:
                    # Get additional details for notification
                    room_number = None
                    student_name = None
                    hostel_name = None
                    
                    if room_id:
                        room_result = conn.execute("SELECT room_number FROM rooms WHERE id = ?", (room_id,)).fetchone()
                        if room_result:
                            room_number = room_result['room_number']
                    
                    if reported_by_id:
                        student_result = conn.execute("SELECT name FROM students WHERE id = ?", (reported_by_id,)).fetchone()
                        if student_result:
                            student_name = student_result['name']
                    
                    if complaint_hostel_id:
                        hostel_result = conn.execute("SELECT name FROM hostels WHERE id = ?", (complaint_hostel_id,)).fetchone()
                        if hostel_result:
                            hostel_name = hostel_result['name']
                      # Determine what changed for the notification message
                    changes = []
                    if original_status != status:
                        changes.append(f"status: {original_status} → {status}")
                    if original_priority != priority:
                        changes.append(f"priority: {original_priority} → {priority}")
                    change_msg = ", ".join(changes) if changes else "details updated"
                    
                    emit_complaint_event('complaint_updated', {
                        'id': complaint_id,
                        'description': description,
                        'priority': priority,
                        'status': status,
                        'student_name': student_name,
                        'room_number': room_number,
                        'hostel_id': complaint_hostel_id,
                        'hostel_name': hostel_name,
                        'changes': changes,
                        'message': f'Complaint #{complaint_id} updated: {change_msg}'
                    }, complaint_hostel_id)
                except Exception as e:
                    print(f"Socket.IO emission error in edit_complaint: {e}")
                
                flash('Maintenance request updated successfully!', 'success')
                return redirect(url_for('complaints.view_complaints'))
            except sqlite3.Error as e:
                conn.rollback()
                flash(f'Error updating maintenance request: {e}', 'error')
        
        # Get complaint details
        complaint = conn.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
        if not complaint:
            flash('Maintenance request not found', 'error')
            return redirect(url_for('complaints.view_complaints'))
        
        # Get list of rooms and students for the form, filtered by hostel if manager
        rooms_query = 'SELECT id, room_number FROM rooms'
        students_query = 'SELECT id, name FROM students'
        query_params = []
        hostel_for_dropdowns = complaint_hostel_id # Use the complaint's hostel for dropdowns

        if hasattr(g, 'user') and g.user and g.user.get('role') == 'manager':
            # Manager should only see rooms/students from their own hostel, 
            # but for editing, it's tied to the complaint's hostel.
            # This logic assumes a manager can only edit complaints for their own hostel, enforced above.
            rooms_query += ' WHERE hostel_id = ?'
            students_query += ' WHERE hostel_id = ?'
            query_params.append(hostel_for_dropdowns)
        elif hasattr(g, 'user') and g.user and g.user.get('role') == 'owner':
            # Owner might be editing a complaint for a specific hostel, so filter dropdowns to that hostel.
            # Or, if they can change the hostel of a complaint, this needs more complex UI.
            # For now, assume dropdowns are relative to the complaint's current hostel.
            rooms_query += ' WHERE hostel_id = ?'
            students_query += ' WHERE hostel_id = ?'
            query_params.append(hostel_for_dropdowns)

        rooms = conn.execute(rooms_query, tuple(query_params)).fetchall()
        students = conn.execute(students_query, tuple(query_params)).fetchall()
        
        hostels = None
        if hasattr(g, 'user') and g.user and g.user.get('role') == 'owner':
            hostels = conn.execute("SELECT id, name FROM hostels ORDER BY name").fetchall()
        
        return render_template('complaints/edit_complaint.html', 
                               complaint=complaint,
                               rooms=rooms, 
                               students=students,
                               hostels=hostels, # Pass hostels for owner if they can change it
                               complaint_statuses=COMPLAINT_STATUSES,
                               complaint_priorities=COMPLAINT_PRIORITIES,
                               current_user=g.user, # Pass current_user
                               complaint_hostel_id=complaint_hostel_id) # Pass complaint's hostel_id

@complaints.route('/complaints/delete/<int:complaint_id>', methods=['POST'])
def delete_complaint(complaint_id):
    """Delete a maintenance complaint."""
    # Ensure user has rights to delete this complaint
    with DatabaseConnection() as conn:
        complaint_hostel_id = conn.execute("SELECT hostel_id FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        if not complaint_hostel_id:
            flash('Complaint not found.', 'error')
            return redirect(url_for('complaints.view_complaints'))
        
        complaint_hostel_id = complaint_hostel_id['hostel_id']

        if not (hasattr(g, 'user') and g.user and 
                (g.user.get('role') == 'owner' or 
                 (g.user.get('role') == 'manager' and g.user.get('hostel_id') == complaint_hostel_id))):
            flash('You do not have permission to delete this complaint.', 'error')
            return redirect(url_for('complaints.view_complaints'))

        # Get complaint details before deletion for notification
        complaint_to_delete = conn.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
        
        try:
            conn.execute('BEGIN TRANSACTION')
            conn.execute('DELETE FROM complaints WHERE id = ?', (complaint_id,))
            conn.commit()
            
            # Emit real-time notification for complaint deletion
            if complaint_to_delete:
                try:
                    # Get additional details for notification                    room_number = None
                    student_name = None
                    hostel_name = None
                    
                    if complaint_to_delete['room_id']:
                        room_result = conn.execute("SELECT room_number FROM rooms WHERE id = ?", (complaint_to_delete['room_id'],)).fetchone()
                        if room_result:
                            room_number = room_result['room_number']
                    
                    if complaint_to_delete['reported_by_id']:
                        student_result = conn.execute("SELECT name FROM students WHERE id = ?", (complaint_to_delete['reported_by_id'],)).fetchone()
                        if student_result:
                            student_name = student_result['name']
                    elif complaint_to_delete['reported_by_name']:
                        student_name = complaint_to_delete['reported_by_name']
                    
                    if complaint_to_delete['hostel_id']:
                        hostel_result = conn.execute("SELECT name FROM hostels WHERE id = ?", (complaint_to_delete['hostel_id'],)).fetchone()
                        if hostel_result:
                            hostel_name = hostel_result['name']
                    emit_complaint_event('complaint_deleted', {
                        'id': complaint_id,
                        'description': complaint_to_delete['description'],
                        'priority': complaint_to_delete['priority'],
                        'status': complaint_to_delete['status'],
                        'student_name': student_name,
                        'room_number': room_number,
                        'hostel_id': complaint_to_delete['hostel_id'],
                        'hostel_name': hostel_name,
                        'message': f'Complaint #{complaint_id} deleted: {complaint_to_delete["description"][:50]}...' if len(complaint_to_delete['description']) > 50 else f'Complaint #{complaint_id} deleted: {complaint_to_delete["description"]}'
                    }, complaint_to_delete['hostel_id'])
                except Exception as e:
                    print(f"Socket.IO emission error in delete_complaint: {e}")
            
            flash('Maintenance request deleted successfully!', 'success')
        except sqlite3.Error as e:
            conn.rollback()
            flash(f'Error deleting maintenance request: {e}', 'error')
        
        return redirect(url_for('complaints.view_complaints'))
