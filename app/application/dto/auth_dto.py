"""Authentication DTOs"""
from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginDTO(BaseModel):
    """DTO for login. Authentication by email only (no password)."""
    email: EmailStr


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

