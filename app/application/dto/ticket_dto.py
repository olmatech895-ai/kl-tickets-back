"""Ticket DTOs"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.domain.entities.ticket import (
    TicketPriority,
    TicketStatus,
    TicketCategory,
)


class CommentCreateDTO(BaseModel):
    """DTO for creating a comment"""
    text: str


class CommentResponseDTO(BaseModel):
    """DTO for comment response"""
    id: str
    text: str
    author_id: str
    author_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketCreateDTO(BaseModel):
    """DTO for creating a ticket"""
    title: str
    description: str
    priority: TicketPriority
    category: TicketCategory


class TicketUpdateDTO(BaseModel):
    """DTO for updating a ticket"""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TicketPriority] = None
    status: Optional[TicketStatus] = None
    category: Optional[TicketCategory] = None
    assigned_to: Optional[str] = None


class TicketResponseDTO(BaseModel):
    """DTO for ticket response"""
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
    created_at: datetime
    updated_at: datetime
    comments: List[CommentResponseDTO] = []

    model_config = {"from_attributes": True}

