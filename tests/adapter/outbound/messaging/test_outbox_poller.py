"""Tests for the OutboxPoller.

These tests pin the two invariants that were broken before the hardening PR:
1. The AMQP ``MessageId`` is the public ``event_id``, not the row's
   internal ``id``.
2. A failed publish increments ``attempts`` and flips to ``FAILED`` after
   ``OUTBOX_MAX_ATTEMPTS``.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from appointment.adapter.outbound.messaging.outbox_poller import (
    OUTBOX_MAX_ATTEMPTS,
    OutboxPoller,
)


def _row(event_id: str = "public-event-id", internal_id: str = "internal-id",
         correlation_id: str = "corr-123") -> dict:
    return {
        "id": internal_id,
        "event_id": event_id,
        "event_type": "AppointmentCreated",
        "payload": '{"x": 1}',
        "correlation_id": correlation_id,
    }


def test_build_message_uses_event_id_not_internal_id():
    """The AMQP MessageId must be the public event_id, not the row's id."""
    poller = OutboxPoller(None, "amqp://test")
    row = _row(event_id="public-evt-1", internal_id="internal-pk-1")

    msg = poller._build_message(row)

    assert msg.message_id == "public-evt-1"
    assert msg.message_id != row["id"]
    assert msg.correlation_id == "corr-123"
    assert msg.type == "AppointmentCreated"
    assert msg.content_type == "application/json"


def test_build_message_with_empty_correlation_id_sends_none():
    """An empty correlation_id must be sent as None, not '', to avoid a
    bogus AMQP header."""
    poller = OutboxPoller(None, "amqp://test")
    row = _row(correlation_id="")

    msg = poller._build_message(row)

    assert msg.correlation_id is None


@pytest.mark.asyncio
async def test_mark_failed_increments_attempts_and_flips_to_failed():
    """_mark_failed must UPDATE attempts, last_error and status."""
    poller = OutboxPoller(None, "amqp://test")
    conn = AsyncMock()

    await poller._mark_failed(conn, [("id-1", "boom")])

    conn.execute.assert_awaited_once()
    call = conn.execute.await_args
    sql, *params = call.args

    assert "attempts = attempts + 1" in sql
    assert "last_error = $1" in sql
    assert "FAILED" in sql
    assert "PENDING" in sql
    assert params[0] == "boom"
    assert params[1] == OUTBOX_MAX_ATTEMPTS
    assert params[2] == "id-1"


@pytest.mark.asyncio
async def test_process_batch_marks_published_and_failed():
    """One row publishes OK, another fails; both must be updated."""
    poller = OutboxPoller(None, "amqp://test")

    row_ok = _row(event_id="evt-ok", internal_id="id-ok")
    row_fail = _row(event_id="evt-fail", internal_id="id-fail")

    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[row_ok, row_fail])
    conn.execute = AsyncMock()

    tx = MagicMock()
    tx.__aenter__ = AsyncMock(return_value=None)
    tx.__aexit__ = AsyncMock(return_value=None)
    conn.transaction = MagicMock(return_value=tx)

    acquire = MagicMock()
    acquire.__aenter__ = AsyncMock(return_value=conn)
    acquire.__aexit__ = AsyncMock(return_value=None)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=acquire)

    exchange = AsyncMock()
    exchange.publish = AsyncMock(side_effect=[None, Exception("no queue")])

    channel = AsyncMock()
    channel.get_exchange = AsyncMock(return_value=exchange)

    poller.pool = pool
    poller.channel = channel

    await poller._process_batch()

    # At least: PUBLISHED update + one FAILED update
    all_sql = [c.args[0] for c in conn.execute.await_args_list if c.args]
    assert any("status = 'PUBLISHED'" in s for s in all_sql)
    assert any("attempts = attempts + 1" in s for s in all_sql)

    # The published update targets only the OK row
    published_call = next(c for c in conn.execute.await_args_list
                          if c.args and "status = 'PUBLISHED'" in c.args[0])
    assert published_call.args[1] == ["id-ok"]

    # The failed update targets only the failing row
    failed_call = next(c for c in conn.execute.await_args_list
                       if c.args and "attempts = attempts + 1" in c.args[0])
    assert failed_call.args[1] == "no queue"
    assert failed_call.args[3] == "id-fail"
