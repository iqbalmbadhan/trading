"""Application configuration loaded from environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Trading Bot Platform"
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://trading:trading@db:5432/trading"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Security
    master_key: str = "dev-insecure-master-key-change-me"
    jwt_secret: str = "dev-insecure-jwt-secret-change-me"

    # Trading safety: live trading is opt-in only.
    paper_trading_default: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
