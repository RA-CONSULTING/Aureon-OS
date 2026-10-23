#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   MARGIN WAVE RIDER — PRE-ENTRY MARGIN SAFETY SYSTEM                        ║
║                                                                              ║
║   CORE RULE:                                                                 ║
║   Never open a margin position unless the PROJECTED post-entry margin        ║
║   level is >= 250%.                                                          ║
║                                                                              ║
║   WHY 250%?                                                                  ║
║   Margin level = (equity / margin_used) * 100                               ║
║   At 250% with 5x leverage you can absorb a ~28% adverse price move         ║
║   before reaching the 110% danger zone — enough room to ride the wave       ║
║   back to profit without getting liquidated.                                 ║
║                                                                              ║
║   WAVE CAPACITY FORMULA:                                                     ║
║   adverse_pct = (start_margin% - danger_margin%) / (leverage * 100) * 100  ║
║   e.g.  5x lev: (250-110) / 500  * 100 = 28% cushion                       ║
║   e.g.  3x lev: (250-110) / 300  * 100 = 47% cushion                       ║
║   e.g. 10x lev: (250-110) / 1000 * 100 = 14% cushion                       ║
║                                                                              ║
║   INTEGRATION:                                                               ║
║   1. find_best_target()  — filters candidates whose entry would drop        ║
║                            projected margin below 250%                       ║
║   2. promote_shadow()    — final gate before real capital is deployed        ║
║   3. _margin_monitor.py  — shows wave capacity per open position             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

