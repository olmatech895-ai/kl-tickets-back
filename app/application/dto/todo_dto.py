"""Todo DTOs"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

# TodoStatus теперь строка для поддержки кастомных статусов колонок
# Используем str напрямую в типах полей


class TodoCommentCreateDTO(BaseModel):
    """DTO for creating a todo comment"""
    text: str


class TodoCommentResponseDTO(BaseModel):
    """DTO for todo comment response"""
    id: str
    text: str
    author_id: str
    author_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TodoListItemCreateDTO(BaseModel):
    """DTO for creating a todo list item"""
    text: str
    checked: bool = False


class TodoListItemUpdateDTO(BaseModel):
    """DTO for updating a todo list item"""
    checked: bool


class TodoListItemResponseDTO(BaseModel):
    """DTO for todo list item response"""
    id: str
    text: str
    checked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TodoAttachmentResponseDTO(BaseModel):
    """DTO for todo attachment response"""
    id: str
    filename: str
    file_path: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    is_background: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class TodoCreateDTO(BaseModel):
    """DTO for creating a todo"""
    title: str
    description: Optional[str] = None
    status: str = "todo"
    assigned_to: List[str] = []
    tags: List[str] = []
    story_points: Optional[int] = None
    in_focus: bool = False
    project: Optional[str] = None
    due_date: Optional[datetime] = None


class TodoUpdateDTO(BaseModel):
    """DTO for updating a todo"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    story_points: Optional[int] = None
    in_focus: Optional[bool] = None
    read: Optional[bool] = None
    project: Optional[str] = None
    due_date: Optional[datetime] = None
    background_image: Optional[str] = None
    todo_lists: Optional[List[TodoListItemCreateDTO]] = None


class TodoResponseDTO(BaseModel):
    """DTO for todo response"""
    id: str
    title: str
    description: Optional[str] = None
    status: str
    assigned_to: List[str] = []
    tags: List[str] = []
    comments: List[TodoCommentResponseDTO] = []
    todo_lists: List[TodoListItemResponseDTO] = []
    attachments: List[TodoAttachmentResponseDTO] = []
    story_points: Optional[int] = None
    in_focus: bool = False
    read: bool = True
    project: Optional[str] = None
    due_date: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    background_image: Optional[str] = None

    model_config = {"from_attributes": True}


class TodoColumnCreateDTO(BaseModel):
    """DTO for creating a todo column"""
    column_id: str
    title: str
    status: str
    color: str = "primary"
    background_image: Optional[str] = None
    order_index: str = "0"


class TodoColumnUpdateDTO(BaseModel):
    """DTO for updating a todo column"""
    title: Optional[str] = None
    status: Optional[str] = None
    color: Optional[str] = None
    background_image: Optional[str] = None
    order_index: Optional[str] = None


class TodoColumnResponseDTO(BaseModel):
    """DTO for todo column response"""
    id: str
    column_id: str
    title: str
    status: str
    color: str
    background_image: Optional[str] = None
    order_index: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TodoColumnsUpdateDTO(BaseModel):
    """DTO for updating all columns at once"""
    columns: List[TodoColumnCreateDTO]

