"""
AffinityChorus — many thoughts, one unified softmax
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CURRENT RELEASE: local contribution math remains available, while ThoughtBus
subscription/publication and PersonaVacuum chorus wiring hard-HOLD until the
production Magic Star release is available.

Each PersonaVacuum ordinarily samples from its OWN local affinity vector —
ten numbers, one per persona, derived from the vault slice + cognition
snapshot + DJ drop at the moment of observation. Two vacuums on the same
bus (or two machines on the same LAN) would each sample independently,
and might collapse to different personas even with identical state.

The AffinityChorus merges contributions so the collapse is collective:

    peer A's local affinity:    {mystic: 2.3, engineer: 0.8, ...}
    peer B's local affinity:    {mystic: 1.9, engineer: 1.1, ...}
    merged affinity (sum):      {mystic: 4.2, engineer: 1.9, ...}
                                      ↓
                               softmax → one winner

Each peer still publishes its own vector as its "thought". The softmax
operates over the merged vector so the system selects one persona —
"many thoughts, one unified speech". Combined with a shared deterministic
seed (e.g. derived from the shared vault fingerprint), two vacuums with
the same merged affinity will sample the exact same winner.

Contributions carry a ``peer_id`` so duplicate updates from the same peer
overwrite rather than double-count. A time-to-live prunes stale entries,
so a peer that goes silent fades out of the consensus.

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aureon.vault.voice.affinity_chorus")


AFFINITY_CHORUS_RELEASE_HOLD = (
    "affinity_chorus_hold:production_magic_star_release_unavailable"
)

_CHORUS_TOPIC: str = "persona.affinity"
DEFAULT_TTL_S: float = 5.0


# ─────────────────────────────────────────────────────────────────────────────
# Data
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class AffinityContribution:
    """One peer's current per-persona affinity vector."""

    peer_id: str
    scores: Dict[str, float]
    ts: float = field(default_factory=time.time)

    def to_payload(self) -> Dict[str, Any]:
        return {
            "peer_id": self.peer_id,
            "scores": dict(self.scores),
            "ts": self.ts,
        }


# ─────────────────────────────────────────────────────────────────────────────
# AffinityChorus
# ─────────────────────────────────────────────────────────────────────────────


