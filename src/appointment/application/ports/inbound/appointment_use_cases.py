"""Input boundaries of the appointment-scheduling application.

The HTTP layer depends only on these Protocols. The concrete use cases
live in `application/usecase/`.
"""

from uuid import UUID

from appointment.application.dto.commands import (
    CancelAppointmentCommand,
    RescheduleAppointmentCommand,
    UpdateAppointmentStatusCommand,
)
from appointment.application.dto.responses import AppointmentResponse


class CancelAppointmentUseCase:
    async def execute(self, cmd: CancelAppointmentCommand, actor_id: UUID) -> AppointmentResponse: ...


class RescheduleAppointmentUseCase:
    async def execute(self, cmd: RescheduleAppointmentCommand) -> AppointmentResponse: ...


class UpdateAppointmentStatusUseCase:
    async def execute(self, cmd: UpdateAppointmentStatusCommand) -> AppointmentResponse: ...


class ListAppointmentsByPatientUseCase:
    async def execute(self, patient_id: UUID, query) -> ...: ...
