"""Hermetic dashboard data contract for Ocean Scanner and detection state."""

from __future__ import annotations

import asyncio
import json

from aureon.scanners import aureon_ocean_scanner as ocean_module
from aureon.scanners.aureon_ocean_scanner import OceanOpportunity, OceanScanner


def test_dashboard_data_contract_uses_scanner_and_local_detection(
    monkeypatch,
    tmp_path,
):
    """Build dashboard fields from deterministic scanner output and local state."""
    monkeypatch.setattr(ocean_module, "THOUGHT_BUS_AVAILABLE", False)
    monkeypatch.setattr(ocean_module, "CHIRP_BUS_AVAILABLE", False)

    scanner = OceanScanner({"kraken": object()})
    scanner.kraken_universe = {"XBTUSD", "ETHUSD"}
    scanner.total_symbols_scanned = 2
    expected = OceanOpportunity(
        symbol="XBTUSD",
        exchange="kraken",
        opportunity_type="momentum",
        current_price=60_000.0,
        momentum_24h=2.5,
        ocean_score=0.91,
        confidence=0.88,
        expected_pnl=0.01,
        reason="receipt-backed fixture",
    )

    async def _scan_exchange(exchange, universe, *, limit):
        assert exchange == "kraken"
        assert universe == {"XBTUSD", "ETHUSD"}
        assert limit == 25
        return [expected]

    monkeypatch.setattr(scanner, "_scan_exchange_universe", _scan_exchange)
    opportunities = asyncio.run(scanner.scan_ocean(limit=100))
    summary = scanner.get_ocean_summary()

    report_path = tmp_path / "bot_intelligence_report.json"
    report_path.write_text(
        json.dumps({
            "all_bots": {
                "bot-1": {
                    "size_class": "whale",
                    "role": "coordinator",
                    "owner_name": "Druidic Desk",
                    "symbol": "XBTUSD",
                },
                "bot-2": {"size_class": "bot", "symbol": "ETHUSD"},
            }
        }),
        encoding="utf-8",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    bots = report["all_bots"]
    whales = sum(
        info.get("size_class", "").lower() == "whale"
        or info.get("role", "").lower() == "coordinator"
        for info in bots.values()
    )
    firms = {
        info["owner_name"]
        for info in bots.values()
        if isinstance(info.get("owner_name"), str)
    }

    dashboard_data = {
        "ocean": {
            "universe_size": summary["universe_size"]["total"],
            "hot_opportunities": len(opportunities),
            "scan_count": summary["scan_count"],
            "top_5_count": len(summary["top_5"]),
        },
        "detection": {
            "total_bots": len(bots),
            "whales": whales,
            "hives": len(firms),
        },
    }

    assert dashboard_data == {
        "ocean": {
            "universe_size": 2,
            "hot_opportunities": 1,
            "scan_count": 1,
            "top_5_count": 1,
        },
        "detection": {"total_bots": 2, "whales": 1, "hives": 1},
    }
    assert summary["top_5"][0]["symbol"] == "XBTUSD"
