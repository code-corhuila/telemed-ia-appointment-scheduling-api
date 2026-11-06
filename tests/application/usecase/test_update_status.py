from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from appointment.application.dto.commands import CreateAppointmentCommand, UpdateAppointmentStatusCommand
from appointment.application.usecase.create_appointment import CreateAppointmentUseCaseImpl
from appointment.application.usecase.update_appointment_status import UpdateAppointmentStatusUseCaseImpl
from appointment.domain.exception import InvalidStatusTransition
from appointment.domain.model.appointment_status import AppointmentStatus
from tests.fakes.in_memory_appointment_repository import InMemoryAppointmentRepository

PATIENT_ID = uuid4()
PROFESSIONAL_ID = uuid4()

def _future(h: int) -> datetime:
    return datetime.now(UTC) + timedelta(hours=h)

@pytest.mark.asyncio
async def test_mark_completed_publishes_event() -> None:
    repo = InMemoryAppointmentRepository()
    create = CreateAppointmentUseCaseImpl(repo)
    a = await create.execute(
        CreateAppointmentCommand(patient_id=PATIENT_ID, professional_id=PROFESSIONAL_ID, start=_future(24))
    )

    use_case = UpdateAppointmentStatusUseCaseImpl(repo)
    updated = await use_case.execute(
        UpdateAppointmentStatusCommand(appointment_id=a.id, status=AppointmentStatus.COMPLETED)
    )
    
    assert updated.status == AppointmentStatus.COMPLETED
    assert len(repo.outbox_events) == 2
    # Si tienes el evento AppointmentCompleted, descomenta la siguiente línea:
    # assert repo.outbox_events[-1].event_type == "AppointmentCompleted"

@pytest.mark.asyncio
async def test_cancel_via_status_endpoint_is_rejected() -> None:
    repo = InMemoryAppointmentRepository()
    create = CreateAppointmentUseCaseImpl(repo)
    a = await create.execute(
        CreateAppointmentCommand(patient_id=PATIENT_ID, professional_id=PROFESSIONAL_ID, start=_future(24))
    )

    use_case = UpdateAppointmentStatusUseCaseImpl(repo)
    with pytest.raises(InvalidStatusTransition):
        await use_case.execute(
            UpdateAppointmentStatusCommand(appointment_id=a.id, status=AppointmentStatus.CANCELLED)
        )
