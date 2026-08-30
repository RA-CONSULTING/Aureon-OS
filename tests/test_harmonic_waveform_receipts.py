import time

from aureon.harmonic.aureon_harmonic_waveform import HarmonicWaveformScanner


def _scanner_without_provider_constructors():
    scanner = object.__new__(HarmonicWaveformScanner)
    scanner.node_counter = {'BIN': 0, 'KRK': 0, 'ALP': 0, 'CAP': 0}
    return scanner


def test_harmonic_nodes_require_fresh_complete_provider_receipts(monkeypatch):
    now = time.time()
    monkeypatch.setattr(
        'aureon.harmonic.aureon_harmonic_waveform.time.time', lambda: now
    )
    scanner = _scanner_without_provider_constructors()
    receipt = {
        'source_id': 'binance:/api/v3/ticker/24hr',
        'source_timestamp': now - 1,
        'received_at': now,
        'receipt_id': 'ETHUSDT:1:2',
        'truth_status': 'real_observed',
        'generated_values': False,
    }

    node = scanner._create_harmonic_node('BIN', 'ETHUSDT', 2.0, 100.0, 110.0, receipt=receipt)
    assert node is not None
    assert node.frequency_shift == 10.0
    assert node.current_energy == 220.0
    assert node.source_timestamp == now - 1
    assert node.action_enabled is False
    assert node.accounting_enabled is False
    assert node.learning_enabled is False

    assert scanner._create_harmonic_node('BIN', 'ETHUSDT', 2.0, 100.0, 110.0) is None
    stale = dict(receipt, source_timestamp=now - 301)
    assert scanner._create_harmonic_node('BIN', 'ETHUSDT', 2.0, 100.0, 110.0, receipt=stale) is None
