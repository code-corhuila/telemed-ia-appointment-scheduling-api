from datetime import UTC, datetime, timedelta
from uuid import uuid4

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
from appointment.domain.exception import PatientSlotUnavailable, SlotUnavailable
from tests.fakes.in_memory_appointment_repository import InMemoryAppointmentRepository
from tests.fakes.recording_event_publisher import RecordingEventPublisher


def _future(h: int) -> datetime:
    return datetime.now(UTC) + timedelta(hours=h)


@pytest.mark.asyncio
async def test_create_rejects_patient_overlap() -> None:
    repo = InMemoryAppointmentRepository()
    use_case = CreateAppointmentUseCaseImpl(repo)
    patient_id = uuid4()

    # Primera cita
    await use_case.execute(
        CreateAppointmentCommand(
            patient_id=patient_id,
            professional_id=uuid4(),
            start=_future(24),
            end=_future(25),
        )
    )

    # Segunda cita, mismo paciente, distinto profesional, hora solapada
    with pytest.raises(PatientSlotUnavailable):
        await use_case.execute(
            CreateAppointmentCommand(
                patient_id=patient_id,
                professional_id=uuid4(),
                start=_future(24.5),
                end=_future(25.5),
            )
        )


@pytest.mark.asyncio
async def test_create_rejects_professional_overlap() -> None:
    repo = InMemoryAppointmentRepository()
    use_case = CreateAppointmentUseCaseImpl(repo)
    prof_id = uuid4()

    # Primera cita
    await use_case.execute(
        CreateAppointmentCommand(
            patient_id=uuid4(),
            professional_id=prof_id,
            start=_future(24),
            end=_future(25),
        )
    )

    # Segunda cita, distinto paciente, mismo profesional, hora solapada
    with pytest.raises(SlotUnavailable):
        await use_case.execute(
            CreateAppointmentCommand(
                patient_id=uuid4(),
                professional_id=prof_id,
                start=_future(24.5),
                end=_future(25.5),
            )
        )


@pytest.mark.asyncio
async def test_reschedule_rejects_patient_overlap() -> None:
    repo = InMemoryAppointmentRepository()
    create = CreateAppointmentUseCaseImpl(repo)
    patient_id = uuid4()

    # Primera cita
    await create.execute(
        CreateAppointmentCommand(
            patient_id=patient_id,
            professional_id=uuid4(),
            start=_future(24),
            end=_future(25),
        )
    )

    # Segunda cita base
    resp2 = await create.execute(
        CreateAppointmentCommand(
            patient_id=patient_id,
            professional_id=uuid4(),
            start=_future(48),
            end=_future(49),
        )
    )

    reschedule = RescheduleAppointmentUseCaseImpl(repo)
    with pytest.raises(PatientSlotUnavailable):
        await reschedule.execute(
            RescheduleAppointmentCommand(
                appointment_id=resp2.id,
                new_start=_future(24.5),
                new_end=_future(25.5),
            )
        )
