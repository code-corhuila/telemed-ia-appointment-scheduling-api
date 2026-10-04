"""No-op event publisher.

Per ADR-011 the message broker (RabbitMQ) is still `Proposed`. Until the
ADR is accepted, this publisher logs the event and does nothing else.
The application depends only on the `EventPublisher` protocol, so replacing
this class with a real RabbitMQ adapter later requires no changes to use
cases.
"""

import logging

from appointment.application.ports.outbound.event_publisher import DomainEvent

logger = logging.getLogger(__name__)


class NoOpEventPublisher:
    async def publish(self, event: DomainEvent) -> None:
        logger.info("event suppressed (broker not configured): %s", event.name)
