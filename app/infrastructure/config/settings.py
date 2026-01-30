"""Application settings"""
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "Tickets System API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    # Database
    DATABASE_URL: Optional[str] = None
    DATABASE_TYPE: str = "postgresql"  # sqlite, postgresql, mysql
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "tickets"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "123456"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours in minutes

    # JWT
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24  # Token expiration time in hours

    # Default Admin User
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_EMAIL: str = "admin@kostalegal.com"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"  # Change this in production!

    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_BOT_ENABLED: bool = False
    BACKEND_URL: str = "http://localhost:8000"  # Backend URL for bot to call API

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

