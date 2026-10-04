"""Appointment aggregate root.

Owns the entire appointment lifecycle: creation, reschedule, cancellation,
completion and no-show. Enforces every invariant the domain contract
defines, independently of any framework.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Self

from appointment.domain.exception import (
    AppointmentInThePast,
    InvalidAppointmentTimes,
    InvalidStatusTransition,
)
from appointment.domain.model.appointment_status import AppointmentStatus


@dataclass(slots=True)
class Appointment:
    """Aggregate root of the appointment-scheduling domain.

    Do not construct directly. Use `Appointment.create()` for new
    appointments or `Appointment.reconstitute()` when rebuilding from
    persisted state.
    """

    id: int | None
    patient_id: int
    professional_id: int
    start: datetime
    end: datetime
    status: AppointmentStatus
    preconsultation_summary_id: int | None
    post_summary_id: int | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = field(default=None)

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        patient_id: int,
        professional_id: int,
        start: datetime,
        end: datetime,
        preconsultation_summary_id: int | None = None,
    ) -> Self:
        """Create a new appointment in CONFIRMED state.

        Rules enforced here:
        - patient, professional positive.
        - end strictly after start.
        - start strictly in the future.
        """
        if patient_id <= 0 or professional_id <= 0:
            raise ValueError("patient_id and professional_id must be positive")
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
        id: int,
        patient_id: int,
        professional_id: int,
        start: datetime,
        end: datetime,
        status: AppointmentStatus,
        preconsultation_summary_id: int | None,
        post_summary_id: int | None,
        cancellation_reason: str | None,
        created_at: datetime,
        updated_at: datetime,
        deleted_at: datetime | None = None,
    ) -> Self:
        """Rebuild an appointment from persisted state, without re-validating."""
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

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def reschedule(self, *, new_start: datetime, new_end: datetime) -> None:
        """Move the appointment to a new time range.

        Rejected when the current status is terminal.
        """
        self._ensure_active()
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
        """Cancel the appointment with a reason.

        A COMPLETED appointment cannot be cancelled.
        """
        if self.status is AppointmentStatus.COMPLETED:
            raise InvalidStatusTransition("a completed appointment cannot be cancelled")
        if self.status is AppointmentStatus.CANCELLED:
            # Idempotent: cancelling an already-cancelled appointment is a no-op.
            return
        trimmed = reason.strip()
        if not trimmed:
            raise ValueError("cancellation reason is required")
        self.status = AppointmentStatus.CANCELLED
        self.cancellation_reason = trimmed
        self.updated_at = datetime.now(UTC)

    def mark_completed(self) -> None:
        """Transition to COMPLETED. Only active states are allowed."""
        if self.status is AppointmentStatus.COMPLETED:
            return
        self._ensure_active()
        self.status = AppointmentStatus.COMPLETED
        self.updated_at = datetime.now(UTC)

    def mark_no_show(self) -> None:
        """Transition to NO_SHOW. Only allowed from CONFIRMED or RESCHEDULED."""
        self._ensure_active()
        self.status = AppointmentStatus.NO_SHOW
        self.updated_at = datetime.now(UTC)

    # ------------------------------------------------------------------
    # Internal guards
    # ------------------------------------------------------------------

    def _ensure_active(self) -> None:
        if self.status.is_terminal:
            raise InvalidStatusTransition(
                f"cannot modify an appointment in status {self.status}"
            )
