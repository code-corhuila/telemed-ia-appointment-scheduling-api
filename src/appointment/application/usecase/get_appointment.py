"""Fetch a single appointment by id."""

from uuid import UUID

from appointment.application.dto.responses import AppointmentResponse
from appointment.application.ports.outbound.appointment_repository import (
    AppointmentRepository,
)
from appointment.application.usecase._mappers import to_response
from appointment.domain.exception import AppointmentNotFound


class GetAppointmentUseCaseImpl:
    def __init__(self, repository: AppointmentRepository) -> None:
        self._repository = repository

    async def execute(self, appointment_id: UUID) -> AppointmentResponse:
        appointment = await self._repository.find_by_id(appointment_id)
        if appointment is None:
            raise AppointmentNotFound(f"appointment {appointment_id} not found")
        return to_response(appointment)
