"""Offline receipt and freshness contract for the HNC live producer."""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from aureon.core.aureon_lambda_engine import LambdaEngine, SubsystemReading
from aureon.core.hnc_live_daemon import (
    HNCLiveDaemon,
    SourceObservation,
    SourceReceipt,
    SourceState,
    _complete_source_observation,
    _map_coingecko,
    _map_harmonic_observer,
    _map_schumann,
    _map_space_weather,
    _map_volatility_sentinel,
    _provider_input_receipt_id,
    _wrap_schumann_observation,
    _wrap_space_weather_observation,
    _wrap_world_data_observation,
)

NOW = 1_786_400_000.0


def _reading(name: str = "x", value: float = 0.6) -> SubsystemReading:
    return SubsystemReading(name=name, value=value, confidence=0.8, state="test")


def _receipt(
    receipt_id: str = "provider:x:1",
    *,
    source_timestamp: float = NOW - 2.0,
    received_at: float = NOW - 1.0,
    truth_status: str = "real_observed",
    generated_values: bool = False,
    input_receipt_ids: tuple[str, ...] = (),
) -> SourceReceipt:
    return SourceReceipt(
        source_id="provider.test",
        source_timestamp=source_timestamp,
        received_at=received_at,
        receipt_id=receipt_id,
        receipt_type="provider_measurement",
        truth_status=truth_status,
        generated_values=generated_values,
        input_receipt_ids=input_receipt_ids,
    )


def _accepted_state(
    name: str = "x",
    *,
    source_timestamp: float = NOW - 2.0,
    max_age_s: float = 120.0,
) -> SourceState:
    st = SourceState(name=name, interval_s=5, max_age_s=max_age_s)
    st.last_reading = _reading(name)
    st.last_receipt = _receipt(
        f"provider:{name}:1", source_timestamp=source_timestamp
    )
    st.last_fetch_ts = st.last_receipt.received_at
    return st


def _memory_receipt(tmp_path, observations: list[SourceObservation]):
    engine = LambdaEngine(state_path=tmp_path / "lambda_history.json")
    receipt_ids = [item.receipt.receipt_id for item in observations]
    state = engine.step(
        [item.reading for item in observations],
        source_receipt_ids=receipt_ids,
        auto_persist=False,
    )
    receipt = engine.save_history(source_receipt_ids=receipt_ids)
    assert receipt is not None
    return state.to_dict(), receipt


def test_fresh_receipt_backed_reading_is_served() -> None:
    st = _accepted_state()
    assert st.reading_for_compute(NOW) is st.last_reading


def test_expiry_uses_provider_source_time_not_local_fetch_time() -> None:
    st = _accepted_state(source_timestamp=NOW - 121.0)
    st.last_fetch_ts = NOW
    assert st.reading_for_compute(NOW) is None


def test_reading_without_receipt_never_enters_lambda() -> None:
    st = SourceState(name="x", interval_s=5)
    st.last_reading = _reading()
    st.last_fetch_ts = NOW
    assert st.reading_for_compute(NOW) is None


def test_source_state_default_is_bounded() -> None:
    assert SourceState(name="schumann", interval_s=600).max_age_s == 300.0


def _bare_daemon() -> HNCLiveDaemon:
    daemon = object.__new__(HNCLiveDaemon)
    daemon._sources = {}
    daemon._fetchers = {}
    return daemon


def test_register_source_derives_a_bounded_default() -> None:
    daemon = _bare_daemon()

    async def fetch():
        return None

    daemon.register_source("custom", 30, fetch)
    assert daemon._sources["custom"].max_age_s == pytest.approx(90.0)
    assert daemon._sources["custom"].interval_s == 30


def test_register_source_stores_explicit_max_age() -> None:
    daemon = _bare_daemon()

    async def fetch():
        return None

    daemon.register_source("volatility_sentinel", 5, fetch, max_age_s=120.0)
    assert daemon._sources["volatility_sentinel"].max_age_s == pytest.approx(120.0)


def test_complete_source_observation_requires_fresh_real_receipt() -> None:
    candidate = SourceObservation(_reading(), _receipt())
    accepted = _complete_source_observation(
        "x", candidate, now=NOW, max_age_s=120.0
    )
    assert accepted is not None
    assert accepted.receipt.source_timestamp == NOW - 2.0
    assert accepted.receipt.received_at == NOW - 1.0

    assert _complete_source_observation(
        "x",
        replace(candidate, receipt=replace(candidate.receipt, generated_values=True)),
        now=NOW,
        max_age_s=120.0,
    ) is None
    assert _complete_source_observation(
        "x",
        replace(
            candidate,
            receipt=replace(candidate.receipt, source_timestamp=NOW - 121.0),
        ),
        now=NOW,
        max_age_s=120.0,
    ) is None
    assert _complete_source_observation(
        "x",
        replace(candidate, receipt=replace(candidate.receipt, receipt_id="")),
        now=NOW,
        max_age_s=120.0,
    ) is None


