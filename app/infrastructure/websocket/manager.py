"""WebSocket connection manager"""
from typing import Dict, Set, List
from fastapi import WebSocket
import json
import asyncio


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        # Store active connections: {user_id: {websocket1, websocket2, ...}}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store connections by ticket: {ticket_id: {websocket1, websocket2, ...}}
        self.ticket_connections: Dict[str, Set[WebSocket]] = {}
        # Store user info for connections: {websocket: {user_id, user_role}}
        self.connection_info: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, user_role: str):
        """Register a new WebSocket connection (connection should already be accepted)"""
        # Store connection info
        self.connection_info[websocket] = {
            "user_id": user_id,
            "user_role": user_role
        }
        
        # Add to user connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        # Log only important connections
        if len(self.active_connections[user_id]) == 1:
            print(f"✅ WebSocket connected: user_id={user_id}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        try:
            if websocket not in self.connection_info:
                return
            
            user_id = self.connection_info[websocket]["user_id"]
            
            # Remove from user connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove from ticket connections
            for ticket_id in list(self.ticket_connections.keys()):
                if websocket in self.ticket_connections[ticket_id]:
                    self.ticket_connections[ticket_id].discard(websocket)
                    if not self.ticket_connections[ticket_id]:
                        del self.ticket_connections[ticket_id]
            
            # Remove connection info
            del self.connection_info[websocket]
            
            # Log only if this was the last connection for the user
            if user_id not in self.active_connections or not self.active_connections[user_id]:
                print(f"🔌 WebSocket disconnected: user_id={user_id}")
        except Exception as e:
            print(f"❌ Error during disconnect: {e}")
            import traceback
            traceback.print_exc()
    
    async def subscribe_to_ticket(self, websocket: WebSocket, ticket_id: str):
        """Subscribe a connection to a specific ticket"""
        if ticket_id not in self.ticket_connections:
            self.ticket_connections[ticket_id] = set()
        self.ticket_connections[ticket_id].add(websocket)
        user_info = self.connection_info.get(websocket, {})
        user_id = user_info.get("user_id", "unknown")
        # Reduced logging
        pass
    
    async def unsubscribe_from_ticket(self, websocket: WebSocket, ticket_id: str):
        """Unsubscribe a connection from a specific ticket"""
        if ticket_id in self.ticket_connections:
            self.ticket_connections[ticket_id].discard(websocket)
            if not self.ticket_connections[ticket_id]:
                del self.ticket_connections[ticket_id]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific connection"""
        try:
            # Check if websocket is still connected (if client_state is available)
            try:
                if hasattr(websocket, 'client_state') and websocket.client_state.name != "CONNECTED":
                    # Silently disconnect broken connections
                    self.disconnect(websocket)
                    return
            except AttributeError:
                # client_state might not be available, continue anyway
                pass
            
            await websocket.send_json(message)
        except Exception as e:
            # Silently disconnect broken connections
            self.disconnect(websocket)
            raise  # Re-raise to let caller know send failed
    
    async def broadcast_to_user(self, message: dict, user_id: str):
        """Broadcast a message to all connections of a specific user"""
        if user_id not in self.active_connections:
            return
        
        disconnected = []
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                # Silently handle disconnected websockets
                disconnected.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_to_ticket(self, message: dict, ticket_id: str):
        """Broadcast a message to all connections subscribed to a ticket"""
        if ticket_id not in self.ticket_connections:
            return
        
        subscribers_count = len(self.ticket_connections[ticket_id])
        
        disconnected = []
        sent_count = 0
        for websocket in list(self.ticket_connections[ticket_id]):
            try:
                # Check if websocket is still connected before sending
                try:
                    if hasattr(websocket, 'client_state') and websocket.client_state.name != "CONNECTED":
                        disconnected.append(websocket)
                        continue
                except AttributeError:
                    pass
                
                await websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                # Silently handle disconnected websockets
                disconnected.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all active connections"""
        disconnected = []
        for user_id, connections in list(self.active_connections.items()):
            for websocket in list(connections):
                try:
                    # Check if websocket is still connected before sending
                    try:
                        if hasattr(websocket, 'client_state') and websocket.client_state.name != "CONNECTED":
                            disconnected.append(websocket)
                            continue
                    except AttributeError:
                        pass
                    
                    await websocket.send_json(message)
                except Exception as e:
                    # Silently handle disconnected websockets
                    disconnected.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_to_role(self, message: dict, role: str):
        """Broadcast a message to all connections with a specific role"""
        disconnected = []
        sent_count = 0
        total_count = 0
        
        for websocket, info in list(self.connection_info.items()):
            if info.get("user_role") == role:
                total_count += 1
                try:
                    # Check if websocket is still connected before sending
                    try:
                        if hasattr(websocket, 'client_state') and websocket.client_state.name != "CONNECTED":
                            disconnected.append(websocket)
                            continue
                    except AttributeError:
                        pass
                    
                    await websocket.send_json(message)
                    sent_count += 1
                except Exception as e:
                    # Silently handle disconnected websockets
                    disconnected.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_to_users(self, message: dict, user_ids: List[str]):
        """Broadcast a message to specific users by their IDs"""
        if not user_ids:
            return
        
        disconnected = []
        sent_count = 0
        
        for user_id in user_ids:
            if user_id not in self.active_connections:
                continue
            
            for websocket in list(self.active_connections[user_id]):
                try:
                    # Check if websocket is still connected before sending
                    try:
                        if hasattr(websocket, 'client_state') and websocket.client_state.name != "CONNECTED":
                            disconnected.append(websocket)
                            continue
                    except AttributeError:
                        pass
                    
                    await websocket.send_json(message)
                    sent_count += 1
                except Exception as e:
                    # Silently handle disconnected websockets
                    disconnected.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected:
            self.disconnect(websocket)


# Global connection manager instance
manager = ConnectionManager()

