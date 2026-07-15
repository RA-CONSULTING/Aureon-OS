"""
Aureon SaaS — the cognitive substrate as verified read APIs.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The organism is connected end-to-end — the HNC field, the connectome body-map,
the mycelium mesh, the thought bus, and the miner brain all breathe together.
This module *productizes* that substrate: it turns each cognitive and
meta-cognitive system into a first-class SaaS surface that anyone can read over
HTTP (``GET /api/cognition/...``), and it stamps every response with honest
**data provenance** so a consumer knows whether they are reading live truth,
a cached real value, or nothing at all.

Two invariants make this safe to expose:

  1. **Never cold-boot a heavy organ from a GET.** ``get_miner_brain()``,
     ``get_mycelium()`` and ``Connectome.sense()`` all have heavy / side-effectful
     init. So the brain surface reads the persisted prediction/knowledge files
     directly (never constructs the brain), and the mycelium surface reports only
     when the singleton already exists (``no_data`` / dormant otherwise) — the
     same posture ``build_organism_payload`` takes for the Queen.

  2. **Never fabricate.** Each surface carries a ``truth_status`` drawn from the
     repo's real-data contract vocabulary (``live`` / ``real_derived`` /
     ``cached_real`` / ``no_data``). When a signal is not flowing the surface
     says ``no_data`` with a blocker — it does not invent a plausible number.

Every builder is guarded and never raises: a dead organ degrades to an
unavailable surface, not a 500.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

logger = logging.getLogger("aureon.saas.cognitive")

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Key topic families that carry the organism's cognition — surfaced by the bus
# view so a consumer sees the living links, not just an anonymous topic count.
_COGNITIVE_TOPIC_FAMILIES = (
    "symbolic.life.pulse", "symbolic.life.subfield", "organism.field.consensus",
    "organism.connectome.pulse", "baton.link", "cognition.complete",
    "auris.throne.cosmic_state", "lighthouse.event", "operator.action.verdict",
)


# ── provenance — reuse the repo's real-data contract vocabulary ───────────────

def provenance_block() -> Dict[str, Any]:
    """A response-level provenance header, mirroring the connections layer's
    ``_real_data_policy_summary`` shape but self-contained (reuses the same
    ``real_data_contract`` / ``live_data_policy`` primitives, no private import).
    Shared by every SaaS surface so each response carries honest provenance.
    Never raises."""
    block: Dict[str, Any] = {
        "simulation_fallback_allowed": False,
        "truth_statuses": [],
        "source_registry_count": 0,
        "policy": "no fabricated values — a dormant organ reports no_data, never a guess",
    }
    try:
        from aureon.observer.live_data_policy import simulation_fallback_allowed
        from aureon.observer.real_data_contract import TRUTH_STATUSES, load_source_registry

        block["simulation_fallback_allowed"] = bool(simulation_fallback_allowed())
        block["truth_statuses"] = sorted(TRUTH_STATUSES)
        try:
            sources = load_source_registry(_REPO_ROOT).get("sources", {})
            block["source_registry_count"] = len(sources) if isinstance(sources, dict) else 0
        except Exception:  # noqa: BLE001 — registry optional
            pass
    except Exception as exc:  # noqa: BLE001 — contract module optional
        block["provenance_error"] = str(exc)[:160]
    return block


def _summarize(surfaces: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    """Roll the per-surface ``truth_status`` up via the contract's summarizer."""
    try:
        from aureon.observer.real_data_contract import summarize_truth_status

        return summarize_truth_status(
            [{"truth_status": s.get("truth_status", "no_data")} for s in surfaces.values()]
        )
    except Exception:  # noqa: BLE001
        return {}


# ── the five cognitive surfaces ───────────────────────────────────────────────

