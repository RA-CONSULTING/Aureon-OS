import json
import sqlite3
import time

from aureon.exchanges.kraken_asset_registry import (
    SCHEMA_VERSION,
    audit_kraken_asset_registry,
    build_kraken_asset_registry,
    build_kraken_order_survival_envelope,
    write_kraken_asset_registry,
)
from aureon.exchanges.kraken_client import KrakenClient


class FakeKrakenClient:
    def __init__(self):
        self.pairs = {
            "XXBTZUSD": {
                "altname": "XBTUSD",
                "wsname": "XBT/USD",
                "base": "XXBT",
                "quote": "ZUSD",
                "lot_decimals": 8,
                "pair_decimals": 1,
                "ordermin": "0.0001",
                "costmin": "0.5",
                "fees": [[0, 0.40], [10000, 0.35]],
                "fees_maker": [[0, 0.25], [10000, 0.20]],
                "leverage_buy": [2, 3, 5],
                "leverage_sell": [2, 3, 5],
            },
            "XETHZUSD": {
                "altname": "ETHUSD",
                "wsname": "ETH/USD",
                "base": "XETH",
                "quote": "ZUSD",
                "lot_decimals": 8,
                "pair_decimals": 2,
                "ordermin": "0.001",
                "costmin": "0.5",
                "fees": [[0, 0.40]],
                "fees_maker": [[0, 0.25]],
                "leverage_buy": [2, 3],
                "leverage_sell": [2, 3],
            },
            "XXDGZUSD": {
                "altname": "DOGEUSD",
                "wsname": "DOGE/USD",
                "base": "XXDG",
                "quote": "ZUSD",
                "lot_decimals": 2,
                "pair_decimals": 5,
                "ordermin": "2",
                "costmin": "0.5",
                "fees": [[0, 0.40]],
                "fees_maker": [[0, 0.25]],
            },
        }
        self.tickers = {
            "XBTUSD": {"price": 100000.0, "bid": 99990.0, "ask": 100010.0},
            "ETHUSD": {"price": 3000.0, "bid": 2999.0, "ask": 3001.0},
            "DOGEUSD": {"price": 0.20, "bid": 0.199, "ask": 0.201},
        }

    def _load_asset_pairs(self, force=False):
        return dict(self.pairs)

    def get_ticker(self, symbol):
        return dict(self.tickers.get(symbol, {}))

    def get_ticker_receipt(self, symbol):
        ticker = self.get_ticker(symbol)
        if not ticker:
            return {
                "data_status": "no_data", "truth_status": "no_data",
                "generated_values": False, "action": False, "accounting": False, "learning": False,
            }
        return {
            **ticker,
            "open_price": ticker["price"],
            "volume_24h": 1.0,
            "data_status": "live",
            "truth_status": "real_observed",
            "generated_values": False,
            "source_id": "kraken:test_ticker",
            "source_timestamp": time.time(),
            "received_at": time.time(),
            "receipt_id": "kraken:test:" + symbol,
            "action": False,
            "accounting": False,
            "learning": False,
        }


def test_kraken_asset_registry_maps_spot_margin_costs_and_routes():
    report = build_kraken_asset_registry(client=FakeKrakenClient(), max_tickers=-1)

    assert report["schema_version"] == SCHEMA_VERSION
    assert report["summary"]["total_pairs"] == 3
    assert report["summary"]["spot_trade_ready_count"] == 3
    assert report["summary"]["margin_pair_count"] == 2
    assert report["summary"]["margin_trade_ready_count"] == 2

    assets = {asset["symbol"]: asset for asset in report["assets"]}
    xbt = assets["XBTUSD"]
    assert xbt["base_asset"] == "BTC"
    assert xbt["quote_asset"] == "USD"
    assert xbt["entry_maker_fee_pct"] == 0.25
    assert xbt["entry_taker_fee_pct"] == 0.40
    assert xbt["max_leverage"] == 5
    assert xbt["min_notional_estimate"] == 0.5
    assert xbt["min_margin_required_estimate"] == 0.1
    assert xbt["spot_trade_ready"] is True
    assert xbt["margin_trade_ready"] is True
    assert 'client.place_market_order("XBTUSD", "buy", quantity=base_qty)' == xbt["spot_buy_call"]
    assert 'client.place_margin_order("XBTUSD", "buy"' in xbt["margin_long_call"]

    doge = assets["DOGEUSD"]
    assert doge["margin_supported"] is False
    assert doge["margin_trade_ready"] is False
    assert doge["spot_trade_ready"] is True
    assert doge["margin_long_call"] == ""

    assert report["audit"]["status"] == "passed"
    assert report["audit"]["score_pct"] == 100.0


