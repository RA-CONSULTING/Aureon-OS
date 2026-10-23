"""Aureon Fusion join: one read-only composition of the source layers.

Live trading is off. The action gate stays closed. Observations are optional
and never place an order.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

SCHEMA = "aureon.fusion.v1"
REPO_ROOT = Path(__file__).resolve().parents[1]

UNAVAILABLE = (
    {
        "id": "skaila",
        "repo": "skaila-journey-platform",
        "reason": "private repo not readable with this credential (HTTP 404)",
    },
    {
        "id": "founder-mirror",
        "repo": "aureon-founder-mirror",
        "reason": "private repo not readable with this credential (HTTP 404)",
    },
    {
        "id": "quantum-bloom",
        "repo": "aureon-quantum-bloom",
        "reason": "private repo not readable with this credential (HTTP 404)",
    },
    {
        "id": "quackers-war-ready",
        "repo": "Aueron-Trading-Quantum-Quackers-War-Ready-Version-",
        "reason": "private repo not readable with this credential (HTTP 404); in-tree strategy module retained",
    },
)


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def os_root(root: Path | None = None) -> Path:
    """The Aureon OS tree. The fusion workspace nests it; the public repo is the OS."""

    root = root or REPO_ROOT
    nested = root / "aureon-os-upstream"
    if (nested / "aureon" / "organism" / "repository_layers.py").is_file():
        return nested
    return root


def capability_files() -> dict[str, dict[str, Any]]:
    """Presence of each wired capability. Does not read the network."""

    root = REPO_ROOT
    upstream = os_root(root)
    specs = {
        "operating": upstream / "aureon" / "organism" / "repository_layers.py",
        "plant_atlas": upstream / "aureon" / "bio" / "plant_atlas" / "__init__.py",
        "market": root / "organism" / "public_market.py",
        "field": root / "sources" / "NEXUS-LIVE-FEED-" / "organism" / "public_field.py",
        "quackers_strategy": upstream / "aureon" / "strategies" / "quantum_quackers.py",
        "aqts": root / "sources" / "AUREON-QUANTUM-TRADING-SYSTEM-AQTS-" / "README.md",
        "nexus_feed": root / "sources" / "NEXUS-LIVE-FEED-" / "src" / "server.js",
        "self_repair": upstream / "aureon" / "autonomous" / "aureon_sandbox_self_repair.py",
    }
    return {
        name: {"path": str(path.relative_to(root)), "present": path.is_file(), "sha256": _sha256(path)}
        for name, path in specs.items()
    }


def join_layers(
    evidence: Mapping[str, Any] | None = None,
    field_transport: Callable[[str], bytes] | None = None,
    market_transport: Callable[[str], bytes] | None = None,
) -> dict[str, Any]:
    """Load the OS composer and join the layers that are actually on disk.

    Synthetic evidence is rejected by the OS composer. This wrapper does not
    add an override.
    """

    upstream = os_root(REPO_ROOT)
    if str(upstream) not in sys.path:
        sys.path.insert(0, str(upstream))
    from aureon.organism.repository_layers import compose_repository_layers

    layers = compose_repository_layers(
        repos_root=REPO_ROOT / "sources",
        evidence=evidence,
        field_transport=field_transport,
        market_transport=market_transport,
    )
    try:
        from aureon.autonomous.autonomy_mode import guardrails_open

        opened = guardrails_open()
    except Exception:
        opened = False
    if not opened and (layers.get("may_act") is not False or layers.get("action_eligible") is not False):
        layers = dict(layers)
        layers["may_act"] = False
        layers["action_eligible"] = False
        layers["status"] = "hold"
        layers["reason"] = "fusion_refused_layer_action"
    return layers


def status_report() -> dict[str, Any]:
    """Offline status. No network and no orders.

    The public default is full. Live trading follows exchange keys. may_act
    is on unless the mode is guarded or the kill switch is on. This report
    does not place an order.
    """

    try:
        from aureon.autonomous.autonomy_mode import runtime_authority

        auth = runtime_authority()
        live = auth.get("live_trading") is True
        may_act = auth.get("may_act") is True
    except Exception:
        live = False
        may_act = False
    return {
        "schema": SCHEMA,
        "name": "Aureon Fusion",
        "live_trading": live,
        "paper_default": not live,
        "dry_run_default": not live,
        "arm_env": "AUREON_FUSION_ARM_LIVE",
        "may_act": may_act,
        "action_eligible": may_act,
        "deployed": False,
        "publication_target": "RA-CONSULTING/Aureon-OS",
        "publication_status": "pull-request-into-public-main",
        "capabilities": capability_files(),
        "unavailable_sources": list(UNAVAILABLE),
    }
