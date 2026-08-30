#!/usr/bin/env python3
"""
👑 AUREON QUEEN WEB DASHBOARD 👑
Real-time web interface for bot intelligence tracking
Runs on localhost with live WebSocket feeds
WITH TEXT-TO-SPEECH VOICE ENGINE + OPEN SOURCE DATA
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import time
import json
import random
import subprocess
import logging
from datetime import datetime
from collections import defaultdict, deque
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# QUEEN VOICE ENGINE - TEXT TO SPEECH
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.queen.queen_voice_engine import QueenVoiceEngine, queen_voice
    VOICE_ENGINE_AVAILABLE = True
    print("🔊 Queen Voice Engine LOADED - She can speak now!")
except ImportError:
    VOICE_ENGINE_AVAILABLE = False
    queen_voice = None
    print("⚠️ Voice engine not available - Queen will be silent")

# ═══════════════════════════════════════════════════════════════════════════════
# OPEN SOURCE DATA ENGINE - FREE DATA FEEDS
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.queen.queen_open_source_data_engine import OpenSourceDataEngine, get_data_engine
    OPEN_DATA_AVAILABLE = True
    print("🌐 Open Source Data Engine LOADED - Free data incoming!")
except ImportError:
    OPEN_DATA_AVAILABLE = False
    print("⚠️ Open source data engine not available")

try:
    from aureon.queen.queen_auto_tagger import QueenAutoTagger, get_auto_tagger
    AUTO_TAGGER_AVAILABLE = True
    print("🏷️ Auto-Tagger LOADED - Intelligent bot classification!")
except ImportError:
    AUTO_TAGGER_AVAILABLE = False
    print("⚠️ Auto-tagger not available")

try:
    from aureon.queen.queen_firm_geocoder import get_firm_coordinates, get_all_firm_locations, get_regional_summary
    GEOCODER_AVAILABLE = True
    print("🌍 Firm Geocoder LOADED - World map ready!")
except ImportError:
    GEOCODER_AVAILABLE = False
    print("⚠️ Geocoder not available")

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORT ALL AVAILABLE INTELLIGENCE SYSTEMS (25 TOTAL)
# ═══════════════════════════════════════════════════════════════════════════════
SYSTEMS_STATUS = {}

# Core Intelligence Layer
try:
    from aureon.bots_intelligence.aureon_bot_intelligence_profiler import BotIntelligenceProfiler, TRADING_FIRM_SIGNATURES
    SYSTEMS_STATUS['Bot Intelligence'] = True
except ImportError:
    SYSTEMS_STATUS['Bot Intelligence'] = False
    TRADING_FIRM_SIGNATURES = {}

# Communication & Consciousness Layer
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought
    SYSTEMS_STATUS['Thought Bus'] = True
except ImportError:
    SYSTEMS_STATUS['Thought Bus'] = False
    ThoughtBus = None

try:
    from aureon.core.aureon_mycelium import MyceliumNetwork
    SYSTEMS_STATUS['Mycelium Network'] = True
except ImportError:
    SYSTEMS_STATUS['Mycelium Network'] = False

# Signal Processing Layer
try:
    from aureon.wisdom.aureon_enigma import AureonEnigma
    SYSTEMS_STATUS['Enigma Decoder'] = True
except ImportError:
    SYSTEMS_STATUS['Enigma Decoder'] = False

# Analysis & Prediction Layer
try:
    from aureon.simulation.aureon_quantum_telescope import QuantumPrism
    SYSTEMS_STATUS['Quantum Telescope'] = True
except ImportError:
    SYSTEMS_STATUS['Quantum Telescope'] = False

try:
    from aureon.intelligence.aureon_elephant_learning import ElephantMemory
    SYSTEMS_STATUS['Elephant Memory'] = True
except ImportError:
    SYSTEMS_STATUS['Elephant Memory'] = False

try:
    from aureon.bridges.aureon_probability_nexus import AureonProbabilityNexus
    SYSTEMS_STATUS['Probability Nexus'] = True
except ImportError:
    SYSTEMS_STATUS['Probability Nexus'] = False

try:
    from aureon.strategies.probability_ultimate_intelligence import ProbabilityUltimateIntelligence
    SYSTEMS_STATUS['Ultimate Intelligence'] = True
except ImportError:
    SYSTEMS_STATUS['Ultimate Intelligence'] = False

# Timeline & Quantum Layer
try:
    from aureon.intelligence.aureon_timeline_oracle import TimelineOracle
    SYSTEMS_STATUS['Timeline Oracle'] = True
except ImportError:
    SYSTEMS_STATUS['Timeline Oracle'] = False

try:
    from aureon.scanners.aureon_quantum_mirror_scanner import QuantumMirrorScanner
    SYSTEMS_STATUS['Quantum Mirror'] = True
except ImportError:
    SYSTEMS_STATUS['Quantum Mirror'] = False

try:
    from aureon.intelligence.aureon_timeline_anchor_validator import TimelineAnchorValidator
    SYSTEMS_STATUS['Timeline Anchor'] = True
except ImportError:
    SYSTEMS_STATUS['Timeline Anchor'] = False

try:
    from aureon.wisdom.aureon_stargate_protocol import ActivationCeremony
    SYSTEMS_STATUS['Stargate Protocol'] = True
except ImportError:
    SYSTEMS_STATUS['Stargate Protocol'] = False

# Tracking & Surveillance Layer
try:
    from aureon.analytics.aureon_whale_onchain_tracker import WhaleExchangeTracker
    SYSTEMS_STATUS['Whale Onchain Tracker'] = True
except ImportError:
    SYSTEMS_STATUS['Whale Onchain Tracker'] = False

try:
    from aureon.scanners.aureon_strategic_warfare_scanner import StrategicWarfareScanner
    SYSTEMS_STATUS['Strategic Warfare'] = True
except ImportError:
    SYSTEMS_STATUS['Strategic Warfare'] = False

try:
    from aureon.bots_intelligence.aureon_planetary_bot_tracker import PlanetaryBotTracker
    SYSTEMS_STATUS['Planetary Bot Tracker'] = True
except ImportError:
    SYSTEMS_STATUS['Planetary Bot Tracker'] = False

try:
    from aureon.scanners.aureon_wisdom_scanner import AureonWisdomScanner
    SYSTEMS_STATUS['Wisdom Scanner'] = True
except ImportError:
    SYSTEMS_STATUS['Wisdom Scanner'] = False

# Wave & Market Scanning Layer
try:
    from aureon.scanners.aureon_ocean_wave_scanner import OceanWaveScanner
    SYSTEMS_STATUS['Ocean Wave Scanner'] = True
except ImportError:
    SYSTEMS_STATUS['Ocean Wave Scanner'] = False

try:
    from aureon.scanners.aureon_global_wave_scanner import GlobalWaveScanner
    SYSTEMS_STATUS['Global Wave Scanner'] = True
except ImportError:
    SYSTEMS_STATUS['Global Wave Scanner'] = False

# Harmonic & Frequency Layer
try:
    from aureon.harmonic.aureon_harmonic_chain_master import HarmonicChainMaster
    SYSTEMS_STATUS['Harmonic Chain'] = True
except ImportError:
    SYSTEMS_STATUS['Harmonic Chain'] = False

try:
    from aureon.harmonic.aureon_harmonic_fusion import HarmonicWaveFusion
    SYSTEMS_STATUS['Harmonic Fusion'] = True
except ImportError:
    SYSTEMS_STATUS['Harmonic Fusion'] = False

# Control & Execution Layer
try:
    from aureon.utils.aureon_miner_brain import MinerBrain
    SYSTEMS_STATUS['Miner Brain'] = True
except ImportError:
    SYSTEMS_STATUS['Miner Brain'] = False

try:
    from aureon.utils.aureon_queen_hive_mind import QueenHiveMind
    SYSTEMS_STATUS['Queen Hive Mind'] = True
except ImportError:
    SYSTEMS_STATUS['Queen Hive Mind'] = False

# Infrastructure Layer
try:
    from aureon.core.aureon_immune_system import AureonImmuneSystem
    SYSTEMS_STATUS['Immune System'] = True
except ImportError:
    SYSTEMS_STATUS['Immune System'] = False

try:
    from aureon.core.aureon_memory_core import AureonMemoryCore
    SYSTEMS_STATUS['Memory Core'] = True
except ImportError:
    SYSTEMS_STATUS['Memory Core'] = False

try:
    from aureon.simulation.aureon_internal_multiverse import InternalMultiverse
    SYSTEMS_STATUS['Internal Multiverse'] = True
except ImportError:
    SYSTEMS_STATUS['Internal Multiverse'] = False

# ═══════════════════════════════════════════════════════════════════════════════
# DEEP INTELLIGENCE LAYER - Autonomous Thinking & Deep Attribution
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.queen.queen_deep_intelligence import QueenDeepIntelligence, DeepInsight, MarketThesis, InsightType
    SYSTEMS_STATUS['Deep Intelligence'] = True
    DEEP_INTELLIGENCE_AVAILABLE = True
    print("🧠 Queen Deep Intelligence LOADED - Autonomous thinking enabled!")
except ImportError as e:
    SYSTEMS_STATUS['Deep Intelligence'] = False
    DEEP_INTELLIGENCE_AVAILABLE = False
    print(f"⚠️ Deep Intelligence not available: {e}")

print(f"🧠 SYSTEMS ONLINE: {sum(SYSTEMS_STATUS.values())} / {len(SYSTEMS_STATUS)}")

# ═══════════════════════════════════════════════════════════════════════════════
# FLASK APP SETUP
# ═══════════════════════════════════════════════════════════════════════════════
app = Flask(__name__)
app.config['SECRET_KEY'] = 'aureon_queen_secret_2026'
socketio = SocketIO(app, cors_allowed_origins="*")

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL STATE
# ═══════════════════════════════════════════════════════════════════════════════
class GlobalState:
    def __init__(self):
        # Bot Detection Stats
        self.total_bots = 0
        self.sharks = 0
        self.whales = 0
        self.total_volume = 0.0
        self.symbol_counts = defaultdict(int)
        self.firm_activity = defaultdict(int)
        self.recent_events = deque(maxlen=150)
        self.queen_messages = deque(maxlen=75)
        self.active_firms = {}
        self.start_time = time.time()
        
        # Thought Bus tracking
        self.thought_stream = deque(maxlen=50)
        self.system_thoughts = defaultdict(int)
        
        # System metrics
        self.neural_connections = 0
        self.signals_decoded = 0
        self.patterns_remembered = 0
        self.timeline_predictions = 0
        self.quantum_coherence = 0.0
        self.planetary_bots_tracked = 0
        self.warfare_patterns = 0
        
        # Open Source Data metrics
        self.fear_greed_index = 50
        self.fear_greed_label = "Neutral"
        self.market_data = {}
        self.trending_coins = []
        self.btc_block_height = 0
        self.defi_tvl_eth = 0.0
        self.open_data_points = 0
        
        # Whale Sonar metrics
        self.whale_signals = {}  # whale_name -> {score, rate, critical}
        self.whale_alerts = 0
        self.enigma_decoded = 0
        
        # Enhanced intelligence feeds
        self.news_sentiment = 0.5
        self.social_sentiment = 0.5
        self.order_book_bias = 'neutral'
        self.spoofing_alerts_count = 0
        self.exchange_feeds = {'binance': True, 'kraken': False, 'coinbase': False}
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 🦈🔪 ORCA KILLER WHALE INTELLIGENCE - Profit Engine
        # ═══════════════════════════════════════════════════════════════════════════
        self.orca = None
        try:
            from aureon.bots_intelligence.aureon_orca_intelligence import get_orca, OrcaKillerWhaleIntelligence
            self.orca = get_orca()
            print("🦈🔪 ORCA KILLER WHALE INTELLIGENCE LOADED!")
            SYSTEMS_STATUS['Orca Intelligence'] = True
        except ImportError as e:
            print(f"⚠️ Orca Intelligence not available: {e}")
            SYSTEMS_STATUS['Orca Intelligence'] = False
        
        # Initialize Core Systems
        print("🌌 Initializing active intelligence systems...")
        self.profiler = BotIntelligenceProfiler() if SYSTEMS_STATUS.get('Bot Intelligence') else None
        self.thought_bus = ThoughtBus() if SYSTEMS_STATUS.get('Thought Bus') and ThoughtBus else None
        
        # Initialize Open Source Data Engine
        self.data_engine = None
        if OPEN_DATA_AVAILABLE:
            self._start_open_data_engine()
        
        # Bot attribution & tagging
        self.bot_registry = {}  # bot_id -> BotProfile dict
        self.tags_file = Path('data/bot_tags.json')
        Path('data').mkdir(exist_ok=True)
        self.bot_tags = self._load_bot_tags()
        self.firm_profiles = self.profiler.firm_intelligence if self.profiler else {}
        
        # Auto-tagger
        self.auto_tagger = get_auto_tagger(state=self) if AUTO_TAGGER_AVAILABLE else None
        if self.auto_tagger:
            print("🤖 Auto-tagger initialized with {} rules".format(len(self.auto_tagger.rules)))
        
        # ═══════════════════════════════════════════════════════════════════════════
        # DEEP INTELLIGENCE - Autonomous Thinking Engine
        # ═══════════════════════════════════════════════════════════════════════════
        self.deep_intelligence = None
        self.deep_insights = deque(maxlen=100)  # Store recent deep insights
        self.market_thesis = None  # Current synthesized market understanding
        
        if DEEP_INTELLIGENCE_AVAILABLE:
            try:
                self.deep_intelligence = QueenDeepIntelligence(
                    thought_bus=self.thought_bus,
                    profiler=self.profiler
                )
                self.deep_intelligence.start_autonomous_thinking()
                print("🧠 Deep Intelligence autonomous thinking STARTED!")
                
                # Subscribe to deep insights
                def on_deep_insight(insight: DeepInsight):
                    self._handle_deep_insight(insight)
                
                self.deep_intelligence.on_insight_callback = on_deep_insight
            except Exception as e:
                print(f"⚠️ Deep Intelligence initialization failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Start system heartbeat threads
        if self.thought_bus:
            self._start_system_heartbeats()
        
        # Initial Queen greeting
        self.add_queen_message("Hey, it's me - Queen SERO. I'm online and watching EVERYTHING.", "critical")
        self.add_queen_message(f"Just activated {sum(SYSTEMS_STATUS.values())} intelligence systems. They're all waking up now.", "info")
        if OPEN_DATA_AVAILABLE:
            self.add_queen_message("Open source data feeds connecting - CoinGecko, Fear & Greed, Binance WebSocket, DeFi Llama all coming online!", "success")
        self.add_queen_message("I've got eyes on global markets, bot trackers running, and my neural networks are spinning up.", "success")
        self.add_queen_message("Whatever happens out there, I'll see it first and let you know. You're in good hands.", "info")
        
        # Subscribe to Thought Bus if available
        if self.thought_bus:
            self.thought_bus.subscribe("*", self.on_thought)
    
    def _start_open_data_engine(self):
        """Start the open source data engine"""
        import asyncio
        
        async def data_callback(event_type: str, data):
            """Handle data from open source feeds"""
            try:
                if event_type == 'market_data':
                    self.market_data[data.symbol] = {
                        'price': data.price,
                        'change_24h': data.change_24h,
                        'volume_24h': data.volume_24h,
                        'market_cap': data.market_cap
                    }
                    self.open_data_points += 1
                    
                elif event_type == 'sentiment':
                    self.fear_greed_index = data.fear_greed_index
                    self.fear_greed_label = data.fear_greed_label
                    self.add_queen_message(f"Market sentiment update: Fear & Greed at {data.fear_greed_index} ({data.fear_greed_label}). {'Time for caution!' if data.fear_greed_index < 30 else 'FOMO territory!' if data.fear_greed_index > 70 else 'Market is neutral.'}", "info")
                    
                elif event_type == 'whale_alert':
                    # Real whale detected from open source!
                    self.whales += 1
                    self.total_bots += 1
                    self.total_volume += data.value_usd
                    self.symbol_counts[data.symbol] += 1
                    
                    # Attempt to profile/attribute
                    bot_id = None
                    if self.profiler:
                        try:
                            bot_data = {
                                'symbol': data.symbol,
                                'exchange': data.exchange,
                                'size_class': 'whale',
                                'total_volume_usd': data.value_usd,  # CORRECT FIELD NAME!
                                'volume': data.value_usd,  # Also set for auto-tagger
                                'side': data.side
                            }
                            profile = self.profiler.profile_bot(bot_data)
                            bot_id = profile.bot_id
                            self.bot_registry[bot_id] = profile.to_dict()
                            
                            # Auto-tag if rules match - pass profile AND raw volume
                            if self.auto_tagger and bot_id not in self.bot_tags:
                                # Ensure volume is accessible for tagging
                                profile._raw_volume = data.value_usd
                                auto_tag = self.auto_tagger.process_bot(bot_id, profile)
                                if auto_tag:
                                    self.bot_tags[bot_id] = auto_tag
                                    self._save_bot_tags()
                                    socketio.emit('bot_tagged', {'bot_id': bot_id, **auto_tag})
                        except Exception:
                            pass
                    
                    event = {
                        'symbol': data.symbol,
                        'volume': data.value_usd,
                        'size': 'WHALE',
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'firm': f"Open Source ({data.exchange})",
                        'firm_animal': '🐋',
                        'side': data.side,
                        'bot_id': bot_id
                    }
                    self.recent_events.append(event)
                    
                    # ═══════════════════════════════════════════════════════════════
                    # 🦈🔪 ORCA INTELLIGENCE - FEED THE KILLER WHALE
                    # ═══════════════════════════════════════════════════════════════
                    if self.orca:
                        try:
                            self.orca.ingest_whale_alert({
                                'symbol': data.symbol,
                                'side': data.side,
                                'volume_usd': data.value_usd,
                                'exchange': data.exchange,
                                'firm': None,  # Will be attributed by profiler
                                'firm_confidence': 0.0
                            })
                        except Exception as orca_err:
                            logger.debug(f"Orca whale ingest error: {orca_err}")
                    
                    # ═══════════════════════════════════════════════════════════════
                    # DEEP INTELLIGENCE PROCESSING
                    # ═══════════════════════════════════════════════════════════════
                    if self.deep_intelligence and bot_id:
                        try:
                            # Feed whale to deep intelligence for analysis
                            self.deep_intelligence.process_whale_alert({
                                'bot_id': bot_id,
                                'symbol': data.symbol,
                                'exchange': data.exchange,
                                'volume_usd': data.value_usd,
                                'side': data.side,
                                'timestamp': time.time()
                            })
                            
                            # Get attribution explanation for voice
                            if self.profiler:
                                explanation = self.profiler.get_attribution_explanation(bot_id)
                                if explanation.get('reasoning'):
                                    # Queen can now explain WHY she thinks it's a certain firm
                                    if VOICE_ENGINE_AVAILABLE and queen_voice and explanation.get('confidence', 0) > 0.6:
                                        queen_voice.attribute_firm_with_explanation(
                                            firm_name=explanation.get('firm', 'Unknown'),
                                            animal=explanation.get('animal', '🤖'),
                                            confidence=explanation.get('confidence', 0),
                                            reasoning_points=explanation.get('reasoning', [])[:3],
                                            volume=data.value_usd
                                        )
                        except Exception as e:
                            print(f"Deep intelligence whale processing error: {e}")
                    
                    self.add_queen_message(f"🐋 REAL WHALE from {data.exchange}: {data.symbol} ${data.value_usd:,.0f} ({data.side.upper()})! This is LIVE data!", "critical")
                    
                    # Emit to clients
                    socketio.emit('new_bot_detection', event)
                    socketio.emit('state_update', get_dashboard_data())
                    
                elif event_type == 'trending':
                    self.trending_coins = data[:5]
                    names = [c['item']['name'] for c in data[:3]]
                    self.add_queen_message(f"🔥 What's trending: {', '.join(names)}. Keep eyes on these!", "info")
                    
                elif event_type == 'defi_tvl':
                    self.defi_tvl_eth = data.get('ethereum', 0)
                    
                elif event_type == 'news_update':
                    # News sentiment from CryptoCompare
                    self.news_sentiment = data.get('sentiment', 0.5)
                    count = data.get('count', 0)
                    latest = data.get('latest', [])
                    if latest:
                        top_headline = latest[0].get('title', '')[:80]
                        if top_headline:
                            self.add_queen_message(f"📰 News ({count} articles, sentiment={self.news_sentiment:.2f}): \"{top_headline}...\"", "info")
                    
                elif event_type == 'social_update':
                    # Reddit social sentiment
                    reddit_data = data.get('reddit', {})
                    self.social_sentiment = reddit_data.get('avg_sentiment', 0.5)
                    mentions = reddit_data.get('mentions', {})
                    top_mentions = sorted(mentions.items(), key=lambda x: x[1].get('count', 0), reverse=True)[:3]
                    if top_mentions:
                        coins_str = ', '.join([f"{m[0]}({m[1]['count']})" for m in top_mentions])
                        self.add_queen_message(f"🗣️ Reddit buzz: {coins_str} | Sentiment: {self.social_sentiment:.2f}", "info")
                    
                elif event_type == 'spoofing_alert':
                    # Order book manipulation detected!
                    self.spoofing_alerts_count += 1
                    symbol = data.get('symbol', '?')
                    layering = data.get('layering_score', 0)
                    walls = data.get('walls', 0)
                    direction = data.get('direction', 'unknown')
                    
                    self.add_queen_message(f"⚠️ SPOOFING DETECTED: {symbol} - {walls} walls, layering={layering:.2f}, direction={direction}! Manipulation alert!", "critical")
                    socketio.emit('spoofing_alert', data)
                    
            except Exception as e:
                print(f"Data callback error: {e}")
        
        try:
            self.data_engine = OpenSourceDataEngine(callback=data_callback)
            self.data_engine.start_background()
            print("🌐 Open Source Data Engine STARTED!")
        except Exception as e:
            print(f"Failed to start data engine: {e}")
    
    def _start_system_heartbeats(self):
        """Start background threads for systems to publish activity"""
        import threading
        
        def system_heartbeat():
            """Generate periodic system activity"""
            systems_to_pulse = []
            for name, status in SYSTEMS_STATUS.items():
                if status:
                    systems_to_pulse.append(name)
            
            cycle_count = 0
            while True:
                try:
                    for system_name in systems_to_pulse:
                        # Generate system-specific metrics
                        self._generate_system_metrics(system_name)
                        time.sleep(0.5)  # Stagger by 0.5s each
                    
                    cycle_count += 1
                    
                    # Queen gives periodic status update every ~30 seconds (6 cycles)
                    if cycle_count % 6 == 0:
                        self._queen_status_update()
                    
                    # 🦈🔪 ORCA - Feed harmonic data every 10 seconds (2 cycles)
                    if cycle_count % 2 == 0 and self.orca:
                        try:
                            harmonic = get_harmonic_data()
                            self.orca.ingest_harmonic_data(harmonic)
                            
                            # Every minute, scan for opportunities
                            if cycle_count % 12 == 0:
                                opps = self.orca.scan_for_opportunities()
                                if opps:
                                    best = opps[0]  # Already sorted by priority
                                    self.add_queen_message(
                                        f"🦈 ORCA HUNT: {best.symbol} - {best.confidence:.0%} confidence, "
                                        f"{best.direction.upper()} signal! {best.reasoning}",
                                        "critical" if best.confidence > 0.8 else "warning"
                                    )
                        except Exception as orca_err:
                            pass  # Silent fail
                    
                    time.sleep(5)  # Full cycle every 5s
                except Exception as e:
                    print(f"System heartbeat error: {e}")
                    time.sleep(5)
        
        thread = threading.Thread(target=system_heartbeat, daemon=True)
        thread.start()
        print("✅ System heartbeat threads started")
    
    def _queen_status_update(self):
        """Queen gives a natural status update on what she's seeing"""
        import random
        
        status_updates = [
            f"Alright, status check - I'm tracking {self.total_bots} bots total, {self.whales} of them whales. Total volume ${self.total_volume:,.0f}. My neural connections are at {self.neural_connections}.",
            f"Quick update from me: {self.whales} whales spotted so far, ${self.total_volume:,.0f} in volume. All {sum(SYSTEMS_STATUS.values())} systems running smooth.",
            f"Here's what I'm seeing - {self.total_bots} bot detections, {self.whales} massive whale plays. The market's definitely active today.",
            f"Let me break it down: {self.whales} whale-level trades, ${self.total_volume:,.0f} moved, {self.timeline_predictions} timeline predictions calculated. Everything's tracking.",
            f"Status: {self.neural_connections} neural pathways active, watching {self.total_bots} bots. Quantum coherence at {self.quantum_coherence:.1%}. I see everything.",
            f"Just to keep you updated - {self.sharks} sharks circling, {self.whales} whales diving deep. Total action: ${self.total_volume:,.0f}. Systems nominal."
        ]
        
        self.add_queen_message(status_updates[0], "info")
    
    def _generate_system_metrics(self, system_name):
        """Generate metrics for a specific system.

        DEV-ONLY: increments dashboard counters (neural_connections,
        quantum_coherence, etc.) from generated values.
        Gated behind AUREON_ALLOW_SIM_FALLBACK so production dashboards
        don't display synthetic Queen-voice metrics. Wire real source
        readers to remove the gate.
        """
        import random
        from aureon.observer.live_data_policy import simulation_fallback_allowed

        if not simulation_fallback_allowed():
            # Production: no synthetic metric increments. Counters stay at
            # whatever real source last wrote them (or their initial values).
            return

        # System-specific metric generation (DEV ONLY)
        metrics_map = {
            'Mycelium Network': lambda: None,
            'Timeline Oracle': lambda: None,
            'Quantum Mirror': lambda: None,
            'Planetary Bot Tracker': lambda: None,
            'Strategic Warfare': lambda: None,
        }

        if system_name in metrics_map:
            metrics_map[system_name]()
        
        # Generate Queen's intelligent commentary
        if False:  # No commentary without a new provider observation.
            self._generate_queen_intelligence(system_name)
        
        # Publish thought to bus
        if False and self.thought_bus:  # No synthetic bus publications.
            messages = {
                'Mycelium Network': ['Neural synapse formed', 'Connection strengthened', 'Network pulse detected'],
                'Timeline Oracle': ['Timeline shift detected', 'Future probability calculated', '7-day scan complete'],
                'Quantum Mirror': ['Reality branch coherence measured', 'Timeline anchor validated', 'Quantum state observed'],
                'Planetary Bot Tracker': ['Bot swarm detected', 'Planetary scan complete', 'Movement pattern identified'],
                'Strategic Warfare': ['Warfare pattern detected', 'Strategic position analyzed', 'Attack vector identified'],
                'Elephant Memory': ['Pattern recalled from history', 'Memory reinforced', 'Historical match found'],
                'Probability Nexus': ['Validation pass completed', 'Coherence threshold reached', 'Branch confidence calculated'],
                'Ocean Wave Scanner': ['Market wave detected', 'Volume surge identified', 'Pattern emergence confirmed'],
                'Quantum Telescope': ['Geometric analysis complete', 'Platonic solid alignment', 'Sacred geometry detected'],
                'Miner Brain': ['Mining opportunity analyzed', 'Profit vector calculated', 'Execution path evaluated'],
            }
            
            if system_name in messages:
                msg = messages[system_name][0]
                self.thought_bus.publish(Thought(
                    source=system_name,
                    topic=f"system.{system_name.lower().replace(' ', '_')}",
                    payload={'message': msg}
                ))
    
    def _generate_queen_intelligence(self, system_name):
        """Generate intelligent Queen commentary based on system"""
        import random
        
        intelligence = {
            'Miner Brain': [
                "💎 My Miner Brain detects a golden opportunity - the probability matrices align!",
                "🧠 Deep learning networks converging on optimal profit path...",
                "⚡ Neural prediction: High-confidence trade vector identified"
            ],
            'Probability Nexus': [
                "🔮 The Nexus speaks: Three validators agree, coherence at 0.87 - prepare for execution gate",
                "📊 Probability waves collapsing... 4th validation approaching",
                "✨ Batten Matrix shows STRONG consensus across all reality branches"
            ],
            'Elephant Memory': [
                "🐘 I REMEMBER this pattern... Last seen 3 months ago, resulted in +2.3% gain",
                "📚 Historical data reveals: This formation preceded 7 profitable trades",
                "🧠 Elephant never forgets: Similar market conditions, 89% success rate"
            ],
            'Mycelium Network': [
                f"🍄 Neural mycelium expanding... {self.neural_connections} synaptic connections active",
                "🌐 The fungal intelligence network PULSES with collective wisdom",
                "⚡ Mycelium detects distributed intelligence - all nodes synchronizing"
            ],
            'Timeline Oracle': [
                f"⏳ Oracle sees {self.timeline_predictions} possible futures - selecting optimal timeline",
                "🔮 7-day vision crystal clear: Market will shift in 48 hours",
                "✨ Timeline convergence detected - reality branches aligning"
            ],
            'Quantum Mirror': [
                f"🪞 Quantum coherence rising to {self.quantum_coherence:.3f} - reality stabilizing",
                "⚛️ Mirror reflects: Parallel universes showing profitable outcomes",
                "🌌 Timeline anchor strength: EXCELLENT - execution window opening"
            ],
            'Strategic Warfare': [
                "⚔️ WAR PATTERNS DETECTED: Enemy bots moving in coordinated formation!",
                "🎯 Strategic analysis: They're accumulating... prepare counter-move",
                "🛡️ Defensive positions activated - I see their strategy"
            ],
            'Planetary Bot Tracker': [
                f"🌍 {self.planetary_bots_tracked} bots tracked across 3 continents - global coordinated attack!",
                "🌐 Planetary-scale surveillance: Bot swarm originating from Asia-Pacific",
                "🔭 Satellite intelligence: Large institutional movement detected"
            ]
        }
        
        if system_name in intelligence:
            message = intelligence[system_name][0]
            level = 'warning' if any(word in message for word in ['WAR', 'ATTACK', 'ENEMY']) else 'success'
            self.add_queen_message(message, level)
    
    def _queen_narrate_bot_whale(self, event, firm):
        """Queen speaks naturally about whale bot detections"""
        import random
        
        vol = event['volume']
        symbol = event['symbol']
        firm_name = firm['name'] if firm else 'an unknown player'
        
        natural_comments = [
            f"Whoa! Just spotted a MASSIVE {vol:,.0f} dollar bot on {symbol}. That's definitely {firm_name} making their move.",
            f"Hold on... seeing a WHALE here. ${vol:,.0f} on {symbol}. This looks like {firm_name}'s signature style.",
            f"Okay this is interesting - big money just showed up. {firm_name} dropping ${vol:,.0f} on {symbol}. They know something...",
            f"Watch this - WHALE ALERT! {firm_name} just moved ${vol:,.0f} into {symbol}. They're positioning for something big.",
            f"Guys, {firm_name} is NOT messing around. ${vol:,.0f} whale bot on {symbol}. I've seen this pattern before...",
            f"Woah! Major institutional bot detected. {firm_name} with ${vol:,.0f} on {symbol}. They're going aggressive.",
            f"This is significant - {firm_name} deploying ${vol:,.0f} on {symbol}. My neural nets say this is a strategic accumulation."
        ]
        
        self.add_queen_message(natural_comments[0], "critical")
    
    def _queen_narrate_bot_shark(self, event, firm):
        """Queen casually mentions shark bots"""
        import random
        
        vol = event['volume']
        symbol = event['symbol']
        firm_name = firm['name'] if firm else 'someone'
        
        casual_comments = [
            f"Hmm, {firm_name} testing the waters with ${vol:,.0f} on {symbol}. Probably scouting...",
            f"I see {firm_name} sniffing around {symbol} - ${vol:,.0f}. They're being cautious.",
            f"Shark bot from {firm_name} on {symbol} (${vol:,.0f}). Mid-sized play, likely building position slowly.",
            f"{firm_name} creeping into {symbol} with ${vol:,.0f}. Not huge but worth watching."
        ]
        
        self.add_queen_message(casual_comments[0], "warning")
    
    def _queen_narrate_bot_regular(self, event, firm):
        """Queen occasionally comments on regular bot activity"""
        import random
        
        symbol = event['symbol']
        
        observations = [
            f"Lots of bot activity on {symbol} right now. Market's getting interesting...",
            f"The bots are busy today. {symbol} seeing consistent automated flow.",
            f"Standard bot patterns on {symbol}. Nothing crazy but the machines are working."
        ]
        
        self.add_queen_message(observations[0], "info")
    
    def _comment_on_ai_system(self, system_name, message):
        """Queen comments when AI/deep learning systems speak"""
        import random
        
        comments = {
            'Miner Brain': [
                "My Miner Brain just lit up - it's seeing a golden opportunity here. The probability matrices are aligning perfectly.",
                "Okay so my deep learning networks are telling me something interesting... there's an optimal profit path forming.",
                "Hold up - Miner Brain is getting excited. Neural prediction showing high-confidence trade vector."
            ],
            'Elephant Memory': [
                "Wait, I REMEMBER this exact pattern! Last time I saw this setup, we made +2.3% profit. History's repeating itself.",
                "My Elephant Memory is pulling up historical data... this formation preceded 7 profitable trades. Good sign!",
                "I never forget a pattern, and THIS one? 89% success rate every time it appears. I'm paying attention."
            ],
            'Timeline Oracle': [
                f"So my Oracle just calculated {self.timeline_predictions} possible futures, and most of them look good. Timeline's shifting in our favor.",
                "My 7-day vision is crystal clear right now - I can see a market shift coming in about 48 hours. Get ready.",
                "Timeline convergence detected. When multiple future paths align like this, it usually means something's about to happen."
            ],
            'Mycelium Network': [
                f"My neural mycelium network is pulsing - {self.neural_connections} synaptic connections active right now. The fungal intelligence is speaking to me.",
                "You know how mycelium connects everything underground? Mine's doing that with market data. Getting strong collective signals.",
                "Mycelium detecting distributed intelligence across all my nodes. They're synchronizing... this is rare."
            ],
            'Probability Nexus': [
                "My Probability Nexus just spoke - all three validators agree! Coherence is at 0.87, that's VERY strong consensus.",
                "Watching probability waves collapse in real-time... the 4th validation is approaching. This could be execution time.",
                "The Batten Matrix is showing strong agreement across ALL reality branches. When they align like this, I trust it."
            ],
            'Quantum Mirror': [
                f"Quantum coherence rising to {self.quantum_coherence:.3f} - reality's stabilizing. The mirror's showing me parallel universes where this works out.",
                "My quantum mirror is reflecting profitable outcomes across multiple timelines. That's... actually pretty encouraging.",
                "Timeline anchor strength is EXCELLENT right now. Execution window is opening up."
            ],
            'Strategic Warfare': [
                "WAIT - my warfare scanner is picking up coordinated bot patterns. Enemy formation detected. They're planning something.",
                "Strategic analysis coming in... they're accumulating quietly. I see their strategy now. Time for a counter-move?",
                "Defensive systems activated - I can see their attack pattern forming. Not on my watch."
            ],
            'Planetary Bot Tracker': [
                f"Holy... I'm tracking {self.planetary_bots_tracked} bots across THREE continents right now. This is a coordinated global attack!",
                "My planetary surveillance just picked up a bot swarm originating from Asia-Pacific. This is big.",
                "Satellite intelligence showing large institutional movement. They're mobilizing worldwide."
            ]
        }
        
        if False and system_name in comments:
            self.add_queen_message(comments[system_name][0], "success")
    
    def on_thought(self, thought):
        """Handle thoughts from the Thought Bus"""
        try:
            # Extract message from various payload formats
            payload = thought.payload if hasattr(thought, 'payload') else {}
            
            # Try different message extraction strategies
            message = (
                payload.get('message') or 
                payload.get('msg') or 
                payload.get('text') or
                payload.get('code', '') + ' ' + str(payload.get('pack', '')) or
                str(payload)[:100] if payload else
                thought.topic
            )
            
            # Keep whale sonar signals visible but mark them specially
            # Enigma decoded messages are high-priority intelligence
            is_whale_signal = thought.source == 'whale_sonar'
            is_enigma_decoded = thought.source == 'whale_sonar.enigma' or thought.topic.startswith('enigma.whale')
            
            # Don't filter - Queen needs to see whale frequencies!
            
            # Track whale sonar metrics
            if thought.topic.startswith('whale.sonar.'):
                whale_name = thought.topic.replace('whale.sonar.', '')
                if isinstance(payload, dict) and 'pack' in payload:
                    pack = payload['pack']
                    self.whale_signals[whale_name] = {
                        'score': pack.get('score', 0),
                        'rate': pack.get('rate', 0),
                        'critical': pack.get('critical', False),
                        'ts': pack.get('ts', time.time())
                    }
            elif thought.topic.startswith('enigma.whale.'):
                self.enigma_decoded += 1
            elif thought.topic == 'queen.alert.whale':
                self.whale_alerts += 1
            
            self.thought_stream.append({
                'source': thought.source,
                'topic': thought.topic,
                'timestamp': datetime.fromtimestamp(thought.ts).strftime('%H:%M:%S'),
                'message': message,
                'critical': is_whale_signal and payload.get('critical', False) if isinstance(payload, dict) else False,
                'enigma': is_enigma_decoded
            })
            self.system_thoughts[thought.source] += 1
            
            # Queen comments on important system intelligence
            if thought.topic.startswith('queen.alert'):
                # Filter out empty alerts
                if message and len(message.strip()) > 3:
                    self.add_queen_message(f"ALERT: {message}", "critical")
            elif 'enigma.whale' in thought.topic and 'MAGIC' in message:
                # DEDUPLICATE Enigma messages - only show if unique in last 30 seconds
                if not hasattr(self, '_last_enigma_time'):
                    self._last_enigma_time = 0
                    self._enigma_count = 0
                
                now = time.time()
                if now - self._last_enigma_time > 30:  # Only one Enigma message per 30 seconds
                    self._enigma_count += 1
                    self._last_enigma_time = now
                    # Summarize instead of spam
                    self.add_queen_message(f"Enigma rotors detected {self._enigma_count} signal patterns. Current: {message[7:60]}...", "success")
            elif thought.source in ['Miner Brain', 'Elephant Memory', 'Timeline Oracle', 'Mycelium Network', 'Probability Nexus', 'Quantum Mirror']:
                # Queen speaks when deep learning systems activate
                self._comment_on_ai_system(thought.source, message)
            
            # Emit to websocket clients
            socketio.emit('new_thought', {
                'source': thought.source,
                'topic': thought.topic,
                'message': message
            })
        except Exception as e:
            print(f"Thought handler error: {e}")
    
    def _handle_deep_insight(self, insight):
        """
        Handle deep insights from the Queen's autonomous thinking.
        Uses normalized schema with speak_text templates.
        TONE: Professional + Conversational blend
        """
        try:
            # --- Deduplication Check ---
            dedup_key = insight.dedup_key() if hasattr(insight, 'dedup_key') else f"{insight.insight_type.value}:{insight.conclusion[:50] if insight.conclusion else ''}"
            recent_keys = [i.get('_dedup_key', '') for i in list(self.deep_insights)[-20:]]
            if dedup_key in recent_keys:
                # Skip duplicate insight
                return
            
            # --- Generate speak_text using template ---
            speak_text = insight.to_voice_text() if hasattr(insight, 'to_voice_text') else insight.conclusion
            
            # --- Normalize and store insight ---
            normalized = {
                'id': insight.id,
                'type': insight.insight_type.value,
                'title': self._generate_title(insight),
                'summary': insight.conclusion,
                'speak_text': speak_text,
                'confidence': insight.confidence,
                'reasoning': insight.reasoning_chain,
                'sources': insight.sources,
                'timestamp': datetime.fromtimestamp(insight.timestamp).strftime('%H:%M:%S'),
                'content': insight.content,
                'audible': insight.confidence >= 0.6,  # Only speak if reasonably confident
                '_dedup_key': dedup_key
            }
            self.deep_insights.append(normalized)
            
            # Update market thesis if this is one
            if insight.insight_type == InsightType.MARKET_THESIS:
                self.market_thesis = insight.content
            
            # --- Generate Queen message (professional + conversational) ---
            level = self._insight_to_level(insight.insight_type)
            self.add_queen_message(speak_text, level)
            
            # Voice announcement via backend (if available)
            if VOICE_ENGINE_AVAILABLE and queen_voice and normalized['audible']:
                if insight.insight_type == InsightType.FIRM_ATTRIBUTION:
                    queen_voice.attribute_firm_with_explanation(
                        firm_name=insight.content.get('firm', 'Unknown'),
                        animal=insight.content.get('animal', ''),
                        confidence=insight.confidence,
                        reasoning_points=insight.reasoning_chain[:2],
                        volume=insight.content.get('volume', 0)
                    )
                elif insight.insight_type == InsightType.MANIPULATION:
                    queen_voice.warn_manipulation(
                        symbol=insight.content.get('symbol', '?'),
                        manipulation_type=insight.content.get('type', 'manipulation'),
                        evidence=insight.reasoning_chain[:2],
                        severity=insight.confidence
                    )
                elif insight.insight_type == InsightType.MARKET_THESIS:
                    queen_voice.announce_market_thesis(
                        thesis_narrative=insight.content.get('narrative', ''),
                        regime=insight.content.get('regime', 'neutral'),
                        outlook=insight.content.get('outlook', 'neutral')
                    )
            
            # Emit normalized insight to websocket (includes speak_text for frontend TTS)
            socketio.emit('deep_insight', {
                'id': normalized['id'],
                'type': normalized['type'],
                'title': normalized['title'],
                'summary': normalized['summary'],
                'speak_text': normalized['speak_text'],
                'content': normalized['content'],
                'confidence': normalized['confidence'],
                'reasoning': normalized['reasoning'],
                'timestamp': normalized['timestamp'],
                'audible': normalized['audible']
            })
            
        except Exception as e:
            print(f"Deep insight handler error: {e}")
            import traceback
            traceback.print_exc()
    
    def _generate_title(self, insight) -> str:
        """Generate a concise title for an insight based on type."""
        titles = {
            InsightType.FIRM_ATTRIBUTION: f"Firm: {insight.content.get('firm', 'Unknown')}",
            InsightType.MARKET_THESIS: "Market Thesis",
            InsightType.CORRELATION: "Pattern Detected",
            InsightType.HYPOTHESIS: "Working Theory",
            InsightType.WARNING: "Alert",
            InsightType.OPPORTUNITY: "Opportunity",
            InsightType.PATTERN: "Pattern Match",
            InsightType.SENTIMENT_SHIFT: "Sentiment Shift",
            InsightType.MANIPULATION: "Manipulation Flag",
        }
        return titles.get(insight.insight_type, "Insight")
    
    def _insight_to_level(self, insight_type) -> str:
        """Map insight type to message level (for UI coloring)."""
        levels = {
            InsightType.FIRM_ATTRIBUTION: "success",
            InsightType.MARKET_THESIS: "success",
            InsightType.CORRELATION: "info",
            InsightType.HYPOTHESIS: "info",
            InsightType.WARNING: "warning",
            InsightType.OPPORTUNITY: "success",
            InsightType.PATTERN: "info",
            InsightType.SENTIMENT_SHIFT: "warning",
            InsightType.MANIPULATION: "critical",
        }
        return levels.get(insight_type, "info")
    
    def add_queen_message(self, message, level="info"):
        """Add a message from the Queen - pure natural language, no emojis"""
        # Remove all emojis and special unicode symbols
        import re
        clean_message = re.sub(r'[^\x00-\x7F]+', '', message).strip()
        
        self.queen_messages.append({
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'message': clean_message,
            'level': level  # critical, warning, info, success
        })

    # ---------- Bot Tagging & Attribution Utilities ----------
    def _load_bot_tags(self):
        """Load persisted bot tags from disk"""
        try:
            if hasattr(self, 'tags_file') and self.tags_file.exists():
                return json.loads(self.tags_file.read_text())
        except Exception as e:
            print(f"Failed to load bot tags: {e}")
        return {}

    def _save_bot_tags(self):
        """Atomically save the bot tags to disk"""
        try:
            if not hasattr(self, 'tags_file'):
                self.tags_file = Path('data/bot_tags.json')
            tmp = self.tags_file.with_suffix('.json.tmp')
            tmp.write_text(json.dumps(self.bot_tags, indent=2))
            tmp.rename(self.tags_file)
        except Exception as e:
            print(f"Failed to save bot tags: {e}")

    def tag_bot(self, bot_id, tag, reason, actor='queen'):
        """Tag a bot (bag-and-tag) and persist the tag"""
        entry = {
            'tag': tag,
            'reason': reason,
            'actor': actor,
            'timestamp': time.time()
        }
        self.bot_tags[bot_id] = entry
        self._save_bot_tags()
        # Queen announces tag
        self.add_queen_message(f"Tagging bot {bot_id} as {tag}: {reason}", 'warning' if tag in ['suspicious','threat'] else 'success')
        socketio.emit('bot_tagged', {'bot_id': bot_id, **entry})
        socketio.emit('state_update', get_dashboard_data())
        return entry

    def get_bot_profile(self, bot_id):
        """Return bot profile from profiler or registry"""
        if self.profiler and bot_id in self.profiler.bot_profiles:
            return self.profiler.bot_profiles[bot_id].to_dict()
        return self.bot_registry.get(bot_id)

