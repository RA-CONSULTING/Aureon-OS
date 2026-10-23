"""Portfolio management primitives for the trading bot."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np


@dataclass
class Position:
    symbol: str
    amount: float
    avg_price: float
    stop_loss: float
    take_profit: float

    def market_value(self, price: float) -> float:
        return self.amount * price


@dataclass
class PortfolioSnapshot:
    equity: float
    cash: float
    positions: Dict[str, Position]


class PortfolioManager:
    """Tracks allocations and provides diversification controls."""

    def __init__(
        self,
        total_capital: float,
        max_allocation_per_asset: float = 0.25,
        rebalance_threshold: float = 0.05,
    ) -> None:
        self.total_capital = float(total_capital)
        self.cash = float(total_capital)
        self.positions: Dict[str, Position] = {}
        self.max_allocation_per_asset = max_allocation_per_asset
        self.rebalance_threshold = rebalance_threshold

    def snapshot(self, prices: Dict[str, float]) -> PortfolioSnapshot:
        equity = self.cash
        for symbol, position in self.positions.items():
            price = prices.get(symbol, position.avg_price)
            equity += position.market_value(price)
        return PortfolioSnapshot(equity, self.cash, self.positions.copy())

    def record_fill(self, symbol: str, side: str, amount: float, price: float, stop: float, target: float) -> None:
        amount = float(amount)
        price = float(price)
        if side == "sell":
            amount = -amount
        existing = self.positions.get(symbol)
        if existing is None:
            self.positions[symbol] = Position(symbol, amount, price, stop, target)
        else:
            new_amount = existing.amount + amount
            if abs(new_amount) < 1e-9:
                self.positions.pop(symbol)
            else:
                if existing.amount * new_amount > 0:
                    if np.sign(amount) == np.sign(existing.amount):
                        new_notional = existing.amount * existing.avg_price + amount * price
                        new_price = new_notional / new_amount
                    else:
                        new_price = existing.avg_price
                        stop = existing.stop_loss
                        target = existing.take_profit
                else:
                    new_price = price
                self.positions[symbol] = Position(symbol, new_amount, new_price, stop, target)
        cash_delta = -amount * price
        self.cash += cash_delta

    def available_capital(self) -> float:
        return max(self.cash, 0.0)

    def allocation_for_symbol(self, symbol: str, prices: Dict[str, float]) -> float:
        snapshot = self.snapshot(prices)
        equity = max(snapshot.equity, 1e-9)
        position = self.positions.get(symbol)
        if position is None:
            return 0.0
        price = prices.get(symbol, position.avg_price)
        return position.market_value(price) / equity

    def allowable_position_value(self, symbol: str, prices: Dict[str, float]) -> float:
        snapshot = self.snapshot(prices)
        max_value = snapshot.equity * self.max_allocation_per_asset
        current_value = self.positions.get(symbol).market_value(prices.get(symbol, 0.0)) if symbol in self.positions else 0.0
        return max(max_value - current_value, 0.0)

    def rebalance_orders(self, prices: Dict[str, float], target_allocations: Dict[str, float]) -> Dict[str, float]:
        orders: Dict[str, float] = {}
        snapshot = self.snapshot(prices)
        for symbol, target_weight in target_allocations.items():
            current_weight = self.allocation_for_symbol(symbol, prices)
            deviation = target_weight - current_weight
            if abs(deviation) < self.rebalance_threshold:
                continue
            desired_value = snapshot.equity * target_weight
            current_value = self.positions.get(symbol).market_value(prices[symbol]) if symbol in self.positions else 0.0
            delta_value = desired_value - current_value
            orders[symbol] = delta_value / prices[symbol]
        return orders


__all__ = ["PortfolioManager", "PortfolioSnapshot", "Position"]
