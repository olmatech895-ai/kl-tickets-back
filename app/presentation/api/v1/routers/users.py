"""Users API router"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.application.dto.user_dto import (
    UserCreateDTO,
    UserUpdateDTO,
    UserResponseDTO,
)
from app.presentation.api.v1.dependencies import (
    get_user_use_cases,
    get_current_active_user,
    get_admin_user,
    get_it_user,
    get_admin_or_it_user,
)
from app.application.use_cases.user_use_cases import UserUseCases

router = APIRouter(prefix="/users", tags=["users"], redirect_slashes=False)


@router.post("/", response_model=UserResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateDTO,
    use_cases: UserUseCases = Depends(get_user_use_cases),
    current_user: dict = Depends(get_admin_user),
):
    """Add a new user. Admin only. This is the only way to create users (no public registration)."""
    try:
        from app.domain.entities.user import UserRole
        # Get role from current user
        creator_role = UserRole(current_user.get("role"))
        return await use_cases.create_user(user_data, created_by_role=creator_role)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=List[UserResponseDTO])
async def get_all_users(
    use_cases: UserUseCases = Depends(get_user_use_cases),
    current_user: dict = Depends(get_current_active_user),  # Requires authentication
):
    """Get all users (Requires authentication)"""
    return await use_cases.get_all_users()


@router.get("/{user_id}", response_model=UserResponseDTO)
async def get_user(
    user_id: str,
    use_cases: UserUseCases = Depends(get_user_use_cases),
    current_user: dict = Depends(get_current_active_user),  # Requires authentication
):
    """Get user by ID (Requires authentication)"""
    user = await use_cases.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )
    return user


@router.put("/{user_id}", response_model=UserResponseDTO)
async def update_user(
    user_id: str,
    user_data: UserUpdateDTO,
    use_cases: UserUseCases = Depends(get_user_use_cases),
    current_user: dict = Depends(get_admin_user),  # Only admin can update users
):
    """Update user (Admin only)"""
    user = await use_cases.update_user(user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    use_cases: UserUseCases = Depends(get_user_use_cases),
    current_user: dict = Depends(get_admin_user),  # Only admin can delete users
):
    """Delete user (Admin only)
    
    Before deleting, handles related data:
    - Tickets created by user: deleted (cascade deletes comments)
    - Tickets assigned to user: assigned_to set to NULL
    - Todos created by user: deleted (cascade handles related data)
    - Inventory items: responsible set to NULL
    - Comments by user in other tickets: kept (author_name is denormalized)
    """
    try:
        # Prevent self-deletion
        if user_id == current_user.get("id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot delete your own account",
            )
        
        success = await use_cases.delete_user(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found",
            )
    except ValueError as e:
        # Handle validation errors from repository
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        # Handle unexpected errors
        print(f"❌ Error deleting user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}",
        )

