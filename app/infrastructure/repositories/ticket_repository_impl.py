"""Ticket repository implementation"""
import uuid
from datetime import datetime
from typing import List, Optional
from app.domain.entities.ticket import Ticket, Comment
from app.domain.repositories.ticket_repository import TicketRepository


class TicketRepositoryImpl(TicketRepository):
    """Ticket repository implementation with in-memory storage"""

    def __init__(self):
        self._tickets: dict[str, Ticket] = {}

    async def create(self, ticket: Ticket) -> Ticket:
        """Create a new ticket"""
        ticket.id = str(uuid.uuid4())
        ticket.created_at = datetime.utcnow()
        ticket.updated_at = datetime.utcnow()
        if ticket.comments is None:
            ticket.comments = []
        
        self._tickets[ticket.id] = ticket
        return ticket

    async def get_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Get ticket by ID"""
        return self._tickets.get(ticket_id)

    async def get_all(self) -> List[Ticket]:
        """Get all tickets"""
        return list(self._tickets.values())

    async def get_by_user_id(self, user_id: str) -> List[Ticket]:
        """Get tickets by user ID"""
        return [
            ticket for ticket in self._tickets.values()
            if ticket.created_by == user_id
        ]

    async def update(self, ticket: Ticket) -> Ticket:
        """Update ticket"""
        if ticket.id not in self._tickets:
            raise ValueError(f"Ticket with ID '{ticket.id}' not found")

        ticket.updated_at = datetime.utcnow()
        self._tickets[ticket.id] = ticket
        return ticket

    async def delete(self, ticket_id: str) -> bool:
        """Delete ticket"""
        if ticket_id not in self._tickets:
            return False

        del self._tickets[ticket_id]
        return True

    async def add_comment(self, ticket_id: str, comment: Comment) -> Ticket:
        """Add comment to ticket"""
        ticket = await self.get_by_id(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket with ID '{ticket_id}' not found")

        comment.id = str(uuid.uuid4())
        comment.created_at = datetime.utcnow()
        
        if ticket.comments is None:
            ticket.comments = []
        
        ticket.comments.append(comment)
        ticket.updated_at = datetime.utcnow()
        self._tickets[ticket.id] = ticket
        
        return ticket




