"""AMQP wiring shared by the event consumers (DEC-007, DEC-009).

Each consumer declares its own durable queue, bound to a topic exchange, with its own DLQ. Like
the OutboxPoller, it never blocks the API start: it connects in the background with exponential
backoff, and aio-pika's robust connection restores the consumer after a broker restart.
"""
import asyncio
import logging
from enum import StrEnum
from typing import Protocol

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

logger = logging.getLogger(__name__)

RECONNECT_INITIAL_SECONDS = 5
RECONNECT_MAX_SECONDS = 60


class MalformedMessage(ValueError):
    """The message is not the envelope the consumer expects."""


class Decision(StrEnum):
    ACK = "ACK"
    DEAD_LETTER = "DEAD_LETTER"


class MessageProcessor(Protocol):
    async def process(self, body: bytes) -> Decision: ...


def dead_letter_arguments(dead_letter_queue: str) -> dict:
    """Rejected messages go, through the default exchange, to the DLQ."""
    return {
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": dead_letter_queue,
    }


class TopicQueueConsumer:
    def __init__(
        self,
        rabbit_url: str,
        processor: MessageProcessor,
        *,
        exchange: str,
        routing_key: str,
        queue: str,
        dead_letter_queue: str,
        name: str,
    ) -> None:
        self._rabbit_url = rabbit_url
        self._processor = processor
        self._exchange = exchange
        self._routing_key = routing_key
        self._queue = queue
        self._dead_letter_queue = dead_letter_queue
        self._name = name
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
                    self._exchange, aio_pika.ExchangeType.TOPIC, durable=True
                )
                await channel.declare_queue(self._dead_letter_queue, durable=True)
                queue = await channel.declare_queue(
                    self._queue,
                    durable=True,
                    arguments=dead_letter_arguments(self._dead_letter_queue),
                )
                await queue.bind(exchange, routing_key=self._routing_key)
                await queue.consume(self._on_message)
                logger.info("%s consumer listening on %s", self._name, self._queue)
                return
            except Exception as e:
                if self._connection is not None and not self._connection.is_closed:
                    await self._connection.close()
                logger.warning(
                    "%s consumer cannot reach RabbitMQ (retry in %ss): %s",
                    self._name, backoff, e,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, RECONNECT_MAX_SECONDS)

    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        decision = await self._processor.process(message.body)
        if decision is Decision.ACK:
            await message.ack()
        else:
            await message.reject(requeue=False)
