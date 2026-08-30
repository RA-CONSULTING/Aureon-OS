#!/usr/bin/env python3
"""
🌊 AUREON OCEAN WAVE SCANNER 🌊
═══════════════════════════════════════════════════════════════════════════

MASSIVE MULTI-EXCHANGE, MULTI-ASSET BOT SCANNER

Scans the ENTIRE OCEAN:
- All major crypto pairs (BTC, ETH, SOL, DOGE, etc.)
- All major stocks (AAPL, TSLA, NVDA, etc.)
- Multiple exchanges (Binance, Kraken, Alpaca)

Detects:
🐋 WHALES - Big bots with massive volume
🐟 MINNOWS - Small bots following whales
🏰 HIVES - Coordinated bot armies (working together)
⚔️  BATTLES - Bots hunting each other (competitive)

Shows WHO OWNS WHO - big whales commanding smaller bot armies
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
if sys.platform == 'win32' and sys.stdout.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

import asyncio
import aiohttp
import builtins
import json
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict, deque
import numpy as np

logger = logging.getLogger(__name__)


def _safe_print(*args, **kwargs):
    try:
        builtins.print(*args, **kwargs)
    except (ValueError, OSError):
        try:
            message = " ".join(str(arg) for arg in args)
            logger.info(message)
        except Exception:
            pass


print = _safe_print

# Import Bot Intelligence Profiler
try:
    from aureon.bots_intelligence.aureon_bot_intelligence_profiler import BotIntelligenceProfiler
    PROFILER_AVAILABLE = True
except ImportError:
    PROFILER_AVAILABLE = False
    print("⚠️  Bot Intelligence Profiler not available - ownership detection disabled")

# ════════════════════════════════════════════════════════════════════════════════
# 🐦 CHIRP BUS INTEGRATION - Emit bot detections to Orca for whale wake riding!
# ════════════════════════════════════════════════════════════════════════════════
CHIRP_BUS_AVAILABLE = False
get_chirp_bus = None
try:
    from aureon.core.aureon_chirp_bus import get_chirp_bus, ChirpDirection, ChirpType
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False

# 📡 THOUGHT BUS INTEGRATION - Neural Persistence
THOUGHT_BUS_AVAILABLE = False
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought, get_thought_bus
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False

# ════════════════════════════════════════════════════════════════════════════════
# 🌐 GLOBAL MARKET INTEGRATION - Full Exchange Coverage
# ════════════════════════════════════════════════════════════════════════════════
# Kraken (crypto)
try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
except ImportError:
    KRAKEN_AVAILABLE = False
    KrakenClient = None

# Binance streaming (crypto real-time)
try:
    from aureon.exchanges.binance_ws_client import BinanceWebSocketClient
    BINANCE_WS_AVAILABLE = True
except ImportError:
    BINANCE_WS_AVAILABLE = False
    BinanceWebSocketClient = None

# Alpaca (stocks + crypto)
try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    AlpacaClient = None

# Capital.com (CFDs + stocks)
try:
    from aureon.exchanges.capital_client import CapitalClient
    CAPITAL_AVAILABLE = True
except ImportError:
    CAPITAL_AVAILABLE = False
    CapitalClient = None

# Massive symbol list - scan EVERYTHING
CRYPTO_PAIRS = [
    # Major crypto
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "MATICUSDT", "DOTUSDT", "AVAXUSDT", "SHIBUSDT", "LINKUSDT",
    "LTCUSDT", "UNIUSDT", "ATOMUSDT", "ETCUSDT", "XLMUSDT", "FILUSDT",
    "TRXUSDT", "APTUSDT", "NEARUSDT", "ICPUSDT", "VETUSDT", "ALGOUSDT",
    # Mid-caps
    "ARBUSDT", "OPUSDT", "INJUSDT", "LDOUSDT", "SUIUSDT", "SEIUSDT",
    "RNDRUSDT", "FETUSDT", "GRTUSDT", "SANDUSDT", "MANAUSDT", "AAVEUSDT",
    # Memecoins
    "PEPEUSDT", "FLOKIUSDT", "BONKUSDT", "WIFUSDT", "BOMEUSDT",
]

STOCK_SYMBOLS = [
    # Tech giants
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    # Finance
    "JPM", "BAC", "GS", "V", "MA",
    # Other majors
    "WMT", "JNJ", "PG", "DIS", "NFLX", "PYPL",
]

@dataclass
class BotProfile:
    """Detailed bot profile with size classification."""
    bot_id: str
    symbol: str
    exchange: str
    pattern: str
    
    # Size classification
    size_class: str = "minnow"  # minnow, shark, whale, megalodon
    total_volume: float = 0.0
    trade_count: int = 0
    avg_trade_size: float = 0.0
    
    # Ownership (from intelligence profiler)
    owner: str = "Unknown"
    owner_confidence: float = 0.0
    firm_id: str = "unknown"
    
    # Hive membership
    hive_id: Optional[str] = None
    is_leader: bool = False
    following: Optional[str] = None
    
    # Behavioral traits
    aggression: float = 0.0
    coordination: float = 0.0
    
    # Combat status
    in_battle: bool = False
    
    # Timestamps
    first_seen: float = 0.0
    last_seen: float = 0.0
    
    # Collections (field factories last)
    followers: Set[str] = field(default_factory=set)
    battle_targets: Set[str] = field(default_factory=set)

@dataclass
class BotHive:
    """A coordinated hive of bots with a leader (whale)."""
    hive_id: str
    leader_id: str
    strategy: str = "unknown"
    mode: str = "hunting"  # hunting, defending, coordinating, battling
    
    # Collections (field factories last)
    member_ids: Set[str] = field(default_factory=set)
    
    # Hive stats
    total_volume: float = 0.0
    coordination_strength: float = 0.0  # How tightly coordinated
    
    # Hive behavior
    target_hive: Optional[str] = None

class OceanWaveScanner:
    """
    Scans the entire trading ocean for bots.
    Detects whales, hives, battles.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Bot tracking
        self.bots: Dict[str, BotProfile] = {}
        self.hives: Dict[str, BotHive] = {}
        
        # Bot Intelligence Profiler
        if PROFILER_AVAILABLE:
            self.profiler = BotIntelligenceProfiler()
            self.logger.info("🧠 Bot Intelligence Profiler enabled")
        else:
            self.profiler = None

        # 🔗 Communication Buses
        self.thought_bus = get_thought_bus() if THOUGHT_BUS_AVAILABLE else None
        self.chirp_bus = get_chirp_bus() if CHIRP_BUS_AVAILABLE else None
        
        if self.thought_bus:
            self.logger.info("📡 Wired to ThoughtBus")
            
        if self.chirp_bus:
            self.logger.info("🐦 Wired to ChirpBus")
        
        # Volume thresholds for size classification
        self.WHALE_THRESHOLD = 1_000_000  # $1M+ volume
        self.SHARK_THRESHOLD = 100_000    # $100K+ volume
        self.MINNOW_THRESHOLD = 10_000    # $10K+ volume
        
        # Real-time data streams
        self.binance_trades: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alpaca_trades: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Connected clients
        self.clients: Set = set()
        
        # 🌐 GLOBAL MARKET CLIENTS - Direct access to all exchanges
        self.kraken_client: Optional[Any] = None
        self.binance_ws: Optional[Any] = None
        self.alpaca_client: Optional[Any] = None
        self.capital_client: Optional[Any] = None
        
        # Initialize market connections
        self._init_market_connections()
        
        # 🐦 CHIRP BUS - Emit bot detections to Orca
        self.chirp_bus = None
        if CHIRP_BUS_AVAILABLE and get_chirp_bus:
            try:
                self.chirp_bus = get_chirp_bus()
                self.logger.info("🐦 Ocean Wave Scanner → Orca CHIRP BUS connected")
            except Exception as e:
                self.logger.debug(f"Chirp bus init failed: {e}")
    
    def _init_market_connections(self):
        """Initialize connections to all global market feeds."""
        market_count = 0
        
        if KRAKEN_AVAILABLE:
            try:
                self.kraken_client = get_kraken_client()
                market_count += 1
                self.logger.info("🐙 Ocean Scanner → Kraken CONNECTED")
            except Exception as e:
                self.logger.debug(f"Kraken connection failed: {e}")
        
        if BINANCE_WS_AVAILABLE:
            try:
                self.binance_ws = BinanceWebSocketClient()
                if os.getenv('BINANCE_API_KEY'):
                    market_count += 1
                    self.logger.info("🟡 Ocean Scanner → Binance WS READY")
            except Exception as e:
                self.logger.debug(f"Binance WS connection failed: {e}")
        
        if ALPACA_AVAILABLE:
            try:
                self.alpaca_client = AlpacaClient()
                market_count += 1
                self.logger.info("🦙 Ocean Scanner → Alpaca CONNECTED")
            except Exception as e:
                self.logger.debug(f"Alpaca connection failed: {e}")
        
        if CAPITAL_AVAILABLE:
            try:
                self.capital_client = CapitalClient()
                if self.capital_client.is_authenticated():
                    market_count += 1
                    self.logger.info("💼 Ocean Scanner → Capital.com CONNECTED")
                else:
                    self.capital_client = None
            except Exception as e:
                self.logger.debug(f"Capital.com connection failed: {e}")
        
        if market_count > 0:
            self.logger.info(f"🌐 Ocean Scanner has {market_count} market feeds")
    
    def emit_bot_detection_to_orca(self, bot: BotProfile):
        """Emit whale/shark bot detection to Orca via chirp bus for wake riding."""
        if not self.chirp_bus or not bot:
            return
        
        # Only emit significant bots (sharks and whales)
        if bot.size_class not in ['whale', 'megalodon', 'shark']:
            return
        
        try:
            # Map bot volume to whale signal strength
            volume_usd = bot.total_volume
            side = 'buy' if bot.aggression > 0 else 'sell'
            
            self.chirp_bus.emit_signal(
                signal_type='BOT_WHALE_DETECTED',
                symbol=bot.symbol,
                coherence=min(1.0, bot.coordination),
                confidence=bot.owner_confidence,
                frequency=880.0 if side == 'buy' else 1760.0,
                amplitude=min(1.0, volume_usd / 1_000_000),
                metadata={
                    'bot_id': bot.bot_id,
                    'size_class': bot.size_class,
                    'owner': bot.owner,
                    'firm_id': bot.firm_id,
                    'pattern': bot.pattern,
                    'exchange': bot.exchange
                }
            )

            # 📡 THOUGHT EMISSION - Neural Persistence
            if hasattr(self, 'thought_bus') and self.thought_bus:
                try:
                    thought = Thought(
                        source="ocean_wave_scanner",
                        topic=f"bot.{bot.size_class}",
                        payload={
                            "symbol": bot.symbol,
                            "bot_id": bot.bot_id,
                            "size_class": bot.size_class,
                            "aggression": bot.aggression,
                            "owner": bot.owner,
                            "firm_id": bot.firm_id,
                            "timestamp": time.time()
                        }
                    )
                    self.thought_bus.publish(thought)
                except Exception:
                    pass

            self.logger.info(f"🐋→🦈 Bot {bot.size_class.upper()} detected: {bot.symbol} on {bot.exchange} (${volume_usd:,.0f})")
        except Exception as e:
            self.logger.debug(f"Failed to emit bot to Orca: {e}")
        
        # 🐦 CHIRP BUS - Emit bot detections to Orca
        self.chirp_bus = None
        if CHIRP_BUS_AVAILABLE and get_chirp_bus:
            try:
                self.chirp_bus = get_chirp_bus()
                self.logger.info("🐦 Ocean Wave Scanner → Orca CHIRP BUS connected")
            except Exception as e:
                self.logger.debug(f"Chirp bus init failed: {e}")
        
    async def scan_binance_stream(self, symbols: List[str]):
        """
        Connect to Binance WebSocket for multiple symbols.
        """
        # Binance allows subscribing to multiple streams
        streams = [f"{s.lower()}@trade" for s in symbols[:20]]  # Batch of 20
        url = f"wss://stream.binance.com/stream?streams={'/'.join(streams)}"
        
        self.logger.info(f"🌊 Connecting to Binance stream: {len(streams)} pairs")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url) as ws:
                    self.logger.info(f"✅ Binance connected: {len(streams)} streams")
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            await self.process_binance_trade(data)
                            
        except Exception as e:
            self.logger.error(f"Binance error: {e}")
            await asyncio.sleep(5)
            await self.scan_binance_stream(symbols)
    
    async def process_binance_trade(self, data: Dict):
        """Process Binance trade and detect bot patterns."""
        if "data" not in data:
            return
        
        trade = data["data"]
        symbol = trade.get("s", "").upper()
        
        # Store trade
        self.binance_trades[symbol].append({
            "price": float(trade.get("p", 0)),
            "quantity": float(trade.get("q", 0)),
            "time": trade.get("T", time.time() * 1000) / 1000,
            "is_buyer_maker": trade.get("m", False),
        })
        
        # Analyze for bot patterns
        await self.analyze_symbol(symbol, "binance")
    
    async def analyze_symbol(self, symbol: str, exchange: str):
        """
        Analyze recent trades for bot patterns.
        Detect bots, classify size, identify hives.
        """
        # Get recent trades
        if exchange == "binance":
            trades = list(self.binance_trades.get(symbol, []))
        else:
            trades = list(self.alpaca_trades.get(symbol, []))
        
        if len(trades) < 50:
            return  # Need more data
        
        # Bot detection patterns
        detected_bots = self._detect_bots_in_trades(trades, symbol, exchange)
        
        for bot_data in detected_bots:
            await self.register_bot(bot_data)
    
    def _detect_bots_in_trades(self, trades: List[Dict], symbol: str, exchange: str) -> List[Dict]:
        """
        Detect bot patterns in trade data.
        
        Returns list of detected bots with their characteristics.
        """
        detected = []
        
        # Pattern 1: Rapid-fire trades (HFT)
        times = [t["time"] for t in trades[-100:]]
        if len(times) > 10:
            time_diffs = np.diff(times)
            if np.mean(time_diffs) < 0.1:  # Trades every 100ms
                detected.append({
                    "pattern": "hft",
                    "symbol": symbol,
                    "exchange": exchange,
                    "trades": trades[-100:],
                    "frequency": 1 / np.mean(time_diffs) if np.mean(time_diffs) > 0 else 0,
                })
        
        # Pattern 2: Large volume bursts (Whale)
        volumes = [t["price"] * t["quantity"] for t in trades[-50:]]
        if volumes:
            avg_volume = np.mean(volumes)
            max_volume = max(volumes)
            if max_volume > avg_volume * 10:  # 10x average = whale
                detected.append({
                    "pattern": "whale",
                    "symbol": symbol,
                    "exchange": exchange,
                    "trades": [t for t in trades[-50:] if t["price"] * t["quantity"] > avg_volume * 3],
                    "total_volume": sum(volumes),
                })
        
        # Pattern 3: Coordinated trading (Hive detection)
        # Look for multiple similar-sized trades at regular intervals
        sizes = [t["quantity"] for t in trades[-50:]]
        if len(sizes) > 10:
            size_variance = np.std(sizes) / (np.mean(sizes) + 1e-9)
            if size_variance < 0.2:  # Low variance = coordinated
                detected.append({
                    "pattern": "coordinated",
                    "symbol": symbol,
                    "exchange": exchange,
                    "trades": trades[-50:],
                    "coordination_score": 1.0 - size_variance,
                })
        
        # Pattern 4: Market making (tight bid-ask)
        buy_trades = [t for t in trades[-50:] if not t["is_buyer_maker"]]
        sell_trades = [t for t in trades[-50:] if t["is_buyer_maker"]]
        if len(buy_trades) > 5 and len(sell_trades) > 5:
            if abs(len(buy_trades) - len(sell_trades)) < 5:  # Balanced
                detected.append({
                    "pattern": "market_maker",
                    "symbol": symbol,
                    "exchange": exchange,
                    "trades": trades[-50:],
                })
        
        # Pattern 5: Scalping (small profits, high frequency)
        prices = [t["price"] for t in trades[-30:]]
        if len(prices) > 20:
            price_changes = np.diff(prices)
            small_moves = sum(1 for p in price_changes if abs(p) < np.mean(prices) * 0.001)
            if small_moves > len(price_changes) * 0.8:  # 80% small moves
                detected.append({
                    "pattern": "scalper",
                    "symbol": symbol,
                    "exchange": exchange,
                    "trades": trades[-30:],
                })
        
        return detected
    
    async def register_bot(self, bot_data: Dict):
        """Register or update a bot."""
        import hashlib
        
        symbol = bot_data["symbol"]
        exchange = bot_data["exchange"]
        pattern = bot_data["pattern"]

        # Generate bot ID
        bot_signature = f"{exchange}_{symbol}_{pattern}_{time.time()}"
        bot_id = hashlib.md5(bot_signature.encode()).hexdigest()[:12]
        
        if bot_id not in self.bots:
            # Calculate volume
            trades = bot_data.get("trades", [])
            total_volume = sum(t["price"] * t["quantity"] for t in trades)
            
            # Classify size
            if total_volume > self.WHALE_THRESHOLD:
                size_class = "megalodon"
            elif total_volume > self.SHARK_THRESHOLD:
                size_class = "whale"
            elif total_volume > self.MINNOW_THRESHOLD:
                size_class = "shark"
            else:
                size_class = "minnow"
            
            bot = BotProfile(
                bot_id=bot_id,
                symbol=symbol,
                exchange=exchange,
                pattern=pattern,
                size_class=size_class,
                total_volume=total_volume,
                trade_count=len(trades),
                avg_trade_size=total_volume / len(trades) if trades else 0,
                first_seen=time.time(),
                last_seen=time.time(),
            )
            
            self.bots[bot_id] = bot
            
            # Profile the bot for ownership identification
            if self.profiler:
                try:
                    bot_data_for_profiler = {
                        'bot_id': bot_id,
                        'symbol': symbol,
                        'exchange': exchange,
                        'pattern': pattern,
                        'size_class': bot.size_class,
                        'trade_count': len(trades),
                        'total_volume_usd': total_volume,
                        'time_window_seconds': 1.0,
                        'trade_sizes': [t.get('volume_usd', 0) for t in trades],
                        'buy_count': sum(1 for t in trades if t.get('is_buyer', False)),
                        'sell_count': sum(1 for t in trades if not t.get('is_buyer', True)),
                        'latency_ms': 1.0,  # Estimate
                    }
                    profile = self.profiler.profile_bot(bot_data_for_profiler)
                    
                    # Update bot with ownership info
                    bot.owner = profile.owner_name
                    bot.owner_confidence = profile.owner_confidence
                    bot.firm_id = profile.likely_owner
                    
                    if profile.owner_confidence > 0.5:
                        self.logger.info(f"   🏢 Likely owner: {profile.owner_name} ({profile.owner_confidence:.0%} confidence)")
                except Exception as e:
                    self.logger.debug(f"Profiler error: {e}")
            
            # Check for hive membership
            await self.detect_hive_affiliation(bot)
            
            # Emit significant bots to Orca for whale wake riding
            self.emit_bot_detection_to_orca(bot)
            
            # Broadcast discovery
            await self.broadcast_bot_discovery(bot)
            
            self.logger.info(f"🤖 Bot detected: {bot.size_class.upper()} {bot.pattern} on {bot.symbol} (${total_volume:,.0f})")
        else:
            # Update existing bot
            bot = self.bots[bot_id]
            bot.last_seen = time.time()
            bot.trade_count += len(bot_data.get("trades", []))
    
    async def detect_hive_affiliation(self, bot: BotProfile):
        """
        Detect if bot belongs to a hive.
        Whales become hive leaders, smaller bots become followers.
        """
        # If whale or megalodon, make it a hive leader
        if bot.size_class in ["whale", "megalodon"]:
            hive_id = f"hive_{bot.bot_id}"
            hive = BotHive(
                hive_id=hive_id,
                leader_id=bot.bot_id,
                strategy=bot.pattern,
            )
            hive.member_ids.add(bot.bot_id)
            self.hives[hive_id] = hive
            
            bot.hive_id = hive_id
            bot.is_leader = True
            
            self.logger.info(f"🏰 Hive created: {hive_id} led by {bot.bot_id}")
        
        # If minnow/shark, try to join existing hive
        elif bot.size_class in ["minnow", "shark"]:
            # Find hives with same pattern and symbol
            for hive in self.hives.values():
                leader = self.bots.get(hive.leader_id)
                if leader and leader.symbol == bot.symbol and leader.pattern == bot.pattern:
                    # Join this hive
                    hive.member_ids.add(bot.bot_id)
                    bot.hive_id = hive.hive_id
                    bot.following = hive.leader_id
                    
                    leader.followers.add(bot.bot_id)
                    
                    self.logger.info(f"🐟 Bot {bot.bot_id} joined hive {hive.hive_id}")
                    break
    
    async def detect_battles(self):
        """
        Detect when hives/bots are battling each other.
        
        Battle indicators:
        - Opposite patterns (buyers vs sellers)
        - Same symbol, different strategies
        - High aggression scores
        """
        battles = []
        
        # Group bots by symbol
        by_symbol = defaultdict(list)
        for bot in self.bots.values():
            by_symbol[bot.symbol].append(bot)
        
        for symbol, bots in by_symbol.items():
            if len(bots) < 2:
                continue
            
            # Look for opposing strategies
            buyers = [b for b in bots if "market_maker" in b.pattern or "buyer" in b.pattern]
            sellers = [b for b in bots if "seller" in b.pattern or "short" in b.pattern]
            
            if buyers and sellers:
                battles.append({
                    "symbol": symbol,
                    "buyers": buyers,
                    "sellers": sellers,
                    "intensity": len(buyers) + len(sellers),
                })
        
        return battles
    
    async def broadcast_bot_discovery(self, bot: BotProfile):
        """Broadcast bot discovery to connected clients."""
        if self.clients:
            message = {
                "type": "bot_discovered",
                "bot": {
                    "bot_id": bot.bot_id,
                    "symbol": bot.symbol,
                    "exchange": bot.exchange,
                    "pattern": bot.pattern,
                    "size_class": bot.size_class,
                    "volume": bot.total_volume,
                    "hive_id": bot.hive_id,
                    "is_leader": bot.is_leader,
                    "follower_count": len(bot.followers),
                }
            }
            
            msg_str = json.dumps(message)
            for client in list(self.clients):
                try:
                    await client.send_str(msg_str)
                except:
                    self.clients.discard(client)
    
    async def broadcast_ocean_overview(self):
        """Broadcast complete ocean overview every 10 seconds."""
        while True:
            await asyncio.sleep(10)
            
            if not self.clients:
                continue
            
            # Count by size class
            size_counts = defaultdict(int)
            for bot in self.bots.values():
                size_counts[bot.size_class] += 1
            
            # Detect battles
            battles = await self.detect_battles()
            
            overview = {
                "type": "ocean_overview",
                "stats": {
                    "total_bots": len(self.bots),
                    "total_hives": len(self.hives),
                    "megalodons": size_counts["megalodon"],
                    "whales": size_counts["whale"],
                    "sharks": size_counts["shark"],
                    "minnows": size_counts["minnow"],
                    "active_battles": len(battles),
                },
                "hives": [
                    {
                        "hive_id": hive.hive_id,
                        "leader": hive.leader_id,
                        "members": len(hive.member_ids),
                        "strategy": hive.strategy,
                        "mode": hive.mode,
                    }
                    for hive in list(self.hives.values())[:20]
                ],
                "battles": battles[:10],
            }
            
            msg_str = json.dumps(overview)
            for client in list(self.clients):
                try:
                    await client.send_str(msg_str)
                except:
                    self.clients.discard(client)
    
    async def run(self):
        """Run the ocean scanner."""
        # Start multiple Binance streams (batches of 20 symbols)
        tasks = []
        for i in range(0, len(CRYPTO_PAIRS), 20):
            batch = CRYPTO_PAIRS[i:i+20]
            tasks.append(self.scan_binance_stream(batch))
        
        # Start overview broadcaster
        tasks.append(self.broadcast_ocean_overview())
        
        await asyncio.gather(*tasks)

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    print("🌊" + "="*78 + "🌊")
    print("         AUREON OCEAN WAVE SCANNER - SCANNING THE ENTIRE OCEAN")
    print("🌊" + "="*78 + "🌊")
    print(f"\n📊 Scanning:")
    print(f"   • {len(CRYPTO_PAIRS)} crypto pairs")
    print(f"   • {len(STOCK_SYMBOLS)} stocks")
    print(f"   • Multiple exchanges (Binance, Kraken, Alpaca)")
    print(f"\n🔍 Detecting:")
    print(f"   🐋 WHALES - Big bots ($1M+ volume)")
    print(f"   🦈 SHARKS - Medium bots ($100K+ volume)")  
    print(f"   🐟 MINNOWS - Small bots ($10K+ volume)")
    print(f"   🏰 HIVES - Coordinated bot armies")
    print(f"   ⚔️  BATTLES - Bots hunting each other")
    print("="*80 + "\n")
    
    scanner = OceanWaveScanner()
    await scanner.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🌊 Ocean scanner stopped")
