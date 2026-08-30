"""Offline provenance contract for the HNC-linked Dr Auris producer."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("aureon.intelligence.dr_auris_throne")

from aureon.intelligence.dr_auris_throne import (  # noqa: E402
    CosmicState,
    DrAurisThrone,
    _space_weather_evidence_receipt,
)
from aureon.harmonic.earth_resonance_engine import EarthResonanceEngine  # noqa: E402


NOW = 1_786_400_000.0


def _base_receipt(
    source: str,
    receipt_id: str,
    *,
    source_timestamp: float = NOW - 2.0,
    received_at: float = NOW - 1.0,
    truth_status: str = "real_observed",
    input_receipt_ids: list[str] | None = None,
    **fields,
) -> dict:
    return {
        "data_status": "live",
        "source_id": source,
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "receipt_id": receipt_id,
        "receipt_type": "provider_measurement",
        "truth_status": truth_status,
        "generated_values": False,
        "input_receipt_ids": list(input_receipt_ids or []),
        "operational_eligible": False,
        "provider_eligible": False,
        "action_eligible": False,
        "actionable": False,
        "accounting_eligible": False,
        "learning_eligible": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "action_gate_passed": False,
        **fields,
    }


def _hnc_receipt(**overrides) -> dict:
    receipt = _base_receipt(
        "aureon:hnc:live_daemon",
        "hnc-1",
        truth_status="real_derived",
        input_receipt_ids=["provider-hnc-input-1"],
        symbolic_life_score=0.72,
        coherence_gamma=0.81,
        consciousness_psi=0.63,
        consciousness_level="CONNECTED",
        lambda_t=0.31,
        receipt_type="hnc_live_field",
        operational_eligible=False,
        provider_eligible=False,
        action_eligible=False,
        accounting_eligible=False,
        learning_eligible=False,
        eligible_for_action=False,
        eligible_for_accounting=False,
        eligible_for_learning=False,
    )
    receipt.update(overrides)
    return receipt


def _earth_schumann_receipt(**overrides) -> dict:
    receipt = _base_receipt(
        "aureon:planetary:schumann",
        "schumann-earth-1",
        truth_status="real_derived",
        input_receipt_ids=["schumann-provider-1"],
        fundamental_hz=7.83,
        coherence=0.86,
        amplitude=0.61,
        earth_disturbance_level=0.18,
        receipt_type="planetary_schumann_evidence",
    )
    receipt.update(overrides)
    return receipt


def _planetary_receipts(*, gate_open: bool = True) -> dict[str, dict]:
    return {
        "space_weather": _base_receipt(
            "provider.noaa.space_weather",
            "space-weather-1",
            kp_index=2.0,
            kp_category="Quiet",
            solar_wind_speed=410.0,
            bz_component=-1.5,
            solar_flares_24h=0,
            geomagnetic_storm_3day="quiet",
            cosmic_score=0.74,
        ),
        "earth_blessing": _base_receipt(
            "provider.schumann.blessing",
            "earth-blessing-1",
            truth_status="real_derived",
            input_receipt_ids=["schumann-1"],
            earth_blessing=0.82,
        ),
        "schumann": _base_receipt(
            "provider.schumann.measurement",
            "schumann-1",
            fundamental_hz=7.83,
            coherence=0.86,
            amplitude=0.61,
            earth_disturbance_level=0.18,
        ),
        "earth_gate": _base_receipt(
            "aureon:planetary:earth_gate",
            "earth-gate-1",
            truth_status="real_derived",
            input_receipt_ids=["schumann-1"],
            gate_open=gate_open,
            reason="validated planetary coherence",
        ),
    }


class _Lambda:
    def __init__(self):
        self.steps = []

    def step(self, readings, volatility=0.0):
        self.steps.append((readings, volatility))
        return type("_S", (), {
            "lambda_t": 1.23,
            "consciousness_psi": 0.4,
            "coherence_gamma": 0.9,
            "consciousness_level": "AWARE",
            "symbolic_life_score": 0.5,
        })()


def _throne(
    *,
    hnc: dict | None = None,
    planetary: dict[str, dict] | None = None,
    lambda_engine=None,
) -> DrAurisThrone:
    receipts = planetary or {}
    throne = DrAurisThrone.__new__(DrAurisThrone)
    throne._clock = lambda: NOW
    throne._receipt_max_age_s = 300.0
    throne._hnc_receipt_fn = lambda: hnc
    throne._space_weather_fn = (
        (lambda: receipts["space_weather"])
        if "space_weather" in receipts else None
    )
    throne._schumann_fn = (
        (lambda: receipts["earth_blessing"])
        if "earth_blessing" in receipts else None
    )
    throne._schumann_reading_fn = (
        (lambda: receipts["schumann"])
        if "schumann" in receipts else None
    )
    throne._earth_gate_fn = (
        (lambda: receipts["earth_gate"])
        if "earth_gate" in receipts else None
    )
    throne._lambda_engine = lambda_engine
    throne._thought_bus = None
    throne._cycle_count = 1
    throne._state = CosmicState()
    return throne


def test_empty_or_partial_chain_is_numeric_free_no_data() -> None:
    state = _throne(
        hnc=_hnc_receipt(),
        planetary={"space_weather": _planetary_receipts()["space_weather"]},
        lambda_engine=_Lambda(),
    )._analyze_cosmos()
    assert state.data_available is False
    assert state.data_status == "no_data"
    assert state.truth_status == "no_data"
    assert state.gate_open is False
    assert state.advisory == "SLEEP"
    assert "schumann" in state.sources_unavailable

    payload = _throne()._evidence_payload(state)
    for metric in (
        "kp_index", "solar_wind_speed", "schumann_hz", "earth_blessing",
        "lambda_t", "coherence_gamma", "cosmic_score",
    ):
        assert metric not in payload


def test_live_evidence_preserves_exact_receipt_causal_metrics() -> None:
    throne = _throne(
        hnc=_hnc_receipt(),
        planetary=_planetary_receipts(),
        lambda_engine=_Lambda(),
    )
    state = throne._analyze_cosmos()
    payload = throne._evidence_payload(state)

    assert payload["lambda_t"] == state.lambda_t
    assert payload["consciousness_psi"] == state.consciousness_psi
    assert payload["coherence_gamma"] == state.coherence_gamma
    assert payload["cosmic_score"] == state.cosmic_score


def test_naked_default_shaped_sources_are_rejected() -> None:
    throne = _throne(hnc=_hnc_receipt(), lambda_engine=_Lambda())
    throne._space_weather_fn = lambda: {"kp_index": 0, "cosmic_score": 0.5}
    throne._schumann_fn = lambda: (0.82, "coherent")
    throne._schumann_reading_fn = lambda: {"fundamental_hz": 7.83}
    throne._earth_gate_fn = lambda: {"gate_open": True}
    state = throne._analyze_cosmos()
    assert state.data_available is False
    assert state.gate_open is False
    assert set(("space_weather", "earth_blessing", "schumann", "earth_gate")).issubset(
        state.sources_unavailable
    )


@pytest.mark.parametrize(
    "hnc_update",
    [
        {"source_timestamp": NOW - 301.0},
        {"generated_values": True},
        {"receipt_id": ""},
        {"eligible_for_action": True},
        {"input_receipt_ids": []},
    ],
)
def test_incomplete_stale_or_actionable_hnc_is_rejected(hnc_update) -> None:
    state = _throne(
        hnc=_hnc_receipt(**hnc_update),
        planetary=_planetary_receipts(),
        lambda_engine=_Lambda(),
    )._analyze_cosmos()
    assert state.data_available is False
    assert state.gate_open is False
    assert "hnc" in state.sources_unavailable


def test_complete_chain_runs_lambda_and_links_exact_receipts() -> None:
    engine = _Lambda()
    state = _throne(
        hnc=_hnc_receipt(),
        planetary=_planetary_receipts(),
        lambda_engine=engine,
    )._analyze_cosmos()
    assert state.data_available is True
    assert state.data_status == "live"
    assert state.truth_status == "real_derived"
    assert state.generated_values is False
    assert len(engine.steps) == 1
    readings, volatility = engine.steps[0]
    assert [reading.name for reading in readings] == [
        "space_weather", "schumann", "earth_disturbance",
        "hnc_canonical_field",
    ]
    assert readings[-1].value == pytest.approx(0.72)
    assert volatility == pytest.approx(0.018)
    assert state.hnc_receipt_id == "hnc-1"
    assert state.planetary_receipt_ids == [
        "earth-blessing-1", "earth-gate-1", "schumann-1", "space-weather-1",
    ]
    assert state.input_receipt_ids == [
        "earth-blessing-1", "earth-gate-1", "hnc-1",
        "provider-hnc-input-1", "schumann-1", "space-weather-1",
    ]
    assert state.source_timestamp == NOW - 2.0
    assert state.received_at == NOW
    for field_name in (
        "operational_eligible", "provider_eligible", "action_eligible",
        "actionable", "accounting_eligible", "learning_eligible",
        "eligible_for_action", "eligible_for_accounting",
        "eligible_for_learning",
    ):
        assert getattr(state, field_name) is False


def test_earth_receipt_rejections_leave_state_unchanged() -> None:
    engine = EarthResonanceEngine(
        coherence_threshold=0.55,
        phase_lock_threshold=0.65,
    )
    initial_state = engine.schumann_state
    initial_update = engine.last_update
    incomplete = _earth_schumann_receipt()
    incomplete.pop("amplitude")
    rejected = [
        incomplete,
        _earth_schumann_receipt(source_timestamp=NOW - 301.0),
        _earth_schumann_receipt(generated_values=True),
        _earth_schumann_receipt(input_receipt_ids=[]),
    ]

    for receipt in rejected:
        assert engine.update_from_schumann_receipt(
            receipt,
            received_at=NOW,
            max_age_s=300.0,
        ) is None
        assert engine.schumann_state is initial_state
        assert engine.last_update == initial_update
        assert engine._schumann_state_initialized is False
        assert engine._accepted_schumann_receipt_id is None


def test_complete_linked_schumann_receipt_initializes_threshold_gate() -> None:
    engine = EarthResonanceEngine(
        coherence_threshold=0.55,
        phase_lock_threshold=0.65,
    )
    receipt = _earth_schumann_receipt()

    state = engine.update_from_schumann_receipt(
        receipt,
        received_at=NOW,
        max_age_s=300.0,
    )

    assert state is not None
    assert state.mode1_power == 0.61
    assert state.mode2_power == 0.86
    assert state.mode3_power == pytest.approx(0.82)
    assert state.field_coherence == 0.86
    assert state.phase_lock == pytest.approx(0.82)
    assert state.resonance_stability == pytest.approx(0.82)
    assert state.timestamp == NOW - 2.0
    assert engine._schumann_state_initialized is True
    assert engine._accepted_schumann_receipt_id == receipt["receipt_id"]
    gate = engine.get_trading_gate_receipt(
        receipt,
        received_at=NOW,
        max_age_s=300.0,
    )
    assert gate is not None
    assert gate["gate_open"] is True
    assert gate["engine_state_initialized"] is True
    assert gate["input_receipt_ids"] == [receipt["receipt_id"]]


def test_complete_linked_schumann_receipt_closes_below_threshold() -> None:
    engine = EarthResonanceEngine(
        coherence_threshold=0.55,
        phase_lock_threshold=0.65,
    )
    receipt = _earth_schumann_receipt(
        receipt_id="schumann-earth-low-coherence",
        coherence=0.54,
    )

    assert engine.update_from_schumann_receipt(
        receipt,
        received_at=NOW,
        max_age_s=300.0,
    ) is not None
    gate = engine.get_trading_gate_receipt(
        receipt,
        received_at=NOW,
        max_age_s=300.0,
    )

    assert gate is not None
    assert gate["gate_open"] is False
    assert "Field coherence" in gate["reason"]
    assert gate["input_receipt_ids"] == [receipt["receipt_id"]]


def test_default_raw_bridges_build_one_linked_live_evidence_cycle() -> None:
    space_payload = {
        "timestamp": NOW - 1.0,
        "kp_index": 2.0,
        "kp_category": "Quiet",
        "solar_wind_speed": 410.0,
        "solar_wind_density": 4.2,
        "bz_component": -1.5,
        "solar_flares_24h": 0,
        "geomagnetic_storm_3day": "quiet",
        "active_sources": ["NOAA-KP", "NOAA-SolarWind"],
        "source_timestamps": {
            "NOAA-KP": NOW - 3.0,
            "NOAA-SolarWind": NOW - 4.0,
        },
        "truth_status": "live",
        "generated_values": False,
    }
    schumann_payload = {
        "timestamp": NOW - 1.0,
        "fundamental_hz": 7.83,
        "harmonics": {"mode2": 14.3},
        "amplitude": 0.61,
        "quality": 0.86,
        "coherence_boost": 0.2,
        "resonance_phase": "stable",
        "active_sources": ["Barcelona-EM"],
        "earth_disturbance_level": 0.18,
        "truth_status": "live",
        "source_timestamp": NOW - 2.0,
        "generated_values": False,
    }

    class _SpaceBridge:
        def __init__(self):
            self.calls = 0

        def get_live_data(self):
            self.calls += 1
            return SimpleNamespace(
                to_dict=lambda: dict(space_payload)
            )

        def get_cosmic_score(self, reading):
            assert reading is not None
            return 0.74

    class _SchumannBridge:
        def __init__(self):
            self.calls = 0

        def get_live_data(self):
            self.calls += 1
            return SimpleNamespace(
                to_dict=lambda: dict(schumann_payload)
            )

        def get_earth_blessing(self, reading):
            assert reading is not None
            return 0.82, "validated coherent field"

    earth = EarthResonanceEngine(
        coherence_threshold=0.55,
        phase_lock_threshold=0.65,
    )
    space_bridge = _SpaceBridge()
    schumann_bridge = _SchumannBridge()
    throne = _throne(hnc=_hnc_receipt(), lambda_engine=_Lambda())
    throne._space_weather_bridge = space_bridge
    throne._schumann_bridge = schumann_bridge
    throne._earth_engine = earth
    throne._planetary_receipt_bundle_fn = throne._build_default_planetary_receipts

    state = throne._analyze_cosmos()
    assert space_bridge.calls == 1
    assert schumann_bridge.calls == 1
    assert state.data_available is True
    assert state.gate_open is True
    assert state.advisory == "TRADE"
    schumann_id = state.source_receipts["schumann"]["receipt_id"]
    assert earth._accepted_schumann_receipt_id == schumann_id
    assert earth.schumann_state.mode1_power == 0.61
    assert earth.schumann_state.mode2_power == 0.86
    assert earth.schumann_state.mode3_power == pytest.approx(0.82)
    assert state.source_receipts["earth_blessing"]["input_receipt_ids"] == [
        schumann_id
    ]
    assert state.source_receipts["earth_gate"]["input_receipt_ids"] == [
        schumann_id
    ]
    assert (
        state.source_receipts["earth_gate"]["receipt_type"]
        == "earth_resonance_gate_evidence"
    )
    for receipt in state.source_receipts.values():
        for field_name in (
            "operational_eligible", "provider_eligible", "action_eligible",
            "actionable", "accounting_eligible", "learning_eligible",
            "eligible_for_action", "eligible_for_accounting",
            "eligible_for_learning", "action_gate_passed",
        ):
            assert receipt[field_name] is False


def test_complete_noaa_receipt_keeps_optional_nasa_flare_as_no_data() -> None:
    raw_space_weather = SimpleNamespace(to_dict=lambda: {
        "timestamp": NOW - 1.0,
        "kp_index": 2.0,
        "kp_category": "Quiet",
        "solar_wind_speed": 410.0,
        "solar_wind_density": 4.2,
        "bz_component": -1.5,
        "solar_flares_24h": None,
        "geomagnetic_storm_3day": "quiet",
        "active_sources": ["NOAA-KP", "NOAA-SolarWind"],
        "source_timestamps": {
            "NOAA-KP": NOW - 3.0,
            "NOAA-SolarWind": NOW - 4.0,
        },
        "truth_status": "live",
        "generated_values": False,
    })
    space_receipt = _space_weather_evidence_receipt(
        raw_space_weather,
        0.74,
        now=NOW,
        max_age_s=300.0,
    )

    assert space_receipt is not None
    assert space_receipt["solar_flares_24h"] is None
    assert space_receipt["solar_flares_24h_available"] is False
    planetary = _planetary_receipts()
    planetary["space_weather"] = space_receipt
    throne = _throne(
        hnc=_hnc_receipt(),
        planetary=planetary,
        lambda_engine=_Lambda(),
    )
    state = throne._analyze_cosmos()
    evidence = throne._evidence_payload(state)

    assert state.data_available is True
    assert state.data_status == "live"
    assert state.solar_flares_24h is None
    assert evidence["solar_flares_24h"] is None
    assert evidence["solar_flares_24h_available"] is False
    for field_name in (
        "operational_eligible", "provider_eligible", "action_eligible",
        "actionable", "accounting_eligible", "learning_eligible",
        "eligible_for_action", "eligible_for_accounting",
        "eligible_for_learning",
    ):
        assert getattr(state, field_name) is False


def test_http_date_parses_without_weakening_provider_freshness_gate() -> None:
    payload = {
        "timestamp": NOW - 1.0,
        "kp_index": 2.0,
        "kp_category": "Quiet",
        "solar_wind_speed": 410.0,
        "solar_wind_density": 4.2,
        "bz_component": -1.5,
        "solar_flares_24h": None,
        "geomagnetic_storm_3day": "quiet",
        "active_sources": [
            "NASA-Flares", "NOAA-Forecast", "NOAA-KP", "NOAA-SolarWind",
        ],
        "source_timestamps": {
            "NOAA-Forecast": "Mon, 10 Aug 2026 22:13:18 GMT",
            "NOAA-KP": NOW - 3.0,
            "NOAA-SolarWind": NOW - 4.0,
        },
        "truth_status": "live",
        "generated_values": False,
    }
    reading = SimpleNamespace(to_dict=lambda: dict(payload))

    fresh = _space_weather_evidence_receipt(
        reading,
        0.74,
        now=NOW,
        max_age_s=300.0,
    )
    assert fresh is not None
    assert dict(fresh["provider_source_timestamps"])["NOAA-Forecast"] == NOW - 2.0

    payload["source_timestamps"]["NOAA-SolarWind"] = "Mon, 10 Aug 2026 22:07:16 GMT"
    cadence_valid = _space_weather_evidence_receipt(
        reading,
        0.74,
        now=NOW,
        max_age_s=300.0,
    )
    assert cadence_valid is not None
    assert cadence_valid["source_timestamp"] == NOW - 2.0
    assert dict(cadence_valid["provider_source_timestamps"])["NOAA-SolarWind"] == NOW - 364.0

    payload["source_timestamps"]["NOAA-SolarWind"] = "Mon, 10 Aug 2026 22:03:18 GMT"
    assert _space_weather_evidence_receipt(
        reading,
        0.74,
        now=NOW,
        max_age_s=300.0,
    ) is None


def test_auris_receipt_id_is_deterministic_for_same_inputs_and_output() -> None:
    kwargs = {
        "hnc": _hnc_receipt(),
        "planetary": _planetary_receipts(),
    }
    first = _throne(**kwargs, lambda_engine=_Lambda())._analyze_cosmos()
    second = _throne(**kwargs, lambda_engine=_Lambda())._analyze_cosmos()
    assert first.receipt_id == second.receipt_id


def test_valid_closed_planetary_gate_stays_live_but_never_opens() -> None:
    state = _throne(
        hnc=_hnc_receipt(),
        planetary=_planetary_receipts(gate_open=False),
        lambda_engine=_Lambda(),
    )._analyze_cosmos()
    assert state.data_available is True
    assert state.gate_open is False
    assert state.advisory == "PROTECT"


def test_published_cosmic_state_carries_receipts_and_false_eligibility(
    monkeypatch,
) -> None:
    published = []

    class _Bus:
        def publish(self, thought):
            published.append(thought)

    import aureon.core.bus_trace as bus_trace

    monkeypatch.setattr(bus_trace, "append_trace", lambda *args, **kwargs: None)
    throne = _throne(
        hnc=_hnc_receipt(),
        planetary=_planetary_receipts(),
        lambda_engine=_Lambda(),
    )
    throne._thought_bus = _Bus()
    state = throne._analyze_cosmos()
    throne._publish_state(state)
    payload = [
        thought.payload for thought in published
        if thought.topic == "auris.throne.cosmic_state"
    ][-1]
    assert payload["receipt_id"] == state.receipt_id
    assert payload["hnc_receipt_id"] == "hnc-1"
    assert payload["input_receipt_ids"] == state.input_receipt_ids
    assert payload["source_timestamp"] == NOW - 2.0
    assert payload["received_at"] == NOW
    assert payload["generated_values"] is False
    assert payload["action_gate_passed"] is False
    for field_name in (
        "operational_eligible", "provider_eligible", "action_eligible",
        "actionable", "accounting_eligible", "learning_eligible",
        "eligible_for_action", "eligible_for_accounting",
        "eligible_for_learning",
    ):
        assert payload[field_name] is False


def test_public_gate_and_score_fail_closed_on_no_data() -> None:
    throne = _throne()
    throne._state = CosmicState()
    assert throne.is_gate_open() is False
    assert throne.get_cosmic_score() is None
    assert throne.get_advisory() == "SLEEP"
