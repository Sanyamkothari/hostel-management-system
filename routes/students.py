"""
Student management routes for the Hostel Management System
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app
from models.db import StudentModel, RoomModel
from models.hostels import Hostel # Add this import
from flask import g # Ensure g is imported
from utils.validators import validate_student_data
from utils.file_handlers import save_profile_photo
from datetime import date, datetime
from db_utils import get_db_connection, DatabaseConnection
from utils.socket_utils import emit_student_event

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
    all_hostels = []
    current_user_role = None
    form_hostel_id = None # To potentially pre-select a hostel if an ID is passed

    if hasattr(g, 'user') and g.user:
        from utils.user_utils import get_user_attribute 
        current_user_role = get_user_attribute('role')
        if current_user_role == 'manager':
            # Managers add students to their own hostel
            form_hostel_id = get_user_attribute('hostel_id')
        elif current_user_role == 'owner':
            all_hostels = Hostel.get_all_hostels()
            # Allow pre-selection via query parameter for owners
            selected_hostel_id_query = request.args.get('hostel_id', type=int)
            if selected_hostel_id_query:
                form_hostel_id = selected_hostel_id_query
    else:
        flash('User not logged in.', 'error')
        return redirect(url_for('auth.login'))

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
        # Define details_data here so it's always available for error paths
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

        # Determine hostel_id for the student
        if current_user_role == 'manager':
            student_data['hostel_id'] = get_user_attribute('hostel_id')
        elif current_user_role == 'owner':
            student_data['hostel_id'] = request.form.get('hostel_id', type=int)
            if not student_data['hostel_id']:
                flash('Owner must select a hostel for the new student.', 'error')
                # Assuming RoomModel.get_available_rooms() fetches all or needs adjustment
                rooms = RoomModel.get_available_rooms() 
                return render_template('students/add_student.html', 
                                       rooms=rooms, 
                                       hostels=all_hostels, 
                                       current_user_role=current_user_role,
                                       form_hostel_id=form_hostel_id,
                                       form_data=request.form)
        else:
            flash('Could not determine hostel for the student. Please login.', 'error')
            return redirect(url_for('auth.login'))

        # Validate data
        errors = validate_student_data(student_data)
        if errors:
            for error in errors:
                flash(error, 'error')
            # Fetch rooms, potentially filtered if get_available_rooms is updated or a new method is used
            rooms = RoomModel.get_available_rooms() # Or RoomModel.get_available_rooms_by_hostel(student_data.get('hostel_id'))
            return render_template('students/add_student.html', 
                                   rooms=rooms, 
                                   hostels=all_hostels, 
                                   current_user_role=current_user_role,
                                   form_hostel_id=student_data.get('hostel_id'),
                                   form_data=request.form)
        
        # Process profile photo if provided
        if 'profile_photo' in request.files:
            photo_file = request.files['profile_photo']
            if photo_file.filename:
                photo_path = save_profile_photo(photo_file)
                student_data['profile_photo'] = photo_path        # Save student to database
        try:
            # Ensure StudentModel.add_student can handle 'hostel_id' in student_data
            result = StudentModel.add_student(student_data, details_data) # details_data is now defined
            
            if result.get('success'):
                student_id = result.get('student_id')
                
                # Emit Socket.IO event for real-time updates
                try:
                    from app import socketio
                    
                    # Get the newly added student's complete information for the event
                    new_student = StudentModel.get_student_by_id(student_id)
                    if new_student:
                        event_data = {
                            'student_id': student_id,
                            'name': student_data['name'],
                            'student_id_number': student_data['student_id_number'],
                            'course': student_data['course'],
                            'room_id': student_data.get('room_id'),
                            'hostel_id': student_data['hostel_id'],
                            'admission_date': student_data['admission_date'],
                            'timestamp': datetime.now().isoformat(),
                            'action': 'student_added',                        'user': g.user.get('username', 'Unknown') if g.user else 'System'
                        }
                        
                        emit_student_event('student_added', event_data, student_data.get('hostel_id'))
                        
                except Exception as socket_error:
                    print(f"Socket.IO error in student addition: {socket_error}")
                    # Don't let socket errors affect the main functionality
                    pass
                
                flash('Student added successfully!', 'success')
                return redirect(url_for('student.view_students'))
            else:
                flash(f'Error adding student: {result.get("error", "Unknown error")}', 'error')
                rooms = RoomModel.get_available_rooms()
                return render_template('students/add_student.html', 
                                       rooms=rooms, 
                                       hostels=all_hostels, 
                                       current_user_role=current_user_role,
                                       form_hostel_id=student_data.get('hostel_id'),
                                       form_data=request.form)
        except Exception as e:
            flash(f'Error adding student: {str(e)}', 'error')
            rooms = RoomModel.get_available_rooms() # Or filter by hostel
            return render_template('students/add_student.html', 
                                   rooms=rooms, 
                                   hostels=all_hostels, 
                                   current_user_role=current_user_role,
                                   form_hostel_id=student_data.get('hostel_id'),
                                   form_data=request.form)
    
    # GET request - show the form
    # Filter rooms based on the (potentially pre-selected) hostel_id for owners, or manager's hostel
    rooms_for_hostel_id = form_hostel_id
    if current_user_role == 'manager':
        rooms_for_hostel_id = get_user_attribute('hostel_id')
    
    # For GET, RoomModel.get_available_rooms might need to be adapted or a new function
    # RoomModel.get_available_rooms_by_hostel(hostel_id) could be used if it exists.
    # If form_hostel_id is None for owner (no pre-selection), maybe show no rooms or all rooms.
    # For now, let's assume get_available_rooms() gets all, and the template handles filtering or is updated.
    if current_user_role == 'manager':
         # If RoomModel.get_available_rooms cannot be filtered by hostel_id,
         # this will fetch all rooms. The template or JS would need to filter.
         # A better approach is to modify RoomModel.get_available_rooms or add a new method.
        rooms = RoomModel.get_available_rooms() # Ideally: RoomModel.get_available_rooms(hostel_id=get_user_attribute('hostel_id'))
    elif current_user_role == 'owner' and form_hostel_id:
        rooms = RoomModel.get_available_rooms() # Ideally: RoomModel.get_available_rooms(hostel_id=form_hostel_id)
    else: # Owner with no specific hostel selected for GET, or other roles
        rooms = RoomModel.get_available_rooms()


    return render_template('students/add_student.html', 
                           rooms=rooms, 
                           hostels=all_hostels, 
                           current_user_role=current_user_role,
                           form_hostel_id=form_hostel_id)

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
    
    # Process dates properly
    # Convert admission_date to date object if it's a string
    if 'admission_date' in student and student['admission_date']:
        try:
            if isinstance(student['admission_date'], str):
                student['admission_date'] = datetime.strptime(student['admission_date'], '%Y-%m-%d').date()
            elif not isinstance(student['admission_date'], date):
                student['admission_date'] = None
        except Exception as e:
            print(f"Error converting admission_date: {e}")
            student['admission_date'] = None
    
    # Convert expected_checkout_date to date object if it's a string
    if 'expected_checkout_date' in student and student['expected_checkout_date']:
        try:
            if isinstance(student['expected_checkout_date'], str):
                student['expected_checkout_date'] = datetime.strptime(student['expected_checkout_date'], '%Y-%m-%d').date()
            elif not isinstance(student['expected_checkout_date'], date):
                # If it's not a string or date object, set it to None to avoid comparison issues
                student['expected_checkout_date'] = None
        except Exception as e:
            print(f"Error converting expected_checkout_date: {e}")
            # Handle potential parsing errors if date string format is unexpected
            student['expected_checkout_date'] = None  # Set to None instead of keeping the original value

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
    student = StudentModel.get_student_by_id(student_id)
    if not student:
        flash('Student not found!', 'error')
        return redirect(url_for('student.view_students'))
    
    if request.method == 'POST':
        # Get form data
        student_data = {
            'name': request.form.get('name'),
            'student_id_number': request.form.get('student_id_number'),
            'contact': request.form.get('contact'),
            'email': request.form.get('email'),
            'course': request.form.get('course'),
            'room_id': request.form.get('room_id', type=int, default=None),
            'admission_date': request.form.get('admission_date'),
            'expected_checkout_date': request.form.get('expected_checkout_date', '')
        }
        
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
        errors = validate_student_data(student_data, is_update=True, student_id=student_id)
        if errors:
            for error in errors:
                flash(error, 'error')
            details = StudentModel.get_student_details(student_id)
            rooms = RoomModel.get_available_rooms()
            return render_template(
                'students/edit_student.html', 
                student=student, 
                details=details,
                rooms=rooms
            )
        
        # Store original data for comparison
        original_room_id = student.get('room_id')
        
        # Update student
        try:
            result = StudentModel.update_student(student_id, student_data, details_data)
            
            if result.get('success'):
                # Emit Socket.IO event for real-time updates
                try:
                    from app import socketio
                    
                    # Get updated student info
                    updated_student = StudentModel.get_student_by_id(student_id)
                    
                    event_data = {
                        'student_id': student_id,
                        'name': student_data['name'],
                        'student_id_number': student_data['student_id_number'],
                        'course': student_data['course'],
                        'room_id': student_data.get('room_id'),
                        'previous_room_id': original_room_id,
                        'hostel_id': student.get('hostel_id'),
                        'timestamp': datetime.now().isoformat(),                    'action': 'student_updated',
                        'user': g.user.get('username', 'Unknown') if g.user else 'System'
                    }
                    
                    emit_student_event('student_updated', event_data, student_data.get('hostel_id'))
                    
                    # If room assignment changed, emit additional event
                    if original_room_id != student_data.get('room_id'):
                        room_event_data = {
                            'student_id': student_id,
                            'student_name': student_data['name'],
                            'from_room_id': original_room_id,                            'to_room_id': student_data.get('room_id'),
                            'timestamp': datetime.now().isoformat(),
                            'action': 'student_room_transfer',
                            'user': g.user.get('username', 'Unknown') if g.user else 'System'
                        }
                        emit_student_event('student_room_transfer', room_event_data, student_data.get('hostel_id'))
                    
                except Exception as socket_error:
                    print(f"Socket.IO error in student update: {socket_error}")
                    # Don't let socket errors affect the main functionality
                    pass
                
                flash('Student updated successfully!', 'success')
                return redirect(url_for('student.view_student', student_id=student_id))
            else:
                flash(f'Error updating student: {result.get("error", "Unknown error")}', 'error')
                
        except Exception as e:
            flash(f'Error updating student: {str(e)}', 'error')
    
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
        # Get student info before deletion for Socket.IO event
        student_info = StudentModel.get_student_by_id(student_id)
        
        if not student_info:
            flash('Student not found!', 'error')
            return redirect(url_for('student.view_students'))
        
        # Store student data for the event
        student_dict = dict(student_info)
        
        # Delete the student
        result = StudentModel.delete_student(student_id)
        
        if result.get('success'):            # Emit Socket.IO event for real-time updates
            try:
                from app import socketio
                event_data = {
                    'student_id': student_id,
                    'name': student_dict.get('name'),
                    'student_id_number': student_dict.get('student_id_number'),
                    'course': student_dict.get('course'),
                    'room_id': student_dict.get('room_id'),
                    'hostel_id': student_dict.get('hostel_id'),
                    'timestamp': datetime.now().isoformat(),
                    'action': 'student_deleted',
                    'user': g.user.get('username', 'Unknown') if g.user else 'System'
                }
                
                emit_student_event('student_deleted', event_data, student_dict.get('hostel_id'))
                
            except Exception as socket_error:
                print(f"Socket.IO error in student deletion: {socket_error}")
                # Don't let socket errors affect the main functionality
                pass
            
            flash('Student deleted successfully!', 'success')
        else:
            flash(f'Error deleting student: {result.get("error", "Unknown error")}', 'error')
            
    except Exception as e:
        flash(f'Error deleting student: {str(e)}', 'error')
    
    return redirect(url_for('student.view_students'))

@student_bp.route('/bulk_transfer', methods=['POST'])
def bulk_transfer():
    """Transfer multiple students from one room to another."""
    try:
        source_room_id = request.form.get('source_room_id')
        destination_room_id = request.form.get('destination_room_id')
        student_ids = request.form.getlist('student_ids')
        
        if not destination_room_id:
            flash('Please select a destination room.', 'error')
            return redirect(request.referrer or url_for('room.view_rooms'))
            
        if not student_ids:
            flash('Please select at least one student to transfer.', 'error')
            return redirect(request.referrer or url_for('room.view_rooms'))
        
        # Check if destination room has capacity
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get destination room capacity
            cursor.execute(
                "SELECT capacity, current_occupancy FROM rooms WHERE id = ?",
                (destination_room_id,)
            )
            room_info = cursor.fetchone()
            
            if not room_info:
                flash('Destination room not found.', 'error')
                return redirect(request.referrer or url_for('room.view_rooms'))
            
            capacity, current_occupancy = room_info
            available_space = capacity - current_occupancy
            
            if len(student_ids) > available_space:
                flash(f'Destination room only has {available_space} available space(s).', 'error')
                return redirect(request.referrer or url_for('room.view_rooms'))
            
            # Get student info before transfer for Socket.IO event
            transferred_students = []
            for student_id in student_ids:
                student_info = cursor.execute(
                    "SELECT id, name, student_id_number FROM students WHERE id = ?",
                    (student_id,)
                ).fetchone()
                if student_info:
                    transferred_students.append(dict(student_info))
            
            # Transfer students
            transferred_count = 0
            for student_id in student_ids:
                try:
                    # Update student's room assignment
                    cursor.execute(
                        "UPDATE students SET room_id = ? WHERE id = ?",
                        (destination_room_id, student_id)
                    )
                    transferred_count += 1
                except Exception as e:
                    print(f"Error transferring student {student_id}: {e}")
                    continue
            
            # Update room occupancy counts
            if source_room_id:
                cursor.execute(
                    "UPDATE rooms SET current_occupancy = current_occupancy - ? WHERE id = ?",
                    (transferred_count, source_room_id)
                )
            
            cursor.execute(
                "UPDATE rooms SET current_occupancy = current_occupancy + ? WHERE id = ?",
                (transferred_count, destination_room_id)
            )
            
            conn.commit()
            
            # Emit Socket.IO event for real-time updates
            if transferred_count > 0:
                try:
                    from app import socketio
                    
                    event_data = {
                        'student_ids': student_ids[:transferred_count],
                        'students': transferred_students[:transferred_count],
                        'from_room_id': source_room_id,
                        'to_room_id': destination_room_id,
                        'count': transferred_count,                    'timestamp': datetime.now().isoformat(),
                        'action': 'students_bulk_transfer',
                        'user': g.user.get('username', 'Unknown') if g.user else 'System'
                    }
                    
                    emit_student_event('students_bulk_transfer', event_data, g.user.get('hostel_id') if g.user else None)
                    
                except Exception as socket_error:
                    print(f"Socket.IO error in bulk transfer: {socket_error}")
                    # Don't let socket errors affect the main functionality
                    pass
                
                flash(f'Successfully transferred {transferred_count} student(s).', 'success')
            else:
                flash('No students were transferred.', 'warning')
                
    except Exception as e:
        flash(f'Error during bulk transfer: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('room.view_rooms'))
