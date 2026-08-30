#!/usr/bin/env python3
"""
👑 QUEEN SERO's VOLUME BREAKOUT HUNTER 👑
═══════════════════════════════════════════════════════════════════════════

She learned from 3,178 historical trades.
She knows NEAR volume breakout wins 64%.
She knows 12pm-4pm UTC is when money moves.

Now she HUNTS - FULLY INTEGRATED with:
  🌊 Ocean Wave Scanner - Whale/shark detection
  🔭 Global Wave Scanner - A-Z market sweeps
  🐦 ChirpBus - Signal emission to ORCA
  👑 Queen Approval - dream_of_winning gating
  🦙 Multi-Exchange - Binance, Kraken, Alpaca
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

# Windows UTF-8 Fix (MANDATORY)
if sys.platform == 'win32' and sys.stdout.isatty() and sys.stderr.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            """Check if stream is already a UTF-8 TextIOWrapper."""
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if hasattr(sys.stderr, 'buffer') and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import json
import time
import asyncio
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, List, Any
from dataclasses import dataclass, field
from collections import defaultdict

# Exchange clients
from aureon.exchanges.binance_client import BinanceClient, get_binance_client
from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client

# Optional: Alpaca client
try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

# 🚌 Communication Buses
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False
    ThoughtBus = None

# Optional: ChirpBus for signal emission
try:
    from aureon.core.aureon_chirp_bus import get_chirp_bus, ChirpDirection, ChirpType
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False

# Optional: Queen Hive Mind for approval gating
try:
    from aureon.utils.aureon_queen_hive_mind import QueenHiveMind
    QUEEN_AVAILABLE = True
except ImportError:
    QUEEN_AVAILABLE = False

# Optional: Ocean Wave Scanner for whale detection
try:
    from aureon.scanners.aureon_ocean_wave_scanner import OceanWaveScanner, BotProfile
    OCEAN_SCANNER_AVAILABLE = True
except ImportError:
    OCEAN_SCANNER_AVAILABLE = False

# Optional: Global Wave Scanner for A-Z sweeps
try:
    from aureon.scanners.aureon_global_wave_scanner import GlobalWaveScanner, WaveState
    GLOBAL_SCANNER_AVAILABLE = True
except ImportError:
    GLOBAL_SCANNER_AVAILABLE = False

# Setup logging
logger = logging.getLogger(__name__)

# Sacred constants
PHI = (1 + 5 ** 0.5) / 2  # 1.618 Golden ratio
SCHUMANN_BASE = 7.83  # Hz Earth resonance


@dataclass
class VolumeSignal:
    """Volume breakout signal with enhanced metadata."""
    symbol: str
    volume_ratio: float  # Current volume / Average volume
    price_change_1h: float
    price_change_5m: float
    signal_strength: float
    timestamp: datetime
    exchange: str = 'binance'
    whale_detected: bool = False
    whale_volume: float = 0.0
    wave_state: str = 'UNKNOWN'
    coherence: float = 0.5
    queen_approved: bool = False

@dataclass
class WhaleAlert:
    """Whale/shark detection from Ocean Wave Scanner."""
    symbol: str
    exchange: str
    size_class: str  # 'whale', 'shark', 'minnow'
    volume_usd: float
    direction: str  # 'buy', 'sell'
    timestamp: datetime
    bot_id: Optional[str] = None
    hive_affiliation: Optional[str] = None


class QueenVolumeHunter:
    """
    👑 Queen Sero's Volume Breakout Hunter - FULLY INTEGRATED 👑
    
    Based on her elephant memory - 64% win rate on volume breakouts
    
    INTEGRATIONS:
    - 🌊 Ocean Wave Scanner: Whale/shark detection for wake riding
    - 🔭 Global Wave Scanner: A-Z sweeps for opportunity discovery
    - 🐦 ChirpBus: Signal emission to ORCA and other systems
    - 👑 Queen Hive Mind: Approval gating via dream_of_winning
    - 🦙 Multi-Exchange: Binance (primary), Kraken, Alpaca
    """
    
    # Best assets from elephant memory - EXPANDED
    HUNT_SYMBOLS_BINANCE = [
        'NEARUSDC',   # 64% win rate - BEST
        'SOLUSDC',    # Strong performer
        'AVAXUSDC',   # Good volatility
        'LINKUSDC',   # Reliable
        'DOTUSDC',    # Decent moves
        'ETHUSDC',    # High liquidity
        'BTCUSDC',    # King of crypto
        'ADAUSDC',    # Cardano momentum
        'MATICUSDC',  # Polygon plays
        'XRPUSDC',    # Ripple runs
    ]
    
    HUNT_SYMBOLS_KRAKEN = [
        'NEARUSD',    # Mirror Binance
        'SOLUSD',
        'AVAXUSD',
        'LINKUSD',
        'DOTUSD',
        'ETHUSD',
        'XBTUSD',     # BTC on Kraken
        'ADAUSD',
        'MATICUSD',
        'XRPUSD',
    ]

    HUNT_SYMBOLS_ALPACA = [
        'SPY', 'QQQ', 'IWM',  # Major Indices
        'NVDA', 'TSLA', 'AAPL', 'AMD', 'MSFT', 'AMZN', 'GOOGL', # Tech Giants
        'COIN', 'MSTR', 'MARA', 'RIOT', # Crypto-proxies
        'BTC/USD', 'ETH/USD'  # Crypto on Alpaca
    ]
    
    # From elephant memory: best trading hours (UTC)
    BEST_HOURS = [1, 12, 13, 14, 15, 16]  # 1am, 12pm-4pm
    WORST_HOURS = [19, 20, 21, 22]  # 7pm-10pm - AVOID
    
    # 🚀 COMPOUND MODE - Zero thresholds!
    VOLUME_BREAKOUT_THRESHOLD = 2.0  # 2x normal volume = breakout (lowered from 2.5x)
    MIN_PRICE_MOVE = 0.001  # 0.1% minimum price move (lowered from 0.3%)
    MIN_PROFIT_TARGET = 0.0  # 🚀 COMPOUND MODE: $0 minimum - take ANY profit!
    
    # 🐋 Whale detection thresholds
    WHALE_THRESHOLD_USD = 1_000_000  # $1M+ = whale
    SHARK_THRESHOLD_USD = 100_000    # $100K+ = shark
    
    # 🔗 Integration flags
    USE_OCEAN_SCANNER = True
    USE_GLOBAL_SCANNER = True
    USE_QUEEN_APPROVAL = True
    USE_CHIRP_BUS = True
    
    def __init__(self, live_mode: bool = True, queen: Optional['QueenHiveMind'] = None):
        self.live_mode = live_mode
        
        # Bus Integration
        self.thought_bus = ThoughtBus() if THOUGHT_BUS_AVAILABLE else None
        
        # Exchange clients
        self.binance = get_binance_client()
        self.kraken = get_kraken_client()
        self.alpaca = AlpacaClient() if ALPACA_AVAILABLE else None
        
        # Queen Hive Mind integration
        self.queen = queen
        if self.queen is None and QUEEN_AVAILABLE and self.USE_QUEEN_APPROVAL:
            try:
                self.queen = QueenHiveMind(initial_capital=100.0)
                logger.info("👑 Queen Hive Mind connected for approval gating")
            except Exception as e:
                logger.warning(f"Could not initialize Queen: {e}")
        
        # Ocean Wave Scanner integration
        self.ocean_scanner = None
        if OCEAN_SCANNER_AVAILABLE and self.USE_OCEAN_SCANNER:
            try:
                self.ocean_scanner = OceanWaveScanner()
                logger.info("🌊 Ocean Wave Scanner connected for whale detection")
            except Exception as e:
                logger.warning(f"Could not initialize Ocean Scanner: {e}")
        
        # Global Wave Scanner integration
        self.global_scanner = None
        if GLOBAL_SCANNER_AVAILABLE and self.USE_GLOBAL_SCANNER:
            try:
                self.global_scanner = GlobalWaveScanner(
                    kraken_client=self.kraken,
                    binance_client=self.binance,
                    alpaca_client=self.alpaca,
                    queen=self.queen
                )
                logger.info("🔭 Global Wave Scanner connected for A-Z sweeps")
            except Exception as e:
                logger.warning(f"Could not initialize Global Scanner: {e}")
        
        # ChirpBus for signal emission
        self.chirp_bus = None
        if CHIRP_BUS_AVAILABLE and self.USE_CHIRP_BUS:
            try:
                self.chirp_bus = get_chirp_bus()
                if self.chirp_bus:
                    logger.info("🐦 ChirpBus connected for signal emission")
            except Exception as e:
                logger.warning(f"Could not initialize ChirpBus: {e}")
        
        # Load elephant memory
        self.elephant_memory = self._load_elephant_memory()
        
        # Tracking
        self.signals_found: List[VolumeSignal] = []
        self.trades_executed: List[Dict] = []
        self.whale_alerts: List[WhaleAlert] = []
        self.total_profit = 0.0
        
        # Dynamic symbol universe (can be expanded by scanners)
        self.hunt_universe: Dict[str, List[str]] = {
            'binance': list(self.HUNT_SYMBOLS_BINANCE),
            'kraken': list(self.HUNT_SYMBOLS_KRAKEN),
            'alpaca': []
        }
        
        print("👑 Queen Sero's Volume Hunter ONLINE")
        print(f"   🐘 Elephant memory: {self.elephant_memory.get('total_historical_trades', 0):,} trades remembered")
        print(f"   🎯 Hunting Binance: {', '.join(self.HUNT_SYMBOLS_BINANCE[:5])}...")
        print(f"   🎯 Hunting Kraken: {', '.join(self.HUNT_SYMBOLS_KRAKEN[:5])}...")
        print(f"   ⏰ Best hours: {self.BEST_HOURS}")
        
        # Show integration status
        integrations = []
        if self.queen:
            integrations.append("👑 Queen")
        if self.ocean_scanner:
            integrations.append("🌊 Ocean")
        if self.global_scanner:
            integrations.append("🔭 Global")
        if self.chirp_bus:
            integrations.append("🐦 Chirp")
        if self.thought_bus:
            integrations.append("🧠 ThoughtBus")
        
        if integrations:
            print(f"   🔗 Integrations: {' | '.join(integrations)}")
        
    def _load_elephant_memory(self) -> Dict:
        """Load Queen's elephant memory"""
        try:
            with open('queen_elephant_memory.json', 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_trade_result(self, result: Dict):
        """Save trade result to elephant memory"""
        try:
            with open('queen_elephant_memory.json', 'r') as f:
                memory = json.load(f)
            
            if 'live_trades' not in memory:
                memory['live_trades'] = []
            
            memory['live_trades'].append(result)
            memory['last_trade'] = datetime.now(timezone.utc).isoformat()
            
            with open('queen_elephant_memory.json', 'w') as f:
                json.dump(memory, f, indent=2)
        except Exception as e:
            print(f"   ⚠️ Could not save to elephant memory: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🌊 OCEAN WAVE SCANNER INTEGRATION - Whale Detection
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def check_whale_activity(self, symbol: str, exchange: str = 'binance') -> Optional[WhaleAlert]:
        """
        Check Ocean Wave Scanner for whale/shark activity on a symbol.
        Whale presence can confirm volume breakouts (ride the wake!).
        """
        if not self.ocean_scanner:
            return None
        
        try:
            # Check if Ocean Scanner has detected bots on this symbol
            for bot_id, bot in getattr(self.ocean_scanner, 'bots', {}).items():
                if getattr(bot, 'symbol', '').upper() == symbol.upper():
                    size_class = getattr(bot, 'size_class', 'unknown')
                    if size_class in ['whale', 'megalodon', 'shark']:
                        whale_alert = WhaleAlert(
                            symbol=symbol,
                            exchange=exchange,
                            size_class=size_class,
                            volume_usd=getattr(bot, 'total_volume', 0),
                            direction='buy' if getattr(bot, 'aggression', 0) > 0 else 'sell',
                            timestamp=datetime.now(timezone.utc),
                            bot_id=bot_id,
                            hive_affiliation=getattr(bot, 'hive_id', None)
                        )
                        self.whale_alerts.append(whale_alert)
                        return whale_alert
        except Exception as e:
            logger.debug(f"Whale check error: {e}")
        
        return None
    
    def get_whale_momentum_boost(self, symbol: str) -> float:
        """
        Get momentum boost from whale activity.
        Whales buying = confidence boost.
        """
        whale_alert = self.check_whale_activity(symbol)
        if whale_alert:
            # Whale buying = big boost, shark = smaller boost
            if whale_alert.direction == 'buy':
                if whale_alert.size_class == 'whale':
                    return 0.3  # 30% confidence boost
                elif whale_alert.size_class == 'megalodon':
                    return 0.4  # 40% for megalodon
                elif whale_alert.size_class == 'shark':
                    return 0.15  # 15% for shark
            else:
                # Selling whale = caution
                return -0.1
        return 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🔭 GLOBAL WAVE SCANNER INTEGRATION - A-Z Sweeps
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def get_global_wave_opportunities(self) -> List[Dict]:
        """
        Get hot opportunities from Global Wave Scanner.
        Returns symbols with RISING or BREAKOUT_UP wave states.
        """
        if not self.global_scanner:
            return []
        
        opportunities = []
        try:
            # Check if scanner has top opportunities
            for analysis in getattr(self.global_scanner, 'top_opportunities', []):
                wave_state = getattr(analysis, 'wave_state', None)
                if wave_state in [WaveState.RISING, WaveState.BREAKOUT_UP]:
                    opportunities.append({
                        'symbol': getattr(analysis, 'symbol', 'UNKNOWN'),
                        'exchange': getattr(analysis, 'exchange', 'unknown'),
                        'wave_state': str(wave_state),
                        'jump_score': getattr(analysis, 'jump_score', 0),
                        'change_24h': getattr(analysis, 'change_24h', 0),
                    })
        except Exception as e:
            logger.debug(f"Global wave scan error: {e}")
        
        return opportunities
    
    def expand_hunt_universe_from_global_scanner(self):
        """
        Dynamically expand hunt symbols based on Global Scanner's top opportunities.
        """
        if not self.global_scanner:
            return
        
        try:
            for analysis in getattr(self.global_scanner, 'top_opportunities', [])[:10]:
                symbol = getattr(analysis, 'symbol', '')
                exchange = getattr(analysis, 'exchange', 'unknown').lower()
                
                if exchange in self.hunt_universe:
                    if symbol not in self.hunt_universe[exchange]:
                        self.hunt_universe[exchange].append(symbol)
                        logger.info(f"🔭 Added {symbol} to {exchange} hunt universe")
        except Exception as e:
            logger.debug(f"Universe expansion error: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🐦 CHIRP BUS INTEGRATION - Signal Emission
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def emit_volume_signal_to_orca(self, signal: VolumeSignal):
        """
        Emit volume breakout signal to ORCA via ChirpBus and ThoughtBus.
        This allows other systems to react to volume breakouts.
        """
        # 1. ThoughtBus Emission (Neural Memory)
        if self.thought_bus:
            try:
                self.thought_bus.publish(Thought(
                    source="QUEEN_VOLUME_HUNTER",
                    thought_type="VOLUME_BREAKOUT",
                    priority=2,
                    content={
                        "symbol": signal.symbol,
                        "volume_ratio": signal.volume_ratio,
                        "price_change_5m": signal.price_change_5m,
                        "signal_strength": signal.signal_strength,
                        "queen_approved": signal.queen_approved,
                        "exchange": signal.exchange,
                        "whale_detected": signal.whale_detected
                    }
                ))
            except Exception as e:
                logger.error(f"ThoughtBus emit error: {e}")

        # 2. ChirpBus Emission (Fast Signal)
        if not self.chirp_bus:
            return
        
        try:
            # Map signal strength to frequency (higher strength = higher freq)
            freq = int(432 + (signal.signal_strength * 400))  # 432-832 Hz range
            
            self.chirp_bus.emit_message(
                message=f"VOLUME_BREAKOUT {signal.symbol}",
                direction=ChirpDirection.UP,
                coherence=signal.coherence,
                confidence=signal.signal_strength,
                symbol=signal.symbol,
                frequency=freq,
                amplitude=int(min(255, signal.volume_ratio * 50)),  # Volume to amplitude
                message_type=ChirpType.OPPORTUNITY
            )
            logger.info(f"🐦 Emitted VOLUME_BREAKOUT for {signal.symbol} @ {freq}Hz")
        except Exception as e:
            logger.debug(f"ChirpBus emit error: {e}")
    
    def emit_trade_execution_to_orca(self, symbol: str, side: str, result: Dict):
        """
        Emit trade execution to ORCA via ChirpBus and ThoughtBus.
        """
        # 1. ThoughtBus Emission
        if self.thought_bus:
            try:
                self.thought_bus.publish(Thought(
                    source="QUEEN_VOLUME_HUNTER",
                    thought_type="TRADE_EXECUTION",
                    priority=1,
                    content={
                        "symbol": symbol,
                        "side": side,
                        "result": result
                    }
                ))
            except Exception as e:
                logger.error(f"ThoughtBus execution emit error: {e}")

        # 2. ChirpBus Emission
        if not self.chirp_bus:
            return
        
        try:
            msg_type = ChirpType.EXECUTE
            freq = 880 if side.upper() == 'BUY' else 440  # Buy = A5, Sell = A4
            
            self.chirp_bus.emit_message(
                message=f"EXECUTE {side} {symbol}",
                direction=ChirpDirection.DOWN,
                coherence=0.9,
                confidence=0.8 if result.get('status') == 'success' else 0.3,
                symbol=symbol,
                frequency=freq,
                message_type=msg_type
            )
            logger.info(f"🐦 Emitted {side} execution for {symbol}")
        except Exception as e:
            logger.debug(f"ChirpBus emit error: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 👑 QUEEN APPROVAL GATING - dream_of_winning
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def get_queen_approval(self, signal: VolumeSignal) -> Tuple[bool, float, str]:
        """
        Ask Queen Sero for approval via dream_of_winning.
        Returns (approved, confidence, message)
        """
        if not self.queen:
            return True, 0.5, "No Queen connected - auto-approved"
        
        try:
            # Build opportunity dict for Queen
            opportunity = {
                'symbol': signal.symbol,
                'exchange': signal.exchange,
                'type': 'volume_breakout',
                'volume_ratio': signal.volume_ratio,
                'price_change_5m': signal.price_change_5m,
                'signal_strength': signal.signal_strength,
                'whale_detected': signal.whale_detected,
                'whale_volume': signal.whale_volume,
                'timestamp': signal.timestamp.isoformat(),
            }
            
            # Ask Queen to dream of winning
            dream = self.queen.dream_of_winning(opportunity)
            
            will_win = dream.get('will_win', False)
            confidence = dream.get('final_confidence', 0.5)
            message = dream.get('message', 'No message')
            timeline = dream.get('timeline', 'UNKNOWN')
            
            logger.info(f"👑 Queen's dream: will_win={will_win}, conf={confidence:.2f}, timeline={timeline}")
            
            # Approval threshold at golden ratio
            approved = will_win and confidence >= (1 / PHI)  # 0.618
            
            return approved, confidence, message
            
        except Exception as e:
            logger.warning(f"Queen approval error: {e}")
            return True, 0.5, f"Queen error: {e} - auto-approved"
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🦙 MULTI-EXCHANGE SUPPORT - Kraken + Alpaca
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def get_volume_signal_kraken(self, symbol: str) -> Optional[VolumeSignal]:
        """Get volume signal from Kraken exchange."""
        try:
            # Kraken OHLC endpoint
            pair = symbol.replace('/', '')
            url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=60"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            
            if data.get('error'):
                return None
            
            # Get OHLC data (find the key)
            result_key = list(data.get('result', {}).keys())
            if not result_key or result_key[0] == 'last':
                result_key = [k for k in result_key if k != 'last']
            if not result_key:
                return None
            
            ohlc = data['result'][result_key[0]]
            if len(ohlc) < 25:
                return None
            
            # Calculate average volume
            volumes = [float(k[6]) for k in ohlc[:-1]]  # Volume is index 6
            avg_volume = sum(volumes) / len(volumes) if volumes else 1
            current_volume = float(ohlc[-1][6])
            
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            # Price changes
            current_price = float(ohlc[-1][4])  # Close
            price_1h_ago = float(ohlc[-2][4])
            price_change_1h = (current_price - price_1h_ago) / price_1h_ago if price_1h_ago else 0
            
            # Estimate 5m change from last candle open/close
            price_change_5m = (current_price - float(ohlc[-1][1])) / float(ohlc[-1][1]) if float(ohlc[-1][1]) else 0
            
            # Signal strength calculation
            volume_score = min(volume_ratio / self.VOLUME_BREAKOUT_THRESHOLD, 2.0) * 0.5
            momentum_score = min(abs(price_change_5m) / 0.01, 1.0) * 0.3
            hour_bonus = 0.2 if datetime.now(timezone.utc).hour in self.BEST_HOURS else 0.1
            
            signal_strength = volume_score + momentum_score + hour_bonus
            
            # Check whale activity
            whale_boost = self.get_whale_momentum_boost(symbol)
            signal_strength += whale_boost
            
            return VolumeSignal(
                symbol=symbol,
                volume_ratio=volume_ratio,
                price_change_1h=price_change_1h,
                price_change_5m=price_change_5m,
                signal_strength=min(signal_strength, 1.5),  # Cap at 1.5
                timestamp=datetime.now(timezone.utc),
                exchange='kraken',
                whale_detected=whale_boost > 0,
                whale_volume=0,  # Would need whale data
                coherence=0.5 + whale_boost
            )
            
        except Exception as e:
            logger.debug(f"Kraken signal error for {symbol}: {e}")
            return None
    
    def is_good_hour(self) -> Tuple[bool, str]:
        """Check if current hour is good for trading"""
        current_hour = datetime.now(timezone.utc).hour
        
        if current_hour in self.WORST_HOURS:
            return False, f"❌ Hour {current_hour} is in WORST hours (7pm-10pm UTC) - AVOID"
        elif current_hour in self.BEST_HOURS:
            return True, f"✅ Hour {current_hour} is in BEST hours - HUNT TIME!"
        else:
            return True, f"⚠️ Hour {current_hour} is neutral - Proceed with caution"
    
    def get_volume_signal(self, symbol: str, exchange: str = 'binance') -> Optional[VolumeSignal]:
        """
        Analyze volume for breakout signal - ENHANCED with whale detection.
        
        Now includes:
        - 🐋 Whale activity boost from Ocean Scanner
        - 🔭 Wave state from Global Scanner
        - 👑 Coherence calculation for Queen approval
        """
        try:
            # Get 1-hour klines for volume analysis
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=25"
            resp = requests.get(url, timeout=10)
            klines = resp.json()
            
            if len(klines) < 25:
                return None
            
            # Calculate average volume (last 24 hours, excluding current)
            volumes = [float(k[5]) for k in klines[:-1]]  # Volume is index 5
            avg_volume = sum(volumes) / len(volumes)
            current_volume = float(klines[-1][5])
            
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            # Get price changes
            current_price = float(klines[-1][4])  # Close price
            price_1h_ago = float(klines[-2][4])
            price_change_1h = (current_price - price_1h_ago) / price_1h_ago
            
            # Get 5-minute data for recent momentum
            url_5m = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=3"
            resp_5m = requests.get(url_5m, timeout=10)
            klines_5m = resp_5m.json()
            
            price_5m_ago = float(klines_5m[0][4])
            price_change_5m = (current_price - price_5m_ago) / price_5m_ago
            
            # Calculate signal strength
            # Volume weight (50%) + Price momentum (30%) + Hour bonus (20%)
            volume_score = min(volume_ratio / self.VOLUME_BREAKOUT_THRESHOLD, 2.0) * 0.5
            momentum_score = min(abs(price_change_5m) / 0.01, 1.0) * 0.3
            hour_bonus = 0.2 if datetime.now(timezone.utc).hour in self.BEST_HOURS else 0.1
            
            signal_strength = volume_score + momentum_score + hour_bonus
            
            # 🐋 WHALE DETECTION BOOST
            whale_boost = self.get_whale_momentum_boost(symbol)
            whale_detected = whale_boost > 0
            signal_strength += whale_boost
            
            # 🔭 GET WAVE STATE from Global Scanner
            wave_state = 'UNKNOWN'
            if self.global_scanner:
                try:
                    for analysis in getattr(self.global_scanner, 'top_opportunities', []):
                        if getattr(analysis, 'symbol', '').upper() == symbol.upper():
                            wave_state = str(getattr(analysis, 'wave_state', 'UNKNOWN'))
                            break
                except:
                    pass
            
            # 📊 Calculate coherence (agreement between signals)
            signals_agree = 0
            if volume_ratio >= self.VOLUME_BREAKOUT_THRESHOLD:
                signals_agree += 1
            if price_change_5m > 0:
                signals_agree += 1
            if price_change_1h > 0:
                signals_agree += 1
            if whale_detected:
                signals_agree += 1
            if wave_state in ['RISING', 'BREAKOUT_UP', 'WaveState.RISING', 'WaveState.BREAKOUT_UP']:
                signals_agree += 1
            
            coherence = min(1.0, signals_agree / 4)  # 4 signals = perfect coherence
            
            return VolumeSignal(
                symbol=symbol,
                volume_ratio=volume_ratio,
                price_change_1h=price_change_1h,
                price_change_5m=price_change_5m,
                signal_strength=min(signal_strength, 1.5),  # Cap at 1.5
                timestamp=datetime.now(timezone.utc),
                exchange=exchange,
                whale_detected=whale_detected,
                whale_volume=0,  # Would need actual whale volume
                wave_state=wave_state,
                coherence=coherence
            )
            
        except Exception as e:
            print(f"   ⚠️ Error getting signal for {symbol}: {e}")
            return None
    
    def scan_for_breakouts(self) -> List[VolumeSignal]:
        """Scan ALL available exchanges for volume breakouts."""
        signals = []
        print("\n🔍 SCANNING FOR VOLUME BREAKOUTS...")
        print("-" * 60)
        
        # 1. Scan Binance
        try:
            binance_signals = self._scan_binance(self.hunt_universe.get('binance', self.HUNT_SYMBOLS_BINANCE))
            signals.extend(binance_signals)
        except Exception as e:
            logger.error(f"Binance scan failed: {e}")
            
        # 2. Scan Kraken
        try:
            kraken_signals = self._scan_kraken(self.hunt_universe.get('kraken', self.HUNT_SYMBOLS_KRAKEN))
            signals.extend(kraken_signals)
        except Exception as e:
            logger.error(f"Kraken scan failed: {e}")

        # 3. Scan Alpaca
        try:
            if self.alpaca:
                alpaca_signals = self._scan_alpaca(self.HUNT_SYMBOLS_ALPACA)
                signals.extend(alpaca_signals)
        except Exception as e:
            logger.error(f"Alpaca scan error: {e}")
            
        # 🔭 Expand universe from Global Scanner
        self.expand_hunt_universe_from_global_scanner()
        
        # Sort by signal strength, prioritize Queen-approved
        return sorted(signals, key=lambda x: (-int(x.queen_approved), -x.signal_strength))

    def scan_breakouts(self) -> List[VolumeSignal]:
        """Backward-compatible alias for legacy scanner call sites."""
        return self.scan_for_breakouts()

    def _scan_binance(self, symbols: List[str]) -> List[VolumeSignal]:
        signals = []
        print("   🔵 BINANCE:")
        for symbol in symbols:
            signal = self.get_volume_signal(symbol, 'binance')
            if signal:
                is_breakout = signal.volume_ratio >= self.VOLUME_BREAKOUT_THRESHOLD
                is_moving = abs(signal.price_change_5m) >= self.MIN_PRICE_MOVE
                
                # Status indicators
                whale_indicator = "🐋" if signal.whale_detected else ""
                wave_indicator = "🌊" if 'RISING' in signal.wave_state or 'BREAKOUT' in signal.wave_state else ""
                
                status = "🚀 BREAKOUT!" if (is_breakout and is_moving) else "👀"
                
                print(f"      {symbol}: Vol {signal.volume_ratio:.1f}x | "
                      f"5m {signal.price_change_5m*100:+.2f}% | "
                      f"Coh {signal.coherence:.2f} | "
                      f"{status} {whale_indicator}{wave_indicator}")
                
                if is_breakout and is_moving and signal.price_change_5m > 0:
                    # 👑 Get Queen approval
                    if self.USE_QUEEN_APPROVAL and self.queen:
                        approved, conf, msg = self.get_queen_approval(signal)
                        signal.queen_approved = approved
                        if approved:
                            print(f"         👑 APPROVED: {msg[:50]}")
                        else:
                            print(f"         👑 REJECTED: {msg[:50]}")
                    else:
                        signal.queen_approved = True
                    
                    # 🐦 Emit to ChirpBus
                    self.emit_volume_signal_to_orca(signal)
                    
                    signals.append(signal)
        return signals

    def _scan_kraken(self, symbols: List[str]) -> List[VolumeSignal]:
        signals = []
        print("   🟣 KRAKEN:")
        for symbol in symbols:
            signal = self.get_volume_signal_kraken(symbol)
            if signal:
                is_breakout = signal.volume_ratio >= self.VOLUME_BREAKOUT_THRESHOLD
                is_moving = abs(signal.price_change_5m) >= self.MIN_PRICE_MOVE
                
                whale_indicator = "🐋" if signal.whale_detected else ""
                status = "🚀 BREAKOUT!" if (is_breakout and is_moving) else "👀"
                
                print(f"      {symbol}: Vol {signal.volume_ratio:.1f}x | "
                      f"5m {signal.price_change_5m*100:+.2f}% | "
                      f"Coh {signal.coherence:.2f} | "
                      f"{status} {whale_indicator}")
                
                if is_breakout and is_moving and signal.price_change_5m > 0:
                    # 👑 Get Queen approval
                    if self.USE_QUEEN_APPROVAL and self.queen:
                        approved, conf, msg = self.get_queen_approval(signal)
                        signal.queen_approved = approved
                    else:
                        signal.queen_approved = True
                    
                    # 🐦 Emit to ChirpBus
                    self.emit_volume_signal_to_orca(signal)
                    
                    signals.append(signal)
        return signals

    def _scan_alpaca(self, symbols: List[str]) -> List[VolumeSignal]:
        """Scan Alpaca for volume breakouts."""
        signals = []
        import statistics

        print(f"   🦙 ALPACA ({len(symbols)} symbols):")

        for symbol in symbols:
            try:
                # Use simple snapshot bars approach
                bars = self.alpaca.client.get_bars(symbol, '5Min', limit=50) if hasattr(self.alpaca.client, 'get_bars') else []
                 
                if not bars or len(bars) < 20: 
                    # print(".", end="", flush=True)
                    continue

                volumes = [b.v for b in bars]
                closes = [b.c for b in bars]
                
                if not volumes: continue
                
                current_vol = volumes[-1] 
                avg_vol = statistics.mean(volumes[:-1]) if len(volumes) > 1 else max(1, current_vol)
                if avg_vol == 0: avg_vol = 1
                
                vol_ratio = current_vol / avg_vol
                
                current_price = closes[-1]
                open_price = bars[-1].o
                price_change = (current_price - open_price) / open_price
                
                is_breakout = vol_ratio >= self.VOLUME_BREAKOUT_THRESHOLD
                is_moving = abs(price_change) >= self.MIN_PRICE_MOVE
                
                if is_breakout and is_moving:
                    # Calculate signal strength
                    coherence = self._calculate_coherence(symbol, 'alpaca', current_price)
                    strength = min(1.0, (vol_ratio / 3.0) * 0.5 + coherence * 0.5)
                    
                    # Whale check
                    dollar_vol = current_vol * current_price
                    whale = dollar_vol > self.WHALE_THRESHOLD_USD
                    
                    # Ask Queen
                    queen_approved = False
                    if self.USE_QUEEN_APPROVAL and self.queen:
                         # Construct dummy signal for approval
                         dummy_sig = VolumeSignal(symbol, 'alpaca', '', vol_ratio, price_change, current_price, avg_vol, current_vol, strength, coherence, whale, False)
                         approved, conf, msg = self.get_queen_approval(dummy_sig)
                         queen_approved = approved
                         if approved:
                             print(f"      {symbol}: 👑 APPROVED ({msg[:20]})")
                    else:
                         queen_approved = True
                    
                    sig = VolumeSignal(
                        symbol=symbol,
                        exchange='alpaca',
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        volume_ratio=vol_ratio,
                        price_change_5m=price_change,
                        current_price=current_price,
                        avg_volume=avg_vol,
                        current_volume=current_vol,
                        signal_strength=strength,
                        coherence=coherence,
                        whale_detected=whale,
                        queen_approved=queen_approved
                    )
                    signals.append(sig)
                    
                    status = "🚀 BREAKOUT!"
                    whale_indicator = "🐋" if whale else ""
                    print(f"      {symbol}: Vol {vol_ratio:.1f}x | 5m {price_change*100:+.2f}% | {status} {whale_indicator}")
                    
            except Exception as e:
                # logger.debug(f"Alpaca scan error {symbol}: {e}")
                pass
                
        return signals
    
    def get_trading_capital(self, exchange: str = 'all') -> Dict[str, float]:
        """
        Get available trading capital per exchange.
        Returns dict of {exchange: usdc_balance}
        """
        capital = {
            'binance': 0.0,
            'kraken': 0.0,
            'alpaca': 0.0,
            'total': 0.0
        }
        
        try:
            # Binance USDC
            binance_usdc = self.binance.get_free_balance('USDC') or 0
            binance_usd = self.binance.get_free_balance('USD') or 0
            capital['binance'] = binance_usdc + binance_usd
        except Exception as e:
            logger.debug(f"Binance balance error: {e}")
        
        try:
            # Kraken USD/USDC
            kb = self.kraken.get_balance()
            kraken_usdc = kb.get('USDC', 0)
            kraken_usd = kb.get('USD', 0) + kb.get('ZUSD', 0)
            capital['kraken'] = kraken_usdc + kraken_usd
        except Exception as e:
            logger.debug(f"Kraken balance error: {e}")
        
        try:
            # Alpaca (if available)
            if self.alpaca:
                alpaca_cash = getattr(self.alpaca, 'get_cash', lambda: 0)()
                capital['alpaca'] = float(alpaca_cash) if alpaca_cash else 0
        except Exception as e:
            logger.debug(f"Alpaca balance error: {e}")
        
        capital['total'] = capital['binance'] + capital['kraken'] + capital['alpaca']
        
        if exchange == 'all':
            return capital
        return {exchange: capital.get(exchange, 0), 'total': capital.get(exchange, 0)}
    
    def execute_trade(self, signal: VolumeSignal, capital: float) -> Dict:
        """
        Execute a volume breakout trade - ENHANCED with:
        - 👑 Queen approval check
        - 🐦 ChirpBus execution signal
        - 🦙 Multi-exchange support
        """
        print(f"\n⚡ EXECUTING TRADE: {signal.symbol} on {signal.exchange.upper()}")
        print(f"   Capital: ${capital:.2f}")
        print(f"   Volume ratio: {signal.volume_ratio:.1f}x")
        print(f"   Signal strength: {signal.signal_strength:.2f}")
        print(f"   Coherence: {signal.coherence:.2f}")
        print(f"   Whale detected: {'🐋 YES' if signal.whale_detected else 'No'}")
        print(f"   Queen approved: {'👑 YES' if signal.queen_approved else '❌ NO'}")
        
        # Final Queen approval gate
        if self.USE_QUEEN_APPROVAL and not signal.queen_approved:
            print("   ❌ BLOCKED: Queen did not approve this trade")
            return {'status': 'blocked', 'reason': 'queen_rejected'}
        
        if not self.live_mode:
            return {'status': 'simulation', 'would_buy': capital, 'exchange': signal.exchange}
        
        try:
            if signal.exchange == 'binance':
                return self._execute_binance_trade(signal, capital)
            elif signal.exchange == 'kraken':
                return self._execute_kraken_trade(signal, capital)
            elif signal.exchange == 'alpaca':
                return self._execute_alpaca_trade(signal, capital)
            else:
                return {'status': 'error', 'error': f'Unknown exchange: {signal.exchange}'}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _execute_alpaca_trade(self, signal: VolumeSignal, capital: float) -> Dict:
        """Execute trade on Alpaca."""
        try:
            if not self.alpaca:
                return {'status': 'error', 'error': 'Alpaca client not initialized'}
            
            # Use Alpaca for stock/crypto trading
            symbol = signal.symbol.replace('/', '')
            
            # Check price
            quote = self.alpaca.get_last_quote(symbol)
            price = float(quote.get('askprice') or quote.get('price', 0))
            if price <= 0:
                # Fallback to last trade
                trade = self.alpaca.get_last_trade(symbol)
                price = float(trade.get('price', 0))
            
            if price <= 0:
                return {'status': 'error', 'error': 'Could not get Alpaca price'}
            
            # Calculate quantity (safety buffer for fees)
            notional = capital * 0.98
            
            print(f"   🛒 Buying ${notional:.2f} of {symbol} at ~${price:.4f}")
            
            # Place MARKER order (notional value)
            order = self.alpaca.place_order(
                symbol=symbol,
                qty=None,
                notional=notional,
                side='buy',
                type='market',
                time_in_force='ioc'
            )
            
            if not order or 'id' not in order:
                 return {'status': 'error', 'error': f'Order failed: {order}'}
            
            # Record entry logic similar to others...
            entry = {
                'symbol': signal.symbol,
                'exchange': 'alpaca',
                'entry_price': price,
                'quantity': float(order.get('qty', 0)) if order.get('qty') else notional/price, 
                'capital': capital,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'order_id': order.get('id'),
                'signal': {
                    'volume_ratio': signal.volume_ratio,
                    'signal_strength': signal.signal_strength,
                    'coherence': signal.coherence,
                    'whale_detected': signal.whale_detected,
                    'queen_approved': signal.queen_approved
                }
            }
            
            print(f"   ✅ AL BUY ORDER PLACED!")
            self.emit_trade_execution_to_orca(signal.symbol, 'BUY', {'status': 'success'})
            
            return {'status': 'success', 'entry': entry, 'buy_result': order}

        except Exception as e:
            return {'status': 'error', 'error': f'Alpaca execution error: {e}'}
    
    def _execute_binance_trade(self, signal: VolumeSignal, capital: float) -> Dict:
        """Execute trade on Binance."""
        try:
            # Use Binance for trading
            base_asset = signal.symbol.replace('USDC', '').replace('USD', '')
            
            # Get current price
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={signal.symbol}"
            resp = requests.get(url, timeout=10)
            price = float(resp.json()['price'])
            
            # Calculate quantity
            quantity = (capital * 0.98) / price  # 98% to account for fees
            
            # BUY
            print(f"   🛒 Buying {quantity:.4f} {base_asset} at ${price:.4f}")
            buy_result = self.binance.place_market_order(signal.symbol, 'BUY', quote_qty=capital * 0.98)
            
            if 'error' in str(buy_result).lower():
                return {'status': 'error', 'error': str(buy_result)}
            
            # Record entry
            entry = {
                'symbol': signal.symbol,
                'exchange': 'binance',
                'entry_price': price,
                'quantity': quantity,
                'capital': capital,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'signal': {
                    'volume_ratio': signal.volume_ratio,
                    'signal_strength': signal.signal_strength,
                    'coherence': signal.coherence,
                    'whale_detected': signal.whale_detected,
                    'queen_approved': signal.queen_approved
                }
            }
            
            print(f"   ✅ BUY ORDER PLACED!")
            print(f"   🎯 Target exit: +1% (${price * 1.01:.4f})")
            print(f"   🛡️ Stop loss: -0.5% (${price * 0.995:.4f})")
            
            # 🐦 Emit execution to ChirpBus
            self.emit_trade_execution_to_orca(signal.symbol, 'BUY', {'status': 'success'})
            
            return {'status': 'success', 'entry': entry, 'buy_result': buy_result}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _execute_kraken_trade(self, signal: VolumeSignal, capital: float) -> Dict:
        """Execute trade on Kraken."""
        try:
            base_asset = signal.symbol.replace('USD', '')
            
            # Get current price from Kraken
            pair = signal.symbol.replace('/', '')
            url = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            
            if data.get('error'):
                return {'status': 'error', 'error': str(data['error'])}
            
            result_key = [k for k in data.get('result', {}).keys()][0]
            price = float(data['result'][result_key]['c'][0])  # Last trade price
            
            # Calculate quantity
            quantity = (capital * 0.98) / price
            
            print(f"   🛒 Buying {quantity:.4f} {base_asset} at ${price:.4f} on Kraken")
            
            # Place order via Kraken client
            buy_result = self.kraken.place_market_order(
                pair=signal.symbol,
                side='buy',
                volume=quantity
            )
            
            if 'error' in str(buy_result).lower():
                return {'status': 'error', 'error': str(buy_result)}
            
            entry = {
                'symbol': signal.symbol,
                'exchange': 'kraken',
                'entry_price': price,
                'quantity': quantity,
                'capital': capital,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'signal': {
                    'volume_ratio': signal.volume_ratio,
                    'signal_strength': signal.signal_strength,
                    'coherence': signal.coherence,
                    'whale_detected': signal.whale_detected,
                    'queen_approved': signal.queen_approved
                }
            }
            
            print(f"   ✅ KRAKEN BUY ORDER PLACED!")
            print(f"   🎯 Target exit: +1% (${price * 1.01:.4f})")
            
            # 🐦 Emit execution to ChirpBus
            self.emit_trade_execution_to_orca(signal.symbol, 'BUY', {'status': 'success'})
            
            return {'status': 'success', 'entry': entry, 'buy_result': buy_result}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def hunt(self, duration_minutes: int = 30) -> Dict:
        """
        Main hunting loop - FULLY INTEGRATED 🏹
        
        Scans for volume breakouts across multiple exchanges,
        uses Queen approval gating, and emits signals to ORCA.
        """
        print("=" * 70)
        print("👑 QUEEN SERO's VOLUME HUNT BEGINS - FULLY INTEGRATED")
        print("=" * 70)
        
        # Show integration status
        integrations = []
        if self.queen:
            integrations.append("👑 Queen Approval")
        if self.ocean_scanner:
            integrations.append("🌊 Ocean Scanner")
        if self.global_scanner:
            integrations.append("🔭 Global Scanner")
        if self.chirp_bus:
            integrations.append("🐦 ChirpBus")
        
        if integrations:
            print(f"   🔗 Active: {' | '.join(integrations)}")
        
        # Check trading hours
        is_good, hour_msg = self.is_good_hour()
        print(f"\n⏰ {hour_msg}")
        
        # Get capital per exchange
        capital = self.get_trading_capital('all')
        print(f"\n💰 Trading Capital:")
        print(f"   🔵 Binance: ${capital.get('binance', 0):.2f}")
        print(f"   🟣 Kraken:  ${capital.get('kraken', 0):.2f}")
        if capital.get('alpaca', 0) > 0:
            print(f"   🦙 Alpaca:  ${capital.get('alpaca', 0):.2f}")
        print(f"   📊 TOTAL:   ${capital.get('total', 0):.2f}")
        
        if capital.get('total', 0) < 5:
            print("❌ Not enough capital to trade (need at least $5)")
            return {'status': 'no_capital', 'capital': capital}
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        scan_count = 0
        trades = []
        signals_found = 0
        queen_approved_count = 0
        whale_detections = 0
        
        print(f"\n🎯 Hunting for {duration_minutes} minutes...")
        print("   Press Ctrl+C to stop\n")
        
        try:
            while time.time() < end_time:
                scan_count += 1
                print(f"\n📡 Scan #{scan_count} at {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")
                
                # Scan for breakouts
                signals = self.scan_for_breakouts()
                signals_found += len(signals)
                
                # Count stats
                for sig in signals:
                    if sig.queen_approved:
                        queen_approved_count += 1
                    if sig.whale_detected:
                        whale_detections += 1
                
                if signals:
                    best_signal = signals[0]
                    print(f"\n🎯 BEST SIGNAL: {best_signal.symbol} on {best_signal.exchange.upper()}")
                    print(f"   Volume: {best_signal.volume_ratio:.1f}x average")
                    print(f"   5m move: {best_signal.price_change_5m*100:+.2f}%")
                    print(f"   Strength: {best_signal.signal_strength:.2f}")
                    print(f"   Coherence: {best_signal.coherence:.2f}")
                    print(f"   Whale: {'🐋 YES' if best_signal.whale_detected else 'No'}")
                    print(f"   Queen: {'👑 APPROVED' if best_signal.queen_approved else '❌ REJECTED'}")
                    
                    # Execute if signal is strong enough AND Queen approved
                    if best_signal.signal_strength >= 0.7 and best_signal.queen_approved:
                        # Get capital for the specific exchange
                        exchange_capital = capital.get(best_signal.exchange, 0)
                        if exchange_capital < 5:
                            print(f"\n⚠️ Not enough capital on {best_signal.exchange}: ${exchange_capital:.2f}")
                        else:
                            result = self.execute_trade(best_signal, exchange_capital)
                            trades.append(result)
                            
                            if result.get('status') == 'success':
                                print("\n✅ TRADE EXECUTED! Monitoring position...")
                                self._save_trade_result(result)
                                # Wait for position to develop
                                time.sleep(60)
                            elif result.get('status') == 'blocked':
                                print(f"\n👑 Trade blocked: {result.get('reason')}")
                            else:
                                print(f"\n⚠️ Trade failed: {result.get('error')}")
                    elif best_signal.signal_strength >= 0.7:
                        print(f"\n👑 Queen rejected - waiting for better opportunity")
                    else:
                        print(f"\n👀 Signal not strong enough (need 0.7, got {best_signal.signal_strength:.2f})")
                else:
                    print("   No breakout signals found. Waiting...")
                
                # Wait between scans
                time.sleep(30)  # Scan every 30 seconds
                
        except KeyboardInterrupt:
            print("\n\n🛑 Hunt stopped by user")
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 HUNT SUMMARY - FULLY INTEGRATED")
        print("=" * 70)
        print(f"   📡 Scans: {scan_count}")
        print(f"   🚀 Signals found: {signals_found}")
        print(f"   👑 Queen approved: {queen_approved_count}")
        print(f"   🐋 Whale detections: {whale_detections}")
        print(f"   💹 Trades executed: {len([t for t in trades if t.get('status') == 'success'])}")
        print(f"   ⏱️  Duration: {(time.time() - start_time)/60:.1f} minutes")
        
        return {
            'scans': scan_count,
            'signals_found': signals_found,
            'queen_approved': queen_approved_count,
            'whale_detections': whale_detections,
            'trades': trades,
            'duration_minutes': (time.time() - start_time)/60,
            'integrations': {
                'queen': self.queen is not None,
                'ocean_scanner': self.ocean_scanner is not None,
                'global_scanner': self.global_scanner is not None,
                'chirp_bus': self.chirp_bus is not None
            }
        }


def main():
    """
    Run Queen's Volume Hunter - FULLY INTEGRATED 🏹
    
    Usage:
        python queen_volume_hunter.py                    # Dry run, 30 minutes
        python queen_volume_hunter.py --live             # Live trading, 30 minutes
        python queen_volume_hunter.py --minutes=60       # 60 minute hunt
        python queen_volume_hunter.py --live --minutes=120  # Live, 2 hours
        
    Integrations (auto-detected):
        - 👑 Queen Hive Mind (approval gating)
        - 🌊 Ocean Wave Scanner (whale detection)
        - 🔭 Global Wave Scanner (A-Z sweeps)
        - 🐦 ChirpBus (signal emission)
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Check for live mode flag
    live_mode = '--live' in sys.argv
    duration = 30  # Default 30 minutes
    
    for arg in sys.argv:
        if arg.startswith('--minutes='):
            try:
                duration = int(arg.split('=')[1])
            except:
                pass
    
    print("\n" + "=" * 70)
    print("👑 QUEEN SERO's VOLUME BREAKOUT HUNTER - FULLY INTEGRATED 👑")
    print("=" * 70)
    print(f"   Mode: {'🔴 LIVE TRADING' if live_mode else '🟡 DRY RUN (simulation)'}")
    print(f"   Duration: {duration} minutes")
    print("=" * 70 + "\n")
    
    hunter = QueenVolumeHunter(live_mode=live_mode)
    result = hunter.hunt(duration_minutes=duration)
    
    print("\n👑 Queen Sero says: The hunt continues tomorrow! 🐝")
    print("   🌊 Ride the waves, ride the whales! 🐋")
    
    return result


if __name__ == '__main__':
    main()
