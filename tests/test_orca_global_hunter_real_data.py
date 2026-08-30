from datetime import datetime, timezone
import time

import pytest

from aureon.bots.orca_global_hunter import GlobalOpportunity, OrcaGlobalHunter


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _hunter() -> OrcaGlobalHunter:
    hunter = object.__new__(OrcaGlobalHunter)
    hunter.exchanges = {}
    hunter.universes = {}
    hunter.opportunities = []
    hunter.min_momentum_pct = 0.5
    hunter.total_scanned = 0
    hunter.scan_count = 0
    return hunter


class _Kraken:
    def __init__(self, now: float, *, provider_time: bool = True, include_volume: bool = True):
        self.now = now
        self.provider_time = provider_time
        self.include_volume = include_volume
        self.pairs = {
            "XXBTZUSD": {
                "altname": "XBTUSD",
                "wsname": "XBT/USD",
                "fees": [[0, 0.40], [10_000, 0.35]],
            }
        }

    def _load_asset_pairs(self, force: bool = False):
        assert force is True
        return self.pairs

    def _ticker(self, symbols):
        assert symbols
        ticker = {
            "c": ["110.0", "1"],
            "o": "100.0",
            "b": ["109.0", "1"],
            "a": ["111.0", "1"],
        }
        if self.include_volume:
            ticker["v"] = ["900.0", "1000.0"]
        return {"XXBTZUSD": ticker}

    def _public_get(self, endpoint):
        assert endpoint == "/0/public/Time"
        return {"unixtime": self.now - 1} if self.provider_time else {}


class _Alpaca:
    def __init__(self, now: float, *, include_fees: bool = True, malformed_bar: bool = False):
        self.now = now
        self.include_fees = include_fees
        self.malformed_bar = malformed_bar

    def get_account_activities(self, *, activity_types, after, direction, page_size):
        assert after.endswith("Z")
        assert direction == "desc"
        assert page_size == 100
        event_time = _iso(self.now - 120)
        if activity_types == "FILL":
            return [
                {"symbol": "BTCUSD", "qty": "10", "price": "100", "transaction_time": event_time},
                {"symbol": "AAPL", "qty": "1000", "price": "200", "transaction_time": event_time},
            ]
        if activity_types == "CFEE" and self.include_fees:
            return [{"symbol": "BTCUSD", "qty": "-0.025", "price": "100", "transaction_time": event_time}]
        return []

    def get_latest_crypto_quotes(self, symbols):
        assert symbols == ["BTC/USD"]
        return {
            "BTC/USD": {
                "bp": "109.9",
                "ap": "110.1",
                "t": _iso(self.now - 10),
            }
        }

    def get_crypto_bars(self, symbols, *, timeframe, limit):
        assert symbols == ["BTC/USD"]
        assert timeframe == "1Hour"
        assert limit == 25
        bars = []
        for index in range(24):
            open_price = 100.0 + index * 0.1
            close_price = open_price + 0.05
            bars.append({
                "t": _iso(self.now - (23 - index) * 60 * 60 - 30),
                "o": open_price,
                "h": close_price + 1.0,
                "l": open_price - 1.0,
                "c": close_price,
                "v": 2.0,
            })
        if self.malformed_bar:
            bars[-1].pop("v")
        return {"bars": {"BTC/USD": bars}}


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_kraken_scan_uses_provider_price_volume_fee_spread_and_time():
    now = time.time()
    hunter = _hunter()
    hunter.exchanges = {"kraken": _Kraken(now)}
    hunter.universes = {"kraken": {"XXBTZUSD"}}

    opportunities = hunter.scan_kraken(limit=1)

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.symbol == "XBT/USD"
    assert opportunity.truth_status == "real_derived"
    assert opportunity.generated_values is False
    assert opportunity.eligible_for_external_action is True
    assert opportunity.volume == pytest.approx(110_000.0)
    assert opportunity.fee_pct == pytest.approx(0.004)
    assert opportunity.spread_pct == pytest.approx(2.0 / 110.0)
    assert opportunity.current_price == pytest.approx(110.0)
    assert opportunity.entry_price == pytest.approx(111.0)
    assert opportunity.source_timestamp == pytest.approx(now - 1)
    assert set(opportunity.field_provenance) == {
        "prices", "momentum_pct", "fee_pct", "spread_pct", "volume", "net_edge"
    }
    assert opportunity.is_profitable is True


