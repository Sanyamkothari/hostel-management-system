"""
Simplified Room Management System
This module provides basic room management functionality with minimal complexity
"""

import sqlite3
from datetime import date
from .db import get_db_connection


class SimpleRoomModel:
    """Simple Room Model with basic CRUD operations only."""
    
    # Basic room statuses
    STATUS_AVAILABLE = 'Available'
    STATUS_FULL = 'Full'
    STATUS_MAINTENANCE = 'Maintenance'
    
    VALID_STATUSES = [STATUS_AVAILABLE, STATUS_FULL, STATUS_MAINTENANCE]
    
    @staticmethod
    def get_all_rooms(hostel_id=None):
        """Get all rooms with basic information."""
        conn = get_db_connection()
        try:
            if hostel_id:
                query = '''
                    SELECT r.id, r.room_number, r.capacity, r.current_occupancy, r.status, 
                           r.hostel_id, h.name as hostel_name
                    FROM rooms r
                    LEFT JOIN hostels h ON r.hostel_id = h.id
                    WHERE r.hostel_id = ?
                    ORDER BY r.room_number
                '''
                rooms = conn.execute(query, (hostel_id,)).fetchall()
            else:
                query = '''
                    SELECT r.id, r.room_number, r.capacity, r.current_occupancy, r.status, 
                           r.hostel_id, h.name as hostel_name
                    FROM rooms r
                    LEFT JOIN hostels h ON r.hostel_id = h.id
                    ORDER BY r.room_number
                '''
                rooms = conn.execute(query).fetchall()
            
            # Convert to list of dicts with basic calculated fields
            room_list = []
            for room in rooms:
                room_dict = dict(room)
                # Calculate simple occupancy percentage
                if room_dict['capacity'] > 0:
                    room_dict['occupancy_percentage'] = round((room_dict['current_occupancy'] / room_dict['capacity']) * 100, 1)
                else:
                    room_dict['occupancy_percentage'] = 0
                room_list.append(room_dict)
            
            return room_list
            
        finally:
            conn.close()
    
    @staticmethod
    def get_room_by_id(room_id):
        """Get a single room by ID."""
        conn = get_db_connection()
        try:
            room = conn.execute('''
                SELECT r.*, h.name as hostel_name
                FROM rooms r
                LEFT JOIN hostels h ON r.hostel_id = h.id
                WHERE r.id = ?
            ''', (room_id,)).fetchone()
            
            if room:
                return dict(room)
            return None
            
        finally:
            conn.close()
    
    @staticmethod
    def add_room(room_number, capacity, hostel_id, status=STATUS_AVAILABLE):
        """Add a new room."""
        # Basic validation
        if not room_number or not room_number.strip():
            return {'success': False, 'error': 'Room number is required'}
        
        if not capacity or capacity <= 0:
            return {'success': False, 'error': 'Capacity must be a positive number'}
        
        if status not in SimpleRoomModel.VALID_STATUSES:
            return {'success': False, 'error': f'Status must be one of: {", ".join(SimpleRoomModel.VALID_STATUSES)}'}
        
        conn = get_db_connection()
        try:
            # Check if room number already exists
            existing = conn.execute(
                'SELECT id FROM rooms WHERE room_number = ? AND hostel_id = ?',
                (room_number.strip(), hostel_id)
            ).fetchone()
            
            if existing:
                return {'success': False, 'error': 'Room number already exists in this hostel'}
            
            # Insert new room
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO rooms (room_number, capacity, status, hostel_id, current_occupancy) 
                VALUES (?, ?, ?, ?, 0)
            ''', (room_number.strip(), capacity, status, hostel_id))
            
            room_id = cursor.lastrowid
            conn.commit()
            
            return {
                'success': True, 
                'room_id': room_id,
                'message': f'Room {room_number} added successfully'
            }
            
        except sqlite3.Error as e:
            return {'success': False, 'error': f'Database error: {str(e)}'}
        finally:
            conn.close()
    
    @staticmethod
    def update_room(room_id, room_number, capacity, status):
        """Update an existing room."""
        # Basic validation
        if not room_number or not room_number.strip():
            return {'success': False, 'error': 'Room number is required'}
        
        if not capacity or capacity <= 0:
            return {'success': False, 'error': 'Capacity must be a positive number'}
        
        if status not in SimpleRoomModel.VALID_STATUSES:
            return {'success': False, 'error': f'Status must be one of: {", ".join(SimpleRoomModel.VALID_STATUSES)}'}
        
        conn = get_db_connection()
        try:
            # Check if room exists
            room = conn.execute('SELECT * FROM rooms WHERE id = ?', (room_id,)).fetchone()
            if not room:
                return {'success': False, 'error': 'Room not found'}
            
            room = dict(room)
            
            # Check if new capacity is valid (can't be less than current occupancy)
            if capacity < room['current_occupancy']:
                return {
                    'success': False, 
                    'error': f'Capacity ({capacity}) cannot be less than current occupancy ({room["current_occupancy"]})'
                }
            
            # Check if room number conflicts with another room in same hostel
            existing = conn.execute(
                'SELECT id FROM rooms WHERE room_number = ? AND hostel_id = ? AND id != ?',
                (room_number.strip(), room['hostel_id'], room_id)
            ).fetchone()
            
            if existing:
                return {'success': False, 'error': 'Room number already exists in this hostel'}
            
            # Update room
            conn.execute('''
                UPDATE rooms SET room_number = ?, capacity = ?, status = ? 
                WHERE id = ?
            ''', (room_number.strip(), capacity, status, room_id))
            conn.commit()
            
            # Update occupancy status if needed
            SimpleRoomModel._update_room_status(conn, room_id)
            
            return {
                'success': True,
                'message': f'Room {room_number} updated successfully'
            }
            
        except sqlite3.Error as e:
            return {'success': False, 'error': f'Database error: {str(e)}'}
        finally:
            conn.close()
    
    @staticmethod
    def delete_room(room_id):
        """Delete a room."""
        conn = get_db_connection()
        try:
            # Check if room exists
            room = conn.execute('SELECT * FROM rooms WHERE id = ?', (room_id,)).fetchone()
            if not room:
                return {'success': False, 'error': 'Room not found'}
            
            room = dict(room)
            
            # Check for current occupants
            occupants = conn.execute(
                'SELECT COUNT(*) as count FROM students WHERE room_id = ?', (room_id,)
            ).fetchone()['count']
            
            if occupants > 0:
                return {
                    'success': False, 
                    'error': f'Cannot delete room {room["room_number"]}: It has {occupants} student(s). Please reassign students first.'
                }
            
            # Delete room
            conn.execute('DELETE FROM rooms WHERE id = ?', (room_id,))
            conn.commit()
            
            return {
                'success': True,
                'message': f'Room {room["room_number"]} deleted successfully'
            }
            
        except sqlite3.Error as e:
            return {'success': False, 'error': f'Database error: {str(e)}'}
        finally:
            conn.close()
    
    @staticmethod
    def get_available_rooms(hostel_id=None):
        """Get rooms available for assignment."""
        conn = get_db_connection()
        try:
            query = '''
                SELECT r.id, r.room_number, r.capacity, r.current_occupancy, 
                       (r.capacity - r.current_occupancy) as available_spots,
                       h.name as hostel_name
                FROM rooms r
                LEFT JOIN hostels h ON r.hostel_id = h.id
                WHERE r.status = ? AND r.current_occupancy < r.capacity
            '''
            params = [SimpleRoomModel.STATUS_AVAILABLE]
            
            if hostel_id:
                query += ' AND r.hostel_id = ?'
                params.append(hostel_id)
            
            query += ' ORDER BY r.room_number'
            
            rooms = conn.execute(query, params).fetchall()
            return [dict(room) for room in rooms]
            
        finally:
            conn.close()
    
    @staticmethod
    def get_room_occupants(room_id):
        """Get students in a room."""
        conn = get_db_connection()
        try:
            occupants = conn.execute('''
                SELECT id, name, student_id_number, course, contact, email
                FROM students 
                WHERE room_id = ?
                ORDER BY name
            ''', (room_id,)).fetchall()
            
            return [dict(occupant) for occupant in occupants]
            
        finally:
            conn.close()
    
    @staticmethod
    def get_room_stats(hostel_id=None):
        """Get basic room statistics."""
        conn = get_db_connection()
        try:
            base_query = 'SELECT {} FROM rooms'
            where_clause = ''
            params = []
            
            if hostel_id:
                where_clause = ' WHERE hostel_id = ?'
                params = [hostel_id]
            
            # Basic counts
            total_rooms = conn.execute(f"{base_query.format('COUNT(*)')}{where_clause}", params).fetchone()[0]
            
            available_rooms = conn.execute(
                f"{base_query.format('COUNT(*)')}{where_clause}{' AND' if where_clause else ' WHERE'} status = ?",
                params + [SimpleRoomModel.STATUS_AVAILABLE]
            ).fetchone()[0]
            
            full_rooms = conn.execute(
                f"{base_query.format('COUNT(*)')}{where_clause}{' AND' if where_clause else ' WHERE'} status = ?",
                params + [SimpleRoomModel.STATUS_FULL]
            ).fetchone()[0]
            
            maintenance_rooms = conn.execute(
                f"{base_query.format('COUNT(*)')}{where_clause}{' AND' if where_clause else ' WHERE'} status = ?",
                params + [SimpleRoomModel.STATUS_MAINTENANCE]
            ).fetchone()[0]
            
            # Capacity and occupancy
            total_capacity = conn.execute(
                f"{base_query.format('SUM(capacity)')}{where_clause}", params
            ).fetchone()[0] or 0
            
            current_occupancy = conn.execute(
                f"{base_query.format('SUM(current_occupancy)')}{where_clause}", params
            ).fetchone()[0] or 0
            
            return {
                'total_rooms': total_rooms,
                'available_rooms': available_rooms,
                'full_rooms': full_rooms,
                'maintenance_rooms': maintenance_rooms,
                'total_capacity': total_capacity,
                'current_occupancy': current_occupancy,
                'available_spots': total_capacity - current_occupancy,
                'occupancy_percentage': round((current_occupancy / total_capacity * 100), 1) if total_capacity > 0 else 0
            }
            
        finally:
            conn.close()
    
    @staticmethod
    def _update_room_status(conn, room_id):
        """Update room status based on occupancy (internal helper)."""
        try:
            # Get current occupancy
            result = conn.execute(
                'SELECT capacity, current_occupancy, status FROM rooms WHERE id = ?', 
                (room_id,)
            ).fetchone()
            
            if not result:
                return
            
            capacity = result['capacity']
            current_occupancy = result['current_occupancy']
            current_status = result['status']
            
            # Only auto-update status if not in maintenance
            if current_status != SimpleRoomModel.STATUS_MAINTENANCE:
                if current_occupancy == 0:
                    new_status = SimpleRoomModel.STATUS_AVAILABLE
                elif current_occupancy >= capacity:
                    new_status = SimpleRoomModel.STATUS_FULL
                else:
                    new_status = SimpleRoomModel.STATUS_AVAILABLE
                
                # Update status
                conn.execute(
                    'UPDATE rooms SET status = ? WHERE id = ?', 
                    (new_status, room_id)
                )
                conn.commit()
                
        except Exception as e:
            print(f"Error updating room status for room {room_id}: {str(e)}")
    
    @staticmethod
    def update_room_occupancy(room_id):
        """Update room occupancy count and status."""
        conn = get_db_connection()
        try:
            # Calculate current occupancy
            result = conn.execute(
                'SELECT COUNT(*) as count FROM students WHERE room_id = ?', 
                (room_id,)
            ).fetchone()
            current_occupancy = result['count'] if result else 0
            
            # Update occupancy
            conn.execute(
                'UPDATE rooms SET current_occupancy = ? WHERE id = ?', 
                (current_occupancy, room_id)
            )
            conn.commit()
            
            # Update status
            SimpleRoomModel._update_room_status(conn, room_id)
            
        except Exception as e:
            print(f"Error updating room occupancy for room {room_id}: {str(e)}")
        finally:
            conn.close()
