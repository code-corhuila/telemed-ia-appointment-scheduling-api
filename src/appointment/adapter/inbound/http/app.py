from fastapi import FastAPI

from appointment.config.settings import get_settings


def create_app() -> FastAPI:
    """FastAPI application factory.

    The composition root wires every adapter here. In this first block,
    only the health endpoint exists; domain routers land later.
    """
    settings = get_settings()

    docs_enabled = settings.environment != "production"

    app = FastAPI(
        title="Appointment Scheduling API",
        version="0.1.0",
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "UP", "service": "appointment-scheduling-api"}

    return app
