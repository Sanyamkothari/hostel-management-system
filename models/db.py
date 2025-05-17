"""
Database Models for Hostel Management System
This module handles database operations and schema definitions
"""

import sqlite3
import os
from datetime import date, timedelta
from pathlib import Path

# Database configuration
DATABASE = 'hostel.db'

def get_db_connection():
    """Establishes a connection to the database."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DATABASE)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def init_db(overwrite=False):
    """Initializes the database schema."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DATABASE)
    if overwrite and os.path.exists(db_path):
        os.remove(db_path)  # Remove existing DB if overwrite is true

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Students Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            student_id_number TEXT UNIQUE,
            contact TEXT,
            email TEXT UNIQUE,
            admission_date DATE DEFAULT CURRENT_DATE,
            expected_checkout_date DATE,
            course TEXT,
            room_id INTEGER,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL 
        )
    ''')
    
    # Student Details Table - for additional information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_details (
            student_id INTEGER PRIMARY KEY,
            home_address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            parent_name TEXT,
            parent_contact TEXT,
            emergency_contact_name TEXT,
            emergency_contact_phone TEXT,
            additional_notes TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        )
    ''')
    
    # Rooms Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT NOT NULL UNIQUE,
            capacity INTEGER NOT NULL,
            current_occupancy INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Available' -- e.g., Available, Full, Maintenance
        )
    ''')

    # Fees Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            due_date DATE,
            paid_date DATE,
            status TEXT DEFAULT 'Pending', -- Pending, Paid, Overdue
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        )
    ''')

    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_room_id ON students(room_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fees_student_id ON fees(student_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fees_status ON fees(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fees_due_date ON fees(due_date)')
    
    # Complaints Table for maintenance requests
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER,
            reported_by_id INTEGER,
            description TEXT NOT NULL,
            priority TEXT DEFAULT 'Medium', -- Low, Medium, High, Critical
            status TEXT DEFAULT 'Pending', -- Pending, In Progress, Resolved, Closed
            report_date DATE DEFAULT CURRENT_DATE,
            resolution_date DATE,
            resolution_notes TEXT,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL,
            FOREIGN KEY (reported_by_id) REFERENCES students(id) ON DELETE SET NULL
        )
    ''')
    
    # Create index for complaints
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_complaints_room_id ON complaints(room_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_complaints_priority ON complaints(priority)')

    conn.commit()
    conn.close()
    print("Database initialized/checked.")


# Student Model Operations
class StudentModel:
    @staticmethod
    def count_all_students():
        """Return the total count of students."""
        conn = get_db_connection()
        count = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
        conn.close()
        return count
        
    @staticmethod
    def get_all_students(search_params=None):
        """Retrieve all students with optional filtering."""
        conn = get_db_connection()
        query = '''
            SELECT s.id, s.name, s.student_id_number, s.contact, s.course, s.email, r.room_number 
            FROM students s 
            LEFT JOIN rooms r ON s.room_id = r.id
        '''
        conditions = []
        params = []

        if search_params:
            if search_params.get('name'):
                conditions.append("s.name LIKE ?")
                params.append(f"%{search_params['name']}%")
            if search_params.get('course'):
                conditions.append("s.course LIKE ?")
                params.append(f"%{search_params['course']}%")
            if search_params.get('room_number'):
                conditions.append("r.room_number LIKE ?")
                params.append(f"%{search_params['room_number']}%")
            if search_params.get('filter_course'):
                conditions.append("s.course = ?")
                params.append(search_params['filter_course'])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY s.name"

        students = conn.execute(query, tuple(params)).fetchall()
        conn.close()
        return students
    
    @staticmethod
    def get_student_by_id(student_id):
        """Get a single student by ID with their room information."""
        conn = get_db_connection()
        student = conn.execute('''
            SELECT s.*, r.room_number, r.capacity 
            FROM students s
            LEFT JOIN rooms r ON s.room_id = r.id
            WHERE s.id = ?
        ''', (student_id,)).fetchone()
        conn.close()
        return student
    
    @staticmethod
    def get_student_details(student_id):
        """Get additional details for a student."""
        conn = get_db_connection()
        details = conn.execute('''
            SELECT * FROM student_details WHERE student_id = ?
        ''', (student_id,)).fetchone()
        conn.close()
        return details
    
    @staticmethod
    def add_student(student_data, details_data=None):
        """Add a new student and optional details."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO students (
                    name, student_id_number, contact, course, email, 
                    room_id, admission_date, expected_checkout_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                student_data['name'],
                student_data.get('student_id_number', ''),
                student_data['contact'],
                student_data['course'],
                student_data['email'],
                student_data.get('room_id'),
                student_data.get('admission_date', date.today().isoformat()),
                student_data.get('expected_checkout_date', '')
            ))
            
            # Get the ID of the inserted student for student_details
            student_id = cursor.lastrowid
            
            # Insert student details if provided
            if details_data and any(details_data.values()):
                conn.execute('''
                    INSERT INTO student_details 
                    (student_id, home_address, city, state, zip_code, parent_name, parent_contact, 
                    emergency_contact_name, emergency_contact_phone, additional_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    student_id,
                    details_data.get('home_address', ''),
                    details_data.get('city', ''),
                    details_data.get('state', ''),
                    details_data.get('zip_code', ''),
                    details_data.get('parent_name', ''),
                    details_data.get('parent_contact', ''),
                    details_data.get('emergency_contact_name', ''),
                    details_data.get('emergency_contact_phone', ''),
                    details_data.get('additional_notes', '')
                ))
            
            conn.commit()
            
            # Update room occupancy if a room was assigned
            if student_data.get('room_id'):
                RoomModel.update_room_occupancy(conn, student_data['room_id'])
                
            return {'success': True, 'student_id': student_id}
        except sqlite3.IntegrityError as e:
            return {'success': False, 'error': e}
        finally:
            conn.close()

    @staticmethod
    def update_student(student_id, student_data, details_data=None):
        """Update an existing student and their details."""
        conn = get_db_connection()
        try:
            # Begin transaction
            conn.execute('BEGIN TRANSACTION')
            
            # Get current room assignment for comparison
            old_room_id = conn.execute(
                'SELECT room_id FROM students WHERE id = ?', (student_id,)
            ).fetchone()['room_id']
            
            # Update student information
            conn.execute('''
                UPDATE students 
                SET name = ?, student_id_number = ?, contact = ?, course = ?, email = ?, 
                    room_id = ?, admission_date = ?, expected_checkout_date = ?
                WHERE id = ?
            ''', (
                student_data['name'],
                student_data.get('student_id_number', ''),
                student_data['contact'],
                student_data['course'],
                student_data['email'],
                student_data.get('room_id'),
                student_data.get('admission_date', ''),
                student_data.get('expected_checkout_date', ''),
                student_id
            ))
            
            # Update or insert student details
            if details_data:
                # Check if details record exists
                details_exist = conn.execute(
                    'SELECT 1 FROM student_details WHERE student_id = ?', (student_id,)
                ).fetchone()
                
                if details_exist:
                    # Update existing details
                    conn.execute('''
                        UPDATE student_details
                        SET home_address = ?, city = ?, state = ?, zip_code = ?,
                            parent_name = ?, parent_contact = ?,
                            emergency_contact_name = ?, emergency_contact_phone = ?,
                            additional_notes = ?
                        WHERE student_id = ?
                    ''', (
                        details_data.get('home_address', ''),
                        details_data.get('city', ''),
                        details_data.get('state', ''),
                        details_data.get('zip_code', ''),
                        details_data.get('parent_name', ''),
                        details_data.get('parent_contact', ''),
                        details_data.get('emergency_contact_name', ''),
                        details_data.get('emergency_contact_phone', ''),
                        details_data.get('additional_notes', ''),
                        student_id
                    ))
                else:
                    # Insert new details record
                    if any(v for k, v in details_data.items() if v):
                        conn.execute('''
                            INSERT INTO student_details
                            (student_id, home_address, city, state, zip_code, parent_name, parent_contact,
                            emergency_contact_name, emergency_contact_phone, additional_notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            student_id,
                            details_data.get('home_address', ''),
                            details_data.get('city', ''),
                            details_data.get('state', ''),
                            details_data.get('zip_code', ''),
                            details_data.get('parent_name', ''),
                            details_data.get('parent_contact', ''),
                            details_data.get('emergency_contact_name', ''),
                            details_data.get('emergency_contact_phone', ''),
                            details_data.get('additional_notes', '')
                        ))
            
            # Commit the transaction
            conn.commit()
            
            # Update room occupancy if changed
            new_room_id = student_data.get('room_id')
            if old_room_id != new_room_id:
                if old_room_id is not None:
                    RoomModel.update_room_occupancy(conn, old_room_id)
                if new_room_id is not None:
                    RoomModel.update_room_occupancy(conn, new_room_id)
            
            return {'success': True}
        except sqlite3.IntegrityError as e:
            conn.execute('ROLLBACK')
            return {'success': False, 'error': e}
        finally:
            conn.close()
    
    @staticmethod
    def delete_student(student_id):
        """Delete a student and update room occupancy."""
        conn = get_db_connection()
        try:
            # Get the student's room assignment before deleting
            student = conn.execute('SELECT room_id FROM students WHERE id = ?', (student_id,)).fetchone()
            if not student:
                return {'success': False, 'error': 'Student not found'}
                
            room_id = student['room_id']
            
            # Delete the student (this also deletes associated details and fees due to CASCADE)
            conn.execute('DELETE FROM students WHERE id = ?', (student_id,))
            conn.commit()
            
            # Update room occupancy if needed
            if room_id:
                RoomModel.update_room_occupancy(conn, room_id)
                
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': e}
        finally:
            conn.close()
    
    @staticmethod
    def get_student_fees(student_id):
        """Get all fees for a student."""
        conn = get_db_connection()
        fees = conn.execute('''
            SELECT f.id, f.amount, f.due_date, f.paid_date, f.status
            FROM fees f
            WHERE f.student_id = ?
            ORDER BY f.due_date DESC
        ''', (student_id,)).fetchall()
        conn.close()
        
        # Process fees to identify overdue ones
        today = date.today()
        processed_fees = []
        total_paid = total_pending = 0
        
        for fee_row in fees:
            fee = dict(fee_row)
            fee['is_overdue'] = False
            
            # Check for overdue
            if fee['status'] == 'Pending' and fee['due_date']:
                try:
                    due_date_obj = date.fromisoformat(fee['due_date'])
                    if due_date_obj < today:
                        fee['is_overdue'] = True
                except (ValueError, TypeError):
                    pass
            
            # Format dates
            if fee['due_date']:
                try:
                    fee['due_date'] = date.fromisoformat(fee['due_date'])
                except ValueError:
                    fee['due_date'] = None
            if fee['paid_date']:
                try:
                    fee['paid_date'] = date.fromisoformat(fee['paid_date'])
                except ValueError:
                    fee['paid_date'] = None
            
            # Calculate totals
            if fee['status'] == 'Paid':
                total_paid += fee['amount']
            else:
                total_pending += fee['amount']
                
            processed_fees.append(fee)
        
        return {
            'fees': processed_fees,
            'total_paid': total_paid,
            'total_pending': total_pending
        }
    
    @staticmethod
    def get_recent_students(limit=5):
        """Get recently admitted students."""
        conn = get_db_connection()
        recent_students = conn.execute('''
            SELECT id, name, admission_date 
            FROM students 
            ORDER BY admission_date DESC, id DESC
            LIMIT ?
        ''', (limit,)).fetchall()
        conn.close()
        return recent_students
        
    @staticmethod
    def get_all_courses():
        """Return all distinct courses."""
        conn = get_db_connection()
        courses = conn.execute(
            "SELECT DISTINCT course FROM students WHERE course IS NOT NULL AND course != '' ORDER BY course"
        ).fetchall()
        conn.close()
        return courses


# Room Model Operations
class RoomModel:
    @staticmethod
    def get_all_rooms(search_params=None):
        """Get all rooms with optional filtering."""
        conn = get_db_connection()
        query = '''
            SELECT r.id, r.room_number, r.capacity, r.current_occupancy, r.status 
            FROM rooms r
        '''
        conditions = []
        params = []

        if search_params:
            if search_params.get('room_number'):
                conditions.append("r.room_number LIKE ?")
                params.append(f"%{search_params['room_number']}%")
            
            if search_params.get('filter_status'):
                conditions.append("r.status = ?")
                params.append(search_params['filter_status'])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY r.room_number"

        rooms = conn.execute(query, tuple(params)).fetchall()
        
        # Convert to list of dicts and add students in each room
        rooms_with_students = []
        for room_row in rooms:
            room = dict(room_row)
            students = conn.execute(
                'SELECT id, name FROM students WHERE room_id = ? ORDER BY name', 
                (room['id'],)
            ).fetchall()
            room['students'] = students
            rooms_with_students.append(room)
        
        conn.close()
        return rooms_with_students
    
    @staticmethod
    def get_room_by_id(room_id):
        """Get a single room by ID."""
        conn = get_db_connection()
        room = conn.execute('SELECT * FROM rooms WHERE id = ?', (room_id,)).fetchone()
        conn.close()
        return room
    
    @staticmethod
    def add_room(room_data):
        """Add a new room."""
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO rooms (room_number, capacity, status) VALUES (?, ?, ?)',
                (room_data['room_number'], room_data['capacity'], room_data.get('status', 'Available'))
            )
            conn.commit()
            return {'success': True}
        except sqlite3.IntegrityError as e:
            return {'success': False, 'error': e}
        finally:
            conn.close()
    
    @staticmethod
    def update_room(room_id, room_data):
        """Update an existing room."""
        conn = get_db_connection()
        try:
            conn.execute(
                'UPDATE rooms SET room_number = ?, capacity = ?, status = ? WHERE id = ?',
                (room_data['room_number'], room_data['capacity'], room_data['status'], room_id)
            )
            conn.commit()
            
            # Update occupancy after capacity/status change
            RoomModel.update_room_occupancy(conn, room_id)
            
            return {'success': True}
        except sqlite3.IntegrityError as e:
            return {'success': False, 'error': e}
        finally:
            conn.close()
    
    @staticmethod
    def delete_room(room_id):
        """Delete a room if unoccupied."""
        conn = get_db_connection()
        try:
            # Check if room has occupants
            occupants = conn.execute(
                'SELECT COUNT(*) FROM students WHERE room_id = ?', (room_id,)
            ).fetchone()[0]
            
            if occupants > 0:
                return {
                    'success': False, 
                    'error': 'Cannot delete room: It is currently occupied. Please reassign students first.'
                }
            
            conn.execute('DELETE FROM rooms WHERE id = ?', (room_id,))
            conn.commit()
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': e}
        finally:
            conn.close()
    
    @staticmethod
    def update_room_occupancy(conn, room_id):
        """Update the current_occupancy and status of a room."""
        if room_id is None:
            return
        
        # This function accepts an existing connection to support transactions
        cursor = conn.cursor()
        
        # Calculate current occupancy
        cursor.execute('SELECT COUNT(*) FROM students WHERE room_id = ?', (room_id,))
        count = cursor.fetchone()[0]
        
        # Get room capacity
        cursor.execute('SELECT capacity FROM rooms WHERE id = ?', (room_id,))
        capacity_row = cursor.fetchone()
        if capacity_row:
            capacity = capacity_row['capacity']
            new_status = 'Available'
            if count >= capacity:
                new_status = 'Full'
            
            cursor.execute(
                'UPDATE rooms SET current_occupancy = ?, status = ? WHERE id = ?', 
                (count, new_status, room_id)
            )
            conn.commit()
    
    @staticmethod
    def get_available_rooms():
        """Get rooms available for assignment."""
        conn = get_db_connection()
        rooms = conn.execute('''
            SELECT id, room_number, capacity, current_occupancy, status 
            FROM rooms 
            WHERE status = 'Available' 
            ORDER BY room_number
        ''').fetchall()
        conn.close()
        return rooms
    
    @staticmethod
    def get_room_statistics():
        """Get statistics about rooms."""
        conn = get_db_connection()
        
        # Get overall room stats
        stats = {}
        
        # Total rooms
        stats['total_rooms'] = conn.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]
        
        # Rooms by status
        stats['available_rooms'] = conn.execute("SELECT COUNT(*) FROM rooms WHERE status = 'Available'").fetchone()[0]
        stats['occupied_rooms'] = conn.execute("SELECT COUNT(*) FROM rooms WHERE status = 'Full'").fetchone()[0]
        stats['maintenance_rooms'] = conn.execute("SELECT COUNT(*) FROM rooms WHERE status = 'Maintenance'").fetchone()[0]
        
        # Capacity and occupancy
        stats['total_capacity'] = conn.execute('SELECT SUM(capacity) FROM rooms').fetchone()[0] or 0
        stats['current_occupancy'] = conn.execute('SELECT COUNT(*) FROM students WHERE room_id IS NOT NULL').fetchone()[0]
        
        conn.close()
        return stats
        
    @staticmethod
    def get_room_occupancy_chart_data():
        """Get data formatted for room occupancy chart."""
        conn = get_db_connection()
        rooms = conn.execute('''
            SELECT id, room_number, capacity, current_occupancy, status 
            FROM rooms
            ORDER BY room_number
        ''').fetchall()
        
        # Convert to list of dictionaries
        room_data = []
        for room in rooms:
            room_data.append({
                'id': room['id'],
                'room_number': room['room_number'],
                'capacity': room['capacity'],
                'current_occupancy': room['current_occupancy'],
                'status': room['status']
            })
        
        conn.close()
        return room_data
        
    @staticmethod
    def get_unique_statuses():
        """Get a list of unique room statuses from the database.
        
        Returns:
            List of unique status strings
        """
        conn = get_db_connection()
        statuses = conn.execute('SELECT DISTINCT status FROM rooms').fetchall()
        conn.close()
        
        # Extract status values from rows
        return [status['status'] for status in statuses]
    
    @staticmethod
    def get_unique_capacities():
        """Get a list of unique room capacities from the database.
        
        Returns:
            List of unique capacity integers
        """
        conn = get_db_connection()
        capacities = conn.execute('SELECT DISTINCT capacity FROM rooms ORDER BY capacity').fetchall()
        conn.close()
        
        # Extract capacity values from rows
        return [capacity['capacity'] for capacity in capacities]
        
    @staticmethod
    def get_all_rooms_with_occupancy():
        """Get all rooms with detailed occupancy information.
        
        Returns:
            List of room dictionaries with occupancy details
        """
        conn = get_db_connection()
        
        # Get all rooms
        rooms = conn.execute('''
            SELECT r.id, r.room_number, r.capacity, r.current_occupancy, r.status
            FROM rooms r
            ORDER BY r.room_number
        ''').fetchall()
        
        # Get student details for each room
        result = []
        for room in rooms:
            room_dict = dict(room)
            
            # Get students in this room
            students = conn.execute('''
                SELECT s.id, s.name, s.student_id_number, s.course
                FROM students s
                WHERE s.room_id = ?
                ORDER BY s.name
            ''', (room['id'],)).fetchall()
            
            # Calculate occupancy percentage
            if room['capacity'] > 0:
                room_dict['occupancy_percentage'] = (room['current_occupancy'] / room['capacity']) * 100
            else:
                room_dict['occupancy_percentage'] = 0
                
            # Add students to room data
            room_dict['students'] = [dict(student) for student in students]
            
            result.append(room_dict)
            
        conn.close()
        return result
        
    @staticmethod
    def get_unique_statuses():
        """Get a list of unique room statuses from the database.
        
        Returns:
            List of unique status strings
        """
        conn = get_db_connection()
        statuses = conn.execute('SELECT DISTINCT status FROM rooms').fetchall()
        conn.close()
        
        # Extract status values from rows
        return [status['status'] for status in statuses]
    
    @staticmethod
    def get_all_rooms_with_occupancy():
        """Get all rooms with detailed occupancy information.
        
        Returns:
            List of room dictionaries with occupancy details
        """
        conn = get_db_connection()
        
        # Get all rooms
        rooms = conn.execute('''
            SELECT r.id, r.room_number, r.capacity, r.current_occupancy, r.status
            FROM rooms r
            ORDER BY r.room_number
        ''').fetchall()
        
        # Get student details for each room
        result = []
        for room in rooms:
            room_dict = dict(room)
            
            # Get students in this room
            students = conn.execute('''
                SELECT s.id, s.name, s.student_id_number, s.course
                FROM students s
                WHERE s.room_id = ?
                ORDER BY s.name
            ''', (room['id'],)).fetchall()
            
            # Calculate occupancy percentage
            if room['capacity'] > 0:
                room_dict['occupancy_percentage'] = (room['current_occupancy'] / room['capacity']) * 100
            else:
                room_dict['occupancy_percentage'] = 0
                
            # Add students to room data
            room_dict['students'] = [dict(student) for student in students]
            
            result.append(room_dict)
            
        conn.close()
        return result

# Fee Model Operations
class FeeModel:
    @staticmethod
    def get_unique_statuses():
        """Get a list of unique fee statuses from the database.
        
        Returns:
            List of unique status strings
        """
        conn = get_db_connection()
        statuses = conn.execute('SELECT DISTINCT status FROM fees').fetchall()
        conn.close()
        
        # Extract status values from rows
        return [status['status'] for status in statuses]
    
    @staticmethod
    def get_all_fees():
        """Get all fee records."""
        conn = get_db_connection()
        fees = conn.execute('''
            SELECT f.id, s.name AS student_name, f.student_id, f.amount, f.due_date, f.paid_date, f.status
            FROM fees f
            JOIN students s ON f.student_id = s.id
            ORDER BY f.due_date ASC, s.name ASC
        ''').fetchall()
        conn.close()
        
        processed_fees = []
        today = date.today()
        
        for fee_row in fees:
            fee = dict(fee_row)
            fee['is_overdue'] = False
            
            if fee['status'] == 'Pending' and fee['due_date']:
                try:
                    due_date_obj = date.fromisoformat(fee['due_date'])
                    if due_date_obj < today:
                        fee['is_overdue'] = True
                except (ValueError, TypeError):
                    pass
            
            # Convert date strings to date objects for consistent formatting
            if fee['due_date']:
                try:
                    fee['due_date'] = date.fromisoformat(fee['due_date'])
                except ValueError:
                    fee['due_date'] = None
            if fee['paid_date']:
                try:
                    fee['paid_date'] = date.fromisoformat(fee['paid_date'])
                except ValueError:
                    fee['paid_date'] = None
                    
            processed_fees.append(fee)
        
        return processed_fees
        
    @staticmethod
    def get_all_fees_with_students(filter_params=None):
        """Get all fees with student information and apply filters.
        
        Args:
            filter_params: Dictionary containing filter parameters
                - status: Filter by fee status
                - student_name: Filter by student name
                - amount_min: Minimum fee amount
                - amount_max: Maximum fee amount
                - start_date: Start date for due date range
                - end_date: End date for due date range
                
        Returns:
            List of fee dictionaries with student information
        """
        conn = get_db_connection()
        
        # Start building the query
        query = '''
            SELECT f.id, s.name AS student_name, f.student_id, f.amount, 
                   f.due_date, f.paid_date, f.status, r.room_number
            FROM fees f
            JOIN students s ON f.student_id = s.id
            LEFT JOIN rooms r ON s.room_id = r.id
        '''
        
        # Add WHERE clauses based on filters
        conditions = []
        params = []
        
        if filter_params:
            if filter_params.get('status'):
                conditions.append("f.status = ?")
                params.append(filter_params['status'])
                
            if filter_params.get('student_name'):
                conditions.append("s.name LIKE ?")
                params.append(f"%{filter_params['student_name']}%")
                
            if filter_params.get('amount_min'):
                conditions.append("f.amount >= ?")
                params.append(filter_params['amount_min'])
                
            if filter_params.get('amount_max'):
                conditions.append("f.amount <= ?")
                params.append(filter_params['amount_max'])
                
            if filter_params.get('start_date'):
                conditions.append("f.due_date >= ?")
                params.append(filter_params['start_date'].isoformat())
                
            if filter_params.get('end_date'):
                conditions.append("f.due_date <= ?")
                params.append(filter_params['end_date'].isoformat())
        
        # Add conditions to query if any
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        # Add ordering
        query += " ORDER BY f.due_date ASC, s.name ASC"
        
        # Execute query
        fees = conn.execute(query, params).fetchall()
        conn.close()
        
        # Process fees
        processed_fees = []
        today = date.today()
        
        for fee_row in fees:
            fee = dict(fee_row)
            fee['is_overdue'] = False
            
            if fee['status'] == 'Pending' and fee['due_date']:
                try:
                    due_date_obj = date.fromisoformat(fee['due_date'])
                    if due_date_obj < today:
                        fee['is_overdue'] = True
                except (ValueError, TypeError):
                    pass
            
            processed_fees.append(fee)
        
        return processed_fees
    
    @staticmethod
    def add_fee(fee_data):
        """Add a new fee record."""
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO fees (student_id, amount, due_date, status) VALUES (?, ?, ?, ?)',
                (
                    fee_data['student_id'], 
                    fee_data['amount'], 
                    fee_data['due_date'], 
                    fee_data.get('status', 'Pending')
                )
            )
            conn.commit()
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': e}
        finally:
            conn.close()
    
    @staticmethod
    def mark_fee_paid(fee_id):
        """Mark a fee as paid."""
        conn = get_db_connection()
        try:
            today = date.today().strftime('%Y-%m-%d')
            conn.execute(
                "UPDATE fees SET status = 'Paid', paid_date = ? WHERE id = ?", 
                (today, fee_id)
            )
            conn.commit()
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': e}
        finally:
            conn.close()
    
    @staticmethod
    def get_fee_report(filters=None, period='monthly', year=None, month=None):
        """Get fee report with optional filtering.
        
        Args:
            filters: Dictionary of filter parameters
            period: Report period ('monthly', 'quarterly', 'yearly')
            year: Year for the report
            month: Month for the report (if period is 'monthly')
            
        Returns:
            Dictionary containing report data
        """
        conn = get_db_connection()
        today = date.today()
        
        # Set default year to current year if not provided
        if year is None:
            year = today.year
            
        # Set default month to current month if not provided
        if month is None and period == 'monthly':
            month = today.month
            
        base_query = """
            SELECT f.id, s.name AS student_name, s.id AS student_id_fk, s.student_id_number, 
                   f.amount, f.due_date, f.paid_date, f.status
            FROM fees f
            JOIN students s ON f.student_id = s.id
        """
        conditions = []
        params = []
        
        if filters:
            if filters.get('start_date'):
                conditions.append("f.due_date >= ?")
                params.append(filters['start_date'])
            if filters.get('end_date'):
                conditions.append("f.due_date <= ?")
                params.append(filters['end_date'])
            if filters.get('student_id_filter'):
                conditions.append("s.id = ?")
                params.append(filters['student_id_filter'])
            
            # Special handling for 'Overdue' status filter
            if filters.get('payment_status_filter') and filters['payment_status_filter'] != 'Overdue':
                conditions.append("f.status = ?")
                params.append(filters['payment_status_filter'])
            elif filters.get('payment_status_filter') == 'Overdue':
                conditions.append("f.status IN ('Pending', 'Overdue')")
                conditions.append("f.due_date < ?")
                params.append(today.isoformat())
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        
        base_query += " ORDER BY f.due_date DESC, s.name ASC"
        
        fees = conn.execute(base_query, tuple(params)).fetchall()
        processed_fees = []
        
        for fee_row in fees:
            fee = dict(fee_row)
            fee['is_overdue'] = False
            
            if fee['status'] != 'Paid' and fee['due_date']:
                try:
                    due_date_obj = date.fromisoformat(fee['due_date'])
                    if due_date_obj < today:
                        fee['is_overdue'] = True
                except (ValueError, TypeError):
                    pass
            
            # Convert date strings to date objects for consistent formatting
            if fee['due_date']:
                try:
                    fee['due_date'] = date.fromisoformat(fee['due_date'])
                except ValueError:
                    fee['due_date'] = None
            if fee['paid_date']:
                try:
                    fee['paid_date'] = date.fromisoformat(fee['paid_date'])
                except ValueError:
                    fee['paid_date'] = None
                    
            processed_fees.append(fee)
        
        # If filtering by 'Overdue', re-filter the list
        if filters and filters.get('payment_status_filter') == 'Overdue':
            processed_fees = [f for f in processed_fees if f['is_overdue']]
        
        students_for_filter = conn.execute(
            "SELECT id, name, student_id_number FROM students ORDER BY name"
        ).fetchall()
        
        conn.close()
        
        # Calculate summary statistics
        paid_count = sum(1 for f in processed_fees if f['status'] == 'Paid')
        pending_count = sum(1 for f in processed_fees if f['status'] == 'Pending' and not f['is_overdue'])
        overdue_count = sum(1 for f in processed_fees if f['status'] == 'Pending' and f['is_overdue'])
        paid_amount = sum(f['amount'] for f in processed_fees if f['status'] == 'Paid')
        pending_amount = sum(f['amount'] for f in processed_fees if f['status'] == 'Pending' and not f['is_overdue'])
        overdue_amount = sum(f['amount'] for f in processed_fees if f['status'] == 'Pending' and f['is_overdue'])
        
        return {
            'fees': processed_fees,
            'students_for_filter': students_for_filter,
            'paid_count': paid_count,
            'pending_count': pending_count,
            'overdue_count': overdue_count,
            'paid_amount': paid_amount,
            'pending_amount': pending_amount,
            'overdue_amount': overdue_amount
        }
    
    @staticmethod
    def get_fee_statistics():
        """Get statistics about fees."""
        conn = get_db_connection()
        today = date.today().isoformat()
        
        # Fee counts
        pending_count = conn.execute("SELECT COUNT(*) FROM fees WHERE status = 'Pending'").fetchone()[0]
        overdue_count = conn.execute(
            "SELECT COUNT(*) FROM fees WHERE status = 'Pending' AND due_date < ?", 
            (today,)
        ).fetchone()[0]
        
        # Fee amounts
        pending_amount = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM fees WHERE status = 'Pending'"
        ).fetchone()[0]
        
        overdue_amount = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM fees WHERE status = 'Pending' AND due_date < ?",
            (today,)
        ).fetchone()[0]
        
        paid_amount = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM fees WHERE status = 'Paid'"
        ).fetchone()[0]
        
        conn.close()
        
        return {
            'pending_count': pending_count,
            'overdue_count': overdue_count,
            'pending_amount': pending_amount,
            'overdue_amount': overdue_amount,
            'paid_amount': paid_amount
        }
    
    @staticmethod
    def get_upcoming_fees(limit=5, days=30):
        """Get upcoming fee payments due within the specified number of days."""
        conn = get_db_connection()
        today = date.today()
        future_date = (today + timedelta(days=days)).isoformat()
        
        upcoming_fees = conn.execute('''
            SELECT f.id, f.amount, f.due_date, s.name as student_name, s.id as student_id
            FROM fees f
            JOIN students s ON f.student_id = s.id
            WHERE f.status = 'Pending' AND f.due_date BETWEEN ? AND ?
            ORDER BY f.due_date ASC
            LIMIT ?
        ''', (today.isoformat(), future_date, limit)).fetchall()
        
        conn.close()
        return upcoming_fees

    @staticmethod
    def get_fee_by_id(fee_id):
        conn = get_db_connection()
        fee = conn.execute('''
            SELECT f.id, f.student_id, f.amount, f.due_date, f.paid_date, f.status
            FROM fees f
            WHERE f.id = ?
        ''', (fee_id,)).fetchone()
        conn.close()
        return dict(fee) if fee else None

    @staticmethod
    def update_fee(fee_id, amount, due_date, status, paid_date=None):
        conn = get_db_connection()
        try:
            if status == 'Paid' and paid_date:
                conn.execute('''
                    UPDATE fees SET amount = ?, due_date = ?, status = ?, paid_date = ? WHERE id = ?
                ''', (amount, due_date, status, paid_date, fee_id))
            else:
                conn.execute('''
                    UPDATE fees SET amount = ?, due_date = ?, status = ?, paid_date = NULL WHERE id = ?
                ''', (amount, due_date, status, fee_id))
            conn.commit()
        finally:
            conn.close()

class ComplaintModel:
    """Model for handling complaint and maintenance request operations."""
    
    @staticmethod
    def get_all_complaints(filters=None):
        """Get all complaints with optional filtering."""
        conn = get_db_connection()
        
        query = """
            SELECT c.*, s.name as reported_by, r.room_number 
            FROM complaints c
            LEFT JOIN students s ON c.reported_by_id = s.id
            LEFT JOIN rooms r ON c.room_id = r.id
            WHERE 1=1
        """
        params = []
        
        # Apply filters if provided
        if filters:
            if 'room_number' in filters and filters['room_number']:
                query += " AND r.room_number LIKE ?"
                params.append(f"%{filters['room_number']}%")
            
            if 'status' in filters and filters['status']:
                query += " AND c.status = ?"
                params.append(filters['status'])
            
            if 'priority' in filters and filters['priority']:
                query += " AND c.priority = ?"
                params.append(filters['priority'])
        
        query += " ORDER BY c.report_date DESC"
        
        complaints = conn.execute(query, params).fetchall()
        conn.close()
        return complaints
    
    @staticmethod
    def get_complaint_by_id(complaint_id):
        """Get a specific complaint by ID."""
        conn = get_db_connection()
        complaint = conn.execute(
            """
            SELECT c.*, s.name as reported_by, r.room_number 
            FROM complaints c
            LEFT JOIN students s ON c.reported_by_id = s.id
            LEFT JOIN rooms r ON c.room_id = r.id
            WHERE c.id = ?
            """, 
            (complaint_id,)
        ).fetchone()
        conn.close()
        return complaint
    
    @staticmethod
    def create_complaint(room_id, description, priority="Medium", reported_by_id=None):
        """Create a new complaint record."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO complaints (room_id, reported_by_id, description, priority, status, report_date)
                VALUES (?, ?, ?, ?, 'Pending', ?)
                """,
                (room_id, reported_by_id, description, priority, date.today().isoformat())
            )
            complaint_id = cursor.lastrowid
            conn.commit()
            return complaint_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    @staticmethod
    def update_complaint(complaint_id, data):
        """Update an existing complaint record."""
        conn = get_db_connection()
        try:
            conn.execute(
                """
                UPDATE complaints 
                SET room_id = ?, reported_by_id = ?, description = ?, priority = ?,
                    status = ?, resolution_notes = ?, resolution_date = ?
                WHERE id = ?
                """,
                (
                    data.get('room_id'), 
                    data.get('reported_by_id'), 
                    data.get('description'), 
                    data.get('priority'),
                    data.get('status'),
                    data.get('resolution_notes', ''),
                    data.get('resolution_date'),
                    complaint_id
                )
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    @staticmethod
    def delete_complaint(complaint_id):
        """Delete a complaint record."""
        conn = get_db_connection()
        try:
            conn.execute('DELETE FROM complaints WHERE id = ?', (complaint_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    @staticmethod
    def get_recent_complaints(limit=5):
        """Get recent complaints for dashboard display."""
        conn = get_db_connection()
        complaints = conn.execute(
            """
            SELECT c.*, s.name as reported_by, r.room_number 
            FROM complaints c
            LEFT JOIN students s ON c.reported_by_id = s.id
            LEFT JOIN rooms r ON c.room_id = r.id
            ORDER BY c.report_date DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        conn.close()
        return complaints
    
    @staticmethod
    def get_complaint_statistics():
        """Get statistics for the complaints dashboard."""
        conn = get_db_connection()
        
        # Get counts by status
        pending_count = conn.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Pending'").fetchone()[0]
        in_progress_count = conn.execute("SELECT COUNT(*) FROM complaints WHERE status = 'In Progress'").fetchone()[0]
        resolved_count = conn.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Resolved'").fetchone()[0]
        closed_count = conn.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Closed'").fetchone()[0]
        
        # Get counts by priority
        critical_count = conn.execute("SELECT COUNT(*) FROM complaints WHERE priority = 'Critical'").fetchone()[0]
        high_count = conn.execute("SELECT COUNT(*) FROM complaints WHERE priority = 'High'").fetchone()[0]
        medium_count = conn.execute("SELECT COUNT(*) FROM complaints WHERE priority = 'Medium'").fetchone()[0]
        low_count = conn.execute("SELECT COUNT(*) FROM complaints WHERE priority = 'Low'").fetchone()[0]
        
        # Get total count
        total_count = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
        
        conn.close()
        
        return {
            'total_count': total_count,
            'by_status': {
                'pending': pending_count,
                'in_progress': in_progress_count,
                'resolved': resolved_count,
                'closed': closed_count
            },
            'by_priority': {
                'critical': critical_count,
                'high': high_count,
                'medium': medium_count,
                'low': low_count
            }
        }
        
# Initialize DB if needed when module is imported
if __name__ == "__main__":
    # Check if DB exists
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DATABASE)
    if not os.path.exists(db_path):
        init_db()
        print(f"Database created at {db_path}")
    else:
        print(f"Database already exists at {db_path}")
