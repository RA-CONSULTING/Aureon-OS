from __future__ import annotations

import importlib
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


unified = importlib.import_module("aureon.core.aureon_unified")


class ObservedResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class ObservedSession:
    def __init__(self, payload_factory):
        self.payload_factory = payload_factory
        self.calls = []

    def get(self, url, *, timeout):
        self.calls.append((url, timeout))
        return ObservedResponse(self.payload_factory())


@pytest.fixture(autouse=True)
def clear_unified_bus():
    unified.BUS.states.clear()
    unified.BUS.history.clear()
    yield
    unified.BUS.states.clear()
    unified.BUS.history.clear()


def _ticker(
    symbol: str,
    *,
    price: float,
    volume: float,
    change: float,
    source_timestamp: float,
):
    return {
        "symbol": symbol,
        "lastPrice": str(price),
        "quoteVolume": str(volume),
        "highPrice": str(price * 1.02),
        "lowPrice": str(price * 0.98),
        "priceChangePercent": str(change),
        "closeTime": int(source_timestamp * 1000),
    }


def _populated_data(monkeypatch):
    clock = SimpleNamespace(value=1_800_000_000.0)
    sequence = SimpleNamespace(index=0)

    def payload():
        sequence.index += 1
        offset = sequence.index * 0.0001
        return [
            _ticker(
                "ETHBTC",
                price=0.04 + offset,
                volume=25.0 + sequence.index,
                change=2.0,
                source_timestamp=clock.value - 1.0,
            ),
            _ticker(
                "BTCUSDT",
                price=70_000.0 + sequence.index,
                volume=1_000_000.0 + sequence.index,
                change=1.0,
                source_timestamp=clock.value - 1.0,
            ),
        ]

    session = ObservedSession(payload)
    client = SimpleNamespace(base="https://api.binance.com", session=session)
    monkeypatch.setattr(unified.time, "time", lambda: clock.value)
    data = unified.DataIngestionSystem(client)
    for _ in range(20):
        receipt = data.update()
        assert receipt["truth_status"] == "real_observed"
        clock.value += 1.0
    return data, clock, session


def test_import_and_construction_are_provider_and_filesystem_inert(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(repo_root), env.get("PYTHONPATH", "")) if part
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from aureon.core.aureon_unified import UnifiedOrchestrator; "
                "o=UnifiedOrchestrator(); "
                "assert o.client is None; "
                "assert o.total_profit is None"
            ),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == []


def test_ingestion_requires_complete_fresh_provider_timestamps(monkeypatch):
    data, clock, session = _populated_data(monkeypatch)

    ticker = data.get_ticker("ETHBTC")
    assert ticker["provider_id"] == "binance"
    assert ticker["truth_status"] == "real_observed"
    assert ticker["source_timestamp"] < ticker["received_at"]
    assert len(data.get_observations("ETHBTC", 20)) == 20
    assert session.calls[-1][1] == 10

    session.payload_factory = lambda: [
        _ticker(
            "ETHBTC",
            price=0.05,
            volume=25.0,
            change=1.0,
            source_timestamp=clock.value - unified.MARKET_DATA_MAX_AGE_SECONDS - 1,
        )
    ]
    receipt = data.update()
    assert receipt["truth_status"] == "no_data"
    assert "timestamp" in receipt["no_data_reason"]
    assert data.get_ticker("ETHBTC") is None
    assert unified.BUS.read("DataIngestion").ready is False
    assert unified.BUS.read("DataIngestion").coherence is None

    relabel_session = ObservedSession(lambda: [])
    relabelled = unified.DataIngestionSystem(
        SimpleNamespace(
            base="https://provider.invalid",
            session=relabel_session,
        )
    )
    mismatch = relabelled.update()
    assert mismatch["truth_status"] == "no_data"
    assert mismatch["no_data_reason"] == "provider_identity_or_endpoint_mismatch"
    assert relabel_session.calls == []


def test_hnc_pipeline_requires_real_history_and_preserves_provenance(monkeypatch):
    data, clock, _ = _populated_data(monkeypatch)
    lighthouse = unified.LighthouseSystem(data)
    lighthouse_results = lighthouse.evaluate(["ETHBTC"])

    assert lighthouse_results["ETHBTC"]["truth_status"] == "real_derived"
    assert lighthouse_results["ETHBTC"]["source_timestamp"] < clock.value
    assert unified.BUS.read("Lighthouse").ready is True

    master = unified.MasterEquationSystem(data)
    unprimed = master.compute_lambda("ETHBTC")
    assert unprimed["truth_status"] == "no_data"
    assert unprimed["Lambda"] is None

    seed_receipts = []
    for index, value in enumerate((0.45, 0.48, 0.50, 0.52)):
        observed_at = clock.value - 12.0 + index
        seed_receipts.append(
            {
                "Lambda": value,
                "truth_status": "real_derived",
                "provider_id": "binance",
                "source_id": f"persisted-hnc:ETHBTC:{index}",
                "source_timestamp": observed_at,
                "received_at": observed_at + 0.25,
                "generated": False,
            }
        )
    assert master.prime_echo_history("ETHBTC", seed_receipts) is True

    master_results = master.evaluate(["ETHBTC"])
    derived = master_results["ETHBTC"]
    assert derived["truth_status"] == "real_derived"
    assert derived["action_eligible"] is True
    assert derived["Lambda"] == pytest.approx(
        (derived["S"] + derived["O"] + derived["E"]) / 3.0
    )
    assert derived["source_timestamp"] < derived["received_at"]

    rainbow = unified.RainbowBridgeSystem()
    rainbow_result = rainbow.evaluate()
    assert rainbow_result["truth_status"] == "real_derived"
    assert rainbow_result["source_timestamp"] < rainbow_result["received_at"]

    fusion = unified.DecisionFusionSystem()
    fusion_result = fusion.evaluate()
    assert fusion_result["truth_status"] == "real_derived"
    assert fusion_result["source_timestamp"] < fusion_result["received_at"]