def test_real_derived_source_requires_upstream_receipt_ids() -> None:
    candidate = SourceObservation(
        _reading(),
        _receipt(truth_status="real_derived"),
    )
    assert _complete_source_observation(
        "x", candidate, now=NOW, max_age_s=120.0
    ) is None
    linked = replace(
        candidate,
        receipt=replace(candidate.receipt, input_receipt_ids=("provider:root:1",)),
    )
    assert _complete_source_observation(
        "x", linked, now=NOW, max_age_s=120.0
    ) is not None


def test_schumann_builtin_preserves_provider_clock_and_named_source() -> None:
    raw = SimpleNamespace(
        amplitude=0.62,
        quality=0.91,
        resonance_phase="stable",
        truth_status="live",
    )
    raw.to_dict = lambda: {
        "timestamp": NOW - 1.0,
        "active_sources": ["Barcelona-EM"],
        "source_timestamp": NOW - 4.0,
        "truth_status": "live",
        "generated_values": False,
    }
    mapped = _map_schumann(raw)
    first = _wrap_schumann_observation(raw, mapped)
    second = _wrap_schumann_observation(raw, mapped)
    assert first is not None
    assert first.receipt.receipt_id == second.receipt.receipt_id
    assert first.receipt.source_timestamp == NOW - 4.0
    assert first.receipt.received_at == NOW - 1.0
    assert len(first.receipt.input_receipt_ids) == 1
    assert _complete_source_observation(
        "schumann", first, now=NOW, max_age_s=120.0
    ) is not None


def test_space_weather_builtin_links_every_timestamped_provider() -> None:
    raw = SimpleNamespace(
        truth_status="live",
        kp_index=2.0,
        kp_category="Quiet",
    )
    payload = {
        "timestamp": NOW - 1.0,
        "active_sources": [
            "NASA-Flares", "NOAA-Forecast", "NOAA-KP", "NOAA-SolarWind",
        ],
        "source_timestamps": {
            "NOAA-Forecast": "Mon, 10 Aug 2026 22:12:21 GMT",
            "NOAA-KP": NOW - 248.0,
            "NOAA-SolarWind": NOW - 368.0,
        },
        "truth_status": "live",
        "generated_values": False,
    }
    raw.to_dict = lambda: dict(payload)
    wrapped = _wrap_space_weather_observation(raw, _map_space_weather(raw))
    assert wrapped is not None
    assert wrapped.receipt.source_timestamp == NOW - 59.0
    assert wrapped.receipt.received_at == NOW - 1.0
    expected_timestamps = {
        "NOAA-Forecast": NOW - 59.0,
        "NOAA-KP": NOW - 248.0,
        "NOAA-SolarWind": NOW - 368.0,
    }
    assert wrapped.receipt.input_receipt_ids == tuple(sorted(
        _provider_input_receipt_id("space_weather", provider, timestamp)
        for provider, timestamp in expected_timestamps.items()
    ))
    assert _complete_source_observation(
        "space_weather", wrapped, now=NOW, max_age_s=300.0
    ) is not None

    payload["source_timestamps"] = {"NOAA-KP": NOW - 3.0}
    assert _wrap_space_weather_observation(raw, _map_space_weather(raw)) is None

    payload["active_sources"] = ["NOAA-KP", "NOAA-SolarWind"]
    payload["source_timestamps"] = {
        "NOAA-KP": NOW - 3.0,
        "NOAA-SolarWind": "Mon, 10 Aug 2026 22:03:18 GMT",
    }
    assert _wrap_space_weather_observation(raw, _map_space_weather(raw)) is None


def test_complete_world_data_item_can_produce_live_hnc_receipt(tmp_path) -> None:
    item = SimpleNamespace(raw={"price": 61_000.0, "change_24h": 2.0})
    item.to_dict = lambda: {
        "source_id": "coingecko",
        "source_timestamp": NOW - 4.0,
        "received_at": NOW - 1.0,
        "receipt_id": "coingecko:bitcoin:provider-1",
        "truth_status": "real_observed",
        "generated_values": False,
        "action_enabled": False,
        "accounting_enabled": False,
        "learning_enabled": False,
    }
    wrapped = _wrap_world_data_observation(
        "coingecko_btc", _map_coingecko(item), item
    )
    assert wrapped is not None
    accepted = _complete_source_observation(
        "coingecko_btc", wrapped, now=NOW, max_age_s=120.0
    )
    assert accepted is not None
    assert accepted.receipt.input_receipt_ids == (
        "coingecko:bitcoin:provider-1",
    )

    daemon = _bare_daemon()
    daemon._sources = {
        "coingecko_btc": SourceState(
            name="coingecko_btc",
            interval_s=300.0,
            last_reading=accepted.reading,
            last_receipt=accepted.receipt,
            max_age_s=900.0,
        )
    }
    state, memory_receipt = _memory_receipt(tmp_path, [accepted])
    envelope = daemon._derived_envelope(
        state,
        [accepted.reading],
        received_at=NOW,
        source_receipts=[accepted.receipt],
        memory_receipt=memory_receipt,
    )
    assert envelope["data_status"] == "live"
    assert envelope["truth_status"] == "real_derived"
    assert envelope["input_receipt_ids"] == sorted([
        accepted.receipt.receipt_id,
        memory_receipt["receipt_id"],
    ])
    assert envelope["action_eligible"] is False
    assert envelope["action_gate_passed"] is False


