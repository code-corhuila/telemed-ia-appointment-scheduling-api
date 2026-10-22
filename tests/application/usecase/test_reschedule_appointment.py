from datetime import UTC, datetime, timedelta

import pytest

from appointment.application.dto.commands import (
    CreateAppointmentCommand,
    RescheduleAppointmentCommand,
)
from appointment.application.usecase.create_appointment import (
    CreateAppointmentUseCaseImpl,
)
from appointment.application.usecase.reschedule_appointment import (
    RescheduleAppointmentUseCaseImpl,
)
from appointment.domain.exception import SlotUnavailable
from appointment.domain.model.appointment_status import AppointmentStatus
from tests.fakes.in_memory_appointment_repository import InMemoryAppointmentRepository
from tests.fakes.recording_event_publisher import RecordingEventPublisher

from uuid import uuid4 as _uuid4
from appointment.application.events.appointment_events import AppointmentRescheduled

PATIENT_ID = _uuid4()
PROFESSIONAL_ID = _uuid4()
OTHER_PATIENT_ID = _uuid4()
OTHER_PROFESSIONAL_ID = _uuid4()




def _future(h: int) -> datetime:
    return datetime.now(UTC) + timedelta(hours=h)


@pytest.mark.asyncio
async def test_reschedule_transitions_and_publishes() -> None:
    repo = InMemoryAppointmentRepository()
    publisher = RecordingEventPublisher()
    create = CreateAppointmentUseCaseImpl(repo, publisher)
    response = await create.execute(
        CreateAppointmentCommand(
            patient_id=PATIENT_ID, professional_id=PROFESSIONAL_ID, start=_future(24), end=_future(25)
        )
    )

    use_case = RescheduleAppointmentUseCaseImpl(repo, publisher)
    updated = await use_case.execute(
        RescheduleAppointmentCommand(
            appointment_id=response.id,
            new_start=_future(48),
            new_end=_future(49),
        )
    )

    assert updated.status == AppointmentStatus.RESCHEDULED
    assert isinstance(publisher.events[-1], AppointmentRescheduled)


@pytest.mark.asyncio
async def test_reschedule_rejects_overlap() -> None:
    repo = InMemoryAppointmentRepository()
    publisher = RecordingEventPublisher()
    create = CreateAppointmentUseCaseImpl(repo, publisher)
    a = await create.execute(
        CreateAppointmentCommand(
            patient_id=PATIENT_ID, professional_id=PROFESSIONAL_ID, start=_future(24), end=_future(25)
        )
    )
    await create.execute(
        CreateAppointmentCommand(
            patient_id=OTHER_PATIENT_ID, professional_id=PROFESSIONAL_ID, start=_future(48), end=_future(49)
        )
    )

    use_case = RescheduleAppointmentUseCaseImpl(repo, publisher)
    with pytest.raises(SlotUnavailable):
        await use_case.execute(
            RescheduleAppointmentCommand(
                appointment_id=a.id,
                new_start=_future(48),
                new_end=_future(49),
            )
        )
