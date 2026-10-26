"""Appointment aggregate root."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Self
from uuid import UUID

from appointment.domain.exception import (
    AppointmentInThePast,
    InvalidAppointmentTimes,
    InvalidStatusTransition,
)
from appointment.domain.model.appointment_status import AppointmentStatus


@dataclass(slots=True)
class Appointment:
    id: UUID | None
    patient_id: UUID
    professional_id: UUID
    start: datetime
    end: datetime
    status: AppointmentStatus
    preconsultation_summary_id: UUID | None
    post_summary_id: UUID | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = field(default=None)

    @classmethod
    def create(
        cls,
        *,
        patient_id: UUID,
        professional_id: UUID,
        start: datetime,
        end: datetime | None = None,  # <-- Ahora es opcional
        preconsultation_summary_id: UUID | None = None,
    ) -> Self:
        if patient_id is None or professional_id is None:
            raise ValueError("patient_id and professional_id are required")
        
        # Si el usuario no envía 'end', calculamos +30 mins automáticamente
        if end is None:
            end = start + timedelta(minutes=30)

        if end <= start:
            raise InvalidAppointmentTimes("end must be after start")
        now = datetime.now(UTC)
        if start <= now:
            raise AppointmentInThePast("appointments must be scheduled in the future")
        return cls(
            id=None,
            patient_id=patient_id,
            professional_id=professional_id,
            start=start,
            end=end,
            status=AppointmentStatus.CONFIRMED,
            preconsultation_summary_id=preconsultation_summary_id,
            post_summary_id=None,
            cancellation_reason=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

    @classmethod
    def reconstitute(
        cls,
        *,
        id: UUID,
        patient_id: UUID,
        professional_id: UUID,
        start: datetime,
        end: datetime,
        status: AppointmentStatus,
        preconsultation_summary_id: UUID | None,
        post_summary_id: UUID | None,
        cancellation_reason: str | None,
        created_at: datetime,
        updated_at: datetime,
        deleted_at: datetime | None = None,
    ) -> Self:
        return cls(
            id=id,
            patient_id=patient_id,
            professional_id=professional_id,
            start=start,
            end=end,
            status=status,
            preconsultation_summary_id=preconsultation_summary_id,
            post_summary_id=post_summary_id,
            cancellation_reason=cancellation_reason,
            created_at=created_at,
            updated_at=updated_at,
            deleted_at=deleted_at,
        )

    def reschedule(self, *, new_start: datetime, new_end: datetime | None = None) -> None:
        self._ensure_active()
        
        if new_end is None:
            new_end = new_start + timedelta(minutes=30)

        if new_end <= new_start:
            raise InvalidAppointmentTimes("end must be after start")
        now = datetime.now(UTC)
        if new_start <= now:
            raise AppointmentInThePast("appointments must be rescheduled to a future time")
        self.start = new_start
        self.end = new_end
        self.status = AppointmentStatus.RESCHEDULED
        self.updated_at = now

    def cancel(self, *, reason: str) -> None:
        if self.status is AppointmentStatus.COMPLETED:
            raise InvalidStatusTransition("a completed appointment cannot be cancelled")
        if self.status is AppointmentStatus.CANCELLED:
            return
        trimmed = reason.strip()
        if not trimmed:
            raise ValueError("cancellation reason is required")
        self.status = AppointmentStatus.CANCELLED
        self.cancellation_reason = trimmed
        self.updated_at = datetime.now(UTC)

    def mark_completed(self) -> None:
        if self.status is AppointmentStatus.COMPLETED:
            return
        self._ensure_active()
        self.status = AppointmentStatus.COMPLETED
        self.updated_at = datetime.now(UTC)

    def mark_no_show(self) -> None:
        self._ensure_active()
        self.status = AppointmentStatus.NO_SHOW
        self.updated_at = datetime.now(UTC)

    def _ensure_active(self) -> None:
        if self.status.is_terminal:
            raise InvalidStatusTransition(
                f"cannot modify an appointment in status {self.status}"
            )
