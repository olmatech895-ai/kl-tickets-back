"""Todo use cases"""
from datetime import date as date_type
from typing import List, Optional
from app.domain.entities.todo import Todo, TodoComment, TodoListItem, TodoAttachment
# TodoStatus теперь строка
TodoStatus = str
from app.domain.repositories.todo_repository import TodoRepository
from app.domain.repositories.user_repository import UserRepository
from app.application.dto.todo_dto import (
    TodoCreateDTO,
    TodoUpdateDTO,
    TodoResponseDTO,
    TodoCommentCreateDTO,
    TodoCommentResponseDTO,
    TodoListItemCreateDTO,
    TodoListItemResponseDTO,
    TodoAttachmentResponseDTO,
)
from datetime import datetime
import uuid


class TodoUseCases:
    """Use cases for todo operations"""

    def __init__(self, todo_repository: TodoRepository, user_repository: UserRepository):
        self.todo_repository = todo_repository
        self.user_repository = user_repository

    async def create_todo(self, todo_data: TodoCreateDTO, created_by_user_id: str) -> TodoResponseDTO:
        """Create a new todo"""
        # Get user info
        user = await self.user_repository.get_by_id(created_by_user_id)
        if not user:
            raise ValueError(f"User with ID '{created_by_user_id}' not found")

        todo = Todo(
            id=str(uuid.uuid4()),
            title=todo_data.title,
            description=todo_data.description,
            status=todo_data.status,
            assigned_to=todo_data.assigned_to or [],
            tags=todo_data.tags or [],
            comments=[],
            todo_lists=[],
            attachments=[],
            story_points=todo_data.story_points,
            in_focus=todo_data.in_focus,
            read=True,
            project=todo_data.project,
            due_date=todo_data.due_date,
            all_day=todo_data.all_day,
            notify_when_due=todo_data.notify_when_due,
            calendar_only=todo_data.calendar_only,
            created_by=created_by_user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        created_todo = await self.todo_repository.create(todo)
        return self._todo_to_dto(created_todo)

    async def get_todo(self, todo_id: str) -> Optional[TodoResponseDTO]:
        """Get todo by ID"""
        todo = await self.todo_repository.get_by_id(todo_id)
        if not todo:
            return None
        return self._todo_to_dto(todo)

    async def get_all_todos(self) -> List[TodoResponseDTO]:
        """Get all todos"""
        todos = await self.todo_repository.get_all()
        return [self._todo_to_dto(todo) for todo in todos]

    async def get_user_todos(
        self,
        user_id: str,
        include_archived: bool = False,
        due_date: Optional[date_type] = None,
        calendar_only: Optional[bool] = None,
        all_day: Optional[bool] = None,
    ) -> List[TodoResponseDTO]:
        """Get todos for a user (created by or assigned to).
        
        Args:
            user_id: User ID
            include_archived: If True, includes archived todos. Default False.
            due_date: If set, return only todos with due_date on this date (for calendar day view).
            calendar_only: If True, only calendar-only items; if False, only board items. None = all.
            all_day: If True, only «весь день»; if False, only «по часам». None = all.
        """
        todos = await self.todo_repository.get_by_user_id(user_id, include_archived=include_archived)
        if due_date is not None:
            todos = [
                t for t in todos
                if t.due_date is not None and t.due_date.date() == due_date
            ]
        if calendar_only is not None:
            todos = [t for t in todos if getattr(t, "calendar_only", False) == calendar_only]
        if all_day is not None:
            todos = [t for t in todos if getattr(t, "all_day", False) == all_day]
        return [self._todo_to_dto(todo) for todo in todos]
    
    async def get_user_archived_todos(self, user_id: str) -> List[TodoResponseDTO]:
        """Get archived todos for a user (created by or assigned to)"""
        todos = await self.todo_repository.get_archived_by_user_id(user_id)
        return [self._todo_to_dto(todo) for todo in todos]

    async def get_todos_by_status(self, status: str) -> List[TodoResponseDTO]:
        """Get todos by status"""
        todos = await self.todo_repository.get_by_status(status)
        return [self._todo_to_dto(todo) for todo in todos]

    async def update_todo(self, todo_id: str, todo_data: TodoUpdateDTO) -> TodoResponseDTO:
        """Update todo"""
        existing_todo = await self.todo_repository.get_by_id(todo_id)
        if not existing_todo:
            raise ValueError(f"Todo with ID '{todo_id}' not found")

        # Update only provided fields
        if todo_data.title is not None:
            existing_todo.title = todo_data.title
        if todo_data.description is not None:
            existing_todo.description = todo_data.description
        if todo_data.status is not None:
            existing_todo.status = todo_data.status
        if todo_data.assigned_to is not None:
            existing_todo.assigned_to = todo_data.assigned_to
        if todo_data.tags is not None:
            existing_todo.tags = todo_data.tags
        if todo_data.story_points is not None:
            existing_todo.story_points = todo_data.story_points
        if todo_data.in_focus is not None:
            existing_todo.in_focus = todo_data.in_focus
        if todo_data.read is not None:
            existing_todo.read = todo_data.read
        if todo_data.project is not None:
            existing_todo.project = todo_data.project
        if todo_data.due_date is not None:
            existing_todo.due_date = todo_data.due_date
        if todo_data.all_day is not None:
            existing_todo.all_day = todo_data.all_day
        if todo_data.notify_when_due is not None:
            existing_todo.notify_when_due = todo_data.notify_when_due
        if todo_data.calendar_only is not None:
            existing_todo.calendar_only = todo_data.calendar_only
        if todo_data.background_image is not None:
            existing_todo.background_image = todo_data.background_image
        if todo_data.todo_lists is not None:
            # Update todo lists - preserve existing items if they exist, otherwise create new ones
            existing_todo.todo_lists = [
                TodoListItem(
                    id=item.id if hasattr(item, 'id') and item.id else str(uuid.uuid4()),
                    text=item.text,
                    checked=getattr(item, 'checked', False),
                    created_at=datetime.utcnow(),
                )
                for item in todo_data.todo_lists
            ]

        existing_todo.updated_at = datetime.utcnow()

        updated_todo = await self.todo_repository.update(existing_todo)
        return self._todo_to_dto(updated_todo)

    async def delete_todo(self, todo_id: str) -> bool:
        """Delete todo permanently"""
        return await self.todo_repository.delete(todo_id)

    async def archive_todo(self, todo_id: str) -> TodoResponseDTO:
        """Archive todo (set status to archived)"""
        existing_todo = await self.todo_repository.get_by_id(todo_id)
        if not existing_todo:
            raise ValueError(f"Todo with ID '{todo_id}' not found")

        existing_todo.status = "archived"
        existing_todo.updated_at = datetime.utcnow()

        updated_todo = await self.todo_repository.update(existing_todo)
        return self._todo_to_dto(updated_todo)

    async def restore_todo(self, todo_id: str) -> TodoResponseDTO:
        """Restore todo from archive (set status to todo)"""
        existing_todo = await self.todo_repository.get_by_id(todo_id)
        if not existing_todo:
            raise ValueError(f"Todo with ID '{todo_id}' not found")

        existing_todo.status = "todo"
        existing_todo.updated_at = datetime.utcnow()

        updated_todo = await self.todo_repository.update(existing_todo)
        return self._todo_to_dto(updated_todo)

    async def add_comment(self, todo_id: str, comment_data: TodoCommentCreateDTO, author_user_id: str) -> TodoResponseDTO:
        """Add comment to todo"""
        todo = await self.todo_repository.get_by_id(todo_id)
        if not todo:
            raise ValueError(f"Todo with ID '{todo_id}' not found")

        # Get user info
        user = await self.user_repository.get_by_id(author_user_id)
        if not user:
            raise ValueError(f"User with ID '{author_user_id}' not found")

        comment = TodoComment(
            id=str(uuid.uuid4()),
            text=comment_data.text,
            author_id=author_user_id,
            author_name=user.username,
            created_at=datetime.utcnow(),
        )

        todo.comments.append(comment)
        todo.updated_at = datetime.utcnow()

        updated_todo = await self.todo_repository.update(todo)
        return self._todo_to_dto(updated_todo)

    async def add_todo_list_item(self, todo_id: str, item_data: TodoListItemCreateDTO) -> TodoResponseDTO:
        """Add item to todo list (checklist)"""
        todo = await self.todo_repository.get_by_id(todo_id)
        if not todo:
            raise ValueError(f"Todo with ID '{todo_id}' not found")

        item = TodoListItem(
            id=str(uuid.uuid4()),
            text=item_data.text,
            checked=item_data.checked,
            created_at=datetime.utcnow(),
        )

        todo.todo_lists.append(item)
        todo.updated_at = datetime.utcnow()

        updated_todo = await self.todo_repository.update(todo)
        return self._todo_to_dto(updated_todo)

    async def update_todo_list_item(self, todo_id: str, item_id: str, checked: bool) -> TodoResponseDTO:
        """Update todo list item (checklist item)"""
        todo = await self.todo_repository.get_by_id(todo_id)
        if not todo:
            raise ValueError(f"Todo with ID '{todo_id}' not found")

        item = next((item for item in todo.todo_lists if item.id == item_id), None)
        if not item:
            raise ValueError(f"Todo list item with ID '{item_id}' not found")

        item.checked = checked
        todo.updated_at = datetime.utcnow()

        updated_todo = await self.todo_repository.update(todo)
        return self._todo_to_dto(updated_todo)

    async def delete_todo_list_item(self, todo_id: str, item_id: str) -> TodoResponseDTO:
        """Delete todo list item (checklist item)"""
        todo = await self.todo_repository.get_by_id(todo_id)
        if not todo:
            raise ValueError(f"Todo with ID '{todo_id}' not found")

        todo.todo_lists = [item for item in todo.todo_lists if item.id != item_id]
        todo.updated_at = datetime.utcnow()

        updated_todo = await self.todo_repository.update(todo)
        return self._todo_to_dto(updated_todo)

    async def add_attachment(
        self,
        todo_id: str,
        filename: str,
        file_path: str,
        file_size: int,
        file_type: Optional[str] = None,
        is_background: bool = False,
    ) -> TodoResponseDTO:
        """Add attachment to todo (любой формат и расширение)."""
        todo = await self.todo_repository.get_by_id(todo_id)
        if not todo:
            raise ValueError(f"Todo with ID '{todo_id}' not found")
        attachment = TodoAttachment(
            id=str(uuid.uuid4()),
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
            is_background=is_background,
            created_at=datetime.utcnow(),
        )
        todo.attachments.append(attachment)
        todo.updated_at = datetime.utcnow()
        updated_todo = await self.todo_repository.update(todo)
        return self._todo_to_dto(updated_todo)

    async def delete_attachment(self, todo_id: str, attachment_id: str) -> TodoResponseDTO:
        """Remove attachment from todo and delete file from storage."""
        todo = await self.todo_repository.get_by_id(todo_id)
        if not todo:
            raise ValueError(f"Todo with ID '{todo_id}' not found")
        att = next((a for a in todo.attachments if a.id == attachment_id), None)
        if not att:
            raise ValueError(f"Attachment with ID '{attachment_id}' not found")
        from app.infrastructure.storage import delete_file
        delete_file(att.file_path)
        todo.attachments = [a for a in todo.attachments if a.id != attachment_id]
        todo.updated_at = datetime.utcnow()
        updated_todo = await self.todo_repository.update(todo)
        return self._todo_to_dto(updated_todo)

    def _todo_to_dto(self, todo: Todo) -> TodoResponseDTO:
        """Convert Todo entity to TodoResponseDTO"""
        return TodoResponseDTO(
            id=todo.id,
            title=todo.title,
            description=todo.description,
            status=todo.status,
            assigned_to=todo.assigned_to,
            tags=todo.tags,
            comments=[
                TodoCommentResponseDTO(
                    id=comment.id,
                    text=comment.text,
                    author_id=comment.author_id,
                    author_name=comment.author_name,
                    created_at=comment.created_at,
                )
                for comment in todo.comments
            ],
            todo_lists=[
                TodoListItemResponseDTO(
                    id=item.id,
                    text=item.text,
                    checked=item.checked,
                    created_at=item.created_at,
                )
                for item in todo.todo_lists
            ],
            attachments=[
                TodoAttachmentResponseDTO(
                    id=attachment.id,
                    filename=attachment.filename,
                    file_path=attachment.file_path,
                    file_type=attachment.file_type,
                    file_size=attachment.file_size,
                    is_background=attachment.is_background,
                    created_at=attachment.created_at,
                )
                for attachment in todo.attachments
            ],
            story_points=todo.story_points,
            in_focus=todo.in_focus,
            read=todo.read,
            project=todo.project,
            due_date=todo.due_date,
            all_day=getattr(todo, "all_day", False),
            notify_when_due=getattr(todo, "notify_when_due", False),
            calendar_only=getattr(todo, "calendar_only", False),
            created_by=todo.created_by,
            created_at=todo.created_at,
            updated_at=todo.updated_at,
            background_image=todo.background_image,
        )

