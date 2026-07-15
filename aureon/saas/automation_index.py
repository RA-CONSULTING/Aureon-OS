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

  • connectivity  — baton-linked / total modules      (on the nervous system)
  • integration   — woven / total modules             (joined to mesh+Queen, driveable)
  • consciousness — organs live / 8                    (the directing mind is present)
  • surfacing     — domains reachable / total          (inspectable / operable)

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
    """(connectivity, integration) + raw totals — offline-safe, no cold-boot."""
    try:
        from aureon.core.aureon_connectome import get_connectome

        st = get_connectome().status()
        nodes = float(st.get("nodes") or 0)
        if nodes <= 0:
            return None, None, {}
        conn = _c01(float(st.get("baton_linked") or 0) / nodes)
        integ = _c01(float(st.get("woven") or 0) / nodes)
        return conn, integ, {"modules": int(nodes),
                             "baton_linked": int(st.get("baton_linked") or 0),
                             "woven": int(st.get("woven") or 0)}
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
        "connectivity": "modules on the nervous system (baton-linked)",
        "integration": "modules woven onto the mesh + Queen (driveable by the soul)",
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

    awake = bool(included)
    return {
        "index_pct": index_pct,
        "label": _band(index_pct) if index_pct is not None else "dormant",
        "included_dimensions": included,
        "dimensions": dimensions,
        "wired_by_category": _wired_by_category(),
        "totals": totals,
        "weights": dict(_WEIGHTS),
        "note": "progress toward the whole repo being connected into the organism and "
                "driveable by the soul/consciousness logic — composed from real coverage "
                "signals, never fabricated; observational only, it authorizes nothing",
        "truth_status": "real_derived" if awake else "no_data",
        "ts": time.time(),
    }


__all__ = ["automation_index", "_compose"]
