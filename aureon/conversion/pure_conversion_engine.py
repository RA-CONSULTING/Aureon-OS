#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                   ║
║   ██████╗ ██╗   ██╗██████╗ ███████╗     ██████╗ ██████╗ ███╗   ██╗██╗   ██╗      ║
║   ██╔══██╗██║   ██║██╔══██╗██╔════╝    ██╔════╝██╔═══██╗████╗  ██║██║   ██║      ║
║   ██████╔╝██║   ██║██████╔╝█████╗      ██║     ██║   ██║██╔██╗ ██║██║   ██║      ║
║   ██╔═══╝ ██║   ██║██╔══██╗██╔══╝      ██║     ██║   ██║██║╚██╗██║╚██╗ ██╔╝      ║
║   ██║     ╚██████╔╝██║  ██║███████╗    ╚██████╗╚██████╔╝██║ ╚████║ ╚████╔╝       ║
║   ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝     ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝  ╚═══╝        ║
║                                                                                   ║
║   🔄 PURE CONVERSION ENGINE - BARTER FOR BETTER 🔄                               ║
║                                                                                   ║
║   NOT BUYING. NOT SELLING. CONVERTING. BARTERING. SNOWBALLING.                   ║
║                                                                                   ║
║   PHILOSOPHY:                                                                     ║
║   • We don't sell assets - we CONVERT them to stronger positions                 ║
║   • We don't buy assets - we BARTER our holdings for better value                ║
║   • Every conversion increases our total buying power                            ║
║   • Compound, snowball, grow - adaptive asset accumulation                       ║
║                                                                                   ║
║   SYSTEMS UNIFIED:                                                                ║
║   • V14 Scoring (100% win rate logic)                                            ║
║   • Mycelium Network (distributed consensus)                                     ║
║   • Probability Matrix (7-day forecasting)                                       ║
║   • Adaptive Learning (pattern recognition)                                      ║
║   • Miner Brain (cognitive intelligence)                                         ║
║   • Quantum Telescope (multi-dimensional)                                        ║
║                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import asyncio
import signal
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import math

import logging
logger = logging.getLogger(__name__)


def _configured_price_max_age_seconds() -> float:
    try:
        value = float(os.getenv("AUREON_CONVERSION_PRICE_MAX_AGE_SECONDS", "120"))
    except (TypeError, ValueError):
        return 120.0
    return value if math.isfinite(value) and value > 0 else 120.0


CONVERSION_PRICE_MAX_AGE_SECONDS = _configured_price_max_age_seconds()


def _finite_number(value: Any, *, minimum: Optional[float] = None,
                   maximum: Optional[float] = None) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    if minimum is not None and numeric < minimum:
        return None
    if maximum is not None and numeric > maximum:
        return None
    return numeric


