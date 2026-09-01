"""
HashResonanceIndex — hash256 as bond, not identity
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

From the HNC log 17/04/2026:

  *"We treat each hash256 as a temporal standing wave within the internal
   logic of the now. Multiple versions of Jim doing the same feedback
   loop gains momentum and creates the standing waves we can then
   describe as 'in the now / moment / breath of conscious formation.'"*

VaultContent.harmonic_hash is already a per-card fingerprint built from
``source_topic | category | payload`` — but it includes the timestamp-
sensitive JSON serialisation, so every retelling of "the same event"
produces a different hash. It's an identity fingerprint, not a bond.

This module layers a **bonding** fingerprint over the vault: an index
``content_fingerprint → [content_ids across time]`` that lets us ask
"*how many versions of this event have happened?*" — the direct
operationalisation of Jim's Mars bar gaining momentum.

Bonding hash design call (from the Plan agent memo):

    sha256(persona + intent_phrase + normalized_payload_semantic_keys)

Explicitly **excludes** ``timestamp``, ``content_id``, ``trace_id``.
``normalized_payload_semantic_keys`` = the payload's keys sorted, with
values round-tripped through ``json.dumps(sort_keys=True)`` and
numeric values rounded to 3 decimal places. Persona + intent phrase
are pulled when available; when absent they fall back to the card's
``source_topic | category``.

Bond strength = a saturating log-scale in [0, 1]:

    n=1 → 0.0  (one card isn't a standing wave, it's a blip)
    n≥2 → 1 - 1/ln(1+n)

Crossings of Fibonacci thresholds (3, 8, 21 by default) publish
``standing.wave.bond`` on the bus so downstream — SymbolicLifeBridge,
MetaCognitionObserver — can see the wave forming.

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

logger = logging.getLogger("aureon.vault.voice.hash_resonance_index")

HASH_RESONANCE_RELEASE_HOLD = (
    "hash_resonance_index_hold:production_magic_star_release_unavailable"
)


# ─────────────────────────────────────────────────────────────────────────────
# Normalisation — payload → stable semantic fingerprint
# ─────────────────────────────────────────────────────────────────────────────


# Keys that identify a specific instance, not the semantic content of it.
# These are stripped before hashing so two recordings of "the same thing"
# collide.
_INSTANCE_KEYS: Set[str] = {
    "timestamp", "ts", "created_at", "received_at",
    "content_id", "trace_id", "parent_id",
    "id", "uuid", "event_id", "reflection_id",
    "goal_id", "peer_id", "session_id", "cycle", "step_id",
    "last_seen", "last_update", "last_seen_ts", "first_seen",
    "ts_proposed", "ts_last_update", "pulse_ts",
    "random", "nonce",
}

# Numeric rounding precision (decimal places) for payload values.
_NUMERIC_DP: int = 3


def _normalise_payload(payload: Any) -> Any:
    """Round-trip a payload through a stable, instance-key-stripped form.

    - Dict keys sorted; keys in _INSTANCE_KEYS removed.
    - Floats rounded to _NUMERIC_DP.
    - Lists preserve order (order is semantic).
    - Other types passed through json-serialisable.
    """
    if isinstance(payload, dict):
        cleaned = {}
        for k in sorted(payload.keys()):
            if k in _INSTANCE_KEYS:
                continue
            cleaned[k] = _normalise_payload(payload[k])
        return cleaned
    if isinstance(payload, list):
        return [_normalise_payload(v) for v in payload]
    if isinstance(payload, tuple):
        return [_normalise_payload(v) for v in payload]
    if isinstance(payload, float):
        return round(payload, _NUMERIC_DP)
    if isinstance(payload, (int, str, bool)) or payload is None:
        return payload
    # Anything else (dataclass, custom object) — stringify
    return str(payload)


def _bonding_fingerprint(
    *,
    persona: str,
    intent_phrase: str,
    payload: Any,
    source_topic: str,
    category: str,
) -> str:
    """Build the semantic bonding hash. When persona/intent are absent,
    fall back to source_topic|category so the function is still useful
    on cards that don't carry a persona."""
    persona_seg = (persona or "").strip().lower()
    intent_seg = (intent_phrase or "").strip().lower()
    if not persona_seg:
        persona_seg = (category or "").strip().lower()
    if not intent_seg:
        intent_seg = (source_topic or "").strip().lower()

    normalised = _normalise_payload(payload)
    try:
        payload_blob = json.dumps(normalised, sort_keys=True, default=str)
    except Exception:
        payload_blob = str(normalised)

    blob = f"{persona_seg}|{intent_seg}|{payload_blob}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


