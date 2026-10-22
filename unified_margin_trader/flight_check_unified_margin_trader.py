#!/usr/bin/env python3
"""Mind-map-backed flight check for the unified margin trader."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "aureon" / "exchanges") not in sys.path:
    sys.path.insert(0, str(ROOT / "aureon" / "exchanges"))

from aureon.exchanges.unified_market_trader import UnifiedMarketTrader
try:
    from aureon.command_centers.aureon_system_hub import SystemRegistry
    SYSTEM_REGISTRY_IMPORT_ERROR = ""
except Exception as exc:
    SystemRegistry = None  # type: ignore[assignment]
    SYSTEM_REGISTRY_IMPORT_ERROR = str(exc)


def _find_system(registry: "SystemRegistry", needle: str) -> bool:
    needle_l = needle.lower()
    return any(needle_l in name.lower() for name in registry.systems.keys())


def run_flight_check() -> Dict[str, object]:
    required_nodes = [
        "kraken_margin_penny_trader",
        "capital_cfd_trader",
        "unified_market_trader",
    ]
    module_files = {
        "unified_market_trader": ROOT / "aureon" / "exchanges" / "unified_market_trader.py",
        "kraken_margin_penny_trader": ROOT / "aureon" / "exchanges" / "kraken_margin_penny_trader.py",
        "capital_cfd_trader": ROOT / "aureon" / "exchanges" / "capital_cfd_trader.py",
    }

    registry = None
    node_results = {name: module_files[name].exists() for name in required_nodes}
    mycelium_systems: List[str] = []
    mind_map: Dict[str, object] = {
        "workspace": str(ROOT),
        "systems_found": 0,
        "required_nodes": node_results,
        "mycelium_systems_found": 0,
        "mycelium_system_examples": [],
    }

    if SystemRegistry is not None:
        registry = SystemRegistry(workspace_path=str(ROOT))
        registry.scan_workspace()
        node_results = {name: _find_system(registry, name) for name in required_nodes}
        mycelium_systems = sorted(
            name for name in registry.systems.keys()
            if "mycel" in name.lower()
        )
        mind_map = {
            "workspace": str(registry.workspace_path),
            "systems_found": len(registry.systems),
            "required_nodes": node_results,
            "mycelium_systems_found": len(mycelium_systems),
            "mycelium_system_examples": mycelium_systems[:10],
        }
    elif SYSTEM_REGISTRY_IMPORT_ERROR:
        mind_map["registry_error"] = SYSTEM_REGISTRY_IMPORT_ERROR

    trader = UnifiedMarketTrader(dry_run=True)
    tick = trader.tick()

    payload = tick.get("payload") or {}
    status_lines: List[str] = trader.get_status_lines()

    mycelium_fields = {
        "mycelium_hives": payload.get("mycelium_hives"),
        "mycelium_agents": payload.get("mycelium_agents"),
        "mycelium_generation": payload.get("mycelium_generation"),
        "max_generation": payload.get("max_generation"),
    }
    nonzero_mycelium = {
        k: v for k, v in mycelium_fields.items()
        if isinstance(v, (int, float)) and float(v) > 0
    }

    static_mycelium_refs = {}
    for name, module_file in module_files.items():
        text = module_file.read_text(encoding="utf-8", errors="ignore")
        static_mycelium_refs[name] = "mycel" in text.lower()

    using_data = []
    not_using_data = []
    if static_mycelium_refs["kraken_margin_penny_trader"]:
        using_data.append("kraken_margin_penny_trader has Mycelium-aware fields in dashboard payload")
    else:
        not_using_data.append("kraken_margin_penny_trader has no Mycelium references")

    if static_mycelium_refs["unified_market_trader"]:
        using_data.append("unified_market_trader contains Mycelium references")
    else:
        not_using_data.append("unified_market_trader has no direct Mycelium references")

    if static_mycelium_refs["capital_cfd_trader"]:
        using_data.append("capital_cfd_trader contains Mycelium references")
    else:
        not_using_data.append("capital_cfd_trader has no Mycelium references")

    if nonzero_mycelium:
        using_data.append("runtime payload contains non-zero Mycelium feed values")
    else:
        not_using_data.append("runtime payload exposes Mycelium fields but all are zero/empty")

    return {
        "mind_map": mind_map,
        "trader": {
            "kraken_ready": bool(trader.kraken_ready),
            "capital_ready": bool(trader.capital_ready),
            "status_lines": status_lines,
            "payload_mode": payload.get("mode"),
            "runtime_sec": payload.get("runtime_sec"),
            "mycelium_payload_fields": mycelium_fields,
            "mycelium_nonzero_fields": nonzero_mycelium,
        },
        "mycelium_feed_audit": {
            "static_references": static_mycelium_refs,
            "using_data": using_data,
            "not_using_data": not_using_data,
        },
    }


def main() -> int:
    report = run_flight_check()

    print("=" * 80)
    print("UNIFIED MARGIN TRADER FLIGHT CHECK (MIND MAP + RUNTIME)")
    print("=" * 80)
    print(json.dumps(report, indent=2, default=str))

    nodes_ok = all(report["mind_map"]["required_nodes"].values())
    trader_ok = report["trader"]["kraken_ready"] or report["trader"]["capital_ready"]

    print("\nSUMMARY")
    print(f"- Mind map wiring: {'PASS' if nodes_ok else 'FAIL'}")
    print(f"- Exchange connectivity: {'PASS' if trader_ok else 'WARN'}")

    if nodes_ok and trader_ok:
        return 0
    if nodes_ok:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
