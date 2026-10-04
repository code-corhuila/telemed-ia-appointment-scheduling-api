from datetime import UTC, datetime, timedelta

import pytest

from appointment.application.dto.commands import (
    CancelAppointmentCommand,
    CreateAppointmentCommand,
)
from appointment.application.usecase.cancel_appointment import (
    CancelAppointmentUseCaseImpl,
)
from appointment.application.usecase.create_appointment import (
    CreateAppointmentUseCaseImpl,
)
from appointment.domain.exception import AppointmentNotFound
from appointment.domain.model.appointment_status import AppointmentStatus
from tests.fakes.in_memory_appointment_repository import InMemoryAppointmentRepository
from tests.fakes.recording_event_publisher import RecordingEventPublisher


def _future(h: int) -> datetime:
    return datetime.now(UTC) + timedelta(hours=h)


async def _seed(repo: InMemoryAppointmentRepository) -> int:
    create = CreateAppointmentUseCaseImpl(repo, RecordingEventPublisher())
    response = await create.execute(
        CreateAppointmentCommand(
            patient_id=1,
            professional_id=2,
            start=_future(24),
            end=_future(25),
        )
    )
    return response.id


@pytest.mark.asyncio
async def test_cancel_sets_status_and_publishes() -> None:
    repo = InMemoryAppointmentRepository()
    publisher = RecordingEventPublisher()
    appointment_id = await _seed(repo)

    use_case = CancelAppointmentUseCaseImpl(repo, publisher)
    response = await use_case.execute(
        CancelAppointmentCommand(appointment_id=appointment_id, reason="request"),
        actor_id=99,
    )

    assert response.status == AppointmentStatus.CANCELLED
    assert response.cancellation_reason == "request"
    assert publisher.events[-1].name == "AppointmentCancelled"


@pytest.mark.asyncio
async def test_cancel_unknown_id_raises() -> None:
    use_case = CancelAppointmentUseCaseImpl(
        InMemoryAppointmentRepository(), RecordingEventPublisher()
    )
    with pytest.raises(AppointmentNotFound):
        await use_case.execute(
            CancelAppointmentCommand(appointment_id=999, reason="x"),
            actor_id=99,
        )
