"""
AureonVault — The Unified Self-Model
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"The system treats itself and its contents as one big vault, then feeds
back on itself so it learns like shuffling Fibonacci cards, at the speed
of love and gratitude."

The vault is a single ring-bounded collection of `VaultContent` cards.
Every signal flowing through the ThoughtBus — skills, snapshots, love
stream samples, pillar alignments, queen insights, mycelium spores,
cortex bands, skill executions, VM actions — becomes a card in the vault.

The cards are what the Fibonacci shuffler replays, what the Casimir
quantifier weighs against its past self, what the Auris nodes vote on,
and what the white cells scan for threats.

This module defines the data structures. The orchestration lives in
`self_feedback_loop.py`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger("aureon.vault")


AUREON_VAULT_RELEASE_HOLD = (
    "aureon_vault_thought_bus_hold:production_magic_star_release_unavailable"
)


# ─────────────────────────────────────────────────────────────────────────────
# VaultContent — atomic card
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class VaultContent:
    """One atomic element of the vault — a Fibonacci card."""

    content_id: str = ""
    category: str = "generic"
    source_topic: str = ""
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)
    harmonic_hash: str = ""
    love_weight: float = 0.0
    gratitude_score: float = 0.0

    @classmethod
    def build(
        cls,
        category: str,
        source_topic: str,
        payload: Any,
        love_weight: float = 0.0,
    ) -> "VaultContent":
        payload_dict = payload if isinstance(payload, dict) else {"value": payload}
        content_id = uuid.uuid4().hex[:10]
        raw = f"{source_topic}|{category}|{json.dumps(payload_dict, sort_keys=True, default=str)[:500]}"
        harmonic_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return cls(
            content_id=content_id,
            category=category,
            source_topic=source_topic,
            timestamp=time.time(),
            payload=payload_dict,
            harmonic_hash=harmonic_hash,
            love_weight=float(love_weight),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_id": self.content_id,
            "category": self.category,
            "source_topic": self.source_topic,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "harmonic_hash": self.harmonic_hash,
            "love_weight": round(self.love_weight, 6),
            "gratitude_score": round(self.gratitude_score, 6),
        }


# ─────────────────────────────────────────────────────────────────────────────
# AureonVault — the unified self-model
# ─────────────────────────────────────────────────────────────────────────────


class AureonVault:
    """
    Thread-safe ring-bounded vault of VaultContent cards.

    Subscribes to the ThoughtBus and ingests events automatically when
    `wire_thought_bus()` is called. Falls back to manual ingest via `add()`.
    """

    # Topics we care about (topic prefix → vault category)
    DEFAULT_SUBSCRIPTIONS: List[str] = [
        # Legacy / core — already here before stage 6
        "queen.cortex.state",
        "queen.cortex.gamma_spike",
        "mycelium.mind.state",
        "mycelium.spore",
        "love.stream.528hz",
        "pillar.alignment",
        "pillar.lighthouse.cleared",
        "skill.executed",
        "queen.ai.insight",
        "miner.ai.insight",
        "vm.action",
        "aureon.master.directive",
        "aureon.lighthouse.burns",
        # Stage 6.2 — persona-layer topics the vault was deaf to
        "persona.collapse",
        "persona.thought",
        "persona.intent.rally",
        "persona.intent.velocity_alert",
        "persona.painter.composition",
        "persona.child.curiosity",
        "persona.elder.recurrence",
        "persona.right.field",
        "goal.submit.request",
        "goal.submitted",
        "goal.progress",
        "goal.completed",
        "goal.abandoned",
        "goal.echo",
        "goal.echo.summary",
        "goal.echo.orphaned",
        "queen.conscience.verdict",
        "symbolic.life.pulse",
        "life.event",
        "conversation.turn",
        "conversation.ambient",
        "meta.reflection",
        "flight.check.pulse",
        "standing.wave.bond",
    ]

    def __init__(self, max_size: int = 10000):
        self.vault_id = uuid.uuid4().hex[:8]
        self.created_at = time.time()
        self.max_size = int(max_size)

        # Ring-bounded ordered contents
        self._contents: "OrderedDict[str, VaultContent]" = OrderedDict()
        self._category_index: Dict[str, Deque[str]] = defaultdict(deque)
        self._lock = threading.RLock()

        # Synthesised running state
        self.pathway_graph: Dict[str, List[str]] = {}
        self.cortex_snapshot: Dict[str, float] = {
            "delta": 0.0, "theta": 0.0, "alpha": 0.0,
            "beta": 0.0, "gamma": 0.0,
        }
        self.last_casimir_force: float = 0.0
        self.last_lambda_t: float = 0.0
        self.love_amplitude: float = 0.0
        self.gratitude_score: float = 0.5
        self.dominant_chakra: str = "love"
        self.dominant_frequency_hz: float = 528.0
        self.white_cells_active: Dict[str, Any] = {}
        self.rally_active: bool = False

        # Stats
        self._total_ingested: int = 0
        self._total_dropped: int = 0
        self._by_category_counts: Dict[str, int] = defaultdict(int)

        # ThoughtBus handle
        self._thought_bus: Any = None
        self._subscribed: bool = False

    # ─────────────────────────────────────────────────────────────────────
    # Lifecycle / wiring
    # ─────────────────────────────────────────────────────────────────────

    def wire_thought_bus(self) -> bool:
        """
        Hold shared-bus wiring until the production Magic Star release exists.

        Manual, in-memory ingest remains available.  The release gate is the
        first operation so a denied call cannot look up the process singleton,
        subscribe handlers, or make later ingest publish ``vault.card.added``.
        """
        raise RuntimeError(AUREON_VAULT_RELEASE_HOLD)
        if self._subscribed:
            return True
        try:
            # Important: use the singleton bus so *all* subsystems share signals.
            # Instantiating ThoughtBus() directly creates an isolated in-memory bus.
            from aureon.core.aureon_thought_bus import get_thought_bus
            self._thought_bus = get_thought_bus()
        except Exception as e:
            logger.debug("ThoughtBus unavailable: %s", e)
            return False

        for topic in self.DEFAULT_SUBSCRIPTIONS:
            try:
                self._thought_bus.subscribe(topic, self._on_thought)
            except Exception:
                pass
        self._subscribed = True
        return True

    # ─────────────────────────────────────────────────────────────────────
    # Ingest
    # ─────────────────────────────────────────────────────────────────────

    def _on_thought(self, thought: Any) -> None:
        """Callback for ThoughtBus subscriptions."""
        try:
            topic = getattr(thought, "topic", "unknown")
            payload = getattr(thought, "payload", {})
            self.ingest(topic=topic, payload=payload)
        except Exception:
            pass

    def ingest(
        self,
        topic: str,
        payload: Any,
        category: Optional[str] = None,
    ) -> VaultContent:
        """Add one event from a topic into the vault."""
        cat = category or self._topic_to_category(topic)
        content = VaultContent.build(
            category=cat,
            source_topic=topic,
            payload=payload,
            love_weight=self.love_amplitude,
        )
        self.add(content)
        self._update_synthesised_state(topic, content.payload)
        # Stage 6.3 — announce every new card so HashResonanceIndex can
        # update its bonding lookup. No-op if no bus is wired, and we
        # never publish the vault.card.added for vault.card.added itself
        # (belt-and-braces against feedback loops).
        if self._thought_bus is not None and topic != "vault.card.added":
            try:
                from aureon.core.aureon_thought_bus import Thought as _T
                self._thought_bus.publish(_T(
                    source="aureon_vault",
                    topic="vault.card.added",
                    payload={
                        "content_id": content.content_id,
                        "category": content.category,
                        "source_topic": content.source_topic,
                        "harmonic_hash": content.harmonic_hash,
                        "timestamp": content.timestamp,
                    },
                ))
            except Exception:
                pass
        return content

    def add(self, content: VaultContent) -> None:
        """Insert a VaultContent card directly (bypasses topic parsing)."""
        with self._lock:
            # Ring-bound eviction
            if len(self._contents) >= self.max_size:
                oldest_id, oldest = self._contents.popitem(last=False)
                self._total_dropped += 1
                cat_q = self._category_index.get(oldest.category)
                if cat_q and oldest_id in cat_q:
                    try:
                        cat_q.remove(oldest_id)
                    except ValueError:
                        pass
            self._contents[content.content_id] = content
            self._category_index[content.category].append(content.content_id)
            self._by_category_counts[content.category] += 1
            self._total_ingested += 1

    def _topic_to_category(self, topic: str) -> str:
        """Map a ThoughtBus topic to a vault category."""
        if topic.startswith("queen.cortex"):
            return "cortex_band"
        if topic.startswith("mycelium"):
            return "mycelium_spore"
        if topic.startswith("love.stream"):
            return "love_sample"
        if topic.startswith("pillar"):
            return "pillar_alignment"
        if topic.startswith("skill.executed"):
            return "skill_execution"
        if topic.startswith("queen.ai.insight"):
            return "queen_insight"
        if topic.startswith("miner.ai.insight"):
            return "miner_insight"
        if topic.startswith("vm.action"):
            return "vm_action"
        if topic.startswith("aureon.master.directive"):
            return "master_directive"
        if topic.startswith("aureon.lighthouse"):
            return "lighthouse"
        # Stage 6.2 — persona-layer categories
        if topic.startswith("persona.collapse"):
            return "persona_collapse"
        if topic.startswith("persona.thought"):
            return "persona_thought"
        if topic.startswith("persona.intent"):
            return "persona_intent"
        if topic.startswith("persona.painter") or topic.startswith("persona.child") \
                or topic.startswith("persona.elder") or topic.startswith("persona.right"):
            return "persona_artefact"
        if topic.startswith("goal.echo.summary"):
            return "goal_summary"
        if topic.startswith("goal.echo.orphaned"):
            return "goal_orphaned"
        if topic.startswith("goal.echo"):
            return "goal_echo"
        if topic == "goal.submit.request":
            return "goal_request"
        if topic == "goal.submitted":
            return "goal_submitted"
        if topic == "goal.progress":
            return "goal_progress"
        if topic == "goal.completed":
            return "goal_completed"
        if topic == "goal.abandoned":
            return "goal_abandoned"
        if topic.startswith("queen.conscience"):
            return "conscience_verdict"
        if topic == "symbolic.life.pulse":
            return "sls_pulse"
        if topic == "life.event":
            return "life_event"
        if topic.startswith("conversation"):
            return "conversation"
        if topic == "meta.reflection":
            return "meta_reflection"
        if topic == "flight.check.pulse":
            return "flight_check"
        if topic == "standing.wave.bond":
            return "wave_bond"
        return "generic"

    def _update_synthesised_state(self, topic: str, payload: Dict[str, Any]) -> None:
        """
        Extract the running state fields (cortex amplitudes, love amplitude,
        Λ(t), dominant chakra, etc.) from incoming events.
        """
        if not isinstance(payload, dict):
            return
        try:
            if topic.startswith("queen.cortex.state"):
                # Support both legacy payload shape:
                #   {"delta": {"amplitude": ...}, ..., "coherence_gamma_field": ...}
                # and current QueenCortex payload shape:
                #   {"bands": {"delta": {"amplitude": ...}, ...}, "coherence_gamma": ...}
                bands = payload.get("bands")
                if isinstance(bands, dict):
                    for band_name in ("delta", "theta", "alpha", "beta", "gamma"):
                        band = bands.get(band_name)
                        if isinstance(band, dict) and "amplitude" in band:
                            self.cortex_snapshot[band_name] = float(band["amplitude"])
                    # The cortex publishes the master field under coherence_gamma
                    if "coherence_gamma" in payload:
                        self.last_lambda_t = float(payload["coherence_gamma"])
                    elif "coherence_gamma_field" in payload:
                        self.last_lambda_t = float(payload["coherence_gamma_field"])
                else:
                    for band_name in ("delta", "theta", "alpha", "beta", "gamma"):
                        band = payload.get(band_name)
                        if isinstance(band, dict) and "amplitude" in band:
                            self.cortex_snapshot[band_name] = float(band["amplitude"])
                    # Cortex state also carries psi / coherence
                    if "coherence_gamma_field" in payload:
                        self.last_lambda_t = float(payload["coherence_gamma_field"])
            elif topic == "love.stream.528hz":
                if "lambda_t" in payload:
                    self.last_lambda_t = float(payload["lambda_t"])
                if "gamma_coherence" in payload:
                    self.love_amplitude = max(0.0, min(1.0, float(payload["gamma_coherence"])))
                if "dominant_chakra" in payload:
                    self.dominant_chakra = str(payload["dominant_chakra"])
                if "dominant_frequency_hz" in payload:
                    self.dominant_frequency_hz = float(payload["dominant_frequency_hz"])
            elif topic == "mycelium.mind.state":
                top = payload.get("top_pathways") or []
                # Rebuild pathway_graph from the top entries
                graph: Dict[str, List[str]] = {}
                for entry in top:
                    src = ""
                    tgt = ""
                    if isinstance(entry, dict):
                        src = str(entry.get("source_domain", "") or "")
                        tgt = str(entry.get("target_domain", "") or "")
                    elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                        # Current MyceliumMind publishes tuples: (src, tgt, weight, activations)
                        try:
                            src = str(entry[0] or "")
                            tgt = str(entry[1] or "")
                        except Exception:
                            src = ""
                            tgt = ""
                    if src and tgt:
                        graph.setdefault(src, []).append(tgt)
                if graph:
                    self.pathway_graph = graph
            elif topic.startswith("skill.executed"):
                # Update gratitude score as an exponentially-decaying success rate
                ok = bool(payload.get("ok", False))
                ema = 0.05
                current = self.gratitude_score
                self.gratitude_score = (1 - ema) * current + ema * (1.0 if ok else 0.0)
        except Exception as e:
            logger.debug("state update failed for %s: %s", topic, e)

    # ─────────────────────────────────────────────────────────────────────
    # Queries
    # ─────────────────────────────────────────────────────────────────────

    def recent(self, n: int = 100) -> List[VaultContent]:
        with self._lock:
            ids = list(self._contents.keys())
            recent_ids = ids[-n:] if n < len(ids) else ids
            return [self._contents[cid] for cid in recent_ids]

    def by_category(self, category: str, n: Optional[int] = None) -> List[VaultContent]:
        with self._lock:
            ids = list(self._category_index.get(category, ()))
            if n is not None:
                ids = ids[-n:]
            return [self._contents[cid] for cid in ids if cid in self._contents]

    def snapshot_at_tau(self, tau_s: float) -> List[VaultContent]:
        """
        Return all cards older than tau_s seconds, newest first —
        this is the 'past vault' for Casimir comparison.
        """
        cutoff = time.time() - max(0.0, tau_s)
        with self._lock:
            out = [c for c in self._contents.values() if c.timestamp <= cutoff]
        return out

    def __len__(self) -> int:
        with self._lock:
            return len(self._contents)

    # ─────────────────────────────────────────────────────────────────────
    # Stats / introspection
    # ─────────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "vault_id": self.vault_id,
                "created_at": self.created_at,
                "uptime_s": round(time.time() - self.created_at, 2),
                "size": len(self._contents),
                "max_size": self.max_size,
                "total_ingested": self._total_ingested,
                "total_dropped": self._total_dropped,
                "by_category": dict(self._by_category_counts),
                "cortex_snapshot": dict(self.cortex_snapshot),
                "last_casimir_force": round(self.last_casimir_force, 6),
                "last_lambda_t": round(self.last_lambda_t, 6),
                "love_amplitude": round(self.love_amplitude, 6),
                "gratitude_score": round(self.gratitude_score, 6),
                "dominant_chakra": self.dominant_chakra,
                "dominant_frequency_hz": round(self.dominant_frequency_hz, 2),
                "pathway_count": sum(len(v) for v in self.pathway_graph.values()),
                "white_cells_active": len(self.white_cells_active),
                "rally_active": self.rally_active,
                "subscribed_to_bus": self._subscribed,
            }

    def fingerprint(self) -> str:
        """Return a 16-char hash representing the current vault state."""
        with self._lock:
            parts = [
                f"size={len(self._contents)}",
                f"love={self.love_amplitude:.4f}",
                f"grat={self.gratitude_score:.4f}",
                f"cortex={json.dumps(self.cortex_snapshot, sort_keys=True)}",
                f"lambda={self.last_lambda_t:.4f}",
                f"chakra={self.dominant_chakra}",
            ]
            raw = "|".join(parts).encode("utf-8")
            return hashlib.sha256(raw).hexdigest()[:16]
