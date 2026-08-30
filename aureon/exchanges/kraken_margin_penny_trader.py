#!/usr/bin/env python3
"""
KRAKEN MARGIN ARMY TRADER - ALL IN, GBP1 PROFIT, OUT
=====================================================
Army discipline: 1 position only. ALL margin. Max leverage.
Capture GBP1 real realized profit (~$1.27). Close. Next target. Repeat.

ARCHITECTURE:
  MONITORING -> FREE APIs (Binance public REST — no auth, no limits)
  EXECUTION  -> Kraken API (open + close ONLY — 3 calls per trade cycle)

  Kraken API calls per trade:
    1. get_trade_balance()       check margin before opening
    2. place_margin_order()      open the position
    3. close_margin_position()   close when profitable

  ALL price monitoring uses Binance public API.
  Zero rate-limit risk. Zero wasted Kraken calls.

Usage:
    python kraken_margin_penny_trader.py              # Live trading
    python kraken_margin_penny_trader.py --dry-run     # Simulation mode
    python kraken_margin_penny_trader.py --scan-only   # Show margin pairs
"""

import os
import sys
import json
import time
import hashlib
import logging
import argparse
import threading
import math
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from collections import deque
from pathlib import Path

# Production startup should be deterministic and quiet unless explicitly overridden.
os.environ.setdefault("AUREON_QUIET_STARTUP", "1")

# Ensure repo-root package imports resolve when this file is launched directly.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from aureon.core.aureon_env import load_aureon_environment

    load_aureon_environment(Path(_REPO_ROOT), override=False)
except Exception:
    pass

# Import ETA predictor for margin positions
try:
    from aureon.monitors.margin_eta_predictor import MarginETAPredictor
    HAS_ETA_PREDICTOR = True
except ImportError:
    try:
        from aureon.monitors.margin_eta_predictor import MarginETAPredictor
        HAS_ETA_PREDICTOR = True
    except ImportError:
        HAS_ETA_PREDICTOR = False
        logger_temp = logging.getLogger("margin_army")
        logger_temp.warning("ETA predictor not available - install margin_eta_predictor.py")

# Dead Man's Switch - Dynamic Take Profit
try:
    from aureon.trading.dynamic_take_profit import DynamicTakeProfit, DTP_CONFIG
    HAS_DTP = True
except ImportError:
    HAS_DTP = False
    DynamicTakeProfit = None
    DTP_CONFIG = {'activation_threshold': 1.27, 'trailing_distance_pct': 0.02, 'gbp_usd_rate': 1.27}

# Margin Wave Rider - pre-entry 250% margin safety gate
try:
    from aureon.trading.margin_wave_rider import MarginWaveRider, WAVE_CONFIG
    HAS_WAVE_RIDER = True
except ImportError:
    HAS_WAVE_RIDER = False
    MarginWaveRider = None
    WAVE_CONFIG = {'entry_min_margin_pct': 250.0, 'danger_margin_pct': 110.0}

# Dynamic margin sizing - live collateral-aware position planner
try:
    from aureon.trading.dynamic_margin_sizer import (
        DynamicMarginConfig,
        DynamicMarginSizer,
        MarginCapitalSnapshot,
        PositionSizePlan,
    )
    HAS_DYNAMIC_MARGIN_SIZER = True
except ImportError:
    HAS_DYNAMIC_MARGIN_SIZER = False
    DynamicMarginConfig = None
    DynamicMarginSizer = None
    MarginCapitalSnapshot = None
    PositionSizePlan = None

# Human-time trade cognition - projection and verification audit trail
try:
    from aureon.trading.temporal_trade_cognition import TemporalTradeCognition
    HAS_TEMPORAL_TRADE_COGNITION = True
except ImportError:
    HAS_TEMPORAL_TRADE_COGNITION = False
    TemporalTradeCognition = None

# Unified margin brain - final approve/wait/reject decision layer
try:
    from aureon.trading.unified_margin_brain import (
        MarginBrainConfig,
        UnifiedMarginDecisionBrain,
    )
    HAS_UNIFIED_MARGIN_BRAIN = True
except ImportError:
    HAS_UNIFIED_MARGIN_BRAIN = False
    MarginBrainConfig = None
    UnifiedMarginDecisionBrain = None

# Stallion Tracker - Apache phase intelligence (ROPING→BUCKING→TIRING→TAMED)
try:
    from aureon.utils.stallion_tracker import classify_phase, StallionPhase
    HAS_STALLION = True
except ImportError:
    HAS_STALLION = False
    classify_phase = None
    StallionPhase = None

# Stallion Multiverse - parallel shadow rides + 1-hour rotation
try:
    from aureon.simulation.stallion_multiverse import StallionMultiverse, MULTIVERSE_CONFIG
    HAS_MULTIVERSE = True
except ImportError:
    HAS_MULTIVERSE = False
    StallionMultiverse = None
    MULTIVERSE_CONFIG = {'real_ride_limit_secs': 3600, 'max_shadows': 10}

# Multiverse Learning Bridge - adaptive learning → Seer, Lyra, pre-trade
try:
    from aureon.bridges.multiverse_learning_bridge import MultiverseLearningBridge
    HAS_LEARNING_BRIDGE = True
except ImportError:
    HAS_LEARNING_BRIDGE = False
    MultiverseLearningBridge = None

# Autonomous Trading Orchestrator - central nervous system for all systems
try:
    from aureon.autonomous.autonomous_trading_orchestrator import AutonomousOrchestrator
    HAS_ORCHESTRATOR = True
except ImportError:
    HAS_ORCHESTRATOR = False
    AutonomousOrchestrator = None

# Goal Recorder — proof file for entry goal vs actual outcome
try:
    from aureon.monitors.margin_goal_recorder import MarginGoalRecorder
    HAS_GOAL_RECORDER = True
except ImportError:
    HAS_GOAL_RECORDER = False
    MarginGoalRecorder = None

# Macro Intelligence — pre-execution market context (F&G, BTC trend, dominance, news)
try:
    from aureon.intelligence.macro_intelligence import MacroIntelligence
    HAS_MACRO_INTEL = True
except ImportError:
    HAS_MACRO_INTEL = False
    MacroIntelligence = None

# Additional repo scanners for mission selection enrichment
try:
    from aureon.intelligence.aureon_seer import get_seer
    HAS_SEER = True
except ImportError:
    HAS_SEER = False
    get_seer = None

try:
    from aureon.command_centers.war_strategy import should_attack, get_quick_kill_estimate
    HAS_WAR_STRATEGY = True
except ImportError:
    HAS_WAR_STRATEGY = False
    should_attack = None
    get_quick_kill_estimate = None

HAS_SNIPER_BRAIN = False
get_unified_brain = None


def _load_unified_sniper_brain():
    """Lazy-load the heavy sniper brain only when a live trader is constructed."""
    global HAS_SNIPER_BRAIN, get_unified_brain
    if get_unified_brain is not None:
        return get_unified_brain
    try:
        from aureon.trading.unified_sniper_brain import get_unified_brain as factory

        get_unified_brain = factory
        HAS_SNIPER_BRAIN = True
        return get_unified_brain
    except Exception:
        HAS_SNIPER_BRAIN = False
        get_unified_brain = None
        return None

try:
    from aureon.intelligence.nexus_predictor import NexusPredictor
    HAS_NEXUS_PREDICTOR = True
except ImportError:
    HAS_NEXUS_PREDICTOR = False
    NexusPredictor = None

try:
    from aureon.core.aureon_lattice import LatticeEngine
    HAS_LATTICE = True
except ImportError:
    HAS_LATTICE = False
    LatticeEngine = None

try:
    from aureon.intelligence.aureon_seer_integration import seer_get_vision
    HAS_SEER_INTEGRATION = True
except ImportError:
    HAS_SEER_INTEGRATION = False
    seer_get_vision = None

try:
    from aureon.trading.aureon_lyra_integration import lyra_get_resonance
    HAS_LYRA_INTEGRATION = True
except ImportError:
    HAS_LYRA_INTEGRATION = False
    lyra_get_resonance = None

try:
    from aureon.atn.aureon_atn_monitor import get_atn_monitor
    HAS_ATN_MONITOR = True
except ImportError:
    HAS_ATN_MONITOR = False
    get_atn_monitor = None

try:
    from aureon.intelligence.aureon_unified_intelligence_registry import get_unified_puller
    HAS_UNIFIED_REGISTRY = True
except ImportError:
    HAS_UNIFIED_REGISTRY = False
    get_unified_puller = None

try:
    from aureon.intelligence.aureon_unified_decision_engine import (
        UnifiedDecisionEngine,
        SignalInput,
        CoordinationInput,
        DecisionType,
        DecisionReason,
    )
    HAS_UNIFIED_DECISION = True
except ImportError:
    HAS_UNIFIED_DECISION = False
    UnifiedDecisionEngine = None
    SignalInput = None
    CoordinationInput = None
    DecisionType = None
    DecisionReason = None

try:
    from aureon.core.aureon_thought_bus import get_thought_bus, Thought
    HAS_THOUGHT_BUS = True
except ImportError:
    HAS_THOUGHT_BUS = False
    get_thought_bus = None
    Thought = None

try:
    from aureon.scanners.aureon_margin_harmonic_scanner import HarmonicMarginWaveformScanner
    HAS_MARGIN_HARMONIC_SCANNER = True
except ImportError:
    HAS_MARGIN_HARMONIC_SCANNER = False
    HarmonicMarginWaveformScanner = None

try:
    from aureon.scanners.aureon_quantum_mirror_scanner import create_quantum_scanner
    HAS_QUANTUM_MIRROR_SCANNER = True
except ImportError:
    HAS_QUANTUM_MIRROR_SCANNER = False
    create_quantum_scanner = None

try:
    from aureon.intelligence.aureon_timeline_oracle import get_timeline_oracle
    HAS_TIMELINE_ORACLE = True
except ImportError:
    HAS_TIMELINE_ORACLE = False
    get_timeline_oracle = None

try:
    from aureon.harmonic.aureon_harmonic_fusion import HarmonicWaveFusion
    HAS_HARMONIC_FUSION = True
except ImportError:
    HAS_HARMONIC_FUSION = False
    HarmonicWaveFusion = None

try:
    from aureon.analytics.aureon_whale_orderbook_analyzer import WhaleOrderbookAnalyzer
    HAS_WHALE_ORDERBOOK = True
except ImportError:
    HAS_WHALE_ORDERBOOK = False
    WhaleOrderbookAnalyzer = None

try:
    from aureon.exchanges.kraken_fee_tracker import get_kraken_fee_tracker
    HAS_KRAKEN_FEE_TRACKER = True
except ImportError:
    try:
        from aureon.exchanges.kraken_fee_tracker import get_kraken_fee_tracker
        HAS_KRAKEN_FEE_TRACKER = True
    except ImportError:
        HAS_KRAKEN_FEE_TRACKER = False
        get_kraken_fee_tracker = None

try:
    from aureon.scanners.aureon_ocean_wave_scanner import OceanWaveScanner
    HAS_OCEAN_WAVE_SCANNER = True
except ImportError:
    HAS_OCEAN_WAVE_SCANNER = False
    OceanWaveScanner = None

try:
    from aureon.intelligence.aureon_brain import AureonBrain
    HAS_AUREON_BRAIN = True
except Exception:
    HAS_AUREON_BRAIN = False
    AureonBrain = None

try:
    from aureon.portfolio.trade_profit_validator import TradeProfitValidator
    HAS_TRADE_PROFIT_VALIDATOR = True
except Exception:
    HAS_TRADE_PROFIT_VALIDATOR = False
    TradeProfitValidator = None

# ── TIER 1: High-Impact Signal Producers ────────────────────────────────────
try:
    from aureon.intelligence.aureon_phase_transition_detector import PhaseTransitionDetector
    HAS_PHASE_TRANSITION = True
except Exception:
    HAS_PHASE_TRANSITION = False
    PhaseTransitionDetector = None

try:
    from aureon.strategies.probability_ultimate_intelligence import get_ultimate_intelligence
    HAS_PROB_ULTIMATE = True
except Exception:
    HAS_PROB_ULTIMATE = False
    get_ultimate_intelligence = None

try:
    from aureon.data_feeds.news_signal import get_news_signal
    HAS_NEWS_SIGNAL = True
except Exception:
    HAS_NEWS_SIGNAL = False
    get_news_signal = None

try:
    from aureon.scanners.aureon_phantom_signal_filter import PhantomSignalFilter
    HAS_PHANTOM_FILTER = True
except Exception:
    HAS_PHANTOM_FILTER = False
    PhantomSignalFilter = None

try:
    from aureon.data_feeds.global_financial_feed import GlobalFinancialFeed
    HAS_GLOBAL_FINANCIAL = True
except Exception:
    HAS_GLOBAL_FINANCIAL = False
    GlobalFinancialFeed = None

try:
    from aureon.analytics.aureon_whale_behavior_predictor import WhaleBehaviorPredictor
    HAS_WHALE_BEHAVIOR = True
except Exception:
    HAS_WHALE_BEHAVIOR = False
    WhaleBehaviorPredictor = None

try:
    from aureon.bridges.aureon_kraken_unified_signal_bridge import KrakenUnifiedSignalBridge
    HAS_KRAKEN_SIGNAL_BRIDGE = True
except Exception:
    HAS_KRAKEN_SIGNAL_BRIDGE = False
    KrakenUnifiedSignalBridge = None

try:
    from aureon.intelligence.aureon_truth_prediction_engine import TruthPredictionEngine
    HAS_TRUTH_PREDICTION = True
except Exception:
    HAS_TRUTH_PREDICTION = False
    TruthPredictionEngine = None

try:
    from aureon.bridges.aureon_probability_nexus import EnhancedProbabilityNexus
    HAS_PROB_NEXUS = True
except Exception:
    HAS_PROB_NEXUS = False
    EnhancedProbabilityNexus = None

# ── TIER 2: Market Intelligence & Context ───────────────────────────────────
try:
    from aureon.intelligence.aureon_real_intelligence_engine import RealIntelligenceEngine
    HAS_REAL_INTEL = True
except Exception:
    HAS_REAL_INTEL = False
    RealIntelligenceEngine = None

try:
    from aureon.intelligence.aureon_market_organism import get_organism as get_market_organism
    HAS_MARKET_ORGANISM = True
except Exception:
    HAS_MARKET_ORGANISM = False
    get_market_organism = None

try:
    from aureon.intelligence.aureon_elephant_learning import ElephantMemory
    HAS_ELEPHANT = True
except Exception:
    HAS_ELEPHANT = False
    ElephantMemory = None

try:
    from aureon.intelligence.aureon_advanced_intelligence import MyceliumNetwork as AdvancedMycelium
    HAS_ADVANCED_INTEL = True
except Exception:
    HAS_ADVANCED_INTEL = False
    AdvancedMycelium = None

try:
    from aureon.intelligence.aureon_multiversal_reality_detector import get_reality_detector
    HAS_REALITY_DETECTOR = True
except Exception:
    HAS_REALITY_DETECTOR = False
    get_reality_detector = None

try:
    from aureon.scanners.aureon_global_wave_scanner import GlobalWaveScanner
    HAS_GLOBAL_WAVE = True
except Exception:
    HAS_GLOBAL_WAVE = False
    GlobalWaveScanner = None

try:
    from aureon.scanners.aureon_obsidian_filter import AureonObsidianFilter
    HAS_OBSIDIAN_FILTER = True
except Exception:
    HAS_OBSIDIAN_FILTER = False
    AureonObsidianFilter = None

# ── TIER 3: Harmonic, Resonance & Correlation ──────────────────────────────
try:
    from aureon.harmonic.aureon_schumann_resonance_bridge import get_schumann_bridge
    HAS_SCHUMANN = True
except Exception:
    HAS_SCHUMANN = False
    get_schumann_bridge = None

try:
    from aureon.harmonic.harmonic_nexus_bridge import HarmonicNexusBridge
    HAS_HARMONIC_NEXUS = True
except Exception:
    HAS_HARMONIC_NEXUS = False
    HarmonicNexusBridge = None

try:
    from aureon.data_feeds.earth_resonance_engine import EarthResonanceEngine, get_earth_engine
    HAS_EARTH_RESONANCE = True
except Exception:
    HAS_EARTH_RESONANCE = False
    EarthResonanceEngine = None
    get_earth_engine = None

try:
    from aureon.data_feeds.market_harp import MarketHarp
    HAS_MARKET_HARP = True
except Exception:
    HAS_MARKET_HARP = False
    MarketHarp = None

try:
    from aureon.data_feeds.crypto_market_map import CryptoMarketMap
    HAS_CRYPTO_MAP = True
except Exception:
    HAS_CRYPTO_MAP = False
    CryptoMarketMap = None

try:
    from aureon.intelligence.aureon_sensory_framework import SensoryRegistry
    HAS_SENSORY = True
except Exception:
    HAS_SENSORY = False
    SensoryRegistry = None

# ── TIER 4: Core Infrastructure ────────────────────────────────────────────
try:
    from aureon.core.aureon_chirp_bus import get_chirp_bus, ChirpBus
    HAS_CHIRP_BUS = True
except Exception:
    HAS_CHIRP_BUS = False
    get_chirp_bus = None
    ChirpBus = None

try:
    from aureon.core.mycelium_whale_sonar import WhaleSonar
    HAS_WHALE_SONAR = True
except Exception:
    HAS_WHALE_SONAR = False
    WhaleSonar = None

try:
    from aureon.core.aureon_hive_state import get_hive as get_hive_state
    HAS_HIVE_STATE = True
except Exception:
    HAS_HIVE_STATE = False
    get_hive_state = None

try:
    from aureon.intelligence.trading_hive_mind import TradingHiveMind
    HAS_TRADING_HIVE_MIND = True
except Exception:
    HAS_TRADING_HIVE_MIND = False
    TradingHiveMind = None

try:
    from aureon.intelligence.aureon_inception_engine import InceptionEngine
    HAS_INCEPTION = True
except Exception:
    HAS_INCEPTION = False
    InceptionEngine = None

try:
    import websocket as _ws_lib
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False

try:
    import numpy as np # type: ignore
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("margin_army")


class _LocalDashboardHandler(BaseHTTPRequestHandler):
    """Minimal local telemetry API for the React dashboard."""

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        server = getattr(self, "server", None)
        trader = getattr(server, "trader_ref", None)
        if not trader:
            self._send_json(503, {"ok": False, "error": "trader unavailable"})
            return

        if self.path.startswith("/health"):
            self._send_json(200, {"ok": True, "service": "kraken-margin-dashboard"})
            return

        if self.path.startswith("/api/terminal-state"):
            self._send_json(200, trader.get_local_dashboard_state())
            return

        self._send_json(404, {"ok": False, "error": "not found"})

    def log_message(self, format: str, *args) -> None:
        return

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

# ==============================================================
#  CONFIGURATION - ARMY DISCIPLINE
# ==============================================================
PROFIT_TARGET_USD = 1.27      # GBP1 approx USD1.27 - minimum net profit to close
MIN_PROFIT_USD = 1.27         # Same - the gate
MONITOR_INTERVAL = 2          # Seconds between FREE API price checks
ENTRY_SCAN_INTERVAL = 30      # Seconds between scanning for new entry
STREAM_STALE_MS = 12000       # Force-refresh stream if no messages for this long
LIQUIDATION_WARN = 150        # Margin level % warning
LIQUIDATION_FORCE = 110       # Margin level % force-close (Kraken liquidates at ~40%)
MARGIN_WAVE_ENTRY_PCT = 250.0 # Minimum PROJECTED margin % before entering any position
                              # Gives ~28% wave cushion at 5x, ~47% at 3x, ~14% at 10x
MIN_TRADE_USD = 25.0          # Minimum trade notional (fee gate)
KRAKEN_TAKER_FEE = 0.004      # 0.40% per side CONSERVATIVE (actual: opens ~0.376%, closes ~0.35%)
KRAKEN_OPEN_FEE = 0.00376     # Actual observed opening fee rate
KRAKEN_CLOSE_FEE = 0.0035     # Actual observed closing fee rate
KRAKEN_ROLLOVER_RATE = 0.0001 # 0.01% per 4 hours (Kraken margin rollover)
KRAKEN_ROLLOVER_INTERVAL = 4 * 3600  # 4 hours in seconds
MARGIN_BUFFER = 0.70          # Use 70% of free margin (30% safety for margin level)
KRAKEN_FAST_PROFIT_CAPTURE_ENABLED = os.getenv("KRAKEN_FAST_PROFIT_CAPTURE_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
KRAKEN_FAST_PROFIT_MIN_USD = max(0.0, float(os.getenv("KRAKEN_FAST_PROFIT_MIN_USD", "0.01")))
KRAKEN_FAST_PROFIT_MIN_HOLD_SECS = max(0.0, float(os.getenv("KRAKEN_FAST_PROFIT_MIN_HOLD_SECS", "1.0")))
KRAKEN_FAST_PROFIT_COLLATERAL_WARN_PCT = max(
    float(LIQUIDATION_FORCE),
    float(os.getenv("KRAKEN_FAST_PROFIT_COLLATERAL_WARN_PCT", str(LIQUIDATION_WARN))),
)
KRAKEN_MARGIN_CAPITAL_CACHE_TTL_SEC = max(3.0, float(os.getenv("KRAKEN_MARGIN_CAPITAL_CACHE_TTL_SEC", "20.0")))
KRAKEN_SPOT_BALANCE_CACHE_TTL_SEC = max(5.0, float(os.getenv("KRAKEN_SPOT_BALANCE_CACHE_TTL_SEC", "30.0")))
KRAKEN_TRUTH_CHECK_INTERVAL_SEC = max(30.0, float(os.getenv("KRAKEN_TRUTH_CHECK_INTERVAL_SEC", "120.0")))
PROVIDER_RECEIPT_MAX_AGE_SEC = 300.0
PROVIDER_ACCOUNT_RECEIPT_MAX_AGE_SEC = 30.0
DYNAMIC_MIN_NOTIONAL_USD = float(os.getenv("KRAKEN_DYNAMIC_MIN_NOTIONAL_USD", "5.0"))
DYNAMIC_MIN_PROFIT_USD = float(os.getenv("KRAKEN_DYNAMIC_MIN_PROFIT_USD", "0.05"))
DYNAMIC_TARGET_EQUITY_FRACTION = float(os.getenv("KRAKEN_DYNAMIC_TARGET_EQUITY_FRACTION", "0.01"))
TINY_ACCOUNT_EQUITY_USD = float(os.getenv("KRAKEN_TINY_ACCOUNT_EQUITY_USD", "50.0"))
TINY_ACCOUNT_MARGIN_BUFFER = float(os.getenv("KRAKEN_TINY_ACCOUNT_MARGIN_BUFFER", "0.90"))
STATE_FILE = "kraken_margin_army_state.json"
RESULTS_FILE = "kraken_margin_army_results.json"
USD_QUOTES = {"USD", "ZUSD"}

# ==============================================================
#  ENTRY GOAL — maximize profit in the quickest time
#  Applied ONLY at buy/entry selection. Never affects exit.
# ==============================================================
GOAL_TARGET_USD       = 1.27   # Profit we're hunting per trade (same as PROFIT_TARGET_USD)
GOAL_MAX_ETA_MINUTES  = 15.0   # Ideal: reach profit within this many minutes
# How goal scoring works:
#   profit_velocity = (|momentum| * leverage) / required_move_pct
#     — a dimensionless ratio: momentum-amplified-by-leverage vs. the move needed to profit
#     — higher = asset is already moving fast enough (relative to target) to close quickly
#   goal_score = capped and scaled profit_velocity, weighted 2x in total_score
#   Result: the entry selector prefers signals where leverage × momentum covers the
#   required move fastest — picking the most profitable signal in the least time.

# Binance public API - FREE, no auth needed
BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"
BINANCE_24H_URL = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_DEPTH_URL = "https://api.binance.com/api/v3/depth"
BINANCE_TRADES_URL = "https://api.binance.com/api/v3/trades"
BINANCE_AGG_TRADES_URL = "https://api.binance.com/api/v3/aggTrades"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
DASHBOARD_LIVE_FEED_USER_ID = os.getenv("AUREON_LIVE_FEED_USER_ID", "69e5567f-7ad1-42af-860f-3709ef1f5935")
DASHBOARD_SYNC_INTERVAL_SEC = 10
LOCAL_DASHBOARD_HOST = os.getenv("AUREON_LOCAL_DASHBOARD_HOST", "127.0.0.1")
LOCAL_DASHBOARD_PORT = int(os.getenv("AUREON_LOCAL_DASHBOARD_PORT", "8787"))

# Kraken public REST (no auth) - order book on our actual trading exchange
KRAKEN_DEPTH_URL = "https://api.kraken.com/0/public/Depth"

# === WAR INTELLIGENCE THRESHOLDS ===
WHALE_WALL_USD = 50000        # $50K+ wall = whale detected
WHALE_WALL_BLOCK_RATIO = 3.0  # Wall must be 3x average level size
BOT_PATTERN_THRESHOLD = 5     # 5+ same-size trades = bot detected
MOMENTUM_ALIGNMENT_MIN = 2    # At least 2 of 3 timeframes must agree
FLEE_MOMENTUM_REVERSAL = -0.3 # % reversal per minute = danger
FLEE_SPREAD_BLOWOUT = 0.5     # Spread > 0.5% = liquidity pulled
FLEE_VOLUME_SPIKE = 5.0       # 5x normal volume = whale dump/pump
INTEL_CACHE_SECONDS = 30      # How long intel stays fresh
# Fake volume detection thresholds
FAKE_VOL_VELOCITY_MIN = 0.5   # trades/sec below this vs high 24h vol = suspicious
FAKE_VOL_BOOK_AGREE_MIN = 0.4 # book imbalance ratio (Binance vs Kraken) must agree within 40%
SPREAD_DIVERGE_MAX = 0.5      # Binance/Kraken spread diff > 0.5% = manipulation signal

# === WAVEFORM ANALYSIS THRESHOLDS ===
WAVE_FFT_WINDOW = 256         # FFT window size (power of 2)
WAVE_STFT_HOP = 32            # STFT hop size
WAVE_BOT_CONFIDENCE = 0.6     # Min confidence to flag bot waveform
WAVE_PREDICTION_HORIZON = 60  # Predict next 60 seconds
WAVE_HARMONIC_BANDS = {
    'accumulator': (0.001, 0.01),   # Very slow: whales accumulating over minutes
    'market_maker': (0.01, 0.5),    # Mid: market makers cycling every 2-100s
    'scalper': (0.5, 5.0),          # Fast: scalper bots every 0.2-2s
    'hft': (5.0, 100.0),            # Ultra fast: HFT sub-second
}
WAVE_DANGER_POWER_SHIFT = 2.0  # 2x power shift in opposing band = danger

# Kraken base asset name cleanup (internal -> standard)
KRAKEN_BASE_MAP = {
    "XXBT": "BTC", "XBT": "BTC", "XETH": "ETH", "XLTC": "LTC",
    "XXRP": "XRP", "XDOGE": "DOGE", "XXLM": "XLM", "XZEC": "ZEC",
    "XREP": "REP", "XMLN": "MLN", "XXMR": "XMR", "XETC": "ETC",
    "ZUSD": "USD", "ZEUR": "EUR", "ZGBP": "GBP", "ZJPY": "JPY",
}

# ==============================================================
#  BINANCE LIVE STREAM - FREE WebSocket (sub-second reaction)
# ==============================================================
# Streams: @trade (every trade in real-time) + @depth@100ms (orderbook)
# ZERO API calls. ZERO rate limits. 100% FREE. No auth.
# This replaces 2-second REST polling with sub-100ms live data.
# ==============================================================

BINANCE_WS_URL = "wss://stream.binance.com:9443/stream?streams="

class LiveStream:
    """
    Binance FREE WebSocket stream — sub-second market data.
    Runs in a daemon thread. The army trader reads from cache.
    
    Streams per symbol:
      @trade      — every trade: price, qty, buyer_maker
      @depth@100ms — orderbook changes every 100ms
    
    Cache (thread-safe reads via GIL):
      .price[symbol]        — latest trade price
      .trade_time[symbol]   — timestamp of last trade
      .buy_pressure[symbol] — rolling buy volume (last 5s)
      .sell_pressure[symbol]— rolling sell volume (last 5s)
      .bid_wall[symbol]     — biggest bid within 0.5%
      .ask_wall[symbol]     — biggest ask within 0.5%
      .spread[symbol]       — current spread %
      .trade_velocity[sym]  — trades per second (last 5s)
      .last_trades[symbol]  — deque of last 200 trades (price, qty, is_buy, ts)
      .flash_alert[symbol]  — True if price moved >0.3% in <2s
    """

    def __init__(self):
        self._ws = None
        self._thread = None
        self._running = False
        self._symbols = set()
        self._lock = threading.Lock()
        self._pending_reconnect = False
        self._last_error = ""
        self._last_close_code = None
        self._last_close_msg = ""
        
        # === LIVE CACHE (read by monitoring loop) ===
        self.price: Dict[str, float] = {}
        self.trade_time: Dict[str, float] = {}
        self.buy_pressure: Dict[str, float] = {}
        self.sell_pressure: Dict[str, float] = {}
        self.best_bid: Dict[str, float] = {}
        self.best_ask: Dict[str, float] = {}
        self.bid_wall: Dict[str, float] = {}
        self.ask_wall: Dict[str, float] = {}
        self.spread: Dict[str, float] = {}
        self.trade_velocity: Dict[str, float] = {}
        self.last_trades: Dict[str, deque] = {}
        self.flash_alert: Dict[str, bool] = {}
        self.orderbook: Dict[str, dict] = {}  # {bids: [...], asks: [...]}
        
        # Rolling windows for pressure calculation
        self._trade_buf: Dict[str, deque] = {}  # (ts, qty, is_buy) last 5s
        self._price_buf: Dict[str, deque] = {}  # (ts, price) for flash detection
        
        # Stats
        self.connected = False
        self.msg_count = 0
        self.connect_time = 0.0
        self._reconnect_count = 0
        self._last_msg_time = 0.0

    def start(self, symbols: List[str]):
        """Start streaming for given Binance symbols (e.g. ['ETHUSDT', 'BTCUSDT'])."""
        if not HAS_WEBSOCKET:
            logger.warning("LIVE STREAM: websocket-client not installed — falling back to REST polling")
            return False

        self._symbols = set(s.upper() for s in symbols)
        if not self._symbols:
            return False

        if self._thread and self._thread.is_alive():
            self._request_reconnect("watchlist refresh")
            return True

        self._running = True
        self._thread = threading.Thread(
            target=self._run_forever,
            daemon=True,
            name="LiveStream"
        )
        self._thread.start()
        logger.info(f"LIVE STREAM: Connecting to {len(self._symbols)} symbols ({len(self._symbols) * 2} streams)...")
        return True

    def add_symbol(self, symbol: str):
        """Dynamically subscribe to a new symbol (reconnects)."""
        symbol = symbol.upper()
        self.sync_symbols(list(self._symbols | {symbol}))

    def sync_symbols(self, symbols: List[str]):
        """Replace the watched symbol set and reconnect once if it changed."""
        new_symbols = set(s.upper() for s in symbols if s)
        if not new_symbols:
            return
        if new_symbols == self._symbols:
            return
        self._symbols = new_symbols
        if self._thread and self._thread.is_alive():
            self._request_reconnect("watchlist sync")
        else:
            self.start(list(self._symbols))

    def stop(self):
        """Stop the stream."""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass

    def get_live_price(self, symbol: str) -> float:
        """Get latest price from stream (0 if not available)."""
        return self.price.get(symbol.upper(), 0.0)

    def get_executable_price(self, symbol: str, side: str | None = None) -> float:
        """
        Return a side-aware executable price from bookTicker when available.

        For a long we should assume exit at the bid.
        For a short we should assume exit at the ask.
        Falls back to last trade when the order book is not populated yet.
        """
        sym = symbol.upper()
        if side == "buy":
            px = self.best_bid.get(sym, 0.0)
            if px > 0:
                return px
        elif side == "sell":
            px = self.best_ask.get(sym, 0.0)
            if px > 0:
                return px
        return self.price.get(sym, 0.0)

    def get_flow_snapshot(self, symbol: str) -> dict:
        """Get current flow analysis from live stream data."""
        sym = symbol.upper()
        bp = self.buy_pressure.get(sym, 0)
        sp = self.sell_pressure.get(sym, 0)
        total = bp + sp
        buy_pct = (bp / total * 100) if total > 0 else 50
        
        return {
            'price': self.price.get(sym, 0),
            'best_bid': self.best_bid.get(sym, 0),
            'best_ask': self.best_ask.get(sym, 0),
            'buy_pressure': bp,
            'sell_pressure': sp,
            'buy_pct': buy_pct,
            'sell_pct': 100 - buy_pct,
            'flow_direction': 'buying' if buy_pct > 55 else ('selling' if buy_pct < 45 else 'neutral'),
            'trade_velocity': self.trade_velocity.get(sym, 0),
            'spread_pct': self.spread.get(sym, 0),
            'bid_wall': self.bid_wall.get(sym, 0),
            'ask_wall': self.ask_wall.get(sym, 0),
            'flash_alert': self.flash_alert.get(sym, False),
            'age_ms': int((time.time() - self.trade_time.get(sym, 0)) * 1000) if sym in self.trade_time else -1,
            'connected': self.connected,
            'msg_count': self.msg_count,
        }

    def is_alive(self) -> bool:
        """Check if stream is healthy (received data in last 10s)."""
        if not self.connected:
            return False
        return (time.time() - self._last_msg_time) < 10

    # ---------- INTERNAL ----------

    def _build_url(self) -> str:
        """Build WebSocket URL from current symbol set."""
        streams = []
        for sym in self._symbols:
            sl = sym.lower()
            streams.append(f"{sl}@trade")
            streams.append(f"{sl}@bookTicker")
        return BINANCE_WS_URL + "/".join(streams)

    def _request_reconnect(self, reason: str):
        """Close the socket once so the run loop reconnects with the latest watchlist."""
        self._pending_reconnect = True
        self._last_error = reason
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass

    def _run_forever(self):
        """WebSocket run loop with auto-reconnect."""
        while self._running:
            # Rebuild URL each iteration to pick up newly added symbols
            current_url = self._build_url()
            try:
                self._ws = _ws_lib.WebSocketApp(
                    current_url,
                    on_message=self._on_message,
                    on_open=self._on_open,
                    on_close=self._on_close,
                    on_error=self._on_error,
                )
                self._ws.run_forever(
                    ping_interval=30,
                    ping_timeout=15,
                )
            except Exception as e:
                logger.warning(f"LIVE STREAM: Connection error: {e}")

            if self._running:
                self._reconnect_count += 1
                wait = 1 if self._pending_reconnect else min(2 * self._reconnect_count, 10)
                if self._pending_reconnect:
                    logger.info("LIVE STREAM: Refreshing subscriptions with latest watchlist...")
                else:
                    logger.info(f"LIVE STREAM: Reconnecting in {wait}s (attempt #{self._reconnect_count})...")
                self.connected = False
                self._pending_reconnect = False
                time.sleep(wait)

    def _on_open(self, ws):
        self.connected = True
        self.connect_time = time.time()
        self._reconnect_count = 0
        self._last_error = ""
        logger.info(f"LIVE STREAM: CONNECTED — {len(self._symbols)} symbols streaming in real-time")

    def _on_close(self, ws, close_code, close_msg):
        self.connected = False
        self._last_close_code = close_code
        self._last_close_msg = str(close_msg or "")
        logger.info(f"LIVE STREAM: Disconnected (code={close_code}) {self._last_close_msg}".rstrip())

    def _on_error(self, ws, error):
        self._last_error = str(error)
        logger.warning(f"LIVE STREAM: Error: {error}")

    def _on_message(self, ws, raw_msg):
        """Process incoming WebSocket message — sub-millisecond path."""
        try:
            msg = json.loads(raw_msg)
            self.msg_count += 1
            self._last_msg_time = time.time()
            
            # Combined stream format: {"stream": "ethusdt@trade", "data": {...}}
            stream = msg.get("stream", "")
            data = msg.get("data", msg)
            
            if "@trade" in stream and "@bookTicker" not in stream:
                self._handle_trade(data)
            elif "@bookTicker" in stream:
                self._handle_book_ticker(data)
        except Exception:
            pass  # Never crash the stream thread

    def _handle_trade(self, data: dict):
        """Process a single trade — update price + flow."""
        sym = data.get("s", "").upper()
        if not sym:
            return
        
        price = float(data.get("p", 0))
        qty = float(data.get("q", 0))
        is_buyer_maker = data.get("m", False)  # True = seller aggressor (sell), False = buyer aggressor (buy)
        is_buy = not is_buyer_maker
        ts = time.time()
        
        # Update latest price
        self.price[sym] = price
        self.trade_time[sym] = ts
        
        # Store trade
        if sym not in self.last_trades:
            self.last_trades[sym] = deque(maxlen=200)
        self.last_trades[sym].append((price, qty, is_buy, ts))
        
        # Rolling trade buffer (5s window for pressure)
        if sym not in self._trade_buf:
            self._trade_buf[sym] = deque(maxlen=2000)
        self._trade_buf[sym].append((ts, qty * price, is_buy))  # USD volume
        
        # Recalculate pressure (purge >5s old)
        cutoff = ts - 5.0
        buf = self._trade_buf[sym]
        while buf and buf[0][0] < cutoff:
            buf.popleft()
        
        bp = sum(v for _, v, b in buf if b)
        sp = sum(v for _, v, b in buf if not b)
        self.buy_pressure[sym] = bp
        self.sell_pressure[sym] = sp
        
        # Trade velocity (trades per second over 5s)
        self.trade_velocity[sym] = len(buf) / 5.0
        
        # Flash detection: >0.3% move in <2s
        if sym not in self._price_buf:
            self._price_buf[sym] = deque(maxlen=100)
        self._price_buf[sym].append((ts, price))
        flash_cutoff = ts - 2.0
        pbuf = self._price_buf[sym]
        while len(pbuf) > 1 and pbuf[0][0] < flash_cutoff:
            pbuf.popleft()
        if len(pbuf) >= 2:
            oldest_price = pbuf[0][1]
            pct_move = abs(price - oldest_price) / oldest_price * 100
            self.flash_alert[sym] = pct_move > 0.3
        else:
            self.flash_alert[sym] = False

    def _handle_book_ticker(self, data: dict):
        """Process bookTicker — best bid/ask in real-time."""
        sym = data.get("s", "").upper()
        if not sym:
            return
        
        try:
            best_bid = float(data.get("b", 0))
            best_ask = float(data.get("a", 0))
            bid_qty = float(data.get("B", 0))
            ask_qty = float(data.get("A", 0))
            
            if best_bid > 0 and best_ask > 0:
                self.best_bid[sym] = best_bid
                self.best_ask[sym] = best_ask
                self.spread[sym] = (best_ask - best_bid) / best_bid * 100
                self.bid_wall[sym] = best_bid * bid_qty  # USD value of best bid
                self.ask_wall[sym] = best_ask * ask_qty  # USD value of best ask
        except (ValueError, ZeroDivisionError):
            pass


@dataclass
class MarginPairInfo:
    """Info about a margin-eligible trading pair."""
    pair: str
    internal: str
    base: str
    base_clean: str
    quote: str
    leverage_buy: list
    leverage_sell: list
    max_leverage: int
    ordermin: float
    costmin: float
    lot_decimals: int
    price_decimals: int
    binance_symbol: str = ""
    last_price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    spread_pct: float = 0.0
    volume_24h: float = 0.0
    momentum: float = 0.0


@dataclass
class ActiveTrade:
    """The ONE active margin trade."""
    pair: str
    side: str
    volume: float
    entry_price: float
    leverage: int
    entry_fee: float
    entry_time: float
    order_id: str
    cost: float = 0.0
    breakeven_price: float = 0.0
    binance_symbol: str = ""
    rollover_fees: float = 0.0
    last_rollover_check: float = 0.0
    profit_target_usd: float = 0.0
    cognition_plan: dict = field(default_factory=dict)
    entry_source_id: str = ""
    entry_source_timestamp: float = 0.0
    entry_fee_asset: str = ""
    entry_fill_receipt_complete: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass
class ShadowTrade:
    """
    Paper trade that validates a prediction BEFORE real capital is deployed.
    Uses live stream data — zero cost, zero risk.
    The system watches the shadow play out and only goes LIVE when
    it proves the prediction was correct.
    """
    pair: str
    side: str               # 'buy' or 'sell'
    binance_symbol: str
    entry_price: float      # Price when shadow opened
    created_at: float       # time.time()
    target_move_pct: float  # How much we need the price to move (fee + profit)
    leverage: int
    volume: float
    trade_val: float
    pair_info_key: str      # Key into margin_pairs dict
    profit_target_usd: float = 0.0
    cognition_context: dict = field(default_factory=dict)
    # Tracking
    best_price: float = 0.0   # Best price seen (highest for buy, lowest for sell)
    worst_price: float = 0.0  # Worst price seen
    current_price: float = 0.0
    validated: bool = False    # True when shadow proved profitable
    validation_time: float = 0.0
    peak_pnl_pct: float = 0.0 # Peak % move in our favour

    def update(self, price: float):
        """Update shadow with latest price."""
        self.current_price = price
        if self.side == "buy":
            if price > self.best_price or self.best_price == 0:
                self.best_price = price
            if price < self.worst_price or self.worst_price == 0:
                self.worst_price = price
            move_pct = (price - self.entry_price) / self.entry_price * 100
        else:
            if price < self.best_price or self.best_price == 0:
                self.best_price = price
            if price > self.worst_price or self.worst_price == 0:
                self.worst_price = price
            move_pct = (self.entry_price - price) / self.entry_price * 100

        if move_pct > self.peak_pnl_pct:
            self.peak_pnl_pct = move_pct

        # Shadow is VALIDATED when price moved enough to cover fees + profit
        if move_pct >= self.target_move_pct * 0.5:
            # Price moved at least 50% of what we need — direction is CONFIRMED
            if not self.validated:
                self.validated = True
                self.validation_time = time.time()

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    @property
    def current_move_pct(self) -> float:
        if self.entry_price <= 0:
            return 0
        if self.side == "buy":
            return (self.current_price - self.entry_price) / self.entry_price * 100
        else:
            return (self.entry_price - self.current_price) / self.entry_price * 100


# ==============================================================
#  FREE PRICE MONITORING - NO KRAKEN API
# ==============================================================
class FreeMarketData:
    """
    Get prices from Binance public API.
    ZERO cost. ZERO auth. ZERO rate limit worries.
    """

    def __init__(self):
        self._binance_prices: Dict[str, float] = {}
        self._binance_24h: Dict[str, dict] = {}
        self._last_fetch = 0
        self._last_24h_fetch = 0

    def fetch_all_binance_prices(self) -> Dict[str, float]:
        """Fetch ALL Binance prices in ONE call."""
        try:
            req = urllib.request.Request(BINANCE_TICKER_URL)
            req.add_header("User-Agent", "AureonTrader/1.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            prices = {}
            for item in data:
                sym = item.get("symbol", "")
                price = float(item.get("price", 0))
                if price > 0:
                    prices[sym] = price
            self._binance_prices = prices
            self._last_fetch = time.time()
            return prices
        except Exception as e:
            logger.warning(f"Binance price fetch failed: {e}")
            return self._binance_prices

    def fetch_binance_24h(self) -> Dict[str, dict]:
        """Fetch 24h stats from Binance (momentum, volume). ONE call."""
        try:
            req = urllib.request.Request(BINANCE_24H_URL)
            req.add_header("User-Agent", "AureonTrader/1.0")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            stats = {}
            for item in data:
                sym = item.get("symbol", "")
                stats[sym] = {
                    "price_change_pct": float(item.get("priceChangePercent", 0)),
                    "volume": float(item.get("quoteVolume", 0)),
                    "high": float(item.get("highPrice", 0)),
                    "low": float(item.get("lowPrice", 0)),
                    "bid": float(item.get("bidPrice", 0)),
                    "ask": float(item.get("askPrice", 0)),
                }
            self._binance_24h = stats
            self._last_24h_fetch = time.time()
            return stats
        except Exception as e:
            logger.warning(f"Binance 24h fetch failed: {e}")
            return self._binance_24h

    def get_price(self, binance_symbol: str) -> float:
        """Get cached price for a Binance symbol."""
        return self._binance_prices.get(binance_symbol, 0)

    def get_bid_ask(self, binance_symbol: str) -> Tuple[float, float]:
        """Get bid/ask from 24h data."""
        stats = self._binance_24h.get(binance_symbol, {})
        bid = stats.get("bid", 0)
        ask = stats.get("ask", 0)
        if bid <= 0 or ask <= 0:
            price = self.get_price(binance_symbol)
            return price, price
        return bid, ask

    def get_single_price(self, binance_symbol: str) -> float:
        """Get a FRESH single price from Binance for close decisions."""
        try:
            url = f"{BINANCE_TICKER_URL}?symbol={binance_symbol}"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "AureonTrader/1.0")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            price = float(data.get("price", 0))
            if price > 0:
                self._binance_prices[binance_symbol] = price
            return price
        except Exception as e:
            logger.debug(f"Single price fetch failed for {binance_symbol}: {e}")
            return self._binance_prices.get(binance_symbol, 0)


# ==============================================================
#  BATTLEFIELD INTELLIGENCE - FREE API WAR RESEARCH
# ==============================================================
class BattlefieldIntel:
    """
    War intelligence using 100% FREE Binance API.
    - Orderbook depth: Detect whale walls
    - Trade flow: Detect bot patterns & aggressor direction
    - Multi-timeframe momentum: Confirm direction across 1h/4h/1d
    - Volatility: Check if required move is achievable
    - Live danger detection: Flee triggers during monitoring
    """

    def __init__(self):
        self._depth_cache: Dict[str, dict] = {}
        self._trades_cache: Dict[str, list] = {}
        self._klines_cache: Dict[str, dict] = {}
        self._cache_times: Dict[str, float] = {}
        self._baseline_volume: Dict[str, float] = {}  # Normal per-minute volume
        self._last_prices: Dict[str, list] = {}  # Price history for momentum tracking
        self.waveform = None  # Initialized lazily after WaveformAnalyzer class defined

    def _fetch_json(self, url: str, timeout: int = 8) -> Any:
        """Fetch JSON from Binance FREE API."""
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "AureonWarIntel/1.0")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            logger.debug(f"Intel fetch failed: {url[:60]}... {e}")
            return None

    # ----------------------------------------------------------
    #  ORDERBOOK DEPTH ANALYSIS (Whale Wall Detection)
    # ----------------------------------------------------------
    def analyze_orderbook(self, symbol: str) -> dict:
        """
        Analyze orderbook depth. Detect whale walls.
        Returns: {
            'bid_walls': [(price, usd_size)],    # Large bid walls
            'ask_walls': [(price, usd_size)],    # Large ask walls
            'bid_depth_usd': float,               # Total bid depth in USD
            'ask_depth_usd': float,               # Total ask depth in USD
            'imbalance': float,                    # bid_depth/ask_depth ratio
            'whale_blocking_buy': bool,            # Whale wall above price (blocks our buy)
            'whale_supporting_buy': bool,          # Whale wall below price (supports our buy)
            'wall_distance_pct': float,            # Distance to nearest blocking wall
        }
        """
        cache_key = f"depth_{symbol}"
        if cache_key in self._cache_times and time.time() - self._cache_times[cache_key] < INTEL_CACHE_SECONDS:
            return self._depth_cache.get(symbol, {})

        url = f"{BINANCE_DEPTH_URL}?symbol={symbol}&limit=50"
        data = self._fetch_json(url)
        if not data:
            return {}

        bids = data.get("bids", [])
        asks = data.get("asks", [])

        result = {
            'bid_walls': [], 'ask_walls': [],
            'bid_depth_usd': 0, 'ask_depth_usd': 0,
            'imbalance': 1.0,
            'whale_blocking_buy': False, 'whale_supporting_buy': False,
            'whale_blocking_sell': False, 'whale_supporting_sell': False,
            'wall_distance_pct': 99.0,
            'best_bid': 0, 'best_ask': 0,
        }

        if not bids or not asks:
            return result

        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        mid_price = (best_bid + best_ask) / 2
        result['best_bid'] = best_bid
        result['best_ask'] = best_ask

        # Analyze bid side
        bid_sizes = []
        for price_s, qty_s in bids:
            price, qty = float(price_s), float(qty_s)
            usd = price * qty
            bid_sizes.append(usd)
            result['bid_depth_usd'] += usd
            if usd >= WHALE_WALL_USD:
                result['bid_walls'].append((price, usd))

        # Analyze ask side
        ask_sizes = []
        for price_s, qty_s in asks:
            price, qty = float(price_s), float(qty_s)
            usd = price * qty
            ask_sizes.append(usd)
            result['ask_depth_usd'] += usd
            if usd >= WHALE_WALL_USD:
                result['ask_walls'].append((price, usd))

        # Depth imbalance (>1 = more buying pressure)
        if result['ask_depth_usd'] > 0:
            result['imbalance'] = result['bid_depth_usd'] / result['ask_depth_usd']

        # Check for whale walls relative to average level
        avg_bid = sum(bid_sizes) / len(bid_sizes) if bid_sizes else 1
        avg_ask = sum(ask_sizes) / len(ask_sizes) if ask_sizes else 1

        # Whale blocking a BUY: Large ask wall within 2% above price
        for price_s, qty_s in asks[:20]:
            price, qty = float(price_s), float(qty_s)
            usd = price * qty
            dist_pct = (price - mid_price) / mid_price * 100
            if usd > avg_ask * WHALE_WALL_BLOCK_RATIO and usd >= WHALE_WALL_USD * 0.5 and dist_pct < 2.0:
                result['whale_blocking_buy'] = True
                result['wall_distance_pct'] = min(result['wall_distance_pct'], dist_pct)

        # Whale supporting a BUY: Large bid wall within 2% below price
        for price_s, qty_s in bids[:20]:
            price, qty = float(price_s), float(qty_s)
            usd = price * qty
            dist_pct = (mid_price - price) / mid_price * 100
            if usd > avg_bid * WHALE_WALL_BLOCK_RATIO and usd >= WHALE_WALL_USD * 0.5 and dist_pct < 2.0:
                result['whale_supporting_buy'] = True

        # Whale blocking a SELL (large bid wall = hard to sell through)
        for price_s, qty_s in bids[:20]:
            price, qty = float(price_s), float(qty_s)
            usd = price * qty
            dist_pct = (mid_price - price) / mid_price * 100
            if usd > avg_bid * WHALE_WALL_BLOCK_RATIO and usd >= WHALE_WALL_USD * 0.5 and dist_pct < 2.0:
                result['whale_blocking_sell'] = True

        self._depth_cache[symbol] = result
        self._cache_times[cache_key] = time.time()
        return result

    def analyze_kraken_orderbook(self, kraken_pair: str) -> dict:
        """
        Fetch Kraken's OWN order book for the pair we actually trade on.
        Compared against Binance depth to detect cross-exchange spoofing.
        Returns: {
            'bid_depth_usd': float, 'ask_depth_usd': float,
            'imbalance': float,     # bid/ask ratio (>1 = more bids)
            'best_bid': float, 'best_ask': float,
            'spread_pct': float,    # Kraken native spread %
            'available': bool,      # False if fetch failed
        }
        """
        default = {'bid_depth_usd': 0, 'ask_depth_usd': 0, 'imbalance': 1.0,
                   'best_bid': 0, 'best_ask': 0, 'spread_pct': 0, 'available': False}
        if not kraken_pair:
            return default
        try:
            url = f"{KRAKEN_DEPTH_URL}?pair={kraken_pair}&count=50"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "AureonWarIntel/1.0")
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            if data.get("error"):
                return default
            result_key = list(data.get("result", {}).keys())
            if not result_key:
                return default
            book = data["result"][result_key[0]]
            bids = book.get("bids", [])
            asks = book.get("asks", [])
            if not bids or not asks:
                return default
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid = (best_bid + best_ask) / 2
            bid_depth = sum(float(p) * float(q) for p, q, _ in bids[:25])
            ask_depth = sum(float(p) * float(q) for p, q, _ in asks[:25])
            imbalance = bid_depth / ask_depth if ask_depth > 0 else 1.0
            spread_pct = (best_ask - best_bid) / mid * 100 if mid > 0 else 0
            return {
                'bid_depth_usd': bid_depth,
                'ask_depth_usd': ask_depth,
                'imbalance': round(imbalance, 4),
                'best_bid': best_bid,
                'best_ask': best_ask,
                'spread_pct': round(spread_pct, 4),
                'available': True,
            }
        except Exception as e:
            logger.debug(f"Kraken depth fetch failed ({kraken_pair}): {e}")
            return default

    # ----------------------------------------------------------
    #  TRADE FLOW ANALYSIS (Bot Detection + Aggressor Side)
    # ----------------------------------------------------------
    def analyze_trade_flow(self, symbol: str) -> dict:
        """
        Analyze recent trades. Detect bots & institutional flow.
        Returns: {
            'bot_detected': bool,
            'bot_type': str,                # 'none', 'grid', 'iceberg', 'market_maker'
            'buy_volume_pct': float,         # % of volume that's aggressive buys
            'sell_volume_pct': float,        # % of volume that's aggressive sells
            'flow_direction': str,           # 'buying', 'selling', 'neutral'
            'flow_strength': float,          # 0-1 how strong the directional flow
            'avg_trade_usd': float,          # Average trade size
            'large_trade_pct': float,        # % of volume from large trades
            'trades_per_second': float,      # Activity rate
        }
        """
        cache_key = f"trades_{symbol}"
        if cache_key in self._cache_times and time.time() - self._cache_times[cache_key] < INTEL_CACHE_SECONDS:
            return self._trades_cache.get(symbol, {})

        url = f"{BINANCE_TRADES_URL}?symbol={symbol}&limit=500"
        data = self._fetch_json(url, timeout=10)
        if not data or len(data) < 10:
            return {'bot_detected': False, 'bot_type': 'none', 'flow_direction': 'neutral',
                    'flow_strength': 0, 'buy_volume_pct': 50, 'sell_volume_pct': 50,
                    'avg_trade_usd': 0, 'large_trade_pct': 0, 'trades_per_second': 0}

        buy_vol = 0
        sell_vol = 0
        trade_sizes = []
        total_usd = 0
        times = []

        for t in data:
            price = float(t.get("price", 0))
            qty = float(t.get("qty", 0))
            usd = price * qty
            is_buyer_maker = t.get("isBuyerMaker", False)
            ts = t.get("time", 0)

            trade_sizes.append(usd)
            total_usd += usd
            times.append(ts)

            if is_buyer_maker:
                sell_vol += usd   # Buyer is maker = seller is aggressor (taker sell)
            else:
                buy_vol += usd    # Buyer is taker = aggressive buy

        total = buy_vol + sell_vol
        buy_pct = (buy_vol / total * 100) if total > 0 else 50
        sell_pct = 100 - buy_pct

        # Flow direction
        if buy_pct > 60:
            direction = "buying"
            strength = min((buy_pct - 50) / 30, 1.0)
        elif sell_pct > 60:
            direction = "selling"
            strength = min((sell_pct - 50) / 30, 1.0)
        else:
            direction = "neutral"
            strength = 0

        # Average trade size
        avg_usd = total_usd / len(data) if data else 0

        # Large trades (>10x average)
        large_vol = sum(s for s in trade_sizes if s > avg_usd * 10)
        large_pct = (large_vol / total_usd * 100) if total_usd > 0 else 0

        # Trades per second
        if len(times) >= 2:
            time_span = (max(times) - min(times)) / 1000  # ms to seconds
            tps = len(data) / time_span if time_span > 0 else 0
        else:
            tps = 0

        # Store baseline volume for spike detection
        if symbol not in self._baseline_volume:
            self._baseline_volume[symbol] = tps
        else:
            self._baseline_volume[symbol] = self._baseline_volume[symbol] * 0.9 + tps * 0.1

        # BOT DETECTION: Look for patterns
        bot_detected = False
        bot_type = "none"

        # Pattern 1: Grid bot - identical trade sizes repeated
        size_counts: Dict[str, int] = {}
        for s in trade_sizes:
            key = f"{s:.2f}"
            size_counts[key] = size_counts.get(key, 0) + 1
        max_repeat = max(size_counts.values()) if size_counts else 0
        if max_repeat >= BOT_PATTERN_THRESHOLD:
            bot_detected = True
            bot_type = "grid"

        # Pattern 2: Iceberg - many same-size aggressive buys/sells in sequence
        consecutive_same = 0
        max_consecutive = 0
        last_size = None
        for t in data:
            qty = float(t.get("qty", 0))
            size_key = f"{qty:.6f}"
            if size_key == last_size:
                consecutive_same += 1
                max_consecutive = max(max_consecutive, consecutive_same)
            else:
                consecutive_same = 1
            last_size = size_key
        if max_consecutive >= 4:
            bot_detected = True
            bot_type = "iceberg"

        # Pattern 3: HFT - extremely high trade rate
        if tps > 10:  # >10 trades per second
            bot_detected = True
            bot_type = "hft" if bot_type == "none" else bot_type

        result = {
            'bot_detected': bot_detected,
            'bot_type': bot_type,
            'buy_volume_pct': buy_pct,
            'sell_volume_pct': sell_pct,
            'flow_direction': direction,
            'flow_strength': strength,
            'avg_trade_usd': avg_usd,
            'large_trade_pct': large_pct,
            'trades_per_second': tps,
        }
        self._trades_cache[symbol] = result
        self._cache_times[cache_key] = time.time()
        return result

    # ----------------------------------------------------------
    #  MULTI-TIMEFRAME MOMENTUM (Candlestick Alignment)
    # ----------------------------------------------------------
    def analyze_momentum(self, symbol: str) -> dict:
        """
        Check if momentum aligns across multiple timeframes.
        Uses Binance klines (free).
        Returns: {
            'aligned': bool,                 # All timeframes agree
            'alignment_count': int,           # How many agree (0-3)
            'direction': str,                # 'up', 'down', 'mixed'
            'tf_1h': float,                   # 1h momentum %
            'tf_4h': float,                   # 4h momentum %
            'tf_1d': float,                   # 1d momentum %
            'volatility_1h': float,           # 1h range as %
            'achievable': bool,               # Required move < recent volatility
        }
        """
        cache_key = f"klines_{symbol}"
        if cache_key in self._cache_times and time.time() - self._cache_times[cache_key] < 60:
            return self._klines_cache.get(symbol, {})

        result = {
            'aligned': False, 'alignment_count': 0, 'direction': 'mixed',
            'tf_1h': 0, 'tf_4h': 0, 'tf_1d': 0,
            'volatility_1h': 0, 'achievable': True,
        }

        timeframes = [
            ('1h', 3),   # Last 3 hours
            ('4h', 2),   # Last 8 hours
            ('1d', 2),   # Last 2 days
        ]
        directions = []

        for tf, limit in timeframes:
            url = f"{BINANCE_KLINES_URL}?symbol={symbol}&interval={tf}&limit={limit}"
            data = self._fetch_json(url)
            if not data or len(data) < 2:
                continue

            latest = data[-1]
            o, h, l, c = float(latest[1]), float(latest[2]), float(latest[3]), float(latest[4])
            change_pct = (c - o) / o * 100 if o > 0 else 0
            volatility = (h - l) / o * 100 if o > 0 else 0

            if tf == '1h':
                result['tf_1h'] = change_pct
                result['volatility_1h'] = volatility
            elif tf == '4h':
                result['tf_4h'] = change_pct
            elif tf == '1d':
                result['tf_1d'] = change_pct

            if change_pct > 0.05:
                directions.append('up')
            elif change_pct < -0.05:
                directions.append('down')
            else:
                directions.append('flat')

        # Check alignment
        up_count = directions.count('up')
        down_count = directions.count('down')

        if up_count >= MOMENTUM_ALIGNMENT_MIN:
            result['direction'] = 'up'
            result['alignment_count'] = up_count
            result['aligned'] = up_count == len(directions)
        elif down_count >= MOMENTUM_ALIGNMENT_MIN:
            result['direction'] = 'down'
            result['alignment_count'] = down_count
            result['aligned'] = down_count == len(directions)
        else:
            result['direction'] = 'mixed'
            result['alignment_count'] = max(up_count, down_count)

        self._klines_cache[symbol] = result
        self._cache_times[cache_key] = time.time()
        return result

    # ----------------------------------------------------------
    #  PRE-STRIKE RESEARCH (Full Assessment Before Entry)
    # ----------------------------------------------------------
    def pre_strike_research(self, symbol: str, side: str, required_move_pct: float,
                            kraken_pair: str = "") -> dict:
        """
        Full battlefield research before entering a position.
        Combines Binance + Kraken order book depth, trade flow, momentum,
        waveform, and cross-source volume validation into GO/NO-GO decision.

        Returns: {
            'verdict': str,        # 'GO', 'CAUTION', 'ABORT'
            'confidence': float,   # 0-1
            'reasons': [str],
            'intel': {orderbook, kraken_book, trade_flow, momentum}
        }
        """
        logger.info(f"INTEL: Running pre-strike research on {symbol} ({side.upper()})...")

        orderbook   = self.analyze_orderbook(symbol)         # Binance depth
        kraken_book = self.analyze_kraken_orderbook(kraken_pair)  # Kraken depth
        trade_flow  = self.analyze_trade_flow(symbol)
        momentum    = self.analyze_momentum(symbol)

        reasons = []
        score = 0
        max_score = 0

        # === ORDERBOOK CHECKS ===
        max_score += 3
        if side == "buy":
            if orderbook.get('whale_blocking_buy'):
                wall_dist = orderbook.get('wall_distance_pct', 99)
                if wall_dist < required_move_pct:
                    reasons.append(f"ABORT: Whale wall BLOCKING buy at {wall_dist:.2f}% (need {required_move_pct:.2f}%)")
                    score -= 2
                else:
                    reasons.append(f"WARN: Whale ask wall at {wall_dist:.2f}% but our target is {required_move_pct:.2f}%")
            if orderbook.get('whale_supporting_buy'):
                reasons.append("GOOD: Whale bid support below price")
                score += 2
            imb = orderbook.get('imbalance', 1.0)
            if imb > 1.3:
                reasons.append(f"GOOD: Orderbook favors buy (imbalance={imb:.2f})")
                score += 1
            elif imb < 0.7:
                reasons.append(f"BAD: Orderbook favors sell (imbalance={imb:.2f})")
                score -= 1
        else:  # sell
            if orderbook.get('whale_blocking_sell'):
                reasons.append("WARN: Whale bid wall may block sell")
                score -= 1
            imb = orderbook.get('imbalance', 1.0)
            if imb < 0.7:
                reasons.append(f"GOOD: Orderbook favors sell (imbalance={imb:.2f})")
                score += 1
            elif imb > 1.3:
                reasons.append(f"BAD: Orderbook favors buy, not sell (imbalance={imb:.2f})")
                score -= 1

        # === TRADE FLOW CHECKS ===
        max_score += 3
        flow = trade_flow.get('flow_direction', 'neutral')
        flow_str = trade_flow.get('flow_strength', 0)

        if side == "buy" and flow == "buying":
            reasons.append(f"GOOD: Aggressive buying flow (strength={flow_str:.2f}, {trade_flow['buy_volume_pct']:.0f}% buy)")
            score += 2
        elif side == "sell" and flow == "selling":
            reasons.append(f"GOOD: Aggressive selling flow (strength={flow_str:.2f}, {trade_flow['sell_volume_pct']:.0f}% sell)")
            score += 2
        elif (side == "buy" and flow == "selling") or (side == "sell" and flow == "buying"):
            reasons.append(f"BAD: Flow is AGAINST our {side} ({flow} detected)")
            score -= 2

        if trade_flow.get('bot_detected'):
            reasons.append(f"WARN: Bot detected ({trade_flow['bot_type']}) - market may be manipulated")
            score -= 1

        if trade_flow.get('large_trade_pct', 0) > 30:
            reasons.append(f"WARN: {trade_flow['large_trade_pct']:.0f}% volume from large trades (whale activity)")

        # === CROSS-SOURCE VOLUME & ORDER BOOK VALIDATION ===
        # Check all available sources to catch fake/wash-traded volume and spoofed books.
        max_score += 2
        velocity = trade_flow.get('trades_per_second', 0)
        avg_trade_usd = trade_flow.get('avg_trade_usd', 0)
        # Estimated 24h Binance USD volume from live trade rate
        binance_vol_proxy = velocity * avg_trade_usd * 86400

        # ── Kraken book cross-check ───────────────────────────────────────
        if kraken_book.get('available'):
            k_imb   = kraken_book.get('imbalance', 1.0)
            b_imb   = orderbook.get('imbalance', 1.0)
            k_sprd  = kraken_book.get('spread_pct', 0)
            b_sprd  = (orderbook.get('best_ask', 0) - orderbook.get('best_bid', 0)) / \
                      max(orderbook.get('best_bid', 1), 1) * 100

            # Both exchanges agree on book direction?
            k_bid_heavy = k_imb > 1.2
            b_bid_heavy = b_imb > 1.2
            k_ask_heavy = k_imb < 0.8
            b_ask_heavy = b_imb < 0.8
            books_agree = (k_bid_heavy == b_bid_heavy) or (k_ask_heavy == b_ask_heavy)

            if books_agree:
                reasons.append(
                    f"GOOD: Binance+Kraken books agree (Binance imb={b_imb:.2f}, Kraken imb={k_imb:.2f})")
                score += 1
            else:
                reasons.append(
                    f"WARN: Books DIVERGE — Binance imb={b_imb:.2f} vs Kraken imb={k_imb:.2f} (possible spoofing)")

            # Spread divergence between exchanges
            spread_diff = abs(k_sprd - b_sprd)
            if spread_diff > SPREAD_DIVERGE_MAX:
                reasons.append(
                    f"WARN: Spread divergence {spread_diff:.3f}% (Kraken={k_sprd:.3f}% Binance={b_sprd:.3f}%) "
                    f"— liquidity fragmented or manipulation")
                score -= 1
            else:
                reasons.append(
                    f"GOOD: Spread consistent across exchanges ({spread_diff:.3f}% diff)")
                score += 1
        else:
            reasons.append("INFO: Kraken depth unavailable — single-source book check only")

        # ── Volume authenticity check ─────────────────────────────────────
        # Low Binance trade velocity with a claimed high 24h volume = likely wash trading
        if velocity > 0 and binance_vol_proxy > 0:
            if velocity < FAKE_VOL_VELOCITY_MIN and avg_trade_usd < 200:
                reasons.append(
                    f"WARN: Very low trade velocity ({velocity:.2f}/s, avg ${avg_trade_usd:.0f}) "
                    f"— volume may be inflated/wash-traded")
                score -= 1
            elif velocity >= 2.0:
                reasons.append(
                    f"GOOD: Healthy trade velocity {velocity:.2f}/s confirms real volume activity")
                score += 1

        # === MOMENTUM CHECKS ===
        max_score += 3
        mom_dir = momentum.get('direction', 'mixed')
        alignment = momentum.get('alignment_count', 0)

        if (side == "buy" and mom_dir == "up") or (side == "sell" and mom_dir == "down"):
            reasons.append(f"GOOD: Momentum aligned {mom_dir} ({alignment}/3 timeframes)")
            score += alignment
        elif mom_dir == "mixed":
            reasons.append(f"NEUTRAL: Mixed momentum ({alignment}/3 aligned)")
        else:
            reasons.append(f"BAD: Momentum is {mom_dir} but we want to {side}")
            score -= 2

        # Check if volatility supports required move
        vol_1h = momentum.get('volatility_1h', 0)
        if vol_1h > 0 and required_move_pct > 0:
            if vol_1h >= required_move_pct:
                reasons.append(f"GOOD: 1h volatility {vol_1h:.2f}% covers {required_move_pct:.2f}% needed")
                score += 1
            else:
                reasons.append(f"WARN: 1h vol {vol_1h:.2f}% may not cover {required_move_pct:.2f}% needed")

        # === VERDICT ===
        _ = max(0, min(1, (score + max_score) / (2 * max_score)))

        if score >= 3:
            verdict = "GO"
        elif score >= 0:
            verdict = "CAUTION"
        else:
            verdict = "ABORT"

        # Hard ABORT conditions
        if side == "buy" and orderbook.get('whale_blocking_buy'):
            wall_dist = orderbook.get('wall_distance_pct', 99)
            if wall_dist < required_move_pct:
                verdict = "ABORT"
                _ = 0.1

        # === WAVEFORM ANALYSIS (See bot moves BEFORE they happen) ===
        waveform_result = {}
        if self.waveform and HAS_NUMPY:
            try:
                waveform_result = self.waveform.full_scan(symbol, side)
                if waveform_result.get('available'):
                    max_score += 3
                    dom = waveform_result.get('dominant_bot', 'organic')
                    shape = waveform_result.get('shape', 'unknown')
                    res_score = waveform_result.get('resonance_score', 0)
                    res_label = waveform_result.get('resonance_label', 'neutral')
                    flow_pred = waveform_result.get('flow_prediction', 'neutral')
                    energy = waveform_result.get('energy_trend', 0)

                    # Resonance check (bots moving WITH or AGAINST us)
                    if res_label == 'harmony':
                        reasons.append(f"WAVE GOOD: Bots in HARMONY (resonance={res_score:+.2f}, {dom})")
                        score += 2
                    elif res_label == 'dissonance':
                        reasons.append(f"WAVE BAD: Bots in DISSONANCE (resonance={res_score:+.2f}, {dom})")
                        score -= 2
                    else:
                        reasons.append(f"WAVE NEUTRAL: resonance={res_score:+.2f}, dominant={dom}")

                    # Shape/energy check
                    if shape == 'surge':
                        reasons.append(f"WAVE ALERT: Energy SURGING (trend={energy:+.2f}) - bots ramping up!")
                        if res_label == 'dissonance':
                            score -= 1  # Surge AGAINST us = very bad
                    elif shape == 'taper':
                        reasons.append(f"WAVE: Bot activity tapering (trend={energy:+.2f})")

                    # Flow prediction from waveform
                    if side == 'buy' and flow_pred == 'strong_sell_building':
                        reasons.append("WAVE DANGER: Strong sell flow building in waveform")
                        score -= 1
                    elif side == 'sell' and flow_pred == 'strong_buy_building':
                        reasons.append("WAVE DANGER: Strong buy flow building in waveform")
                        score -= 1
                    elif (side == 'buy' and flow_pred == 'strong_buy_building') or \
                         (side == 'sell' and flow_pred == 'strong_sell_building'):
                        reasons.append(f"WAVE GOOD: {flow_pred} supports our {side}")
                        score += 1
                # Push wave context to Seer, Lyra, King via learning bridge
                if self.learning_bridge is not None and waveform_result.get('available'):
                    try:
                        self.learning_bridge.push_wave_context(waveform_result)
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"Waveform analysis failed: {e}")

        # === VERDICT (recalculate with waveform) ===
        confidence = max(0, min(1, (score + max_score) / (2 * max_score)))

        if score >= 3:
            verdict = "GO"
        elif score >= 0:
            verdict = "CAUTION"
        else:
            verdict = "ABORT"

        # Hard ABORT conditions
        if side == "buy" and orderbook.get('whale_blocking_buy'):
            wall_dist = orderbook.get('wall_distance_pct', 99)
            if wall_dist < required_move_pct:
                verdict = "ABORT"
                confidence = 0.1

        result = {
            'verdict': verdict,
            'confidence': confidence,
            'score': score,
            'max_score': max_score,
            'reasons': reasons,
            'intel': {
                'orderbook': orderbook,
                'kraken_book': kraken_book,
                'trade_flow': trade_flow,
                'momentum': momentum,
                'waveform': waveform_result,
            }
        }

        logger.info(f"INTEL VERDICT: {verdict} (confidence={confidence:.2f}, score={score}/{max_score})")
        for r in reasons:
            logger.info(f"  {r}")

        return result

    # ----------------------------------------------------------
    #  LIVE DANGER DETECTION (Flee Trigger During Monitoring)
    # ----------------------------------------------------------
    def check_danger(self, symbol: str, side: str, entry_price: float,
                     target_price: float) -> dict:
        """
        Quick danger check during position monitoring.
        Returns: {
            'flee': bool,           # Should we close immediately?
            'danger_level': int,    # 0=safe, 1=watch, 2=danger, 3=flee
            'reasons': [str],
        }
        """
        reasons = []
        danger = 0

        # Quick orderbook check
        orderbook = self.analyze_orderbook(symbol)
        trade_flow = self.analyze_trade_flow(symbol)

        # Check 1: Whale wall appeared between us and target
        if side == "buy" and orderbook.get('whale_blocking_buy'):
            ask_walls = orderbook.get('ask_walls', [])
            for wall_price, wall_usd in ask_walls:
                if entry_price < wall_price < target_price:
                    reasons.append(f"DANGER: ${wall_usd:,.0f} whale wall at ${wall_price:.4f} BLOCKING target")
                    danger += 2
                    break

        if side == "sell" and orderbook.get('whale_blocking_sell'):
            bid_walls = orderbook.get('bid_walls', [])
            for wall_price, wall_usd in bid_walls:
                if target_price < wall_price < entry_price:
                    reasons.append(f"DANGER: ${wall_usd:,.0f} whale wall at ${wall_price:.4f} BLOCKING target")
                    danger += 2
                    break

        # Check 2: Flow reversed hard against us
        flow = trade_flow.get('flow_direction', 'neutral')
        flow_str = trade_flow.get('flow_strength', 0)
        if side == "buy" and flow == "selling" and flow_str > 0.5:
            reasons.append(f"DANGER: Strong selling flow ({trade_flow['sell_volume_pct']:.0f}% sells)")
            danger += 1
        elif side == "sell" and flow == "buying" and flow_str > 0.5:
            reasons.append(f"DANGER: Strong buying flow ({trade_flow['buy_volume_pct']:.0f}% buys)")
            danger += 1

        # Check 3: Volume spike (whale dump/pump)
        tps = trade_flow.get('trades_per_second', 0)
        baseline = self._baseline_volume.get(symbol, tps)
        if baseline > 0 and tps > baseline * FLEE_VOLUME_SPIKE:
            reasons.append(f"DANGER: Volume spike {tps:.1f}/s vs normal {baseline:.1f}/s")
            danger += 1

        # Check 4: Spread blowout
        best_bid = orderbook.get('best_bid', 0)
        best_ask = orderbook.get('best_ask', 0)
        if best_bid > 0 and best_ask > 0:
            spread_pct = (best_ask - best_bid) / best_bid * 100
            if spread_pct > FLEE_SPREAD_BLOWOUT:
                reasons.append(f"DANGER: Spread blowout {spread_pct:.3f}% (normal <{FLEE_SPREAD_BLOWOUT}%)")
                danger += 1

        # Check 5: Depth imbalance flip
        imb = orderbook.get('imbalance', 1.0)
        if side == "buy" and imb < 0.5:
            reasons.append(f"DANGER: Depth strongly favors sellers (imb={imb:.2f})")
            danger += 1
        elif side == "sell" and imb > 2.0:
            reasons.append(f"DANGER: Depth strongly favors buyers (imb={imb:.2f})")
            danger += 1

        # Check 6: WAVEFORM ANALYSIS — see the bots' next move
        if self.waveform and HAS_NUMPY:
            try:
                wave = self.waveform.full_scan(symbol, side)
                if wave.get('available'):
                    res_score    = wave.get('resonance_score', 0)
                    res_label    = wave.get('resonance_label', 'neutral')
                    shape        = wave.get('shape', 'unknown')
                    flow_pred    = wave.get('flow_prediction', 'neutral')
                    energy_trend = wave.get('energy_trend', 0)
                    flow_vel     = wave.get('flow_velocity', 0)
                    shifted      = wave.get('spectrum_shifted', False)

                    # Strong dissonance = bots moving against us
                    if res_label == 'dissonance' and res_score < -0.4:
                        reasons.append(f"WAVE DANGER: Bot dissonance {res_score:+.2f} — moving AGAINST us")
                        danger += 1

                    # Energy surge + dissonance = imminent attack
                    if shape == 'surge' and res_label == 'dissonance':
                        reasons.append(f"WAVE CRITICAL: Surge + dissonance — bots attacking our direction!")
                        danger += 2

                    # Extreme energy surge (>1.5) with dissonance = all-out attack
                    if energy_trend > 1.5 and res_label == 'dissonance':
                        reasons.append(
                            f"WAVE CRITICAL: Extreme energy surge ({energy_trend:+.2f}) "
                            f"+ dissonance — full bot offensive against our position")
                        danger += 1

                    # Flow velocity building hard against our direction
                    if side == 'buy' and flow_vel < -0.5:
                        reasons.append(
                            f"WAVE DANGER: Sell momentum accelerating fast "
                            f"(flow_velocity={flow_vel:+.3f})")
                        danger += 1
                    elif side == 'sell' and flow_vel > 0.5:
                        reasons.append(
                            f"WAVE DANGER: Buy momentum accelerating fast "
                            f"(flow_velocity={flow_vel:+.3f})")
                        danger += 1

                    # Sell building when we're long (or vice versa)
                    if side == 'buy' and flow_pred == 'strong_sell_building':
                        reasons.append("WAVE DANGER: Strong sell flow building in waveform")
                        danger += 1
                    elif side == 'sell' and flow_pred == 'strong_buy_building':
                        reasons.append("WAVE DANGER: Strong buy flow building in waveform")
                        danger += 1

                    # Spectrum shift = bots changed strategy
                    if shifted:
                        reasons.append("WAVE ALERT: Spectrum shifted — bots changed strategy!")
                        danger += 1
            except Exception as e:
                logger.debug(f"Waveform danger check failed: {e}")

        flee = danger >= 3
        return {
            'flee': flee,
            'danger_level': min(danger, 3),
            'reasons': reasons,
        }


# ==============================================================
#  WAVEFORM ANALYZER - SEE THEIR MOVES BEFORE THEY MAKE THEM
# ==============================================================
class WaveformAnalyzer:
    """
    The harmonic pool — crypto is a living waveform.
    Bots leave frequency signatures they can't hide.
    FFT reveals their rhythm. STFT shows it evolving.
    We predict their next move before they even make it.

    Input: Raw Binance trades (FREE API, 1000 trades per call)
    Analysis:
      1. FFT Spectral Fingerprint: Volume resampled → frequency bands → bot classification
      2. STFT Price Spectrogram: Log returns → sliding FFT → shape classification
      3. Flow Momentum Waveform: Buy/sell aggressor pressure as wave → phase prediction
      4. Harmonic Resonance: Do bot frequencies align WITH or AGAINST our trade?
    """

    def __init__(self):
        if not HAS_NUMPY:
            logger.warning("numpy not available - WaveformAnalyzer disabled")
        self._trade_buffers: Dict[str, deque] = {}  # Raw trades per symbol
        self._spectral_cache: Dict[str, dict] = {}
        self._cache_times: Dict[str, float] = {}
        self._prev_spectrums: Dict[str, dict] = {}  # Previous spectrum for shift detection
        self._flow_waves: Dict[str, deque] = {}  # Buy/sell pressure wave per symbol

    def _fetch_trades(self, symbol: str) -> list:
        """Fetch 1000 recent trades from Binance (FREE)."""
        try:
            url = f"{BINANCE_AGG_TRADES_URL}?symbol={symbol}&limit=1000"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "AureonWaveform/1.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            # aggTrades: {a: id, p: price, q: qty, f: first_trade_id, l: last_trade_id, T: timestamp, m: is_buyer_maker}
            trades = []
            for t in data:
                trades.append({
                    'ts': t['T'] / 1000.0,  # ms -> seconds
                    'price': float(t['p']),
                    'qty': float(t['p']) * float(t['q']),  # USD volume
                    'qty_base': float(t['q']),
                    'is_sell': t['m'],  # isBuyerMaker = seller is aggressor
                })
            return trades
        except Exception as e:
            logger.debug(f"Waveform trade fetch failed for {symbol}: {e}")
            return []

    # ----------------------------------------------------------
    #  FFT SPECTRAL FINGERPRINT: What bots are in the pool?
    # ----------------------------------------------------------
    def _fft_spectral_fingerprint(self, trades: list) -> dict:
        """
        Resample trade volume onto uniform time grid.
        Run FFT. Extract power in each frequency band.
        Returns band powers + dominant frequencies + bot classification.
        """
        if not HAS_NUMPY or len(trades) < 50:
            return {}

        # Build time series: volume per time bucket
        ts_start = trades[0]['ts']
        ts_end = trades[-1]['ts']
        duration = ts_end - ts_start
        if duration < 5:  # Need at least 5 seconds of data
            return {}

        # Resample to uniform grid (100ms buckets for good resolution)
        bucket_size = 0.1  # 100ms
        n_buckets = int(duration / bucket_size) + 1
        n_buckets = min(n_buckets, 8192)  # Cap for performance

        # Three signals: total volume, buy volume, sell volume
        vol_signal = np.zeros(n_buckets)
        buy_signal = np.zeros(n_buckets)
        sell_signal = np.zeros(n_buckets)

        for t in trades:
            idx = int((t['ts'] - ts_start) / bucket_size)
            idx = min(idx, n_buckets - 1)
            vol_signal[idx] += t['qty']
            if t['is_sell']:
                sell_signal[idx] += t['qty']
            else:
                buy_signal[idx] += t['qty']

        # Remove DC component (mean)
        vol_centered = vol_signal - np.mean(vol_signal)
        buy_centered = buy_signal - np.mean(buy_signal)
        sell_centered = sell_signal - np.mean(sell_signal)

        # Apply Hanning window to reduce spectral leakage
        window = np.hanning(n_buckets)
        vol_windowed = vol_centered * window
        buy_windowed = buy_centered * window
        sell_windowed = sell_centered * window

        # FFT
        vol_fft = np.abs(np.fft.rfft(vol_windowed))
        buy_fft = np.abs(np.fft.rfft(buy_windowed))
        sell_fft = np.abs(np.fft.rfft(sell_windowed))
        freqs = np.fft.rfftfreq(n_buckets, d=bucket_size)

        # Extract power per harmonic band
        total_power = np.sum(vol_fft) + 1e-10
        bands = {}
        dominant_freq = 0
        dominant_power = 0

        for band_name, (f_lo, f_hi) in WAVE_HARMONIC_BANDS.items():
            mask = (freqs >= f_lo) & (freqs < f_hi)
            if not np.any(mask):
                bands[band_name] = {
                    'power': 0, 'power_pct': 0, 'dominant_freq': 0,
                    'buy_power': 0, 'sell_power': 0, 'buy_sell_ratio': 1.0,
                }
                continue

            band_power = np.sum(vol_fft[mask])
            band_buy = np.sum(buy_fft[mask])
            band_sell = np.sum(sell_fft[mask])

            # Find peak frequency in this band
            band_freqs = freqs[mask]
            band_mags = vol_fft[mask]
            peak_idx = np.argmax(band_mags)
            peak_freq = band_freqs[peak_idx]
            peak_power = band_mags[peak_idx]

            if peak_power > dominant_power:
                dominant_power = peak_power
                dominant_freq = peak_freq

            bands[band_name] = {
                'power': float(band_power),
                'power_pct': float(band_power / total_power * 100),
                'dominant_freq': float(peak_freq),
                'peak_amplitude': float(peak_power),
                'buy_power': float(band_buy),
                'sell_power': float(band_sell),
                'buy_sell_ratio': float(band_buy / (band_sell + 1e-10)),
            }

        # Classify the dominant bot type
        max_band = max(bands.items(), key=lambda x: x[1]['power_pct'])
        bot_class = max_band[0]
        bot_power = max_band[1]['power_pct']

        # Check if organic (no strong peaks, flat spectrum)
        if bot_power < 30:
            bot_class = 'organic'

        return {
            'bands': bands,
            'dominant_freq': float(dominant_freq),
            'dominant_band': bot_class,
            'dominant_power_pct': float(bot_power),
            'total_power': float(total_power),
            'duration_sec': duration,
            'n_trades': len(trades),
        }

    # ----------------------------------------------------------
    #  STFT SPECTROGRAM: How is the waveform EVOLVING?
    # ----------------------------------------------------------
    def _stft_spectrogram(self, trades: list) -> dict:
        """
        Short-time FFT on price log returns.
        Shows how bot activity is CHANGING over time.
        Reveals: are bots ramping up? Fading? Shifting frequency?
        """
        if not HAS_NUMPY or len(trades) < WAVE_FFT_WINDOW:
            return {}

        # Extract price series
        prices = np.array([t['price'] for t in trades])

        # Log returns (the actual signal)
        log_returns = np.diff(np.log(prices + 1e-12))
        if len(log_returns) < WAVE_FFT_WINDOW:
            return {}

        # STFT: sliding window FFT
        n_fft = min(WAVE_FFT_WINDOW, len(log_returns))
        hop = WAVE_STFT_HOP
        frames = []
        timestamps = []

        for start in range(0, len(log_returns) - n_fft + 1, hop):
            chunk = log_returns[start:start + n_fft]
            windowed = chunk * np.hanning(n_fft)
            fft_result = np.fft.rfft(windowed)
            frames.append(np.abs(fft_result))
            # Timestamp of this frame (midpoint)
            mid_idx = start + n_fft // 2
            if mid_idx < len(trades):
                timestamps.append(trades[mid_idx]['ts'])

        if not frames:
            return {}

        S = np.column_stack(frames)  # shape: (n_fft//2+1, n_frames)

        # Spectral features per frame
        freq_bins = np.arange(S.shape[0], dtype=float)
        mean_power = np.mean(S, axis=1) + 1e-12

        # Centroid: where is the "center of mass" of the spectrum?
        centroid = float(np.sum(freq_bins * mean_power) / np.sum(mean_power))

        # Bandwidth: how spread out is the spectrum?
        bandwidth = float(np.sqrt(np.sum(((freq_bins - centroid)**2) * mean_power) / np.sum(mean_power)))

        # Dominant peaks
        sorted_bins = np.argsort(mean_power)[::-1]
        peaks = [{'bin': int(b), 'power': float(mean_power[b])} for b in sorted_bins[:5]]

        # Flatness: geometric_mean / arithmetic_mean (1.0 = white noise, 0.0 = pure tone)
        geo_mean = np.exp(np.mean(np.log(mean_power + 1e-12)))
        arith_mean = np.mean(mean_power)
        flatness = float(geo_mean / (arith_mean + 1e-12))

        # Energy evolution: is the spectrum getting STRONGER or WEAKER over time?
        frame_energies = np.sum(S, axis=0)
        if len(frame_energies) >= 4:
            first_half = np.mean(frame_energies[:len(frame_energies)//2])
            second_half = np.mean(frame_energies[len(frame_energies)//2:])
            energy_trend = float((second_half - first_half) / (first_half + 1e-10))
        else:
            energy_trend = 0.0

        # Classify the spectrogram shape
        shape = self._classify_shape(centroid, bandwidth, flatness, peaks, energy_trend)

        return {
            'centroid': centroid,
            'bandwidth': bandwidth,
            'flatness': flatness,
            'peaks': peaks,
            'energy_trend': energy_trend,
            'shape': shape,
            'n_frames': len(frames),
        }

    def _classify_shape(self, centroid: float, bandwidth: float, flatness: float,
                        peaks: list, energy_trend: float) -> str:
        """
        Classify spectrogram shape — reveals bot strategy.
        - grid: Regular pattern (grid bots placing orders at intervals)
        - oscillator: Single dominant frequency (market maker bouncing)
        - spiral: Wide bandwidth, high centroid (chaotic algo)
        - taper: Energy fading (bot withdrawing from market)
        - surge: Energy increasing (bot ramping up — ALERT!)
        - organic: Flat spectrum, no dominant patterns (real humans)
        """
        # Energy change is the most critical signal
        if energy_trend > 0.5:
            return 'surge'  # Something is ramping up activity — WATCH CLOSELY
        if energy_trend < -0.3:
            return 'taper'  # Activity dying down

        # Multiple strong peaks = grid pattern
        if len(peaks) >= 2 and peaks[1]['power'] > 0.4 * peaks[0]['power'] and flatness < 0.5:
            return 'grid'

        # Single dominant peak = oscillator (market maker)
        if bandwidth < 2.0 and peaks[0]['power'] > 0.5 * sum(p['power'] for p in peaks):
            return 'oscillator'

        # Wide bandwidth + high centroid = chaotic high-freq algo
        if bandwidth > 4.0 and centroid > 3.0:
            return 'spiral'

        # Very flat = organic/noise
        if flatness > 0.8:
            return 'organic'

        return 'mixed'

    # ----------------------------------------------------------
    #  FLOW MOMENTUM WAVEFORM: Buy/Sell pressure as a wave
    # ----------------------------------------------------------
    def _flow_momentum_wave(self, trades: list) -> dict:
        """
        Build the buy/sell pressure wave over time.
        Phase analysis tells us: are buyers or sellers building momentum?
        Derivative tells us: is the momentum ACCELERATING or DECELERATING?
        This predicts the next price move direction.
        """
        if not HAS_NUMPY or len(trades) < 100:
            return {}

        # Build cumulative buy-sell pressure in 1-second buckets
        ts_start = trades[0]['ts']
        ts_end = trades[-1]['ts']
        duration = ts_end - ts_start
        if duration < 10:
            return {}

        n_buckets = min(int(duration), 600)  # 1-second buckets, max 10 min
        flow = np.zeros(n_buckets)

        for t in trades:
            idx = int(t['ts'] - ts_start)
            idx = min(idx, n_buckets - 1)
            if t['is_sell']:
                flow[idx] -= t['qty']
            else:
                flow[idx] += t['qty']

        # Cumulative flow (running sum)
        cum_flow = np.cumsum(flow)

        # Smooth with simple moving average (5-second window)
        kernel = np.ones(5) / 5
        if len(cum_flow) >= 5:
            smoothed = np.convolve(cum_flow, kernel, mode='valid')
        else:
            smoothed = cum_flow

        if len(smoothed) < 3:
            return {}

        # Current phase: last value of cumulative flow
        current_flow = float(cum_flow[-1])

        # Velocity: rate of change (first derivative)
        velocity = np.diff(smoothed)
        current_velocity = float(velocity[-1]) if len(velocity) > 0 else 0

        # Acceleration: rate of velocity change (second derivative)
        if len(velocity) >= 2:
            acceleration = np.diff(velocity)
            current_accel = float(acceleration[-1])
        else:
            current_accel = 0

        # Recent trend (last 20% of data)
        recent_start = max(0, len(smoothed) - len(smoothed) // 5)
        recent = smoothed[recent_start:]
        if len(recent) >= 2:
            recent_slope = float(np.polyfit(range(len(recent)), recent, 1)[0])
        else:
            recent_slope = 0

        # Prediction: extrapolate flow momentum
        # If velocity > 0 AND accelerating → strong buy pressure building
        # If velocity > 0 AND decelerating → buy pressure fading
        # If velocity < 0 AND accelerating down → strong sell pressure building
        if current_velocity > 0 and current_accel > 0:
            prediction = 'strong_buy_building'
            confidence = min(abs(current_velocity) / (abs(current_flow) + 1e-10), 1.0)
        elif current_velocity > 0 and current_accel <= 0:
            prediction = 'buy_fading'
            confidence = 0.3
        elif current_velocity < 0 and current_accel < 0:
            prediction = 'strong_sell_building'
            confidence = min(abs(current_velocity) / (abs(current_flow) + 1e-10), 1.0)
        elif current_velocity < 0 and current_accel >= 0:
            prediction = 'sell_fading'
            confidence = 0.3
        else:
            prediction = 'neutral'
            confidence = 0.1

        return {
            'current_flow': current_flow,
            'velocity': current_velocity,
            'acceleration': current_accel,
            'recent_slope': recent_slope,
            'prediction': prediction,
            'confidence': confidence,
            'total_buy_usd': float(sum(t['qty'] for t in trades if not t['is_sell'])),
            'total_sell_usd': float(sum(t['qty'] for t in trades if t['is_sell'])),
            'duration_sec': duration,
        }

    # ----------------------------------------------------------
    #  HARMONIC RESONANCE: Are bots moving WITH or AGAINST us?
    # ----------------------------------------------------------
    def _harmonic_resonance(self, spectrum: dict, flow: dict, side: str) -> dict:
        """
        The key question: do the bot waveforms HELP or HURT our position?

        If we're LONG (buy):
          - Buy flow building + accumulator power rising = HARMONY (they're buying WITH us)
          - Sell flow building + market_maker power shifting to sell = DISSONANCE (against us)

        Returns resonance score: -1 (total dissonance) to +1 (perfect harmony)
        """
        if not spectrum or not flow:
            return {'resonance': 0, 'label': 'no_data', 'details': []}

        resonance = 0
        details = []
        bands = spectrum.get('bands', {})

        # Check flow alignment
        pred = flow.get('prediction', 'neutral')
        if side == 'buy':
            if pred in ('strong_buy_building', 'buy_fading'):
                resonance += 0.3 if pred == 'strong_buy_building' else 0.1
                details.append(f"Flow: {pred} (helps buy)")
            elif pred in ('strong_sell_building', 'sell_fading'):
                resonance -= 0.3 if pred == 'strong_sell_building' else -0.1
                details.append(f"Flow: {pred} (hurts buy)")
        else:  # sell
            if pred in ('strong_sell_building', 'sell_fading'):
                resonance += 0.3 if pred == 'strong_sell_building' else 0.1
                details.append(f"Flow: {pred} (helps sell)")
            elif pred in ('strong_buy_building', 'buy_fading'):
                resonance -= 0.3 if pred == 'strong_buy_building' else -0.1
                details.append(f"Flow: {pred} (hurts sell)")

        # Check band-level buy/sell power ratios
        for band_name in ['accumulator', 'market_maker', 'scalper']:
            band = bands.get(band_name, {})
            bsr = band.get('buy_sell_ratio', 1.0)
            power_pct = band.get('power_pct', 0)

            if power_pct < 5:  # Negligible band
                continue

            if side == 'buy':
                if bsr > 1.5:
                    resonance += 0.15
                    details.append(f"{band_name}: buy-heavy ({bsr:.1f}x ratio)")
                elif bsr < 0.67:
                    resonance -= 0.15
                    details.append(f"{band_name}: sell-heavy ({bsr:.1f}x ratio)")
            else:
                if bsr < 0.67:
                    resonance += 0.15
                    details.append(f"{band_name}: sell-heavy (helps our sell)")
                elif bsr > 1.5:
                    resonance -= 0.15
                    details.append(f"{band_name}: buy-heavy (hurts our sell)")

        # Check if dominant bot is accumulator (whale) — most important signal
        dom = spectrum.get('dominant_band', 'organic')
        if dom == 'accumulator':
            acc_band = bands.get('accumulator', {})
            acc_bsr = acc_band.get('buy_sell_ratio', 1.0)
            if side == 'buy' and acc_bsr > 1.2:
                resonance += 0.2
                details.append("WHALE ACCUMULATING (buying with us)")
            elif side == 'buy' and acc_bsr < 0.8:
                resonance -= 0.2
                details.append("WHALE DISTRIBUTING (selling against us)")
            elif side == 'sell' and acc_bsr < 0.8:
                resonance += 0.2
                details.append("WHALE DISTRIBUTING (selling with us)")
            elif side == 'sell' and acc_bsr > 1.2:
                resonance -= 0.2
                details.append("WHALE ACCUMULATING (buying against us)")

        resonance = max(-1, min(1, resonance))

        if resonance > 0.3:
            label = 'harmony'
        elif resonance < -0.3:
            label = 'dissonance'
        else:
            label = 'neutral'

        return {
            'resonance': float(resonance),
            'label': label,
            'details': details,
        }

    # ----------------------------------------------------------
    #  SPECTRUM SHIFT DETECTION: Did the waveform change?
    # ----------------------------------------------------------
    def _detect_spectrum_shift(self, symbol: str, current: dict) -> dict:
        """
        Compare current spectrum to previous.
        A sudden shift means bots are changing strategy.
        """
        prev = self._prev_spectrums.get(symbol)
        if not prev or not current:
            self._prev_spectrums[symbol] = current
            return {'shifted': False, 'shift_magnitude': 0, 'details': []}

        details = []
        total_shift = 0

        curr_bands = current.get('bands', {})
        prev_bands = prev.get('bands', {})

        for band_name in WAVE_HARMONIC_BANDS:
            curr_pct = curr_bands.get(band_name, {}).get('power_pct', 0)
            prev_pct = prev_bands.get(band_name, {}).get('power_pct', 0)
            delta = curr_pct - prev_pct

            if abs(delta) > 10:  # >10% shift in band power
                direction = "increased" if delta > 0 else "decreased"
                details.append(f"{band_name} {direction} {abs(delta):.0f}%")
                total_shift += abs(delta)

        shifted = total_shift > 20  # Total >20% cross-band shift
        self._prev_spectrums[symbol] = current

        return {
            'shifted': shifted,
            'shift_magnitude': total_shift,
            'details': details,
        }

    # ----------------------------------------------------------
    #  FULL WAVEFORM SCAN: The complete picture
    # ----------------------------------------------------------
    def full_scan(self, symbol: str, side: str = 'buy') -> dict:
        """
        Complete waveform analysis on a symbol.
        Returns the full harmonic picture: who's in the pool,
        what they're doing, and whether it helps or hurts us.
        """
        if not HAS_NUMPY:
            return {'available': False, 'reason': 'numpy not installed'}

        cache_key = f"wave_{symbol}"
        if cache_key in self._cache_times and time.time() - self._cache_times[cache_key] < 10:
            return self._spectral_cache.get(symbol, {})

        trades = self._fetch_trades(symbol)
        if len(trades) < 50:
            return {'available': False, 'reason': f'only {len(trades)} trades'}

        # Run all analyzers
        spectrum = self._fft_spectral_fingerprint(trades)
        spectrogram = self._stft_spectrogram(trades)
        flow = self._flow_momentum_wave(trades)
        resonance = self._harmonic_resonance(spectrum, flow, side)
        shift = self._detect_spectrum_shift(symbol, spectrum)

        result = {
            'available': True,
            'symbol': symbol,
            'side': side,
            'spectrum': spectrum,
            'spectrogram': spectrogram,
            'flow': flow,
            'resonance': resonance,
            'shift': shift,
            'timestamp': time.time(),
            # === SUMMARY for quick decisions ===
            'dominant_bot': spectrum.get('dominant_band', 'unknown'),
            'dominant_power': spectrum.get('dominant_power_pct', 0),
            'shape': spectrogram.get('shape', 'unknown'),
            'energy_trend': spectrogram.get('energy_trend', 0),
            'flow_prediction': flow.get('prediction', 'neutral'),
            'flow_velocity': flow.get('velocity', 0),
            'resonance_score': resonance.get('resonance', 0),
            'resonance_label': resonance.get('label', 'neutral'),
            'spectrum_shifted': shift.get('shifted', False),
        }

        self._spectral_cache[symbol] = result
        self._cache_times[cache_key] = time.time()
        return result


# ==============================================================
#  BOT CATALOG - LABEL, TRACK, AND PREDICT EVERY PLAYER
# ==============================================================
# Firm signatures: frequency range → name + animal mascot
# Source: aureon_bot_intelligence_profiler.py (30+ firms)
FIRM_SIGNATURES = {
    # firm_id: (name, animal, freq_lo_Hz, freq_hi_Hz, order_size_lo, order_size_hi, mm_ratio, strategies)
    'jane_street':    ('Jane Street',         '🦈 Shark',     0.5, 8.0,   50000, 500000, 0.80, ['mm', 'arb', 'hft']),
    'citadel':        ('Citadel Securities',   '🦁 Lion',      1.0, 8.0,   50000, 500000, 0.85, ['mm', 'stat_arb', 'hft']),
    'renaissance':    ('Renaissance Tech',     '🦉 Owl',       0.2, 3.0,   10000, 200000, 0.30, ['stat_arb', 'mean_rev']),
    'two_sigma':      ('Two Sigma',            '🐺 Wolf',      0.3, 5.0,   10000, 300000, 0.50, ['ml', 'stat_arb']),
    'jump_trading':   ('Jump Trading',         '🐆 Cheetah',   1.0, 10.0,  100000, 800000, 0.75, ['hft', 'arb']),
    'virtu':          ('Virtu Financial',      '🕷️ Spider',    0.8, 8.0,   20000, 400000, 0.90, ['mm', 'liquidity']),
    'de_shaw':        ('D.E. Shaw',            '🦅 Eagle',     0.1, 2.0,   10000, 200000, 0.40, ['stat_arb', 'macro']),
    'point72':        ('Point72',              '🐻 Bear',      0.15, 1.5,  10000, 150000, 0.35, ['fundamental', 'quant']),
    'millennium':     ('Millennium Mgmt',      '🦎 Chameleon',  0.2, 3.0,   10000, 200000, 0.45, ['multi_strat']),
    'aqr':            ('AQR Capital',          '🐘 Elephant',   0.05, 1.0,  5000,  100000, 0.25, ['factor', 'momentum']),
    'bridgewater':    ('Bridgewater',          '🐋 Blue Whale', 0.01, 0.3,  5000,  50000,  0.10, ['macro', 'risk_parity']),
    'blackrock':      ('BlackRock',            '🦍 Gorilla',    0.05, 1.5,  50000, 1000000, 0.20, ['index', 'etf']),
    'susquehanna':    ('SIG',                  '🦊 Fox',        0.5, 6.0,   20000, 300000, 0.85, ['options_mm', 'arb']),
    'drw':            ('DRW Trading',          '🐉 Dragon',     0.6, 7.0,   30000, 400000, 0.70, ['mm', 'arb', 'crypto']),
    'hudson_river':   ('Hudson River Trading', '🦑 Squid',      1.5, 12.0,  50000, 600000, 0.88, ['hft', 'mm']),
    'tower_research': ('Tower Research',       '🦇 Bat',        2.0, 12.0,  75000, 400000, 0.82, ['hft', 'mm', 'stat_arb']),
    'optiver':        ('Optiver',              '🐙 Octopus',    1.0, 10.0,  30000, 400000, 0.92, ['options_mm', 'arb']),
    'flow_traders':   ('Flow Traders',         '🐟 Fish',       0.5, 6.0,   20000, 200000, 0.88, ['etf_mm', 'crypto']),
    'wintermute':     ('Wintermute',           '🐧 Penguin',    0.5, 8.0,   10000, 300000, 0.85, ['crypto_mm', 'defi']),
    'alameda_ghost':  ('Alameda Ghost',        '👻 Ghost',      0.3, 5.0,   50000, 500000, 0.60, ['arb', 'manipulation']),
    'binance_house':  ('Binance Internal',     '🏠 House',      0.5, 10.0,  100000, 2000000, 0.90, ['mm', 'liquidity']),
    'retail_swarm':   ('Retail Swarm',         '🐜 Ants',       0.01, 0.5,  10,    5000,   0.50, ['momentum', 'fomo']),
    'grid_bot':       ('Grid Bot Army',        '🤖 Robot',      0.1, 3.0,   100,   10000,  0.95, ['grid', 'dca']),
}

# Catalog state file
BOT_CATALOG_FILE = "bot_army_catalog.json"


class BotCatalog:
    """
    THE WAR ROOM REGISTRY — Every player labeled, cataloged, tracked.

    We see:
    - WHO is in the market (firm, animal mascot, type)
    - WHAT they're doing (buying/selling, power level, strategy)
    - WHERE they've been (first seen, sighting history)
    - WHAT they'll do next (based on past behavior patterns)

    Persistent: saves every sighting to bot_army_catalog.json
    Knowledge is power. We have ALL the knowledge.
    """

    def __init__(self):
        self.catalog: Dict[str, dict] = {}  # bot_id -> full record
        self._load_catalog()

    def _load_catalog(self):
        """Load persistent catalog from disk."""
        try:
            if os.path.exists(BOT_CATALOG_FILE):
                with open(BOT_CATALOG_FILE, 'r') as f:
                    self.catalog = json.load(f)
                logger.info(f"BOT CATALOG: Loaded {len(self.catalog)} known players from disk")
        except Exception as e:
            logger.warning(f"BOT CATALOG: Fresh start ({e})")
            self.catalog = {}

    def _save_catalog(self):
        """Save catalog to disk (atomic write)."""
        try:
            tmp = BOT_CATALOG_FILE + ".tmp"
            with open(tmp, 'w') as f:
                json.dump(self.catalog, f, indent=2, default=str)
            os.replace(tmp, BOT_CATALOG_FILE)
        except Exception as e:
            logger.debug(f"Catalog save failed: {e}")

    def _match_firm(self, dominant_freq: float, band_powers: dict,
                    avg_trade_usd: float, shape: str) -> tuple:
        """
        Match spectral fingerprint to a known firm.
        Frequency is the #1 identifier — bots can't change their rhythm.
        Returns: (firm_id, name, animal, confidence)
        """
        best_match = ('unknown', 'Unknown Bot', '❓ Unknown', 0.0)
        best_score = 0

        # In crypto, individual aggTrade sizes are small (fragmented)
        # so we weight frequency more heavily than size
        is_crypto_scale = avg_trade_usd < 5000  # Typical crypto aggTrade

        for firm_id, sig in FIRM_SIGNATURES.items():
            name, animal, freq_lo, freq_hi, size_lo, size_hi, mm_ratio, strategies = sig
            score = 0
            factors = 0

            # Factor 1: Frequency match (MOST IMPORTANT — spectral DNA)
            freq_weight = 50 if is_crypto_scale else 40
            if freq_lo <= dominant_freq <= freq_hi:
                score += freq_weight
            elif dominant_freq < freq_lo:
                dist = (freq_lo - dominant_freq) / max(freq_lo, 0.01)
                score += max(0, freq_weight * 0.7 - dist * 40)
            else:
                dist = (dominant_freq - freq_hi) / max(freq_hi, 0.01)
                score += max(0, freq_weight * 0.7 - dist * 40)
            factors += freq_weight

            # Factor 2: Trade size (less weight for crypto — fragmented orderflow)
            size_weight = 10 if is_crypto_scale else 25
            if size_lo <= avg_trade_usd <= size_hi:
                score += size_weight
            elif avg_trade_usd < size_lo:
                # In crypto small trades are normal — don't penalize too much
                ratio = avg_trade_usd / max(size_lo, 1)
                score += max(0, size_weight * 0.5 * ratio) if is_crypto_scale else max(0, size_weight * 0.8 * ratio)
            else:
                ratio = size_hi / max(avg_trade_usd, 1)
                score += max(0, size_weight * 0.8 * ratio)
            factors += size_weight

            # Factor 3: Band power distribution matches expected strategy
            mm_band_pct = band_powers.get('market_maker', {}).get('power_pct', 0)
            scalper_band_pct = band_powers.get('scalper', {}).get('power_pct', 0)
            acc_band_pct = band_powers.get('accumulator', {}).get('power_pct', 0)

            strat_weight = 25
            if mm_ratio > 0.7:  # Firm is a market maker
                if mm_band_pct > 8 or scalper_band_pct > 50:
                    score += strat_weight
                elif scalper_band_pct > 30:
                    score += strat_weight * 0.7
            elif mm_ratio < 0.3:  # Firm is slow/strategic
                if acc_band_pct > 1 or (mm_band_pct > 5 and scalper_band_pct < 30):
                    score += strat_weight
            else:
                score += strat_weight * 0.5  # Mixed
            factors += strat_weight

            # Factor 4: Shape matches strategy
            shape_weight = 15
            if shape in ('grid', 'oscillator') and 'mm' in strategies:
                score += shape_weight
            elif shape == 'spiral' and ('hft' in strategies or 'arb' in strategies):
                score += shape_weight
            elif shape == 'taper' and ('momentum' in strategies or 'factor' in strategies):
                score += shape_weight * 0.7
            elif shape == 'surge' and ('manipulation' in strategies or 'fomo' in strategies):
                score += shape_weight
            elif shape == 'organic' and ('macro' in strategies or 'fundamental' in strategies):
                score += shape_weight * 0.6
            else:
                score += shape_weight * 0.2  # Small base score
            factors += shape_weight

            # Factor 5: Crypto-specific firm bonus
            if is_crypto_scale:
                crypto_strats = ['crypto_mm', 'crypto', 'defi', 'arb']
                if any(s in strategies for s in crypto_strats):
                    score += 10
                factors += 10

            confidence = score / factors if factors > 0 else 0

            if score > best_score:
                best_score = score
                best_match = (firm_id, name, animal, confidence)

        return best_match

    def _generate_bot_id(self, symbol: str, dominant_freq: float,
                         dominant_band: str, shape: str) -> str:
        """
        Generate a consistent bot ID from spectral signature.
        Same bot = same frequency + band + shape → same ID.
        """
        # Quantize frequency to 0.5Hz buckets for stability
        freq_bucket = round(dominant_freq * 2) / 2
        sig = f"{symbol}:{dominant_band}:{freq_bucket:.1f}:{shape}"
        return hashlib.md5(sig.encode()).hexdigest()[:12]

    def catalog_from_waveform(self, symbol: str, wave_result: dict) -> dict:
        """
        Take a waveform analysis result and catalog every bot we can identify.
        Returns summary of players in this market right now.
        """
        if not wave_result or not wave_result.get('available'):
            return {'players': [], 'total': 0}

        spectrum = wave_result.get('spectrum', {})
        spectrogram = wave_result.get('spectrogram', {})
        flow = wave_result.get('flow', {})
        bands = spectrum.get('bands', {})

        _ = spectrum.get('dominant_freq', 0)
        _ = spectrum.get('dominant_band', 'organic')
        shape = spectrogram.get('shape', 'unknown')
        n_trades = spectrum.get('n_trades', 0)

        # Average trade size (total volume / num trades)
        total_buy = flow.get('total_buy_usd', 0)
        total_sell = flow.get('total_sell_usd', 0)
        avg_trade = (total_buy + total_sell) / max(n_trades, 1)

        now = time.time()
        players = []

        # For each active band, identify a player
        for band_name, band_data in bands.items():
            power_pct = band_data.get('power_pct', 0)
            if power_pct < 2:  # Negligible
                continue

            band_freq = band_data.get('dominant_freq', 0)
            bsr = band_data.get('buy_sell_ratio', 1.0)
            _ = band_data.get('peak_amplitude', 0)

            # Generate bot ID for this band's actor
            bot_id = self._generate_bot_id(symbol, band_freq, band_name, shape)

            # Match to firm
            firm_id, firm_name, animal, confidence = self._match_firm(
                band_freq, bands, avg_trade, shape
            )

            # Determine what this player is doing right now
            if bsr > 1.3:
                action = 'BUYING'
                direction = 'bullish'
            elif bsr < 0.77:
                action = 'SELLING'
                direction = 'bearish'
            else:
                action = 'NEUTRAL'
                direction = 'neutral'

            player = {
                'bot_id': bot_id,
                'firm_id': firm_id,
                'firm_name': firm_name,
                'animal': animal,
                'band': band_name,
                'frequency': round(band_freq, 4),
                'power_pct': round(power_pct, 1),
                'buy_sell_ratio': round(bsr, 2),
                'action': action,
                'direction': direction,
                'confidence': round(confidence, 2),
                'shape': shape,
                'symbol': symbol,
                'timestamp': now,
            }
            players.append(player)

            # === UPDATE PERSISTENT CATALOG ===
            if bot_id in self.catalog:
                record = self.catalog[bot_id]
                record['last_seen'] = now
                record['sighting_count'] = record.get('sighting_count', 0) + 1
                record['last_action'] = action
                record['last_direction'] = direction
                record['last_power_pct'] = power_pct
                record['last_bsr'] = round(bsr, 2)
                record['last_shape'] = shape
                record['last_symbol'] = symbol

                # Track action history (last 50 sightings)
                history = record.get('action_history', [])
                history.append({
                    'ts': round(now),
                    'action': action,
                    'bsr': round(bsr, 2),
                    'power': round(power_pct, 1),
                    'symbol': symbol,
                })
                record['action_history'] = history[-50:]

                # Update confidence if better match found
                if confidence > record.get('confidence', 0):
                    record['firm_id'] = firm_id
                    record['firm_name'] = firm_name
                    record['animal'] = animal
                    record['confidence'] = round(confidence, 2)
            else:
                # NEW PLAYER DETECTED — catalog them
                self.catalog[bot_id] = {
                    'bot_id': bot_id,
                    'firm_id': firm_id,
                    'firm_name': firm_name,
                    'animal': animal,
                    'band': band_name,
                    'first_seen': now,
                    'last_seen': now,
                    'first_symbol': symbol,
                    'last_symbol': symbol,
                    'sighting_count': 1,
                    'confidence': round(confidence, 2),
                    'frequency': round(band_freq, 4),
                    'shape': shape,
                    'last_action': action,
                    'last_direction': direction,
                    'last_power_pct': round(power_pct, 1),
                    'last_bsr': round(bsr, 2),
                    'action_history': [{
                        'ts': round(now),
                        'action': action,
                        'bsr': round(bsr, 2),
                        'power': round(power_pct, 1),
                        'symbol': symbol,
                    }],
                }
                logger.info(
                    f"NEW PLAYER CATALOGED: {animal} {firm_name} | "
                    f"ID={bot_id} band={band_name} freq={band_freq:.3f}Hz | "
                    f"{action} (bsr={bsr:.2f}) power={power_pct:.1f}%"
                )

        # Save every 10 sightings to avoid excessive I/O
        total_sightings = sum(r.get('sighting_count', 0) for r in self.catalog.values())
        if total_sightings % 10 < len(players):
            self._save_catalog()

        return {
            'players': players,
            'total': len(players),
            'catalog_size': len(self.catalog),
        }

    def predict_player(self, bot_id: str) -> dict:
        """
        Predict a player's next move based on their history.
        Knowledge is power — we've watched them before.
        """
        record = self.catalog.get(bot_id)
        if not record:
            return {'prediction': 'unknown', 'confidence': 0}

        history = record.get('action_history', [])
        if len(history) < 3:
            return {
                'prediction': record.get('last_direction', 'neutral'),
                'confidence': 0.2,
                'reason': 'insufficient_history',
            }

        # Analyze recent pattern
        recent = history[-10:]  # Last 10 sightings
        buy_count = sum(1 for h in recent if h['action'] == 'BUYING')
        sell_count = sum(1 for h in recent if h['action'] == 'SELLING')
        _ = sum(1 for h in recent if h['action'] == 'NEUTRAL')

        # Power trend
        powers = [h['power'] for h in recent]
        if len(powers) >= 3:
            power_trend = powers[-1] - powers[0]
        else:
            power_trend = 0

        # BSR trend (are they becoming more bullish or bearish?)
        bsrs = [h['bsr'] for h in recent]
        if len(bsrs) >= 3:
            bsr_trend = bsrs[-1] - bsrs[0]
        else:
            bsr_trend = 0

        # Predict based on momentum of their behavior
        total = len(recent)
        if buy_count > sell_count * 2:
            if bsr_trend > 0:
                prediction = 'will_keep_buying'
                confidence = min(0.9, buy_count / total)
            else:
                prediction = 'buy_exhaustion'
                confidence = 0.5
        elif sell_count > buy_count * 2:
            if bsr_trend < 0:
                prediction = 'will_keep_selling'
                confidence = min(0.9, sell_count / total)
            else:
                prediction = 'sell_exhaustion'
                confidence = 0.5
        elif power_trend > 5:
            prediction = 'ramping_up'
            confidence = 0.6
        elif power_trend < -5:
            prediction = 'withdrawing'
            confidence = 0.6
        else:
            prediction = 'holding_pattern'
            confidence = 0.3

        return {
            'prediction': prediction,
            'confidence': confidence,
            'history_length': len(history),
            'recent_buys': buy_count,
            'recent_sells': sell_count,
            'power_trend': round(power_trend, 1),
            'bsr_trend': round(bsr_trend, 2),
            'firm': record.get('firm_name', 'Unknown'),
            'animal': record.get('animal', '❓'),
        }

    def get_market_players(self, symbol: str) -> list:
        """
        Get all known players in a specific market.
        Shows: who's been here, what they've done, what they'll do.
        """
        now = time.time()
        players = []
        for bot_id, record in self.catalog.items():
            if record.get('last_symbol') == symbol or record.get('first_symbol') == symbol:
                age = now - record.get('first_seen', now)
                last_active = now - record.get('last_seen', now)

                if last_active > 3600:  # Gone for > 1 hour
                    status = 'GONE'
                elif last_active > 300:  # Gone for > 5 min
                    status = 'DORMANT'
                else:
                    status = 'ACTIVE'

                prediction = self.predict_player(bot_id)

                players.append({
                    'bot_id': bot_id,
                    'animal': record.get('animal', '❓'),
                    'firm': record.get('firm_name', 'Unknown'),
                    'status': status,
                    'sightings': record.get('sighting_count', 0),
                    'first_seen_ago': round(age),
                    'last_action': record.get('last_action', '?'),
                    'power': record.get('last_power_pct', 0),
                    'prediction': prediction.get('prediction', '?'),
                    'pred_confidence': prediction.get('confidence', 0),
                })

        # Sort: active first, then by power
        status_order = {'ACTIVE': 0, 'DORMANT': 1, 'GONE': 2}
        players.sort(key=lambda p: (status_order.get(p['status'], 3), -p['power']))
        return players

    def get_battlefield_summary(self, symbol: str, wave_result: dict = None) -> str:
        """
        One-line summary of all players in this market.
        For the monitoring log: who's here and what they're doing.
        """
        if wave_result:
            self.catalog_from_waveform(symbol, wave_result)

        players = self.get_market_players(symbol)
        active = [p for p in players if p['status'] == 'ACTIVE']

        if not active:
            return "no known players"

        parts = []
        for p in active[:4]:  # Show top 4
            animal = p['animal'].split(' ')[0] if p['animal'] else '❓'
            action = p['last_action'][0] if p['last_action'] else '?'
            pred = p['prediction'][:8] if p['prediction'] else '?'
            parts.append(f"{animal}{action}({p['power']:.0f}%→{pred})")

        total = len(self.catalog)
        return f"{' '.join(parts)} [{len(active)} active/{total} cataloged]"


# ==============================================================
#  THE ARMY TRADER
# ==============================================================
class KrakenMarginArmyTrader:
    """
    Army discipline: 1 position. ALL in. GBP1 profit. Out. Next.
    Monitoring: FREE APIs only (Binance public)
    Execution: Kraken API only (open/close)
    """

    def __init__(
        self,
        dry_run: bool = False,
        *,
        unity_composition: Any = None,
        unity_plan_supplier: Any = None,
        trusted_unity_plan_supplier_ids: Tuple[str, ...] = (),
        mycelium_network: Any = None,
    ):
        if dry_run:
            os.environ["KRAKEN_DRY_RUN"] = "true"
        try:
            from aureon.exchanges.kraken_client import KrakenClient
        except ImportError:
            from aureon.exchanges.kraken_client import KrakenClient
        self.client = KrakenClient()
        self.dry_run = dry_run or self.client.dry_run
        self.market = FreeMarketData()
        self.intel = BattlefieldIntel()
        # Arm the intel with the waveform analyzer (sees bot moves before they happen)
        if HAS_NUMPY:
            self.intel.waveform = WaveformAnalyzer()
            logger.info("WAVEFORM ANALYZER: Armed and scanning the harmonic pool")
        # The War Room: label, catalog, and track every player
        self.bot_catalog = BotCatalog()
        logger.info(f"BOT CATALOG: {len(self.bot_catalog.catalog)} players in the war room")
        # LIVE STREAM: Binance WebSocket for sub-second reaction
        self.stream = LiveStream() if HAS_WEBSOCKET else None
        self._stream_started = False
        self._last_stream_self_heal = 0.0
        self.margin_pairs: Dict[str, MarginPairInfo] = {}
        # DUAL POSITION: 1 LONG + 1 SHORT simultaneously
        self.active_long: Optional[ActiveTrade] = None
        self.active_short: Optional[ActiveTrade] = None
        self.extra_active_longs: List[ActiveTrade] = []
        self.extra_active_shorts: List[ActiveTrade] = []
        # SHADOW TRADES: Prove predictions before deploying capital
        self.shadow_trades: List[ShadowTrade] = []
        self.shadow_validated_count = 0  # How many shadows proved right
        self.shadow_failed_count = 0     # How many shadows proved wrong
        self.shadow_pair_cooldowns: Dict[str, float] = {}
        # Legacy alias for code that still references active_trade
        self.active_trade: Optional[ActiveTrade] = None
        self.total_profit = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.completed_trades: List[dict] = []
        # Submission acknowledgements are not fills. Keep unresolved receipts
        # latched in memory so a subsequent invocation reconciles once instead
        # of creating a duplicate order.
        self._unresolved_open_submissions: Dict[str, Dict[str, Any]] = {}
        self._unresolved_close_submissions: Dict[str, Dict[str, Any]] = {}
        self._last_execution_receipt: Dict[str, Any] = {}
        self.start_time = time.time()
        self.starting_equity = 0.0
        self.dashboard_user_id = DASHBOARD_LIVE_FEED_USER_ID
        self.dashboard_sync_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.dashboard_sync_key = (
            os.getenv("SUPABASE_ANON_KEY", "")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        )
        self.dashboard_sync_enabled = bool(self.dashboard_sync_url and self.dashboard_sync_key)
        self._last_dashboard_push = 0.0
        self._peak_equity_seen = 0.0
        self._max_drawdown_seen = 0.0
        self._latest_monitor_line = ""
        self._latest_status_lines: List[str] = []
        self._latest_dashboard_payload: Dict[str, Any] = {}
        self._last_margin_capital = None
        self._last_margin_capital_at = 0.0
        self._last_margin_capital_error = ""
        self._last_spot_balance_snapshot: Dict[str, Any] = {}
        self._last_spot_balance_snapshot_at = 0.0
        self._last_truth_check_at = 0.0
        self._latest_truth_check: Dict[str, Any] = {}
        self._last_fast_profit_capture: Dict[str, Any] = {}
        self._fast_profit_capture_by_order: Dict[str, Dict[str, Any]] = {}
        self._local_dashboard_server: Optional[ThreadingHTTPServer] = None
        self._local_dashboard_thread: Optional[threading.Thread] = None
        self._last_danger_check = 0
        self._danger_check_interval = 15  # Check danger every 15s
        self._consecutive_danger = 0       # Track consecutive danger signals
        # ETA predictor for margin time-to-profit estimates
        self.eta_predictor = MarginETAPredictor() if HAS_ETA_PREDICTOR else None
        self._last_eta_report = 0        # Track ETA report frequency
        self._eta_report_interval = 300  # Report ETA every 300s (5 min)
        # Dead Man's Switch trackers - one DTP instance per active margin trade.
        # Keyed by trade.order_id so they survive across monitoring cycles.
        # The DTP receives the pre-calculated net_pnl (USD) directly so all
        # rollover/fee math already done by the existing pipeline feeds straight in.
        self.dtp_trackers: dict = {}
        # Margin Wave Rider - pre-entry 250% margin gate
        self.wave_rider = MarginWaveRider(
            entry_min_margin_pct=MARGIN_WAVE_ENTRY_PCT,
            danger_margin_pct=LIQUIDATION_FORCE,
        ) if HAS_WAVE_RIDER else None
        self.dynamic_sizer = (
            DynamicMarginSizer(DynamicMarginConfig(
                max_free_margin_fraction=MARGIN_BUFFER,
                tiny_account_max_free_margin_fraction=TINY_ACCOUNT_MARGIN_BUFFER,
                tiny_account_equity_usd=TINY_ACCOUNT_EQUITY_USD,
                entry_min_margin_pct=MARGIN_WAVE_ENTRY_PCT,
                min_free_margin_usd=WAVE_CONFIG.get("min_free_margin_usd", 5.0),
                fallback_min_notional_usd=DYNAMIC_MIN_NOTIONAL_USD,
                min_profit_target_usd=DYNAMIC_MIN_PROFIT_USD,
                target_equity_fraction=DYNAMIC_TARGET_EQUITY_FRACTION,
            ))
            if HAS_DYNAMIC_MARGIN_SIZER else None
        )
        self.temporal_cognition = (
            TemporalTradeCognition()
            if HAS_TEMPORAL_TRADE_COGNITION and TemporalTradeCognition is not None
            else None
        )
        self.margin_decision_brain = (
            UnifiedMarginDecisionBrain(
                MarginBrainConfig(max_eta_minutes=GOAL_MAX_ETA_MINUTES)
            )
            if (
                HAS_UNIFIED_MARGIN_BRAIN
                and UnifiedMarginDecisionBrain is not None
                and MarginBrainConfig is not None
            )
            else None
        )
        self._candidate_cognition_context: Dict[str, Dict[str, Any]] = {}
        self._latest_trade_cognition: Dict[str, Any] = {}
        self._last_cognition_status: Dict[str, str] = {}
        self._latest_margin_brain_decision: Dict[str, Any] = {}
        self._margin_brain_decisions: Dict[str, Any] = {}
        # Stallion Multiverse - 1-hour ride limit + parallel shadow rides
        self.multiverse: object = StallionMultiverse() if HAS_MULTIVERSE else None
        self._multiverse_ride_registered = False
        # Learning Bridge - pipes multiverse insight to Seer, Lyra, pre-trade
        self.learning_bridge: object = (
            MultiverseLearningBridge(self.multiverse)
            if HAS_LEARNING_BRIDGE and self.multiverse is not None
            else None
        )
        # Autonomous Orchestrator - central nervous system for all Queen's systems
        self.orchestrator: object = (
            AutonomousOrchestrator(self)
            if HAS_ORCHESTRATOR else None
        )
        # Goal Recorder — records every scan + outcome to margin_goal_proof.jsonl
        self._goal_recorder = MarginGoalRecorder() if HAS_GOAL_RECORDER else None
        self._pending_scan_id: str = ""
        # Macro Intelligence — market-wide context fed into every entry decision
        self.macro: object = MacroIntelligence() if HAS_MACRO_INTEL else None
        self.seer = get_seer() if HAS_SEER and get_seer is not None else None
        sniper_factory = _load_unified_sniper_brain()
        self.sniper_brain = sniper_factory(exchange='kraken') if sniper_factory is not None else None
        self.nexus_predictor = NexusPredictor() if HAS_NEXUS_PREDICTOR and NexusPredictor is not None else None
        self.lattice = LatticeEngine() if HAS_LATTICE and LatticeEngine is not None else None
        self.atn_monitor = get_atn_monitor() if HAS_ATN_MONITOR and get_atn_monitor is not None else None
        self.unified_registry = get_unified_puller() if HAS_UNIFIED_REGISTRY and get_unified_puller is not None else None
        self.unified_decision_engine = UnifiedDecisionEngine() if HAS_UNIFIED_DECISION and UnifiedDecisionEngine is not None else None
        self.thought_bus = (
            get_thought_bus(os.path.join(_REPO_ROOT, "state", "kraken_thoughts.jsonl"))
            if HAS_THOUGHT_BUS and get_thought_bus is not None else None
        )
        self.margin_harmonic_scanner = (
            HarmonicMarginWaveformScanner() if HAS_MARGIN_HARMONIC_SCANNER and HarmonicMarginWaveformScanner is not None else None
        )
        self.quantum_mirror_scanner = (
            create_quantum_scanner(with_integrations=False)
            if HAS_QUANTUM_MIRROR_SCANNER and create_quantum_scanner is not None else None
        )
        self.timeline_oracle = (
            get_timeline_oracle() if HAS_TIMELINE_ORACLE and get_timeline_oracle is not None else None
        )
        self.harmonic_fusion = (
            HarmonicWaveFusion() if HAS_HARMONIC_FUSION and HarmonicWaveFusion is not None else None
        )
        self.whale_orderbook = (
            WhaleOrderbookAnalyzer(poll_symbols=[], poll_interval=1.0)
            if HAS_WHALE_ORDERBOOK and WhaleOrderbookAnalyzer is not None else None
        )
        self.kraken_fee_tracker = (
            get_kraken_fee_tracker(self.client)
            if HAS_KRAKEN_FEE_TRACKER and get_kraken_fee_tracker is not None
            else None
        )
        self.ocean_wave_scanner = (
            OceanWaveScanner() if HAS_OCEAN_WAVE_SCANNER and OceanWaveScanner is not None else None
        )
        self.live_tv_log_path = Path(os.getenv("AUREON_LIVE_TV_LOG_PATH", os.path.join(_REPO_ROOT, "data", "live_tv_stream.jsonl")))
        self._live_tv_tail_offset = 0
        self._live_tv_symbol_cache: Dict[str, Dict[str, Any]] = {}
        self._live_tv_snapshot: Dict[str, Any] = {}
        self._ocean_snapshot: Dict[str, Any] = {}
        self._registry_snapshot: Dict[str, Any] = {}
        self._decision_snapshot: Dict[str, Any] = {}
        self._harmonic_snapshot: Dict[str, Any] = {}
        self._quantum_snapshot: Dict[str, Any] = {}
        self._timeline_snapshot: Dict[str, Any] = {}
        self._fusion_snapshot: Dict[str, Any] = {}
        self._whale_snapshot: Dict[str, Any] = {}
        self._fee_snapshot: Dict[str, Any] = {}
        self._brain_snapshot: Dict[str, Any] = {}
        self._validator_snapshot: Dict[str, Any] = {}
        self._thought_bus_snapshot: Dict[str, Any] = {}
        self._cognition_snapshot: Dict[str, Any] = {}
        # ── TIER 1: High-Impact Signal Producers ────────────────────
        self.phase_transition_detector = (
            PhaseTransitionDetector() if HAS_PHASE_TRANSITION and PhaseTransitionDetector is not None else None
        )
        self.prob_ultimate = (
            get_ultimate_intelligence() if HAS_PROB_ULTIMATE and get_ultimate_intelligence is not None else None
        )
        self.phantom_filter = (
            PhantomSignalFilter() if HAS_PHANTOM_FILTER and PhantomSignalFilter is not None else None
        )
        self.global_financial_feed = (
            GlobalFinancialFeed() if HAS_GLOBAL_FINANCIAL and GlobalFinancialFeed is not None else None
        )
        self.whale_behavior_predictor = (
            WhaleBehaviorPredictor() if HAS_WHALE_BEHAVIOR and WhaleBehaviorPredictor is not None else None
        )
        self.kraken_signal_bridge = (
            KrakenUnifiedSignalBridge() if HAS_KRAKEN_SIGNAL_BRIDGE and KrakenUnifiedSignalBridge is not None else None
        )
        self.truth_prediction_engine = (
            TruthPredictionEngine() if HAS_TRUTH_PREDICTION and TruthPredictionEngine is not None else None
        )
        self.prob_nexus = (
            EnhancedProbabilityNexus() if HAS_PROB_NEXUS and EnhancedProbabilityNexus is not None else None
        )
        # ── TIER 2: Market Intelligence & Context ───────────────────
        self.real_intel_engine = (
            RealIntelligenceEngine() if HAS_REAL_INTEL and RealIntelligenceEngine is not None else None
        )
        self.market_organism = (
            get_market_organism() if HAS_MARKET_ORGANISM and get_market_organism is not None else None
        )
        self.elephant_memory = (
            ElephantMemory() if HAS_ELEPHANT and ElephantMemory is not None else None
        )
        self.advanced_intel = (
            AdvancedMycelium() if HAS_ADVANCED_INTEL and AdvancedMycelium is not None else None
        )
        self.reality_detector = (
            get_reality_detector() if HAS_REALITY_DETECTOR and get_reality_detector is not None else None
        )
        self.global_wave_scanner = (
            GlobalWaveScanner() if HAS_GLOBAL_WAVE and GlobalWaveScanner is not None else None
        )
        self.obsidian_filter = (
            AureonObsidianFilter() if HAS_OBSIDIAN_FILTER and AureonObsidianFilter is not None else None
        )
        # ── TIER 3: Harmonic, Resonance & Correlation ───────────────
        self.schumann_bridge = (
            get_schumann_bridge() if HAS_SCHUMANN and get_schumann_bridge is not None else None
        )
        self.harmonic_nexus = (
            HarmonicNexusBridge() if HAS_HARMONIC_NEXUS and HarmonicNexusBridge is not None else None
        )
        self.earth_resonance = (
            get_earth_engine() if HAS_EARTH_RESONANCE and get_earth_engine is not None else None
        )
        self.market_harp = (
            MarketHarp() if HAS_MARKET_HARP and MarketHarp is not None else None
        )
        self.crypto_map = (
            CryptoMarketMap() if HAS_CRYPTO_MAP and CryptoMarketMap is not None else None
        )
        self.sensory_registry = (
            SensoryRegistry() if HAS_SENSORY and SensoryRegistry is not None else None
        )
        # ── TIER 4: Core Infrastructure ─────────────────────────────
        self.chirp_bus = (
            get_chirp_bus() if HAS_CHIRP_BUS and get_chirp_bus is not None else None
        )
        self.whale_sonar = (
            WhaleSonar(thought_bus=self.thought_bus) if HAS_WHALE_SONAR and WhaleSonar is not None else None
        )
        self.hive_state = (
            get_hive_state() if HAS_HIVE_STATE and get_hive_state is not None else None
        )
        self.trading_hive_mind = (
            TradingHiveMind() if HAS_TRADING_HIVE_MIND and TradingHiveMind is not None else None
        )
        self.inception_engine = (
            InceptionEngine() if HAS_INCEPTION and InceptionEngine is not None else None
        )
        # ── Snapshots for all new systems ───────────────────────────
        self._phase_transition_snapshot: Dict[str, Any] = {}
        self._prob_ultimate_snapshot: Dict[str, Any] = {}
        self._news_signal_snapshot: Dict[str, Any] = {}
        self._phantom_filter_snapshot: Dict[str, Any] = {}
        self._global_financial_snapshot: Dict[str, Any] = {}
        self._whale_behavior_snapshot: Dict[str, Any] = {}
        self._kraken_signal_bridge_snapshot: Dict[str, Any] = {}
        self._truth_prediction_snapshot: Dict[str, Any] = {}
        self._prob_nexus_snapshot: Dict[str, Any] = {}
        self._real_intel_snapshot: Dict[str, Any] = {}
        self._market_organism_snapshot: Dict[str, Any] = {}
        self._elephant_snapshot: Dict[str, Any] = {}
        self._advanced_intel_snapshot: Dict[str, Any] = {}
        self._reality_detector_snapshot: Dict[str, Any] = {}
        self._global_wave_snapshot: Dict[str, Any] = {}
        self._obsidian_snapshot: Dict[str, Any] = {}
        self._schumann_snapshot: Dict[str, Any] = {}
        self._harmonic_nexus_snapshot: Dict[str, Any] = {}
        self._earth_resonance_snapshot: Dict[str, Any] = {}
        self._market_harp_snapshot: Dict[str, Any] = {}
        self._crypto_map_snapshot: Dict[str, Any] = {}
        self._sensory_snapshot: Dict[str, Any] = {}
        self._whale_sonar_snapshot: Dict[str, Any] = {}
        self._hive_state_snapshot: Dict[str, Any] = {}
        self._inception_snapshot: Dict[str, Any] = {}
        self.signal_brain = AureonBrain() if HAS_AUREON_BRAIN and AureonBrain is not None else None
        self.trade_profit_validator = (
            TradeProfitValidator(validation_log_file=os.path.join(_REPO_ROOT, "state", "kraken_trade_validations.json"))
            if HAS_TRADE_PROFIT_VALIDATOR and TradeProfitValidator is not None
            else None
        )
        self._load_state()
        try:
            snap = self._get_capital_snapshot()
            self.starting_equity = snap["equity"]
        except Exception:
            if not self.dry_run:
                raise
            self.starting_equity = 0.0
            logger.info("Dry-run account state is no_data; live submission remains disabled")
        self._install_unity_exchange_brain(
            raw_client=self.client,
            unity_composition=unity_composition,
            unity_plan_supplier=unity_plan_supplier,
            trusted_unity_plan_supplier_ids=trusted_unity_plan_supplier_ids,
            mycelium_network=mycelium_network,
        )
        if os.getenv("AUREON_DISABLE_LOCAL_DASHBOARD", "0") != "1":
            self._start_local_dashboard_server()

        # Subscribe to Queen Hive Command hunt signals
        if self.thought_bus is not None:
            try:
                self.thought_bus.subscribe("queen.command.hunt", self._on_queen_hunt)
                logger.info("[QUEEN HIVE] Subscribed to queen.command.hunt")
            except Exception:
                pass

    def _install_unity_exchange_brain(
        self,
        *,
        raw_client: Any,
        unity_composition: Any,
        unity_plan_supplier: Any,
        trusted_unity_plan_supplier_ids: Tuple[str, ...],
        mycelium_network: Any = None,
    ) -> None:
        """Put Kraken mutations behind the Queen while preserving read surfaces."""

        from aureon.core.economic_sensation import OrganismEconomicSensationRouter
        from aureon.queen.unity_exchange_brain import build_queen_exchange_brains

        if mycelium_network is None:
            try:
                from aureon.core.aureon_mycelium import get_mycelium

                mycelium_network = get_mycelium()
            except Exception:
                mycelium_network = None
        self.mycelium_network = mycelium_network
        self._economic_sensation_router = OrganismEconomicSensationRouter(
            bus_getter=lambda: getattr(self, "thought_bus", None),
            hive_getter=lambda: getattr(self, "hive_state", None),
            mycelium_getter=lambda: getattr(self, "mycelium_network", None),
        )
        fallback_read_clients = (
            None if unity_composition is not None else {"kraken": raw_client}
        )
        brains, governed, status = build_queen_exchange_brains(
            unity_composition=unity_composition,
            unity_plan_supplier=unity_plan_supplier,
            trusted_unity_plan_supplier_ids=trusted_unity_plan_supplier_ids,
            fallback_read_clients=fallback_read_clients,
            outcome_observer=self._economic_sensation_router.observe,
        )
        self._queen_exchange_brains = brains
        self._queen_governed_exchange_client = governed
        self._queen_exchange_governance_status = status
        self.client = brains["kraken"]

    def recent_economic_sensations(self) -> List[Dict[str, Any]]:
        """Return bounded feedback receipts; never mutation authority."""

        router = getattr(self, "_economic_sensation_router", None)
        return router.recent() if router is not None else []

    # ----------------------------------------------------------
    #  QUEEN HIVE COMMAND: Execute hunts issued by the Queen
    # ----------------------------------------------------------

    def _on_queen_hunt(self, thought) -> None:
        """Queen issued a hunt command — gate through orchestrator and execute."""
        try:
            payload = thought.payload if hasattr(thought, 'payload') else thought
            if not isinstance(payload, dict):
                return
            pair = str(payload.get("symbol") or "")
            if not pair:
                return
            # Normalize pair to Kraken format if needed
            if not any(pair.endswith(q) for q in ("USD", "ZUSD", "EUR")):
                pair = pair + "USD"
            side = "buy"
            composite = float(payload.get("composite_score", 0) or 0)
            consensus = int(payload.get("consensus_count", 0) or 0)
            logger.info(
                f"[QUEEN HUNT] Received: {pair} composite={composite:.3f} consensus={consensus}"
            )
            # Gate through orchestrator
            if self.orchestrator is not None:
                approved, reason, sizing = self.orchestrator.gate_pre_trade(pair, side)
                if not approved:
                    logger.info(f"[QUEEN HUNT] Blocked by orchestrator: {reason}")
                    return
                logger.info(f"[QUEEN HUNT] Approved: {pair} sizing={sizing:.2f}x reason={reason}")
                # TODO: Execute margin trade with the approved sizing
                # self._open_margin_position(pair, side, sizing_modifier=sizing)
            else:
                logger.debug("[QUEEN HUNT] No orchestrator — skipping execution")
        except Exception as e:
            logger.debug(f"[QUEEN HUNT] Error: {e}")

    # ----------------------------------------------------------
    #  ETA PREDICTION: Estimate time to profitability
    # ----------------------------------------------------------
    def _report_margin_eta(self) -> None:
        """Calculate and log ETA for margin positions (every 5 mins)."""
        if not HAS_ETA_PREDICTOR or not self.eta_predictor:
            return
        
        try:
            now = time.time()
            if now - self._last_eta_report < self._eta_report_interval:
                return  # Not time yet
            
            self._last_eta_report = now
            etas = self.eta_predictor.predict_all()
            
            if not etas:
                return
            
            # Log ETA summary
            logger.info("="*80)
            logger.info("MARGIN ETA ANALYSIS - TIME-TO-PROFITABILITY")
            logger.info("="*80)
            
            for eta in etas:
                logger.info(
                    f"{eta.symbol}: Entry={eta.entry_price:.6f} | Current={eta.current_price:.6f} | "
                    f"Breakeven={eta.breakeven_price:.6f} | Distance={eta.pct_to_breakeven:+.2f}%"
                )
                
                if eta.eta_minutes == 0:
                    logger.info(f"  ✅ PROFITABLE - Position is now profitable!")
                else:
                    logger.info(
                        f"  ⏱️  ETA: {eta.eta_minutes:.0f}m ({eta.eta_minutes/60:.1f}h) | "
                        f"Bullish: {eta.bullish_eta:.0f}m | Bearish: {eta.bearish_eta:.0f}m | "
                        f"Confidence: {eta.confidence*100:.0f}%"
                    )
            
            logger.info("="*80)
        except Exception as e:
            logger.debug(f"ETA report failed: {e}")

    def _start_local_dashboard_server(self) -> None:
        """Expose trader telemetry over localhost for the React dashboard."""
        try:
            server = ThreadingHTTPServer((LOCAL_DASHBOARD_HOST, LOCAL_DASHBOARD_PORT), _LocalDashboardHandler)
            server.trader_ref = self  # type: ignore[attr-defined]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self._local_dashboard_server = server
            self._local_dashboard_thread = thread
            logger.info(f"LOCAL DASHBOARD: http://{LOCAL_DASHBOARD_HOST}:{LOCAL_DASHBOARD_PORT}/api/terminal-state")
        except OSError as e:
            logger.warning(f"LOCAL DASHBOARD: unavailable on {LOCAL_DASHBOARD_HOST}:{LOCAL_DASHBOARD_PORT} ({e})")

    def get_local_dashboard_state(self) -> dict:
        """Return the last local telemetry payload for the dashboard."""
        payload = dict(self._latest_dashboard_payload)
        payload.setdefault("ok", True)
        payload.setdefault("source", "local-trader")
        payload.setdefault("generated_at", datetime.now().isoformat())
        return payload

    def _binance_symbol_for_pair(self, pair: str) -> str:
        """Derive Binance symbol for a Kraken alt/internal pair."""
        try:
            if pair in self.margin_pairs and self.margin_pairs[pair].binance_symbol:
                return self.margin_pairs[pair].binance_symbol
            pairs = self.client._load_asset_pairs()
            internal = self.client._alt_to_int.get(pair, pair)
            info = pairs.get(internal, {})
            base = info.get("base", "")
            if not base:
                return ""
            base_clean = KRAKEN_BASE_MAP.get(base, base)
            return f"{base_clean}USDT"
        except Exception:
            return ""

    def _get_fee_rates(self, symbol: str = "", is_taker: bool = True) -> Dict[str, Any]:
        """Resolve current Kraken fee rates with a safe static fallback."""
        fallback = {
            "maker": KRAKEN_CLOSE_FEE,
            "taker": KRAKEN_OPEN_FEE,
            "current": KRAKEN_OPEN_FEE if is_taker else KRAKEN_CLOSE_FEE,
            "tier": None,
            "volume_30d": 0.0,
            "pair_type": "fallback",
            "source": "fallback",
        }
        if self.kraken_fee_tracker is None:
            self._fee_snapshot = dict(fallback)
            return fallback
        try:
            rates = dict(self.kraken_fee_tracker.get_fee_rates(symbol=symbol, is_taker=is_taker))
            rates["source"] = "tracker"
            self._fee_snapshot = dict(rates)
            return rates
        except Exception as e:
            logger.debug(f"Dynamic Kraken fee lookup failed for {symbol or 'default'}: {e}")
            self._fee_snapshot = dict(fallback)
            return fallback

    def _get_open_close_fee_rates(self, symbol: str = "") -> Tuple[float, float]:
        """Return effective open/close fee rates for selector and monitor math."""
        taker_rates = self._get_fee_rates(symbol=symbol, is_taker=True)
        open_fee = float(taker_rates.get("current", KRAKEN_OPEN_FEE) or KRAKEN_OPEN_FEE)
        close_fee = float(taker_rates.get("current", KRAKEN_CLOSE_FEE) or KRAKEN_CLOSE_FEE)
        return open_fee, close_fee

    def _estimate_round_trip_fee(self, trade_value: float, symbol: str = "") -> Tuple[float, float, float]:
        """Estimate open+close fees using live Kraken tier rates when available."""
        open_fee_rate, close_fee_rate = self._get_open_close_fee_rates(symbol=symbol)
        return trade_value * (open_fee_rate + close_fee_rate), open_fee_rate, close_fee_rate

    def _estimate_required_move_pct(self, trade_value: float, profit_target_usd: float, symbol: str = "") -> Tuple[float, float, float]:
        """Return required move %, plus the underlying open/close fee rates used."""
        round_trip_fee, open_fee_rate, close_fee_rate = self._estimate_round_trip_fee(trade_value, symbol=symbol)
        required_move_pct = ((round_trip_fee + profit_target_usd) / trade_value * 100) if trade_value > 0 else 0.0
        return required_move_pct, open_fee_rate, close_fee_rate

    def _validator_required_move_pct(self, trade_value: float, profit_target_usd: float, symbol: str = "") -> Tuple[float, float]:
        """Estimate stricter required move using validator slippage/spread costs."""
        if self.trade_profit_validator is None or trade_value <= 0:
            self._validator_snapshot = {
                "symbol": symbol,
                "trade_value": trade_value,
                "round_trip_cost": 0.0,
                "required_move_pct": ((profit_target_usd / trade_value) * 100) if trade_value > 0 else 0.0,
                "source": "disabled",
            }
            return (((profit_target_usd / trade_value) * 100) if trade_value > 0 else 0.0), 0.0
        try:
            costs = self.trade_profit_validator.get_exchange_costs(
                "kraken",
                trade_value,
                is_taker=True,
                symbol=symbol,
            )
            round_trip_cost = float(costs.get("total", 0.0) or 0.0) * 2.0
            required_move_pct = ((round_trip_cost + profit_target_usd) / trade_value * 100) if trade_value > 0 else 0.0
            self._validator_snapshot = {
                "symbol": symbol,
                "trade_value": trade_value,
                "round_trip_cost": round_trip_cost,
                "required_move_pct": required_move_pct,
                "source": "validator",
            }
            return required_move_pct, round_trip_cost
        except Exception as e:
            logger.debug(f"Validator cost estimate failed for {symbol or 'default'}: {e}")
            self._validator_snapshot = {"symbol": symbol, "error": str(e)}
            return (((profit_target_usd / trade_value) * 100) if trade_value > 0 else 0.0), 0.0

    def _cognition_key(self, pair: str, side: str) -> str:
        return f"{pair}|{side}".lower()

    def _build_candidate_cognition_context(
        self,
        *,
        info: MarginPairInfo,
        side: str,
        required_move_pct: float,
        eta_minutes: float,
        goal_score: float,
        route_to_profit: float,
        profit_target_usd: float,
        projection: Optional[dict] = None,
        timeline: Optional[dict] = None,
        alignment: Optional[dict] = None,
    ) -> Dict[str, Any]:
        projection = projection or {}
        timeline = timeline or {}
        alignment = alignment or {}
        projection_conf = float(projection.get("confidence", 0.0) or 0.0)
        live_match = float(projection.get("live_match", 0.0) or 0.0)
        timeline_conf = float(timeline.get("confidence", 0.0) or 0.0)
        alignment_score = max(0.0, min(1.0, (float(alignment.get("score", 0.0) or 0.0) + 2.0) / 4.0))
        goal_conf = max(0.0, min(1.0, float(goal_score or 0.0) / 3.5))
        confidence = max(0.05, min(0.99, (
            projection_conf + live_match + timeline_conf + alignment_score + goal_conf
        ) / 5.0))
        return {
            "pair": info.pair,
            "side": side,
            "ticker_symbol": info.binance_symbol,
            "required_move_pct": float(required_move_pct or 0.0),
            "eta_minutes": float(eta_minutes or 0.0),
            "goal_score": float(goal_score or 0.0),
            "route_to_profit": float(route_to_profit or 0.0),
            "profit_target_usd": float(profit_target_usd or 0.0),
            "confidence": confidence,
            "probability": max(0.05, min(0.99, 0.35 + confidence * 0.55)),
            "reason": (
                f"required_move={required_move_pct:.3f}% "
                f"eta={eta_minutes:.2f}m goal={goal_score:.2f} "
                f"timeline={timeline.get('action', 'hold')} "
                f"projection={projection.get('side', side)}"
            ),
            "sources": {
                "projection": projection,
                "timeline": timeline,
                "alignment": alignment,
                "goal_score": float(goal_score or 0.0),
                "route_to_profit": float(route_to_profit or 0.0),
            },
        }

    def _build_trade_cognition_plan(
        self,
        *,
        pair_info: MarginPairInfo,
        side: str,
        entry_price: float,
        target_price: float,
        trade_value: float,
        profit_target_usd: float,
        cognition_context: Optional[dict] = None,
    ) -> dict:
        if getattr(self, "temporal_cognition", None) is None:
            return {}
        ctx = dict(cognition_context or {})
        required_move_pct = float(ctx.get("required_move_pct", 0.0) or 0.0)
        if required_move_pct <= 0 and trade_value > 0:
            required_move_pct, _, _ = self._estimate_required_move_pct(
                trade_value, profit_target_usd, symbol=pair_info.pair
            )
        plan = self.temporal_cognition.plan_trade(
            pair=pair_info.pair,
            side=side,
            ticker_symbol=pair_info.binance_symbol,
            entry_price=entry_price,
            target_price=target_price,
            required_move_pct=required_move_pct,
            profit_target_usd=profit_target_usd,
            eta_minutes=ctx.get("eta_minutes"),
            confidence=float(ctx.get("confidence", 0.5) or 0.5),
            probability=ctx.get("probability"),
            reason=str(ctx.get("reason", "margin entry projection")),
            sources=ctx.get("sources", ctx),
        )
        self._latest_trade_cognition = plan
        self._publish_trade_cognition("trade.cognition.plan", plan)
        return plan

    def _verify_trade_cognition(
        self,
        trade: ActiveTrade,
        current_price: float,
        validated_net_pnl: float,
    ) -> dict:
        plan = dict(getattr(trade, "cognition_plan", {}) or {})
        if not plan or getattr(self, "temporal_cognition", None) is None:
            return {}
        verification = self.temporal_cognition.verify(
            plan,
            current_price=current_price,
            validated_net_pnl=validated_net_pnl,
        )
        trade.cognition_plan = self.temporal_cognition.with_verification(plan, verification)
        self._latest_trade_cognition = trade.cognition_plan
        order_id = str(getattr(trade, "order_id", "") or "")
        if not hasattr(self, "_last_cognition_status"):
            self._last_cognition_status = {}
        previous = self._last_cognition_status.get(order_id)
        status = str(verification.get("status", ""))
        if status and status != previous:
            self._last_cognition_status[order_id] = status
            logger.info(
                f"[CognitionTime] {trade.pair} {trade.side.upper()} "
                f"status={status} progress={verification.get('price_progress', 0):.2f} "
                f"time={verification.get('time_progress', 0):.2f} "
                f"due_in={verification.get('seconds_to_eta', 0):.0f}s"
            )
            self._publish_trade_cognition("trade.cognition.verify", verification)
        return verification

    def _publish_trade_cognition(self, topic: str, payload: dict) -> None:
        thought_bus = getattr(self, "thought_bus", None)
        if thought_bus is None or Thought is None or not payload:
            return
        try:
            thought_bus.publish(Thought(
                source="kraken_margin_trader",
                topic=topic,
                payload=payload,
                meta={"mode": "kraken_margin"},
            ))
        except Exception as e:
            logger.debug(f"Trade cognition publish failed: {e}")

    def _candidate_brain_payload(self, item: Tuple, cognition_context: Optional[dict] = None) -> Dict[str, Any]:
        """Convert the ranked candidate tuple into the brain's stable contract."""
        info, side, _vol, trade_val, lev, score, req, fees, goal_score, eta, route = item
        ctx = cognition_context or {}
        return {
            "pair": getattr(info, "pair", ""),
            "side": side,
            "score": float(score or 0.0),
            "required_move_pct": float(req or 0.0),
            "estimated_fees": float(fees or 0.0),
            "goal_score": float(goal_score or 0.0),
            "eta_minutes": float(eta or 0.0),
            "route_to_profit": float(route or 0.0),
            "spread_pct": float(getattr(info, "spread_pct", 0.0) or 0.0),
            "momentum_pct": float(getattr(info, "momentum", 0.0) or 0.0),
            "leverage": int(lev or 0),
            "trade_value": float(trade_val or 0.0),
            "profit_target_usd": float(ctx.get("profit_target_usd", 0.0) or 0.0),
        }

    def _apply_brain_gate_to_candidates(self, candidates: List[Tuple]) -> List[Tuple]:
        """Apply the legacy signal brain and unified margin brain gates."""
        if getattr(self, "signal_brain", None) is None or not candidates:
            gated = candidates
            brain_snapshot: Dict[str, Any] = {}
        else:
            population_scores = [float(item[5]) for item in candidates]
            gated: List[Tuple] = []
            brain_snapshot: Dict[str, Any] = {}
            for item in candidates:
                info, side, vol, trade_val, lev, score, req, fees, gs, eta, route = item
                threshold = max(0.05, min(2.0, abs(float(info.momentum)) or 0.05))
                features = {
                    "momentum": float(info.momentum),
                    "volatility": max(float(info.spread_pct), float(req) / 4.0, 0.0001),
                    "trend_strength": min(abs(float(info.momentum)) / threshold, 1.0),
                    "rsi": 50.0 + max(-40.0, min(40.0, float(info.momentum) * 8.0)),
                }
                try:
                    decision = self.signal_brain.decide(
                        symbol=info.pair,
                        base_score=float(score),
                        features=features,
                        population_scores=population_scores,
                    )
                except Exception as e:
                    brain_snapshot[info.pair] = {"error": str(e)}
                    gated.append(item)
                    continue

                if decision is None:
                    brain_snapshot[info.pair] = {"decision": "rejected"}
                    continue

                brain_snapshot[info.pair] = {
                    "decision": "accepted",
                    "score": float(decision.score),
                    "coherence": float(decision.coherence),
                }
                gated.append((info, side, vol, trade_val, lev, float(decision.score), req, fees, gs, eta, route))

        margin_brain = getattr(self, "margin_decision_brain", None)
        if margin_brain is None or not gated:
            self._brain_snapshot = brain_snapshot
            return gated

        final_gated: List[Tuple] = []
        margin_decisions: Dict[str, Any] = {}
        population_scores = [float(item[5]) for item in gated]
        for item in gated:
            info, side, vol, trade_val, lev, score, req, fees, gs, eta, route = item
            key = self._cognition_key(getattr(info, "pair", ""), side)
            ctx = dict(getattr(self, "_candidate_cognition_context", {}).get(key, {}) or {})
            payload = self._candidate_brain_payload(item, ctx)
            try:
                decision = margin_brain.evaluate_candidate(
                    payload,
                    cognition_context=ctx,
                    population_scores=population_scores,
                )
            except Exception as e:
                brain_snapshot.setdefault(info.pair, {})["unified_margin_brain"] = {"error": str(e)}
                final_gated.append(item)
                continue

            decision_dict = decision.to_dict()
            margin_decisions[info.pair] = decision_dict
            brain_snapshot.setdefault(info.pair, {})["unified_margin_brain"] = decision_dict
            ctx["brain_decision"] = decision_dict
            ctx["confidence"] = max(float(ctx.get("confidence", 0.0) or 0.0), float(decision.confidence))
            ctx["probability"] = max(float(ctx.get("probability", 0.0) or 0.0), float(decision.probability))
            self._candidate_cognition_context[key] = ctx
            self._publish_trade_cognition("brain.margin.decision", decision_dict)

            if not decision.approved:
                logger.debug(
                    f"[MarginBrain] {info.pair} {side.upper()} waiting: "
                    f"{'; '.join(decision.vetoes) or 'not enough support'}"
                )
                continue

            final_gated.append((
                info, side, vol, trade_val, lev,
                float(decision.adjusted_score), req, fees, gs, eta, route
            ))

        self._margin_brain_decisions = margin_decisions
        self._brain_snapshot = brain_snapshot
        return final_gated

    def _validated_net_pnl(self, symbol: str, exit_value: float, net_pnl: float) -> float:
        """Apply extra slippage/spread buffer to reported net P&L when available."""
        if self.trade_profit_validator is None or exit_value <= 0:
            return net_pnl
        try:
            costs = self.trade_profit_validator.get_exchange_costs(
                "kraken",
                exit_value,
                is_taker=True,
                symbol=symbol,
            )
            exit_buffer = float(costs.get("slippage", 0.0) or 0.0) + float(costs.get("spread", 0.0) or 0.0)
            return net_pnl - exit_buffer
        except Exception:
            return net_pnl

    def _refresh_unified_intel_snapshot(self) -> None:
        """Capture high-level registry/decision-engine state without changing trade logic."""
        snapshot: Dict[str, Any] = {}
        if self.unified_registry is not None:
            try:
                snapshot["categories"] = self.unified_registry.get_category_summary()
                snapshot["chain_flow"] = self.unified_registry.get_chain_flow()
            except Exception as e:
                snapshot["error"] = str(e)
        self._registry_snapshot = snapshot
        self._refresh_new_intel_snapshots()
        self._refresh_thought_bus_snapshot()

    def _refresh_new_intel_snapshots(self) -> None:
        """Refresh cached state for systems that benefit from periodic updates."""
        # Global financial feed snapshot (macro data, refreshes slowly)
        if self.global_financial_feed is not None:
            try:
                snap = self.global_financial_feed.get_snapshot()
                if snap is not None:
                    self._global_financial_snapshot["macro"] = snap.to_dict() if hasattr(snap, 'to_dict') else str(snap)
            except Exception:
                pass
        # Reality detector snapshot
        if self.reality_detector is not None:
            try:
                permitted, reason, confidence = self.reality_detector.get_trading_permission()
                self._reality_detector_snapshot["permitted"] = permitted
                self._reality_detector_snapshot["reason"] = reason
                self._reality_detector_snapshot["confidence"] = confidence
            except Exception:
                pass
        # Schumann resonance (slow-changing earth data)
        if self.schumann_bridge is not None:
            try:
                from aureon.harmonic.aureon_schumann_resonance_bridge import get_earth_blessing
                blessing_score, blessing_label = get_earth_blessing()
                self._schumann_snapshot["coherence"] = float(blessing_score)
                self._schumann_snapshot["blessing"] = blessing_label
            except Exception:
                pass
        # Phase transition detector needs continuous feeding but status can be cached
        if self.phase_transition_detector is not None:
            try:
                status = self.phase_transition_detector.get_status()
                self._phase_transition_snapshot["state"] = status.get("phase_state", "UNKNOWN")
                self._phase_transition_snapshot["score"] = status.get("transition_score", 0.0)
            except Exception:
                pass

    def _refresh_thought_bus_snapshot(self) -> None:
        if self.thought_bus is None:
            self._thought_bus_snapshot = {}
            self._cognition_snapshot = {}
            return
        try:
            market_events = self.thought_bus.recall("market.", limit=8)
            decision_events = self.thought_bus.recall("decisions.", limit=8)
            cognition_events = self.thought_bus.recall("brain.", limit=8)
            queen_events = self.thought_bus.recall("queen.", limit=8)
            self._thought_bus_snapshot = {
                "market_events": len(market_events),
                "decision_events": len(decision_events),
                "latest_market_topic": (market_events[-1].get("topic") if market_events else ""),
                "latest_decision_topic": (decision_events[-1].get("topic") if decision_events else ""),
            }
            self._cognition_snapshot = {
                "cognition_events": len(cognition_events),
                "queen_events": len(queen_events),
                "latest_cognition_topic": (cognition_events[-1].get("topic") if cognition_events else ""),
                "latest_queen_topic": (queen_events[-1].get("topic") if queen_events else ""),
            }
        except Exception as e:
            self._thought_bus_snapshot = {"error": str(e)}
            self._cognition_snapshot = {"error": str(e)}

    def _publish_market_snapshot_to_thought_bus(self) -> None:
        if self.thought_bus is None or Thought is None:
            return
        try:
            candidates = list(getattr(self, "_last_candidates", []) or [])[:7]
            market_by_symbol: Dict[str, Dict[str, Any]] = {}
            universe: List[str] = []
            for item in candidates:
                info, side, _vol, trade_val, lev, score, req, fees, goal_score, eta, route = item
                symbol = str(info.pair).upper()
                universe.append(symbol)
                market_by_symbol[symbol] = {
                    "momentum": float(info.momentum),
                    "spread_pct": float(info.spread_pct),
                    "score": float(score),
                    "direction": str(side).upper(),
                    "trade_value": float(trade_val),
                    "leverage": int(lev),
                    "required_move_pct": float(req),
                    "estimated_fees": float(fees),
                    "goal_score": float(goal_score),
                    "eta_to_target": float(eta),
                    "route_to_profit": float(route),
                }
            if not universe:
                return
            self.thought_bus.publish(Thought(
                source="kraken_margin_trader",
                topic="market.snapshot",
                payload={
                    "venue": "kraken",
                    "universe": universe,
                    "market_by_symbol": market_by_symbol,
                    "capital": self._get_capital_snapshot(),
                },
                meta={"mode": "kraken_margin"},
            ))
        except Exception as e:
            logger.debug(f"Kraken ThoughtBus publish failed: {e}")

    def _feed_unified_decision_engine(self, symbol: str, side: str, score: float = 0.5, metadata: Optional[dict] = None) -> None:
        """Publish trader candidate signals into the unified decision engine for auditability."""
        if self.unified_decision_engine is None or SignalInput is None:
            return
        try:
            direction = "bullish" if side.lower() == "buy" else "bearish"
            self.unified_decision_engine.add_signal(
                SignalInput(
                    source="kraken_margin_trader",
                    symbol=symbol,
                    direction=direction,
                    strength=max(0.0, min(1.0, score)),
                    metadata=metadata or {},
                )
            )
            if CoordinationInput is not None:
                self.unified_decision_engine.set_coordination_state(
                    CoordinationInput(
                        orca_ready=True,
                        all_systems_ready=1,
                        total_systems=1,
                        blockers=[],
                    )
                )
            decision = None
            if DecisionType is not None and DecisionReason is not None:
                decision = self.unified_decision_engine.generate_decision(
                    symbol,
                    DecisionType.BUY if side.lower() == "buy" else DecisionType.SELL,
                    DecisionReason.SIGNAL_STRENGTH,
                )
            self._decision_snapshot = {
                "symbol": symbol,
                "side": side.upper(),
                "score": score,
                "decision": {
                    "type": decision.decision_type.value,
                    "confidence": decision.confidence,
                    "reason": decision.reason.value,
                } if decision else None,
            }
        except Exception as e:
            self._decision_snapshot = {"error": str(e), "symbol": symbol, "side": side.upper()}

    def _score_harmonic_margin_scanner(
        self,
        symbol: str,
        side: str,
        current_price: float,
        momentum_pct: float,
        required_pct: float,
        leverage: int,
    ) -> dict:
        """Use the harmonic margin scanner as a directional/coherence bonus layer."""
        result = {
            "bonus": 0.0,
            "signal": "OFF",
            "confidence": 0.0,
            "coherence": 0.0,
        }
        if self.margin_harmonic_scanner is None:
            return result
        try:
            approx_pnl_pct = momentum_pct if side == "buy" else -momentum_pct
            approx_pnl_usd = required_pct * leverage
            self.margin_harmonic_scanner.process_tick(
                price=current_price,
                pnl_usd=approx_pnl_usd,
                pnl_pct=approx_pnl_pct,
                margin_level=300.0,
            )
            signal = self.margin_harmonic_scanner.get_probability_signal(symbol=symbol) or {}
            scanner_side = str(signal.get("signal", "HOLD")).upper()
            confidence = float(signal.get("confidence", 0.0) or 0.0)
            coherence = float(signal.get("coherence", signal.get("global_coherence", 0.0)) or 0.0)
            bonus = max(-1.0, min(2.0, (confidence - 0.5) * 3.0 + (coherence - 0.5) * 2.0))
            expected = "LONG" if side == "buy" else "SHORT"
            if scanner_side == expected:
                bonus += 0.75
            elif scanner_side not in {"HOLD", "OFF"}:
                bonus -= 1.0
            result.update({
                "bonus": bonus,
                "signal": scanner_side,
                "confidence": confidence,
                "coherence": coherence,
            })
            self._harmonic_snapshot = {
                "symbol": symbol,
                "side": side.upper(),
                "signal": scanner_side,
                "confidence": confidence,
                "coherence": coherence,
                "bonus": bonus,
            }
        except Exception as e:
            self._harmonic_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_quantum_mirror_scanner(
        self,
        symbol: str,
        side: str,
        current_price: float,
        momentum_pct: float,
        spread_pct: float,
    ) -> dict:
        """Use the quantum mirror scanner as a branch-probability bonus layer."""
        result = {
            "bonus": 0.0,
            "branch_score": 0.0,
            "coherence": 0.0,
            "beneficial_probability": 0.0,
        }
        if self.quantum_mirror_scanner is None:
            return result
        try:
            branch = self.quantum_mirror_scanner.register_branch(symbol, "kraken", initial_price=current_price)
            frequency = 432.0 + momentum_pct * 10.0
            phase = 0.0 if side == "buy" else 3.14159
            self.quantum_mirror_scanner.update_branch(
                branch.branch_id,
                price=current_price,
                frequency=frequency,
                phase=phase,
            )
            p1 = self.quantum_mirror_scanner.validation_pass_1_harmonic(branch.branch_id)
            p2 = self.quantum_mirror_scanner.validation_pass_2_coherence(branch.branch_id)
            p3 = self.quantum_mirror_scanner.validation_pass_3_stability(branch.branch_id)
            details = self.quantum_mirror_scanner.get_branch_details(branch.branch_id) or {}
            branch_score = float(details.get("branch_score", 0.0) or 0.0)
            coherence = float(details.get("coherence_score", 0.0) or 0.0)
            beneficial_probability = float(details.get("beneficial_probability", 0.0) or 0.0)
            bonus = (
                max(-1.0, min(2.5, branch_score * 2.5))
                + max(-0.5, min(1.5, (coherence - 0.5) * 3.0))
                + max(-0.5, min(1.5, (beneficial_probability - 0.5) * 3.0))
                + max(-0.25, min(0.25, (0.3 - spread_pct) * 0.5))
            )
            result.update({
                "bonus": bonus,
                "branch_score": branch_score,
                "coherence": coherence,
                "beneficial_probability": beneficial_probability,
            })
            self._quantum_snapshot = {
                "symbol": symbol,
                "side": side.upper(),
                "p1": p1,
                "p2": p2,
                "p3": p3,
                "branch_score": branch_score,
                "coherence": coherence,
                "beneficial_probability": beneficial_probability,
                "bonus": bonus,
            }
        except Exception as e:
            self._quantum_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_timeline_oracle(
        self,
        symbol: str,
        side: str,
        current_price: float,
        volume: float,
        change_pct: float,
    ) -> dict:
        """Use timeline approval as a directional confidence overlay."""
        result = {
            "bonus": 0.0,
            "action": "hold",
            "confidence": 0.0,
            "reason": "",
        }
        if self.timeline_oracle is None:
            return result
        try:
            action, confidence, reason = self.timeline_oracle.get_approved_action(
                symbol=symbol,
                price=current_price,
                volume=volume,
                change_pct=change_pct,
            )
            action_value = getattr(action, "value", "hold") if action is not None else "hold"
            confidence = float(confidence or 0.0)
            expected = "buy" if side == "buy" else "sell"
            bonus = (confidence - 0.5) * 3.0
            if action_value == expected:
                bonus += 0.75
            elif action_value not in {"hold", "wait"}:
                bonus -= 1.0
            result.update({
                "bonus": max(-1.5, min(2.5, bonus)),
                "action": action_value,
                "confidence": confidence,
                "reason": str(reason or ""),
            })
            self._timeline_snapshot = {
                "symbol": symbol,
                "side": side.upper(),
                "action": action_value.upper(),
                "confidence": confidence,
                "reason": str(reason or ""),
                "bonus": result["bonus"],
            }
        except Exception as e:
            self._timeline_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_harmonic_fusion(self, symbol: str, side: str) -> dict:
        """Use harmonic fusion global and symbol phase as an alignment bonus."""
        result = {
            "bonus": 0.0,
            "global_coherence": 0.0,
            "symbol_coherence": 0.0,
            "phase_alignment": 0.0,
        }
        if self.harmonic_fusion is None:
            return result
        try:
            state = self.harmonic_fusion.get_harmonic_state() or {}
            phase = self.harmonic_fusion.get_symbol_phase(symbol) or {}
            global_coh = float(state.get("global_coherence", 0.0) or 0.0)
            symbol_coh = float(phase.get("coherence", phase.get("amplitude", 0.0)) or 0.0)
            raw_phase = float(phase.get("phase", 0.0) or 0.0)
            directional_phase = math.cos(raw_phase)
            if side == "sell":
                directional_phase *= -1.0
            phase_alignment = max(-1.0, min(1.0, directional_phase))
            bonus = (
                max(-0.75, min(1.5, (global_coh - 0.5) * 2.5))
                + max(-0.75, min(1.5, (symbol_coh - 0.5) * 2.5))
                + phase_alignment * 0.75
            )
            result.update({
                "bonus": max(-2.0, min(3.0, bonus)),
                "global_coherence": global_coh,
                "symbol_coherence": symbol_coh,
                "phase_alignment": phase_alignment,
            })
            self._fusion_snapshot = {
                "symbol": symbol,
                "side": side.upper(),
                "global_coherence": global_coh,
                "symbol_coherence": symbol_coh,
                "phase_alignment": phase_alignment,
                "bonus": result["bonus"],
            }
        except Exception as e:
            self._fusion_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_whale_orderbook(
        self,
        symbol: str,
        side: str,
        current_price: float,
        spread_pct: float,
    ) -> dict:
        """Use whale orderbook pressure as a support/blocker bonus layer."""
        result = {
            "bonus": 0.0,
            "wall_count": 0,
            "layering_score": 0.0,
            "depth_imbalance": 0.0,
        }
        if self.whale_orderbook is None:
            return result
        try:
            analysis = self.whale_orderbook.analyze_symbol(symbol) or {}
            walls = analysis.get("walls", []) or []
            layering_score = float(analysis.get("layering_score", 0.0) or 0.0)
            bids_depth = float(analysis.get("bids_depth", 0.0) or 0.0)
            asks_depth = float(analysis.get("asks_depth", 0.0) or 0.0)
            total_depth = bids_depth + asks_depth
            depth_imbalance = ((bids_depth - asks_depth) / total_depth) if total_depth > 0 else 0.0
            support = 0
            blocking = 0
            for wall in walls:
                wall_side = str(wall.get("side", "")).lower()
                wall_price = float(wall.get("price", current_price) or current_price)
                if side == "buy":
                    if wall_side == "bid" and wall_price <= current_price:
                        support += 1
                    elif wall_side == "ask" and wall_price >= current_price:
                        blocking += 1
                else:
                    if wall_side == "ask" and wall_price >= current_price:
                        support += 1
                    elif wall_side == "bid" and wall_price <= current_price:
                        blocking += 1
            directional_imbalance = depth_imbalance if side == "buy" else -depth_imbalance
            bonus = (
                support * 0.35
                - blocking * 0.45
                + max(-0.75, min(0.75, layering_score))
                + max(-1.0, min(1.0, directional_imbalance * 1.5))
                + max(-0.25, min(0.25, (0.3 - spread_pct) * 0.5))
            )
            result.update({
                "bonus": max(-2.0, min(2.5, bonus)),
                "wall_count": len(walls),
                "layering_score": layering_score,
                "depth_imbalance": depth_imbalance,
            })
            self._whale_snapshot = {
                "symbol": symbol,
                "side": side.upper(),
                "wall_count": len(walls),
                "layering_score": layering_score,
                "depth_imbalance": depth_imbalance,
                "support_walls": support,
                "blocking_walls": blocking,
                "bonus": result["bonus"],
            }
        except Exception as e:
            self._whale_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _refresh_live_tv_cache(self) -> None:
        """Tail the Live TV JSONL feed into a latest-per-symbol cache."""
        try:
            if not self.live_tv_log_path.exists():
                return
            with self.live_tv_log_path.open("r", encoding="utf-8", errors="replace") as handle:
                handle.seek(self._live_tv_tail_offset)
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except Exception:
                        continue
                    symbol = str(payload.get("symbol", "")).upper()
                    if not symbol:
                        continue
                    self._live_tv_symbol_cache[symbol] = payload
                self._live_tv_tail_offset = handle.tell()
        except Exception:
            pass

    def _score_live_tv_station(
        self,
        symbol: str,
        side: str,
        fallback_momentum: float,
    ) -> dict:
        """Use Live TV truth-feed output as a passive market-context overlay."""
        result = {
            "bonus": 0.0,
            "change_24h": 0.0,
            "momentum": 0.0,
            "volatility": 0.0,
            "hz": 0.0,
            "label": "OFF",
        }
        try:
            self._refresh_live_tv_cache()
            payload = self._live_tv_symbol_cache.get(str(symbol or "").upper())
            if not payload:
                return result
            change_24h = float(payload.get("change_24h", 0.0) or 0.0)
            momentum = float(payload.get("momentum", fallback_momentum) or fallback_momentum or 0.0)
            volatility = float(payload.get("volatility", 0.0) or 0.0)
            hz = float(payload.get("hz", 0.0) or 0.0)
            label = str(payload.get("hz_label", payload.get("type", "LIVE_TV")) or "LIVE_TV")
            directional_signal = momentum if abs(momentum) > 0.0001 else change_24h / 8.0
            aligned = (directional_signal >= 0 and side == "buy") or (directional_signal < 0 and side == "sell")
            bonus = min(1.75, abs(directional_signal) * 0.8 + volatility * 4.0)
            if aligned:
                bonus += 0.35
            else:
                bonus *= -0.6
            result.update({
                "bonus": max(-1.5, min(2.25, bonus)),
                "change_24h": change_24h,
                "momentum": momentum,
                "volatility": volatility,
                "hz": hz,
                "label": label,
            })
            self._live_tv_snapshot = {
                "symbol": str(symbol).upper(),
                "side": side.upper(),
                "change_24h": change_24h,
                "momentum": momentum,
                "volatility": volatility,
                "hz": hz,
                "label": label,
                "bonus": result["bonus"],
            }
        except Exception as e:
            self._live_tv_snapshot = {"symbol": str(symbol).upper(), "error": str(e)}
        return result

    def _score_ocean_wave_scanner(self, symbol: str, side: str) -> dict:
        """Use Ocean Wave bot/whale detection as a live microstructure overlay."""
        result = {
            "bonus": 0.0,
            "bots": 0,
            "whales": 0,
            "aggression": 0.0,
        }
        if self.ocean_wave_scanner is None or not self.stream or not self.stream.is_alive():
            return result
        try:
            trades = []
            for price, qty, is_buy, ts in list(self.stream.last_trades.get(symbol, []))[-120:]:
                trades.append({
                    "price": float(price),
                    "quantity": float(qty),
                    "time": float(ts),
                    "is_buyer_maker": not bool(is_buy),
                })
            if len(trades) < 25:
                return result
            detected = self.ocean_wave_scanner._detect_bots_in_trades(trades, symbol, "binance") or []
            if not detected:
                self._ocean_snapshot = {
                    "symbol": str(symbol).upper(),
                    "side": side.upper(),
                    "bots": 0,
                    "whales": 0,
                    "bonus": 0.0,
                }
                return result
            whales = 0
            aggression_sum = 0.0
            bonus = 0.0
            for bot in detected[:5]:
                pattern = str(bot.get("pattern", "")).lower()
                freq = float(bot.get("frequency", 0.0) or 0.0)
                notional = sum(float(t.get("price", 0.0) or 0.0) * float(t.get("quantity", 0.0) or 0.0) for t in bot.get("trades", [])[-25:])
                bias = 1.0 if pattern in {"accumulation", "momentum_burst", "hft"} else 0.0
                if side == "sell":
                    bias *= -1.0
                aggression = min(1.0, freq / 15.0) if freq > 0 else min(1.0, notional / 250000.0)
                aggression_sum += aggression
                if notional >= 100000:
                    whales += 1
                bonus += bias * (0.25 + aggression)
            result.update({
                "bonus": max(-1.5, min(2.25, bonus)),
                "bots": len(detected),
                "whales": whales,
                "aggression": aggression_sum / max(len(detected[:5]), 1),
            })
            self._ocean_snapshot = {
                "symbol": str(symbol).upper(),
                "side": side.upper(),
                "bots": len(detected),
                "whales": whales,
                "aggression": result["aggression"],
                "bonus": result["bonus"],
            }
        except Exception as e:
            self._ocean_snapshot = {"symbol": str(symbol).upper(), "error": str(e)}
        return result

    # ══════════════════════════════════════════════════════════════════════
    #  NEW INTELLIGENCE SCORING METHODS — Tier 1, 2, 3
    # ══════════════════════════════════════════════════════════════════════

    def _score_phase_transition(self, symbol: str, side: str, current_price: float) -> dict:
        """Phase transition detector: penalise entry during CRITICAL regime changes."""
        result = {"bonus": 0.0, "state": "UNKNOWN", "score": 0.0}
        if self.phase_transition_detector is None:
            return result
        try:
            self.phase_transition_detector.ingest(current_price)
            # get_status() runs predict() internally — one call, not two, or the
            # detector's state transitions fire twice per scoring pass. The real
            # keys are state / current_prediction / navigation_signal; the old
            # phase_state / transition_score reads left state pinned at UNKNOWN
            # since this scorer shipped.
            status = self.phase_transition_detector.get_status()
            state = str(status.get("state", "UNKNOWN"))
            pred = status.get("current_prediction") or {}
            t_score = float(pred.get("probability", 0.0) or 0.0)
            nav = str(status.get("navigation_signal", "HOLD")).lower()
            bonus = 0.0
            if state == "STABLE":
                bonus += 0.5
            elif state == "ELEVATED":
                bonus -= 0.25
            elif state == "CRITICAL":
                bonus -= 1.5
            elif state == "RECOVERY":
                bonus += 0.25
            # navigation_signal speaks enter/exit; side speaks buy/sell — the
            # old direct comparison could never match.
            nav_side = {"enter": "buy", "exit": "sell"}.get(nav, nav)
            if nav_side == side:
                bonus += 0.5
            elif nav_side not in {"hold", "unknown", ""}:
                bonus -= 0.5
            result.update({"bonus": max(-2.0, min(2.0, bonus)), "state": state, "score": t_score})
            self._phase_transition_snapshot = {"symbol": symbol, "state": state, "score": t_score, "nav": nav, "bonus": result["bonus"]}
        except Exception as e:
            self._phase_transition_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_prob_ultimate(self, symbol: str, side: str, current_price: float, momentum_pct: float) -> dict:
        """Probability Ultimate Intelligence: 95% accuracy pattern-based prediction."""
        result = {"bonus": 0.0, "win_rate": 0.0, "pattern": ""}
        if self.prob_ultimate is None:
            return result
        try:
            signals = self.prob_ultimate.get_pattern_signals(
                symbol=symbol, current_price=current_price, momentum=momentum_pct / 100.0
            ) if hasattr(self.prob_ultimate, 'get_pattern_signals') else {}
            if not signals:
                return result
            win_rate = float(signals.get("win_rate", 0.5) or 0.5)
            pattern = str(signals.get("pattern_key", "") or "")
            direction = str(signals.get("direction", "neutral") or "neutral").lower()
            bonus = (win_rate - 0.5) * 4.0
            if direction == side or (direction == "bullish" and side == "buy") or (direction == "bearish" and side == "sell"):
                bonus += 0.5
            elif direction not in {"neutral", "flat", ""}:
                bonus -= 0.5
            result.update({"bonus": max(-2.0, min(2.0, bonus)), "win_rate": win_rate, "pattern": pattern})
            self._prob_ultimate_snapshot = {"symbol": symbol, "win_rate": win_rate, "pattern": pattern, "bonus": result["bonus"]}
        except Exception as e:
            self._prob_ultimate_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_news_signal(self, symbol: str, side: str) -> dict:
        """News signal: sentiment-based directional bias from live news."""
        result = {"bonus": 0.0, "sentiment": 0.0, "headline_count": 0}
        if not HAS_NEWS_SIGNAL or get_news_signal is None:
            return result
        try:
            news = get_news_signal()
            if news is None:
                return result
            sentiment = float(getattr(news, 'sentiment_score', 0.0) or 0.0)
            count = int(getattr(news, 'article_count', 0) or 0)
            bonus = sentiment * 1.5
            if (sentiment > 0 and side == "sell") or (sentiment < 0 and side == "buy"):
                bonus *= -0.5
            result.update({"bonus": max(-1.5, min(1.5, bonus)), "sentiment": sentiment, "headline_count": count})
            self._news_signal_snapshot = {"symbol": symbol, "sentiment": sentiment, "count": count, "bonus": result["bonus"]}
        except Exception as e:
            self._news_signal_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_phantom_filter(self, symbol: str, side: str) -> dict:
        """Phantom signal filter: penalise signals that appear in only one reality layer."""
        result = {"bonus": 0.0, "verified": False, "layers": 0}
        if self.phantom_filter is None:
            return result
        try:
            status = {}
            if hasattr(self.phantom_filter, 'get_signal_status'):
                status = self.phantom_filter.get_signal_status(symbol) or {}
            elif hasattr(self.phantom_filter, 'check_signal'):
                status = self.phantom_filter.check_signal(symbol) or {}
            verified = bool(status.get("verified", False))
            layers = int(status.get("layers_confirmed", 0) or 0)
            bonus = 0.0
            if verified:
                bonus = min(layers * 0.5, 2.0)
            elif layers == 0:
                bonus = 0.0
            else:
                bonus = -0.5
            result.update({"bonus": bonus, "verified": verified, "layers": layers})
            self._phantom_filter_snapshot = {"symbol": symbol, "verified": verified, "layers": layers, "bonus": bonus}
        except Exception as e:
            self._phantom_filter_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_global_financial(self, symbol: str, side: str) -> dict:
        """Global financial feed: macro ecosystem probability adjustment."""
        result = {"bonus": 0.0, "signal": "neutral", "probability": 0.5}
        if self.global_financial_feed is None:
            return result
        try:
            sig = self.global_financial_feed.get_trading_signal(symbol) or {}
            direction = str(sig.get("signal", "neutral") or "neutral").lower()
            probability = float(sig.get("probability", 0.5) or 0.5)
            strength = float(sig.get("strength", 0.0) or 0.0)
            bonus = (probability - 0.5) * 3.0 + strength * 0.5
            if (direction in {"bullish", "buy"} and side == "sell") or (direction in {"bearish", "sell"} and side == "buy"):
                bonus *= -0.5
            result.update({"bonus": max(-2.0, min(2.0, bonus)), "signal": direction, "probability": probability})
            self._global_financial_snapshot = {"symbol": symbol, "signal": direction, "prob": probability, "bonus": result["bonus"]}
        except Exception as e:
            self._global_financial_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_whale_behavior(self, symbol: str, side: str) -> dict:
        """Whale behavior predictor: predict next whale move direction."""
        result = {"bonus": 0.0, "prediction": "neutral", "confidence": 0.0}
        if self.whale_behavior_predictor is None:
            return result
        try:
            pred = self.whale_behavior_predictor.predict_next_move(symbol) if hasattr(self.whale_behavior_predictor, 'predict_next_move') else {}
            if not pred:
                return result
            direction = str(pred.get("direction", "neutral") or "neutral").lower()
            confidence = float(pred.get("confidence", 0.0) or 0.0)
            bonus = confidence * 2.0
            if (direction in {"buy", "bullish", "accumulate"} and side == "buy") or (direction in {"sell", "bearish", "distribute"} and side == "sell"):
                bonus = abs(bonus)
            elif direction not in {"neutral", "unknown", ""}:
                bonus = -abs(bonus) * 0.5
            result.update({"bonus": max(-1.5, min(2.0, bonus)), "prediction": direction, "confidence": confidence})
            self._whale_behavior_snapshot = {"symbol": symbol, "direction": direction, "confidence": confidence, "bonus": result["bonus"]}
        except Exception as e:
            self._whale_behavior_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_kraken_signal_bridge(self, symbol: str, side: str, current_price: float) -> dict:
        """Kraken unified signal bridge: synthesised multi-source Kraken signal."""
        result = {"bonus": 0.0, "strength": "NEUTRAL", "confidence": 0.0}
        if self.kraken_signal_bridge is None:
            return result
        try:
            decision = None
            if hasattr(self.kraken_signal_bridge, 'synthesize_unified_decision'):
                signals = []
                if hasattr(self.kraken_signal_bridge, 'parse_kraken_trade_analysis'):
                    sig = self.kraken_signal_bridge.parse_kraken_trade_analysis(
                        symbol=symbol, price=current_price, side=side
                    )
                    if sig:
                        signals.append(sig)
                if signals:
                    decision = self.kraken_signal_bridge.synthesize_unified_decision(signals)
            if decision is None:
                return result
            strength = str(getattr(decision, 'overall_strength', 'NEUTRAL') or 'NEUTRAL')
            confidence = float(getattr(decision, 'confidence', 0.0) or 0.0)
            direction = str(getattr(decision, 'direction', 'neutral') or 'neutral').lower()
            bonus = confidence * 2.0
            if direction == side or (direction == "bullish" and side == "buy") or (direction == "bearish" and side == "sell"):
                bonus = abs(bonus)
            elif direction not in {"neutral", ""}:
                bonus = -abs(bonus) * 0.5
            if strength in {"STRONG", "VERY_STRONG"}:
                bonus += 0.5
            result.update({"bonus": max(-2.0, min(2.5, bonus)), "strength": strength, "confidence": confidence})
            self._kraken_signal_bridge_snapshot = {"symbol": symbol, "strength": strength, "confidence": confidence, "bonus": result["bonus"]}
        except Exception as e:
            self._kraken_signal_bridge_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_truth_prediction(self, symbol: str, side: str, current_price: float, momentum_pct: float) -> dict:
        """Truth prediction engine: scenario-based directional predictions."""
        result = {"bonus": 0.0, "accuracy": 0.0, "prediction": ""}
        if self.truth_prediction_engine is None:
            return result
        try:
            from aureon.intelligence.aureon_truth_prediction_engine import MarketSnapshot
            snap = MarketSnapshot(
                symbol=symbol, price=current_price, volume=0.0,
                momentum=momentum_pct / 100.0, timestamp=time.time(),
                bid=current_price, ask=current_price, spread_pct=0.0, hz=432.0,
            )
            pred = self.truth_prediction_engine.generate_prediction(snap)
            if pred is None:
                return result
            direction = str(getattr(pred, 'predicted_direction', '') or '').lower()
            confidence = float(getattr(pred, 'confidence', 0.0) or 0.0)
            stats = self.truth_prediction_engine.get_accuracy_stats()
            accuracy = float(stats.get("overall_accuracy", 0.0) or 0.0)
            bonus = (confidence - 0.5) * 3.0
            if (direction in {"up", "bullish", "buy"} and side == "buy") or (direction in {"down", "bearish", "sell"} and side == "sell"):
                bonus = abs(bonus)
            elif direction not in {"flat", "neutral", ""}:
                bonus = -abs(bonus) * 0.5
            if accuracy > 0.6:
                bonus *= 1.0 + (accuracy - 0.6) * 2.0
            result.update({"bonus": max(-2.0, min(2.0, bonus)), "accuracy": accuracy, "prediction": direction})
            self._truth_prediction_snapshot = {"symbol": symbol, "direction": direction, "confidence": confidence, "accuracy": accuracy, "bonus": result["bonus"]}
        except Exception as e:
            self._truth_prediction_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_prob_nexus(self, symbol: str, side: str) -> dict:
        """Enhanced probability nexus: probability bridging signal."""
        result = {"bonus": 0.0, "signal": "neutral"}
        if self.prob_nexus is None:
            return result
        try:
            sig = self.prob_nexus.get_signal() if hasattr(self.prob_nexus, 'get_signal') else None
            if sig is None:
                return result
            if isinstance(sig, dict):
                direction = str(sig.get("direction", "neutral") or "neutral").lower()
                strength = float(sig.get("strength", 0.0) or 0.0)
            else:
                direction = str(getattr(sig, 'direction', 'neutral') or 'neutral').lower()
                strength = float(getattr(sig, 'strength', 0.0) or 0.0)
            bonus = strength * 2.0
            if (direction in {"buy", "bullish"} and side == "sell") or (direction in {"sell", "bearish"} and side == "buy"):
                bonus *= -0.5
            result.update({"bonus": max(-1.5, min(1.5, bonus)), "signal": direction})
            self._prob_nexus_snapshot = {"symbol": symbol, "signal": direction, "strength": strength, "bonus": result["bonus"]}
        except Exception as e:
            self._prob_nexus_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    # ── TIER 2 SCORING ──────────────────────────────────────────────────

    def _score_real_intel(self, symbol: str, side: str) -> dict:
        """Real intelligence engine: bot profiling + whale prediction + momentum."""
        result = {"bonus": 0.0, "validated_count": 0, "momentum_type": ""}
        if self.real_intel_engine is None:
            return result
        try:
            intel = self.real_intel_engine.gather_all_intelligence({}, {}) if hasattr(self.real_intel_engine, 'gather_all_intelligence') else {}
            if not intel:
                return result
            validated = int(intel.get("validated_count", 0) or 0)
            momentum_opps = intel.get("momentum_opportunities", {})
            best_type = str(intel.get("best_momentum_type", "") or "")
            bonus = min(validated * 0.3, 1.5)
            if best_type in {"wolf", "lion"}:
                bonus += 0.5
            result.update({"bonus": max(-1.0, min(2.0, bonus)), "validated_count": validated, "momentum_type": best_type})
            self._real_intel_snapshot = {"symbol": symbol, "validated": validated, "type": best_type, "bonus": result["bonus"]}
        except Exception as e:
            self._real_intel_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_market_organism(self, symbol: str, side: str) -> dict:
        """Market organism: ecosystem health and manipulation detection."""
        result = {"bonus": 0.0, "health": "unknown", "manipulation": False}
        if self.market_organism is None:
            return result
        try:
            report = self.market_organism.sense_ecosystem() if hasattr(self.market_organism, 'sense_ecosystem') else None
            if report is None:
                return result
            health = str(getattr(report, 'health', 'unknown') or 'unknown').lower() if not isinstance(report, dict) else str(report.get('health', 'unknown')).lower()
            manipulated = bool(getattr(report, 'manipulation_detected', False)) if not isinstance(report, dict) else bool(report.get('manipulation_detected', False))
            bonus = 0.0
            if health in {"healthy", "strong"}:
                bonus += 0.5
            elif health in {"sick", "weak", "critical"}:
                bonus -= 0.75
            if manipulated:
                bonus -= 1.0
            result.update({"bonus": max(-1.5, min(1.0, bonus)), "health": health, "manipulation": manipulated})
            self._market_organism_snapshot = {"symbol": symbol, "health": health, "manipulated": manipulated, "bonus": result["bonus"]}
        except Exception as e:
            self._market_organism_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_elephant(self, symbol: str, side: str, current_price: float, momentum_pct: float) -> dict:
        """Elephant learning: long-term pattern memory score for this asset."""
        result = {"bonus": 0.0, "asset_score": 0.0, "hour_ok": True}
        if self.elephant_memory is None:
            return result
        try:
            asset_score = self.elephant_memory.get_asset_score(symbol) if hasattr(self.elephant_memory, 'get_asset_score') else 0.0
            asset_score = float(asset_score or 0.0)
            patterns = {}
            if hasattr(self.elephant_memory, 'get_pattern_signals'):
                patterns = self.elephant_memory.get_pattern_signals(symbol, current_price, momentum_pct / 100.0) or {}
            import datetime as _dt
            current_hour = _dt.datetime.utcnow().hour
            best_hours = self.elephant_memory.get_best_trading_hours() if hasattr(self.elephant_memory, 'get_best_trading_hours') else []
            worst_hours = self.elephant_memory.get_worst_trading_hours() if hasattr(self.elephant_memory, 'get_worst_trading_hours') else []
            hour_ok = current_hour not in worst_hours
            bonus = asset_score * 1.5
            if current_hour in best_hours:
                bonus += 0.3
            if not hour_ok:
                bonus -= 0.5
            pattern_dir = str(patterns.get("direction", "") or "").lower()
            if pattern_dir == side or (pattern_dir == "bullish" and side == "buy") or (pattern_dir == "bearish" and side == "sell"):
                bonus += 0.4
            result.update({"bonus": max(-1.5, min(2.0, bonus)), "asset_score": asset_score, "hour_ok": hour_ok})
            self._elephant_snapshot = {"symbol": symbol, "asset_score": asset_score, "hour_ok": hour_ok, "bonus": result["bonus"]}
        except Exception as e:
            self._elephant_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_advanced_intel(self, symbol: str, side: str) -> dict:
        """Advanced intelligence mycelium network: neural agent consensus."""
        result = {"bonus": 0.0, "consensus": "neutral"}
        if self.advanced_intel is None:
            return result
        try:
            if hasattr(self.advanced_intel, 'get_consensus'):
                consensus = self.advanced_intel.get_consensus(symbol) or {}
            elif hasattr(self.advanced_intel, 'propagate'):
                consensus = {"direction": "neutral"}
            else:
                return result
            direction = str(consensus.get("direction", "neutral") or "neutral").lower()
            confidence = float(consensus.get("confidence", 0.0) or 0.0)
            bonus = confidence * 1.5
            if (direction in {"buy", "bullish"} and side == "sell") or (direction in {"sell", "bearish"} and side == "buy"):
                bonus *= -0.5
            result.update({"bonus": max(-1.0, min(1.5, bonus)), "consensus": direction})
            self._advanced_intel_snapshot = {"symbol": symbol, "direction": direction, "confidence": confidence, "bonus": result["bonus"]}
        except Exception as e:
            self._advanced_intel_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_reality_detector(self, symbol: str, side: str) -> dict:
        """Multiversal reality detector: trading permission and reality class."""
        result = {"bonus": 0.0, "reality": "UNKNOWN", "permitted": True}
        if self.reality_detector is None:
            return result
        try:
            permitted, reason, confidence = self.reality_detector.get_trading_permission()
            reality = str(self.reality_detector.current_reality_class.value) if hasattr(self.reality_detector, 'current_reality_class') else "UNKNOWN"
            bonus = 0.0
            if not permitted:
                bonus = -2.0
            else:
                bonus = confidence * 1.0
            if reality == "PRIME":
                bonus += 0.25
            result.update({"bonus": max(-2.0, min(1.5, bonus)), "reality": reality, "permitted": permitted})
            self._reality_detector_snapshot = {"symbol": symbol, "reality": reality, "permitted": permitted, "confidence": confidence, "bonus": result["bonus"]}
        except Exception as e:
            self._reality_detector_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_global_wave(self, symbol: str, side: str) -> dict:
        """Global wave scanner: wave pattern allocation signal."""
        result = {"bonus": 0.0, "wave_state": "UNKNOWN"}
        if self.global_wave_scanner is None:
            return result
        try:
            alloc = self.global_wave_scanner.get_wave_allocation() if hasattr(self.global_wave_scanner, 'get_wave_allocation') else {}
            if not alloc:
                return result
            wave_state = str(alloc.get("wave_state", "UNKNOWN") or "UNKNOWN")
            attention = float(alloc.get("attention_score", 0.0) or 0.0)
            bonus = attention * 1.0
            if wave_state in {"RISING", "STRONG"}:
                bonus += 0.3 if side == "buy" else -0.2
            elif wave_state in {"FALLING", "WEAK"}:
                bonus += 0.3 if side == "sell" else -0.2
            result.update({"bonus": max(-1.0, min(1.5, bonus)), "wave_state": wave_state})
            self._global_wave_snapshot = {"symbol": symbol, "wave_state": wave_state, "attention": attention, "bonus": result["bonus"]}
        except Exception as e:
            self._global_wave_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_obsidian(self, symbol: str, side: str, current_price: float) -> dict:
        """Obsidian filter: signal purification and noise reduction."""
        result = {"bonus": 0.0, "clarity": 0.0, "shielded": False}
        if self.obsidian_filter is None:
            return result
        try:
            if hasattr(self.obsidian_filter, 'filter_signal'):
                filtered = self.obsidian_filter.filter_signal(current_price) or {}
            elif hasattr(self.obsidian_filter, 'process'):
                filtered = self.obsidian_filter.process(current_price) or {}
            else:
                return result
            clarity = float(filtered.get("clarity", 0.0) or filtered.get("snr", 0.0) or 0.0)
            shielded = bool(filtered.get("shielded", False) or filtered.get("protected", False))
            bonus = (clarity - 0.5) * 2.0
            if shielded:
                bonus -= 0.5
            result.update({"bonus": max(-1.5, min(1.5, bonus)), "clarity": clarity, "shielded": shielded})
            self._obsidian_snapshot = {"symbol": symbol, "clarity": clarity, "shielded": shielded, "bonus": result["bonus"]}
        except Exception as e:
            self._obsidian_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    # ── TIER 3 SCORING ──────────────────────────────────────────────────

    def _score_schumann(self, symbol: str, side: str) -> dict:
        """Schumann resonance: earth coherence as a macro timing overlay."""
        result = {"bonus": 0.0, "coherence": 0.0, "blessing": ""}
        if self.schumann_bridge is None:
            return result
        try:
            from aureon.harmonic.aureon_schumann_resonance_bridge import get_earth_blessing
            blessing_score, blessing_label = get_earth_blessing()
            bonus = (float(blessing_score) - 0.5) * 1.5
            result.update({"bonus": max(-1.0, min(1.0, bonus)), "coherence": float(blessing_score), "blessing": blessing_label})
            self._schumann_snapshot = {"symbol": symbol, "coherence": float(blessing_score), "blessing": blessing_label, "bonus": result["bonus"]}
        except Exception as e:
            self._schumann_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_harmonic_nexus(self, symbol: str, side: str) -> dict:
        """Harmonic nexus bridge: cross-domain anomaly detection."""
        result = {"bonus": 0.0, "anomalies": 0, "coherence": 0.0}
        if self.harmonic_nexus is None:
            return result
        try:
            analysis = None
            if hasattr(self.harmonic_nexus, 'analyze'):
                analysis = self.harmonic_nexus.analyze(symbol) or {}
            elif hasattr(self.harmonic_nexus, 'get_analysis'):
                analysis = self.harmonic_nexus.get_analysis(symbol) or {}
            if not analysis:
                return result
            anomalies = int(analysis.get("anomaly_count", 0) or 0) if isinstance(analysis, dict) else int(getattr(analysis, 'anomaly_count', 0) or 0)
            coherence = float(analysis.get("coherence", 0.0) or 0.0) if isinstance(analysis, dict) else float(getattr(analysis, 'coherence', 0.0) or 0.0)
            bonus = (coherence - 0.5) * 2.0
            if anomalies > 2:
                bonus -= 0.5
            result.update({"bonus": max(-1.0, min(1.5, bonus)), "anomalies": anomalies, "coherence": coherence})
            self._harmonic_nexus_snapshot = {"symbol": symbol, "anomalies": anomalies, "coherence": coherence, "bonus": result["bonus"]}
        except Exception as e:
            self._harmonic_nexus_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_earth_resonance(self, symbol: str, side: str) -> dict:
        """Earth resonance engine: planetary coherence for timing."""
        result = {"bonus": 0.0, "resonance": 0.0}
        if self.earth_resonance is None:
            return result
        try:
            state = None
            if hasattr(self.earth_resonance, 'get_coherence'):
                state = self.earth_resonance.get_coherence()
            elif hasattr(self.earth_resonance, 'get_state'):
                state = self.earth_resonance.get_state()
            if state is None:
                return result
            coherence = float(state.get("coherence", 0.5) or 0.5) if isinstance(state, dict) else float(getattr(state, 'coherence', 0.5) or 0.5)
            bonus = (coherence - 0.5) * 1.5
            result.update({"bonus": max(-0.75, min(1.0, bonus)), "resonance": coherence})
            self._earth_resonance_snapshot = {"symbol": symbol, "resonance": coherence, "bonus": result["bonus"]}
        except Exception as e:
            self._earth_resonance_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_market_harp(self, symbol: str, side: str) -> dict:
        """Market harp: harmonic string resonance across markets."""
        result = {"bonus": 0.0, "ripple": "neutral"}
        if self.market_harp is None:
            return result
        try:
            ripple = None
            if hasattr(self.market_harp, 'get_ripple'):
                ripple = self.market_harp.get_ripple(symbol)
            elif hasattr(self.market_harp, 'pluck'):
                ripple = self.market_harp.pluck(symbol)
            if ripple is None:
                return result
            direction = str(ripple.get("direction", "neutral") or "neutral").lower() if isinstance(ripple, dict) else str(getattr(ripple, 'direction', 'neutral') or 'neutral').lower()
            amplitude = float(ripple.get("amplitude", 0.0) or 0.0) if isinstance(ripple, dict) else float(getattr(ripple, 'amplitude', 0.0) or 0.0)
            bonus = amplitude * 1.0
            if (direction in {"buy", "bullish"} and side == "sell") or (direction in {"sell", "bearish"} and side == "buy"):
                bonus *= -0.5
            result.update({"bonus": max(-0.75, min(1.0, bonus)), "ripple": direction})
            self._market_harp_snapshot = {"symbol": symbol, "ripple": direction, "amplitude": amplitude, "bonus": result["bonus"]}
        except Exception as e:
            self._market_harp_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_crypto_map(self, symbol: str, side: str) -> dict:
        """Crypto market map: sector opportunity and correlation data."""
        result = {"bonus": 0.0, "sector_score": 0.0}
        if self.crypto_map is None:
            return result
        try:
            summary = self.crypto_map.get_map_summary() if hasattr(self.crypto_map, 'get_map_summary') else {}
            if not summary:
                return result
            sector_score = float(summary.get("sector_opportunity", 0.0) or 0.0)
            bonus = sector_score * 1.0
            result.update({"bonus": max(-0.75, min(1.0, bonus)), "sector_score": sector_score})
            self._crypto_map_snapshot = {"symbol": symbol, "sector_score": sector_score, "bonus": result["bonus"]}
        except Exception as e:
            self._crypto_map_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_sensory(self, symbol: str, side: str) -> dict:
        """Sensory framework: multi-sense data fusion."""
        result = {"bonus": 0.0, "experience_quality": 0.0}
        if self.sensory_registry is None:
            return result
        try:
            experience = None
            if hasattr(self.sensory_registry, 'sense'):
                experience = self.sensory_registry.sense(symbol)
            elif hasattr(self.sensory_registry, 'get_experience'):
                experience = self.sensory_registry.get_experience(symbol)
            if experience is None:
                return result
            quality = float(experience.get("quality", 0.5) or 0.5) if isinstance(experience, dict) else float(getattr(experience, 'quality', 0.5) or 0.5)
            bonus = (quality - 0.5) * 1.5
            result.update({"bonus": max(-0.75, min(1.0, bonus)), "experience_quality": quality})
            self._sensory_snapshot = {"symbol": symbol, "quality": quality, "bonus": result["bonus"]}
        except Exception as e:
            self._sensory_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    # ── TIER 4 SCORING (Infrastructure with signal value) ───────────

    def _score_whale_sonar(self, symbol: str, side: str) -> dict:
        """Mycelium whale sonar: aggregate whale signal score."""
        result = {"bonus": 0.0, "whale_score": 0.0}
        if self.whale_sonar is None:
            return result
        try:
            if hasattr(self.whale_sonar, 'get_whale_signal'):
                sig = self.whale_sonar.get_whale_signal(symbol) or {}
            elif hasattr(self.whale_sonar, 'get_aggregated'):
                sig = self.whale_sonar.get_aggregated() or {}
            else:
                return result
            score = float(sig.get("whale_signal_score", 0.0) or 0.0)
            bonus = score * 1.5
            result.update({"bonus": max(-1.0, min(1.5, bonus)), "whale_score": score})
            self._whale_sonar_snapshot = {"symbol": symbol, "score": score, "bonus": result["bonus"]}
        except Exception as e:
            self._whale_sonar_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_hive_state(self, symbol: str, side: str) -> dict:
        """Hive state: cross-system coordination status."""
        result = {"bonus": 0.0, "coherent": True}
        if self.hive_state is None:
            return result
        try:
            state = self.hive_state.get_state() if hasattr(self.hive_state, 'get_state') else {}
            if not state:
                return result
            coherent = bool(state.get("coherent", True))
            mood = str(state.get("mood", "neutral") or "neutral").lower()
            bonus = 0.0
            if not coherent:
                bonus = -0.75
            if mood in {"bullish", "optimistic"}:
                bonus += 0.25 if side == "buy" else -0.15
            elif mood in {"bearish", "fearful"}:
                bonus += 0.25 if side == "sell" else -0.15
            result.update({"bonus": max(-1.0, min(0.75, bonus)), "coherent": coherent})
            self._hive_state_snapshot = {"symbol": symbol, "coherent": coherent, "mood": mood, "bonus": result["bonus"]}
        except Exception as e:
            self._hive_state_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _score_inception(self, symbol: str, side: str) -> dict:
        """Inception engine: Russian-doll dream-layer probability."""
        result = {"bonus": 0.0, "deepest_signal": "neutral", "limbo_prob": 0.0}
        if self.inception_engine is None:
            return result
        try:
            insight = None
            if hasattr(self.inception_engine, 'get_limbo_insight'):
                insight = self.inception_engine.get_limbo_insight(symbol)
            elif hasattr(self.inception_engine, 'dream'):
                insight = self.inception_engine.dream(symbol)
            if insight is None:
                return result
            direction = str(insight.get("direction", "neutral") or "neutral").lower() if isinstance(insight, dict) else str(getattr(insight, 'direction', 'neutral') or 'neutral').lower()
            probability = float(insight.get("probability", 0.5) or 0.5) if isinstance(insight, dict) else float(getattr(insight, 'probability', 0.5) or 0.5)
            bonus = (probability - 0.5) * 2.0
            if (direction in {"buy", "bullish"} and side == "sell") or (direction in {"sell", "bearish"} and side == "buy"):
                bonus *= -0.5
            result.update({"bonus": max(-1.0, min(1.0, bonus)), "deepest_signal": direction, "limbo_prob": probability})
            self._inception_snapshot = {"symbol": symbol, "direction": direction, "probability": probability, "bonus": result["bonus"]}
        except Exception as e:
            self._inception_snapshot = {"symbol": symbol, "error": str(e)}
        return result

    def _select_new_position(self, positions: list[dict], known_ids: set[str], pair: str, side: str) -> Optional[dict]:
        """Find the newly opened Kraken position for this order without trusting pair-only matching."""
        candidates = []
        for pos in positions:
            pos_id = str(pos.get("position_id", ""))
            kp_pair = pos.get("pair", "")
            alt_pair = self.client._int_to_alt.get(kp_pair, kp_pair)
            if pos_id in known_ids:
                continue
            if side != pos.get("side", ""):
                continue
            if alt_pair != pair and kp_pair != pair:
                continue
            candidates.append(pos)
        if len(candidates) == 1:
            return candidates[0]
        if candidates:
            candidates.sort(key=lambda p: float(p.get("open_time", 0.0) or 0.0), reverse=True)
            return candidates[0]
        return None

    def _select_close_trade(self, trades: list[dict], trade: ActiveTrade, close_side: str, since_ts: float) -> Optional[dict]:
        """Find the best matching close fill from recent Kraken trade history."""
        candidates = []
        for td in trades:
            tp = td.get("pair", "")
            alt = self.client._int_to_alt.get(tp, tp)
            if alt != trade.pair and tp != trade.pair:
                continue
            if td.get("type", "") != close_side:
                continue
            if float(td.get("time", 0.0) or 0.0) + 2 < since_ts:
                continue
            vol = float(td.get("vol", 0.0) or 0.0)
            if trade.volume > 0 and abs(vol - trade.volume) / trade.volume > 0.15:
                continue
            candidates.append(td)
        if not candidates:
            return None
        candidates.sort(
            key=lambda td: (
                abs(float(td.get("vol", 0.0) or 0.0) - trade.volume),
                -float(td.get("time", 0.0) or 0.0),
            )
        )
        return candidates[0]

    def _fetch_binance_klines(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 100,
    ) -> list:
        """Fetch Binance klines with a small timeout for projection work."""
        url = f"{BINANCE_KLINES_URL}?symbol={symbol}&interval={interval}&limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": "MarginArmy/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode())

    def _build_prime_projection(self, symbol: str, side: str) -> dict:
        """
        Use one month of hourly candles to project forward across prime horizons,
        then validate that projection against recent live 1m tape.
        """
        projection = {
            "side": side,
            "confidence": 0.0,
            "edge": 0.0,
            "live_match": 0.0,
            "samples": 0,
        }
        try:
            hist = self._fetch_binance_klines(symbol, interval="1h", limit=720)
            if len(hist) < 120:
                return projection

            closes = [float(k[4]) for k in hist]
            vols = [float(k[5]) for k in hist]
            primes = [2, 3, 5, 7, 11, 13]
            max_prime = max(primes)

            curr_mom3 = (closes[-1] - closes[-4]) / closes[-4] if closes[-4] > 0 else 0.0
            curr_mom12 = (closes[-1] - closes[-13]) / closes[-13] if closes[-13] > 0 else 0.0
            curr_vol = (
                sum(abs(closes[j] - closes[j - 1]) / closes[j - 1] for j in range(len(closes) - 12, len(closes)))
                / 12
            ) if len(closes) >= 13 else 0.0
            curr_surge = vols[-1] / max(1.0, sum(vols[-13:-1]) / 12)

            snapshots = []
            for i in range(24, len(closes) - max_prime - 1):
                p = closes[i]
                if p <= 0:
                    continue
                mom3 = (closes[i] - closes[i - 3]) / closes[i - 3] if closes[i - 3] > 0 else 0.0
                mom12 = (closes[i] - closes[i - 12]) / closes[i - 12] if closes[i - 12] > 0 else 0.0
                vol = sum(abs(closes[j] - closes[j - 1]) / closes[j - 1] for j in range(i - 11, i + 1)) / 12
                surge = vols[i] / max(1.0, sum(vols[i - 12:i]) / 12)
                dist = (
                    abs(mom3 - curr_mom3) * 5.0
                    + abs(mom12 - curr_mom12) * 3.0
                    + abs(vol - curr_vol) * 8.0
                    + abs(surge - curr_surge) * 0.5
                )
                future_moves = [(closes[i + pstep] - p) / p for pstep in primes]
                snapshots.append((dist, future_moves))

            if len(snapshots) < 12:
                return projection

            snapshots.sort(key=lambda x: x[0])
            matched = snapshots[:24]
            weighted_moves = []
            for dist, future_moves in matched:
                weight = 1.0 / max(0.05, dist)
                avg_future = sum(future_moves) / len(future_moves)
                weighted_moves.append((weight, avg_future))

            total_weight = sum(w for w, _ in weighted_moves)
            if total_weight <= 0:
                return projection
            mean_move = sum(w * mv for w, mv in weighted_moves) / total_weight
            agreement = sum(
                w for w, mv in weighted_moves
                if (side == "buy" and mv > 0) or (side == "sell" and mv < 0)
            ) / total_weight
            projected_side = "buy" if mean_move >= 0 else "sell"

            live = self._fetch_binance_klines(symbol, interval="1m", limit=16)
            if len(live) >= 14:
                live_closes = [float(k[4]) for k in live]
                live_primes = [2, 3, 5, 7, 11]
                checks = 0
                hits = 0
                for pstep in live_primes:
                    if pstep >= len(live_closes):
                        continue
                    delta = live_closes[-1] - live_closes[-1 - pstep]
                    checks += 1
                    if (projected_side == "buy" and delta > 0) or (projected_side == "sell" and delta < 0):
                        hits += 1
                projection["live_match"] = (hits / checks) if checks else 0.0

            projection["side"] = projected_side
            projection["confidence"] = max(0.0, min(1.0, agreement))
            projection["edge"] = mean_move * 100.0
            projection["samples"] = len(matched)
            return projection
        except Exception:
            return projection

    def _collect_alignment_metrics(self, pair: str, side: str, momentum_pct: float) -> dict:
        """Aggregate coherence, lambda, HNC-style, macro, and planetary/solar alignment."""
        data = {
            "coherence": 0.5,
            "lyra": 0.5,
            "lambda": 0.5,
            "purity": 0.5,
            "macro": 0.0,
            "earth": 0.75,
            "solar": 0.0,
            "score": 0.0,
        }

        try:
            if HAS_SEER_INTEGRATION and seer_get_vision is not None:
                sv = seer_get_vision() or {}
                data["coherence"] = float(sv.get("score", sv.get("confidence", data["coherence"])) or data["coherence"])
        except Exception:
            pass

        try:
            if HAS_LYRA_INTEGRATION and lyra_get_resonance is not None:
                lr = lyra_get_resonance()
                if isinstance(lr, dict):
                    data["lyra"] = float(lr.get("resonance", lr.get("coherence", data["lyra"])) or data["lyra"])
                elif isinstance(lr, (int, float)):
                    data["lyra"] = float(lr)
        except Exception:
            pass

        try:
            if self.lattice is not None:
                external = max(0.0, min(1.0, 0.5 + momentum_pct / 4.0))
                state = self.lattice.update(
                    opportunities=[{"symbol": pair, "coherence": external, "change24h": momentum_pct}],
                    external_coherence=external,
                )
                data["lambda"] = float(getattr(state, "lambda_value", data["lambda"]) or data["lambda"])
                data["purity"] = float(getattr(state, "field_purity", data["purity"]) or data["purity"])
        except Exception:
            pass

        try:
            if self.macro is not None:
                mctx = self.macro.get_entry_context(pair)
                data["macro"] = float(mctx.get("macro_score", 0.0) or 0.0)
        except Exception:
            pass

        try:
            if self.atn_monitor is not None:
                earth = self.atn_monitor.get_state()
                data["earth"] = float(getattr(earth, "risk_factor", data["earth"]) or data["earth"])
                space = getattr(earth, "streams", {}).get("space")
                if space is not None and isinstance(getattr(space, "raw", None), dict):
                    raw = space.raw
                    solar_terms = [
                        float(raw.get("kp_index", 0.0) or 0.0) / 9.0,
                        min(1.0, float(raw.get("solar_flares_24h", 0.0) or 0.0) / 5.0),
                        min(1.0, float(raw.get("cme_24h", 0.0) or 0.0) / 3.0),
                    ]
                    data["solar"] = sum(solar_terms) / len(solar_terms)
        except Exception:
            pass

        data["score"] = (
            (data["coherence"] - 0.5) * 2.0
            + (data["lyra"] - 0.5) * 1.5
            + (data["lambda"] - 0.5) * 2.0
            + (data["purity"] - 0.5) * 2.0
            + data["macro"]
            + (data["earth"] - 0.5) * 1.0
            - data["solar"] * 0.75
        )
        return data

    @staticmethod
    def _observed_number(
        value: Any,
        *,
        positive: bool = False,
        nonnegative: bool = False,
    ) -> Optional[float]:
        """Return a finite provider number without substituting a default."""
        if value is None or isinstance(value, bool):
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
    def _fresh_receipt_timestamp(value: Any, *, max_age: float) -> Optional[float]:
        timestamp = KrakenMarginArmyTrader._observed_number(value, positive=True)
        if timestamp is None:
            return None
        age = time.time() - timestamp
        if age < -5.0 or age > max_age:
            return None
        return timestamp

    def _fresh_provider_quote(self, pair: str) -> Optional[Dict[str, Any]]:
        """Fetch a timestamped Kraken quote receipt suitable for an action gate."""
        try:
            quote = self.client.get_24h_ticker(pair)
        except Exception as exc:
            logger.warning("Fresh Kraken quote unavailable for %s: %s", pair, exc)
            return None
        if (
            not isinstance(quote, dict)
            or quote.get("truth_status") not in {"real_observed", "real_derived"}
            or quote.get("generated_values") is not False
            or not isinstance(quote.get("source_id"), str)
            or not quote.get("source_id")
        ):
            return None
        source_timestamp = self._fresh_receipt_timestamp(
            quote.get("source_timestamp"),
            max_age=PROVIDER_RECEIPT_MAX_AGE_SEC,
        )
        price = self._observed_number(quote.get("price"), positive=True)
        if source_timestamp is None or price is None:
            return None
        return {
            "provider": "kraken",
            "symbol": str(quote.get("symbol") or pair),
            "price": price,
            "source_id": quote["source_id"],
            "source_timestamp": source_timestamp,
            "received_at": quote.get("received_at"),
            "truth_status": quote["truth_status"],
            "generated_values": False,
        }

    def _validate_trade_balance_receipt(self, tb: Any) -> Dict[str, Any]:
        """Require a complete synchronous private-account receipt."""
        if (
            not isinstance(tb, dict)
            or tb.get("data_status") != "live"
            or tb.get("truth_status") != "real_observed"
            or tb.get("generated_values") is not False
            or not isinstance(tb.get("source_id"), str)
            or not tb.get("source_id")
        ):
            raise RuntimeError("Kraken margin account receipt is no_data or incomplete")
        received_at = self._fresh_receipt_timestamp(
            tb.get("received_at"),
            max_age=PROVIDER_ACCOUNT_RECEIPT_MAX_AGE_SEC,
        )
        if received_at is None:
            raise RuntimeError("Kraken margin account receipt is missing or stale")
        observed: Dict[str, float] = {}
        for field_name in (
            "equity_value",
            "trade_balance",
            "margin_amount",
            "unrealized_pnl",
            "cost_basis",
            "floating_valuation",
            "free_margin",
            "margin_level",
        ):
            value = self._observed_number(tb.get(field_name))
            if value is None:
                raise RuntimeError(f"Kraken margin account receipt lacks {field_name}")
            observed[field_name] = value
        if (
            observed["equity_value"] < 0
            or observed["trade_balance"] < 0
            or observed["margin_amount"] < 0
            or observed["free_margin"] < 0
            or observed["margin_level"] < 0
        ):
            raise RuntimeError("Kraken margin account receipt contains invalid negative balances")
        return {
            **observed,
            "source_id": tb["source_id"],
            "received_at": received_at,
            "freshness_basis": "synchronous_private_response_received_at",
            "data_status": "live",
            "truth_status": "real_observed",
            "generated_values": False,
        }

    def _margin_capital_from_trade_balance(self, tb: Dict[str, Any]):
        if MarginCapitalSnapshot is None:
            equity = float(tb.get("equity", tb.get("equity_value", tb.get("e", 0.0))) or 0.0)
            margin_used = float(tb.get("margin_amount", tb.get("m", 0.0)) or 0.0)
            free_margin = float(
                tb.get("free_margin", tb.get("margin_free", tb.get("mf", max(0.0, equity - margin_used)))) or 0.0
            )
            return type("MarginCapitalSnapshotFallback", (), {
                "equity": equity,
                "free_margin": free_margin,
                "margin_used": margin_used,
                "unrealized_pnl": float(tb.get("unrealized_pnl", tb.get("n", 0.0)) or 0.0),
                "margin_level": float(tb.get("margin_level", tb.get("ml", 0.0)) or 0.0),
                "trade_balance": float(tb.get("trade_balance", tb.get("tb", 0.0)) or 0.0),
            })()
        return MarginCapitalSnapshot.from_trade_balance(tb)

    def _get_margin_capital(self, *, force: bool = False):
        """Return only a complete, fresh Kraken margin-account snapshot."""
        if getattr(self, "dry_run", False):
            raise RuntimeError("dry-run margin account is not_submitted")
        now = time.time()
        cached = getattr(self, "_last_margin_capital", None)
        cached_at = float(getattr(self, "_last_margin_capital_at", 0.0) or 0.0)
        cached_receipt = getattr(self, "_last_margin_capital_receipt", None)
        if (
            cached is not None
            and isinstance(cached_receipt, dict)
            and not force
            and (now - cached_at) < KRAKEN_MARGIN_CAPITAL_CACHE_TTL_SEC
            and self._fresh_receipt_timestamp(
                cached_receipt.get("received_at"),
                max_age=PROVIDER_ACCOUNT_RECEIPT_MAX_AGE_SEC,
            ) is not None
        ):
            return cached

        try:
            receipt = self._validate_trade_balance_receipt(self.client.get_trade_balance())
            snapshot = self._margin_capital_from_trade_balance(receipt)
            self._last_margin_capital = snapshot
            self._last_margin_capital_receipt = receipt
            self._last_margin_capital_at = time.time()
            self._last_margin_capital_error = ""
            return snapshot
        except Exception as e:
            self._last_margin_capital_error = str(e)
            raise

    def _dynamic_profit_target_for_equity(self, equity: float) -> float:
        if getattr(self, "dynamic_sizer", None) is None:
            return PROFIT_TARGET_USD
        return self.dynamic_sizer.profit_target_usd(equity, PROFIT_TARGET_USD)

    def _dynamic_profit_target_for_trade(self, trade_value: float = 0.0) -> float:
        try:
            return self._dynamic_profit_target_for_equity(self._get_margin_capital().equity)
        except Exception:
            return PROFIT_TARGET_USD

    def _trade_profit_target(self, trade: ActiveTrade) -> float:
        stored = float(getattr(trade, "profit_target_usd", 0.0) or 0.0)
        if stored > 0:
            return stored
        return self._dynamic_profit_target_for_trade(float(getattr(trade, "cost", 0.0) or 0.0))

    def _plan_dynamic_margin_position(
        self,
        pair_info: MarginPairInfo,
        leverage: int,
        *,
        split_slot: bool = False,
        snapshot=None,
    ):
        """Plan a position from the latest Kraken free margin and pair limits."""
        if getattr(self, "dynamic_sizer", None) is None or PositionSizePlan is None:
            return None
        snapshot = snapshot or self._get_margin_capital()
        return self.dynamic_sizer.plan(
            snapshot,
            price=pair_info.last_price,
            ordermin=pair_info.ordermin,
            costmin=getattr(pair_info, "costmin", 0.0),
            lot_decimals=pair_info.lot_decimals,
            leverage=leverage,
            max_profit_target_usd=PROFIT_TARGET_USD,
            split_slot=split_slot,
        )

    def _usd_value_for_asset_balance(self, asset: str, amount: float) -> float:
        asset_norm = KRAKEN_BASE_MAP.get(str(asset or "").upper(), str(asset or "").upper())
        if amount <= 0:
            return 0.0
        if asset_norm == "USD":
            return amount
        quote = self._fresh_provider_quote(f"{asset_norm}USD")
        if quote is None:
            return 0.0
        return amount * quote["price"]

    def _get_spot_balance_snapshot(self, *, force: bool = False) -> Dict[str, Any]:
        """Return live Kraken spot/cash balances with cached USD valuation for the runtime mirror."""
        now = time.time()
        cached = getattr(self, "_last_spot_balance_snapshot", {}) or {}
        cached_at = float(getattr(self, "_last_spot_balance_snapshot_at", 0.0) or 0.0)
        if cached and not force and (now - cached_at) < KRAKEN_SPOT_BALANCE_CACHE_TTL_SEC:
            return dict(cached)

        balances: Dict[str, float] = {}
        try:
            if hasattr(self.client, "get_account_balance"):
                balances = {
                    str(asset).upper(): float(amount)
                    for asset, amount in self.client.get_account_balance().items()
                    if float(amount or 0.0) > 0
                }
        except Exception as e:
            if cached:
                snapshot = dict(cached)
                snapshot["stale"] = True
                snapshot["error"] = str(e)
                return snapshot
            snapshot = {
                "generated_at": datetime.now().isoformat(),
                "source": "kraken_private_balance",
                "available": False,
                "stale": True,
                "error": str(e),
                "balances": {},
                "total_usd_estimate": 0.0,
                "tradable_cash_usd": 0.0,
            }
            self._last_spot_balance_snapshot = snapshot
            self._last_spot_balance_snapshot_at = now
            return snapshot

        valued_balances: Dict[str, Dict[str, Any]] = {}
        total_usd = 0.0
        tradable_cash_usd = 0.0
        for asset, amount in sorted(balances.items()):
            usd_value = self._usd_value_for_asset_balance(asset, amount)
            total_usd += usd_value
            if KRAKEN_BASE_MAP.get(asset, asset) in {"USD", "USDT", "USDC", "DAI", "GBP", "EUR"}:
                tradable_cash_usd += usd_value
            valued_balances[asset] = {
                "amount": round(float(amount), 12),
                "usd_estimate": round(float(usd_value), 6),
            }

        snapshot = {
            "generated_at": datetime.now().isoformat(),
            "source": "kraken_private_balance_cached_live",
            "available": bool(balances),
            "stale": False,
            "balances": valued_balances,
            "asset_count": len(valued_balances),
            "total_usd_estimate": round(float(total_usd), 6),
            "tradable_cash_usd": round(float(tradable_cash_usd), 6),
            "cache_ttl_sec": KRAKEN_SPOT_BALANCE_CACHE_TTL_SEC,
        }
        self._last_spot_balance_snapshot = snapshot
        self._last_spot_balance_snapshot_at = time.time()
        return dict(snapshot)

    def _get_capital_snapshot(self) -> dict:
        """Return current Kraken portfolio metrics for sizing and UI."""
        snapshot = self._get_margin_capital()
        self._last_margin_capital = snapshot
        margin_equity = float(snapshot.equity or 0.0)
        free_margin = float(snapshot.free_margin or 0.0)
        margin_used = float(snapshot.margin_used or 0.0)
        unrealized = float(getattr(snapshot, "unrealized_pnl", 0.0) or 0.0)
        spot_snapshot = self._get_spot_balance_snapshot()
        spot_value_usd = float(spot_snapshot.get("total_usd_estimate", 0.0) or 0.0)
        spot_cash_usd = float(spot_snapshot.get("tradable_cash_usd", 0.0) or 0.0)
        equity = max(margin_equity, spot_value_usd)
        if margin_equity <= 0:
            free_margin = max(free_margin, spot_cash_usd)
        budget_fraction = TINY_ACCOUNT_MARGIN_BUFFER if equity <= TINY_ACCOUNT_EQUITY_USD else MARGIN_BUFFER
        budget = free_margin * budget_fraction
        profit_target_usd = self._dynamic_profit_target_for_equity(equity)
        target_pct_equity = (profit_target_usd / equity * 100.0) if equity > 0 else 0.0
        return {
            "equity": equity,
            "margin_equity": margin_equity,
            "spot_value_usd": spot_value_usd,
            "spot_cash_usd": spot_cash_usd,
            "free_margin": free_margin,
            "margin_used": margin_used,
            "unrealized": unrealized,
            "budget": budget,
            "budget_fraction": budget_fraction,
            "profit_target_usd": profit_target_usd,
            "target_pct_equity": target_pct_equity,
            "balance_snapshot": spot_snapshot,
            "margin_capital_error": getattr(self, "_last_margin_capital_error", ""),
            "portfolio_value_source": "margin_trade_balance" if margin_equity >= spot_value_usd else "spot_balance",
        }

    def _track_equity_metrics(self, equity: float) -> tuple[float, float]:
        """Track peak equity and drawdown values for dashboard telemetry."""
        if equity > self._peak_equity_seen:
            self._peak_equity_seen = equity
        peak = max(self._peak_equity_seen, equity, self.starting_equity)
        drawdown = ((peak - equity) / peak * 100.0) if peak > 0 else 0.0
        self._max_drawdown_seen = max(self._max_drawdown_seen, drawdown)
        return drawdown, self._max_drawdown_seen

    def _build_dashboard_positions(self) -> list[dict]:
        """Build open-position payload for the live dashboard."""
        positions: list[dict] = []
        for trade in (self.active_long, self.active_short):
            if not trade:
                continue
            current_price = 0.0
            if trade.binance_symbol and self.stream and self.stream.is_alive():
                current_price = self.stream.get_executable_price(trade.binance_symbol, side=trade.side)
            if current_price <= 0 and trade.binance_symbol:
                current_price = self.market.get_single_price(trade.binance_symbol)
            if current_price <= 0:
                current_price = trade.entry_price
            unrealized_pnl = (
                (current_price - trade.entry_price) * trade.volume
                if trade.side == "buy"
                else (trade.entry_price - current_price) * trade.volume
            )
            positions.append({
                "symbol": trade.pair,
                "trade_id": trade.order_id,
                "side": trade.side.upper(),
                "entry_price": trade.entry_price,
                "quantity": trade.volume,
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "exchange": "kraken",
                "opened_at": datetime.fromtimestamp(trade.open_time).isoformat() if getattr(trade, "open_time", 0) else "",
                "cognition_plan": getattr(trade, "cognition_plan", {}) or {},
            })
        return positions

    def _build_dashboard_trades(self) -> list[dict]:
        """Map completed margin trades into the shared dashboard trade format."""
        trades = []
        for idx, trade in enumerate(self.completed_trades[-25:]):
            trades.append({
                "symbol": trade.get("pair", ""),
                "side": str(trade.get("side", "")).upper(),
                "price": float(trade.get("exit_price", 0.0) or 0.0),
                "quantity": float(trade.get("volume", 0.0) or 0.0),
                "fee": float(trade.get("total_fees", 0.0) or 0.0),
                "fee_asset": "USD",
                "timestamp": trade.get("exit_time", datetime.now().isoformat()),
                "transaction_id": trade.get("close_order_id") or trade.get("order_id") or f"margin-{idx}",
                "pnl": float(trade.get("net_pnl", 0.0) or 0.0),
                "is_win": float(trade.get("net_pnl", 0.0) or 0.0) > 0,
                "exchange": "kraken",
            })
        return trades

    def _build_dashboard_recent_trades(self) -> list[dict]:
        """Map closed trades into the session/dashboard recent trade format."""
        recent = []
        for trade in reversed(self.completed_trades[-10:]):
            recent.append({
                "time": trade.get("exit_time", datetime.now().isoformat()),
                "side": str(trade.get("side", "")).upper(),
                "symbol": trade.get("pair", ""),
                "quantity": float(trade.get("volume", 0.0) or 0.0),
                "pnl": float(trade.get("net_pnl", 0.0) or 0.0),
                "success": float(trade.get("net_pnl", 0.0) or 0.0) > 0,
                "hold_seconds": float(trade.get("hold_seconds", 0.0) or 0.0),
                "reason": trade.get("reason", ""),
                "trade_id": trade.get("close_order_id") or trade.get("order_id") or "",
            })
        return recent

    def _push_dashboard_state(self, force: bool = False) -> None:
        """Push live terminal state into the dashboard ingest endpoint."""
        now = time.time()
        if not force and (now - self._last_dashboard_push) < DASHBOARD_SYNC_INTERVAL_SEC:
            return
        try:
            capital = self._get_capital_snapshot()
            equity = float(capital["equity"] or 0.0)
            current_drawdown, max_drawdown = self._track_equity_metrics(equity)
            completed = self.completed_trades
            wins = sum(1 for t in completed if float(t.get("net_pnl", 0.0) or 0.0) > 0)
            avg_hold_minutes = (
                sum(float(t.get("hold_seconds", 0.0) or 0.0) for t in completed) / len(completed) / 60.0
                if completed else 0.0
            )
            payload = {
                "user_id": self.dashboard_user_id,
                "equity": equity,
                "equity_usd": equity,
                "portfolio_value": equity,
                "portfolio_value_usd": equity,
                "free_margin": float(capital["free_margin"] or 0.0),
                "margin_used": float(capital["margin_used"] or 0.0),
                "margin_equity_usd": float(capital.get("margin_equity", 0.0) or 0.0),
                "spot_balance_value_usd": float(capital.get("spot_value_usd", 0.0) or 0.0),
                "spot_cash_usd": float(capital.get("spot_cash_usd", 0.0) or 0.0),
                "portfolio_value_source": capital.get("portfolio_value_source", ""),
                "balance_snapshot": capital.get("balance_snapshot", {}),
                "portfolio_balances": capital.get("balance_snapshot", {}),
                "peak_equity": max(self._peak_equity_seen, equity, self.starting_equity),
                "current_drawdown": current_drawdown,
                "max_drawdown": max_drawdown,
                "trades": self._build_dashboard_trades(),
                "recent_trades": self._build_dashboard_recent_trades(),
                "total_trades": self.total_trades,
                "wins": wins,
                "win_rate": (wins / self.total_trades * 100.0) if self.total_trades else 0.0,
                "avg_hold_time": avg_hold_minutes,
                "positions": self._build_dashboard_positions(),
                "coherence": 0.0,
                "lambda": 0.0,
                "gaia_state": "NEUTRAL",
                "gaia_frequency": 432.0,
                "gaia_purity": 0.0,
                "gaia_carrier_phi": 0.0,
                "gaia_432_lock": 0.0,
                "hnc_frequency": 432.0,
                "hnc_market_state": "CONSOLIDATION",
                "hnc_coherence_percent": 0.0,
                "hnc_modifier": 1.0,
                "mycelium_hives": 0,
                "mycelium_agents": 0,
                "mycelium_generation": 0,
                "max_generation": 0,
                "queen_state": "HOLD",
                "queen_pnl": float(self.total_profit),
                "compounded": float(self.total_profit),
                "harvested": 0.0,
                "pool_total": equity,
                "pool_available": float(capital["free_margin"] or 0.0),
                "scout_count": 0,
                "split_count": 0,
                "trading_mode": "BALANCED",
                "entry_threshold": 0.0,
                "exit_threshold": 0.0,
                "risk_multiplier": 1.0,
                "tp_multiplier": 1.0,
                "runtime_minutes": (time.time() - self.start_time) / 60.0,
                "ws_connected": bool(self.stream and self.stream.connected),
                "ws_message_count": int(self.stream.msg_count if self.stream else 0),
                "latest_monitor_line": self._latest_monitor_line,
                "status_lines": self._latest_status_lines[-16:],
                "registry_snapshot": self._registry_snapshot,
                "decision_snapshot": self._decision_snapshot,
                "brain_snapshot": getattr(self, "_brain_snapshot", {}),
                "margin_brain": getattr(self, "_latest_margin_brain_decision", {}),
                "margin_brain_decisions": getattr(self, "_margin_brain_decisions", {}),
                "harmonic_snapshot": self._harmonic_snapshot,
                "quantum_snapshot": self._quantum_snapshot,
                "timeline_snapshot": self._timeline_snapshot,
                "fusion_snapshot": self._fusion_snapshot,
                "whale_snapshot": self._whale_snapshot,
                "live_tv_snapshot": self._live_tv_snapshot,
                "ocean_snapshot": self._ocean_snapshot,
                "thought_bus_snapshot": self._thought_bus_snapshot,
                "cognition_snapshot": self._cognition_snapshot,
                "trade_cognition": getattr(self, "_latest_trade_cognition", {}),
                "truth_check": getattr(self, "_latest_truth_check", {}),
                "kraken_fast_profit_capture": getattr(self, "_last_fast_profit_capture", {}),
            }
            self._latest_dashboard_payload = dict(payload)
            self._last_dashboard_push = now
            if not self.dashboard_sync_enabled:
                return
            req = urllib.request.Request(
                f"{self.dashboard_sync_url}/functions/v1/ingest-terminal-state",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "apikey": self.dashboard_sync_key,
                    "Authorization": f"Bearer {self.dashboard_sync_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8):
                pass
        except Exception as e:
            logger.debug(f"Dashboard sync skipped: {e}")

    def _get_seer_bias(self) -> tuple[str, float, float]:
        """Return Seer verdict, confidence, and score bonus for mission selection."""
        if self.seer is None:
            return ("OFF", 0.0, 0.0)

        try:
            vision = self.seer.see()
            confidence = float(getattr(vision, "confidence", 0.0) or 0.0)
            unified = float(getattr(vision, "unified_score", 0.5) or 0.5)
            risk_modifier = float(getattr(vision, "risk_modifier", 1.0) or 1.0)
            verdict = "GO" if risk_modifier >= 0.95 and unified >= 0.55 else "CAUTION"
            bonus = max(-1.0, min(2.0, (unified - 0.5) * 4.0 + (risk_modifier - 1.0)))
            return (verdict, confidence, bonus)
        except Exception:
            return ("ERROR", 0.0, -0.25)

    def _score_aux_scanners(
        self,
        symbol: str,
        side: str,
        prices: list[float],
        volumes: list[float],
        current_price: float,
        momentum_pct: float,
    ) -> dict:
        """Collect optional scanner inputs without letting any one module break selection."""
        result = {
            "war_go": True,
            "war_prob": 0.0,
            "war_priority": 0,
            "war_bonus": 0.0,
            "sniper_action": "OFF",
            "sniper_conf": 0.0,
            "sniper_prob": 0.0,
            "sniper_bonus": 0.0,
            "nexus_trade": False,
            "nexus_prob": 0.0,
            "nexus_edge": 0.0,
            "nexus_bonus": 0.0,
        }

        if should_attack is not None and get_quick_kill_estimate is not None:
            try:
                war_go, _reason, war_priority = should_attack(symbol, "kraken", prices[-20:])
                estimate = get_quick_kill_estimate(symbol, "kraken", prices[-20:])
                war_prob = float(getattr(estimate, "prob_penny_profit", 0.0) or 0.0)
                result["war_go"] = bool(war_go)
                result["war_priority"] = int(war_priority or 0)
                result["war_prob"] = war_prob
                result["war_bonus"] = (-2.5 if not war_go else 0.0) + min(war_prob * 2.0, 2.0) + min(result["war_priority"] / 10.0, 1.0)
            except Exception:
                result["war_go"] = True

        if self.sniper_brain is not None:
            try:
                sig = self.sniper_brain.get_entry_signal(symbol, prices[-20:], volumes[-20:])
                if sig is not None:
                    result["sniper_action"] = getattr(sig, "action", "HOLD") or "HOLD"
                    result["sniper_conf"] = float(getattr(sig, "confidence", 0.0) or 0.0)
                    result["sniper_prob"] = float(getattr(sig, "probability_score", 0.0) or 0.0)
                    direction_bonus = 0.4 if result["sniper_action"].upper() in {"BUY", "LONG", side.upper()} else 0.0
                    hold_penalty = -0.5 if result["sniper_action"].upper() == "HOLD" else 0.0
                    result["sniper_bonus"] = hold_penalty + direction_bonus + result["sniper_conf"] + result["sniper_prob"]
            except Exception:
                pass

        if self.nexus_predictor is not None:
            try:
                pred = self.nexus_predictor.predict_instant(
                    price=current_price,
                    high_24h=max(prices[-20:]),
                    low_24h=min(prices[-20:]),
                    momentum=momentum_pct / 100.0,
                )
                result["nexus_trade"] = bool(pred.get("should_trade", False))
                result["nexus_prob"] = float(pred.get("probability", 0.0) or 0.0)
                result["nexus_edge"] = float(pred.get("edge", 0.0) or 0.0)
                result["nexus_bonus"] = (
                    (-1.0 if not result["nexus_trade"] else 0.0)
                    + max(0.0, (result["nexus_prob"] - 0.5) * 4.0)
                    + max(-0.5, min(result["nexus_edge"], 1.0))
                )
            except Exception:
                pass

        return result

    # ----------------------------------------------------------
    #  STARTUP: Discover margin pairs (ONE Kraken API batch)
    # ----------------------------------------------------------
    def discover_margin_universe(self) -> Dict[str, MarginPairInfo]:
        """Fetch ALL margin-eligible pairs from Kraken (once at startup)."""
        logger.info("Scanning Kraken margin universe (one-time)...")
        margin_pairs_raw = self.client.get_margin_pairs()
        pairs_data = self.client._load_asset_pairs()
        usd_margin_pairs = {}

        for mp in margin_pairs_raw:
            pair_name = mp["pair"]
            internal = mp["internal"]
            base = mp["base"]
            quote = mp["quote"]
            if quote not in USD_QUOTES and quote != "USD":
                continue
            pair_info = pairs_data.get(internal, {})
            ordermin = float(pair_info.get("ordermin", 0.0001))
            costmin = float(pair_info.get("costmin", 0.0) or 0.0)
            lot_decimals = int(pair_info.get("lot_decimals", 8))
            price_decimals = int(pair_info.get("pair_decimals", 4))

            base_clean = KRAKEN_BASE_MAP.get(base, base)
            binance_sym = f"{base_clean}USDT"

            info = MarginPairInfo(
                pair=pair_name,
                internal=internal,
                base=base,
                base_clean=base_clean,
                quote="USD",
                leverage_buy=mp["leverage_buy"],
                leverage_sell=mp["leverage_sell"],
                max_leverage=mp["max_leverage"],
                ordermin=ordermin,
                costmin=costmin,
                lot_decimals=lot_decimals,
                price_decimals=price_decimals,
                binance_symbol=binance_sym,
            )
            usd_margin_pairs[pair_name] = info

        self.margin_pairs = usd_margin_pairs
        logger.info(f"Found {len(usd_margin_pairs)} USD margin-eligible pairs")
        return usd_margin_pairs

    # ----------------------------------------------------------
    #  FREE PRICE UPDATE (Binance public API)
    # ----------------------------------------------------------
    def update_prices_free(self):
        """Update all pair prices using Binance public API. ONE call."""
        prices = self.market.fetch_all_binance_prices()
        stats = self.market.fetch_binance_24h()
        matched = 0
        for _, info in self.margin_pairs.items():
            bsym = info.binance_symbol
            price = prices.get(bsym, 0)
            if price > 0:
                info.last_price = price
                matched += 1
            s = stats.get(bsym, {})
            if s:
                info.bid = s.get("bid", price)
                info.ask = s.get("ask", price)
                info.momentum = s.get("price_change_pct", 0)
                info.volume_24h = s.get("volume", 0)
                if info.bid > 0 and info.ask > 0:
                    info.spread_pct = (info.ask - info.bid) / info.bid * 100
        logger.info(f"FREE API: {matched}/{len(self.margin_pairs)} pairs priced from Binance")
        return matched

    # ----------------------------------------------------------
    #  TARGET SELECTION - pick THE ONE best trade
    # ----------------------------------------------------------
    def find_best_target(self) -> Optional[Tuple[MarginPairInfo, str, float, float, int]]:
        """
        Score all margin pairs and pick THE ONE best target.
        All margin into this one trade. Maximum leverage.
        Returns: (pair_info, side, volume, trade_value, leverage) or None
        """
        try:
            capital = self._get_capital_snapshot()
        except Exception as e:
            logger.error(f"Could not get trade balance: {e}")
            return None

        equity = capital["equity"]
        free_margin = capital["free_margin"]
        margin_used = capital["margin_used"]
        margin_budget = capital["budget"]
        capital_snapshot = getattr(self, "_last_margin_capital", None)
        target_pct_equity = capital["target_pct_equity"]
        profit_target_usd = capital["profit_target_usd"]

        if free_margin < WAVE_CONFIG.get("min_free_margin_usd", 5.0):
            logger.warning(f"Not enough free margin: ${free_margin:.2f}")
            return None

        logger.info(
            f"ARMY: equity=${equity:.2f} | free=${free_margin:.2f} | "
            f"used=${margin_used:.2f} | budget=${margin_budget:.2f} | "
            f"target=${profit_target_usd:.2f} ({target_pct_equity:.3f}% eq)"
        )
        self._refresh_unified_intel_snapshot()

        # Log wave rider status (informational — per-candidate check below)
        if self.wave_rider and equity > 0:
            logger.info(
                f"[WaveRider] {self.wave_rider.status_line(equity, margin_used, 5)}"
            )

        # ── MACRO INTELLIGENCE — fetch once, shapes all buy signals ─────────
        _macro_ctx = {}
        if self.macro is not None:
            try:
                _macro_ctx = self.macro.get_entry_context("")
                logger.info(self.macro.summary_line(""))
            except Exception:
                pass

        candidates = []
        self._candidate_cognition_context = {}
        for _, info in self.margin_pairs.items():
            if info.last_price <= 0:
                continue
            if info.spread_pct > 0.5:
                continue
            if not info.leverage_buy or not info.leverage_sell:
                continue

            # === DIRECTION: Use ALL intel, not just momentum ===
            # Live stream flow is the #1 signal (sub-second real data)
            stream_side = None
            if self.stream and self.stream.is_alive():
                bsym = info.binance_symbol
                if bsym:
                    sf = self.stream.get_flow_snapshot(bsym)
                    if sf['buy_pct'] > 60 and sf['trade_velocity'] > 10:
                        stream_side = "buy"
                    elif sf['sell_pct'] > 60 and sf['trade_velocity'] > 10:
                        stream_side = "sell"

            # Stream flow overrides kline momentum (it's LIVE vs 24h delayed)
            if stream_side:
                side = stream_side
            elif info.momentum > 0.05:
                side = "buy"
            elif info.momentum < -0.05:
                side = "sell"
            else:
                # Neutral momentum — let stream or orderbook decide
                side = stream_side if stream_side else "buy"

            leverages = info.leverage_buy if side == "buy" else info.leverage_sell

            max_lev = max(leverages)
            split_slot = (side == "buy" and self.active_short) or (side == "sell" and self.active_long)
            plan = self._plan_dynamic_margin_position(
                info, max_lev, split_slot=split_slot, snapshot=capital_snapshot
            )
            if plan is None:
                logger.debug(f"{info.pair}: dynamic sizer unavailable")
                continue
            if not plan.approved:
                logger.debug(f"{info.pair}: sizing blocked - {plan.reason}")
                continue
            notional = plan.notional
            target_usd = plan.profit_target_usd

            # ── WAVE RIDER: pre-entry 250% margin gate ────────────────
            # Cap notional to the largest size that keeps projected
            # margin level >= 250% after entry.  If even the minimum
            # trade size would breach 250%, skip this pair entirely.
            if self.wave_rider:
                wave_ok, wave_check = self.wave_rider.check(
                    equity=equity,
                    margin_used=margin_used,
                    new_notional=plan.notional,
                    leverage=max_lev,
                    free_margin=free_margin,
                )
                if not wave_ok:
                    # Try capping to max safe notional instead of skipping
                    if wave_check.max_safe_notional >= plan.min_notional:
                        notional = min(wave_check.max_safe_notional, plan.notional)
                        logger.debug(
                            f"[WaveRider] {info.pair}: capped notional to "
                            f"${notional:.2f} (projected {wave_check.projected_margin_pct:.0f}%)"
                        )
                    else:
                        logger.debug(
                            f"[WaveRider] {info.pair}: skipped — {wave_check.reason}"
                        )
                        continue
                else:
                    logger.debug(
                        f"[WaveRider] {info.pair}: {wave_check.reason}"
                    )

            vol = plan.volume
            trade_val = plan.notional
            logger.debug(
                f"{info.pair}: dynamic size ${trade_val:.2f} notional "
                f"({max_lev}x, margin=${plan.required_margin:.2f}, "
                f"projected_ml={plan.projected_margin_pct:.0f}%, target=${target_usd:.2f})"
            )

            round_trip_fee, _, _ = self._estimate_round_trip_fee(
                trade_val, symbol=info.pair
            )
            required_move_pct, _, _ = self._estimate_required_move_pct(
                trade_val, target_usd, symbol=info.pair
            )
            validator_required_move_pct, validator_round_trip_cost = self._validator_required_move_pct(
                trade_val, target_usd, symbol=info.pair
            )
            if validator_required_move_pct > required_move_pct:
                required_move_pct = validator_required_move_pct
            if validator_round_trip_cost > round_trip_fee:
                round_trip_fee = validator_round_trip_cost

            momentum_score = min(abs(info.momentum) / 5, 2.0)  # Normalize to 0-2
            spread_score = max(0, 1.0 - info.spread_pct * 5)
            lev_score = max_lev / 5.0  # 10x = 2.0, 5x = 1.0, 3x = 0.6
            vol_score = min(info.volume_24h / 500_000, 1.0)
            ease_score = max(0, 2.0 - required_move_pct * 2)  # Bigger = easier target

            # For our small account, LEVERAGE is king:
            # 10x lev needs 0.7% move vs 3x needing 1.4% move
            # Weight leverage and ease heavily, momentum as tiebreaker
            # Multiverse learning conviction: ±0.5 based on shadow phase history
            conviction_bonus = (
                self.learning_bridge.get_conviction_bonus(info.pair)
                if self.learning_bridge is not None else 0.0
            )
            # Hive Mind ripple boost — Market Harp shared signal from TradingHiveMind
            # Positive ripple on a correlated market amplifies this pair's score
            _sym_root = info.pair.split('/')[0]  # "XBT", "ETH", "SOL" ...
            _hive_boosts = getattr(self, '_hive_boosts', {})
            _hive_factor = (
                _hive_boosts.get(_sym_root, 0) or
                _hive_boosts.get(_sym_root.replace('XBT', 'BTC'), 0) or
                _hive_boosts.get(_sym_root.replace('XXBT', 'BTC'), 0) or
                (float(_hive_boosts.get((info.binance_symbol or '')[:3], 0))
                 if info.binance_symbol else 0.0)
            )
            hive_bonus = float(_hive_factor) * 1.0   # Up to +1.0 score boost from harp

            # ── ENTRY GOAL: maximize profit in quickest time ──────────────────
            # profit_velocity = how much leverage × momentum covers the required
            # move.  A velocity > 1.0 means the asset is already moving fast
            # enough (leveraged) to hit the profit target in theory.
            # Use live stream trade_velocity to weight if available; fall back
            # to 24h momentum as a proxy for directional speed.
            stream_velocity = 0.0
            if self.stream and self.stream.is_alive() and info.binance_symbol:
                _sf = self.stream.get_flow_snapshot(info.binance_symbol)
                # Normalise: 20 trades/sec = maximum pressure signal
                stream_velocity = min(_sf.get('trade_velocity', 0) / 20.0, 1.0)
                # Directional alignment bonus: buy pressure on a buy side = faster
                if side == 'buy':
                    stream_velocity *= (_sf.get('buy_pct', 50) / 100.0)
                else:
                    stream_velocity *= (_sf.get('sell_pct', 50) / 100.0)

            # Leverage × directional momentum vs. required move
            # (required_move_pct == 0 guarded to avoid div/zero)
            _req_safe = max(required_move_pct, 0.01)
            profit_velocity = (abs(info.momentum) * max_lev) / _req_safe

            # Estimated ETA in minutes: assume 24h momentum distributes evenly
            # per minute → (|momentum| / 24h / 60) = % per minute.
            # With leverage, actual PnL velocity is higher.
            _pct_per_minute = abs(info.momentum) / (24 * 60) * max_lev
            eta_minutes = required_move_pct / _pct_per_minute if _pct_per_minute > 0 else 999

            # Goal score: reward signals that are heading to profit fastest.
            # Blend profit_velocity (trend) + stream_velocity (live order flow).
            _pv_capped = min(profit_velocity, 4.0)
            _sv_scaled = stream_velocity * 2.0          # 0→2 bonus
            # Extra bonus when ETA already inside target window
            _eta_bonus = 1.0 if eta_minutes <= GOAL_MAX_ETA_MINUTES else 0.0
            goal_score = (_pv_capped + _sv_scaled + _eta_bonus) * 0.5  # 0 → ~3.5

            # ── MACRO BONUS — coin-specific context from MacroIntelligence ──────
            # Coin's own 24h trend relative to BTC + Fear&Greed + dominance
            macro_bonus = 0.0
            if self.macro is not None and _macro_ctx:
                try:
                    _coin_ctx = self.macro.get_entry_context(info.pair)
                    macro_bonus = _coin_ctx.get("macro_score", 0.0)  # -2.0 → +2.0
                except Exception:
                    pass

            # ── WAVE BONUS — ocean wave scanner (cached, no new API calls) ───
            # Reads the waveform result from the last pre_strike_research scan.
            # Rewards coins where bot resonance is in harmony with our direction;
            # penalises coins where bots are in active dissonance.
            # Never triggers a new waveform fetch — uses cache only.
            wave_bonus = 0.0
            _waveform = getattr(self.intel, 'waveform', None)
            if _waveform is not None and HAS_NUMPY and info.binance_symbol:
                _wc = _waveform._spectral_cache.get(info.binance_symbol, {})
                _wc_age = time.time() - _waveform._cache_times.get(
                    f"wave_{info.binance_symbol}", 0)
                if _wc.get('available') and _wc_age < 120:
                    _res_score = _wc.get('resonance_score', 0)
                    _res_label = _wc.get('resonance_label', 'neutral')
                    _flow_pred = _wc.get('flow_prediction', 'neutral')
                    _dom_bot   = _wc.get('dominant_bot', 'organic')
                    _shape     = _wc.get('shape', 'mixed')

                    # Resonance score: -1 → +1 (bots against us → bots with us)
                    wave_bonus += _res_score * 1.0

                    # Flow prediction alignment with our intended side
                    _flow_align = {
                        ('buy',  'strong_buy_building'):  0.5,
                        ('buy',  'buy_fading'):           0.1,
                        ('buy',  'strong_sell_building'): -0.5,
                        ('sell', 'strong_sell_building'): 0.5,
                        ('sell', 'sell_fading'):          0.1,
                        ('sell', 'strong_buy_building'):  -0.5,
                    }
                    wave_bonus += _flow_align.get((side, _flow_pred), 0.0)

                    # Dominant bot type quality (accumulator = whale, hft = noise)
                    _bot_q = {'accumulator': 0.3, 'organic': 0.2,
                              'scalper': 0.1, 'market_maker': 0.0, 'hft': -0.1}
                    wave_bonus += _bot_q.get(_dom_bot, 0.0)

                    # Energy surge: amplifies signal if aligned, worsens if hostile
                    if _shape == 'surge':
                        wave_bonus += 0.25 if _res_label == 'harmony' else -0.25

                    wave_bonus = round(max(-2.0, min(2.0, wave_bonus)), 3)
                    logger.debug(
                        f"[Wave] {info.pair} {side}: res={_res_score:+.2f} "
                        f"flow={_flow_pred} bot={_dom_bot} shape={_shape} "
                        f"→ wave_bonus={wave_bonus:+.2f}"
                    )

            harmonic = self._score_harmonic_margin_scanner(
                symbol=info.pair,
                side=side,
                current_price=info.last_price,
                momentum_pct=abs(info.momentum),
                required_pct=required_move_pct,
                leverage=max_lev,
            )
            quantum = self._score_quantum_mirror_scanner(
                symbol=info.pair,
                side=side,
                current_price=info.last_price,
                momentum_pct=float(info.momentum),
                spread_pct=float(info.spread_pct),
            )
            timeline = self._score_timeline_oracle(
                symbol=info.pair,
                side=side,
                current_price=info.last_price,
                volume=float(info.volume_24h),
                change_pct=float(info.momentum),
            )
            fusion = self._score_harmonic_fusion(symbol=info.pair, side=side)
            whale = self._score_whale_orderbook(
                symbol=info.binance_symbol or info.pair,
                side=side,
                current_price=info.last_price,
                spread_pct=float(info.spread_pct),
            )
            live_tv = self._score_live_tv_station(
                symbol=info.base_clean or info.base or info.pair,
                side=side,
                fallback_momentum=float(info.momentum),
            )
            ocean = self._score_ocean_wave_scanner(
                symbol=info.binance_symbol or info.pair,
                side=side,
            )

            # ── NEW INTELLIGENCE SCORES ─────────────────────────────
            # Tier 1: High-impact signal producers
            phase_t = self._score_phase_transition(symbol=info.pair, side=side, current_price=info.last_price)
            prob_ult = self._score_prob_ultimate(symbol=info.pair, side=side, current_price=info.last_price, momentum_pct=float(info.momentum))
            news_sig = self._score_news_signal(symbol=info.base_clean or info.base or info.pair, side=side)
            phantom = self._score_phantom_filter(symbol=info.binance_symbol or info.pair, side=side)
            global_fin = self._score_global_financial(symbol=info.pair, side=side)
            whale_beh = self._score_whale_behavior(symbol=info.binance_symbol or info.pair, side=side)
            kraken_sig = self._score_kraken_signal_bridge(symbol=info.pair, side=side, current_price=info.last_price)
            truth_pred = self._score_truth_prediction(symbol=info.pair, side=side, current_price=info.last_price, momentum_pct=float(info.momentum))
            prob_nex = self._score_prob_nexus(symbol=info.pair, side=side)
            # Tier 2: Market intelligence & context
            real_int = self._score_real_intel(symbol=info.pair, side=side)
            organism = self._score_market_organism(symbol=info.pair, side=side)
            elephant = self._score_elephant(symbol=info.pair, side=side, current_price=info.last_price, momentum_pct=float(info.momentum))
            adv_int = self._score_advanced_intel(symbol=info.pair, side=side)
            reality = self._score_reality_detector(symbol=info.pair, side=side)
            g_wave = self._score_global_wave(symbol=info.pair, side=side)
            obsidian = self._score_obsidian(symbol=info.pair, side=side, current_price=info.last_price)
            # Tier 3: Harmonic, resonance & correlation
            schumann = self._score_schumann(symbol=info.pair, side=side)
            h_nexus = self._score_harmonic_nexus(symbol=info.pair, side=side)
            earth_res = self._score_earth_resonance(symbol=info.pair, side=side)
            m_harp = self._score_market_harp(symbol=info.pair, side=side)
            c_map = self._score_crypto_map(symbol=info.pair, side=side)
            sensory = self._score_sensory(symbol=info.pair, side=side)
            # Tier 4: Infrastructure with signal value
            w_sonar = self._score_whale_sonar(symbol=info.binance_symbol or info.pair, side=side)
            hive_st = self._score_hive_state(symbol=info.pair, side=side)
            incept = self._score_inception(symbol=info.pair, side=side)

            total_score = (ease_score * 3 + lev_score * 3 + spread_score * 2
                          + momentum_score + vol_score + conviction_bonus + hive_bonus
                          + goal_score * 2          # weight 2 — quickest profitable signal wins
                          + macro_bonus * 1.5       # weight 1.5 — macro context shapes the battlefield
                          + wave_bonus * 1.5        # weight 1.5 — ocean wave scanner bot resonance
                          + harmonic["bonus"] * 1.5
                          + quantum["bonus"] * 1.5
                          + timeline["bonus"] * 1.25
                          + fusion["bonus"] * 1.25
                          + whale["bonus"] * 1.25
                          + live_tv["bonus"] * 1.25
                          + ocean["bonus"] * 1.25
                          # ── Tier 1 new intelligence (high weight) ──
                          + phase_t["bonus"] * 1.5    # phase transition detector
                          + prob_ult["bonus"] * 1.5   # probability ultimate intelligence
                          + news_sig["bonus"] * 1.25  # news sentiment signal
                          + phantom["bonus"] * 1.5    # phantom signal filter
                          + global_fin["bonus"] * 1.25  # global financial feed
                          + whale_beh["bonus"] * 1.25   # whale behavior predictor
                          + kraken_sig["bonus"] * 1.5   # kraken unified signal bridge
                          + truth_pred["bonus"] * 1.25  # truth prediction engine
                          + prob_nex["bonus"] * 1.25    # probability nexus bridge
                          # ── Tier 2 market intelligence (medium weight) ──
                          + real_int["bonus"] * 1.0   # real intelligence engine
                          + organism["bonus"] * 1.0   # market organism
                          + elephant["bonus"] * 1.0   # elephant learning
                          + adv_int["bonus"] * 1.0    # advanced intelligence
                          + reality["bonus"] * 1.0    # reality detector
                          + g_wave["bonus"] * 1.0     # global wave scanner
                          + obsidian["bonus"] * 1.0   # obsidian filter
                          # ── Tier 3 harmonic & resonance (lower weight) ──
                          + schumann["bonus"] * 0.75  # schumann resonance
                          + h_nexus["bonus"] * 0.75   # harmonic nexus bridge
                          + earth_res["bonus"] * 0.75 # earth resonance
                          + m_harp["bonus"] * 0.75    # market harp
                          + c_map["bonus"] * 0.75     # crypto market map
                          + sensory["bonus"] * 0.75   # sensory framework
                          # ── Tier 4 infrastructure signals ──
                          + w_sonar["bonus"] * 1.0    # whale sonar
                          + hive_st["bonus"] * 0.75   # hive state
                          + incept["bonus"] * 0.75    # inception engine
                          )

            route_to_profit = goal_score / max(required_move_pct, 0.01)
            projection_summary = {
                "side": side,
                "confidence": max(
                    float(prob_nex.get("probability", 0.0) or 0.0),
                    float(truth_pred.get("confidence", 0.0) or 0.0),
                    float(quantum.get("beneficial_probability", 0.0) or 0.0),
                ),
                "live_match": min(1.0, stream_velocity),
                "edge": float(prob_nex.get("bonus", 0.0) or 0.0),
            }
            alignment_summary = {
                "score": (
                    float(timeline.get("bonus", 0.0) or 0.0)
                    + float(fusion.get("bonus", 0.0) or 0.0)
                    + float(harmonic.get("bonus", 0.0) or 0.0)
                    + float(quantum.get("bonus", 0.0) or 0.0)
                ) / 4.0,
                "timeline": timeline,
                "fusion": fusion,
                "harmonic": harmonic,
                "quantum": quantum,
            }
            self._candidate_cognition_context[self._cognition_key(info.pair, side)] = (
                self._build_candidate_cognition_context(
                    info=info,
                    side=side,
                    required_move_pct=required_move_pct,
                    eta_minutes=eta_minutes,
                    goal_score=goal_score,
                    route_to_profit=route_to_profit,
                    profit_target_usd=target_usd,
                    projection=projection_summary,
                    timeline=timeline,
                    alignment=alignment_summary,
                )
            )
            candidates.append((info, side, vol, trade_val, max_lev,
                              total_score, required_move_pct, round_trip_fee,
                              goal_score, eta_minutes, route_to_profit))

        if not candidates:
            logger.info("No valid candidates found")
            return None

        candidates = self._apply_brain_gate_to_candidates(candidates)
        if not candidates:
            logger.info("No candidates passed final brain gates")
            return None

        # Multiverse scout boost: if the multiverse already knows the next
        # stallion, give that pair a +2 score bonus so it wins the selection.
        _mv_next = (
            self.multiverse.get_next_stallion()
            if self.multiverse is not None else None
        )
        if _mv_next:
            boosted = []
            for item in candidates:
                info_obj, side, vol, tv, lev, score, req, fees, gs, eta, route = item
                bonus = 2.0 if info_obj.pair == _mv_next else 0.0
                if bonus:
                    logger.info(
                        f"[Multiverse] Boosting {info_obj.pair} score by +{bonus:.1f} "
                        f"(scouted as next stallion)"
                    )
                boosted.append((info_obj, side, vol, tv, lev, score + bonus, req, fees, gs, eta, route))
            candidates = boosted

        candidates.sort(key=lambda x: x[5], reverse=True)

        logger.info(
            f"TOP 7 TARGETS (goal: ${GOAL_TARGET_USD:.2f} net | fastest route ranked, "
            f"target ETA benchmark {GOAL_MAX_ETA_MINUTES:.0f}m):"
        )
        for i, (info, side, vol, tv, lev, score, req, fees, gs, eta, route) in enumerate(candidates[:7]):
            eta_str = f"{eta:.0f}m" if eta < 999 else "∞"
            logger.info(
                f"  #{i+1} {info.pair} {side.upper()} | "
                f"${tv:.0f} notional ({lev}x) | mom={info.momentum:+.2f}% | "
                f"spread={info.spread_pct:.3f}% | need={req:.3f}% | "
                f"eta≈{eta_str} | goal={gs:.2f} | route={route:.2f} | score={score:.3f}"
            )

        best = candidates[0]
        best_ctx = getattr(self, "_candidate_cognition_context", {}).get(
            self._cognition_key(best[0].pair, best[1]),
            {},
        )
        if best_ctx.get("brain_decision"):
            self._latest_margin_brain_decision = dict(best_ctx["brain_decision"])
            logger.info(
                f"[MarginBrain] chose {best[0].pair} {best[1].upper()} | "
                f"action={self._latest_margin_brain_decision.get('action')} "
                f"conf={float(self._latest_margin_brain_decision.get('confidence', 0.0) or 0.0):.2f} "
                f"eta={float(self._latest_margin_brain_decision.get('eta_minutes', 0.0) or 0.0):.2f}m"
            )
        self._feed_unified_decision_engine(
            best[0].pair,
            best[1],
            score=min(max(float(best[5]) / 10.0, 0.0), 1.0),
            metadata={
                "trade_value": float(best[3]),
                "leverage": int(best[4]),
                "required_move_pct": float(best[6]),
                "estimated_fees": float(best[7]),
                "goal_score": float(best[8]),
                "eta_min": float(best[9]),
                "route_to_profit": float(best[10]),
            },
        )
        # Store top candidates for fallback if intel rejects #1
        self._last_candidates = candidates[:7]
        self._publish_market_snapshot_to_thought_bus()
        self._refresh_thought_bus_snapshot()
        self._sync_market_watchlist(top_n=7)

        # Record this scan to the proof file (all candidates + winner)
        if self._goal_recorder is not None:
            try:
                self._pending_scan_id = self._goal_recorder.record_scan(
                    candidates_raw=candidates,
                    winner_pair=best[0].pair,
                    winner_side=best[1],
                )
            except Exception:
                pass

        return (best[0], best[1], best[2], best[3], best[4])

    # ----------------------------------------------------------
    #  PRE-STRIKE RESEARCH GATE (War Intelligence Before Entry)
    # ----------------------------------------------------------
    def research_target(self, pair_info: MarginPairInfo, side: str,
                        trade_val: float, leverage: int) -> tuple:
        """
        Run full battlefield research before committing capital.
        If intel says ABORT for our side, FLIP to the other side.
        
        Returns: (approved: bool, final_side: str)
          - approved=True, side=original  -> GO with original direction
          - approved=True, side=flipped   -> Intel said FLIP, go other way
          - approved=False, side=original -> Both directions rejected
        """
        if not pair_info.binance_symbol:
            logger.warning("No Binance symbol for intel - skipping research (CAUTION)")
            return (True, side)

        # ── MACRO INTELLIGENCE — log context alongside the buy signal ────────
        if self.macro is not None:
            try:
                logger.info(self.macro.summary_line(pair_info.pair))
            except Exception:
                pass

        # ── MULTIVERSE PRE-TRADE CONTEXT ─────────────────────────────────────
        # Before burning API calls on full research, check what the shadow herd
        # already knows about this pair from parallel tracking.
        if self.learning_bridge is not None:
            try:
                mv_ctx = self.learning_bridge.get_pre_trade_context(pair_info.pair)
                rec    = mv_ctx.get('recommendation', 'HOLD')
                conviction = mv_ctx.get('conviction', 0.5)
                phase  = mv_ctx.get('phase', 'UNKNOWN')
                logger.info(
                    f"[LearningBridge] Pre-trade: {pair_info.pair} | "
                    f"phase={phase} | conviction={conviction:.2f} | rec={rec} | "
                    f"seer={mv_ctx.get('seer_aligned')} lyra={mv_ctx.get('lyra_aligned')}"
                )
                if mv_ctx.get('stubborn_bucking'):
                    logger.warning(
                        f"[LearningBridge] {pair_info.pair} has been BUCKING in shadow "
                        f"for 45+ min — treat this as a caution signal"
                    )
            except Exception:
                pass

        # Calculate required move for profit
        profit_target_usd = self._dynamic_profit_target_for_trade(trade_val)
        round_trip_fee, _, _ = self._estimate_round_trip_fee(
            trade_val, symbol=pair_info.pair
        )
        required_move_pct, _, _ = self._estimate_required_move_pct(
            trade_val, profit_target_usd, symbol=pair_info.pair
        )

        research = self.intel.pre_strike_research(
            symbol=pair_info.binance_symbol,
            side=side,
            required_move_pct=required_move_pct,
            kraken_pair=pair_info.pair,
        )

        verdict = research.get('verdict', 'ABORT')
        confidence = research.get('confidence', 0)

        if verdict == "GO":
            logger.info(f"INTEL: GO signal for {pair_info.pair} {side.upper()} (confidence={confidence:.2f})")
            return (True, side)
        elif verdict == "CAUTION":
            if confidence >= 0.4:
                logger.info(f"INTEL: CAUTION but proceeding {side.upper()} (confidence={confidence:.2f} >= 0.4)")
                return (True, side)
            # Low-confidence caution — try flipping

        # === ABORT or low-confidence CAUTION: FLIP DIRECTION ===
        # The intel that was used to FEAR is now used to CAPITALIZE
        flip_side = "sell" if side == "buy" else "buy"
        logger.info(
            f"INTEL: {verdict} for {pair_info.pair} {side.upper()} "
            f"— FLIPPING to {flip_side.upper()} (using fear as fuel)"
        )

        # Check if the flipped side has leverage available
        flip_levs = pair_info.leverage_sell if flip_side == "sell" else pair_info.leverage_buy
        if not flip_levs:
            logger.warning(f"  No {flip_side} leverage for {pair_info.pair} — cannot flip")
            return (False, side)

        # Research the flipped side
        flip_research = self.intel.pre_strike_research(
            symbol=pair_info.binance_symbol,
            side=flip_side,
            required_move_pct=required_move_pct,
            kraken_pair=pair_info.pair,
        )

        fv = flip_research.get('verdict', 'ABORT')
        fc = flip_research.get('confidence', 0)

        if fv == "GO":
            logger.info(f"INTEL: FLIP CONFIRMED — {flip_side.upper()} is GO (confidence={fc:.2f})")
            return (True, flip_side)
        elif fv == "CAUTION" and fc >= 0.35:
            logger.info(f"INTEL: FLIP to {flip_side.upper()} CAUTION but proceeding (confidence={fc:.2f})")
            return (True, flip_side)
        else:
            logger.warning(
                f"INTEL: Both {side.upper()} and {flip_side.upper()} rejected for {pair_info.pair}"
            )
            return (False, side)

    # ----------------------------------------------------------
    #  EXECUTION - Kraken API (open/close only)
    # ----------------------------------------------------------
    def _terminal_fill_receipt(
        self,
        receipt: Any,
        *,
        expected_order_id: str,
        expected_side: str,
        expected_quantity: float,
    ) -> Optional[Dict[str, Any]]:
        """Validate a complete, fresh terminal provider fill without defaults."""
        required_flags = (
            isinstance(receipt, dict)
            and receipt.get("status") == "FILLED"
            and receipt.get("data_status") == "live"
            and receipt.get("truth_status") == "real_observed"
            and receipt.get("fill_receipt_complete") is True
            and receipt.get("eligible_for_accounting") is True
            and receipt.get("generated_values") is False
            and str(receipt.get("orderId") or "") == expected_order_id
            and str(receipt.get("side") or "").upper() == expected_side.upper()
        )
        if not required_flags:
            return None
        source_timestamp = self._fresh_receipt_timestamp(
            receipt.get("provider_timestamp"),
            max_age=PROVIDER_RECEIPT_MAX_AGE_SEC,
        )
        quantity = self._observed_number(receipt.get("executedQty"), positive=True)
        price = self._observed_number(receipt.get("filled_avg_price"), positive=True)
        notional = self._observed_number(receipt.get("cummulativeQuoteQty"), positive=True)
        fee = self._observed_number(receipt.get("fee"), nonnegative=True)
        fee_asset = receipt.get("fee_asset")
        source_id = receipt.get("source_id")
        fills = receipt.get("fills")
        if (
            source_timestamp is None
            or quantity is None
            or price is None
            or notional is None
            or fee is None
            or not isinstance(fee_asset, str)
            or not fee_asset.strip()
            or not isinstance(source_id, str)
            or not source_id
            or not isinstance(fills, list)
            or not fills
        ):
            return None
        trade_ids = [
            str(item.get("tradeId") or "")
            for item in fills
            if isinstance(item, dict) and item.get("tradeId")
        ]
        if (
            len(trade_ids) != len(fills)
            or len(set(trade_ids)) != len(trade_ids)
            or not math.isclose(quantity, expected_quantity, rel_tol=1e-8, abs_tol=1e-12)
            or not math.isclose(notional, quantity * price, rel_tol=1e-3, abs_tol=1e-8)
        ):
            return None
        return {
            "status": "FILLED",
            "data_status": "live",
            "truth_status": "real_observed",
            "order_id": expected_order_id,
            "side": expected_side.lower(),
            "quantity": quantity,
            "price": price,
            "notional": notional,
            "fee": fee,
            "fee_asset": fee_asset.strip().upper(),
            "source_id": source_id,
            "source_timestamp": source_timestamp,
            "trade_ids": trade_ids,
            "generated_values": False,
            "fill_receipt_complete": True,
            "eligible_for_accounting": True,
        }

    def _readback_terminal_fill_once(
        self,
        submission: Dict[str, Any],
        *,
        expected_side: str,
        expected_quantity: float,
    ) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Perform at most one hardened QueryOrders readback."""
        order_id = str(submission.get("orderId") or "")
        if not order_id:
            return None, None
        try:
            readback = self.client.get_order_status(order_id)
        except Exception as exc:
            logger.warning("Kraken order %s readback unavailable: %s", order_id, exc)
            return None, None
        fill = self._terminal_fill_receipt(
            readback,
            expected_order_id=order_id,
            expected_side=expected_side,
            expected_quantity=expected_quantity,
        )
        return fill, readback if isinstance(readback, dict) else None

    @staticmethod
    def _terminal_without_fill(receipt: Any) -> bool:
        return (
            isinstance(receipt, dict)
            and receipt.get("data_status") == "live"
            and str(receipt.get("status") or "").upper() in {"CANCELED", "EXPIRED"}
            and receipt.get("generated_values") is False
        )

    def _commit_open_fill(
        self,
        fill: Dict[str, Any],
        pair_info: MarginPairInfo,
        side: str,
        leverage: int,
        profit_target_usd: Optional[float],
        cognition_context: Optional[dict],
        unresolved_key: str,
    ) -> ActiveTrade:
        price = fill["price"]
        volume = fill["quantity"]
        trade_value = fill["notional"]
        entry_fee = fill["fee"]
        target_usd = (
            float(profit_target_usd)
            if profit_target_usd is not None and float(profit_target_usd) > 0
            else self._dynamic_profit_target_for_trade(trade_value)
        )
        _, close_fee_rate = self._get_open_close_fee_rates(pair_info.pair)
        projected_close_fee = trade_value * close_fee_rate
        target_cost = entry_fee + projected_close_fee + target_usd
        target_price = price + target_cost / volume if side == "buy" else price - target_cost / volume
        cognition_plan = self._build_trade_cognition_plan(
            pair_info=pair_info,
            side=side,
            entry_price=price,
            target_price=target_price,
            trade_value=trade_value,
            profit_target_usd=target_usd,
            cognition_context=cognition_context,
        )
        if not isinstance(cognition_plan, dict):
            cognition_plan = {}
        cognition_plan["exit_fee_projection"] = {
            "amount": projected_close_fee,
            "accounting_eligible": False,
            "source": "configured_decision_policy",
        }
        trade = ActiveTrade(
            pair=pair_info.pair,
            side=side,
            volume=volume,
            entry_price=price,
            leverage=leverage,
            entry_fee=entry_fee,
            entry_time=fill["source_timestamp"],
            order_id=fill["order_id"],
            cost=trade_value,
            breakeven_price=target_price,
            binance_symbol=pair_info.binance_symbol,
            profit_target_usd=target_usd,
            cognition_plan=cognition_plan,
            entry_source_id=fill["source_id"],
            entry_source_timestamp=fill["source_timestamp"],
            entry_fee_asset=fill["fee_asset"],
            entry_fill_receipt_complete=True,
        )
        if side == "buy":
            self.active_long = trade
        else:
            self.active_short = trade
        self.active_trade = self.active_long or self.active_short
        self._unresolved_open_submissions.pop(unresolved_key, None)
        self._last_execution_receipt = {
            **fill,
            "action": "open_margin_position",
            "position_committed": True,
            "accounting_status": "live",
        }
        if trade.binance_symbol:
            self._start_stream_for(trade.binance_symbol)
        self._save_state()
        orchestrator = getattr(self, "orchestrator", None)
        if orchestrator is not None:
            try:
                orchestrator.register_position(
                    system="margin",
                    pair=pair_info.pair,
                    side=side,
                    value_usd=trade_value,
                    exchange="kraken",
                )
            except Exception as exc:
                logger.debug("Position register error: %s", exc)
        recorder = getattr(self, "_goal_recorder", None)
        scan_id = getattr(self, "_pending_scan_id", "")
        if recorder is not None and scan_id:
            try:
                recorder.link_order(scan_id, fill["order_id"])
            except Exception:
                pass
            self._pending_scan_id = ""
        return trade

    def open_position(
        self,
        pair_info: MarginPairInfo,
        side: str,
        volume: float,
        leverage: int,
        profit_target_usd: Optional[float] = None,
        cognition_context: Optional[dict] = None,
    ) -> Optional[ActiveTrade]:
        """Submit once; only a terminal provider fill may create a position."""
        side = str(side).lower()
        quantity = self._observed_number(volume, positive=True)
        leverage_number = self._observed_number(leverage, positive=True)
        if side not in {"buy", "sell"} or quantity is None or leverage_number is None:
            self._last_execution_receipt = {
                "status": "NOT_SUBMITTED",
                "data_status": "not_submitted",
                "reason": "invalid_margin_order_request",
                "position_committed": False,
            }
            return None
        leverage_value = int(leverage_number)
        if leverage_value != leverage_number:
            self._last_execution_receipt = {
                "status": "NOT_SUBMITTED",
                "data_status": "not_submitted",
                "reason": "invalid_noninteger_leverage",
                "position_committed": False,
            }
            return None
        unresolved = getattr(self, "_unresolved_open_submissions", None)
        if not isinstance(unresolved, dict):
            unresolved = {}
            self._unresolved_open_submissions = unresolved
        unresolved_key = f"{pair_info.pair}:{side}"
        pending = unresolved.get(unresolved_key)
        if isinstance(pending, dict):
            submission = pending["submission"]
            if not submission.get("orderId"):
                self._last_execution_receipt = {
                    "status": "PENDING_RECONCILIATION",
                    "data_status": "pending_reconciliation",
                    "reason": "ambiguous_submission_without_provider_order_id",
                    "position_committed": False,
                }
                return None
            fill, readback = self._readback_terminal_fill_once(
                submission,
                expected_side=side,
                expected_quantity=quantity,
            )
            if fill is not None:
                return self._commit_open_fill(
                    fill,
                    pending["pair_info"],
                    side,
                    pending["leverage"],
                    pending["profit_target_usd"],
                    pending["cognition_context"],
                    unresolved_key,
                )
            if self._terminal_without_fill(readback):
                unresolved.pop(unresolved_key, None)
            self._last_execution_receipt = {
                "status": "PENDING_RECONCILIATION",
                "data_status": "pending_reconciliation",
                "reason": "terminal_complete_fill_not_observed",
                "order_id": submission.get("orderId"),
                "position_committed": False,
            }
            return None
        if getattr(self, "dry_run", False):
            self._last_execution_receipt = {
                "status": "NOT_SUBMITTED",
                "data_status": "not_submitted",
                "reason": "dry_run_order_not_submitted",
                "position_committed": False,
            }
            return None
        if (self.active_long if side == "buy" else self.active_short) is not None:
            self._last_execution_receipt = {
                "status": "NOT_SUBMITTED",
                "data_status": "not_submitted",
                "reason": "margin_side_slot_already_occupied",
                "position_committed": False,
            }
            return None
        quote = self._fresh_provider_quote(pair_info.pair)
        if quote is None:
            self._last_execution_receipt = {
                "status": "NOT_SUBMITTED",
                "data_status": "no_data",
                "reason": "fresh_provider_quote_required",
                "position_committed": False,
            }
            return None
        try:
            account = self._get_margin_capital(force=True)
        except Exception as exc:
            self._last_execution_receipt = {
                "status": "NOT_SUBMITTED",
                "data_status": "no_data",
                "reason": f"fresh_provider_account_required:{exc}",
                "position_committed": False,
            }
            return None
        if quantity * quote["price"] / leverage_value > float(account.free_margin):
            self._last_execution_receipt = {
                "status": "NOT_SUBMITTED",
                "data_status": "live",
                "reason": "provider_free_margin_insufficient",
                "position_committed": False,
            }
            return None
        try:
            submission = self.client.place_margin_order(
                symbol=pair_info.pair,
                side=side,
                quantity=quantity,
                leverage=leverage_value,
                order_type="market",
            )
        except Exception as exc:
            logger.error("FAILED to submit open for %s: %s", pair_info.pair, exc)
            return None
        if not isinstance(submission, dict):
            submission = {}
        if submission.get("data_status") == "not_submitted" or submission.get("error"):
            self._last_execution_receipt = {**submission, "position_committed": False}
            return None
        pending = {
            "submission": submission,
            "pair_info": pair_info,
            "leverage": leverage_value,
            "profit_target_usd": profit_target_usd,
            "cognition_context": cognition_context,
        }
        fill, readback = self._readback_terminal_fill_once(
            submission,
            expected_side=side,
            expected_quantity=quantity,
        )
        if fill is not None:
            return self._commit_open_fill(
                fill,
                pair_info,
                side,
                leverage_value,
                profit_target_usd,
                cognition_context,
                unresolved_key,
            )
        if not self._terminal_without_fill(readback):
            unresolved[unresolved_key] = pending
        self._last_execution_receipt = {
            "status": "PENDING_RECONCILIATION",
            "data_status": "pending_reconciliation",
            "reason": "terminal_complete_fill_not_observed",
            "order_id": submission.get("orderId"),
            "position_committed": False,
        }
        return None

    def _clear_filled_trade(self, trade: ActiveTrade) -> None:
        if self.active_long and self.active_long.order_id == trade.order_id:
            self.active_long = None
        if self.active_short and self.active_short.order_id == trade.order_id:
            self.active_short = None
        self.active_trade = self.active_long or self.active_short

    def _deregister_filled_trade(self, trade: ActiveTrade) -> None:
        orchestrator = getattr(self, "orchestrator", None)
        if orchestrator is not None:
            try:
                orchestrator.deregister_position(
                    system="margin",
                    pair=trade.pair,
                    side=trade.side,
                )
            except Exception as exc:
                logger.debug("Position deregister error: %s", exc)

    def _commit_close_fill(
        self,
        fill: Dict[str, Any],
        trade: ActiveTrade,
        reason: str,
        unresolved_key: str,
    ) -> Dict[str, Any]:
        """Clear a provider-closed position; account only from complete receipts."""
        self._unresolved_close_submissions.pop(unresolved_key, None)
        self._clear_filled_trade(trade)
        entry_timestamp = self._observed_number(
            getattr(trade, "entry_source_timestamp", None),
            positive=True,
        )
        entry_cost = self._observed_number(getattr(trade, "cost", None), positive=True)
        entry_fee = self._observed_number(getattr(trade, "entry_fee", None), nonnegative=True)
        accounting_reason = None
        if (
            getattr(trade, "entry_fill_receipt_complete", False) is not True
            or not getattr(trade, "entry_source_id", "")
            or entry_timestamp is None
            or entry_cost is None
            or entry_fee is None
        ):
            accounting_reason = "complete_provider_entry_fill_receipt_required"
        elif str(getattr(trade, "entry_fee_asset", "")).upper() != fill["fee_asset"]:
            accounting_reason = "entry_and_exit_fee_assets_do_not_match"
        elif fill["source_timestamp"] - entry_timestamp >= KRAKEN_ROLLOVER_INTERVAL:
            accounting_reason = "provider_rollover_fee_receipt_unavailable"
        if accounting_reason:
            result = {
                **fill,
                "action": "close_margin_position",
                "position_closed": True,
                "accounting_status": "no_data",
                "eligible_for_learning": False,
                "reason": accounting_reason,
            }
            self._last_execution_receipt = result
            self._save_state()
            self._deregister_filled_trade(trade)
            return result
        gross_pnl = (
            fill["notional"] - entry_cost
            if trade.side == "buy"
            else entry_cost - fill["notional"]
        )
        total_fees = entry_fee + fill["fee"]
        net_pnl = gross_pnl - total_fees
        completed = {
            "status": "FILLED",
            "data_status": "live",
            "truth_status": "real_derived",
            "accounting_status": "live",
            "pair": trade.pair,
            "side": trade.side,
            "volume": fill["quantity"],
            "entry_price": trade.entry_price,
            "exit_price": fill["price"],
            "leverage": trade.leverage,
            "entry_fee": entry_fee,
            "exit_fee": fill["fee"],
            "fee_asset": fill["fee_asset"],
            "rollover_fees": 0.0,
            "total_fees": total_fees,
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "reason": reason,
            "entry_time": datetime.fromtimestamp(entry_timestamp).isoformat(),
            "exit_time": datetime.fromtimestamp(fill["source_timestamp"]).isoformat(),
            "hold_seconds": fill["source_timestamp"] - entry_timestamp,
            "order_id": trade.order_id,
            "close_order_id": fill["order_id"],
            "entry_source_id": trade.entry_source_id,
            "close_source_id": fill["source_id"],
            "source_timestamp": fill["source_timestamp"],
            "generated_values": False,
            "cognition_plan": getattr(trade, "cognition_plan", {}) or {},
            "cognition_verification": self._verify_trade_cognition(
                trade,
                current_price=fill["price"],
                validated_net_pnl=net_pnl,
            ),
        }
        self.completed_trades.append(completed)
        recorder = getattr(self, "_goal_recorder", None)
        if recorder is not None:
            try:
                recorder.record_outcome(trade.order_id, completed)
            except Exception:
                pass
        self.total_trades += 1
        self.total_profit += net_pnl
        if net_pnl > 0:
            self.winning_trades += 1
        getattr(self, "_fast_profit_capture_by_order", {}).pop(str(trade.order_id), None)
        self._last_execution_receipt = {
            **fill,
            "action": "close_margin_position",
            "position_closed": True,
            "accounting_status": "live",
        }
        self._save_state()
        self._deregister_filled_trade(trade)
        self._push_dashboard_state(force=True)
        return completed

    def close_position(
        self,
        reason: str = "PROFIT_TARGET",
        trade: Optional[ActiveTrade] = None,
    ) -> Optional[dict]:
        """Submit once; only a terminal provider fill may close local lifecycle."""
        trade = trade or self.active_trade
        if trade is None:
            return None
        close_side = "sell" if trade.side == "buy" else "buy"
        quantity = self._observed_number(trade.volume, positive=True)
        if quantity is None:
            self._last_execution_receipt = {
                "status": "NOT_SUBMITTED",
                "data_status": "not_submitted",
                "reason": "invalid_active_position_quantity",
                "position_closed": False,
            }
            return None
        unresolved = getattr(self, "_unresolved_close_submissions", None)
        if not isinstance(unresolved, dict):
            unresolved = {}
            self._unresolved_close_submissions = unresolved
        unresolved_key = str(trade.order_id)
        pending = unresolved.get(unresolved_key)
        if isinstance(pending, dict):
            submission = pending["submission"]
            if not submission.get("orderId"):
                self._last_execution_receipt = {
                    "status": "PENDING_RECONCILIATION",
                    "data_status": "pending_reconciliation",
                    "reason": "ambiguous_close_without_provider_order_id",
                    "position_closed": False,
                }
                return None
            fill, readback = self._readback_terminal_fill_once(
                submission,
                expected_side=close_side,
                expected_quantity=quantity,
            )
            if fill is not None:
                return self._commit_close_fill(
                    fill,
                    pending["trade"],
                    pending["reason"],
                    unresolved_key,
                )
            if self._terminal_without_fill(readback):
                unresolved.pop(unresolved_key, None)
            self._last_execution_receipt = {
                "status": "PENDING_RECONCILIATION",
                "data_status": "pending_reconciliation",
                "reason": "terminal_complete_close_fill_not_observed",
                "order_id": submission.get("orderId"),
                "position_closed": False,
            }
            return None
        if getattr(self, "dry_run", False):
            self._last_execution_receipt = {
                "status": "NOT_SUBMITTED",
                "data_status": "not_submitted",
                "reason": "dry_run_order_not_submitted",
                "position_closed": False,
            }
            return None
        if self._fresh_provider_quote(trade.pair) is None:
            self._last_execution_receipt = {
                "status": "NOT_SUBMITTED",
                "data_status": "no_data",
                "reason": "fresh_provider_quote_required",
                "position_closed": False,
            }
            return None
        try:
            submission = self.client.close_margin_position(
                symbol=trade.pair,
                side=close_side,
                volume=quantity,
                leverage=trade.leverage,
            )
        except Exception as exc:
            logger.error("FAILED to submit close for %s: %s", trade.pair, exc)
            return None
        if not isinstance(submission, dict):
            submission = {}
        if submission.get("data_status") == "not_submitted" or submission.get("error"):
            self._last_execution_receipt = {**submission, "position_closed": False}
            return None
        pending = {"submission": submission, "trade": trade, "reason": reason}
        fill, readback = self._readback_terminal_fill_once(
            submission,
            expected_side=close_side,
            expected_quantity=quantity,
        )
        if fill is not None:
            return self._commit_close_fill(fill, trade, reason, unresolved_key)
        if not self._terminal_without_fill(readback):
            unresolved[unresolved_key] = pending
        self._last_execution_receipt = {
            "status": "PENDING_RECONCILIATION",
            "data_status": "pending_reconciliation",
            "reason": "terminal_complete_close_fill_not_observed",
            "order_id": submission.get("orderId"),
            "position_closed": False,
        }
        return None

    # ----------------------------------------------------------
    #  MONITOR - FREE API price check + profit gate
    # ----------------------------------------------------------
    def _start_stream_for(self, binance_symbol: str):
        """Start or add a symbol to the live WebSocket stream."""
        if not self.stream:
            return
        if not self._stream_started:
            self.stream.start([binance_symbol])
            self._stream_started = True
            # Give WebSocket a moment to connect
            for _ in range(10):
                if self.stream.connected:
                    break
                time.sleep(0.3)
            if self.stream.connected:
                logger.info(f"LIVE STREAM: ARMED for {binance_symbol} — sub-second kill speed")
            else:
                logger.warning("LIVE STREAM: Connecting... will use REST fallback until ready")
        else:
            self.stream.add_symbol(binance_symbol)

    def _stream_age_ms(self) -> int:
        if not self.stream:
            return -1
        last = float(getattr(self.stream, "_last_msg_time", 0.0) or 0.0)
        if last <= 0:
            return -1
        return max(0, int((time.time() - last) * 1000))

    def _self_heal_stream_if_stale(self) -> None:
        """Proactively refresh the websocket if it stops advancing."""
        if not self.stream or not self._stream_started:
            return
        age_ms = self._stream_age_ms()
        if age_ms < 0 or age_ms < STREAM_STALE_MS:
            return
        now = time.time()
        if (now - self._last_stream_self_heal) < 15:
            return
        self._last_stream_self_heal = now
        logger.warning(
            f"LIVE STREAM: stale feed detected (age={age_ms}ms) — forcing watchlist refresh"
        )
        self._sync_market_watchlist(top_n=7)

    def _sync_market_watchlist(self, extra_symbols: Optional[List[str]] = None, top_n: int = 6) -> None:
        """Keep the live stream subscribed to the active market watchlist, not just one trade symbol."""
        if not self.stream:
            return
        symbols: List[str] = []

        if extra_symbols:
            symbols.extend([str(s).upper() for s in extra_symbols if s])

        for trade in (self.active_long, self.active_short):
            if trade and trade.binance_symbol:
                symbols.append(str(trade.binance_symbol).upper())

        for shadow in self.shadow_trades[: max(2, top_n)]:
            if shadow.binance_symbol:
                symbols.append(str(shadow.binance_symbol).upper())

        for cand in getattr(self, "_last_candidates", [])[:top_n]:
            try:
                info = cand[0]
            except Exception:
                continue
            bsym = getattr(info, "binance_symbol", "") or ""
            if bsym:
                symbols.append(str(bsym).upper())

        deduped: List[str] = []
        seen = set()
        for sym in symbols:
            if sym and sym not in seen:
                deduped.append(sym)
                seen.add(sym)

        if not deduped:
            return

        if not self._stream_started:
            self.stream.start(deduped)
            self._stream_started = True
            return

        self.stream.sync_symbols(deduped)

    def _kraken_margin_fast_profit_capture_decision(
        self,
        trade: ActiveTrade,
        *,
        current_price: float,
        net_pnl: float,
        validated_net_pnl: float,
        total_fees: float,
        exit_fee: float,
        rollover: float,
        stream_live: bool,
    ) -> Dict[str, Any]:
        """Decide whether a Kraken margin position has true profit worth capturing now."""
        now = time.time()
        hold_seconds = max(0.0, now - float(getattr(trade, "entry_time", now) or now))
        blockers: List[str] = []
        if not KRAKEN_FAST_PROFIT_CAPTURE_ENABLED:
            blockers.append("fast_profit_capture_disabled")
        if hold_seconds < KRAKEN_FAST_PROFIT_MIN_HOLD_SECS:
            blockers.append("min_hold_time_not_met")
        if validated_net_pnl < KRAKEN_FAST_PROFIT_MIN_USD:
            blockers.append("validated_net_profit_below_minimum_after_all_costs")
        if net_pnl < 0:
            blockers.append("raw_net_profit_negative_after_fees")

        capital = {
            "available": False,
            "equity": 0.0,
            "free_margin": 0.0,
            "margin_used": 0.0,
            "margin_level": 0.0,
            "collateral_pressure": False,
        }
        try:
            snapshot = self._get_margin_capital()
            margin_level = float(getattr(snapshot, "margin_level", 0.0) or 0.0)
            capital.update(
                {
                    "available": True,
                    "equity": round(float(getattr(snapshot, "equity", 0.0) or 0.0), 6),
                    "free_margin": round(float(getattr(snapshot, "free_margin", 0.0) or 0.0), 6),
                    "margin_used": round(float(getattr(snapshot, "margin_used", 0.0) or 0.0), 6),
                    "margin_level": round(margin_level, 6),
                    "collateral_pressure": bool(0 < margin_level < KRAKEN_FAST_PROFIT_COLLATERAL_WARN_PCT),
                }
            )
        except Exception as e:
            capital["reason"] = str(e)

        ready = bool(not blockers)
        decision = {
            "schema_version": 1,
            "generated_at": datetime.now().isoformat(),
            "mode": "kraken_margin_true_profit_first_past_the_post",
            "pair": trade.pair,
            "side": trade.side,
            "order_id": str(getattr(trade, "order_id", "")),
            "current_price": round(float(current_price), 8),
            "entry_price": round(float(trade.entry_price), 8),
            "volume": round(float(trade.volume), 12),
            "leverage": int(trade.leverage),
            "hold_seconds": round(hold_seconds, 3),
            "stream_live": bool(stream_live),
            "min_true_profit_usd": round(KRAKEN_FAST_PROFIT_MIN_USD, 6),
            "min_hold_seconds": round(KRAKEN_FAST_PROFIT_MIN_HOLD_SECS, 3),
            "gross_minus_all_costs_usd": round(float(net_pnl), 8),
            "validated_true_profit_usd": round(float(validated_net_pnl), 8),
            "costs": {
                "entry_fee_usd": round(float(getattr(trade, "entry_fee", 0.0) or 0.0), 8),
                "estimated_exit_fee_usd": round(float(exit_fee), 8),
                "rollover_fees_usd": round(float(rollover), 8),
                "total_costs_usd": round(float(total_fees), 8),
            },
            "collateral": capital,
            "ready_to_capture": ready,
            "blockers": blockers,
            "reason": "capture_true_profit_after_costs" if ready else ",".join(blockers),
            "collateral_note": (
                "Live Kraken trade-balance is checked because spot cash movement can reduce margin headroom."
                if capital.get("available")
                else "Collateral snapshot unavailable this cycle; profit decision still uses net fee math."
            ),
        }
        self._last_fast_profit_capture = decision
        if ready:
            if not hasattr(self, "_fast_profit_capture_by_order"):
                self._fast_profit_capture_by_order = {}
            self._fast_profit_capture_by_order[str(getattr(trade, "order_id", ""))] = decision
        return decision

    def _emit_monitor_snapshot(
        self,
        trade: ActiveTrade,
        hold_str: str,
        current_price: float,
        net_pnl: float,
        total_fees: float,
        need_pct: float,
        stream_live: bool,
        dtp_status_str: str,
        dtp_progress_str: str,
        danger_level: int = 0,
        danger_note: str = "SAFE",
    ) -> None:
        """Print a compact live terminal snapshot for the active trade."""
        src = "LIVE" if stream_live else "REST"
        dtp_text = dtp_status_str.replace("|", "").strip() if dtp_status_str else "DTP: idle"
        line = (
            f"[MONITOR] t={hold_str:<6} pair={trade.pair:<10} side={trade.side.upper():<4} "
            f"lev={trade.leverage}x src={src:<4} "
            f"entry=${trade.entry_price:,.4f} now=${current_price:,.4f} "
            f"net=${net_pnl:+.2f} fees=${total_fees:.2f} "
            f"target=${trade.breakeven_price:,.4f} dist={need_pct:+.2f}% "
            f"danger={danger_level}:{danger_note} {dtp_text} {dtp_progress_str}"
        )
        self._latest_monitor_line = line
        logger.info(line)
        self._push_dashboard_state()

    def _format_dtp_progress_bar(self, validated_net_pnl: float) -> str:
        """Visualize progress toward the first DTP activation threshold."""
        threshold_gbp = float(DTP_CONFIG.get("activation_threshold", 1.27) or 1.27)
        gbp_usd_rate = float(DTP_CONFIG.get("gbp_usd_rate", 1.27) or 1.27)
        threshold_usd = threshold_gbp * gbp_usd_rate
        current_usd = max(0.0, float(validated_net_pnl))
        progress = 1.0 if threshold_usd <= 0 else max(0.0, min(current_usd / threshold_usd, 1.0))
        filled = int(round(progress * 12))
        bar = "#" * filled + "-" * (12 - filled)
        current_gbp = current_usd / gbp_usd_rate if gbp_usd_rate > 0 else 0.0
        remaining_gbp = max(0.0, threshold_gbp - current_gbp)
        if progress >= 1.0:
            return f"DTP1=[{bar}] ARMED £{current_gbp:.2f}/£{threshold_gbp:.2f}"
        return f"DTP1=[{bar}] £{current_gbp:.2f}/£{threshold_gbp:.2f} rem=£{remaining_gbp:.2f}"

    def monitor_position(self, trade: Optional[ActiveTrade] = None) -> Optional[dict]:
        """
        Check a position using LIVE WebSocket stream (sub-second).
        Falls back to FREE Binance REST if stream unavailable.
        Returns completed trade dict if closed, else None.
        ALL COSTS INCLUDED: entry fee + estimated exit fee + rollover fees.
        """
        if trade is None:
            trade = self.active_trade
        if not trade:
            return None
        target_usd = self._trade_profit_target(trade)

        # === LIVE STREAM PRICE (sub-100ms) — preferred ===
        stream_live = False
        if self.stream and self.stream.is_alive():
            stream_price = self.stream.get_executable_price(
                trade.binance_symbol,
                side=trade.side,
            )
            if stream_price > 0:
                stream_live = True

        # === FLASH CRASH DETECTION (stream-only, sub-second) ===
        if stream_live and self.stream.flash_alert.get(trade.binance_symbol, False):
            flow = self.stream.get_flow_snapshot(trade.binance_symbol)
            logger.warning(
                f"⚡ FLASH ALERT: {trade.binance_symbol} moved >0.3% in <2s! "
                f"flow={flow['flow_direction']} vel={flow['trade_velocity']:.1f}/s "
                f"spread={flow['spread_pct']:.3f}%"
            )

        quote = self._fresh_provider_quote(trade.pair)
        if quote is None:
            msg = f"Fresh provider quote unavailable for {trade.pair}; refusing an unstamped close decision"
            if self.dry_run:
                logger.warning(msg)
                return None
            raise RuntimeError(msg)
        current_price = quote["price"]

        # Decision-only projection; never persist it as provider-observed fees.
        hold_time = time.time() - trade.entry_time
        rollover_periods = int(hold_time / KRAKEN_ROLLOVER_INTERVAL)
        projected_rollover = rollover_periods * trade.cost * KRAKEN_ROLLOVER_RATE
        _, projected_close_fee_rate = self._get_open_close_fee_rates(trade.pair)
        projected_target_cost = (
            trade.entry_fee
            + trade.cost * projected_close_fee_rate
            + projected_rollover
            + target_usd
        )
        projected_target_price = (
            trade.entry_price + projected_target_cost / trade.volume
            if trade.side == "buy"
            else trade.entry_price - projected_target_cost / trade.volume
        )

        if trade.side == "buy":
            gross_pnl = (current_price - trade.entry_price) * trade.volume
        else:
            gross_pnl = (trade.entry_price - current_price) * trade.volume

        exit_value = current_price * trade.volume
        _, close_fee_rate = self._get_open_close_fee_rates(trade.pair)
        exit_fee = exit_value * close_fee_rate
        rollover = projected_rollover
        net_pnl = gross_pnl - trade.entry_fee - exit_fee - rollover
        validated_net_pnl = self._validated_net_pnl(trade.pair, exit_value, net_pnl)
        total_fees = trade.entry_fee + exit_fee + rollover
        cognition_verification = self._verify_trade_cognition(
            trade,
            current_price=current_price,
            validated_net_pnl=validated_net_pnl,
        )

        if hold_time < 60:
            hold_str = f"{int(hold_time)}s"
        elif hold_time < 3600:
            hold_str = f"{hold_time/60:.1f}m"
        else:
            hold_str = f"{hold_time/3600:.1f}h"

        # Show clear target price
        need_to_target = projected_target_price - current_price if trade.side == "buy" else current_price - projected_target_price
        need_pct = need_to_target / current_price * 100 if current_price > 0 else 0

        # ── DEAD MAN'S SWITCH ─────────────────────────────────────────────────
        # Feed the fully-calculated net P&L (includes entry fee + exit fee est +
        # rollover) straight into the DTP engine.  Keyed by order_id so the
        # floor survives across monitoring cycles.
        dtp_status_str = ""
        dtp_progress_str = self._format_dtp_progress_bar(validated_net_pnl)
        if HAS_DTP and DynamicTakeProfit is not None:
            trade_key = getattr(trade, 'order_id', trade.pair)
            if trade_key not in self.dtp_trackers:
                self.dtp_trackers[trade_key] = DynamicTakeProfit(
                    activation_threshold_gbp=DTP_CONFIG['activation_threshold'],
                    gbp_usd_rate=DTP_CONFIG['gbp_usd_rate'],
                    trailing_distance_pct=DTP_CONFIG['trailing_distance_pct'],
                    thought_bus=getattr(self, 'thought_bus', None),
                )
                logger.info(
                    f"[DTP] Armed Dead Man's Switch for {trade.pair} "
                    f"(activates at £{DTP_CONFIG['activation_threshold']:.2f} net profit)"
                )
            dtp = self.dtp_trackers[trade_key]
            dtp_triggered, dtp_reason, dtp_state = dtp.update(validated_net_pnl)
            if dtp_state.activated:
                net_gbp = validated_net_pnl / DTP_CONFIG['gbp_usd_rate']
                dtp_status_str = (
                    f" | DTP: floor=£{dtp_state.floor_gbp:.2f} "
                    f"peak=£{dtp_state.peak_profit_gbp:.2f}"
                )
            if dtp_triggered:
                logger.info(f"[DTP] DEAD MAN TRIGGERED: {dtp_reason}")
                # Only fire DTP if net_pnl is positive — never close at a loss
                if validated_net_pnl >= 0:
                    return self.close_position(
                        reason=f"DTP_DEAD_MAN (floor=£{dtp_state.floor_gbp:.2f})",
                        trade=trade
                    )
                else:
                    logger.info(
                        f"[DTP] Holding — DTP triggered but validated_net=${validated_net_pnl:+.4f} < 0. "
                        f"Waiting for profit before closing."
                    )

        # ── STALLION PHASE ────────────────────────────────────────────────────
        fast_capture = self._kraken_margin_fast_profit_capture_decision(
            trade,
            current_price=current_price,
            net_pnl=net_pnl,
            validated_net_pnl=validated_net_pnl,
            total_fees=total_fees,
            exit_fee=exit_fee,
            rollover=rollover,
            stream_live=stream_live,
        )
        if fast_capture.get("ready_to_capture"):
            logger.info(
                "[KRAKEN FAST PROFIT] true net=%+.4f after all costs (fees=%.4f, hold=%.1fs) - closing now",
                validated_net_pnl,
                total_fees,
                hold_time,
            )
            return self.close_position(
                reason=f"FAST_PROFIT_CAPTURE (${validated_net_pnl:+.4f} true_after_costs)",
                trade=trade,
            )

        stallion_str = ""
        if HAS_STALLION and classify_phase is not None:
            # Pull live margin level for wave capacity (best-effort)
            _ml = 0.0
            try:
                _tb = self.client.get_trade_balance()
                _ml = float(_tb.get("margin_level", 0) or 0)
            except Exception:
                pass
            _dtp_activated  = dtp_state.activated  if HAS_DTP and 'dtp_state' in dir() else False
            _dtp_triggers   = dtp_state.trigger_count if _dtp_activated else 0
            _dtp_floor_gbp  = dtp_state.floor_gbp    if _dtp_activated else 0.0
            _dtp_peak_gbp   = dtp_state.peak_profit_gbp if _dtp_activated else 0.0

            snap = classify_phase(
                hold_seconds    = hold_time,
                entry_price     = trade.entry_price,
                current_price   = current_price,
                net_pnl         = net_pnl,
                trade_side      = trade.side,
                dtp_activated   = _dtp_activated,
                dtp_trigger_count = _dtp_triggers,
                dtp_floor_gbp   = _dtp_floor_gbp,
                dtp_peak_gbp    = _dtp_peak_gbp,
                margin_level    = _ml,
                leverage        = float(trade.leverage),
            )
            stallion_str = f" | STALLION:{snap.phase.value}"

        # ── LEARNING BRIDGE SYNC — push to Seer, Lyra, ThoughtBus ────────
        if self.learning_bridge is not None:
            try:
                self.learning_bridge.sync()
            except Exception:
                pass

        if validated_net_pnl >= target_usd:
            status = f"TARGET HIT +${validated_net_pnl:.2f} validated - CLOSING!"
        elif validated_net_pnl > 0:
            status = f"+${validated_net_pnl:.2f} validated (need ${target_usd - validated_net_pnl:.2f} more -> ${trade.breakeven_price:.4f})"
        elif gross_pnl > 0:
            status = f"Gross+ but fees/friction eating (validated ${validated_net_pnl:+.2f}, fees=${total_fees:.2f})"
        else:
            status = f"${validated_net_pnl:+.2f} validated | target=${trade.breakeven_price:.4f} ({need_pct:+.2f}% away)"

        danger_level = 0
        danger_note = "SAFE"
        logger.info(
            f"[{hold_str}] {trade.pair} {trade.side.upper()} {trade.leverage}x | "
            f"${trade.entry_price:,.4f} -> ${current_price:,.4f} | "
            f"Net: ${net_pnl:+.2f} raw / ${validated_net_pnl:+.2f} validated (fees:${total_fees:.2f}) | {status}"
            f"{' [LIVE]' if stream_live else ' [REST]'}"
            f"{dtp_status_str}"
            f"{stallion_str}"
        )

        # === MULTIVERSE: register real ride on first monitor call ===
        if self.multiverse is not None and not self._multiverse_ride_registered:
            self.multiverse.start_real_ride(
                pair       = trade.pair,
                entry_time = trade.entry_time,
            )
            self._multiverse_ride_registered = True

        # === 1-HOUR ROTATION CHECK — only rotate when profitable ===
        if self.multiverse is not None and self.multiverse.is_rotation_due():
            _next = self.multiverse.get_next_stallion()
            if validated_net_pnl >= target_usd:
                # Profitable — rotate to next stallion
                logger.info(
                    f"[Multiverse] 1-hour ride limit reached on {trade.pair} "
                    f"(validated_net=${validated_net_pnl:+.2f}) — rotating to next stallion: {_next or '?'}"
                )
                result = self.close_position(
                    reason=f"ROTATION_DUE (1h limit | next→{_next or '?'})",
                    trade=trade,
                )
                if _next and self.multiverse is not None:
                    self.multiverse.start_real_ride(_next, time.time())
                    self._multiverse_ride_registered = False
                return result
            else:
                # Underwater — hold, reset the rotation clock and keep riding
                logger.info(
                    f"[Multiverse] 1-hour rotation due on {trade.pair} "
                    f"but validated_net=${validated_net_pnl:+.4f} — HOLDING until profitable, "
                    f"resetting rotation clock."
                )
                if self.multiverse is not None:
                    self.multiverse.start_real_ride(trade.pair, time.time())  # reset clock

        # === THE GBP1 PROFIT GATE - close immediately ===
        if validated_net_pnl >= target_usd:
            return self.close_position(reason=f"PROFIT_TARGET (${validated_net_pnl:+.2f} validated)", trade=trade)

        # === LIVE STREAM INTEL (log-only, NO closing on loss) ===
        if stream_live and self.stream:
            flow = self.stream.get_flow_snapshot(trade.binance_symbol)
            # Log opposing flow as intel — but NEVER close on it
            opposing_flow = (
                (trade.side == "buy" and flow['sell_pct'] > 80) or
                (trade.side == "sell" and flow['buy_pct'] > 80)
            )
            if opposing_flow and flow['trade_velocity'] > 20:
                logger.info(
                    f"  STREAM: opposing flow {flow['flow_direction']} "
                    f"{flow['sell_pct' if trade.side == 'buy' else 'buy_pct']:.0f}% "
                    f"vel={flow['trade_velocity']:.0f}/s — HOLDING (no stop loss)"
                )
            # Spread info (log only)
            if flow['spread_pct'] > FLEE_SPREAD_BLOWOUT:
                logger.info(
                    f"  STREAM: Wide spread {flow['spread_pct']:.3f}% — watching"
                )

        # === WAR INTELLIGENCE: DEEP DANGER CHECK (every 15s) ===
        now = time.time()
        if now - self._last_danger_check >= self._danger_check_interval and trade.binance_symbol:
            self._last_danger_check = now
            try:
                danger = self.intel.check_danger(
                    symbol=trade.binance_symbol,
                    side=trade.side,
                    entry_price=trade.entry_price,
                    target_price=trade.breakeven_price,
                )
                dl = danger.get('danger_level', 0)
                danger_level = dl
                if dl > 0:
                    reasons = danger.get('reasons', [])
                    danger_note = reasons[0][:48] if reasons else "WATCH"
                    for r in danger.get('reasons', []):
                        logger.warning(f"  INTEL: {r}")
                else:
                    danger_note = "SAFE"
                    flow = danger.get('reasons', [])
                    # Show flow info from trade analysis
                    tf = self.intel._trades_cache.get(trade.binance_symbol, {})
                    flow_dir = tf.get('flow_direction', '?')
                    buy_pct = tf.get('buy_volume_pct', 50)
                    bot = tf.get('bot_type', 'none')
                    ob = self.intel._depth_cache.get(trade.binance_symbol, {})
                    imb = ob.get('imbalance', 1.0)
                    # Waveform info
                    wave_tag = ""
                    players_tag = ""
                    if self.intel.waveform and HAS_NUMPY:
                        try:
                            wc = self.intel.waveform._spectral_cache.get(trade.binance_symbol, {})
                            if wc.get('available'):
                                res = wc.get('resonance_score', 0)
                                dom = wc.get('dominant_bot', '?')
                                shp = wc.get('shape', '?')
                                fpred = wc.get('flow_prediction', '?')
                                wave_tag = f" | WAVE: {dom}/{shp} res={res:+.2f} {fpred}"
                                # Catalog the players and get summary
                                try:
                                    players_tag = " | PLAYERS: " + self.bot_catalog.get_battlefield_summary(
                                        trade.binance_symbol, wc
                                    )
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    # Live stream overlay
                    stream_tag = ""
                    if stream_live and self.stream:
                        sf = self.stream.get_flow_snapshot(trade.binance_symbol)
                        stream_tag = (
                            f" | STREAM: vel={sf['trade_velocity']:.0f}/s "
                            f"buy={sf['buy_pct']:.0f}% spread={sf['spread_pct']:.3f}%"
                        )
                    logger.info(
                        f"  INTEL: SAFE | flow={flow_dir} buy={buy_pct:.0f}% | "
                        f"depth_imb={imb:.2f} | bots={bot}{wave_tag}{stream_tag}"
                    )
                    if players_tag:
                        logger.info(f"  {players_tag}")

                # === INTEL IS EYES ONLY — NO CLOSING ON LOSS ===
                # Log danger for awareness but NEVER close at a loss
                if danger.get('flee'):
                    logger.warning(
                        f"  INTEL: Flee signal detected (level={dl}) — "
                        f"HOLDING (net=${net_pnl:+.2f}, no stop loss)"
                    )
                elif dl >= 2:
                    logger.warning(
                        f"  INTEL: Danger level {dl} — HOLDING "
                        f"(net=${net_pnl:+.2f}, no stop loss)"
                    )
                else:
                    pass  # Safe, nothing to report
            except Exception as e:
                logger.debug(f"Danger check error: {e}")

        self._emit_monitor_snapshot(
            trade=trade,
            hold_str=hold_str,
            current_price=current_price,
            net_pnl=net_pnl,
            total_fees=total_fees,
            need_pct=need_pct,
            stream_live=stream_live,
            dtp_status_str=dtp_status_str,
            dtp_progress_str=dtp_progress_str,
            danger_level=danger_level,
            danger_note=danger_note,
        )

        # === TRUTH CHECK: Reconcile with Kraken on a real interval, not modulo time.
        # Keep the monitor alive if Kraken private endpoints are slow/rate-limited;
        # the unified supervisor separately times the whole Kraken tick.
        if now - float(getattr(self, "_last_truth_check_at", 0.0) or 0.0) >= KRAKEN_TRUTH_CHECK_INTERVAL_SEC:
            self._last_truth_check_at = now
            try:
                tb = self.client.get_trade_balance()
                ml = tb.get("margin_level", 0)
                kraken_equity = tb.get("trade_balance", 0) + tb.get("unrealized_pnl", 0)

                # Get Kraken's actual position P&L
                positions = self.client.get_open_margin_positions(do_calcs=True)
                matching_positions = []
                for p in positions:
                    pp = p.get("pair", "")
                    alt = self.client._int_to_alt.get(pp, pp)
                    if alt == trade.pair or pp == trade.pair:
                        matching_positions.append(p)

                if not matching_positions:
                    raise RuntimeError(f"Kraken no longer reports live position for {trade.pair}")
                if len(matching_positions) > 1:
                    raise RuntimeError(f"Kraken reports multiple live positions for {trade.pair}; local state is ambiguous")

                p = matching_positions[0]
                kraken_pnl = p.get("net", p.get("unrealized_pnl", 0))
                kraken_fee = p.get("fee", 0)
                logger.info(
                    f"TRUTH CHECK: Kraken equity=${kraken_equity:.2f} ml={ml:.1f}% | "
                    f"Position pnl=${kraken_pnl:+.2f} fee=${kraken_fee:.4f} | "
                    f"Our net=${net_pnl:+.2f} fees=${total_fees:.4f}"
                )
                self._latest_truth_check = {
                    "generated_at": datetime.now().isoformat(),
                    "ok": True,
                    "pair": trade.pair,
                    "kraken_equity": float(kraken_equity or 0.0),
                    "margin_level": float(ml or 0.0),
                    "kraken_unrealized_pnl": float(kraken_pnl or 0.0),
                    "kraken_fee": float(kraken_fee or 0.0),
                    "local_net_pnl": float(net_pnl or 0.0),
                    "validated_net_pnl": float(validated_net_pnl or 0.0),
                }
                # Open-position telemetry is not a terminal fee receipt and
                # cannot rewrite fill accounting.
                if kraken_fee > 0 and abs(kraken_fee - trade.entry_fee) > 0.001:
                    logger.info(
                        f"Observed fee drift: Kraken=${kraken_fee:.4f} "
                        f"vs entry receipt=${trade.entry_fee:.4f}"
                    )

                if 0 < ml < LIQUIDATION_FORCE:
                    if validated_net_pnl >= 0:
                        return self.close_position(reason=f"LIQUIDATION_RISK (ml={ml:.0f}%)", trade=trade)
                    else:
                        logger.error(
                            f"LIQUIDATION DANGER: ml={ml:.0f}% but position underwater "
                            f"(validated_net=${validated_net_pnl:+.4f}) — HOLDING to avoid locking in loss"
                        )
                elif 0 < ml < LIQUIDATION_WARN:
                    logger.warning(f"WARNING: Margin level {ml:.1f}%")
            except Exception as e:
                self._latest_truth_check = {
                    "generated_at": datetime.now().isoformat(),
                    "ok": False,
                    "pair": trade.pair,
                    "error": str(e),
                    "using_local_position_state": True,
                }
                if self.dry_run:
                    logger.debug(f"Truth check failed: {e}")
                else:
                    logger.warning(f"Live truth check deferred: {e}")

        return None

    # ----------------------------------------------------------
    #  STATE PERSISTENCE (atomic writes)
    # ----------------------------------------------------------
    def _save_state(self):
        """Save current state atomically."""
        if getattr(self, "dry_run", False):
            return
        try:
            # Legacy active_trade = whichever is open (prefer long)
            at = self.active_long or self.active_short
            state = {
                "active_long": self.active_long.to_dict() if self.active_long else None,
                "active_short": self.active_short.to_dict() if self.active_short else None,
                "extra_active_longs": [trade.to_dict() for trade in self.extra_active_longs[-10:]],
                "extra_active_shorts": [trade.to_dict() for trade in self.extra_active_shorts[-10:]],
                "active_trade": at.to_dict() if at else None,
                "total_profit": self.total_profit,
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "shadow_validated": self.shadow_validated_count,
                "shadow_failed": self.shadow_failed_count,
                "completed_trades": self.completed_trades[-50:],
                "last_updated": datetime.now().isoformat(),
            }
            tmp = STATE_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(state, f, indent=2)
            os.replace(tmp, STATE_FILE)
            self._push_dashboard_state()
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _reconcile_live_positions(self) -> Dict[str, Any]:
        """Rebuild active Kraken margin slots from the exchange, even without local state."""
        live_positions_by_slot: Dict[str, Any] = {
            "active_long": None,
            "active_short": None,
            "extra_active_longs": [],
            "extra_active_shorts": [],
        }
        if self.dry_run:
            return live_positions_by_slot

        try:
            for kp in self.client.get_open_margin_positions(do_calcs=True):
                kp_pair = kp.get("pair", "")
                alt_pair = self.client._int_to_alt.get(kp_pair, kp_pair)
                side = kp.get("side", "")
                slot = "active_long" if side == "buy" else "active_short" if side == "sell" else None
                if slot is None:
                    continue

                volume = float(kp.get("volume", 0.0) or 0.0)
                cost = float(kp.get("cost", 0.0) or 0.0)
                fee_total = float(kp.get("fee", 0.0) or 0.0)
                entry_price = (cost / volume) if volume > 0 and cost > 0 else 0.0
                lev_raw = str(kp.get("leverage", "1") or "1").replace(":", "")
                try:
                    leverage = int(float(lev_raw))
                except Exception:
                    leverage = 1

                breakeven_price = entry_price
                target_usd = self._dynamic_profit_target_for_trade(cost)
                if volume > 0 and entry_price > 0:
                    if side == "buy":
                        breakeven_price = entry_price + (fee_total + target_usd) / volume
                    elif side == "sell":
                        breakeven_price = entry_price - (fee_total + target_usd) / volume

                trade = ActiveTrade(
                    pair=alt_pair,
                    side=side,
                    volume=volume,
                    entry_price=entry_price,
                    leverage=leverage,
                    entry_fee=fee_total,
                    entry_time=float(kp.get("open_time", time.time()) or time.time()),
                    order_id=str(kp.get("position_id", "")),
                    cost=cost,
                    breakeven_price=breakeven_price,
                    binance_symbol=self._binance_symbol_for_pair(alt_pair),
                    profit_target_usd=target_usd,
                )
                primary_trade = live_positions_by_slot[slot]
                extras_key = "extra_active_longs" if slot == "active_long" else "extra_active_shorts"
                if primary_trade is None:
                    live_positions_by_slot[slot] = trade
                else:
                    primary_key = (
                        float(getattr(primary_trade, "entry_time", 0.0) or 0.0),
                        -float(getattr(primary_trade, "cost", 0.0) or 0.0),
                    )
                    new_key = (
                        float(getattr(trade, "entry_time", 0.0) or 0.0),
                        -float(getattr(trade, "cost", 0.0) or 0.0),
                    )
                    if new_key < primary_key:
                        live_positions_by_slot[extras_key].append(primary_trade)
                        live_positions_by_slot[slot] = trade
                    else:
                        live_positions_by_slot[extras_key].append(trade)
        except Exception as e:
            raise RuntimeError(f"Live position reconciliation failed: {e}")

        return live_positions_by_slot

    def _load_state(self):
        """Load saved state — supports dual positions."""
        try:
            state: Dict[str, Any] = {}
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE) as f:
                    state = json.load(f)
            if self.dry_run:
                self.active_long = None
                self.active_short = None
                self.extra_active_longs = []
                self.extra_active_shorts = []
                self.active_trade = None
                self.total_profit = 0.0
                self.total_trades = 0
                self.winning_trades = 0
                self.completed_trades = []
                return

            valid_fields = {f.name for f in ActiveTrade.__dataclass_fields__.values()}
            live_positions_by_slot = self._reconcile_live_positions()
            self.extra_active_longs = list(live_positions_by_slot.get("extra_active_longs", []) or [])
            self.extra_active_shorts = list(live_positions_by_slot.get("extra_active_shorts", []) or [])

            # Load dual positions (new format)
            for slot, attr in [("active_long", "active_long"), ("active_short", "active_short")]:
                td = state.get(slot)
                reconciled = live_positions_by_slot.get(slot)
                if reconciled is not None:
                    if td:
                        filtered = {k: v for k, v in td.items() if k in valid_fields}
                        for key in ("breakeven_price", "rollover_fees", "last_rollover_check", "profit_target_usd", "cognition_plan"):
                            value = filtered.get(key)
                            if value not in (None, "", 0):
                                setattr(reconciled, key, value)
                    setattr(self, attr, reconciled)
                    logger.info(f"Resumed {slot} from Kraken: {reconciled.pair} {reconciled.side.upper()}")
                    if reconciled.binance_symbol:
                        self._start_stream_for(reconciled.binance_symbol)
                elif td and not self.dry_run:
                    logger.warning(f"Dropping stale local {slot}; Kraken shows no matching live margin position.")
                elif td:
                    filtered = {k: v for k, v in td.items() if k in valid_fields}
                    t = ActiveTrade(**filtered)
                    setattr(self, attr, t)
                    logger.info(f"Resumed {slot}: {t.pair} {t.side.upper()}")
                    if t.binance_symbol:
                        self._start_stream_for(t.binance_symbol)

            # Legacy: load old single active_trade into correct slot
            if self.dry_run and not self.active_long and not self.active_short:
                td = state.get("active_trade")
                if td:
                    filtered = {k: v for k, v in td.items() if k in valid_fields}
                    t = ActiveTrade(**filtered)
                    if t.side == "buy":
                        self.active_long = t
                    else:
                        self.active_short = t
                    logger.info(f"Resumed active trade (legacy): {t.pair} {t.side.upper()}")
                    if t.binance_symbol:
                        self._start_stream_for(t.binance_symbol)

            # Keep active_trade alias pointing at something
            self.active_trade = self.active_long or self.active_short

            # Register restored positions with orchestrator for cross-system awareness
            if self.orchestrator is not None:
                for pos in (self.active_long, self.active_short, *self.extra_active_longs, *self.extra_active_shorts):
                    if pos is not None:
                        try:
                            self.orchestrator.register_position(
                                system='margin',
                                pair=pos.pair,
                                side=pos.side,
                                value_usd=pos.cost,
                                exchange='kraken',
                            )
                        except Exception as e:
                            logger.debug(f"Restored position register error: {e}")

            self.total_profit = state.get("total_profit", 0)
            self.total_trades = state.get("total_trades", 0)
            self.winning_trades = state.get("winning_trades", 0)
            self.shadow_validated_count = state.get("shadow_validated", 0)
            self.shadow_failed_count = state.get("shadow_failed", 0)
            self.completed_trades = state.get("completed_trades", [])
            if self.extra_active_longs or self.extra_active_shorts:
                logger.warning(
                    "Kraken startup found extra live positions; keeping one primary slot per side and tracking extras "
                    "(extra_longs=%s extra_shorts=%s)",
                    len(self.extra_active_longs),
                    len(self.extra_active_shorts),
                )
            if not self.dry_run:
                self._save_state()
        except Exception as e:
            if not self.dry_run:
                raise RuntimeError(f"Live startup state load failed: {e}")
            logger.warning(f"Could not load state: {e}")

    def _save_results(self):
        """Save completed trades."""
        try:
            results = {
                "session_start": datetime.fromtimestamp(self.start_time).isoformat(),
                "session_end": datetime.now().isoformat(),
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "total_profit": self.total_profit,
                "completed_trades": self.completed_trades,
            }
            with open(RESULTS_FILE, "w") as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

    # ----------------------------------------------------------
    #  DISPLAY
    # ----------------------------------------------------------
    def print_universe(self):
        """Print margin pairs ranked by suitability."""
        pairs_with_price = [p for p in self.margin_pairs.values() if p.last_price > 0]
        pairs_with_price.sort(key=lambda x: x.max_leverage * abs(x.momentum), reverse=True)

        print()
        print(f"{'=' * 90}")
        print(f"  MARGIN ARMY - {len(pairs_with_price)} pairs with Binance prices")
        print(f"{'=' * 90}")
        print(f"  {'Pair':<12} {'Binance':<12} {'Price':>12} {'Spread':>8} "
              f"{'MaxLev':>7} {'Mom%':>8} {'24hVol':>14}")
        print(f"  {'-' * 85}")

        for info in pairs_with_price[:30]:
            print(
                f"  {info.pair:<12} {info.binance_symbol:<12} "
                f"${info.last_price:>11,.4f} "
                f"{info.spread_pct:>7.3f}% "
                f"{info.max_leverage:>5}x "
                f"{info.momentum:>+7.2f}% "
                f"${info.volume_24h:>13,.0f}"
            )

        if len(pairs_with_price) > 30:
            print(f"  ... and {len(pairs_with_price) - 30} more")
        no_price = len(self.margin_pairs) - len(pairs_with_price)
        if no_price > 0:
            print(f"  ({no_price} pairs had no Binance match)")
        print(f"{'=' * 90}")
        print()

    # ----------------------------------------------------------
    #  SHADOW VALIDATION — simulate before deploying real capital
    # ----------------------------------------------------------
    SHADOW_MAX_AGE = 120       # Kill shadows older than 2 min
    SHADOW_MIN_VALIDATE = 10   # Must be validated for at least 10s
    SHADOW_MAX_ACTIVE = 4      # Max simultaneous shadows
    SHADOW_PAIR_COOLDOWN = 45  # Block rapid same-pair reversals between scans

    def _set_shadow_cooldown(self, pair: str, seconds: Optional[int] = None):
        """Temporarily prevent rapid re-shadowing of the same pair."""
        ttl = float(seconds if seconds is not None else self.SHADOW_PAIR_COOLDOWN)
        self.shadow_pair_cooldowns[pair] = time.time() + max(1.0, ttl)

    def _shadow_cooldown_remaining(self, pair: str) -> float:
        """Return the remaining cooldown for a pair and prune expired entries."""
        until = self.shadow_pair_cooldowns.get(pair, 0.0)
        remaining = until - time.time()
        if remaining <= 0:
            self.shadow_pair_cooldowns.pop(pair, None)
            return 0.0
        return remaining

    def create_shadow(self, pair_info: MarginPairInfo, side: str,
                      vol: float, trade_val: float, lev: int) -> Optional[ShadowTrade]:
        """Create a paper trade to validate a prediction."""
        if len(self.shadow_trades) >= self.SHADOW_MAX_ACTIVE:
            logger.debug("Shadow slots full — skipping")
            return None

        cooldown_left = self._shadow_cooldown_remaining(pair_info.pair)
        if cooldown_left > 0:
            logger.debug(
                f"Shadow cooldown active for {pair_info.pair} "
                f"({cooldown_left:.0f}s remaining) — skipping"
            )
            return None

        # Don't shadow a pair we already have a real or shadow position on
        existing_pairs = set()
        if self.active_long:
            existing_pairs.add(self.active_long.pair)
        if self.active_short:
            existing_pairs.add(self.active_short.pair)
        for s in self.shadow_trades:
            existing_pairs.add(s.pair)

        if pair_info.pair in existing_pairs:
            return None

        # Get entry price from live stream or REST
        entry_price = 0.0
        if self.stream and self.stream.is_alive() and pair_info.binance_symbol:
            entry_price = self.stream.get_live_price(pair_info.binance_symbol)
        if entry_price <= 0:
            entry_price = self.market.get_single_price(pair_info.binance_symbol)
        if entry_price <= 0:
            entry_price = pair_info.last_price
        if entry_price <= 0:
            return None

        profit_target_usd = self._dynamic_profit_target_for_trade(trade_val)
        required_move_pct, open_fee_rate, close_fee_rate = self._estimate_required_move_pct(
            trade_val, profit_target_usd, symbol=pair_info.pair
        )
        round_trip_fee_pct = (open_fee_rate + close_fee_rate) * 100
        target_move_pct = required_move_pct
        cognition_context = dict(
            getattr(self, "_candidate_cognition_context", {}).get(
                self._cognition_key(pair_info.pair, side),
                {},
            )
        )
        if not cognition_context:
            eta_minutes = 999.0
            if abs(pair_info.momentum) > 0:
                pct_per_minute = abs(pair_info.momentum) / (24 * 60) * max(1, lev)
                eta_minutes = required_move_pct / pct_per_minute if pct_per_minute > 0 else 999.0
            cognition_context = self._build_candidate_cognition_context(
                info=pair_info,
                side=side,
                required_move_pct=required_move_pct,
                eta_minutes=eta_minutes,
                goal_score=0.0,
                route_to_profit=0.0,
                profit_target_usd=profit_target_usd,
            )
        brain_decision = dict(cognition_context.get("brain_decision", {}) or {})
        if brain_decision and not bool(brain_decision.get("approved", True)):
            logger.info(
                f"[MarginBrain] {pair_info.pair} {side.upper()} chose WAIT before shadow: "
                f"{'; '.join(brain_decision.get('vetoes', []) or ['not enough support'])}"
            )
            return None

        shadow = ShadowTrade(
            pair=pair_info.pair,
            side=side,
            binance_symbol=pair_info.binance_symbol,
            entry_price=entry_price,
            created_at=time.time(),
            target_move_pct=target_move_pct,
            leverage=lev,
            volume=vol,
            trade_val=trade_val,
            pair_info_key=pair_info.pair,
            profit_target_usd=profit_target_usd,
            cognition_context=cognition_context,
        )

        self.shadow_trades.append(shadow)
        self._set_shadow_cooldown(pair_info.pair)

        # Start stream for this symbol
        if pair_info.binance_symbol:
            self._start_stream_for(pair_info.binance_symbol)

        logger.info(
            f"SHADOW OPENED: {pair_info.pair} {side.upper()} {lev}x | "
            f"entry=${entry_price:,.4f} | need {target_move_pct:.3f}% move | "
            f"Watching prediction play out..."
        )
        return shadow

    def update_shadows(self):
        """Update all shadow trades with live prices. Expire stale ones."""
        expired = []
        for shadow in self.shadow_trades:
            price = 0.0
            if self.stream and self.stream.is_alive():
                price = self.stream.get_live_price(shadow.binance_symbol)
            if price <= 0:
                price = self.market.get_single_price(shadow.binance_symbol)
            if price > 0:
                shadow.update(price)

            # Expire shadows that are too old without validating
            if shadow.age_seconds > self.SHADOW_MAX_AGE and not shadow.validated:
                expired.append(shadow)
                self.shadow_failed_count += 1
                self._set_shadow_cooldown(shadow.pair, seconds=self.SHADOW_PAIR_COOLDOWN * 2)
                logger.info(
                    f"SHADOW EXPIRED: {shadow.pair} {shadow.side.upper()} | "
                    f"age={shadow.age_seconds:.0f}s | moved {shadow.current_move_pct:+.3f}% "
                    f"(needed {shadow.target_move_pct:.3f}%) — prediction WRONG"
                )

        for s in expired:
            self.shadow_trades.remove(s)

    def promote_shadow(self, shadow: ShadowTrade) -> Optional[ActiveTrade]:
        """
        Shadow validated — deploy REAL capital on this prediction.
        Returns the real ActiveTrade if successfully opened.
        """
        # Check correct slot is free
        if shadow.side == "buy" and self.active_long:
            logger.debug(f"Long slot occupied — cannot promote {shadow.pair}")
            return None
        if shadow.side == "sell" and self.active_short:
            logger.debug(f"Short slot occupied — cannot promote {shadow.pair}")
            return None

        # Get the pair info
        pair_info = self.margin_pairs.get(shadow.pair_info_key)
        if not pair_info:
            logger.warning(f"Pair info missing for {shadow.pair_info_key}")
            return None
        brain_decision = dict(getattr(shadow, "cognition_context", {}).get("brain_decision", {}) or {})
        if brain_decision and not bool(brain_decision.get("approved", True)):
            logger.info(
                f"SHADOW VALIDATED but MarginBrain says WAIT for {shadow.pair}: "
                f"{'; '.join(brain_decision.get('vetoes', []) or ['not enough support'])}"
            )
            self._set_shadow_cooldown(shadow.pair, seconds=self.SHADOW_PAIR_COOLDOWN * 2)
            self.shadow_trades.remove(shadow)
            return None

        # Run intel research on the validated shadow
        approved, final_side = self.research_target(
            pair_info, shadow.side, shadow.trade_val, shadow.leverage
        )

        if not approved:
            logger.info(
                f"SHADOW VALIDATED but intel says NO for {shadow.pair} — skipping promotion"
            )
            self._set_shadow_cooldown(shadow.pair, seconds=self.SHADOW_PAIR_COOLDOWN * 2)
            self.shadow_trades.remove(shadow)
            return None

        # Use the intel's final_side (may have flipped)
        side = final_side
        lev = shadow.leverage
        if side != shadow.side:
            flip_levs = pair_info.leverage_sell if side == "sell" else pair_info.leverage_buy
            lev = max(flip_levs) if flip_levs else lev

        split_slot = (side == "buy" and self.active_short) or (side == "sell" and self.active_long)
        plan = self._plan_dynamic_margin_position(pair_info, lev, split_slot=split_slot)
        if plan is None or not plan.approved:
            reason = "dynamic sizer unavailable" if plan is None else plan.reason
            logger.warning(f"Not enough safe margin to promote shadow: {reason}")
            return None

        notional = plan.notional
        vol = plan.volume
        shadow.trade_val = notional
        shadow.volume = vol
        shadow.profit_target_usd = plan.profit_target_usd

        # ── WAVE RIDER: final 250% margin gate before real capital ────
        if self.wave_rider:
            try:
                tb2 = self.client.get_trade_balance()
                eq2 = float(tb2.get("equity", tb2.get("equity_value", 0)) or 0)
                mu2 = float(tb2.get("margin_amount", tb2.get("m", 0)) or 0)
                free2 = float(tb2.get("free_margin", tb2.get("margin_free", tb2.get("mf", 0))) or 0)
            except Exception:
                eq2, mu2, free2 = 0.0, 0.0, 0.0

            if eq2 > 0:
                wave_ok, wave_check = self.wave_rider.check(eq2, mu2, notional, lev, free_margin=free2)
                if not wave_ok:
                    if wave_check.max_safe_notional >= plan.min_notional:
                        # Cap to safe size rather than abandoning entirely
                        notional = min(wave_check.max_safe_notional, notional)
                        logger.info(
                            f"[WaveRider] Shadow {shadow.pair}: notional capped to "
                            f"${notional:.2f} — projected margin "
                            f"{wave_check.projected_margin_pct:.0f}% >= "
                            f"{self.wave_rider.entry_min:.0f}%"
                        )
                    else:
                        logger.warning(
                            f"[WaveRider] Shadow {shadow.pair}: BLOCKED — "
                            f"{wave_check.reason} — waiting for margin to recover"
                        )
                        # Leave shadow in place; retry next scan cycle
                        return None
                else:
                    logger.info(
                        f"[WaveRider] Shadow {shadow.pair}: APPROVED — "
                        f"{wave_check.reason}"
                    )

        vol = notional / pair_info.last_price if pair_info.last_price > 0 else shadow.volume
        vol = max(vol, pair_info.ordermin)
        vol = round(vol, pair_info.lot_decimals)
        shadow.volume = vol
        shadow.trade_val = vol * pair_info.last_price if pair_info.last_price > 0 else notional

        logger.info(
            f"SHADOW VALIDATED -> DEPLOYING REAL: {shadow.pair} {side.upper()} {lev}x | "
            f"Shadow moved {shadow.peak_pnl_pct:+.3f}% in {shadow.age_seconds:.0f}s | "
            f"Prediction CONFIRMED — going LIVE!"
        )

        trade = self.open_position(
            pair_info,
            side,
            vol,
            lev,
            profit_target_usd=shadow.profit_target_usd,
            cognition_context=shadow.cognition_context,
        )
        if trade:
            self.shadow_validated_count += 1
            self._start_stream_for(trade.binance_symbol)
            tag = "FLIPPED" if side != shadow.side else "CONFIRMED"
            logger.info(
                f"ARMY DEPLOYED (shadow-validated): {trade.pair} {side.upper()} | "
                f"Intel {tag} | Shadow peak={shadow.peak_pnl_pct:+.3f}%"
            )

        # Remove the shadow regardless of success
        if shadow in self.shadow_trades:
            self._set_shadow_cooldown(shadow.pair, seconds=self.SHADOW_PAIR_COOLDOWN * 2)
            self.shadow_trades.remove(shadow)
        return trade

    def print_status(self):
        """Print current status — dual positions + shadows."""
        runtime = time.time() - self.start_time
        hours = int(runtime // 3600)
        mins = int((runtime % 3600) // 60)
        capital = self._get_capital_snapshot()
        equity_delta = capital["equity"] - self.starting_equity if self.starting_equity > 0 else 0.0
        realized = sum(float(t.get("net_pnl", 0.0) or 0.0) for t in self.completed_trades)
        closed_count = len(self.completed_trades)
        avg_net = realized / closed_count if closed_count else 0.0
        wins = sum(1 for t in self.completed_trades if float(t.get("net_pnl", 0.0) or 0.0) > 0)
        losses = sum(1 for t in self.completed_trades if float(t.get("net_pnl", 0.0) or 0.0) <= 0)
        win_rate = (wins / closed_count * 100.0) if closed_count else 0.0
        best_trade = max(self.completed_trades, key=lambda t: float(t.get("net_pnl", 0.0) or 0.0), default=None)
        worst_trade = min(self.completed_trades, key=lambda t: float(t.get("net_pnl", 0.0) or 0.0), default=None)
        recent_trades = list(reversed(self.completed_trades[-3:]))
        status_lines = [
            f"ARMY STATUS | Runtime: {hours}h {mins}m",
            (
                f"Equity=${capital['equity']:.2f} Free=${capital['free_margin']:.2f} "
                f"Used=${capital['margin_used']:.2f} UPNL=${capital['unrealized']:+.2f}"
            ),
            (
                f"Budget=${capital['budget']:.2f} Target=${capital['profit_target_usd']:.2f} "
                f"EqDelta=${equity_delta:+.2f}"
            ),
        ]
        if self.stream:
            stream_mode = "LIVE" if self.stream.is_alive() else ("CONNECTED" if self.stream.connected else "REST")
            stream_age_ms = (
                max(0, int((time.time() - getattr(self.stream, "_last_msg_time", 0.0)) * 1000))
                if getattr(self.stream, "_last_msg_time", 0.0)
                else -1
            )
            stream_error = str(getattr(self.stream, "_last_error", "") or "")
            status_lines.append(
                f"Stream: {stream_mode} watch={len(getattr(self.stream, '_symbols', []))} "
                f"reconnects={getattr(self.stream, '_reconnect_count', 0)} "
                f"msgs={getattr(self.stream, 'msg_count', 0)} age_ms={stream_age_ms}"
            )
            if stream_error:
                status_lines.append(f"StreamErr: {stream_error[:90]}")
        for label, trade in [("LONG", self.active_long), ("SHORT", self.active_short)]:
            if trade:
                status_lines.append(
                    f"{label}: {trade.pair} {trade.side.upper()} {trade.leverage}x @ ${trade.entry_price:,.4f}"
                )
            else:
                status_lines.append(f"{label}: EMPTY")
        if self.extra_active_longs or self.extra_active_shorts:
            status_lines.append(
                f"ExtraLive: longs={len(self.extra_active_longs)} shorts={len(self.extra_active_shorts)}"
            )
        fast_capture = getattr(self, "_last_fast_profit_capture", {}) or {}
        if fast_capture:
            status_lines.append(
                "FastProfit: "
                f"ready={bool(fast_capture.get('ready_to_capture'))} "
                f"net=${float(fast_capture.get('validated_true_profit_usd', 0.0) or 0.0):+.4f} "
                f"reason={fast_capture.get('reason') or 'measuring'}"
            )
        status_lines.append(
            f"History: closed={closed_count} wins={wins} losses={losses} win_rate={win_rate:.1f}% avg={avg_net:+.2f}"
        )
        if recent_trades:
            for t in recent_trades:
                pnl = float(t.get('net_pnl', 0.0) or 0.0)
                status_lines.append(
                    f"CLOSE: {t.get('pair', '?')} {str(t.get('side', '?')).upper()} ${pnl:+.2f} reason={t.get('reason', '?')}"
                )
        self._latest_status_lines = status_lines

        print()
        print(f"{'=' * 65}")
        print(f"  ARMY STATUS | Runtime: {hours}h {mins}m")
        print(f"  Equity: ${capital['equity']:.2f} | Free: ${capital['free_margin']:.2f} | Used: ${capital['margin_used']:.2f} | UPNL: ${capital['unrealized']:+.2f}")
        print(f"  Budget: ${capital['budget']:.2f} | Target/trade: ${capital['profit_target_usd']:.2f} ({capital['target_pct_equity']:.3f}% of equity) | Since start: ${equity_delta:+.2f}")
        if self.stream:
            stream_mode = "LIVE" if self.stream.is_alive() else ("CONNECTED" if self.stream.connected else "REST")
            stream_age_ms = (
                max(0, int((time.time() - getattr(self.stream, "_last_msg_time", 0.0)) * 1000))
                if getattr(self.stream, "_last_msg_time", 0.0)
                else -1
            )
            print(
                f"  Stream: {stream_mode} | watch={len(getattr(self.stream, '_symbols', []))} "
                f"| reconnects={getattr(self.stream, '_reconnect_count', 0)} "
                f"| msgs={getattr(self.stream, 'msg_count', 0)} | age_ms={stream_age_ms}"
            )

        # Dual position display
        for label, trade in [("LONG", self.active_long), ("SHORT", self.active_short)]:
            if trade:
                age = time.time() - trade.entry_time
                if age < 60:
                    age_str = f"{int(age)}s"
                elif age < 3600:
                    age_str = f"{age/60:.1f}m"
                else:
                    age_str = f"{age/3600:.1f}h"
                # Stallion phase for status display
                phase_str = ""
                if HAS_STALLION and classify_phase is not None:
                    try:
                        _snap = classify_phase(
                            hold_seconds=age,
                            entry_price=trade.entry_price,
                            current_price=getattr(trade, 'last_price', trade.entry_price),
                            net_pnl=0.0,
                            trade_side=trade.side,
                        )
                        phase_str = f" | {_snap.phase.value}"
                    except Exception:
                        pass
                print(f"  {label}: {trade.pair} {trade.side.upper()} {trade.leverage}x | "
                      f"${trade.entry_price:,.4f} | age={age_str}{phase_str}")
            else:
                print(f"  {label}: EMPTY (scanning)")

        # Shadow trades
        if self.shadow_trades:
            print(f"  Shadows: {len(self.shadow_trades)} active")
            for s in self.shadow_trades:
                v = "VALIDATED" if s.validated else f"{s.current_move_pct:+.3f}%"
                print(f"    {s.pair} {s.side.upper()} | {v} | age={s.age_seconds:.0f}s")
        else:
            print(f"  Shadows: none (will create on next scan)")

        # Multiverse status + learning bridge status
        if self.multiverse is not None:
            for mv_line in self.multiverse.status_lines():
                print(mv_line)
        if self.learning_bridge is not None:
            for lb_line in self.learning_bridge.learning_status_lines():
                print(lb_line)
        if self.orchestrator is not None:
            for orch_line in self.orchestrator.status_report():
                print(orch_line)
        if self._registry_snapshot.get("categories"):
            category_count = len(self._registry_snapshot.get("categories", {}))
            print(f"  [UNIFIED REGISTRY] categories={category_count} linked")
        if self._decision_snapshot:
            ds = self._decision_snapshot
            if ds.get("decision"):
                decision = ds["decision"]
                print(
                    f"  [DECISION ENGINE] {ds.get('symbol', '?')} {ds.get('side', '?')} "
                    f"-> {decision.get('type', '?')} conf={float(decision.get('confidence', 0.0)):.2f}"
                )
            elif ds.get("error"):
                print(f"  [DECISION ENGINE] error={ds['error']}")
        latest_brain = getattr(self, "_latest_margin_brain_decision", {})
        if latest_brain:
            print(
                f"  [MARGIN BRAIN] {latest_brain.get('pair', '?')} "
                f"{str(latest_brain.get('side', '?')).upper()} "
                f"{latest_brain.get('action', '?')} "
                f"conf={float(latest_brain.get('confidence', 0.0) or 0.0):.2f} "
                f"risk={float(latest_brain.get('risk', 0.0) or 0.0):.2f} "
                f"eta={float(latest_brain.get('eta_minutes', 0.0) or 0.0):.2f}m"
            )
        if self._thought_bus_snapshot:
            tbs = self._thought_bus_snapshot
            if tbs.get("error"):
                print(f"  [THOUGHT BUS] error={tbs['error']}")
            else:
                print(
                    f"  [THOUGHT BUS] market={int(tbs.get('market_events', 0) or 0)} "
                    f"decision={int(tbs.get('decision_events', 0) or 0)}"
                )
        if self._cognition_snapshot:
            cs = self._cognition_snapshot
            if cs.get("error"):
                print(f"  [COGNITION] error={cs['error']}")
            else:
                print(
                    f"  [COGNITION] brain={int(cs.get('cognition_events', 0) or 0)} "
                    f"queen={int(cs.get('queen_events', 0) or 0)}"
                )
        if self._timeline_snapshot:
            ts = self._timeline_snapshot
            if ts.get("action"):
                print(
                    f"  [TIMELINE] {ts.get('symbol', '?')} {ts.get('action', '?')} "
                    f"conf={float(ts.get('confidence', 0.0) or 0.0):.2f}"
                )
            elif ts.get("error"):
                print(f"  [TIMELINE] error={ts['error']}")
        if self._fusion_snapshot:
            fs = self._fusion_snapshot
            if "global_coherence" in fs:
                print(
                    f"  [FUSION] {fs.get('symbol', '?')} global={float(fs.get('global_coherence', 0.0) or 0.0):.2f} "
                    f"symbol={float(fs.get('symbol_coherence', 0.0) or 0.0):.2f} "
                    f"phase={float(fs.get('phase_alignment', 0.0) or 0.0):+.2f}"
                )
            elif fs.get("error"):
                print(f"  [FUSION] error={fs['error']}")
        if self._whale_snapshot:
            ws = self._whale_snapshot
            if "wall_count" in ws:
                print(
                    f"  [WHALE] {ws.get('symbol', '?')} walls={int(ws.get('wall_count', 0) or 0)} "
                    f"layer={float(ws.get('layering_score', 0.0) or 0.0):.2f} "
                    f"imb={float(ws.get('depth_imbalance', 0.0) or 0.0):+.2f}"
                )
            elif ws.get("error"):
                print(f"  [WHALE] error={ws['error']}")
        if self._live_tv_snapshot:
            lt = self._live_tv_snapshot
            if "hz" in lt:
                print(
                    f"  [LIVE TV] {lt.get('symbol', '?')} hz={float(lt.get('hz', 0.0) or 0.0):.1f} "
                    f"mom={float(lt.get('momentum', 0.0) or 0.0):+.2f}% "
                    f"vol={float(lt.get('volatility', 0.0) or 0.0):.3f}%"
                )
            elif lt.get("error"):
                print(f"  [LIVE TV] error={lt['error']}")
        if self._ocean_snapshot:
            oc = self._ocean_snapshot
            if "bots" in oc:
                print(
                    f"  [OCEAN] {oc.get('symbol', '?')} bots={int(oc.get('bots', 0) or 0)} "
                    f"whales={int(oc.get('whales', 0) or 0)} "
                    f"agg={float(oc.get('aggression', 0.0) or 0.0):.2f}"
                )
            elif oc.get("error"):
                print(f"  [OCEAN] error={oc['error']}")

        print()
        print(f"  Trades: {self.total_trades} ({self.winning_trades} wins)")
        print(f"  Shadows: {self.shadow_validated_count} validated, {self.shadow_failed_count} failed")
        print(f"  Session P&L tracker: ${self.total_profit:+.2f}")
        print(f"  Realized history: {closed_count} closed | wins={wins} losses={losses} | win-rate={win_rate:.1f}% | avg=${avg_net:+.2f}")
        if best_trade:
            print(f"  Best trade: {best_trade['pair']} {best_trade['side'].upper()} ${float(best_trade.get('net_pnl', 0.0) or 0.0):+.2f} | reason={best_trade.get('reason', '?')}")
        if worst_trade:
            print(f"  Worst trade: {worst_trade['pair']} {worst_trade['side'].upper()} ${float(worst_trade.get('net_pnl', 0.0) or 0.0):+.2f} | reason={worst_trade.get('reason', '?')}")
        if recent_trades:
            print(f"  Recent closes:")
            for t in recent_trades:
                pnl = float(t.get("net_pnl", 0.0) or 0.0)
                hold_s = float(t.get("hold_seconds", 0.0) or 0.0)
                hold_str = f"{hold_s/60:.1f}m" if hold_s >= 60 else f"{int(hold_s)}s"
                print(
                    f"    {t.get('pair', '?')} {str(t.get('side', '?')).upper()} "
                    f"${pnl:+.2f} | hold={hold_str} | reason={t.get('reason', '?')}"
                )
        print(f"  Target: ${capital['profit_target_usd']:.2f} per trade (dynamic)")
        print(f"{'=' * 65}")
        print()

    # ----------------------------------------------------------
    #  MISSION HUNT: SELECT WINNER → OPEN → HOLD UNTIL PROFIT
    # ----------------------------------------------------------
    def mission_hunt(self, side_filter: str = None) -> dict:
        """
        Mission hunt — scan for the best live setup, enter once confirmed,
        then hold until realized net profit after all fees clears the target.

        DISCIPLINE:
          Selection IS the gate. Open only when the fastest high-conviction
          setup is available. The 1-minute signal is an entry benchmark, not a
          forced holding limit.

        ENTRY CRITERIA (all must pass):
          ✓ 3+ consecutive 1-minute candles in same direction (streak)
          ✓ Last candle volume >= 1.2× average of previous 5 candles (surge)
          ✓ Momentum score > 0.75% net move on last 3 candles
          ✓ Spread < 0.3%
          ✓ Leverage >= 3×
          ✓ Required breakeven move <= 1-minute ATR (achievable in 1 minute)

        EXECUTION:
          → Open market order (Kraken margin)
          → Monitor continuously from Binance data
          → Close only when realized net profit clears the configured target

        ARGS:
          side_filter : 'buy' | 'sell' | None (None = hunt both directions)
        """
        MONITOR_POLL_SEC     = 2       # Price check interval
        MIN_STREAK           = 2       # Need direction confirmation, not perfection
        MIN_VOLUME_SURGE     = 1.05    # Accept smaller but real participation
        MIN_MOM_PCT          = 0.30    # Favor momentum that can still compound with leverage
        MIN_LAST_CANDLE_PCT  = 0.08    # Current impulse should be alive, but not extreme
        MAX_SPREAD_PCT       = 0.45    # Allow more pairs; scoring still penalizes wide spread
        MIN_LEVERAGE         = 3       # Minimum leverage to bother
        MISSION_PROFIT_MIN   = PROFIT_TARGET_USD  # Updated after live capital snapshot
        SCAN_INTERVAL_SEC    = 1       # Seconds between re-scans when hunting
        HUNT_TIMEOUT_SEC     = 300     # Keep hunting for up to 5 minutes per patrol
        MIN_PROJ_CONF        = 0.52    # Projection should lean clearly, not just random drift
        MIN_PROJ_LIVE        = 0.40    # Live tape should agree with projection often enough
        MIN_ALIGNMENT_SCORE  = -0.25   # Weak disagreement allowed, strong dissonance rejected

        mode_tag = "DRY RUN" if self.dry_run else "LIVE"
        direction_tag = ("SHORT ONLY ↓" if side_filter == "sell"
                         else "LONG ONLY ↑" if side_filter == "buy"
                         else "LONG + SHORT")
        print("=" * 70)
        print(f"  🎯 MISSION HUNT  |  Mode: {mode_tag}  |  Direction: {direction_tag}")
        print("  Discipline: SELECT WINNER → OPEN → HOLD UNTIL REALIZED PROFIT")
        print("  Signal: streak + volume surge + momentum + spread + leverage")
        print("  Entry gate: ALL criteria must pass – no exceptions")
        print("=" * 70)
        seer_verdict, seer_confidence, seer_bonus = self._get_seer_bias()
        self._refresh_unified_intel_snapshot()

        # ── Step 0: Orchestrator cycle sync ────────────────────────────────
        if self.orchestrator is not None:
            self.orchestrator.cycle_sync()

        # ── Step 1: Discover universe and live prices ──────────────────────
        # Skip re-discovery if already loaded (pride mode calls hunt repeatedly)
        if not self.margin_pairs:
            self.discover_margin_universe()
        self.update_prices_free()

        # ── Step 2: Check available capital ───────────────────────────────
        try:
            capital = self._get_capital_snapshot()
            free_margin = capital["free_margin"]
            equity = capital["equity"]
            MISSION_PROFIT_MIN = capital["profit_target_usd"]
            capital_snapshot = getattr(self, "_last_margin_capital", None)
        except Exception as e:
            logger.error(f"MISSION: Cannot get trade balance: {e}")
            return {'traded': False, 'reason': 'balance_error', 'net_pnl': 0.0,
                    'pair': None, 'side': None}

        margin_budget = capital["budget"]
        print(f"\n💰 Capital: ${equity:.2f} equity  |  ${free_margin:.2f} free"
              f"  |  Budget: ${margin_budget:.2f}")
        if equity > 0:
            print(
                f"   Goal metrics: target ${MISSION_PROFIT_MIN:.2f} = {MISSION_PROFIT_MIN / equity * 100:.3f}% of equity"
                f" | budget usage {margin_budget / equity * 100:.1f}%"
            )

        if free_margin < 5.0:
            print("❌ MISSION ABORTED: Insufficient free margin (need $5+)")
            return {'traded': False, 'reason': 'insufficient_margin', 'net_pnl': 0.0,
                    'pair': None, 'side': None}

        # ── Step 3: Scan 1-minute Binance klines for momentum signals ─────
        print("\n🔍 Scanning 1-minute momentum signals across margin universe...")
        candidates = []
        reject_stats = {
            "kline_fetch": 0,
            "short_history": 0,
            "streak": 0,
            "surge": 0,
            "exhaustion": 0,
            "momentum": 0,
            "impulse": 0,
            "side_filter": 0,
            "leverage": 0,
            "notional": 0,
            "atr_frozen": 0,
            "projection_side": 0,
            "projection_conf": 0,
            "projection_live": 0,
            "alignment": 0,
        }

        valid_pairs = [
            (pair, info) for pair, info in self.margin_pairs.items()
            if (info.binance_symbol
                and info.last_price > 0
                and info.spread_pct <= MAX_SPREAD_PCT
                and (max(info.leverage_buy or [0]) >= MIN_LEVERAGE or
                     max(info.leverage_sell or [0]) >= MIN_LEVERAGE))
        ]

        MAX_SCAN_PAIRS = 24
        valid_pairs.sort(
            key=lambda item: (
                max((item[1].leverage_buy or [0]) + (item[1].leverage_sell or [0])),
                abs(item[1].momentum),
                -item[1].spread_pct,
                item[1].volume_24h,
            ),
            reverse=True,
        )
        scan_pairs = valid_pairs[:MAX_SCAN_PAIRS]

        print(f"   Universe: {len(valid_pairs)} pairs with Binance symbol, spread"
              f" ≤{MAX_SPREAD_PCT}%, leverage ≥{MIN_LEVERAGE}×")

        macro_ctx = {}
        if self.macro is not None:
            try:
                macro_ctx = self.macro.get_entry_context("")
                logger.info(self.macro.summary_line(""))
            except Exception:
                macro_ctx = {}

        for pair_name, info in scan_pairs:
            bsym = info.binance_symbol
            try:
                url = (f"{BINANCE_KLINES_URL}?symbol={bsym}"
                       f"&interval=1m&limit=10")
                req = urllib.request.Request(
                    url, headers={"User-Agent": "MissionHunt/1.0"})
                with urllib.request.urlopen(req, timeout=5) as r:
                    klines = json.loads(r.read().decode())
            except Exception:
                reject_stats["kline_fetch"] += 1
                continue

            if len(klines) < 6:
                reject_stats["short_history"] += 1
                continue

            # kline layout: [open_time, open, high, low, close, volume, ...]
            closes  = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]

            # ── Candle direction streak (last MIN_STREAK candles) ──────────
            # Work from the most-recent complete candle backwards (skip last
            # partially-formed candle by analysing klines[-2] as "last closed")
            # Use closes[-6] .. closes[-1] for analysis (6 complete candles)
            c = closes[-7:]   # 7 values → 6 candle bodies
            v = volumes[-7:]

            directions = []
            for i in range(1, len(c)):
                if c[i] > c[i - 1]:
                    directions.append(1)     # bullish
                elif c[i] < c[i - 1]:
                    directions.append(-1)    # bearish
                else:
                    directions.append(0)     # doji

            # Streak: count consecutive matching direction at the end
            streak_dir   = directions[-1]    # direction of most recent candle
            streak_count = 0
            for d in reversed(directions):
                if d == streak_dir:
                    streak_count += 1
                else:
                    break

            if streak_count < MIN_STREAK or streak_dir == 0:
                reject_stats["streak"] += 1
                continue   # Streak gate

            # ── Volume surge: last vs avg of prior 5 ──────────────────────
            last_vol = v[-1]
            avg_vol  = sum(v[-6:-1]) / 5 if len(v) >= 6 else last_vol
            vol_surge = last_vol / avg_vol if avg_vol > 0 else 1.0

            if vol_surge < MIN_VOLUME_SURGE:
                reject_stats["surge"] += 1
                continue   # Volume surge gate

            # ── Climax/Exhaustion filter ───────────────────────────────────
            # A >5× volume spike at streak-end with a reversal wick means the
            # move is EXHAUSTED (sell climax / buy climax), not a breakout.
            # ZEC post-mortem: 10.5× vol candle had a lower wick → reversed 3%.
            if vol_surge > 5.0 and len(klines) >= 2:
                last_k  = klines[-2]   # last fully-closed candle
                k_hi    = float(last_k[2])
                k_lo    = float(last_k[3])
                k_cl    = float(last_k[4])
                k_range = k_hi - k_lo
                if k_range > 0:
                    if streak_dir == -1:   # SELL signal
                        lower_wick = (k_cl - k_lo) / k_range  # bounce off low
                        if lower_wick > 0.20:  # wick ≥ 20% of range → sell climax
                            reject_stats["exhaustion"] += 1
                            continue  # Exhaustion — skip
                    else:              # BUY signal
                        upper_wick = (k_hi - k_cl) / k_range  # rejection off high
                        if upper_wick > 0.20:  # wick ≥ 20% of range → buy climax
                            reject_stats["exhaustion"] += 1
                            continue  # Exhaustion — skip

            # ── 3-candle momentum ──────────────────────────────────────────
            mom_3c = abs(c[-1] - c[-4]) / c[-4] * 100 if c[-4] > 0 else 0.0
            if mom_3c < MIN_MOM_PCT:
                reject_stats["momentum"] += 1
                continue   # Momentum gate

            # ── Current candle impulse check (last closed candle) ─────────
            last_candle_pct = abs(c[-1] - c[-2]) / c[-2] * 100 if c[-2] > 0 else 0.0
            if last_candle_pct < MIN_LAST_CANDLE_PCT:
                reject_stats["impulse"] += 1
                continue   # Current impulse gate

            # ── Side from streak direction ─────────────────────────────────
            side = "buy" if streak_dir == 1 else "sell"

            # ── Direction filter (--side long/short) ──────────────────────
            if side_filter and side != side_filter:
                reject_stats["side_filter"] += 1
                continue

            # ── Leverage available for this side ──────────────────────────
            levs = info.leverage_buy if side == "buy" else info.leverage_sell
            if not levs:
                reject_stats["leverage"] += 1
                continue
            max_lev = max(levs)
            if max_lev < MIN_LEVERAGE:
                reject_stats["leverage"] += 1
                continue

            # ── Position size ──────────────────────────────────────────────
            split_slot = (side == "buy" and self.active_short) or (side == "sell" and self.active_long)
            plan = self._plan_dynamic_margin_position(
                info, max_lev, split_slot=split_slot, snapshot=capital_snapshot
            )
            if plan is None or not plan.approved:
                reject_stats["notional"] += 1
                continue
            MISSION_PROFIT_MIN = plan.profit_target_usd
            vol_qty = plan.volume
            trade_val = plan.notional

            # ── Check achievability: can it move enough in 1 minute? ───────
            # Use 1-min ATR (average of high-low range of last 5 candles)
            atr_1m_pct = (
                sum(abs(float(k[2]) - float(k[3])) / float(k[4]) * 100
                    for k in klines[-6:-1]) / 5
            ) if len(klines) >= 6 else 0.5
            round_trip_fee, _, _ = self._estimate_round_trip_fee(
                trade_val, symbol=info.pair
            )
            required_pct, _, _ = self._estimate_required_move_pct(
                trade_val, MISSION_PROFIT_MIN, symbol=info.pair
            )
            # ATR gate: hard reject only if 1m ATR is basically zero (ultra-frozen market)
            # During momentum surges, price can move 5-10× normal ATR in a single minute
            if atr_1m_pct < 0.02:   # Completely frozen — skip
                reject_stats["atr_frozen"] += 1
                continue

            # ── Mission score ──────────────────────────────────────────────
            streak_score  = min(streak_count / 5, 1.0)        # 0-1
            surge_score   = min((vol_surge - 1) / 2, 1.0)     # 0-1
            mom_score     = min(mom_3c / 2.0, 1.0)            # 0-1
            lev_score     = min(max_lev / 10.0, 1.0)          # 0-1
            spread_score  = max(0, 1.0 - info.spread_pct / MAX_SPREAD_PCT)
            atr_ease      = max(0, 1.0 - required_pct / atr_1m_pct) if atr_1m_pct else 0
            signal_edge   = (mom_3c / required_pct) if required_pct > 0 else 0.0
            est_minutes_to_target = (
                required_pct / max(last_candle_pct, 0.001)
            )
            aux = self._score_aux_scanners(
                symbol=info.pair,
                side=side,
                prices=c,
                volumes=v,
                current_price=info.last_price,
                momentum_pct=mom_3c,
            )
            projection = self._build_prime_projection(info.binance_symbol, side)
            if projection["side"] != side:
                reject_stats["projection_side"] += 1
                continue
            if projection["confidence"] < MIN_PROJ_CONF:
                reject_stats["projection_conf"] += 1
                continue
            if projection["live_match"] < MIN_PROJ_LIVE:
                reject_stats["projection_live"] += 1
                continue
            alignment = self._collect_alignment_metrics(info.pair, side, mom_3c)
            if alignment["score"] < MIN_ALIGNMENT_SCORE:
                reject_stats["alignment"] += 1
                continue
            harmonic = self._score_harmonic_margin_scanner(
                symbol=info.pair,
                side=side,
                current_price=info.last_price,
                momentum_pct=mom_3c,
                required_pct=required_pct,
                leverage=max_lev,
            )
            quantum = self._score_quantum_mirror_scanner(
                symbol=info.pair,
                side=side,
                current_price=info.last_price,
                momentum_pct=mom_3c,
                spread_pct=info.spread_pct,
            )
            timeline = self._score_timeline_oracle(
                symbol=info.pair,
                side=side,
                current_price=info.last_price,
                volume=float(sum(v[-6:])) if v else 0.0,
                change_pct=float(mom_3c),
            )
            fusion = self._score_harmonic_fusion(symbol=info.pair, side=side)
            whale = self._score_whale_orderbook(
                symbol=info.binance_symbol or info.pair,
                side=side,
                current_price=info.last_price,
                spread_pct=info.spread_pct,
            )
            live_flow_bonus = 0.0
            if self.stream and self.stream.is_alive() and info.binance_symbol:
                sf = self.stream.get_flow_snapshot(info.binance_symbol)
                if side == "buy":
                    live_flow_bonus = max(0.0, (sf.get("buy_pct", 50.0) - 50.0) / 25.0)
                else:
                    live_flow_bonus = max(0.0, (sf.get("sell_pct", 50.0) - 50.0) / 25.0)
                live_flow_bonus += min(sf.get("trade_velocity", 0.0) / 20.0, 1.0)

            conviction_bonus = (
                self.learning_bridge.get_conviction_bonus(info.pair)
                if self.learning_bridge is not None else 0.0
            )

            macro_bonus = 0.0
            if self.macro is not None and macro_ctx:
                try:
                    macro_bonus = self.macro.get_entry_context(info.pair).get("macro_score", 0.0)
                except Exception:
                    macro_bonus = 0.0

            intel_bonus = 0.0
            intel_verdict = "UNTESTED"
            intel_confidence = 0.0
            try:
                intel = self.intel.pre_strike_research(
                    symbol=info.binance_symbol,
                    side=side,
                    required_move_pct=required_pct,
                    kraken_pair=info.pair,
                )
                intel_verdict = intel.get("verdict", "UNTESTED")
                intel_confidence = float(intel.get("confidence", 0.0) or 0.0)
                if intel_verdict == "GO":
                    intel_bonus = 2.0 + intel_confidence
                elif intel_verdict == "CAUTION":
                    intel_bonus = max(0.0, intel_confidence - 0.25)
                else:
                    intel_bonus = -3.0
            except Exception:
                intel_verdict = "ERROR"
                intel_bonus = -0.5

            mission_score = (
                streak_score * 2.5
                + surge_score * 2.0
                + mom_score * 2.0
                + atr_ease * 2.5
                + lev_score
                + spread_score
                + min(signal_edge, 3.0) * 1.5
                + max(0.0, 2.0 - est_minutes_to_target) * 1.5
                + live_flow_bonus
                + conviction_bonus
                + macro_bonus
                + intel_bonus
                + seer_bonus
                + aux["war_bonus"]
                + aux["sniper_bonus"]
                + aux["nexus_bonus"]
                + (1.5 if projection["side"] == side else -1.5)
                + projection["confidence"] * 2.0
                + projection["live_match"] * 2.0
                + max(-1.5, min(projection["edge"], 1.5))
                + alignment["score"]
                + harmonic["bonus"] * 1.5
                + quantum["bonus"] * 1.5
                + timeline["bonus"] * 1.25
                + fusion["bonus"] * 1.25
                + whale["bonus"] * 1.25
            )

            candidates.append({
                "info":         info,
                "side":         side,
                "vol":          vol_qty,
                "trade_val":    trade_val,
                "leverage":     max_lev,
                "profit_target_usd": MISSION_PROFIT_MIN,
                "streak":       streak_count,
                "vol_surge":    vol_surge,
                "mom_3c_pct":   mom_3c,
                "last_c_pct":   last_candle_pct,
                "atr_1m_pct":   atr_1m_pct,
                "required_pct": required_pct,
                "signal_edge":  signal_edge,
                "eta_min":      est_minutes_to_target,
                "live_flow":    live_flow_bonus,
                "conviction":   conviction_bonus,
                "macro":        macro_bonus,
                "intel":        intel_verdict,
                "intel_conf":   intel_confidence,
                "seer":         seer_verdict,
                "seer_conf":    seer_confidence,
                "war_prob":     aux["war_prob"],
                "war_pri":      aux["war_priority"],
                "sniper":       aux["sniper_action"],
                "sniper_conf":  aux["sniper_conf"],
                "nexus_prob":   aux["nexus_prob"],
                "nexus_edge":   aux["nexus_edge"],
                "proj_side":    projection["side"],
                "proj_conf":    projection["confidence"],
                "proj_edge":    projection["edge"],
                "proj_live":    projection["live_match"],
                "align":        alignment["score"],
                "harmonic_sig": harmonic["signal"],
                "harmonic_conf": harmonic["confidence"],
                "harmonic_coh": harmonic["coherence"],
                "quantum_branch": quantum["branch_score"],
                "quantum_coh": quantum["coherence"],
                "quantum_prob": quantum["beneficial_probability"],
                "timeline_action": timeline["action"],
                "timeline_conf": timeline["confidence"],
                "fusion_coh": fusion["global_coherence"],
                "fusion_phase": fusion["phase_alignment"],
                "whale_walls": whale["wall_count"],
                "whale_layer": whale["layering_score"],
                "whale_imb": whale["depth_imbalance"],
                "coh":          alignment["coherence"],
                "lyra_h":       alignment["lyra"],
                "lambda_h":     alignment["lambda"],
                "purity_h":     alignment["purity"],
                "earth_h":      alignment["earth"],
                "solar_h":      alignment["solar"],
                "score":        mission_score,
            })

        if not candidates:
            print(
                f"   Rejections: streak={reject_stats['streak']} surge={reject_stats['surge']} "
                f"momentum={reject_stats['momentum']} impulse={reject_stats['impulse']} "
                f"exhaustion={reject_stats['exhaustion']} leverage={reject_stats['leverage']} "
                f"atr={reject_stats['atr_frozen']} proj_side={reject_stats['projection_side']} "
                f"proj_conf={reject_stats['projection_conf']} proj_live={reject_stats['projection_live']} "
                f"align={reject_stats['alignment']} fetch={reject_stats['kline_fetch']}"
            )
            print(f"\n⏳ No targets qualifying right now. Continuous scanning every {SCAN_INTERVAL_SEC}s...")
            print(f"   Will hunt for up to {HUNT_TIMEOUT_SEC//60} minutes. Ctrl+C to abort.")
            hunt_start = time.time()
            while time.time() - hunt_start < HUNT_TIMEOUT_SEC:
                elapsed_hunt = int(time.time() - hunt_start)
                remaining_hunt = HUNT_TIMEOUT_SEC - elapsed_hunt
                print(f"   [{elapsed_hunt:>3}s] Rescanning... ({remaining_hunt}s remaining)", end="\r")
                time.sleep(SCAN_INTERVAL_SEC)
                # Skip update_prices_free() here — the kline scan below fetches
                # fresh data per-pair already. The bulk price call adds 30s delay.
                candidates = []
                for pair_name2, info2 in scan_pairs:
                    bsym2 = info2.binance_symbol
                    try:
                        url2 = (f"{BINANCE_KLINES_URL}?symbol={bsym2}"
                                f"&interval=1m&limit=10")
                        req2 = urllib.request.Request(url2, headers={"User-Agent": "MissionHunt/1.0"})
                        with urllib.request.urlopen(req2, timeout=5) as r2:
                            klines2 = json.loads(r2.read().decode())
                    except Exception:
                        continue
                    if len(klines2) < 6:
                        continue
                    c2 = [float(k[4]) for k in klines2[-7:]]
                    v2 = [float(k[5]) for k in klines2[-7:]]
                    dirs2 = [1 if c2[i]>c2[i-1] else (-1 if c2[i]<c2[i-1] else 0)
                             for i in range(1, len(c2))]
                    sd2 = dirs2[-1]
                    sc2 = 0
                    for d2 in reversed(dirs2):
                        if d2 == sd2: sc2 += 1
                        else: break
                    if sc2 < MIN_STREAK or sd2 == 0:
                        continue
                    lv2 = v2[-1]; av2 = sum(v2[-6:-1])/5 if len(v2)>=6 else lv2
                    vs2 = lv2/av2 if av2>0 else 1.0
                    if vs2 < MIN_VOLUME_SURGE:
                        continue
                    # Climax exhaustion filter (pass 2)
                    if vs2 > 5.0 and len(klines2) >= 2:
                        lk2  = klines2[-2]
                        lkhi = float(lk2[2]); lklo = float(lk2[3]); lkcl = float(lk2[4])
                        lkrng = lkhi - lklo
                        if lkrng > 0:
                            if sd2 == -1 and (lkcl - lklo) / lkrng > 0.20:
                                continue  # sell climax
                            elif sd2 == 1 and (lkhi - lkcl) / lkrng > 0.20:
                                continue  # buy climax
                    m2 = abs(c2[-1]-c2[-4])/c2[-4]*100 if c2[-4]>0 else 0
                    if m2 < MIN_MOM_PCT:
                        continue
                    m2_last = abs(c2[-1]-c2[-2])/c2[-2]*100 if c2[-2]>0 else 0
                    if m2_last < MIN_LAST_CANDLE_PCT:
                        continue
                    side2 = "buy" if sd2==1 else "sell"
                    if side_filter and side2 != side_filter:
                        continue
                    levs2 = info2.leverage_buy if side2=="buy" else info2.leverage_sell
                    if not levs2 or max(levs2)<MIN_LEVERAGE:
                        continue
                    lev2 = max(levs2)
                    split2 = (side2 == "buy" and self.active_short) or (side2 == "sell" and self.active_long)
                    plan2 = self._plan_dynamic_margin_position(
                        info2, lev2, split_slot=split2, snapshot=capital_snapshot
                    )
                    if plan2 is None or not plan2.approved:
                        continue
                    vq2 = plan2.volume
                    tv2 = plan2.notional
                    MISSION_PROFIT_MIN = plan2.profit_target_usd
                    atr2 = (sum(abs(float(k[2])-float(k[3]))/float(k[4])*100
                                for k in klines2[-6:-1])/5) if len(klines2)>=6 else 0.5
                    if atr2 < 0.02:
                        continue
                    rt2, _, _ = self._estimate_round_trip_fee(tv2, symbol=info2.pair)
                    rp2, _, _ = self._estimate_required_move_pct(
                        tv2, MISSION_PROFIT_MIN, symbol=info2.pair
                    )
                    ss2 = min(sc2/5,1.0); sg2 = min((vs2-1)/2,1.0)
                    ms2 = min(m2/2,1.0); ls2 = min(lev2/10,1.0)
                    sprd2 = max(0,1.0-info2.spread_pct/MAX_SPREAD_PCT)
                    ae2 = max(0,1.0-rp2/atr2) if atr2>0 else 0
                    edge2 = (m2 / rp2) if rp2 > 0 else 0.0
                    eta2 = rp2 / max(m2_last, 0.001)
                    aux2 = self._score_aux_scanners(
                        symbol=info2.pair,
                        side=side2,
                        prices=c2,
                        volumes=v2,
                        current_price=info2.last_price,
                        momentum_pct=m2,
                    )
                    projection2 = self._build_prime_projection(info2.binance_symbol, side2)
                    if projection2["side"] != side2:
                        continue
                    if projection2["confidence"] < MIN_PROJ_CONF:
                        continue
                    if projection2["live_match"] < MIN_PROJ_LIVE:
                        continue
                    alignment2 = self._collect_alignment_metrics(info2.pair, side2, m2)
                    if alignment2["score"] < MIN_ALIGNMENT_SCORE:
                        continue
                    live_flow2 = 0.0
                    if self.stream and self.stream.is_alive() and info2.binance_symbol:
                        sf2 = self.stream.get_flow_snapshot(info2.binance_symbol)
                        if side2 == "buy":
                            live_flow2 = max(0.0, (sf2.get("buy_pct", 50.0) - 50.0) / 25.0)
                        else:
                            live_flow2 = max(0.0, (sf2.get("sell_pct", 50.0) - 50.0) / 25.0)
                        live_flow2 += min(sf2.get("trade_velocity", 0.0) / 20.0, 1.0)

                    conviction2 = (
                        self.learning_bridge.get_conviction_bonus(info2.pair)
                        if self.learning_bridge is not None else 0.0
                    )

                    macro2 = 0.0
                    if self.macro is not None and macro_ctx:
                        try:
                            macro2 = self.macro.get_entry_context(info2.pair).get("macro_score", 0.0)
                        except Exception:
                            macro2 = 0.0

                    intel_bonus2 = 0.0
                    intel_verdict2 = "UNTESTED"
                    intel_conf2 = 0.0
                    try:
                        intel2 = self.intel.pre_strike_research(
                            symbol=info2.binance_symbol,
                            side=side2,
                            required_move_pct=rp2,
                            kraken_pair=info2.pair,
                        )
                        intel_verdict2 = intel2.get("verdict", "UNTESTED")
                        intel_conf2 = float(intel2.get("confidence", 0.0) or 0.0)
                        if intel_verdict2 == "GO":
                            intel_bonus2 = 2.0 + intel_conf2
                        elif intel_verdict2 == "CAUTION":
                            intel_bonus2 = max(0.0, intel_conf2 - 0.25)
                        else:
                            intel_bonus2 = -3.0
                    except Exception:
                        intel_verdict2 = "ERROR"
                        intel_bonus2 = -0.5

                    sc_total = (
                        ss2*2.5 + sg2*2.0 + ms2*2.0 + ae2*2.5 + ls2 + sprd2
                        + min(edge2, 3.0)*1.5
                        + max(0.0, 2.0 - eta2)*1.5
                        + live_flow2 + conviction2 + macro2 + intel_bonus2
                        + seer_bonus + aux2["war_bonus"] + aux2["sniper_bonus"] + aux2["nexus_bonus"]
                        + (1.5 if projection2["side"] == side2 else -1.5)
                        + projection2["confidence"] * 2.0
                        + projection2["live_match"] * 2.0
                        + max(-1.5, min(projection2["edge"], 1.5))
                        + alignment2["score"]
                    )
                    candidates.append({
                        "info": info2, "side": side2, "vol": vq2,
                        "trade_val": tv2, "leverage": lev2,
                        "profit_target_usd": MISSION_PROFIT_MIN,
                        "streak": sc2, "vol_surge": vs2, "mom_3c_pct": m2,
                        "last_c_pct": m2_last,
                        "atr_1m_pct": atr2, "required_pct": rp2,
                        "signal_edge": edge2, "eta_min": eta2,
                        "live_flow": live_flow2, "conviction": conviction2,
                        "macro": macro2, "intel": intel_verdict2,
                        "intel_conf": intel_conf2, "seer": seer_verdict,
                        "seer_conf": seer_confidence, "war_prob": aux2["war_prob"],
                        "war_pri": aux2["war_priority"], "sniper": aux2["sniper_action"],
                        "sniper_conf": aux2["sniper_conf"], "nexus_prob": aux2["nexus_prob"],
                        "nexus_edge": aux2["nexus_edge"], "proj_side": projection2["side"],
                        "proj_conf": projection2["confidence"], "proj_edge": projection2["edge"],
                        "proj_live": projection2["live_match"], "align": alignment2["score"],
                        "coh": alignment2["coherence"], "lyra_h": alignment2["lyra"],
                        "lambda_h": alignment2["lambda"], "purity_h": alignment2["purity"],
                        "earth_h": alignment2["earth"], "solar_h": alignment2["solar"], "score": sc_total
                    })
                if candidates:
                    print()
                    print(f"\n🚨 SIGNAL LOCKED after {elapsed_hunt}s scanning!")
                    break

        if not candidates:
            print()
            print(f"\n⏸️  No qualifying signal this patrol ({HUNT_TIMEOUT_SEC//60}m window). Resuming hunt...")
            return {'traded': False, 'reason': 'no_signal', 'net_pnl': 0.0,
                    'pair': None, 'side': None}

        # Sort by mission score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)

        print(f"\n🏆 TOP MISSION CANDIDATES (goal-aligned after-fee signals):")
        print(f"{'#':<3} {'PAIR':<12} {'SIDE':<5} {'LEV':>4} {'REQ%':>7}"
              f" {'EDGE':>6} {'ETAm':>6} {'PRJ':>5} {'LIV':>5} {'ALN':>5} {'SCORE':>6}")
        print("-" * 86)
        for i, c_ in enumerate(candidates[:5]):
            print(
                f"{i+1:<3} {c_['info'].pair:<12} {c_['side'].upper():<5}"
                f" {c_['leverage']:>3}×"
                f" {c_['required_pct']:>6.3f}%"
                f" {c_['signal_edge']:>5.2f}"
                f" {c_['eta_min']:>5.2f}"
                f" {c_['proj_conf']:>5.2f}"
                f" {c_['proj_live']:>5.2f}"
                f" {c_['align']:>5.2f}"
                f" {c_['score']:>6.2f}"
            )

        best = candidates[0]
        info_b   = best["info"]
        side_b   = best["side"]
        vol_b    = best["vol"]
        lev_b    = best["leverage"]
        tv_b     = best["trade_val"]
        MISSION_PROFIT_MIN = float(best.get("profit_target_usd", MISSION_PROFIT_MIN) or MISSION_PROFIT_MIN)
        self._feed_unified_decision_engine(
            info_b.pair,
            side_b,
            score=min(max(float(best["score"]) / 10.0, 0.0), 1.0),
            metadata={
                "trade_value": float(tv_b),
                "leverage": int(lev_b),
                "required_move_pct": float(best["required_pct"]),
                "signal_edge": float(best["signal_edge"]),
                "eta_min": float(best["eta_min"]),
                "projection_confidence": float(best["proj_conf"]),
                "projection_live_match": float(best["proj_live"]),
                "alignment_score": float(best["align"]),
            },
        )

        print(f"\n🎯 MISSION TARGET: {info_b.pair} {side_b.upper()} {lev_b}×")
        print(f"   Streak          : {best['streak']} consecutive 1m candles")
        print(f"   Volume surge    : {best['vol_surge']:.1f}× normal")
        print(f"   3-candle mom    : {best['mom_3c_pct']:+.3f}%")
        print(f"   Last candle     : {best['last_c_pct']:+.3f}%  (current impulse)")
        print(f"   1m ATR          : {best['atr_1m_pct']:.3f}%  |  Required move: {best['required_pct']:.3f}%")
        print(f"   Signal edge     : {best['signal_edge']:.2f}x  |  ETA to target: {best['eta_min']:.2f} min")
        print(f"   Intel verdict   : {best['intel']}  |  Confidence: {best['intel_conf']:.2f}")
        print(f"   Seer            : {best['seer']}  |  Confidence: {best['seer_conf']:.2f}")
        print(f"   War / Sniper    : {best['war_prob']:.2f} / {best['sniper']} {best['sniper_conf']:.2f}")
        print(f"   Nexus           : prob {best['nexus_prob']:.2f}  |  edge {best['nexus_edge']:+.2f}")
        print(f"   Projection      : {best['proj_side'].upper()}  |  conf {best['proj_conf']:.2f}  |  live match {best['proj_live']:.2f}")
        print(f"   Alignment       : coh {best['coh']:.2f} | lyra {best['lyra_h']:.2f} | lambda {best['lambda_h']:.2f} | purity {best['purity_h']:.2f}")
        print(f"   Planet / Solar  : earth {best['earth_h']:.2f} | solar {best['solar_h']:.2f} | align {best['align']:+.2f}")
        print(f"   Live flow bonus : {best['live_flow']:+.2f}  |  Macro: {best['macro']:+.2f}  |  Learning: {best['conviction']:+.2f}")
        print(f"   Notional        : ${tv_b:.2f}  |  Volume: {vol_b}")

        # ── Step 3b: Orchestrator gate before committing capital ───────────
        if self.orchestrator is not None:
            _approved, _reason, _sizing = self.orchestrator.gate_pre_trade(
                info_b.pair, side_b, tv_b
            )
            if not _approved:
                print(f"\n  [Orchestrator] Trade HELD — {_reason}")
                return {
                    'traded': False,
                    'reason': f'orchestrator_gate: {_reason}',
                    'net_pnl': 0.0,
                    'pair': info_b.pair,
                    'side': side_b,
                }

        # ── Step 4: Open the position ──────────────────────────────────────
        print(f"\n⚡ Opening {side_b.upper()} position...")
        mission_cognition_context = self._build_candidate_cognition_context(
            info=info_b,
            side=side_b,
            required_move_pct=float(best.get("required_pct", 0.0) or 0.0),
            eta_minutes=float(best.get("eta_min", 0.0) or 0.0),
            goal_score=float(best.get("signal_edge", 0.0) or 0.0),
            route_to_profit=float(best.get("signal_edge", 0.0) or 0.0),
            profit_target_usd=MISSION_PROFIT_MIN,
            projection={
                "side": best.get("proj_side", side_b),
                "confidence": float(best.get("proj_conf", 0.0) or 0.0),
                "live_match": float(best.get("proj_live", 0.0) or 0.0),
                "edge": float(best.get("proj_edge", 0.0) or 0.0),
            },
            timeline={"action": side_b, "confidence": float(best.get("proj_conf", 0.0) or 0.0)},
            alignment={"score": float(best.get("align", 0.0) or 0.0)},
        )
        trade = self.open_position(
            info_b,
            side_b,
            vol_b,
            lev_b,
            profit_target_usd=MISSION_PROFIT_MIN,
            cognition_context=mission_cognition_context,
        )
        if not trade:
            print("❌ MISSION FAILED: Order rejected by Kraken. Aborting.")
            return {'traded': False, 'reason': 'order_rejected', 'net_pnl': 0.0,
                    'pair': info_b.pair, 'side': side_b}

        print(f"✅ POSITION OPEN: {trade.pair} {trade.side.upper()}"
              f" @ ${trade.entry_price:,.4f}  |  Breakeven: ${trade.breakeven_price:,.4f}")

        # ── Step 5: Monitor until profit — NEVER close at a loss ────────────
        # SINGLE EXIT RULE: net_pnl > 0 only. Entry gates guarantee recovery.
        # We hold as long as needed. No stop loss. No time deadline.
        mission_start  = time.time()
        poll           = 0
        max_net_pnl    = -9999.0
        closed_result  = None

        print(f"\n⏱️  MONITORING POSITION — HOLD UNTIL REALIZED PROFIT")
        print(f"   ONLY exit: net_pnl >= ${MISSION_PROFIT_MIN:.2f} after fees  |  No stop loss  |  No time limit")
        print("-" * 55)

        while True:  # Hold until profitable — no deadline
            poll += 1
            elapsed = time.time() - mission_start

            # Orchestrator sync every cycle (feeds Seer/Lyra/ThoughtBus)
            if self.orchestrator is not None:
                self.orchestrator.cycle_sync()

            # Get live price
            current = 0.0
            price_source = "REST"
            if self.stream and self.stream.is_alive():
                current = self.stream.get_executable_price(trade.binance_symbol, side=trade.side)
                if current > 0:
                    price_source = "LIVE"
            if current <= 0:
                current = self.market.get_single_price(trade.binance_symbol)
            if current <= 0:
                time.sleep(MONITOR_POLL_SEC)
                continue

            # Calculate net P&L
            if trade.side == "buy":
                gross = (current - trade.entry_price) * trade.volume
            else:
                gross = (trade.entry_price - current) * trade.volume

            _, close_fee_rate = self._get_open_close_fee_rates(trade.pair)
            exit_fee_est = current * trade.volume * close_fee_rate
            net_pnl = gross - trade.entry_fee - exit_fee_est
            mission_cognition = self._verify_trade_cognition(
                trade,
                current_price=current,
                validated_net_pnl=net_pnl,
            )
            max_net_pnl = max(max_net_pnl, net_pnl)
            status_icon = "UP" if net_pnl > 0 else "WAIT"
            status_line = (
                f"\r[{status_icon}] t={elapsed:6.0f}s src={price_source:<4} "
                f"pair={trade.pair:<10} side={trade.side.upper():<4} lev={trade.leverage}x "
                f"entry=${trade.entry_price:,.4f} now=${current:,.4f} "
                f"net=${net_pnl:+.4f} peak=${max_net_pnl:+.4f} "
                f"target=${MISSION_PROFIT_MIN:.2f}"
            )
            print(status_line.ljust(180), end="", flush=True)

            status_icon = "📈" if net_pnl > 0 else "⏳"
            print(f"  {status_icon} {elapsed:6.0f}s | ${trade.entry_price:,.4f}→${current:,.4f}"
                  f" | Net: ${net_pnl:+.4f}  peak=${max_net_pnl:+.4f}",
                  end="\r", flush=True)

            # ONLY exit condition: realized net profit reaches the live target
            if net_pnl >= MISSION_PROFIT_MIN:
                print()
                print(f"\n💰 PROFIT TARGET HIT! Net: ${net_pnl:+.4f} (≥ ${MISSION_PROFIT_MIN:.2f} after fees)  Closing...")
                closed_result = self.close_position(
                    reason=f"MISSION_PROFIT (${net_pnl:+.4f})",
                    trade=trade
                )
                break

            time.sleep(MONITOR_POLL_SEC)

        # ── Mission report ─────────────────────────────────────────────────
        print("\n" + "=" * 70)
        print("  🏁  MISSION COMPLETE")
        if closed_result:
            final_pnl = closed_result.get("net_pnl", 0.0)
            hold_s    = closed_result.get("hold_seconds", 0.0)
            reason    = closed_result.get("reason", "?")
            print(f"  Pair     : {trade.pair}")
            print(f"  Side     : {trade.side.upper()}  {lev_b}× leverage")
            print(f"  Entry    : ${trade.entry_price:,.4f}")
            print(f"  Exit     : ${closed_result.get('exit_price', 0):,.4f}")
            print(f"  Hold     : {hold_s:.1f}s")
            print(f"  Net P&L  : ${final_pnl:+.4f}")
            print(f"  Reason   : {reason}")
            if final_pnl > 0:
                print(f"  Result   : ✅  PROFITABLE MISSION")
            else:
                print(f"  Result   : ⚠️  MISSION CLOSED (market did not cooperate)")
        else:
            print("  Position close failed — check Kraken dashboard manually!")
        print("=" * 70)
        self._save_results()

        final_pnl = closed_result.get("net_pnl", 0.0) if closed_result else 0.0
        return {
            'traded':   True,
            'reason':   closed_result.get('reason', '?') if closed_result else 'close_failed',
            'net_pnl':  final_pnl,
            'pair':     trade.pair,
            'side':     trade.side,
        }

    # ----------------------------------------------------------
    #  PRIDE HUNT — Infinite patrol loop (lion never stops hunting)
    # ----------------------------------------------------------
    def pride_hunt(self, side_filter: str = None) -> None:
        """
        PRIDE MODE — Continuous mission hunt loop.
        The lion does not eat once and sleep. It patrols, strikes, feeds,
        rests briefly, then resumes the patrol. Runs until Ctrl+C.

        After each hunt cycle (trade or no-trade), rest briefly then scan again.
        Tracks all kills (profits) and displays pride stats.
        """
        REST_AFTER_TRADE_SEC   = 30   # Digest after a kill — brief rest
        REST_AFTER_NO_SIGNAL   = 15   # Resume quickly when no signal found
        REST_AFTER_REJECTION   = 20   # Brief pause after rejected order

        direction_tag = ("SHORT ONLY ↓" if side_filter == "sell"
                         else "LONG ONLY ↑" if side_filter == "buy"
                         else "LONG + SHORT")
        mode_tag = "DRY RUN" if self.dry_run else "LIVE"

        print("\n" + "▓" * 70)
        print("  🦁  PRIDE MODE — THE HUNT NEVER ENDS")
        print(f"  Mode: {mode_tag}  |  Direction: {direction_tag}")
        print("  The pride patrols the Serengeti. The meal comes to those who wait.")
        print("  Ctrl+C to end the patrol.")
        print("▓" * 70 + "\n")

        patrol     = 0
        kills      = 0
        total_pnl  = 0.0
        no_signal_streak = 0

        try:
            while True:
                patrol += 1
                print(f"\n{'─'*70}")
                print(f"  🐾  PATROL #{patrol}  |  Kills: {kills}  |  "
                      f"Cumulative P&L: ${total_pnl:+.4f}")
                print(f"{'─'*70}")

                result = self.mission_hunt(side_filter=side_filter)

                if result is None:
                    result = {'traded': False, 'reason': 'unknown', 'net_pnl': 0.0,
                              'pair': None, 'side': None}

                traded  = result.get('traded', False)
                net_pnl = result.get('net_pnl', 0.0)
                reason  = result.get('reason', '?')
                pair    = result.get('pair')

                if traded:
                    total_pnl += net_pnl
                    if net_pnl > 0:
                        kills += 1
                        print(f"\n🥩 KILL #{kills}!  {pair}  P&L: ${net_pnl:+.4f}")
                        print(f"   Total kills: {kills}  |  Total P&L: ${total_pnl:+.4f}")
                    else:
                        print(f"\n⚔️  Traded but market moved against us: ${net_pnl:+.4f}")
                    no_signal_streak = 0
                    rest = REST_AFTER_TRADE_SEC

                elif reason == 'insufficient_margin':
                    print("\n❌ Insufficient margin. Waiting 60s before re-check...")
                    rest = 60

                elif reason == 'order_rejected':
                    rest = REST_AFTER_REJECTION
                    no_signal_streak = 0

                else:  # no_signal
                    no_signal_streak += 1
                    rest = REST_AFTER_NO_SIGNAL

                print(f"\n💤  Resting {rest}s before next patrol...  "
                      f"(Press Ctrl+C to end hunt)")
                time.sleep(rest)

        except KeyboardInterrupt:
            print("\n\n" + "▓" * 70)
            print("  🦁  PRIDE PATROL ENDED  — The pride rests.")
            print(f"  Patrols   : {patrol}")
            print(f"  Kills     : {kills}")
            print(f"  Total P&L : ${total_pnl:+.4f}")
            print("▓" * 70 + "\n")

    # ----------------------------------------------------------
    #  MAIN LOOP - THE ARMY CYCLE (DUAL POSITIONS + SHADOW VALIDATION)
    # ----------------------------------------------------------
    def run(self, scan_only: bool = False):
        """
        Main loop — Shadow Validation + Dual Positions.
        The cycle:
        1. Monitor active positions (LONG and/or SHORT)
        2. Update shadows with live prices — expire stale, note validated
        3. Promote validated shadows to real positions
        4. If slots empty → find candidates → create shadows
        5. Repeat forever. NO STOP LOSS.
        """
        mode = "DRY RUN" if self.dry_run else "LIVE"

        print("=" * 70)
        print(f"  KRAKEN MARGIN ARMY TRADER — SHADOW VALIDATION + DUAL POSITIONS")
        print(f"  Mode: {mode}")
        print(f"  Strategy: 1 LONG + 1 SHORT | SHADOW VALIDATE FIRST | NO STOP LOSS")
        print(f"  Intel: Pre-strike research + Live danger detection")
        print(f"  Stream: {'Binance WebSocket (sub-second)' if HAS_WEBSOCKET else 'REST polling (2s)'}")
        print(f"  Shadow: Simulated plays validate predictions before real capital")
        print(f"  Execution: Kraken API (open/close only)")
        print(f"  Profit target: dynamic per position (capped at ${PROFIT_TARGET_USD:.2f})")
        print(f"  Policy: NO STOP LOSS — only close on PROFIT or liquidation risk")
        print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # Step 1: Discover pairs (ONE Kraken batch)
        self.discover_margin_universe()

        # Step 2: Prices from FREE API
        self.update_prices_free()

        capital = self._get_capital_snapshot()
        print(
            f"  Capital: equity=${capital['equity']:.2f} | free=${capital['free_margin']:.2f} | "
            f"used=${capital['margin_used']:.2f} | budget=${capital['budget']:.2f} | "
            f"target=${capital['profit_target_usd']:.2f} ({capital['target_pct_equity']:.3f}% eq)"
        )
        print("=" * 70)

        # Step 3: Show universe
        self.print_universe()

        if scan_only:
            print("Scan-only mode. Exiting.")
            return

        # Step 4: The Army cycle
        cycle = 0
        last_full_refresh = 0
        last_shadow_scan = 0
        SHADOW_SCAN_INTERVAL = 15  # Seconds between shadow creation scans

        try:
            while True:
                cycle += 1
                now = time.time()

                # ============================
                # PHASE 0: ORCHESTRATOR CYCLE SYNC
                # Update all Queen's systems: multiverse shadows, learning
                # bridge → Seer/Lyra/ThoughtBus, quick gate refresh.
                # Fast path — no heavy API calls on every iteration.
                # ============================
                if self.orchestrator is not None:
                    self.orchestrator.cycle_sync()

                # ETA reporting (every 5 mins)
                self._report_margin_eta()
                self._self_heal_stream_if_stale()

                # ============================
                # PHASE 1: Monitor active positions
                # ============================
                for label, trade in [("LONG", self.active_long), ("SHORT", self.active_short)]:
                    if trade:
                        result = self.monitor_position(trade=trade)
                        if result:
                            pnl = result.get("net_pnl", 0)
                            logger.info(
                                f"TRADE #{self.total_trades}: {result['pair']} {label} "
                                f"${pnl:+.2f} | Session: ${self.total_profit:+.2f}"
                            )
                            self._save_results()

                # ============================
                # PHASE 2: Update shadows
                # ============================
                if self.shadow_trades:
                    self.update_shadows()

                # ============================
                # PHASE 3: Promote validated shadows
                # ============================
                promoted_this_cycle = False
                for shadow in list(self.shadow_trades):
                    if not shadow.validated:
                        continue
                    # Must have been validated for at least SHADOW_MIN_VALIDATE seconds
                    if shadow.validation_time > 0 and (now - shadow.validation_time) < self.SHADOW_MIN_VALIDATE:
                        continue
                    # Check if the correct slot is free
                    if shadow.side == "buy" and self.active_long:
                        continue
                    if shadow.side == "sell" and self.active_short:
                        continue

                    # ── ORCHESTRATOR GATE: all Queen's systems must agree ──
                    # Quadrumvirate (Seer + Lyra + Queen + King) votes before
                    # real capital is deployed on this validated shadow.
                    if self.orchestrator is not None:
                        _orch_approved, _orch_reason, _orch_sizing = (
                            self.orchestrator.gate_pre_trade(
                                shadow.pair, shadow.side, shadow.trade_val
                            )
                        )
                        if not _orch_approved:
                            logger.info(
                                f"[Orchestrator] Shadow {shadow.pair} {shadow.side.upper()} "
                                f"HELD — {_orch_reason} (will retry next cycle)"
                            )
                            continue   # don't promote — leave shadow, retry next cycle

                    trade = self.promote_shadow(shadow)
                    if trade:
                        promoted_this_cycle = True
                        break  # Only promote one per cycle

                # ============================
                # PHASE 4: Find candidates → create shadows (if slots empty)
                # ============================
                has_open = self.active_long or self.active_short
                need_long = self.active_long is None
                need_short = self.active_short is None

                if (need_long or need_short) and not promoted_this_cycle:
                    if now - last_full_refresh > 30:
                        self.update_prices_free()
                        last_full_refresh = now

                    if now - last_shadow_scan > SHADOW_SCAN_INTERVAL:
                        last_shadow_scan = now

                        # Get candidates
                        target = self.find_best_target()
                        if target:
                            info, side, vol, trade_val, lev = target

                            # Create shadow for this candidate's side
                            if (side == "buy" and need_long) or (side == "sell" and need_short):
                                self.create_shadow(info, side, vol, trade_val, lev)

                        else:
                            if not has_open and not self.shadow_trades:
                                logger.info("No targets met criteria. Scanning again soon...")

                # ============================
                # Sleep & periodic tasks
                # ============================
                if self.active_long or self.active_short:
                    time.sleep(MONITOR_INTERVAL)
                elif self.shadow_trades:
                    time.sleep(1)  # Fast updates for shadows
                else:
                    time.sleep(5)  # Idle scanning

                if cycle % 30 == 0:
                    self.print_status()
                if cycle % 60 == 0:
                    self._save_results()

        except KeyboardInterrupt:
            print()
            print("Army trader stopped by user.")
            self.print_status()
            self._save_state()
            self._save_results()

    # ----------------------------------------------------------
    #  TICK — one autonomous trading cycle (no internal loop)
    #  Called by the Orca Kill Cycle's run_autonomous() each
    #  iteration so both loops stay in sync.
    # ----------------------------------------------------------
    def tick(self) -> list:
        """
        Execute ONE complete autonomous trading cycle and return.

        This is the headless version of run(): same logic, no while-loop,
        no sleep. The Orca calls this from its own infinite loop so the
        full Queen's system stack (Orchestrator → Seer → Lyra → Queen)
        gates every decision without a second blocking loop.

        Returns
        -------
        list of dict  — trades closed this tick (may be empty)
        """
        now = time.time()
        closed_this_tick: list = []
        self._self_heal_stream_if_stale()

        # ── PHASE 0: Orchestrator cycle sync ─────────────────────────────
        # Updates multiverse shadows, syncs learning bridge → Seer/Lyra/ThoughtBus,
        # refreshes quick gate flags.  No heavy API calls.
        if self.orchestrator is not None:
            try:
                self.orchestrator.cycle_sync()
            except Exception:
                pass

        # ── PHASE 1: Monitor active positions ─────────────────────────────
        for label, trade in [("LONG", self.active_long), ("SHORT", self.active_short)]:
            if trade:
                result = self.monitor_position(trade=trade)
                if result:
                    pnl = result.get("net_pnl", 0)
                    logger.info(
                        f"[tick] TRADE #{self.total_trades}: "
                        f"{result['pair']} {label} ${pnl:+.2f} | "
                        f"Session: ${self.total_profit:+.2f}"
                    )
                    closed_this_tick.append(result)
                    self._save_results()

        # ── PHASE 2: Update validation shadows ────────────────────────────
        if self.shadow_trades:
            self.update_shadows()

        # ── PHASE 3: Promote validated shadows (Orchestrator gated) ───────
        for shadow in list(self.shadow_trades):
            if not shadow.validated:
                continue
            if (shadow.validation_time > 0 and
                    (now - shadow.validation_time) < self.SHADOW_MIN_VALIDATE):
                continue
            if shadow.side == "buy" and self.active_long:
                continue
            if shadow.side == "sell" and self.active_short:
                continue

            # Dynamic door: Queen controls sizing, only cross-system conflict blocks
            if self.orchestrator is not None:
                try:
                    _ok, _reason, sizing_mod = self.orchestrator.gate_pre_trade(
                        shadow.pair, shadow.side, shadow.trade_val
                    )
                    if not _ok:
                        # Only cross-system conflict returns False
                        logger.info(
                            f"[tick] Shadow {shadow.pair} BLOCKED by Orchestrator: {_reason}"
                        )
                        continue
                    # Apply Queen's sizing modifier to trade value
                    sizing_mod = max(0.10, min(2.0, float(sizing_mod or 1.0)))
                    if sizing_mod != 1.0:
                        original_val = shadow.trade_val
                        shadow.trade_val = shadow.trade_val * sizing_mod
                        if shadow.entry_price > 0:
                            shadow.volume = shadow.trade_val / shadow.entry_price
                        logger.info(
                            f"[tick] Shadow {shadow.pair} Queen sizing={sizing_mod:.2f}x "
                            f"(${original_val:.2f} -> ${shadow.trade_val:.2f})"
                        )
                except Exception:
                    pass

            trade = self.promote_shadow(shadow)
            if trade:
                break   # one promotion per tick

        # ── PHASE 4: Find candidates → create new shadows ─────────────────
        need_long  = self.active_long  is None
        need_short = self.active_short is None

        if need_long or need_short:
            # Price refresh every 30 s
            if now - getattr(self, '_tick_last_price_refresh', 0) > 30:
                self.update_prices_free()
                self._tick_last_price_refresh = now

            # Shadow scan every 15 s
            if now - getattr(self, '_tick_last_shadow_scan', 0) > 15:
                self._tick_last_shadow_scan = now
                target = self.find_best_target()
                if target:
                    info, side, vol, trade_val, lev = target
                    if (side == "buy" and need_long) or (side == "sell" and need_short):
                        self.create_shadow(info, side, vol, trade_val, lev)
        return closed_this_tick

    def monitor_positions(self) -> list:
        """Compatibility wrapper — monitors both active positions, returns closed list."""
        return self.tick()

    def refresh_prices(self) -> None:
        """Compatibility wrapper — refresh all margin pair prices."""
        try:
            self.update_prices_free()
        except Exception:
            pass

    def init_multiverse_candidates(self) -> None:
        """
        Seed the Stallion Multiverse with the top candidate pairs from the
        current margin universe. Call once after discover_margin_universe().
        """
        if self.multiverse is None or not self.margin_pairs:
            return
        candidates = [
            {'pair': pair, 'volume': 0.01, 'leverage': 5}
            for pair in list(self.margin_pairs.keys())[:10]
        ]
        prices = {
            pair: info.last_price
            for pair, info in self.margin_pairs.items()
            if info.last_price > 0
        }
        self.multiverse.set_candidates(candidates, prices)
        logger.info(
            f"[Multiverse] Seeded {self.multiverse.shadow_count} shadow rides "
            f"from margin universe"
        )


def main():
    global PROFIT_TARGET_USD, MIN_PROFIT_USD

    parser = argparse.ArgumentParser(
        description="Kraken Margin Army Trader - ALL IN, GBP1 PROFIT, OUT"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulation mode")
    parser.add_argument("--scan-only", action="store_true", help="Show pairs and exit")
    parser.add_argument(
        "--target", type=float, default=PROFIT_TARGET_USD,
        help=f"Profit target in USD (default: {PROFIT_TARGET_USD})"
    )
    parser.add_argument(
        "--mission-hunt", action="store_true",
        help="1-minute mission: scan for winner, open, close within 60s"
    )
    parser.add_argument(
        "--pride", action="store_true",
        help="Pride mode: continuous hunt loop — patrol, strike, feed, repeat until Ctrl+C"
    )
    parser.add_argument(
        "--side", choices=["long", "short"], default=None,
        help="Force mission/pride direction: 'long' (buy) or 'short' (sell). Default: hunt both."
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    PROFIT_TARGET_USD = args.target
    MIN_PROFIT_USD = args.target

    trader = KrakenMarginArmyTrader(dry_run=args.dry_run)

    if args.mission_hunt or args.pride:
        # Map CLI --side (long/short) → internal side filter (buy/sell)
        side_filter = None
        if args.side == "long":
            side_filter = "buy"
        elif args.side == "short":
            side_filter = "sell"

        if args.pride:
            trader.pride_hunt(side_filter=side_filter)
        else:
            trader.mission_hunt(side_filter=side_filter)
    else:
        trader.run(scan_only=args.scan_only)


if __name__ == "__main__":
    main()
