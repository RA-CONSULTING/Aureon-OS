"""
Aureon SaaS — domain taxonomy + capability adapters ("connected").
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Reconciles the repo's three taxonomies and gives every filesystem domain under
aureon/ a product-domain home + a canonical entry point:

  • product domains  — the 6 the React console groups by
                       (trading · accounting · research · cognition · security ·
                        self-improvement)
  • filesystem domains — every folder under aureon/ (docs/MODULES_AT_A_GLANCE.md)
  • capability categories — the 12 SystemRegistry semantic classes (in catalog.py)

`domain_report()` probes each filesystem domain's entry point by import (cheap —
``importlib.util.find_spec``, no heavy construction) so we can honestly say which
domains are reachable. The known singletons come from the inventory; everything
else falls back to "is the package importable".
"""

from __future__ import annotations

import importlib.util
from typing import Any, Dict, List, Tuple

# The 6 product domains the frontend console presents.
PRODUCT_DOMAINS: List[str] = [
    "trading", "accounting", "research", "cognition", "security", "self-improvement",
]

# 24 filesystem domains → product domain. Unmapped → "self-improvement".
_FS_TO_PRODUCT: Dict[str, str] = {
    "trading": "trading", "exchanges": "trading", "strategies": "trading",
    "scanners": "trading", "s51": "trading", "bots": "trading",
    "portfolio": "accounting", "analytics": "accounting", "conversion": "accounting",
    "accounting": "accounting",  # the King's Court — the commercial accounting body
    "harmonic": "research", "wisdom": "research", "decoders": "research",
    "simulation": "research", "atn": "research", "intelligence": "research",
    "operator": "cognition", "cognition": "cognition", "queen": "cognition",
    "bots_intelligence": "cognition",
    "utils": "security", "bridges": "security", "data_feeds": "security",
    "governance": "security",
    "autonomous": "self-improvement", "monitors": "self-improvement",
    "command_centers": "self-improvement", "core": "self-improvement",
    "saas": "self-improvement", "observability": "self-improvement",
    # previously-unmapped real packages under aureon/ — categorized so the whole
    # body is surfaced/probed instead of silently defaulting to self-improvement.
    "bio": "research", "alignment": "research", "search": "research",
    "observer": "cognition", "inhouse_ai": "cognition", "miner": "cognition",
    "swarm_motion": "cognition",
    "swarm": "cognition",  # the harmonic hive — HNC-grounded multi-agent company
    "integrations": "security",
    "code_architect": "self-improvement", "vault": "self-improvement",
    "generated": "self-improvement",
    # Consolidated governed operations: each package remains separately visible
    # in the coverage audit while sharing the closest public product domain.
    "appliance": "self-improvement",
    "approval": "security",
    "briefing": "research",
    "connectors": "security",
    "gates": "security",
    "grants": "research",
    "identity": "security",
    "portals": "security",
}

# Canonical entry point per filesystem domain: (module, attribute, kind).
# Domains without a clean singleton fall back to the package spec (kind="package").
_ADAPTERS: Dict[str, Tuple[str, str, str]] = {
    "core": ("aureon.core.aureon_operational_core", "get_operational_core", "singleton"),
    "queen": ("aureon.utils.aureon_queen_hive_mind", "get_queen", "singleton"),
    "operator": ("aureon.operator.aureon_operator", "run_operator", "function"),
    "cognition": ("aureon.operator.cognition", "AureonCognition", "class"),
    "data_feeds": ("aureon.data_feeds.aureon_real_data_feed_hub", "get_feed_hub", "singleton"),
    "bio": ("aureon.bio.celestial_observatory", "observe", "function"),
    "observer": ("aureon.observer", "get_observer", "singleton"),
}


# The cognitive substrate's read accessors — the systems the Cognitive SaaS
# surface (``/api/cognition``) exposes. Unlike ``_ADAPTERS`` (one entry point per
# filesystem domain), these are the individual read accessors that span core/utils,
# so they live in their own registry: surface → (module, accessor, backing_note).
COGNITIVE_SURFACES: Dict[str, Tuple[str, str, str]] = {
    "field": ("aureon.core.hnc_field", "read_canonical_field", "canonical HNC field + sub-fields + blend"),
    "bus": ("aureon.core.aureon_thought_bus", "get_thought_bus", "thought-bus topic links + subscribers"),
    "mycelium": ("aureon.core.aureon_mycelium", "get_mycelium", "mesh coherence + hives + connected systems"),
    "connectome": ("aureon.core.aureon_connectome", "get_connectome", "body-map coverage + node roll-up"),
    "brain": ("aureon.saas.cognitive", "brain_surface", "miner-brain accuracy + knowledge (file-read shim)"),
}


def product_domain_for(fs_domain: str) -> str:
    return _FS_TO_PRODUCT.get(fs_domain, "self-improvement")


def cognitive_surface_report() -> List[Dict[str, object]]:
    """Import-reachability of each cognitive surface's backing accessor — the
    catalog view of the Cognitive SaaS surface (cheap ``find_spec``, no
    construction)."""
    report: List[Dict[str, object]] = []
    for surface, (module, accessor, note) in COGNITIVE_SURFACES.items():
        report.append({
            "surface": surface,
            "product_domain": "cognition",
            "accessor": f"{module}:{accessor}",
            "note": note,
            "available": _module_importable(module),
        })
    return report


def fs_domain_from_path(filepath: str) -> str:
    """Extract the filesystem domain (folder under aureon/) from a module path."""
    norm = str(filepath).replace("\\", "/")
    parts = norm.split("/")
    if "aureon" in parts:
        i = parts.index("aureon")
        if i + 1 < len(parts) - 1:  # there's a folder between aureon/ and the file
            return parts[i + 1]
    return "core"


def _module_importable(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def probe_domain(fs_domain: str) -> Dict[str, object]:
    """Cheap reachability probe for one domain (import spec check, no construction)."""
    adapter: Tuple[str, str, str] | None = _ADAPTERS.get(fs_domain)
    if adapter is not None:
        module, attr, kind = adapter
        entry = f"{module}:{attr}"
    else:
        module, attr, kind, entry = f"aureon.{fs_domain}", "", "package", f"aureon.{fs_domain}"
    available = _module_importable(module)
    return {
        "domain": fs_domain,
        "product_domain": product_domain_for(fs_domain),
        "entry_point": entry,
        "kind": kind,
        "has_adapter": fs_domain in _ADAPTERS,
        "available": available,
    }


def _rollup_by_domain(catalog: Dict[str, Any] | None) -> Dict[str, Dict[str, Any]]:
    """Roll the catalog's per-module scan up into a real operational summary per filesystem
    domain — module / dashboard / Queen-wired / bus-wired counts, total LOC, and the distinct
    capability categories present. All derived from the honest filesystem scan; nothing fabricated."""
    roll: Dict[str, Dict[str, Any]] = {}
    cats = catalog.get("categories", {}) if isinstance(catalog, dict) else {}
    for cat_name, cat in cats.items():
        for s in cat.get("systems", []) if isinstance(cat, dict) else []:
            d = str(s.get("fs_domain", "core"))
            r = roll.setdefault(d, {
                "system_count": 0, "dashboards": 0, "queen_integrated": 0,
                "bus_wired": 0, "wired_count": 0, "total_loc": 0, "capabilities": set(),
            })
            r["system_count"] += 1
            r["dashboards"] += 1 if s.get("is_dashboard") else 0
            r["queen_integrated"] += 1 if s.get("has_queen_integration") else 0
            r["bus_wired"] += 1 if s.get("has_thought_bus") else 0
            r["wired_count"] += 1 if (s.get("has_thought_bus") or s.get("has_queen_integration")) else 0
            r["total_loc"] += int(s.get("loc", 0) or 0)
            r["capabilities"].add(cat_name)
    return roll


def _finalize_health(r: Dict[str, Any] | None) -> Dict[str, Any] | None:
    """Shape one raw rollup bucket into the public ``health`` dict (sorted, fractions rounded)."""
    if r is None:
        return None
    n = int(r["system_count"])
    return {
        "system_count": n,
        "dashboards": int(r["dashboards"]),
        "queen_integrated": int(r["queen_integrated"]),
        "bus_wired": int(r["bus_wired"]),
        "wired_count": int(r["wired_count"]),
        "wired_fraction": round(r["wired_count"] / n, 3) if n else 0.0,
        "total_loc": int(r["total_loc"]),
        "capabilities": sorted(r["capabilities"]),
    }


def domain_health(fs_domain: str, catalog: Dict[str, Any] | None) -> Dict[str, Any] | None:
    """The real operational rollup for one domain from the catalog scan, or ``None`` when the
    catalog carries no systems for it (honest — never a fabricated zero-with-confidence)."""
    return _finalize_health(_rollup_by_domain(catalog).get(fs_domain))


def domain_report(
    fs_domains: List[str] | None = None,
    catalog: Dict[str, Any] | None = None,
) -> List[Dict[str, object]]:
    """Reachability + operational-depth report across the known filesystem domains.

    Each domain carries the cheap import-reachability probe; when a ``catalog`` (from
    ``build_catalog``) is supplied, every domain also carries a real ``health`` rollup derived
    from the filesystem scan (module/dashboard/wiring counts, LOC, capabilities) — so all 38
    domains report operational depth, not just "is the package importable"."""
    domains = fs_domains if fs_domains is not None else sorted(
        set(_FS_TO_PRODUCT) | set(_ADAPTERS)
    )
    roll = _rollup_by_domain(catalog) if catalog else {}
    report: List[Dict[str, object]] = []
    for d in domains:
        rec = probe_domain(d)
        if catalog is not None:
            rec["health"] = _finalize_health(roll.get(d))
        report.append(rec)
    return report


def known_fs_domains() -> List[str]:
    """The filesystem domains the taxonomy knows about (taxonomy ∪ adapters), sorted."""
    return sorted(set(_FS_TO_PRODUCT) | set(_ADAPTERS))


__all__ = [
    "PRODUCT_DOMAINS",
    "product_domain_for",
    "fs_domain_from_path",
    "probe_domain",
    "domain_health",
    "domain_report",
    "known_fs_domains",
]
