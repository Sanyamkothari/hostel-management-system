from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages
import sqlite3
import os
from datetime import date
from dotenv import load_dotenv
from db_utils import get_db_connection, DatabaseConnection

# Load environment variables from .env file if it exists
load_dotenv()

# Create .env file if it doesn't exist
if not os.path.exists('.env'):
    with open('.env', 'w') as f:
        f.write('''# Flask secret key for session management
SECRET_KEY=your_very_secret_key_change_this_in_production

# Database configuration
DATABASE_PATH=hostel.db

# Email configuration (if needed)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
''')
    print("Created .env file with default values. Please update with your actual values.")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_very_secret_key")  # Fall back to default if env var not set
DATABASE = os.environ.get("DATABASE_PATH", "hostel.db")

# Register blueprints
from routes.students import student_bp
app.register_blueprint(student_bp)
from routes.rooms import room_bp
app.register_blueprint(room_bp)
from routes.fees import fee_bp
app.register_blueprint(fee_bp)
from routes.exports import fee_bp as export_bp
app.register_blueprint(export_bp)
from routes.dashboard import dashboard_bp
app.register_blueprint(dashboard_bp)
from routes.complaints import complaints
app.register_blueprint(complaints)

@app.context_processor
def inject_current_date():
    return {'current_date': date.today()}

