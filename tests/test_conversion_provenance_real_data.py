from __future__ import annotations

import os
import asyncio
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")

from aureon.conversion.mycelium_conversion_hub import (  # noqa: E402
    ConversionSignal,
    MyceliumConversionHub,
    MyceliumSignal,
    SystemSignal,
)
from aureon.conversion.pure_conversion_engine import (  # noqa: E402
    Asset,
    CompletedConversion,
    ConversionOpportunity,
    ConversionType,
    PureConversionEngine,
    UnifiedConversionBrain,
)


def _bare_hub() -> MyceliumConversionHub:
    hub = object.__new__(MyceliumConversionHub)
    hub.v14 = None
    hub.probability_nexus = None
    hub.multiverse = None
    hub.miner_brain = None
    hub.harmonic = None
    hub.lighthouse = None
    hub.mycelium = None
    hub.unified_ecosystem = None
    hub.thought_bus = None
    hub.pathways = {}
    hub.signal_history = deque(maxlen=10)
    hub.conversion_history = deque(maxlen=10)
    hub.stats = {
        "signals_generated": 0,
        "conversions_recommended": 0,
        "successful_conversions": 0,
        "total_profit": 0.0,
    }
    return hub


def _signal(
    signal: ConversionSignal,
    confidence: float,
    *,
    system: str = "v14",
    symbol: str = "BTCUSDT",
    observed_at: datetime | None = None,
) -> SystemSignal:
    return SystemSignal(
        system_name=system,
        symbol=symbol,
        signal=signal,
        confidence=confidence,
        score=confidence,
        reason="fresh provider-derived observation",
        source_timestamp=observed_at or datetime.now(timezone.utc),
        provenance=f"{system}:provider_derived",
    )


def test_multiverse_signal_uses_fresh_world_votes_not_random() -> None:
    hub = _bare_hub()
    observed_at = time.time()
    votes = [
        SimpleNamespace(
            symbol="BTCUSDT",
            timestamp=observed_at,
            strength=0.8,
            confidence=0.9,
            signal_type="BUY",
        )
        for _ in range(3)
    ]
    worlds = [
        SimpleNamespace(state=SimpleNamespace(last_signal=vote))
        for vote in votes
    ]

    class Consensus:
        @staticmethod
        def compute_consensus(received):
            assert received == votes
            return {"action": "BUY", "strength": 0.8, "confidence": 1.0}

    hub.multiverse = SimpleNamespace(worlds=worlds, consensus=Consensus())

    result = hub.get_multiverse_signal("BTCUSDT", 100.0)

    assert result is not None
    assert result.signal is ConversionSignal.BUY
    assert result.score == pytest.approx(0.8)
    assert result.confidence == pytest.approx(1.0)
    assert result.provenance == "internal_multiverse:fresh_world_votes"

    source = Path(
        "aureon/conversion/mycelium_conversion_hub.py"
    ).read_text(encoding="utf-8")
    assert "random.choice" not in source


def test_multiverse_missing_or_stale_vote_is_no_data() -> None:
    hub = _bare_hub()
    stale_vote = SimpleNamespace(
        symbol="BTCUSDT",
        timestamp=time.time() - 10_000,
        strength=0.8,
        confidence=0.9,
        signal_type="BUY",
    )
    hub.multiverse = SimpleNamespace(
        worlds=[SimpleNamespace(state=SimpleNamespace(last_signal=stale_vote))],
        consensus=SimpleNamespace(compute_consensus=lambda votes: {}),
    )

    assert hub.get_multiverse_signal("BTCUSDT", 100.0) is None


def test_hub_incomplete_factor_pair_returns_non_actionable_no_data() -> None:
    hub = _bare_hub()
    hub.v14 = object()
    now = datetime.now(timezone.utc)
    hub.get_v14_signal = lambda symbol, price, volume, source_timestamp: (
        _signal(ConversionSignal.SELL, 0.8, symbol=symbol)
        if symbol == "ETHUSDT"
        else None
    )

    result = hub.get_conversion_signal(
        "ETH",
        "BTC",
        3_000.0,
        100_000.0,
        from_source_timestamp=now,
        to_source_timestamp=now,
        from_volume=100.0,
        to_volume=200.0,
    )

    assert result.data_status == "no_data"
    assert result.proof_eligible is False
    assert result.unified_score == 0.0
    assert "v14" in result.no_data_reason
    assert hub.stats["signals_generated"] == 0
    assert hub.stats["no_data_signals"] == 1
    assert hub.stats["last_no_data_reason"] == result.no_data_reason
    assert list(hub.signal_history) == []


