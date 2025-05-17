"""
Fee management routes for the Hostel Management System
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.db import FeeModel, StudentModel
from datetime import date, datetime, timedelta
from utils.date_utils import parse_date, format_date, get_month_range, get_date_intervals
from utils.export import ExportUtility
from db_utils import get_db_connection, DatabaseConnection
import json

fee_bp = Blueprint('fee', __name__, url_prefix='/fees')

@fee_bp.route('/')
def view_fees():
    """View all fees with advanced filtering options."""
    # Get filter parameters
    status_filter = request.args.get('status', '')
    date_range = request.args.get('date_range', '')
    student_name = request.args.get('student_name', '')
    amount_min = request.args.get('amount_min', type=float, default=0)
    amount_max = request.args.get('amount_max', type=float, default=0)
    
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
        'end_date': end_date
    }
    
    # Get fees with filters
    fees = FeeModel.get_all_fees_with_students(filter_params)
    
    # Get data for filter dropdowns
    statuses = FeeModel.get_unique_statuses()
    
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
            calendar_data=calendar_data
        )
    else:
        # Standard list or card view
        return render_template(
            'fees/view_fees.html',
            fees=fees,
            statuses=statuses,
            filter_params=filter_params,
            view_mode=view_mode
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
            'status': str(fee_row.get('status', 'Unknown')) # Ensure string, provide default
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
    if request.method == 'POST':
        fee_data = {
            'student_id': request.form.get('student_id', type=int),
            'amount': request.form.get('amount', type=float),
            'due_date': request.form.get('due_date'),
            'status': request.form.get('status', 'Pending')
        }
        
        # Validate fee data
        if not fee_data['student_id'] or not fee_data['amount']:
            flash('Student and amount are required!', 'error')
            students = StudentModel.get_all_students()
            return render_template('fees/add_fee.html', students=students)
        
        if fee_data['amount'] <= 0:
            flash('Amount must be greater than zero!', 'error')
            students = StudentModel.get_all_students()
            return render_template('fees/add_fee.html', students=students)
        
        # Check if payment is being recorded directly
        if fee_data['status'] == 'Paid':
            fee_data['paid_date'] = request.form.get('paid_date', date.today().isoformat())
        
        try:
            FeeModel.add_fee(fee_data)
            flash('Fee added successfully!', 'success')
            return redirect(url_for('fee.view_fees'))
        except Exception as e:
            flash(f'Error adding fee: {str(e)}', 'error')
    
    # GET request - show the form
    students = StudentModel.get_all_students()
    return render_template('fees/add_fee.html', students=students)

@fee_bp.route('/batch/add', methods=['GET', 'POST'])
def add_batch_fees():
    """Add fees for multiple students at once."""
    if request.method == 'POST':
        student_ids = request.form.getlist('student_ids')
        amount = request.form.get('amount', type=float)
        due_date = request.form.get('due_date')
        
        # Validate inputs
        if not student_ids:
            flash('Please select at least one student!', 'error')
            students = StudentModel.get_all_students()
            return render_template('fees/add_batch_fees.html', students=students)
        
        if not amount or amount <= 0:
            flash('Please enter a valid amount!', 'error')
            students = StudentModel.get_all_students()
            return render_template('fees/add_batch_fees.html', students=students)
        
        # Add fees for each selected student
        success_count = 0
        for student_id in student_ids:
            try:
                FeeModel.add_fee({
                    'student_id': int(student_id),
                    'amount': amount,
                    'due_date': due_date,
                    'status': 'Pending'
                })
                success_count += 1
            except Exception as e:
                flash(f'Error adding fee for student ID {student_id}: {str(e)}', 'error')
        
        if success_count > 0:
            flash(f'Successfully added fees for {success_count} students!', 'success')
            return redirect(url_for('fee.view_fees'))
    
    # GET request - show the form
    students = StudentModel.get_all_students()
    return render_template('fees/add_batch_fees.html', students=students)

@fee_bp.route('/<int:fee_id>/mark_paid', methods=['POST'])
def mark_fee_paid(fee_id):
    """Mark a fee as paid."""
    paid_date = request.form.get('paid_date', date.today().isoformat())
    
    try:
        FeeModel.mark_fee_paid(fee_id, paid_date)
        flash('Fee marked as paid successfully!', 'success')
    except Exception as e:
        flash(f'Error marking fee as paid: {str(e)}', 'error')
    
    # Determine where to redirect based on the source
    redirect_url = request.form.get('redirect_url', url_for('fee.view_fees'))
    return redirect(redirect_url)

@fee_bp.route('/<int:fee_id>/delete', methods=['POST'])
def delete_fee(fee_id):
    """Delete a fee."""
    try:
        FeeModel.delete_fee(fee_id)
        flash('Fee deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting fee: {str(e)}', 'error')
    
    return redirect(url_for('fee.view_fees'))

@fee_bp.route('/reminders')
def fee_reminders():
    """View and manage fee payment reminders."""
    # Get upcoming and overdue fees
    upcoming_fees = FeeModel.get_upcoming_fees(days=7)
    overdue_fees = FeeModel.get_overdue_fees()
    
    return render_template(
        'fees/fee_reminders.html',
        upcoming_fees=upcoming_fees,
        overdue_fees=overdue_fees
    )

@fee_bp.route('/reports')
def fee_reports():
    """Generate fee reports."""
    # Get report parameters
    period = request.args.get('period', 'monthly')
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int) if period == 'monthly' else None
    
    # Generate report data
    report_data = FeeModel.get_fee_report(period=period, year=year, month=month)
    
    return render_template(
        'fees/fee_reports.html',
        report_data=report_data,
        period=period,
        year=year,
        month=month
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
    
    # Get fees data with the applied filters
    fees = FeeModel.get_all_fees(filter_params)
    
    # Convert SQLite Row objects to dictionaries
    fee_data = []
    for fee in fees:
        fee_dict = dict(fee)  # Convert SQLite Row to dict
        fee_data.append({
            'ID': fee_dict['id'],
            'Student Name': fee_dict['student_name'],
            'Amount': f"${fee_dict['amount']}",
            'Due Date': fee_dict['due_date'],
            'Paid Date': fee_dict['paid_date'] or '-',
            'Status': fee_dict['status']
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
        headers = ['ID', 'Student Name', 'Amount', 'Due Date', 'Paid Date', 'Status']
        
        # Generate PDF
        return ExportUtility.export_to_pdf(
            data=fee_data,
            filename=f"fees_report_{timestamp}.pdf",
            title=title,
            description=description,
            headers=headers
        )
    else:  # Default to CSV
        headers = ['ID', 'Student Name', 'Amount', 'Due Date', 'Paid Date', 'Status']
        return ExportUtility.export_to_csv(
            data=fee_data,
            filename=f"fees_export_{timestamp}.csv",
            headers=headers
        )

@fee_bp.route('/send_reminders', methods=['POST'])
def send_fee_reminders():
    """Send email reminders for pending fees."""
    from utils.email_notifier import EmailNotifier
    
    # Default to 3 days before due date for upcoming reminders
    days_threshold = request.form.get('days_threshold', type=int, default=3)
    
    # Send the reminders
    results = EmailNotifier.send_bulk_fee_reminders(days_threshold=days_threshold)
    
    # Flash message with results
    flash(f"Reminders processed: {results['sent']} sent, {results['failed']} failed, {results['skipped']} skipped (no email)", 
          'info' if results['sent'] > 0 else 'warning')
    
    # Redirect back to the fees page
    return redirect(url_for('fee.view_fees'))

@fee_bp.route('/fees/calendar')
def view_fees_calendar():
    with DatabaseConnection() as conn:
        # Get all fees with student and room information
        fees_data = conn.execute("""
            SELECT f.*, s.name as student_name, r.room_number
            FROM fees f
            LEFT JOIN students s ON f.student_id = s.id
            LEFT JOIN rooms r ON s.room_id = r.id
            ORDER BY f.due_date
        """).fetchall()

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
        print("Debug: calendar_data before rendering template:", calendar_data)

        # Convert calendar_data to a JSON string
        calendar_data_json = json.dumps(calendar_data)

        return render_template('fees/view_fees_calendar.html', 
                             fees=calendar_data, # Keep for potential other uses in the template
                             calendar_data_json=calendar_data_json, # Pass JSON string
                             filter_params=filter_params,
                             statuses=['Pending', 'Paid', 'Overdue'])

@fee_bp.route('/<int:fee_id>/edit', methods=['GET', 'POST'])
def edit_fee(fee_id):
    from models.db import FeeModel, StudentModel
    fee = FeeModel.get_fee_by_id(fee_id)
    if not fee:
        flash('Fee record not found.', 'error')
        return redirect(url_for('fee.view_fees'))
    if request.method == 'POST':
        amount = request.form.get('amount', type=float)
        due_date = request.form.get('due_date')
        status = request.form.get('status', 'Pending')
        paid_date = request.form.get('paid_date') if status == 'Paid' else None
        try:
            FeeModel.update_fee(fee_id, amount, due_date, status, paid_date)
            flash('Fee record updated successfully!', 'success')
            return redirect(url_for('fee.view_fees'))
        except Exception as e:
            flash(f'Error updating fee: {e}', 'error')
    students = StudentModel.get_all_students()
    return render_template('fees/edit_fee.html', fee=fee, students=students)
