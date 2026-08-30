from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aureon.autonomous.aureon_full_autonomy import (
    AutonomyExecutor,
    CosmicHarmonicState,
    MarginPosition,
    PositionHealthReport,
    SolarRadarReport,
)


def _executor(state_root: Path) -> AutonomyExecutor:
    executor = AutonomyExecutor.__new__(AutonomyExecutor)
    executor._cosmic_state = None
    executor._radar_state = None
    executor._epas_state = None
    executor._epas_state_root = state_root
    return executor


def _timestamp(*, seconds_ago: float = 0.0) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()


def _cosmic(timestamp: str, score: object = 0.8) -> CosmicHarmonicState:
    return CosmicHarmonicState(
        timestamp=timestamp,
        positions=[],
        aspects=[],
        cosmic_score=0.8,
        schumann_phase=0.25,
        schumann_modulated_score=score,
        dominant_aspect='observed aspect',
        phi_locked=False,
        interpretation='BUY',
        total_aspects=1,
        positive_aspects=1,
        negative_aspects=0,
    )


def _radar(timestamp: str, score: object = 0.6) -> SolarRadarReport:
    return SolarRadarReport(
        scan_timestamp=timestamp,
        scan_horizon_days=7,
        events=[],
        events_1d=[],
        events_3d=[],
        events_7d=[],
        radar_score=score,
        incoming_positive=0,
        incoming_negative=0,
        nearest_event='none observed',
        dominant_incoming='none observed',
        lunar_phase_now='observed phase',
        lunar_phase_next='observed next phase',
        phi_event_incoming=False,
        interpretation='RADAR_NEUTRAL',
    )


def _health(timestamp: str) -> PositionHealthReport:
    position = MarginPosition(
        pos_id='provider-position-id',
        symbol='DOGE/USD',
        side='long',
        vol=100.0,
        entry_price=0.1,
        cost_usd=10.0,
        margin_posted=2.0,
        rollover_pct_per_4h=0.001,
        unrealised_pnl=1.0,
        current_price=0.11,
    )
    return PositionHealthReport(
        timestamp=timestamp,
        equity=30.0,
        trade_balance=30.0,
        margin_used=2.0,
        free_margin=28.0,
        margin_level_pct=1500.0,
        unrealised_pnl=1.0,
        rollover_per_day=2.0,
        rollover_days_remaining=7.0,
        rollover_total_cost=14.0,
        equity_buffer=28.0,
        liq_price_today=0.03,
        liq_price_at_target=0.04,
        doge_price_now=0.11,
        pct_drop_to_liq_today=-9.0,
        pct_drop_to_liq_at_target=-8.0,
        target_date_str='provider target',
        predicted_pct_gain=0.0,
        predicted_price=0.11,
        gross_pnl_at_target=0.0,
        net_pnl_at_target=-14.0,
        can_survive=True,
        action='HOLD',
        positions=[position],
    )


def _write_entry_premise(state_root: Path, score: object = 0.7) -> None:
    (state_root / 'intent_feedback_queue.json').write_text(
        json.dumps(
            [
                {
                    'queued_at': _timestamp(seconds_ago=30),
                    'status': 'pending',
                    'neural_input': {'gaia_resonance': score},
                    'epas_receipt': {
                        'truth_status': 'real_derived',
                        'source_id': 'recorded-entry-epas',
                        'source_timestamp': _timestamp(seconds_ago=31),
                        'generated_values': False,
                        'eligible_for_external_action': True,
                    },
                }
            ]
        ),
        encoding='utf-8',
    )


def _run(executor: AutonomyExecutor, health: PositionHealthReport | None):
    return asyncio.run(executor.run_epas_shield(health))


def _assert_fail_closed(state) -> None:
    assert state.truth_status == 'no_data'
    assert state.new_entry_blocked is True
    assert state.eligible_for_external_action is False
    assert state.generated_values is False
    assert state.shield_integrity is None
    assert state.layer1_field_score is None
    assert state.layer2_score is None
    assert state.layer3_score is None
    assert AutonomyExecutor._epas_allows_external_entry(state) is False


def test_epas_missing_evidence_is_no_data_and_blocks_entry(tmp_path: Path) -> None:
    executor = _executor(tmp_path)

    state = _run(executor, None)

    _assert_fail_closed(state)
    assert 'cosmic evidence is unavailable' in state.no_data_reason


