"""
Simple test script to verify app initialization
"""
import os
import sys

# Import the Flask application
try:
    from app_new import app
    print("Successfully imported app_new module")
    
    # Check if blueprints are registered
    registered_blueprints = [bp.name for bp in app.blueprints.values()]
    print(f"Registered blueprints: {registered_blueprints}")
    
    # Check database connection
    from models.db import get_db_connection
    conn = get_db_connection()
    print("Database connection successful")
    conn.close()
    
    print("All tests passed! The application should run correctly.")
    
except Exception as e:
    print(f"Error during initialization: {e}")
    import traceback
    traceback.print_exc()
