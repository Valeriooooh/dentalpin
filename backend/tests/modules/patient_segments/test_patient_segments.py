"""patient_segments: CRUD, membership, tenancy, and HTTP codes."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.models import Clinic
from app.modules.patient_segments.service import PatientSegmentsService
from app.modules.patients.models import Patient


async def _other_patient(db_session, clinic_id):
    p = Patient(clinic_id=clinic_id, first_name="Seg", last_name="Member")
    db_session.add(p)
    await db_session.commit()
    return p


@pytest.mark.asyncio
async def test_crud_and_membership_happy_path(
    db_session: AsyncSession, test_clinic: Clinic, test_patient: Patient
):
    seg = await PatientSegmentsService.create_segment(
        db_session, test_clinic.id, {"name": "vip", "color": "#gold"}
    )
    await db_session.commit()
    assert seg.name == "vip"

    member = await _other_patient(db_session, test_clinic.id)
    await PatientSegmentsService.assign_patient(db_session, test_clinic.id, seg.id, member.id)
    await db_session.commit()

    mine = await PatientSegmentsService.list_for_patient(db_session, test_clinic.id, member.id)
    assert [s.name for s in mine] == ["vip"]
    members = await PatientSegmentsService.list_members(db_session, test_clinic.id, seg.id)
    assert [pid for pid, _ in members] == [member.id]

    await PatientSegmentsService.unassign_patient(db_session, test_clinic.id, seg.id, member.id)
    await db_session.commit()
    assert (
        await PatientSegmentsService.list_for_patient(db_session, test_clinic.id, member.id)
    ) == []


@pytest.mark.asyncio
async def test_duplicate_name_is_409_from_constraint(db_session: AsyncSession, test_clinic: Clinic):
    await PatientSegmentsService.create_segment(db_session, test_clinic.id, {"name": "vip"})
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await PatientSegmentsService.create_segment(db_session, test_clinic.id, {"name": "vip"})
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_double_assign_is_409(
    db_session: AsyncSession, test_clinic: Clinic, test_patient: Patient
):
    seg = await PatientSegmentsService.create_segment(db_session, test_clinic.id, {"name": "vip"})
    await db_session.commit()
    await PatientSegmentsService.assign_patient(db_session, test_clinic.id, seg.id, test_patient.id)
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await PatientSegmentsService.assign_patient(
            db_session, test_clinic.id, seg.id, test_patient.id
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_rename_conflict_is_409(db_session: AsyncSession, test_clinic: Clinic):
    await PatientSegmentsService.create_segment(db_session, test_clinic.id, {"name": "a"})
    b = await PatientSegmentsService.create_segment(db_session, test_clinic.id, {"name": "b"})
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await PatientSegmentsService.update_segment(db_session, b, {"name": "a"})
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_patch_keeps_untouched_fields(db_session: AsyncSession, test_clinic: Clinic):
    seg = await PatientSegmentsService.create_segment(
        db_session, test_clinic.id, {"name": "vip", "color": "#gold"}
    )
    await db_session.commit()
    updated = await PatientSegmentsService.update_segment(db_session, seg, {"description": "d"})
    assert updated.name == "vip" and updated.color == "#gold"
    assert updated.description == "d"


@pytest.mark.asyncio
async def test_foreign_clinic_segment_is_invisible(
    db_session: AsyncSession, test_clinic: Clinic, test_patient: Patient
):
    other = Clinic(id=uuid4(), name="Other", tax_id="B9", address={}, settings={})
    db_session.add(other)
    await db_session.commit()
    seg = await PatientSegmentsService.create_segment(db_session, other.id, {"name": "vip"})
    await db_session.commit()
    assert await PatientSegmentsService.get_segment(db_session, test_clinic.id, seg.id) is None
    assert await PatientSegmentsService.list_segments(db_session, test_clinic.id) == []
    # Cross-clinic assign is rejected even at direct-service level.
    with pytest.raises(HTTPException) as exc:
        await PatientSegmentsService.assign_patient(
            db_session, test_clinic.id, seg.id, test_patient.id
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_unassign_missing_link_is_404(
    db_session: AsyncSession, test_clinic: Clinic, test_patient: Patient
):
    seg = await PatientSegmentsService.create_segment(db_session, test_clinic.id, {"name": "vip"})
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await PatientSegmentsService.unassign_patient(
            db_session, test_clinic.id, seg.id, test_patient.id
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_http_codes(client, auth_headers, test_clinic: Clinic, test_patient: Patient):
    # Capture now: later requests expire fixture attributes (conftest #188),
    # and sync refresh outside a greenlet raises MissingGreenlet.
    patient_id = str(test_patient.id)
    created = await client.post(
        "/api/v1/patient_segments/segments", json={"name": "vip"}, headers=auth_headers
    )
    assert created.status_code == 201
    seg_id = created.json()["data"]["id"]

    dup = await client.post(
        "/api/v1/patient_segments/segments", json={"name": "vip"}, headers=auth_headers
    )
    assert dup.status_code == 409

    bad = await client.post(
        "/api/v1/patient_segments/segments", json={"name": ""}, headers=auth_headers
    )
    assert bad.status_code == 422

    blank = await client.post(
        "/api/v1/patient_segments/segments", json={"name": "   "}, headers=auth_headers
    )
    assert blank.status_code == 422

    bad_color = await client.post(
        "/api/v1/patient_segments/segments",
        json={"name": "c", "color": "red"},
        headers=auth_headers,
    )
    assert bad_color.status_code == 422

    listed = await client.get("/api/v1/patient_segments/segments", headers=auth_headers)
    assert listed.status_code == 200
    assert [s["name"] for s in listed.json()["data"]] == ["vip"]

    assigned = await client.post(
        f"/api/v1/patient_segments/patients/{patient_id}/segments",
        json={"segment_id": seg_id},
        headers=auth_headers,
    )
    assert assigned.status_code == 201

    missing_patient = await client.post(
        f"/api/v1/patient_segments/patients/{uuid4()}/segments",
        json={"segment_id": seg_id},
        headers=auth_headers,
    )
    assert missing_patient.status_code == 404

    removed = await client.delete(
        f"/api/v1/patient_segments/patients/{patient_id}/segments/{seg_id}",
        headers=auth_headers,
    )
    assert removed.status_code == 204

    removed_again = await client.delete(
        f"/api/v1/patient_segments/patients/{patient_id}/segments/{seg_id}",
        headers=auth_headers,
    )
    assert removed_again.status_code == 404

    dropped = await client.delete(
        f"/api/v1/patient_segments/segments/{seg_id}", headers=auth_headers
    )
    assert dropped.status_code == 204
