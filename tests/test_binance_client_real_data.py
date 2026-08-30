from __future__ import annotations

import json
import time

import pytest

from aureon.exchanges.binance_client import BinanceClient, BinancePoolClient


def _client(monkeypatch: pytest.MonkeyPatch) -> BinanceClient:
    monkeypatch.setenv("BINANCE_DRY_RUN", "true")
    monkeypatch.setenv("BINANCE_UK_MODE", "false")
    calls: list[bool] = []
    monkeypatch.setattr(BinanceClient, "_sync_server_time", lambda self: calls.append(True))
    client = BinanceClient()
    assert calls == []
    return client


def test_constructor_does_not_probe_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    assert client._time_sync_timestamp == 0


_PERMISSION_SECRET = "DO_NOT_RETURN_PERMISSION_SOURCE_SECRET"
_DELETE = object()


def _safe_permission_payloads(now_ms: int) -> dict[str, dict]:
    return {
        "account": {
            "accountType": "SPOT",
            "canTrade": True,
            "permissions": ["TRD_GRP_001", "SPOT"],
            "uid": "private-account-id",
            "secret": _PERMISSION_SECRET,
        },
        "restrictions": {
            "enableReading": True,
            "enableSpotAndMarginTrading": True,
            "ipRestrict": True,
            "enableWithdrawals": False,
            "enableInternalTransfer": False,
            "permitsUniversalTransfer": False,
            "enableMargin": False,
            "enableFutures": False,
            "enableVanillaOptions": False,
            "enablePortfolioMarginTrading": False,
            "ipList": ["192.0.2.10"],
            "secret": _PERMISSION_SECRET,
        },
        "trading_status": {
            "data": {
                "isLocked": False,
                "plannedRecoverTime": 0,
                "secret": _PERMISSION_SECRET,
            },
            "secret": _PERMISSION_SECRET,
        },
        "time": {"serverTime": now_ms, "secret": _PERMISSION_SECRET},
    }


