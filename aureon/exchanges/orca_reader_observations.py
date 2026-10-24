"""Observations for the Orca dashboard.

``build_orca_reader_observations`` calls ``get_account_balance`` on the
clients the dashboard already holds. That call is an authenticated read.
It does not place an order. Balance maps are not summed into equity.
Kraken equity is one USD total, or none. Any other client uses
``get_account().equity``, or none, so USD cash is not added to a
position quantity.
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


def _account_equity(client: Any) -> float | None:
    """Equity from ``get_account()``. A balance map is not summed.

    ``get_account`` is an authenticated read. It does not place an order.
    Missing equity stays null, including when the account object has no
    ``equity`` or ``portfolio_value``.
    """

    if not hasattr(client, "get_account"):
        return None
    try:
        account = client.get_account()
    except Exception:
        return None
    if isinstance(account, dict):
        equity = account.get("equity", account.get("portfolio_value"))
    else:
        equity = getattr(account, "equity", None)
        if equity is None:
            equity = getattr(account, "portfolio_value", None)
    if equity is None or equity == "":
        return None
    try:
        return float(equity)
    except (TypeError, ValueError):
        return None


def build_orca_reader_observations(alpaca: Any, kraken: Any, systems_status: Any) -> dict[str, Any]:
    """Read account balances from the clients this dashboard holds.

    ``get_account_balance`` and ``get_account`` are authenticated reads.
    This function does not place an order. No balance map is summed.
    Kraken equity stays null unless one USD total is present. Alpaca and
    any other client use ``get_account().equity``, or null.
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
        if name == "kraken":
            equity = _kraken_usd_equity(balances, client)
        else:
            equity = _account_equity(client)
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
