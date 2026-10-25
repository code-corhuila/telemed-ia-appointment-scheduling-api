"""Cancel an existing appointment."""
from datetime import UTC, datetime
from uuid import UUID, uuid4

from appointment.application.dto.commands import CancelAppointmentCommand
from appointment.application.dto.responses import AppointmentResponse
from appointment.application.ports.outbound.appointment_repository import AppointmentRepository
from appointment.application.usecase._mappers import to_response
from appointment.domain.exception import AppointmentNotFound
from appointment.domain.model.outbox_event import OutboxEvent


class CancelAppointmentUseCaseImpl:
    def __init__(self, repository: AppointmentRepository) -> None:
        self._repository = repository

    async def execute(self, cmd: CancelAppointmentCommand, actor_id: UUID) -> AppointmentResponse:
        appointment = await self._repository.find_by_id(cmd.appointment_id)
        if appointment is None:
            raise AppointmentNotFound(f"appointment {cmd.appointment_id} not found")

        appointment.cancel(reason=cmd.reason)

        payload = {
            "appointmentId": str(appointment.id),
            "patientId": str(appointment.patient_id),
            "professionalId": str(appointment.professional_id),
            "startDateTime": appointment.start.isoformat().replace("+00:00", "Z"),
            "cancelledBy": str(actor_id),
            "cancelledAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        event = OutboxEvent(
            id=str(uuid4()),
            event_type="AppointmentCancelled",
            payload=payload,
            created_at=datetime.now(UTC)
        )

        saved = await self._repository.update(appointment, outbox_event=event)
        return to_response(saved)
