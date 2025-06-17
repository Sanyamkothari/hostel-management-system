"""
Authentication routes for the Hostel Management System.
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, g
from models.users import User
from models.hostels import Hostel
from functools import wraps

auth_bp = Blueprint('auth', __name__)

# Authentication decorators
def login_required(f):
    """Decorator to ensure user is logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def owner_required(f):
    """Decorator to ensure user is the owner."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != User.ROLE_OWNER:
            flash('Access denied: Owner privileges required', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
        
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"[DEBUG] Login attempt: username={username}")
        
        user = User.get_by_username(username)
        print(f"[DEBUG] User fetched: {user}")
        if user:
            valid = user.check_password(password)
            print(f"[DEBUG] Password check result for user {username}: {valid}")
        if user and user.check_password(password):
            # Store user info in session
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['hostel_id'] = user.hostel_id
            
            # Check if this is the first login (for setup)
            if not session['hostel_id'] and session['role'] == User.ROLE_OWNER:
                hostels = Hostel.get_all_hostels()
                if not hostels:
                    flash('Welcome! Please set up your first hostel.', 'info')
                    return redirect(url_for('owner.setup_hostels'))
            
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            error = 'Invalid username or password'
    
    return render_template('auth/login.html', error=error)

@auth_bp.route('/logout')
def logout():
    """User logout."""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page."""
    user = User.get_by_id(session['user_id'])
    if not user:
        session.clear()
        flash('User not found', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        full_name = request.form['full_name']
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Update full name
        if full_name and full_name != user.full_name:
            user.update(full_name=full_name)
            session['full_name'] = full_name
            flash('Profile updated successfully', 'success')
            
        # Change password if requested
        if current_password and new_password:
            if not user.check_password(current_password):
                flash('Current password is incorrect', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match', 'danger')
            else:
                user.change_password(new_password)
                flash('Password changed successfully', 'success')
                
    return render_template('auth/profile.html', user=user)
