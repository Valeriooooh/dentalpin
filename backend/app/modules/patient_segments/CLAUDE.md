# patient_segments module

Clinic-local patient tags for grouping and campaigns ("Groups" card on the
patient summary). No points, no currency, no expiry — grouping only.

## Public API

Routes mounted at `/api/v1/patient_segments/`.

- `GET    /segments` — list with member counts; `patient_segments.read`
- `POST   /segments` — create (409 on duplicate name); `patient_segments.write`
- `PATCH  /segments/{id}` — rename/recolor (all-optional + `exclude_unset`); `patient_segments.write`
- `DELETE /segments/{id}` — delete, links cascade; `patient_segments.write`
- `GET    /segments/{id}/patients` — members with names (campaign targeting); `patient_segments.read`
- `GET    /patients/{id}/segments` — one patient's segments (card); `patient_segments.read`
- `POST   /patients/{id}/segments` — assign (409 if linked); `patient_segments.write`
- `DELETE /patients/{id}/segments/{segment_id}` — unassign (404 if missing); `patient_segments.write`

409s come from UNIQUE constraints, never select-then-insert (L6).

## Dependencies

`manifest.depends = ["patients"]`. Reads `Patient.full_name` for member
names; migration FKs to `patients.id` with `depends_on = ("pat_0003",)`.

## Permissions

`patient_segments.read`, `patient_segments.write` (dentist/assistant/
receptionist rw, hygienist read — campaign work is front-desk work).

## Frontend

`PatientSegmentsCard.vue` in the `patient.summary.cards` slot (order 56,
after relationships). Chips + add-existing + inline create + remove.

## Lifecycle

- `installable=True`, `auto_install=False`, `removable=True`.
- Own Alembic branch (`patient_segments`, `pseg_0001`).

## CHANGELOG

See `./CHANGELOG.md`.
