"""Inventory API router"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
from app.application.dto.inventory_dto import (
    InventoryItemCreateDTO,
    InventoryItemUpdateDTO,
    InventoryItemResponseDTO,
)
from app.presentation.api.v1.dependencies import (
    get_inventory_use_cases,
    get_admin_user,
    get_admin_or_it_user,
)
from app.application.use_cases.inventory_use_cases import InventoryUseCases
from app.infrastructure.storage import save_uploaded_file
from app.domain.entities.inventory import InventoryStatus

router = APIRouter(prefix="/inventory", tags=["inventory"], redirect_slashes=False)


@router.post("/", response_model=InventoryItemResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    name: str = Form(...),
    type: str = Form(...),
    serial_number: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    status: str = Form("working"),
    description: Optional[str] = Form(None),
    responsible: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    use_cases: InventoryUseCases = Depends(get_inventory_use_cases),
    current_user: dict = Depends(get_admin_or_it_user),
):
    """Create a new inventory item
    
    Administrators and IT department can create inventory items.
    """
    try:
        # Handle file upload
        photo_path = None
        if photo and photo.filename:
            try:
                photo_path = await save_uploaded_file(photo)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
        
        # Convert "none" to None for responsible
        responsible_value = None if responsible == "none" or responsible == "" else responsible
        
        # Create DTO
        item_data = InventoryItemCreateDTO(
            name=name,
            type=type,
            serial_number=serial_number,
            location=location,
            status=InventoryStatus(status),
            description=description,
            photo=photo_path,
            responsible=responsible_value,
        )
        
        item = await use_cases.create_inventory_item(item_data)
        return item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=List[InventoryItemResponseDTO])
async def get_all_inventory_items(
    use_cases: InventoryUseCases = Depends(get_inventory_use_cases),
    current_user: dict = Depends(get_admin_or_it_user),
):
    """Get all inventory items
    
    Administrators and IT department can view inventory items.
    """
    items = await use_cases.get_all_inventory_items()
    return items


@router.get("/{item_id}", response_model=InventoryItemResponseDTO)
async def get_inventory_item(
    item_id: str,
    use_cases: InventoryUseCases = Depends(get_inventory_use_cases),
    current_user: dict = Depends(get_admin_or_it_user),
):
    """Get inventory item by ID
    
    Administrators and IT department can view inventory items.
    """
    item = await use_cases.get_inventory_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with ID '{item_id}' not found",
        )
    return item


@router.put("/{item_id}", response_model=InventoryItemResponseDTO)
async def update_inventory_item(
    item_id: str,
    name: Optional[str] = Form(None),
    type: Optional[str] = Form(None),
    serial_number: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    responsible: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    use_cases: InventoryUseCases = Depends(get_inventory_use_cases),
    current_user: dict = Depends(get_admin_or_it_user),
):
    """Update inventory item
    
    Administrators and IT department can update inventory items.
    """
    try:
        # Handle file upload if new photo provided
        photo_path = None
        if photo and photo.filename:
            try:
                photo_path = await save_uploaded_file(photo)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
        
        # Convert "none" to None for responsible
        responsible_value = None
        if responsible is not None:
            responsible_value = None if responsible == "none" or responsible == "" else responsible
        
        # Create DTO with only provided fields
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if type is not None:
            update_data["type"] = type
        if serial_number is not None:
            update_data["serial_number"] = serial_number
        if location is not None:
            update_data["location"] = location
        if status is not None:
            update_data["status"] = InventoryStatus(status)
        if description is not None:
            update_data["description"] = description
        if photo_path is not None:
            update_data["photo"] = photo_path
        if responsible is not None:
            update_data["responsible"] = responsible_value
        
        item_data = InventoryItemUpdateDTO(**update_data)
        item = await use_cases.update_inventory_item(item_id, item_data)
        return item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    item_id: str,
    use_cases: InventoryUseCases = Depends(get_inventory_use_cases),
    current_user: dict = Depends(get_admin_user),
):
    """Delete inventory item
    
    Only administrators can delete inventory items.
    """
    deleted = await use_cases.delete_inventory_item(item_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with ID '{item_id}' not found",
        )


