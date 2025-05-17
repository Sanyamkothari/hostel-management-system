import sqlite3
import os
from datetime import date

def get_db_connection():
    """Establishes a connection to the database."""
    try:
        from flask import current_app
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), current_app.config.get('DATABASE', 'hostel.db'))
    except RuntimeError:
        # Not in app context
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hostel.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

class DatabaseConnection:
    def __init__(self):
        self.conn = None

    def __enter__(self):
        self.conn = get_db_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is not None:
                self.conn.rollback()
            else:
                self.conn.commit()
            self.conn.close() 