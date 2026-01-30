"""User repository implementation"""
import uuid
import bcrypt
from datetime import datetime
from typing import List, Optional
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository


class UserRepositoryImpl(UserRepository):
    """User repository implementation with in-memory storage"""

    def __init__(self):
        self._users: dict[str, User] = {}
        self._passwords: dict[str, str] = {}

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        print(f"[DEBUG] Hashing password, length: {len(password)}")
        salt = bcrypt.gensalt()
        password_bytes = password.encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, salt)
        hashed_str = hashed.decode('utf-8')
        print(f"[DEBUG] Password hashed successfully, hash length: {len(hashed_str)}")
        return hashed_str

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password using bcrypt"""
        try:
            print(f"[DEBUG] _verify_password called")
            print(f"[DEBUG] Plain password length: {len(plain_password)}")
            print(f"[DEBUG] Hashed password length: {len(hashed_password)}")
            print(f"[DEBUG] Hashed password starts with: {hashed_password[:20]}...")
            
            plain_bytes = plain_password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            
            print(f"[DEBUG] Plain bytes length: {len(plain_bytes)}")
            print(f"[DEBUG] Hashed bytes length: {len(hashed_bytes)}")
            
            result = bcrypt.checkpw(plain_bytes, hashed_bytes)
            print(f"[DEBUG] bcrypt.checkpw result: {result}")
            
            return result
        except Exception as e:
            print(f"[DEBUG] Exception in _verify_password: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def create(self, user: User, password: str) -> User:
        """Create a new user"""
        user.id = str(uuid.uuid4())
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()

        # Hash password and store
        hashed = self._hash_password(password)
        self._users[user.id] = user
        self._passwords[user.username] = hashed
        
        print(f"[DEBUG] Created user: {user.username}, ID: {user.id}")
        print(f"[DEBUG] Stored password for username: {user.username}")
        print(f"[DEBUG] Total users after create: {len(self._users)}")
        print(f"[DEBUG] Total passwords after create: {len(self._passwords)}")

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

        user = self._users[user_id]
        del self._users[user_id]

        if user.username in self._passwords:
            del self._passwords[user.username]

        return True

    async def verify_password(self, username: str, password: str) -> bool:
        """Verify user password"""
        print(f"[DEBUG] Verifying password for username: {username}")
        print(f"[DEBUG] Stored usernames: {list(self._passwords.keys())}")
        print(f"[DEBUG] Total users: {len(self._users)}")
        
        hashed_password = self._passwords.get(username)
        if not hashed_password:
            print(f"[DEBUG] No password found for username: {username}")
            return False

        print(f"[DEBUG] Found hashed password for {username}")
        result = self._verify_password(password, hashed_password)
        print(f"[DEBUG] Password verification result: {result}")
        return result

