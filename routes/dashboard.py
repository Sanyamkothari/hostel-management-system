"""
Dashboard and index routes for the Hostel Management System
"""
from flask import Blueprint, render_template, request, g, flash, redirect, url_for
from datetime import date
from models.db import StudentModel, RoomModel, FeeModel, ExpenseModel, get_db_connection
from utils.dashboard import get_recent_activity

# Socket.IO imports with error handling
try:
    from flask_socketio import emit
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    print("Warning: Flask-SocketIO not available for dashboard real-time updates")

dashboard_bp = Blueprint('dashboard', __name__)

def emit_dashboard_update(hostel_id=None, update_type='general'):
    """
    Emit dashboard statistics update via Socket.IO
    """
    if not SOCKETIO_AVAILABLE:
        return
    
    try:
        # Get updated statistics
        stats = get_dashboard_statistics(hostel_id)
          # Emit dashboard update event
        emit('dashboard_stats_updated', {
            'stats': stats,
            'hostel_id': hostel_id,
            'update_type': update_type,
            'timestamp': date.today().isoformat()
        }, to=f'hostel_{hostel_id}' if hostel_id else None, broadcast=True)
        
    except Exception as e:
        print(f"Error emitting dashboard update: {e}")

def get_dashboard_statistics(hostel_id=None):
    """
    Get dashboard statistics for Socket.IO updates
    """
    try:
        # Basic stats - filtered by hostel if specified
        num_students = StudentModel.count_all_students(hostel_id=hostel_id)
        rooms_stats = RoomModel.get_room_statistics(hostel_id=hostel_id)
        fee_stats = FeeModel.get_fee_statistics(hostel_id=hostel_id)
        
        # Get expense statistics for current month
        today = date.today()
        expense_stats = ExpenseModel.get_expense_statistics(
            hostel_id=hostel_id,
            period='monthly',
            year=today.year,
            month=today.month
        )
        
        # Calculate total capacity and occupancy percentage
        total_capacity = rooms_stats['total_capacity']
        current_occupancy = rooms_stats['current_occupancy']
        occupancy_percentage = (current_occupancy / total_capacity * 100) if total_capacity > 0 else 0
        
        return {
            'students': num_students,
            'rooms': rooms_stats['total_rooms'],
            'available_rooms': rooms_stats['available_rooms'],
            'occupied_rooms': rooms_stats['occupied_rooms'],
            'maintenance_rooms': rooms_stats['maintenance_rooms'],
            'total_capacity': total_capacity,
            'current_occupancy': current_occupancy,
            'occupancy_percentage': occupancy_percentage,
            'pending_fees': fee_stats['pending_count'],
            'overdue_fees': fee_stats['overdue_count'],
            'pending_fees_amount': fee_stats['pending_amount'],
            'overdue_fees_amount': fee_stats['overdue_amount'],
            'paid_fees_amount': fee_stats['paid_amount'],
            'monthly_expenses': expense_stats['total_amount'],
            'monthly_expense_count': expense_stats['total_count'],
            'monthly_avg_expense': expense_stats['average_expense']
        }
    except Exception as e:
        print(f"Error getting dashboard statistics: {e}")
        return {}

def get_hostel_access_control(request_method='GET', hostel_id_param_name='hostel_id'):
    """
    Utility function to handle hostel access control based on user role.
    Returns a dictionary with hostel_id, current_hostel_name, and hostels_list.
    """
    hostel_id = None
    current_hostel_name = None
    hostels_list = []
    selected_hostel_id = None
    
    if hasattr(g, 'user') and g.user:
        if g.user.get('role') == 'manager':
            # Managers are restricted to their assigned hostel
            hostel_id = g.user.get('hostel_id')
            from models.hostels import Hostel
            hostel = Hostel.get_by_id(hostel_id)
            if hostel:
                current_hostel_name = hostel.name
        elif g.user.get('role') == 'owner':
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

@dashboard_bp.route('/')
def index():
    """Homepage for the admin panel with enhanced dashboard."""
    # Get hostel access control
    hostel_context = get_hostel_access_control()
    hostel_id = hostel_context['hostel_id']
    
    # Get dashboard statistics
    stats = get_dashboard_statistics(hostel_id)
    
    # Get recent activity for dashboard
    with get_db_connection() as conn:
        recent_activity = get_recent_activity(conn, limit=5, hostel_id=hostel_id)
    
    # Recent activities - newest students and upcoming fee payments (also filtered by hostel)
    recent_students = StudentModel.get_recent_students(limit=5)
    upcoming_fees = FeeModel.get_upcoming_fees(limit=5, hostel_id=hostel_id)
    
    # Get recent expenses
    recent_expenses = ExpenseModel.get_recent_expenses(hostel_id=hostel_id, limit=5)
    
    # Ensure room_data is available for the chart (also filtered by hostel)
    room_data = RoomModel.get_room_occupancy_chart_data(hostel_id=hostel_id)
    if room_data is None:
        room_data = [] # Default to an empty list if no data

    return render_template('index.html', 
                           stats=stats, 
                           recent_students=recent_students,
                           upcoming_fees=upcoming_fees,
                           recent_activity=recent_activity,
                           room_data=room_data,
                           **hostel_context) # Pass hostel context to template

@dashboard_bp.route('/reports/room_occupancy')
def room_occupancy_report():
    """Room occupancy report page."""
    rooms = RoomModel.get_all_rooms()
    return render_template('reports/room_occupancy.html', rooms=rooms)

@dashboard_bp.route('/reports/fee_status')
def fee_status_report():
    """Fee status report page."""
    fees = FeeModel.get_all_fees_with_students()
    return render_template('reports/fee_status.html', fees=fees)

@dashboard_bp.route('/reports/activity_reports')
def activity_reports():
    """Activity reports page for owners to see all historical activities."""
    # Check if user is owner
    if not g.user or g.user.get('role') != 'owner':
        flash('Access denied. Owner privileges required.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    hostel_filter = request.args.get('hostel_id', type=int)
    
    # Get hostel list for filter dropdown
    from models.hostels import Hostel
    hostels_list = Hostel.get_all_hostels()
    
    # Get all activities with pagination
    from utils.dashboard import get_all_activities
    with get_db_connection() as conn:
        activity_data = get_all_activities(conn, page=page, per_page=per_page, hostel_id=hostel_filter)
    
    # Get current hostel name if filtered
    current_hostel_name = None
    if hostel_filter:
        hostel = Hostel.get_by_id(hostel_filter)
        if hostel:
            current_hostel_name = hostel.name
    
    return render_template('reports/activity_reports.html', 
                         activities=activity_data['activities'],
                         pagination={
                             'page': activity_data['page'],
                             'per_page': activity_data['per_page'],
                             'total': activity_data['total'],
                             'total_pages': activity_data['total_pages'],
                             'has_prev': activity_data['has_prev'],
                             'has_next': activity_data['has_next']
                         },
                         hostels_list=hostels_list,
                         current_hostel_name=current_hostel_name,
                         selected_hostel_id=hostel_filter)

# Route to export or print reports can be added here
