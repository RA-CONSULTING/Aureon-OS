import time

from aureon.harmonic.aureon_sacred_waveform_visualizer import TerminalSacredVisualizer


def test_visualizer_requires_fresh_real_receipt_before_mutating_history(monkeypatch):
    now = time.time()
    monkeypatch.setattr(
        'aureon.harmonic.aureon_sacred_waveform_visualizer.time.time', lambda: now
    )
    visualizer = TerminalSacredVisualizer(width=20, height=10)
    receipt = {
        'price': 100.0,
        'source_id': 'binance:/api/v3/ticker/24hr',
        'source_timestamp': now - 1,
        'received_at': now,
        'receipt_id': 'BTCUSDT:1:2',
        'truth_status': 'real_observed',
        'generated_values': False,
    }

    rendered = visualizer.update_and_render(receipt)
    assert rendered
    assert len(visualizer.processor.history) == 1
    assert visualizer.processor.history[-1].price == 100.0

    invalid = dict(receipt, generated_values=True)
    assert visualizer.update_and_render(invalid) == ''
    assert len(visualizer.processor.history) == 1

    stale = dict(receipt, source_timestamp=now - 301)
    assert visualizer.update_and_render(stale) == ''
    assert len(visualizer.processor.history) == 1
