import time

from aureon.harmonic.aureon_harmonic_reality import HarmonicRealityAnalyzer


def _receipt(now):
    return {
        'source_id': 'provider.kraken',
        'source_timestamp': now - 2.0,
        'received_at': now - 1.0,
        'receipt_id': 'ticker-001',
        'truth_status': 'real_observed',
        'generated_values': False,
        'price': 101.5,
        'volume': 2500.0,
        'momentum': 0.1,
        'volatility': 0.02,
    }


def test_analyze_requires_fresh_observed_market_receipt_before_field_updates():
    analyzer = HarmonicRealityAnalyzer()
    blocked = analyzer.analyze({'price': 101.5, 'volume': 2500.0})
    assert blocked['status'] == 'no_data'
    assert blocked['truth_status'] == 'no_data'
    assert blocked['generated_values'] is False
    assert blocked['eligible_for_action'] is False
    assert blocked['eligible_for_accounting'] is False
    assert blocked['eligible_for_learning'] is False
    assert 'coherence' not in blocked
    assert len(analyzer.analysis_history) == 0

    accepted = analyzer.analyze(_receipt(time.time()))
    assert accepted['truth_status'] == 'real_derived'
    assert accepted['generated_values'] is False
    assert accepted['source_id'] == 'provider.kraken'
    assert accepted['receipt_id'] == 'ticker-001'
    assert accepted['eligible_for_action'] is False
    assert len(analyzer.analysis_history) == 1
