"""API dependencies"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.infrastructure.database.base import get_db
from app.infrastructure.repositories.user_repository_db import UserRepositoryDB
from app.infrastructure.repositories.ticket_repository_db import TicketRepositoryDB
from app.infrastructure.repositories.inventory_repository_db import InventoryRepositoryDB
from app.infrastructure.repositories.todo_repository_db import TodoRepositoryDB
from app.infrastructure.repositories.todo_column_repository_db import TodoColumnRepositoryDB
from app.application.use_cases.user_use_cases import UserUseCases
from app.application.use_cases.ticket_use_cases import TicketUseCases
from app.application.use_cases.inventory_use_cases import InventoryUseCases
from app.application.use_cases.todo_use_cases import TodoUseCases
from app.infrastructure.security.jwt import decode_access_token

# HTTP Bearer token scheme (optional for public endpoints)
security = HTTPBearer(auto_error=False)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepositoryDB:
    """Get user repository instance with database session"""
    return UserRepositoryDB(db)


def get_user_use_cases(db: Session = Depends(get_db)) -> UserUseCases:
    """Get user use cases instance with database session"""
    repository = get_user_repository(db)
    return UserUseCases(repository)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    use_cases: UserUseCases = Depends(get_user_use_cases),
) -> dict:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer token credentials
        use_cases: User use cases instance
    
    Returns:
        User data dictionary
    
    Raises:
        HTTPException: If token is invalid or user not found
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await use_cases.get_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is blocked",
        )
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "blocked": user.blocked,
    }


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get current active (non-blocked) user"""
    if current_user.get("blocked"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is blocked",
        )
    return current_user


def get_admin_user(
    current_user: dict = Depends(get_current_active_user),
) -> dict:
    """Get current admin user"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


def get_it_user(
    current_user: dict = Depends(get_current_active_user),
) -> dict:
    """Get current IT user"""
    if current_user.get("role") != "it":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


def get_admin_or_it_user(
    current_user: dict = Depends(get_current_active_user),
) -> dict:
    """Get current admin or IT user"""
    role = current_user.get("role")
    if role not in ["admin", "it"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


def get_ticket_repository(db: Session = Depends(get_db)) -> TicketRepositoryDB:
    """Get ticket repository instance with database session"""
    return TicketRepositoryDB(db)


def get_ticket_use_cases(db: Session = Depends(get_db)) -> TicketUseCases:
    """Get ticket use cases instance with database session"""
    ticket_repository = get_ticket_repository(db)
    user_repository = get_user_repository(db)
    return TicketUseCases(ticket_repository, user_repository)


def get_inventory_repository(db: Session = Depends(get_db)) -> InventoryRepositoryDB:
    """Get inventory repository instance with database session"""
    return InventoryRepositoryDB(db)


def get_inventory_use_cases(db: Session = Depends(get_db)) -> InventoryUseCases:
    """Get inventory use cases instance with database session"""
    repository = get_inventory_repository(db)
    return InventoryUseCases(repository)


def get_todo_repository(db: Session = Depends(get_db)) -> TodoRepositoryDB:
    """Get todo repository instance with database session"""
    return TodoRepositoryDB(db)


def get_todo_use_cases(db: Session = Depends(get_db)) -> TodoUseCases:
    """Get todo use cases instance with database session"""
    todo_repository = get_todo_repository(db)
    user_repository = get_user_repository(db)
    return TodoUseCases(todo_repository, user_repository)


def get_todo_column_repository(db: Session = Depends(get_db)) -> TodoColumnRepositoryDB:
    """Get todo column repository instance with database session"""
    return TodoColumnRepositoryDB(db)
