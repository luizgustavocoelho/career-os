from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    environment: str = "development"
    database_url: str = "sqlite:///./data/careeros.db"
    app_origin: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    cookie_secure: bool = False
    registration_enabled: bool = True
    registration_limit: int = 1
    session_days: int = 7
    openai_api_key: str = ""
    ai_model: str = "gpt-4.1-mini"
    ai_daily_limit: int = 30
    upload_max_mb: int = 8
    data_dir: Path = Path("data")

    def validate_production(self):
        if self.environment == "production":
            if not self.cookie_secure or not self.app_origin.startswith("https://"):
                raise RuntimeError("Production requires HTTPS and COOKIE_SECURE=true")
            if not self.database_url.startswith("postgresql"):
                raise RuntimeError("Production requires PostgreSQL")


@lru_cache
def settings() -> Settings:
    return Settings()
