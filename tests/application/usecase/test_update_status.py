from datetime import UTC, datetime, timedelta

import pytest

from appointment.application.dto.commands import (
    CreateAppointmentCommand,
    UpdateAppointmentStatusCommand,
)
from appointment.application.usecase.create_appointment import (
    CreateAppointmentUseCaseImpl,
)
from appointment.application.usecase.update_appointment_status import (
    UpdateAppointmentStatusUseCaseImpl,
)
from appointment.domain.exception import InvalidStatusTransition
from appointment.domain.model.appointment_status import AppointmentStatus
from tests.fakes.in_memory_appointment_repository import InMemoryAppointmentRepository
from tests.fakes.recording_event_publisher import RecordingEventPublisher

from uuid import uuid4 as _uuid4
from appointment.application.events.appointment_events import AppointmentCompleted

PATIENT_ID = _uuid4()
PROFESSIONAL_ID = _uuid4()
OTHER_PATIENT_ID = _uuid4()
OTHER_PROFESSIONAL_ID = _uuid4()




def _future(h: int) -> datetime:
    return datetime.now(UTC) + timedelta(hours=h)


@pytest.mark.asyncio
async def test_mark_completed_publishes_event() -> None:
    repo = InMemoryAppointmentRepository()
    publisher = RecordingEventPublisher()
    create = CreateAppointmentUseCaseImpl(repo, publisher)
    a = await create.execute(
        CreateAppointmentCommand(
            patient_id=PATIENT_ID, professional_id=PROFESSIONAL_ID, start=_future(24), end=_future(25)
        )
    )

    use_case = UpdateAppointmentStatusUseCaseImpl(repo, publisher)
    updated = await use_case.execute(
        UpdateAppointmentStatusCommand(
            appointment_id=a.id, status=AppointmentStatus.COMPLETED
        )
    )
    assert updated.status == AppointmentStatus.COMPLETED
    assert isinstance(publisher.events[-1], AppointmentCompleted)


@pytest.mark.asyncio
async def test_cancel_via_status_endpoint_is_rejected() -> None:
    repo = InMemoryAppointmentRepository()
    publisher = RecordingEventPublisher()
    create = CreateAppointmentUseCaseImpl(repo, publisher)
    a = await create.execute(
        CreateAppointmentCommand(
            patient_id=PATIENT_ID, professional_id=PROFESSIONAL_ID, start=_future(24), end=_future(25)
        )
    )

    use_case = UpdateAppointmentStatusUseCaseImpl(repo, publisher)
    with pytest.raises(InvalidStatusTransition):
        await use_case.execute(
            UpdateAppointmentStatusCommand(
                appointment_id=a.id, status=AppointmentStatus.CANCELLED
            )
        )
