"""Ticket domain entity"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List


class TicketPriority(str, Enum):
    """Ticket priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TicketStatus(str, Enum):
    """Ticket status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class TicketCategory(str, Enum):
    """Ticket categories"""
    HARDWARE = "hardware"
    SOFTWARE = "software"
    NETWORK = "network"
    ACCOUNT = "account"
    OTHER = "other"


@dataclass
class Comment:
    """Comment entity"""
    id: str
    text: str
    author_id: str
    author_name: str
    created_at: datetime


@dataclass
class Ticket:
    """Ticket domain entity"""
    id: str
    title: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    category: TicketCategory
    created_by: str
    created_by_name: str
    created_by_email: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    estimated_time: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    comments: List[Comment] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        if self.comments is None:
            self.comments = []

