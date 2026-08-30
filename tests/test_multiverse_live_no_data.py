import ast
import logging
import math
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest


def _load_fetch_market_data_without_module_side_effects():
    return _load_engine_method_without_module_side_effects('fetch_market_data')


def _load_engine_method_without_module_side_effects(method_name):
    source_path = (
        Path(__file__).resolve().parents[1]
        / 'aureon'
        / 'simulation'
        / 'aureon_multiverse_live.py'
    )
    tree = ast.parse(source_path.read_text(encoding='utf-8'))
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'MultiverseLiveEngine'
    )
    method_node = next(
        node
        for node in class_node.body
        if isinstance(node, ast.FunctionDef) and node.name == method_name
    )
    isolated = ast.Module(body=[method_node], type_ignores=[])
    ast.fix_missing_locations(isolated)
    namespace = {
        'Dict': dict,
        'logger': logging.getLogger('multiverse-no-data-test'),
        'time': time,
        'math': math,
        'datetime': datetime,
        'KRAKEN_BLACKLIST': set(),
        'Any': Any,
        'Dict': Dict,
        'List': List,
        'Optional': Optional,
    }
    exec(compile(isolated, str(source_path), 'exec'), namespace)
    return namespace[method_name]


def _load_engine_class_without_module_side_effects(*method_names):
    source_path = (
        Path(__file__).resolve().parents[1]
        / 'aureon'
        / 'simulation'
        / 'aureon_multiverse_live.py'
    )
    tree = ast.parse(source_path.read_text(encoding='utf-8'))
    source_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'MultiverseLiveEngine'
    )
    selected = [
        node
        for node in source_class.body
        if isinstance(node, ast.FunctionDef) and node.name in method_names
    ]
    isolated_class = ast.ClassDef(
        name='IsolatedEngine',
        bases=[],
        keywords=[],
        body=selected,
        decorator_list=[],
    )
    isolated = ast.Module(body=[isolated_class], type_ignores=[])
    ast.fix_missing_locations(isolated)
    namespace = {
        'Any': Any,
        'CommandoSignal': Any,
        'Dict': Dict,
        'List': List,
        'Optional': Optional,
        'datetime': datetime,
        'logger': logging.getLogger('multiverse-no-data-test'),
        'math': math,
        'time': time,
        'MULTIVERSE_AVAILABLE': False,
        'Thought': SimpleNamespace,
        'multiverse_record_outcome': lambda *args, **kwargs: None,
    }
    exec(compile(isolated, str(source_path), 'exec'), namespace)
    return namespace['IsolatedEngine']


def _execution_engine_class():
    return _load_engine_class_without_module_side_effects(
        '_quote_asset_for_symbol',
        '_actionable_market_price',
        'get_available_capital',
        '_capital_for_signal',
        '_receipt_timestamp',
        '_base_asset_for_symbol',
        '_terminal_fill_receipt',
        '_execute_signal_with_receipts',
    )


def _signal(action='BUY', symbol='BTCUSDT', exchange='binance'):
    payload = {
        'symbol': symbol,
        'action': action,
        'exchange': exchange,
    }
    return SimpleNamespace(
        action=action,
        symbol=symbol,
        exchange=exchange,
        source='TEST_PROVIDER_SIGNAL',
        confidence=0.9,
        commando_type='FALCON',
        to_dict=lambda: dict(payload),
    )


def _fresh_market(symbol='BTCUSDT', exchange='binance', price=10.0):
    now = time.time()
    return {
        'prices': {symbol: price},
        'source': {symbol: exchange},
        'provenance': {
            symbol: {
                'source_id': f'{exchange}:ticker',
                'source_timestamp': now,
                'truth_status': 'real_observed',
                'generated_values': False,
            }
        },
        'eligible_for_external_action': True,
        'generated_values': False,
    }


def _venue_snapshot(exchange='binance', asset='USDT', amount=100.0):
    received_at = time.time()
    return {
        'venues': {
            exchange: {
                'status': 'observed',
                'truth_status': 'real_observed',
                'source_id': f'{exchange}:account',
                'source_timestamp': None,
                'received_at': received_at,
                'settlement_asset': asset,
                'settlement_amount': amount,
                'eligible_for_external_action': True,
                'generated_values': False,
            }
        },
        'aggregate_status': 'complete',
        'aggregate_cash': amount,
        'aggregate_currency': asset,
        'generated_values': False,
    }


