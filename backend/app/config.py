from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Wireframe"
    
    # Security / Auth (existing ones)
    STRIPE_API_KEY: Optional[str] = None
    FRONTEND_URL: str = "http://localhost:3000"
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # External Services (existing ones)
    UL_CLIENT_ID: Optional[str] = None
    UL_CLIENT_SECRET: Optional[str] = None
    DIGIKEY_CLIENT_ID: Optional[str] = None
    DIGIKEY_CLIENT_SECRET: Optional[str] = None
    
    # Infrastructure
    REDIS_URL: str = "redis://localhost:6379/0"
    POSTGRES_URL: str = "postgresql://postgres:postgres@localhost:5432/wireframe"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
