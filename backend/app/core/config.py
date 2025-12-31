"""
Configuration settings for the application.
Uses Pydantic Settings for environment variable management.
"""
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Annoy - Data Anonymization Tool"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Quebec Law 25 Compliant Data Anonymization API"

    # CORS Settings
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "annoy_db"
    POSTGRES_PORT: int = 5432

    # Computed database URL
    DATABASE_URL: PostgresDsn | None = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None, values) -> str:
        """Construct database URL from components if not provided."""
        if isinstance(v, str):
            return v

        # Access data dict for Pydantic v2
        data = values.data if hasattr(values, 'data') else values

        return PostgresDsn.build(
            scheme="postgresql",
            username=data.get("POSTGRES_USER"),
            password=data.get("POSTGRES_PASSWORD"),
            host=data.get("POSTGRES_SERVER"),
            port=data.get("POSTGRES_PORT"),
            path=f"{data.get('POSTGRES_DB') or ''}",
        ).unicode_string()

    # File Upload Settings
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB in bytes
    ALLOWED_EXTENSIONS: set[str] = {".csv"}
    UPLOAD_DIR: str = "./uploads"

    # Anonymization Settings
    DEFAULT_PSEUDONYM_SEED: int = 42

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )


# Global settings instance
settings = Settings()
