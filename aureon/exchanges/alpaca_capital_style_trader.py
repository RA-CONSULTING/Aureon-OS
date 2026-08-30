#!/usr/bin/env python3
"""
Alpaca trader that mirrors the Capital CFD trader lifecycle for stock trading.
"""

from __future__ import annotations

import logging
import math
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_SUPPRESS_IMPORT_SIDE_EFFECTS = os.getenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

AlpacaClient = None  # type: ignore
AureonBrain = None  # type: ignore
get_unified_puller = None  # type: ignore
UnifiedDecisionEngine = None  # type: ignore
SignalInput = None  # type: ignore
CoordinationInput = None  # type: ignore
DecisionType = None  # type: ignore
DecisionReason = None  # type: ignore
AutonomousOrchestrator = None  # type: ignore
get_timeline_oracle = None  # type: ignore
HarmonicWaveFusion = None  # type: ignore
Thought = None  # type: ignore
get_thought_bus = None  # type: ignore
HAS_UNIFIED_REGISTRY = False
HAS_UNIFIED_DECISION = False
HAS_ALPACA_ORCHESTRATOR = False
HAS_TIMELINE_ORACLE = False
HAS_HARMONIC_FUSION = False
HAS_THOUGHT_BUS = False

if not _SUPPRESS_IMPORT_SIDE_EFFECTS:
    try:
        from aureon.exchanges.alpaca_client import AlpacaClient
    except ImportError:
        pass

    try:
        from aureon.intelligence.aureon_brain import AureonBrain
    except Exception:
        pass

    try:
        from aureon.intelligence.aureon_unified_intelligence_registry import get_unified_puller
        HAS_UNIFIED_REGISTRY = True
    except Exception:
        pass

    try:
        from aureon.intelligence.aureon_unified_decision_engine import (
            UnifiedDecisionEngine,
            SignalInput,
            CoordinationInput,
            DecisionType,
            DecisionReason,
        )
        HAS_UNIFIED_DECISION = True
    except Exception:
        pass

    try:
        from aureon.autonomous.autonomous_trading_orchestrator import AutonomousOrchestrator
        HAS_ALPACA_ORCHESTRATOR = True
    except Exception:
        pass

    try:
        from aureon.intelligence.aureon_timeline_oracle import get_timeline_oracle
        HAS_TIMELINE_ORACLE = True
    except Exception:
        pass

    try:
        from aureon.harmonic.aureon_harmonic_fusion import HarmonicWaveFusion
        HAS_HARMONIC_FUSION = True
    except Exception:
        pass

    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus
        HAS_THOUGHT_BUS = True
    except Exception:
        pass


logger = logging.getLogger(__name__)

ALPACA_CAPITAL_UNIVERSE: Dict[str, Dict[str, float]] = {
    "AAPL": {"tp_pct": 0.80, "sl_pct": 0.45, "size": 1, "max_spread_pct": 0.20, "momentum_threshold": 0.20},
    "TSLA": {"tp_pct": 1.00, "sl_pct": 0.60, "size": 1, "max_spread_pct": 0.30, "momentum_threshold": 0.30},
    "NVDA": {"tp_pct": 0.90, "sl_pct": 0.55, "size": 1, "max_spread_pct": 0.25, "momentum_threshold": 0.25},
    "AMZN": {"tp_pct": 0.80, "sl_pct": 0.45, "size": 1, "max_spread_pct": 0.20, "momentum_threshold": 0.20},
    "MSFT": {"tp_pct": 0.75, "sl_pct": 0.40, "size": 1, "max_spread_pct": 0.15, "momentum_threshold": 0.18},
    "META": {"tp_pct": 0.85, "sl_pct": 0.50, "size": 1, "max_spread_pct": 0.20, "momentum_threshold": 0.22},
    "AMD": {"tp_pct": 0.90, "sl_pct": 0.55, "size": 1, "max_spread_pct": 0.25, "momentum_threshold": 0.25},
    "SPY": {"tp_pct": 0.35, "sl_pct": 0.20, "size": 1, "max_spread_pct": 0.08, "momentum_threshold": 0.10},
    "QQQ": {"tp_pct": 0.45, "sl_pct": 0.25, "size": 1, "max_spread_pct": 0.10, "momentum_threshold": 0.12},
}
ALPACA_UNIVERSE_LIMIT = max(25, int(float(os.getenv("ALPACA_UNIVERSE_LIMIT", "250") or 250)))
ALPACA_SCAN_WINDOW = max(10, int(float(os.getenv("ALPACA_SCAN_WINDOW", "40") or 40)))
ALPACA_MIN_PRICE = max(0.1, float(os.getenv("ALPACA_MIN_PRICE", "2.0") or 2.0))
ALPACA_MIN_DOLLAR_VOLUME = max(10000.0, float(os.getenv("ALPACA_MIN_DOLLAR_VOLUME", "250000") or 250000))
ALPACA_INTEL_TOP_N = max(1, int(float(os.getenv("ALPACA_INTEL_TOP_N", "5") or 5)))

