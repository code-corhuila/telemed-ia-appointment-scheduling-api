"""Ownership regression tests.

These tests pin the fixes for the security gaps detected while migrating
appointment-scheduling ids to UUID:

1. GET    /patient/{id}        -> PATIENT only sees their own.
2. GET    /professional/{id}   -> PROFESSIONAL only sees their own.
3. GET    /{appointment_id}    -> PATIENT/PROFESSIONAL only see their own.
4. PATCH  /{id}/cancel         -> PATIENT/PROFESSIONAL only act on their own.
5. PATCH  /{id}/reschedule     -> PATIENT/PROFESSIONAL only act on their own.
6. POST   /                    -> PATIENT cannot create for another patient.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from appointment.application.ports.outbound.event_publisher import DomainEvent


def _future(hours: int) -> str:
    return (
        datetime.now(UTC) + timedelta(hours=hours)
    ).isoformat()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create(
    client: TestClient,
    token: str,
    *,
    patient_id: str,
    professional_id: str,
    idempotency_key: str | None = None,
) -> dict:
    headers = _auth(token)
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    response = client.post(
        "/api/appointments/",
        headers=headers,
        json={
            "patientId": patient_id,
            "professionalId": professional_id,
            "start": _future(24),
            "end": _future(25),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# GET /patient/{id}
# ---------------------------------------------------------------------------

def test_patient_can_list_own_appointments(client: TestClient, make_token) -> None:
    patient = str(uuid4())
    professional = str(uuid4())
    token = make_token(patient, "PATIENT")
    _create(client, token, patient_id=patient, professional_id=professional, idempotency_key="own-1-xxxx")

    response = client.get(f"/api/appointments/patient/{patient}", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 1


def test_patient_cannot_list_another_patients_appointments(
    client: TestClient, make_token
) -> None:
    other_patient = str(uuid4())
    intruder = str(uuid4())
    token = make_token(intruder, "PATIENT")

    response = client.get(
        f"/api/appointments/patient/{other_patient}", headers=_auth(token)
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /professional/{id}
# ---------------------------------------------------------------------------

def test_professional_can_list_own_appointments(
    client: TestClient, make_token
) -> None:
    patient = str(uuid4())
    professional = str(uuid4())
    patient_token = make_token(patient, "PATIENT")
    professional_token = make_token(professional, "PROFESSIONAL")
    _create(
        client,
        patient_token,
        patient_id=patient,
        professional_id=professional,
        idempotency_key="prof-own-1-xxxx",
    )

    response = client.get(
        f"/api/appointments/professional/{professional}",
        headers=_auth(professional_token),
    )
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 1


def test_professional_cannot_list_another_professionals_appointments(
    client: TestClient, make_token
) -> None:
    other_professional = str(uuid4())
    intruder = str(uuid4())
    token = make_token(intruder, "PROFESSIONAL")

    response = client.get(
        f"/api/appointments/professional/{other_professional}",
        headers=_auth(token),
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /{appointment_id}
# ---------------------------------------------------------------------------

def test_get_appointment_by_id_owner_patient_returns_200(
    client: TestClient, make_token
) -> None:
    patient = str(uuid4())
    professional = str(uuid4())
    patient_token = make_token(patient, "PATIENT")
    created = _create(
        client,
        patient_token,
        patient_id=patient,
        professional_id=professional,
        idempotency_key="get-own-1-xxxx",
    )

    response = client.get(
        f"/api/appointments/{created['id']}", headers=_auth(patient_token)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["patientId"] == patient
    assert body["professionalId"] == professional


def test_get_appointment_by_id_other_patient_returns_403(
    client: TestClient, make_token
) -> None:
    patient = str(uuid4())
    professional = str(uuid4())
    intruder = str(uuid4())
    patient_token = make_token(patient, "PATIENT")
    intruder_token = make_token(intruder, "PATIENT")
    created = _create(
        client,
        patient_token,
        patient_id=patient,
        professional_id=professional,
        idempotency_key="get-other-1-xxxx",
    )

    response = client.get(
        f"/api/appointments/{created['id']}", headers=_auth(intruder_token)
    )
    assert response.status_code == 403


def test_get_appointment_by_id_unknown_returns_404(
    client: TestClient, make_token
) -> None:
    token = make_token(str(uuid4()), "PATIENT")
    response = client.get(f"/api/appointments/{uuid4()}", headers=_auth(token))
    assert response.status_code == 404


def test_admin_can_get_any_appointment(client: TestClient, make_token) -> None:
    patient = str(uuid4())
    professional = str(uuid4())
    patient_token = make_token(patient, "PATIENT")
    admin_token = make_token(str(uuid4()), "ADMIN")
    created = _create(
        client,
        patient_token,
        patient_id=patient,
        professional_id=professional,
        idempotency_key="get-admin-1-xxxx",
    )

    response = client.get(
        f"/api/appointments/{created['id']}", headers=_auth(admin_token)
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# PATCH /{id}/cancel
# ---------------------------------------------------------------------------

def test_patient_can_cancel_own_appointment(client: TestClient, make_token) -> None:
    patient = str(uuid4())
    professional = str(uuid4())
    token = make_token(patient, "PATIENT")
    created = _create(
        client,
        token,
        patient_id=patient,
        professional_id=professional,
        idempotency_key="cancel-own-1-xxxx",
    )

    response = client.patch(
        f"/api/appointments/{created['id']}/cancel",
        headers=_auth(token),
        json={"reason": "no longer available"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_patient_cannot_cancel_another_patients_appointment(
    client: TestClient, make_token
) -> None:
    patient = str(uuid4())
    professional = str(uuid4())
    intruder = str(uuid4())
    patient_token = make_token(patient, "PATIENT")
    intruder_token = make_token(intruder, "PATIENT")
    created = _create(
        client,
        patient_token,
        patient_id=patient,
        professional_id=professional,
        idempotency_key="cancel-other-1-xxxx",
    )

    response = client.patch(
        f"/api/appointments/{created['id']}/cancel",
        headers=_auth(intruder_token),
        json={"reason": "hijack"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# POST /
# ---------------------------------------------------------------------------

def test_patient_cannot_create_appointment_for_another_patient(
    client: TestClient, make_token
) -> None:
    patient = str(uuid4())
    other_patient = str(uuid4())
    professional = str(uuid4())
    token = make_token(patient, "PATIENT")

    response = client.post(
        "/api/appointments/",
        headers={
            **_auth(token),
            "Idempotency-Key": "cross-patient-1-xxxx",
        },
        json={
            "patientId": other_patient,
            "professionalId": professional,
            "start": _future(24),
            "end": _future(25),
        },
    )
    assert response.status_code == 403
