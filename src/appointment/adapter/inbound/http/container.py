"""Composition root of the HTTP adapter.

Holds the use cases so routers can inject them via FastAPI dependencies.
The concrete instances are wired in `app.create_app()`.
"""

from dataclasses import dataclass

from appointment.application.usecase.cancel_appointment import (
    CancelAppointmentUseCaseImpl,
)
from appointment.application.usecase.create_appointment import (
    CreateAppointmentUseCaseImpl,
)
from appointment.application.usecase.list_appointments import (
    ListPatientAppointmentsUseCaseImpl,
    ListProfessionalAppointmentsUseCaseImpl,
)
from appointment.application.usecase.reschedule_appointment import (
    RescheduleAppointmentUseCaseImpl,
)
from appointment.application.usecase.update_appointment_status import (
    UpdateAppointmentStatusUseCaseImpl,
)


@dataclass(frozen=True)
class Container:
    create: CreateAppointmentUseCaseImpl
    cancel: CancelAppointmentUseCaseImpl
    reschedule: RescheduleAppointmentUseCaseImpl
    update_status: UpdateAppointmentStatusUseCaseImpl
    list_patient: ListPatientAppointmentsUseCaseImpl
    list_professional: ListProfessionalAppointmentsUseCaseImpl
