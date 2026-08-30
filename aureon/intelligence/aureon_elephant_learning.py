#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     🐘👑 QUEEN SERO's ELEPHANT MEMORY LEARNING SYSTEM 👑🐘                          ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                           ║
║                                                                                      ║
║     "An elephant NEVER forgets. Neither does Queen Sero."                          ║
║                                                                                      ║
║     FEATURES:                                                                        ║
║       • Learn from YEARS of historical data without losing money                     ║
║       • Permanent elephant memory - NEVER forgets patterns                           ║
║       • Pattern recognition across 1000s of trades                                   ║
║       • Win rate calculation BEFORE real trading                                     ║
║       • Fee-aware profit calculation                                                 ║
║                                                                                      ║
║     Gary Leckey & Tina Brown | January 2026                                          ║
║     "Learn from history, profit from the future"                                     ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import time
import logging
import math
import requests
from datetime import datetime, timedelta, timezone

# ═══════════════════════════════════════════════════════════════════════════
# WINDOWS UTF-8 FIX - Must be at top before any logging/printing
# ═══════════════════════════════════════════════════════════════════════════
from typing import Callable, Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import hashlib

# ═══════════════════════════════════════════════════════════════════════════════
# 🐦 CHIRP BUS INTEGRATION - kHz-Speed Memory Signals
# ═══════════════════════════════════════════════════════════════════════════════
CHIRP_BUS_AVAILABLE = False
get_chirp_bus = None
try:
    from aureon.core.aureon_chirp_bus import get_chirp_bus
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False

logger = logging.getLogger(__name__)

MARKET_RECEIPT_MAX_AGE_SECONDS = 120.0
EXECUTION_RECEIPT_MAX_AGE_SECONDS = 300.0


