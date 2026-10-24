"""Passive observations for the Orca dashboard.

The dashboard imports this module at load time. The function reads attributes
already on the clients. It does not open a new order and it does not place one.
"""

from __future__ import annotations

from typing import Any


def build_orca_reader_observations(alpaca: Any, kraken: Any, systems_status: Any) -> dict[str, Any]:
    """Project the readers the dashboard already holds."""

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
