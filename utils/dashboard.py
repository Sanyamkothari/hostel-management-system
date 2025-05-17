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

def get_recent_activity(connection, limit=5):
    """Get recent activity data for the dashboard.
    
    Args:
        connection: Database connection
        limit: Maximum number of activities to return
        
    Returns:
        List of recent activity dictionaries
    """
    try:
        recent_activity = []
        
        # Most recent student additions (up to half the limit)
        student_limit = limit // 2
        recent_students = connection.execute('''
            SELECT id, name, admission_date 
            FROM students 
            ORDER BY admission_date DESC, id DESC
            LIMIT ?
        ''', (student_limit,)).fetchall()
        
        for student in recent_students:
            recent_activity.append({
                'type': 'student',
                'description': f"New student {student['name']} was added",
                'time': f"{student['admission_date']} (Student ID: {student['id']})"
            })
        
        # Most recent fee payments (remaining limit)
        payment_limit = limit - len(recent_activity)
        if payment_limit > 0:
            recent_payments = connection.execute('''
                SELECT f.id, f.amount, f.paid_date, s.name as student_name
                FROM fees f
                JOIN students s ON f.student_id = s.id
                WHERE f.status = 'Paid' AND f.paid_date IS NOT NULL
                ORDER BY f.paid_date DESC, f.id DESC
                LIMIT ?
            ''', (payment_limit,)).fetchall()
            
            for payment in recent_payments:
                recent_activity.append({
                    'type': 'fee',
                    'description': f"Payment of ${payment['amount']} received from {payment['student_name']}",
                    'time': f"{payment['paid_date']} (Fee ID: {payment['id']})"
                })
                
        # Sort by most recent first (would need to parse dates properly for real implementation)
        # For now, just return in the order retrieved
        return recent_activity
        
    except Exception as e:
        print(f"Error generating recent activity: {e}")
        return [{'type': 'error', 'description': f"Error loading recent activity: {e}", 'time': date.today().isoformat()}]
