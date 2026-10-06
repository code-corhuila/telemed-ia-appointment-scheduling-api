"""Paginated listings for patients and professionals (norm 5.3.6)."""

from appointment.application.dto.pagination import (
    PaginatedResponse,
    PaginationQuery,
)
from appointment.application.dto.responses import AppointmentResponse
from appointment.application.ports.outbound.appointment_repository import (
    AppointmentRepository,
)
from appointment.application.usecase._mappers import to_page


class ListPatientAppointmentsUseCaseImpl:
    def __init__(self, repository: AppointmentRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        patient_id: int,
        query: PaginationQuery,
    ) -> PaginatedResponse[AppointmentResponse]:
        offset = (query.page - 1) * query.limit
        appointments, total = await self._repository.find_by_patient(
            patient_id, offset=offset, limit=query.limit
        )
        return to_page(
            appointments, page=query.page, limit=query.limit, total=total
        )


class ListProfessionalAppointmentsUseCaseImpl:
    def __init__(self, repository: AppointmentRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        professional_id: int,
        query: PaginationQuery,
    ) -> PaginatedResponse[AppointmentResponse]:
        offset = (query.page - 1) * query.limit
        appointments, total = await self._repository.find_by_professional(
            professional_id, offset=offset, limit=query.limit
        )
        return to_page(
            appointments, page=query.page, limit=query.limit, total=total
        )
