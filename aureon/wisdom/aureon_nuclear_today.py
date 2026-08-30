"""Nuclear Today: high-tempo opportunity observer over live market receipts.

This module does not generate prices, volume, momentum, fills, or P&L. It emits
order intentions derived from fresh provider observations. Submission and
account mutation belong to an authenticated execution adapter and require the
owner-controlled execution workflow.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from aureon.core.aureon_baton_link import link_system as _baton_link

_baton_link(__name__)
logger = logging.getLogger(__name__)


class NuclearConfig:
    """Reference strategy settings; these are not observed performance."""

    MAX_LEVERAGE = 20
    MIN_PROFIT_PCT = 0.0005
    ENTRY_CONFIDENCE = 0.30
    MAX_CONCURRENT_POSITIONS = 50
    POSITION_SIZE_PCT = 0.90
    TAKE_PROFIT_PCT = 0.003
    STOP_LOSS_PCT = 0.002
    MAX_OBSERVATION_AGE_SECONDS = 30.0


@dataclass(frozen=True)
class MarketObservation:
    symbol: str
    exchange: str
    price: float
    volume: float
    momentum: float
    source_id: str
    source_event_id: str
    source_timestamp: str
    truth_status: str = "live"
    generated_values: bool = False


class NuclearDayTrader:
    """Observe fresh opportunities and form auditable order intentions."""

    def __init__(self, starting_capital: Optional[float] = None):
        if starting_capital is not None and (
            not math.isfinite(float(starting_capital)) or float(starting_capital) < 0
        ):
            raise ValueError("starting_capital must be an observed finite balance")
        self.config = NuclearConfig()
        self.starting_capital = (
            float(starting_capital) if starting_capital is not None else None
        )
        self.current_capital = self.starting_capital
        self.observations: Dict[str, MarketObservation] = {}
        self.order_intents: List[Dict[str, Any]] = []
        self.execution_receipts: List[Dict[str, Any]] = []

    @staticmethod
    def _timestamp(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("source_timestamp must include a timezone")
        return parsed.astimezone(timezone.utc)

    def ingest_market_observation(self, payload: Dict[str, Any]) -> MarketObservation:
        required = (
            "symbol",
            "exchange",
            "price",
            "volume",
            "momentum",
            "source_id",
            "source_event_id",
            "source_timestamp",
            "truth_status",
            "generated_values",
        )
        missing = [name for name in required if payload.get(name) is None]
        if missing:
            raise ValueError(f"missing observation fields: {', '.join(missing)}")
        if payload["truth_status"] not in {"live", "provider_observed"}:
            raise ValueError("market observation must be provider-observed")
        if payload["generated_values"] is not False:
            raise ValueError("generated market observations are prohibited")
        timestamp = self._timestamp(str(payload["source_timestamp"]))
        age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        if age < -30 or age > self.config.MAX_OBSERVATION_AGE_SECONDS:
            raise ValueError(f"stale market observation: age_seconds={age:.3f}")
        price = float(payload["price"])
        volume = float(payload["volume"])
        momentum = float(payload["momentum"])
        if not all(math.isfinite(value) for value in (price, volume, momentum)):
            raise ValueError("market metrics must be finite")
        if price <= 0 or volume < 0:
            raise ValueError("price must be positive and volume non-negative")
        observation = MarketObservation(
            symbol=str(payload["symbol"]),
            exchange=str(payload["exchange"]),
            price=price,
            volume=volume,
            momentum=momentum,
            source_id=str(payload["source_id"]),
            source_event_id=str(payload["source_event_id"]),
            source_timestamp=str(payload["source_timestamp"]),
            truth_status=str(payload["truth_status"]),
        )
        self.observations[observation.symbol] = observation
        return observation

    async def scan_nuclear_opportunities(self) -> List[Dict[str, Any]]:
        """Derive candidates only from the current fresh observation set."""
        opportunities: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        for observation in self.observations.values():
            age = (now - self._timestamp(observation.source_timestamp)).total_seconds()
            if age > self.config.MAX_OBSERVATION_AGE_SECONDS:
                continue
            if abs(observation.momentum) < self.config.MIN_PROFIT_PCT:
                continue
            opportunities.append(
                {
                    "symbol": observation.symbol,
                    "exchange": observation.exchange,
                    "momentum": observation.momentum,
                    "price": observation.price,
                    "direction": "BUY" if observation.momentum > 0 else "SELL",
                    "confidence": min(
                        0.99,
                        abs(observation.momentum) / self.config.MIN_PROFIT_PCT,
                    ),
                    "volume": observation.volume,
                    "truth_status": "real_derived",
                    "generated_values": False,
                    "source_id": observation.source_id,
                    "source_event_id": observation.source_event_id,
                    "source_timestamp": observation.source_timestamp,
                }
            )
        return opportunities

    def can_trade(self) -> bool:
        """Report whether an observed balance is available for intent sizing."""
        return self.current_capital is not None and self.current_capital > 0

    async def execute_nuclear_trade(self, opportunity: Dict[str, Any]) -> bool:
        """Create an intention; never claim exchange execution."""
        if not self.can_trade():
            return False
        required = (
            "symbol",
            "exchange",
            "direction",
            "price",
            "source_event_id",
            "source_timestamp",
        )
        if any(opportunity.get(name) is None for name in required):
            return False
        canonical = json.dumps(
            {name: opportunity[name] for name in required},
            sort_keys=True,
            separators=(",", ":"),
        )
        intent = {
            "intent_id": "nuclear_intent_"
            + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "symbol": opportunity["symbol"],
            "exchange": opportunity["exchange"],
            "direction": opportunity["direction"],
            "reference_price": float(opportunity["price"]),
            "truth_status": "real_derived",
            "generated_values": False,
            "source_event_id": opportunity["source_event_id"],
            "source_timestamp": opportunity["source_timestamp"],
            "execution_status": "not_submitted",
        }
        self.order_intents.append(intent)
        return True

    async def manage_positions_nuclear(
        self, execution_receipts: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Adopt provider execution receipts; absent receipts remain no_data."""
        if not execution_receipts:
            return {
                "truth_status": "no_data",
                "generated_values": False,
                "reason": "no_provider_execution_receipts",
            }
        adopted = 0
        for receipt in execution_receipts:
            required = (
                "source_id",
                "source_event_id",
                "source_timestamp",
                "truth_status",
                "generated_values",
                "realized_pnl",
                "balance_after",
            )
            if any(receipt.get(name) is None for name in required):
                continue
            if (
                receipt["truth_status"] not in {"live", "provider_observed"}
                or receipt["generated_values"] is not False
            ):
                continue
            self._timestamp(str(receipt["source_timestamp"]))
            balance = float(receipt["balance_after"])
            if not math.isfinite(balance) or balance < 0:
                continue
            self.current_capital = balance
            self.execution_receipts.append(dict(receipt))
            adopted += 1
        return {
            "truth_status": "provider_observed" if adopted else "no_data",
            "generated_values": False,
            "adopted_receipt_count": adopted,
        }

    def calculate_required_performance(self) -> Dict[str, Any]:
        if self.starting_capital is None or self.current_capital is None:
            return {
                "truth_status": "no_data",
                "generated_values": False,
                "reason": "no_provider_balance",
            }
        return {
            "truth_status": "real_derived",
            "generated_values": False,
            "starting_capital": self.starting_capital,
            "current_capital": self.current_capital,
            "return_pct": (
                (self.current_capital - self.starting_capital)
                / self.starting_capital
                * 100.0
            ),
            "source_event_ids": [
                receipt["source_event_id"] for receipt in self.execution_receipts
            ],
        }

    def print_nuclear_stats(self) -> None:
        logger.info("%s", self.calculate_required_performance())


async def main() -> None:
    trader = NuclearDayTrader()
    result = await trader.scan_nuclear_opportunities()
    print(
        {
            "truth_status": "no_data",
            "generated_values": False,
            "opportunities": result,
            "reason": "no_live_market_observations_ingested",
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
