from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import time

import pytest

from aureon.queen import queen_quantum_frog as queen_module


@pytest.fixture
def cycle():
    instance = queen_module.OrcaKillCycle.__new__(queen_module.OrcaKillCycle)
    instance.clients = {}
    instance.energy_last_totals = {}
    for attribute in (
        "elephant",
        "hft_engine",
        "historical_hunter",
        "hnc_surge_detector",
        "immune_system",
        "inception_engine",
        "luck_mapper",
        "moby_dick",
        "quantum_mirror",
        "russian_doll",
        "stargate",
        "stargate_grid",
    ):
        setattr(instance, attribute, None)
    return instance


def test_live_price_collection_returns_no_data_instead_of_market_fallbacks(
    cycle, monkeypatch
):
    monkeypatch.setattr(queen_module, "UNIFIED_CACHE_AVAILABLE", False)
    monkeypatch.setattr(queen_module, "get_all_prices", None)

    prices = cycle._get_live_crypto_prices()

    assert prices == {}
    assert cycle.last_live_price_coverage["truth_status"] == "no_data"
    assert cycle.last_live_price_coverage["decision_status"] == "blocked"
    assert cycle.last_live_price_coverage["generated_values"] is False
    assert "BTCUSD" in cycle.last_live_price_coverage["missing_pairs"]


def test_test_mode_environment_never_invents_cash(cycle, monkeypatch):
    monkeypatch.setenv("AUREON_TEST_MODE", "true")
    monkeypatch.setattr(queen_module, "UNIFIED_CACHE_AVAILABLE", False)
    cycle.clients = {
        "alpaca": SimpleNamespace(api_key=None, secret_key=None),
    }

    cash = cycle.get_available_cash()

    assert cash == {"alpaca": 0.0}
    assert cycle.last_cash_status["alpaca"] == "no_keys"


def test_position_without_fresh_price_is_explicitly_blocked(cycle, monkeypatch):
    class Kraken:
        def get_balance(self):
            return {"ETH": "0.25"}

    monkeypatch.setattr(queen_module, "UNIFIED_CACHE_AVAILABLE", False)
    cycle.clients = {"kraken": Kraken()}

    positions = cycle.get_all_positions()

    assert positions["kraken"] == [
        {
            "symbol": "ETH",
            "qty": 0.25,
            "market_value": None,
            "entry_price": None,
            "current_price": None,
            "unrealized_pl": None,
            "pnl_pct": None,
            "can_sell": False,
            "truth_status": "no_data",
            "decision_status": "blocked",
            "reason": "NO_FRESH_PRICE",
            "generated_values": False,
        }
    ]
    assert cycle.last_position_valuation_coverage["truth_status"] == "incomplete"
    assert cycle.last_position_valuation_coverage["decision_status"] == "blocked"


def test_incomplete_alpaca_position_receipt_does_not_invent_zero_values(
    cycle, monkeypatch
):
    class Alpaca:
        def get_positions(self):
            return [{"symbol": "BTCUSD", "qty": "0.01"}]

    monkeypatch.setattr(queen_module, "UNIFIED_CACHE_AVAILABLE", False)
    cycle.clients = {"alpaca": Alpaca()}

    position = cycle.get_all_positions()["alpaca"][0]

    assert position["market_value"] is None
    assert position["current_price"] is None
    assert position["unrealized_pl"] is None
    assert position["pnl_pct"] is None
    assert position["truth_status"] == "no_data"
    assert position["decision_status"] == "blocked"
    assert position["can_sell"] is False


def test_position_valuation_uses_only_observed_cache_price(cycle, monkeypatch):
    class Binance:
        def get_balance(self):
            return {"ETH": "0.25"}

        def get_ticker_price(self, _pair):
            return None

    monkeypatch.setattr(queen_module, "UNIFIED_CACHE_AVAILABLE", True)
    monkeypatch.setattr(queen_module, "get_all_prices", lambda max_age: {})
    monkeypatch.setattr(
        queen_module,
        "get_cached_price",
        lambda asset, max_age: 2000.0 if asset == "ETH" else None,
    )
    cycle.clients = {"binance": Binance()}

    positions = cycle.get_all_positions()

    position = positions["binance"][0]
    assert position["current_price"] == 2000.0
    assert position["market_value"] == 500.0
    assert position["truth_status"] == "real_derived"
    assert position["generated_values"] is False


