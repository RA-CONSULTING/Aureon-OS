from __future__ import annotations

import json
from datetime import datetime

from aureon.autonomous.aureon_7day_planner import Aureon7DayPlanner


def make_planner() -> Aureon7DayPlanner:
    planner = Aureon7DayPlanner.__new__(Aureon7DayPlanner)
    planner.matrix = {}
    planner.validation_history = []
    planner.adaptive_weights = {
        'hourly_weight': 1.0,
        'daily_weight': 1.0,
        'symbol_weight': 1.0,
        'validation_count': 0,
        'accuracy_7d': None,
        'accuracy_30d': None,
    }
    return planner


def test_missing_matrix_returns_no_data():
    planner = make_planner()

    recommendation = planner.get_current_recommendation('BTC/USD')

    assert recommendation['action'] == 'NO_DATA'
    assert recommendation['confidence'] is None
    assert recommendation['truth_status'] == 'no_data'
    assert recommendation['generated_values'] is False
    assert recommendation['reason'] == 'MISSING_TRAINED_PROBABILITY_MATRIX'


def test_matrix_observations_are_real_derived_without_fake_accuracy():
    planner = make_planner()
    now = datetime.now()
    planner.matrix = {
        'hourly_edge': {str(now.hour): {'edge': 2.0}},
        'daily_edge': {str(now.weekday()): {'edge': 1.0}},
        'symbol_patterns': {
            'BTC/USD': {'hourly_edge': {str(now.hour): {'edge': 1.0}}}
        },
        '_provenance': {
            'source_id': 'observed-matrix.json',
            'source_timestamp': '2026-08-10T12:00:00+00:00',
        },
    }

    recommendation = planner.get_current_recommendation('BTC/USD')

    assert recommendation['action'] != 'NO_DATA'
    assert recommendation['truth_status'] == 'real_derived'
    assert recommendation['model_accuracy'] is None
    assert recommendation['source_id'] == 'observed-matrix.json'
    assert recommendation['generated_values'] is False


def test_empty_validation_history_is_no_data():
    planner = make_planner()

    stats = planner.get_validation_stats()

    assert stats['accuracy'] is None
    assert stats['avg_error_pct'] is None
    assert stats['truth_status'] == 'no_data'


def test_legacy_unvalidated_accuracy_is_removed(tmp_path):
    planner = make_planner()
    planner.base_path = str(tmp_path)
    (tmp_path / '7day_adaptive_weights.json').write_text(
        json.dumps({
            'hourly_weight': 1.0,
            'daily_weight': 1.0,
            'symbol_weight': 1.0,
            'validation_count': 0,
            'accuracy_7d': 0.5,
            'accuracy_30d': 0.5,
        }),
        encoding='utf-8',
    )

    weights = planner._load_adaptive_weights()

    assert weights['accuracy_7d'] is None
    assert weights['accuracy_30d'] is None
