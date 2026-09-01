from __future__ import annotations

import base64
import json
import threading
from typing import Any, Optional

import pytest

pytest.importorskip("flask")

from aureon.harmonic.phi_bridge_discovery import PhiBridgeDiscovery
from aureon.vault.ui.server import VAULT_UI_AUTH_ENV, create_app


TOKEN = "vault-ui-discovery-test-" + ("D" * 48)
HNC_KEY = base64.urlsafe_b64encode(b"D" * 32).decode().rstrip("=")
AUTH = {"Authorization": f"Bearer {TOKEN}"}


class _StubTransport:
    def __init__(self) -> None:
        self.sent: list[bytes] = []
        self.inbox: list[tuple[bytes, tuple[str, int]]] = []
        self._lock = threading.Lock()
        self.open_calls = 0

    def open(self) -> None:
        self.open_calls += 1

    def close(self) -> None:
        return None

    def send(self, data: bytes) -> None:
        self.sent.append(bytes(data))

    def recv(self) -> Optional[tuple[bytes, tuple[str, int]]]:
        return self.inbox.pop(0) if self.inbox else None

    def feed(self, packet: Any) -> None:
        self.inbox.append((json.dumps(packet).encode(), ("10.0.0.9", 26181)))


@pytest.fixture
def guarded_app(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(VAULT_UI_AUTH_ENV, TOKEN)
    monkeypatch.setenv("AUREON_HNC_PACKET_MASTER_KEY", HNC_KEY)
    transport = _StubTransport()
    discovery = PhiBridgeDiscovery(
        peer_id="self-app",
        host="10.0.0.1",
        port=8000,
        label="self",
        kind="desktop",
        transport=transport,
        interval_s=0.05,
        peer_timeout_s=30.0,
    )
    with pytest.raises(RuntimeError, match="supplied_mesh_discovery_forbidden"):
        create_app(mesh_discovery=discovery, mesh_port=8000)
    app = create_app(base_interval_s=0.01)
    app.testing = True
    yield app, app.test_client(), discovery, transport
    discovery.stop()


def test_injected_discovery_is_rejected_and_app_mesh_is_inert(guarded_app) -> None:
    app, _client, discovery, transport = guarded_app
    mesh = app.config["AUREON_PHI_BRIDGE_MESH"]

    assert discovery.announce_count == 0
    assert transport.open_calls == 0
    assert transport.sent == []
    assert mesh.info()["running"] is False
    assert app.config["AUREON_PHI_BRIDGE_DISCOVERY"] is None


def test_unprocessed_announcement_cannot_become_ssrf_peer(guarded_app) -> None:
    _app, client, discovery, transport = guarded_app
    transport.feed({
        "aureon": "untrusted",
        "peer_id": "attacker",
        "host": "169.254.169.254",
        "port": 80,
    })

    response = client.get("/api/bridge/discovery/peers", headers=AUTH)
    body = response.get_json()

    assert response.status_code == 200
    assert body["running"] is False
    assert body["status"] == "HOLD"
    assert body["peers"] == []
    assert discovery.known_peers() == []
    assert transport.sent == []