def field_surface(bus: Any = None) -> Dict[str, Any]:
    """The HNC field — the organism's shared coherence. Canonical reading +
    every local sub-field + the blended whole-body consensus + the age of the
    last breathed consensus event.

    ``truth_status``: ``live`` when a fresh pulse is on the local bus,
    ``cached_real`` when only the cross-process trace file answered, else
    ``no_data``.
    """
    surface: Dict[str, Any] = {"truth_status": "no_data", "blocker": "field not flowing"}
    try:
        from aureon.core.hnc_field import blend_field, read_canonical_field, read_subfields

        canonical = read_canonical_field(bus)
        subs = read_subfields(bus)
        blended = blend_field(bus)
        surface = {
            "canonical": canonical.to_dict(),
            "subfields": {"count": len(subs), "sources": sorted(subs.keys()), "fields": subs},
            "blended": blended.to_dict(),
            "consensus_event": _consensus_event(bus),
        }
        if canonical.available and canonical.source and canonical.source != "hnc_trace_file":
            surface["truth_status"] = "live"
        elif canonical.available:
            surface["truth_status"] = "cached_real"
            surface["derivation"] = "hnc_live_trace.jsonl (cross-process)"
        else:
            surface["truth_status"] = "no_data"
            surface["blocker"] = "no symbolic.life.pulse and no trace file"
    except Exception as exc:  # noqa: BLE001
        surface = {"truth_status": "no_data", "blocker": f"field read failed: {str(exc)[:120]}"}
    return surface


def _consensus_event(bus: Any = None) -> Dict[str, Any] | None:
    try:
        from aureon.core.aureon_thought_bus import get_thought_bus, payload_of

        b = bus if bus is not None else get_thought_bus()
        events = b.recall("organism.field.consensus", limit=1) or []
        if events:
            ev = events[-1]
            ts = ev.get("ts") if isinstance(ev, dict) else getattr(ev, "ts", None)
            return {
                "age_s": round(time.time() - float(ts), 1) if ts else None,
                "payload": payload_of(ev),
                "source": "bus",
            }
    except Exception:  # noqa: BLE001
        pass
    # Cross-process fallback: the organism daemon breathes consensus in another
    # process; read the dedicated trace it writes so the heartbeat still shows.
    try:
        from aureon.core.bus_trace import read_trace_latest

        row = read_trace_latest("organism_consensus")
        if not row:
            return None
        ts = row.get("ts")
        return {
            "age_s": round(time.time() - float(ts), 1) if ts else None,
            "payload": {k: v for k, v in row.items() if k != "ts"},
            "source": "consensus_trace_file",
        }
    except Exception:  # noqa: BLE001
        return None


def bus_surface(bus: Any = None) -> Dict[str, Any]:
    """Thought-bus links — the living topology: which topic families carry
    signal, how many subscribers listen, how many recent thoughts flowed. This
    is real runtime introspection of the running bus, so it is ``live`` when the
    bus exists, ``no_data`` when there is no bus at all."""
    surface: Dict[str, Any] = {"truth_status": "no_data", "blocker": "no thought bus"}
    try:
        from aureon.core.aureon_thought_bus import get_thought_bus

        b = bus if bus is not None else get_thought_bus()
        if b is None:
            return surface
        subscribed = b.list_subscribed_topics() if hasattr(b, "list_subscribed_topics") else []
        total_subs = b.subscriber_count() if hasattr(b, "subscriber_count") else 0
        families: Dict[str, Dict[str, int]] = {}
        for topic in _COGNITIVE_TOPIC_FAMILIES:
            recent = b.recall(topic, limit=200) if hasattr(b, "recall") else []
            families[topic] = {
                "recent": len(recent or []),
                "subscribers": b.subscriber_count(topic) if hasattr(b, "subscriber_count") else 0,
            }
        surface = {
            "truth_status": "live",
            "subscribed_topics": sorted(subscribed),
            "subscribed_topic_count": len(subscribed),
            "total_subscribers": total_subs,
            "cognitive_links": families,
            "cognitive_links_flowing": sum(1 for f in families.values() if f["recent"] > 0),
        }
    except Exception as exc:  # noqa: BLE001
        surface = {"truth_status": "no_data", "blocker": f"bus read failed: {str(exc)[:120]}"}
    return surface


