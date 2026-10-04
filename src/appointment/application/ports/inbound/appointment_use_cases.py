"""Input boundaries of the appointment-scheduling application.

The HTTP layer depends only on these Protocols. The concrete use cases
live in `application/usecase/`.
"""

from typing import Protocol

from appointment.application.dto.commands import (
    CancelAppointmentCommand,
    CreateAppointmentCommand,
    RescheduleAppointmentCommand,
    UpdateAppointmentStatusCommand,
)
from appointment.application.dto.pagination import PaginatedResponse, PaginationQuery
from appointment.application.dto.responses import AppointmentResponse


class CreateAppointmentUseCase(Protocol):
    async def execute(self, cmd: CreateAppointmentCommand) -> AppointmentResponse:
        ...


class CancelAppointmentUseCase(Protocol):
    async def execute(self, cmd: CancelAppointmentCommand, actor_id: int) -> AppointmentResponse:
        ...


class RescheduleAppointmentUseCase(Protocol):
    async def execute(self, cmd: RescheduleAppointmentCommand) -> AppointmentResponse:
        ...


class UpdateAppointmentStatusUseCase(Protocol):
    async def execute(self, cmd: UpdateAppointmentStatusCommand) -> AppointmentResponse:
        ...


class ListPatientAppointmentsUseCase(Protocol):
    async def execute(
        self,
        patient_id: int,
        query: PaginationQuery,
    ) -> PaginatedResponse[AppointmentResponse]:
        ...


class ListProfessionalAppointmentsUseCase(Protocol):
    async def execute(
        self,
        professional_id: int,
        query: PaginationQuery,
    ) -> PaginatedResponse[AppointmentResponse]:
        ...
