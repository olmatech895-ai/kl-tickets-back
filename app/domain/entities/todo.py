"""Todo domain entity"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

# TodoStatus теперь строка для поддержки кастомных статусов колонок
# Стандартные значения: "todo", "in_progress", "done", "archived"
# Но можно использовать любые строковые значения, соответствующие статусам колонок
TodoStatus = str


@dataclass
class TodoComment:
    """Todo comment entity"""
    id: str
    text: str
    author_id: str
    author_name: str
    created_at: datetime


@dataclass
class TodoListItem:
    """Todo list item (checklist item) entity"""
    id: str
    text: str
    checked: bool
    created_at: datetime


@dataclass
class TodoAttachment:
    """Todo attachment entity"""
    id: str
    filename: str
    file_path: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    is_background: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Todo:
    """Todo domain entity"""
    id: str
    title: str
    description: Optional[str] = None
    status: str = "todo"  # Может быть любая строка, соответствующая статусу колонки
    assigned_to: List[str] = field(default_factory=list)  # List of user IDs
    tags: List[str] = field(default_factory=list)
    comments: List[TodoComment] = field(default_factory=list)
    todo_lists: List[TodoListItem] = field(default_factory=list)
    attachments: List[TodoAttachment] = field(default_factory=list)
    story_points: Optional[int] = None
    in_focus: bool = False
    read: bool = True
    project: Optional[str] = None
    due_date: Optional[datetime] = None
    created_by: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    background_image: Optional[str] = None  # Path to background image

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()



