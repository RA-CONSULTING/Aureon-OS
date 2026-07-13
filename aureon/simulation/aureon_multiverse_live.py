#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                   ║
║     ⚡🌌 AUREON MULTIVERSE LIVE - THE ULTIMATE UNIFIED TRADING SYSTEM 🌌⚡                          ║
║                                                                                                   ║
║     "One System, Many Worlds, Zero Fear - Sweep Profits Before Markets React!"                   ║
║                                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════╝

COMPLETE INTEGRATION OF ALL SYSTEMS:
=====================================

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                            AUREON MULTIVERSE LIVE - ALL SYSTEMS WIRED                               │
│                                                                                                     │
│   ┌───────────────────┐         ┌───────────────────┐         ┌───────────────────┐                │
│   │  🦅 COMMANDO      │────────▶│  🌌 MULTIVERSE    │────────▶│  ⚡ CONVERTER     │                │
│   │  (1885 CAPM)      │         │  (10-9-1-10)      │         │  (50ms Sweep)     │                │
│   └────────┬──────────┘         └────────┬──────────┘         └────────┬──────────┘                │
│            │                             │                             │                            │
│            ▼                             ▼                             ▼                            │
│   ┌───────────────────┐         ┌───────────────────┐         ┌───────────────────┐                │
│   │  🧠 MINER BRAIN   │◀───────▶│  🎵 AURIS NODES   │◀───────▶│  💎 NEXUS         │                │
│   │  (Critical Think) │         │  (9 Frequencies)  │         │  (Signal Hub)     │                │
│   └────────┬──────────┘         └────────┬──────────┘         └────────┬──────────┘                │
│            │                             │                             │                            │
│            └─────────────────────────────┼─────────────────────────────┘                            │
│                                          ▼                                                          │
│                            ┌───────────────────────────────┐                                        │
│                            │  🍄 MYCELIUM COGNITION MESH   │                                        │
│                            │  (Underground Signal Network)  │                                        │
│                            └─────────────┬─────────────────┘                                        │
│                                          │                                                          │
│                                          ▼                                                          │
│                            ┌───────────────────────────────┐                                        │
│                            │  💰 UNIFIED EXCHANGE CLIENT   │                                        │
│                            │  Binance | Kraken | Alpaca    │                                        │
│                            └───────────────────────────────┘                                        │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

THE COMMANDO DOCTRINE (Wired Into Every System):
=================================================
🔥 ZERO FEAR - Execute immediately when conditions are met
🔥 ONE GOAL - GROW_NET_PROFIT_FAST
🔥 DUAL PATH - SELL or CONVERT, whichever is faster to profit
🔥 PENNY PROFIT - Even $0.01 net is a WIN
🔥 SWEEP BEFORE REACT - 50ms converter beats market reaction

Gary Leckey & GitHub Copilot | January 2026
"We don't quit. We compound. We conquer." 🌌⚡
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import os
import sys
import json
import time
import math
import logging
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

# ═══════════════════════════════════════════════════════════════════════════════
# WINDOWS UTF-8 FIX - MUST BE AT TOP
# ═══════════════════════════════════════════════════════════════════════════════
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            """Check if stream is already a UTF-8 TextIOWrapper."""
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            """Check if stream buffer is valid and not closed."""
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        # Only wrap if not already UTF-8 wrapped AND buffer is valid
        if _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════════════════════
# SAFE PRINT - Handles closed stdout gracefully (Windows multi-module imports)
# ═══════════════════════════════════════════════════════════════════════════════
def _safe_print(*args, **kwargs):
    """Print that won't crash if stdout is closed."""
    try:
        print(*args, **kwargs)
    except (ValueError, OSError, IOError):
        pass  # stdout closed or unavailable - skip silently

# ═══════════════════════════════════════════════════════════════════════════════
# CORE IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

# Memory Core
try:
    from aureon.core.aureon_memory_core import memory
    MEMORY_AVAILABLE = True
except ImportError:
    memory = None
    MEMORY_AVAILABLE = False

# Thought Bus for Unity Consciousness
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought
    THOUGHT_BUS = ThoughtBus(persist_path="multiverse_live_thoughts.jsonl")
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS = None
    THOUGHT_BUS_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# 🌌 INTERNAL MULTIVERSE - 10-9-1-10 Architecture
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.simulation.aureon_internal_multiverse import (
        get_multiverse, multiverse_predict, multiverse_record_outcome,
        InternalMultiverse, World, OmegaConverter, ConsensusEngine
    )
    MULTIVERSE_AVAILABLE = True
    _safe_print("🌌 Internal Multiverse WIRED! (10-9-1-10 many worlds)")
except ImportError as e:
    MULTIVERSE_AVAILABLE = False
    _safe_print(f"⚠️ Internal Multiverse not available: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 🦅 COMMANDO DOCTRINE - Zero Fear Trading
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.conversion.aureon_conversion_commando import (
        DualProfitPathDecision, DualProfitPathEvaluator,
        ZERO_FEAR, ONE_GOAL, GROWTH_AGGRESSION, COMPOUND_RATE, MIN_PROFIT_TARGET
    )
    COMMANDO_AVAILABLE = True
    _safe_print("🦅 Conversion Commando WIRED! (Zero Fear Doctrine)")
except ImportError:
    COMMANDO_AVAILABLE = False
    ZERO_FEAR = True
    ONE_GOAL = "GROW_NET_PROFIT_FAST"
    GROWTH_AGGRESSION = 0.95
    COMPOUND_RATE = 0.95
    # Global epsilon profit policy: accept any net-positive edge after costs.
    MIN_PROFIT_TARGET = 0.0001

# ═══════════════════════════════════════════════════════════════════════════════
# 🧠 MINER BRAIN - Critical Thinking & Speculation
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.utils.aureon_miner_brain import MinerBrain, SandboxEvolution
    MINER_BRAIN_AVAILABLE = True
    _miner_brain = MinerBrain() if hasattr(MinerBrain, '__init__') else None
    _safe_print("🧠 Miner Brain WIRED! (Critical thinking engine)")
except ImportError:
    MINER_BRAIN_AVAILABLE = False
    _miner_brain = None

# ═══════════════════════════════════════════════════════════════════════════════
# 💎 NEXUS - The Signal Hub
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.core.aureon_nexus import AURIS_NODES, RAINBOW_STATES, PHI, LOVE_FREQUENCY
    NEXUS_AVAILABLE = True
    _safe_print("💎 Nexus WIRED! (9 Auris nodes active)")
except ImportError:
    NEXUS_AVAILABLE = False
    PHI = (1 + math.sqrt(5)) / 2
    LOVE_FREQUENCY = 528
    AURIS_NODES = {}
    RAINBOW_STATES = {}

# ═══════════════════════════════════════════════════════════════════════════════
# 🍄 MYCELIUM NETWORK
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.core.aureon_mycelium import Synapse, Neuron, Agent, Hive, MyceliumNetwork
    MYCELIUM_AVAILABLE = True
    _safe_print("🍄 Mycelium Network WIRED! (Neural substrate)")
except ImportError:
    MYCELIUM_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# 💰 EXCHANGE CLIENTS
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
    BINANCE_AVAILABLE = True
    _safe_print("📈 Binance Client WIRED!")
except ImportError:
    BINANCE_AVAILABLE = False
    BinanceClient = None

try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
    KRAKEN_AVAILABLE = True
    _safe_print("📈 Kraken Client WIRED!")
except ImportError:
    KRAKEN_AVAILABLE = False
    KrakenClient = None

try:
    from aureon.exchanges.alpaca_client import AlpacaClient
    ALPACA_AVAILABLE = True
    _safe_print("📈 Alpaca Client WIRED!")
except ImportError:
    ALPACA_AVAILABLE = False
    AlpacaClient = None

try:
    from aureon.trading.unified_exchange_client import UnifiedExchangeClient
    UNIFIED_CLIENT_AVAILABLE = True
    _safe_print("📈 Unified Exchange Client WIRED!")
except ImportError:
    UNIFIED_CLIENT_AVAILABLE = False
    UnifiedExchangeClient = None

# ═══════════════════════════════════════════════════════════════════════════════
# ⛏️ QUANTUM MINER INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.utils.aureon_miner import AureonMiner, KNOWN_POOLS, BINANCE_COINS
    MINER_AVAILABLE = True
    _safe_print("⛏️ Quantum Miner WIRED!")
except ImportError:
    MINER_AVAILABLE = False
    AureonMiner = None

# ═══════════════════════════════════════════════════════════════════════════════
# 🎵 QGITA ENGINE - Quantum Auris
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.wisdom.aureon_qgita import AurisState, CONFIG as QGITA_CONFIG
    QGITA_AVAILABLE = True
    _safe_print("🎵 QGITA Engine WIRED! (Quantum Auris)")
except ImportError:
    QGITA_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# 🔱 PROBABILITY INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.strategies.probability_ultimate_intelligence import (
        get_ultimate_intelligence, ultimate_predict, record_ultimate_outcome,
        UltimatePrediction
    )
    PROBABILITY_AVAILABLE = True
    _safe_print("🔱 Probability Intelligence WIRED! (95% accuracy)")
except ImportError:
    PROBABILITY_AVAILABLE = False
    ultimate_predict = None

# ═══════════════════════════════════════════════════════════════════════════════
# 🎬 INCEPTION ENGINE - Russian Doll Probability Architecture
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.intelligence.aureon_inception_engine import (
        InceptionEngine, get_inception_engine, inception_dive, get_limbo_insight,
        InceptionLevel, LimboProbabilityMatrix, RussianDoll
    )
    INCEPTION_AVAILABLE = True
    _inception_engine = get_inception_engine()
    _safe_print("🎬 INCEPTION ENGINE WIRED! (Russian Doll: REALITY → DREAM_1 → DREAM_2 → LIMBO)")
