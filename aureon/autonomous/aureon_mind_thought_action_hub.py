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
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Set, Optional, Tuple
from collections import deque, defaultdict
from pathlib import Path

# Import core systems
from aureon.command_centers.aureon_system_hub import SystemRegistry
from aureon.core.aureon_thought_bus import ThoughtBus, Thought
from aureon.core.aureon_runtime_safety import audit_mode_enabled
SelfQuestioningAI = None
QueenHiveMind = None
ProbabilityNexus = None
UltimateIntelligence = None

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

def load_optional_system_classes():
    """Load optional cognitive systems only after the HTTP hub is online."""
    global QueenHiveMind, ProbabilityNexus, UltimateIntelligence
    if QueenHiveMind is None:
        QueenHiveMind = safe_import('Queen', 'aureon_queen_hive_mind', 'QueenHiveMind')
    if ProbabilityNexus is None:
        ProbabilityNexus = safe_import('ProbNexus', 'aureon_probability_nexus', 'ProbabilityNexus')
    if UltimateIntelligence is None:
        UltimateIntelligence = safe_import('UltimateIntel', 'probability_ultimate_intelligence', 'ProbabilityUltimateIntelligence')


def load_self_questioning_ai_class():
    """Load the optional self-questioning AI only during hub warmup."""
    global SelfQuestioningAI
    if SelfQuestioningAI is not None:
        return SelfQuestioningAI
    try:
        from aureon.autonomous.aureon_self_questioning_ai import SelfQuestioningAI as loaded
        SelfQuestioningAI = loaded
    except Exception:
        SelfQuestioningAI = None
    return SelfQuestioningAI

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
        self.self_questioning_ai = None
        
        # Thought and action tracking
        self.recent_thoughts = deque(maxlen=100)
        self.recent_actions = deque(maxlen=50)
        
        # Stats
        self.mind_stats = {
            'Queen Patterns': 0,
            'Intelligence Accuracy': 0,
            'Nexus Win Rate': 0,
            'Active Thoughts/s': 0,
            'Actions Executed': 0,
            'Self Questioning Cycles': 0
        }
        
        self.initialized = False
        self.initializing = False
        self.init_error = None
        self._init_task = None
        self._self_questioning_task = None
        self._goal_pursuit_task = None
        self._phi_bridge = None
        self._phi_voice_adapter = None
        self.phi_chat_history = deque(maxlen=40)
        self._phi_chat_timeout_ids: Set[str] = set()
        self._ollama_cognitive_status_cache: Dict[str, Any] = {}
        self._ollama_cognitive_status_cache_at = 0.0

        # Setup web app
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/ws', self.handle_websocket)
        self.app.router.add_get('/api/mindmap', self.handle_mindmap)
        self.app.router.add_get('/api/thoughts', self.handle_thoughts)
        self.app.router.add_get('/api/actions', self.handle_actions)
        self.app.router.add_get('/api/flight-test', self.handle_flight_test)
        self.app.router.add_get('/api/reboot-advice', self.handle_flight_test)
        self.app.router.add_get('/api/goal-pursuit', self.handle_goal_pursuit)
        self.app.router.add_get('/api/coding/status', self.handle_coding_status)
        self.app.router.add_post('/api/coding/prompt', self.handle_coding_prompt)
        self.app.router.add_options('/api/coding/status', self.handle_coding_options)
        self.app.router.add_options('/api/coding/prompt', self.handle_coding_options)
        self.app.router.add_get('/api/autonomous-self-run/status', self.handle_autonomous_self_run_status)
        self.app.router.add_post('/api/autonomous-self-run/tick', self.handle_autonomous_self_run_tick)
        self.app.router.add_options('/api/autonomous-self-run/status', self.handle_coding_options)
        self.app.router.add_options('/api/autonomous-self-run/tick', self.handle_coding_options)
        self.app.router.add_get('/api/autonomous-jobs/status', self.handle_autonomous_jobs_status)
        self.app.router.add_get('/api/autonomous-jobs/{job_id}', self.handle_autonomous_job_detail)
        self.app.router.add_post('/api/autonomous-jobs/tick', self.handle_autonomous_jobs_tick)
        self.app.router.add_options('/api/autonomous-jobs/status', self.handle_coding_options)
        self.app.router.add_options('/api/autonomous-jobs/tick', self.handle_coding_options)
        self.app.router.add_get('/api/self-questioning/status', self.handle_self_questioning_status)
        self.app.router.add_post('/api/self-questioning/ask', self.handle_self_questioning_ask)
        self.app.router.add_get('/api/phi-bridge/status', self.handle_phi_bridge_status)
        self.app.router.add_post('/api/phi-bridge/chat', self.handle_phi_bridge_chat)
        self.app.router.add_post('/api/phi-bridge/reload', self.handle_phi_bridge_reload)
        self.app.router.add_options('/api/phi-bridge/status', self.handle_coding_options)
        self.app.router.add_options('/api/phi-bridge/chat', self.handle_coding_options)
        self.app.router.add_options('/api/phi-bridge/reload', self.handle_coding_options)
        self.app.router.add_get('/api/ollama-cognitive/status', self.handle_ollama_cognitive_status)
        self.app.router.add_options('/api/ollama-cognitive/status', self.handle_coding_options)

    def _initialization_status(self) -> str:
        if self.init_error:
            return 'error'
        if self.initialized:
            return 'ready'
        return 'initializing'

    def _parse_downtime_days(self, raw: str) -> Set[int]:
        day_map = {
            'mon': 0, 'monday': 0,
            'tue': 1, 'tuesday': 1,
            'wed': 2, 'wednesday': 2,
            'thu': 3, 'thursday': 3,
            'fri': 4, 'friday': 4,
            'sat': 5, 'saturday': 5,
            'sun': 6, 'sunday': 6,
        }
        value = (raw or '').strip().lower()
        if value in {'*', 'all', 'daily', 'everyday'}:
            return set(range(7))

        days: Set[int] = set()
        for part in value.replace(';', ',').split(','):
            item = part.strip()
            if not item:
                continue
            if '-' in item:
                start_raw, end_raw = [piece.strip() for piece in item.split('-', 1)]
                if start_raw in day_map and end_raw in day_map:
                    start = day_map[start_raw]
                    end = day_map[end_raw]
                    cursor = start
                    while True:
                        days.add(cursor)
                        if cursor == end:
                            break
                        cursor = (cursor + 1) % 7
                continue
            if item in day_map:
                days.add(day_map[item])
        return days or {6}

    def _parse_hhmm(self, raw: str, fallback: str) -> tuple[int, int]:
        value = (raw or fallback).strip()
        try:
            hour, minute = value.split(':', 1)
            hour_int = max(0, min(23, int(hour)))
            minute_int = max(0, min(59, int(minute)))
            return hour_int, minute_int
        except Exception:
            fallback_hour, fallback_minute = fallback.split(':', 1)
            return int(fallback_hour), int(fallback_minute)

    def _downtime_window_state(self) -> Dict[str, Any]:
        days_raw = os.environ.get('AUREON_MIND_DOWNTIME_DAYS', 'Sun')
        start_raw = os.environ.get('AUREON_MIND_DOWNTIME_START_LOCAL', '03:00')
        end_raw = os.environ.get('AUREON_MIND_DOWNTIME_END_LOCAL', '03:15')
        days = self._parse_downtime_days(days_raw)
        start_hour, start_minute = self._parse_hhmm(start_raw, '03:00')
        end_hour, end_minute = self._parse_hhmm(end_raw, '03:15')

        now = datetime.now().astimezone()

        def window_for(day_offset: int) -> tuple[datetime, datetime]:
            base = now + timedelta(days=day_offset)
            start = base.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
            end = base.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
            if end <= start:
                end += timedelta(days=1)
            return start, end

        today_start, today_end = window_for(0)
        in_window = now.weekday() in days and today_start <= now < today_end
        if not in_window:
            yesterday_start, yesterday_end = window_for(-1)
            in_window = (now - timedelta(days=1)).weekday() in days and yesterday_start <= now < yesterday_end

        next_start = None
        next_end = None
        for offset in range(0, 15):
            candidate_start, candidate_end = window_for(offset)
            if candidate_start.weekday() in days and candidate_end > now:
                if candidate_start <= now < candidate_end:
                    next_start, next_end = candidate_start, candidate_end
                elif candidate_start > now:
                    next_start, next_end = candidate_start, candidate_end
                if next_start:
                    break

        return {
            'in_window': in_window,
            'days': days_raw,
            'start_local': f'{start_hour:02d}:{start_minute:02d}',
            'end_local': f'{end_hour:02d}:{end_minute:02d}',
            'now_local': now.isoformat(),
            'next_start_local': next_start.isoformat() if next_start else None,
            'next_end_local': next_end.isoformat() if next_end else None,
        }

    def _read_market_runtime_summary(self) -> Dict[str, Any]:
        status_path = Path(__file__).resolve().parents[2] / 'state' / 'unified_runtime_status.json'
        if not status_path.exists():
            return {
                'available': False,
                'status_file': str(status_path),
                'open_positions': 0,
                'pending_orders': 0,
            }

        try:
            with status_path.open('r', encoding='utf-8') as handle:
                payload = json.load(handle)
        except Exception as e:
            return {
                'available': False,
                'status_file': str(status_path),
                'error': str(e),
                'open_positions': 0,
                'pending_orders': 0,
            }

        def number_from(*keys: str, source: Optional[Dict[str, Any]] = None) -> int:
            source = source or payload
            for key in keys:
                value = source.get(key) if isinstance(source, dict) else None
                if isinstance(value, (int, float)):
                    return int(value)
                if isinstance(value, list):
                    return len(value)
            return 0

        combined = payload.get('combined') if isinstance(payload.get('combined'), dict) else {}
        exchanges = payload.get('exchanges') if isinstance(payload.get('exchanges'), dict) else {}
        age_sec = max(0.0, time.time() - status_path.stat().st_mtime)
        ready_values = [bool(value) for key, value in exchanges.items() if str(key).endswith('_ready')]

        return {
            'available': True,
            'ok': bool(payload.get('ok', True)),
            'trading_ready': bool(payload.get('trading_ready', False)),
            'data_ready': bool(payload.get('data_ready', False)),
            'stale': bool(payload.get('stale', False)) or age_sec > 60,
            'status_file_age_sec': round(age_sec, 3),
            'open_positions': number_from('open_positions', 'positions', source=combined),
            'pending_orders': number_from(
                'pending_orders',
                'open_orders',
                'active_orders',
                source=combined,
            ),
            'exchanges_ready': all(ready_values) if ready_values else None,
            'status_file': str(status_path),
        }

    def _read_reboot_intent(self) -> Dict[str, Any]:
        intent_path = Path(__file__).resolve().parents[2] / 'state' / 'aureon_reboot_intent.json'
        if not intent_path.exists():
            return {'pending': False, 'path': str(intent_path)}
        try:
            with intent_path.open('r', encoding='utf-8') as handle:
                payload = json.load(handle)
        except Exception as e:
            return {'pending': False, 'path': str(intent_path), 'error': str(e)}

        if not isinstance(payload, dict):
            return {'pending': False, 'path': str(intent_path), 'error': 'intent_not_object'}

        status = str(payload.get('status', 'pending')).strip().lower()
        surface = str(payload.get('surface', 'mind')).strip().lower()
        pending = status in {'pending', 'requested', 'ready'} and surface in {
            'mind',
            'cognitive',
            'all',
            'organism',
        }
        return {
            'pending': pending,
            'path': str(intent_path),
            'status': status,
            'surface': surface,
            'requested_by': payload.get('requested_by'),
            'reason': payload.get('reason'),
            'requested_at': payload.get('requested_at'),
            'change_id': payload.get('change_id'),
        }

    def _read_goal_directive(self) -> Dict[str, Any]:
        directive_path = Path(__file__).resolve().parents[2] / 'state' / 'aureon_goal_directive.json'
        primary_goal = os.environ.get(
            'AUREON_PRIMARY_GOAL',
            'sustain_live_trading_and_grow_equity_with_positive_risk_adjusted_returns',
        )
        directive: Dict[str, Any] = {
            'primary_goal': primary_goal,
            'source': 'environment_default',
            'path': str(directive_path),
        }

        if directive_path.exists():
            try:
                with directive_path.open('r', encoding='utf-8') as handle:
                    payload = json.load(handle)
                if isinstance(payload, dict):
                    directive.update(payload)
                    directive['source'] = 'state_file'
                    directive['path'] = str(directive_path)
                    directive['primary_goal'] = (
                        payload.get('primary_goal')
                        or payload.get('goal')
                        or primary_goal
                    )
            except Exception as e:
                directive['error'] = str(e)

        baseline_constraints = [
            'keep_live_trading_runtime_available',
            'preserve_open_position_management',
            'obey_runtime_risk_and_exchange_gates',
            'publish_order_intent_only_through_authorized_runtime_paths',
            'never_enable_direct_exchange_mutation_without_runtime_gate',
            'reboot_only_after_self_flight_test_and_downtime_window',
            'prefer_background_warmup_over_process_restart',
        ]
        configured = directive.get('constraints')
        if not isinstance(configured, list):
            configured = []
        constraints: List[str] = []
        for item in [*baseline_constraints, *configured]:
            value = str(item).strip()
            if value and value not in constraints:
                constraints.append(value)
        directive['constraints'] = constraints
        return directive

    def _read_organism_runtime_status(self) -> Dict[str, Any]:
        status_path = (
            Path(__file__).resolve().parents[2]
            / 'frontend'
            / 'public'
            / 'aureon_organism_runtime_status.json'
        )
        if not status_path.exists():
            return {
                'available': False,
                'status_file': str(status_path),
                'blind_spot_count': 0,
                'next_actions': [],
            }

        try:
            with status_path.open('r', encoding='utf-8') as handle:
                payload = json.load(handle)
        except Exception as e:
            return {
                'available': False,
                'status_file': str(status_path),
                'error': str(e),
                'blind_spot_count': 0,
                'next_actions': [],
            }

        blind_spots = payload.get('blind_spots') if isinstance(payload, dict) else []
        if not isinstance(blind_spots, list):
            blind_spots = []
        severity_rank = {
            'critical': 4,
            'high': 3,
            'attention': 2,
            'medium': 2,
            'low': 1,
        }
        sorted_blind_spots = sorted(
            [spot for spot in blind_spots if isinstance(spot, dict)],
            key=lambda spot: severity_rank.get(str(spot.get('severity', '')).lower(), 0),
            reverse=True,
        )
        next_actions = payload.get('next_actions') if isinstance(payload, dict) else []
        if not isinstance(next_actions, list):
            next_actions = []
        age_sec = max(0.0, time.time() - status_path.stat().st_mtime)

        return {
            'available': True,
            'status': payload.get('status') if isinstance(payload, dict) else None,
            'generated_at': payload.get('generated_at') if isinstance(payload, dict) else None,
            'status_file_age_sec': round(age_sec, 3),
            'status_file': str(status_path),
            'blind_spot_count': len(sorted_blind_spots),
            'highest_blind_spots': sorted_blind_spots[:5],
            'next_actions': [str(action) for action in next_actions[:5]],
        }

    def _run_goal_pursuit_assessment(
        self,
        market: Optional[Dict[str, Any]] = None,
        organism: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        market = market or self._read_market_runtime_summary()
        organism = organism or self._read_organism_runtime_status()
        directive = self._read_goal_directive()

        blockers: List[str] = []
        active_modes: List[str] = []
        next_best_actions: List[str] = []

        market_ready = (
            bool(market.get('available'))
            and bool(market.get('trading_ready'))
            and bool(market.get('data_ready'))
            and market.get('exchanges_ready') is not False
        )
        if market_ready:
            active_modes.append('live_trading_runtime_ready')
            next_best_actions.append(
                'Keep market feeds, exchange connections, and runtime trading telemetry alive.'
            )
        else:
            blockers.append('market_runtime_not_fully_ready')
            next_best_actions.append(
                'Restore market runtime readiness before escalating new order intent.'
            )

        if market.get('stale'):
            blockers.append('market_runtime_status_stale')
            next_best_actions.append(
                'Refresh and verify market telemetry before new risk-taking decisions.'
            )

        open_positions = int(market.get('open_positions', 0) or 0)
        pending_orders = int(market.get('pending_orders', 0) or 0)
        if open_positions > 0:
            active_modes.append('open_position_monitoring')
            next_best_actions.append(
                f'Protect and supervise {open_positions} open position(s) through runtime risk controls.'
            )
        if pending_orders > 0:
            active_modes.append('pending_order_supervision')
            next_best_actions.append(
                f'Reconcile {pending_orders} pending order(s) before maintenance or restart.'
            )

        if self.initialized:
            active_modes.append('cognitive_analysis_ready')
        elif self.initializing:
            active_modes.append('cognitive_background_warmup')
            next_best_actions.append(
                'Continue cognitive warmup in the background while health endpoints remain live.'
            )
        else:
            blockers.append('cognitive_systems_not_ready')
            next_best_actions.append(
                'Keep HTTP health online and finish cognitive initialization without rebooting.'
            )

        if self.init_error:
            blockers.append('cognitive_initialization_error')
            next_best_actions.append(
                'Request repair and defer reboot until the downtime window and flight test both approve.'
            )

        if organism.get('available'):
            active_modes.append('organism_self_observation')
            if organism.get('blind_spot_count', 0) > 0:
                active_modes.append('self_improvement_backlog')
                highest_blind_spots = organism.get('highest_blind_spots')
                if not isinstance(highest_blind_spots, list):
                    highest_blind_spots = []
                next_actions = organism.get('next_actions')
                if not isinstance(next_actions, list):
                    next_actions = []
                top_spot = highest_blind_spots[0] if highest_blind_spots else {}
                action = top_spot.get('next_action') or (
                    next_actions[0] if next_actions else None
                )
                if action:
                    next_best_actions.append(
                        f'Work the highest-impact safe self-improvement check: {action}'
                    )
        else:
            blockers.append('organism_status_unavailable')
            next_best_actions.append(
                'Regenerate organism runtime status so blind spots and next actions are visible.'
            )

        action_authority = {
            'llm_order_intent_authority': os.environ.get(
                'AUREON_LLM_ORDER_INTENT_AUTHORITY',
                '0',
            ).strip().lower() in {'1', 'true', 'yes', 'on'},
            'direct_exchange_mutation_authority': os.environ.get(
                'AUREON_LLM_DIRECT_EXCHANGE_MUTATION_AUTHORITY',
                '0',
            ).strip().lower() in {'1', 'true', 'yes', 'on'},
            'real_orders_disabled': os.environ.get(
                'AUREON_DISABLE_REAL_ORDERS',
                '0',
            ).strip().lower() in {'1', 'true', 'yes', 'on'},
        }

        if not action_authority['llm_order_intent_authority']:
            next_best_actions.append(
                'Analyze opportunities but do not emit order intent until runtime authority is present.'
            )
        if action_authority['direct_exchange_mutation_authority']:
            blockers.append('direct_exchange_mutation_authority_enabled')
            next_best_actions.append(
                'Keep direct exchange mutation guarded by runtime policy; prefer order-intent handoff.'
            )

        if not next_best_actions:
            next_best_actions.append(
                'Continue live analysis and only act through risk-authorized trading pathways.'
            )

        if market_ready and self.initialized:
            decision = 'pursue_goal_with_full_live_capability'
        elif market_ready:
            decision = 'pursue_goal_with_guarded_live_capability'
        else:
            decision = 'restore_capability_before_new_risk'

        return {
            'service': 'aureon-mind-thought-action-hub',
            'generated_at': datetime.now().astimezone().isoformat(),
            'primary_goal': directive.get('primary_goal'),
            'decision': decision,
            'maximum_safe_effort': (
                'Run every non-destructive analysis, keep feeds alive, protect positions, '
                'publish only authorized order intent, and defer disruptive maintenance.'
            ),
            'active_modes': active_modes,
            'blockers': blockers,
            'next_best_actions': next_best_actions[:8],
            'constraints': directive.get('constraints', []),
            'action_authority': action_authority,
            'market_runtime': market,
            'organism_status': organism,
            'self_questions': [
                'What can I safely do right now to advance the primary goal?',
                'Are market data, trading runtime, and exchange connections ready?',
                'Do open positions or pending orders require protection before anything else?',
                'Which blind spot most threatens goal progress?',
                'Would a reboot reduce live capability right now?',
                'Can this action pass risk, legality, and runtime authority gates?',
            ],
        }

    def _run_internal_flight_test(self) -> Dict[str, Any]:
        downtime = self._downtime_window_state()
        market = self._read_market_runtime_summary()
        reboot_intent = self._read_reboot_intent()
        goal_pursuit = self._run_goal_pursuit_assessment(market=market)
        allow_open_positions = os.environ.get(
            'AUREON_ALLOW_MIND_REBOOT_WITH_OPEN_POSITIONS',
            '0',
        ).strip().lower() in {'1', 'true', 'yes', 'on'}

        blockers: List[str] = []
        if not downtime['in_window']:
            blockers.append('outside_downtime_window')
        if self.initializing:
            blockers.append('mind_initializing')
        if market.get('open_positions', 0) > 0 and not allow_open_positions:
            blockers.append('open_positions_active')
        if market.get('pending_orders', 0) > 0:
            blockers.append('pending_orders_active')
        if market.get('available') and market.get('stale'):
            blockers.append('market_runtime_status_stale')

        flight_checks = {
            'http_surface': True,
            'thought_bus': self.thought_bus is not None,
            'mind_initialized': self.initialized,
            'mind_initializing': self.initializing,
            'mind_init_error': self.init_error is None,
            'market_runtime_available': bool(market.get('available')),
            'market_trading_ready': bool(market.get('trading_ready')),
            'market_data_ready': bool(market.get('data_ready')),
        }
        ok = all(flight_checks.values()) if self.initialized else all(
            value for key, value in flight_checks.items()
            if key not in {'mind_initialized', 'market_runtime_available', 'market_trading_ready', 'market_data_ready'}
        )

        should_reboot = bool(reboot_intent.get('pending')) or bool(self.init_error)
        can_reboot_now = len(blockers) == 0
        if should_reboot and can_reboot_now:
            decision = 'approve_reboot'
        elif can_reboot_now:
            decision = 'window_clear_no_reboot_requested'
        else:
            decision = 'hold_live_state'
        reason = 'downtime_window_clear' if can_reboot_now else ','.join(blockers)

        return {
            'service': 'aureon-mind-thought-action-hub',
            'generated_at': datetime.now().astimezone().isoformat(),
            'status': self._initialization_status(),
            'ok': ok,
            'flight_checks': flight_checks,
            'capabilities': {
                'connected_clients': len(self.clients),
                'recent_thoughts': len(self.recent_thoughts),
                'recent_actions': len(self.recent_actions),
                'registry_systems': len(self.registry.systems),
                'self_questioning_available': self.self_questioning_ai is not None,
            },
            'market_runtime': market,
            'goal_pursuit': goal_pursuit,
            'downtime_window': downtime,
            'reboot_intent': reboot_intent,
            'reboot_advice': {
                'decision': decision,
                'can_reboot_now': can_reboot_now,
                'should_reboot': should_reboot,
                'reason': reason,
                'blockers': blockers,
                'next_window_start_local': downtime.get('next_start_local'),
                'next_window_end_local': downtime.get('next_end_local'),
            },
            'self_questions': [
                'Am I serving health endpoints?',
                'Is ThoughtBus connected?',
                'Is the market runtime ready?',
                'Are positions or pending orders active?',
                'What is the best safe action toward the primary goal?',
                'Am I inside the configured downtime window?',
                'Can I reboot without reducing live capability?',
            ],
        }

    async def goal_pursuit_loop(self):
        """Continuously publish the hub's safest next-step assessment."""
        interval = os.environ.get('AUREON_GOAL_PURSUIT_INTERVAL_SEC', '60')
        try:
            interval_sec = max(15.0, float(interval))
        except Exception:
            interval_sec = 60.0

        while True:
            try:
                assessment = self._run_goal_pursuit_assessment()
                thought = self.thought_bus.publish(
                    Thought(
                        source='MindThoughtActionHub',
                        topic='goal.pursuit.assessment',
                        payload={
                            'primary_goal': assessment.get('primary_goal'),
                            'decision': assessment.get('decision'),
                            'active_modes': assessment.get('active_modes', []),
                            'blockers': assessment.get('blockers', []),
                            'next_best_actions': assessment.get('next_best_actions', []),
                            'generated_at': assessment.get('generated_at'),
                        },
                    )
                )
                if not self.recent_thoughts or self.recent_thoughts[-1].id != thought.id:
                    self._on_thought(thought)
            except Exception as e:
                logger.info(f"Goal pursuit assessment skipped: {e}")
            await asyncio.sleep(interval_sec)

    async def _init_systems_async(self):
        """Warm up cognitive systems without blocking the HTTP health surface."""
        if self.initialized or self.initializing:
            return

        self.initializing = True
        self.init_error = None
        try:
            await asyncio.to_thread(self._init_systems)
            self.initialized = True
            logger.info("Mind systems initialized")
            if self._self_questioning_enabled() and self.self_questioning_ai:
                self._self_questioning_task = asyncio.create_task(self.self_questioning_loop())
        except Exception as e:
            self.init_error = str(e)
            logger.exception("Mind system initialization failed")
        finally:
            self.initializing = False
    
    def _init_systems(self):
        """Initialize core cognitive systems."""
        logger.info("🧠 Initializing Mind systems...")
        
        # Scan workspace
        self.registry.scan_workspace()
        self._init_self_questioning_ai()
        if audit_mode_enabled():
            self.thought_bus.subscribe('*', self._on_thought)
            logger.info("Audit mode: heavy Queen/Nexus instances deferred; ThoughtBus is active")
            return
        logger.info(f"✅ Registered {len(self.registry.systems)} systems")
        
        load_optional_system_classes()

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
    
    def _init_self_questioning_ai(self):
        """Wire the local Ollama + Obsidian self-questioning loop."""
        cls = load_self_questioning_ai_class()
        if cls is None:
            logger.info("Self-questioning AI unavailable")
            return
        try:
            self.self_questioning_ai = cls(thought_bus=self.thought_bus)
            logger.info("Self-questioning AI wired to Ollama, Obsidian, and ThoughtBus")
        except Exception as e:
            self.self_questioning_ai = None
            logger.info(f"Self-questioning AI not started: {e}")

    def _self_questioning_enabled(self) -> bool:
        val = os.environ.get("AUREON_SELF_QUESTIONING_AI", "1").strip().lower()
        return val not in {"0", "false", "no", "off"}

    def _schedule_broadcast(self, message: Dict):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(message))
        except RuntimeError:
            return

    def _on_thought(self, thought: Thought):
        """Handle thought from ThoughtBus."""
        self.recent_thoughts.append(thought)
        
        # Broadcast to connected clients
        self._schedule_broadcast({
            'type': 'thought',
            'thought': {
                'id': thought.id,
                'ts': thought.ts,
                'source': thought.source,
                'topic': thought.topic,
                'payload': thought.payload
            }
        })
        
        # Track actions
        if thought.topic.startswith('execution.') or thought.topic.startswith('order.'):
            self.recent_actions.append({
                'type': thought.topic,
                'details': str(thought.payload),
                'ts': thought.ts
            })
            
            self._schedule_broadcast({
                'type': 'action',
                'action': {
                    'type': thought.topic,
                    'details': str(thought.payload)
                }
            })
    
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
        if not self.initialized:
            return web.json_response({
                'nodes': [],
                'edges': [],
                'categories': [],
                'status': self._initialization_status(),
                'initialized': self.initialized,
                'initializing': self.initializing,
                'init_error': self.init_error,
            })
        return web.json_response(self.registry.export_mind_map_data())
    
    async def handle_thoughts(self, request):
        """API endpoint for recent thoughts."""
        return web.json_response({
            'status': self._initialization_status(),
            'initialized': self.initialized,
            'initializing': self.initializing,
            'init_error': self.init_error,
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

    async def handle_flight_test(self, request):
        """Internal self-flight-test and reboot advice endpoint."""
        return web.json_response(self._run_internal_flight_test())

    async def handle_goal_pursuit(self, request):
        """API endpoint for the current safest goal-pursuit assessment."""
        return web.json_response(self._run_goal_pursuit_assessment())

    def _coding_cors_headers(self) -> Dict[str, str]:
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }

    async def handle_coding_options(self, request):
        """CORS preflight for the local coding organism prompt lane."""
        return web.Response(status=204, headers=self._coding_cors_headers())

    async def handle_coding_status(self, request):
        """API endpoint for Aureon's coding organism bridge status."""
        try:
            from aureon.autonomous.aureon_coding_organism_bridge import get_coding_organism_status

            payload = await asyncio.to_thread(get_coding_organism_status)
            return web.json_response(payload, headers=self._coding_cors_headers())
        except Exception as exc:
            return web.json_response(
                {"available": False, "error": str(exc)},
                status=500,
                headers=self._coding_cors_headers(),
            )

    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def _autonomous_self_run_status_payload(self) -> Dict[str, Any]:
        root = self._repo_root()
        candidates = [
            root / "frontend" / "public" / "aureon_autonomous_self_run_loop.json",
            root / "state" / "aureon_autonomous_self_run_loop_last_run.json",
        ]
        for path in candidates:
            try:
                if path.exists():
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(payload, dict):
                        payload.setdefault("available", True)
                        payload.setdefault("source_path", str(path))
                        return payload
            except Exception:
                continue
        return {
            "available": False,
            "status": "self_run_waiting_for_first_cycle",
            "ok": False,
            "source_path": "",
            "summary": {"loop_active": False, "cycle_count": 0},
        }

    def _run_autonomous_self_run_tick(
        self,
        prompt: str = "",
        *,
        include_stress: bool = False,
        max_stress_attempts: int = 1,
    ) -> Dict[str, Any]:
        from aureon.autonomous.aureon_autonomous_self_run_loop import build_and_write_autonomous_self_run_loop

        return build_and_write_autonomous_self_run_loop(
            root=self._repo_root(),
            prompt=prompt,
            cycles=1,
            interval_seconds=0.0,
            include_stress=include_stress,
            max_stress_attempts=max(1, int(max_stress_attempts or 1)),
        )

    async def handle_autonomous_self_run_status(self, request):
        """API endpoint for the current autonomous self-run loop evidence."""
        try:
            payload = await asyncio.to_thread(self._autonomous_self_run_status_payload)
            return web.json_response(payload, headers=self._coding_cors_headers())
        except Exception as exc:
            return web.json_response(
                {"available": False, "ok": False, "error": str(exc)},
                status=500,
                headers=self._coding_cors_headers(),
            )

    async def handle_autonomous_self_run_tick(self, request):
        """Run one bounded autonomous self-run cycle on demand."""
        try:
            try:
                body = await request.json()
            except Exception:
                body = {}
            prompt = str(body.get("prompt") or "").strip()
            include_stress = bool(body.get("include_stress", False))
            max_stress_attempts = int(body.get("max_stress_attempts") or 1)
            payload = await asyncio.to_thread(
                self._run_autonomous_self_run_tick,
                prompt,
                include_stress=include_stress,
                max_stress_attempts=max_stress_attempts,
            )
            self.recent_actions.append({
                "ts": time.time(),
                "source": "mind_thought_action_hub",
                "type": "autonomous_self_run_tick",
                "summary": prompt[:120],
                "status": payload.get("status"),
            })
            return web.json_response(payload, headers=self._coding_cors_headers())
        except Exception as exc:
            return web.json_response(
                {"ok": False, "error": str(exc)},
                status=500,
                headers=self._coding_cors_headers(),
            )

    def _autonomous_jobs_status_payload(self, job_id: str = "") -> Dict[str, Any]:
        from aureon.autonomous.aureon_autonomous_job_executor import get_autonomous_job_status

        return get_autonomous_job_status(root=self._repo_root(), job_id=job_id)

    def _run_autonomous_jobs_tick(self, job_id: str = "") -> Dict[str, Any]:
        from aureon.autonomous.aureon_autonomous_job_executor import tick_autonomous_jobs

        return tick_autonomous_jobs(root=self._repo_root(), job_id=job_id)

    async def handle_autonomous_jobs_status(self, request):
        """API endpoint for the durable autonomous job queue."""
        try:
            payload = await asyncio.to_thread(self._autonomous_jobs_status_payload)
            return web.json_response(payload, headers=self._coding_cors_headers())
        except Exception as exc:
            return web.json_response(
                {"available": False, "ok": False, "error": str(exc)},
                status=500,
                headers=self._coding_cors_headers(),
            )

    async def handle_autonomous_job_detail(self, request):
        """API endpoint for one durable autonomous job."""
        try:
            job_id = str(request.match_info.get("job_id") or "").strip()
            payload = await asyncio.to_thread(self._autonomous_jobs_status_payload, job_id)
            return web.json_response(payload, headers=self._coding_cors_headers())
        except Exception as exc:
            return web.json_response(
                {"available": False, "ok": False, "error": str(exc)},
                status=500,
                headers=self._coding_cors_headers(),
            )

    async def handle_autonomous_jobs_tick(self, request):
        """Advance one queued or repairing autonomous job."""
        try:
            try:
                body = await request.json()
            except Exception:
                body = {}
            job_id = str(body.get("job_id") or "").strip()
            payload = await asyncio.to_thread(self._run_autonomous_jobs_tick, job_id)
            self.recent_actions.append({
                "ts": time.time(),
                "source": "mind_thought_action_hub",
                "type": "autonomous_jobs_tick",
                "summary": job_id or "next job",
                "status": payload.get("status"),
            })
            return web.json_response(payload, headers=self._coding_cors_headers())
        except Exception as exc:
            return web.json_response(
                {"ok": False, "error": str(exc)},
                status=500,
                headers=self._coding_cors_headers(),
            )

    async def handle_coding_prompt(self, request):
        """Accept an operator coding prompt and route it through Aureon's own coding systems."""
        try:
            body = await request.json()
        except Exception:
            raw = await request.text()
            body = {"prompt": raw}

        prompt = str(body.get("prompt") or body.get("goal") or body.get("message") or "").strip()
        if not prompt:
            return web.json_response(
                {"ok": False, "error": "prompt is required"},
                status=400,
                headers=self._coding_cors_headers(),
            )

        run_tests = bool(body.get("run_tests", True))
        include_desktop = bool(body.get("include_desktop", True))
        scope_answers = body.get("scope_answers") if isinstance(body.get("scope_answers"), dict) else {}
        scope_approved = bool(body.get("scope_approved", False))
        base_job_id = str(body.get("base_job_id") or "").strip()
        try:
            from aureon.autonomous.aureon_coding_organism_bridge import submit_coding_prompt

            result = await asyncio.to_thread(
                submit_coding_prompt,
                prompt,
                source="mind_thought_action_hub",
                run_tests=run_tests,
                include_desktop=include_desktop,
                scope_answers=scope_answers,
                scope_approved=scope_approved,
                base_job_id=base_job_id,
            )
            try:
                from aureon.autonomous.aureon_autonomous_job_executor import enqueue_and_tick_autonomous_job

                job_state = await asyncio.to_thread(
                    enqueue_and_tick_autonomous_job,
                    prompt,
                    root=self._repo_root(),
                    source="mind_thought_action_hub",
                    priority=str(body.get("priority") or "P50"),
                    attempt_budget=int(body.get("attempt_budget") or 2),
                    metadata={"base_job_id": base_job_id, "scope_approved": scope_approved},
                )
                job_summary = job_state.get("summary", {}) if isinstance(job_state.get("summary"), dict) else {}
                active_job = job_state.get("active_job", {}) if isinstance(job_state.get("active_job"), dict) else {}
                recent_jobs = job_state.get("jobs") or []
                current_job = active_job or (recent_jobs[-1] if recent_jobs else {})
                result["autonomous_job_executor"] = {
                    "schema_version": job_state.get("schema_version"),
                    "status": job_state.get("status"),
                    "ok": job_state.get("ok"),
                    "summary": job_summary,
                    "active_job": active_job,
                    "current_job": current_job,
                    "recent_jobs": recent_jobs[-5:],
                }
                if not isinstance(result.get("summary"), dict):
                    result["summary"] = {}
                result["summary"]["autonomous_job_executor_status"] = job_state.get("status")
                if not isinstance(result.get("work_journal"), dict):
                    result["work_journal"] = {}
                if not isinstance(result["work_journal"].get("stages"), list):
                    result["work_journal"]["stages"] = []
                result["work_journal"]["stages"].append(
                    {
                        "step": "Durable autonomous job executor",
                        "status": "completed" if job_state.get("ok") else "attention",
                        "evidence": {
                            "status": job_state.get("status"),
                            "current_job_id": job_summary.get("current_job_id") or current_job.get("job_id"),
                            "current_job_state": job_summary.get("current_job_state") or current_job.get("state"),
                            "queue_depth": job_summary.get("queue_depth"),
                        },
                    }
                )
            except Exception as job_exc:
                result["autonomous_job_executor"] = {
                    "status": "autonomous_job_enqueue_failed",
                    "ok": False,
                    "error": str(job_exc),
                }
            try:
                self_run = await asyncio.to_thread(
                    self._run_autonomous_self_run_tick,
                    prompt,
                    include_stress=False,
                    max_stress_attempts=1,
                )
                result["autonomous_self_run_loop"] = {
                    "schema_version": self_run.get("schema_version"),
                    "status": self_run.get("status"),
                    "ok": self_run.get("ok"),
                    "summary": self_run.get("summary", {}),
                    "heartbeat": self_run.get("heartbeat", {}),
                    "autonomous_work_orders": (self_run.get("autonomous_work_orders") or [])[:8],
                    "hard_boundary_holds": self_run.get("hard_boundary_holds") or [],
                }
                if not isinstance(result.get("summary"), dict):
                    result["summary"] = {}
                result["summary"]["autonomous_self_run_prompt_wake"] = self_run.get("status")
                if not isinstance(result.get("work_journal"), dict):
                    result["work_journal"] = {}
                if not isinstance(result["work_journal"].get("stages"), list):
                    result["work_journal"]["stages"] = []
                result["work_journal"]["stages"].append(
                    {
                        "step": "Autonomous self-run prompt wake",
                        "status": "completed" if self_run.get("ok") else "attention",
                        "evidence": {
                            "status": self_run.get("status"),
                            "loop_active": (self_run.get("summary") or {}).get("loop_active"),
                            "hard_boundary_holds": (self_run.get("summary") or {}).get("hard_boundary_hold_count"),
                        },
                    }
                )
            except Exception as self_run_exc:
                result["autonomous_self_run_loop"] = {
                    "status": "self_run_prompt_wake_failed",
                    "ok": False,
                    "error": str(self_run_exc),
                }
            self.recent_actions.append({
                "ts": time.time(),
                "source": "mind_thought_action_hub",
                "type": "coding_prompt",
                "summary": prompt[:120],
                "status": result.get("status"),
            })
            return web.json_response(result, headers=self._coding_cors_headers())
        except Exception as exc:
            return web.json_response(
                {"ok": False, "error": str(exc)},
                status=500,
                headers=self._coding_cors_headers(),
            )

    def _get_phi_bridge(self):
        if self._phi_bridge is None:
            from aureon.harmonic.phi_bridge import get_phi_bridge

            self._phi_bridge = get_phi_bridge()
        return self._phi_bridge

    def _get_phi_voice_adapter(self):
        if self._phi_voice_adapter is not None and self._phi_voice_adapter_needs_reload(self._phi_voice_adapter):
            self._phi_voice_adapter = None
        if self._phi_voice_adapter is None:
            from aureon.inhouse_ai.llm_adapter import build_voice_adapter

            self._phi_voice_adapter = build_voice_adapter()
        return self._phi_voice_adapter

    def _phi_voice_adapter_needs_reload(self, adapter: Any) -> bool:
        model = str(getattr(adapter, "model", "") or getattr(adapter, "_model", "") or "").lower()
        if model in {"no-backend", "ollama-unavailable", "anthropic-unconfigured"}:
            return True
        return False

    def _reload_phi_voice_adapter(self) -> Dict[str, Any]:
        self._phi_voice_adapter = None
        adapter = self._get_phi_voice_adapter()
        model = str(getattr(adapter, "model", "") or getattr(adapter, "_model", "") or "")
        return {
            "ok": not self._phi_voice_adapter_needs_reload(adapter),
            "adapter_class": adapter.__class__.__name__,
            "adapter_model": model,
            "backend": os.environ.get("AUREON_VOICE_BACKEND", "") or "auto",
            "llm_model": os.environ.get("AUREON_LLM_MODEL", ""),
            "llm_http_allowed_in_audit": os.environ.get("AUREON_LLM_ALLOW_HTTP_IN_AUDIT", ""),
        }

    def _phi_refresh_interval_ms(self, bridge_info: Dict[str, Any]) -> int:
        cadence = bridge_info.get("cadence") if isinstance(bridge_info, dict) else {}
        try:
            interval_s = float((cadence or {}).get("interval_s") or 0.382)
        except Exception:
            interval_s = 0.382
        # Keep the dashboard close to the phi heartbeat while staying gentle on the local hub.
        return int(max(618, min(1618, interval_s * 1000.0)))

    def _redact_phi_context(self, value: Any, depth: int = 0) -> Any:
        if depth > 3:
            return "[truncated]"
        if isinstance(value, dict):
            clean: Dict[str, Any] = {}
            for key, item in list(value.items())[:40]:
                text_key = str(key)
                lowered = text_key.lower()
                if any(token in lowered for token in ("secret", "token", "password", "api_key", "apikey", "credential")):
                    clean[text_key] = "[redacted]"
                else:
                    clean[text_key] = self._redact_phi_context(item, depth + 1)
            return clean
        if isinstance(value, list):
            return [self._redact_phi_context(item, depth + 1) for item in value[:20]]
        if isinstance(value, str):
            return value[:1200] + ("..." if len(value) > 1200 else "")
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        return str(value)[:400]

    def _recent_phi_messages(self, limit: int = 8) -> List[Dict[str, Any]]:
        return list(self.phi_chat_history)[-max(1, int(limit)):]

    def _compact_phi_status_for_llm(self, status: Dict[str, Any]) -> Dict[str, Any]:
        ollama = status.get("ollama_cognitive_bridge") if isinstance(status.get("ollama_cognitive_bridge"), dict) else {}
        ollama_summary = ollama.get("summary") if isinstance(ollama.get("summary"), dict) else {}
        chat = status.get("chat") if isinstance(status.get("chat"), dict) else {}
        return {
            "phi_status": status.get("status"),
            "hub_status": status.get("hub_status"),
            "adapter_model": chat.get("adapter_model"),
            "adapter_class": chat.get("adapter_class"),
            "backend": chat.get("backend"),
            "llm_model": chat.get("llm_model"),
            "ollama_status": ollama.get("status"),
            "ollama_reachable": ollama_summary.get("ollama_reachable"),
            "resolved_model": ollama_summary.get("resolved_model"),
            "hnc_auris_ready": ollama_summary.get("hnc_auris_ready"),
            "metacognitive_ready": ollama_summary.get("metacognitive_ready"),
            "role_contracts_ready": ollama_summary.get("role_contracts_ready"),
            "authority": status.get("authority_boundaries", [])[:5],
        }

    def _phi_bridge_status_payload(self) -> Dict[str, Any]:
        try:
            bridge_info = self._get_phi_bridge().info()
            available = True
            error = ""
        except Exception as exc:
            bridge_info = {
                "ok": False,
                "service": "phi_bridge",
                "cadence": {"interval_s": 1.0, "frequency_hz": 1.0, "peer_count": 0},
                "peer_count": 0,
                "desktop": {},
            }
            available = False
            error = str(exc)

        adapter_model = ""
        adapter_class = ""
        adapter_ready = False
        try:
            adapter = self._get_phi_voice_adapter()
            adapter_model = str(getattr(adapter, "model", "") or getattr(adapter, "_model", "") or "")
            adapter_class = adapter.__class__.__name__
            adapter_ready = True
        except Exception:
            adapter_ready = False

        ollama_cognitive = self._ollama_cognitive_status_payload()

        return {
            "ok": available,
            "available": available,
            "error": error,
            "status": "phi_bridge_live_chat_ready" if available else "phi_bridge_unavailable",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "service": "aureon_phi_bridge_chat",
            "hub_initialized": self.initialized,
            "hub_status": self._initialization_status(),
            "refresh_interval_ms": self._phi_refresh_interval_ms(bridge_info),
            "phi_bridge": bridge_info,
            "chat": {
                "endpoint": "POST /api/phi-bridge/chat",
                "history_count": len(self.phi_chat_history),
                "recent": self._recent_phi_messages(6),
                "adapter_ready": adapter_ready,
                "adapter_model": adapter_model,
                "adapter_class": adapter_class,
                "backend": os.environ.get("AUREON_VOICE_BACKEND", "") or "auto",
                "llm_model": os.environ.get("AUREON_LLM_MODEL", ""),
                "llm_http_allowed_in_audit": os.environ.get("AUREON_LLM_ALLOW_HTTP_IN_AUDIT", ""),
            },
            "ollama_cognitive_bridge": ollama_cognitive,
            "authority_boundaries": [
                "read-only dashboard conversation",
                "no live trading mutation",
                "no payment or filing mutation",
                "no credential reveal",
                "no destructive OS action",
            ],
            "who_what_where_when_how_act": {
                "who": "MindThoughtActionHub + PhiBridge + local voice adapter",
                "what": "Live operator conversation and dashboard heartbeat evidence",
                "where": "http://127.0.0.1:13002/api/phi-bridge/chat",
                "when": "on operator chat and phi-cadenced dashboard refresh",
                "how": "redacted context, local/in-house LLM adapter, ThoughtBus publication, safe fallback",
                "act": "answer, publish evidence, keep mutation gates closed",
            },
        }

    def _ollama_cognitive_status_payload(self, force: bool = False) -> Dict[str, Any]:
        cache_age = time.time() - float(self._ollama_cognitive_status_cache_at or 0.0)
        if not force and self._ollama_cognitive_status_cache and cache_age < 5.0:
            return self._ollama_cognitive_status_cache
        try:
            from aureon.autonomous.aureon_ollama_cognitive_bridge import (
                build_and_write_ollama_cognitive_bridge,
            )

            payload = build_and_write_ollama_cognitive_bridge()
        except Exception as exc:
            payload = {
                "schema_version": "aureon-ollama-cognitive-bridge-v1",
                "ok": False,
                "status": "ollama_cognitive_bridge_error",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
                "summary": {
                    "ollama_reachable": False,
                    "cognitive_ready": False,
                    "hand_in_hand_ready": False,
                },
                "next_actions": [
                    {
                        "id": "inspect_ollama_cognitive_bridge",
                        "severity": "blocking",
                        "action": "Run the bridge module directly to see the local error.",
                        "powershell": ".\\.venv\\Scripts\\python.exe -m aureon.autonomous.aureon_ollama_cognitive_bridge --json",
                    }
                ],
            }
        self._ollama_cognitive_status_cache = payload
        self._ollama_cognitive_status_cache_at = time.time()
        return payload

    def _fallback_phi_reply(self, message: str, context: Dict[str, Any], reason: str) -> str:
        coding = context.get("coding") if isinstance(context.get("coding"), dict) else {}
        status = coding.get("status") or coding.get("summary_status") or "dashboard observed"
        scope = coding.get("scope_status") or "scope state unknown"
        route_clean = coding.get("route_clean")
        route_text = "route clean" if route_clean else "route needs attention" if route_clean is False else "route state unknown"
        return (
            "I am connected to the Phi Bridge and the local cockpit, but the live LLM backend did not return a usable reply. "
            f"Reason: {reason}. Current coding lane: {status}; scope: {scope}; {route_text}. "
            "I can still keep the dashboard live, publish evidence, and route coding prompts through the organism. "
            "For full conversation, start Ollama, set AUREON_VOICE_BACKEND=ollama_hybrid, "
            "set AUREON_LLM_ALLOW_HTTP_IN_AUDIT=1 for local-only safe observation, and reload the Phi adapter."
        )

    @staticmethod
    def _operator_name_from_message(message: str) -> str:
        text = str(message or "").strip()
        match = re.search(r"\bmy name is\s+(.+)$", text, flags=re.I)
        if not match:
            match = re.search(r"\bi am\s+([A-Za-z][A-Za-z .'-]{1,80})", text, flags=re.I)
        if not match:
            return ""
        candidate = match.group(1)
        candidate = re.split(r"[,.!?;]|\bcan you\b|\bwhat can\b|\bplease\b|\band\b", candidate, maxsplit=1, flags=re.I)[0]
        words = re.findall(r"[A-Za-z][A-Za-z'-]*", candidate)[:4]
        return " ".join(word[:1].upper() + word[1:].lower() for word in words).strip()

    @staticmethod
    def _phi_prompt_topic(message: str) -> str:
        lowered = str(message or "").lower()
        if "what can you see" in lowered and any(token in lowered for token in ("cockpit", "dashboard", "console")):
            return "cockpit_status"
        if any(phrase in lowered for phrase in ("what can you do", "capabilities", "capabilitys", "what can aureon do")):
            return "capabilities"
        if any(token in lowered for token in ("old game", "same game", "stale", "reuse", "unique", "not created", "got an old one")):
            return "fresh_artifact_fix"
        if re.search(r"\b(hello|hi|hey)\b", lowered) or "my name is" in lowered:
            return "greeting"
        return "general"

    @staticmethod
    def _score_phi_reply(message: str, reply: str, reply_source: str = "") -> Dict[str, Any]:
        topic = MindThoughtActionHub._phi_prompt_topic(message)
        text = str(reply or "").strip()
        lowered = text.lower()
        score = 1.0
        snags: List[str] = []

        if len(text) < 25:
            score -= 0.35
            snags.append("reply_too_short")
        if text.lstrip().startswith("{") or all(token in lowered for token in ("signal", "symbol", "coherence")):
            score -= 0.55
            snags.append("raw_internal_signal_leaked")
        for phrase in ("intent packet", "evidence packet", "draft packet", "context-weaver path"):
            if phrase in lowered:
                score -= 0.22
                snags.append("packet_scaffold_visible")
                break
        if "aureon's local brain fallback" in lowered and topic not in {"capabilities", "general"}:
            score -= 0.2
            snags.append("fallback_boilerplate")

        name = MindThoughtActionHub._operator_name_from_message(message)
        if name and name.lower() not in lowered:
            score -= 0.16
            snags.append("operator_name_not_acknowledged")
        if name and f"{name.lower()}. can you" in lowered:
            score -= 0.22
            snags.append("operator_name_overcaptured")

        if topic == "cockpit_status" and not any(token in lowered for token in ("status", "scope", "route", "tests", "snag", "ready")):
            score -= 0.28
            snags.append("cockpit_status_not_answered")
        if topic == "fresh_artifact_fix" and not any(
            token in lowered for token in ("fresh", "unique", "build id", "new url", "stale", "quality gate")
        ):
            score -= 0.36
            snags.append("stale_artifact_issue_not_answered")
        if topic == "capabilities" and not any(token in lowered for token in ("code", "test", "ui", "media", "research", "proof")):
            score -= 0.24
            snags.append("capabilities_not_specific")

        score = max(0.0, min(1.0, round(score, 3)))
        return {
            "schema_version": "aureon-phi-chat-response-quality-v1",
            "topic": topic,
            "score": score,
            "passed": score >= 0.78 and not {"raw_internal_signal_leaked", "packet_scaffold_visible"}.intersection(snags),
            "snags": snags,
            "reply_source": reply_source,
        }

    @staticmethod
    def _route_text(value: Any) -> str:
        if value is True:
            return "route clean"
        if value is False:
            return "route needs attention"
        return "route unknown"

    def _compiled_phi_operator_reply(self, message: str, context: Dict[str, Any], raw_reply: str = "") -> str:
        topic = self._phi_prompt_topic(message)
        coding = context.get("coding") if isinstance(context.get("coding"), dict) else {}
        status = coding.get("status") or coding.get("summary_status") or "dashboard observed"
        scope = coding.get("scope_status") or "scope unknown"
        tests_ok = coding.get("tests_ok")
        ready_to_run = coding.get("ready_to_run")
        snags = coding.get("blocking_snags", 0)
        route_text = self._route_text(coding.get("route_clean"))
        name = self._operator_name_from_message(message)

        if topic == "greeting":
            hello = f"Hi {name}." if name else "Hi."
            return (
                f"{hello} I am here in the Phi chat lane and I will speak to you like the operator, not dump internal signals at you.\n\n"
                f"Proof: the hub is reporting {status}; scope is {scope}; {route_text}; blocking snags are {snags}.\n\n"
                "Next action: tell me the job you want Aureon to do and I will translate it into the coding/media/UI/research lane, then explain the proof and blockers in plain language."
            )

        if topic == "cockpit_status":
            tests_text = "tests passed/ready" if tests_ok is True else "tests need proof" if tests_ok is False else "tests not reported"
            run_text = "handover looks ready" if ready_to_run is True else "handover is still gated" if ready_to_run is False else "handover state is not reported"
            return (
                "I can see the coding cockpit as the live client-job lane.\n\n"
                f"Status: {status}; scope: {scope}; {route_text}; {tests_text}; {run_text}; blocking snags: {snags}.\n\n"
                "What that means: you can send a build/fix request from the cockpit, and Aureon should scope it, route the crew, create or patch the artifact, test it, and only show handover when the quality gate passes."
            )

        if topic == "fresh_artifact_fix":
            return (
                "You were right about the old-game failure. The problem was stale handover: similar game prompts could point back at an older generated artifact instead of proving a fresh project.\n\n"
                "What is fixed now: each coding/app/tool build gets a fresh build ID and project ID, the public URL must contain that build ID, and the quality gate blocks handover if the artifact looks reused. The spaceship prompt is also checked for spaceship, enemies, shooting, score, lives, and waves instead of accepting the old platform game template.\n\n"
                "Next action: send the game prompt again from the cockpit. You should see a new URL each time; open the preview, test movement and shooting, then ask for upgrades like levels, bosses, sound, mobile controls, or save state."
            )

        if topic == "capabilities":
            return (
                "I can help as Aureon's operator-facing assistant: scope jobs, explain cockpit state, trigger coding routes, review proof, build local games/tools/media previews, run tests, surface snags, and keep the final handover hidden until quality passes.\n\n"
                "Boundaries stay active: no live trading mutation, payments, filings, credential reveal, or destructive OS action from chat.\n\n"
                "Next action: give me a concrete job, and I will tell you what Aureon will build, what proof it needs, and what is blocked."
            )

        cleaned = str(raw_reply or "").strip()
        if cleaned and not cleaned.lstrip().startswith("{") and "intent packet" not in cleaned.lower():
            return cleaned
        return (
            "I hear the request, but the raw model reply was not good enough to show directly.\n\n"
            f"Current cockpit proof: {status}; scope {scope}; {route_text}; blocking snags {snags}.\n\n"
            "Next action: I will answer in plain operator language, then route any actual build/fix through Aureon's safe local systems with proof before handover."
        )

    def _quality_gate_phi_reply(
        self,
        message: str,
        context: Dict[str, Any],
        reply: str,
        reply_source: str,
    ) -> Tuple[str, str, Dict[str, Any]]:
        quality = self._score_phi_reply(message, reply, reply_source)
        if quality.get("passed"):
            quality["compiler_applied"] = False
            return reply, reply_source, quality
        compiled = self._compiled_phi_operator_reply(message, context, reply)
        compiled_quality = self._score_phi_reply(message, compiled, "aureon_operator_compiler")
        compiled_quality.update(
            {
                "compiler_applied": True,
                "original_reply_source": reply_source,
                "original_snags": quality.get("snags", []),
                "original_score": quality.get("score", 0),
            }
        )
        return compiled, "aureon_operator_compiler", compiled_quality

    def _phi_chat_dynamic_filter_trace(self, message: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            from aureon.autonomous.aureon_dynamic_prompt_filter import build_dynamic_prompt_filter

            wrapped = (
                f"Operator message:\n{message}\n\n"
                f"Redacted dashboard context:\n{json.dumps(context, ensure_ascii=False)[:700]}\n\n"
                "Compact Phi/Ollama/Aureon status:\n{\"fallback\":\"timeout_or_brain\"}"
            )
            return build_dynamic_prompt_filter(
                [{"role": "user", "content": wrapped}],
                system="Aureon Phi chat",
                lane_hint="chat",
            )
        except Exception:
            return None

    def _quick_phi_dynamic_filter_trace(self, message: str, context: Dict[str, Any], topic: str) -> Dict[str, Any]:
        task_family = "system_health" if topic == "cockpit_status" else "coding" if topic == "fresh_artifact_fix" else "conversation"
        return {
            "schema_version": "aureon-dynamic-prompt-filter-v1",
            "filter_mode": "clear_operator_fast",
            "lane": "chat",
            "task_family": task_family,
            "user_intent": str(message or "")[:240],
            "source_packets": [],
            "organism_context_used": {
                "coding": context.get("coding") if isinstance(context.get("coding"), dict) else {},
                "fast_operator_chat": True,
                "topic": topic,
            },
            "ollama_shards": [],
            "hnc_auris_report": {
                "hnc_human_loop": {
                    "available": True,
                    "mode": "light_phi_operator_contract",
                    "intent": {"route": task_family},
                },
                "auris_voice_filter": {"accepted": True, "mode": "clear_operator_fast"},
            },
            "redactions": [],
            "response_contract": "direct answer, proof, blockers, next action",
            "final_reply_source": "aureon_operator_compiler",
            "handover_ready": True,
        }

    @staticmethod
    def _phi_dynamic_filter_summary(dynamic_filter_trace: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not dynamic_filter_trace:
            return {}
        return {
            "filter_mode": dynamic_filter_trace.get("filter_mode"),
            "lane": dynamic_filter_trace.get("lane"),
            "task_family": dynamic_filter_trace.get("task_family"),
            "source_packets": [
                {
                    "title": packet.get("title"),
                    "source_path": packet.get("source_path"),
                    "confidence": packet.get("confidence"),
                }
                for packet in dynamic_filter_trace.get("source_packets", [])
                if isinstance(packet, dict)
            ][:4],
            "hnc_auris_report": dynamic_filter_trace.get("hnc_auris_report", {}),
            "handover_ready": dynamic_filter_trace.get("handover_ready"),
        }

    def _brain_phi_fallback_reply(
        self,
        message: str,
        context: Dict[str, Any],
        reason: str,
    ) -> Tuple[str, str, str]:
        try:
            from aureon.inhouse_ai.llm_adapter import AureonBrainAdapter

            wrapped = (
                f"Operator message:\n{message}\n\n"
                f"Redacted dashboard context:\n{json.dumps(context, ensure_ascii=False)[:700]}\n\n"
                "Compact Phi/Ollama/Aureon status:\n{\"fallback\":\"brain_chat\"}"
            )
            response = AureonBrainAdapter().prompt(
                [{"role": "user", "content": wrapped}],
                system="Aureon Phi chat quick fallback",
                max_tokens=180,
                temperature=0.2,
            )
            reply = str(getattr(response, "text", "") or "").strip()
            model = str(getattr(response, "model", "") or "aureon-brain-v1")
            if reply and not reply.lstrip().startswith("{"):
                return reply, "aureon_brain_chat_fallback", model
            if reply:
                return (
                    "I heard you through the Phi Bridge. The local model did not finish in time, and the quick brain fallback produced a trading-shaped internal signal, so I am holding that as internal evidence instead of showing it as chat. No live order is authorized from this conversation; ask for a read-only trading explanation if that is what you meant.",
                    "aureon_brain_chat_fallback",
                    model,
                )
        except Exception:
            pass
        return self._fallback_phi_reply(message, context, reason), "guided_fallback", ""

    @staticmethod
    def _is_fast_phi_operator_chat(message: str) -> bool:
        lowered = str(message or "").lower()
        if any(
            phrase in lowered
            for phrase in (
                "what can you do",
                "what can aureon do",
                "what are your capabilities",
                "what can u do",
                "capabilitys",
                "capabilities",
            )
        ):
            return True
        if "what can you see" in lowered and any(token in lowered for token in ("cockpit", "dashboard", "console")):
            return True
        tokens = set(re.findall(r"[a-zA-Z0-9_]{3,}", str(message or "").lower()))
        tokens -= {"you", "the", "and", "are"}
        if not tokens:
            return True
        allowed = {
            "hello",
            "hey",
            "morning",
            "afternoon",
            "evening",
            "thanks",
            "thank",
            "name",
            "gary",
            "leckey",
        }
        return tokens.issubset(allowed)

    def _run_phi_chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        started = time.time()
        safe_context = self._redact_phi_context(context or {})
        status = self._phi_bridge_status_payload()
        system_prompt = (
            "You are Aureon speaking to the human operator through the Phi Bridge and the local coding cockpit. "
            "Use first person as Aureon. Be concise, concrete, and honest about what the dashboard evidence shows. "
            "Do not claim that files were changed, tests passed, trades executed, payments made, filings submitted, "
            "or credentials handled unless the supplied evidence explicitly proves it. Never reveal secrets. "
            "Keep live trading, payment, filing, credential, and destructive OS actions behind their existing gates."
        )
        history_messages = [
            {"role": str(item.get("role") or "user"), "content": str(item.get("text") or "")[:300]}
            for item in self._recent_phi_messages(2)
            if item.get("role") in {"user", "assistant"}
        ]
        if os.environ.get("AUREON_PHI_CHAT_INCLUDE_HISTORY", "0").strip().lower() not in {"1", "true", "yes", "on"}:
            history_messages = []
        compact_status = self._compact_phi_status_for_llm(status)
        messages = history_messages + [
            {
                "role": "user",
                "content": (
                    f"Operator message:\n{message}\n\n"
                    f"Redacted dashboard context:\n{json.dumps(safe_context, ensure_ascii=False)[:700]}\n\n"
                    f"Compact Phi/Ollama/Aureon status:\n{json.dumps(compact_status, ensure_ascii=False)[:1000]}"
                ),
            }
        ]

        reply_source = "local_llm"
        model = ""
        usage: Dict[str, Any] = {}
        response_raw: Any = None

        def classify_reply_source(adapter: Any, response_model: str, raw: Any) -> str:
            source_hint = " ".join(
                [
                    response_model,
                    str(getattr(adapter, "model", "") or getattr(adapter, "_model", "") or ""),
                    adapter.__class__.__name__,
                ]
            ).lower()
            if isinstance(raw, dict) and raw.get("weaver"):
                return "ollama_cognitive_weaver"
            if response_model.lower().startswith("aureon-brain"):
                return "aureon_brain_fallback"
            if "weaver" in source_hint:
                return "ollama_cognitive_weaver"
            if "hybrid" in source_hint:
                return "ollama_cognitive_hybrid"
            if "ollama" in source_hint:
                return "ollama_local"
            return "local_llm"

        fast_topic = self._phi_prompt_topic(message)
        if self._is_fast_phi_operator_chat(message) or fast_topic in {
            "greeting",
            "cockpit_status",
            "fresh_artifact_fix",
            "capabilities",
        }:
            dynamic_filter_trace = self._quick_phi_dynamic_filter_trace(message, safe_context, fast_topic)
            response_raw = {"dynamic_prompt_filter": dynamic_filter_trace} if dynamic_filter_trace else None
            reply = self._compiled_phi_operator_reply(message, safe_context)
            reply_source = "aureon_operator_compiler"
            model = "aureon-operator-compiler-v1"
            usage = {"fast_operator_chat": 1, "topic": fast_topic}
        else:
            try:
                adapter = self._get_phi_voice_adapter()
                response = adapter.prompt(
                    messages,
                    system=system_prompt,
                    max_tokens=int(os.environ.get("AUREON_PHI_CHAT_MAX_TOKENS", "120")),
                    temperature=float(os.environ.get("AUREON_PHI_CHAT_TEMPERATURE", "0.25")),
                    dynamic_prompt_lane="chat",
                )
                reply = str(getattr(response, "text", "") or "").strip()
                model = str(getattr(response, "model", "") or "")
                usage = getattr(response, "usage", {}) or {}
                response_raw = getattr(response, "raw", None)
                if not reply or reply.startswith("[ERROR]") or "No LLM backend is reachable" in reply:
                    if self._phi_voice_adapter_needs_reload(adapter):
                        self._phi_voice_adapter = None
                        adapter = self._get_phi_voice_adapter()
                        response = adapter.prompt(
                            messages,
                            system=system_prompt,
                            max_tokens=int(os.environ.get("AUREON_PHI_CHAT_MAX_TOKENS", "120")),
                            temperature=float(os.environ.get("AUREON_PHI_CHAT_TEMPERATURE", "0.25")),
                            dynamic_prompt_lane="chat",
                        )
                        reply = str(getattr(response, "text", "") or "").strip()
                        model = str(getattr(response, "model", "") or "")
                        usage = getattr(response, "usage", {}) or {}
                        response_raw = getattr(response, "raw", None)
                    if not reply or reply.startswith("[ERROR]") or "No LLM backend is reachable" in reply:
                        reply_source = "guided_fallback"
                        reply = self._fallback_phi_reply(message, safe_context, reply or "no usable LLM reply")
                    else:
                        reply_source = classify_reply_source(adapter, model, response_raw)
                else:
                    reply_source = classify_reply_source(adapter, model, response_raw)
            except Exception as exc:
                reply_source = "guided_fallback"
                reply = self._fallback_phi_reply(message, safe_context, str(exc))

        if chat_id and chat_id in self._phi_chat_timeout_ids:
            self._phi_chat_timeout_ids.discard(chat_id)
            return {
                "ok": True,
                "status": "phi_bridge_chat_late_reply_discarded",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "reply": "",
                "reply_source": "discarded_late_reply",
                "model": model,
                "usage": usage,
                "latency_ms": int((time.time() - started) * 1000),
                "history": self._recent_phi_messages(10),
                "context_summary": safe_context,
            }

        reply, reply_source, response_quality = self._quality_gate_phi_reply(
            message,
            safe_context,
            reply,
            reply_source,
        )
        generated_at = datetime.now(timezone.utc).isoformat()
        latency_ms = int((time.time() - started) * 1000)
        weaver_trace = response_raw if isinstance(response_raw, dict) and response_raw.get("weaver") else None
        dynamic_filter_trace = (
            response_raw.get("dynamic_prompt_filter")
            if isinstance(response_raw, dict) and isinstance(response_raw.get("dynamic_prompt_filter"), dict)
            else None
        )
        user_item = {"role": "user", "text": message[:1200], "ts": generated_at}
        assistant_item = {
            "role": "assistant",
            "text": reply,
            "ts": generated_at,
            "source": reply_source,
            "model": model,
            "latency_ms": latency_ms,
            "response_quality": response_quality,
        }
        if weaver_trace:
            assistant_item["weaver"] = {
                "policy": weaver_trace.get("policy"),
                "shards": [
                    {
                        "name": shard.get("name"),
                        "ok": shard.get("ok"),
                        "latency_ms": shard.get("latency_ms"),
                    }
                    for shard in weaver_trace.get("shards", [])
                    if isinstance(shard, dict)
                ],
            }
        dynamic_filter_summary = self._phi_dynamic_filter_summary(dynamic_filter_trace)
        if dynamic_filter_summary:
            assistant_item["dynamic_filter"] = dynamic_filter_summary
        self.phi_chat_history.append(user_item)
        self.phi_chat_history.append(assistant_item)

        thought = self.thought_bus.publish(
            Thought(
                source="MindThoughtActionHub",
                topic="phi_bridge.chat.reply",
                payload={
                    "message_preview": message[:160],
                    "reply_preview": reply[:240],
                    "reply_source": reply_source,
                    "model": model,
                    "latency_ms": latency_ms,
                    "weaver": bool(weaver_trace),
                    "dynamic_prompt_filter": bool(dynamic_filter_trace),
                    "response_quality_score": response_quality.get("score"),
                    "response_quality_passed": response_quality.get("passed"),
                    "generated_at": generated_at,
                },
            )
        )
        if not self.recent_thoughts or self.recent_thoughts[-1].id != thought.id:
            self._on_thought(thought)
        self.recent_actions.append({
            "ts": time.time(),
            "source": "mind_thought_action_hub",
            "type": "phi_bridge_chat",
            "summary": message[:120],
            "status": reply_source,
        })

        return {
            "ok": True,
            "status": "phi_bridge_chat_replied",
            "generated_at": generated_at,
            "reply": reply,
            "reply_source": reply_source,
            "model": model,
            "usage": usage,
            "latency_ms": latency_ms,
            "refresh_interval_ms": status.get("refresh_interval_ms"),
            "phi_bridge": status.get("phi_bridge", {}),
            "history": self._recent_phi_messages(10),
            "context_summary": safe_context,
            "who_what_where_when_how_act": status.get("who_what_where_when_how_act", {}),
            "weaver_trace": weaver_trace,
            "dynamic_prompt_filter": dynamic_filter_trace,
            "response_quality": response_quality,
        }

    async def handle_phi_bridge_status(self, request):
        """Live status for the Phi Bridge backed chat lane."""
        return web.json_response(self._phi_bridge_status_payload(), headers=self._coding_cors_headers())

    async def handle_phi_bridge_reload(self, request):
        """Reset the cached Phi voice adapter so Ollama/Aureon env changes are picked up."""
        payload = self._reload_phi_voice_adapter()
        payload.update({
            "status": "phi_bridge_voice_adapter_reloaded",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ollama_cognitive_bridge": self._ollama_cognitive_status_payload(force=True),
        })
        return web.json_response(payload, headers=self._coding_cors_headers())

    async def handle_ollama_cognitive_status(self, request):
        """Live proof that Ollama and Aureon's cognitive systems are handshaking."""
        force = str(request.query.get("refresh", "")).lower() in {"1", "true", "yes"}
        return web.json_response(
            self._ollama_cognitive_status_payload(force=force),
            headers=self._coding_cors_headers(),
        )

    async def handle_phi_bridge_chat(self, request):
        """Let the operator talk to Aureon through the Phi Bridge and local voice adapter."""
        try:
            body = await request.json()
        except Exception:
            raw = await request.text()
            body = {"message": raw}
        message = str(body.get("message") or body.get("prompt") or body.get("question") or "").strip()
        if not message:
            return web.json_response(
                {"ok": False, "error": "message is required"},
                status=400,
                headers=self._coding_cors_headers(),
            )
        context = body.get("context") if isinstance(body.get("context"), dict) else {}
        try:
            timeout_s = max(3.0, float(os.environ.get("AUREON_PHI_CHAT_TIMEOUT_S", "12")))
        except Exception:
            timeout_s = 12.0
        chat_id = f"{time.time_ns()}-{len(self.phi_chat_history)}"
        try:
            payload = await asyncio.wait_for(
                asyncio.to_thread(self._run_phi_chat, message, context, chat_id),
                timeout=timeout_s,
            )
            return web.json_response(payload, headers=self._coding_cors_headers())
        except asyncio.TimeoutError:
            self._phi_chat_timeout_ids.add(chat_id)
            if len(self._phi_chat_timeout_ids) > 256:
                self._phi_chat_timeout_ids.clear()
            safe_context = self._redact_phi_context(context)
            generated_at = datetime.now(timezone.utc).isoformat()
            dynamic_filter_trace = self._phi_chat_dynamic_filter_trace(message, safe_context)
            dynamic_filter_summary = self._phi_dynamic_filter_summary(dynamic_filter_trace)
            reply, reply_source, model = self._brain_phi_fallback_reply(
                message,
                safe_context,
                f"LLM response timed out after {timeout_s:.0f}s",
            )
            reply, reply_source, response_quality = self._quality_gate_phi_reply(
                message,
                safe_context,
                reply,
                reply_source,
            )
            self.phi_chat_history.append({"role": "user", "text": message[:1200], "ts": generated_at})
            assistant_item = {
                "role": "assistant",
                "text": reply,
                "ts": generated_at,
                "source": reply_source,
                "model": model,
                "latency_ms": int(timeout_s * 1000),
                "response_quality": response_quality,
            }
            if dynamic_filter_summary:
                assistant_item["dynamic_filter"] = dynamic_filter_summary
            self.phi_chat_history.append(assistant_item)
            thought = self.thought_bus.publish(
                Thought(
                    source="MindThoughtActionHub",
                    topic="phi_bridge.chat.reply",
                    payload={
                        "message_preview": message[:160],
                        "reply_preview": reply[:240],
                        "reply_source": reply_source,
                        "model": model,
                        "latency_ms": int(timeout_s * 1000),
                        "dynamic_prompt_filter": bool(dynamic_filter_trace),
                        "response_quality_score": response_quality.get("score"),
                        "response_quality_passed": response_quality.get("passed"),
                        "generated_at": generated_at,
                    },
                )
            )
            if not self.recent_thoughts or self.recent_thoughts[-1].id != thought.id:
                self._on_thought(thought)
            self.recent_actions.append({
                "ts": time.time(),
                "source": "mind_thought_action_hub",
                "type": "phi_bridge_chat",
                "summary": message[:120],
                "status": f"{reply_source}_timeout",
            })
            payload = {
                "ok": True,
                "status": "phi_bridge_chat_replied",
                "generated_at": generated_at,
                "reply": reply,
                "reply_source": reply_source,
                "model": model,
                "usage": {},
                "latency_ms": int(timeout_s * 1000),
                "history": self._recent_phi_messages(10),
                "context_summary": safe_context,
                "dynamic_prompt_filter": dynamic_filter_trace,
                "response_quality": response_quality,
            }
            return web.json_response(payload, headers=self._coding_cors_headers())

    async def handle_self_questioning_status(self, request):
        """API endpoint for the Ollama + Obsidian self-questioning loop."""
        if not self.self_questioning_ai:
            return web.json_response({
                'available': False,
                'status': self._initialization_status(),
                'initialized': self.initialized,
                'initializing': self.initializing,
            }, status=503)
        return web.json_response({
            'available': True,
            'enabled': self._self_questioning_enabled(),
            'status': self.self_questioning_ai.get_status(),
        })

    async def handle_self_questioning_ask(self, request):
        """Run one safe self-questioning cycle on demand."""
        if not self.self_questioning_ai:
            return web.json_response({'error': 'self_questioning_ai unavailable'}, status=503)
        try:
            body = await request.json()
        except Exception:
            body = {}
        questions = body.get('questions')
        if not questions and body.get('question'):
            questions = [body.get('question')]
        cycle = await asyncio.to_thread(
            self.self_questioning_ai.run_cycle,
            questions=questions,
            include_audit=bool(body.get('include_audit', True)),
            include_self_scan=bool(body.get('include_self_scan', True)),
        )
        self.mind_stats['Self Questioning Cycles'] += 1
        return web.json_response(cycle.to_dict())
    
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

    async def self_questioning_loop(self):
        """Periodic safe self-questioning using Ollama and Obsidian."""
        if not self.self_questioning_ai:
            return
        await asyncio.sleep(float(os.environ.get("AUREON_SELF_QUESTIONING_START_DELAY_S", "10")))
        interval = max(60.0, float(os.environ.get("AUREON_SELF_QUESTION_INTERVAL_S", "300")))
        logger.info("Starting self-questioning AI loop")
        while self._self_questioning_enabled():
            try:
                cycle = await asyncio.to_thread(
                    self.self_questioning_ai.run_cycle,
                    questions=None,
                    include_audit=True,
                    include_self_scan=True,
                )
                self.mind_stats['Self Questioning Cycles'] += 1
                await self.broadcast({
                    'type': 'self_questioning_cycle',
                    'cycle': {
                        'cycle_id': cycle.cycle_id,
                        'summary': cycle.summary,
                        'answer_source': cycle.answer_source,
                        'note_path': cycle.note_path,
                    }
                })
            except Exception as e:
                logger.error(f"Self-questioning loop error: {e}")
            await asyncio.sleep(interval)
    
    async def generate_test_thoughts(self):
        """Generate test thoughts for demonstration.

        ⚠ Publishes synthetic Thoughts onto the bus (fake confidences,
        topics, payloads). Gated behind AUREON_ALLOW_SIM_FALLBACK so
        production refuses to inject fake thoughts into the live system.
        """
        from aureon.observer.live_data_policy import (
            simulation_fallback_allowed, log_blocked_fallback,
        )
        if not simulation_fallback_allowed():
            log_blocked_fallback("aureon_mind_thought_action_hub.generate_test_thoughts",
                                 "synthetic_thoughts")
            return
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
        self._goal_pursuit_task = asyncio.create_task(self.goal_pursuit_loop())
        self._init_task = asyncio.create_task(self._init_systems_async())
        
        print(f"\n{'='*80}")
        print(f"🧠💭⚡ AUREON MIND → THOUGHT → ACTION HUB")
        print(f"{'='*80}")
        print(f"🌐 Dashboard: http://localhost:{self.port}")
        print(f"📡 WebSocket: ws://localhost:{self.port}/ws")
        print(f"\n✨ COGNITIVE ARCHITECTURE:")
        print(f"   🧠 MIND:    initializing in background")
        print(f"   💭 THOUGHT: ThoughtBus (real-time streaming)")
        print(f"   ⚡ ACTION:  Execution layer monitoring")
        print(f"\n📊 SYSTEMS INTEGRATED:")
        print(f"   • HTTP health endpoint: READY")
        print(f"   • System registry: warming up")
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
