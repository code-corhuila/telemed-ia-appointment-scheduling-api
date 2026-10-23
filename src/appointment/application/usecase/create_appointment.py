"""Create a new appointment.

Flow:
1. Rebuild the aggregate from the command. Domain validates future start
   and end > start.
2. Verify no active appointment overlaps the same professional and time.
3. Persist.
4. Publish AppointmentCreated.
"""

from datetime import UTC, datetime

from appointment.application.dto.commands import CreateAppointmentCommand
from appointment.application.dto.responses import AppointmentResponse
from appointment.application.events.appointment_events import AppointmentCreated
from appointment.application.ports.outbound.appointment_repository import (
    AppointmentRepository,
)
from appointment.application.ports.outbound.event_publisher import EventPublisher
from appointment.application.usecase._mappers import to_response
from appointment.domain.exception import SlotUnavailable, PatientSlotUnavailable
from appointment.domain.model.appointment import Appointment


class CreateAppointmentUseCaseImpl:
    def __init__(
        self,
        repository: AppointmentRepository,
        publisher: EventPublisher,
    ) -> None:
        self._repository = repository
        self._publisher = publisher

    async def execute(self, cmd: CreateAppointmentCommand) -> AppointmentResponse:
        appointment = Appointment.create(
            patient_id=cmd.patient_id,
            professional_id=cmd.professional_id,
            start=cmd.start,
            end=cmd.end,
            preconsultation_summary_id=cmd.preconsultation_summary_id,
        )

        prof_overlaps = await self._repository.find_active_overlapping(
            cmd.professional_id, appointment.start, appointment.end
        )
        if prof_overlaps:
            raise SlotUnavailable(
                "another active appointment occupies the requested time slot"
            )

        patient_overlaps = await self._repository.find_active_overlapping_by_patient(
            cmd.patient_id, appointment.start, appointment.end
        )
        if patient_overlaps:
            raise PatientSlotUnavailable(
                "the patient already has another active appointment at this time"
            )

        saved = await self._repository.save(appointment)

        if saved.id is None:
            raise RuntimeError("saved appointment has no id")

        await self._publisher.publish(
            AppointmentCreated(
                appointment_id=saved.id,
                patient_id=saved.patient_id,
                professional_id=saved.professional_id,
                occurred_at=datetime.now(UTC),
            )
        )

        return to_response(saved)
