"""PatientSegmentsService — segments CRUD + membership.

Cross-module read of ``patients`` is allowed: this module lists ``patients``
in ``manifest.depends`` (ADR 0002). Duplicate names / double links answer
409 from their UNIQUE constraints (L6), never select-then-insert.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from fastapi import status as http_status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patients.models import Patient
from app.modules.patients.service import PatientService

from .models import PatientSegment, PatientSegmentLink


class PatientSegmentsService:
    @staticmethod
    async def list_segments(db: AsyncSession, clinic_id: UUID) -> list[tuple]:
        """Segments with member counts, ordered by name."""
        stmt = (
            select(PatientSegment, func.count(PatientSegmentLink.id))
            .outerjoin(
                PatientSegmentLink,
                PatientSegmentLink.segment_id == PatientSegment.id,
            )
            .where(PatientSegment.clinic_id == clinic_id)
            .group_by(PatientSegment.id)
            .order_by(PatientSegment.name)
        )
        return (await db.execute(stmt)).all()

    @staticmethod
    async def create_segment(db: AsyncSession, clinic_id: UUID, data: dict) -> PatientSegment:
        row = PatientSegment(clinic_id=clinic_id, **data)
        db.add(row)
        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="A segment with this name already exists",
            ) from exc
        return row

    @staticmethod
    async def get_segment(
        db: AsyncSession, clinic_id: UUID, segment_id: UUID
    ) -> PatientSegment | None:
        stmt = select(PatientSegment).where(
            PatientSegment.id == segment_id, PatientSegment.clinic_id == clinic_id
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def update_segment(db: AsyncSession, row: PatientSegment, data: dict) -> PatientSegment:
        for key, value in data.items():
            setattr(row, key, value)
        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="A segment with this name already exists",
            ) from exc
        return row

    @staticmethod
    async def delete_segment(db: AsyncSession, row: PatientSegment) -> None:
        # Links drop via ON DELETE CASCADE on segment_id.
        await db.delete(row)
        await db.flush()

    @staticmethod
    async def assign_patient(
        db: AsyncSession, clinic_id: UUID, segment_id: UUID, patient_id: UUID
    ) -> PatientSegmentLink:
        segment = await PatientSegmentsService.get_segment(db, clinic_id, segment_id)
        if segment is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND, detail="Segment not found"
            )
        patient = await PatientService.get_patient(db, clinic_id, patient_id)
        if patient is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND, detail="Patient not found"
            )
        row = PatientSegmentLink(clinic_id=clinic_id, segment_id=segment_id, patient_id=patient_id)
        db.add(row)
        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Patient is already in this segment",
            ) from exc
        return row

    @staticmethod
    async def unassign_patient(
        db: AsyncSession, clinic_id: UUID, segment_id: UUID, patient_id: UUID
    ) -> None:
        stmt = select(PatientSegmentLink).where(
            PatientSegmentLink.segment_id == segment_id,
            PatientSegmentLink.patient_id == patient_id,
            PatientSegmentLink.clinic_id == clinic_id,
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Patient is not in this segment",
            )
        await db.delete(row)
        await db.flush()

    @staticmethod
    async def list_members(db: AsyncSession, clinic_id: UUID, segment_id: UUID) -> list[tuple]:
        """``(patient_id, full_name)`` pairs, ordered by name."""
        stmt = (
            select(Patient)
            .join(PatientSegmentLink, PatientSegmentLink.patient_id == Patient.id)
            .where(
                PatientSegmentLink.segment_id == segment_id,
                PatientSegmentLink.clinic_id == clinic_id,
                Patient.clinic_id == clinic_id,
            )
            .order_by(Patient.first_name, Patient.last_name)
        )
        patients = (await db.execute(stmt)).scalars().all()
        return [(p.id, p.full_name) for p in patients]

    @staticmethod
    async def list_for_patient(
        db: AsyncSession, clinic_id: UUID, patient_id: UUID
    ) -> list[PatientSegment]:
        stmt = (
            select(PatientSegment)
            .join(PatientSegmentLink, PatientSegmentLink.segment_id == PatientSegment.id)
            .where(
                PatientSegmentLink.patient_id == patient_id,
                PatientSegmentLink.clinic_id == clinic_id,
                PatientSegment.clinic_id == clinic_id,
            )
            .order_by(PatientSegment.name)
        )
        return (await db.execute(stmt)).scalars().all()
