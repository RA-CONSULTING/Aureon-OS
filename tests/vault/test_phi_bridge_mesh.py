"""Fail-closed contract for Phi card gossip and peer HTTP transport."""

from __future__ import annotations

import pytest

from aureon.harmonic.phi_bridge_mesh import HTTPPeerClient, PhiBridgeMesh


class GuardedVault:
    def add(self, *_args, **_kwargs):
        pytest.fail("mesh HOLD must not mutate vault")

    def recent(self, *_args, **_kwargs):
        pytest.fail("mesh HOLD must not disclose vault cards")

    def fingerprint(self):
        pytest.fail("mesh HOLD must not fingerprint vault for transfer")


class GuardedDiscovery:
    peer_id = "self"

    def known_peers(self):
        pytest.fail("mesh HOLD must not enumerate discovery peers")


class GuardedClient:
    def post_json(self, *_args, **_kwargs):
        pytest.fail("mesh HOLD must not perform peer HTTP")


def test_http_peer_client_holds_before_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon.harmonic import phi_bridge_mesh as mesh_module

    monkeypatch.setattr(
        mesh_module,
        "urlopen",
        lambda *_args, **_kwargs: pytest.fail("urlopen must not run"),
    )
    with pytest.raises(RuntimeError, match="phi_bridge_mesh_hold"):
        HTTPPeerClient().post_json("http://127.0.0.1/api/bridge/cards", {"cards": []})


def test_mesh_public_effects_hold_before_threads_network_or_vault(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aureon.harmonic import phi_bridge_mesh as mesh_module

    mesh = PhiBridgeMesh(
        vault=GuardedVault(),
        discovery=GuardedDiscovery(),
        client=GuardedClient(),
    )
    monkeypatch.setattr(
        mesh_module.threading,
        "Thread",
        lambda *_args, **_kwargs: pytest.fail("mesh HOLD must not create thread"),
    )
    effects = (
        mesh.start,
        lambda: mesh.build_payload_for("peer-a"),
        lambda: mesh.apply_response("peer-a", {"cards": []}),
        lambda: mesh.handle_inbound({"from_peer_id": "peer-a", "cards": []}),
        lambda: mesh.gossip_to({"peer_id": "peer-a", "url_base": "http://127.0.0.2"}),
        mesh.gossip_once,
    )

    for effect in effects:
        with pytest.raises(RuntimeError, match="phi_bridge_mesh_hold"):
            effect()

    assert mesh.info()["running"] is False
    assert mesh.info()["gossip_cycles"] == 0
    assert mesh.info()["total_cards_in"] == 0
    assert mesh.info()["total_cards_out"] == 0
    assert mesh.info()["peers"] == {}


def test_mesh_info_is_a_pure_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    mesh = PhiBridgeMesh(vault=None)
    monkeypatch.setattr(
        mesh,
        "_our_hashes",
        lambda: pytest.fail("info must not inspect vault contents"),
    )

    first = mesh.info()
    second = mesh.info()

    assert first == second
    assert first["running"] is False
