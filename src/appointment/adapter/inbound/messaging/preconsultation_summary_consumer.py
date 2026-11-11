"""Consumer of PreConsultationSummaryGenerated (appointment DEC-009)."""
from collections.abc import Awaitable, Callable

from appointment.adapter.inbound.messaging.consultation_completed_consumer import (
    Decision,
    MalformedMessage,
)
from appointment.application.dto.commands import PreConsultationSummaryGeneratedCommand

AGENT_EXCHANGE = "agent.events"
ROUTING_KEY = "pre-consultation-summary-generated"
QUEUE = "appointment.pre-consultation-summary-generated"
DEAD_LETTER_QUEUE = "appointment.pre-consultation-summary-generated.dlq"

__all__ = ["Decision", "MalformedMessage"]


def queue_arguments() -> dict:
    raise NotImplementedError


def parse_pre_consultation_summary_generated(body: bytes) -> PreConsultationSummaryGeneratedCommand:
    raise NotImplementedError


class PreConsultationSummaryProcessor:
    def __init__(self, use_case, sleep: Callable[[float], Awaitable[None]]) -> None:
        self._use_case = use_case
        self._sleep = sleep

    async def process(self, body: bytes) -> Decision:
        raise NotImplementedError