WAVE_CONFIG = {
    # Minimum projected margin level after opening a position.
    # Below this we DO NOT enter — we wait for margin to recover.
    'entry_min_margin_pct': 250.0,

    # The margin level at which the position monitor force-closes.
    # Must match LIQUIDATION_FORCE in kraken_margin_penny_trader.py.
    'danger_margin_pct': 110.0,

    # Absolute minimum free margin in USD before we even consider entering.
    # Guards against rounding errors when the account is nearly empty.
    'min_free_margin_usd': 5.0,
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarginSnapshot:
    """Live state of the margin account."""
    equity: float           # Total equity (balance + unrealised P&L)
    free_margin: float      # Available margin for new positions
    margin_used: float      # Margin currently committed
    margin_level: float     # Kraken's reported ML% (0 if no open positions)


@dataclass
class WaveCheck:
    """Result of a pre-entry wave-rider check."""
    approved: bool              # True → safe to enter
    reason: str                 # Human-readable verdict
    projected_margin_pct: float # What margin level would be after entry
    wave_capacity_pct: float    # How far price can move against us safely
    max_safe_notional: float    # Largest notional that still passes 250% gate
    snapshot: MarginSnapshot    # The margin snapshot used for the check


# ═══════════════════════════════════════════════════════════════════════════════
# CORE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class MarginWaveRider:
    """
    Pre-entry margin health validator.

    Usage
    -----
    wave_rider = MarginWaveRider()

    # From live account data:
    ok, check = wave_rider.check(equity=500, margin_used=0,
                                  new_notional=250, leverage=5)

    # Or one-shot with Kraken client:
    ok, check = wave_rider.check_from_client(kraken_client,
                                              new_notional=250, leverage=5)
    if not ok:
        print(check.reason)  # "Projected margin 180% < required 250%"
    else:
        print(f"Wave capacity: {check.wave_capacity_pct:.1f}% adverse move cushion")
    """

    def __init__(
        self,
        entry_min_margin_pct: float = None,
        danger_margin_pct: float = None,
        min_free_margin_usd: float = None,
    ):
        self.entry_min = entry_min_margin_pct or WAVE_CONFIG['entry_min_margin_pct']
        self.danger_pct = danger_margin_pct or WAVE_CONFIG['danger_margin_pct']
        self.min_free_usd = min_free_margin_usd or WAVE_CONFIG['min_free_margin_usd']

    # ------------------------------------------------------------------
    # Wave capacity maths
    # ------------------------------------------------------------------

    def wave_capacity_pct(self, start_margin_pct: float, leverage: float) -> float:
        """
        How far (%) price can move AGAINST the position before margin level
        hits the danger zone.

        Formula: (start_margin_pct - danger_margin_pct) / (leverage * 100) * 100

        Example: 250% start, 5x leverage, 110% danger
                 (250 - 110) / 500 * 100 = 28%
        """
        if leverage <= 0:
            return 0.0
        return (start_margin_pct - self.danger_pct) / (leverage * 100.0) * 100.0

    def projected_margin_pct(
        self,
        equity: float,
        current_margin_used: float,
        new_notional: float,
        leverage: float,
    ) -> float:
        """
        Project the margin level AFTER opening a position.

        margin_used_after = current_margin_used + (new_notional / leverage)
        projected_pct     = equity / margin_used_after * 100

        Returns 0.0 if any input is invalid.
        """
        if leverage <= 0 or new_notional <= 0 or equity <= 0:
            return 0.0
        additional_margin = new_notional / leverage
        total_margin = current_margin_used + additional_margin
        if total_margin <= 0:
            return 0.0
        return (equity / total_margin) * 100.0

    def max_safe_notional(
        self,
        equity: float,
        current_margin_used: float,
        leverage: float,
        free_margin: Optional[float] = None,
    ) -> float:
        """
        Maximum notional size for a new position that keeps projected
        margin level >= entry_min (250%).

        Derivation:
          entry_min = equity / (current_margin + notional/leverage) * 100
          current_margin + notional/leverage = equity / entry_min * 100
          notional/leverage = equity * 100/entry_min - current_margin
          notional = leverage * (equity * 100/entry_min - current_margin)
        """
        if equity <= 0 or leverage <= 0:
            return 0.0
        max_margin = equity * 100.0 / self.entry_min
        additional_margin_allowed = max_margin - current_margin_used
        if additional_margin_allowed <= 0:
            return 0.0
        level_limited = additional_margin_allowed * leverage
        if free_margin is None:
            return level_limited
        return min(level_limited, max(0.0, free_margin) * leverage)

    # ------------------------------------------------------------------
    # Main check
    # ------------------------------------------------------------------

    def check(
        self,
        equity: float,
        margin_used: float,
        new_notional: float,
        leverage: float,
        free_margin: Optional[float] = None,
    ) -> Tuple[bool, WaveCheck]:
        """
        Validate whether it is safe to open a new position.

        Parameters
        ----------
        equity:       total account equity
        margin_used:  margin currently committed (0 if no open positions)
        new_notional: notional value of the position we want to open
        leverage:     leverage multiplier for the new position

        Returns
        -------
        (approved: bool, check: WaveCheck)
        """
        actual_free_margin = (
            max(0.0, float(free_margin))
            if free_margin is not None
            else max(0.0, equity - margin_used)
        )
        snap = MarginSnapshot(
            equity=equity,
            free_margin=actual_free_margin,
            margin_used=margin_used,
            margin_level=(equity / margin_used * 100.0) if margin_used > 0 else 0.0,
        )

        # Gate 1: absolute free margin floor
        if snap.free_margin < self.min_free_usd:
            return False, WaveCheck(
                approved=False,
                reason=f"Free margin ${snap.free_margin:.2f} < minimum ${self.min_free_usd:.2f}",
                projected_margin_pct=0.0,
                wave_capacity_pct=0.0,
                max_safe_notional=0.0,
                snapshot=snap,
            )

        # Gate 2: projected margin after entry
        proj = self.projected_margin_pct(equity, margin_used, new_notional, leverage)
        capacity = self.wave_capacity_pct(proj, leverage)
        max_notional = self.max_safe_notional(equity, margin_used, leverage, free_margin=actual_free_margin)

        if proj < self.entry_min:
            return False, WaveCheck(
                approved=False,
                reason=(
                    f"Projected margin {proj:.1f}% < required {self.entry_min:.0f}% "
                    f"(max safe notional ${max_notional:.2f})"
                ),
                projected_margin_pct=proj,
                wave_capacity_pct=capacity,
                max_safe_notional=max_notional,
                snapshot=snap,
            )

        return True, WaveCheck(
            approved=True,
            reason=(
                f"Margin OK: projected {proj:.1f}% >= {self.entry_min:.0f}% | "
                f"wave capacity {capacity:.1f}% adverse move cushion"
            ),
            projected_margin_pct=proj,
            wave_capacity_pct=capacity,
            max_safe_notional=max_notional,
            snapshot=snap,
        )

    def check_from_client(
        self,
        kraken_client,
        new_notional: float,
        leverage: float,
    ) -> Tuple[bool, WaveCheck]:
        """
        Fetch live margin data from Kraken and run the wave check.

        Parameters
        ----------
        kraken_client: KrakenClient instance with get_trade_balance()
        new_notional:  notional USD value of the intended position
        leverage:      leverage multiplier

        Returns
        -------
        (approved: bool, check: WaveCheck)
        """
        try:
            tb = kraken_client.get_trade_balance()
            equity = float(tb.get("equity", tb.get("equity_value", 0)) or 0)
            margin_used = float(tb.get("margin_amount", tb.get("m", 0)) or 0)
            free_margin = float(
                tb.get("free_margin", tb.get("margin_free", tb.get("mf", max(0.0, equity - margin_used)))) or 0
            )
        except Exception as e:
            logger.error(f"[WaveRider] Could not fetch trade balance: {e}")
            # Fail safe — do not allow entry if we can't read margin data
            snap = MarginSnapshot(equity=0, free_margin=0, margin_used=0, margin_level=0)
            return False, WaveCheck(
                approved=False,
                reason=f"Cannot read margin data: {e}",
                projected_margin_pct=0.0,
                wave_capacity_pct=0.0,
                max_safe_notional=0.0,
                snapshot=snap,
            )

        return self.check(equity, margin_used, new_notional, leverage, free_margin=free_margin)

    # ------------------------------------------------------------------
    # Convenience: cap notional to safe size
    # ------------------------------------------------------------------

    def safe_notional(
        self,
        equity: float,
        margin_used: float,
        requested_notional: float,
        leverage: float,
        free_margin: Optional[float] = None,
    ) -> float:
        """
        Return the smaller of requested_notional and max_safe_notional.
        Use this to auto-cap position sizes instead of rejecting entirely.
        """
        max_n = self.max_safe_notional(equity, margin_used, leverage, free_margin=free_margin)
        return min(requested_notional, max_n)

    # ------------------------------------------------------------------
    # Status report
    # ------------------------------------------------------------------

    def status_line(
        self,
        equity: float,
        margin_used: float,
        leverage: float,
    ) -> str:
        """One-line status for logging / display."""
        current_ml = (equity / margin_used * 100.0) if margin_used > 0 else 0.0
        capacity = self.wave_capacity_pct(current_ml, leverage) if current_ml > 0 else 0.0
        max_n = self.max_safe_notional(equity, margin_used, leverage)
        return (
            f"Margin {current_ml:.0f}% "
            f"(need {self.entry_min:.0f}% to enter) | "
            f"wave cap {capacity:.1f}% | "
            f"max new notional ${max_n:.2f}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

WAVE_RIDER = MarginWaveRider()


def check_wave(equity: float, margin_used: float,
               new_notional: float, leverage: float) -> Tuple[bool, WaveCheck]:
    """Module-level convenience — uses the global WAVE_RIDER instance."""
    return WAVE_RIDER.check(equity, margin_used, new_notional, leverage)


def check_wave_from_client(kraken_client, new_notional: float,
                           leverage: float) -> Tuple[bool, WaveCheck]:
    """Module-level convenience — fetches live data then checks."""
    return WAVE_RIDER.check_from_client(kraken_client, new_notional, leverage)


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE DEMO / TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║         MARGIN WAVE RIDER — PRE-ENTRY SAFETY DEMO                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    rider = MarginWaveRider()

    cases = [
        # (equity, margin_used, new_notional, leverage, label)
        (500,  0,    250,  5, "Empty account, $250 @ 5x"),
        (500,  0,    500,  5, "Empty account, $500 @ 5x  [RISKY]"),
        (500,  0,   1000,  5, "Empty account, $1000 @ 5x [TOO BIG]"),
        (500,  50,   200,  5, "Existing position + new $200 @ 5x"),
        (500,  50,   400,  5, "Existing position + new $400 @ 5x [TOO BIG]"),
        (1000, 0,    200, 10, "10x leverage, $200 notional"),
        (1000, 0,    800, 10, "10x leverage, $800 notional [TOO BIG]"),
        (200,  0,    100,  3, "3x leverage, $100 notional"),
        (3,    0,     10,  5, "Tiny account — free margin too low"),
    ]

    print(f"{'Scenario':<45} {'Proj ML':>8}  {'WaveCap':>8}  {'Verdict'}")
    print("─" * 90)
    for eq, mu, notl, lev, label in cases:
        approved, wc = rider.check(eq, mu, notl, lev)
        verdict = "ENTER" if approved else "WAIT"
        sign = "  " if approved else "  "
        print(f"{sign}{label:<43} {wc.projected_margin_pct:>7.0f}%  {wc.wave_capacity_pct:>7.1f}%  {verdict}")
        if not approved:
            print(f"    {wc.reason}")
            if wc.max_safe_notional > 0:
                print(f"    Max safe notional: ${wc.max_safe_notional:.2f}")

    print("─" * 90)
    print("\nWave capacity cushion at 250% margin, various leverages:")
    for lev in [2, 3, 5, 10]:
        cap = rider.wave_capacity_pct(250, lev)
        print(f"  {lev}x leverage → {cap:.1f}% adverse price move before danger zone")
