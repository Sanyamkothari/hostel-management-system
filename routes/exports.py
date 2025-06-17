from flask import request, flash, redirect, url_for, Blueprint, g
from datetime import datetime, date, timedelta
from models.db import FeeModel # Assuming FeeModel is in models.db
from utils.date_utils import get_month_range, parse_date # Assuming these are in utils.date_utils
from utils.export import ExportUtility
from utils.email_notifier import EmailNotifier

fee_bp = Blueprint('export', __name__)

@fee_bp.route('/export')
def export_fees():
    """Export fees data to CSV or PDF."""
    
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
        if g.user.role == 'manager':
            # Managers are restricted to their hostel
            hostel_id = g.user.hostel_id
            from models.hostels import Hostel
            hostel = Hostel.get_by_id(hostel_id)
            if hostel:
                current_hostel_name = hostel.name
        elif g.user.role == 'owner':
            # Owners can filter by hostel
            from models.hostels import Hostel
            hostel_id_param = request.args.get('hostel_id')
            if hostel_id_param:
                hostel_id = int(hostel_id_param)
                hostel = Hostel.get_by_id(hostel_id)
                if hostel:
                    current_hostel_name = hostel.name
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
        'status': status_filter,        'student_name': student_name,
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
        
        # Generate description text        # Add hostel name to title if available
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
    # Determine hostel_id based on user role
    hostel_id = None
    if hasattr(g, 'user') and g.user:
        if g.user.role == 'manager':
            hostel_id = g.user.hostel_id
        elif g.user.role == 'owner':
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
