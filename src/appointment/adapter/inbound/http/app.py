"""FastAPI application factory.

Two modes:
- Tests pass an explicit `Container` with fakes (`create_app(container=...)`).
- Runtime passes a `lifespan` that builds the real container and manages
  the database pool (`create_app(lifespan=...)`).
"""

from typing import Any

from fastapi import FastAPI

from appointment.adapter.inbound.http.container import Container
from appointment.adapter.inbound.http.errors import register_error_handlers
from appointment.adapter.inbound.http.idempotency import InMemoryIdempotencyStore
from appointment.adapter.inbound.http.middleware import CorrelationMiddleware
from appointment.adapter.inbound.http.routers.appointments import router as appointments_router
from appointment.config.settings import get_settings


def create_app(
    *,
    container: Container | None = None,
    lifespan: Any = None,
) -> FastAPI:
    settings = get_settings()
    docs_enabled = settings.environment != "production"

    app = FastAPI(
        title="Appointment Scheduling API",
        version="0.1.0",
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
    )

    app.add_middleware(CorrelationMiddleware)

    if container is not None:
        app.state.container = container
        app.state.idempotency = InMemoryIdempotencyStore()

    register_error_handlers(app)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "UP", "service": "appointment-scheduling-api"}

    app.include_router(appointments_router)
    return app
