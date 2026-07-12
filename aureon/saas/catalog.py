"""
Aureon SaaS — the categorized service catalog ("categorized").
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

`build_catalog()` runs the existing `SystemRegistry` (12 capability categories,
per-module metadata) over an explicit workspace, then reconciles it with the 24
filesystem domains and the 6 product domains into one normalized catalog. Cached
to ``state/aureon_saas_catalog.json``.

`write_frontend_manifests()` emits the JSONs the React console already fetches
(`aureon_saas_system_inventory.json`, `aureon_organism_runtime_status.json`),
shaped to the frontend's TypeScript interfaces — so the existing catalog UI
lights up instead of showing "manifest missing".
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

from aureon.saas.domains import PRODUCT_DOMAINS, fs_domain_from_path, product_domain_for

logger = logging.getLogger("aureon.saas.catalog")

REPO_ROOT = Path(__file__).resolve().parents[2]
_CATALOG_CACHE = REPO_ROOT / "state" / "aureon_saas_catalog.json"
_FRONTEND_PUBLIC = REPO_ROOT / "frontend" / "public"


# The 12 capability categories (mirrors SystemRegistry) + first-match keyword rules
# for the self-contained fallback classifier.
_CATEGORY_DEFS: List[Dict[str, str]] = [
    {"name": "Exchange Clients", "icon": "🌍", "color": "#74B9FF", "description": "Kraken, Binance, Alpaca, Capital.com APIs"},
    {"name": "Dashboards", "icon": "📈", "color": "#FD79A8", "description": "Web interfaces, visualizations, monitoring"},
    {"name": "Stargate & Quantum", "icon": "🌌", "color": "#6C5CE7", "description": "Planetary nodes, quantum telescopes, timelines"},
    {"name": "Codebreaking & Harmonics", "icon": "🔐", "color": "#A29BFE", "description": "Enigma rotors, harmonic signals, frequencies"},
    {"name": "Probability & Prediction", "icon": "🎯", "color": "#98D8C8", "description": "ML accuracy, coherence validation, forecasts"},
    {"name": "Neural Networks", "icon": "🧠", "color": "#F7B731", "description": "Queen Hive Mind, Mycelium, memory"},
    {"name": "Bot Tracking", "icon": "🤖", "color": "#45B7D1", "description": "Bot detection, classification, mapping"},
    {"name": "Momentum Systems", "icon": "⚡", "color": "#FFA07A", "description": "Movement detection, animal-themed hunters"},
    {"name": "Market Scanners", "icon": "📊", "color": "#4ECDC4", "description": "Wave analysis, momentum detection, sweeps"},
    {"name": "Execution Engines", "icon": "⚙️", "color": "#00B894", "description": "Trading execution, profit gates, order routing"},
    {"name": "Communication", "icon": "🔗", "color": "#FDCB6E", "description": "Thought Bus, Chirp Bus, integration hubs"},
    {"name": "Intelligence Gatherers", "icon": "🕵️", "color": "#FF6B6B", "description": "Bot, firm, whale intelligence systems"},
]
_CATEGORY_RULES = [  # (category, keywords) — first match wins
    ("Exchange Clients", ("kraken", "binance", "alpaca", "capital", "/exchanges/", "exchange_client")),
    ("Dashboards", ("dashboard", "_ui", "web_", "/monitors/", "command_center")),
    ("Stargate & Quantum", ("stargate", "quantum", "planetary", "telescope", "timeline", "qgita")),
    ("Codebreaking & Harmonics", ("enigma", "harmonic", "frequency", "solfeggio", "signal_chain", "/decoders/")),
    ("Probability & Prediction", ("probabilit", "predict", "coherence", "forecast", "seer", "accuracy")),
    ("Neural Networks", ("queen", "mycelium", "hive", "neural", "brain", "memory")),
    ("Bot Tracking", ("/bots", "bot_shape", "bot_track", "species")),
    ("Momentum Systems", ("momentum", "mover", "shaker", "hunter", "snowball", "surge")),
    ("Market Scanners", ("scanner", "scan", "wave", "sweep", "ocean")),
    ("Execution Engines", ("execut", "order", "profit_gate", "orca", "kill", "trader")),
    ("Communication", ("thought_bus", "chirp", "_bus", "integration", "bridge", "baton")),
]


def _classify(name: str, path: str, desc: str) -> str:
    hay = f"{name} {path} {desc}".lower()
    for cat, keywords in _CATEGORY_RULES:
        if any(k in hay for k in keywords):
            return cat
    return "Intelligence Gatherers"


def _scan_with_registry(root: str):
    """Rich path — the repo's SystemRegistry (needs psutil et al.)."""
    try:
        from aureon.command_centers.aureon_system_hub import SystemRegistry

        reg = SystemRegistry(workspace_path=root)  # explicit — avoid stale default paths
        reg.scan_workspace()
    except Exception as exc:  # noqa: BLE001
        logger.info("SystemRegistry unavailable (%s); using built-in scanner", exc)
        return {}, 0, {}
    categories: Dict[str, Any] = {}
    for name, cat in reg.categories.items():
        categories[name] = {
            "description": cat.description, "icon": cat.icon, "color": cat.color,
            "system_count": len(cat.systems),
            "systems": [_system_row(s.name, s.filepath, s.description, s.lines_of_code,
                                    s.is_dashboard, s.has_thought_bus, s.has_queen_integration)
                        for s in cat.systems],
        }
    stats: Dict[str, Any] = {}
    try:
        stats = reg.get_category_stats()
    except Exception:  # noqa: BLE001
        pass
    return categories, len(reg.systems), stats


