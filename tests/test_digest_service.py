from datetime import datetime, timezone

from digest_service import DigestWindow, compose_digest


def test_digest_keeps_actionable_storefront_events_and_drops_noise() -> None:
    window = DigestWindow.model_validate(
        {
            "builds": [
                {"project": "checkout", "status": "failed", "revision": "bad123", "occurred_at": "2026-09-03T10:00:00Z"},
                {"project": "catalog", "status": "passed", "revision": "good45", "occurred_at": "2026-09-03T11:00:00Z"},
                {"project": "theme", "status": "failed", "revision": "old789", "occurred_at": "2026-08-20T10:00:00Z"},
            ],
            "releases": [
                {"storefront": "uk-store", "version": "8.4.0", "action": "deployed", "occurred_at": "2026-09-02T12:00:00Z"}
            ],
            "diagnostics": [
                {"service": "payments", "severity": "critical", "summary": "Contract tests regressed", "occurred_at": "2026-09-01T08:00:00Z"},
                {"service": "search", "severity": "info", "summary": "Index refreshed", "occurred_at": "2026-09-01T09:00:00Z"},
            ],
        }
    )

    result = compose_digest(window, datetime(2026, 9, 4, tzinfo=timezone.utc))

    assert result.included_items == 3
    assert "checkout at bad123: failed" in result.body
    assert "uk-store 8.4.0: deployed" in result.body
    assert "[critical] payments: Contract tests regressed" in result.body
    assert "catalog" not in result.body
    assert "old789" not in result.body
    assert "Index refreshed" not in result.body
