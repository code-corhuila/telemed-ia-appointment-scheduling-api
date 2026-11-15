"""Consumer of ConsultationCompleted (consultation DEC-003, appointment DEC-007).

Queue ``appointment.consultation-completed`` is bound to ``consultation.events`` with the
routing key ``consultation-completed``; a dead-lettered message goes to
``appointment.consultation-completed.dlq``. The consumer reads identifiers only; the optional
``postSummaryId`` is stored on the appointment (appointment DEC-008).
"""
import json
import logging
from collections.abc import Awaitable, Callable

from appointment.adapter.inbound.messaging.topic_queue_consumer import (
    Decision,
    MalformedMessage,
    TopicQueueConsumer,
    dead_letter_arguments,
)
from appointment.application.dto.commands import ConsultationCompletedCommand
from appointment.application.usecase.complete_from_consultation import CompletionOutcome
from appointment.domain.exception import AppointmentNotFound

logger = logging.getLogger(__name__)

CONSULTATION_EXCHANGE = "consultation.events"
ROUTING_KEY = "consultation-completed"
QUEUE = "appointment.consultation-completed"
DEAD_LETTER_QUEUE = "appointment.consultation-completed.dlq"
EVENT_TYPE = "ConsultationCompleted"
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (3, 6)

__all__ = [
    "ConsultationCompletedConsumer",
    "ConsultationCompletedProcessor",
    "Decision",
    "MalformedMessage",
    "parse_consultation_completed",
    "queue_arguments",
]


def queue_arguments() -> dict:
    """Rejected messages go, through the default exchange, to the DLQ."""
    return dead_letter_arguments(DEAD_LETTER_QUEUE)


def parse_consultation_completed(body: bytes) -> ConsultationCompletedCommand:
    try:
        envelope = json.loads(body)
        if not isinstance(envelope, dict) or envelope.get("eventType") != EVENT_TYPE:
            raise MalformedMessage("not a ConsultationCompleted envelope")
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise MalformedMessage("payload must be an object")
        return ConsultationCompletedCommand(
            appointment_id=payload["appointmentId"],
            consultation_id=payload["consultationId"],
            post_summary_id=payload.get("postSummaryId"),
            correlation_id=str(envelope.get("correlationId") or ""),
        )
    except MalformedMessage:
        raise
    except (ValueError, KeyError, TypeError) as e:
        raise MalformedMessage(str(e)) from e


class ConsultationCompletedProcessor:
    """Turns one message into a decision; the AMQP wiring acks or dead-letters it."""

    def __init__(self, use_case, sleep: Callable[[float], Awaitable[None]]) -> None:
        self._use_case = use_case
        self._sleep = sleep

    async def process(self, body: bytes) -> Decision:
        try:
            cmd = parse_consultation_completed(body)
        except MalformedMessage as e:
            logger.warning("ConsultationCompleted malformed, sent to %s: %s", DEAD_LETTER_QUEUE, e)
            return Decision.DEAD_LETTER

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                outcome = await self._use_case.execute(cmd)
            except AppointmentNotFound:
                logger.warning(
                    "ConsultationCompleted for unknown appointment %s (correlationId=%s), "
                    "sent to %s",
                    cmd.appointment_id, cmd.correlation_id, DEAD_LETTER_QUEUE,
                )
                return Decision.DEAD_LETTER
            except Exception as e:
                if attempt == MAX_ATTEMPTS:
                    logger.error(
                        "ConsultationCompleted for appointment %s failed %s times "
                        "(correlationId=%s), sent to %s: %s",
                        cmd.appointment_id, attempt, cmd.correlation_id, DEAD_LETTER_QUEUE, e,
                    )
                    return Decision.DEAD_LETTER
                await self._sleep(BACKOFF_SECONDS[attempt - 1])
                continue

            if outcome is CompletionOutcome.IGNORED:
                logger.warning(
                    "ConsultationCompleted left appointment %s unchanged: it is cancelled or "
                    "missed (correlationId=%s)",
                    cmd.appointment_id, cmd.correlation_id,
                )
            else:
                logger.info(
                    "ConsultationCompleted for appointment %s: %s (correlationId=%s)",
                    cmd.appointment_id, outcome, cmd.correlation_id,
                )
            return Decision.ACK
        return Decision.DEAD_LETTER  # unreachable: the loop always returns


class ConsultationCompletedConsumer(TopicQueueConsumer):
    """AMQP wiring of ``appointment.consultation-completed`` (see TopicQueueConsumer)."""

    def __init__(self, rabbit_url: str, processor: ConsultationCompletedProcessor) -> None:
        super().__init__(
            rabbit_url,
            processor,
            exchange=CONSULTATION_EXCHANGE,
            routing_key=ROUTING_KEY,
            queue=QUEUE,
            dead_letter_queue=DEAD_LETTER_QUEUE,
            name=EVENT_TYPE,
        )
