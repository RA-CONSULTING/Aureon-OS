from __future__ import annotations

import importlib
from dataclasses import fields

import aureon.intelligence.aureon_universal_forecast as forecast_module


NOW = 2_000_000_000.0


def _header(
    receipt_id: str,
    *,
    source_id: str,
    truth_status: str,
) -> dict:
    return {
        "receipt_id": receipt_id,
        "provider_receipt_type": "CompleteProviderReceipt",
        "source_id": source_id,
        "source_timestamp": NOW - 0.5,
        "received_at": NOW - 0.4,
        "data_status": "live",
        "truth_status": truth_status,
        "generated_values": False,
    }


class _QuoteClient:
    def __init__(self, *, venue: str = "kraken") -> None:
        self.venue = venue
        self.calls = 0

    def get_ticker_receipt(self, symbol: str) -> dict:
        self.calls += 1
        source_timestamp = NOW - 20.0 + self.calls * 0.1
        return {
            **_header(
                f"quote-{self.calls}",
                source_id=f"{self.venue}:public:ticker",
                truth_status="real_observed",
            ),
            "source_timestamp": source_timestamp,
            "received_at": source_timestamp + 0.01,
            "venue": self.venue,
            "symbol": symbol,
            "quote_currency": "USD",
            "price": 100.0 + self.calls,
            "bid": 99.5 + self.calls,
            "ask": 100.5 + self.calls,
            "volume": 1000.0 + self.calls,
        }


def _gate(request: dict) -> dict:
    quote_ids = set(request["market_receipt_ids"])
    hnc = {
        **_header(
            "hnc-1",
            source_id="aureon:hnc:canonical",
            truth_status="real_derived",
        ),
        "input_receipt_ids": sorted(quote_ids),
        "eligible_for_action": True,
        "hnc_coherence": "0.91",
        "lambda_value": "0.73",
        "phi_alignment": str(forecast_module.PHI),
    }
    auris = {
        **_header(
            "auris-1",
            source_id="aureon:auris:canonical",
            truth_status="real_derived",
        ),
        "input_receipt_ids": sorted(quote_ids | {"hnc-1"}),
        "eligible_for_action": True,
        "auris_coherence": "0.89",
        "auris_resonance": "0.82",
    }
    return {
        **_header(
            "gate-1",
            source_id="aureon:hnc_auris:gate",
            truth_status="real_derived",
        ),
        "venue": request["venue"],
        "symbol": request["symbol"],
        "input_receipt_ids": sorted(
            quote_ids | {"hnc-1", "auris-1"}
        ),
        "hnc_receipt": hnc,
        "auris_receipt": auris,
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


def _fee(request: dict) -> dict:
    return {
        **_header(
            "fee-1",
            source_id="kraken:private:fee-schedule",
            truth_status="real_observed",
        ),
        "venue": request["venue"],
        "symbol": request["symbol"],
        "fee_currency": request["quote_currency"],
        "fee_schedule_complete": True,
        "round_trip_fee_pct": "0.52",
        "input_receipt_ids": list(request["input_receipt_ids"]),
        "eligible_for_action": True,
    }


def _numeric_values(instance) -> list:
    return [
        getattr(instance, item.name)
        for item in fields(instance)
        if type(getattr(instance, item.name)) in {int, float}
    ]


def test_import_constructor_and_falsey_paths_are_inert_and_numeric_free(
    monkeypatch,
    capsys,
) -> None:
    marker = "leave-unchanged"
    monkeypatch.setenv("LIVE", marker)
    module = importlib.reload(forecast_module)
    engine = module.UniversalForecastEngine()

    assert module.__dict__.get("main") is None
    assert module.__dict__.get("argparse") is None
    assert module.__dict__.get("json") is None
    assert module.__dict__.get("os") is None
    assert engine.clients == {}
    assert engine.earth_engine is None
    assert engine.price_history == {}
    assert capsys.readouterr().out == ""
    assert module.PriceSnapshot.__dataclass_fields__["bid"].default is None
    assert module.ProbabilityForecast(
        symbol="XBTUSD", platform="kraken", asset_class="crypto"
    ).recommended_action == "NO_DATA"

    gates = engine.check_cosmic_gates()
    assert gates.evidence_complete is False
    assert gates.actionable is False
    assert _numeric_values(gates) == []
    not_started = engine.generate_forecast("kraken", "XBTUSD")
    assert not_started.reason == "explicit_collection_duration_required"
    assert not_started.action == "NO_DATA"
    assert _numeric_values(not_started) == []


def test_market_receipts_are_same_venue_and_history_waits_for_all_gates() -> None:
    foreign = _QuoteClient(venue="binance")
    foreign_engine = forecast_module.UniversalForecastEngine(
        clients={"kraken": foreign},
        clock=lambda: NOW,
        sleeper=lambda _: None,
    )
    assert foreign_engine.get_price_receipt("kraken", "XBTUSD") is None

    client = _QuoteClient()
    engine = forecast_module.UniversalForecastEngine(
        clients={"kraken": client},
        gate_receipt_supplier=_gate,
        clock=lambda: NOW,
        sleeper=lambda _: None,
    )
    snapshots = engine.collect_price_data(
        "kraken", "XBTUSD", duration_sec=6, interval_sec=0.5
    )
    assert len(snapshots) == 11
    assert len({snapshot.receipt_id for snapshot in snapshots}) == 11
    assert all(snapshot.timestamp == snapshot.source_timestamp for snapshot in snapshots)
    assert all(snapshot.venue == "kraken" for snapshot in snapshots)
    assert engine.price_history == {}

    gates = engine.check_cosmic_gates("kraken", "XBTUSD", snapshots)
    assert gates.evidence_complete is True
    assert gates.combined_multiplier == 1.2 * 1.1 * 1.5
    assert gates.hnc_receipt_id == "hnc-1"
    assert gates.auris_receipt_id == "auris-1"
    assert gates.actionable is False

    no_fee = engine.generate_probability_forecast(
        "kraken", "XBTUSD", snapshots, gates
    )
    assert no_fee.data_status == "no_data"
    assert no_fee.recommended_action == "NO_DATA"
    assert no_fee.actionable is False
    assert no_fee.accounting_eligible is False
    assert no_fee.learning_eligible is False
    assert _numeric_values(no_fee) == []
    assert engine.price_history == {}


def test_full_linked_receipts_enable_forecast_then_history_not_accounting() -> None:
    client = _QuoteClient()
    engine = forecast_module.UniversalForecastEngine(
        clients={"kraken": client},
        gate_receipt_supplier=_gate,
        fee_receipt_supplier=_fee,
        clock=lambda: NOW,
        sleeper=lambda _: None,
    )

    result = engine.generate_forecast(
        "kraken", "XBTUSD", collect_duration=6
    )
    assert result.data_status == "live"
    assert result.truth_status == "real_derived"
    assert result.probability is not None
    assert result.probability.data_status == "live"
    assert result.probability.truth_status == "real_derived"
    assert result.probability.recommended_action in {"BUY", "SELL", "HOLD"}
    assert result.accounting_eligible is False
    assert result.learning_eligible is False
    assert result.probability.accounting_eligible is False
    assert result.probability.learning_eligible is False
    assert {"gate-1", "hnc-1", "auris-1", "fee-1"}.issubset(
        set(result.input_receipt_ids)
    )
    assert len(engine.price_history["kraken:XBTUSD"]) == 11
