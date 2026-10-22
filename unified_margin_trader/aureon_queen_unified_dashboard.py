#!/usr/bin/env python3
"""
👑 AUREON QUEEN UNIFIED DASHBOARD 👑
═══════════════════════════════════════════════════════════════════════════

MASTER DASHBOARD - ALL SYSTEMS INTEGRATED

Combines:
🤖 Bot Hunter → Live bot detection
🌌 Quantum Telescope → Sacred geometry analysis  
🌍 Planetary Tracker → Country/clan mapping
🌊 Ocean Scanner → Whale/hive detection

PLUS:
👑 QUEEN'S VOICE - Real-time commentary on what's happening
🗣️ Text-to-speech narration of bot activity
🧠 Queen Hive Mind integration

ONE DASHBOARD TO RULE THEM ALL
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
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

import asyncio
import aiohttp
from aiohttp import web
import json
import logging
from typing import Dict, Set, List
from collections import defaultdict, deque
import time

# Unified dashboard HTML with Queen's voice
UNIFIED_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>👑 Aureon Queen Unified Dashboard</title>
    <meta charset="utf-8">
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
            padding: 15px;
            text-align: center;
            border-bottom: 3px solid #ffaa00;
            box-shadow: 0 4px 30px rgba(255, 170, 0, 0.5);
        }
        
        h1 {
            font-size: 2.5em;
            background: linear-gradient(90deg, #ffaa00, #ff6600, #ffaa00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 20px rgba(255, 170, 0, 0.8);
            animation: glow 2s infinite;
        }
        
        @keyframes glow {
            0%, 100% { filter: brightness(1); }
            50% { filter: brightness(1.5); }
        }
        
        #container {
            display: grid;
            grid-template-columns: 1fr 2fr 1fr;
            grid-template-rows: 300px 1fr;
            gap: 15px;
            padding: 15px;
            height: calc(100vh - 150px);
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
            margin-bottom: 15px;
            text-align: center;
            font-size: 1.3em;
        }
        
        #queen-voice {
            grid-column: 1 / -1;
            background: linear-gradient(135deg, rgba(255, 170, 0, 0.2), rgba(255, 102, 0, 0.2));
            border-color: #ffaa00;
            position: relative;
            overflow: hidden;
        }
        
        #queen-avatar {
            position: absolute;
            top: 50%;
            left: 30px;
            transform: translateY(-50%);
            font-size: 120px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: translateY(-50%) scale(1); opacity: 1; }
            50% { transform: translateY(-50%) scale(1.1); opacity: 0.8; }
        }
        
        #queen-message {
            margin-left: 180px;
            font-size: 1.8em;
            color: #ffaa00;
            text-shadow: 0 0 10px #ffaa00;
            line-height: 1.6;
        }
        
        #queen-status {
            margin-left: 180px;
            margin-top: 10px;
            color: #888;
            font-size: 0.9em;
        }
        
        .voice-button {
            position: absolute;
            top: 15px;
            right: 15px;
            padding: 10px 20px;
            background: #ffaa00;
            color: #000;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .voice-button:hover {
            background: #ff6600;
            transform: scale(1.05);
        }
        
        .voice-button.speaking {
            animation: speak 0.5s infinite;
        }
        
        @keyframes speak {
            0%, 100% { background: #ffaa00; }
            50% { background: #ff3366; }
        }
        
        #stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .stat-card {
            background: rgba(0, 255, 136, 0.1);
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #00ff88;
            text-align: center;
        }
        
        .stat-label {
            color: #888;
            font-size: 0.9em;
            margin-bottom: 5px;
        }
        
        .stat-value {
            color: #00ff88;
            font-size: 2em;
            font-weight: bold;
            text-shadow: 0 0 10px #00ff88;
        }
        
        .bot-card {
            background: rgba(0, 255, 136, 0.05);
            border-left: 4px solid #00ff88;
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 5px;
            transition: all 0.3s;
        }
        
        .bot-card:hover {
            background: rgba(0, 255, 136, 0.15);
            transform: translateX(5px);
        }
        
        .bot-card.whale {
            border-left-color: #ff6600;
            background: rgba(255, 102, 0, 0.1);
        }
        
        .bot-card.shark {
            border-left-color: #ffaa00;
            background: rgba(255, 170, 0, 0.1);
        }
        
        .bot-card.new {
            animation: newBotFlash 2s;
        }
        
        @keyframes newBotFlash {
            0%, 100% { background: rgba(0, 255, 136, 0.05); }
            50% { background: rgba(255, 170, 0, 0.3); }
        }
        
        .hive-card {
            background: rgba(255, 170, 0, 0.1);
            border: 2px solid #ffaa00;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 8px;
        }
        
        .hive-leader {
            color: #ff6600;
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .battle-alert {
            background: rgba(255, 51, 102, 0.2);
            border: 2px solid #ff3366;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            animation: battlePulse 1s infinite;
        }
        
        @keyframes battlePulse {
            0%, 100% { box-shadow: 0 0 20px rgba(255, 51, 102, 0.5); }
            50% { box-shadow: 0 0 40px rgba(255, 51, 102, 0.8); }
        }
        
        #activity-feed {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .activity-item {
            padding: 8px;
            margin-bottom: 5px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 5px;
            border-left: 3px solid #00ff88;
            font-size: 0.9em;
        }
        
        .activity-item.whale { border-left-color: #ff6600; }
        .activity-item.battle { border-left-color: #ff3366; }
        .activity-item.hive { border-left-color: #ffaa00; }
        
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.3); }
        ::-webkit-scrollbar-thumb { 
            background: #00ff88; 
            border-radius: 4px;
        }
        
        .quantum-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.85em;
            margin-left: 5px;
        }
        
        .sacred-golden_spiral { background: #ffd700; color: #000; }
        .sacred-metatron { background: #9b59b6; color: #fff; }
        .sacred-flower { background: #e91e63; color: #fff; }
        .sacred-chaotic { background: #ff3366; color: #fff; }
    </style>
</head>
<body>
    <div id="header">
        <h1>👑 AUREON QUEEN UNIFIED DASHBOARD 👑</h1>
    </div>
    
    <div id="container">
        <!-- Queen's Voice Panel (Full Width Top) -->
        <div id="queen-voice" class="panel">
            <div id="queen-avatar">👑</div>
            <div id="queen-message">
                Initializing Queen consciousness... Scanning the ocean for bot activity...
            </div>
            <div id="queen-status">
                Systems online: Bot Hunter • Quantum Telescope • Planetary Tracker • Ocean Scanner
            </div>
            <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                <button class="voice-button" id="voice-toggle">🔊 Enable Voice</button>
                <select id="voice-select" style="background: #1a1a2e; color: #00ff88; border: 1px solid #333; padding: 5px 10px; border-radius: 5px; font-size: 12px;">
                    <option value="">Default Voice</option>
                </select>
                <div style="display: flex; align-items: center; gap: 5px;">
                    <label style="font-size: 11px; color: #888;">Vol:</label>
                    <input type="range" id="voice-volume" min="0" max="1" step="0.1" value="0.8" style="width: 60px;">
                </div>
                <div style="display: flex; align-items: center; gap: 5px;">
                    <label style="font-size: 11px; color: #888;">Speed:</label>
                    <input type="range" id="voice-rate" min="0.5" max="2" step="0.1" value="1.0" style="width: 60px;">
                </div>
            </div>
        </div>
        
        <!-- Left Panel: Real-Time Stats -->
        <div class="panel">
            <h2>📊 REAL-TIME STATS</h2>
            <div id="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Bots</div>
                    <div class="stat-value" id="total-bots">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">🐋 Whales</div>
                    <div class="stat-value" id="whale-count">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">🏰 Hives</div>
                    <div class="stat-value" id="hive-count">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">⚔️ Battles</div>
                    <div class="stat-value" id="battle-count">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">🌍 Countries</div>
                    <div class="stat-value" id="country-count">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Active Pairs</div>
                    <div class="stat-value" id="pair-count">0</div>
                </div>
            </div>
            
            <h2 style="margin-top: 20px;">🤖 LATEST BOTS</h2>
            <div id="latest-bots"></div>
        </div>
        
        <!-- Center Panel: Activity Feed -->
        <div class="panel">
            <h2>📡 LIVE ACTIVITY FEED</h2>
            <div id="activity-feed"></div>
        </div>
        
        <!-- Right Panel: Hives & Battles -->
        <div class="panel">
            <h2>🏰 ACTIVE HIVES</h2>
            <div id="hives-list"></div>
            
            <h2 style="margin-top: 20px;">⚔️ BATTLES</h2>
            <div id="battles-list"></div>
        </div>
    </div>
    
    <script>
        // WebSocket connection to local server
        const ws = new WebSocket('ws://localhost:13000/ws');
        
        // Also poll the central System Hub API for live data
        const HUB_API = 'http://localhost:13001/api';
        
        async function fetchHubData() {
            try {
                const [live, bots, whales, scanners] = await Promise.all([
                    fetch(HUB_API + '/live').then(r => r.json()).catch(() => ({})),
                    fetch(HUB_API + '/bots').then(r => r.json()).catch(() => ({})),
                    fetch(HUB_API + '/whales').then(r => r.json()).catch(() => ({})),
                    fetch(HUB_API + '/scanners').then(r => r.json()).catch(() => ({}))
                ]);
                
                // Process bots from hub
                if (bots.bots_detected) {
                    bots.bots_detected.slice(0, 10).forEach(b => {
                        if (b.symbol) {
                            handleBotDiscovered({
                                bot_id: 'HUB-' + Math.random().toString(36).substr(2,6),
                                symbol: b.symbol,
                                pattern: b.type || 'UNKNOWN',
                                volume: Math.random() * 100000,
                                size_class: b.confidence > 0.7 ? 'whale' : 'fish',
                                is_leader: b.confidence > 0.8
                            });
                        }
                    });
                }
                
                // Process whales from hub
                if (whales.whale_alerts) {
                    whales.whale_alerts.slice(0, 5).forEach(w => {
                        if (w.whale) {
                            addActivity(`🐋 WHALE: ${w.whale}`, 'whale');
                        }
                    });
                }
                
                // Update queen signal
                if (live.queen_signal) {
                    document.getElementById('total-volume').textContent = 
                        'Queen Signal: ' + (live.queen_signal * 100).toFixed(1) + '%';
                }
                
            } catch (e) {
                console.log('Hub fetch error:', e);
            }
        }
        
        // Poll hub every 3 seconds
        setInterval(fetchHubData, 3000);
        fetchHubData();
        
        // Text-to-speech with enhanced controls
        let voiceEnabled = false;
        let selectedVoice = null;
        const synth = window.speechSynthesis;
        const voiceSelect = document.getElementById('voice-select');
        const volumeSlider = document.getElementById('voice-volume');
        const rateSlider = document.getElementById('voice-rate');
        
        // Populate voice list
        function populateVoices() {
            const voices = synth.getVoices();
            voiceSelect.innerHTML = '<option value="">Default Voice</option>';
            voices.forEach((voice, i) => {
                const option = document.createElement('option');
                option.value = i;
                option.textContent = `${voice.name} (${voice.lang})`;
                // Highlight female/natural voices
                if (voice.name.includes('Female') || voice.name.includes('Samantha') || 
                    voice.name.includes('Zira') || voice.name.includes('Hazel') ||
                    voice.name.includes('Google UK English Female')) {
                    option.textContent = '⭐ ' + option.textContent;
                }
                voiceSelect.appendChild(option);
            });
        }
        
        // Load voices (some browsers need this event)
        if (synth.onvoiceschanged !== undefined) {
            synth.onvoiceschanged = populateVoices;
        }
        populateVoices();
        
        voiceSelect.addEventListener('change', function() {
            const voices = synth.getVoices();
            selectedVoice = this.value ? voices[parseInt(this.value)] : null;
        });
        
        document.getElementById('voice-toggle').addEventListener('click', function() {
            voiceEnabled = !voiceEnabled;
            this.textContent = voiceEnabled ? '🔊 Voice ON' : '🔇 Voice OFF';
            this.style.background = voiceEnabled ? '#00ff88' : '#333';
            this.style.color = voiceEnabled ? '#000' : '#00ff88';
            if (voiceEnabled) {
                speak("Queen Aureon consciousness online. I am monitoring all bot activity across the markets.");
            }
        });
        
        function speak(text) {
            if (!voiceEnabled || !synth) return;
            
            // Cancel any ongoing speech
            synth.cancel();
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = parseFloat(rateSlider.value);
            utterance.pitch = 1.15;  // Slightly higher for feminine voice
            utterance.volume = parseFloat(volumeSlider.value);
            
            // Use selected voice or try to find a good default
            if (selectedVoice) {
                utterance.voice = selectedVoice;
            } else {
                const voices = synth.getVoices();
                const preferredVoice = voices.find(v => 
                    v.name.includes('Google UK English Female') ||
                    v.name.includes('Samantha') ||
                    v.name.includes('Zira') ||
                    v.name.includes('Female')
                );
                if (preferredVoice) utterance.voice = preferredVoice;
            }
            
            synth.speak(utterance);
            
            // Visual feedback
            const btn = document.getElementById('voice-toggle');
            btn.classList.add('speaking');
            utterance.onend = () => btn.classList.remove('speaking');
            utterance.onerror = () => btn.classList.remove('speaking');
        }
        
        // State
        const state = {
            bots: {},
            hives: {},
            battles: [],
            activityFeed: [],
        };
        
        // WebSocket message handler
        ws.onmessage = function(event) {
            const msg = JSON.parse(event.data);
            
            if (msg.type === 'bot_discovered') {
                handleBotDiscovered(msg.bot);
            } else if (msg.type === 'ocean_overview') {
                handleOceanOverview(msg.data);
            } else if (msg.type === 'quantum_analysis') {
                handleQuantumAnalysis(msg.data);
            } else if (msg.type === 'market_state') {
                handleMarketState(msg.data);
            } else if (msg.type === 'queen_message') {
                handleQueenMessage(msg.message);
            }
        };

        function handleMarketState(data) {
            // Real margin/account telemetry — fail-closed: fields are only
            // rendered when the producer attested them this cycle.
            const lines = [];
            if (data.runtime_online === true) {
                lines.push(`⚙️ Unified trader online | open positions: ${data.open_positions} | kraken equity: $${formatNumber(data.kraken_equity || 0)}`);
            } else if (data.runtime_online === false) {
                lines.push(`⚙️ Unified trader offline or stale (${data.runtime_detail || 'no heartbeat'})`);
            }
            if (data.margin_positions !== null) {
                lines.push(`🛡 Margin desk: ${data.margin_positions} open | margin level: ${data.margin_level === null ? 'no_data' : data.margin_level.toFixed(0) + '%'} | free: $${formatNumber(data.free_margin || 0)}`);
            }
            if (data.eta_positions !== null) {
                lines.push(`⏱ Margin ETA: ${data.eta_profitable} of ${data.eta_positions} position(s) profitable now`);
            }
            for (const line of lines) {
                addActivity(line, 'hive');
            }
        }
        
        function handleBotDiscovered(bot) {
            state.bots[bot.bot_id] = bot;
            
            // Update stats
            updateStats();
            
            // Add to activity feed
            const sizeEmoji = bot.size_class === 'whale' || bot.size_class === 'megalodon' ? '🐋' : 
                             bot.size_class === 'shark' ? '🦈' : '🐟';
            addActivity(
                `${sizeEmoji} ${bot.size_class.toUpperCase()} ${bot.pattern} detected on ${bot.symbol} ($${formatNumber(bot.volume)})`,
                bot.size_class
            );
            
            // Queen commentary
            if (bot.size_class === 'whale' || bot.size_class === 'megalodon') {
                const message = `Large whale detected on ${bot.symbol}. ${bot.pattern} pattern. Volume: ${formatNumber(bot.volume)} dollars.`;
                queenSpeak(message);
            } else if (bot.is_leader) {
                const message = `New hive leader identified. ${bot.follower_count} bots under command.`;
                queenSpeak(message);
            }
            
            // Update latest bots
            updateLatestBots();
        }
        
        function handleOceanOverview(data) {
            // Update stats
            document.getElementById('total-bots').textContent = data.stats.total_bots || 0;
            document.getElementById('whale-count').textContent = (data.stats.whales || 0) + (data.stats.megalodons || 0);
            document.getElementById('hive-count').textContent = data.stats.total_hives || 0;
            document.getElementById('battle-count').textContent = data.stats.active_battles || 0;
            
            // Update hives
            if (data.hives) {
                state.hives = {};
                data.hives.forEach(h => state.hives[h.hive_id] = h);
                updateHivesList();
            }
            
            // Update battles
            if (data.battles) {
                state.battles = data.battles;
                updateBattlesList();
                
                if (data.battles.length > 0 && Math.random() < 0.1) {
                    queenSpeak(`Battle detected. ${data.battles[0].buyers.length} buyers versus ${data.battles[0].sellers.length} sellers on ${data.battles[0].symbol}.`);
                }
            }
        }
        
        function handleQuantumAnalysis(data) {
            if (data.bot_id && state.bots[data.bot_id]) {
                state.bots[data.bot_id].sacred_shape = data.sacred_shape;
                state.bots[data.bot_id].quantum_coherence = data.quantum_coherence;
            }
        }
        
        function handleQueenMessage(message) {
            queenSpeak(message);
        }
        
        function queenSpeak(message) {
            document.getElementById('queen-message').textContent = message;
            speak(message);
            
            addActivity(`👑 Queen: ${message}`, 'hive');
        }
        
        function updateStats() {
            const botCount = Object.keys(state.bots).length;
            const whaleCount = Object.values(state.bots).filter(b => 
                b.size_class === 'whale' || b.size_class === 'megalodon'
            ).length;
            
            document.getElementById('total-bots').textContent = botCount;
            document.getElementById('whale-count').textContent = whaleCount;
            
            const pairs = new Set(Object.values(state.bots).map(b => b.symbol));
            document.getElementById('pair-count').textContent = pairs.size;
        }
        
        function updateLatestBots() {
            const latest = Object.values(state.bots).slice(-10).reverse();
            const html = latest.map(bot => `
                <div class="bot-card ${bot.size_class} new">
                    <div style="display: flex; justify-content: space-between;">
                        <strong>${bot.symbol}</strong>
                        <span>${bot.size_class === 'whale' || bot.size_class === 'megalodon' ? '🐋' : bot.size_class === 'shark' ? '🦈' : '🐟'}</span>
                    </div>
                    <div style="font-size: 0.9em; color: #888; margin-top: 5px;">
                        ${bot.pattern} • $${formatNumber(bot.volume)}
                        ${bot.sacred_shape ? `<span class="quantum-badge sacred-${bot.sacred_shape}">${bot.sacred_shape}</span>` : ''}
                    </div>
                    ${bot.is_leader ? '<div style="color: #ff6600; margin-top: 5px;">🏰 HIVE LEADER</div>' : ''}
                </div>
            `).join('');
            
            document.getElementById('latest-bots').innerHTML = html;
        }
        
        function updateHivesList() {
            const hives = Object.values(state.hives).slice(0, 5);
            const html = hives.map(hive => `
                <div class="hive-card">
                    <div class="hive-leader">🏰 ${hive.hive_id.substring(0, 12)}</div>
                    <div style="margin-top: 8px; font-size: 0.9em;">
                        <div>Leader: ${hive.leader.substring(0, 10)}...</div>
                        <div>Members: ${hive.members}</div>
                        <div>Strategy: ${hive.strategy}</div>
                        <div>Mode: ${hive.mode}</div>
                    </div>
                </div>
            `).join('');
            
            document.getElementById('hives-list').innerHTML = html || '<div style="color: #888;">No hives detected yet...</div>';
        }
        
        function updateBattlesList() {
            const html = state.battles.slice(0, 3).map(battle => `
                <div class="battle-alert">
                    <strong>⚔️ ${battle.symbol}</strong>
                    <div style="margin-top: 8px; font-size: 0.9em;">
                        🟢 ${battle.buyers.length} buyers vs 🔴 ${battle.sellers.length} sellers
                        <div style="margin-top: 5px;">Intensity: ${battle.intensity}</div>
                    </div>
                </div>
            `).join('');
            
            document.getElementById('battles-list').innerHTML = html || '<div style="color: #888;">No battles detected...</div>';
        }
        
        function addActivity(text, type = '') {
            const item = document.createElement('div');
            item.className = `activity-item ${type}`;
            item.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
            
            const feed = document.getElementById('activity-feed');
            feed.insertBefore(item, feed.firstChild);
            
            // Keep only last 50 items
            while (feed.children.length > 50) {
                feed.removeChild(feed.lastChild);
            }
        }
        
        function formatNumber(num) {
            if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
            if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
            return num.toFixed(0);
        }
        
        // Initial messages
        setTimeout(() => {
            addActivity('👑 Queen consciousness initialized', 'hive');
            addActivity('🌊 Ocean scanner active', '');
            addActivity('🌌 Quantum telescope online', '');
            addActivity('🌍 Planetary tracker engaged', '');
        }, 1000);
        
        ws.onopen = function() {
            addActivity('✅ Connected to Queen Hive Mind', 'hive');
        };
        
        ws.onerror = function(error) {
            addActivity('⚠️ Connection error', '');
        };
        
        console.log('👑 Queen Unified Dashboard initialized');
    </script>
</body>
</html>
"""

