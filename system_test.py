"""
System Test Script for Hostel Management System
This script performs diagnostic tests on various components of the system.
"""
import os
import sys
import sqlite3
import importlib.util
from datetime import date

def print_header(message):
    """Print a formatted header."""
    print("\n" + "="*80)
    print(f" {message}")
    print("="*80)

def test_db_connection():
    """Test database connection and basic structure."""
    print_header("Testing Database Connection")
    
    try:
        # Attempt to import the db module
        from models.db import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if tables exist
        tables = [
            'students', 'student_details', 'rooms', 'fees'
        ]
        
        for table in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                print(f"✓ Table '{table}' exists")
            else:
                print(f"✗ Table '{table}' does not exist")
                
        # Check student schema
        cursor.execute("PRAGMA table_info(students)")
        columns = [row[1] for row in cursor.fetchall()]
        required_cols = ['student_id_number', 'expected_checkout_date']
        
        for col in required_cols:
            if col in columns:
                print(f"✓ Column '{col}' exists in students table")
            else:
                print(f"✗ Column '{col}' missing from students table")
        
        conn.close()
        print("Database connection test completed")
        return True
    
    except Exception as e:
        print(f"✗ Database test failed: {str(e)}")
        return False

def test_models():
    """Test model class functionality."""
    print_header("Testing Model Classes")
    
    try:
        from models.db import StudentModel, RoomModel, FeeModel
        
        # Test basic methods
        tests = [
            ("StudentModel.count_all_students()", StudentModel.count_all_students),
            ("RoomModel.get_room_statistics()", RoomModel.get_room_statistics),
            ("FeeModel.get_fee_statistics()", FeeModel.get_fee_statistics)
        ]
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                print(f"✓ {test_name} successful")
            except Exception as e:
                print(f"✗ {test_name} failed: {str(e)}")
                
        return True
        
    except Exception as e:
        print(f"✗ Model test failed: {str(e)}")
        return False

def test_route_modules():
    """Test that all route modules can be imported."""
    print_header("Testing Route Modules")
    
    route_modules = [
        'routes.dashboard',
        'routes.students',
        'routes.rooms',
        'routes.fees'
    ]
    
    for module_name in route_modules:
        try:
            module = importlib.import_module(module_name)
            print(f"✓ Module '{module_name}' imported successfully")
        except Exception as e:
            print(f"✗ Module '{module_name}' import failed: {str(e)}")
    
    return True

def test_app_configuration():
    """Test application configuration."""
    print_header("Testing Application Configuration")
    
    try:
        from app_new import app
        
        # Check secret key
        if app.secret_key:
            print(f"✓ App secret key is configured")
        else:
            print(f"✗ App secret key is not configured")
            
        # Check blueprints registration
        blueprint_names = [
            'dashboard', 'student', 'room', 'fee'
        ]
        
        for name in blueprint_names:
            # Look for a blueprint with this name in the app's blueprints
            found = False
            for bp in app.blueprints:
                if name in bp:
                    found = True
                    print(f"✓ Blueprint '{name}' is registered")
                    break
                    
            if not found:
                print(f"✗ Blueprint '{name}' is not registered")
        
        return True
        
    except Exception as e:
        print(f"✗ App configuration test failed: {str(e)}")
        return False

def test_static_files():
    """Test presence of required static files."""
    print_header("Testing Static Files")
    
    static_files = [
        'static/css/dashboard.css',
        'static/css/fee-calendar.css',
        'static/css/room-visualization.css',
        'static/css/student-cards.css',
        'static/css/student-profile.css',
        'static/js/dashboard-charts.js'
    ]
    
    for file_path in static_files:
        if os.path.exists(file_path):
            print(f"✓ Static file '{file_path}' exists")
        else:
            print(f"✗ Static file '{file_path}' is missing")
    
    return True

def test_template_files():
    """Test presence of required template files."""
    print_header("Testing Template Files")
    
    template_files = [
        'templates/index.html',
        'templates/layout.html',
        'templates/errors/404.html',
        'templates/errors/500.html',
        'templates/students/student_details.html',
        'templates/students/view_students.html',
        'templates/fees/add_batch_fees.html',
        'templates/fees/view_fees_calendar.html',
        'templates/reports/fee_payments_report.html', 
        'templates/reports/room_occupancy_report.html'
    ]
    
    for file_path in template_files:
        if os.path.exists(file_path):
            print(f"✓ Template file '{file_path}' exists")
        else:
            print(f"✗ Template file '{file_path}' is missing")
    
    return True

def run_all_tests():
    """Run all system tests."""
    print_header("HOSTEL MANAGEMENT SYSTEM - SYSTEM TEST")
    print(f"Test Date: {date.today()}")
    
    tests = [
        ("Database Connection", test_db_connection),
        ("Model Classes", test_models),
        ("Route Modules", test_route_modules),
        ("App Configuration", test_app_configuration),
        ("Static Files", test_static_files),
        ("Template Files", test_template_files)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nRunning test: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"Test '{test_name}' failed with error: {str(e)}")
            results.append((test_name, False))
    
    print_header("TEST SUMMARY")
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "PASSED" if result else "FAILED"
        if result:
            passed += 1
        else:
            failed += 1
        print(f"{name.ljust(25)}: {status}")
    
    print(f"\nTotal: {len(results)}, Passed: {passed}, Failed: {failed}")
    
    if failed == 0:
        print("\n✓ All tests passed! The system appears to be correctly configured.")
    else:
        print(f"\n✗ {failed} test(s) failed. Please review the issues above.")

if __name__ == "__main__":
    run_all_tests()