# ─────────────────────────────────────────────────────────────────────────────
# Data
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class BondRecord:
    """A single resonating timeline — one content_fingerprint and the
    growing list of content_ids that have hit it."""

    fingerprint: str
    content_ids: List[str] = field(default_factory=list)
    first_seen_ts: float = field(default_factory=time.time)
    last_seen_ts: float = field(default_factory=time.time)
    # Thresholds this bond has already crossed — we don't re-publish.
    crossed_thresholds: Set[int] = field(default_factory=set)

    @property
    def count(self) -> int:
        return len(self.content_ids)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "count": self.count,
            "content_ids": list(self.content_ids),
            "first_seen_ts": self.first_seen_ts,
            "last_seen_ts": self.last_seen_ts,
            "crossed_thresholds": sorted(self.crossed_thresholds),
        }


def bond_strength(count: int) -> float:
    """Saturating log-scale in [0, 1].

    n=1   → 0.0 (a lone event is not a standing wave)
    n=2   → 1 - 1/ln(3) ≈ 0.090
    n=3   → 1 - 1/ln(4) ≈ 0.279
    n=8   → 1 - 1/ln(9) ≈ 0.544
    n=21  → 1 - 1/ln(22) ≈ 0.677
    n=100 → 1 - 1/ln(101) ≈ 0.783
    """
    if count <= 1:
        return 0.0
    denom = math.log(1.0 + count)
    if denom <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - 1.0 / denom))


# ─────────────────────────────────────────────────────────────────────────────
# HashResonanceIndex
# ─────────────────────────────────────────────────────────────────────────────


