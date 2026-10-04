"""Domain events published by the appointment-scheduling service.

Per ADR-011 the message broker (RabbitMQ) is still `Proposed`. Until the
ADR is accepted, the infrastructure provides a no-op publisher that logs
the events. This module defines the contract the application relies on.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AppointmentCreated:
    appointment_id: int
    patient_id: int
    professional_id: int
    start: datetime
    occurred_at: datetime

    @property
    def name(self) -> str:
        return "AppointmentCreated"


@dataclass(frozen=True, slots=True)
class AppointmentRescheduled:
    appointment_id: int
    patient_id: int
    professional_id: int
    previous_start: datetime
    new_start: datetime
    occurred_at: datetime

    @property
    def name(self) -> str:
        return "AppointmentRescheduled"


@dataclass(frozen=True, slots=True)
class AppointmentCancelled:
    appointment_id: int
    patient_id: int
    professional_id: int
    cancelled_by: str
    occurred_at: datetime

    @property
    def name(self) -> str:
        return "AppointmentCancelled"


@dataclass(frozen=True, slots=True)
class AppointmentCompleted:
    appointment_id: int
    patient_id: int
    professional_id: int
    occurred_at: datetime

    @property
    def name(self) -> str:
        return "AppointmentCompleted"
