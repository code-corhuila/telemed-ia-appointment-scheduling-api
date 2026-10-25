"""Reschedule an existing appointment."""
from datetime import UTC, datetime
from uuid import uuid4

from appointment.application.dto.commands import RescheduleAppointmentCommand
from appointment.application.dto.responses import AppointmentResponse
from appointment.application.ports.outbound.appointment_repository import AppointmentRepository
from appointment.application.usecase._mappers import to_response
from appointment.domain.exception import AppointmentNotFound, SlotUnavailable, PatientSlotUnavailable
from appointment.domain.model.outbox_event import OutboxEvent


class RescheduleAppointmentUseCaseImpl:
    def __init__(self, repository: AppointmentRepository) -> None:
        self._repository = repository

    async def execute(self, cmd: RescheduleAppointmentCommand) -> AppointmentResponse:
        appointment = await self._repository.find_by_id(cmd.appointment_id)
        if appointment is None:
            raise AppointmentNotFound(f"appointment {cmd.appointment_id} not found")

        previous_start = appointment.start
        appointment.reschedule(new_start=cmd.new_start, new_end=cmd.new_end)

        prof_overlaps = await self._repository.find_active_overlapping(
            appointment.professional_id, appointment.start, appointment.end
        )
        prof_overlaps = [o for o in prof_overlaps if o.id != appointment.id]
        if prof_overlaps:
            raise SlotUnavailable("another active appointment occupies the requested time slot")

        patient_overlaps = await self._repository.find_active_overlapping_by_patient(
            appointment.patient_id, appointment.start, appointment.end
        )
        patient_overlaps = [o for o in patient_overlaps if o.id != appointment.id]
        if patient_overlaps:
            raise PatientSlotUnavailable("the patient already has another active appointment at this time")

        payload = {
            "appointmentId": str(appointment.id),
            "patientId": str(appointment.patient_id),
            "professionalId": str(appointment.professional_id),
            "previousStartDateTime": previous_start.isoformat().replace("+00:00", "Z"),
            "newStartDateTime": appointment.start.isoformat().replace("+00:00", "Z"),
        }
        event = OutboxEvent(
            id=str(uuid4()),
            event_type="AppointmentRescheduled",
            payload=payload,
            created_at=datetime.now(UTC)
        )

        saved = await self._repository.update(appointment, outbox_event=event)
        return to_response(saved)
