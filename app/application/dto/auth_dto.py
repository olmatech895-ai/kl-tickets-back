"""Authentication DTOs"""
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.domain.entities.user import UserRole


class RegisterDTO(BaseModel):
    """DTO for user registration"""
    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.USER


class LoginDTO(BaseModel):
    """DTO for user login"""
    username: str
    password: str


class TokenResponseDTO(BaseModel):
    """DTO for token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: dict


class TokenData(BaseModel):
    """Token payload data"""
    user_id: Optional[str] = None
    username: Optional[str] = None

