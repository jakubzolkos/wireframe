from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    aws_access_key_id: str
    aws_secret_access_key: str
    aws_endpoint_url: str = "http://localhost:9000"
    s3_bucket_name: str = "eda-artifacts"
    use_minio: bool = True

    openai_api_key: str
    anthropic_api_key: str = ""

    e2b_api_key: str

    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    otel_service_name: str = "eda-backend"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
