"""Persistence boundary for the Appointment aggregate."""

from datetime import datetime
from typing import Protocol

from appointment.domain.model.appointment import Appointment


class AppointmentRepository(Protocol):
    """Persistence operations the application needs.

    The concrete implementation lives in infrastructure
    (`adapter/outbound/persistence`). Everything is async.
    """

    async def save(self, appointment: Appointment) -> Appointment:
        """Insert a new appointment and return it with its assigned id."""
        ...

    async def update(self, appointment: Appointment) -> Appointment:
        """Persist changes to an existing appointment."""
        ...

    async def find_by_id(self, appointment_id: int) -> Appointment | None:
        """Return the appointment with the given id, or None."""
        ...

    async def find_by_patient(
        self,
        patient_id: int,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[Appointment], int]:
        """Return (page, total) of active appointments for a patient."""
        ...

    async def find_by_professional(
        self,
        professional_id: int,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[Appointment], int]:
        """Return (page, total) of active appointments for a professional."""
        ...

    async def find_active_overlapping(
        self,
        professional_id: int,
        start: datetime,
        end: datetime,
    ) -> list[Appointment]:
        """Return active appointments (CONFIRMED or RESCHEDULED) whose time
        range overlaps [start, end) for the same professional.

        Excludes CANCELLED, COMPLETED and NO_SHOW.
        """
        ...
