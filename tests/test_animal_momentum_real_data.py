from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from aureon.scanners import aureon_animal_momentum_scanners as animal
from aureon.scanners.aureon_live_momentum_hunter import HuntResult, LiveMomentumHunter


def _raw_bars(now: float, *, count: int = 3):
    return [
        {
            "open": 100.0 + index,
            "high": 102.0 + index,
            "low": 99.0 + index,
            "close": 101.0 + index,
            "volume": 10.0 + index,
            "timestamp": now - (count - index) * 60,
        }
        for index in range(count)
    ]


def _proven_opportunity(now: float) -> animal.AnimalOpportunity:
    return animal.AnimalOpportunity(
        symbol="BTCUSD",
        side="buy",
        move_pct=-1.2,
        net_pct=0.8,
        volume=100.0,
        reason="provider bars",
        truth_status="real_derived",
        source_id="alpaca_crypto_bars_1h",
        source_timestamp=now,
        received_at=now,
        generated_values=False,
        eligible_for_external_action=True,
    )


class _Bridge:
    def __init__(self):
        self.calls = []

    def is_move_profitable(self, move_pct):
        return True, "provider_cost_policy"

    def calculate_net_profit(self, move_pct):
        return move_pct - 0.1

    def execute_with_trailing_stop(self, **kwargs):
        self.calls.append(kwargs)
        return {"id": "provider-order-1"}


class _Alpaca:
    def __init__(self):
        self.calls = []

    def _resolve_symbol(self, symbol):
        return symbol

    def get_crypto_bars(self, symbols, timeframe, limit):
        self.calls.append((symbols, timeframe, limit))
        return {"bars": {}}

    def place_market_order(self, *args):
        self.calls.append(args)
        return {"id": "provider-order-2"}


def test_provider_bars_require_complete_fresh_source_evidence():
    now = time.time()
    complete = _raw_bars(now)
    normalised = animal._normalise_provider_bars(
        complete,
        source_id="provider-bars",
        received_at=now,
    )
    assert len(normalised) == len(complete)
    assert normalised[-1]["truth_status"] == "live"
    assert normalised[-1]["source_id"] == "provider-bars"
    assert normalised[-1]["generated_values"] is False

    missing_high = _raw_bars(now)
    missing_high[-1].pop("high")
    assert animal._normalise_provider_bars(
        missing_high,
        source_id="provider-bars",
        received_at=now,
    ) == []

    stale = _raw_bars(now - animal.MAX_HISTORICAL_BAR_AGE_SECONDS - 60)
    assert animal._normalise_provider_bars(
        stale,
        source_id="provider-bars",
        received_at=now,
    ) == []


def test_ticker_cache_is_not_expanded_into_invented_ohlc(monkeypatch):
    scanner = object.__new__(animal.BaseAnimalScanner)
    scanner.alpaca = _Alpaca()
    monkeypatch.setattr(animal, "_BATCH_BARS_CACHE", {})
    monkeypatch.setattr(animal, "_BATCH_CACHE_TIME", 0.0)
    monkeypatch.setattr(
        animal,
        "_read_external_cache",
        lambda *_args, **_kwargs: {
            "BTC/USD": {
                "price": 100.0,
                "volume": 50.0,
                "timestamp": time.time(),
            }
        },
    )

    assert scanner._get_all_bars_batched(["BTC/USD"], limit=6) == {}
    assert len(scanner.alpaca.calls) == 1


def test_whale_priority_requires_fresh_proven_signal():
    scanner = object.__new__(animal.BaseAnimalScanner)
    scanner._orca_whale_targets = []
    scanner._orca_target_time = 0.0

    scanner._on_whale_detected({"symbol": "BTC/USD", "coherence": 0.9})
    assert scanner._orca_whale_targets == []

    now = time.time()
    scanner._on_whale_detected(
        {
            "symbol": "BTC/USD",
            "coherence": 0.9,
            "truth_status": "real_derived",
            "source_id": "orca_provider_receipt",
            "source_timestamp": now,
            "generated_values": False,
        }
    )
    assert scanner._orca_whale_targets == ["BTC/USD"]
    assert scanner._orca_target_time >= now


def test_wolf_rejects_raw_bars_and_preserves_provenance_on_real_bars():
    now = time.time()
    wolf = object.__new__(animal.AlpacaLoneWolf)
    wolf.bridge = _Bridge()
    wolf._get_crypto_universe = lambda: ["BTC/USD"]
    wolf._get_all_bars_batched = lambda *_args, **_kwargs: {
        "BTC/USD": _raw_bars(now)
    }
    assert wolf.find_targets() == []

    proven_bars = animal._normalise_provider_bars(
        _raw_bars(now),
        source_id="alpaca_crypto_bars_1h",
        received_at=now,
    )
    wolf._get_all_bars_batched = lambda *_args, **_kwargs: {
        "BTC/USD": proven_bars
    }
    result = wolf.find_targets()
    assert len(result) == 1
    assert result[0].truth_status == "real_derived"
    assert result[0].source_id == "alpaca_crypto_bars_1h"
    assert result[0].eligible_for_external_action is True
    assert result[0].generated_values is False


