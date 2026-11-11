"""Consumer of ConsultationCompleted (consultation DEC-003, appointment DEC-007)."""
from collections.abc import Awaitable, Callable
from enum import StrEnum

from appointment.application.dto.commands import ConsultationCompletedCommand

CONSULTATION_EXCHANGE = "consultation.events"
ROUTING_KEY = "consultation-completed"
QUEUE = "appointment.consultation-completed"
DEAD_LETTER_QUEUE = "appointment.consultation-completed.dlq"
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (3, 6)


class MalformedMessage(ValueError):
    """The message is not a ConsultationCompleted envelope."""


class Decision(StrEnum):
    ACK = "ACK"
    DEAD_LETTER = "DEAD_LETTER"


def queue_arguments() -> dict:
    raise NotImplementedError


def parse_consultation_completed(body: bytes) -> ConsultationCompletedCommand:
    raise NotImplementedError


class ConsultationCompletedProcessor:
    """Turns one message into a decision; the AMQP wiring acks or dead-letters it."""

    def __init__(self, use_case, sleep: Callable[[float], Awaitable[None]]) -> None:
        self._use_case = use_case
        self._sleep = sleep

    async def process(self, body: bytes) -> Decision:
        raise NotImplementedError
