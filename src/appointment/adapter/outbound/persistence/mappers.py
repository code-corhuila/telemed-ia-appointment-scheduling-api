"""Row ↔ domain mapping helpers."""

from asyncpg import Record

from appointment.domain.model.appointment import Appointment
from appointment.domain.model.appointment_status import AppointmentStatus


def row_to_appointment(row: Record) -> Appointment:
    return Appointment.reconstitute(
        id=row["id"],
        patient_id=row["patient_id"],
        professional_id=row["professional_id"],
        start=row["start_time"],
        end=row["end_time"],
        status=AppointmentStatus(row["status"]),
        preconsultation_summary_id=row["preconsultation_summary_id"],
        post_summary_id=row["post_summary_id"],
        cancellation_reason=row["cancellation_reason"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )
