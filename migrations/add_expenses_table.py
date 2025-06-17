"""
Add expenses table to existing database.
"""
import os
import sqlite3

def add_expenses_table():
    """Add the expenses table to the existing database."""
    # Get the database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hostel.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if the expenses table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='expenses'")
        if cursor.fetchone():
            print("Expenses table already exists.")
            return True
        
        print("Creating expenses table...")
        
        # Create expenses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                expense_date DATE DEFAULT CURRENT_DATE,
                category TEXT NOT NULL,
                expense_type TEXT DEFAULT 'Operational',
                vendor_name TEXT,
                receipt_number TEXT,
                payment_method TEXT DEFAULT 'Cash',
                approved_by INTEGER,
                notes TEXT,
                hostel_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (hostel_id) REFERENCES hostels(id) ON DELETE SET NULL
            )
        ''')
        
        # Create indexes for expenses
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_hostel_id ON expenses(hostel_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_type ON expenses(expense_type)')
        
        # Commit the changes
        conn.commit()
        print("Expenses table created successfully.")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Failed to create expenses table: {e}")
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    success = add_expenses_table()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
