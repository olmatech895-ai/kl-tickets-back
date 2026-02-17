"""Database base configuration"""

import sys

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.infrastructure.config.settings import settings

# Get database URL
try:
    database_url = settings.get_database_url()
except Exception as e:
    print(f"❌ Error getting database URL: {e}")
    sys.exit(1)

# Create database engine with appropriate connect_args
try:
    if settings.DATABASE_TYPE == "postgresql":
        # PostgreSQL doesn't need check_same_thread
        print(
            f"🔌 Connecting to PostgreSQL database: {settings.DB_NAME}@{settings.DB_HOST}:{settings.DB_PORT}"
        )
        engine = create_engine(
            database_url,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=10,
            max_overflow=20,
        )
        # Test connection
        with engine.connect() as conn:
            print("✅ PostgreSQL connection successful!")
    elif settings.DATABASE_TYPE == "sqlite":
        # SQLite needs check_same_thread=False
        print(f"🔌 Using SQLite database: {database_url}")
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
    else:
        raise ValueError(f"Unsupported database type: {settings.DATABASE_TYPE}")
except Exception as e:
    print(f"❌ Database connection error: {e}")
    print(f"\n💡 Troubleshooting:")
    print(f"   1. Check if PostgreSQL is running")
    print(f"   2. Verify database credentials in .env file:")
    print(f"      DB_HOST={settings.DB_HOST}")
    print(f"      DB_PORT={settings.DB_PORT}")
    print(f"      DB_NAME={settings.DB_NAME}")
    print(f"      DB_USER={settings.DB_USER}")
    print(f"   3. Make sure database '{settings.DB_NAME}' exists")
    print(f"   4. Check PostgreSQL password for user '{settings.DB_USER}'")
    sys.exit(1)

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
    except Exception as e:
        print(f"❌ Database session error: {e}")
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
                    print("✅ users.password_hash: NOT NULL constraint removed")
                except Exception as inner:
                    trans.rollback()
                    raise inner
        except Exception as e:
            err = str(e).lower()
            if "does not exist" in err or "not have a not null" in err or "constraint" in err:
                pass  # Already nullable
            else:
                print(f"⚠️ Migration password_hash nullable: {e}")
