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

def get_db():
    """Alias for get_db_connection to maintain compatibility."""
    return get_db_connection()

def init_db(overwrite=False):
    """Initializes the database schema."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DATABASE)
    if overwrite and os.path.exists(db_path):
        os.remove(db_path)  # Remove existing DB if overwrite is true

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Hostels Table (must be created first due to foreign key constraints)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hostels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            address TEXT,
            contact_person TEXT,
            contact_email TEXT UNIQUE,
            contact_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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
            hostel_id INTEGER,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL,
            FOREIGN KEY (hostel_id) REFERENCES hostels(id) ON DELETE SET NULL
        )
    ''')
    
    # Add hostel_id column to existing students table if it doesn't exist
    cursor.execute("""
        SELECT name FROM pragma_table_info('students') WHERE name='hostel_id'
    """)
    students_hostel_id_exists = cursor.fetchone()
    if not students_hostel_id_exists:
        cursor.execute("ALTER TABLE students ADD COLUMN hostel_id INTEGER")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_hostel_id ON students(hostel_id)")
    
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
            status TEXT DEFAULT 'Available', -- e.g., Available, Full, Maintenance
            hostel_id INTEGER,
            FOREIGN KEY (hostel_id) REFERENCES hostels(id) ON DELETE SET NULL
        )
    ''')
    
    # Add hostel_id column to existing rooms table if it doesn't exist
    cursor.execute("""
        SELECT name FROM pragma_table_info('rooms') WHERE name='hostel_id'
    """)
    hostel_id_exists = cursor.fetchone()
    if not hostel_id_exists:
        cursor.execute("ALTER TABLE rooms ADD COLUMN hostel_id INTEGER")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rooms_hostel_id ON rooms(hostel_id)")    # Fees Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            due_date DATE,
            paid_date DATE,
            status TEXT DEFAULT 'Pending', -- Pending, Paid, Overdue
            hostel_id INTEGER,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (hostel_id) REFERENCES hostels(id) ON DELETE SET NULL
        )
    ''')
    
    # Add hostel_id column to existing fees table if it doesn't exist
    cursor.execute("""
        SELECT name FROM pragma_table_info('fees') WHERE name='hostel_id'
    """)
    fees_hostel_id_exists = cursor.fetchone()
    if not fees_hostel_id_exists:
        cursor.execute("ALTER TABLE fees ADD COLUMN hostel_id INTEGER")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fees_hostel_id ON fees(hostel_id)")

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

    # Expenses Table for tracking hostel expenses
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date DATE DEFAULT CURRENT_DATE,
            category TEXT NOT NULL, -- Maintenance, Utilities, Food, Supplies, Staff, Other
            expense_type TEXT DEFAULT 'Operational', -- Operational, Capital, Emergency
            vendor_name TEXT,
            receipt_number TEXT,
            payment_method TEXT DEFAULT 'Cash', -- Cash, Card, Bank Transfer, Cheque
            approved_by INTEGER,
            notes TEXT,
            hostel_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (hostel_id) REFERENCES hostels(id) ON DELETE SET NULL
        )
    ''')
    
    # Create indexes for expenses
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_hostel_id ON expenses(hostel_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_type ON expenses(expense_type)')

    conn.commit()
    conn.close()
    print("Database initialized/checked.")


# Student Model Operations
class StudentModel:
    @staticmethod
    def count_all_students(hostel_id=None):
        """Return the total count of students, optionally filtered by hostel_id."""
        conn = get_db_connection()
        if hostel_id is not None:
            count = conn.execute('SELECT COUNT(*) FROM students WHERE hostel_id = ?', (hostel_id,)).fetchone()[0]
        else:
            count = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
        conn.close()
        return count
        
    @staticmethod
    def get_all_students(search_params=None, hostel_id=None):
        """Retrieve all students with optional filtering and hostel_id."""
        conn = get_db_connection()
        query = '''
            SELECT s.id, s.name, s.student_id_number, s.contact, s.course, s.email, r.room_number,
                   h.name as hostel_name, s.hostel_id
            FROM students s 
            LEFT JOIN rooms r ON s.room_id = r.id
            LEFT JOIN hostels h ON s.hostel_id = h.id
        '''
        conditions = []
        params = []

        # Add hostel filtering if specified
        if hostel_id is not None:
            conditions.append("s.hostel_id = ?")
            params.append(hostel_id)

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
                    room_id, admission_date, expected_checkout_date, hostel_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                student_data['name'],
                student_data.get('student_id_number', ''),
                student_data['contact'],
                student_data['course'],
                student_data['email'],
                student_data.get('room_id'),
                student_data.get('admission_date', date.today().isoformat()),
                student_data.get('expected_checkout_date', ''),
                student_data.get('hostel_id')
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
            LIMIT ?        ''', (limit,)).fetchall()
        conn.close()
        return recent_students
        
    @staticmethod
    def get_all_courses(hostel_id=None):
        """Return all distinct courses, optionally filtered by hostel_id."""
        conn = get_db_connection()
        
        if hostel_id is not None:
            query = """
                SELECT DISTINCT course 
                FROM students 
                WHERE course IS NOT NULL AND course != '' AND hostel_id = ?
                ORDER BY course
            """
            courses = conn.execute(query, (hostel_id,)).fetchall()
        else:
            query = """
                SELECT DISTINCT course 
                FROM students 
                WHERE course IS NOT NULL AND course != ''
                ORDER BY course
            """
            courses = conn.execute(query).fetchall()
        
        conn.close()
        return courses


# Room Model Operations
class RoomModel:
    """Enhanced Room Model with comprehensive room management functionality."""
    
    # Room status constants
    STATUS_AVAILABLE = 'Available'
    STATUS_FULL = 'Full'
    STATUS_MAINTENANCE = 'Maintenance'
    STATUS_RESERVED = 'Reserved'
    STATUS_OUT_OF_ORDER = 'Out of Order'
    
    VALID_STATUSES = [STATUS_AVAILABLE, STATUS_FULL, STATUS_MAINTENANCE, STATUS_RESERVED, STATUS_OUT_OF_ORDER]
    
    @staticmethod
    def validate_room_data(room_data, room_id=None):
        """Validate room data before insertion or update."""
        errors = []
        
        # Required fields validation
        if not room_data.get('room_number', '').strip():
            errors.append('Room number is required and cannot be empty')
        
        # Capacity validation
        try:
            capacity = int(room_data.get('capacity', 0))
            if capacity <= 0:
                errors.append('Capacity must be a positive integer')
            elif capacity > 50:  # reasonable upper limit
                errors.append('Capacity cannot exceed 50 students per room')
        except (ValueError, TypeError):
            errors.append('Capacity must be a valid number')
        
        # Status validation
        status = room_data.get('status', RoomModel.STATUS_AVAILABLE)
        if status not in RoomModel.VALID_STATUSES:
            errors.append(f'Status must be one of: {", ".join(RoomModel.VALID_STATUSES)}')
          # Room number uniqueness check (if adding new room or changing room number)
        if room_data.get('room_number'):
            conn = get_db_connection()
            try:
                if room_id:  # Updating existing room
                    existing = conn.execute(
                        'SELECT id FROM rooms WHERE room_number = ? AND id != ?',
                        (room_data['room_number'].strip(), room_id)
                    ).fetchone()
                else:  # Adding new room
                    existing = conn.execute(
                        'SELECT id FROM rooms WHERE room_number = ?',
                        (room_data['room_number'].strip(),)
                    ).fetchone()
                
                if existing:
                    errors.append('Room number already exists')
            finally:
                conn.close()
        
        return errors

    @staticmethod
    def get_all_rooms(search_params=None, hostel_id=None, include_students=True):
        """Get all rooms with optional filtering and detailed information."""
        conn = get_db_connection()
        try:
            query = '''
                SELECT r.id, r.room_number, r.capacity, r.current_occupancy, r.status, 
                       r.hostel_id, h.name as hostel_name,
                       COUNT(c.id) as complaint_count,
                       MAX(c.report_date) as last_complaint_date
                FROM rooms r
                LEFT JOIN hostels h ON r.hostel_id = h.id
                LEFT JOIN complaints c ON r.id = c.room_id AND c.status != 'Resolved'
            '''
            conditions = []
            params = []

            # Add hostel filtering if specified
            if hostel_id is not None:
                conditions.append("r.hostel_id = ?")
                params.append(hostel_id)
            if search_params:
                if search_params.get('room_number'):
                    conditions.append("r.room_number LIKE ?")
                    params.append(f"%{search_params['room_number'].strip()}%")
                if search_params.get('filter_status'):
                    conditions.append("r.status = ?")
                    params.append(search_params['filter_status'])
                if search_params.get('min_capacity'):
                    conditions.append("r.capacity >= ?")
                    params.append(int(search_params['min_capacity']))
                if search_params.get('max_capacity'):
                    conditions.append("r.capacity <= ?")
                    params.append(int(search_params['max_capacity']))
                if search_params.get('occupancy_filter'):
                    if search_params['occupancy_filter'] == 'empty':
                        conditions.append("r.current_occupancy = 0")
                    elif search_params['occupancy_filter'] == 'full':
                        conditions.append("r.current_occupancy >= r.capacity")
                    elif search_params['occupancy_filter'] == 'partial':
                        conditions.append("r.current_occupancy > 0 AND r.current_occupancy < r.capacity")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            # Ensure all columns in GROUP BY are qualified
            query += " GROUP BY r.id, r.room_number, r.capacity, r.current_occupancy, r.status, r.hostel_id, h.name ORDER BY r.room_number"

            rooms = conn.execute(query, tuple(params)).fetchall()
            
            # Convert to list of dicts and optionally add students in each room
            rooms_with_details = []
            for room_row in rooms:
                room = dict(room_row)
                
                # Calculate occupancy percentage
                if room['capacity'] > 0:
                    room['occupancy_percentage'] = (room['current_occupancy'] / room['capacity']) * 100
                else:
                    room['occupancy_percentage'] = 0
                
                # Add students if requested
                if include_students:
                    students = conn.execute(
                        '''SELECT id, name, student_id_number, course, contact, email 
                           FROM students WHERE room_id = ? ORDER BY name''', 
                        (room['id'],)
                    ).fetchall()
                    room['students'] = [dict(student) for student in students]
                    room['student_names'] = ', '.join([s['name'] for s in room['students']])
                else:
                    room['students'] = []
                    room['student_names'] = ''
                
                # Add room condition indicators
                room['has_complaints'] = room['complaint_count'] > 0
                room['needs_attention'] = (room['status'] == RoomModel.STATUS_MAINTENANCE or 
                                         room['complaint_count'] > 2)
                
                rooms_with_details.append(room)
            
            return rooms_with_details
        
        finally:
            conn.close()

    @staticmethod
    def get_room_by_id(room_id, include_full_details=False):
        """Get a single room by ID with optional detailed information."""
        if not room_id:
            return None
            
        conn = get_db_connection()
        try:
            room = conn.execute('''
                SELECT r.*, h.name as hostel_name
                FROM rooms r
                LEFT JOIN hostels h ON r.hostel_id = h.id
                WHERE r.id = ?
            ''', (room_id,)).fetchone()
            
            if not room:
                return None
            
            room_dict = dict(room)
            
            if include_full_details:
                # Add occupancy percentage
                if room_dict['capacity'] > 0:
                    room_dict['occupancy_percentage'] = (room_dict['current_occupancy'] / room_dict['capacity']) * 100
                else:
                    room_dict['occupancy_percentage'] = 0
                
                # Add recent complaints
                complaints = conn.execute('''
                    SELECT c.*, s.name as reporter_name
                    FROM complaints c
                    LEFT JOIN students s ON c.reported_by_id = s.id
                    WHERE c.room_id = ?
                    ORDER BY c.report_date DESC
                    LIMIT 5
                ''', (room_id,)).fetchall()
                room_dict['recent_complaints'] = [dict(complaint) for complaint in complaints]
                
                # Add maintenance history (could be expanded)
                room_dict['maintenance_required'] = room_dict['status'] == RoomModel.STATUS_MAINTENANCE
            
            return room_dict
            
        finally:
            conn.close()

    @staticmethod
    def add_room(room_data):
        """Add a new room with comprehensive validation."""
        # Validate input data
        validation_errors = RoomModel.validate_room_data(room_data)
        if validation_errors:
            return {'success': False, 'errors': validation_errors}
        
        conn = get_db_connection()
        try:
            # Clean and prepare data
            clean_data = {
                'room_number': room_data['room_number'].strip(),
                'capacity': int(room_data['capacity']),
                'status': room_data.get('status', RoomModel.STATUS_AVAILABLE),
                'hostel_id': room_data.get('hostel_id'),
                'current_occupancy': 0  # New rooms start empty
            }
            
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO rooms (room_number, capacity, status, hostel_id, current_occupancy) 
                VALUES (?, ?, ?, ?, ?)
            ''', (
                clean_data['room_number'],
                clean_data['capacity'],
                clean_data['status'],
                clean_data['hostel_id'],
                clean_data['current_occupancy']
            ))
            
            room_id = cursor.lastrowid
            conn.commit()
            
            return {
                'success': True, 
                'room_id': room_id,
                'message': f'Room {clean_data["room_number"]} added successfully'
            }
            
        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed' in str(e):
                return {'success': False, 'errors': ['Room number already exists']}
            return {'success': False, 'errors': [f'Database error: {str(e)}']}
        except Exception as e:
            return {'success': False, 'errors': [f'Unexpected error: {str(e)}']}
        finally:
            conn.close()

    @staticmethod
    def update_room(room_id, room_data):
        """Update an existing room with validation and occupancy checks."""
        if not room_id:
            return {'success': False, 'errors': ['Invalid room ID']}
        
        # Validate input data
        validation_errors = RoomModel.validate_room_data(room_data, room_id)
        if validation_errors:
            return {'success': False, 'errors': validation_errors}
        
        conn = get_db_connection()
        try:
            # Get current room data
            current_room = conn.execute('SELECT * FROM rooms WHERE id = ?', (room_id,)).fetchone()
            if not current_room:
                return {'success': False, 'errors': ['Room not found']}
            
            current_room = dict(current_room)
            
            # Check if new capacity is valid (can't be less than current occupancy)
            new_capacity = int(room_data['capacity'])
            if new_capacity < current_room['current_occupancy']:
                return {
                    'success': False, 
                    'errors': [f'New capacity ({new_capacity}) cannot be less than current occupancy ({current_room["current_occupancy"]})']
                }
            
            # Clean and prepare data
            clean_data = {
                'room_number': room_data['room_number'].strip(),
                'capacity': new_capacity,
                'status': room_data.get('status', current_room['status'])
            }
            
            # Build update query dynamically
            set_clauses = ['room_number = ?', 'capacity = ?', 'status = ?']
            params = [clean_data['room_number'], clean_data['capacity'], clean_data['status']]
            
            # Include hostel_id if provided (for owners)
            if 'hostel_id' in room_data and room_data['hostel_id'] is not None:
                set_clauses.append('hostel_id = ?')
                params.append(room_data['hostel_id'])
                clean_data['hostel_id'] = room_data['hostel_id']
            
            params.append(room_id)
            
            query = f'UPDATE rooms SET {", ".join(set_clauses)} WHERE id = ?'
            conn.execute(query, params)
            conn.commit()
            
            # Update room occupancy and status based on current students
            RoomModel.update_room_occupancy(conn, room_id)
            
            return {
                'success': True,
                'message': f'Room {clean_data["room_number"]} updated successfully'
            }
            
        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed' in str(e):
                return {'success': False, 'errors': ['Room number already exists']}
            return {'success': False, 'errors': [f'Database error: {str(e)}']}
        except Exception as e:
            return {'success': False, 'errors': [f'Unexpected error: {str(e)}']}
        finally:
            conn.close()

    @staticmethod
    def delete_room(room_id):
        """Delete a room with comprehensive checks."""
        if not room_id:
            return {'success': False, 'errors': ['Invalid room ID']}
        
        conn = get_db_connection()
        try:
            # Check if room exists
            room = conn.execute('SELECT * FROM rooms WHERE id = ?', (room_id,)).fetchone()
            if not room:
                return {'success': False, 'errors': ['Room not found']}
            
            room = dict(room)
            
            # Check for current occupants
            occupants = conn.execute(
                'SELECT COUNT(*) as count FROM students WHERE room_id = ?', (room_id,)
            ).fetchone()['count']
            
            if occupants > 0:
                student_names = conn.execute(
                    'SELECT name FROM students WHERE room_id = ? ORDER BY name', (room_id,)
                ).fetchall()
                names = ', '.join([s['name'] for s in student_names])
                return {
                    'success': False, 
                    'errors': [f'Cannot delete room {room["room_number"]}: It has {occupants} occupant(s): {names}. Please reassign students first.']
                }
            
            # Check for pending complaints
            pending_complaints = conn.execute(
                'SELECT COUNT(*) as count FROM complaints WHERE room_id = ? AND status != ?', 
                (room_id, 'Resolved')
            ).fetchone()['count']
            
            if pending_complaints > 0:
                return {
                    'success': False,
                    'errors': [f'Cannot delete room {room["room_number"]}: It has {pending_complaints} unresolved complaint(s). Please resolve them first.']
                }
            
            # Perform deletion
            conn.execute('DELETE FROM rooms WHERE id = ?', (room_id,))
            conn.commit()
            
            return {
                'success': True,
                'message': f'Room {room["room_number"]} deleted successfully'
            }
            
        except Exception as e:
            return {'success': False, 'errors': [f'Error deleting room: {str(e)}']}
        finally:
            conn.close()

    @staticmethod
    def update_room_occupancy(conn, room_id):
        """Update room occupancy and status with enhanced logic."""
        if room_id is None:
            return
        
        try:
            cursor = conn.cursor()
            
            # Calculate current occupancy
            result = cursor.execute('SELECT COUNT(*) as count FROM students WHERE room_id = ?', (room_id,)).fetchone()
            current_occupancy = result['count'] if result else 0
            
            # Get room details
            room_result = cursor.execute('SELECT capacity, status FROM rooms WHERE id = ?', (room_id,)).fetchone()
            if not room_result:
                return
            
            capacity = room_result['capacity']
            current_status = room_result['status']
            
            # Determine new status based on occupancy and current status
            new_status = current_status
            
            # Only auto-update status if not in maintenance or out of order
            if current_status not in [RoomModel.STATUS_MAINTENANCE, RoomModel.STATUS_OUT_OF_ORDER, RoomModel.STATUS_RESERVED]:
                if current_occupancy == 0:
                    new_status = RoomModel.STATUS_AVAILABLE
                elif current_occupancy >= capacity:
                    new_status = RoomModel.STATUS_FULL
                else:
                    new_status = RoomModel.STATUS_AVAILABLE
            
            # Update occupancy and status
            cursor.execute(
                'UPDATE rooms SET current_occupancy = ?, status = ? WHERE id = ?', 
                (current_occupancy, new_status, room_id)
            )
            conn.commit()
            
        except Exception as e:
            # Log error but don't raise to avoid breaking other operations
            print(f"Error updating room occupancy for room {room_id}: {str(e)}")

    @staticmethod
    def get_available_rooms(hostel_id=None, min_capacity=None):
        """Get rooms available for assignment with enhanced filtering."""
        conn = get_db_connection()
        try:
            query = '''
                SELECT r.id, r.room_number, r.capacity, r.current_occupancy, r.status,
                       r.hostel_id, h.name as hostel_name,
                       (r.capacity - r.current_occupancy) as available_spots
                FROM rooms r
                LEFT JOIN hostels h ON r.hostel_id = h.id
                WHERE r.status = ? AND r.current_occupancy < r.capacity
            '''
            params = [RoomModel.STATUS_AVAILABLE]
            
            if hostel_id is not None:
                query += ' AND r.hostel_id = ?'
                params.append(hostel_id)
            
            if min_capacity is not None:
                query += ' AND (r.capacity - r.current_occupancy) >= ?'
                params.append(min_capacity)
            
            query += ' ORDER BY r.room_number'
            
            rooms = conn.execute(query, params).fetchall()
            return [dict(room) for room in rooms]
            
        finally:
            conn.close()

    @staticmethod
    def get_room_statistics(hostel_id=None):
        """Get comprehensive room statistics."""
        conn = get_db_connection()
        try:
            base_query = 'SELECT {} FROM rooms'
            qualified_where_clause = ''
            params = []
            
            if hostel_id is not None:
                where_clause = ' WHERE hostel_id = ?'
                qualified_where_clause = ' WHERE r.hostel_id = ?'
                params = [hostel_id]
            else:
                where_clause = ''
                qualified_where_clause = ''
            
            stats = {}
            
            # Basic counts
            stats['total_rooms'] = conn.execute(f"{base_query.format('COUNT(*)')}{where_clause}", params).fetchone()[0]
            
            # Status breakdown
            for status in RoomModel.VALID_STATUSES:
                status_query = f"{base_query.format('COUNT(*)')}{where_clause}"
                status_params = params.copy()
                
                if where_clause:
                    status_query += ' AND status = ?'
                else:
                    status_query += ' WHERE status = ?'
                status_params.append(status)
                
                count = conn.execute(status_query, status_params).fetchone()[0]
                stats[f'{status.lower().replace(" ", "_")}_rooms'] = count
            
            # Capacity and occupancy
            capacity_query = f"{base_query.format('SUM(capacity)')}{where_clause}"
            stats['total_capacity'] = conn.execute(capacity_query, params).fetchone()[0] or 0
            
            occupancy_query = f"{base_query.format('SUM(current_occupancy)')}{where_clause}"
            stats['current_occupancy'] = conn.execute(occupancy_query, params).fetchone()[0] or 0
            
            # Calculate percentages
            if stats['total_capacity'] > 0:
                stats['occupancy_percentage'] = (stats['current_occupancy'] / stats['total_capacity']) * 100
            else:
                stats['occupancy_percentage'] = 0
              # Available spots
            stats['available_spots'] = stats['total_capacity'] - stats['current_occupancy']
            
            # Add calculated fields for dashboard compatibility
            stats['occupied_rooms'] = stats.get('full_rooms', 0)  # Rooms that are completely full
            
            # Calculate occupied rooms properly (rooms with any occupants)
            occupied_query = f'''
                SELECT COUNT(*) 
                FROM rooms r
                {qualified_where_clause}
                {'AND' if qualified_where_clause else 'WHERE'} r.current_occupancy > 0
            '''
            stats['occupied_rooms'] = conn.execute(occupied_query, params).fetchone()[0]
              # Rooms needing attention (maintenance + high complaint count)
            attention_query = f'''
                SELECT COUNT(DISTINCT r.id)
                FROM rooms r
                LEFT JOIN complaints c ON r.id = c.room_id AND c.status != 'Resolved'
                {qualified_where_clause}
                {'AND' if qualified_where_clause else 'WHERE'} (r.status = ? OR (SELECT COUNT(*) FROM complaints WHERE room_id = r.id AND status != 'Resolved') > 2)
            '''
            attention_params = params + [RoomModel.STATUS_MAINTENANCE]
            
            stats['rooms_needing_attention'] = conn.execute(attention_query, attention_params).fetchone()[0]
            
            return stats
            
        finally:
            conn.close()

    @staticmethod
    def get_room_occupancy_chart_data(hostel_id=None):
        """Get enhanced data for room occupancy visualizations."""
        conn = get_db_connection()
        try:
            query = '''
                SELECT r.id, r.room_number, r.capacity, r.current_occupancy, r.status,
                       r.hostel_id, h.name as hostel_name
                FROM rooms r
                LEFT JOIN hostels h ON r.hostel_id = h.id
            '''
            params = []
            
            if hostel_id is not None:
                query += ' WHERE r.hostel_id = ?'
                params.append(hostel_id)
            
            query += ' ORDER BY r.room_number'
            
            rooms = conn.execute(query, params).fetchall()
            
            # Convert to enhanced chart data
            chart_data = []
            for room in rooms:
                room_dict = dict(room)
                
                # Calculate occupancy percentage
                if room_dict['capacity'] > 0:
                    room_dict['occupancy_percentage'] = (room_dict['current_occupancy'] / room_dict['capacity']) * 100
                else:
                    room_dict['occupancy_percentage'] = 0
                
                # Add color coding for status
                status_colors = {
                    RoomModel.STATUS_AVAILABLE: '#28a745',
                    RoomModel.STATUS_FULL: '#17a2b8',
                    RoomModel.STATUS_MAINTENANCE: '#dc3545',
                    RoomModel.STATUS_RESERVED: '#ffc107',
                    RoomModel.STATUS_OUT_OF_ORDER: '#6c757d'
                }
                room_dict['status_color'] = status_colors.get(room_dict['status'], '#6c757d')
                
                chart_data.append(room_dict)
            
            return chart_data
            
        finally:
            conn.close()

    @staticmethod
    def get_room_occupants(room_id, include_details=False):
        """Get students occupying a specific room with optional detailed information."""
        if not room_id:
            return []
        
        conn = get_db_connection()
        try:
            if include_details:
                query = '''
                    SELECT s.id, s.name, s.student_id_number, s.course, s.contact, s.email,
                           s.admission_date, s.expected_checkout_date,
                           sd.parent_name, sd.parent_contact, sd.emergency_contact_name, sd.emergency_contact_phone
                    FROM students s
                    LEFT JOIN student_details sd ON s.id = sd.student_id
                    WHERE s.room_id = ?
                    ORDER BY s.name
                '''
            else:
                query = '''
                    SELECT s.id, s.name, s.student_id_number, s.course, s.contact, s.email,
                           s.admission_date, s.expected_checkout_date
                    FROM students s
                    WHERE s.room_id = ?
                    ORDER BY s.name
                '''
            
            occupants = conn.execute(query, (room_id,)).fetchall()
            return [dict(occupant) for occupant in occupants]
            
        finally:
            conn.close()

    @staticmethod
    def get_unique_statuses(hostel_id=None):
        """Get unique room statuses with counts."""
        conn = get_db_connection()
        try:
            query = 'SELECT status, COUNT(*) as count FROM rooms'
            params = []
            
            if hostel_id is not None:
                query += ' WHERE hostel_id = ?'
                params.append(hostel_id)
            
            query += ' GROUP BY status ORDER BY status'
            
            results = conn.execute(query, params).fetchall()
            return [{'status': row['status'], 'count': row['count']} for row in results]
            
        finally:
            conn.close()

    @staticmethod
    def get_unique_capacities(hostel_id=None):
        """Get unique room capacities with counts."""
        conn = get_db_connection()
        try:
            query = 'SELECT capacity, COUNT(*) as count FROM rooms'
            params = []
            
            if hostel_id is not None:
                query += ' WHERE hostel_id = ?'
                params.append(hostel_id)
            
            query += ' GROUP BY capacity ORDER BY capacity'
            
            results = conn.execute(query, params).fetchall()
            return [{'capacity': row['capacity'], 'count': row['count']} for row in results]
            
        finally:
            conn.close()

    @staticmethod
    def bulk_update_status(room_ids, new_status, reason=None):
        """Update status for multiple rooms at once."""
        if not room_ids or new_status not in RoomModel.VALID_STATUSES:
            return {'success': False, 'errors': ['Invalid room IDs or status']}
        
        conn = get_db_connection()
        try:
            # Validate that all room IDs exist
            placeholders = ','.join(['?'] * len(room_ids))
            existing_rooms = conn.execute(
                f'SELECT id, room_number FROM rooms WHERE id IN ({placeholders})',
                room_ids
            ).fetchall()
            
            if len(existing_rooms) != len(room_ids):
                return {'success': False, 'errors': ['Some room IDs do not exist']}
            
            # Update all rooms
            conn.execute(
                f'UPDATE rooms SET status = ? WHERE id IN ({placeholders})',
                [new_status] + room_ids
            )
            conn.commit()
            
            room_numbers = [room['room_number'] for room in existing_rooms]
            return {
                'success': True,
                'message': f'Updated status to "{new_status}" for rooms: {", ".join(room_numbers)}'
            }
            
        except Exception as e:
            return {'success': False, 'errors': [f'Error updating rooms: {str(e)}']}
        finally:
            conn.close()

    @staticmethod
    def get_maintenance_schedule(hostel_id=None, days_ahead=30):
        """Get rooms that might need maintenance based on complaints and status."""
        conn = get_db_connection()
        try:
            query = '''
                SELECT r.id, r.room_number, r.status, r.hostel_id, h.name as hostel_name,
                       COUNT(c.id) as complaint_count,
                       MAX(c.report_date) as last_complaint_date,
                       GROUP_CONCAT(c.description, '; ') as complaint_descriptions
                FROM rooms r
                LEFT JOIN hostels h ON r.hostel_id = h.id
                LEFT JOIN complaints c ON r.id = c.room_id AND c.status != 'Resolved'
            '''
            conditions = []
            params = []
            
            if hostel_id is not None:
                conditions.append('r.hostel_id = ?')
                params.append(hostel_id)
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += '''
                GROUP BY r.id, r.room_number, r.status, r.hostel_id, h.name
                HAVING (r.status = ? OR COUNT(c.id) > 1)
                ORDER BY COUNT(c.id) DESC, r.room_number
            '''
            params.append(RoomModel.STATUS_MAINTENANCE)
            
            maintenance_rooms = conn.execute(query, params).fetchall()
            return [dict(room) for room in maintenance_rooms]
            
        finally:
            conn.close()

# Fee Model Operations
class FeeModel:
    @staticmethod
    def get_unique_statuses(hostel_id=None):
        """Get a list of unique fee statuses from the database.
        
        Args:
            hostel_id: Optional hostel ID to filter by
            
        Returns:
            List of unique status strings
        """
        conn = get_db_connection()
        
        query = 'SELECT DISTINCT status FROM fees'
        params = []
        
        if hostel_id is not None:
            query += ' WHERE hostel_id = ?'
            params.append(hostel_id)
            
        statuses = conn.execute(query, params).fetchall()
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
    def get_all_fees_with_students(filter_params=None, hostel_id=None):
        """Get all fees with student information and apply filters.
        
        Args:
            filter_params: Dictionary containing filter parameters
                - status: Filter by fee status
                - student_name: Filter by student name
                - amount_min: Minimum fee amount
                - amount_max: Maximum fee amount
                - start_date: Start date for due date range
                - end_date: End date for due date range
            hostel_id: Optional hostel ID to filter fees by hostel
                
        Returns:
            List of fee dictionaries with student information
        """
        conn = get_db_connection()
        
        # Start building the query with hostel information
        query = '''
            SELECT f.id, s.name AS student_name, f.student_id, f.amount, 
                   f.due_date, f.paid_date, f.status, r.room_number, h.name AS hostel_name
            FROM fees f
            JOIN students s ON f.student_id = s.id
            LEFT JOIN rooms r ON s.room_id = r.id
            LEFT JOIN hostels h ON f.hostel_id = h.id
        '''
        
        # Add WHERE clauses based on filters
        conditions = []
        params = []
        
        # Add hostel filter if specified
        if hostel_id is not None:
            conditions.append("f.hostel_id = ?")
            params.append(hostel_id)
        
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
                params.append(filter_params['start_date'].isoformat() if hasattr(filter_params['start_date'], 'isoformat') else filter_params['start_date'])
                
            if filter_params.get('end_date'):
                conditions.append("f.due_date <= ?")
                params.append(filter_params['end_date'].isoformat() if hasattr(filter_params['end_date'], 'isoformat') else filter_params['end_date'])
        
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
    def add_fee(fee_data, hostel_id=None):
        """Add a new fee record."""
        conn = get_db_connection()
        try:
            # Use hostel_id from fee_data if available, otherwise use the passed hostel_id
            actual_hostel_id = fee_data.get('hostel_id') or hostel_id
            
            conn.execute(
                'INSERT INTO fees (student_id, amount, due_date, status, hostel_id) VALUES (?, ?, ?, ?, ?)',
                (
                    fee_data['student_id'], 
                    fee_data['amount'], 
                    fee_data['due_date'], 
                    fee_data.get('status', 'Pending'),
                    actual_hostel_id
                )            )
            conn.commit()
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': e}
        finally:
            conn.close()

    @staticmethod
    def mark_fee_paid(fee_id, hostel_id=None):
        """Mark a fee as paid."""
        conn = get_db_connection()
        try:
            today = date.today().strftime('%Y-%m-%d')
            
            # If hostel_id is provided (for managers), include it in the WHERE clause
            if hostel_id is not None:
                result = conn.execute(
                    "UPDATE fees SET status = 'Paid', paid_date = ? WHERE id = ? AND hostel_id = ?", 
                    (today, fee_id, hostel_id)
                )
            else:
                result = conn.execute(
                    "UPDATE fees SET status = 'Paid', paid_date = ? WHERE id = ?", 
                    (today, fee_id)
                )
            
            if result.rowcount == 0:
                return {'success': False, 'error': 'Fee not found or access denied'}            
            conn.commit()
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': e}
        finally:
            conn.close()

    @staticmethod
    def get_overdue_fees(hostel_id=None):
        """Get all overdue fees with optional hostel filtering."""
        conn = get_db_connection()
        today = date.today().isoformat()
        
        if hostel_id is not None:
            overdue_fees = conn.execute('''
                SELECT f.id, f.amount, f.due_date, s.name as student_name, s.id as student_id,
                       h.name as hostel_name
                FROM fees f
                JOIN students s ON f.student_id = s.id
                LEFT JOIN hostels h ON f.hostel_id = h.id
                WHERE f.status = 'Pending' AND f.due_date < ? AND f.hostel_id = ?
                ORDER BY f.due_date ASC
            ''', (today, hostel_id)).fetchall()
        else:
            overdue_fees = conn.execute('''
                SELECT f.id, f.amount, f.due_date, s.name as student_name, s.id as student_id,
                       h.name as hostel_name
                FROM fees f
                JOIN students s ON f.student_id = s.id
                LEFT JOIN hostels h ON f.hostel_id = h.id
                WHERE f.status = 'Pending' AND f.due_date < ?
                ORDER BY f.due_date ASC
            ''', (today,)).fetchall()
        
        conn.close()
        return overdue_fees

    @staticmethod
    def get_fee_report(filters=None, period='monthly', year=None, month=None, hostel_id=None):
        """Get fee report with optional filtering.
        
        Args:
            filters: Dictionary of filter parameters
            period: Report period ('monthly', 'quarterly', 'yearly')
            year: Year for the report
            month: Month for the report (if period is 'monthly')
            hostel_id: Optional hostel ID for filtering (for multi-hostel support)
            
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
        
        # Add hostel filter if specified
        if hostel_id is not None:
            conditions.append("f.hostel_id = ?")
            params.append(hostel_id)
        
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
    def get_fee_statistics(hostel_id=None):
        """Get statistics about fees with optional hostel filtering."""
        conn = get_db_connection()
        today = date.today().isoformat()
        
        # Base queries with hostel filtering if needed
        base_where = ""
        params_base = []
        if hostel_id is not None:
            base_where = " WHERE hostel_id = ?"
            params_base = [hostel_id]
        
        # Fee counts
        pending_query = f"SELECT COUNT(*) FROM fees{base_where}"
        if base_where:
            pending_query += " AND status = 'Pending'"
            params_pending = params_base + []
        else:
            pending_query += " WHERE status = 'Pending'"
            params_pending = []
        
        pending_count = conn.execute(pending_query, params_pending).fetchone()[0]
        
        overdue_query = f"SELECT COUNT(*) FROM fees{base_where}"
        if base_where:
            overdue_query += " AND status = 'Pending' AND due_date < ?"
            params_overdue = params_base + [today]
        else:
            overdue_query += " WHERE status = 'Pending' AND due_date < ?"
            params_overdue = [today]
        
        overdue_count = conn.execute(overdue_query, params_overdue).fetchone()[0]
        
        # Fee amounts
        pending_amount_query = f"SELECT COALESCE(SUM(amount), 0) FROM fees{base_where}"
        if base_where:
            pending_amount_query += " AND status = 'Pending'"
            params_pending_amount = params_base + []
        else:
            pending_amount_query += " WHERE status = 'Pending'"
            params_pending_amount = []
        
        pending_amount = conn.execute(pending_amount_query, params_pending_amount).fetchone()[0]
        
        overdue_amount_query = f"SELECT COALESCE(SUM(amount), 0) FROM fees{base_where}"
        if base_where:
            overdue_amount_query += " AND status = 'Pending' AND due_date < ?"
            params_overdue_amount = params_base + [today]
        else:
            overdue_amount_query += " WHERE status = 'Pending' AND due_date < ?"
            params_overdue_amount = [today]
        
        overdue_amount = conn.execute(overdue_amount_query, params_overdue_amount).fetchone()[0]
        
        paid_amount_query = f"SELECT COALESCE(SUM(amount), 0) FROM fees{base_where}"
        if base_where:
            paid_amount_query += " AND status = 'Paid'"
            params_paid_amount = params_base + []
        else:
            paid_amount_query += " WHERE status = 'Paid'"
            params_paid_amount = []
        
        paid_amount = conn.execute(paid_amount_query, params_paid_amount).fetchone()[0]
        
        conn.close()
        
        return {
            'pending_count': pending_count,
            'overdue_count': overdue_count,
            'pending_amount': pending_amount,
            'overdue_amount': overdue_amount,
            'paid_amount': paid_amount
        }
    
    @staticmethod
    def get_upcoming_fees(limit=5, days=30, hostel_id=None):
        """Get upcoming fee payments due within the specified number of days."""
        conn = get_db_connection()
        today = date.today()
        future_date = (today + timedelta(days=days)).isoformat()
        
        if hostel_id is not None:
            upcoming_fees = conn.execute('''
                SELECT f.id, f.amount, f.due_date, s.name as student_name, s.id as student_id,
                       h.name as hostel_name
                FROM fees f
                JOIN students s ON f.student_id = s.id
                LEFT JOIN hostels h ON f.hostel_id = h.id
                WHERE f.status = 'Pending' AND f.due_date BETWEEN ? AND ? AND f.hostel_id = ?
                ORDER BY f.due_date ASC
                LIMIT ?
            ''', (today.isoformat(), future_date, hostel_id, limit)).fetchall()
        else:
            upcoming_fees = conn.execute('''
                SELECT f.id, f.amount, f.due_date, s.name as student_name, s.id as student_id,
                       h.name as hostel_name
                FROM fees f
                JOIN students s ON f.student_id = s.id
                LEFT JOIN hostels h ON f.hostel_id = h.id
                WHERE f.status = 'Pending' AND f.due_date BETWEEN ? AND ?
                ORDER BY f.due_date ASC
                LIMIT ?
            ''', (today.isoformat(), future_date, limit)).fetchall()
        
        conn.close()
        return upcoming_fees

    @staticmethod
    def get_fee_by_id(fee_id, hostel_id=None):
        """Get a fee by ID with optional hostel filtering."""
        conn = get_db_connection()
        
        if hostel_id is not None:
            fee = conn.execute('''
                SELECT f.id, f.student_id, f.amount, f.due_date, f.paid_date, f.status, f.hostel_id,
                       h.name as hostel_name
                FROM fees f
                LEFT JOIN hostels h ON f.hostel_id = h.id
                WHERE f.id = ? AND f.hostel_id = ?
            ''', (fee_id, hostel_id)).fetchone()
        else:
            fee = conn.execute('''
                SELECT f.id, f.student_id, f.amount, f.due_date, f.paid_date, f.status, f.hostel_id,
                       h.name as hostel_name
                FROM fees f
                LEFT JOIN hostels h ON f.hostel_id = h.id
                WHERE f.id = ?            ''', (fee_id,)).fetchone()
        conn.close()
        return dict(fee) if fee else None
    
    @staticmethod
    def update_fee(fee_id, amount, due_date, status, paid_date=None, hostel_id=None):
        """Update a fee record with optional hostel filtering."""
        conn = get_db_connection()
        try:
            if status == 'Paid' and paid_date:
                if hostel_id is not None:
                    result = conn.execute('''
                        UPDATE fees SET amount = ?, due_date = ?, status = ?, paid_date = ? 
                        WHERE id = ? AND hostel_id = ?
                    ''', (amount, due_date, status, paid_date, fee_id, hostel_id))
                else:
                    result = conn.execute('''
                        UPDATE fees SET amount = ?, due_date = ?, status = ?, paid_date = ? WHERE id = ?
                    ''', (amount, due_date, status, paid_date, fee_id))
            else:
                if hostel_id is not None:
                    result = conn.execute('''
                        UPDATE fees SET amount = ?, due_date = ?, status = ?, paid_date = NULL 
                        WHERE id = ? AND hostel_id = ?
                    ''', (amount, due_date, status, fee_id, hostel_id))
                else:
                    result = conn.execute('''
                        UPDATE fees SET amount = ?, due_date = ?, status = ?, paid_date = NULL WHERE id = ?
                    ''', (amount, due_date, status, fee_id))
            
            if result.rowcount == 0:
                raise Exception('Fee not found or access denied')
            
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


