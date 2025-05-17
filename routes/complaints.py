"""
Maintenance and Complaints routes for the Hostel Management System
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import date
import sqlite3
from db_utils import get_db_connection, DatabaseConnection

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

        query = """
            SELECT c.id, c.reported_date, c.reported_by_name, c.description, c.priority, c.status, c.resolved_date,
                   s.name AS student_name, s.id AS student_id,
                   r.room_number, r.id AS room_id
            FROM complaints c
            LEFT JOIN students s ON c.student_id = s.id
            LEFT JOIN rooms r ON c.room_id = r.id
        """
        conditions = []
        params = []

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
        
        query += " ORDER BY c.reported_date DESC, c.priority, c.id DESC"

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

        return render_template('complaints/view_complaints.html', 
                               complaints=processed_complaints,
                               complaint_statuses=["Open", "In Progress", "Resolved", "Closed"],
                               complaint_priorities=["Low", "Medium", "High"],
                               request=request)

@complaints.route('/complaints/add', methods=['GET', 'POST'])
def add_complaint():
    with DatabaseConnection() as conn:
        if request.method == 'POST':
            reported_by_name = request.form.get('reported_by_name', '').strip()
            student_id_str = request.form.get('student_id')
            room_id_str = request.form.get('room_id')
            description = request.form['description'].strip()
            priority = request.form.get('priority', 'Medium')
            status = request.form.get('status', 'Open')

            student_id = int(student_id_str) if student_id_str else None
            room_id = int(room_id_str) if room_id_str else None

            if not description:
                flash('Description is required.', 'error')
                students = conn.execute("SELECT id, name, contact FROM students ORDER BY name").fetchall()
                rooms = conn.execute("SELECT id, room_number FROM rooms ORDER BY room_number").fetchall()
                return render_template('complaints/add_complaint.html', 
                                       students=students, rooms=rooms, 
                                       complaint_statuses=["Open", "In Progress", "Resolved", "Closed"],
                                       complaint_priorities=["Low", "Medium", "High"],
                                       form_data=request.form)
            try:
                conn.execute("""
                    INSERT INTO complaints (reported_by_name, student_id, room_id, description, priority, status, reported_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (reported_by_name, student_id, room_id, description, priority, status, date.today().isoformat()))
                flash('Complaint/Maintenance request added successfully!', 'success')
                return redirect(url_for('complaints.view_complaints'))
            except Exception as e:
                flash(f'An error occurred: {e}', 'error')
                students = conn.execute("SELECT id, name, contact FROM students ORDER BY name").fetchall()
                rooms = conn.execute("SELECT id, room_number FROM rooms ORDER BY room_number").fetchall()
                return render_template('complaints/add_complaint.html', 
                                       students=students, rooms=rooms,
                                       complaint_statuses=["Open", "In Progress", "Resolved", "Closed"],
                                       complaint_priorities=["Low", "Medium", "High"],
                                       form_data=request.form)

        # GET request
        students = conn.execute("SELECT id, name, contact FROM students ORDER BY name").fetchall()
        rooms = conn.execute("SELECT id, room_number FROM rooms ORDER BY room_number").fetchall()
        return render_template('complaints/add_complaint.html', 
                               students=students, 
                               rooms=rooms,
                               complaint_statuses=["Open", "In Progress", "Resolved", "Closed"],
                               complaint_priorities=["Low", "Medium", "High"])

@complaints.route('/complaints/edit/<int:complaint_id>', methods=['GET', 'POST'])
def edit_complaint(complaint_id):
    """Edit a maintenance complaint."""
    conn = get_db_connection()
    
    if request.method == 'POST':
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
            flash('Maintenance request updated successfully!', 'success')
            return redirect(url_for('complaints.view_complaints'))
        except sqlite3.Error as e:
            conn.rollback()
            flash(f'Error updating maintenance request: {e}', 'error')
        finally:
            conn.close()
    
    # Get complaint details
    complaint = conn.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
    if not complaint:
        conn.close()
        flash('Maintenance request not found', 'error')
        return redirect(url_for('complaints.view_complaints'))
    
    # Get list of rooms for the form
    rooms = conn.execute('SELECT id, room_number FROM rooms').fetchall()
    # Get list of students for the form
    students = conn.execute('SELECT id, name FROM students').fetchall()
    conn.close()
    
    return render_template('complaints/edit_complaint.html', 
                           complaint=complaint,
                           rooms=rooms, 
                           students=students,
                           complaint_statuses=COMPLAINT_STATUSES,
                           complaint_priorities=COMPLAINT_PRIORITIES)

@complaints.route('/complaints/delete/<int:complaint_id>', methods=['POST'])
def delete_complaint(complaint_id):
    """Delete a maintenance complaint."""
    conn = get_db_connection()
    
    try:
        conn.execute('BEGIN TRANSACTION')
        conn.execute('DELETE FROM complaints WHERE id = ?', (complaint_id,))
        conn.commit()
        flash('Maintenance request deleted successfully!', 'success')
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Error deleting maintenance request: {e}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('complaints.view_complaints'))
