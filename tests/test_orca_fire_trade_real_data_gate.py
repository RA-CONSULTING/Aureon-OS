import ast
import math
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace


def _load_methods(requests_obj, seer_available=False, get_seer=None):
    source_path = (
        Path(__file__).resolve().parents[1]
        / 'aureon'
        / 'bots'
        / 'orca_fire_trade.py'
    )
    tree = ast.parse(source_path.read_text(encoding='utf-8'))
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'FireTrader'
    )
    wanted = {
        '_account_receipt',
        '_definitely_not_submitted',
        '_finite_number',
        '_fresh_timestamp',
        '_seer_global_gate',
        '_seer_symbol_signal',
        '_log_seer_prediction',
        '_normalize_terminal_fill',
        '_order_id',
        '_quote_asset',
        '_quote_receipt',
        '_submit_and_confirm',
    }
    methods = [
        node
        for node in class_node.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    isolated_class = ast.ClassDef(
        name='FireTrader',
        bases=[],
        keywords=[],
        body=methods,
        decorator_list=[],
    )
    isolated = ast.Module(body=[isolated_class], type_ignores=[])
    ast.fix_missing_locations(isolated)
    namespace = {
        '_seer_available': seer_available,
        'datetime': datetime,
        'get_seer': get_seer,
        'json': __import__('json'),
        'log_fire': lambda message: None,
        'math': math,
        'requests': requests_obj,
        'time': time,
    }
    exec(compile(isolated, str(source_path), 'exec'), namespace)
    fire_trader = namespace['FireTrader']
    return {
        **{name: getattr(fire_trader, name) for name in wanted},
        '_class': fire_trader,
    }


def _trader():
    return SimpleNamespace(
        _SEER_VISION_TTL_SECS=300,
        _SEER_CANDLE_TTL_SECS=5400,
        _TIMEFRAME_LAYERS=[('1m', 60)],
        _load_goal_distance=lambda: 100.0,
        _publish_fire_event=lambda *args, **kwargs: None,
    )


def test_global_seer_unavailable_denies_buy():
    methods = _load_methods(SimpleNamespace(), seer_available=False)

    approved, risk, receipt = methods['_seer_global_gate'](_trader())

    assert approved is False
    assert risk == 0.0
    assert receipt['truth_status'] == 'no_data'
    assert receipt['decision_status'] == 'denied'
    assert receipt['generated_values'] is False


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def _candles(last_close_time):
    rows = []
    for index in range(6):
        close_time = last_close_time - (5 - index) * 3600
        open_price = 100.0 + index
        rows.append([
            int((close_time - 3600) * 1000),
            str(open_price),
            str(open_price + 2.0),
            str(open_price - 1.0),
            str(open_price + 1.0),
            str(100.0 + index * 10.0),
            int(close_time * 1000),
        ])
    return rows


def test_symbol_signal_requires_fresh_closed_candles():
    now = time.time()
    requests_obj = SimpleNamespace(
        get=lambda *args, **kwargs: _Response(200, _candles(now - 30))
    )
    methods = _load_methods(requests_obj)

    bullish, confidence, details = methods['_seer_symbol_signal'](
        _trader(), 'BTC'
    )

    assert bullish is True
    assert confidence > 0
    assert details['truth_status'] == 'real_derived'
    assert details['source_timestamp']
    assert details['generated_values'] is False


def test_symbol_signal_provider_error_or_stale_data_denies_buy():
    error_methods = _load_methods(
        SimpleNamespace(
            get=lambda *args, **kwargs: _Response(503, [])
        )
    )
    approved, confidence, details = error_methods['_seer_symbol_signal'](
        _trader(), 'BTC'
    )
    assert approved is False
    assert confidence == 0.0
    assert details['truth_status'] == 'no_data'

    stale_methods = _load_methods(
        SimpleNamespace(
            get=lambda *args, **kwargs: _Response(
                200,
                _candles(time.time() - 5401),
            )
        )
    )
    approved, confidence, details = stale_methods['_seer_symbol_signal'](
        _trader(), 'BTC'
    )
    assert approved is False
    assert confidence == 0.0
    assert details['reason'] == 'STALE_CANDLE_RECEIPT'


def test_prediction_writer_refuses_unproven_symbol_signal():
    methods = _load_methods(SimpleNamespace())

    result = methods['_log_seer_prediction'](
        _trader(),
        'BTCUSDC',
        'binance',
        100.0,
        {},
        None,
    )

    assert result is False


def _execution_trader(methods, kraken=None, binance=None):
    trader = methods['_class'].__new__(methods['_class'])
    trader.kraken = kraken
    trader.binance = binance
    trader._ACCOUNT_TTL_SECS = 120
    trader._QUOTE_TTL_SECS = 120
    trader._FILL_TTL_SECS = 900
    trader._reconciliation_attempted = set()
    trader._unresolved_order_keys = set()
    trader._blocked_submission_exchanges = set()
    return trader


class _OrderClient:
    def __init__(self, submitted, readback=None):
        self.submitted = submitted
        self.readback = readback
        self.place_calls = 0
        self.read_calls = 0

    def place_market_order(self, *args, **kwargs):
        self.place_calls += 1
        return self.submitted

    def get_order_status(self, order_id):
        self.read_calls += 1
        return self.readback


def _kraken_fill(order_id='K1'):
    now = time.time()
    return {
        'status': 'FILLED',
        'orderId': order_id,
        'symbol': 'XXBTZUSD',
        'side': 'BUY',
        'source_timestamp': now,
        'executedQty': '0.01',
        'filled_avg_price': '50000',
        'cummulativeQuoteQty': '500',
        'fee': '1.30',
        'fee_asset': 'USD',
        'fills': [{'tradeId': 'T1'}],
        'fill_receipt_complete': True,
        'eligible_for_accounting': True,
        'eligible_for_learning': True,
        'generated_values': False,
        'reconciliation_required': False,
    }


def test_ack_reconciles_once_and_unresolved_submission_is_suppressed():
    methods = _load_methods(SimpleNamespace())
    ack = {
        'status': 'pending_reconciliation',
        'orderId': 'K1',
        'symbol': 'XBTUSD',
        'side': 'BUY',
        'submitted': True,
    }
    client = _OrderClient(ack, _kraken_fill())
    trader = _execution_trader(methods, kraken=client)

    confirmed = trader._submit_and_confirm('kraken', 'XBTUSD', 'buy', quote_qty=500)

    assert confirmed['status'] == 'filled'
    assert confirmed['receipt']['fee'] == 1.30
    assert client.place_calls == 1
    assert client.read_calls == 1

    pending_client = _OrderClient(ack, {**ack, 'status': 'open'})
    trader = _execution_trader(methods, kraken=pending_client)
    first = trader._submit_and_confirm('kraken', 'XBTUSD', 'buy', quote_qty=500)
    second = trader._submit_and_confirm('kraken', 'XBTUSD', 'buy', quote_qty=500)

    assert first['status'] == 'unresolved'
    assert second['status'] == 'suppressed_unresolved_duplicate'
    assert pending_client.place_calls == 1
    assert pending_client.read_calls == 1


def test_dry_run_and_incomplete_or_stale_receipts_fail_closed():
    methods = _load_methods(SimpleNamespace())
    dry_client = _OrderClient({
        'status': 'not_submitted',
        'dryRun': True,
        'submitted': False,
        'symbol': 'BTCUSDC',
        'side': 'BUY',
    })
    trader = _execution_trader(methods, binance=dry_client)
    result = trader._submit_and_confirm('binance', 'BTCUSDC', 'buy', quote_qty=100)
    assert result['status'] == 'not_submitted'

    fresh_quote = {
        'symbol': 'BTCUSDC',
        'lastPrice': '100',
        'priceChangePercent': '1.5',
        'quoteVolume': '1000000',
        'closeTime': int(time.time() * 1000),
    }
    assert trader._quote_receipt('binance', 'BTCUSDC', fresh_quote) is not None
    stale_quote = {**fresh_quote, 'closeTime': int((time.time() - 121) * 1000)}
    assert trader._quote_receipt('binance', 'BTCUSDC', stale_quote) is None
    assert trader._normalize_terminal_fill(
        'binance', {'status': 'FILLED'}, 'BTCUSDC', 'buy'
    ) is None