ALPACA_SELF_CONFIDENCE_ENABLED = os.getenv("ALPACA_SELF_CONFIDENCE_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
ALPACA_SELF_CONFIDENCE_MAX_BOOST = max(0.0, float(os.getenv("ALPACA_SELF_CONFIDENCE_MAX_BOOST", "0.08") or 0.08))
ALPACA_SELF_CONFIDENCE_MIN_VALIDATE_SECS = max(0.5, float(os.getenv("ALPACA_SELF_CONFIDENCE_MIN_VALIDATE_SECS", "2.5") or 2.5))
ALPACA_MIN_TARGET_USD = max(0.01, float(os.getenv("ALPACA_MIN_TARGET_USD", "0.01") or 0.01))

MAX_POSITIONS = 2
SCAN_INTERVAL_SECS = 5.0
MONITOR_INTERVAL_SECS = 2.0
ALPACA_QUOTE_TTL_SECS = max(1.0, float(os.getenv("ALPACA_QUOTE_TTL_SECS", "120") or 120))
ALPACA_BAR_TTL_SECS = max(60.0, float(os.getenv("ALPACA_BAR_TTL_SECS", "604800") or 604800))
ALPACA_FILL_TTL_SECS = max(60.0, float(os.getenv("ALPACA_FILL_TTL_SECS", "900") or 900))
ALPACA_PROVIDER_FUTURE_SKEW_SECS = 300.0


def _finite_number(value: Any, *, positive: bool = False, nonnegative: bool = False) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0:
        return None
    if nonnegative and number < 0:
        return None
    return number


def _provider_timestamp(value: Any) -> Optional[float]:
    numeric = _finite_number(value, positive=True)
    if numeric is not None:
        while numeric > 10_000_000_000:
            numeric /= 1000.0
        return numeric
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    timestamp = parsed.timestamp()
    return timestamp if math.isfinite(timestamp) and timestamp > 0 else None


def _is_fresh_provider_time(timestamp: Optional[float], ttl_seconds: float, now: Optional[float] = None) -> bool:
    if timestamp is None:
        return False
    observed_at = time.time() if now is None else float(now)
    age = observed_at - float(timestamp)
    return -ALPACA_PROVIDER_FUTURE_SKEW_SECS <= age <= float(ttl_seconds)


def _format_observed(value: Any, format_spec: str) -> str:
    number = _finite_number(value)
    return format(number, format_spec) if number is not None else "NO_DATA"


@dataclass
class AlpacaShadowTrade:
    symbol: str
    direction: str
    size: float
    entry_price: float
    target_move_pct: float
    score: float
    opened_at: float = field(default_factory=time.time)
    current_price: float = 0.0
    peak_move_pct: float = 0.0
    validated: bool = False
    validation_time: float = 0.0

    @property
    def age_secs(self) -> float:
        return time.time() - self.opened_at

    @property
    def current_move_pct(self) -> float:
        price = self.current_price if self.current_price > 0 else self.entry_price
        if self.entry_price <= 0 or price <= 0:
            return 0.0
        if self.direction == "BUY":
            return ((price - self.entry_price) / self.entry_price) * 100.0
        return ((self.entry_price - price) / self.entry_price) * 100.0

    def update(self, price: float, validation_window_secs: float) -> None:
        if price <= 0:
            return
        self.current_price = price
        move_pct = self.current_move_pct
        self.peak_move_pct = max(self.peak_move_pct, move_pct)
        if not self.validated and move_pct >= self.target_move_pct and self.age_secs >= max(0.0, float(validation_window_secs or 0.0)):
            self.validated = True
            self.validation_time = time.time()


@dataclass
class AlpacaMomentumPosition:
    symbol: str
    order_id: str
    direction: str
    qty: float
    entry_price: float
    tp_price: float
    sl_price: float
    opened_at: Optional[float] = field(default_factory=time.time)
    current_price: Optional[float] = None
    entry_source_id: str = ""
    entry_source_timestamp: Optional[float] = None
    entry_received_at: Optional[float] = None
    entry_commission_usd: Optional[float] = None
    entry_fee_complete: bool = False
    entry_reference_price: Optional[float] = None
    entry_spread_usd: Optional[float] = None
    generated_values: bool = False
    eligible_for_learning: bool = False

    @property
    def age_secs(self) -> Optional[float]:
        if self.opened_at is None:
            return None
        return max(0.0, time.time() - self.opened_at)

    @property
    def pnl_pct(self) -> float:
        price = self.current_price if self.current_price is not None and self.current_price > 0 else self.entry_price
        if self.entry_price <= 0 or price <= 0:
            return 0.0
        if self.direction == "BUY":
            return ((price - self.entry_price) / self.entry_price) * 100.0
        return ((self.entry_price - price) / self.entry_price) * 100.0

    def one_line(self) -> str:
        return (
            f"    LIVE   {self.direction:4} {self.symbol:5} [stock] "
            f"entry:{self.entry_price:.4f} now:{self.current_price or self.entry_price:.4f} "
            f"pnl:{self.pnl_pct:+.3f}% age:"
            f"{(f'{self.age_secs/60.0:.1f}m' if self.age_secs is not None else 'NO_DATA')}"
        )


class AlpacaCapitalStyleTrader:
    SHADOW_MAX_ACTIVE = 4
    SHADOW_MIN_VALIDATE = 6.0
    SHADOW_MAX_AGE = 20.0 * 60.0

    def __init__(self) -> None:
        self.client: Optional[AlpacaClient] = AlpacaClient() if AlpacaClient is not None else None
        self.init_error = ""
        if self.client is None or not getattr(self.client, "is_authenticated", False):
            self.init_error = "alpaca_client_unavailable_or_not_authenticated"
            self.client = None

        self._universe_snapshot: Dict[str, Any] = {}
        self.positions: List[AlpacaMomentumPosition] = []
        self.shadow_trades: List[AlpacaShadowTrade] = []
        self.universe: Dict[str, Dict[str, float]] = self._build_universe()
        self._prices: Dict[str, Dict[str, Any]] = {}
        self._price_failures: Dict[str, Dict[str, Any]] = {}
        self._pending_orders: Dict[str, Dict[str, Any]] = {}
        self._execution_cost_receipts: Dict[str, Dict[str, Any]] = {}
        self._latest_candidate_snapshot: List[Dict[str, Any]] = []
        self._latest_target_snapshot: Dict[str, Any] = {}
        self._latest_status_lines: List[str] = []
        self._latest_order_error = ""
        self._latest_monitor_line = ""
        self._recent_closed_trades: List[Dict[str, Any]] = []
        self._lane_snapshot: Dict[str, Any] = {}
        self._registry_snapshot: Dict[str, Any] = {}
        self._decision_snapshot: Dict[str, Any] = {}
        self._orchestrator_snapshot: Dict[str, Any] = {}
        self._thought_bus_snapshot: Dict[str, Any] = {}
        self._cognition_snapshot: Dict[str, Any] = {}
        self._swarm_snapshot: Dict[str, Any] = {
            "enabled": True,
            "leader": {},
            "votes": [],
            "ranked": [],
        }
        self._timeline_snapshot: Dict[str, Any] = {}
        self._fusion_snapshot: Dict[str, Any] = {}
        self._probability_snapshot: Dict[str, Any] = {}
        self._probability_snapshot_at: float = 0.0
        self._self_confidence_snapshot: Dict[str, Any] = {}
        self._scan_window_snapshot: Dict[str, Any] = {}
        self._shadow_validated_count = 0
        self._shadow_failed_count = 0
        self._shortable_cache: Dict[str, bool] = {}
        self._signal_brain = AureonBrain() if AureonBrain is not None else None
        self.unified_registry = get_unified_puller() if HAS_UNIFIED_REGISTRY and get_unified_puller is not None else None
        self.unified_decision_engine = UnifiedDecisionEngine() if HAS_UNIFIED_DECISION and UnifiedDecisionEngine is not None else None
        self.orchestrator = AutonomousOrchestrator(self) if HAS_ALPACA_ORCHESTRATOR and AutonomousOrchestrator is not None else None
        self.timeline_oracle = get_timeline_oracle() if HAS_TIMELINE_ORACLE and get_timeline_oracle is not None else None
        self.harmonic_fusion = HarmonicWaveFusion() if HAS_HARMONIC_FUSION and HarmonicWaveFusion is not None else None
        self.thought_bus = (
            get_thought_bus(os.path.join(os.path.dirname(__file__), "..", "..", "state", "alpaca_thoughts.jsonl"))
            if HAS_THOUGHT_BUS and get_thought_bus is not None else None
        )
        self._harmonic_wiring_audit: Dict[str, Any] = self._build_harmonic_wiring_audit()
        self._harmonic_wiring_audit_at: float = time.time()
        self.start_time = time.time()
        self._last_scan = 0.0
        self._last_monitor = 0.0
        self._scan_cursor = 0
        self.stats = {
            "trades_opened": 0.0,
            "trades_closed": 0.0,
            "winning_trades": 0.0,
            "losing_trades": 0.0,
            "total_pnl_usd": 0.0,
        }
        account = self.get_account_snapshot()
        self.starting_equity_usd = _finite_number(account.get("equity_usd"), positive=True)

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def _default_symbol_config(self, symbol: str) -> Dict[str, float]:
        seed = sum(ord(ch) for ch in symbol.upper())
        if seed % 7 == 0:
            return {"tp_pct": 1.00, "sl_pct": 0.60, "size": 1, "max_spread_pct": 0.30, "momentum_threshold": 0.30}
        if seed % 5 == 0:
            return {"tp_pct": 0.90, "sl_pct": 0.55, "size": 1, "max_spread_pct": 0.25, "momentum_threshold": 0.25}
        if seed % 3 == 0:
            return {"tp_pct": 0.80, "sl_pct": 0.45, "size": 1, "max_spread_pct": 0.20, "momentum_threshold": 0.20}
        return {"tp_pct": 0.70, "sl_pct": 0.40, "size": 1, "max_spread_pct": 0.18, "momentum_threshold": 0.18}

    def _is_symbol_quality_ok(self, symbol: str) -> bool:
        sym = (symbol or "").upper().strip()
        if not sym:
            return False
        bad_suffixes = ("W", "WS", "WT", "U", "RT", "R", "PRA", "PRB", "PRC", "PRD", "PRE", "PRF", "PRG")
        if "." in sym:
            return False
        if "-" in sym:
            return False
        if len(sym) > 5 and sym.endswith(bad_suffixes):
            return False
        return sym.isalnum()

    def _build_universe(self) -> Dict[str, Dict[str, float]]:
        if not self.client:
            self._universe_snapshot = {
                "mode": "fallback",
                "reason": "client_unavailable",
                "size": len(ALPACA_CAPITAL_UNIVERSE),
                "limit": ALPACA_UNIVERSE_LIMIT,
            }
            return dict(ALPACA_CAPITAL_UNIVERSE)
        try:
            symbols = list(dict.fromkeys(self.client.get_tradable_stock_symbols() or []))
        except Exception:
            symbols = []
        if not symbols:
            self._universe_snapshot = {
                "mode": "fallback",
                "reason": "tradable_stock_discovery_empty",
                "size": len(ALPACA_CAPITAL_UNIVERSE),
                "limit": ALPACA_UNIVERSE_LIMIT,
            }
            return dict(ALPACA_CAPITAL_UNIVERSE)
        preferred = list(ALPACA_CAPITAL_UNIVERSE.keys())
        extras = [sym for sym in symbols if sym not in ALPACA_CAPITAL_UNIVERSE and self._is_symbol_quality_ok(sym)]
        selected = (preferred + extras)[:ALPACA_UNIVERSE_LIMIT]
        universe: Dict[str, Dict[str, float]] = {}
        for sym in selected:
            universe[sym] = dict(ALPACA_CAPITAL_UNIVERSE.get(sym) or self._default_symbol_config(sym))
        self._universe_snapshot = {
            "mode": "live",
            "reason": "tradable_stock_discovery_ok",
            "size": len(universe),
            "limit": ALPACA_UNIVERSE_LIMIT,
            "discovered_symbols": len(symbols),
        }
        return universe

    def _direction_counts(self) -> Dict[str, int]:
        counts = {"BUY": 0, "SELL": 0}
        for pos in self.positions:
            direction = str(pos.direction or "").upper()
            counts[direction] = counts.get(direction, 0) + 1
        return counts

    def _is_shortable(self, symbol: str) -> bool:
        cached = self._shortable_cache.get(symbol.upper())
        if cached is not None:
            return cached
        allowed = bool(self.client and self.client.is_shortable(symbol))
        self._shortable_cache[symbol.upper()] = allowed
        return allowed

    def _refresh_registry_snapshot(self) -> None:
        snapshot: Dict[str, Any] = {}
        if self.unified_registry is not None:
            try:
                snapshot["categories"] = self.unified_registry.get_category_summary()
                snapshot["chain_flow"] = self.unified_registry.get_chain_flow()
            except Exception as e:
                snapshot["error"] = str(e)
        if not snapshot:
            snapshot = {
                "categories": {
                    "stocks": len(self.universe),
                    "open_positions": len(self.positions),
                    "shadow_positions": len(self.shadow_trades),
                },
                "universe_size": len(self.universe),
            }
        self._registry_snapshot = snapshot

    def _build_swarm_snapshot(self, scored: List[Dict[str, Any]]) -> Dict[str, Any]:
        ranked: List[Dict[str, Any]] = []
        for item in scored[:7]:
            votes = max(0, min(5, int(round(float(item.get("score", 0.0) or 0.0)))))
            ranked.append({
                "symbol": str(item.get("symbol") or ""),
                "direction": str(item.get("direction") or "").upper(),
                "votes": votes,
                "swarm_score": float(item.get("score", 0.0) or 0.0),
            })
        leader = dict(ranked[0]) if ranked else {}
        return {
            "enabled": True,
            "leader": leader,
            "votes": ranked,
            "ranked": ranked,
        }

    def _update_coordination_snapshots(self) -> None:
        target = dict(self._latest_target_snapshot or {})
        symbol = str(target.get("symbol") or "")
        side = str(target.get("direction") or "").upper()
        score = float(target.get("score", 0.0) or 0.0)
        net = float(target.get("expected_net_profit", 0.0) or 0.0)
        approved = bool(
            symbol
            and side in {"BUY", "SELL"}
            and score > 0
            and net > 0
            and target.get("eligible_for_external_action") is True
        )
        if symbol:
            self._feed_unified_decision_engine(symbol, side, score=max(0.0, min(1.0, score / 3.0)), metadata=target)
            self._orchestrator_snapshot = self._orchestrator_pretrade_gate(symbol, side)
            if not self._decision_snapshot:
                self._decision_snapshot = {
                    "symbol": symbol,
                    "side": side,
                    "decision": {
                        "type": "execute" if approved else "hold",
                        "confidence": max(0.0, min(1.0, score / 3.0)),
                    },
                }
        else:
            self._decision_snapshot = {}
            self._orchestrator_snapshot = {}

    def _record_price_failure(
        self,
        symbol: str,
        reason: str,
        *,
        source_timestamp: Optional[float] = None,
        received_at: Optional[float] = None,
    ) -> None:
        self._prices.pop(symbol, None)
        self._price_failures[symbol] = {
            "symbol": symbol,
            "truth_status": "no_data",
            "reason": reason,
            "source_id": "alpaca_stock_snapshot",
            "source_timestamp": source_timestamp,
            "received_at": time.time() if received_at is None else received_at,
            "generated_values": False,
            "eligible_for_external_action": False,
        }

    def _ticker_is_actionable(self, ticker: Dict[str, Any], *, now: Optional[float] = None) -> bool:
        if (
            not isinstance(ticker, dict)
            or ticker.get("truth_status") != "real_derived"
            or ticker.get("generated_values") is not False
            or ticker.get("eligible_for_external_action") is not True
        ):
            return False
        observed_at = time.time() if now is None else float(now)
        quote_timestamp = _provider_timestamp(ticker.get("source_timestamp"))
        if not _is_fresh_provider_time(quote_timestamp, ALPACA_QUOTE_TTL_SECS, observed_at):
            return False
        required = ("price", "bid", "ask", "change_pct", "bar_volume", "dollar_volume")
        parsed = {name: _finite_number(ticker.get(name)) for name in required}
        if any(value is None for value in parsed.values()):
            return False
        return bool(
            parsed["price"] > 0
            and parsed["bid"] > 0
            and parsed["ask"] > parsed["bid"]
            and parsed["bar_volume"] >= 0
            and parsed["dollar_volume"] >= 0
        )

    def _refresh_prices(self) -> None:
        if not self.client:
            return
        symbols = list(self.universe.keys())
        if not symbols:
            self._scan_window_snapshot = {"start": 0, "end": 0, "size": 0, "total": 0}
            return
        total = len(symbols)
        window_size = min(ALPACA_SCAN_WINDOW, total)
        start = self._scan_cursor % total
        window = symbols[start:start + window_size]
        if len(window) < window_size:
            window += symbols[:window_size - len(window)]
        self._scan_cursor = (start + window_size) % total
        self._scan_window_snapshot = {
            "start": start,
            "end": (start + len(window) - 1) % total if window else start,
            "size": len(window),
            "total": total,
            "symbols": list(window[:5]),
        }
        received_at = time.time()
        try:
            snapshots = self.client.get_stock_snapshots(window) or {}
        except Exception as exc:
            snapshots = {}
            logger.warning("Alpaca stock snapshot read failed: %s", exc)
        for symbol in window:
            self._prices.pop(symbol, None)
            snap = snapshots.get(symbol) or {}
            latest_quote = snap.get("latestQuote", {}) or snap.get("latest_quote", {}) or {}
            daily_bar = snap.get("dailyBar", {}) or snap.get("daily_bar", {}) or {}
            prev_bar = snap.get("prevDailyBar", {}) or snap.get("prev_daily_bar", {}) or {}
            bid = _finite_number(latest_quote.get("bp"), positive=True)
            ask = _finite_number(latest_quote.get("ap"), positive=True)
            daily_close = _finite_number(daily_bar.get("c"), positive=True)
            prev_close = _finite_number(prev_bar.get("c"), positive=True)
            bar_volume = _finite_number(daily_bar.get("v"), nonnegative=True)
            quote_timestamp = _provider_timestamp(latest_quote.get("t"))
            daily_timestamp = _provider_timestamp(daily_bar.get("t"))
            prev_timestamp = _provider_timestamp(prev_bar.get("t"))
            if any(value is None for value in (bid, ask, daily_close, prev_close, bar_volume)):
                self._record_price_failure(symbol, "missing_or_invalid_quote_bar_fields", received_at=received_at)
                continue
            if not _is_fresh_provider_time(quote_timestamp, ALPACA_QUOTE_TTL_SECS, received_at):
                self._record_price_failure(
                    symbol,
                    "quote_timestamp_missing_or_stale",
                    source_timestamp=quote_timestamp,
                    received_at=received_at,
                )
                continue
            if not _is_fresh_provider_time(daily_timestamp, ALPACA_BAR_TTL_SECS, received_at):
                self._record_price_failure(
                    symbol,
                    "daily_bar_timestamp_missing_or_stale",
                    source_timestamp=daily_timestamp,
                    received_at=received_at,
                )
                continue
            if not _is_fresh_provider_time(prev_timestamp, ALPACA_BAR_TTL_SECS, received_at):
                self._record_price_failure(
                    symbol,
                    "previous_bar_timestamp_missing_or_stale",
                    source_timestamp=prev_timestamp,
                    received_at=received_at,
                )
                continue
            if ask <= bid:
                self._record_price_failure(
                    symbol,
                    "crossed_or_locked_quote",
                    source_timestamp=quote_timestamp,
                    received_at=received_at,
                )
                continue
            price = (bid + ask) / 2.0
            dollar_volume = price * bar_volume
            if price < ALPACA_MIN_PRICE:
                self._record_price_failure(
                    symbol,
                    "below_minimum_price_policy",
                    source_timestamp=quote_timestamp,
                    received_at=received_at,
                )
                continue
            if dollar_volume < ALPACA_MIN_DOLLAR_VOLUME:
                self._record_price_failure(
                    symbol,
                    "below_minimum_observed_dollar_volume",
                    source_timestamp=quote_timestamp,
                    received_at=received_at,
                )
                continue
            change_pct = ((price - prev_close) / prev_close) * 100.0
            self._prices[symbol] = {
                "price": price,
                "bid": bid,
                "ask": ask,
                "change_pct": change_pct,
                "dollar_volume": dollar_volume,
                "bar_volume": bar_volume,
                "truth_status": "real_derived",
                "source_id": "alpaca_stock_snapshot",
                "source_timestamp": quote_timestamp,
                "received_at": received_at,
                "generated_values": False,
                "eligible_for_external_action": True,
                "field_provenance": {
                    "bid": {"source": "latestQuote.bp", "source_timestamp": quote_timestamp},
                    "ask": {"source": "latestQuote.ap", "source_timestamp": quote_timestamp},
                    "price": {"source": "midpoint(latestQuote.bp,latestQuote.ap)", "source_timestamp": quote_timestamp},
                    "bar_volume": {"source": "dailyBar.v", "source_timestamp": daily_timestamp},
                    "daily_close": {"source": "dailyBar.c", "source_timestamp": daily_timestamp},
                    "previous_close": {"source": "prevDailyBar.c", "source_timestamp": prev_timestamp},
                },
            }
            self._price_failures.pop(symbol, None)

    def _capital_style_cost_profile(self, symbol: str, size: float, price: float, tp_pct: float) -> Dict[str, Any]:
        ticker = self._prices.get(symbol) or {}
        parsed_size = _finite_number(size, positive=True)
        parsed_price = _finite_number(price, positive=True)
        parsed_target = _finite_number(tp_pct, nonnegative=True)
        if not self._ticker_is_actionable(ticker) or None in (parsed_size, parsed_price, parsed_target):
            return {
                "notional": None,
                "expected_gross_profit": None,
                "observed_spread_cost": None,
                "round_trip_cost": None,
                "expected_net_profit": None,
                "truth_status": "no_data",
                "reason": "fresh_provider_quote_or_strategy_inputs_unavailable",
                "source_id": ticker.get("source_id"),
                "source_timestamp": ticker.get("source_timestamp"),
                "generated_values": False,
                "eligible_for_external_action": False,
                "unpriced_cost_components": ["regulatory_fees", "slippage"],
            }
        bid = _finite_number(ticker.get("bid"), positive=True)
        ask = _finite_number(ticker.get("ask"), positive=True)
        if bid is None or ask is None or ask <= bid:
            return {
                "notional": None,
                "expected_gross_profit": None,
                "observed_spread_cost": None,
                "round_trip_cost": None,
                "expected_net_profit": None,
                "truth_status": "no_data",
                "reason": "valid_bid_ask_unavailable",
                "source_id": ticker.get("source_id"),
                "source_timestamp": ticker.get("source_timestamp"),
                "generated_values": False,
                "eligible_for_external_action": False,
                "unpriced_cost_components": ["regulatory_fees", "slippage"],
            }
        notional = parsed_size * parsed_price
        expected_gross_profit = notional * (parsed_target / 100.0)
        spread_cost = (ask - bid) * parsed_size
        cost_receipt = self._execution_cost_receipts.get(symbol.upper()) or {}
        receipt_total_pct = _finite_number(cost_receipt.get("total_cost_pct"), nonnegative=True)
        receipt_timestamp = _provider_timestamp(cost_receipt.get("source_timestamp"))
        receipt_is_valid = bool(
            cost_receipt.get("truth_status") in {"real_observed", "real_derived"}
            and cost_receipt.get("generated_values") is False
            and str(cost_receipt.get("source_id") or "").strip()
            and receipt_total_pct is not None
            and _is_fresh_provider_time(receipt_timestamp, 86400.0)
        )
        if receipt_is_valid:
            round_trip_cost = notional * (receipt_total_pct / 100.0)
            return {
                "notional": notional,
                "expected_gross_profit": expected_gross_profit,
                "observed_spread_cost": spread_cost,
                "round_trip_cost": round_trip_cost,
                "expected_net_profit": expected_gross_profit - round_trip_cost,
                "expected_net_before_unpriced_costs": expected_gross_profit - spread_cost,
                "truth_status": "real_derived",
                "reason": "fresh_provider_execution_cost_receipt",
                "source_id": f"{ticker.get('source_id')}+{cost_receipt.get('source_id')}",
                "source_timestamp": min(
                    float(_provider_timestamp(ticker.get("source_timestamp"))),
                    float(receipt_timestamp),
                ),
                "received_at": ticker.get("received_at"),
                "generated_values": False,
                "eligible_for_external_action": True,
                "unpriced_cost_components": [],
                "cost_sample_count": int(cost_receipt.get("sample_count") or 1),
            }
        return {
            "notional": notional,
            "expected_gross_profit": expected_gross_profit,
            "observed_spread_cost": spread_cost,
            "round_trip_cost": None,
            "expected_net_profit": None,
            "expected_net_before_unpriced_costs": expected_gross_profit - spread_cost,
            "truth_status": "incomplete",
            "reason": "provider_quote_proves_spread_but_not_future_regulatory_fees_or_slippage",
            "source_id": ticker.get("source_id"),
            "source_timestamp": ticker.get("source_timestamp"),
            "received_at": ticker.get("received_at"),
            "generated_values": False,
            "eligible_for_external_action": False,
            "unpriced_cost_components": ["regulatory_fees", "slippage"],
        }

    def record_execution_cost_receipt(self, symbol: str, receipt: Dict[str, Any]) -> bool:
        normalized_symbol = str(symbol or "").upper().strip()
        total_cost_pct = _finite_number(receipt.get("total_cost_pct"), nonnegative=True) if isinstance(receipt, dict) else None
        source_timestamp = _provider_timestamp(receipt.get("source_timestamp")) if isinstance(receipt, dict) else None
        if not (
            normalized_symbol
            and isinstance(receipt, dict)
            and receipt.get("truth_status") in {"real_observed", "real_derived"}
            and receipt.get("generated_values") is False
            and str(receipt.get("source_id") or "").strip()
            and total_cost_pct is not None
            and _is_fresh_provider_time(source_timestamp, 86400.0)
        ):
            return False
        stored = dict(receipt)
        stored["total_cost_pct"] = total_cost_pct
        stored["source_timestamp"] = source_timestamp
        stored["received_at"] = time.time()
        stored["eligible_for_external_action"] = True
        self._execution_cost_receipts[normalized_symbol] = stored
        return True

    def _compute_self_confidence(self, candidate: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        snapshot: Dict[str, Any] = {
            "enabled": ALPACA_SELF_CONFIDENCE_ENABLED,
            "score": None,
            "boost_multiplier": 1.0,
            "validation_window_secs": self.SHADOW_MIN_VALIDATE,
            "recent_success_ratio": None,
            "alignment_score": None,
            "rejection_pressure": None,
            "reason": "disabled" if not ALPACA_SELF_CONFIDENCE_ENABLED else "no_data",
            "truth_status": "no_data",
            "generated_values": False,
        }
        if not ALPACA_SELF_CONFIDENCE_ENABLED:
            return snapshot

        validated = float(self._shadow_validated_count or 0.0)
        failed = float(self._shadow_failed_count or 0.0)
        completed = validated + failed
        if completed > 0:
            recent_success_ratio = validated / completed
        else:
            wins = float(self.stats.get("winning_trades", 0.0) or 0.0)
            losses = float(self.stats.get("losing_trades", 0.0) or 0.0)
            proven_outcomes = wins + losses
            if proven_outcomes <= 0:
                return snapshot
            recent_success_ratio = wins / proven_outcomes

        source = dict(candidate or self._latest_target_snapshot or {})
        change_pct = _finite_number(source.get("change_pct"))
        source_timestamp = _provider_timestamp(source.get("source_timestamp"))
        if (
            source.get("truth_status") not in {"real_observed", "real_derived", "incomplete"}
            or source.get("generated_values") is not False
            or change_pct is None
            or not _is_fresh_provider_time(source_timestamp, ALPACA_QUOTE_TTL_SECS)
        ):
            return snapshot
        alignment_score = max(0.0, min(1.0, abs(change_pct) / 1.5))
        rejection_pressure = 1.0 if self._latest_order_error else 0.0
        raw_score = (recent_success_ratio * 0.5) + (alignment_score * 0.4) + ((1.0 - rejection_pressure) * 0.1)
        score = max(0.0, min(1.0, raw_score))
        boost_multiplier = 1.0 + max(0.0, score - 0.5) * 2.0 * ALPACA_SELF_CONFIDENCE_MAX_BOOST
        validation_window = max(
            ALPACA_SELF_CONFIDENCE_MIN_VALIDATE_SECS,
            float(self.SHADOW_MIN_VALIDATE) - max(0.0, score - 0.55) * (float(self.SHADOW_MIN_VALIDATE) - ALPACA_SELF_CONFIDENCE_MIN_VALIDATE_SECS),
        )
        snapshot.update({
            "score": score,
            "boost_multiplier": boost_multiplier,
            "validation_window_secs": validation_window,
            "recent_success_ratio": recent_success_ratio,
            "alignment_score": alignment_score,
            "rejection_pressure": rejection_pressure,
            "reason": "armed" if score >= 0.55 else "warming_up",
            "truth_status": "real_derived",
            "source_id": source.get("source_id"),
            "source_timestamp": source_timestamp,
            "received_at": source.get("received_at"),
        })
        return snapshot

    def _compute_growth_metrics(self) -> Dict[str, Any]:
        runtime_secs = max(1.0, time.time() - self.start_time)
        runtime_hours = runtime_secs / 3600.0
        pnl = float(self.stats.get("total_pnl_usd", 0.0) or 0.0)
        trades_closed = int(self.stats.get("trades_closed", 0.0) or 0.0)
        wins = int(self.stats.get("winning_trades", 0.0) or 0.0)
        losses = int(self.stats.get("losing_trades", 0.0) or 0.0)
        account = self.get_account_snapshot()
        equity_now = _finite_number(account.get("equity_usd"), positive=True)
        equity_start = _finite_number(self.starting_equity_usd, positive=True)
        equity_growth_pct = (
            ((equity_now - equity_start) / equity_start) * 100.0
            if equity_now is not None and equity_start is not None
            else None
        )
        pnl_per_hour = pnl / runtime_hours if runtime_hours > 0 else 0.0
        trades_per_hour = trades_closed / runtime_hours if runtime_hours > 0 else 0.0
        proven_closes = wins + losses
        avg_pnl = pnl / proven_closes if proven_closes > 0 else None
        recent = [
            item
            for item in list(self._recent_closed_trades or [])[-3:]
            if item.get("eligible_for_learning") is True and _finite_number(item.get("net_pnl")) is not None
        ]
        recent_pnl = sum(float(item["net_pnl"]) for item in recent) if recent else None
        recent_avg = recent_pnl / len(recent) if recent_pnl is not None and recent else None
        trend = "no_data"
        if recent_avg is not None and avg_pnl is not None and recent_avg > avg_pnl + 1e-9:
            trend = "accelerating"
        elif recent_avg is not None and avg_pnl is not None and recent_avg < avg_pnl - 1e-9:
            trend = "cooling"
        elif recent_avg is not None and avg_pnl is not None:
            trend = "steady"
        return {
            "runtime_hours": runtime_hours,
            "equity_growth_pct": equity_growth_pct,
            "pnl_per_hour_usd": pnl_per_hour,
            "trades_per_hour": trades_per_hour,
            "avg_pnl_per_close_usd": avg_pnl,
            "recent_avg_pnl_usd": recent_avg,
            "recent_total_pnl_usd": recent_pnl,
            "win_rate": (wins / proven_closes) if proven_closes > 0 else None,
            "closed_trades": trades_closed,
            "proven_net_pnl_trades": proven_closes,
            "wins": wins,
            "losses": losses,
            "trend": trend,
            "truth_status": "real_derived" if equity_growth_pct is not None else "incomplete",
            "generated_values": False,
            "incomplete_reason": None if equity_growth_pct is not None else "account_equity_receipt_unavailable",
        }

    def _refresh_thought_bus_snapshot(self) -> None:
        if self.thought_bus is None:
            self._thought_bus_snapshot = {}
            self._cognition_snapshot = {}
            return
        try:
            market_events = self.thought_bus.recall("market.", limit=8)
            decision_events = self.thought_bus.recall("decisions.", limit=8)
            cognition_events = self.thought_bus.recall("brain.", limit=8)
            queen_events = self.thought_bus.recall("queen.", limit=8)
            self._thought_bus_snapshot = {"market_events": len(market_events), "decision_events": len(decision_events)}
            self._cognition_snapshot = {"cognition_events": len(cognition_events), "queen_events": len(queen_events)}
        except Exception as e:
            self._thought_bus_snapshot = {"error": str(e)}
            self._cognition_snapshot = {"error": str(e)}

    def _publish_market_snapshot_to_thought_bus(self) -> None:
        if self.thought_bus is None or Thought is None or not self._latest_candidate_snapshot:
            return
        try:
            market_by_symbol: Dict[str, Dict[str, Any]] = {}
            universe: List[str] = []
            for candidate in self._latest_candidate_snapshot[:7]:
                symbol = str(candidate.get("symbol") or "").upper()
                direction = str(candidate.get("direction") or "").upper()
                ticker = self._prices.get(symbol) or {}
                momentum = _finite_number(candidate.get("change_pct"))
                score = _finite_number(candidate.get("score"))
                spread_pct = _finite_number(candidate.get("spread_pct"), nonnegative=True)
                if (
                    not symbol
                    or direction not in {"BUY", "SELL"}
                    or not self._ticker_is_actionable(ticker)
                    or None in (momentum, score, spread_pct)
                ):
                    continue
                universe.append(symbol)
                market_by_symbol[symbol] = {
                    "price": ticker["price"],
                    "momentum": momentum,
                    "score": score,
                    "spread_pct": spread_pct,
                    "direction": direction,
                    "truth_status": "real_derived",
                    "source_id": ticker.get("source_id"),
                    "source_timestamp": ticker.get("source_timestamp"),
                    "received_at": ticker.get("received_at"),
                    "generated_values": False,
                    "eligible_for_external_action": bool(candidate.get("eligible_for_external_action")),
                    "field_provenance": ticker.get("field_provenance"),
                }
            if not universe:
                return
            self.thought_bus.publish(Thought(
                source="alpaca_capital_style_trader",
                topic="market.snapshot",
                payload={
                    "venue": "alpaca",
                    "universe": universe,
                    "market_by_symbol": market_by_symbol,
                    "truth_status": "real_derived",
                    "generated_values": False,
                },
                meta={"mode": "alpaca_capital_style", "truth_status": "real_derived"},
            ))
        except Exception as e:
            logger.debug("Alpaca ThoughtBus publish failed: %s", e)

    def _publish_learning_update(self, record: Dict[str, Any]) -> None:
        if self.thought_bus is None or Thought is None:
            return
        learning_update = dict(record.get("learning_update") or {})
        if not learning_update:
            return
        try:
            symbol = str(record.get("symbol") or "").upper()
            payload = {
                "venue": "alpaca",
                "symbol": symbol,
                "direction": str(record.get("direction") or "").upper(),
                "net_pnl_usd": float(record.get("net_pnl", 0.0) or 0.0),
                "reason": str(record.get("reason") or ""),
                "learning_update": learning_update,
            }
            self.thought_bus.publish(Thought(
                source="alpaca_capital_style_trader",
                topic="brain.learning",
                payload=payload,
                meta={"mode": "alpaca_capital_style", "expressive": True},
            ))
            self.thought_bus.publish(Thought(
                source="alpaca_capital_style_trader",
                topic="queen.learning",
                payload={
                    "voice": (
                        f"I learned from {symbol}. "
                        f"Net outcome was {float(record.get('net_pnl', 0.0) or 0.0):+.2f} USD, "
                        f"and my bias is now {float(learning_update.get('symbol_bias', 0.0) or 0.0):+.3f}."
                    ),
                    **payload,
                },
                meta={"mode": "alpaca_capital_style", "expressive": True},
            ))
        except Exception as e:
            logger.debug("Alpaca learning publish failed: %s", e)

    def _feed_unified_decision_engine(self, symbol: str, side: str, score: float, metadata: Optional[dict] = None) -> None:
        if self.unified_decision_engine is None or SignalInput is None:
            return
        normalized_side = str(side or "").upper()
        parsed_score = _finite_number(score)
        evidence = dict(metadata or {})
        if (
            normalized_side not in {"BUY", "SELL"}
            or parsed_score is None
            or evidence.get("truth_status") not in {"real_observed", "real_derived"}
            or evidence.get("generated_values") is not False
            or not _is_fresh_provider_time(
                _provider_timestamp(evidence.get("source_timestamp")),
                ALPACA_QUOTE_TTL_SECS,
            )
        ):
            self._decision_snapshot = {
                "symbol": symbol,
                "side": normalized_side,
                "decision": None,
                "truth_status": "no_data",
                "reason": "fresh_proven_signal_unavailable",
                "generated_values": False,
            }
            return
        try:
            direction = "bullish" if normalized_side == "BUY" else "bearish"
            self.unified_decision_engine.add_signal(
                SignalInput(
                    source="alpaca_capital_style_trader",
                    symbol=symbol,
                    direction=direction,
                    strength=max(0.0, min(1.0, parsed_score)),
                    metadata=evidence,
                )
            )
            coordination = evidence.get("coordination_receipt")
            if (
                CoordinationInput is not None
                and isinstance(coordination, dict)
                and coordination.get("truth_status") in {"real_observed", "real_derived"}
                and coordination.get("generated_values") is False
            ):
                ready_count = _finite_number(coordination.get("ready_systems"), nonnegative=True)
                total_count = _finite_number(coordination.get("total_systems"), positive=True)
                blockers = coordination.get("blockers")
                if ready_count is not None and total_count is not None and isinstance(blockers, list):
                    self.unified_decision_engine.set_coordination_state(
                        CoordinationInput(
                            orca_ready=coordination.get("orca_ready") is True,
                            all_systems_ready=int(ready_count),
                            total_systems=int(total_count),
                            blockers=list(blockers),
                        )
                    )
            decision = None
            if DecisionType is not None and DecisionReason is not None:
                decision = self.unified_decision_engine.generate_decision(
                    symbol,
                    DecisionType.BUY if normalized_side == "BUY" else DecisionType.SELL,
                    DecisionReason.SIGNAL_STRENGTH,
                )
            self._decision_snapshot = {
                "symbol": symbol,
                "side": normalized_side,
                "score": parsed_score,
                "truth_status": "real_derived",
                "source_id": evidence.get("source_id"),
                "source_timestamp": evidence.get("source_timestamp"),
                "received_at": evidence.get("received_at"),
                "generated_values": False,
                "decision": {
                    "type": decision.decision_type.value,
                    "confidence": decision.confidence,
                    "reason": decision.reason.value,
                } if decision else None,
            }
        except Exception as e:
            self._decision_snapshot = {
                "error": str(e),
                "symbol": symbol,
                "side": normalized_side,
                "decision": None,
                "truth_status": "no_data",
                "generated_values": False,
            }

    def _score_timeline_oracle(
        self,
        symbol: str,
        side: str,
        price: float,
        change_pct: float,
        volume: float,
        source_timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        result = {
            "bonus": None,
            "action": None,
            "confidence": None,
            "reason": "timeline_unavailable",
            "truth_status": "no_data",
            "source_timestamp": source_timestamp,
            "generated_values": False,
        }
        if self.timeline_oracle is None:
            return result
        parsed_price = _finite_number(price, positive=True)
        parsed_change = _finite_number(change_pct)
        parsed_volume = _finite_number(volume, nonnegative=True)
        if (
            None in (parsed_price, parsed_change, parsed_volume)
            or not _is_fresh_provider_time(source_timestamp, ALPACA_QUOTE_TTL_SECS)
        ):
            result["reason"] = "fresh_timeline_inputs_unavailable"
            return result
        try:
            action, confidence, reason = self.timeline_oracle.get_approved_action(
                symbol=symbol,
                price=parsed_price,
                volume=parsed_volume,
                change_pct=parsed_change,
            )
            action_value = str(getattr(action, "value", "") or "").lower()
            confidence = _finite_number(confidence)
            if action_value not in {"buy", "sell", "hold", "wait"} or confidence is None or not 0.0 <= confidence <= 1.0:
                result["reason"] = "timeline_output_missing_or_invalid"
                return result
            expected = "buy" if str(side).upper() == "BUY" else "sell"
            bonus = (confidence - 0.5) * 2.0
            if action_value == expected:
                bonus += 0.5
            elif action_value not in {"hold", "wait"}:
                bonus -= 0.75
            result.update({
                "bonus": max(-1.5, min(2.0, bonus)),
                "action": action_value,
                "confidence": confidence,
                "reason": str(reason or ""),
                "truth_status": "real_derived",
                "source_id": "timeline_oracle+alpaca_stock_snapshot",
            })
        except Exception as e:
            result["error"] = str(e)
        self._timeline_snapshot = {"symbol": symbol, "side": str(side).upper(), **result}
        return result

    def _score_harmonic_fusion(self, symbol: str, side: str) -> Dict[str, Any]:
        result = {
            "bonus": None,
            "global_coherence": None,
            "symbol_coherence": None,
            "truth_status": "no_data",
            "reason": "harmonic_fusion_unavailable",
            "generated_values": False,
        }
        if self.harmonic_fusion is None:
            return result
        try:
            state = self.harmonic_fusion.get_harmonic_state() or {}
            phase = self.harmonic_fusion.get_symbol_phase(symbol) or {}
            global_coh = _finite_number(state.get("global_coherence"))
            symbol_coh = _finite_number(phase.get("coherence"))
            source_timestamp = _provider_timestamp(
                phase.get("source_timestamp") or state.get("source_timestamp")
            )
            if (
                global_coh is None
                or symbol_coh is None
                or not 0.0 <= global_coh <= 1.0
                or not 0.0 <= symbol_coh <= 1.0
                or state.get("generated_values") is not False
                or phase.get("generated_values") is not False
                or not _is_fresh_provider_time(source_timestamp, ALPACA_QUOTE_TTL_SECS)
            ):
                result["reason"] = "fresh_proven_harmonic_state_unavailable"
                return result
            bonus = max(-1.5, min(2.0, (global_coh - 0.5) * 2.0 + (symbol_coh - 0.5) * 2.0))
            result.update({
                "bonus": bonus,
                "global_coherence": global_coh,
                "symbol_coherence": symbol_coh,
                "truth_status": "real_derived",
                "reason": "fresh_proven_harmonic_state",
                "source_id": f"{state.get('source_id')}+{phase.get('source_id')}",
                "source_timestamp": source_timestamp,
            })
        except Exception as e:
            result["error"] = str(e)
        self._fusion_snapshot = {"symbol": symbol, "side": str(side).upper(), **result}
        return result

    def _orchestrator_pretrade_gate(self, symbol: str, side: str) -> Dict[str, Any]:
        result = {
            "approved": False,
            "reason": "orchestrator_unavailable",
            "sizing": {},
            "truth_status": "no_data",
            "generated_values": False,
        }
        if self.orchestrator is None:
            return {"symbol": symbol, "side": str(side).upper(), **result}
        try:
            approved, reason, sizing = self.orchestrator.gate_pre_trade(symbol, str(side).lower())
            result = {
                "approved": approved is True,
                "reason": str(reason or "no_reason"),
                "sizing": sizing if isinstance(sizing, dict) else {},
                "truth_status": "real_derived",
                "generated_values": False,
            }
        except Exception as e:
            result = {
                "approved": False,
                "reason": f"orchestrator_error:{e}",
                "sizing": {},
                "truth_status": "no_data",
                "generated_values": False,
            }
        return {"symbol": symbol, "side": str(side).upper(), **result}

    def _probability_validation_snapshot(self, force: bool = False) -> Dict[str, Any]:
        now = time.time()
        if not force and self._probability_snapshot and (now - self._probability_snapshot_at) < 30.0:
            return dict(self._probability_snapshot)
        payload = {
            "ok": False,
            "direction_accuracy": None,
            "profit_factor": None,
            "updated": None,
            "reason": "probability_receipt_unavailable",
            "truth_status": "no_data",
            "source_id": None,
            "source_timestamp": None,
            "received_at": now,
            "generated_values": False,
            "eligible_for_external_action": False,
        }
        self._probability_snapshot = payload
        self._probability_snapshot_at = now
        return dict(payload)

    def _build_harmonic_wiring_audit(self) -> Dict[str, Any]:
        return {
            "timeline_oracle": self.timeline_oracle is not None,
            "harmonic_fusion": self.harmonic_fusion is not None,
            "unified_registry": self.unified_registry is not None,
            "unified_decision_engine": self.unified_decision_engine is not None,
            "orchestrator": self.orchestrator is not None,
            "thought_bus": self.thought_bus is not None,
        }

    def _apply_intelligence_overlays(self, scored: List[Dict[str, Any]]) -> None:
        ranked = [
            item for item in scored
            if float(item.get("score", 0.0) or 0.0) > 0
        ]
        ranked.sort(key=lambda item: float(item.get("score", 0.0) or 0.0), reverse=True)
        for item in ranked[:ALPACA_INTEL_TOP_N]:
            base_score = float(item.get("score", 0.0) or 0.0)
            if base_score <= 0:
                continue
            symbol = str(item.get("symbol") or "")
            side = str(item.get("direction") or "").upper()
            price = _finite_number(item.get("price"), positive=True)
            change_pct = _finite_number(item.get("change_pct"))
            volume = _finite_number(item.get("bar_volume"), nonnegative=True)
            source_timestamp = _provider_timestamp(item.get("source_timestamp"))
            if (
                not symbol
                or side not in {"BUY", "SELL"}
                or None in (price, change_pct, volume)
                or not _is_fresh_provider_time(source_timestamp, ALPACA_QUOTE_TTL_SECS)
            ):
                item["eligible_for_external_action"] = False
                item["intel_reason"] = "fresh_proven_overlay_inputs_unavailable"
                continue
            timeline = self._score_timeline_oracle(
                symbol,
                side,
                price,
                change_pct,
                volume,
                source_timestamp,
            )
            fusion = self._score_harmonic_fusion(symbol, side)
            gate = self._orchestrator_pretrade_gate(symbol, side)
            timeline_bonus = _finite_number(timeline.get("bonus"))
            fusion_bonus = _finite_number(fusion.get("bonus"))
            item["timeline_bonus"] = timeline_bonus
            item["timeline_action"] = timeline.get("action")
            item["timeline_confidence"] = _finite_number(timeline.get("confidence"))
            item["timeline_truth_status"] = timeline.get("truth_status")
            item["fusion_bonus"] = fusion_bonus
            item["fusion_global_coherence"] = _finite_number(fusion.get("global_coherence"))
            item["fusion_symbol_coherence"] = _finite_number(fusion.get("symbol_coherence"))
            item["fusion_truth_status"] = fusion.get("truth_status")
            item["brain_coherence"] = _finite_number(fusion.get("symbol_coherence"))
            item["orchestrator_reason"] = str(gate.get("reason") or "")
            item["orchestrator_approved"] = bool(gate.get("approved"))
            item["orchestrator_truth_status"] = gate.get("truth_status")
            item["eligible_for_external_action"] = bool(
                item.get("eligible_for_external_action") is True and gate.get("approved") is True
            )
            if not gate.get("approved"):
                item["intel_reason"] = f"orchestrator_gate:{gate.get('reason') or 'blocked'}"
            item["score"] = max(
                0.0,
                base_score
                + (timeline_bonus * 1.25 if timeline_bonus is not None else 0.0)
                + (fusion_bonus if fusion_bonus is not None else 0.0),
            )
            confidence = self._compute_self_confidence(item)
            item["self_confidence"] = confidence.get("score")
            item["self_confidence_boost"] = float(confidence.get("boost_multiplier", 1.0) or 1.0)
            item["self_confidence_reason"] = str(confidence.get("reason") or "")
            item["self_confidence_truth_status"] = confidence.get("truth_status")
            item["score"] = max(0.0, float(item.get("score", 0.0) or 0.0) * item["self_confidence_boost"])

    def _score_symbol(self, symbol: str, cfg: Dict[str, float], ticker: Dict[str, Any]) -> Tuple[float, str]:
        if not self._ticker_is_actionable(ticker):
            return 0.0, ""
        price = _finite_number(ticker.get("price"), positive=True)
        bid = _finite_number(ticker.get("bid"), positive=True)
        ask = _finite_number(ticker.get("ask"), positive=True)
        change_pct = _finite_number(ticker.get("change_pct"))
        if None in (price, bid, ask, change_pct) or ask <= bid:
            return 0.0, ""
        spread_pct = ((ask - bid) / price) * 100.0
        if spread_pct > float(cfg.get("max_spread_pct", 0.2) or 0.2):
            return 0.0, ""
        threshold = float(cfg.get("momentum_threshold", 0.2) or 0.2)
        if abs(change_pct) < threshold:
            return 0.0, ""
        direction = "BUY" if change_pct > 0 else "SELL"
        if direction == "SELL" and not self._is_shortable(symbol):
            return 0.0, ""
        costs = self._capital_style_cost_profile(symbol, float(cfg.get("size", 1.0) or 1.0), price, float(cfg.get("tp_pct", 0.0) or 0.0))
        net_before_unknown = _finite_number(costs.get("expected_net_before_unpriced_costs"))
        if net_before_unknown is None or net_before_unknown <= 0:
            return 0.0, direction
        score = abs(change_pct) - (spread_pct * 0.25)
        score += min(1.5, net_before_unknown / max(ALPACA_MIN_TARGET_USD, 0.0001)) * 0.2
        central_symbols = getattr(self, "_central_beat_symbols", {}) or {}
        central_regime = getattr(self, "_central_beat_regime", {}) or {}
        central_signal = central_symbols.get(symbol) or central_symbols.get(symbol.upper()) or {}
        if isinstance(central_signal, dict) and central_signal:
            support_count = max(1, int(central_signal.get("support_count", 1) or 1))
            central_side = str(central_signal.get("side") or direction).upper()
            central_strength = max(0.0, float(central_signal.get("strength", 0.0) or 0.0))
            aligned = central_side == direction
            multiplier = 1.0 + min(0.18, central_strength * 0.12 + (support_count - 1) * 0.03)
            if aligned:
                score *= multiplier
            else:
                score *= max(0.82, 1.0 - min(0.18, central_strength * 0.10))
        if isinstance(central_regime, dict) and central_regime:
            regime_bias = str(central_regime.get("bias") or direction).upper()
            regime_conf = max(0.0, min(1.0, float(central_regime.get("confidence", 0.0) or 0.0)))
            if regime_conf > 0:
                regime_multiplier = 1.0 + regime_conf * 0.05 if regime_bias == direction else 1.0 - regime_conf * 0.05
                score *= max(0.9, regime_multiplier)
        confidence = self._compute_self_confidence({
            "symbol": symbol,
            "direction": direction,
            "change_pct": change_pct,
            "spread_pct": spread_pct,
            **costs,
        })
        score *= float(confidence.get("boost_multiplier", 1.0) or 1.0)
        observed_features = ticker.get("brain_features")
        if (
            self._signal_brain is not None
            and ticker.get("brain_features_truth_status") == "real_observed"
            and isinstance(observed_features, dict)
            and all(_finite_number(observed_features.get(name)) is not None for name in ("momentum", "volatility", "trend_strength", "rsi"))
        ):
            features = {name: float(observed_features[name]) for name in ("momentum", "volatility", "trend_strength", "rsi")}
            decision = self._signal_brain.decide(symbol, score, features, [score])
            if decision is None:
                return 0.0, direction
            score = float(decision.score)
        return max(0.0, score), direction

    def _find_best_opportunity(self) -> Optional[Tuple[str, Dict[str, float], Dict[str, Any]]]:
        counts = self._direction_counts()
        scored: List[Dict[str, Any]] = []
        for symbol, cfg in self.universe.items():
            ticker = self._prices.get(symbol) or {}
            if not self._ticker_is_actionable(ticker):
                continue
            score, direction = self._score_symbol(symbol, cfg, ticker)
            price = _finite_number(ticker.get("price"), positive=True)
            bid = _finite_number(ticker.get("bid"), positive=True)
            ask = _finite_number(ticker.get("ask"), positive=True)
            change_pct = _finite_number(ticker.get("change_pct"))
            if None in (price, bid, ask, change_pct) or ask <= bid:
                continue
            costs = self._capital_style_cost_profile(
                symbol,
                float(cfg.get("size", 1.0) or 1.0),
                price,
                float(cfg.get("tp_pct", 0.0) or 0.0),
            )
            scored.append({
                "symbol": symbol,
                "direction": direction,
                "asset_class": "stock",
                "score": score,
                "price": price,
                "change_pct": change_pct,
                "spread_pct": ((ask - bid) / price) * 100.0,
                "bar_volume": ticker["bar_volume"],
                "dollar_volume": ticker["dollar_volume"],
                "profit_target_usd": ALPACA_MIN_TARGET_USD,
                "truth_status": "real_derived",
                "source_id": ticker.get("source_id"),
                "source_timestamp": ticker.get("source_timestamp"),
                "received_at": ticker.get("received_at"),
                "generated_values": False,
                "eligible_for_external_action": bool(costs.get("eligible_for_external_action")),
                **costs,
            })
        self._apply_intelligence_overlays(scored)
        scored.sort(key=lambda item: float(item.get("score", 0.0) or 0.0), reverse=True)
        self._latest_candidate_snapshot = scored[:7]
        self._swarm_snapshot = self._build_swarm_snapshot(scored)
        self._latest_target_snapshot = dict(scored[0]) if scored else {}
        for item in scored:
            symbol = str(item.get("symbol") or "")
            direction = str(item.get("direction") or "")
            if float(item.get("score", 0.0) or 0.0) <= 0 or direction not in {"BUY", "SELL"}:
                continue
            if counts.get(direction, 0) >= 1 or len(self.positions) >= MAX_POSITIONS:
                continue
            if self._shadow_blocks_symbol(symbol, direction):
                continue
            cfg = dict(self.universe[symbol])
            cfg["direction"] = direction
            self._latest_target_snapshot = dict(item)
            return symbol, cfg, dict(self._prices.get(symbol) or {})
        return None

    def _shadow_blocks_symbol(self, symbol: str, direction: str) -> bool:
        for pos in self.positions:
            if pos.symbol == symbol and str(pos.direction or "").upper() == direction:
                return True
        for shadow in self.shadow_trades:
            if shadow.symbol == symbol and str(shadow.direction or "").upper() == direction:
                return True
        return False

    def _create_shadow(self, symbol: str, cfg: Dict[str, float], ticker: Dict[str, Any]) -> Optional[AlpacaShadowTrade]:
        if len(self.shadow_trades) >= self.SHADOW_MAX_ACTIVE:
            return None
        direction = str(cfg.get("direction") or "BUY").upper()
        if self._shadow_blocks_symbol(symbol, direction):
            return None
        if not self._ticker_is_actionable(ticker):
            return None
        price = _finite_number(ticker.get("price"), positive=True)
        if price is None:
            return None
        size = float(cfg.get("size", 1.0) or 1.0)
        target_move_pct = max(float(cfg.get("tp_pct", 0.0) or 0.0) * 0.35, 0.05)
        score = 0.0
        for candidate in self._latest_candidate_snapshot:
            if str(candidate.get("symbol") or "").upper() == symbol.upper():
                score = float(candidate.get("score", 0.0) or 0.0)
                break
        shadow = AlpacaShadowTrade(
            symbol=symbol,
            direction=direction,
            size=size,
            entry_price=price,
            target_move_pct=target_move_pct,
            score=score,
        )
        self.shadow_trades.append(shadow)
        self._latest_monitor_line = f"ALPACA SHADOW OPEN {symbol} {direction} entry={price:.4f} need={shadow.target_move_pct:.4f}%"
        logger.info("ALPACA SHADOW OPENED: %s %s entry=%.4f need %.4f%%", symbol, direction, price, shadow.target_move_pct)
        return shadow

    def _update_shadows(self) -> None:
        confidence = self._compute_self_confidence()
        validation_window = float(confidence.get("validation_window_secs", self.SHADOW_MIN_VALIDATE) or self.SHADOW_MIN_VALIDATE)
        survivors: List[AlpacaShadowTrade] = []
        for shadow in self.shadow_trades:
            ticker = self._prices.get(shadow.symbol) or {}
            price = _finite_number(ticker.get("price"), positive=True) if self._ticker_is_actionable(ticker) else None
            if price is not None:
                shadow.update(price, validation_window)
            if shadow.validated:
                survivors.append(shadow)
                continue
            if shadow.age_secs > self.SHADOW_MAX_AGE:
                self._shadow_failed_count += 1
                logger.info(
                    "ALPACA SHADOW EXPIRED: %s %s moved=%+.4f%% need=%.4f%% age=%.0fs",
                    shadow.symbol,
                    shadow.direction,
                    shadow.current_move_pct,
                    shadow.target_move_pct,
                    shadow.age_secs,
                )
                continue
            survivors.append(shadow)
        self.shadow_trades = survivors

    def _promote_shadow(self, shadow: AlpacaShadowTrade) -> Optional[AlpacaMomentumPosition]:
        ticker = dict(self._prices.get(shadow.symbol) or {})
        cfg = dict(self.universe.get(shadow.symbol) or {})
        if not ticker or not cfg:
            return None
        cfg["direction"] = shadow.direction
        cfg["size"] = shadow.size
        pos = self._open_position(shadow.symbol, cfg, ticker)
        if pos is not None:
            self._shadow_validated_count += 1
            self._latest_monitor_line = f"ALPACA SHADOW PROMOTED {shadow.symbol} {shadow.direction} order={pos.order_id}"
            logger.info("ALPACA SHADOW PROMOTED: %s %s peak=%+.4f%%", shadow.symbol, shadow.direction, shadow.peak_move_pct)
        return pos

    def _validated_fill_receipt(
        self,
        result: Any,
        *,
        expected_symbol: str,
        expected_side: str,
        expected_qty: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(result, dict) or str(result.get("status") or "").lower() != "filled":
            return None
        order_id = str(result.get("id") or "").strip()
        normalized_id = order_id.lower().replace("-", "_")
        if not order_id or normalized_id in {"dry_run_id", "dryrun_id", "test_order", "mock_order"}:
            return None
        symbol = str(result.get("symbol") or "").upper().strip()
        side = str(result.get("side") or "").lower().strip()
        asset_class = str(result.get("asset_class") or "us_equity").lower().strip()
        filled_qty = _finite_number(result.get("filled_qty"), positive=True)
        filled_price = _finite_number(result.get("filled_avg_price"), positive=True)
        filled_at = _provider_timestamp(result.get("filled_at"))
        if (
            symbol != expected_symbol.upper()
            or side != expected_side.lower()
            or asset_class != "us_equity"
            or filled_qty is None
            or filled_price is None
            or not _is_fresh_provider_time(filled_at, ALPACA_FILL_TTL_SECS)
        ):
            return None
        if expected_qty is not None and not math.isclose(filled_qty, float(expected_qty), rel_tol=1e-6, abs_tol=1e-9):
            return None
        fee_complete = result.get("fee_receipt_complete") is True
        fee_usd = _finite_number(result.get("total_fee_usd"), nonnegative=True) if fee_complete else None
        fee_source_id = str(result.get("fee_source_id") or "").strip() if fee_complete else ""
        fee_source_timestamp = _provider_timestamp(result.get("fee_source_timestamp")) if fee_complete else None
        if fee_complete and (
            fee_usd is None
            or not fee_source_id
            or not _is_fresh_provider_time(fee_source_timestamp, 86400.0)
        ):
            return None
        return {
            "provider_order_id": order_id,
            "symbol": symbol,
            "side": side,
            "filled_qty": filled_qty,
            "filled_avg_price": filled_price,
            "source_timestamp": filled_at,
            "received_at": time.time(),
            "source_id": f"alpaca_order:{order_id}",
            "truth_status": "real_observed",
            "generated_values": False,
            "fee_complete": fee_complete,
            "fee_usd": fee_usd,
            "fee_source_id": fee_source_id or None,
            "fee_source_timestamp": fee_source_timestamp,
        }

    def _quarantine_nonterminal_order(
        self,
        purpose: str,
        symbol: str,
        result: Any,
        *,
        side: str,
        quantity: float,
    ) -> None:
        if not isinstance(result, dict):
            self._latest_order_error = f"{symbol} {purpose} returned no provider receipt"
            return
        order_id = str(result.get("id") or "").strip()
        normalized_id = order_id.lower().replace("-", "_")
        status = str(result.get("status") or "unknown").lower()
        if getattr(self.client, "dry_run", False) or normalized_id in {"dry_run_id", "dryrun_id"}:
            self._latest_order_error = f"{symbol} {purpose} not submitted (dry_run)"
            return
        if order_id and status not in {"rejected", "canceled", "expired", "failed"}:
            self._pending_orders[f"{purpose}:{symbol}"] = {
                "purpose": purpose,
                "symbol": symbol,
                "side": side,
                "requested_quantity": quantity,
                "provider_order_id": order_id,
                "provider_status": status,
                "truth_status": "real_observed",
                "source_id": f"alpaca_order:{order_id}",
                "source_timestamp": _provider_timestamp(result.get("updated_at") or result.get("submitted_at")),
                "received_at": time.time(),
                "generated_values": False,
                "eligible_for_learning": False,
                "reason": "terminal_fill_receipt_pending_reconciliation",
            }
            self._latest_order_error = f"{symbol} {purpose} pending provider reconciliation"
        else:
            self._latest_order_error = f"{symbol} {purpose} rejected or receipt invalid"

    def _sync_positions(self) -> None:
        if not self.client:
            return
        try:
            open_positions = self.client.get_positions() or []
        except Exception as exc:
            self._latest_order_error = f"position_read_unavailable:{exc}"
            return
        received_at = time.time()
        synced: List[AlpacaMomentumPosition] = []
        existing = {p.symbol: p for p in self.positions}
        for raw in open_positions:
            symbol = str(raw.get("symbol") or "").upper()
            qty_raw = _finite_number(raw.get("qty"))
            if qty_raw is None:
                continue
            qty = abs(qty_raw)
            if qty <= 0 or symbol not in self.universe:
                continue
            side = "BUY" if qty_raw > 0 else "SELL"
            entry_price = _finite_number(raw.get("avg_entry_price"), positive=True)
            if entry_price is None:
                continue
            cfg = self.universe[symbol]
            tp_price = entry_price * (1 + float(cfg["tp_pct"]) / 100.0) if side == "BUY" else entry_price * (1 - float(cfg["tp_pct"]) / 100.0)
            sl_price = entry_price * (1 - float(cfg["sl_pct"]) / 100.0) if side == "BUY" else entry_price * (1 + float(cfg["sl_pct"]) / 100.0)
            current_price = _finite_number(raw.get("current_price"), positive=True)
            prior = existing.get(symbol)
            synced.append(
                AlpacaMomentumPosition(
                    symbol=symbol,
                    order_id=prior.order_id if prior is not None else "",
                    direction=side,
                    qty=qty,
                    entry_price=entry_price,
                    tp_price=tp_price,
                    sl_price=sl_price,
                    opened_at=prior.opened_at if prior is not None else None,
                    current_price=current_price,
                    entry_source_id=prior.entry_source_id if prior is not None else "alpaca_position_read",
                    entry_source_timestamp=prior.entry_source_timestamp if prior is not None else None,
                    entry_received_at=prior.entry_received_at if prior is not None else received_at,
                    entry_commission_usd=prior.entry_commission_usd if prior is not None else None,
                    entry_fee_complete=prior.entry_fee_complete if prior is not None else False,
                    entry_reference_price=prior.entry_reference_price if prior is not None else None,
                    entry_spread_usd=prior.entry_spread_usd if prior is not None else None,
                    generated_values=False,
                    eligible_for_learning=prior.eligible_for_learning if prior is not None else False,
                )
            )
        self.positions = synced
        open_symbols = {position.symbol for position in synced}
        for key, pending in list(self._pending_orders.items()):
            purpose = str(pending.get("purpose") or "")
            symbol = str(pending.get("symbol") or "")
            if (purpose == "open" and symbol in open_symbols) or (purpose in {"close", "liquidate"} and symbol not in open_symbols):
                self._pending_orders.pop(key, None)

    def free_existing_assets(self) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        liquidated: List[Dict[str, Any]] = []
        open_positions = self.client.get_positions() or []
        for raw in open_positions:
            symbol = str(raw.get("symbol") or "").upper()
            qty_raw = _finite_number(raw.get("qty"))
            if qty_raw is None:
                continue
            qty = abs(qty_raw)
            if not symbol or qty <= 0:
                continue
            side = "sell" if qty_raw > 0 else "buy"
            result = self.client.place_market_order(symbol, side, quantity=qty)
            fill = self._validated_fill_receipt(
                result,
                expected_symbol=symbol,
                expected_side=side,
                expected_qty=qty,
            )
            if fill is None:
                self._quarantine_nonterminal_order("liquidate", symbol, result, side=side, quantity=qty)
                continue
            liquidated.append({
                "symbol": symbol,
                "qty": fill["filled_qty"],
                "side": side,
                "order_id": fill["provider_order_id"],
                "reason": "FREE_ASSETS",
                "truth_status": "real_observed",
                "source_id": fill["source_id"],
                "source_timestamp": fill["source_timestamp"],
                "received_at": fill["received_at"],
                "generated_values": False,
                "eligible_for_learning": False,
            })
        if liquidated:
            self._latest_monitor_line = f"ALPACA FREE ASSETS closed={len(liquidated)}"
        return liquidated

    def _open_position(self, symbol: str, cfg: Dict[str, float], ticker: Dict[str, Any]) -> Optional[AlpacaMomentumPosition]:
        if not self.client:
            return None
        direction = str(cfg.get("direction") or "BUY").upper()
        qty = _finite_number(cfg.get("size"), positive=True)
        if direction not in {"BUY", "SELL"} or qty is None or not self._ticker_is_actionable(ticker):
            self._latest_order_error = f"{symbol} open blocked: fresh quote or valid size unavailable"
            return None
        if f"open:{symbol}" in self._pending_orders:
            self._latest_order_error = f"{symbol} open blocked: provider reconciliation pending"
            return None
        price = _finite_number(ticker.get("price"), positive=True)
        costs = self._capital_style_cost_profile(symbol, qty, price, float(cfg.get("tp_pct", 0.0) or 0.0)) if price is not None else {}
        if costs.get("eligible_for_external_action") is not True:
            self._latest_order_error = f"{symbol} open blocked: complete provider execution-cost receipt unavailable"
            return None
        orchestrator_receipt = self._orchestrator_pretrade_gate(symbol, direction)
        if orchestrator_receipt.get("approved") is not True:
            self._latest_order_error = (
                f"{symbol} open blocked: orchestrator "
                f"{orchestrator_receipt.get('reason') or 'no_data'}"
            )
            return None
        side = "buy" if direction == "BUY" else "sell"
        reference_price = _finite_number(ticker.get("ask" if direction == "BUY" else "bid"), positive=True)
        bid = _finite_number(ticker.get("bid"), positive=True)
        ask = _finite_number(ticker.get("ask"), positive=True)
        if reference_price is None or bid is None or ask is None:
            return None
        result = self.client.place_market_order(symbol, side, quantity=qty)
        fill = self._validated_fill_receipt(result, expected_symbol=symbol, expected_side=side)
        if fill is None:
            self._quarantine_nonterminal_order("open", symbol, result, side=side, quantity=qty)
            return None
        entry_price = fill["filled_avg_price"]
        filled_qty = fill["filled_qty"]
        tp_price = entry_price * (1 + float(cfg["tp_pct"]) / 100.0) if direction == "BUY" else entry_price * (1 - float(cfg["tp_pct"]) / 100.0)
        sl_price = entry_price * (1 - float(cfg["sl_pct"]) / 100.0) if direction == "BUY" else entry_price * (1 + float(cfg["sl_pct"]) / 100.0)
        pos = AlpacaMomentumPosition(
            symbol=symbol,
            order_id=fill["provider_order_id"],
            direction=direction,
            qty=filled_qty,
            entry_price=entry_price,
            tp_price=tp_price,
            sl_price=sl_price,
            opened_at=fill["source_timestamp"],
            current_price=entry_price,
            entry_source_id=fill["source_id"],
            entry_source_timestamp=fill["source_timestamp"],
            entry_received_at=fill["received_at"],
            entry_commission_usd=fill["fee_usd"],
            entry_fee_complete=fill["fee_complete"],
            entry_reference_price=reference_price,
            entry_spread_usd=((ask - bid) / 2.0) * filled_qty,
            generated_values=False,
            eligible_for_learning=fill["fee_complete"],
        )
        self.positions = [p for p in self.positions if p.symbol != symbol]
        self.positions.append(pos)
        self.stats["trades_opened"] += 1
        self._latest_order_error = ""
        logger.info("ALPACA CAPITAL OPEN: %s %s qty=%s entry=%.4f", symbol, direction, qty, entry_price)
        return pos

    def _close_position(self, pos: AlpacaMomentumPosition, reason: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        ticker = self._prices.get(pos.symbol) or {}
        if not self._ticker_is_actionable(ticker):
            self._latest_order_error = f"{pos.symbol} close blocked: fresh provider quote unavailable"
            return None
        if f"close:{pos.symbol}" in self._pending_orders:
            self._latest_order_error = f"{pos.symbol} close blocked: provider reconciliation pending"
            return None
        side = "sell" if pos.direction == "BUY" else "buy"
        result = self.client.place_market_order(pos.symbol, side, quantity=pos.qty)
        fill = self._validated_fill_receipt(
            result,
            expected_symbol=pos.symbol,
            expected_side=side,
            expected_qty=pos.qty,
        )
        if fill is None:
            self._quarantine_nonterminal_order("close", pos.symbol, result, side=side, quantity=pos.qty)
            return None
        exit_price = fill["filled_avg_price"]
        closed_qty = min(pos.qty, fill["filled_qty"])
        gross_pnl = ((exit_price - pos.entry_price) * closed_qty) if pos.direction == "BUY" else ((pos.entry_price - exit_price) * closed_qty)
        fees_complete = bool(pos.entry_fee_complete and fill["fee_complete"])
        total_fee = (
            float(pos.entry_commission_usd) + float(fill["fee_usd"])
            if fees_complete and pos.entry_commission_usd is not None and fill["fee_usd"] is not None
            else None
        )
        net_pnl = gross_pnl - total_fee if total_fee is not None else None
        self.stats["trades_closed"] += 1
        if net_pnl is not None:
            self.stats["total_pnl_usd"] += net_pnl
            if net_pnl >= 0:
                self.stats["winning_trades"] += 1
            else:
                self.stats["losing_trades"] += 1
        record = {
            "symbol": pos.symbol,
            "direction": pos.direction,
            "entry_price": pos.entry_price,
            "exit_price": exit_price,
            "filled_qty": closed_qty,
            "gross_pnl": gross_pnl,
            "reported_fees_usd": total_fee,
            "net_pnl": net_pnl,
            "reason": reason,
            "closed_at": fill["source_timestamp"],
            "truth_status": "real_derived" if net_pnl is not None else "incomplete",
            "source_id": f"{pos.entry_source_id}+{fill['source_id']}",
            "source_timestamp": fill["source_timestamp"],
            "received_at": fill["received_at"],
            "generated_values": False,
            "eligible_for_learning": net_pnl is not None,
            "incomplete_reason": None if net_pnl is not None else "complete_provider_fee_receipts_unavailable",
        }
        if net_pnl is not None:
            bid = _finite_number(ticker.get("bid"), positive=True)
            ask = _finite_number(ticker.get("ask"), positive=True)
            entry_reference = _finite_number(pos.entry_reference_price, positive=True)
            entry_spread = _finite_number(pos.entry_spread_usd, nonnegative=True)
            if None not in (bid, ask, entry_reference, entry_spread) and ask > bid:
                exit_reference = bid if side == "sell" else ask
                entry_slippage = (
                    max(pos.entry_price - entry_reference, 0.0) * closed_qty
                    if pos.direction == "BUY"
                    else max(entry_reference - pos.entry_price, 0.0) * closed_qty
                )
                exit_slippage = (
                    max(exit_reference - exit_price, 0.0) * closed_qty
                    if side == "sell"
                    else max(exit_price - exit_reference, 0.0) * closed_qty
                )
                exit_spread = ((ask - bid) / 2.0) * closed_qty
                reference_notional = pos.entry_price * closed_qty
                observed_cost_usd = entry_spread + exit_spread + entry_slippage + exit_slippage + total_fee
                if reference_notional > 0:
                    cost_receipt = {
                        "total_cost_pct": (observed_cost_usd / reference_notional) * 100.0,
                        "sample_count": 1,
                        "truth_status": "real_derived",
                        "source_id": f"{pos.entry_source_id}+{fill['source_id']}+provider_fee_receipts",
                        "source_timestamp": fill["source_timestamp"],
                        "generated_values": False,
                        "field_provenance": {
                            "entry_fill": pos.entry_source_id,
                            "exit_fill": fill["source_id"],
                            "quote": ticker.get("source_id"),
                            "fee_receipts": [pos.entry_source_id, fill["fee_source_id"]],
                        },
                    }
                    if self.record_execution_cost_receipt(pos.symbol, cost_receipt):
                        record["execution_cost_receipt"] = cost_receipt
        if net_pnl is not None and self._signal_brain is not None and hasattr(self._signal_brain, "learn_from_outcome"):
            try:
                return_pct = abs(gross_pnl) / max(pos.entry_price * closed_qty, 1e-12) * 100.0
                record["learning_update"] = self._signal_brain.learn_from_outcome(
                    pos.symbol,
                    net_pnl,
                    confidence=max(0.1, min(1.0, return_pct / 2.0)),
                )
            except Exception:
                pass
        if record["eligible_for_learning"]:
            self._publish_learning_update(record)
        self._recent_closed_trades.append(record)
        self._recent_closed_trades = self._recent_closed_trades[-5:]
        logger.info(
            "ALPACA CAPITAL CLOSE: %s %s gross=%+.4f net=%s reason=%s",
            pos.symbol,
            pos.direction,
            gross_pnl,
            f"{net_pnl:+.4f}" if net_pnl is not None else "NO_DATA",
            reason,
        )
        return record

    def _monitor_positions(self) -> List[Dict[str, Any]]:
        closed: List[Dict[str, Any]] = []
        remaining: List[AlpacaMomentumPosition] = []
        for pos in self.positions:
            ticker = self._prices.get(pos.symbol) or {}
            if not self._ticker_is_actionable(ticker):
                remaining.append(pos)
                continue
            price = _finite_number(ticker.get("price"), positive=True)
            if price is None:
                remaining.append(pos)
                continue
            pos.current_price = price
            hit_tp = price >= pos.tp_price if pos.direction == "BUY" else price <= pos.tp_price
            hit_sl = price <= pos.sl_price if pos.direction == "BUY" else price >= pos.sl_price
            if hit_tp:
                record = self._close_position(pos, "TP_HIT")
                if record:
                    closed.append(record)
                    continue
                remaining.append(pos)
                continue
            if hit_sl:
                record = self._close_position(pos, "SL_HIT")
                if record:
                    closed.append(record)
                    continue
                remaining.append(pos)
                continue
            remaining.append(pos)
        self.positions = remaining
        return closed

    def _build_lane_snapshot(self) -> Dict[str, Any]:
        lanes: Dict[str, Any] = {}
        for direction in ("BUY", "SELL"):
            live = next((pos for pos in self.positions if pos.direction == direction), None)
            validated = next((shadow for shadow in self.shadow_trades if shadow.direction == direction and shadow.validated), None)
            queued = next((shadow for shadow in self.shadow_trades if shadow.direction == direction and not shadow.validated), None)
            next_action = "manage_position" if live else ("promote_shadow" if validated else ("await_shadow_validation" if queued else "scan_for_candidate"))
            lanes[direction] = {
                "next_action": next_action,
                "position_symbol": live.symbol if live else "",
                "validated_shadow_symbol": validated.symbol if validated else "",
                "queued_shadow_symbol": queued.symbol if queued else "",
            }
        self._lane_snapshot = lanes
        return lanes

    def get_account_snapshot(self) -> Dict[str, Any]:
        received_at = time.time()
        if not self.client:
            return {
                "equity_usd": None,
                "cash_usd": None,
                "buying_power_usd": None,
                "truth_status": "no_data",
                "reason": "alpaca_client_unavailable",
                "source_id": "alpaca_account",
                "source_timestamp": None,
                "received_at": received_at,
                "generated_values": False,
            }
        try:
            acct = self.client.get_account() or {}
        except Exception as exc:
            return {
                "equity_usd": None,
                "cash_usd": None,
                "buying_power_usd": None,
                "truth_status": "no_data",
                "reason": f"alpaca_account_read_failed:{exc}",
                "source_id": "alpaca_account",
                "source_timestamp": None,
                "received_at": received_at,
                "generated_values": False,
            }
        equity = _finite_number(acct.get("equity"), positive=True)
        cash = _finite_number(acct.get("cash"))
        buying_power = _finite_number(acct.get("buying_power"), nonnegative=True)
        if None in (equity, cash, buying_power):
            return {
                "equity_usd": None,
                "cash_usd": None,
                "buying_power_usd": None,
                "truth_status": "no_data",
                "reason": "alpaca_account_fields_missing_or_invalid",
                "source_id": "alpaca_account",
                "source_timestamp": _provider_timestamp(acct.get("updated_at")),
                "received_at": received_at,
                "generated_values": False,
            }
        return {
            "equity_usd": equity,
            "cash_usd": cash,
            "buying_power_usd": buying_power,
            "truth_status": "real_observed",
            "reason": "synchronous_provider_read",
            "source_id": "alpaca_account",
            "source_timestamp": _provider_timestamp(acct.get("updated_at")),
            "received_at": received_at,
            "generated_values": False,
        }

    def status_lines(self) -> List[str]:
        snap = self.get_account_snapshot()
        runtime_m = (time.time() - self.start_time) / 60.0
        equity = _finite_number(snap.get("equity_usd"), positive=True)
        cash = _finite_number(snap.get("cash_usd"))
        buying_power = _finite_number(snap.get("buying_power_usd"), nonnegative=True)
        starting_equity = _finite_number(self.starting_equity_usd, positive=True)
        eq_delta = equity - starting_equity if equity is not None and starting_equity is not None else None
        growth = self._compute_growth_metrics()
        confidence = self._compute_self_confidence()
        if snap.get("truth_status") == "real_observed":
            account_line = (
                f"  Equity=${_format_observed(equity, '.2f')} | Cash=${_format_observed(cash, '.2f')} "
                f"| BuyingPower=${_format_observed(buying_power, '.2f')} | EqDelta={_format_observed(eq_delta, '+.2f')}"
            )
        else:
            account_line = f"  Account=NO_DATA | reason={snap.get('reason', 'provider_receipt_unavailable')}"
        lines = [
            f"  ALPACA STATUS | runtime={runtime_m:.1f}m",
            account_line,
            (
                f"  ALPACA STOCKS: {len(self.positions)} open / {int(self.stats['trades_closed'])} closed | "
                f"W:{int(self.stats['winning_trades'])} L:{int(self.stats['losing_trades'])} | "
                f"PnL:${float(self.stats['total_pnl_usd']):+.2f} | gate:open"
            ),
            f"  Shadows: {len(self.shadow_trades)} active | validated={self._shadow_validated_count} failed={self._shadow_failed_count}",
            (
                f"  Confidence: {_format_observed(confidence.get('score'), '.2f')} "
                f"| boost={float(confidence.get('boost_multiplier', 1.0) or 1.0):.2f}x "
                f"| promote_wait={float(confidence.get('validation_window_secs', self.SHADOW_MIN_VALIDATE) or self.SHADOW_MIN_VALIDATE):.1f}s "
                f"| mode={confidence.get('reason', 'n/a')}"
            ),
            (
                f"  Growth: eq={_format_observed(growth.get('equity_growth_pct'), '+.2f')}% "
                f"| pnl/hr=${_format_observed(growth.get('pnl_per_hour_usd'), '+.3f')} "
                f"| trades/hr={_format_observed(growth.get('trades_per_hour'), '.2f')} "
                f"| avg/close=${_format_observed(growth.get('avg_pnl_per_close_usd'), '+.3f')} "
                f"| trend={growth.get('trend', 'no_data')}"
            ),
        ]
        if self._signal_brain is not None and hasattr(self._signal_brain, "learning_snapshot"):
            try:
                learning = self._signal_brain.learning_snapshot()
                lines.append(
                    f"  Learning: feedback={int(learning.get('total_feedback', 0) or 0)} "
                    f"| win_bias={float(learning.get('win_bias', 0.0) or 0.0):.2f}"
                )
            except Exception:
                pass
        if self._universe_snapshot:
            lines.append(
                f"  Universe: mode={self._universe_snapshot.get('mode', 'unknown')} "
                f"size={int(self._universe_snapshot.get('size', len(self.universe)) or len(self.universe))} "
                f"reason={self._universe_snapshot.get('reason', 'n/a')}"
            )
        if self._scan_window_snapshot:
            lines.append(
                f"  ScanWindow: {int(self._scan_window_snapshot.get('size', 0) or 0)}/"
                f"{int(self._scan_window_snapshot.get('total', len(self.universe)) or len(self.universe))} "
                f"start={int(self._scan_window_snapshot.get('start', 0) or 0)}"
            )
        if self._lane_snapshot:
            buy_lane = self._lane_snapshot.get("BUY", {}) or {}
            sell_lane = self._lane_snapshot.get("SELL", {}) or {}
            lines.append(
                f"  Lanes: BUY={buy_lane.get('next_action', 'scan_for_candidate')} "
                f"[pos={buy_lane.get('position_symbol', '-') or '-'} valid={buy_lane.get('validated_shadow_symbol', '-') or '-'} queue={buy_lane.get('queued_shadow_symbol', '-') or '-'}]"
            )
            lines.append(
                f"         SELL={sell_lane.get('next_action', 'scan_for_candidate')} "
                f"[pos={sell_lane.get('position_symbol', '-') or '-'} valid={sell_lane.get('validated_shadow_symbol', '-') or '-'} queue={sell_lane.get('queued_shadow_symbol', '-') or '-'}]"
            )
        if self._latest_order_error:
            lines.append(f"    Last order: {self._latest_order_error}")
        if self._latest_target_snapshot:
            tgt = self._latest_target_snapshot
            lines.append(
                f"  Target: {tgt.get('symbol', '?')} {tgt.get('direction', '?')} [stock] "
                f"score={float(tgt.get('score', 0.0) or 0.0):.3f} "
                f"chg={float(tgt.get('change_pct', 0.0) or 0.0):+.3f}% "
                f"goal=${float(tgt.get('profit_target_usd', ALPACA_MIN_TARGET_USD) or ALPACA_MIN_TARGET_USD):.2f}"
            )
            lines.append(
                f"    HFT: net=${_format_observed(tgt.get('expected_net_profit'), '+.4f')} "
                f"cost=${_format_observed(tgt.get('round_trip_cost'), '.4f')} "
                f"evidence={tgt.get('truth_status', 'no_data')} "
                f"coh={_format_observed(tgt.get('brain_coherence'), '.3f')}"
            )
            lines.append(
                f"    Intel: timeline={float(tgt.get('timeline_confidence', 0.0) or 0.0):.2f} "
                f"fusion={float(tgt.get('fusion_global_coherence', 0.0) or 0.0):.2f} "
                f"orch={tgt.get('orchestrator_reason', 'n/a')}"
            )
        if self._latest_candidate_snapshot:
            lines.append("  Top 7 candidates:")
            for idx, item in enumerate(self._latest_candidate_snapshot[:7], start=1):
                lines.append(
                    f"    #{idx} {item.get('symbol', '?')} {item.get('direction', '?')} [stock] "
                    f"score={float(item.get('score', 0.0) or 0.0):.3f} "
                    f"chg={float(item.get('change_pct', 0.0) or 0.0):+.3f}% "
                    f"spr={float(item.get('spread_pct', 0.0) or 0.0):.3f}% "
                    f"net=${_format_observed(item.get('expected_net_profit'), '+.4f')} "
                    f"goal=${float(item.get('profit_target_usd', ALPACA_MIN_TARGET_USD) or ALPACA_MIN_TARGET_USD):.2f}"
                )
        swarm_leader = dict(self._swarm_snapshot.get("leader", {}) or {})
        if swarm_leader:
            lines.append(
                f"  Swarm: {swarm_leader.get('symbol', '?')} {swarm_leader.get('direction', '?')} "
                f"votes={int(swarm_leader.get('votes', 0) or 0)} "
                f"swarm={float(swarm_leader.get('swarm_score', 0.0) or 0.0):.3f}"
            )
        for pos in self.positions:
            lines.append(pos.one_line())
        for shadow in self.shadow_trades[:4]:
            lines.append(
                f"    SHADOW {shadow.direction:4} {shadow.symbol:5} [stock] "
                f"entry:{shadow.entry_price:.4f} now:{shadow.current_price or shadow.entry_price:.4f} "
                f"move:{shadow.current_move_pct:+.3f}% need:{shadow.target_move_pct:.3f}% "
                f"age:{shadow.age_secs/60.0:.1f}m{' VALID' if shadow.validated else ''}"
            )
        for trade in reversed(self._recent_closed_trades[-3:]):
            lines.append(
                f"  CLOSE: {trade.get('symbol', '?')} {trade.get('direction', '?')} "
                f"net={_format_observed(trade.get('net_pnl'), '+.2f')} USD "
                f"gross={_format_observed(trade.get('gross_pnl'), '+.2f')} USD "
                f"evidence={trade.get('truth_status', 'no_data')} reason={trade.get('reason', '?')}"
            )
        if self._registry_snapshot.get("categories"):
            lines.append(f"  Registry: {len(self._registry_snapshot.get('categories', {}))} categories linked")
        if self._decision_snapshot:
            if self._decision_snapshot.get("decision"):
                decision = self._decision_snapshot.get("decision", {}) or {}
                lines.append(
                    f"  Decision: {self._decision_snapshot.get('symbol', '?')} {self._decision_snapshot.get('side', '?')} "
                    f"-> {decision.get('type', '?')} conf={float(decision.get('confidence', 0.0) or 0.0):.2f}"
                )
            elif self._decision_snapshot.get("error"):
                lines.append(f"  Decision: error={self._decision_snapshot.get('error')}")
        if self._orchestrator_snapshot:
            lines.append(
                f"  Orchestrator: {self._orchestrator_snapshot.get('symbol', '?')} "
                f"{self._orchestrator_snapshot.get('side', '?')} "
                f"approved={self._orchestrator_snapshot.get('approved', False)} "
                f"reason={self._orchestrator_snapshot.get('reason', '')}"
            )
        if self._thought_bus_snapshot:
            if self._thought_bus_snapshot.get("error"):
                lines.append(f"  ThoughtBus: error={self._thought_bus_snapshot.get('error')}")
            else:
                lines.append(
                    f"  ThoughtBus: market={int(self._thought_bus_snapshot.get('market_events', 0) or 0)} "
                    f"decision={int(self._thought_bus_snapshot.get('decision_events', 0) or 0)}"
                )
        if self._cognition_snapshot:
            if self._cognition_snapshot.get("error"):
                lines.append(f"  Cognition: error={self._cognition_snapshot.get('error')}")
            else:
                lines.append(
                    f"  Cognition: brain={int(self._cognition_snapshot.get('cognition_events', 0) or 0)} "
                    f"queen={int(self._cognition_snapshot.get('queen_events', 0) or 0)}"
                )
        if self._harmonic_wiring_audit:
            ready = sum(1 for value in self._harmonic_wiring_audit.values() if value)
            lines.append(f"  Harmonics: {ready}/{len(self._harmonic_wiring_audit)} wired")
        self._latest_status_lines = lines
        return lines

    def get_dashboard_payload(self) -> Dict[str, Any]:
        growth = self._compute_growth_metrics()
        snap = self.get_account_snapshot()
        return {
            "exchange": "alpaca",
            "mode": "capital_style_stocks",
            "ok": self.enabled,
            "equity_usd": snap["equity_usd"],
            "cash_usd": snap["cash_usd"],
            "buying_power_usd": snap["buying_power_usd"],
            "account_snapshot": dict(snap),
            "positions": [
                {
                    "symbol": pos.symbol,
                    "order_id": pos.order_id,
                    "direction": pos.direction,
                    "qty": pos.qty,
                    "entry_price": pos.entry_price,
                    "current_price": pos.current_price,
                    "tp_price": pos.tp_price,
                    "sl_price": pos.sl_price,
                    "age_secs": pos.age_secs,
                    "pnl_pct": pos.pnl_pct,
                    "entry_source_id": pos.entry_source_id,
                    "entry_source_timestamp": pos.entry_source_timestamp,
                    "entry_received_at": pos.entry_received_at,
                    "generated_values": pos.generated_values,
                    "eligible_for_learning": pos.eligible_for_learning,
                }
                for pos in self.positions
            ],
            "shadows": [
                {
                    "symbol": shadow.symbol,
                    "direction": shadow.direction,
                    "size": shadow.size,
                    "entry_price": shadow.entry_price,
                    "current_price": shadow.current_price,
                    "target_move_pct": shadow.target_move_pct,
                    "peak_move_pct": shadow.peak_move_pct,
                    "validated": shadow.validated,
                    "age_secs": shadow.age_secs,
                }
                for shadow in self.shadow_trades
            ],
            "lane_snapshot": dict(self._lane_snapshot),
            "swarm_snapshot": dict(self._swarm_snapshot),
            "registry_snapshot": dict(self._registry_snapshot),
            "decision_snapshot": dict(self._decision_snapshot),
            "orchestrator_snapshot": dict(self._orchestrator_snapshot),
            "timeline_snapshot": dict(self._timeline_snapshot),
            "fusion_snapshot": dict(self._fusion_snapshot),
            "harmonic_wiring_audit": dict(self._harmonic_wiring_audit),
            "universe_snapshot": dict(self._universe_snapshot),
            "scan_window_snapshot": dict(self._scan_window_snapshot),
            "price_failures": dict(self._price_failures),
            "pending_orders": dict(self._pending_orders),
            "execution_cost_receipts": dict(self._execution_cost_receipts),
            "target_snapshot": dict(self._latest_target_snapshot),
            "candidate_snapshot": list(self._latest_candidate_snapshot),
            "growth_metrics": dict(growth),
            "recent_closed_trades": list(self._recent_closed_trades[-5:]),
            "thought_bus_snapshot": dict(self._thought_bus_snapshot),
            "cognition_snapshot": dict(self._cognition_snapshot),
        }

    def tick(self) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        self._refresh_prices()
        self._sync_positions()
        now = time.time()
        closed: List[Dict[str, Any]] = []
        if now - self._last_monitor >= MONITOR_INTERVAL_SECS:
            self._last_monitor = now
            closed.extend(self._monitor_positions())
            self._update_shadows()
            for shadow in list(self.shadow_trades):
                if shadow.validated:
                    pos = self._promote_shadow(shadow)
                    if pos is not None and shadow in self.shadow_trades:
                        self.shadow_trades.remove(shadow)
        if now - self._last_scan >= SCAN_INTERVAL_SECS:
            self._last_scan = now
            if len(self.positions) < MAX_POSITIONS:
                best = self._find_best_opportunity()
                if best is not None:
                    symbol, cfg, ticker = best
                    self._create_shadow(symbol, cfg, ticker)
        if now - float(self._harmonic_wiring_audit_at or 0.0) > 120.0:
            self._harmonic_wiring_audit = self._build_harmonic_wiring_audit()
            self._harmonic_wiring_audit_at = now
        self._probability_validation_snapshot()
        self._build_lane_snapshot()
        self._refresh_registry_snapshot()
        self._update_coordination_snapshots()
        self._publish_market_snapshot_to_thought_bus()
        self._refresh_thought_bus_snapshot()
        self.status_lines()
        return closed