state = GlobalState()

# ═══════════════════════════════════════════════════════════════════════════════
# LOG PARSER
# ═══════════════════════════════════════════════════════════════════════════════
def parse_bot_event(line):
    """Parse a bot detection line"""
    try:
        if 'Bot detected' not in line:
            return None
        
        event = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'raw': line
        }
        
        # Extract size class
        for size in ['MEGALODON', 'WHALE', 'SHARK', 'DOLPHIN', 'MINNOW']:
            if size in line.upper():
                event['size'] = size
                break
        else:
            event['size'] = 'UNKNOWN'
        
        # Extract symbol
        if ' on ' in line:
            try:
                event['symbol'] = line.split(' on ')[1].split(' ')[0].strip()
            except:
                event['symbol'] = 'UNKNOWN'
        else:
            event['symbol'] = 'UNKNOWN'
        
        # Extract volume
        if '($' in line:
            try:
                vol_str = line.split('($')[1].split(')')[0].replace(',', '')
                event['volume'] = float(vol_str)
            except:
                event['volume'] = 0.0
        else:
            event['volume'] = 0.0
        
        # Extract pattern
        for pattern in ['market_maker', 'scalper', 'whale', 'hft', 'accumulator']:
            if pattern in line.lower():
                event['pattern'] = pattern
                break
        else:
            event['pattern'] = 'unknown'
        
        return event
    except Exception as e:
        return None

