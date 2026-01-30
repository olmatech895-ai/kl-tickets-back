"""SQLAlchemy database models"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from datetime import datetime
from app.infrastructure.database.base import Base
from app.infrastructure.config.settings import settings
from app.domain.entities.user import UserRole
from app.domain.entities.ticket import TicketPriority, TicketStatus, TicketCategory
from app.domain.entities.inventory import InventoryStatus
# TodoStatus теперь строка, не нужен импорт
from sqlalchemy import JSON


def get_id_column():
    """Get ID column based on database type"""
    if settings.DATABASE_TYPE == "postgresql":
        return Column(PG_UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    else:
        return Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


def get_foreign_key_column(foreign_table):
    """Get foreign key column based on database type"""
    if settings.DATABASE_TYPE == "postgresql":
        return Column(PG_UUID(as_uuid=False), ForeignKey(foreign_table), nullable=False)
    else:
        return Column(String(36), ForeignKey(foreign_table), nullable=False)


def get_foreign_key_column_nullable(foreign_table):
    """Get nullable foreign key column based on database type"""
    if settings.DATABASE_TYPE == "postgresql":
        return Column(PG_UUID(as_uuid=False), ForeignKey(foreign_table), nullable=True)
    else:
        return Column(String(36), ForeignKey(foreign_table), nullable=True)


class UserModel(Base):
    """User database model"""
    __tablename__ = "users"

    id = get_id_column()
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole, native_enum=False), nullable=False, default=UserRole.USER)
    blocked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    created_tickets = relationship("TicketModel", back_populates="creator", foreign_keys="TicketModel.created_by")
    assigned_tickets = relationship("TicketModel", back_populates="assignee", foreign_keys="TicketModel.assigned_to")
    comments = relationship("CommentModel", back_populates="author")
    assigned_todos = relationship("TodoModel", secondary="todo_assignments", back_populates="assigned_users")


class TicketModel(Base):
    """Ticket database model"""
    __tablename__ = "tickets"

    id = get_id_column()
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(SQLEnum(TicketPriority, native_enum=False), nullable=False, default=TicketPriority.MEDIUM)
    status = Column(SQLEnum(TicketStatus, native_enum=False), nullable=False, default=TicketStatus.OPEN)
    category = Column(SQLEnum(TicketCategory, native_enum=False), nullable=False, default=TicketCategory.OTHER)
    
    # Foreign keys - use appropriate type based on database
    created_by = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    assigned_to = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )
    
    # Denormalized fields for performance (can be removed if needed)
    created_by_name = Column(String(100), nullable=False)
    created_by_email = Column(String(255), nullable=True)
    assigned_to_name = Column(String(100), nullable=True)
    estimated_time = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = relationship("UserModel", foreign_keys=[created_by], back_populates="created_tickets")
    assignee = relationship("UserModel", foreign_keys=[assigned_to], back_populates="assigned_tickets")
    comments = relationship("CommentModel", back_populates="ticket", cascade="all, delete-orphan", order_by="CommentModel.created_at")


class CommentModel(Base):
    """Comment database model"""
    __tablename__ = "comments"

    id = get_id_column()
    text = Column(Text, nullable=False)
    
    # Foreign keys - use appropriate type based on database
    ticket_id = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    author_id = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Denormalized field for performance
    author_name = Column(String(100), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    ticket = relationship("TicketModel", back_populates="comments")
    author = relationship("UserModel", back_populates="comments")


class InventoryModel(Base):
    """Inventory item database model"""
    __tablename__ = "inventory"

    id = get_id_column()
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    serial_number = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    status = Column(SQLEnum(InventoryStatus, native_enum=False), nullable=False, default=InventoryStatus.WORKING)
    description = Column(Text, nullable=True)
    photo = Column(Text, nullable=True)  # Store as base64 or URL
    
    # Foreign key to user (responsible)
    responsible = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    responsible_user = relationship("UserModel", foreign_keys=[responsible])


class TodoModel(Base):
    """Todo database model"""
    __tablename__ = "todos"

    id = get_id_column()
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(100), nullable=False, default="todo", index=True)
    story_points = Column(String(10), nullable=True)
    in_focus = Column(Boolean, default=False, nullable=False)
    read = Column(Boolean, default=True, nullable=False)
    project = Column(String(100), nullable=True)
    due_date = Column(DateTime, nullable=True)
    background_image = Column(Text, nullable=True)
    
    # Foreign key to user (created by)
    created_by = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = relationship("UserModel", foreign_keys=[created_by])
    comments = relationship("TodoCommentModel", back_populates="todo", cascade="all, delete-orphan", order_by="TodoCommentModel.created_at")
    todo_list_items = relationship("TodoListItemModel", back_populates="todo", cascade="all, delete-orphan", order_by="TodoListItemModel.created_at")
    attachments = relationship("TodoAttachmentModel", back_populates="todo", cascade="all, delete-orphan", order_by="TodoAttachmentModel.created_at")
    assigned_users = relationship("UserModel", secondary="todo_assignments", back_populates="assigned_todos")


class TodoAssignmentModel(Base):
    """Many-to-many relationship between todos and users (assigned to)"""
    __tablename__ = "todo_assignments"

    todo_id = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("todos.id", ondelete="CASCADE"),
        primary_key=True
    )
    user_id = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )


class TodoTagModel(Base):
    """Many-to-many relationship between todos and tags"""
    __tablename__ = "todo_tags"

    todo_id = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("todos.id", ondelete="CASCADE"),
        primary_key=True
    )
    tag = Column(String(50), primary_key=True, nullable=False)


class TodoCommentModel(Base):
    """Todo comment database model"""
    __tablename__ = "todo_comments"

    id = get_id_column()
    text = Column(Text, nullable=False)
    
    # Foreign keys
    todo_id = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("todos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    author_id = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Denormalized field for performance
    author_name = Column(String(100), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    todo = relationship("TodoModel", back_populates="comments")
    author = relationship("UserModel")


class TodoListItemModel(Base):
    """Todo list item (checklist item) database model"""
    __tablename__ = "todo_list_items"

    id = get_id_column()
    text = Column(String(500), nullable=False)
    checked = Column(Boolean, default=False, nullable=False)
    
    # Foreign key
    todo_id = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("todos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    todo = relationship("TodoModel", back_populates="todo_list_items")


class TodoAttachmentModel(Base):
    """Todo attachment database model"""
    __tablename__ = "todo_attachments"

    id = get_id_column()
    filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_type = Column(String(50), nullable=True)
    file_size = Column(String(20), nullable=True)
    is_background = Column(Boolean, default=False, nullable=False)
    
    # Foreign key
    todo_id = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("todos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    todo = relationship("TodoModel", back_populates="attachments")


class TodoColumnModel(Base):
    """Todo board column database model"""
    __tablename__ = "todo_columns"

    id = get_id_column()
    column_id = Column(String(100), nullable=False, index=True)  # Frontend column ID (not unique, as each user has their own)
    title = Column(String(255), nullable=False)
    status = Column(String(100), nullable=False, index=True)  # todo, in_progress, done, or custom
    color = Column(String(50), nullable=False, default='primary')
    background_image = Column(Text, nullable=True)  # Base64 or URL
    order_index = Column(String(10), nullable=False, default='0')  # Order of column
    
    # Foreign key to user (each user has their own columns)
    # Note: This column may not exist in older databases - code handles this gracefully
    # Using String(36) to match VARCHAR(36) in database (UUID stored as string)
    user_id = Column(
        String(36),  # VARCHAR(36) - UUID stored as string
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,  # Made nullable to support backward compatibility
        index=True
    )
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Unique constraint: column_id must be unique per user
    __table_args__ = (
        {'sqlite_autoincrement': True} if settings.DATABASE_TYPE == "sqlite" else {},
    )


# Import Telegram models
from app.infrastructure.telegram.models import UserTelegramModel, TelegramLinkTokenModel

