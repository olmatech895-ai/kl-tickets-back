"""Database base configuration"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.infrastructure.config.settings import settings

try:
    database_url = settings.get_database_url()
except Exception as e:
    raise RuntimeError(f"Не удалось сформировать DATABASE_URL. Проверьте .env: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD (или DATABASE_URL). Ошибка: {e}") from e

try:
    if settings.DATABASE_TYPE == "postgresql":
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        with engine.connect():
            pass
    elif settings.DATABASE_TYPE == "sqlite":
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
    else:
        raise ValueError(f"Unsupported database type: {settings.DATABASE_TYPE}")
except Exception as e:
    raise RuntimeError(
        f"Подключение к БД не удалось. Проверьте: PostgreSQL запущен, в .env указаны DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD (или полный DATABASE_URL). Ошибка: {e}"
    ) from e

# Create session factory
# autocommit=False means we need to explicitly commit transactions
# autoflush=False means we need to explicitly flush before commit
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Get database session

    This is a FastAPI dependency that provides a database session.
    The session is automatically closed after the request completes.

    IMPORTANT: Repositories must commit their own transactions.
    This function only ensures the session is properly closed.
    """
    db = SessionLocal()
    try:
        # Test connection before yielding
        db.execute(text("SELECT 1"))
        yield db
        # Don't commit here - repositories handle their own commits
        # This ensures that commits happen before the response is sent
    except Exception:
        db.rollback()
        raise
    finally:
        # Close the session - this happens AFTER the response is sent
        db.close()


def init_db():
    """Initialize database - create all tables and run schema migrations."""
    from app.infrastructure.database import models  # Import models to register them

    Base.metadata.create_all(bind=engine)

    # Allow password_hash to be NULL (auth by email only)
    if settings.DATABASE_TYPE == "postgresql":
        try:
            with engine.connect() as conn:
                trans = conn.begin()
                try:
                    conn.execute(text("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL"))
                    trans.commit()
                except Exception as inner:
                    trans.rollback()
                    raise inner
        except Exception as e:
            err = str(e).lower()
            if "does not exist" in err or "not have a not null" in err or "constraint" in err:
                pass
