"""DEC-009: how the PreConsultationSummaryGenerated consumer treats each message."""
import json
import logging
from uuid import uuid4

import pytest

from appointment.adapter.inbound.messaging.preconsultation_summary_consumer import (
    AGENT_EXCHANGE,
    DEAD_LETTER_QUEUE,
    QUEUE,
    ROUTING_KEY,
    Decision,
    MalformedMessage,
    PreConsultationSummaryProcessor,
    parse_pre_consultation_summary_generated,
    queue_arguments,
)
from appointment.application.usecase.link_preconsultation_summary import (
    LinkOutcome,
    PreconsultationPatientMismatch,
)
from appointment.domain.exception import AppointmentNotFound

APPOINTMENT_ID = str(uuid4())
SUMMARY_ID = str(uuid4())
PATIENT_ID = str(uuid4())


def _payload(**overrides) -> dict:
    payload = {
        "summaryId": SUMMARY_ID,
        "appointmentId": APPOINTMENT_ID,
        "patientId": PATIENT_ID,
        "conversationId": str(uuid4()),
        "generatedAt": "2026-11-11T18:55:00Z",
    }
    payload.update(overrides)
    return payload


def _body(payload=None, **overrides) -> bytes:
    envelope = {
        "eventId": str(uuid4()),
        "eventType": "PreConsultationSummaryGenerated",
        "occurredAt": "2026-11-11T18:55:01Z",
        "correlationId": "corr-1",
        "version": 1,
        "payload": _payload() if payload is None else payload,
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


def test_binds_its_own_queue_to_the_agent_exchange() -> None:
    assert AGENT_EXCHANGE == "agent.events"
    assert ROUTING_KEY == "pre-consultation-summary-generated"
    assert QUEUE == "appointment.pre-consultation-summary-generated"
    assert queue_arguments() == {
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": DEAD_LETTER_QUEUE,
    }


def test_parses_the_summary_envelope() -> None:
    cmd = parse_pre_consultation_summary_generated(_body())

    assert str(cmd.appointment_id) == APPOINTMENT_ID
    assert str(cmd.summary_id) == SUMMARY_ID
    assert str(cmd.patient_id) == PATIENT_ID
    assert cmd.correlation_id == "corr-1"


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"[]",
        _body(eventType="ConsultationCompleted"),
        _body(payload="nope"),
        _body(payload=_payload(summaryId=None)),
        _body(payload={k: v for k, v in _payload().items() if k != "appointmentId"}),
        _body(payload=_payload(patientId="not-a-uuid")),
    ],
)
def test_rejects_a_malformed_summary_message(body: bytes) -> None:
    with pytest.raises(MalformedMessage):
        parse_pre_consultation_summary_generated(body)


@pytest.mark.parametrize(
    "outcome", [LinkOutcome.LINKED, LinkOutcome.ALREADY_LINKED, LinkOutcome.KEPT_EXISTING]
)
async def test_acknowledges_every_link_outcome(outcome) -> None:
    use_case = FakeUseCase(outcome)

    decision = await PreConsultationSummaryProcessor(use_case, RecordingSleep()).process(_body())

    assert decision is Decision.ACK
    assert str(use_case.commands[0].summary_id) == SUMMARY_ID


async def test_logs_a_warning_when_another_summary_is_kept(caplog) -> None:
    caplog.set_level(logging.WARNING)

    processor = PreConsultationSummaryProcessor(
        FakeUseCase(LinkOutcome.KEPT_EXISTING), RecordingSleep()
    )
    await processor.process(_body())

    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any(APPOINTMENT_ID in m and "corr-1" in m for m in messages)


async def test_dead_letters_a_malformed_summary_without_calling_the_use_case() -> None:
    use_case = FakeUseCase(LinkOutcome.LINKED)
    sleep = RecordingSleep()

    decision = await PreConsultationSummaryProcessor(use_case, sleep).process(b"not json")

    assert decision is Decision.DEAD_LETTER
    assert use_case.commands == []
    assert sleep.delays == []


@pytest.mark.parametrize(
    "error", [AppointmentNotFound("missing"), PreconsultationPatientMismatch("other patient")]
)
async def test_dead_letters_a_summary_without_retrying(error) -> None:
    use_case = FakeUseCase(error)
    sleep = RecordingSleep()

    decision = await PreConsultationSummaryProcessor(use_case, sleep).process(_body())

    assert decision is Decision.DEAD_LETTER
    assert len(use_case.commands) == 1
    assert sleep.delays == []


async def test_retries_a_transient_link_failure_with_backoff() -> None:
    use_case = FakeUseCase(RuntimeError("db down"), RuntimeError("db down"), LinkOutcome.LINKED)
    sleep = RecordingSleep()

    decision = await PreConsultationSummaryProcessor(use_case, sleep).process(_body())

    assert decision is Decision.ACK
    assert len(use_case.commands) == 3
    assert sleep.delays == [3, 6]


async def test_dead_letters_a_summary_after_three_failed_attempts() -> None:
    use_case = FakeUseCase(RuntimeError("db down"))
    sleep = RecordingSleep()

    decision = await PreConsultationSummaryProcessor(use_case, sleep).process(_body())

    assert decision is Decision.DEAD_LETTER
    assert len(use_case.commands) == 3
    assert sleep.delays == [3, 6]
