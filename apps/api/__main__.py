"""Runtime entry point: `python -m apps.api`.

Builds the real container, manages the asyncpg pool through FastAPI's
lifespan, and starts uvicorn.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from appointment.adapter.inbound.http.app import create_app
from appointment.adapter.inbound.http.container import Container
from appointment.adapter.inbound.http.idempotency import InMemoryIdempotencyStore
from appointment.adapter.outbound.persistence.appointment_repository import (
    PostgresAppointmentRepository,
)
from appointment.adapter.outbound.persistence.availability_repository import (
    PostgresAvailabilityRepository,
)
from appointment.application.usecase.cancel_appointment import (
    CancelAppointmentUseCaseImpl,
)
from appointment.application.usecase.create_appointment import (
    CreateAppointmentUseCaseImpl,
)
from appointment.application.usecase.get_appointment import (
    GetAppointmentUseCaseImpl,
)
from appointment.application.usecase.list_upcoming_reminders import ListUpcomingRemindersUseCaseImpl
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
from appointment.config.database import create_pool
from appointment.adapter.outbound.messaging.outbox_poller import OutboxPoller
from appointment.config.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    pool = await create_pool(settings)
    try:
        appointment_repo = PostgresAppointmentRepository(pool, settings.db_schema)
        # AvailabilityRepository is not used yet by the exposed endpoints,
        # but is wired so the next PR (slot computation) can consume it
        # without touching the composition root.
        _availability_repo = PostgresAvailabilityRepository(pool, settings.db_schema)

        app.state.container = Container(
            create=CreateAppointmentUseCaseImpl(appointment_repo),
            cancel=CancelAppointmentUseCaseImpl(appointment_repo),
            reschedule=RescheduleAppointmentUseCaseImpl(appointment_repo),
            update_status=UpdateAppointmentStatusUseCaseImpl(appointment_repo),
            list_patient=ListPatientAppointmentsUseCaseImpl(appointment_repo),
            list_professional=ListProfessionalAppointmentsUseCaseImpl(appointment_repo),
            get_by_id=GetAppointmentUseCaseImpl(appointment_repo),
            list_reminders=ListUpcomingRemindersUseCaseImpl(appointment_repo),
        )
        app.state.idempotency = InMemoryIdempotencyStore()
        
        # Start Outbox Poller (resilient: don't crash the API if RabbitMQ is down)
        try:
            poller = OutboxPoller(pool, settings.rabbitmq_url)
            await poller.start()
            app.state.outbox_poller = poller
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                f"Failed to start OutboxPoller (RabbitMQ might be down). "
                f"The API will start but outbox events won't be published until the next restart. Error: {e}"
            )

        yield
    finally:
        if hasattr(app.state, 'outbox_poller'):
            await app.state.outbox_poller.stop()
        await pool.close()


def factory() -> FastAPI:
    return create_app(lifespan=lifespan)


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "apps.api.__main__:factory",
        factory=True,
        host="0.0.0.0",
        port=settings.server_port,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
