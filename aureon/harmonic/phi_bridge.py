"""
PhiBridge — φ²-cadenced device-to-device peer bridge for the Aureon vault.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The desktop runs the full vault. A second device (typically a phone on the
same WiFi) opens the mobile bridge page, gets a peer id, and starts a
bidirectional sync loop:

  phone  ──POST /api/bridge/sync (peer state) ──▶  desktop vault
  phone  ◀── desktop fingerprint + last utterance + cadence  ──── desktop

Each successful exchange is fed back into the vault as a ``bridge.peer``
card so every voice (Queen, Lover, Council, …) can see that an embodied
peer is currently coupled to the system.

The cadence is computed from φ² so that the two devices breathe at the
same harmonic interval that the rest of the system uses for coherence
gating. The actual interval scales with how many peers are coupled — more
peers means a slightly faster heartbeat, capped at a sane minimum.

This module is pure-Python, has no Flask dependency, and is unit-tested
in ``tests/vault/test_phi_bridge.py``. The Flask wiring lives in
``aureon/vault/ui/server.py``.
"""

from __future__ import annotations

import logging
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aureon.harmonic.phi_bridge")

PHI_BRIDGE_RELEASE_HOLD = (
    "phi_bridge_hold:production_magic_star_release_unavailable"
)


# φ and φ² — the same constants the rest of the harmonic stack uses.
PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
PHI_SQUARED: float = PHI * PHI  # ≈ 2.618033988…

# Default base cadence: PHI_SQUARED / φ⁴ ≈ 0.382 s (~2.618 Hz).
# The interval is still constructed out of φ so the breathing stays on
# the golden-ratio lattice, but this is fast enough for a live phone UI
# without hammering the LLM. MIN_INTERVAL_S floors at 100 ms so a flood
# of peers can still scale up without ever overrunning the server.
DEFAULT_BASE_INTERVAL_S: float = PHI_SQUARED / (PHI ** 4)  # ≈ 0.3820 s
MIN_INTERVAL_S: float = 0.1                                 # 10 Hz floor
MAX_INTERVAL_S: float = PHI_SQUARED * 4.0                   # ~10.5 s ceiling


# ─────────────────────────────────────────────────────────────────────────────
# Peer state
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class BridgePeer:
    """A device coupled to the desktop vault over the LAN."""

    peer_id: str
    label: str = "peer"
    kind: str = "phone"  # phone | tablet | desktop | other
    user_agent: str = ""
    remote_addr: str = ""
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    last_fingerprint: str = ""
    last_state: Dict[str, Any] = field(default_factory=dict)
    packets_in: int = 0
    packets_out: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peer_id": self.peer_id,
            "label": self.label,
            "kind": self.kind,
            "user_agent": self.user_agent[:200],
            "remote_addr": self.remote_addr,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "age_s": max(0.0, time.time() - self.first_seen),
            "idle_s": max(0.0, time.time() - self.last_seen),
            "last_fingerprint": self.last_fingerprint,
            "last_state": self.last_state,
            "packets_in": self.packets_in,
            "packets_out": self.packets_out,
        }


@dataclass
class BridgePacket:
    """One round-trip between desktop and a peer."""

    packet_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: float = field(default_factory=time.time)
    peer_id: str = ""
    direction: str = "in"  # in | out
    payload: Dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# PhiBridge
# ─────────────────────────────────────────────────────────────────────────────


