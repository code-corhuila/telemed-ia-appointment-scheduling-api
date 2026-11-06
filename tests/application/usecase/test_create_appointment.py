from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from appointment.application.dto.commands import CreateAppointmentCommand
from appointment.application.usecase.create_appointment import CreateAppointmentUseCaseImpl
from appointment.domain.exception import AppointmentInThePast, SlotUnavailable
from appointment.domain.model.appointment_status import AppointmentStatus
from tests.fakes.in_memory_appointment_repository import InMemoryAppointmentRepository

PATIENT_ID = uuid4()
PROFESSIONAL_ID = uuid4()

def _future(h: int) -> datetime:
    return datetime.now(UTC) + timedelta(hours=h)

@pytest.mark.asyncio
async def test_create_persists_and_publishes() -> None:
    repo = InMemoryAppointmentRepository()
    use_case = CreateAppointmentUseCaseImpl(repo)

    response = await use_case.execute(
        CreateAppointmentCommand(
            patient_id=PATIENT_ID,
            professional_id=PROFESSIONAL_ID,
            start=_future(24),
        )
    )

    assert response.id is not None
    assert response.status == "CONFIRMED"
    assert len(repo.outbox_events) == 1
    assert repo.outbox_events[0].event_type == "AppointmentCreated"

@pytest.mark.asyncio
async def test_create_rejects_past_start() -> None:
    use_case = CreateAppointmentUseCaseImpl(InMemoryAppointmentRepository())
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
    use_case = CreateAppointmentUseCaseImpl(repo)

    await use_case.execute(
        CreateAppointmentCommand(
            patient_id=PATIENT_ID,
            professional_id=PROFESSIONAL_ID,
            start=_future(24),
        )
    )

    with pytest.raises(SlotUnavailable):
        await use_case.execute(
            CreateAppointmentCommand(
                patient_id=uuid4(),
                professional_id=PROFESSIONAL_ID,
                start=_future(24.25), # 15 mins después, dentro de los 30 mins
            )
        )
