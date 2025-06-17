#!/usr/bin/env python3
"""
Quick Application Test Script
Tests the application components without starting the full server
"""

import os
import sys
from pathlib import Path

# Set environment variables for testing
os.environ['SECRET_KEY'] = 'test_key_12345678901234567890123456789012345'
os.environ['FLASK_ENV'] = 'development'
os.environ['DATABASE_URL'] = 'sqlite:///hostel.db'

def test_imports():
    """Test that all critical modules can be imported"""
    print("🔍 Testing Module Imports...")
    
    try:
        import flask
        print("  ✅ Flask imported successfully")
    except ImportError as e:
        print(f"  ❌ Flask import failed: {e}")
        return False
    
    try:
        import socket_events
        print("  ✅ Socket.IO events imported successfully")
    except ImportError as e:
        print(f"  ❌ Socket.IO events import failed: {e}")
        return False
    
    try:
        from routes.health import health_check
        print("  ✅ Health check imported successfully")
    except ImportError as e:
        print(f"  ❌ Health check import failed: {e}")
        return False
    
    try:
        from db_utils import get_db_connection
        print("  ✅ Database utils imported successfully")
    except ImportError as e:
        print(f"  ❌ Database utils import failed: {e}")
        return False
    
    return True

def test_database():
    """Test database connectivity"""
    print("\n💾 Testing Database Connectivity...")
    
    try:
        # Test direct SQLite connection without Flask context
        import sqlite3
        import os
        
        # Get database path
        database_url = os.environ.get('DATABASE_URL', 'sqlite:///hostel.db')
        if database_url.startswith('sqlite:///'):
            db_path = database_url.replace('sqlite:///', '')
        else:
            db_path = 'hostel.db'
        
        # Make path absolute
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        print(f"  ✅ Database connected successfully, found {len(tables)} tables")
        return True
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False

def test_redis_connection():
    """Test Redis connectivity (optional)"""
    print("\n🔴 Testing Redis Connectivity...")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("  ✅ Redis connected successfully")
        return True
    except Exception as e:
        print(f"  ⚠️ Redis connection failed (optional): {e}")
        return False  # Redis is optional for basic functionality

def main():
    print("🚀 Quick Application Test")
    print("=" * 50)
    
    # Test imports
    imports_ok = test_imports()
    
    # Test database
    db_ok = test_database()
    
    # Test Redis (optional)
    redis_ok = test_redis_connection()
    
    print("\n📊 Test Results:")
    print(f"  • Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"  • Database: {'✅ PASS' if db_ok else '❌ FAIL'}")
    print(f"  • Redis: {'✅ PASS' if redis_ok else '⚠️ OPTIONAL'}")
    
    if imports_ok and db_ok:
        print("\n🎉 Application is ready to run!")
        print("To start the application:")
        print("  python app.py")
        return True
    else:
        print("\n❌ Application has critical issues that need to be resolved")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
