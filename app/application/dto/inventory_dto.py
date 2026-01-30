"""Inventory DTOs"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.domain.entities.inventory import InventoryStatus


class InventoryItemCreateDTO(BaseModel):
    """DTO for creating an inventory item"""
    name: str
    type: str
    serial_number: Optional[str] = None
    location: Optional[str] = None
    status: InventoryStatus = InventoryStatus.WORKING
    description: Optional[str] = None
    photo: Optional[str] = None
    responsible: Optional[str] = None


class InventoryItemUpdateDTO(BaseModel):
    """DTO for updating an inventory item"""
    name: Optional[str] = None
    type: Optional[str] = None
    serial_number: Optional[str] = None
    location: Optional[str] = None
    status: Optional[InventoryStatus] = None
    description: Optional[str] = None
    photo: Optional[str] = None
    responsible: Optional[str] = None


class InventoryItemResponseDTO(BaseModel):
    """DTO for inventory item response"""
    id: str
    name: str
    type: str
    serial_number: Optional[str] = None
    location: Optional[str] = None
    status: InventoryStatus
    description: Optional[str] = None
    photo: Optional[str] = None
    responsible: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

