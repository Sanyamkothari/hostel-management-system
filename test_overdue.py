"""
Test script for updating overdue fees
"""
from datetime import date
import os
import sqlite3

def update_overdue_fees():
    conn = sqlite3.connect('hostel.db')
    today = date.today().isoformat()
    
    try:
        cursor = conn.execute(
            "UPDATE fees SET status = 'Overdue' WHERE status = 'Pending' AND due_date < ?", 
            (today,)
        )
        
        updated = cursor.rowcount
        conn.commit()
        return updated
    except Exception as e:
        conn.rollback()
        print(f"Error updating overdue fees: {e}")
        return 0
    finally:
        conn.close()

if __name__ == "__main__":
    updated = update_overdue_fees()
    print(f"Updated {updated} fees to Overdue status")
