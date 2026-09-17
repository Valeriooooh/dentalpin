"""Error tracking helper: DSN-gated, never raises, PII-free."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

from app.config import Settings
from app.core.log_context import scrub_event, setup_error_tracking


def test_off_by_default_at_settings_level() -> None:
    assert Settings().SENTRY_DSN == ""
    assert Settings().SENTRY_TRACES_SAMPLE_RATE == 0.0


def test_no_dsn_is_noop() -> None:
    assert setup_error_tracking(dsn="") is False
    assert setup_error_tracking() is False


def test_missing_sdk_is_noop(monkeypatch) -> None:
    """Without sentry_sdk installed, a configured DSN logs and stays off."""
    monkeypatch.setitem(sys.modules, "sentry_sdk", None)
    assert setup_error_tracking(dsn="https://key@sentry.io/1") is False


def test_successful_init_returns_true(monkeypatch) -> None:
    """With sentry_sdk present and init succeeding, tracking turns on."""
    mock_sdk = MagicMock()
    monkeypatch.setitem(sys.modules, "sentry_sdk", mock_sdk)
    assert setup_error_tracking(dsn="https://key@sentry.io/1") is True
    mock_sdk.init.assert_called_once()
    kwargs = mock_sdk.init.call_args.kwargs
    assert kwargs["send_default_pii"] is False
    assert kwargs["dsn"] == "https://key@sentry.io/1"
    assert kwargs["before_send"] is scrub_event
    assert kwargs["before_send_transaction"] is scrub_event


def test_scrub_event_drops_identifiers_from_url() -> None:
    pid = "123e4567-e89b-12d3-a456-426614174000"
    token = "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-"
    event = {
        "request": {
            "url": f"https://api/api/v1/patients/{pid}/notes",
            "query_string": "t=secret",
        }
    }
    out = scrub_event(event, {})
    assert out["request"]["url"] == "https://api/api/v1/patients/[id]/notes"
    assert "query_string" not in out["request"]
    tok = scrub_event({"request": {"url": f"https://api/public/budgets/{token}/pdf"}})
    assert tok["request"]["url"] == "https://api/public/budgets/[id]/pdf"
    # Short route words survive; events without a request pass through.
    assert scrub_event({"request": {"url": "https://api/api/v1/patients"}})["request"][
        "url"
    ].endswith("/patients")
    assert scrub_event({"message": "x"}) == {"message": "x"}