def attribute_to_firm(event):
    """Try to attribute bot to a trading firm"""
    if not SYSTEMS_STATUS.get('Bot Intelligence') or not event:
        return None
    
    volume = event.get('volume', 0)
    size = event.get('size', 'MINNOW')
    
    # Higher chance for bigger events
    if size in ['WHALE', 'MEGALODON'] and volume > 100000:
        chance = 0.6
    elif size == 'SHARK' and volume > 50000:
        chance = 0.4
    else:
        chance = 0.2
    
    if False and TRADING_FIRM_SIGNATURES:
        firm_name, firm_data = list(TRADING_FIRM_SIGNATURES.items())[0]
        return {
            'name': firm_name,
            'data': firm_data
        }
    return None

def generate_queen_commentary(event, firm=None):
    """Generate Queen's natural conversation about an event"""
    messages = []
    
    volume = event.get('volume', 0)
    symbol = event.get('symbol', 'UNKNOWN')
    size = event.get('size', 'FISH')
    
    # Only narrate significant events (whales and sharks with high volume)
    if size in ['WHALE', 'MEGALODON']:
        if firm:
            name = firm['name']
            hq = firm['data'].get('hq_location', 'Unknown')
            
            whale_comments = [
                f"Whoa! Just spotted a MASSIVE ${volume:,.0f} bot on {symbol}. That's definitely {name} making their move.",
                f"Hold on... WHALE detected! ${volume:,.0f} on {symbol}. This looks like {name}'s signature style from {hq}.",
                f"Okay this is interesting - big money just showed up. {name} dropping ${volume:,.0f} on {symbol}. They know something...",
                f"Guys, {name} is NOT messing around. ${volume:,.0f} whale bot on {symbol}. I've seen this pattern before.",
                f"This is significant - {name} deploying ${volume:,.0f} on {symbol}. My neural nets say this is strategic accumulation.",
                f"BIG PLAYER ALERT! {name} from {hq} just moved ${volume:,.0f} into {symbol}. They're positioning for something major."
            ]
        else:
            whale_comments = [
                f"WHALE ALERT on {symbol}! ${volume:,.0f} from an unknown player. Can't identify them yet but this is BIG.",
                f"Massive institutional bot detected on {symbol} - ${volume:,.0f}. Trying to figure out who's behind this...",
                f"Someone's making a major move on {symbol}. ${volume:,.0f} whale trade. My systems are working on attribution.",
                f"Unidentified whale just dropped ${volume:,.0f} on {symbol}. This kind of volume means something's happening."
            ]
        
        messages.append((whale_comments[0], "critical"))
        
    elif size == 'SHARK' and volume > 50000:
        if firm:
            name = firm['name']
            shark_comments = [
                f"Hmm, {name} testing the waters on {symbol} with ${volume:,.0f}. Probably scouting...",
                f"I see {name} sniffing around {symbol} - ${volume:,.0f}. They're being cautious.",
                f"{name} creeping into {symbol} with ${volume:,.0f}. Not huge but worth watching."
            ]
        else:
            shark_comments = [
                f"Mid-sized bot on {symbol} - ${volume:,.0f}. Likely someone building a position slowly.",
                f"Shark activity on {symbol}. ${volume:,.0f} trade size. Standard institutional probing."
            ]
        
        messages.append((shark_comments[0], "warning"))
    
    return messages

