"""Initialize default data. No passwords; auth by email only."""

DEFAULT_USER_EMAILS = [
    "alina.abdullaeva@kostalegal.com",
    "amametkulova@kostalegal.com",
    "aablyalimova@kostalegal.com",
    "ayuldashev@kostalegal.com",
    "asanina@kostalegal.com",
    "aakhmadjonov@kostalegal.com",
    "ddavidbaeva@kostalegal.com",
    "dorifjonov@kostalegal.com",
    "dnishonov@kostalegal.com",
    "ebaranovskaya@kostalegal.com",
    "gulnoza.usmonova@kostalegal.com",
    "gtemirova@kostalegal.com",
    "info@kostalegal.com",
    "itokhirova@kostalegal.com",
    "idjakabaev@kostalegal.com",
    "ibaratov@kostalegal.com",
    "iismatov@kostalegal.com",
    "jbahodirov@kostalegal.com",
    "kamila.djabbarova@kostalegal.com",
    "kyusupova@kostalegal.com",
    "karimaxon.xabibullaxoja@kostalegal.com",
    "klenneshmidt@kostalegal.com",
    "kumushkhon.abdumutalimova@kostalegal.com",
    "labdullaeva@kostalegal.com",
    "mdogonkin@kostalegal.com",
    "nhassanov@kostalegal.com",
    "oidrisova@kostalegal.com",
    "Project.Everest@kostalegal.com",
    "sevara.abdusaidova@kostalegal.com",
    "shahzoda.khusenova@kostalegal.com",
    "shmirzayev@kostalegal.com",
    "shukhrat.yunusov@kostalegal.com",
    "tsoboleva@kostalegal.com",
    "vgrigoryan@kostalegal.com",
    "zumerov@kostalegal.com",
]

from app.domain.entities.user import User, UserRole
from app.infrastructure.config.settings import settings


async def init_default_admin():
    """Create default admin user if missing (no password)."""
    from app.infrastructure.database.base import SessionLocal
    from app.infrastructure.repositories.user_repository_db import UserRepositoryDB

    db = SessionLocal()
    try:
        repository = UserRepositoryDB(db)
        existing = await repository.get_by_email(settings.DEFAULT_ADMIN_EMAIL)
        if existing:
            print(f"✅ Default admin '{settings.DEFAULT_ADMIN_EMAIL}' already exists")
            return

        if not settings.DEFAULT_ADMIN_EMAIL.lower().endswith("@kostalegal.com"):
            print(f"❌ Invalid admin email domain: {settings.DEFAULT_ADMIN_EMAIL}")
            return

        admin_user = User(
            id="",
            username=settings.DEFAULT_ADMIN_USERNAME,
            email=settings.DEFAULT_ADMIN_EMAIL,
            role=UserRole.ADMIN,
            blocked=False,
        )
        await repository.create(admin_user)
        print(f"✅ Default admin created: {settings.DEFAULT_ADMIN_EMAIL}")
    except Exception as e:
        print(f"❌ Failed to create default admin: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


async def init_default_users():
    """Create default users from DEFAULT_USER_EMAILS if missing."""
    from app.infrastructure.database.base import SessionLocal
    from app.infrastructure.repositories.user_repository_db import UserRepositoryDB

    db = SessionLocal()
    try:
        repository = UserRepositoryDB(db)
        for email in DEFAULT_USER_EMAILS:
            email = email.strip().lower()
            if not email.endswith("@kostalegal.com"):
                continue
            existing = await repository.get_by_email(email)
            if existing:
                continue
            username = email.split("@")[0]
            user = User(
                id="",
                username=username,
                email=email,
                role=UserRole.USER,
                blocked=False,
            )
            await repository.create(user)
            print(f"✅ User created: {email}")
    except Exception as e:
        print(f"❌ Failed to create default users: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

