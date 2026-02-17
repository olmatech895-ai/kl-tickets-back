"""Todo column repository implementation with database"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from datetime import datetime
from app.infrastructure.database.models import TodoColumnModel


class TodoColumnRepositoryDB:
    """Todo column repository implementation with PostgreSQL database"""

    def __init__(self, db: Session):
        self.db = db
        self._table_exists = None

    def _check_table_exists(self) -> bool:
        """Check if todo_columns table exists"""
        if self._table_exists is None:
            try:
                inspector = inspect(self.db.bind)
                tables = inspector.get_table_names()
                self._table_exists = "todo_columns" in tables
                if not self._table_exists:
                    print("⚠️ Table 'todo_columns' does not exist in database")
                    print(
                        "💡 Run: python create_todo_columns_table.py or check database initialization"
                    )
            except Exception as e:
                print(f"⚠️ Error checking table existence: {e}")
                self._table_exists = False
        return self._table_exists

    def _has_user_id_column(self) -> bool:
        """Check if user_id column exists in todo_columns table"""
        try:
            if not self._check_table_exists():
                return False
            inspector = inspect(self.db.bind)
            columns = inspector.get_columns("todo_columns")
            return any(col["name"] == "user_id" for col in columns)
        except Exception:
            return False

    async def get_all(self, user_id: Optional[str] = None) -> List[TodoColumnModel]:
        """Get all columns for a user, ordered by order_index

        If user_id column doesn't exist, returns empty list (user needs to create columns first).
        This ensures that each user starts with their own columns.
        """
        if not self._check_table_exists():
            return []
        try:
            has_user_id = self._has_user_id_column()

            if not has_user_id:
                # If user_id column doesn't exist, return empty list
                # This forces users to create their own columns via POST /columns
                # After migration, this will work correctly with user_id filtering
                return []
            else:
                # Use direct SQL when column exists - filter by user_id (to avoid type mismatch)
                if user_id:
                    sql = text(
                        """
                        SELECT id, column_id, title, status, color, background_image, order_index, user_id, created_at, updated_at
                        FROM todo_columns
                        WHERE user_id = :user_id
                        ORDER BY order_index
                    """
                    )
                    result = self.db.execute(sql, {"user_id": user_id})
                    rows = result.fetchall()

                    # Convert rows to model instances
                    columns = []
                    for row in rows:
                        column = TodoColumnModel(
                            id=row[0],
                            column_id=row[1],
                            title=row[2],
                            status=row[3],
                            color=row[4],
                            background_image=row[5],
                            order_index=row[6],
                            user_id=row[7],
                            created_at=row[8],
                            updated_at=row[9],
                        )
                        columns.append(column)
                    return columns
                else:
                    # If no user_id provided but column exists, return empty (shouldn't happen in normal flow)
                    return []
        except Exception as e:
            print(f"❌ Error getting columns: {e}")
            import traceback

            traceback.print_exc()
            raise

    async def get_by_column_id(
        self, column_id: str, user_id: Optional[str] = None
    ) -> Optional[TodoColumnModel]:
        """Get column by column_id for a specific user"""
        has_user_id = self._has_user_id_column()

        if not has_user_id:
            # Use direct SQL to avoid loading user_id column
            sql = text(
                """
                SELECT id, column_id, title, status, color, background_image, order_index, created_at, updated_at
                FROM todo_columns
                WHERE column_id = :column_id
                LIMIT 1
            """
            )
            result = self.db.execute(sql, {"column_id": column_id})
            row = result.fetchone()

            if not row:
                return None

            return TodoColumnModel(
                id=row[0],
                column_id=row[1],
                title=row[2],
                status=row[3],
                color=row[4],
                background_image=row[5],
                order_index=row[6],
                created_at=row[7],
                updated_at=row[8],
            )
        else:
            # Use direct SQL when column exists (to avoid type mismatch)
            if user_id:
                sql = text(
                    """
                    SELECT id, column_id, title, status, color, background_image, order_index, user_id, created_at, updated_at
                    FROM todo_columns
                    WHERE column_id = :column_id AND user_id = :user_id
                    LIMIT 1
                """
                )
                result = self.db.execute(
                    sql, {"column_id": column_id, "user_id": user_id}
                )
                row = result.fetchone()

                if not row:
                    return None

                return TodoColumnModel(
                    id=row[0],
                    column_id=row[1],
                    title=row[2],
                    status=row[3],
                    color=row[4],
                    background_image=row[5],
                    order_index=row[6],
                    user_id=row[7],
                    created_at=row[8],
                    updated_at=row[9],
                )
            else:
                sql = text(
                    """
                    SELECT id, column_id, title, status, color, background_image, order_index, user_id, created_at, updated_at
                    FROM todo_columns
                    WHERE column_id = :column_id
                    LIMIT 1
                """
                )
                result = self.db.execute(sql, {"column_id": column_id})
                row = result.fetchone()

                if not row:
                    return None

                return TodoColumnModel(
                    id=row[0],
                    column_id=row[1],
                    title=row[2],
                    status=row[3],
                    color=row[4],
                    background_image=row[5],
                    order_index=row[6],
                    user_id=row[7],
                    created_at=row[8],
                    updated_at=row[9],
                )

    async def create(self, column_data: dict) -> TodoColumnModel:
        """Create a new column"""
        has_user_id = self._has_user_id_column()

        # Remove user_id if column doesn't exist
        if not has_user_id and "user_id" in column_data:
            column_data = {k: v for k, v in column_data.items() if k != "user_id"}

        if not has_user_id:
            # Use direct SQL INSERT to avoid user_id
            from datetime import datetime
            import uuid

            col_id = column_data.get("id") or str(uuid.uuid4())
            sql = text(
                """
                INSERT INTO todo_columns 
                (id, column_id, title, status, color, background_image, order_index, created_at, updated_at)
                VALUES 
                (:id, :column_id, :title, :status, :color, :background_image, :order_index, :created_at, :updated_at)
            """
            )

            self.db.execute(
                sql,
                {
                    "id": col_id,
                    "column_id": column_data.get("column_id", ""),
                    "title": column_data.get("title", ""),
                    "status": column_data.get("status", "todo"),
                    "color": column_data.get("color", "primary"),
                    "background_image": column_data.get("background_image"),
                    "order_index": column_data.get("order_index", "0"),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                },
            )
            self.db.commit()

            # Fetch using direct SQL
            select_sql = text(
                """
                SELECT id, column_id, title, status, color, background_image, order_index, created_at, updated_at
                FROM todo_columns
                WHERE id = :id
            """
            )
            result = self.db.execute(select_sql, {"id": col_id})
            row = result.fetchone()

            if row:
                return TodoColumnModel(
                    id=row[0],
                    column_id=row[1],
                    title=row[2],
                    status=row[3],
                    color=row[4],
                    background_image=row[5],
                    order_index=row[6],
                    created_at=row[7],
                    updated_at=row[8],
                )
            else:
                raise Exception(f"Failed to create column with id: {col_id}")
        else:
            # Use ORM when column exists
            column_model = TodoColumnModel(**column_data)
            self.db.add(column_model)
            self.db.flush()
            self.db.commit()
            self.db.refresh(column_model)
            return column_model

    async def update(
        self, column_id: str, column_data: dict, user_id: Optional[str] = None
    ) -> Optional[TodoColumnModel]:
        """Update a column"""
        has_user_id = self._has_user_id_column()
        column_model = await self.get_by_column_id(column_id, user_id)
        if not column_model:
            return None

        # Don't set user_id if column doesn't exist
        filtered_data = {
            k: v for k, v in column_data.items() if k != "user_id" or has_user_id
        }

        if not has_user_id:
            # Use direct SQL UPDATE to avoid user_id
            update_fields = []
            update_values = {"column_id": column_id}

            for key, value in filtered_data.items():
                if value is not None and key != "id":
                    update_fields.append(f"{key} = :{key}")
                    update_values[key] = value

            if update_fields:
                update_values["updated_at"] = datetime.utcnow()
                update_fields.append("updated_at = :updated_at")

                sql = text(
                    f"""
                    UPDATE todo_columns 
                    SET {', '.join(update_fields)}
                    WHERE column_id = :column_id
                """
                )
                self.db.execute(sql, update_values)
                self.db.commit()

                # Fetch updated row
                return await self.get_by_column_id(column_id, user_id)
            else:
                return column_model
        else:
            # Use direct SQL UPDATE when column exists (to avoid type mismatch)
            update_fields = []
            update_values = {"column_id": column_id, "user_id": user_id}

            for key, value in filtered_data.items():
                if value is not None and key != "id":
                    update_fields.append(f"{key} = :{key}")
                    update_values[key] = value

            if update_fields:
                update_values["updated_at"] = datetime.utcnow()
                update_fields.append("updated_at = :updated_at")

                sql = text(
                    f"""
                    UPDATE todo_columns 
                    SET {', '.join(update_fields)}
                    WHERE column_id = :column_id AND user_id = :user_id
                """
                )
                self.db.execute(sql, update_values)
                self.db.commit()

                # Fetch updated row
                return await self.get_by_column_id(column_id, user_id)
            else:
                return column_model

    async def delete(self, column_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a column"""
        has_user_id = self._has_user_id_column()

        if not has_user_id:
            # Use direct SQL if column doesn't exist
            sql = text("DELETE FROM todo_columns WHERE column_id = :column_id")
            result = self.db.execute(sql, {"column_id": column_id})
            self.db.commit()
            return result.rowcount > 0
        else:
            # Use direct SQL to avoid type mismatch (VARCHAR = VARCHAR)
            if user_id:
                sql = text(
                    "DELETE FROM todo_columns WHERE column_id = :column_id AND user_id = :user_id"
                )
                result = self.db.execute(
                    sql, {"column_id": column_id, "user_id": user_id}
                )
            else:
                sql = text("DELETE FROM todo_columns WHERE column_id = :column_id")
                result = self.db.execute(sql, {"column_id": column_id})
            self.db.commit()
            return result.rowcount > 0

    async def delete_all(self) -> int:
        """Delete all columns (for reset)"""
        has_user_id = self._has_user_id_column()

        if not has_user_id:
            # Use direct SQL DELETE to avoid user_id
            sql = text("DELETE FROM todo_columns")
            result = self.db.execute(sql)
            self.db.commit()
            return result.rowcount
        else:
            # Use ORM when column exists
            count = self.db.query(TodoColumnModel).delete()
            self.db.flush()
            self.db.commit()
            return count

    async def bulk_create(
        self, columns_data: List[dict], user_id: str
    ) -> List[TodoColumnModel]:
        """Create multiple columns at once for a specific user (replaces all user's columns)

        IMPORTANT: This method requires user_id column to exist in database.
        Without user_id column, columns cannot be isolated per user.
        """
        try:
            # Check if table exists
            if not self._check_table_exists():
                raise ValueError(
                    "Table 'todo_columns' does not exist. Please run database migration first."
                )

            # Validate input
            if not columns_data:
                return []

            if not user_id:
                raise ValueError("user_id is required to create columns")

            has_user_id = self._has_user_id_column()

            if not has_user_id:
                raise ValueError(
                    "user_id column does not exist in database. "
                    "Please run migration to add user_id column (see RUN_MIGRATION.md). "
                    "Without this column, columns cannot be isolated per user."
                )

            # Delete all existing columns for this user only (within same transaction)
            # Use direct SQL to ensure proper type casting (VARCHAR = VARCHAR)
            delete_sql = text("DELETE FROM todo_columns WHERE user_id = :user_id")
            self.db.execute(delete_sql, {"user_id": user_id})
            self.db.flush()  # Ensure delete is executed before insert

            # Create new columns using direct SQL to avoid ORM issues with unique constraints
            column_models = []
            import uuid

            for col_data in columns_data:
                try:
                    # Create a copy to avoid modifying original
                    column_data = dict(col_data)

                    # Generate ID if not provided
                    col_id = column_data.get("id") or str(uuid.uuid4())

                    # Use direct SQL INSERT to avoid unique constraint issues
                    insert_sql = text(
                        """
                        INSERT INTO todo_columns 
                        (id, column_id, title, status, color, background_image, order_index, user_id, created_at, updated_at)
                        VALUES 
                        (:id, :column_id, :title, :status, :color, :background_image, :order_index, :user_id, :created_at, :updated_at)
                    """
                    )

                    self.db.execute(
                        insert_sql,
                        {
                            "id": col_id,
                            "column_id": column_data.get("column_id", ""),
                            "title": column_data.get("title", ""),
                            "status": column_data.get("status", "todo"),
                            "color": column_data.get("color", "primary"),
                            "background_image": column_data.get("background_image"),
                            "order_index": column_data.get("order_index", "0"),
                            "user_id": user_id,
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow(),
                        },
                    )

                    # Fetch the created model using direct SQL
                    select_sql = text(
                        """
                        SELECT id, column_id, title, status, color, background_image, order_index, user_id, created_at, updated_at
                        FROM todo_columns
                        WHERE id = :id
                    """
                    )
                    result = self.db.execute(select_sql, {"id": col_id})
                    row = result.fetchone()

                    if row:
                        column_model = TodoColumnModel(
                            id=row[0],
                            column_id=row[1],
                            title=row[2],
                            status=row[3],
                            color=row[4],
                            background_image=row[5],
                            order_index=row[6],
                            user_id=row[7],
                            created_at=row[8],
                            updated_at=row[9],
                        )
                        column_models.append(column_model)
                except Exception as col_error:
                    print(f"❌ Error creating column: {col_error}")
                    print(f"   Column data: {column_data}")
                    import traceback

                    traceback.print_exc()
                    raise

            # Commit transaction
            self.db.commit()

            return column_models

        except Exception as e:
            print(f"❌ Error in bulk_create: {e}")
            import traceback

            traceback.print_exc()
            # Rollback on error
            try:
                self.db.rollback()
            except Exception as rollback_error:
                print(f"❌ Error during rollback: {rollback_error}")
            raise
