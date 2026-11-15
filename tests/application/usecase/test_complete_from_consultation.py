"""DEC-007: ConsultationCompleted moves the appointment to COMPLETED."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from appointment.application.dto.commands import ConsultationCompletedCommand
from appointment.application.usecase.complete_from_consultation import (
    CompleteAppointmentFromConsultationUseCaseImpl,
    CompletionOutcome,
)
from appointment.domain.exception import AppointmentNotFound
from appointment.domain.model.appointment import Appointment
from appointment.domain.model.appointment_status import AppointmentStatus
from tests.fakes.in_memory_appointment_repository import InMemoryAppointmentRepository

PATIENT_ID = uuid4()
PROFESSIONAL_ID = uuid4()


async def _appointment(
    repo: InMemoryAppointmentRepository, status: AppointmentStatus
) -> Appointment:
    now = datetime.now(UTC)
    appointment = Appointment.reconstitute(
        id=uuid4(),
        patient_id=PATIENT_ID,
        professional_id=PROFESSIONAL_ID,
        start=now + timedelta(hours=1),
        end=now + timedelta(hours=1, minutes=30),
        status=status,
        preconsultation_summary_id=None,
        post_summary_id=None,
        cancellation_reason="patient asked" if status is AppointmentStatus.CANCELLED else None,
        created_at=now,
        updated_at=now,
    )
    repo._items[appointment.id] = appointment
    return appointment


def _command(appointment_id, post_summary_id=None) -> ConsultationCompletedCommand:
    return ConsultationCompletedCommand(
        appointment_id=appointment_id,
        consultation_id=uuid4(),
        post_summary_id=post_summary_id,
        correlation_id="corr-1",
    )


@pytest.mark.parametrize("status", [AppointmentStatus.CONFIRMED, AppointmentStatus.RESCHEDULED])
async def test_completes_an_active_appointment_and_publishes_appointment_completed(status) -> None:
    repo = InMemoryAppointmentRepository()
    appointment = await _appointment(repo, status)

    use_case = CompleteAppointmentFromConsultationUseCaseImpl(repo)
    outcome = await use_case.execute(_command(appointment.id))

    assert outcome is CompletionOutcome.COMPLETED
    assert (await repo.find_by_id(appointment.id)).status is AppointmentStatus.COMPLETED
    assert len(repo.outbox_events) == 1
    event = repo.outbox_events[0]
    assert event.event_type == "AppointmentCompleted"
    assert event.correlation_id == "corr-1"
    assert event.payload["appointmentId"] == str(appointment.id)
    assert event.payload["patientId"] == str(PATIENT_ID)
    assert event.payload["professionalId"] == str(PROFESSIONAL_ID)


async def test_a_repeated_event_changes_nothing() -> None:
    repo = InMemoryAppointmentRepository()
    appointment = await _appointment(repo, AppointmentStatus.COMPLETED)

    use_case = CompleteAppointmentFromConsultationUseCaseImpl(repo)
    outcome = await use_case.execute(_command(appointment.id))

    assert outcome is CompletionOutcome.ALREADY_COMPLETED
    assert repo.outbox_events == []


@pytest.mark.parametrize("status", [AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW])
async def test_leaves_a_cancelled_or_missed_appointment_unchanged(status) -> None:
    repo = InMemoryAppointmentRepository()
    appointment = await _appointment(repo, status)

    use_case = CompleteAppointmentFromConsultationUseCaseImpl(repo)
    outcome = await use_case.execute(_command(appointment.id))

    assert outcome is CompletionOutcome.IGNORED
    assert (await repo.find_by_id(appointment.id)).status is status
    assert repo.outbox_events == []


async def test_an_unknown_appointment_is_an_error() -> None:
    repo = InMemoryAppointmentRepository()

    with pytest.raises(AppointmentNotFound):
        await CompleteAppointmentFromConsultationUseCaseImpl(repo).execute(_command(uuid4()))


async def test_completing_stores_the_post_summary_id() -> None:
    repo = InMemoryAppointmentRepository()
    appointment = await _appointment(repo, AppointmentStatus.CONFIRMED)
    post_summary_id = uuid4()

    use_case = CompleteAppointmentFromConsultationUseCaseImpl(repo)
    await use_case.execute(_command(appointment.id, post_summary_id))

    assert (await repo.find_by_id(appointment.id)).post_summary_id == post_summary_id


async def test_a_completed_appointment_without_summary_takes_it_from_a_repeated_event() -> None:
    repo = InMemoryAppointmentRepository()
    appointment = await _appointment(repo, AppointmentStatus.COMPLETED)
    post_summary_id = uuid4()

    use_case = CompleteAppointmentFromConsultationUseCaseImpl(repo)
    outcome = await use_case.execute(_command(appointment.id, post_summary_id))

    assert outcome is CompletionOutcome.ALREADY_COMPLETED
    assert (await repo.find_by_id(appointment.id)).post_summary_id == post_summary_id
    assert repo.outbox_events == []


async def test_a_repeated_event_does_not_replace_a_stored_summary() -> None:
    repo = InMemoryAppointmentRepository()
    appointment = await _appointment(repo, AppointmentStatus.COMPLETED)
    stored = uuid4()
    appointment.post_summary_id = stored

    use_case = CompleteAppointmentFromConsultationUseCaseImpl(repo)
    await use_case.execute(_command(appointment.id, uuid4()))

    assert (await repo.find_by_id(appointment.id)).post_summary_id == stored


async def test_an_event_without_summary_completes_as_before() -> None:
    repo = InMemoryAppointmentRepository()
    appointment = await _appointment(repo, AppointmentStatus.CONFIRMED)

    use_case = CompleteAppointmentFromConsultationUseCaseImpl(repo)
    outcome = await use_case.execute(_command(appointment.id))

    assert outcome is CompletionOutcome.COMPLETED
    assert (await repo.find_by_id(appointment.id)).post_summary_id is None
