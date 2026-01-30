"""PostgreSQL implementation of InventoryRepository"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.domain.entities.inventory import InventoryItem, InventoryStatus
from app.domain.repositories.inventory_repository import InventoryRepository
from app.infrastructure.database.models import InventoryModel
import uuid


class InventoryRepositoryDB(InventoryRepository):
    """PostgreSQL implementation of InventoryRepository"""

    def __init__(self, db: Session):
        self.db = db

    def _inventory_model_to_entity(self, model: InventoryModel) -> InventoryItem:
        """Convert InventoryModel to InventoryItem entity"""
        return InventoryItem(
            id=str(model.id),
            name=model.name,
            type=model.type,
            serial_number=model.serial_number,
            location=model.location,
            status=InventoryStatus(model.status.value) if hasattr(model.status, 'value') else InventoryStatus(model.status),
            description=model.description,
            photo=model.photo,
            responsible=str(model.responsible) if model.responsible else None,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create(self, item: InventoryItem) -> InventoryItem:
        """Create a new inventory item"""
        inventory_model = InventoryModel(
            id=item.id if item.id else None,
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

        self.db.add(inventory_model)
        self.db.commit()
        self.db.refresh(inventory_model)

        return self._inventory_model_to_entity(inventory_model)

    async def get_by_id(self, item_id: str) -> Optional[InventoryItem]:
        """Get inventory item by ID"""
        inventory_model = self.db.query(InventoryModel).filter(InventoryModel.id == item_id).first()
        if not inventory_model:
            return None
        return self._inventory_model_to_entity(inventory_model)

    async def get_all(self) -> List[InventoryItem]:
        """Get all inventory items"""
        inventory_models = self.db.query(InventoryModel).order_by(InventoryModel.created_at.desc()).all()
        return [self._inventory_model_to_entity(model) for model in inventory_models]

    async def update(self, item: InventoryItem) -> InventoryItem:
        """Update inventory item"""
        inventory_model = self.db.query(InventoryModel).filter(InventoryModel.id == item.id).first()
        if not inventory_model:
            raise ValueError(f"Inventory item with ID '{item.id}' not found")

        inventory_model.name = item.name
        inventory_model.type = item.type
        inventory_model.serial_number = item.serial_number
        inventory_model.location = item.location
        inventory_model.status = item.status
        inventory_model.description = item.description
        inventory_model.photo = item.photo
        inventory_model.responsible = item.responsible
        inventory_model.updated_at = item.updated_at

        self.db.commit()
        self.db.refresh(inventory_model)

        return self._inventory_model_to_entity(inventory_model)

    async def delete(self, item_id: str) -> bool:
        """Delete inventory item"""
        inventory_model = self.db.query(InventoryModel).filter(InventoryModel.id == item_id).first()
        if not inventory_model:
            return False

        self.db.delete(inventory_model)
        self.db.commit()
        return True




