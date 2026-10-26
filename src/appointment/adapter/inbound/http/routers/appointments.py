"""HTTP endpoints of the appointment-scheduling service."""

from typing import Annotated
from uuid import UUID

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
from appointment.application.dto.responses import AppointmentResponse


def _container(request: Request) -> Container:
    return request.app.state.container


def _idempotency(request: Request) -> InMemoryIdempotencyStore:
    return request.app.state.idempotency


def _user_uuid(user: AuthenticatedUser) -> UUID:
    try:
        return UUID(user.user_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid subject claim",
        )


def _check_appointment_access(
    user: AuthenticatedUser,
    appointment: AppointmentResponse,
) -> None:
    if user.role == "ADMIN":
        return
    uid = _user_uuid(user)
    if user.role == "PATIENT" and appointment.patient_id != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient permissions",
        )
    if user.role == "PROFESSIONAL" and appointment.professional_id != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient permissions",
        )


router = APIRouter(prefix="/api/appointments", tags=["Appointments"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create(
    body: CreateAppointmentRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("PATIENT", "PROFESSIONAL"))],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    try:
        key = validate_idempotency_key(idempotency_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if user.role == "PATIENT":
        if _user_uuid(user) != body.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="cannot create an appointment for another patient",
            )

    store = _idempotency(request)
    if (cached := store.get(key)) is not None:
        return cached

    response = await _container(request).create.execute(
        CreateAppointmentCommand(
            patient_id=body.patient_id,
            professional_id=body.professional_id,
            start=body.start,
        )
    )
    payload = response.model_dump(by_alias=True, mode="json")
    store.put(key, payload)
    return payload


@router.get("/patient/{patient_id}")
async def list_by_patient(
    patient_id: UUID,
    request: Request,
    user: Annotated[
        AuthenticatedUser,
        Depends(require_roles("PATIENT", "PROFESSIONAL", "ADMIN")),
    ],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    if user.role == "PATIENT" and _user_uuid(user) != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient permissions",
        )
    query = PaginationQuery(page=page, limit=limit)
    page_obj = await _container(request).list_patient.execute(patient_id, query)
    return page_obj.model_dump(by_alias=True, mode="json")


@router.get("/professional/{professional_id}")
async def list_by_professional(
    professional_id: UUID,
    request: Request,
    user: Annotated[
        AuthenticatedUser,
        Depends(require_roles("PROFESSIONAL", "ADMIN")),
    ],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    if user.role == "PROFESSIONAL" and _user_uuid(user) != professional_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="insufficient permissions",
        )
    query = PaginationQuery(page=page, limit=limit)
    page_obj = await _container(request).list_professional.execute(professional_id, query)
    return page_obj.model_dump(by_alias=True, mode="json")


@router.get("/{appointment_id}")
async def get_by_id(
    appointment_id: UUID,
    request: Request,
    user: Annotated[
        AuthenticatedUser,
        Depends(require_roles("PATIENT", "PROFESSIONAL", "ADMIN")),
    ],
):
    appointment = await _container(request).get_by_id.execute(appointment_id)
    _check_appointment_access(user, appointment)
    return appointment.model_dump(by_alias=True, mode="json")


@router.patch("/{appointment_id}/cancel")
async def cancel(
    appointment_id: UUID,
    body: CancelAppointmentRequest,
    request: Request,
    user: Annotated[
        AuthenticatedUser,
        Depends(require_roles("PATIENT", "PROFESSIONAL", "ADMIN")),
    ],
):
    container = _container(request)
    appointment = await container.get_by_id.execute(appointment_id)
    _check_appointment_access(user, appointment)
    response = await container.cancel.execute(
        CancelAppointmentCommand(appointment_id=appointment_id, reason=body.reason),
        actor_id=_user_uuid(user),
    )
    return response.model_dump(by_alias=True, mode="json")


@router.patch("/{appointment_id}/reschedule")
async def reschedule(
    appointment_id: UUID,
    body: RescheduleAppointmentRequest,
    request: Request,
    user: Annotated[
        AuthenticatedUser,
        Depends(require_roles("PATIENT", "PROFESSIONAL", "ADMIN")),
    ],
):
    container = _container(request)
    appointment = await container.get_by_id.execute(appointment_id)
    _check_appointment_access(user, appointment)
    response = await container.reschedule.execute(
        RescheduleAppointmentCommand(
            appointment_id=appointment_id,
            new_start=body.start,
        )
    )
    return response.model_dump(by_alias=True, mode="json")


@router.patch("/{appointment_id}/status")
async def update_status(
    appointment_id: UUID,
    body: UpdateStatusRequest,
    request: Request,
    user: Annotated[
        AuthenticatedUser,
        Depends(require_roles("PROFESSIONAL", "ADMIN")),
    ],
):
    container = _container(request)
    appointment = await container.get_by_id.execute(appointment_id)
    _check_appointment_access(user, appointment)
    response = await container.update_status.execute(
        UpdateAppointmentStatusCommand(
            appointment_id=appointment_id,
            status=body.status,
        )
    )
    return response.model_dump(by_alias=True, mode="json")
