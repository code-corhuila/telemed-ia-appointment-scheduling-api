"""Store the pre-consultation summary id on its appointment (DEC-009)."""
from enum import StrEnum

from appointment.application.dto.commands import PreConsultationSummaryGeneratedCommand
from appointment.application.ports.outbound.appointment_repository import AppointmentRepository
from appointment.domain.exception import AppointmentNotFound


class LinkOutcome(StrEnum):
    LINKED = "LINKED"
    ALREADY_LINKED = "ALREADY_LINKED"
    KEPT_EXISTING = "KEPT_EXISTING"


class PreconsultationPatientMismatch(Exception):
    """The event's patient is not the appointment's patient."""


class LinkPreconsultationSummaryUseCaseImpl:
    """An empty preconsultation_summary_id takes the event's summaryId, whatever the status: it
    is a reference, not a transition. A stored id is never replaced, and the link is never
    written to another patient's appointment. No outbox event: nobody listens for the link."""

    def __init__(self, repository: AppointmentRepository) -> None:
        self._repository = repository

    async def execute(self, cmd: PreConsultationSummaryGeneratedCommand) -> LinkOutcome:
        appointment = await self._repository.find_by_id(cmd.appointment_id)
        if appointment is None:
            raise AppointmentNotFound(f"appointment {cmd.appointment_id} not found")
        if appointment.patient_id != cmd.patient_id:
            raise PreconsultationPatientMismatch(
                f"summary {cmd.summary_id} is not for the patient of appointment "
                f"{cmd.appointment_id}"
            )

        if appointment.preconsultation_summary_id == cmd.summary_id:
            return LinkOutcome.ALREADY_LINKED
        if appointment.preconsultation_summary_id is not None:
            return LinkOutcome.KEPT_EXISTING

        appointment.preconsultation_summary_id = cmd.summary_id
        await self._repository.update(appointment)
        return LinkOutcome.LINKED