# --- Database Setup ---
def init_db(overwrite=False):
    """Initializes the database schema."""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE)
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
    
    # Student Details Table
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
            description TEXT,
            fee_type TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        )
    ''')

    # Complaints/Maintenance Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER, -- Optional: if reported by a student
            room_id INTEGER,    -- Optional: if related to a specific room
            reported_by_name TEXT, -- Name of the person reporting (if not a student from DB)
            description TEXT NOT NULL,
            reported_date DATE DEFAULT CURRENT_DATE,
            status TEXT DEFAULT 'Open', -- Open, In Progress, Resolved, Closed
            priority TEXT DEFAULT 'Medium', -- Low, Medium, High
            resolved_date DATE,
            resolution_notes TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL
        )
    ''')

    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_room_id ON students(room_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fees_student_id ON fees(student_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fees_status ON fees(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fees_due_date ON fees(due_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_complaints_priority ON complaints(priority)')
    
    conn.commit()
    conn.close()
    print("Database initialized/checked.")

# Initialize DB if it doesn't exist
if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE)):
    init_db()
else:
    # If DB exists, ensure all tables are created
    init_db(overwrite=False)


# --- Helper Functions ---
def update_room_occupancy(conn, room_id):
    """Updates the current_occupancy and status of a room."""
    if room_id is None:
        return

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
        
        cursor.execute('UPDATE rooms SET current_occupancy = ?, status = ? WHERE id = ?', (count, new_status, room_id))
        conn.commit()


# --- Routes ---
@app.route('/')
def index():
    """Homepage for the admin panel with enhanced dashboard."""
    from utils.dashboard import get_dashboard_stats, get_recent_activity
    
    conn = get_db_connection()
    
    # Get dashboard statistics with caching
    stats = get_dashboard_stats(conn)
    
    # Get room occupancy data
    room_data = conn.execute('''
        SELECT id, room_number, capacity, current_occupancy, status
        FROM rooms
        ORDER BY room_number
        LIMIT 10
    ''').fetchall()
    room_data = [dict(room) for room in room_data]
    
    # Get recent activity with error handling
    recent_activity = get_recent_activity(conn, limit=5)
    
    conn.close()
    
    return render_template('index.html', 
                           stats=stats, 
                           room_data=room_data,
                           recent_activity=recent_activity)


# --- Student Routes ---
@app.route('/students')
def view_students():
    """Displays a list of all students with search and filtering."""
    conn = get_db_connection()

    search_name = request.args.get('name', '').strip()
    search_course = request.args.get('course', '').strip()
    search_room = request.args.get('room_number', '').strip()
    filter_course = request.args.get('filter_course', '').strip()

    query = '''
        SELECT s.id, s.name, s.student_id_number, s.contact, s.course, s.email, r.room_number 
        FROM students s 
        LEFT JOIN rooms r ON s.room_id = r.id
    '''
    conditions = []
    params = []

    if search_name:
        conditions.append("s.name LIKE ?")
        params.append(f"%{search_name}%")
    if search_course: # This will search within the course string
        conditions.append("s.course LIKE ?")
        params.append(f"%{search_course}%")
    if search_room:
        conditions.append("r.room_number LIKE ?")
        params.append(f"%{search_room}%")
    if filter_course:
        conditions.append("s.course = ?")
        params.append(filter_course)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY s.name"

    students = conn.execute(query, tuple(params)).fetchall()
    
    # Get distinct courses for the filter dropdown
    courses = conn.execute("SELECT DISTINCT course FROM students WHERE course IS NOT NULL AND course != '' ORDER BY course").fetchall()
    
    conn.close()
    return render_template('view_students.html', 
                           students=students, 
                           courses=courses,
                           search_params={
                               'name': search_name, 
                               'course': search_course, 
                               'room_number': search_room,
                               'filter_course': filter_course
                           })


@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    """Handles adding a new student."""
    conn = get_db_connection()
    if request.method == 'POST':
        # Basic student information
        name = request.form['name']
        student_id_number = request.form.get('student_id_number', '')
        contact = request.form['contact']
        course = request.form['course']
        email = request.form['email']
        admission_date = request.form.get('admission_date') or date.today().isoformat()
        expected_checkout_date = request.form.get('expected_checkout_date', '')
        room_id_str = request.form.get('room_id')

        # Student details
        home_address = request.form.get('home_address', '')
        city = request.form.get('city', '')
        state = request.form.get('state', '')
        zip_code = request.form.get('zip_code', '')
        parent_name = request.form.get('parent_name', '')
        parent_contact = request.form.get('parent_contact', '')
        emergency_contact_name = request.form.get('emergency_contact_name', '')
        emergency_contact_phone = request.form.get('emergency_contact_phone', '')
        additional_notes = request.form.get('additional_notes', '')

        new_room_id = None
        # Prepare form_data for re-rendering in case of error
        form_data = request.form 

        if room_id_str and room_id_str != "None" and room_id_str != "":
            try:
                new_room_id = int(room_id_str)
                room_to_assign = conn.execute('SELECT * FROM rooms WHERE id = ?', (new_room_id,)).fetchone()
                if not room_to_assign:
                    flash('Selected room does not exist.', 'error')
                    available_rooms = conn.execute("SELECT id, room_number, capacity, current_occupancy, status FROM rooms WHERE status = 'Available' ORDER BY room_number").fetchall()
                    conn.close()
                    return render_template('add_student.html', rooms=available_rooms, form_data=form_data)
                if room_to_assign['status'] == 'Maintenance':
                    flash('Cannot assign to a room under maintenance.', 'error')
                    available_rooms = conn.execute("SELECT id, room_number, capacity, current_occupancy, status FROM rooms WHERE status = 'Available' ORDER BY room_number").fetchall()
                    conn.close()
                    return render_template('add_student.html', rooms=available_rooms, form_data=form_data)
                if room_to_assign['current_occupancy'] >= room_to_assign['capacity']:
                    flash('Selected room is already full.', 'error')
                    available_rooms = conn.execute("SELECT id, room_number, capacity, current_occupancy, status FROM rooms WHERE status = 'Available' ORDER BY room_number").fetchall()
                    conn.close()
                    return render_template('add_student.html', rooms=available_rooms, form_data=form_data)
            except ValueError:
                flash('Invalid room ID selected.', 'error')
                available_rooms = conn.execute("SELECT id, room_number, capacity, current_occupancy, status FROM rooms WHERE status = 'Available' ORDER BY room_number").fetchall()
                conn.close()
                return render_template('add_student.html', rooms=available_rooms, form_data=form_data)
        
        try:
            # Insert basic student data
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO students (name, student_id_number, contact, course, email, room_id, admission_date, expected_checkout_date) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, student_id_number, contact, course, email, new_room_id, admission_date, expected_checkout_date))
            
            # Get the ID of the inserted student for student_details
            student_id = cursor.lastrowid
            
            # Insert student details
            if any([home_address, city, state, zip_code, parent_name, parent_contact, 
                    emergency_contact_name, emergency_contact_phone, additional_notes]):
                conn.execute('''
                    INSERT INTO student_details 
                    (student_id, home_address, city, state, zip_code, parent_name, parent_contact, 
                    emergency_contact_name, emergency_contact_phone, additional_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (student_id, home_address, city, state, zip_code, parent_name, parent_contact, 
                      emergency_contact_name, emergency_contact_phone, additional_notes))
            
            conn.commit()
            
            if new_room_id:
                update_room_occupancy(conn, new_room_id)
            flash('Student added successfully!', 'success')
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: students.student_id_number" in str(e):
                flash('Error: Student ID Number already exists.', 'error')
            elif "UNIQUE constraint failed: students.email" in str(e):
                flash('Error: Email already exists.', 'error')
            else:
                flash(f'Error: {e}', 'error')
            # In case of integrity error, re-render with form data
            available_rooms = conn.execute("SELECT id, room_number, capacity, current_occupancy, status FROM rooms WHERE status = 'Available' ORDER BY room_number").fetchall()
            conn.close()
            return render_template('add_student.html', rooms=available_rooms, form_data=form_data)
        except Exception as e:
            flash(f'An error occurred: {e}', 'error')
            available_rooms = conn.execute("SELECT id, room_number, capacity, current_occupancy, status FROM rooms WHERE status = 'Available' ORDER BY room_number").fetchall()
            conn.close()
            return render_template('add_student.html', rooms=available_rooms, form_data=form_data)
        finally:
            if conn: # Ensure connection is closed if it was opened
                conn.close()
        return redirect(url_for('view_students'))

    # GET request
    available_rooms = conn.execute("SELECT id, room_number, capacity, current_occupancy, status FROM rooms WHERE status = 'Available' ORDER BY room_number").fetchall()
    conn.close()
    return render_template('add_student.html', rooms=available_rooms)


@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    """Handles editing an existing student."""
    conn = get_db_connection()
    # Fetch student details once
    student_from_db = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()

    if not student_from_db:
        flash('Student not found!', 'error')
        conn.close()
        return redirect(url_for('view_students'))

    # Fetch student details if available
    student_details = conn.execute('SELECT * FROM student_details WHERE student_id = ?', (student_id,)).fetchone()

    if request.method == 'POST':
        # Basic student information
        name = request.form['name']
        student_id_number = request.form.get('student_id_number', '')
        contact = request.form['contact']
        course = request.form['course']
        email = request.form['email']
        admission_date = request.form.get('admission_date') or student_from_db['admission_date']
        expected_checkout_date = request.form.get('expected_checkout_date', '')
        new_room_id_str = request.form.get('room_id')
        
        # Student details
        home_address = request.form.get('home_address', '')
        city = request.form.get('city', '')
        state = request.form.get('state', '')
        zip_code = request.form.get('zip_code', '')
        parent_name = request.form.get('parent_name', '')
        parent_contact = request.form.get('parent_contact', '')
        emergency_contact_name = request.form.get('emergency_contact_name', '')
        emergency_contact_phone = request.form.get('emergency_contact_phone', '')
        additional_notes = request.form.get('additional_notes', '')
        
        new_room_id = None
        if new_room_id_str and new_room_id_str != "None" and new_room_id_str != "":
            try:
                new_room_id = int(new_room_id_str)
            except ValueError:
                flash('Invalid Room ID format.', 'error')
                current_student_room_id = student_from_db['room_id']
                rooms_for_form = conn.execute('''
                    SELECT id, room_number, capacity, current_occupancy, status FROM rooms 
                    WHERE status = 'Available' OR id = ?
                    ORDER BY room_number
                ''', (current_student_room_id if current_student_room_id is not None else -1,)).fetchall()
                conn.close()
                # Use a merged dict of student_from_db and form to repopulate
                student_display_data = {**student_from_db, **request.form}
                return render_template('edit_student.html', student=student_display_data, details=student_details, rooms=rooms_for_form)

        old_room_id = student_from_db['room_id']
        proceed_with_update = True

        if new_room_id != old_room_id and new_room_id is not None:
            room_to_assign = conn.execute('SELECT capacity, current_occupancy, status FROM rooms WHERE id = ?', (new_room_id,)).fetchone()
            if not room_to_assign:
                flash('New selected room does not exist.', 'error')
                proceed_with_update = False
            elif room_to_assign['status'] == 'Maintenance':
                flash('Cannot assign student to a room under maintenance.', 'error')
                proceed_with_update = False
            elif room_to_assign['current_occupancy'] >= room_to_assign['capacity']:
                flash('New selected room is already full.', 'error')
                proceed_with_update = False
        
        if proceed_with_update:
            try:
                # Begin transaction
                conn.execute('BEGIN TRANSACTION')
                
                # Update basic student information
                conn.execute('''
                    UPDATE students 
                    SET name = ?, student_id_number = ?, contact = ?, course = ?, email = ?, 
                        room_id = ?, admission_date = ?, expected_checkout_date = ?
                    WHERE id = ?
                ''', (name, student_id_number, contact, course, email, new_room_id, 
                      admission_date, expected_checkout_date, student_id))
                
                # Update or insert student details
                if student_details:
                    # Update existing details
                    conn.execute('''
                        UPDATE student_details
                        SET home_address = ?, city = ?, state = ?, zip_code = ?,
                            parent_name = ?, parent_contact = ?,
                            emergency_contact_name = ?, emergency_contact_phone = ?,
                            additional_notes = ?
                        WHERE student_id = ?
                    ''', (home_address, city, state, zip_code, parent_name, parent_contact,
                         emergency_contact_name, emergency_contact_phone, additional_notes, student_id))
                else:
                    # Insert new details if any provided
                    if any([home_address, city, state, zip_code, parent_name, parent_contact, 
                           emergency_contact_name, emergency_contact_phone, additional_notes]):
                        conn.execute('''
                            INSERT INTO student_details
                            (student_id, home_address, city, state, zip_code, parent_name, parent_contact,
                            emergency_contact_name, emergency_contact_phone, additional_notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (student_id, home_address, city, state, zip_code, parent_name, parent_contact,
                             emergency_contact_name, emergency_contact_phone, additional_notes))
                
                # Commit the transaction
                conn.commit()

                # Update room occupancy if changed
                if old_room_id != new_room_id:
                    if old_room_id is not None:
                        update_room_occupancy(conn, old_room_id)
                    if new_room_id is not None:
                        update_room_occupancy(conn, new_room_id)
                
                flash('Student updated successfully!', 'success')
                conn.close()
                return redirect(url_for('view_students'))
            except sqlite3.IntegrityError as e:
                conn.execute('ROLLBACK')
                if "UNIQUE constraint failed: students.student_id_number" in str(e):
                    flash('Error: Student ID Number already exists.', 'error')
                elif "UNIQUE constraint failed: students.email" in str(e):
                    flash('Error: Email already exists.', 'error')
                else:
                    flash(f'Error: {e}', 'error')
            except Exception as e:
                conn.execute('ROLLBACK')
                flash(f'An error occurred: {e}', 'error')
        
        # If update failed or was prevented (proceed_with_update is False or exception occurred)
        current_student_room_id = student_from_db['room_id'] 
        rooms_for_form = conn.execute('''
            SELECT id, room_number, capacity, current_occupancy, status FROM rooms 
            WHERE status = 'Available' OR id = ?
            ORDER BY room_number
        ''', (current_student_room_id if current_student_room_id is not None else -1,)).fetchall()
        conn.close()
        student_display_data = {**student_from_db, **request.form, 'room_id': new_room_id} # Ensure room_id reflects attempted change
        return render_template('edit_student.html', student=student_display_data, details=student_details, rooms=rooms_for_form)

    # GET request for edit_student
    current_student_room_id = student_from_db['room_id']
    available_rooms = conn.execute('''
        SELECT id, room_number, capacity, current_occupancy, status 
        FROM rooms 
        WHERE status = 'Available' OR id = ?
        ORDER BY room_number
    ''', (current_student_room_id if current_student_room_id is not None else -1,)).fetchall()
    
    conn.close()
    return render_template('edit_student.html', student=student_from_db, details=student_details, rooms=available_rooms)


@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    """Handles deleting a student."""
    conn = get_db_connection()
    try:
        # Check if student exists
        student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
        if not student:
            flash('Student not found!', 'error')
            return redirect(url_for('view_students'))

        old_room_id = student['room_id']

        # Delete student
        conn.execute('DELETE FROM students WHERE id = ?', (student_id,))
        # Fees are deleted automatically due to ON DELETE CASCADE

        conn.commit()

        # Update occupancy of the room the student was in
        if old_room_id is not None:
            update_room_occupancy(conn, old_room_id)
        
        flash('Student deleted successfully!', 'success')
    except Exception as e:
        flash(f'An error occurred while deleting student: {e}', 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('view_students'))


@app.route('/student/<int:student_id>')
def view_student_detail(student_id):
    """Displays detailed information about a single student."""
    conn = get_db_connection()
    
    # Get basic student information
    student = conn.execute('''
        SELECT s.*, r.room_number, r.capacity 
        FROM students s
        LEFT JOIN rooms r ON s.room_id = r.id
        WHERE s.id = ?
    ''', (student_id,)).fetchone()
    
    if not student:
        flash('Student not found!', 'error')
        conn.close()
        return redirect(url_for('view_students'))
    
    # Get student details if available
    details = conn.execute('''
        SELECT * FROM student_details WHERE student_id = ?
    ''', (student_id,)).fetchone()
    
    # Get fee history
    fees = conn.execute('''
        SELECT f.id, f.amount, f.due_date, f.paid_date, f.status
        FROM fees f
        WHERE f.student_id = ?
        ORDER BY f.due_date DESC
    ''', (student_id,)).fetchall()
    
    # Process fees to check for overdue status
    processed_fees = []
    today = date.today()
    total_paid = 0
    total_pending = 0
    
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
    
    conn.close()
    
    return render_template('student_detail.html', 
                          student=student, 
                          details=details,
                          fees=processed_fees,
                          total_paid=total_paid,
                          total_pending=total_pending)

# --- Room Routes ---
@app.route('/rooms')
def view_rooms():
    """Displays a list of all rooms with search, filtering and visual representation."""
    conn = get_db_connection()

    search_room_number = request.args.get('room_number', '').strip()
    filter_status = request.args.get('filter_status', '').strip()

    query = '''
        SELECT r.id, r.room_number, r.capacity, r.current_occupancy, r.status 
        FROM rooms r
    '''
    conditions = []
    params = []

    if search_room_number:
        conditions.append("r.room_number LIKE ?")
        params.append(f"%{search_room_number}%")
    
    if filter_status:
        conditions.append("r.status = ?")
        params.append(filter_status)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY r.room_number"

    rooms_from_db = conn.execute(query, tuple(params)).fetchall()

    rooms_with_students = []
    for room_row in rooms_from_db:
        room = dict(room_row)
        students_in_room = conn.execute('SELECT id, name FROM students WHERE room_id = ? ORDER BY name', (room['id'],)).fetchall()
        room['students'] = students_in_room
        
        # Prevent division by zero in template
        if room['capacity'] == 0:
            room['capacity'] = 1
            
        rooms_with_students.append(room)
    
    # For the filter dropdown - these are usually fixed statuses
    room_statuses = ['Available', 'Full', 'Maintenance']
    
    conn.close()
    return render_template('view_rooms_enhanced.html', 
                           rooms=rooms_with_students,
                           room_statuses=room_statuses,
                           search_params={
                               'room_number': search_room_number,
                               'filter_status': filter_status
                           })


@app.route('/add_room', methods=['GET', 'POST'])
def add_room():
    """Handles adding a new room."""
    if request.method == 'POST':
        room_number = request.form['room_number']
        capacity = request.form['capacity']
        status = request.form.get('status', 'Available')
        conn = get_db_connection()
        try:
            capacity = int(capacity)
            if capacity <= 0:
                flash('Capacity must be a positive number.', 'error')
            else:
                conn.execute('INSERT INTO rooms (room_number, capacity, status) VALUES (?, ?, ?)',
                             (room_number, capacity, status))
                conn.commit()
                flash('Room added successfully!', 'success')
                return redirect(url_for('view_rooms'))
        except ValueError:
            flash('Invalid capacity. Must be a number.', 'error')
        except sqlite3.IntegrityError:
            flash('Error: Room number already exists.', 'error')
        except Exception as e:
            flash(f'An error occurred: {e}', 'error')
        finally:
            conn.close()
    return render_template('add_room.html')


@app.route('/edit_room/<int:room_id>', methods=['GET', 'POST'])
def edit_room(room_id):
    """Handles editing an existing room."""
    conn = get_db_connection()
    if request.method == 'POST':
        room_number = request.form['room_number']
        capacity = request.form['capacity']
        status = request.form['status']
        try:
            capacity = int(capacity)
            if capacity <= 0:
                flash('Capacity must be a positive number.', 'error')
            else:
                conn.execute('UPDATE rooms SET room_number = ?, capacity = ?, status = ? WHERE id = ?',
                             (room_number, capacity, status, room_id))
                conn.commit()
                update_room_occupancy(conn, room_id)
                flash('Room updated successfully!', 'success')
                return redirect(url_for('view_rooms'))
        except ValueError:
            flash('Invalid capacity. Must be a number.', 'error')
        except sqlite3.IntegrityError:
            flash('Error: Room number already exists for another room.', 'error')
        except Exception as e:
            flash(f'An error occurred: {e}', 'error')
        finally:
            conn.close()
        return render_template('edit_room.html', room={'id': room_id, 'room_number': room_number, 'capacity': capacity, 'status': status})

    room = conn.execute('SELECT * FROM rooms WHERE id = ?', (room_id,)).fetchone()
    conn.close()
    if not room:
        flash('Room not found!', 'error')
        return redirect(url_for('view_rooms'))
    return render_template('edit_room.html', room=room)


@app.route('/delete_room/<int:room_id>', methods=['POST'])
def delete_room(room_id):
    """Handles deleting a room."""
    conn = get_db_connection()
    occupants = conn.execute('SELECT COUNT(*) FROM students WHERE room_id = ?', (room_id,)).fetchone()[0]
    try:
        if occupants > 0:
            flash('Cannot delete room: It is currently occupied. Please reassign students first.', 'error')
        else:
            conn.execute('DELETE FROM rooms WHERE id = ?', (room_id,))
            conn.commit()
            flash('Room deleted successfully!', 'success')
    except Exception as e:
        flash(f'An error occurred while deleting room: {e}', 'error')
    finally:
        conn.close()
    return redirect(url_for('view_rooms'))


# --- Fee Routes ---
@app.route('/fees')
def view_fees():
    """Displays fee records."""
    conn = get_db_connection()
    fees_from_db = conn.execute('''
        SELECT f.id, s.name AS student_name, f.student_id, f.amount, f.due_date, f.paid_date, f.status
        FROM fees f
        JOIN students s ON f.student_id = s.id
        ORDER BY f.due_date ASC, s.name ASC    ''').fetchall()
    conn.close()
    
    processed_fees = []
    today = date.today()
    for fee_row in fees_from_db:
        fee = dict(fee_row)  # Convert sqlite3.Row to dict for easier modification
        fee['is_overdue'] = False
        
        # Process overdue status
        if fee['status'] == 'Pending' and fee['due_date']:
            try:
                due_date_obj = date.fromisoformat(fee['due_date'])
                if due_date_obj < today:
                    fee['is_overdue'] = True
                    # Auto-update overdue fees
                    with get_db_connection() as update_conn:
                        update_conn.execute("UPDATE fees SET status = 'Overdue' WHERE id = ? AND status = 'Pending'", (fee['id'],))
                        update_conn.commit()
                    fee['status'] = 'Overdue'  # Reflect change immediately
            except (ValueError, TypeError):
                pass  # Invalid date format in DB, treat as not overdue
        
        # Convert date strings to date objects for consistent formatting in template
        if fee['due_date']:
            try:
                fee['due_date'] = date.fromisoformat(fee['due_date'])
            except ValueError:
                fee['due_date'] = None  # Or handle as an error
        if fee['paid_date']:
            try:
                fee['paid_date'] = date.fromisoformat(fee['paid_date'])
            except ValueError:
                fee['paid_date'] = None  # Or handle as an error
        processed_fees.append(fee)
    
    return render_template('view_fees.html', fees=processed_fees)


@app.route('/add_fee', methods=['GET', 'POST'])
def add_fee():
    """Adds a fee record for a student."""
    conn = get_db_connection()
    if request.method == 'POST':
        student_id = request.form['student_id']
        amount = request.form['amount']
        due_date = request.form['due_date']
        status = request.form.get('status', 'Pending')
        try:
            amount = float(amount)
            conn.execute('BEGIN TRANSACTION')
            conn.execute('INSERT INTO fees (student_id, amount, due_date, status) VALUES (?, ?, ?, ?)',
                         (student_id, amount, due_date, status))
            conn.commit()
            
            # Get student name for the flash message
            student_name = conn.execute('SELECT name FROM students WHERE id = ?', (student_id,)).fetchone()['name']
            flash(f'Fee record for {student_name} added successfully!', 'success')
            return redirect(url_for('view_fees'))
        except ValueError:
            flash('Invalid amount. Please enter a valid number.', 'error')
        except Exception as e:
            conn.execute('ROLLBACK')
            flash(f'An error occurred: {e}', 'error')
        finally:
            conn.close()
        students = conn.execute('SELECT id, name FROM students ORDER BY name').fetchall()
        return render_template('add_fee.html', students=students, form_data=request.form)

    students = conn.execute('SELECT id, name FROM students ORDER BY name').fetchall()
    conn.close()
    return render_template('add_fee.html', students=students)

@app.route('/mark_fee_paid/<int:fee_id>', methods=['POST'])
def mark_fee_paid(fee_id):
    """Marks a fee record as paid."""
    conn = get_db_connection()
    try:
        today = date.today().strftime('%Y-%m-%d')
        conn.execute("UPDATE fees SET status = 'Paid', paid_date = ? WHERE id = ?", (today, fee_id))
        conn.commit()
        flash('Fee marked as paid!', 'success')
    except Exception as e:
        flash(f'Error updating fee status: {e}', 'error')
    finally:
        conn.close()
    return redirect(url_for('view_fees'))


# --- Reporting Routes ---
@app.route('/reports/fee_payments')
def fee_payments_report():
    conn = get_db_connection()
    today = date.today()

    # Get filter parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    student_id_filter = request.args.get('student_id_filter')
    payment_status_filter = request.args.get('payment_status_filter')

    base_query = """
        SELECT f.id, s.name AS student_name, s.id AS student_id_fk, s.contact AS student_id_number, 
               f.amount, f.due_date, f.paid_date, f.status
        FROM fees f
        JOIN students s ON f.student_id = s.id
    """
    conditions = []
    params = []

    if start_date_str:
        conditions.append("f.due_date >= ?")
        params.append(start_date_str)
    if end_date_str:
        conditions.append("f.due_date <= ?")
        params.append(end_date_str)
    if student_id_filter:
        conditions.append("s.id = ?")
        params.append(student_id_filter)
    
    # Special handling for 'Overdue' status filter
    if payment_status_filter and payment_status_filter != 'Overdue':
        conditions.append("f.status = ?")
        params.append(payment_status_filter)
    elif payment_status_filter == 'Overdue':
        conditions.append("f.status IN ('Pending', 'Overdue')")
        conditions.append("f.due_date < ?")
        params.append(today.isoformat())

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)
    
    base_query += " ORDER BY f.due_date DESC, s.name ASC"

    fees_from_db = conn.execute(base_query, tuple(params)).fetchall()

    processed_fees = []
    for fee_row in fees_from_db:
        fee = dict(fee_row)
        fee['is_overdue'] = False
        if fee['status'] != 'Paid' and fee['due_date']:
            try:
                due_date_obj = date.fromisoformat(fee['due_date'])
                if due_date_obj < today:
                    fee['is_overdue'] = True
            except (ValueError, TypeError):
                pass # Invalid date format
        
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

    # If filtering by 'Overdue', we need to re-filter the Python list 
    # because the SQL for overdue is broad (Pending/Overdue AND due_date < today)
    # but we only want to show those that are *actually* overdue after Python processing.
    if payment_status_filter == 'Overdue':
        processed_fees = [f for f in processed_fees if f['is_overdue']]

    students_for_filter = conn.execute("SELECT id, name, contact AS student_id_number FROM students ORDER BY name").fetchall()
    conn.close()

    return render_template('reports/fee_payments_report.html', 
                           fees=processed_fees, 
                           students_for_filter=students_for_filter,
                           request=request) # Pass request for sticky form values