def mycelium_surface() -> Dict[str, Any]:
    """The mycelium mesh links — coherence, hive/agent counts, connected systems,
    growth. Reports ONLY when the mesh singleton already exists; a status read
    must never cold-boot the network (which spawns a hive and wires the nexus).
    Dormant → ``no_data`` (honest: the mesh isn't running here)."""
    surface: Dict[str, Any] = {"truth_status": "no_data", "blocker": "mycelium dormant — not constructed in this process"}
    try:
        import aureon.core.aureon_mycelium as _myc

        inst = getattr(_myc, "_mycelium_instance", None)
        if inst is None:
            return surface
        mesh = inst.get_mesh_status()
        surface = {
            "truth_status": "live",
            "coherence": mesh.get("coherence"),
            "queen_signal": mesh.get("queen_signal"),
            "hive_count": mesh.get("hive_count"),
            "agent_count": mesh.get("agent_count"),
            "connected_systems": [c.get("name") for c in mesh.get("connected_systems", []) if isinstance(c, dict)],
            "connected_count": len(mesh.get("connected_systems", [])),
            "external_signals": mesh.get("external_signals"),
            "broadcasts_pending": mesh.get("broadcasts_pending"),
        }
        try:
            growth = inst.get_growth_stats()
            surface["growth"] = {
                "net_profit_total": growth.get("net_profit_total"),
                "growth_percentage": growth.get("growth_percentage"),
                "profit_rate_per_day": growth.get("profit_rate_per_day"),
            }
        except Exception:  # noqa: BLE001 — growth optional
            surface["growth"] = None
        # Honest reconciliation: the live mesh's connected_count is per-process (rebuilt
        # each boot), while the connectome persists what the body has woven across
        # cycles. Report both so a freshly-booted "0 connected" mesh reads against the
        # coverage the organism actually carries — the logic IS connected, just not yet
        # re-woven in this process. Guarded (no cold-boot beyond the cheap status read).
        try:
            from aureon.core.aureon_connectome import get_connectome

            surface["woven_persisted"] = get_connectome().status().get("woven")
        except Exception:  # noqa: BLE001 — reconciliation is best-effort
            surface["woven_persisted"] = None
    except Exception as exc:  # noqa: BLE001
        surface = {"truth_status": "no_data", "blocker": f"mycelium read failed: {str(exc)[:120]}"}
    return surface


def connectome_surface() -> Dict[str, Any]:
    """The connectome body-map — how much of the 715-module body the organism
    has actually felt (linked / touched / woven), plus a per-status node roll-up.
    Pure read (``status()``, never ``pulse()`` which publishes)."""
    surface: Dict[str, Any] = {"truth_status": "no_data", "blocker": "connectome unavailable"}
    try:
        from aureon.core.aureon_connectome import get_connectome

        conn = get_connectome()
        status = conn.status()
        by_status: Dict[str, int] = {}
        try:
            for node in conn.nodes():
                st = str(node.get("status", "unknown"))
                by_status[st] = by_status.get(st, 0) + 1
        except Exception:  # noqa: BLE001 — node listing optional
            by_status = {}
        surface = {
            "truth_status": "live",
            "body_map": status,
            "nodes_by_status": by_status,
        }
    except Exception as exc:  # noqa: BLE001
        surface = {"truth_status": "no_data", "blocker": f"connectome read failed: {str(exc)[:120]}"}
    return surface


def _brain_path(env_key: str, default_name: str) -> Path:
    return Path(os.environ.get(env_key) or (_REPO_ROOT / default_name))


