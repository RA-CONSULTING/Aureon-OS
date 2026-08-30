import json
from pathlib import Path

import pytest

from aureon.bots.gaia_aggressive_reclaimer import (
    PHI,
    SCHUMANN,
    AggressiveReclaimer,
)


NOW = 2_000_000_000.0


def _base(receipt_type: str, receipt_id: str, venue: str = "kraken") -> dict:
    return {
        "receipt_id": receipt_id,
        "receipt_type": receipt_type,
        "provider": venue,
        "venue": venue,
        "provider_timestamp": NOW,
    }


class _ReceiptAdapter:
    venue = "kraken"

    def __init__(
        self,
        *,
        submit_status: str = "accepted",
        readback_statuses: list[str] | None = None,
        market_venue: str = "kraken",
    ) -> None:
        self.submit_status = submit_status
        self.readback_statuses = list(readback_statuses or [])
        self.market_venue = market_venue
        self.submit_calls = 0
        self.readback_calls = 0
        self.position_active = True
        self.client_order_id = ""

    def get_account_receipt(self) -> dict:
        return {
            **_base("account", "acct-1"),
            "account_id": "provider-account-1",
            "provider_account_status": "active",
            "trading_permitted": True,
        }

    def get_position_receipts(self) -> list[dict]:
        if not self.position_active:
            return []
        return [
            {
                **_base("position", "position-1"),
                "account_id": "provider-account-1",
                "symbol": "SOLUSD",
                "quantity": "2",
                "sellable_quantity": "2",
            }
        ]

    def get_market_receipt(self, symbol: str) -> dict:
        return {
            **_base("market", "market-1", self.market_venue),
            "symbol": symbol,
            "price": "110",
            "quote_currency": "USD",
            "observed_exit_cost_pct": "0.10",
            "actionable": True,
        }

    def get_cost_basis_receipt(self, symbol: str) -> dict:
        return {
            **_base("cost_basis", "basis-1"),
            "account_id": "provider-account-1",
            "symbol": symbol,
            "unit_cost": "100",
            "quote_currency": "USD",
            "unit_cost_includes_fees": True,
        }

    def _order(self, status: str, receipt_id: str) -> dict:
        receipt = {
            **_base("order", receipt_id),
            "symbol": "SOLUSD",
            "side": "sell",
            "client_order_id": self.client_order_id,
            "status": status,
        }
        if status != "dry_run":
            receipt["provider_order_id"] = "provider-order-1"
        if status == "dry_run":
            receipt["dry_run"] = True
        if status == "filled":
            receipt.update(
                {
                    "is_final": True,
                    "filled_quantity": "2",
                    "remaining_quantity": "0",
                    "average_fill_price": "110",
                    "filled_notional": "220",
                    "filled_notional_currency": "USD",
                    "fee_amount": "0.22",
                    "fee_currency": "USD",
                    "realized_pnl": "19.78",
                    "realized_pnl_currency": "USD",
                    "realized_pnl_source": "provider",
                }
            )
        return receipt

    def submit_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str,
        client_order_id: str,
    ) -> dict:
        self.submit_calls += 1
        assert (symbol, side, quantity) == ("SOLUSD", "sell", "2")
        self.client_order_id = client_order_id
        return self._order(self.submit_status, "submission-1")

    def read_order_receipt(self, order_reference: str) -> dict:
        self.readback_calls += 1
        assert order_reference in {"provider-order-1", self.client_order_id}
        status = self.readback_statuses.pop(0)
        if status == "filled":
            self.position_active = False
        return self._order(status, f"readback-{self.readback_calls}")