@app.route('/reports/room_occupancy')
def room_occupancy_report():
    conn = get_db_connection()
    filter_status = request.args.get('filter_status', '').strip()

    query = """
        SELECT r.id, r.room_number, r.capacity, r.current_occupancy, r.status
        FROM rooms r
    """
    params = []
    if filter_status:
        query += " WHERE r.status = ?"
        params.append(filter_status)
    
    query += " ORDER BY r.room_number"

    rooms_from_db = conn.execute(query, tuple(params)).fetchall()

    rooms_data = []
    for room_row in rooms_from_db:
        room = dict(room_row) # Convert to dict for easier modification        # Fetch students in this room, including their student ID number (assuming 'contact' field stores this)
        students_in_room = conn.execute("""
            SELECT id, name, contact AS student_id_number 
            FROM students 
            WHERE room_id = ? 
            ORDER BY name
        """, (room['id'],)).fetchall()
        
        room['students'] = [dict(s) for s in students_in_room]
        rooms_data.append(room)

    # For the filter dropdown
    room_statuses_for_filter = ['Available', 'Full', 'Maintenance']
    
    conn.close()
    return render_template('reports/room_occupancy_report.html', 
                           rooms_data=rooms_data, 
                           room_statuses_for_filter=room_statuses_for_filter,
                           request=request) # Pass request for sticky form values

