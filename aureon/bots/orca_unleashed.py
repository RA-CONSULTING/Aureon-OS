#!/usr/bin/env python3
"""
🦈🔪⚡ ORCA UNLEASHED - THE KILLER WHALE HUNTS! ⚡🔪🦈
═══════════════════════════════════════════════════════════

NO MORE TINY TRADES!
NO MORE DEATH BY FEES!
NO MORE PHANTOM PROFITS!

THE ORCA WAITS... WATCHES... AND STRIKES WITH PRECISION!

Rules:
1. MINIMUM $5 trade (no more dust!)
2. ONLY trade when confidence > 75%
3. Wait for REAL opportunities (not noise)
4. Take profit at 1-2%, cut losses at 0.5%
5. Maximum 3 trades per hour (quality over quantity)

Gary Leckey | January 2026 | UNLEASH THE BEAST!
"""

from __future__ import annotations
import json
import time
import math
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Real portfolio tracker
try:
    from aureon.portfolio.aureon_real_portfolio_tracker import get_real_portfolio_tracker, RealPortfolioSnapshot
    PORTFOLIO_TRACKER_AVAILABLE = True
except ImportError:
    PORTFOLIO_TRACKER_AVAILABLE = False
    get_real_portfolio_tracker = None

# 🔮 PROBABILITY NEXUS - For smart kill decisions!
try:
    from aureon.bridges.aureon_probability_nexus import AureonProbabilityNexus, Prediction
    PROBABILITY_NEXUS_AVAILABLE = True
    logger.info("🔮 Probability Nexus CONNECTED - Smart kill decisions enabled!")
except ImportError:
    PROBABILITY_NEXUS_AVAILABLE = False
    AureonProbabilityNexus = None
    Prediction = None

# 🎯 HUNTING GROUNDS - Find best places to hunt!
try:
    from aureon.bots.orca_hunting_grounds import OrcaHuntingGrounds, HuntingGround
    HUNTING_GROUNDS_AVAILABLE = True
    logger.info("🎯 Hunting Grounds CONNECTED - Smart venue selection enabled!")
except ImportError:
    HUNTING_GROUNDS_AVAILABLE = False
    OrcaHuntingGrounds = None
    HuntingGround = None

# Exchange clients
try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    AlpacaClient = None

try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False
    KrakenClient = None

try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    BinanceClient = None


@dataclass
class OrcaHunt:
    """A potential hunting opportunity."""
    symbol: str
    exchange: str
    direction: str  # 'long' or 'short'
    confidence: float
    entry_price: float
    target_price: float
    stop_price: float
    size_usd: float
    reasoning: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    market_receipt: Dict[str, Any] = field(default_factory=dict)
    action_eligible: bool = False
    source_id: Optional[str] = None
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    truth_status: str = "no_data"
    generated_values: bool = False


@dataclass
class OrcaKill:
    """A completed trade."""
    symbol: str
    exchange: str
    direction: str
    entry_price: float
    exit_price: float
    size_usd: float
    pnl_usd: float
    pnl_pct: float
    duration_seconds: float
    timestamp: float
    entry_order_id: Optional[str] = None
    exit_order_id: Optional[str] = None
    entry_fee: Optional[float] = None
    exit_fee: Optional[float] = None
    fee_currency: Optional[str] = None
    trade_ids: List[str] = field(default_factory=list)
    source_timestamp: Optional[float] = None
    truth_status: str = "no_data"
    eligible_for_learning: bool = False
    generated_values: bool = False