def test_hub_complete_evidence_preserves_weighted_score_equation() -> None:
    hub = _bare_hub()
    hub.v14 = object()
    now = datetime.now(timezone.utc)

    def v14(symbol, price, volume, source_timestamp):
        if symbol == "ETHUSDT":
            return _signal(
                ConversionSignal.SELL,
                0.8,
                symbol=symbol,
                observed_at=source_timestamp,
            )
        return _signal(
            ConversionSignal.BUY,
            0.6,
            symbol=symbol,
            observed_at=source_timestamp,
        )

    hub.get_v14_signal = v14

    result = hub.get_conversion_signal(
        "ETH",
        "BTC",
        3_000.0,
        100_000.0,
        from_source_timestamp=now,
        to_source_timestamp=now,
        from_volume=100.0,
        to_volume=200.0,
    )

    # Existing equation:
    # ((SELL_from * .8 + BUY_to * .6) * V14 .25 + 2) / 4
    expected = (((0.5 * 0.8) + (0.5 * 0.6)) * 0.25 + 2.0) / 4.0
    assert result.unified_score == pytest.approx(expected)
    assert result.unified_confidence == pytest.approx(1 / 8)
    assert result.data_status == "ok"
    assert result.proof_eligible is True
    assert result.participating_systems == ["v14"]
    assert hub.stats["signals_generated"] == 1


def test_hub_stale_price_evidence_never_queries_decision_systems() -> None:
    hub = _bare_hub()
    hub.v14 = object()
    called = False

    def v14(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("stale prices must fail before factor evaluation")

    hub.get_v14_signal = v14
    stale = datetime.now(timezone.utc) - timedelta(hours=1)
    result = hub.get_conversion_signal(
        "ETH",
        "BTC",
        3_000.0,
        100_000.0,
        from_source_timestamp=stale,
        to_source_timestamp=stale,
        from_volume=100.0,
        to_volume=200.0,
    )

    assert result.data_status == "no_data"
    assert result.no_data_reason == "missing_or_stale_provider_timestamp"
    assert called is False


def test_unreceipted_outcome_cannot_train_mycelium_pathways() -> None:
    hub = _bare_hub()
    before = dict(hub.stats)

    recorded = hub.record_conversion_outcome("ETH", "BTC", True, 10.0)

    assert recorded is False
    assert hub.stats == before


def _opportunity() -> ConversionOpportunity:
    return ConversionOpportunity(
        from_asset="ETH",
        to_asset="BTC",
        conversion_type=ConversionType.STRENGTH_SWAP,
        from_price=3_000.0,
        to_price=100_000.0,
    )


def test_pure_brain_propagates_hub_no_data_without_numeric_fallback() -> None:
    brain = object.__new__(UnifiedConversionBrain)
    brain.mycelium_hub = SimpleNamespace(
        get_conversion_signal=lambda **kwargs: MyceliumSignal(
            from_asset="ETH",
            to_asset="BTC",
            data_status="no_data",
            no_data_reason="missing_stale_or_malformed_factor:multiverse",
            proof_eligible=False,
        )
    )
    now = datetime.now(timezone.utc)
    opp = brain.score_conversion(
        _opportunity(),
        {"ETHUSDT": 3_000.0, "BTCUSDT": 100_000.0},
        {},
        {"ETHUSDT": now, "BTCUSDT": now},
        {"ETHUSDT": 100.0, "BTCUSDT": 200.0},
    )

    assert opp.data_status == "no_data"
    assert opp.proof_eligible is False
    assert opp.unified_score == 0.0
    assert "multiverse" in opp.no_data_reason


def test_no_data_opportunity_cannot_call_broker_or_mutate_portfolio() -> None:
    class Broker:
        def __init__(self):
            self.calls = []

        def place_market_order(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            raise AssertionError("broker must not be called for no_data")

    engine = object.__new__(PureConversionEngine)
    engine.dry_run = False
    engine.kraken = Broker()
    engine.portfolio = {"ETH": Asset("ETH", 1.0, 3_000.0, 3_000.0)}
    opp = _opportunity()
    before = engine.portfolio["ETH"].amount

    executed = asyncio.run(engine._execute_conversion(opp))

    assert executed is False
    assert engine.kraken.calls == []
    assert engine.portfolio["ETH"].amount == before


def test_unproven_completed_conversion_cannot_train_pure_brain() -> None:
    brain = object.__new__(UnifiedConversionBrain)
    brain.conversion_history = []
    brain.successful_pairs = {}
    conversion = CompletedConversion(
        id="CONV-1",
        from_asset="ETH",
        to_asset="BTC",
        from_amount=1.0,
        to_amount=0.03,
        from_price=3_000.0,
        to_price=100_000.0,
        usd_value=3_000.0,
        conversion_type=ConversionType.STRENGTH_SWAP,
        unified_score=0.9,
        timestamp=datetime.now(),
    )

    assert brain.record_conversion(conversion, True) is False
    assert brain.conversion_history == []
    assert brain.successful_pairs == {}
