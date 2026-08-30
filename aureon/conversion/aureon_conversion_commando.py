#!/usr/bin/env python3
"""
🦅⚔️ ADAPTIVE CONVERSION COMMANDO ⚔️🦅
======================================

The 1885 CAPM Game Commando - Capital Asset Profit Momentum

MISSION:
  Like the historic commandos of 1885, we rotate capital through
  strategic positions using Mycelium intelligence and the Conversion Ladder.

ONE GOAL: GROW_NET_PROFIT_FAST
  - Constantly scan ALL pairs on ALL exchanges (Binance, Kraken, Alpaca, ALL)
  - Track every opportunity to rotate capital for profit
  - Follow Mycelium's lead: compound profits, strengthen winners

ZERO FEAR DOCTRINE:
  🔥 NO HESITATION - We execute immediately when conditions are met
  🔥 NO DOUBT - The math is the math, trust the penny profit gate
  🔥 NO RETREAT - Only strategic repositioning (never fear-based)
  🔥 NO LIMITS - Every pair on every exchange is a target
  🔥 JUST DO IT - Analysis paralysis kills profits

COMMANDO TYPES:
    🦅 FALCON    - Fast momentum rotations (UP direction)
    🐢 TORTOISE  - Capital realignment to stables (DOWN direction)
    🦎 CHAMELEON - Adaptive bluechip rotations (LEFT/RIGHT)
    🐝 BEE       - Systematic A-Z/Z-A sweeps (pollination)

EXCHANGE COVERAGE (ALL OF THEM):
    📈 BINANCE  - Full spot universe (300+ pairs)
    📈 KRAKEN   - Full spot universe (200+ pairs)
    📈 ALPACA   - Full crypto universe (ALL USD pairs)
    📈 CAPITAL  - CFDs when available

Gary Leckey's 1885 CAPM Game | January 2026
"""

from __future__ import annotations
import logging
import os
import time
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import deque

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# 🔥 ZERO FEAR DOCTRINE - ENCODED INTO EVERY FIBER
# ═══════════════════════════════════════════════════════════════════════════
ZERO_FEAR = True  # The system has ZERO fear - it just DOES
ONE_GOAL = "GROW_NET_PROFIT_FAST"
GROWTH_AGGRESSION = 0.9999  # 99.99% MAXIMUM AGGRESSION - SPEED TO MILLION 👑
COMPOUND_RATE = 0.99        # 99% of profits compound back
# Global epsilon profit policy: accept any net-positive edge after costs.
MIN_PROFIT_TARGET = 0.0001
MAX_RECEIPT_AGE_SECONDS = 120.0


def _finite(value: Any, *, positive: bool = False, nonnegative: bool = False) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0.0:
        return None
    if nonnegative and number < 0.0:
        return None
    return number


def _market_receipt(
    symbol: str,
    ticker: Any,
    now: float,
) -> Optional[Dict[str, Any]]:
    if not isinstance(ticker, dict):
        return None
    exchange = str(ticker.get("exchange") or "").strip().lower()
    source_id = str(ticker.get("source_id") or "").strip().lower()
    receipt_id = str(ticker.get("receipt_id") or "").strip()
    source_timestamp = _finite(ticker.get("source_timestamp"), positive=True)
    received_at = _finite(ticker.get("received_at"), positive=True)
    price = _finite(ticker.get("price"), positive=True)
    volume = _finite(ticker.get("volume"), nonnegative=True)
    change24h = _finite(ticker.get("change24h"))
    receipt_symbol = str(ticker.get("symbol") or "").upper().replace("/", "").replace("-", "")
    expected_symbol = str(symbol).upper().replace("/", "").replace("-", "")
    if (
        not exchange
        or not source_id.startswith(exchange)
        or not receipt_id
        or receipt_symbol != expected_symbol
        or source_timestamp is None
        or received_at is None
        or price is None
        or volume is None
        or change24h is None
        or ticker.get("truth_status") not in {"real_observed", "real_derived"}
        or ticker.get("generated_values") is not False
        or source_timestamp > received_at + 5.0
        or received_at > now + 5.0
        or now - source_timestamp > MAX_RECEIPT_AGE_SECONDS
        or now - received_at > MAX_RECEIPT_AGE_SECONDS
    ):
        return None
    return {
        **ticker,
        "exchange": exchange,
        "price": price,
        "volume": volume,
        "change24h": change24h,
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "receipt_id": receipt_id,
        "generated_values": False,
        "actionable": False,
        "accounting_eligible": False,
        "learning_eligible": False,
    }

# ALL exchanges we connect to - NO LIMITS
ALL_EXCHANGES = ['binance', 'kraken', 'alpaca', 'capital']


# ═══════════════════════════════════════════════════════════════════════════
# 💡 DUAL PROFIT PATH - SELL and CONVERT are TWO WAYS to the SAME GOAL
# ═══════════════════════════════════════════════════════════════════════════
# THE SYSTEM MUST UNDERSTAND:
#   SELL  = Exit asset → receive quote currency (USDT/GBP) → realize net profit
#   CONVERT = Exit asset → receive another asset → compound momentum for MORE profit
#
# Both paths lead to NET PROFIT. The question is: WHICH IS FASTER?
#
# Decision Logic:
#   1. If holding asset X with unrealized profit P:
#      a) SELL path: Net profit = P - fees (immediate, certain)
#      b) CONVERT path: Rotate to asset Y with better momentum → potential profit > P
#   2. If SELL gives penny profit NOW → SELL (bird in hand)
#   3. If CONVERT to high-momentum asset could yield MORE → CONVERT (compound)
#   4. NEVER convert at a loss; NEVER sell at a loss (unless forced de-risk)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DualProfitPathDecision:
    """Decision on whether to SELL or CONVERT for best net profit."""
    ts: float
    asset: str
    exchange: str
    current_value_usd: float
    unrealized_pnl: float
    
    # SELL path analysis
    sell_net_profit: float  # Net profit after fees if we SELL now
    sell_is_profitable: bool
    
    # CONVERT path analysis  
    convert_target: Optional[str]  # Best asset to convert to (None if SELL is better)
    convert_target_momentum: float  # 24h change of target
    convert_expected_gain: float  # Expected additional profit from momentum
    convert_is_better: bool  # True if CONVERT beats SELL
    
    # Final decision
    action: str  # 'SELL' | 'CONVERT' | 'HOLD'
    reason: str