class OrcaUnleashed:
    """
    🦈🔪⚡ THE UNLEASHED ORCA ⚡🔪🦈
    
    No more tiny trades. No more death by fees.
    The Orca waits for the perfect moment, then STRIKES!
    """
    
    # STRICT RULES - NO EXCEPTIONS!
    # 🔥 TRUTH: Alpaca fees are 0.25% PER SIDE = 0.50% round trip MINIMUM!
    # So we MUST have take profit > 0.50% just to break even!
    MIN_TRADE_SIZE_USD = 5.0       # Minimum $5 per trade (bigger = better fee ratio)
    MIN_CONFIDENCE = 0.70          # 70% confidence minimum 
    MAX_TRADES_PER_HOUR = 3        # FEWER trades = FEWER fees!
    TAKE_PROFIT_PCT = 0.015        # Risk policy, not a provider fee observation
    STOP_LOSS_PCT = 0.008          # 0.8% stop loss (tighter risk management)
    MAX_POSITION_PCT = 0.60        # Max 60% of capital per trade
    MAX_HOLD_MINUTES = 30          # 🕐 MAX 30 minutes - give trades TIME to develop!
    
    # Freshness policies for evidence used in external actions.
    QUOTE_MAX_AGE_SECONDS = 120.0
    ACCOUNT_MAX_AGE_SECONDS = 120.0
    ORDER_MAX_AGE_SECONDS = 300.0
    
    # Track when positions were opened
    position_open_times: Dict[str, float] = {}
    
    def __init__(self):
        self._runtime_started = False
        logger.info("🦈🔪⚡ ORCA UNLEASHED - INITIALIZING ⚡🔪🦈")
        
        # Position timing
        self.position_open_times = {}
        
        # 🔮 PROBABILITY NEXUS - For smart kill validation!
        self.probability_nexus = None
        if self._runtime_started and PROBABILITY_NEXUS_AVAILABLE and AureonProbabilityNexus:
            try:
                self.probability_nexus = AureonProbabilityNexus()
                logger.info("🔮 Probability Nexus INITIALIZED - Batten Matrix validation ready!")
            except Exception as e:
                logger.warning(f"⚠️ Probability Nexus failed to init: {e}")
        
        # 🎯 HUNTING GROUNDS - Find best places to hunt!
        self.hunting_grounds = None
        if self._runtime_started and HUNTING_GROUNDS_AVAILABLE and OrcaHuntingGrounds:
            try:
                self.hunting_grounds = OrcaHuntingGrounds()
                logger.info("🎯 Hunting Grounds INITIALIZED - Smart venue selection ready!")
            except Exception as e:
                logger.warning(f"⚠️ Hunting Grounds failed to init: {e}")
        
        # Portfolio tracker
        self.portfolio_tracker = None
        if self._runtime_started and PORTFOLIO_TRACKER_AVAILABLE and get_real_portfolio_tracker:
            self.portfolio_tracker = get_real_portfolio_tracker()
            logger.info("💰👁️ Real Portfolio Tracker connected!")
        
        # Exchange clients
        self.alpaca = None
        self.kraken = None
        self.binance = None
        # Provider construction is owned by start(), never by the constructor.
        
        # Hunting state
        self.active_hunts: List[OrcaHunt] = []
        self.completed_kills: List[OrcaKill] = []
        self.dry_run_attempts: List[Dict[str, Any]] = []
        self.execution_receipts: List[Dict[str, Any]] = []
        self.pending_orders: Dict[str, Dict[str, Any]] = {}
        self.entry_fill_receipts: Dict[str, Dict[str, Any]] = {}
        self.accounted_order_ids: set[str] = set()
        self.trades_this_hour = 0
        self.hour_start = time.time()
        
        # Session stats
        self.session_start = time.time()
        self.session_pnl = 0.0
        self.session_trades = 0
        self.session_wins = 0
        self.session_losses = 0
        
        # State persistence
        self.state_file = Path("orca_unleashed_state.json")
        # Local state reads are owned by start().
        
        logger.info("🦈 ORCA IS READY TO HUNT!")
        # Status output is owned by run().
    
    def start(self) -> bool:
        """Explicitly construct dependencies and read local state."""
        if self._runtime_started:
            return True
        try:
            from aureon.core.aureon_baton_link import link_system
            link_system(__name__)
        except Exception as exc:
            logger.warning("Baton link unavailable: %s", type(exc).__name__)
        if PROBABILITY_NEXUS_AVAILABLE and AureonProbabilityNexus:
            try:
                self.probability_nexus = AureonProbabilityNexus()
            except Exception as exc:
                logger.warning("Probability Nexus unavailable: %s", type(exc).__name__)
        if HUNTING_GROUNDS_AVAILABLE and OrcaHuntingGrounds:
            try:
                self.hunting_grounds = OrcaHuntingGrounds()
            except Exception as exc:
                logger.warning("Hunting Grounds unavailable: %s", type(exc).__name__)
        if PORTFOLIO_TRACKER_AVAILABLE and get_real_portfolio_tracker:
            try:
                self.portfolio_tracker = get_real_portfolio_tracker()
            except Exception as exc:
                logger.warning("Portfolio tracker unavailable: %s", type(exc).__name__)
        self._init_exchanges()
        self._load_state()
        self._runtime_started = True
        return True

    def close(self) -> None:
        """Release explicitly started providers."""
        for client in (self.alpaca, self.kraken, self.binance):
            closer = getattr(client, "close", None)
            if callable(closer):
                try:
                    closer()
                except Exception:
                    logger.debug("Provider close failed", exc_info=True)
        self._runtime_started = False

    def _init_exchanges(self):
        """Initialize exchange connections."""
        exchange_count = 0
        
        if ALPACA_AVAILABLE:
            try:
                self.alpaca = AlpacaClient()
                exchange_count += 1
                logger.info("🦙 Alpaca CONNECTED")
            except Exception as e:
                logger.warning(f"🦙 Alpaca failed: {e}")
        
        if KRAKEN_AVAILABLE:
            try:
                self.kraken = get_kraken_client()
                exchange_count += 1
                logger.info("🐙 Kraken CONNECTED")
            except Exception as e:
                logger.warning(f"🐙 Kraken failed: {e}")
        
        if BINANCE_AVAILABLE:
            try:
                self.binance = get_binance_client()
                exchange_count += 1
                logger.info("🟡 Binance CONNECTED")
            except Exception as e:
                logger.warning(f"🟡 Binance failed: {e}")
        
        if exchange_count == 0:
            logger.error("🚨 NO EXCHANGES CONNECTED! Orca is BLIND!")
        else:
            logger.info(f"🌐 {exchange_count} exchanges connected")
    
    def _load_state(self):
        """Load previous state."""
        try:
            if self.state_file.exists():
                data = json.loads(self.state_file.read_text())
                self.session_pnl = data.get('total_pnl', 0.0)
                self.session_trades = data.get('total_trades', 0)
                self.session_wins = data.get('total_wins', 0)
                self.session_losses = data.get('total_losses', 0)
                pending = data.get('pending_orders')
                entries = data.get('entry_fill_receipts')
                accounted = data.get('accounted_order_ids')
                if isinstance(pending, dict):
                    self.pending_orders = {
                        str(key): dict(value)
                        for key, value in pending.items()
                        if isinstance(value, dict)
                    }
                if isinstance(entries, dict):
                    self.entry_fill_receipts = {
                        str(key): dict(value)
                        for key, value in entries.items()
                        if isinstance(value, dict)
                    }
                if isinstance(accounted, list):
                    self.accounted_order_ids = {
                        str(value) for value in accounted if str(value).strip()
                    }
                logger.info(f"📂 Loaded state: {self.session_trades} trades, ${self.session_pnl:.2f} P&L")
        except Exception as e:
            logger.warning(f"Could not load state: {e}")
    
    def _save_state(self):
        """Save current state."""
        try:
            data = {
                'total_pnl': self.session_pnl,
                'total_trades': self.session_trades,
                'total_wins': self.session_wins,
                'total_losses': self.session_losses,
                'pending_orders': {
                    key: self._durable_receipt(value)
                    for key, value in self.pending_orders.items()
                },
                'entry_fill_receipts': {
                    key: self._durable_receipt(value)
                    for key, value in self.entry_fill_receipts.items()
                },
                'accounted_order_ids': sorted(self.accounted_order_ids),
                'last_update': time.time()
            }
            tmp = self.state_file.with_suffix('.tmp')
            tmp.write_text(json.dumps(data, indent=2))
            tmp.rename(self.state_file)
        except Exception as e:
            logger.warning(f"Could not save state: {e}")

    @staticmethod
    def _durable_receipt(receipt: Dict[str, Any]) -> Dict[str, Any]:
        """Persist only the canonical JSON receipt, never arbitrary raw payloads."""
        durable_keys = {
            "kind", "exchange", "symbol", "side", "status", "provider_status",
            "data_status", "truth_status", "reason", "provider_order_id",
            "source_id", "source_timestamp", "received_at", "filled_qty",
            "filled_avg_price", "filled_notional", "fee", "fee_currency",
            "trade_ids", "fill_receipt_complete", "eligible_for_accounting",
            "eligible_for_learning", "reconciliation_required", "generated_values",
        }
        return {key: receipt.get(key) for key in durable_keys if key in receipt}
    
    def _log_status(self):
        """Log current status."""
        if self.portfolio_tracker:
            summary = self.portfolio_tracker.get_quick_summary()
            print()
            print("🦈═══════════════════════════════════════════════════🦈")
            print("         ORCA UNLEASHED - STATUS")
            print("🦈═══════════════════════════════════════════════════🦈")
            print(f"  💰 Available Capital: {summary['total_usd']}")
            print(f"  📊 Portfolio P&L: {summary['pnl']} ({summary['pnl_pct']})")
            print(f"  📈 Session P&L: ${self.session_pnl:.2f}")
            print(f"  🎯 Session Trades: {self.session_trades}")
            print(f"  ✅ Wins: {self.session_wins} | ❌ Losses: {self.session_losses}")
            if self.session_trades > 0:
                win_rate = (self.session_wins / self.session_trades) * 100
                print(f"  📊 Win Rate: {win_rate:.1f}%")
            print(f"  ⏰ Trades This Hour: {self.trades_this_hour}/{self.MAX_TRADES_PER_HOUR}")
            print("🦈═══════════════════════════════════════════════════🦈")
            print()
    
    @staticmethod
    def _finite_number(value: Any, *, positive: bool = False, nonnegative: bool = False) -> Optional[float]:
        if isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(number):
            return None
        if positive and number <= 0:
            return None
        if nonnegative and number < 0:
            return None
        return number

    @staticmethod
    def _timestamp_epoch(value: Any) -> Optional[float]:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            timestamp = float(value)
            while timestamp > 10_000_000_000:
                timestamp /= 1000.0
            return timestamp if math.isfinite(timestamp) and timestamp > 0 else None
        text = str(value).strip()
        if not text:
            return None
        try:
            numeric = float(text)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.timestamp()
            except ValueError:
                return None
        return OrcaUnleashed._timestamp_epoch(numeric)

    @classmethod
    def _fresh_timestamp(
        cls,
        value: Any,
        *,
        max_age_seconds: float,
        now: Optional[float] = None,
    ) -> Optional[float]:
        timestamp = cls._timestamp_epoch(value)
        observed_now = time.time() if now is None else now
        if timestamp is None or timestamp > observed_now + 5.0:
            return None
        if observed_now - timestamp > max_age_seconds:
            return None
        return timestamp

    @staticmethod
    def _valid_provider_id(value: Any) -> Optional[str]:
        text = str(value or "").strip()
        if not text or text.lower() in {"none", "null", "unknown", "pending"}:
            return None
        if text.lower().startswith(("fake", "mock", "demo", "simulated")):  # sentinel rejected as no_data
            return None
        if text.lstrip("-").isdigit() and int(text) <= 0:
            return None
        return text

    @staticmethod
    def _no_data_receipt(kind: str, reason: str, **context: Any) -> Dict[str, Any]:
        return {
            "kind": kind,
            "status": "no_data",
            "data_status": "no_data",
            "truth_status": "no_data",
            "reason": reason,
            "source_id": None,
            "source_timestamp": None,
            "received_at": time.time(),
            "generated_values": False,
            "action_eligible": False,
            **context,
        }

    def _account_cash_receipt(self, account: Any, field_name: str) -> Dict[str, Any]:
        if not isinstance(account, dict):
            return self._no_data_receipt("account_cash", "provider_account_receipt_required")
        amount = self._finite_number(account.get(field_name), nonnegative=True)
        currency = str(account.get("currency") or "").strip().upper()
        account_id = self._valid_provider_id(account.get("id") or account.get("account_id"))
        source_timestamp = self._fresh_timestamp(
            account.get("source_timestamp") or account.get("provider_timestamp") or account.get("updated_at"),
            max_age_seconds=self.ACCOUNT_MAX_AGE_SECONDS,
        )
        truth_status = str(account.get("truth_status") or "").strip().lower()
        data_status = str(account.get("data_status") or "").strip().lower()
        if (
            amount is None
            or currency != "USD"
            or account_id is None
            or source_timestamp is None
            or truth_status not in {"real_observed", "real_derived"}
            or data_status != "live"
            or account.get("generated_values") is not False
        ):
            return self._no_data_receipt(
                "account_cash",
                "fresh_currency_specific_provider_account_receipt_required",
                currency=currency or None,
                amount=None,
            )
        return {
            "kind": "account_cash",
            "status": "live",
            "data_status": "live",
            "truth_status": truth_status,
            "provider": "alpaca",
            "source_id": str(account.get("source_id") or f"alpaca_account:{account_id}"),
            "source_timestamp": source_timestamp,
            "received_at": time.time(),
            "account_id": account_id,
            "currency": currency,
            "field": field_name,
            "amount": amount,
            "generated_values": False,
            "action_eligible": True,
        }

    def get_real_capital(self) -> Dict[str, Any]:
        """Return only a fresh USD cash receipt; never total-equity fallback."""
        if not self.alpaca:
            return self._no_data_receipt("account_cash", "alpaca_account_provider_unavailable")
        try:
            return self._account_cash_receipt(self.alpaca.get_account(), "cash")
        except Exception as exc:
            return self._no_data_receipt("account_cash", f"provider_account_error:{type(exc).__name__}")

    def get_available_cash(
        self,
        exchange: str = "alpaca",
        currency: str = "USD",
    ) -> Dict[str, Any]:
        """Return fresh USD buying-power evidence, or an explicit no-data receipt."""
        if exchange != "alpaca" or currency != "USD":
            return self._no_data_receipt(
                "account_cash",
                "exchange_and_currency_specific_account_adapter_receipt_required",
                exchange=exchange,
                currency=currency,
                amount=None,
            )
        if not self.alpaca:
            return self._no_data_receipt("account_cash", "alpaca_account_provider_unavailable")
        try:
            return self._account_cash_receipt(self.alpaca.get_account(), "buying_power")
        except Exception as exc:
            return self._no_data_receipt("account_cash", f"provider_account_error:{type(exc).__name__}")
    
    def validate_kill_decision(self, symbol: str, current_pnl_pct: float, hold_minutes: float) -> Tuple[bool, str, Optional[float]]:
        """
        🔮 BATTEN MATRIX KILL VALIDATION 🔮
        
        Uses the Probability Nexus to make smart close decisions:
        - If probability says trend will CONTINUE in our favor → HOLD
        - If probability says trend will REVERSE → CLOSE NOW
        - If coherence is LOW → CLOSE (uncertain market)
        
        Returns: (should_close, reason, confidence)
        """
        # Default: use basic timer
        if not self.probability_nexus:
            if hold_minutes >= self.MAX_HOLD_MINUTES:
                return True, "⏰ Timer expired (no nexus)", None
            return False, "Holding (no nexus)", None
        
        try:
            # Get current market state and prediction
            state = self.probability_nexus.calculate_indicators()
            prediction = self.probability_nexus.predict(state)
            
            prob = self._finite_number(getattr(prediction, 'probability', None), nonnegative=True)
            confidence = self._finite_number(getattr(prediction, 'confidence', None), nonnegative=True)
            coherence = self._finite_number(getattr(state, 'coherence', None), nonnegative=True)
            direction = prediction.direction  # 'BULLISH' or 'BEARISH'
            if prob is None or confidence is None or coherence is None:
                if hold_minutes >= self.MAX_HOLD_MINUTES:
                    return True, "Timer expired (nexus evidence unavailable)", None
                return False, "Holding (nexus evidence unavailable)", None
            
            # 🔮 VALIDATION PASS 1: Coherence Check
            # Low coherence = uncertain market = CLOSE
            if coherence < 0.5:
                return True, f"🔮 Low coherence ({coherence:.2f}) - market uncertain", coherence
            
            # 🔮 VALIDATION PASS 2: Trend Alignment
            # If we're LONG and nexus says BULLISH with high confidence → HOLD
            # If we're LONG and nexus says BEARISH → CLOSE
            we_are_long = True  # Our BTC position is always long for now
            trend_favorable = (we_are_long and direction == 'BULLISH') or \
                            (not we_are_long and direction == 'BEARISH')
            
            # 🔮 VALIDATION PASS 3: Confidence + Time Check
            # High confidence favorable trend → can hold longer
            # Low confidence or unfavorable → close sooner
            
            if trend_favorable and confidence >= 0.65:
                # Trend is in our favor with high confidence
                # Allow holding up to 2x normal time
                extended_time = self.MAX_HOLD_MINUTES * 1.5
                if hold_minutes >= extended_time:
                    return True, f"🔮 Extended hold expired ({hold_minutes:.1f}m)", confidence
                logger.info(f"🔮 Nexus says HOLD: {direction} @ {prob:.1%} conf={confidence:.2f} coh={coherence:.2f}")
                return False, f"🔮 Favorable: {direction} @ {confidence:.0%}", confidence
            
            elif not trend_favorable and confidence >= 0.55:
                # Trend is AGAINST us with medium+ confidence → CLOSE NOW
                return True, f"🔮 Trend reversal: {direction} @ {confidence:.0%}", confidence
            
            else:
                # Low confidence either way → use normal timer
                if hold_minutes >= self.MAX_HOLD_MINUTES:
                    return True, f"⏰ Timer expired (low conf {confidence:.0%})", confidence
                return False, f"Holding (low conf {confidence:.0%})", confidence
                
        except Exception as e:
            logger.warning(f"⚠️ Nexus validation error: {e}")
            # Fallback to timer
            if hold_minutes >= self.MAX_HOLD_MINUTES:
                return True, "⏰ Timer expired (nexus error)", None
            return False, "Holding (nexus error)", None
    
    def _normalize_position_receipt(self, position: Any) -> Dict[str, Any]:
        if not isinstance(position, dict):
            return self._no_data_receipt("position", "provider_position_receipt_required")
        symbol = str(position.get("symbol") or "").strip()
        position_id = self._valid_provider_id(
            position.get("provider_position_id")
            or position.get("asset_id")
            or position.get("id")
        )
        quantity = self._finite_number(position.get("qty"), positive=True)
        entry_price = self._finite_number(position.get("avg_entry_price"), positive=True)
        current_price = self._finite_number(position.get("current_price"), positive=True)
        source_timestamp = self._fresh_timestamp(
            position.get("source_timestamp")
            or position.get("provider_timestamp")
            or position.get("updated_at"),
            max_age_seconds=self.QUOTE_MAX_AGE_SECONDS,
        )
        truth_status = str(position.get("truth_status") or "").strip().lower()
        data_status = str(position.get("data_status") or "").strip().lower()
        if (
            not symbol
            or position_id is None
            or quantity is None
            or entry_price is None
            or current_price is None
            or source_timestamp is None
            or truth_status not in {"real_observed", "real_derived"}
            or data_status != "live"
            or position.get("generated_values") is not False
        ):
            return self._no_data_receipt(
                "position",
                "fresh_complete_provider_position_receipt_required",
                symbol=symbol or None,
            )
        return {
            "kind": "position",
            "status": "live",
            "data_status": "live",
            "truth_status": truth_status,
            "provider": "alpaca",
            "symbol": symbol,
            "provider_position_id": position_id,
            "source_id": str(
                position.get("source_id") or f"alpaca:position:{position_id}"
            ),
            "source_timestamp": source_timestamp,
            "received_at": time.time(),
            "quantity": quantity,
            "entry_price": entry_price,
            "current_price": current_price,
            "generated_values": False,
            "action_eligible": True,
            "raw_receipt": dict(position),
        }

    @staticmethod
    def _quote_asset(symbol: Any) -> Optional[str]:
        normalized = OrcaUnleashed._symbol_key(symbol)
        for quote in ("USDT", "USDC", "USD", "EUR", "GBP", "BTC", "ETH"):
            if normalized.endswith(quote) and len(normalized) > len(quote):
                return quote
        return None

    def _complete_close_fill(
        self,
        position: Dict[str, Any],
        exit_fill: Dict[str, Any],
    ) -> Optional[OrcaKill]:
        symbol_key = self._symbol_key(position.get("symbol"))
        entry_fill = self.entry_fill_receipts.get(symbol_key)
        if not isinstance(entry_fill, dict):
            self.execution_receipts.append(
                self._no_data_receipt(
                    "close_accounting",
                    "recorded_terminal_entry_fill_required",
                    symbol=position.get("symbol"),
                )
            )
            return None
        entry_qty = self._finite_number(entry_fill.get("filled_qty"), positive=True)
        exit_qty = self._finite_number(exit_fill.get("filled_qty"), positive=True)
        entry_notional = self._finite_number(entry_fill.get("filled_notional"), positive=True)
        exit_notional = self._finite_number(exit_fill.get("filled_notional"), positive=True)
        entry_fee = self._finite_number(entry_fill.get("fee"), nonnegative=True)
        exit_fee = self._finite_number(exit_fill.get("fee"), nonnegative=True)
        quote_asset = self._quote_asset(position.get("symbol"))
        entry_fee_currency = str(entry_fill.get("fee_currency") or "").upper()
        exit_fee_currency = str(exit_fill.get("fee_currency") or "").upper()
        entry_order_id = self._valid_provider_id(entry_fill.get("provider_order_id"))
        exit_order_id = self._valid_provider_id(exit_fill.get("provider_order_id"))
        if (
            entry_qty is None
            or exit_qty is None
            or entry_notional is None
            or exit_notional is None
            or entry_fee is None
            or exit_fee is None
            or quote_asset is None
            or entry_fee_currency != quote_asset
            or exit_fee_currency != quote_asset
            or entry_order_id is None
            or exit_order_id is None
        ):
            self.execution_receipts.append(
                self._no_data_receipt(
                    "close_accounting",
                    "complete_quote_currency_entry_and_exit_fill_receipts_required",
                    symbol=position.get("symbol"),
                )
            )
            return None
        qty_tolerance = max(1e-12, entry_qty * 1e-6)
        if abs(entry_qty - exit_qty) > qty_tolerance:
            self.execution_receipts.append(
                self._no_data_receipt(
                    "close_accounting",
                    "entry_and_exit_fill_quantities_must_match",
                    symbol=position.get("symbol"),
                )
            )
            return None
        if exit_order_id in self.accounted_order_ids:
            return None
        cost = entry_notional + entry_fee
        proceeds = exit_notional - exit_fee
        pnl_usd = proceeds - cost
        pnl_pct = (pnl_usd / cost) * 100.0
        entry_timestamp = self._finite_number(entry_fill.get("source_timestamp"), positive=True)
        exit_timestamp = self._finite_number(exit_fill.get("source_timestamp"), positive=True)
        if entry_timestamp is None or exit_timestamp is None or exit_timestamp < entry_timestamp:
            self.execution_receipts.append(
                self._no_data_receipt(
                    "close_accounting",
                    "ordered_entry_and_exit_provider_timestamps_required",
                    symbol=position.get("symbol"),
                )
            )
            return None
        kill = OrcaKill(
            symbol=str(position["symbol"]),
            exchange="alpaca",
            direction="long",
            entry_price=float(entry_fill["filled_avg_price"]),
            exit_price=float(exit_fill["filled_avg_price"]),
            size_usd=entry_notional,
            pnl_usd=pnl_usd,
            pnl_pct=pnl_pct,
            duration_seconds=exit_timestamp - entry_timestamp,
            timestamp=exit_timestamp,
            entry_order_id=entry_order_id,
            exit_order_id=exit_order_id,
            entry_fee=entry_fee,
            exit_fee=exit_fee,
            fee_currency=quote_asset,
            trade_ids=list(entry_fill.get("trade_ids") or [])
            + list(exit_fill.get("trade_ids") or []),
            source_timestamp=exit_timestamp,
            truth_status="real_derived",
            eligible_for_learning=True,
            generated_values=False,
        )
        self.accounted_order_ids.add(exit_order_id)
        self.session_pnl += pnl_usd
        if pnl_usd > 0:
            self.session_wins += 1
        else:
            self.session_losses += 1
        self.entry_fill_receipts.pop(symbol_key, None)
        self.position_open_times.pop(symbol_key, None)
        self._save_state()
        return kill

    def check_and_close_positions(self) -> List[OrcaKill]:
        """Close only from fresh position and complete provider fill receipts."""
        kills: List[OrcaKill] = []
        if not self.alpaca:
            return kills
        try:
            positions = self.alpaca.get_positions()
        except Exception as exc:
            self.execution_receipts.append(
                self._no_data_receipt(
                    "position_collection",
                    f"provider_position_read_failed:{type(exc).__name__}",
                )
            )
            return kills
        if not isinstance(positions, list) or not positions:
            self.execution_receipts.append(
                self._no_data_receipt(
                    "position_collection",
                    "stamped_provider_position_collection_receipt_required",
                )
            )
            return kills
        for raw_position in positions:
            position = self._normalize_position_receipt(raw_position)
            if position.get("action_eligible") is not True:
                self.execution_receipts.append(position)
                continue
            symbol = str(position["symbol"])
            symbol_key = self._symbol_key(symbol)
            entry_fill = self.entry_fill_receipts.get(symbol_key)
            if not isinstance(entry_fill, dict):
                self.execution_receipts.append(
                    self._no_data_receipt(
                        "close_decision",
                        "recorded_terminal_entry_fill_required",
                        symbol=symbol,
                    )
                )
                continue
            entry_qty = self._finite_number(entry_fill.get("filled_qty"), positive=True)
            entry_price = self._finite_number(entry_fill.get("filled_avg_price"), positive=True)
            if entry_qty is None or entry_price is None:
                continue
            quantity = float(position["quantity"])
            position_entry = float(position["entry_price"])
            qty_tolerance = max(1e-12, entry_qty * 1e-6)
            price_tolerance = max(1e-8, entry_price * 1e-3)
            if (
                abs(quantity - entry_qty) > qty_tolerance
                or abs(position_entry - entry_price) > price_tolerance
            ):
                self.execution_receipts.append(
                    self._no_data_receipt(
                        "close_decision",
                        "provider_position_does_not_match_recorded_entry_fill",
                        symbol=symbol,
                    )
                )
                continue
            current_price = float(position["current_price"])
            gross_pnl_fraction = (current_price - entry_price) / entry_price
            entry_timestamp = self._finite_number(entry_fill.get("source_timestamp"), positive=True)
            if entry_timestamp is None:
                continue
            hold_minutes = (time.time() - entry_timestamp) / 60.0
            should_close = (
                gross_pnl_fraction >= self.TAKE_PROFIT_PCT
                or gross_pnl_fraction <= -self.STOP_LOSS_PCT
            )
            close_reason = "provider_price_risk_threshold"
            if not should_close:
                should_close, close_reason, _ = self.validate_kill_decision(
                    symbol, gross_pnl_fraction, hold_minutes
                )
            if not should_close:
                continue
            latch_key = self._order_latch_key("alpaca", symbol, "sell")
            if latch_key in self.pending_orders:
                exit_fill = self._reconcile_latched_order(
                    latch_key,
                    exchange="alpaca",
                    symbol=symbol,
                    side="sell",
                    quantity=quantity,
                )
            else:
                try:
                    order = self.alpaca.place_order(
                        symbol=symbol,
                        qty=quantity,
                        side="sell",
                        type="market",
                        time_in_force="gtc",
                    )
                except Exception as exc:
                    exit_fill = self._pending_order_receipt(
                        "alpaca",
                        symbol,
                        "sell",
                        None,
                        f"provider_submission_outcome_unproven:{type(exc).__name__}",
                    )
                else:
                    exit_fill = self._normalize_terminal_fill(
                        "alpaca",
                        order,
                        expected_symbol=symbol,
                        expected_side="sell",
                        expected_quantity=quantity,
                    )
                if exit_fill.get("fill_receipt_complete") is not True:
                    self.pending_orders[latch_key] = exit_fill
                    self._save_state()
                    exit_fill = self._reconcile_latched_order(
                        latch_key,
                        exchange="alpaca",
                        symbol=symbol,
                        side="sell",
                        quantity=quantity,
                    )
            self.execution_receipts.append(exit_fill)
            if exit_fill.get("fill_receipt_complete") is not True:
                continue
            kill = self._complete_close_fill(position, exit_fill)
            if kill is not None:
                kills.append(kill)
        return kills
    
    def can_trade(self) -> Tuple[bool, str]:
        """Check if trading is allowed."""
        # Check hourly limit
        if time.time() - self.hour_start > 3600:
            self.trades_this_hour = 0
            self.hour_start = time.time()
        
        if self.trades_this_hour >= self.MAX_TRADES_PER_HOUR:
            return False, f"⏰ Hourly limit reached ({self.MAX_TRADES_PER_HOUR} trades)"
        
        # Check capital - use AVAILABLE CASH not total equity
        capital_receipt = self.get_available_cash()
        if capital_receipt.get("action_eligible") is not True:
            return False, f"NO_DATA: {capital_receipt.get('reason') or 'fresh account receipt required'}"
        capital = self._finite_number(capital_receipt.get("amount"), nonnegative=True)
        if capital is None or capital < self.MIN_TRADE_SIZE_USD:
            available_text = "unknown" if capital is None else f"{capital:.2f}"
            return False, f"Insufficient USD buying power: {available_text}"
        
        return True, "✅ Ready to hunt!"
    
    def calculate_position_size(
        self,
        exchange: str = "alpaca",
        currency: str = "USD",
    ) -> Dict[str, Any]:
        """Derive a USD size only from an eligible account receipt."""
        cash_receipt = self.get_available_cash(exchange, currency)
        if cash_receipt.get("action_eligible") is not True:
            return self._no_data_receipt(
                "position_size",
                "fresh_currency_specific_account_receipt_required",
                account_receipt=cash_receipt,
                size_usd=None,
            )
        available = self._finite_number(cash_receipt.get("amount"), nonnegative=True)
        if available is None:
            return self._no_data_receipt(
                "position_size", "finite_available_cash_required", size_usd=None
            )
        safe_capital = available * 0.90
        if safe_capital < self.MIN_TRADE_SIZE_USD:
            return self._no_data_receipt(
                "position_size",
                "minimum_trade_size_not_available",
                currency="USD",
                size_usd=None,
            )
        max_size = safe_capital * self.MAX_POSITION_PCT
        size = max(self.MIN_TRADE_SIZE_USD, min(max_size, safe_capital * 0.5))
        return {
            "kind": "position_size",
            "status": "live",
            "data_status": "live",
            "truth_status": "real_derived",
            "source_id": cash_receipt["source_id"],
            "source_timestamp": cash_receipt["source_timestamp"],
            "received_at": time.time(),
            "currency": "USD",
            "provider": exchange,
            "size_usd": size,
            "account_receipt": cash_receipt,
            "risk_policy": {
                "cash_reserve_fraction": 0.10,
                "max_position_fraction": self.MAX_POSITION_PCT,
            },
            "generated_values": False,
            "action_eligible": True,
        }
    
    @staticmethod
    def _symbol_key(symbol: Any) -> str:
        return "".join(character for character in str(symbol or "").upper() if character.isalnum())

    def _normalize_quote_receipt(
        self,
        exchange: str,
        symbol: str,
        ticker: Any,
        *,
        now: Optional[float] = None,
    ) -> Dict[str, Any]:
        observed_now = time.time() if now is None else now
        if not isinstance(ticker, dict):
            return self._no_data_receipt("market_quote", "provider_quote_receipt_required", exchange=exchange, symbol=symbol)
        truth_status = str(ticker.get("truth_status") or "real_observed").strip().lower()
        data_status = str(ticker.get("data_status") or "live").strip().lower()
        if (
            truth_status not in {"real_observed", "real_derived"}
            or data_status != "live"
            or ticker.get("generated_values") is True
        ):
            return self._no_data_receipt("market_quote", "live_provider_quote_required", exchange=exchange, symbol=symbol)

        bid = self._finite_number(ticker.get("bid") if "bid" in ticker else ticker.get("bidPrice"), positive=True)
        ask = self._finite_number(ticker.get("ask") if "ask" in ticker else ticker.get("askPrice"), positive=True)
        raw_last = ticker.get("last") if "last" in ticker else ticker.get("lastPrice")
        price_kind = "provider_last_trade"
        price_source = "provider_ticker"
        if isinstance(raw_last, dict):
            price = self._finite_number(raw_last.get("price"), positive=True)
            price_source = str(raw_last.get("source") or "").strip()
            price_kind = "derived_midpoint" if "midpoint" in price_source.lower() else "provider_last_trade"
        else:
            price = self._finite_number(
                raw_last if raw_last is not None else ticker.get("price"),
                positive=True,
            )
            if exchange == "alpaca" and truth_status == "real_derived":
                price_kind = "derived_midpoint"
                price_source = "provider_quote_midpoint"
        source_timestamp = self._fresh_timestamp(
            ticker.get("source_timestamp")
            or ticker.get("provider_timestamp")
            or ticker.get("closeTime"),
            max_age_seconds=self.QUOTE_MAX_AGE_SECONDS,
            now=observed_now,
        )
        if (
            bid is None
            or ask is None
            or price is None
            or bid > ask
            or price < bid
            or price > ask
            or source_timestamp is None
        ):
            return self._no_data_receipt(
                "market_quote",
                "fresh_finite_two_sided_provider_quote_required",
                exchange=exchange,
                symbol=symbol,
            )
        source_id = str(
            ticker.get("source_id")
            or f"{exchange}:provider_ticker:{self._symbol_key(symbol)}"
        )
        midpoint = (bid + ask) / 2.0
        spread_fraction = (ask - bid) / midpoint
        spread_score = 1.0 / (1.0 + spread_fraction)
        if ask == bid:
            price_position = 1.0
        else:
            price_position = (price - bid) / (ask - bid)
        confidence = math.sqrt(spread_score * price_position)
        return {
            "kind": "market_quote",
            "status": "live",
            "data_status": "live",
            "truth_status": "real_derived",
            "exchange": exchange,
            "symbol": symbol,
            "source_id": source_id,
            "source_timestamp": source_timestamp,
            "received_at": observed_now,
            "bid": bid,
            "ask": ask,
            "price": price,
            "price_kind": price_kind,
            "price_source": price_source,
            "spread_fraction": spread_fraction,
            "price_position": price_position,
            "confidence": confidence,
            "confidence_formula": "sqrt((1/(1+spread_fraction))*price_position)",
            "generated_values": False,
            "action_eligible": True,
            "raw_receipt": dict(ticker),
        }

    def _scan_exchange_opportunities(
        self,
        exchange: str,
        client: Any,
        symbols: List[str],
    ) -> List[OrcaHunt]:
        if client is None:
            return []
        quote_currency = self._quote_asset(symbols[0]) if symbols else None
        if quote_currency is None:
            return []
        size_receipt = self.calculate_position_size(exchange, quote_currency)
        if size_receipt.get("action_eligible") is not True:
            return []
        size_usd = self._finite_number(size_receipt.get("size_usd"), positive=True)
        if size_usd is None:
            return []
        opportunities: List[OrcaHunt] = []
        reader_name = "get_ticker" if exchange == "alpaca" else "get_24h_ticker"
        reader = getattr(client, reader_name, None)
        if not callable(reader):
            return []
        for symbol in symbols:
            try:
                quote = self._normalize_quote_receipt(exchange, symbol, reader(symbol))
            except Exception as exc:
                logger.debug("%s quote read failed for %s: %s", exchange, symbol, type(exc).__name__)
                continue
            confidence = self._finite_number(quote.get("confidence"), nonnegative=True)
            if quote.get("action_eligible") is not True or confidence is None:
                continue
            if confidence < self.MIN_CONFIDENCE:
                continue
            entry = self._finite_number(quote.get("ask"), positive=True)
            if entry is None:
                continue
            target = entry * (1.0 + self.TAKE_PROFIT_PCT)
            stop = entry * (1.0 - self.STOP_LOSS_PCT)
            receipt = {
                **quote,
                "position_size_receipt": size_receipt,
                "risk_policy": {
                    "take_profit_fraction": self.TAKE_PROFIT_PCT,
                    "stop_loss_fraction": self.STOP_LOSS_PCT,
                },
            }
            opportunities.append(
                OrcaHunt(
                    symbol=symbol,
                    exchange=exchange,
                    direction="long",
                    confidence=confidence,
                    entry_price=entry,
                    target_price=target,
                    stop_price=stop,
                    size_usd=size_usd,
                    reasoning=[
                        f"Fresh provider quote: {quote['source_id']}",
                        f"Derived confidence: {quote['confidence_formula']}",
                    ],
                    timestamp=quote["source_timestamp"],
                    market_receipt=receipt,
                    action_eligible=True,
                    source_id=quote["source_id"],
                    source_timestamp=quote["source_timestamp"],
                    received_at=quote["received_at"],
                    truth_status="real_derived",
                    generated_values=False,
                )
            )
        return opportunities

    def scan_alpaca_opportunities(self) -> List[OrcaHunt]:
        """Scan Alpaca for hunting opportunities."""
        return self._scan_exchange_opportunities(
            "alpaca",
            self.alpaca,
            ["BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "AVAX/USD", "LINK/USD"],
        )

    def scan_binance_opportunities(self) -> List[OrcaHunt]:
        """Scan Binance for hunting opportunities."""
        return self._scan_exchange_opportunities(
            "binance",
            self.binance,
            ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"],
        )

    def scan_kraken_opportunities(self) -> List[OrcaHunt]:
        """Scan Kraken for hunting opportunities."""
        return self._scan_exchange_opportunities(
            "kraken",
            self.kraken,
            ["XBTUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD"],
        )
    
    def scan_all_markets(self) -> List[OrcaHunt]:
        """Scan all markets for opportunities."""
        all_opportunities = []
        
        # Scan each exchange
        all_opportunities.extend(self.scan_alpaca_opportunities())
        all_opportunities.extend(self.scan_binance_opportunities())
        all_opportunities.extend(self.scan_kraken_opportunities())
        
        # Sort by confidence
        all_opportunities.sort(key=lambda x: x.confidence, reverse=True)
        
        return all_opportunities
    
    def _pending_order_receipt(
        self,
        exchange: str,
        symbol: str,
        side: str,
        raw_receipt: Any,
        reason: str,
    ) -> Dict[str, Any]:
        raw = dict(raw_receipt) if isinstance(raw_receipt, dict) else {}
        provider_order_id = self._valid_provider_id(
            raw.get("provider_order_id") or raw.get("orderId") or raw.get("id")
        )
        return {
            "kind": "order_execution",
            "exchange": exchange,
            "symbol": symbol,
            "side": side,
            "status": "pending_reconciliation",
            "provider_status": raw.get("provider_status") or raw.get("status"),
            "data_status": "pending_reconciliation",
            "truth_status": "real_observed" if raw else "no_data",
            "reason": reason,
            "provider_order_id": provider_order_id,
            "source_id": (
                f"{exchange}:order:{provider_order_id}" if provider_order_id else None
            ),
            "source_timestamp": None,
            "received_at": time.time(),
            "filled_qty": None,
            "filled_avg_price": None,
            "filled_notional": None,
            "fee": None,
            "fee_currency": None,
            "trade_ids": [],
            "fill_receipt_complete": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "reconciliation_required": True,
            "generated_values": False,
            "raw_receipt": raw,
        }

    def _normalize_terminal_fill(
        self,
        exchange: str,
        receipt: Any,
        *,
        expected_symbol: str,
        expected_side: str,
        expected_quantity: float,
        now: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not isinstance(receipt, dict):
            return self._pending_order_receipt(
                exchange, expected_symbol, expected_side, receipt, "provider_order_receipt_required"
            )
        provider_order_id = self._valid_provider_id(
            receipt.get("provider_order_id") or receipt.get("orderId") or receipt.get("id")
        )
        provider_status = str(
            receipt.get("provider_status") or receipt.get("status") or ""
        ).strip().lower()
        if provider_order_id is None or provider_status != "filled":
            return self._pending_order_receipt(
                exchange,
                expected_symbol,
                expected_side,
                receipt,
                "fresh_terminal_provider_fill_required",
            )
        symbol = str(receipt.get("symbol") or "").strip()
        side = str(receipt.get("side") or "").strip().lower()
        filled_qty = self._finite_number(
            receipt.get("filled_qty")
            or receipt.get("filledQty")
            or receipt.get("executedQty"),
            positive=True,
        )
        filled_price = self._finite_number(
            receipt.get("filled_avg_price")
            or receipt.get("avg_fill_price")
            or receipt.get("avgPrice"),
            positive=True,
        )
        filled_notional = self._finite_number(
            receipt.get("filled_notional")
            or receipt.get("cummulativeQuoteQty"),
            positive=True,
        )
        source_timestamp = self._fresh_timestamp(
            receipt.get("source_timestamp")
            or receipt.get("provider_timestamp")
            or receipt.get("transactTime")
            or receipt.get("updateTime")
            or receipt.get("filled_at")
            or receipt.get("closedTime"),
            max_age_seconds=self.ORDER_MAX_AGE_SECONDS,
            now=now,
        )
        expected_qty = self._finite_number(expected_quantity, positive=True)
        provider_requested_qty = self._finite_number(
            receipt.get("requestedQty") or receipt.get("origQty"),
            positive=True,
        )
        if (
            not symbol
            or self._symbol_key(symbol) != self._symbol_key(expected_symbol)
            or side != expected_side
            or filled_qty is None
            or filled_price is None
            or filled_notional is None
            or source_timestamp is None
            or expected_qty is None
        ):
            return self._pending_order_receipt(
                exchange,
                expected_symbol,
                expected_side,
                receipt,
                "matching_fresh_fill_identity_quantity_price_and_notional_required",
            )
        validated_request_qty = provider_requested_qty or expected_qty
        request_tolerance = max(1e-12, expected_qty * 1e-2)
        qty_tolerance = max(1e-12, validated_request_qty * 1e-6)
        notional_tolerance = max(1e-8, filled_notional * 1e-3)
        if (
            validated_request_qty > expected_qty + request_tolerance
            or expected_qty - validated_request_qty > request_tolerance
            or abs(filled_qty - validated_request_qty) > qty_tolerance
            or abs((filled_qty * filled_price) - filled_notional) > notional_tolerance
        ):
            return self._pending_order_receipt(
                exchange,
                expected_symbol,
                expected_side,
                receipt,
                "provider_fill_totals_do_not_match_request",
            )

        raw_fills = receipt.get("fills")
        trade_ids: List[str] = []
        fill_fees: List[float] = []
        fill_currencies: set[str] = set()
        if isinstance(raw_fills, list):
            for raw_fill in raw_fills:
                if not isinstance(raw_fill, dict):
                    trade_ids = []
                    break
                trade_id = self._valid_provider_id(
                    raw_fill.get("trade_id")
                    or raw_fill.get("tradeId")
                    or raw_fill.get("id")
                )
                if trade_id is None or trade_id in trade_ids:
                    trade_ids = []
                    break
                trade_ids.append(trade_id)
                if "commission" in raw_fill:
                    commission = self._finite_number(raw_fill.get("commission"), nonnegative=True)
                    currency = str(
                        raw_fill.get("commissionAsset")
                        or raw_fill.get("fee_currency")
                        or ""
                    ).strip().upper()
                    if commission is None or not currency:
                        fill_fees = []
                        fill_currencies = set()
                        break
                    fill_fees.append(commission)
                    fill_currencies.add(currency)
        fee = self._finite_number(receipt.get("fee"), nonnegative=True)
        fee_currency = str(
            receipt.get("fee_currency") or receipt.get("fee_asset") or ""
        ).strip().upper()
        if (fee is None or not fee_currency) and trade_ids:
            if len(fill_fees) == len(trade_ids) and len(fill_currencies) == 1:
                fee = sum(fill_fees)
                fee_currency = next(iter(fill_currencies))
        truth_status = str(receipt.get("truth_status") or "real_observed").strip().lower()
        data_status = str(receipt.get("data_status") or "live").strip().lower()
        if (
            not trade_ids
            or fee is None
            or not fee_currency
            or truth_status not in {"real_observed", "real_derived"}
            or data_status != "live"
            or receipt.get("generated_values") is True
        ):
            return self._pending_order_receipt(
                exchange,
                expected_symbol,
                expected_side,
                receipt,
                "provider_trade_ids_fee_and_currency_receipts_required",
            )
        return {
            "kind": "order_execution",
            "exchange": exchange,
            "symbol": expected_symbol,
            "side": expected_side,
            "status": "FILLED",
            "provider_status": provider_status,
            "data_status": "live",
            "truth_status": "real_derived",
            "reason": "complete_fresh_terminal_provider_fill_receipt",
            "provider_order_id": provider_order_id,
            "source_id": str(
                receipt.get("source_id") or f"{exchange}:order:{provider_order_id}"
            ),
            "source_timestamp": source_timestamp,
            "received_at": time.time(),
            "filled_qty": filled_qty,
            "filled_avg_price": filled_price,
            "filled_notional": filled_notional,
            "fee": fee,
            "fee_currency": fee_currency,
            "trade_ids": trade_ids,
            "fill_receipt_complete": True,
            "eligible_for_accounting": True,
            "eligible_for_learning": True,
            "reconciliation_required": False,
            "generated_values": False,
            "raw_receipt": dict(receipt),
        }

    def _order_latch_key(self, exchange: str, symbol: str, side: str) -> str:
        return f"{exchange}:{self._symbol_key(symbol)}:{side.lower()}"

    def _reconcile_latched_order(
        self,
        latch_key: str,
        *,
        exchange: str,
        symbol: str,
        side: str,
        quantity: float,
    ) -> Dict[str, Any]:
        pending = self.pending_orders.get(latch_key)
        if not isinstance(pending, dict):
            return self._pending_order_receipt(
                exchange, symbol, side, None, "pending_order_receipt_required"
            )
        provider_order_id = self._valid_provider_id(pending.get("provider_order_id"))
        client = getattr(self, exchange, None)
        reader = None
        if exchange == "alpaca":
            reader = getattr(client, "get_order_with_fees", None)
        elif exchange == "kraken":
            reader = getattr(client, "get_order_status", None)
        elif exchange == "binance":
            reader = getattr(client, "get_order", None)
        if provider_order_id is None or not callable(reader):
            duplicate = dict(pending)
            duplicate["reason"] = "duplicate_submission_suppressed_pending_reconciliation"
            duplicate["received_at"] = time.time()
            return duplicate
        try:
            observed = reader(provider_order_id)
        except Exception as exc:
            duplicate = dict(pending)
            duplicate["reason"] = f"reconciliation_read_failed:{type(exc).__name__}"
            duplicate["received_at"] = time.time()
            return duplicate
        normalized = self._normalize_terminal_fill(
            exchange,
            observed,
            expected_symbol=symbol,
            expected_side=side,
            expected_quantity=quantity,
        )
        if normalized.get("fill_receipt_complete") is True:
            self.pending_orders.pop(latch_key, None)
        else:
            self.pending_orders[latch_key] = normalized
        self._save_state()
        return normalized

    def _record_entry_fill(self, fill: Dict[str, Any]) -> None:
        provider_order_id = self._valid_provider_id(fill.get("provider_order_id"))
        if provider_order_id is None or provider_order_id in self.accounted_order_ids:
            return
        symbol_key = self._symbol_key(fill.get("symbol"))
        self.entry_fill_receipts[symbol_key] = dict(fill)
        self.position_open_times[symbol_key] = float(fill["source_timestamp"])
        self.accounted_order_ids.add(provider_order_id)
        self.trades_this_hour += 1
        self.session_trades += 1
        self._save_state()

    def _hunt_action_receipt(self, hunt: OrcaHunt) -> Dict[str, Any]:
        market_receipt = hunt.market_receipt if isinstance(hunt.market_receipt, dict) else {}
        size_receipt = market_receipt.get("position_size_receipt")
        if not isinstance(size_receipt, dict):
            size_receipt = {}
        quote_currency = self._quote_asset(hunt.symbol)
        source_timestamp = self._fresh_timestamp(
            hunt.source_timestamp,
            max_age_seconds=self.QUOTE_MAX_AGE_SECONDS,
        )
        size = self._finite_number(hunt.size_usd, positive=True)
        receipt_size = self._finite_number(size_receipt.get("size_usd"), positive=True)
        entry = self._finite_number(hunt.entry_price, positive=True)
        if (
            hunt.action_eligible is not True
            or market_receipt.get("action_eligible") is not True
            or size_receipt.get("action_eligible") is not True
            or size_receipt.get("provider") != hunt.exchange
            or size_receipt.get("currency") != quote_currency
            or hunt.truth_status != "real_derived"
            or hunt.generated_values is not False
            or source_timestamp is None
            or size is None
            or receipt_size is None
            or abs(receipt_size - size) > max(1e-8, size * 1e-9)
            or entry is None
            or hunt.direction != "long"
        ):
            return self._no_data_receipt(
                "hunt_execution",
                "fresh_proof_carrying_long_hunt_required",
                symbol=hunt.symbol,
                exchange=hunt.exchange,
            )
        return {
            "kind": "hunt_execution",
            "status": "eligible",
            "data_status": "live",
            "truth_status": "real_derived",
            "source_id": hunt.source_id,
            "source_timestamp": source_timestamp,
            "received_at": time.time(),
            "size_usd": size,
            "entry_price": entry,
            "generated_values": False,
            "action_eligible": True,
        }

    def execute_hunt(self, hunt: OrcaHunt, dry_run: bool = True) -> Optional[Any]:
        """
        Execute a hunt (trade).
        
        Args:
            hunt: The hunting opportunity
            dry_run: If True, record intent only and never submit an order
        """
        can_trade, reason = self.can_trade()
        if not can_trade:
            logger.warning(f"🚫 Cannot trade: {reason}")
            return self._no_data_receipt("hunt_execution", reason)
        
        logger.info(f"🦈🔪 EXECUTING HUNT: {hunt.symbol} @ {hunt.exchange}")
        logger.info(f"   Direction: {hunt.direction.upper()}")
        logger.info(f"   Confidence: {hunt.confidence:.1%}")
        logger.info(f"   Size: ${hunt.size_usd:.2f}")
        logger.info(f"   Entry: ${hunt.entry_price:.4f}")
        logger.info(f"   Target: ${hunt.target_price:.4f}")
        logger.info(f"   Stop: ${hunt.stop_price:.4f}")
        
        if dry_run:
            logger.info("   🧪 DRY RUN - No real trade executed")
            receipt = {
                'status': 'not_submitted',
                'truth_status': 'dry_run',
                'provider_order_id': None,
                'fill': None,
                'actual_pnl': None,
                'eligible_for_learning': False,
                'generated_values': False,
                'symbol': hunt.symbol,
                'exchange': hunt.exchange,
                'direction': hunt.direction,
                'recorded_at': time.time(),
            }
            self.dry_run_attempts.append(receipt)
            return receipt

        action_receipt = self._hunt_action_receipt(hunt)
        if action_receipt.get("action_eligible") is not True:
            return action_receipt
        qty = hunt.size_usd / hunt.entry_price
        side = "buy"
        latch_key = self._order_latch_key(hunt.exchange, hunt.symbol, side)
        if latch_key in self.pending_orders:
            reconciled = self._reconcile_latched_order(
                latch_key,
                exchange=hunt.exchange,
                symbol=hunt.symbol,
                side=side,
                quantity=qty,
            )
            if reconciled.get("fill_receipt_complete") is True:
                self._record_entry_fill(reconciled)
            self.execution_receipts.append(reconciled)
            return reconciled

        order: Any = None
        try:
            if hunt.exchange == 'alpaca' and self.alpaca:
                order = self.alpaca.place_order(
                    symbol=hunt.symbol.replace('/', ''),
                    qty=qty,
                    side=side,
                    type='market',
                    time_in_force='gtc'
                )

            elif hunt.exchange == 'binance' and self.binance:
                order = self.binance.place_market_order(
                    symbol=hunt.symbol,
                    side=side,
                    quantity=qty
                )

            elif hunt.exchange == 'kraken' and self.kraken:
                order = self.kraken.place_market_order(
                    symbol=hunt.symbol,
                    side=side,
                    quantity=qty
                )
            else:
                return self._no_data_receipt(
                    "hunt_execution",
                    "requested_exchange_provider_unavailable",
                    exchange=hunt.exchange,
                    symbol=hunt.symbol,
                )
        
        except Exception as e:
            logger.error(f"❌ Execution error: {e}")
            pending = self._pending_order_receipt(
                hunt.exchange,
                hunt.symbol,
                side,
                order,
                f"provider_submission_outcome_unproven:{type(e).__name__}",
            )
            self.pending_orders[latch_key] = pending
            self.execution_receipts.append(pending)
            self._save_state()
            return pending

        normalized = self._normalize_terminal_fill(
            hunt.exchange,
            order,
            expected_symbol=hunt.symbol,
            expected_side=side,
            expected_quantity=qty,
        )
        if normalized.get("fill_receipt_complete") is True:
            self._record_entry_fill(normalized)
        else:
            self.pending_orders[latch_key] = normalized
            self._save_state()
            if hunt.exchange in {"alpaca", "kraken"}:
                normalized = self._reconcile_latched_order(
                    latch_key,
                    exchange=hunt.exchange,
                    symbol=hunt.symbol,
                    side=side,
                    quantity=qty,
                )
                if normalized.get("fill_receipt_complete") is True:
                    self._record_entry_fill(normalized)
        self.execution_receipts.append(normalized)
        return normalized
    
    def hunt_cycle(self, dry_run: bool = True) -> None:
        """Run one hunting cycle."""
        logger.info("🦈 Starting hunt cycle...")
        
        # 🔥 FIRST: Check existing positions and close if target/stop hit!
        if not dry_run:
            kills = self.check_and_close_positions()
            for kill in kills:
                self.completed_kills.append(kill)
                logger.info(f"💰 REALIZED GAIN: ${kill.pnl_usd:+.4f} ({kill.pnl_pct:+.2f}%)")
        
        # Check if we can trade
        can_trade, reason = self.can_trade()
        if not can_trade:
            logger.info(f"⏸️ {reason}")
            return
        
        # Scan for opportunities
        opportunities = self.scan_all_markets()
        
        if not opportunities:
            logger.info("🔍 No opportunities found (waiting for the perfect moment...)")
            return
        
        # Take the best opportunity above threshold
        best = opportunities[0]
        
        if best.confidence < self.MIN_CONFIDENCE:
            logger.info(f"🔍 Best opportunity ({best.confidence:.1%}) below threshold ({self.MIN_CONFIDENCE:.1%})")
            return
        
        logger.info(f"🎯 Found opportunity: {best.symbol} @ {best.confidence:.1%} confidence")
        
        # Execute!
        execution_result = self.execute_hunt(best, dry_run=dry_run)

        if isinstance(execution_result, OrcaKill):
            self.completed_kills.append(execution_result)
            logger.info(
                f"💰 KILL COMPLETE: ${execution_result.pnl_usd:+.2f} "
                f"({execution_result.pnl_pct:+.2f}%)"
            )
        elif isinstance(execution_result, dict) and execution_result.get('status') == 'not_submitted':
            logger.info("🧪 DRY RUN INTENT RECORDED - excluded from live kills and performance")
    
    def run(self, duration_minutes: int = 60, dry_run: bool = True, cycle_seconds: int = 30):
        """
        Run the Orca hunting session.
        
        Args:
            duration_minutes: How long to run
            dry_run: If True, record intents without provider submission
            cycle_seconds: Seconds between hunt cycles
        """
        self.start()
        print()
        print("🦈" * 30)
        print()
        print("    ⚡🔪 ORCA UNLEASHED - HUNTING SESSION 🔪⚡")
        print()
        print("🦈" * 30)
        print()
        
        if dry_run:
            print("    🧪 DRY RUN MODE - No real trades!")
        else:
            print("    🚨 LIVE MODE - Real money on the line!")
        
        print()
        self._log_status()
        
        end_time = time.time() + (duration_minutes * 60)
        cycles = 0
        
        try:
            while time.time() < end_time:
                cycles += 1
                logger.info(f"━━━ Cycle {cycles} ━━━")
                
                self.hunt_cycle(dry_run=dry_run)
                
                # Status every 5 cycles
                if cycles % 5 == 0:
                    self._log_status()
                
                # Wait for next cycle
                remaining = end_time - time.time()
                if remaining > cycle_seconds:
                    time.sleep(cycle_seconds)
                elif remaining > 0:
                    time.sleep(remaining)
        
        except KeyboardInterrupt:
            print("\n🛑 Hunt interrupted by user")
        
        # Final status
        print()
        print("🦈" * 30)
        print()
        print("    SESSION COMPLETE!")
        print()
        self._log_status()
        print("🦈" * 30)
        self.close()


def main():
    """Run the unleashed Orca!"""
    import argparse
    
    parser = argparse.ArgumentParser(description="🦈 ORCA UNLEASHED - The Killer Whale Hunts!")
    parser.add_argument("--live", action="store_true", help="Run in LIVE mode (real trades!)")
    parser.add_argument("--duration", type=int, default=60, help="Duration in minutes")
    parser.add_argument("--cycle", type=int, default=30, help="Seconds between cycles")
    parser.add_argument("--status", action="store_true", help="Just show status")
    parser.add_argument("--force", action="store_true", help="Skip confirmation (DANGEROUS!)")
    args = parser.parse_args()
    
    orca = OrcaUnleashed()
    
    if args.status:
        orca.start()
        orca._log_status()
        orca.close()
        return
    
    dry_run = not args.live
    
    if not dry_run and not args.force:
        print()
        print("🚨" * 20)
        print()
        print("    ⚠️  WARNING: LIVE TRADING MODE! ⚠️")
        print("    Real money will be used!")
        print()
        print("🚨" * 20)
        print()
        response = input("Type 'HUNT' to confirm: ")
        if response != 'HUNT':
            print("Aborted.")
            return
    
    if not dry_run:
        logger.info("🔴🔴🔴 LIVE MODE ACTIVATED - REAL MONEY! 🔴🔴🔴")
    
    orca.run(
        duration_minutes=args.duration,
        dry_run=dry_run,
        cycle_seconds=args.cycle
    )


if __name__ == "__main__":
    main()
