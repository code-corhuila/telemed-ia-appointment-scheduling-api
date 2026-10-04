"""Output DTOs of the use cases.

Serialization is camelCase (norm 5.3.5). Dates serialize as RFC 3339 in
UTC, which Pydantic does natively for `datetime` fields.
"""

from datetime import datetime

from appointment.application.dto.base import CamelCaseModel
from appointment.domain.model.appointment import Appointment
from appointment.domain.model.appointment_status import AppointmentStatus


class AppointmentResponse(CamelCaseModel):
    id: int
    patient_id: int
    professional_id: int
    start: datetime
    end: datetime
    status: AppointmentStatus
    preconsultation_summary_id: int | None = None
    post_summary_id: int | None = None
    cancellation_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, appointment: Appointment) -> "AppointmentResponse":
        if appointment.id is None:
            raise ValueError("cannot build a response from a non-persisted appointment")
        return cls(
            id=appointment.id,
            patient_id=appointment.patient_id,
            professional_id=appointment.professional_id,
            start=appointment.start,
            end=appointment.end,
            status=appointment.status,
            preconsultation_summary_id=appointment.preconsultation_summary_id,
            post_summary_id=appointment.post_summary_id,
            cancellation_reason=appointment.cancellation_reason,
            created_at=appointment.created_at,
            updated_at=appointment.updated_at,
        )


class AvailabilityResponse(CamelCaseModel):
    professional_id: int
    start: datetime
    end: datetime
