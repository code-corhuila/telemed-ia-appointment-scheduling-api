from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from appointment.application.dto.commands import CancelAppointmentCommand, CreateAppointmentCommand
from appointment.application.usecase.cancel_appointment import CancelAppointmentUseCaseImpl
from appointment.application.usecase.create_appointment import CreateAppointmentUseCaseImpl
from appointment.domain.exception import AppointmentNotFound
from appointment.domain.model.appointment_status import AppointmentStatus
from tests.fakes.in_memory_appointment_repository import InMemoryAppointmentRepository

PATIENT_ID = uuid4()
PROFESSIONAL_ID = uuid4()

def _future(h: int) -> datetime:
    return datetime.now(UTC) + timedelta(hours=h)

async def _seed(repo: InMemoryAppointmentRepository, patient_id=None) -> object:
    create = CreateAppointmentUseCaseImpl(repo)
    response = await create.execute(
        CreateAppointmentCommand(
            patient_id=patient_id or PATIENT_ID,
            professional_id=PROFESSIONAL_ID,
            start=_future(24),
            end=_future(25),
        )
    )
    return response.id

@pytest.mark.asyncio
async def test_cancel_sets_status_and_publishes() -> None:
    repo = InMemoryAppointmentRepository()
    appointment_id = await _seed(repo)

    use_case = CancelAppointmentUseCaseImpl(repo)
    response = await use_case.execute(
        CancelAppointmentCommand(appointment_id=appointment_id, reason="request"),
        actor_id=PATIENT_ID,
    )

    assert response.status == AppointmentStatus.CANCELLED
    assert response.cancellation_reason == "request"
    assert len(repo.outbox_events) == 2 # Created + Cancelled
    assert repo.outbox_events[-1].event_type == "AppointmentCancelled"

@pytest.mark.asyncio
async def test_cancel_unknown_id_raises() -> None:
    use_case = CancelAppointmentUseCaseImpl(InMemoryAppointmentRepository())
    with pytest.raises(AppointmentNotFound):
        await use_case.execute(
            CancelAppointmentCommand(appointment_id=uuid4(), reason="x"),
            actor_id=PATIENT_ID,
        )
