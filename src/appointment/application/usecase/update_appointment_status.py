"""Update the status of an appointment."""
from appointment.application.dto.commands import UpdateAppointmentStatusCommand
from appointment.application.dto.responses import AppointmentResponse
from appointment.application.ports.outbound.appointment_repository import AppointmentRepository
from appointment.application.usecase._events import appointment_completed_event
from appointment.application.usecase._mappers import to_response
from appointment.domain.exception import AppointmentNotFound, InvalidStatusTransition
from appointment.domain.model.appointment_status import AppointmentStatus


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
                event = appointment_completed_event(appointment, cmd.correlation_id)
            case AppointmentStatus.NO_SHOW:
                appointment.mark_no_show()
            case AppointmentStatus.CANCELLED:
                raise InvalidStatusTransition("use the /cancel endpoint to cancel an appointment")
            case AppointmentStatus.CONFIRMED | AppointmentStatus.RESCHEDULED:
                raise InvalidStatusTransition(f"status {cmd.status} is not settable through this endpoint")

        saved = await self._repository.update(appointment, outbox_event=event)
        return to_response(saved)
