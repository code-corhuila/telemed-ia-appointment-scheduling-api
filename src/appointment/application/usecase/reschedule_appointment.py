"""Reschedule an existing appointment to a new time range.

Flow:
1. Load the aggregate.
2. Delegate to `Appointment.reschedule()` (rejects terminal statuses).
3. Check no active appointment overlaps the new range for the same professional.
4. Persist.
5. Publish AppointmentRescheduled.
"""

from datetime import UTC, datetime

from appointment.application.dto.commands import RescheduleAppointmentCommand
from appointment.application.dto.responses import AppointmentResponse
from appointment.application.events.appointment_events import AppointmentRescheduled
from appointment.application.ports.outbound.appointment_repository import (
    AppointmentRepository,
)
from appointment.application.ports.outbound.event_publisher import EventPublisher
from appointment.application.usecase._mappers import to_response
from appointment.domain.exception import AppointmentNotFound, SlotUnavailable


class RescheduleAppointmentUseCaseImpl:
    def __init__(
        self,
        repository: AppointmentRepository,
        publisher: EventPublisher,
    ) -> None:
        self._repository = repository
        self._publisher = publisher

    async def execute(
        self, cmd: RescheduleAppointmentCommand
    ) -> AppointmentResponse:
        appointment = await self._repository.find_by_id(cmd.appointment_id)
        if appointment is None:
            raise AppointmentNotFound(f"appointment {cmd.appointment_id} not found")

        previous_start = appointment.start
        appointment.reschedule(new_start=cmd.new_start, new_end=cmd.new_end)

        overlaps = await self._repository.find_active_overlapping(
            appointment.professional_id, appointment.start, appointment.end
        )
        # The appointment itself may appear in the result if the repo does not
        # exclude it. Filter out by id.
        overlaps = [o for o in overlaps if o.id != appointment.id]
        if overlaps:
            raise SlotUnavailable(
                "another active appointment occupies the requested time slot"
            )

        saved = await self._repository.update(appointment)

        await self._publisher.publish(
            AppointmentRescheduled(
                appointment_id=saved.id or 0,
                patient_id=saved.patient_id,
                professional_id=saved.professional_id,
                previous_start=previous_start,
                new_start=saved.start,
                occurred_at=datetime.now(UTC),
            )
        )

        return to_response(saved)
