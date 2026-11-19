"""Confirmed-fill decision for an Orca attempt.

The kill chain uses this when it labels ``orca_executions.json``. The
real-fill ledger can call ``confirmed_exchange_fill`` before it writes a
row. This module does not place orders or write that ledger.
"""
import math

_SENTINEL_TXIDS = frozenset({
    'unknown', 'none', 'null', '0', 'dry_run', 'dry-run', 'dryrun',
    'not_submitted', 'mock', 'mock_order', 'test', 'test_order',
})


def positive_fill_amount(value):
    """True when a provider quantity is a finite number greater than zero."""
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return False
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return False
    # NaN makes every comparison false, so `not (amount <= 0)` would count
    # NaN as positive if this rejection were removed. Infinity would too.
    if not math.isfinite(amount):
        return False
    return not (amount <= 0)


def kraken_order_txids(raw):
    """Kraken txid string or txid list. Sentinels and dry-run ids are dropped."""
    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        return []
    found = []
    for item in items:
        if not isinstance(item, str):
            return []
        token = item.strip()
        if not token:
            return []
        normalized = token.lower().replace('-', '_').replace(' ', '_')
        if (
            normalized in _SENTINEL_TXIDS
            or normalized.startswith(('dry_run', 'mock_', 'test_'))
        ):
            return []
        found.append(token)
    return found


def confirmed_exchange_fill(order_result, exchange):
    """True only for a confirmed exchange fill.

    Kraken: status ``closed``, ``vol_exec`` > 0, and a real txid.
    Binance: status ``FILLED`` and ``executedQty`` > 0.
    """
    if not isinstance(order_result, dict):
        return False
    venue = str(exchange or '').strip().lower()
    if venue == 'kraken':
        status = str(order_result.get('status') or '').strip().lower()
        return (
            status == 'closed'
            and positive_fill_amount(order_result.get('vol_exec'))
            and bool(kraken_order_txids(order_result.get('txid')))
        )
    if venue == 'binance':
        status = str(order_result.get('status') or '').strip().upper()
        return (
            status == 'FILLED'
            and positive_fill_amount(order_result.get('executedQty'))
        )
    return False
