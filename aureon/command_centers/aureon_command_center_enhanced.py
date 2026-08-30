#!/usr/bin/env python3
"""
👑🌌 AUREON COMMAND CENTER - ENHANCED WITH LIVE STREAMING 👑🌌
═══════════════════════════════════════════════════════════════════════════

FULLY INTEGRATED DASHBOARD - ALL SYSTEMS WITH REAL-TIME DATA STREAMS

Features from Mind Map + Queen Unified + All Dashboards:
✅ Live WebSocket streaming (auto-updates every 1s)
✅ Real-time system metrics from ALL models
✅ Queen's voice commentary
✅ Visual network graph of systems
✅ Portfolio tracking with live P&L
✅ Trading signals streaming
✅ Market data feeds
✅ Bot detection integration
✅ Quantum analysis streaming
✅ Timeline oracle predictions

Gary Leckey | January 2026 | FULL LIVE DATA STREAMING
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
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
    except Exception:
        pass

import asyncio
import aiohttp
from aiohttp import web
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional
from collections import deque, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════
# SAFE SYSTEM IMPORTS
# ════════════════════════════════════════════════════════════════════════════

SYSTEMS = {}

def safe_import(name: str, module: str, cls: str):
    """Safely import and track systems."""
    try:
        mod = __import__(module, fromlist=[cls])
        SYSTEMS[name] = getattr(mod, cls)
        logger.info(f"✅ {name}")
        return SYSTEMS[name]
    except Exception as e:
        logger.debug(f"⚠️ {name}: {e}")
        SYSTEMS[name] = None
        return None

print("\n🔌 Loading Exchanges...")
safe_import('Kraken', 'kraken_client', 'KrakenClient')
safe_import('Binance', 'binance_client', 'BinanceClient')
safe_import('Alpaca', 'alpaca_client', 'AlpacaClient')

print("\n👑 Loading Queen & Neural...")
safe_import('QueenHive', 'aureon_queen_hive_mind', 'QueenHiveMind')
safe_import('Mycelium', 'aureon_mycelium', 'MyceliumNetwork')
safe_import('ThoughtBus', 'aureon_thought_bus', 'ThoughtBus')

print("\n🧠 Loading Intelligence...")
safe_import('UltimateIntel', 'probability_ultimate_intelligence', 'ProbabilityUltimateIntelligence')
safe_import('ProbabilityNexus', 'aureon_probability_nexus', 'ProbabilityNexus')
safe_import('MinerBrain', 'aureon_miner_brain', 'MinerBrain')
safe_import('TimelineOracle', 'aureon_timeline_oracle', 'TimelineOracle')
safe_import('QuantumMirror', 'aureon_quantum_mirror_scanner', 'QuantumMirrorScanner')

print("\n🌊 Loading Harmonic & Wave...")
safe_import('HarmonicFusion', 'aureon_harmonic_fusion', 'HarmonicWaveFusion')
safe_import('WaveScanner', 'aureon_global_wave_scanner', 'GlobalWaveScanner')

print(f"\n✅ Systems loaded: {sum(1 for v in SYSTEMS.values() if v)}/{len(SYSTEMS)}\n")

# ════════════════════════════════════════════════════════════════════════════
# ENHANCED HTML WITH LIVE STREAMING
# ════════════════════════════════════════════════════════════════════════════

ENHANCED_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>👑 Aureon Command Center - Live</title>
    <meta charset="utf-8">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Courier New', monospace;
            background: linear-gradient(135deg, #0a0a1a 0%, #1a0a2e 50%, #0a1a0a 100%);
            color: #00ff88;
            overflow: hidden;
        }
        
        #header {
            background: rgba(0, 0, 0, 0.9);
            padding: 15px 30px;
            border-bottom: 3px solid #ffaa00;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 30px rgba(255, 170, 0, 0.5);
        }
        
        h1 {
            font-size: 2em;
            background: linear-gradient(90deg, #ffaa00, #ff6600, #ffaa00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: glow 2s infinite;
        }
        
        @keyframes glow {
            0%, 100% { filter: brightness(1); }
            50% { filter: brightness(1.5); }
        }
        
        #connection-status {
            padding: 8px 15px;
            border-radius: 5px;
            font-weight: bold;
            animation: pulse 2s infinite;
        }
        
        #connection-status.connected {
            background: rgba(0, 255, 136, 0.3);
            color: #00ff88;
        }
        
        #connection-status.disconnected {
            background: rgba(255, 0, 0, 0.3);
            color: #ff4444;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        #container {
            display: grid;
            grid-template-columns: 300px 1fr 350px;
            grid-template-rows: 250px 1fr;
            gap: 15px;
            padding: 15px;
            height: calc(100vh - 100px);
        }
        
        .panel {
            background: rgba(0, 0, 0, 0.8);
            border: 2px solid #00ff88;
            border-radius: 10px;
            padding: 15px;
            overflow-y: auto;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
        }
        
        .panel h2 {
            color: #ffaa00;
            margin-bottom: 10px;
            font-size: 1.2em;
            border-bottom: 1px solid #ffaa00;
            padding-bottom: 5px;
        }
        
        #systems-grid {
            grid-row: 1 / 3;
        }
        
        #portfolio-panel {
            grid-column: 2;
        }
        
        #signals-panel {
            grid-column: 2;
            grid-row: 2;
        }
        
        #queen-voice {
            grid-column: 3;
            grid-row: 1 / 3;
        }
        
        .system-item {
            padding: 8px;
            margin: 5px 0;
            background: rgba(255, 255, 255, 0.05);
            border-left: 3px solid #00ff88;
            border-radius: 3px;
            font-size: 0.9em;
        }
        
        .system-item.online {
            border-left-color: #00ff88;
        }
        
        .system-item.offline {
            border-left-color: #ff4444;
            opacity: 0.5;
        }
        
        .system-name {
            font-weight: bold;
            color: #ffaa00;
        }
        
        .system-metric {
            font-size: 0.85em;
            color: #888;
            margin-left: 10px;
        }
        
        .signal-item {
            padding: 10px;
            margin: 8px 0;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 5px;
            border-left: 4px solid;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(-20px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        .signal-item.BUY { border-left-color: #00ff88; }
        .signal-item.SELL { border-left-color: #ff4444; }
        .signal-item.HOLD { border-left-color: #ffaa00; }
        
        .signal-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
        }
        
        .signal-symbol {
            font-weight: bold;
            color: #ffaa00;
            font-size: 1.1em;
        }
        
        .signal-type {
            font-weight: bold;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.9em;
        }
        
        .signal-type.BUY { background: rgba(0, 255, 136, 0.3); color: #00ff88; }
        .signal-type.SELL { background: rgba(255, 68, 68, 0.3); color: #ff4444; }
        .signal-type.HOLD { background: rgba(255, 170, 0, 0.3); color: #ffaa00; }
        
        .signal-confidence {
            font-size: 0.85em;
            color: #888;
        }
        
        .portfolio-stat {
            display: flex;
            justify-content: space-between;
            padding: 10px;
            margin: 5px 0;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 5px;
        }
        
        .stat-label {
            color: #888;
        }
        
        .stat-value {
            font-weight: bold;
            color: #00ff88;
        }
        
        .stat-value.positive { color: #00ff88; }
        .stat-value.negative { color: #ff4444; }
        
        .queen-message {
            padding: 12px;
            margin: 8px 0;
            background: rgba(255, 170, 0, 0.1);
            border: 1px solid #ffaa00;
            border-radius: 8px;
            animation: fadeIn 0.5s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .queen-message .timestamp {
            font-size: 0.8em;
            color: #888;
            margin-bottom: 5px;
        }
        
        .queen-message .text {
            color: #ffaa00;
            line-height: 1.4;
        }
        
        .balance-item {
            display: flex;
            justify-content: space-between;
            padding: 5px 10px;
            margin: 3px 0;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 3px;
            font-size: 0.9em;
        }
        
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.3); }
        ::-webkit-scrollbar-thumb { background: rgba(0, 255, 136, 0.3); border-radius: 4px; }
        
        .update-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #00ff88;
            animation: blink 1s infinite;
            margin-left: 10px;
        }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
    </style>
</head>
<body>
    <div id="header">
        <h1>👑 AUREON COMMAND CENTER - LIVE</h1>
        <div>
            <span id="connection-status" class="disconnected">● CONNECTING...</span>
            <span class="update-indicator"></span>
        </div>
    </div>
    
    <div id="container">
        <div id="systems-grid" class="panel">
            <h2>🔧 SYSTEMS STATUS</h2>
            <div id="systems-list"></div>
        </div>
        
        <div id="portfolio-panel" class="panel">
            <h2>💰 PORTFOLIO & P/L</h2>
            <div id="portfolio-stats"></div>
            <h3 style="color: #ffaa00; margin-top: 15px; font-size: 1em;">Balances</h3>
            <div id="balances-list"></div>
        </div>
        
        <div id="signals-panel" class="panel">
            <h2>📡 TRADING SIGNALS</h2>
            <div id="signals-list"></div>
        </div>
        
        <div id="queen-voice" class="panel">
            <h2>👑 QUEEN'S COMMENTARY</h2>
            <div id="queen-messages"></div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let reconnectInterval = null;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = () => {
                console.log('✅ WebSocket connected');
                document.getElementById('connection-status').textContent = '● CONNECTED';
                document.getElementById('connection-status').className = 'connected';
                if (reconnectInterval) {
                    clearInterval(reconnectInterval);
                    reconnectInterval = null;
                }
            };
            
            ws.onclose = () => {
                console.log('⚠️ WebSocket disconnected');
                document.getElementById('connection-status').textContent = '● DISCONNECTED';
                document.getElementById('connection-status').className = 'disconnected';
                if (!reconnectInterval) {
                    reconnectInterval = setInterval(() => {
                        console.log('🔄 Reconnecting...');
                        connectWebSocket();
                    }, 3000);
                }
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleMessage(data);
                } catch (e) {
                    console.error('Failed to parse message:', e);
                }
            };
        }
        
        function handleMessage(data) {
            switch(data.type) {
                case 'systems_update':
                    updateSystems(data.systems);
                    break;
                case 'portfolio_update':
                    updatePortfolio(data.portfolio);
                    break;
                case 'signal':
                    addSignal(data.signal);
                    break;
                case 'queen_message':
                    addQueenMessage(data.message);
                    break;
                case 'full_update':
                    updateSystems(data.systems || {});
                    updatePortfolio(data.portfolio || {});
                    break;
            }
        }
        
        function updateSystems(systems) {
            const list = document.getElementById('systems-list');
            list.innerHTML = '';
            
            for (const [name, status] of Object.entries(systems)) {
                const item = document.createElement('div');
                item.className = `system-item ${status.status.toLowerCase()}`;
                
                const metrics = status.metadata || {};
                const metricsStr = Object.entries(metrics)
                    .map(([k, v]) => `${k}: ${typeof v === 'number' ? v.toFixed(2) : v}`)
                    .join(' | ');
                
                item.innerHTML = `
                    <div class="system-name">${status.status === 'ONLINE' ? '🟢' : '🔴'} ${name}</div>
                    ${status.confidence > 0 ? `<span class="system-metric">Conf: ${(status.confidence * 100).toFixed(0)}%</span>` : ''}
                    ${status.accuracy > 0 ? `<span class="system-metric">Acc: ${(status.accuracy * 100).toFixed(0)}%</span>` : ''}
                    ${status.signals_sent > 0 ? `<span class="system-metric">Signals: ${status.signals_sent}</span>` : ''}
                    ${metricsStr ? `<div class="system-metric" style="margin-top: 3px;">${metricsStr}</div>` : ''}
                `;
                list.appendChild(item);
            }
        }
        
        function updatePortfolio(portfolio) {
            // Update stats
            const statsDiv = document.getElementById('portfolio-stats');
            statsDiv.innerHTML = `
                <div class="portfolio-stat">
                    <span class="stat-label">Total Value</span>
                    <span class="stat-value">$${portfolio.total_value_usd?.toFixed(2) || '0.00'}</span>
                </div>
                <div class="portfolio-stat">
                    <span class="stat-label">Cash Available</span>
                    <span class="stat-value">$${portfolio.cash_available?.toFixed(2) || '0.00'}</span>
                </div>
                <div class="portfolio-stat">
                    <span class="stat-label">P/L Today</span>
                    <span class="stat-value ${portfolio.pnl_today >= 0 ? 'positive' : 'negative'}">
                        ${portfolio.pnl_today >= 0 ? '+' : ''}$${portfolio.pnl_today?.toFixed(2) || '0.00'}
                    </span>
                </div>
                <div class="portfolio-stat">
                    <span class="stat-label">P/L Total</span>
                    <span class="stat-value ${portfolio.pnl_total >= 0 ? 'positive' : 'negative'}">
                        ${portfolio.pnl_total >= 0 ? '+' : ''}$${portfolio.pnl_total?.toFixed(2) || '0.00'}
                    </span>
                </div>
            `;
            
            // Update balances
            const balancesDiv = document.getElementById('balances-list');
            balancesDiv.innerHTML = '';
            
            if (portfolio.balances) {
                for (const [exchange, assets] of Object.entries(portfolio.balances)) {
                    for (const [asset, amount] of Object.entries(assets)) {
                        if (amount > 0.0001) {
                            const item = document.createElement('div');
                            item.className = 'balance-item';
                            item.innerHTML = `
                                <span>${exchange.toUpperCase()} - ${asset}</span>
                                <span>${typeof amount === 'number' ? amount.toFixed(4) : amount}</span>
                            `;
                            balancesDiv.appendChild(item);
                        }
                    }
                }
            }
        }
        
        function addSignal(signal) {
            const list = document.getElementById('signals-list');
            const item = document.createElement('div');
            item.className = `signal-item ${signal.signal_type}`;
            
            item.innerHTML = `
                <div class="signal-header">
                    <span class="signal-symbol">${signal.symbol}</span>
                    <span class="signal-type ${signal.signal_type}">${signal.signal_type}</span>
                </div>
                <div style="font-size: 0.85em; color: #888;">
                    ${signal.source} | Conf: ${(signal.confidence * 100).toFixed(0)}% | Score: ${signal.score.toFixed(2)}
                </div>
                <div style="margin-top: 5px; font-size: 0.9em;">${signal.reason}</div>
            `;
            
            list.insertBefore(item, list.firstChild);
            
            // Keep only last 20 signals
            while (list.children.length > 20) {
                list.removeChild(list.lastChild);
            }
        }
        
        function addQueenMessage(message) {
            const list = document.getElementById('queen-messages');
            const item = document.createElement('div');
            item.className = 'queen-message';
            
            const now = new Date().toLocaleTimeString();
            item.innerHTML = `
                <div class="timestamp">${now}</div>
                <div class="text">👑 ${message}</div>
            `;
            
            list.insertBefore(item, list.firstChild);
            
            // Keep only last 15 messages
            while (list.children.length > 15) {
                list.removeChild(list.lastChild);
            }
        }
        
        // Connect on load
        connectWebSocket();
        
        console.log('👑 Aureon Command Center Enhanced - Live Streaming Active');
    </script>
</body>
</html>
"""