def brain_surface() -> Dict[str, Any]:
    """The miner brain — prediction accuracy + knowledge memory, read straight
    from the persisted state files (``brain_predictions_history.json`` and
    ``miner_brain_knowledge.json`` at the repo root). This NEVER constructs the
    brain (``get_miner_brain()`` is heavy and side-effectful). ``real_derived``
    from the persisted history; ``no_data`` when the files are absent.
    Paths overridable via ``AUREON_BRAIN_PREDICTIONS_PATH`` /
    ``AUREON_BRAIN_KNOWLEDGE_PATH``."""
    surface: Dict[str, Any] = {"truth_status": "no_data", "blocker": "brain state files absent"}
    predictions_path = _brain_path("AUREON_BRAIN_PREDICTIONS_PATH", "brain_predictions_history.json")
    knowledge_path = _brain_path("AUREON_BRAIN_KNOWLEDGE_PATH", "miner_brain_knowledge.json")

    accuracy: Dict[str, Any] | None = None
    knowledge: Dict[str, Any] | None = None

    if predictions_path.exists():
        try:
            data = json.loads(predictions_path.read_text(encoding="utf-8"))
            preds = data.get("predictions", []) if isinstance(data, dict) else []
            validated = [p for p in preds if isinstance(p, dict) and p.get("validated")]
            correct = [p for p in validated if p.get("was_correct")]
            accuracy = {
                "total_predictions": len(preds),
                "validated": len(validated),
                "correct": len(correct),
                "accuracy_pct": round(100.0 * len(correct) / len(validated), 2) if validated else None,
                "last_updated": data.get("last_updated") if isinstance(data, dict) else None,
            }
        except Exception as exc:  # noqa: BLE001
            accuracy = {"error": f"predictions unreadable: {str(exc)[:120]}"}

    if knowledge_path.exists():
        try:
            kdata = json.loads(knowledge_path.read_text(encoding="utf-8"))
            entries = kdata if isinstance(kdata, list) else kdata.get("entries", []) if isinstance(kdata, dict) else []
            last = entries[-1] if entries else {}
            knowledge = {
                "entries": len(entries),
                "last_timestamp": last.get("timestamp") if isinstance(last, dict) else None,
            }
        except Exception as exc:  # noqa: BLE001
            knowledge = {"error": f"knowledge unreadable: {str(exc)[:120]}"}

    if accuracy is not None or knowledge is not None:
        surface = {
            "truth_status": "real_derived",
            "derivation": "read from persisted brain state files (brain never constructed)",
            "accuracy": accuracy,
            "knowledge": knowledge,
        }
    return surface


# ── the umbrella ──────────────────────────────────────────────────────────────

_SURFACE_BUILDERS: Dict[str, Callable[[], Dict[str, Any]]] = {
    "field": field_surface,
    "bus": bus_surface,
    "mycelium": mycelium_surface,
    "connectome": connectome_surface,
    "brain": brain_surface,
}


def build_cognitive_payload() -> Dict[str, Any]:
    """The whole cognitive substrate as one verified SaaS payload: every surface
    plus a provenance header and a truth-status roll-up. Never raises — a dead
    organ shows as a ``no_data`` surface, and the roll-up counts it as blocked."""
    surfaces: Dict[str, Dict[str, Any]] = {}
    bus = None
    try:  # one bus read shared across field + bus surfaces
        from aureon.core.aureon_thought_bus import get_thought_bus

        bus = get_thought_bus()
    except Exception:  # noqa: BLE001
        bus = None

    for name, builder in _SURFACE_BUILDERS.items():
        try:
            surfaces[name] = builder(bus) if name in ("field", "bus") else builder()  # type: ignore[call-arg]
        except Exception as exc:  # noqa: BLE001 — one dead organ never sinks the payload
            surfaces[name] = {"truth_status": "no_data", "blocker": f"{name} failed: {str(exc)[:120]}"}

    roll = _summarize(surfaces)
    registry: List[Dict[str, Any]] = []
    try:
        from aureon.saas.domains import cognitive_surface_report

        registry = cognitive_surface_report()
    except Exception:  # noqa: BLE001 — catalog view optional
        registry = []
    return {
        "available": True,
        "product_domain": "cognition",
        "surfaces": surfaces,
        "registry": registry,
        "provenance": provenance_block(),
        "truth_summary": roll,
        "operational_ready": roll.get("operational_ready", 0),
        "blocked": roll.get("blocked", 0),
    }


__all__ = [
    "build_cognitive_payload",
    "provenance_block",
    "field_surface",
    "bus_surface",
    "mycelium_surface",
    "connectome_surface",
    "brain_surface",
]