# Expense Model Operations
class ExpenseModel:
    """Model for handling expense tracking operations with multi-hostel support."""
    
    # Expense categories
    CATEGORIES = [
        'Maintenance', 'Utilities', 'Food', 'Supplies', 
        'Staff', 'Security', 'Cleaning', 'Internet', 'Other'
    ]
    
    # Expense types
    EXPENSE_TYPES = ['Operational', 'Capital', 'Emergency']
    
    # Payment methods
    PAYMENT_METHODS = ['Cash', 'Card', 'Bank Transfer', 'Cheque', 'UPI', 'Other']
    
    @staticmethod
    def get_all_expenses(filters=None, hostel_id=None):
        """Get all expenses with optional filtering and hostel support."""
        conn = get_db_connection()
        try:
            query = """
                SELECT e.*, u.full_name as approved_by_name, h.name as hostel_name
                FROM expenses e
                LEFT JOIN users u ON e.approved_by = u.id
                LEFT JOIN hostels h ON e.hostel_id = h.id
                WHERE 1=1
            """
            params = []
            
            # Add hostel filter
            if hostel_id is not None:
                query += " AND e.hostel_id = ?"
                params.append(hostel_id)
            
            # Apply filters if provided
            if filters:
                if filters.get('category'):
                    query += " AND e.category = ?"
                    params.append(filters['category'])
                
                if filters.get('expense_type'):
                    query += " AND e.expense_type = ?"
                    params.append(filters['expense_type'])
                
                if filters.get('payment_method'):
                    query += " AND e.payment_method = ?"
                    params.append(filters['payment_method'])
                
                if filters.get('start_date'):
                    query += " AND e.expense_date >= ?"
                    params.append(filters['start_date'])
                
                if filters.get('end_date'):
                    query += " AND e.expense_date <= ?"
                    params.append(filters['end_date'])
                
                if filters.get('min_amount'):
                    query += " AND e.amount >= ?"
                    params.append(float(filters['min_amount']))
                
                if filters.get('max_amount'):
                    query += " AND e.amount <= ?"
                    params.append(float(filters['max_amount']))
                
                if filters.get('vendor_name'):
                    query += " AND e.vendor_name LIKE ?"
                    params.append(f"%{filters['vendor_name']}%")
                
                if filters.get('description'):
                    query += " AND e.description LIKE ?"
                    params.append(f"%{filters['description']}%")
            
            query += " ORDER BY e.expense_date DESC, e.created_at DESC"
            
            expenses = conn.execute(query, params).fetchall()
            return [dict(expense) for expense in expenses]
            
        finally:
            conn.close()
    
    @staticmethod
    def get_expense_by_id(expense_id, hostel_id=None):
        """Get a specific expense by ID with optional hostel filtering."""
        conn = get_db_connection()
        try:
            query = """
                SELECT e.*, u.full_name as approved_by_name, h.name as hostel_name
                FROM expenses e
                LEFT JOIN users u ON e.approved_by = u.id
                LEFT JOIN hostels h ON e.hostel_id = h.id
                WHERE e.id = ?
            """
            params = [expense_id]
            
            if hostel_id is not None:
                query += " AND e.hostel_id = ?"
                params.append(hostel_id)
            
            expense = conn.execute(query, params).fetchone()
            return dict(expense) if expense else None
            
        finally:
            conn.close()
    
    @staticmethod
    def add_expense(expense_data, hostel_id=None):
        """Add a new expense record."""
        conn = get_db_connection()
        try:
            # Use hostel_id from expense_data if available, otherwise use the passed hostel_id
            actual_hostel_id = expense_data.get('hostel_id') or hostel_id
            
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO expenses (
                    description, amount, expense_date, category, expense_type,
                    vendor_name, receipt_number, payment_method, approved_by,
                    notes, hostel_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                expense_data['description'],
                float(expense_data['amount']),
                expense_data.get('expense_date', date.today().isoformat()),
                expense_data['category'],
                expense_data.get('expense_type', 'Operational'),
                expense_data.get('vendor_name', ''),
                expense_data.get('receipt_number', ''),
                expense_data.get('payment_method', 'Cash'),
                expense_data.get('approved_by'),
                expense_data.get('notes', ''),
                actual_hostel_id
            ))
            
            expense_id = cursor.lastrowid
            conn.commit()
            return {'success': True, 'expense_id': expense_id}
            
        except Exception as e:
            conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    @staticmethod
    def update_expense(expense_id, expense_data, hostel_id=None):
        """Update an existing expense record with optional hostel filtering."""
        conn = get_db_connection()
        try:
            # Build the update query with hostel filtering if needed
            query = """
                UPDATE expenses 
                SET description = ?, amount = ?, expense_date = ?, category = ?,
                    expense_type = ?, vendor_name = ?, receipt_number = ?,
                    payment_method = ?, approved_by = ?, notes = ?
                WHERE id = ?
            """
            params = [
                expense_data['description'],
                float(expense_data['amount']),
                expense_data.get('expense_date', date.today().isoformat()),
                expense_data['category'],
                expense_data.get('expense_type', 'Operational'),
                expense_data.get('vendor_name', ''),
                expense_data.get('receipt_number', ''),
                expense_data.get('payment_method', 'Cash'),
                expense_data.get('approved_by'),
                expense_data.get('notes', ''),
                expense_id
            ]
            
            if hostel_id is not None:
                query += " AND hostel_id = ?"
                params.append(hostel_id)
            
            result = conn.execute(query, params)
            
            if result.rowcount == 0:
                return {'success': False, 'error': 'Expense not found or access denied'}
            
            conn.commit()
            return {'success': True}
            
        except Exception as e:
            conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    @staticmethod
    def delete_expense(expense_id, hostel_id=None):
        """Delete an expense record with optional hostel filtering."""
        conn = get_db_connection()
        try:
            query = "DELETE FROM expenses WHERE id = ?"
            params = [expense_id]
            
            if hostel_id is not None:
                query += " AND hostel_id = ?"
                params.append(hostel_id)
            
            result = conn.execute(query, params)
            
            if result.rowcount == 0:
                return {'success': False, 'error': 'Expense not found or access denied'}
            
            conn.commit()
            return {'success': True}
            
        except Exception as e:
            conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    @staticmethod
    def get_expense_statistics(hostel_id=None, period='monthly', year=None, month=None):
        """Get expense statistics with optional hostel filtering."""
        conn = get_db_connection()
        try:
            today = date.today()
            
            # Set default year and month if not provided
            if year is None:
                year = today.year
            if month is None and period == 'monthly':
                month = today.month
            
            # Base query conditions
            base_conditions = []
            base_params = []
            
            if hostel_id is not None:
                base_conditions.append("hostel_id = ?")
                base_params.append(hostel_id)
            
            # Period filtering
            if period == 'monthly' and year and month:
                base_conditions.append("strftime('%Y', expense_date) = ? AND strftime('%m', expense_date) = ?")
                base_params.extend([str(year), f"{month:02d}"])
            elif period == 'yearly' and year:
                base_conditions.append("strftime('%Y', expense_date) = ?")
                base_params.append(str(year))
            
            where_clause = " WHERE " + " AND ".join(base_conditions) if base_conditions else ""
            
            # Total expenses
            total_query = f"SELECT COALESCE(SUM(amount), 0) FROM expenses{where_clause}"
            total_amount = conn.execute(total_query, base_params).fetchone()[0]
            
            # Count of expenses
            count_query = f"SELECT COUNT(*) FROM expenses{where_clause}"
            total_count = conn.execute(count_query, base_params).fetchone()[0]
            
            # Category breakdown
            category_query = f"""
                SELECT category, COALESCE(SUM(amount), 0) as total, COUNT(*) as count
                FROM expenses{where_clause}
                GROUP BY category
                ORDER BY total DESC
            """
            category_breakdown = conn.execute(category_query, base_params).fetchall()
            
            # Expense type breakdown
            type_query = f"""
                SELECT expense_type, COALESCE(SUM(amount), 0) as total, COUNT(*) as count
                FROM expenses{where_clause}
                GROUP BY expense_type
                ORDER BY total DESC
            """
            type_breakdown = conn.execute(type_query, base_params).fetchall()
            
            # Payment method breakdown
            payment_query = f"""
                SELECT payment_method, COALESCE(SUM(amount), 0) as total, COUNT(*) as count
                FROM expenses{where_clause}
                GROUP BY payment_method
                ORDER BY total DESC
            """
            payment_breakdown = conn.execute(payment_query, base_params).fetchall()
            
            # Monthly trend (last 12 months)
            monthly_trend_query = f"""
                SELECT strftime('%Y-%m', expense_date) as month, COALESCE(SUM(amount), 0) as total
                FROM expenses
                WHERE expense_date >= date('now', '-12 months'){' AND ' + ' AND '.join(base_conditions) if base_conditions else ''}
                GROUP BY strftime('%Y-%m', expense_date)
                ORDER BY month
            """
            monthly_trend = conn.execute(monthly_trend_query, base_params).fetchall()
            
            # Recent large expenses (top 10)
            large_expenses_conditions = base_conditions.copy()
            large_expenses_params = base_params.copy()
            large_expenses_query = f"""
                SELECT description, amount, expense_date, category
                FROM expenses{where_clause}
                ORDER BY amount DESC
                LIMIT 10
            """
            large_expenses = conn.execute(large_expenses_query, base_params).fetchall()
            
            return {
                'total_amount': total_amount,
                'total_count': total_count,
                'average_expense': total_amount / total_count if total_count > 0 else 0,
                'category_breakdown': [dict(row) for row in category_breakdown],
                'type_breakdown': [dict(row) for row in type_breakdown],
                'payment_breakdown': [dict(row) for row in payment_breakdown],
                'monthly_trend': [dict(row) for row in monthly_trend],
                'large_expenses': [dict(row) for row in large_expenses],
                'period': period,
                'year': year,
                'month': month
            }
            
        finally:
            conn.close()
    
    @staticmethod
    def get_recent_expenses(limit=10, hostel_id=None):
        """Get recent expenses for dashboard display."""
        conn = get_db_connection()
        try:
            query = """
                SELECT e.*, h.name as hostel_name
                FROM expenses e
                LEFT JOIN hostels h ON e.hostel_id = h.id
                WHERE 1=1
            """
            params = []
            
            if hostel_id is not None:
                query += " AND e.hostel_id = ?"
                params.append(hostel_id)
            
            query += " ORDER BY e.expense_date DESC, e.created_at DESC LIMIT ?"
            params.append(limit)
            
            expenses = conn.execute(query, params).fetchall()
            return [dict(expense) for expense in expenses]
            
        finally:
            conn.close()
    
    @staticmethod
    def get_expense_report(filters=None, hostel_id=None):
        """Generate a comprehensive expense report."""
        expenses = ExpenseModel.get_all_expenses(filters, hostel_id)
        
        if not expenses:
            return {
                'expenses': [],
                'summary': {
                    'total_amount': 0,
                    'total_count': 0,
                    'average_expense': 0,
                    'by_category': {},
                    'by_type': {},
                    'by_payment_method': {}
                }
            }
        
        # Calculate summary statistics
        total_amount = sum(expense['amount'] for expense in expenses)
        total_count = len(expenses)
        average_expense = total_amount / total_count if total_count > 0 else 0
        
        # Group by category
        by_category = {}
        by_type = {}
        by_payment_method = {}
        
        for expense in expenses:
            # By category
            category = expense['category']
            if category not in by_category:
                by_category[category] = {'amount': 0, 'count': 0}
            by_category[category]['amount'] += expense['amount']
            by_category[category]['count'] += 1
            
            # By type
            expense_type = expense['expense_type']
            if expense_type not in by_type:
                by_type[expense_type] = {'amount': 0, 'count': 0}
            by_type[expense_type]['amount'] += expense['amount']
            by_type[expense_type]['count'] += 1
            
            # By payment method
            payment_method = expense['payment_method']
            if payment_method not in by_payment_method:
                by_payment_method[payment_method] = {'amount': 0, 'count': 0}
            by_payment_method[payment_method]['amount'] += expense['amount']
            by_payment_method[payment_method]['count'] += 1
        
        return {
            'expenses': expenses,
            'summary': {
                'total_amount': total_amount,
                'total_count': total_count,
                'average_expense': average_expense,
                'by_category': by_category,
                'by_type': by_type,
                'by_payment_method': by_payment_method
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
