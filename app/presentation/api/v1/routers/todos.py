"""Todos API router"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.application.dto.todo_dto import (
    TodoCreateDTO,
    TodoUpdateDTO,
    TodoResponseDTO,
    TodoCommentCreateDTO,
    TodoCommentResponseDTO,
    TodoListItemCreateDTO,
    TodoListItemUpdateDTO,
    TodoListItemResponseDTO,
    TodoColumnCreateDTO,
    TodoColumnUpdateDTO,
    TodoColumnResponseDTO,
    TodoColumnsUpdateDTO,
)
from app.presentation.api.v1.dependencies import (
    get_todo_use_cases,
    get_current_active_user,
    get_todo_column_repository,
)
from app.application.use_cases.todo_use_cases import TodoUseCases
from app.infrastructure.websocket import manager
from app.infrastructure.telegram.bot import telegram_bot

router = APIRouter(prefix="/todos", tags=["todos"], redirect_slashes=False)


@router.post("/", response_model=TodoResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_todo(
    todo_data: TodoCreateDTO,
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Create a new todo
    
    Any authenticated user can create a todo.
    """
    try:
        todo = await use_cases.create_todo(todo_data, current_user["id"])
        
        # Convert todo to dict for WebSocket
        if hasattr(todo, 'model_dump'):
            todo_dict = todo.model_dump(mode='json')
        elif hasattr(todo, 'dict'):
            todo_dict = todo.dict()
        else:
            todo_dict = todo
        
        # Broadcast todo_created event only to users who should see this todo
        # (creator + assigned users)
        try:
            event = {
                "type": "todo_created",
                "todo": todo_dict,
            }
            # Get list of users who should receive this update
            users_to_notify = [todo_dict.get("created_by")]
            if todo_dict.get("assigned_to"):
                users_to_notify.extend(todo_dict["assigned_to"])
            # Remove duplicates
            users_to_notify = list(set(users_to_notify))
            # Broadcast only to relevant users
            await manager.broadcast_to_users(event, users_to_notify)
        except Exception as ws_error:
            # Silently ignore WebSocket errors
            pass
        
        # Send Telegram notifications to assigned users
        try:
            creator_info = telegram_bot.get_user_info(current_user["id"])
            creator_name = creator_info["username"] if creator_info else current_user.get("username", "Неизвестный")
            
            assigned_users = todo_dict.get("assigned_to", [])
            # Notify assigned users (excluding creator)
            for assigned_user_id in assigned_users:
                if assigned_user_id != current_user["id"]:
                    await telegram_bot.notify_task_assigned(
                        assigned_user_id,
                        todo_dict.get("title", "Новая задача"),
                        creator_name
                    )
        except Exception as tg_error:
            # Silently ignore Telegram errors
            pass
        
        return todo
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=List[TodoResponseDTO])
async def get_all_todos(
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Get all todos for current user
    
    Each user sees only their own todos:
    - Todos created by the user
    - Todos where the user is assigned (in assigned_to list)
    
    When a user adds someone to assigned_to, the todo becomes shared for all assigned users.
    """
    # Все пользователи (включая admin/it) видят только свои todos
    return await use_cases.get_user_todos(current_user["id"])


@router.get("/my", response_model=List[TodoResponseDTO])
async def get_my_todos(
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Get current user's todos"""
    return await use_cases.get_user_todos(current_user["id"])


@router.get("/status/{status}", response_model=List[TodoResponseDTO])
async def get_todos_by_status(
    status: str,
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Get todos by status for current user
    
    Returns todos with the specified status that belong to the current user
    (created by them or where they are assigned).
    """
    # Все пользователи видят только свои todos по статусу
    all_user_todos = await use_cases.get_user_todos(current_user["id"])
    return [todo for todo in all_user_todos if todo.status == status]


@router.get("/archived", response_model=List[TodoResponseDTO])
async def get_archived_todos(
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Get all archived todos for current user
    
    Returns todos with status 'archived' that belong to the current user
    (created by them or where they are assigned).
    """
    return await use_cases.get_user_archived_todos(current_user["id"])


# ========== Todo Columns Endpoints (должны быть ПЕРЕД /{todo_id}) ==========

@router.get("/columns", response_model=List[TodoColumnResponseDTO])
async def get_todo_columns(
    column_repo = Depends(get_todo_column_repository),
    current_user: dict = Depends(get_current_active_user),
):
    """Get all todo board columns for current user
    
    Each user sees only their own columns.
    If no columns exist, returns empty list - user needs to create columns via POST /columns.
    
    Note: Requires user_id column in database. See RUN_MIGRATION.md if you get migration error.
    """
    try:
        # Check if user_id column exists
        has_user_id = column_repo._has_user_id_column()
        if not has_user_id:
            # Return empty list and suggest migration
            return []
        
        columns = await column_repo.get_all(user_id=current_user["id"])
        # Convert models to DTOs
        columns_response = [
            TodoColumnResponseDTO(
                id=str(col.id),
                column_id=col.column_id,
                title=col.title,
                status=col.status,
                color=col.color,
                background_image=col.background_image,
                order_index=col.order_index,
                created_at=col.created_at,
                updated_at=col.updated_at,
            )
            for col in columns
        ]
        return columns_response
    except Exception as e:
        print(f"❌ Error getting todo columns: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting columns: {str(e)}",
        )


@router.post("/columns", response_model=List[TodoColumnResponseDTO])
async def update_todo_columns(
    columns_data: TodoColumnsUpdateDTO,
    column_repo = Depends(get_todo_column_repository),
    current_user: dict = Depends(get_current_active_user),
):
    """Update all todo board columns (replace all)
    
    This endpoint replaces all existing columns for the current user with the provided ones.
    Each user has their own columns - they cannot see or modify other users' columns.
    Requires authentication.
    
    Note: If user_id column doesn't exist in database, you need to run migration first.
    See RUN_MIGRATION.md for instructions.
    """
    try:
        # Validate input
        if not columns_data.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No columns provided. At least one column is required.",
            )
        
        # Check if user_id column exists
        has_user_id = column_repo._has_user_id_column()
        if not has_user_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database migration required: user_id column is missing. Please run migration (see RUN_MIGRATION.md). Without this column, columns cannot be isolated per user.",
            )
        
        # Convert DTOs to dicts
        columns_dict = []
        for col in columns_data.columns:
            if not col.column_id or not col.title or not col.status:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid column data: column_id, title, and status are required. Got: {col}",
                )
            columns_dict.append({
                "column_id": col.column_id,
                "title": col.title,
                "status": col.status,
                "color": col.color or "primary",
                "background_image": col.background_image,
                "order_index": col.order_index or "0",
            })
        
        # Bulk create (replaces all columns for current user only)
        columns = await column_repo.bulk_create(columns_dict, user_id=current_user["id"])
        
        # Convert to response DTOs
        columns_response = [
            TodoColumnResponseDTO(
                id=str(col.id),
                column_id=col.column_id,
                title=col.title,
                status=col.status,
                color=col.color,
                background_image=col.background_image,
                order_index=col.order_index,
                created_at=col.created_at,
                updated_at=col.updated_at,
            )
            for col in columns
        ]
        
        # Broadcast columns update only to current user via WebSocket
        try:
            await manager.broadcast_to_users({
                "type": "columns_updated",
                "columns": [
                    {
                        "id": col.column_id,
                        "title": col.title,
                        "status": col.status,
                        "color": col.color,
                        "backgroundImage": col.background_image,
                        "orderIndex": col.order_index,
                    }
                    for col in columns_response
                ]
            }, [current_user["id"]])
        except Exception as ws_error:
            # Silently ignore WebSocket errors
            pass
        
        return columns_response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        print(f"❌ Error updating todo columns: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating columns: {str(e)}",
        )


