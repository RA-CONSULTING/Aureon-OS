from __future__ import annotations

import math
import time

import pytest

from aureon.core import aureon_nexus as nexus


def _feature_receipt(*, source_timestamp: float | None = None, **overrides):
    receipt = {
        "price": 64_321.25,
        "volatility": 0.2,
        "momentum": 0.7,
        "sentiment": 0.6,
        "trend_strength": 0.8,
        "pattern_match": 0.4,
        "harmony": 0.9,
        "volume_ratio": 0.5,
        "correlation": 0.3,
        "truth_status": "live",
        "source_id": "binance.klines:BTCUSDT:15m",
        "source_timestamp": source_timestamp if source_timestamp is not None else time.time() - 1.0,
        "generated_values": False,
    }
    receipt.update(overrides)
    return receipt


class FeatureBinance:
    dry_run = True

    def __init__(self, receipt):
        self.receipt = receipt

    def get_market_features(self, symbol):
        assert symbol == "BTCUSDT"
        return dict(self.receipt)


def test_master_equation_rejects_incomplete_or_nonfinite_features():
    equation = nexus.MasterEquation()

    with pytest.raises(ValueError, match="incomplete market feature receipt"):
        equation.update_substrate({"momentum": 0.5})

    malformed = _feature_receipt()
    malformed["correlation"] = math.nan
    with pytest.raises(ValueError, match="invalid normalized market feature"):
        equation.update_substrate(malformed)


def test_master_equation_preserves_existing_math_for_complete_evidence():
    receipt = _feature_receipt()
    equation = nexus.MasterEquation()

    substrate = equation.update_substrate(receipt)
    expected_total = 0.0
    for node in nexus.AURIS_NODES.values():
        role = node["role"]
        if role == "stability":
            value = 1.0 - receipt["volatility"]
        elif role == "emotion":
            value = receipt["sentiment"]
        elif role == "sensing":
            value = receipt["trend_strength"]
        elif role == "memory":
            value = receipt["pattern_match"]
        elif role == "love":
            value = receipt["harmony"]
        elif role == "infrastructure":
            value = receipt["volume_ratio"]
        elif role == "symbiosis":
            value = receipt["correlation"]
        else:
            value = receipt[role]
        phase = (node["freq"] / nexus.LOVE_FREQUENCY) * math.pi
        expected_total += value * math.cos(phase) * node["weight"]

    assert substrate == pytest.approx(
        (expected_total / len(nexus.AURIS_NODES) + 1.0) / 2.0
    )


def test_missing_feature_reader_is_visible_no_data_and_does_not_mutate_hnc():
    organism = nexus.AureonNexus(use_mycelium=False)
    organism.binance = object()

    result = organism.run_cycle()

    assert result["truth_status"] == "no_data"
    assert result["signal"] == "NO_DATA"
    assert result["eligible_for_external_action"] is False
    assert result["generated_values"] is False
    assert result["lambda"] is None
    assert list(organism.master_equation.history) == []
    assert organism.coherence_history == []


def test_stale_or_generated_feature_receipts_are_no_data():
    organism = nexus.AureonNexus(use_mycelium=False)
    organism.binance = FeatureBinance(
        _feature_receipt(
            source_timestamp=time.time() - nexus.MARKET_RECEIPT_MAX_AGE_SECONDS - 1.0
        )
    )
    assert organism.get_market_data()["reason"] == "market_feature_receipt_stale"

    organism.binance = FeatureBinance(_feature_receipt(generated_values=True))
    assert organism.get_market_data()["reason"] == "generated_or_unproven_market_features"


def test_complete_provider_features_drive_live_derived_cycle(monkeypatch):
    organism = nexus.AureonNexus(use_mycelium=False)
    organism.binance = FeatureBinance(_feature_receipt())
    published = []
    monkeypatch.setattr(nexus.NEXUS, "publish", published.append)
    monkeypatch.setattr(nexus.NEXUS, "get_consensus", lambda: ("NEUTRAL", 0.0))
    monkeypatch.setattr(organism.master_equation, "display", lambda: None)

    result = organism.run_cycle()

    assert result["truth_status"] == "real_derived"
    assert result["eligible_for_external_action"] is True
    assert result["generated_values"] is False
    assert result["source_id"] == "binance.klines:BTCUSDT:15m"
    assert result["source_timestamp"] < result["received_at"]
    assert len(published) == 1
    assert len(organism.master_equation.history) == 1


def test_compatibility_fallback_never_generates_market_values(monkeypatch):
    monkeypatch.setenv("AUREON_ALLOW_SIM_FALLBACK", "1")
    organism = nexus.AureonNexus(use_mycelium=False)

    receipt = organism._default_market_data()

    assert receipt["truth_status"] == "no_data"
    assert receipt["source_timestamp"] is None
    assert receipt["eligible_for_external_action"] is False
    assert "price" not in receipt


def test_dry_execution_receipt_is_not_submitted_or_learnable():
    organism = nexus.AureonNexus(use_mycelium=False)
    organism.binance = FeatureBinance(_feature_receipt())
    market_receipt = organism._validated_market_receipt(
        _feature_receipt(), received_at=time.time()
    )

    receipt = organism._execute_signal("BUY", 0.95, market_receipt)

    assert receipt["status"] == "not_submitted"
    assert receipt["provider_order_id"] is None
    assert receipt["fill"] is None
    assert receipt["eligible_for_external_action"] is False
    assert receipt["eligible_for_learning"] is False


def test_direct_execution_rejects_unproven_market_data():
    organism = nexus.AureonNexus(use_mycelium=False)
    organism.binance = FeatureBinance(_feature_receipt())

    receipt = organism._execute_signal("BUY", 0.95, _feature_receipt())

    assert receipt["truth_status"] == "no_data"
    assert receipt["status"] == "not_submitted"
    assert receipt["provider_order_id"] is None


def test_unproven_hive_performance_metrics_are_unknown():
    stats = nexus.QueenHive().get_stats()
    assert stats["win_rate"] is None
    assert stats["roi"] is None