def _configured_execution_engine(order, action='BUY'):
    engine = _execution_engine_class()()
    calls = []

    def place_market_order(*args, **kwargs):
        calls.append((args, kwargs))
        return order

    engine.simulation_mode = False
    engine.positions = {}
    engine.pending_orders = {}
    engine.binance = SimpleNamespace(place_market_order=place_market_order)
    engine.kraken = None
    engine.alpaca = None
    engine.balance_snapshot = _venue_snapshot()
    engine.real_balances = {'binance': {'USDT': 100.0, 'BTC': 2.0}}
    engine.market_data = _fresh_market()
    engine._refresh_real_balances = lambda: engine.balance_snapshot
    engine._validate_symbol_tradeable = lambda symbol, exchange: (True, 'OK')
    engine._mycelium_allows_entry = lambda *args, **kwargs: True
    engine.commando = SimpleNamespace(growth_aggression=1.0)
    engine.mycelium_directive = {'entry_budget_scale': 1.0}
    engine.stats = {
        'trades_executed': 0,
        'total_profit': None,
        'total_profit_currency': None,
        'realized_profit_by_currency': {},
        'win_count': 0,
        'loss_count': 0,
    }
    engine.revenue_board = None
    engine.mycelium = None
    engine.thought_bus = None
    if action == 'SELL':
        engine.positions['BTCUSDT'] = {
            'entry_price': 20.0,
            'quantity': 1.5,
            'executed_quantity': 1.5,
            'entry_quote_amount': 30.0,
            'entry_fee_quote': 0.3,
            'quote_asset': 'USDT',
            'exchange': 'binance',
            'truth_status': 'real_observed',
            'eligible_for_accounting': True,
            'generated_values': False,
        }
    return engine, calls


def test_market_feed_failure_is_explicit_no_data_without_generated_prices():
    fetch_market_data = _load_fetch_market_data_without_module_side_effects()
    engine = SimpleNamespace(
        binance=None,
        kraken=None,
        alpaca=None,
        market_data={},
    )

    result = fetch_market_data(engine)

    assert result['prices'] == {}
    assert result['changes'] == {}
    assert result['volumes'] == {}
    assert result['momentum'] == {}
    assert result['truth_status'] == 'no_data'
    assert result['decision_status'] == 'no_data'
    assert result['source_timestamp'] is None
    assert result['source_timestamps'] == {}
    assert result['provenance'] == {}
    assert result['eligible_for_external_action'] is False
    assert result['generated_values'] is False


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _Session:
    def __init__(self, payload):
        self.payload = payload

    def get(self, *args, **kwargs):
        return _Response(self.payload)


def test_binance_rows_require_provider_close_time_and_keep_per_symbol_provenance():
    now = time.time()
    rows = [
        {
            'symbol': 'BTCUSDT',
            'lastPrice': '100.0',
            'priceChangePercent': '2.0',
            'quoteVolume': '12345.0',
            'closeTime': int(now * 1000),
        },
        {
            'symbol': 'STALEUSDT',
            'lastPrice': '5.0',
            'priceChangePercent': '1.0',
            'quoteVolume': '50.0',
            'closeTime': int((now - 121.0) * 1000),
        },
    ]
    binance = SimpleNamespace(
        base='https://provider.invalid',
        session=_Session(rows),
        get_allowed_pairs_uk=lambda: {'BTCUSDT', 'STALEUSDT'},
    )
    engine = SimpleNamespace(
        binance=binance,
        kraken=None,
        alpaca=None,
        market_data={},
    )

    result = _load_fetch_market_data_without_module_side_effects()(engine)

    assert result['prices'] == {'BTCUSDT': 100.0}
    assert result['source_timestamp'] is None
    assert result['source_timestamps']['BTCUSDT'] == pytest.approx(now, abs=0.01)
    assert result['provenance']['BTCUSDT']['source_id'] == (
        'binance:/api/v3/ticker/24hr'
    )
    assert result['truth_status'] == 'real_observed'
    assert result['decision_status'] == 'ready'
    assert result['eligible_for_external_action'] is True


