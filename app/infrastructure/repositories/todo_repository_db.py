"""PostgreSQL implementation of TodoRepository"""
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.domain.entities.todo import Todo, TodoComment, TodoListItem, TodoAttachment
# TodoStatus теперь строка
TodoStatus = str
from app.domain.repositories.todo_repository import TodoRepository
from app.infrastructure.database.models import (
    TodoModel, TodoCommentModel, TodoListItemModel, TodoAttachmentModel,
    TodoAssignmentModel, TodoTagModel
)


class TodoRepositoryDB(TodoRepository):
    """PostgreSQL implementation of TodoRepository"""

    def __init__(self, db: Session):
        self.db = db

    def _comment_model_to_entity(self, model: TodoCommentModel) -> TodoComment:
        """Convert TodoCommentModel to TodoComment entity"""
        return TodoComment(
            id=str(model.id),
            text=model.text,
            author_id=str(model.author_id),
            author_name=model.author_name,
            created_at=model.created_at,
        )

    def _list_item_model_to_entity(self, model: TodoListItemModel) -> TodoListItem:
        """Convert TodoListItemModel to TodoListItem entity"""
        return TodoListItem(
            id=str(model.id),
            text=model.text,
            checked=model.checked,
            created_at=model.created_at,
        )

    def _attachment_model_to_entity(self, model: TodoAttachmentModel) -> TodoAttachment:
        """Convert TodoAttachmentModel to TodoAttachment entity"""
        return TodoAttachment(
            id=str(model.id),
            filename=model.filename,
            file_path=model.file_path,
            file_type=model.file_type,
            file_size=int(model.file_size) if model.file_size else None,
            is_background=model.is_background,
            created_at=model.created_at,
        )

    def _todo_model_to_entity(self, model: TodoModel) -> Todo:
        """Convert TodoModel to Todo entity"""
        # Load relationships
        comments = [self._comment_model_to_entity(c) for c in model.comments]
        todo_lists = [self._list_item_model_to_entity(item) for item in model.todo_list_items]
        attachments = [self._attachment_model_to_entity(att) for att in model.attachments]
        
        # Get assigned users - need to query the association table
        assigned_to = [
            str(assignment.user_id) 
            for assignment in self.db.query(TodoAssignmentModel).filter(TodoAssignmentModel.todo_id == model.id).all()
        ]
        
        # Get tags
        tags = [
            tag.tag 
            for tag in self.db.query(TodoTagModel).filter(TodoTagModel.todo_id == model.id).all()
        ]
        
        return Todo(
            id=str(model.id),
            title=model.title,
            description=model.description,
            status=str(model.status) if model.status else "todo",
            assigned_to=assigned_to,
            tags=tags,
            comments=comments,
            todo_lists=todo_lists,
            attachments=attachments,
            story_points=model.story_points,
            in_focus=model.in_focus,
            read=model.read,
            project=model.project,
            due_date=model.due_date,
            created_by=str(model.created_by),
            created_at=model.created_at,
            updated_at=model.updated_at,
            background_image=model.background_image,
        )

    async def create(self, todo: Todo) -> Todo:
        """Create a new todo"""
        todo_model = TodoModel(
            id=todo.id if todo.id else None,
            title=todo.title,
            description=todo.description,
            status=todo.status,
            story_points=str(todo.story_points) if todo.story_points else None,
            in_focus=todo.in_focus,
            read=todo.read,
            project=todo.project,
            due_date=todo.due_date,
            background_image=todo.background_image,
            created_by=todo.created_by,
            created_at=todo.created_at,
            updated_at=todo.updated_at,
        )

        self.db.add(todo_model)
        self.db.flush()

        # Add assigned users
        for user_id in todo.assigned_to:
            assignment = TodoAssignmentModel(todo_id=todo_model.id, user_id=user_id)
            self.db.add(assignment)

        # Add tags
        for tag in todo.tags:
            tag_model = TodoTagModel(todo_id=todo_model.id, tag=tag)
            self.db.add(tag_model)

        # Add comments
        for comment in todo.comments:
            comment_model = TodoCommentModel(
                id=comment.id if comment.id else None,
                text=comment.text,
                todo_id=todo_model.id,
                author_id=comment.author_id,
                author_name=comment.author_name,
                created_at=comment.created_at,
            )
            self.db.add(comment_model)

        # Add todo list items
        for item in todo.todo_lists:
            item_model = TodoListItemModel(
                id=item.id if item.id else None,
                text=item.text,
                checked=item.checked,
                todo_id=todo_model.id,
                created_at=item.created_at,
            )
            self.db.add(item_model)

        # Add attachments
        for attachment in todo.attachments:
            attachment_model = TodoAttachmentModel(
                id=attachment.id if attachment.id else None,
                filename=attachment.filename,
                file_path=attachment.file_path,
                file_type=attachment.file_type,
                file_size=str(attachment.file_size) if attachment.file_size else None,
                is_background=attachment.is_background,
                todo_id=todo_model.id,
                created_at=attachment.created_at,
            )
            self.db.add(attachment_model)

        self.db.commit()
        self.db.refresh(todo_model)

        # Reload with all relationships
        todo_model = self.db.query(TodoModel).options(
            joinedload(TodoModel.comments),
            joinedload(TodoModel.todo_list_items),
            joinedload(TodoModel.attachments),
            joinedload(TodoModel.assigned_users),
        ).filter(TodoModel.id == todo_model.id).first()

        return self._todo_model_to_entity(todo_model)

    async def get_by_id(self, todo_id: str) -> Optional[Todo]:
        """Get todo by ID"""
        todo_model = self.db.query(TodoModel).options(
            joinedload(TodoModel.comments),
            joinedload(TodoModel.todo_list_items),
            joinedload(TodoModel.attachments),
            joinedload(TodoModel.assigned_users),
        ).filter(TodoModel.id == todo_id).first()
        
        if not todo_model:
            return None
        return self._todo_model_to_entity(todo_model)

    async def get_all(self) -> List[Todo]:
        """Get all todos"""
        todo_models = self.db.query(TodoModel).options(
            joinedload(TodoModel.comments),
            joinedload(TodoModel.todo_list_items),
            joinedload(TodoModel.attachments),
            joinedload(TodoModel.assigned_users),
        ).order_by(TodoModel.created_at.desc()).all()
        return [self._todo_model_to_entity(model) for model in todo_models]

    async def get_by_user_id(self, user_id: str, include_archived: bool = False) -> List[Todo]:
        """Get todos by user ID (created by or assigned to)
        
        Args:
            user_id: User ID
            include_archived: If True, includes archived todos. Default False (excludes archived).
        """
        query = self.db.query(TodoModel).options(
            joinedload(TodoModel.comments),
            joinedload(TodoModel.todo_list_items),
            joinedload(TodoModel.attachments),
            joinedload(TodoModel.assigned_users),
        ).filter(
            (TodoModel.created_by == user_id) |
            (TodoModel.assigned_users.any(TodoAssignmentModel.user_id == user_id))
        )
        
        # Exclude archived todos by default
        if not include_archived:
            query = query.filter(TodoModel.status != "archived")
        
        todo_models = query.order_by(TodoModel.created_at.desc()).all()
        return [self._todo_model_to_entity(model) for model in todo_models]
    
    async def get_archived_by_user_id(self, user_id: str) -> List[Todo]:
        """Get archived todos by user ID (created by or assigned to)"""
        todo_models = self.db.query(TodoModel).options(
            joinedload(TodoModel.comments),
            joinedload(TodoModel.todo_list_items),
            joinedload(TodoModel.attachments),
            joinedload(TodoModel.assigned_users),
        ).filter(
            (TodoModel.created_by == user_id) |
            (TodoModel.assigned_users.any(TodoAssignmentModel.user_id == user_id)),
            TodoModel.status == "archived"
        ).order_by(TodoModel.created_at.desc()).all()
        return [self._todo_model_to_entity(model) for model in todo_models]

    async def get_by_status(self, status: str) -> List[Todo]:
        """Get todos by status"""
        todo_models = self.db.query(TodoModel).options(
            joinedload(TodoModel.comments),
            joinedload(TodoModel.todo_list_items),
            joinedload(TodoModel.attachments),
            joinedload(TodoModel.assigned_users),
        ).filter(TodoModel.status == status).order_by(TodoModel.created_at.desc()).all()
        return [self._todo_model_to_entity(model) for model in todo_models]

    async def update(self, todo: Todo) -> Todo:
        """Update todo"""
        todo_model = self.db.query(TodoModel).filter(TodoModel.id == todo.id).first()
        if not todo_model:
            raise ValueError(f"Todo with ID '{todo.id}' not found")

        todo_model.title = todo.title
        todo_model.description = todo.description
        todo_model.status = todo.status
        todo_model.story_points = str(todo.story_points) if todo.story_points else None
        todo_model.in_focus = todo.in_focus
        todo_model.read = todo.read
        todo_model.project = todo.project
        todo_model.due_date = todo.due_date
        todo_model.background_image = todo.background_image
        todo_model.updated_at = todo.updated_at

        # Update assigned users
        self.db.query(TodoAssignmentModel).filter(TodoAssignmentModel.todo_id == todo.id).delete()
        for user_id in todo.assigned_to:
            assignment = TodoAssignmentModel(todo_id=todo.id, user_id=user_id)
            self.db.add(assignment)

        # Update tags
        self.db.query(TodoTagModel).filter(TodoTagModel.todo_id == todo.id).delete()
        for tag in todo.tags:
            tag_model = TodoTagModel(todo_id=todo.id, tag=tag)
            self.db.add(tag_model)

        # Update comments (delete old, add new)
        self.db.query(TodoCommentModel).filter(TodoCommentModel.todo_id == todo.id).delete()
        for comment in todo.comments:
            comment_model = TodoCommentModel(
                id=comment.id if comment.id else None,
                text=comment.text,
                todo_id=todo.id,
                author_id=comment.author_id,
                author_name=comment.author_name,
                created_at=comment.created_at,
            )
            self.db.add(comment_model)

        # Update todo list items
        self.db.query(TodoListItemModel).filter(TodoListItemModel.todo_id == todo.id).delete()
        for item in todo.todo_lists:
            item_model = TodoListItemModel(
                id=item.id if item.id else None,
                text=item.text,
                checked=item.checked,
                todo_id=todo.id,
                created_at=item.created_at,
            )
            self.db.add(item_model)

        # Update attachments
        self.db.query(TodoAttachmentModel).filter(TodoAttachmentModel.todo_id == todo.id).delete()
        for attachment in todo.attachments:
            attachment_model = TodoAttachmentModel(
                id=attachment.id if attachment.id else None,
                filename=attachment.filename,
                file_path=attachment.file_path,
                file_type=attachment.file_type,
                file_size=str(attachment.file_size) if attachment.file_size else None,
                is_background=attachment.is_background,
                todo_id=todo.id,
                created_at=attachment.created_at,
            )
            self.db.add(attachment_model)

        self.db.commit()
        self.db.refresh(todo_model)

        # Reload with all relationships
        todo_model = self.db.query(TodoModel).options(
            joinedload(TodoModel.comments),
            joinedload(TodoModel.todo_list_items),
            joinedload(TodoModel.attachments),
            joinedload(TodoModel.assigned_users),
        ).filter(TodoModel.id == todo.id).first()

        return self._todo_model_to_entity(todo_model)

    async def delete(self, todo_id: str) -> bool:
        """Delete todo permanently"""
        todo_model = self.db.query(TodoModel).filter(TodoModel.id == todo_id).first()
        if not todo_model:
            return False

        self.db.delete(todo_model)
        self.db.commit()
        return True

