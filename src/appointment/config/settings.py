"""Application settings, loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "telemed_ia"
    db_schema: str = "appointment_scheduling"

    # JWT (private key only used in tests; production only needs public)
    jwt_private_key: str = ""
    jwt_public_key: str = ""

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"

    # Server
    server_port: int = 8080
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
