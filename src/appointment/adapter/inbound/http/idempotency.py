"""In-process idempotency cache (norm 5.3.8).

For the current PR the cache lives in memory. When the service is scaled
horizontally, this must be replaced by a shared store (Postgres table
`idempotency_key`, following the pattern of the patient-management
service). Tracked as debt.
"""

from threading import Lock
from typing import Any

_IDEMPOTENCY_HEADER = "Idempotency-Key"
_MIN_KEY_LEN = 8
_MAX_KEY_LEN = 128


def validate_idempotency_key(value: str | None) -> str:
    if value is None:
        raise ValueError("Idempotency-Key header is required")
    trimmed = value.strip()
    if not (_MIN_KEY_LEN <= len(trimmed) <= _MAX_KEY_LEN):
        raise ValueError(
            f"Idempotency-Key must be between {_MIN_KEY_LEN} and {_MAX_KEY_LEN} characters"
        )
    return trimmed


class IdempotencyConflict(Exception):
    """Same key reused with a different request body (Anexo C)."""


class InMemoryIdempotencyStore:
    """Maps a key to (body_hash, response body)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._store: dict[str, tuple[str, dict[str, Any]]] = {}

    def get(self, key: str, body_hash: str) -> dict[str, Any] | None:
        with self._lock:
            cached = self._store.get(key)
            if cached is None:
                return None
            cached_hash, cached_body = cached
            if cached_hash != body_hash:
                raise IdempotencyConflict(
                    "Idempotency-Key was already used with a different request body"
                )
            return cached_body

    def put(self, key: str, body_hash: str, body: dict[str, Any]) -> None:
        with self._lock:
            self._store[key] = (body_hash, body)
