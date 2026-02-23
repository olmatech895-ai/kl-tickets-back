"""Application settings — все значения задаются в .env (см. .env.example)."""

from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """Настройки приложения. Источник: .env (пример — .env.example)."""

    # Application
    APP_NAME: str = "Tickets System API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    # Database (в .env: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD или DATABASE_URL)
    DATABASE_URL: Optional[str] = None
    DATABASE_TYPE: str = "postgresql"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "tickets"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""

    # Security (в .env для продакшена задать SECRET_KEY; если пусто — подставляется dev-значение)
    SECRET_KEY: str = "dev-change-in-env"

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def secret_key_default(cls, v: Optional[str]) -> str:
        if not v or not str(v).strip():
            return "dev-change-in-env"
        return str(v)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # Default Admin (создаётся при первом запуске; пароль — только из .env)
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_EMAIL: str = "admin@kostalegal.com"
    DEFAULT_ADMIN_PASSWORD: str = ""

    # File Upload (размеры в байтах)
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    TODO_MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_BOT_ENABLED: bool = False
    BACKEND_URL: str = "http://localhost:1234"

    # Hikvision: отчёт посещений GET /report/attendance-from-device
    HIKVISION_DEVICE_IP: Optional[str] = None
    HIKVISION_DEVICE_PORT: int = 80
    HIKVISION_DEVICE_USER: Optional[str] = None
    HIKVISION_DEVICE_PASSWORD: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_database_url(self) -> str:
        """Get database URL from settings or environment"""
        if self.DATABASE_URL:
            return self.DATABASE_URL

        if self.DATABASE_TYPE == "postgresql":
            return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        elif self.DATABASE_TYPE == "sqlite":
            return "sqlite:///./tickets.db"
        else:
            raise ValueError(f"Unsupported database type: {self.DATABASE_TYPE}")


settings = Settings()
