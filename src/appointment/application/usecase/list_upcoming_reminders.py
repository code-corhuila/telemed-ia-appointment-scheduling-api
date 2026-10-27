from datetime import UTC, datetime, timedelta

from appointment.application.dto.responses import AppointmentResponse
from appointment.application.ports.outbound.appointment_repository import AppointmentRepository
from appointment.application.usecase._mappers import to_response


class ListUpcomingRemindersUseCaseImpl:
    def __init__(self, repository: AppointmentRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[AppointmentResponse]:
        now = datetime.now(UTC)
        window_end = now + timedelta(hours=24)
        appointments = await self._repository.find_upcoming_for_reminders(now, window_end)
        return [to_response(a) for a in appointments]
