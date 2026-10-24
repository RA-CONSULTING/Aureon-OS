"""Equity from one currency. Mixed units are not added together."""

from __future__ import annotations

from typing import Any


def gbp_equity_from_balances(raw: Any) -> tuple[float | None, str]:
    """One GBP amount, or null.

    ``capital_equity_gbp`` is a sterling figure. A map with two currencies
    is not added together. A single non-GBP currency is not relabeled as
    GBP. An empty map is not a zero reading.
    """

    if not isinstance(raw, dict) or not raw:
        return None, "capital balance had no currency"
    amounts: dict[str, float] = {}
    for key, value in raw.items():
        currency = str(key or "").strip().upper()
        if not currency:
            return None, "capital balance was not a number"
        try:
            amounts[currency] = float(value)
        except (TypeError, ValueError):
            return None, "capital balance was not a number"
    if len(amounts) != 1:
        return None, "capital balances span more than one currency"
    currency, amount = next(iter(amounts.items()))
    if currency != "GBP":
        return None, f"capital balance currency is {currency}, not GBP"
    return amount, ""