def _permission_client(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[BinanceClient, dict[str, dict], list[tuple[str, str]]]:
    client = _client(monkeypatch)
    client.dry_run = False
    client.use_testnet = False
    client.uk_mode = True
    payloads = _safe_permission_payloads(int((time.time() - 1) * 1000))
    calls: list[tuple[str, str]] = []

    def signed(method: str, path: str, _params: dict) -> dict:
        calls.append((method, path))
        if path == "/api/v3/account":
            return payloads["account"]
        if path == "/sapi/v1/account/apiRestrictions":
            return payloads["restrictions"]
        if path == "/sapi/v1/account/apiTradingStatus":
            return payloads["trading_status"]
        raise AssertionError(f"unexpected signed endpoint: {method} {path}")

    def provider_time() -> dict:
        calls.append(("GET", "/api/v3/time"))
        return payloads["time"]

    client._signed_request = signed
    client.server_time = provider_time
    return client, payloads, calls


def test_account_permission_receipt_is_deterministic_sanitized_and_spot_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, calls = _permission_client(monkeypatch)

    receipt = client.get_account_permission_receipt()
    repeated = client.get_account_permission_receipt()

    assert calls == [
        ("GET", "/api/v3/account"),
        ("GET", "/sapi/v1/account/apiRestrictions"),
        ("GET", "/sapi/v1/account/apiTradingStatus"),
        ("GET", "/api/v3/time"),
    ] * 2
    assert receipt["account_type"] == "SPOT"
    assert receipt["permissions"] == ["SPOT", "TRD_GRP_001"]
    assert receipt["provider_receipt_type"] == (
        "Account+ApiRestrictions+ApiTradingStatus+Time"
    )
    assert receipt["source_id"] == (
        "binance:/api/v3/account"
        "+/sapi/v1/account/apiRestrictions"
        "+/sapi/v1/account/apiTradingStatus"
        "+/api/v3/time"
    )
    assert receipt["truth_status"] == "real_provider"
    assert receipt["data_status"] == "live"
    assert receipt["safe_for_bounded_spot_buy"] is True
    assert receipt["eligible_for_action"] is True
    assert receipt["eligible_for_accounting"] is False
    assert receipt["eligible_for_learning"] is False
    assert receipt["receipt_id"].startswith("binance:account_permission:")
    assert receipt["receipt_id"] == repeated["receipt_id"]
    assert _PERMISSION_SECRET not in json.dumps(receipt)
    assert "uid" not in receipt
    assert "ipList" not in receipt


@pytest.mark.parametrize(
    ("target", "field", "unsafe_value"),
    (
        ("account", "accountType", "MARGIN"),
        ("account", "permissions", ["SPOT", "MARGIN"]),
        ("account", "permissions", ["TRD_GRP_001"]),
        ("account", "permissions", "SPOT"),
        ("account", "canTrade", False),
        ("account", "canTrade", "true"),
        ("restrictions", "enableReading", _DELETE),
        ("restrictions", "enableReading", 1),
        ("restrictions", "enableSpotAndMarginTrading", False),
        ("restrictions", "ipRestrict", False),
        ("restrictions", "enableWithdrawals", True),
        ("restrictions", "enableWithdrawals", 0),
        ("restrictions", "enableInternalTransfer", True),
        ("restrictions", "permitsUniversalTransfer", True),
        ("restrictions", "enableMargin", True),
        ("restrictions", "enableFutures", True),
        ("restrictions", "enableVanillaOptions", True),
        ("restrictions", "enablePortfolioMarginTrading", True),
        ("restrictions", "enablePortfolioMarginTrading", _DELETE),
        ("trading_status", "isLocked", True),
        ("trading_status", "isLocked", 0),
        ("time", "serverTime", 1),
        ("client", "dry_run", True),
        ("client", "use_testnet", True),
        ("client", "uk_mode", False),
    ),
    ids=(
        "wrong-account-type",
        "margin-permission",
        "spot-permission-missing",
        "permissions-wrong-type",
        "cannot-trade",
        "can-trade-wrong-type",
        "reading-missing",
        "reading-integer-one",
        "spot-trading-disabled",
        "ip-restriction-disabled",
        "withdrawals-enabled",
        "withdrawals-integer-zero",
        "internal-transfer-enabled",
        "universal-transfer-enabled",
        "margin-enabled",
        "futures-enabled",
        "options-enabled",
        "portfolio-margin-enabled",
        "portfolio-margin-missing",
        "trading-locked",
        "locked-integer-zero",
        "stale-server-time",
        "dry-run-client",
        "testnet-client",
        "uk-guard-disabled",
    ),
)
def test_account_permission_receipt_fails_closed_for_each_unsafe_capability(
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    field: str,
    unsafe_value: object,
) -> None:
    client, payloads, _ = _permission_client(monkeypatch)
    if target == "client":
        setattr(client, field, unsafe_value)
    else:
        container = (
            payloads["trading_status"]["data"]
            if target == "trading_status"
            else payloads[target]
        )
        if unsafe_value is _DELETE:
            container.pop(field)
        else:
            container[field] = unsafe_value

    receipt = client.get_account_permission_receipt()

    assert receipt["data_status"] == "no_data"
    assert receipt["truth_status"] == "no_data"
    assert receipt["source_timestamp"] is None
    assert receipt["receipt_id"] is None
    assert receipt["safe_for_bounded_spot_buy"] is False
    assert receipt["eligible_for_action"] is False
    assert receipt["eligible_for_accounting"] is False
    assert receipt["eligible_for_learning"] is False
    assert _PERMISSION_SECRET not in json.dumps(receipt)


def test_balance_receipt_requires_fresh_provider_server_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    server_time = int((time.time() - 1) * 1000)
    account_update_time = server_time - 500
    client.account = lambda: {
        "updateTime": account_update_time,
        "balances": [{"asset": "ETH", "free": "1.25", "locked": "0.50"}],
    }
    client.server_time = lambda: {"serverTime": server_time}

    receipt = client.get_asset_balance("eth")
    repeated = client.get_asset_balance("ETH")

    assert receipt is not None
    assert repeated is not None
    assert receipt["free"] == pytest.approx(1.25)
    assert receipt["locked"] == pytest.approx(0.5)
    assert receipt["account_update_time"] == account_update_time
    assert receipt["server_time"] == server_time
    assert receipt["source_timestamp"] == pytest.approx(server_time / 1000)
    assert receipt["source_id"] == (
        "binance:/api/v3/account+/api/v3/time"
    )
    assert receipt["provider_receipt_type"] == "Account+Time"
    assert receipt["truth_status"] == "real_provider"
    assert receipt["eligible_for_action"] is True
    assert receipt["generated_values"] is False
    assert receipt["receipt_id"].startswith("binance:account:ETH:")
    assert receipt["receipt_id"] == repeated["receipt_id"]
    assert client.get_free_balance("ETH") == pytest.approx(1.25)


def test_stale_account_update_time_with_fresh_server_clock_is_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    server_time = int((time.time() - 1) * 1000)
    client.account = lambda: {
        "updateTime": 1,
        "balances": [{"asset": "ETH", "free": "1.25", "locked": "0"}],
    }
    client.server_time = lambda: {"serverTime": server_time}

    receipt = client.get_asset_balance("ETH")

    assert receipt is not None
    assert receipt["truth_status"] == "real_provider"
    assert receipt["data_status"] == "live"
    assert receipt["eligible_for_action"] is True
    assert receipt["account_update_time"] == 1
    assert receipt["source_timestamp"] == pytest.approx(server_time / 1000)


@pytest.mark.parametrize(
    "provider_clock",
    [{}, {"serverTime": None}, {"serverTime": 1}],
)
def test_missing_or_stale_server_clock_is_no_data(
    monkeypatch: pytest.MonkeyPatch,
    provider_clock: dict[str, int | None],
) -> None:
    client = _client(monkeypatch)
    account_update_time = int(time.time() * 1000)
    client.account = lambda: {
        "updateTime": account_update_time,
        "balances": [{"asset": "ETH", "free": "1.25", "locked": "0"}],
    }
    client.server_time = lambda: provider_clock

    receipt = client.get_asset_balance("ETH")

    assert receipt is not None
    assert receipt["truth_status"] == "no_data"
    assert receipt["data_status"] == "no_data"
    assert receipt["source_timestamp"] is None
    assert receipt["eligible_for_action"] is False
    assert receipt["receipt_id"] is None
    assert receipt["account_update_time"] == account_update_time
    with pytest.raises(RuntimeError, match="NO_DATA"):
        client.get_free_balance("ETH")


def test_missing_or_malformed_asset_is_not_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    server_time = int(time.time() * 1000)
    client.account = lambda: {
        "updateTime": server_time,
        "balances": [{"asset": "ETH", "free": "not-a-number", "locked": "0"}],
    }
    client.server_time = lambda: {"serverTime": server_time}

    assert client.get_asset_balance("ETH") is None
    with pytest.raises(RuntimeError, match="NO_DATA"):
        client.get_free_balance("ETH")
    with pytest.raises(RuntimeError, match="NO_DATA"):
        client.get_free_balance("BTC")


def test_observed_zero_balance_remains_real_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    server_time = int(time.time() * 1000)
    client.account = lambda: {
        "updateTime": server_time,
        "balances": [{"asset": "ETH", "free": "0", "locked": "0"}],
    }
    client.server_time = lambda: {"serverTime": server_time}

    receipt = client.get_asset_balance("ETH")

    assert receipt is not None
    assert receipt["free"] == 0.0
    assert receipt["eligible_for_action"] is True
    assert client.get_free_balance("ETH") == 0.0


def _full_order(
    *,
    order_id: int = 42,
    symbol: str = "ETHUSDT",
    side: str = "SELL",
    executed_qty: str = "2",
    filled_notional: str = "200",
) -> dict:
    now_ms = int(time.time() * 1000)
    return {
        "symbol": symbol,
        "side": side,
        "orderId": order_id,
        "status": "FILLED",
        "transactTime": now_ms,
        "executedQty": executed_qty,
        "cummulativeQuoteQty": filled_notional,
        "fills": [
            {
                "tradeId": 7001,
                "qty": "1",
                "price": "100",
                "commission": "0.10",
                "commissionAsset": "USDT",
            },
            {
                "tradeId": 7002,
                "qty": "1",
                "price": "100",
                "commission": "0.15",
                "commissionAsset": "USDT",
            },
        ],
    }


def _terminal_hop_receipt(
    *,
    symbol: str,
    side: str,
    order_id: str,
    quantity: float,
    notional: float,
    fee: float,
    fee_asset: str,
) -> dict:
    now = time.time()
    return {
        "symbol": symbol,
        "side": side,
        "orderId": order_id,
        "provider_order_id": order_id,
        "status": "FILLED",
        "provider_status": "FILLED",
        "data_status": "live",
        "truth_status": "real_observed",
        "reason": "complete_fresh_terminal_provider_fill_receipt",
        "source_id": f"binance:order:{order_id}:trades",
        "source_timestamp": now,
        "provider_timestamp": now,
        "received_at": now,
        "receipt_id": f"binance:fill:{order_id}",
        "fills": [{"tradeId": f"trade-{order_id}"}],
        "filled_qty": quantity,
        "filled_notional": notional,
        "filled_avg_price": notional / quantity,
        "fee": fee,
        "fee_asset": fee_asset,
        "fee_currency": fee_asset,
        "fill_receipt_complete": True,
        "eligible_for_action": False,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
        "generated_values": False,
        "reconciliation_required": False,
    }


def test_full_order_normalizes_exact_fills_fee_ids_and_provider_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    now = time.time()

    receipt = client._normalize_order_receipt(
        _full_order(),
        symbol="ETHUSDT",
        side="SELL",
        margin=False,
        expected_order_id="42",
        now=now,
    )

    assert receipt["status"] == "FILLED"
    assert receipt["filled_qty"] == pytest.approx(2.0)
    assert receipt["filled_notional"] == pytest.approx(200.0)
    assert receipt["filled_avg_price"] == pytest.approx(100.0)
    assert receipt["fee"] == pytest.approx(0.25)
    assert receipt["fee_asset"] == "USDT"
    assert [row["tradeId"] for row in receipt["fills"]] == ["7001", "7002"]
    assert receipt["source_timestamp"] <= receipt["received_at"] + 5.0
    assert receipt["fill_receipt_complete"] is True
    assert receipt["eligible_for_accounting"] is True
    assert receipt["eligible_for_learning"] is True
    assert receipt["generated_values"] is False


def test_terminal_status_without_complete_fee_evidence_remains_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    raw = _full_order()
    raw["fills"][0].pop("commissionAsset")

    receipt = client._normalize_order_receipt(
        raw,
        symbol="ETHUSDT",
        side="SELL",
        margin=False,
        expected_order_id="42",
    )

    assert receipt["status"] == "pending_reconciliation"
    assert receipt["fill_receipt_complete"] is False
    assert receipt["eligible_for_accounting"] is False
    assert receipt["eligible_for_learning"] is False


def _ready_live_order_client(
    monkeypatch: pytest.MonkeyPatch,
) -> BinanceClient:
    client = _client(monkeypatch)
    client.dry_run = False
    client.get_asset_balance = lambda _asset: {
        "asset": "ETH",
        "free": 10.0,
        "locked": 0.0,
        "source_timestamp": time.time(),
        "received_at": time.time(),
        "receipt_id": "balance-1",
        "truth_status": "real_provider",
        "generated_values": False,
        "eligible_for_action": True,
    }
    client.get_symbol_filters = lambda _symbol: {
        "step_size": 0.001,
        "min_qty": 0.001,
        "max_qty": 1000.0,
        "min_notional": 1.0,
        "base_precision": 8,
        "quote_precision": 8,
    }
    client.adjust_quantity = lambda _symbol, value: float(value)
    client.adjust_quote_qty = lambda _symbol, value: float(value)
    client.get_ticker = lambda symbol: {
        "symbol": symbol,
        "price": 100.0,
        "source_timestamp": time.time(),
        "received_at": time.time(),
        "receipt_id": "quote-1",
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
    }
    return client


def test_pending_order_suppresses_duplicates_and_reads_one_stage_per_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _ready_live_order_client(monkeypatch)
    calls: list[tuple[str, str]] = []

    def signed(method: str, path: str, _params: dict):
        calls.append((method, path))
        now_ms = int(time.time() * 1000)
        if path == "/api/v3/order" and method == "POST":
            return {
                "symbol": "ETHUSDT",
                "side": "SELL",
                "orderId": 42,
                "status": "NEW",
                "updateTime": now_ms,
                "executedQty": "0",
                "cummulativeQuoteQty": "0",
            }
        if path == "/api/v3/order" and method == "GET":
            return {
                "symbol": "ETHUSDT",
                "side": "SELL",
                "orderId": 42,
                "status": "FILLED",
                "updateTime": now_ms,
                "executedQty": "2",
                "cummulativeQuoteQty": "200",
            }
        if path == "/api/v3/myTrades":
            return [
                {
                    "symbol": "ETHUSDT",
                    "orderId": 42,
                    "id": 7001,
                    "qty": "1",
                    "price": "100",
                    "quoteQty": "100",
                    "commission": "0.10",
                    "commissionAsset": "USDT",
                    "time": now_ms,
                },
                {
                    "symbol": "ETHUSDT",
                    "orderId": 42,
                    "id": 7002,
                    "qty": "1",
                    "price": "100",
                    "quoteQty": "100",
                    "commission": "0.15",
                    "commissionAsset": "USDT",
                    "time": now_ms,
                },
            ]
        raise AssertionError(f"unexpected endpoint {method} {path}")

    client._signed_request = signed

    acknowledgement = client.place_market_order("ETHUSDT", "SELL", quantity=2.0)
    order_readback = client.place_market_order("ETHUSDT", "SELL", quantity=2.0)
    trade_readback = client.place_market_order("ETHUSDT", "SELL", quantity=2.0)

    assert acknowledgement["status"] == "pending_reconciliation"
    assert order_readback["status"] == "pending_reconciliation"
    assert trade_readback["status"] == "FILLED"
    assert trade_readback["fee"] == pytest.approx(0.25)
    assert calls == [
        ("POST", "/api/v3/order"),
        ("GET", "/api/v3/order"),
        ("GET", "/api/v3/myTrades"),
    ]
    assert client._pending_orders == {}


def test_ambiguous_submission_is_latched_without_automatic_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _ready_live_order_client(monkeypatch)
    calls: list[str] = []

    def unavailable(_method: str, path: str, _params: dict):
        calls.append(path)
        raise RuntimeError("submission outcome unavailable")

    client._signed_request = unavailable

    first = client.place_market_order("ETHUSDT", "SELL", quantity=2.0)
    second = client.place_market_order("ETHUSDT", "SELL", quantity=2.0)

    assert first["status"] == "pending_reconciliation"
    assert second["status"] == "pending_reconciliation"
    assert second["reason"] == "ambiguous_submission_requires_external_reconciliation"
    assert calls == ["/api/v3/order"]
    assert len(client._pending_orders) == 1


def test_dry_run_orders_are_not_submitted_or_accounting_eligible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    client._signed_request = lambda *_args, **_kwargs: pytest.fail("dry run must not call a provider")

    spot = client.place_market_order("ETHUSDT", "BUY", quote_qty=10.0)
    margin = client.place_margin_order("ETHUSDT", "BUY", quantity=0.1)

    for receipt in (spot, margin):
        assert receipt["status"] == "not_submitted"
        assert receipt["data_status"] == "not_submitted"
        assert receipt["fill_receipt_complete"] is False
        assert receipt["eligible_for_accounting"] is False
        assert receipt["eligible_for_learning"] is False


def test_multihop_conversion_advances_once_and_never_repeats_completed_hop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    client.dry_run = False
    client.get_asset_balance = lambda _asset: {
        "free": 2.0,
        "receipt_id": "balance-eth",
        "truth_status": "real_provider",
        "generated_values": False,
        "eligible_for_action": True,
    }
    client.find_conversion_path = lambda _source, _target: [
        {"pair": "ETHUSDT", "side": "SELL", "from": "ETH", "to": "USDT"},
        {"pair": "BTCUSDT", "side": "BUY", "from": "USDT", "to": "BTC"},
    ]
    submitted: list[tuple[str, str, float | None, float | None]] = []
    receipts = [
        _terminal_hop_receipt(
            symbol="ETHUSDT",
            side="SELL",
            order_id="sell-1",
            quantity=1.998,
            notional=199.8,
            fee=0.8,
            fee_asset="USDT",
        ),
        _terminal_hop_receipt(
            symbol="BTCUSDT",
            side="BUY",
            order_id="buy-1",
            quantity=0.0039,
            notional=199.0,
            fee=0.000001,
            fee_asset="BTC",
        ),
    ]

    def place(symbol: str, side: str, quantity=None, quote_qty=None):
        submitted.append((symbol, side, quantity, quote_qty))
        return receipts[len(submitted) - 1]

    client.place_market_order = place
    pool = BinancePoolClient(client)

    first = pool.convert_crypto("ETH", "BTC", 2.0)
    second = pool.convert_crypto("ETH", "BTC", 2.0)

    assert first["success"] is False
    assert first["reason"] == "next_conversion_hop_not_submitted"
    assert first["eligible_for_accounting"] is False
    assert second["success"] is True
    assert second["eligible_for_accounting"] is True
    assert second["eligible_for_learning"] is True
    assert second["final_amount"] == pytest.approx(0.003899)
    assert [row[0] for row in submitted] == ["ETHUSDT", "BTCUSDT"]
    assert submitted[1][3] == pytest.approx(199.0)
    assert client._pending_conversions == {}


def test_conversion_missing_balance_is_no_data_and_submits_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    client.dry_run = False
    client.get_asset_balance = lambda _asset: None
    client.find_conversion_path = lambda *_args: pytest.fail("path lookup must not follow missing balance")
    client.place_market_order = lambda *_args, **_kwargs: pytest.fail("order must not be submitted")

    result = client.convert_crypto("ETH", "BTC", 1.0)

    assert result["success"] is False
    assert result["status"] == "no_data"
    assert result["eligible_for_accounting"] is False
    assert client._pending_conversions == {}


def test_post_fill_conversion_failure_is_latched_without_resubmission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    client.dry_run = False
    client.get_asset_balance = lambda _asset: {
        "free": 2.0,
        "receipt_id": "balance-eth",
        "truth_status": "real_provider",
        "generated_values": False,
        "eligible_for_action": True,
    }
    client.find_conversion_path = lambda _source, _target: [
        {"pair": "ETHUSDT", "side": "SELL", "from": "ETH", "to": "USDT"}
    ]
    calls: list[str] = []

    def terminal_with_fee_larger_than_output(*_args, **_kwargs):
        calls.append("submitted")
        return _terminal_hop_receipt(
            symbol="ETHUSDT",
            side="SELL",
            order_id="sell-fee",
            quantity=1.0,
            notional=1.0,
            fee=2.0,
            fee_asset="USDT",
        )

    client.place_market_order = terminal_with_fee_larger_than_output

    first = client.convert_crypto("ETH", "USDT", 1.0)
    second = client.convert_crypto("ETH", "USDT", 1.0)

    assert first["success"] is False
    assert first["reason"] == "positive_post_fee_hop_output_required"
    assert second["reason"] == "positive_post_fee_hop_output_required"
    assert calls == ["submitted"]
    assert client._pending_conversions[("ETH", "USDT")]["terminal_failure"]


def test_margin_position_without_live_price_is_not_emitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    client.dry_run = False
    client.get_margin_account = lambda: {
        "userAssets": [
            {
                "asset": "ETH",
                "borrowed": "1",
                "netAsset": "-1",
                "free": "0",
                "interest": "0.01",
            }
        ]
    }
    client.get_ticker = lambda _symbol: {
        "data_status": "no_data",
        "truth_status": "no_data",
        "generated_values": False,
    }

    assert client.get_open_margin_positions() == []


def test_fee_quote_helper_requires_canonical_terminal_fee_asset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    receipt = _terminal_hop_receipt(
        symbol="ETHUSDT",
        side="SELL",
        order_id="fee-1",
        quantity=1.0,
        notional=100.0,
        fee=0.25,
        fee_asset="USDT",
    )

    assert client.compute_order_fees_in_quote(receipt, "USDT") == pytest.approx(0.25)
    assert client.compute_order_fees_in_quote(receipt, "GBP") is None
    receipt["eligible_for_accounting"] = False
    assert client.compute_order_fees_in_quote(receipt, "USDT") is None
