from __future__ import annotations

import base64

import pytest

pytest.importorskip("flask")

from aureon.vault.ui.server import VAULT_UI_AUTH_ENV, create_app


TOKEN = "vault-ui-compat-test-" + ("T" * 48)
HNC_KEY = base64.urlsafe_b64encode(b"U" * 32).decode().rstrip("=")
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def client_and_loop(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(VAULT_UI_AUTH_ENV, TOKEN)
    monkeypatch.setenv("AUREON_HNC_PACKET_MASTER_KEY", HNC_KEY)
    app = create_app(base_interval_s=0.01)
    loop = app.config["AUREON_LOOP"]
    app.testing = True
    yield app.test_client(), loop


def test_browser_ui_is_held_while_health_status_and_voice_inventory_are_safe(
    client_and_loop,
) -> None:
    client, loop = client_and_loop

    index = client.get("/", headers=AUTH)
    assert index.status_code == 423
    assert index.get_json()["request_executed"] is False

    health = client.get("/api/health", headers=AUTH)
    assert health.status_code == 200
    assert health.get_json()["loop_id"] == loop.loop_id

    status = client.get("/api/status", headers=AUTH).get_json()["status"]
    assert {
        "loop_id",
        "cycles",
        "vault",
        "clock",
        "casimir",
        "auris",
        "deployer",
        "pinger",
        "rally",
        "voice",
    } <= set(status)

    voices = client.get("/api/voices", headers=AUTH).get_json()["voices"]
    assert voices == []


@pytest.mark.parametrize(
    "path",
    [
        "/api/message",
        "/api/speak",
        "/api/converse",
        "/api/tick",
        "/api/loop/start",
        "/api/loop/stop",
    ],
)
def test_interaction_routes_are_hnc_held_without_mutating_loop(
    client_and_loop,
    path: str,
) -> None:
    client, loop = client_and_loop
    cycle_before = loop._cycle

    response = client.post(path, json={"text": "held", "voice": "queen"}, headers=AUTH)
    body = response.get_json()

    assert response.status_code == 423
    assert body["status"] == "HOLD"
    assert body["request_executed"] is False
    assert body["plumber_hnc_admitted"] is True
    assert loop._cycle == cycle_before
    assert loop.voice_engine is None


def test_read_only_utterance_history_remains_available_after_held_message(
    client_and_loop,
) -> None:
    client, loop = client_and_loop
    assert loop.voice_engine is None
    before = 0

    held = client.post(
        "/api/message",
        json={"text": "must-not-enter-history", "voice": "queen"},
        headers=AUTH,
    )
    history = client.get("/api/utterances?n=10", headers=AUTH).get_json()

    assert held.status_code == 423
    assert history["ok"] is True
    assert history["count"] == before
    assert all(
        item.get("statement", {}).get("text") != "must-not-enter-history"
        for item in history["utterances"]
    )
