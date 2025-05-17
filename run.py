"""
Run script for the Hostel Management System
This script helps with running the application using the new modular structure
"""
import os
import sys
import argparse
from shutil import copy2
from app_new import app  # Import the new modular application

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run Hostel Management System')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--backup-db', action='store_true', help='Backup the database before running')
    return parser.parse_args()

def backup_database():
    """Backup the database file."""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hostel.db')
    backup_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hostel.db.backup')
    
    if os.path.exists(db_path):
        try:
            copy2(db_path, backup_path)
            print(f"Database backed up to {backup_path}")
        except Exception as e:
            print(f"Error backing up database: {e}")
    else:
        print("No database file found to backup.")

def main():
    """Main entry point for the script."""
    args = parse_args()
    
    if args.backup_db:
        backup_database()
    
    # Run the Flask application
    app.run(debug=args.debug, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
