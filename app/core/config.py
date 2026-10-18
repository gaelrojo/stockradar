from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "StockRadar"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://stockradar:stockradar@localhost:5432/stockradar"
    coverage_window_days: int = 14
    coverage_critical_days: float = 3.0
    coverage_warning_days: float = 7.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
