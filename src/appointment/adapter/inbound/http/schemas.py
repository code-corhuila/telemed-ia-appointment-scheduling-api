"""HTTP request bodies.

They are distinct from the application DTOs on purpose: HTTP field names
come from the contract, while application DTOs are Python-idiomatic. The
router translates between them.
"""

from datetime import datetime

from pydantic import Field, field_validator

from appointment.application.dto.base import CamelCaseModel
from appointment.domain.model.appointment_status import AppointmentStatus


class CreateAppointmentRequest(CamelCaseModel):
    patient_id: int = Field(gt=0)
    professional_id: int = Field(gt=0)
    start: datetime
    end: datetime


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
