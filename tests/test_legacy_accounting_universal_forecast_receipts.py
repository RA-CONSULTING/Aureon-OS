from __future__ import annotations

import inspect
import json

import pytest

from Kings_Accounting_Suite.aureon_systems import aureon_universal_forecast as legacy


NOW = 1_800_000_000.0


class _ReceiptClient:
    def __init__(self, *, source_id: str = "kraken:public:ticker") -> None:
        self.source_id = source_id
        self.calls = 0
        self.receipt_ids: list[str] = []

    def get_ticker_receipt(self, symbol: str) -> dict:
        self.calls += 1
        receipt_id = f"quote-{self.calls}"
        self.receipt_ids.append(receipt_id)
        source_timestamp = NOW - 20.0 + self.calls * 0.1
        return {
            "symbol": symbol,
            "price": 100.0 + self.calls,
            "bid": 99.5 + self.calls,
            "ask": 100.5 + self.calls,
            "volume": 1_000.0 + self.calls,
            "source_id": self.source_id,
            "source_timestamp": source_timestamp,
            "received_at": source_timestamp + 0.01,
            "receipt_id": receipt_id,
            "truth_status": "real_observed",
            "generated_values": False,
        }


def _gate_receipt() -> dict:
    return {
        "source_id": "aureon.hnc_auris.live",
        "source_timestamp": NOW - 1.0,
        "received_at": NOW - 0.5,
        "receipt_id": "gate-1",
        "truth_status": "real_derived",
        "generated_values": False,
        "eligible_for_action": True,
        "earth_open": True,
        "earth_coherence": 0.8,
        "earth_phase_lock": 0.7,
        "earth_phi_boost": 1.2,
        "earth_reason": "fresh_native_receipt",
        "cosmic_open": True,
        "cosmic_phase": "COHERENCE",
        "cosmic_coherence": 0.75,
        "cosmic_distortion": 0.01,
        "cosmic_boost": 1.1,
        "cosmic_joy": 0.6,
        "cosmic_reciprocity": 0.65,
        "planetary_torque": 1.5,
        "lunar_phase": 0.4,
    }


def test_import_constructor_and_cli_are_inert(capsys: pytest.CaptureFixture[str]) -> None:
    source = inspect.getsource(legacy)
    assert "aureon_baton_link" not in source
    assert "os.environ" not in source
    assert "get_24h_ticker" not in source
    assert "configure_default_runtime" not in source
    assert "input(" not in source

    engine = legacy.UniversalForecastEngine()
    assert engine.clients == {}
    assert engine.earth_engine is None
    assert capsys.readouterr().out == ""

    assert legacy.main([]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["truth_status"] == "no_data"
    assert payload["actionable"] is False
    assert payload["accounting_eligible"] is False
    assert payload["learning_eligible"] is False


def test_incomplete_or_cross_venue_inputs_return_numeric_free_no_data() -> None:
    empty = legacy.UniversalForecastEngine(clock=lambda: NOW, sleeper=lambda _: None)
    gates = empty.check_cosmic_gates()
    assert gates.truth_status == "no_data"
    assert gates.earth_coherence is None
    assert gates.combined_multiplier is None
    assert gates.actionable is False
    assert gates.accounting_eligible is False
    assert gates.learning_eligible is False

    forecast = empty.generate_forecast("kraken", "SOLUSD", collect_duration=6)
    assert forecast.action == "NO_DATA"
    assert forecast.probability is None
    assert forecast.position_usd is None
    assert forecast.quantity is None
    assert forecast.actionable is False
    assert forecast.accounting_eligible is False
    assert forecast.learning_eligible is False

    foreign = legacy.UniversalForecastEngine(
        clients={"kraken": _ReceiptClient(source_id="binance:public:ticker")},
        clock=lambda: NOW,
        sleeper=lambda _: None,
    )
    assert foreign.get_price_receipt("kraken", "SOLUSD") is None


def test_complete_fresh_same_venue_receipts_preserve_gate_equation() -> None:
    client = _ReceiptClient()
    engine = legacy.UniversalForecastEngine(
        clients={"kraken": client},
        gate_receipt_supplier=_gate_receipt,
        clock=lambda: NOW,
        sleeper=lambda _: None,
    )

    quote = engine.get_price_receipt("kraken", "SOLUSD")
    assert quote is not None
    assert quote["actionable"] is False
    assert quote["accounting_eligible"] is False
    assert quote["learning_eligible"] is False

    gates = engine.check_cosmic_gates()
    assert gates.evidence_complete is True
    assert gates.combined_multiplier == pytest.approx(1.2 * 1.1 * 1.5)
    assert gates.receipt_id == "gate-1"

    snapshots = engine.collect_price_data("kraken", "SOLUSD", duration_sec=6, interval_sec=0.5)
    assert len(snapshots) == 11
    assert len({snapshot.receipt_id for snapshot in snapshots}) == 11
    assert all(snapshot.timestamp == snapshot.source_timestamp for snapshot in snapshots)
    assert all(snapshot.actionable is False for snapshot in snapshots)


def test_only_complete_linked_fee_evidence_can_produce_an_action() -> None:
    client = _ReceiptClient()

    def fee_receipt(platform: str, symbol: str) -> dict:
        return {
            "source_id": f"{platform}:private:fees",
            "symbol": symbol,
            "source_timestamp": NOW - 0.4,
            "received_at": NOW - 0.3,
            "receipt_id": "fee-1",
            "truth_status": "real_observed",
            "generated_values": False,
            "eligible_for_action": True,
            "round_trip_fee_pct": 0.1,
            "input_receipt_ids": tuple(client.receipt_ids),
        }

    engine = legacy.UniversalForecastEngine(
        clients={"kraken": client},
        gate_receipt_supplier=_gate_receipt,
        fee_receipt_supplier=fee_receipt,
        clock=lambda: NOW,
        sleeper=lambda _: None,
    )
    forecast = engine.generate_forecast("kraken", "SOLUSD", collect_duration=6)

    assert forecast.should_trade is True
    assert forecast.action == "BUY"
    assert forecast.actionable is True
    assert forecast.truth_status == "real_derived"
    assert "gate-1" in forecast.input_receipt_ids
    assert "fee-1" in forecast.input_receipt_ids
    assert forecast.accounting_eligible is False
    assert forecast.learning_eligible is False
