"""Lifecycle states of an appointment."""

from enum import StrEnum


class AppointmentStatus(StrEnum):
    """The five states the contract accepts.

    The string values match the OpenAPI enum exactly:
    CONFIRMED, RESCHEDULED, COMPLETED, CANCELLED, NO_SHOW.
    """

    CONFIRMED = "CONFIRMED"
    RESCHEDULED = "RESCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"

    @property
    def is_terminal(self) -> bool:
        """Terminal states cannot transition any further."""
        return self in (AppointmentStatus.COMPLETED,
            AppointmentStatus.CANCELLED,
            AppointmentStatus.NO_SHOW,
            )

    @property
    def is_active(self) -> bool:
        """Active states occupy a time slot and must be checked for conflicts."""
        return self in (AppointmentStatus.CONFIRMED, AppointmentStatus.RESCHEDULED)
