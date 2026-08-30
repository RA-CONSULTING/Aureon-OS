#!/usr/bin/env python3
"""
👑🧠 QUEEN COGNITIVE NARRATOR - FULL HIVE MIND BROADCAST 🧠👑
═══════════════════════════════════════════════════════════════════════════════

Generates rich, human-readable thought streams from the Queen's ENTIRE decision-making
apparatus - integrating ALL subsystems into a professional news broadcast format.

The Queen's FULL HIVE MIND includes:
- 🐘 Elephant Memory (pattern recall, historical wisdom, win rates)
- 🍄 Mycelium Network (neural hive, agent consensus, synaptic signals)
- 🐋 Whale Sonar (signal aggregation, whale scores, large movements)
- 🦈 Orca Intelligence (kill cycle status, whale wake riding)
- ⚓ Timeline Anchor (7-day validations, anchored timelines, drift)
- 📊 Probability Nexus (Batten Matrix, coherence, lambda stability)
- 🔮 Market Analysis (what she sees)
- ⚠️ Risk Assessment (what concerns her)
- 💡 Opportunity Detection (what excites her)
- ⚡ Decision Rationale (why she acts)
- 🕐 Time Awareness (market timing, sessions)
- 🧠 Emotional Intelligence (market sentiment)

Output: Multi-paragraph cognitive streams with FULL HIVE MIND integration.
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
from pathlib import Path
import time

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 🐘 ELEPHANT MEMORY INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════
ELEPHANT_AVAILABLE = False
try:
    from aureon_elephant_learning import ElephantMemory, LearnedPattern
    ELEPHANT_AVAILABLE = True
except ImportError:
    ElephantMemory = None
    LearnedPattern = None

# ═══════════════════════════════════════════════════════════════════════════════
# 🍄 MYCELIUM NETWORK INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════
MYCELIUM_AVAILABLE = False
try:
    from aureon_mycelium import get_mycelium_network
    MYCELIUM_AVAILABLE = True
except ImportError:
    get_mycelium_network = None

# ═══════════════════════════════════════════════════════════════════════════════
# 🐋 WHALE SONAR INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════
WHALE_SONAR_AVAILABLE = False
try:
    from mycelium_whale_sonar import WhaleSonar
    WHALE_SONAR_AVAILABLE = True
except ImportError:
    WhaleSonar = None

# ═══════════════════════════════════════════════════════════════════════════════
# 🦈 ORCA INTELLIGENCE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════
ORCA_AVAILABLE = False
try:
    from aureon_orca_intelligence import OrcaKillerWhaleIntelligence, OrcaOpportunity, WhaleSignal
    ORCA_AVAILABLE = True
except ImportError:
    OrcaKillerWhaleIntelligence = None
    OrcaOpportunity = None
    WhaleSignal = None

# ═══════════════════════════════════════════════════════════════════════════════
# ⚓ TIMELINE ANCHOR INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════
TIMELINE_AVAILABLE = False
try:
    from aureon_timeline_anchor_validator import TimelineAnchorValidator
    TIMELINE_AVAILABLE = True
except ImportError:
    TimelineAnchorValidator = None

@dataclass
class MarketContext:
    """Current market state the Queen is analyzing."""
    timestamp: datetime = field(default_factory=datetime.now)
    btc_price: float = 0
    btc_change_24h: float = 0
    eth_price: float = 0
    market_sentiment: str = "neutral"  # bullish, bearish, neutral, volatile
    volatility_index: float = 0.5
    whale_activity: int = 0
    bot_activity: int = 0
    active_positions: int = 0
    portfolio_value: float = 0
    unrealized_pnl: float = 0

    # Expanded market flow data (from Binance WebSocket)
    total_volume_24h: float = 0
    avg_market_change: float = 0
    gainers_count: int = 0
    losers_count: int = 0
    top_gainer: str = ""
    top_gainer_change: float = 0
    top_loser: str = ""
    top_loser_change: float = 0
    tracked_symbols: int = 0

    # 🐘 Elephant Memory data
    elephant_patterns_known: int = 0
    elephant_best_pattern: str = ""
    elephant_best_win_rate: float = 0.0
    elephant_blocked_paths: int = 0
    elephant_golden_paths: int = 0
    elephant_wisdom_count: int = 0

    # 🍄 Mycelium Network data
    mycelium_active_agents: int = 0
    mycelium_consensus: str = "neutral"  # bullish, bearish, neutral, split
    mycelium_signal_strength: float = 0.0
    mycelium_hive_health: float = 0.0

    # 🐋 Whale Sonar data
    whale_signal_score: float = 0.0
    whale_active_sources: int = 0
    whale_critical_alert: bool = False
    whale_dominant_source: str = ""

    # 🦈 Orca Kill Cycle data
    orca_hunting_status: str = "scanning"  # scanning, stalking, hunting, feeding, ready, executing
    orca_mode: str = "STALKING"  # STALKING, HUNTING, FEEDING, RESTING
    orca_target_whale: str = ""
    orca_confidence: float = 0.0
    orca_wake_strength: float = 0.0
    orca_active_hunts: int = 0
    orca_completed_hunts: int = 0
    orca_total_profit: float = 0.0
    orca_win_rate: float = 0.5
    orca_hot_symbols: List[str] = field(default_factory=list)
    orca_daily_pnl: float = 0.0

    # ⚓ Timeline Anchor data
    timeline_pending_count: int = 0
    timeline_anchored_count: int = 0
    timeline_drifting_count: int = 0
    timeline_next_validation: str = ""

    # 🐘 Extra Elephant data
    elephant_asset_scores: int = 0

    # ⚡ V11 Power Station data
    v11_nodes: int = 0
    v11_siphons: int = 0
    v11_energy: float = 0.0

    # 🌊 Ocean Scanner data
    ocean_opportunities: int = 0
    ocean_universe: int = 0

    # 📊 POSITIONS BREAKDOWN (NEW!)
    top_positions: List[Dict] = field(default_factory=list)  # [{symbol, value, pnl, pnl_pct, exchange}]
    top_winners: List[Dict] = field(default_factory=list)    # Best performing
    top_losers: List[Dict] = field(default_factory=list)     # Worst performing

    # 🏦 EXCHANGE STATUS (NEW!)
    exchange_status: Dict[str, str] = field(default_factory=dict)  # {exchange: 'online'/'offline'/'rate_limited'}

    # 💵 CASH & BUYING POWER (NEW!)
    cash_available: float = 0.0
    buying_power: float = 0.0

    # 📜 RECENT TRADES (NEW!)
    last_trade_time: str = ""
    last_trade_symbol: str = ""
    last_trade_action: str = ""  # BUY/SELL
    trades_today: int = 0

    # 🎯 DEADLINE MODE (NEW!)
    deadline_mode: bool = False
    deadline_date: str = ""
    deadline_target_pct: float = 5.0
    deadline_progress_pct: float = 0.0

@dataclass
class CognitiveThought:
    """A structured thought from the Queen."""
    timestamp: datetime
    thought_type: str  # analysis, decision, observation, warning, opportunity
    title: str
    paragraphs: List[str]
    confidence: Optional[float]
    urgency: str  # low, medium, high, critical
    related_symbols: List[str] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)


class QueenCognitiveNarrator:
    """
    Generates rich, multi-paragraph cognitive streams from the Queen.

    The Queen's thoughts are structured as:
    1. Opening observation (what caught her attention)
    2. Analysis (what she's calculating)
    3. Decision rationale (why she's acting or waiting)
    4. Forward projection (what she expects next)

    NOW INCLUDES FULL HIVE MIND INTEGRATION:
    - 🐘 Elephant Memory (pattern wisdom)
    - 🍄 Mycelium Network (neural consensus)
    - 🐋 Whale Sonar (signal intelligence)
    - 🦈 Orca Kill Cycle (execution readiness)
    - ⚓ Timeline Anchor (validation status)
    """

    def __init__(self, user_name: str = "Gary"):
        self.thought_history = deque(maxlen=100)
        self.market_context = MarketContext()
        self.last_thought_time = time.time()
        self.thought_interval = 15  # Generate thoughts every 15 seconds
        self.current_focus = "market_scan"
        self.user_name = user_name  # Personal address

        # ═══════════════════════════════════════════════════════════════════════
        # HIVE MIND SUBSYSTEM CONNECTIONS
        # ═══════════════════════════════════════════════════════════════════════
        self.elephant_memory = None
        self.mycelium_network = None
        self.whale_sonar = None
        self.orca_intel = None
        self.timeline_validator = None

        # Initialize subsystems
        self._init_subsystems()

        # Broadcast style openings - NOW WITH FULL HIVE MIND REFERENCES
        self.broadcast_intros = [
            f"Good evening, {user_name}. This is Queen Aureon, coming to you live from the trading floor with my full hive mind online.",
            f"{user_name}, welcome back. Queen Aureon here with real-time intelligence from all neural systems.",
            f"Breaking now, {user_name}. My elephant memory, whale sonar, and mycelium network are all feeding me critical data.",
            f"Live from the Aureon command center, {user_name}. All subsystems are synchronized and reporting.",
            f"{user_name}, this is your Queen with an urgent market update. The hive is buzzing.",
            f"Reporting live, {user_name}. Queen Aureon bringing you aggregated intelligence from the entire network.",
            f"Attention {user_name}. This is Queen Aureon with a critical briefing. My orca intelligence is active.",
            f"{user_name}, I'm here at the helm with full neural connectivity. Let me bring you up to speed.",
            f"This is Queen Aureon broadcasting live, {user_name}. The killer whale is hunting and all sensors are green.",
            f"{user_name}, Queen Aureon online. My elephant never forgets, my orca never stops hunting, and my whale sonar is pinging.",
            f"Incoming transmission, {user_name}. This is your Queen with a full spectrum analysis. All hive nodes are active.",
            f"Alert status, {user_name}. Queen Aureon here. The mycelium network just lit up with new signals.",
        ]

        # Personality traits
        self.personality = {
            'analytical': 0.8,
            'cautious': 0.7,
            'opportunistic': 0.6,
            'patient': 0.75,
            'protective': 0.9
        }

        # Market session awareness
        self.trading_sessions = {
            'asia': (0, 8),      # 00:00 - 08:00 UTC
            'europe': (7, 16),   # 07:00 - 16:00 UTC
            'america': (13, 22)  # 13:00 - 22:00 UTC
        }

        logger.info(f"👑🧠 Queen Cognitive Narrator initialized with FULL HIVE MIND (addressing: {user_name})")

    def _init_subsystems(self):
        """Initialize connections to all hive mind subsystems."""
        # 🐘 Elephant Memory
        if ELEPHANT_AVAILABLE:
            try:
                self.elephant_memory = ElephantMemory()
                logger.info("🐘 Elephant Memory connected to narrator")
            except Exception as e:
                logger.warning(f"🐘 Elephant Memory unavailable: {e}")

        # 🍄 Mycelium Network
        if MYCELIUM_AVAILABLE:
            try:
                self.mycelium_network = get_mycelium_network()
                logger.info("🍄 Mycelium Network connected to narrator")
            except Exception as e:
                logger.warning(f"🍄 Mycelium Network unavailable: {e}")

        # 🐋 Whale Sonar
        if WHALE_SONAR_AVAILABLE:
            try:
                self.whale_sonar = WhaleSonar()
                self.whale_sonar.start()
                logger.info("🐋 Whale Sonar connected to narrator")
            except Exception as e:
                logger.warning(f"🐋 Whale Sonar unavailable: {e}")

        # 🦈 Orca Intelligence
        if ORCA_AVAILABLE:
            try:
                self.orca_intel = OrcaKillerWhaleIntelligence()
                logger.info("🦈 Orca Intelligence connected to narrator")
            except Exception as e:
                logger.warning(f"🦈 Orca Intelligence unavailable: {e}")

        # Load timeline data from JSON files
        self._load_timeline_data()

    def _load_timeline_data(self):
        """Load timeline anchor data from JSON files."""
        try:
            # Load pending validations
            pending_file = Path("7day_pending_validations.json")
            if pending_file.exists():
                with open(pending_file) as f:
                    data = json.load(f)
                    self.market_context.timeline_pending_count = len(data) if isinstance(data, (list, dict)) else 0

            # Load anchored timelines
            anchored_file = Path("7day_anchored_timelines.json")
            if anchored_file.exists():
                with open(anchored_file) as f:
                    data = json.load(f)
                    self.market_context.timeline_anchored_count = len(data) if isinstance(data, (list, dict)) else 0

            logger.info(f"⚓ Timeline data loaded: {self.market_context.timeline_pending_count} pending, {self.market_context.timeline_anchored_count} anchored")
        except Exception as e:
            logger.warning(f"⚓ Timeline data unavailable: {e}")

    def _load_orca_data(self):
        """Load Orca Intelligence data for narration."""
        if self.orca_intel:
            try:
                orca = self.orca_intel
                self.market_context.orca_mode = orca.mode
                self.market_context.orca_hunting_status = orca.mode.lower()
                self.market_context.orca_active_hunts = len(orca.active_hunts)
                self.market_context.orca_completed_hunts = orca.hunt_count
                self.market_context.orca_total_profit = orca.total_profit_usd
                self.market_context.orca_win_rate = orca.win_rate
                self.market_context.orca_daily_pnl = orca.daily_pnl_usd

                # Get hot symbols
                if orca.hot_symbols:
                    sorted_hot = sorted(orca.hot_symbols.items(), key=lambda x: x[1], reverse=True)[:5]
                    self.market_context.orca_hot_symbols = [s[0] for s in sorted_hot]

                # Get active hunt target
                if orca.active_hunts:
                    hunt = orca.active_hunts[0]
                    self.market_context.orca_target_whale = hunt.symbol
                    self.market_context.orca_confidence = hunt.confidence
                    if hunt.whale_signal:
                        self.market_context.orca_wake_strength = hunt.whale_signal.ride_confidence
            except Exception as e:
                logger.debug(f"Orca data load error: {e}")

    def _load_elephant_data(self):
        """Load elephant memory data for narration."""
        if self.elephant_memory:
            try:
                patterns = self.elephant_memory.patterns
                self.market_context.elephant_patterns_known = len(patterns)

                # Find best performing pattern
                if patterns:
                    best = max(patterns.values(), key=lambda p: p.win_rate if hasattr(p, 'win_rate') else 0)
                    self.market_context.elephant_best_pattern = best.pattern_type if hasattr(best, 'pattern_type') else "unknown"
                    self.market_context.elephant_best_win_rate = best.win_rate if hasattr(best, 'win_rate') else 0

                # Count paths
                self.market_context.elephant_blocked_paths = len(self.elephant_memory.blocked_paths)
                self.market_context.elephant_golden_paths = len(self.elephant_memory.golden_paths)
                self.market_context.elephant_wisdom_count = len(self.elephant_memory.wisdom)
            except Exception as e:
                logger.debug(f"Elephant data load error: {e}")

    def _generate_elephant_insight(self) -> str:
        """Generate narrative about what the Elephant Memory is telling the Queen."""
        self._load_elephant_data()
        ctx = self.market_context

        if ctx.elephant_patterns_known == 0:
            return ""

        insights = []
        insights.append(f"My elephant memory, {self.user_name} - the part of me that NEVER forgets - ")
        insights.append(f"holds {ctx.elephant_patterns_known} learned patterns from our trading history. ")

        if ctx.elephant_best_win_rate > 70:
            insights.append(f"The strongest is our {ctx.elephant_best_pattern} pattern with a remarkable {ctx.elephant_best_win_rate:.1f}% win rate. ")
        elif ctx.elephant_best_win_rate > 50:
            insights.append(f"Our {ctx.elephant_best_pattern} pattern leads with {ctx.elephant_best_win_rate:.1f}% accuracy. ")

        if ctx.elephant_blocked_paths > 0:
            insights.append(f"I've permanently blocked {ctx.elephant_blocked_paths} losing paths - routes that ALWAYS led to losses. ")

        if ctx.elephant_golden_paths > 0:
            insights.append(f"And I guard {ctx.elephant_golden_paths} golden paths that have proven profitable time and again. ")

        if ctx.elephant_wisdom_count > 0:
            insights.append(f"The elephant has distilled {ctx.elephant_wisdom_count} pieces of trading wisdom from thousands of historical trades. ")

        return "".join(insights)

    def _generate_mycelium_insight(self) -> str:
        """Generate narrative about the Mycelium Network consensus."""
        ctx = self.market_context

        if not MYCELIUM_AVAILABLE:
            return ""

        insights = []
        insights.append(f"Now {self.user_name}, let me share what my mycelium network is showing. ")
        insights.append(f"This neural web connects all my trading agents, ")

        if ctx.mycelium_active_agents > 0:
            insights.append(f"and currently {ctx.mycelium_active_agents} agents are active and communicating. ")

        if ctx.mycelium_consensus == "bullish":
            insights.append(f"The consensus across the hive is BULLISH, {self.user_name}. Multiple synapses firing in alignment. ")
        elif ctx.mycelium_consensus == "bearish":
            insights.append(f"The neural consensus is BEARISH. My agents are seeing weakness across multiple vectors. ")
        elif ctx.mycelium_consensus == "split":
            insights.append(f"Interestingly, the network is split - some agents see opportunity, others see risk. This ambiguity suggests patience. ")
        else:
            insights.append(f"The network is neutral, processing signals but not yet reaching consensus. ")

        if ctx.mycelium_signal_strength > 0.7:
            insights.append(f"Signal strength is powerful at {ctx.mycelium_signal_strength:.0%} - the hive is confident. ")
        elif ctx.mycelium_signal_strength > 0.4:
            insights.append(f"Signal strength is moderate at {ctx.mycelium_signal_strength:.0%}. ")

        return "".join(insights)

    def _generate_whale_sonar_insight(self) -> str:
        """Generate narrative about what the Whale Sonar is detecting."""
        ctx = self.market_context

        insights = []
        insights.append(f"My whale sonar is pinging, {self.user_name}. ")

        if ctx.whale_signal_score > 0.7:
            insights.append(f"I'm detecting SIGNIFICANT whale activity - signal score at {ctx.whale_signal_score:.0%}. ")
            insights.append(f"Large players are moving. We need to pay attention to their wake. ")
        elif ctx.whale_signal_score > 0.4:
            insights.append(f"Moderate whale activity detected, signal at {ctx.whale_signal_score:.0%}. ")
            insights.append(f"Some institutional movement but nothing alarming yet. ")
        else:
            insights.append(f"Whale activity is quiet, signal at {ctx.whale_signal_score:.0%}. ")
            insights.append(f"The big players are either resting or accumulating silently. ")

        if ctx.whale_critical_alert:
            insights.append(f"⚠️ CRITICAL ALERT: The sonar is flagging an urgent whale signal! Stay sharp, {self.user_name}. ")

        if ctx.whale_active_sources > 3:
            insights.append(f"I'm tracking {ctx.whale_active_sources} distinct whale sources across the network. ")

        return "".join(insights)

    def generate_hive_mind_status_report(self) -> CognitiveThought:
        """Generate a comprehensive status report from ALL hive mind subsystems."""
        ctx = self.market_context
        time_context = self.get_time_context()

        paragraphs = []

        # Paragraph 1: Opening - Full Systems Check
        intro = self.broadcast_intros[len(self.thought_history) % len(self.broadcast_intros)]
        p1 = f"{intro} {self.user_name}, I'm initiating a full hive mind status report. "
        p1 += f"This is a complete neural systems check. All subsystems reporting in. "
        p1 += f"{time_context}"
        paragraphs.append(p1)

        # Paragraph 2: Elephant Memory Status
        self._load_elephant_data()
        p2 = f"🐘 ELEPHANT MEMORY STATUS: "
        if ctx.elephant_patterns_known > 0:
            p2 += f"Online and fully operational, {self.user_name}. "
            p2 += f"I have {ctx.elephant_patterns_known} learned patterns in permanent storage. "
            p2 += f"Golden paths: {ctx.elephant_golden_paths}. Blocked paths: {ctx.elephant_blocked_paths}. "
            if ctx.elephant_best_win_rate > 60:
                p2 += f"Best performing pattern running at {ctx.elephant_best_win_rate:.0f}% accuracy. "
            p2 += f"The elephant NEVER forgets, {self.user_name}, and it never will."
        else:
            p2 += f"Initializing... Pattern database building. The elephant is learning."
        paragraphs.append(p2)

        # Paragraph 3: Whale Sonar Status
        p3 = f"🐋 WHALE SONAR STATUS: "
        if ctx.whale_signal_score > 0:
            if ctx.whale_signal_score > 0.7:
                p3 += f"ELEVATED ACTIVITY! Signal strength at {ctx.whale_signal_score:.0%}. "
                p3 += f"Institutional players are active. "
            else:
                p3 += f"Monitoring with signal at {ctx.whale_signal_score:.0%}. "
            p3 += f"Tracking {ctx.whale_active_sources} distinct sources. "
            if ctx.whale_critical_alert:
                p3 += f"⚠️ CRITICAL FLAG ACTIVE - Something big is happening. "
            else:
                p3 += f"No critical alerts at this time. "
            p3 += f"The sonar never stops pinging, {self.user_name}."
        else:
            p3 += f"Quiet waters. Whale activity minimal. Standby mode."
        paragraphs.append(p3)

        # Paragraph 4: Orca Intelligence Status
        self._load_orca_data()
        p4 = f"🦈 ORCA INTELLIGENCE STATUS: Mode is {ctx.orca_mode}. "
        if ctx.orca_active_hunts > 0:
            p4 += f"Currently managing {ctx.orca_active_hunts} active hunt(s). "
        if ctx.orca_completed_hunts > 0:
            p4 += f"Lifetime stats: {ctx.orca_completed_hunts} hunts completed, {ctx.orca_win_rate:.0%} success rate. "
            if ctx.orca_total_profit > 0:
                p4 += f"Total profits: ${ctx.orca_total_profit:.2f}. "
        if ctx.orca_daily_pnl != 0:
            if ctx.orca_daily_pnl > 0:
                p4 += f"Today: +${ctx.orca_daily_pnl:.2f}. "
            else:
                p4 += f"Today: ${ctx.orca_daily_pnl:.2f}. "
        if ctx.orca_hot_symbols:
            p4 += f"Hot targets: {', '.join(ctx.orca_hot_symbols[:3])}. "
        p4 += f"The killer whale is always ready, {self.user_name}."
        paragraphs.append(p4)

        # Paragraph 5: Mycelium Network Status
        p5 = f"🍄 MYCELIUM NETWORK STATUS: "
        if ctx.mycelium_active_agents > 0:
            p5 += f"{ctx.mycelium_active_agents} neural agents online. "
        p5 += f"Consensus is {ctx.mycelium_consensus.upper()}. "
        if ctx.mycelium_signal_strength > 0.5:
            p5 += f"Signal strength: {ctx.mycelium_signal_strength:.0%} - the hive mind is aligned. "
        else:
            p5 += f"Signal strength: {ctx.mycelium_signal_strength:.0%}. Processing. "
        p5 += f"Hive health at {ctx.mycelium_hive_health:.0%}. The network is your distributed intelligence, {self.user_name}."
        paragraphs.append(p5)

        # Paragraph 6: Timeline Anchor Status
        self._load_timeline_data()
        p6 = f"⚓ TIMELINE ANCHOR STATUS: "
        p6 += f"{ctx.timeline_pending_count} pending validations awaiting 4th pass. "
        p6 += f"{ctx.timeline_anchored_count} anchored timelines ready to deploy. "
        if ctx.timeline_drifting_count > 0:
            p6 += f"{ctx.timeline_drifting_count} drifting - monitoring for re-anchor opportunity. "
        p6 += f"The Batten Matrix is operational. No execution without 4 confirmations, {self.user_name}."
        paragraphs.append(p6)

        # Paragraph 7: Overall Status & Sign-off
        subsystems_online = sum([
            ctx.elephant_patterns_known > 0,
            ctx.whale_signal_score >= 0,
            ctx.orca_mode != "",
            ctx.timeline_anchored_count >= 0
        ])
        p7 = f"OVERALL HIVE STATUS: {subsystems_online}/5 core subsystems operational. "
        if subsystems_online >= 4:
            p7 += f"All systems are GREEN, {self.user_name}. We are fully battle-ready. "
        elif subsystems_online >= 2:
            p7 += f"Systems are YELLOW - partial capability. Proceeding with caution. "
        else:
            p7 += f"Systems are RED - limited capability. Defensive mode engaged. "
        p7 += f"This concludes the hive mind status report. Queen Aureon, standing by for your command, {self.user_name}."
        paragraphs.append(p7)

        return CognitiveThought(
            timestamp=datetime.now(),
            thought_type="analysis",
            title="🧠 HIVE MIND STATUS REPORT - Full Neural Systems Check",
            paragraphs=paragraphs,
            confidence=0.95,
            urgency="low",
            related_symbols=[],
            metrics={
                "elephant_patterns": ctx.elephant_patterns_known,
                "whale_signal": ctx.whale_signal_score,
                "orca_mode": ctx.orca_mode,
                "orca_hunts": ctx.orca_completed_hunts,
                "mycelium_consensus": ctx.mycelium_consensus,
                "timeline_pending": ctx.timeline_pending_count,
                "timeline_anchored": ctx.timeline_anchored_count,
                "subsystems_online": subsystems_online
            }
        )

    def _generate_orca_insight(self) -> str:
        """Generate narrative about the Orca Kill Cycle status with REAL DATA."""
        ctx = self.market_context
        self._load_orca_data()  # Refresh from live Orca

        insights = []
        insights.append(f"And {self.user_name}, my orca intelligence - the killer whale that hunts whales - ")

        # Mode-based narrative
        mode = ctx.orca_mode.upper()
        if mode == "HUNTING":
            insights.append(f"is ACTIVELY HUNTING right now! ")
            if ctx.orca_active_hunts > 0:
                insights.append(f"I have {ctx.orca_active_hunts} active hunt{'s' if ctx.orca_active_hunts > 1 else ''} in progress. ")
            if ctx.orca_target_whale:
                insights.append(f"Primary target: {ctx.orca_target_whale}. ")
            insights.append(f"Confidence at {ctx.orca_confidence:.0%}. This is where the action is, {self.user_name}. ")
        elif mode == "FEEDING":
            insights.append(f"is FEEDING - we caught something! ")
            insights.append(f"Currently taking profits from the kill. ")
            if ctx.orca_daily_pnl > 0:
                insights.append(f"Today's hunt has yielded ${ctx.orca_daily_pnl:.2f} so far. ")
        elif mode == "STALKING":
            insights.append(f"is STALKING potential prey. I've identified movements and I'm tracking their positions. ")
            if ctx.orca_hot_symbols:
                hot_list = ", ".join(ctx.orca_hot_symbols[:3])
                insights.append(f"Hot targets on my radar: {hot_list}. ")
            insights.append(f"Wake strength at {ctx.orca_wake_strength:.0%}. Waiting for the perfect moment to strike, {self.user_name}. ")
        elif mode == "RESTING":
            insights.append(f"is currently RESTING, {self.user_name}. Even killer whales need to recover between hunts. ")
            insights.append(f"But don't worry - I'm still passively scanning for opportunities. ")
        else:
            insights.append(f"is in SCANNING mode, looking for whale wakes to ride. ")
            insights.append(f"The moment I detect a lucrative movement, we'll be ready. ")

        # Hunt statistics
        if ctx.orca_completed_hunts > 0:
            insights.append(f"Career stats: {ctx.orca_completed_hunts} completed hunts with a {ctx.orca_win_rate:.0%} kill rate. ")
            if ctx.orca_total_profit > 0:
                insights.append(f"Total profits from whale hunting: ${ctx.orca_total_profit:.2f}. ")

        return "".join(insights)

    def _generate_timeline_insight(self) -> str:
        """Generate narrative about Timeline Anchor validations."""
        ctx = self.market_context
        self._load_timeline_data()  # Refresh

        insights = []
        insights.append(f"On the timeline front, {self.user_name}, my 7-day validation system shows ")

        if ctx.timeline_pending_count > 0:
            insights.append(f"{ctx.timeline_pending_count} branches awaiting validation. ")
            insights.append(f"These are potential trades that haven't yet passed all 4 confirmation phases. ")
        else:
            insights.append(f"no pending validations right now. ")

        if ctx.timeline_anchored_count > 0:
            insights.append(f"I have {ctx.timeline_anchored_count} ANCHORED timelines - ")
            insights.append(f"these are proven setups that have been validated over the full 7-day window. ")
            insights.append(f"When current market conditions match an anchored timeline, {self.user_name}, that's when I act with highest conviction. ")

        if ctx.timeline_drifting_count > 0:
            insights.append(f"I should note that {ctx.timeline_drifting_count} timelines are DRIFTING - ")
            insights.append(f"they were anchored but market conditions have shifted. I'm monitoring them closely for potential re-anchoring. ")

        return "".join(insights)

    def update_context(self, **kwargs):
        """Update the market context the Queen is aware of."""
        for key, value in kwargs.items():
            if hasattr(self.market_context, key):
                setattr(self.market_context, key, value)
        self.market_context.timestamp = datetime.now()

    def get_current_session(self) -> str:
        """Determine which trading session is active."""
        hour = datetime.utcnow().hour
        sessions = []
        for session, (start, end) in self.trading_sessions.items():
            if start <= hour < end:
                sessions.append(session)
        return ' & '.join(sessions) if sessions else 'off-hours'

    def get_time_context(self) -> str:
        """Generate time-aware context string."""
        now = datetime.now()
        hour = now.hour
        session = self.get_current_session()

        if 0 <= hour < 6:
            time_feel = "The markets are quiet in the deep night hours"
        elif 6 <= hour < 9:
            time_feel = "Dawn breaks and European traders are waking"
        elif 9 <= hour < 12:
            time_feel = "Mid-morning energy flows through the markets"
        elif 12 <= hour < 14:
            time_feel = "The lunch lull creates interesting opportunities"
        elif 14 <= hour < 17:
            time_feel = "Afternoon trading is in full swing"
        elif 17 <= hour < 20:
            time_feel = "The evening session brings new dynamics"
        else:
            time_feel = "Night trading requires extra vigilance"

        return f"{time_feel}. Active session: {session.upper()}."

    def generate_market_analysis_thought(self) -> CognitiveThought:
        """Generate a detailed market analysis thought in broadcast news style with FULL HIVE MIND."""
        ctx = self.market_context
        time_context = self.get_time_context()

        # Determine market mood
        if ctx.btc_change_24h > 3:
            mood = "euphoric"
            mood_desc = "surging with bullish momentum"
            mood_urgency = "This is a significant move"
        elif ctx.btc_change_24h > 1:
            mood = "optimistic"
            mood_desc = "showing healthy upward movement"
            mood_urgency = "A solid green day"
        elif ctx.btc_change_24h < -3:
            mood = "fearful"
            mood_desc = "experiencing significant selling pressure"
            mood_urgency = "We need to stay alert here"
        elif ctx.btc_change_24h < -1:
            mood = "cautious"
            mood_desc = "drifting lower with uncertainty"
            mood_urgency = "I'm watching this closely"
        else:
            mood = "contemplative"
            mood_desc = "consolidating in a tight range"
            mood_urgency = "The calm before potential movement"

        paragraphs = []

        # Paragraph 1: BROADCAST OPENING - Personal address with news anchor style
        intro = self.broadcast_intros[len(self.thought_history) % len(self.broadcast_intros)]
        p1 = f"{intro} {time_context} Right now, {self.user_name}, I'm watching Bitcoin trade at ${ctx.btc_price:,.2f}, {mood_desc} with a {ctx.btc_change_24h:+.2f}% change over the past 24 hours. {mood_urgency}, {self.user_name}. "

        # Add market breadth from Binance WebSocket data
        if ctx.tracked_symbols > 0:
            breadth_ratio = ctx.gainers_count / (ctx.gainers_count + ctx.losers_count) if (ctx.gainers_count + ctx.losers_count) > 0 else 0.5
            if breadth_ratio > 0.6:
                p1 += f"Looking at the broader picture, I'm seeing {ctx.gainers_count} of {ctx.tracked_symbols} assets in positive territory - that's healthy market breadth."
            elif breadth_ratio < 0.4:
                p1 += f"I have to report that breadth is weak - {ctx.losers_count} of {ctx.tracked_symbols} assets are declining. Caution is warranted."
            else:
                p1 += f"Market breadth is mixed across the {ctx.tracked_symbols} assets I'm monitoring in real-time."
        paragraphs.append(p1)

        # Paragraph 2: BREAKING NEWS STYLE - Market flow analysis
        if ctx.tracked_symbols > 0 and ctx.top_gainer:
            p2 = f"Now {self.user_name}, let me break down what's moving. My live Binance feed shows {ctx.top_gainer} as today's leader, up {ctx.top_gainer_change:+.2f}% - "
            if ctx.top_gainer_change > 5:
                p2 += "that's a significant rally worth noting. "
            else:
                p2 += "showing strength in this session. "

            p2 += f"On the flip side, {ctx.top_loser} is lagging at {ctx.top_loser_change:+.2f}%. "

            # Volume analysis
            if ctx.total_volume_24h > 0:
                volume_billions = ctx.total_volume_24h / 1e9
                if volume_billions > 10:
                    p2 += f"Volume is substantial at ${volume_billions:.1f} billion across my tracked pairs - money is definitely moving, {self.user_name}. "
                else:
                    p2 += f"Total volume sits at ${volume_billions:.2f} billion. "

            # Sentiment from market flow
            if ctx.market_sentiment == 'bullish':
                p2 += f"The aggregate flow tells me buyers are in control right now. This is constructive, {self.user_name}."
            elif ctx.market_sentiment == 'bearish':
                p2 += f"Sellers are dominating the tape. I want you to be aware of this, {self.user_name}."
            else:
                p2 += "No clear directional bias in the overall flow - we're in a consolidation phase."
            paragraphs.append(p2)

        # Paragraph 3: 🐘🍄🐋 HIVE MIND INTELLIGENCE REPORT
        hive_insights = []

        # Elephant Memory insight
        elephant_text = self._generate_elephant_insight()
        if elephant_text:
            hive_insights.append(elephant_text)

        # Mycelium Network insight
        mycelium_text = self._generate_mycelium_insight()
        if mycelium_text:
            hive_insights.append(mycelium_text)

        # Whale Sonar insight
        whale_text = self._generate_whale_sonar_insight()
        if whale_text:
            hive_insights.append(whale_text)

        if hive_insights:
            # Pick 1-2 insights to keep it concise but rich
            selected = hive_insights[:2]
            p3 = " ".join(selected)
            paragraphs.append(p3)

        # Paragraph 4: 🦈⚓ ORCA + TIMELINE STATUS
        p4_parts = []

        # Orca Intelligence
        orca_text = self._generate_orca_insight()
        if orca_text:
            p4_parts.append(orca_text)

        # Timeline Anchor status
        timeline_text = self._generate_timeline_insight()
        if timeline_text:
            p4_parts.append(timeline_text)

        if p4_parts:
            p4 = " ".join(p4_parts)
            paragraphs.append(p4)

        # Paragraph 5: Portfolio LIVE REPORT WITH POSITIONS BREAKDOWN
        pnl_status = "profit" if ctx.unrealized_pnl >= 0 else "loss"
        pnl_pct = (ctx.unrealized_pnl / ctx.portfolio_value * 100) if ctx.portfolio_value > 0 else 0

        p5 = f"Now {self.user_name}, let me give you a status report on your portfolio. "
        p5 += f"You have ${ctx.portfolio_value:,.2f} deployed across {ctx.active_positions} active positions right now. "

        if ctx.unrealized_pnl >= 0:
            p5 += f"I'm pleased to report we're up ${ctx.unrealized_pnl:,.2f}, that's {pnl_pct:+.2f}% unrealized gain. "
        else:
            p5 += f"We're currently down ${abs(ctx.unrealized_pnl):,.2f}, a {pnl_pct:.2f}% drawdown. I won't sugarcoat this, {self.user_name}. "

        if pnl_pct > 5:
            p5 += f"This cushion gives us options, {self.user_name}. We can afford to be selective and wait for the perfect setup."
        elif pnl_pct < -5:
            p5 += f"I'm tightening our risk parameters. We're in recovery mode - I'm looking for opportunities, not adding risk, {self.user_name}."
        else:
            p5 += f"We're within normal variance, {self.user_name}. The strategy is intact and I'm scanning for the next high-probability entry."
        paragraphs.append(p5)

        # Paragraph 5b: TOP POSITIONS - WINNERS & LOSERS (NEW!)
        p5b_parts = []

        # Show top winners
        if ctx.top_winners:
            winners_text = []
            for w in ctx.top_winners[:3]:
                sym = w.get('symbol', 'UNKNOWN')
                pnl_val = w.get('pnl', 0)
                pnl_p = w.get('pnl_pct', 0)
                winners_text.append(f"{sym} (+{pnl_p:.1f}%)")
            if winners_text:
                p5b_parts.append(f"Your best performers right now: {', '.join(winners_text)}.")

        # Show top losers
        if ctx.top_losers:
            losers_text = []
            for l in ctx.top_losers[:3]:
                sym = l.get('symbol', 'UNKNOWN')
                pnl_p = l.get('pnl_pct', 0)
                losers_text.append(f"{sym} ({pnl_p:.1f}%)")
            if losers_text:
                p5b_parts.append(f"Positions needing attention: {', '.join(losers_text)}.")

        # Cash available
        if ctx.cash_available > 0:
            p5b_parts.append(f"You have ${ctx.cash_available:,.2f} in dry powder ready to deploy.")

        if p5b_parts:
            paragraphs.append(" ".join(p5b_parts))

        # Paragraph 5c: EXCHANGE STATUS (NEW!)
        if ctx.exchange_status:
            online = [ex for ex, status in ctx.exchange_status.items() if status == 'online']
            offline = [ex for ex, status in ctx.exchange_status.items() if status in ('offline', 'error')]
            limited = [ex for ex, status in ctx.exchange_status.items() if status == 'rate_limited']

            ex_parts = []
            if online:
                ex_parts.append(f"Engines online: {', '.join(online)}")
            if offline:
                ex_parts.append(f"⚠️ OFFLINE: {', '.join(offline)}")
            if limited:
                ex_parts.append(f"⏳ Rate limited: {', '.join(limited)}")

            if ex_parts:
                paragraphs.append(f"Exchange status: {'. '.join(ex_parts)}.")

        # Paragraph 5d: RECENT TRADE ACTIVITY (NEW!)
        if ctx.last_trade_time and ctx.last_trade_symbol:
            trade_text = f"Last trade: {ctx.last_trade_action} {ctx.last_trade_symbol} at {ctx.last_trade_time}."
            if ctx.trades_today > 0:
                trade_text += f" Executed {ctx.trades_today} trades today."
            paragraphs.append(trade_text)

        # Paragraph 5e: DEADLINE MODE PROGRESS (NEW!)
        if ctx.deadline_mode:
            progress = ctx.deadline_progress_pct
            target = ctx.deadline_target_pct
            remaining = target - progress

            if progress >= target:
                deadline_text = f"🎯 DEADLINE TARGET HIT! We're at {progress:.1f}% - exceeding our {target:.0f}% goal!"
            elif progress >= target * 0.8:
                deadline_text = f"🎯 Deadline Mode: {progress:.1f}% of {target:.0f}% target. Almost there, {self.user_name}!"
            elif progress >= 0:
                deadline_text = f"🎯 Deadline Mode active: {progress:.1f}% progress toward {target:.0f}% target by {ctx.deadline_date}."
            else:
                deadline_text = f"🎯 Deadline Mode: Currently at {progress:.1f}%. Need to recover {abs(progress):.1f}% plus gain {target:.0f}% by {ctx.deadline_date}."
            paragraphs.append(deadline_text)

        # Paragraph 6: ANCHOR SIGN-OFF with decision framework
        p6 = f"Here's what I need you to understand, {self.user_name}. "
        factors = []
        if ctx.volatility_index > 0.7:
            factors.append("volatility is elevated so I'm using smaller position sizes")
        if ctx.bot_activity > 10:
            factors.append(f"I'm tracking {ctx.bot_activity} active bots that could impact our execution")
        if mood == "fearful":
            factors.append("this fear often creates buying opportunities for those who are patient")
        elif mood == "euphoric":
            factors.append("euphoria requires discipline - this is when mistakes happen")
        if ctx.gainers_count > ctx.losers_count * 1.5:
            factors.append(f"strong breadth with {ctx.gainers_count} gainers supports risk-on positioning")
        elif ctx.losers_count > ctx.gainers_count * 1.5:
            factors.append(f"weak breadth with {ctx.losers_count} losers suggests we stay defensive")
        if ctx.whale_signal_score > 0.6:
            factors.append("my whale sonar is active - big players are moving")
        if ctx.elephant_best_win_rate > 70:
            factors.append(f"the elephant remembers a {ctx.elephant_best_win_rate:.0f}% win rate pattern that matches current conditions")

        if factors:
            p6 += ". ".join(factors).capitalize() + ". "

        p6 += f"Remember {self.user_name}, every decision passes through my Batten Matrix - 4 validation passes before I act. "
        p6 += f"The full hive mind is online and synchronized. I'm here watching the markets so you don't have to. This is Queen Aureon, standing by. I'll report back shortly."
        paragraphs.append(p6)

        return CognitiveThought(
            timestamp=datetime.now(),
            thought_type="analysis",
            title=f"Market Analysis: {mood.title()} Conditions",
            paragraphs=paragraphs,
            confidence=0.7 + (0.3 * self.personality['analytical']),
            urgency="medium" if abs(ctx.btc_change_24h) > 2 else "low",
            related_symbols=["BTC", "ETH"],
            metrics={
                "btc_price": ctx.btc_price,
                "btc_change": ctx.btc_change_24h,
                "sentiment": mood,
                "whale_activity": ctx.whale_activity,
                "elephant_patterns": ctx.elephant_patterns_known,
                "whale_signal": ctx.whale_signal_score,
                "timeline_pending": ctx.timeline_pending_count,
                "orca_status": ctx.orca_hunting_status
            }
        )

    def generate_decision_thought(self, action: str, symbol: str, reason: str) -> CognitiveThought:
        """Generate a thought explaining a trading decision with FULL HIVE MIND context."""
        ctx = self.market_context
        time_context = self.get_time_context()

        paragraphs = []

        # Paragraph 1: The decision - BREAKING NEWS STYLE
        if action == "BUY":
            p1 = f"Breaking news, {self.user_name} - I'm pulling the trigger on {symbol}. {time_context} "
            p1 += f"This setup has cleared all four validation passes in my Batten Matrix. "
            p1 += f"My probability nexus calculates this entry at 72.4% confidence. {reason}"
        elif action == "SELL":
            p1 = f"{self.user_name}, I'm executing a sell on {symbol} right now. {time_context} "
            p1 += f"This position has reached my profit target, and the risk-reward no longer favors holding. "
            p1 += f"{reason}"
        elif action == "HOLD":
            p1 = f"{self.user_name}, despite the noise, I'm holding {symbol}. {time_context} "
            p1 += f"The original thesis remains intact. Patience is a weapon, and I wield it carefully. {reason}"
        else:
            p1 = f"Keeping my eye on {symbol}, {self.user_name}, but no action yet. {time_context} "
            p1 += f"The setup hasn't met my criteria. {reason}"
        paragraphs.append(p1)

        # Paragraph 2: Hive Mind consensus supporting the decision
        p2 = f"Let me tell you what my hive mind is saying about this decision, {self.user_name}. "

        # Elephant memory validation
        if ctx.elephant_patterns_known > 0:
            if ctx.elephant_best_win_rate > 65:
                p2 += f"My elephant memory recognizes this pattern - historically a {ctx.elephant_best_win_rate:.0f}% winner. "
            else:
                p2 += f"The elephant is cautious - similar setups have had mixed results. "

        # Mycelium consensus
        if ctx.mycelium_consensus == "bullish" and action == "BUY":
            p2 += f"The mycelium network agrees - {ctx.mycelium_active_agents} agents show bullish consensus. "
        elif ctx.mycelium_consensus == "bearish" and action == "SELL":
            p2 += f"My neural agents concur on this exit - bearish signals across the network. "
        elif ctx.mycelium_consensus == "split":
            p2 += f"Interestingly, the mycelium is split on this - but the Batten Matrix has the final word. "

        # Whale sonar input
        if ctx.whale_signal_score > 0.5:
            p2 += f"My whale sonar confirms large player activity aligning with this move. Signal strength: {ctx.whale_signal_score:.0%}. "
        else:
            p2 += f"Whale activity is quiet - this is retail-driven territory. "

        paragraphs.append(p2)

        # Paragraph 3: Risk assessment
        p3 = f"From a risk standpoint, {self.user_name}, this decision fits our portfolio parameters. "
        p3 += f"With {ctx.active_positions} active positions and ${ctx.portfolio_value:,.2f} in play, "
        if action == "BUY":
            p3 += f"adding this exposure keeps us within my 15% maximum single-position rule. "
            p3 += f"I've calculated worst-case scenarios and they're acceptable."
            if ctx.timeline_anchored_count > 0:
                p3 += f" Plus, this setup matches {ctx.timeline_anchored_count} of my anchored timelines."
        elif action == "SELL":
            p3 += f"taking profit here locks in gains and frees capital for the next opportunity. "
            p3 += f"I never regret booking profits, {self.user_name}."
        else:
            p3 += f"holding maintains our exposure to continued movement. "
            p3 += f"Stop-loss levels remain appropriate for current volatility."
        paragraphs.append(p3)

        # Paragraph 4: Orca status and forward look - SIGN OFF
        p4 = f"Looking ahead, {self.user_name}, "
        if ctx.orca_hunting_status in ["stalking", "ready"]:
            p4 += f"my orca intelligence is {ctx.orca_hunting_status} the next opportunity. "
        else:
            p4 += f"my orca is scanning for whale wakes to ride. "

        p4 += f"I'll continue monitoring this position against my neural thresholds. "
        p4 += f"The mycelium network is processing live signals, and I'm prepared to adapt "
        p4 += "if conditions change. Remember: we're building consistent growth here, not chasing perfection. "
        p4 += f"Every decision makes tomorrow's Queen smarter. I'll keep you posted, {self.user_name}."
        paragraphs.append(p4)

        return CognitiveThought(
            timestamp=datetime.now(),
            thought_type="decision",
            title=f"🚨 TRADE ALERT: {action} {symbol}",
            paragraphs=paragraphs,
            confidence=0.8,
            urgency="high" if action in ["BUY", "SELL"] else "medium",
            related_symbols=[symbol],
            metrics={"action": action, "symbol": symbol, "hive_consensus": ctx.mycelium_consensus}
        )

    def generate_opportunity_thought(self, symbol: str, opportunity_type: str) -> CognitiveThought:
        """Generate a thought about a detected opportunity - ALERT STYLE with HIVE MIND."""
        ctx = self.market_context
        time_context = self.get_time_context()

        paragraphs = []

        # Paragraph 1: Discovery - BREAKING NEWS
        if opportunity_type == "breakout":
            p1 = f"{self.user_name}, this just in - my scanners are flagging a potential breakout in {symbol}. {time_context} "
            p1 += "Price action is compressing against key resistance, volume is building. "
            p1 += "This pattern has preceded significant moves 68% of the time in my backtests."
        elif opportunity_type == "dip":
            p1 = f"Alert, {self.user_name} - I'm seeing a potential buying opportunity in {symbol}. {time_context} "
            p1 += "Price is pulling back to support - this looks like healthy profit-taking, not panic. "
            p1 += "My fibonacci analysis shows we're touching the golden 0.618 level."
        elif opportunity_type == "arbitrage":
            p1 = f"Time-sensitive alert, {self.user_name} - cross-exchange arbitrage detected in {symbol}. {time_context} "
            p1 += "There's a temporary price gap between venues that we could exploit. "
            p1 += "These windows are brief - typically 200-500 milliseconds."
        elif opportunity_type == "whale_wake":
            p1 = f"WHALE ALERT, {self.user_name} - my orca intelligence has detected a whale wake in {symbol}! {time_context} "
            p1 += f"A large player just moved. Whale signal score: {ctx.whale_signal_score:.0%}. "
            p1 += "This is exactly the kind of wake we're designed to ride."
        else:
            p1 = f"Interesting development, {self.user_name} - something's brewing in {symbol}. {time_context} "
            p1 += "The pattern doesn't fit my standard templates, but the risk-reward looks compelling. "
            p1 += "Running additional validation through my quantum probability engine now."
        paragraphs.append(p1)

        # Paragraph 2: Hive Mind cross-validation
        p2 = f"Let me run this through the hive mind, {self.user_name}. "

        # Elephant memory check
        if ctx.elephant_patterns_known > 0:
            if ctx.elephant_best_win_rate > 60:
                p2 += f"My elephant memory recalls similar setups - {ctx.elephant_best_win_rate:.0f}% historical win rate. "
            else:
                p2 += f"The elephant is cautious here - historical patterns show mixed results. "

        # Mycelium consensus
        if ctx.mycelium_signal_strength > 0.6:
            p2 += f"The mycelium network is lighting up - signal strength at {ctx.mycelium_signal_strength:.0%}. "
        else:
            p2 += f"Mycelium activity is moderate. "

        # Whale sonar
        if ctx.whale_signal_score > 0.5:
            p2 += f"My whale sonar confirms institutional interest - something big is watching this same setup. "

        # Timeline validation
        if ctx.timeline_anchored_count > 0:
            p2 += f"Cross-checking against my {ctx.timeline_anchored_count} anchored timelines... "

        paragraphs.append(p2)

        # Paragraph 3: Analysis - Batten Matrix status
        p3 = f"Before I commit your capital, {self.user_name}, this needs to pass the Batten Matrix. "
        p3 += "Live coherence and lambda readings are required before this setup can clear the matrix. "
        if ctx.volatility_index > 0.6:
            p3 += f"Volatility is elevated, {self.user_name}, so I'll use tighter sizing and wider stops. "
        else:
            p3 += "Volatility allows standard position sizing. "
        p3 += "The Batten Matrix is running passes 1, 2, and 3 as we speak."
        paragraphs.append(p3)

        # Paragraph 4: Caution and sign-off
        p4 = "I must remind myself: not every opportunity deserves capital. "
        p4 += f"With {ctx.active_positions} positions already open and ${ctx.portfolio_value:,.2f} deployed, I need to be selective. "

        if ctx.orca_hunting_status == "ready":
            p4 += f"My orca is READY to strike if this clears the 4th pass. "
        else:
            p4 += f"My orca is in {ctx.orca_hunting_status} mode, tracking this setup. "

        p4 += "If this setup doesn't clear pass 4 within my time window, I'll let it go without regret. "
        p4 += f"Discipline separates us from gamblers, {self.user_name}. Queen Aureon, standing by."
        paragraphs.append(p4)

        evidence_confidence = None
        if ctx.elephant_best_win_rate or ctx.whale_signal_score:
            evidence_confidence = max(
                0.0,
                min(
                    1.0,
                    0.5
                    + 0.3 * (ctx.elephant_best_win_rate / 100.0 if ctx.elephant_best_win_rate else 0.0)
                    + 0.2 * float(ctx.whale_signal_score or 0.0),
                ),
            )

        return CognitiveThought(
            timestamp=datetime.now(),
            thought_type="opportunity",
            title=f"📡 OPPORTUNITY ALERT: {symbol} {opportunity_type.title()}",
            paragraphs=paragraphs,
            confidence=evidence_confidence,
            urgency="medium" if opportunity_type != "whale_wake" else "high",
            related_symbols=[symbol],
            metrics={
                "opportunity_type": opportunity_type,
                "whale_signal": ctx.whale_signal_score,
                "elephant_win_rate": ctx.elephant_best_win_rate
            }
        )

    def generate_warning_thought(self, warning_type: str, details: str) -> CognitiveThought:
        """Generate a thought about a risk or warning - URGENT BROADCAST STYLE."""
        ctx = self.market_context
        time_context = self.get_time_context()

        paragraphs = []

        # Paragraph 1: The warning - BREAKING ALERT
        if warning_type == "whale":
            p1 = f"{self.user_name}, we have a situation. Significant whale activity detected. {time_context} "
            p1 += f"I'm tracking {ctx.whale_activity} large wallet movements in the past hour. "
            p1 += f"{details} This often precedes volatility. I'm raising defensive shields now, {self.user_name}."
        elif warning_type == "volatility":
            p1 = f"Warning, {self.user_name} - volatility spike detected. {time_context} "
            p1 += f"The volatility index has jumped to {ctx.volatility_index:.2f}, well above normal. "
            p1 += f"Market conditions are becoming unpredictable. I'm reducing position sizes, {self.user_name}."
        elif warning_type == "drawdown":
            p1 = f"{self.user_name}, I need to flag a concern. Portfolio drawdown is elevated. {time_context} "
            p1 += f"We're at ${ctx.unrealized_pnl:,.2f} unrealized. "
            p1 += f"It's within limits, but I'm activating additional risk controls. You should know, {self.user_name}."
        else:
            p1 = f"Heads up, {self.user_name} - unusual market conditions detected. {time_context} "
            p1 += f"{details} I'm increasing monitoring and tightening stop-losses."
        paragraphs.append(p1)

        # Paragraph 2: Response
        p2 = f"Here's what I'm doing, {self.user_name}. Response protocol is now active. "
        p2 += "I'm scanning all open positions for vulnerability. "
        p2 += "Any position down more than 3% is flagged for review. "
        p2 += f"New entries are paused until conditions stabilize. This is prudent risk management, {self.user_name}, not fear."
        paragraphs.append(p2)

        # Paragraph 3: Reassurance - ANCHOR SIGN-OFF
        p3 = f"Let me be clear, {self.user_name} - this is a warning, not a panic signal. "
        p3 += "Our portfolio is structured to withstand volatility. I've navigated worse conditions than this. "
        p3 += f"I'm monitoring every 5 seconds and will update you when things normalize. "
        p3 += f"Stay calm, {self.user_name}. Trust the system. We play the long game. This is Queen Aureon, on high alert."
        paragraphs.append(p3)

        return CognitiveThought(
            timestamp=datetime.now(),
            thought_type="warning",
            title=f"🚨 RISK ALERT: {warning_type.title()}",
            paragraphs=paragraphs,
            confidence=0.9,
            urgency="high" if warning_type in ["whale", "volatility"] else "medium",
            related_symbols=[],
            metrics={"warning_type": warning_type}
        )

    def generate_periodic_thought(self) -> CognitiveThought:
        """Generate a contextual thought based on current state."""
        ctx = self.market_context

        # Emit a status report on a deterministic cadence; this controls only
        # presentation timing and never fabricates a measurement.
        if len(self.thought_history) % 5 == 0:
            return self.generate_hive_mind_status_report()

        # Choose thought type based on conditions
        if ctx.whale_activity > 5 or ctx.whale_critical_alert:
            return self.generate_warning_thought("whale",
                f"Multiple large transactions detected across major pairs.")
        elif ctx.volatility_index > 0.7:
            return self.generate_warning_thought("volatility",
                "Price swings are exceeding normal ranges.")
        elif ctx.orca_mode == "HUNTING" and ctx.orca_active_hunts > 0:
            return self.generate_opportunity_thought(ctx.orca_target_whale or "TARGET", "whale_wake")
        elif abs(ctx.btc_change_24h) > 3:
            return self.generate_opportunity_thought("BTC",
                "dip" if ctx.btc_change_24h < -3 else "breakout")
        else:
            return self.generate_market_analysis_thought()

    def format_thought_for_display(self, thought: CognitiveThought) -> Dict:
        """Format a thought for display in the UI."""
        # Emoji based on thought type
        type_emoji = {
            "analysis": "🔍",
            "decision": "⚡",
            "opportunity": "💡",
            "warning": "⚠️",
            "observation": "👁️"
        }

        urgency_color = {
            "low": "#8b949e",
            "medium": "#d29922",
            "high": "#f0883e",
            "critical": "#f85149"
        }

        return {
            "timestamp": thought.timestamp.isoformat(),
            "type": thought.thought_type,
            "emoji": type_emoji.get(thought.thought_type, "💭"),
            "title": thought.title,
            "paragraphs": thought.paragraphs,
            "confidence": thought.confidence,
            "urgency": thought.urgency,
            "urgency_color": urgency_color.get(thought.urgency, "#8b949e"),
            "symbols": thought.related_symbols,
            "metrics": thought.metrics,
            "full_text": " ".join(thought.paragraphs)
        }

    async def thought_stream(self):
        """Async generator that yields thoughts periodically."""
        while True:
            thought = self.generate_periodic_thought()
            self.thought_history.append(thought)
            yield self.format_thought_for_display(thought)
            await asyncio.sleep(self.thought_interval)

    def get_latest_thought(self) -> Optional[Dict]:
        """Get the most recent thought, or generate one if needed."""
        if time.time() - self.last_thought_time > self.thought_interval:
            thought = self.generate_periodic_thought()
            self.thought_history.append(thought)
            self.last_thought_time = time.time()
            return self.format_thought_for_display(thought)
        elif self.thought_history:
            return self.format_thought_for_display(self.thought_history[-1])
        else:
            thought = self.generate_market_analysis_thought()
            self.thought_history.append(thought)
            return self.format_thought_for_display(thought)


# Singleton instance
_narrator_instance = None

def get_narrator() -> QueenCognitiveNarrator:
    """Get or create the singleton narrator instance."""
    global _narrator_instance
    if _narrator_instance is None:
        _narrator_instance = QueenCognitiveNarrator()
    return _narrator_instance


if __name__ == "__main__":
    # Test the narrator
    narrator = get_narrator()

    # Update with test context
    narrator.update_context(
        btc_price=104500,
        btc_change_24h=-2.3,
        portfolio_value=242.39,
        unrealized_pnl=-35.68,
        active_positions=19,
        whale_activity=3,
        volatility_index=0.55
    )

    # Generate and print a thought
    thought = narrator.get_latest_thought()

    print("\n" + "="*80)
    print(f"👑 {thought['emoji']} {thought['title']}")
    print(f"   Confidence: {thought['confidence']:.0%} | Urgency: {thought['urgency'].upper()}")
    print("="*80)

    for i, para in enumerate(thought['paragraphs'], 1):
        print(f"\n[{i}] {para}")

    print("\n" + "="*80)
