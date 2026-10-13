from __future__ import annotations
from typing import List
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    API_V1_PREFIX: str = "/api"
    DATABASE_URL: str | None = None
    SECRET_KEY: str = "dev-insecure-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DOSE_OVERDUE_GRACE_MINUTES: int = 60
    DOSE_REMINDER_LEAD_MINUTES: int = 15
    WORKER_POLL_SECONDS: int = 60
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    ENVIRONMENT: str = "development"

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
        if self.DOSE_OVERDUE_GRACE_MINUTES < 0:
            raise ValueError("DOSE_OVERDUE_GRACE_MINUTES must not be negative")
        if self.DOSE_REMINDER_LEAD_MINUTES < 0:
            raise ValueError("DOSE_REMINDER_LEAD_MINUTES must not be negative")
        if self.WORKER_POLL_SECONDS <= 0:
            raise ValueError("WORKER_POLL_SECONDS must be positive")
        if self.ENVIRONMENT.lower() not in {"development", "test"} and (
            len(self.SECRET_KEY) < 32
            or self.SECRET_KEY == "dev-insecure-change-me"
            or self.SECRET_KEY.startswith("CHANGE_ME")
            or len(set(self.SECRET_KEY)) < 16
            or sum((
                any(char.islower() for char in self.SECRET_KEY),
                any(char.isupper() for char in self.SECRET_KEY),
                any(char.isdigit() for char in self.SECRET_KEY),
                any(not char.isalnum() for char in self.SECRET_KEY),
            )) < 3
        ):
            raise ValueError("Set a strong, random SECRET_KEY outside development")
        return self


settings = Settings()


def get_cors_origins() -> List[str]:
    raw = settings.CORS_ORIGINS
    if not raw:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    # Split by comma, strip spaces
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins if origins else ["http://localhost:5173", "http://127.0.0.1:5173"]
