import time

import pytest

from aureon.command_centers import war_strategy as war


def _strategy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return war.WarStrategy()


def test_estimate_refuses_missing_observations(tmp_path, monkeypatch):
    strategy = _strategy(tmp_path, monkeypatch)

    with pytest.raises(ValueError, match='NO_DATA'):
        strategy.estimate_quick_kill('BTCUSDT', 'binance')


def test_estimate_refuses_stale_volatility_receipt(tmp_path, monkeypatch):
    strategy = _strategy(tmp_path, monkeypatch)
    strategy.volatility_cache['BTCUSDT'] = {
        'avg_bar_move_pct': 0.01,
        'volatility': 0.002,
        'sample_size': 10,
        'updated_at': time.time() - war.VOLATILITY_EVIDENCE_TTL_SECONDS - 1,
        'exchange': 'binance',
    }

    with pytest.raises(ValueError, match='stale'):
        strategy.estimate_quick_kill('BTCUSDT', 'binance')


def test_fresh_observations_return_provenance(tmp_path, monkeypatch):
    strategy = _strategy(tmp_path, monkeypatch)
    monkeypatch.setattr(war, 'get_dynamic_required_r', lambda exchange, size: 0.01)

    estimate = strategy.estimate_quick_kill(
        'BTCUSDT',
        'binance',
        prices=[100.0, 101.0, 100.5, 102.0, 101.5, 103.0],
    )

    assert estimate.truth_status == 'real_derived'
    assert estimate.source_id == 'binance:observed_prices'
    assert estimate.source_timestamp
    assert estimate.generated_values is False
