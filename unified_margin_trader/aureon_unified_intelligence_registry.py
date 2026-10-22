#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
 AUREON UNIFIED INTELLIGENCE REGISTRY
 Chain-Linked Categories for Unified Data Pulling
═══════════════════════════════════════════════════════════════════════════════
 
 CATEGORY STRUCTURE:
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │  SCANNERS (13) ───────────┬──► INTELLIGENCE (11) ───┬──► QUEEN HIVE MIND    │
 │  MARKET DATA (18) ────────┤                         │                        │
 │  WHALE TRACKING (17) ─────┤   BRAINS (6) ───────────┤   (Final 4th Decision) │
 │  BOT/COUNTER-INTEL (14) ──┤   QUANTUM (11) ─────────┤                        │
 │  ANALYZERS (8) ───────────┘   PROBABILITY (14) ─────┘                        │
 └──────────────────────────────────────────────────────────────────────────────┘
 
 Created: 2026-01-17
═══════════════════════════════════════════════════════════════════════════════
"""

try:
    from aureon.core.aureon_baton_link import link_system as _baton_link
    _baton_link(__name__)
except Exception:
    pass
import sys
import os

# Windows UTF-8 fix (opt-in only; avoid import-time stdio mutation)
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        force_stdio_wrap = os.getenv("AUREON_FORCE_UTF8_STDIO", "false").lower() == "true"
        if force_stdio_wrap and _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if force_stdio_wrap and _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import json
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# SACRED CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
PHI = 1.618033988749895  # Golden Ratio
SCHUMANN = 7.83          # Earth's resonance Hz
LOVE_FREQ = 528          # DNA repair frequency Hz

# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SystemEntry:
    """Individual system entry in the registry."""
    name: str
    module: str
    main_class: Optional[str] = None
    purpose: str = ""
    chain_outputs: List[str] = field(default_factory=list)  # What data it produces
    chain_inputs: List[str] = field(default_factory=list)   # What data it consumes
    thought_bus_topics: List[str] = field(default_factory=list)
    is_loaded: bool = False
    instance: Any = None

@dataclass
class CategoryDefinition:
    """Category with chain-link configuration."""
    name: str
    emoji: str
    description: str
    systems: List[SystemEntry] = field(default_factory=list)
    upstream_categories: List[str] = field(default_factory=list)  # Categories that feed INTO this one
    downstream_categories: List[str] = field(default_factory=list)  # Categories this feeds INTO
    thought_bus_pattern: str = ""  # Topic pattern for ThoughtBus


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLETE SYSTEM REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

CATEGORIES: Dict[str, CategoryDefinition] = {
    
    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 1: DATA ACQUISITION
    # ─────────────────────────────────────────────────────────────────────────
    
    "market_data": CategoryDefinition(
        name="Market Data",
        emoji="📊",
        description="Raw market data acquisition - prices, tickers, orderbooks, feeds",
        upstream_categories=[],  # Root layer - no upstream
        downstream_categories=["scanners", "whale_tracking", "analyzers"],
        thought_bus_pattern="market.*",
        systems=[
            SystemEntry("Global Financial Feed", "global_financial_feed", "GlobalFinancialFeed",
                       "Aggregates ENTIRE Earth's financial ecosystem - Crypto, Forex, Stocks, Commodities, Bonds, DXY, Fear & Greed, VIX",
                       chain_outputs=["prices", "volumes", "indices", "sentiment"],
                       thought_bus_topics=["market.global", "market.fear_greed", "market.vix"]),
            SystemEntry("Unified Ecosystem", "aureon_unified_ecosystem", "AureonKrakenEcosystem",
                       "Multi-exchange live market data feeds",
                       chain_outputs=["ticker_data", "exchange_status", "balances"],
                       thought_bus_topics=["market.ecosystem", "execution.*"]),
            SystemEntry("WebSocket Aggregator", "unified_ws_feed", "UnifiedWSFeed",
                       "Production-grade WebSocket aggregator for Binance, Kraken, Capital.com, Coinbase streams",
                       chain_outputs=["live_trades", "live_orderbooks", "depth_updates"],
                       thought_bus_topics=["market.ws.*"]),
            SystemEntry("Central Prefetch Service", "market_data_hub", "MarketDataHub",
                       "Central prefetching service - reduces API calls/429 errors",
                       chain_outputs=["cached_prices", "cached_tickers"],
                       thought_bus_topics=["market.cache"]),
            SystemEntry("Binance Feed", "aureon_live_market_feed", "BinanceLiveFeed",
                       "Binance exchange data feed",
                       chain_outputs=["binance_prices", "binance_trades"]),
            SystemEntry("Kraken Feed", "aureon_live_market_feed", "KrakenLiveFeed",
                       "Kraken exchange data feed",
                       chain_outputs=["kraken_prices", "kraken_trades"]),
            SystemEntry("Alpaca Feed", "alpaca_sse_client", "AlpacaSSEClient",
                       "Alpaca SSE streaming for stocks",
                       chain_outputs=["alpaca_prices", "alpaca_quotes"]),
            SystemEntry("Coinbase History", "coinbase_historical_feed", None,
                       "Coinbase historical data feed",
                       chain_outputs=["historical_candles"]),
            SystemEntry("CoinGecko Feed", "aureon_live_market_feed", "CoinGeckoFeed",
                       "CoinGecko price data feed",
                       chain_outputs=["coingecko_prices", "market_caps"]),
            SystemEntry("Orderbook Depth", "aureon_whale_orderbook_analyzer", "WhaleOrderbookAnalyzer",
                       "Orderbook depth analysis for whale detection",
                       chain_outputs=["bid_walls", "ask_walls", "depth_imbalance"],
                       thought_bus_topics=["market.orderbook.*"]),
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 2: SCANNERS (Pattern Detection)
    # ─────────────────────────────────────────────────────────────────────────
    
    "scanners": CategoryDefinition(
        name="Scanners",
        emoji="🔍",
        description="Pattern detection across markets - momentum, arbitrage, wave states",
        upstream_categories=["market_data"],
        downstream_categories=["intelligence", "probability"],
        thought_bus_pattern="scanner.*",
        systems=[
            SystemEntry("Global Wave Scanner", "aureon_global_wave_scanner", "GlobalWaveScanner",
                       "Full A-Z, Z-A market coverage with wave allocation analysis - RISING, PEAK, FALLING, TROUGH, BALANCED",
                       chain_inputs=["prices", "volumes"],
                       chain_outputs=["wave_states", "momentum_scores", "breakout_signals"],
                       thought_bus_topics=["scanner.wave", "wave.*"]),
            SystemEntry("Ocean Scanner", "aureon_ocean_scanner", "OceanScanner",
                       "Turtle in the ocean - scans 13,000+ opportunities across Kraken, Alpaca, Binance",
                       chain_inputs=["ticker_data", "exchange_status"],
                       chain_outputs=["opportunities", "arbitrage_pairs", "momentum_signals"],
                       thought_bus_topics=["scanner.ocean", "ocean.*"]),
            SystemEntry("Quantum Mirror Scanner", "aureon_quantum_mirror_scanner", "QuantumMirrorScanner",
                       "Reality branch coherence detection - maps beneficial outcome probability fields",
                       chain_inputs=["prices", "wave_states"],
                       chain_outputs=["branch_coherence", "timeline_probability"],
                       thought_bus_topics=["scanner.quantum", "quantum.*"]),
            SystemEntry("Animal Momentum Scanners", "aureon_animal_momentum_scanners", None,
                       "Wolf (sniper), Lion (multi-target), Army Ants (small profits), Hummingbird (micro-rotation)",
                       chain_inputs=["prices", "volumes", "wave_states"],
                       chain_outputs=["sniper_targets", "hunt_targets", "micro_opportunities"],
                       thought_bus_topics=["scanner.wolf", "scanner.lion", "scanner.ants"]),
            SystemEntry("Alpaca Stock Scanner", "aureon_alpaca_stock_scanner", None,
                       "Alpaca-specific stock market scanner",
                       chain_inputs=["alpaca_prices", "alpaca_quotes"],
                       chain_outputs=["stock_momentum", "stock_opportunities"],
                       thought_bus_topics=["scanner.alpaca"]),
            SystemEntry("Bot Shape Scanner", "aureon_bot_shape_scanner", "BotShapeScanner",
                       "Scans for bot shape patterns in market data",
                       chain_inputs=["live_trades", "orderbook_depth"],
                       chain_outputs=["bot_shapes", "bot_confidence"],
                       thought_bus_topics=["scanner.bot"]),
            SystemEntry("Wisdom Scanner", "aureon_wisdom_scanner", "AureonWisdomScanner",
                       "Scans for wisdom insights across civilizations",
                       chain_outputs=["wisdom_insights"],
                       thought_bus_topics=["scanner.wisdom"]),
            SystemEntry("Warfare Intelligence Scanner", "aureon_strategic_warfare_scanner", "StrategicWarfareScanner",
                       "Sun Tzu + IRA + Apache warfare intelligence - power structures, coordination networks",
                       chain_inputs=["bot_shapes", "firm_activity"],
                       chain_outputs=["strategic_vulnerabilities", "power_maps"],
                       thought_bus_topics=["scanner.warfare"]),
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 2B: WHALE TRACKING (Large Player Detection)
    # ─────────────────────────────────────────────────────────────────────────
    
    "whale_tracking": CategoryDefinition(
        name="Whale Tracking",
        emoji="🐋",
        description="Large player detection and tracking - whales, sharks, institutional moves",
        upstream_categories=["market_data"],
        downstream_categories=["intelligence", "counter_intel"],
        thought_bus_pattern="whale.*",
        systems=[
            SystemEntry("Whale Orderbook Analyzer", "aureon_whale_orderbook_analyzer", "WhaleOrderbookAnalyzer",
                       "Comprehensive whale classification by position size - MEGALODON, LEVIATHAN, SHARK, WHALE, MINNOW",
                       chain_inputs=["bid_walls", "ask_walls", "depth_imbalance"],
                       chain_outputs=["whale_walls", "whale_classification", "position_sizes"],
                       thought_bus_topics=["whale.orderbook", "whale.walls"]),
            SystemEntry("Moby Dick Hunter", "aureon_moby_dick_whale_hunter", "MobyDickWhaleHunter",
                       "Captain Ahab's whale hunting - GAM system, Fedallah's Prophecies, Three Harpoons validation",
                       chain_inputs=["whale_walls", "live_trades"],
                       chain_outputs=["whale_targets", "hunting_opportunities"],
                       thought_bus_topics=["whale.hunt", "whale.moby"]),
            SystemEntry("Whale Behavior Predictor", "aureon_whale_behavior_predictor", "WhaleBehaviorPredictor",
                       "Batten Matrix 4-pass validation to predict whale next moves",
                       chain_inputs=["whale_classification", "historical_patterns"],
                       chain_outputs=["predicted_moves", "whale_intent"],
                       thought_bus_topics=["whale.predict"]),
            SystemEntry("Whale Live Profiler", "aureon_live_whale_profiler", "LiveWhaleProfiler",
                       "Real-time whale profiling",
                       chain_inputs=["live_trades", "whale_classification"],
                       chain_outputs=["whale_profiles", "activity_patterns"],
                       thought_bus_topics=["whale.profile"]),
            SystemEntry("Whale Sonar", "mycelium_whale_sonar", "WhaleSonar",
                       "ThoughtBus listener treating subsystems as whales - emits compact sonar for Queen/Enigma",
                       chain_inputs=["all_thoughts"],
                       chain_outputs=["whale_signals", "sonar_codes"],
                       thought_bus_topics=["whale.sonar.*"]),
            SystemEntry("Orca Intelligence", "aureon_orca_intelligence", "OrcaKillerWhaleIntelligence",
                       "Killer whale hunts whales - ride whale momentum for micro-profits",
                       chain_inputs=["whale_targets", "predicted_moves"],
                       chain_outputs=["ride_signals", "exit_timing"],
                       thought_bus_topics=["whale.orca", "orca.*"]),
            SystemEntry("Orca Breakout Hunter", "queen_volume_hunter", "QueenVolumeHunter",
                       "Queen's volume breakout hunter - trained on 3,178 trades, 64% win rate",
                       chain_inputs=["volumes", "whale_walls"],
                       chain_outputs=["breakout_signals"],
                       thought_bus_topics=["whale.breakout"]),
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 2C: BOT/COUNTER-INTELLIGENCE
    # ─────────────────────────────────────────────────────────────────────────
    
    "counter_intel": CategoryDefinition(
        name="Counter-Intelligence",
        emoji="🕵️",
        description="Bot detection, firm tracking, counter-measures against algorithmic opponents",
        upstream_categories=["market_data", "whale_tracking"],
        downstream_categories=["intelligence"],
        thought_bus_pattern="bot.*|firm.*|counter.*",
        systems=[
            SystemEntry("Bot Hunter Dashboard", "aureon_bot_hunter_dashboard", "BotEngine",
                       "Real-time bot detection - HFT, market maker, iceberg, scalper, wash trading",
                       chain_inputs=["live_trades", "orderbook_depth"],
                       chain_outputs=["bot_detections", "bot_types", "bot_confidence"],
                       thought_bus_topics=["bot.detected", "bot.type.*"]),
            SystemEntry("Bot Live Tracker", "aureon_planetary_bot_tracker", "PlanetaryBotTracker",
                       "Live WebSocket bot tracking from Binance/Kraken with known bot signatures",
                       chain_inputs=["live_trades"],
                       chain_outputs=["bot_activity", "known_bot_trades"],
                       thought_bus_topics=["bot.live", "bot.known"]),
            SystemEntry("Bot Shape Classifier", "aureon_bot_shape_classifier", "BotShapeClassifier",
                       "Spectral analysis to classify bot shapes - grid, spiral, oscillator, taper, accumulation/distribution",
                       chain_inputs=["bot_shapes"],
                       chain_outputs=["classified_bots", "shape_patterns"],
                       thought_bus_topics=["bot.shape"]),
            SystemEntry("Cultural Bot Fingerprinting", "aureon_cultural_bot_fingerprinting", None,
                       "Cultural pattern-based bot ownership - holiday gaps, timezone preferences, risk appetites",
                       chain_inputs=["bot_activity", "timing_patterns"],
                       chain_outputs=["cultural_fingerprints", "likely_owners"],
                       thought_bus_topics=["bot.cultural"]),
            SystemEntry("Firm Intelligence Catalog", "aureon_firm_intelligence_catalog", "FirmIntelligenceCatalog",
                       "50+ major trading firm database with bot signatures, geographic distribution",
                       chain_inputs=["bot_detections", "classified_bots"],
                       chain_outputs=["firm_attribution", "firm_patterns"],
                       thought_bus_topics=["firm.intel", "firm.activity"]),
            SystemEntry("Firm Live Intelligence", "aureon_global_firm_intelligence", "FirmAttributionEngine",
                       "Real-time intelligence tracking 24-hour movement history, pattern recognition",
                       chain_inputs=["firm_attribution", "live_trades"],
                       chain_outputs=["firm_live_activity", "firm_success_rates"],
                       thought_bus_topics=["firm.live"]),
            SystemEntry("Counter Intelligence System", "aureon_queen_counter_intelligence", "QueenCounterIntelligence",
                       "Queen's counter-intelligence weapon - timing advantages (30-200ms faster)",
                       chain_inputs=["firm_patterns", "bot_types"],
                       chain_outputs=["counter_strategies", "exploit_signals"],
                       thought_bus_topics=["counter.strategy", "counter.exploit"]),
            SystemEntry("Global Bot Map", "aureon_global_bot_map", None,
                       "Maps global bot movements as TIDAL WAVES - countries, companies, governments",
                       chain_inputs=["firm_attribution", "cultural_fingerprints"],
                       chain_outputs=["global_bot_map", "tidal_patterns"],
                       thought_bus_topics=["bot.global"]),
            SystemEntry("Surveillance Dashboard", "aureon_surveillance_dashboard", None,
                       "WATCH THEM MOVE OUR MONEY - live streaming, spectrogram visualization",
                       chain_inputs=["live_trades", "bot_activity", "whale_activity"],
                       chain_outputs=["surveillance_alerts"],
                       thought_bus_topics=["surveillance.*"]),
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 3: ANALYZERS (Deep Analysis)
    # ─────────────────────────────────────────────────────────────────────────
    
    "analyzers": CategoryDefinition(
        name="Analyzers",
        emoji="🔬",
        description="Deep analysis systems - money flow, trade profiling, pattern recognition",
        upstream_categories=["market_data", "scanners"],
        downstream_categories=["intelligence", "probability"],
        thought_bus_pattern="analyzer.*",
        systems=[
            SystemEntry("Deep Money Flow Analyzer", "aureon_deep_money_flow_analyzer", "DeepMoneyFlowAnalyzer",
                       "Ultimate system tracing money flows through time - who moved it, where it went",
                       chain_inputs=["live_trades", "whale_activity", "firm_activity"],
                       chain_outputs=["money_flow_maps", "flow_predictions"],
                       thought_bus_topics=["analyzer.money_flow"]),
            SystemEntry("Historical Coordination Analysis", "aureon_historical_manipulation_hunter", "HistoricalManipulationHunter",
                       "Tracks coordination across 125 years (1900-2026) - Federal Reserve, Great Depression, 2008",
                       chain_inputs=["historical_data"],
                       chain_outputs=["coordination_patterns", "macro_signals"],
                       thought_bus_topics=["analyzer.historical"]),
            SystemEntry("Trade Profiler", "trade_analyzer", "TradeDataAnalyzer",
                       "Uses 16 learned patterns with 90%+ win rate to predict setups",
                       chain_inputs=["prices", "volumes", "wave_states"],
                       chain_outputs=["trade_setups", "pattern_matches"],
                       thought_bus_topics=["analyzer.trades"]),
            SystemEntry("Bot Intelligence Profiler", "aureon_bot_intelligence_profiler", "BotIntelligenceProfiler",
                       "Bot-to-firm intelligence profiling",
                       chain_inputs=["bot_detections", "firm_attribution"],
                       chain_outputs=["bot_firm_profiles"],
                       thought_bus_topics=["analyzer.bots"]),
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 4: INTELLIGENCE SYSTEMS (Synthesis)
    # ─────────────────────────────────────────────────────────────────────────
    
    "intelligence": CategoryDefinition(
        name="Intelligence Systems",
        emoji="🧠",
        description="High-level intelligence synthesis - combining all inputs into actionable signals",
        upstream_categories=["scanners", "whale_tracking", "counter_intel", "analyzers"],
        downstream_categories=["probability", "brains"],
        thought_bus_pattern="intel.*",
        systems=[
            SystemEntry("Ultimate Intelligence", "probability_ultimate_intelligence", "ProbabilityUltimateIntelligence",
                       "95% accuracy ML prediction with multi-dimensional pattern keys",
                       chain_inputs=["all_scanner_outputs", "all_analyzer_outputs"],
                       chain_outputs=["ultimate_predictions", "confidence_scores"],
                       thought_bus_topics=["intel.ultimate"]),
            SystemEntry("Advanced Intelligence", "aureon_advanced_intelligence", "AdvancedIntelligence",
                       "Consolidated intelligence from 27+ systems: Mycelium neural, Piano harmonic, Multiverse temporal",
                       chain_inputs=["ultimate_predictions", "wave_states", "whale_signals"],
                       chain_outputs=["synthesized_intel", "action_signals"],
                       thought_bus_topics=["intel.advanced"]),
            SystemEntry("Deep Intelligence", "queen_deep_intelligence", "QueenDeepIntelligence",
                       "Autonomous deep thought engine - hypothesis generation, explainable reasoning",
                       chain_inputs=["synthesized_intel", "market_context"],
                       chain_outputs=["deep_insights", "hypotheses"],
                       thought_bus_topics=["intel.deep"]),
            SystemEntry("Complete Profiler Integration", "aureon_complete_profiler_integration", None,
                       "Master integration hub wiring Queen, Enigma, Mycelium, Elephant, Ghost Dance",
                       chain_inputs=["all_intelligence_outputs"],
                       chain_outputs=["integrated_profile"],
                       thought_bus_topics=["intel.integrated"]),
            SystemEntry("Wake Rider Intelligence", "aureon_live_momentum_hunter", "LiveMomentumHunter",
                       "Whale Wake Riding strategy - DETECT → ANALYZE → HARMONIZE → RIDE → EXIT",
                       chain_inputs=["whale_targets", "predicted_moves"],
                       chain_outputs=["ride_strategies", "timing_signals"],
                       thought_bus_topics=["intel.wake_rider"]),
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 5: PROBABILITY & QUANTUM (Prediction)
    # ─────────────────────────────────────────────────────────────────────────
    
    "probability": CategoryDefinition(
        name="Probability Systems",
        emoji="🎯",
        description="Probability calculation and quantum coherence - prediction engines",
        upstream_categories=["scanners", "intelligence", "analyzers"],
        downstream_categories=["brains"],
        thought_bus_pattern="probability.*|quantum.*",
        systems=[
            SystemEntry("Probability Nexus", "aureon_probability_nexus", "EnhancedProbabilityNexus",
                       "ULTIMATE prediction: Harmonic, Coherence, Multi-factor, Mean reversion, Momentum, Volatility, Temporal, Clownfish",
                       chain_inputs=["all_scanner_outputs", "all_intel_outputs"],
                       chain_outputs=["nexus_probability", "batten_validation"],
                       thought_bus_topics=["probability.nexus"]),
            SystemEntry("Quantum Telescope", "aureon_quantum_telescope", "QuantumPrism",
                       "Quantum market observation system",
                       chain_inputs=["market_state", "wave_states"],
                       chain_outputs=["quantum_observations", "collapse_predictions"],
                       thought_bus_topics=["quantum.telescope"]),
            SystemEntry("Timeline Oracle", "aureon_timeline_oracle", "TimelineOracle",
                       "Temporal prediction engine",
                       chain_inputs=["quantum_observations", "historical_patterns"],
                       chain_outputs=["timeline_predictions", "temporal_anchors"],
                       thought_bus_topics=["quantum.timeline"]),
            SystemEntry("Stargate Protocol", "aureon_stargate_protocol", "StargateProtocolEngine",
                       "Planetary node resonance network",
                       chain_inputs=["schumann_resonance", "harmonic_state"],
                       chain_outputs=["stargate_coherence", "manifestation_windows"],
                       thought_bus_topics=["quantum.stargate"]),
            SystemEntry("Timeline Anchor Validator", "aureon_timeline_anchor_validator", None,
                       "7-day validation across prime/Fibonacci intervals",
                       chain_inputs=["timeline_predictions"],
                       chain_outputs=["anchored_timelines", "validation_strength"],
                       thought_bus_topics=["quantum.anchor"]),
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 6: BRAINS (Decision Making)
    # ─────────────────────────────────────────────────────────────────────────
    
    "brains": CategoryDefinition(
        name="Brain Systems",
        emoji="🧬",
        description="Neural decision systems - Queen SERO, Miner Brain, Sniper Brain",
        upstream_categories=["intelligence", "probability"],
        downstream_categories=["queen"],
        thought_bus_pattern="brain.*",
        systems=[
            SystemEntry("Miner Brain", "aureon_miner_brain", "MinerBrain",
                       "Critical thinking engine: SEARCH, SPECULATE, CROSS-EXAMINE, DEBATE, SYNTHESIZE, LEARN",
                       chain_inputs=["all_intel_outputs", "probability_scores"],
                       chain_outputs=["brain_decisions", "confidence_levels"],
                       thought_bus_topics=["brain.miner"]),
            SystemEntry("Unified Sniper Brain", "unified_sniper_brain", "UnifiedSniperBrain",
                       "1 MILLION trade trained - 100% win rate, Probability Nexus + Wisdom + Sniper Mode",
                       chain_inputs=["nexus_probability", "sniper_targets"],
                       chain_outputs=["sniper_decisions", "kill_signals"],
                       thought_bus_topics=["brain.sniper"]),
            SystemEntry("Core Brain", "aureon_brain", "AureonBrain",
                       "Core brain decision-making module",
                       chain_inputs=["brain_decisions", "sniper_decisions"],
                       chain_outputs=["final_brain_output"],
                       thought_bus_topics=["brain.core"]),
            SystemEntry("Cognition Runtime", "aureon_cognition_runtime", None,
                       "Thought-to-action coordination hub",
                       chain_inputs=["final_brain_output"],
                       chain_outputs=["action_commands"],
                       thought_bus_topics=["brain.cognition"]),
        ]
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 7: QUEEN HIVE MIND (Final Decision)
    # ─────────────────────────────────────────────────────────────────────────
    
    "queen": CategoryDefinition(
        name="Queen Hive Mind",
        emoji="👑",
        description="Central neural controller - 4th decision gate, final execution authority",
        upstream_categories=["brains", "probability", "intelligence"],
        downstream_categories=[],  # Terminal layer - executes
        thought_bus_pattern="queen.*",
        systems=[
            SystemEntry("Queen Hive Mind", "aureon_queen_hive_mind", "QueenHiveMind",
                       "Central neural controller - Tina B with 12 neurons, 4th decision gate",
                       chain_inputs=["all_brain_outputs", "nexus_probability", "batten_validation"],
                       chain_outputs=["queen_decision", "execution_signal"],
                       thought_bus_topics=["queen.decision", "queen.signal"]),
            SystemEntry("Queen SERO", "queen_fully_online", "QueenFullyOnline",
                       "12,000+ lines - Dream Engine, Queen Neuron, Mycelium Network, Enigma Codebreak",
                       chain_inputs=["queen_decision"],
                       chain_outputs=["sero_guidance"],
                       thought_bus_topics=["queen.sero"]),
            SystemEntry("Micro Profit Labyrinth", "micro_profit_labyrinth", None,
                       "Execution engine with turn-based exchange rotation",
                       chain_inputs=["execution_signal"],
                       chain_outputs=["trade_executed", "profit_loss"],
                       thought_bus_topics=["queen.execution", "execution.*"]),
            SystemEntry("Voice Engine", "queen_voice_engine", "QueenVoiceEngine",
                       "Queen's voice - audio feedback system",
                       chain_inputs=["queen_decision"],
                       chain_outputs=["voice_message"],
                       thought_bus_topics=["queen.voice"]),
        ]
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# CHAIN-LINK DATA FLOW DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

CHAIN_LINKS = {
    "market_to_scanner": {
        "source": "market_data",
        "target": "scanners",
        "data_types": ["prices", "volumes", "ticker_data", "orderbook_depth"],
        "description": "Raw market data flows to pattern scanners"
    },
    "market_to_whale": {
        "source": "market_data",
        "target": "whale_tracking",
        "data_types": ["bid_walls", "ask_walls", "depth_imbalance", "live_trades"],
        "description": "Orderbook data flows to whale detection"
    },
    "scanner_to_intel": {
        "source": "scanners",
        "target": "intelligence",
        "data_types": ["wave_states", "momentum_scores", "opportunities", "bot_shapes"],
        "description": "Scanner patterns flow to intelligence synthesis"
    },
    "whale_to_intel": {
        "source": "whale_tracking",
        "target": "intelligence",
        "data_types": ["whale_targets", "predicted_moves", "ride_signals"],
        "description": "Whale signals flow to intelligence"
    },
    "whale_to_counter": {
        "source": "whale_tracking",
        "target": "counter_intel",
        "data_types": ["whale_activity", "whale_classification"],
        "description": "Whale data informs counter-intelligence"
    },
    "counter_to_intel": {
        "source": "counter_intel",
        "target": "intelligence",
        "data_types": ["bot_detections", "firm_attribution", "counter_strategies"],
        "description": "Counter-intel flows to decision making"
    },
    "analyzer_to_intel": {
        "source": "analyzers",
        "target": "intelligence",
        "data_types": ["money_flow_maps", "trade_setups", "pattern_matches"],
        "description": "Analysis results flow to intelligence"
    },
    "intel_to_probability": {
        "source": "intelligence",
        "target": "probability",
        "data_types": ["synthesized_intel", "ultimate_predictions", "action_signals"],
        "description": "Intelligence feeds probability calculations"
    },
    "probability_to_brain": {
        "source": "probability",
        "target": "brains",
        "data_types": ["nexus_probability", "batten_validation", "quantum_observations"],
        "description": "Probabilities feed brain decisions"
    },
    "brain_to_queen": {
        "source": "brains",
        "target": "queen",
        "data_types": ["brain_decisions", "sniper_decisions", "action_commands"],
        "description": "Brain outputs feed Queen's 4th decision"
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED DATA PULLER
# ═══════════════════════════════════════════════════════════════════════════════

class UnifiedDataPuller:
    """
    Chain-linked data puller that aggregates data from all categories.
    
    Usage:
        puller = UnifiedDataPuller()
        puller.initialize()
        
        # Pull all scanner data
        scanner_data = puller.pull_category("scanners")
        
        # Pull unified feed across all categories
        unified = puller.pull_unified()
        
        # Pull chain-linked data (follows upstream dependencies)
        intel_with_deps = puller.pull_with_chain("intelligence")
    """
    
    def __init__(self):
        self.categories = CATEGORIES
        self.chain_links = CHAIN_LINKS
        self.thought_bus = None
        self.loaded_systems: Dict[str, Any] = {}
        self._category_cache: Dict[str, Dict] = {}
        self._last_pull_time: Dict[str, float] = {}
        
    def initialize(self):
        """Initialize ThoughtBus connection and load available systems."""
        try:
            from aureon.core.aureon_thought_bus import ThoughtBus
            self.thought_bus = ThoughtBus.instance() if hasattr(ThoughtBus, 'instance') else ThoughtBus()
            logger.info("✅ ThoughtBus connected for unified data pulling")
        except ImportError:
            logger.warning("⚠️ ThoughtBus not available - using file-based data")
        
        # Try to load each system
        for cat_name, category in self.categories.items():
            for system in category.systems:
                self._try_load_system(system)
        
        loaded_count = sum(1 for s in self.loaded_systems.values() if s is not None)
        logger.info(f"📊 Loaded {loaded_count} / {sum(len(c.systems) for c in self.categories.values())} systems")
        
    def _try_load_system(self, system: SystemEntry) -> bool:
        """Attempt to load a system module."""
        try:
            module = __import__(system.module)
            if system.main_class:
                cls = getattr(module, system.main_class, None)
                if cls:
                    system.is_loaded = True
                    self.loaded_systems[system.name] = cls
                    return True
            else:
                system.is_loaded = True
                self.loaded_systems[system.name] = module
                return True
        except (ImportError, NameError, AttributeError, SyntaxError) as e:
            # Catch common import issues silently
            system.is_loaded = False
            self.loaded_systems[system.name] = None
        except Exception as e:
            # Log unexpected errors but don't crash
            logger.debug(f"Could not load {system.name}: {e}")
            system.is_loaded = False
            self.loaded_systems[system.name] = None
        return False
    
    def pull_category(self, category_name: str, use_cache: bool = True, cache_ttl: float = 5.0) -> Dict:
        """
        Pull all data from a specific category.
        
        Args:
            category_name: Name of category to pull from
            use_cache: Whether to use cached data if fresh
            cache_ttl: Cache time-to-live in seconds
        """
        if category_name not in self.categories:
            return {"error": f"Unknown category: {category_name}"}
        
        # Check cache
        if use_cache and category_name in self._category_cache:
            if time.time() - self._last_pull_time.get(category_name, 0) < cache_ttl:
                return self._category_cache[category_name]
        
        category = self.categories[category_name]
        data = {
            "category": category_name,
            "emoji": category.emoji,
            "description": category.description,
            "systems": {},
            "thought_bus_data": [],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Pull from ThoughtBus if available
        if self.thought_bus:
            data["thought_bus_data"] = self._pull_from_thought_bus(category.thought_bus_pattern)
        
        # Pull from loaded systems
        for system in category.systems:
            if system.is_loaded:
                data["systems"][system.name] = {
                    "loaded": True,
                    "outputs": system.chain_outputs,
                    "topics": system.thought_bus_topics
                }
            else:
                data["systems"][system.name] = {"loaded": False}
        
        # Cache result
        self._category_cache[category_name] = data
        self._last_pull_time[category_name] = time.time()
        
        return data
    
    def _pull_from_thought_bus(self, pattern: str) -> List[Dict]:
        """Pull data from ThoughtBus matching pattern."""
        thoughts = []
        thoughts_file = Path(__file__).parent / "thoughts.jsonl"
        
        if thoughts_file.exists():
            try:
                import re
                regex = re.compile(pattern.replace("*", ".*").replace("|", "|"))
                with open(thoughts_file, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()[-500:]  # Last 500 thoughts
                
                for line in lines:
                    line = line.strip()
                    if line:
                        try:
                            t = json.loads(line)
                            topic = t.get("topic", "")
                            if regex.match(topic):
                                thoughts.append(t)
                        except:
                            pass
            except Exception as e:
                logger.error(f"Error reading thoughts: {e}")
        
        return thoughts[-100:]  # Return last 100 matching
    
    def pull_with_chain(self, category_name: str) -> Dict:
        """
        Pull data from a category AND all its upstream dependencies.
        Follows the chain-link graph to gather all required data.
        """
        if category_name not in self.categories:
            return {"error": f"Unknown category: {category_name}"}
        
        category = self.categories[category_name]
        
        result = {
            "target_category": category_name,
            "chain_data": {},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Pull upstream categories first
        for upstream in category.upstream_categories:
            result["chain_data"][upstream] = self.pull_category(upstream)
        
        # Pull target category
        result["chain_data"][category_name] = self.pull_category(category_name)
        
        return result
    
    def pull_unified(self) -> Dict:
        """
        Pull unified data from ALL categories following the chain-link structure.
        Returns a complete snapshot of the entire intelligence network.
        """
        result = {
            "unified_feed": {},
            "chain_links": self.chain_links,
            "system_counts": {},
            "loaded_counts": {},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        for cat_name in self.categories:
            result["unified_feed"][cat_name] = self.pull_category(cat_name, use_cache=False)
            category = self.categories[cat_name]
            result["system_counts"][cat_name] = len(category.systems)
            result["loaded_counts"][cat_name] = sum(1 for s in category.systems if s.is_loaded)
        
        return result
    
    def get_chain_flow(self) -> Dict:
        """Get the data flow diagram as a structured object."""
        return {
            "categories": {
                name: {
                    "emoji": cat.emoji,
                    "upstream": cat.upstream_categories,
                    "downstream": cat.downstream_categories,
                    "systems_count": len(cat.systems),
                    "loaded_count": sum(1 for s in cat.systems if s.is_loaded)
                }
                for name, cat in self.categories.items()
            },
            "links": self.chain_links
        }
    
    def get_category_summary(self) -> Dict:
        """Get a summary of all categories and their systems."""
        return {
            cat_name: {
                "emoji": cat.emoji,
                "description": cat.description,
                "system_count": len(cat.systems),
                "loaded_count": sum(1 for s in cat.systems if s.is_loaded),
                "systems": [
                    {"name": s.name, "loaded": s.is_loaded, "outputs": s.chain_outputs}
                    for s in cat.systems
                ]
            }
            for cat_name, cat in self.categories.items()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_puller_instance: Optional[UnifiedDataPuller] = None

def get_unified_puller() -> UnifiedDataPuller:
    """Get or create the global UnifiedDataPuller instance."""
    global _puller_instance
    if _puller_instance is None:
        _puller_instance = UnifiedDataPuller()
        _puller_instance.initialize()
    return _puller_instance


# ═══════════════════════════════════════════════════════════════════════════════
# CLI / DIAGNOSTIC
# ═══════════════════════════════════════════════════════════════════════════════

def print_registry_summary():
    """Print a formatted summary of the entire registry."""
    print("═" * 80)
    print("🌌 AUREON UNIFIED INTELLIGENCE REGISTRY")
    print("═" * 80)
    
    total_systems = 0
    total_loaded = 0
    
    for cat_name, category in CATEGORIES.items():
        sys_count = len(category.systems)
        total_systems += sys_count
        
        print(f"\n{category.emoji} {category.name.upper()} ({sys_count} systems)")
        print(f"   {category.description}")
        print(f"   ↑ Upstream: {', '.join(category.upstream_categories) or 'None (root)'}")
        print(f"   ↓ Downstream: {', '.join(category.downstream_categories) or 'None (terminal)'}")
        print(f"   📡 ThoughtBus: {category.thought_bus_pattern}")
        print(f"   Systems:")
        
        for system in category.systems:
            status = "✅" if system.is_loaded else "⬜"
            total_loaded += 1 if system.is_loaded else 0
            outputs = ", ".join(system.chain_outputs[:3]) + ("..." if len(system.chain_outputs) > 3 else "")
            print(f"      {status} {system.name}")
            if outputs:
                print(f"         → Outputs: {outputs}")
    
    print("\n" + "═" * 80)
    print(f"📊 TOTAL: {total_systems} systems across {len(CATEGORIES)} categories")
    print(f"🔗 CHAIN LINKS: {len(CHAIN_LINKS)} data flow connections")
    print("═" * 80)


def print_chain_flow():
    """Print the data flow chain as ASCII art."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    AUREON INTELLIGENCE CHAIN FLOW                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   ┌─────────────────┐                                                        ║
