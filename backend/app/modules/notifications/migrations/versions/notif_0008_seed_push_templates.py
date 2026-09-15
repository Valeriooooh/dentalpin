"""notifications: seed system push templates (notif_0008).

Template-kind push sends render ``subject`` (notification title) and
``body_text`` from the template row at dispatch time; with no
``channel='push'`` row the adapter has nothing to push and the message
fails ("empty body"). Same shape as ``smg_0002`` for SMS: one system row
(clinic_id NULL, is_system) per notification type and locale (es/en);
clinic rows for the same key/locale take precedence and are never
touched here. Downgrade removes exactly the seeded rows (marker).

Revision ID: notif_0008
Revises: notif_0007
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "notif_0008"
down_revision: str | None = "notif_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MARKER = "Seeded by notifications notif_0008 (system push templates)"

# (template_key, (es_title, es_body), (en_title, en_body)). Literal text:
# the push adapter uses subject/body_text verbatim (no placeholders).
ROWS: tuple[tuple[str, tuple[str, str], tuple[str, str]], ...] = (
    (
        "appointment_confirmation",
        ("Cita confirmada", "Su cita ha quedado confirmada. Le esperamos en la clínica."),
        ("Appointment confirmed", "Your appointment is confirmed. We look forward to seeing you."),
    ),
    (
        "appointment_reminder",
        ("Recordatorio de cita", "Recordatorio: tiene cita mañana en su clínica dental."),
        (
            "Appointment reminder",
            "Reminder: you have an appointment tomorrow at your dental clinic.",
        ),
    ),
    (
        "appointment_cancelled",
        ("Cita cancelada", "Su cita ha sido cancelada. Llámenos para pedir una nueva."),
        ("Appointment cancelled", "Your appointment has been cancelled. Call us to reschedule."),
    ),
    (
        "budget_sent",
        ("Nuevo presupuesto", "Tiene un nuevo presupuesto disponible en su clínica dental."),
        ("New estimate", "A new treatment estimate is available at your dental clinic."),
    ),
    (
        "budget_accepted",
        ("Presupuesto aceptado", "Gracias, hemos registrado la aceptación de su presupuesto."),
        ("Estimate accepted", "Thank you, your treatment estimate acceptance is recorded."),
    ),
    (
        "budget_reminder",
        ("Presupuesto pendiente", "Le recordamos que tiene un presupuesto pendiente de respuesta."),
        ("Estimate pending", "Reminder: you have a treatment estimate awaiting your reply."),
    ),
    (
        "invoice_sent",
        ("Nueva factura", "Tiene una nueva factura disponible en su clínica dental."),
        ("New invoice", "A new invoice is available at your dental clinic."),
    ),
    (
        "welcome",
        ("Bienvenido/a", "Bienvenido/a a su clínica dental. Este es nuestro canal de avisos."),
        ("Welcome", "Welcome to your dental clinic. This is our notifications channel."),
    ),
    (
        "recall_reminder",
        ("Revisión dental", "Le recordamos su próxima revisión dental. Llámenos para confirmar."),
        ("Dental check-up", "Reminder about your upcoming dental check-up. Call us to confirm."),
    ),
)

_INSERT = sa.text(
    """
INSERT INTO notification_templates
    (id, clinic_id, channel, template_key, locale, subject, body_text,
     is_system, is_active, description, created_at, updated_at)
SELECT gen_random_uuid(), NULL, 'push',
       CAST(:key AS VARCHAR(100)), CAST(:locale AS VARCHAR(5)),
       CAST(:subject AS VARCHAR(255)), CAST(:body AS TEXT),
       TRUE, TRUE, CAST(:marker AS VARCHAR(500)), now(), now()
WHERE NOT EXISTS (
    SELECT 1 FROM notification_templates
    WHERE clinic_id IS NULL
      AND channel = 'push'
      AND template_key = :key
      AND locale = :locale
)
"""
)

_DELETE = sa.text(
    """
DELETE FROM notification_templates
WHERE clinic_id IS NULL
  AND channel = 'push'
  AND description = :marker
"""
)


def upgrade() -> None:
    conn = op.get_bind()
    for key, es, en in ROWS:
        for locale, (subject, body) in (("es", es), ("en", en)):
            conn.execute(
                _INSERT,
                {"key": key, "locale": locale, "subject": subject, "body": body, "marker": MARKER},
            )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(_DELETE, {"marker": MARKER})
