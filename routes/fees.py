"""
Fee management routes for the Hostel Management System
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g, current_app
from models.db import FeeModel, StudentModel
from datetime import date, datetime, timedelta
from utils.date_utils import parse_date, format_date, get_month_range, get_date_intervals
from utils.export import ExportUtility
from utils.user_utils import get_user_attribute
from db_utils import get_db_connection, DatabaseConnection
import json

# Import for Socket.IO real-time updates
try:
    from app import socketio
    from utils.socket_utils import (
        emit_fee_event,
        emit_system_notification
    )
    # Import dashboard update function with update_type support
    from socket_events import emit_dashboard_update
    SOCKETIO_AVAILABLE = True
    DASHBOARD_UPDATES_AVAILABLE = True
except ImportError:
    socketio = None
    SOCKETIO_AVAILABLE = False
    DASHBOARD_UPDATES_AVAILABLE = False

fee_bp = Blueprint('fee', __name__, url_prefix='/fees')

def get_hostel_access_control(request_method='GET', hostel_id_param_name='hostel_id'):
    """
    Utility function to handle hostel access control based on user role.
    Returns a dictionary with hostel_id, current_hostel_name, and hostels_list.
    """
    hostel_id = None
    current_hostel_name = None
    hostels_list = []
    selected_hostel_id = None
    
    user_role = get_user_attribute('role')
    user_hostel_id = get_user_attribute('hostel_id')
    
    if user_role == 'manager':
        # Managers are restricted to their assigned hostel
        hostel_id = user_hostel_id
        from models.hostels import Hostel
        hostel = Hostel.get_by_id(hostel_id)
        if hostel:
            current_hostel_name = hostel.name
    elif user_role == 'owner':
        # Owners need to select a hostel
        from models.hostels import Hostel
        hostels_list = Hostel.get_all_hostels()
        
        # Check if hostel_id is in parameters (selected from dropdown)
        if request_method == 'GET':
            hostel_id_param = request.args.get(hostel_id_param_name)
            if hostel_id_param:
                selected_hostel_id = int(hostel_id_param)
                hostel_id = selected_hostel_id
                hostel = Hostel.get_by_id(hostel_id)
                if hostel:
                    current_hostel_name = hostel.name
    
    return {
        'hostel_id': hostel_id,
        'current_hostel_name': current_hostel_name,
        'hostels_list': hostels_list,
        'selected_hostel_id': selected_hostel_id
    }

@fee_bp.route('/')
def view_fees():
    """View all fees with advanced filtering options."""
    # Get filter parameters
    status_filter = request.args.get('status', '')
    date_range = request.args.get('date_range', '')
    student_name = request.args.get('student_name', '')
    amount_min = request.args.get('amount_min', type=float, default=0)
    amount_max = request.args.get('amount_max', type=float, default=0)
    
    # Get hostel access control
    access_control = get_hostel_access_control()
    hostel_id = access_control['hostel_id']
    current_hostel_name = access_control['current_hostel_name']
    hostels_list = access_control['hostels_list']
    
    # Prepare date filters
    start_date = None
    end_date = None
    
    if date_range:
        # Process predefined date ranges
        if date_range == 'this_month':
            start_date, end_date = get_month_range(date.today())
        elif date_range == 'prev_month':
            prev_month = date.today().replace(day=1) - timedelta(days=1)
            start_date, end_date = get_month_range(prev_month)
        elif date_range == 'next_month':
            next_month = date.today().replace(day=28) + timedelta(days=4)
            next_month = next_month.replace(day=1)
            start_date, end_date = get_month_range(next_month)
        elif date_range == 'overdue':
            end_date = date.today()
    else:
        # Custom date range if provided
        start_date_str = request.args.get('start_date', '')
        end_date_str = request.args.get('end_date', '')
        
        if start_date_str:
            start_date = parse_date(start_date_str)
        if end_date_str:
            end_date = parse_date(end_date_str)
    
    # Prepare filter params
    filter_params = {
        'status': status_filter,
        'student_name': student_name,
        'amount_min': amount_min,
        'amount_max': amount_max,
        'start_date': start_date,
        'end_date': end_date,
        'hostel_id': hostel_id
    }
    
    # Get fees with filters
    fees = FeeModel.get_all_fees_with_students(filter_params, hostel_id)
      # Get data for filter dropdowns
    statuses = FeeModel.get_unique_statuses(hostel_id)
    
    # For passing to template
    search_params = {
        'status': status_filter,
        'student_name': student_name,
        'hostel_id': hostel_id
    }
    
    # Determine the view mode (list, calendar, or card)
    view_mode = request.args.get('view', 'list')
    if view_mode == 'calendar':
        # Prepare calendar data
        calendar_data = prepare_calendar_data(fees)
        
        return render_template(
            'fees/view_fees_calendar.html',
            fees=fees,
            statuses=statuses,
            filter_params=filter_params,
            view_mode=view_mode,
            calendar_data=calendar_data,
            search_params=search_params,
            current_hostel_name=current_hostel_name,
            hostels_list=hostels_list
        )
    else:
        # Standard list or card view
        return render_template(
            'view_fees.html',
            fees=fees,
            statuses=statuses,
            filter_params=filter_params,
            view_mode=view_mode,
            search_params=search_params,
            current_hostel_name=current_hostel_name,
            hostels_list=hostels_list
        )

def prepare_calendar_data(fees):
    """
    Prepare fee data for calendar visualization.
    Groups fees by due date and status.
    """
    calendar_data = {}

    for fee_row in fees:
        # Explicitly create a new dictionary and ensure all values are serializable
        fee = {
            'id': str(fee_row.get('id', '')), # Convert ID to string
            'student_name': str(fee_row.get('student_name', 'N/A')), # Ensure string, provide default
            'amount': float(fee_row.get('amount', 0.0)) if fee_row.get('amount') is not None else 0.0, # Ensure float, handle None
            'due_date': str(fee_row.get('due_date', '')), # Ensure string, provide default
            'paid_date': str(fee_row.get('paid_date', '')), # Ensure string, provide default
            'status': str(fee_row.get('status', 'Unknown')), # Ensure string, provide default
            'hostel_name': str(fee_row.get('hostel_name', '')) # Add hostel name for multi-hostel support
        }

        # Ensure due_date is a string in ISO format for consistency
        due_date_str = fee.get('due_date')
        if not due_date_str:
            continue # Skip if no due date

        # Validate and format date string
        try:
            # Attempt to parse and format to ensure consistent string format
            due_date_obj = date.fromisoformat(due_date_str)
            due_date_iso = due_date_obj.isoformat()
        except ValueError:
            # If the date string is invalid, skip this fee entry
            continue

        if due_date_iso not in calendar_data:
            calendar_data[due_date_iso] = {
                'total': 0,
                'pending': 0,
                'paid': 0,
                'overdue': 0,
                'details': []
            }

        # Update counters - now using consistently formatted due_date_iso
        calendar_data[due_date_iso]['total'] += 1
        today_iso = date.today().isoformat()
        if fee['status'] == 'Pending':
            if due_date_iso < today_iso:
                calendar_data[due_date_iso]['overdue'] += 1
            else:
                calendar_data[due_date_iso]['pending'] += 1
        elif fee['status'] == 'Paid':
            calendar_data[due_date_iso]['paid'] += 1

        # Add details, ensuring all values are serializable strings or numbers
        calendar_data[due_date_iso]['details'].append({
            'id': fee['id'], # Use the explicitly converted string ID
            'student_name': fee['student_name'],
            'amount': fee['amount'], # Use the handled float amount
            'status': fee['status'] # Use the handled string status
        })

    return calendar_data

@fee_bp.route('/add', methods=['GET', 'POST'])
def add_fee():
    """Add a new fee."""
    # Get hostel access control
    access_control = get_hostel_access_control(request_method=request.method)
    hostel_id = access_control['hostel_id']
    current_hostel_name = access_control['current_hostel_name']
    hostels_list = access_control['hostels_list']
    selected_hostel_id = access_control['selected_hostel_id']
    
    if request.method == 'POST' and ('student_id' in request.form):
        fee_data = {
            'student_id': request.form.get('student_id', type=int),
            'amount': request.form.get('amount', type=float),
            'due_date': request.form.get('due_date'),
            'status': request.form.get('status', 'Pending')
        }

        # Add hostel_id based on current user
        if get_user_attribute('role') == 'manager':
            fee_data['hostel_id'] = get_user_attribute('hostel_id')
        elif get_user_attribute('role') == 'owner':
            fee_data['hostel_id'] = request.form.get('hostel_id', type=int)
            if not fee_data['hostel_id']:
                flash('Owner must select a hostel for the new fee.', 'error')
                return render_template('fees/add_fee.html', 
                                      students=[], 
                                      hostels_list=hostels_list,
                                      selected_hostel_id=None,
                                      current_hostel_name=None)
        else:
            flash('Could not determine hostel for the fee. Please login.', 'error')
            return redirect(url_for('auth.login'))
        
        # Validate fee data
        if not fee_data['student_id'] or not fee_data['amount']:
            flash('Student and amount are required!', 'error')
            students = StudentModel.get_all_students(hostel_id=hostel_id)
            return render_template('fees/add_fee.html', 
                                  students=students,
                                  hostels_list=hostels_list, 
                                  selected_hostel_id=selected_hostel_id,
                                  current_hostel_name=current_hostel_name)
        
        if fee_data['amount'] <= 0:
            flash('Amount must be greater than zero!', 'error')
            students = StudentModel.get_all_students(hostel_id=hostel_id)
            return render_template('fees/add_fee.html', 
                                  students=students,
                                  hostels_list=hostels_list, 
                                  selected_hostel_id=selected_hostel_id,
                                  current_hostel_name=current_hostel_name)
          # Check if payment is being recorded directly
        if fee_data['status'] == 'Paid':
            fee_data['paid_date'] = request.form.get('paid_date', date.today().isoformat())
        
        try:
            # Pass hostel_id to FeeModel.add_fee
            result = FeeModel.add_fee(fee_data, hostel_id=fee_data['hostel_id'])
            if result.get('success', False):
                flash('Fee added successfully!', 'success')                # Emit real-time update for fee addition
                try:
                    if SOCKETIO_AVAILABLE:
                        # Get student details for notification
                        student = StudentModel.get_student_by_id(fee_data['student_id'])
                        
                        fee_event_data = {
                            'fee_id': result.get('fee_id'),
                            'student_id': fee_data['student_id'],
                            'student_name': student.get('name', 'Unknown') if student else 'Unknown',
                            'amount': fee_data['amount'],
                            'due_date': fee_data['due_date'],
                            'status': fee_data['status'],
                            'hostel_id': fee_data['hostel_id'],
                            'action': 'fee_added',
                            'user': get_user_attribute('name') or get_user_attribute('username', 'System')
                        }
                        
                        # Use the new socket utility function
                        emit_fee_event('added', fee_event_data, fee_data['hostel_id'])
                        
                        # Trigger dashboard update
                        if DASHBOARD_UPDATES_AVAILABLE:
                            emit_dashboard_update(hostel_id=fee_data['hostel_id'], update_type='fee_added')
                            
                except Exception as socket_error:
                    print(f"Socket.IO emission error in add_fee: {socket_error}")
                
                return redirect(url_for('fee.view_fees'))
            else:
                flash(f'Error adding fee: {result.get("error", "Unknown error")}', 'error')
        except Exception as e:
            flash(f'Error adding fee: {str(e)}', 'error')
    
    # GET request - show the form
    students = StudentModel.get_all_students(hostel_id=hostel_id) if hostel_id else []
    return render_template('fees/add_fee.html', 
                          students=students,
                          hostels_list=hostels_list, 
                          selected_hostel_id=selected_hostel_id,
                          current_hostel_name=current_hostel_name)

@fee_bp.route('/batch/add', methods=['GET', 'POST'])
def add_batch_fees():
    """Add fees for multiple students at once."""
    # Initialize variables
    hostel_id = None
    current_hostel_name = None
    hostels_list = []
    selected_hostel_id = None
    students = []
    
    if hasattr(g, 'user') and g.user:
        if g.user.get('role') == 'manager':
            # Managers are restricted to their assigned hostel
            hostel_id = g.user.hostel_id
            from models.hostels import Hostel
            hostel = Hostel.get_by_id(hostel_id)
            if hostel:
                current_hostel_name = hostel.name
                students = StudentModel.get_all_students(hostel_id=hostel_id)
        elif g.user.get('role') == 'owner':
            # Owners need to select a hostel
            from models.hostels import Hostel
            hostels_list = Hostel.get_all_hostels()
            
            # Check if hostel_id is in GET parameters (selected from dropdown)
            if request.method == 'GET':
                hostel_id_param = request.args.get('hostel_id')
                if hostel_id_param:
                    selected_hostel_id = int(hostel_id_param)
                    hostel_id = selected_hostel_id
                    hostel = Hostel.get_by_id(hostel_id)
                    if hostel:
                        current_hostel_name = hostel.name
                        students = StudentModel.get_all_students(hostel_id=hostel_id)
            # Check if hostel_id is in POST data
            elif request.method == 'POST':
                hostel_id_param = request.form.get('hostel_id')
                if hostel_id_param:
                    selected_hostel_id = int(hostel_id_param)
                    hostel_id = selected_hostel_id
                    hostel = Hostel.get_by_id(hostel_id)
                    if hostel:
                        current_hostel_name = hostel.name
                        students = StudentModel.get_all_students(hostel_id=hostel_id)
    
    if request.method == 'POST' and 'amount' in request.form:
        student_ids = request.form.getlist('student_ids')
        amount = request.form.get('amount', type=float)
        due_date = request.form.get('due_date')
        description = request.form.get('description', '')

        # Validate that hostel_id is set
        if not hostel_id:
            flash('Owner must select a hostel for the batch fees.', 'error')
            return render_template('fees/add_batch_fees.html', 
                                  students=[],
                                  hostels_list=hostels_list, 
                                  selected_hostel_id=None,
                                  current_hostel_name=None)

        # Validate inputs        if not student_ids:
            flash('Please select at least one student!', 'error')
            return render_template('fees/add_batch_fees.html', 
                                  students=students,
                                  hostels_list=hostels_list, 
                                  selected_hostel_id=selected_hostel_id,
                                  current_hostel_name=current_hostel_name)
        
        if not amount or amount <= 0:
            flash('Please enter a valid amount!', 'error')
            return render_template('fees/add_batch_fees.html', 
                                  students=students,
                                  hostels_list=hostels_list, 
                                  selected_hostel_id=selected_hostel_id,
                                  current_hostel_name=current_hostel_name)
        
        # Add fees for each selected student
        success_count = 0
        added_fees = []
        for student_id in student_ids:
            try:
                result = FeeModel.add_fee({
                    'student_id': int(student_id),
                    'amount': amount,
                    'due_date': due_date,
                    'status': 'Pending',
                    'description': description                }, hostel_id=hostel_id)
                
                if result.get('success', False):
                    success_count += 1
                    student = StudentModel.get_student_by_id(int(student_id))
                    if student:
                        added_fees.append({
                            'fee_id': result.get('fee_id'),
                            'student_id': int(student_id),
                            'student_name': student.get('name', 'Unknown'),
                            'amount': amount
                        })
                else:
                    flash(f'Error adding fee for student ID {student_id}: {result.get("error", "Unknown error")}', 'error')
            except Exception as e:
                flash(f'Error adding fee for student ID {student_id}: {str(e)}', 'error')
        
        if success_count > 0:
            flash(f'Successfully added fees for {success_count} students!', 'success')
            
            # Emit real-time update for batch fee addition
            try:
                if socketio and added_fees:
                    emit_fee_event('fees_batch_added', {
                        'count': success_count,
                        'amount': amount,
                        'due_date': due_date,
                        'hostel_id': hostel_id,
                        'fees': added_fees,
                        'timestamp': datetime.now().isoformat(),
                        'action': 'fees_batch_added',
                        'user': get_user_attribute('name') or get_user_attribute('username', 'System')
                    }, hostel_id)
                    
                    # Trigger dashboard update
                    if DASHBOARD_UPDATES_AVAILABLE:
                        emit_dashboard_update(hostel_id=hostel_id, update_type='fees_batch_added')
                        
            except Exception as socket_error:
                print(f"Socket.IO emission error in add_batch_fees: {socket_error}")
            
            return redirect(url_for('fee.view_fees'))
    
    # GET request - show the form
    return render_template('fees/add_batch_fees.html', 
                          students=students,
                          hostels_list=hostels_list, 
                          selected_hostel_id=selected_hostel_id,
                          current_hostel_name=current_hostel_name)

@fee_bp.route('/<int:fee_id>/mark_paid', methods=['POST'])
def mark_fee_paid(fee_id):
    """Mark a fee as paid."""
    paid_date = request.form.get('paid_date', date.today().isoformat())
    
    # Determine hostel_id based on user role
    hostel_id = get_user_attribute('hostel_id') if get_user_attribute('role') == 'manager' else None
    
    try:
        result = FeeModel.mark_fee_paid(fee_id, hostel_id=hostel_id)
        if result.get('success'):
            flash('Fee marked as paid successfully!', 'success')
            
            # Emit real-time update for fee payment
            try:
                from app import socketio
                # Get fee details for notification
                conn = get_db_connection()
                fee_details = conn.execute(
                    "SELECT f.amount, s.name as student_name, f.hostel_id FROM fees f JOIN students s ON f.student_id = s.id WHERE f.id = ?", 
                    (fee_id,)
                ).fetchone()
                conn.close()
                
                if fee_details and SOCKETIO_AVAILABLE:
                    fee_event_data = {
                        'fee_id': fee_id,
                        'amount': fee_details['amount'],
                        'student_name': fee_details['student_name'],
                        'hostel_id': fee_details['hostel_id']
                    }
                    
                    # Use the new socket utility function
                    emit_fee_event('paid', fee_event_data, fee_details['hostel_id'])
                    
                    # Trigger dashboard update
                    emit_dashboard_update(hostel_id=fee_details['hostel_id'])
                        
            except Exception as socket_error:
                print(f"Socket.IO emission error: {socket_error}")
                
        else:
            flash(f'Error marking fee as paid: {result.get("error", "Unknown error")}', 'error')
    except Exception as e:
        flash(f'Error marking fee as paid: {str(e)}', 'error')
    
    # Determine where to redirect based on the source
    redirect_url = request.form.get('redirect_url', url_for('fee.view_fees'))
    return redirect(redirect_url)

@fee_bp.route('/<int:fee_id>/delete', methods=['POST'])
def delete_fee(fee_id):
    """Delete a fee."""
    # Determine hostel_id based on user role
    hostel_id = get_user_attribute('hostel_id') if get_user_attribute('role') == 'manager' else None
    
    try:
        # First check if the fee exists and belongs to the correct hostel for managers
        fee = FeeModel.get_fee_by_id(fee_id, hostel_id)
        if not fee:
            flash('Fee record not found or you do not have permission to delete it.', 'error')
            return redirect(url_for('fee.view_fees'))
        
        # Store fee data for Socket.IO event before deletion
        fee_data_for_event = {
            'fee_id': fee_id,
            'student_id': fee.get('student_id'),
            'student_name': fee.get('student_name', 'Unknown'),
            'amount': fee.get('amount'),
            'due_date': fee.get('due_date'),
            'status': fee.get('status'),
            'hostel_id': fee.get('hostel_id')
        }
          # Now we can safely delete it
        conn = get_db_connection()
        try:
            # For managers, include hostel_id in the WHERE clause
            if hostel_id is not None:
                conn.execute('DELETE FROM fees WHERE id = ? AND hostel_id = ?', (fee_id, hostel_id))
            else:
                # For owners, can delete any fee
                conn.execute('DELETE FROM fees WHERE id = ?', (fee_id,))
                
            conn.commit()
            flash('Fee deleted successfully!', 'success')
            
            # Emit real-time update for fee deletion
            try:
                if socketio:
                    emit_fee_event('fee_deleted', {
                        **fee_data_for_event,
                        'timestamp': datetime.now().isoformat(),
                        'action': 'fee_deleted',
                        'user': get_user_attribute('name') or get_user_attribute('username', 'System')
                    }, fee_data_for_event['hostel_id'])
                    
                    # Trigger dashboard update
                    if DASHBOARD_UPDATES_AVAILABLE:
                        emit_dashboard_update(hostel_id=fee_data_for_event['hostel_id'], update_type='fee_deleted')
                        
            except Exception as socket_error:
                print(f"Socket.IO emission error in delete_fee: {socket_error}")
                
        except Exception as e:
            conn.rollback()
            flash(f'Error deleting fee: {str(e)}', 'error')
        finally:
            conn.close()
    except Exception as e:
        flash(f'Error deleting fee: {str(e)}', 'error')
    
    return redirect(url_for('fee.view_fees'))

@fee_bp.route('/reminders')
def fee_reminders():
    """View and manage fee payment reminders."""
    # Determine hostel_id based on user role
    hostel_id = None
    current_hostel_name = None
    hostels_list = []
    
    if hasattr(g, 'user') and g.user:
        if g.user.get('role') == 'manager':
            # Managers are restricted to their hostel
            hostel_id = g.user.hostel_id
            from models.hostels import Hostel
            hostel = Hostel.get_by_id(hostel_id)
            if hostel:
                current_hostel_name = hostel.name
        elif g.user.get('role') == 'owner':
            # Owners can filter by hostel
            from models.hostels import Hostel
            hostels_list = Hostel.get_all_hostels()
            hostel_id_param = request.args.get('hostel_id')
            if hostel_id_param:
                hostel_id = int(hostel_id_param)
                hostel = Hostel.get_by_id(hostel_id)
                if hostel:
                    current_hostel_name = hostel.name
    
    # Get upcoming and overdue fees with hostel filtering
    upcoming_fees = FeeModel.get_upcoming_fees(days=7, hostel_id=hostel_id)
    overdue_fees = FeeModel.get_overdue_fees(hostel_id=hostel_id)
    
    return render_template(
        'fees/fee_reminders.html',
        upcoming_fees=upcoming_fees,
        overdue_fees=overdue_fees,
        current_hostel_name=current_hostel_name,
        hostels_list=hostels_list
    )

@fee_bp.route('/reports')
def fee_reports():
    """Generate fee reports."""
    # Determine hostel_id based on user role
    hostel_id = None
    current_hostel_name = None
    hostels_list = []
    
    if hasattr(g, 'user') and g.user:
        if g.user.get('role') == 'manager':
            # Managers are restricted to their hostel
            hostel_id = g.user.hostel_id
            from models.hostels import Hostel
            hostel = Hostel.get_by_id(hostel_id)
            if hostel:
                current_hostel_name = hostel.name
        elif g.user.get('role') == 'owner':
            # Owners can filter by hostel
            from models.hostels import Hostel
            hostels_list = Hostel.get_all_hostels()
            hostel_id_param = request.args.get('hostel_id')
            if hostel_id_param:
                hostel_id = int(hostel_id_param)
                hostel = Hostel.get_by_id(hostel_id)
                if hostel:
                    current_hostel_name = hostel.name
    
    # Get report parameters
    period = request.args.get('period', 'monthly')
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int) if period == 'monthly' else None
    
    # Generate report data with hostel filtering
    report_data = FeeModel.get_fee_report(period=period, year=year, month=month, hostel_id=hostel_id)
    
    return render_template(
        'fees/fee_reports.html',
        report_data=report_data,
        period=period,
        year=year,
        month=month,
        current_hostel_name=current_hostel_name,
        hostels_list=hostels_list
    )

@fee_bp.route('/export')
def export_fees():
    """Export fees data to CSV or PDF."""
    from utils.export import ExportUtility
    
    # Get filter parameters - same as view_fees route
    status_filter = request.args.get('status', '')
    date_range = request.args.get('date_range', '')
    student_name = request.args.get('student_name', '')
    amount_min = request.args.get('amount_min', type=float, default=0)
    amount_max = request.args.get('amount_max', type=float, default=0)
    
    # Get hostel filter parameter (for owner)
    hostel_id = None
    current_hostel_name = None
    
    if hasattr(g, 'user') and g.user:
        if g.user.get('role') == 'manager':
            # Managers are restricted to their hostel
            hostel_id = g.user.hostel_id
            from models.hostels import Hostel
            hostel = Hostel.get_by_id(hostel_id)
            if hostel:
                current_hostel_name = hostel.name
        elif g.user.get('role') == 'owner':
            # Owners can filter by hostel
            from models.hostels import Hostel
            hostel_id_param = request.args.get('hostel_id')
            if hostel_id_param:
                hostel_id = int(hostel_id_param)
                hostel = Hostel.get_by_id(hostel_id)
                if hostel:
                    current_hostel_name = hostel.name
    
    # Prepare date filters
    start_date = None
    end_date = None
    
    if date_range:
        # Process predefined date ranges
        if date_range == 'this_month':
            start_date, end_date = get_month_range(date.today())
        elif date_range == 'prev_month':
            prev_month = date.today().replace(day=1) - timedelta(days=1)
            start_date, end_date = get_month_range(prev_month)
        elif date_range == 'next_month':
            next_month = date.today().replace(day=28) + timedelta(days=4)
            next_month = next_month.replace(day=1)
            start_date, end_date = get_month_range(next_month)
        elif date_range == 'overdue':
            end_date = date.today()
    else:
        # Custom date range if provided
        start_date_str = request.args.get('start_date', '')
        end_date_str = request.args.get('end_date', '')
        
        if start_date_str:
            start_date = parse_date(start_date_str)
        if end_date_str:
            end_date = parse_date(end_date_str)
    
    # Prepare filter params
    filter_params = {
        'status': status_filter,
        'student_name': student_name,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    if amount_min > 0:
        filter_params['amount_min'] = amount_min
    if amount_max > 0:
        filter_params['amount_max'] = amount_max
    
    # Get fees data with the applied filters including hostel_id
    fees = FeeModel.get_all_fees_with_students(filter_params, hostel_id)
    
    # Convert SQLite Row objects to dictionaries
    fee_data = []
    for fee in fees:
        fee_dict = dict(fee) if isinstance(fee, dict) else fee  # Ensure fee is a dictionary
        fee_data.append({
            'ID': fee_dict.get('id', ''),
            'Student Name': fee_dict.get('student_name', ''),
            'Amount': f"${fee_dict.get('amount', 0)}",
            'Due Date': fee_dict.get('due_date', ''),
            'Paid Date': fee_dict.get('paid_date', '') or '-',
            'Status': fee_dict.get('status', ''),
            'Hostel': fee_dict.get('hostel_name', '') or current_hostel_name or 'Unknown'
        })
    
    # Determine export format
    export_format = request.args.get('format', 'csv').lower()
    
    # Prepare file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if export_format == 'pdf':
        # Determine a title based on filters
        title = "Fee Report"
        if status_filter:
            title += f" - {status_filter} Fees"
        elif date_range:
            title += f" - {date_range.replace('_', ' ').title()} Fees"
        
        # Add hostel name to title if available
        if current_hostel_name:
            title += f" - {current_hostel_name}"
        
        # Generate description text
        description = "Fee report generated on " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if start_date and end_date:
            description += f"\nPeriod: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elif start_date:
            description += f"\nFrom: {start_date.strftime('%Y-%m-%d')}"
        elif end_date:
            description += f"\nUntil: {end_date.strftime('%Y-%m-%d')}"
        
        if student_name:
            description += f"\nStudent: {student_name}"
        
        # Column headers
        headers = ['ID', 'Student Name', 'Amount', 'Due Date', 'Paid Date', 'Status', 'Hostel']
        
        # Generate PDF
        return ExportUtility.export_to_pdf(
            data=fee_data,
            filename=f"fees_report_{timestamp}.pdf",
            title=title,
            description=description,
            headers=headers
        )
    else:  # Default to CSV
        headers = ['ID', 'Student Name', 'Amount', 'Due Date', 'Paid Date', 'Status', 'Hostel']
        return ExportUtility.export_to_csv(
            data=fee_data,
            filename=f"fees_export_{timestamp}.csv",
            headers=headers
        )

@fee_bp.route('/send_reminders', methods=['POST'])
def send_fee_reminders():
    """Send email reminders for pending fees."""
    from utils.email_notifier import EmailNotifier
    
    # Determine hostel_id based on user role
    hostel_id = None
    if hasattr(g, 'user') and g.user:
        if g.user.get('role') == 'manager':
            hostel_id = g.user.hostel_id
        elif g.user.get('role') == 'owner':
            # Owners can send reminders for a specific hostel if selected
            hostel_id_param = request.form.get('hostel_id')
            if hostel_id_param:
                hostel_id = int(hostel_id_param)
    
    # Default to 3 days before due date for upcoming reminders
    days_threshold = request.form.get('days_threshold', type=int, default=3)
    
    # Send the reminders with hostel filtering
    results = EmailNotifier.send_bulk_fee_reminders(days_threshold=days_threshold, hostel_id=hostel_id)
    
    # Flash message with results
    flash(f"Reminders processed: {results['sent']} sent, {results['failed']} failed, {results['skipped']} skipped (no email)", 
          'info' if results['sent'] > 0 else 'warning')
    
    # Redirect back to the fees page
    return redirect(url_for('fee.view_fees'))

@fee_bp.route('/fees/calendar')
def view_fees_calendar():
    # Determine hostel_id based on user role
    hostel_id = None
    current_hostel_name = None
    hostels_list = []
    
    if hasattr(g, 'user') and g.user:
        if g.user.get('role') == 'manager':
            # Managers are restricted to their hostel
            hostel_id = g.user.hostel_id
            from models.hostels import Hostel
            hostel = Hostel.get_by_id(hostel_id)
            if hostel:
                current_hostel_name = hostel.name
        elif g.user.get('role') == 'owner':
            # Owners can filter by hostel
            from models.hostels import Hostel
            hostels_list = Hostel.get_all_hostels()
            hostel_id_param = request.args.get('hostel_id')
            if hostel_id_param:
                hostel_id = int(hostel_id_param)
                hostel = Hostel.get_by_id(hostel_id)
                if hostel:
                    current_hostel_name = hostel.name
    
    with DatabaseConnection() as conn:
        # Build query with hostel filter if needed
        query = """
            SELECT f.*, s.name as student_name, r.room_number, h.name as hostel_name
            FROM fees f
            LEFT JOIN students s ON f.student_id = s.id
            LEFT JOIN rooms r ON s.room_id = r.id
            LEFT JOIN hostels h ON f.hostel_id = h.id
        """
        
        params = []
        if hostel_id:
            query += " WHERE f.hostel_id = ?"
            params.append(hostel_id)
        
        query += " ORDER BY f.due_date"
        
        # Get all fees with student, room, and hostel information
        fees_data = conn.execute(query, params).fetchall()

        # Process the fees data for the calendar
        calendar_data = []
        for fee in fees_data:
            fee_dict = dict(fee)
            # Convert dates to ISO format for JavaScript
            if fee_dict['due_date']:
                fee_dict['due_date'] = date.fromisoformat(fee_dict['due_date']).isoformat()
            if fee_dict['paid_date']:
                fee_dict['paid_date'] = date.fromisoformat(fee_dict['paid_date']).isoformat()
            calendar_data.append(fee_dict)

        # Ensure calendar_data is always defined
        if not calendar_data:
            calendar_data = []  # Set to empty list if no fees

        filter_params = {
            'date_range': '',
            'start_date': '',
            'end_date': '',
            'status': '',
            'student_name': ''
        }
        
        # For passing to template
        search_params = {
            'hostel_id': hostel_id
        }
        
        # Convert calendar_data to a JSON string
        calendar_data_json = json.dumps(calendar_data)

        return render_template('fees/view_fees_calendar.html', 
                              fees=calendar_data, # Keep for potential other uses in the template
                              calendar_data_json=calendar_data_json, # Pass JSON string
                              filter_params=filter_params,
                              statuses=['Pending', 'Paid', 'Overdue'],
                              search_params=search_params,
                              current_hostel_name=current_hostel_name,
                              hostels_list=hostels_list)

@fee_bp.route('/<int:fee_id>/edit', methods=['GET', 'POST'])
def edit_fee(fee_id):
    from models.db import FeeModel, StudentModel
    from models.hostels import Hostel
    
    # Determine hostel_id based on user role
    hostel_id = None
    if hasattr(g, 'user') and g.user:
        if g.user.get('role') == 'manager':
            hostel_id = g.user.hostel_id
    
    fee = FeeModel.get_fee_by_id(fee_id, hostel_id)
    if not fee:
        flash('Fee record not found.', 'error')
        return redirect(url_for('fee.view_fees'))
      # Get hostel name for display
    current_hostel_name = None
    if fee.get('hostel_id'):
        hostel = Hostel.get_by_id(fee['hostel_id'])
        if hostel:
            fee['hostel_name'] = hostel.name
            current_hostel_name = hostel.name
    
    if request.method == 'POST':
        amount = request.form.get('amount', type=float)
        due_date = request.form.get('due_date')
        status = request.form.get('status', 'Pending')
        paid_date = request.form.get('paid_date') if status == 'Paid' else None
        
        # Store original fee data for comparison
        original_fee = dict(fee)
        
        try:
            FeeModel.update_fee(fee_id, amount, due_date, status, paid_date, hostel_id)
            flash('Fee record updated successfully!', 'success')
            
            # Emit real-time update for fee edit
            try:
                if socketio:
                    # Get updated fee data
                    updated_fee = FeeModel.get_fee_by_id(fee_id, hostel_id)
                    
                    emit_fee_event('fee_updated', {
                        'fee_id': fee_id,
                        'student_id': updated_fee.get('student_id') if updated_fee else original_fee.get('student_id'),
                        'student_name': updated_fee.get('student_name') if updated_fee else original_fee.get('student_name', 'Unknown'),
                        'amount': amount,
                        'due_date': due_date,
                        'status': status,
                        'paid_date': paid_date,
                        'hostel_id': updated_fee.get('hostel_id') if updated_fee else original_fee.get('hostel_id'),
                        'previous_amount': original_fee.get('amount'),
                        'previous_status': original_fee.get('status'),                        'timestamp': datetime.now().isoformat(),
                        'action': 'fee_updated',
                        'user': get_user_attribute('name') or get_user_attribute('username', 'System')
                    }, updated_fee.get('hostel_id') if updated_fee else original_fee.get('hostel_id'))
                    
                    # Trigger dashboard update
                    if DASHBOARD_UPDATES_AVAILABLE:
                        emit_dashboard_update(hostel_id=updated_fee.get('hostel_id') if updated_fee else original_fee.get('hostel_id'), update_type='fee_updated')
                        
            except Exception as socket_error:
                print(f"Socket.IO emission error in edit_fee: {socket_error}")
            
            return redirect(url_for('fee.view_fees'))
        except Exception as e:
            flash(f'Error updating fee: {e}', 'error')
    
    students = StudentModel.get_all_students(hostel_id=hostel_id)
    return render_template('fees/edit_fee.html', 
                          fee=fee, 
                          students=students,
                          current_hostel_name=current_hostel_name)
