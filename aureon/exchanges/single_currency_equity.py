"""Equity from one currency. Mixed units are not added together."""

from __future__ import annotations

import math
from typing import Any


def _real_amount(value: Any) -> float | None:
    """A finite int or float. Booleans, strings, NaN, and infinities are not amounts."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def nonnegative_amount(value: Any) -> float | None:
    """A finite account amount that is not negative. Zero stays zero."""

    number = _real_amount(value)
    if number is None or number < 0:
        return None
    return number


def gbp_equity_from_balances(raw: Any) -> tuple[float | None, str]:
    """One GBP amount, or null.

    ``capital_equity_gbp`` is a sterling figure. A map with two currencies
    is not added together. A single non-GBP currency is not relabeled as
    GBP. An empty map is not a zero reading. Two keys that are the same
    currency in different case are not collapsed. NaN, inf, and a negative
    amount are not coerced into a figure.
    """

    if not isinstance(raw, dict) or not raw:
        return None, "capital balance had no currency"
    if raw.get("_unreadable"):
        return None, "capital balance was not a number"
    amounts: dict[str, float] = {}
    for key, value in raw.items():
        original = str(key or "").strip()
        currency = original.upper()
        if not currency:
            return None, "capital balance was not a number"
        if currency in amounts:
            return None, "capital balance currency key is duplicated under another case"
        number = _real_amount(value)
        if number is None:
            return None, "capital balance was not a number"
        if number < 0:
            return None, "capital balance was negative"
        amounts[currency] = number
    if len(amounts) != 1:
        return None, "capital balances span more than one currency"
    currency, amount = next(iter(amounts.items()))
    if currency != "GBP":
        return None, f"capital balance currency is {currency}, not GBP"
    return amount, ""


def currency_amount_map(accounts: Any, field: str) -> dict[str, Any]:
    """Sum one field per currency.

    A missing field, a non-finite amount, or a negative amount makes the
    whole map unreadable. Those rows are not dropped and not replaced with 0.
    """

    totals: dict[str, Any] = {}
    for account in list(accounts or []):
        if not isinstance(account, dict):
            return {"_unreadable": True}
        currency = str(account.get("currency") or "").strip().upper()
        if not currency or field not in account:
            return {"_unreadable": True}
        number = nonnegative_amount(account.get(field))
        if number is None:
            return {"_unreadable": True}
        totals[currency] = float(totals.get(currency, 0.0)) + number
    return totals


def gbp_field_from_accounts(accounts: Any, field: str) -> tuple[float | None, bool]:
    """One sterling field, and whether the rows were present but unreadable.

    An empty account list is not a reading (``unreadable`` is false). A row
    that cannot be a non-negative GBP amount is unreadable.
    """

    mapped = currency_amount_map(accounts, field)
    if mapped.get("_unreadable"):
        return None, True
    amount, _reason = gbp_equity_from_balances(mapped)
    unreadable = amount is None and bool(mapped)
    return amount, unreadable


def assemble_sterling_snapshot(
    equity: float | None,
    free: float | None,
    *,
    min_profit_gbp: float,
) -> dict[str, float | None]:
    """Derived sterling fields stay null when either input is null."""

    equity_amount = None if equity is None else nonnegative_amount(equity)
    free_amount = None if free is None else nonnegative_amount(free)
    if equity_amount is None or free_amount is None:
        used = None
        budget = None
        target = None
    else:
        used = max(0.0, equity_amount - free_amount)
        budget = free_amount * 0.70
        target = (min_profit_gbp / equity_amount * 100.0) if equity_amount > 0 else 0.0
    return {
        "equity_gbp": equity_amount,
        "free_gbp": free_amount,
        "used_gbp": used,
        "budget_gbp": budget,
        "target_pct_equity": target,
    }
