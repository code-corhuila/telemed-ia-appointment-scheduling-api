"""Consumer of ConsultationCompleted (consultation DEC-003, appointment DEC-007).

Queue ``appointment.consultation-completed`` is bound to ``consultation.events`` with the
routing key ``consultation-completed``; a dead-lettered message goes to
``appointment.consultation-completed.dlq``. The consumer reads identifiers only; the optional
``postSummaryId`` is stored on the appointment (appointment DEC-008).
"""
import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from enum import StrEnum

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

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
RECONNECT_INITIAL_SECONDS = 5
RECONNECT_MAX_SECONDS = 60


class MalformedMessage(ValueError):
    """The message is not a ConsultationCompleted envelope."""


class Decision(StrEnum):
    ACK = "ACK"
    DEAD_LETTER = "DEAD_LETTER"


def queue_arguments() -> dict:
    """Rejected messages go, through the default exchange, to the DLQ."""
    return {
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": DEAD_LETTER_QUEUE,
    }


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


class ConsultationCompletedConsumer:
    """AMQP wiring. Like the OutboxPoller, it never blocks the API start: it connects in the
    background with exponential backoff, and aio-pika's robust connection restores the
    consumer after a broker restart."""

    def __init__(self, rabbit_url: str, processor: ConsultationCompletedProcessor) -> None:
        self._rabbit_url = rabbit_url
        self._processor = processor
        self._connection = None
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._connect_with_retry())

    async def stop(self) -> None:
        self._running = False
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()

    async def _connect_with_retry(self) -> None:
        backoff = RECONNECT_INITIAL_SECONDS
        while self._running:
            try:
                self._connection = await aio_pika.connect_robust(self._rabbit_url, timeout=5)
                channel = await self._connection.channel()
                await channel.set_qos(prefetch_count=1)
                exchange = await channel.declare_exchange(
                    CONSULTATION_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
                )
                await channel.declare_queue(DEAD_LETTER_QUEUE, durable=True)
                queue = await channel.declare_queue(
                    QUEUE, durable=True, arguments=queue_arguments()
                )
                await queue.bind(exchange, routing_key=ROUTING_KEY)
                await queue.consume(self._on_message)
                logger.info("ConsultationCompleted consumer listening on %s", QUEUE)
                return
            except Exception as e:
                if self._connection is not None and not self._connection.is_closed:
                    await self._connection.close()
                logger.warning(
                    "ConsultationCompleted consumer cannot reach RabbitMQ (retry in %ss): %s",
                    backoff, e,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, RECONNECT_MAX_SECONDS)

    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        decision = await self._processor.process(message.body)
        if decision is Decision.ACK:
            await message.ack()
        else:
            await message.reject(requeue=False)
