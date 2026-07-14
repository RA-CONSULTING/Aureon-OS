"""
The canonical HNC field — one shared reading, not thirteen private ones.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The organism had ~13 independent ``LambdaEngine`` instances, each computing its own
``symbolic_life_score`` / ``coherence_gamma`` with nothing reconciling them. The HNC
live daemon (driven by real world data) now publishes the authoritative field on the
thought bus as ``symbolic.life.pulse``. This module is the single place to READ that
field, so a system that only wants "the current shared coherence" reads the one
canonical value instead of spinning a private engine — the field becomes shared
logic, not a per-module opinion.

Read path uses ``recall(topic_prefix)`` (filters by topic) so a high-volume bus
(baton.link heartbeats, etc.) can never evict the pulse from a recency window. Fully
guarded and offline-safe: with no bus / no pulse, ``read_canonical_field()`` returns
an ``available=False`` field rather than raising.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CanonicalField:
    """A snapshot of the organism's shared HNC field."""

    available: bool = False
    symbolic_life_score: float | None = None
    coherence_gamma: float | None = None
    consciousness_psi: float | None = None
    consciousness_level: str | None = None
    lambda_t: float | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "symbolic_life_score": self.symbolic_life_score,
            "coherence_gamma": self.coherence_gamma,
            "consciousness_psi": self.consciousness_psi,
            "consciousness_level": self.consciousness_level,
            "lambda_t": self.lambda_t,
            "source": self.source,
        }


_EMPTY = CanonicalField()


def read_canonical_field(bus: Any = None) -> CanonicalField:
    """Read the latest ``symbolic.life.pulse`` — the one shared field.

    Pass ``bus`` to read from a specific ThoughtBus; otherwise the global
    singleton is used. Never raises; returns an unavailable field when there is
    no bus, no pulse, or no score.
    """
    try:
        from aureon.core.aureon_thought_bus import get_thought_bus, payload_of

        b = bus if bus is not None else get_thought_bus()
        if b is None or not hasattr(b, "recall"):
            return _EMPTY
        pulses = b.recall("symbolic.life.pulse", limit=1) or []
        if not pulses:
            return _EMPTY
        p = payload_of(pulses[-1])
        sls = p.get("symbolic_life_score")
        if sls is None:
            return _EMPTY
        return CanonicalField(
            available=True,
            symbolic_life_score=float(sls),
            coherence_gamma=p.get("coherence_gamma"),
            consciousness_psi=p.get("consciousness_psi"),
            consciousness_level=p.get("consciousness_level"),
            lambda_t=p.get("lambda_t"),
            source=p.get("source"),
        )
    except Exception:  # noqa: BLE001 — a missing field is a value, never a crash
        return _EMPTY


def publish_subfield(source: str, state: Any, bus: Any = None) -> None:
    """Publish a producer's LOCAL field as a namespaced sub-field.

    The organism has many legitimate ``LambdaEngine`` producers (the Queen's
    cortex, source-law, metacognition, sentient loop, mycelium mind, the human
    loop). Each computes a real local field; reconciling them into one would
    destroy that. Instead each publishes its field here as
    ``symbolic.life.subfield`` so the organism can SENSE every sub-field — the
    fields become connected (visible on the shared bus) without losing their
    local computation. Guarded / no-op on any error.
    """
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        b = bus if bus is not None else get_thought_bus()
        if b is None:
            return
        b.publish(Thought(
            source=source, topic="symbolic.life.subfield",
            payload={
                "source": source,
                "symbolic_life_score": getattr(state, "symbolic_life_score", None),
                "coherence_gamma": getattr(state, "coherence_gamma", None),
                "consciousness_level": getattr(state, "consciousness_level", None),
            },
        ))
    except Exception:  # noqa: BLE001 — visibility is best-effort, never fatal
        pass


def read_subfields(bus: Any = None) -> dict[str, dict[str, Any]]:
    """All recently-published local sub-fields, keyed by source — the organism's
    view of every field its producers are computing."""
    out: dict[str, dict[str, Any]] = {}
    try:
        from aureon.core.aureon_thought_bus import get_thought_bus, payload_of

        b = bus if bus is not None else get_thought_bus()
        if b is None or not hasattr(b, "recall"):
            return out
        for t in b.recall("symbolic.life.subfield", limit=200) or []:
            p = payload_of(t)
            src = p.get("source")
            if src:
                out[src] = {
                    "symbolic_life_score": p.get("symbolic_life_score"),
                    "coherence_gamma": p.get("coherence_gamma"),
                    "consciousness_level": p.get("consciousness_level"),
                }
    except Exception:  # noqa: BLE001
        pass
    return out


__all__ = ["CanonicalField", "read_canonical_field", "publish_subfield", "read_subfields"]
