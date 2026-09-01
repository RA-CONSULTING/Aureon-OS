"""Fail-closed contract for the unreleased PhiBridge effect owner."""

from __future__ import annotations

import time

import pytest

from aureon.harmonic.phi_bridge import BridgePeer, PhiBridge


class GuardedVault:
    def ingest(self, *_args, **_kwargs):
        pytest.fail("PhiBridge HOLD must not ingest a vault card")

    def fingerprint(self) -> str:
        return "snapshot"

    def __len__(self) -> int:
        return 0


def test_constructor_is_inert_and_public_mutators_hold() -> None:
    bridge = PhiBridge(vault=GuardedVault())

    effect_calls = (
        lambda: bridge.register_peer(peer_id="peer-a"),
        lambda: bridge.drop_peer("peer-a"),
        lambda: bridge.exchange("peer-a", peer_state={"hostile": True}),
        lambda: bridge.push_state({"hostile": True}),
    )
    for effect in effect_calls:
        with pytest.raises(RuntimeError, match="phi_bridge_hold"):
            effect()

    assert bridge._peers == {}
    assert bridge._history == []
    assert bridge._live_state == {}
    assert bridge._total_in == 0
    assert bridge._total_out == 0


def test_public_reads_are_pure_and_do_not_sweep_or_write(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = PhiBridge(vault=GuardedVault(), peer_timeout_s=0.001)
    stale = BridgePeer(peer_id="stale", last_seen=time.time() - 1000)
    bridge._peers[stale.peer_id] = stale
    monkeypatch.setattr(
        bridge,
        "_sweep_locked",
        lambda: pytest.fail("read path must not perform cleanup mutation"),
    )

    assert bridge.peer_count() == 1
    assert [peer["peer_id"] for peer in bridge.peers()] == ["stale"]
    assert bridge.cadence()["peer_count"] == 1
    assert bridge.info()["peer_count"] == 1
    assert bridge.history() == []
    assert "stale" in bridge._peers