# --- Complaint / Maintenance Routes ---
# COMPLAINT_STATUSES = ["Open", "In Progress", "Resolved", "Closed"]
# COMPLAINT_PRIORITIES = ["Low", "Medium", "High"]

# @app.route('/complaints')
# def view_complaints():
#     conn = get_db_connection()
#     filter_room_number = request.args.get('filter_room_number', '').strip()
#     filter_status = request.args.get('filter_status', '').strip()
#     filter_priority = request.args.get('filter_priority', '').strip()

#     query = \"\"\"
#         SELECT c.id, c.reported_date, c.reported_by_name, c.description, c.priority, c.status, c.resolved_date,
#                s.name AS student_name, s.id AS student_id,
#                r.room_number, r.id AS room_id
#         FROM complaints c
#         LEFT JOIN students s ON c.student_id = s.id
#         LEFT JOIN rooms r ON c.room_id = r.id
#     \"\"\"
#     conditions = []
#     params = []

#     if filter_room_number:
#         conditions.append("r.room_number LIKE ?")
#         params.append(f"%{filter_room_number}%")
#     if filter_status:
#         conditions.append("c.status = ?")
#         params.append(filter_status)
#     if filter_priority:
#         conditions.append("c.priority = ?")
#         params.append(filter_priority)

#     if conditions:
#         query += " WHERE " + " AND ".join(conditions)
    
