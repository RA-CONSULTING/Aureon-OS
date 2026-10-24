"""Observations for the Orca dashboard.

``build_orca_reader_observations`` calls ``get_account_balance`` on the
clients the dashboard already holds. That call is an authenticated read.
It does not place an order. Kraken amounts are different units, so they
are not added together into an equity figure.
"""

from __future__ import annotations

from typing import Any


def _kraken_usd_equity(balances: dict[str, Any], client: Any) -> float | None:
    sources = [balances]
    client_fields = getattr(client, "__dict__", None)
    if isinstance(client_fields, dict):
        sources.append(client_fields)
    for source in sources:
        for key in ("equity_usd", "portfolio_value_usd", "total_usd_estimate"):
            if key not in source:
                continue
            try:
                return float(source[key])
            except (TypeError, ValueError):
                return None
    return None


def build_orca_reader_observations(alpaca: Any, kraken: Any, systems_status: Any) -> dict[str, Any]:
    """Read account balances from the clients this dashboard holds.

    ``get_account_balance`` is an authenticated read. This function does not
    place an order. Kraken equity stays null unless one USD total is present.
    """

    def one(name: str, client: Any) -> dict[str, Any]:
        if client is None:
            return {"name": name, "alive": False, "error": "not loaded", "balances": {}, "equity": None, "live": False}
        error = str(getattr(client, "last_error", "") or getattr(client, "init_error", "") or "")
        balances: dict[str, Any] = {}
        try:
            raw = client.get_account_balance() if hasattr(client, "get_account_balance") else {}
            if isinstance(raw, dict) and "balances" not in raw:
                balances = {str(key): value for key, value in raw.items() if not str(key).startswith("_")}
            elif hasattr(raw, "balances") and isinstance(raw.balances, dict):
                balances = dict(raw.balances)
        except Exception as exc:
            error = error or str(exc)
        equity = None
        if name == "kraken":
            equity = _kraken_usd_equity(balances, client)
        else:
            try:
                if balances:
                    equity = float(sum(float(value) for value in balances.values()))
            except (TypeError, ValueError):
                equity = None
        if name == "binance" and "region" in error.lower():
            error = "region blocked"
        live = bool(equity) and not error
        return {
            "name": name,
            "alive": client is not None and not error,
            "error": error,
            "balances": balances,
            "equity": equity,
            "live": live,
        }

    return {
        "ok": True,
        "live_trading": False,
        "orders": 0,
        "alpaca": one("alpaca", alpaca),
        "kraken": one("kraken", kraken),
        "systems": systems_status if isinstance(systems_status, dict) else {},
    }
