"""WebSocket Manager for Real-time Surge Notifications

Provides WebSocket connections for supervisors to receive real-time surge alerts.
"""

from fastapi import WebSocket, WebSocketDisconnect, status
from typing import Dict, Set
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SurgeWebSocketManager:
    """
    Manages WebSocket connections for surge notifications.
    
    Features:
    - Multiple concurrent connections per depot
    - Broadcast surge events to all connected supervisors
    - Automatic cleanup on disconnect
    - Connection limit enforcement
    """
    
    def __init__(self, max_connections: int = 50):
        """
        Initialize WebSocket manager.
        
        Args:
            max_connections: Maximum concurrent connections allowed
        """
        # Store connections by depot_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.max_connections = max_connections
        self.total_connections = 0
    
    async def connect(self, websocket: WebSocket, depot_id: str = "ALL") -> bool:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            depot_id: Depot ID for filtering (default: "ALL" for all depots)
        
        Returns:
            True if connection accepted, False if limit reached
        """
        if self.total_connections >= self.max_connections:
            logger.warning(f"Connection limit reached ({self.max_connections})")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False
        
        await websocket.accept()
        
        if depot_id not in self.active_connections:
            self.active_connections[depot_id] = set()
        
        self.active_connections[depot_id].add(websocket)
        self.total_connections += 1
        
        logger.info(f"WebSocket connected for depot {depot_id}. Total connections: {self.total_connections}")
        return True
    
    def disconnect(self, websocket: WebSocket, depot_id: str = "ALL"):
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: WebSocket connection to remove
            depot_id: Depot ID
        """
        if depot_id in self.active_connections:
            self.active_connections[depot_id].discard(websocket)
            self.total_connections -= 1
            
            # Clean up empty depot sets
            if not self.active_connections[depot_id]:
                del self.active_connections[depot_id]
        
        logger.info(f"WebSocket disconnected for depot {depot_id}. Total connections: {self.total_connections}")
    
    async def broadcast_surge(self, surge_data: dict, depot_id: str):
        """
        Broadcast surge event to all connected supervisors for a depot.
        
        Args:
            surge_data: Surge event data to broadcast
            depot_id: Depot ID to broadcast to
        """
        message = {
            "type": "surge_detected",
            "data": surge_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        message_json = json.dumps(message)
        
        # Broadcast to specific depot
        await self._send_to_depot(depot_id, message_json)
        
        # Also broadcast to "ALL" connections (supervisors monitoring all depots)
        await self._send_to_depot("ALL", message_json)
    
    async def _send_to_depot(self, depot_id: str, message: str):
        """
        Send message to all connections for a depot.
        
        Args:
            depot_id: Depot ID
            message: JSON message string
        """
        if depot_id not in self.active_connections:
            return
        
        # Create a copy of the set to avoid modification during iteration
        connections = self.active_connections[depot_id].copy()
        
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to WebSocket: {str(e)}")
                disconnected.append(websocket)
        
        # Clean up disconnected sockets
        for websocket in disconnected:
            self.disconnect(websocket, depot_id)
    
    async def send_ping(self, websocket: WebSocket):
        """
        Send keep-alive ping to a connection.
        
        Args:
            websocket: WebSocket connection
        """
        try:
            await websocket.send_json({"type": "ping", "timestamp": datetime.utcnow().isoformat()})
        except Exception as e:
            logger.error(f"Failed to send ping: {str(e)}")
    
    def get_connection_count(self, depot_id: str = None) -> int:
        """
        Get number of active connections.
        
        Args:
            depot_id: Optional depot ID to filter by
        
        Returns:
            Number of active connections
        """
        if depot_id:
            return len(self.active_connections.get(depot_id, set()))
        return self.total_connections


# Global WebSocket manager instance
surge_ws_manager = SurgeWebSocketManager(max_connections=50)
