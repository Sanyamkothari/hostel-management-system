"""
Function to apply hostel filtering to queries based on user role.
"""
from flask import g, session, redirect, url_for, flash, has_request_context
from functools import wraps

def login_required(f):
    """Decorator to ensure user is logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if has_request_context() and 'user_id' not in session:
            flash('Please log in first', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def filter_by_hostel(model_class, method_name, hostel_id_param=None):
    """
    Decorator to modify model methods to filter by hostel_id based on user role.
    
    Args:
        model_class: The model class being modified
        method_name: The name of the static method being decorated
        hostel_id_param: Optional name of the hostel_id parameter in the method
    
    Returns:
        Decorated method that filters by hostel_id when appropriate
    """
    original_method = getattr(model_class, method_name)
    
    @wraps(original_method)
    def decorated_method(*args, **kwargs):
        # If user is a manager, force filtering by their assigned hostel_id
        if session.get('role') == 'manager' and session.get('hostel_id'):
            if hostel_id_param:
                kwargs[hostel_id_param] = session.get('hostel_id')
            else:
                # If no specific parameter name, assume first parameter is hostel_id
                args = (session.get('hostel_id'),) + args[1:]
                
        return original_method(*args, **kwargs)
    
    # Replace the original method with the decorated one
    setattr(model_class, method_name, decorated_method)
    return decorated_method

def apply_hostel_filters():
    """Apply hostel filtering to all relevant model methods."""
    from models.db import StudentModel, RoomModel, FeeModel, ComplaintModel
    
    # Filter Student methods
    filter_by_hostel(StudentModel, 'get_all_students', 'hostel_id')
    filter_by_hostel(StudentModel, 'get_student_by_id')
      # Filter Room methods
    filter_by_hostel(RoomModel, 'get_all_rooms', 'hostel_id')
    filter_by_hostel(RoomModel, 'get_room_by_id')
      # Filter Fee methods
    filter_by_hostel(FeeModel, 'get_all_fees', 'hostel_id')
    filter_by_hostel(FeeModel, 'get_fee_by_id')
      # Filter Complaint methods
    filter_by_hostel(ComplaintModel, 'get_all_complaints', 'hostel_id')
    filter_by_hostel(ComplaintModel, 'get_complaint_by_id')