def _coerce_source_timestamp(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric = float(value)
        if not math.isfinite(numeric):
            return None
        if numeric > 10_000_000_000:
            numeric /= 1000.0
        try:
            parsed = datetime.fromtimestamp(numeric, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fresh_source_timestamp(value: Any) -> Optional[datetime]:
    parsed = _coerce_source_timestamp(value)
    if parsed is None:
        return None
    age = (datetime.now(timezone.utc) - parsed).total_seconds()
    if age < -5.0 or age > CONVERSION_PRICE_MAX_AGE_SECONDS:
        return None
    return parsed

try:
    import websockets
except ImportError:
    websockets = None  # Allow graceful degradation

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ═══════════════════════════════════════════════════════════════════════════════════
# IMPORT ALL SYSTEMS
# ═══════════════════════════════════════════════════════════════════════════════════

# V14 Scoring
try:
    from aureon.strategies.s5_v14_dance_enhancements import V14DanceEnhancer, V14_CONFIG, V14ScoringEngine
    V14_AVAILABLE = True
except ImportError:
    V14_AVAILABLE = False
    print("⚠️ V14 not available")

# Mycelium Network
try:
    from aureon.core.aureon_mycelium import MyceliumNetwork
    MYCELIUM_AVAILABLE = True
except ImportError:
    MYCELIUM_AVAILABLE = False

# Probability Matrix  
try:
    from aureon.strategies.hnc_probability_matrix import HNCProbabilityIntegration
    PROB_MATRIX_AVAILABLE = True
except ImportError:
    PROB_MATRIX_AVAILABLE = False

# Adaptive Learning
try:
    from aureon.trading.aureon_unified_ecosystem import AdaptiveLearner
    ADAPTIVE_AVAILABLE = True
except ImportError:
    ADAPTIVE_AVAILABLE = False

# Miner Brain
try:
    from aureon.utils.aureon_miner_brain import MinerBrain
    MINER_BRAIN_AVAILABLE = True
except ImportError:
    MINER_BRAIN_AVAILABLE = False

# Kraken Client
try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════════
# 🍄 MYCELIUM CONVERSION HUB - ALL SYSTEMS WIRED THROUGH ONE PLACE
# ═══════════════════════════════════════════════════════════════════════════════════
try:
    from aureon.conversion.mycelium_conversion_hub import (
        MyceliumConversionHub, get_conversion_hub,
        MyceliumSignal, ConversionSignal, SystemSignal
    )
    MYCELIUM_HUB_AVAILABLE = True
    print("🍄 Mycelium Conversion Hub LOADED - All systems wired!")
except ImportError as e:
    MYCELIUM_HUB_AVAILABLE = False
    print(f"⚠️ Mycelium Hub not available: {e}")

# Additional ecosystem systems
try:
    from aureon.simulation.aureon_internal_multiverse import InternalMultiverse
    MULTIVERSE_AVAILABLE = True
except ImportError:
    MULTIVERSE_AVAILABLE = False

try:
    from aureon.bridges.aureon_probability_nexus import EnhancedProbabilityNexus
    PROBABILITY_NEXUS_AVAILABLE = True
except ImportError:
    PROBABILITY_NEXUS_AVAILABLE = False

try:
    from aureon.harmonic.aureon_harmonic_fusion import HarmonicWaveFusion
    HARMONIC_AVAILABLE = True
except ImportError:
    HARMONIC_AVAILABLE = False

try:
    from aureon.analytics.aureon_lighthouse import AureonLighthouse
    LIGHTHOUSE_AVAILABLE = True
except ImportError:
    LIGHTHOUSE_AVAILABLE = False

try:
    from aureon.core.aureon_thought_bus import ThoughtBus, get_thought_bus
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False

try:
    from aureon.conversion.aureon_conversion_commando import AdaptiveConversionCommando
    CONVERSION_COMMANDO_AVAILABLE = True
except ImportError:
    CONVERSION_COMMANDO_AVAILABLE = False
except ImportError:
    KRAKEN_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════════
# CONVERSION PHILOSOPHY
# ═══════════════════════════════════════════════════════════════════════════════════

"""
THE PURE CONVERSION PHILOSOPHY:

1. NEVER SELL TO USD (unless converting to another asset)
2. ALWAYS CONVERT TO STRONGER POSITION
3. SNOWBALL - compound gains through conversions
4. ADAPTIVE - learn which conversions work best
5. PATIENCE - wait for the RIGHT conversion, not just any conversion

CONVERSION TYPES:
- STRENGTH SWAP: Asset A weakening → Convert to Asset B strengthening
- VALUE CAPTURE: Asset A up significantly → Lock in gains by converting
- DISCOUNT GRAB: Asset B down significantly → Convert TO it for discount
- ROTATION: Sector rotation - move to where momentum is going

THE KEY INSIGHT:
We're not trying to time the market.
We're trying to always be in the STRONGEST position.
Every conversion should increase our TOTAL BUYING POWER.
"""


class ConversionType(Enum):
    STRENGTH_SWAP = "strength_swap"      # Weak → Strong
    VALUE_CAPTURE = "value_capture"      # Lock in gains
    DISCOUNT_GRAB = "discount_grab"      # Buy the dip via conversion
    ROTATION = "rotation"                # Sector rotation
    SNOWBALL = "snowball"                # Compound small gains


@dataclass
class Asset:
    """An asset in our portfolio"""
    symbol: str
    amount: float
    avg_cost_usd: float = 0.0
    current_price: float = 0.0
    
    @property
    def usd_value(self) -> float:
        return self.amount * self.current_price
    
    @property
    def pnl_pct(self) -> float:
        if self.avg_cost_usd <= 0:
            return 0.0
        return ((self.current_price - self.avg_cost_usd) / self.avg_cost_usd) * 100


@dataclass
class ConversionOpportunity:
    """A potential conversion between assets"""
    from_asset: str
    to_asset: str
    conversion_type: ConversionType
    
    # Scores from all systems
    v14_score: int = 0
    mycelium_score: float = 0.0
    probability_score: float = 0.0
    adaptive_score: float = 0.0
    miner_score: float = 0.0
    
    # Combined
    unified_score: float = 0.0
    confidence: float = 0.0
    data_status: str = "no_data"
    no_data_reason: str = "unscored"
    proof_eligible: bool = False
    evidence: Dict[str, Any] = field(default_factory=dict)
    
    # Metrics
    from_momentum: float = 0.0
    to_momentum: float = 0.0
    relative_strength: float = 0.0
    expected_gain_pct: float = 0.0
    from_strength: float = 0.0
    to_strength: float = 0.0
    strength_diff: float = 0.0
    
    # Execution
    from_amount: float = 0.0
    to_amount: float = 0.0
    from_price: float = 0.0
    to_price: float = 0.0
    
    # Alias for compatibility
    @property
    def type(self):
        return self.conversion_type
    
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CompletedConversion:
    """A completed conversion"""
    id: str
    from_asset: str
    to_asset: str
    from_amount: float
    to_amount: float
    from_price: float
    to_price: float
    usd_value: float
    conversion_type: ConversionType
    unified_score: float
    timestamp: datetime
    
    # Track if this conversion was profitable
    to_price_at_check: float = 0.0
    realized_gain_pct: float = 0.0
    provider_receipt_id: Optional[str] = None
    source_timestamp: Optional[datetime] = None
    proof_eligible: bool = False


class UnifiedConversionBrain:
    """
    🧠 UNIFIED CONVERSION BRAIN 🧠
    
    ALL SYSTEMS NOW WIRED THROUGH MYCELIUM HUB!
    
    Combines ALL systems for conversion decisions:
    - V14: Technical scoring (100% win rate logic)
    - Mycelium Network: Distributed consensus
    - Internal Multiverse: 10-world consensus
    - Probability Nexus: Future price forecasting
    - Harmonic Systems: Wave alignment
    - Lighthouse: Pattern detection
    - Miner Brain: Cognitive intelligence
    - Conversion Commando: 1885 CAPM execution
    
    Every system flows through the Mycelium neural mesh.
    """
    
    def __init__(self, starting_capital: float = 10000.0):
        self.starting_capital = starting_capital
        
        # Initialize all systems
        print("\n🧠 Initializing Unified Conversion Brain...")
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🍄 MYCELIUM HUB - THE CENTRAL NERVOUS SYSTEM
        # ═══════════════════════════════════════════════════════════════════════
        self.mycelium_hub: Optional[MyceliumConversionHub] = None
        if MYCELIUM_HUB_AVAILABLE:
            self.mycelium_hub = get_conversion_hub(starting_capital)
            print("   🍄 Mycelium Hub: ALL SYSTEMS WIRED!")
        
        # ═══════════════════════════════════════════════════════════════════════
        # Individual systems (fallback if hub not available)
        # ═══════════════════════════════════════════════════════════════════════
        
        # V14 Scoring
        self.v14 = None
        if V14_AVAILABLE:
            self.v14 = V14DanceEnhancer()
            print("   ✅ V14 Scoring Engine (100% win rate logic)")
        
        # Mycelium Network
        self.mycelium = None
        if MYCELIUM_AVAILABLE:
            self.mycelium = MyceliumNetwork(initial_capital=starting_capital)
            print("   ✅ Mycelium Network (distributed consensus)")
        
        # Internal Multiverse
        self.multiverse = None
        if MULTIVERSE_AVAILABLE:
            try:
                self.multiverse = InternalMultiverse(initial_equity=starting_capital)
                print("   ✅ Internal Multiverse (10 worlds)")
            except:
                pass
        
        # Probability Nexus
        self.probability_nexus = None
        if PROBABILITY_NEXUS_AVAILABLE:
            try:
                self.probability_nexus = EnhancedProbabilityNexus(
                    exchange='binance', leverage=1.0, starting_balance=starting_capital
                )
                print("   ✅ Probability Nexus (80%+ win rate)")
            except:
                pass
        
        # Probability Matrix
        self.probability = None
        if PROB_MATRIX_AVAILABLE:
            try:
                self.probability = HNCProbabilityIntegration()
                print("   ✅ Probability Matrix (7-day forecasting)")
            except:
                pass
        
        # Harmonic Systems
        self.harmonic = None
        if HARMONIC_AVAILABLE:
            try:
                self.harmonic = HarmonicWaveFusion()
                print("   ✅ Harmonic Fusion (wave alignment)")
            except:
                pass
        
        # Lighthouse
        self.lighthouse = None
        if LIGHTHOUSE_AVAILABLE:
            try:
                self.lighthouse = AureonLighthouse()
                print("   ✅ Lighthouse (pattern detection)")
            except:
                pass
        
        # Miner Brain
        self.miner = None
        if MINER_BRAIN_AVAILABLE:
            try:
                self.miner = MinerBrain()
                print("   ✅ Miner Brain (cognitive intelligence)")
            except:
                pass
        
        # Conversion Commando
        self.commando = None
        if CONVERSION_COMMANDO_AVAILABLE:
            try:
                self.commando = AdaptiveConversionCommando()
                print("   ✅ Conversion Commando (1885 CAPM)")
            except:
                pass
        
        # Thought Bus for publishing
        self.thought_bus = None
        if THOUGHT_BUS_AVAILABLE:
            try:
                self.thought_bus = get_thought_bus()
                print("   ✅ Thought Bus (unity consciousness)")
            except:
                pass
        
        # Adaptive Learner
        self.adaptive = None
        if ADAPTIVE_AVAILABLE:
            try:
                self.adaptive = AdaptiveLearner()
                print("   ✅ Adaptive Learning (pattern recognition)")
            except:
                pass
        
        # Conversion history for learning
        self.conversion_history: List[CompletedConversion] = []
        self.successful_pairs: Dict[str, int] = defaultdict(int)  # pair -> success count
        
        print("   🧠 Unified Brain ONLINE!\n")
    
    def score_conversion(
        self,
        opp: ConversionOpportunity,
        prices: Dict[str, float],
        price_history: Dict[str, deque],
        price_timestamps: Optional[Dict[str, Any]] = None,
        volumes: Optional[Dict[str, float]] = None,
    ) -> ConversionOpportunity:
        """Score only a complete, fresh Mycelium evidence packet.

        The Mycelium hub is the conversion nervous system. If it is absent,
        errors, or returns incomplete evidence, the opportunity stays visible
        as no_data but cannot become executable or train adaptive pathways.
        """
        opp.unified_score = 0.0
        opp.confidence = 0.0
        opp.data_status = 'no_data'
        opp.no_data_reason = 'unscored'
        opp.proof_eligible = False
        opp.evidence = {}

        from_symbol = f"{opp.from_asset}USDT"
        to_symbol = f"{opp.to_asset}USDT"
        feed_from_price = _finite_number(prices.get(from_symbol), minimum=0.000000000001)
        feed_to_price = _finite_number(prices.get(to_symbol), minimum=0.000000000001)
        clean_from_price = _finite_number(opp.from_price, minimum=0.000000000001)
        clean_to_price = _finite_number(opp.to_price, minimum=0.000000000001)
        if (
            feed_from_price is None
            or feed_to_price is None
            or clean_from_price is None
            or clean_to_price is None
            or not math.isclose(feed_from_price, clean_from_price, rel_tol=1e-12)
            or not math.isclose(feed_to_price, clean_to_price, rel_tol=1e-12)
        ):
            opp.no_data_reason = 'missing_or_malformed_provider_price'
            return opp

        timestamps = price_timestamps or {}
        from_observed_at = _fresh_source_timestamp(timestamps.get(from_symbol))
        to_observed_at = _fresh_source_timestamp(timestamps.get(to_symbol))
        if from_observed_at is None or to_observed_at is None:
            opp.no_data_reason = 'missing_or_stale_provider_timestamp'
            return opp

        if not self.mycelium_hub:
            opp.no_data_reason = 'mycelium_hub_unavailable'
            return opp

        clean_volumes = volumes or {}
        try:
            hub_signal = self.mycelium_hub.get_conversion_signal(
                from_asset=opp.from_asset,
                to_asset=opp.to_asset,
                from_price=clean_from_price,
                to_price=clean_to_price,
                from_source_timestamp=from_observed_at,
                to_source_timestamp=to_observed_at,
                from_volume=clean_volumes.get(from_symbol),
                to_volume=clean_volumes.get(to_symbol),
            )
        except Exception as exc:
            logger.warning("Mycelium Hub evidence error: %s", exc)
            opp.no_data_reason = 'mycelium_hub_error'
            return opp

        if (
            getattr(hub_signal, 'data_status', 'no_data') != 'ok'
            or not getattr(hub_signal, 'proof_eligible', False)
        ):
            opp.no_data_reason = str(
                getattr(hub_signal, 'no_data_reason', 'incomplete_mycelium_evidence')
            )
            return opp

        unified_score = _finite_number(
            getattr(hub_signal, 'unified_score', None), minimum=0.0, maximum=1.0
        )
        confidence = _finite_number(
            getattr(hub_signal, 'unified_confidence', None), minimum=0.0, maximum=1.0
        )
        if unified_score is None or confidence is None:
            opp.no_data_reason = 'malformed_mycelium_score'
            return opp

        opp.unified_score = unified_score
        opp.confidence = confidence
        opp.data_status = 'ok'
        opp.no_data_reason = ''
        opp.proof_eligible = True
        opp.evidence = {
            'from_price_source_timestamp': from_observed_at.isoformat(),
            'to_price_source_timestamp': to_observed_at.isoformat(),
            'mycelium_source_timestamps': dict(
                getattr(hub_signal, 'source_timestamps', {})
            ),
            'participating_systems': list(
                getattr(hub_signal, 'participating_systems', [])
            ),
        }

        if hub_signal.v14_signal:
            opp.v14_score = int(hub_signal.v14_signal.score)
        if hub_signal.mycelium_signal:
            opp.mycelium_score = hub_signal.mycelium_signal.confidence
        if hub_signal.probability_signal:
            opp.probability_score = hub_signal.probability_signal.confidence
        if hub_signal.miner_signal:
            opp.miner_score = hub_signal.miner_signal.confidence

        return opp

    def record_conversion(
        self,
        conversion: CompletedConversion,
        was_profitable: bool,
    ) -> bool:
        """Learn only from a fresh provider-proven conversion outcome."""
        if (
            not isinstance(was_profitable, bool)
            or not conversion.proof_eligible
            or not conversion.provider_receipt_id
            or _fresh_source_timestamp(conversion.source_timestamp) is None
            or _finite_number(conversion.realized_gain_pct) is None
        ):
            return False
        self.conversion_history.append(conversion)
        
        pair_key = f"{conversion.from_asset}→{conversion.to_asset}"
        if was_profitable:
            self.successful_pairs[pair_key] += 1
        return True


class PureConversionEngine:
    """
    🔄 PURE CONVERSION ENGINE 🔄
    
    NOT BUYING. NOT SELLING. CONVERTING. BARTERING. SNOWBALLING.
    
    Core Strategy:
    1. Monitor all assets for relative strength changes
    2. When Asset A weakens relative to Asset B → Convert A to B
    3. Compound gains through strategic conversions
    4. Snowball - each conversion increases total buying power
    """
    
    # Binance WebSocket
    WS_URL = "wss://stream.binance.com:9443/stream?streams="
    
    # Asset universe - what we can convert between
    UNIVERSE = {
        # Majors
        'BTC': {'binance': 'BTCUSDT', 'kraken': 'XBTUSD', 'tier': 1},
        'ETH': {'binance': 'ETHUSDT', 'kraken': 'ETHUSD', 'tier': 1},
        
        # Large caps
        'SOL': {'binance': 'SOLUSDT', 'kraken': 'SOLUSD', 'tier': 2},
        'XRP': {'binance': 'XRPUSDT', 'kraken': 'XRPUSD', 'tier': 2},
        'ADA': {'binance': 'ADAUSDT', 'kraken': 'ADAUSD', 'tier': 2},
        'AVAX': {'binance': 'AVAXUSDT', 'kraken': 'AVAXUSD', 'tier': 2},
        'DOT': {'binance': 'DOTUSDT', 'kraken': 'DOTUSD', 'tier': 2},
        'LINK': {'binance': 'LINKUSDT', 'kraken': 'LINKUSD', 'tier': 2},
        
        # Mid caps
        'ATOM': {'binance': 'ATOMUSDT', 'kraken': 'ATOMUSD', 'tier': 3},
        'NEAR': {'binance': 'NEARUSDT', 'kraken': 'NEARUSD', 'tier': 3},
        'UNI': {'binance': 'UNIUSDT', 'kraken': 'UNIUSD', 'tier': 3},
        'LTC': {'binance': 'LTCUSDT', 'kraken': 'LTCUSD', 'tier': 3},
        'MATIC': {'binance': 'MATICUSDT', 'kraken': 'MATICUSD', 'tier': 3},
        'APT': {'binance': 'APTUSDT', 'kraken': 'APTUSD', 'tier': 3},
        'ARB': {'binance': 'ARBUSDT', 'kraken': 'ARBUSD', 'tier': 3},
        'OP': {'binance': 'OPUSDT', 'kraken': 'OPUSD', 'tier': 3},
        
        # Small caps (higher risk, higher reward)
        'DOGE': {'binance': 'DOGEUSDT', 'kraken': 'DOGEUSD', 'tier': 4},
        'SHIB': {'binance': 'SHIBUSDT', 'kraken': 'SHIBUSD', 'tier': 4},
        'PEPE': {'binance': 'PEPEUSDT', 'kraken': 'PEPEUSD', 'tier': 4},
    }
    
    # Conversion thresholds
    MIN_CONVERSION_USD = 10.0
    MAX_CONVERSION_PCT = 0.30  # Max 30% of holdings per conversion
    CONVERSION_COOLDOWN = 60   # Seconds between conversions
    
    # Relative strength thresholds
    MIN_STRENGTH_DIFF = 0.02   # 2% relative strength difference to trigger
    MIN_UNIFIED_SCORE = 0.60   # Minimum unified score to convert
    
    # Kraken fees
    TAKER_FEE = 0.0026
    
    def __init__(self, starting_capital: float = 10000.0, dry_run: bool = False):
        self.starting_capital = starting_capital
        self.dry_run = dry_run
        
        # Unified brain
        self.brain = UnifiedConversionBrain(starting_capital)
        
        # Kraken client
        if KRAKEN_AVAILABLE and not dry_run:
            self.kraken = get_kraken_client()
        else:
            self.kraken = None
        
        # Portfolio
        self.portfolio: Dict[str, Asset] = {}
        self.initial_portfolio_value = 0.0
        
        # Price tracking
        self.prices: Dict[str, float] = {}
        self.volumes: Dict[str, float] = {}
        self.price_source_timestamps: Dict[str, datetime] = {}
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self.momentum: Dict[str, float] = {}  # 5-min momentum
        self.strength: Dict[str, float] = {}  # Relative strength vs BTC
        
        # Conversions
        self.pending_conversions: List[ConversionOpportunity] = []
        self.completed_conversions: List[CompletedConversion] = []
        self.conversion_counter = 0
        self.last_conversion_time = datetime.now() - timedelta(hours=1)
        
        # State
        self.running = False
        self.start_time = None
        self.ws_connected = False
        
        # Stats
        self.stats = {
            'price_updates': 0,
            'opportunities_found': 0,
            'conversions_executed': 0,
            'total_converted_usd': 0.0,
            'snowball_gain_pct': 0.0,
        }
        
        # Signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print("\n\n🛑 Stopping Pure Conversion Engine...")
        self.running = False
    
    def banner(self):
        """Display startup banner"""
        mode = "DRY RUN" if self.dry_run else "🔴 LIVE CONVERSIONS"
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ██████╗ ██╗   ██╗██████╗ ███████╗     ██████╗ ██████╗ ███╗   ██╗██╗   ██╗   ║
║   ██╔══██╗██║   ██║██╔══██╗██╔════╝    ██╔════╝██╔═══██╗████╗  ██║██║   ██║   ║
║   ██████╔╝██║   ██║██████╔╝█████╗      ██║     ██║   ██║██╔██╗ ██║██║   ██║   ║
║   ██╔═══╝ ██║   ██║██╔══██╗██╔══╝      ██║     ██║   ██║██║╚██╗██║╚██╗ ██╔╝   ║
║   ██║     ╚██████╔╝██║  ██║███████╗    ╚██████╗╚██████╔╝██║ ╚████║ ╚████╔╝    ║
║   ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝     ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝  ╚═══╝     ║
║                                                                               ║
║      🔄 BARTER FOR BETTER - SNOWBALL YOUR ASSETS 🔄                           ║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║   PHILOSOPHY: NOT BUYING. NOT SELLING. CONVERTING.                            ║
║                                                                               ║
║   • Convert WEAK assets → STRONG assets                                       ║
║   • Snowball gains through strategic bartering                                ║
║   • Every conversion increases total buying power                             ║
║   • Unified brain: V14 + Mycelium + Probability + Adaptive                    ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║   MODE: {mode:<60}        ║
║   Min Score: {self.MIN_UNIFIED_SCORE:.0%} | Min Strength Diff: {self.MIN_STRENGTH_DIFF:.0%}                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
""")
    
    def load_portfolio(self) -> bool:
        """Load current portfolio"""
        print("\n   📊 Loading portfolio...")
        
        if self.dry_run or not self.kraken:
            print("      ⚠️ no_data - provider portfolio receipt unavailable")
            return False
        else:
            try:
                balance = self.kraken.get_account_balance()
                if not balance:
                    return False
                
                for asset, amount in balance.items():
                    if amount > 0.0001:
                        # Clean asset name
                        clean = asset.replace('X', '').replace('Z', '')
                        if clean == 'XBT':
                            clean = 'BTC'
                        
                        if clean in self.UNIVERSE:
                            self.portfolio[clean] = Asset(clean, amount, 0, 0)
                            print(f"         {clean}: {amount:.4f}")
            except Exception as e:
                print(f"      ❌ Error: {e}")
                return False
        
        # Calculate initial value
        self._update_portfolio_values()
        self.initial_portfolio_value = self._get_total_value()
        print(f"\n      💰 Total Portfolio: ${self.initial_portfolio_value:.2f}")
        
        return len(self.portfolio) > 0
    
    def _update_portfolio_values(self):
        """Update portfolio USD values from current prices"""
        for asset in self.portfolio.values():
            binance_sym = self.UNIVERSE.get(asset.symbol, {}).get('binance')
            if binance_sym and binance_sym in self.prices:
                asset.current_price = self.prices[binance_sym]
    
    def _get_total_value(self) -> float:
        """Get total portfolio USD value"""
        return sum(a.usd_value for a in self.portfolio.values())
    
    async def _fetch_initial_prices(self):
        """Fetch initial prices"""
        print("\n   📡 Fetching initial prices...")
        
        try:
            response = requests.get('https://api.binance.com/api/v3/ticker/24hr', timeout=10)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                raise ValueError("Binance ticker response is not a list")
            
            symbols = {v['binance'] for v in self.UNIVERSE.values()}
            
            for ticker in data:
                if not isinstance(ticker, dict):
                    continue
                required = {'symbol', 'lastPrice', 'volume', 'closeTime'}
                if not required.issubset(ticker):
                    continue
                symbol = ticker['symbol']
                if symbol in symbols:
                    price = _finite_number(ticker['lastPrice'], minimum=0.000000000001)
                    volume = _finite_number(ticker['volume'], minimum=0.0)
                    observed_at = _fresh_source_timestamp(ticker['closeTime'])
                    if price is None or volume is None or observed_at is None:
                        continue
                    self.prices[symbol] = price
                    self.volumes[symbol] = volume
                    self.price_source_timestamps[symbol] = observed_at
                    self.price_history[symbol].append({
                        'price': price,
                        'volume': volume,
                        'source_time': observed_at,
                        'received_at': datetime.now(timezone.utc),
                    })
                    
                    # Update V14 scoring
                    if self.brain.v14:
                        self.brain.v14.scoring_engine.update_price_history(
                            symbol, price, volume
                        )
            
            print(f"      ✅ Loaded {len(self.prices)} prices")
            self._update_portfolio_values()
            
        except Exception as e:
            print(f"      ⚠️ Error: {e}")
    
    async def _price_feed(self):
        """WebSocket price feed"""
        symbols = [v['binance'].lower() for v in self.UNIVERSE.values()]
        streams = [f"{s}@ticker" for s in symbols]
        url = self.WS_URL + "/".join(streams)
        
        print(f"\n   🌐 Connecting to price feed...")
        
        while self.running:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    self.ws_connected = True
                    print(f"      ✅ Connected!")
                    
                    async for message in ws:
                        if not self.running:
                            break
                        
                        try:
                            data = json.loads(message)
                            if 'data' in data:
                                ticker = data['data']
                                if not isinstance(ticker, dict):
                                    continue
                                required = {'s', 'c', 'v', 'E'}
                                if not required.issubset(ticker):
                                    continue
                                symbol = ticker['s']
                                price = _finite_number(
                                    ticker['c'], minimum=0.000000000001
                                )
                                volume = _finite_number(ticker['v'], minimum=0.0)
                                observed_at = _fresh_source_timestamp(ticker['E'])
                                
                                if (
                                    symbol in {v['binance'] for v in self.UNIVERSE.values()}
                                    and price is not None
                                    and volume is not None
                                    and observed_at is not None
                                ):
                                    self.prices[symbol] = price
                                    self.volumes[symbol] = volume
                                    self.price_source_timestamps[symbol] = observed_at
                                    self.price_history[symbol].append({
                                        'price': price,
                                        'volume': volume,
                                        'source_time': observed_at,
                                        'received_at': datetime.now(timezone.utc),
                                    })
                                    
                                    # Update V14
                                    if self.brain.v14:
                                        self.brain.v14.scoring_engine.update_price_history(
                                            symbol, price, volume
                                        )
                                    
                                    self.stats['price_updates'] += 1
                                    
                                    # Update momentum & strength
                                    self._update_momentum(symbol)
                                    self._update_relative_strength()
                                    
                                    # Check for conversion opportunities
                                    await self._check_conversions()
                                    
                        except:
                            pass
                            
            except Exception as e:
                self.ws_connected = False
                if self.running:
                    await asyncio.sleep(5)
    
    def _update_momentum(self, symbol: str):
        """Calculate 5-minute momentum"""
        history = list(self.price_history[symbol])
        if len(history) < 10:
            self.momentum.pop(symbol, None)
            return
        
        five_min_ago = []
        for observation in history:
            if not isinstance(observation, dict):
                continue
            observed_at = _fresh_source_timestamp(observation.get('source_time'))
            price = _finite_number(
                observation.get('price'), minimum=0.000000000001
            )
            if observed_at is not None and price is not None:
                five_min_ago.append((observed_at, price))
        
        if len(five_min_ago) >= 2:
            five_min_ago.sort(key=lambda item: item[0])
            old_price = five_min_ago[0][1]
            new_price = five_min_ago[-1][1]
            self.momentum[symbol] = (new_price - old_price) / old_price
        else:
            self.momentum.pop(symbol, None)
    
    def _update_relative_strength(self):
        """Update relative strength vs BTC"""
        btc_momentum = self.momentum.get('BTCUSDT')
        if btc_momentum is None:
            self.strength.clear()
            return
        
        for asset, info in self.UNIVERSE.items():
            symbol = info['binance']
            if symbol in self.momentum:
                # Relative strength = asset momentum - BTC momentum
                self.strength[asset] = self.momentum[symbol] - btc_momentum
            else:
                self.strength.pop(asset, None)
    
    async def find_conversion_opportunities(self) -> List[ConversionOpportunity]:
        """Find all conversion opportunities (for display/testing)"""
        
        # Fetch initial prices if not loaded
        if not self.prices:
            await self._fetch_initial_prices()
        
        # Calculate momentum and strength for all assets
        self._calculate_all_metrics()
        
        opportunities = []
        
        for from_asset in list(self.portfolio.keys()):
            if from_asset not in self.UNIVERSE or from_asset not in self.strength:
                continue
            from_strength = self.strength[from_asset]
            
            for to_asset, info in self.UNIVERSE.items():
                if to_asset == from_asset:
                    continue
                if to_asset not in self.strength:
                    continue
                
                to_strength = self.strength[to_asset]
                strength_diff = to_strength - from_strength
                
                # Only consider if TO asset is stronger
                if strength_diff < self.MIN_STRENGTH_DIFF * 0.5:  # Lower threshold for finding opps
                    continue
                
                # Determine conversion type
                if strength_diff > 0.05:
                    conv_type = ConversionType.STRENGTH_SWAP
                elif from_strength > 0.02:
                    conv_type = ConversionType.VALUE_CAPTURE
                elif to_strength < -0.02:
                    conv_type = ConversionType.DISCOUNT_GRAB
                else:
                    conv_type = ConversionType.SNOWBALL
                
                # Create opportunity
                from_symbol = self.UNIVERSE.get(from_asset, {}).get('binance', f'{from_asset}USDT')
                to_symbol = self.UNIVERSE.get(to_asset, {}).get('binance', f'{to_asset}USDT')
                from_price = _finite_number(
                    self.prices.get(from_symbol), minimum=0.000000000001
                )
                to_price = _finite_number(
                    self.prices.get(to_symbol), minimum=0.000000000001
                )
                if (
                    from_price is None
                    or to_price is None
                    or _fresh_source_timestamp(
                        self.price_source_timestamps.get(from_symbol)
                    )
                    is None
                    or _fresh_source_timestamp(
                        self.price_source_timestamps.get(to_symbol)
                    )
                    is None
                ):
                    continue
                
                opp = ConversionOpportunity(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    conversion_type=conv_type,
                    from_momentum=self.momentum[from_symbol],
                    to_momentum=self.momentum[to_symbol],
                    relative_strength=strength_diff,
                    from_price=from_price,
                    to_price=to_price,
                    from_strength=from_strength,
                    to_strength=to_strength,
                    strength_diff=strength_diff,
                )
                
                # Score with unified brain
                opp = self.brain.score_conversion(
                    opp,
                    self.prices,
                    self.price_history,
                    self.price_source_timestamps,
                    self.volumes,
                )
                
                if (
                    opp.data_status == 'ok'
                    and opp.proof_eligible
                    and opp.unified_score >= self.MIN_UNIFIED_SCORE * 0.5
                ):
                    opportunities.append(opp)
        
        # Sort by unified score
        opportunities.sort(key=lambda x: x.unified_score, reverse=True)
        return opportunities
    
    def _calculate_all_metrics(self):
        """Calculate momentum and strength for all assets.

        Derives momentum only from the rolling delta of provider-observed
        prices. Missing history clears the value so stale or invented
        momentum cannot influence conversion routing.
        """
        for asset, info in self.UNIVERSE.items():
            symbol = info['binance']
            if (
                symbol in self.prices
                and _fresh_source_timestamp(
                    getattr(self, 'price_source_timestamps', {}).get(symbol)
                )
                is not None
            ):
                history = getattr(self, "price_history", {}).get(symbol)
                clean_history = []
                for observation in history or ():
                    if not isinstance(observation, dict):
                        continue
                    observed_at = _fresh_source_timestamp(observation.get('source_time'))
                    price = _finite_number(
                        observation.get('price'), minimum=0.000000000001
                    )
                    if observed_at is not None and price is not None:
                        clean_history.append((observed_at, price))
                if len(clean_history) >= 2:
                    clean_history.sort(key=lambda item: item[0])
                    first, last = clean_history[0][1], clean_history[-1][1]
                    self.momentum[symbol] = (last - first) / first
                    continue
            self.momentum.pop(symbol, None)
        
        # Update relative strength
        btc_momentum = self.momentum.get('BTCUSDT')
        if btc_momentum is None:
            self.strength.clear()
            return
        
        for asset, info in self.UNIVERSE.items():
            symbol = info['binance']
            if symbol in self.momentum:
                self.strength[asset] = self.momentum[symbol] - btc_momentum
            else:
                self.strength.pop(asset, None)
    
    async def _check_conversions(self):
        """Check for conversion opportunities"""
        
        # Cooldown check
        elapsed = (datetime.now() - self.last_conversion_time).total_seconds()
        if elapsed < self.CONVERSION_COOLDOWN:
            return
        
        # Update portfolio values
        self._update_portfolio_values()
        
        # Find best conversion opportunity
        best_opp = None
        best_score = 0
        
        for from_asset in self.portfolio:
            if self.portfolio[from_asset].usd_value < self.MIN_CONVERSION_USD:
                continue
            
            if from_asset not in self.strength:
                continue
            from_strength = self.strength[from_asset]
            
            for to_asset, info in self.UNIVERSE.items():
                if to_asset == from_asset:
                    continue
                if to_asset in self.portfolio and self.portfolio[to_asset].usd_value > 1000:
                    continue  # Don't over-concentrate
                
                if to_asset not in self.strength:
                    continue
                to_strength = self.strength[to_asset]
                strength_diff = to_strength - from_strength
                
                # Only consider if TO asset is significantly stronger
                if strength_diff < self.MIN_STRENGTH_DIFF:
                    continue
                
                # Determine conversion type
                if strength_diff > 0.05:
                    conv_type = ConversionType.STRENGTH_SWAP
                elif from_strength > 0.02:
                    conv_type = ConversionType.VALUE_CAPTURE
                elif to_strength < -0.02:
                    conv_type = ConversionType.DISCOUNT_GRAB
                else:
                    conv_type = ConversionType.SNOWBALL
                
                # Create opportunity
                from_symbol = self.UNIVERSE[from_asset]['binance']
                to_symbol = self.UNIVERSE[to_asset]['binance']
                from_price = _finite_number(
                    self.prices.get(from_symbol), minimum=0.000000000001
                )
                to_price = _finite_number(
                    self.prices.get(to_symbol), minimum=0.000000000001
                )
                if (
                    from_price is None
                    or to_price is None
                    or _fresh_source_timestamp(
                        self.price_source_timestamps.get(from_symbol)
                    )
                    is None
                    or _fresh_source_timestamp(
                        self.price_source_timestamps.get(to_symbol)
                    )
                    is None
                ):
                    continue
                
                opp = ConversionOpportunity(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    conversion_type=conv_type,
                    from_momentum=self.momentum[from_symbol],
                    to_momentum=self.momentum[to_symbol],
                    relative_strength=strength_diff,
                    from_price=from_price,
                    to_price=to_price,
                )
                
                # Score with unified brain
                opp = self.brain.score_conversion(
                    opp,
                    self.prices,
                    self.price_history,
                    self.price_source_timestamps,
                    self.volumes,
                )
                
                if (
                    opp.data_status == 'ok'
                    and opp.proof_eligible
                    and opp.unified_score >= self.MIN_UNIFIED_SCORE
                    and opp.unified_score > best_score
                ):
                    best_opp = opp
                    best_score = opp.unified_score
        
        if best_opp:
            self.stats['opportunities_found'] += 1
            await self._execute_conversion(best_opp)
    
    async def _execute_conversion(self, opp: ConversionOpportunity) -> bool:
        """Execute only a complete, provider-proven conversion opportunity."""
        if opp.data_status != 'ok' or not opp.proof_eligible:
            logger.warning(
                "Conversion blocked: %s",
                opp.no_data_reason or 'unproven_conversion_evidence',
            )
            return False
        if self.dry_run:
            logger.info("Dry run: conversion was not submitted and state was not mutated")
            return False
        
        from_holding = self.portfolio.get(opp.from_asset)
        if not from_holding:
            return False
        if (
            _finite_number(opp.from_price, minimum=0.000000000001) is None
            or _finite_number(opp.to_price, minimum=0.000000000001) is None
            or _finite_number(from_holding.amount, minimum=0.000000000001) is None
        ):
            return False
        
        # Calculate amounts
        convert_pct = min(self.MAX_CONVERSION_PCT, 0.15 + opp.unified_score * 0.15)
        opp.from_amount = from_holding.amount * convert_pct
        opp.to_amount = (opp.from_amount * opp.from_price / opp.to_price) * (1 - self.TAKER_FEE * 2)
        
        usd_value = opp.from_amount * opp.from_price
        if usd_value < self.MIN_CONVERSION_USD:
            return False
        
        opp.reason = f"{opp.conversion_type.value}: {opp.from_asset}→{opp.to_asset} (str diff: {opp.relative_strength:.2%})"
        
        # Execute (sell FROM, buy TO)
        if not self.dry_run and self.kraken:
            try:
                # Sell FROM asset
                from_pair = self.UNIVERSE[opp.from_asset]['kraken']
                sell_result = self.kraken.place_market_order(from_pair, 'sell', opp.from_amount)
                
                if not sell_result:
                    print(f"\n   ⚠️ Sell failed")
                    return False
                
                # Buy TO asset
                to_pair = self.UNIVERSE[opp.to_asset]['kraken']
                buy_result = self.kraken.place_market_order(to_pair, 'buy', opp.to_amount)
                
                if not buy_result:
                    print(f"\n   ⚠️ Buy failed")
                    return False

                def receipt_is_filled(receipt: Any) -> bool:
                    if not isinstance(receipt, dict) or receipt.get('error'):
                        return False
                    order_id = receipt.get('orderId')
                    executed = _finite_number(
                        receipt.get('executedQty'), minimum=0.000000000001
                    )
                    observed_at = _fresh_source_timestamp(receipt.get('transactTime'))
                    return bool(
                        order_id
                        and str(order_id).lower() != 'unknown'
                        and receipt.get('status') == 'FILLED'
                        and executed is not None
                        and observed_at is not None
                    )

                if not receipt_is_filled(sell_result) or not receipt_is_filled(buy_result):
                    logger.error("Conversion blocked from local accounting: malformed fill receipt")
                    return False
                    
            except Exception as e:
                print(f"\n   ❌ Conversion error: {e}")
                return False
        else:
            return False
        
        # Update portfolio
        from_holding.amount -= opp.from_amount
        
        if opp.to_asset not in self.portfolio:
            self.portfolio[opp.to_asset] = Asset(opp.to_asset, 0, opp.to_price, opp.to_price)
        self.portfolio[opp.to_asset].amount += opp.to_amount
        self.portfolio[opp.to_asset].current_price = opp.to_price
        
        # Record conversion
        self.conversion_counter += 1
        conv_id = f"CONV-{self.conversion_counter:04d}"
        
        completed = CompletedConversion(
            id=conv_id,
            from_asset=opp.from_asset,
            to_asset=opp.to_asset,
            from_amount=opp.from_amount,
            to_amount=opp.to_amount,
            from_price=opp.from_price,
            to_price=opp.to_price,
            usd_value=usd_value,
            conversion_type=opp.conversion_type,
            unified_score=opp.unified_score,
            timestamp=datetime.now(),
            provider_receipt_id=(
                f"{sell_result['orderId']}:{buy_result['orderId']}"
            ),
            source_timestamp=min(
                _coerce_source_timestamp(sell_result['transactTime']),
                _coerce_source_timestamp(buy_result['transactTime']),
            ),
            proof_eligible=True,
        )
        self.completed_conversions.append(completed)
        
        # Update stats
        self.stats['conversions_executed'] += 1
        self.stats['total_converted_usd'] += usd_value
        self.last_conversion_time = datetime.now()
        
        # Calculate snowball
        current_value = self._get_total_value()
        self.stats['snowball_gain_pct'] = ((current_value - self.initial_portfolio_value) / 
                                           self.initial_portfolio_value * 100)
        
        # Display
        mode = "(DRY)" if self.dry_run else ""
        print(f"\n   🔄 CONVERSION {mode}: {conv_id}")
        print(f"      {opp.from_amount:.4f} {opp.from_asset} → {opp.to_amount:.4f} {opp.to_asset}")
        print(f"      Type: {opp.conversion_type.value} | Score: {opp.unified_score:.2f}")
        print(f"      V14: {opp.v14_score} | Mycelium: {opp.mycelium_score:.2f} | Prob: {opp.probability_score:.2f}")
        print(f"      USD Value: ${usd_value:.2f} | Snowball: {self.stats['snowball_gain_pct']:+.2f}%")
        return True
    
    async def _display_loop(self):
        """Display stats"""
        while self.running:
            await asyncio.sleep(5)
            self._display_stats()
    
    def _display_stats(self):
        """Display current stats"""
        if not self.start_time:
            return
        
        elapsed = time.time() - self.start_time
        current_value = self._get_total_value()
        snowball = self.stats['snowball_gain_pct']
        
        # Portfolio summary
        portfolio_str = " ".join([f"{a}:{v.usd_value:.0f}" for a, v in 
                                  sorted(self.portfolio.items(), key=lambda x: -x[1].usd_value)[:4]])
        
        print(f"\r   ⏱️ {elapsed:.0f}s | "
              f"📡 {self.stats['price_updates']:,} | "
              f"🔄 {self.stats['conversions_executed']} convs | "
              f"💰 ${current_value:.2f} | "
              f"❄️ {snowball:+.2f}% snowball | "
              f"[{portfolio_str}]",
              end='', flush=True)
    
    def _final_report(self):
        """Final report"""
        if not self.start_time:
            return
        
        elapsed = time.time() - self.start_time
        final_value = self._get_total_value()
        gain_pct = ((final_value - self.initial_portfolio_value) / self.initial_portfolio_value * 100)
        
        print("\n\n" + "═"*80)
        print("🔄 PURE CONVERSION SESSION REPORT")
        print("═"*80)
        
        print(f"\n⏱️ SESSION")
        print(f"   Runtime: {elapsed:.1f}s ({elapsed/3600:.2f} hours)")
        print(f"   Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        
        print(f"\n🔄 CONVERSIONS")
        print(f"   Executed: {self.stats['conversions_executed']}")
        print(f"   Total USD Converted: ${self.stats['total_converted_usd']:.2f}")
        
        print(f"\n💰 PORTFOLIO")
        print(f"   Initial Value: ${self.initial_portfolio_value:.2f}")
        print(f"   Final Value: ${final_value:.2f}")
        print(f"   ❄️ SNOWBALL GAIN: {gain_pct:+.2f}%")
        
        print(f"\n📊 HOLDINGS")
        for asset, holding in sorted(self.portfolio.items(), key=lambda x: -x[1].usd_value):
            if holding.usd_value > 1:
                print(f"   {asset}: {holding.amount:.4f} (${holding.usd_value:.2f})")
        
        if self.completed_conversions:
            print(f"\n📝 RECENT CONVERSIONS")
            for conv in self.completed_conversions[-5:]:
                print(f"   {conv.id}: {conv.from_asset}→{conv.to_asset} ${conv.usd_value:.2f} ({conv.conversion_type.value})")
        
        print("\n" + "═"*80)
        print("🔄 PURE CONVERSION: BARTER FOR BETTER - SNOWBALL YOUR ASSETS 🔄")
        print("═"*80 + "\n")
    
    async def run(self):
        """Main run loop"""
        self.banner()

        await self._fetch_initial_prices()
        if not self.prices:
            print("\n   ❌ no_data - no fresh provider prices")
            return
        
        if not self.load_portfolio():
            print("\n   ❌ No portfolio to convert!")
            return
        
        if not self.dry_run:
            print("\n" + "═"*70)
            print("⚠️  LIVE PURE CONVERSION MODE ⚠️")
            print("═"*70)
            print("\n   This will execute REAL conversions between your assets.")
            print("   Philosophy: NOT buying or selling. BARTERING for better positions.")
            
            confirm = input("\n   Type 'BARTER' to start: ")
            if confirm != 'BARTER':
                print("\n   Aborted.")
                return
        
        print("\n🔄🔄🔄 PURE CONVERSION ENGINE ACTIVATED! 🔄🔄🔄\n")
        
        self.running = True
        self.start_time = time.time()
        
        try:
            await asyncio.gather(
                self._price_feed(),
                self._display_loop(),
            )
        except asyncio.CancelledError:
            pass
        finally:
            self._final_report()


async def main():
    """Entry point"""
    import argparse
    parser = argparse.ArgumentParser(description='Pure Conversion Engine')
    parser.add_argument('--dry-run', action='store_true', help='Run without real trades')
    parser.add_argument('--capital', type=float, default=10000.0, help='Starting capital')
    args = parser.parse_args()
    
    print("\n🔄🔄🔄 PURE CONVERSION ENGINE 🔄🔄🔄")
    print("   BARTER FOR BETTER - SNOWBALL YOUR ASSETS")
    print("   Press Ctrl+C to stop\n")
    
    engine = PureConversionEngine(
        starting_capital=args.capital,
        dry_run=args.dry_run
    )
    await engine.run()


if __name__ == "__main__":
    asyncio.run(main())
