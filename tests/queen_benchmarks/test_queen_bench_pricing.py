"""Queen pricing seed set — the real sterling, margin, cost and fee maths.

Grounded in the code paths the live traders use:
* aureon/exchanges/single_currency_equity.py (the Capital sterling read)
* CapitalCFDTrader cost/margin/TP maths and the order preflight
* KrakenClient.compute_order_fees_in_quote (verified fee only)

Values are hand-checkable invariants (price*qty, spread*size, 25% slippage,
margin %, currency normalisation). The one observed figure is the Capital read
of 2026-11-10 after the balance fix: equity 105.29 GBP, free margin 0.0. That
figure was reported by the running status server, not stored in a benchmark file.
Every target below is mutated by aureon/autonomous/queen_benchmark_gate.py.
"""

import math

import pytest

from aureon.exchanges import capital_cfd_trader as cct
from aureon.exchanges import kraken_client as kc
from aureon.exchanges import single_currency_equity as sce

Trader = cct.CapitalCFDTrader


# ── single_currency_equity ─────────────────────────────────────────────────


def test_observed_capital_read_no_free_margin():
    snap = sce.assemble_sterling_snapshot(105.29, 0.0, min_profit_gbp=0.01)
    assert snap["equity_gbp"] == 105.29
    assert snap["free_gbp"] == 0.0
    assert snap["used_gbp"] == pytest.approx(105.29)
    assert snap["budget_gbp"] == 0.0
    assert snap["target_pct_equity"] == pytest.approx(0.01 / 105.29 * 100.0)


def test_snapshot_arithmetic_by_hand():
    snap = sce.assemble_sterling_snapshot(200.0, 50.0, min_profit_gbp=1.0)
    assert snap["used_gbp"] == pytest.approx(150.0)
    assert snap["budget_gbp"] == pytest.approx(35.0)  # 70% of free
    assert snap["target_pct_equity"] == pytest.approx(0.5)
    over = sce.assemble_sterling_snapshot(10.0, 25.0, min_profit_gbp=1.0)
    assert over["used_gbp"] == 0.0  # free above equity never makes used negative
    zero = sce.assemble_sterling_snapshot(0.0, 0.0, min_profit_gbp=1.0)
    assert zero["target_pct_equity"] == 0.0


@pytest.mark.parametrize("equity,free", [(None, 1.0), (1.0, None), (-1.0, 1.0), (1.0, -0.5)])
def test_snapshot_derived_fields_stay_null(equity, free):
    snap = sce.assemble_sterling_snapshot(equity, free, min_profit_gbp=1.0)
    assert snap["used_gbp"] is None and snap["budget_gbp"] is None and snap["target_pct_equity"] is None


def test_nonnegative_amount_edges():
    assert sce.nonnegative_amount(0) == 0.0
    assert sce.nonnegative_amount(2.5) == 2.5
    assert sce.nonnegative_amount(-0.01) is None
    assert sce.nonnegative_amount(True) is None
    assert sce.nonnegative_amount(float("nan")) is None
    assert sce.nonnegative_amount("3") is None


def test_gbp_equity_one_currency_only():
    assert sce.gbp_equity_from_balances({"GBP": 105.29}) == (105.29, "")
    assert sce.gbp_equity_from_balances({"gbp": 0.0}) == (0.0, "")
    for bad in ({}, {"USD": 5.0}, {"GBP": 1.0, "USD": 1.0}, {"gbp": 1.0, "GBP": 2.0},
                {"GBP": -1.0}, {"GBP": float("inf")}, {"_unreadable": True}, None):
        amount, reason = sce.gbp_equity_from_balances(bad)
        assert amount is None and reason


