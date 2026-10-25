import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

import aio_pika
import asyncpg
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class OutboxPoller:
    def __init__(self, pool: asyncpg.Pool, rabbit_url: str):
        self.pool = pool
        self.rabbit_url = rabbit_url
        self.connection = None
        self.channel = None
        self.running = False

    async def start(self):
        self.running = True
        # Conexión inicial a RabbitMQ
        self.connection = await aio_pika.connect_robust(self.rabbit_url)
        self.channel = await self.connection.channel()
        # Declarar el Topic Exchange
        await self.channel.declare_exchange("appointments.events", aio_pika.ExchangeType.TOPIC, durable=True)
        
        logger.info("OutboxPoller started. Polling every 5 seconds...")
        asyncio.create_task(self._loop())

    async def stop(self):
        self.running = False
        if self.connection:
            await self.connection.close()

    async def _loop(self):
        while self.running:
            try:
                await self._process_batch()
            except Exception as e:
                logger.error(f"Error in OutboxPoller: {e}")
            await asyncio.sleep(5)

    async def _process_batch(self):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Seleccionar eventos pendientes (SKIP LOCKED evita colisiones)
                rows = await conn.fetch("""
                    SELECT id, event_type, payload, correlation_id
                    FROM appointment_scheduling.outbox_event
                    WHERE status = 'PENDING'
                    ORDER BY created_at ASC
                    LIMIT 10
                    FOR UPDATE SKIP LOCKED
                """)
                
                if not rows:
                    return

                exchange = await self.channel.get_exchange("appointments.events")
                published_ids = []

                for row in rows:
                    # El event_type en la DB está en PascalCase (ej: AppointmentCreated)
                    # La routing key debe ser kebab-case (ej: appointment-created)
                    routing_key = row["event_type"]
                    if routing_key == "AppointmentCreated": routing_key = "appointment-created"
                    elif routing_key == "AppointmentRescheduled": routing_key = "appointment-rescheduled"
                    elif routing_key == "AppointmentCancelled": routing_key = "appointment-cancelled"
                    
                    message = aio_pika.Message(
                        body=row["payload"].encode(),
                        content_type="application/json",
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        message_id=str(row["id"]),
                        type=row["event_type"],
                        correlation_id=row["correlation_id"]
                    )
                    
                    try:
                        # mandatory=True para que rebote si no hay cola
                        await exchange.publish(message, routing_key=routing_key, mandatory=True)
                        published_ids.append(row["id"])
                        logger.info(f"Published outbox event {row['id']} ({row['event_type']})")
                    except Exception as e:
                        logger.warning(f"Failed to publish {row['id']} (no queue?): {e}")

                if published_ids:
                    await conn.execute("""
                        UPDATE appointment_scheduling.outbox_event
                        SET status = 'PUBLISHED', published_at = now()
                        WHERE id = ANY($1)
                    """, published_ids)
