"""Domain events published by the appointment-scheduling service.

Per ADR-011 the message broker (RabbitMQ) is still `Proposed`. Until the
ADR is accepted, the infrastructure provides a no-op publisher that logs
the events. This module defines the contract the application relies on.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AppointmentCreated:
    appointment_id: UUID
    patient_id: UUID
    professional_id: UUID
    occurred_at: datetime


@dataclass(frozen=True)
class AppointmentCancelled:
    appointment_id: UUID
    patient_id: UUID
    professional_id: UUID
    cancelled_by: UUID
    occurred_at: datetime


@dataclass(frozen=True)
class AppointmentRescheduled:
    appointment_id: UUID
    patient_id: UUID
    professional_id: UUID
    previous_start: datetime
    new_start: datetime
    occurred_at: datetime


@dataclass(frozen=True)
class AppointmentCompleted:
    appointment_id: UUID
    patient_id: UUID
    professional_id: UUID
    occurred_at: datetime


@dataclass(frozen=True)
class AppointmentStatusChanged:
    appointment_id: UUID
    patient_id: UUID
    professional_id: UUID
    new_status: str
    occurred_at: datetime
