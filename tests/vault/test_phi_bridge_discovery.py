"""Fail-closed contract for Phi LAN discovery and UDP transport."""

from __future__ import annotations

import time

import pytest

from aureon.harmonic.phi_bridge_discovery import (
    ANNOUNCE_MAGIC,
    PROTO_VER,
    PhiBridgeDiscovery,
    RemotePeer,
    UDPBroadcastTransport,
)


class GuardedTransport:
    def __init__(self) -> None:
        self.close_calls = 0

    def open(self) -> None:
        pytest.fail("discovery HOLD must not open transport")

    def send(self, _data: bytes) -> None:
        pytest.fail("discovery HOLD must not send")

    def recv(self):
        pytest.fail("discovery HOLD must not receive")

    def close(self) -> None:
        self.close_calls += 1


def test_udp_transport_effects_hold_before_socket_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aureon.harmonic import phi_bridge_discovery as discovery_module

    monkeypatch.setattr(
        discovery_module.socket,
        "socket",
        lambda *_args, **_kwargs: pytest.fail("socket must not be created"),
    )
    transport = UDPBroadcastTransport()

    for effect in (transport.open, lambda: transport.send(b"x"), transport.recv):
        with pytest.raises(RuntimeError, match="phi_bridge_discovery_hold"):
            effect()


def test_discovery_constructor_defaults_to_loopback_without_network_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aureon.harmonic import phi_bridge_discovery as discovery_module

    monkeypatch.setattr(
        discovery_module.socket,
        "socket",
        lambda *_args, **_kwargs: pytest.fail("constructor must not probe network"),
    )

    discovery = PhiBridgeDiscovery(transport=GuardedTransport())

    assert discovery.host == "127.0.0.1"


def test_discovery_start_and_protocol_mutators_hold_without_threads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aureon.harmonic import phi_bridge_discovery as discovery_module

    transport = GuardedTransport()
    discovery = PhiBridgeDiscovery(
        peer_id="self",
        host="127.0.0.1",
        port=8000,
        transport=transport,
    )
    monkeypatch.setattr(
        discovery_module.threading,
        "Thread",
        lambda *_args, **_kwargs: pytest.fail("discovery HOLD must not create threads"),
    )
    packet = {
        "aureon": ANNOUNCE_MAGIC,
        "ver": PROTO_VER,
        "peer_id": "peer-a",
        "host": "127.0.0.2",
        "port": 8001,
    }

    effects = (
        discovery.start,
        discovery.build_announcement,
        discovery.announce_once,
        lambda: discovery.record_announcement(packet),
    )
    for effect in effects:
        with pytest.raises(RuntimeError, match="phi_bridge_discovery_hold"):
            effect()

    assert discovery._running is False
    assert discovery.known_peers() == []
    assert discovery.announce_count == 0
    assert discovery.recv_count == 0


def test_peer_reads_do_not_prune_or_invoke_callbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    discovery = PhiBridgeDiscovery(peer_timeout_s=0.001, transport=GuardedTransport())
    stale = RemotePeer(
        peer_id="stale",
        host="127.0.0.2",
        port=8001,
        last_seen=time.time() - 1000,
    )
    discovery._peers[stale.peer_id] = stale
    monkeypatch.setattr(
        discovery,
        "_sweep_stale",
        lambda: pytest.fail("read path must not mutate peer state"),
    )

    assert [peer.peer_id for peer in discovery.known_peers()] == ["stale"]
    assert [peer["peer_id"] for peer in discovery.known_peers_dict()] == ["stale"]
    assert "stale" in discovery._peers