class AffinityChorus:
    """Aggregates per-peer affinity vectors into one merged score map.

    Subscribes to the `persona.affinity` topic on a ThoughtBus if one is
    given, so peer contributions land automatically. Use `add()` directly
    for tests or for piping in contributions from cross-machine transports.
    """

    TOPIC: str = _CHORUS_TOPIC

    def __init__(
        self,
        thought_bus: Any = None,
        *,
        ttl_s: float = DEFAULT_TTL_S,
        weight_self: float = 1.0,
    ):
        self.thought_bus = thought_bus
        self.ttl_s = float(ttl_s)
        self.weight_self = float(weight_self)
        self._lock = threading.RLock()
        self._contributions: Dict[str, AffinityContribution] = {}
        self._subscribed = False

    # ─── wiring ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Attach to the bus if one is present. Safe to call twice."""
        raise RuntimeError(AFFINITY_CHORUS_RELEASE_HOLD)
        if self._subscribed or self.thought_bus is None:
            return
        try:
            self.thought_bus.subscribe(self.TOPIC, self._on_publication)
            self._subscribed = True
        except Exception as e:
            logger.debug("AffinityChorus: subscribe failed: %s", e)

    def _on_publication(self, thought: Any) -> None:
        payload = getattr(thought, "payload", {}) or {}
        if not isinstance(payload, dict):
            return
        peer_id = str(payload.get("peer_id") or "").strip()
        scores_raw = payload.get("scores") or {}
        if not peer_id or not isinstance(scores_raw, dict):
            return
        try:
            scores = {str(k): float(v) for k, v in scores_raw.items()}
        except (TypeError, ValueError):
            return
        self.add(peer_id=peer_id, scores=scores,
                 ts=float(payload.get("ts") or time.time()))

    # ─── direct contribution api ─────────────────────────────────────────

    def add(
        self,
        peer_id: str,
        scores: Dict[str, float],
        ts: Optional[float] = None,
    ) -> None:
        """Record or replace a peer's current affinity vector.

        Empty score maps are rejected — an "empty thought" shouldn't
        count as a peer in the consensus.
        """
        if not peer_id or not scores:
            return
        ts = float(ts) if ts is not None else time.time()
        with self._lock:
            self._contributions[peer_id] = AffinityContribution(
                peer_id=str(peer_id),
                scores={str(k): float(v) for k, v in scores.items()},
                ts=ts,
            )

    def publish(self, peer_id: str, scores: Dict[str, float]) -> None:
        """Publish OUR OWN affinity onto the bus so remote chorus instances
        can pick it up. Also stamps it into the local table so a single-bus
        case works without relying on the subscription round trip.
        """
        raise RuntimeError(AFFINITY_CHORUS_RELEASE_HOLD)
        ts = time.time()
        self.add(peer_id=peer_id, scores=scores, ts=ts)
        if self.thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought  # type: ignore
        except Exception:
            Thought = None  # type: ignore
        payload = {"peer_id": peer_id, "scores": dict(scores), "ts": ts}
        try:
            if Thought is not None:
                self.thought_bus.publish(Thought(
                    source="persona_vacuum",
                    topic=self.TOPIC,
                    payload=payload,
                ))
            else:
                self.thought_bus.publish(topic=self.TOPIC, payload=payload,
                                         source="persona_vacuum")
        except Exception as e:
            logger.debug("AffinityChorus: publish failed: %s", e)

    # ─── merging ─────────────────────────────────────────────────────────

    def merged(
        self,
        self_scores: Optional[Dict[str, float]] = None,
        self_peer_id: str = "",
    ) -> Dict[str, float]:
        """Mean of all live contributions (self + peers) — a single
        unified affinity vector for sampling.

        Averaging rather than summing makes the merged map invariant to
        *how many* peers have contributed so far. Two nodes that see the
        same local state and read the chorus at moments when 1 vs 2
        peers have published will still end up with the same merged
        map once everyone has the same data, so their deterministic
        softmax picks the same winner.

        Stale entries (past TTL) are pruned as a side effect.
        """
        now = time.time()
        sums: Dict[str, float] = {}
        count = 0
        with self._lock:
            # Prune stale.
            if self.ttl_s > 0:
                stale = [pid for pid, c in self._contributions.items()
                         if now - c.ts > self.ttl_s]
                for pid in stale:
                    del self._contributions[pid]

            for pid, c in self._contributions.items():
                # If the caller is also publishing as `self_peer_id`, their
                # self_scores take precedence so we don't double-count a
                # publish-then-merge race.
                if self_peer_id and pid == self_peer_id and self_scores:
                    continue
                for name, value in c.scores.items():
                    sums[name] = sums.get(name, 0.0) + float(value)
                count += 1

            if self_scores:
                for name, value in self_scores.items():
                    sums[name] = sums.get(name, 0.0) + float(value) * self.weight_self
                count += 1

        if count == 0:
            return {}
        return {name: total / count for name, total in sums.items()}

    # ─── introspection ───────────────────────────────────────────────────

    def peer_count(self) -> int:
        """How many distinct peers currently have live (non-stale) contributions."""
        now = time.time()
        with self._lock:
            if self.ttl_s <= 0:
                return len(self._contributions)
            return sum(
                1 for c in self._contributions.values()
                if now - c.ts <= self.ttl_s
            )

    def contributions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [c.to_payload() for c in self._contributions.values()]

    def clear(self) -> None:
        with self._lock:
            self._contributions.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic-seed helpers — same state + same seed_fn ⇒ same winner
# ─────────────────────────────────────────────────────────────────────────────


def vault_fingerprint_seed(vault: Any) -> int:
    """Stable integer seed derived from a vault's current fingerprint.

    Two nodes whose vaults have converged (same card set, same fingerprint)
    will produce the same seed. Pass this as ``seed_fn`` to PersonaVacuum
    so softmax sampling is deterministic across the mesh.
    """
    fp = ""
    try:
        if vault is not None and hasattr(vault, "fingerprint"):
            fp = str(vault.fingerprint() or "")
    except Exception:
        fp = ""
    digest = hashlib.sha256(fp.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def make_vault_seed_fn(vault: Any) -> Callable[[], int]:
    """Return a zero-arg callable usable as PersonaVacuum.seed_fn."""
    def _fn() -> int:
        return vault_fingerprint_seed(vault)
    return _fn


__all__ = [
    "AFFINITY_CHORUS_RELEASE_HOLD",
    "AffinityChorus",
    "AffinityContribution",
    "DEFAULT_TTL_S",
    "vault_fingerprint_seed",
    "make_vault_seed_fn",
]
