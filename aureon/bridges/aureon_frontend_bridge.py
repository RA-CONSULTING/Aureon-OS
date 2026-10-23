#!/usr/bin/env python3
"""
🌉 AUREON FRONTEND BRIDGE 🌉
============================

Collects data from ALL trading platforms and ALL systems,
then streams it to the frontend via WebSocket.

DATA SOURCES:
  📊 EXCHANGES:
    - Kraken (crypto)
    - Binance (crypto)
    - Alpaca (crypto + stocks)
    - Capital.com (CFDs)

  🧠 SYSTEMS:
    - V14 Labyrinth (100% win rate scoring)
    - Mycelium Conversion Hub (10 systems, 90 pathways)
    - Conversion Commando (Falcon/Tortoise/Chameleon/Bee)
    - Probability Nexus (80%+ win rate)
    - Internal Multiverse (10 worlds)
    - Miner Brain (cognitive intelligence)
    - Harmonic Fusion (wave patterns)
    - Omega (high confidence signals)

FRONTEND OUTPUT:
  - ws://127.0.0.1:8787/command-stream (real-time data)
  - Supabase tables (persistent storage)

Gary Leckey | January 2026 | ALL PLATFORMS → FRONTEND
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import asyncio
import json
import os
import sys
import time
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("🔐 Environment loaded from .env")
except ImportError:
    print("⚠️ python-dotenv not installed")

try:
    import websockets
    from websockets.server import serve
except ImportError:
    websockets = None
    serve = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════
def bridge_bind() -> tuple[str, int]:
    """Match the UI sockets. Bind the loopback interface unless the operator overrides it."""

    host = os.getenv("NEXUS_WS_HOST", "127.0.0.1") or "127.0.0.1"
    raw = os.getenv("AUREON_FRONTEND_BRIDGE_PORT") or os.getenv("NEXUS_COMMAND_PORT") or "8787"
    try:
        port = int(raw)
    except (TypeError, ValueError):
        port = 8787
    return host, port


WS_HOST, WS_PORT = bridge_bind()
UPDATE_INTERVAL = float(os.getenv("NEXUS_UPDATE_INTERVAL", "1.0"))  # seconds

# ════════════════════════════════════════════════════════════════════════════
# EXCHANGE CLIENTS
# ════════════════════════════════════════════════════════════════════════════
print("\n🔌 LOADING EXCHANGE CLIENTS...")

# Kraken
try:
    from aureon.exchanges.kraken_client import KrakenClient
    def get_kraken_client():
        return KrakenClient()
    KRAKEN_AVAILABLE = True
    print("   🐙 Kraken Client: LOADED")
except ImportError as e:
    KRAKEN_AVAILABLE = False
    print(f"   ⚠️ Kraken Client: {e}")

# Binance
try:
    from aureon.exchanges.binance_client import BinanceClient
    def get_binance_client():
        return BinanceClient()
    BINANCE_AVAILABLE = True
    print("   🟡 Binance Client: LOADED")
except ImportError:
    BINANCE_AVAILABLE = False
    print("   ⚠️ Binance Client: Not available")

# Alpaca
try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_AVAILABLE = True
    print("   🦙 Alpaca Client: LOADED")
except ImportError:
    ALPACA_AVAILABLE = False
    print("   ⚠️ Alpaca Client: Not available")

# ════════════════════════════════════════════════════════════════════════════
# TRADING SYSTEMS
# ════════════════════════════════════════════════════════════════════════════
print("\n🧠 LOADING TRADING SYSTEMS...")

# Mycelium Conversion Hub
try:
    from aureon.conversion.mycelium_conversion_hub import get_conversion_hub, MyceliumConversionHub
    MYCELIUM_AVAILABLE = True
    print("   🍄 Mycelium Conversion Hub: LOADED")
except ImportError:
    MYCELIUM_AVAILABLE = False
    print("   ⚠️ Mycelium Hub: Not available")

# V14 Labyrinth
try:
    from aureon.strategies.s5_v14_labyrinth import V14DanceEnhancer, V14_CONFIG
    V14_AVAILABLE = True
    print("   🏆 V14 Labyrinth: LOADED")
except ImportError:
    V14_AVAILABLE = False
    print("   ⚠️ V14 Labyrinth: Not available")

# Conversion Commando
try:
    from aureon.conversion.aureon_conversion_commando import AdaptiveConversionCommando, PairScanner
    COMMANDO_AVAILABLE = True
    print("   🦅 Conversion Commando: LOADED")
except ImportError:
    COMMANDO_AVAILABLE = False
    print("   ⚠️ Conversion Commando: Not available")

# Probability Nexus
try:
    from aureon.bridges.aureon_probability_nexus import EnhancedProbabilityNexus
    NEXUS_AVAILABLE = True
    print("   🔮 Probability Nexus: LOADED")
except ImportError:
    NEXUS_AVAILABLE = False
    print("   ⚠️ Probability Nexus: Not available")

# Internal Multiverse — simulated 10 worlds × $10.
# The import and the LOADED line run only when AUREON_SIMULATED_BOOT is on.
MULTIVERSE_AVAILABLE = False
InternalMultiverse = None
try:
    from aureon.core.simulated_boot import INTERNAL_MULTIVERSE, take_simulated
    if take_simulated(INTERNAL_MULTIVERSE, "aureon.simulation, 10 worlds × $10"):
        from aureon.simulation.aureon_internal_multiverse import InternalMultiverse
        MULTIVERSE_AVAILABLE = True
        print("   🌌 Internal Multiverse: LOADED")
except ImportError:
    MULTIVERSE_AVAILABLE = False
    InternalMultiverse = None
    print("   ⚠️ Internal Multiverse: Not available")

# Miner Brain
try:
    from aureon.utils.aureon_miner_brain import MinerBrain
    MINER_AVAILABLE = True
    print("   🧠 Miner Brain: LOADED")
except ImportError:
    MINER_AVAILABLE = False
    print("   ⚠️ Miner Brain: Not available")

# Harmonic Fusion
try:
    from aureon.harmonic.aureon_harmonic_fusion import HarmonicWaveFusion
    HARMONIC_AVAILABLE = True
    print("   🌊 Harmonic Fusion: LOADED")
except ImportError:
    HARMONIC_AVAILABLE = False
    print("   ⚠️ Harmonic Fusion: Not available")

# Omega
try:
    from aureon.trading.aureon_omega import Omega
    OMEGA_AVAILABLE = True
    print("   🔱 Omega: LOADED")
except ImportError:
    OMEGA_AVAILABLE = False
    print("   ⚠️ Omega: Not available")

print()


# ════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class ExchangeData:
    """Data from a single exchange."""
    name: str
    connected: bool = False
    balances: Dict[str, float] = field(default_factory=dict)
    total_value_usd: float = 0.0
    positions: List[Dict] = field(default_factory=list)
    tickers: Dict[str, Dict] = field(default_factory=dict)
    last_update: float = 0.0
    error: Optional[str] = None


@dataclass
class SystemSignal:
    """Signal from a trading system."""
    system: str
    signal_type: str  # BUY, SELL, CONVERT, HOLD
    symbol: str
    confidence: float
    score: float
    reason: str
    timestamp: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class FrontendPayload:
    """Complete payload for frontend."""
    timestamp: float
    
    # Exchange data
    exchanges: Dict[str, Dict] = field(default_factory=dict)
    total_portfolio_value: float = 0.0
    
    # All balances combined
    all_balances: Dict[str, Dict] = field(default_factory=dict)  # asset -> {exchange: amount}
    
    # Signals from all systems
    signals: List[Dict] = field(default_factory=list)
    signal_count: int = 0
    
    # System status
    systems_online: List[str] = field(default_factory=list)
    systems_offline: List[str] = field(default_factory=list)
    
    # Market overview
    top_movers: List[Dict] = field(default_factory=list)
    opportunities: List[Dict] = field(default_factory=list)


# ════════════════════════════════════════════════════════════════════════════
# FRONTEND BRIDGE
# ════════════════════════════════════════════════════════════════════════════

class AureonFrontendBridge:
    """
    Bridges ALL exchange data and system signals to the frontend.
    """
    
    def __init__(self):
        self.running = False
        self.clients: set = set()
        
        # Exchange clients
        self.kraken = None
        self.binance = None
        self.alpaca = None
        
        # Trading systems
        self.hub = None
        self.v14 = None
        self.commando = None
        self.nexus = None
        self.multiverse = None
        self.miner = None
        self.harmonic = None
        self.omega = None
        self.scanner = None
        
        # Data cache
        self.exchange_data: Dict[str, ExchangeData] = {}
        self.all_signals: List[SystemSignal] = []
        self.ticker_cache: Dict[str, Dict] = {}
        self.prices: Dict[str, float] = {}
        
        # Stats
        self.updates_sent = 0
        self.errors = 0
    
    async def initialize(self):
        """Initialize all connections."""
        print("\n" + "=" * 70)
        print("🌉 INITIALIZING AUREON FRONTEND BRIDGE")
        print("=" * 70)
        
        # ════════════════════════════════════════════════════════════════
        # EXCHANGE CLIENTS
        # ════════════════════════════════════════════════════════════════
        print("\n📊 CONNECTING TO EXCHANGES...")
        
        if KRAKEN_AVAILABLE:
            try:
                self.kraken = get_kraken_client()
                self.exchange_data['kraken'] = ExchangeData(name='kraken', connected=True)
                print("   🐙 Kraken: CONNECTED")
            except Exception as e:
                print(f"   ❌ Kraken error: {e}")
        
        if BINANCE_AVAILABLE:
            try:
                self.binance = get_binance_client()
                self.exchange_data['binance'] = ExchangeData(name='binance', connected=True)
                print("   🟡 Binance: CONNECTED")
            except Exception as e:
                print(f"   ❌ Binance error: {e}")
        
        if ALPACA_AVAILABLE:
            try:
                self.alpaca = AlpacaClient()
                self.exchange_data['alpaca'] = ExchangeData(name='alpaca', connected=True)
                print("   🦙 Alpaca: CONNECTED")
            except Exception as e:
                print(f"   ❌ Alpaca error: {e}")
        
        # ════════════════════════════════════════════════════════════════
        # TRADING SYSTEMS
        # ════════════════════════════════════════════════════════════════
        print("\n🧠 INITIALIZING TRADING SYSTEMS...")
        
        if MYCELIUM_AVAILABLE:
            try:
                self.hub = get_conversion_hub()
                print("   🍄 Mycelium Hub: WIRED")
            except Exception as e:
                print(f"   ⚠️ Mycelium error: {e}")
        
        if V14_AVAILABLE:
            try:
                self.v14 = V14DanceEnhancer()
                print("   🏆 V14 Scoring: WIRED")
            except Exception as e:
                print(f"   ⚠️ V14 error: {e}")
        
        if COMMANDO_AVAILABLE:
            try:
                self.commando = AdaptiveConversionCommando()
                self.scanner = PairScanner()
                print("   🦅 Conversion Commando: WIRED")
            except Exception as e:
                print(f"   ⚠️ Commando error: {e}")
        
        if NEXUS_AVAILABLE:
            try:
                self.nexus = EnhancedProbabilityNexus()
                print("   🔮 Probability Nexus: WIRED")
            except Exception as e:
                print(f"   ⚠️ Nexus error: {e}")
        
        if MULTIVERSE_AVAILABLE:
            try:
                self.multiverse = InternalMultiverse()
                print("   🌌 Internal Multiverse: WIRED")
            except Exception as e:
                print(f"   ⚠️ Multiverse error: {e}")
        
        if MINER_AVAILABLE:
            try:
                self.miner = MinerBrain()
                print("   🧠 Miner Brain: WIRED")
            except Exception as e:
                print(f"   ⚠️ Miner error: {e}")
        
        if HARMONIC_AVAILABLE:
            try:
                self.harmonic = HarmonicWaveFusion()
                print("   🌊 Harmonic Fusion: WIRED")
            except Exception as e:
                print(f"   ⚠️ Harmonic error: {e}")
        
        if OMEGA_AVAILABLE:
            try:
                self.omega = Omega()
                print("   🔱 Omega: WIRED")
            except Exception as e:
                print(f"   ⚠️ Omega error: {e}")
        
        print("\n" + "=" * 70)
        print(f"✅ Bridge initialized!")
        print(f"   Exchanges: {len(self.exchange_data)}")
        print(f"   Systems: {sum([1 for x in [self.hub, self.v14, self.commando, self.nexus, self.multiverse, self.miner, self.harmonic, self.omega] if x])}")
        print("=" * 70)
    
    async def fetch_kraken_data(self) -> ExchangeData:
        """Fetch all data from Kraken."""
        data = self.exchange_data.get('kraken', ExchangeData(name='kraken'))
        
        if not self.kraken:
            data.error = "Client not available"
            return data
        
        try:
            # Get all balances using get_account_balance()
            if hasattr(self.kraken, 'get_account_balance'):
                balances = self.kraken.get_account_balance() or {}
            else:
                balances = {}
            
            # Clean and store balances
            data.balances = {}
            for asset, amount in balances.items():
                try:
                    amount = float(amount)
                    if amount > 0:
                        # Clean Kraken naming
                        clean = asset
                        if len(asset) == 4 and asset[0] in ('X', 'Z'):
                            clean = asset[1:]
                        if clean == 'XBT':
                            clean = 'BTC'
                        data.balances[clean] = amount
                except:
                    pass
            
            # Get tickers
            if hasattr(self.kraken, 'get_all_tickers'):
                tickers = self.kraken.get_all_tickers() or {}
                data.tickers = {}
                for symbol, ticker in tickers.items():
                    if isinstance(ticker, dict):
                        try:
                            price = float(ticker.get('c', [0])[0]) if isinstance(ticker.get('c'), list) else 0
                            if price > 0:
                                data.tickers[symbol] = {
                                    'price': price,
                                    'volume': float(ticker.get('v', [0])[0]) if isinstance(ticker.get('v'), list) else 0,
                                    'change': float(ticker.get('p', [0, 0])[1]) if isinstance(ticker.get('p'), list) else 0,
                                }
                                # Extract base asset price
                                for quote in ['USD', 'USDT', 'GBP']:
                                    if symbol.endswith(quote):
                                        base = symbol.replace(quote, '').lstrip('XZ')
                                        if base == 'XBT':
                                            base = 'BTC'
                                        self.prices[base] = price
                                        break
                        except:
                            pass
            
            # Calculate total value
            data.total_value_usd = sum(
                data.balances.get(asset, 0) * self.prices.get(asset, 0)
                for asset in data.balances
            )
            
            data.connected = True
            data.last_update = time.time()
            data.error = None
            
        except Exception as e:
            data.error = str(e)
            logger.error(f"Kraken fetch error: {e}")
        
        return data
    
    async def fetch_binance_data(self) -> ExchangeData:
        """Fetch all data from Binance."""
        data = self.exchange_data.get('binance', ExchangeData(name='binance'))
        
        if not self.binance:
            data.error = "Client not available"
            return data
        
        try:
            # Get balances
            if hasattr(self.binance, 'get_balance'):
                balances = self.binance.get_balance() or {}
                data.balances = {k: float(v) for k, v in balances.items() if float(v) > 0}
            
            # Get tickers
            if hasattr(self.binance, 'get_all_tickers'):
                tickers = self.binance.get_all_tickers() or {}
                data.tickers = tickers
                for symbol, price in tickers.items():
                    for quote in ['USDT', 'USD', 'BUSD']:
                        if symbol.endswith(quote):
                            base = symbol.replace(quote, '')
                            self.prices[base] = float(price) if isinstance(price, (int, float, str)) else 0
                            break
            
            # Calculate total value
            data.total_value_usd = sum(
                data.balances.get(asset, 0) * self.prices.get(asset, 0)
                for asset in data.balances
            )
            
            data.connected = True
            data.last_update = time.time()
            data.error = None
            
        except Exception as e:
            data.error = str(e)
            logger.error(f"Binance fetch error: {e}")
        
        return data
    
    async def fetch_alpaca_data(self) -> ExchangeData:
        """Fetch all data from Alpaca."""
        data = self.exchange_data.get('alpaca', ExchangeData(name='alpaca'))
        
        if not self.alpaca:
            data.error = "Client not available"
            return data
        
        try:
            # Get account
            if hasattr(self.alpaca, 'get_account'):
                account = self.alpaca.get_account()
                if account:
                    data.total_value_usd = float(account.get('portfolio_value', 0))
                    data.balances['USD'] = float(account.get('cash', 0))
            
            # Get positions
            if hasattr(self.alpaca, 'get_positions'):
                positions = self.alpaca.get_positions() or []
                data.positions = positions
                for pos in positions:
                    symbol = pos.get('symbol', '')
                    qty = float(pos.get('qty', 0))
                    if qty > 0:
                        data.balances[symbol] = qty
            
            data.connected = True
            data.last_update = time.time()
            data.error = None
            
        except Exception as e:
            data.error = str(e)
            logger.error(f"Alpaca fetch error: {e}")
        
        return data
    
    async def collect_signals(self) -> List[SystemSignal]:
        """Collect signals from all trading systems."""
        signals = []
        now = time.time()
        
        # ════════════════════════════════════════════════════════════════
        # V14 SIGNALS
        # ════════════════════════════════════════════════════════════════
        if self.v14:
            try:
                if hasattr(self.v14, 'get_scores'):
                    scores = self.v14.get_scores(self.ticker_cache)
                    for symbol, score in scores.items():
                        if score >= 6:  # Lower threshold for visibility
                            signals.append(SystemSignal(
                                system='V14',
                                signal_type='CONVERT' if score >= 8 else 'WATCH',
                                symbol=symbol,
                                confidence=score / 10.0,
                                score=score,
                                reason=f"V14 Score: {score}/10",
                                timestamp=now,
                            ))
            except Exception as e:
                logger.debug(f"V14 signal error: {e}")
        
        # ════════════════════════════════════════════════════════════════
        # MYCELIUM HUB SIGNALS
        # ════════════════════════════════════════════════════════════════
        if self.hub:
            try:
                if hasattr(self.hub, 'get_all_signals'):
                    hub_signals = self.hub.get_all_signals() or []
                    for sig in hub_signals:
                        signals.append(SystemSignal(
                            system='Mycelium',
                            signal_type=sig.get('type', 'UNKNOWN'),
                            symbol=sig.get('symbol', ''),
                            confidence=sig.get('confidence', 0),
                            score=sig.get('score', 0),
                            reason=sig.get('reason', ''),
                            timestamp=now,
                            metadata=sig,
                        ))
            except Exception as e:
                logger.debug(f"Mycelium signal error: {e}")
        
        # ════════════════════════════════════════════════════════════════
        # COMMANDO SIGNALS
        # ════════════════════════════════════════════════════════════════
        if self.commando:
            try:
                if hasattr(self.commando, 'scan_all_opportunities'):
                    opps = self.commando.scan_all_opportunities(self.ticker_cache) or []
                    for opp in opps:
                        signals.append(SystemSignal(
                            system='Commando',
                            signal_type=opp.get('type', 'CONVERT'),
                            symbol=opp.get('symbol', ''),
                            confidence=opp.get('confidence', 0),
                            score=opp.get('score', 0),
                            reason=opp.get('reason', ''),
                            timestamp=now,
                            metadata=opp,
                        ))
            except Exception as e:
                logger.debug(f"Commando signal error: {e}")
        
        # ════════════════════════════════════════════════════════════════
        # PROBABILITY NEXUS SIGNALS
        # ════════════════════════════════════════════════════════════════
        if self.nexus:
            try:
                if hasattr(self.nexus, 'get_predictions'):
                    preds = self.nexus.get_predictions() or []
                    for pred in preds:
                        signals.append(SystemSignal(
                            system='Nexus',
                            signal_type='BUY' if pred.get('direction') == 'up' else 'SELL',
                            symbol=pred.get('symbol', ''),
                            confidence=pred.get('probability', 0),
                            score=pred.get('score', 0),
                            reason=f"Probability: {pred.get('probability', 0):.1%}",
                            timestamp=now,
                            metadata=pred,
                        ))
            except Exception as e:
                logger.debug(f"Nexus signal error: {e}")
        
        # ════════════════════════════════════════════════════════════════
        # MULTIVERSE CONSENSUS
        # ════════════════════════════════════════════════════════════════
        if self.multiverse:
            try:
                if hasattr(self.multiverse, 'get_consensus'):
                    consensus = self.multiverse.get_consensus() or []
                    for c in consensus:
                        signals.append(SystemSignal(
                            system='Multiverse',
                            signal_type=c.get('action', 'HOLD'),
                            symbol=c.get('symbol', ''),
                            confidence=c.get('confidence', 0),
                            score=c.get('worlds_agree', 0),
                            reason=f"{c.get('worlds_agree', 0)}/10 worlds agree",
                            timestamp=now,
                            metadata=c,
                        ))
            except Exception as e:
                logger.debug(f"Multiverse signal error: {e}")
        
        # ════════════════════════════════════════════════════════════════
        # MINER BRAIN SIGNALS
        # ════════════════════════════════════════════════════════════════
        if self.miner:
            try:
                if hasattr(self.miner, 'get_signals'):
                    brain_signals = self.miner.get_signals() or []
                    for sig in brain_signals:
                        signals.append(SystemSignal(
                            system='MinerBrain',
                            signal_type=sig.get('action', 'UNKNOWN'),
                            symbol=sig.get('symbol', ''),
                            confidence=sig.get('confidence', 0),
                            score=sig.get('score', 0),
                            reason=sig.get('reason', ''),
                            timestamp=now,
                            metadata=sig,
                        ))
            except Exception as e:
                logger.debug(f"MinerBrain signal error: {e}")
        
        # ════════════════════════════════════════════════════════════════
        # OMEGA HIGH CONFIDENCE
        # ════════════════════════════════════════════════════════════════
        if self.omega:
            try:
                if hasattr(self.omega, 'get_high_conf_signals'):
                    omega_signals = self.omega.get_high_conf_signals() or []
                    for sig in omega_signals:
                        signals.append(SystemSignal(
                            system='Omega',
                            signal_type=sig.get('action', 'UNKNOWN'),
                            symbol=sig.get('symbol', ''),
                            confidence=sig.get('confidence', 0.95),
                            score=sig.get('score', 9),
                            reason='High confidence signal',
                            timestamp=now,
                            metadata=sig,
                        ))
            except Exception as e:
                logger.debug(f"Omega signal error: {e}")
        
        self.all_signals = signals
        return signals
    
    async def build_payload(self) -> FrontendPayload:
        """Build complete payload for frontend."""
        payload = FrontendPayload(timestamp=time.time())
        
        # Fetch exchange data
        if self.kraken:
            self.exchange_data['kraken'] = await self.fetch_kraken_data()
        if self.binance:
            self.exchange_data['binance'] = await self.fetch_binance_data()
        if self.alpaca:
            self.exchange_data['alpaca'] = await self.fetch_alpaca_data()
        
        # Build exchange summary
        for name, data in self.exchange_data.items():
            payload.exchanges[name] = {
                'connected': data.connected,
                'total_value': data.total_value_usd,
                'balances': data.balances,
                'ticker_count': len(data.tickers),
                'last_update': data.last_update,
                'error': data.error,
            }
            payload.total_portfolio_value += data.total_value_usd
        
        # Combine all balances
        for name, data in self.exchange_data.items():
            for asset, amount in data.balances.items():
                if asset not in payload.all_balances:
                    payload.all_balances[asset] = {}
                payload.all_balances[asset][name] = amount
        
        # Collect signals
        signals = await self.collect_signals()
        payload.signals = [asdict(s) for s in signals]
        payload.signal_count = len(signals)
        
        # System status
        payload.systems_online = []
        payload.systems_offline = []
        
        systems = [
            ('V14', self.v14),
            ('Mycelium', self.hub),
            ('Commando', self.commando),
            ('Nexus', self.nexus),
            ('Multiverse', self.multiverse),
            ('MinerBrain', self.miner),
            ('Harmonic', self.harmonic),
            ('Omega', self.omega),
        ]
        
        for name, obj in systems:
            if obj:
                payload.systems_online.append(name)
            else:
                payload.systems_offline.append(name)
        
        # Top movers (from tickers)
        movers = []
        for name, data in self.exchange_data.items():
            for symbol, ticker in data.tickers.items():
                if isinstance(ticker, dict) and 'change' in ticker:
                    movers.append({
                        'symbol': symbol,
                        'exchange': name,
                        'change': ticker['change'],
                        'price': ticker.get('price', 0),
                    })
        
        movers.sort(key=lambda x: abs(x['change']), reverse=True)
        payload.top_movers = movers[:10]
        
        # Opportunities (high score signals)
        high_score_signals = [s for s in signals if s.score >= 7]
        payload.opportunities = [asdict(s) for s in high_score_signals[:10]]
        
        return payload
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        if not self.clients:
            return
        
        data = json.dumps(message)
        dead_clients = set()
        
        for client in self.clients:
            try:
                await client.send(data)
            except websockets.exceptions.ConnectionClosed:
                dead_clients.add(client)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                dead_clients.add(client)
        
        self.clients -= dead_clients
    
    async def handle_client(self, websocket, path):
        """Handle a WebSocket client connection."""
        self.clients.add(websocket)
        client_id = id(websocket)
        logger.info(f"🔌 Client {client_id} connected (total: {len(self.clients)})")
        
        try:
            # Send initial payload
            payload = await self.build_payload()
            await websocket.send(json.dumps({
                'type': 'initial_state',
                'payload': asdict(payload) if hasattr(payload, '__dataclass_fields__') else payload.__dict__,
            }))
            
            # Listen for commands
            async for message in websocket:
                try:
                    data = json.loads(message)
                    cmd = data.get('command', '')
                    
                    if cmd == 'refresh':
                        payload = await self.build_payload()
                        await websocket.send(json.dumps({
                            'type': 'refresh',
                            'payload': asdict(payload) if hasattr(payload, '__dataclass_fields__') else payload.__dict__,
                        }))
                    
                    elif cmd == 'get_signals':
                        signals = await self.collect_signals()
                        await websocket.send(json.dumps({
                            'type': 'signals',
                            'payload': [asdict(s) for s in signals],
                        }))
                    
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    logger.error(f"Command error: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            logger.info(f"🔌 Client {client_id} disconnected (total: {len(self.clients)})")
    
    async def stream_loop(self):
        """Main streaming loop - push updates to all clients."""
        while self.running:
            try:
                payload = await self.build_payload()
                
                await self.broadcast({
                    'type': 'stream_tick',
                    'payload': asdict(payload) if hasattr(payload, '__dataclass_fields__') else payload.__dict__,
                })
                
                self.updates_sent += 1
                
                if self.updates_sent % 60 == 0:
                    logger.info(f"📡 Updates sent: {self.updates_sent} | Clients: {len(self.clients)} | Signals: {len(self.all_signals)}")
                
            except Exception as e:
                self.errors += 1
                logger.error(f"Stream error: {e}")
            
            await asyncio.sleep(UPDATE_INTERVAL)
    
    async def run(self):
        """Run the frontend bridge server."""
        await self.initialize()
        
        self.running = True
        
        print(f"\n🌉 AUREON FRONTEND BRIDGE STARTING...")
        print(f"   WebSocket: ws://{WS_HOST}:{WS_PORT}/command-stream")
        print(f"   Update Interval: {UPDATE_INTERVAL}s")
        print()

        async def _http_health(path, _request_headers):
            if str(path).split("?", 1)[0] not in {"/health", "/healthz"}:
                return None
            body = json.dumps(
                {
                    "ok": True,
                    "service": "aureon-frontend-bridge",
                    "listening": True,
                    "live_trading": False,
                    "orders": 0,
                    "bind": WS_HOST,
                    "port": WS_PORT,
                }
            ).encode("utf-8")
            return (
                200,
                [("Content-Type", "application/json"), ("Content-Length", str(len(body)))],
                body,
            )

        # Start WebSocket server. GET /health answers the seat tab.
        async with serve(self.handle_client, WS_HOST, WS_PORT, process_request=_http_health):
            print(f"✅ WebSocket server running on ws://{WS_HOST}:{WS_PORT}")
            
            # Run stream loop
            await self.stream_loop()


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

async def main():
    bridge = AureonFrontendBridge()
    
    try:
        await bridge.run()
    except KeyboardInterrupt:
        print("\n\n⚠️ Shutting down...")
        bridge.running = False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🌉 AUREON FRONTEND BRIDGE 🌉")
    print("=" * 70)
    print("Streaming ALL exchange data and system signals to frontend")
    print("=" * 70)
    
    asyncio.run(main())
