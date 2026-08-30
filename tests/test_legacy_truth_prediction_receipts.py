from __future__ import annotations

import importlib.util
import math
from dataclasses import asdict
from pathlib import Path

from scripts.validation.validate_real_data_contract import scan_text_file


ROOT = Path(__file__).resolve().parents[1]
ENGINE_PATH = (
    ROOT
    / "Kings_Accounting_Suite"
    / "aureon_systems"
    / "aureon_truth_prediction_engine.py"
)
QUEEN_PATH = (
    ROOT / "Kings_Accounting_Suite" / "aureon_systems" / "queen_eternal_machine.py"
)
LAYER_PATH = ROOT / "Kings_Accounting_Suite" / "aureon_systems" / "queen_layer.py"


def _load_engine_module():
    spec = importlib.util.spec_from_file_location("legacy_truth_prediction_receipts", ENGINE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _market_receipt(timestamp: float, *, price: float = 100.0) -> dict:
    return {
        "provider": "exchange-a",
        "provider_receipt_type": "ticker",
        "receipt_id": f"market-{timestamp}",
        "symbol": "BTCUSD",
        "provider_timestamp": timestamp,
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "eligible_for_prediction": True,
        "price": price,
        "change_24h": 1.5,
        "volume_24h": 250000.0,
        "momentum_30s": 0.2,
        "volatility_30s": 0.1,
        "hz_frequency": 275.0,
    }


def test_legacy_truth_prediction_requires_linked_fresh_receipts_and_is_inert(tmp_path, monkeypatch):
    module = _load_engine_module()
    monkeypatch.chdir(tmp_path)
    engine = module.TruthPredictionEngine(max_receipt_age_seconds=30.0)
    snapshot = module.MarketSnapshot(
        symbol="BTCUSD",
        price=100.0,
        change_24h=1.5,
        volume_24h=250000.0,
        momentum_30s=0.2,
        volatility_30s=0.1,
        hz_frequency=275.0,
        timestamp=1000.0,
    )

    refused = engine.generate_prediction(snapshot, observed_at=1002.0)
    assert not refused
    assert refused.data_status == "no_data"
    assert refused.eligible_for_learning is False
    assert not any(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in asdict(refused).values()
    )

    market = _market_receipt(1000.0)
    hnc = {
        "provider": "aureon-hnc",
        "provider_receipt_type": "hnc_probability",
        "receipt_id": "hnc-1",
        "market_receipt_id": market["receipt_id"],
        "symbol": "BTCUSD",
        "provider_timestamp": 1001.0,
        "data_status": "complete",
        "truth_status": "real_observed",
        "generated_values": False,
        "eligible_for_prediction": True,
        "pattern_key": ["strong", "clear", "near", "up", "strong"],
        "win_probability": 0.8,
        "pattern_confidence": 0.75,
        "queen_approved": True,
    }
    auris = {
        "provider": "dr-auris",
        "provider_receipt_type": "geometric_validation",
        "receipt_id": "auris-1",
        "market_receipt_id": market["receipt_id"],
        "hnc_receipt_id": hnc["receipt_id"],
        "symbol": "BTCUSD",
        "provider_timestamp": 1002.0,
        "data_status": "complete",
        "truth_status": "real_observed",
        "generated_values": False,
        "eligible_for_prediction": True,
        "approved": True,
        "geometric_truth": 0.75,
    }

    prediction = engine.generate_prediction(
        snapshot,
        horizon_seconds=30.0,
        market_receipt=market,
        hnc_receipt=hnc,
        auris_receipt=auris,
        observed_at=1002.0,
    )
    assert prediction
    assert prediction.predicted_direction == "UP"
    assert prediction.predicted_change_pct == 0.2 * 0.8 * 0.75
    assert prediction.pattern_key == tuple(hnc["pattern_key"])
    assert prediction.market_receipt_id == market["receipt_id"]
    assert prediction.hnc_receipt_id == hnc["receipt_id"]
    assert prediction.auris_receipt_id == auris["receipt_id"]

    stale = engine.generate_prediction(
        snapshot,
        market_receipt=market,
        hnc_receipt=hnc,
        auris_receipt=auris,
        observed_at=1040.0,
    )
    assert not stale
    assert stale.reason == "provider_receipt_stale"

    outcome = _market_receipt(1031.0, price=101.0)
    outcome["eligible_for_learning"] = True
    outcome["prediction_receipt_id"] = auris["receipt_id"]
    outcome_snapshot = module.MarketSnapshot(
        symbol="BTCUSD",
        price=101.0,
        change_24h=1.5,
        volume_24h=250000.0,
        momentum_30s=0.2,
        volatility_30s=0.1,
        hz_frequency=275.0,
        timestamp=1031.0,
    )
    validated = engine.validate_predictions(
        outcome_snapshot,
        market_receipt=outcome,
        observed_at=1032.0,
    )
    assert validated.data_status == "live"
    assert validated.eligible_for_learning is True
    assert len(validated) == 1
    assert validated[0].actual_change_pct == 1.0
    expected_truth = math.exp(-abs(1.0 - abs(prediction.predicted_change_pct / 1.0)))
    assert validated[0].geometric_truth == expected_truth
    assert list(tmp_path.iterdir()) == []

    queen_source = QUEEN_PATH.read_text(encoding="utf-8")
    truth_block = queen_source[
        queen_source.index("# 📺 LIVE TV STATION - Validate Predictions") :
        queen_source.index("# 1. PROTECT - ORCA KILL CYCLE DEFENSE")
    ]
    assert "TruthPredictionEngine()" not in queen_source
    assert "MarketSnapshot(" not in truth_block
    assert "datetime.now" not in truth_block
    assert "prediction_observation_supplier" in truth_block

    layer_source = LAYER_PATH.read_text(encoding="utf-8")
    assert '"aureon_truth_prediction_engine",       {})' in layer_source
    for path in (ENGINE_PATH, QUEEN_PATH, LAYER_PATH):
        assert scan_text_file(path, ROOT) == []
