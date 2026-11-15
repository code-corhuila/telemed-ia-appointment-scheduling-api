"""DEC-009: PreConsultationSummaryGenerated links the summary to its appointment."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from appointment.application.dto.commands import PreConsultationSummaryGeneratedCommand
from appointment.application.usecase.link_preconsultation_summary import (
    LinkOutcome,
    LinkPreconsultationSummaryUseCaseImpl,
    PreconsultationPatientMismatch,
)
from appointment.domain.exception import AppointmentNotFound
from appointment.domain.model.appointment import Appointment
from appointment.domain.model.appointment_status import AppointmentStatus
from tests.fakes.in_memory_appointment_repository import InMemoryAppointmentRepository

PATIENT_ID = uuid4()


async def _appointment(repo, status=AppointmentStatus.CONFIRMED, summary_id=None) -> Appointment:
    now = datetime.now(UTC)
    appointment = Appointment.reconstitute(
        id=uuid4(),
        patient_id=PATIENT_ID,
        professional_id=uuid4(),
        start=now + timedelta(hours=1),
        end=now + timedelta(hours=1, minutes=30),
        status=status,
        preconsultation_summary_id=summary_id,
        post_summary_id=None,
        cancellation_reason="patient asked" if status is AppointmentStatus.CANCELLED else None,
        created_at=now,
        updated_at=now,
    )
    repo._items[appointment.id] = appointment
    return appointment


def _command(appointment_id, summary_id=None, patient_id=PATIENT_ID):
    return PreConsultationSummaryGeneratedCommand(
        appointment_id=appointment_id,
        summary_id=summary_id or uuid4(),
        patient_id=patient_id,
        correlation_id="corr-1",
    )


@pytest.mark.parametrize(
    "status",
    [
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.RESCHEDULED,
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
    ],
)
async def test_stores_the_summary_id_whatever_the_status(status) -> None:
    repo = InMemoryAppointmentRepository()
    appointment = await _appointment(repo, status)
    summary_id = uuid4()

    outcome = await LinkPreconsultationSummaryUseCaseImpl(repo).execute(
        _command(appointment.id, summary_id)
    )

    stored = await repo.find_by_id(appointment.id)
    assert outcome is LinkOutcome.LINKED
    assert stored.preconsultation_summary_id == summary_id
    assert stored.status is status
    assert repo.outbox_events == []


async def test_a_repeated_summary_event_changes_nothing() -> None:
    repo = InMemoryAppointmentRepository()
    summary_id = uuid4()
    appointment = await _appointment(repo, summary_id=summary_id)

    outcome = await LinkPreconsultationSummaryUseCaseImpl(repo).execute(
        _command(appointment.id, summary_id)
    )

    assert outcome is LinkOutcome.ALREADY_LINKED
    assert (await repo.find_by_id(appointment.id)).preconsultation_summary_id == summary_id


async def test_another_stored_summary_is_kept() -> None:
    repo = InMemoryAppointmentRepository()
    existing = uuid4()
    appointment = await _appointment(repo, summary_id=existing)

    outcome = await LinkPreconsultationSummaryUseCaseImpl(repo).execute(
        _command(appointment.id, uuid4())
    )

    assert outcome is LinkOutcome.KEPT_EXISTING
    assert (await repo.find_by_id(appointment.id)).preconsultation_summary_id == existing


async def test_never_links_another_patients_appointment() -> None:
    repo = InMemoryAppointmentRepository()
    appointment = await _appointment(repo)

    with pytest.raises(PreconsultationPatientMismatch):
        await LinkPreconsultationSummaryUseCaseImpl(repo).execute(
            _command(appointment.id, patient_id=uuid4())
        )

    assert (await repo.find_by_id(appointment.id)).preconsultation_summary_id is None


async def test_linking_an_unknown_appointment_is_an_error() -> None:
    repo = InMemoryAppointmentRepository()

    with pytest.raises(AppointmentNotFound):
        await LinkPreconsultationSummaryUseCaseImpl(repo).execute(_command(uuid4()))
