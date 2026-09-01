from __future__ import annotations

import base64

import pytest

pytest.importorskip("flask")

from aureon.vault.aureon_vault import VaultContent
from aureon.vault.ui.server import VAULT_UI_AUTH_ENV, create_app


TOKEN = "vault-ui-mesh-test-" + ("M" * 48)
HNC_KEY = base64.urlsafe_b64encode(b"M" * 32).decode().rstrip("=")
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def client_and_loop(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(VAULT_UI_AUTH_ENV, TOKEN)
    monkeypatch.setenv("AUREON_HNC_PACKET_MASTER_KEY", HNC_KEY)
    app = create_app(base_interval_s=0.01)
    loop = app.config["AUREON_LOOP"]
    app.testing = True
    yield app.test_client(), loop, app


def _card(topic: str) -> dict:
    return VaultContent.build(
        category="bridge.test",
        source_topic=topic,
        payload={"origin": "untrusted-peer"},
    ).to_dict()


def test_card_ingress_is_hnc_held_without_merge_or_card_disclosure(client_and_loop) -> None:
    client, loop, _app = client_and_loop
    remote = _card("remote.hostile")
    hashes_before = {item.harmonic_hash for item in loop.vault._contents.values()}

    response = client.post(
        "/api/bridge/cards",
        json={
            "from_peer_id": "attacker",
            "our_hashes": [],
            "cards": [remote],
        },
        headers=AUTH,
    )
    body = response.get_json()
    hashes_after = {item.harmonic_hash for item in loop.vault._contents.values()}

    assert response.status_code == 423
    assert body["status"] == "HOLD"
    assert body["request_executed"] is False
    assert "cards" not in body
    assert hashes_after == hashes_before
    assert remote["harmonic_hash"] not in hashes_after


def test_mesh_runtime_is_inert_and_info_requires_authentication(client_and_loop) -> None:
    client, _loop, app = client_and_loop

    assert client.get("/api/bridge/mesh/info").status_code == 401
    response = client.get("/api/bridge/mesh/info", headers=AUTH)
    runtime = app.config["AUREON_PHI_BRIDGE_MESH_RUNTIME"]

    assert response.status_code == 200
    assert response.get_json()["running"] is False
    assert runtime["status"] == "HOLD"
    assert runtime["udp_discovery_started"] is False
    assert runtime["card_gossip_started"] is False


def test_two_apps_do_not_converge_through_held_card_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(VAULT_UI_AUTH_ENV, TOKEN)
    monkeypatch.setenv("AUREON_HNC_PACKET_MASTER_KEY", HNC_KEY)
    app_a = create_app(base_interval_s=0.01)
    loop_a = app_a.config["AUREON_LOOP"]
    card_a = VaultContent.build(category="g", source_topic="app.a", payload={"who": "a"})
    loop_a.vault.add(card_a)
    mesh_a = app_a.config["AUREON_PHI_BRIDGE_MESH"]
    mesh_a._total_in = 7
    mesh_a._gossip_cycles = 3

    app_b = create_app(base_interval_s=0.01)
    loop_b = app_b.config["AUREON_LOOP"]
    card_b = VaultContent.build(category="g", source_topic="app.b", payload={"who": "b"})
    loop_b.vault.add(card_b)
    app_b.testing = True
    mesh_b = app_b.config["AUREON_PHI_BRIDGE_MESH"]

    assert mesh_b is not mesh_a
    assert mesh_a.vault is loop_a.vault
    assert mesh_b.vault is loop_b.vault
    assert mesh_a.info()["total_cards_in"] == 7
    assert mesh_b.info()["total_cards_in"] == 0
    assert mesh_b.info()["gossip_cycles"] == 0

    response = app_b.test_client().post(
        "/api/bridge/cards",
        json={"from_peer_id": "app-a", "our_hashes": [], "cards": [card_a.to_dict()]},
        headers=AUTH,
    )

    assert response.status_code == 423
    assert card_b.harmonic_hash not in {item.harmonic_hash for item in loop_a.vault._contents.values()}
    assert card_a.harmonic_hash not in {item.harmonic_hash for item in loop_b.vault._contents.values()}
