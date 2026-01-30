"""Ticket repository implementation with database"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from app.domain.entities.ticket import Ticket, Comment, TicketPriority, TicketStatus, TicketCategory
from app.domain.repositories.ticket_repository import TicketRepository
from app.infrastructure.database.models import TicketModel, CommentModel


class TicketRepositoryDB(TicketRepository):
    """Ticket repository implementation with PostgreSQL database"""

    def __init__(self, db: Session):
        self.db = db
        self._has_estimated_time = None  # Cache for column existence check
    
    def _check_estimated_time_column(self):
        """Check if estimated_time column exists and cache result"""
        if self._has_estimated_time is None:
            try:
                inspector = inspect(self.db.bind)
                columns = [col['name'] for col in inspector.get_columns('tickets')]
                self._has_estimated_time = 'estimated_time' in columns
                
                # If column doesn't exist, try to add it automatically
                if not self._has_estimated_time:
                    try:
                        self.db.execute(text("ALTER TABLE tickets ADD COLUMN estimated_time VARCHAR(100)"))
                        self.db.commit()
                        self._has_estimated_time = True
                        print("✅ Auto-migrated: Added estimated_time column to tickets table")
                    except Exception as migrate_error:
                        self.db.rollback()
                        print(f"⚠️ Could not auto-migrate estimated_time column: {migrate_error}")
                        print("💡 Please run: ALTER TABLE tickets ADD COLUMN estimated_time VARCHAR(100);")
            except Exception as e:
                print(f"⚠️ Error checking estimated_time column: {e}")
                self._has_estimated_time = False
        
        return self._has_estimated_time

    def _comment_model_to_entity(self, model: CommentModel) -> Comment:
        """Convert CommentModel to Comment entity"""
        return Comment(
            id=str(model.id),  # Ensure ID is string
            text=model.text,
            author_id=str(model.author_id),  # Ensure ID is string
            author_name=model.author_name,
            created_at=model.created_at,
        )

    def _ticket_model_to_entity(self, model: TicketModel) -> Ticket:
        """Convert TicketModel to Ticket entity"""
        comments = [self._comment_model_to_entity(c) for c in model.comments]
        # Handle estimated_time field - it might not exist in old database
        # Use __dict__ to avoid triggering SQLAlchemy lazy loading
        estimated_time = None
        if self._check_estimated_time_column():
            try:
                # Safe access - check if attribute exists in instance dict first
                if 'estimated_time' in model.__dict__:
                    estimated_time = model.__dict__['estimated_time']
                else:
                    # Try normal access but catch any errors
                    estimated_time = model.estimated_time
            except (AttributeError, KeyError):
                estimated_time = None
        return Ticket(
            id=str(model.id),  # Ensure ID is string
            title=model.title,
            description=model.description,
            priority=TicketPriority(model.priority.value) if hasattr(model.priority, 'value') else TicketPriority(model.priority),
            status=TicketStatus(model.status.value) if hasattr(model.status, 'value') else TicketStatus(model.status),
            category=TicketCategory(model.category.value) if hasattr(model.category, 'value') else TicketCategory(model.category),
            created_by=str(model.created_by),  # Ensure ID is string
            created_by_name=model.created_by_name,
            created_by_email=model.created_by_email,
            assigned_to=str(model.assigned_to) if model.assigned_to else None,  # Ensure ID is string or None
            assigned_to_name=model.assigned_to_name,
            estimated_time=estimated_time,
            created_at=model.created_at,
            updated_at=model.updated_at,
            comments=comments,
        )

    async def create(self, ticket: Ticket) -> Ticket:
        """Create a new ticket"""
        try:
            # Ensure column exists before creating
            self._check_estimated_time_column()
            
            print(f"📝 Creating ticket in database: {ticket.title}")
            
            ticket_model = TicketModel(
                id=ticket.id if ticket.id else None,
                title=ticket.title,
                description=ticket.description,
                priority=ticket.priority,
                status=ticket.status,
                category=ticket.category,
                created_by=ticket.created_by,
                created_by_name=ticket.created_by_name,
                created_by_email=ticket.created_by_email,
                assigned_to=ticket.assigned_to,
                assigned_to_name=ticket.assigned_to_name,
                estimated_time=ticket.estimated_time if self._has_estimated_time else None,
                created_at=ticket.created_at,
                updated_at=ticket.updated_at,
            )

            print(f"📝 Adding ticket model to session...")
            self.db.add(ticket_model)
            
            print(f"📝 Flushing changes to database...")
            # Flush changes to database - this sends SQL but doesn't commit
            self.db.flush()
            
            # Get ticket ID after flush (it should be generated by now)
            ticket_id = ticket_model.id
            print(f"📝 Ticket ID after flush: {ticket_id}")
            
            # IMPORTANT: Commit the transaction explicitly
            # The session from FastAPI dependency will be closed after request,
            # so we MUST commit here to persist the data
            print(f"📝 Committing transaction...")
            try:
                self.db.commit()
                print(f"✅ Commit successful! Ticket {ticket_id} should be saved.")
            except Exception as commit_error:
                print(f"❌ Commit failed: {commit_error}")
                import traceback
                traceback.print_exc()
                self.db.rollback()
                raise
            
            # Refresh to get any database-generated values
            print(f"📝 Refreshing ticket model...")
            try:
                self.db.refresh(ticket_model)
                print(f"✅ Refresh successful!")
            except Exception as refresh_error:
                print(f"⚠️ Refresh failed (may be OK if no DB-generated fields): {refresh_error}")
            
            # Verify ticket was saved by querying the database
            print(f"📝 Verifying ticket was saved to database...")
            # Use expire_all to force fresh query from database
            self.db.expire_all()
            saved_ticket = self.db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
            
            if saved_ticket:
                print(f"✅ VERIFIED: Ticket {saved_ticket.id} exists in database!")
                print(f"   Title: {saved_ticket.title}")
                print(f"   Status: {saved_ticket.status}")
                print(f"   Priority: {saved_ticket.priority}")
                print(f"   Created by: {saved_ticket.created_by_name}")
            else:
                print(f"❌ CRITICAL ERROR: Ticket {ticket_id} NOT FOUND in database after commit!")
                # Check total tickets
                all_tickets = self.db.query(TicketModel).all()
                print(f"   Total tickets in database: {len(all_tickets)}")
                if len(all_tickets) > 0:
                    print(f"   Sample ticket IDs: {[t.id for t in all_tickets[:3]]}")
                # This is a critical error - raise exception
                raise Exception(f"Ticket {ticket_id} was not saved to database despite successful commit!")
            
            return self._ticket_model_to_entity(ticket_model)
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error creating ticket: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def get_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Get ticket by ID"""
        try:
            from sqlalchemy.orm import joinedload, defer
            
            # Check and auto-migrate if needed
            has_estimated_time = self._check_estimated_time_column()
            
            query = self.db.query(TicketModel).options(joinedload(TicketModel.comments)).filter(TicketModel.id == ticket_id)
            
            # If column doesn't exist, exclude it from query using defer
            if not has_estimated_time:
                query = query.options(defer(TicketModel.estimated_time))
            
            ticket_model = query.first()
            if not ticket_model:
                print(f"⚠️ Ticket {ticket_id} not found in database")
                return None
            print(f"✅ Loaded ticket {ticket_id} from database")
            return self._ticket_model_to_entity(ticket_model)
        except Exception as e:
            print(f"❌ Error loading ticket {ticket_id}: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def get_all(self) -> List[Ticket]:
        """Get all tickets"""
        try:
            from sqlalchemy.orm import joinedload, defer
            
            # Check and auto-migrate if needed
            has_estimated_time = self._check_estimated_time_column()
            
            query = self.db.query(TicketModel).options(joinedload(TicketModel.comments))
            
            # If column doesn't exist, exclude it from query using defer
            if not has_estimated_time:
                query = query.options(defer(TicketModel.estimated_time))
            
            ticket_models = query.all()
            print(f"📥 Loaded {len(ticket_models)} tickets from database")
            tickets = [self._ticket_model_to_entity(model) for model in ticket_models]
            print(f"✅ Converted {len(tickets)} tickets to entities")
            return tickets
        except Exception as e:
            print(f"❌ Error loading tickets: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def get_by_user_id(self, user_id: str) -> List[Ticket]:
        """Get tickets by user ID"""
        try:
            from sqlalchemy.orm import joinedload, defer
            
            # Check and auto-migrate if needed
            has_estimated_time = self._check_estimated_time_column()
            
            query = self.db.query(TicketModel).filter(TicketModel.created_by == user_id).options(joinedload(TicketModel.comments))
            
            # If column doesn't exist, exclude it from query using defer
            if not has_estimated_time:
                query = query.options(defer(TicketModel.estimated_time))
            
            ticket_models = query.all()
            print(f"📥 Loaded {len(ticket_models)} tickets for user {user_id} from database")
            tickets = [self._ticket_model_to_entity(model) for model in ticket_models]
            return tickets
        except Exception as e:
            print(f"❌ Error loading tickets for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def update(self, ticket: Ticket) -> Ticket:
        """Update ticket"""
        try:
            ticket_model = self.db.query(TicketModel).filter(TicketModel.id == ticket.id).first()
            if not ticket_model:
                raise ValueError(f"Ticket with ID '{ticket.id}' not found")

            ticket_model.title = ticket.title
            ticket_model.description = ticket.description
            ticket_model.priority = ticket.priority
            ticket_model.status = ticket.status
            ticket_model.category = ticket.category
            ticket_model.assigned_to = ticket.assigned_to
            ticket_model.assigned_to_name = ticket.assigned_to_name
            # Handle estimated_time field - ensure column exists before updating
            if self._check_estimated_time_column():
                ticket_model.estimated_time = ticket.estimated_time
            ticket_model.updated_at = ticket.updated_at

            # Flush changes to database before commit
            self.db.flush()
            self.db.commit()
            self.db.refresh(ticket_model)
            
            print(f"✅ Updated ticket {ticket_model.id} in database: {ticket_model.title}")
            return self._ticket_model_to_entity(ticket_model)
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error updating ticket {ticket.id}: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def delete(self, ticket_id: str) -> bool:
        """Delete ticket"""
        try:
            ticket_model = self.db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
            if not ticket_model:
                print(f"⚠️ Ticket {ticket_id} not found for deletion")
                return False

            self.db.delete(ticket_model)
            # Flush changes to database before commit
            self.db.flush()
            self.db.commit()
            print(f"✅ Deleted ticket {ticket_id} from database")
            return True
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error deleting ticket {ticket_id}: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def add_comment(self, ticket_id: str, comment: Comment) -> Ticket:
        """Add comment to ticket"""
        try:
            ticket_model = self.db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
            if not ticket_model:
                raise ValueError(f"Ticket with ID '{ticket_id}' not found")

            comment_model = CommentModel(
                id=comment.id if comment.id else None,
                text=comment.text,
                ticket_id=ticket_id,
                author_id=comment.author_id,
                author_name=comment.author_name,
                created_at=comment.created_at,
            )

            self.db.add(comment_model)
            # Flush changes to database before commit
            self.db.flush()
            self.db.commit()
            
            # Refresh ticket model to get updated comments
            self.db.refresh(ticket_model)
            # Explicitly reload comments relationship
            from sqlalchemy.orm import joinedload, defer
            
            # Check and auto-migrate if needed
            has_estimated_time = self._check_estimated_time_column()
            
            query = self.db.query(TicketModel).options(joinedload(TicketModel.comments)).filter(TicketModel.id == ticket_id)
            
            # If column doesn't exist, exclude it from query using defer
            if not has_estimated_time:
                query = query.options(defer(TicketModel.estimated_time))
            
            ticket_model = query.first()

            print(f"✅ Added comment to ticket {ticket_id}, total comments: {len(ticket_model.comments)}")
            return self._ticket_model_to_entity(ticket_model)
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error adding comment to ticket {ticket_id}: {e}")
            import traceback
            traceback.print_exc()
            raise