#     query += " ORDER BY c.reported_date DESC, c.priority, c.id DESC"

#     complaints_from_db = conn.execute(query, tuple(params)).fetchall()
#     conn.close()

#     processed_complaints = []
#     for complaint_row in complaints_from_db:
#         complaint = dict(complaint_row)
#         if complaint['reported_date']:
#             try:
#                 complaint['reported_date'] = date.fromisoformat(complaint['reported_date'])
#             except (ValueError, TypeError):
#                 complaint['reported_date'] = None # Or handle as an error / keep as string
#         if complaint['resolved_date']:
#             try:
#                 complaint['resolved_date'] = date.fromisoformat(complaint['resolved_date'])
#             except (ValueError, TypeError):
#                 complaint['resolved_date'] = None # Or handle as an error / keep as string
#         processed_complaints.append(complaint)

#     return render_template('view_complaints.html', 
#                            complaints=processed_complaints,
#                            complaint_statuses=COMPLAINT_STATUSES,
#                            complaint_priorities=COMPLAINT_PRIORITIES,
#                            request=request)

# @app.route('/add_complaint', methods=['GET', 'POST'])
# def add_complaint():
#     conn = get_db_connection()
#     if request.method == 'POST':
#         reported_by_name = request.form.get('reported_by_name', '').strip()
#         student_id_str = request.form.get('student_id')
#         room_id_str = request.form.get('room_id')
#         description = request.form['description'].strip()
#         priority = request.form.get('priority', 'Medium')
#         status = request.form.get('status', 'Open')

