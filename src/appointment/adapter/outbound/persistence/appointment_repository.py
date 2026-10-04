"""asyncpg implementation of AppointmentRepository (Anexo C layout)."""

from datetime import datetime

import asyncpg

from appointment.adapter.outbound.persistence.mappers import row_to_appointment
from appointment.config.database import validate_schema_name
from appointment.domain.model.appointment import Appointment
from appointment.domain.model.appointment_status import AppointmentStatus

_ACTIVE_STATUSES = (AppointmentStatus.CONFIRMED.value, AppointmentStatus.RESCHEDULED.value)


class PostgresAppointmentRepository:
    def __init__(self, pool: asyncpg.Pool, schema: str) -> None:
        self._pool = pool
        self._schema = validate_schema_name(schema)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def save(self, appointment: Appointment) -> Appointment:
        sql = f"""
            INSERT INTO {self._schema}.appointments
                (patient_id, professional_id, preconsultation_summary_id,
                 post_summary_id, start_time, end_time, status,
                 cancellation_reason, created_at, updated_at, deleted_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id, patient_id, professional_id, preconsultation_summary_id,
                      post_summary_id, start_time, end_time, status,
                      cancellation_reason, created_at, updated_at, deleted_at
        """
        row = await self._pool.fetchrow(
            sql,
            appointment.patient_id,
            appointment.professional_id,
            appointment.preconsultation_summary_id,
            appointment.post_summary_id,
            appointment.start,
            appointment.end,
            appointment.status.value,
            appointment.cancellation_reason,
            appointment.created_at,
            appointment.updated_at,
            appointment.deleted_at,
        )
        return row_to_appointment(row)

    async def update(self, appointment: Appointment) -> Appointment:
        if appointment.id is None:
            raise ValueError("cannot update an appointment without id")
        sql = f"""
            UPDATE {self._schema}.appointments
            SET patient_id = $2,
                professional_id = $3,
                preconsultation_summary_id = $4,
                post_summary_id = $5,
                start_time = $6,
                end_time = $7,
                status = $8,
                cancellation_reason = $9,
                updated_at = $10,
                deleted_at = $11
            WHERE id = $1
            RETURNING id, patient_id, professional_id, preconsultation_summary_id,
                      post_summary_id, start_time, end_time, status,
                      cancellation_reason, created_at, updated_at, deleted_at
        """
        row = await self._pool.fetchrow(
            sql,
            appointment.id,
            appointment.patient_id,
            appointment.professional_id,
            appointment.preconsultation_summary_id,
            appointment.post_summary_id,
            appointment.start,
            appointment.end,
            appointment.status.value,
            appointment.cancellation_reason,
            appointment.updated_at,
            appointment.deleted_at,
        )
        if row is None:
            raise ValueError(f"appointment {appointment.id} not found")
        return row_to_appointment(row)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def find_by_id(self, appointment_id: int) -> Appointment | None:
        sql = f"""
            SELECT id, patient_id, professional_id, preconsultation_summary_id,
                   post_summary_id, start_time, end_time, status,
                   cancellation_reason, created_at, updated_at, deleted_at
            FROM {self._schema}.appointments
            WHERE id = $1 AND deleted_at IS NULL
        """
        row = await self._pool.fetchrow(sql, appointment_id)
        return row_to_appointment(row) if row else None

    async def find_by_patient(
        self, patient_id: int, *, offset: int, limit: int
    ) -> tuple[list[Appointment], int]:
        sql = f"""
            SELECT id, patient_id, professional_id, preconsultation_summary_id,
                   post_summary_id, start_time, end_time, status,
                   cancellation_reason, created_at, updated_at, deleted_at
            FROM {self._schema}.appointments
            WHERE patient_id = $1 AND deleted_at IS NULL
            ORDER BY start_time DESC
            LIMIT $2 OFFSET $3
        """
        count_sql = f"""
            SELECT COUNT(*) FROM {self._schema}.appointments
            WHERE patient_id = $1 AND deleted_at IS NULL
        """
        rows = await self._pool.fetch(sql, patient_id, limit, offset)
        total = await self._pool.fetchval(count_sql, patient_id)
        return [row_to_appointment(r) for r in rows], int(total or 0)

    async def find_by_professional(
        self, professional_id: int, *, offset: int, limit: int
    ) -> tuple[list[Appointment], int]:
        sql = f"""
            SELECT id, patient_id, professional_id, preconsultation_summary_id,
                   post_summary_id, start_time, end_time, status,
                   cancellation_reason, created_at, updated_at, deleted_at
            FROM {self._schema}.appointments
            WHERE professional_id = $1 AND deleted_at IS NULL
            ORDER BY start_time DESC
            LIMIT $2 OFFSET $3
        """
        count_sql = f"""
            SELECT COUNT(*) FROM {self._schema}.appointments
            WHERE professional_id = $1 AND deleted_at IS NULL
        """
        rows = await self._pool.fetch(sql, professional_id, limit, offset)
        total = await self._pool.fetchval(count_sql, professional_id)
        return [row_to_appointment(r) for r in rows], int(total or 0)

    async def find_active_overlapping(
        self,
        professional_id: int,
        start: datetime,
        end: datetime,
    ) -> list[Appointment]:
        sql = f"""
            SELECT id, patient_id, professional_id, preconsultation_summary_id,
                   post_summary_id, start_time, end_time, status,
                   cancellation_reason, created_at, updated_at, deleted_at
            FROM {self._schema}.appointments
            WHERE professional_id = $1
              AND status = ANY($2::text[])
              AND start_time < $4
              AND $3 < end_time
              AND deleted_at IS NULL
        """
        rows = await self._pool.fetch(
            sql, professional_id, list(_ACTIVE_STATUSES), start, end
        )
        return [row_to_appointment(r) for r in rows]