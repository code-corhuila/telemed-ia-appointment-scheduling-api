"""Store the pre-consultation summary id on its appointment (DEC-009)."""
from enum import StrEnum

from appointment.application.dto.commands import PreConsultationSummaryGeneratedCommand
from appointment.application.ports.outbound.appointment_repository import AppointmentRepository


class LinkOutcome(StrEnum):
    LINKED = "LINKED"
    ALREADY_LINKED = "ALREADY_LINKED"
    KEPT_EXISTING = "KEPT_EXISTING"


class PreconsultationPatientMismatch(Exception):
    """The event's patient is not the appointment's patient."""


class LinkPreconsultationSummaryUseCaseImpl:
    def __init__(self, repository: AppointmentRepository) -> None:
        self._repository = repository

    async def execute(self, cmd: PreConsultationSummaryGeneratedCommand) -> LinkOutcome:
        raise NotImplementedError
