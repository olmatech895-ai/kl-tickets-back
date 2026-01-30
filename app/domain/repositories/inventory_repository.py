"""Inventory repository interface"""
from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.inventory import InventoryItem


class InventoryRepository(ABC):
    """Interface for inventory repository"""

    @abstractmethod
    async def create(self, item: InventoryItem) -> InventoryItem:
        """Create a new inventory item"""
        pass

    @abstractmethod
    async def get_by_id(self, item_id: str) -> Optional[InventoryItem]:
        """Get inventory item by ID"""
        pass

    @abstractmethod
    async def get_all(self) -> List[InventoryItem]:
        """Get all inventory items"""
        pass

    @abstractmethod
    async def update(self, item: InventoryItem) -> InventoryItem:
        """Update inventory item"""
        pass

    @abstractmethod
    async def delete(self, item_id: str) -> bool:
        """Delete inventory item"""
        pass