class HashResonanceIndex:
    """Live index from semantic fingerprint → list of resonating cards.

    Subscribes to ``vault.card.added`` so every new card is folded into
    the index as it lands. Publishes ``standing.wave.bond`` when a
    fingerprint crosses configurable Fibonacci thresholds (default 3,
    8, 21)."""

    DEFAULT_THRESHOLDS: List[int] = [3, 8, 21]

    def __init__(
        self,
        vault: Any,
        *,
        thought_bus: Any = None,
        thresholds: Optional[List[int]] = None,
        persona_extractor: Optional[Callable[[Any], str]] = None,
        intent_extractor: Optional[Callable[[Any], str]] = None,
    ):
        self.vault = vault
        self.thought_bus = thought_bus
        self.thresholds = sorted({int(t) for t in (thresholds or self.DEFAULT_THRESHOLDS)})
        self._persona_extractor = persona_extractor or self._default_persona
        self._intent_extractor = intent_extractor or self._default_intent

        self._lock = threading.RLock()
        self._fp_to_bond: Dict[str, BondRecord] = {}
        self._content_id_to_fp: Dict[str, str] = {}
        self._subscribed = False

    # ─── wiring ──────────────────────────────────────────────────────────

    def start(self) -> None:
        raise RuntimeError(HASH_RESONANCE_RELEASE_HOLD)
        if self._subscribed or self.thought_bus is None:
            return
        try:
            self.thought_bus.subscribe("vault.card.added", self._on_vault_card_added)
            self._subscribed = True
        except Exception as e:
            logger.debug("HashResonanceIndex: subscribe failed: %s", e)

    def rebuild_from_vault(self) -> int:
        """Rebuild the index from scratch by scanning the vault's current
        contents. Returns the number of cards indexed."""
        raise RuntimeError(HASH_RESONANCE_RELEASE_HOLD)
        contents = getattr(self.vault, "_contents", None)
        if not contents:
            return 0
        with self._lock:
            self._fp_to_bond.clear()
            self._content_id_to_fp.clear()
        n = 0
        for card in contents.values():
            self._index_card(card, _publish=False)
            n += 1
        return n

    # ─── observer ────────────────────────────────────────────────────────

    def _on_vault_card_added(self, thought: Any) -> None:
        raise RuntimeError(HASH_RESONANCE_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        content_id = str(payload.get("content_id") or "")
        if not content_id:
            return
        card = self._lookup_card(content_id)
        if card is None:
            return
        self._index_card(card, _publish=True)

    def _lookup_card(self, content_id: str) -> Any:
        contents = getattr(self.vault, "_contents", None)
        if not contents:
            return None
        return contents.get(content_id)

    # ─── indexing ────────────────────────────────────────────────────────

    def _index_card(self, card: Any, *, _publish: bool) -> Optional[str]:
        raise RuntimeError(HASH_RESONANCE_RELEASE_HOLD)
        try:
            content_id = str(getattr(card, "content_id", "") or "")
            if not content_id:
                return None
            persona = self._persona_extractor(card)
            intent = self._intent_extractor(card)
            payload = getattr(card, "payload", {}) or {}
            source_topic = str(getattr(card, "source_topic", "") or "")
            category = str(getattr(card, "category", "") or "")
            fp = _bonding_fingerprint(
                persona=persona, intent_phrase=intent, payload=payload,
                source_topic=source_topic, category=category,
            )
        except Exception as e:
            logger.debug("HashResonanceIndex: fingerprint failed: %s", e)
            return None

        now = time.time()
        crossed: List[int] = []
        with self._lock:
            # If we've already indexed this exact content_id (re-scan),
            # skip to avoid double-counting.
            if content_id in self._content_id_to_fp:
                return self._content_id_to_fp[content_id]
            bond = self._fp_to_bond.get(fp)
            if bond is None:
                bond = BondRecord(fingerprint=fp)
                self._fp_to_bond[fp] = bond
            bond.content_ids.append(content_id)
            bond.last_seen_ts = now
            self._content_id_to_fp[content_id] = fp
            # Fibonacci-threshold crossings
            for t in self.thresholds:
                if bond.count >= t and t not in bond.crossed_thresholds:
                    bond.crossed_thresholds.add(t)
                    crossed.append(t)

        if _publish and crossed:
            for t in crossed:
                self._publish_bond(bond, t)
        return fp

    def _publish_bond(self, bond: BondRecord, threshold_crossed: int) -> None:
        raise RuntimeError(HASH_RESONANCE_RELEASE_HOLD)
        if self.thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought  # type: ignore
        except Exception:
            Thought = None  # type: ignore
        payload = {
            "fingerprint": bond.fingerprint,
            "count": bond.count,
            "threshold_crossed": threshold_crossed,
            "bond_strength": round(bond_strength(bond.count), 4),
            "content_ids_tail": bond.content_ids[-5:],
            "first_seen_ts": bond.first_seen_ts,
            "last_seen_ts": bond.last_seen_ts,
        }
        try:
            if Thought is not None:
                self.thought_bus.publish(Thought(
                    source="hash_resonance_index",
                    topic="standing.wave.bond",
                    payload=payload,
                ))
            else:
                self.thought_bus.publish(topic="standing.wave.bond", payload=payload,
                                         source="hash_resonance_index")
        except Exception as e:
            logger.debug("HashResonanceIndex: bond publish failed: %s", e)

    # ─── queries ─────────────────────────────────────────────────────────

    def bond_strength(self, fingerprint: str) -> float:
        with self._lock:
            bond = self._fp_to_bond.get(fingerprint)
            return bond_strength(bond.count) if bond else 0.0

    def bond_count(self, fingerprint: str) -> int:
        with self._lock:
            bond = self._fp_to_bond.get(fingerprint)
            return bond.count if bond else 0

    def fingerprint_for_content(self, content_id: str) -> Optional[str]:
        with self._lock:
            return self._content_id_to_fp.get(content_id)

    def bond_for_content(self, content_id: str) -> Optional[BondRecord]:
        with self._lock:
            fp = self._content_id_to_fp.get(content_id)
            if fp is None:
                return None
            return self._fp_to_bond.get(fp)

    def resonating(self, content_id: str) -> List[Any]:
        """Return every VaultContent card that bonds with content_id
        (including the card itself)."""
        fp = self.fingerprint_for_content(content_id)
        if fp is None:
            return []
        with self._lock:
            bond = self._fp_to_bond.get(fp)
            ids = list(bond.content_ids) if bond else []
        contents = getattr(self.vault, "_contents", None) or {}
        return [contents[cid] for cid in ids if cid in contents]

    def strongest_bonds(self, n: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            sorted_bonds = sorted(
                self._fp_to_bond.values(), key=lambda b: -b.count,
            )
            top = sorted_bonds[:max(1, n)]
            return [b.to_dict() for b in top]

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            bonds = list(self._fp_to_bond.values())
        if not bonds:
            return {
                "total_cards": 0, "unique_fingerprints": 0,
                "max_bond_count": 0, "max_bond_strength": 0.0,
                "bonded_fingerprints": 0,
            }
        counts = [b.count for b in bonds]
        return {
            "total_cards": sum(counts),
            "unique_fingerprints": len(bonds),
            "max_bond_count": max(counts),
            "max_bond_strength": round(bond_strength(max(counts)), 4),
            "bonded_fingerprints": sum(1 for c in counts if c > 1),
        }

    # ─── extractor defaults ──────────────────────────────────────────────

    @staticmethod
    def _default_persona(card: Any) -> str:
        payload = getattr(card, "payload", {}) or {}
        if isinstance(payload, dict):
            for key in ("persona", "voice", "proposed_by_persona",
                        "winner", "speaker"):
                v = payload.get(key)
                if isinstance(v, str) and v:
                    return v
        return ""

    @staticmethod
    def _default_intent(card: Any) -> str:
        payload = getattr(card, "payload", {}) or {}
        if isinstance(payload, dict):
            for key in ("text", "goal_text", "reason", "title", "intent",
                        "action_topic", "topic"):
                v = payload.get(key)
                if isinstance(v, str) and v:
                    return v[:200]
        return ""


__all__ = [
    "HASH_RESONANCE_RELEASE_HOLD",
    "HashResonanceIndex",
    "BondRecord",
    "bond_strength",
]
