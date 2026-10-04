"""Entry point: `python -m apps.api`."""

import uvicorn

from appointment.adapter.inbound.http.app import create_app
from appointment.adapter.inbound.http.container import Container
from appointment.config.settings import get_settings


def _build_container() -> Container:
    """Build the runtime container.

    Until the Postgres adapter lands (next PR), the runtime cannot start
    with the real container. For now, raise a clear error.
    """
    raise RuntimeError(
        "runtime container is not yet wired; the Postgres adapter arrives "
        "in the next PR. Until then, tests build their own container."
    )


def _factory() -> object:
    return create_app(container=_build_container())


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "apps.api:_factory",
        factory=True,
        host="0.0.0.0",
        port=settings.server_port,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