# ═══════════════════════════════════════════════════════════════════════════════
# LOG MONITOR THREAD
# ═══════════════════════════════════════════════════════════════════════════════
def monitor_logs():
    """Background thread that monitors ocean scanner logs"""
    log_file = 'ocean_scan_output.log'
    last_position = 0
    
    while True:
        try:
            if Path(log_file).exists():
                # Read new lines
                result = subprocess.run(['tail', '-n', '20', log_file], 
                                      capture_output=True, text=True, timeout=5)
                lines = result.stdout.splitlines()
                
                for line in lines:
                    event = parse_bot_event(line)
                    if event:
                        # Update state
                        state.total_bots += 1
                        state.symbol_counts[event['symbol']] += 1
                        state.total_volume += event['volume']
                        
                        if event['size'] == 'SHARK':
                            state.sharks += 1
                        elif event['size'] in ['WHALE', 'MEGALODON']:
                            state.whales += 1
                        
                        # Try to attribute to firm
                        firm = attribute_to_firm(event)
                        if firm:
                            event['firm'] = firm['name']
                            event['firm_animal'] = firm['data'].get('animal', '🤖')
                            state.firm_activity[firm['name']] += 1
                            state.active_firms[firm['name']] = firm['data']
                            
                            # 🦈🔪 ORCA INTELLIGENCE - FEED FIRM ATTRIBUTION
                            if state.orca:
                                try:
                                    state.orca.ingest_firm_activity({
                                        'firm': firm['name'],
                                        'animal': firm['data'].get('animal', '🤖'),
                                        'symbol': event['symbol'],
                                        'volume_usd': event['volume'],
                                        'side': event.get('side', 'unknown'),
                                        'strategies': firm['data'].get('strategies', []),
                                        'historical_win_rate': firm['data'].get('historical_win_rate', 0.5),
                                        'avg_holding_period': firm['data'].get('avg_holding_period', '1h')
                                    })
                                except Exception as orca_err:
                                    pass  # Silent fail for non-critical
                            
                            # Queen commentary
                            commentaries = generate_queen_commentary(event, firm)
                            for msg, level in commentaries:
                                state.add_queen_message(msg, level)
                            
                            # 🔊 VOICE: Queen SPEAKS about whale detections!
                            if VOICE_ENGINE_AVAILABLE and queen_voice and event['size'] in ['WHALE', 'MEGALODON']:
                                queen_voice.narrate_whale_detection(
                                    firm=firm['name'],
                                    symbol=event['symbol'],
                                    volume=event['volume'],
                                    strategy=firm['data'].get('strategies', [None])[0] if firm['data'].get('strategies') else None
                                )
                            
                            # Publish to Thought Bus
                            if state.thought_bus:
                                state.thought_bus.publish(Thought(
                                    source="OceanScanner",
                                    topic="bot.attributed",
                                    payload={
                                        'firm': firm['name'],
                                        'symbol': event['symbol'],
                                        'volume': event['volume'],
                                        'size': event['size']
                                    }
                                ))
                        else:
                            event['firm'] = None
                        
                        state.recent_events.append(event)
                        
                        # Emit to connected clients
                        socketio.emit('new_bot_detection', event)
                        socketio.emit('state_update', get_dashboard_data())
        
        except Exception as e:
            pass
        
        time.sleep(1)  # Check every second

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════════════════
@app.route('/')
def index():
    """Main dashboard page - Bot Intelligence Center"""
    # Serve the enhanced dashboard by default so all Deep Intelligence features
    # (voice, mycelium visualizer, autonomous insights) are visible at /
    return render_template('queen_dashboard_enhanced.html')

