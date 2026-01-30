"""Tickets API router"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.application.dto.ticket_dto import (
    TicketCreateDTO,
    TicketUpdateDTO,
    TicketResponseDTO,
    CommentCreateDTO,
)
from app.presentation.api.v1.dependencies import (
    get_ticket_use_cases,
    get_current_active_user,
    get_admin_or_it_user,
)
from app.application.use_cases.ticket_use_cases import TicketUseCases
from app.infrastructure.websocket import manager
from app.infrastructure.telegram.bot import telegram_bot

router = APIRouter(prefix="/tickets", tags=["tickets"], redirect_slashes=False)


@router.post("/", response_model=TicketResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: TicketCreateDTO,
    use_cases: TicketUseCases = Depends(get_ticket_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Create a new ticket
    
    Any authenticated user can create a ticket.
    """
    try:
        print(f"📥 Creating ticket: {ticket_data.title}")
        ticket = await use_cases.create_ticket(ticket_data, current_user["id"])
        print(f"✅ Ticket created successfully: {ticket.id}")
        
        # Convert ticket to dict for WebSocket - use mode='json' to serialize datetime properly
        if hasattr(ticket, 'model_dump'):
            ticket_dict = ticket.model_dump(mode='json')
        elif hasattr(ticket, 'dict'):
            ticket_dict = ticket.dict()
        else:
            ticket_dict = ticket
        
        print(f"📨 Created ticket {ticket_dict.get('id')}, broadcasting to all users")
        
        # Verify ticket exists in database before broadcasting
        # This ensures data is persisted before notifying clients
        from app.infrastructure.database.base import SessionLocal
        from app.infrastructure.database.models import TicketModel
        verify_db = SessionLocal()
        try:
            verify_ticket = verify_db.query(TicketModel).filter(TicketModel.id == ticket_dict.get('id')).first()
            if verify_ticket:
                print(f"✅ Verified ticket {verify_ticket.id} exists in database before broadcast")
            else:
                print(f"❌ WARNING: Ticket {ticket_dict.get('id')} not found in database!")
        finally:
            verify_db.close()
        
        # Create event with ticket data
        ticket_event = {
            "type": "ticket_created",
            "ticket": ticket_dict
        }
        
        # Create notification event for IT and admin (with additional info)
        notification_event = {
            "type": "ticket_created",
            "ticket": ticket_dict,
            "message": f"Создан новый тикет: {ticket_dict.get('title', 'Без названия')}",
            "priority": ticket_dict.get('priority', 'medium'),
            "created_by": ticket_dict.get('created_by_name', 'Пользователь')
        }
        
        # Broadcast to all users (for real-time updates)
        await manager.broadcast_to_all(ticket_event)
        
        # Also send notification event to IT and admin (they will receive both, but frontend handles deduplication)
        await manager.broadcast_to_role(notification_event, "it")
        await manager.broadcast_to_role(notification_event, "admin")
        
        # Send Telegram notifications to all IT users
        try:
            ticket_title = ticket_dict.get('title', 'Без названия')
            ticket_priority = ticket_dict.get('priority', 'medium')
            creator_name = ticket_dict.get('created_by_name', current_user.get('username', 'Пользователь'))
            ticket_id = ticket_dict.get('id')
            
            await telegram_bot.notify_all_it_users(
                ticket_title,
                ticket_priority,
                creator_name,
                ticket_id
            )
        except Exception as tg_error:
            # Silently ignore Telegram errors
            print(f"⚠️ Error sending Telegram notifications for ticket: {tg_error}")
            pass
        
        print(f"✅ Ticket creation broadcast completed for ticket {ticket_dict.get('id')}")
        
        return ticket
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=List[TicketResponseDTO])
async def get_all_tickets(
    use_cases: TicketUseCases = Depends(get_ticket_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Get all tickets
    
    - Admin: sees all tickets
    - IT: sees all tickets
    - User: sees only their own tickets
    """
    user_role = current_user.get("role")
    if user_role in ["admin", "it"]:
        return await use_cases.get_all_tickets()
    else:
        return await use_cases.get_user_tickets(current_user["id"])


@router.get("/my", response_model=List[TicketResponseDTO])
async def get_my_tickets(
    use_cases: TicketUseCases = Depends(get_ticket_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Get current user's tickets"""
    return await use_cases.get_user_tickets(current_user["id"])


@router.get("/{ticket_id}", response_model=TicketResponseDTO)
async def get_ticket(
    ticket_id: str,
    use_cases: TicketUseCases = Depends(get_ticket_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Get ticket by ID
    
    - Admin and IT: can see any ticket
    - User: can only see their own tickets
    """
    ticket = await use_cases.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' not found",
        )
    
    # Check permissions
    user_role = current_user.get("role")
    if user_role not in ["admin", "it"] and ticket.created_by != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own tickets",
        )
    
    return ticket


@router.put("/{ticket_id}", response_model=TicketResponseDTO)
async def update_ticket(
    ticket_id: str,
    ticket_data: TicketUpdateDTO,
    use_cases: TicketUseCases = Depends(get_ticket_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Update ticket
    
    - Admin and IT: can update any ticket and close tickets
    - User: can only update their own tickets (but cannot close them)
    """
    # Check if ticket exists
    ticket = await use_cases.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' not found",
        )
    
    # Check permissions
    user_role = current_user.get("role")
    if user_role not in ["admin", "it"] and ticket.created_by != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own tickets",
        )
    
    try:
        updated_ticket = await use_cases.update_ticket(ticket_id, ticket_data, user_role)
        
        # Convert ticket to dict for WebSocket
        ticket_dict = updated_ticket.model_dump() if hasattr(updated_ticket, 'model_dump') else (updated_ticket.dict() if hasattr(updated_ticket, 'dict') else updated_ticket)
        
        # Broadcast ticket update event
        await manager.broadcast_to_ticket({
            "type": "ticket_updated",
            "ticket": ticket_dict
        }, ticket_id)
        
        # Also notify ticket creator
        await manager.broadcast_to_user({
            "type": "ticket_updated",
            "ticket": ticket_dict
        }, updated_ticket.created_by)
        
        return updated_ticket
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: str,
    use_cases: TicketUseCases = Depends(get_ticket_use_cases),
    current_user: dict = Depends(get_admin_or_it_user),  # Only admin and IT can delete
):
    """Delete ticket (Admin and IT only)"""
    # Get ticket before deletion to notify users
    ticket = await use_cases.get_ticket(ticket_id)
    
    success = await use_cases.delete_ticket(ticket_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' not found",
        )
    
    # Broadcast ticket deletion event
    if ticket:
        ticket_dict = ticket.model_dump() if hasattr(ticket, 'model_dump') else (ticket.dict() if hasattr(ticket, 'dict') else ticket)
        await manager.broadcast_to_all({
            "type": "ticket_deleted",
            "ticket_id": ticket_id,
            "ticket": ticket_dict
        })


@router.post("/{ticket_id}/comments", response_model=TicketResponseDTO)
async def add_comment(
    ticket_id: str,
    comment_data: CommentCreateDTO,
    use_cases: TicketUseCases = Depends(get_ticket_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Add comment to ticket
    
    Any authenticated user can add comments to tickets they have access to.
    """
    # Check if ticket exists and user has access
    ticket = await use_cases.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' not found",
        )
    
    # Check permissions
    user_role = current_user.get("role")
    if user_role not in ["admin", "it"] and ticket.created_by != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only comment on tickets you have access to",
        )
    
    try:
        updated_ticket = await use_cases.add_comment(ticket_id, comment_data, current_user["id"])
        
        # Convert ticket to dict for WebSocket - use mode='json' to serialize datetime properly
        if hasattr(updated_ticket, 'model_dump'):
            # Pydantic v2
            ticket_dict = updated_ticket.model_dump(mode='json')
        elif hasattr(updated_ticket, 'dict'):
            # Pydantic v1
            ticket_dict = updated_ticket.dict()
        else:
            ticket_dict = updated_ticket
        
        # Log ticket data for debugging
        print(f"📨 Ticket data for WebSocket: {ticket_dict.get('id')}")
        print(f"📨 Comments count in ticket_dict: {len(ticket_dict.get('comments', []))}")
        if ticket_dict.get('comments'):
            print(f"📨 Last comment ID: {ticket_dict['comments'][-1].get('id')}")
            print(f"📨 Last comment text: {ticket_dict['comments'][-1].get('text')[:50]}...")
        
        # Broadcast comment added event to all subscribers of this ticket
        comment_event = {
            "type": "comment_added",
            "ticket_id": ticket_id,
            "ticket": ticket_dict
        }
        print(f"📨 Broadcasting comment_added event for ticket {ticket_id}")
        
        # Broadcast to ticket subscribers (users viewing this ticket)
        await manager.broadcast_to_ticket(comment_event, ticket_id)
        
        # Also notify ticket creator (in case they're not subscribed)
        print(f"📨 Notifying ticket creator: {updated_ticket.created_by}")
        await manager.broadcast_to_user(comment_event, updated_ticket.created_by)
        
        # Also broadcast to IT and admin users (they should see all ticket updates)
        print(f"📨 Broadcasting to IT and Admin users")
        await manager.broadcast_to_role(comment_event, "it")
        await manager.broadcast_to_role(comment_event, "admin")
        
        print(f"✅ Comment broadcast completed for ticket {ticket_id}")
        
        return updated_ticket
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

