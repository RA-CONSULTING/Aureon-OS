"""Risk management utilities for the automated trading bot."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass(frozen=True)
class TradePlan:
    """Container for a proposed trade configuration."""

    side: str
    size: float
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float


class RiskManager:
    """Implements Kelly-based position sizing and guardrails."""

    def __init__(
        self,
        max_risk_per_trade: float = 0.02,
        volatility_lookback: int = 20,
        default_rr: float = 2.0,
        min_confidence: float = 0.1,
        max_leverage: float = 3.0,
    ) -> None:
        self.max_risk_per_trade = max_risk_per_trade
        self.volatility_lookback = volatility_lookback
        self.default_rr = default_rr
        self.min_confidence = min_confidence
        self.max_leverage = max_leverage

    @staticmethod
    def kelly_fraction(win_rate: float, reward_risk: float) -> float:
        win_rate = np.clip(win_rate, 1e-6, 1 - 1e-6)
        reward_risk = max(reward_risk, 1e-6)
        edge = win_rate * reward_risk - (1 - win_rate)
        return max(edge / reward_risk, 0.0)

    @staticmethod
    def _annualized_volatility(prices: np.ndarray) -> float:
        if prices.size < 2:
            return 0.0
        returns = np.diff(np.log(prices))
        if returns.size == 0:
            return 0.0
        return float(np.std(returns) * np.sqrt(252))

    def compute_stop_targets(
        self,
        price: float,
        direction: str,
        reward_risk: float | None = None,
        volatility: float | None = None,
    ) -> Tuple[float, float]:
        reward_risk = reward_risk or self.default_rr
        if volatility is None or not np.isfinite(volatility) or volatility <= 0:
            pct_risk = 0.01
        else:
            pct_risk = np.clip(volatility / 10.0, 0.005, 0.05)
        if direction == "long":
            stop = price * (1 - pct_risk)
            target = price * (1 + pct_risk * reward_risk)
        else:
            stop = price * (1 + pct_risk)
            target = price * (1 - pct_risk * reward_risk)
        return stop, target

    def generate_trade_plan(
        self,
        balance: float,
        price: float,
        direction: str,
        confidence: float,
        win_rate: float,
        reward_risk: float | None = None,
        recent_prices: np.ndarray | None = None,
    ) -> TradePlan:
        if confidence < self.min_confidence:
            return TradePlan(direction, 0.0, price, price, price, confidence)
        reward_risk = reward_risk or self.default_rr
        kelly = self.kelly_fraction(win_rate, reward_risk)
        risk_fraction = min(self.max_risk_per_trade, kelly * confidence)
        risk_fraction = min(risk_fraction, self.max_leverage * self.max_risk_per_trade)
        if risk_fraction <= 0:
            return TradePlan(direction, 0.0, price, price, price, confidence)
        volatility = None
        if recent_prices is not None and recent_prices.size:
            prices = np.asarray(recent_prices, dtype=float)[-self.volatility_lookback :]
            volatility = self._annualized_volatility(prices)
        stop, target = self.compute_stop_targets(price, direction, reward_risk, volatility)
        risk_per_unit = abs(price - stop)
        if risk_per_unit <= 0:
            return TradePlan(direction, 0.0, price, price, price, confidence)
        capital_at_risk = balance * risk_fraction
        raw_size = capital_at_risk / risk_per_unit
        max_affordable = balance * self.max_leverage / price
        size = float(np.clip(raw_size, 0.0, max_affordable))
        return TradePlan(direction, size, price, stop, target, confidence)


__all__ = ["RiskManager", "TradePlan"]
