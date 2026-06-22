import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "dopaPal"
    API_V1_STR: str = "/api/v1"
    
    # Database and Cache configuration
    # Default to SQLite for local dev; override with env var for PostgreSQL in Docker
    DATABASE_URL: str = "sqlite:///./dopapal_dev.db"
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Security Configuration
    SECRET_KEY: str = "supersecretjwtkeyforauthenticatingclients"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Google OAuth settings (External integration)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # AI / NLP Module Configuration
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_API_KEY: str = ""
    NVIDIA_MODEL: str = "nvidia/nemotron-3-super-120b-a12b"
    AI_USE_LLM: bool = False  # Deterministic-first: LLM enrichment is opt-in
    OPENAI_API_KEY: str = ""
    
    # Optional local file system path for configuration fallback
    model_config = SettingsConfigDict(
        env_file=[".env", "../.env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
