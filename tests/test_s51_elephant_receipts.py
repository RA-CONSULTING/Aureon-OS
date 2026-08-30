import time

from aureon.s51.aureon_51_live import ElephantMemory


def test_elephant_memory_rejects_local_outcomes_and_dedupes_provider_receipts(tmp_path):
    memory = ElephantMemory(str(tmp_path / 'elephant.json'))

    blocked = memory.record('BTCUSD', 1.0)

    assert blocked['status'] == 'no_data'
    assert memory.symbols == {}
    assert not (tmp_path / 'elephant_history.jsonl').exists()

    now = time.time()
    receipt = {
        'receipt_id': 'receipt-1', 'provider': 'provider', 'source_id': 'provider.closed_trades',
        'source_timestamp': now - 1, 'received_at': now, 'terminal_status': 'closed',
        'trade_id': 'trade-1', 'realized_pnl': 1.5, 'fees': 0.1, 'fee_currency': 'USD',
        'balance_after': 101.4, 'truth_status': 'real_observed', 'generated_values': False,
        'eligible_for_learning': True,
    }

    accepted = memory.record('BTCUSD', receipt)
    duplicate = memory.record('BTCUSD', receipt)

    assert accepted['status'] == 'ok'
    assert duplicate['status'] == 'no_data'
    assert duplicate['blocker'] == 'duplicate_receipt_or_trade'
    assert memory.symbols['BTCUSD']['trades'] == 1
