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


def _attempt_not_submitted(order_result):
    for key in ('status', 'data_status', 'truth_status'):
        if str(order_result.get(key) or '').strip().lower() == 'not_submitted':
            return True
    if order_result.get('dryRun') is True or order_result.get('dry_run') is True:
        return True
    reason = str(order_result.get('reason') or '').strip().lower()
    return 'not_submitted' in reason or reason.startswith('dry_run')


def _attempt_error_status(order_result, error):
    """Keep the provider's own status or error text. Never return FILLED."""
    status = order_result.get('status')
    if isinstance(status, str) and status.strip():
        token = status.strip().upper()
        if token != 'FILLED':
            return token
    candidate = ''
    if isinstance(error, str):
        candidate = error.strip()
    elif isinstance(error, (list, tuple)):
        texts = [str(item).strip() for item in error if str(item).strip()]
        if len(texts) == 1:
            candidate = texts[0]
        elif texts:
            candidate = '; '.join(texts)
    if candidate and candidate.upper() != 'FILLED':
        return candidate
    return 'FAILED'


def _plain_kraken_addorder_ack(order_result):
    """Kraken AddOrder result: txid list plus descr, no status or executedQty."""
    if str(order_result.get('status') or '').strip():
        return False
    if 'executedQty' in order_result or 'vol_exec' in order_result:
        return False
    descr = order_result.get('descr')
    txids = order_result.get('txid')
    if not isinstance(descr, dict) or not descr:
        return False
    if not isinstance(txids, (list, tuple)) or not txids:
        return False
    return bool(kraken_order_txids(txids))


def _attempt_log_status(order_result, exchange):
    """Status string written to orca_executions.json.

    Does not place, size, or exit an order. FILLED is only
    confirmed_exchange_fill: Kraken closed with vol_exec > 0 and a txid,
    or Binance FILLED with executedQty > 0.
    """
    if not isinstance(order_result, dict):
        return 'FAILED'
    if _attempt_not_submitted(order_result):
        return 'NOT_SUBMITTED'
    error = order_result.get('error')
    if error:
        return _attempt_error_status(order_result, error)
    venue = str(exchange or '').strip().lower()
    if confirmed_exchange_fill(order_result, venue):
        return 'FILLED'
    if venue == 'kraken' and _plain_kraken_addorder_ack(order_result):
        return 'SUBMITTED/UNCONFIRMED'
    status = order_result.get('status')
    if isinstance(status, str) and status.strip():
        token = status.strip().upper()
        if token == 'FILLED':
            if venue == 'kraken':
                return 'UNCONFIRMED'
            return 'ZERO_FILL'
        return token
    return 'FAILED'
