"""Update the status of an appointment."""
from datetime import UTC, datetime
from uuid import uuid4

from appointment.application.dto.commands import UpdateAppointmentStatusCommand
from appointment.application.dto.responses import AppointmentResponse
from appointment.application.ports.outbound.appointment_repository import AppointmentRepository
from appointment.application.usecase._mappers import to_response
from appointment.domain.exception import AppointmentNotFound, InvalidStatusTransition
from appointment.domain.model.appointment_status import AppointmentStatus
from appointment.domain.model.outbox_event import OutboxEvent


class UpdateAppointmentStatusUseCaseImpl:
    def __init__(self, repository: AppointmentRepository) -> None:
        self._repository = repository

    async def execute(self, cmd: UpdateAppointmentStatusCommand) -> AppointmentResponse:
        appointment = await self._repository.find_by_id(cmd.appointment_id)
        if appointment is None:
            raise AppointmentNotFound(f"appointment {cmd.appointment_id} not found")

        event = None
        match cmd.status:
            case AppointmentStatus.COMPLETED:
                appointment.mark_completed()
                event = OutboxEvent(
                    id=str(uuid4()),
                    event_type="AppointmentCompleted",
                    payload={
                        "appointmentId": str(appointment.id),
                        "patientId": str(appointment.patient_id),
                        "professionalId": str(appointment.professional_id),
                        "completedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z")
                    },
                    correlation_id=cmd.correlation_id,
                    created_at=datetime.now(UTC)
                )
            case AppointmentStatus.NO_SHOW:
                appointment.mark_no_show()
            case AppointmentStatus.CANCELLED:
                raise InvalidStatusTransition("use the /cancel endpoint to cancel an appointment")
            case AppointmentStatus.CONFIRMED | AppointmentStatus.RESCHEDULED:
                raise InvalidStatusTransition(f"status {cmd.status} is not settable through this endpoint")

        saved = await self._repository.update(appointment, outbox_event=event)
        return to_response(saved)
