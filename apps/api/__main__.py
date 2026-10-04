"""Entry point: `python -m apps.api`."""

import uvicorn

from appointment.config.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "appointment.adapter.inbound.http.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=settings.server_port,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