def test_market_data_without_provider_is_no_data(cycle):
    result = cycle._get_real_market_data("BTC/USD", {"BTC/USD": 99999.0})

    assert result["price"] is None
    assert result["volume"] is None
    assert result["truth_status"] == "no_data"
    assert result["decision_status"] == "blocked"
    assert result["reason"] == "MARKET_PROVIDER_UNAVAILABLE"
    assert result["generated_values"] is False


def test_fresh_complete_bars_produce_real_derived_market_data(cycle):
    now = datetime.now(timezone.utc)

    class Alpaca:
        def get_crypto_bars(self, symbols, timeframe, limit):
            assert symbols == ["BTC/USD"]
            assert timeframe == "1Min"
            assert limit == 60
            return {
                "bars": {
                    "BTC/USD": [
                        {"c": 100.0, "v": 10.0, "t": (now - timedelta(minutes=1)).isoformat()},
                        {"c": 102.0, "v": 20.0, "t": now.isoformat()},
                    ]
                }
            }

    cycle.clients = {"alpaca": Alpaca()}

    result = cycle._get_real_market_data("BTC/USD", {})

    assert result["price"] == 102.0
    assert result["change_pct"] == pytest.approx(2.0)
    assert result["volume"] == 30.0
    assert result["momentum"] == pytest.approx(0.7)
    assert result["truth_status"] == "real_derived"
    assert result["decision_status"] == "ready"
    assert result["sample_count"] == 2
    assert result["generated_values"] is False


def test_stale_bars_block_quantum_market_input(cycle):
    stale = datetime.now(timezone.utc) - timedelta(hours=1)

    class Alpaca:
        def get_crypto_bars(self, _symbols, timeframe, limit):
            return {
                "bars": {
                    "BTC/USD": [
                        {"c": 100.0, "v": 10.0, "t": (stale - timedelta(minutes=1)).isoformat()},
                        {"c": 101.0, "v": 20.0, "t": stale.isoformat()},
                    ]
                }
            }

    cycle.clients = {"alpaca": Alpaca()}

    result = cycle._get_real_market_data("BTC/USD", {})

    assert result["truth_status"] == "no_data"
    assert result["decision_status"] == "blocked"
    assert result["reason"] == "STALE_OR_FUTURE_MARKET_DATA"
    assert result["price"] is None


def test_quantum_score_blocks_when_market_or_component_evidence_is_missing(cycle):
    incomplete = cycle.get_quantum_score(
        "BTC/USD", None, None, None, None, source_timestamp=None
    )
    no_components = cycle.get_quantum_score(
        "BTC/USD", 100.0, 1.0, 20.0, 0.6, source_timestamp=time.time()
    )
    stale = cycle.get_quantum_score(
        "BTC/USD", 100.0, 1.0, 20.0, 0.6, received_at=time.time() - 3600
    )
    receipt_clock_only = cycle.get_quantum_score(
        "BTC/USD", 100.0, 1.0, 20.0, 0.6, received_at=time.time()
    )

    assert incomplete["reason"] == "INCOMPLETE_MARKET_INPUT"
    assert incomplete["quantum_boost"] is None
    assert no_components["reason"] == "NO_QUANTUM_COMPONENT_OBSERVATION"
    assert no_components["decision_status"] == "blocked"
    assert no_components["quantum_boost"] is None
    assert stale["reason"] == "MISSING_OR_STALE_MARKET_TIMESTAMP"
    assert stale["decision_status"] == "blocked"
    assert receipt_clock_only["reason"] == "MISSING_OR_STALE_MARKET_TIMESTAMP"
    assert receipt_clock_only["decision_status"] == "blocked"


