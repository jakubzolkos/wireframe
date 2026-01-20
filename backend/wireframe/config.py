from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Wireframe"
    
    # Security / Auth (existing ones)
    FRONTEND_URL: str = "http://localhost:3000"
    
    # External Services (existing ones)
    UL_CLIENT_ID: Optional[str] = None
    UL_CLIENT_SECRET: Optional[str] = None
    DIGIKEY_CLIENT_ID: Optional[str] = None
    DIGIKEY_CLIENT_SECRET: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    # Infrastructure
    REDIS_URL: str = "redis://localhost:6379/0"
    POSTGRES_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/wireframe"

settings = Settings()
