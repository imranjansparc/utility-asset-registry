"""Runtime settings. Values come from the environment, never from source."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings the application reads when it starts.

    Copy `.env.example` to `.env` for local development. Production supplies
    the same names through the process environment so a laptop and the
    utility server can run the same build.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./dev.db"
    jwt_secret: str
    jwt_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173"
    rate_limit_per_minute: int = 60
    bootstrap_admin_username: str = ""
    bootstrap_admin_password: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
