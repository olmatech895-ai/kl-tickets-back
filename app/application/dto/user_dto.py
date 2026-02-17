"""User DTOs"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.domain.entities.user import UserRole


class UserCreateDTO(BaseModel):
    """DTO for creating a user (email list; no password)."""
    username: str
    email: EmailStr
    role: UserRole = UserRole.USER


class UserUpdateDTO(BaseModel):
    """DTO for updating a user"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    blocked: Optional[bool] = None


class UserResponseDTO(BaseModel):
    """DTO for user response"""
    id: str
    username: str
    email: str
    role: UserRole
    blocked: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