def test_direct_trade_entrypoint_cannot_bypass_no_data_epas(tmp_path: Path) -> None:
    executor = _executor(tmp_path)
    _run(executor, None)

    trades = asyncio.run(
        executor.execute_trades(
            {'predictions': [{'symbol': 'BTC', 'signal': 'BUY'}]}
        )
    )

    assert trades['executed'] == []
    assert trades['failed'][0]['error'] == 'EPAS_EXTERNAL_ENTRY_BLOCKED'
    assert trades['failed'][0]['truth_status'] == 'no_data'
    assert trades['failed'][0]['eligible_for_external_action'] is False


def test_epas_stale_evidence_is_no_data_and_blocks_entry(tmp_path: Path) -> None:
    executor = _executor(tmp_path)
    executor._cosmic_state = _cosmic(_timestamp(seconds_ago=601))
    executor._radar_state = _radar(_timestamp())

    state = _run(executor, _health(_timestamp()))

    _assert_fail_closed(state)
    assert 'stale' in state.no_data_reason


def test_epas_malformed_evidence_is_no_data_and_blocks_entry(tmp_path: Path) -> None:
    executor = _executor(tmp_path)
    executor._cosmic_state = _cosmic(_timestamp(), score='not-a-number')
    executor._radar_state = _radar(_timestamp())

    state = _run(executor, _health(_timestamp()))

    _assert_fail_closed(state)
    assert 'cosmic field score must be numeric' in state.no_data_reason


def test_epas_math_exception_is_no_data_and_blocks_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executor = _executor(tmp_path)
    executor._cosmic_state = _cosmic(_timestamp())
    executor._radar_state = _radar(_timestamp())
    (tmp_path / 'active_position.json').write_text(
        json.dumps({'timestamp': _timestamp(seconds_ago=60)}),
        encoding='utf-8',
    )

    def _raise_math_failure(**_kwargs):
        raise RuntimeError('VSOP87 provider/math unavailable')

    monkeypatch.setattr(executor, '_compute_planet_positions_math', _raise_math_failure)

    state = _run(executor, _health(_timestamp()))

    _assert_fail_closed(state)
    assert 'VSOP87 provider/math unavailable' in state.no_data_reason


def test_epas_rejects_unreceipted_entry_premise(tmp_path: Path) -> None:
    executor = _executor(tmp_path)
    executor._cosmic_state = _cosmic(_timestamp())
    executor._radar_state = _radar(_timestamp())
    (tmp_path / 'intent_feedback_queue.json').write_text(
        json.dumps(
            [
                {
                    'queued_at': _timestamp(seconds_ago=30),
                    'status': 'pending',
                    'neural_input': {'gaia_resonance': 0.7},
                }
            ]
        ),
        encoding='utf-8',
    )

    state = _run(executor, _health(_timestamp()))

    _assert_fail_closed(state)
    assert 'entry premise EPAS receipt is missing' in state.no_data_reason


def test_epas_complete_evidence_preserves_weighted_equations(tmp_path: Path) -> None:
    executor = _executor(tmp_path)
    executor._cosmic_state = _cosmic(_timestamp(), score=0.8)
    executor._radar_state = _radar(_timestamp(), score=0.6)
    _write_entry_premise(tmp_path, score=0.7)

    state = _run(executor, _health(_timestamp()))

    assert state.truth_status == 'real_derived'
    assert state.generated_values is False
    assert state.layer1_field_score == pytest.approx(0.69)
    assert state.layer2_score == pytest.approx(0.86)
    assert state.layer3_score == pytest.approx(0.6)
    assert state.shield_integrity == pytest.approx(0.757)
    assert state.new_entry_blocked is False
    assert state.eligible_for_external_action is True
    assert state.source_timestamp is not None
    assert 'intent_feedback_queue' in state.source_id
    assert AutonomyExecutor._epas_allows_external_entry(state) is True


def test_intent_snapshot_persists_validated_epas_receipt(tmp_path: Path) -> None:
    executor = _executor(tmp_path)
    executor._cosmic_state = _cosmic(_timestamp(), score=0.8)
    executor._radar_state = _radar(_timestamp(), score=0.6)
    _write_entry_premise(tmp_path, score=0.7)
    state = _run(executor, _health(_timestamp()))

    executor._enqueue_intent_snapshot(
        symbol='DOGE/USD',
        entry_price=0.11,
        target_price=0.12,
        stop_price=0.10,
        net_pnl_at_target=1.0,
        neural_input={'gaia_resonance': state.layer3_now_cosmic},
    )

    queue = json.loads(
        (tmp_path / 'intent_feedback_queue.json').read_text(encoding='utf-8')
    )
    receipt = queue[-1]['epas_receipt']
    assert receipt['truth_status'] == 'real_derived'
    assert receipt['generated_values'] is False
    assert receipt['eligible_for_external_action'] is True
    assert receipt['source_timestamp'] == state.source_timestamp
