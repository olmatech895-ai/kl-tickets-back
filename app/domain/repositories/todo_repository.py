"""Todo repository interface"""
from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.todo import Todo


class TodoRepository(ABC):
    """Interface for todo repository"""

    @abstractmethod
    async def create(self, todo: Todo) -> Todo:
        """Create a new todo"""
        pass

    @abstractmethod
    async def get_by_id(self, todo_id: str) -> Optional[Todo]:
        """Get todo by ID"""
        pass

    @abstractmethod
    async def get_all(self) -> List[Todo]:
        """Get all todos"""
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: str, include_archived: bool = False) -> List[Todo]:
        """Get todos by user ID (created by or assigned to)
        
        Args:
            user_id: User ID
            include_archived: If True, includes archived todos. Default False (excludes archived).
        """
        pass
    
    @abstractmethod
    async def get_archived_by_user_id(self, user_id: str) -> List[Todo]:
        """Get archived todos by user ID (created by or assigned to)"""
        pass

    @abstractmethod
    async def get_by_status(self, status: str) -> List[Todo]:
        """Get todos by status"""
        pass

    @abstractmethod
    async def update(self, todo: Todo) -> Todo:
        """Update todo"""
        pass

    @abstractmethod
    async def delete(self, todo_id: str) -> bool:
        """Delete todo permanently"""
        pass



