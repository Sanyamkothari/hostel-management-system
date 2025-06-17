import sqlite3
import os
import psycopg2
import psycopg2.extras # For DictCursor
from urllib.parse import urlparse
from flask import g, current_app # Import g and current_app directly

def get_db_connection():
    """Establishes a connection to the database based on DATABASE_URL.
       Manages connection via Flask's g object if in app context.
    """
    # Attempt to get connection from g if already set for this context
    # and app context is active
    if 'db_conn' in g:
        # Check if connection is closed (psycopg2 uses .closed attribute which is 0 if open)
        # sqlite3 connection objects don't have a .closed attribute, so we check type
        if isinstance(g.db_conn, psycopg2.extensions.connection) and g.db_conn.closed == 0:
            return g.db_conn
        elif isinstance(g.db_conn, sqlite3.Connection): # No simple closed check for sqlite3, assume open if present in g
            return g.db_conn 

    database_url = current_app.config.get('DATABASE_URL')

    if not database_url:
        # Default to local SQLite if DATABASE_URL is not set
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hostel.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name (for SQLite)
    elif database_url.startswith("postgres://") or database_url.startswith("postgresql://"):
        try:
            conn = psycopg2.connect(database_url)
            # For psycopg2, to get dict-like rows, a DictCursor is typically used.
            # The caller can create a cursor like: cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            # Or we can set a default cursor factory for the connection if that's desired globally for this app.
            # conn.cursor_factory = psycopg2.extras.DictCursor # Example of setting globally for this connection
        except psycopg2.OperationalError as e:
            current_app.logger.error(f"Error connecting to PostgreSQL: {e}")
            raise
    else: # Assume SQLite if not PostgreSQL and URL is provided (e.g., sqlite:///hostel.db)
        parsed_url = urlparse(database_url)
        db_path = parsed_url.path
        if db_path.startswith('/') and not os.path.isabs(db_path):
            db_path = db_path[1:] 
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

    g.db_conn = conn # Store the new connection in g    return conn

# Only register teardown handler if we have an app context
try:
    from flask import current_app
    @current_app.teardown_appcontext
    def close_db_connection(exception=None):
        """Closes the database connection at the end of the request if it's in g."""
        db = g.pop('db_conn', None)
        if db is not None:
            # Check if connection is not already closed
            is_closed = getattr(db, 'closed', False)
            if isinstance(is_closed, int): # psycopg2 style
                is_closed = is_closed != 0
        
            if not is_closed:
                db.close()
except RuntimeError:
    # No app context available, skip teardown handler registration
    pass

class DatabaseConnection:
    def __init__(self):
        self.conn = None

    def __enter__(self):
        # get_db_connection now handles g, so we just call it.
        self.conn = get_db_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        # The connection is now managed by teardown_appcontext, 
        # so this context manager might not need to explicitly close/commit/rollback
        # if get_db_connection always returns the g.db_conn.
        # However, if used outside app context, it should manage its own connection.
        if self.conn:
            # Check if we are outside an app context (g might not be available or not have db_conn)
            try:
                from flask import g
                in_flask_context_with_g_conn = hasattr(g, 'db_conn') and g.db_conn == self.conn
            except RuntimeError:
                in_flask_context_with_g_conn = False

            if not in_flask_context_with_g_conn: # Only manage if not managed by g / teardown_appcontext
                is_closed = getattr(self.conn, 'closed', False)
                if isinstance(is_closed, int): # psycopg2 style
                    is_closed = is_closed != 0

                if not is_closed:
                    if exc_type is not None:
                        self.conn.rollback()
                    else:
                        self.conn.commit()
                    self.conn.close()
            # If in Flask context and g.db_conn is this conn, teardown_appcontext will handle it.