def test_currency_amount_map_sums_and_refuses():
    rows = [{"currency": "GBP", "available": 1.5}, {"currency": "gbp", "available": 2.25},
            {"currency": "USD", "available": 4.0}]
    assert sce.currency_amount_map(rows, "available") == {"GBP": 3.75, "USD": 4.0}
    assert sce.currency_amount_map([{"currency": "GBP", "available": -1}], "available") == {"_unreadable": True}
    assert sce.currency_amount_map([{"currency": "GBP"}], "available") == {"_unreadable": True}
    assert sce.gbp_field_from_accounts([{"currency": "GBP", "available": 0.0}], "available") == (0.0, False)
    assert sce.gbp_field_from_accounts([], "available") == (None, False)


# ── Capital CFD maths ──────────────────────────────────────────────────────


class _Stub:
    _trade_profit_validator = object()


def test_margin_required_is_notional_times_pct():
    assert Trader._estimate_capital_margin_required(2.0, 100.0, 5.0) == pytest.approx(10.0)
    assert Trader._estimate_capital_margin_required(0.5, 3000.0, 20.0) == pytest.approx(300.0)
    assert Trader._estimate_capital_margin_required(2.0, 100.0, 0.0) == 0.0
    assert Trader._estimate_capital_margin_required(-1.0, 100.0, 5.0) == 0.0


def test_required_tp_pct_is_penny_over_notional():
    assert cct.CAPITAL_MIN_PROFIT_GBP == 0.01
    assert Trader._required_tp_pct_for_profit(None, 50.0, 2.0) == pytest.approx(0.01)  # 0.01/100*100
    assert Trader._required_tp_pct_for_profit(None, 10.0, 0.1) == pytest.approx(1.0)   # 0.01/1*100


def test_cost_profile_spread_and_slippage_by_hand():
    out = Trader._capital_cost_profile(_Stub(), "X", 2.0, 100.0, 1.0, bid=99.9, ask=100.1)
    assert out["notional"] == pytest.approx(200.0)
    assert out["expected_gross_profit"] == pytest.approx(2.0)
    assert out["round_trip_cost"] == pytest.approx(0.5)  # spread 0.2*2 = 0.4, slippage 25% = 0.1
    assert out["expected_net_profit"] == pytest.approx(1.5)
    assert out["expected_net_profit"] < out["expected_gross_profit"]


def test_cost_profile_crossed_quote_and_no_validator():
    crossed = Trader._capital_cost_profile(_Stub(), "X", 2.0, 100.0, 1.0, bid=100.1, ask=99.9)
    assert crossed["round_trip_cost"] == 0.0
    plain = type("P", (), {"_trade_profit_validator": None})()
    out = Trader._capital_cost_profile(plain, "X", 3.0, 10.0, 2.0, bid=9.9, ask=10.1)
    assert out["round_trip_cost"] == 0.0 and out["expected_net_profit"] == pytest.approx(0.6)


def test_cost_and_margin_degenerate_inputs_are_zero_not_defaults():
    for size, price in ((None, 100.0), (0.0, 100.0), (2.0, None), (2.0, 0.0)):
        out = Trader._capital_cost_profile(_Stub(), "X", size, price, 1.0, bid=99.9, ask=100.1)
        assert out["notional"] == 0.0 and out["expected_gross_profit"] == 0.0
        assert out["round_trip_cost"] == 0.0 and out["expected_net_profit"] == 0.0
        assert Trader._estimate_capital_margin_required(size, price, 5.0) == 0.0
    assert Trader._estimate_capital_margin_required(2.0, 100.0, None) == 0.0
    assert Trader._estimate_capital_margin_required(2.0, 100.0, -5.0) == 0.0
    neg_tp = Trader._capital_cost_profile(_Stub(), "X", 2.0, 100.0, -1.0, bid=99.9, ask=100.1)
    assert neg_tp["expected_gross_profit"] == 0.0
    none_tp = Trader._capital_cost_profile(_Stub(), "X", 2.0, 100.0, None, bid=99.9, ask=100.1)
    assert none_tp["expected_gross_profit"] == 0.0
    assert none_tp["round_trip_cost"] == pytest.approx(0.5)


