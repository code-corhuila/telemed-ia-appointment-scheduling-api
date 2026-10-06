"""Input DTOs of the use cases.

Commands only enforce *shape* validation (positive ids, non-blank strings).
Business rules (end > start, future start, state transitions) stay in the
domain, not here.
"""

from datetime import datetime

from pydantic import field_validator

from appointment.application.dto.base import CamelCaseModel
from appointment.domain.model.appointment_status import AppointmentStatus


class CreateAppointmentCommand(CamelCaseModel):
    patient_id: int
    professional_id: int
    start: datetime
    end: datetime
    preconsultation_summary_id: int | None = None

    @field_validator("patient_id", "professional_id")
    @classmethod
    def _positive_ids(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("must be positive")
        return v


class CancelAppointmentCommand(CamelCaseModel):
    appointment_id: int
    reason: str

    @field_validator("appointment_id")
    @classmethod
    def _positive_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("must be positive")
        return v

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("reason must not be blank")
        return v


class RescheduleAppointmentCommand(CamelCaseModel):
    appointment_id: int
    new_start: datetime
    new_end: datetime

    @field_validator("appointment_id")
    @classmethod
    def _positive_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("must be positive")
        return v


class UpdateAppointmentStatusCommand(CamelCaseModel):
    appointment_id: int
    status: AppointmentStatus

    @field_validator("appointment_id")
    @classmethod
    def _positive_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("must be positive")
        return v
