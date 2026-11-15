"""Complete an appointment when its consultation is completed (DEC-007)."""
from enum import StrEnum

from appointment.application.dto.commands import ConsultationCompletedCommand
from appointment.application.ports.outbound.appointment_repository import AppointmentRepository
from appointment.application.usecase._events import appointment_completed_event
from appointment.domain.exception import AppointmentNotFound
from appointment.domain.model.appointment_status import AppointmentStatus


class CompletionOutcome(StrEnum):
    COMPLETED = "COMPLETED"
    ALREADY_COMPLETED = "ALREADY_COMPLETED"
    IGNORED = "IGNORED"


class CompleteAppointmentFromConsultationUseCaseImpl:
    """CONFIRMED or RESCHEDULED -> COMPLETED; COMPLETED stays (a repeated event);
    CANCELLED and NO_SHOW are left unchanged.

    DEC-008: the event's postSummaryId is stored on the appointment. A completed appointment
    without one takes it from a repeated event; a stored one is never replaced."""

    def __init__(self, repository: AppointmentRepository) -> None:
        self._repository = repository

    async def execute(self, cmd: ConsultationCompletedCommand) -> CompletionOutcome:
        appointment = await self._repository.find_by_id(cmd.appointment_id)
        if appointment is None:
            raise AppointmentNotFound(f"appointment {cmd.appointment_id} not found")

        if appointment.status is AppointmentStatus.COMPLETED:
            if appointment.post_summary_id is None and cmd.post_summary_id is not None:
                appointment.post_summary_id = cmd.post_summary_id
                await self._repository.update(appointment)
            return CompletionOutcome.ALREADY_COMPLETED
        if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW):
            return CompletionOutcome.IGNORED

        appointment.mark_completed()
        appointment.post_summary_id = cmd.post_summary_id
        await self._repository.update(
            appointment, outbox_event=appointment_completed_event(appointment, cmd.correlation_id)
        )
        return CompletionOutcome.COMPLETED
