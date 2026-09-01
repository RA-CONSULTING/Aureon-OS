"""
PhiBridgeMesh — P2P card-level gossip over the φ²-cadenced bridge
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Once PhiBridgeDiscovery has a directory of peers, the mesh runs a background
gossip loop that, on every φ² beat, iterates discovered peers and exchanges
actual vault cards (not just fingerprints). Each exchange:

  1. We compute the harmonic_hash set of everything we already have.
  2. We pick cards we've ingested since the last sync to this peer (capped
     at BATCH_LIMIT) and POST them to the peer's /api/bridge/cards endpoint.
  3. The peer's response carries back cards we don't have yet; we add each
     into our vault via vault.add() so memory converges across the mesh.

Conflict model: eventually-consistent union by harmonic_hash. Cards are
append-only once written (the vault already ring-evicts the oldest). A
card's hash is deterministic (category + source_topic + payload), so any
two nodes that independently observe the same event collapse to the same
id and never duplicate.

Transport is injectable so tests don't touch the network.

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.error import URLError
from urllib.request import Request, urlopen

from aureon.harmonic.phi_bridge import DEFAULT_BASE_INTERVAL_S, MIN_INTERVAL_S, PHI

logger = logging.getLogger("aureon.harmonic.phi_bridge_mesh")

PHI_MESH_RELEASE_HOLD = (
    "phi_bridge_mesh_hold:production_magic_star_release_unavailable"
)


BATCH_LIMIT: int = 64
HTTP_TIMEOUT_S: float = 2.0
CARDS_PATH: str = "/api/bridge/cards"


# ─────────────────────────────────────────────────────────────────────────────
# HTTP transport
# ─────────────────────────────────────────────────────────────────────────────


class HTTPPeerClient:
    """Real HTTP POST client. Swappable in tests."""

    def __init__(self, timeout: float = HTTP_TIMEOUT_S):
        self.timeout = float(timeout)

    def post_json(self, url: str, body: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError(PHI_MESH_RELEASE_HOLD)
        data = json.dumps(body, default=str).encode("utf-8")
        req = Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "aureon-phi-bridge/1"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except URLError as e:
            raise ConnectionError(f"POST {url} failed: {e}") from e
        try:
            return json.loads(raw) if raw else {}
        except Exception as e:
            raise ValueError(f"POST {url} returned non-JSON: {raw[:200]}") from e


# ─────────────────────────────────────────────────────────────────────────────
# Peer sync state
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class _PeerSync:
    last_sync_ts: float = 0.0
    last_error: str = ""
    cards_out: int = 0
    cards_in: int = 0
    exchanges: int = 0
    known_hashes: Set[str] = field(default_factory=set)


# ─────────────────────────────────────────────────────────────────────────────
# PhiBridgeMesh
# ─────────────────────────────────────────────────────────────────────────────


class _NullDiscovery:
    """No-op discovery used when the mesh is instantiated server-side for
    inbound exchange only (the Flask endpoint needs handle_inbound but
    does not need to enumerate peers for outbound gossip)."""

    peer_id: str = ""

    def known_peers(self) -> List[Any]:
        return []


class PhiBridgeMesh:
    """Card-level P2P gossip over the mesh discovered by PhiBridgeDiscovery."""

    def __init__(
        self,
        *,
        vault: Any,
        discovery: Any = None,
        bridge: Any = None,
        client: Optional[Any] = None,
        interval_s: Optional[float] = None,
        batch_limit: int = BATCH_LIMIT,
        cards_path: str = CARDS_PATH,
    ):
        self.vault = vault
        self.discovery = discovery if discovery is not None else _NullDiscovery()
        self.bridge = bridge
        self.client = client or HTTPPeerClient()
        self.interval_s = float(interval_s) if interval_s else None
        self.batch_limit = int(batch_limit)
        self.cards_path = str(cards_path)

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._peer_sync: Dict[str, _PeerSync] = {}
        self._total_out = 0
        self._total_in = 0
        self._gossip_cycles = 0

    # ─────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        raise RuntimeError(PHI_MESH_RELEASE_HOLD)
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, name="PhiBridgeMeshGossip", daemon=True,
        )
        self._thread.start()
        logger.info("PhiBridgeMesh: started")

    def stop(self) -> None:
        self._running = False
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    # ─────────────────────────────────────────────────────────────────────
    # Cadence
    # ─────────────────────────────────────────────────────────────────────

    def _current_interval(self) -> float:
        if self.interval_s is not None:
            return max(MIN_INTERVAL_S, self.interval_s)
        # Discovery enumeration can prune/mutate state in legacy providers.
        # The unreleased snapshot therefore reports the fixed base cadence.
        return max(MIN_INTERVAL_S, DEFAULT_BASE_INTERVAL_S)

    # ─────────────────────────────────────────────────────────────────────
    # Vault helpers
    # ─────────────────────────────────────────────────────────────────────

    def _our_hashes(self) -> Set[str]:
        """Every harmonic_hash our vault currently holds."""
        vault = self.vault
        if vault is None:
            return set()
        # Prefer an explicit API if the vault exposes one; fall back to _contents.
        getter = getattr(vault, "all_cards", None)
        if callable(getter):
            try:
                cards = list(getter())
            except Exception:
                cards = []
        else:
            contents = getattr(vault, "_contents", None)
            cards = list(contents.values()) if contents else []
        out: Set[str] = set()
        for c in cards:
            h = getattr(c, "harmonic_hash", "") or (c.get("harmonic_hash", "") if isinstance(c, dict) else "")
            if h:
                out.add(h)
        return out

    def _recent_cards(self, known_by_peer: Set[str], limit: int) -> List[Dict[str, Any]]:
        """Cards we have that the peer doesn't yet, newest first, capped."""
        vault = self.vault
        if vault is None:
            return []
        contents = getattr(vault, "_contents", None)
        cards_iter: List[Any]
        if contents:
            # AureonVault uses an OrderedDict insertion-ordered, newest last
            cards_iter = list(contents.values())[::-1]
        else:
            getter = getattr(vault, "all_cards", None)
            cards_iter = list(getter())[::-1] if callable(getter) else []

        out: List[Dict[str, Any]] = []
        for c in cards_iter:
            if len(out) >= limit:
                break
            h = getattr(c, "harmonic_hash", "")
            if not h or h in known_by_peer:
                continue
            to_dict = getattr(c, "to_dict", None)
            card_dict = to_dict() if callable(to_dict) else dict(c) if isinstance(c, dict) else {}
            if card_dict:
                out.append(card_dict)
        return out

    def _ingest_remote_card(self, card: Dict[str, Any]) -> bool:
        """Insert a card dict into the vault if we don't already have its hash."""
        if not isinstance(card, dict):
            return False
        h = str(card.get("harmonic_hash") or "")
        if not h:
            return False
        our_hashes = self._our_hashes()
        if h in our_hashes:
            return False
        # Rebuild a VaultContent so the vault's internal indices stay consistent.
        try:
            from aureon.vault.aureon_vault import VaultContent
            content = VaultContent(
                content_id=str(card.get("content_id") or "")[:16] or _short_id(),
                category=str(card.get("category") or "peer_card"),
                source_topic=str(card.get("source_topic") or "bridge.peer.card"),
                timestamp=float(card.get("timestamp") or time.time()),
                payload=dict(card.get("payload") or {}),
                harmonic_hash=h,
                love_weight=float(card.get("love_weight") or 0.0),
                gratitude_score=float(card.get("gratitude_score") or 0.0),
            )
        except Exception as e:
            logger.debug("PhiBridgeMesh: card rebuild failed: %s", e)
            return False
        adder = getattr(self.vault, "add", None)
        if not callable(adder):
            return False
        try:
            adder(content)
            return True
        except Exception as e:
            logger.debug("PhiBridgeMesh: vault.add failed: %s", e)
            return False

    # ─────────────────────────────────────────────────────────────────────
    # Exchange
    # ─────────────────────────────────────────────────────────────────────

    def build_payload_for(self, peer_id: str) -> Dict[str, Any]:
        """Build the outbound gossip payload for a given peer."""
        raise RuntimeError(PHI_MESH_RELEASE_HOLD)
        with self._lock:
            state = self._peer_sync.setdefault(peer_id, _PeerSync())
            known_by_peer = set(state.known_hashes)
        cards = self._recent_cards(known_by_peer, self.batch_limit)
        our_hashes = self._our_hashes()
        peer_id_self = getattr(self.discovery, "peer_id", "")
        fingerprint = ""
        try:
            if self.vault is not None and hasattr(self.vault, "fingerprint"):
                fingerprint = str(self.vault.fingerprint())
        except Exception:
            pass
        return {
            "from_peer_id": peer_id_self,
            "to_peer_id": peer_id,
            "fingerprint": fingerprint,
            "ts": time.time(),
            "our_hashes": sorted(our_hashes),
            "cards": cards,
        }

    def apply_response(self, peer_id: str, response: Dict[str, Any]) -> Dict[str, int]:
        """Ingest cards returned by a peer; update per-peer sync state."""
        raise RuntimeError(PHI_MESH_RELEASE_HOLD)
        cards = response.get("cards") or []
        peer_hashes = response.get("our_hashes") or []
        merged = 0
        for card in cards:
            if self._ingest_remote_card(card):
                merged += 1
        with self._lock:
            state = self._peer_sync.setdefault(peer_id, _PeerSync())
            state.last_sync_ts = time.time()
            state.cards_in += merged
            state.exchanges += 1
            if isinstance(peer_hashes, list):
                state.known_hashes = set(str(h) for h in peer_hashes)
            state.last_error = ""
        self._total_in += merged
        return {"cards_in": merged, "cards_total_in": self._total_in}

    def handle_inbound(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Apply an inbound payload from a peer and build our response.

        This is the server-side of the exchange — a node running an HTTP
        endpoint calls this and returns its output as JSON.
        """
        raise RuntimeError(PHI_MESH_RELEASE_HOLD)
        sender = str(payload.get("from_peer_id") or "")
        peer_hashes = payload.get("our_hashes") or []
        cards = payload.get("cards") or []
        merged = 0
        for card in cards:
            if self._ingest_remote_card(card):
                merged += 1
        known_by_peer = set(str(h) for h in peer_hashes)
        with self._lock:
            state = self._peer_sync.setdefault(sender or "unknown", _PeerSync())
            state.cards_in += merged
            state.known_hashes = known_by_peer
            state.last_sync_ts = time.time()
            state.exchanges += 1
        self._total_in += merged

        reply_cards = self._recent_cards(known_by_peer, self.batch_limit)
        our_hashes = self._our_hashes()
        self._total_out += len(reply_cards)
        with self._lock:
            state.cards_out += len(reply_cards)
        return {
            "ok": True,
            "from_peer_id": getattr(self.discovery, "peer_id", ""),
            "to_peer_id": sender,
            "cards_received": merged,
            "cards": reply_cards,
            "our_hashes": sorted(our_hashes),
            "ts": time.time(),
        }

    def gossip_to(self, peer: Any) -> Dict[str, Any]:
        """Exchange with one remote peer."""
        raise RuntimeError(PHI_MESH_RELEASE_HOLD)
        if isinstance(peer, dict):
            peer_id = str(peer.get("peer_id", ""))
            url_base = str(peer.get("url_base", ""))
        else:
            peer_id = str(getattr(peer, "peer_id", "") or "")
            url_base = str(getattr(peer, "url_base", "") or "")
        if not peer_id or not url_base:
            return {"ok": False, "error": "peer missing id or url_base"}
        payload = self.build_payload_for(peer_id)
        url = f"{url_base.rstrip('/')}{self.cards_path}"
        try:
            response = self.client.post_json(url, payload)
        except Exception as e:
            with self._lock:
                state = self._peer_sync.setdefault(peer_id, _PeerSync())
                state.last_error = str(e)
            logger.debug("PhiBridgeMesh: gossip to %s failed: %s", peer_id, e)
            return {"ok": False, "error": str(e)}
        with self._lock:
            state = self._peer_sync.setdefault(peer_id, _PeerSync())
            state.cards_out += len(payload["cards"])
        self._total_out += len(payload["cards"])
        merged_stats = self.apply_response(peer_id, response)
        return {"ok": True, "cards_out": len(payload["cards"]), **merged_stats}

    def gossip_once(self) -> Dict[str, Any]:
        """One pass over all discovered peers."""
        raise RuntimeError(PHI_MESH_RELEASE_HOLD)
        try:
            peers = self.discovery.known_peers()
        except Exception as e:
            return {"ok": False, "error": f"discovery failed: {e}", "peers": 0}
        results: Dict[str, Any] = {}
        for peer in peers:
            result = self.gossip_to(peer)
            pid = getattr(peer, "peer_id", "")
            results[pid] = result
        self._gossip_cycles += 1
        return {"ok": True, "peers": len(peers), "results": results, "cycle": self._gossip_cycles}

    # ─────────────────────────────────────────────────────────────────────
    # Loop
    # ─────────────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                self.gossip_once()
            except Exception as e:
                logger.debug("PhiBridgeMesh: gossip cycle failed: %s", e)
            time.sleep(self._current_interval())

    # ─────────────────────────────────────────────────────────────────────
    # Introspection
    # ─────────────────────────────────────────────────────────────────────

    def info(self) -> Dict[str, Any]:
        with self._lock:
            peers_info = {
                pid: {
                    "last_sync_ts": s.last_sync_ts,
                    "cards_out": s.cards_out,
                    "cards_in": s.cards_in,
                    "exchanges": s.exchanges,
                    "last_error": s.last_error,
                    "known_hashes_count": len(s.known_hashes),
                }
                for pid, s in self._peer_sync.items()
            }
        return {
            "ok": True,
            "service": "phi_bridge_mesh",
            "running": self._running,
            "interval_s": self._current_interval(),
            "gossip_cycles": self._gossip_cycles,
            "total_cards_out": self._total_out,
            "total_cards_in": self._total_in,
            "peers": peers_info,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _short_id() -> str:
    import uuid
    return uuid.uuid4().hex[:10]


_mesh_singleton: Optional[PhiBridgeMesh] = None
_mesh_lock = __import__("threading").Lock()


def get_phi_bridge_mesh(
    vault: Any = None,
    *,
    discovery: Any = None,
    client: Optional[Any] = None,
) -> PhiBridgeMesh:
    """Return the process-wide PhiBridgeMesh, creating it on first call.

    Used by the Flask server so the POST /api/bridge/cards handler talks
    to the same mesh any background gossip loop would use. Pass `vault`
    on the first call so handle_inbound can add received cards into the
    right vault; subsequent calls pick up the existing mesh.
    """
    global _mesh_singleton
    with _mesh_lock:
        if _mesh_singleton is None:
            _mesh_singleton = PhiBridgeMesh(
                vault=vault,
                discovery=discovery,
                client=client,
            )
        else:
            # Late-bind vault / discovery if they weren't known at first use.
            if vault is not None and _mesh_singleton.vault is None:
                _mesh_singleton.vault = vault
            if discovery is not None and isinstance(_mesh_singleton.discovery, _NullDiscovery):
                _mesh_singleton.discovery = discovery
        return _mesh_singleton


def reset_phi_bridge_mesh() -> None:
    """Drop the singleton — tests use this to start from a clean slate."""
    global _mesh_singleton
    with _mesh_lock:
        _mesh_singleton = None


__all__ = [
    "PhiBridgeMesh",
    "HTTPPeerClient",
    "BATCH_LIMIT",
    "CARDS_PATH",
    "get_phi_bridge_mesh",
    "reset_phi_bridge_mesh",
]
