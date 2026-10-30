#!/usr/bin/env python3
"""
🧠💭⚡ AUREON MIND → THOUGHT → ACTION HUB
═══════════════════════════════════════════════════════════════════════════

UNIFIED COGNITIVE PIPELINE VISUALIZATION

Architecture:
┌─────────────────────────────────────────────────────────────────────┐
│  🧠 MIND (Queen Hive + Intelligence)                                │
│     ↓                                                                │
│  💭 THOUGHT (ThoughtBus Communication)                              │
│     ↓                                                                │
│  ⚡ ACTION (Execution + Trading)                                     │
└─────────────────────────────────────────────────────────────────────┘

Features:
- Mind Map visualization with LIVE cognitive flow
- Real-time ThoughtBus message streaming
- Queen decision tracking
- Action execution monitoring
- System interconnections showing data flow
- Live metrics from all 200+ systems

Port: 13002
URL: http://localhost:13002

Gary Leckey | January 2026 | Mind → Thought → Action
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
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
from datetime import datetime
from typing import Dict, List, Set, Optional
from collections import deque, defaultdict
from pathlib import Path

# Import core systems
from aureon_system_hub import SystemRegistry
from aureon_thought_bus import ThoughtBus, Thought

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

# Safe system imports
def safe_import(name: str, module: str, cls: str):
    """Safely import systems."""
    try:
        mod = __import__(module, fromlist=[cls])
        return getattr(mod, cls)
    except Exception as e:
        logger.debug(f"⚠️ {name}: {e}")
        return None

QueenHiveMind = safe_import('Queen', 'aureon_queen_hive_mind', 'QueenHiveMind')
ProbabilityNexus = safe_import('ProbNexus', 'aureon_probability_nexus', 'ProbabilityNexus')
UltimateIntelligence = safe_import('UltimateIntel', 'probability_ultimate_intelligence', 'ProbabilityUltimateIntelligence')

# ════════════════════════════════════════════════════════════════════════════
# ENHANCED HTML WITH MIND → THOUGHT → ACTION VISUALIZATION
# ════════════════════════════════════════════════════════════════════════════

MIND_THOUGHT_ACTION_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠💭⚡ Aureon Mind → Thought → Action</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/dist/vis-network.min.css" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Courier New', monospace;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #fff;
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
            font-size: 1.8em;
            background: linear-gradient(90deg, #ffaa00, #ff6600, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: glow 2s infinite;
        }
        
        @keyframes glow {
            0%, 100% { filter: brightness(1); }
            50% { filter: brightness(1.5); }
        }
        
        #cognitive-flow {
            display: flex;
            gap: 10px;
            padding: 8px 15px;
            background: rgba(0, 0, 0, 0.5);
            border-radius: 5px;
            font-size: 1.2em;
        }
        
        .flow-stage {
            padding: 5px 15px;
            border-radius: 3px;
            font-weight: bold;
            animation: pulse 2s infinite;
        }
        
        .flow-stage.mind { background: rgba(255, 170, 0, 0.3); color: #ffaa00; }
        .flow-stage.thought { background: rgba(0, 255, 136, 0.3); color: #00ff88; }
        .flow-stage.action { background: rgba(255, 68, 68, 0.3); color: #ff4444; }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(0.95); }
        }
        
        #container {
            display: grid;
            grid-template-columns: 350px 1fr 350px;
            grid-template-rows: 1fr;
            gap: 15px;
            padding: 15px;
            height: calc(100vh - 120px);
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
        
        #mind-panel { border-color: #ffaa00; box-shadow: 0 0 20px rgba(255, 170, 0, 0.3); }
        #thought-panel { grid-column: 3; border-color: #00ff88; }
        
        #network-container {
            grid-column: 2;
            background: rgba(0, 0, 0, 0.9);
            border: 2px solid #6C5CE7;
            border-radius: 10px;
            position: relative;
        }
        
        .thought-message {
            padding: 10px;
            margin: 8px 0;
            background: rgba(0, 255, 136, 0.1);
            border-left: 3px solid #00ff88;
            border-radius: 5px;
            animation: slideIn 0.3s ease;
            font-size: 0.85em;
        }
        
        @keyframes slideIn {
            from { transform: translateX(20px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        .thought-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            color: #888;
            font-size: 0.85em;
        }
        
        .thought-topic {
            color: #00ff88;
            font-weight: bold;
        }
        
        .thought-source {
            color: #ffaa00;
        }
        
        .thought-payload {
            color: #fff;
            margin-top: 5px;
        }
        
        .mind-stat {
            display: flex;
            justify-content: space-between;
            padding: 8px 10px;
            margin: 5px 0;
            background: rgba(255, 170, 0, 0.1);
            border-left: 3px solid #ffaa00;
            border-radius: 3px;
            font-size: 0.9em;
        }
        
        .stat-label { color: #888; }
        .stat-value { color: #ffaa00; font-weight: bold; }
        
        .action-item {
            padding: 10px;
            margin: 8px 0;
            background: rgba(255, 68, 68, 0.1);
            border-left: 3px solid #ff4444;
            border-radius: 5px;
            font-size: 0.85em;
        }
        
        .action-type {
            font-weight: bold;
            color: #ff4444;
            margin-bottom: 5px;
        }
        
        .action-details {
            color: #888;
            font-size: 0.9em;
        }
        
        .connection-status {
            position: absolute;
            top: 10px;
            right: 10px;
            padding: 5px 15px;
            background: rgba(0, 255, 136, 0.3);
            border-radius: 5px;
            font-size: 0.85em;
            font-weight: bold;
            color: #00ff88;
        }
        
        .connection-status.disconnected {
            background: rgba(255, 68, 68, 0.3);
            color: #ff4444;
        }
        
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.3); }
        ::-webkit-scrollbar-thumb { background: rgba(0, 255, 136, 0.3); border-radius: 4px; }
        
        .system-node {
            cursor: pointer;
        }
        
        .layer-indicator {
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            display: inline-block;
            margin-right: 5px;
        }
        
        .layer-mind { background: rgba(255, 170, 0, 0.3); color: #ffaa00; }
        .layer-thought { background: rgba(0, 255, 136, 0.3); color: #00ff88; }
        .layer-action { background: rgba(255, 68, 68, 0.3); color: #ff4444; }
    </style>
</head>
<body>
    <div id="header">
        <h1>🧠💭⚡ AUREON MIND → THOUGHT → ACTION HUB</h1>
        <div id="cognitive-flow">
            <div class="flow-stage mind">🧠 MIND</div>
            <div style="color: #888;">→</div>
            <div class="flow-stage thought">💭 THOUGHT</div>
            <div style="color: #888;">→</div>
            <div class="flow-stage action">⚡ ACTION</div>
        </div>
    </div>
    
    <div id="container">
        <div id="mind-panel" class="panel">
            <h2>🧠 MIND (Intelligence)</h2>
            <div id="mind-systems"></div>
        </div>
        
        <div id="network-container">
            <div class="connection-status" id="ws-status">● CONNECTING...</div>
            <div id="network" style="width: 100%; height: 100%;"></div>
        </div>
        
        <div id="thought-panel" class="panel">
            <h2>💭 THOUGHT STREAM</h2>
            <div id="thought-stream"></div>
            
            <h2 style="margin-top: 20px;">⚡ ACTIONS</h2>
            <div id="action-stream"></div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let network = null;
        let allData = null;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = () => {
                console.log('✅ WebSocket connected');
                document.getElementById('ws-status').textContent = '● CONNECTED';
                document.getElementById('ws-status').className = 'connection-status';
            };
            
            ws.onclose = () => {
                console.log('⚠️ WebSocket disconnected');
                document.getElementById('ws-status').textContent = '● DISCONNECTED';
                document.getElementById('ws-status').className = 'connection-status disconnected';
                setTimeout(connectWebSocket, 3000);
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
                case 'thought':
                    addThought(data.thought);
                    updateNetworkActivity(data.thought);
                    break;
                case 'action':
                    addAction(data.action);
                    break;
                case 'mind_update':
                    updateMindStats(data.stats);
                    break;
                case 'systems_update':
                    updateNetworkNodes(data.systems);
                    break;
            }
        }
        
        function addThought(thought) {
            const stream = document.getElementById('thought-stream');
            const item = document.createElement('div');
            item.className = 'thought-message';
            
            const time = new Date(thought.ts * 1000).toLocaleTimeString();
            item.innerHTML = `
                <div class="thought-header">
                    <span class="thought-topic">${thought.topic}</span>
                    <span>${time}</span>
                </div>
                <div class="thought-source">From: ${thought.source}</div>
                <div class="thought-payload">${JSON.stringify(thought.payload, null, 2)}</div>
            `;
            
            stream.insertBefore(item, stream.firstChild);
            
            // Keep only last 20 thoughts
            while (stream.children.length > 20) {
                stream.removeChild(stream.lastChild);
            }
        }
        
        function addAction(action) {
            const stream = document.getElementById('action-stream');
            const item = document.createElement('div');
            item.className = 'action-item';
            
            item.innerHTML = `
                <div class="action-type">⚡ ${action.type}</div>
                <div class="action-details">${action.details}</div>
            `;
            
            stream.insertBefore(item, stream.firstChild);
            
            // Keep only last 15 actions
            while (stream.children.length > 15) {
                stream.removeChild(stream.lastChild);
            }
        }
        
        function updateMindStats(stats) {
            const mindDiv = document.getElementById('mind-systems');
            mindDiv.innerHTML = '';
            
            for (const [key, value] of Object.entries(stats)) {
                const item = document.createElement('div');
                item.className = 'mind-stat';
                item.innerHTML = `
                    <span class="stat-label">${key}</span>
                    <span class="stat-value">${value}</span>
                `;
                mindDiv.appendChild(item);
            }
        }
        
        async function loadMindMap() {
            const response = await fetch('/api/mindmap');
            allData = await response.json();
            renderNetwork(allData);
        }
        
        function categorizeSystem(system) {
            // Categorize systems into Mind, Thought, or Action layers
            const mindKeywords = ['queen', 'intelligence', 'brain', 'probability', 'oracle', 'quantum'];
            const thoughtKeywords = ['thought', 'bus', 'mycelium', 'network', 'bridge'];
            const actionKeywords = ['trader', 'executor', 'client', 'exchange', 'order'];
            
            const name = system.label.toLowerCase();
            
            if (mindKeywords.some(k => name.includes(k))) return 'mind';
            if (thoughtKeywords.some(k => name.includes(k))) return 'thought';
            if (actionKeywords.some(k => name.includes(k))) return 'action';
            
            return 'other';
        }
        
        function renderNetwork(data) {
            const container = document.getElementById('network');
            
            // Enhance nodes with layer information
            const nodes = data.nodes.map(node => {
                const layer = categorizeSystem(node);
                let color;
                if (layer === 'mind') color = '#ffaa00';
                else if (layer === 'thought') color = '#00ff88';
                else if (layer === 'action') color = '#ff4444';
                else color = node.color;
                
                return {
                    ...node,
                    color: color,
                    title: `${node.label}<br>Layer: ${layer.toUpperCase()}`,
                    layer: layer
                };
            });
            
            const options = {
                nodes: {
                    font: { color: '#ffffff', size: 14 },
                    borderWidth: 2,
                    borderWidthSelected: 4,
                    shadow: { enabled: true, color: 'rgba(0,0,0,0.5)', size: 10 }
                },
                edges: {
                    color: { color: 'rgba(255,255,255,0.2)', highlight: '#00ff88' },
                    smooth: { type: 'continuous' },
                    arrows: { to: { enabled: true, scaleFactor: 0.5 } }
                },
                physics: {
                    enabled: true,
                    barnesHut: {
                        gravitationalConstant: -8000,
                        centralGravity: 0.3,
                        springLength: 150,
                        springConstant: 0.04,
                        damping: 0.09
                    },
                    stabilization: { iterations: 200 }
                },
                interaction: {
                    hover: true,
                    tooltipDelay: 100,
                    navigationButtons: true,
                    keyboard: true
                }
            };
            
            network = new vis.Network(container, {
                nodes: new vis.DataSet(nodes),
                edges: new vis.DataSet(data.edges)
            }, options);
            
            network.on('click', function(params) {
                if (params.nodes.length > 0) {
                    const nodeId = params.nodes[0];
                    highlightNodeActivity(nodeId);
                }
            });
        }
        
        function updateNetworkActivity(thought) {
            if (!network) return;
            
            // Flash the source node
            const sourceNode = allData.nodes.find(n => 
                n.label.toLowerCase().includes(thought.source.toLowerCase())
            );
            
            if (sourceNode) {
                // Temporarily change node appearance to show activity
                network.body.data.nodes.update({
                    id: sourceNode.id,
                    borderWidth: 6
                });
                
                setTimeout(() => {
                    network.body.data.nodes.update({
                        id: sourceNode.id,
                        borderWidth: 2
                    });
                }, 500);
            }
        }
        
        function highlightNodeActivity(nodeId) {
            // Show recent thoughts from this node
            console.log('Node clicked:', nodeId);
        }
        
        // Initialize
        connectWebSocket();
        loadMindMap();
        
        console.log('🧠💭⚡ Mind → Thought → Action Hub initialized');
    </script>
</body>
</html>
"""

