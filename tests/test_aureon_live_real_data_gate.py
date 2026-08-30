import ast
import logging
import math
import time
from pathlib import Path
from types import SimpleNamespace


def _load_methods():
    source_path = (
        Path(__file__).resolve().parents[1]
        / 'aureon'
        / 'trading'
        / 'aureon_live.py'
    )
    tree = ast.parse(source_path.read_text(encoding='utf-8'))
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'AureonLiveTrader'
    )
    methods = [
        node
        for node in class_node.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {'run_coherence_test', 'run'}
    ]
    isolated = ast.Module(body=methods, type_ignores=[])
    ast.fix_missing_locations(isolated)
    namespace = {
        'COHERENCE_MARKET_TTL_SECONDS': 180,
        'logger': logging.getLogger('aureon-live-gate-test'),
        'math': math,
        'sys': SimpleNamespace(
            exit=lambda code: (_ for _ in ()).throw(SystemExit(code))
        ),
        'time': time,
    }
    exec(compile(isolated, str(source_path), 'exec'), namespace)
    return namespace


class _Equation:
    def __init__(self):
        self.seen = None

    def compute_lambda(self, market_data):
        self.seen = market_data
        return {
            'lambda': 1.0,
            'coherence': 0.95,
            'substrate': 0.5,
        }


def _candle(close_time):
    return {
        'timestamp': int((close_time - 60) * 1000),
        'open': 100.0,
        'high': 102.0,
        'low': 99.0,
        'close': 101.0,
        'volume': 10.0,
        'quote_volume': 1005.0,
        'close_time': int(close_time * 1000),
    }


def test_coherence_gate_uses_complete_provider_candle():
    methods = _load_methods()
    equation = _Equation()
    now = time.time()
    trader = SimpleNamespace(
        symbol='BTCUSDT',
        client=SimpleNamespace(
            get_klines=lambda *args, **kwargs: [_candle(now)]
        ),
        master_eq=equation,
    )

    assert methods['run_coherence_test'](trader) is True
    assert equation.seen == {
        'price': 101.0,
        'volume': 1005.0,
        'high': 102.0,
        'low': 99.0,
        'open': 100.0,
        'change': 1.0,
    }
    assert trader.last_coherence_receipt['truth_status'] == 'live'
    assert trader.last_coherence_receipt['generated_values'] is False


def test_coherence_gate_rejects_stale_or_incomplete_candle():
    methods = _load_methods()
    equation = _Equation()
    stale = _candle(time.time() - 181)
    trader = SimpleNamespace(
        symbol='BTCUSDT',
        client=SimpleNamespace(
            get_klines=lambda *args, **kwargs: [stale]
        ),
        master_eq=equation,
    )
    assert methods['run_coherence_test'](trader) is False
    assert equation.seen is None

    incomplete = _candle(time.time())
    del incomplete['quote_volume']
    trader.client = SimpleNamespace(
        get_klines=lambda *args, **kwargs: [incomplete]
    )
    assert methods['run_coherence_test'](trader) is False
    assert equation.seen is None


def test_run_never_executes_when_coherence_is_unavailable():
    methods = _load_methods()
    executed = []
    trader = SimpleNamespace(
        stage=2,
        trades_executed=[],
        preflight_check=lambda: True,
        run_coherence_test=lambda: False,
        execute_trade=lambda side: executed.append(side),
    )

    assert methods['run'](trader, num_trades=2) is False
    assert executed == []