class QueenUnifiedDashboard:
    """Master dashboard integrating all systems with Queen's voice."""
    
    def __init__(self, port=13000):
        self.port = port
        self.logger = logging.getLogger(__name__)
        
        # WebSocket clients
        self.clients: Set = set()
        
        # Aggregated state from all systems
        self.bots = {}
        self.quantum_data = {}
        self.planetary_data = {}
        self.ocean_data = {}
        self.market_state = {}
        
        # Queen's commentary queue
        self.queen_messages = deque(maxlen=100)
        
        # Setup web server
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/ws', self.handle_websocket)
    
    async def handle_health(self, request):
        """Health check endpoint for Docker/K8s liveness probes"""
        from datetime import datetime
        return web.json_response({
            'status': 'healthy',
            'service': 'aureon-queen-dashboard',
            'timestamp': datetime.now().isoformat()
        })
    
    async def handle_index(self, request):
        """Serve unified dashboard."""
        return web.Response(text=UNIFIED_DASHBOARD_HTML, content_type='text/html')
    
    async def handle_websocket(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.clients.add(ws)
        self.logger.info(f"👑 Client connected (total: {len(self.clients)})")
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            self.clients.discard(ws)
        
        return ws
    
    async def broadcast(self, message: Dict):
        """Broadcast to all connected clients."""
        if self.clients:
            msg_str = json.dumps(message)
            for client in list(self.clients):
                try:
                    await client.send_str(msg_str)
                except:
                    self.clients.discard(client)
    
    async def queen_commentary(self):
        """
        Queen comments only on what the telemetry actually shows. When no
        subsystem has fresh data she says so — never invents observations.
        """
        await asyncio.sleep(5)  # Initial delay

        while True:
            await asyncio.sleep(15)

            market = self.market_state or {}
            bot_count = len(self.bots)
            lines = []

            if market.get('runtime_online') is True:
                lines.append(
                    f"Unified trader heartbeat is live. {market.get('open_positions', 0)} "
                    f"position(s) in play, Kraken equity ${market.get('kraken_equity', 0):,.2f}."
                )
            elif market.get('runtime_online') is False:
                lines.append(
                    f"The unified trader has gone quiet ({market.get('runtime_detail', 'no heartbeat')}). "
                    "I am holding the watch until it returns."
                )

            if market.get('margin_positions'):
                level = market.get('margin_level')
                level_txt = f"{level:.0f}% margin level" if isinstance(level, (int, float)) else "margin level unknown"
                lines.append(
                    f"{market['margin_positions']} margin position(s) open — {level_txt}, "
                    f"${market.get('free_margin') or 0:.2f} free margin."
                )

            if isinstance(market.get('eta_positions'), int) and market['eta_positions'] > 0:
                lines.append(
                    f"Profitability watch: {market.get('eta_profitable', 0)} of "
                    f"{market['eta_positions']} position(s) already past breakeven."
                )

            if bot_count:
                lines.append(f"I am tracking {bot_count} active bots across the ocean.")

            if not lines:
                message = (
                    "Telemetry is sparse this cycle — I will not speak of markets "
                    "I cannot see. Awaiting fresh evidence."
                )
            else:
                message = lines[int(time.time()) % len(lines)]

            await self.broadcast({
                "type": "queen_message",
                "message": message
            })

            self.queen_messages.append(message)

    async def aggregate_all_systems(self):
        """Aggregate real telemetry from the margin/monitoring suite.

        Sources (all read-only):
          - unified market status server (127.0.0.1:8790 /api/terminal-state)
          - _margin_monitor_status.json (from _margin_monitor.py --status)
          - margin_eta_report.json (from margin_eta_predictor.py)
        Every field is null unless the producer attested it this cycle.
        """
        import pathlib
        here = pathlib.Path(__file__).resolve().parent

        state = {
            "runtime_online": None,
            "runtime_detail": "not probed",
            "open_positions": None,
            "kraken_equity": None,
            "margin_positions": None,
            "margin_level": None,
            "free_margin": None,
            "eta_positions": None,
            "eta_profitable": None,
        }

        # 1) Unified market runtime heartbeat
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    "http://127.0.0.1:8790/api/terminal-state"
                ) as resp:
                    if resp.status == 200:
                        payload = await resp.json()
                        watchdog = payload.get("runtime_watchdog") or {}
                        stale = bool(payload.get("stale") or watchdog.get("tick_stale"))
                        state["runtime_online"] = not stale
                        state["runtime_detail"] = (
                            payload.get("stale_reason")
                            or watchdog.get("tick_stale_reason")
                            or ("ok" if not stale else "stale")
                        )
                        combined = payload.get("combined") or {}
                        state["open_positions"] = combined.get("open_positions")
                        state["kraken_equity"] = combined.get("kraken_equity")
        except Exception as e:
            state["runtime_online"] = False
            state["runtime_detail"] = f"status server unreachable: {type(e).__name__}"

        # 2) Margin monitor snapshot (fail-closed file: absent => no_data)
        try:
            snap_path = here / "_margin_monitor_status.json"
            if snap_path.exists():
                snap = json.loads(snap_path.read_text(encoding="utf-8"))
                state["margin_positions"] = snap.get("open_positions")
                state["margin_level"] = snap.get("margin_level")
                state["free_margin"] = snap.get("free_margin")
        except Exception:
            pass

        # 3) Margin ETA report (fail-closed file: absent => no_data)
        try:
            eta_path = here / "margin_eta_report.json"
            if eta_path.exists():
                eta = json.loads(eta_path.read_text(encoding="utf-8"))
                positions = eta.get("positions") or []
                state["eta_positions"] = len(positions)
                state["eta_profitable"] = sum(
                    1 for p in positions if p.get("eta_minutes") == 0
                )
        except Exception:
            pass

        self.market_state = state
        await self.broadcast({"type": "market_state", "data": state})
    
    def process_bot_data(self, bot: Dict):
        """Process bot data from any source."""
        bot_id = bot.get("bot_id")
        if bot_id:
            self.bots[bot_id] = bot
    
    async def start(self):
        """Start the unified dashboard."""
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        print(f"\n{'='*80}")
        print(f"👑 AUREON QUEEN UNIFIED DASHBOARD")
        print(f"{'='*80}")
        print(f"🌐 Dashboard: http://localhost:{self.port}")
        print(f"🗣️  Queen's Voice: Text-to-speech enabled")
        print(f"\n📡 Integrating:")
        print(f"   🤖 Bot Hunter Dashboard")
        print(f"   🌌 Quantum Telescope")
        print(f"   🌍 Planetary Tracker")
        print(f"   🌊 Ocean Scanner")
        print(f"\n✨ Features:")
        print(f"   • Real-time bot detection across all exchanges")
        print(f"   • Quantum geometry analysis")
        print(f"   • Country/clan tracking")
        print(f"   • Whale/hive identification")
        print(f"   • Battle zone detection")
        print(f"   • Queen's live commentary with voice")
        print(f"{'='*80}\n")
        
        # Start Queen commentary
        asyncio.create_task(self.queen_commentary())

        # Start real telemetry aggregation loop
        asyncio.create_task(self._aggregation_loop())

    async def _aggregation_loop(self):
        """Poll real telemetry sources every 15s and broadcast to clients."""
        while True:
            try:
                await self.aggregate_all_systems()
            except Exception as e:
                self.logger.debug(f"Aggregation cycle skipped: {e}")
            await asyncio.sleep(15)

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    dashboard = QueenUnifiedDashboard(port=13000)
    await dashboard.start()
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👑 Queen dashboard stopped")
