"""
trading_hive_mind.py  —  The Unity Coordinator

Every sub-trader (Kraken Margin, Capital CFD, Alpaca/main scan) is a soldier.
The Hive Mind is their Queen: she shares intelligence, enforces discipline,
and points EVERY soldier toward the SAME common goal.

Rules of Unity:
  1. ONE active trade per exchange at a time — no capital scatter
  2. ALL trade gates pass through ONE shared Quadrumvirate check (TTL-cached)
  3. Market Harp ripple signals are injected into ALL traders before their tick
  4. Session PnL target is shared and visible across every system
  5. ThoughtBus broadcast every cycle keeps the entire organism synchronised
  6. After each tick the hive publishes one unified state to all listeners

The Hive Mind does NOT implement trading logic — it COORDINATES.
All execution stays in the specialist traders (Kraken, Capital, Alpaca).

Author: Aureon Trading System  |  March 2026
"""

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ── QUADRUMVIRATE IMPORTS ───────────────────────────────────────────────────────
try:
    from aureon.intelligence.aureon_seer_integration import seer_should_trade
    from aureon.trading.aureon_lyra_integration import lyra_should_trade
    HAS_QUAD_GATES = True
except ImportError:
    HAS_QUAD_GATES = False
    seer_should_trade = None   # type: ignore
    lyra_should_trade = None   # type: ignore

# ── THOUGHTBUS ─────────────────────────────────────────────────────────────────
try:
    from aureon.core.aureon_thought_bus import Thought
    HAS_THOUGHT_BUS = True
except ImportError:
    Thought = None             # type: ignore
    HAS_THOUGHT_BUS = False


# ── EXCHANGE SLOT ──────────────────────────────────────────────────────────────
@dataclass
class ExchangeSlot:
    """
    Represents one exchange's trade capacity.
    Max 1 active position per exchange — the Stallion Rule applied globally.
    """
    name:         str
    max_active:   int   = 1      # One trade per exchange
    active_count: int   = 0      # Synced from the real trader each cycle
    total_pnl:    float = 0.0
    trades:       int   = 0
    wins:         int   = 0
    losses:       int   = 0
    opened_at:    float = 0.0
    closed_at:    float = 0.0

    @property
    def is_occupied(self) -> bool:
        return self.active_count >= self.max_active

    @property
    def is_available(self) -> bool:
        return self.active_count < self.max_active

    @property
    def win_rate(self) -> float:
        return self.wins / max(self.trades, 1)

    def register_open(self) -> None:
        self.active_count = min(self.max_active, self.active_count + 1)
        self.opened_at    = time.time()
        self.trades      += 1

    def register_close(self, pnl: float = 0.0) -> None:
        self.active_count = max(0, self.active_count - 1)
        self.closed_at    = time.time()
        self.total_pnl   += pnl
        if pnl > 0:
            self.wins    += 1
        else:
            self.losses  += 1

    def status_str(self) -> str:
        state   = "TRADING" if self.is_occupied else "HUNTING"
        wr      = self.win_rate * 100
        return (
            f"  {self.name.upper():8} [{state:7}] "
            f"W:{self.wins} L:{self.losses} ({wr:.0f}%) | "
            f"PnL:{self.total_pnl:+.4f}"
        )


