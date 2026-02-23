"""FastAPI application entry point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
from app.infrastructure.config.settings import settings
from app.presentation.api.v1.routers import users, auth, tickets, websocket, inventory, todos, telegram, report
from app.infrastructure.init_data import init_default_admin, init_default_users
from app.infrastructure.storage import ensure_upload_dir


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Initialize database tables
    from app.infrastructure.database.base import init_db
    init_db()

    try:
        from app.infrastructure.database.base import engine
        from app.infrastructure.config.settings import settings as _s
        from sqlalchemy import text, inspect
        inspector = inspect(engine)
        if _s.DATABASE_TYPE == "postgresql" and "todos" in inspector.get_table_names():
            cols = [c["name"] for c in inspector.get_columns("todos")]
            if "notify_when_due" not in cols:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE todos ADD COLUMN notify_when_due BOOLEAN NOT NULL DEFAULT false"))
                    conn.commit()
            if "calendar_only" not in cols:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE todos ADD COLUMN calendar_only BOOLEAN NOT NULL DEFAULT false"))
                    conn.commit()
            if "all_day" not in cols:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE todos ADD COLUMN all_day BOOLEAN NOT NULL DEFAULT false"))
                    conn.commit()
    except Exception:
        pass

    try:
        from app.infrastructure.database.base import engine
        from sqlalchemy import text, inspect
        inspector = inspect(engine)
        if 'todo_columns' in inspector.get_table_names():
            columns = inspector.get_columns('todo_columns')
            has_user_id = any(col['name'] == 'user_id' for col in columns)
            
            if not has_user_id:
                with engine.connect() as conn:
                    trans = conn.begin()
                    try:
                        # Add column
                        conn.execute(text("ALTER TABLE todo_columns ADD COLUMN user_id VARCHAR(36)"))
                        
                        # Set default value for existing rows
                        result = conn.execute(text("SELECT id FROM users LIMIT 1"))
                        user_row = result.fetchone()
                        if user_row:
                            default_user_id = user_row[0]
                            conn.execute(text("UPDATE todo_columns SET user_id = :user_id WHERE user_id IS NULL"), 
                                       {"user_id": default_user_id})
                        
                        # Make NOT NULL
                        conn.execute(text("ALTER TABLE todo_columns ALTER COLUMN user_id SET NOT NULL"))
                        
                        # Add foreign key
                        trans.commit()
                        trans = conn.begin()
                        try:
                            conn.execute(text("""
                                ALTER TABLE todo_columns 
                                ADD CONSTRAINT fk_todo_columns_user_id 
                                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                            """))
                            trans.commit()
                        except Exception as fk_error:
                            trans.rollback()
                            # Constraint may already exist - that's OK
                            pass
                        
                        # Create index
                        trans = conn.begin()
                        try:
                            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_todo_columns_user_id ON todo_columns(user_id)"))
                            trans.commit()
                        except Exception as idx_error:
                            trans.rollback()
                            # Index may already exist - that's OK
                            pass
                        
                        # Remove old unique index on column_id (if exists) - now column_id should be unique per user
                        trans = conn.begin()
                        try:
                            # Check if old unique index exists
                            result = conn.execute(text("""
                                SELECT indexname FROM pg_indexes 
                                WHERE tablename = 'todo_columns' 
                                AND indexname = 'ix_todo_columns_column_id'
                            """))
                            if result.fetchone():
                                # Drop the old unique index
                                conn.execute(text("DROP INDEX IF EXISTS ix_todo_columns_column_id"))
                                trans.commit()
                            else:
                                trans.commit()
                        except Exception as idx_error:
                            trans.rollback()
                            # Index may not exist - that's OK
                            pass
                        
                        # Create composite unique constraint on (column_id, user_id)
                        trans = conn.begin()
                        try:
                            # Check if constraint already exists
                            result = conn.execute(text("""
                                SELECT constraint_name FROM information_schema.table_constraints 
                                WHERE table_name = 'todo_columns' 
                                AND constraint_name = 'uq_todo_columns_column_id_user_id'
                            """))
                            if not result.fetchone():
                                conn.execute(text("""
                                    ALTER TABLE todo_columns 
                                    ADD CONSTRAINT uq_todo_columns_column_id_user_id 
                                    UNIQUE (column_id, user_id)
                                """))
                                trans.commit()
                            else:
                                trans.commit()
                        except Exception as uq_error:
                            trans.rollback()
                            # Constraint may already exist - that's OK
                            pass
                        
                    except Exception:
                        trans.rollback()
    except Exception:
        pass
    ensure_upload_dir()
    # Initialize default admin and default users
    await init_default_admin()
    await init_default_users()

    try:
        yield
    except (KeyboardInterrupt, asyncio.CancelledError):
        # Normal shutdown - don't log as error
        pass
    finally:
        pass


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Add explicit CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using ["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(tickets.router, prefix=settings.API_V1_PREFIX)
app.include_router(inventory.router, prefix=settings.API_V1_PREFIX)
app.include_router(todos.router, prefix=settings.API_V1_PREFIX)
app.include_router(websocket.router, prefix=settings.API_V1_PREFIX)
app.include_router(telegram.router, prefix=settings.API_V1_PREFIX)
# Отчёт посещений с устройства Hikvision (ТЗ face-control)
app.include_router(report.router, prefix="/report")
# Путь для фронта (прокси /api-attendance -> backend)
app.include_router(report.router, prefix="/api-attendance/report")

# Mount static files for uploads (ensure directory exists before mount)
ensure_upload_dir()
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

