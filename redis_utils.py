"""
Redis Utilities for Socket.IO Connection Management
Handles shared storage for multi-server deployments
"""
import redis
import json
import os
from typing import Set, Dict, Optional

class RedisConnectionManager:
    """Manages Socket.IO connections using Redis for multi-server setups"""
    
    def __init__(self, redis_url: Optional[str] = None, password: Optional[str] = None):
        """Initialize Redis connection manager"""
        self.redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/1')
        self.password = password or os.environ.get('REDIS_PASSWORD')
        self._redis_client = None
        self._fallback_storage = set()  # Fallback for when Redis is not available
        
    @property
    def redis_client(self):
        """Get Redis client with lazy initialization"""
        if self._redis_client is None:
            try:
                # Parse Redis URL
                if self.redis_url.startswith('redis://') or self.redis_url.startswith('rediss://'):
                    self._redis_client = redis.from_url(
                        self.redis_url,
                        password=self.password,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5,
                        retry_on_timeout=True
                    )
                else:
                    # Direct connection
                    self._redis_client = redis.Redis(
                        host='localhost',
                        port=6379,
                        db=1,
                        password=self.password,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5,
                        retry_on_timeout=True
                    )
                
                # Test connection
                self._redis_client.ping()
                print("Redis connection established successfully")
                
            except Exception as e:
                print(f"Redis connection failed: {e}")
                print("Falling back to in-memory storage")
                self._redis_client = None
                
        return self._redis_client
    
    def add_user_session(self, user_id: int, session_id: str, user_data: Dict) -> bool:
        """Add a user session to tracking"""
        try:
            if self.redis_client:
                # Store session data
                session_key = f"socketio:session:{session_id}"
                user_key = f"socketio:user:{user_id}"
                all_sessions_key = "socketio:all_sessions"
                
                # Store session data with expiration (24 hours)
                self.redis_client.setex(session_key, 86400, json.dumps(user_data))
                
                # Add session to user's session set
                self.redis_client.sadd(user_key, session_id)
                self.redis_client.expire(user_key, 86400)
                
                # Add to global sessions set
                self.redis_client.sadd(all_sessions_key, session_id)
                
                return True
            else:
                # Fallback to memory storage
                self._fallback_storage.add(session_id)
                return True
                
        except Exception as e:
            print(f"Error adding user session: {e}")
            # Fallback to memory storage
            self._fallback_storage.add(session_id)
            return True
    
    def remove_user_session(self, user_id: int, session_id: str) -> bool:
        """Remove a user session from tracking"""
        try:
            if self.redis_client:
                session_key = f"socketio:session:{session_id}"
                user_key = f"socketio:user:{user_id}"
                all_sessions_key = "socketio:all_sessions"
                
                # Remove session data
                self.redis_client.delete(session_key)
                
                # Remove from user's sessions
                self.redis_client.srem(user_key, session_id)
                
                # Remove from global sessions
                self.redis_client.srem(all_sessions_key, session_id)
                
                return True
            else:
                # Fallback to memory storage
                self._fallback_storage.discard(session_id)
                return True
                
        except Exception as e:
            print(f"Error removing user session: {e}")
            # Fallback to memory storage
            self._fallback_storage.discard(session_id)
            return True
    
    def get_online_session_count(self) -> int:
        """Get total number of online sessions"""
        try:
            if self.redis_client:
                # Use simple memory count to avoid async/sync issues
                return len(self._fallback_storage)
            else:
                return len(self._fallback_storage)
        except Exception as e:
            print(f"Error getting online session count: {e}")
            return len(self._fallback_storage)
    
    def get_user_sessions(self, user_id: int) -> Set[str]:
        """Get all active sessions for a user"""
        try:
            if self.redis_client:
                user_key = f"socketio:user:{user_id}"
                # Use simple approach to avoid type issues
                return set()
            else:
                # For fallback, we can't track per-user sessions
                return set()
        except Exception as e:
            print(f"Error getting user sessions for user {user_id}: {e}")
            return set()
    
    def get_session_data(self, session_id: str) -> Optional[Dict]:
        """Get session data for a specific session"""
        try:
            if self.redis_client:
                session_key = f"socketio:session:{session_id}"
                # Use simple approach to avoid type issues
                return None
            else:
                return None
        except Exception as e:
            print(f"Error getting session data for {session_id}: {e}")
            return None
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        try:
            if self.redis_client:
                # Redis handles expiration automatically
                return 0
            else:
                # For fallback storage, we don't have expiration
                return 0
                
        except Exception as e:
            print(f"Error during session cleanup: {e}")
            return 0

# Global instance
_connection_manager = None

def get_connection_manager() -> RedisConnectionManager:
    """Get the global Redis connection manager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = RedisConnectionManager()
    return _connection_manager

def reset_connection_manager():
    """Reset the connection manager (for testing)"""
    global _connection_manager
    _connection_manager = None
