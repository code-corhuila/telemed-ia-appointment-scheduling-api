from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient


def test_health_is_public(client: TestClient) -> None:
    assert client.get("/health").status_code == 200


def test_list_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/appointments/patient/1")
    assert response.status_code == 401
    body = response.json()
    assert body["error"] == "UNAUTHORIZED"
    assert "traceId" in body


def test_list_with_wrong_role_returns_403(client: TestClient, make_token) -> None:
    token = make_token("1", "PATIENT")
    response = client.get(
        "/api/appointments/professional/2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"] == "FORBIDDEN"


def test_expired_token_returns_401(client: TestClient, make_token) -> None:
    token = make_token("1", "PATIENT", minutes=-10)
    response = client.get(
        "/api/appointments/patient/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_hs256_token_is_rejected(client: TestClient) -> None:
    # Sign with HMAC using a random key: the algorithm must be rejected
    # before signature verification.
    exp = int((datetime.now(UTC) + timedelta(hours=1)).timestamp())
    payload = {"sub": "1", "role": "PATIENT", "exp": exp}
    token = jwt.encode(payload, "01234567890123456789012345678901", algorithm="HS256")
    response = client.get(
        "/api/appointments/patient/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_correlation_id_is_echoed_back(client: TestClient, make_token) -> None:
    token = make_token("1", "PATIENT")
    response = client.get(
        "/api/appointments/patient/1",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Correlation-Id": "test-correlation-123",
        },
    )
    assert response.headers["X-Correlation-Id"] == "test-correlation-123"
