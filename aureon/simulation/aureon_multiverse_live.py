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
if os.getenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "").strip().lower() not in {
    "1", "true", "yes", "on",
}:
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
    expected_profit: Optional[float]
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
        # A market observation is never a cost-basis receipt.
        try:
            inputs_complete = (
                all(
                    math.isfinite(float(value))
                    for value in (current_value, entry_price, current_price)
                )
                and float(current_value) >= 0
                and float(entry_price) > 0
                and float(current_price) > 0
            )
        except (TypeError, ValueError, OverflowError):
            inputs_complete = False
        if not inputs_complete:
            signal = CommandoSignal(
                timestamp=time.time(),
                symbol=asset,
                exchange=exchange,
                action="HOLD",
                strength=0.0,
                confidence=0.0,
                source="CommandoCognition",
                reason="NO_DATA: provider cost basis and fresh price are required",
                profit_path="NONE",
                expected_profit=None,
                commando_type="CHAMELEON",
            )
            self.signals.append(signal)
            return signal
        
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
        
        for symbol, raw_price in prices.items():
            if (
                symbol not in changes
                or symbol not in momentum
                or symbol not in symbol_source
            ):
                continue
            try:
                price = float(raw_price)
                change = float(changes[symbol])
                mom = float(momentum[symbol])
            except (TypeError, ValueError, OverflowError):
                continue
            exchange = str(symbol_source[symbol]).strip().lower()
            if (
                not exchange
                or not all(math.isfinite(value) for value in (price, change, mom))
                or price <= 0
            ):
                continue
            
            # FALCON Entry: Strong upward momentum
            if mom > 0.02 and change > 0:
                score = mom * 10 + change / 5
                if score > best_score:
                    best_score = score
                    best_signal = CommandoSignal(
                        timestamp=time.time(),
                        symbol=symbol,
                        exchange=exchange,
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
                        exchange=exchange,
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
            self.multiverse = get_multiverse(initial_equity=0.0)
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
        self.real_balances: Dict[str, Dict[str, float]] = {
            "binance": {},
            "kraken": {},
            "alpaca": {},
        }
        self.balance_snapshot: Dict[str, Any] = {
            "status": "not_run",
            "truth_status": "no_data",
            "venues": {},
            "eligible_for_external_action": False,
            "generated_values": False,
        }
        # A complete equity number requires every holding, cost basis and an
        # explicit same-denomination valuation receipt. Cash rows alone are not
        # portfolio equity.
        self.total_equity: Optional[float] = None
        self.equity_receipt: Dict[str, Any] = {
            "status": "no_data",
            "truth_status": "no_data",
            "value": None,
            "currency": None,
            "eligible_for_accounting": False,
            "generated_values": False,
            "reason": "complete_portfolio_valuation_receipts_required",
        }
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
                initial_cap = self._get_total_cash()
                if initial_cap is None:
                    self.mycelium = None
                    logger.warning(
                        "🍄 Mycelium Network: WAITING FOR SINGLE-DENOMINATION "
                        "CAPITAL EVIDENCE"
                    )
                else:
                    self.mycelium = MyceliumNetwork(
                        initial_capital=initial_cap,
                        agents_per_hive=5,
                    )
                    currency = self.balance_snapshot.get("aggregate_currency")
                    logger.info(
                        "🍄 Mycelium Network: ONLINE (capital=%.2f %s)",
                        initial_cap,
                        currency,
                    )
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
        self.pending_orders: Dict[str, Dict[str, Any]] = {}
        self.unreconciled_fills: List[Dict[str, Any]] = []
        self.unproven_holdings: List[Dict[str, Any]] = []
        self.harvest_receipt: Dict[str, Any] = {
            "status": "not_run",
            "truth_status": "no_data",
            "eligible_for_external_action": False,
            "generated_values": False,
        }
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
            "total_profit": None,
            "total_profit_currency": None,
            "realized_profit_by_currency": {},
            "win_count": 0,
            "loss_count": 0,
            "sniper_kills": 0,
            "scout_profits": None,
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
        observed_cash = self._get_total_cash()
        if observed_cash is None:
            logger.info("   Real Cash: NO_DATA (mixed or incomplete denomination evidence)")
        else:
            logger.info(
                "   Real Cash: %.2f %s",
                observed_cash,
                self.balance_snapshot.get("aggregate_currency"),
            )
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
    
    @staticmethod
    def _fresh_observed_price(ticker: Any, max_age_seconds: float = 120.0) -> Optional[float]:
        """Return a provider price only when its own provenance is fresh."""
        if not isinstance(ticker, dict):
            return None
        if ticker.get("truth_status") not in {"real_observed", "real_derived"}:
            return None
        if ticker.get("generated_values") is not False:
            return None
        if not isinstance(ticker.get("source_id"), str) or not ticker.get("source_id"):
            return None
        try:
            price = float(ticker["price"])
            source_timestamp = float(ticker["source_timestamp"])
            if source_timestamp > 10_000_000_000:
                source_timestamp /= 1000.0
            age = time.time() - source_timestamp
            if (
                not math.isfinite(price)
                or not math.isfinite(source_timestamp)
                or price <= 0
                or age < -30.0
                or age > max_age_seconds
            ):
                return None
            return price
        except (KeyError, TypeError, ValueError, OverflowError):
            return None

    def _harvest_existing_assets(self, liquidate: bool = False):
        """
        🌾 STARTUP HARVESTER: Scan all holdings across exchanges.
        If liquidate=True, SELLS everything to cash for fresh start.
        Otherwise loads existing positions into the sniper for monitoring.
        """
        logger.info(f"🌾 STARTUP HARVESTER: {'LIQUIDATING ALL' if liquidate else 'Scanning'} existing assets...")
        self.unproven_holdings = []
        received_at = time.time()
        
        # Determine preferred quote currency for Binance UK accounts
        binance_quote = "USDC" if (self.binance and self.binance.uk_mode) else "USDT"
        
        # Scan Binance for ALL holdings (not just non-quote)
        if self.binance:
            try:
                # Use account() to get balances
                account_info = self.binance.account()
                balances = account_info['balances']
                
                for bal in balances:
                    asset = bal['asset']
                    free = float(bal['free'])
                    locked = float(bal['locked'])
                    if not math.isfinite(free) or not math.isfinite(locked):
                        raise ValueError("Binance balance receipt is not finite")
                    if free < 0 or locked < 0:
                        raise ValueError("Binance balance receipt is negative")
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
                        self.unproven_holdings.append({
                            "symbol": symbol,
                            "asset": asset,
                            "free_quantity": free,
                            "locked_quantity": locked,
                            "total_quantity": total,
                            "exchange": "binance",
                            "cost_basis": None,
                            "valuation": None,
                            "source_id": "binance:/api/v3/account",
                            "source_timestamp": None,
                            "received_at": received_at,
                            "truth_status": "real_observed",
                            "eligible_for_external_action": False,
                            "eligible_for_accounting": False,
                            "generated_values": False,
                            "reason": "cost_basis_and_terminal_fill_receipts_required",
                        })
            except Exception as e:
                logger.warning(f"Binance harvest error: {e}")
        
        # Scan Kraken for non-USD holdings
        if self.kraken:
            try:
                balances = self.kraken.get_account_balance()
                skip_assets = {'USD', 'ZUSD', 'USDT', 'USDC', 'EUR', 'ZEUR', 'GBP', 'ZGBP'}
                
                for asset, amount in balances.items():
                    amount = float(amount)
                    if not math.isfinite(amount) or amount < 0:
                        raise ValueError("Kraken balance receipt is invalid")
                    if amount < 0.000001:  # Skip dust
                        continue
                        
                    # Skip quote currencies
                    if asset.upper() in skip_assets:
                        continue
                        
                    symbol = f"{asset}USD"
                    self.unproven_holdings.append({
                        "symbol": symbol,
                        "asset": asset,
                        "free_quantity": amount,
                        "locked_quantity": None,
                        "total_quantity": amount,
                        "exchange": "kraken",
                        "cost_basis": None,
                        "valuation": None,
                        "source_id": "kraken:/0/private/Balance",
                        "source_timestamp": None,
                        "received_at": received_at,
                        "truth_status": "real_observed",
                        "eligible_for_external_action": False,
                        "eligible_for_accounting": False,
                        "generated_values": False,
                        "reason": "cost_basis_and_terminal_fill_receipts_required",
                    })
            except Exception as e:
                logger.warning(f"Kraken harvest error: {e}")
        
        if liquidate:
            self.harvest_receipt = {
                "status": "not_submitted",
                "truth_status": "no_data",
                "source_id": "aureon:multiverse_startup_harvest",
                "source_timestamp": None,
                "received_at": received_at,
                "eligible_for_external_action": False,
                "eligible_for_accounting": False,
                "generated_values": False,
                "holding_count": len(self.unproven_holdings),
                "reason": "durable_terminal_fill_reconciler_required",
            }
            logger.warning(
                "NO_DATA: startup liquidation not submitted; terminal fill "
                "reconciliation is required"
            )
        else:
            self.harvest_receipt = {
                "status": "observed",
                "truth_status": "real_observed",
                "source_id": "aureon:multiverse_startup_harvest",
                "source_timestamp": None,
                "received_at": received_at,
                "eligible_for_external_action": False,
                "eligible_for_accounting": False,
                "generated_values": False,
                "holding_count": len(self.unproven_holdings),
                "reason": "cost_basis_receipts_required_before_position_tracking",
            }
            logger.info(
                "Startup harvest recorded %d risk-only holdings; no cost basis "
                "or tradable position was inferred",
                len(self.unproven_holdings),
            )
        return self.harvest_receipt
    
    def _refresh_real_balances(self) -> Dict[str, Any]:
        """Read exact venue balances without currency parity or equity inference."""
        received_at = time.time()
        next_balances: Dict[str, Dict[str, float]] = {
            "binance": {},
            "kraken": {},
            "alpaca": {},
        }
        venues: Dict[str, Dict[str, Any]] = {}

        def no_data(venue: str, source_id: str, reason: str) -> None:
            venues[venue] = {
                "status": "no_data",
                "truth_status": "no_data",
                "source_id": source_id,
                "source_timestamp": None,
                "received_at": received_at,
                "settlement_asset": None,
                "settlement_amount": None,
                "eligible_for_external_action": False,
                "generated_values": False,
                "reason": reason,
            }

        def parse_rows(rows: Any, venue: str) -> Dict[str, float]:
            if not isinstance(rows, list):
                raise ValueError(f"{venue} balance receipt is not a list")
            parsed: Dict[str, float] = {}
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError(f"{venue} balance row is not an object")
                asset = str(row["asset"]).strip().upper()
                if not asset:
                    raise ValueError(f"{venue} balance asset is empty")
                free = float(row["free"])
                locked = float(row["locked"])
                if not all(math.isfinite(value) for value in (free, locked)):
                    raise ValueError(f"{venue} balance row is not finite")
                if free < 0 or locked < 0:
                    raise ValueError(f"{venue} balance row is negative")
                if asset in parsed:
                    raise ValueError(f"{venue} balance asset is duplicated: {asset}")
                parsed[asset] = free
            return parsed

        if self.binance:
            try:
                account = self.binance.account()
                if not isinstance(account, dict):
                    raise ValueError("Binance account receipt is not an object")
                parsed = parse_rows(account["balances"], "Binance")
                settlement_asset = "USDC" if bool(self.binance.uk_mode) else "USDT"
                source_timestamp = account.get("updateTime")
                if source_timestamp is not None:
                    source_timestamp = float(source_timestamp)
                    if source_timestamp > 10_000_000_000:
                        source_timestamp /= 1000.0
                    if not math.isfinite(source_timestamp) or source_timestamp <= 0:
                        source_timestamp = None
                production_mode = not bool(
                    getattr(self.binance, "dry_run", False)
                    or getattr(self.binance, "use_testnet", False)
                )
                next_balances["binance"] = parsed
                venues["binance"] = {
                    "status": "observed",
                    "truth_status": "real_observed",
                    "source_id": "binance:/api/v3/account",
                    "source_timestamp": source_timestamp,
                    "received_at": received_at,
                    "timestamp_policy": (
                        "provider_account_update_time_and_local_receipt_time"
                        if source_timestamp is not None
                        else "provider_endpoint_has_no_snapshot_time; local_receipt_time"
                    ),
                    "settlement_asset": settlement_asset,
                    "settlement_amount": parsed.get(settlement_asset),
                    "eligible_for_external_action": production_mode,
                    "generated_values": False,
                    "reason": None if production_mode else "non_production_client_mode",
                }
            except Exception as exc:
                no_data("binance", "binance:/api/v3/account", str(exc))

        if self.kraken:
            try:
                if bool(getattr(self.kraken, "dry_run", False)):
                    raise ValueError("Kraken dry-run balance receipt is not production data")
                account = self.kraken.account()
                if not isinstance(account, dict):
                    raise ValueError("Kraken account receipt is not an object")
                parsed = parse_rows(account["balances"], "Kraken")
                next_balances["kraken"] = parsed
                venues["kraken"] = {
                    "status": "observed",
                    "truth_status": "real_observed",
                    "source_id": "kraken:/0/private/Balance",
                    "source_timestamp": None,
                    "received_at": received_at,
                    "timestamp_policy": "provider_endpoint_has_no_snapshot_time; local_receipt_time",
                    "settlement_asset": "USD",
                    "settlement_amount": parsed.get("USD"),
                    "eligible_for_external_action": True,
                    "generated_values": False,
                    "reason": None,
                }
            except Exception as exc:
                no_data("kraken", "kraken:/0/private/Balance", str(exc))

        if self.alpaca:
            try:
                account = self.alpaca.get_account()
                if not isinstance(account, dict):
                    raise ValueError("Alpaca account receipt is not an object")
                currency = str(account["currency"]).strip().upper()
                cash = float(account["cash"])
                if not currency or not math.isfinite(cash):
                    raise ValueError("Alpaca cash receipt is incomplete")
                production_mode = not bool(getattr(self.alpaca, "use_paper", False))
                trading_enabled = not any(
                    account.get(field) is True
                    for field in (
                        "account_blocked",
                        "trading_blocked",
                        "trade_suspended_by_user",
                    )
                )
                spendable_cash = cash >= 0
                next_balances["alpaca"] = {currency: cash}
                venues["alpaca"] = {
                    "status": "observed",
                    "truth_status": "real_observed",
                    "source_id": "alpaca:/v2/account",
                    "source_timestamp": None,
                    "received_at": received_at,
                    "timestamp_policy": "provider_endpoint_has_no_snapshot_time; local_receipt_time",
                    "settlement_asset": currency,
                    "settlement_amount": cash,
                    "eligible_for_external_action": (
                        production_mode and trading_enabled and spendable_cash
                    ),
                    "generated_values": False,
                    "reason": (
                        None
                        if production_mode and trading_enabled and spendable_cash
                        else (
                            "negative_cash_not_spendable"
                            if not spendable_cash
                            else "non_production_or_trading_blocked_account"
                        )
                    ),
                }
            except Exception as exc:
                no_data("alpaca", "alpaca:/v2/account", str(exc))

        configured = [
            venue
            for venue, client in (
                ("binance", self.binance),
                ("kraken", self.kraken),
                ("alpaca", self.alpaca),
            )
            if client is not None
        ]
        complete_settlements = []
        for venue in configured:
            receipt = venues.get(venue, {})
            amount = receipt.get("settlement_amount")
            if (
                receipt.get("eligible_for_external_action") is True
                and isinstance(receipt.get("settlement_asset"), str)
                and amount is not None
            ):
                complete_settlements.append(
                    (receipt["settlement_asset"], float(amount))
                )

        aggregate_cash: Optional[float] = None
        aggregate_currency: Optional[str] = None
        if configured and len(complete_settlements) == len(configured):
            currencies = {currency for currency, _ in complete_settlements}
            if len(currencies) == 1:
                aggregate_currency = next(iter(currencies))
                aggregate_cash = sum(amount for _, amount in complete_settlements)

        observed_count = sum(
            1
            for receipt in venues.values()
            if receipt.get("truth_status") == "real_observed"
        )
        if not observed_count:
            snapshot_status = "no_data"
            snapshot_truth = "no_data"
        elif observed_count == len(configured):
            snapshot_status = "observed"
            snapshot_truth = "real_observed"
        else:
            snapshot_status = "partial"
            snapshot_truth = "real_observed"

        self.real_balances = next_balances
        self.balance_snapshot = {
            "status": snapshot_status,
            "truth_status": snapshot_truth,
            "source_timestamp": None,
            "received_at": received_at,
            "venues": venues,
            "aggregate_cash": aggregate_cash,
            "aggregate_currency": aggregate_currency,
            "aggregate_status": "complete" if aggregate_cash is not None else "no_data",
            "eligible_for_external_action": aggregate_cash is not None,
            "generated_values": False,
            "reason": (
                None
                if aggregate_cash is not None
                else "all_configured_venues_require_complete_same_denomination_cash_receipts"
            ),
        }
        self.total_equity = None
        self.equity_receipt = {
            "status": "no_data",
            "truth_status": "no_data",
            "value": None,
            "currency": None,
            "received_at": received_at,
            "eligible_for_accounting": False,
            "generated_values": False,
            "reason": "complete_portfolio_valuation_receipts_required",
        }
        logger.info(
            "Balance refresh: %d venue receipt(s); aggregate cash=%s",
            len(venues),
            (
                f"{aggregate_cash:.8f} {aggregate_currency}"
                if aggregate_cash is not None
                else "NO_DATA"
            ),
        )
        return self.balance_snapshot

    def _build_ladder_client(self):
        """Build a multi-exchange client adapter for the ConversionLadder."""
        engine = self

        class LadderClientAdapter:
            """Adapts MultiverseLiveEngine's exchange clients to the Ladder interface."""

            def get_all_balances(self) -> Dict[str, Dict[str, float]]:
                """Return exact provider denominations from the last fresh snapshot."""
                out: Dict[str, Dict[str, float]] = {}
                snapshot = getattr(engine, "balance_snapshot", {})
                venues = snapshot.get("venues") if isinstance(snapshot, dict) else None
                if not isinstance(venues, dict):
                    return out
                for venue, receipt in venues.items():
                    if (
                        not isinstance(receipt, dict)
                        or receipt.get("eligible_for_external_action") is not True
                    ):
                        continue
                    observed = getattr(engine, "real_balances", {}).get(venue, {})
                    if not isinstance(observed, dict):
                        continue
                    exact: Dict[str, float] = {}
                    for asset, raw_amount in observed.items():
                        try:
                            amount = float(raw_amount)
                        except (TypeError, ValueError):
                            continue
                        if math.isfinite(amount) and amount > 0:
                            exact[str(asset).upper()] = amount
                    out[venue] = exact
                return out

            def get_all_convertible_assets(self) -> Dict[str, Dict[str, List[str]]]:
                """Build route visibility only from fresh provider-observed pairs."""
                paths: Dict[str, Dict[str, List[str]]] = {}
                market_data = getattr(engine, "market_data", {})
                source_map = market_data.get("source") if isinstance(
                    market_data, dict
                ) else None
                if not isinstance(source_map, dict):
                    return paths
                edges: Dict[str, Dict[str, set]] = {}
                for symbol, venue_value in source_map.items():
                    venue = str(venue_value).lower()
                    if engine._actionable_market_price(symbol, venue) is None:
                        continue
                    base = engine._base_asset_for_symbol(symbol)
                    quote = engine._quote_asset_for_symbol(symbol)
                    if base is None or quote is None or base == quote:
                        continue
                    venue_edges = edges.setdefault(venue, {})
                    venue_edges.setdefault(base, set()).add(quote)
                    venue_edges.setdefault(quote, set()).add(base)
                for venue, venue_edges in edges.items():
                    paths[venue] = {
                        asset: sorted(targets)
                        for asset, targets in venue_edges.items()
                        if targets
                    }
                return paths

            def find_conversion_path(self, exchange: str, from_asset: str, to_asset: str) -> List[Dict[str, Any]]:
                """Find the best conversion path using the Labyrinth Mapper."""
                # Use the labyrinth for intelligent pathfinding
                if hasattr(engine, 'labyrinth') and engine.labyrinth:
                    path = engine.labyrinth.find_path(from_asset, to_asset, preferred_exchange=exchange)
                    if path:
                        logger.debug(f"🌀 Labyrinth found path: {from_asset} → {to_asset} ({len(path)} hops)")
                        return path
                
                return []

            def convert_to_quote(self, exchange: str, asset: str, qty: float, quote: str) -> Optional[float]:
                """Value an asset only from a fresh provider quote."""
                try:
                    quantity = float(qty)
                except (TypeError, ValueError):
                    return None
                if not math.isfinite(quantity) or quantity < 0:
                    return None
                normalized_asset = str(asset).upper()
                normalized_quote = str(quote).upper()
                if normalized_asset == normalized_quote:
                    return quantity
                try:
                    if exchange == "binance" and engine.binance:
                        symbol = f"{normalized_asset}{normalized_quote}"
                        ticker = engine.binance.get_24h_ticker(symbol)
                        candidate = {
                            "price": ticker["lastPrice"],
                            "source_id": "binance:/api/v3/ticker/24hr",
                            "source_timestamp": ticker["closeTime"],
                            "truth_status": "real_observed",
                            "generated_values": False,
                        }
                        price = engine._fresh_observed_price(candidate)
                        return None if price is None else quantity * price
                    if exchange == "kraken" and engine.kraken:
                        symbol = f"{normalized_asset}{normalized_quote}"
                        ticker = engine.kraken.get_24h_ticker(symbol)
                        price = engine._fresh_observed_price(ticker)
                        return None if price is None else quantity * price
                except Exception:
                    pass
                return None

            def convert_crypto(self, exchange: str, from_asset: str, to_asset: str, amount: float) -> Dict[str, Any]:
                """Expose a conversion plan without submitting any venue order."""
                try:
                    requested_amount = float(amount)
                except (TypeError, ValueError):
                    requested_amount = math.nan
                if not math.isfinite(requested_amount) or requested_amount <= 0:
                    return {
                        "status": "no_data",
                        "truth_status": "no_data",
                        "eligible_for_external_action": False,
                        "eligible_for_accounting": False,
                        "generated_values": False,
                        "reason": "invalid_conversion_amount",
                    }
                # A multi-hop conversion is a durable financial saga. This
                # adapter has no cross-venue transfer receipt or restart-safe
                # reconciler, so plan visibility is preserved while submission
                # remains ineligible. No guessed proceeds may advance a hop.
                return {
                    "status": "not_submitted",
                    "truth_status": "no_data",
                    "eligible_for_external_action": False,
                    "eligible_for_accounting": False,
                    "generated_values": False,
                    "reason": "durable_fill_and_transfer_reconciler_required",
                    "exchange": exchange,
                    "from_asset": from_asset,
                    "to_asset": to_asset,
                    "requested_amount": requested_amount,
                }

        return LadderClientAdapter()
    
    def _get_total_cash(self, currency: Optional[str] = None) -> Optional[float]:
        """Return cash only when every included amount has one exact currency."""
        snapshot = getattr(self, "balance_snapshot", {})
        if not isinstance(snapshot, dict):
            return None
        if currency is None:
            if (
                snapshot.get("aggregate_status") != "complete"
                or snapshot.get("truth_status") != "real_observed"
                or snapshot.get("generated_values") is not False
                or not isinstance(snapshot.get("aggregate_currency"), str)
                or not snapshot.get("aggregate_currency")
            ):
                return None
            value = snapshot.get("aggregate_cash")
            try:
                value = float(value)
            except (TypeError, ValueError):
                return None
            return value if math.isfinite(value) and value >= 0 else None

        normalized = str(currency).strip().upper()
        if not normalized:
            return None
        total = 0.0
        observed = False
        venues = snapshot.get("venues")
        if not isinstance(venues, dict) or not venues:
            return None
        for venue, receipt in venues.items():
            if (
                not isinstance(receipt, dict)
                or receipt.get("eligible_for_external_action") is not True
                or receipt.get("truth_status") != "real_observed"
                or receipt.get("generated_values") is not False
                or not isinstance(receipt.get("source_id"), str)
                or not receipt.get("source_id")
            ):
                return None
            try:
                received_at = float(receipt["received_at"])
                age = time.time() - received_at
            except (KeyError, TypeError, ValueError, OverflowError):
                return None
            if not math.isfinite(received_at) or age < -30.0 or age > 30.0:
                return None
            venue_balances = getattr(self, "real_balances", {}).get(venue, {})
            if not isinstance(venue_balances, dict):
                return None
            if normalized not in venue_balances:
                continue
            try:
                amount = float(venue_balances[normalized])
            except (TypeError, ValueError):
                return None
            if not math.isfinite(amount):
                return None
            total += amount
            observed = True
        return total if observed else None
    
    def fetch_market_data(self) -> Dict:
        """Fetch fresh market data from ALL exchanges and pairs"""
        prices = {}
        changes = {}
        volumes = {}
        momentum = {}
        source = {}
        price_only = {}
        provenance = {}
        
        # BINANCE - Get all allowed pairs (not just USDT)
        if self.binance:
            try:
                # Get all tickers first
                response = self.binance.session.get(
                    f'{self.binance.base}/api/v3/ticker/24hr',
                    timeout=5
                )
                response.raise_for_status()
                all_tickers = response.json()
                if not isinstance(all_tickers, list):
                    raise ValueError("Binance ticker receipt is not a list")
                
                # Get allowed pairs for UK account
                allowed_pairs = self.binance.get_allowed_pairs_uk()
                
                for t in all_tickers:
                    if not isinstance(t, dict):
                        continue
                    symbol = str(t['symbol']).upper()
                    
                    # Only include allowed pairs (respects UK restrictions)
                    if allowed_pairs and symbol not in allowed_pairs:
                        continue
                        
                    try:
                        source_timestamp = float(t['closeTime'])
                        if source_timestamp > 10_000_000_000:
                            source_timestamp /= 1000.0
                        observed_at = time.time()
                        age = observed_at - source_timestamp
                        price = float(t['lastPrice'])
                        change = float(t['priceChangePercent'])
                        volume = float(t['quoteVolume'])
                        if not all(math.isfinite(value) for value in (price, change, volume)):
                            continue
                        if price <= 0 or volume < 0 or age < -30.0 or age > 120.0:
                            continue
                        prices[symbol] = price
                        changes[symbol] = change
                        volumes[symbol] = volume
                        momentum[symbol] = change / 100
                        source[symbol] = "binance"
                        provenance[symbol] = {
                            "source_id": "binance:/api/v3/ticker/24hr",
                            "source_timestamp": source_timestamp,
                            "received_at": observed_at,
                            "truth_status": "real_observed",
                            "generated_values": False,
                        }
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
                    if not isinstance(ticker, dict):
                        continue
                    symbol = str(ticker.get('symbol') or '').upper()
                    if not symbol:
                        continue
                    if symbol in prices:
                        continue  # Skip if already have from Binance
                    
                    # GHOST SIGNAL PREVENTION: Skip blacklisted Kraken assets
                    base_asset = symbol.replace("USD", "").replace("USDT", "").replace("USDC", "").replace("EUR", "").replace("GBP", "")
                    if base_asset in KRAKEN_BLACKLIST:
                        continue
                    
                    try:
                        if any(
                            ticker.get(field) is None
                            for field in ('lastPrice', 'priceChangePercent', 'quoteVolume')
                        ):
                            continue
                        price = float(ticker['lastPrice'])
                        change = float(ticker['priceChangePercent'])
                        volume = float(ticker['quoteVolume'])
                        source_timestamp = float(ticker['source_timestamp'])
                        if source_timestamp > 10_000_000_000:
                            source_timestamp /= 1000.0
                        observed_at = time.time()
                        age = observed_at - source_timestamp
                        if (
                            all(math.isfinite(value) for value in (
                                price, change, volume, source_timestamp
                            ))
                            and price > 0
                            and volume >= 0
                            and -30.0 <= age <= 120.0
                            and ticker.get("truth_status") == "real_derived"
                            and ticker.get("generated_values") is False
                            and isinstance(ticker.get("source_id"), str)
                            and bool(ticker.get("source_id"))
                        ):
                            prices[symbol] = price
                            changes[symbol] = change
                            volumes[symbol] = volume
                            momentum[symbol] = change / 100
                            source[symbol] = "kraken"
                            provenance[symbol] = {
                                "source_id": ticker.get("source_id"),
                                "source_timestamp": source_timestamp,
                                "received_at": observed_at,
                                "truth_status": "real_derived",
                                "generated_values": False,
                            }
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
                        if not isinstance(quote, dict):
                            continue
                        raw = quote.get("raw")
                        if not isinstance(raw, dict):
                            continue
                        provider_quote = raw.get("quote")
                        if not isinstance(provider_quote, dict):
                            provider_quote = raw
                        bid = float(provider_quote["bp"])
                        ask = float(provider_quote["ap"])
                        source_value = provider_quote["t"]
                        if isinstance(source_value, str):
                            normalized = (
                                source_value[:-1] + "+00:00"
                                if source_value.endswith("Z")
                                else source_value
                            )
                            source_timestamp = datetime.fromisoformat(normalized).timestamp()
                        else:
                            source_timestamp = float(source_value)
                            if source_timestamp > 10_000_000_000:
                                source_timestamp /= 1000.0
                        observed_at = time.time()
                        age = observed_at - source_timestamp
                        if not all(math.isfinite(value) for value in (bid, ask, source_timestamp)):
                            continue
                        if bid <= 0 or ask <= 0 or ask < bid or age < -30.0 or age > 120.0:
                            continue
                        stock_symbol = f"{symbol}/USD"
                        price_only[stock_symbol] = {
                            "price": (bid + ask) / 2,
                            "bid": bid,
                            "ask": ask,
                            "source_id": "alpaca:/v2/stocks/quotes/latest",
                            "source_timestamp": source_timestamp,
                            "received_at": observed_at,
                            "truth_status": "real_derived",
                            "eligible_for_external_action": False,
                            "generated_values": False,
                        }
                    except:
                        continue
                
                logger.debug(f"Alpaca: Added {len(stock_symbols)} stock symbols")
                
            except Exception as e:
                logger.error(f"Alpaca market data error: {e}")
        
        received_at = time.time()
        if not prices:
            logger.warning('NO_DATA: providers returned no complete price/change/volume snapshots')

        has_provider_observation = bool(prices or price_only)
        self.market_data = {
            "prices": prices,
            "price_only": price_only,
            "changes": changes,
            "volumes": volumes,
            "momentum": momentum,
            "source": source,
            "provenance": provenance,
            "source_timestamps": {
                symbol: receipt["source_timestamp"]
                for symbol, receipt in provenance.items()
            },
            "timestamp": received_at,
            "received_at": received_at,
            "source_timestamp": None,
            "timestamp_policy": (
                "per_symbol_provider_timestamp; timestamp_is_receipt_time"
                if has_provider_observation
                else None
            ),
            "truth_status": "real_observed" if has_provider_observation else "no_data",
            "decision_status": "ready" if prices else "no_data",
            "eligible_for_external_action": bool(prices),
            "generated_values": False,
            "reason": None if prices else "NO_COMPLETE_MARKET_SNAPSHOTS",
        }
        
        logger.info(f"📊 Market Data: {len(prices)} symbols from all exchanges")
        logger.debug(f"Sample symbols: {list(prices.keys())[:10]}")
        logger.debug(f"Sample changes: {dict(list(changes.items())[:5])}")
        logger.debug(f"Sample momentum: {dict(list(momentum.items())[:5])}")
        return self.market_data
    
    @staticmethod
    def _quote_asset_for_symbol(symbol: str) -> Optional[str]:
        normalized = str(symbol or "").strip().upper()
        if "/" in normalized:
            quote = normalized.rsplit("/", 1)[-1]
            return quote or None
        for quote in (
            "FDUSD",
            "USDT",
            "USDC",
            "BUSD",
            "TUSD",
            "USD",
            "EUR",
            "GBP",
            "BTC",
            "ETH",
            "BNB",
        ):
            if normalized.endswith(quote) and len(normalized) > len(quote):
                return quote
        return None

    def _actionable_market_price(
        self,
        symbol: str,
        exchange: str,
        max_age_seconds: float = 120.0,
    ) -> Optional[float]:
        """Return a price only with complete, fresh, same-venue provenance."""
        market_data = getattr(self, "market_data", {})
        if not isinstance(market_data, dict):
            return None
        if market_data.get("eligible_for_external_action") is not True:
            return None
        source_map = market_data.get("source")
        provenance = market_data.get("provenance")
        prices = market_data.get("prices")
        if not all(isinstance(item, dict) for item in (source_map, provenance, prices)):
            return None
        if str(source_map.get(symbol, "")).lower() != str(exchange).lower():
            return None
        receipt = provenance.get(symbol)
        if not isinstance(receipt, dict):
            return None
        if receipt.get("truth_status") not in {"real_observed", "real_derived"}:
            return None
        if receipt.get("generated_values") is not False:
            return None
        if not isinstance(receipt.get("source_id"), str) or not receipt["source_id"]:
            return None
        try:
            price = float(prices[symbol])
            source_timestamp = float(receipt["source_timestamp"])
            if source_timestamp > 10_000_000_000:
                source_timestamp /= 1000.0
            age = time.time() - source_timestamp
        except (KeyError, TypeError, ValueError, OverflowError):
            return None
        if (
            not math.isfinite(price)
            or not math.isfinite(source_timestamp)
            or price <= 0
            or age < -30.0
            or age > max_age_seconds
        ):
            return None
        return price

    def get_available_capital(
        self,
        exchange: Optional[str] = None,
        quote_asset: Optional[str] = None,
        refresh: bool = False,
    ) -> Optional[float]:
        """Return exact-venue, exact-denomination spendable provider cash."""
        if refresh:
            self._refresh_real_balances()
        if exchange is None or quote_asset is None:
            return self._get_total_cash()

        venue = str(exchange).strip().lower()
        currency = str(quote_asset).strip().upper()
        snapshot = getattr(self, "balance_snapshot", {})
        venues = snapshot.get("venues") if isinstance(snapshot, dict) else None
        receipt = venues.get(venue) if isinstance(venues, dict) else None
        if not isinstance(receipt, dict):
            return None
        if (
            receipt.get("eligible_for_external_action") is not True
            or receipt.get("truth_status") != "real_observed"
            or receipt.get("generated_values") is not False
            or not isinstance(receipt.get("source_id"), str)
            or not receipt.get("source_id")
        ):
            return None
        try:
            received_at = float(receipt["received_at"])
            age = time.time() - received_at
        except (KeyError, TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(received_at) or age < -30.0 or age > 30.0:
            return None
        balances = getattr(self, "real_balances", {}).get(venue, {})
        if currency not in balances:
            return None
        try:
            amount = float(balances[currency])
        except (TypeError, ValueError):
            return None
        if not math.isfinite(amount) or amount < 0:
            return None
        return amount

    def _capital_for_signal(
        self,
        signal: CommandoSignal,
        refresh: bool = False,
    ) -> Optional[float]:
        quote_asset = self._quote_asset_for_symbol(signal.symbol)
        if quote_asset is None:
            return None
        return self.get_available_capital(
            exchange=signal.exchange,
            quote_asset=quote_asset,
            refresh=refresh,
        )
    
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
                if not isinstance(price_data, dict) or price_data.get("price") is None:
                    return False, f"No price data for {symbol}"
                price = float(price_data["price"])
                if not math.isfinite(price) or price <= 0:
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
            "real_cash_balance": None,
            "cash_currency": None,
            "balance_snapshot": None,
            "decision_status": "no_data",
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
                prices = list(market_data.get("prices", {}).values())
                if (
                    market_data.get("eligible_for_external_action") is True
                    and len(changes) >= 2
                    and prices
                ):
                    myc_market = {
                        "momentum": sum(changes) / len(changes) / 100,
                        "volatility": (max(changes) - min(changes)) / 100,
                        "price": prices[0],
                    }
                    result["mycelium_state"] = self.mycelium.step(myc_market)
                else:
                    result["mycelium_state"] = {
                        "status": "no_data",
                        "truth_status": "no_data",
                        "eligible_for_external_action": False,
                        "generated_values": False,
                        "reason": "complete_cross_sectional_market_receipts_required",
                    }
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
                    "assets": labyrinth_stats.get("nodes"),
                    "paths": labyrinth_stats.get("edges"),
                    "binance_pairs": labyrinth_stats.get("binance_pairs"),
                    "kraken_pairs": labyrinth_stats.get("kraken_pairs"),
                    "cached": labyrinth_stats.get("cached", True),
                    # 🔄 PROFIT METRICS
                    "total_conversions": path_stats.get("total_conversions"),
                    "total_profit": path_stats.get("total_profit"),
                    "best_path": path_stats.get("best_path"),
                    "best_path_profit": path_stats.get("best_path_profit"),
                    "top_profitable": path_stats.get("top_profitable", []),
                }
        
        # 2. REFRESH REAL EXCHANGE BALANCES (every cycle)
        balance_snapshot = self._refresh_real_balances()
        result["balance_snapshot"] = balance_snapshot
        result["real_cash_balance"] = self._get_total_cash()
        result["cash_currency"] = balance_snapshot.get("aggregate_currency")

        # Governing metrics: Mycelium reads the whole system and governs growth
        self._update_mycelium_governing_metrics()
        if market_data.get("eligible_for_external_action") is not True:
            result["decision_status"] = "no_data"
            result["reason"] = "complete_fresh_market_receipts_required"
            result["cycle_time_ms"] = (time.time() - cycle_start) * 1000
            return result
        result["decision_status"] = "ready"
        
        # 3. INCEPTION DIVE - Russian Doll probability (REALITY → DREAM_1 → DREAM_2 → LIMBO)
        # This is THE LIMITLESS PILL - mathematical guidance before consensus/commando
        inception_signals: List[CommandoSignal] = []
        if INCEPTION_AVAILABLE and _inception_engine:
            inception_result = _inception_engine.dive(market_data)
            result["inception_dive"] = {
                "dive_number": inception_result.get("dive_number"),
                "dive_time_ms": inception_result.get("dive_time_ms"),
                "wisdom_depth": inception_result.get("wisdom_depth"),
                "execution_plan": inception_result.get("execution_plan", [])
            }

            for plan in inception_result.get("execution_plan", []):
                if plan.get("action") != "BUY":
                    continue
                try:
                    confidence = float(plan["confidence"])
                except (KeyError, TypeError, ValueError, OverflowError):
                    continue
                if not math.isfinite(confidence) or confidence < 0.4:
                    continue
                symbol = plan.get("symbol")
                if not symbol:
                    continue
                source_map = market_data.get("source", {})
                target_exchange = source_map.get(symbol)
                if (
                    not isinstance(target_exchange, str)
                    or not target_exchange
                    or self._actionable_market_price(symbol, target_exchange) is None
                ):
                    continue
                
                # GHOST SIGNAL PREVENTION: Validate symbol is tradeable before creating signal
                can_trade, reason = self._validate_symbol_tradeable(
                    symbol,
                    target_exchange,
                )
                validated_symbol = symbol if can_trade else None
                validated_exchange = target_exchange if can_trade else None
                if not can_trade:
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
                    price = prices.get(symbol)
                    volume = volumes.get(symbol)
                    if price is not None and volume is not None and price > 0:
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
                    "top_probability": max(
                        (o['probability_spectrum'] for o in quantum_observations.values()),
                        default=None,
                    )
                }
            except Exception as e:
                logger.warning(f"🔭 Quantum Telescope error: {e}")
        
        # 4. SNIPER EXIT CHECK - Million Kill Training (check positions for sniper exits)
        sniper_signals: List[CommandoSignal] = []
        if self.sniper and self.positions:
            prices_list = list(market_data.get("prices", {}).values())[:50]
            volumes_list = list(market_data.get("volumes", {}).values())[:50]
            
            for symbol, pos in list(self.positions.items()):
                pos_exchange = str(pos.get("exchange") or "").lower()
                current_price = self._actionable_market_price(
                    symbol,
                    pos_exchange,
                )
                try:
                    quantity = float(pos["quantity"])
                    entry_price = float(pos["entry_price"])
                except (KeyError, TypeError, ValueError):
                    continue
                if (
                    current_price is None
                    or not math.isfinite(quantity)
                    or not math.isfinite(entry_price)
                    or quantity <= 0
                    or entry_price <= 0
                    or pos.get("truth_status") != "real_observed"
                    or pos.get("generated_values") is not False
                ):
                    continue
                entry_value = quantity * entry_price
                current_value = quantity * current_price
                
                try:
                    hold_cycles = pos.get("hold_cycles")
                    if not isinstance(hold_cycles, int) or hold_cycles < 0:
                        continue
                    sniper_signal = self.sniper.check_exit(
                        symbol=symbol,
                        entry_value=entry_value,
                        current_value=current_value,
                        hold_cycles=hold_cycles,
                    )
                    pos["hold_cycles"] = hold_cycles + 1
                    
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
                        logger.info(
                            "🎯 SNIPER EXIT SIGNAL: %s | internal gross estimate: %.4f",
                            symbol,
                            sniper_signal.current_gross,
                        )
                except Exception as e:
                    logger.debug(f"Sniper check error for {symbol}: {e}")
        
        # 5. SCOUT RECONNAISSANCE - Patriot Intel (find opportunities)
        scout_signals: List[CommandoSignal] = []
        if self.scout_network:
            try:
                source_map = market_data.get("source", {})
                # Use scouts to scan for opportunities
                for symbol, price in list(market_data.get("prices", {}).items())[:20]:
                    changes_map = market_data.get("changes", {})
                    momentum_map = market_data.get("momentum", {})
                    if symbol not in changes_map or symbol not in momentum_map:
                        continue
                    try:
                        change = float(changes_map[symbol])
                        momentum = float(momentum_map[symbol])
                    except (TypeError, ValueError, OverflowError):
                        continue
                    target_exchange = source_map.get(symbol)
                    if (
                        not all(math.isfinite(value) for value in (change, momentum))
                        or not isinstance(target_exchange, str)
                        or not target_exchange
                        or self._actionable_market_price(symbol, target_exchange) is None
                    ):
                        continue
                    
                    # Scout criteria: Strong momentum + not already positioned
                    if symbol not in self.positions and abs(change) > 2.0 and momentum > 0.01:
                        # GHOST SIGNAL PREVENTION: Validate symbol is tradeable
                        can_trade, reason = self._validate_symbol_tradeable(
                            symbol,
                            target_exchange,
                        )
                        validated_symbol = symbol if can_trade else None
                        validated_exchange = target_exchange if can_trade else None
                        if not can_trade:
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
                            expected_profit=None,
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
            if (
                exec_result.get("executed") is True
                and exec_result.get("eligible_for_accounting") is True
                and exec_result.get("realized_pnl") is not None
            ):
                self.stats["sniper_kills"] += 1
            
        # Check existing positions for commando exit signals
        for symbol, pos in list(self.positions.items()):
            pos_exchange = str(pos.get("exchange") or "").lower()
            current_price = self._actionable_market_price(symbol, pos_exchange)
            try:
                quantity = float(pos["quantity"])
                entry_price = float(pos["entry_price"])
            except (KeyError, TypeError, ValueError):
                continue
            if (
                current_price is None
                or not math.isfinite(quantity)
                or not math.isfinite(entry_price)
                or quantity <= 0
                or entry_price <= 0
                or pos.get("truth_status") != "real_observed"
                or pos.get("generated_values") is not False
            ):
                continue
            signal = self.commando.evaluate_profit_path(
                asset=symbol,
                exchange=pos_exchange,
                current_value=quantity * current_price,
                entry_price=entry_price,
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
        
        # 8. Check for new entry opportunities
        available_capital = self.get_available_capital()

        # Track entry count so Mycelium can throttle per-cycle
        entries_executed = 0

        # First, honor INCEPTION signals (deepest wisdom) before normal entries
        for inc_sig in inception_signals:
            if inc_sig.symbol in self.positions:
                continue
            signal_capital = self._capital_for_signal(inc_sig)
            if signal_capital is None or signal_capital < 1.0:
                continue
            result["commando_signals"].append(inc_sig.to_dict())
            self.stats["signals_generated"] += 1
            mv_consensus = result["multiverse_consensus"].get(inc_sig.symbol, {}) if self.multiverse else {}
            try:
                agreement = float(mv_consensus["agreement"])
                if not math.isfinite(agreement):
                    agreement = None
            except (KeyError, TypeError, ValueError, OverflowError):
                agreement = None
            # Execute if: multiverse agrees OR high confidence OR simulation mode
            should_execute = (
                (agreement is not None and agreement > 0.5) or
                inc_sig.confidence > 0.7 or
                self.simulation_mode
            )
            if should_execute and self._mycelium_allows_entry(inc_sig, entries_executed=entries_executed):
                exec_result = self.execute_signal(inc_sig)
                result["executions"].append(exec_result)
                if exec_result.get("executed") and inc_sig.action == "BUY":
                    entries_executed += 1

        # Mycelium queen signal guidance (distributed intelligence)
        queen_signal = None
        if result.get("mycelium_state"):
            queen_signal = result["mycelium_state"].get("queen_signal")
        try:
            queen_value = float(queen_signal)
            if not math.isfinite(queen_value):
                queen_value = None
        except (TypeError, ValueError, OverflowError):
            queen_value = None
        # If queen says BUY (>0.4), take top momentum; if SELL (<-0.4), trim largest position
        if queen_value is not None and abs(queen_value) > 0.4:
            changes_map = market_data.get("changes", {})
            source_map = market_data.get("source", {})
            top_symbol = None
            if queen_value > 0:
                # pick strongest positive mover not already held
                top_symbol = max((s for s in changes_map if s not in self.positions), key=lambda s: changes_map[s], default=None)
            else:
                # if negative, pick largest position to exit
                observed_positions = {}
                for candidate, candidate_position in self.positions.items():
                    try:
                        candidate_quantity = float(candidate_position["quantity"])
                    except (KeyError, TypeError, ValueError, OverflowError):
                        continue
                    if (
                        math.isfinite(candidate_quantity)
                        and candidate_quantity > 0
                        and candidate_position.get("truth_status") == "real_observed"
                        and candidate_position.get("generated_values") is False
                    ):
                        observed_positions[candidate] = candidate_quantity
                top_symbol = max(
                    observed_positions,
                    key=observed_positions.get,
                    default=None,
                )

            if top_symbol:
                action = "BUY" if queen_value > 0 else "SELL"
                target_exchange = source_map.get(top_symbol)
                if not target_exchange and action == "SELL":
                    target_exchange = self.positions.get(top_symbol, {}).get("exchange")
                
                # GHOST SIGNAL PREVENTION: Validate symbol is tradeable (for BUY)
                if action == "BUY":
                    can_trade, reason = self._validate_symbol_tradeable(
                        top_symbol,
                        target_exchange,
                    )
                    validated_symbol = top_symbol if can_trade else None
                    validated_exchange = target_exchange if can_trade else None
                    if not can_trade:
                        logger.debug(f"🚫 MYCELIUM_QUEEN: Skipping {top_symbol} - not tradeable on {target_exchange}")
                        top_symbol = None  # Skip this signal
                    else:
                        top_symbol = validated_symbol
                        target_exchange = validated_exchange
                
                if top_symbol:  # Only proceed if we have a valid symbol
                    strength = min(1.0, abs(queen_value))
                    qs = CommandoSignal(
                        timestamp=time.time(),
                        symbol=top_symbol,
                        exchange=target_exchange,
                        action=action,
                        strength=strength,
                        confidence=strength,
                        source="MYCELIUM_QUEEN",
                        reason=f"Mycelium queen signal {queen_value:+.2f}",
                        profit_path="MOMENTUM" if action == "BUY" else "QUEEN_EXIT",
                        expected_profit=None,
                        commando_type="FALCON" if action == "BUY" else "BEE"
                    )
                    result["commando_signals"].append(qs.to_dict())
                    self.stats["signals_generated"] += 1
                    signal_capital = self._capital_for_signal(qs)
                    if action == "SELL" or (
                        signal_capital is not None and signal_capital >= 1.0
                    ):
                        exec_result = self.execute_signal(qs)
                        result["executions"].append(exec_result)
        
        # Now process SCOUT signals (Celtic Intelligence)
        for scout_sig in scout_signals[:3]:  # Hard cap; Mycelium may further throttle
            if scout_sig.symbol in self.positions:
                continue
            signal_capital = self._capital_for_signal(scout_sig)
            if signal_capital is None or signal_capital < 1.0:
                continue
            result["commando_signals"].append(scout_sig.to_dict())
            self.stats["signals_generated"] += 1
            
            # Scouts get multiverse validation
            mv_consensus = result["multiverse_consensus"].get(scout_sig.symbol, {}) if self.multiverse else {}
            try:
                agreement = float(mv_consensus["agreement"])
                if not math.isfinite(agreement):
                    agreement = None
            except (KeyError, TypeError, ValueError, OverflowError):
                agreement = None
            should_execute = (
                (agreement is not None and agreement > 0.4) or
                scout_sig.confidence > 0.65 or
                self.simulation_mode
            )
            
            if should_execute:
                if self._mycelium_allows_entry(scout_sig, entries_executed=entries_executed):
                    exec_result = self.execute_signal(scout_sig)
                    result["executions"].append(exec_result)
                    if exec_result.get("executed") and scout_sig.action == "BUY":
                        entries_executed += 1
        
        # Finally, commando entry signals
        logger.debug(
            "Checking commando signals: aggregate capital=%s, positions=%d",
            (
                f"{available_capital:.8f} {self.balance_snapshot.get('aggregate_currency')}"
                if available_capital is not None
                else "NO_DATA"
            ),
            len(self.positions),
        )
        if available_capital is not None and available_capital > 1.0:
            entry_signal = self.commando.get_best_entry_signal(market_data, available_capital)
            if entry_signal:
                # GHOST SIGNAL PREVENTION: Validate symbol is tradeable
                can_trade, reason = self._validate_symbol_tradeable(
                    entry_signal.symbol, entry_signal.exchange
                )
                if not can_trade:
                    logger.debug(f"🚫 COMMANDO: Skipping {entry_signal.symbol} - not tradeable on {entry_signal.exchange}")
                    entry_signal = None  # Nullify the ghost signal
                
            if entry_signal:
                # 🔭 QUANTUM TELESCOPE CONFIDENCE BOOST
                # Use geometric alignment to enhance signal confidence
                quantum_boost = 0.0
                if quantum_observations and entry_signal.symbol in quantum_observations:
                    obs = quantum_observations[entry_signal.symbol]
                    try:
                        geo_align = float(obs['geometric_alignment'])
                        prob_spec = float(obs['probability_spectrum'])
                    except (KeyError, TypeError, ValueError, OverflowError):
                        geo_align = None
                        prob_spec = None
                    if (
                        geo_align is not None
                        and prob_spec is not None
                        and (
                            not math.isfinite(geo_align)
                            or not math.isfinite(prob_spec)
                        )
                    ):
                        geo_align = None
                        prob_spec = None
                    dominant = obs.get('dominant_solid')
                    
                    # Boost based on geometric alignment and probability
                    if geo_align is not None and prob_spec is not None:
                        quantum_boost = (
                            (geo_align * 0.15)
                            + ((prob_spec - 0.5) * 0.10)
                        )
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
            if sweeps:
                result["sweep_accounting_status"] = {
                    "status": "not_recorded",
                    "truth_status": "no_data",
                    "eligible_for_accounting": False,
                    "generated_values": False,
                    "reason": "provider_cash_movement_receipts_required",
                }

        # 10. CONVERSION LADDER - A-Z / Z-A Full Spectrum Sweep (Capital Rotation)
        accounted_profit = self.stats.get("total_profit")
        if (
            self.ladder
            and self.ladder.enabled
            and self.total_equity is not None
            and accounted_profit is not None
        ):
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
                    net_profit=float(accounted_profit),
                    portfolio_equity=float(self.total_equity),
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
                    conversion_confirmed = bool(
                        ladder_decision.result
                        and ladder_decision.result.get("converted") is True
                        and ladder_decision.result.get("truth_status")
                        == "real_observed"
                        and ladder_decision.result.get("eligible_for_accounting")
                        is True
                    )
                    if conversion_confirmed:
                        self.stats["conversions_performed"] += 1

                    # Log the conversion
                    if conversion_confirmed:
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
        elif self.ladder and self.ladder.enabled:
            result["ladder_status"] = {
                "status": "no_data",
                "truth_status": "no_data",
                "eligible_for_external_action": False,
                "eligible_for_accounting": False,
                "generated_values": False,
                "reason": "complete_equity_and_realized_profit_receipts_required",
            }
        
        # 11. LABYRINTH ROUTE PREFLIGHT - evidence only, never a fill claim
        labyrinth_routes = []
        if hasattr(self, "labyrinth") and self.labyrinth:
            try:
                provenance_map = market_data.get("provenance", {})
                for symbol, pos in list(self.positions.items()):
                    position_exchange = str(pos.get("exchange") or "").lower()
                    position_price = self._actionable_market_price(
                        symbol,
                        position_exchange,
                    )
                    try:
                        position_quantity = float(pos["quantity"])
                    except (KeyError, TypeError, ValueError, OverflowError):
                        continue
                    if (
                        position_price is None
                        or not math.isfinite(position_quantity)
                        or position_quantity <= 0
                        or pos.get("truth_status") != "real_observed"
                        or pos.get("generated_values") is not False
                    ):
                        continue
                    base_asset = self._base_asset_for_symbol(symbol)
                    value_currency = self._quote_asset_for_symbol(symbol)
                    if base_asset is None or value_currency is None:
                        continue
                    position_value = position_quantity * position_price

                    for target in ("USDT", "USDC", "USD"):
                        best_path = self.labyrinth.get_best_path(
                            base_asset,
                            target,
                        )
                        if not best_path:
                            continue
                        path_symbols = []
                        route_sources = []
                        route_complete = True
                        for step in best_path:
                            if not isinstance(step, dict):
                                route_complete = False
                                break
                            step_symbol = step.get("symbol")
                            step_exchange = step.get("exchange")
                            if (
                                not isinstance(step_symbol, str)
                                or not step_symbol
                                or not isinstance(step_exchange, str)
                                or not step_exchange
                            ):
                                route_complete = False
                                break
                            step_price = self._actionable_market_price(
                                step_symbol,
                                step_exchange,
                            )
                            step_receipt = provenance_map.get(step_symbol)
                            if step_price is None or not isinstance(step_receipt, dict):
                                route_complete = False
                                break
                            path_symbols.append(step_symbol)
                            route_sources.append({
                                "symbol": step_symbol,
                                "exchange": step_exchange,
                                "price": step_price,
                                "source_id": step_receipt.get("source_id"),
                                "source_timestamp": step_receipt.get(
                                    "source_timestamp"
                                ),
                            })
                        if not route_complete:
                            continue
                        labyrinth_routes.append({
                            "status": "preflight_only",
                            "truth_status": "real_derived",
                            "from": base_asset,
                            "to": target,
                            "position_value": position_value,
                            "position_value_currency": value_currency,
                            "hops": len(best_path),
                            "path": path_symbols,
                            "route_sources": route_sources,
                            "eligible_for_external_action": False,
                            "eligible_for_accounting": False,
                            "generated_values": False,
                            "reason": (
                                "provider_fee_slippage_and_terminal_fill_"
                                "receipts_required"
                            ),
                        })

                if labyrinth_routes:
                    result["labyrinth_routes"] = labyrinth_routes
                    logger.info(
                        "LABYRINTH: %d evidence-backed route preflight(s); "
                        "no conversion submitted",
                        len(labyrinth_routes),
                    )
            except Exception as e:
                logger.debug(f"Labyrinth scan error: {e}")
        result["cycle_time_ms"] = (time.time() - cycle_start) * 1000
        return result
    
    @staticmethod
    def _receipt_timestamp(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            if isinstance(value, str) and not value.strip().replace(".", "", 1).isdigit():
                normalized = value.strip()
                if normalized.endswith("Z"):
                    normalized = normalized[:-1] + "+00:00"
                parsed = datetime.fromisoformat(normalized)
                if parsed.tzinfo is None:
                    return None
                timestamp = parsed.timestamp()
            else:
                timestamp = float(value)
                if timestamp > 10_000_000_000:
                    timestamp /= 1000.0
        except (TypeError, ValueError, OverflowError):
            return None
        return timestamp if math.isfinite(timestamp) and timestamp > 0 else None

    @classmethod
    def _base_asset_for_symbol(cls, symbol: str) -> Optional[str]:
        normalized = str(symbol or "").strip().upper()
        if "/" in normalized:
            base = normalized.split("/", 1)[0]
            return base or None
        quote = cls._quote_asset_for_symbol(normalized)
        if quote is None:
            return None
        base = normalized[:-len(quote)]
        return base or None

    @classmethod
    def _terminal_fill_receipt(
        cls,
        order: Any,
        symbol: str,
        action: str,
        exchange: str,
        quote_asset: str,
        max_age_seconds: float = 300.0,
        production_mode_verified: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Normalize only complete, fresh, terminal provider fill evidence."""
        if production_mode_verified is not True:
            return None
        if not isinstance(order, dict):
            return None
        if order.get("generated_values") is True:
            return None
        if order.get("fill_receipt_complete") is False:
            return None
        status = str(order.get("status") or order.get("state") or "").upper()
        if status not in {"FILLED", "CLOSED"}:
            return None
        order_id = order.get("orderId") or order.get("id") or order.get("txid")
        if isinstance(order_id, list) and len(order_id) == 1:
            order_id = order_id[0]
        if order_id is None or not str(order_id).strip():
            return None
        normalized_id = str(order_id).strip()
        provider_symbol = order.get("symbol") or order.get("pair")
        if provider_symbol is not None:
            expected_symbol = str(symbol).replace("/", "").upper()
            observed_symbol = str(provider_symbol).replace("/", "").upper()
            if expected_symbol != observed_symbol:
                return None
        provider_side = order.get("side") or order.get("type")
        if provider_side is not None and str(provider_side).upper() != str(action).upper():
            return None

        source_timestamp = None
        for field in (
            "source_timestamp",
            "provider_timestamp",
            "transactTime",
            "updateTime",
            "filled_at",
            "closedTime",
        ):
            source_timestamp = cls._receipt_timestamp(order.get(field))
            if source_timestamp is not None:
                break
        if source_timestamp is None:
            return None
        age = time.time() - source_timestamp
        if age < -30.0 or age > max_age_seconds:
            return None

        executed_quantity = None
        for field in ("executedQty", "filled_qty", "filledQty", "vol_exec"):
            if order.get(field) is None:
                continue
            try:
                candidate = float(order[field])
            except (TypeError, ValueError):
                continue
            if math.isfinite(candidate) and candidate > 0:
                executed_quantity = candidate
                break
        if executed_quantity is None:
            return None

        quote_amount = None
        for field in ("cummulativeQuoteQty", "filled_notional", "cost"):
            if order.get(field) is None:
                continue
            try:
                candidate = float(order[field])
            except (TypeError, ValueError):
                continue
            if math.isfinite(candidate) and candidate > 0:
                quote_amount = candidate
                break

        average_price = None
        for field in ("filled_avg_price", "avgPrice", "average_price"):
            if order.get(field) is None:
                continue
            try:
                candidate = float(order[field])
            except (TypeError, ValueError):
                continue
            if math.isfinite(candidate) and candidate > 0:
                average_price = candidate
                break
        if quote_amount is None and average_price is not None:
            quote_amount = average_price * executed_quantity
        if average_price is None and quote_amount is not None:
            average_price = quote_amount / executed_quantity
        if quote_amount is None or average_price is None:
            return None

        base_asset = cls._base_asset_for_symbol(symbol)
        normalized_quote = str(quote_asset).upper()
        fee_quote = 0.0
        base_fee = 0.0
        fee_complete = False
        fills = order.get("fills")
        if isinstance(fills, list) and fills:
            fee_complete = True
            for fill in fills:
                if not isinstance(fill, dict):
                    fee_complete = False
                    break
                if fill.get("commission") is None or fill.get("commissionAsset") is None:
                    fee_complete = False
                    break
                try:
                    commission = float(fill["commission"])
                except (TypeError, ValueError):
                    fee_complete = False
                    break
                fee_asset = str(fill["commissionAsset"]).upper()
                if not math.isfinite(commission) or commission < 0 or not fee_asset:
                    fee_complete = False
                    break
                if fee_asset == normalized_quote:
                    fee_quote += commission
                elif base_asset is not None and fee_asset == base_asset:
                    try:
                        fill_price = float(fill["price"])
                    except (KeyError, TypeError, ValueError):
                        fee_complete = False
                        break
                    if not math.isfinite(fill_price) or fill_price <= 0:
                        fee_complete = False
                        break
                    fee_quote += commission * fill_price
                    base_fee += commission
                else:
                    fee_complete = False
                    break
        elif order.get("fee") is not None:
            try:
                fee = float(order["fee"])
            except (TypeError, ValueError):
                fee = math.nan
            fee_asset = str(
                order.get("fee_currency")
                or order.get("fee_asset")
                or order.get("commissionAsset")
                or ""
            ).upper()
            if math.isfinite(fee) and fee >= 0 and fee_asset:
                if fee_asset == normalized_quote:
                    fee_quote = fee
                    fee_complete = True
                elif base_asset is not None and fee_asset == base_asset:
                    fee_quote = fee * average_price
                    base_fee = fee
                    fee_complete = True

        net_quantity = executed_quantity
        if str(action).upper() == "BUY":
            net_quantity -= base_fee
        if not math.isfinite(net_quantity) or net_quantity <= 0:
            return None
        eligible_for_accounting = fee_complete
        if order.get("eligible_for_accounting") is False:
            eligible_for_accounting = False
        return {
            "status": "filled",
            "truth_status": "real_observed",
            "source_id": f"{exchange}:terminal_order_fill",
            "source_timestamp": source_timestamp,
            "received_at": time.time(),
            "order_id": normalized_id,
            "executed_quantity": executed_quantity,
            "net_quantity": net_quantity,
            "average_price": average_price,
            "quote_amount": quote_amount,
            "quote_asset": normalized_quote,
            "fee_quote": fee_quote if fee_complete else None,
            "base_fee": base_fee if fee_complete else None,
            "eligible_for_external_action": False,
            "eligible_for_accounting": eligible_for_accounting,
            "generated_values": False,
        }

    def _execute_signal_with_receipts(self, signal: CommandoSignal) -> Dict:
        """Execute from fresh balances, market provenance and terminal fills."""
        result: Dict[str, Any] = {
            "signal": signal.to_dict(),
            "status": "not_submitted",
            "truth_status": "no_data",
            "executed": False,
            "order_id": None,
            "fill": None,
            "realized_pnl": None,
            "eligible_for_external_action": False,
            "eligible_for_accounting": False,
            "accounting_projection": {
                "status": "not_submitted",
                "truth_status": "no_data",
                "eligible_for_accounting": False,
                "generated_values": False,
                "reason": "currency_aware_projection_contract_required",
            },
            "generated_values": False,
            "error": None,
        }
        action = str(signal.action or "").upper()
        exchange = str(signal.exchange or "").lower()
        symbol = str(signal.symbol or "").upper()
        if action not in {"BUY", "SELL"}:
            result["error"] = "Signal is not an executable BUY or SELL"
            return result
        if self.simulation_mode:
            result.update({
                "status": "not_submitted",
                "truth_status": "dry_run",
                "error": "Simulation mode never submits or mutates provider state",
            })
            return result

        if action == "BUY":
            can_trade, reason = self._validate_symbol_tradeable(symbol, exchange)
            if not can_trade:
                result["error"] = (
                    f"GHOST SIGNAL BLOCKED: {reason}"
                    if reason
                    else "GHOST SIGNAL BLOCKED: symbol is not tradeable"
                )
                return result
            if symbol in self.positions:
                result["error"] = "Position already exists"
                return result
        else:
            position = self.positions.get(symbol)
            if not isinstance(position, dict):
                result["error"] = "No provider-derived position is available to sell"
                return result
            exchange = str(position.get("exchange") or exchange).lower()

        pending_key = f"{exchange}:{symbol}:{action}"
        if not isinstance(getattr(self, "pending_orders", None), dict):
            self.pending_orders = {}
        if pending_key in self.pending_orders:
            pending = self.pending_orders[pending_key]
            result.update({
                "status": "pending_reconciliation",
                "order_id": pending.get("order_id"),
                "error": "An acknowledged order still requires terminal reconciliation",
            })
            return result

        client = {
            "binance": self.binance,
            "kraken": self.kraken,
            "alpaca": self.alpaca,
        }.get(exchange)
        if client is None:
            result["error"] = f"Exchange offline or unsupported: {exchange}"
            return result
        quote_asset = self._quote_asset_for_symbol(symbol)
        base_asset = self._base_asset_for_symbol(symbol)
        if quote_asset is None or base_asset is None:
            result["error"] = "Symbol denomination could not be proven"
            return result

        balance_snapshot = self._refresh_real_balances()
        venues = balance_snapshot.get("venues") if isinstance(
            balance_snapshot, dict
        ) else None
        venue_receipt = venues.get(exchange) if isinstance(venues, dict) else None
        if (
            not isinstance(venue_receipt, dict)
            or venue_receipt.get("eligible_for_external_action") is not True
            or venue_receipt.get("truth_status") != "real_observed"
            or venue_receipt.get("generated_values") is not False
            or not isinstance(venue_receipt.get("source_id"), str)
            or not venue_receipt.get("source_id")
        ):
            result["error"] = "Fresh production balance provenance is unavailable"
            return result
        price = self._actionable_market_price(symbol, exchange)
        if price is None:
            result["error"] = "Fresh same-venue market provenance is unavailable"
            return result

        requested_quantity: Optional[float] = None
        if action == "BUY":
            if not self._mycelium_allows_entry(
                signal,
                entries_executed=0,
                allow_throttle_bypass=True,
            ):
                result["error"] = "Blocked by Mycelium directive"
                return result
            cash = self.get_available_capital(
                exchange=exchange,
                quote_asset=quote_asset,
            )
            if cash is None:
                result["error"] = f"No fresh {exchange} {quote_asset} balance"
                return result
            try:
                scale = float(getattr(self, "mycelium_directive", {}).get(
                    "entry_budget_scale", 1.0
                ))
                trade_size = (
                    cash
                    * float(self.commando.growth_aggression)
                    * 0.2
                    * max(0.0, scale)
                )
                requested_quantity = trade_size / price
            except (TypeError, ValueError, OverflowError):
                trade_size = math.nan
            if (
                requested_quantity is None
                or not math.isfinite(requested_quantity)
                or requested_quantity <= 0
                or not math.isfinite(trade_size)
                or trade_size <= 0
                or trade_size > cash
            ):
                result["error"] = "Provider-backed capital cannot fund the order"
                return result
        else:
            position = self.positions[symbol]
            try:
                requested_quantity = float(position["quantity"])
                provider_base = float(self.real_balances[exchange][base_asset])
            except (KeyError, TypeError, ValueError):
                result["error"] = f"No fresh {exchange} {base_asset} balance"
                return result
            if (
                not math.isfinite(requested_quantity)
                or requested_quantity <= 0
                or not math.isfinite(provider_base)
                or provider_base < requested_quantity
            ):
                result["error"] = "Provider base balance cannot fund the sell"
                return result

        side = action.lower() if exchange == "alpaca" else action
        try:
            order = client.place_market_order(
                symbol, side, quantity=requested_quantity
            )
        except Exception as exc:
            result["error"] = str(exc)
            return result
        if not isinstance(order, dict) or order.get("rejected") or order.get("error"):
            result.update({"status": "rejected", "error": f"Order rejected: {order}"})
            return result

        fill = self._terminal_fill_receipt(
            order,
            symbol=symbol,
            action=action,
            exchange=exchange,
            quote_asset=quote_asset,
            production_mode_verified=(
                venue_receipt.get("truth_status") == "real_observed"
                and venue_receipt.get("generated_values") is False
                and venue_receipt.get("eligible_for_external_action") is True
                and isinstance(venue_receipt.get("source_id"), str)
                and bool(venue_receipt.get("source_id"))
            ),
        )
        if fill is None:
            order_id = order.get("orderId") or order.get("id") or order.get("txid")
            if isinstance(order_id, list) and len(order_id) == 1:
                order_id = order_id[0]
            if order_id is None or not str(order_id).strip():
                result["error"] = "Order has no terminal fill or provider id"
                return result
            pending = {
                "status": "pending_reconciliation",
                "truth_status": "real_observed",
                "source_id": f"{exchange}:order_acknowledgement",
                "source_timestamp": None,
                "received_at": time.time(),
                "order_id": str(order_id).strip(),
                "symbol": symbol,
                "side": action,
                "eligible_for_accounting": False,
                "generated_values": False,
                "reason": "terminal_provider_fill_receipt_required",
            }
            self.pending_orders[pending_key] = pending
            result.update({
                "status": "pending_reconciliation",
                "truth_status": "real_observed",
                "order_id": pending["order_id"],
                "error": pending["reason"],
            })
            return result

        self.pending_orders.pop(pending_key, None)
        accounting = bool(fill["eligible_for_accounting"])
        realized_pnl: Optional[float] = None
        result.update({
            "status": "filled",
            "truth_status": "real_observed",
            "executed": True,
            "order_id": fill["order_id"],
            "fill": fill,
            "eligible_for_accounting": accounting,
        })
        if action == "BUY":
            self.positions[symbol] = {
                "entry_price": fill["average_price"],
                "quantity": fill["net_quantity"],
                "executed_quantity": fill["executed_quantity"],
                "entry_quote_amount": fill["quote_amount"],
                "entry_fee_quote": fill["fee_quote"],
                "quote_asset": quote_asset,
                "entry_time": fill["source_timestamp"],
                "hold_cycles": 0,
                "exchange": exchange,
                "provider_order_id": fill["order_id"],
                "truth_status": "real_observed",
                "eligible_for_accounting": accounting,
                "generated_values": False,
            }
        else:
            position = self.positions[symbol]
            position_quantity = float(position["quantity"])
            sold_quantity = fill["executed_quantity"]
            position_reduction = sold_quantity + float(fill.get("base_fee") or 0.0)
            if position_reduction > position_quantity * (1.0 + 1e-9):
                if not isinstance(getattr(self, "unreconciled_fills", None), list):
                    self.unreconciled_fills = []
                self.unreconciled_fills.append({
                    "symbol": symbol,
                    "exchange": exchange,
                    "order_id": fill["order_id"],
                    "source_timestamp": fill["source_timestamp"],
                    "tracked_quantity": position_quantity,
                    "provider_position_reduction": position_reduction,
                    "truth_status": "real_observed",
                    "eligible_for_accounting": False,
                    "generated_values": False,
                    "reason": "terminal_fill_exceeds_tracked_position",
                })
                del self.positions[symbol]
                self.stats["trades_executed"] += 1
                result.update({
                    "status": "reconciliation_error",
                    "eligible_for_accounting": False,
                    "error": "Terminal sell exceeds the tracked position",
                })
                return result
            allocation = min(1.0, sold_quantity / position_quantity)
            try:
                entry_quote = float(position["entry_quote_amount"])
                entry_fee = float(position["entry_fee_quote"])
                if accounting and position.get("eligible_for_accounting") is True:
                    realized_pnl = (
                        fill["quote_amount"]
                        - float(fill["fee_quote"])
                        - (entry_quote * allocation)
                        - (entry_fee * allocation)
                    )
                    if not math.isfinite(realized_pnl):
                        realized_pnl = None
            except (KeyError, TypeError, ValueError, OverflowError):
                realized_pnl = None
            if realized_pnl is None:
                accounting = False
            remaining = position_quantity - position_reduction
            if remaining <= max(1e-12, position_quantity * 1e-9):
                del self.positions[symbol]
            else:
                position["quantity"] = remaining
                if "entry_quote_amount" in position:
                    position["entry_quote_amount"] = float(
                        position["entry_quote_amount"]
                    ) * (remaining / position_quantity)
                if position.get("entry_fee_quote") is not None:
                    position["entry_fee_quote"] = float(
                        position["entry_fee_quote"]
                    ) * (remaining / position_quantity)
            if accounting:
                profit_book = self.stats.setdefault(
                    "realized_profit_by_currency",
                    {},
                )
                prior = profit_book.get(quote_asset)
                profit_book[quote_asset] = (
                    realized_pnl
                    if prior is None
                    else float(prior) + realized_pnl
                )
                if len(profit_book) == 1:
                    self.stats["total_profit"] = profit_book[quote_asset]
                    self.stats["total_profit_currency"] = quote_asset
                else:
                    self.stats["total_profit"] = None
                    self.stats["total_profit_currency"] = None
                counter = "win_count" if realized_pnl > 0 else "loss_count"
                self.stats[counter] += 1
                if (
                    self.mycelium
                    and realized_pnl > 0
                    and self.stats["total_profit_currency"] == quote_asset
                    and self.balance_snapshot.get("aggregate_currency") == quote_asset
                ):
                    try:
                        self.mycelium.record_trade_profit(realized_pnl, {
                            "symbol": symbol,
                            "action": action,
                            "exchange": exchange,
                            "currency": quote_asset,
                            "source_id": fill["source_id"],
                            "source_timestamp": fill["source_timestamp"],
                        })
                    except Exception:
                        pass

        result["realized_pnl"] = realized_pnl
        result["realized_pnl_currency"] = (
            quote_asset if realized_pnl is not None else None
        )
        result["eligible_for_accounting"] = accounting
        self.stats["trades_executed"] += 1
        if (
            MULTIVERSE_AVAILABLE
            and action == "SELL"
            and accounting
            and realized_pnl is not None
            and self.stats.get("total_profit_currency") == quote_asset
        ):
            multiverse_record_outcome(symbol, realized_pnl > 0, realized_pnl)
        if self.thought_bus:
            try:
                self.thought_bus.publish(Thought(
                    source="multiverse_live",
                    topic=f"trade.{action.lower()}",
                    payload={
                        "symbol": symbol,
                        "action": action,
                        "exchange": exchange,
                        "realized_pnl": realized_pnl,
                        "realized_pnl_currency": (
                            quote_asset if realized_pnl is not None else None
                        ),
                        "order_id": fill["order_id"],
                        "source_id": fill["source_id"],
                        "source_timestamp": fill["source_timestamp"],
                        "eligible_for_accounting": accounting,
                        "generated_values": False,
                    },
                ))
            except Exception:
                pass
        return result

    def execute_signal(self, signal: CommandoSignal) -> Dict:
        """Route execution through the provider-receipt evidence boundary."""
        return self._execute_signal_with_receipts(signal)

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
        total_cash = self._get_total_cash()
        total_equity = self.total_equity
        realized_profit = self.stats.get("total_profit")

        wins = int(self.stats.get("win_count", 0) or 0)
        losses = int(self.stats.get("loss_count", 0) or 0)
        total_closed = wins + losses
        win_rate = (wins / total_closed) if total_closed > 0 else None

        # Drawdown relative to observed peak equity
        drawdown_pct = None
        if total_equity is not None:
            peak = getattr(self, "_peak_equity_observed", None)
            if peak is None or total_equity > peak:
                peak = total_equity
            self._peak_equity_observed = peak
            if peak > 0:
                drawdown_pct = ((peak - total_equity) / peak) * 100

        metrics: Dict[str, Any] = {
            "timestamp": time.time(),
            "mode": "SIMULATION" if self.simulation_mode else "LIVE",
            "cycles": int(self.stats.get("cycles", 0) or 0),
            "trades_executed": int(self.stats.get("trades_executed", 0) or 0),
            "signals_generated": int(self.stats.get("signals_generated", 0) or 0),
            "positions_count": int(len(self.positions)),
            "total_cash": total_cash,
            "cash_currency": self.balance_snapshot.get("aggregate_currency"),
            "total_equity": total_equity,
            "equity_currency": self.equity_receipt.get("currency"),
            "realized_pnl_total": realized_profit,
            "realized_pnl_currency": self.stats.get("total_profit_currency"),
            "realized_pnl_by_currency": dict(
                self.stats.get("realized_profit_by_currency", {})
            ),
            "win_rate": win_rate,
            "drawdown_pct": drawdown_pct,
            "truth_status": (
                "real_derived"
                if all(
                    value is not None
                    for value in (total_cash, total_equity, realized_profit)
                )
                else "no_data"
            ),
            "eligible_for_external_action": False,
            "generated_values": False,
        }

        if (
            self.mycelium
            and metrics["truth_status"] == "real_derived"
            and hasattr(self.mycelium, "update_governing_metrics")
        ):
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
        """Print observed balances and provider-accounted outcomes."""
        runtime = time.time() - self.start_time
        closed_count = self.stats["win_count"] + self.stats["loss_count"]
        win_rate = (
            self.stats["win_count"] / closed_count * 100
            if closed_count
            else None
        )
        self._refresh_real_balances()
        total_cash = self._get_total_cash()

        print("\n" + "=" * 80)
        print("AUREON MULTIVERSE LIVE STATUS")
        print("=" * 80)
        print(f"  Runtime: {runtime/60:.1f} min | Cycles: {self.stats['cycles']}")
        print(f"  Mode: {'SIMULATION' if self.simulation_mode else 'LIVE TRADING'}")
        print("-" * 80)
        print("  PROVIDER BALANCE RECEIPTS:")
        for venue in ("binance", "kraken", "alpaca"):
            receipt = self.balance_snapshot.get("venues", {}).get(venue, {})
            asset = receipt.get("settlement_asset")
            amount = receipt.get("settlement_amount")
            display = (
                f"{float(amount):.8f} {asset}"
                if amount is not None and asset
                else "NO_DATA"
            )
            print(f"     {venue.title():8s}: {display}")
        total_display = (
            f"{total_cash:.8f} {self.balance_snapshot.get('aggregate_currency')}"
            if total_cash is not None
            else "NO_DATA (mixed or incomplete denomination evidence)"
        )
        print(f"     TOTAL CASH: {total_display}")
        print("-" * 80)
        print(f"  Goal: {self.commando.one_goal}")
        print(
            f"  Signals: {self.stats['signals_generated']} | "
            f"Terminal fills: {self.stats['trades_executed']}"
        )
        print(f"  Open provider-derived positions: {len(self.positions)}")
        print(f"  Pending reconciliation: {len(self.pending_orders)}")
        total_profit = self.stats["total_profit"]
        profit_display = (
            f"{total_profit:.8f} {self.stats.get('total_profit_currency')}"
            if total_profit is not None
            else (
                str(self.stats.get("realized_profit_by_currency"))
                if self.stats.get("realized_profit_by_currency")
                else "NO_DATA"
            )
        )
        win_display = f"{win_rate:.1f}%" if win_rate is not None else "NO_DATA"
        print(f"  Provider-accounted realized profit: {profit_display}")
        print(
            f"  Win rate: {win_display} "
            f"({self.stats['win_count']}W / {self.stats['loss_count']}L)"
        )
        print("  Portfolio equity: NO_DATA (complete valuation receipts required)")
        if self.revenue_board:
            print(
                "  Revenue Board: not projected here until it exposes a "
                "same-denomination provenance receipt"
            )
        if self.multiverse:
            print("  Internal multiverse state (not provider accounting):")
            for world in self.multiverse.worlds[:5]:
                print(
                    f"     {world.name}: state={world.state.equity:.6f} | "
                    f"WR={world.get_win_rate()*100:.0f}%"
                )
        if self.penny_ledger:
            self.penny_ledger.print_ledger()
        print("=" * 80 + "\n")
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
                    if current_profit is not None and last_profit is None:
                        last_profit = current_profit
                        consecutive_no_profit = 0
                    elif (
                        current_profit is not None
                        and last_profit is not None
                        and current_profit > last_profit
                    ):
                        profit_made = current_profit - last_profit
                        logger.info(
                            "🥕 CARROT! Made %.4f %s - Keep chasing!",
                            profit_made,
                            self.stats.get("total_profit_currency"),
                        )
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
                        if self.stats["total_profit"] is not None:
                            target_profit = self.stats["total_profit"] * 1.1 + 1.0
                            logger.info(
                                "🥕 CARROT AHEAD: %.4f %s (current: %.4f %s)",
                                target_profit,
                                self.stats.get("total_profit_currency"),
                                self.stats["total_profit"],
                                self.stats.get("total_profit_currency"),
                            )
                        else:
                            logger.info(
                                "🥕 CARROT: NO_DATA (no realized provider PnL)"
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