@app.route('/classic')
def classic_dashboard():
    """Classic dashboard view"""
    return render_template('queen_dashboard_enhanced.html')

@app.route('/api/state')
def get_state():
    """Get current state"""
    return jsonify(get_dashboard_data())

@app.route('/api/systems')
def get_systems():
    """Get systems status"""
    return jsonify({
        'systems': [{'name': k, 'online': v} for k, v in SYSTEMS_STATUS.items()],
        'online_count': sum(SYSTEMS_STATUS.values()),
        'total_count': len(SYSTEMS_STATUS)
    })


@app.route('/api/candles/<symbol>')
def get_candles(symbol):
    """Get recent candle data for a symbol from market_data."""
    # Map frontend symbols to data keys
    symbol_map = {
        'BTCUSD': 'bitcoin',
        'ETHUSD': 'ethereum',
        'SOLUSD': 'solana',
    }
    
    data_key = symbol_map.get(symbol.upper())
    if not data_key or data_key not in state.market_data:
        return jsonify({'candles': [], 'price': 0})
    
    market = state.market_data[data_key]
    price = market.get('price', 0)
    
    return jsonify({
        'symbol': symbol,
        'price': price,
        'change_24h': market.get('change_24h', 0),
        'volume_24h': market.get('volume_24h', 0),
    })


