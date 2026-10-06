"""Value object representing a bookable time slot for a professional."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Availability:
    """A General Practitioner and time slot currently available for booking.

    This is a value object: it has no identity, only attributes. Two
    availabilities with the same fields are equivalent.

    The API computes availabilities at query time from the recurring
    `professional_availability` table plus existing appointments. Nothing
    is persisted here.
    """

    professional_id: int
    start: datetime
    end: datetime
    is_bookable: bool = True

    def __post_init__(self) -> None:
        if self.professional_id <= 0:
            raise ValueError("professional_id must be positive")
        if self.end <= self.start:
            raise ValueError("end must be after start")

    def overlaps_with(self, other_start: datetime, other_end: datetime) -> bool:
        """Return True when the given time range overlaps this availability."""
        return self.start < other_end and other_start < self.end
