"""
File handling utility functions for the Hostel Management System
"""
import os
import uuid
from werkzeug.utils import secure_filename
from pathlib import Path

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_upload_dir():
    """Ensure the upload directory exists."""
    base_path = Path(__file__).parent.parent
    upload_path = base_path / UPLOAD_FOLDER
    
    if not os.path.exists(upload_path):
        os.makedirs(upload_path)
    
    return upload_path

def save_profile_photo(file_storage):
    """
    Save a profile photo from a FileStorage object.
    Returns the relative path to the saved image.
    """
    if not file_storage or file_storage.filename == '':
        return None
    
    if not allowed_file(file_storage.filename):
        return None
    
    # Generate a unique filename
    filename = secure_filename(file_storage.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    
    # Ensure upload directory exists
    upload_path = ensure_upload_dir()
    
    # Save the file
    file_path = os.path.join(upload_path, unique_filename)
    file_storage.save(file_path)
    
    # Return the path relative to the app
    return os.path.join(UPLOAD_FOLDER, unique_filename)

def delete_profile_photo(file_path):
    """Delete a profile photo."""
    if not file_path:
        return False
    
    # Get the absolute path
    base_path = Path(__file__).parent.parent
    abs_path = base_path / file_path
    
    # Check if the file exists and is within the uploads directory
    if os.path.exists(abs_path) and os.path.commonpath([abs_path, ensure_upload_dir()]) == str(ensure_upload_dir()):
        os.remove(abs_path)
        return True
    
    return False
