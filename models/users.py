"""
User model for authentication and authorization.
"""
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from models.db import get_db

class User:
    ROLE_OWNER = 'owner'
    ROLE_MANAGER = 'manager'
    
    def __init__(self, id=None, username=None, password_hash=None, full_name=None, role=None, hostel_id=None, email=None, created_at=None, hostel_name=None): # Added hostel_name
        self.id = id
        self.username = username
        self.password_hash = password_hash  # Stored hashed
        self.full_name = full_name
        self.role = role
        self.hostel_id = hostel_id  # None for owner (all hostels)
        self.email = email
        self.created_at = created_at
        self.hostel_name = hostel_name # Initialize hostel_name
        
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID."""
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT id, username, password_hash, full_name, role, hostel_id, email FROM users WHERE id = ?', 
                      (user_id,))
        user_data = cursor.fetchone()
        
        if user_data:
            return User(
                id=user_data[0],
                username=user_data[1],
                password_hash=user_data[2],
                full_name=user_data[3],
                role=user_data[4],
                hostel_id=user_data[5],
                email=user_data[6],
                created_at=None  # We don't have this column yet
            )
        return None
    
    @staticmethod
    def get_by_username(username):
        """Get user by username."""
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT id, username, password_hash, full_name, role, hostel_id, email FROM users WHERE username = ?', 
                       (username,))
        user_data = cursor.fetchone()
        
        if user_data:
            return User(
                id=user_data[0],
                username=user_data[1],
                password_hash=user_data[2],
                full_name=user_data[3],
                role=user_data[4],
                hostel_id=user_data[5],
                email=user_data[6],
                created_at=None  
            )
        return None
    
    @staticmethod
    def create_user(username, password, full_name, role, hostel_id=None, email=None):
        """Create a new user."""
        db = get_db()
        cursor = db.cursor()
        
        # Hash the password
        password_hash = generate_password_hash(password)
        
        cursor.execute(
            'INSERT INTO users (username, password_hash, full_name, role, hostel_id, email) VALUES (?, ?, ?, ?, ?, ?)',
            (username, password_hash, full_name, role, hostel_id, email)
        )
        db.commit()
        return cursor.lastrowid
    
    @staticmethod
    def get_all_managers():
        """Get all users with manager role."""
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            SELECT u.id, u.username, u.password_hash, u.full_name, u.role, u.hostel_id, u.email, h.name as hostel_name  
            FROM users u  
            LEFT JOIN hostels h ON u.hostel_id = h.id  
            WHERE u.role = ?  
            ORDER BY u.username  
        ''', (User.ROLE_MANAGER,))
        
        managers = []
        for row in cursor.fetchall():
            user = User(
                id=row[0],
                username=row[1],
                password_hash=row[2],
                full_name=row[3],
                role=row[4],
                hostel_id=row[5],
                email=row[6],
                created_at=None,  
                hostel_name=row[7] # Assign hostel_name from query
            )
            managers.append(user)
            
        return managers
    
    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)
    
    def update(self, full_name=None, hostel_id=None, email=None):
        """Update user details."""
        db = get_db()
        cursor = db.cursor()
        
        updates = []
        params = []
        
        if full_name is not None:
            updates.append('full_name = ?')
            params.append(full_name)
            self.full_name = full_name
            
        if hostel_id is not None:
            updates.append('hostel_id = ?')
            params.append(hostel_id)
            self.hostel_id = hostel_id
            
        if email is not None:
            updates.append('email = ?')
            params.append(email)
            self.email = email
            
        if not updates:
            return False
            
        query = f'UPDATE users SET {", ".join(updates)} WHERE id = ?'
        params.append(self.id)
        
        cursor.execute(query, params)
        db.commit()
        return True
    
    def change_password(self, new_password):
        """Change user's password."""
        db = get_db()
        cursor = db.cursor()
        
        password_hash = generate_password_hash(new_password)
        self.password_hash = password_hash
        
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, self.id))
        db.commit()
        return True