def test_quantum_score_runs_existing_math_with_observed_component(cycle):
    class LuckReading:
        luck_field = 0.75
        luck_state = SimpleNamespace(value="FAVORABLE")
        action_bias = "BUY"

    cycle.luck_mapper = SimpleNamespace(read_field=lambda **_kwargs: LuckReading())

    result = cycle.get_quantum_score(
        "BTC/USD", 100.0, 1.0, 20.0, 0.6, source_timestamp=time.time()
    )

    assert result["truth_status"] == "real_derived"
    assert result["decision_status"] == "ready"
    assert result["luck_field"] == 0.75
    assert result["quantum_boost"] == pytest.approx(1.15)
    assert result["generated_values"] is False


def test_energy_snapshot_blocks_incomplete_asset_valuation(cycle, monkeypatch):
    class Binance:
        def get_balance(self):
            return {"USDT": 25.0, "BTC": 0.01}

    cycle.clients = {"binance": Binance()}
    monkeypatch.setattr(cycle, "_get_live_crypto_prices", lambda: {})

    snapshot = cycle._get_energy_snapshot()

    assert snapshot["exchanges"]["binance"]["truth_status"] == "incomplete"
    assert snapshot["exchanges"]["binance"]["decision_status"] == "blocked"
    assert snapshot["exchanges"]["binance"]["total"] is None
    assert snapshot["exchanges"]["binance"]["observed_total_usd"] == 25.0
    assert "BTCUSDT" in snapshot["exchanges"]["binance"]["missing_prices"]
    assert snapshot["total"]["total"] is None


def test_verified_market_receipt_keeps_provider_and_receipt_clocks_distinct():
    provider_time = time.time() - 2.0
    received_at = time.time()

    receipt = queen_module._verified_market_receipt(
        symbol="BTCUSDT",
        source_id="binance:/api/v3/ticker/24hr",
        source_timestamp=provider_time * 1000,
        received_at=received_at,
        price="100.0",
        bid="99.9",
        ask="100.1",
        change_pct="1.25",
        volume="2500",
        required_fields=("price", "bid", "ask", "change_pct", "volume"),
    )

    assert receipt["decision_status"] == "ready"
    assert receipt["source_timestamp"] == pytest.approx(provider_time)
    assert receipt["received_at"] == received_at
    assert receipt["source_timestamp"] != receipt["received_at"]
    assert receipt["generated_values"] is False


@pytest.mark.parametrize(
    "overrides, reason",
    [
        ({"source_timestamp": None}, "MISSING_PROVIDER_TIMESTAMP"),
        (
            {"source_timestamp": lambda: time.time() - 3600},
            "STALE_OR_FUTURE_PROVIDER_OBSERVATION",
        ),
        ({"price": None}, "MISSING_OR_MALFORMED_PROVIDER_FIELDS:price"),
        ({"bid": 101.0, "ask": 100.0}, "CROSSED_PROVIDER_BOOK"),
    ],
)
def test_verified_market_receipt_blocks_incomplete_or_stale_inputs(overrides, reason):
    values = {
        "symbol": "BTCUSDT",
        "source_id": "provider:ticker",
        "source_timestamp": time.time(),
        "received_at": time.time(),
        "price": 100.0,
        "bid": 99.0,
        "ask": 101.0,
        "change_pct": 1.0,
        "volume": 10.0,
        "required_fields": ("price", "bid", "ask", "change_pct", "volume"),
    }
    values.update(overrides)
    if callable(values["source_timestamp"]):
        values["source_timestamp"] = values["source_timestamp"]()

    receipt = queen_module._verified_market_receipt(**values)

    assert receipt["truth_status"] == "no_data"
    assert receipt["decision_status"] == "blocked"
    assert receipt["action_eligible"] is False
    assert receipt["eligible_for_learning"] is False
    assert receipt["reason"] == reason
    assert receipt["price"] is None


def test_binance_ticker_requires_full_timestamped_book(cycle):
    class CompleteClient:
        def get_24h_ticker(self, symbol):
            return {
                "symbol": symbol,
                "lastPrice": "100",
                "bidPrice": "99",
                "askPrice": "101",
                "priceChangePercent": "1.5",
                "quoteVolume": "1200",
                "closeTime": int(time.time() * 1000),
            }

    class PriceOnlyClient:
        get_ticker_price_called = False

        def get_ticker_price(self, _symbol):
            self.get_ticker_price_called = True
            return {"price": "100"}

    complete = cycle._get_binance_ticker(CompleteClient(), "BTC/USDT")
    price_only_client = PriceOnlyClient()
    blocked = cycle._get_binance_ticker(price_only_client, "BTC/USDT")

    assert complete["decision_status"] == "ready"
    assert complete["bid"] == 99.0
    assert complete["ask"] == 101.0
    assert complete["source_timestamp"] is not None
    assert blocked["decision_status"] == "blocked"
    assert blocked["reason"] == "NO_FRESH_COMPLETE_BINANCE_BOOK"
    assert price_only_client.get_ticker_price_called is False


def test_kraken_smart_ticker_joins_provider_clock_to_real_book(monkeypatch):
    monkeypatch.setattr(queen_module, "UNIFIED_CACHE_AVAILABLE", False)
    monkeypatch.setattr(queen_module, "kraken_rate_limit_check", lambda: True)
    monkeypatch.setattr(queen_module, "kraken_rate_limit_record", lambda: None)

    class Kraken:
        def get_24h_ticker(self, symbol):
            return {
                "symbol": symbol,
                "price": 100.0,
                "priceChangePercent": 1.0,
                "quoteVolume": 500.0,
                "source_id": "kraken:/0/public/Ticker+/0/public/Time",
                "source_timestamp": time.time() - 1.0,
                "received_at": time.time(),
                "truth_status": "real_derived",
                "generated_values": False,
            }

        def get_ticker(self, _symbol):
            return {"price": 100.0, "bid": 99.0, "ask": 101.0}

    receipt = queen_module.smart_get_ticker(Kraken(), "BTCUSD", exchange="kraken")

    assert receipt["decision_status"] == "ready"
    assert receipt["bid"] == 99.0
    assert receipt["ask"] == 101.0
    assert receipt["source_id"].startswith("kraken:")


def test_orderbook_requires_two_fresh_provider_sides():
    fresh = queen_module._verified_orderbook_receipt(
        {
            "bids": [{"p": "99"}],
            "asks": [{"p": "101"}],
            "t": datetime.now(timezone.utc).isoformat(),
        },
        symbol="BTC/USD",
        source_id="alpaca:/v1beta3/crypto/us/latest/orderbooks",
    )
    stale = queen_module._verified_orderbook_receipt(
        {
            "bids": [{"p": "99"}],
            "asks": [{"p": "101"}],
            "t": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        },
        symbol="BTC/USD",
        source_id="alpaca:/v1beta3/crypto/us/latest/orderbooks",
    )
    one_sided = queen_module._verified_orderbook_receipt(
        {
            "bids": [{"p": "99"}],
            "asks": [],
            "t": datetime.now(timezone.utc).isoformat(),
        },
        symbol="BTC/USD",
        source_id="alpaca:/v1beta3/crypto/us/latest/orderbooks",
    )

    assert fresh["decision_status"] == "ready"
    assert fresh["bid"] == 99.0
    assert fresh["ask"] == 101.0
    assert stale["decision_status"] == "blocked"
    assert stale["reason"] == "STALE_OR_FUTURE_PROVIDER_OBSERVATION"
    assert one_sided["decision_status"] == "blocked"
    assert one_sided["reason"] == "ORDERBOOK_SIDES_INCOMPLETE"


def test_cached_book_is_valuation_only(monkeypatch):
    monkeypatch.setattr(queen_module, "UNIFIED_CACHE_AVAILABLE", True)
    monkeypatch.setattr(
        queen_module,
        "get_ticker",
        lambda _symbol, max_age: SimpleNamespace(
            source="kraken_rest",
            timestamp=time.time(),
            price=100.0,
            bid=99.0,
            ask=101.0,
            change_24h=1.0,
            volume_24h=1000.0,
        ),
    )

    receipt = queen_module.get_cached_ticker_dict("BTCUSD", max_age=30.0)

    assert receipt["decision_status"] == "ready"
    assert receipt["action_eligible"] is False
    assert receipt["eligible_for_learning"] is False
    assert receipt["reason"] == "CACHE_BOOK_FIELD_PROVENANCE_INCOMPLETE"


