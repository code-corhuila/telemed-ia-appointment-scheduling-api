"""In-memory implementation of AppointmentRepository for use case tests."""

from datetime import datetime
from uuid import UUID, uuid4

from appointment.domain.model.appointment import Appointment
from appointment.domain.model.appointment_status import AppointmentStatus


class InMemoryAppointmentRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Appointment] = {}

    async def save(self, appointment: Appointment) -> Appointment:
        if appointment.id is None:
            appointment.id = uuid4()
        self._items[appointment.id] = appointment
        return appointment

    async def update(self, appointment: Appointment) -> Appointment:
        if appointment.id is None or appointment.id not in self._items:
            raise ValueError("appointment does not exist")
        self._items[appointment.id] = appointment
        return appointment

    async def find_by_id(self, appointment_id: UUID) -> Appointment | None:
        return self._items.get(appointment_id)

    async def find_by_patient(
        self, patient_id: UUID, *, offset: int, limit: int
    ) -> tuple[list[Appointment], int]:
        filtered = [
            a for a in self._items.values()
            if a.patient_id == patient_id and a.deleted_at is None
        ]
        filtered.sort(key=lambda a: a.start, reverse=True)
        total = len(filtered)
        return filtered[offset : offset + limit], total

    async def find_by_professional(
        self, professional_id: UUID, *, offset: int, limit: int
    ) -> tuple[list[Appointment], int]:
        filtered = [
            a for a in self._items.values()
            if a.professional_id == professional_id and a.deleted_at is None
        ]
        filtered.sort(key=lambda a: a.start, reverse=True)
        total = len(filtered)
        return filtered[offset : offset + limit], total

    async def find_active_overlapping_by_patient(
        self,
        patient_id: UUID,
        start: datetime,
        end: datetime,
    ) -> list[Appointment]:
        return [
            a
            for a in self._items.values()
            if a.patient_id == patient_id
            and a.status in (AppointmentStatus.CONFIRMED, AppointmentStatus.RESCHEDULED)
            and a.start < end
            and start < a.end
        ]

    async def find_active_overlapping(
        self,
        professional_id: UUID,
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
