"""patient_segments: initial schema.

Tables:
    - ``patient_segments`` — named groups per clinic (unique name).
    - ``patient_segment_links`` — patient membership (unique pair, both
      FKs CASCADE so deleting a segment or patient drops its links).

clinics.id is core (created by "0001" itself). patients.id lives on the
pat_0001 -> pat_0002 -> pat_0003 chain with no branch label of its own,
so depends_on pins patients' chain first — same pattern as
recalls/rec_0001 and patient_relationships/prel_0001.

Lives on its own Alembic branch (``patient_segments``) per ADR 0002.

Revision ID: pseg_0001
Revises: 0001
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "pseg_0001"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = ("patient_segments",)
depends_on: str | Sequence[str] | None = ("pat_0003",)


def upgrade() -> None:
    op.create_table(
        "patient_segments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", "name", name="uq_patient_segments_clinic_name"),
    )
    op.create_index("ix_patient_segments_clinic_id", "patient_segments", ["clinic_id"])

    op.create_table(
        "patient_segment_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("segment_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["segment_id"], ["patient_segments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("segment_id", "patient_id", name="uq_patient_segment_links_pair"),
    )
    op.create_index("ix_patient_segment_links_clinic_id", "patient_segment_links", ["clinic_id"])
    op.create_index("ix_patient_segment_links_segment_id", "patient_segment_links", ["segment_id"])
    op.create_index("ix_patient_segment_links_patient_id", "patient_segment_links", ["patient_id"])


def downgrade() -> None:
    op.drop_table("patient_segment_links")
    op.drop_table("patient_segments")