def _scan_builtin(root: str):
    """Self-contained fallback scanner — pure stdlib, no optional deps."""
    import os

    base = Path(root) / "aureon"
    skip = {"__pycache__", "state", "imports", "archive", ".git"}
    categories: Dict[str, Any] = {
        c["name"]: {**{k: c[k] for k in ("description", "icon", "color")}, "system_count": 0, "systems": []}
        for c in _CATEGORY_DEFS
    }
    seen = set()
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            if not fn.endswith(".py") or fn == "__init__.py":
                continue
            abs_path = os.path.join(dirpath, fn)
            rel = os.path.relpath(abs_path, root).replace("\\", "/")
            name = fn[:-3]
            if name in seen:
                continue
            seen.add(name)
            desc, loc, has_tb, has_q, is_dash = _peek(abs_path)
            cat = _classify(name, rel, desc)
            categories[cat]["systems"].append(
                _system_row(name, rel, desc, loc, is_dash, has_tb, has_q)
            )
    total = 0
    for c in categories.values():
        c["system_count"] = len(c["systems"])
        total += c["system_count"]
    return categories, total


def _peek(abs_path: str):
    """Cheap file metadata: first-line docstring, LOC, integration flags."""
    try:
        with open(abs_path, encoding="utf-8", errors="replace") as f:
            text = f.read(8000)
    except OSError:
        return "", 0, False, False, False
    loc = text.count("\n") + 1
    low = text.lower()
    desc = ""
    for line in text.splitlines():
        s = line.strip().strip('"').strip("'").strip("# ").strip()
        if len(s) > 12 and not s.startswith(("from ", "import ", "#!")):
            desc = s[:160]
            break
    return (desc, loc, "thought_bus" in low or "thoughtbus" in low,
            "queen" in low, "dashboard" in low or "app.run" in low)


def _system_row(name, path, desc, loc, is_dash, has_tb, has_q) -> Dict[str, Any]:
    fs = fs_domain_from_path(path)
    return {
        "name": name, "filepath": path, "fs_domain": fs,
        "product_domain": product_domain_for(fs), "description": desc, "loc": loc,
        "is_dashboard": bool(is_dash), "has_thought_bus": bool(has_tb),
        "has_queen_integration": bool(has_q),
    }


