"""
Aureon Operator — connections logic (view · readiness · probe · set).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pure-ish helpers behind the ``/api/connections`` surface, kept out of the Flask
module so they're unit-testable. Secrets are always masked on the way out; the
raw key only ever travels inward (set/test).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from aureon.observer.live_data_policy import simulation_fallback_allowed
from aureon.observer.real_data_contract import TRUTH_STATUSES, load_source_registry
from aureon.operator import keystore
from aureon.operator.connections_catalog import CATEGORIES, Connection

_RUNTIME_STATUS = Path(__file__).resolve().parents[2] / "state" / "unified_runtime_status.json"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_REAL_SOURCE_PROBE_REPORTS = (
    _REPO_ROOT / "state" / "real_source_probe.json",
    _REPO_ROOT / "docs" / "audits" / "aureon_real_source_probe.json",
)


# ── credential presence (keystore first, then env / aliases) ──────────────────

# ``allow_env`` is the tenancy switch. ``os.environ`` holds the INSTANCE's credentials, so a tenant
# view must never consult it: otherwise a signed-in end user enumerates which of the operator's
# exchange keys exist, where each comes from, and its last 4 characters. Default True keeps the
# admin / single-operator view byte-for-byte unchanged.

def _key_source(conn: Connection, store: Dict[str, Any], *, allow_env: bool = True) -> str:
    if store.get(conn.id, {}).get("api_key"):
        return "keystore"
    if allow_env and conn.key_env and os.environ.get(conn.key_env, "").strip():
        return "env"
    return "none"


def _key_masked(conn: Connection, store: Dict[str, Any], *, allow_env: bool = True) -> str:
    stored = store.get(conn.id, {}).get("api_key")
    if stored:
        return keystore.mask(stored)
    if not allow_env:
        return ""
    envv = os.environ.get(conn.key_env, "") if conn.key_env else ""
    return keystore.mask(envv) if envv else ""


def _has_key(conn: Connection, store: Dict[str, Any], *, allow_env: bool = True) -> bool:
    if conn.requirement == "keyless":
        return True
    return _key_source(conn, store, allow_env=allow_env) != "none"


def _exchange_ready() -> Dict[str, bool]:
    """Best-effort read of the trader's runtime status (exchanges.*_ready)."""
    try:
        data = json.loads(_RUNTIME_STATUS.read_text(encoding="utf-8"))
        ex = data.get("exchanges", {}) or {}
        return {k.replace("_ready", ""): bool(v) for k, v in ex.items() if k.endswith("_ready")}
    except Exception:  # noqa: BLE001 — status file optional
        return {}


def _real_data_policy_summary() -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "simulation_fallback_allowed": simulation_fallback_allowed(),
        "truth_statuses": sorted(TRUTH_STATUSES),
        "source_registry_count": 0,
        "probe_summary": {
            "live": 0,
            "real_derived": 0,
            "cached_real": 0,
            "no_data": 0,
            "test_fixture": 0,
            "operational_ready": 0,
            "blocked": 0,
        },
        "probe_report_path": "",
        "probe_report_status": "missing",
    }
    try:
        registry = load_source_registry(_REPO_ROOT)
        sources = registry.get("sources", {})
        summary["source_registry_count"] = len(sources) if isinstance(sources, dict) else 0
    except Exception as exc:  # noqa: BLE001
        summary["source_registry_error"] = str(exc)[:160]

    for path in _REAL_SOURCE_PROBE_REPORTS:
        if not path.exists():
            continue
        try:
            report = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            probe_summary = report.get("summary") if isinstance(report, dict) else {}
            if isinstance(probe_summary, dict):
                summary["probe_summary"].update(
                    {key: int(probe_summary.get(key, 0) or 0) for key in summary["probe_summary"]}
                )
            summary["probe_report_path"] = str(path)
            summary["probe_report_status"] = "loaded"
            break
        except Exception as exc:  # noqa: BLE001
            summary["probe_report_path"] = str(path)
            summary["probe_report_status"] = f"unreadable:{type(exc).__name__}"
            break
    return summary


