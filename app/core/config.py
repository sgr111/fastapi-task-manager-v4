from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ===== APP INFO =====
    APP_NAME: str = "FastAPI Task Manager"
    APP_VERSION: str = "2.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # ===== DATABASE =====
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/taskdb"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_RECYCLE: int = 3600
    
    # ===== JWT/AUTH =====
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ===== RATE LIMITING =====
    RATE_LIMIT_ENABLED: bool = True
    # Format: "requests/period" (e.g., "60/minute", "1000/hour")
    RATE_LIMIT_AUTH: str = "30/minute"        # Login/Register
    RATE_LIMIT_TASKS_READ: str = "10/minute"  # List/Get tasks
    RATE_LIMIT_TASKS_WRITE: str = "30/minute"  # Create/Update/Delete tasks
    
    # ===== PAGINATION =====
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100
    
    # ===== VALIDATION =====
    MIN_PASSWORD_LENGTH: int = 8
    BCRYPT_ROUNDS: int = 12
    
    # ===== LOGGING =====
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "text"
    
    # ===== CORS =====
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
