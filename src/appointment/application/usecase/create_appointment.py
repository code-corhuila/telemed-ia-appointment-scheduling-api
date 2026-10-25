"""Create a new appointment."""
from datetime import UTC, datetime
from uuid import uuid4

from appointment.application.dto.commands import CreateAppointmentCommand
from appointment.application.dto.responses import AppointmentResponse
from appointment.application.ports.outbound.appointment_repository import AppointmentRepository
from appointment.application.usecase._mappers import to_response
from appointment.domain.exception import SlotUnavailable, PatientSlotUnavailable
from appointment.domain.model.appointment import Appointment
from appointment.domain.model.outbox_event import OutboxEvent


class CreateAppointmentUseCaseImpl:
    def __init__(self, repository: AppointmentRepository) -> None:
        self._repository = repository

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
            raise SlotUnavailable("another active appointment occupies the requested time slot")

        patient_overlaps = await self._repository.find_active_overlapping_by_patient(
            cmd.patient_id, appointment.start, appointment.end
        )
        if patient_overlaps:
            raise PatientSlotUnavailable("the patient already has another active appointment at this time")

        # Creamos el evento (el ID se llena en el repositorio)
        payload = {
            "appointmentId": None,
            "patientId": str(appointment.patient_id),
            "professionalId": str(appointment.professional_id),
            "startDateTime": appointment.start.isoformat().replace("+00:00", "Z"),
            "endDateTime": appointment.end.isoformat().replace("+00:00", "Z"),
        }
        event = OutboxEvent(
            id=str(uuid4()),
            event_type="AppointmentCreated",
            payload=payload,
            created_at=datetime.now(UTC)
        )

        saved = await self._repository.save(appointment, outbox_event=event)
        return to_response(saved)