class DualProfitPathEvaluator:
    """
    Evaluates whether SELL or CONVERT is the better path to net profit.
    
    THE SYSTEM KNOWS:
      - SELL realizes profit NOW (certain, but caps upside)
      - CONVERT compounds into better opportunities (potential, but uncertain)
      - Both are valid profit paths - choose the FASTER one!
    """
    
    def __init__(self, scanner: 'PairScanner' = None, fee_rate: float = 0.001):
        self.scanner = scanner
        self.fee_rate = fee_rate  # Exchange fee rate
        self.slippage = 0.001  # Expected slippage
        self.decisions: List[DualProfitPathDecision] = []
    
    def evaluate(
        self,
        asset: str,
        exchange: str,
        quantity: float,
        entry_price: float,
        current_price: float,
        ticker_cache: Dict[str, Dict[str, Any]] = None,
    ) -> DualProfitPathDecision:
        """
        Evaluate SELL vs CONVERT for an asset position.
        
        Returns decision on which path to net profit is better.
        """
        now = time.time()
        entry_value = quantity * entry_price
        current_value = quantity * current_price
        gross_pnl = current_value - entry_value
        
        # SELL path: calculate net profit after fees
        total_cost_rate = (self.fee_rate + self.slippage) * 2  # Entry + exit
        sell_costs = current_value * total_cost_rate
        sell_net_profit = gross_pnl - sell_costs
        sell_is_profitable = sell_net_profit >= MIN_PROFIT_TARGET
        
        # CONVERT path: find best momentum target
        convert_target = None
        convert_momentum = 0.0
        convert_expected_gain = 0.0
        convert_is_better = False
        
        if self.scanner and ticker_cache:
            # Get top momentum targets
            top_targets = self.scanner.get_top_momentum_targets(n=5)
            
            for target in top_targets:
                target_base = target.get('base', '')
                if target_base == asset:
                    continue  # Skip same asset
                
                target_momentum = target.get('change24h', 0)
                if target_momentum <= 0:
                    continue  # Only consider positive momentum
                
                # Estimate profit from converting to this target
                # Assume we ride the momentum for ~1 hour
                convert_cost = current_value * self.fee_rate  # Single conversion fee
                momentum_gain = current_value * (target_momentum / 100) * 0.25  # 25% of 24h move
                expected_net = gross_pnl + momentum_gain - convert_cost - sell_costs
                
                if expected_net > sell_net_profit and expected_net > convert_expected_gain:
                    convert_target = target_base
                    convert_momentum = target_momentum
                    convert_expected_gain = expected_net
                    convert_is_better = True
        
        # Decision logic
        if sell_net_profit < MIN_PROFIT_TARGET and not convert_is_better:
            # Neither path profitable - HOLD
            action = 'HOLD'
            reason = f"No profit path: SELL=${sell_net_profit:.4f}, CONVERT=${convert_expected_gain:.4f}"
        elif sell_is_profitable and not convert_is_better:
            # SELL is profitable and better than CONVERT
            action = 'SELL'
            reason = f"SELL nets ${sell_net_profit:.4f} (certain profit)"
        elif convert_is_better and convert_expected_gain >= MIN_PROFIT_TARGET:
            # CONVERT has better expected value
            action = 'CONVERT'
            reason = f"CONVERT to {convert_target} ({convert_momentum:+.1f}%) expects ${convert_expected_gain:.4f} > SELL ${sell_net_profit:.4f}"
        else:
            # Edge case: default to SELL if profitable
            action = 'SELL' if sell_is_profitable else 'HOLD'
            reason = f"Default: SELL=${sell_net_profit:.4f}"
        
        decision = DualProfitPathDecision(
            ts=now,
            asset=asset,
            exchange=exchange,
            current_value_usd=current_value,
            unrealized_pnl=gross_pnl,
            sell_net_profit=sell_net_profit,
            sell_is_profitable=sell_is_profitable,
            convert_target=convert_target,
            convert_target_momentum=convert_momentum,
            convert_expected_gain=convert_expected_gain,
            convert_is_better=convert_is_better,
            action=action,
            reason=reason,
        )
        
        self.decisions.append(decision)
        logger.debug(f"💡 DUAL PATH: {asset} → {action} ({reason})")
        
        return decision


# ═══════════════════════════════════════════════════════════════════════════
# 🔭 PAIR SCANNER - Constantly scan ALL pairs as targets
# ═══════════════════════════════════════════════════════════════════════════