#         student_id = int(student_id_str) if student_id_str else None
#         room_id = int(room_id_str) if room_id_str else None

#         if not description:
#             flash('Description is required.', 'error')
#             # Re-populate dropdowns for the form
#             students = conn.execute("SELECT id, name, contact FROM students ORDER BY name").fetchall()
#             rooms = conn.execute("SELECT id, room_number FROM rooms ORDER BY room_number").fetchall()
#             conn.close()
#             return render_template('add_complaint.html', 
#                                    students=students, rooms=rooms, 
#                                    complaint_statuses=COMPLAINT_STATUSES,
#                                    complaint_priorities=COMPLAINT_PRIORITIES,
#                                    form_data=request.form)
#         try:
#             conn.execute(\"\"\"
#                 INSERT INTO complaints (reported_by_name, student_id, room_id, description, priority, status, reported_date)
#                 VALUES (?, ?, ?, ?, ?, ?, ?)
#             \"\"\", (reported_by_name, student_id, room_id, description, priority, status, date.today().isoformat()))
#             conn.commit()
#             flash('Complaint/Maintenance request added successfully!', 'success')
#         except Exception as e:
#             flash(f'An error occurred: {e}', 'error')
#         finally:
#             conn.close()
#         return redirect(url_for('view_complaints'))

