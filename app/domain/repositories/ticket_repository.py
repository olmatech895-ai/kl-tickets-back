"""Ticket repository interface"""
from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.ticket import Ticket


class TicketRepository(ABC):
    """Interface for ticket repository"""

    @abstractmethod
    async def create(self, ticket: Ticket) -> Ticket:
        """Create a new ticket"""
        pass

    @abstractmethod
    async def get_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Get ticket by ID"""
        pass

    @abstractmethod
    async def get_all(self) -> List[Ticket]:
        """Get all tickets"""
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> List[Ticket]:
        """Get tickets by user ID"""
        pass

    @abstractmethod
    async def update(self, ticket: Ticket) -> Ticket:
        """Update ticket"""
        pass

    @abstractmethod
    async def delete(self, ticket_id: str) -> bool:
        """Delete ticket"""
        pass

    @abstractmethod
    async def add_comment(self, ticket_id: str, comment) -> Ticket:
        """Add comment to ticket"""
        pass

