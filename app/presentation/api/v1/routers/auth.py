"""Authentication API router. Login by email only. No public registration."""
from fastapi import APIRouter, Depends, HTTPException, status
from app.application.dto.auth_dto import LoginDTO, TokenResponseDTO
from app.presentation.api.v1.dependencies import (
    get_user_use_cases,
    get_current_active_user,
)
from app.application.use_cases.user_use_cases import UserUseCases
from app.infrastructure.security.jwt import create_access_token
from app.infrastructure.config.settings import settings
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponseDTO)
async def login(
    login_data: LoginDTO,
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    """
    Log in by email only (no password). User must exist in DB.
    Users are added via POST /api/v1/users/ (admin).
    """
    user = await use_cases.authenticate_user(login_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is blocked",
        )

    access_token_expires = timedelta(hours=settings.JWT_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": user.id, "username": user.username, "role": user.role.value},
        expires_delta=access_token_expires,
    )
    return TokenResponseDTO(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_HOURS * 3600,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "blocked": user.blocked,
        },
    )


@router.get("/me", response_model=dict)
async def get_current_user_info(
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get current authenticated user information
    
    Requires valid JWT token in Authorization header
    """
    return current_user

