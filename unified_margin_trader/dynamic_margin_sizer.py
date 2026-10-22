"""Dynamic collateral-aware margin sizing for Kraken spot margin.

The sizing model is intentionally conservative:
- live Kraken free margin is the hard source of truth;
- projected margin level must stay above the configured safety floor;
- tiny accounts can still trade if the pair minimum fits inside that live
  free margin and the projected margin-level gate passes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _first_number(data: Mapping[str, Any], *keys: str) -> float:
    for key in keys:
        if key in data:
            return _as_float(data.get(key))
    return 0.0


@dataclass(frozen=True)
class MarginCapitalSnapshot:
    """Normalized view of Kraken /private/TradeBalance values."""

    equity: float
    free_margin: float
    margin_used: float
    unrealized_pnl: float = 0.0
    margin_level: float = 0.0
    trade_balance: float = 0.0

    @classmethod
    def from_trade_balance(cls, trade_balance: Mapping[str, Any]) -> "MarginCapitalSnapshot":
        equity = _first_number(trade_balance, "equity", "equity_value", "e")
        trade_bal = _first_number(trade_balance, "trade_balance", "tb")
        margin_used = _first_number(trade_balance, "margin_amount", "margin_used", "m")
        unrealized = _first_number(trade_balance, "unrealized_pnl", "n")
        margin_level = _first_number(trade_balance, "margin_level", "ml")

        has_free_margin = any(key in trade_balance for key in ("free_margin", "margin_free", "mf"))
        free_margin = _first_number(trade_balance, "free_margin", "margin_free", "mf")

        if equity <= 0 and trade_bal > 0:
            equity = trade_bal
        if not has_free_margin:
            free_margin = max(0.0, equity - margin_used)

        return cls(
            equity=max(0.0, equity),
            free_margin=max(0.0, free_margin),
            margin_used=max(0.0, margin_used),
            unrealized_pnl=unrealized,
            margin_level=max(0.0, margin_level),
            trade_balance=max(0.0, trade_bal),
        )


@dataclass(frozen=True)
class DynamicMarginConfig:
    max_free_margin_fraction: float = 0.70
    tiny_account_max_free_margin_fraction: float = 0.90
    tiny_account_equity_usd: float = 50.0
    entry_min_margin_pct: float = 250.0
    min_free_margin_usd: float = 5.0
    fallback_min_notional_usd: float = 5.0
    min_profit_target_usd: float = 0.05
    target_equity_fraction: float = 0.01


@dataclass(frozen=True)
class PositionSizePlan:
    approved: bool
    reason: str
    volume: float = 0.0
    notional: float = 0.0
    leverage: int = 1
    required_margin: float = 0.0
    free_margin_after: float = 0.0
    projected_margin_pct: float = 0.0
    max_safe_notional: float = 0.0
    min_notional: float = 0.0
    profit_target_usd: float = 0.0
    target_pct_equity: float = 0.0


class DynamicMarginSizer:
    """Plan Kraken margin position size from live free margin and equity."""

    def __init__(self, config: DynamicMarginConfig | None = None):
        self.config = config or DynamicMarginConfig()

    def profit_target_usd(self, equity: float, max_target_usd: float) -> float:
        """Scale the profit target down for tiny accounts and up as equity grows."""
        equity = max(0.0, float(equity or 0.0))
        max_target = max(self.config.min_profit_target_usd, float(max_target_usd or 0.0))
        if equity <= 0:
            return self.config.min_profit_target_usd
        target = equity * self.config.target_equity_fraction
        return max(self.config.min_profit_target_usd, min(max_target, target))

    def pair_min_notional(self, price: float, ordermin: float, costmin: float = 0.0) -> float:
        price = max(0.0, float(price or 0.0))
        ordermin = max(0.0, float(ordermin or 0.0))
        costmin = max(0.0, float(costmin or 0.0))
        return max(costmin, ordermin * price, self.config.fallback_min_notional_usd)

    def max_safe_notional(
        self,
        snapshot: MarginCapitalSnapshot,
        leverage: float,
        free_margin_fraction: float,
    ) -> float:
        if snapshot.equity <= 0 or leverage <= 0:
            return 0.0
        max_margin_for_level = snapshot.equity * 100.0 / self.config.entry_min_margin_pct
        additional_margin_for_level = max_margin_for_level - snapshot.margin_used
        if additional_margin_for_level <= 0:
            return 0.0
        level_limited = additional_margin_for_level * leverage
        free_limited = snapshot.free_margin * max(0.0, min(1.0, free_margin_fraction)) * leverage
        return max(0.0, min(level_limited, free_limited))

    def plan(
        self,
        snapshot: MarginCapitalSnapshot,
        *,
        price: float,
        ordermin: float,
        lot_decimals: int,
        leverage: int,
        max_profit_target_usd: float,
        costmin: float = 0.0,
        split_slot: bool = False,
    ) -> PositionSizePlan:
        price = float(price or 0.0)
        leverage = int(leverage or 1)
        lot_decimals = max(0, int(lot_decimals or 0))
        slot_fraction = 0.5 if split_slot else 1.0

        target = self.profit_target_usd(snapshot.equity, max_profit_target_usd)
        target_pct = (target / snapshot.equity * 100.0) if snapshot.equity > 0 else 0.0
        min_notional = self.pair_min_notional(price, ordermin, costmin)

        if price <= 0:
            return PositionSizePlan(False, "missing live price", min_notional=min_notional, profit_target_usd=target)
        if leverage <= 0:
            return PositionSizePlan(False, "invalid leverage", min_notional=min_notional, profit_target_usd=target)
        if snapshot.free_margin < self.config.min_free_margin_usd:
            return PositionSizePlan(
                False,
                f"free margin ${snapshot.free_margin:.2f} < minimum ${self.config.min_free_margin_usd:.2f}",
                min_notional=min_notional,
                profit_target_usd=target,
                target_pct_equity=target_pct,
            )

        base_fraction = (
            self.config.tiny_account_max_free_margin_fraction
            if snapshot.equity <= self.config.tiny_account_equity_usd
            else self.config.max_free_margin_fraction
        )
        desired_margin_fraction = base_fraction * slot_fraction
        hard_margin_fraction = 1.0 * slot_fraction

        requested_notional = snapshot.free_margin * desired_margin_fraction * leverage
        max_safe = self.max_safe_notional(snapshot, leverage, hard_margin_fraction)
        if max_safe <= 0:
            return PositionSizePlan(
                False,
                "projected margin level has no safe room",
                max_safe_notional=max_safe,
                min_notional=min_notional,
                profit_target_usd=target,
                target_pct_equity=target_pct,
            )

        notional = min(requested_notional, max_safe)
        if notional < min_notional:
            if min_notional <= max_safe:
                notional = min_notional
            else:
                return PositionSizePlan(
                    False,
                    f"safe notional ${max_safe:.2f} < pair minimum ${min_notional:.2f}",
                    max_safe_notional=max_safe,
                    min_notional=min_notional,
                    profit_target_usd=target,
                    target_pct_equity=target_pct,
                )

        volume = self._round_down(notional / price, lot_decimals)
        if volume < ordermin:
            volume = self._round_up(ordermin, lot_decimals)
        actual_notional = volume * price
        if actual_notional < min_notional:
            volume = self._round_up(min_notional / price, lot_decimals)
            actual_notional = volume * price

        required_margin = actual_notional / leverage
        projected_margin_pct = self._projected_margin_pct(snapshot, required_margin)
        free_after = snapshot.free_margin - required_margin

        if required_margin > snapshot.free_margin * hard_margin_fraction + 1e-9:
            return PositionSizePlan(
                False,
                "pair minimum requires more free margin than this slot can use",
                volume=volume,
                notional=actual_notional,
                leverage=leverage,
                required_margin=required_margin,
                free_margin_after=free_after,
                projected_margin_pct=projected_margin_pct,
                max_safe_notional=max_safe,
                min_notional=min_notional,
                profit_target_usd=target,
                target_pct_equity=target_pct,
            )
        if actual_notional > max_safe + max(0.01, price * 10 ** -lot_decimals):
            return PositionSizePlan(
                False,
                "rounded volume exceeds safe notional",
                volume=volume,
                notional=actual_notional,
                leverage=leverage,
                required_margin=required_margin,
                free_margin_after=free_after,
                projected_margin_pct=projected_margin_pct,
                max_safe_notional=max_safe,
                min_notional=min_notional,
                profit_target_usd=target,
                target_pct_equity=target_pct,
            )
        if projected_margin_pct < self.config.entry_min_margin_pct:
            return PositionSizePlan(
                False,
                f"projected margin {projected_margin_pct:.1f}% < required {self.config.entry_min_margin_pct:.0f}%",
                volume=volume,
                notional=actual_notional,
                leverage=leverage,
                required_margin=required_margin,
                free_margin_after=free_after,
                projected_margin_pct=projected_margin_pct,
                max_safe_notional=max_safe,
                min_notional=min_notional,
                profit_target_usd=target,
                target_pct_equity=target_pct,
            )

        return PositionSizePlan(
            True,
            "approved",
            volume=volume,
            notional=actual_notional,
            leverage=leverage,
            required_margin=required_margin,
            free_margin_after=free_after,
            projected_margin_pct=projected_margin_pct,
            max_safe_notional=max_safe,
            min_notional=min_notional,
            profit_target_usd=target,
            target_pct_equity=target_pct,
        )

    @staticmethod
    def _projected_margin_pct(snapshot: MarginCapitalSnapshot, required_margin: float) -> float:
        total_margin = snapshot.margin_used + required_margin
        if snapshot.equity <= 0 or total_margin <= 0:
            return 0.0
        return snapshot.equity / total_margin * 100.0

    @staticmethod
    def _round_down(value: float, decimals: int) -> float:
        factor = 10 ** decimals
        return math.floor(max(0.0, value) * factor) / factor

    @staticmethod
    def _round_up(value: float, decimals: int) -> float:
        factor = 10 ** decimals
        return math.ceil(max(0.0, value) * factor) / factor
