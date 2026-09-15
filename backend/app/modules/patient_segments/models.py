"""patient_segments — clinic-local patient tags for grouping and campaigns.

Segments are free-form labels (``vip``, ``ortho-active``, ``recall-risk``)
a clinic assigns to patients. No points, no currency, no expiry — grouping
only (a points ledger would need dispute/expiry semantics this module
deliberately avoids). Feeds future portal campaign targeting via the
member-listing endpoint.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class PatientSegment(Base, TimestampMixin):
    """A named patient group owned by one clinic."""

    __tablename__ = "patient_segments"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    clinic_id: Mapped[UUID] = mapped_column(ForeignKey("clinics.id"), index=True)

    name: Mapped[str] = mapped_column(String(60))
    color: Mapped[str | None] = mapped_column(String(7), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        UniqueConstraint("clinic_id", "name", name="uq_patient_segments_clinic_name"),
    )


class PatientSegmentLink(Base, TimestampMixin):
    """Membership of one patient in one segment (same clinic on both sides)."""

    __tablename__ = "patient_segment_links"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    clinic_id: Mapped[UUID] = mapped_column(ForeignKey("clinics.id"), index=True)
    segment_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patient_segments.id", ondelete="CASCADE"),
        index=True,
    )
    patient_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("segment_id", "patient_id", name="uq_patient_segment_links_pair"),
    )
