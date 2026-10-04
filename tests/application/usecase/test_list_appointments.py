from datetime import UTC, datetime, timedelta

import pytest

from appointment.application.dto.commands import CreateAppointmentCommand
from appointment.application.dto.pagination import PaginationQuery
from appointment.application.usecase.create_appointment import (
    CreateAppointmentUseCaseImpl,
)
from appointment.application.usecase.list_appointments import (
    ListPatientAppointmentsUseCaseImpl,
    ListProfessionalAppointmentsUseCaseImpl,
)
from tests.fakes.in_memory_appointment_repository import InMemoryAppointmentRepository
from tests.fakes.recording_event_publisher import RecordingEventPublisher


def _future(h: int) -> datetime:
    return datetime.now(UTC) + timedelta(hours=h)


async def _seed(repo: InMemoryAppointmentRepository, n: int) -> None:
    create = CreateAppointmentUseCaseImpl(repo, RecordingEventPublisher())
    for i in range(n):
        await create.execute(
            CreateAppointmentCommand(
                patient_id=1,
                professional_id=2,
                start=_future(24 + i * 2),
                end=_future(25 + i * 2),
            )
        )


@pytest.mark.asyncio
async def test_list_patient_paginated() -> None:
    repo = InMemoryAppointmentRepository()
    await _seed(repo, 5)

    use_case = ListPatientAppointmentsUseCaseImpl(repo)
    page = await use_case.execute(1, PaginationQuery(page=1, limit=2))

    assert len(page.data) == 2
    assert page.meta.total == 5
    assert page.meta.total_pages == 3
    assert page.meta.page == 1


@pytest.mark.asyncio
async def test_list_professional_paginated() -> None:
    repo = InMemoryAppointmentRepository()
    await _seed(repo, 3)

    use_case = ListProfessionalAppointmentsUseCaseImpl(repo)
    page = await use_case.execute(2, PaginationQuery(page=1, limit=20))

    assert len(page.data) == 3
    assert page.meta.total == 3
    assert page.meta.total_pages == 1
