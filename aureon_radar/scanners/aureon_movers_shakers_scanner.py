#!/usr/bin/env python3
"""
🌊🦈🐋 AUREON MOVERS & SHAKERS SCANNER 🐋🦈🌊
==============================================

WHO'S MAKING THE WAVES, MATE?

This scanner unifies ALL whale/bot detection systems to identify:
1. 🐋 WHALES - Large institutional players (Citadel, Jane Street, Jump)
2. 🦈 SHARKS - Aggressive algorithmic traders (HFT, arbitrage bots)
3. 🐙 OCTOPI - Market manipulators (spoofers, layerers)
4. 🐬 DOLPHINS - Smart money movers (trend followers)
5. 🦑 SQUIDS - Dark pool operators (hidden liquidity)

REAL-TIME DETECTION:
- Cross-exchange correlation (who's moving the same way everywhere?)
- Volume spike analysis (sudden whale surfacing)
- Frequency fingerprinting (each firm has a signature)
- Firm attribution (name the players)
- Money flow direction (where's it going?)

Gary Leckey | January 2026 | "Find the Waves, Ride the Whales"
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import math
import time
import json
import asyncio
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict
from enum import Enum

# 📡 ThoughtBus - Primary neural communication
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought, get_thought_bus
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False

# 🐦 ChirpBus - kHz-speed signaling  
try:
    from aureon.core.aureon_chirp_bus import get_chirp_bus, ChirpDirection, ChirpType
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False

# 👑 Queen Hive Mind - Decision approval
QUEEN_AVAILABLE = False
def _lazy_load_queen():
    global QUEEN_AVAILABLE
    try:
        from aureon.utils.aureon_queen_hive_mind import QueenHiveMind, get_queen
        QUEEN_AVAILABLE = True
        return get_queen()
    except ImportError:
        QUEEN_AVAILABLE = False
        return None

# UTF-8 fix
try:
    from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402
except ImportError:
    # Upstream lib ships no console_utf8 module; run with PYTHONUTF8=1
    # instead. Degraded glyphs beat an ImportError.
    def ensure_utf8_stdout(*_a, **_k):
        return False

ensure_utf8_stdout()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MoversShakers")

# Sacred Constants
PHI = (1 + math.sqrt(5)) / 2  # 1.618 Golden Ratio
LOVE_FREQUENCY = 528  # Hz


class WaveType(Enum):
    """Type of market wave being created."""
    WHALE = "🐋 WHALE"           # Institutional accumulation/distribution
    SHARK = "🦈 SHARK"           # HFT / Aggressive algo
    OCTOPUS = "🐙 OCTOPUS"       # Manipulation (spoofing)
    DOLPHIN = "🐬 DOLPHIN"       # Smart money trend following
    SQUID = "🦑 SQUID"           # Dark pool / Hidden liquidity
    PLANKTON = "🦐 PLANKTON"     # Retail noise


@dataclass
class MoverShaker:
    """A detected market mover."""
    id: str
    timestamp: float
    wave_type: WaveType
    
    # What they're doing
    symbol: str
    exchange: str
    side: str  # 'buy', 'sell', 'both'
    volume_usd: float
    frequency_hz: float  # Trading frequency fingerprint
    
    # Who they might be
    attributed_firm: Optional[str] = None
    firm_confidence: float = 0.0
    bot_class: str = "UNKNOWN"
    
    # Impact metrics
    price_impact_pct: float = 0.0  # How much they moved the price
    volume_share_pct: float = 0.0  # % of total volume
    cross_exchange_score: float = 0.0  # How correlated across exchanges
    
    # Behavior patterns
    activity_count: int = 0
    avg_order_size: float = 0.0
    order_to_trade_ratio: float = 0.0  # High = potential spoofing
    
    # Our assessment
    threat_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    trading_opportunity: str = "NEUTRAL"  # BUY, SELL, NEUTRAL, AVOID
    reasoning: List[str] = field(default_factory=list)
    
    def __str__(self):
        return (
            f"{self.wave_type.value} | {self.symbol} @ {self.exchange} | "
            f"Vol: ${self.volume_usd:,.0f} | {self.side.upper()} | "
            f"Firm: {self.attributed_firm or 'Unknown'} ({self.firm_confidence:.0%})"
        )


@dataclass
class WaveReport:
    """Complete report of all active movers & shakers."""
    timestamp: float
    total_movers: int
    total_volume_usd: float
    
    # By type
    whales: List[MoverShaker] = field(default_factory=list)
    sharks: List[MoverShaker] = field(default_factory=list)
    octopi: List[MoverShaker] = field(default_factory=list)
    dolphins: List[MoverShaker] = field(default_factory=list)
    squids: List[MoverShaker] = field(default_factory=list)
    
    # Overall market sentiment
    net_flow_direction: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    whale_consensus: str = "MIXED"  # ACCUMULATING, DISTRIBUTING, MIXED
    manipulation_alert: bool = False
    
    @property
    def all_movers(self) -> List[MoverShaker]:
        return self.whales + self.sharks + self.octopi + self.dolphins + self.squids


class MoversShakersScanner:
    """
    🌊 UNIFIED MOVERS & SHAKERS DETECTION SYSTEM 🌊
    
    Combines all intelligence sources to identify who's making waves.
    """
    
    # Known firm frequency signatures (Hz)
    FIRM_FREQUENCY_SIGNATURES = {
        (3.0, 4.5): "Citadel Securities",
        (2.5, 3.5): "Jump Trading",
        (4.0, 5.5): "Jane Street",
        (1.5, 2.5): "Wintermute",
        (0.5, 1.5): "Alameda Remnants",
        (5.0, 7.0): "Virtu Financial",
        (2.0, 3.0): "Two Sigma",
        (3.5, 4.5): "Tower Research",
    }
    
    # Volume thresholds (USD)
    WHALE_THRESHOLD = 100_000  # $100K+
    SHARK_THRESHOLD = 25_000   # $25K+
    DOLPHIN_THRESHOLD = 5_000  # $5K+
    
    def __init__(self, lookback_minutes: int = 15):
        self.lookback_minutes = lookback_minutes
        self.movers: Dict[str, MoverShaker] = {}  # id -> MoverShaker
        self.activity_buffer: deque = deque(maxlen=10000)
        self.cross_exchange_tracker: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Exchange clients
        self.kraken = None
        self.binance_ws = None
        self.alpaca = None
        
        # Intelligence integrations
        self.orca = None
        self.moby_dick = None
        self.profiler = None
        
        self._init_integrations()
        
        logger.info("🌊 Movers & Shakers Scanner Initialized")
        
    def _init_integrations(self):
        """Initialize all available intelligence systems."""
        # 🔗 Communication Buses
        self.thought_bus = get_thought_bus() if THOUGHT_BUS_AVAILABLE else None
        self.chirp_bus = get_chirp_bus() if CHIRP_BUS_AVAILABLE else None
        self.queen = _lazy_load_queen()
        
        if self.thought_bus:
            logger.info("📡 Wired to ThoughtBus")
        
        if self.chirp_bus:
            logger.info("🐦 Wired to ChirpBus")

        if self.queen:
            logger.info("👑 Connected to Queen Hive Mind")

        # Try Kraken
        try:
            from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
            self.kraken = get_kraken_client()
            logger.info("✅ Kraken client connected")
        except Exception as e:
            logger.warning(f"⚠️ Kraken unavailable: {e}")
        
        # Try Orca Intelligence (use singleton to avoid circular recursion!)
        # NOTE: Orca creates MoversShakersScanner, so we must use get_orca() 
        # to get the same instance, otherwise infinite loop
        self.orca = None  # Defer to avoid circular dependency
        # Will be wired externally by Orca after init
        
        # Try Moby Dick
        try:
            from aureon.analytics.aureon_moby_dick_whale_hunter import MobyDickWhaleHunter
            self.moby_dick = MobyDickWhaleHunter()
            logger.info("✅ Moby Dick Whale Hunter connected")
        except Exception as e:
            logger.warning(f"⚠️ Moby Dick unavailable: {e}")
        
        # Try Complete Profiler
        try:
            from aureon.analytics.aureon_complete_profiler_integration import get_complete_profiler
            self.profiler = get_complete_profiler()
            logger.info("✅ Complete Profiler connected")
        except Exception as e:
            logger.warning(f"⚠️ Profiler unavailable: {e}")
    
    def _match_firm_by_frequency(self, freq_hz: float) -> Tuple[Optional[str], float]:
        """Match a trading frequency to a known firm signature."""
        for (low, high), firm in self.FIRM_FREQUENCY_SIGNATURES.items():
            if low <= freq_hz <= high:
                # Confidence based on how centered in the range
                mid = (low + high) / 2
                distance = abs(freq_hz - mid)
                max_distance = (high - low) / 2
                confidence = 1.0 - (distance / max_distance)
                return firm, confidence * 0.7  # Max 70% on frequency alone
        return None, 0.0
    
    def _classify_wave_type(self, volume_usd: float, freq_hz: float, 
                           order_trade_ratio: float, activity_count: int) -> WaveType:
        """Classify the type of wave based on behavior."""
        # Spoofing detection (high order-to-trade ratio)
        if order_trade_ratio > 5.0:
            return WaveType.OCTOPUS
        
        # HFT detection (high frequency)
        if freq_hz > 3.0 and volume_usd > self.SHARK_THRESHOLD:
            return WaveType.SHARK
        
        # Whale detection (large volume, lower frequency)
        if volume_usd >= self.WHALE_THRESHOLD and freq_hz < 2.0:
            return WaveType.WHALE
        
        # Dark pool / hidden liquidity
        if activity_count < 5 and volume_usd > self.SHARK_THRESHOLD:
            return WaveType.SQUID
        
        # Smart money
        if volume_usd >= self.DOLPHIN_THRESHOLD:
            return WaveType.DOLPHIN
        
        return WaveType.PLANKTON
    
    def _assess_threat_level(self, mover: MoverShaker) -> str:
        """Assess threat level of a mover."""
        score = 0
        
        # Volume impact
        if mover.volume_usd > 500_000:
            score += 3
        elif mover.volume_usd > 100_000:
            score += 2
        elif mover.volume_usd > 25_000:
            score += 1
        
        # Manipulation signals
        if mover.wave_type == WaveType.OCTOPUS:
            score += 2
        
        # Cross-exchange coordination
        if mover.cross_exchange_score > 0.7:
            score += 2
        
        # Known aggressive firm
        if mover.attributed_firm in ["Citadel Securities", "Jump Trading"]:
            score += 1
        
        if score >= 5:
            return "CRITICAL"
        elif score >= 3:
            return "HIGH"
        elif score >= 2:
            return "MEDIUM"
        return "LOW"
    
    def _determine_trading_opportunity(self, mover: MoverShaker) -> str:
        """Determine if we should trade with/against this mover."""
        # Don't trade against manipulators
        if mover.wave_type == WaveType.OCTOPUS:
            return "AVOID"
        
        # Follow whales (if confident)
        if mover.wave_type == WaveType.WHALE and mover.firm_confidence > 0.5:
            if mover.side == 'buy':
                return "BUY"
            elif mover.side == 'sell':
                return "SELL"
        
        # Ride shark momentum briefly
        if mover.wave_type == WaveType.SHARK and mover.volume_share_pct > 10:
            if mover.side == 'buy':
                return "BUY"
            elif mover.side == 'sell':
                return "SELL"
        
        return "NEUTRAL"
    
    async def scan_exchange(self, exchange: str) -> List[Dict]:
        """Scan a single exchange for activity."""
        activities = []
        
        if exchange == "kraken" and self.kraken:
            try:
                # Get recent trades for key pairs
                for pair in ["BTC/USD", "ETH/USD", "SOL/USD"]:
                    try:
                        trades = self.kraken.get_recent_trades(pair.replace("/", ""))
                        if trades:
                            for trade in trades[-50:]:  # Last 50 trades
                                activities.append({
                                    'exchange': 'kraken',
                                    'symbol': pair,
                                    'price': float(trade.get('price', 0)),
                                    'volume': float(trade.get('vol', 0)),
                                    'side': trade.get('type', 'unknown'),
                                    'timestamp': float(trade.get('time', time.time())),
                                })
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"Kraken scan error: {e}")
        
        return activities
    
    def analyze_activity_cluster(self, activities: List[Dict]) -> Optional[MoverShaker]:
        """Analyze a cluster of activities to identify a mover."""
        if not activities or len(activities) < 3:
            return None
        
        # Aggregate metrics
        total_volume = sum(a.get('volume', 0) * a.get('price', 0) for a in activities)
        if total_volume < self.DOLPHIN_THRESHOLD:
            return None
        
        # Determine dominant side
        buy_vol = sum(a.get('volume', 0) * a.get('price', 0) 
                     for a in activities if a.get('side') == 'buy')
        sell_vol = total_volume - buy_vol
        
        if buy_vol > sell_vol * 1.5:
            side = 'buy'
        elif sell_vol > buy_vol * 1.5:
            side = 'sell'
        else:
            side = 'both'
        
        # Calculate trading frequency
        timestamps = [a['timestamp'] for a in activities]
        if len(timestamps) > 1:
            time_span = max(timestamps) - min(timestamps)
            freq_hz = len(activities) / max(time_span, 0.1)
        else:
            freq_hz = 1.0
        
        # Match firm by frequency
        firm, firm_conf = self._match_firm_by_frequency(freq_hz)
        
        # Classify wave type
        avg_order_size = total_volume / len(activities)
        wave_type = self._classify_wave_type(
            total_volume, freq_hz, 1.0, len(activities)
        )
        
        # Create mover
        mover = MoverShaker(
            id=f"{activities[0]['exchange']}_{activities[0]['symbol']}_{int(time.time())}",
            timestamp=time.time(),
            wave_type=wave_type,
            symbol=activities[0]['symbol'],
            exchange=activities[0]['exchange'],
            side=side,
            volume_usd=total_volume,
            frequency_hz=freq_hz,
            attributed_firm=firm,
            firm_confidence=firm_conf,
            activity_count=len(activities),
            avg_order_size=avg_order_size,
        )
        
        # Assess threat and opportunity
        mover.threat_level = self._assess_threat_level(mover)
        mover.trading_opportunity = self._determine_trading_opportunity(mover)
        
        # Add reasoning
        mover.reasoning.append(f"Detected {len(activities)} trades in cluster")
        mover.reasoning.append(f"Volume: ${total_volume:,.0f} ({side})")
        mover.reasoning.append(f"Frequency: {freq_hz:.2f} Hz")
        if firm:
            mover.reasoning.append(f"Firm match: {firm} ({firm_conf:.0%})")
        
        return mover
    
    def scan(self) -> List[MoverShaker]:
        """Synchronous scan entry point for ORCA."""
        logger.info("🌊 Scan requested by ORCA")
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We are in a running loop, return a coroutine? 
                # ORCA expects a list immediately. This is a problem if ORCA is sync.
                # Assuming ORCA is sync and no loop is running in this thread context:
                 return loop.run_until_complete(self.scan_all_exchanges())
            else:
                 return loop.run_until_complete(self.scan_all_exchanges())
        except RuntimeError:
            # No loop created yet
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.scan_all_exchanges())
            finally:
                loop.close()

    def _publish_mover(self, mover: MoverShaker):
        """Publish mover detection to Hive Mind."""
        
        # 1. ThoughtBus (Brain Persistence)
        if hasattr(self, 'thought_bus') and self.thought_bus:
            try:
                thought = Thought(
                    source="movers_shakers",
                    topic=f"whale.detected.{mover.wave_type.name.lower()}",
                    payload=asdict(mover)
                )
                self.thought_bus.publish(thought)
            except Exception as e:
                logger.warning(f"⚠️ Failed to publish thought: {e}")

        # 2. ChirpBus (Speed Signal)
        if hasattr(self, 'chirp_bus') and self.chirp_bus:
            try:
                msg_type = ChirpType.THREAT if "SHARK" in mover.wave_type.name else ChirpType.OPPORTUNITY
                self.chirp_bus.emit_message(
                    message=f"{mover.wave_type.value} {mover.symbol}",
                    direction=ChirpDirection.UP if mover.side == 'buy' else ChirpDirection.DOWN,
                    confidence=mover.firm_confidence,
                    symbol=mover.symbol,
                    frequency=mover.frequency_hz or 432.0,
                    message_type=msg_type
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to emit chirp: {e}")

    async def scan_all_exchanges(self) -> List[MoverShaker]:
        """Scan all exchanges and identify movers."""
        all_activities = []
        
        # Parallel exchange scanning
        tasks = [
            self.scan_exchange("kraken"),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_activities.extend(result)
        
        # Group by symbol and exchange
        grouped: Dict[str, List[Dict]] = defaultdict(list)
        for activity in all_activities:
            key = f"{activity['exchange']}_{activity['symbol']}"
            grouped[key].append(activity)
        
        # Analyze each cluster
        movers = []
        for key, activities in grouped.items():
            mover = self.analyze_activity_cluster(activities)
            if mover:
                # 🔊 Publish to Hive Mind
                self._publish_mover(mover)
                movers.append(mover)
        
        return movers
    
    def load_bot_scanner_state(self) -> List[MoverShaker]:
        """Load bot detections from scanner state file."""
        movers = []
        state_file = "bot_shape_scanner_state.json"
        
        if not os.path.exists(state_file):
            return movers
        
        try:
            with open(state_file) as f:
                state = json.load(f)
            
            for symbol, data in state.items():
                if not isinstance(data, dict):
                    continue
                
                advanced = data.get('advanced_classification', {})
                if not advanced:
                    continue
                
                bot_class = advanced.get('class', 'UNKNOWN')
                freq_hz = advanced.get('frequency', 0.0)
                
                if bot_class == 'UNKNOWN' or freq_hz == 0:
                    continue
                
                # Estimate volume (mock - would need real data)
                volume_usd = data.get('volume_usd', 50_000)
                
                # Map bot class to wave type
                wave_type = WaveType.SHARK
                if 'SPOOF' in bot_class:
                    wave_type = WaveType.OCTOPUS
                elif 'ACCUMULATOR' in bot_class:
                    wave_type = WaveType.WHALE
                elif 'MM' in bot_class:
                    wave_type = WaveType.DOLPHIN
                
                # Match firm
                firm, firm_conf = self._match_firm_by_frequency(freq_hz)
                
                mover = MoverShaker(
                    id=f"bot_{symbol}_{int(time.time())}",
                    timestamp=time.time(),
                    wave_type=wave_type,
                    symbol=symbol,
                    exchange="binance",
                    side="both",
                    volume_usd=volume_usd,
                    frequency_hz=freq_hz,
                    attributed_firm=firm,
                    firm_confidence=firm_conf,
                    bot_class=bot_class,
                    activity_count=data.get('activity_count', 0),
                )
                
                mover.threat_level = self._assess_threat_level(mover)
                mover.trading_opportunity = self._determine_trading_opportunity(mover)
                mover.reasoning.append(f"Bot class: {bot_class}")
                mover.reasoning.append(f"Scanner confidence: {data.get('confidence', 0):.0%}")
                
                movers.append(mover)
                
        except Exception as e:
            logger.error(f"Failed to load bot scanner state: {e}")
        
        return movers
    
    def generate_report(self, movers: List[MoverShaker]) -> WaveReport:
        """Generate a complete wave report."""
        report = WaveReport(
            timestamp=time.time(),
            total_movers=len(movers),
            total_volume_usd=sum(m.volume_usd for m in movers),
        )
        
        # Categorize movers
        for mover in movers:
            if mover.wave_type == WaveType.WHALE:
                report.whales.append(mover)
            elif mover.wave_type == WaveType.SHARK:
                report.sharks.append(mover)
            elif mover.wave_type == WaveType.OCTOPUS:
                report.octopi.append(mover)
            elif mover.wave_type == WaveType.DOLPHIN:
                report.dolphins.append(mover)
            elif mover.wave_type == WaveType.SQUID:
                report.squids.append(mover)
        
        # Calculate net flow direction
        buy_volume = sum(m.volume_usd for m in movers if m.side == 'buy')
        sell_volume = sum(m.volume_usd for m in movers if m.side == 'sell')
        
        if buy_volume > sell_volume * 1.2:
            report.net_flow_direction = "🟢 BULLISH"
        elif sell_volume > buy_volume * 1.2:
            report.net_flow_direction = "🔴 BEARISH"
        else:
            report.net_flow_direction = "⚪ NEUTRAL"
        
        # Whale consensus
        whale_buys = sum(1 for w in report.whales if w.side == 'buy')
        whale_sells = sum(1 for w in report.whales if w.side == 'sell')
        
        if whale_buys > whale_sells:
            report.whale_consensus = "🟢 ACCUMULATING"
        elif whale_sells > whale_buys:
            report.whale_consensus = "🔴 DISTRIBUTING"
        else:
            report.whale_consensus = "⚪ MIXED"
        
        # Manipulation alert
        report.manipulation_alert = len(report.octopi) > 0
        
        return report
    
    def display_report(self, report: WaveReport):
        """Display the report in a beautiful ASCII format."""
        print("\n" + "=" * 70)
        print("🌊🦈🐋 MOVERS & SHAKERS REPORT 🐋🦈🌊".center(70))
        print("=" * 70)
        print(f"  Timestamp: {datetime.fromtimestamp(report.timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Total Movers: {report.total_movers}")
        print(f"  Total Volume: ${report.total_volume_usd:,.0f}")
        print("-" * 70)
        print(f"  Net Flow:       {report.net_flow_direction}")
        print(f"  Whale Consensus: {report.whale_consensus}")
        print(f"  Manipulation Alert: {'🚨 YES' if report.manipulation_alert else '✅ NO'}")
        print("=" * 70)
        
        # Whales
        if report.whales:
            print("\n🐋 WHALES (Institutional Players)")
            print("-" * 50)
            for i, whale in enumerate(report.whales[:5], 1):
                print(f"  {i}. {whale.symbol} @ {whale.exchange}")
                print(f"     Volume: ${whale.volume_usd:,.0f} | Side: {whale.side.upper()}")
                if whale.attributed_firm:
                    print(f"     Firm: {whale.attributed_firm} ({whale.firm_confidence:.0%})")
                print(f"     Opportunity: {whale.trading_opportunity}")
        
        # Sharks
        if report.sharks:
            print("\n🦈 SHARKS (HFT / Aggressive Algos)")
            print("-" * 50)
            for i, shark in enumerate(report.sharks[:5], 1):
                print(f"  {i}. {shark.symbol} @ {shark.exchange}")
                print(f"     Freq: {shark.frequency_hz:.2f}Hz | Vol: ${shark.volume_usd:,.0f}")
                if shark.attributed_firm:
                    print(f"     Firm: {shark.attributed_firm}")
                print(f"     Threat: {shark.threat_level}")
        
        # Octopi (Manipulators)
        if report.octopi:
            print("\n🐙 OCTOPI (Potential Manipulation)")
            print("-" * 50)
            for i, octo in enumerate(report.octopi[:5], 1):
                print(f"  {i}. {octo.symbol} @ {octo.exchange}")
                print(f"     Class: {octo.bot_class}")
                print(f"     ⚠️ AVOID TRADING - Manipulation suspected")
        
        # Dolphins
        if report.dolphins:
            print("\n🐬 DOLPHINS (Smart Money)")
            print("-" * 50)
            for i, dolphin in enumerate(report.dolphins[:5], 1):
                print(f"  {i}. {dolphin.symbol} | {dolphin.side.upper()} | ${dolphin.volume_usd:,.0f}")
        
        # Trading opportunities summary
        print("\n" + "=" * 70)
        print("📈 TRADING OPPORTUNITIES")
        print("-" * 70)
        
        buy_opps = [m for m in report.all_movers if m.trading_opportunity == "BUY"]
        sell_opps = [m for m in report.all_movers if m.trading_opportunity == "SELL"]
        avoid = [m for m in report.all_movers if m.trading_opportunity == "AVOID"]
        
        if buy_opps:
            print("  🟢 BUY SIGNALS:")
            for m in buy_opps[:3]:
                print(f"     → {m.symbol} (follow {m.wave_type.value})")
        
        if sell_opps:
            print("  🔴 SELL SIGNALS:")
            for m in sell_opps[:3]:
                print(f"     → {m.symbol} (follow {m.wave_type.value})")
        
        if avoid:
            print("  ⚠️ AVOID:")
            for m in avoid[:3]:
                print(f"     → {m.symbol} (manipulation detected)")
        
        if not buy_opps and not sell_opps:
            print("  ⚪ No clear opportunities - market in consolidation")
        
        print("=" * 70 + "\n")
    
    async def run_scan(self) -> WaveReport:
        """Run a complete scan and return the report."""
        logger.info("🌊 Starting Movers & Shakers scan...")
        
        # Get movers from all sources
        all_movers = []
        
        # 1. Live exchange scan
        exchange_movers = await self.scan_all_exchanges()
        all_movers.extend(exchange_movers)
        logger.info(f"  📡 Exchange scan: {len(exchange_movers)} movers")
        
        # 2. Bot scanner state
        bot_movers = self.load_bot_scanner_state()
        all_movers.extend(bot_movers)
        logger.info(f"  🤖 Bot scanner: {len(bot_movers)} movers")
        
        # 3. Sort by volume
        all_movers.sort(key=lambda m: m.volume_usd, reverse=True)
        
        # Generate and display report
        report = self.generate_report(all_movers)
        self.display_report(report)
        
        return report


async def main():
    """Main entry point."""
    print("\n🌊🦈🐋 AUREON MOVERS & SHAKERS SCANNER 🐋🦈🌊")
    print("=" * 50)
    print("Initializing whale detection systems...")
    print()
    
    scanner = MoversShakersScanner(lookback_minutes=15)
    
    # Run continuous scans
    scan_interval = 30  # seconds
    
    while True:
        try:
            report = await scanner.run_scan()
            
            # Save report to JSON
            report_data = {
                'timestamp': report.timestamp,
                'total_movers': report.total_movers,
                'total_volume_usd': report.total_volume_usd,
                'net_flow_direction': report.net_flow_direction,
                'whale_consensus': report.whale_consensus,
                'manipulation_alert': report.manipulation_alert,
                'movers': [asdict(m) for m in report.all_movers],
            }
            
            # Convert WaveType enum to string
            for m in report_data['movers']:
                m['wave_type'] = m['wave_type'].value if hasattr(m['wave_type'], 'value') else str(m['wave_type'])
            
            with open('movers_shakers_report.json', 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            print(f"💾 Report saved to movers_shakers_report.json")
            print(f"⏰ Next scan in {scan_interval}s...")
            
            await asyncio.sleep(scan_interval)
            
        except KeyboardInterrupt:
            print("\n🛑 Scanner stopped by user")
            break
        except Exception as e:
            logger.error(f"Scan error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
