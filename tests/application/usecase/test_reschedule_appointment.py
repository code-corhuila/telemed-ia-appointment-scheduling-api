from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from appointment.application.dto.commands import CreateAppointmentCommand, RescheduleAppointmentCommand
from appointment.application.usecase.create_appointment import CreateAppointmentUseCaseImpl
from appointment.application.usecase.reschedule_appointment import RescheduleAppointmentUseCaseImpl
from appointment.domain.exception import SlotUnavailable
from appointment.domain.model.appointment_status import AppointmentStatus
from tests.fakes.in_memory_appointment_repository import InMemoryAppointmentRepository

PATIENT_ID = uuid4()
PROFESSIONAL_ID = uuid4()

def _future(h: int) -> datetime:
    return datetime.now(UTC) + timedelta(hours=h)

@pytest.mark.asyncio
async def test_reschedule_transitions_and_publishes() -> None:
    repo = InMemoryAppointmentRepository()
    create = CreateAppointmentUseCaseImpl(repo)
    response = await create.execute(
        CreateAppointmentCommand(patient_id=PATIENT_ID, professional_id=PROFESSIONAL_ID, start=_future(24), end=_future(25))
    )

    use_case = RescheduleAppointmentUseCaseImpl(repo)
    updated = await use_case.execute(
        RescheduleAppointmentCommand(
            appointment_id=response.id,
            new_start=_future(48),
            new_end=_future(49),
        )
    )

    assert updated.status == AppointmentStatus.RESCHEDULED
    assert len(repo.outbox_events) == 2
    assert repo.outbox_events[-1].event_type == "AppointmentRescheduled"

@pytest.mark.asyncio
async def test_reschedule_rejects_overlap() -> None:
    repo = InMemoryAppointmentRepository()
    create = CreateAppointmentUseCaseImpl(repo)
    a = await create.execute(
        CreateAppointmentCommand(patient_id=PATIENT_ID, professional_id=PROFESSIONAL_ID, start=_future(24), end=_future(25))
    )
    await create.execute(
        CreateAppointmentCommand(patient_id=uuid4(), professional_id=PROFESSIONAL_ID, start=_future(48), end=_future(49))
    )

    use_case = RescheduleAppointmentUseCaseImpl(repo)
    with pytest.raises(SlotUnavailable):
        await use_case.execute(
            RescheduleAppointmentCommand(
                appointment_id=a.id,
                new_start=_future(48.5),
                new_end=_future(49.5),
            )
        )