def test_gaia_requires_same_venue_receipts_and_only_terminal_fill_mutates(tmp_path: Path) -> None:
    source = Path(
        "aureon/bots/gaia_aggressive_reclaimer.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "_baton_link",
        "PYTHONUNBUFFERED",
        "sys.path",
        "get_binance_client",
        "get_kraken_client",
        "AlpacaClient()",
    ):
        assert forbidden not in source
    assert PHI > 1
    assert SCHUMANN == 7.83

    empty_path = tmp_path / "empty.json"
    empty = AggressiveReclaimer(state_path=empty_path, now=lambda: NOW)
    assert empty.run_cycle() == {
        "status": "no_data",
        "reason": "no_injected_adapters",
    }
    assert not empty_path.exists()
    with pytest.raises(RuntimeError, match="continuous execution is disabled"):
        empty.run()

    state_path = tmp_path / "gaia.json"
    adapter = _ReceiptAdapter(readback_statuses=["partially_filled", "filled"])
    gaia = AggressiveReclaimer(
        {"kraken": adapter},
        state_path=state_path,
        now=lambda: NOW,
    )

    assert gaia.run_cycle() == {
        "status": "unresolved_order_latched",
        "venue": "kraken",
    }
    latched = json.loads(state_path.read_text(encoding="utf-8"))
    assert latched["trade_count"] == 0
    assert latched["realized_pnl_by_currency"] == {}
    assert latched["pending"]["kraken"]["last_status"] == "accepted"

    assert gaia.run_cycle() == {
        "status": "unresolved_order_latched",
        "venue": "kraken",
    }
    assert adapter.readback_calls == 1
    partial = json.loads(state_path.read_text(encoding="utf-8"))
    assert partial["trade_count"] == 0
    assert partial["fee_totals_by_currency"] == {}

    assert gaia.run_cycle() == {
        "status": "terminal_fill_applied",
        "venue": "kraken",
    }
    assert adapter.readback_calls == 2
    filled = json.loads(state_path.read_text(encoding="utf-8"))
    assert filled["pending"] == {}
    assert filled["trade_count"] == 1
    assert filled["applied_fill_receipt_ids"] == ["readback-2"]
    assert filled["filled_notional_by_currency"] == {"USD": "220"}
    assert filled["fee_totals_by_currency"] == {"USD": "0.22"}
    assert filled["realized_pnl_by_currency"] == {"USD": "19.78"}
    assert gaia.run_cycle()["status"] == "no_action"
    assert adapter.submit_calls == 1

    dry_path = tmp_path / "dry.json"
    dry_adapter = _ReceiptAdapter(submit_status="dry_run")
    dry = AggressiveReclaimer(
        {"kraken": dry_adapter},
        state_path=dry_path,
        now=lambda: NOW,
    )
    assert dry.run_cycle()["status"] == "dry_run_no_accounting"
    dry_state = json.loads(dry_path.read_text(encoding="utf-8"))
    assert dry_state["pending"] == {}
    assert dry_state["trade_count"] == 0

    rejected_path = tmp_path / "rejected.json"
    rejected_adapter = _ReceiptAdapter(readback_statuses=["rejected"])
    rejected = AggressiveReclaimer(
        {"kraken": rejected_adapter},
        state_path=rejected_path,
        now=lambda: NOW,
    )
    assert rejected.run_cycle()["status"] == "unresolved_order_latched"
    assert rejected.run_cycle()["status"] == "terminal_nonfill_no_accounting"
    rejected_state = json.loads(rejected_path.read_text(encoding="utf-8"))
    assert rejected_state["pending"] == {}
    assert rejected_state["trade_count"] == 0

    incomplete_path = tmp_path / "incomplete.json"
    incomplete_adapter = _ReceiptAdapter(readback_statuses=["filled"])
    complete_order = incomplete_adapter._order

    def _missing_realized_pnl(status: str, receipt_id: str) -> dict:
        receipt = complete_order(status, receipt_id)
        if status == "filled":
            receipt.pop("realized_pnl")
        return receipt

    incomplete_adapter._order = _missing_realized_pnl
    incomplete = AggressiveReclaimer(
        {"kraken": incomplete_adapter},
        state_path=incomplete_path,
        now=lambda: NOW,
    )
    assert incomplete.run_cycle()["status"] == "unresolved_order_latched"
    assert incomplete.run_cycle()["status"] == "no_action"
    incomplete_state = json.loads(incomplete_path.read_text(encoding="utf-8"))
    assert "kraken" in incomplete_state["pending"]
    assert incomplete_state["trade_count"] == 0
    assert incomplete_state["applied_fill_receipt_ids"] == []

    mismatch_path = tmp_path / "mismatch.json"
    mismatch_adapter = _ReceiptAdapter(market_venue="binance")
    mismatch = AggressiveReclaimer(
        {"kraken": mismatch_adapter},
        state_path=mismatch_path,
        now=lambda: NOW,
    )
    mismatch_result = mismatch.run_cycle()
    assert mismatch_result["status"] == "no_action"
    assert "cross-venue receipt relabeling is forbidden" in (
        mismatch_result["rejected_inputs"]["kraken"]
    )
    assert mismatch_adapter.submit_calls == 0
    assert not mismatch_path.exists()
