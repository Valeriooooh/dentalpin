"""HTTP surface for patient_segments.

Mounted under ``/api/v1/patient_segments/*`` (module name literal, per the
lab_orders lesson). Patient-scoped reads live under the segment id —
membership rows always carry their own ``clinic_id`` so no lookup is ever
id-only (L1).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import ClinicContext, get_clinic_context, require_permission
from app.core.schemas import ApiResponse
from app.database import get_db
from app.modules.patients.service import PatientService

from .schemas import (
    SegmentAssign,
    SegmentCreate,
    SegmentMemberResponse,
    SegmentResponse,
    SegmentUpdate,
)
from .service import PatientSegmentsService

router = APIRouter()


async def _ensure_segment(db: AsyncSession, clinic_id: UUID, segment_id: UUID):
    row = await PatientSegmentsService.get_segment(db, clinic_id, segment_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    return row


def _to_response(row, member_count: int = 0) -> SegmentResponse:
    return SegmentResponse(
        id=row.id,
        name=row.name,
        color=row.color,
        description=row.description,
        member_count=member_count,
        created_at=row.created_at,
    )


# --- Segments ------------------------------------------------------------


@router.get("/segments", response_model=ApiResponse[list[SegmentResponse]])
async def list_segments(
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("patient_segments.read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[SegmentResponse]]:
    rows = await PatientSegmentsService.list_segments(db, ctx.clinic_id)
    return ApiResponse(data=[_to_response(row, count) for row, count in rows])


@router.post(
    "/segments",
    response_model=ApiResponse[SegmentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_segment(
    data: SegmentCreate,
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("patient_segments.write"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SegmentResponse]:
    row = await PatientSegmentsService.create_segment(db, ctx.clinic_id, data.model_dump())
    await db.commit()
    await db.refresh(row)
    return ApiResponse(data=_to_response(row))


@router.patch("/segments/{segment_id}", response_model=ApiResponse[SegmentResponse])
async def update_segment(
    segment_id: UUID,
    data: SegmentUpdate,
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("patient_segments.write"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SegmentResponse]:
    row = await _ensure_segment(db, ctx.clinic_id, segment_id)
    row = await PatientSegmentsService.update_segment(db, row, data.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(row)
    return ApiResponse(data=_to_response(row))


@router.delete("/segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_segment(
    segment_id: UUID,
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("patient_segments.write"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    row = await _ensure_segment(db, ctx.clinic_id, segment_id)
    await PatientSegmentsService.delete_segment(db, row)
    await db.commit()


@router.get(
    "/segments/{segment_id}/patients",
    response_model=ApiResponse[list[SegmentMemberResponse]],
)
async def list_segment_members(
    segment_id: UUID,
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("patient_segments.read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[SegmentMemberResponse]]:
    await _ensure_segment(db, ctx.clinic_id, segment_id)
    rows = await PatientSegmentsService.list_members(db, ctx.clinic_id, segment_id)
    return ApiResponse(
        data=[SegmentMemberResponse(patient_id=pid, full_name=name) for pid, name in rows]
    )


# --- Patient membership ----------------------------------------------------


@router.get(
    "/patients/{patient_id}/segments",
    response_model=ApiResponse[list[SegmentResponse]],
)
async def list_patient_segments(
    patient_id: UUID,
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("patient_segments.read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[SegmentResponse]]:
    patient = await PatientService.get_patient(db, ctx.clinic_id, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    rows = await PatientSegmentsService.list_for_patient(db, ctx.clinic_id, patient_id)
    return ApiResponse(data=[_to_response(row) for row in rows])


@router.post(
    "/patients/{patient_id}/segments",
    response_model=ApiResponse[list[SegmentResponse]],
    status_code=status.HTTP_201_CREATED,
)
async def assign_patient_segment(
    patient_id: UUID,
    data: SegmentAssign,
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("patient_segments.write"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[SegmentResponse]]:
    await _ensure_segment(db, ctx.clinic_id, data.segment_id)
    await PatientSegmentsService.assign_patient(db, ctx.clinic_id, data.segment_id, patient_id)
    await db.commit()
    rows = await PatientSegmentsService.list_for_patient(db, ctx.clinic_id, patient_id)
    return ApiResponse(data=[_to_response(row) for row in rows])


@router.delete(
    "/patients/{patient_id}/segments/{segment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unassign_patient_segment(
    patient_id: UUID,
    segment_id: UUID,
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("patient_segments.write"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await _ensure_segment(db, ctx.clinic_id, segment_id)
    await PatientSegmentsService.unassign_patient(db, ctx.clinic_id, segment_id, patient_id)
    await db.commit()
