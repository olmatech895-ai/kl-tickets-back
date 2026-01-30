"""Inventory use cases"""
from typing import List, Optional
from app.domain.entities.inventory import InventoryItem, InventoryStatus
from app.domain.repositories.inventory_repository import InventoryRepository
from app.application.dto.inventory_dto import (
    InventoryItemCreateDTO,
    InventoryItemUpdateDTO,
    InventoryItemResponseDTO,
)
from datetime import datetime
import uuid


class InventoryUseCases:
    """Use cases for inventory operations"""

    def __init__(self, inventory_repository: InventoryRepository):
        self.inventory_repository = inventory_repository

    async def create_inventory_item(self, item_data: InventoryItemCreateDTO) -> InventoryItemResponseDTO:
        """Create a new inventory item"""
        inventory_item = InventoryItem(
            id=str(uuid.uuid4()),
            name=item_data.name,
            type=item_data.type,
            serial_number=item_data.serial_number,
            location=item_data.location,
            status=item_data.status,
            description=item_data.description,
            photo=item_data.photo,
            responsible=item_data.responsible,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        created_item = await self.inventory_repository.create(inventory_item)
        return self._inventory_item_to_dto(created_item)

    async def get_inventory_item(self, item_id: str) -> Optional[InventoryItemResponseDTO]:
        """Get inventory item by ID"""
        item = await self.inventory_repository.get_by_id(item_id)
        if not item:
            return None
        return self._inventory_item_to_dto(item)

    async def get_all_inventory_items(self) -> List[InventoryItemResponseDTO]:
        """Get all inventory items"""
        items = await self.inventory_repository.get_all()
        return [self._inventory_item_to_dto(item) for item in items]

    async def update_inventory_item(
        self, item_id: str, item_data: InventoryItemUpdateDTO
    ) -> InventoryItemResponseDTO:
        """Update inventory item"""
        existing_item = await self.inventory_repository.get_by_id(item_id)
        if not existing_item:
            raise ValueError(f"Inventory item with ID '{item_id}' not found")

        # Update only provided fields
        if item_data.name is not None:
            existing_item.name = item_data.name
        if item_data.type is not None:
            existing_item.type = item_data.type
        if item_data.serial_number is not None:
            existing_item.serial_number = item_data.serial_number
        if item_data.location is not None:
            existing_item.location = item_data.location
        if item_data.status is not None:
            existing_item.status = item_data.status
        if item_data.description is not None:
            existing_item.description = item_data.description
        if item_data.photo is not None:
            existing_item.photo = item_data.photo
        if item_data.responsible is not None:
            existing_item.responsible = item_data.responsible

        existing_item.updated_at = datetime.utcnow()

        updated_item = await self.inventory_repository.update(existing_item)
        return self._inventory_item_to_dto(updated_item)

    async def delete_inventory_item(self, item_id: str) -> bool:
        """Delete inventory item"""
        return await self.inventory_repository.delete(item_id)

    def _inventory_item_to_dto(self, item: InventoryItem) -> InventoryItemResponseDTO:
        """Convert InventoryItem entity to InventoryItemResponseDTO"""
        return InventoryItemResponseDTO(
            id=item.id,
            name=item.name,
            type=item.type,
            serial_number=item.serial_number,
            location=item.location,
            status=item.status,
            description=item.description,
            photo=item.photo,
            responsible=item.responsible,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )




