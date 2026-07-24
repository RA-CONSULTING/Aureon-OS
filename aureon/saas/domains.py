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
from typing import Dict, List, Tuple

# The 6 product domains the frontend console presents.
PRODUCT_DOMAINS: List[str] = [
    "trading", "accounting", "research", "cognition", "security", "self-improvement",
]

# 24 filesystem domains → product domain. Unmapped → "self-improvement".
_FS_TO_PRODUCT: Dict[str, str] = {
    "trading": "trading", "exchanges": "trading", "strategies": "trading",
    "scanners": "trading", "s51": "trading", "bots": "trading",
    "portfolio": "accounting", "analytics": "accounting", "conversion": "accounting",
    "harmonic": "research", "wisdom": "research", "decoders": "research",
    "simulation": "research", "atn": "research", "intelligence": "research",
    "operator": "cognition", "cognition": "cognition", "queen": "cognition",
    "bots_intelligence": "cognition",
    "utils": "security", "bridges": "security", "data_feeds": "security",
    "autonomous": "self-improvement", "monitors": "self-improvement",
    "command_centers": "self-improvement", "core": "self-improvement",
    "saas": "self-improvement",
    # previously-unmapped real packages under aureon/ — categorized so the whole
    # body is surfaced/probed instead of silently defaulting to self-improvement.
    "bio": "research", "alignment": "research", "search": "research",
    "observer": "cognition", "inhouse_ai": "cognition", "miner": "cognition",
    "swarm_motion": "cognition",
    "integrations": "security",
    "code_architect": "self-improvement", "vault": "self-improvement",
    "generated": "self-improvement",
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
        "available": available,
    }


def domain_report(fs_domains: List[str] | None = None) -> List[Dict[str, object]]:
    """Reachability report across the known filesystem domains."""
    domains = fs_domains if fs_domains is not None else sorted(
        set(_FS_TO_PRODUCT) | set(_ADAPTERS)
    )
    return [probe_domain(d) for d in domains]


__all__ = [
    "PRODUCT_DOMAINS",
    "product_domain_for",
    "fs_domain_from_path",
    "probe_domain",
    "domain_report",
]