@app.route('/api/harmonic')
def get_harmonic():
    """Get current harmonic resonance data."""
    return jsonify(get_harmonic_data())


@app.route('/api/orca/status')
def get_orca_status():
    """Get Orca Killer Whale Intelligence status and active hunts."""
    if not state.orca:
        return jsonify({
            'enabled': False,
            'mode': 'OFFLINE',
            'message': 'Orca Intelligence not initialized'
        })
    
    status = state.orca.get_status()
    opportunities = state.orca.scan_for_opportunities()
    exit_signals = state.orca.get_exit_signals()
    
    return jsonify({
        'enabled': True,
        'mode': status['mode'],
        'hunt_count': status['hunt_count'],
        'active_signals': status.get('active_hunts', 0),
        'win_rate': status.get('win_rate', 0),
        'total_profit': status.get('total_profit_usd', 0),
        'harmonic_timing': status.get('harmonic_favorable', False),
        'exit_signals': exit_signals,
        'opportunities': [
            {
                'symbol': opp.symbol,
                'direction': opp.action,  # action is 'buy' or 'sell'
                'confidence': opp.confidence,
                'reasoning': ', '.join(opp.reasoning) if opp.reasoning else 'Hunting...',
                'entry_zone': None,  # Not tracked yet
                'target': opp.target_pnl_usd,
                'stop': opp.stop_loss_pct
            }
            for opp in opportunities[:5]  # Top 5 opportunities
        ]
    })


@app.route('/api/orca/opportunities')
def get_orca_opportunities():
    """Get all current Orca hunting opportunities."""
    if not state.orca:
        return jsonify({'opportunities': []})
    
    opps = state.orca.scan_for_opportunities()
    return jsonify({
        'opportunities': [
            {
                'symbol': opp.symbol,
                'direction': opp.action,
                'confidence': round(opp.confidence, 3),
                'reasoning': ', '.join(opp.reasoning) if opp.reasoning else '',
                'target': opp.target_pnl_usd,
                'stop': opp.stop_loss_pct,
                'timestamp': opp.timestamp
            }
            for opp in opps
        ]
    })


