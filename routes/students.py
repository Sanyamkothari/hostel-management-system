"""
Student management routes for the Hostel Management System
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.db import StudentModel, RoomModel
from utils.validators import validate_student_data
from utils.file_handlers import save_profile_photo
from datetime import date, datetime
from db_utils import get_db_connection, DatabaseConnection

student_bp = Blueprint('student', __name__, url_prefix='/students')

@student_bp.route('/')
def view_students():
    """List all students with optional filtering."""
    search_params = {
        'name': request.args.get('name', ''),
        'course': request.args.get('course', ''),
        'room_number': request.args.get('room_number', ''),
        'filter_course': request.args.get('filter_course', '')
    }
    
    students = StudentModel.get_all_students(search_params)
    courses = StudentModel.get_all_courses()
    
    # Determine the view mode (list or card)
    view_mode = request.args.get('view', 'list')
    
    return render_template(
        'students/view_students.html', 
        students=students, 
        courses=courses,
        search_params=search_params,
        view_mode=view_mode
    )

@student_bp.route('/add', methods=['GET', 'POST'])
def add_student():
    """Add a new student."""
    if request.method == 'POST':
        # Get form data
        student_data = {
            'name': request.form.get('name'),
            'student_id_number': request.form.get('student_id_number'),
            'contact': request.form.get('contact'),
            'email': request.form.get('email'),
            'course': request.form.get('course'),
            'room_id': request.form.get('room_id', type=int, default=None),
            'admission_date': request.form.get('admission_date', date.today().isoformat()),
            'expected_checkout_date': request.form.get('expected_checkout_date', '')
        }
        
        # Get additional details
        details_data = {
            'home_address': request.form.get('home_address', ''),
            'city': request.form.get('city', ''),
            'state': request.form.get('state', ''),
            'zip_code': request.form.get('zip_code', ''),
            'parent_name': request.form.get('parent_name', ''),
            'parent_contact': request.form.get('parent_contact', ''),
            'emergency_contact_name': request.form.get('emergency_contact_name', ''),
            'emergency_contact_phone': request.form.get('emergency_contact_phone', ''),
            'additional_notes': request.form.get('additional_notes', '')
        }
        
        # Validate data
        errors = validate_student_data(student_data)
        if errors:
            for error in errors:
                flash(error, 'error')
            rooms = RoomModel.get_available_rooms()
            return render_template('students/add_student.html', rooms=rooms)
        
        # Process profile photo if provided
        if 'profile_photo' in request.files:
            photo_file = request.files['profile_photo']
            if photo_file.filename:
                photo_path = save_profile_photo(photo_file)
                student_data['profile_photo'] = photo_path
        
        # Save student to database
        try:
            StudentModel.add_student(student_data, details_data)
            flash('Student added successfully!', 'success')
            return redirect(url_for('student.view_students'))
        except Exception as e:
            flash(f'Error adding student: {str(e)}', 'error')
    
    # GET request - show the form
    rooms = RoomModel.get_available_rooms()
    return render_template('students/add_student.html', rooms=rooms)

@student_bp.route('/<int:student_id>')
def view_student(student_id):
    """View student details."""
    student_row = StudentModel.get_student_by_id(student_id)
    if not student_row:
        flash('Student not found!', 'error')
        return redirect(url_for('student.view_students'))
    
    # Convert sqlite3.Row to a dictionary for easier modification
    student = dict(student_row)
    
    details = StudentModel.get_student_details(student_id)
    
    # Get fee data using our utility function
    from utils.fee_utils import get_student_fee_summary
    fee_data = get_student_fee_summary(student_id)

    # Convert expected_checkout_date to date object if it's a string
    if 'expected_checkout_date' in student and student['expected_checkout_date']:
        try:
            if isinstance(student['expected_checkout_date'], str):
                student['expected_checkout_date'] = datetime.strptime(student['expected_checkout_date'], '%Y-%m-%d').date()
        except Exception:
            # Handle potential parsing errors if date string format is unexpected
            pass # Keep original value if conversion fails

    return render_template(
        'students/student_details.html', 
        student=student, # Pass the modified dictionary
        details=details,
        fees=fee_data['fees'],
        fees_summary=fee_data['summary'],
        current_date=date.today()  # Pass as date object
    )

@student_bp.route('/<int:student_id>/edit', methods=['GET', 'POST'])
def edit_student(student_id):
    """Edit student details."""
    # Similar to add_student but with pre-filled data
    student = StudentModel.get_student_by_id(student_id)
    if not student:
        flash('Student not found!', 'error')
        return redirect(url_for('student.view_students'))
    
    if request.method == 'POST':
        # Update student data
        # Implementation similar to add_student
        # Would need to get all form data and update the database
        pass
    
    # GET request - show the form with current data
    details = StudentModel.get_student_details(student_id)
    rooms = RoomModel.get_available_rooms()
    return render_template(
        'students/edit_student.html', 
        student=student, 
        details=details,
        rooms=rooms
    )

@student_bp.route('/<int:student_id>/delete', methods=['POST'])
def delete_student(student_id):
    """Delete a student."""
    try:
        StudentModel.delete_student(student_id)
        flash('Student deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting student: {str(e)}', 'error')
    
    return redirect(url_for('student.view_students'))