def _finite_number(
    value: Any,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0.0:
        return None
    if nonnegative and number < 0.0:
        return None
    return number


def _timestamp_epoch(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if not math.isfinite(timestamp) or timestamp <= 0.0:
            return None
        if timestamp >= 1e17:
            timestamp /= 1e9
        elif timestamp >= 1e14:
            timestamp /= 1e6
        elif timestamp >= 1e11:
            timestamp /= 1e3
        return timestamp
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return None
        timestamp = parsed.timestamp()
        return timestamp if math.isfinite(timestamp) and timestamp > 0.0 else None
    return None


def _iso_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _fresh_receipt_times(
    source_timestamp: Any,
    received_at: Any,
    *,
    now: float,
    max_age_seconds: float,
) -> Optional[Tuple[float, float]]:
    source = _timestamp_epoch(source_timestamp)
    received = _timestamp_epoch(received_at)
    if source is None or received is None or not math.isfinite(now):
        return None
    if source >= received or received > now + 5.0:
        return None
    if now - source > max_age_seconds:
        return None
    return source, received


def _no_data_receipt(reason: str, *, now: float, purpose: str) -> Dict[str, Any]:
    return {
        "purpose": purpose,
        "data_status": "no_data",
        "truth_status": "no_data",
        "reason": reason,
        "source_id": None,
        "source_timestamp": None,
        "received_at": _iso_timestamp(now),
        "generated_values": False,
        "should_trade": False,
        "recorded": False,
        "action_eligible": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
    }


def _normalize_market_receipt(
    receipt: Any,
    *,
    from_asset: str,
    to_asset: str,
    now: float,
) -> Optional[Dict[str, Any]]:
    if not isinstance(receipt, dict):
        return None
    if (
        receipt.get("data_status") != "live"
        or receipt.get("truth_status") not in {"real_observed", "real_derived", "real_provider"}
        or receipt.get("generated_values") is not False
    ):
        return None
    base_currency = str(receipt.get("base_currency") or "").strip().upper()
    quote_currency = str(receipt.get("quote_currency") or "").strip().upper()
    symbol = str(receipt.get("symbol") or "").strip().upper()
    source_id = str(receipt.get("source_id") or "").strip()
    if (
        not base_currency
        or not quote_currency
        or base_currency != str(to_asset).strip().upper()
        or quote_currency != str(from_asset).strip().upper()
        or not symbol
        or not source_id
    ):
        return None
    price = _finite_number(receipt.get("price"), positive=True)
    price_change = _finite_number(receipt.get("price_change_1h"))
    volume_change = _finite_number(receipt.get("volume_change_pct"))
    times = _fresh_receipt_times(
        receipt.get("source_timestamp"),
        receipt.get("received_at"),
        now=now,
        max_age_seconds=MARKET_RECEIPT_MAX_AGE_SECONDS,
    )
    if price is None or price_change is None or volume_change is None or times is None:
        return None
    source_timestamp, received_at = times
    return {
        **receipt,
        "symbol": symbol,
        "base_currency": base_currency,
        "quote_currency": quote_currency,
        "price": price,
        "price_change_1h": price_change,
        "volume_change_pct": volume_change,
        "source_id": source_id,
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "generated_values": False,
    }


def _normalize_terminal_execution_receipt(
    receipt: Any,
    *,
    now: float,
) -> Optional[Dict[str, Any]]:
    if not isinstance(receipt, dict):
        return None
    if (
        str(receipt.get("status") or "").strip().lower() not in {"filled", "closed", "settled"}
        or receipt.get("terminal_fill_receipt_complete") is not True
        or receipt.get("data_status") != "live"
        or receipt.get("truth_status") not in {"real_observed", "real_derived", "real_provider"}
        or receipt.get("generated_values") is not False
        or receipt.get("eligible_for_accounting") is not True
        or receipt.get("eligible_for_learning") is not True
        or receipt.get("pnl_net_of_fees") is not True
    ):
        return None
    provider_order_id = str(
        receipt.get("provider_order_id") or receipt.get("order_id") or ""
    ).strip()
    provider_fill_id = str(
        receipt.get("provider_fill_id") or receipt.get("fill_id") or receipt.get("trade_id") or ""
    ).strip()
    from_asset = str(receipt.get("from_asset") or "").strip().upper()
    to_asset = str(receipt.get("to_asset") or "").strip().upper()
    fee_currency = str(receipt.get("fee_currency") or "").strip().upper()
    pnl_currency = str(receipt.get("pnl_currency") or "").strip().upper()
    source_id = str(receipt.get("source_id") or "").strip()
    quantity = _finite_number(receipt.get("filled_qty"), positive=True)
    price = _finite_number(receipt.get("filled_avg_price"), positive=True)
    notional = _finite_number(receipt.get("filled_notional"), positive=True)
    fee = _finite_number(receipt.get("fee"), nonnegative=True)
    realized_pnl = _finite_number(receipt.get("realized_pnl"))
    times = _fresh_receipt_times(
        receipt.get("provider_timestamp") or receipt.get("source_timestamp"),
        receipt.get("received_at"),
        now=now,
        max_age_seconds=EXECUTION_RECEIPT_MAX_AGE_SECONDS,
    )
    if (
        not provider_order_id
        or not provider_fill_id
        or not from_asset
        or not to_asset
        or not fee_currency
        or not pnl_currency
        or fee_currency != pnl_currency
        or not source_id
        or quantity is None
        or price is None
        or notional is None
        or fee is None
        or realized_pnl is None
        or times is None
        or not math.isclose(notional, quantity * price, rel_tol=1e-6, abs_tol=1e-8)
    ):
        return None
    source_timestamp, received_at = times
    return {
        **receipt,
        "provider_order_id": provider_order_id,
        "provider_fill_id": provider_fill_id,
        "from_asset": from_asset,
        "to_asset": to_asset,
        "filled_qty": quantity,
        "filled_avg_price": price,
        "filled_notional": notional,
        "fee": fee,
        "fee_currency": fee_currency,
        "realized_pnl": realized_pnl,
        "pnl_currency": pnl_currency,
        "source_id": source_id,
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "generated_values": False,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 🐘 ELEPHANT MEMORY - PERMANENT PATTERN STORAGE
# ═══════════════════════════════════════════════════════════════════════════════

ELEPHANT_MEMORY_FILE = "queen_elephant_memory.json"

@dataclass
class LearnedPattern:
    """A pattern Queen has learned from historical data"""
    pattern_id: str
    pattern_type: str  # 'momentum', 'reversal', 'breakout', 'support', 'resistance'
    symbol: str
    timeframe: str  # '1h', '4h', '1d'
    
    # Pattern conditions
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Performance metrics
    total_occurrences: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    avg_profit_per_trade: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0  # total profit / total loss
    
    # Best conditions
    best_entry_hour: int = 0  # Hour of day (0-23)
    best_exit_hours: int = 4  # How long to hold
    best_move_threshold: float = 0.5  # Min % move to act on
    
    # When learned
    first_seen: str = ""
    last_updated: str = ""
    
    # Confidence
    confidence: float = 0.0  # Based on sample size and consistency
    evidence_scope: str = "legacy_unproven"
    fee_model: Optional[str] = None
    source_id: Optional[str] = None
    source_timestamp: Optional[float] = None
    received_at: Optional[str] = None
    generated_values: bool = False
    action_eligible: bool = False
    eligible_for_learning: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LearnedPattern':
        return cls(**data)
    
    def update_performance(self, profit: float, is_win: bool):
        """Update pattern performance with new trade result"""
        self.total_occurrences += 1
        if is_win:
            self.winning_trades += 1
            self.total_profit += profit
        else:
            self.losing_trades += 1
            self.total_loss += abs(profit)
        
        # Recalculate metrics
        if self.total_occurrences > 0:
            self.win_rate = (self.winning_trades / self.total_occurrences) * 100
            self.avg_profit_per_trade = (self.total_profit - self.total_loss) / self.total_occurrences
        
        if self.total_loss > 0:
            self.profit_factor = self.total_profit / self.total_loss
        
        # Confidence based on sample size
        if self.total_occurrences >= 100:
            self.confidence = min(95, 50 + (self.win_rate - 50) * 0.9)
        elif self.total_occurrences >= 50:
            self.confidence = min(85, 40 + (self.win_rate - 50) * 0.8)
        elif self.total_occurrences >= 20:
            self.confidence = min(75, 30 + (self.win_rate - 50) * 0.7)
        else:
            self.confidence = min(50, 20 + self.total_occurrences)
        
        self.last_updated = datetime.now().isoformat()


@dataclass 
class TradingWisdom:
    """High-level wisdom learned from thousands of trades"""
    wisdom_id: str
    category: str  # 'timing', 'asset', 'market_condition', 'risk'
    insight: str
    
    # Supporting data
    sample_size: int = 0
    confidence: float = 0.0
    evidence: Dict[str, Any] = field(default_factory=dict)
    
    # Performance when following this wisdom
    win_rate_following: float = 0.0
    win_rate_ignoring: float = 0.0
    
    created: str = ""
    last_validated: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TradingWisdom':
        return cls(**data)


class ElephantMemory:
    """
    🐘 Queen Sero's Elephant Memory
    
    NEVER forgets:
    - Winning patterns
    - Losing patterns  
    - Best times to trade
    - Which assets to avoid
    - Market conditions that work
    """
    
    def __init__(
        self,
        memory_file: str = ELEPHANT_MEMORY_FILE,
        *,
        clock: Optional[Callable[[], float]] = None,
        autoload: bool = False,
    ):
        self.memory_file = memory_file
        self._clock = clock or time.time
        self._loaded = False
        self.patterns: Dict[str, LearnedPattern] = {}
        self.wisdom: Dict[str, TradingWisdom] = {}
        self.blocked_paths: Dict[str, Dict] = {}  # Paths that ALWAYS lose
        self.golden_paths: Dict[str, Dict] = {}   # Paths that ALWAYS win
        
        # Statistics
        self.total_historical_trades: int = 0
        self.total_historical_profit: float = 0.0
        self.learning_sessions: int = 0
        
        # Timing insights
        self.best_hours: Dict[int, float] = {}  # hour -> avg profit
        self.worst_hours: Dict[int, float] = {}
        self.best_days: Dict[int, float] = {}   # day of week -> avg profit
        
        # Asset insights
        self.asset_performance: Dict[str, Dict] = {}  # symbol -> stats
        self.processed_execution_ids: Set[str] = set()
        
        if autoload:
            self.ensure_loaded()

    def ensure_loaded(self) -> None:
        """Load persisted memory lazily, never as a constructor side effect."""
        if not self._loaded:
            self._load_memory()
    
    def _load_memory(self):
        """Load elephant memory from disk"""
        self._loaded = True
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                
                # Load patterns
                for pid, pdata in data.get('patterns', {}).items():
                    self.patterns[pid] = LearnedPattern.from_dict(pdata)
                
                # Load wisdom
                for wid, wdata in data.get('wisdom', {}).items():
                    self.wisdom[wid] = TradingWisdom.from_dict(wdata)
                
                # Load paths
                # 🔓 FULL AUTONOMOUS MODE: Never load blocked paths - Queen has full access!
                self.blocked_paths = {}  # Always empty - no blocking!
                self.golden_paths = data.get('golden_paths', {})
                
                # Load stats
                self.total_historical_trades = data.get('total_historical_trades', 0)
                self.total_historical_profit = data.get('total_historical_profit', 0.0)
                self.learning_sessions = data.get('learning_sessions', 0)
                
                # Load insights
                self.best_hours = {int(k): v for k, v in data.get('best_hours', {}).items()}
                self.worst_hours = {int(k): v for k, v in data.get('worst_hours', {}).items()}
                self.best_days = {int(k): v for k, v in data.get('best_days', {}).items()}
                self.asset_performance = data.get('asset_performance', {})
                processed = data.get('processed_execution_ids')
                if isinstance(processed, list):
                    self.processed_execution_ids = {
                        str(value) for value in processed if str(value).strip()
                    }
                
                logger.info(f"🐘 Elephant Memory loaded: {len(self.patterns)} patterns, {len(self.wisdom)} wisdoms")
                logger.info(f"   📊 Historical trades: {self.total_historical_trades:,}")
                logger.info(f"   💰 Historical profit: ${self.total_historical_profit:,.2f}")
                logger.info(f"   🚫 Blocked paths: {len(self.blocked_paths)}")
                logger.info(f"   ⭐ Golden paths: {len(self.golden_paths)}")
                
            except Exception as e:
                logger.warning(f"Failed to load elephant memory: {e}")
    
    def _save_memory(self):
        """Save elephant memory to disk - NEVER FORGET!"""
        self.ensure_loaded()
        data = {
            'patterns': {pid: p.to_dict() for pid, p in self.patterns.items()},
            'wisdom': {wid: w.to_dict() for wid, w in self.wisdom.items()},
            'blocked_paths': {},  # 🔓 ALWAYS EMPTY - Full autonomous mode!
            'golden_paths': self.golden_paths,
            'total_historical_trades': self.total_historical_trades,
            'total_historical_profit': self.total_historical_profit,
            'learning_sessions': self.learning_sessions,
            'best_hours': self.best_hours,
            'worst_hours': self.worst_hours,
            'best_days': self.best_days,
            'asset_performance': self.asset_performance,
            'processed_execution_ids': sorted(self.processed_execution_ids),
            'last_saved': _iso_timestamp(float(self._clock()))
        }
        
        with open(self.memory_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"🐘 Elephant Memory saved: {len(self.patterns)} patterns")
    
    def remember_pattern(self, pattern: LearnedPattern):
        """Remember a new pattern FOREVER"""
        self.ensure_loaded()
        self.patterns[pattern.pattern_id] = pattern
        self._save_memory()
        
        # 🐦 CHIRP EMISSION - kHz-Speed Memory Signals
        # Emit pattern learning chirps for system-wide awareness
        if pattern.action_eligible and CHIRP_BUS_AVAILABLE and get_chirp_bus:
            try:
                chirp_bus = get_chirp_bus()
                
                chirp_bus.emit_signal(
                    signal_type='ELEPHANT_PATTERN_LEARNED',
                    symbol=pattern.symbol,
                    coherence=pattern.confidence,
                    confidence=pattern.win_rate,
                    frequency=396.0,  # Liberation frequency
                    amplitude=pattern.confidence
                )
                
            except Exception as e:
                # Chirp emission failure - non-critical, continue
                pass
    
    def remember_wisdom(self, wisdom: TradingWisdom):
        """Remember wisdom FOREVER"""
        self.ensure_loaded()
        self.wisdom[wisdom.wisdom_id] = wisdom
        self._save_memory()
        
        # 🐦 CHIRP EMISSION - kHz-Speed Memory Signals
        # Emit wisdom learning chirps for system-wide awareness
        if CHIRP_BUS_AVAILABLE and get_chirp_bus:
            try:
                chirp_bus = get_chirp_bus()
                
                chirp_bus.emit_signal(
                    signal_type='ELEPHANT_WISDOM_LEARNED',
                    symbol='SYSTEM',  # Wisdom applies system-wide
                    coherence=wisdom.confidence,
                    confidence=wisdom.confidence,
                    frequency=528.0,  # Love frequency for wisdom
                    amplitude=wisdom.confidence
                )
                
            except Exception as e:
                # Chirp emission failure - non-critical, continue
                pass
    
    def block_path_forever(self, from_asset: str, to_asset: str, reason: str, 
                           loss_count: int, total_loss: float):
        """Block a trading path FOREVER
        
        🔓 FULL AUTONOMOUS MODE: DO NOT BLOCK - Just log for learning!
        Queen Sero needs all paths available to explore and learn!
        """
        self.ensure_loaded()
        path_key = f"{from_asset}→{to_asset}"
        # 🔓 DISABLED: Don't actually block, just log
        logger.info(f"🐘📝 NOTED (not blocked): {path_key} - {reason} (losses: {loss_count}, total: ${total_loss:.2f})")
        # Original blocking code disabled:
        # self.blocked_paths[path_key] = {...}
        # self._save_memory()
    
    def mark_golden_path(self, from_asset: str, to_asset: str, 
                         win_count: int, total_profit: float, win_rate: float,
                         *, evidence_scope: str = "legacy_unproven"):
        """Mark a consistently winning path"""
        self.ensure_loaded()
        path_key = f"{from_asset}→{to_asset}"
        self.golden_paths[path_key] = {
            'from': from_asset,
            'to': to_asset,
            'win_count': win_count,
            'total_profit': total_profit,
            'win_rate': win_rate,
            'evidence_scope': evidence_scope,
            'discovered_at': datetime.now().isoformat()
        }
        self._save_memory()
        logger.info(f"🐘⭐ GOLDEN PATH DISCOVERED: {path_key} - {win_rate:.1f}% win rate!")
    
    def is_path_blocked(self, from_asset: str, to_asset: str) -> Tuple[bool, Optional[str]]:
        """Check if a path is permanently blocked
        
        🔓 FULL AUTONOMOUS MODE: NEVER BLOCK ANY PATH!
        Queen Sero must be free to explore ALL possibilities!
        """
        self.ensure_loaded()
        # 🔓 DISABLED FOR FULL AUTONOMOUS TRADING - Let Queen try everything!
        return False, None
    
    def is_golden_path(self, from_asset: str, to_asset: str) -> Tuple[bool, Optional[float]]:
        """Check if a path is a golden winner"""
        self.ensure_loaded()
        path_key = f"{from_asset}→{to_asset}"
        if path_key in self.golden_paths:
            win_rate = _finite_number(self.golden_paths[path_key].get('win_rate'), nonnegative=True)
            return (win_rate is not None), win_rate
        return False, None
    
    def get_best_trading_hours(self) -> List[int]:
        """Get the best hours to trade based on personal history AND ingrested wisdom"""
        self.ensure_loaded()
        # 1. Gather Personal Experience (Self-Learning)
        personal_best = []
        if self.best_hours:
            sorted_hours = sorted(self.best_hours.items(), key=lambda x: x[1], reverse=True)
            personal_best = [h for h, _ in sorted_hours[:6]] # Top 6 from experience
            
        # 2. Gather Historical Wisdom (Ingested Knowledge)
        wisdom_best = []
        for wid, w in self.wisdom.items():
            if wid.startswith('coinbase_golden_hour_'):
                try:
                    hour = int(wid.split('_')[-1])
                    wisdom_best.append(hour)
                except ValueError:
                    pass
                    
        # 3. Merge & Prioritize
        # If we have NO personal experience, trust Wisdom 100%
        if not personal_best:
            if not wisdom_best:
                return list(range(24)) # Absolute zero knowledge
            return list(set(wisdom_best)) # Return unique wisdom hours
            
        # If we have both, combine them (Union of top personal + all wisdom)
        combined = list(set(personal_best + wisdom_best))
        return combined

    def get_worst_trading_hours(self) -> List[int]:
        """Get hours to AVOID based on history and wisdom"""
        self.ensure_loaded()
        avoid = []
        # Wisdom avoids (e.g. "coinbase_avoid_hour_X")
        for wid, w in self.wisdom.items():
            if wid.startswith('coinbase_avoid_hour_'):
                try:
                    hour = int(wid.split('_')[-1])
                    avoid.append(hour)
                except ValueError:
                    pass
        return list(set(avoid))
    
    def get_asset_score(
        self,
        symbol: str,
        *,
        as_of_timestamp: Optional[float] = None,
    ) -> Optional[float]:
        """Get historical performance score for an asset (0-100)"""
        self.ensure_loaded()
        # 1. Base Score from Personal Stats
        if symbol in self.asset_performance:
            stats = self.asset_performance[symbol]
            win_rate = _finite_number(stats.get('win_rate'), nonnegative=True)
            profit_factor = _finite_number(stats.get('profit_factor'), nonnegative=True)
            sample_size = _finite_number(stats.get('trades'), nonnegative=True)
            if (
                win_rate is None
                or win_rate > 100.0
                or profit_factor is None
                or sample_size is None
                or not sample_size.is_integer()
            ):
                return None
            
            # Score based on win rate and profit factor
            base_score = (win_rate + (profit_factor - 1) * 20) / 2
            
            # Confidence adjustment based on sample size
            if sample_size < 10:
                confidence = 0.3
            elif sample_size < 50:
                confidence = 0.6
            elif sample_size < 100:
                confidence = 0.8
            else:
                confidence = 1.0
            
            final_score = 50 + (base_score - 50) * confidence
        else:
            return None
            
        # 2. Apply Wisdom Modifiers (Macro Context)
        current_date = (
            datetime.fromtimestamp(as_of_timestamp, tz=timezone.utc)
            if as_of_timestamp is not None
            else None
        )
        
        # September Effect (Bearish) - Slight penalty
        if current_date is not None and current_date.month == 9:
            sept_wisdom = self.wisdom.get('wiki_september_effect')
            if sept_wisdom:
                final_score *= 0.9 
                
        # Weekend Effect (Sunday Dump) - Slight penalty for buys
        if current_date is not None and current_date.weekday() == 6: # Sunday
            sunday_wisdom = self.wisdom.get('wiki_sunday_dump')
            if sunday_wisdom:
                final_score *= 0.95
                
        # Bitcoin Halving Boost (Post-Halving Bull Run assumption)
        halving_wisdom = self.wisdom.get('wiki_bitcoin_halving_cycle')
        if halving_wisdom and symbol.startswith('BTC'):
             # Slight permanent boost for BTC if Aware of Halving Cycle
             final_score *= 1.02
             
        return min(100.0, max(0.0, final_score))
    
    def get_pattern_signals(self, symbol: str, current_price: float, 
                           price_change_1h: float, volume_change: float) -> List[Dict]:
        """Get signals from learned patterns"""
        self.ensure_loaded()
        current_price = _finite_number(current_price, positive=True)
        price_change_1h = _finite_number(price_change_1h)
        volume_change = _finite_number(volume_change)
        if current_price is None or price_change_1h is None or volume_change is None:
            return []
        signals = []
        
        for pattern in self.patterns.values():
            if pattern.symbol != symbol and pattern.symbol != '*':
                continue
            
            if pattern.win_rate < 55 or pattern.confidence < 50:
                continue
            
            # Check if current conditions match pattern
            conditions = pattern.conditions
            
            # Momentum pattern
            if pattern.pattern_type == 'momentum':
                min_change = _finite_number(conditions.get('min_change_1h'))
                if min_change is None:
                    continue
                if price_change_1h >= min_change:
                    signals.append({
                        'pattern_id': pattern.pattern_id,
                        'type': 'momentum',
                        'action': 'BUY',
                        'confidence': pattern.confidence,
                        'win_rate': pattern.win_rate,
                        'avg_profit': pattern.avg_profit_per_trade,
                        'evidence_scope': pattern.evidence_scope,
                        'action_eligible': pattern.action_eligible,
                        'reason': f"Momentum pattern ({pattern.win_rate:.1f}% win rate)"
                    })
            
            # Reversal pattern
            elif pattern.pattern_type == 'reversal':
                max_drop = _finite_number(conditions.get('max_drop_1h'))
                if max_drop is None:
                    continue
                if price_change_1h <= max_drop:
                    signals.append({
                        'pattern_id': pattern.pattern_id,
                        'type': 'reversal',
                        'action': 'BUY',
                        'confidence': pattern.confidence,
                        'win_rate': pattern.win_rate,
                        'avg_profit': pattern.avg_profit_per_trade,
                        'evidence_scope': pattern.evidence_scope,
                        'action_eligible': pattern.action_eligible,
                        'reason': f"Reversal pattern ({pattern.win_rate:.1f}% win rate)"
                    })
            
            # Volume breakout
            elif pattern.pattern_type == 'volume_breakout':
                min_volume = _finite_number(conditions.get('min_volume_change'), nonnegative=True)
                if min_volume is None:
                    continue
                if volume_change >= min_volume:
                    signals.append({
                        'pattern_id': pattern.pattern_id,
                        'type': 'volume_breakout',
                        'action': 'BUY',
                        'confidence': pattern.confidence,
                        'win_rate': pattern.win_rate,
                        'avg_profit': pattern.avg_profit_per_trade,
                        'evidence_scope': pattern.evidence_scope,
                        'action_eligible': pattern.action_eligible,
                        'reason': f"Volume breakout ({pattern.win_rate:.1f}% win rate)"
                    })
        
        return signals
    
    def summarize(self) -> str:
        """Get a summary of elephant memory"""
        self.ensure_loaded()
        lines = [
            "🐘 QUEEN'S ELEPHANT MEMORY SUMMARY 🐘",
            "=" * 50,
            f"📊 Learning sessions: {self.learning_sessions}",
            f"📈 Historical trades analyzed: {self.total_historical_trades:,}",
            f"💰 Historical profit (sim): ${self.total_historical_profit:,.2f}",
            f"",
            f"🧠 Patterns learned: {len(self.patterns)}",
            f"💡 Wisdom collected: {len(self.wisdom)}",
            f"🚫 Blocked paths: {len(self.blocked_paths)}",
            f"⭐ Golden paths: {len(self.golden_paths)}",
            f"📊 Assets tracked: {len(self.asset_performance)}",
            ""
        ]
        
        # Best patterns
        if self.patterns:
            best = sorted(self.patterns.values(), 
                         key=lambda p: p.win_rate * p.confidence, 
                         reverse=True)[:5]
            lines.append("🏆 TOP 5 PATTERNS:")
            for p in best:
                lines.append(f"   • {p.pattern_type}: {p.win_rate:.1f}% win ({p.total_occurrences} trades)")
        
        # Golden paths
        if self.golden_paths:
            lines.append("")
            lines.append("⭐ GOLDEN PATHS (HIGH WIN RATE):")
            for path, data in list(self.golden_paths.items())[:5]:
                lines.append(f"   • {path}: {data['win_rate']:.1f}% win, ${data['total_profit']:.2f} profit")
        
        # Blocked paths
        if self.blocked_paths:
            lines.append("")
            lines.append("🚫 BLOCKED PATHS (ALWAYS LOSE):")
            for path, data in list(self.blocked_paths.items())[:5]:
                lines.append(f"   • {path}: {data['reason']}")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 HISTORICAL DATA LEARNER
# ═══════════════════════════════════════════════════════════════════════════════

class HistoricalLearner:
    """
    Learn from historical data and store in elephant memory
    """
    
    # Public APIs for historical data
    BINANCE_URL = "https://api.binance.com"
    COINGECKO_URL = "https://api.coingecko.com/api/v3"
    
    # Trading fee assumption
    TRADING_FEE = 0.001  # 0.1% per trade
    
    def __init__(
        self,
        elephant_memory: ElephantMemory,
        *,
        session=None,
        cache_file: str = "historical_candles_cache.json",
        clock: Optional[Callable[[], float]] = None,
    ):
        self.memory = elephant_memory
        self.session = session
        self.cache_file = cache_file
        self._clock = clock or time.time
        self.cached_data: Dict[str, Dict[str, Any]] = {}
        self._cache_loaded = False

    def _ensure_cache_loaded(self) -> None:
        if not self._cache_loaded:
            self.cached_data = self._load_cache()
            self._cache_loaded = True
    
    def _load_cache(self) -> Dict:
        """Load only the provenance-bearing historical cache schema."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    payload = json.load(f)
                if (
                    isinstance(payload, dict)
                    and payload.get("schema_version") == "aureon-historical-candles-v2"
                    and payload.get("generated_values") is False
                    and isinstance(payload.get("entries"), dict)
                ):
                    return payload["entries"]
            except Exception:
                logger.warning("Historical candle cache is unreadable; ignoring it")
        return {}
    
    def _save_cache(self):
        """Save historical data with explicit research-only provenance."""
        with open(self.cache_file, 'w') as f:
            json.dump(
                {
                    "schema_version": "aureon-historical-candles-v2",
                    "generated_values": False,
                    "action_eligible": False,
                    "eligible_for_accounting": False,
                    "eligible_for_learning": False,
                    "entries": self.cached_data,
                    "saved_at": _iso_timestamp(float(self._clock())),
                },
                f,
            )

    def _normalize_historical_candles(
        self,
        candles: Any,
        *,
        expected_symbol: str,
    ) -> List[Dict[str, Any]]:
        if not isinstance(candles, list):
            return []
        normalized: List[Dict[str, Any]] = []
        previous_source_timestamp: Optional[float] = None
        for raw in candles:
            if not isinstance(raw, dict):
                return []
            if (
                raw.get("truth_status") != "real_observed"
                or raw.get("generated_values") is not False
                or raw.get("action_eligible") is not False
                or raw.get("source_id") != "binance:/api/v3/klines"
                or str(raw.get("symbol") or "").upper() != expected_symbol.upper()
            ):
                return []
            source_timestamp = _timestamp_epoch(raw.get("source_timestamp"))
            open_timestamp = _timestamp_epoch(raw.get("open_timestamp"))
            received_at = _timestamp_epoch(raw.get("received_at"))
            open_price = _finite_number(raw.get("open"), positive=True)
            high = _finite_number(raw.get("high"), positive=True)
            low = _finite_number(raw.get("low"), positive=True)
            close = _finite_number(raw.get("close"), positive=True)
            volume = _finite_number(raw.get("volume"), nonnegative=True)
            quote_volume = _finite_number(raw.get("quote_volume"), nonnegative=True)
            trade_count = _finite_number(raw.get("trade_count"), nonnegative=True)
            if (
                source_timestamp is None
                or open_timestamp is None
                or received_at is None
                or source_timestamp <= open_timestamp
                or source_timestamp >= received_at
                or open_price is None
                or high is None
                or low is None
                or close is None
                or volume is None
                or quote_volume is None
                or trade_count is None
                or not trade_count.is_integer()
                or not (low <= open_price <= high and low <= close <= high)
                or (
                    previous_source_timestamp is not None
                    and source_timestamp <= previous_source_timestamp
                )
            ):
                return []
            normalized.append({
                **raw,
                "open_timestamp": open_timestamp,
                "source_timestamp": source_timestamp,
                "received_at": _iso_timestamp(received_at),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "quote_volume": quote_volume,
                "trade_count": int(trade_count),
                "generated_values": False,
                "action_eligible": False,
                "eligible_for_accounting": False,
                "eligible_for_learning": False,
            })
            previous_source_timestamp = source_timestamp
        return normalized
    
    def fetch_binance_history(self, symbol: str, interval: str = '1h', 
                              days: int = 30) -> List[Dict]:
        """
        Fetch historical candles from Binance (PUBLIC API)
        """
        cache_key = f"binance_{symbol}_{interval}_{days}d"
        self._ensure_cache_loaded()
        
        # Check cache first
        cached = self.cached_data.get(cache_key)
        if (
            isinstance(cached, dict)
            and cached.get("generated_values") is False
            and cached.get("action_eligible") is False
        ):
            normalized_cached = self._normalize_historical_candles(
                cached.get("candles"),
                expected_symbol=symbol,
            )
            if normalized_cached:
                logger.info(f"📦 Using provenance-verified cached data for {symbol}")
                return normalized_cached
        
        try:
            # Calculate time range
            end_time = int(time.time() * 1000)
            start_time = end_time - (days * 24 * 60 * 60 * 1000)
            
            url = f"{self.BINANCE_URL}/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': start_time,
                'endTime': end_time,
                'limit': 1000
            }
            
            if self.session is None:
                self.session = requests.Session()
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            received_at = float(self._clock())
            
            candles = []
            for k in response.json():
                if not isinstance(k, list) or len(k) < 11:
                    return []
                candles.append({
                    'timestamp': k[0],
                    'open_timestamp': k[0],
                    'source_timestamp': k[6],
                    'received_at': _iso_timestamp(received_at),
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]),
                    'quote_volume': float(k[7]),
                    'trade_count': k[8],
                    'taker_buy_base_volume': float(k[9]),
                    'taker_buy_quote_volume': float(k[10]),
                    'symbol': symbol,
                    'source_id': "binance:/api/v3/klines",
                    'truth_status': "real_observed",
                    'data_status': "historical",
                    'generated_values': False,
                    'action_eligible': False,
                    'eligible_for_accounting': False,
                    'eligible_for_learning': False,
                })
            candles = self._normalize_historical_candles(candles, expected_symbol=symbol)
            if not candles:
                return []
            
            # Cache it
            self.cached_data[cache_key] = {
                "source_id": "binance:/api/v3/klines",
                "symbol": symbol,
                "interval": interval,
                "days": days,
                "candles": candles,
                "generated_values": False,
                "action_eligible": False,
                "eligible_for_accounting": False,
                "eligible_for_learning": False,
                "fee_model": "research_assumption_only",
            }
            self._save_cache()
            
            logger.info(f"📊 Fetched {len(candles)} candles for {symbol}")
            return candles
            
        except Exception as e:
            logger.warning(f"Failed to fetch {symbol}: {e}")
            return []
    
    def analyze_patterns(self, candles: List[Dict]) -> Dict[str, LearnedPattern]:
        """
        Analyze historical candles for patterns
        """
        if not candles or not isinstance(candles[0], dict):
            return {}
        expected_symbol = str(candles[0].get("symbol") or "").strip().upper()
        candles = self._normalize_historical_candles(
            candles,
            expected_symbol=expected_symbol,
        )
        if not expected_symbol or len(candles) < 100:
            return {}
        
        patterns = {}
        symbol = candles[0]['symbol']
        
        # Track simulated trades
        trades = []
        
        # Strategy 1: Momentum (buy after 1%+ rise)
        momentum_wins = 0
        momentum_losses = 0
        momentum_profit = 0.0
        momentum_loss = 0.0
        
        for i in range(24, len(candles) - 4):
            prev_close = candles[i-1]['close']
            curr_close = candles[i]['close']
            change = ((curr_close - prev_close) / prev_close) * 100
            
            if change >= 1.0:  # 1%+ rise
                # Simulate buying and holding for 4 hours
                entry_price = curr_close
                exit_price = candles[i + 4]['close']
                
                # Calculate profit after fees
                gross_profit_pct = ((exit_price - entry_price) / entry_price) * 100
                net_profit_pct = gross_profit_pct - (self.TRADING_FEE * 2 * 100)  # Buy + sell fee
                
                if net_profit_pct > 0:
                    momentum_wins += 1
                    momentum_profit += net_profit_pct
                else:
                    momentum_losses += 1
                    momentum_loss += abs(net_profit_pct)
                
                trades.append({
                    'type': 'momentum',
                    'entry': entry_price,
                    'exit': exit_price,
                    'profit_pct': net_profit_pct
                })
        
        # Create momentum pattern
        if momentum_wins + momentum_losses > 20:
            total = momentum_wins + momentum_losses
            pattern = LearnedPattern(
                pattern_id=f"momentum_{symbol}_1h",
                pattern_type='momentum',
                symbol=symbol,
                timeframe='1h',
                conditions={'min_change_1h': 1.0, 'hold_hours': 4},
                total_occurrences=total,
                winning_trades=momentum_wins,
                losing_trades=momentum_losses,
                total_profit=momentum_profit,
                total_loss=momentum_loss,
                win_rate=(momentum_wins / total) * 100 if total > 0 else 0,
                avg_profit_per_trade=(momentum_profit - momentum_loss) / total if total > 0 else 0,
                profit_factor=momentum_profit / momentum_loss if momentum_loss > 0 else 0,
                first_seen=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat(),
                confidence=min(90, 50 + total / 2)
            )
            patterns[pattern.pattern_id] = pattern
        
        # Strategy 2: Reversal (buy after 2%+ drop)
        reversal_wins = 0
        reversal_losses = 0
        reversal_profit = 0.0
        reversal_loss = 0.0
        
        for i in range(24, len(candles) - 4):
            prev_close = candles[i-1]['close']
            curr_close = candles[i]['close']
            change = ((curr_close - prev_close) / prev_close) * 100
            
            if change <= -2.0:  # 2%+ drop
                entry_price = curr_close
                exit_price = candles[i + 4]['close']
                
                gross_profit_pct = ((exit_price - entry_price) / entry_price) * 100
                net_profit_pct = gross_profit_pct - (self.TRADING_FEE * 2 * 100)
                
                if net_profit_pct > 0:
                    reversal_wins += 1
                    reversal_profit += net_profit_pct
                else:
                    reversal_losses += 1
                    reversal_loss += abs(net_profit_pct)
        
        # Create reversal pattern
        if reversal_wins + reversal_losses > 20:
            total = reversal_wins + reversal_losses
            pattern = LearnedPattern(
                pattern_id=f"reversal_{symbol}_1h",
                pattern_type='reversal',
                symbol=symbol,
                timeframe='1h',
                conditions={'max_drop_1h': -2.0, 'hold_hours': 4},
                total_occurrences=total,
                winning_trades=reversal_wins,
                losing_trades=reversal_losses,
                total_profit=reversal_profit,
                total_loss=reversal_loss,
                win_rate=(reversal_wins / total) * 100 if total > 0 else 0,
                avg_profit_per_trade=(reversal_profit - reversal_loss) / total if total > 0 else 0,
                profit_factor=reversal_profit / reversal_loss if reversal_loss > 0 else 0,
                first_seen=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat(),
                confidence=min(90, 50 + total / 2)
            )
            patterns[pattern.pattern_id] = pattern
        
        # Strategy 3: Volume breakout
        volume_wins = 0
        volume_losses = 0
        volume_profit = 0.0
        volume_loss = 0.0
        
        for i in range(24, len(candles) - 4):
            avg_volume = sum(c['volume'] for c in candles[i-24:i]) / 24
            curr_volume = candles[i]['volume']
            
            if curr_volume > avg_volume * 3:  # 3x average volume
                entry_price = candles[i]['close']
                exit_price = candles[i + 4]['close']
                
                gross_profit_pct = ((exit_price - entry_price) / entry_price) * 100
                net_profit_pct = gross_profit_pct - (self.TRADING_FEE * 2 * 100)
                
                if net_profit_pct > 0:
                    volume_wins += 1
                    volume_profit += net_profit_pct
                else:
                    volume_losses += 1
                    volume_loss += abs(net_profit_pct)
        
        # Create volume pattern
        if volume_wins + volume_losses > 10:
            total = volume_wins + volume_losses
            pattern = LearnedPattern(
                pattern_id=f"volume_{symbol}_1h",
                pattern_type='volume_breakout',
                symbol=symbol,
                timeframe='1h',
                conditions={'min_volume_change': 300, 'hold_hours': 4},
                total_occurrences=total,
                winning_trades=volume_wins,
                losing_trades=volume_losses,
                total_profit=volume_profit,
                total_loss=volume_loss,
                win_rate=(volume_wins / total) * 100 if total > 0 else 0,
                avg_profit_per_trade=(volume_profit - volume_loss) / total if total > 0 else 0,
                profit_factor=volume_profit / volume_loss if volume_loss > 0 else 0,
                first_seen=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat(),
                confidence=min(80, 40 + total)
            )
            patterns[pattern.pattern_id] = pattern
        
        # Analyze best hours
        hourly_profits = defaultdict(list)
        for i, candle in enumerate(candles[:-1]):
            ts = datetime.fromtimestamp(candle['timestamp'] / 1000, tz=timezone.utc)
            hour = ts.hour
            
            next_close = candles[i + 1]['close']
            change = ((next_close - candle['close']) / candle['close']) * 100
            hourly_profits[hour].append(change)
        
        # Update elephant memory with hour insights
        for hour, profits in hourly_profits.items():
            avg_profit = sum(profits) / len(profits) if profits else 0
            if avg_profit > 0.1:
                self.memory.best_hours[hour] = avg_profit
            elif avg_profit < -0.1:
                self.memory.worst_hours[hour] = avg_profit
        
        for pattern in patterns.values():
            pattern.evidence_scope = "historical_backtest"
            pattern.fee_model = "assumed_binance_spot_0.1pct_per_leg"
            pattern.source_id = "binance:/api/v3/klines"
            pattern.source_timestamp = candles[-1]["source_timestamp"]
            pattern.received_at = candles[-1]["received_at"]
            pattern.first_seen = _iso_timestamp(candles[0]["source_timestamp"])
            pattern.last_updated = _iso_timestamp(candles[-1]["source_timestamp"])
            pattern.generated_values = False
            pattern.action_eligible = False
            pattern.eligible_for_learning = False
        return patterns
    
    def learn_from_symbol(self, symbol: str, days: int = 90) -> Dict:
        """Learn everything from a symbol's history"""
        logger.info(f"🐘📚 Learning from {symbol} ({days} days)...")
        
        # Fetch data
        candles = self.fetch_binance_history(symbol, '1h', days)
        
        if not candles:
            return _no_data_receipt(
                "complete_provenance_bearing_historical_candles_required",
                now=float(self._clock()),
                purpose="historical_research",
            )
        
        # Analyze patterns
        patterns = self.analyze_patterns(candles)
        if not patterns:
            return _no_data_receipt(
                "no_proven_historical_pattern_sample",
                now=float(self._clock()),
                purpose="historical_research",
            )
        
        # Store in elephant memory
        for pattern in patterns.values():
            self.memory.remember_pattern(pattern)
        
        # Update asset performance
        total_trades = sum(p.total_occurrences for p in patterns.values())
        total_wins = sum(p.winning_trades for p in patterns.values())
        total_profit = sum(p.total_profit - p.total_loss for p in patterns.values())
        
        self.memory.asset_performance[symbol] = {
            'trades': total_trades,
            'wins': total_wins,
            'win_rate': (total_wins / total_trades * 100),
            'total_profit': total_profit,
            'profit_factor': sum(p.profit_factor for p in patterns.values()) / len(patterns),
            'last_analyzed': _iso_timestamp(candles[-1]["source_timestamp"]),
            'evidence_scope': "historical_backtest",
            'fee_model': "assumed_binance_spot_0.1pct_per_leg",
            'action_eligible': False,
            'eligible_for_learning': False,
            'generated_values': False,
        }
        
        # Update stats
        self.memory.total_historical_trades += total_trades
        self.memory.total_historical_profit += total_profit
        self.memory.learning_sessions += 1
        self.memory._save_memory()
        
        return {
            'success': True,
            'data_status': "historical_research",
            'truth_status': "real_derived",
            'symbol': symbol,
            'candles_analyzed': len(candles),
            'patterns_found': len(patterns),
            'total_trades': total_trades,
            'win_rate': (total_wins / total_trades * 100) if total_trades > 0 else 0,
            'profit': total_profit,
            'fee_model': "assumed_binance_spot_0.1pct_per_leg",
            'action_eligible': False,
            'eligible_for_accounting': False,
            'eligible_for_learning': False,
            'generated_values': False,
        }
    
    def learn_all_major_pairs(self, days: int = 30):
        """Learn from all major trading pairs"""
        major_pairs = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT',
            'SOLUSDT', 'DOTUSDT', 'AVAXUSDT', 'LINKUSDT', 'MATICUSDT',
            'LTCUSDT', 'ATOMUSDT', 'UNIUSDT', 'NEARUSDT', 'APTUSDT'
        ]
        
        results = []
        for symbol in major_pairs:
            try:
                result = self.learn_from_symbol(symbol, days)
                results.append(result)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.warning(f"Failed to learn {symbol}: {e}")
        
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# 👑 QUEEN INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class QueenElephantBrain:
    """
    Queen Sero's brain enhanced with elephant memory
    """
    
    def __init__(self):
        self.elephant = ElephantMemory()
        self.learner = HistoricalLearner(self.elephant)
        
        logger.info("🐘👑 Queen's Elephant Brain initialized!")
        logger.info(f"   📊 Patterns in memory: {len(self.elephant.patterns)}")
        logger.info(f"   🚫 Blocked paths: {len(self.elephant.blocked_paths)}")
        logger.info(f"   ⭐ Golden paths: {len(self.elephant.golden_paths)}")
    
    def should_trade(self, from_asset: str, to_asset: str, 
                     price_change: float, volume_change: float) -> Dict:
        """
        Use elephant memory to decide if a trade is good
        """
        # Check if path is blocked
        is_blocked, reason = self.elephant.is_path_blocked(from_asset, to_asset)
        if is_blocked:
            return {
                'should_trade': False,
                'confidence': 100,
                'reason': f"🐘🚫 ELEPHANT NEVER FORGETS: {reason}"
            }
        
        # Check if path is golden
        is_golden, win_rate = self.elephant.is_golden_path(from_asset, to_asset)
        if is_golden and win_rate > 70:
            return {
                'should_trade': True,
                'confidence': win_rate,
                'reason': f"🐘⭐ GOLDEN PATH: {win_rate:.1f}% historical win rate!"
            }
        
        # Check hour
        current_hour = datetime.now().hour
        if current_hour in self.elephant.worst_hours:
            return {
                'should_trade': False,
                'confidence': 70,
                'reason': f"🐘⏰ BAD HOUR: Hour {current_hour} historically loses money"
            }
        
        # Get pattern signals.
        # ⚠ Pass 0.0 as price; downstream consumers should treat 0.0 as
        # "price not available" rather than a real reading. Logged once.
        if not getattr(self, "_warned_zero_price", False):
            self._warned_zero_price = True
            logger.warning("[stub] aureon_elephant_learning.get_pattern_signals "
                           "called with price=0.0 placeholder — wire real "
                           "current price to populate the signal")
        signals = self.elephant.get_pattern_signals(
            f"{from_asset}{to_asset}",
            0,  # Would need real price
            price_change,
            volume_change
        )
        
        if signals:
            best_signal = max(signals, key=lambda s: s['confidence'])
            return {
                'should_trade': best_signal['win_rate'] > 55,
                'confidence': best_signal['confidence'],
                'reason': f"🐘📊 PATTERN: {best_signal['reason']}",
                'expected_profit': best_signal['avg_profit']
            }
        
        # Check asset score
        asset_score = self.elephant.get_asset_score(to_asset)
        if asset_score < 40:
            return {
                'should_trade': False,
                'confidence': 60,
                'reason': f"🐘📉 WEAK ASSET: {to_asset} scores {asset_score:.1f}/100"
            }
        
        # Default: no strong signal
        return {
            'should_trade': False,
            'confidence': 50,
            'reason': "🐘🤔 NO STRONG PATTERN - waiting for better setup"
        }
    
    def learn_before_trading(self, days: int = 30):
        """Learn from history before starting to trade"""
        logger.info("🐘📚 ELEPHANT LEARNING SESSION STARTING...")
        logger.info(f"   📅 Analyzing {days} days of historical data")
        
        results = self.learner.learn_all_major_pairs(days)
        
        # Summary
        total_patterns = sum(r.get('patterns_found', 0) for r in results if r.get('success'))
        total_trades = sum(r.get('total_trades', 0) for r in results if r.get('success'))
        avg_win_rate = sum(r.get('win_rate', 0) for r in results if r.get('success')) / len(results)
        
        logger.info(f"🐘✅ LEARNING COMPLETE!")
        logger.info(f"   📊 Patterns learned: {total_patterns}")
        logger.info(f"   📈 Trades analyzed: {total_trades}")
        logger.info(f"   🎯 Average win rate: {avg_win_rate:.1f}%")
        
        return {
            'patterns_learned': total_patterns,
            'trades_analyzed': total_trades,
            'avg_win_rate': avg_win_rate
        }
    
    def record_trade_result(self, from_asset: str, to_asset: str, 
                           profit: float, was_profitable: bool):
        """Record a real trade result in elephant memory"""
        path_key = f"{from_asset}→{to_asset}"
        
        # Update or create path stats
        if path_key not in self.elephant.asset_performance:
            self.elephant.asset_performance[path_key] = {
                'trades': 0, 'wins': 0, 'losses': 0,
                'total_profit': 0, 'total_loss': 0
            }
        
        stats = self.elephant.asset_performance[path_key]
        stats['trades'] += 1
        
        if was_profitable:
            stats['wins'] += 1
            stats['total_profit'] += profit
        else:
            stats['losses'] += 1
            stats['total_loss'] += abs(profit)
        
        stats['win_rate'] = (stats['wins'] / stats['trades']) * 100
        
        # Auto-block consistently losing paths
        if stats['trades'] >= 5 and stats['win_rate'] < 30:
            self.elephant.block_path_forever(
                from_asset, to_asset,
                f"Only {stats['win_rate']:.1f}% win rate after {stats['trades']} trades",
                stats['losses'],
                stats['total_loss']
            )
        
        # Auto-mark golden paths
        if stats['trades'] >= 10 and stats['win_rate'] > 70:
            self.elephant.mark_golden_path(
                from_asset, to_asset,
                stats['wins'],
                stats['total_profit'],
                stats['win_rate']
            )
        
        self.elephant._save_memory()

    def record_trade_outcome(self, outcome: Any):
        """Convenience method to accept WinOutcome dict or dataclass and record it."""
        try:
            if isinstance(outcome, dict):
                from_asset = outcome.get('from_asset') or outcome.get('from') or ''
                to_asset = outcome.get('to_asset') or outcome.get('to') or ''
                profit = outcome.get('net_profit_usd') or outcome.get('pnl') or outcome.get('profit_usd') or 0.0
                is_win = bool(outcome.get('is_win') or (profit is not None and float(profit) >= 0.01))
            else:
                # Dataclass-like object
                from_asset = getattr(outcome, 'from_asset', '')
                to_asset = getattr(outcome, 'to_asset', '')
                profit = getattr(outcome, 'net_profit_usd', None) or getattr(outcome, 'pnl', None) or 0.0
                is_win = bool(getattr(outcome, 'is_win', (profit is not None and float(profit) >= 0.01)))

            # Fall back if empty
            if not from_asset or not to_asset:
                return False

            self.record_trade_result(from_asset, to_asset, float(profit), is_win)
            return True
        except Exception:
            logger.exception('Failed to record trade outcome in Elephant Memory')
            return False

# ═══════════════════════════════════════════════════════════════════════════════
# 🏃 MAIN - Test the elephant learning
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("🐘👑 QUEEN SERO's ELEPHANT MEMORY LEARNING SYSTEM 👑🐘")
    print("=" * 70)
    print()
    print('"An elephant NEVER forgets. Neither does Queen Sero."')
    print()
    
    # Initialize
    brain = QueenElephantBrain()
    
    # Show current memory
    print()
    print(brain.elephant.summarize())
    print()
    
    # Learn from history
    print("=" * 70)
    print("📚 LEARNING FROM HISTORICAL DATA...")
    print("=" * 70)
    
    # Learn from top pairs
    results = brain.learn_before_trading(days=30)
    
    print()
    print("=" * 70)
    print("🐘 LEARNING COMPLETE!")
    print("=" * 70)
    print(f"   📊 Patterns learned: {results['patterns_learned']}")
    print(f"   📈 Trades analyzed: {results['trades_analyzed']}")
    print(f"   🎯 Average win rate: {results['avg_win_rate']:.1f}%")
    print()
    
    # Show updated memory
    print(brain.elephant.summarize())
    
    # Test a trade decision
    print()
    print("=" * 70)
    print("🧪 TESTING TRADE DECISIONS...")
    print("=" * 70)
    
    # Test cases
    test_trades = [
        ('USDT', 'BTC', 1.5, 200),   # Momentum + volume
        ('BTC', 'ETH', -2.5, 50),    # Reversal pattern
        ('USDT', 'DOGE', 0.1, 10),   # No pattern
    ]
    
    for from_a, to_a, price_chg, vol_chg in test_trades:
        result = brain.should_trade(from_a, to_a, price_chg, vol_chg)
        print(f"\n{from_a}→{to_a} (price:{price_chg:+.1f}%, vol:{vol_chg}%):")
        print(f"   Trade: {'✅ YES' if result['should_trade'] else '❌ NO'}")
        print(f"   Confidence: {result['confidence']:.1f}%")
        print(f"   Reason: {result['reason']}")


if __name__ == "__main__":
    main()