def test_incomplete_world_data_item_remains_no_data() -> None:
    item = SimpleNamespace(raw={"price": 61_000.0, "change_24h": 2.0})
    item.to_dict = lambda: {
        "source_id": "coingecko",
        "source_timestamp": NOW - 4.0,
        "received_at": NOW - 1.0,
        "receipt_id": "",
        "truth_status": "real_observed",
        "generated_values": False,
    }
    assert _wrap_world_data_observation(
        "coingecko_btc", _map_coingecko(item), item
    ) is None


def test_derived_hnc_receipt_binds_timestamps_and_is_non_actionable(tmp_path) -> None:
    daemon = _bare_daemon()
    daemon._sources = {
        "a": _accepted_state("a", source_timestamp=NOW - 4.0),
        "b": _accepted_state("b", source_timestamp=NOW - 2.0),
    }
    readings = [
        daemon._sources["a"].last_reading,
        daemon._sources["b"].last_reading,
    ]
    source_receipts = [
        daemon._sources["a"].last_receipt,
        daemon._sources["b"].last_receipt,
    ]
    observations = [
        SourceObservation(reading=reading, receipt=receipt)
        for reading, receipt in zip(readings, source_receipts, strict=True)
    ]
    state, memory_receipt = _memory_receipt(tmp_path, observations)
    first = daemon._derived_envelope(
        state,
        readings,
        received_at=NOW,
        source_receipts=source_receipts,
        memory_receipt=memory_receipt,
    )
    second = daemon._derived_envelope(
        state,
        readings,
        received_at=NOW,
        source_receipts=source_receipts,
        memory_receipt=memory_receipt,
    )
    later = daemon._derived_envelope(
        state,
        readings,
        received_at=NOW + 1.0,
        source_receipts=source_receipts,
        memory_receipt=memory_receipt,
    )
    assert first["receipt_id"] == second["receipt_id"]
    assert first["receipt_id"] != later["receipt_id"]
    assert first["source_timestamp"] == NOW - 2.0
    assert first["received_at"] == NOW
    assert first["input_receipt_ids"] == sorted([
        "provider:a:1", "provider:b:1", memory_receipt["receipt_id"],
    ])
    for field_name in (
        "operational_eligible", "provider_eligible", "action_eligible",
        "actionable", "accounting_eligible", "learning_eligible",
        "eligible_for_action", "eligible_for_accounting",
        "eligible_for_learning", "action_gate_passed",
    ):
        assert first[field_name] is False


def test_no_data_envelope_and_trace_are_numeric_free(tmp_path) -> None:
    daemon = _bare_daemon()
    daemon._trace_path = tmp_path / "hnc.jsonl"
    envelope = daemon._no_data_envelope(
        NOW, "complete_fresh_real_source_receipt_required"
    )
    for metric in (
        "lambda_t", "coherence_gamma", "consciousness_psi",
        "symbolic_life_score", "source_count",
    ):
        assert metric not in envelope
    assert envelope["truth_status"] == "no_data"
    assert envelope["generated_values"] is False
    assert envelope["source_timestamp"] is None
    daemon._append_trace(envelope, [])
    row = json.loads(daemon._trace_path.read_text(encoding="utf-8"))
    assert row == envelope


def test_map_volatility_sentinel_refuses_riskless_ok_row() -> None:
    assessment = SimpleNamespace(
        status="ok", volatility_risk=None, confidence=0.5, factors=()
    )
    assert _map_volatility_sentinel(assessment) is None


def test_map_harmonic_observer_warming_is_none() -> None:
    observer = SimpleNamespace(
        regime=lambda: "WARMING", coherence_score=lambda: 0.0
    )
    assert _map_harmonic_observer(observer) is None
    assert _map_harmonic_observer(None) is None


def test_map_harmonic_observer_caps_confidence() -> None:
    observer = SimpleNamespace(
        regime=lambda: "QUIET", coherence_score=lambda: 0.83
    )
    reading = _map_harmonic_observer(observer)
    assert reading is not None
    assert reading.name == "harmonic_spectrum"
    assert reading.value == pytest.approx(0.83)
    assert reading.confidence == pytest.approx(0.6)
    assert reading.state == "QUIET"
