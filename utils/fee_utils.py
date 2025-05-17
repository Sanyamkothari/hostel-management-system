"""
Utility functions for fee management in the Hostel Management System.
"""
from datetime import date
from db_utils import get_db_connection

def update_overdue_fees():
    """
    Update fee status to 'Overdue' for all pending fees past their due date.
    Returns the number of fees updated.
    """
    conn = get_db_connection()
    today = date.today().isoformat()
    count = 0
    
    try:
        cursor = conn.execute("""
            UPDATE fees 
            SET status = 'Overdue' 
            WHERE status = 'Pending' 
            AND due_date < ?
        """, (today,))
        
        count = cursor.rowcount
        conn.commit()
        return count
    except Exception as e:
        conn.rollback()
        print(f"Error updating overdue fees: {e}")
        return 0
    finally:
        conn.close()

def get_student_fee_summary(student_id):
    """
    Get comprehensive fee information for a student.
    
    Returns:
        dict: Contains processed fees and summary statistics
    """
    conn = get_db_connection()
    today = date.today()
    
    try:
        fees = conn.execute('''
            SELECT id, amount, due_date, paid_date, status, description, fee_type
            FROM fees
            WHERE student_id = ?
            ORDER BY due_date DESC
        ''', (student_id,)).fetchall()
        
        processed_fees = []
        total_paid = 0
        total_pending = 0
        total_overdue = 0
        
        for fee_row in fees:
            fee = dict(fee_row)
            
            # Format dates for display
            if fee['due_date']:
                try:
                    fee['due_date_obj'] = date.fromisoformat(fee['due_date'])
                    fee['due_date_formatted'] = fee['due_date_obj'].strftime('%b %d, %Y')
                except (ValueError, TypeError):
                    fee['due_date_obj'] = None
                    fee['due_date_formatted'] = 'Invalid date'
                    
            if fee['paid_date']:
                try:
                    fee['paid_date_obj'] = date.fromisoformat(fee['paid_date'])
                    fee['paid_date_formatted'] = fee['paid_date_obj'].strftime('%b %d, %Y')
                except (ValueError, TypeError):
                    fee['paid_date_obj'] = None
                    fee['paid_date_formatted'] = 'Invalid date'
            
            # Check for overdue status
            fee['is_overdue'] = False
            if fee['status'] == 'Pending' and fee.get('due_date_obj') and fee['due_date_obj'] < today:
                fee['is_overdue'] = True
                total_overdue += fee['amount']
            
            # Calculate totals
            if fee['status'] == 'Paid':
                total_paid += fee['amount']
            elif fee['status'] == 'Overdue':
                total_overdue += fee['amount']
                total_pending += fee['amount']
            else:  # 'Pending'
                total_pending += fee['amount']
            
            processed_fees.append(fee)
        
        # Create summary for template
        summary = {
            'total': total_paid + total_pending,
            'paid': total_paid,
            'pending': total_pending - total_overdue,
            'overdue': total_overdue,
            'count': len(processed_fees)
        }
        
        return {
            'fees': processed_fees,
            'summary': summary
        }
    finally:
        conn.close()
