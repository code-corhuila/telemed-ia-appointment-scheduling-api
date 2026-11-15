"""Outbox events shared by the use cases."""
from datetime import UTC, datetime
from uuid import uuid4

from appointment.domain.model.appointment import Appointment
from appointment.domain.model.outbox_event import OutboxEvent


def appointment_completed_event(appointment: Appointment, correlation_id: str) -> OutboxEvent:
    """AppointmentCompleted for an appointment that has just been completed."""
    now = datetime.now(UTC)
    return OutboxEvent(
        id=str(uuid4()),
        event_type="AppointmentCompleted",
        payload={
            "appointmentId": str(appointment.id),
            "patientId": str(appointment.patient_id),
            "professionalId": str(appointment.professional_id),
            "completedAt": now.isoformat().replace("+00:00", "Z"),
        },
        correlation_id=correlation_id,
        created_at=now,
    )
