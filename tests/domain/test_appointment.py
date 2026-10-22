from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from appointment.domain.exception import (
    AppointmentInThePast,
    InvalidAppointmentTimes,
    InvalidStatusTransition,
)
from appointment.domain.model.appointment import Appointment
from appointment.domain.model.appointment_status import AppointmentStatus


def _future(hours: int = 24) -> datetime:
    return datetime.now(UTC) + timedelta(hours=hours)


def _create() -> Appointment:
    return Appointment.create(
        patient_id=uuid4(),
        professional_id=uuid4(),
        start=_future(24),
        end=_future(25),
    )


def test_create_starts_in_confirmed() -> None:
    appt = _create()
    assert appt.status is AppointmentStatus.CONFIRMED
    assert appt.cancellation_reason is None


def test_create_rejects_end_before_start() -> None:
    with pytest.raises(InvalidAppointmentTimes):
        Appointment.create(
            patient_id=uuid4(),
            professional_id=uuid4(),
            start=_future(25),
            end=_future(24),
        )


def test_create_rejects_start_in_the_past() -> None:
    with pytest.raises(AppointmentInThePast):
        Appointment.create(
            patient_id=uuid4(),
            professional_id=uuid4(),
            start=_future(-24),
            end=_future(-23),
        )


def test_create_rejects_missing_ids() -> None:
    with pytest.raises(ValueError):
        Appointment.create(patient_id=None, professional_id=uuid4(), start=_future(24), end=_future(25))
    with pytest.raises(ValueError):
        Appointment.create(patient_id=uuid4(), professional_id=None, start=_future(24), end=_future(25))


def test_reschedule_from_confirmed_transitions_to_rescheduled() -> None:
    appt = _create()
    appt.reschedule(new_start=_future(48), new_end=_future(49))
    assert appt.status is AppointmentStatus.RESCHEDULED


def test_reschedule_rejects_terminal_status() -> None:
    appt = _create()
    appt.cancel(reason="patient request")
    with pytest.raises(InvalidStatusTransition):
        appt.reschedule(new_start=_future(48), new_end=_future(49))


def test_cancel_sets_reason_and_status() -> None:
    appt = _create()
    appt.cancel(reason="patient unavailable")
    assert appt.status is AppointmentStatus.CANCELLED
    assert appt.cancellation_reason == "patient unavailable"


def test_cancel_is_idempotent() -> None:
    appt = _create()
    appt.cancel(reason="first")
    appt.cancel(reason="second")
    assert appt.cancellation_reason == "first"


def test_cancel_rejects_completed() -> None:
    appt = _create()
    appt.mark_completed()
    with pytest.raises(InvalidStatusTransition):
        appt.cancel(reason="too late")


def test_mark_completed_from_active() -> None:
    appt = _create()
    appt.mark_completed()
    assert appt.status is AppointmentStatus.COMPLETED


def test_mark_completed_is_idempotent() -> None:
    appt = _create()
    appt.mark_completed()
    appt.mark_completed()
    assert appt.status is AppointmentStatus.COMPLETED


def test_mark_no_show_from_confirmed() -> None:
    appt = _create()
    appt.mark_no_show()
    assert appt.status is AppointmentStatus.NO_SHOW


def test_mark_no_show_rejects_completed() -> None:
    appt = _create()
    appt.mark_completed()
    with pytest.raises(InvalidStatusTransition):
        appt.mark_no_show()


def test_cancel_requires_non_blank_reason() -> None:
    appt = _create()
    with pytest.raises(ValueError):
        appt.cancel(reason="   ")