def test_scaled_preflight_is_linear():
    base = {"requested_size": 4.0, "notional": 400.0, "estimated_margin_required": 20.0,
            "expected_gross_profit": 4.0, "expected_net_profit": 3.0, "round_trip_cost": 1.0}
    half = Trader._scaled_preflight(None, base, 2.0)
    assert half["requested_size"] == 2.0
    assert half["notional"] == pytest.approx(200.0)
    assert half["estimated_margin_required"] == pytest.approx(10.0)
    assert half["expected_net_profit"] == pytest.approx(1.5)
    assert half["round_trip_cost"] == pytest.approx(0.5)
    assert Trader._scaled_preflight(None, {"requested_size": 0.0, "notional": 5.0}, 1.0)["notional"] == 0.0
    nulls = Trader._scaled_preflight(None, {"requested_size": 2.0, "notional": 0.0, "round_trip_cost": None}, None)
    assert nulls["requested_size"] == 0.0 and nulls["notional"] == 0.0 and nulls["round_trip_cost"] is None
    assert Trader._scaled_preflight(None, {"requested_size": -2.0, "notional": 4.0}, 1.0)["notional"] == 0.0
    assert Trader._scaled_preflight(None, {"requested_size": 2.0, "notional": 4.0}, -1.0)["notional"] == 0.0
    assert Trader._scaled_preflight(None, {"requested_size": None, "notional": 4.0}, 1.0)["notional"] == 0.0


class _Accounts:
    def __init__(self, available):
        self.available = available

    def get_accounts(self):
        return [{"currency": "GBP", "available": self.available}]


def _preflight(available):
    trader = Trader.__new__(Trader)
    trader.client = _Accounts(available)
    return trader._capital_preflight("X", 1.0, {"bid": 99.9, "ask": 100.1})


def test_preflight_spread_sign_and_pct():
    pf = _preflight(50.0)
    assert pf["price"] == pytest.approx(100.0)  # mid of bid/ask
    assert pf["spread"] == pytest.approx(0.2) and pf["spread"] >= 0
    assert pf["spread_pct"] == pytest.approx(0.2)
    assert pf["ok"] is True


def test_preflight_refuses_zero_free_margin_like_the_observed_read():
    pf = _preflight(0.0)
    assert pf["ok"] is False
    assert pf["reason"] == "available account balance <= 0"


# ── Kraken fee inclusion ───────────────────────────────────────────────────


def _kraken():
    return kc.KrakenClient.__new__(kc.KrakenClient)


VERIFIED = {"data_status": "live", "fill_receipt_complete": True, "eligible_for_accounting": True}


def test_kraken_fee_counted_only_when_verified_and_in_quote():
    k = _kraken()
    assert k.compute_order_fees_in_quote({**VERIFIED, "fee": "0.26", "fee_asset": "ZGBP"}, "GBP") == pytest.approx(0.26)
    assert k.compute_order_fees_in_quote({**VERIFIED, "fee": "0.26", "fee_asset": "XBT"}, "GBP") is None
    assert k.compute_order_fees_in_quote({**VERIFIED, "fee": "-0.1", "fee_asset": "GBP"}, "GBP") is None
    assert k.compute_order_fees_in_quote({**VERIFIED, "data_status": "dry_run", "fee": "1", "fee_asset": "GBP"}, "GBP") is None
    assert k.compute_order_fees_in_quote({**VERIFIED, "fee": "0", "fee_asset": "GBP"}, "GBP") == 0.0


def test_kraken_finite_decimal():
    assert kc._finite_decimal("1.50") == kc.Decimal("1.50")
    assert kc._finite_decimal("0", positive=True) is None
    assert kc._finite_decimal("-1", nonnegative=True) is None
    assert kc._finite_decimal("0", nonnegative=True) == 0
    assert kc._finite_decimal("1", positive=True) == 1
    assert kc._finite_decimal(True) is None and kc._finite_decimal("nan") is None
    assert kc._finite_decimal(None) is None and kc._finite_decimal("abc") is None
    assert math.isclose(float(kc._finite_decimal(2.5)), 2.5)
