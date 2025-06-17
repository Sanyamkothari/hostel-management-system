"""
Initial User Setup Script for Hostel Management System
Creates owner and manager accounts for first-time deployment
"""
import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_utils import get_db_connection

def create_initial_users():
    """Create initial user accounts for owner and managers"""
    
    # User data for initial setup
    users = [
        {
            'username': 'owner',
            'password': 'owner123',  # Change this!
            'name': 'Hostel Owner',
            'role': 'owner',
            'email': 'owner@hostel.com'
        },
        {
            'username': 'manager1',
            'password': 'manager123',  # Change this!
            'name': 'Manager One',
            'role': 'manager',
            'email': 'manager1@hostel.com'
        },
        {
            'username': 'manager2',
            'password': 'manager123',  # Change this!
            'name': 'Manager Two',
            'role': 'manager',
            'email': 'manager2@hostel.com'
        }
    ]
    
    conn = get_db_connection()
    if not conn:
        print("❌ Could not connect to database")
        return False
    
    cursor = conn.cursor()
    
    try:
        for user in users:
            # Check if user already exists
            cursor.execute('SELECT id FROM users WHERE username = ?', (user['username'],))
            if cursor.fetchone():
                print(f"⚠️  User {user['username']} already exists, skipping...")
                continue
            
            # Hash the password
            hashed_password = generate_password_hash(user['password'])
            
            # Insert user
            cursor.execute('''
                INSERT INTO users (username, password_hash, name, role, email, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user['username'],
                hashed_password,
                user['name'],
                user['role'],
                user['email'],
                datetime.now().isoformat(),
                1
            ))
            
            print(f"✅ Created user: {user['username']} ({user['role']})")
        
        conn.commit()
        print("\n🎉 Initial users created successfully!")
        print("\n📋 Login Credentials:")
        print("=" * 40)
        for user in users:
            print(f"Username: {user['username']}")
            print(f"Password: {user['password']}")
            print(f"Role: {user['role']}")
            print("-" * 20)
        
        print("\n⚠️  IMPORTANT: Change these passwords after first login!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating users: {e}")
        conn.rollback()
        return False
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    # Set production environment
    os.environ['FLASK_ENV'] = 'production'
    
    print("🚀 Creating initial user accounts...")
    success = create_initial_users()
    
    if success:
        print("\n✅ Setup complete! You can now login to the application.")
    else:
        print("\n❌ Setup failed. Please check your database configuration.")
