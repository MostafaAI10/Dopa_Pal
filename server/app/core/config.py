import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "dopaPal"
    API_V1_STR: str = "/api/v1"
    
    # Database and Cache configuration
    # By default, use docker db host, fallback to localhost
    DATABASE_URL: str = "postgresql://dopapal_user:dopapal_password@db:5432/dopapal_db"
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Security Configuration
    SECRET_KEY: str = "supersecretjwtkeyforauthenticatingclients"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Google OAuth settings (External integration)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    
    # Optional local file system path for configuration fallback
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
