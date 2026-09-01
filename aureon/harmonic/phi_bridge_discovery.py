"""
PhiBridgeDiscovery — LAN peer discovery over UDP broadcast
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every Aureon node (phone, tablet, desktop) announces itself on the local
network at the φ²-derived cadence. Every node listens to the same port and
builds a directory of visible peers. This is what turns the PhiBridge from
"phone → one desktop" into a real mesh: any node can enumerate peers and
open a direct sync link to any other node.

Transport is a tiny abstraction so tests can drive the protocol without
binding real sockets.

Wire format (JSON, UTF-8, one packet per datagram, <= 1024 bytes):

    {
      "aureon": "phi_bridge_announce",
      "ver": 1,
      "peer_id": "4a8b…",
      "host":    "192.168.1.42",
      "port":    8765,
      "label":   "tina-macbook",
      "kind":    "desktop",
      "fingerprint": "abc123…",
      "ts":      1747512345.123
    }

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from aureon.harmonic.phi_bridge import DEFAULT_BASE_INTERVAL_S, MIN_INTERVAL_S, PHI

logger = logging.getLogger("aureon.harmonic.phi_bridge_discovery")

PHI_RELEASE_HOLD = (
    "phi_bridge_discovery_hold:production_magic_star_release_unavailable"
)

DEFAULT_PORT: int = 26181
MAX_PACKET_BYTES: int = 1024
ANNOUNCE_MAGIC: str = "phi_bridge_announce"
PROTO_VER: int = 1


# ─────────────────────────────────────────────────────────────────────────────
# Data
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class RemotePeer:
    """A peer we learned about from a UDP announcement."""

    peer_id: str
    host: str
    port: int
    label: str = "peer"
    kind: str = "desktop"
    fingerprint: str = ""
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    @property
    def url_base(self) -> str:
        return f"http://{self.host}:{self.port}"

    def to_dict(self) -> Dict[str, Any]:
        now = time.time()
        return {
            "peer_id": self.peer_id,
            "host": self.host,
            "port": self.port,
            "label": self.label,
            "kind": self.kind,
            "fingerprint": self.fingerprint,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "age_s": max(0.0, now - self.first_seen),
            "idle_s": max(0.0, now - self.last_seen),
            "url_base": self.url_base,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Transport abstraction
# ─────────────────────────────────────────────────────────────────────────────


class UDPBroadcastTransport:
    """Real UDP broadcast transport. Sends to 255.255.255.255, listens on DEFAULT_PORT."""

    def __init__(self, port: int = DEFAULT_PORT, broadcast_addr: str = "255.255.255.255"):
        self.port = int(port)
        self.broadcast_addr = str(broadcast_addr)
        self._send_sock: Optional[socket.socket] = None
        self._recv_sock: Optional[socket.socket] = None

    def open(self) -> None:
        raise RuntimeError(PHI_RELEASE_HOLD)
        if self._send_sock is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._send_sock = s
        if self._recv_sock is None:
            r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            r.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                r.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                pass
            r.bind(("", self.port))
            r.settimeout(0.25)
            self._recv_sock = r

    def send(self, data: bytes) -> None:
        raise RuntimeError(PHI_RELEASE_HOLD)
        if self._send_sock is None:
            self.open()
        assert self._send_sock is not None
        self._send_sock.sendto(data, (self.broadcast_addr, self.port))

    def recv(self) -> Optional[Tuple[bytes, Tuple[str, int]]]:
        raise RuntimeError(PHI_RELEASE_HOLD)
        if self._recv_sock is None:
            self.open()
        assert self._recv_sock is not None
        try:
            data, addr = self._recv_sock.recvfrom(MAX_PACKET_BYTES)
            return data, addr
        except socket.timeout:
            return None
        except OSError:
            return None

    def close(self) -> None:
        for s in (self._send_sock, self._recv_sock):
            try:
                if s is not None:
                    s.close()
            except Exception:
                pass
        self._send_sock = None
        self._recv_sock = None


# ─────────────────────────────────────────────────────────────────────────────
# PhiBridgeDiscovery
# ─────────────────────────────────────────────────────────────────────────────


class PhiBridgeDiscovery:
    """Announce our presence and listen for other peers on the LAN."""

    def __init__(
        self,
        *,
        peer_id: Optional[str] = None,
        host: str = "",
        port: int = 0,
        label: str = "aureon",
        kind: str = "desktop",
        fingerprint_fn: Optional[Callable[[], str]] = None,
        transport: Optional[Any] = None,
        interval_s: float = DEFAULT_BASE_INTERVAL_S * PHI * PHI,  # slower than sync
        peer_timeout_s: float = 30.0,
        on_peer_seen: Optional[Callable[[RemotePeer], None]] = None,
    ):
        self.peer_id = peer_id or uuid.uuid4().hex[:12]
        self.host = str(host or "").strip() or "127.0.0.1"
        self.port = int(port)
        self.label = str(label)
        self.kind = str(kind)
        self._fingerprint_fn = fingerprint_fn or (lambda: "")
        self.transport = transport or UDPBroadcastTransport()
        self.interval_s = max(MIN_INTERVAL_S, float(interval_s))
        self.peer_timeout_s = float(peer_timeout_s)
        self._on_peer_seen = on_peer_seen

        self._peers: Dict[str, RemotePeer] = {}
        self._lock = threading.RLock()
        self._running = False
        self._announce_thread: Optional[threading.Thread] = None
        self._listen_thread: Optional[threading.Thread] = None
        self._announce_count = 0
        self._recv_count = 0

    # ─────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        raise RuntimeError(PHI_RELEASE_HOLD)
        if self._running:
            return
        self._running = True
        if hasattr(self.transport, "open"):
            try:
                self.transport.open()
            except Exception as e:
                logger.warning("PhiBridgeDiscovery: transport open failed: %s", e)
                self._running = False
                return
        self._announce_thread = threading.Thread(
            target=self._announce_loop, name="PhiBridgeDiscoveryAnnounce", daemon=True,
        )
        self._listen_thread = threading.Thread(
            target=self._listen_loop, name="PhiBridgeDiscoveryListen", daemon=True,
        )
        self._announce_thread.start()
        self._listen_thread.start()
        logger.info(
            "PhiBridgeDiscovery: started id=%s host=%s port=%d interval=%.3fs",
            self.peer_id, self.host, self.port, self.interval_s,
        )

    def stop(self) -> None:
        self._running = False
        for t in (self._announce_thread, self._listen_thread):
            if t is not None and t.is_alive():
                t.join(timeout=2.0)
        if hasattr(self.transport, "close"):
            try:
                self.transport.close()
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────
    # Protocol
    # ─────────────────────────────────────────────────────────────────────

    def build_announcement(self) -> Dict[str, Any]:
        raise RuntimeError(PHI_RELEASE_HOLD)
        try:
            fp = str(self._fingerprint_fn() or "")
        except Exception:
            fp = ""
        return {
            "aureon": ANNOUNCE_MAGIC,
            "ver": PROTO_VER,
            "peer_id": self.peer_id,
            "host": self.host,
            "port": self.port,
            "label": self.label,
            "kind": self.kind,
            "fingerprint": fp,
            "ts": time.time(),
        }

    def announce_once(self) -> bool:
        raise RuntimeError(PHI_RELEASE_HOLD)
        data = json.dumps(self.build_announcement(), separators=(",", ":")).encode("utf-8")
        if len(data) > MAX_PACKET_BYTES:
            logger.warning("PhiBridgeDiscovery: announcement truncated (%d bytes)", len(data))
            return False
        try:
            self.transport.send(data)
            self._announce_count += 1
            return True
        except Exception as e:
            logger.debug("PhiBridgeDiscovery: send failed: %s", e)
            return False

    def record_announcement(
        self, packet: Dict[str, Any], source_addr: Optional[Tuple[str, int]] = None,
    ) -> Optional[RemotePeer]:
        """Parse an announcement dict and update the peer table.

        Public so tests and higher layers can drive the state machine
        directly without a real socket.
        """
        raise RuntimeError(PHI_RELEASE_HOLD)
        if not isinstance(packet, dict):
            return None
        if packet.get("aureon") != ANNOUNCE_MAGIC:
            return None
        try:
            if int(packet.get("ver", 0)) != PROTO_VER:
                return None
        except (TypeError, ValueError):
            return None

        peer_id = str(packet.get("peer_id") or "")
        if not peer_id or peer_id == self.peer_id:
            return None  # ignore our own echoes

        host = str(packet.get("host") or "")
        if not host and source_addr:
            host = source_addr[0]
        try:
            port = int(packet.get("port") or 0)
        except (TypeError, ValueError):
            port = 0

        now = time.time()
        with self._lock:
            peer = self._peers.get(peer_id)
            if peer is None:
                peer = RemotePeer(
                    peer_id=peer_id,
                    host=host,
                    port=port,
                    label=str(packet.get("label") or "peer"),
                    kind=str(packet.get("kind") or "desktop"),
                    fingerprint=str(packet.get("fingerprint") or ""),
                    first_seen=now,
                    last_seen=now,
                )
                self._peers[peer_id] = peer
                logger.info(
                    "PhiBridgeDiscovery: new peer id=%s label=%s host=%s:%d",
                    peer_id, peer.label, host, port,
                )
                if self._on_peer_seen:
                    try:
                        self._on_peer_seen(peer)
                    except Exception as e:
                        logger.debug("PhiBridgeDiscovery: on_peer_seen failed: %s", e)
            else:
                peer.last_seen = now
                if host:
                    peer.host = host
                if port:
                    peer.port = port
                peer.label = str(packet.get("label") or peer.label)
                peer.fingerprint = str(packet.get("fingerprint") or peer.fingerprint)
        self._recv_count += 1
        return peer

    # ─────────────────────────────────────────────────────────────────────
    # Loops
    # ─────────────────────────────────────────────────────────────────────

    def _announce_loop(self) -> None:
        while self._running:
            self.announce_once()
            time.sleep(self.interval_s)

    def _listen_loop(self) -> None:
        while self._running:
            try:
                pkt = self.transport.recv()
            except Exception as e:
                logger.debug("PhiBridgeDiscovery: recv failed: %s", e)
                time.sleep(self.interval_s)
                continue
            if pkt is None:
                continue
            data, addr = pkt
            try:
                msg = json.loads(data.decode("utf-8"))
            except Exception:
                continue
            self.record_announcement(msg, source_addr=addr)
            self._sweep_stale()

    def _sweep_stale(self) -> None:
        if self.peer_timeout_s <= 0:
            return
        now = time.time()
        with self._lock:
            stale = [pid for pid, p in self._peers.items() if (now - p.last_seen) > self.peer_timeout_s]
            for pid in stale:
                del self._peers[pid]

    # ─────────────────────────────────────────────────────────────────────
    # Introspection
    # ─────────────────────────────────────────────────────────────────────

    def known_peers(self) -> List[RemotePeer]:
        with self._lock:
            return list(self._peers.values())

    def known_peers_dict(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self.known_peers()]

    @property
    def announce_count(self) -> int:
        return self._announce_count

    @property
    def recv_count(self) -> int:
        return self._recv_count


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _detect_host() -> str:
    """Network-inert compatibility helper."""

    return "127.0.0.1"


__all__ = [
    "RemotePeer",
    "UDPBroadcastTransport",
    "PhiBridgeDiscovery",
    "DEFAULT_PORT",
    "ANNOUNCE_MAGIC",
    "PROTO_VER",
]
