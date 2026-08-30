#!/usr/bin/env python3
"""Compound King capital discipline over provider-observed account receipts.

The original standalone projection generated returns, trade counts, and win
rates. This module now records only observed daily account results. Targets are
reference policy values; they are never emitted as achieved performance.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Dict, List, Optional

from aureon.core.aureon_baton_link import link_system as _baton_link

_baton_link(__name__)


@dataclass(frozen=True)
class DayResult:
    """One provider-observed daily account result."""

    day: int
    starting_capital: float
    ending_capital: float
    return_pct: float
    trades: int
    win_rate: Optional[float]
    pdt_restricted: bool
    has_margin: bool
    status: str
    truth_status: str
    source_id: str
    source_event_id: str
    source_timestamp: str
    generated_values: bool = False


class CompoundKing:
    """Track compounding discipline using real account and execution receipts."""

    def __init__(self, starting_capital: Optional[float] = None):
        if starting_capital is not None and (
            not isfinite(float(starting_capital)) or float(starting_capital) < 0
        ):
            raise ValueError("starting_capital must be a finite observed balance")
        self.starting_capital = (
            float(starting_capital) if starting_capital is not None else None
        )
        self.current_capital = self.starting_capital
        self.target_capital = 100000.0

        # Reference policy thresholds and targets, not observed performance.
        self.margin_threshold = 2000.0
        self.pdt_threshold = 25000.0
        self.base_daily_return = 0.125
        self.margin_boost = 0.15
        self.pdt_unlocked_return = 0.20

        self.has_margin = False
        self.pdt_unlocked = False
        self.days: List[DayResult] = []
        self._source_event_ids: set[str] = set()

    def get_daily_return_target(self) -> float:
        """Return the current reference target; this is never actual P&L."""
        if self.pdt_unlocked:
            return self.pdt_unlocked_return
        if self.has_margin:
            return self.margin_boost
        return self.base_daily_return

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("source_timestamp is required")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("source_timestamp must include a timezone")
        return parsed.astimezone(timezone.utc)

    def observe_day(
        self,
        *,
        day: int,
        starting_capital: float,
        ending_capital: float,
        trades: int,
        wins: Optional[int],
        margin_enabled: bool,
        pdt_restricted: bool,
        source_id: str,
        source_event_id: str,
        source_timestamp: str,
        truth_status: str = "live",
        generated_values: bool = False,
    ) -> DayResult:
        """Record an authenticated balance/execution summary.

        ``source_event_id`` must identify a provider receipt or a durable
        read-back event. The only calculated fields are return percentage and
        win rate, both deterministically derived from the supplied receipt.
        """
        if truth_status not in {"live", "provider_observed"}:
            raise ValueError("truth_status must identify observed provider data")
        if generated_values:
            raise ValueError("generated_values must be false for account results")
        if not source_id or not source_event_id:
            raise ValueError("source_id and source_event_id are required")
        if source_event_id in self._source_event_ids:
            raise ValueError(f"duplicate source_event_id: {source_event_id}")
        self._parse_timestamp(source_timestamp)

        start = float(starting_capital)
        end = float(ending_capital)
        if not all(isfinite(value) and value >= 0 for value in (start, end)):
            raise ValueError("balances must be finite non-negative observations")
        if start <= 0:
            raise ValueError("starting_capital must be greater than zero")
        if not isinstance(trades, int) or trades < 0:
            raise ValueError("trades must be an observed non-negative integer")
        if wins is not None and (
            not isinstance(wins, int) or wins < 0 or wins > trades
        ):
            raise ValueError("wins must be between zero and trades")

        if self.current_capital is not None and abs(start - self.current_capital) > 1e-8:
            raise ValueError("starting balance does not match the prior receipt")
        if self.starting_capital is None:
            self.starting_capital = start

        self.has_margin = bool(margin_enabled)
        self.pdt_unlocked = not bool(pdt_restricted)
        status = (
            "pdt_unlocked"
            if self.pdt_unlocked
            else "margin_enabled"
            if self.has_margin
            else "building"
        )
        result = DayResult(
            day=int(day),
            starting_capital=start,
            ending_capital=end,
            return_pct=((end - start) / start) * 100.0,
            trades=trades,
            win_rate=(wins / trades) if wins is not None and trades else None,
            pdt_restricted=bool(pdt_restricted),
            has_margin=self.has_margin,
            status=status,
            truth_status=truth_status,
            source_id=source_id,
            source_event_id=source_event_id,
            source_timestamp=source_timestamp,
        )
        self.current_capital = end
        self.days.append(result)
        self._source_event_ids.add(source_event_id)
        return result

    def simulate_day(self, day: int) -> DayResult:
        """Retained API marker: generated account performance is prohibited."""
        raise RuntimeError(
            "CompoundKing no longer generates daily results; call observe_day() "
            "with an authenticated provider receipt"
        )

    def run_30_days(self) -> Dict[str, Any]:
        """Summarize the observed receipt window without creating missing days."""
        if not self.days or self.starting_capital is None or self.current_capital is None:
            return {
                "truth_status": "no_data",
                "reason": "no_provider_account_receipts",
                "generated_values": False,
                "days": [],
            }
        total_return = (
            (self.current_capital - self.starting_capital) / self.starting_capital
        ) * 100.0
        return {
            "truth_status": "real_derived",
            "generated_values": False,
            "source_event_ids": [item.source_event_id for item in self.days],
            "success": self.current_capital >= self.target_capital,
            "final_capital": self.current_capital,
            "days_observed": len(self.days),
            "total_return_pct": total_return,
            "days": [asdict(item) for item in self.days],
        }


def run_multiple_simulations(num_sims: int = 100) -> None:
    """Retained import surface; generated account-performance runs are disabled."""
    raise RuntimeError(
        "Monte Carlo account-performance generation is disabled in production"
    )


def main() -> None:
    print(
        "Compound King is ready but has no provider account receipts. "
        "Connect a live account read-back and call observe_day()."
    )


if __name__ == "__main__":
    main()
