"""Offline proof that the fusion join stays disarmed and keeps synthetic evidence out."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aureon_fusion.join import REPO_ROOT, join_layers, status_report

FIELD = {
    "time_tag": "2026-10-15T06:00:00",
    "Kp": 1.33,
    "a_running": 5,
    "station_count": 8,
}
MARKET = {"symbol": "BTCUSDT", "price": "81290.01000000"}


def _field(_url: str) -> bytes:
    return json.dumps([FIELD]).encode()


def _market(_url: str) -> bytes:
    return json.dumps(MARKET).encode()


def test_status_is_offline_and_disarmed():
    report = status_report()
    assert report["schema"] == "aureon.fusion.v1"
    assert report["live_trading"] is False
    assert report["paper_default"] is True
    assert report["dry_run_default"] is True
    assert report["may_act"] is False
    assert report["action_eligible"] is False
    assert report["capabilities"]["market"]["present"] is True
    assert report["capabilities"]["field"]["present"] is True
    assert report["capabilities"]["operating"]["present"] is True
    assert {item["id"] for item in report["unavailable_sources"]} >= {
        "skaila",
        "founder-mirror",
        "quantum-bloom",
        "quackers-war-ready",
    }


def test_market_adapter_matches_the_sero_module():
    original = (REPO_ROOT / "organism" / "public_market.py").read_bytes()
    adapter = (REPO_ROOT / "sources" / "Aureon-Trading--Project-Sero" / "organism" / "public_market.py").read_bytes()
    assert hashlib.sha256(original).hexdigest() == hashlib.sha256(adapter).hexdigest()


def test_join_records_public_readings_and_rejects_synthetic_evidence():
    joined = join_layers(
        evidence={"authority": "synthetic", "gate": "HOLD", "readiness": 62, "adoption": 43},
        field_transport=_field,
        market_transport=_market,
    )
    assert joined["may_act"] is False
    assert joined["action_eligible"] is False
    assert joined["economic_mutation"] is False
    assert joined["status"] == "hold"
    by_id = {layer["id"]: layer for layer in joined["layers"]}
    assert by_id["skaila"]["truth_status"] == "no_data"
    assert by_id["skaila"]["reason"] == "sample_or_synthetic_evidence_excluded"
    assert by_id["skaila"]["observation"] is None
    assert by_id["nexus"]["truth_status"] == "real_observed"
    assert by_id["nexus"]["observation"]["kp"] == 1.33
    assert by_id["nexus"]["may_act"] is False
    assert by_id["sero"]["observation"]["price"] == "81290.01000000"
    assert by_id["sero"]["observation"]["order_count"] == 0
    assert by_id["sero"]["may_act"] is False
    assert by_id["founder-mirror"]["reason"] == "decision_contract_missing"
    assert by_id["aureon-os"]["may_act"] is False


def test_live_trading_defaults_are_paper_in_the_vendored_aqts_template():
    example = (REPO_ROOT / "sources" / "AUREON-QUANTUM-TRADING-SYSTEM-AQTS-" / ".env.example").read_text(encoding="utf-8")
    assert "BINANCE_TESTNET=true" in example
    assert "PAPER_MODE=true" in example
    assert "BINANCE_API_KEY=your_binance_api_key_here" in example
    tree = REPO_ROOT / "sources" / "AUREON-QUANTUM-TRADING-SYSTEM-AQTS-"
    assert not (tree / "scripts" / "start_honey.sh").exists()
    offenders = []
    for path in tree.rglob("*.ts"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "testnet: false" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []
