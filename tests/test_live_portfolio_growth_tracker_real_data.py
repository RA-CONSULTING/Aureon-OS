import asyncio
import json
import time

import pytest

from aureon.portfolio.live_portfolio_growth_tracker import LivePortfolioTracker
from aureon.portfolio.live_portfolio_growth_with_trades import LivePortfolioGrowthTrader


class KrakenReceipt:
    dry_run = False

    def __init__(self, balances, tickers=None):
        self.balances = balances
        self.tickers = tickers or {}
        self.ticker_calls = []

    def get_account_balance(self):
        return dict(self.balances)

    def get_ticker(self, symbol):
        self.ticker_calls.append(symbol)
        return dict(self.tickers.get(symbol, {}))


class AlpacaAccountReceipt:
    dry_run = False
    use_paper = False

    def __init__(self, account):
        self.account = account

    def get_account(self):
        return dict(self.account)


def make_tracker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tracker = LivePortfolioTracker()
    tracker.proof_file = tmp_path / 'portfolio_growth_proof.json'
    tracker.snapshot_file = tmp_path / 'portfolio_snapshots.json'
    return tracker


def test_unknown_asset_has_no_default_price_and_usd_is_only_a_unit_conversion(
    tmp_path, monkeypatch
):
    tracker = make_tracker(tmp_path, monkeypatch)

    unknown = asyncio.run(tracker.get_asset_price_observation('UNKNOWN', 'kraken'))
    usd = asyncio.run(tracker.get_asset_price_observation('ZUSD', 'kraken'))

    assert unknown.price_usd is None
    assert unknown.truth_status == 'no_data'
    assert unknown.generated_values is False
    assert usd.price_usd == 1.0
    assert usd.truth_status == 'real_derived'
    assert usd.source_id == 'usd_denomination_unit_conversion'
    assert usd.source_timestamp is None
    assert usd.reason == 'USD amount denominated in USD; not a market-price observation'


def test_kraken_valuation_uses_provider_quote_with_provenance(tmp_path, monkeypatch):
    tracker = make_tracker(tmp_path, monkeypatch)
    provider_timestamp = time.time()
    kraken = KrakenReceipt(
        {'ZUSD': 25.0, 'XXBT': 2.0},
        {'BTC/USD': {'price': 100.0, 'timestamp': provider_timestamp}},
    )
    tracker.exchanges = {'kraken': kraken}

    snapshot = asyncio.run(tracker.get_full_portfolio_snapshot())

    assert snapshot.valuation_status == 'complete'
    assert snapshot.truth_status == 'real_derived'
    assert snapshot.generated_values is False
    assert snapshot.proof_eligible is True
    assert snapshot.total_usd_value == pytest.approx(225.0)
    assert snapshot.pnl_usd is None
    assert kraken.ticker_calls == ['BTC/USD']
    holdings = {holding.asset: holding for holding in snapshot.exchanges[0].holdings}
    assert holdings['ZUSD'].valuation_method == 'usd_unit_conversion'
    assert holdings['ZUSD'].current_price == 1.0
    assert holdings['XXBT'].current_price == 100.0
    assert holdings['XXBT'].source_id == 'kraken.get_ticker:BTC/USD'
    assert holdings['XXBT'].source_timestamp == pytest.approx(provider_timestamp)
    assert 'kraken.get_account_balance' in snapshot.source_ids
    assert 'kraken.get_ticker:BTC/USD' in snapshot.source_ids


def test_unpriced_holding_invalidates_total_and_cannot_write_growth_proof(
    tmp_path, monkeypatch
):
    tracker = make_tracker(tmp_path, monkeypatch)
    tracker.exchanges = {
        'kraken': KrakenReceipt(
            {'USD': 10.0, 'DOGE': 2.0},
            {'DOGE/USD': {'price': 0.0, 'timestamp': time.time()}},
        )
    }

    snapshot = asyncio.run(tracker.get_full_portfolio_snapshot())

    assert snapshot.valuation_status == 'incomplete'
    assert snapshot.truth_status == 'no_data'
    assert snapshot.total_usd_value is None
    assert snapshot.pnl_usd is None
    assert snapshot.growth_pct is None
    assert snapshot.proof_eligible is False
    assert snapshot.incomplete_exchanges == ['kraken']
    assert snapshot.exchanges[0].unpriced_assets == ['DOGE']
    assert tracker.update_growth_proof(snapshot) is False
    assert tracker.growth_proof.start_value == 0.0
    assert not tracker.proof_file.exists()
    assert not tracker.snapshot_file.exists()


def test_stale_provider_quote_invalidates_portfolio(tmp_path, monkeypatch):
    tracker = make_tracker(tmp_path, monkeypatch)
    tracker.max_data_age_seconds = 60.0
    tracker.exchanges = {
        'kraken': KrakenReceipt(
            {'BTC': 1.0},
            {'BTC/USD': {'price': 100.0, 'timestamp': time.time() - 120.0}},
        )
    }

    snapshot = asyncio.run(tracker.get_full_portfolio_snapshot())

    assert snapshot.valuation_status == 'incomplete'
    assert snapshot.total_usd_value is None
    holding = snapshot.exchanges[0].holdings[0]
    assert holding.current_price is None
    assert holding.truth_status == 'no_data'
    assert holding.reason == 'provider ticker is stale or future-dated'


def test_alpaca_equity_is_not_added_to_cash(tmp_path, monkeypatch):
    tracker = make_tracker(tmp_path, monkeypatch)
    tracker.exchanges = {
        'alpaca': AlpacaAccountReceipt({'equity': '150.00', 'cash': '50.00'})
    }

    snapshot = asyncio.run(tracker.get_full_portfolio_snapshot())

    assert snapshot.valuation_status == 'complete'
    assert snapshot.total_usd_value == pytest.approx(150.0)
    exchange = snapshot.exchanges[0]
    assert exchange.total_usd_value == pytest.approx(150.0)
    assert exchange.cash_usd == pytest.approx(50.0)
    assert exchange.holdings == []
    assert exchange.source_id == 'alpaca.get_account:equity'


def test_legacy_unproven_growth_file_is_not_loaded(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'portfolio_growth_proof.json').write_text(
        json.dumps({'start_time': 1.0, 'start_value': 999.0}),
        encoding='utf-8',
    )

    tracker = LivePortfolioTracker()

    assert tracker.growth_proof.start_value == 0.0
    assert tracker.growth_proof.truth_status == 'no_data'


def test_complete_snapshot_writes_provenance_bound_proof(tmp_path, monkeypatch):
    tracker = make_tracker(tmp_path, monkeypatch)
    tracker.snapshot_file.write_text(
        json.dumps([{'total_usd_value': 999999.0, 'growth_pct': 1000.0}]),
        encoding='utf-8',
    )
    tracker.exchanges = {
        'alpaca': AlpacaAccountReceipt({'equity': '150.00', 'cash': '50.00'})
    }
    snapshot = asyncio.run(tracker.get_full_portfolio_snapshot())

    assert tracker.update_growth_proof(snapshot) is True

    proof = json.loads(tracker.proof_file.read_text(encoding='utf-8'))
    history = json.loads(tracker.snapshot_file.read_text(encoding='utf-8'))
    assert proof['schema_version'] == 2
    assert proof['valuation_status'] == 'complete'
    assert proof['truth_status'] == 'real_derived'
    assert proof['generated_values'] is False
    assert proof['start_value'] == pytest.approx(150.0)
    assert proof['total_pnl'] == pytest.approx(0.0)
    assert proof['source_ids'] == ['alpaca.get_account:equity']
    assert len(history) == 1
    assert history[0]['schema_version'] == 2
    assert history[0]['proof_eligible'] is True
    assert history[0]['generated_values'] is False


def test_growth_session_refuses_incomplete_start_without_fallback(tmp_path):
    class IncompleteTracker:
        async def get_full_portfolio_snapshot(self):
            class Snapshot:
                valuation_status = 'incomplete'
                truth_status = 'no_data'
                generated_values = False
                total_usd_value = None
                reason = 'provider balance unavailable'

            return Snapshot()

    trader = LivePortfolioGrowthTrader.__new__(LivePortfolioGrowthTrader)
    trader.portfolio_tracker = IncompleteTracker()
    trader.session = None
    trader.session_file = tmp_path / 'live_growth_session.json'

    started = asyncio.run(trader.start_new_session())

    assert started is False
    assert trader.session is None
    assert not trader.session_file.exists()
