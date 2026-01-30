"""User domain entity"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class UserRole(str, Enum):
    """User roles enum"""
    ADMIN = "admin"
    IT = "it"
    USER = "user"


@dataclass
class User:
    """User domain entity"""
    id: str
    username: str
    email: str
    role: UserRole
    blocked: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

