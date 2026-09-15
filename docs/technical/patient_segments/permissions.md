# patient_segments — permissions

| Permission | Grants | Gated endpoints |
|---|---|---|
| `patient_segments.read` | list segments + members, patient card | `GET /segments`, `GET /segments/{id}/patients`, `GET /patients/{id}/segments` |
| `patient_segments.write` | create/rename/delete, assign/unassign | `POST/PATCH/DELETE /segments*`, `POST/DELETE /patients/{id}/segments*` |

Role defaults: admin `*`, dentist/assistant/receptionist read+write,
hygienist read.
