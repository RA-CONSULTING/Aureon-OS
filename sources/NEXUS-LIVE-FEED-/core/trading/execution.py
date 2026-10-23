"""Exchange connectivity and order management helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


class ExchangeError(RuntimeError):
    """Raised when an order action fails."""


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: str
    amount: float
    price: float
    status: str


class PaperExchange:
    """A deterministic in-memory exchange used for paper trading."""

    def __init__(self, balances: Optional[Dict[str, float]] = None, fee_rate: float = 0.0005) -> None:
        self.balances = balances.copy() if balances else {"USDT": 10000.0}
        self.fee_rate = fee_rate
        self.last_order_id = 0
        self.trades: List[OrderResult] = []

    def _next_order_id(self) -> str:
        self.last_order_id += 1
        return f"paper-{self.last_order_id}"

    def fetch_balance(self) -> Dict[str, float]:
        return self.balances.copy()

    def place_market_order(self, symbol: str, side: str, amount: float, price: float) -> OrderResult:
        base, quote = symbol.split("/")
        if side not in {"buy", "sell"}:
            raise ExchangeError(f"Unsupported side {side}")
        amount = float(amount)
        price = float(price)
        fee = amount * price * self.fee_rate
        if side == "buy":
            cost = amount * price + fee
            quote_balance = self.balances.get(quote, 0.0)
            if quote_balance < cost:
                raise ExchangeError("Insufficient quote balance for paper trade")
            self.balances[quote] = quote_balance - cost
            self.balances[base] = self.balances.get(base, 0.0) + amount
        else:
            base_balance = self.balances.get(base, 0.0)
            if base_balance < amount:
                raise ExchangeError("Insufficient base balance for paper trade")
            self.balances[base] = base_balance - amount
            proceeds = amount * price - fee
            self.balances[quote] = self.balances.get(quote, 0.0) + proceeds
        order = OrderResult(self._next_order_id(), symbol, side, amount, price, "filled")
        self.trades.append(order)
        return order


class ExchangeConnector:
    """Unified API for interacting with multiple exchanges via CCXT or paper sim."""

    def __init__(
        self,
        exchange: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        password: Optional[str] = None,
        testnet: bool = False,
        paper: bool = False,
        balances: Optional[Dict[str, float]] = None,
    ) -> None:
        self.exchange_name = exchange.lower()
        self.paper = paper
        self.client = None
        self.paper_backend: Optional[PaperExchange] = None
        if paper or testnet:
            self.paper_backend = PaperExchange(balances=balances)
            self.paper = True
        else:
            try:
                import ccxt  # type: ignore
            except Exception as exc:  # pragma: no cover - optional dependency
                raise ExchangeError("ccxt is required for live trading") from exc
            if not hasattr(ccxt, self.exchange_name):
                raise ExchangeError(f"Exchange {exchange} is not supported by ccxt")
            klass = getattr(ccxt, self.exchange_name)
            params = {"apiKey": api_key or "", "secret": api_secret or ""}
            if password:
                params["password"] = password
            self.client = klass(params)
            if testnet and hasattr(self.client, "set_sandbox_mode"):
                self.client.set_sandbox_mode(True)

    def fetch_balance(self) -> Dict[str, float]:
        if self.paper_backend is not None:
            return self.paper_backend.fetch_balance()
        assert self.client is not None
        try:
            balance = self.client.fetch_balance()
        except Exception as exc:  # pragma: no cover - network call
            raise ExchangeError(str(exc)) from exc
        free = balance.get("free") or {}
        total = balance.get("total") or {}
        return {asset: float(free.get(asset, total.get(asset, 0.0))) for asset in set(total) | set(free)}

    def create_market_order(self, symbol: str, side: str, amount: float, price: Optional[float] = None) -> OrderResult:
        if self.paper_backend is not None:
            if price is None:
                raise ExchangeError("Paper trading requires explicit price")
            return self.paper_backend.place_market_order(symbol, side, amount, price)
        assert self.client is not None
        try:
            order = self.client.create_order(symbol, "market", side, amount)
        except Exception as exc:  # pragma: no cover - network call
            raise ExchangeError(str(exc)) from exc
        order_id = order.get("id", "")
        status = order.get("status", "open")
        filled = float(order.get("filled", amount))
        price_value = float(order.get("average") or price or 0.0)
        return OrderResult(order_id, symbol, side, filled, price_value, status)

    def cancel_order(self, order_id: str, symbol: str) -> None:
        if self.paper_backend is not None:
            return
        assert self.client is not None
        try:
            self.client.cancel_order(order_id, symbol)
        except Exception as exc:  # pragma: no cover - network call
            raise ExchangeError(str(exc)) from exc


__all__ = ["ExchangeConnector", "ExchangeError", "OrderResult", "PaperExchange"]
