"""Dashboard utilities for the Hostel Management System.

This module provides helper functions for the dashboard page.
"""

from datetime import date
from utils.cache import cached

@cached(ttl_seconds=300)  # Cache dashboard stats for 5 minutes
def get_dashboard_stats(connection):
    """Get all statistics needed for the dashboard.
    
    Args:
        connection: Database connection
        
    Returns:
        Dictionary containing all dashboard statistics
    """
    try:
        # Basic stats
        num_students = connection.execute('SELECT COUNT(*) FROM students').fetchone()[0]
        num_rooms = connection.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]
        occupied_rooms = connection.execute("SELECT COUNT(*) FROM rooms WHERE status = 'Full'").fetchone()[0]
        available_rooms = connection.execute("SELECT COUNT(*) FROM rooms WHERE status = 'Available'").fetchone()[0]
        maintenance_rooms = connection.execute("SELECT COUNT(*) FROM rooms WHERE status = 'Maintenance'").fetchone()[0]
        
        # Fee statistics
        today_iso = date.today().isoformat()
        pending_fees = connection.execute("SELECT COUNT(*) FROM fees WHERE status = 'Pending'").fetchone()[0]
        overdue_fees = connection.execute(
            "SELECT COUNT(*) FROM fees WHERE status = 'Pending' AND due_date < ?", 
            (today_iso,)
        ).fetchone()[0]
        pending_fees_amount = connection.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM fees WHERE status = 'Pending'"
        ).fetchone()[0]
        overdue_fees_amount = connection.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM fees WHERE status = 'Pending' AND due_date < ?",
            (today_iso,)
        ).fetchone()[0]
        paid_fees_amount = connection.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM fees WHERE status = 'Paid'"
        ).fetchone()[0]
        
        # Get total capacity and occupancy
        total_capacity = connection.execute('SELECT SUM(capacity) FROM rooms').fetchone()[0] or 0
        current_occupancy = connection.execute('SELECT COUNT(*) FROM students WHERE room_id IS NOT NULL').fetchone()[0]
        
        # Calculate occupancy percentage
        occupancy_percentage = (current_occupancy / total_capacity * 100) if total_capacity > 0 else 0
        
        return {
            'students': num_students,
            'rooms': num_rooms,
            'occupied_rooms': occupied_rooms,
            'available_rooms': available_rooms,
            'maintenance_rooms': maintenance_rooms,
            'pending_fees': pending_fees,
            'overdue_fees': overdue_fees,
            'pending_fees_amount': pending_fees_amount,
            'overdue_fees_amount': overdue_fees_amount,
            'paid_fees_amount': paid_fees_amount,
            'total_capacity': total_capacity,
            'current_occupancy': current_occupancy,
            'occupancy_percentage': occupancy_percentage
        }
    except Exception as e:
        # Return default values in case of error
        print(f"Error generating dashboard stats: {e}")
        return {
            'students': 0, 'rooms': 0, 'occupied_rooms': 0, 'available_rooms': 0,
            'maintenance_rooms': 0, 'pending_fees': 0, 'overdue_fees': 0,
            'pending_fees_amount': 0, 'overdue_fees_amount': 0, 'paid_fees_amount': 0,
            'total_capacity': 0, 'current_occupancy': 0, 'occupancy_percentage': 0,
            'error': str(e)
        }

