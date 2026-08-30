import importlib.util
import sys
import time
import types
from pathlib import Path

import pytest


def test_legacy_accounting_nexus_requires_fresh_receipted_market_data(
    monkeypatch, tmp_path
):
    """The accounting mirror must observe, not invent, when evidence is absent."""
    baton = types.ModuleType("aureon_baton_link")
    baton.link_system = lambda _name: None
    thought_bus = types.ModuleType("aureon_thought_bus")
    thought_bus.ThoughtBus = object
    thought_bus.Thought = object

    class ConnectedProvider:
        dry_run = True

        def ping(self):
            return True

    connected_provider = ConnectedProvider()
    binance = types.ModuleType("binance_client")
    binance.BinanceClient = ConnectedProvider
    binance.get_binance_client = lambda: connected_provider

    monkeypatch.setitem(sys.modules, "aureon_baton_link", baton)
    monkeypatch.setitem(sys.modules, "aureon_thought_bus", thought_bus)
    monkeypatch.setitem(sys.modules, "binance_client", binance)
    monkeypatch.chdir(tmp_path)

    source = (
        Path(__file__).resolve().parents[1]
        / "Kings_Accounting_Suite"
        / "aureon_systems"
        / "aureon_nexus.py"
    )
    spec = importlib.util.spec_from_file_location("legacy_accounting_nexus_test", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)

    nexus = module.AureonNexus(use_mycelium=False)
    absent = nexus.get_market_data()
    assert absent["truth_status"] == "no_data"
    assert absent["reason"] == "binance_unavailable"
    assert absent["generated_values"] is False
    assert absent["eligible_for_external_action"] is False

    equation_history_before = list(nexus.master_equation.history)
    cycle = nexus.run_cycle()
    assert cycle["truth_status"] == "no_data"
    assert cycle["signal"] == "NO_DATA"
    assert cycle["lambda"] is None
    assert cycle["eligible_for_learning"] is False
    assert list(nexus.master_equation.history) == equation_history_before
    assert nexus.coherence_history == []

    # Connectivity alone is not an account-balance or market-feature receipt.
    assert nexus.connect_binance() is True
    unavailable = nexus.get_market_data()
    assert unavailable["reason"] == "provider_feature_receipt_unavailable"
    assert nexus.queen_hive.initial_capital == 0.0

    class FeatureProvider(ConnectedProvider):
        def __init__(self, receipt):
            self.receipt = receipt

        def get_market_features(self, _symbol):
            return dict(self.receipt)

    receipt = {
        "price": 101_250.5,
        "volatility": 0.31,
        "momentum": 0.62,
        "sentiment": 0.57,
        "trend_strength": 0.66,
        "pattern_match": 0.73,
        "harmony": 0.59,
        "volume_ratio": 0.48,
        "correlation": 0.52,
        "truth_status": "live",
        "source_id": "binance.market_features.BTCUSDT",
        "source_timestamp": time.time(),
        "generated_values": False,
    }
    nexus.binance = FeatureProvider(receipt)
    validated = nexus.get_market_data()
    assert validated["truth_status"] == "real_derived"
    assert validated["decision_status"] == "eligible"
    assert validated["price"] == receipt["price"]
    assert validated["source_id"] == receipt["source_id"]
    assert validated["eligible_for_external_action"] is True

    real_cycle = nexus.run_cycle()
    assert real_cycle["truth_status"] == "real_derived"
    assert real_cycle["source_timestamp"] == receipt["source_timestamp"]
    assert len(nexus.master_equation.history) == 1

    stale = dict(receipt, source_timestamp=time.time() - 1_000)
    nexus.binance = FeatureProvider(stale)
    rejected = nexus.get_market_data()
    assert rejected["truth_status"] == "no_data"
    assert rejected["reason"] == "market_feature_receipt_stale"

    generated = dict(receipt, generated_values=True)
    nexus.binance = FeatureProvider(generated)
    rejected = nexus.get_market_data()
    assert rejected["reason"] == "generated_or_unproven_market_features"

    with pytest.raises(ValueError, match="incomplete market feature receipt"):
        module.MasterEquation().update_substrate({"momentum": 0.5})

    nexus.binance = FeatureProvider(receipt)
    dry_run = nexus._execute_signal("BUY", 0.95, validated)
    assert dry_run["status"] == "not_submitted"
    assert dry_run["provider_order_id"] is None
    assert dry_run["eligible_for_external_action"] is False
