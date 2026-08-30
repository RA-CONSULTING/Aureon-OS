#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                          ║
║     👑💰 AUREON QUEEN EXECUTE - MAKE THAT MONEY! 💰👑                                                    ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━              ║
║                                                                                                          ║
║     THE QUEEN'S EXECUTION ENGINE - UNIFIED HARMONIC MOMENTUM TRADING                                    ║
║                                                                                                          ║
║     "Scan → Validate → Execute → Profit"                                                                ║
║                                                                                                          ║
║     Aureon Creator | Aureon Trading System | January 2026                                                  ║
║                                                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import sys
import os
if sys.platform == 'win32':
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

import time
import json
import logging
import requests
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 💸 COST THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════════

ROUND_TRIP_COST_PCT = 0.34   # Total trading cost
MIN_TRADE_USD = 1.00          # Minimum trade size

# ═══════════════════════════════════════════════════════════════════════════════
# 🔌 IMPORT HARMONIC MOMENTUM SCANNER
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from aureon_harmonic_momentum_wave import HarmonicMomentumWaveScanner, HarmonicMomentumSignal
    SCANNER_OK = True
except ImportError:
    SCANNER_OK = False
    print("❌ Cannot import HarmonicMomentumWaveScanner")


# ═══════════════════════════════════════════════════════════════════════════════
# 💰 MULTI-EXCHANGE EXECUTION CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

# Import Kraken client
try:
    from kraken_client import KrakenClient, get_kraken_client
    KRAKEN_OK = True
except ImportError:
    KRAKEN_OK = False
    KrakenClient = None

# ═══════════════════════════════════════════════════════════════════════════════
# 🏹⚔️ APACHE WAR BAND INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from aureon_war_band_enhanced import EnhancedWarBand, UnifiedEnhancementSignal
    WAR_BAND_OK = True
except ImportError:
    WAR_BAND_OK = False
    EnhancedWarBand = None

try:
    from queen_loss_learning import QueenLossLearningSystem
    LOSS_LEARNING_OK = True
except ImportError:
    LOSS_LEARNING_OK = False
    QueenLossLearningSystem = None

try:
    from aureon_mycelium import MyceliumNetwork
    MYCELIUM_OK = True
except ImportError:
    MYCELIUM_OK = False
    MyceliumNetwork = None

try:
    from aureon_market_pulse import MarketPulse
    MARKET_PULSE_OK = True
except ImportError:
    MARKET_PULSE_OK = False
    MarketPulse = None

try:
    from unified_exchange_client import MultiExchangeClient
    UNIFIED_CLIENT_OK = True
except ImportError:
    UNIFIED_CLIENT_OK = False
    MultiExchangeClient = None

# ═══════════════════════════════════════════════════════════════════════════════
# 🌈 RAINBOW BRIDGE - Emotional Frequency Trading
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from rainbow_bridge import RainbowBridge, EMOTIONAL_FREQUENCIES, THE_VOW
    RAINBOW_OK = True
except ImportError:
    RAINBOW_OK = False
    RainbowBridge = None

# ═══════════════════════════════════════════════════════════════════════════════
# 📚 WISDOM & KNOWLEDGE SYSTEMS - Ancient Civilization Learning
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from aureon_wisdom_scanner import AureonWisdomScanner, ScannerConfig
    WISDOM_SCANNER_OK = True
except ImportError:
    WISDOM_SCANNER_OK = False
    AureonWisdomScanner = None

try:
    from bhoys_wisdom import get_victory_quote, get_patience_wisdom, get_resilience_message, BHOYS_WISDOM
    BHOYS_WISDOM_OK = True
except ImportError:
    BHOYS_WISDOM_OK = False
    BHOYS_WISDOM = None

# ═══════════════════════════════════════════════════════════════════════════════
# ⚡🧬 HIGH FREQUENCY TRADING - HARMONIC MYCELIUM ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from aureon_hft_harmonic_mycelium import get_hft_engine, HFTHarmonicEngine
    HFT_ENGINE_AVAILABLE = True
except ImportError as e:
    HFT_ENGINE_AVAILABLE = False
    get_hft_engine = None
    HFTHarmonicEngine = None
    print(f"⚠️ HFT Engine not available: {e}")

try:
    from aureon_hft_websocket_order_router import get_order_router, HFTOrderRouter
    HFT_ORDER_ROUTER_AVAILABLE = True
except ImportError as e:
    HFT_ORDER_ROUTER_AVAILABLE = False
    get_order_router = None
    HFTOrderRouter = None
    print(f"⚠️ HFT Order Router not available: {e}")

try:
    from queen_repository_scanner import QueenRepositoryScanner
    REPO_SCANNER_OK = True
except ImportError:
    REPO_SCANNER_OK = False
    QueenRepositoryScanner = None

# ═══════════════════════════════════════════════════════════════════════════════
# 🇮🇪🎯 IRA SNIPER MODE - Zero Loss Configuration
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from ira_sniper_mode import (
        IRA_SNIPER_MODE, SNIPER_CONFIG, apply_sniper_mode,
        MyceliumStateAggregator, MyceliumSynapse
    )
    IRA_SNIPER_OK = True
except ImportError:
    IRA_SNIPER_OK = False
    IRA_SNIPER_MODE = None

# ═══════════════════════════════════════════════════════════════════════════════
# 🧠 THOUGHT BUS - Universal Consciousness Network
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from aureon_thought_bus import ThoughtBus, Thought, get_thought_bus
    THOUGHT_BUS_OK = True
except ImportError:
    THOUGHT_BUS_OK = False
    ThoughtBus = None
    Thought = None

# ═══════════════════════════════════════════════════════════════════════════════
# 🧠⛏️ MINER BRAIN - Critical Thinking & Speculation Engine
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from aureon_miner_brain import (
        MinerBrain, SpeculationEngine, WisdomCognitionEngine,
        WebKnowledgeMiner
    )
    MINER_BRAIN_OK = True
except ImportError:
    try:
        from aureon_miner_brain import MinerBrain
        MINER_BRAIN_OK = True
        SpeculationEngine = None
        WisdomCognitionEngine = None
        WebKnowledgeMiner = None
    except ImportError:
        MINER_BRAIN_OK = False
        MinerBrain = None

# ═══════════════════════════════════════════════════════════════════════════════
# 🐋🔊 WHALE SONAR - Mycelium Deep Frequency Network
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from mycelium_whale_sonar import WhaleSonar, create_and_start_sonar
    WHALE_SONAR_OK = True
except ImportError:
    WHALE_SONAR_OK = False
    WhaleSonar = None


