from aureon.trading.unified_exchange_client import UnifiedExchangeClient


class TrapKraken:
    def place_market_order(self, *_args, **_kwargs):
        raise AssertionError("order submission must not occur without price evidence")

    def place_margin_order(self, *_args, **_kwargs):
        raise AssertionError("margin submission must not occur without price evidence")


def client_without_provider_price() -> UnifiedExchangeClient:
    client = UnifiedExchangeClient.__new__(UnifiedExchangeClient)
    client.exchange_id = "kraken"
    client.client = TrapKraken()
    client.available = True
    client.dry_run = False
    client.kraken_min_notional = 5.0
    client.get_ticker = lambda _symbol: {
        "status": "no_data",
        "truth_status": "no_data",
        "generated_values": False,
    }
    return client


def test_market_order_preflight_is_numeric_free_without_price_receipt():
    result = client_without_provider_price().place_market_order(
        "BTCUSD",
        "buy",
        quantity=0.01,
    )
    assert result["status"] == "not_submitted"
    assert result["truth_status"] == "no_data"
    assert result["actionable"] is False
    assert result["eligible_for_accounting"] is False
    assert "price" not in result


def test_margin_preflight_is_numeric_free_without_price_receipt():
    result = client_without_provider_price().place_margin_order(
        "BTCUSD",
        "buy",
        quantity=0.01,
        leverage=2,
    )
    assert result["status"] == "not_submitted"
    assert result["truth_status"] == "no_data"
    assert result["eligible_for_learning"] is False
    assert "notional" not in result