def connection_public(conn: Connection, store: Dict[str, Any], ready: Dict[str, bool],
                      *, allow_env: bool = True) -> Dict[str, Any]:
    entry = store.get(conn.id, {})
    d = conn.to_public_dict()
    d.update({
        "has_key": _has_key(conn, store, allow_env=allow_env),
        "key_masked": _key_masked(conn, store, allow_env=allow_env),
        "key_source": _key_source(conn, store, allow_env=allow_env),
        "enabled": bool(entry.get("enabled", True)) if entry else (conn.requirement == "keyless"),
        "extra_masked": {k: keystore.mask(v) for k, v in (entry.get("extra") or {}).items()},
    })
    if conn.category == "exchange":
        d["runtime_ready"] = ready.get(conn.id)
    return d


# ── the unified categorized view ──────────────────────────────────────────────

def build_view(llm_providers: List[Dict[str, Any]], *, tenant: str | None = None) -> Dict[str, Any]:
    """Categorized connections. ``llm_providers`` is the operator's LLM provider
    view (from providers_list); everything else comes from the catalog.

    ``tenant`` scopes the non-LLM half to that user's isolated store. The LLM half was already
    per-tenant via ``_provider_view(tenant)``; this closes the same gap for the exchange / data-source
    rows, which is where the real money keys are. Under a tenant, ``os.environ`` is not consulted and
    the instance's exchange runtime readiness is withheld — both describe the instance, not the user.
    """
    store = keystore.load(tenant=tenant)
    allow_env = tenant is None
    ready = _exchange_ready() if tenant is None else {}
    llm_rows = [{
        "id": p["id"], "label": p["label"], "category": "ai_llm",
        "requirement": "optional", "consumed_by": "operator",
        "has_key": p["has_key"], "key_masked": p["key_masked"], "key_source": p["key_source"],
        "enabled": p["enabled"], "connected": p.get("live"),
        "unlocks": "LLM model for the operator switchboard",
        "get_keys_url": p.get("get_keys_url", ""), "docs_url": p.get("docs_url", ""),
    } for p in llm_providers]

    sections = []
    for cat_id, cat_label in CATEGORIES:
        if cat_id == "ai_llm":
            items = llm_rows
        else:
            items = [connection_public(c, store, ready, allow_env=allow_env) for c in _by_cat(cat_id)]
        sections.append({"category": cat_id, "label": cat_label, "connections": items})
    return {"categories": sections}


def _by_cat(cat_id: str) -> List[Connection]:
    from aureon.operator.connections_catalog import CATALOG

    return [c for c in CATALOG if c.category == cat_id]


# ── full operational-capacity readiness (presence only, no network) ───────────

def readiness(llm_providers: List[Dict[str, Any]], *, tenant: str | None = None) -> Dict[str, Any]:
    """Presence-only readiness. ``tenant`` scopes it to that user's store (see :func:`build_view`)."""
    store = keystore.load(tenant=tenant)
    allow_env = tenant is None
    items: List[Dict[str, Any]] = []

    for p in llm_providers:
        items.append({
            "id": p["id"], "label": p["label"], "category": "ai_llm",
            "requirement": "optional", "present": bool(p["has_key"]),
            "unlocks": "LLM model for the switchboard", "get_keys_url": p.get("get_keys_url", ""),
        })
    from aureon.operator.connections_catalog import CATALOG

    for c in CATALOG:
        items.append({
            "id": c.id, "label": c.label, "category": c.category,
            "requirement": c.requirement, "present": _has_key(c, store, allow_env=allow_env),
            "unlocks": c.unlocks, "get_keys_url": c.get_keys_url,
        })

    def _count(req: str):
        rows = [i for i in items if i["requirement"] == req]
        return sum(1 for i in rows if i["present"]), len(rows)

    req_present, req_total = _count("required")
    opt_present, opt_total = _count("optional")
    keyless_total = sum(1 for i in items if i["requirement"] == "keyless")
    missing = [i for i in items if i["requirement"] != "keyless" and not i["present"]]
    keyed_total = req_total + opt_total
    keyed_present = req_present + opt_present
    capacity_pct = round(100 * keyed_present / keyed_total) if keyed_total else 100
    # required-gap = the system can't run its core without these (currently none);
    # all_connected = every enrichment key also present → true full capacity.
    return {
        "summary": {
            "required_present": req_present, "required_total": req_total,
            "optional_present": opt_present, "optional_total": opt_total,
            "keyless": keyless_total,
            "keyed_present": keyed_present, "keyed_total": keyed_total,
            "capacity_pct": capacity_pct,
            "core_ready": req_present == req_total,   # no required gap
            "all_connected": len(missing) == 0,        # true full operational capacity
            "missing_count": len(missing),
            "real_data_policy": _real_data_policy_summary(),
        },
        "missing": missing,
        "items": items,
    }


