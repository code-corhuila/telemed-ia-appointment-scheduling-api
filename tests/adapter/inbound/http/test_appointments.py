from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _future(h: int) -> str:
    return (datetime.now(UTC) + timedelta(hours=h)).isoformat()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_create_appointment_returns_201(client: TestClient, make_token) -> None:
    token = make_token("1", "PATIENT")
    response = client.post(
        "/api/appointments/",
        headers={**_auth(token), "Idempotency-Key": "test-key-12345678"},
        json={
            "patientId": 1,
            "professionalId": 2,
            "start": _future(24),
            "end": _future(25),
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "CONFIRMED"
    assert body["patientId"] == 1


def test_create_without_idempotency_key_returns_400(client: TestClient, make_token) -> None:
    token = make_token("1", "PATIENT")
    response = client.post(
        "/api/appointments/",
        headers=_auth(token),
        json={
            "patientId": 1,
            "professionalId": 2,
            "start": _future(24),
            "end": _future(25),
        },
    )
    assert response.status_code == 400


def test_create_is_idempotent(client: TestClient, make_token) -> None:
    token = make_token("1", "PATIENT")
    headers = {**_auth(token), "Idempotency-Key": "same-key-12345678"}
    body = {
        "patientId": 1,
        "professionalId": 2,
        "start": _future(24),
        "end": _future(25),
    }
    first = client.post("/api/appointments/", headers=headers, json=body)
    second = client.post("/api/appointments/", headers=headers, json=body)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_cancel_and_list(client: TestClient, make_token) -> None:
    token = make_token("1", "PATIENT")
    created = client.post(
        "/api/appointments/",
        headers={**_auth(token), "Idempotency-Key": "cancel-test-12345678"},
        json={
            "patientId": 1,
            "professionalId": 2,
            "start": _future(24),
            "end": _future(25),
        },
    ).json()

    cancelled = client.patch(
        f"/api/appointments/{created['id']}/cancel",
        headers=_auth(token),
        json={"reason": "no longer available"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["cancellationReason"] == "no longer available"

    listing = client.get("/api/appointments/patient/1", headers=_auth(token))
    assert listing.status_code == 200
    body = listing.json()
    assert "data" in body and "meta" in body
    assert body["meta"]["total"] == 1


def test_invalid_json_returns_400_envelope(client: TestClient, make_token) -> None:
    token = make_token("1", "PATIENT")
    response = client.post(
        "/api/appointments/",
        headers={
            **_auth(token),
            "Idempotency-Key": "bad-json-12345678",
            "Content-Type": "application/json",
        },
        content=b"{not json",
    )
    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"
    assert "traceId" in response.json()


def test_unknown_route_returns_404_with_envelope(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"
    assert "traceId" in response.json()
