"""Correlation ID propagated through the request lifecycle.

The value lives in a `ContextVar` so any function can read it without
receiving it explicitly. FastAPI runs each request in its own context.
"""

from contextvars import ContextVar

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


def get_correlation_id() -> str:
    return _correlation_id.get() or "unknown"