def test_unproven_or_future_signal_cannot_reach_execution_bridge():
    orchestrator = object.__new__(animal.AlpacaSwarmOrchestrator)
    orchestrator.dry_run = False
    orchestrator.bridge = _Bridge()
    orchestrator.alpaca = _Alpaca()

    blocked = orchestrator.execute_opportunity(
        animal.AnimalOpportunity("BTCUSD", "buy", 1.0, 0.5, 10.0),
        1.0,
    )
    assert blocked["status"] == "blocked"
    assert blocked["truth_status"] == "no_data"
    assert orchestrator.bridge.calls == []

    future = _proven_opportunity(time.time() + animal.MAX_SOURCE_CLOCK_SKEW_SECONDS + 60)
    blocked = orchestrator.execute_opportunity(future, 1.0)
    assert blocked["status"] == "blocked"
    assert orchestrator.bridge.calls == []


def test_dry_run_is_not_a_submission_or_learning_receipt():
    now = time.time()
    orchestrator = object.__new__(animal.AlpacaSwarmOrchestrator)
    orchestrator.dry_run = True
    orchestrator.bridge = _Bridge()
    orchestrator.alpaca = _Alpaca()

    result = orchestrator.execute_opportunity(_proven_opportunity(now), 1.0)
    assert result["status"] == "not_submitted"
    assert result["truth_status"] == "dry_run"
    assert result["provider_order_id"] is None
    assert result["filled_qty"] is None
    assert result["filled_avg_price"] is None
    assert result["eligible_for_learning"] is False
    assert orchestrator.bridge.calls == []


def test_provider_acknowledgement_is_submitted_not_filled():
    now = time.time()
    orchestrator = object.__new__(animal.AlpacaSwarmOrchestrator)
    orchestrator.dry_run = False
    orchestrator.bridge = _Bridge()
    orchestrator.alpaca = _Alpaca()

    result = orchestrator.execute_opportunity(_proven_opportunity(now), 1.0)
    assert result["status"] == "submitted"
    assert result["provider_order_id"] == "provider-order-1"
    assert result["eligible_for_learning"] is False
    assert "filled_qty" not in result


def test_hunt_result_requires_complete_signal_and_nexus_provenance():
    base = dict(
        symbol="BTC/USD",
        side="buy",
        scanner_source="wolf",
        momentum_pct=-1.0,
        net_pct=0.8,
        volume=100.0,
        nexus_direction="LONG",
        nexus_probability=0.8,
        nexus_confidence=0.8,
    )
    assert HuntResult(**base).is_valid_opportunity() is False

    now = time.time()
    proven = HuntResult(
        **base,
        truth_status="real_derived",
        source_id="alpaca_crypto_bars_1h",
        source_timestamp=now,
        received_at=now,
        generated_values=False,
        nexus_truth_status="real_derived",
        nexus_source_id="probability_nexus:alpaca_crypto_bars_1m",
        nexus_source_timestamp=now,
        eligible_for_external_action=True,
    )
    assert proven.is_valid_opportunity() is True


def test_queen_failure_is_a_no_data_denial():
    hunter = object.__new__(LiveMomentumHunter)
    hunter.queen = None
    approved, confidence, reason = hunter.ask_queen({"symbol": "BTC/USD"})
    assert approved is False
    assert confidence is None
    assert reason.startswith("NO_DATA")

    hunter.queen = SimpleNamespace(
        get_queen_decision_with_intelligence=lambda _opportunity: (_ for _ in ()).throw(
            RuntimeError("offline")
        )
    )
    approved, confidence, reason = hunter.ask_queen({"symbol": "BTC/USD"})
    assert approved is False
    assert confidence is None
    assert reason.startswith("NO_DATA")


def test_execute_best_stops_before_provider_access_for_unproven_result(capsys):
    hunter = object.__new__(LiveMomentumHunter)
    hunter.equity = 100.0
    hunter.dry_run = False
    unproven = HuntResult(
        symbol="BTC/USD",
        side="buy",
        scanner_source="wolf",
        momentum_pct=-1.0,
        net_pct=0.8,
        volume=100.0,
        nexus_direction="LONG",
        nexus_probability=0.8,
        nexus_confidence=0.8,
        queen_approved=True,
        queen_confidence=0.9,
    )

    assert hunter.execute_best([unproven]) is None
    assert "No proven" in capsys.readouterr().out
