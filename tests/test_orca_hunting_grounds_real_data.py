import time
from datetime import datetime, timezone

import pytest

from aureon.bots import orca_hunting_grounds as orca


class StubAlpaca:
    def __init__(self, observation):
        self.observation = observation

    def get_ticker(self, symbol):
        if symbol != 'BTC/USD':
            return None
        return dict(self.observation)


class StubKraken:
    def __init__(self, observation):
        self.observation = observation

    def get_24h_ticker(self, symbol):
        if symbol != 'XBTUSD':
            return None
        return dict(self.observation)


class RaisingKraken:
    def get_24h_ticker(self, symbol):
        raise RuntimeError('offline provider failure')


def _hunter(*, alpaca=None, kraken=None):
    hunter = orca.OrcaHuntingGrounds.__new__(orca.OrcaHuntingGrounds)
    hunter.alpaca = alpaca
    hunter.kraken = kraken
    hunter.binance = None
    hunter.last_no_data = []
    return hunter


def _receipt(**overrides):
    source_timestamp = datetime.now(timezone.utc).isoformat()
    receipt = {
        'price': 100.0,
        'bid': 99.0,
        'ask': 101.0,
        'volatility_1h': 0.05,
        'liquidity_score': 0.8,
        'fee_pct': 0.001,
        'source_id': 'alpaca:latest_quote+observed_1h_metrics',
        'source_timestamp': source_timestamp,
        'market_receipt_id': 'market-receipt-1',
        'fee_source_id': 'alpaca:account_fee_schedule',
        'fee_source_timestamp': source_timestamp,
        'fee_receipt_id': 'fee-receipt-1',
        'truth_status': 'real_derived',
        'generated_values': False,
        'fee_generated_values': False,
    }
    receipt.update(overrides)
    return receipt


def _assert_no_data(record):
    assert record['truth_status'] == 'no_data'
    assert record['provider_observation'] is False
    assert record['generated_values'] is False
    assert record['operational_eligible'] is False
    assert record['action_eligible'] is False
    assert record['actionable'] is False
    assert record['accounting_eligible'] is False
    assert record['learning_eligible'] is False
    for forbidden in (
        'price',
        'spread_pct',
        'fee_pct',
        'volatility_1h',
        'liquidity_score',
        'hunt_score',
    ):
        assert forbidden not in record


def test_complete_fresh_provider_and_fee_receipts_preserve_scoring_equations():
    hunter = _hunter(alpaca=StubAlpaca(_receipt()))

    grounds = hunter.scan_alpaca()

    assert len(grounds) == 1
    ground = grounds[0]
    expected_spread = (101.0 - 99.0) / 99.0
    expected_cost = (0.001 * 2) + expected_spread
    assert ground.spread_pct == pytest.approx(expected_spread)
    assert ground.round_trip_cost == pytest.approx(expected_cost)
    assert ground.profit_threshold == pytest.approx(expected_cost * 1.5)
    assert ground.hunt_score == pytest.approx((0.05 - expected_cost) * 0.8 * 100)
    assert ground.source_id == 'alpaca:latest_quote+observed_1h_metrics'
    assert ground.market_receipt_id == 'market-receipt-1'
    assert ground.fee_receipt_id == 'fee-receipt-1'
    assert ground.provider_observation is True
    assert ground.operational_eligible is True
    assert ground.actionable is True
    assert ground.accounting_eligible is False
    assert ground.learning_eligible is True
    assert ground.generated_values is False


def test_raw_ticker_without_complete_provenance_is_no_data():
    raw = {'price': 100.0, 'bid': 99.0, 'ask': 101.0}
    hunter = _hunter(alpaca=StubAlpaca(raw))

    assert hunter.scan_alpaca() == []
    btc_record = next(
        record for record in hunter.last_no_data
        if record['symbol'] == 'BTC/USD'
    )
    _assert_no_data(btc_record)


@pytest.mark.parametrize(
    'field',
    ['source_timestamp', 'fee_source_timestamp'],
)
def test_stale_market_or_fee_receipt_is_no_data(field):
    stale = datetime.fromtimestamp(
        time.time() - orca.EVIDENCE_TTL_SECONDS - 1,
        timezone.utc,
    ).isoformat()
    hunter = _hunter(alpaca=StubAlpaca(_receipt(**{field: stale})))

    assert hunter.scan_alpaca() == []
    btc_record = next(
        record for record in hunter.last_no_data
        if record['symbol'] == 'BTC/USD'
    )
    _assert_no_data(btc_record)


def test_generated_or_malformed_values_are_no_data():
    generated = _hunter(
        alpaca=StubAlpaca(_receipt(generated_values=True)),
    )
    malformed = _hunter(
        alpaca=StubAlpaca(_receipt(volatility_1h='not-a-number')),
    )

    assert generated.scan_alpaca() == []
    assert malformed.scan_alpaca() == []
    _assert_no_data(next(
        record for record in generated.last_no_data
        if record['symbol'] == 'BTC/USD'
    ))
    _assert_no_data(next(
        record for record in malformed.last_no_data
        if record['symbol'] == 'BTC/USD'
    ))


def test_kraken_price_only_receipt_cannot_invent_missing_inputs():
    timestamp = datetime.now(timezone.utc).isoformat()
    price_only = {
        'price': 100.0,
        'source_id': 'kraken:public_ticker',
        'source_timestamp': timestamp,
        'market_receipt_id': 'kraken-market-1',
        'truth_status': 'real_derived',
        'generated_values': False,
    }
    hunter = _hunter(kraken=StubKraken(price_only))

    assert hunter.scan_kraken() == []
    btc_record = next(
        record for record in hunter.last_no_data
        if record['symbol'] == 'BTC/USD'
    )
    _assert_no_data(btc_record)


def test_provider_failure_is_explicit_no_data():
    hunter = _hunter(kraken=RaisingKraken())

    assert hunter.scan_kraken() == []
    assert len(hunter.last_no_data) == 3
    assert all(
        record['reason'] == 'provider_call_or_parse_failed'
        for record in hunter.last_no_data
    )
    for record in hunter.last_no_data:
        _assert_no_data(record)