def test_kraken_asset_registry_marks_unsampled_pairs_as_no_data_and_not_ready():
    report = build_kraken_asset_registry(client=FakeKrakenClient(), max_tickers=1)

    assets = {asset["symbol"]: asset for asset in report["assets"]}
    assert assets["DOGEUSD"]["snapshot_status"] == "no_data"
    assert assets["DOGEUSD"]["spot_trade_ready"] is False
    assert "no_data" in assets["DOGEUSD"]["blockers"]
    assert report["summary"]["known_but_not_sampled_count"] == 2


def test_write_kraken_asset_registry_outputs_json_csv_sqlite_and_markdown(tmp_path):
    report = build_kraken_asset_registry(client=FakeKrakenClient(), max_tickers=-1)
    paths = write_kraken_asset_registry(
        report,
        state_json=tmp_path / "state" / "registry.json",
        output_json=tmp_path / "docs" / "registry.json",
        output_csv=tmp_path / "docs" / "registry.csv",
        output_md=tmp_path / "docs" / "registry.md",
        output_db=tmp_path / "state" / "registry.sqlite",
        public_json=tmp_path / "public" / "registry.json",
    )

    for path in paths.values():
        assert path

    public_payload = json.loads((tmp_path / "public" / "registry.json").read_text(encoding="utf-8"))
    assert public_payload["summary"]["margin_pair_count"] == 2
    assert public_payload["audit"]["status"] == "passed"
    assert "XBTUSD" in (tmp_path / "docs" / "registry.csv").read_text(encoding="utf-8")
    assert "Kraken Tradable Asset Registry" in (tmp_path / "docs" / "registry.md").read_text(encoding="utf-8")
    assert "Audit Checks" in (tmp_path / "docs" / "registry.md").read_text(encoding="utf-8")

    conn = sqlite3.connect(str(tmp_path / "state" / "registry.sqlite"))
    try:
        count = conn.execute("SELECT COUNT(*) FROM kraken_assets").fetchone()[0]
        xbt = conn.execute(
            "SELECT margin_trade_ready, spot_buy_call FROM kraken_assets WHERE symbol='XBTUSD'"
        ).fetchone()
    finally:
        conn.close()
    assert count == 3
    assert xbt[0] == 1
    assert 'place_market_order("XBTUSD", "buy"' in xbt[1]


def test_kraken_survival_envelope_blocks_unsafe_pending_ladder():
    report = build_kraken_asset_registry(client=FakeKrakenClient(), max_tickers=-1)
    assets = {asset["symbol"]: asset for asset in report["assets"]}
    planned = [
        {"symbol": "XBTUSD", "side": "buy", "quantity": 0.01, "price": 100000, "order_type": "limit", "post_only": True},
        {"symbol": "ETHUSD", "side": "buy", "quantity": 2.0, "price": 3000, "order_type": "limit", "margin": True, "leverage": 2},
    ]
    envelope = build_kraken_order_survival_envelope(
        planned_orders=planned,
        balances={"USD": 1000.0},
        trade_balance={"free_margin": 1000.0, "equity_value": 2500.0, "margin_amount": 0.0, "margin_level": 0.0},
        registry_assets=assets,
        policy={
            "pending_order_submission_enabled": True,
            "spot_quote_budget_pct": 25.0,
            "margin_budget_pct": 20.0,
            "min_margin_level_pct": 250.0,
        },
    )

    assert envelope["can_submit_pending_orders"] is False
    assert "spot_quote_budget_would_be_breached" in envelope["blockers"]
    assert "margin_budget_would_be_breached" in envelope["blockers"]
    assert envelope["spot_quote_required_if_all_fill"] > envelope["spot_quote_budget"]
    assert envelope["margin_required_if_all_fill"] > envelope["margin_budget"]


def test_kraken_survival_envelope_blocks_hundred_order_stress_case():
    report = build_kraken_asset_registry(client=FakeKrakenClient(), max_tickers=-1)
    assets = {asset["symbol"]: asset for asset in report["assets"]}
    planned = [
        {"symbol": "XBTUSD", "side": "buy", "quantity": 0.001, "price": 100000, "order_type": "limit", "post_only": True}
        for _ in range(100)
    ]
    envelope = build_kraken_order_survival_envelope(
        planned_orders=planned,
        balances={"USD": 50000.0},
        trade_balance={"free_margin": 100000.0, "equity_value": 100000.0, "margin_amount": 0.0, "margin_level": 0.0},
        registry_assets=assets,
        policy={
            "pending_order_submission_enabled": True,
            "max_pending_orders": 8,
            "max_pending_per_pair": 2,
            "spot_quote_budget_pct": 90.0,
        },
    )

    assert envelope["can_submit_pending_orders"] is False
    assert envelope["pending_order_count"] == 100
    assert envelope["per_pair_counts"]["XBTUSD"] == 100
    assert "max_pending_orders" in envelope["blockers"]
    assert "max_pending_per_pair" in envelope["blockers"]


