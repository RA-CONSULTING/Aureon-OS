from __future__ import annotations

from aureon.operator.authorization_lease import (
    LEASE_SCHEMA,
    MAX_LEASE_SECONDS,
    TRADING_CONTROL_SCOPE,
    build_operator_authorization_receipt,
    record_operator_authorization,
)


def test_authorization_lease_is_bounded_expires_and_never_grants_release(tmp_path, monkeypatch):
    path = tmp_path / "release-ledger.jsonl"
    monkeypatch.setenv("AUREON_RELEASE_LEDGER_PATH", str(path))
    missing = build_operator_authorization_receipt(now=1000)
    assert missing["state"] == "unavailable" and missing["active"] is False

    granted = record_operator_authorization(
        action="grant", duration_seconds=MAX_LEASE_SECONDS, now=1000
    )
    assert granted["schema"] == LEASE_SCHEMA
    assert granted["scope"] == list(TRADING_CONTROL_SCOPE)
    assert granted["release_authority"] is False
    assert granted["mutation_authority"] is False

    active = build_operator_authorization_receipt(now=1001)
    assert active["active"] is True
    assert active["remaining_seconds"] == MAX_LEASE_SECONDS - 1
    assert active["ledger_event_sha256"] == granted["ledger_event_sha256"]

    expired = build_operator_authorization_receipt(now=1000 + MAX_LEASE_SECONDS)
    assert expired["state"] == "expired" and expired["active"] is False


def test_latest_revocation_wins_and_invalid_durations_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_RELEASE_LEDGER_PATH", str(tmp_path / "release-ledger.jsonl"))
    record_operator_authorization(action="grant", duration_seconds=3600, now=2000)
    revoked = record_operator_authorization(action="revoke", now=2001)
    assert revoked["state"] == "revoked"
    readback = build_operator_authorization_receipt(now=2002)
    assert readback["state"] == "revoked" and readback["active"] is False

    for duration in (None, 59, MAX_LEASE_SECONDS + 1, 1.5):
        try:
            record_operator_authorization(action="grant", duration_seconds=duration, now=3000)
        except ValueError as exc:
            assert str(exc) == "authorization_lease_duration_invalid"
        else:
            raise AssertionError("invalid authorization duration accepted")