def test_rainbow_and_fusion_fail_closed_without_complete_state_receipts(monkeypatch):
    now = 1_800_000_000.0
    monkeypatch.setattr(unified.time, "time", lambda: now)
    unified.BUS.publish(
        unified.SystemState(
            system_name="MasterEquation",
            timestamp=now,
            ready=True,
            coherence=0.8,
            confidence=0.8,
            signal="BUY",
            data={"truth_status": "real_derived"},
        )
    )

    rainbow = unified.RainbowBridgeSystem().evaluate()
    assert rainbow["truth_status"] == "no_data"
    assert rainbow["signal"] == "HOLD"

    fusion = unified.DecisionFusionSystem().evaluate()
    assert fusion["truth_status"] == "no_data"
    assert fusion["decision"] == "HOLD"
    assert fusion["action_eligible"] is False


def test_cycle_returns_not_submitted_intent_and_never_counts_a_trade(monkeypatch):
    now = 1_800_000_000.0
    monkeypatch.setattr(unified.time, "time", lambda: now)
    orchestrator = unified.UnifiedOrchestrator()
    monkeypatch.setattr(
        orchestrator.data,
        "update",
        lambda: {
            "truth_status": "real_observed",
            "source_timestamp": now - 1.0,
            "received_at": now,
        },
    )
    monkeypatch.setattr(
        orchestrator,
        "get_tradeable_symbols",
        lambda: ["ETHBTC"],
    )
    monkeypatch.setattr(
        orchestrator.lighthouse,
        "evaluate",
        lambda symbols: {
            "ETHBTC": {"L": 0.8, "action_eligible": True}
        },
    )
    monkeypatch.setattr(
        orchestrator.master_eq,
        "evaluate",
        lambda symbols: {
            "ETHBTC": {"Lambda": 0.7, "action_eligible": True}
        },
    )
    monkeypatch.setattr(
        orchestrator.rainbow,
        "evaluate",
        lambda: {"emotion": "LOVE", "frequency": 528.0},
    )
    monkeypatch.setattr(
        orchestrator.fusion,
        "evaluate",
        lambda: {
            "decision": "BUY",
            "confidence": 0.9,
            "coherence": 0.8,
            "truth_status": "real_derived",
            "source_timestamp": now - 1.0,
        },
    )
    monkeypatch.setattr(orchestrator, "display_bus_status", lambda: None)
    monkeypatch.setattr(orchestrator.memory, "should_avoid", lambda symbol: False)

    result = orchestrator.run_cycle()

    assert result["action"] == "NOT_SUBMITTED"
    assert result["truth_status"] == "not_submitted"
    assert result["submission_status"] == "not_submitted"
    assert orchestrator.trade_count == 0
    assert orchestrator.total_profit is None


def test_elephant_learning_requires_terminal_fill_and_complete_accounting(
    monkeypatch,
    tmp_path,
):
    now = 1_800_000_000.0
    monkeypatch.setattr(unified.time, "time", lambda: now)
    memory_path = tmp_path / "elephant.json"
    memory = unified.ElephantMemorySystem(str(memory_path))

    assert memory.record_trade("ETHBTC", 0.01, "SELL") is False
    assert memory.symbols == {}
    assert not memory_path.exists()

    receipt = {
        "truth_status": "real_observed",
        "generated": False,
        "provider_id": "binance",
        "status": "FILLED",
        "symbol": "ETHBTC",
        "side": "SELL",
        "order_id": "order-1",
        "trade_id": "trade-1",
        "source_timestamp": now - 1.0,
        "received_at": now,
        "accounting_status": "complete",
        "realized_profit": 0.01,
        "fee_total": 0.0001,
        "fee_asset": "BTC",
        "filled_quantity": 1.0,
        "filled_notional": 0.05,
    }
    assert memory.record_trade(
        "ETHBTC",
        0.01,
        "SELL",
        execution_receipt=receipt,
    ) is True
    assert memory.symbols["ETHBTC"]["trades"] == 1
    assert memory.symbols["ETHBTC"]["profit"] == pytest.approx(0.01)
    assert memory_path.exists()

    reloaded = unified.ElephantMemorySystem(str(memory_path))
    assert reloaded.load() is True
    assert reloaded.symbols["ETHBTC"]["trades"] == 1
    assert reloaded.symbols["ETHBTC"]["profit"] == pytest.approx(0.01)
    assert len(reloaded.symbols["ETHBTC"]["learning_receipts"]) == 1
