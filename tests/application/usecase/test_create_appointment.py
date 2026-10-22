from datetime import UTC, datetime, timedelta

import pytest

from appointment.application.dto.commands import CreateAppointmentCommand
from appointment.application.usecase.create_appointment import (
    CreateAppointmentUseCaseImpl,
)
from appointment.domain.exception import AppointmentInThePast, SlotUnavailable
from tests.fakes.in_memory_appointment_repository import InMemoryAppointmentRepository
from tests.fakes.recording_event_publisher import RecordingEventPublisher

from uuid import uuid4 as _uuid4
from appointment.application.events.appointment_events import AppointmentCreated

PATIENT_ID = _uuid4()
PROFESSIONAL_ID = _uuid4()
OTHER_PATIENT_ID = _uuid4()
OTHER_PROFESSIONAL_ID = _uuid4()




def _future(h: int) -> datetime:
    return datetime.now(UTC) + timedelta(hours=h)


@pytest.mark.asyncio
async def test_create_persists_and_publishes() -> None:
    repo = InMemoryAppointmentRepository()
    publisher = RecordingEventPublisher()
    use_case = CreateAppointmentUseCaseImpl(repo, publisher)

    response = await use_case.execute(
        CreateAppointmentCommand(
            patient_id=PATIENT_ID,
            professional_id=PROFESSIONAL_ID,
            start=_future(24),
            end=_future(25),
        )
    )

    assert response.id is not None
    assert response.status == "CONFIRMED"
    assert len(publisher.events) == 1
    assert isinstance(publisher.events[0], AppointmentCreated)


@pytest.mark.asyncio
async def test_create_rejects_past_start() -> None:
    use_case = CreateAppointmentUseCaseImpl(
        InMemoryAppointmentRepository(), RecordingEventPublisher()
    )
    with pytest.raises(AppointmentInThePast):
        await use_case.execute(
            CreateAppointmentCommand(
                patient_id=PATIENT_ID,
                professional_id=PROFESSIONAL_ID,
                start=_future(-2),
                end=_future(-1),
            )
        )


@pytest.mark.asyncio
async def test_create_rejects_overlapping_slot() -> None:
    repo = InMemoryAppointmentRepository()
    use_case = CreateAppointmentUseCaseImpl(repo, RecordingEventPublisher())

    await use_case.execute(
        CreateAppointmentCommand(
            patient_id=PATIENT_ID,
            professional_id=PROFESSIONAL_ID,
            start=_future(24),
            end=_future(25),
        )
    )

    with pytest.raises(SlotUnavailable):
        await use_case.execute(
            CreateAppointmentCommand(
                patient_id=OTHER_PATIENT_ID,
                professional_id=PROFESSIONAL_ID,  # same professional
                start=_future(24),  # overlapping
                end=_future(25),
            )
        )
