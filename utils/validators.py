"""
Validation utility functions for the Hostel Management System
"""
import re
from datetime import datetime

def validate_email(email):
    """Validate an email address format."""
    if not email:
        return False
    
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone):
    """Validate a phone number format."""
    if not phone:
        return False
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
    
    # Check if it's a valid numeric phone (simple check)
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15

def validate_date_format(date_str, formats=None):
    """Validate date string format."""
    if not date_str:
        return False
    
    if not formats:
        formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']
    
    for fmt in formats:
        try:
            datetime.strptime(date_str, fmt)
            return True
        except ValueError:
            continue
    
    return False

def validate_student_data(data, is_update=False, student_id=None):
    """Validate student data. Returns a list of error messages."""
    errors = []
    
    # Required fields
    if not data.get('name'):
        errors.append('Student name is required')
    
    # Email validation
    if data.get('email'):
        if not validate_email(data['email']):
            errors.append('Invalid email format')
    else:
        errors.append('Email is required')
    
    # Phone validation
    if data.get('contact'):
        if not validate_phone(data['contact']):
            errors.append('Invalid phone number format')
    else:
        errors.append('Contact number is required')
    
    # Course validation
    if not data.get('course'):
        errors.append('Course is required')
    
    # Date validations
    if data.get('admission_date') and not validate_date_format(data['admission_date']):
        errors.append('Invalid admission date format')
    
    if data.get('expected_checkout_date') and not validate_date_format(data['expected_checkout_date']):
        errors.append('Invalid expected checkout date format')
    
    return errors

def validate_room_data(data):
    """Validate room data. Returns a list of error messages."""
    errors = []
    
    # Required fields
    if not data.get('room_number'):
        errors.append('Room number is required')
    
    # Capacity validation
    try:
        capacity = int(data.get('capacity', 0))
        if capacity <= 0:
            errors.append('Capacity must be greater than zero')
    except ValueError:
        errors.append('Capacity must be a number')
    
    return errors

def validate_fee_data(data):
    """Validate fee data. Returns a list of error messages."""
    errors = []
    
    # Required fields
    if not data.get('student_id'):
        errors.append('Student must be selected')
    
    # Amount validation
    try:
        amount = float(data.get('amount', 0))
        if amount <= 0:
            errors.append('Amount must be greater than zero')
    except ValueError:
        errors.append('Amount must be a number')
    
    # Date validations
    if data.get('due_date') and not validate_date_format(data['due_date']):
        errors.append('Invalid due date format')
    
    if data.get('paid_date') and not validate_date_format(data['paid_date']):
        errors.append('Invalid payment date format')
    
    return errors
