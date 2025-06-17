"""
Owner routes for managing mul      # Get recent activity for owner dashboard with hostel names
    with get_db_connection() as conn:
        recent_activity = get_recent_activity(conn, limit=10, include_hostel_names=True) Get recent activity for owner dashboard with hostel names
    with get_db_connection() as conn:
        recent_activity = get_recent_activity(conn, limit=10, include_hostel_names=True)le hostels.
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, g
from models.users import User
from models.hostels import Hostel
from models.db import get_db_connection
from utils.dashboard import get_recent_activity
from routes.auth import owner_required, login_required

owner_bp = Blueprint('owner', __name__, url_prefix='/owner')

@owner_bp.route('/dashboard')
@login_required
@owner_required
def dashboard():
    """Owner dashboard showing aggregated data from all hostels."""
    # Get all hostels
    hostels = Hostel.get_all_hostels()
    
    # Get statistics for each hostel
    hostels_data = []
    
    for hostel in hostels:
        stats = Hostel.get_dashboard_stats(hostel.id)
        hostels_data.append({
            'id': hostel.id,
            'name': hostel.name,
            'address': hostel.address,
            'stats': stats
        })
      # Get overall statistics
    overall_stats = Hostel.get_dashboard_stats()
      # Get recent activity for owner dashboard with hostel names
    with get_db_connection() as conn:
        recent_activity = get_recent_activity(conn, limit=10, include_hostel_names=True)
    
    return render_template('owner/dashboard.html', 
                          hostels=hostels_data,
                          overall_stats=overall_stats,
                          recent_activity=recent_activity)

@owner_bp.route('/hostels')
@login_required
@owner_required
def manage_hostels():
    """List and manage all hostels."""
    hostels = Hostel.get_all_hostels()
    return render_template('owner/hostels.html', hostels=hostels)

@owner_bp.route('/hostels/add', methods=['GET', 'POST'])
@login_required
@owner_required
def add_hostel():
    """Add a new hostel."""
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        contact_number = request.form['contact_number']
        
        if not name or not address:
            flash('Name and address are required', 'danger')
        else:
            hostel_id = Hostel.create_hostel(name, address, contact_number)
            flash(f'Hostel "{name}" created successfully', 'success')
            return redirect(url_for('owner.manage_hostels'))
    
    return render_template('owner/hostel_form.html')

@owner_bp.route('/hostels/edit/<int:hostel_id>', methods=['GET', 'POST'])
@login_required
@owner_required
def edit_hostel(hostel_id):
    """Edit an existing hostel."""
    hostel = Hostel.get_by_id(hostel_id)
    if not hostel:
        flash('Hostel not found', 'danger')
        return redirect(url_for('owner.manage_hostels'))
    
    if request.method == 'POST':
        hostel.name = request.form['name']
        hostel.address = request.form['address']
        hostel.contact_number = request.form['contact_number']
        
        if not hostel.name or not hostel.address:
            flash('Name and address are required', 'danger')
        else:
            hostel.update()
            flash(f'Hostel "{hostel.name}" updated successfully', 'success')
            return redirect(url_for('owner.manage_hostels'))
    
    return render_template('owner/hostel_form.html', hostel=hostel)

@owner_bp.route('/hostels/delete/<int:hostel_id>', methods=['POST'])
@login_required
@owner_required
def delete_hostel(hostel_id):
    """Delete a hostel."""
    hostel = Hostel.get_by_id(hostel_id)
    if not hostel:
        flash('Hostel not found', 'danger')
    else:
        success, message = hostel.delete()
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    
    return redirect(url_for('owner.manage_hostels'))

@owner_bp.route('/managers')
@login_required
@owner_required
def manage_managers():
    """List and manage hostel managers."""
    managers = User.get_all_managers()
    hostels = Hostel.get_all_hostels()
    return render_template('owner/managers.html', managers=managers, hostels=hostels)

@owner_bp.route('/managers/add', methods=['GET', 'POST'])
@login_required
@owner_required
def add_manager():
    """Add a new hostel manager."""
    hostels = Hostel.get_all_hostels()
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        hostel_id = request.form['hostel_id'] or None
        
        if not username or not password:
            flash('Username and password are required', 'danger')
        elif User.get_by_username(username):
            flash('Username already exists', 'danger')
        else:
            User.create_user(username, password, full_name, User.ROLE_MANAGER, hostel_id)
            flash(f'Manager "{username}" created successfully', 'success')
            return redirect(url_for('owner.manage_managers'))
    
    return render_template('owner/manager_form.html', hostels=hostels)

@owner_bp.route('/managers/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@owner_required
def edit_manager(user_id):
    """Edit an existing hostel manager."""
    user = User.get_by_id(user_id)
    if not user or user.role != User.ROLE_MANAGER:
        flash('Manager not found', 'danger')
        return redirect(url_for('owner.manage_managers'))
    
    hostels = Hostel.get_all_hostels()
    
    if request.method == 'POST':
        full_name = request.form['full_name']
        hostel_id = request.form['hostel_id'] or None
        new_password = request.form.get('new_password')
        
        # Update user details
        user.update(full_name=full_name, hostel_id=hostel_id)
        
        # Update password if provided
        if new_password:
            user.change_password(new_password)
            flash('Password updated', 'success')
            
        flash(f'Manager "{user.username}" updated successfully', 'success')
        return redirect(url_for('owner.manage_managers'))
    
    return render_template('owner/manager_form.html', user=user, hostels=hostels)

@owner_bp.route('/setup_hostels', methods=['GET', 'POST'])
@login_required
@owner_required
def setup_hostels():
    """Initial setup page for creating hostels."""
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        contact_number = request.form['contact_number']
        
        if not name or not address:
            flash('Name and address are required', 'danger')
        else:
            hostel_id = Hostel.create_hostel(name, address, contact_number)
            flash(f'Hostel "{name}" created successfully! You can now add more hostels or continue to the dashboard.', 'success')
            return redirect(url_for('owner.dashboard'))
    
    return render_template('owner/setup_hostels.html')