#     # GET request
#     students = conn.execute("SELECT id, name, contact FROM students ORDER BY name").fetchall() # contact is student_id_number
#     rooms = conn.execute("SELECT id, room_number FROM rooms ORDER BY room_number").fetchall()
#     conn.close()
#     return render_template('add_complaint.html', 
#                            students=students, 
#                            rooms=rooms,
#                            complaint_statuses=COMPLAINT_STATUSES,
#                            complaint_priorities=COMPLAINT_PRIORITIES)

# @app.route('/edit_complaint/<int:complaint_id>', methods=['GET', 'POST'])
# def edit_complaint(complaint_id):
#     # This is a placeholder. Implement actual edit logic here.
#     conn = get_db_connection()
#     complaint = conn.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    
#     if not complaint:
#         flash('Complaint not found!', 'error')
#         conn.close()
#         return redirect(url_for('view_complaints'))

#     if request.method == 'POST':
#         reported_by_name = request.form.get('reported_by_name', '').strip()
#         student_id_str = request.form.get('student_id')
#         room_id_str = request.form.get('room_id')
#         description = request.form['description'].strip()
#         priority = request.form.get('priority', 'Medium')
#         status = request.form.get('status', 'Open')
#         resolved_date_str = request.form.get('resolved_date')
#         resolution_notes = request.form.get('resolution_notes', '').strip()

#         student_id = int(student_id_str) if student_id_str else None
#         room_id = int(room_id_str) if room_id_str else None
#         resolved_date = date.fromisoformat(resolved_date_str) if resolved_date_str else None

#         if not description:
#             flash('Description is required.', 'error')
#             # Re-populate dropdowns for the form
#             students = conn.execute("SELECT id, name, contact FROM students ORDER BY name").fetchall()
#             rooms = conn.execute("SELECT id, room_number FROM rooms ORDER BY room_number").fetchall()
#             # Pass current complaint data merged with form data to preserve edits
#             current_form_data = {**dict(complaint), **request.form}
#             conn.close()
#             return render_template('edit_complaint.html', 
#                                    complaint=current_form_data, 
#                                    students=students, rooms=rooms,
#                                    complaint_statuses=COMPLAINT_STATUSES,
#                                    complaint_priorities=COMPLAINT_PRIORITIES,
#                                    complaint_id=complaint_id)
#         try:
#             conn.execute(\"\"\"
#                 UPDATE complaints 
#                 SET reported_by_name = ?, student_id = ?, room_id = ?, description = ?, 
#                     priority = ?, status = ?, resolved_date = ?, resolution_notes = ?
#                 WHERE id = ?
#             \"\"\", (reported_by_name, student_id, room_id, description, priority, status, 
#                   resolved_date.isoformat() if resolved_date else None, resolution_notes, complaint_id))
#             conn.commit()
#             flash('Complaint updated successfully!', 'success')
#         except Exception as e:
#             flash(f'An error occurred: {e}', 'error') # Basic error flashing
#         finally:
#             if conn: # Ensure connection is closed if it was opened
#                 conn.close()
#         return redirect(url_for('view_complaints'))

#     # GET request
#     students = conn.execute("SELECT id, name, contact FROM students ORDER BY name").fetchall()
#     rooms = conn.execute("SELECT id, room_number FROM rooms ORDER BY room_number").fetchall()
#     conn.close()
#     # Convert date strings to YYYY-MM-DD for date input field
#     complaint_data = dict(complaint)
#     if complaint_data.get('resolved_date') and isinstance(complaint_data['resolved_date'], str):
#         try:
#             complaint_data['resolved_date'] = date.fromisoformat(complaint_data['resolved_date']).strftime('%Y-%m-%d')
#         except ValueError:
#             complaint_data['resolved_date'] = '' # Clear if invalid
#     elif complaint_data.get('resolved_date') is None:
#         complaint_data['resolved_date'] = '' # Ensure it's an empty string for the form input

#     return render_template('edit_complaint.html', 
#                            complaint=complaint_data, 
#                            students=students, 
#                            rooms=rooms,
#                            complaint_statuses=COMPLAINT_STATUSES,
#                            complaint_priorities=COMPLAINT_PRIORITIES,
#                            complaint_id=complaint_id)

