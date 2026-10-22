"""HTTP request bodies.

They are distinct from the application DTOs on purpose: HTTP field names
come from the contract, while application DTOs are Python-idiomatic. The
router translates between them.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from appointment.application.dto.base import CamelCaseModel
from appointment.domain.model.appointment_status import AppointmentStatus


class CreateAppointmentRequest(CamelCaseModel):
    patient_id: UUID
    professional_id: UUID
    start: datetime
    end: datetime

    @field_validator("patient_id", "professional_id")
    @classmethod
    def _non_nil_uuid(cls, v: UUID) -> UUID:
        if v.int == 0:
            raise ValueError("uuid cannot be nil")
        return v


class CancelAppointmentRequest(CamelCaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("reason must not be blank")
        return v


class RescheduleAppointmentRequest(CamelCaseModel):
    start: datetime
    end: datetime


class UpdateStatusRequest(CamelCaseModel):
    status: AppointmentStatus
