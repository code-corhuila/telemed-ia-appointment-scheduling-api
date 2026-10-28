"""Input DTOs of the use cases.

Commands only enforce *shape* validation (non-nil UUIDs, non-blank strings).
Business rules (end > start, future start, state transitions) stay in the
domain, not here.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

from appointment.domain.model.appointment_status import AppointmentStatus


class CreateAppointmentCommand(BaseModel):
    patient_id: UUID
    professional_id: UUID
    start: datetime
    preconsultation_summary_id: UUID | None = None
    correlation_id: str = ""

    @field_validator("patient_id", "professional_id")
    @classmethod
    def _non_nil_uuid(cls, v: UUID) -> UUID:
        if v.int == 0:
            raise ValueError("uuid cannot be nil")
        return v


class CancelAppointmentCommand(BaseModel):
    appointment_id: UUID
    reason: str
    correlation_id: str = ""

    @field_validator("appointment_id")
    @classmethod
    def _non_nil_uuid(cls, v: UUID) -> UUID:
        if v.int == 0:
            raise ValueError("uuid cannot be nil")
        return v


class RescheduleAppointmentCommand(BaseModel):
    appointment_id: UUID
    new_start: datetime
    correlation_id: str = ""

    @field_validator("appointment_id")
    @classmethod
    def _non_nil_uuid(cls, v: UUID) -> UUID:
        if v.int == 0:
            raise ValueError("uuid cannot be nil")
        return v


class UpdateAppointmentStatusCommand(BaseModel):
    appointment_id: UUID
    status: AppointmentStatus
    correlation_id: str = ""

    @field_validator("appointment_id")
    @classmethod
    def _non_nil_uuid(cls, v: UUID) -> UUID:
        if v.int == 0:
            raise ValueError("uuid cannot be nil")
        return v
