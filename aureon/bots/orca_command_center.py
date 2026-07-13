#!/usr/bin/env python3
"""
🦈⚔️🎮 ORCA COMMAND CENTER - THE ONE BIG DASHBOARD 🎮⚔️🦈
═══════════════════════════════════════════════════════════════════════════════

    ██████╗ ██████╗  ██████╗ █████╗      ██████╗███████╗███╗   ██╗████████╗███████╗██████╗ 
   ██╔═══██╗██╔══██╗██╔════╝██╔══██╗    ██╔════╝██╔════╝████╗  ██║╚══██╔══╝██╔════╝██╔══██╗
   ██║   ██║██████╔╝██║     ███████║    ██║     █████╗  ██╔██╗ ██║   ██║   █████╗  ██████╔╝
   ██║   ██║██╔══██╗██║     ██╔══██║    ██║     ██╔══╝  ██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗
   ╚██████╔╝██║  ██║╚██████╗██║  ██║    ╚██████╗███████╗██║ ╚████║   ██║   ███████╗██║  ██║
    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝     ╚═════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝

THE ULTIMATE ORCA HUNTING DASHBOARD - ALL SYSTEMS IN ONE EPIC INTERFACE

Features:
🦈 Live Position Tracking & Kill Status
💰 Real-time P&L with Entry/Exit Analysis
🦈🔍 Predator Detection (Front-Running Detection)
🥷 Stealth Execution Mode Status
🐋 Whale Intelligence & Bot Tracking
📊 Multi-Exchange Status (Alpaca + Kraken)
⚡ Live Trade Execution Feed
🎯 28 Intelligence Systems Status
🔊 Audio Alerts & Victory Sounds
📈 Live Charts & Market Data Streaming

ONE DASHBOARD TO HUNT THEM ALL!

Gary Leckey | January 2026 | THE ORCA HUNTS
═══════════════════════════════════════════════════════════════════════════════
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

# Windows UTF-8 fix (MANDATORY)
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
        if hasattr(sys.stderr, 'buffer') and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from collections import deque, defaultdict
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 🌐 WEB FRAMEWORK
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aiohttp import web
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("⚠️  Install aiohttp for web dashboard: pip install aiohttp")

# ═══════════════════════════════════════════════════════════════════════════════
# 🦈 ORCA SYSTEM IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEMS_STATUS = {}

def safe_import(name: str, module: str, cls: str):
    """Safely import a class, tracking status."""
    try:
        mod = __import__(module, fromlist=[cls])
        SYSTEMS_STATUS[name] = True
        return getattr(mod, cls)
    except Exception as e:
        SYSTEMS_STATUS[name] = False
        logger.debug(f"⚠️  {name}: {e}")
        return None

print("\n🦈 LOADING ORCA COMMAND CENTER SYSTEMS...")

# Core Orca Systems
print("  🔪 Loading Kill Cycle...")
OrcaKillCycle = safe_import('OrcaKillCycle', 'orca_complete_kill_cycle', 'OrcaKillCycle')
OrcaKillExecutor = safe_import('OrcaKillExecutor', 'orca_complete_kill_cycle', 'OrcaKillExecutor')

# Predator & Stealth
print("  🦈🔍 Loading Predator Detection...")
OrcaPredatorDetector = safe_import('PredatorDetection', 'orca_predator_detection', 'OrcaPredatorDetector')

print("  🥷 Loading Stealth Execution...")
OrcaStealthExecution = safe_import('StealthExecution', 'orca_stealth_execution', 'OrcaStealthExecution')

# Exchange Clients
print("  📊 Loading Exchange Clients...")
AlpacaClient = safe_import('Alpaca', 'alpaca_client', 'AlpacaClient')
KrakenClient = safe_import('Kraken', 'kraken_client', 'KrakenClient')

# Intelligence Systems
print("  🧠 Loading Intelligence Systems...")
ProbabilityUltimateIntelligence = safe_import('UltimateIntel', 'probability_ultimate_intelligence', 'ProbabilityUltimateIntelligence')
OrcaIntelligence = safe_import('OrcaIntelligence', 'aureon_orca_intelligence', 'OrcaKillerWhaleIntelligence')
GlobalWaveScanner = safe_import('WaveScanner', 'aureon_global_wave_scanner', 'GlobalWaveScanner')
MoversShakersScanner = safe_import('MoversShakers', 'aureon_movers_shakers_scanner', 'MoversShakersScanner')

# Whale & Bot Tracking
print("  🐋 Loading Whale Intelligence...")
WhaleProfiler = safe_import('WhaleProfiler', 'aureon_whale_profiler_system', 'WhaleProfilerSystem')
BotShapeClassifier = safe_import('BotClassifier', 'aureon_bot_shape_classifier', 'BotShapeClassifier')

# ThoughtBus
print("  💭 Loading ThoughtBus...")
ThoughtBus = safe_import('ThoughtBus', 'aureon_thought_bus', 'ThoughtBus')
get_thought_bus = safe_import('get_thought_bus', 'aureon_thought_bus', 'get_thought_bus')

# Fee & Cost Tracking
print("  💰 Loading Fee Trackers...")
AlpacaFeeTracker = safe_import('FeeTracker', 'alpaca_fee_tracker', 'AlpacaFeeTracker')
CostBasisTracker = safe_import('CostBasis', 'cost_basis_tracker', 'CostBasisTracker')

# Streaming
print("  📡 Loading SSE Client...")
AlpacaSSEClient = safe_import('SSEClient', 'alpaca_sse_client', 'AlpacaSSEClient')

working = sum(1 for v in SYSTEMS_STATUS.values() if v)
total = len(SYSTEMS_STATUS)
print(f"\n✅ ORCA SYSTEMS LOADED: {working}/{total}\n")

# ═══════════════════════════════════════════════════════════════════════════════
# 📊 DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OrcaPosition:
    """Active hunting position."""
    symbol: str
    exchange: str
    side: str
    qty: float
    entry_price: float
    current_price: float
    entry_time: datetime
    unrealized_pnl: float = 0.0
    target_price: float = 0.0
    stop_price: float = 0.0
    status: str = "hunting"  # hunting, profit, danger, killed

@dataclass  
class OrcaKill:
    """Completed kill (closed position)."""
    symbol: str
    exchange: str
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    entry_time: datetime
    exit_time: datetime
    duration_seconds: float
    kill_type: str = "profit"  # profit, stop_loss, timeout

@dataclass
class OrcaStats:
    """Overall Orca hunting statistics."""
    total_kills: int = 0
    successful_kills: int = 0
    failed_kills: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    avg_kill_time: float = 0.0
    best_kill: float = 0.0
    worst_kill: float = 0.0
    active_positions: int = 0
    stealth_mode: str = "normal"
    threat_level: str = "🟢 LOW"
    front_run_detections: int = 0

# ═══════════════════════════════════════════════════════════════════════════════
# 🦈 ORCA COMMAND CENTER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class OrcaCommandCenter:
    """
    The One Big Dashboard for the Orca Hunting System.
    Web-based interface showing all positions, kills, intelligence, and stats.
    """
    
    def __init__(self, port: int = 8888):
        self.port = port
        self.app = web.Application() if AIOHTTP_AVAILABLE else None
        self.websockets: Set[web.WebSocketResponse] = set()
        
        # Core state
        self.positions: Dict[str, OrcaPosition] = {}
        self.kills: List[OrcaKill] = []
        self.stats = OrcaStats()
        self.event_log: deque = deque(maxlen=100)
        
        # Intelligence state
        self.intelligence_signals: deque = deque(maxlen=50)
        self.whale_detections: deque = deque(maxlen=50)
        self.bot_shapes: deque = deque(maxlen=50)
        
        # Predator/Stealth state
        self.predator_detector = OrcaPredatorDetector() if OrcaPredatorDetector else None
        self.stealth_executor = OrcaStealthExecution() if OrcaStealthExecution else None
        self.predator_alerts: deque = deque(maxlen=20)
        
        # Exchange clients
        self.alpaca = None
        self.kraken = None
        self._init_exchanges()
        
        # ThoughtBus subscription
        self.thought_bus = None
        self._init_thought_bus()
        
        # Setup routes
        if self.app:
            self._setup_routes()
    
    def _init_exchanges(self):
        """Initialize exchange clients."""
        try:
            if AlpacaClient:
                self.alpaca = AlpacaClient()
                logger.info("✅ Alpaca connected")
        except Exception as e:
            logger.warning(f"⚠️  Alpaca: {e}")
        
        try:
            if KrakenClient:
                from aureon.exchanges.kraken_client import get_kraken_client
                self.kraken = get_kraken_client()
                logger.info("✅ Kraken connected")
        except Exception as e:
            logger.warning(f"⚠️  Kraken: {e}")
    
    def _init_thought_bus(self):
        """Subscribe to ThoughtBus for intelligence."""
        try:
            if get_thought_bus:
                self.thought_bus = get_thought_bus()
                # Subscribe to key topics
                self.thought_bus.subscribe('whale.*', self._on_whale_thought)
                self.thought_bus.subscribe('bot.*', self._on_bot_thought)
                self.thought_bus.subscribe('signal.*', self._on_signal_thought)
                self.thought_bus.subscribe('orca.*', self._on_orca_thought)
                logger.info("✅ ThoughtBus connected")
        except Exception as e:
            logger.warning(f"⚠️  ThoughtBus: {e}")
    
    def _on_whale_thought(self, thought):
        """Handle whale detection thoughts."""
        self.whale_detections.append({
            'time': datetime.now().isoformat(),
            'topic': thought.topic,
            'data': thought.payload
        })
    
    def _on_bot_thought(self, thought):
        """Handle bot shape thoughts."""
        self.bot_shapes.append({
            'time': datetime.now().isoformat(),
            'topic': thought.topic,
            'data': thought.payload
        })
    
    def _on_signal_thought(self, thought):
        """Handle trading signal thoughts."""
        self.intelligence_signals.append({
            'time': datetime.now().isoformat(),
            'topic': thought.topic,
            'data': thought.payload
        })
    
    def _on_orca_thought(self, thought):
        """Handle Orca-specific thoughts."""
        self.event_log.append({
            'time': datetime.now().isoformat(),
            'type': 'orca',
            'message': str(thought.payload)
        })
    
    def load_json(self, filename):
        """Load JSON file safely."""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _setup_routes(self):
        """Setup web routes."""
        self.app.router.add_get('/', self._handle_index)
        self.app.router.add_get('/ws', self._handle_websocket)
        self.app.router.add_get('/api/status', self._handle_api_status)
        self.app.router.add_get('/api/positions', self._handle_api_positions)
        self.app.router.add_get('/api/kills', self._handle_api_kills)
        self.app.router.add_get('/api/stats', self._handle_api_stats)
        self.app.router.add_get('/api/intelligence', self._handle_api_intelligence)
        self.app.router.add_get('/api/predator', self._handle_api_predator)
        self.app.router.add_post('/api/stealth', self._handle_api_stealth)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🌐 WEB HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def _handle_index(self, request):
        """Serve the main dashboard HTML."""
        return web.Response(text=ORCA_DASHBOARD_HTML, content_type='text/html')
    
    async def _handle_websocket(self, request):
        """Handle WebSocket connections for live updates."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.websockets.add(ws)
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    # Handle client messages
                    data = json.loads(msg.data)
                    if data.get('type') == 'ping':
                        await ws.send_json({'type': 'pong'})
        finally:
            self.websockets.discard(ws)
        
        return ws
    
    async def _handle_api_status(self, request):
        """Return overall system status from live data files."""
        # Load live data from files that War Room writes to
        active_positions = self.load_json('active_position.json')
        pending_validations = self.load_json('7day_pending_validations.json')
        predator_history = self.load_json('predator_detection_history.json')
        
        # Count active positions
        position_count = len(active_positions) if isinstance(active_positions, dict) else 0
        
        # Get predator threat level
        threat_level = 'low'
        if predator_history and isinstance(predator_history, dict):
            predators = predator_history.get('predators', {})
            if predators:
                # Check if any predator has critical threat
                for p_data in predators.values():
                    if isinstance(p_data, dict) and p_data.get('threat_level') == 'critical':
                        threat_level = 'critical'
                        break
                else:
                    threat_level = 'medium'
        
        status = {
            'timestamp': datetime.now().isoformat(),
            'systems': SYSTEMS_STATUS,
            'exchanges': {
                'alpaca': self.alpaca is not None,
                'kraken': self.kraken is not None
            },
            'active_positions': position_count,
            'pending_validations': len(pending_validations) if isinstance(pending_validations, dict) else 0,
            'stealth_mode': self.stats.stealth_mode,
            'threat_level': threat_level
        }
        return web.json_response(status)
    
    async def _handle_api_positions(self, request):
        """Return active positions from live data file."""
        active_positions = self.load_json('active_position.json')
        
        if not isinstance(active_positions, dict):
            return web.json_response({'positions': []})
        
        # Convert to list format expected by frontend
        positions = []
        for symbol, pos_data in active_positions.items():
            if isinstance(pos_data, dict):
                position = {
                    'symbol': symbol,
                    'exchange': pos_data.get('exchange', 'unknown'),
                    'entry_price': pos_data.get('entry_price', 0),
                    'current_price': pos_data.get('current_price', pos_data.get('entry_price', 0)),
                    'quantity': pos_data.get('quantity', 0),
                    'pnl': pos_data.get('pnl', 0),
                    'entry_time': pos_data.get('entry_time', datetime.now().isoformat()),
                    'firm': pos_data.get('firm', 'unknown')
                }
                positions.append(position)
        
        return web.json_response({'positions': positions})
    
    async def _handle_api_kills(self, request):
        """Return kill history - currently returns empty as War Room doesn't persist kills."""
        # TODO: War Room doesn't save kills to file yet, so return empty for now
        return web.json_response({'kills': []})
    
    async def _handle_api_stats(self, request):
        """Return hunting statistics."""
        return web.json_response(asdict(self.stats))
    
    async def _handle_api_intelligence(self, request):
        """Return intelligence feeds from live data files."""
        predator_history = self.load_json('predator_detection_history.json')
        
        # Extract intelligence data
        signals = []
        whales = []
        bots = []
        events = []
        
        if predator_history and isinstance(predator_history, dict):
            # Add predator signals
            predators = predator_history.get('predators', {})
            for firm_id, p_data in predators.items():
                if isinstance(p_data, dict):
                    signals.append({
                        'type': 'predator_detected',
                        'firm': firm_id,
                        'threat_level': p_data.get('threat_level', 'unknown'),
                        'last_seen': p_data.get('last_seen', 0),
                        'times_detected': p_data.get('times_detected', 0)
                    })
                    whales.append({
                        'firm': firm_id,
                        'score': p_data.get('stalking_score', 0),
                        'symbols': p_data.get('symbols_targeted', [])
                    })
        
        return web.json_response({
            'signals': signals,
            'whales': whales,
            'bots': bots,
            'events': events
        })
    
    async def _handle_api_predator(self, request):
        """Return predator detection status."""
        if not self.predator_detector:
            return web.json_response({'error': 'Predator detection not available'})
        
        report = self.predator_detector.generate_hunting_report()
        # Get top predator from the list (top_predators is a list of PredatorProfile)
        top_predator_name = 'None'
        if report.top_predators:
            p = report.top_predators[0]
            top_predator_name = p.firm_name if hasattr(p, 'firm_name') else str(p)
        
        return web.json_response({
            'threat_level': report.threat_level,
            'front_run_rate': report.front_run_rate,
            'top_predator': top_predator_name,
            'decay_alert': report.strategy_decay_alert,
            'recommendations': report.recommendations,
            'alerts': list(self.predator_alerts)
        })
    
    async def _handle_api_stealth(self, request):
        """Set stealth mode."""
        if not self.stealth_executor:
            return web.json_response({'error': 'Stealth execution not available'})
        
        data = await request.json()
        mode = data.get('mode', 'normal')
        
        # Update the config directly (stealth_mode is in config)
        self.stealth_executor.config.stealth_mode = mode
        
        # Adjust settings based on mode
        if mode == 'normal':
            self.stealth_executor.config.min_delay_ms = 50
            self.stealth_executor.config.max_delay_ms = 500
            self.stealth_executor.config.split_threshold_usd = 50.0
        elif mode == 'aggressive':
            self.stealth_executor.config.min_delay_ms = 100
            self.stealth_executor.config.max_delay_ms = 800
            self.stealth_executor.config.split_threshold_usd = 25.0
        elif mode == 'paranoid':
            self.stealth_executor.config.min_delay_ms = 200
            self.stealth_executor.config.max_delay_ms = 1500
            self.stealth_executor.config.split_threshold_usd = 15.0
        
        self.stats.stealth_mode = mode
        return web.json_response({'mode': mode, 'status': 'ok'})
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 📡 LIVE UPDATES
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def broadcast(self, data: dict):
        """Broadcast data to all connected WebSocket clients."""
        if not self.websockets:
            return
        
        message = json.dumps(data)
        dead = set()
        
        for ws in self.websockets:
            try:
                await ws.send_str(message)
            except Exception:
                dead.add(ws)
        
        self.websockets -= dead
    
    async def _update_loop(self):
        """Main update loop - refreshes data and broadcasts."""
        while True:
            try:
                # Update positions from exchanges
                await self._refresh_positions()
                
                # Update stats
                self._calculate_stats()
                
                # Check predator detection
                if self.predator_detector:
                    report = self.predator_detector.generate_hunting_report()
                    self.stats.threat_level = report.threat_level
                    self.stats.front_run_detections = int(report.front_run_rate * 100)
                    
                    # Auto-escalate stealth if needed
                    if self.stealth_executor:
                        if '🔴' in report.threat_level:
                            self.stealth_executor.set_paranoid_mode()
                            self.stats.stealth_mode = 'paranoid'
                        elif '🟠' in report.threat_level:
                            self.stealth_executor.set_aggressive_mode()
                            self.stats.stealth_mode = 'aggressive'
                
                # Broadcast update
                await self.broadcast({
                    'type': 'update',
                    'timestamp': datetime.now().isoformat(),
                    'positions': [asdict(p) for p in self.positions.values()],
                    'stats': asdict(self.stats),
                    'events': list(self.event_log)[-10:]
                })
                
            except Exception as e:
                logger.error(f"Update error: {e}")
            
            await asyncio.sleep(1)  # 1-second updates
    
    async def _refresh_positions(self):
        """Refresh positions from exchanges."""
        # Alpaca positions
        if self.alpaca:
            try:
                alpaca_positions = self.alpaca.get_all_positions()
                for pos in alpaca_positions:
                    symbol = pos.get('symbol', '')
                    if symbol:
                        self.positions[f"alpaca:{symbol}"] = OrcaPosition(
                            symbol=symbol,
                            exchange='alpaca',
                            side=pos.get('side', 'long'),
                            qty=float(pos.get('qty', 0)),
                            entry_price=float(pos.get('avg_entry_price', 0)),
                            current_price=float(pos.get('current_price', 0)),
                            entry_time=datetime.now(),
                            unrealized_pnl=float(pos.get('unrealized_pl', 0)),
                            status='hunting' if float(pos.get('unrealized_pl', 0)) >= 0 else 'danger'
                        )
            except Exception as e:
                logger.debug(f"Alpaca refresh: {e}")
        
        # Kraken positions (if available)
        if self.kraken:
            try:
                kraken_positions = self.kraken.get_open_positions()
                for pos_id, pos in kraken_positions.items():
                    symbol = pos.get('pair', '')
                    if symbol:
                        self.positions[f"kraken:{symbol}"] = OrcaPosition(
                            symbol=symbol,
                            exchange='kraken',
                            side=pos.get('type', 'long'),
                            qty=float(pos.get('vol', 0)),
                            entry_price=float(pos.get('cost', 0)),
                            current_price=float(pos.get('value', 0)),
                            entry_time=datetime.now(),
                            unrealized_pnl=float(pos.get('net', 0)),
                            status='hunting'
                        )
            except Exception as e:
                logger.debug(f"Kraken refresh: {e}")
        
        self.stats.active_positions = len(self.positions)
    
    def _calculate_stats(self):
        """Calculate overall statistics."""
        if not self.kills:
            return
        
        self.stats.total_kills = len(self.kills)
        self.stats.successful_kills = sum(1 for k in self.kills if k.pnl > 0)
        self.stats.failed_kills = sum(1 for k in self.kills if k.pnl <= 0)
        self.stats.total_pnl = sum(k.pnl for k in self.kills)
        self.stats.win_rate = (self.stats.successful_kills / self.stats.total_kills * 100) if self.stats.total_kills > 0 else 0
        self.stats.avg_kill_time = sum(k.duration_seconds for k in self.kills) / len(self.kills)
        self.stats.best_kill = max(k.pnl for k in self.kills)
        self.stats.worst_kill = min(k.pnl for k in self.kills)
    
    def add_kill(self, kill: OrcaKill):
        """Record a completed kill."""
        self.kills.append(kill)
        self._calculate_stats()
        
        # Log event
        emoji = "🎯" if kill.pnl > 0 else "💀"
        self.event_log.append({
            'time': datetime.now().isoformat(),
            'type': 'kill',
            'message': f"{emoji} {kill.symbol} | P&L: ${kill.pnl:.2f}"
        })
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🚀 RUN
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def start(self):
        """Start the command center."""
        if not AIOHTTP_AVAILABLE:
            print("❌ aiohttp required. Install with: pip install aiohttp")
            return
        
        # Start update loop
        asyncio.create_task(self._update_loop())
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   🦈⚔️  ORCA COMMAND CENTER ONLINE  ⚔️🦈                                       ║
║                                                                               ║
║   Dashboard: http://localhost:{self.port}                                        ║
║   WebSocket: ws://localhost:{self.port}/ws                                       ║
║                                                                               ║
║   Systems: {working}/{total} online                                                 ║
║   Exchanges: Alpaca {'✅' if self.alpaca else '❌'} | Kraken {'✅' if self.kraken else '❌'}                              ║
║   Predator Detection: {'✅' if self.predator_detector else '❌'}                                             ║
║   Stealth Execution: {'✅' if self.stealth_executor else '❌'}                                              ║
║                                                                               ║
║   THE HUNT BEGINS! 🔪                                                         ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        # Keep running
        while True:
            await asyncio.sleep(3600)