@pytest.mark.parametrize(
    "client",
    [
        lambda now: _Kraken(now, provider_time=False),
        lambda now: _Kraken(now, include_volume=False),
    ],
)
def test_kraken_scan_fails_closed_on_missing_provider_evidence(client):
    now = time.time()
    hunter = _hunter()
    hunter.exchanges = {"kraken": client(now)}
    hunter.universes = {"kraken": {"XXBTZUSD"}}

    assert hunter.scan_kraken(limit=1) == []


def test_alpaca_scan_derives_every_numeric_from_timestamped_provider_records():
    now = time.time()
    hunter = _hunter()
    hunter.exchanges = {"alpaca": _Alpaca(now)}
    hunter.universes = {"alpaca_crypto": {"BTC/USD"}}

    opportunities = hunter.scan_alpaca_crypto()

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.symbol == "BTC/USD"
    assert opportunity.fee_pct == pytest.approx(0.0025)
    assert opportunity.current_price == pytest.approx(110.0)
    assert opportunity.entry_price == pytest.approx(110.1)
    assert opportunity.volume > 0
    assert opportunity.source_id == "alpaca_crypto_quotes+hour_bars+account_fee_activities"
    assert opportunity.field_provenance["fee_pct"]["source_timestamp"] == pytest.approx(now - 120)
    assert opportunity.is_profitable is True


@pytest.mark.parametrize("kwargs", [{"include_fees": False}, {"malformed_bar": True}])
def test_alpaca_scan_fails_closed_on_missing_or_malformed_evidence(kwargs):
    now = time.time()
    hunter = _hunter()
    hunter.exchanges = {"alpaca": _Alpaca(now, **kwargs)}
    hunter.universes = {"alpaca_crypto": {"BTC/USD"}}

    assert hunter.scan_alpaca_crypto() == []


def test_binance_signal_uses_real_kraken_execution_quote_and_pair_alias(monkeypatch):
    now = time.time()
    payload = [{
        "symbol": "BTCUSDT",
        "lastPrice": "105.0",
        "priceChangePercent": "6.0",
        "quoteVolume": "500000.0",
        "closeTime": int((now - 5) * 1000),
    }]
    monkeypatch.setattr("requests.get", lambda *args, **kwargs: _Response(payload))
    hunter = _hunter()
    hunter.exchanges = {"kraken": _Kraken(now)}
    hunter.universes = {"kraken": {"XXBTZUSD"}}

    opportunities = hunter.scan_binance(limit=10)

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.symbol == "BTC/USD"
    assert opportunity.exchange == "kraken"
    assert opportunity.current_price == pytest.approx(110.0)
    assert opportunity.current_price != 105.0
    assert opportunity.volume == pytest.approx(500_000.0)
    assert opportunity.source_timestamp == pytest.approx(now - 5, abs=0.01)
    assert "binance_public_ticker_24hr" in opportunity.source_id
    assert "kraken_public_ticker" in opportunity.source_id
    assert opportunity.field_provenance["signal_reference_price"]["value"] == 105.0
    assert opportunity.is_profitable is True


def test_binance_signal_without_provider_event_time_emits_no_opportunity(monkeypatch):
    now = time.time()
    payload = [{
        "symbol": "BTCUSDT",
        "lastPrice": "105.0",
        "priceChangePercent": "6.0",
        "quoteVolume": "500000.0",
    }]
    monkeypatch.setattr("requests.get", lambda *args, **kwargs: _Response(payload))
    hunter = _hunter()
    hunter.exchanges = {"kraken": _Kraken(now)}
    hunter.universes = {"kraken": {"XXBTZUSD"}}

    assert hunter.scan_binance(limit=10) == []


def test_stale_opportunity_is_not_returned_as_a_kill():
    now = time.time()
    stale = GlobalOpportunity(
        symbol="BTC/USD",
        exchange="kraken",
        region="GLOBAL",
        direction="buy",
        momentum_pct=5.0,
        confidence=1.0,
        current_price=100.0,
        entry_price=101.0,
        fee_pct=0.004,
        spread_pct=0.001,
        net_edge=0.041,
        source="test_provider",
        reason="provider evidence",
        volume=500_000.0,
        truth_status="real_derived",
        source_id="provider_snapshot",
        source_timestamp=now - 3 * 60 * 60,
        received_at=now - 3 * 60 * 60,
        generated_values=False,
        eligible_for_external_action=True,
        field_provenance={"prices": {"source_id": "provider_snapshot"}},
    )
    hunter = _hunter()
    hunter.opportunities = [stale]

    assert stale.is_profitable is False
    assert hunter.get_best_kill() is None
