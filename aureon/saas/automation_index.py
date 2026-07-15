"""
Automation progress index — one honest number for "how far to fully automated".
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 39 categorized *what* the organism can do; Phase 40 reported *how it is*. This
reports **how far along the automation is** — a single percentage measuring how much of
the repo is actually connected into the organism and driveable by the soul/consciousness
logic, decomposed so the number is never a black box.

It composes **only signals that already exist** — nothing is measured anew, nothing is
fabricated. Four dimensions, each a fraction in [0,1] (a dormant one is dropped, never
counted as zero):

  • connectivity  — touched / reachable modules        (reached & felt — on the nervous system)
  • integration   — woven / reachable modules          (joined to mesh+Queen, driveable)
  • consciousness — organs live / 8                     (the directing mind is present)
  • surfacing     — domains reachable / total           (inspectable / operable)

``reachable = nodes − denied``: the ``denied`` modules are deliberately deny-listed (unsafe
to import), so "fully automated" is measured against the body we *intend* to connect. The
connectome dims count the **persisted** carried coverage (``touched``/``woven``), not the
process-local ``baton_linked`` ping — so a cold read reflects the real coverage the organism
carries across cycles, and 100% is an honest, achievable target.

The index is the weight-renormalized mean of the dimensions actually present; when every
dimension is dormant it is ``None`` (honest ``no_data``, never a fabricated 0). The
weighting is transparent — the full per-dimension breakdown is always returned — and
tunable. This is **observational only**: it measures, it changes nothing.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("aureon.saas.automation_index")

# Integration (woven ⇒ the soul can actually drive it) is weighted highest.
_WEIGHTS: Dict[str, float] = {
    "connectivity": 0.25,
    "integration": 0.40,
    "consciousness": 0.20,
    "surfacing": 0.15,
}


def _c01(x: Any) -> float | None:
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return None


def _band(pct: float) -> str:
    """An honest descriptor for the number — a label, never inflation."""
    if pct < 10:
        return "nascent"
    if pct < 30:
        return "emerging"
    if pct < 60:
        return "developing"
    if pct < 85:
        return "maturing"
    return "near-complete"


def _compose(fractions: Dict[str, float | None]) -> Tuple[float | None, List[str]]:
    """Weight-renormalized mean over only the dimensions actually present. Returns
    ``(index_pct, included)`` — ``(None, [])`` when every dimension is dormant, so a
    cold organism reports no_data rather than a fabricated zero."""
    present = [(n, f) for n, f in fractions.items() if f is not None and n in _WEIGHTS]
    if not present:
        return None, []
    wsum = sum(_WEIGHTS[n] for n, _ in present)
    if wsum <= 0:
        return None, []
    idx = sum(_WEIGHTS[n] * f for n, f in present) / wsum
    return round(100.0 * idx, 2), [n for n, _ in present]


def _connectome_fractions() -> Tuple[float | None, float | None, Dict[str, Any]]:
    """(connectivity, integration) + the honest coverage breakdown — offline-safe, no
    cold-boot.

    Two honesty rules make 100% a truthful, achievable target:
      • **Carried coverage, not a process-local ping.** connectivity counts the persisted
        ``touched`` (modules the connectome has imported + felt, carried across cycles) —
        not ``baton_linked`` (only what pinged in *this* process). ``baton_linked`` stays
        reported as the live signal (mirrors Phase 45's live-vs-persisted reconciliation).
      • **Reachable denominator.** the ``denied`` modules are deliberately deny-listed
        (unsafe to import — loop-at-boot / heavy) and can never be woven, so "fully
        automated" is measured against ``reachable = nodes − denied``. ``failed`` stays
        counted against the goal (retryable debt, not an exclusion)."""
    try:
        from aureon.core.aureon_connectome import get_connectome

        st = get_connectome().status()
        nodes = int(st.get("nodes") or 0)
        denied = int(st.get("denied") or 0)
        reachable = max(0, nodes - denied)
        if reachable <= 0:
            return None, None, {}
        touched = int(st.get("touched") or 0)
        woven = int(st.get("woven") or 0)
        conn = _c01(touched / reachable)                 # persisted carried coverage
        integ = _c01(woven / reachable)
        return conn, integ, {
            "modules": nodes, "reachable": reachable,
            "touched": touched, "woven": woven,
            "baton_linked": int(st.get("baton_linked") or 0),  # the live signal, kept visible
            "denied": denied,                            # the deliberate ceiling
            "failed": int(st.get("failed") or 0),        # retryable debt (still counted)
            "unfelt": int(st.get("unfelt") or 0),        # remaining to reach
        }
    except Exception as exc:  # noqa: BLE001 — a cold connectome is no_data, never a crash
        logger.debug("connectome fractions skipped: %s", exc)
        return None, None, {}


def _consciousness_fraction() -> Tuple[float | None, Dict[str, Any]]:
    """organs live / total — guarded (the organ singletons cold-boot once, cached)."""
    try:
        from aureon.saas.consciousness_catalog import build_consciousness_catalog

        counts = build_consciousness_catalog().get("counts", {})
        total = float(counts.get("total") or 0)
        if total <= 0:
            return None, {}
        return _c01(float(counts.get("operational") or 0) / total), {
            "organs_live": int(counts.get("operational") or 0),
            "organs_total": int(total)}
    except Exception as exc:  # noqa: BLE001
        logger.debug("consciousness fraction skipped: %s", exc)
        return None, {}


def _surfacing_fraction() -> Tuple[float | None, Dict[str, Any]]:
    """domains reachable / total — cheapest + safest (find_spec only)."""
    try:
        from aureon.saas.status import get_platform_status

        st = get_platform_status()
        total = float(st.get("domains_total") or 0)
        if total <= 0:
            return None, {}
        return _c01(float(st.get("domains_reachable") or 0) / total), {
            "domains_reachable": int(st.get("domains_reachable") or 0),
            "domains_total": int(total)}
    except Exception as exc:  # noqa: BLE001
        logger.debug("surfacing fraction skipped: %s", exc)
        return None, {}


def _wired_by_category() -> Dict[str, Any]:
    """Per-category wired fraction (has thought-bus / Queen wiring) — where the soul
    logic reaches, by part of the repo. Derived from the cached catalog; guarded."""
    out: Dict[str, Any] = {}
    try:
        from aureon.saas.catalog import build_catalog

        cats = build_catalog(use_cache=True).get("categories", {})
        for name, block in cats.items():
            systems = block.get("systems", []) if isinstance(block, dict) else []
            total = len(systems)
            wired = sum(1 for s in systems
                        if s.get("has_thought_bus") or s.get("has_queen_integration"))
            out[name] = {"wired": wired, "total": total,
                         "pct": round(100.0 * wired / total, 1) if total else 0.0}
    except Exception as exc:  # noqa: BLE001 — the breakdown is best-effort
        logger.debug("wired_by_category skipped: %s", exc)
    return out


def automation_index() -> Dict[str, Any]:
    """One honest percentage toward "the whole repo, fully automated", decomposed by
    dimension and by category. Composes only real coverage signals; guarded/never-raises;
    a cold organism reports ``index_pct: None`` + ``no_data``. Observational only."""
    conn, integ, cst = _connectome_fractions()
    cons, cons_t = _consciousness_fraction()
    surf, surf_t = _surfacing_fraction()

    fractions: Dict[str, float | None] = {
        "connectivity": conn, "integration": integ,
        "consciousness": cons, "surfacing": surf,
    }
    details = {
        "connectivity": "modules reached & felt on the nervous system (touched / reachable, persisted)",
        "integration": "modules woven onto the mesh + Queen (driveable by the soul; / reachable)",
        "consciousness": "consciousness organs live (the directing mind present)",
        "surfacing": "domains reachable (inspectable / operable)",
    }
    index_pct, included = _compose(fractions)

    dimensions: Dict[str, Any] = {}
    for name, frac in fractions.items():
        dimensions[name] = {
            "fraction": frac,
            "pct": round(100.0 * frac, 2) if frac is not None else None,
            "weight": _WEIGHTS[name],
            "truth_status": "real_derived" if frac is not None else "no_data",
            "detail": details[name],
        }

    totals: Dict[str, Any] = {}
    totals.update(cst)
    totals.update(cons_t)
    totals.update(surf_t)
    # lineage maturity — reported only, never a weighted dimension (does not touch
    # index_pct). The organism reads its own diary: how many cycles it has carried.
    try:
        from aureon.core.awakening import read_genome

        totals["generation"] = int(read_genome().get("generation") or 0)
    except Exception:  # noqa: BLE001 — lineage echo is best-effort
        totals["generation"] = None

    awake = bool(included)
    return {
        "index_pct": index_pct,
        "label": _band(index_pct) if index_pct is not None else "dormant",
        "included_dimensions": included,
        "dimensions": dimensions,
        "wired_by_category": _wired_by_category(),
        "journey": journey(60),
        "totals": totals,
        "weights": dict(_WEIGHTS),
        "note": "progress toward the whole repo being connected into the organism and "
                "driveable by the soul/consciousness logic — composed from real coverage "
                "signals, never fabricated; observational only, it authorizes nothing",
        "truth_status": "real_derived" if awake else "no_data",
        "ts": time.time(),
    }


_JOURNEY = "automation_journey"


def journey(limit: int = 60) -> List[Dict[str, Any]]:
    """The recorded climb — compact index snapshots over time (oldest→newest), so the
    progress toward fully automated is visible as a trend, not just a number. Read-only,
    guarded; empty when nothing has been recorded yet."""
    try:
        from aureon.core.bus_trace import read_trace

        rows = read_trace(_JOURNEY, limit=max(1, int(limit)))
        return [r for r in rows if isinstance(r, dict) and "index_pct" in r]
    except Exception as exc:  # noqa: BLE001 — a missing journey is empty, never a crash
        logger.debug("journey read skipped: %s", exc)
        return []


def record_journey(idx: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
    """Append one compact snapshot of the current index to the journey trace (bounded).
    Called from the organism daemon's breath so the climb is captured as the connectome
    weaves more of the repo. Guarded/never-raises; a dormant index (``None``) is not
    recorded (no fabricated point). Returns the snapshot written, or ``None``."""
    try:
        idx = idx if idx is not None else automation_index()
        pct = idx.get("index_pct")
        if pct is None:
            return None
        snap = {
            "ts": idx.get("ts") or time.time(),
            "index_pct": pct,
            "dims": {k: v.get("pct") for k, v in idx.get("dimensions", {}).items()},
        }
        from aureon.core.bus_trace import append_trace

        append_trace(_JOURNEY, snap, cap=500)
        return snap
    except Exception as exc:  # noqa: BLE001 — recording is best-effort, never fatal
        logger.debug("journey record skipped: %s", exc)
        return None


__all__ = ["automation_index", "journey", "record_journey", "_compose"]
