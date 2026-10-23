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
from appointment.domain.exception import AppointmentNotFound, SlotUnavailable, PatientSlotUnavailable


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

        prof_overlaps = await self._repository.find_active_overlapping(
            appointment.professional_id, appointment.start, appointment.end
        )
        # The appointment itself may appear in the result if the repo does not
        # exclude it. Filter out by id.
        prof_overlaps = [o for o in prof_overlaps if o.id != appointment.id]
        if prof_overlaps:
            raise SlotUnavailable(
                "another active appointment occupies the requested time slot"
            )

        patient_overlaps = await self._repository.find_active_overlapping_by_patient(
            appointment.patient_id, appointment.start, appointment.end
        )
        patient_overlaps = [o for o in patient_overlaps if o.id != appointment.id]
        if patient_overlaps:
            raise PatientSlotUnavailable(
                "the patient already has another active appointment at this time"
            )

        saved = await self._repository.update(appointment)

        if saved.id is None:
            raise RuntimeError("saved appointment has no id")

        await self._publisher.publish(
            AppointmentRescheduled(
                appointment_id=saved.id,
                patient_id=saved.patient_id,
                professional_id=saved.professional_id,
                previous_start=previous_start,
                new_start=saved.start,
                occurred_at=datetime.now(UTC),
            )
        )

        return to_response(saved)
