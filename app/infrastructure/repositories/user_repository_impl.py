"""User repository implementation (in-memory). No passwords; auth by email only."""
import uuid
from datetime import datetime
from typing import List, Optional
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository


class UserRepositoryImpl(UserRepository):
    """User repository implementation with in-memory storage"""

    def __init__(self):
        self._users: dict[str, User] = {}

    async def create(self, user: User) -> User:
        """Create a new user (no password)."""
        user.id = str(uuid.uuid4())
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        self._users[user.id] = user
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self._users.get(user_id)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        email_lower = email.lower()
        for user in self._users.values():
            if user.email.lower() == email_lower:
                return user
        return None

    async def get_all(self) -> List[User]:
        """Get all users"""
        return list(self._users.values())

    async def update(self, user: User) -> User:
        """Update user"""
        if user.id not in self._users:
            raise ValueError(f"User with ID '{user.id}' not found")

        user.updated_at = datetime.utcnow()
        self._users[user.id] = user

        return user

    async def delete(self, user_id: str) -> bool:
        """Delete user"""
        if user_id not in self._users:
            return False
        del self._users[user_id]
        return True

