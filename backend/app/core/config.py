"""
Configuration settings for the application.
Uses Pydantic Settings for environment variable management.
"""
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

import json
from typing import Any



class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Annoy - Data Anonymization Tool"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Quebec Law 25 Compliant Data Anonymization API"

    # CORS Settings
    BACKEND_CORS_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any):
        """
        Accepts:
        - list already (ok)
        - JSON string: '["http://localhost:3000"]'
        - comma string: 'http://localhost:3000,http://127.0.0.1:3000'
        """
        if v is None:
            return v
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            # JSON list
            if s.startswith("["):
                try:
                    return json.loads(s)
                except Exception:
                    pass
            # Comma-separated
            return [item.strip() for item in s.split(",") if item.strip()]
        return v

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
    MAX_UPLOAD_SIZE: int = 1 * 1024 * 1024 * 1024  # 1GB in bytes (increased for banking institutions with large datasets)
    ALLOWED_EXTENSIONS: set[str] = {".csv"}
    UPLOAD_DIR: str = "./uploads"

    # Anonymization Settings
    DEFAULT_PSEUDONYM_SEED: int = 42

    # AI Enhanced Detection Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    ENABLE_AI_DETECTION: bool = True  # Activé par défaut
    AI_CONFIDENCE_THRESHOLD: float = 70.0
    OLLAMA_ANALYZE_ALL_COLUMNS: bool = True  # Analyser TOUS les champs avec Ollama

    # Authentication & Security Settings
    JWT_SECRET_KEY: str = "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes token expiration

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )


# Global settings instance
settings = Settings()
