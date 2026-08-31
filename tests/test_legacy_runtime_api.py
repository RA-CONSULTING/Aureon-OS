"""Tests for the legacy runtime API surface mounted on the operator.

The older trading console's endpoints (terminal-state / flight-test / reboot-advice / env-credentials /
bots / trades / telegram) now resolve on the operator gateway. Each serves real state or an explicit
honest "unavailable" — never a fabricated value, never a 404/500. Offline; no network.
"""

from __future__ import annotations

import pytest

pytest.importorskip("flask", reason="operator HTTP surface requires the `.[operator]` extra")


def _client(monkeypatch=None):
    import importlib

    import aureon.operator.operator_server as srv

    importlib.reload(srv)
    return srv.create_app(
        test_ingress_release=srv.TestOnlyOperatorIngressRelease(
            master_key=b"legacy-runtime-http-route-test-key-material",
        )
    ).test_client()


def test_terminal_state_resolves_with_ok_flag():
    r = _client().get("/api/terminal-state")
    assert r.status_code == 200
    body = r.get_json()
    assert isinstance(body, dict) and "ok" in body   # honest booting/stale payload when trader is down


def test_flight_test_has_checks_and_reboot_advice():
    r = _client().get("/api/flight-test")
    assert r.status_code == 200
    body = r.get_json()
    assert "checks" in body and "reboot_advice" in body


def test_reboot_advice_carries_reboot_advice():
    r = _client().get("/api/reboot-advice")
    assert r.status_code == 200
    assert "reboot_advice" in r.get_json()


def test_env_credentials_masked_no_raw_values():
    r = _client().get("/api/env-credentials")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("secret_policy") == "metadata_only_no_values_returned"
    assert "exchanges" in body


def test_bots_is_honestly_empty_not_fabricated():
    r = _client().get("/api/bots")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("bots") == []                    # honest empty, never invented tails


def test_trades_is_honestly_empty_not_mock():
    r = _client().get("/api/trades?symbols=ETHUSDT")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("trades") == {}
    assert body.get("mock") is not True              # never fabricated trades


def test_telegram_missing_message_is_400():
    r = _client().post("/api/notifications/telegram", json={})
    assert r.status_code == 400
    assert r.get_json()["ok"] is False


def test_telegram_unconfigured_is_honest_503(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    r = _client().post("/api/notifications/telegram", json={"message": "hi"})
    assert r.status_code == 503
    body = r.get_json()
    assert body["ok"] is False and "not configured" in body["reason"]