# ═══════════════════════════════════════════════════════════════════════════════
# 🎨 DASHBOARD HTML
# ═══════════════════════════════════════════════════════════════════════════════

ORCA_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🦈 ORCA COMMAND CENTER</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%);
            color: #00ff88;
            font-family: 'Courier New', monospace;
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        .header {
            background: linear-gradient(90deg, #000, #0a1628, #000);
            border-bottom: 2px solid #00ff88;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .logo {
            font-size: 28px;
            font-weight: bold;
            text-shadow: 0 0 20px #00ff88;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        .status-bar {
            display: flex;
            gap: 20px;
            font-size: 14px;
        }
        
        .status-item {
            padding: 5px 15px;
            background: rgba(0, 255, 136, 0.1);
            border: 1px solid #00ff88;
            border-radius: 5px;
        }
        
        .status-item.danger {
            border-color: #ff4444;
            color: #ff4444;
            background: rgba(255, 68, 68, 0.1);
        }
        
        .status-item.warning {
            border-color: #ffaa00;
            color: #ffaa00;
            background: rgba(255, 170, 0, 0.1);
        }
        
        .main {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            padding: 15px;
        }
        
        .panel {
            background: rgba(0, 20, 40, 0.8);
            border: 1px solid #00ff88;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.2);
        }
        
        .panel-header {
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #00ff8844;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .panel.wide {
            grid-column: span 2;
        }
        
        .panel.tall {
            grid-row: span 2;
        }
        
        .panel.full {
            grid-column: span 3;
        }
        
        /* Stats Panel */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        
        .stat-box {
            background: rgba(0, 255, 136, 0.05);
            border: 1px solid #00ff8844;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .stat-value.positive { color: #00ff88; }
        .stat-value.negative { color: #ff4444; }
        .stat-value.warning { color: #ffaa00; }
        
        .stat-label {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
        }
        
        /* Positions Table */
        .positions-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .positions-table th,
        .positions-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #00ff8822;
        }
        
        .positions-table th {
            color: #00ff88;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 11px;
        }
        
        .positions-table tr:hover {
            background: rgba(0, 255, 136, 0.1);
        }
        
        .pnl-positive { color: #00ff88; }
        .pnl-negative { color: #ff4444; }
        
        /* Kill Feed */
        .kill-feed {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .kill-item {
            padding: 10px;
            margin-bottom: 8px;
            background: rgba(0, 255, 136, 0.05);
            border-left: 3px solid #00ff88;
            border-radius: 0 5px 5px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .kill-item.loss {
            border-left-color: #ff4444;
            background: rgba(255, 68, 68, 0.05);
        }
        
        /* Predator Panel */
        .threat-indicator {
            font-size: 48px;
            text-align: center;
            margin: 20px 0;
            animation: threat-pulse 1s infinite;
        }
        
        @keyframes threat-pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        .predator-stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        
        .predator-stat {
            background: rgba(255, 68, 68, 0.1);
            border: 1px solid #ff444444;
            border-radius: 5px;
            padding: 10px;
            text-align: center;
        }
        
        /* Stealth Panel */
        .stealth-modes {
            display: flex;
            gap: 10px;
            margin: 15px 0;
        }
        
        .stealth-btn {
            flex: 1;
            padding: 15px;
            border: 2px solid #00ff88;
            background: transparent;
            color: #00ff88;
            cursor: pointer;
            border-radius: 5px;
            font-family: inherit;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .stealth-btn:hover {
            background: rgba(0, 255, 136, 0.2);
        }
        
        .stealth-btn.active {
            background: #00ff88;
            color: #000;
        }
        
        .stealth-btn.aggressive {
            border-color: #ffaa00;
            color: #ffaa00;
        }
        
        .stealth-btn.aggressive.active {
            background: #ffaa00;
            color: #000;
        }
        
        .stealth-btn.paranoid {
            border-color: #ff4444;
            color: #ff4444;
        }
        
        .stealth-btn.paranoid.active {
            background: #ff4444;
            color: #000;
        }
        
        /* Event Log */
        .event-log {
            max-height: 200px;
            overflow-y: auto;
            font-size: 12px;
        }
        
        .event-item {
            padding: 5px 10px;
            border-bottom: 1px solid #00ff8811;
        }
        
        .event-time {
            color: #666;
            margin-right: 10px;
        }
        
        /* Intelligence Panel */
        .intel-list {
            max-height: 250px;
            overflow-y: auto;
        }
        
        .intel-item {
            padding: 8px;
            margin-bottom: 5px;
            background: rgba(0, 100, 200, 0.1);
            border-left: 3px solid #0088ff;
            border-radius: 0 5px 5px 0;
            font-size: 12px;
        }
        
        /* Systems Grid */
        .systems-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
        }
        
        .system-item {
            padding: 8px;
            background: rgba(0, 255, 136, 0.1);
            border: 1px solid #00ff8844;
            border-radius: 5px;
            font-size: 11px;
            text-align: center;
        }
        
        .system-item.offline {
            background: rgba(255, 68, 68, 0.1);
            border-color: #ff444444;
            color: #ff4444;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #0a0a0a;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #00ff8844;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #00ff88;
        }
        
        /* Connection Status */
        .connection-status {
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 10px 20px;
            background: rgba(0, 0, 0, 0.8);
            border: 1px solid #00ff88;
            border-radius: 5px;
            font-size: 12px;
        }
        
        .connection-status.disconnected {
            border-color: #ff4444;
            color: #ff4444;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🦈⚔️ ORCA COMMAND CENTER ⚔️🦈</div>
        <div class="status-bar">
            <div class="status-item" id="threat-status">THREAT: 🟢 LOW</div>
            <div class="status-item" id="stealth-status">STEALTH: NORMAL</div>
            <div class="status-item" id="positions-count">POSITIONS: 0</div>
            <div class="status-item" id="pnl-total">P&L: $0.00</div>
        </div>
    </div>
    
    <div class="main">
        <!-- Stats Panel -->
        <div class="panel">
            <div class="panel-header">📊 HUNTING STATS</div>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-value positive" id="total-kills">0</div>
                    <div class="stat-label">Total Kills</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="win-rate">0%</div>
                    <div class="stat-label">Win Rate</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value positive" id="best-kill">$0</div>
                    <div class="stat-label">Best Kill</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value negative" id="worst-kill">$0</div>
                    <div class="stat-label">Worst Kill</div>
                </div>
            </div>
        </div>
        
        <!-- Predator Detection -->
        <div class="panel">
            <div class="panel-header">🦈🔍 PREDATOR DETECTION</div>
            <div class="threat-indicator" id="threat-emoji">🟢</div>
            <div class="predator-stats">
                <div class="predator-stat">
                    <div class="stat-value" id="front-run-rate">0%</div>
                    <div class="stat-label">Front-Run Rate</div>
                </div>
                <div class="predator-stat">
                    <div class="stat-value" id="top-predator">None</div>
                    <div class="stat-label">Top Predator</div>
                </div>
            </div>
        </div>
        
        <!-- Stealth Mode -->
        <div class="panel">
            <div class="panel-header">🥷 STEALTH MODE</div>
            <div class="stealth-modes">
                <button class="stealth-btn active" id="btn-normal" onclick="setStealthMode('normal')">
                    🟢 NORMAL
                </button>
                <button class="stealth-btn aggressive" id="btn-aggressive" onclick="setStealthMode('aggressive')">
                    🟠 AGGRESSIVE
                </button>
                <button class="stealth-btn paranoid" id="btn-paranoid" onclick="setStealthMode('paranoid')">
                    🔴 PARANOID
                </button>
            </div>
            <div id="stealth-stats">
                <div>Delayed Orders: <span id="delayed-count">0</span></div>
                <div>Split Orders: <span id="split-count">0</span></div>
                <div>Rotated Symbols: <span id="rotated-count">0</span></div>
            </div>
        </div>
        
        <!-- Active Positions -->
        <div class="panel wide">
            <div class="panel-header">
                🎯 ACTIVE HUNTS
                <span id="active-count">(0 positions)</span>
            </div>
            <table class="positions-table">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Exchange</th>
                        <th>Side</th>
                        <th>Qty</th>
                        <th>Entry</th>
                        <th>Current</th>
                        <th>P&L</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="positions-body">
                    <tr>
                        <td colspan="8" style="text-align: center; color: #666;">No active positions</td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <!-- Kill Feed -->
        <div class="panel">
            <div class="panel-header">🔪 KILL FEED</div>
            <div class="kill-feed" id="kill-feed">
                <div class="kill-item">
                    <span>🎯 Awaiting first kill...</span>
                </div>
            </div>
        </div>
        
        <!-- Intelligence Feed -->
        <div class="panel">
            <div class="panel-header">🧠 INTELLIGENCE</div>
            <div class="intel-list" id="intel-feed">
                <div class="intel-item">🔍 Scanning markets...</div>
            </div>
        </div>
        
        <!-- Systems Status -->
        <div class="panel">
            <div class="panel-header">⚡ SYSTEMS</div>
            <div class="systems-grid" id="systems-grid">
                <!-- Populated by JS -->
            </div>
        </div>
        
        <!-- Event Log -->
        <div class="panel full">
            <div class="panel-header">📜 EVENT LOG</div>
            <div class="event-log" id="event-log">
                <div class="event-item">
                    <span class="event-time">--:--:--</span>
                    <span>🦈 Orca Command Center initialized</span>
                </div>
            </div>
        </div>
    </div>
    
    <div class="connection-status" id="connection-status">
        🟢 CONNECTED
    </div>
    
    <script>
        let ws = null;
        let reconnectAttempts = 0;
        
        function connect() {
            const wsUrl = `ws://${window.location.host}/ws`;
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                console.log('WebSocket connected');
                document.getElementById('connection-status').textContent = '🟢 CONNECTED';
                document.getElementById('connection-status').classList.remove('disconnected');
                reconnectAttempts = 0;
                
                // Start ping
                setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({type: 'ping'}));
                    }
                }, 30000);
            };
            
            ws.onclose = () => {
                console.log('WebSocket disconnected');
                document.getElementById('connection-status').textContent = '🔴 DISCONNECTED';
                document.getElementById('connection-status').classList.add('disconnected');
                
                // Reconnect
                reconnectAttempts++;
                setTimeout(connect, Math.min(5000 * reconnectAttempts, 30000));
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleUpdate(data);
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }
        
        function handleUpdate(data) {
            if (data.type === 'pong') return;
            
            if (data.type === 'update') {
                updatePositions(data.positions || []);
                updateStats(data.stats || {});
                updateEvents(data.events || []);
            }
        }
        
        function updatePositions(positions) {
            const tbody = document.getElementById('positions-body');
            document.getElementById('active-count').textContent = `(${positions.length} positions)`;
            document.getElementById('positions-count').textContent = `POSITIONS: ${positions.length}`;
            
            if (positions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: #666;">No active positions</td></tr>';
                return;
            }
            
            tbody.innerHTML = positions.map(p => `
                <tr>
                    <td>${p.symbol}</td>
                    <td>${p.exchange}</td>
                    <td>${p.side}</td>
                    <td>${p.qty.toFixed(4)}</td>
                    <td>$${p.entry_price.toFixed(4)}</td>
                    <td>$${p.current_price.toFixed(4)}</td>
                    <td class="${p.unrealized_pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}">
                        $${p.unrealized_pnl.toFixed(2)}
                    </td>
                    <td>${getStatusEmoji(p.status)}</td>
                </tr>
            `).join('');
        }
        
        function getStatusEmoji(status) {
            switch(status) {
                case 'hunting': return '🎯';
                case 'profit': return '💰';
                case 'danger': return '⚠️';
                case 'killed': return '🔪';
                default: return '❓';
            }
        }
        
        function updateStats(stats) {
            document.getElementById('total-kills').textContent = stats.total_kills || 0;
            document.getElementById('win-rate').textContent = `${(stats.win_rate || 0).toFixed(1)}%`;
            document.getElementById('best-kill').textContent = `$${(stats.best_kill || 0).toFixed(2)}`;
            document.getElementById('worst-kill').textContent = `$${(stats.worst_kill || 0).toFixed(2)}`;
            document.getElementById('pnl-total').textContent = `P&L: $${(stats.total_pnl || 0).toFixed(2)}`;
            
            // Update threat
            document.getElementById('threat-status').textContent = `THREAT: ${stats.threat_level || '🟢 LOW'}`;
            document.getElementById('stealth-status').textContent = `STEALTH: ${(stats.stealth_mode || 'normal').toUpperCase()}`;
            
            // Update threat emoji
            const threatEmoji = document.getElementById('threat-emoji');
            if (stats.threat_level?.includes('🔴')) {
                threatEmoji.textContent = '🔴';
                threatEmoji.style.color = '#ff4444';
            } else if (stats.threat_level?.includes('🟠')) {
                threatEmoji.textContent = '🟠';
                threatEmoji.style.color = '#ffaa00';
            } else {
                threatEmoji.textContent = '🟢';
                threatEmoji.style.color = '#00ff88';
            }
            
            // Update stealth buttons
            const mode = stats.stealth_mode || 'normal';
            document.querySelectorAll('.stealth-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(`btn-${mode}`)?.classList.add('active');
        }
        
        function updateEvents(events) {
            const log = document.getElementById('event-log');
            events.forEach(e => {
                const time = new Date(e.time).toLocaleTimeString();
                const div = document.createElement('div');
                div.className = 'event-item';
                div.innerHTML = `<span class="event-time">${time}</span><span>${e.message}</span>`;
                log.insertBefore(div, log.firstChild);
            });
            
            // Keep only last 50 events
            while (log.children.length > 50) {
                log.removeChild(log.lastChild);
            }
        }
        
        async function setStealthMode(mode) {
            try {
                const response = await fetch('/api/stealth', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({mode})
                });
                const data = await response.json();
                console.log('Stealth mode set:', data);
            } catch (error) {
                console.error('Failed to set stealth mode:', error);
            }
        }
        
        async function loadSystems() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                const grid = document.getElementById('systems-grid');
                grid.innerHTML = Object.entries(data.systems || {}).map(([name, online]) => `
                    <div class="system-item ${online ? '' : 'offline'}">
                        ${online ? '✅' : '❌'} ${name}
                    </div>
                `).join('');
            } catch (error) {
                console.error('Failed to load systems:', error);
            }
        }
        
        async function loadPredator() {
            try {
                const response = await fetch('/api/predator');
                const data = await response.json();
                
                document.getElementById('front-run-rate').textContent = `${((data.front_run_rate || 0) * 100).toFixed(1)}%`;
                document.getElementById('top-predator').textContent = data.top_predator || 'None';
            } catch (error) {
                console.error('Failed to load predator data:', error);
            }
        }
        
        // Initialize
        connect();
        loadSystems();
        loadPredator();
        
        // Refresh predator data every 10 seconds
        setInterval(loadPredator, 10000);
    </script>
</body>
</html>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Launch the Orca Command Center."""
    import argparse
    
    parser = argparse.ArgumentParser(description='🦈 Orca Command Center')
    parser.add_argument('--port', type=int, default=8888, help='Web server port (default: 8888)')
    args = parser.parse_args()
    
    print("""
    
    ██████╗ ██████╗  ██████╗ █████╗ 
   ██╔═══██╗██╔══██╗██╔════╝██╔══██╗
   ██║   ██║██████╔╝██║     ███████║
   ██║   ██║██╔══██╗██║     ██╔══██║
   ╚██████╔╝██║  ██║╚██████╗██║  ██║
    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
                                    
    ⚔️ COMMAND CENTER ⚔️
    
    THE HUNT BEGINS!
    
    """)
    
    center = OrcaCommandCenter(port=args.port)
    
    try:
        asyncio.run(center.start())
    except KeyboardInterrupt:
        print("\n\n🦈 Orca Command Center shutting down...")


if __name__ == '__main__':
    main()
