"""
Expense management routes for the Hostel Management System
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g
from models.db import ExpenseModel
from datetime import date, datetime, timedelta
from utils.date_utils import parse_date, format_date, get_month_range, get_date_intervals
from utils.export import ExportUtility
from utils.user_utils import get_user_attribute
from db_utils import get_db_connection, DatabaseConnection
import json

expense_bp = Blueprint('expense', __name__, url_prefix='/expenses')

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
        current_hostel_name = Hostel.get_hostel_name(hostel_id)
    elif user_role == 'owner':
        # Owners can view all hostels or filter by specific hostel
        from models.hostels import Hostel
        hostels_list = Hostel.get_all_hostels()
        
        if request_method == 'GET':
            selected_hostel_id = request.args.get(hostel_id_param_name, type=int)
        elif request_method == 'POST':
            selected_hostel_id = request.form.get(hostel_id_param_name, type=int)
        
        if selected_hostel_id:
            hostel_id = selected_hostel_id
            current_hostel_name = Hostel.get_hostel_name(hostel_id)
        else:
            current_hostel_name = "All Hostels"
    
    return {
        'hostel_id': hostel_id,
        'current_hostel_name': current_hostel_name,
        'hostels_list': hostels_list,
        'selected_hostel_id': selected_hostel_id or hostel_id
    }

@expense_bp.route('/')
def list_expenses():
    """Display all expenses with filtering options"""
    try:
        access_control = get_hostel_access_control()
        
        # Get filter parameters
        category = request.args.get('category', '')
        expense_type = request.args.get('expense_type', '')
        payment_method = request.args.get('payment_method', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        search = request.args.get('search', '')
          # Parse dates
        start_date_obj = parse_date(start_date) if start_date else None
        end_date_obj = parse_date(end_date) if end_date else None
          # Get expenses with filters
        filters = {
            'category': category if category else None,
            'expense_type': expense_type if expense_type else None,
            'payment_method': payment_method if payment_method else None,
            'start_date': start_date_obj.isoformat() if start_date_obj else None,
            'end_date': end_date_obj.isoformat() if end_date_obj else None,
            'description': search if search else None
        }
        # Remove None values from filters
        filters = {k: v for k, v in filters.items() if v is not None}
        
        expenses = ExpenseModel.get_all_expenses(
            filters=filters,
            hostel_id=access_control['hostel_id']
        )
        
        # Get expense categories and types for filter dropdown
        categories = ['Maintenance', 'Utilities', 'Food', 'Supplies', 'Staff', 'Security', 'Cleaning', 'Internet', 'Other']
        expense_types = ['Operational', 'Capital', 'Emergency']
        payment_methods = ['Cash', 'Card', 'Bank Transfer', 'Cheque', 'UPI', 'Other']
        
        return render_template('expenses/list.html',
                             expenses=expenses,
                             categories=categories,
                             expense_types=expense_types,
                             payment_methods=payment_methods,
                             filters={
                                 'category': category,
                                 'expense_type': expense_type,
                                 'payment_method': payment_method,
                                 'start_date': start_date,
                                 'end_date': end_date,
                                 'search': search                             },
                             **access_control)
    except Exception as e:
        flash(f'Error loading expenses: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))

@expense_bp.route('/add', methods=['GET', 'POST'])
def add_expense():
    """Add a new expense"""
    try:
        # Pass the correct request method to access control
        access_control = get_hostel_access_control(request.method)
        
        if request.method == 'POST':
            # Validate required fields
            description = request.form.get('description', '').strip()
            amount = request.form.get('amount', '').strip()
            expense_date = request.form.get('expense_date', '').strip()
            category = request.form.get('category', '').strip()
            expense_type = request.form.get('expense_type', '').strip()
            payment_method = request.form.get('payment_method', '').strip()
            
            if not all([description, amount, expense_date, category, expense_type, payment_method]):
                flash('Please fill in all required fields.', 'error')
                return render_template('expenses/add.html', **access_control)
            
            try:
                amount = float(amount)
                if amount <= 0:
                    flash('Amount must be greater than 0.', 'error')
                    return render_template('expenses/add.html', **access_control)
            except ValueError:
                flash('Please enter a valid amount.', 'error')
                return render_template('expenses/add.html', **access_control)
            
            expense_date_obj = parse_date(expense_date)
            if not expense_date_obj:
                flash('Please enter a valid date.', 'error')
                return render_template('expenses/add.html', **access_control)
            
            # Get optional fields
            vendor_name = request.form.get('vendor_name', '').strip()
            receipt_number = request.form.get('receipt_number', '').strip()
            approved_by = request.form.get('approved_by', '').strip()
            notes = request.form.get('notes', '').strip()
            
            # Determine hostel_id
            expense_hostel_id = access_control['selected_hostel_id']
            if not expense_hostel_id:
                flash('Please select a hostel.', 'error')
                return render_template('expenses/add.html', **access_control)
              # Add expense
            expense_data = {
                'description': description,
                'amount': amount,
                'expense_date': expense_date_obj,
                'category': category,
                'expense_type': expense_type,
                'vendor_name': vendor_name if vendor_name else None,
                'receipt_number': receipt_number if receipt_number else None,
                'payment_method': payment_method,
                'approved_by': approved_by if approved_by else None,
                'notes': notes if notes else None
            }
            result = ExpenseModel.add_expense(expense_data, expense_hostel_id)
            expense_id = result.get('expense_id') if result.get('success') else None
            
            if expense_id:
                flash('Expense added successfully!', 'success')
                return redirect(url_for('expense.list_expenses'))
            else:
                flash('Failed to add expense. Please try again.', 'error')
        
        # Get dropdown options
        categories = ['Maintenance', 'Utilities', 'Food', 'Supplies', 'Staff', 'Security', 'Cleaning', 'Internet', 'Other']
        expense_types = ['Operational', 'Capital', 'Emergency']
        payment_methods = ['Cash', 'Card', 'Bank Transfer', 'Cheque', 'UPI', 'Other']
        
        return render_template('expenses/add.html',
                             categories=categories,
                             expense_types=expense_types,
                             payment_methods=payment_methods,
                             **access_control)
    except Exception as e:
        flash(f'Error adding expense: {str(e)}', 'error')
        return redirect(url_for('expense.list_expenses'))

@expense_bp.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    """Edit an existing expense"""
    try:
        access_control = get_hostel_access_control('POST')
        
        # Get expense
        expense = ExpenseModel.get_expense_by_id(expense_id, access_control['hostel_id'])
        if not expense:
            flash('Expense not found.', 'error')
            return redirect(url_for('expense.list_expenses'))
        
        if request.method == 'POST':
            # Validate required fields
            description = request.form.get('description', '').strip()
            amount = request.form.get('amount', '').strip()
            expense_date = request.form.get('expense_date', '').strip()
            category = request.form.get('category', '').strip()
            expense_type = request.form.get('expense_type', '').strip()
            payment_method = request.form.get('payment_method', '').strip()
            
            if not all([description, amount, expense_date, category, expense_type, payment_method]):
                flash('Please fill in all required fields.', 'error')
                return render_template('expenses/edit.html', expense=expense, **access_control)
            
            try:
                amount = float(amount)
                if amount <= 0:
                    flash('Amount must be greater than 0.', 'error')
                    return render_template('expenses/edit.html', expense=expense, **access_control)
            except ValueError:
                flash('Please enter a valid amount.', 'error')
                return render_template('expenses/edit.html', expense=expense, **access_control)
            
            expense_date_obj = parse_date(expense_date)
            if not expense_date_obj:
                flash('Please enter a valid date.', 'error')
                return render_template('expenses/edit.html', expense=expense, **access_control)
            
            # Get optional fields
            vendor_name = request.form.get('vendor_name', '').strip()
            receipt_number = request.form.get('receipt_number', '').strip()
            approved_by = request.form.get('approved_by', '').strip()
            notes = request.form.get('notes', '').strip()
              # Update expense
            expense_data = {
                'description': description,
                'amount': amount,
                'expense_date': expense_date_obj,
                'category': category,
                'expense_type': expense_type,
                'vendor_name': vendor_name if vendor_name else None,
                'receipt_number': receipt_number if receipt_number else None,
                'payment_method': payment_method,
                'approved_by': approved_by if approved_by else None,
                'notes': notes if notes else None
            }
            result = ExpenseModel.update_expense(expense_id, expense_data, access_control['hostel_id'])
            success = result.get('success', False)
            
            if success:
                flash('Expense updated successfully!', 'success')
                return redirect(url_for('expense.list_expenses'))
            else:
                flash('Failed to update expense. Please try again.', 'error')
        
        # Get dropdown options
        categories = ['Maintenance', 'Utilities', 'Food', 'Supplies', 'Staff', 'Security', 'Cleaning', 'Internet', 'Other']
        expense_types = ['Operational', 'Capital', 'Emergency']
        payment_methods = ['Cash', 'Card', 'Bank Transfer', 'Cheque', 'UPI', 'Other']
        
        return render_template('expenses/edit.html',
                             expense=expense,
                             categories=categories,
                             expense_types=expense_types,
                             payment_methods=payment_methods,
                             **access_control)
    except Exception as e:
        flash(f'Error editing expense: {str(e)}', 'error')
        return redirect(url_for('expense.list_expenses'))

@expense_bp.route('/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    """Delete an expense"""
    try:
        access_control = get_hostel_access_control('POST')
        
        result = ExpenseModel.delete_expense(expense_id, access_control['hostel_id'])
        if result.get('success'):
            flash('Expense deleted successfully!', 'success')
        else:
            flash('Failed to delete expense or expense not found.', 'error')
        
        return redirect(url_for('expense.list_expenses'))
    except Exception as e:
        flash(f'Error deleting expense: {str(e)}', 'error')
        return redirect(url_for('expense.list_expenses'))

@expense_bp.route('/view/<int:expense_id>')
def view_expense(expense_id):
    """View expense details"""
    try:
        access_control = get_hostel_access_control()
        
        expense = ExpenseModel.get_expense_by_id(expense_id, access_control['hostel_id'])
        if not expense:
            flash('Expense not found.', 'error')
            return redirect(url_for('expense.list_expenses'))
        
        return render_template('expenses/view.html', expense=expense, **access_control)
    except Exception as e:
        flash(f'Error viewing expense: {str(e)}', 'error')
        return redirect(url_for('expense.list_expenses'))

@expense_bp.route('/reports')
def expense_reports():
    """Display expense reports and analytics"""
    try:
        access_control = get_hostel_access_control()
        
        # Get filter parameters
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        category = request.args.get('category', '')
        expense_type = request.args.get('expense_type', '')
          # Default to current month if no dates provided
        if not start_date or not end_date:
            today = date.today()
            start_date = today.replace(day=1).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        
        start_date_obj = parse_date(start_date)
        end_date_obj = parse_date(end_date)
        
        # Get expense statistics
        stats = ExpenseModel.get_expense_statistics(
            hostel_id=access_control['hostel_id'],
            period='monthly'
        )
        
        # Get detailed expense report
        filters = {
            'start_date': start_date_obj.isoformat() if start_date_obj else None,
            'end_date': end_date_obj.isoformat() if end_date_obj else None,
            'category': category if category else None,
            'expense_type': expense_type if expense_type else None
        }
        # Remove None values from filters
        filters = {k: v for k, v in filters.items() if v is not None}
        
        report = ExpenseModel.get_expense_report(
            filters=filters,
            hostel_id=access_control['hostel_id']
        )
        
        # Get dropdown options
        categories = ['Maintenance', 'Utilities', 'Food', 'Supplies', 'Staff', 'Security', 'Cleaning', 'Internet', 'Other']
        expense_types = ['Operational', 'Capital', 'Emergency']
        
        return render_template('expenses/reports.html',
                             stats=stats,
                             report=report,
                             categories=categories,
                             expense_types=expense_types,
                             filters={
                                 'start_date': start_date,
                                 'end_date': end_date,
                                 'category': category,
                                 'expense_type': expense_type                             },
                             **access_control)
    except Exception as e:
        flash(f'Error loading expense reports: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))

@expense_bp.route('/export')
def export_expenses():
    """Export expenses to CSV/Excel"""
    try:
        access_control = get_hostel_access_control()
        
        # Get filter parameters
        category = request.args.get('category', '')
        expense_type = request.args.get('expense_type', '')
        payment_method = request.args.get('payment_method', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        search = request.args.get('search', '')
        export_format = request.args.get('format', 'csv')
          # Parse dates
        start_date_obj = parse_date(start_date) if start_date else None
        end_date_obj = parse_date(end_date) if end_date else None
          # Get expenses
        filters = {
            'category': category if category else None,
            'expense_type': expense_type if expense_type else None,
            'payment_method': payment_method if payment_method else None,
            'start_date': start_date_obj.isoformat() if start_date_obj else None,
            'end_date': end_date_obj.isoformat() if end_date_obj else None,
            'description': search if search else None
        }
        # Remove None values from filters
        filters = {k: v for k, v in filters.items() if v is not None}
        
        expenses = ExpenseModel.get_all_expenses(
            filters=filters,
            hostel_id=access_control['hostel_id']
        )
        
        # Prepare data for export
        export_data = []
        for expense in expenses:
            export_data.append({
                'ID': expense['id'],
                'Description': expense['description'],
                'Amount': expense['amount'],
                'Date': expense['expense_date'],
                'Category': expense['category'],
                'Type': expense['expense_type'],
                'Vendor': expense['vendor_name'] or '',
                'Receipt Number': expense['receipt_number'] or '',
                'Payment Method': expense['payment_method'],
                'Approved By': expense['approved_by'] or '',
                'Notes': expense['notes'] or '',
                'Hostel': expense.get('hostel_name', ''),
                'Created At': expense['created_at']
            })
        
        # Generate filename
        filename = f"expenses_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Export using utility
        return ExportUtility.export_data(
            data=export_data,
            filename=filename,
            format_type=export_format,
            title='Expense Report'
        )
        
    except Exception as e:
        flash(f'Error exporting expenses: {str(e)}', 'error')
        return redirect(url_for('expense.list_expenses'))

# API Routes for AJAX requests
@expense_bp.route('/api/recent')
def api_recent_expenses():
    """API endpoint for recent expenses (for dashboard)"""
    try:
        access_control = get_hostel_access_control()
        limit = request.args.get('limit', 5, type=int)
        
        expenses = ExpenseModel.get_recent_expenses(
            hostel_id=access_control['hostel_id'],
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'expenses': expenses
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@expense_bp.route('/api/statistics')
def api_expense_statistics():
    """API endpoint for expense statistics (for dashboard)"""
    try:
        access_control = get_hostel_access_control()
          # Get current month statistics
        today = date.today()
        start_date = today.replace(day=1)
        end_date = today
        stats = ExpenseModel.get_expense_statistics(
            hostel_id=access_control['hostel_id'],
            period='monthly',
            year=today.year,
            month=today.month
        )
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
