"""User repository implementation with database. No passwords; auth by email only."""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.domain.entities.user import User, UserRole
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.database.models import UserModel


class UserRepositoryDB(UserRepository):
    """User repository implementation with PostgreSQL database"""

    def __init__(self, db: Session):
        self.db = db

    def _model_to_entity(self, model: UserModel) -> User:
        """Convert UserModel to User entity"""
        return User(
            id=str(model.id),  # Ensure ID is string
            username=model.username,
            email=model.email,
            role=UserRole(model.role.value) if hasattr(model.role, 'value') else UserRole(model.role),
            blocked=model.blocked,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create(self, user: User) -> User:
        """Create a new user (no password)."""
        existing = await self.get_by_username(user.username)
        if existing:
            raise ValueError(f"User with username '{user.username}' already exists")

        user_model = UserModel(
            id=user.id if user.id else None,
            username=user.username,
            email=user.email,
            password_hash=None,
            role=user.role,
            blocked=user.blocked,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

        self.db.add(user_model)
        self.db.commit()
        self.db.refresh(user_model)

        return self._model_to_entity(user_model)

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        user_model = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user_model:
            return None
        return self._model_to_entity(user_model)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        user_model = self.db.query(UserModel).filter(UserModel.username == username).first()
        if not user_model:
            return None
        return self._model_to_entity(user_model)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        user_model = self.db.query(UserModel).filter(UserModel.email == email.lower()).first()
        if not user_model:
            return None
        return self._model_to_entity(user_model)

    async def get_all(self) -> List[User]:
        """Get all users"""
        user_models = self.db.query(UserModel).all()
        return [self._model_to_entity(model) for model in user_models]

    async def update(self, user: User) -> User:
        """Update user"""
        user_model = self.db.query(UserModel).filter(UserModel.id == user.id).first()
        if not user_model:
            raise ValueError(f"User with ID '{user.id}' not found")

        user_model.username = user.username
        user_model.email = user.email
        user_model.role = user.role
        user_model.blocked = user.blocked
        user_model.updated_at = user.updated_at

        self.db.commit()
        self.db.refresh(user_model)

        return self._model_to_entity(user_model)

    async def delete(self, user_id: str) -> bool:
        """Delete user
        
        Before deleting, we need to handle related data:
        - Tickets created by user: set created_by to NULL or delete (if allowed)
        - Tickets assigned to user: set assigned_to to NULL
        - Comments by user: keep comments but mark author as deleted
        - Todos created by user: handle appropriately
        - Inventory items: set responsible to NULL
        """
        try:
            user_model = self.db.query(UserModel).filter(UserModel.id == user_id).first()
            if not user_model:
                return False

            # Check if user has related data
            from app.infrastructure.database.models import TicketModel, CommentModel, TodoModel, InventoryModel
            
            # Count related records
            tickets_created = self.db.query(TicketModel).filter(TicketModel.created_by == user_id).count()
            tickets_assigned = self.db.query(TicketModel).filter(TicketModel.assigned_to == user_id).count()
            comments_count = self.db.query(CommentModel).filter(CommentModel.author_id == user_id).count()
            todos_count = self.db.query(TodoModel).filter(TodoModel.created_by == user_id).count()
            inventory_count = self.db.query(InventoryModel).filter(InventoryModel.responsible == user_id).count()
            
            print(f"🗑️ Deleting user {user_id} ({user_model.username})")
            print(f"   Related data: {tickets_created} tickets created, {tickets_assigned} tickets assigned, {comments_count} comments, {todos_count} todos, {inventory_count} inventory items")
            
            # Handle related tickets - set assigned_to to NULL for tickets assigned to this user
            if tickets_assigned > 0:
                self.db.query(TicketModel).filter(TicketModel.assigned_to == user_id).update({
                    TicketModel.assigned_to: None,
                    TicketModel.assigned_to_name: None
                })
                print(f"   ✅ Set assigned_to to NULL for {tickets_assigned} tickets")
            
            # Handle inventory - set responsible to NULL
            if inventory_count > 0:
                self.db.query(InventoryModel).filter(InventoryModel.responsible == user_id).update({
                    InventoryModel.responsible: None
                })
                print(f"   ✅ Set responsible to NULL for {inventory_count} inventory items")
            
            # For tickets created by user and comments, we need to handle them carefully
            # Option 1: Delete all tickets created by user (cascade will delete comments)
            # Option 2: Set created_by to a system user or keep tickets but mark user as deleted
            # For now, we'll delete tickets created by user (cascade will handle comments)
            if tickets_created > 0:
                # Delete tickets created by this user (cascade will delete comments)
                self.db.query(TicketModel).filter(TicketModel.created_by == user_id).delete()
                print(f"   ✅ Deleted {tickets_created} tickets created by user")
            
            # Delete todos created by user
            if todos_count > 0:
                # Delete todos created by this user (cascade will handle related data)
                self.db.query(TodoModel).filter(TodoModel.created_by == user_id).delete()
                print(f"   ✅ Deleted {todos_count} todos created by user")
            
            # Comments by user in tickets created by others - we'll keep them but they'll reference deleted user
            # This is OK as we have denormalized author_name field
            
            # Now delete the user
            self.db.delete(user_model)
            self.db.flush()
            self.db.commit()
            
            print(f"   ✅ User {user_id} deleted successfully")
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"   ❌ Error deleting user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"Failed to delete user: {str(e)}")


