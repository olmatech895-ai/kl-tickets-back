"""Inventory domain entity"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class InventoryStatus(str, Enum):
    """Inventory item status"""
    WORKING = "working"
    REPAIR = "repair"
    BROKEN = "broken"
    WRITTEN_OFF = "written_off"


@dataclass
class InventoryItem:
    """Inventory item domain entity"""
    id: str
    name: str
    type: str
    serial_number: Optional[str] = None
    location: Optional[str] = None
    status: InventoryStatus = InventoryStatus.WORKING
    description: Optional[str] = None
    photo: Optional[str] = None
    responsible: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

