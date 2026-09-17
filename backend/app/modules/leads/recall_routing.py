"""Matched-enquiry routing: an enquiry from a known patient becomes a recall.

RecallService.create is the **only** writer of a recall here. It dedupes
per (patient, reason) against active recalls and publishes
recall.created transactionally, which feeds activity_journal and (when
installed) recall_reminders. A hand-written insert would silently drop
both — never route around it.

recalls is in manifest.depends, so importing RecallService is legal.
"""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patients.models import Patient
from app.modules.recalls.service import RecallService

logger = logging.getLogger(__name__)

# The recall reason matched enquiries land on. "other" already exists in
# recalls.models.REASONS; a dedicated lead_callback reason would filter
# better but means editing another module's enum, its interval defaults,
# its picker and ten locale files — a follow-up, not a side effect of
# this module.
ENQUIRY_REASON = "other"

# Ceiling for the composed note. RecallService.create overwrites
# reason_note on its dedupe path, so a flood that kept appending would
# grow one row without bound.
NOTE_CAP = 4000
_NOTE_SEPARATOR = "\n\n---\n\n"


def _compose_enquiry_note(data: dict) -> str:
    """motive / description / availability, verbatim.

    Blank-line separated, no invented labels: the note is data the staff
    reads, in the enquirer's own words.
    """
    fields = ("motive", "description", "availability")
    parts = [str(data.get(field) or "").strip() for field in fields]
    return "\n\n".join(part for part in parts if part)[:NOTE_CAP]


def _merged_note(existing_note: str | None, note: str) -> str | None:
    """Append note to an existing note without ever losing text.

    A staff member may have written their own other recall for this
    patient, and a repeat enquiry must not stack a second copy of the
    same block. So:

    * no existing note -> the new note;
    * the block is already in there -> the existing note, unchanged;
    * appending would exceed the cap -> the existing note, unchanged;
    * otherwise -> existing + separator + new.
    """
    if not existing_note:
        return note
    if not note or note in existing_note:
        return existing_note
    if len(existing_note) + len(_NOTE_SEPARATOR) + len(note) > NOTE_CAP:
        return existing_note
    return f"{existing_note}{_NOTE_SEPARATOR}{note}"


async def route_matched_enquiry(
    db: AsyncSession,
    clinic_id: UUID,
    patients: list[Patient],
    data: dict,
    recommended_by: UUID | None,
) -> list[Patient]:
    """Queue a recall for each matched patient; return the patients touched.

    Every match gets a recall — each one needs a phone call, and a family
    sharing a phone is a legitimate two-patient match.

    An opted-out (do_not_contact) patient's recall is created in
    needs_review so it never sits in the default call list (which filters
    opted-out patients out and would silently swallow the enquiry).
    Outbound contact stays blocked independently by the notifications
    gateway, even with force_send.
    """
    note = _compose_enquiry_note(data)
    today = date.today()
    recalled: list[Patient] = []

    for patient in patients:
        existing = await RecallService.find_pending_for(db, clinic_id, patient.id, ENQUIRY_REASON)
        recall, _created = await RecallService.create(
            db,
            clinic_id,
            {
                "patient_id": patient.id,
                "due_month": today,  # the service normalises to day-1
                "due_date": today,  # "call today"
                "reason": ENQUIRY_REASON,
                "priority": "high",  # the call list sorts high first
                "reason_note": _merged_note(existing.reason_note if existing else None, note),
                "assigned_professional_id": None,
            },
            recommended_by=recommended_by,
        )
        if patient.do_not_contact and recall.status != "needs_review":
            recall.status = "needs_review"
            await db.flush()
        recalled.append(patient)

    logger.info(
        "leads: enquiry routed to %s recall(s) for clinic %s",
        len(recalled),
        clinic_id,
    )
    return recalled
