"""A trailing slash must never produce a redirect.

Behind the gateway, Starlette's automatic 307 points to the service's
internal host, which leaks it and breaks the client.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient


def _body(patient_id: str) -> dict[str, str]:
    return {
        "patientId": patient_id,
        "professionalId": str(uuid4()),
        "start": (datetime.now(UTC) + timedelta(hours=30)).isoformat(),
    }


def test_create_without_trailing_slash_returns_201(client: TestClient, make_token) -> None:
    patient_id = str(uuid4())
    response = client.post(
        "/api/appointments",
        headers={
            "Authorization": f"Bearer {make_token(patient_id, 'PATIENT')}",
            "Idempotency-Key": "no-slash-create-1234",
        },
        json=_body(patient_id),
        follow_redirects=False,
    )

    assert response.status_code == 201
    assert "location" not in response.headers


def test_unknown_trailing_slash_returns_404_without_redirect(
    client: TestClient, make_token
) -> None:
    patient_id = str(uuid4())
    response = client.get(
        f"/api/appointments/patient/{patient_id}/",
        headers={"Authorization": f"Bearer {make_token(patient_id, 'PATIENT')}"},
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert "location" not in response.headers
    assert response.json()["error"] == "NOT_FOUND"
