"""Persistence boundary for recurring professional availability.

The API computes bookable slots from these records plus existing
appointments. Nothing is persisted about the computed slots themselves.
"""

from datetime import time
from typing import Protocol


class AvailabilityRepository(Protocol):
    """Read-only access to the recurring availability records."""

    async def find_active_by_professional(
        self,
        professional_id: int,
    ) -> list[tuple[int, time, time]]:
        """Return [(day_of_week, start_time, end_time), ...] for the given
        professional.

        Only `active = true` records are returned. `day_of_week` follows
        ISO (1 = Monday, 7 = Sunday).
        """
        ...