class PhiBridge:
    """
    Manages peer pairings and the φ²-cadenced packet exchange.

    Usage::

        bridge = PhiBridge(vault=my_vault)
        peer_id, info = bridge.register_peer(label="ayman-pixel", kind="phone")
        result = bridge.exchange(peer_id, peer_state={"battery": 0.86})
    """

    def __init__(
        self,
        vault: Any = None,
        *,
        base_interval_s: float = DEFAULT_BASE_INTERVAL_S,
        peer_timeout_s: float = 60.0,
        max_history: int = 256,
    ):
        self.vault = vault
        self.base_interval_s = float(base_interval_s)
        self.peer_timeout_s = float(peer_timeout_s)
        self.max_history = int(max_history)

        self._peers: Dict[str, BridgePeer] = {}
        self._history: List[BridgePacket] = []
        self._lock = threading.RLock()
        self._created_at = time.time()
        self._total_in = 0
        self._total_out = 0
        self._live_state: Dict[str, Any] = {}  # pushed by ICS every tick

    # ─────────────────────────────────────────────────────────────────
    # Peer registration
    # ─────────────────────────────────────────────────────────────────

    def register_peer(
        self,
        *,
        label: str = "peer",
        kind: str = "phone",
        user_agent: str = "",
        remote_addr: str = "",
        peer_id: Optional[str] = None,
    ) -> BridgePeer:
        """
        Create or refresh a peer. If ``peer_id`` is given and already known,
        the existing peer is returned with ``last_seen`` bumped.
        """
        raise RuntimeError(PHI_BRIDGE_RELEASE_HOLD)
        with self._lock:
            self._sweep_locked()
            if peer_id and peer_id in self._peers:
                peer = self._peers[peer_id]
                peer.last_seen = time.time()
                if user_agent:
                    peer.user_agent = user_agent
                if remote_addr:
                    peer.remote_addr = remote_addr
                return peer

            new_id = peer_id or uuid.uuid4().hex[:12]
            peer = BridgePeer(
                peer_id=new_id,
                label=str(label or "peer")[:40],
                kind=str(kind or "phone")[:20],
                user_agent=str(user_agent or "")[:300],
                remote_addr=str(remote_addr or "")[:64],
            )
            self._peers[new_id] = peer
            logger.info(
                "PhiBridge: peer registered id=%s label=%s kind=%s addr=%s",
                new_id,
                peer.label,
                peer.kind,
                peer.remote_addr,
            )
            self._feedback_card(
                "bridge.peer.joined",
                {
                    "peer_id": new_id,
                    "label": peer.label,
                    "kind": peer.kind,
                    "remote_addr": peer.remote_addr,
                },
            )
            return peer

    def drop_peer(self, peer_id: str) -> bool:
        raise RuntimeError(PHI_BRIDGE_RELEASE_HOLD)
        with self._lock:
            peer = self._peers.pop(peer_id, None)
            if peer is None:
                return False
            logger.info("PhiBridge: peer dropped id=%s label=%s", peer_id, peer.label)
            self._feedback_card(
                "bridge.peer.dropped",
                {"peer_id": peer_id, "label": peer.label},
            )
            return True

    def peers(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [p.to_dict() for p in self._peers.values()]

    def peer_count(self) -> int:
        with self._lock:
            return len(self._peers)

    # ─────────────────────────────────────────────────────────────────
    # Cadence
    # ─────────────────────────────────────────────────────────────────

    def cadence(self) -> Dict[str, float]:
        """
        Current φ²-derived heartbeat for the bridge.

        With one peer the interval is ``base_interval_s`` (≈ φ² seconds).
        Each additional peer divides the interval by φ, asymptotically
        approaching ``MIN_INTERVAL_S``.
        """
        n = max(1, self.peer_count())
        interval = self.base_interval_s / (PHI ** (n - 1))
        interval = max(MIN_INTERVAL_S, min(MAX_INTERVAL_S, interval))
        return {
            "phi": PHI,
            "phi_squared": PHI_SQUARED,
            "base_interval_s": self.base_interval_s,
            "interval_s": interval,
            "frequency_hz": 1.0 / interval,
            "peer_count": n if self.peer_count() > 0 else 0,
        }

    # ─────────────────────────────────────────────────────────────────
    # Sync exchange
    # ─────────────────────────────────────────────────────────────────

    def exchange(
        self,
        peer_id: str,
        *,
        peer_state: Optional[Dict[str, Any]] = None,
        peer_fingerprint: str = "",
    ) -> Dict[str, Any]:
        """
        One round-trip sync. Records the inbound peer state, returns the
        current desktop view + cadence so the peer knows when to call back.
        """
        raise RuntimeError(PHI_BRIDGE_RELEASE_HOLD)
        peer_state = dict(peer_state or {})
        with self._lock:
            self._sweep_locked()
            peer = self._peers.get(peer_id)
            if peer is None:
                # Auto-register on first sync so a phone that lost its
                # peer_id (cleared cookies / restarted) can re-couple.
                peer = self.register_peer(
                    label=str(peer_state.get("label") or "peer"),
                    kind=str(peer_state.get("kind") or "phone"),
                    peer_id=peer_id,
                )

            now = time.time()
            peer.last_seen = now
            peer.last_state = peer_state
            peer.last_fingerprint = peer_fingerprint
            peer.packets_in += 1
            self._total_in += 1
            self._record(BridgePacket(
                peer_id=peer.peer_id,
                direction="in",
                payload=peer_state,
            ))

            # Feed peer state back into the vault so the voices can see it.
            self._feedback_card(
                "bridge.peer.state",
                {
                    "peer_id": peer.peer_id,
                    "label": peer.label,
                    "kind": peer.kind,
                    "fingerprint": peer_fingerprint,
                    "state": peer_state,
                },
            )

            # Build the response.
            desktop_view = self._build_desktop_view()
            cadence = self.cadence()
            response = {
                "ok": True,
                "peer_id": peer.peer_id,
                "server_time": now,
                "cadence": cadence,
                "desktop": desktop_view,
                "echo": {
                    "fingerprint": peer_fingerprint,
                    "received_keys": sorted(peer_state.keys()),
                },
            }

            peer.packets_out += 1
            self._total_out += 1
            self._record(BridgePacket(
                peer_id=peer.peer_id,
                direction="out",
                payload={"fingerprint": desktop_view.get("fingerprint", "")},
            ))
            return response

    # ─────────────────────────────────────────────────────────────────
    # Status / introspection
    # ─────────────────────────────────────────────────────────────────

    def info(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "service": "phi_bridge",
                "created_at": self._created_at,
                "uptime_s": max(0.0, time.time() - self._created_at),
                "peer_count": len(self._peers),
                "peers": [p.to_dict() for p in self._peers.values()],
                "cadence": self.cadence(),
                "totals": {"packets_in": self._total_in, "packets_out": self._total_out},
                "desktop": self._build_desktop_view(),
            }

    def history(self, n: int = 32) -> List[Dict[str, Any]]:
        with self._lock:
            tail = self._history[-int(max(1, n)):]
            return [
                {
                    "packet_id": p.packet_id,
                    "timestamp": p.timestamp,
                    "peer_id": p.peer_id,
                    "direction": p.direction,
                    "payload": p.payload,
                }
                for p in tail
            ]

    # ─────────────────────────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────────────────────────

    def push_state(self, state: Dict[str, Any]) -> None:
        """ICS calls this every ~5s to keep the bridge view current with live Queen state."""
        raise RuntimeError(PHI_BRIDGE_RELEASE_HOLD)
        with self._lock:
            self._live_state.update(state)

    def _sweep_locked(self) -> None:
        if self.peer_timeout_s <= 0:
            return
        now = time.time()
        stale = [pid for pid, p in self._peers.items() if (now - p.last_seen) > self.peer_timeout_s]
        for pid in stale:
            peer = self._peers.pop(pid, None)
            if peer is None:
                continue
            logger.info("PhiBridge: peer timeout id=%s label=%s", pid, peer.label)
            self._feedback_card(
                "bridge.peer.timeout",
                {"peer_id": pid, "label": peer.label, "idle_s": now - peer.last_seen},
            )

    def _record(self, packet: BridgePacket) -> None:
        self._history.append(packet)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

    def _build_desktop_view(self) -> Dict[str, Any]:
        view: Dict[str, Any] = {
            "fingerprint": "",
            "love_amplitude": None,
            "gratitude_score": None,
            "dominant_chakra": None,
            "card_count": 0,
            "last_utterance": None,
        }
        # Merge live Queen state pushed by ICS (mood, cycle, lambda, position, etc.)
        with self._lock:
            view.update(self._live_state)
        vault = self.vault
        if vault is None:
            return view
        try:
            if hasattr(vault, "fingerprint"):
                view["fingerprint"] = str(vault.fingerprint())
        except Exception:
            pass
        for attr in ("love_amplitude", "gratitude_score", "dominant_chakra"):
            try:
                view[attr] = getattr(vault, attr, None)
            except Exception:
                view[attr] = None
        try:
            view["card_count"] = int(len(vault))
        except Exception:
            view["card_count"] = 0
        # Last utterance is best-effort: the SelfFeedbackLoop or UI server
        # may attach a `voice_engine` to the vault. We try the most common
        # locations without taking a hard dependency.
        try:
            engine = getattr(vault, "_voice_engine", None) or getattr(vault, "voice_engine", None)
            if engine is not None and hasattr(engine, "_history") and engine._history:
                # Walk backwards until we find a healthy utterance — skip
                # any where the text is an adapter error string so the phone
                # never sees "[ERROR] HTTPConnectionPool..." as the vault
                # speaking.
                for u in reversed(list(engine._history)[-8:]):
                    text = (
                        getattr(getattr(u, "response", None), "text", "")
                        or getattr(getattr(u, "statement", None), "text", "")
                        or ""
                    )
                    if not text:
                        continue
                    if text.startswith("[ERROR]") or "timed out" in text.lower():
                        continue
                    view["last_utterance"] = {
                        "speaker": getattr(u, "speaker", ""),
                        "listener": getattr(u, "listener", ""),
                        "text": text[:400],
                    }
                    break
        except Exception:
            pass
        return view

    def _feedback_card(self, topic: str, payload: Dict[str, Any]) -> None:
        if self.vault is None or not hasattr(self.vault, "ingest"):
            return
        try:
            self.vault.ingest(topic=topic, payload=payload, category="bridge_peer")
        except Exception as e:
            logger.debug("PhiBridge feedback card failed: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton helper (used by the Flask server)
# ─────────────────────────────────────────────────────────────────────────────


_bridge_singleton: Optional[PhiBridge] = None
_bridge_lock = threading.Lock()


def get_phi_bridge(vault: Any = None) -> PhiBridge:
    """
    Return a process-wide PhiBridge instance, creating it on first call.

    The Flask server uses this so every request handler talks to the same
    bridge regardless of how the loop was wired up.
    """
    global _bridge_singleton
    with _bridge_lock:
        if _bridge_singleton is None:
            _bridge_singleton = PhiBridge(vault=vault)
        elif vault is not None and _bridge_singleton.vault is None:
            _bridge_singleton.vault = vault
        return _bridge_singleton


def reset_phi_bridge() -> None:
    """Drop the singleton — used by tests to start from a clean slate."""
    global _bridge_singleton
    with _bridge_lock:
        _bridge_singleton = None
