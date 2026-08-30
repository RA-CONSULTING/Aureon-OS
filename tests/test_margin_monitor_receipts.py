import importlib.util
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / 'aureon' / 'monitors' / '_margin_monitor.py'


def _monitor_module():
    spec = importlib.util.spec_from_file_location('margin_monitor_receipt_test', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _receipt(now, **values):
    receipt = {
        'source_id': 'kraken',
        'source_timestamp': now - 1,
        'received_at': now - 1,
        'receipt_id': 'provider-receipt-1',
        'truth_status': 'real_observed',
        'generated_values': False,
    }
    receipt.update(values)
    return receipt


def test_receipt_gates_are_inert_by_default_and_reject_unproven_state(capsys):
    monitor = _monitor_module()
    now = 1_700_000_000.0

    assert monitor.main([]) == 0
    assert 'No provider monitoring started' in capsys.readouterr().out

    quote, problem = monitor._complete_quote(_receipt(now, bid=100.0, ask=101.0), now)
    assert problem is None and quote == (100.0, 101.0)
    _, problem = monitor._complete_quote(_receipt(now, bid=0.0, ask=101.0), now)
    assert problem == 'receipt has no complete two-sided quote'
    _, problem = monitor._complete_quote(_receipt(now, bid=100.0, ask=101.0, generated_values=True), now)
    assert problem == 'receipt is not real observed evidence'

    pending, problem = monitor._complete_terminal_fill(
        _receipt(now, status='pending', orderId='o-1', fill_id='f-1', fee_currency='USD',
                 filled_volume=1.0, fill_price=100.0, fee=0.1, realized_pnl=1.0),
        now,
    )
    assert pending is None and problem == 'close receipt is not a terminal fill'

    terminal, problem = monitor._complete_terminal_fill(
        _receipt(now, status='filled', orderId='o-1', fill_id='f-1', fee_currency='USD',
                 filled_volume=1.0, fill_price=100.0, fee=0.1, realized_pnl=1.0),
        now,
    )
    assert problem is None and terminal['fill_id'] == 'f-1'

    source = SOURCE.read_text(encoding='utf-8')
    assert "terminal_fill, fill_problem = _complete_terminal_fill(close_order, receipt_now)" in source
    assert source.index("terminal_fill, fill_problem = _complete_terminal_fill(close_order, receipt_now)") < source.index('closed_positions.append({')
