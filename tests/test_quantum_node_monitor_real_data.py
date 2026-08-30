import copy
import inspect

from aureon.monitors import aureon_quantum_node_monitor as monitor_module
from aureon.monitors.aureon_quantum_node_monitor import QuantumNodeMonitor


NOW = 1_800_000_000.0


class InMemoryBinance:
    def __init__(self, account_receipt, ticker_receipt):
        self.account_receipt = account_receipt
        self.ticker_receipt = ticker_receipt
        self.calls = []

    def account(self):
        self.calls.append(("account", None))
        return copy.deepcopy(self.account_receipt)

    def get_24h_ticker(self, symbol):
        self.calls.append(("ticker", symbol))
        return copy.deepcopy(self.ticker_receipt)


def _account_receipt(source_timestamp=NOW - 2.0):
    return {
        "updateTime": int(source_timestamp * 1000),
        "balances": [
            {"asset": "BTC", "free": "1.5", "locked": "0.5"},
            {"asset": "USDT", "free": "25", "locked": "1"},
            {"asset": "USDC", "free": "7", "locked": "0"},
        ],
    }


def _ticker_receipt(source_timestamp=NOW - 1.0):
    return {
        "symbol": "BTCUSDT",
        "priceChange": "10",
        "priceChangePercent": "10",
        "weightedAvgPrice": "105",
        "prevClosePrice": "100",
        "lastPrice": "110",
        "lastQty": "0.5",
        "bidPrice": "109.9",
        "bidQty": "2",
        "askPrice": "110.1",
        "askQty": "3",
        "openPrice": "100",
        "highPrice": "112",
        "lowPrice": "99",
        "volume": "1000",
        "quoteVolume": "105000",
        "openTime": int((source_timestamp - 86_400.0) * 1000),
        "closeTime": int(source_timestamp * 1000),
        "firstId": 1,
        "lastId": 10,
        "count": 10,
    }


def test_monitor_requires_complete_fresh_position_and_market_receipts():
    source = inspect.getsource(monitor_module)
    assert "current_price = entry_price" not in source
    assert "Placeholder" not in source
    assert "aureon_kraken_state.json" not in source

    client = InMemoryBinance(_account_receipt(), _ticker_receipt())
    monitor = QuantumNodeMonitor(
        binance=client,
        clock=lambda: NOW,
        autoload_clients=False,
    )
    network = monitor.scan_network()

    assert client.calls == [("account", None), ("ticker", "BTCUSDT")]
    assert network.data_status == "live"
    assert network.truth_status == "real_derived"
    assert network.generated_values is False
    assert network.action_eligible is False
    assert network.accounting_eligible is False
    assert network.learning_eligible is False
    assert network.total_nodes == 1
    assert network.unclassified_nodes == 1
    assert network.free_energy_by_currency == {"USDT": 25.0, "USDC": 7.0}
    assert network.entangled_energy_by_currency == {"USDT": 220.0}

    node = network.nodes[0]
    assert node.symbol == "BTC/USDT"
    assert node.quote_currency == "USDT"
    assert node.quantity == 2.0
    assert node.current_price == 110.0
    assert node.current_value == 220.0
    assert node.entry_price is None
    assert node.unrealized_profit is None
    assert node.profit_pct is None
    assert node.quantum_state is None
    assert node.entanglement_strength is None
    assert node.generated_values is False
    assert node.action_eligible is False
    assert node.accounting_eligible is False
    assert node.learning_eligible is False
    assert monitor._timestamp_epoch(node.received_at) > node.source_timestamp
    assert node.field_provenance["quantity"]["source_timestamp"] == NOW - 2.0
    assert node.field_provenance["current_price"]["source_timestamp"] == NOW - 1.0

    invalid_cases = []
    missing_position_timestamp = _account_receipt()
    missing_position_timestamp.pop("updateTime")
    invalid_cases.append((missing_position_timestamp, _ticker_receipt()))
    stale_position = _account_receipt(source_timestamp=NOW - 121.0)
    invalid_cases.append((stale_position, _ticker_receipt()))
    laundered_quote_timestamp = _ticker_receipt(source_timestamp=NOW)
    invalid_cases.append((_account_receipt(), laundered_quote_timestamp))
    mismatched_quote = _ticker_receipt()
    mismatched_quote["symbol"] = "ETHUSDT"
    invalid_cases.append((_account_receipt(), mismatched_quote))
    nonfinite_quote = _ticker_receipt()
    nonfinite_quote["lastPrice"] = "nan"
    invalid_cases.append((_account_receipt(), nonfinite_quote))

    for account_receipt, ticker_receipt in invalid_cases:
        invalid_monitor = QuantumNodeMonitor(
            binance=InMemoryBinance(account_receipt, ticker_receipt),
            clock=lambda: NOW,
            autoload_clients=False,
        )
        no_data = invalid_monitor.scan_network()
        assert no_data.data_status == "no_data"
        assert no_data.truth_status == "no_data"
        assert no_data.generated_values is False
        assert no_data.action_eligible is False
        assert no_data.accounting_eligible is False
        assert no_data.learning_eligible is False
        assert no_data.nodes == []
        assert no_data.total_nodes is None
        assert no_data.active_nodes is None
        assert no_data.resonating_nodes is None
        assert no_data.hibernating_nodes is None
        assert no_data.dust_nodes is None
        assert no_data.unclassified_nodes is None
        assert no_data.entangled_energy_by_currency == {}
        assert no_data.free_energy_by_currency == {}
        assert no_data.harvestable_energy_by_currency == {}
        assert no_data.source_receipts
        assert all(receipt["generated_values"] is False for receipt in no_data.source_receipts)
        assert all(receipt["action_eligible"] is False for receipt in no_data.source_receipts)
        assert all(receipt["accounting_eligible"] is False for receipt in no_data.source_receipts)
        assert all(receipt["learning_eligible"] is False for receipt in no_data.source_receipts)
        assert all(receipt["source_timestamp"] is None for receipt in no_data.source_receipts)
        assert all(
            set(receipt).isdisjoint(
                {"price", "quantity", "balance", "value", "profit", "pnl", "volume"}
            )
            for receipt in no_data.source_receipts
        )