# ── TRADING HIVE MIND ──────────────────────────────────────────────────────────
class TradingHiveMind:
    """
    The Unity Coordinator — makes Kraken · Capital · Alpaca work as ONE organism.

    Lifecycle inside orca_complete_kill_cycle run_autonomous():

      Startup:
        _hive_mind = TradingHiveMind()
        _hive_mind.set_bus(self.bus)

      Every cycle (replaces separate Kraken+Capital tick blocks):
        _hive_mind.sync_alpaca(positions)
        closed = _hive_mind.tick(
            kraken_trader  = self.margin_penny_trader,
            capital_trader = self.capital_cfd_trader,
            price_map      = batch_prices,
            market_harp    = _market_harp,
        )
        # closed = {'kraken': [...], 'capital': [...]}

      Before main scan:
        if _hive_mind.alpaca_slot_available():
            # scan for new opportunity

      After Alpaca trade opens:
        _hive_mind.register_alpaca_open()

      After Alpaca trade closes:
        _hive_mind.register_alpaca_close(pnl)

      Each cycle:
        _hive_mind.broadcast(session_stats)
    """

    # Session goal can be overridden via env HIVE_SESSION_TARGET_GBP
    DEFAULT_SESSION_TARGET_GBP: float = 50.0
    GATE_TTL_SECS:              float = 30.0    # How long to cache Seer+Lyra result
    BROADCAST_INTERVAL_SECS:    float = 15.0    # Min gap between ThoughtBus publishes

    def __init__(self) -> None:
        # Per-exchange slots
        self.slots: Dict[str, ExchangeSlot] = {
            "kraken":  ExchangeSlot("kraken"),
            "capital": ExchangeSlot("capital"),
            "alpaca":  ExchangeSlot("alpaca"),
        }

        # Shared session goal
        self.session_target_gbp: float = float(
            os.getenv("HIVE_SESSION_TARGET_GBP", str(self.DEFAULT_SESSION_TARGET_GBP))
        )
        self.session_pnl_gbp: float = 0.0

        # Unified Quadrumvirate gate (TTL-cached — expensive to call every cycle)
        self._gate_ok:           bool  = True    # Fail-open
        self._gate_refreshed_at: float = 0.0
        self._gate_seer_ok:      bool  = True
        self._gate_lyra_ok:      bool  = True

        # Shared Market Harp ripple signals
        self._harp_boosts: Dict[str, float] = {}
        self._harp_updated_at: float = 0.0

        # ThoughtBus
        self._bus                    = None
        self._last_broadcast:  float = 0.0

        # Cycle counter
        self._cycle: int = 0

        logger.info(
            f"TradingHiveMind: ONLINE — "
            f"{len(self.slots)} exchange slots | "
            f"goal £{self.session_target_gbp:.0f}/session"
        )

    # ── BUS ────────────────────────────────────────────────────────────────────
    def set_bus(self, bus) -> None:
        """Attach the orca's ThoughtBus instance."""
        self._bus = bus

    # ── GATE ───────────────────────────────────────────────────────────────────
    def gate_open(self) -> bool:
        """
        Unified Quadrumvirate gate — cached for GATE_TTL_SECS.
        Returns True if ALL traders may open new positions.
        Fail-open: returns True if gate systems unavailable.
        """
        now = time.time()
        if now - self._gate_refreshed_at < self.GATE_TTL_SECS:
            return self._gate_ok
        self._gate_refreshed_at = now
        try:
            self._gate_seer_ok = seer_should_trade() if (HAS_QUAD_GATES and seer_should_trade) else True
            self._gate_lyra_ok = lyra_should_trade() if (HAS_QUAD_GATES and lyra_should_trade) else True
            self._gate_ok = self._gate_seer_ok and self._gate_lyra_ok
        except Exception:
            self._gate_ok = True   # Fail-open
        return self._gate_ok

    def gate_status_str(self) -> str:
        if not HAS_QUAD_GATES:
            return "GATE:unavailable(open)"
        s = "✓" if self._gate_seer_ok else "✗"
        l = "✓" if self._gate_lyra_ok else "✗"
        state = "OPEN" if self._gate_ok else "CLOSED"
        return f"GATE:{state}  Seer:{s}  Lyra:{l}"

    # ── HARP SIGNALS ───────────────────────────────────────────────────────────
    def update_harp(self, boosts: Dict[str, float]) -> None:
        """Receive fresh Market Harp ripple signals — shared across ALL traders."""
        self._harp_boosts     = boosts or {}
        self._harp_updated_at = time.time()

    def _inject_harp_to_capital(self, capital_trader) -> None:
        """Push harp boosts into the Capital CFD trader's scoring layer."""
        if capital_trader is not None:
            capital_trader._hive_boosts = self._harp_boosts

    def _inject_harp_to_kraken(self, kraken_trader) -> None:
        """Push harp boosts into the Kraken margin trader's find_best_target layer."""
        if kraken_trader is not None:
            kraken_trader._hive_boosts = self._harp_boosts

    # ── SLOT MANAGEMENT ────────────────────────────────────────────────────────
    def sync_slot(self, exchange: str, active_count: int) -> None:
        """Sync a slot's active count from the real trader's live state."""
        slot = self.slots.get(exchange)
        if slot is not None:
            slot.active_count = max(0, active_count)

    def sync_alpaca(self, orca_positions: list) -> None:
        """
        Infer the Alpaca slot count from the orca's live position list.
        Matches any position whose .exchange contains 'alpaca'.
        """
        count = sum(
            1 for p in orca_positions
            if "alpaca" in str(getattr(p, "exchange", "")).lower()
        )
        self.sync_slot("alpaca", count)

    def alpaca_slot_available(self) -> bool:
        """True when the Alpaca slot is free and the hive gate is open."""
        return self.slots["alpaca"].is_available and self.gate_open()

    def register_alpaca_open(self) -> None:
        self.slots["alpaca"].register_open()

    def register_alpaca_close(self, pnl: float = 0.0) -> None:
        self.slots["alpaca"].register_close(pnl)
        self.session_pnl_gbp += pnl

    # ── COORDINATED TICK ───────────────────────────────────────────────────────
    def tick(
        self,
        kraken_trader  = None,
        capital_trader = None,
        price_map:    Optional[Dict[str, float]] = None,
        market_harp   = None,
    ) -> Dict[str, List[dict]]:
        """
        One unified hive coordination cycle.

        Phases:
          0  Update Market Harp → gather shared ripple signals
          1  Refresh Quadrumvirate gate (TTL-cached)
          2  Sync slot counts from real trader states
          3  Inject harp boosts into ALL traders (shared intelligence)
          4  Run Kraken Margin tick — monitoring + conditional opens
          5  Run Capital CFD tick  — monitoring + conditional opens
          6  Accumulate PnL into session goal

        Returns:
          {'kraken': [closed_trade_dicts], 'capital': [closed_trade_dicts]}
        """
        self._cycle += 1
        result: Dict[str, List[dict]] = {"kraken": [], "capital": []}

        # Phase 0: update harp
        if market_harp is not None and price_map:
            harp_boosts = market_harp.tick(price_map)
            self.update_harp(harp_boosts)

        # Phase 1: refresh gate
        self.gate_open()

        # Phase 2: sync real slot counts
        if kraken_trader is not None:
            k_count = (
                (1 if getattr(kraken_trader, "active_long",  None) else 0) +
                (1 if getattr(kraken_trader, "active_short", None) else 0)
            )
            self.sync_slot("kraken", k_count)

        if capital_trader is not None:
            self.sync_slot("capital", len(getattr(capital_trader, "positions", [])))

        # Phase 3: inject shared harp intelligence
        self._inject_harp_to_kraken(kraken_trader)
        self._inject_harp_to_capital(capital_trader)

        # Phase 4: Kraken Margin tick
        # Always runs for position monitoring; orchestrator gate handles new-open blocking
        if kraken_trader is not None:
            try:
                k_closed = kraken_trader.tick()
                for ct in (k_closed or []):
                    pnl = float(ct.get("net_pnl", 0))
                    self.slots["kraken"].register_close(pnl)
                    self.session_pnl_gbp += pnl
                result["kraken"] = k_closed or []
            except Exception as _ke:
                logger.debug(f"HiveMind: Kraken tick error: {_ke}")

        # Phase 5: Capital CFD tick
        if capital_trader is not None:
            try:
                c_closed = capital_trader.tick()
                for ct in (c_closed or []):
                    pnl = float(ct.get("net_pnl", 0))
                    self.slots["capital"].register_close(pnl)
                    self.session_pnl_gbp += pnl
                result["capital"] = c_closed or []
            except Exception as _ce:
                logger.debug(f"HiveMind: Capital CFD tick error: {_ce}")

        return result

    # ── THOUGHTBUS BROADCAST ───────────────────────────────────────────────────
    def broadcast(self, session_stats: Optional[dict] = None) -> None:
        """
        Publish the unified hive state to ThoughtBus.
        Rate-limited to BROADCAST_INTERVAL_SECS.
        """
        if not self._bus or not HAS_THOUGHT_BUS:
            return
        now = time.time()
        if now - self._last_broadcast < self.BROADCAST_INTERVAL_SECS:
            return
        self._last_broadcast = now

        goal_pct = self.session_pnl_gbp / max(self.session_target_gbp, 0.01)
        total_ext_pnl = float((session_stats or {}).get("total_pnl", 0))

        try:
            self._bus.publish(Thought(
                source="trading_hive_mind",
                topic="hive.unity.status",
                payload={
                    # Session goal
                    "session_pnl_gbp":    self.session_pnl_gbp,
                    "session_target_gbp": self.session_target_gbp,
                    "goal_pct":           goal_pct,
                    # Gate state
                    "gate_open":          self._gate_ok,
                    "seer_ok":            self._gate_seer_ok,
                    "lyra_ok":            self._gate_lyra_ok,
                    # Exchange slots
                    "slots": {
                        name: {
                            "occupied":  slot.is_occupied,
                            "pnl":       slot.total_pnl,
                            "trades":    slot.trades,
                            "wins":      slot.wins,
                            "losses":    slot.losses,
                            "win_rate":  slot.win_rate,
                        }
                        for name, slot in self.slots.items()
                    },
                    # Market Harp
                    "harp_signals":  len(self._harp_boosts),
                    # Full orca PnL (all exchanges combined)
                    "total_pnl_usd": total_ext_pnl,
                    "cycle":         self._cycle,
                },
            ))
        except Exception as _be:
            logger.debug(f"HiveMind: broadcast error: {_be}")

    # ── STATUS ─────────────────────────────────────────────────────────────────
    def goal_banner(self) -> List[str]:
        """
        Prominent goal display — shown at top of each cycle report.

        Example:
          ╔═ HIVE MIND: Working toward £50/day ═══════════════════╗
          ║  Session PnL: +£12.34 (24.7%)  ▓▓▓░░░░░░░  Gate:OPEN ║
          ╚═══════════════════════════════════════════════════════╝
        """
        pnl   = self.session_pnl_gbp
        tgt   = self.session_target_gbp
        pct   = pnl / max(tgt, 0.01)
        bar_filled = int(pct * 10)
        bar   = "▓" * min(bar_filled, 10) + "░" * max(0, 10 - bar_filled)
        gate  = "OPEN" if self._gate_ok else "CLOSED"
        harp  = f"{len(self._harp_boosts)}sig" if self._harp_boosts else "quiet"

        lines = [
            f"  ┌─ HIVE MIND — Unity Command ─────────────────────────────────────┐",
            f"  │  Goal: £{tgt:.0f}/session  Today: {pnl:+.4f} ({pct:.1%})  [{bar}]  │",
            f"  │  {self.gate_status_str():40}  Harp:{harp:8}       │",
            f"  └────────────────────────────────────────────────────────────────┘",
        ]
        return lines

    def status_lines(self) -> List[str]:
        """Compact per-exchange status for periodic reporting."""
        lines = self.goal_banner()
        for slot in self.slots.values():
            lines.append(slot.status_str())
        return lines

    def one_liner(self) -> str:
        occupied = [n for n, s in self.slots.items() if s.is_occupied]
        free     = [n for n, s in self.slots.items() if s.is_available]
        gate     = "OPEN" if self._gate_ok else "CLOSED"
        return (
            f"HIVE: goal£{self.session_target_gbp:.0f} | "
            f"today:{self.session_pnl_gbp:+.2f} | "
            f"trading:{','.join(occupied) or 'none'} | "
            f"hunting:{','.join(free) or 'none'} | "
            f"gate:{gate} | harp:{len(self._harp_boosts)}sig"
        )