def get_recent_activity(connection, limit=5, hostel_id=None, include_hostel_names=False):
    """Get recent activity data for the dashboard.
    
    Args:
        connection: Database connection
        limit: Maximum number of activities to return
        hostel_id: Filter activities by hostel ID (for managers)
        include_hostel_names: Include hostel names in activity descriptions (for owners)
        
    Returns:
        List of recent activity dictionaries
    """
    try:
        recent_activity = []
        
        # Most recent student additions (up to half the limit)
        student_limit = limit // 2
        if include_hostel_names:
            student_query = '''
                SELECT s.id, s.name, s.admission_date, h.name as hostel_name
                FROM students s
                LEFT JOIN hostels h ON s.hostel_id = h.id
            '''
        else:
            student_query = '''
                SELECT s.id, s.name, s.admission_date 
                FROM students s        '''
        student_params = []
        
        if hostel_id is not None:
            student_query += ' WHERE s.hostel_id = ?' if 'WHERE' not in student_query else ' AND s.hostel_id = ?'
            student_params.append(hostel_id)
            
        student_query += ' ORDER BY s.admission_date DESC, s.id DESC LIMIT ?'
        student_params.append(student_limit)
        
        recent_students = connection.execute(student_query, student_params).fetchall()
        
        for student in recent_students:
            # Convert SQLite Row to dict for easier access
            student_dict = dict(student)
            hostel_name = student_dict.get('hostel_name') if include_hostel_names else None
            
            if include_hostel_names and hostel_name:
                description = f"New student {student_dict['name']} was added to {hostel_name}"
            else:
                description = f"New student {student_dict['name']} was added"
            
            recent_activity.append({
                'type': 'student',
                'description': description,
                'time': f"{student_dict['admission_date']} (Student ID: {student_dict['id']})",
                'hostel_name': hostel_name
            })
        
        # Most recent fee payments (remaining limit)
        payment_limit = limit - len(recent_activity)
        if payment_limit > 0:
            if include_hostel_names:
                payment_query = '''
                    SELECT f.id, f.amount, f.paid_date, s.name as student_name, h.name as hostel_name
                    FROM fees f
                    JOIN students s ON f.student_id = s.id
                    LEFT JOIN hostels h ON s.hostel_id = h.id
                    WHERE f.status = 'Paid' AND f.paid_date IS NOT NULL
                '''
            else:
                payment_query = '''
                    SELECT f.id, f.amount, f.paid_date, s.name as student_name
                    FROM fees f
                    JOIN students s ON f.student_id = s.id
                    WHERE f.status = 'Paid' AND f.paid_date IS NOT NULL            '''
            payment_params = []
            
            if hostel_id is not None:
                payment_query += ' AND s.hostel_id = ?'
                payment_params.append(hostel_id)
                
            payment_query += ' ORDER BY f.paid_date DESC, f.id DESC LIMIT ?'
            payment_params.append(payment_limit)
            
            recent_payments = connection.execute(payment_query, payment_params).fetchall()
            
            for payment in recent_payments:
                # Convert SQLite Row to dict for easier access
                payment_dict = dict(payment)
                hostel_name = payment_dict.get('hostel_name') if include_hostel_names else None
                
                if include_hostel_names and hostel_name:
                    description = f"Payment of ${payment_dict['amount']} received from {payment_dict['student_name']} at {hostel_name}"
                else:
                    description = f"Payment of ${payment_dict['amount']} received from {payment_dict['student_name']}"
                
                recent_activity.append({
                    'type': 'fee',
                    'description': description,
                    'time': f"{payment_dict['paid_date']} (Fee ID: {payment_dict['id']})",
                    'hostel_name': hostel_name
                })
                
        # Sort by most recent first (would need to parse dates properly for real implementation)
        # For now, just return in the order retrieved
        return recent_activity
        
    except Exception as e:
        print(f"Error generating recent activity: {e}")
        return [{'type': 'error', 'description': f"Error loading recent activity: {e}", 'time': date.today().isoformat()}]