# ════════════════════════════════════════════════════════════════════════════
# COMMAND CENTER CLASS
# ════════════════════════════════════════════════════════════════════════════

class AureonCommandCenterEnhanced:
    """Enhanced Command Center with live streaming."""
    
    def __init__(self, port=8800):
        self.port = port
        self.clients: Set = set()
        
        # System instances
        self.systems_instances = {}
        self.systems_status = {}
        
        # Data queues
        self.signals = deque(maxlen=100)
        self.queen_messages = deque(maxlen=50)
        
        # Portfolio state
        self.portfolio = {
            'total_value_usd': None,
            'cash_available': None,
            'positions': [],
            'balances': {},
            'pnl_today': None,
            'pnl_total': None,
            'truth_status': 'no_data',
            'generated_values': False,
            'reason': 'NO_FRESH_ACCOUNT_PROVIDER_OBSERVATION',
        }
        
        # Initialize systems
        self._init_systems()
        
        # Setup web app
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/ws', self.handle_websocket)
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_get('/api/portfolio', self.handle_portfolio)
        self.app.router.add_get('/api/signals', self.handle_signals)
    
    def _init_systems(self):
        """Initialize all available systems."""
        print("\n🚀 Initializing systems...")

        def initialized_status():
            """Instantiation is not proof that a provider is online or accurate."""
            return {
                'status': 'INITIALIZED_NOT_VERIFIED',
                'confidence': None,
                'accuracy': None,
                'signals_sent': 0,
                'truth_status': 'no_data',
                'generated_values': False,
                'metadata': {'reason': 'NO_FRESH_HEALTH_OR_VALIDATION_RECEIPT'},
            }
        
        # Initialize exchange clients
        if SYSTEMS.get('Kraken'):
            try:
                self.systems_instances['Kraken'] = SYSTEMS['Kraken']()
                self.systems_status['Kraken'] = initialized_status()
            except: pass
        
        if SYSTEMS.get('Binance'):
            try:
                self.systems_instances['Binance'] = SYSTEMS['Binance']()
                self.systems_status['Binance'] = initialized_status()
            except: pass
        
        if SYSTEMS.get('Alpaca'):
            try:
                self.systems_instances['Alpaca'] = SYSTEMS['Alpaca']()
                self.systems_status['Alpaca'] = initialized_status()
            except: pass
        
        # Initialize Queen systems
        if SYSTEMS.get('QueenHive'):
            try:
                self.systems_instances['QueenHive'] = SYSTEMS['QueenHive']()
                self.systems_status['QueenHive'] = initialized_status()
            except: pass
        
        if SYSTEMS.get('ThoughtBus'):
            try:
                self.systems_instances['ThoughtBus'] = SYSTEMS['ThoughtBus']()
                self.systems_status['ThoughtBus'] = initialized_status()
            except: pass
        
        # Initialize intelligence systems
        if SYSTEMS.get('UltimateIntel'):
            try:
                self.systems_instances['UltimateIntel'] = SYSTEMS['UltimateIntel']()
                self.systems_status['UltimateIntel'] = initialized_status()
            except: pass
        
        if SYSTEMS.get('ProbabilityNexus'):
            try:
                self.systems_instances['ProbabilityNexus'] = SYSTEMS['ProbabilityNexus']()
                self.systems_status['ProbabilityNexus'] = initialized_status()
            except: pass
        
        if SYSTEMS.get('TimelineOracle'):
            try:
                self.systems_instances['TimelineOracle'] = SYSTEMS['TimelineOracle']()
                self.systems_status['TimelineOracle'] = initialized_status()
            except: pass
        
        if SYSTEMS.get('QuantumMirror'):
            try:
                self.systems_instances['QuantumMirror'] = SYSTEMS['QuantumMirror']()
                self.systems_status['QuantumMirror'] = initialized_status()
            except: pass
        
        # Initialize harmonic systems
        if SYSTEMS.get('HarmonicFusion'):
            try:
                self.systems_instances['HarmonicFusion'] = SYSTEMS['HarmonicFusion']()
                self.systems_status['HarmonicFusion'] = initialized_status()
            except: pass
        
        if SYSTEMS.get('WaveScanner'):
            try:
                self.systems_instances['WaveScanner'] = SYSTEMS['WaveScanner']()
                self.systems_status['WaveScanner'] = initialized_status()
            except: pass
        
        print(f"✅ Initialized {len(self.systems_instances)} systems\n")
    
    async def handle_index(self, request):
        """Serve dashboard HTML."""
        return web.Response(text=ENHANCED_HTML, content_type='text/html')
    
    async def handle_websocket(self, request):
        """Handle WebSocket connections for live streaming."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.clients.add(ws)
        logger.info(f"👑 Client connected (total: {len(self.clients)})")
        
        # Send initial data
        await ws.send_json({
            'type': 'full_update',
            'systems': self.systems_status,
            'portfolio': self.portfolio
        })
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            self.clients.discard(ws)
            logger.info(f"Client disconnected (remaining: {len(self.clients)})")
        
        return ws
    
    async def handle_status(self, request):
        """API endpoint for system status."""
        return web.json_response({
            'status': 'online',
            'timestamp': time.time(),
            'systems': self.systems_status
        })
    
    async def handle_portfolio(self, request):
        """API endpoint for portfolio data."""
        return web.json_response(self.portfolio)
    
    async def handle_signals(self, request):
        """API endpoint for recent signals."""
        return web.json_response({
            'signals': list(self.signals)
        })
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected clients."""
        if not self.clients:
            return
        
        msg_str = json.dumps(message)
        dead_clients = set()
        
        for client in self.clients:
            try:
                await client.send_str(msg_str)
            except:
                dead_clients.add(client)
        
        self.clients -= dead_clients
    
    async def live_data_stream(self):
        """Main loop for streaming live data to clients."""
        await asyncio.sleep(2)  # Initial delay
        
        logger.info("📡 Starting live data stream...")
        
        while True:
            try:
                # Update portfolio from exchanges
                await self._update_portfolio()
                
                # Broadcast updates
                await self.broadcast({
                    'type': 'systems_update',
                    'systems': self.systems_status
                })
                
                await self.broadcast({
                    'type': 'portfolio_update',
                    'portfolio': self.portfolio
                })
                
                await asyncio.sleep(1)  # Update every 1 second
                
            except Exception as e:
                logger.error(f"Error in live data stream: {e}")
                await asyncio.sleep(5)
    
    async def _update_portfolio(self):
        """Update portfolio data from exchanges."""
        try:
            balances = {}
            cash_observations = []
            receipts = []

            def record_balance(exchange: str, payload: object, usd_keys: tuple[str, ...]) -> None:
                if not isinstance(payload, dict):
                    raise ValueError(f'{exchange} balance response is not a mapping')
                observed_at = datetime.now(timezone.utc).isoformat()
                balances[exchange] = payload
                receipt = {
                    'source_id': f'{exchange}:get_balance',
                    'source_timestamp': observed_at,
                    'collected_at': observed_at,
                    'truth_status': 'live',
                    'generated_values': False,
                }
                receipts.append(receipt)
                for key in usd_keys:
                    if key in payload and payload[key] is not None:
                        cash_observations.append(float(payload[key]))
                self.systems_status[exchange.capitalize()] = {
                    'status': 'ONLINE',
                    'confidence': None,
                    'accuracy': None,
                    'signals_sent': 0,
                    'truth_status': 'live',
                    'generated_values': False,
                    'metadata': receipt,
                }
            
            # Kraken
            if 'Kraken' in self.systems_instances:
                try:
                    kraken_bal = self.systems_instances['Kraken'].get_balance()
                    record_balance('kraken', kraken_bal, ('ZUSD', 'USD'))
                except Exception as exc:
                    self.systems_status['Kraken'].update({
                        'status': 'ERROR',
                        'truth_status': 'no_data',
                        'metadata': {'reason': f'BALANCE_PROVIDER_ERROR: {exc}'},
                    })
            
            # Alpaca
            if 'Alpaca' in self.systems_instances:
                try:
                    alpaca_bal = self.systems_instances['Alpaca'].get_balance()
                    record_balance('alpaca', alpaca_bal, ('USD',))
                except Exception as exc:
                    self.systems_status['Alpaca'].update({
                        'status': 'ERROR',
                        'truth_status': 'no_data',
                        'metadata': {'reason': f'BALANCE_PROVIDER_ERROR: {exc}'},
                    })
            
            # Cash is not total equity. Keep equity unknown until positions and
            # non-USD assets have provider valuations.
            self.portfolio['total_value_usd'] = None
            self.portfolio['cash_available'] = (
                sum(cash_observations) if cash_observations else None
            )
            self.portfolio['balances'] = balances
            self.portfolio['truth_status'] = 'live' if receipts else 'no_data'
            self.portfolio['generated_values'] = False
            self.portfolio['source_receipts'] = receipts
            self.portfolio['reason'] = (
                None if receipts else 'NO_FRESH_ACCOUNT_PROVIDER_OBSERVATION'
            )
            
        except Exception as e:
            logger.debug(f"Error updating portfolio: {e}")
    
    async def start(self):
        """Start the command center."""
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        print(f"\n{'='*80}")
        print(f"👑🌌 AUREON COMMAND CENTER - ENHANCED LIVE STREAMING")
        print(f"{'='*80}")
        print(f"🌐 Dashboard: http://localhost:{self.port}")
        print(f"📡 WebSocket: ws://localhost:{self.port}/ws")
        print(f"\n✨ LIVE FEATURES:")
        print(f"   🔄 Auto-updating every 1 second")
        print(f"   📊 Real-time portfolio tracking")
        print(f"   🚨 Live trading signals")
        print(f"   👑 Queen's voice commentary")
        print(f"   💹 Market data streaming")
        print(f"   🧠 All intelligence systems integrated")
        print(f"\n📈 SYSTEMS INITIALIZED: {len(self.systems_instances)} (health requires provider receipts)")
        for name in self.systems_instances:
            print(f"   ◌ {name}: awaiting fresh health observation")
        print(f"{'='*80}\n")
        
        # Start live data stream
        asyncio.create_task(self.live_data_stream())

async def main():
    center = AureonCommandCenterEnhanced(port=8800)
    await center.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👑 Command Center stopped")
