"""
Hostel model for managing multiple hostel properties.
"""
import sqlite3
from models.db import get_db_connection

class Hostel:
    def __init__(self, id=None, name=None, address=None, contact_person=None, contact_email=None, contact_number=None, created_at=None):
        self.id = id
        self.name = name
        self.address = address
        self.contact_person = contact_person
        self.contact_email = contact_email
        self.contact_number = contact_number
        self.created_at = created_at
    
    @staticmethod
    def get_by_id(hostel_id):
        """Get hostel by ID."""
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute('SELECT id, name, address, contact_person, contact_email, contact_number, created_at FROM hostels WHERE id = ?', 
                      (hostel_id,))
        hostel_data = cursor.fetchone()
        
        if hostel_data:
            return Hostel(
                id=hostel_data[0],
                name=hostel_data[1],
                address=hostel_data[2],
                contact_person=hostel_data[3],
                contact_email=hostel_data[4],
                contact_number=hostel_data[5],
                created_at=hostel_data[6]            )
        return None
    
    @staticmethod
    def get_hostel_name(hostel_id):
        """Get hostel name by ID."""
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute('SELECT name FROM hostels WHERE id = ?', (hostel_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    
    @staticmethod
    def get_all_hostels():
        """Get all hostels."""
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute('SELECT id, name, address, contact_person, contact_email, contact_number, created_at FROM hostels ORDER BY name')
        
        hostels = []
        for row in cursor.fetchall():
            hostel = Hostel(
                id=row[0],
                name=row[1],
                address=row[2],
                contact_person=row[3],
                contact_email=row[4],
                contact_number=row[5],
                created_at=row[6]
            )
            hostels.append(hostel)
            
        return hostels

    @staticmethod
    def create_hostel(name, address, contact_person=None, contact_email=None, contact_number=None):
        """Create a new hostel."""
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute(
            'INSERT INTO hostels (name, address, contact_person, contact_email, contact_number) VALUES (?, ?, ?, ?, ?)',
            (name, address, contact_person, contact_email, contact_number)
        )
        db.commit()
        return cursor.lastrowid

    def update(self):
        """Update hostel details."""
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute(
            'UPDATE hostels SET name = ?, address = ?, contact_person = ?, contact_email = ?, contact_number = ? WHERE id = ?',
            (self.name, self.address, self.contact_person, self.contact_email, self.contact_number, self.id)
        )
        db.commit()
        return True
    
    def delete(self):
        """Delete a hostel (only if it has no associated data)."""
        db = get_db_connection()
        cursor = db.cursor()
        
        # Check if hostel has any associated data
        tables = ['students', 'rooms', 'fees', 'complaints']
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table} WHERE hostel_id = ?', (self.id,))
            count = cursor.fetchone()[0]
            if count > 0:
                return False, f"Cannot delete hostel: {count} {table} records are associated with it"
        
        # Check if any managers are assigned to this hostel
        cursor.execute('SELECT COUNT(*) FROM users WHERE hostel_id = ?', (self.id,))
        count = cursor.fetchone()[0]
        if count > 0:
            return False, f"Cannot delete hostel: {count} managers are assigned to it"
        
        # Delete the hostel
        cursor.execute('DELETE FROM hostels WHERE id = ?', (self.id,))
        db.commit()
        return True, "Hostel deleted successfully"
        
    @staticmethod
    def get_dashboard_stats(hostel_id=None):
        """Get dashboard statistics for a hostel or all hostels."""
        db = get_db_connection()
        cursor = db.cursor()
        
        # Base conditions for queries
        condition = "WHERE hostel_id = ?" if hostel_id else ""
        params = (hostel_id,) if hostel_id else ()
        
        # Get room statistics
        # Total rooms
        cursor.execute(f'SELECT COUNT(*) FROM rooms {condition}', params)
        total_rooms = cursor.fetchone()[0] or 0

        # Occupied rooms (count rooms that have at least one student)
        if hostel_id:
            cursor.execute('SELECT COUNT(DISTINCT room_id) FROM students WHERE hostel_id = ? AND room_id IS NOT NULL', (hostel_id,))
        else:
            cursor.execute('SELECT COUNT(DISTINCT room_id) FROM students WHERE room_id IS NOT NULL')
        occupied_rooms = cursor.fetchone()[0] or 0
        vacant_rooms = total_rooms - occupied_rooms
        if vacant_rooms < 0:
            vacant_rooms = 0  # Prevent negative vacant rooms due to data inconsistencies
        
        # Get student count
        cursor.execute(f'SELECT COUNT(*) FROM students {condition}', params)
        total_students = cursor.fetchone()[0] or 0
        
        # Get pending fees
        if hostel_id:
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0.0) FROM fees WHERE status = 'Pending' AND hostel_id = ?", (hostel_id,))
        else:
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0.0) FROM fees WHERE status = 'Pending'")
        fee_data = cursor.fetchone()
        pending_fee_count = fee_data[0] or 0
        pending_fee_amount = float(fee_data[1]) if fee_data[1] is not None else 0.0  # Always return float
        
        # Get complaints count
        if hostel_id:
            cursor.execute("SELECT COUNT(*) FROM complaints WHERE status IN ('Pending', 'In Progress', 'Open') AND hostel_id = ?", (hostel_id,))
        else:
            cursor.execute("SELECT COUNT(*) FROM complaints WHERE status IN ('Pending', 'In Progress', 'Open')")
        open_complaints = int(cursor.fetchone()[0] or 0)

        return {
            'total_rooms': int(total_rooms),
            'vacant_rooms': int(vacant_rooms),
            'occupied_rooms': int(occupied_rooms),
            'occupancy_rate': (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0,
            'total_students': int(total_students),
            'pending_fee_count': int(pending_fee_count),
            'pending_fee_amount': pending_fee_amount,
            # 'total_complaints': total_complaints, # Uncomment if needed
            'open_complaints': int(open_complaints)
        }
