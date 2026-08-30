from collections import deque
from datetime import datetime
from types import SimpleNamespace

import pytest

from aureon.bots_intelligence import aureon_bot_shape_scanner as scanner_module


SYMBOL = "BTCUSDT"


def _scanner():
    scanner = object.__new__(scanner_module.BotShapeScanner)
    scanner.symbols = [SYMBOL]
    scanner.trade_buffers = {SYMBOL: deque(maxlen=100000)}
    scanner.depth_snapshot = {}
    scanner.last_no_data = {}
    scanner.counter_signal_envelopes = []
    scanner.bus = None
    scanner.chirp_bus = None
    scanner.attribution_engine = None
    scanner.counter_intelligence = None
    scanner.firm_catalog = None
    return scanner


def _trade(timestamp, trade_id, price=100.0, quantity=2.0):
    return scanner_module.WSTrade(
        symbol=SYMBOL,
        price=price,
        quantity=quantity,
        timestamp=datetime.fromtimestamp(timestamp),
        trade_id=trade_id,
        is_buyer_maker=False,
        source="binance",
    )


def _depth(timestamp, bid=99.9, ask=100.1):
    return scanner_module.WSOrderBook(
        symbol=SYMBOL,
        bids=[(bid - index * 0.1, 3.0 + index) for index in range(5)],
        asks=[(ask + index * 0.1, 4.0 + index) for index in range(5)],
        timestamp=datetime.fromtimestamp(timestamp),
        first_update_id=700,
        final_update_id=705,
        source="binance",
    )


def _load_live_observations(scanner, now):
    for index in range(20):
        scanner._on_trade(
            _trade(
                now - (19 - index) * 0.05,
                1000 + index,
                price=100.0 + index * 0.01,
                quantity=1.0 + index * 0.02,
            )
        )
    scanner._on_depth(_depth(now))


def _assert_numeric_free_no_data(envelope):
    assert envelope["data_status"] == "no_data"
    assert envelope["truth_status"] == "no_data"
    assert envelope["operational_eligible"] is False
    assert envelope["actionable"] is False
    assert envelope["accounting_eligible"] is False
    assert envelope["learning_eligible"] is False
    assert envelope["generated_values"] is False
    assert not any(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in envelope.values()
    )


def test_fresh_provider_observations_produce_stamped_shape_and_market_data(monkeypatch):
    now = 2_000_000_000.0
    monkeypatch.setattr(scanner_module.time, "time", lambda: now)
    scanner = _scanner()
    _load_live_observations(scanner, now)

    fingerprint = scanner._compute_full_spectrum_fingerprint(SYMBOL)

    assert scanner_module._complete_shape_evidence(fingerprint, now=now)
    assert fingerprint.data_status == "live"
    assert fingerprint.truth_status == "real_derived"
    assert fingerprint.generated_values is False
    assert fingerprint.actionable is False
    assert fingerprint.accounting_eligible is False
    assert fingerprint.learning_eligible is True
    assert len(fingerprint.input_receipt_ids) == 3
    assert sum(fingerprint.volume_profile) == pytest.approx(1.0)
    assert fingerprint.confidence == pytest.approx(
        min(1.0, max(0.0, max(row.activity_score for row in fingerprint.spectrum_results)))
    )

    market_data = scanner._prepare_market_data(SYMBOL)
    assert market_data["data_status"] == "live"
    assert market_data["truth_status"] == "real_derived"
    assert market_data["generated_values"] is False
    assert market_data["input_provider_observation"] is True
    assert market_data["source_id"].startswith("derived:binance.websocket.market:")
    assert market_data["receipt_id"]
    assert market_data["volatility"] >= 0
    assert market_data["volume_ratio"] > 0
    assert market_data["spread_pips"] > 0
    assert market_data["average_latency_ms"] >= 0


def test_stale_or_malformed_provider_inputs_are_numeric_free_no_data(monkeypatch):
    now = 2_000_000_000.0
    monkeypatch.setattr(scanner_module.time, "time", lambda: now)
    scanner = _scanner()

    scanner._on_trade(
        _trade(
            now - scanner_module.PROVIDER_OBSERVATION_MAX_AGE_SECONDS - 1,
            1000,
        )
    )
    assert not scanner.trade_buffers[SYMBOL]
    _assert_numeric_free_no_data(scanner.last_no_data[SYMBOL])

    scanner._on_depth(_depth(now, bid=101.0, ask=100.0))
    assert SYMBOL not in scanner.depth_snapshot
    _assert_numeric_free_no_data(scanner.last_no_data[SYMBOL])


def test_missing_depth_or_unstamped_buffer_cannot_emit_shape(monkeypatch):
    now = 2_000_000_000.0
    monkeypatch.setattr(scanner_module.time, "time", lambda: now)
    scanner = _scanner()
    for index in range(20):
        scanner._on_trade(_trade(now - index * 0.01, 2000 + index))

    assert scanner._compute_full_spectrum_fingerprint(SYMBOL) is None
    _assert_numeric_free_no_data(scanner.last_no_data[SYMBOL])

    scanner.trade_buffers[SYMBOL].clear()
    for index in range(20):
        scanner.trade_buffers[SYMBOL].append(
            {"ts": now - index * 0.01, "px": 100.0, "qty": 1.0}
        )
    scanner._on_depth(_depth(now))
    assert scanner._analyze_band(
        list(scanner.trade_buffers[SYMBOL]),
        scanner_module.SPECTRUM_BANDS[0],
        now,
    ) is None
    assert scanner._compute_full_spectrum_fingerprint(SYMBOL) is None
    _assert_numeric_free_no_data(scanner.last_no_data[SYMBOL])


def test_counter_output_is_stamped_and_never_actionable(monkeypatch):
    now = 2_000_000_000.0
    monkeypatch.setattr(scanner_module.time, "time", lambda: now)
    scanner = _scanner()
    _load_live_observations(scanner, now)
    fingerprint = scanner._compute_full_spectrum_fingerprint(SYMBOL)
    market_data = scanner._prepare_market_data(SYMBOL)
    signal = SimpleNamespace(
        firm_id="firm-7",
        strategy=SimpleNamespace(value="counter"),
        confidence=0.8,
        timing_advantage=12.0,
        expected_profit_pips=3.0,
        risk_score=0.2,
        execution_window_seconds=5.0,
        reasoning="provider-derived test assertion",
    )

    envelope = scanner._emit_counter_signal(
        signal,
        shape=fingerprint,
        market_data=market_data,
        attribution_confidence=0.75,
    )

    assert envelope["data_status"] == "live"
    assert envelope["truth_status"] == "real_derived"
    assert envelope["generated_values"] is False
    assert envelope["actionable"] is False
    assert envelope["accounting_eligible"] is False
    assert envelope["learning_eligible"] is True
    assert envelope["source_id"]
    assert envelope["source_timestamp"] == now
    assert envelope["receipt_id"]
    assert scanner.counter_signal_envelopes == [envelope]


def test_empty_snapshot_is_explicit_numeric_free_no_data(monkeypatch, tmp_path):
    scanner = _scanner()
    monkeypatch.chdir(tmp_path)

    scanner._save_3d_snapshot([])

    payload = scanner_module.json.loads(
        (tmp_path / "bot_shape_snapshot.json").read_text(encoding="utf-8")
    )
    _assert_numeric_free_no_data(
        {key: value for key, value in payload.items() if key not in {"shapes", "rejections"}}
    )
    assert payload["shapes"] == []
