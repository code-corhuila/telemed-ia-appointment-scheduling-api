"""HTTP endpoints of the appointment-scheduling service.

Six endpoints, matching the contract exactly:
- POST  /api/appointments/
- GET   /api/appointments/patient/{id}
- GET   /api/appointments/professional/{id}
- PATCH /api/appointments/{id}/cancel
- PATCH /api/appointments/{id}/reschedule
- PATCH /api/appointments/{id}/status
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from appointment.adapter.inbound.http.auth import AuthenticatedUser, require_roles
from appointment.adapter.inbound.http.container import Container
from appointment.adapter.inbound.http.idempotency import (
    InMemoryIdempotencyStore,
    validate_idempotency_key,
)
from appointment.adapter.inbound.http.schemas import (
    CancelAppointmentRequest,
    CreateAppointmentRequest,
    RescheduleAppointmentRequest,
    UpdateStatusRequest,
)
from appointment.application.dto.commands import (
    CancelAppointmentCommand,
    CreateAppointmentCommand,
    RescheduleAppointmentCommand,
    UpdateAppointmentStatusCommand,
)
from appointment.application.dto.pagination import PaginationQuery


def _container(request: Request) -> Container:
    return request.app.state.container


def _idempotency(request: Request) -> InMemoryIdempotencyStore:
    return request.app.state.idempotency


router = APIRouter(prefix="/api/appointments", tags=["Appointments"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create(
    body: CreateAppointmentRequest,
    request: Request,
    _user: Annotated[AuthenticatedUser, Depends(require_roles("PATIENT", "PROFESSIONAL"))],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    try:
        key = validate_idempotency_key(idempotency_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    store = _idempotency(request)
    if (cached := store.get(key)) is not None:
        return cached

    response = await _container(request).create.execute(
        CreateAppointmentCommand(
            patient_id=body.patient_id,
            professional_id=body.professional_id,
            start=body.start,
            end=body.end,
        )
    )
    payload = response.model_dump(by_alias=True, mode="json")
    store.put(key, payload)
    return payload


@router.get("/patient/{patient_id}")
async def list_by_patient(
    patient_id: int,
    request: Request,
    _user: Annotated[AuthenticatedUser, Depends(require_roles("PATIENT", "PROFESSIONAL", "ADMIN"))],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    query = PaginationQuery(page=page, limit=limit)
    page_obj = await _container(request).list_patient.execute(patient_id, query)
    return page_obj.model_dump(by_alias=True, mode="json")


@router.get("/professional/{professional_id}")
async def list_by_professional(
    professional_id: int,
    request: Request,
    _user: Annotated[AuthenticatedUser, Depends(require_roles("PROFESSIONAL", "ADMIN"))],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    query = PaginationQuery(page=page, limit=limit)
    page_obj = await _container(request).list_professional.execute(professional_id, query)
    return page_obj.model_dump(by_alias=True, mode="json")


@router.patch("/{appointment_id}/cancel")
async def cancel(
    appointment_id: int,
    body: CancelAppointmentRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("PATIENT", "PROFESSIONAL", "ADMIN"))],
):
    response = await _container(request).cancel.execute(
        CancelAppointmentCommand(appointment_id=appointment_id, reason=body.reason),
        actor_id=int(user.user_id) if user.user_id.isdigit() else 0,
    )
    return response.model_dump(by_alias=True, mode="json")


@router.patch("/{appointment_id}/reschedule")
async def reschedule(
    appointment_id: int,
    body: RescheduleAppointmentRequest,
    request: Request,
    _user: Annotated[AuthenticatedUser, Depends(require_roles("PATIENT", "PROFESSIONAL", "ADMIN"))],
):
    response = await _container(request).reschedule.execute(
        RescheduleAppointmentCommand(
            appointment_id=appointment_id,
            new_start=body.start,
            new_end=body.end,
        )
    )
    return response.model_dump(by_alias=True, mode="json")


@router.patch("/{appointment_id}/status")
async def update_status(
    appointment_id: int,
    body: UpdateStatusRequest,
    request: Request,
    _user: Annotated[AuthenticatedUser, Depends(require_roles("PROFESSIONAL", "ADMIN"))],
):
    response = await _container(request).update_status.execute(
        UpdateAppointmentStatusCommand(
            appointment_id=appointment_id,
            status=body.status,
        )
    )
    return response.model_dump(by_alias=True, mode="json")
