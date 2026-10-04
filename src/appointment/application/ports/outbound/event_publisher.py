"""Publish boundary for domain events.

The application only depends on this Protocol. The infrastructure provides
a NoOp implementation (logs the event) until ADR-011 (message broker) is
accepted.
"""

from typing import Protocol

from appointment.application.events.appointment_events import (
    AppointmentCancelled,
    AppointmentCompleted,
    AppointmentCreated,
    AppointmentRescheduled,
)

DomainEvent = (
    AppointmentCreated
    | AppointmentRescheduled
    | AppointmentCancelled
    | AppointmentCompleted
)


class EventPublisher(Protocol):
    """Publishes domain events after the transaction commits."""

    async def publish(self, event: DomainEvent) -> None:
        ...