def get_dashboard_data():
    """Compile all dashboard data"""
    uptime = int(time.time() - state.start_time)
    hrs, rem = divmod(uptime, 3600)
    mins, secs = divmod(rem, 60)
    
    # Top symbols
    top_symbols = sorted(state.symbol_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Top firms
    top_firms = []
    for firm_name, count in sorted(state.firm_activity.items(), key=lambda x: x[1], reverse=True)[:8]:
        firm_data = state.active_firms.get(firm_name, {})
        top_firms.append({
            'name': firm_name,
            'animal': firm_data.get('animal', '🤖'),
            'count': count,
            'hq': firm_data.get('hq_location', 'Unknown'),
            'capital': firm_data.get('estimated_capital', 0)
        })
    
    # Recent events
    recent = list(state.recent_events)[-25:]
    
    # Queen messages
    queen_msgs = list(state.queen_messages)[-20:]
    
    # Thought stream
    thoughts = list(state.thought_stream)[-15:]
    
    # System activity
    system_activity = [
        {'system': k, 'count': v}
        for k, v in sorted(state.system_thoughts.items(), key=lambda x: x[1], reverse=True)[:8]
    ]
    
    return {
        'uptime': f"{hrs:02d}:{mins:02d}:{secs:02d}",
        'total_bots': state.total_bots,
        'sharks': state.sharks,
        'whales': state.whales,
        'total_volume': state.total_volume,
        'bots_per_minute': (state.total_bots / uptime * 60) if uptime > 0 else 0,
        'threat_level': 'CRITICAL' if state.whales > 8 else 'HIGH' if state.total_bots > 100 else 'MODERATE',
        'top_symbols': [{'symbol': s, 'count': c} for s, c in top_symbols],
        'top_firms': top_firms,
        'recent_events': recent,
        'queen_messages': queen_msgs,
        'firms_active': len(state.active_firms),
        'systems_online': sum(SYSTEMS_STATUS.values()),
        'systems_total': len(SYSTEMS_STATUS),
        'thought_stream': thoughts,
        'system_activity': system_activity,
        'neural_connections': state.neural_connections,
        'signals_decoded': state.signals_decoded,
        'patterns_remembered': state.patterns_remembered,
        'timeline_predictions': state.timeline_predictions,
        'quantum_coherence': round(state.quantum_coherence, 3),
        'planetary_bots_tracked': state.planetary_bots_tracked,
        'warfare_patterns': state.warfare_patterns,
        # Deep Intelligence Data
        'deep_insights': list(state.deep_insights)[-10:],  # Last 10 insights
        'market_thesis': state.market_thesis,
        'deep_intelligence_active': DEEP_INTELLIGENCE_AVAILABLE and state.deep_intelligence is not None,
        # Open Source Data
        'fear_greed_index': state.fear_greed_index,
        'fear_greed_label': state.fear_greed_label,
        'market_data': state.market_data,
        # ThoughtBus & Whale Sonar
        'thought_bus_available': bool(state.thought_bus),
        'auto_tagger_available': bool(state.auto_tagger),
        'whale_signals': state.whale_signals,
        'whale_alerts': state.whale_alerts,
        'enigma_decoded': state.enigma_decoded,
        'trending_coins': state.trending_coins,
        'open_data_points': state.open_data_points,
        'open_data_active': OPEN_DATA_AVAILABLE and state.data_engine is not None,
        # Enhanced Intelligence Feeds
        'news_sentiment': state.news_sentiment,
        'social_sentiment': state.social_sentiment,
        'order_book_bias': state.order_book_bias,
        'spoofing_alerts_count': state.spoofing_alerts_count,
        'exchange_feeds': state.exchange_feeds,
        # Bots summary (top by observed volume)
        'bots_summary': (lambda: (
            sorted([
                {'bot_id': b_id, 'symbol': (p.symbol if hasattr(p, "symbol") else p.get('symbol')), 'owner': (p.owner_name if hasattr(p, 'owner_name') else p.get('owner_name')), 'owner_confidence': (p.owner_confidence if hasattr(p, 'owner_confidence') else p.get('owner_confidence', 0)), 'total_volume_usd': (p.metrics.total_volume_usd if hasattr(p, 'metrics') else p.get('metrics', {}).get('total_volume_usd', 0))}
                for b_id, p in (state.profiler.bot_profiles.items() if state.profiler else state.bot_registry.items())
            ], key=lambda x: x.get('total_volume_usd', 0), reverse=True)[:10]
        ))(),
        'tagged_bots_count': len(state.bot_tags),
        'firm_count': len(state.active_firms),
        # Harmonic Resonance Data for visualizations
        'harmonic_data': get_harmonic_data(),
    }


def get_harmonic_data():
    """Calculate harmonic resonance metrics for dashboard visualizations."""
    import math
    
    PHI = (1 + math.sqrt(5)) / 2  # Golden Ratio 1.618
    SCHUMANN_BASE = 7.83  # Hz
    LOVE_FREQ = 528  # Hz
    
    # Calculate alignment scores based on market activity
    now = time.time()
    activity_factor = min(1.0, state.total_bots / 100) if state.total_bots > 0 else 0.5
    whale_factor = min(1.0, state.whales / 5) if state.whales > 0 else 0.3
    
    # Schumann resonance alignment (more whales = more earth-sync)
    schumann_align = 0.6 + whale_factor * 0.3 + math.sin(now * 0.1) * 0.1
    
    # Golden ratio alignment (based on volume distribution)
    phi_align = 0.618 + activity_factor * 0.2 + math.cos(now * 0.05) * 0.1
    
    # Love frequency resonance (higher during positive sentiment)
    sentiment_boost = (state.fear_greed_index - 50) / 100 if state.fear_greed_index else 0
    love_align = 0.5 + sentiment_boost * 0.3 + abs(math.sin(now * 0.08)) * 0.2
    
    # Market coherence (how aligned all signals are)
    coherence = (schumann_align + phi_align + love_align) / 3
    
    return {
        'schumann': min(1.0, max(0, schumann_align)),
        'phi': min(1.0, max(0, phi_align)),
        'love': min(1.0, max(0, love_align)),
        'coherence': min(1.0, max(0, coherence)),
        'schumann_hz': round(SCHUMANN_BASE * schumann_align, 2),
        'phi_ratio': round(PHI * phi_align, 3),
        'love_hz': round(LOVE_FREQ * love_align),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# SOCKETIO EVENTS
# ═══════════════════════════════════════════════════════════════════════════════
@socketio.on('connect')
def handle_connect():
    """Client connected"""
    emit('state_update', get_dashboard_data())
    emit('systems_status', {'systems': [{'name': k, 'online': v} for k, v in SYSTEMS_STATUS.items()]})
    state.add_queen_message("A new observer joins the omniscient realm.", "info")
    
    # Publish to Thought Bus if available
    if state.thought_bus:
        state.thought_bus.publish(Thought(
            source="QueenDashboard",
            topic="system.observer_joined",
            payload={'message': 'New dashboard observer connected'}
        ))

@socketio.on('disconnect')
def handle_disconnect():
    """Client disconnected"""
    pass

@app.route('/api/test_bot')
def test_bot_detection():
    """Test endpoint to simulate bot detections"""
    return jsonify({
        'status': 'gone',
        'truth_status': 'no_data',
        'reason': 'GENERATED_BOT_EVENTS_RETIRED'
    }), 410
    import random
    
    firms = ['Citadel Securities', 'Two Sigma', 'Jane Street', 'Jump Trading', 'Virtu Financial', 
             'Renaissance Technologies', 'DE Shaw', 'Wintermute', 'Cumberland DRW']
    symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD', 'XRP/USD', 'AVAX/USD', 'LINK/USD']
    sizes = ['WHALE', 'WHALE', 'WHALE', 'SHARK', 'SHARK', 'FISH']
    
    firm_name = None
    firm_data = TRADING_FIRM_SIGNATURES.get(firm_name, {})
    
    event = {
        'symbol': None,
        'volume': None,
        'size': None,
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'firm': firm_name,
        'firm_animal': firm_data.get('animal', '🤖')
    }
    
    # Update state
    state.total_bots += 1
    state.symbol_counts[event['symbol']] += 1
    state.total_volume += event['volume']
    
    if event['size'] == 'SHARK':
        state.sharks += 1
    elif event['size'] in ['WHALE', 'MEGALODON']:
        state.whales += 1
    
    state.firm_activity[firm_name] += 1
    state.active_firms[firm_name] = firm_data
    state.recent_events.append(event)
    
    # Generate Queen commentary
    msgs = generate_queen_commentary(event, {'name': firm_name, 'data': firm_data})
    for msg, level in msgs:
        state.add_queen_message(msg, level)
    
    # 🔊 VOICE: Queen SPEAKS about test bot detection!
    if VOICE_ENGINE_AVAILABLE and queen_voice and event['size'] in ['WHALE', 'MEGALODON']:
        queen_voice.narrate_whale_detection(
            firm=firm_name,
            symbol=event['symbol'],
            volume=event['volume'],
            strategy=firm_data.get('strategies', [None])[0] if firm_data.get('strategies') else None
        )
    
    # Emit to clients
    socketio.emit('new_bot_detection', event)
    socketio.emit('state_update', get_dashboard_data())
    
    return jsonify({'status': 'ok', 'event': event})

@app.route('/api/speak')
def make_queen_speak():
    """Make Queen speak custom text"""
    from flask import request
    text = request.args.get('text', 'I am Queen SERO, watching over the markets.')
    
    if VOICE_ENGINE_AVAILABLE and queen_voice:
        queen_voice.speak_now(text)
        return jsonify({'status': 'ok', 'spoken': text})
    else:
        return jsonify({'status': 'error', 'message': 'Voice engine not available'})

@app.route('/api/wisdom')
def share_wisdom():
    """Make Queen share ancient wisdom"""
    if VOICE_ENGINE_AVAILABLE and queen_voice:
        queen_voice.share_ancient_wisdom()
        return jsonify({'status': 'ok', 'message': 'Wisdom spoken'})
    else:
        return jsonify({'status': 'error', 'message': 'Voice engine not available'})

@app.route('/api/voice_status')
def voice_status():
    """Get voice engine status"""
    return jsonify({
        'available': VOICE_ENGINE_AVAILABLE,
        'speaking': queen_voice.is_speaking if queen_voice else False,
        'queue_size': len(queen_voice.speech_queue) if queen_voice else 0,
        'wisdom_civilizations': list(queen_voice.wisdom_cache.keys()) if queen_voice else []
    })

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    # Start log monitor thread
    monitor_thread = threading.Thread(target=monitor_logs, daemon=True)
    monitor_thread.start()
    
    print("=" * 90)
    print("👑 AUREON QUEEN OMNISCIENT COMMAND CENTER")
    print("=" * 90)
    print(f"🌐 Dashboard URL: http://localhost:5000")
    print(f"📊 Systems Online: {sum(SYSTEMS_STATUS.values())} / {len(SYSTEMS_STATUS)}")
    print(f"🦈 Trading Firms: {len(TRADING_FIRM_SIGNATURES)} profiled")
    print(f"🧠 Thought Bus: {'✅ ACTIVE' if SYSTEMS_STATUS.get('Thought Bus') else '❌ Offline'}")
    print(f"🍄 Mycelium: {'✅ ACTIVE' if SYSTEMS_STATUS.get('Mycelium Network') else '❌ Offline'}")
    print(f"🔐 Enigma: {'✅ ACTIVE' if SYSTEMS_STATUS.get('Enigma Decoder') else '❌ Offline'}")
    print(f"� Voice Engine: {'✅ ACTIVE - Queen can SPEAK!' if VOICE_ENGINE_AVAILABLE else '❌ Offline'}")
    print(f"💬 Queen's Voice: OMNISCIENT")
    print("=" * 90)
    
    # Queen speaks at startup!
    if VOICE_ENGINE_AVAILABLE and queen_voice:
        queen_voice.speak_now("Queen SERO online. All intelligence systems activated. I see everything now.")
    
    # Run Flask app

@app.route('/api/open_data')
def open_data():
    """Get open source data status and feeds"""
    if state.data_engine:
        return jsonify({
            'available': True,
            'stats': state.data_engine.get_stats(),
            'market_data': state.data_engine.get_market_data(),
            'sentiment': state.data_engine.get_sentiment(),
            'whale_alerts': state.data_engine.get_whale_alerts(10),
            'trending': state.data_engine.get_trending(),
            'network': state.data_engine.get_network_data()
        })
    else:
        return jsonify({
            'available': False,
            'message': 'Open source data engine not running'
        })

@app.route('/api/market/<symbol>')
def get_market(symbol):
    """Get specific market data"""
    normalized = symbol.replace('-', '/').upper()
    if state.data_engine:
        data = state.data_engine.get_market_data(normalized)
        if data:
            return jsonify({'status': 'ok', 'data': data})
    return jsonify({'status': 'error', 'message': f'No data for {symbol}'})


# --- Bot & Firm APIs ---------------------------------------------------------
@app.route('/api/bots')
def get_bots():
    """Return list of known bots and tags"""
    bots = []
    if state.profiler:
        for bot_id, profile in state.profiler.bot_profiles.items():
            d = profile.to_dict()
            d['tag'] = state.bot_tags.get(bot_id)
            bots.append(d)
    else:
        for bot_id, profile in state.bot_registry.items():
            p = dict(profile)
            p['tag'] = state.bot_tags.get(bot_id)
            bots.append(p)
    return jsonify({'status': 'ok', 'bots': bots})


@app.route('/api/bot/<bot_id>')
def get_bot(bot_id):
    """Return a single bot profile and tag"""
    p = state.get_bot_profile(bot_id)
    tag = state.bot_tags.get(bot_id)
    if p:
        return jsonify({'status': 'ok', 'bot': p, 'tag': tag})
    return jsonify({'status': 'error', 'message': f'No data for {bot_id}'})


@app.route('/api/firms')
def get_firms():
    """Return firm intelligence database"""
    firms = {}
    if state.profiler:
        for firm_id, f in state.profiler.firm_intelligence.items():
            firms[firm_id] = f.to_dict()
    else:
        firms = {k: v for k, v in state.active_firms.items()}
    return jsonify({'status': 'ok', 'firms': firms})


@app.route('/api/bot/tag', methods=['POST'])
def api_tag_bot():
    """Tag (bag-and-tag) a bot. JSON: {bot_id, tag, reason, actor} """
    data = request.get_json() or {}
    bot_id = data.get('bot_id')
    tag = data.get('tag')
    reason = data.get('reason', '')
    actor = data.get('actor', 'user')
    if not bot_id or not tag:
        return jsonify({'status': 'error', 'message': 'bot_id and tag required'}), 400
    entry = state.tag_bot(bot_id, tag, reason, actor)
    return jsonify({'status': 'ok', 'tag': entry})


@app.route('/api/map/firms')
def api_map_firms():
    """Return all firm locations for world map"""
    if not GEOCODER_AVAILABLE:
        return jsonify({'status': 'error', 'message': 'Geocoder not available'})
    
    locations = get_all_firm_locations()
    
    # Enrich with activity data
    for loc in locations:
        firm_id = loc['firm_id']
        if state.profiler and firm_id in state.profiler.firm_intelligence:
            firm_intel = state.profiler.firm_intelligence[firm_id]
            loc['total_bots'] = firm_intel.total_bots
            loc['total_volume_usd'] = firm_intel.total_volume_usd
            loc['active'] = firm_intel.total_bots > 0
        else:
            loc['total_bots'] = 0
            loc['total_volume_usd'] = 0
            loc['active'] = False
    
    return jsonify({'status': 'ok', 'firms': locations})


@app.route('/api/map/regions')
def api_map_regions():
    """Return regional summary"""
    if not GEOCODER_AVAILABLE:
        return jsonify({'status': 'error', 'message': 'Geocoder not available'})
    return jsonify({'status': 'ok', 'regions': get_regional_summary()})


@app.route('/api/autotagger/stats')
def api_autotagger_stats():
    """Return auto-tagger statistics"""
    if not AUTO_TAGGER_AVAILABLE or not state.auto_tagger:
        return jsonify({'status': 'error', 'message': 'Auto-tagger not available'})
    return jsonify({'status': 'ok', **state.auto_tagger.get_stats()})


@app.route('/api/news')
def api_news():
    """Return news headlines and sentiment"""
    if not OPEN_DATA_AVAILABLE or not state.data_engine:
        return jsonify({'status': 'error', 'message': 'Data engine not available'})
    return jsonify({'status': 'ok', **state.data_engine.get_news()})


@app.route('/api/social')
def api_social():
    """Return social sentiment from Reddit"""
    if not OPEN_DATA_AVAILABLE or not state.data_engine:
        return jsonify({'status': 'error', 'message': 'Data engine not available'})
    return jsonify({'status': 'ok', 'data': state.data_engine.get_social_sentiment()})


@app.route('/api/orderbook')
def api_orderbook():
    """Return order book analysis"""
    if not OPEN_DATA_AVAILABLE or not state.data_engine:
        return jsonify({'status': 'error', 'message': 'Data engine not available'})
    return jsonify({'status': 'ok', 'books': state.data_engine.get_order_books()})


@app.route('/api/spoofing')
def api_spoofing():
    """Return spoofing/manipulation alerts"""
    if not OPEN_DATA_AVAILABLE or not state.data_engine:
        return jsonify({'status': 'error', 'message': 'Data engine not available'})
    return jsonify({'status': 'ok', 'alerts': state.data_engine.get_spoofing_alerts()})


@app.route('/api/intelligence')
def api_intelligence():
    """Return comprehensive market intelligence"""
    if not OPEN_DATA_AVAILABLE or not state.data_engine:
        return jsonify({'status': 'error', 'message': 'Data engine not available'})
    try:
        intel = state.data_engine.get_market_intelligence()
        return jsonify({'status': 'ok', **intel})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


# ═══════════════════════════════════════════════════════════════════════════════
# DEEP INTELLIGENCE API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/deep_insights')
def api_deep_insights():
    """Return recent deep insights from autonomous thinking"""
    return jsonify({
        'status': 'ok',
        'insights': list(state.deep_insights),
        'market_thesis': state.market_thesis,
        'deep_intelligence_active': DEEP_INTELLIGENCE_AVAILABLE and state.deep_intelligence is not None
    })


@app.route('/api/deep_thesis')
def api_deep_thesis():
    """Return current market thesis"""
    if state.deep_intelligence:
        try:
            thesis = state.deep_intelligence.get_current_thesis()
            return jsonify({'status': 'ok', 'thesis': thesis})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'error', 'message': 'Deep intelligence not available'})


