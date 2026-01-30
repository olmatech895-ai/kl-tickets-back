"""Authentication API router"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.application.dto.auth_dto import RegisterDTO, LoginDTO, TokenResponseDTO
from app.application.dto.user_dto import UserCreateDTO, UserResponseDTO
from app.domain.entities.user import UserRole
from app.presentation.api.v1.dependencies import (
    get_user_use_cases,
    get_current_active_user,
)
from app.application.use_cases.user_use_cases import UserUseCases
from app.infrastructure.security.jwt import create_access_token
from app.infrastructure.config.settings import settings
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=TokenResponseDTO, status_code=status.HTTP_201_CREATED)
async def register(
    register_data: RegisterDTO,
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    """
    Register a new user and return JWT token
    
    Validates:
    - Username uniqueness
    - Email domain (@kostalegal.com)
    - Email uniqueness
    - Role: Only USER role allowed for public registration
    """
    try:
        # Only allow USER role for public registration
        # Admin and IT roles can only be assigned by existing admins
        if register_data.role != UserRole.USER:
            raise ValueError("Only USER role can be assigned during registration. Admin and IT roles must be assigned by an administrator.")
        
        # Convert RegisterDTO to UserCreateDTO
        user_create_dto = UserCreateDTO(
            username=register_data.username,
            email=register_data.email,
            password=register_data.password,
            role=UserRole.USER,  # Force USER role for public registration
        )

        # Create user
        print(f"Creating user: {register_data.username}")  # Debug
        user = await use_cases.create_user(user_create_dto)
        print(f"User created successfully: {user.username}, ID: {user.id}")  # Debug

        # Create access token
        access_token_expires = timedelta(hours=settings.JWT_EXPIRE_HOURS)
        access_token = create_access_token(
            data={"sub": user.id, "username": user.username, "role": user.role.value},
            expires_delta=access_token_expires,
        )

        return TokenResponseDTO(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.JWT_EXPIRE_HOURS * 3600,  # Convert hours to seconds
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "blocked": user.blocked,
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenResponseDTO)
async def login(
    login_data: LoginDTO,
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    """
    Authenticate user and return JWT token
    
    Returns:
        TokenResponseDTO with access token and user data
    """
    # Authenticate user
    print(f"Login attempt for username: {login_data.username}")  # Debug
    user = await use_cases.authenticate_user(login_data.username, login_data.password)
    
    if not user:
        print(f"Authentication failed for username: {login_data.username}")  # Debug
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"Authentication successful for user: {user.username}")  # Debug
    
    if user.blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is blocked",
        )

    # Create access token
    access_token_expires = timedelta(hours=settings.JWT_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": user.id, "username": user.username, "role": user.role.value},
        expires_delta=access_token_expires,
    )

    return TokenResponseDTO(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRE_HOURS * 3600,  # Convert hours to seconds
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