@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo_column(
    column_id: str,
    column_repo = Depends(get_todo_column_repository),
    current_user: dict = Depends(get_current_active_user),
):
    """Delete a todo column
    
    User can only delete their own columns.
    Each user has isolated columns - they cannot delete other users' columns.
    """
    try:
        # Check if user_id column exists
        has_user_id = column_repo._has_user_id_column()
        if not has_user_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database migration required: user_id column is missing. Please run migration (see RUN_MIGRATION.md). Without this column, columns cannot be isolated per user.",
            )
        
        # Check if column exists and belongs to user
        column = await column_repo.get_by_column_id(column_id, user_id=current_user["id"])
        if not column:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Column with ID '{column_id}' not found or you don't have permission to delete it",
            )
        
        # Delete the column (only user's own column)
        deleted = await column_repo.delete(column_id, user_id=current_user["id"])
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Column with ID '{column_id}' not found",
            )
        
        # Broadcast column deleted event only to current user
        try:
            await manager.broadcast_to_users({
                "type": "column_deleted",
                "column_id": column_id,
            }, [current_user["id"]])
        except Exception as ws_error:
            # Silently ignore WebSocket errors
            pass
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting todo column: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting column: {str(e)}",
        )


@router.get("/{todo_id}", response_model=TodoResponseDTO)
async def get_todo(
    todo_id: str,
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Get todo by ID
    
    User can only see todos:
    - Created by them
    - Where they are assigned (in assigned_to list)
    
    When a user adds someone to assigned_to, that person can also see the todo.
    """
    todo = await use_cases.get_todo(todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID '{todo_id}' not found",
        )
    
    # Check permissions - все пользователи (включая admin/it) могут видеть только свои todos
    if todo.created_by != current_user["id"] and current_user["id"] not in todo.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view this todo. You can only see todos you created or are assigned to.",
        )
    
    return todo


@router.put("/{todo_id}", response_model=TodoResponseDTO)
async def update_todo(
    todo_id: str,
    todo_data: TodoUpdateDTO,
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Update todo
    
    User can update todos:
    - Created by them
    - Where they are assigned (in assigned_to list)
    
    When updating assigned_to, the todo becomes shared for all users in the list.
    """
    # Check permissions
    existing_todo = await use_cases.get_todo(todo_id)
    if not existing_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID '{todo_id}' not found",
        )
    
    # Все пользователи (включая admin/it) могут обновлять только свои todos
    if existing_todo.created_by != current_user["id"] and current_user["id"] not in existing_todo.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to update this todo. You can only update todos you created or are assigned to.",
        )
    
    try:
        todo = await use_cases.update_todo(todo_id, todo_data)
        
        # Convert todo to dict for WebSocket
        if hasattr(todo, 'model_dump'):
            todo_dict = todo.model_dump(mode='json')
        elif hasattr(todo, 'dict'):
            todo_dict = todo.dict()
        else:
            todo_dict = todo
        
        # Broadcast todo_updated event only to users who should see this todo
        try:
            event = {
                "type": "todo_updated",
                "todo": todo_dict,
            }
            # Get list of users who should receive this update
            users_to_notify = [todo_dict.get("created_by")]
            if todo_dict.get("assigned_to"):
                users_to_notify.extend(todo_dict["assigned_to"])
            # Remove duplicates
            users_to_notify = list(set(users_to_notify))
            # Broadcast only to relevant users
            await manager.broadcast_to_users(event, users_to_notify)
        except Exception as ws_error:
            # Silently ignore WebSocket errors
            pass
        
        # Send Telegram notifications for changes made by OTHER users
        try:
            creator_id = existing_todo.created_by
            current_user_id = current_user["id"]
            
            # Get creator info for notifications
            creator_info = telegram_bot.get_user_info(creator_id)
            creator_name = creator_info["username"] if creator_info else current_user.get("username", "Неизвестный")
            
            # Check if assigned_to changed - notify newly assigned users
            if todo_data.assigned_to is not None:
                old_assigned_to = set(existing_todo.assigned_to or [])
                new_assigned_to = set(todo_data.assigned_to)
                
                # Find newly assigned users (in new but not in old)
                newly_assigned = new_assigned_to - old_assigned_to
                
                # Отправляем уведомления всем новым пользователям
                for user_id in newly_assigned:
                    # Не отправляем уведомление самому создателю, если он добавил себя
                    if user_id != creator_id:
                        await telegram_bot.notify_task_assigned(
                            user_id,
                            todo_dict.get("title", "Задача"),
                            creator_name
                        )
            
            # Не отправляем уведомление, если создатель сам изменил задачу
            if creator_id == current_user_id:
                # Создатель сам изменил задачу - уведомления о статусе/чекбоксах не нужны
                pass
            else:
                # Другой пользователь изменил задачу - отправляем уведомление создателю
                old_status = existing_todo.status
                new_status = todo_dict.get("status")
                
                # Get current user info (who made the change)
                updater_info = telegram_bot.get_user_info(current_user_id)
                updater_name = updater_info["username"] if updater_info else current_user.get("username", "Неизвестный")
                
                # Check if status changed
                if new_status and new_status != old_status:
                    # Notify creator if they are admin/IT
                    if telegram_bot.is_admin(creator_id):
                        if new_status == "done":
                            # Task completed
                            await telegram_bot.notify_task_completed(
                                creator_id,
                                todo_dict.get("title", "Задача"),
                                updater_name
                            )
                        else:
                            # Task moved to different status
                            await telegram_bot.notify_task_moved(
                                creator_id,
                                todo_dict.get("title", "Задача"),
                                old_status,
                                new_status,
                                updater_name
                            )
                
                # Check if todo_lists (checkboxes) changed
                if todo_data.todo_lists is not None:
                    old_todo_lists = existing_todo.todo_lists or []
                    new_todo_lists = todo_data.todo_lists  # Используем данные из запроса, а не из обновленного todo
                    
                    # Find changed checkboxes
                    old_items_dict = {item.id: item.checked for item in old_todo_lists}
                    
                    for new_item in new_todo_lists:
                        item_id = new_item.id if hasattr(new_item, 'id') else None
                        new_checked = new_item.checked if hasattr(new_item, 'checked') else False
                        item_text = new_item.text if hasattr(new_item, 'text') else ""
                        
                        if item_id and item_id in old_items_dict:
                            old_checked = old_items_dict[item_id]
                            if old_checked != new_checked:
                                # Checkbox changed - notify creator
                                await telegram_bot.notify_checkbox_updated(
                                    creator_id,
                                    todo_dict.get("title", "Задача"),
                                    item_text,
                                    new_checked,
                                    updater_name
                                )
        except Exception as tg_error:
            # Silently ignore Telegram errors
            pass
        
        return todo
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    todo_id: str,
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Delete todo permanently
    
    User can only delete todos they created.
    Assigned users cannot delete todos (only the creator can).
    """
    # Check permissions
    existing_todo = await use_cases.get_todo(todo_id)
    if not existing_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID '{todo_id}' not found",
        )
    
    # Только создатель может удалить todo (включая admin/it)
    if existing_todo.created_by != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete this todo. Only the creator can delete a todo.",
        )
    
    deleted = await use_cases.delete_todo(todo_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID '{todo_id}' not found",
        )
    
    # Broadcast todo_deleted event only to users who should see this todo
    try:
        event = {
            "type": "todo_deleted",
            "todo_id": todo_id,
        }
        # Get list of users who should receive this update
        users_to_notify = [existing_todo.created_by]
        if existing_todo.assigned_to:
            users_to_notify.extend(existing_todo.assigned_to)
        # Remove duplicates
        users_to_notify = list(set(users_to_notify))
        # Broadcast only to relevant users
        await manager.broadcast_to_users(event, users_to_notify)
    except Exception as ws_error:
        # Silently ignore WebSocket errors
        pass


@router.post("/{todo_id}/archive", response_model=TodoResponseDTO)
async def archive_todo(
    todo_id: str,
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Archive todo (set status to archived)
    
    User can archive todos they created or are assigned to.
    Archived todos are excluded from regular todo lists but can be viewed via /archived endpoint.
    """
    # Check permissions
    existing_todo = await use_cases.get_todo(todo_id)
    if not existing_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID '{todo_id}' not found",
        )
    
    # Все пользователи могут архивировать только свои todos
    if existing_todo.created_by != current_user["id"] and current_user["id"] not in existing_todo.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to archive this todo. You can only archive todos you created or are assigned to.",
        )
    
    # Check if already archived
    if existing_todo.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Todo is already archived",
        )
    
    try:
        todo = await use_cases.archive_todo(todo_id)
        
        # Convert todo to dict for WebSocket
        if hasattr(todo, 'model_dump'):
            todo_dict = todo.model_dump(mode='json')
        elif hasattr(todo, 'dict'):
            todo_dict = todo.dict()
        else:
            todo_dict = todo
        
        # Broadcast todo_archived event
        try:
            event = {
                "type": "todo_archived",
                "todo": todo_dict,
            }
            # Get list of users who should receive this update
            users_to_notify = [todo_dict.get("created_by")]
            if todo_dict.get("assigned_to"):
                users_to_notify.extend(todo_dict["assigned_to"])
            # Remove duplicates
            users_to_notify = list(set(users_to_notify))
            # Broadcast only to relevant users
            await manager.broadcast_to_users(event, users_to_notify)
        except Exception as ws_error:
            # Silently ignore WebSocket errors
            pass
        
        return todo
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{todo_id}/restore", response_model=TodoResponseDTO)
async def restore_todo(
    todo_id: str,
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Restore todo from archive (set status to todo)
    
    User can restore todos they created or are assigned to.
    Restored todos will appear in regular todo lists again.
    """
    # Check permissions
    existing_todo = await use_cases.get_todo(todo_id)
    if not existing_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID '{todo_id}' not found",
        )
    
    # Все пользователи могут восстанавливать только свои todos
    if existing_todo.created_by != current_user["id"] and current_user["id"] not in existing_todo.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to restore this todo. You can only restore todos you created or are assigned to.",
        )
    
    # Check if not archived
    if existing_todo.status != "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Todo is not archived",
        )
    
    try:
        todo = await use_cases.restore_todo(todo_id)
        
        # Convert todo to dict for WebSocket
        if hasattr(todo, 'model_dump'):
            todo_dict = todo.model_dump(mode='json')
        elif hasattr(todo, 'dict'):
            todo_dict = todo.dict()
        else:
            todo_dict = todo
        
        # Broadcast todo_restored event
        try:
            event = {
                "type": "todo_restored",
                "todo": todo_dict,
            }
            # Get list of users who should receive this update
            users_to_notify = [todo_dict.get("created_by")]
            if todo_dict.get("assigned_to"):
                users_to_notify.extend(todo_dict["assigned_to"])
            # Remove duplicates
            users_to_notify = list(set(users_to_notify))
            # Broadcast only to relevant users
            await manager.broadcast_to_users(event, users_to_notify)
        except Exception as ws_error:
            # Silently ignore WebSocket errors
            pass
        
        return todo
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{todo_id}/comments", response_model=TodoResponseDTO)
async def add_comment(
    todo_id: str,
    comment_data: TodoCommentCreateDTO,
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Add comment to todo
    
    User can comment on todos they created or are assigned to.
    """
    # Check permissions
    existing_todo = await use_cases.get_todo(todo_id)
    if not existing_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID '{todo_id}' not found",
        )
    
    # Все пользователи могут комментировать только свои todos
    if existing_todo.created_by != current_user["id"] and current_user["id"] not in existing_todo.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to comment on this todo. You can only comment on todos you created or are assigned to.",
        )
    
    try:
        todo = await use_cases.add_comment(todo_id, comment_data, current_user["id"])
        
        # Convert todo to dict for WebSocket
        if hasattr(todo, 'model_dump'):
            todo_dict = todo.model_dump(mode='json')
        elif hasattr(todo, 'dict'):
            todo_dict = todo.dict()
        else:
            todo_dict = todo
        
        # Broadcast todo_comment_added event only to users who should see this todo
        try:
            event = {
                "type": "todo_comment_added",
                "todo": todo_dict,
                "todo_id": todo_id,
            }
            # Get list of users who should receive this update
            users_to_notify = [todo_dict.get("created_by")]
            if todo_dict.get("assigned_to"):
                users_to_notify.extend(todo_dict["assigned_to"])
            # Remove duplicates
            users_to_notify = list(set(users_to_notify))
            # Broadcast only to relevant users
            await manager.broadcast_to_users(event, users_to_notify)
        except Exception as ws_error:
            # Silently ignore WebSocket errors
            pass
        
        return todo
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{todo_id}/todo-list-items", response_model=TodoResponseDTO)
async def add_todo_list_item(
    todo_id: str,
    item_data: TodoListItemCreateDTO,
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Add item to todo list (checklist)
    
    User can add checklist items to todos they created or are assigned to.
    """
    # Check permissions
    existing_todo = await use_cases.get_todo(todo_id)
    if not existing_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID '{todo_id}' not found",
        )
    
    # Все пользователи могут добавлять элементы чеклиста только в свои todos
    if existing_todo.created_by != current_user["id"] and current_user["id"] not in existing_todo.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify this todo. You can only modify todos you created or are assigned to.",
        )
    
    try:
        todo = await use_cases.add_todo_list_item(todo_id, item_data)
        
        # Convert todo to dict for WebSocket
        if hasattr(todo, 'model_dump'):
            todo_dict = todo.model_dump(mode='json')
        elif hasattr(todo, 'dict'):
            todo_dict = todo.dict()
        else:
            todo_dict = todo
        
        # Broadcast todo_list_item_added event only to users who should see this todo
        try:
            event = {
                "type": "todo_list_item_added",
                "todo": todo_dict,
                "todo_id": todo_id,
            }
            # Get list of users who should receive this update
            users_to_notify = [todo_dict.get("created_by")]
            if todo_dict.get("assigned_to"):
                users_to_notify.extend(todo_dict["assigned_to"])
            # Remove duplicates
            users_to_notify = list(set(users_to_notify))
            # Broadcast only to relevant users
            await manager.broadcast_to_users(event, users_to_notify)
        except Exception as ws_error:
            # Silently ignore WebSocket errors
            pass
        
        return todo
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{todo_id}/todo-list-items/{item_id}", response_model=TodoResponseDTO)
async def update_todo_list_item(
    todo_id: str,
    item_id: str,
    item_data: TodoListItemUpdateDTO,  # Accept JSON body with checked field
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Update todo list item (checklist item)
    
    User can update checklist items in todos they created or are assigned to.
    """
    # Check permissions
    existing_todo = await use_cases.get_todo(todo_id)
    if not existing_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID '{todo_id}' not found",
        )
    
    # Все пользователи могут обновлять элементы чеклиста только в своих todos
    if existing_todo.created_by != current_user["id"] and current_user["id"] not in existing_todo.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify this todo. You can only modify todos you created or are assigned to.",
        )
    
    try:
        # Use checked from DTO
        checked = item_data.checked
        todo = await use_cases.update_todo_list_item(todo_id, item_id, checked)
        
        # Convert todo to dict for WebSocket
        if hasattr(todo, 'model_dump'):
            todo_dict = todo.model_dump(mode='json')
        elif hasattr(todo, 'dict'):
            todo_dict = todo.dict()
        else:
            todo_dict = todo
        
        # Broadcast todo_list_item_updated event only to users who should see this todo
        try:
            event = {
                "type": "todo_list_item_updated",
                "todo": todo_dict,
                "todo_id": todo_id,
                "item_id": item_id,
            }
            # Get list of users who should receive this update
            users_to_notify = [todo_dict.get("created_by")]
            if todo_dict.get("assigned_to"):
                users_to_notify.extend(todo_dict["assigned_to"])
            # Remove duplicates
            users_to_notify = list(set(users_to_notify))
            # Broadcast only to relevant users
            await manager.broadcast_to_users(event, users_to_notify)
        except Exception as ws_error:
            # Silently ignore WebSocket errors
            pass
        
        # Send Telegram notification if checkbox was updated by someone other than creator
        try:
            creator_id = existing_todo.created_by
            current_user_id = current_user["id"]
            
            # Не отправляем уведомление, если создатель сам изменил чекбокс
            if creator_id != current_user_id:
                # Найти измененный пункт в списке
                updated_item = None
                for item in existing_todo.todo_lists:
                    if item.id == item_id:
                        updated_item = item
                        break
                
                if updated_item:
                    # Get current user info (who made the change)
                    updater_info = telegram_bot.get_user_info(current_user_id)
                    updater_name = updater_info["username"] if updater_info else current_user.get("username", "Неизвестный")
                    
                    # Отправить уведомление создателю
                    await telegram_bot.notify_checkbox_updated(
                        creator_id,
                        todo_dict.get("title", "Задача"),
                        updated_item.text,
                        checked,
                        updater_name
                    )
        except Exception as tg_error:
            # Silently ignore Telegram errors
            pass
        
        return todo
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{todo_id}/todo-list-items/{item_id}", response_model=TodoResponseDTO)
async def delete_todo_list_item(
    todo_id: str,
    item_id: str,
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    current_user: dict = Depends(get_current_active_user),
):
    """Delete todo list item (checklist item)
    
    User can delete checklist items from todos they created or are assigned to.
    """
    # Check permissions
    existing_todo = await use_cases.get_todo(todo_id)
    if not existing_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID '{todo_id}' not found",
        )
    
    # Все пользователи могут удалять элементы чеклиста только из своих todos
    if existing_todo.created_by != current_user["id"] and current_user["id"] not in existing_todo.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify this todo. You can only modify todos you created or are assigned to.",
        )
    
    try:
        todo = await use_cases.delete_todo_list_item(todo_id, item_id)
        
        # Convert todo to dict for WebSocket
        if hasattr(todo, 'model_dump'):
            todo_dict = todo.model_dump(mode='json')
        elif hasattr(todo, 'dict'):
            todo_dict = todo.dict()
        else:
            todo_dict = todo
        
        # Broadcast todo_list_item_deleted event only to users who should see this todo
        try:
            event = {
                "type": "todo_list_item_deleted",
                "todo": todo_dict,
                "todo_id": todo_id,
                "item_id": item_id,
            }
            # Get list of users who should receive this update
            users_to_notify = [todo_dict.get("created_by")]
            if todo_dict.get("assigned_to"):
                users_to_notify.extend(todo_dict["assigned_to"])
            # Remove duplicates
            users_to_notify = list(set(users_to_notify))
            # Broadcast only to relevant users
            await manager.broadcast_to_users(event, users_to_notify)
        except Exception as ws_error:
            # Silently ignore WebSocket errors
            pass
        
        return todo
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

