"""HTTP middlewares.

Currently only correlation. The idempotency and access log middlewares
live in their own modules.
"""

import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from appointment.correlation import set_correlation_id

CORRELATION_HEADER = "X-Correlation-Id"


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Reuses the incoming X-Correlation-Id or generates a new one.

    The value is:
    - stored in a ContextVar so handlers and error envelopes can read it,
    - echoed back in the response header.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get(CORRELATION_HEADER)
        correlation_id = incoming if incoming else str(uuid.uuid4())
        set_correlation_id(correlation_id)
        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response
