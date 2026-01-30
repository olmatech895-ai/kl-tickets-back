"""Telegram bot database models"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.infrastructure.database.base import Base
from app.infrastructure.config.settings import settings
from datetime import datetime
import uuid

def get_id_column():
    """Get ID column based on database type"""
    if settings.DATABASE_TYPE == "postgresql":
        return Column(PG_UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    else:
        return Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

class UserTelegramModel(Base):
    """User Telegram chat ID mapping"""
    __tablename__ = "user_telegram"

    id = get_id_column()
    
    # Foreign key to user
    user_id = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Telegram chat ID (unique per user)
    telegram_chat_id = Column(String(50), nullable=False, unique=True, index=True)
    
    # User info for notifications
    username = Column(String(100), nullable=True)  # Telegram username
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    user = relationship("UserModel", foreign_keys=[user_id])


class TelegramLinkTokenModel(Base):
    """Temporary token for linking Telegram account"""
    __tablename__ = "telegram_link_tokens"

    id = get_id_column()
    
    # Foreign key to user
    user_id = Column(
        PG_UUID(as_uuid=False) if settings.DATABASE_TYPE == "postgresql" else String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Unique token for deep linking
    token = Column(String(64), nullable=False, unique=True, index=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=False)
    
    # Status
    used = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    user = relationship("UserModel", foreign_keys=[user_id])
