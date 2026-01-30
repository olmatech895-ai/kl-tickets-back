"""WebSocket router for real-time updates"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.infrastructure.websocket import manager
from app.infrastructure.security.jwt import decode_access_token
import json

router = APIRouter(tags=["websocket"], redirect_slashes=False)


async def get_current_user_ws(websocket: WebSocket):
    """Get current user from WebSocket token"""
    try:
        # Accept connection with proper headers for proxy support
        # This is important for WebSocket to work through reverse proxies (nginx, etc.)
        await websocket.accept()
        
        # Reduced logging
        pass
        
        # Get token from query parameter
        token = websocket.query_params.get("token")
        if not token:
            print("❌ WebSocket: No token in query params")
            await websocket.close(code=1008, reason="Missing authentication token")
            return None
        
        # Decode token
        try:
            payload = decode_access_token(token)
        except Exception as token_error:
            print(f"❌ WebSocket: Token decode error: {token_error}")
            await websocket.close(code=1008, reason="Invalid authentication token")
            return None
            
        if not payload:
            print(f"❌ WebSocket: Invalid token - {token[:20] if len(token) > 20 else token}...")
            await websocket.close(code=1008, reason="Invalid authentication token")
            return None
        
        user_id = payload.get("sub")
        user_role = payload.get("role", "user")
        
        if not user_id:
            print(f"❌ WebSocket: No user_id in token payload. Payload: {payload}")
            await websocket.close(code=1008, reason="Invalid token payload")
            return None
        
        # Reduced logging - only log on first connection
        pass
        return {
            "id": user_id,
            "role": user_role
        }
    except Exception as e:
        print(f"❌ Error authenticating WebSocket: {e}")
        import traceback
        traceback.print_exc()
        try:
            # Only close if connection was accepted
            try:
                if hasattr(websocket, 'client_state') and websocket.client_state.name == "CONNECTED":
                    await websocket.close(code=1011, reason=f"Authentication error: {str(e)}")
            except AttributeError:
                # Fallback: try to close anyway
                try:
                    await websocket.close(code=1011, reason=f"Authentication error: {str(e)}")
                except:
                    pass
        except Exception as close_error:
            print(f"❌ Error closing WebSocket: {close_error}")
        return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    user = None
    try:
        # Reduced logging
        pass
        
        # Authenticate user (this also accepts the connection)
        user = await get_current_user_ws(websocket)
        if not user:
            print("❌ WebSocket: Authentication failed, closing connection")
            return
        
        user_id = user["id"]
        user_role = user["role"]
        
        # Connect to manager (connection already accepted in get_current_user_ws)
        await manager.connect(websocket, user_id, user_role)
        
        # Send welcome message
        await manager.send_personal_message({
            "type": "connected",
            "message": "WebSocket connected successfully",
            "user_id": user_id
        }, websocket)
        
        # Reduced logging
        pass
        
        # Listen for messages
        while True:
            try:
                # Check if websocket is still connected before receiving
                try:
                    if hasattr(websocket, 'client_state') and websocket.client_state.name != "CONNECTED":
                        break
                except AttributeError:
                    # client_state might not be available, continue anyway
                    pass
                
                data = await websocket.receive_json()
                
                # Check again after receiving
                try:
                    if hasattr(websocket, 'client_state') and websocket.client_state.name != "CONNECTED":
                        break
                except AttributeError:
                    pass
                
                message_type = data.get("type")
                
                if message_type == "subscribe_ticket":
                    # Subscribe to a specific ticket
                    ticket_id = data.get("ticket_id")
                    if ticket_id:
                        await manager.subscribe_to_ticket(websocket, ticket_id)
                        try:
                            await manager.send_personal_message({
                                "type": "subscribed",
                                "ticket_id": ticket_id,
                                "message": f"Subscribed to ticket {ticket_id}"
                            }, websocket)
                        except Exception as send_error:
                            break
                
                elif message_type == "unsubscribe_ticket":
                    # Unsubscribe from a specific ticket
                    ticket_id = data.get("ticket_id")
                    if ticket_id:
                        await manager.unsubscribe_from_ticket(websocket, ticket_id)
                        try:
                            await manager.send_personal_message({
                                "type": "unsubscribed",
                                "ticket_id": ticket_id
                            }, websocket)
                        except Exception as send_error:
                            break
                
                elif message_type == "ping":
                    # Respond to ping
                    try:
                        await manager.send_personal_message({
                            "type": "pong"
                        }, websocket)
                    except Exception as send_error:
                        break
                
                else:
                    try:
                        await manager.send_personal_message({
                            "type": "error",
                            "message": f"Unknown message type: {message_type}"
                        }, websocket)
                    except Exception as send_error:
                        break
            
            except json.JSONDecodeError as json_error:
                # Silently ignore invalid JSON
                try:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }, websocket)
                except Exception:
                    break
            except WebSocketDisconnect:
                # This will be caught by outer handler
                raise
            except Exception as msg_error:
                # Silently handle errors and break loop
                try:
                    if hasattr(websocket, 'client_state') and websocket.client_state.name != "CONNECTED":
                        break
                except AttributeError:
                    pass
                break
    
    except WebSocketDisconnect:
        # Normal disconnect - no logging needed
        manager.disconnect(websocket)
    except Exception as e:
        # Log only critical errors
        print(f"❌ WebSocket critical error: {e}")
        manager.disconnect(websocket)

