"""FastAPI application factory.

The composition root wires every adapter here: middlewares, error
handlers, routers and the use cases they depend on.
"""

from fastapi import FastAPI

from appointment.adapter.inbound.http.container import Container
from appointment.adapter.inbound.http.errors import register_error_handlers
from appointment.adapter.inbound.http.idempotency import InMemoryIdempotencyStore
from appointment.adapter.inbound.http.middleware import CorrelationMiddleware
from appointment.adapter.inbound.http.routers.appointments import router as appointments_router
from appointment.config.settings import get_settings


def _default_container() -> Container:
    """Temporary in-memory container.

    Until the Postgres adapter lands (next PR), endpoints respond only
    after receiving a fake repository. Exposed so tests can build their
    own container and pass it to `create_app(container=...)`.
    """
    raise RuntimeError("create_app requires an explicit container")


def create_app(*, container: Container | None = None) -> FastAPI:
    settings = get_settings()
    docs_enabled = settings.environment != "production"

    app = FastAPI(
        title="Appointment Scheduling API",
        version="0.1.0",
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    app.add_middleware(CorrelationMiddleware)

    if container is None:
        raise RuntimeError(
            "create_app requires a Container; the default one is not yet wired"
        )
    app.state.container = container
    app.state.idempotency = InMemoryIdempotencyStore()

    register_error_handlers(app)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "UP", "service": "appointment-scheduling-api"}

    app.include_router(appointments_router)
    return app
