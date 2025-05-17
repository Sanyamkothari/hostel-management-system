"""
Dashboard and index routes for the Hostel Management System
"""
from flask import Blueprint, render_template
from datetime import date
from models.db import StudentModel, RoomModel, FeeModel

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    """Homepage for the admin panel with enhanced dashboard."""
    # Basic stats
    num_students = StudentModel.count_all_students()
    rooms_stats = RoomModel.get_room_statistics()
    fee_stats = FeeModel.get_fee_statistics()
    
    # Recent activities - newest students and upcoming fee payments
    recent_students = StudentModel.get_recent_students(limit=5)
    upcoming_fees = FeeModel.get_upcoming_fees(limit=5)
    
    # Calculate total capacity and occupancy percentage
    total_capacity = rooms_stats['total_capacity']
    current_occupancy = rooms_stats['current_occupancy']
    occupancy_percentage = (current_occupancy / total_capacity * 100) if total_capacity > 0 else 0
    
    # Prepare stats dictionary for template
    stats = {
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
        'paid_fees_amount': fee_stats['paid_amount']
    }
    
    # Ensure room_data is available for the chart
    room_data = RoomModel.get_room_occupancy_chart_data() # Assuming this method exists and prepares data for the chart
    if room_data is None:
        room_data = [] # Default to an empty list if no data

    return render_template('index.html', 
                           stats=stats, 
                           recent_students=recent_students,
                           upcoming_fees=upcoming_fees,
                           room_data=room_data) # Pass room_data to the template

@dashboard_bp.route('/reports/room_occupancy')
def room_occupancy_report():
    """Room occupancy report page."""
    rooms = RoomModel.get_all_rooms_with_occupancy()
    return render_template('reports/room_occupancy.html', rooms=rooms)

@dashboard_bp.route('/reports/fee_status')
def fee_status_report():
    """Fee status report page."""
    fees = FeeModel.get_all_fees_with_students()
    return render_template('reports/fee_status.html', fees=fees)

# Route to export or print reports can be added here
