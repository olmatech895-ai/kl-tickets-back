"""User repository interface"""
from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.user import User


class UserRepository(ABC):
    """Interface for user repository"""

    @abstractmethod
    async def create(self, user: User, password: str) -> User:
        """Create a new user"""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        pass

    @abstractmethod
    async def get_all(self) -> List[User]:
        """Get all users"""
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update user"""
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """Delete user"""
        pass

    @abstractmethod
    async def verify_password(self, username: str, password: str) -> bool:
        """Verify user password"""
        pass

