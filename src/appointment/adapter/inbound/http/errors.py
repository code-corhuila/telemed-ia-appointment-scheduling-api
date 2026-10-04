"""Single error envelope of the API (norm 5.3.5).

Every failure — including unknown routes and malformed JSON — responds with
the same shape:

    {"error": "...", "message": "...", "details": [...], "traceId": "..."}

The mapping from domain exception to HTTP status lives here and only here.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from appointment.correlation import get_correlation_id
from appointment.domain.exception import (
    AppointmentNotFound,
    DomainException,
    InvalidStatusTransition,
    SlotUnavailable,
    UnauthorizedOperation,
)


def _envelope(
    *,
    error: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": error,
        "message": message,
        "traceId": get_correlation_id(),
    }
    if details:
        body["details"] = details
    return body


def _status_and_code(exc: Exception) -> tuple[int, str]:
    if isinstance(exc, AppointmentNotFound):
        return 404, "NOT_FOUND"
    if isinstance(exc, InvalidStatusTransition):
        return 422, "INVALID_STATUS_TRANSITION"
    if isinstance(exc, SlotUnavailable):
        return 409, "SLOT_UNAVAILABLE"
    if isinstance(exc, UnauthorizedOperation):
        return 403, "FORBIDDEN"
    if isinstance(exc, DomainException):
        return 422, "BUSINESS_RULE_VIOLATION"
    return 500, "INTERNAL_ERROR"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainException)
    async def _domain(_: Request, exc: DomainException) -> JSONResponse:
        status, code = _status_and_code(exc)
        return JSONResponse(
            status_code=status,
            content=_envelope(error=code, message=str(exc)),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details: list[dict[str, Any]] = []
        for err in exc.errors():
            field = ".".join(str(p) for p in err.get("loc", ()) if p != "body")
            details.append({"field": field or "body", "message": err.get("msg", "invalid")})
        return JSONResponse(
            status_code=400,
            content=_envelope(
                error="VALIDATION_ERROR",
                message="the request has invalid fields",
                details=details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(
                error=code_map.get(exc.status_code, "ERROR"),
                message=str(exc.detail) if exc.detail else "error",
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_envelope(
                error="INTERNAL_ERROR",
                message="an unexpected error occurred",
            ),
        )
