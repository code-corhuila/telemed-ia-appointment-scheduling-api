from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration of the service.

    Values are read from environment variables and, in local development,
    from a `.env` file at the project root.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "development"
    server_port: int = 8080

    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "telemed_ia"
    db_user: str = "appointment_scheduling_app"
    db_password: str = ""
    db_schema: str = "appointment_scheduling"

    jwt_public_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