# ── connectivity probe (real outbound GET; never raises) ──────────────────────

def probe(conn: Connection, api_key: str = "", timeout: float = 8.0) -> Dict[str, Any]:
    if not conn.probe_url:
        return {"ok": False, "http_status": 0, "latency_ms": 0,
                "error": "no probe endpoint for this source"}
    if conn.requirement != "keyless" and not api_key:
        return {"ok": False, "http_status": 0, "latency_ms": 0, "error": "no key to test"}
    try:
        import requests

        url = conn.probe_url
        headers: Dict[str, str] = {}
        params: Dict[str, str] = {}
        if api_key and conn.probe_auth == "header" and conn.probe_header:
            headers[conn.probe_header] = api_key
        elif api_key and conn.probe_auth == "bearer":
            headers["Authorization"] = f"Bearer {api_key}"
        elif api_key and conn.probe_auth == "query":
            params[conn.probe_query_param] = api_key
        t0 = time.perf_counter()
        r = requests.get(url, headers=headers, params=params or None, timeout=timeout)
        elapsed = int((time.perf_counter() - t0) * 1000)
        ok = r.status_code < 400
        return {"ok": ok, "http_status": r.status_code, "latency_ms": elapsed,
                "error": "" if ok else f"HTTP {r.status_code}"}
    except Exception as exc:  # noqa: BLE001 — a failed probe is a verdict, not a 500
        return {"ok": False, "http_status": 0, "latency_ms": 0,
                "error": f"{type(exc).__name__}: {str(exc)[:140]}"}


# ── writing an exchange credential — delegate to the existing .env writer ─────

def set_exchange_credential(conn: Connection, api_key: str, extra: Dict[str, str]) -> Dict[str, Any]:
    """Route exchange keys through the trader's existing .env writer + restart
    intent (never the operator keystore). Returns a status dict."""
    creds: Dict[str, str] = {}
    if api_key and conn.key_env:
        creds[conn.key_env] = api_key
    for var, val in (extra or {}).items():
        if val:
            creds[var] = val
    if not creds:
        return {"ok": False, "error": "no credentials provided"}
    try:
        from aureon.exchanges.unified_market_status_server import (
            _extract_env_updates,
            _record_env_update_intent,
            _write_env_updates,
        )

        updates = _extract_env_updates(conn.id, creds)
        if not updates:
            return {"ok": False, "error": "no recognised credential keys"}
        _write_env_updates(updates)
        _record_env_update_intent(conn.id, list(updates.keys()))
        return {"ok": True, "updated_keys": list(updates.keys()),
                "restart_required": True,
                "note": "written to .env; the trading process picks it up on its next restart"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"exchange writer unavailable: {type(exc).__name__}: {str(exc)[:120]}"}


__all__ = ["build_view", "readiness", "probe", "connection_public", "set_exchange_credential"]
