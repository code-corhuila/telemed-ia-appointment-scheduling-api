"""Cancel an existing appointment.

Flow:
1. Load the aggregate.
2. Delegate to `Appointment.cancel()` (rejects COMPLETED, idempotent on CANCELLED).
3. Persist.
4. Publish AppointmentCancelled.
"""

from datetime import UTC, datetime

from appointment.application.dto.commands import CancelAppointmentCommand
from appointment.application.dto.responses import AppointmentResponse
from appointment.application.events.appointment_events import AppointmentCancelled
from appointment.application.ports.outbound.appointment_repository import (
    AppointmentRepository,
)
from appointment.application.ports.outbound.event_publisher import EventPublisher
from appointment.application.usecase._mappers import to_response
from appointment.domain.exception import AppointmentNotFound


class CancelAppointmentUseCaseImpl:
    def __init__(
        self,
        repository: AppointmentRepository,
        publisher: EventPublisher,
    ) -> None:
        self._repository = repository
        self._publisher = publisher

    async def execute(
        self,
        cmd: CancelAppointmentCommand,
        actor_id: int,
    ) -> AppointmentResponse:
        appointment = await self._repository.find_by_id(cmd.appointment_id)
        if appointment is None:
            raise AppointmentNotFound(f"appointment {cmd.appointment_id} not found")

        appointment.cancel(reason=cmd.reason)
        saved = await self._repository.update(appointment)

        await self._publisher.publish(
            AppointmentCancelled(
                appointment_id=saved.id or 0,
                patient_id=saved.patient_id,
                professional_id=saved.professional_id,
                cancelled_by=str(actor_id),
                occurred_at=datetime.now(UTC),
            )
        )

        return to_response(saved)