except ImportError as e:
    INCEPTION_AVAILABLE = False
    _inception_engine = None
    _safe_print(f"⚠️ Inception Engine not available: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 🪜 CONVERSION LADDER - A-Z / Z-A Full Spectrum Sweep
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.conversion.aureon_conversion_ladder import ConversionLadder, LadderDecision
    LADDER_AVAILABLE = True
    _safe_print("🪜 Conversion Ladder WIRED! (A-Z / Z-A Full Spectrum Sweep)")
except ImportError as e:
    LADDER_AVAILABLE = False
    ConversionLadder = None
    _safe_print(f"⚠️ Conversion Ladder not available: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 🛡️ COGNITION RUNTIME
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.autonomous.aureon_cognition_runtime import MinerModule, RiskModule, ExecutionModule, AureonRuntime
    COGNITION_AVAILABLE = True
    _safe_print("🛡️ Cognition Runtime WIRED!")
except ImportError:
    COGNITION_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# 💰 REVENUE BOARD - Real-Time Portfolio Tracker
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.portfolio.aureon_revenue_board import RevenueBoard, get_revenue_board, print_revenue_board
    REVENUE_BOARD_AVAILABLE = True
    _safe_print("💰 Revenue Board WIRED! (Live portfolio tracking)")
except ImportError as e:
    REVENUE_BOARD_AVAILABLE = False
    RevenueBoard = None
    _safe_print(f"⚠️ Revenue Board not available: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 UNIFIED SNIPER BRAIN - Million Kill Training
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.trading.unified_sniper_brain import (
        UnifiedSniperBrain, UnifiedSignal, TrainedSniperParams,
        SNIPER_AVAILABLE, PENNY_AVAILABLE
    )
    SNIPER_BRAIN_AVAILABLE = True
    _sniper_brain = UnifiedSniperBrain(exchange='binance', position_size=10.0)
    _safe_print("🎯 Unified Sniper Brain WIRED! (Million Kill Training)")
except ImportError as e:
    SNIPER_BRAIN_AVAILABLE = False
    _sniper_brain = None
    _safe_print(f"⚠️ Sniper Brain not available: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# ☘️ IRISH PATRIOT SCOUTS - Force Scouts with Celtic Intelligence
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.wisdom.irish_patriot_scouts import (
        PatriotScoutNetwork, PatriotScout, PatriotScoutDeployer,
        PATRIOT_CONFIG, PATRIOT_WISDOM
    )
    SCOUTS_AVAILABLE = True
    _safe_print("☘️ Irish Patriot Scouts WIRED! (Force Scouts)")
except ImportError as e:
    SCOUTS_AVAILABLE = False
    PatriotScoutNetwork = None
    _safe_print(f"⚠️ Patriot Scouts not available: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 🔭 QUANTUM TELESCOPE - Multi-Dimensional Geometric Analysis
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.simulation.aureon_quantum_telescope import QuantumTelescope, LightBeam, GeometricSolid
    QUANTUM_TELESCOPE_AVAILABLE = True
    _safe_print("🔭 Quantum Telescope WIRED! (5 Platonic Lenses)")
except ImportError as e:
    QUANTUM_TELESCOPE_AVAILABLE = False
    QuantumTelescope = None
    _safe_print(f"⚠️ Quantum Telescope not available: {e}")

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('multiverse_live.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 💰 PENNY PROFIT LEDGER - Validated Timestamps
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PennyProfitEntry:
    """A validated penny profit entry with timestamp"""
    timestamp: float
    datetime_str: str
    symbol: str
    exchange: str
    gross_pnl: float
    fees: float
    net_pnl: float
    validated: bool
    validation_method: str
    source: str  # SNIPER, SCOUT, COMMANDO, INCEPTION, SWEEP
    
    def to_dict(self) -> Dict:
        return {
            "ts": self.timestamp,
            "dt": self.datetime_str,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "gross": self.gross_pnl,
            "fees": self.fees,
            "net": self.net_pnl,
            "validated": self.validated,
            "method": self.validation_method,
            "source": self.source
        }


class PennyProfitLedger:
    """
    💰 PENNY PROFIT LEDGER - Validated Portfolio Tracker
    
    Every penny profit is:
    - Timestamped to the millisecond
    - Validated against fee calculations
    - Tracked for real portfolio increases
    """
    
    def __init__(self):
        self.entries: List[PennyProfitEntry] = []
        self.total_validated_profit = 0.0
        self.total_fees_paid = 0.0
        self.start_time = time.time()
        
    def validate_and_record(self, symbol: str, exchange: str, gross_pnl: float, 
                           fees: float, source: str = "UNKNOWN") -> PennyProfitEntry:
        """
        Validate a profit and record with timestamp
        """
        now = time.time()
        net_pnl = gross_pnl - fees
        
        # Validation: Net must be positive for penny profit
        validated = net_pnl >= MIN_PROFIT_TARGET
        validation_method = "NET_POSITIVE" if validated else "INSUFFICIENT"
        
        entry = PennyProfitEntry(
            timestamp=now,
            datetime_str=datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            symbol=symbol,
            exchange=exchange,
            gross_pnl=gross_pnl,
            fees=fees,
            net_pnl=net_pnl,
            validated=validated,
            validation_method=validation_method,
            source=source
        )
        
        self.entries.append(entry)
        
        if validated:
            self.total_validated_profit += net_pnl
            self.total_fees_paid += fees
            logger.info(f"💰 PENNY PROFIT VALIDATED: +${net_pnl:.4f} net | {symbol} | {source} | {entry.datetime_str}")
        
        return entry
    
    def get_summary(self) -> Dict:
        """Get ledger summary"""
        validated_entries = [e for e in self.entries if e.validated]
        return {
            "total_entries": len(self.entries),
            "validated_entries": len(validated_entries),
            "total_validated_profit": self.total_validated_profit,
            "total_fees_paid": self.total_fees_paid,
            "net_after_fees": self.total_validated_profit,
            "runtime_seconds": time.time() - self.start_time,
            "profit_per_minute": self.total_validated_profit / max(1, (time.time() - self.start_time) / 60)
        }
    
    def print_ledger(self):
        """Print the penny profit ledger"""
        summary = self.get_summary()
        print("\n" + "=" * 70)
        print("💰 PENNY PROFIT LEDGER - VALIDATED TIMESTAMPS 💰")
        print("=" * 70)
        print(f"  Total Validated Profit: ${summary['total_validated_profit']:.4f}")
        print(f"  Total Fees Paid:        ${summary['total_fees_paid']:.4f}")
        print(f"  Profit Rate:            ${summary['profit_per_minute']:.4f}/min")
        print(f"  Validated Entries:      {summary['validated_entries']}/{summary['total_entries']}")
        print("-" * 70)
        
        # Last 10 entries
        recent = self.entries[-10:] if len(self.entries) > 10 else self.entries
        for e in reversed(recent):
            status = "✅" if e.validated else "❌"
            print(f"  {status} {e.datetime_str} | {e.symbol:12s} | "
                  f"Net: ${e.net_pnl:+.4f} | {e.source}")
        print("=" * 70 + "\n")

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]

# Commando Speed Settings
CONVERTER_REACTION_MS = 50  # Must beat market reaction
SIGNAL_SCAN_INTERVAL_MS = 100  # 100ms signal scanning
SWEEP_THRESHOLD_PCT = 0.002  # 0.2% profit triggers sweep

# KRAKEN BLACKLIST - Delisted/restricted assets (cancel_only, decommissioned)
KRAKEN_BLACKLIST = {"TUSD", "LUNA", "UST", "FTT", "DASH", "LUNC", "USTC"}

# ═══════════════════════════════════════════════════════════════════════════════
# 🌀 LABYRINTH MAPPER - Crypto Conversion Path Intelligence
# ═══════════════════════════════════════════════════════════════════════════════

class LabyrinthMapper:
    """
    THE LABYRINTH - Maps ALL possible conversion paths across ALL exchanges.
    
    Like a maze, some crypto can move directly (1 hop), others need 
    intermediate assets (2-3 hops). This class builds the complete graph
    and finds optimal paths through the market labyrinth.
    
    Features:
    - Multi-exchange graph (Binance, Kraken, Alpaca)
    - BFS shortest path finding
    - Historical path tracking (which routes are most profitable)
    - Real-time path availability checking
    - UK account awareness (USDC paths, not USDT)
    """
    
    def __init__(self, binance_client=None, kraken_client=None, alpaca_client=None):
        self.binance = binance_client
        self.kraken = kraken_client
        self.alpaca = alpaca_client
        
        # The labyrinth graph: {asset: {target_asset: [(exchange, symbol, direction)]}}
        self.graph: Dict[str, Dict[str, List[tuple]]] = {}
        
        # All known assets across all exchanges
        self.all_assets: set = set()
        
        # Exchange-specific tradeable pairs
        self.binance_pairs: set = set()
        self.kraken_pairs: set = set()
        
        # Path history: {(from, to): {"count": N, "avg_slippage": X, "last_used": ts}}
        self.path_history: Dict[tuple, Dict] = {}
        
        # Last graph build time
        self.last_build_time = 0
        self.graph_ttl = 300  # Rebuild every 5 minutes
        
        logger.info("🌀 Labyrinth Mapper initialized")
    
    def build_labyrinth(self, force: bool = False) -> Dict[str, Any]:
        """
        Build the complete conversion labyrinth across all exchanges.
        Returns stats about the graph.
        """
        if not force and time.time() - self.last_build_time < self.graph_ttl:
            return {"cached": True, "nodes": len(self.all_assets), "edges": sum(len(v) for v in self.graph.values())}
        
        logger.info("🌀 Building labyrinth graph...")
        self.graph = {}
        self.all_assets = set()
        
        # Common quote currencies
        QUOTES = {"USDT", "USDC", "USD", "BTC", "ETH", "EUR", "GBP", "BNB"}
        
        # === BINANCE ===
        if self.binance:
            try:
                # Get UK-allowed pairs if UK account
                if self.binance.uk_mode:
                    pairs = self.binance.get_allowed_pairs_uk()
                    logger.info(f"🌀 Binance UK: {len(pairs)} tradeable pairs")
                else:
                    # Get all pairs from exchange info
                    info = self.binance.exchange_info()
                    pairs = {s['symbol'] for s in info.get('symbols', []) if s.get('status') == 'TRADING'}
                    logger.info(f"🌀 Binance: {len(pairs)} tradeable pairs")
                
                self.binance_pairs = pairs
                
                # Parse pairs into graph edges
                for pair in pairs:
                    base, quote = self._parse_pair(pair, QUOTES)
                    if base and quote:
                        self._add_edge(base, quote, "binance", pair, "SELL")
                        self._add_edge(quote, base, "binance", pair, "BUY")
                        self.all_assets.add(base)
                        self.all_assets.add(quote)
                        
            except Exception as e:
                logger.error(f"🌀 Binance labyrinth error: {e}")
        
        # === KRAKEN ===
        if self.kraken:
            try:
                pairs_info = self.kraken._load_asset_pairs()
                kraken_pairs = set()
                
                for internal, info in pairs_info.items():
                    altname = info.get('altname', internal)
                    # Skip blacklisted assets
                    skip = False
                    for blacklisted in KRAKEN_BLACKLIST:
                        if blacklisted in altname.upper():
                            skip = True
                            break
                    if skip:
                        continue
                    
                    base, quote = self._parse_pair(altname, QUOTES)
                    if base and quote:
                        kraken_pairs.add(altname)
                        self._add_edge(base, quote, "kraken", altname, "SELL")
                        self._add_edge(quote, base, "kraken", altname, "BUY")
                        self.all_assets.add(base)
                        self.all_assets.add(quote)
                
                self.kraken_pairs = kraken_pairs
                logger.info(f"🌀 Kraken: {len(kraken_pairs)} tradeable pairs")
                
            except Exception as e:
                logger.error(f"🌀 Kraken labyrinth error: {e}")
        
        # === ALPACA (Stocks) ===
        if self.alpaca:
            try:
                # Alpaca is stocks - simpler model
                stock_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']
                for symbol in stock_symbols:
                    self._add_edge(symbol, "USD", "alpaca", f"{symbol}/USD", "SELL")
                    self._add_edge("USD", symbol, "alpaca", f"{symbol}/USD", "BUY")
                    self.all_assets.add(symbol)
                self.all_assets.add("USD")
                logger.info(f"🌀 Alpaca: {len(stock_symbols)} stock symbols")
            except Exception as e:
                logger.error(f"🌀 Alpaca labyrinth error: {e}")
        
        self.last_build_time = time.time()
        
        stats = {
            "cached": False,
            "nodes": len(self.all_assets),
            "edges": sum(len(targets) for targets in self.graph.values()),
            "binance_pairs": len(self.binance_pairs),
            "kraken_pairs": len(self.kraken_pairs),
            "assets": sorted(list(self.all_assets))[:50],  # First 50 for logging
        }
        logger.info(f"🌀 Labyrinth built: {stats['nodes']} assets, {stats['edges']} conversion edges")
        return stats
    
    def _parse_pair(self, pair: str, quotes: set) -> tuple:
        """Parse a trading pair into (base, quote) assets."""
        pair_upper = pair.upper()
        for quote in sorted(quotes, key=len, reverse=True):  # Try longer quotes first
            if pair_upper.endswith(quote):
                base = pair_upper[:-len(quote)]
                if base and base != quote:
                    return base, quote
        return None, None
    
    def _add_edge(self, from_asset: str, to_asset: str, exchange: str, symbol: str, direction: str):
        """Add a directed edge to the graph."""
        if from_asset not in self.graph:
            self.graph[from_asset] = {}
        if to_asset not in self.graph[from_asset]:
            self.graph[from_asset][to_asset] = []
        
        # Don't add duplicates
        edge = (exchange, symbol, direction)
        if edge not in self.graph[from_asset][to_asset]:
            self.graph[from_asset][to_asset].append(edge)
    
    def find_path(self, from_asset: str, to_asset: str, preferred_exchange: str = None) -> List[Dict]:
        """
        Find the shortest conversion path from one asset to another.
        Uses BFS for shortest path.
        
        Returns list of steps: [{"from": X, "to": Y, "exchange": E, "symbol": S, "direction": D}, ...]
        """
        from_asset = from_asset.upper()
        to_asset = to_asset.upper()
        
        if from_asset == to_asset:
            return []  # Already there
        
        if from_asset not in self.graph:
            return []  # Unknown source
        
        # BFS for shortest path
        from collections import deque
        queue = deque([(from_asset, [])])
        visited = {from_asset}
        
        while queue:
            current, path = queue.popleft()
            
            if current not in self.graph:
                continue
            
            for target, edges in self.graph[current].items():
                if target in visited:
                    continue
                
                # Pick best edge (prefer specified exchange)
                best_edge = None
                for edge in edges:
                    if preferred_exchange and edge[0] == preferred_exchange:
                        best_edge = edge
                        break
                if not best_edge:
                    best_edge = edges[0]
                
                new_path = path + [{
                    "from": current,
                    "to": target,
                    "exchange": best_edge[0],
                    "symbol": best_edge[1],
                    "direction": best_edge[2]
                }]
                
                if target == to_asset:
                    return new_path
                
                visited.add(target)
                queue.append((target, new_path))
        
        return []  # No path found
    
    def find_all_paths(self, from_asset: str, to_asset: str, max_hops: int = 3) -> List[List[Dict]]:
        """
        Find ALL conversion paths up to max_hops.
        Useful for comparing routes and finding arbitrage.
        """
        from_asset = from_asset.upper()
        to_asset = to_asset.upper()
        
        if from_asset == to_asset:
            return [[]]
        
        all_paths = []
        
        def dfs(current: str, path: List[Dict], visited: set):
            if len(path) > max_hops:
                return
            
            if current == to_asset:
                all_paths.append(path.copy())
                return
            
            if current not in self.graph:
                return
            
            for target, edges in self.graph[current].items():
                if target in visited:
                    continue
                
                for edge in edges:
                    step = {
                        "from": current,
                        "to": target,
                        "exchange": edge[0],
                        "symbol": edge[1],
                        "direction": edge[2]
                    }
                    visited.add(target)
                    path.append(step)
                    dfs(target, path, visited)
                    path.pop()
                    visited.remove(target)
        
        dfs(from_asset, [], {from_asset})
        return all_paths
    
    def get_direct_conversions(self, asset: str) -> Dict[str, List[tuple]]:
        """Get all assets that can be reached in 1 hop from the given asset."""
        asset = asset.upper()
        return self.graph.get(asset, {})
    
    def get_conversion_map(self) -> Dict[str, Any]:
        """
        Get a complete conversion map showing all possible paths.
        Used for UI visualization and debugging.
        """
        # Group assets by type
        stablecoins = {"USDT", "USDC", "USD", "BUSD", "DAI", "TUSD", "FDUSD"}
        fiat = {"USD", "EUR", "GBP", "JPY", "AUD", "CAD"}
        major_crypto = {"BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"}
        
        # Build categorized map
        conversion_map = {
            "stablecoins": [],
            "fiat": [],
            "major_crypto": [],
            "altcoins": [],
            "stocks": [],
        }
        
        for asset in self.all_assets:
            direct = self.get_direct_conversions(asset)
            entry = {
                "asset": asset,
                "direct_targets": list(direct.keys()),
                "exchanges": list(set(e[0] for targets in direct.values() for e in targets)),
                "hop_count": len(direct)
            }
            
            if asset in stablecoins:
                conversion_map["stablecoins"].append(entry)
            elif asset in fiat:
                conversion_map["fiat"].append(entry)
            elif asset in major_crypto:
                conversion_map["major_crypto"].append(entry)
            elif asset in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']:
                conversion_map["stocks"].append(entry)
            else:
                conversion_map["altcoins"].append(entry)
        
        return conversion_map
    
    def record_path_usage(self, path: List[Dict], profit: float = 0.0, slippage: float = 0.0, success: bool = True):
        """
        Record that a path was used for historical tracking.
        Now includes profit tracking for Mycelium integration.
        """
        if not path:
            return
        
        key = (path[0]["from"], path[-1]["to"])
        if key not in self.path_history:
            self.path_history[key] = {
                "count": 0, 
                "total_slippage": 0, 
                "last_used": 0,
                # 🔄 NEW: Profit metrics
                "total_profit": 0.0,
                "avg_profit": 0.0,
                "wins": 0,
                "losses": 0,
                "success_rate": 0.0,
            }
        
        self.path_history[key]["count"] += 1
        self.path_history[key]["total_slippage"] += slippage
        self.path_history[key]["last_used"] = time.time()
        
        # 🔄 Track profit metrics
        self.path_history[key]["total_profit"] += profit
        if profit > 0:
            self.path_history[key]["wins"] += 1
        elif profit < 0:
            self.path_history[key]["losses"] += 1
        
        count = self.path_history[key]["count"]
        self.path_history[key]["avg_profit"] = self.path_history[key]["total_profit"] / count if count > 0 else 0
        
        wins = self.path_history[key]["wins"]
        losses = self.path_history[key]["losses"]
        total_trades = wins + losses
        self.path_history[key]["success_rate"] = wins / total_trades if total_trades > 0 else 0.5
    
    def get_path_stats(self) -> Dict[str, Any]:
        """Get statistics for all recorded paths - useful for Mycelium learning."""
        if not self.path_history:
            return {"paths": 0, "total_profit": 0, "best_path": None, "worst_path": None}
        
        total_profit = sum(p["total_profit"] for p in self.path_history.values())
        total_conversions = sum(p["count"] for p in self.path_history.values())
        
        # Find best and worst paths
        sorted_paths = sorted(
            self.path_history.items(),
            key=lambda x: x[1]["avg_profit"],
            reverse=True
        )
        
        best_path = sorted_paths[0] if sorted_paths else None
        worst_path = sorted_paths[-1] if sorted_paths else None
        
        # Top 5 most profitable paths
        top_profitable = [
            {
                "path": f"{p[0][0]}→{p[0][1]}",
                "avg_profit": p[1]["avg_profit"],
                "count": p[1]["count"],
                "success_rate": p[1]["success_rate"],
            }
            for p in sorted_paths[:5]
        ]
        
        return {
            "paths": len(self.path_history),
            "total_conversions": total_conversions,
            "total_profit": total_profit,
            "best_path": f"{best_path[0][0]}→{best_path[0][1]}" if best_path else None,
            "best_path_profit": best_path[1]["avg_profit"] if best_path else 0,
            "worst_path": f"{worst_path[0][0]}→{worst_path[0][1]}" if worst_path else None,
            "worst_path_profit": worst_path[1]["avg_profit"] if worst_path else 0,
            "top_profitable": top_profitable,
        }
    
    def get_best_path(self, from_asset: str, to_asset: str) -> List[Dict]:
        """
        Get the best path based on historical performance.
        Falls back to shortest path if no history.
        """
        all_paths = self.find_all_paths(from_asset, to_asset, max_hops=3)
        
        if not all_paths:
            return []
        
        # Score paths
        def score_path(path):
            if not path:
                return float('inf')
            
            key = (path[0]["from"], path[-1]["to"])
            history = self.path_history.get(key, {})
            
            # Prefer shorter paths
            hop_penalty = len(path) * 10
            
            # Prefer paths with good history
            count = history.get("count", 0)
            avg_slippage = history.get("total_slippage", 0) / max(count, 1)
            
            return hop_penalty + avg_slippage - (count * 0.1)  # More usage = better
        
        return min(all_paths, key=score_path)
    
    def estimate_conversion_cost(self, path: List[Dict], amount: float, prices: Dict[str, float]) -> Dict:
        """
        Estimate the cost of a conversion path including fees and slippage.
        """
        if not path:
            return {"output": amount, "fees": 0, "slippage": 0}
        
        current_amount = amount
        total_fees = 0
        total_slippage = 0
        
        for step in path:
            # Estimate fee (0.1% for crypto, 0% for same-exchange)
            fee_rate = 0.001
            fee = current_amount * fee_rate
            total_fees += fee
            current_amount -= fee
            
            # Estimate slippage (0.05% per hop)
            slippage_rate = 0.0005
            slippage = current_amount * slippage_rate
            total_slippage += slippage
            current_amount -= slippage
        
        return {
            "input": amount,
            "output": current_amount,
            "fees": total_fees,
            "slippage": total_slippage,
            "hops": len(path),
            "efficiency": current_amount / amount if amount > 0 else 0
        }
    
    def print_labyrinth_summary(self):
        """Print a summary of the labyrinth for debugging."""
        print("\n" + "=" * 70)
        print("🌀 LABYRINTH CONVERSION MAP SUMMARY")
        print("=" * 70)
        print(f"Total Assets: {len(self.all_assets)}")
        print(f"Binance Pairs: {len(self.binance_pairs)}")
        print(f"Kraken Pairs: {len(self.kraken_pairs)}")
        
        # Show hub assets (most connected)
        hub_counts = [(asset, len(self.graph.get(asset, {}))) for asset in self.all_assets]
        hub_counts.sort(key=lambda x: -x[1])
        
        print(f"\n🔗 TOP 10 HUB ASSETS (most connections):")
        for asset, count in hub_counts[:10]:
            print(f"   {asset}: {count} direct conversions")
        
        # Show sample paths
        print(f"\n🛤️ SAMPLE CONVERSION PATHS:")
        test_pairs = [("ADA", "USDC"), ("PEPE", "BTC"), ("ETH", "USD"), ("BTC", "USDC")]
        for from_a, to_a in test_pairs:
            path = self.find_path(from_a, to_a)
            if path:
                route = " → ".join([from_a] + [p["to"] for p in path])
                exchanges = [p["exchange"] for p in path]
                print(f"   {from_a} → {to_a}: {route} via {exchanges}")
            else:
                print(f"   {from_a} → {to_a}: ❌ No path found")
        
        print("=" * 70 + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
# 🦅 COMMANDO COGNITION - Wired Into Everything
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CommandoSignal:
    """A commando-style signal that all systems understand"""
    timestamp: float
    symbol: str
    exchange: str
    action: str  # BUY, SELL, CONVERT, SWEEP, HOLD
    strength: float  # -1 to 1
    confidence: float  # 0 to 1
    source: str  # Which system generated this
    reason: str
    profit_path: str  # 'SELL' or 'CONVERT' 
    expected_profit: float
    commando_type: str  # FALCON, TORTOISE, CHAMELEON, BEE
    
    def to_dict(self) -> Dict:
        return {
            "ts": self.timestamp,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "action": self.action,
            "strength": self.strength,
            "confidence": self.confidence,
            "source": self.source,
            "reason": self.reason,
            "profit_path": self.profit_path,
            "expected_profit": self.expected_profit,
            "commando_type": self.commando_type
        }


class CommandoCognition:
    """
    THE COMMANDO DOCTRINE - Wired Into Every System
    
    This class encapsulates the commando logic so that:
    - Multiverse worlds understand it
    - Miner brain can reason with it
    - Nexus signals incorporate it
    - Cognition runtime executes it
    """
    
    def __init__(self):
        self.zero_fear = ZERO_FEAR
        self.one_goal = ONE_GOAL
        self.growth_aggression = GROWTH_AGGRESSION
        self.compound_rate = COMPOUND_RATE
        self.min_profit_target = MIN_PROFIT_TARGET
        
        # Signal history
        self.signals: deque = deque(maxlen=10000)
        self.executed_trades: List[Dict] = []
        self.total_profit: float = 0.0
        
        # Commando types
        self.commando_types = {
            "FALCON": {"direction": "UP", "speed": "FAST", "aggression": 0.9},
            "TORTOISE": {"direction": "DOWN", "speed": "SLOW", "aggression": 0.4},
            "CHAMELEON": {"direction": "ADAPTIVE", "speed": "MEDIUM", "aggression": 0.7},
            "BEE": {"direction": "SWEEP", "speed": "SYSTEMATIC", "aggression": 0.8}
        }
        
        logger.info("🦅 Commando Cognition initialized - ZERO FEAR mode")
    
    def evaluate_profit_path(self, asset: str, exchange: str, 
                             current_value: float, entry_price: float,
                             current_price: float, market_data: Dict) -> CommandoSignal:
        """
        DUAL PROFIT PATH EVALUATION
        
        Decides: SELL (realize profit now) or CONVERT (compound into better opportunity)
        """
        # Calculate unrealized PnL
        if entry_price <= 0:
            entry_price = current_price
        
        pnl_pct = (current_price - entry_price) / entry_price if entry_price > 0 else 0
        pnl_value = current_value * pnl_pct
        
        # Fee estimation
        fee_rate = 0.001  # 0.1% per side
        sell_fees = current_value * fee_rate * 2  # Entry + exit
        sell_net_profit = pnl_value - sell_fees
        
        # Check for momentum targets (CONVERT path)
        convert_target = None
        convert_momentum = 0.0
        convert_expected = 0.0
        
        changes = market_data.get("changes", {})
        for symbol, change in changes.items():
            if symbol == asset:
                continue
            if change > convert_momentum:
                convert_momentum = change
                convert_target = symbol
        
        if convert_target and convert_momentum > 2.0:
            # Estimate conversion gain
            convert_fee = current_value * fee_rate
            momentum_gain = current_value * (convert_momentum / 100) * 0.25  # 25% of momentum
            convert_expected = pnl_value + momentum_gain - convert_fee - sell_fees
        
        # DECISION LOGIC (Zero Fear)
        if sell_net_profit >= self.min_profit_target:
            if convert_expected > sell_net_profit * 1.5:
                # CONVERT is significantly better
                action = "CONVERT"
                profit_path = "CONVERT"
                expected = convert_expected
                reason = f"CONVERT to {convert_target} ({convert_momentum:+.1f}%) expects ${convert_expected:.4f} > SELL ${sell_net_profit:.4f}"
                commando_type = "FALCON"  # Fast momentum rotation
            else:
                # SELL is safer
                action = "SELL"
                profit_path = "SELL"
                expected = sell_net_profit
                reason = f"SELL nets ${sell_net_profit:.4f} (penny profit secured)"
                commando_type = "BEE"  # Systematic harvest
        elif pnl_pct < -0.05:
            # Loss exceeds 5% - defensive exit
            action = "SELL"
            profit_path = "SELL"
            expected = sell_net_profit
            reason = f"DEFENSIVE EXIT: Loss {pnl_pct*100:.1f}%"
            commando_type = "TORTOISE"
        else:
            # HOLD - no profit path yet
            action = "HOLD"
            profit_path = "NONE"
            expected = 0
            reason = f"HOLD: Unrealized ${pnl_value:.4f}, need ${self.min_profit_target:.2f} net"
            commando_type = "CHAMELEON"
        
        signal = CommandoSignal(
            timestamp=time.time(),
            symbol=asset,
            exchange=exchange,
            action=action,
            strength=min(1.0, abs(pnl_pct) * 10),
            confidence=0.8 if action != "HOLD" else 0.3,
            source="CommandoCognition",
            reason=reason,
            profit_path=profit_path,
            expected_profit=expected,
            commando_type=commando_type
        )
        
        self.signals.append(signal)
        return signal
    
    def get_best_entry_signal(self, market_data: Dict, available_capital: float) -> Optional[CommandoSignal]:
        """
        Find the best entry opportunity using commando doctrine.
        """
        prices = market_data.get("prices", {})
        changes = market_data.get("changes", {})
        momentum = market_data.get("momentum", {})
        symbol_source = market_data.get("source", {})
        
        best_signal = None
        best_score = 0
        
        for symbol in prices:
            change = changes.get(symbol, 0)
            mom = momentum.get(symbol, 0)
            price = prices[symbol]
            
            # FALCON Entry: Strong upward momentum
            if mom > 0.02 and change > 0:
                score = mom * 10 + change / 5
                if score > best_score:
                    best_score = score
                    best_signal = CommandoSignal(
                        timestamp=time.time(),
                        symbol=symbol,
                        exchange=symbol_source.get(symbol, "binance"),
                        action="BUY",
                        strength=min(1.0, score),
                        confidence=min(0.9, 0.5 + score * 0.1),
                        source="CommandoCognition",
                        reason=f"FALCON ENTRY: {symbol} momentum {mom*100:.1f}%, change {change:+.1f}%",
                        profit_path="MOMENTUM",
                        expected_profit=available_capital * mom * 0.5,
                        commando_type="FALCON"
                    )
            
            # CHAMELEON Entry: Mean reversion on oversold
            elif change < -3 and mom > -0.01:
                score = abs(change) / 5 + (mom + 0.01) * 5
                if score > best_score:
                    best_score = score
                    best_signal = CommandoSignal(
                        timestamp=time.time(),
                        symbol=symbol,
                        exchange=symbol_source.get(symbol, "binance"),
                        action="BUY",
                        strength=min(1.0, score),
                        confidence=min(0.8, 0.4 + score * 0.1),
                        source="CommandoCognition",
                        reason=f"CHAMELEON ENTRY: {symbol} oversold {change:+.1f}%, reversal signal",
                        profit_path="MEAN_REVERT",
                        expected_profit=available_capital * abs(change) / 100 * 0.3,
                        commando_type="CHAMELEON"
                    )
        
        return best_signal


# ═══════════════════════════════════════════════════════════════════════════════
# 🌌 MULTIVERSE LIVE ENGINE - The Main System
# ═══════════════════════════════════════════════════════════════════════════════

class MultiverseLiveEngine:
    """
    THE COMPLETE LIVE TRADING ENGINE
    
    Integrates:
    - Internal Multiverse (10-9-1-10 architecture)
    - Commando Cognition (Zero Fear doctrine)
    - Miner Brain (Critical thinking)
    - Nexus/Auris (Signal processing)
    - Exchange Clients (Execution)
    - Revenue Board (Real-time P&L tracking)
    - Sniper Brain (Million Kill Training)
    - Patriot Scouts (Force Scout Intelligence)
    - Penny Profit Ledger (Validated Timestamps)
    """
    
    def __init__(self, simulation_mode: bool = False):
        self.simulation_mode = simulation_mode
        self.running = False
        self.start_time = time.time()
        
        # Initialize ThoughtBus (UNIFIED COMMUNICATION)
        self.thought_bus = THOUGHT_BUS if THOUGHT_BUS_AVAILABLE else None
        if self.thought_bus:
            logger.info("💭 ThoughtBus: ONLINE (Unified Communication)")
        
        # Initialize Commando Cognition (FIRST - wired into everything)
        self.commando = CommandoCognition()
        logger.info("🦅 Commando Cognition: ONLINE")
        
        # Initialize Internal Multiverse
        if MULTIVERSE_AVAILABLE:
            self.multiverse = get_multiverse(initial_equity=100.0)
            logger.info("🌌 Internal Multiverse: ONLINE (10 worlds)")
        else:
            self.multiverse = None
            logger.warning("⚠️ Internal Multiverse: OFFLINE")
        
        # Initialize Exchange Clients (Binance, Kraken)
        if BINANCE_AVAILABLE and not simulation_mode:
            try:
                self.binance = get_binance_client()
                logger.info("📈 Binance Client: ONLINE")
            except Exception as e:
                self.binance = None
                logger.warning(f"📈 Binance Client: OFFLINE ({e})")
        else:
            self.binance = None
            logger.info("📈 Binance Client: SIMULATION MODE")
        
        # Initialize Kraken Client
        if KRAKEN_AVAILABLE and not simulation_mode:
            try:
                self.kraken = get_kraken_client()
                logger.info("📈 Kraken Client: ONLINE")
            except Exception as e:
                self.kraken = None
                logger.warning(f"📈 Kraken Client: OFFLINE ({e})")
        else:
            self.kraken = None
        
        # Initialize Alpaca Client (for stocks)
        if ALPACA_AVAILABLE and not simulation_mode:
            try:
                self.alpaca = AlpacaClient()
                logger.info("📈 Alpaca Client: ONLINE")
            except Exception as e:
                self.alpaca = None
                logger.warning(f"📈 Alpaca Client: OFFLINE ({e})")
        else:
            self.alpaca = None
            logger.info("📈 Alpaca Client: SIMULATION MODE")
        
        # EARLY INIT: Real cash balances (must be before Mycelium init)
        self.real_balances = {
            "binance": {"USD": 0.0, "USDT": 0.0},
            "kraken": {"USD": 0.0},
            "alpaca": {"USD": 0.0}
        }
        self.total_equity = 0.0  # Initialize total equity
        # Fetch initial real balances immediately
        self._refresh_real_balances()
        
        # Initialize Revenue Board (LIVE portfolio tracking from REAL exchanges)
        if REVENUE_BOARD_AVAILABLE:
            self.revenue_board = RevenueBoard(
                binance_client=self.binance,
                kraken_client=self.kraken,
                alpaca_client=self.alpaca
            )
            logger.info("💰 Revenue Board: ONLINE (Live exchange balances)")
        else:
            self.revenue_board = None
            logger.warning("⚠️ Revenue Board: OFFLINE")
        
        # Initialize Sniper Brain (Million Kill Training)
        if SNIPER_BRAIN_AVAILABLE:
            self.sniper = _sniper_brain
            logger.info("🎯 Sniper Brain: ONLINE (Million Kill Training)")
        else:
            self.sniper = None
            logger.warning("⚠️ Sniper Brain: OFFLINE")
        
        # Initialize Patriot Scout Network
        if SCOUTS_AVAILABLE and PatriotScoutNetwork:
            try:
                self.scout_network = PatriotScoutNetwork()
                logger.info("☘️ Patriot Scout Network: ONLINE (Celtic Intelligence)")
            except Exception as e:
                self.scout_network = None
                logger.warning(f"☘️ Patriot Scouts: OFFLINE ({e})")
        else:
            self.scout_network = None
            logger.warning("⚠️ Patriot Scout Network: OFFLINE")
        
        # Initialize Quantum Telescope (Multi-Dimensional Geometric Analysis)
        if QUANTUM_TELESCOPE_AVAILABLE and QuantumTelescope:
            try:
                self.quantum_telescope = QuantumTelescope()
                logger.info("🔭 Quantum Telescope: ONLINE (5 Platonic Lenses)")
            except Exception as e:
                self.quantum_telescope = None
                logger.warning(f"🔭 Quantum Telescope: OFFLINE ({e})")
        else:
            self.quantum_telescope = None
            logger.warning("⚠️ Quantum Telescope: OFFLINE")
        
        # Initialize Mycelium Network (distributed intelligence)
        if MYCELIUM_AVAILABLE:
            try:
                initial_cap = max(self._get_total_cash(), 100.0)
                self.mycelium = MyceliumNetwork(initial_capital=initial_cap, agents_per_hive=5)
                logger.info(f"🍄 Mycelium Network: ONLINE (capital=${initial_cap:.2f})")
            except Exception as e:
                self.mycelium = None
                logger.warning(f"🍄 Mycelium Network: OFFLINE ({e})")
        else:
            self.mycelium = None

        # Make Mycelium aware of all ecosystem connections
        self._update_mycelium_connections()

        # Initialize Penny Profit Ledger (Validated Timestamps)
        self.penny_ledger = PennyProfitLedger()
        logger.info("💰 Penny Profit Ledger: ONLINE (Validated timestamps)")
        
        # Market data cache
        self.market_data: Dict = {}
        self.positions: Dict[str, Dict] = {}
        self.last_scan_time: float = 0

        # Mycelium control layer (set each cycle)
        self.mycelium_directive: Dict[str, Any] = {}
        
        # Note: real_balances already initialized earlier before Mycelium
        
        # Performance tracking
        self.stats = {
            "cycles": 0,
            "signals_generated": 0,
            "trades_executed": 0,
            "sweeps_performed": 0,
            "conversions_performed": 0,
            "total_profit": 0.0,
            "win_count": 0,
            "loss_count": 0,
            "sniper_kills": 0,
            "scout_profits": 0.0
        }

        # Initialize Conversion Ladder (A-Z / Z-A Full Spectrum Sweep)
        self.ladder = None
        if LADDER_AVAILABLE and ConversionLadder:
            try:
                # Build a multi-exchange client wrapper for the ladder
                ladder_client = self._build_ladder_client()
                self.ladder = ConversionLadder(
                    bus=self.thought_bus,
                    mycelium=self.mycelium,
                    client=ladder_client,
                )
                # Enable ladder and set to execute mode for 99.99% aggression
                self.ladder.enabled = True
                self.ladder.mode = "execute"
                self.ladder.fraction = 0.95  # 95% of holding per rotation - FULL SWEEP
                self.ladder.min_value_usd = 1.0  # Lower minimum - accept penny conversions
                self.ladder.cooldown_s = 5.0  # Fast rotations
                self.ladder.exchange_priority = ["kraken", "binance"]  # Prefer Kraken (more holdings)
                logger.info("🪜 Conversion Ladder: ONLINE (A-Z / Z-A Full Spectrum Sweep)")
            except Exception as e:
                self.ladder = None
                logger.warning(f"🪜 Conversion Ladder: OFFLINE ({e})")
        
        # Initialize Labyrinth Mapper (All Conversion Paths)
        self.labyrinth = LabyrinthMapper(
            binance_client=self.binance,
            kraken_client=self.kraken,
            alpaca_client=self.alpaca
        )
        # Build the labyrinth on startup
        if not simulation_mode:
            labyrinth_stats = self.labyrinth.build_labyrinth(force=True)
            logger.info(f"🌀 Labyrinth Mapper: ONLINE ({labyrinth_stats['nodes']} assets, {labyrinth_stats['edges']} paths)")
        else:
            logger.info("🌀 Labyrinth Mapper: SIMULATION MODE")
        
        # Thread pool for parallel operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Note: Real balances already fetched earlier in __init__
        
        logger.info("=" * 60)
        logger.info("⚡🌌 MULTIVERSE LIVE ENGINE INITIALIZED 🌌⚡")
        logger.info(f"   Mode: {'SIMULATION' if simulation_mode else 'LIVE TRADING'}")
        logger.info(f"   Commando: {self.commando.one_goal}")
        logger.info(f"   Multiverse: {len(self.multiverse.worlds) if self.multiverse else 0} worlds")
        logger.info(f"   Revenue Board: {'ONLINE' if self.revenue_board else 'OFFLINE'}")
        logger.info(f"   Sniper Brain: {'ONLINE' if self.sniper else 'OFFLINE'}")
        logger.info(f"   Scout Network: {'ONLINE' if self.scout_network else 'OFFLINE'}")
        logger.info(f"   Conversion Ladder: {'ONLINE' if self.ladder else 'OFFLINE'}")
        logger.info(f"   ThoughtBus: {'ONLINE' if self.thought_bus else 'OFFLINE'}")
        logger.info(f"   Real Cash: ${self._get_total_cash():.2f}")
        logger.info("=" * 60)
        
        # 🌾 STARTUP HARVEST - Scan existing assets for compounding
        # Mode flags are env-driven so CLI + orchestrators can reuse
        self.fresh_start = os.environ.get('AUREON_FRESH_START', '').lower() == 'true'
        self.fresh_start_confirm = os.environ.get('AUREON_FRESH_START_CONFIRM', '').strip().upper() == 'YES'
        self.donkey_mode = os.environ.get('AUREON_DONKEY_MODE', '').lower() == 'true'
        if not simulation_mode:
            if self.fresh_start:
                if not self.fresh_start_confirm:
                    logger.warning(
                        "🔥 FRESH START requested but NOT confirmed. "
                        "Set AUREON_FRESH_START_CONFIRM=YES to allow liquidation. "
                        "Proceeding with scan-only harvest."
                    )
                    self._harvest_existing_assets(liquidate=False)
                else:
                    logger.info("🔥 FRESH START MODE (CONFIRMED): Liquidating all positions to cash...")
                    self._harvest_existing_assets(liquidate=True)
            else:
                self._harvest_existing_assets(liquidate=False)
    
    def _harvest_existing_assets(self, liquidate: bool = False):
        """
        🌾 STARTUP HARVESTER: Scan all holdings across exchanges.
        If liquidate=True, SELLS everything to cash for fresh start.
        Otherwise loads existing positions into the sniper for monitoring.
        """
        logger.info(f"🌾 STARTUP HARVESTER: {'LIQUIDATING ALL' if liquidate else 'Scanning'} existing assets...")
        
        # Determine preferred quote currency for Binance UK accounts
        binance_quote = "USDC" if (self.binance and self.binance.uk_mode) else "USDT"
        
        # Scan Binance for ALL holdings (not just non-quote)
        if self.binance:
            try:
                # Use account() to get balances
                account_info = self.binance.account()
                balances = account_info.get('balances', [])
                
                for bal in balances:
                    asset = bal['asset']
                    free = float(bal.get('free', 0))
                    locked = float(bal.get('locked', 0))
                    total = free + locked
                    
                    if total < 0.000001:  # Skip dust
                        continue
                        
                    # Check if it's a base asset (not quote currency)
                    if asset in ['USDT', 'USDC', 'USD', 'EUR', 'GBP', 'BNB', 'LDUSDC']:
                        continue
                        
                    # Construct symbol - try preferred quote first, then alternatives
                    symbol = f"{asset}{binance_quote}"
                    can_trade = False
                    
                    # Check if tradeable (UK restrictions)
                    can_trade, reason = self.binance.can_trade_symbol(symbol)
                    if not can_trade:
                        # Try other quote currencies (USDC first for UK)
                        for quote in ['USDC', 'USDT', 'BTC', 'ETH', 'BNB', 'EUR']:
                            alt_symbol = f"{asset}{quote}"
                            can_trade, reason = self.binance.can_trade_symbol(alt_symbol)
                            if can_trade:
                                symbol = alt_symbol
                                break
                    
                    if can_trade:
                        # Get current price
                        try:
                            price = float(self.binance.best_price(symbol).get("price", 0) or 0)
                        except Exception:
                            price = 0
                        if price > 0:
                            value = total * price
                            
                            if liquidate and free > 0:
                                # 🔥 LIQUIDATE: Sell everything to cash
                                try:
                                    order = self.binance.place_market_order(symbol, "SELL", quantity=free)
                                    if order:
                                        logger.info(f"   💰 LIQUIDATED {symbol}: {free:.6f} @ ${price:.4f} = ${value:.4f}")
                                except Exception as sell_err:
                                    logger.warning(f"   ⚠️ Failed to liquidate {symbol}: {sell_err}")
                            else:
                                # Load ALL positions, not just >$0.50
                                self.positions[symbol] = {
                                    "entry_price": price,  # Assume current as entry
                                    "quantity": total,
                                    "entry_time": time.time(),
                                    "hold_cycles": 0,
                                    "source": "STARTUP_HARVEST",
                                    "exchange": "binance"
                                }
                                logger.info(f"   🌾 Loaded {symbol} (Binance): {total:.6f} @ ${price:.4f} = ${value:.4f}")
            except Exception as e:
                logger.warning(f"Binance harvest error: {e}")
        
        # Scan Kraken for non-USD holdings
        if self.kraken:
            try:
                balances = self.kraken.get_account_balance()
                skip_assets = {'USD', 'ZUSD', 'USDT', 'USDC', 'EUR', 'ZEUR', 'GBP', 'ZGBP'}
                
                for asset, amount in balances.items():
                    if amount < 0.000001:  # Skip dust
                        continue
                        
                    # Skip quote currencies
                    if asset.upper() in skip_assets:
                        continue
                        
                    # Map asset to pair (Kraken is tricky, try USD then USDT)
                    # e.g. ATOM -> ATOMUSD
                    symbol = f"{asset}USD"
                    ticker = self.kraken.get_ticker(symbol)
                    price = ticker.get('price', 0)
                    
                    if price == 0:
                        symbol = f"{asset}USDT"
                        ticker = self.kraken.get_ticker(symbol)
                        price = ticker.get('price', 0)
                        
                    if price > 0:
                        value = amount * price
                        
                        if liquidate and amount > 0:
                            # 🔥 LIQUIDATE: Sell everything to cash
                            try:
                                order = self.kraken.place_market_order(symbol, "sell", quantity=amount)
                                if order:
                                    logger.info(f"   💰 LIQUIDATED {symbol}: {amount:.6f} @ ${price:.4f} = ${value:.4f}")
                            except Exception as sell_err:
                                logger.warning(f"   ⚠️ Failed to liquidate {symbol}: {sell_err}")
                        else:
                            # Load ALL positions, not just >$0.50
                            self.positions[symbol] = {
                                "entry_price": price,
                                "quantity": amount,
                                "entry_time": time.time(),
                                "hold_cycles": 0,
                                "source": "STARTUP_HARVEST",
                                "exchange": "kraken"
                            }
                            logger.info(f"   🌾 Loaded {symbol} (Kraken): {amount:.6f} @ ${price:.4f} = ${value:.4f}")
            except Exception as e:
                logger.warning(f"Kraken harvest error: {e}")
        
        if liquidate:
            logger.info(f"💰 HARVESTER: LIQUIDATION COMPLETE - All assets converted to cash")
            time.sleep(2)  # Wait for orders to settle
            self._refresh_real_balances()  # Get updated cash balance
        else:
            logger.info(f"🌾 HARVESTER: Loaded {len(self.positions)} existing positions for sniper monitoring")
    
    def _refresh_real_balances(self):
        """Refresh cash balances from actual exchanges"""
        total_equity = 0.0
        
        # Binance - count both cash and asset values (UK uses USDC, non-UK uses USDT)
        if self.binance:
            try:
                acct = self.binance.account()
                quote_cash = 0.0
                asset_value = 0.0
                
                # UK accounts use USDC, non-UK use USDT
                is_uk = self.binance.uk_mode
                primary_quote = "USDC" if is_uk else "USDT"
                cash_assets = {"USDC", "LDUSDC"} if is_uk else {"USDT"}
                
                for bal in acct.get("balances", []):
                    asset = bal["asset"]
                    free = float(bal.get("free", 0))
                    locked = float(bal.get("locked", 0))
                    total_amount = free + locked
                    
                    if total_amount > 0:
                        if asset in cash_assets:
                            quote_cash += free  # Only count free as cash
                        elif asset not in ["BNB", "EUR", "GBP", "USD", "USDT", "USDC"]:
                            # Get current price for asset valuation - try preferred quote first
                            for quote in [primary_quote, "USDC", "USDT", "BTC"]:
                                symbol = f"{asset}{quote}"
                                try:
                                    price = float(self.binance.best_price(symbol).get("price", 0) or 0)
                                    if price > 0:
                                        # Convert to USD if needed
                                        if quote == "BTC":
                                            btc_price = float(self.binance.best_price(f"BTC{primary_quote}").get("price", 0) or 0)
                                            price = price * btc_price
                                        asset_value += total_amount * price
                                        logger.debug(
                                            f"Binance {asset}: {total_amount:.6f} @ ${price:.4f} = ${total_amount * price:.4f}"
                                        )
                                        break
                                except:
                                    continue
                
                # Store as USDT for compatibility but actually tracking USDC for UK
                self.real_balances["binance"]["USDT"] = quote_cash
                total_equity += quote_cash + asset_value
                logger.debug(f"Binance: Cash ${quote_cash:.2f} ({primary_quote}), Assets ${asset_value:.2f}, Total ${quote_cash + asset_value:.2f}")
            except Exception as e:
                logger.debug(f"Binance balance error: {e}")
        
        # Kraken - count both cash and asset values
        if self.kraken:
            try:
                balances = self.kraken.get_account_balance()
                usd_cash = 0.0
                asset_value = 0.0
                
                for asset, amount in balances.items():
                    if amount > 0:
                        if asset in ["USD", "ZUSD", "USDT"]:
                            usd_cash += amount
                        else:
                            # Get current price for asset valuation
                            symbol = f"{asset}USD"
                            try:
                                ticker = self.kraken.get_ticker(symbol)
                                price = ticker.get('price', 0)
                                if price == 0:
                                    symbol = f"{asset}USDT"
                                    ticker = self.kraken.get_ticker(symbol)
                                    price = ticker.get('price', 0)
                                
                                if price > 0:
                                    asset_value += amount * price
                                    logger.debug(f"Kraken {asset}: {amount:.6f} @ ${price:.4f} = ${amount * price:.4f}")
                            except:
                                pass
                
                self.real_balances["kraken"]["USD"] = usd_cash
                total_equity += usd_cash + asset_value
                logger.debug(f"Kraken: Cash ${usd_cash:.2f}, Assets ${asset_value:.2f}, Total ${usd_cash + asset_value:.2f}")
            except Exception as e:
                logger.debug(f"Kraken balance error: {e}")
        
        # Alpaca - cash only (stocks)
        if self.alpaca:
            try:
                account = self.alpaca.get_account()
                usd_cash = float(account.get('cash', 0))
                # Note: Alpaca positions would need separate valuation
                self.real_balances["alpaca"]["USD"] = usd_cash
                total_equity += usd_cash
                logger.debug(f"Alpaca: Cash ${usd_cash:.2f}")
            except Exception as e:
                logger.debug(f"Alpaca balance error: {e}")
        
        # Store total equity for revenue board
        self.total_equity = total_equity
        logger.info(f"💰 Total Equity: ${total_equity:.2f} (includes all assets + cash)")

    def _build_ladder_client(self):
        """Build a multi-exchange client adapter for the ConversionLadder."""
        engine = self

        class LadderClientAdapter:
            """Adapts MultiverseLiveEngine's exchange clients to the Ladder interface."""

            def get_all_balances(self) -> Dict[str, Dict[str, float]]:
                """Return balances per exchange (with USD value filter)."""
                out: Dict[str, Dict[str, float]] = {}
                if engine.binance:
                    try:
                        acct = engine.binance.account()
                        b: Dict[str, float] = {}
                        
                        # UK accounts use USDC, non-UK use USDT
                        is_uk = engine.binance.uk_mode
                        primary_quote = "USDC" if is_uk else "USDT"
                        
                        for bal in acct.get("balances", []):
                            free = float(bal.get("free", 0) or 0)
                            # Only include assets with meaningful balance
                            if free > 0:
                                asset = bal["asset"]
                                # Skip LDUSDC (staked), count as USDC
                                if asset == "LDUSDC":
                                    b["USDC"] = b.get("USDC", 0) + free
                                    continue
                                    
                                # Estimate USD value to filter dust
                                usd_value = free
                                if asset not in ("USD", "USDT", "USDC", "GBP", "EUR"):
                                    # Try to get price using preferred quote for UK
                                    for quote in [primary_quote, "USDC", "USDT", "BTC"]:
                                        try:
                                            price_data = engine.binance.best_price(f"{asset}{quote}")
                                            price = float(price_data.get("price", 0) or 0)
                                            if price > 0:
                                                if quote == "BTC":
                                                    btc_price = float(engine.binance.best_price(f"BTC{primary_quote}").get("price", 0) or 0)
                                                    price = price * btc_price
                                                usd_value = free * price
                                                break
                                        except Exception:
                                            continue
                                    else:
                                        usd_value = 0
                                
                                # Only include if worth at least $1
                                if usd_value >= 1.0 or asset in ("USD", "USDT", "USDC", "GBP", "EUR"):
                                    b[asset] = free
                                    logger.debug(f"🪜 Binance balance: {asset}={free:.4f} (~${usd_value:.2f})")
                        out["binance"] = b
                    except Exception as e:
                        logger.debug(f"🪜 Binance balance error: {e}")
                        out["binance"] = {}
                if engine.kraken:
                    try:
                        # Use global KRAKEN_BLACKLIST constant
                        kb = engine.kraken.get_account_balance() or {}
                        # Normalize Kraken prefixes
                        normalized: Dict[str, float] = {}
                        for k, v in kb.items():
                            asset = k.lstrip("ZX")
                            if asset == "USD":
                                asset = "USD"
                            if asset in KRAKEN_BLACKLIST:
                                continue  # Skip restricted assets
                            val = float(v or 0)
                            if val > 0:
                                normalized[asset] = val
                        out["kraken"] = normalized
                    except Exception:
                        out["kraken"] = {}
                if engine.alpaca:
                    try:
                        a = engine.alpaca.get_account()
                        out["alpaca"] = {"USD": float(a.get("cash", 0) or 0)}
                    except Exception:
                        out["alpaca"] = {}
                return out

            def get_all_convertible_assets(self) -> Dict[str, Dict[str, List[str]]]:
                """Return convertible paths per exchange (UK-aware)."""
                paths: Dict[str, Dict[str, List[str]]] = {}
                
                # === BINANCE UK-AWARE CONVERSION PATHS ===
                if engine.binance:
                    uk_allowed = set()
                    if hasattr(engine.binance, "get_allowed_pairs_uk"):
                        uk_allowed = engine.binance.get_allowed_pairs_uk()
                    
                    binance_map: Dict[str, List[str]] = {}
                    
                    if uk_allowed:
                        # Build actual conversion graph from UK-allowed pairs
                        # Parse symbols to extract base/quote assets
                        quotes = {"USDT", "USDC", "GBP", "EUR", "BTC", "ETH"}
                        assets_seen: set = set()
                        edges: Dict[str, set] = {}  # asset -> set of reachable assets
                        
                        for sym in uk_allowed:
                            # Find quote by checking known quotes
                            for q in quotes:
                                if sym.endswith(q):
                                    base = sym[:-len(q)]
                                    if base and base != q:
                                        assets_seen.add(base)
                                        assets_seen.add(q)
                                        edges.setdefault(base, set()).add(q)
                                        edges.setdefault(q, set()).add(base)
                                    break
                        
                        # Build convertible map
                        for asset in assets_seen:
                            targets = list(edges.get(asset, set()))
                            if targets:
                                binance_map[asset] = targets
                    else:
                        # Fallback: assume all major pairs (non-UK)
                        blues = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT", "LINK", "LTC"]
                        stables = ["USDT", "USDC", "GBP", "EUR"]
                        for asset in blues + stables:
                            targets = [a for a in blues + stables if a != asset]
                            binance_map[asset] = targets
                    
                    paths["binance"] = binance_map
                
                # Kraken: simplified USD-based, with restricted asset blacklist
                if engine.kraken:
                    # Use global KRAKEN_BLACKLIST constant
                    blues = ["BTC", "ETH", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "LTC", "ATOM"]
                    blues = [b for b in blues if b not in KRAKEN_BLACKLIST]
                    
                    kraken_map: Dict[str, List[str]] = {}
                    for asset in blues + ["USD"]:
                        targets = [a for a in blues + ["USD"] if a != asset]
                        kraken_map[asset] = targets
                    paths["kraken"] = kraken_map
                
                return paths

            def find_conversion_path(self, exchange: str, from_asset: str, to_asset: str) -> List[Dict[str, Any]]:
                """Find the best conversion path using the Labyrinth Mapper."""
                # Use the labyrinth for intelligent pathfinding
                if hasattr(engine, 'labyrinth') and engine.labyrinth:
                    path = engine.labyrinth.find_path(from_asset, to_asset, preferred_exchange=exchange)
                    if path:
                        logger.debug(f"🌀 Labyrinth found path: {from_asset} → {to_asset} ({len(path)} hops)")
                        return path
                
                # Fallback: single-hop path
                return [{"from": from_asset, "to": to_asset, "exchange": exchange}]

            def convert_to_quote(self, exchange: str, asset: str, qty: float, quote: str) -> float:
                """Estimate USD value of asset qty."""
                if asset in ("USD", "USDT", "USDC"):
                    return float(qty)
                try:
                    if exchange == "binance" and engine.binance:
                        symbol = f"{asset}{quote}"
                        price = float(engine.binance.best_price(symbol).get("price", 0) or 0)
                        return qty * price
                    if exchange == "kraken" and engine.kraken:
                        symbol = f"{asset}USD"
                        ticker = engine.kraken.get_ticker(symbol)
                        price = float(ticker.get("price", 0) or 0)
                        return qty * price
                except Exception:
                    pass
                return 0.0

            def convert_crypto(self, exchange: str, from_asset: str, to_asset: str, amount: float) -> Dict[str, Any]:
                """Execute actual conversion via exchange using Labyrinth pathfinding."""
                
                # === TRACK INPUT VALUE FOR PROFIT CALCULATION ===
                input_value_usd = self.convert_to_quote(exchange, from_asset, amount, "USDT")
                if input_value_usd == 0 and from_asset in ("USD", "USDT", "USDC"):
                    input_value_usd = amount
                
                # === USE LABYRINTH FOR INTELLIGENT PATHFINDING ===
                if hasattr(engine, 'labyrinth') and engine.labyrinth:
                    path = engine.labyrinth.find_path(from_asset, to_asset, preferred_exchange=exchange)
                    if path and len(path) > 0:
                        logger.info(f"🌀 Labyrinth conversion: {from_asset} → {to_asset} via {len(path)} hops")
                        
                        current_amount = amount
                        all_orders = []
                        
                        for step in path:
                            step_exchange = step.get("exchange", exchange)
                            step_symbol = step.get("symbol", "")
                            step_direction = step.get("direction", "SELL")
                            step_from = step.get("from")
                            step_to = step.get("to")
                            
                            logger.debug(f"🌀 Step: {step_from} → {step_to} via {step_symbol} ({step_direction}) on {step_exchange}")
                            
                            try:
                                if step_exchange == "binance" and engine.binance:
                                    if step_direction == "SELL":
                                        order = engine.binance.place_market_order(step_symbol, "SELL", quantity=current_amount)
                                    else:
                                        # For BUY, we use quote_qty
                                        order = engine.binance.place_market_order(step_symbol, "BUY", quote_qty=current_amount)
                                    
                                    if order and not order.get("error"):
                                        all_orders.append(order)
                                        # Update current amount for next hop
                                        if step_direction == "SELL":
                                            current_amount = float(order.get("cummulativeQuoteQty", 0) or 0)
                                        else:
                                            current_amount = float(order.get("executedQty", 0) or 0)
                                    else:
                                        logger.warning(f"🌀 Step failed: {order}")
                                        break
                                
                                elif step_exchange == "kraken" and engine.kraken:
                                    side = "sell" if step_direction == "SELL" else "buy"
                                    order = engine.kraken.place_market_order(step_symbol, side, quantity=current_amount)
                                    
                                    if order and not order.get("error"):
                                        all_orders.append(order)
                                        # Estimate next amount from price
                                        ticker = engine.kraken.get_ticker(step_symbol)
                                        price = float(ticker.get("price", 1) or 1)
                                        if step_direction == "SELL":
                                            current_amount = current_amount * price
                                        else:
                                            current_amount = current_amount / price if price > 0 else 0
                                    else:
                                        logger.warning(f"🌀 Kraken step failed: {order}")
                                        break
                            
                            except Exception as e:
                                logger.error(f"🌀 Step error: {e}")
                                break
                        
                        # === CALCULATE OUTPUT VALUE AND PROFIT ===
                        output_amount = current_amount
                        output_value_usd = self.convert_to_quote(exchange, to_asset, output_amount, "USDT")
                        if output_value_usd == 0 and to_asset in ("USD", "USDT", "USDC"):
                            output_value_usd = output_amount
                        
                        # Calculate net profit
                        net_profit = output_value_usd - input_value_usd
                        
                        # Record path usage WITH PROFIT to labyrinth
                        engine.labyrinth.record_path_usage(path, profit=net_profit, success=len(all_orders) > 0)
                        
                        # Record to Mycelium if available
                        if hasattr(engine, 'mycelium') and engine.mycelium and hasattr(engine.mycelium, 'record_conversion_profit'):
                            try:
                                engine.mycelium.record_conversion_profit({
                                    'from_asset': from_asset,
                                    'to_asset': to_asset,
                                    'exchange': exchange,
                                    'path': path,
                                    'input_amount': amount,
                                    'output_amount': output_amount,
                                    'input_value_usd': input_value_usd,
                                    'output_value_usd': output_value_usd,
                                    'fees': input_value_usd * 0.001 * len(path),  # Estimated fees
                                    'net_profit': net_profit,
                                    'success': len(all_orders) > 0,
                                    'hops': len(path),
                                })
                            except Exception:
                                pass
                        
                        if all_orders:
                            return {
                                "orders": all_orders, 
                                "hops": len(path), 
                                "converted": True, 
                                "path": path,
                                "input_value_usd": input_value_usd,
                                "output_value_usd": output_value_usd,
                                "net_profit": net_profit,
                            }
                
                # === FALLBACK: Direct exchange-specific conversion ===
                if exchange == "binance" and engine.binance:
                    try:
                        # === UK ACCOUNT AWARENESS ===
                        # Get UK-allowed pairs and only convert through permitted paths
                        uk_allowed = set()
                        if hasattr(engine.binance, "get_allowed_pairs_uk"):
                            uk_allowed = engine.binance.get_allowed_pairs_uk()
                        
                        logger.debug(f"🪜 Ladder: Converting {from_asset}→{to_asset}, UK pairs: {len(uk_allowed)}")
                        
                        # Find best conversion path through UK-allowed pairs
                        # UK accounts: Try USDC first, then EUR
                        is_uk = engine.binance.uk_mode
                        direct_pair = f"{from_asset}{to_asset}"
                        direct_pair_rev = f"{to_asset}{from_asset}"
                        
                        if uk_allowed and direct_pair in uk_allowed:
                            # Direct conversion: BUY to_asset using from_asset
                            logger.info(f"🪜 Direct UK path: {direct_pair}")
                            order = engine.binance.place_market_order(direct_pair, "BUY", quantity=amount)
                            return {"direct": order, "converted": True, "path": direct_pair}
                        
                        if uk_allowed and direct_pair_rev in uk_allowed:
                            # Reverse pair: SELL from_asset to get to_asset
                            logger.info(f"🪜 Reverse UK path: {direct_pair_rev}")
                            order = engine.binance.place_market_order(direct_pair_rev, "SELL", quantity=amount)
                            return {"direct_rev": order, "converted": True, "path": direct_pair_rev}
                        
                        # Find intermediate path (USDC first for UK, then EUR, then others)
                        if is_uk:
                            intermediates = ["USDC", "EUR", "BTC", "ETH"]  # UK-allowed intermediates
                        else:
                            intermediates = ["USDT", "USDC", "BTC", "ETH"]
                        for quote in intermediates:
                            sell_sym = f"{from_asset}{quote}"
                            buy_sym = f"{to_asset}{quote}"
                            
                            # Check both legs are UK-allowed
                            sell_ok = (not uk_allowed) or (sell_sym in uk_allowed)
                            buy_ok = (not uk_allowed) or (buy_sym in uk_allowed)
                            
                            logger.debug(f"🪜 Checking {quote} path: sell={sell_sym}({sell_ok}) buy={buy_sym}({buy_ok})")
                            
                            if sell_ok and buy_ok:
                                logger.info(f"🪜 UK path via {quote}: {sell_sym} → {buy_sym}")
                                # Sell from_asset to quote
                                sell_order = engine.binance.place_market_order(sell_sym, "SELL", quantity=amount)
                                if not sell_order or sell_order.get("error"):
                                    logger.warning(f"🪜 Sell failed: {sell_order}")
                                    continue  # Try next intermediate
                                
                                # Buy to_asset with proceeds
                                proceeds = float(sell_order.get("cummulativeQuoteQty", 0) or 0)
                                if proceeds <= 0:
                                    logger.warning(f"🪜 No proceeds from sell")
                                    continue
                                
                                buy_price = float(engine.binance.best_price(buy_sym).get("price", 1) or 1)
                                buy_qty = proceeds / buy_price if buy_price > 0 else 0
                                if buy_qty <= 0:
                                    continue
                                
                                buy_order = engine.binance.place_market_order(buy_sym, "BUY", quantity=buy_qty)
                                return {"sell": sell_order, "buy": buy_order, "via": quote, "converted": True}
                        
                        logger.warning(f"🪜 No UK-allowed conversion path from {from_asset} to {to_asset}")
                        return {"error": f"No UK-allowed conversion path from {from_asset} to {to_asset}"}
                    except Exception as e:
                        return {"error": str(e)}
                if exchange == "kraken" and engine.kraken:
                    try:
                        # Kraken uses USD as quote currency, not USDT
                        # Normalize target asset for Kraken
                        kraken_to = to_asset
                        if to_asset in ("USDT", "USDC"):
                            kraken_to = "USD"  # Kraken uses USD
                        
                        # Kraken: sell to USD then buy target (if not already stable)
                        sell_sym = f"{from_asset}USD"
                        logger.info(f"🪜 Kraken: Selling {amount:.4f} {from_asset} via {sell_sym}")
                        sell_order = engine.kraken.place_market_order(sell_sym, "sell", quantity=amount)
                        if not sell_order or sell_order.get("error"):
                            return {"error": f"kraken sell failed: {sell_order}"}
                        
                        # If target is USD, we're done
                        if kraken_to == "USD":
                            return {"sell": sell_order, "converted": True, "to": "USD"}
                        
                        # Otherwise buy target with proceeds
                        ticker = engine.kraken.get_ticker(sell_sym)
                        proceeds = amount * float(ticker.get("price", 0) or 0)
                        buy_sym = f"{kraken_to}USD"
                        buy_ticker = engine.kraken.get_ticker(buy_sym)
                        buy_price = float(buy_ticker.get("price", 1) or 1)
                        buy_qty = proceeds / buy_price if buy_price > 0 else 0
                        if buy_qty <= 0:
                            return {"error": "buy_qty zero"}
                        buy_order = engine.kraken.place_market_order(buy_sym, "buy", quantity=buy_qty)
                        return {"sell": sell_order, "buy": buy_order, "converted": True}
                    except Exception as e:
                        return {"error": str(e)}
                return {"error": f"unsupported exchange: {exchange}"}

        return LadderClientAdapter()
    
    def _get_total_cash(self) -> float:
        """Get total cash across all exchanges"""
        total = 0.0
        total += self.real_balances["binance"].get("USDT", 0)
        total += self.real_balances["kraken"].get("USD", 0)
        total += self.real_balances["alpaca"].get("USD", 0)
        
        # Fallback for simulation
        if total == 0 and self.simulation_mode:
            return 100.0
        return total
    
    def fetch_market_data(self) -> Dict:
        """Fetch fresh market data from ALL exchanges and pairs"""
        prices = {}
        changes = {}
        volumes = {}
        momentum = {}
        source = {}
        
        # BINANCE - Get all allowed pairs (not just USDT)
        if self.binance:
            try:
                # Get all tickers first
                all_tickers = self.binance.session.get(
                    f'{self.binance.base}/api/v3/ticker/24hr',
                    timeout=5
                ).json()
                
                # Get allowed pairs for UK account
                allowed_pairs = self.binance.get_allowed_pairs_uk()
                
                for t in all_tickers:
                    symbol = t['symbol']
                    
                    # Only include allowed pairs (respects UK restrictions)
                    if allowed_pairs and symbol not in allowed_pairs:
                        continue
                        
                    try:
                        prices[symbol] = float(t['lastPrice'])
                        changes[symbol] = float(t['priceChangePercent'])
                        volumes[symbol] = float(t['quoteVolume'])
                        # Calculate momentum from price change
                        momentum[symbol] = float(t['priceChangePercent']) / 100
                        source[symbol] = "binance"
                    except:
                        continue
                
                logger.debug(f"Binance: Loaded {len(prices)} market symbols")
                
            except Exception as e:
                logger.error(f"Binance market data error: {e}")
        
        # KRAKEN - Add Kraken pairs
        if self.kraken:
            try:
                # Get all Kraken 24h tickers
                kraken_tickers = self.kraken.get_24h_tickers()
                kraken_added = 0
                
                for ticker in kraken_tickers:
                    symbol = ticker.get('symbol', '')
                    if symbol in prices:
                        continue  # Skip if already have from Binance
                    
                    # GHOST SIGNAL PREVENTION: Skip blacklisted Kraken assets
                    base_asset = symbol.replace("USD", "").replace("USDT", "").replace("USDC", "").replace("EUR", "").replace("GBP", "")
                    if base_asset in KRAKEN_BLACKLIST:
                        continue
                    
                    try:
                        price = float(ticker.get('lastPrice', 0))
                        change = float(ticker.get('priceChangePercent', 0))
                        volume = float(ticker.get('quoteVolume', 0))
                        
                        if price > 0:
                            prices[symbol] = price
                            changes[symbol] = change
                            volumes[symbol] = volume
                            momentum[symbol] = change / 100 if change != 0 else 0
                            source[symbol] = "kraken"
                            kraken_added += 1
                    except:
                        continue
                
                logger.debug(f"Kraken: Added {kraken_added} market symbols (filtered {len(kraken_tickers) - kraken_added} blacklisted)")
                
            except Exception as e:
                logger.error(f"Kraken market data error: {e}")
        
        # ALPACA - Add stock data if available
        if self.alpaca:
            try:
                # Get some major stocks for additional signals
                stock_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']
                
                for symbol in stock_symbols:
                    try:
                        quote = self.alpaca.get_last_quote(symbol)
                        if quote:
                            price = float(quote.get('last', {}).get('price', 0))
                            if price > 0:
                                stock_symbol = f"{symbol}/USD"  # Alpaca format
                                prices[stock_symbol] = price
                                changes[stock_symbol] = 0  # No change data from quote
                                volumes[stock_symbol] = 0
                                momentum[stock_symbol] = 0
                                source[stock_symbol] = "alpaca"
                    except:
                        continue
                
                logger.debug(f"Alpaca: Added {len(stock_symbols)} stock symbols")
                
            except Exception as e:
                logger.error(f"Alpaca market data error: {e}")
        
        # If no real data, use simulation data
        if not prices:
            logger.warning("No market data available, using simulation data")
            # Simulation data - generate realistic opportunities
            import random
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOGEUSDT', 
                      'XRPUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT', 'MATICUSDT',
                      'LTCUSDT', 'BCHUSDT', 'ETCUSDT', 'XLMUSDT', 'TRXUSDT',
                      'VETUSDT', 'ICPUSDT', 'FILUSDT', 'HBARUSDT', 'NEARUSDT']
            base_prices = {
                'BTCUSDT': 95000, 'ETHUSDT': 3400, 'SOLUSDT': 200, 'ADAUSDT': 1.1,
                'DOGEUSDT': 0.32, 'XRPUSDT': 2.3, 'AVAXUSDT': 40, 'DOTUSDT': 7,
                'LINKUSDT': 22, 'MATICUSDT': 0.5, 'LTCUSDT': 65, 'BCHUSDT': 220,
                'ETCUSDT': 18, 'XLMUSDT': 0.09, 'TRXUSDT': 0.15, 'VETUSDT': 0.02,
                'ICPUSDT': 8, 'FILUSDT': 3.5, 'HBARUSDT': 0.05, 'NEARUSDT': 4.2
            }
            for symbol in symbols:
                # Create some momentum opportunities
                base = base_prices.get(symbol, 100)
                change = random.uniform(-8, 12)  # Wider range for more signals
                prices[symbol] = base * (1 + change / 100)
                changes[symbol] = change
                volumes[symbol] = random.uniform(100000, 10000000)
                momentum[symbol] = change / 100
        
        self.market_data = {
            "prices": prices,
            "changes": changes,
            "volumes": volumes,
            "momentum": momentum,
            "source": source,
            "timestamp": time.time()
        }
        
        logger.info(f"📊 Market Data: {len(prices)} symbols from all exchanges")
        logger.debug(f"Sample symbols: {list(prices.keys())[:10]}")
        logger.debug(f"Sample changes: {dict(list(changes.items())[:5])}")
        logger.debug(f"Sample momentum: {dict(list(momentum.items())[:5])}")
        return self.market_data
    
    def get_available_capital(self) -> float:
        """Get available trading capital from all exchanges (cash + asset values)"""
        # Use the total equity calculation which includes both cash and asset values
        if hasattr(self, 'total_equity') and self.total_equity > 0:
            return self.total_equity
        
        # Fallback: calculate manually
        total = 0.0
        
        # Get fresh balance data
        self._refresh_real_balances()
        
        # Add cash balances
        total += self.real_balances["binance"].get("USDT", 0)
        total += self.real_balances["kraken"].get("USD", 0)
        total += self.real_balances["alpaca"].get("USD", 0)
        
        # Fallback for simulation
        if total == 0 and self.simulation_mode:
            return 100.0
            
        return total
    
    def _validate_symbol_tradeable(self, symbol: str, exchange: str) -> tuple[bool, str]:
        """
        GHOST SIGNAL PREVENTION - Validate a symbol is actually tradeable.
        
        Checks:
        1. Symbol format is valid (has base + quote)
        2. Exchange client exists
        3. Symbol is allowed for UK account (Binance)
        4. Symbol exists on exchange
        5. Has sufficient price data
        
        Returns: (can_trade: bool, reason: str)
        """
        if not symbol or len(symbol) < 3:
            return False, "Invalid symbol format"
        
        exchange = (exchange or "binance").lower()
        
        # Check exchange client exists
        if exchange == "binance":
            if not self.binance:
                return False, "Binance client offline"
            # UK restriction check
            can_trade, reason = self.binance.can_trade_symbol(symbol)
            if not can_trade:
                return False, reason
            # Verify symbol exists with price
            try:
                price_data = self.binance.best_price(symbol)
                price = float(price_data.get("price", 0) or 0)
                if price <= 0:
                    return False, f"No price data for {symbol}"
            except Exception as e:
                return False, f"Price lookup failed: {e}"
        elif exchange == "kraken":
            if not self.kraken:
                return False, "Kraken client offline"
            # Verify symbol exists
            try:
                ticker = self.kraken.get_ticker(symbol)
                if not ticker or ticker.get("error"):
                    # Try with alternate format
                    alt_symbol = symbol.replace("USD", "ZUSD").replace("BTC", "XBT")
                    ticker = self.kraken.get_ticker(alt_symbol)
                    if not ticker or ticker.get("error"):
                        return False, f"Symbol {symbol} not found on Kraken"
            except Exception as e:
                return False, f"Kraken lookup failed: {e}"
        elif exchange == "alpaca":
            if not self.alpaca:
                return False, "Alpaca client offline"
            # Alpaca: assume valid if client exists (API validates on order)
        else:
            return False, f"Unknown exchange: {exchange}"
        
        return True, "OK"
    
    def _normalize_symbol_for_exchange(self, symbol: str, exchange: str) -> tuple[str, str]:
        """
        Normalize a symbol for a specific exchange and find correct format.
        
        Returns: (normalized_symbol, exchange) - may switch exchange if not available
        """
        exchange = (exchange or "binance").lower()
        symbol_upper = symbol.upper()
        
        # Try original format first
        can_trade, _ = self._validate_symbol_tradeable(symbol_upper, exchange)
        if can_trade:
            return symbol_upper, exchange
        
        # For Binance: try different quote currencies (USDC first for UK accounts)
        if exchange == "binance" and self.binance:
            # Extract base asset (assume symbol ends with common quote)
            base = symbol_upper
            for quote in ["USDT", "USD", "USDC", "BTC", "ETH", "GBP", "EUR", "BNB"]:
                if symbol_upper.endswith(quote):
                    base = symbol_upper[:-len(quote)]
                    break
            
            # UK accounts: try USDC first, non-UK: try USDT first
            if self.binance.uk_mode:
                quote_order = ["USDC", "EUR", "BTC", "ETH", "BNB"]
            else:
                quote_order = ["USDT", "USDC", "BTC", "ETH", "BNB"]
            
            for quote in quote_order:
                test_sym = f"{base}{quote}"
                can_trade, _ = self._validate_symbol_tradeable(test_sym, "binance")
                if can_trade:
                    return test_sym, "binance"
        
        # For Kraken: try USD format
        if exchange == "kraken" and self.kraken:
            base = symbol_upper
            for quote in ["USD", "ZUSD", "EUR", "XBT"]:
                if symbol_upper.endswith(quote):
                    base = symbol_upper[:-len(quote)]
                    break
            test_sym = f"{base}USD"
            can_trade, _ = self._validate_symbol_tradeable(test_sym, "kraken")
            if can_trade:
                return test_sym, "kraken"
        
        # Fallback: try other exchanges
        if exchange != "binance" and self.binance:
            # UK accounts: try USDC first
            quote_list = ["USDC", "EUR"] if self.binance.uk_mode else ["USDT", "USDC"]
            for quote in quote_list:
                base = symbol_upper.rstrip("USDTUSDCBTCETH")[:6]  # crude base extraction
                test_sym = f"{base}{quote}"
                can_trade, _ = self._validate_symbol_tradeable(test_sym, "binance")
                if can_trade:
                    return test_sym, "binance"
        
        # Not found anywhere
        return symbol_upper, exchange
    
    def run_cycle(self) -> Dict:
        """
        Run a complete trading cycle:
        1. Fetch market data (Reality layer)
        2. Refresh real exchange balances
        3. Inception dive (Russian dolls down to LIMBO)
        4. Sniper exit check (Million Kill Training)
        5. Scout reconnaissance (Patriot Intel)
        6. Update multiverse (10-9-1-10 consensus)
        7. Generate commando signals (exits + entries)
        8. Execute profitable actions
        9. Validate penny profits (timestamped)
        10. Sweep profits (Omega converter)
        """
        cycle_start = time.time()
        self.stats["cycles"] += 1
        
        result = {
            "cycle": self.stats["cycles"],
            "timestamp": cycle_start,
            "market_symbols": 0,
            "real_cash_balance": 0.0,
            "inception_dive": {},
            "sniper_exits": [],
            "scout_intel": [],
            "multiverse_consensus": {},
            "commando_signals": [],
            "executions": [],
            "sweeps": [],
            "penny_profits_validated": []
        }
        
        # 1. FETCH MARKET DATA
        market_data = self.fetch_market_data()
        result["market_symbols"] = len(market_data.get("prices", {}))

        # Mycelium step (distributed intelligence) using summarized market stats
        if self.mycelium:
            try:
                changes = list(market_data.get("changes", {}).values())
                momentum_val = sum(changes) / len(changes) / 100 if changes else 0.0
                volatility_val = (max(changes) - min(changes)) / 100 if len(changes) >= 2 else 0.1
                price_val = market_data.get("prices", {}).get("BTCUSDT", next(iter(market_data.get("prices", {}).values()), 95000))
                myc_market = {
                    "momentum": momentum_val,
                    "volatility": volatility_val,
                    "price": price_val
                }
                myc_state = self.mycelium.step(myc_market)
                result["mycelium_state"] = myc_state
            except Exception as e:
                result["mycelium_state_error"] = str(e)

        # Mycelium directive (top-level control): gates entries and modulates sizing
        self.mycelium_directive = self._compute_mycelium_directive(result.get("mycelium_state"), market_data)
        result["mycelium_directive"] = dict(self.mycelium_directive)
        self._publish_mycelium_directive(self.mycelium_directive)

        # Publish/update the full connection graph periodically (and expose in results)
        if self.stats.get("cycles", 0) <= 1 or (self.stats.get("cycles", 0) % 5 == 0):
            conn = self._update_mycelium_connections()
            if conn:
                result["ecosystem_connections"] = conn
            
            # Rebuild labyrinth periodically
            if hasattr(self, 'labyrinth') and self.labyrinth:
                labyrinth_stats = self.labyrinth.build_labyrinth()
                path_stats = self.labyrinth.get_path_stats()
                result["labyrinth"] = {
                    "assets": labyrinth_stats.get("nodes", 0),
                    "paths": labyrinth_stats.get("edges", 0),
                    "binance_pairs": labyrinth_stats.get("binance_pairs", 0),
                    "kraken_pairs": labyrinth_stats.get("kraken_pairs", 0),
                    "cached": labyrinth_stats.get("cached", True),
                    # 🔄 PROFIT METRICS
                    "total_conversions": path_stats.get("total_conversions", 0),
                    "total_profit": path_stats.get("total_profit", 0),
                    "best_path": path_stats.get("best_path"),
                    "best_path_profit": path_stats.get("best_path_profit", 0),
                    "top_profitable": path_stats.get("top_profitable", []),
                }
        
        # 2. REFRESH REAL EXCHANGE BALANCES (every cycle)
        self._refresh_real_balances()
        result["real_cash_balance"] = self._get_total_cash()

        # Governing metrics: Mycelium reads the whole system and governs growth
        self._update_mycelium_governing_metrics()
        
        # 3. INCEPTION DIVE - Russian Doll probability (REALITY → DREAM_1 → DREAM_2 → LIMBO)
        # This is THE LIMITLESS PILL - mathematical guidance before consensus/commando
        inception_signals: List[CommandoSignal] = []
        if INCEPTION_AVAILABLE and _inception_engine:
            inception_result = _inception_engine.dive(market_data)
            result["inception_dive"] = {
                "dive_number": inception_result.get("dive_number", 0),
                "dive_time_ms": inception_result.get("dive_time_ms", 0),
                "wisdom_depth": inception_result.get("wisdom_depth", 0),
                "execution_plan": inception_result.get("execution_plan", [])
            }

            for plan in inception_result.get("execution_plan", []):
                if plan.get("action") != "BUY":
                    continue
                confidence = plan.get("confidence", 0)
                if confidence < 0.4:  # Lowered from 0.65 to 0.4
                    continue
                symbol = plan.get("symbol")
                if not symbol:
                    continue
                source_map = market_data.get("source", {})
                target_exchange = source_map.get(symbol, "binance")
                
                # GHOST SIGNAL PREVENTION: Validate symbol is tradeable before creating signal
                validated_symbol, validated_exchange = self._validate_symbol_tradeable(symbol, target_exchange)
                if not validated_symbol:
                    logger.debug(f"🚫 INCEPTION: Skipping {symbol} - not tradeable on {target_exchange}")
                    continue
                
                # Build a commando-style signal so it flows through the same execution path
                inception_signal = CommandoSignal(
                    timestamp=time.time(),
                    symbol=validated_symbol,
                    exchange=validated_exchange,
                    action="BUY",
                    strength=min(1.0, confidence),
                    confidence=confidence,
                    source="INCEPTION_KICK",
                    reason=f"Inception depth {len(plan.get('depth_traversed', []))} | LIMITLESS PILL",
                    profit_path="MOMENTUM",
                    expected_profit=max(MIN_PROFIT_TARGET, 0.01),
                    commando_type="FALCON"
                )
                inception_signals.append(inception_signal)
                logger.info(
                    f"🎬 INCEPTION: BUY {validated_symbol} on {validated_exchange} (confidence: {confidence:.2f}, depth: {len(plan.get('depth_traversed', []))})"
                )
        
        # 3.5. QUANTUM TELESCOPE - Multi-Dimensional Geometric Analysis
        # Uses 5 Platonic Solid lenses to refract market data into probability spectrum
        quantum_observations = {}
        if self.quantum_telescope:
            try:
                prices = market_data.get("prices", {})
                volumes = market_data.get("volumes", {})
                changes = market_data.get("changes", {})
                
                # Observe top movers through the telescope
                top_movers = sorted(changes.items(), key=lambda x: abs(x[1]), reverse=True)[:10]
                for symbol, change in top_movers:
                    price = prices.get(symbol, 0)
                    volume = volumes.get(symbol, 10000)
                    if price > 0:
                        observation = self.quantum_telescope.observe(
                            symbol=symbol,
                            price=price,
                            volume=volume,
                            change_pct=change
                        )
                        quantum_observations[symbol] = observation
                        
                        # Log high-alignment observations
                        if observation['geometric_alignment'] > 0.7:
                            logger.info(
                                f"🔭 QUANTUM: {symbol} | Alignment: {observation['geometric_alignment']:.2f} | "
                                f"Dominant: {observation['dominant_solid']} | Prob: {observation['probability_spectrum']:.1%}"
                            )
                
                result["quantum_telescope"] = {
                    "observations": len(quantum_observations),
                    "high_alignment_count": sum(1 for o in quantum_observations.values() if o['geometric_alignment'] > 0.7),
                    "top_probability": max((o['probability_spectrum'] for o in quantum_observations.values()), default=0)
                }
            except Exception as e:
                logger.warning(f"🔭 Quantum Telescope error: {e}")
        
        # 4. SNIPER EXIT CHECK - Million Kill Training (check positions for sniper exits)
        sniper_signals: List[CommandoSignal] = []
        if self.sniper and self.positions:
            prices_list = list(market_data.get("prices", {}).values())[:50]
            volumes_list = list(market_data.get("volumes", {}).values())[:50]
            
            for symbol, pos in list(self.positions.items()):
                current_price = market_data.get("prices", {}).get(symbol, pos.get("entry_price", 0))
                entry_value = pos.get("quantity", 0) * pos.get("entry_price", current_price)
                current_value = pos.get("quantity", 0) * current_price
                pos_exchange = pos.get("exchange", "binance")
                
                try:
                    sniper_signal = self.sniper.check_exit(
                        symbol=symbol,
                        entry_value=entry_value,
                        current_value=current_value,
                        hold_cycles=pos.get("hold_cycles", 0)
                    )
                    
                    if sniper_signal.action == 'EXIT_WIN':
                        # Sniper confirms penny profit!
                        sniper_cmd = CommandoSignal(
                            timestamp=time.time(),
                            symbol=symbol,
                            exchange=pos_exchange,
                            action="SELL",
                            strength=sniper_signal.confidence,
                            confidence=sniper_signal.confidence,
                            source="SNIPER_KILL",
                            reason=f"🎯 Sniper Kill! Gross: ${sniper_signal.current_gross:.4f} >= Threshold: ${sniper_signal.penny_threshold:.4f}",
                            profit_path="SNIPER_EXIT",
                            expected_profit=sniper_signal.current_gross * 0.9,  # Net after fees
                            commando_type="BEE"
                        )
                        sniper_signals.append(sniper_cmd)
                        result["sniper_exits"].append({
                            "symbol": symbol,
                            "gross_pnl": sniper_signal.current_gross,
                            "threshold": sniper_signal.penny_threshold,
                            "confidence": sniper_signal.confidence
                        })
                        self.stats["sniper_kills"] += 1
                        logger.info(f"🎯 SNIPER KILL: {symbol} | Gross: ${sniper_signal.current_gross:.4f}")
                except Exception as e:
                    logger.debug(f"Sniper check error for {symbol}: {e}")
        
        # 5. SCOUT RECONNAISSANCE - Patriot Intel (find opportunities)
        scout_signals: List[CommandoSignal] = []
        if self.scout_network:
            try:
                source_map = market_data.get("source", {})
                # Use scouts to scan for opportunities
                for symbol, price in list(market_data.get("prices", {}).items())[:20]:
                    change = market_data.get("changes", {}).get(symbol, 0)
                    momentum = market_data.get("momentum", {}).get(symbol, 0)
                    
                    # Scout criteria: Strong momentum + not already positioned
                    if symbol not in self.positions and abs(change) > 2.0 and momentum > 0.01:
                        target_exchange = source_map.get(symbol, "binance")
                        
                        # GHOST SIGNAL PREVENTION: Validate symbol is tradeable
                        validated_symbol, validated_exchange = self._validate_symbol_tradeable(symbol, target_exchange)
                        if not validated_symbol:
                            logger.debug(f"🚫 SCOUT: Skipping {symbol} - not tradeable on {target_exchange}")
                            continue
                        
                        scout_cmd = CommandoSignal(
                            timestamp=time.time(),
                            symbol=validated_symbol,
                            exchange=validated_exchange,
                            action="BUY",
                            strength=min(1.0, abs(change) / 10),
                            confidence=min(0.85, 0.5 + abs(change) / 20),
                            source="SCOUT_INTEL",
                            reason=f"☘️ Scout Intel: {validated_symbol} momentum {change:+.1f}%",
                            profit_path="MOMENTUM",
                            expected_profit=0.01,
                            commando_type="FALCON"
                        )
                        scout_signals.append(scout_cmd)
                        result["scout_intel"].append({
                            "symbol": validated_symbol,
                            "exchange": validated_exchange,
                            "change": change,
                            "momentum": momentum
                        })
            except Exception as e:
                logger.debug(f"Scout network error: {e}")
        
        # 6. UPDATE MULTIVERSE
        if self.multiverse:
            self.multiverse.update_market_data(market_data)
            multiverse_result = self.multiverse.run_cycle()
            result["multiverse_consensus"] = multiverse_result.get("consensus", {})
        
        # 7. GENERATE COMMANDO SIGNALS
        # First, process sniper exit signals (highest priority - guaranteed profit)
        for sniper_sig in sniper_signals:
            result["commando_signals"].append(sniper_sig.to_dict())
            self.stats["signals_generated"] += 1
            exec_result = self.execute_signal(sniper_sig)
            result["executions"].append(exec_result)
            
            # Validate penny profit with timestamp
            if exec_result.get("executed") and sniper_sig.expected_profit > 0:
                entry = self.penny_ledger.validate_and_record(
                    symbol=sniper_sig.symbol,
                    exchange=sniper_sig.exchange,
                    gross_pnl=sniper_sig.expected_profit / 0.9,  # Reverse the net calculation
                    fees=sniper_sig.expected_profit * 0.1,
                    source="SNIPER"
                )
                result["penny_profits_validated"].append(entry.to_dict())
        
        # Check existing positions for commando exit signals
        for symbol, pos in list(self.positions.items()):
            current_price = market_data.get("prices", {}).get(symbol, pos.get("entry_price", 0))
            pos_exchange = (pos.get("exchange") or "binance")
            signal = self.commando.evaluate_profit_path(
                asset=symbol,
                exchange=pos_exchange,
                current_value=pos.get("quantity", 0) * current_price,
                entry_price=pos.get("entry_price", current_price),
                current_price=current_price,
                market_data=market_data
            )
            
            if signal.action in ["SELL", "CONVERT"]:
                result["commando_signals"].append(signal.to_dict())
                self.stats["signals_generated"] += 1
                
                # Execute if profitable
                if signal.expected_profit >= MIN_PROFIT_TARGET:
                    exec_result = self.execute_signal(signal)
                    result["executions"].append(exec_result)
                    
                    # Validate penny profit with timestamp
                    if exec_result.get("executed") and signal.expected_profit > 0:
                        entry = self.penny_ledger.validate_and_record(
                            symbol=symbol,
                            exchange=signal.exchange,
                            gross_pnl=signal.expected_profit * 1.1,
                            fees=signal.expected_profit * 0.1,
                            source="COMMANDO"
                        )
                        result["penny_profits_validated"].append(entry.to_dict())
        
        # 8. Check for new entry opportunities
        available_capital = self.get_available_capital()

        # Track entry count so Mycelium can throttle per-cycle
        entries_executed = 0

        # First, honor INCEPTION signals (deepest wisdom) before normal entries
        for inc_sig in inception_signals:
            if inc_sig.symbol in self.positions:
                continue
            if available_capital < 1.0:
                break
            result["commando_signals"].append(inc_sig.to_dict())
            self.stats["signals_generated"] += 1
            mv_consensus = result["multiverse_consensus"].get(inc_sig.symbol, {}) if self.multiverse else {}
            # Execute if: multiverse agrees OR high confidence OR simulation mode
            should_execute = (
                mv_consensus.get("agreement", 0) > 0.5 or 
                inc_sig.confidence > 0.7 or
                self.simulation_mode
            )
            if should_execute and self._mycelium_allows_entry(inc_sig, entries_executed=entries_executed):
                exec_result = self.execute_signal(inc_sig)
                result["executions"].append(exec_result)
                if exec_result.get("executed") and inc_sig.action == "BUY":
                    entries_executed += 1
                if not self.simulation_mode:
                    available_capital = self.get_available_capital()

        # Mycelium queen signal guidance (distributed intelligence)
        queen_signal = None
        if result.get("mycelium_state"):
            queen_signal = result["mycelium_state"].get("queen_signal")
        # If queen says BUY (>0.4), take top momentum; if SELL (<-0.4), trim largest position
        if queen_signal is not None and abs(queen_signal) > 0.4:
            changes_map = market_data.get("changes", {})
            source_map = market_data.get("source", {})
            top_symbol = None
            if queen_signal > 0:
                # pick strongest positive mover not already held
                top_symbol = max((s for s in changes_map if s not in self.positions), key=lambda s: changes_map[s], default=None)
            else:
                # if negative, pick largest position to exit
                top_symbol = max(self.positions, key=lambda s: self.positions[s].get("quantity", 0), default=None)

            if top_symbol and available_capital >= 1.0:
                action = "BUY" if queen_signal > 0 else "SELL"
                target_exchange = source_map.get(top_symbol, "binance")
                
                # GHOST SIGNAL PREVENTION: Validate symbol is tradeable (for BUY)
                if action == "BUY":
                    validated_symbol, validated_exchange = self._validate_symbol_tradeable(top_symbol, target_exchange)
                    if not validated_symbol:
                        logger.debug(f"🚫 MYCELIUM_QUEEN: Skipping {top_symbol} - not tradeable on {target_exchange}")
                        top_symbol = None  # Skip this signal
                    else:
                        top_symbol = validated_symbol
                        target_exchange = validated_exchange
                
                if top_symbol:  # Only proceed if we have a valid symbol
                    strength = min(1.0, abs(queen_signal))
                    qs = CommandoSignal(
                        timestamp=time.time(),
                        symbol=top_symbol,
                        exchange=target_exchange,
                        action=action,
                        strength=strength,
                        confidence=strength,
                        source="MYCELIUM_QUEEN",
                        reason=f"Mycelium queen signal {queen_signal:+.2f}",
                        profit_path="MOMENTUM" if action == "BUY" else "QUEEN_EXIT",
                        expected_profit=0.01,
                        commando_type="FALCON" if action == "BUY" else "BEE"
                    )
                    result["commando_signals"].append(qs.to_dict())
                    self.stats["signals_generated"] += 1
                    exec_result = self.execute_signal(qs)
                    result["executions"].append(exec_result)
                    if not self.simulation_mode:
                        available_capital = self.get_available_capital()
        
        # Now process SCOUT signals (Celtic Intelligence)
        for scout_sig in scout_signals[:3]:  # Hard cap; Mycelium may further throttle
            if scout_sig.symbol in self.positions:
                continue
            if available_capital < 1.0:
                break
            result["commando_signals"].append(scout_sig.to_dict())
            self.stats["signals_generated"] += 1
            
            # Scouts get multiverse validation
            mv_consensus = result["multiverse_consensus"].get(scout_sig.symbol, {}) if self.multiverse else {}
            should_execute = (
                mv_consensus.get("agreement", 0) > 0.4 or
                scout_sig.confidence > 0.65 or
                self.simulation_mode
            )
            
            if should_execute:
                if self._mycelium_allows_entry(scout_sig, entries_executed=entries_executed):
                    exec_result = self.execute_signal(scout_sig)
                    result["executions"].append(exec_result)
                    self.stats["scout_profits"] += scout_sig.expected_profit
                    if exec_result.get("executed") and scout_sig.action == "BUY":
                        entries_executed += 1
                if not self.simulation_mode:
                    available_capital = self.get_available_capital()
        
        # Finally, commando entry signals
        logger.debug(f"Checking commando signals: capital=${available_capital:.2f}, positions={len(self.positions)}")
        if available_capital > 1.0:  # Lowered threshold from 10
            entry_signal = self.commando.get_best_entry_signal(market_data, available_capital)
            if entry_signal:
                # GHOST SIGNAL PREVENTION: Validate symbol is tradeable
                validated_symbol, validated_exchange = self._validate_symbol_tradeable(
                    entry_signal.symbol, entry_signal.exchange
                )
                if not validated_symbol:
                    logger.debug(f"🚫 COMMANDO: Skipping {entry_signal.symbol} - not tradeable on {entry_signal.exchange}")
                    entry_signal = None  # Nullify the ghost signal
                else:
                    # Update signal with validated symbol/exchange
                    entry_signal.symbol = validated_symbol
                    entry_signal.exchange = validated_exchange
                
            if entry_signal:
                # 🔭 QUANTUM TELESCOPE CONFIDENCE BOOST
                # Use geometric alignment to enhance signal confidence
                quantum_boost = 0.0
                if quantum_observations and entry_signal.symbol in quantum_observations:
                    obs = quantum_observations[entry_signal.symbol]
                    geo_align = obs.get('geometric_alignment', 0)
                    prob_spec = obs.get('probability_spectrum', 0.5)
                    dominant = obs.get('dominant_solid', 'UNKNOWN')
                    
                    # Boost based on geometric alignment and probability
                    quantum_boost = (geo_align * 0.15) + ((prob_spec - 0.5) * 0.10)
                    entry_signal.confidence = min(1.0, entry_signal.confidence + quantum_boost)
                    
                    if quantum_boost > 0.05:
                        logger.info(
                            f"🔭 QUANTUM BOOST: {entry_signal.symbol} +{quantum_boost:.1%} "
                            f"(align={geo_align:.2f}, prob={prob_spec:.1%}, solid={dominant})"
                        )
                
                logger.info(f"🎯 COMMANDO SIGNAL: {entry_signal.action} {entry_signal.symbol} on {entry_signal.exchange} (conf: {entry_signal.confidence:.2f})")
                result["commando_signals"].append(entry_signal.to_dict())
                self.stats["signals_generated"] += 1
                
                # Execute if confidence is reasonable
                should_execute = (
                    entry_signal.confidence > 0.4 or  # Lowered threshold
                    self.simulation_mode
                )
                
                if should_execute:
                    if self._mycelium_allows_entry(entry_signal, entries_executed=entries_executed):
                        logger.info(f"✅ EXECUTING COMMANDO: {entry_signal.action} {entry_signal.symbol}")
                        exec_result = self.execute_signal(entry_signal)
                        result["executions"].append(exec_result)
                        if exec_result.get("executed") and entry_signal.action == "BUY":
                            entries_executed += 1
        
        # 9. SWEEP PROFITS (via Omega Converter)
        if self.multiverse:
            sweeps = self.multiverse.converter.sweep_all(self.multiverse.worlds, market_data)
            result["sweeps"] = sweeps
            self.stats["sweeps_performed"] += len(sweeps)
            
            # Record sweeps to Revenue Board and Penny Ledger
            if sweeps:
                for sweep in sweeps:
                    profit = sweep.get("profit", 0)
                    if self.revenue_board:
                        self.revenue_board.record_sweep(
                            from_world=sweep.get("from_world", "unknown"),
                            amount=profit,
                            reason=sweep.get("reason", "PROFIT_SWEEP")
                        )
                    # Validate sweep profit with timestamp
                    if profit > 0:
                        entry = self.penny_ledger.validate_and_record(
                            symbol=sweep.get("from_world", "SWEEP"),
                            exchange="MULTIVERSE",
                            gross_pnl=profit,
                            fees=0,  # Sweeps are internal
                            source="SWEEP"
                        )
                        result["penny_profits_validated"].append(entry.to_dict())
                        
                        # Publish validated profit to ThoughtBus
                        if self.thought_bus:
                            try:
                                self.thought_bus.publish(Thought(
                                    source="penny_ledger",
                                    topic="profit.validated",
                                    payload={
                                        "symbol": sweep.get("from_world", "SWEEP"),
                                        "net_profit": entry.net_profit,
                                        "timestamp": entry.timestamp,
                                        "source": "SWEEP",
                                        "validated": entry.validated
                                    }
                                ))
                            except Exception:
                                pass

        # 10. CONVERSION LADDER - A-Z / Z-A Full Spectrum Sweep (Capital Rotation)
        if self.ladder and self.ladder.enabled:
            try:
                # Determine scan direction from Mycelium directive
                directive = self.mycelium_directive or {}
                mode = directive.get("mode", "NEUTRAL")
                if mode == "RISK_ON":
                    scan_dir = "A→Z"  # Climb into risk assets
                elif mode == "RISK_OFF":
                    scan_dir = "Z→A"  # De-risk into stables
                else:
                    scan_dir = "A→Z"  # Default forward sweep

                # Gather preferred symbols from market movers
                preferred = list(directive.get("preferred_symbols", []) or [])[:10]

                ladder_decision = self.ladder.step(
                    ticker_cache=market_data.get("prices", {}),
                    scan_direction=scan_dir,
                    net_profit=float(self.stats.get("total_profit", 0.0) or 0.0),
                    portfolio_equity=float(self.total_equity or 0.0),
                    preferred_assets=preferred,
                    locked_assets=list(self.positions.keys()),  # Don't rotate open positions
                )

                if ladder_decision:
                    # Log full decision for debugging
                    logger.info(
                        f"🪜 LADDER DECISION: {ladder_decision.from_asset}({ladder_decision.amount:.4f}) → "
                        f"{ladder_decision.to_asset} [{ladder_decision.direction}] on {ladder_decision.exchange}"
                    )
                    
                    result["ladder_decision"] = {
                        "direction": ladder_decision.direction,
                        "exchange": ladder_decision.exchange,
                        "from": ladder_decision.from_asset,
                        "to": ladder_decision.to_asset,
                        "amount": ladder_decision.amount,
                        "mode": ladder_decision.mode,
                        "result": ladder_decision.result,
                    }
                    self.stats["conversions_performed"] += 1

                    # Log the conversion
                    if ladder_decision.result and ladder_decision.result.get("converted"):
                        logger.info(
                            f"🪜 LADDER CONVERTED: {ladder_decision.from_asset} → {ladder_decision.to_asset} "
                            f"({ladder_decision.direction}) on {ladder_decision.exchange}"
                        )
                    elif ladder_decision.result and ladder_decision.result.get("error"):
                        logger.warning(f"🪜 Ladder error: {ladder_decision.result.get('error')}")
                    else:
                        logger.info(
                            f"🪜 LADDER SUGGEST: {ladder_decision.from_asset} → {ladder_decision.to_asset} "
                            f"({ladder_decision.direction})"
                        )
            except Exception as e:
                logger.debug(f"Ladder step error: {e}")
        
        # 11. LABYRINTH ARBITRAGE - Find profitable conversion paths across exchanges
        labyrinth_opportunities = []
        if hasattr(self, 'labyrinth') and self.labyrinth:
            try:
                prices = market_data.get("prices", {})
                
                # Check for cross-exchange arbitrage opportunities
                # Look at our positioned assets and find better paths to profit
                for symbol, pos in list(self.positions.items()):
                    # Extract base asset from symbol (e.g., BTCUSDT -> BTC)
                    # MUST use endswith() — .replace() corrupts symbols like ETHFI, BTCB
                    base_asset = symbol
                    for _q in ['USDT', 'USDC', 'BUSD', 'USD', 'BTC', 'ETH']:
                        if symbol.endswith(_q):
                            base_asset = symbol[:-len(_q)]
                            break
                    if not base_asset or len(base_asset) < 2:
                        continue
                    
                    # Find best path to stable coin (USD/USDT/USDC)
                    for target in ["USDT", "USDC", "USD"]:
                        best_path = self.labyrinth.get_best_path(base_asset, target)
                        if best_path and len(best_path) > 0:
                            # Estimate conversion efficiency
                            pos_value = pos.get("quantity", 0) * prices.get(symbol, pos.get("entry_price", 0))
                            cost_est = self.labyrinth.estimate_conversion_cost(best_path, pos_value, prices)
                            
                            # If path is efficient (>99% output), record the opportunity
                            if cost_est.get("efficiency", 0) > 0.99:
                                labyrinth_opportunities.append({
                                    "from": base_asset,
                                    "to": target,
                                    "hops": cost_est.get("hops", 0),
                                    "efficiency": cost_est.get("efficiency", 0),
                                    "estimated_fees": cost_est.get("fees", 0),
                                    "path": " → ".join([s.get("symbol", "?") for s in best_path]) if best_path else "direct"
                                })
                                
                                # Record this path usage
                                self.labyrinth.record_path_usage(
                                    path=best_path,
                                    slippage=cost_est.get("slippage", 0),
                                    profit=0  # Will update after actual conversion
                                )
                
                if labyrinth_opportunities:
                    result["labyrinth_opportunities"] = labyrinth_opportunities
                    logger.info(f"🌀 LABYRINTH: Found {len(labyrinth_opportunities)} efficient conversion paths")
                    
                    # Log the most efficient path
                    best_opp = max(labyrinth_opportunities, key=lambda x: x["efficiency"])
                    logger.info(
                        f"🌀 Best Path: {best_opp['from']} → {best_opp['to']} "
                        f"({best_opp['hops']} hops, {best_opp['efficiency']:.2%} efficiency)"
                    )
                    
            except Exception as e:
                logger.debug(f"Labyrinth scan error: {e}")
        
        result["cycle_time_ms"] = (time.time() - cycle_start) * 1000
        return result
    
    def execute_signal(self, signal: CommandoSignal) -> Dict:
        """Execute a trading signal"""
        exec_result = {
            "signal": signal.to_dict(),
            "executed": False,
            "order_id": None,
            "error": None
        }

        exchange = (signal.exchange or "binance").lower()
        
        # FINAL SAFETY GATE: Validate symbol is tradeable before execution (BUY only)
        if signal.action == "BUY" and not self.simulation_mode:
            validated_symbol, validated_exchange = self._validate_symbol_tradeable(signal.symbol, exchange)
            if not validated_symbol:
                exec_result["error"] = f"GHOST SIGNAL BLOCKED: {signal.symbol} not tradeable on {exchange}"
                logger.warning(f"🚫 BLOCKED: {signal.symbol} on {exchange} - not tradeable (source: {signal.source})")
                return exec_result
            # Update signal with validated values
            signal.symbol = validated_symbol
            signal.exchange = validated_exchange
            exchange = validated_exchange

        if self.simulation_mode:
            # Simulation execution - NO PROFIT COUNTING
            exec_result["executed"] = True
            exec_result["order_id"] = f"SIM_{int(time.time()*1000)}"
            self.stats["trades_executed"] += 1
            
            if signal.action == "BUY":
                self.positions[signal.symbol] = {
                    "entry_price": self.market_data.get("prices", {}).get(signal.symbol, 0),
                    "quantity": 10.0,  # Simulated
                    "entry_time": time.time()
                }
            elif signal.action == "SELL":
                if signal.symbol in self.positions:
                    del self.positions[signal.symbol]
            
            logger.info(f"🎯 EXECUTED (SIM): {signal.action} {signal.symbol} | "
                       f"Expected: ${signal.expected_profit:.4f} | {signal.reason}")
            
            # NO PROFIT RECORDING IN SIMULATION MODE
            # Record to Revenue Board (SIM - NO PnL)
            if self.revenue_board:
                price = self.market_data.get("prices", {}).get(signal.symbol, 0)
                self.revenue_board.record_trade(
                    symbol=signal.symbol,
                    exchange="SIMULATION",
                    side=signal.action,
                    quantity=10.0,
                    price=price,
                    fee=0.0,
                    pnl=0.0,  # NO SIMULATED PROFIT COUNTING
                    source="MULTIVERSE_SIM"
                )
        else:
            # LIVE EXECUTION ONLY - REAL PROFITS ONLY
            quantity = 0  # Initialize for revenue board
            realized_pnl = 0.0  # Initialize realized profit
            
            try:
                price = self.market_data.get("prices", {}).get(signal.symbol, 0)

                # Route to the correct exchange client
                client = None
                cash_available = 0.0
                fee_rate = 0.001  # default 0.1%

                if exchange == "binance":
                    client = self.binance
                    # UK accounts use USDC, non-UK use USDT (but stored under USDT key for compatibility)
                    cash_available = float(self.real_balances.get("binance", {}).get("USDT", 0.0) or 0.0)
                    fee_rate = 0.001
                elif exchange == "kraken":
                    client = self.kraken
                    cash_available = float(self.real_balances.get("kraken", {}).get("USD", 0.0) or 0.0)
                    fee_rate = 0.001
                elif exchange == "alpaca":
                    client = self.alpaca
                    cash_available = float(self.real_balances.get("alpaca", {}).get("USD", 0.0) or 0.0)
                    fee_rate = 0.001

                if client is None:
                    exec_result["error"] = f"Exchange offline or unsupported: {exchange}"
                    return exec_result
                
                if signal.action == "BUY":
                    # Final safety gate: Mycelium controls all entries (down to execution)
                    if not self._mycelium_allows_entry(signal, entries_executed=0, allow_throttle_bypass=True):
                        exec_result["error"] = "Blocked by Mycelium directive"
                        return exec_result

                    # Calculate quantity
                    entry_scale = float(self.mycelium_directive.get("entry_budget_scale", 1.0) or 1.0)
                    trade_size = cash_available * self.commando.growth_aggression * 0.2 * max(0.0, entry_scale)  # 20% per trade
                    quantity = trade_size / price if price > 0 else 0
                    
                    # Skip if quantity too small
                    if quantity <= 0:
                        exec_result["error"] = "Quantity too small"
                        return exec_result
                    
                    side = "buy" if exchange == "alpaca" else "BUY"
                    order = client.place_market_order(signal.symbol, side, quantity=quantity)

                    # Treat rejects/empty responses as non-executed
                    if not isinstance(order, dict) or order.get("rejected") or order.get("error"):
                        exec_result["error"] = f"Order rejected: {order}"
                        return exec_result
                    order_id = order.get("orderId") or order.get("id")
                    if not order_id:
                        exec_result["error"] = f"Order missing orderId: {order}"
                        return exec_result

                    exec_result["executed"] = True
                    exec_result["order_id"] = order_id
                    
                    # Store actual executed price and quantity
                    executed_price = float(order.get("price", price) or price)  # Use executed price if available
                    if executed_price <= 0:
                        executed_price = float(price or 0.0)
                    executed_qty = float(order.get("executedQty", quantity) or quantity)
                    
                    self.positions[signal.symbol] = {
                        "entry_price": executed_price,
                        "quantity": executed_qty,
                        "entry_time": time.time(),
                        "exchange": exchange,
                    }
                    
                elif signal.action == "SELL":
                    if signal.symbol in self.positions:
                        pos = self.positions[signal.symbol]
                        sell_qty = pos["quantity"]
                        entry_price = pos["entry_price"]
                        
                        # If position was entered on a different exchange, sell on that same exchange.
                        pos_exchange = (pos.get("exchange") or exchange).lower()
                        if pos_exchange != exchange:
                            exchange = pos_exchange
                            if exchange == "binance":
                                client = self.binance
                                fee_rate = 0.001
                            elif exchange == "kraken":
                                client = self.kraken
                                fee_rate = 0.001
                            elif exchange == "alpaca":
                                client = self.alpaca
                                fee_rate = 0.001

                        if client is None:
                            exec_result["error"] = f"Exchange offline for position sell: {exchange}"
                            return exec_result

                        side = "sell" if exchange == "alpaca" else "SELL"
                        order = client.place_market_order(signal.symbol, side, quantity=sell_qty)

                        # Treat rejects/empty responses as non-executed
                        if not isinstance(order, dict) or order.get("rejected") or order.get("error"):
                            exec_result["error"] = f"Order rejected: {order}"
                            return exec_result
                        order_id = order.get("orderId") or order.get("id")
                        if not order_id:
                            exec_result["error"] = f"Order missing orderId: {order}"
                            return exec_result

                        exec_result["executed"] = True
                        exec_result["order_id"] = order_id
                        exec_result["quantity"] = sell_qty
                        
                        # Calculate ACTUAL REALIZED PROFIT from executed trade
                        executed_sell_price = float(order.get("price", price) or price)
                        if executed_sell_price <= 0:
                            executed_sell_price = float(price or 0.0)
                        executed_sell_qty = float(order.get("executedQty", sell_qty) or sell_qty)
                        
                        # Realized PnL = (sell proceeds) - (entry cost) - fees
                        sell_proceeds = executed_sell_price * executed_sell_qty
                        entry_cost = entry_price * executed_sell_qty
                        fee = sell_proceeds * fee_rate
                        realized_pnl = sell_proceeds - entry_cost - fee
                        
                        # Record REAL profit in stats
                        self.stats["total_profit"] += realized_pnl
                        if realized_pnl > 0:
                            self.stats["win_count"] += 1
                        else:
                            self.stats["loss_count"] += 1
                        
                        del self.positions[signal.symbol]
                        
                        # Feed REAL profit to Mycelium for learning/compounding
                        if self.mycelium and realized_pnl > 0:
                            try:
                                self.mycelium.record_trade_profit(realized_pnl, {
                                    "symbol": signal.symbol,
                                    "action": signal.action,
                                    "exchange": signal.exchange
                                })
                            except Exception:
                                pass
                
                if exec_result.get("executed"):
                    self.stats["trades_executed"] += 1
                    logger.info(
                        f"✅ EXECUTED (LIVE): {signal.action} {signal.symbol} | "
                        f"Order: {exec_result['order_id']} | "
                        f"Realized PnL: ${realized_pnl:.4f}"
                    )
                
                # Record to Revenue Board (LIVE - REAL PnL)
                if self.revenue_board and exec_result.get("executed"):
                    trade_qty = quantity if signal.action == "BUY" else exec_result.get("quantity", 0)
                    trade_fee = abs(float(price or 0.0) * float(trade_qty or 0.0) * fee_rate)
                    self.revenue_board.record_trade(
                        symbol=signal.symbol,
                        exchange=exchange.upper(),
                        side=signal.action,
                        quantity=trade_qty,
                        price=price,
                        fee=abs(trade_fee),  # Always positive fee
                        pnl=realized_pnl if signal.action == "SELL" else 0.0,  # Only record PnL on sells
                        source="MULTIVERSE_LIVE"
                    )
                
            except Exception as e:
                exec_result["error"] = str(e)
                logger.error(f"❌ EXECUTION FAILED: {e}")
        
        # Record outcome in multiverse (only for real executed trades)
        if MULTIVERSE_AVAILABLE and exec_result["executed"] and not self.simulation_mode:
            multiverse_record_outcome(
                signal.symbol,
                realized_pnl > 0 if 'realized_pnl' in locals() else False,
                realized_pnl if 'realized_pnl' in locals() else 0.0
            )
        
        # Publish to ThoughtBus (UNIFIED COMMUNICATION)
        if self.thought_bus and exec_result.get("executed"):
            try:
                thought = Thought(
                    source="multiverse_live",
                    topic=f"trade.{signal.action.lower()}",
                    payload={
                        "symbol": signal.symbol,
                        "action": signal.action,
                        "exchange": signal.exchange,
                        "source": signal.source,
                        "realized_pnl": realized_pnl if 'realized_pnl' in locals() else 0.0,
                        "order_id": exec_result.get("order_id"),
                        "confidence": signal.confidence,
                        "commando_type": signal.commando_type
                    }
                )
                self.thought_bus.publish(thought)
            except Exception:
                pass  # Don't fail trade on thought bus error
        
        return exec_result

    def _compute_mycelium_directive(self, mycelium_state: Optional[Dict[str, Any]], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate Mycelium queen signal into an execution directive for all ecosystems."""
        queen_signal = None
        surge_active = False
        if isinstance(mycelium_state, dict):
            queen_signal = mycelium_state.get("queen_signal")
            surge_active = bool(mycelium_state.get("surge_active", False))

        # Default directive: allow normal flow
        directive: Dict[str, Any] = {
            "queen_signal": queen_signal,
            "surge_active": surge_active,
            "mode": "UNKNOWN" if queen_signal is None else "NEUTRAL",
            "allow_entries": True,
            "entry_budget_scale": 1.0,
            "entry_confidence_floor": 0.4,
            "max_entries_per_cycle": 3,
            "max_positions_total": 12,
            "preferred_symbols": [],
        }

        # If Mycelium has governing metrics, let its governor modulate the directive
        if self.mycelium and hasattr(self.mycelium, "get_growth_governor"):
            try:
                gov = self.mycelium.get_growth_governor() or {}
                # Only apply expected keys (avoid arbitrary payload injection)
                for k in ("allow_entries", "entry_budget_scale", "entry_confidence_floor", "max_entries_per_cycle", "max_positions_total"):
                    if k in gov:
                        directive[k] = gov[k]
                if gov.get("reason"):
                    directive["governor_reason"] = gov.get("reason")
            except Exception:
                pass

        # Build a preference list from current market movers (used to tighten control in neutral mode)
        changes_map = market_data.get("changes", {}) or {}
        if isinstance(changes_map, dict) and changes_map:
            # Top movers by % change
            sorted_syms = sorted(changes_map.keys(), key=lambda s: float(changes_map.get(s, 0) or 0), reverse=True)
            directive["preferred_symbols"] = sorted_syms[:20]

        if queen_signal is None:
            return directive

        try:
            q = float(queen_signal)
        except Exception:
            return directive

        # Strong BUY bias: loosen entry constraints + allow more entries
        if q >= 0.6:
            directive.update({
                "mode": "RISK_ON",
                "allow_entries": True,
                "entry_budget_scale": 1.25,
                "entry_confidence_floor": 0.35,
                "max_entries_per_cycle": 5,
            })
        elif q >= 0.4:
            directive.update({
                "mode": "RISK_ON",
                "allow_entries": True,
                "entry_budget_scale": 1.0,
                "entry_confidence_floor": 0.4,
                "max_entries_per_cycle": 4,
            })
        # Strong SELL bias: block new entries; focus on exits only
        elif q <= -0.4:
            directive.update({
                "mode": "RISK_OFF",
                "allow_entries": False,
                "entry_budget_scale": 0.0,
                "entry_confidence_floor": 1.0,
                "max_entries_per_cycle": 0,
            })
        # Neutral: tighten entries, and prefer top movers only
        else:
            directive.update({
                "mode": "NEUTRAL",
                "allow_entries": True,
                "entry_budget_scale": 0.5,
                "entry_confidence_floor": 0.7,
                "max_entries_per_cycle": 1,
                "preferred_symbols": directive.get("preferred_symbols", [])[:5],
            })

        # During surge windows, permit slightly more throughput
        if surge_active and directive.get("mode") != "RISK_OFF":
            directive["max_entries_per_cycle"] = max(int(directive.get("max_entries_per_cycle", 0)), 3)
            directive["entry_budget_scale"] = max(float(directive.get("entry_budget_scale", 1.0)), 1.0)

        return directive

    def _mycelium_allows_entry(
        self,
        signal: CommandoSignal,
        *,
        entries_executed: int,
        allow_throttle_bypass: bool = False,
    ) -> bool:
        """Centralized gate: Mycelium controls all BUY entries across ecosystems."""
        if self.simulation_mode:
            return True

        if signal.action != "BUY":
            return True

        directive = self.mycelium_directive or {}
        allow_entries = bool(directive.get("allow_entries", True))
        if not allow_entries:
            return False

        # Throttle per-cycle entries unless this is an execution-level bypass check
        if not allow_throttle_bypass:
            max_entries = int(directive.get("max_entries_per_cycle", 3) or 0)
            if entries_executed >= max_entries:
                return False

        # Cap total portfolio expansion
        try:
            max_positions_total = int(directive.get("max_positions_total", 12) or 0)
        except Exception:
            max_positions_total = 12
        if max_positions_total > 0 and len(self.positions) >= max_positions_total:
            return False

        # Confidence floor
        try:
            floor = float(directive.get("entry_confidence_floor", 0.4) or 0.4)
        except Exception:
            floor = 0.4
        if float(getattr(signal, "confidence", 0.0) or 0.0) < floor:
            return False

        # In NEUTRAL mode, only allow preferred symbols (tight control)
        if directive.get("mode") == "NEUTRAL":
            preferred = set(directive.get("preferred_symbols", []) or [])
            if preferred and signal.symbol not in preferred:
                # Allow Inception to override only at very high confidence
                if signal.source != "INCEPTION_KICK" or float(signal.confidence or 0.0) < 0.9:
                    return False

        return True

    def _publish_mycelium_directive(self, directive: Dict[str, Any]) -> None:
        """Push Mycelium control state onto the ThoughtBus so downstream ecosystems can consume it."""
        if not self.thought_bus:
            return
        try:
            self.thought_bus.publish(Thought(
                source="mycelium",
                topic="mycelium.directive",
                payload={
                    "timestamp": time.time(),
                    **(directive or {}),
                },
            ))
        except Exception:
            pass

    def _build_ecosystem_connection_map(self) -> Dict[str, Any]:
        """Build a connectivity graph (nodes + edges + state) for the full multiverse ecosystem."""
        nodes: Dict[str, Any] = {
            "market_data": {"type": "data", "online": True},
            "thought_bus": {"type": "bus", "online": bool(self.thought_bus)},
            "mycelium": {"type": "controller", "online": bool(self.mycelium)},
            "directive": {"type": "control", "online": True},
            "commando": {"type": "strategy", "online": bool(self.commando)},
            "inception": {"type": "strategy", "online": bool(INCEPTION_AVAILABLE and _inception_engine)},
            "sniper": {"type": "strategy", "online": bool(self.sniper)},
            "scouts": {"type": "strategy", "online": bool(self.scout_network)},
            "multiverse": {"type": "worlds", "online": bool(self.multiverse)},
            "converter": {"type": "converter", "online": bool(self.multiverse and getattr(self.multiverse, "converter", None))},
            "revenue_board": {"type": "ledger", "online": bool(self.revenue_board)},
            "execution": {"type": "executor", "online": True},
            "exchange.binance": {"type": "exchange", "online": bool(self.binance)},
            "exchange.kraken": {"type": "exchange", "online": bool(self.kraken)},
            "exchange.alpaca": {"type": "exchange", "online": bool(self.alpaca)},
        }

        edges: List[Dict[str, Any]] = [
            {"from": "market_data", "to": "inception", "type": "inputs"},
            {"from": "market_data", "to": "scouts", "type": "inputs"},
            {"from": "market_data", "to": "multiverse", "type": "inputs"},
            {"from": "market_data", "to": "commando", "type": "inputs"},
            {"from": "market_data", "to": "mycelium", "type": "inputs"},

            # Signals flow into execution
            {"from": "inception", "to": "execution", "type": "signals"},
            {"from": "scouts", "to": "execution", "type": "signals"},
            {"from": "sniper", "to": "execution", "type": "signals"},
            {"from": "commando", "to": "execution", "type": "signals"},

            # Mycelium control layer gates execution
            {"from": "mycelium", "to": "directive", "type": "control"},
            {"from": "directive", "to": "execution", "type": "gate"},

            # Execution routes to exchanges
            {"from": "execution", "to": "exchange.binance", "type": "orders"},
            {"from": "execution", "to": "exchange.kraken", "type": "orders"},
            {"from": "execution", "to": "exchange.alpaca", "type": "orders"},

            # Outcomes to ledgers + learning
            {"from": "execution", "to": "revenue_board", "type": "record"},
            {"from": "execution", "to": "multiverse", "type": "outcome"},
            {"from": "execution", "to": "mycelium", "type": "profit_feedback"},

            # Sweeps
            {"from": "multiverse", "to": "converter", "type": "sweep"},
            {"from": "converter", "to": "revenue_board", "type": "record"},
        ]

        return {
            "timestamp": time.time(),
            "mode": "SIMULATION" if self.simulation_mode else "LIVE",
            "nodes": nodes,
            "edges": edges,
        }

    def _update_mycelium_connections(self) -> Dict[str, Any]:
        """Compute + publish the full ecosystem connection graph and feed it into Mycelium."""
        conn = self._build_ecosystem_connection_map()

        # Feed into Mycelium so it can reason about all connected systems
        if self.mycelium and hasattr(self.mycelium, "update_connection_map"):
            try:
                self.mycelium.update_connection_map(conn)
            except Exception:
                pass

        # Publish on ThoughtBus so other ecosystems can align their logic
        if self.thought_bus:
            try:
                self.thought_bus.publish(Thought(
                    source="multiverse_live",
                    topic="ecosystem.connections",
                    payload=conn,
                ))
            except Exception:
                pass

        return conn

    def _update_mycelium_governing_metrics(self) -> Dict[str, Any]:
        """Push governing metrics into Mycelium so it can govern net-profit growth and portfolio expansion."""
        total_cash = float(self._get_total_cash() or 0.0)
        total_equity = float(getattr(self, "total_equity", 0.0) or 0.0)
        if total_equity <= 0:
            total_equity = float(self.get_available_capital() or 0.0)

        wins = int(self.stats.get("win_count", 0) or 0)
        losses = int(self.stats.get("loss_count", 0) or 0)
        total_closed = wins + losses
        win_rate = (wins / total_closed) if total_closed > 0 else 0.0

        # Drawdown relative to observed peak equity
        peak = float(getattr(self, "_peak_equity_observed", total_equity) or total_equity)
        if total_equity > peak:
            peak = total_equity
        self._peak_equity_observed = peak
        drawdown_pct = ((peak - total_equity) / peak) * 100 if peak > 0 else 0.0

        metrics: Dict[str, Any] = {
            "timestamp": time.time(),
            "mode": "SIMULATION" if self.simulation_mode else "LIVE",
            "cycles": int(self.stats.get("cycles", 0) or 0),
            "trades_executed": int(self.stats.get("trades_executed", 0) or 0),
            "signals_generated": int(self.stats.get("signals_generated", 0) or 0),
            "positions_count": int(len(self.positions)),
            "total_cash": total_cash,
            "total_equity": total_equity,
            "realized_pnl_total": float(self.stats.get("total_profit", 0.0) or 0.0),
            "win_rate": float(win_rate),
            "drawdown_pct": float(drawdown_pct),
        }

        if self.mycelium and hasattr(self.mycelium, "update_governing_metrics"):
            try:
                self.mycelium.update_governing_metrics(metrics)
            except Exception:
                pass

        if self.thought_bus:
            try:
                self.thought_bus.publish(Thought(
                    source="multiverse_live",
                    topic="mycelium.metrics",
                    payload=metrics,
                ))
            except Exception:
                pass

        return metrics

    def exchange_healthcheck(self) -> int:
        """Non-trading connectivity + data sanity checks for all configured exchanges."""
        results: List[Tuple[str, str]] = []

        def ok(msg: str) -> None:
            results.append(("OK", msg))

        def warn(msg: str) -> None:
            results.append(("WARN", msg))

        def fail(msg: str) -> None:
            results.append(("FAIL", msg))

        # Balances + spot/quote sample per exchange
        for ex, client in [("binance", self.binance), ("kraken", self.kraken), ("alpaca", self.alpaca)]:
            if client is None:
                warn(f"{ex}: client OFFLINE")
                continue
            try:
                if ex == "binance":
                    acct = client.account()
                    ok(f"binance: account ok (balances={len(acct.get('balances', []))})")
                    bp = client.best_price("BTCUSDT")
                    ok(f"binance: price ok BTCUSDT={bp.get('price')}")
                elif ex == "kraken":
                    bal = client.get_account_balance()
                    ok(f"kraken: balances ok (assets={len(bal)})")
                    bp = client.best_price("BTCUSD")
                    ok(f"kraken: price ok BTCUSD={bp.get('price')}")
                elif ex == "alpaca":
                    acct = client.get_account()
                    ok(f"alpaca: account ok (cash={acct.get('cash')})")
                    q = client.get_last_quote("AAPL")
                    ok(f"alpaca: quote ok AAPL")
            except Exception as e:
                fail(f"{ex}: healthcheck error: {e}")

        # Combined market data
        try:
            md = self.fetch_market_data()
            src = md.get("source", {})
            ok(f"market_data: symbols={len(md.get('prices', {}))} (binance={sum(1 for v in src.values() if v=='binance')}, kraken={sum(1 for v in src.values() if v=='kraken')}, alpaca={sum(1 for v in src.values() if v=='alpaca')})")
        except Exception as e:
            fail(f"market_data: error: {e}")

        print("\n" + "=" * 80)
        print("🩺 EXCHANGE HEALTHCHECK")
        print("=" * 80)
        for level, msg in results:
            print(f"[{level}] {msg}")
        print("=" * 80 + "\n")

        return 0 if not any(level == "FAIL" for level, _ in results) else 1
    
    def print_status(self):
        """Print current status with REAL balances and validated profits"""
        runtime = time.time() - self.start_time
        win_rate = self.stats["win_count"] / max(1, self.stats["win_count"] + self.stats["loss_count"]) * 100
        
        # Refresh real balances
        self._refresh_real_balances()
        total_cash = self._get_total_cash()
        
        print("\n" + "═" * 80)
        print("⚡🌌 MULTIVERSE LIVE STATUS 🌌⚡")
        print("═" * 80)
        print(f"  Runtime: {runtime/60:.1f} min | Cycles: {self.stats['cycles']}")
        print(f"  Mode: {'SIMULATION' if self.simulation_mode else 'LIVE TRADING'}")
        print("-" * 80)
        
        # 💵 REAL EXCHANGE BALANCES
        print("  💵 REAL EXCHANGE BALANCES:")
        print(f"     Binance USDT:   ${self.real_balances['binance'].get('USDT', 0):.2f}")
        print(f"     Kraken USD:     ${self.real_balances['kraken'].get('USD', 0):.2f}")
        print(f"     Alpaca USD:     ${self.real_balances['alpaca'].get('USD', 0):.2f}")
        print(f"     ─────────────────────────")
        print(f"     TOTAL CASH:     ${total_cash:.2f}")
        print("-" * 80)
        
        print(f"  🦅 COMMANDO DOCTRINE:")
        print(f"     Goal: {self.commando.one_goal}")
        print(f"     Signals: {self.stats['signals_generated']} | Trades: {self.stats['trades_executed']}")
        print(f"     Sweeps: {self.stats['sweeps_performed']}")
        print("-" * 80)
        
        print(f"  🎯 SNIPER & ☘️ SCOUT STATUS:")
        print(f"     Sniper Kills:   {self.stats['sniper_kills']}")
        print(f"     Scout Profits:  ${self.stats['scout_profits']:.4f}")
        print(f"     Sniper Brain:   {'ONLINE' if self.sniper else 'OFFLINE'}")
        print(f"     Scout Network:  {'ONLINE' if self.scout_network else 'OFFLINE'}")
        print("-" * 80)
        
        print(f"  💰 PERFORMANCE:")
        print(f"     Total Profit:   ${self.stats['total_profit']:.4f}")
        print(f"     Win Rate:       {win_rate:.1f}% ({self.stats['win_count']}W / {self.stats['loss_count']}L)")
        print(f"     Open Positions: {len(self.positions)}")
        print("-" * 80)
        
        if self.multiverse:
            print("  🌌 MULTIVERSE STATUS:")
            for world in self.multiverse.worlds[:5]:
                print(f"     {world.emoji} {world.name}: ${world.state.equity:.2f} | "
                      f"WR: {world.get_win_rate()*100:.0f}%")
            print(f"     ... and {len(self.multiverse.worlds)-5} more worlds")
        
        # Print Revenue Board
        if self.revenue_board:
            try:
                snapshot = self.revenue_board.compute_equity()
                print("-" * 80)
                print("  💰 REVENUE BOARD (Live Exchange Data):")
                print(f"     Total Equity:   ${snapshot.total_equity:.2f}")
                print(f"     Cash Balance:   ${snapshot.cash_balance:.2f}")
                print(f"     Positions:      ${snapshot.positions_value:.2f}")
                print(f"     Realized PnL:   ${snapshot.realized_pnl:.4f}")
                print(f"     Total PnL:      ${snapshot.total_pnl:.4f}")
            except Exception as e:
                print(f"  💰 Revenue Board error: {e}")
        
        # Print Penny Profit Ledger
        if self.penny_ledger:
            self.penny_ledger.print_ledger()
        
        print("═" * 80 + "\n")
    
    async def run_live(self, interval_seconds: float = 5.0, max_cycles: int = None):
        """Run the live trading loop (optionally in Donkey & Carrot mode)."""
        self.running = True
        cycle_count = 0
        consecutive_no_profit = 0
        last_profit = self.stats["total_profit"]

        donkey_mode = bool(getattr(self, "donkey_mode", False))

        logger.info(f"🚀 STARTING MULTIVERSE LIVE - Interval: {interval_seconds}s")
        if donkey_mode:
            logger.info("🥕🐴 DONKEY MODE: Never stopping, always chasing the carrot!")

        try:
            while self.running:
                cycle_count += 1

                # Update Revenue Board with fresh exchange data (every 5 cycles)
                if self.revenue_board and cycle_count % 5 == 0:
                    try:
                        self.revenue_board.compute_equity()
                    except Exception:
                        pass

                # Run cycle (never let one exception stop the loop)
                try:
                    result = self.run_cycle()
                except Exception as e:
                    logger.error(f"⚠️ Cycle error: {e}")
                    await asyncio.sleep(min(5.0, max(1.0, interval_seconds)))
                    continue

                # 🥕 CARROT TRACKING (only in donkey mode)
                if donkey_mode:
                    current_profit = self.stats["total_profit"]
                    if current_profit > last_profit:
                        profit_made = current_profit - last_profit
                        logger.info(f"🥕 CARROT! Made ${profit_made:.4f} - Keep chasing!")
                        consecutive_no_profit = 0
                        last_profit = current_profit
                    else:
                        consecutive_no_profit += 1
                        if consecutive_no_profit >= 100:
                            logger.info(
                                f"🐴 Donkey hungry ({consecutive_no_profit} cycles no carrot) - scanning faster!"
                            )
                            interval_seconds = max(1.0, interval_seconds * 0.9)
                            consecutive_no_profit = 0

                # Log summary (REAL-only: count executed trades, not attempts)
                if result.get("commando_signals"):
                    executed_trades = sum(1 for e in result.get("executions", []) if e.get("executed"))
                    logger.info(
                        f"📡 Cycle {result['cycle']}: {len(result['commando_signals'])} signals, "
                        f"{executed_trades} executed, {len(result['sweeps'])} sweeps"
                    )

                # Print status every 10 cycles
                if cycle_count % 10 == 0:
                    self.print_status()
                    if donkey_mode:
                        target_profit = self.stats["total_profit"] * 1.1 + 1.0
                        logger.info(
                            f"🥕 CARROT AHEAD: ${target_profit:.4f} (current: ${self.stats['total_profit']:.4f})"
                        )

                # Respect max_cycles only when NOT in donkey mode
                if (not donkey_mode) and max_cycles and cycle_count >= max_cycles:
                    logger.info(f"Reached max cycles ({max_cycles})")
                    break

                await asyncio.sleep(interval_seconds)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.running = False
            self.print_status()
            logger.info("🛑 MULTIVERSE LIVE STOPPED")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    _safe_print("""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                   ║
║     ⚡🌌 AUREON MULTIVERSE LIVE - THE ULTIMATE UNIFIED TRADING SYSTEM 🌌⚡                          ║
║                                                                                                   ║
║     🦅 COMMANDO DOCTRINE: Zero Fear | One Goal | Sweep Before They React                         ║
║     🌌 MULTIVERSE: 10 Worlds | 9 Processing | 1 Converter | 10 Together                           ║
║     🧠 COGNITION: Miner Brain | Nexus | Auris | Probability | Quantum                            ║
║                                                                                                   ║
║     "We don't quit. We compound. We conquer." 🌌⚡                                                 ║
║                                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════╝
    """)
    
    import argparse
    parser = argparse.ArgumentParser(description="Aureon Multiverse Live Trading")
    parser.add_argument("--sim", action="store_true", help="Run in simulation mode")
    parser.add_argument("--interval", type=float, default=5.0, help="Cycle interval in seconds")
    parser.add_argument("--cycles", type=int, default=None, help="Max cycles (None for infinite)")
    parser.add_argument("--fresh", action="store_true", help="Fresh start - liquidate all positions to cash first")
    parser.add_argument("--donkey", action="store_true", help="Donkey mode - never stop, always chase the carrot")
    parser.add_argument("--healthcheck", action="store_true", help="Run exchange connectivity/data checks and exit")
    args = parser.parse_args()
    
    # Set environment variables for modes
    if args.fresh:
        os.environ['AUREON_FRESH_START'] = 'true'
        print("🔥 FRESH START: Will liquidate all positions to cash!")
    if args.donkey:
        os.environ['AUREON_DONKEY_MODE'] = 'true'
        print("🥕🐴 DONKEY MODE: Will run forever chasing profits!")
    
    # Create engine
    engine = MultiverseLiveEngine(simulation_mode=args.sim)

    # Optional non-trading healthcheck
    if args.healthcheck:
        raise SystemExit(engine.exchange_healthcheck())
    
    # Run live
    asyncio.run(engine.run_live(
        interval_seconds=args.interval,
        max_cycles=args.cycles
    ))


if __name__ == "__main__":
    main()
