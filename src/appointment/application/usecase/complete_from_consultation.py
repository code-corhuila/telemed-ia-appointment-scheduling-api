"""Complete an appointment when its consultation is completed (DEC-007)."""
from enum import StrEnum

from appointment.application.dto.commands import ConsultationCompletedCommand
from appointment.application.ports.outbound.appointment_repository import AppointmentRepository


class CompletionOutcome(StrEnum):
    COMPLETED = "COMPLETED"
    ALREADY_COMPLETED = "ALREADY_COMPLETED"
    IGNORED = "IGNORED"


class CompleteAppointmentFromConsultationUseCaseImpl:
    def __init__(self, repository: AppointmentRepository) -> None:
        self._repository = repository

    async def execute(self, cmd: ConsultationCompletedCommand) -> CompletionOutcome:
        raise NotImplementedError
