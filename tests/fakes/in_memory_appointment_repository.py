"""In-memory implementation of AppointmentRepository for use case tests."""

from datetime import datetime

from appointment.domain.model.appointment import Appointment
from appointment.domain.model.appointment_status import AppointmentStatus


class InMemoryAppointmentRepository:
    def __init__(self) -> None:
        self._items: dict[int, Appointment] = {}
        self._next_id = 1

    async def save(self, appointment: Appointment) -> Appointment:
        appointment.id = self._next_id
        self._next_id += 1
        self._items[appointment.id] = appointment
        return appointment

    async def update(self, appointment: Appointment) -> Appointment:
        if appointment.id is None or appointment.id not in self._items:
            raise ValueError("appointment does not exist")
        self._items[appointment.id] = appointment
        return appointment

    async def find_by_id(self, appointment_id: int) -> Appointment | None:
        return self._items.get(appointment_id)

    async def find_by_patient(
        self, patient_id: int, *, offset: int, limit: int
    ) -> tuple[list[Appointment], int]:
        filtered = [
            a for a in self._items.values()
            if a.patient_id == patient_id and a.deleted_at is None
        ]
        filtered.sort(key=lambda a: a.start, reverse=True)
        total = len(filtered)
        return filtered[offset : offset + limit], total

    async def find_by_professional(
        self, professional_id: int, *, offset: int, limit: int
    ) -> tuple[list[Appointment], int]:
        filtered = [
            a for a in self._items.values()
            if a.professional_id == professional_id and a.deleted_at is None
        ]
        filtered.sort(key=lambda a: a.start, reverse=True)
        total = len(filtered)
        return filtered[offset : offset + limit], total

    async def find_active_overlapping(
        self,
        professional_id: int,
        start: datetime,
        end: datetime,
    ) -> list[Appointment]:
        return [
            a
            for a in self._items.values()
            if a.professional_id == professional_id
            and a.status in (AppointmentStatus.CONFIRMED, AppointmentStatus.RESCHEDULED)
            and a.start < end
            and start < a.end
        ]
