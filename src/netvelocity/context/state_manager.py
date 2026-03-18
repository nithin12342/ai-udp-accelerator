"""
Context Engineering: State Manager
===================================
Redis-based rapid state retrieval for the NetVelocity AI rate-controller.
Manages real-time state and history for context engineering.

Key Features:
- Redis-backed state storage
- State versioning and history
- Rapid retrieval for ML inference
- Connection pooling
"""

import json
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import threading


class StateKey(Enum):
    """Enumeration of state keys for consistent naming."""
    TELEMETRY_CURRENT = "netvelocity:telemetry:current"
    TELEMETRY_HISTORY = "netvelocity:telemetry:history"
    RATE_CONTROLLER_STATE = "netvelocity:rate_controller:state"
    CONNECTION_STATE = "netvelocity:connection:state"
    MODEL_INFERENCE_STATE = "netvelocity:model:inference"
    SESSION_STATE = "netvelocity:session:state"


@dataclass
class ConnectionState:
    """State of a network connection."""
    connection_id: str
    source_ip: str
    source_port: int
    dest_ip: str
    dest_port: int
    protocol: str  # UDP, TCP
    state: str  # CONNECTED, DISCONNECTED, etc.
    bytes_sent: int = 0
    bytes_received: int = 0
    packets_sent: int = 0
    packets_received: int = 0
    packets_lost: int = 0
    created_at: float = 0.0
    last_activity: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectionState':
        return cls(**data)


@dataclass
class RateControllerState:
    """State of the AI rate controller."""
    controller_id: str
    current_rate_mbps: float
    target_rate_mbps: float
    intent: str  # The declared intent
    model_version: str
    last_inference_time: float = 0.0
    inference_count: int = 0
    optimal_rate_mbps: float = 0.0
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RateControllerState':
        return cls(**data)


class StateManager:
    """
    Redis-backed state manager for rapid state retrieval.
    
    Provides high-performance state management with:
    - Connection pooling
    - Automatic serialization/deserialization
    - State history tracking
    - Thread-safe operations
    """
    
    def __init__(self, 
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 redis_db: int = 0,
                 password: Optional[str] = None,
                 use_redis: bool = False):  # Mock mode if Redis unavailable
        """
        Initialize the state manager.
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            password: Redis password (optional)
            use_redis: Whether to use actual Redis (False = in-memory mock)
        """
        self.use_redis = use_redis
        self._redis_client = None
        self._memory_store: Dict[str, Any] = {}
        self._history_store: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = threading.RLock()
        
        if use_redis:
            try:
                import redis
                self._redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                self._redis_client.ping()
            except ImportError:
                print("Redis not available, using in-memory store")
                self.use_redis = False
            except Exception as e:
                print(f"Redis connection failed: {e}, using in-memory store")
                self.use_redis = False
    
    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        if hasattr(value, 'to_dict'):
            return json.dumps(value.to_dict())
        return json.dumps(value)
    
    def _deserialize(self, data: str, target_type: Optional[type] = None) -> Any:
        """Deserialize JSON string to object."""
        parsed = json.loads(data)
        if target_type and hasattr(target_type, 'from_dict'):
            return target_type.from_dict(parsed)
        return parsed
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a state value.
        
        Args:
            key: State key
            value: Value to store
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            True if successful
        """
        with self._lock:
            serialized = self._serialize(value)
            
            if self.use_redis and self._redis_client:
                try:
                    if ttl:
                        self._redis_client.setex(key, ttl, serialized)
                    else:
                        self._redis_client.set(key, serialized)
                    return True
                except Exception as e:
                    print(f"Redis set error: {e}")
            
            # Fallback to memory store
            self._memory_store[key] = {
                'value': serialized,
                'timestamp': time.time()
            }
            
            # Add to history
            if key not in self._history_store:
                self._history_store[key] = []
            self._history_store[key].append({
                'value': serialized,
                'timestamp': time.time()
            })
            
            # Keep only last 1000 history entries
            if len(self._history_store[key]) > 1000:
                self._history_store[key] = self._history_store[key][-1000:]
            
            return True
    
    def get(self, key: str, target_type: Optional[type] = None) -> Optional[Any]:
        """
        Get a state value.
        
        Args:
            key: State key
            target_type: Target type for deserialization (optional)
            
        Returns:
            Stored value or None
        """
        with self._lock:
            if self.use_redis and self._redis_client:
                try:
                    data = self._redis_client.get(key)
                    if data:
                        return self._deserialize(data, target_type)
                    return None
                except Exception as e:
                    print(f"Redis get error: {e}")
            
            # Fallback to memory store
            if key in self._memory_store:
                return self._deserialize(
                    self._memory_store[key]['value'], 
                    target_type
                )
            return None
    
    def get_history(self, key: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get state history.
        
        Args:
            key: State key
            limit: Maximum number of history entries
            
        Returns:
            List of historical values
        """
        with self._lock:
            if key in self._history_store:
                return self._history_store[key][-limit:]
            return []
    
    def delete(self, key: str) -> bool:
        """Delete a state key."""
        with self._lock:
            if self.use_redis and self._redis_client:
                try:
                    self._redis_client.delete(key)
                except Exception:
                    pass
            
            if key in self._memory_store:
                del self._memory_store[key]
            if key in self._history_store:
                del self._history_store[key]
            
            return True
    
    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if self.use_redis and self._redis_client:
            try:
                return bool(self._redis_client.exists(key))
            except Exception:
                pass
        
        return key in self._memory_store
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        if self.use_redis and self._redis_client:
            try:
                return self._redis_client.keys(pattern)
            except Exception:
                pass
        
        # Memory store fallback
        import fnmatch
        return [k for k in self._memory_store.keys() if fnmatch.fnmatch(k, pattern)]
    
    # Convenience methods for NetVelocity-specific state
    
    def save_telemetry(self, telemetry: Dict[str, Any]) -> bool:
        """Save current telemetry state."""
        return self.set(StateKey.TELEMETRY_CURRENT.value, telemetry, ttl=300)
    
    def get_telemetry(self) -> Optional[Dict[str, Any]]:
        """Get current telemetry state."""
        return self.get(StateKey.TELEMETRY_CURRENT.value)
    
    def save_connection_state(self, state: ConnectionState) -> bool:
        """Save connection state."""
        key = f"{StateKey.CONNECTION_STATE.value}:{state.connection_id}"
        return self.set(key, state)
    
    def get_connection_state(self, connection_id: str) -> Optional[ConnectionState]:
        """Get connection state."""
        key = f"{StateKey.CONNECTION_STATE.value}:{connection_id}"
        return self.get(key, ConnectionState)
    
    def save_rate_controller_state(self, state: RateControllerState) -> bool:
        """Save rate controller state."""
        return self.set(StateKey.RATE_CONTROLLER_STATE.value, state)
    
    def get_rate_controller_state(self) -> Optional[RateControllerState]:
        """Get rate controller state."""
        return self.get(StateKey.RATE_CONTROLLER_STATE.value, RateControllerState)
    
    def close(self) -> None:
        """Close connections and cleanup."""
        if self.use_redis and self._redis_client:
            try:
                self._redis_client.close()
            except Exception:
                pass


# Module exports
__all__ = [
    'StateKey',
    'ConnectionState',
    'RateControllerState', 
    'StateManager'
]
