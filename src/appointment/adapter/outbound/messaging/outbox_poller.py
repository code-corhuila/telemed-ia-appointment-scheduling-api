import asyncio
import logging

import aio_pika
import asyncpg

logger = logging.getLogger(__name__)

OUTBOX_EXCHANGE = "appointments.events"
OUTBOX_BATCH_SIZE = 10
OUTBOX_MAX_ATTEMPTS = 5
OUTBOX_POLL_INTERVAL_SECONDS = 5
OUTBOX_RECONNECT_INITIAL_SECONDS = 5
OUTBOX_RECONNECT_MAX_SECONDS = 60

ROUTING_KEYS = {
    "AppointmentCreated": "appointment-created",
    "AppointmentRescheduled": "appointment-rescheduled",
    "AppointmentCancelled": "appointment-cancelled",
    "AppointmentCompleted": "appointment-completed",
    "AppointmentReminderDue": "appointment-reminder-due",
}


class OutboxPoller:
    """Background worker that publishes pending outbox events to RabbitMQ.

    The poller is resilient to RabbitMQ being unavailable at startup or
    during runtime:

    * ``start()`` never raises. It spawns a reconnect task with
      exponential backoff (5s -> 60s) and the polling loop.
    * ``_loop()`` skips batches while the channel is not ready, so no
      events are lost if the broker is down when the API boots.
    * ``stop()`` cancels both tasks and closes the AMQP connection
      cleanly.

    This decouples the API lifecycle from the broker: the API can start
    and serve traffic while RabbitMQ comes up, and the poller resumes
    publishing as soon as the broker is reachable.
    """

    def __init__(self, pool: asyncpg.Pool, rabbit_url: str):
        self.pool = pool
        self.rabbit_url = rabbit_url
        self.connection = None
        self.channel = None
        self.running = False
        self._reconnect_task: asyncio.Task | None = None
        self._loop_task: asyncio.Task | None = None

    async def start(self):
        self.running = True
        self._reconnect_task = asyncio.create_task(self._connect_with_retry())
        self._loop_task = asyncio.create_task(self._loop())
        logger.info(
            "OutboxPoller starting. Polling every %ss (max attempts: %s)",
            OUTBOX_POLL_INTERVAL_SECONDS,
            OUTBOX_MAX_ATTEMPTS,
        )

    async def stop(self):
        self.running = False
        for task in (self._reconnect_task, self._loop_task):
            if task is None or task.done():
                continue
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if self.connection is not None and not self.connection.is_closed:
            await self.connection.close()
        logger.info("OutboxPoller stopped.")

    async def _connect_with_retry(self):
        """Reconnect with exponential backoff until RabbitMQ is reachable."""
        backoff = OUTBOX_RECONNECT_INITIAL_SECONDS
        while self.running:
            if self.connection is not None and not self.connection.is_closed:
                return
            try:
                self.connection = await aio_pika.connect_robust(
                    self.rabbit_url, timeout=5
                )
                self.channel = await self.connection.channel()
                await self.channel.declare_exchange(
                    OUTBOX_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
                )
                logger.info("OutboxPoller connected to RabbitMQ")
                backoff = OUTBOX_RECONNECT_INITIAL_SECONDS
                return
            except Exception as e:
                logger.warning(
                    "OutboxPoller cannot reach RabbitMQ (retry in %ss): %s",
                    backoff,
                    e,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, OUTBOX_RECONNECT_MAX_SECONDS)

    async def _loop(self):
        while self.running:
            try:
                if (
                    self.channel is None
                    or self.connection is None
                    or self.connection.is_closed
                ):
                    await asyncio.sleep(OUTBOX_POLL_INTERVAL_SECONDS)
                    continue
                await self._process_batch()
            except Exception as e:
                logger.error("Error in OutboxPoller: %s", e)
            await asyncio.sleep(OUTBOX_POLL_INTERVAL_SECONDS)

    def _build_message(self, row) -> aio_pika.Message:
        """Build the AMQP message for one outbox row.

        Uses the public ``event_id`` (not the row's internal ``id``) as the
        AMQP ``MessageId`` so that consumers can deduplicate by the envelope's
        ``eventId`` without seeing a different value at the AMQP level.

        An empty ``correlation_id`` is sent as ``None`` so aio-pika does not
        emit a bogus header.
        """
        return aio_pika.Message(
            body=row["payload"].encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=str(row["event_id"]),
            type=row["event_type"],
            correlation_id=row["correlation_id"] or None,
        )

    async def _process_batch(self):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                rows = await conn.fetch(
                    """
                    SELECT id, event_id, event_type, payload,
                           COALESCE(correlation_id, '') AS correlation_id
                    FROM appointment_scheduling.outbox_event
                    WHERE status = 'PENDING'
                    ORDER BY created_at ASC
                    LIMIT $1
                    FOR UPDATE SKIP LOCKED
                    """,
                    OUTBOX_BATCH_SIZE,
                )

                if not rows:
                    return

                exchange = await self.channel.get_exchange(OUTBOX_EXCHANGE)
                published_ids: list = []
                failed: list[tuple] = []

                for row in rows:
                    routing_key = ROUTING_KEYS.get(
                        row["event_type"], row["event_type"].lower()
                    )
                    message = self._build_message(row)

                    try:
                        await exchange.publish(
                            message, routing_key=routing_key, mandatory=True
                        )
                        published_ids.append(row["id"])
                        logger.info(
                            "Published outbox event id=%s event_id=%s type=%s",
                            row["id"],
                            row["event_id"],
                            row["event_type"],
                        )
                    except Exception as e:
                        failed.append((row["id"], str(e)))
                        logger.warning(
                            "Failed to publish outbox event id=%s event_id=%s: %s",
                            row["id"],
                            row["event_id"],
                            e,
                        )

                if published_ids:
                    await conn.execute(
                        """
                        UPDATE appointment_scheduling.outbox_event
                        SET status = 'PUBLISHED',
                            published_at = now(),
                            updated_at = now(),
                            attempts = 0,
                            last_error = NULL
                        WHERE id = ANY($1)
                        """,
                        published_ids,
                    )

                if failed:
                    await self._mark_failed(conn, failed)

    async def _mark_failed(self, conn, failed: list[tuple]) -> None:
        """Mark each failed event, incrementing attempts and flipping to
        FAILED after OUTBOX_MAX_ATTEMPTS. One UPDATE per row keeps the
        per-event error message visible in ``last_error``."""
        for event_id, reason in failed:
            await conn.execute(
                """
                UPDATE appointment_scheduling.outbox_event
                SET attempts = attempts + 1,
                    last_error = $1,
                    updated_at = now(),
                    status = CASE
                        WHEN attempts + 1 >= $2 THEN 'FAILED'
                        ELSE 'PENDING'
                    END
                WHERE id = $3
                """,
                reason,
                OUTBOX_MAX_ATTEMPTS,
                event_id,
            )
