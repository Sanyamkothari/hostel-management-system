#!/usr/bin/env python3
"""
Production startup script for Hostel Management System
Handles environment setup, database initialization, and server startup
"""

import os
import sys
import subprocess
from pathlib import Path

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'SECRET_KEY',
        'DATABASE_URL',
        'FLASK_ENV'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file or environment")
        return False
    
    print("✅ All required environment variables are set")
    return True

def setup_directories():
    """Create necessary directories"""
    directories = ['logs', 'backups', 'uploads', 'static/uploads']
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Directory created/verified: {directory}")

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False
    return True

def initialize_database():
    """Initialize database if needed"""
    print("🗄️ Initializing database...")
    try:
        from models.db import init_db
        from migrations.migrate import run_migration
        
        # Check if database exists
        db_url = os.environ.get('DATABASE_URL', 'sqlite:///hostel.db')
        if 'sqlite' in db_url:
            db_path = db_url.replace('sqlite:///', '')
            if not os.path.exists(db_path):
                print("Creating new SQLite database...")
                init_db()
                run_migration()
        else:
            # For PostgreSQL, assume it's already set up
            print("Using existing PostgreSQL database")
            run_migration()  # Apply any pending migrations
        
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False

def start_production_server():
    """Start the production server using Gunicorn"""
    print("🚀 Starting production server...")
    
    # Gunicorn configuration
    gunicorn_config = [
        'gunicorn',
        '--bind', '0.0.0.0:5000',
        '--workers', os.environ.get('GUNICORN_WORKERS', '4'), # Allow overriding worker count via env var
        '--worker-class', 'eventlet',
        '--timeout', '120',
        '--keepalive', '5',
        '--max-requests', '1000',
        '--max-requests-jitter', '100',
        '--access-logfile', '-',  # Log to stdout
        '--error-logfile', '-',   # Log to stderr
        '--log-level', os.environ.get('GUNICORN_LOG_LEVEL', 'info'), # Allow overriding log level
        'app:app'
    ]
    
    try:
        print(f"Attempting to start Gunicorn with command: {' '.join(gunicorn_config)}")
        subprocess.run(gunicorn_config, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting Gunicorn production server: {e}")
        # Removed fallback to Flask development server
        # If Gunicorn fails, the container should ideally exit and be restarted by an orchestrator.
        sys.exit(1) # Exit with error code
    except FileNotFoundError:
        print("❌ Gunicorn command not found. Ensure Gunicorn is installed and in PATH.")
        sys.exit(1)

def start_development_server():
    """Start the development server"""
    print("🚀 Starting development server...")
    os.system('python app.py')

def main():
    """Main startup function"""
    print("🏨 Hostel Management System - Production Startup")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Setup directories
    setup_directories()
    
    # Install dependencies (optional in production)
    if os.environ.get('SKIP_INSTALL') != 'true':
        if not install_dependencies():
            print("⚠️ Continuing without installing dependencies...")
    
    # Initialize database
    if not initialize_database():
        print("❌ Database initialization failed. Exiting...")
        sys.exit(1)
    
    # Determine server type
    env = os.environ.get('FLASK_ENV', 'development')
    
    if env == 'production':
        start_production_server()
    else:
        start_development_server()

if __name__ == '__main__':
    main()
