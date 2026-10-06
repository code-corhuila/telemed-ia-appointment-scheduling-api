"""Update the status of an appointment.

Only the states reachable from the domain state machine are allowed:
COMPLETED, CANCELLED, NO_SHOW. CONFIRMED and RESCHEDULED are managed by
the create / reschedule use cases, not here.
"""

from datetime import UTC, datetime

from appointment.application.dto.commands import UpdateAppointmentStatusCommand
from appointment.application.dto.responses import AppointmentResponse
from appointment.application.events.appointment_events import AppointmentCompleted
from appointment.application.ports.outbound.appointment_repository import (
    AppointmentRepository,
)
from appointment.application.ports.outbound.event_publisher import EventPublisher
from appointment.application.usecase._mappers import to_response
from appointment.domain.exception import AppointmentNotFound, InvalidStatusTransition
from appointment.domain.model.appointment_status import AppointmentStatus


class UpdateAppointmentStatusUseCaseImpl:
    def __init__(
        self,
        repository: AppointmentRepository,
        publisher: EventPublisher,
    ) -> None:
        self._repository = repository
        self._publisher = publisher

    async def execute(
        self, cmd: UpdateAppointmentStatusCommand
    ) -> AppointmentResponse:
        appointment = await self._repository.find_by_id(cmd.appointment_id)
        if appointment is None:
            raise AppointmentNotFound(f"appointment {cmd.appointment_id} not found")

        match cmd.status:
            case AppointmentStatus.COMPLETED:
                appointment.mark_completed()
                saved = await self._repository.update(appointment)
                await self._publisher.publish(
                    AppointmentCompleted(
                        appointment_id=saved.id or 0,
                        patient_id=saved.patient_id,
                        professional_id=saved.professional_id,
                        occurred_at=datetime.now(UTC),
                    )
                )
            case AppointmentStatus.NO_SHOW:
                appointment.mark_no_show()
                saved = await self._repository.update(appointment)
            case AppointmentStatus.CANCELLED:
                raise InvalidStatusTransition(
                    "use the /cancel endpoint to cancel an appointment"
                )
            case AppointmentStatus.CONFIRMED | AppointmentStatus.RESCHEDULED:
                raise InvalidStatusTransition(
                    f"status {cmd.status} is not settable through this endpoint"
                )

        return to_response(saved)
