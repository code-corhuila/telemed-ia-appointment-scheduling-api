"""DEC-007: how the ConsultationCompleted consumer treats each message."""
import json
import logging
from uuid import uuid4

import pytest

from appointment.adapter.inbound.messaging.consultation_completed_consumer import (
    DEAD_LETTER_QUEUE,
    ConsultationCompletedProcessor,
    Decision,
    MalformedMessage,
    parse_consultation_completed,
    queue_arguments,
)
from appointment.application.usecase.complete_from_consultation import CompletionOutcome
from appointment.domain.exception import AppointmentNotFound

APPOINTMENT_ID = str(uuid4())
CONSULTATION_ID = str(uuid4())


def _body(**overrides) -> bytes:
    payload = {
        "consultationId": CONSULTATION_ID,
        "appointmentId": APPOINTMENT_ID,
        "patientId": str(uuid4()),
        "professionalId": str(uuid4()),
        "completedAt": "2026-11-11T15:04:05Z",
    }
    envelope = {
        "eventId": str(uuid4()),
        "eventType": "ConsultationCompleted",
        "occurredAt": "2026-11-11T15:04:06Z",
        "correlationId": "corr-1",
        "version": 1,
        "payload": payload,
    }
    envelope.update(overrides)
    return json.dumps(envelope).encode()


class FakeUseCase:
    def __init__(self, *results) -> None:
        self.results = list(results)
        self.commands = []

    async def execute(self, cmd):
        self.commands.append(cmd)
        result = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        if isinstance(result, Exception):
            raise result
        return result


class RecordingSleep:
    def __init__(self) -> None:
        self.delays = []

    async def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


def test_parses_the_post_summary_id() -> None:
    post_summary_id = str(uuid4())
    payload = json.loads(_body())["payload"] | {"postSummaryId": post_summary_id}

    cmd = parse_consultation_completed(_body(payload=payload))

    assert str(cmd.post_summary_id) == post_summary_id


def test_an_event_without_post_summary_id_still_parses() -> None:
    assert parse_consultation_completed(_body()).post_summary_id is None


def test_rejects_a_post_summary_id_that_is_not_a_uuid() -> None:
    payload = json.loads(_body())["payload"] | {"postSummaryId": "not-a-uuid"}

    with pytest.raises(MalformedMessage):
        parse_consultation_completed(_body(payload=payload))


def test_the_queue_dead_letters_to_its_own_dlq() -> None:
    assert queue_arguments() == {
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": DEAD_LETTER_QUEUE,
    }
    assert DEAD_LETTER_QUEUE == "appointment.consultation-completed.dlq"


def test_parses_the_envelope() -> None:
    cmd = parse_consultation_completed(_body())

    assert str(cmd.appointment_id) == APPOINTMENT_ID
    assert str(cmd.consultation_id) == CONSULTATION_ID
    assert cmd.correlation_id == "corr-1"


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"[]",
        _body(eventType="PostConsultationSummaryGenerated"),
        _body(payload={"consultationId": CONSULTATION_ID}),
        _body(payload={"consultationId": CONSULTATION_ID, "appointmentId": "nope"}),
        _body(payload="text"),
    ],
)
def test_rejects_a_malformed_message(body: bytes) -> None:
    with pytest.raises(MalformedMessage):
        parse_consultation_completed(body)


@pytest.mark.parametrize(
    "outcome",
    [CompletionOutcome.COMPLETED, CompletionOutcome.ALREADY_COMPLETED, CompletionOutcome.IGNORED],
)
async def test_acknowledges_every_outcome(outcome) -> None:
    use_case = FakeUseCase(outcome)

    decision = await ConsultationCompletedProcessor(use_case, RecordingSleep()).process(_body())

    assert decision is Decision.ACK
    assert str(use_case.commands[0].appointment_id) == APPOINTMENT_ID


async def test_logs_a_warning_when_the_appointment_is_left_unchanged(caplog) -> None:
    caplog.set_level(logging.WARNING)

    use_case = FakeUseCase(CompletionOutcome.IGNORED)
    processor = ConsultationCompletedProcessor(use_case, RecordingSleep())
    await processor.process(_body())

    messages = [r.getMessage() for r in caplog.records]
    assert any(APPOINTMENT_ID in m and "corr-1" in m for m in messages)


async def test_dead_letters_a_malformed_message_without_calling_the_use_case() -> None:
    use_case = FakeUseCase(CompletionOutcome.COMPLETED)
    sleep = RecordingSleep()

    decision = await ConsultationCompletedProcessor(use_case, sleep).process(b"not json")

    assert decision is Decision.DEAD_LETTER
    assert use_case.commands == []
    assert sleep.delays == []


async def test_dead_letters_an_unknown_appointment_without_retrying() -> None:
    use_case = FakeUseCase(AppointmentNotFound("missing"))
    sleep = RecordingSleep()

    decision = await ConsultationCompletedProcessor(use_case, sleep).process(_body())

    assert decision is Decision.DEAD_LETTER
    assert len(use_case.commands) == 1
    assert sleep.delays == []


async def test_retries_a_transient_failure_with_backoff() -> None:
    use_case = FakeUseCase(
        RuntimeError("db down"), RuntimeError("db down"), CompletionOutcome.COMPLETED
    )
    sleep = RecordingSleep()

    decision = await ConsultationCompletedProcessor(use_case, sleep).process(_body())

    assert decision is Decision.ACK
    assert len(use_case.commands) == 3
    assert sleep.delays == [3, 6]


async def test_dead_letters_after_three_failed_attempts() -> None:
    use_case = FakeUseCase(RuntimeError("db down"))
    sleep = RecordingSleep()

    decision = await ConsultationCompletedProcessor(use_case, sleep).process(_body())

    assert decision is Decision.DEAD_LETTER
    assert len(use_case.commands) == 3
    assert sleep.delays == [3, 6]