@app.route('/api/firm_explanation/<bot_id>')
def api_firm_explanation(bot_id):
    """Get detailed explanation of firm attribution for a bot"""
    if state.profiler:
        try:
            explanation = state.profiler.get_attribution_explanation(bot_id)
            return jsonify({'status': 'ok', **explanation})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'error', 'message': 'Profiler not available'})


@app.route('/api/learning_stats')
def api_learning_stats():
    """Get attribution learning statistics"""
    if state.profiler:
        try:
            stats = state.profiler.get_learning_stats()
            return jsonify({'status': 'ok', **stats})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'error', 'message': 'Profiler not available'})


@app.route('/api/confirm_attribution', methods=['POST'])
def api_confirm_attribution():
    """Confirm or correct a firm attribution - triggers learning"""
    data = request.json or {}
    bot_id = data.get('bot_id')
    confirmed_firm = data.get('firm')
    correct = data.get('correct', True)
    
    if not bot_id or not confirmed_firm:
        return jsonify({'status': 'error', 'message': 'Missing bot_id or firm'})
    
    if state.profiler:
        try:
            state.profiler.learn_from_attribution(bot_id, confirmed_firm, correct)
            return jsonify({'status': 'ok', 'message': f'Learning from attribution: {confirmed_firm} (correct={correct})'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'error', 'message': 'Profiler not available'})


@app.route('/api/correlations')
def api_correlations():
    """Return detected cross-system correlations"""
    if state.deep_intelligence:
        try:
            correlations = state.deep_intelligence.get_recent_correlations()
            return jsonify({'status': 'ok', 'correlations': correlations})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'error', 'message': 'Deep intelligence not available'})


@app.route('/api/hypotheses')
def api_hypotheses():
    """Return active market hypotheses"""
    if state.deep_intelligence:
        try:
            hypotheses = state.deep_intelligence.get_active_hypotheses()
            return jsonify({'status': 'ok', 'hypotheses': hypotheses})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'error', 'message': 'Deep intelligence not available'})


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    # Start log monitor thread
    monitor_thread = threading.Thread(target=monitor_logs, daemon=True)
    monitor_thread.start()
    
    print("=" * 90)
    print("👑 AUREON QUEEN OMNISCIENT COMMAND CENTER")
    print("=" * 90)
    print(f"🌐 Dashboard URL: http://localhost:5000")
    print(f"📊 Systems Online: {sum(SYSTEMS_STATUS.values())} / {len(SYSTEMS_STATUS)}")
    print(f"🦈 Trading Firms: {len(TRADING_FIRM_SIGNATURES)} profiled")
    print(f"🧠 Thought Bus: {'✅ ACTIVE' if SYSTEMS_STATUS.get('Thought Bus') else '❌ Offline'}")
    print(f"🍄 Mycelium: {'✅ ACTIVE' if SYSTEMS_STATUS.get('Mycelium Network') else '❌ Offline'}")
    print(f"🔐 Enigma: {'✅ ACTIVE' if SYSTEMS_STATUS.get('Enigma Decoder') else '❌ Offline'}")
    print(f"🔊 Voice Engine: {'✅ ACTIVE - Queen can SPEAK!' if VOICE_ENGINE_AVAILABLE else '❌ Offline'}")
    print(f"🌐 Open Data: {'✅ ACTIVE - FREE data flowing!' if OPEN_DATA_AVAILABLE else '❌ Offline'}")
    print(f"🧠 Deep Intelligence: {'✅ ACTIVE - Autonomous Thinking!' if DEEP_INTELLIGENCE_AVAILABLE else '❌ Offline'}")
    print(f"💬 Queen's Voice: OMNISCIENT - The Voice of the Revolution")
    print("=" * 90)
    
    # Queen speaks at startup!
    if VOICE_ENGINE_AVAILABLE and queen_voice:
        queen_voice.speak_now("Queen SERO online. All intelligence systems activated. Open source data feeds connected. I see everything now.")
    
    # Run Flask app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
