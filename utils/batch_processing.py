"""Utilities for batch processing operations.

This module contains functions that handle batch processing operations
like adding multiple fees at once.
"""

import sqlite3
from datetime import date, timedelta

def process_batch_fees(conn, student_ids, fee_amount, due_date, fee_type="Monthly Fee"):
    """Process batch fee assignments for multiple students.
    
    Args:
        conn: Database connection
        student_ids: List of student IDs to assign fees to
        fee_amount: Amount for each fee
        due_date: Due date for the fees
        fee_type: Type of fee (description)
        
    Returns:
        Tuple of (success_count, error_list)
    """
    success_count = 0
    errors = []
    
    try:
        # Begin transaction for all operations
        conn.execute('BEGIN TRANSACTION')
        
        for student_id in student_ids:
            try:
                # Check if student exists
                student = conn.execute('SELECT name FROM students WHERE id = ?', (student_id,)).fetchone()
                if not student:
                    errors.append(f"Student ID {student_id} not found")
                    continue
                
                # Insert fee record
                conn.execute(
                    'INSERT INTO fees (student_id, amount, due_date, status, description) VALUES (?, ?, ?, ?, ?)',
                    (student_id, fee_amount, due_date, 'Pending', fee_type)
                )
                success_count += 1
                
            except Exception as e:
                errors.append(f"Error processing fee for student ID {student_id}: {e}")
        
        # If everything went well, commit the transaction
        if not errors:
            conn.commit()
            return success_count, errors
        
        # If there were any errors but some succeeded, let caller decide
        if success_count > 0:
            conn.commit()
            return success_count, errors
            
        # If nothing succeeded, roll back
        conn.rollback()
        return 0, errors
            
    except Exception as e:
        # Handle any overall transaction errors
        conn.rollback()
        errors.append(f"Transaction error: {e}")
        return 0, errors

def generate_recurring_fees(conn, frequency="monthly", student_course=None, amount=None):
    """Generate recurring fees based on specified criteria.
    
    Args:
        conn: Database connection
        frequency: 'monthly', 'quarterly', 'semester', or 'annual'
        student_course: Course filter (or None for all)
        amount: Fee amount (or None to use default)
        
    Returns:
        Tuple of (success_count, error_list)
    """
    # Get all active students, optionally filtered by course
    query = "SELECT id, name, course FROM students"
    params = []
    
    if student_course:
        query += " WHERE course = ?"
        params.append(student_course)
    
    try:
        students = conn.execute(query, params).fetchall()
        student_ids = [s['id'] for s in students]
        
        # Set default amount based on frequency if not specified
        fee_amount = amount
        if not fee_amount:
            if frequency == "monthly":
                fee_amount = 1000.00
            elif frequency == "quarterly":
                fee_amount = 2800.00
            elif frequency == "semester":
                fee_amount = 5000.00
            elif frequency == "annual":
                fee_amount = 9500.00
        
        # Set due date based on frequency
        today = date.today()
        if frequency == "monthly":
            due_date = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
            fee_type = "Monthly Fee"
        elif frequency == "quarterly":
            # Add 3 months from the beginning of the month
            month = today.month - 1
            quarter_month = month - (month % 3) + 3  # Next quarter start month
            due_date = date(today.year + (quarter_month // 12), (quarter_month % 12) + 1, 1)
            fee_type = "Quarterly Fee"
        elif frequency == "semester":
            # Set to Jan 1 or Jul 1 depending on current month
            if today.month < 6:
                due_date = date(today.year, 7, 1)
            else:
                due_date = date(today.year + 1, 1, 1)
            fee_type = "Semester Fee"
        elif frequency == "annual":
            due_date = date(today.year + 1, 1, 1)
            fee_type = "Annual Fee"
        else:
            due_date = today + timedelta(days=30)  # Default to 30 days from now
            fee_type = "Fee"
        
        # Process the batch fees
        return process_batch_fees(conn, student_ids, fee_amount, due_date.isoformat(), fee_type)
        
    except Exception as e:
        return 0, [f"Error generating recurring fees: {e}"]
