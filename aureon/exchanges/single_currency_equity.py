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


def gbp_equity_from_balances(raw: Any) -> tuple[float | None, str]:
    """One GBP amount, or null.

    ``capital_equity_gbp`` is a sterling figure. A map with two currencies
    is not added together. A single non-GBP currency is not relabeled as
    GBP. An empty map is not a zero reading. Two keys that are the same
    currency in different case are not collapsed, and a value that is not
    a finite number is not coerced.
    """

    if not isinstance(raw, dict) or not raw:
        return None, "capital balance had no currency"
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
        amounts[currency] = number
    if len(amounts) != 1:
        return None, "capital balances span more than one currency"
    currency, amount = next(iter(amounts.items()))
    if currency != "GBP":
        return None, f"capital balance currency is {currency}, not GBP"
    return amount, ""