def get_all_activities(connection, page=1, per_page=50, hostel_id=None):
    """Get all historical activities with pagination for detailed view.
    
    Args:
        connection: Database connection
        page: Page number (1-based)
        per_page: Number of activities per page
        hostel_id: Filter activities by hostel ID (optional)
        
    Returns:
        Dictionary with activities list, total count, and pagination info
    """
    try:
        offset = (page - 1) * per_page
        all_activities = []
        
        # Get student activities with timestamps
        student_query = '''
            SELECT s.id, s.name, s.admission_date as activity_date, h.name as hostel_name,
                   'student' as activity_type, s.created_at
            FROM students s
            LEFT JOIN hostels h ON s.hostel_id = h.id        '''
        student_params = []
        
        if hostel_id is not None:
            student_query += ' WHERE s.hostel_id = ?'
            student_params.append(hostel_id)
        
        students = connection.execute(student_query, student_params).fetchall()
        
        for student in students:
            # Convert SQLite Row to dict for easier access
            student_dict = dict(student)
            all_activities.append({
                'type': 'student',
                'description': f"New student {student_dict['name']} was added to {student_dict['hostel_name'] or 'Unknown Hostel'}",
                'time': student_dict['admission_date'],
                'created_at': student_dict['created_at'] or student_dict['admission_date'],
                'hostel_name': student_dict['hostel_name'],
                'entity_id': student_dict['id']
            })
        
        # Get fee payment activities
        fee_query = '''
            SELECT f.id, f.amount, f.paid_date as activity_date, s.name as student_name, 
                   h.name as hostel_name, 'fee' as activity_type, f.updated_at
            FROM fees f
            JOIN students s ON f.student_id = s.id
            LEFT JOIN hostels h ON s.hostel_id = h.id
            WHERE f.status = 'Paid' AND f.paid_date IS NOT NULL        '''
        fee_params = []
        
        if hostel_id is not None:
            fee_query += ' AND s.hostel_id = ?'
            fee_params.append(hostel_id)
        
        fees = connection.execute(fee_query, fee_params).fetchall()
        
        for fee in fees:
            # Convert SQLite Row to dict for easier access
            fee_dict = dict(fee)
            all_activities.append({
                'type': 'fee',
                'description': f"Payment of ${fee_dict['amount']} received from {fee_dict['student_name']} at {fee_dict['hostel_name'] or 'Unknown Hostel'}",
                'time': fee_dict['paid_date'],
                'created_at': fee_dict['updated_at'] or fee_dict['paid_date'],
                'hostel_name': fee_dict['hostel_name'],
                'entity_id': fee_dict['id']
            })
        
        # Get expense activities (if expenses table exists)
        try:
            expense_query = '''
                SELECT e.id, e.description, e.amount, e.expense_date as activity_date,
                       h.name as hostel_name, 'expense' as activity_type, e.created_at
                FROM expenses e
                LEFT JOIN hostels h ON e.hostel_id = h.id            '''
            expense_params = []
            
            if hostel_id is not None:
                expense_query += ' WHERE e.hostel_id = ?'
                expense_params.append(hostel_id)
            
            expenses = connection.execute(expense_query, expense_params).fetchall()
            
            for expense in expenses:
                # Convert SQLite Row to dict for easier access
                expense_dict = dict(expense)
                all_activities.append({
                    'type': 'expense',
                    'description': f"Expense: {expense_dict['description']} - ${expense_dict['amount']} at {expense_dict['hostel_name'] or 'Unknown Hostel'}",
                    'time': expense_dict['expense_date'],
                    'created_at': expense_dict['created_at'] or expense_dict['expense_date'],
                    'hostel_name': expense_dict['hostel_name'],
                    'entity_id': expense_dict['id']
                })
        except Exception:
            # Expenses table might not exist, skip
            pass
        
        # Sort all activities by created_at/time in descending order
        all_activities.sort(key=lambda x: x['created_at'] or x['time'], reverse=True)
        
        # Get total count
        total_activities = len(all_activities)
        
        # Apply pagination
        paginated_activities = all_activities[offset:offset + per_page]
        
        return {
            'activities': paginated_activities,
            'total': total_activities,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_activities + per_page - 1) // per_page,
            'has_prev': page > 1,
            'has_next': page * per_page < total_activities
        }
        
    except Exception as e:
        print(f"Error generating all activities: {e}")
        return {
            'activities': [{'type': 'error', 'description': f"Error loading activities: {e}", 'time': date.today().isoformat()}],
            'total': 1,
            'page': 1,
            'per_page': per_page,
            'total_pages': 1,
            'has_prev': False,
            'has_next': False
        }