class AlpacaExecutor:
    """Simple Alpaca execution client"""

    def __init__(self):
        self.api_key = os.environ.get('ALPACA_API_KEY')
        # Try both possible secret key names
        self.api_secret = os.environ.get('ALPACA_SECRET_KEY') or os.environ.get('ALPACA_API_SECRET')
        # Use LIVE trading URL (not paper)
        self.base_url = "https://api.alpaca.markets"
        self.crypto_url = "https://data.alpaca.markets/v1beta3/crypto/us"

        self.headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.api_secret,
            'Content-Type': 'application/json'
        }

    def get_account(self) -> Dict:
        """Get account info"""
        resp = requests.get(f"{self.base_url}/v2/account", headers=self.headers)
        return resp.json()

    def get_buying_power(self) -> float:
        """Get available buying power"""
        acct = self.get_account()
        return float(acct.get('buying_power', 0))

    def get_positions(self) -> List[Dict]:
        """Get all positions"""
        resp = requests.get(f"{self.base_url}/v2/positions", headers=self.headers)
        data = resp.json()
        return data if isinstance(data, list) else []

    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for symbol"""
        # Convert BTC/USD -> BTCUSD
        alpaca_symbol = symbol.replace('/', '')

        try:
            resp = requests.get(
                f"{self.base_url}/v2/positions/{alpaca_symbol}",
                headers=self.headers
            )
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return None

    def get_quote(self, symbol: str) -> Dict:
        """Get current quote"""
        alpaca_symbol = symbol.replace('/', '')
        resp = requests.get(
            f"{self.crypto_url}/latest/quotes",
            headers=self.headers,
            params={'symbols': alpaca_symbol}
        )
        data = resp.json()
        return data.get('quotes', {}).get(alpaca_symbol, {})

    def place_order(
        self,
        symbol: str,
        side: str,  # "buy" or "sell"
        notional: float = None,  # USD amount
        qty: float = None        # Crypto quantity
    ) -> Dict:
        """Place a market order"""
        alpaca_symbol = symbol.replace('/', '')

        order_data = {
            'symbol': alpaca_symbol,
            'side': side,
            'type': 'market',
            'time_in_force': 'gtc'
        }

        if notional:
            order_data['notional'] = str(notional)
        elif qty:
            order_data['qty'] = str(qty)

        resp = requests.post(
            f"{self.base_url}/v2/orders",
            headers=self.headers,
            json=order_data
        )

        return resp.json()


class KrakenExecutor:
    """Kraken execution client using existing KrakenClient"""

    def __init__(self):
        if KRAKEN_OK:
            self.client = get_kraken_client()
            self.client.dry_run = False  # Enable live trading
        else:
            self.client = None

    def get_balance(self) -> Dict[str, float]:
        """Get all balances"""
        if not self.client:
            return {}
        return self.client.get_account_balance()

    def get_stablecoin_balance(self) -> float:
        """Get total USD-equivalent stablecoin balance"""
        balances = self.get_balance()
        stables = ['ZUSD', 'USD', 'USDC', 'USDT', 'TUSD', 'DAI']
        total = 0.0
        for asset, amount in balances.items():
            if asset in stables:
                total += float(amount)
        return total

    def get_quote(self, symbol: str) -> Dict:
        """Get current quote"""
        if not self.client:
            return {}
        return self.client.best_price(symbol)

    def place_order(
        self,
        symbol: str,
        side: str,  # "buy" or "sell"
        quantity: float = None,
        quote_qty: float = None  # USD amount
    ) -> Dict:
        """Place a market order"""
        if not self.client:
            return {"error": "Kraken client not available"}

        return self.client.place_market_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            quote_qty=quote_qty
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 TRADE LOGGER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeRecord:
    """Record of a trade execution"""
    timestamp: str
    symbol: str
    side: str
    entry_price: float
    quantity: float
    notional_usd: float
    momentum_pct: float
    net_profit_expected: float
    harmonic_tier: str
    composite_score: float
    order_id: str
    status: str

    def to_dict(self) -> Dict:
        return asdict(self)


class TradeLogger:
    """Log trades to file"""

    def __init__(self, log_file: str = "queen_trades.jsonl"):
        self.log_file = log_file

    def log_trade(self, record: TradeRecord):
        """Append trade to log file"""
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(record.to_dict()) + '\n')

        print(f"📝 Trade logged: {record.side} {record.symbol} @ ${record.entry_price:.4f}")


# ═══════════════════════════════════════════════════════════════════════════════
# 👑 QUEEN EXECUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class QueenExecutionEngine:
    """
    👑💰 THE QUEEN'S EXECUTION ENGINE 💰👑

    Workflow:
    1. Scan for momentum using HarmonicMomentumWaveScanner
    2. Filter for actionable signals (momentum > 0.34%)
    3. Check available buying power (Kraken or Alpaca)
    4. Execute on best opportunity
    5. Log trade and monitor
    """

    def __init__(self, dry_run: bool = False, exchange: str = "kraken"):
        self.dry_run = dry_run
        self.exchange = exchange.lower()

        print("\n" + "═" * 70)
        print("👑💰 QUEEN EXECUTION ENGINE - INITIALIZING 💰👑")
        print("═" * 70)
        print(f"   Mode: {'🔒 DRY RUN (no real trades)' if dry_run else '🔥 LIVE TRADING'}")
        print(f"   Exchange: {exchange.upper()}")

        # Initialize scanner
        if SCANNER_OK:
            self.scanner = HarmonicMomentumWaveScanner()
            print("   ✅ Harmonic Momentum Scanner loaded")
        else:
            self.scanner = None
            print("   ❌ Scanner not available")

        # Initialize executors
        self.alpaca = AlpacaExecutor()
        print("   ✅ Alpaca Executor loaded")

        if KRAKEN_OK:
            self.kraken = KrakenExecutor()
            print("   ✅ Kraken Executor loaded")
        else:
            self.kraken = None
            print("   ⚠️ Kraken Executor not available")

        # Initialize logger
        self.logger = TradeLogger()
        print("   ✅ Trade Logger loaded")

        # ═══════════════════════════════════════════════════════════════════════════════
        # 🏹⚔️ APACHE WAR BAND - Scouts & Snipers
        # ═══════════════════════════════════════════════════════════════════════════════
        self.war_band = None
        self.mycelium = None
        self.loss_learning = None
        self.market_pulse = None
        self.unified_client = None
        self.rainbow_bridge = None
        self.wisdom_scanner = None
        self.repo_scanner = None

        # 🧠 Deep Learning & Neural Systems
        self.thought_bus = None
        self.miner_brain = None
        self.ira_sniper = None
        self.whale_sonar = None
        self.mycelium_aggregator = None

        self._init_war_band()
        self._init_rainbow_bridge()
        self._init_knowledge_systems()
        self._init_deep_learning_systems()
        self._init_thought_bus()

        # ═══════════════════════════════════════════════════════════════════════════════
        # ⚡🧬 HIGH FREQUENCY TRADING - HARMONIC MYCELIUM ENGINE
        # ═══════════════════════════════════════════════════════════════════════════════
        self.hft_engine = None
        self.hft_order_router = None

        if HFT_ENGINE_AVAILABLE and get_hft_engine:
            try:
                self.hft_engine = get_hft_engine()
                print("   ⚡🧬 HFT Engine loaded (Sub-10ms latency)")
            except Exception as e:
                print(f"   ⚠️ HFT Engine failed: {e}")

        if HFT_ORDER_ROUTER_AVAILABLE and get_order_router:
            try:
                self.hft_order_router = get_order_router()

                # Wire exchange clients for execution
                exchange_clients = {
                    'kraken': self.kraken.kraken_client if self.kraken else None,
                    'alpaca': self.alpaca.alpaca_client if self.alpaca else None,
                }
                self.hft_order_router.wire_exchange_clients(exchange_clients)

                print("   🌐⚡ HFT Order Router loaded (WebSocket execution)")
                print(f"      Exchanges: {len([e for e in exchange_clients.values() if e])} connected")
            except Exception as e:
                print(f"   ⚠️ HFT Order Router failed: {e}")

        # Stats
        self.trades_executed = 0
        self.total_profit = 0.0
        self.scout_finds = 0
        self.sniper_kills = 0
        self._execution_cycles = 0
        self._wisdom_topic_index = 0

        print("═" * 70 + "\n")

    def _init_war_band(self):
        """Initialize Apache War Band and supporting systems"""

        # Get buying power to initialize Mycelium
        buying_power = 0.0
        try:
            if self.exchange == "kraken" and self.kraken:
                buying_power = self.kraken.get_stablecoin_balance()
            else:
                buying_power = self.alpaca.get_buying_power()
        except Exception:
            buying_power = 15.0  # Default starting capital

        # Initialize Unified Exchange Client first
        if UNIFIED_CLIENT_OK:
            try:
                self.unified_client = MultiExchangeClient()
                print("   🔗 Unified Exchange Client: ACTIVE")
            except Exception as e:
                print(f"   ⚠️ Unified Client: {e}")

        # Initialize Market Pulse
        if MARKET_PULSE_OK and self.unified_client:
            try:
                self.market_pulse = MarketPulse(client=self.unified_client)
                print("   📊 Market Pulse: ACTIVE")
            except Exception as e:
                print(f"   ⚠️ Market Pulse: {e}")

        # Initialize Mycelium Network (neural intelligence)
        if MYCELIUM_OK:
            try:
                self.mycelium = MyceliumNetwork(
                    initial_capital=buying_power,
                    target_equity=100000.0  # £100K goal
                )
                print("   🍄 Mycelium Neural Network: ACTIVE")
            except Exception as e:
                print(f"   ⚠️ Mycelium: {e}")

        # Initialize Enhanced War Band
        if WAR_BAND_OK:
            try:
                self.war_band = EnhancedWarBand(
                    war_band=None,  # We'll use enhanced standalone
                    client=self.unified_client,
                    pulse=self.market_pulse
                )
                # Wire Mycelium for neural targeting
                if self.mycelium:
                    self.war_band.set_mycelium(self.mycelium)
                print("   🏹 Apache War Band: SCOUTS & SNIPERS DEPLOYED")
            except Exception as e:
                print(f"   ⚠️ War Band: {e}")

        # Initialize Queen Loss Learning (Apache tactics)
        if LOSS_LEARNING_OK:
            try:
                self.loss_learning = QueenLossLearningSystem(
                    mycelium=self.mycelium,
                    kraken_client=self.kraken.client if self.kraken else None
                )
                print("   🪶 Apache Warfare Tactics: LOADED")
            except Exception as e:
                print(f"   ⚠️ Loss Learning: {e}")

    def _init_rainbow_bridge(self):
        """Initialize Rainbow Bridge - Emotional Frequency Trading"""
        if RAINBOW_OK:
            try:
                self.rainbow_bridge = RainbowBridge()
                print("   🌈 Rainbow Bridge: LOVE FREQUENCY ACTIVE (528 Hz)")
                # Display the vow
                if THE_VOW:
                    print(f"      \"{THE_VOW.get('line1', '')} {THE_VOW.get('line2', '')},")
                    print(f"       {THE_VOW.get('line3', '')} {THE_VOW.get('line4', '')}.\"")
            except Exception as e:
                print(f"   ⚠️ Rainbow Bridge: {e}")
        else:
            print("   ⚠️ Rainbow Bridge: Not available")

    def get_rainbow_state(self, lambda_val: float = 0.5, coherence: float = 0.5, volatility: float = 0.2):
        """Get current Rainbow Bridge emotional state and trading modifier"""
        if not self.rainbow_bridge:
            return None

        state = self.rainbow_bridge.update_from_market(lambda_val, coherence, volatility)
        return state

    def display_rainbow_status(self):
        """Display current Rainbow Bridge status"""
        if self.rainbow_bridge:
            print(f"   {self.rainbow_bridge.display_status()}")

    def _init_knowledge_systems(self):
        """Initialize Wisdom & Knowledge Systems - Ancient Civilization Learning"""

        # Initialize Wisdom Scanner (11 Civilizations)
        if WISDOM_SCANNER_OK:
            try:
                config = ScannerConfig(
                    rate_limit_strategy="gentle",
                    scan_interval_hours=24
                )
                self.wisdom_scanner = AureonWisdomScanner(config)
                summary = self.wisdom_scanner.get_wisdom_summary()
                total_insights = summary['scan_stats']['total_insights']
                print(f"   📚 Wisdom Scanner: 11 CIVILIZATIONS ACTIVE")
                print(f"      Celtic, Aztec, Egyptian, Pythagorean, Chinese, Hindu, Mayan, Norse...")
                print(f"      Total insights learned: {total_insights}")
            except Exception as e:
                print(f"   ⚠️ Wisdom Scanner: {e}")

        # Initialize Repository Scanner (Queen's Reading Glasses)
        if REPO_SCANNER_OK:
            try:
                self.repo_scanner = QueenRepositoryScanner()
                wisdom_factor = self.repo_scanner.scan_repository()
                print(f"   👑👁️ Repository Scanner: QUEEN'S READING GLASSES ACTIVE")
                print(f"      Wisdom Factor: {wisdom_factor:.4f}")
            except Exception as e:
                print(f"   ⚠️ Repository Scanner: {e}")

        # Display Bhoy's Wisdom if available
        if BHOYS_WISDOM_OK:
            try:
                wisdom = get_patience_wisdom()
                print(f"   🍀 Bhoy's Wisdom: IRISH STRATEGY LOADED")
                print(f"      \"{wisdom[:60]}...\"")
            except Exception as e:
                print(f"   ⚠️ Bhoy's Wisdom: {e}")

    def _init_deep_learning_systems(self):
        """Initialize Deep Learning & Neural Intelligence Systems"""

        # ═══════════════════════════════════════════════════════════════════════════════
        # 🇮🇪🎯 IRA SNIPER MODE - Zero Loss Configuration
        # ═══════════════════════════════════════════════════════════════════════════════
        if IRA_SNIPER_OK:
            try:
                self.ira_sniper = IRA_SNIPER_MODE
                if SNIPER_CONFIG:
                    print(f"   🇮🇪🎯 IRA Sniper Mode: ZERO LOSS ARMED")
                    print(f"      \"One bullet. One kill. NO MISSES. EVER.\"")
                    print(f"      Exit Rule: Only on CONFIRMED NET PROFIT")
            except Exception as e:
                print(f"   ⚠️ IRA Sniper: {e}")

        # ═══════════════════════════════════════════════════════════════════════════════
        # 🧠⛏️ MINER BRAIN - Critical Thinking & Speculation Engine
        # ═══════════════════════════════════════════════════════════════════════════════
        if MINER_BRAIN_OK:
            try:
                self.miner_brain = MinerBrain()
                print(f"   🧠⛏️ Miner Brain: COGNITION ENGINE ACTIVE")
                print(f"      \"Your feet are for dancing, your brain is for cutting out the bullshit!\"")

                # Wire Miner Brain to Mycelium if available
                if self.mycelium and hasattr(self.miner_brain, 'set_mycelium'):
                    self.miner_brain.set_mycelium(self.mycelium)
                    print(f"      → Wired to Mycelium Neural Network")
            except Exception as e:
                print(f"   ⚠️ Miner Brain: {e}")

        # ═══════════════════════════════════════════════════════════════════════════════
        # 🍄🔗 MYCELIUM STATE AGGREGATOR - Unified Intelligence Network
        # ═══════════════════════════════════════════════════════════════════════════════
        if IRA_SNIPER_OK and MyceliumStateAggregator:
            try:
                self.mycelium_aggregator = MyceliumStateAggregator()

                # Register all systems with the aggregator
                if self.mycelium:
                    self.mycelium_aggregator.systems['mycelium'] = self.mycelium
                if self.miner_brain:
                    self.mycelium_aggregator.systems['miner_brain'] = self.miner_brain
                if self.wisdom_scanner:
                    self.mycelium_aggregator.systems['wisdom_scanner'] = self.wisdom_scanner
                if self.war_band:
                    self.mycelium_aggregator.systems['war_band'] = self.war_band
                if self.rainbow_bridge:
                    self.mycelium_aggregator.systems['rainbow_bridge'] = self.rainbow_bridge

                num_systems = len(self.mycelium_aggregator.systems)
                print(f"   🍄🔗 Mycelium Aggregator: {num_systems} SYSTEMS CONNECTED")
                print(f"      Synapses: Bidirectional intelligence flow enabled")
            except Exception as e:
                print(f"   ⚠️ Mycelium Aggregator: {e}")

    def _init_thought_bus(self):
        """Initialize ThoughtBus - Universal Consciousness Network"""

        # ═══════════════════════════════════════════════════════════════════════════════
        # 🧠 THOUGHT BUS - Universal Consciousness Network
        # ═══════════════════════════════════════════════════════════════════════════════
        if THOUGHT_BUS_OK:
            try:
                self.thought_bus = ThoughtBus(
                    max_memory=5000,
                    persist_path="queen_thoughts.jsonl"
                )
                print(f"   🧠 ThoughtBus: CONSCIOUSNESS NETWORK ONLINE")
                print(f"      Memory: 5000 thoughts | Persist: queen_thoughts.jsonl")

                # Subscribe to key topics
                self._subscribe_thought_handlers()

                # Emit startup thought
                self.emit_thought(
                    message="Queen Execution Engine awakening...",
                    topic="queen.startup",
                    priority="high",
                    metadata={"exchange": self.exchange, "dry_run": self.dry_run}
                )
            except Exception as e:
                print(f"   ⚠️ ThoughtBus: {e}")

        # ═══════════════════════════════════════════════════════════════════════════════
        # 🐋🔊 WHALE SONAR - Mycelium Deep Frequency Network
        # ═══════════════════════════════════════════════════════════════════════════════
        if WHALE_SONAR_OK and self.thought_bus:
            try:
                self.whale_sonar = WhaleSonar(
                    thought_bus=self.thought_bus,
                    sample_window=5.0,
                    agg_interval=1.0,
                    queen_alert_threshold=0.6
                )
                self.whale_sonar.start()
                print(f"   🐋🔊 Whale Sonar: DEEP FREQUENCY SCANNING")
                print(f"      Listening for subsystem songs...")
            except Exception as e:
                print(f"   ⚠️ Whale Sonar: {e}")

    def _subscribe_thought_handlers(self):
        """Subscribe to ThoughtBus topics for Queen decision making"""
        if not self.thought_bus:
            return

        # Subscribe to whale sonar alerts
        def handle_whale_alert(thought):
            if thought.payload.get('critical'):
                logger.warning(f"🐋 WHALE ALERT: {thought.source} - {thought.payload}")

        try:
            self.thought_bus.subscribe("whale.sonar.*", handle_whale_alert)
            self.thought_bus.subscribe("enigma.whale.*", handle_whale_alert)
        except Exception as e:
            logger.debug(f"ThoughtBus subscription error: {e}")

    def emit_thought(self, message: str, topic: str = "queen.thought",
                     priority: str = "normal", metadata: Dict = None) -> Optional[Any]:
        """Emit a thought to the ThoughtBus network"""
        if not self.thought_bus:
            return None

        try:
            thought = self.thought_bus.think(
                message=message,
                topic=topic,
                priority=priority,
                metadata=metadata or {}
            )
            return thought
        except Exception as e:
            logger.debug(f"Emit thought error: {e}")
            return None

    def get_miner_speculation(self, symbol: str) -> Optional[Dict]:
        """Get Miner Brain speculation for a symbol"""
        if not self.miner_brain:
            return None

        try:
            # Let the miner brain speculate on the symbol
            if hasattr(self.miner_brain, 'speculate'):
                return self.miner_brain.speculate(symbol)
            elif hasattr(self.miner_brain, 'analyze'):
                return self.miner_brain.analyze(symbol)
            else:
                return {"symbol": symbol, "status": "miner_active"}
        except Exception as e:
            logger.debug(f"Miner speculation error: {e}")
            return None

    def trigger_wisdom_learning(self):
        """Trigger Wikipedia learning scan for wisdom updates"""
        if not self.wisdom_scanner:
            return None

        try:
            # Deterministic round-robin scheduling; research results still
            # come from the configured live provider.
            civilizations = [
                "Celtic_mythology", "Aztec_mythology", "Egyptian_mythology",
                "Pythagorean", "Chinese_philosophy", "Hindu_philosophy",
                "Mayan_civilization", "Norse_mythology"
            ]
            topic = civilizations[self._wisdom_topic_index % len(civilizations)]
            self._wisdom_topic_index += 1

            # Trigger async scan if available
            if hasattr(self.wisdom_scanner, 'scan_topic'):
                insight = self.wisdom_scanner.scan_topic(topic)
                if insight:
                    self.emit_thought(
                        message=f"Learned from {topic}: {str(insight)[:100]}...",
                        topic="wisdom.learning",
                        priority="normal"
                    )
                    return insight
        except Exception as e:
            logger.debug(f"Wisdom learning error: {e}")
        return None

    def get_wisdom_for_trade(self, trade_type: str = "entry") -> str:
        """Get wisdom guidance for trading decision"""
        if not BHOYS_WISDOM_OK:
            return "Trust the process."

        try:
            if trade_type == "victory":
                return get_victory_quote()
            elif trade_type == "patience":
                return get_patience_wisdom()
            elif trade_type == "resilience":
                return get_resilience_message()
            else:
                return get_patience_wisdom()
        except:
            return "Every penny is a battle won."

    def get_buying_power(self) -> float:
        """Get available buying power from selected exchange"""
        if self.exchange == "kraken" and self.kraken:
            return self.kraken.get_stablecoin_balance()
        else:
            return self.alpaca.get_buying_power()

    # ═══════════════════════════════════════════════════════════════════════════════
    # 🏄 RIDE THE WAVE - Position Profit Scanner
    # ═══════════════════════════════════════════════════════════════════════════════

    def check_positions_for_profit_sale(self) -> Optional[Dict]:
        """
        🏄 RIDE THE WAVE: Check existing positions for profit-taking opportunities

        This scans ALL existing positions (even from previous sessions) and sells
        them when they're in profit above the threshold. IRA Sniper Mode ensures
        we only sell at a CONFIRMED NET PROFIT.

        Returns:
            Dict with sale result if a position was sold, None otherwise
        """
        if self.exchange != "alpaca":
            return None  # Only implemented for Alpaca currently

        try:
            positions = self.alpaca.get_positions()
            if not positions:
                return None

            print("\n🏄 RIDING THE WAVE - Scanning positions for profit...")

            MIN_PROFIT_PCT = 0.34  # Same threshold as buying (covers fees)
            MIN_PROFIT_USD = 0.01  # Minimum $0.01 profit to sell

            best_profit_position = None
            best_profit_pct = 0.0

            for pos in positions:
                try:
                    # Handle both dict and object formats
                    if isinstance(pos, dict):
                        symbol = pos.get('symbol', '')
                        qty = float(pos.get('qty', 0))
                        unrealized_pl = float(pos.get('unrealized_pl', 0))
                        unrealized_plpc = float(pos.get('unrealized_plpc', 0)) * 100
                        market_value = float(pos.get('market_value', 0))
                        current_price = float(pos.get('current_price', 0))
                    else:
                        symbol = pos.symbol
                        qty = float(pos.qty)
                        unrealized_pl = float(pos.unrealized_pl)
                        unrealized_plpc = float(pos.unrealized_plpc) * 100
                        market_value = float(pos.market_value)
                        current_price = float(pos.current_price)

                    # Skip USDT (stablecoin) - not a tradeable position
                    if 'USDT' in symbol or 'USDC' in symbol:
                        continue

                    # Check if in profit
                    if unrealized_pl > MIN_PROFIT_USD and unrealized_plpc > MIN_PROFIT_PCT:
                        emoji = "🟢"
                        status = "PROFIT"

                        # Track best profit position
                        if unrealized_plpc > best_profit_pct:
                            best_profit_pct = unrealized_plpc
                            best_profit_position = {
                                'symbol': symbol,
                                'qty': qty,
                                'profit_usd': unrealized_pl,
                                'profit_pct': unrealized_plpc,
                                'market_value': market_value,
                                'current_price': current_price
                            }
                    else:
                        emoji = "🔴" if unrealized_pl < 0 else "⚪"
                        status = "LOSS" if unrealized_pl < 0 else "FLAT"

                    print(f"   {emoji} {symbol}: ${market_value:.2f} | P/L: ${unrealized_pl:+.4f} ({unrealized_plpc:+.2f}%) [{status}]")

                except Exception as e:
                    continue

            # Execute sale on best profit position
            if best_profit_position:
                print(f"\n🎯 PROFIT TARGET ACQUIRED: {best_profit_position['symbol']}")
                print(f"   💰 Profit: ${best_profit_position['profit_usd']:+.4f} ({best_profit_position['profit_pct']:+.2f}%)")
                print(f"   📊 Selling {best_profit_position['qty']:.6f} @ ${best_profit_position['current_price']:.4f}")

                # Execute the SELL order
                result = self.execute_position_sale(best_profit_position)

                if result:
                    print(f"   ✅ PROFIT CAPTURED! ${best_profit_position['profit_usd']:+.4f}")
                    self.emit_thought(
                        message=f"Sold {best_profit_position['symbol']} for ${best_profit_position['profit_usd']:+.4f} profit!",
                        topic="queen.trade.profit_sale",
                        priority="high"
                    )
                    return result
            else:
                print("   ⏳ No positions ready for profit-taking")

            return None

        except Exception as e:
            print(f"   ⚠️ Position scan error: {e}")
            return None

    def execute_position_sale(self, position: Dict) -> Optional[Dict]:
        """
        Execute a SELL order for an existing position

        Args:
            position: Dict with symbol, qty, profit_usd, profit_pct

        Returns:
            Dict with sale result if successful, None otherwise
        """
        try:
            symbol = position['symbol']
            qty = position['qty']

            # Convert symbol format (BTCUSD -> BTC/USD)
            if 'USD' in symbol and '/' not in symbol:
                formatted_symbol = symbol[:-3] + '/' + symbol[-3:]
            else:
                formatted_symbol = symbol

            print(f"\n🔫 EXECUTING SELL: {formatted_symbol} x {qty:.6f}")

            # Execute via Alpaca
            result = self.alpaca.place_order(
                symbol=symbol,
                side='sell',
                qty=qty
            )

            if result:
                # Log the trade
                if hasattr(self, 'trade_logger') and self.trade_logger:
                    self.trade_logger.log_trade({
                        'action': 'SELL',
                        'symbol': formatted_symbol,
                        'quantity': qty,
                        'price': position['current_price'],
                        'profit_usd': position['profit_usd'],
                        'profit_pct': position['profit_pct'],
                        'exchange': 'alpaca',
                        'reason': 'profit_taking'
                    })

                return {
                    'action': 'SELL',
                    'symbol': formatted_symbol,
                    'qty': qty,
                    'profit': position['profit_usd'],
                    'result': result
                }

            return None

        except Exception as e:
            print(f"   ❌ Sale execution failed: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════════════════
    # 🏹 SCOUT - The Hunter (Target Acquisition)
    # ═══════════════════════════════════════════════════════════════════════════════

    def war_band_scout(self, signals: List) -> Optional[Any]:
        """
        🏹 SCOUT: Use War Band to find the best target

        The Scout uses:
        - V14 scoring (100% win rate logic)
        - Neural targeting from Mycelium
        - 7-day planner windows
        - Enhancement modifiers
        """
        if not self.war_band or not signals:
            return None

        best_target = None
        best_score = 0.0

        for signal in signals:
            try:
                # Get War Band unified evaluation
                unified = self.war_band.evaluate_target(
                    symbol=signal.symbol,
                    exchange=self.exchange,
                    price=signal.current_price,
                    volume=0,
                    lambda_value=signal.composite_score
                )

                if unified.proceed and unified.unified_score > best_score:
                    best_score = unified.unified_score
                    best_target = {
                        'signal': signal,
                        'unified': unified,
                        'score': best_score
                    }

            except Exception as e:
                logger.debug(f"Scout evaluation error for {signal.symbol}: {e}")
                continue

        if best_target:
            self.scout_finds += 1
            unified = best_target['unified']
            print(f"   🏹 SCOUT ACQUIRED: {best_target['signal'].symbol}")
            print(f"      V14 Score: {unified.v14_score}/{unified.v14_threshold}")
            print(f"      Enhancement: {unified.enhancement_modifier:.2f}x")
            print(f"      Unified Score: {unified.unified_score:.3f}")
            if unified.reasons:
                for r in unified.reasons[:3]:
                    print(f"      {r}")

        return best_target

    # ═══════════════════════════════════════════════════════════════════════════════
    # 🔫 SNIPER - The Killer (Precision Execution)
    # ═══════════════════════════════════════════════════════════════════════════════

    def war_band_sniper_check(self, signal) -> bool:
        """
        🔫 SNIPER: Final validation before kill

        Applies Apache patience tactics:
        - Wait for confirmation
        - Check terrain (market conditions)
        - Ensure clean shot (no slippage risk)
        """
        if not signal:
            return False

        # Get Apache tactics wisdom if available
        if self.loss_learning:
            try:
                # Research Apache warfare for this situation
                tactics = self.loss_learning.get_applicable_tactics(
                    context={'action': 'entry', 'symbol': signal.symbol}
                )
                if tactics:
                    logger.info(f"🪶 Apache Wisdom: {tactics[0].get('trading_application', 'Wait for right moment')}")
            except Exception:
                pass

        # Check Mycelium network coherence
        coherence_ok = True
        if self.mycelium:
            try:
                coherence = self.mycelium.get_network_coherence()
                queen_signal = self.mycelium.get_queen_signal()
                if coherence < 0.3:
                    print(f"   🔫 SNIPER: Coherence low ({coherence:.2f}) - holding fire")
                    coherence_ok = False
                elif queen_signal < -0.3:
                    print(f"   🔫 SNIPER: Queen bearish ({queen_signal:.2f}) - holding fire")
                    coherence_ok = False
            except Exception:
                pass

        return coherence_ok

    def war_band_sniper_kill(self, target: Dict) -> Optional:
        """
        🔫 SNIPER: Execute the kill with precision
        """
        if not target:
            return None

        signal = target.get('signal')
        unified = target.get('unified')

        # Final sniper check
        if not self.war_band_sniper_check(signal):
            print("   🔫 SNIPER: Shot aborted - conditions not optimal")
            return None

        self.sniper_kills += 1
        print(f"   🔫 SNIPER: TAKING THE SHOT!")

        # Execute the trade
        return self.execute_trade(signal)

    def scan_for_opportunity(self) -> Optional[HarmonicMomentumSignal]:
        """Scan for the best momentum opportunity"""
        if not self.scanner:
            print("❌ Scanner not available")
            return None

        print("\n🔍 Scanning for harmonic momentum...")
        signals = self.scanner.scan_all()
        actionable = [s for s in signals if s.is_actionable()]

        if not actionable:
            print(f"   ⏳ No momentum > {ROUND_TRIP_COST_PCT}% threshold")
            # Show the best one for context
            if signals:
                best = signals[0]
                needed = ROUND_TRIP_COST_PCT - abs(best.momentum_5m_pct)
                print(f"   📊 Best: {best.symbol} at {best.momentum_5m_pct:+.3f}% (need +{needed:.3f}% more)")
            return None

        # Return best opportunity
        best = actionable[0]
        print(f"   🎯 FOUND: {best.harmonic_tier.value} {best.symbol}")
        print(f"      Momentum: {best.momentum_5m_pct:+.3f}%")
        print(f"      Direction: {best.direction}")
        print(f"      Net Profit: {best.net_profit_potential:+.3f}%")
        print(f"      Confidence: {best.confidence:.1%}")

        return best

    def calculate_position_size(self, signal: HarmonicMomentumSignal) -> float:
        """Calculate position size based on buying power and confidence"""
        buying_power = self.get_buying_power()

        # Use confidence to scale position (max 50% of buying power)
        max_position_pct = 0.50
        position_pct = min(signal.confidence, max_position_pct)

        position_size = buying_power * position_pct

        # Enforce minimum
        if position_size < MIN_TRADE_USD:
            position_size = min(MIN_TRADE_USD, buying_power)

        return position_size

    def execute_trade(self, signal: HarmonicMomentumSignal) -> Optional[TradeRecord]:
        """Execute a trade based on signal"""
        if not signal.is_actionable():
            print("❌ Signal not actionable")
            return None

        # Consult Autonomy Hub (Big Wheel) for cross-system validation
        try:
            from aureon_autonomy_hub import get_autonomy_hub
            hub = get_autonomy_hub()
            hub_decision = hub.spin_cycle(signal.symbol)
            if hub_decision and hub_decision.direction == "HOLD" and hub_decision.confidence > 0.5:
                print(f"   ⚙️ BIG WHEEL: HOLD (confidence={hub_decision.confidence:.2f}) - skipping")
                return None
            if hub_decision and hub_decision.direction != "NEUTRAL":
                print(f"   ⚙️ BIG WHEEL: {hub_decision.direction} @ {hub_decision.confidence:.2f}")
        except Exception:
            pass

        # Consult War Planner (adversarial chess mind)
        try:
            from aureon_strategic_war_planner import get_war_planner
            planner = get_war_planner()
            war_plan = planner.plan(
                symbol=signal.symbol, price=signal.price,
                change_pct=signal.momentum_score * 100,
                has_position=False, position_side="none",
            )
            if war_plan and war_plan.final_move:
                fm = war_plan.final_move
                print(f"   ⚔️ WAR PLANNER: {fm.move_type.value} | "
                      f"Survival: {fm.survival_probability:.0%} | "
                      f"Stance: {war_plan.stance.value}")
                if fm.move_type.value in ('RETREAT', 'HOLD') and fm.confidence > 0.6:
                    print(f"   ⚔️ WAR PLANNER: Enemy too strong — skipping trade")
                    return None
        except Exception:
            pass

        # Only allow LONG trades when we have stablecoins (can't short without crypto)
        if signal.direction != "LONG":
            print(f"   ⚠️ Skipping {signal.direction} - Only LONG trades allowed with stablecoins")
            return None

        # Calculate position size
        position_size = self.calculate_position_size(signal)
        buying_power = self.get_buying_power()

        if position_size < MIN_TRADE_USD:
            print(f"❌ Insufficient buying power: ${buying_power:.2f} < ${MIN_TRADE_USD:.2f}")
            return None

        print(f"\n💰 EXECUTING TRADE ({self.exchange.upper()})")
        print(f"   Symbol: {signal.symbol}")
        print(f"   Direction: {signal.direction}")
        print(f"   Position Size: ${position_size:.2f}")
        print(f"   Expected Profit: {signal.net_profit_potential:+.3f}%")

        side = "buy" if signal.direction == "LONG" else "sell"

        if self.dry_run:
            print(f"\n   🔒 DRY RUN - Would {side} ${position_size:.2f} of {signal.symbol}")
            order_id = f"DRY_RUN_{int(time.time())}"
            status = "dry_run"
        else:
            print(f"\n   🔥 LIVE - Executing {side} order on {self.exchange.upper()}...")

            # ═══════════════════════════════════════════════════════════════════════════════
            # ⚡🧬 HIGH FREQUENCY TRADING EXECUTION - SUB-10MS LATENCY
            # ═══════════════════════════════════════════════════════════════════════════════
            if HFT_ORDER_ROUTER_AVAILABLE and hasattr(self, 'hft_order_router') and self.hft_order_router:
                try:
                    print(f"   ⚡ Using HFT Order Router (WebSocket execution)...")

                    # Create HFT order request
                    from aureon_hft_websocket_order_router import OrderRequest

                    order_request = OrderRequest(
                        symbol=signal.symbol,
                        side=side,
                        quantity=position_size / signal.current_price,  # Convert USD to crypto quantity
                        price=None,  # Market order
                        exchange=self.exchange,
                        order_type="market",
                        timestamp=time.time()
                    )

                    # Execute via HFT router
                    result = self.hft_order_router.execute_order(order_request)

                    if result and result.success:
                        order_id = result.order_id or f"HFT_{int(time.time())}"
                        status = "filled" if result.filled_quantity > 0 else "pending"
                        print(f"   ✅ HFT Order executed: {order_id}")
                        print(f"   📊 Filled: {result.filled_quantity:.6f} @ ${result.average_price:.2f}")
                        print(f"   ⚡ Latency: {result.execution_time_ms:.1f}ms")
                    else:
                        error_msg = result.error_message if result else "Unknown HFT error"
                        print(f"   ❌ HFT Order failed: {error_msg}")
                        return None

                except Exception as e:
                    print(f"   ⚠️ HFT execution failed, falling back to REST: {e}")
                    # Fall through to REST execution
                    HFT_ORDER_ROUTER_AVAILABLE = False

            # ═══════════════════════════════════════════════════════════════════════════════
            # 🌐 REST API EXECUTION - FALLBACK MODE
            # ═══════════════════════════════════════════════════════════════════════════════
            if not HFT_ORDER_ROUTER_AVAILABLE or not hasattr(self, 'hft_order_router') or not self.hft_order_router:
                print(f"   🌐 Using REST API execution...")

                if self.exchange == "kraken" and self.kraken:
                    result = self.kraken.place_order(
                        symbol=signal.symbol,
                        side=side,
                        quote_qty=position_size
                    )
                    order_id = result.get('txid', result.get('id', 'unknown'))
                    status = result.get('status', 'filled' if 'txid' in result else 'unknown')
                else:
                    result = self.alpaca.place_order(
                        symbol=signal.symbol,
                        side=side,
                        notional=position_size
                    )
                    order_id = result.get('id', 'unknown')
                    status = result.get('status', 'unknown')

                if 'error' in str(result).lower():
                    print(f"   ❌ REST Order failed: {result}")
                    return None

                print(f"   ✅ REST Order placed: {order_id}")
                print(f"   Status: {status}")

            print(f"   ✅ Order placed: {order_id}")
            print(f"   Status: {status}")

        # Create trade record
        record = TradeRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=signal.symbol,
            side=side,
            entry_price=signal.current_price,
            quantity=position_size / signal.current_price,
            notional_usd=position_size,
            momentum_pct=signal.momentum_5m_pct,
            net_profit_expected=signal.net_profit_potential,
            harmonic_tier=str(signal.harmonic_tier.value),
            composite_score=signal.composite_score,
            order_id=order_id,
            status=status
        )

        # Log trade
        self.logger.log_trade(record)

        self.trades_executed += 1

        return record

    def run_cycle(self) -> Optional[TradeRecord]:
        """
        Run one complete trading cycle:
        1. ThoughtBus emit cycle start
        2. Miner Brain speculation
        3. Rainbow Bridge emotional check
        4. Scan for opportunity (Harmonic Momentum)
        5. Scout (War Band target acquisition)
        6. Sniper (Precision execution)
        7. ThoughtBus emit result
        """
        self._execution_cycles += 1
        print("\n" + "=" * 70)
        print(f"👑 QUEEN CYCLE @ {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 70)

        # Emit cycle start thought
        self.emit_thought(
            message="Starting trading cycle...",
            topic="queen.cycle.start",
            priority="normal"
        )

        # Check buying power
        buying_power = self.get_buying_power()
        print(f"\n💰 Buying Power: ${buying_power:.2f}")

        if buying_power < MIN_TRADE_USD:
            print(f"   ⚠️ Below minimum trade size (${MIN_TRADE_USD:.2f})")

        # ═══════════════════════════════════════════════════════════════════════════════
        # 🏄 RIDE THE WAVE - Check existing positions for profit-taking opportunities
        # ═══════════════════════════════════════════════════════════════════════════════
        profit_sale = self.check_positions_for_profit_sale()
        if profit_sale:
            return profit_sale  # Executed a profitable sale!

        # ═══════════════════════════════════════════════════════════════════════════════
        # RAINBOW BRIDGE - Emotional Frequency Check
        # ═══════════════════════════════════════════════════════════════════════════════
        rainbow_modifier = 1.0
        if self.rainbow_bridge:
            # Get coherence from mycelium if available
            coherence = None
            if self.mycelium:
                try:
                    coherence = self.mycelium.get_network_coherence()
                except:
                    pass

            # Lambda and volatility are not available at this point in the
            # cycle, so do not substitute values or alter position sizing.
            state = None
            if state:
                rainbow_modifier = state.trading_modifier
                symbol = self.rainbow_bridge.get_cycle_symbol()
                print(f"\n{symbol} Rainbow Bridge: {state.emotional_state} @ {state.current_frequency} Hz")
                print(f"   Phase: {state.cycle_phase} | Resonance: {state.resonance:.3f} | Modifier: {rainbow_modifier:.2f}x")

                # If in FEAR phase, be extra cautious
                if state.cycle_phase == 'FEAR':
                    print(f"   ⚠️ FEAR PHASE - Extra caution advised")

        # ═══════════════════════════════════════════════════════════════════════════════
        # MINER BRAIN - Deep Speculation & Critical Thinking
        # ═══════════════════════════════════════════════════════════════════════════════
        if self.miner_brain:
            try:
                # Trigger learning on a deterministic ten-cycle cadence.
                if self._execution_cycles % 10 == 0:
                    self.trigger_wisdom_learning()
            except Exception:
                pass

        # ═══════════════════════════════════════════════════════════════════════════════
        # PHASE 1: SCAN - Harmonic Momentum Detection
        # ═══════════════════════════════════════════════════════════════════════════════
        signal = self.scan_for_opportunity()

        if not signal:
            print("\n⏳ Waiting for momentum...")
            return None

        # ═══════════════════════════════════════════════════════════════════════════════
        # PHASE 2: SCOUT - War Band Target Acquisition
        # ═══════════════════════════════════════════════════════════════════════════════
        if self.war_band:
            print("\n🏹 WAR BAND SCOUTING...")
            target = self.war_band_scout([signal])

            if target:
                # ═══════════════════════════════════════════════════════════════════════════════
                # PHASE 3: SNIPER - Precision Execution
                # ═══════════════════════════════════════════════════════════════════════════════
                print("\n🔫 SNIPER ENGAGING...")
                record = self.war_band_sniper_kill(target)

                if record:
                    print(f"\n✅ KILL CONFIRMED!")
                    print(f"   🎯 {record.side.upper()} {record.symbol}")
                    print(f"   💰 Size: ${record.notional_usd:.2f}")
                    print(f"   📈 Expected: {record.net_profit_expected:+.3f}%")
                    print(f"   🏹 Scout Finds: {self.scout_finds}")
                    print(f"   🔫 Sniper Kills: {self.sniper_kills}")

                    # Emit successful trade thought
                    self.emit_thought(
                        message=f"KILL CONFIRMED: {record.side.upper()} {record.symbol} for ${record.notional_usd:.2f}",
                        topic="queen.execution.success",
                        priority="high",
                        metadata={
                            "symbol": record.symbol,
                            "side": record.side,
                            "amount": record.notional_usd,
                            "expected_profit_pct": record.net_profit_expected
                        }
                    )
                    return record
                else:
                    print("   🔫 SNIPER: Shot aborted")
            else:
                print("   🏹 SCOUT: No approved targets")

        # ═══════════════════════════════════════════════════════════════════════════════
        # FALLBACK: Direct execution without War Band
        # ═══════════════════════════════════════════════════════════════════════════════
        print("\n⚡ DIRECT EXECUTION...")
        record = self.execute_trade(signal)

        if record:
            print(f"\n✅ TRADE EXECUTED!")
            print(f"   {record.side.upper()} {record.symbol}")
            print(f"   Size: ${record.notional_usd:.2f}")
            print(f"   Expected: {record.net_profit_expected:+.3f}%")

        return record

    def run_continuous(self, interval_seconds: int = 30, max_cycles: int = 0):
        """
        Run continuous trading cycles.

        Args:
            interval_seconds: Seconds between cycles
            max_cycles: Maximum cycles (0 = unlimited)
        """
        print("\n" + "═" * 70)
        print("👑💰 QUEEN CONTINUOUS TRADING MODE 💰👑")
        print("═" * 70)
        print(f"   Interval: {interval_seconds}s")
        print(f"   Max Cycles: {'Unlimited' if max_cycles == 0 else max_cycles}")
        print(f"   Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print("   Press Ctrl+C to stop")
        print("═" * 70)

        cycle_count = 0

        try:
            while max_cycles == 0 or cycle_count < max_cycles:
                cycle_count += 1

                self.run_cycle()

                print(f"\n⏳ Next scan in {interval_seconds}s...")
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\n\n👑 Queen stopped by user")

        print(f"\n📊 Session Summary:")
        print(f"   Cycles: {cycle_count}")
        print(f"   Trades: {self.trades_executed}")


# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Queen Execution Engine")
    parser.add_argument("--live", action="store_true", help="Enable live trading")
    parser.add_argument("--exchange", type=str, default="kraken", help="Exchange (kraken or alpaca)")
    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=30, help="Scan interval (seconds)")
    parser.add_argument("--cycles", type=int, default=0, help="Max cycles (0=unlimited)")

    args = parser.parse_args()

    # Initialize engine
    engine = QueenExecutionEngine(dry_run=not args.live, exchange=args.exchange)

    if args.continuous:
        engine.run_continuous(
            interval_seconds=args.interval,
            max_cycles=args.cycles
        )
    else:
        # Single cycle
        engine.run_cycle()


if __name__ == "__main__":
    main()
