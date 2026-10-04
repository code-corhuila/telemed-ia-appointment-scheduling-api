"""asyncpg connection pool with explicit limits (norm 5.3.10)."""

import asyncpg

from appointment.config.settings import Settings

_SCHEMA_PATTERN = r"^[a-z_][a-z0-9_]*$"


def validate_schema_name(schema: str) -> str:
    """Defensive check before interpolating the schema into SQL."""
    import re

    if not re.match(_SCHEMA_PATTERN, schema):
        raise ValueError(f"invalid schema name: {schema!r}")
    return schema


async def create_pool(settings: Settings) -> asyncpg.Pool:
    """Create the pool. Statement timeout is set per connection."""
    return await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        min_size=2,
        max_size=10,
        command_timeout=5.0,
        server_settings={
            "search_path": settings.db_schema,
            "statement_timeout": "5000",
        },
    )
