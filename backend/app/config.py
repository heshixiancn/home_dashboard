from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Home Service Dashboard"
    db_host: str = "mysql8"
    db_port: int = 3306
    db_name: str = "home_dashboard"
    db_user: str = "home_dashboard"
    db_password: str = Field(default="", repr=False)
    database_url: str | None = None
    check_interval_seconds: int = 60
    cache_ttl_seconds: int = 30
    health_concurrency: int = 10
    static_dir: str = "/app/frontend"

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"mysql+asyncmy://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