def test_kraken_survival_envelope_blocks_margin_level_breach():
    report = build_kraken_asset_registry(client=FakeKrakenClient(), max_tickers=-1)
    assets = {asset["symbol"]: asset for asset in report["assets"]}
    envelope = build_kraken_order_survival_envelope(
        planned_orders=[
            {"symbol": "ETHUSD", "side": "buy", "quantity": 1.0, "price": 3000.0, "order_type": "limit", "margin": True, "leverage": 2}
        ],
        balances={"USD": 10000.0},
        trade_balance={"free_margin": 10000.0, "equity_value": 2000.0, "margin_amount": 0.0, "margin_level": 0.0},
        registry_assets=assets,
        policy={
            "pending_order_submission_enabled": True,
            "margin_budget_pct": 100.0,
            "min_margin_level_pct": 250.0,
            "stress_move_pct_crypto": 5.0,
        },
    )

    assert envelope["can_submit_pending_orders"] is False
    assert "projected_margin_level_below_minimum" in envelope["blockers"]
    assert envelope["projected_margin_level_pct"] < 250.0


def test_kraken_survival_envelope_allows_small_budgeted_plan_when_submission_enabled():
    report = build_kraken_asset_registry(client=FakeKrakenClient(), max_tickers=-1)
    assets = {asset["symbol"]: asset for asset in report["assets"]}
    envelope = build_kraken_order_survival_envelope(
        planned_orders=[
            {"symbol": "XBTUSD", "side": "buy", "quantity": 0.001, "price": 100000, "order_type": "limit", "post_only": True}
        ],
        balances={"USD": 1000.0},
        trade_balance={"free_margin": 5000.0, "equity_value": 5000.0, "margin_amount": 0.0, "margin_level": 0.0},
        registry_assets=assets,
        policy={"pending_order_submission_enabled": True, "spot_quote_budget_pct": 50.0},
    )

    assert envelope["can_submit_pending_orders"] is True
    assert envelope["blockers"] == []


def test_kraken_asset_registry_does_not_emit_secret_like_pair_fields():
    client = FakeKrakenClient()
    client.pairs["XXBTZUSD"]["api_secret"] = "SECRET-DO-NOT-EMIT"
    report = build_kraken_asset_registry(client=client, max_tickers=-1)

    rendered = json.dumps(report)
    assert "SECRET-DO-NOT-EMIT" not in rendered
    assert "api_secret" not in rendered


def test_kraken_registry_audit_detects_missing_routes_or_sensitive_keys():
    report = build_kraken_asset_registry(client=FakeKrakenClient(), max_tickers=-1)
    damaged = dict(report)
    damaged["execution_contract"] = {**report["execution_contract"], "margin_long": ""}
    damaged["credential_token"] = "do-not-emit"

    audit = audit_kraken_asset_registry(damaged)
    checks = {item["name"]: item for item in audit["checks"]}
    assert audit["status"] == "attention"
    assert checks["margin_route_declared"]["passed"] is False
    assert checks["secret_key_scan"]["passed"] is False


def test_kraken_ticker_receipt_and_registry_reject_incomplete_evidence(tmp_path):
    client = object.__new__(KrakenClient)
    client._ticker = lambda _symbols: {
        "XXBTZUSD": {"c": ["100"], "b": ["99"], "a": ["101"], "o": "98", "v": ["1", "2"]}
    }
    client._public_get = lambda _path: {"unixtime": time.time()}
    client._int_to_alt = {"XXBTZUSD": "XBTUSD"}
    receipt = client.get_ticker_receipt("XBTUSD")
    assert receipt["data_status"] == "live"
    assert receipt["truth_status"] == "real_observed"
    assert receipt["bid"] == 99.0 and receipt["ask"] == 101.0
    assert receipt["receipt_id"].startswith("kraken_ticker:")

    bad = FakeKrakenClient()
    bad.get_ticker_receipt = lambda _symbol: {
        "data_status": "live", "truth_status": "real_observed", "generated_values": True,
        "action": False, "accounting": False, "learning": False,
    }
    report = build_kraken_asset_registry(client=bad, max_tickers=-1)
    asset = report["assets"][0]
    assert report["data_status"] == "no_data"
    assert asset["market_data_status"] == "no_data"
    assert asset["bid"] is None and asset["ask"] is None and asset["mid_price"] is None
    assert asset["action"] is False and asset["accounting"] is False and asset["learning"] is False
    paths = write_kraken_asset_registry(
        report,
        state_json=tmp_path / "state.json",
        output_json=tmp_path / "output.json",
        output_csv=tmp_path / "output.csv",
        output_md=tmp_path / "output.md",
        output_db=tmp_path / "output.sqlite",
        public_json=tmp_path / "public.json",
    )
    assert paths["status"] == "no_data"
    assert not any(tmp_path.iterdir())