def test_kraken_rows_without_fresh_provider_time_are_excluded():
    now = time.time()
    kraken = SimpleNamespace(
        get_24h_tickers=lambda: [
            {
                'symbol': 'ETHUSD',
                'lastPrice': '2000.0',
                'priceChangePercent': '1.5',
                'quoteVolume': '9000.0',
                'source_id': 'kraken:/0/public/Ticker+/0/public/Time',
                'source_timestamp': now,
                'truth_status': 'real_derived',
                'generated_values': False,
            },
            {
                'symbol': 'OLDUSD',
                'lastPrice': '10.0',
                'priceChangePercent': '1.0',
                'quoteVolume': '10.0',
                'source_id': 'kraken:/0/public/Ticker+/0/public/Time',
                'source_timestamp': now - 121.0,
                'truth_status': 'real_derived',
                'generated_values': False,
            },
        ]
    )
    engine = SimpleNamespace(
        binance=None,
        kraken=kraken,
        alpaca=None,
        market_data={},
    )

    result = _load_fetch_market_data_without_module_side_effects()(engine)

    assert result['prices'] == {'ETHUSD': 2000.0}
    assert result['source'] == {'ETHUSD': 'kraken'}
    assert 'OLDUSD' not in result['provenance']


def test_alpaca_quote_is_visible_but_not_actionable_without_change_and_volume():
    now = time.time()
    provider_iso = datetime.fromtimestamp(now).astimezone().isoformat()

    def get_last_quote(symbol):
        if symbol != 'AAPL':
            return {}
        return {
            'last': {'price': 101.0},
            'raw': {
                'quote': {
                    'bp': 100.0,
                    'ap': 102.0,
                    't': provider_iso,
                }
            },
        }

    engine = SimpleNamespace(
        binance=None,
        kraken=None,
        alpaca=SimpleNamespace(get_last_quote=get_last_quote),
        market_data={},
    )

    result = _load_fetch_market_data_without_module_side_effects()(engine)

    assert result['prices'] == {}
    assert result['price_only']['AAPL/USD']['price'] == 101.0
    assert result['price_only']['AAPL/USD']['source_timestamp'] == pytest.approx(
        now, abs=0.01
    )
    assert result['decision_status'] == 'no_data'
    assert result['eligible_for_external_action'] is False
    assert result['generated_values'] is False


