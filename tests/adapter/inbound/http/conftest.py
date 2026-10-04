"""Fixtures shared by HTTP tests: fake container, JWT factory, TestClient."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from appointment.adapter.inbound.http.app import create_app
from appointment.adapter.inbound.http.container import Container
from appointment.application.usecase.cancel_appointment import (
    CancelAppointmentUseCaseImpl,
)
from appointment.application.usecase.create_appointment import (
    CreateAppointmentUseCaseImpl,
)
from appointment.application.usecase.list_appointments import (
    ListPatientAppointmentsUseCaseImpl,
    ListProfessionalAppointmentsUseCaseImpl,
)
from appointment.application.usecase.reschedule_appointment import (
    RescheduleAppointmentUseCaseImpl,
)
from appointment.application.usecase.update_appointment_status import (
    UpdateAppointmentStatusUseCaseImpl,
)
from appointment.config.settings import get_settings
from tests.fakes.in_memory_appointment_repository import InMemoryAppointmentRepository
from tests.fakes.recording_event_publisher import RecordingEventPublisher

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_KEY = _PRIVATE_KEY.public_key()


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    pem = _PUBLIC_KEY.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    monkeypatch.setenv("JWT_PUBLIC_KEY", pem)
    get_settings.cache_clear()
    from appointment.adapter.inbound.http import auth

    auth._public_key_pem.cache_clear()


@pytest.fixture
def container() -> Container:
    repo = InMemoryAppointmentRepository()
    publisher = RecordingEventPublisher()
    return Container(
        create=CreateAppointmentUseCaseImpl(repo, publisher),
        cancel=CancelAppointmentUseCaseImpl(repo, publisher),
        reschedule=RescheduleAppointmentUseCaseImpl(repo, publisher),
        update_status=UpdateAppointmentStatusUseCaseImpl(repo, publisher),
        list_patient=ListPatientAppointmentsUseCaseImpl(repo),
        list_professional=ListProfessionalAppointmentsUseCaseImpl(repo),
    )


@pytest.fixture
def client(container: Container) -> TestClient:
    return TestClient(create_app(container=container))


@pytest.fixture
def make_token() -> Callable[..., str]:
    def _factory(sub: str, role: str, *, minutes: int = 60) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": sub,
            "role": role,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=minutes)).timestamp()),
        }
        return jwt.encode(payload, _PRIVATE_KEY, algorithm="RS256")

    return _factory
