"""
Database migration utility for multi-hostel system.
"""
import os
import sqlite3
from werkzeug.security import generate_password_hash

def run_migration():
    """Run the multi-hostel system migration."""
    # Get the database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hostel.db')
    
    # Create a backup first
    backup_path = db_path + '.backup'
    if os.path.exists(db_path):
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"Created database backup at {backup_path}")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if the hostels table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hostels'")
        if cursor.fetchone():
            print("Hostels table exists: skipping schema creation.")
        else:
            # Read and execute the migration SQL
            migration_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                         'migrations', 'multi_hostel_schema.sql')
            with open(migration_path, 'r') as f:
                migration_sql = f.read()
            for statement in migration_sql.split(';'):
                if statement.strip():
                    cursor.execute(statement)
            # Create default hostel
            cursor.execute(
                'INSERT INTO hostels (name, address, contact_number) VALUES (?, ?, ?)',
                ('Main Hostel', '123 Main Street', '+1-555-123-4567')
            )
            hostel_id = cursor.lastrowid
            # Update existing records to associate with the default hostel
            for table in ['students', 'rooms', 'fees', 'complaints']:
                cursor.execute(f"UPDATE {table} SET hostel_id = ? WHERE hostel_id IS NULL", (hostel_id,))
        
        # Ensure default owner account exists
        cursor.execute("SELECT id FROM users WHERE username = 'owner'")
        if not cursor.fetchone():
            print("Creating default owner user.")
            hashed_password = generate_password_hash('owner123')
            cursor.execute(
                'INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)',
                ('owner', hashed_password, 'Hostel Owner', 'owner')
            )
        
        # Commit all changes
        conn.commit()
        print("Multi-hostel system migration completed successfully.")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        
        # Restore from backup if available
        if os.path.exists(backup_path):
            import shutil
            shutil.copy2(backup_path, db_path)
            print("Restored database from backup.")
    
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
