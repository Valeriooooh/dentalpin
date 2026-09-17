# Changelog — prescriptions

## Unreleased

- Declare `patients_clinical` + `medical_reference` in
  `manifest.depends` (review: service imports both; honest dependency).
- Agent tools no longer roll back the session on 404 (match the
  `agenda/tools.py` precedent: rollback only on `IntegrityError`).

- fix: import relative paths in the prescriptions page and summary card
  resolve to the layer composables (TS2307 in CI on current main).

- Initial module: drafts with free-text/catalog-soft lines, issue/cancel
  lifecycle with prescriber snapshot, country hook registry
  (`PrescriptionComplianceHook`), templates, prescriber profiles,
  allergy/interaction banner, PDF download, agent draft tools.
