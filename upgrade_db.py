#!/usr/bin/env python
"""
Database Upgrade Script for Hostel Management System
This script upgrades the database schema to include new fields without data loss.
"""

import os
import sqlite3
import sys

# Database path
DATABASE = 'hostel.db'

def upgrade_database():
    """Run SQL upgrade script on the database."""
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE)
        
        if not os.path.exists(db_path):
            print(f"Database not found at {db_path}")
            sys.exit(1)
            
        # Create backup before making changes
        backup_path = f"{db_path}.backup"
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        print(f"Created backup at {backup_path}")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Check existing columns in students table
            cursor.execute("PRAGMA table_info(students)")
            existing_columns = [col['name'] for col in cursor.fetchall()]
            
            # Add new columns if they don't exist
            if 'student_id_number' not in existing_columns:
                print("Adding student_id_number column...")
                cursor.execute("ALTER TABLE students ADD COLUMN student_id_number TEXT DEFAULT NULL")
            
            if 'expected_checkout_date' not in existing_columns:
                print("Adding expected_checkout_date column...")
                cursor.execute("ALTER TABLE students ADD COLUMN expected_checkout_date DATE DEFAULT NULL")
            
            # Check if student_details table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='student_details'")
            if not cursor.fetchone():
                print("Creating student_details table...")
                cursor.execute('''
                    CREATE TABLE student_details (
                        student_id INTEGER PRIMARY KEY,
                        home_address TEXT,
                        city TEXT,
                        state TEXT,
                        zip_code TEXT,
                        parent_name TEXT,
                        parent_contact TEXT,
                        emergency_contact_name TEXT,
                        emergency_contact_phone TEXT,
                        additional_notes TEXT,
                        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
                    )
                ''')
            
            # Create unique index for student_id_number if it doesn't exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_students_student_id_number'")
            if not cursor.fetchone():
                print("Creating unique index for student_id_number...")
                cursor.execute('''
                    CREATE UNIQUE INDEX idx_students_student_id_number 
                    ON students(student_id_number)
                    WHERE student_id_number IS NOT NULL
                ''')
            
            conn.commit()
            print("Database schema upgraded successfully!")
            
            # Verify changes
            cursor.execute("PRAGMA table_info(students)")
            columns = [col['name'] for col in cursor.fetchall()]
            missing_cols = []
            for col in ['student_id_number', 'expected_checkout_date']:
                if col not in columns:
                    missing_cols.append(col)
            
            if missing_cols:
                print(f"ERROR: Expected columns {missing_cols} not found in students table")
                sys.exit(1)
                
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='student_details'")
            if not cursor.fetchone():
                print("ERROR: Expected table 'student_details' not found")
                sys.exit(1)
                
            print("Verification successful!")
            
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
            print("Rolling back to backup...")
            conn.close()
            with open(backup_path, 'rb') as src, open(db_path, 'wb') as dst:
                dst.write(src.read())
            print("Rollback complete")
            sys.exit(1)
            
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    if input("This will upgrade your hostel management database schema. Continue? (y/n): ").lower() != 'y':
        print("Operation cancelled")
        sys.exit(0)
    upgrade_database()
