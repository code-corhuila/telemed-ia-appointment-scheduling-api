"""Output DTOs of the use cases.

Serialization is camelCase (norm 5.3.5). Dates serialize as RFC 3339 in
UTC, which Pydantic does natively for `datetime` fields.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    patient_id: UUID = Field(alias="patientId")
    professional_id: UUID = Field(alias="professionalId")
    preconsultation_summary_id: UUID | None = Field(default=None, alias="preconsultationSummaryId")
    post_summary_id: UUID | None = Field(default=None, alias="postSummaryId")
    start: datetime
    end: datetime
    status: str
    cancellation_reason: str | None = Field(default=None, alias="cancellationReason")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    @classmethod
    def from_domain(cls, appointment) -> "AppointmentResponse":
        return cls(
            id=appointment.id,
            patientId=appointment.patient_id,
            professionalId=appointment.professional_id,
            preconsultationSummaryId=appointment.preconsultation_summary_id,
            postSummaryId=appointment.post_summary_id,
            start=appointment.start,
            end=appointment.end,
            status=appointment.status.value,
            cancellationReason=appointment.cancellation_reason,
            createdAt=appointment.created_at,
            updatedAt=appointment.updated_at,
        )