def test_binance_scan_uses_close_time_and_rejects_stale_payload(cycle):
    class Response:
        status_code = 200

        def __init__(self, close_time):
            self.close_time = close_time

        def json(self):
            return [
                {
                    "symbol": "BTCUSDT",
                    "lastPrice": "100",
                    "bidPrice": "99",
                    "askPrice": "101",
                    "priceChangePercent": "2",
                    "quoteVolume": "1000",
                    "closeTime": self.close_time,
                }
            ]

    class Session:
        def __init__(self, close_time):
            self.close_time = close_time

        def get(self, *_args, **_kwargs):
            return Response(self.close_time)

    class Binance:
        base = "https://provider.invalid"
        uk_mode = False
        api_key = None
        api_secret = None

        def __init__(self, close_time):
            self.session = Session(close_time)

        def is_uk_restricted_symbol(self, _symbol):
            return False

    cycle.fee_rates = {"binance": 0.001}
    cycle.clients = {"binance": Binance(int(time.time() * 1000))}
    fresh = cycle._scan_binance_market(0.25, 0)

    cycle.clients = {"binance": Binance(int((time.time() - 3600) * 1000))}
    stale = cycle._scan_binance_market(0.25, 0)

    assert len(fresh) == 1
    assert fresh[0].truth_status == "real_derived"
    assert fresh[0].decision_status == "ready"
    assert fresh[0].source_id == "binance:/api/v3/ticker/24hr"
    assert fresh[0].source_timestamp != fresh[0].received_at
    assert stale == []


def test_capital_scan_blocks_when_provider_has_no_observed_volume(cycle):
    class Capital:
        enabled = True

        def get_tickers_for_symbols(self, _symbols, max_workers):
            return {
                "US500": {
                    "price": 5000.0,
                    "bid": 4999.0,
                    "ask": 5001.0,
                    "change_pct": 1.0,
                    "source_id": "capital_market:US500",
                    "source_timestamp": time.time() - 1.0,
                    "received_at": time.time(),
                    "truth_status": "real_derived",
                    "action_eligible": True,
                    "generated_values": False,
                }
            }

    cycle.fee_rates = {"capital": 0.0008}
    cycle._ensure_capital_client = lambda: Capital()
    cycle.last_market_scan_rejections = []

    opportunities = cycle._scan_capital_market(0.25, 0)

    assert opportunities == []
    assert cycle.last_market_scan_rejections[0]["decision_status"] == "blocked"
    assert "volume" in cycle.last_market_scan_rejections[0]["reason"]


def test_kraken_cache_never_relabels_binance_source(cycle, monkeypatch):
    cycle.fee_rates = {"kraken": 0.0026}

    class Kraken:
        def get_24h_tickers(self):
            return []

    cycle.clients = {"kraken": Kraken()}
    monkeypatch.setattr(queen_module, "UNIFIED_CACHE_AVAILABLE", True)
    monkeypatch.setattr(queen_module, "get_all_prices", lambda max_age: {"BTC": 100.0})
    monkeypatch.setattr(
        queen_module,
        "get_ticker",
        lambda _symbol, max_age: SimpleNamespace(
            source="binance_ws",
            timestamp=time.time(),
            price=100.0,
            bid=99.0,
            ask=101.0,
            change_24h=2.0,
            volume_24h=1000.0,
        ),
    )

    assert cycle._scan_kraken_market(0.25, 0) == []


def test_pack_hunt_blocks_unproven_opportunity_before_any_order(cycle, monkeypatch):
    orders = []
    cycle.get_available_cash = lambda: {"alpaca": 100.0}
    cycle.primary_exchange = "alpaca"
    cycle.clients = {
        "alpaca": SimpleNamespace(
            place_market_order=lambda **kwargs: orders.append(kwargs)
        )
    }
    unproven = queen_module.MarketOpportunity(
        symbol="BTC/USD",
        exchange="alpaca",
        price=100.0,
        change_pct=2.0,
        volume=1000.0,
        momentum_score=2.0,
        fee_rate=0.0025,
    )

    result = cycle.pack_hunt(
        opportunities=[unproven],
        num_positions=1,
        amount_per_position=10.0,
    )

    assert result == []
    assert orders == []
