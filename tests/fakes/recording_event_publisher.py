"""Fake publisher that records every event instead of sending it."""

from appointment.application.ports.outbound.event_publisher import DomainEvent


class RecordingEventPublisher:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)