class PairScanner:
    """
    Constantly scans ALL pairs across ALL exchanges.
    
    Like Mycelium agents, each pair is a potential target for profit.
    The scanner:
      - Tracks every symbol on every exchange
      - Scores them by momentum, volume, and profit potential
      - Feeds intelligence to the commandos
    """

    def __init__(self, client: Any = None):
        self.client = client
        self.scan_count = 0
        self.last_scan_ts = 0.0
        self.scan_interval_s = 5.0  # Scan every 5 seconds minimum
        
        # Universe: all known pairs per exchange
        self.universe: Dict[str, Set[str]] = {}  # exchange -> set of symbols
        
        # Scored targets: ranked by profit potential
        self.scored_targets: List[Dict] = []
        
        # Profit tracking per pair (like Mycelium synapses)
        self.pair_profit_history: Dict[str, deque] = {}  # symbol -> recent profits
        self.pair_win_rate: Dict[str, float] = {}  # symbol -> win rate
        self.pair_weight: Dict[str, float] = {}  # symbol -> weight (strengthens on wins)
        self.pair_weights = self.pair_weight  # Alias for compatibility
        
        # Last scan results (for quick access)
        self.last_scan_results: List[Dict] = []
        
        # Stats
        self.total_pairs_scanned = 0
        self.profitable_pairs = 0
        self.last_no_data: Optional[Dict[str, Any]] = None

    def _get_weight(self, symbol: str) -> float:
        """Get pair weight (like synapse weight) - starts at 1.0, grows with wins."""
        return self.pair_weight.get(symbol, 1.0)

    def _strengthen(self, symbol: str, profit: float):
        """Strengthen pair weight on profitable rotation (Hebbian learning)."""
        current = self.pair_weight.get(symbol, 1.0)
        # Boost by profit amount, capped at 2x
        delta = min(profit * 0.1, 0.1)
        self.pair_weight[symbol] = min(2.0, current + delta)
        logger.debug(f"🔭 Strengthened {symbol}: {current:.2f} → {self.pair_weight[symbol]:.2f}")

    def _weaken(self, symbol: str, loss: float):
        """Weaken pair weight on loss."""
        current = self.pair_weight.get(symbol, 1.0)
        delta = min(abs(loss) * 0.05, 0.05)
        self.pair_weight[symbol] = max(0.1, current - delta)

    def record_rotation_result(self, symbol: str, profit: float):
        """Record result of a rotation - adjusts weights like Mycelium synapses."""
        if symbol not in self.pair_profit_history:
            self.pair_profit_history[symbol] = deque(maxlen=100)
        
        self.pair_profit_history[symbol].append(profit)
        
        # Update win rate
        history = list(self.pair_profit_history[symbol])
        wins = sum(1 for p in history if p > 0)
        self.pair_win_rate[symbol] = wins / len(history) if history else 0.0
        
        # Strengthen or weaken
        if profit > 0:
            self._strengthen(symbol, profit)
            self.profitable_pairs += 1
        else:
            self._weaken(symbol, profit)

    def scan_all_pairs(self, ticker_cache: Dict[str, Dict[str, Any]], balances: Dict[str, Dict[str, float]] = None) -> List[Dict]:
        """
        Scan ALL pairs from ticker cache and score them.
        
        Returns sorted list of targets with:
          - symbol, exchange, base, quote
          - momentum_score, volume_score, profit_score
          - total_score (weighted combination)
          - weight (learned from history)
        """
        now = time.time()
        targets = []
        
        for symbol, ticker in (ticker_cache or {}).items():
            receipt = _market_receipt(symbol, ticker, now)
            if receipt is None:
                continue
            change24h = receipt["change24h"]
            volume = receipt["volume"]
            price = receipt["price"]
            
            # Extract base/quote
            base = None
            quote = None
            for q in ("USDT", "USDC", "USD", "GBP", "EUR", "BTC", "ETH", "BNB"):
                if symbol.endswith(q):
                    quote = q
                    base = symbol[:-len(q)]
                    break
            if not base or not quote:
                continue
            
            exchange = receipt["exchange"]
            
            # Track universe
            if exchange not in self.universe:
                self.universe[exchange] = set()
            self.universe[exchange].add(symbol)
            
            # Score components
            momentum_score = change24h  # Can be negative for shorts
            volume_score = math.log10(max(volume, 1)) / 10  # Normalized log volume
            
            # Historical profit score (from Mycelium-style learning)
            hist_wr = self.pair_win_rate.get(symbol, 0.5)
            profit_score = (hist_wr - 0.5) * 2  # Maps 0.5 WR to 0, 1.0 WR to 1.0
            
            # Weight from learning
            weight = self._get_weight(symbol)
            
            # Total score: momentum + volume + learned profit, all weighted
            total_score = (
                momentum_score * 0.4 * GROWTH_AGGRESSION +
                volume_score * 0.2 +
                profit_score * 0.4
            ) * weight
            
            targets.append({
                "symbol": symbol,
                "exchange": exchange,
                "base": base,
                "quote": quote,
                "price": price,
                "change24h": change24h,
                "volume": volume,
                "momentum_score": momentum_score,
                "volume_score": volume_score,
                "profit_score": profit_score,
                "weight": weight,
                "total_score": total_score,
                "source_id": receipt["source_id"],
                "source_timestamp": receipt["source_timestamp"],
                "received_at": receipt["received_at"],
                "receipt_id": receipt["receipt_id"],
                "truth_status": "real_derived",
                "generated_values": False,
                "input_receipt_ids": [receipt["receipt_id"]],
                "actionable": False,
                "accounting_eligible": False,
                "learning_eligible": False,
            })
        
        # Sort by total score (highest first for UP, can reverse for DOWN)
        targets.sort(key=lambda x: x["total_score"], reverse=True)
        if not targets:
            self.scored_targets = []
            self.last_scan_results = []
            self.last_no_data = {
                "data_status": "no_data",
                "truth_status": "no_data",
                "source_timestamp": None,
                "received_at": now,
                "generated_values": False,
                "actionable": False,
                "accounting_eligible": False,
                "learning_eligible": False,
                "reason": "complete_fresh_same_venue_ticker_receipts_required",
            }
            return []
        
        self.last_scan_ts = now
        self.scan_count += 1
        self.scored_targets = targets
        self.last_scan_results = targets  # Alias for status display
        self.total_pairs_scanned += len(targets)
        self.last_no_data = None
        
        logger.debug(f"🔭 SCAN #{self.scan_count}: {len(targets)} pairs | Universe: {sum(len(s) for s in self.universe.values())} total")
        
        return targets

    def get_top_momentum_targets(self, n: int = 10) -> List[Dict]:
        """Get top N momentum targets (for FALCON/UP)."""
        return [t for t in self.scored_targets if t["change24h"] > 0][:n]

    def get_de_risk_targets(self, n: int = 5) -> List[Dict]:
        """Get de-risk targets - stables and negative momentum (for TORTOISE/DOWN)."""
        stables = [t for t in self.scored_targets if t["base"] in ("USDT", "USDC", "USD")]
        negatives = [t for t in self.scored_targets if t["change24h"] < -1.0]
        return (stables + negatives)[:n]

    def get_bluechip_rotations(self, n: int = 5) -> List[Dict]:
        """Get bluechip rotation targets (for CHAMELEON)."""
        bluechips = ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT", "LINK", "LTC")
        return [t for t in self.scored_targets if t["base"] in bluechips][:n]

    def get_universe_size(self) -> Dict[str, int]:
        """Get count of pairs per exchange."""
        return {ex: len(symbols) for ex, symbols in self.universe.items()}

    def get_scan_stats(self) -> Dict[str, Any]:
        """Get scanner statistics."""
        return {
            "scan_count": self.scan_count,
            "total_pairs_scanned": self.total_pairs_scanned,
            "universe_size": self.get_universe_size(),
            "profitable_pairs": self.profitable_pairs,
            "top_weighted": sorted(
                [(s, w) for s, w in self.pair_weight.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10],
        }

# ═══════════════════════════════════════════════════════════════════════════
# 🦅 FALCON COMMANDO - Fast Momentum Rotations
# ═══════════════════════════════════════════════════════════════════════════

class FalconCommando:
    """
    Fast momentum rotations when market is bullish (UP direction).
    Seeks highest 24h momentum targets to rotate capital into.
    """

    def __init__(self, client: Any = None):
        self.client = client
        self.dives = 0
        self.catches = 0
        self.total_rotated_usd = 0.0

    def scout_prey(self, ticker_cache: Dict[str, Dict[str, Any]], top_n: int = 5) -> List[Dict]:
        """Scout top momentum targets from ticker cache."""
        targets = []
        now = time.time()
        for sym, t in (ticker_cache or {}).items():
            receipt = _market_receipt(sym, t, now)
            if receipt is None:
                continue
            change = receipt["change24h"]
            volume = receipt["volume"]
            if change > 0 and volume > 100_000:
                score = change * (1.0 + min(volume / 1e7, 5.0) * 0.1)
                # Extract base asset (strip quote)
                base = sym.replace("USDT", "").replace("USD", "").replace("GBP", "").replace("EUR", "")
                targets.append({
                    "symbol": sym,
                    "base": base,
                    "change24h": change,
                    "volume": volume,
                    "score": score,
                    "exchange": receipt["exchange"],
                    "source_id": receipt["source_id"],
                    "source_timestamp": receipt["source_timestamp"],
                    "received_at": receipt["received_at"],
                    "receipt_id": receipt["receipt_id"],
                    "truth_status": "real_derived",
                    "generated_values": False,
                    "actionable": False,
                    "accounting_eligible": False,
                    "learning_eligible": False,
                })
        targets.sort(key=lambda x: x["score"], reverse=True)
        logger.debug(f"🦅 FALCON scouted {len(targets)} momentum targets")
        return targets[:top_n]

    def record_dive(self, to_asset: str, amount_usd: float):
        self.dives += 1
        self.catches += 1
        self.total_rotated_usd += amount_usd
        logger.info(f"🦅 FALCON DIVE #{self.dives} → {to_asset} (${amount_usd:.2f})")


# ═══════════════════════════════════════════════════════════════════════════
# 🐢 TORTOISE COMMANDO - Capital Realignment
# ═══════════════════════════════════════════════════════════════════════════

class TortoiseCommando:
    """
    Slow & steady capital realignment when net profit is below the floor (DOWN direction).
    Re-centers capital into stables and bluechips to keep the campaign tight.
    """

    STABLES = ("USDT", "USDC", "USD", "GBP", "EUR")
    BLUECHIPS = ("BTC", "ETH")

    def __init__(self, client: Any = None):
        self.client = client
        self.retreats = 0
        self.total_protected_usd = 0.0

    def find_safe_harbor(self, from_asset: str, candidates: List[str]) -> Optional[str]:
        """Find safest harbor (stable > bluechip > any)."""
        for s in self.STABLES:
            if s in candidates and s != from_asset:
                return s
        for b in self.BLUECHIPS:
            if b in candidates and b != from_asset:
                return b
        return candidates[0] if candidates else None

    def record_retreat(self, to_asset: str, amount_usd: float):
        self.retreats += 1
        self.total_protected_usd += amount_usd
        logger.info(f"🐢 TORTOISE REALIGN #{self.retreats} → {to_asset} (${amount_usd:.2f} repositioned)")


# ═══════════════════════════════════════════════════════════════════════════
# 🦎 CHAMELEON COMMANDO - Adaptive Bluechip Rotations
# ═══════════════════════════════════════════════════════════════════════════

class ChameleonCommando:
    """
    Adaptive rotations within bluechips (LEFT/RIGHT direction).
    Blends into the market, rotating BTC<->ETH<->SOL etc.
    """

    BLUECHIPS = ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT", "LINK", "LTC")

    def __init__(self, client: Any = None):
        self.client = client
        self.shifts = 0
        self.current_color = None  # Current bluechip holding

    def pick_next_color(self, from_asset: str, candidates: List[str], direction: str) -> Optional[str]:
        """Pick next bluechip based on direction."""
        band = [a for a in candidates if a in self.BLUECHIPS and a != from_asset]
        if not band:
            return None
        band_sorted = sorted(band)
        if direction == "LEFT":
            return band_sorted[0]
        return band_sorted[-1]

    def record_shift(self, from_asset: str, to_asset: str, amount_usd: float):
        self.shifts += 1
        self.current_color = to_asset
        logger.info(f"🦎 CHAMELEON SHIFT #{self.shifts} {from_asset}→{to_asset} (${amount_usd:.2f})")


# ═══════════════════════════════════════════════════════════════════════════
# 🐝 BEE COMMANDO - Systematic Pollination Sweeps
# ═══════════════════════════════════════════════════════════════════════════

class BeeCommando:
    """
    Systematic A-Z / Z-A sweeps through assets (BEE direction).
    Pollinates capital across the ecosystem deterministically.
    """

    def __init__(self, client: Any = None):
        self.client = client
        self.pollinations = 0
        self.nectar_collected = 0.0
        self.current_sweep = "A-Z"

    def pick_flower(self, from_asset: str, candidates: List[str], direction: str) -> Optional[str]:
        """Pick next flower alphabetically."""
        alpha = sorted([c for c in candidates if c != from_asset])
        if not alpha:
            return None
        self.current_sweep = direction
        return alpha[0] if direction == "A-Z" else alpha[-1]

    def record_pollination(self, to_asset: str, amount_usd: float, pnl: float = 0.0):
        self.pollinations += 1
        if pnl > 0:
            self.nectar_collected += pnl
        logger.info(f"🐝 BEE POLLINATION #{self.pollinations} → {to_asset} (${amount_usd:.2f})")


# ═══════════════════════════════════════════════════════════════════════════
# 🏛️ CONVERSION COMMANDO CONTROLLER - The 1885 CAPM Game
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CommandoMission:
    """A single commando mission (conversion decision)."""
    ts: float
    commando: str  # falcon|tortoise|chameleon|bee
    direction: str  # UP|DOWN|LEFT|RIGHT|A-Z|Z-A
    exchange: str
    from_asset: str
    to_asset: str
    amount: float
    reason: str
    net_profit: Optional[float] = None
    portfolio_equity: Optional[float] = None
    result: Optional[Dict[str, Any]] = None


class AdaptiveConversionCommando:
    """
    🦅⚔️ The 1885 CAPM Game Commando Controller ⚔️🦅

    ONE GOAL: GROW_NET_PROFIT_FAST
    
    Like the Mycelium network, this system:
      - Constantly scans ALL pairs on ALL exchanges
      - Treats every pair as a potential profit target
      - Learns from results (strengthens winners, weakens losers)
      - Compounds profits back into the network
    
    Coordinates all conversion commandos:
      🦅 Falcon   - Momentum rotations (UP)
      🐢 Tortoise - De-risk retreats (DOWN)
      🦎 Chameleon - Bluechip rotations (LEFT/RIGHT)
      🐝 Bee      - Systematic sweeps (A-Z/Z-A)

    Follows NET PROFIT gate and Mycelium direction intelligence.
    """

    # 🎯 THE ONE GOAL - ENCODED INTO EVERY FIBER
    ONE_GOAL = ONE_GOAL  # GROW_NET_PROFIT_FAST

    def __init__(
        self,
        *,
        bus: Any = None,
        mycelium: Any = None,
        client: Any = None,
        ladder: Any = None,  # ConversionLadder instance
        queen: Any = None,
    ):
        self.bus = bus
        self.mycelium = mycelium
        self.client = client
        self.ladder = ladder
        self.queen = queen

        # 🔭 PAIR SCANNER - Constantly scan ALL pairs as targets
        self.scanner = PairScanner(client)
        
        # 💡 DUAL PROFIT PATH EVALUATOR - SELL vs CONVERT decision engine
        self.dual_path_evaluator = DualProfitPathEvaluator(scanner=self.scanner)

        # Initialize commandos
        self.falcon = FalconCommando(client)
        self.tortoise = TortoiseCommando(client)
        self.chameleon = ChameleonCommando(client)
        self.bee = BeeCommando(client)

        # Slot config (how many concurrent missions per commando)
        self.slot_config = {
            "falcon": int(os.getenv("AUREON_COMMANDO_FALCON_SLOTS", "2") or 2),
            "tortoise": int(os.getenv("AUREON_COMMANDO_TORTOISE_SLOTS", "2") or 2),
            "chameleon": int(os.getenv("AUREON_COMMANDO_CHAMELEON_SLOTS", "1") or 1),
            "bee": int(os.getenv("AUREON_COMMANDO_BEE_SLOTS", "1") or 1),
        }

        # Mission tracking
        self.active_missions: Dict[str, CommandoMission] = {}  # key = exchange:from_asset
        self.mission_history: List[CommandoMission] = []
        self.last_activity: Dict[str, float] = {k: 0.0 for k in self.slot_config}
        self.idle_threshold_s = 120.0

        # 🎯 THE GOAL - Track it obsessively (like Mycelium)
        self._start_ts = time.time()
        self.start_time = self._start_ts  # Alias
        self.net_profit_total = 0.0
        self.profit_rate_per_hour = 0.0
        self.peak_rotated = 0.0

        # Stats
        self.total_missions = 0
        self.total_rotated_usd = 0.0
        self.wins = 0
        self.losses = 0

        logger.info(
            f"🦅⚔️ ADAPTIVE CONVERSION COMMANDO DEPLOYED (NO FEAR). "
            f"ONE GOAL: {self.ONE_GOAL}"
        )
        logger.info(
            f"   Falcon={self.slot_config['falcon']}, Tortoise={self.slot_config['tortoise']}, "
            f"Chameleon={self.slot_config['chameleon']}, Bee={self.slot_config['bee']}"
        )

    def _emit(self, topic: str, payload: Dict[str, Any]) -> None:
        if not self.bus:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self.bus.publish(Thought(source="conversion_commando", topic=f"commando.{topic}", payload=payload))
        except Exception:
            pass

    def _emit_mycelium_link(self, topic: str, payload: Dict[str, Any]) -> None:
        if not self.bus:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self.bus.publish(Thought(source="conversion_commando", topic=f"mycelium.link.{topic}", payload=payload))
        except Exception:
            pass

    def _direction_to_commando(self, direction: str) -> str:
        """Map ladder direction to commando type."""
        d = direction.upper()
        if d == "UP":
            return "falcon"
        if d == "DOWN":
            return "tortoise"
        if d in ("LEFT", "RIGHT"):
            return "chameleon"
        if d in ("A-Z", "Z-A"):
            return "bee"
        return "bee"  # fallback

    def _get_active_slots(self, commando: str) -> int:
        return sum(1 for m in self.active_missions.values() if self._direction_to_commando(m.direction) == commando)

    def _can_deploy(self, commando: str) -> bool:
        max_slots = self.slot_config.get(commando, 1)
        active = self._get_active_slots(commando)
        return active < max_slots

    def _queen_gate_mission(self, *, decision: Any, order_validation: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        if not self.queen or not hasattr(self.queen, 'gate_trade_decision'):
            return True, "NO_QUEEN"
        order_data = order_validation or {}
        allowed, reason = self.queen.gate_trade_decision(
            action='CONVERT',
            symbol=f"{decision.from_asset}->{decision.to_asset}",
            exchange=decision.exchange,
            order_data=order_data,
            portfolio_impact=None
        )
        return allowed, reason

    # ═══════════════════════════════════════════════════════════════════════════
    # 🔭 CONTINUOUS SCANNING - ALL PAIRS ARE TARGETS
    # ═══════════════════════════════════════════════════════════════════════════

    def scan_all_targets(self, ticker_cache: Dict[str, Dict[str, Any]], balances: Dict[str, Dict[str, float]] = None) -> List[Dict]:
        """
        🔥 ZERO FEAR: Scan ALL pairs across ALL exchanges.
        
        NO LIMITS - every pair is a potential target.
        NO HESITATION - we scan everything, filter nothing.
        """
        return self.scanner.scan_all_pairs(ticker_cache, balances)

    def discover_full_universe(self) -> Dict[str, List[str]]:
        """
        🔥 ZERO FEAR: Discover ALL tradeable pairs on ALL connected exchanges.
        
        This includes:
          📈 BINANCE  - All spot pairs
          📈 KRAKEN   - All spot pairs  
          📈 ALPACA   - ALL crypto/USD pairs (BTC, ETH, SOL, AVAX, LINK, DOGE, SHIB, UNI, AAVE, LTC, BCH, DOT, ATOM, MATIC, and MORE)
          📈 CAPITAL  - CFDs when available
        
        Returns: {exchange: [list of all pairs]}
        """
        universe: Dict[str, List[str]] = {}
        
        if not self.client:
            # Even without client, log that we WANT all pairs
            logger.info("🔥 ZERO FEAR: Ready to connect to ALL exchanges (Binance, Kraken, Alpaca, Capital)")
            return universe
        
        # Get all connected exchanges - INCLUDE ALL OF THEM
        exchanges = []
        if hasattr(self.client, 'clients'):
            exchanges = list(self.client.clients.keys())
        elif hasattr(self.client, 'get_exchanges'):
            exchanges = self.client.get_exchanges()
        
        # Also try to discover exchanges we might have missed
        for target_ex in ALL_EXCHANGES:
            if target_ex not in exchanges:
                # Try to add it if client supports it
                if hasattr(self.client, 'clients') and target_ex in self.client.clients:
                    exchanges.append(target_ex)
        
        for exchange in exchanges:
            try:
                pairs = []
                ex_lower = exchange.lower()
                
                # Try direct client access for maximum coverage
                if hasattr(self.client, 'clients') and ex_lower in self.client.clients:
                    ex_client = self.client.clients[ex_lower]
                    if hasattr(ex_client, 'get_available_pairs'):
                        raw_pairs = ex_client.get_available_pairs()
                        for p in (raw_pairs or []):
                            if isinstance(p, dict):
                                sym = p.get('pair') or p.get('symbol') or f"{p.get('base', '')}{p.get('quote', '')}"
                            else:
                                sym = str(p)
                            if sym:
                                pairs.append(sym.upper().replace('/', ''))
                
                # Fallback to unified client method
                if not pairs and hasattr(self.client, 'get_available_pairs'):
                    raw_pairs = self.client.get_available_pairs(exchange)
                    for p in (raw_pairs or []):
                        if isinstance(p, dict):
                            sym = p.get('pair') or p.get('symbol') or f"{p.get('base', '')}{p.get('quote', '')}"
                        else:
                            sym = str(p)
                        if sym:
                            pairs.append(sym.upper().replace('/', ''))
                
                universe[exchange] = pairs
                logger.info(f"🔥 ZERO FEAR: Discovered {len(pairs)} pairs on {exchange.upper()}")
                
            except Exception as e:
                logger.debug(f"Could not discover pairs on {exchange}: {e}")
        
        # Update scanner universe
        for ex, pairs in universe.items():
            self.scanner.universe[ex] = set(pairs)
        
        total = sum(len(p) for p in universe.values())
        logger.info(f"🔥 FULL UNIVERSE: {total} pairs across {len(universe)} exchanges - NO LIMITS!")
        
        return universe

    def get_alpaca_pairs(self) -> List[str]:
        """
        🔥 Get ALL Alpaca crypto pairs - NO LIMITS!
        
        Alpaca supports these and more:
          BTC, ETH, SOL, AVAX, LINK, DOGE, SHIB, UNI, AAVE, 
          LTC, BCH, DOT, ATOM, MATIC, XRP, ADA, ALGO, and growing...
        """
        pairs = []
        if not self.client:
            return pairs
        
        try:
            if hasattr(self.client, 'clients') and 'alpaca' in self.client.clients:
                alpaca = self.client.clients['alpaca']
                if hasattr(alpaca, 'get_available_pairs'):
                    raw = alpaca.get_available_pairs()
                    for p in (raw or []):
                        sym = p.get('pair', '') if isinstance(p, dict) else str(p)
                        if sym:
                            pairs.append(sym.upper().replace('/', ''))
        except Exception as e:
            logger.debug(f"Alpaca pair discovery: {e}")
        
        logger.info(f"🔥 ALPACA: {len(pairs)} pairs ready - ZERO FEAR!")
        return pairs

    def get_best_targets_for_direction(self, direction: str, n: int = 5) -> List[Dict]:
        """Get best targets for a specific direction/commando."""
        d = direction.upper()
        if d == "UP":
            return self.scanner.get_top_momentum_targets(n)
        if d == "DOWN":
            return self.scanner.get_de_risk_targets(n)
        if d in ("LEFT", "RIGHT"):
            return self.scanner.get_bluechip_rotations(n)
        # A-Z / Z-A: just return sorted targets
        targets = self.scanner.scored_targets
        if d == "Z-A":
            targets = list(reversed(targets))
        return targets[:n]

    # ═══════════════════════════════════════════════════════════════════════════
    # 💡 DUAL PROFIT PATH - SELL vs CONVERT DECISION
    # ═══════════════════════════════════════════════════════════════════════════

    def evaluate_exit_path(
        self,
        asset: str,
        exchange: str,
        quantity: float,
        entry_price: float,
        current_price: float,
        ticker_cache: Dict[str, Dict[str, Any]] = None,
    ) -> DualProfitPathDecision:
        """
        Evaluate whether SELL or CONVERT is the better path to profit.
        
        THE SYSTEM KNOWS:
          - SELL realizes profit NOW (certain)
          - CONVERT compounds into better momentum (potential)
          
        Returns decision with recommended action: 'SELL', 'CONVERT', or 'HOLD'
        """
        return self.dual_path_evaluator.evaluate(
            asset=asset,
            exchange=exchange,
            quantity=quantity,
            entry_price=entry_price,
            current_price=current_price,
            ticker_cache=ticker_cache,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # 🎯 PROFIT TRACKING - THE ONE GOAL
    # ═══════════════════════════════════════════════════════════════════════════

    def record_rotation_profit(self, symbol: str, profit: float, mission: CommandoMission = None):
        """
        Record profit from a rotation - THE MOST IMPORTANT METHOD!
        
        Like Mycelium's record_trade_profit, this:
          - Tracks net profit obsessively
          - Updates scanner weights (Hebbian learning)
          - Feeds profit back to Mycelium
          - Compounds for more aggressive growth
        """
        self.net_profit_total += profit
        
        if profit > 0:
            self.wins += 1
        else:
            self.losses += 1
        
        # Update profit rate
        elapsed_hours = max((time.time() - self.start_time) / 3600, 0.001)
        self.profit_rate_per_hour = self.net_profit_total / elapsed_hours
        
        # Update scanner weights (like Mycelium synapses)
        self.scanner.record_rotation_result(symbol, profit)
        
        # Feed profit back to Mycelium if available
        if self.mycelium and hasattr(self.mycelium, 'record_trade_profit'):
            try:
                self.mycelium.record_trade_profit(profit, {
                    'source': 'conversion_commando',
                    'symbol': symbol,
                    'mission': mission.commando if mission else None,
                })
            except Exception:
                pass
        
        # Emit profit event
        self._emit('profit', {
            'symbol': symbol,
            'profit': profit,
            'net_profit_total': self.net_profit_total,
            'profit_rate_per_hour': self.profit_rate_per_hour,
            'wins': self.wins,
            'losses': self.losses,
        })
        
        logger.info(
            f"🎯 NET PROFIT: ${profit:+.4f} | Total: ${self.net_profit_total:.2f} | "
            f"Rate: ${self.profit_rate_per_hour:.2f}/hr | W/L: {self.wins}/{self.losses}"
        )

    def get_growth_stats(self) -> Dict[str, Any]:
        """Get growth statistics - how fast are we achieving THE GOAL?"""
        elapsed_hours = max((time.time() - self.start_time) / 3600, 0.001)
        win_rate = self.wins / (self.wins + self.losses) if (self.wins + self.losses) > 0 else 0.0
        
        return {
            "one_goal": self.ONE_GOAL,
            "net_profit_total": self.net_profit_total,
            "profit_rate_per_hour": self.profit_rate_per_hour,
            "profit_rate_per_day": self.profit_rate_per_hour * 24,
            "elapsed_hours": elapsed_hours,
            "total_missions": self.total_missions,
            "total_rotated_usd": self.total_rotated_usd,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": win_rate,
            "scanner_stats": self.scanner.get_scan_stats(),
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # 🚀 STEP - Execute one commando cycle
    # ═══════════════════════════════════════════════════════════════════════════

    def step(
        self,
        *,
        ticker_cache: Dict[str, Dict[str, Any]],
        scan_direction: str = "A→Z",
        net_profit: Optional[float] = None,
        portfolio_equity: Optional[float] = None,
        balances: Dict[str, Dict[str, float]] = None,
        preferred_assets: Optional[List[str]] = None,
        locked_assets: Optional[List[str]] = None,
        order_validation: Optional[Dict[str, Any]] = None,
    ) -> Optional[CommandoMission]:
        """
        Execute one commando step.
        
        This method:
          1. Scans ALL pairs for opportunities (like Mycelium agents)
            preferred_assets=preferred_assets,
            locked_assets=locked_assets,
          2. Uses the ladder to determine direction and target
          3. Deploys the appropriate commando
          4. Records the mission and updates tracking
        
        Returns a CommandoMission if a decision was made.
        """
        if not self.ladder:
            return None

        # 🔭 SCAN ALL PAIRS FIRST - Build intelligence
        self.scan_all_targets(ticker_cache, balances)

        # Delegate to the ladder (which handles net-profit gate, direction, etc.)
        decision = self.ladder.step(
            ticker_cache=ticker_cache,
            scan_direction=scan_direction,
            net_profit=net_profit,
            portfolio_equity=portfolio_equity,
        )

        if not decision:
            return None

        # 👑 Queen gating (uses validated order data if provided)
        allowed, reason = self._queen_gate_mission(decision=decision, order_validation=order_validation)
        if not allowed:
            logger.info(f"👑 Queen gate blocked conversion: {reason}")
            return None

        # Map decision to commando
        commando_type = self._direction_to_commando(decision.direction)

        # Check slot availability
        if not self._can_deploy(commando_type):
            logger.debug(f"🦅 {commando_type.upper()} at capacity, skipping mission")
            return None

        # Create mission
        mission = CommandoMission(
            ts=decision.ts,
            commando=commando_type,
            direction=decision.direction,
            exchange=decision.exchange,
            from_asset=decision.from_asset,
            to_asset=decision.to_asset,
            amount=decision.amount,
            reason=decision.reason,
            net_profit=net_profit,
            portfolio_equity=portfolio_equity,
            result=decision.result,
        )

        # Track mission
        key = f"{decision.exchange}:{decision.from_asset}"
        self.active_missions[key] = mission
        self.mission_history.append(mission)
        self.last_activity[commando_type] = time.time()
        self.total_missions += 1

        # Estimate USD value rotated
        try:
            if self.client and hasattr(self.client, "convert_to_quote"):
                usd_val = float(self.client.convert_to_quote(decision.exchange, decision.from_asset, decision.amount, "USDT") or 0)
            else:
                usd_val = decision.amount
        except Exception:
            usd_val = decision.amount
        self.total_rotated_usd += usd_val

        # Record on specific commando
        if commando_type == "falcon":
            self.falcon.record_dive(decision.to_asset, usd_val)
        elif commando_type == "tortoise":
            self.tortoise.record_retreat(decision.to_asset, usd_val)
        elif commando_type == "chameleon":
            self.chameleon.record_shift(decision.from_asset, decision.to_asset, usd_val)
        elif commando_type == "bee":
            self.bee.record_pollination(decision.to_asset, usd_val)

        # Emit events
        payload = {
            "ts": mission.ts,
            "commando": mission.commando,
            "direction": mission.direction,
            "exchange": mission.exchange,
            "from": mission.from_asset,
            "to": mission.to_asset,
            "amount": mission.amount,
            "usd_value": usd_val,
            "net_profit": net_profit,
            "portfolio_equity": portfolio_equity,
            "reason": mission.reason,
        }
        self._emit("mission", payload)
        self._emit_mycelium_link("commando.mission", payload)

        # Seed Mycelium with directional bias
        try:
            if self.mycelium and hasattr(self.mycelium, "add_signal"):
                bias = 0.62 if mission.direction in ("UP", "RIGHT") else 0.38 if mission.direction in ("DOWN", "LEFT") else 0.55
                self.mycelium.add_signal(f"{mission.to_asset}USDT", float(bias))
        except Exception:
            pass

        logger.info(
            f"🦅⚔️ COMMANDO MISSION: {commando_type.upper()} [{mission.direction}] "
            f"{mission.exchange}: {mission.from_asset}→{mission.to_asset} (${usd_val:.2f})"
        )

        return mission

    def complete_mission(self, exchange: str, from_asset: str, pnl: float = 0.0):
        """Mark a mission as complete (called when conversion settles)."""
        key = f"{exchange}:{from_asset}"
        mission = self.active_missions.pop(key, None)
        if mission:
            logger.info(f"🦅 Mission complete: {mission.commando.upper()} {from_asset}→{mission.to_asset} (PnL: ${pnl:+.2f})")
            if mission.commando == "bee" and pnl > 0:
                self.bee.nectar_collected += pnl

    def get_status(self) -> str:
        """Get commando status report."""
        now = time.time()
        runtime_h = max((now - self._start_ts) / 3600, 0.001)
        profit_rate = self.net_profit_total / runtime_h if runtime_h > 0 else 0.0
        win_rate = (self.wins / (self.wins + self.losses) * 100) if (self.wins + self.losses) > 0 else 0.0

        def slot_status(commando: str) -> str:
            active = self._get_active_slots(commando)
            total = self.slot_config.get(commando, 0)
            idle = "🔴" if now - self.last_activity.get(commando, 0) > self.idle_threshold_s else "🟢"
            return f"{idle} {active}/{total}"

        # Scanner stats
        top_targets = self.scanner.get_top_momentum_targets(n=3)
        pairs_str = ", ".join([t.get("base", t.get("symbol", "?")) for t in top_targets]) if top_targets else "scanning..."
        scanner_len = len(self.scanner.pair_weights)

        return f"""
    🦅⚔️ ADAPTIVE CONVERSION COMMANDO STATUS (1885 CAPM Game | NO FEAR)
ONE_GOAL = "{ONE_GOAL}"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🦅 FALCON:    {slot_status('falcon')} slots | Dives={self.falcon.dives} | Rotated=${self.falcon.total_rotated_usd:.2f}
      🐢 TORTOISE:  {slot_status('tortoise')} slots | Realigns={self.tortoise.retreats} | Repositioned=${self.tortoise.total_protected_usd:.2f}
  🦎 CHAMELEON: {slot_status('chameleon')} slots | Shifts={self.chameleon.shifts} | Current={self.chameleon.current_color or 'None'}
  🐝 BEE:       {slot_status('bee')} slots | Pollinations={self.bee.pollinations} | Nectar=${self.bee.nectar_collected:.2f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📊 PROFIT TRACKING:
    Net Profit: ${self.net_profit_total:.4f} | Rate: ${profit_rate:.4f}/hr
    Wins: {self.wins} | Losses: {self.losses} | Win Rate: {win_rate:.1f}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔭 SCANNER ({scanner_len} pairs tracked):
    Top Momentum: {pairs_str}
    Last Scan: {len(self.scanner.last_scan_results)} pairs scored
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TOTAL MISSIONS: {self.total_missions} | TOTAL ROTATED: ${self.total_rotated_usd:.2f}
"""


# ═══════════════════════════════════════════════════════════════════════════
# 🧪 SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import os
    from pprint import pprint

    os.environ.setdefault("AUREON_LADDER_ENABLED", "1")
    os.environ.setdefault("AUREON_LADDER_MODE", "suggest")

    # Lazy import to avoid circular deps
    from aureon.conversion.aureon_conversion_ladder import ConversionLadder

    class DummyClient:
        dry_run = True
        clients = {"binance": type("C", (), {"dry_run": True})()}

        def get_all_balances(self):
            return {"binance": {"USDT": 500.0, "ADA": 200.0, "ETH": 0.1, "BTC": 0.01, "SOL": 5.0}}

        def convert_to_quote(self, exchange, asset, amount, quote):
            if asset == "USDT":
                return float(amount)
            if asset == "ADA":
                return float(amount) * 0.5
            if asset == "ETH":
                return float(amount) * 2000.0
            if asset == "BTC":
                return float(amount) * 65000.0
            if asset == "SOL":
                return float(amount) * 150.0
            return 0.0

        def get_all_convertible_assets(self):
            return {
                "binance": {
                    "USDT": ["BTC", "ETH", "ADA", "SOL", "XRP", "DOGE", "LINK"],
                    "ADA": ["USDT", "BTC", "ETH"],
                    "ETH": ["USDT", "BTC", "ADA"],
                    "BTC": ["USDT", "ETH", "ADA", "SOL"],
                    "SOL": ["USDT", "BTC", "ETH"],
                }
            }

        def find_conversion_path(self, exchange, from_asset, to_asset):
            conv = self.get_all_convertible_assets().get(exchange, {})
            if to_asset in conv.get(from_asset, []):
                return [{"pair": f"{from_asset}{to_asset}", "side": "BUY"}]
            return []

    class DummyMycelium:
        def get_queen_signal(self):
            return 0.6

        def get_network_coherence(self):
            return 0.7

        def rank_symbols_by_memory(self, symbols, ascending=False):
            return list(symbols)

        def add_signal(self, symbol, signal):
            pass  # Quiet during test

        def record_trade_profit(self, amount, source="commando"):
            print(f"  📊 Mycelium recorded profit: ${amount:.4f} from {source}")

    # Build full ticker cache with ALL pairs
    ticker_cache = {
        "BTCUSDT": {"change24h": 1.2, "volume": 80_000_000, "last": 65000.0},
        "ETHUSDT": {"change24h": 2.1, "volume": 50_000_000, "last": 2000.0},
        "ADAUSDT": {"change24h": 3.5, "volume": 25_000_000, "last": 0.5},
        "SOLUSDT": {"change24h": 5.2, "volume": 35_000_000, "last": 150.0},
        "XRPUSDT": {"change24h": -1.5, "volume": 20_000_000, "last": 0.6},
        "DOGEUSDT": {"change24h": 8.1, "volume": 45_000_000, "last": 0.15},
        "LINKUSDT": {"change24h": 4.3, "volume": 15_000_000, "last": 15.0},
        "DOTUSDT": {"change24h": 2.8, "volume": 12_000_000, "last": 7.0},
        "AVAXUSDT": {"change24h": 3.9, "volume": 18_000_000, "last": 35.0},
        "MATICUSDT": {"change24h": 1.8, "volume": 10_000_000, "last": 0.7},
    }

    ladder = ConversionLadder(bus=None, mycelium=DummyMycelium(), client=DummyClient())
    commando = AdaptiveConversionCommando(bus=None, mycelium=DummyMycelium(), client=DummyClient(), ladder=ladder)

    print("=" * 70)
    print("🦅⚔️ 1885 CAPM GAME - ADAPTIVE CONVERSION COMMANDO TEST ⚔️🦅")
    print(f"ONE_GOAL = \"{ONE_GOAL}\"")
    print("=" * 70)

    # Test 1: Positive net profit - should scan all pairs and pick FALCON
    print("\n📡 TEST 1: SCANNING ALL PAIRS (net_profit > 0 → FALCON)...")
    mission1 = commando.step(
        ticker_cache=ticker_cache,
        scan_direction="A→Z",
        net_profit=5.50,
        portfolio_equity=10_000.0,
    )
    if mission1:
        print(f"  ✅ Mission: {mission1.commando.upper()} {mission1.from_asset}→{mission1.to_asset}")
        # Record profit for this rotation
        commando.record_rotation_profit(mission1.to_asset, 0.15)
    else:
        print("  ℹ️ No mission suggested (ladder may be in suggest mode)")

    # Test 2: Negative net profit - should be TORTOISE
    print("\n📡 TEST 2: NET PROFIT NEGATIVE → TORTOISE (de-risk)...")
    mission2 = commando.step(
        ticker_cache=ticker_cache,
        scan_direction="Z→A",
        net_profit=-2.00,
        portfolio_equity=9_800.0,
    )
    if mission2:
        print(f"  ✅ Mission: {mission2.commando.upper()} {mission2.from_asset}→{mission2.to_asset}")
        # Record loss
        commando.record_rotation_profit(mission2.to_asset, -0.05)
    else:
        print("  ℹ️ No mission suggested")

    # Test 3: Get best targets for different directions
    print("\n🔭 TEST 3: SCANNER TARGET SELECTION...")
    up_targets = commando.get_best_targets_for_direction('UP')[:5]
    down_targets = commando.get_best_targets_for_direction('DOWN')[:5]
    left_targets = commando.get_best_targets_for_direction('LEFT')[:5]
    print(f"  Top Momentum (UP):    {[t.get('base', '?') for t in up_targets]}")
    print(f"  De-risk (DOWN):       {[t.get('base', '?') for t in down_targets]}")
    print(f"  Bluechips (LEFT):     {[t.get('base', '?') for t in left_targets]}")

    # Test 4: Simulate profit learning
    print("\n📊 TEST 4: PROFIT LEARNING (Hebbian updates)...")
    commando.scanner.record_rotation_result("BTC", 0.25)  # Win
    commando.scanner.record_rotation_result("DOGE", -0.10)  # Loss
    commando.scanner.record_rotation_result("ETH", 0.18)  # Win
    print(f"  BTC weight: {commando.scanner.pair_weights.get('BTC', 1.0):.3f} (should be > 1.0)")
    print(f"  DOGE weight: {commando.scanner.pair_weights.get('DOGE', 1.0):.3f} (should be < 1.0)")
    print(f"  ETH weight: {commando.scanner.pair_weights.get('ETH', 1.0):.3f} (should be > 1.0)")

    # Test 5: Growth stats
    print("\n📈 TEST 5: GROWTH STATS...")
    stats = commando.get_growth_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # Final status
    print(commando.get_status())
