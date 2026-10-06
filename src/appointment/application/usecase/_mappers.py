"""Internal helpers shared by the use cases."""

from appointment.application.dto.pagination import PageMeta, PaginatedResponse
from appointment.application.dto.responses import AppointmentResponse
from appointment.domain.model.appointment import Appointment


def to_response(appointment: Appointment) -> AppointmentResponse:
    return AppointmentResponse.from_domain(appointment)


def to_page(
    appointments: list[Appointment],
    *,
    page: int,
    limit: int,
    total: int,
) -> PaginatedResponse[AppointmentResponse]:
    return PaginatedResponse[AppointmentResponse](
        data=[to_response(a) for a in appointments],
        meta=PageMeta.of(page=page, limit=limit, total=total),
    )