def test_conversion_adapter_is_preflight_only_and_never_calls_a_venue():
    calls = []

    def forbidden_order(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError('conversion adapter attempted an order')

    venue = SimpleNamespace(place_market_order=forbidden_order)
    engine = SimpleNamespace(
        binance=venue,
        kraken=venue,
        alpaca=None,
        labyrinth=None,
    )
    build = _load_engine_method_without_module_side_effects(
        '_build_ladder_client'
    )
    adapter = build(engine)

    receipt = adapter.convert_crypto('kraken', 'BTC', 'USD', 0.25)

    assert receipt['status'] == 'not_submitted'
    assert receipt['eligible_for_external_action'] is False
    assert receipt['eligible_for_accounting'] is False
    assert receipt['generated_values'] is False
    assert calls == []


def test_startup_harvest_keeps_holdings_risk_only_and_never_liquidates():
    calls = []

    def forbidden_order(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError('startup harvest attempted an order')

    binance = SimpleNamespace(
        uk_mode=False,
        account=lambda: {
            'balances': [
                {'asset': 'BTC', 'free': '0.2', 'locked': '0.1'},
                {'asset': 'USDT', 'free': '20.0', 'locked': '0.0'},
            ]
        },
        can_trade_symbol=lambda symbol: (True, 'provider_allowed'),
        place_market_order=forbidden_order,
    )
    kraken = SimpleNamespace(
        get_account_balance=lambda: {'ETH': 0.5, 'USD': 10.0},
        place_market_order=forbidden_order,
    )
    engine = SimpleNamespace(
        binance=binance,
        kraken=kraken,
        positions={},
        unproven_holdings=[],
        harvest_receipt={},
    )
    harvest = _load_engine_method_without_module_side_effects(
        '_harvest_existing_assets'
    )

    receipt = harvest(engine, liquidate=True)

    assert receipt['status'] == 'not_submitted'
    assert receipt['eligible_for_external_action'] is False
    assert receipt['eligible_for_accounting'] is False
    assert receipt['holding_count'] == 2
    assert engine.positions == {}
    assert all(item['cost_basis'] is None for item in engine.unproven_holdings)
    assert all(item['valuation'] is None for item in engine.unproven_holdings)
    assert calls == []


def test_balance_refresh_preserves_exact_currencies_without_parity_or_equity():
    now_ms = int(time.time() * 1000)
    engine = SimpleNamespace(
        binance=SimpleNamespace(
            uk_mode=True,
            dry_run=False,
            use_testnet=False,
            account=lambda: {
                'updateTime': now_ms,
                'balances': [
                    {'asset': 'USDC', 'free': '11', 'locked': '0'},
                    {'asset': 'USDT', 'free': '4', 'locked': '0'},
                ],
            },
        ),
        kraken=SimpleNamespace(
            dry_run=False,
            account=lambda: {
                'balances': [
                    {'asset': 'USD', 'free': '3', 'locked': '0'},
                    {'asset': 'USDT', 'free': '7', 'locked': '0'},
                ]
            },
        ),
        alpaca=SimpleNamespace(
            use_paper=False,
            get_account=lambda: {
                'currency': 'USD',
                'cash': '5',
                'trading_blocked': False,
            },
        ),
        real_balances={
            'binance': {'USDT': 999.0},
            'kraken': {'USD': 999.0},
            'alpaca': {'USD': 999.0},
        },
        total_equity=999.0,
    )

    snapshot = _load_engine_method_without_module_side_effects(
        '_refresh_real_balances'
    )(engine)

    assert engine.real_balances['binance'] == {'USDC': 11.0, 'USDT': 4.0}
    assert engine.real_balances['kraken'] == {'USD': 3.0, 'USDT': 7.0}
    assert engine.real_balances['alpaca'] == {'USD': 5.0}
    assert snapshot['venues']['binance']['settlement_asset'] == 'USDC'
    assert snapshot['venues']['binance']['settlement_amount'] == 11.0
    assert snapshot['venues']['kraken']['settlement_amount'] == 3.0
    assert snapshot['aggregate_cash'] is None
    assert snapshot['aggregate_currency'] is None
    assert snapshot['eligible_for_external_action'] is False
    assert engine.total_equity is None
    assert engine.equity_receipt['value'] is None


def test_malformed_venue_receipt_clears_stale_value_and_blocks_partial_total():
    engine = SimpleNamespace(
        binance=SimpleNamespace(
            uk_mode=False,
            dry_run=False,
            use_testnet=False,
            account=lambda: {
                'balances': [
                    {'asset': 'USDT', 'free': '10', 'locked': '0'},
                ]
            },
        ),
        kraken=SimpleNamespace(
            dry_run=False,
            account=lambda: {
                'balances': [
                    {'asset': 'USD', 'free': '9'},
                ]
            },
        ),
        alpaca=None,
        real_balances={
            'binance': {'USDT': 1000.0},
            'kraken': {'USD': 1000.0},
            'alpaca': {},
        },
    )

    snapshot = _load_engine_method_without_module_side_effects(
        '_refresh_real_balances'
    )(engine)

    assert engine.real_balances['binance'] == {'USDT': 10.0}
    assert engine.real_balances['kraken'] == {}
    assert snapshot['status'] == 'partial'
    assert snapshot['truth_status'] == 'real_observed'
    assert snapshot['venues']['kraken']['status'] == 'no_data'
    assert snapshot['aggregate_cash'] is None
    assert snapshot['reason'].startswith('all_configured_venues_require')


def test_all_failed_balance_receipts_are_not_labelled_observed():
    engine = SimpleNamespace(
        binance=SimpleNamespace(
            uk_mode=False,
            dry_run=False,
            use_testnet=False,
            account=lambda: {'balances': [{'asset': 'USDT', 'free': 'x'}]},
        ),
        kraken=None,
        alpaca=None,
        real_balances={'binance': {'USDT': 1000.0}},
    )

    snapshot = _load_engine_method_without_module_side_effects(
        '_refresh_real_balances'
    )(engine)

    assert engine.real_balances['binance'] == {}
    assert snapshot['status'] == 'no_data'
    assert snapshot['truth_status'] == 'no_data'
    assert snapshot['aggregate_cash'] is None


def test_total_cash_requires_complete_same_denomination_receipts():
    engine_class = _load_engine_class_without_module_side_effects(
        '_get_total_cash',
    )
    engine = engine_class()
    engine.real_balances = {
        'binance': {'USDT': 4.0},
        'kraken': {'USD': 3.0},
        'alpaca': {'USD': 5.0},
    }
    engine.balance_snapshot = {
        'aggregate_status': 'no_data',
        'aggregate_cash': None,
        'aggregate_currency': None,
        'venues': {
            'binance': {
                'eligible_for_external_action': True,
                'truth_status': 'real_observed',
                'generated_values': False,
                'source_id': 'binance:account',
                'received_at': time.time(),
            },
            'kraken': {
                'eligible_for_external_action': True,
                'truth_status': 'real_observed',
                'generated_values': False,
                'source_id': 'kraken:account',
                'received_at': time.time(),
            },
            'alpaca': {
                'eligible_for_external_action': True,
                'truth_status': 'real_observed',
                'generated_values': False,
                'source_id': 'alpaca:account',
                'received_at': time.time(),
            },
        },
    }

    assert engine._get_total_cash() is None
    assert engine._get_total_cash('USD') == 8.0
    assert engine._get_total_cash('USDT') == 4.0
    assert engine._get_total_cash('USDC') is None


def test_available_capital_requires_fresh_exact_venue_currency():
    engine_class = _load_engine_class_without_module_side_effects(
        '_get_total_cash',
        'get_available_capital',
    )
    engine = engine_class()
    engine.real_balances = {'binance': {'USDC': 0.0}}
    engine.balance_snapshot = _venue_snapshot(
        exchange='binance',
        asset='USDC',
        amount=0.0,
    )

    assert engine.get_available_capital('binance', 'USDC') == 0.0
    assert engine.get_available_capital('binance', 'USDT') is None
    engine.balance_snapshot['venues']['binance']['received_at'] = time.time() - 31
    assert engine.get_available_capital('binance', 'USDC') is None


def test_available_capital_rejects_unproven_eligibility_flag():
    engine_class = _load_engine_class_without_module_side_effects(
        '_get_total_cash',
        'get_available_capital',
    )
    engine = engine_class()
    engine.real_balances = {'binance': {'USDT': 100.0}}
    engine.balance_snapshot = _venue_snapshot()
    engine.balance_snapshot['venues']['binance']['generated_values'] = True

    assert engine.get_available_capital('binance', 'USDT') is None


def test_tradeability_rejects_nonfinite_provider_price():
    validate = _load_engine_method_without_module_side_effects(
        '_validate_symbol_tradeable'
    )
    engine = SimpleNamespace(
        binance=SimpleNamespace(
            can_trade_symbol=lambda symbol: (True, 'OK'),
            best_price=lambda symbol: {'price': 'nan'},
        ),
        kraken=None,
        alpaca=None,
    )

    can_trade, reason = validate(engine, 'BTCUSDT', 'binance')

    assert can_trade is False
    assert 'No price data' in reason


def test_actionable_market_price_requires_fresh_same_venue_provenance():
    engine = _execution_engine_class()()
    engine.market_data = _fresh_market(price=12.5)

    assert engine._actionable_market_price('BTCUSDT', 'binance') == 12.5
    assert engine._actionable_market_price('BTCUSDT', 'kraken') is None
    engine.market_data['provenance']['BTCUSDT']['source_timestamp'] = (
        time.time() - 121
    )
    assert engine._actionable_market_price('BTCUSDT', 'binance') is None


def test_run_cycle_returns_no_data_before_any_action_without_market_evidence():
    no_market = {
        'prices': {},
        'changes': {},
        'volumes': {},
        'source': {},
        'provenance': {},
        'eligible_for_external_action': False,
        'truth_status': 'no_data',
        'generated_values': False,
    }
    balance_snapshot = {
        'venues': {},
        'aggregate_cash': None,
        'aggregate_currency': None,
        'aggregate_status': 'no_data',
        'eligible_for_external_action': False,
        'generated_values': False,
    }
    action_calls = []
    engine = SimpleNamespace(
        stats={'cycles': 0},
        fetch_market_data=lambda: no_market,
        mycelium=None,
        mycelium_directive={},
        _compute_mycelium_directive=lambda *args: {
            'allow_entries': False,
            'truth_status': 'no_data',
        },
        _publish_mycelium_directive=lambda *args: None,
        _update_mycelium_connections=lambda: {},
        labyrinth=None,
        _refresh_real_balances=lambda: balance_snapshot,
        _get_total_cash=lambda: None,
        _update_mycelium_governing_metrics=lambda: {},
        execute_signal=lambda signal: action_calls.append(signal),
    )

    result = _load_engine_method_without_module_side_effects('run_cycle')(
        engine
    )

    assert result['decision_status'] == 'no_data'
    assert result['reason'] == 'complete_fresh_market_receipts_required'
    assert result['real_cash_balance'] is None
    assert result['executions'] == []
    assert action_calls == []


def test_terminal_fill_normalizer_rejects_ack_and_uses_provider_fill_values():
    engine_class = _execution_engine_class()
    now_ms = int(time.time() * 1000)
    acknowledgement = {
        'symbol': 'BTCUSDT',
        'orderId': 101,
        'side': 'BUY',
        'status': 'NEW',
        'transactTime': now_ms,
    }
    assert engine_class._terminal_fill_receipt(
        acknowledgement,
        symbol='BTCUSDT',
        action='BUY',
        exchange='binance',
        quote_asset='USDT',
        production_mode_verified=True,
    ) is None

    terminal = {
        'symbol': 'BTCUSDT',
        'orderId': 102,
        'side': 'BUY',
        'status': 'FILLED',
        'transactTime': now_ms,
        'executedQty': '1.5',
        'cummulativeQuoteQty': '30',
        'fills': [
            {
                'price': '20',
                'qty': '1.5',
                'commission': '0.3',
                'commissionAsset': 'USDT',
            }
        ],
    }
    assert engine_class._terminal_fill_receipt(
        terminal,
        symbol='BTCUSDT',
        action='BUY',
        exchange='binance',
        quote_asset='USDT',
    ) is None
    receipt = engine_class._terminal_fill_receipt(
        terminal,
        symbol='BTCUSDT',
        action='BUY',
        exchange='binance',
        quote_asset='USDT',
        production_mode_verified=True,
    )

    assert receipt['average_price'] == 20.0
    assert receipt['executed_quantity'] == 1.5
    assert receipt['quote_amount'] == 30.0
    assert receipt['fee_quote'] == 0.3
    assert receipt['eligible_for_accounting'] is True
    assert receipt['generated_values'] is False


def test_terminal_fill_requires_fresh_provider_timestamp():
    engine_class = _execution_engine_class()
    terminal = {
        'symbol': 'BTCUSDT',
        'orderId': 102,
        'side': 'BUY',
        'status': 'FILLED',
        'executedQty': '1.5',
        'cummulativeQuoteQty': '30',
        'fills': [
            {
                'price': '20',
                'qty': '1.5',
                'commission': '0.3',
                'commissionAsset': 'USDT',
            }
        ],
    }
    assert engine_class._terminal_fill_receipt(
        terminal,
        symbol='BTCUSDT',
        action='BUY',
        exchange='binance',
        quote_asset='USDT',
        production_mode_verified=True,
    ) is None
    terminal['transactTime'] = int((time.time() - 301) * 1000)
    assert engine_class._terminal_fill_receipt(
        terminal,
        symbol='BTCUSDT',
        action='BUY',
        exchange='binance',
        quote_asset='USDT',
        production_mode_verified=True,
    ) is None


def test_simulation_execution_never_submits_or_mutates_positions():
    engine, calls = _configured_execution_engine(
        {'status': 'FILLED'},
        action='BUY',
    )
    engine.simulation_mode = True

    result = engine._execute_signal_with_receipts(_signal())

    assert result['status'] == 'not_submitted'
    assert result['truth_status'] == 'dry_run'
    assert result['executed'] is False
    assert engine.positions == {}
    assert engine.stats['trades_executed'] == 0
    assert calls == []


def test_order_ack_is_quarantined_without_position_or_accounting_mutation():
    order = {
        'symbol': 'BTCUSDT',
        'orderId': 201,
        'side': 'BUY',
        'status': 'NEW',
    }
    engine, calls = _configured_execution_engine(order, action='BUY')

    first = engine._execute_signal_with_receipts(_signal())
    second = engine._execute_signal_with_receipts(_signal())

    assert first['status'] == 'pending_reconciliation'
    assert first['executed'] is False
    assert first['eligible_for_accounting'] is False
    assert engine.positions == {}
    assert engine.stats['trades_executed'] == 0
    assert engine.stats['total_profit'] is None
    assert len(engine.pending_orders) == 1
    assert second['status'] == 'pending_reconciliation'
    assert len(calls) == 1


def test_execution_does_not_submit_when_balance_provenance_is_incomplete():
    order = {
        'symbol': 'BTCUSDT',
        'orderId': 202,
        'side': 'BUY',
        'status': 'NEW',
    }
    engine, calls = _configured_execution_engine(order, action='BUY')
    engine.balance_snapshot['venues']['binance'][
        'eligible_for_external_action'
    ] = False

    result = engine._execute_signal_with_receipts(_signal())

    assert result['status'] == 'not_submitted'
    assert result['executed'] is False
    assert 'balance provenance' in result['error']
    assert engine.positions == {}
    assert calls == []


def test_execution_rejects_generated_balance_receipt_before_submission():
    order = {
        'symbol': 'BTCUSDT',
        'orderId': 203,
        'side': 'BUY',
        'status': 'NEW',
    }
    engine, calls = _configured_execution_engine(order, action='BUY')
    engine.balance_snapshot['venues']['binance']['generated_values'] = True

    result = engine._execute_signal_with_receipts(_signal())

    assert result['status'] == 'not_submitted'
    assert result['executed'] is False
    assert 'balance provenance' in result['error']
    assert engine.positions == {}
    assert calls == []


def test_run_cycle_route_preflight_never_estimates_or_records_a_fill():
    source_path = (
        Path(__file__).resolve().parents[1]
        / 'aureon'
        / 'simulation'
        / 'aureon_multiverse_live.py'
    )
    tree = ast.parse(source_path.read_text(encoding='utf-8'))
    engine_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'MultiverseLiveEngine'
    )
    run_cycle = next(
        node
        for node in engine_class.body
        if isinstance(node, ast.FunctionDef) and node.name == 'run_cycle'
    )
    called_attributes = {
        node.func.attr
        for node in ast.walk(run_cycle)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert 'estimate_conversion_cost' not in called_attributes
    assert 'record_path_usage' not in called_attributes


def test_terminal_buy_uses_actual_provider_fill_not_market_or_requested_values():
    order = {
        'symbol': 'BTCUSDT',
        'orderId': 301,
        'side': 'BUY',
        'status': 'FILLED',
        'transactTime': int(time.time() * 1000),
        'executedQty': '1.5',
        'cummulativeQuoteQty': '30',
        'fills': [
            {
                'price': '20',
                'qty': '1.5',
                'commission': '0.3',
                'commissionAsset': 'USDT',
            }
        ],
    }
    engine, calls = _configured_execution_engine(order, action='BUY')

    result = engine._execute_signal_with_receipts(_signal())

    assert result['status'] == 'filled'
    assert result['executed'] is True
    assert result['eligible_for_accounting'] is True
    assert engine.positions['BTCUSDT']['entry_price'] == 20.0
    assert engine.positions['BTCUSDT']['quantity'] == 1.5
    assert engine.positions['BTCUSDT']['entry_quote_amount'] == 30.0
    assert engine.positions['BTCUSDT']['entry_fee_quote'] == 0.3
    assert engine.positions['BTCUSDT']['entry_price'] != 10.0
    assert engine.stats['trades_executed'] == 1
    assert len(calls) == 1


def test_terminal_sell_accounts_only_with_complete_provider_fee_receipt():
    complete = {
        'symbol': 'BTCUSDT',
        'orderId': 401,
        'side': 'SELL',
        'status': 'FILLED',
        'transactTime': int(time.time() * 1000),
        'executedQty': '1.5',
        'cummulativeQuoteQty': '37.5',
        'fills': [
            {
                'price': '25',
                'qty': '1.5',
                'commission': '0.375',
                'commissionAsset': 'USDT',
            }
        ],
    }
    engine, _ = _configured_execution_engine(complete, action='SELL')

    result = engine._execute_signal_with_receipts(
        _signal(action='SELL')
    )

    assert result['status'] == 'filled'
    assert result['eligible_for_accounting'] is True
    assert result['realized_pnl'] == pytest.approx(6.825)
    assert engine.stats['total_profit'] == pytest.approx(6.825)
    assert engine.stats['total_profit_currency'] == 'USDT'
    assert engine.stats['realized_profit_by_currency'] == {
        'USDT': pytest.approx(6.825)
    }
    assert engine.stats['win_count'] == 1
    assert engine.positions == {}

    incomplete = dict(complete)
    incomplete['orderId'] = 402
    incomplete['fills'] = []
    engine, _ = _configured_execution_engine(incomplete, action='SELL')

    result = engine._execute_signal_with_receipts(
        _signal(action='SELL')
    )

    assert result['executed'] is True
    assert result['eligible_for_accounting'] is False
    assert result['realized_pnl'] is None
    assert engine.stats['total_profit'] is None
    assert engine.stats['win_count'] == 0
    assert engine.stats['loss_count'] == 0
    assert engine.positions == {}


def test_realized_profit_is_never_summed_across_quote_currencies():
    first = {
        'symbol': 'BTCUSDT',
        'orderId': 501,
        'side': 'SELL',
        'status': 'FILLED',
        'transactTime': int(time.time() * 1000),
        'executedQty': '1.5',
        'cummulativeQuoteQty': '37.5',
        'fills': [
            {
                'price': '25',
                'qty': '1.5',
                'commission': '0.375',
                'commissionAsset': 'USDT',
            }
        ],
    }
    engine, _ = _configured_execution_engine(first, action='SELL')
    engine._execute_signal_with_receipts(_signal(action='SELL'))

    second = {
        'symbol': 'ETHUSD',
        'orderId': 502,
        'side': 'SELL',
        'status': 'FILLED',
        'transactTime': int(time.time() * 1000),
        'executedQty': '1',
        'cummulativeQuoteQty': '12',
        'fills': [
            {
                'price': '12',
                'qty': '1',
                'commission': '0.12',
                'commissionAsset': 'USD',
            }
        ],
    }
    engine.binance = SimpleNamespace(
        place_market_order=lambda *args, **kwargs: second
    )
    engine.real_balances['binance'].update({'ETH': 1.0, 'USD': 20.0})
    engine.market_data = _fresh_market(
        symbol='ETHUSD',
        exchange='binance',
        price=12.0,
    )
    engine.positions['ETHUSD'] = {
        'entry_price': 10.0,
        'quantity': 1.0,
        'executed_quantity': 1.0,
        'entry_quote_amount': 10.0,
        'entry_fee_quote': 0.1,
        'quote_asset': 'USD',
        'exchange': 'binance',
        'truth_status': 'real_observed',
        'eligible_for_accounting': True,
        'generated_values': False,
    }

    result = engine._execute_signal_with_receipts(
        _signal(action='SELL', symbol='ETHUSD')
    )

    assert result['realized_pnl'] == pytest.approx(1.78)
    assert result['realized_pnl_currency'] == 'USD'
    assert engine.stats['realized_profit_by_currency']['USDT'] == pytest.approx(
        6.825
    )
    assert engine.stats['realized_profit_by_currency']['USD'] == pytest.approx(
        1.78
    )
    assert engine.stats['total_profit'] is None
    assert engine.stats['total_profit_currency'] is None
