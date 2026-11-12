"""
Aureon SaaS — live platform status ("working").
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Honest health/readiness aggregation across the platform. Composes the existing
health surfaces — the operational core, the system coordinator, and per-domain
reachability — WITHOUT booting the whole organism (that would be heavy and
side-effectful). Degraded/partial states are reported truthfully, not masked.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from aureon.saas.domains import PRODUCT_DOMAINS, domain_report, product_domain_for

logger = logging.getLogger("aureon.saas.status")


def _operational_health() -> Dict[str, Any]:
    try:
        from aureon.core.aureon_operational_core import get_operational_core

        health = get_operational_core().get_health()
        if isinstance(health, dict):
            return {"available": True, **health}
        return {"available": True, "raw": str(health)}
    except Exception as exc:  # noqa: BLE001 — health probe must never crash the endpoint
        return {"available": False, "error": str(exc)}


def _coordinator_state() -> Dict[str, Any]:
    try:
        from aureon.core.aureon_system_coordinator import SystemCoordinator

        coord = SystemCoordinator()
        state = coord.get_coordination_state()
        return {"available": True, "state": state} if isinstance(state, dict) else {"available": True}
    except Exception as exc:  # noqa: BLE001
        logger.debug("coordinator state unavailable: %s", exc)
        return {"available": False, "error": str(exc)}


def get_platform_status() -> Dict[str, Any]:
    """
    Aggregate platform health. Cheap probes only — per-domain module reachability
    (spec on disk, nothing imported)
    + the operational core's own health snapshot + (if present) coordinator state.
    """
    domains = domain_report()
    reachable = sum(1 for d in domains if d["available"])

    # Roll domain reachability up into per-product-domain status.
    pd_reach: Dict[str, List[bool]] = {d: [] for d in PRODUCT_DOMAINS}
    for d in domains:
        pd = product_domain_for(str(d["domain"]))
        pd_reach.setdefault(pd, []).append(bool(d["available"]))
    product_domains = {}
    for pd, flags in pd_reach.items():
        if not flags:
            product_domains[pd] = {"status": "unknown", "reachable": 0, "total": 0}
            continue
        up = sum(1 for f in flags if f)
        product_domains[pd] = {
            "status": "ready" if up == len(flags) else ("degraded" if up else "down"),
            "reachable": up,
            "total": len(flags),
        }

    op = _operational_health()
    coord = _coordinator_state()

    if reachable == len(domains) and op.get("available"):
        overall = "healthy"
    elif reachable == 0:
        overall = "critical"
    else:
        overall = "degraded"

    return {
        "status": overall,
        "domains_reachable": reachable,
        "domains_total": len(domains),
        "product_domains": product_domains,
        "operational_core": op,
        "coordinator": {"available": coord.get("available", False)},
        "note": "Reachability means the module is on disk (spec check, nothing imported); a "
                "domain can be reachable yet fail to import or run degraded "
                "(e.g. optional deps like numpy missing). Health is reported honestly.",
    }


__all__ = ["get_platform_status"]
