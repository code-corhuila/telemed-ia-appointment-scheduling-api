import pytest
import jwt
from datetime import datetime, timedelta, UTC
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from appointment.adapter.inbound.http.app import create_app
from appointment.adapter.inbound.http.container import Container
from appointment.application.usecase.cancel_appointment import CancelAppointmentUseCaseImpl
from appointment.application.usecase.create_appointment import CreateAppointmentUseCaseImpl
from appointment.application.usecase.get_appointment import GetAppointmentUseCaseImpl
from appointment.application.usecase.list_appointments import (
    ListPatientAppointmentsUseCaseImpl,
    ListProfessionalAppointmentsUseCaseImpl,
)
from appointment.application.usecase.reschedule_appointment import RescheduleAppointmentUseCaseImpl
from appointment.application.usecase.update_appointment_status import UpdateAppointmentStatusUseCaseImpl
from appointment.config.settings import get_settings
from tests.fakes.in_memory_appointment_repository import InMemoryAppointmentRepository

# ==============================================================================
# 1. Generar llaves RSA para tests (una sola vez por sesión)
# ==============================================================================
@pytest.fixture(scope="session", autouse=True)
def setup_test_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode("utf-8")

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")

    settings = get_settings()
    settings.jwt_private_key = private_pem
    settings.jwt_public_key = public_pem
    yield

# ==============================================================================
# 2. Fixtures base
# ==============================================================================
@pytest.fixture
def container() -> Container:
    repo = InMemoryAppointmentRepository()
    return Container(
        create=CreateAppointmentUseCaseImpl(repo),
        cancel=CancelAppointmentUseCaseImpl(repo),
        reschedule=RescheduleAppointmentUseCaseImpl(repo),
        update_status=UpdateAppointmentStatusUseCaseImpl(repo),
        list_patient=ListPatientAppointmentsUseCaseImpl(repo),
        list_professional=ListProfessionalAppointmentsUseCaseImpl(repo),
        get_by_id=GetAppointmentUseCaseImpl(repo),
    )

@pytest.fixture
def client(container: Container) -> TestClient:
    app = create_app(container=container)
    return TestClient(app)

# ==============================================================================
# 3. Fixture de autenticación
# ==============================================================================
@pytest.fixture
def make_token():
    def _factory(subject: str, role: str, minutes: int = 10) -> str:
        settings = get_settings()
        now = datetime.now(UTC)
        payload = {
            "sub": subject,
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=minutes)
        }
        return jwt.encode(payload, settings.jwt_private_key, algorithm="RS256")
    return _factory
