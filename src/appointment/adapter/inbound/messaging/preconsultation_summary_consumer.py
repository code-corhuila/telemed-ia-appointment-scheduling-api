"""Consumer of PreConsultationSummaryGenerated (appointment DEC-009).

Queue ``appointment.pre-consultation-summary-generated`` is bound to ``agent.events`` with the
routing key ``pre-consultation-summary-generated``; a dead-lettered message goes to
``appointment.pre-consultation-summary-generated.dlq``. The consumer reads identifiers only and
never logs clinical content.
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
from appointment.application.dto.commands import PreConsultationSummaryGeneratedCommand
from appointment.application.usecase.link_preconsultation_summary import (
    LinkOutcome,
    PreconsultationPatientMismatch,
)
from appointment.domain.exception import AppointmentNotFound

logger = logging.getLogger(__name__)

AGENT_EXCHANGE = "agent.events"
ROUTING_KEY = "pre-consultation-summary-generated"
QUEUE = "appointment.pre-consultation-summary-generated"
DEAD_LETTER_QUEUE = "appointment.pre-consultation-summary-generated.dlq"
EVENT_TYPE = "PreConsultationSummaryGenerated"
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (3, 6)

__all__ = [
    "Decision",
    "MalformedMessage",
    "PreConsultationSummaryConsumer",
    "PreConsultationSummaryProcessor",
    "parse_pre_consultation_summary_generated",
    "queue_arguments",
]


def queue_arguments() -> dict:
    return dead_letter_arguments(DEAD_LETTER_QUEUE)


def parse_pre_consultation_summary_generated(body: bytes) -> PreConsultationSummaryGeneratedCommand:
    try:
        envelope = json.loads(body)
        if not isinstance(envelope, dict) or envelope.get("eventType") != EVENT_TYPE:
            raise MalformedMessage("not a PreConsultationSummaryGenerated envelope")
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise MalformedMessage("payload must be an object")
        return PreConsultationSummaryGeneratedCommand(
            appointment_id=payload["appointmentId"],
            summary_id=payload["summaryId"],
            patient_id=payload["patientId"],
            correlation_id=str(envelope.get("correlationId") or ""),
        )
    except MalformedMessage:
        raise
    except (ValueError, KeyError, TypeError) as e:
        raise MalformedMessage(str(e)) from e


class PreConsultationSummaryProcessor:
    """Turns one message into a decision; the AMQP wiring acks or dead-letters it."""

    def __init__(self, use_case, sleep: Callable[[float], Awaitable[None]]) -> None:
        self._use_case = use_case
        self._sleep = sleep

    async def process(self, body: bytes) -> Decision:
        try:
            cmd = parse_pre_consultation_summary_generated(body)
        except MalformedMessage as e:
            logger.warning("%s malformed, sent to %s: %s", EVENT_TYPE, DEAD_LETTER_QUEUE, e)
            return Decision.DEAD_LETTER

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                outcome = await self._use_case.execute(cmd)
            except (AppointmentNotFound, PreconsultationPatientMismatch) as e:
                logger.warning(
                    "%s for appointment %s not linked (correlationId=%s), sent to %s: %s",
                    EVENT_TYPE, cmd.appointment_id, cmd.correlation_id, DEAD_LETTER_QUEUE,
                    type(e).__name__,
                )
                return Decision.DEAD_LETTER
            except Exception as e:
                if attempt == MAX_ATTEMPTS:
                    logger.error(
                        "%s for appointment %s failed %s times (correlationId=%s), sent to %s: %s",
                        EVENT_TYPE, cmd.appointment_id, attempt, cmd.correlation_id,
                        DEAD_LETTER_QUEUE, e,
                    )
                    return Decision.DEAD_LETTER
                await self._sleep(BACKOFF_SECONDS[attempt - 1])
                continue

            if outcome is LinkOutcome.KEPT_EXISTING:
                logger.warning(
                    "%s left appointment %s with its stored summary (correlationId=%s)",
                    EVENT_TYPE, cmd.appointment_id, cmd.correlation_id,
                )
            else:
                logger.info(
                    "%s for appointment %s: %s (correlationId=%s)",
                    EVENT_TYPE, cmd.appointment_id, outcome, cmd.correlation_id,
                )
            return Decision.ACK
        return Decision.DEAD_LETTER  # unreachable: the loop always returns


class PreConsultationSummaryConsumer(TopicQueueConsumer):
    """AMQP wiring of ``appointment.pre-consultation-summary-generated``."""

    def __init__(self, rabbit_url: str, processor: PreConsultationSummaryProcessor) -> None:
        super().__init__(
            rabbit_url,
            processor,
            exchange=AGENT_EXCHANGE,
            routing_key=ROUTING_KEY,
            queue=QUEUE,
            dead_letter_queue=DEAD_LETTER_QUEUE,
            name=EVENT_TYPE,
        )