# @app.route('/delete_complaint/<int:complaint_id>', methods=['POST'])
# def delete_complaint(complaint_id):
#     conn = get_db_connection()
#     try:
#         conn.execute('DELETE FROM complaints WHERE id = ?', (complaint_id,))
#         conn.commit()
#         flash('Complaint deleted successfully!', 'success')
#     except Exception as e:
#         flash(f'An error occurred: {e}', 'error')
#     finally:
#         if conn:
#             conn.close()
#     return redirect(url_for('view_complaints'))

@app.route('/batch_fees', methods=['GET', 'POST'])
def batch_assign_fees():
    """Handle batch assignment of fees to multiple students."""
    from utils.batch_processing import process_batch_fees, generate_recurring_fees
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        assignment_type = request.form.get('assignment_type')
        fee_type = request.form.get('fee_type')
        amount = request.form.get('amount')
        due_date = request.form.get('due_date')
        description = request.form.get('description', '')
        
        # Convert amount to float
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            flash('Invalid amount. Please enter a valid number.', 'error')
            students = conn.execute("SELECT id, name, course FROM students ORDER BY name").fetchall()
            courses = conn.execute("SELECT DISTINCT course FROM students WHERE course IS NOT NULL AND course != '' ORDER BY course").fetchall()
            conn.close()
            return render_template('fees/add_batch_fees.html', students=students, courses=courses)
        
        if assignment_type == 'selected':
            # Get selected student IDs (multi-select)
            student_ids = request.form.getlist('student_ids')
            if not student_ids:
                flash('Please select at least one student.', 'error')
                students = conn.execute("SELECT id, name, course FROM students ORDER BY name").fetchall()
                courses = conn.execute("SELECT DISTINCT course FROM students WHERE course IS NOT NULL AND course != '' ORDER BY course").fetchall()
                conn.close()
                return render_template('fees/add_batch_fees.html', students=students, courses=courses)
                
            # Process the batch
            success_count, errors = process_batch_fees(conn, student_ids, amount, due_date, description or f"{fee_type.title()} Fee")
            
        elif assignment_type == 'course':
            course_filter = request.form.get('course_filter')
            if not course_filter:
                flash('Please select a course.', 'error')
                students = conn.execute("SELECT id, name, course FROM students ORDER BY name").fetchall()
                courses = conn.execute("SELECT DISTINCT course FROM students WHERE course IS NOT NULL AND course != '' ORDER BY course").fetchall()
                conn.close()
                return render_template('fees/add_batch_fees.html', students=students, courses=courses)
                
            # Get all students in the course
            course_students = conn.execute("SELECT id FROM students WHERE course = ? ORDER BY name", (course_filter,)).fetchall()
            student_ids = [s['id'] for s in course_students]
            
            if not student_ids:
                flash(f'No students found for course: {course_filter}', 'error')
                students = conn.execute("SELECT id, name, course FROM students ORDER BY name").fetchall()
                courses = conn.execute("SELECT DISTINCT course FROM students WHERE course IS NOT NULL AND course != '' ORDER BY course").fetchall()
                conn.close()
                return render_template('fees/add_batch_fees.html', students=students, courses=courses)
                
            # Process the batch
            success_count, errors = process_batch_fees(conn, student_ids, amount, due_date, description or f"{fee_type.title()} Fee - {course_filter}")
            
        elif assignment_type == 'all':
            # For predefined fee types, use the predefined frequencies
            if fee_type != 'custom':
                success_count, errors = generate_recurring_fees(conn, fee_type, None, amount)
            else:
                # Get all students for custom amount
                all_students = conn.execute("SELECT id FROM students").fetchall()
                student_ids = [s['id'] for s in all_students]
                success_count, errors = process_batch_fees(conn, student_ids, amount, due_date, description or "Fee")
        
        # Display results
        if errors:
            for error in errors:
                flash(error, 'error')
        
        if success_count > 0:
            flash(f'Successfully assigned fees to {success_count} student(s).', 'success')
        
        conn.close()
        return redirect(url_for('view_fees'))
        
    # GET request - form display
    students = conn.execute("SELECT id, name, course FROM students ORDER BY name").fetchall()
    courses = conn.execute("SELECT DISTINCT course FROM students WHERE course IS NOT NULL AND course != '' ORDER BY course").fetchall()
    conn.close()
    
    return render_template('fees/add_batch_fees.html', students=students, courses=courses)

@app.route('/generate_recurring_fees', methods=['POST'])
def generate_fees():
    """Generate recurring fees for all students."""
    try:
        from utils.batch_processing import generate_recurring_fees
    except ImportError:
        flash('Fee generation module not found. Please ensure utils/batch_processing.py exists.', 'error')
        return redirect(url_for('view_fees'))
    
    try:
        with DatabaseConnection() as conn:
            fee_type = request.form.get('fee_type', 'monthly')
            course_filter = request.form.get('course_filter')
            
            if fee_type not in ['monthly', 'semester', 'yearly']:
                flash('Invalid fee type selected.', 'error')
                return redirect(url_for('view_fees'))
            
            success_count, errors = generate_recurring_fees(conn, fee_type, course_filter)
            
            if errors:
                for error in errors:
                    flash(error, 'error')
            
            if success_count > 0:
                flash(f'Successfully generated {fee_type} fees for {success_count} student(s).', 'success')
            else:
                flash('No fees were generated.', 'warning')
            
    except Exception as e:
        flash(f'An error occurred while generating fees: {str(e)}', 'error')
    
    return redirect(url_for('view_fees'))

if __name__ == '__main__':
    # To make it accessible on your local network:
    app.run(host='0.0.0.0', port=5000, debug=True)
    # For development only (accessible only on your machine):
    # app.run(debug=True)