║   │ 📊 MARKET DATA  │ ◄── Raw feeds: prices, orderbooks, tickers             ║
║   └────────┬────────┘                                                        ║
║            │                                                                 ║
║   ┌────────┼────────────────────────┐                                        ║
║   ▼        ▼                        ▼                                        ║
║ ┌──────┐ ┌─────────────┐ ┌────────────────┐                                  ║
║ │🔍 SCAN│ │🐋 WHALE TRACK│ │🕵️ COUNTER-INTEL│                                  ║
║ └──┬───┘ └──────┬──────┘ └───────┬────────┘                                  ║
║    │            │                │                                           ║
║    └────────────┼────────────────┘                                           ║
║                 ▼                                                            ║
║         ┌─────────────┐      ┌────────────┐                                  ║
║         │🔬 ANALYZERS │ ───► │🧠 INTELLIGENCE│                                ║
║         └─────────────┘      └──────┬─────┘                                  ║
║                                     │                                        ║
║                              ┌──────┴──────┐                                 ║
║                              ▼             ▼                                 ║
║                        ┌──────────┐  ┌───────────┐                           ║
║                        │🎯 PROBAB │  │🧬 BRAINS  │                           ║
║                        └────┬─────┘  └─────┬─────┘                           ║
║                             │              │                                 ║
║                             └──────┬───────┘                                 ║
║                                    ▼                                         ║
║                           ┌────────────────┐                                 ║
║                           │ 👑 QUEEN HIVE  │ ◄── 4th Decision Gate           ║
║                           │    MIND        │                                 ║
║                           └────────┬───────┘                                 ║
║                                    ▼                                         ║
║                              ⚡ EXECUTION                                    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Aureon Unified Intelligence Registry")
    parser.add_argument("--summary", action="store_true", help="Print registry summary")
    parser.add_argument("--flow", action="store_true", help="Print chain flow diagram")
    parser.add_argument("--pull", type=str, help="Pull data from category")
    parser.add_argument("--unified", action="store_true", help="Pull unified data")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.summary:
        print_registry_summary()
    elif args.flow:
        print_chain_flow()
    elif args.pull:
        puller = get_unified_puller()
        data = puller.pull_category(args.pull)
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"\n{data['emoji']} {args.pull.upper()}")
            print(f"Systems: {len(data['systems'])}")
            print(f"ThoughtBus events: {len(data['thought_bus_data'])}")
    elif args.unified:
        puller = get_unified_puller()
        data = puller.pull_unified()
        if args.json:
            print(json.dumps(data, indent=2, default=str))
        else:
            print("\n🌌 UNIFIED DATA PULL")
            for cat, count in data["system_counts"].items():
                loaded = data["loaded_counts"][cat]
                print(f"  {cat}: {loaded}/{count} loaded")
    else:
        print_registry_summary()
        print()
        print_chain_flow()
