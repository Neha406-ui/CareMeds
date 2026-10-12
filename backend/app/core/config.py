from __future__ import annotations
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    API_V1_PREFIX: str = "/api"
    DATABASE_URL: str | None = None
    SECRET_KEY: str = "dev-insecure-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    ENVIRONMENT: str = "development"


settings = Settings()


def get_cors_origins() -> List[str]:
    raw = settings.CORS_ORIGINS
    if not raw:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    # Split by comma, strip spaces
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins if origins else ["http://localhost:5173", "http://127.0.0.1:5173"]
