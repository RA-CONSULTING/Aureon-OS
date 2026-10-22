"""Full trading loop assembly for the QGITA-powered bot."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional

import numpy as np

from .detection import LighthouseEvent, QGITADetector
from .execution import ExchangeConnector, OrderResult
from .portfolio import PortfolioManager
from .risk import RiskManager


@dataclass
class MarketSnapshot:
    symbol: str
    times: Iterable[float]
    features: Iterable[Iterable[float]]
    price: float
    exchange: str
    recent_prices: Optional[Iterable[float]] = None
    win_rate: float = 0.55
    reward_risk: float = 2.0


class TradingBot:
    """Coordinates detection, risk sizing and execution across exchanges."""

    def __init__(
        self,
        detector: QGITADetector,
        risk_manager: RiskManager,
        portfolio: PortfolioManager,
        connectors: Mapping[str, ExchangeConnector],
    ) -> None:
        self.detector = detector
        self.risk_manager = risk_manager
        self.portfolio = portfolio
        self.connectors = dict(connectors)

    def _event_confidence(self, event: LighthouseEvent, threshold: float) -> float:
        if threshold <= 0:
            return 0.0
        return float(np.clip(event.intensity / threshold, 0.0, 5.0))

    def evaluate_snapshot(self, snapshot: MarketSnapshot) -> Dict[str, object]:
        result = self.detector.detect(snapshot.times, snapshot.features)
        events: List[LighthouseEvent] = result["events"]  # type: ignore[assignment]
        if not events:
            return {"events": [], "orders": []}
        event = events[-1]
        confidence = self._event_confidence(event, result["threshold"])  # type: ignore[index]
        direction = "long" if event.curvature >= 0 else "short"
        plan = self.risk_manager.generate_trade_plan(
            balance=self.portfolio.available_capital(),
            price=snapshot.price,
            direction=direction,
            confidence=confidence,
            win_rate=snapshot.win_rate,
            reward_risk=snapshot.reward_risk,
            recent_prices=None if snapshot.recent_prices is None else np.asarray(list(snapshot.recent_prices), dtype=float),
        )
        if plan.size <= 0:
            return {"events": events, "orders": []}
        connector = self.connectors.get(snapshot.exchange)
        if connector is None:
            raise KeyError(f"No connector configured for {snapshot.exchange}")
        side = "buy" if plan.side == "long" else "sell"
        order = connector.create_market_order(snapshot.symbol, side, plan.size, price=snapshot.price)
        self.portfolio.record_fill(snapshot.symbol, side, order.amount, order.price or snapshot.price, plan.stop_loss, plan.take_profit)
        return {"events": events, "orders": [order]}

    def rebalance(self, prices: Dict[str, float], targets: Dict[str, float], exchange: str) -> List[OrderResult]:
        connector = self.connectors.get(exchange)
        if connector is None:
            raise KeyError(f"No connector configured for {exchange}")
        adjustments = self.portfolio.rebalance_orders(prices, targets)
        orders: List[OrderResult] = []
        for symbol, amount in adjustments.items():
            side = "buy" if amount > 0 else "sell"
            price = prices[symbol]
            order = connector.create_market_order(symbol, side, abs(amount), price=price)
            self.portfolio.record_fill(symbol, side, order.amount, price, 0.0, 0.0)
            orders.append(order)
        return orders


__all__ = ["MarketSnapshot", "TradingBot"]