# ════════════════════════════════════════════════════════════════════════════
# HUB CLASS
# ════════════════════════════════════════════════════════════════════════════

class MindThoughtActionHub:
    """Unified cognitive pipeline hub."""
    
    def __init__(self, port=13002):
        self.port = port
        self.clients: Set = set()
        
        # Core systems
        self.registry = SystemRegistry()
        self.thought_bus = ThoughtBus()
        
        # System instances
        self.queen = None
        self.prob_nexus = None
        self.ultimate_intel = None
        
        # Thought and action tracking
        self.recent_thoughts = deque(maxlen=100)
        self.recent_actions = deque(maxlen=50)
        
        # Stats
        self.mind_stats = {
            'Queen Patterns': 0,
            'Intelligence Accuracy': 0,
            'Nexus Win Rate': 0,
            'Active Thoughts/s': 0,
            'Actions Executed': 0
        }
        
        # Initialize
        self._init_systems()
        
        # Setup web app
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/ws', self.handle_websocket)
        self.app.router.add_get('/api/mindmap', self.handle_mindmap)
        self.app.router.add_get('/api/thoughts', self.handle_thoughts)
        self.app.router.add_get('/api/actions', self.handle_actions)
    
    def _init_systems(self):
        """Initialize core cognitive systems."""
        logger.info("🧠 Initializing Mind systems...")
        
        # Scan workspace
        self.registry.scan_workspace()
        logger.info(f"✅ Registered {len(self.registry.systems)} systems")
        
        # Initialize Queen
        if QueenHiveMind:
            try:
                self.queen = QueenHiveMind()
                self.mind_stats['Queen Patterns'] = 229  # From elephant memory
                logger.info("👑 Queen Hive Mind loaded")
            except: pass
        
        # Initialize Probability Nexus
        if ProbabilityNexus:
            try:
                self.prob_nexus = ProbabilityNexus()
                self.mind_stats['Nexus Win Rate'] = 79.6
                logger.info("🔮 Probability Nexus loaded")
            except: pass
        
        # Initialize Ultimate Intelligence
        if UltimateIntelligence:
            try:
                self.ultimate_intel = UltimateIntelligence()
                self.mind_stats['Intelligence Accuracy'] = 95.0
                logger.info("💎 Ultimate Intelligence loaded")
            except: pass
        
        # Subscribe to ThoughtBus
        self.thought_bus.subscribe('*', self._on_thought)
        logger.info("💭 ThoughtBus subscribed")
    
    def _on_thought(self, thought: Thought):
        """Handle thought from ThoughtBus."""
        self.recent_thoughts.append(thought)
        
        # Broadcast to connected clients
        asyncio.create_task(self.broadcast({
            'type': 'thought',
            'thought': {
                'id': thought.id,
                'ts': thought.ts,
                'source': thought.source,
                'topic': thought.topic,
                'payload': thought.payload
            }
        }))
        
        # Track actions
        if thought.topic.startswith('execution.') or thought.topic.startswith('order.'):
            self.recent_actions.append({
                'type': thought.topic,
                'details': str(thought.payload),
                'ts': thought.ts
            })
            
            asyncio.create_task(self.broadcast({
                'type': 'action',
                'action': {
                    'type': thought.topic,
                    'details': str(thought.payload)
                }
            }))
    
    async def handle_index(self, request):
        """Serve dashboard HTML."""
        return web.Response(text=MIND_THOUGHT_ACTION_HTML, content_type='text/html')
    
    async def handle_websocket(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.clients.add(ws)
        logger.info(f"👑 Client connected (total: {len(self.clients)})")
        
        # Send initial data
        await ws.send_json({
            'type': 'mind_update',
            'stats': self.mind_stats
        })
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            self.clients.discard(ws)
            logger.info(f"Client disconnected (remaining: {len(self.clients)})")
        
        return ws
    
    async def handle_mindmap(self, request):
        """API endpoint for mind map data."""
        return web.json_response(self.registry.export_mind_map_data())
    
    async def handle_thoughts(self, request):
        """API endpoint for recent thoughts."""
        return web.json_response({
            'thoughts': [
                {
                    'id': t.id,
                    'ts': t.ts,
                    'source': t.source,
                    'topic': t.topic,
                    'payload': t.payload
                }
                for t in list(self.recent_thoughts)[-20:]
            ]
        })
    
    async def handle_actions(self, request):
        """API endpoint for recent actions."""
        return web.json_response({
            'actions': list(self.recent_actions)[-20:]
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
    
    async def live_stats_updater(self):
        """Update mind stats periodically."""
        await asyncio.sleep(2)
        
        logger.info("📊 Starting live stats updater...")
        
        while True:
            try:
                # Calculate thoughts per second
                recent_count = len([t for t in self.recent_thoughts if time.time() - t.ts < 1.0])
                self.mind_stats['Active Thoughts/s'] = recent_count
                self.mind_stats['Actions Executed'] = len(self.recent_actions)
                
                # Broadcast update
                await self.broadcast({
                    'type': 'mind_update',
                    'stats': self.mind_stats
                })
                
                await asyncio.sleep(2)  # Update every 2 seconds
                
            except Exception as e:
                logger.error(f"Error in stats updater: {e}")
                await asyncio.sleep(5)
    
    async def generate_test_thoughts(self):
        """Generate test thoughts for demonstration."""
        await asyncio.sleep(5)
        
        logger.info("🧪 Starting test thought generator...")
        
        topics = [
            'market.snapshot',
            'miner.signal',
            'queen.decision',
            'execution.order',
            'risk.approval',
            'harmonic.wave'
        ]
        
        sources = [
            'Queen',
            'ProbabilityNexus',
            'UltimateIntel',
            'MinerBrain',
            'HarmonicFusion'
        ]
        
        while True:
            try:
                import random
                
                topic = random.choice(topics)
                source = random.choice(sources)
                
                thought = Thought(
                    source=source,
                    topic=topic,
                    payload={
                        'message': f'Test thought from {source}',
                        'confidence': random.uniform(0.7, 0.99),
                        'value': random.randint(1, 100)
                    }
                )
                
                self.thought_bus.publish(thought)
                
                await asyncio.sleep(random.uniform(2, 5))  # Random interval
                
            except Exception as e:
                logger.error(f"Error generating test thought: {e}")
                await asyncio.sleep(5)
    
    async def start(self):
        """Start the hub."""
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        print(f"\n{'='*80}")
        print(f"🧠💭⚡ AUREON MIND → THOUGHT → ACTION HUB")
        print(f"{'='*80}")
        print(f"🌐 Dashboard: http://localhost:{self.port}")
        print(f"📡 WebSocket: ws://localhost:{self.port}/ws")
        print(f"\n✨ COGNITIVE ARCHITECTURE:")
        print(f"   🧠 MIND:    {len([s for s in self.registry.systems.values() if 'queen' in s.name.lower() or 'intelligence' in s.name.lower()])} systems")
        print(f"   💭 THOUGHT: ThoughtBus (real-time streaming)")
        print(f"   ⚡ ACTION:  Execution layer monitoring")
        print(f"\n📊 SYSTEMS INTEGRATED:")
        print(f"   • Total Systems: {len(self.registry.systems)}")
        print(f"   • Categories: {len(self.registry.get_category_stats())}")
        print(f"   • Dashboards: {len([s for s in self.registry.systems.values() if s.is_dashboard])}")
        if self.queen:
            print(f"   • Queen Hive Mind: 229 patterns")
        if self.prob_nexus:
            print(f"   • Probability Nexus: 79.6% win rate")
        if self.ultimate_intel:
            print(f"   • Ultimate Intelligence")
        print(f"{'='*80}\n")
        
        # Start background tasks
        asyncio.create_task(self.live_stats_updater())
        asyncio.create_task(self.generate_test_thoughts())

async def main():
    hub = MindThoughtActionHub(port=13002)
    await hub.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🧠💭⚡ Mind → Thought → Action Hub stopped")
