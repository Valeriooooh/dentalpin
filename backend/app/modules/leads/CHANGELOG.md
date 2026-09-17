# Changelog — leads module

## Unreleased

### Added

- `leads` module: inbound enquiries from the clinic external website form,
  mounted at `/api/v1/leads/`, with the `/leads` queue page and the
  Settings → Integrations → "Formulario web" settings page.
- Public, key-gated intake endpoint `POST /api/v1/leads/public/intake`
  (`X-Lead-Key`): honeypot, 8 KB body cap, optional captcha, per-clinic
  daily cap and identical responses in every routing branch (D12).
- Routing rule: an enquiry whose phone **or** email matches a non-archived
  patient of the clinic queues a recall (`reason="other"`, `priority="high"`,
  due today) and writes **no** lead row; `do_not_contact` matches land in
  `needs_review`.
- Repeat enquiries refresh the existing `(patient, "other")` recall and append
  the enquiry note instead of overwriting it (4000-character cap).
- Tables `leads`, `leads_intake_keys` (SHA-256 hash only) and `leads_settings`
  on the module own Alembic branch `leads` (`leads_0001`).
- `manifest.depends = ["patients", "recalls"]` — the module cannot be installed
  without them, because a matched enquiry has nowhere to go otherwise.
- Six agent tools; intake-key rotation and the active toggle are deliberately
  not exposed to agents.
- Publishes no events of its own: the recall it creates publishes
  `recall.created` through the `recalls` module.
- The daily counter is committed before a 429, so a blocked flood keeps showing
  in the gauge instead of being rolled back with the rejected request;
  `tests/modules/leads/test_intake.py` asserts it through a separate
  connection.
- The settings page builds the intake URL from the app's API base
  (`runtimeConfig.public.apiBaseUrl`) instead of the browser origin, so the URL it
  hands the clinic's web developer points at the API — posting to the SPA origin
  answers with a login redirect, not `{"received": true}`.
- Frontend layer with the `/leads` page, the convert drawer, the manual
  create/edit modal and the settings page.
- Localised into all ten UI locales (en, es, fr, de, pt, it, pl, hu, ta, ar) —
  key-identical and placeholder-checked by
  `frontend/tests/i18n/locale-parity.test.ts`. Each language reuses the host locale
  own word for Recalls and its own address register.
- The /leads queue opens filtered to **New** (the status chip reads
  `Status · 1`): converted cards leave the default view as soon as they are
  converted. Deliberate deviation from the original plan (which defaulted to all
  statuses) — the default is a *visible* chip selection and the API still answers
  "no status param = every status", so nothing is hidden server-side and the
  converted history stays reachable by clearing the chip.
- Form validation on both staff forms (`utils/leadValidation.ts`): an invalid email,
  a phone with too few digits, a missing required field or a future date of birth
  is refused **before** it is sent, with the reason shown on the field and a toast
  — every message translated in all ten locales. The rules mirror what pydantic
  accepts (single @, dot in the domain, 6+ digits, the 20-char patient phone
  column), so anything the form accepts is not rejected by the server.
- Copy buttons on the website-form settings page for the intake URL, the intake
  key and the `curl` example (with an explicit error toast when the browser
  denies clipboard access).