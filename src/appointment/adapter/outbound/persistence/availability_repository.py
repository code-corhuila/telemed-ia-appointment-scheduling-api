"""asyncpg implementation of AvailabilityRepository."""

from datetime import time

import asyncpg

from appointment.config.database import validate_schema_name


class PostgresAvailabilityRepository:
    def __init__(self, pool: asyncpg.Pool, schema: str) -> None:
        self._pool = pool
        self._schema = validate_schema_name(schema)

    async def find_active_by_professional(
        self,
        professional_id: int,
    ) -> list[tuple[int, time, time]]:
        sql = f"""
            SELECT day_of_week, start_time, end_time
            FROM {self._schema}.professional_availability
            WHERE professional_id = $1 AND active = true
            ORDER BY day_of_week, start_time
        """
        rows = await self._pool.fetch(sql, professional_id)
        return [(r["day_of_week"], r["start_time"], r["end_time"]) for r in rows]