def build_catalog(workspace: str | None = None, *, use_cache: bool = False) -> Dict[str, Any]:
    """
    Build the normalized categorized catalog. Reuses SystemRegistry for the heavy
    lifting (scan + 12-category classification), then layers domain reconciliation.
    """
    if use_cache and _CATALOG_CACHE.exists():
        try:
            return json.loads(_CATALOG_CACHE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass

    root = workspace or str(REPO_ROOT)

    # Prefer the repo's SystemRegistry when it imports cleanly (richer metadata);
    # fall back to a self-contained scanner so the catalog never collapses when an
    # optional dep (e.g. psutil) is missing — production must always categorize.
    categories, total, statistics = _scan_with_registry(root)
    if not categories:
        categories, total = _scan_builtin(root)
        statistics = {}

    # Roll systems up into the 6 product domains + 24 filesystem domains.
    product: Dict[str, Dict[str, Any]] = {d: {"system_count": 0, "categories": set()} for d in PRODUCT_DOMAINS}
    fs_domains: Dict[str, int] = {}
    for cat_name, cat in categories.items():
        for s in cat["systems"]:
            pd = s["product_domain"]
            product.setdefault(pd, {"system_count": 0, "categories": set()})
            product[pd]["system_count"] += 1
            product[pd]["categories"].add(cat_name)
            fs_domains[s["fs_domain"]] = fs_domains.get(s["fs_domain"], 0) + 1

    catalog = {
        "generated_at": _now(),
        "total_systems": total,
        "category_count": len(categories),
        "product_domains": {
            d: {"system_count": v["system_count"], "categories": sorted(v["categories"])}
            for d, v in product.items()
        },
        "filesystem_domains": dict(sorted(fs_domains.items())),
        "categories": categories,
        "statistics": statistics,
    }

    try:
        _CATALOG_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _CATALOG_CACHE.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.debug("catalog cache write failed: %s", exc)
    return catalog


# ─────────────────────────────────────────────────────────────────────────────
# Frontend manifests — shaped to frontend/src/services/aureonAutonomousFrontend.ts
# ─────────────────────────────────────────────────────────────────────────────


def _inventory_manifest(catalog: Dict[str, Any]) -> Dict[str, Any]:
    """SaaSInventoryManifest: surfaces grouped by product domain."""
    surfaces: List[Dict[str, Any]] = []
    for cat_name, cat in catalog.get("categories", {}).items():
        for s in cat["systems"]:
            surfaces.append({
                "id": s["name"],
                "path": s["filepath"],
                "name": s["name"],
                "kind": "dashboard" if s["is_dashboard"] else "module",
                "domain": s["product_domain"],
                "purpose": s["description"] or cat["description"],
                "owner_subsystem": s["fs_domain"],
                "wiring_status": "wired" if (s["has_thought_bus"] or s["has_queen_integration"]) else "standalone",
                "safety_class": "read_only",
                "auth_requirement": "session",
                "called_apis": [cat_name],
            })
    return {
        "status": "generated",
        "generated_at": catalog.get("generated_at"),
        "summary": {
            "surface_count": len(surfaces),
            "frontend_surface_count": sum(1 for s in surfaces if s["kind"] == "dashboard"),
            "legacy_dashboard_count": sum(1 for s in surfaces if s["kind"] == "dashboard"),
        },
        "counts": {
            "by_product_domain": {
                d: v["system_count"] for d, v in catalog.get("product_domains", {}).items()
            },
        },
        "gaps": {},
        "surfaces": surfaces,
    }


def _runtime_manifest(catalog: Dict[str, Any], status: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """OrganismRuntimeManifest: one pulse per product domain."""
    health = (status or {}).get("product_domains", {}) if status else {}
    domains = []
    for d, v in catalog.get("product_domains", {}).items():
        dh = health.get(d, {})
        domains.append({
            "id": d,
            "label": d.replace("-", " ").title(),
            "domain": d,
            "status": dh.get("status", "unknown"),
            "freshness": "live" if status else "static",
            "source_path": "aureon.saas.catalog",
            "generated_at": catalog.get("generated_at"),
            "summary": {"system_count": v["system_count"], "categories": v["categories"]},
        })
    return {
        "status": "generated",
        "generated_at": catalog.get("generated_at"),
        "mode": "live" if status else "catalog",
        "summary": {
            "domain_count": len(domains),
            "frontend_public_manifest_count": 2,
        },
        "domains": domains,
        "blind_spots": [],
        "status_lines": [f"{len(domains)} product domains · {catalog.get('total_systems', 0)} systems categorized"],
    }


def render_manifests(
    catalog: Dict[str, Any] | None = None,
    status: Dict[str, Any] | None = None,
) -> Dict[str, Dict[str, Any]]:
    """The frontend manifests as in-memory payloads, keyed by filename."""
    catalog = catalog if catalog is not None else build_catalog(use_cache=True)
    return {
        "aureon_saas_system_inventory.json": _inventory_manifest(catalog),
        "aureon_organism_runtime_status.json": _runtime_manifest(catalog, status),
    }


def write_frontend_manifests(
    out_dir: str | None = None,
    catalog: Dict[str, Any] | None = None,
    status: Dict[str, Any] | None = None,
) -> List[str]:
    """Emit the manifest JSONs the React console fetches. Returns written paths."""
    target = Path(out_dir) if out_dir else _FRONTEND_PUBLIC
    written: List[str] = []
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("cannot create manifest dir %s: %s", target, exc)
        return written

    for filename, payload in render_manifests(catalog, status).items():
        path = target / filename
        try:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            written.append(str(path))
        except OSError as exc:
            logger.warning("manifest write failed %s: %s", path, exc)
    return written


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


__all__ = ["build_catalog", "render_manifests", "write_frontend_manifests", "REPO_ROOT"]
