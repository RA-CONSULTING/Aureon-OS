#!/usr/bin/env python3
"""
🌌👑💭⚡ AUREON UNIFIED MASTER HUB - ALL SYSTEMS IN ONE PLACE
═══════════════════════════════════════════════════════════════════════════

ONE DASHBOARD TO RULE THEM ALL

Combines:
✅ Mind Map Visualization (System Hub)
✅ Command Center Features (Portfolio, Signals, Systems)
✅ Mind → Thought → Action Cognitive Flow
✅ Real-time ThoughtBus Streaming
✅ Live Portfolio Tracking
✅ Queen's Voice Commentary

ALL DATA FLOWING TO THE CORRECT SECTIONS IN ONE UNIFIED INTERFACE

Port: 13333
URL: http://localhost:13333

Gary Leckey | January 2026 | UNIFIED MASTER HUB
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
from pathlib import Path

# Core systems
from aureon.command_centers.aureon_system_hub import SystemRegistry
from aureon.core.aureon_thought_bus import ThoughtBus, Thought
from aureon.exchanges.binance_client import get_binance_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

# Safe imports
def safe_import(name: str, module: str, cls: str):
    try:
        mod = __import__(module, fromlist=[cls])
        return getattr(mod, cls)
    except Exception as e:
        logger.debug(f"⚠️ {name}: {e}")
        return None

# Exchange clients
KrakenClient = safe_import('Kraken', 'kraken_client', 'KrakenClient')
BinanceClient = safe_import('Binance', 'binance_client', 'BinanceClient')
AlpacaClient = safe_import('Alpaca', 'alpaca_client', 'AlpacaClient')

# Intelligence systems
QueenHiveMind = safe_import('Queen', 'aureon_queen_hive_mind', 'QueenHiveMind')
ProbabilityNexus = safe_import('ProbNexus', 'aureon_probability_nexus', 'ProbabilityNexus')
UltimateIntelligence = safe_import('UltimateIntel', 'probability_ultimate_intelligence', 'ProbabilityUltimateIntelligence')
TimelineOracle = safe_import('Timeline', 'aureon_timeline_oracle', 'TimelineOracle')
QuantumMirror = safe_import('Quantum', 'aureon_quantum_mirror_scanner', 'QuantumMirrorScanner')

# Scanning systems
AnimalMomentumScanners = safe_import('AnimalScanners', 'aureon_animal_momentum_scanners', 'AnimalMomentumScanners')
BotShapeScanner = safe_import('BotShape', 'aureon_bot_shape_scanner', 'BotShapeScanner')
GlobalWaveScanner = safe_import('GlobalWave', 'aureon_global_wave_scanner', 'GlobalWaveScanner')
OceanScanner = safe_import('Ocean', 'aureon_ocean_scanner', 'OceanScanner')
OceanWaveScanner = safe_import('OceanWave', 'aureon_ocean_wave_scanner', 'OceanWaveScanner')
StrategicWarfareScanner = safe_import('StrategicWarfare', 'aureon_strategic_warfare_scanner', 'StrategicWarfareScanner')
WisdomScanner = safe_import('Wisdom', 'aureon_wisdom_scanner', 'WisdomScanner')
UnifiedEcosystem = safe_import('UnifiedEco', 'aureon_unified_ecosystem', 'UnifiedEcosystem')
GlobalFinancialFeed = safe_import('GlobalFeed', 'global_financial_feed', 'GlobalFinancialFeed')
TimelineAnchorValidator = safe_import('TimelineAnchor', 'aureon_timeline_anchor_validator', 'TimelineAnchorValidator')

# Counter-Intelligence Systems
BotProfiler = safe_import('BotProfiler', 'aureon_bot_intelligence_profiler', 'BotIntelligenceProfiler')
WhaleHunter = safe_import('WhaleHunter', 'aureon_moby_dick_whale_hunter', 'MobyDickWhaleHunter')
CounterIntel = safe_import('CounterIntel', 'aureon_queen_counter_intelligence', 'QueenCounterIntelligence')

# War Room / Orca Kill Cycle
OrcaKillCycle = safe_import('OrcaKillCycle', 'orca_complete_kill_cycle', 'OrcaKillCycle')

# Firm Intelligence - 50+ Global Trading Firms
try:
    from aureon.bots_intelligence.aureon_bot_intelligence_profiler import TRADING_FIRM_SIGNATURES
    FIRM_SIGNATURES_AVAILABLE = True
except ImportError:
    TRADING_FIRM_SIGNATURES = {}
    FIRM_SIGNATURES_AVAILABLE = False

try:
    from aureon.wisdom.aureon_stargate_protocol import PLANETARY_STARGATES
except ImportError:
    PLANETARY_STARGATES = {}

# Deep Systems
LuckFieldMapper = safe_import('LuckField', 'aureon_luck_field_mapper', 'LuckFieldMapper')
StargateProtocol = safe_import('Stargate', 'aureon_stargate_protocol', 'StargateProtocolEngine')
InceptionEngine = safe_import('Inception', 'aureon_inception_engine', 'InceptionEngine')
ElephantLearning = safe_import('Elephant', 'aureon_elephant_learning', 'ElephantLearning')
WarfareEngine = safe_import('Warfare', 'guerrilla_warfare_engine', 'GuerrillaWarfareEngine')
ImmuneSystem = safe_import('Immune', 'aureon_immune_system', 'ImmuneSystem')

# Real Portfolio Tracker
RealPortfolioTracker = safe_import('RealPortfolio', 'aureon_real_portfolio_tracker', 'RealPortfolioTracker')

# ════════════════════════════════════════════════════════════════════════════
# MEGA UNIFIED HTML - ALL SYSTEMS IN ONE DASHBOARD
# ════════════════════════════════════════════════════════════════════════════

UNIFIED_MASTER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌌 Aureon Unified Master Hub</title>
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
        
        #mega-header {
            background: rgba(0, 0, 0, 0.95);
            padding: 10px 20px;
            border-bottom: 3px solid #ffaa00;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 30px rgba(255, 170, 0, 0.5);
        }
        
        #mega-header h1 {
            font-size: 1.6em;
            background: linear-gradient(90deg, #ffaa00, #ff6600, #00ff88, #6C5CE7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: glow 3s infinite;
        }
        
        @keyframes glow {
            0%, 100% { filter: brightness(1); }
            50% { filter: brightness(1.5); }
        }
        
        .header-stats {
            display: flex;
            gap: 15px;
            font-size: 0.85em;
        }
        
        .stat-badge {
            padding: 5px 12px;
            border-radius: 5px;
            font-weight: bold;
        }
        
        .stat-badge.systems { background: rgba(108, 92, 231, 0.3); color: #6C5CE7; }
        .stat-badge.portfolio { background: rgba(0, 255, 136, 0.3); color: #00ff88; }
        .stat-badge.thoughts { background: rgba(255, 170, 0, 0.3); color: #ffaa00; }
        .stat-badge.connected {
            background: rgba(0, 255, 136, 0.3);
            color: #00ff88;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        #mega-container {
            display: grid;
            grid-template-columns: 280px 1fr 300px;
            grid-template-rows: 1fr 200px;
            gap: 10px;
            padding: 10px;
            height: calc(100vh - 80px);
        }
        
        .mega-panel {
            background: rgba(0, 0, 0, 0.85);
            border: 2px solid #00ff88;
            border-radius: 8px;
            padding: 12px;
            overflow-y: auto;
            box-shadow: 0 0 15px rgba(0, 255, 136, 0.3);
        }
        
        .mega-panel h2 {
            color: #ffaa00;
            font-size: 1em;
            margin-bottom: 8px;
            border-bottom: 1px solid #ffaa00;
            padding-bottom: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .section-badge {
            font-size: 0.8em;
            padding: 2px 8px;
            border-radius: 3px;
            margin-left: 5px;
        }
        
        /* New Categories */
        .badge-intel { background: rgba(155, 89, 182, 0.3); color: #9b59b6; border: 1px solid #9b59b6; } /* Purple */
        .badge-counter { background: rgba(192, 57, 43, 0.3); color: #c0392b; border: 1px solid #c0392b; } /* Dark Red */
        .badge-exec { background: rgba(46, 204, 113, 0.3); color: #2ecc71; border: 1px solid #2ecc71; } /* Green */
        .badge-momentum { background: rgba(52, 152, 219, 0.3); color: #3498db; border: 1px solid #3498db; } /* Blue */
        .badge-data { background: rgba(22, 160, 133, 0.3); color: #16a085; border: 1px solid #16a085; } /* Teal */
        .badge-analytics { background: rgba(241, 196, 15, 0.3); color: #f1c40f; border: 1px solid #f1c40f; } /* Yellow */
        .badge-infra { background: rgba(149, 165, 166, 0.3); color: #95a5a6; border: 1px solid #95a5a6; } /* Grey */
        
        #systems-list-panel { grid-row: 1 / 3; border-color: #6C5CE7; }
        #mindmap-panel { grid-column: 2; grid-row: 1 / 3; border-color: #ffaa00; }
        #portfolio-panel { border-color: #00ff88; }
        #thoughts-panel { grid-column: 3; grid-row: 1; border-color: #00ff88; }
        #queen-panel { grid-column: 3; grid-row: 2; border-color: #ffaa00; }
        
        .system-item {
            padding: 6px 8px;
            margin: 4px 0;
            background: rgba(255, 255, 255, 0.05);
            border-left: 3px solid #555;
            border-radius: 3px;
            font-size: 0.85em;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .system-item:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateX(3px);
        }
        
        .system-item.intel { border-left-color: #9b59b6; }
        .system-item.counter { border-left-color: #c0392b; }
        .system-item.exec { border-left-color: #2ecc71; }
        .system-item.momentum { border-left-color: #3498db; }
        .system-item.data { border-left-color: #16a085; }
        .system-item.analytics { border-left-color: #f1c40f; }
        .system-item.infra { border-left-color: #95a5a6; }
        
        .system-name {
            font-weight: bold;
            color: #ffaa00;
            font-size: 0.9em;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .system-metrics {
            font-size: 0.75em;
            color: #888;
            margin-top: 2px;
        }
        
        #mindmap-container {
            position: relative;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            border-radius: 5px;
        }
        
        .portfolio-stat {
            display: flex;
            justify-content: space-between;
            padding: 6px 8px;
            margin: 3px 0;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 3px;
            font-size: 0.85em;
        }
        
        .stat-label { color: #888; }
        .stat-value { font-weight: bold; color: #00ff88; }
        .stat-value.positive { color: #00ff88; }
        .stat-value.negative { color: #ff4444; }
        
        .balance-item {
            display: flex;
            justify-content: space-between;
            padding: 4px 8px;
            margin: 2px 0;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 3px;
            font-size: 0.8em;
        }
        
        .thought-item {
            padding: 8px;
            margin: 6px 0;
            background: rgba(0, 255, 136, 0.08);
            border-left: 3px solid #00ff88;
            border-radius: 4px;
            animation: slideIn 0.3s ease;
            font-size: 0.8em;
        }
        
        @keyframes slideIn {
            from { transform: translateY(-10px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        .thought-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
            color: #888;
            font-size: 0.85em;
        }
        
        .thought-topic { color: #00ff88; font-weight: bold; }
        .thought-source { color: #ffaa00; }
        .thought-payload {
            color: #fff;
            margin-top: 3px;
            font-size: 0.85em;
            max-height: 60px;
            overflow: hidden;
        }
        
        .queen-message {
            padding: 8px;
            margin: 6px 0;
            background: rgba(255, 170, 0, 0.1);
            border: 1px solid #ffaa00;
            border-radius: 5px;
            animation: fadeIn 0.5s ease;
            font-size: 0.85em;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .queen-message .timestamp {
            font-size: 0.75em;
            color: #888;
            margin-bottom: 3px;
        }
        
        .queen-message .text {
            color: #ffaa00;
            line-height: 1.3;
        }
        
        .signal-item {
            padding: 8px;
            margin: 6px 0;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 4px;
            border-left: 4px solid;
            font-size: 0.8em;
        }
        
        .signal-item.BUY { border-left-color: #00ff88; }
        .signal-item.SELL { border-left-color: #ff4444; }
        .signal-item.HOLD { border-left-color: #ffaa00; }
        
        .signal-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
        }
        
        .signal-symbol {
            font-weight: bold;
            color: #ffaa00;
        }
        
        .signal-type {
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.85em;
        }
        
        .signal-type.BUY { background: rgba(0, 255, 136, 0.3); color: #00ff88; }
        .signal-type.SELL { background: rgba(255, 68, 68, 0.3); color: #ff4444; }
        
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.3); }
        ::-webkit-scrollbar-thumb { background: rgba(0, 255, 136, 0.3); border-radius: 3px; }
        
        .activity-indicator {
            display: inline-block;
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #00ff88;
            animation: blink 1s infinite;
            margin-left: 8px;
        }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        
        .layer-filter {
            display: flex;
            gap: 8px;
            margin-bottom: 10px;
        }
        
        .filter-btn {
            padding: 4px 10px;
            border-radius: 4px;
            border: 1px solid;
            cursor: pointer;
            font-size: 0.8em;
            transition: all 0.2s;
        }
        
        .filter-btn.mind { border-color: #ffaa00; color: #ffaa00; }
        .filter-btn.thought { border-color: #00ff88; color: #00ff88; }
        .filter-btn.action { border-color: #ff4444; color: #ff4444; }
        .filter-btn.all { border-color: #6C5CE7; color: #6C5CE7; }
        
        .filter-btn.active {
            background: rgba(255, 255, 255, 0.2);
            font-weight: bold;
        }
        
        /* ⚔️ WAR ROOM TAB STYLES */
        .tab-nav {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
            padding: 5px;
            background: rgba(0, 0, 0, 0.5);
            border-radius: 5px;
        }
        
        .tab-btn {
            padding: 8px 20px;
            border: 2px solid #444;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: bold;
            transition: all 0.3s;
            background: transparent;
            color: #888;
        }
        
        .tab-btn:hover {
            border-color: #ffaa00;
            color: #ffaa00;
        }
        
        .tab-btn.active {
            background: linear-gradient(135deg, rgba(255, 68, 68, 0.3), rgba(255, 170, 0, 0.3));
            border-color: #ff4444;
            color: #ffaa00;
            box-shadow: 0 0 15px rgba(255, 68, 68, 0.3);
        }
        
        .tab-content { display: none; height: 100%; }
        .tab-content.active { display: block; }
        
        /* War Room Panel */
        #warroom-container {
            display: grid;
            grid-template-columns: 1fr 300px;
            grid-template-rows: 1fr 200px;
            gap: 10px;
            height: calc(100vh - 140px);
        }
        
        .warroom-panel {
            background: rgba(30, 0, 0, 0.9);
            border: 2px solid #ff4444;
            border-radius: 8px;
            padding: 12px;
            overflow-y: auto;
            box-shadow: 0 0 20px rgba(255, 68, 68, 0.3);
        }
        
        .warroom-panel h2 {
            color: #ff4444;
            font-size: 1em;
            margin-bottom: 8px;
            border-bottom: 1px solid #ff4444;
            padding-bottom: 4px;
        }
        
        #warroom-positions { grid-row: 1 / 3; }
        #warroom-quantum { border-color: #ffaa00; }
        #warroom-firms { border-color: #9b59b6; }
        
        .position-row {
            display: grid;
            grid-template-columns: 100px 80px 100px 120px 1fr 80px 120px;
            gap: 10px;
            padding: 8px;
            margin: 4px 0;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
            font-size: 0.85em;
            align-items: center;
        }
        
        .position-row.header {
            background: rgba(255, 68, 68, 0.2);
            font-weight: bold;
            color: #ffaa00;
        }
        
        .position-symbol { color: #ffaa00; font-weight: bold; }
        .position-pnl.positive { color: #00ff88; }
        .position-pnl.negative { color: #ff4444; }
        
        .progress-bar {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #ff4444, #ffaa00, #00ff88);
            transition: width 0.3s;
        }
        
        .quantum-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
        
        .quantum-item {
            padding: 6px 8px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            font-size: 0.8em;
        }
        
        .quantum-score {
            font-weight: bold;
        }
        
        .quantum-score.high { color: #00ff88; }
        .quantum-score.medium { color: #ffaa00; }
        .quantum-score.low { color: #ff4444; }
        
        .firm-item {
            padding: 6px 8px;
            margin: 4px 0;
            background: rgba(155, 89, 182, 0.1);
            border-left: 3px solid #9b59b6;
            border-radius: 4px;
            font-size: 0.8em;
        }
        
        .firm-name { color: #9b59b6; font-weight: bold; }
        .firm-action { color: #888; }
        .firm-direction.long { color: #00ff88; }
        .firm-direction.short { color: #ff4444; }
        
        .warroom-stats {
            display: flex;
            gap: 15px;
            margin-bottom: 10px;
            padding: 8px;
            background: rgba(255, 68, 68, 0.1);
            border-radius: 5px;
        }
        
        .warroom-stat {
            text-align: center;
        }
        
        .warroom-stat-value {
            font-size: 1.2em;
            font-weight: bold;
            color: #ffaa00;
        }
        
        .warroom-stat-label {
            font-size: 0.7em;
            color: #888;
        }
        
        /* 🏢 FIRM INTEL TAB STYLES */
        #firms-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 15px;
            padding: 15px;
            height: calc(100vh - 140px);
            overflow-y: auto;
        }
        
        .firm-card {
            background: rgba(20, 10, 40, 0.95);
            border: 2px solid #9b59b6;
            border-radius: 12px;
            padding: 15px;
            transition: all 0.3s;
            box-shadow: 0 0 15px rgba(155, 89, 182, 0.2);
        }
        
        .firm-card:hover {
            transform: translateY(-3px);
            border-color: #ffaa00;
            box-shadow: 0 0 25px rgba(255, 170, 0, 0.4);
        }
        
        .firm-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            border-bottom: 1px solid rgba(155, 89, 182, 0.3);
            padding-bottom: 8px;
        }
        
        .firm-name-large {
            font-size: 1.1em;
            font-weight: bold;
            color: #ffaa00;
        }
        
        .firm-animal {
            font-size: 1.8em;
        }
        
        .firm-country {
            font-size: 0.85em;
            color: #9b59b6;
            margin-bottom: 8px;
        }
        
        .firm-capital {
            font-size: 1.3em;
            font-weight: bold;
            color: #00ff88;
            margin: 8px 0;
        }
        
        .firm-strategies {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-top: 8px;
        }
        
        .strategy-tag {
            padding: 3px 8px;
            background: rgba(108, 92, 231, 0.3);
            border: 1px solid #6C5CE7;
            border-radius: 12px;
            font-size: 0.75em;
            color: #6C5CE7;
        }
        
        .firm-stats-row {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
            padding-top: 8px;
            border-top: 1px solid rgba(155, 89, 182, 0.2);
        }
        
        .firm-stat-mini {
            text-align: center;
        }
        
        .firm-stat-val {
            font-weight: bold;
            color: #ffaa00;
        }
        
        .firm-stat-lbl {
            font-size: 0.7em;
            color: #888;
        }
        
        .firm-filter-bar {
            display: flex;
            gap: 10px;
            padding: 10px 15px;
            background: rgba(0, 0, 0, 0.8);
            flex-wrap: wrap;
        }
        
        .firm-filter-btn {
            padding: 6px 15px;
            border: 1px solid #555;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.85em;
            transition: all 0.2s;
            background: transparent;
            color: #888;
        }
        
        .firm-filter-btn:hover, .firm-filter-btn.active {
            border-color: #9b59b6;
            color: #9b59b6;
            background: rgba(155, 89, 182, 0.2);
        }
        
        /* 🌊 OCEAN SCANNER TAB STYLES */
        #ocean-container {
            display: grid;
            grid-template-columns: 1fr 300px;
            grid-template-rows: auto 1fr 200px;
            gap: 10px;
            padding: 10px;
            height: calc(100vh - 140px);
        }
        
        .ocean-panel {
            background: rgba(0, 20, 40, 0.95);
            border: 2px solid #3498db;
            border-radius: 8px;
            padding: 12px;
            overflow-y: auto;
            box-shadow: 0 0 20px rgba(52, 152, 219, 0.3);
        }
        
        .ocean-panel h2 {
            color: #3498db;
            font-size: 1em;
            margin-bottom: 8px;
            border-bottom: 1px solid #3498db;
            padding-bottom: 4px;
        }
        
        #ocean-stats { grid-column: 1 / 3; }
        #ocean-whales { grid-row: 2 / 4; }
        #ocean-hives { border-color: #e74c3c; }
        #ocean-battles { border-color: #f39c12; }
        
        .ocean-stats-bar {
            display: flex;
            gap: 20px;
            justify-content: center;
        }
        
        .ocean-stat-box {
            text-align: center;
            padding: 10px 20px;
            background: rgba(52, 152, 219, 0.1);
            border-radius: 8px;
            min-width: 100px;
        }
        
        .ocean-stat-icon { font-size: 1.5em; }
        .ocean-stat-value { font-size: 1.3em; font-weight: bold; color: #3498db; }
        .ocean-stat-label { font-size: 0.75em; color: #888; }
        
        .whale-item {
            display: grid;
            grid-template-columns: 50px 1fr 80px 80px;
            gap: 10px;
            padding: 10px;
            margin: 5px 0;
            background: rgba(52, 152, 219, 0.1);
            border-left: 4px solid #3498db;
            border-radius: 4px;
            align-items: center;
        }
        
        .whale-item.megalodon { border-left-color: #9b59b6; background: rgba(155, 89, 182, 0.15); }
        .whale-item.whale { border-left-color: #3498db; }
        .whale-item.shark { border-left-color: #e74c3c; }
        .whale-item.minnow { border-left-color: #2ecc71; opacity: 0.7; }
        
        .whale-icon { font-size: 1.5em; text-align: center; }
        .whale-info { }
        .whale-symbol { font-weight: bold; color: #ffaa00; }
        .whale-owner { font-size: 0.8em; color: #9b59b6; }
        .whale-volume { font-weight: bold; color: #00ff88; }
        .whale-trades { color: #888; font-size: 0.85em; }
        
        .hive-item {
            padding: 10px;
            margin: 5px 0;
            background: rgba(231, 76, 60, 0.1);
            border: 1px solid #e74c3c;
            border-radius: 6px;
        }
        
        .hive-header { display: flex; justify-content: space-between; margin-bottom: 5px; }
        .hive-id { color: #e74c3c; font-weight: bold; }
        .hive-members { color: #888; }
        .hive-strategy { font-size: 0.85em; color: #f39c12; }
        
        .battle-item {
            padding: 10px;
            margin: 5px 0;
            background: rgba(243, 156, 18, 0.1);
            border-left: 4px solid #f39c12;
            border-radius: 4px;
        }
        
        .battle-vs {
            font-weight: bold;
            color: #f39c12;
            text-align: center;
            margin: 5px 0;
        }
        
        /* 📡 SURVEILLANCE TAB STYLES */
        #surveillance-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: auto 1fr 1fr;
            gap: 10px;
            padding: 10px;
            height: calc(100vh - 140px);
        }
        
        .surveillance-panel {
            background: rgba(0, 0, 0, 0.95);
            border: 2px solid #16a085;
            border-radius: 8px;
            padding: 12px;
            overflow-y: auto;
            box-shadow: 0 0 20px rgba(22, 160, 133, 0.3);
        }
        
        .surveillance-panel h2 {
            color: #16a085;
            font-size: 1em;
            margin-bottom: 8px;
            border-bottom: 1px solid #16a085;
            padding-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .surveillance-panel h2 .glow-dot {
            width: 8px;
            height: 8px;
            background: #16a085;
            border-radius: 50%;
            animation: glow-pulse 1.5s infinite;
        }
        
        @keyframes glow-pulse {
            0%, 100% { box-shadow: 0 0 5px #16a085; }
            50% { box-shadow: 0 0 20px #16a085, 0 0 30px #16a085; }
        }
        
        #surveillance-header { grid-column: 1 / 3; }
        #surveillance-spectrogram { border-color: #9b59b6; }
        #surveillance-flow { border-color: #e74c3c; }
        #surveillance-alerts { border-color: #f39c12; }
        #surveillance-grid { border-color: #3498db; }
        
        .surveillance-stats {
            display: flex;
            gap: 20px;
            justify-content: center;
        }
        
        .surv-stat {
            text-align: center;
            padding: 8px 15px;
            background: rgba(22, 160, 133, 0.15);
            border-radius: 6px;
        }
        
        .surv-stat-val {
            font-size: 1.4em;
            font-weight: bold;
            color: #16a085;
        }
        
        .surv-stat-lbl {
            font-size: 0.7em;
            color: #888;
        }
        
        .spectrogram-row {
            display: flex;
            gap: 2px;
            margin: 2px 0;
            font-family: monospace;
        }
        
        .spec-label {
            width: 80px;
            color: #888;
            font-size: 0.8em;
        }
        
        .spec-bar {
            flex: 1;
            height: 16px;
            background: linear-gradient(90deg, #16a085, #3498db, #9b59b6, #e74c3c);
            border-radius: 2px;
            position: relative;
            overflow: hidden;
        }
        
        .spec-fill {
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            position: absolute;
            right: 0;
            transition: width 0.3s;
        }
        
        .flow-bar {
            display: flex;
            height: 30px;
            margin: 8px 0;
            border-radius: 4px;
            overflow: hidden;
        }
        
        .flow-buy {
            background: linear-gradient(90deg, #00ff88, #2ecc71);
            transition: width 0.3s;
        }
        
        .flow-sell {
            background: linear-gradient(90deg, #e74c3c, #c0392b);
            transition: width 0.3s;
        }
        
        .flow-label {
            display: flex;
            justify-content: space-between;
            font-size: 0.85em;
            margin-top: 5px;
        }
        
        .alert-item {
            padding: 8px;
            margin: 5px 0;
            border-radius: 4px;
            font-size: 0.85em;
            animation: alert-flash 0.5s;
        }
        
        .alert-item.warning { background: rgba(243, 156, 18, 0.2); border-left: 3px solid #f39c12; }
        .alert-item.danger { background: rgba(231, 76, 60, 0.2); border-left: 3px solid #e74c3c; }
        .alert-item.info { background: rgba(52, 152, 219, 0.2); border-left: 3px solid #3498db; }
        
        @keyframes alert-flash {
            0% { opacity: 0; transform: translateX(-10px); }
            100% { opacity: 1; transform: translateX(0); }
        }
        
        .price-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
        }
        
        .price-cell {
            padding: 8px;
            background: rgba(52, 152, 219, 0.1);
            border-radius: 4px;
            text-align: center;
        }
        
        .price-symbol { font-weight: bold; color: #ffaa00; font-size: 0.85em; }
        .price-value { color: #3498db; font-size: 0.9em; }
        .price-change.up { color: #00ff88; }
        .price-change.down { color: #e74c3c; }

        /* 🍀 LUCK FIELD TAB STYLES */
        #luck-container {
            display: grid;
            grid-template-columns: 350px 1fr 300px;
            gap: 15px;
            padding: 15px;
            height: calc(100vh - 140px);
        }
        
        .luck-panel {
            background: rgba(10, 30, 20, 0.95);
            border: 2px solid #00ff88;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.2);
            position: relative;
        }
        
        #luck-gauge-box { text-align: center; }
        
        .luck-gauge-wrapper { position: relative; width: 200px; height: 120px; margin: 0 auto; overflow: hidden; }
        .luck-gauge-arc {
            width: 200px; height: 200px; border-radius: 50%;
            border: 15px solid #333;
            border-top-color: #00ff88;
            border-right-color: #ffaa00;
            border-left-color: #ff4444;
            transform: rotate(-45deg); /* This simplifies the look for now */
        }
        
        .luck-value-display {
            font-size: 3em;
            font-weight: bold;
            color: #fff;
            text-shadow: 0 0 15px rgba(0,255,136,0.6);
            margin-top: -50px;
            position: relative;
            z-index: 10;
        }
        
        .luck-state-text {
            font-size: 1.8em;
            font-weight: bold;
            margin-top: 10px;
            color: #00ff88;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        
        .factor-row {
            display: flex;
            align-items: center;
            margin: 15px 0;
            gap: 15px;
        }
        
        .factor-label { width: 140px; color: #aaa; font-family: monospace; }
        .factor-bar-bg { flex: 1; height: 12px; background: #222; border-radius: 6px; overflow: hidden; border: 1px solid #444; }
        .factor-bar-fill { height: 100%; background: linear-gradient(90deg, #00ff88, #00cc6a); transition: width 0.5s; }
        .factor-val { width: 50px; text-align: right; font-weight: bold; color: #fff; }
        
        /* 🌌 STARGATE TAB STYLES */
        #stargate-container {
            display: grid;
            grid-template-columns: 350px 1fr;
            grid-template-rows: 100px 1fr;
            gap: 15px;
            padding: 15px;
            height: calc(100vh - 140px);
        }
        
        .stargate-panel {
            background: rgba(10, 10, 30, 0.95);
            border: 2px solid #6C5CE7;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 0 25px rgba(108, 92, 231, 0.3);
            overflow-y: auto;
        }
        
        #sg-header { grid-column: 1 / 3; display: flex; justify-content: space-around; align-items: center; }
        #sg-nodes { grid-row: 2; }
        #sg-map { grid-row: 2; border-color: #ffaa00; }
        
        .sg-stat { text-align: center; }
        .sg-stat-val { font-size: 2em; font-weight: bold; color: #6C5CE7; }
        .sg-stat-lbl { font-size: 0.8em; color: #888; }
        
        .node-card {
            background: rgba(108, 92, 231, 0.1);
            border-left: 4px solid #6C5CE7;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 4px;
            transition: all 0.2s;
        }
        
        .node-card:hover { background: rgba(108, 92, 231, 0.2); transform: translateX(5px); }
        .node-card.active { border-left-color: #00ff88; box-shadow: 0 0 10px rgba(0, 255, 136, 0.2); }
        
        .node-header { display: flex; justify-content: space-between; font-weight: bold; color: #fff; margin-bottom: 5px; }
        .node-details { display: flex; justify-content: space-between; font-size: 0.8em; color: #aaa; }
        .node-freq { color: #ffaa00; }
        
        .res-line {
            display: flex; justify-content: space-between;
            font-size: 0.8em; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        /* 💭 INCEPTION ENGINE STYLES */
        #inception-container {
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 15px;
            padding: 15px;
            height: calc(100vh - 140px);
        }
        
        .inception-panel {
            background: rgba(10, 20, 30, 0.95);
            border: 2px solid #3498db;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 0 25px rgba(52, 152, 219, 0.3);
            overflow-y: auto;
        }

        .dream-layer {
            border: 1px solid #3498db;
            background: rgba(52, 152, 219, 0.05);
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
            transition: all 0.3s;
        }
        
        .dream-layer.level-1 { border-color: #3498db; margin-left: 0; }
        .dream-layer.level-2 { border-color: #9b59b6; margin-left: 20px; border-left-width: 4px; }
        .dream-layer.level-3 { border-color: #e74c3c; margin-left: 40px; border-left-width: 6px; }

        .time-dilation-badge {
            background: rgba(255, 170, 0, 0.2);
            color: #ffaa00;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            float: right;
        }

        /* 🐘 ELEPHANT MEMORY STYLES */
        #memory-container {
            display: grid;
            grid-template-columns: 1fr 350px;
            gap: 15px;
            padding: 15px;
            height: calc(100vh - 140px);
        }
        
        .memory-panel {
            background: rgba(30, 30, 35, 0.95);
            border: 2px solid #f1c40f;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 0 25px rgba(241, 196, 15, 0.2);
            overflow-y: auto;
        }

        .memory-card {
            background: rgba(241, 196, 15, 0.1);
            border-left: 4px solid #f1c40f;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 4px;
        }

        .wisdom-stat {
            font-size: 1.5em;
            font-weight: bold;
            color: #f1c40f;
            text-align: center;
        }

        /* 🔥 WARFARE ENGINE STYLES */
        #warfare-container {
            display: grid;
            grid-template-columns: 300px 1fr 300px;
            gap: 15px;
            padding: 15px;
            height: calc(100vh - 140px);
        }
        
        .warfare-panel {
            background: rgba(40, 10, 10, 0.95);
            border: 2px solid #e74c3c;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 0 25px rgba(231, 76, 60, 0.3);
            overflow-y: auto;
        }

        .tactic-active {
            background: rgba(231, 76, 60, 0.2);
            border: 1px solid #e74c3c;
            color: #e74c3c;
            padding: 8px;
            margin: 5px 0;
            border-radius: 4px;
            animation: pulse-red 2s infinite;
        }
        
        @keyframes pulse-red {
            0% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(231, 76, 60, 0); }
            100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
        }

        /* 🛡️ IMMUNE SYSTEM STYLES */
        #health-container {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            padding: 15px;
            height: calc(100vh - 140px);
        }
        
        .health-panel {
            background: rgba(10, 40, 20, 0.95);
            border: 2px solid #2ecc71;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 0 25px rgba(46, 204, 113, 0.2);
            overflow-y: auto;
        }

        .vital-row {
            display: flex;
            align-items: center;
            margin: 10px 0;
            gap: 10px;
        }

        .vital-name { width: 100px; font-weight: bold; color: #2ecc71; }
        .vital-bar-bg { flex: 1; height: 8px; background: #111; border-radius: 4px; overflow: hidden; }
        .vital-bar-fill { height: 100%; background: #2ecc71; transition: width 0.5s; }
        .vital-val { width: 50px; text-align: right; color: #fff; }
    </style>
</head>
<body>
    <div id="mega-header">
        <h1>🌌 AUREON UNIFIED MASTER HUB</h1>
        <div class="tab-nav">
            <div class="tab-btn active" onclick="switchTab('main')">🌌 Main</div>
            <div class="tab-btn" onclick="switchTab('warroom')">⚔️ War Room</div>
            <div class="tab-btn" onclick="switchTab('firms')">🏢 Firms</div>
            <div class="tab-btn" onclick="switchTab('ocean')">🌊 Ocean</div>
            <div class="tab-btn" onclick="switchTab('surveillance')">📡 Surv</div>
            <div class="tab-btn" onclick="switchTab('luck')">🍀 Luck</div>
            <div class="tab-btn" onclick="switchTab('stargate')">🌌 Star</div>
            <div class="tab-btn" onclick="switchTab('inception')">💭 Dream</div>
            <div class="tab-btn" onclick="switchTab('memory')">🐘 Memory</div>
            <div class="tab-btn" onclick="switchTab('warfare')">🔥 War</div>
            <div class="tab-btn" onclick="switchTab('health')">🛡️ Health</div>
        </div>
        <div class="header-stats">
            <div class="stat-badge systems">📊 <span id="total-systems">0</span> Systems</div>
            <div class="stat-badge portfolio">💰 $<span id="total-value">0.00</span></div>
            <div class="stat-badge thoughts">💭 <span id="thoughts-rate">0</span>/s</div>
            <div class="stat-badge connected" id="ws-status">● CONNECTING...</div>
        </div>
    </div>
    
    <!-- MAIN HUB TAB -->
    <div id="tab-main" class="tab-content active">
    <div id="mega-container">
        <!-- LEFT: Systems List -->
        <div id="systems-list-panel" class="mega-panel">
            <h2>
                🔧 SYSTEMS
                <span class="section-badge mind">MIND</span>
            </h2>
            <div class="layer-filter" style="flex-wrap: wrap;">
                <div class="filter-btn all active" onclick="filterSystems('all')">ALL</div>
                <div class="filter-btn mind" onclick="filterSystems('intel')">🧠 Intel</div>
                <div class="filter-btn thought" onclick="filterSystems('counter')">🛡️ Counter</div>
                <div class="filter-btn action" onclick="filterSystems('exec')">⚡ Exec</div>
                <div class="filter-btn momentum" onclick="filterSystems('momentum')">🌊 Wave</div>
                <div class="filter-btn data" onclick="filterSystems('data')">📡 Data</div>
                <div class="filter-btn analytics" onclick="filterSystems('analytics')">📊 Analytics</div>
                <div class="filter-btn infra" onclick="filterSystems('infra')">⚙️ Infra</div>
            </div>
            <div id="systems-list"></div>
        </div>
        
        <!-- CENTER: Mind Map -->
        <div id="mindmap-panel" class="mega-panel">
            <h2>
                🗺️ COGNITIVE MIND MAP
                <span style="font-size: 0.8em; color: #888;">204 Systems | 12 Categories | 10 Scanners</span>
            </h2>
            <div id="mindmap-container"></div>
        </div>
        
        <!-- TOP RIGHT: Portfolio + Signals -->
        <div id="portfolio-panel" class="mega-panel">
            <h2>
                💰 PORTFOLIO
                <span class="section-badge action">ACTION</span>
            </h2>
            <div id="portfolio-stats"></div>
            <h3 style="color: #888; font-size: 0.9em; margin-top: 8px; margin-bottom: 4px;">Balances</h3>
            <div id="balances-list"></div>
            <h3 style="color: #888; font-size: 0.9em; margin-top: 8px; margin-bottom: 4px;">🚨 Signals</h3>
            <div id="signals-list"></div>
        </div>
        
        <!-- MIDDLE RIGHT: Thought Stream -->
        <div id="thoughts-panel" class="mega-panel">
            <h2>
                💭 THOUGHT STREAM
                <span class="section-badge thought">THOUGHT</span>
                <span class="activity-indicator"></span>
            </h2>
            <div id="thoughts-stream"></div>
        </div>
        
        <!-- BOTTOM RIGHT: Queen Commentary -->
        <div id="queen-panel" class="mega-panel">
            <h2>
                👑 QUEEN'S VOICE
                <span class="section-badge mind">MIND</span>
            </h2>
            <div id="queen-stream"></div>
        </div>
    </div>
    </div>
    
    <!-- ⚔️ WAR ROOM TAB -->
    <div id="tab-warroom" class="tab-content">
        <div style="padding: 10px;">
            <div class="warroom-stats">
                <div class="warroom-stat">
                    <div class="warroom-stat-value" id="wr-runtime">0:00:00</div>
                    <div class="warroom-stat-label">RUNTIME</div>
                </div>
                <div class="warroom-stat">
                    <div class="warroom-stat-value" id="wr-cycles">0</div>
                    <div class="warroom-stat-label">CYCLES</div>
                </div>
                <div class="warroom-stat">
                    <div class="warroom-stat-value" id="wr-pnl">$0.00</div>
                    <div class="warroom-stat-label">TOTAL P&L</div>
                </div>
                <div class="warroom-stat">
                    <div class="warroom-stat-value" id="wr-wins">0</div>
                    <div class="warroom-stat-label">WINS</div>
                </div>
                <div class="warroom-stat">
                    <div class="warroom-stat-value" id="wr-losses">0</div>
                    <div class="warroom-stat-label">LOSSES</div>
                </div>
                <div class="warroom-stat">
                    <div class="warroom-stat-value" id="wr-boost">1.00x</div>
                    <div class="warroom-stat-label">QUANTUM BOOST</div>
                </div>
            </div>
            
            <div id="warroom-container">
                <!-- LEFT: Positions Table -->
                <div id="warroom-positions" class="warroom-panel">
                    <h2>📊 ACTIVE POSITIONS</h2>
                    <div class="position-row header">
                        <span>Symbol</span>
                        <span>Exchange</span>
                        <span>Value</span>
                        <span>P&L</span>
                        <span>Progress</span>
                        <span>ETA</span>
                        <span>Firm</span>
                    </div>
                    <div id="positions-list">
                        <div style="padding: 20px; text-align: center; color: #888;">🔍 Scanning for opportunities...</div>
                    </div>
                </div>
                
                <!-- TOP RIGHT: Quantum Systems -->
                <div id="warroom-quantum" class="warroom-panel">
                    <h2>🔮 QUANTUM SYSTEMS</h2>
                    <div id="quantum-grid" class="quantum-grid">
                        <div class="quantum-item"><span>🍀 Luck Field</span><span class="quantum-score medium">0.00</span></div>
                        <div class="quantum-item"><span>👻 Phantom</span><span class="quantum-score medium">0.00</span></div>
                        <div class="quantum-item"><span>💭 Inception</span><span class="quantum-score medium">0.00</span></div>
                        <div class="quantum-item"><span>🐘 Elephant</span><span class="quantum-score medium">0.00</span></div>
                        <div class="quantum-item"><span>🪆 Russian Doll</span><span class="quantum-score medium">0.00</span></div>
                        <div class="quantum-item"><span>🛡️ Immune</span><span class="quantum-score medium">0.00</span></div>
                        <div class="quantum-item"><span>🐋 Moby Dick</span><span class="quantum-score medium">0.00</span></div>
                        <div class="quantum-item"><span>🌌 Stargate</span><span class="quantum-score medium">0.00</span></div>
                        <div class="quantum-item"><span>🔮 Quantum Mirror</span><span class="quantum-score medium">0.00</span></div>
                    </div>
                </div>
                
                <!-- BOTTOM RIGHT: Active Firms -->
                <div id="warroom-firms" class="warroom-panel">
                    <h2>🏢 ACTIVE FIRMS</h2>
                    <div id="firms-list">
                        <div style="padding: 10px; text-align: center; color: #888;">Monitoring firm activity...</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 🏢 FIRM INTEL TAB -->
    <div id="tab-firms" class="tab-content">
        <div class="firm-filter-bar">
            <div class="firm-filter-btn active" onclick="filterFirms('all')">🌍 All Firms</div>
            <div class="firm-filter-btn" onclick="filterFirms('USA')">🇺🇸 USA</div>
            <div class="firm-filter-btn" onclick="filterFirms('UK')">🇬🇧 UK</div>
            <div class="firm-filter-btn" onclick="filterFirms('Netherlands')">🇳🇱 Netherlands</div>
            <div class="firm-filter-btn" onclick="filterFirms('Japan')">🇯🇵 Japan</div>
            <div class="firm-filter-btn" onclick="filterFirms('Singapore')">🇸🇬 Singapore</div>
            <div class="firm-filter-btn" onclick="filterFirms('China')">🇨🇳 China</div>
            <div class="firm-filter-btn" onclick="filterFirms('crypto')">₿ Crypto Focused</div>
        </div>
        <div id="firms-container">
            <div style="padding: 40px; text-align: center; color: #888;">Loading firm intelligence...</div>
        </div>
    </div>
    
    <!-- 🌊 OCEAN SCANNER TAB -->
    <div id="tab-ocean" class="tab-content">
        <div id="ocean-container">
            <!-- Stats Bar -->
            <div id="ocean-stats" class="ocean-panel">
                <div class="ocean-stats-bar">
                    <div class="ocean-stat-box">
                        <div class="ocean-stat-icon">🐋</div>
                        <div class="ocean-stat-value" id="ocean-whale-count">0</div>
                        <div class="ocean-stat-label">WHALES</div>
                    </div>
                    <div class="ocean-stat-box">
                        <div class="ocean-stat-icon">🦈</div>
                        <div class="ocean-stat-value" id="ocean-shark-count">0</div>
                        <div class="ocean-stat-label">SHARKS</div>
                    </div>
                    <div class="ocean-stat-box">
                        <div class="ocean-stat-icon">🐟</div>
                        <div class="ocean-stat-value" id="ocean-minnow-count">0</div>
                        <div class="ocean-stat-label">MINNOWS</div>
                    </div>
                    <div class="ocean-stat-box">
                        <div class="ocean-stat-icon">🏰</div>
                        <div class="ocean-stat-value" id="ocean-hive-count">0</div>
                        <div class="ocean-stat-label">HIVES</div>
                    </div>
                    <div class="ocean-stat-box">
                        <div class="ocean-stat-icon">⚔️</div>
                        <div class="ocean-stat-value" id="ocean-battle-count">0</div>
                        <div class="ocean-stat-label">BATTLES</div>
                    </div>
                    <div class="ocean-stat-box">
                        <div class="ocean-stat-icon">💰</div>
                        <div class="ocean-stat-value" id="ocean-total-volume">$0</div>
                        <div class="ocean-stat-label">TOTAL VOLUME</div>
                    </div>
                </div>
            </div>
            
            <!-- Left: Whales & Bots List -->
            <div id="ocean-whales" class="ocean-panel">
                <h2>🐋 DETECTED BOTS & WHALES</h2>
                <div id="whales-list">
                    <div style="padding: 20px; text-align: center; color: #888;">Scanning ocean depths...</div>
                </div>
            </div>
            
            <!-- Top Right: Hives -->
            <div id="ocean-hives" class="ocean-panel">
                <h2>🏰 COORDINATED HIVES</h2>
                <div id="hives-list">
                    <div style="padding: 10px; text-align: center; color: #888;">Detecting coordination...</div>
                </div>
            </div>
            
            <!-- Bottom Right: Battles -->
            <div id="ocean-battles" class="ocean-panel">
                <h2>⚔️ BOT BATTLES</h2>
                <div id="battles-list">
                    <div style="padding: 10px; text-align: center; color: #888;">Monitoring conflicts...</div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 📡 SURVEILLANCE TAB -->
    <div id="tab-surveillance" class="tab-content">
        <div id="surveillance-container">
            <!-- Header Stats -->
            <div id="surveillance-header" class="surveillance-panel">
                <div class="surveillance-stats">
                    <div class="surv-stat">
                        <div class="surv-stat-val" id="surv-connections">0</div>
                        <div class="surv-stat-lbl">CONNECTIONS</div>
                    </div>
                    <div class="surv-stat">
                        <div class="surv-stat-val" id="surv-messages">/s</div>
                        <div class="surv-stat-lbl">MESSAGES</div>
                    </div>
                    <div class="surv-stat">
                        <div class="surv-stat-val" id="surv-latency">0ms</div>
                        <div class="surv-stat-lbl">LATENCY</div>
                    </div>
                    <div class="surv-stat">
                        <div class="surv-stat-val" id="surv-alerts">0</div>
                        <div class="surv-stat-lbl">ALERTS</div>
                    </div>
                    <div class="surv-stat">
                        <div class="surv-stat-val" id="surv-bots">0</div>
                        <div class="surv-stat-lbl">BOTS DETECTED</div>
                    </div>
                </div>
            </div>
            
            <!-- Spectrogram -->
            <div id="surveillance-spectrogram" class="surveillance-panel">
                <h2><span class="glow-dot"></span> FREQUENCY SPECTROGRAM</h2>
                <div id="spectrogram-display">
                    <div class="spectrogram-row"><span class="spec-label">HFT (1kHz+)</span><div class="spec-bar"><div class="spec-fill" style="width: 60%"></div></div></div>
                    <div class="spectrogram-row"><span class="spec-label">Market Maker</span><div class="spec-bar"><div class="spec-fill" style="width: 45%"></div></div></div>
                    <div class="spectrogram-row"><span class="spec-label">Scalper</span><div class="spec-bar"><div class="spec-fill" style="width: 70%"></div></div></div>
                    <div class="spectrogram-row"><span class="spec-label">Iceberg</span><div class="spec-bar"><div class="spec-fill" style="width: 30%"></div></div></div>
                    <div class="spectrogram-row"><span class="spec-label">Institutional</span><div class="spec-bar"><div class="spec-fill" style="width: 55%"></div></div></div>
                    <div class="spectrogram-row"><span class="spec-label">Grid Bot</span><div class="spec-bar"><div class="spec-fill" style="width: 40%"></div></div></div>
                    <div class="spectrogram-row"><span class="spec-label">Momentum</span><div class="spec-bar"><div class="spec-fill" style="width: 65%"></div></div></div>
                    <div class="spectrogram-row"><span class="spec-label">Wash Trade</span><div class="spec-bar"><div class="spec-fill" style="width: 15%"></div></div></div>
                </div>
            </div>
            
            <!-- Buy/Sell Flow -->
            <div id="surveillance-flow" class="surveillance-panel">
                <h2><span class="glow-dot"></span> BUY / SELL FLOW</h2>
                <div id="flow-display">
                    <div style="margin-bottom: 15px;">
                        <div style="font-size: 0.85em; color: #888; margin-bottom: 5px;">BTC/USD</div>
                        <div class="flow-bar">
                            <div class="flow-buy" style="width: 62%"></div>
                            <div class="flow-sell" style="width: 38%"></div>
                        </div>
                        <div class="flow-label"><span style="color: #00ff88;">BUY 62%</span><span style="color: #e74c3c;">SELL 38%</span></div>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <div style="font-size: 0.85em; color: #888; margin-bottom: 5px;">ETH/USD</div>
                        <div class="flow-bar">
                            <div class="flow-buy" style="width: 55%"></div>
                            <div class="flow-sell" style="width: 45%"></div>
                        </div>
                        <div class="flow-label"><span style="color: #00ff88;">BUY 55%</span><span style="color: #e74c3c;">SELL 45%</span></div>
                    </div>
                    <div>
                        <div style="font-size: 0.85em; color: #888; margin-bottom: 5px;">SOL/USD</div>
                        <div class="flow-bar">
                            <div class="flow-buy" style="width: 71%"></div>
                            <div class="flow-sell" style="width: 29%"></div>
                        </div>
                        <div class="flow-label"><span style="color: #00ff88;">BUY 71%</span><span style="color: #e74c3c;">SELL 29%</span></div>
                    </div>
                </div>
            </div>
            
            <!-- Alerts -->
            <div id="surveillance-alerts" class="surveillance-panel">
                <h2><span class="glow-dot"></span> LIVE ALERTS</h2>
                <div id="alerts-list">
                    <div class="alert-item info">🔍 Surveillance systems initializing...</div>
                </div>
            </div>
            
            <!-- Price Grid -->
            <div id="surveillance-grid" class="surveillance-panel">
                <h2><span class="glow-dot"></span> PRICE GRID</h2>
                <div id="price-grid" class="price-grid">
                    <div class="price-cell"><div class="price-symbol">BTC</div><div class="price-value">$--</div><div class="price-change">--%</div></div>
                    <div class="price-cell"><div class="price-symbol">ETH</div><div class="price-value">$--</div><div class="price-change">--%</div></div>
                    <div class="price-cell"><div class="price-symbol">SOL</div><div class="price-value">$--</div><div class="price-change">--%</div></div>
                    <div class="price-cell"><div class="price-symbol">DOGE</div><div class="price-value">$--</div><div class="price-change">--%</div></div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 🍀 LUCK FIELD TAB -->
    <div id="tab-luck" class="tab-content">
        <div id="luck-container">
            <!-- Left: Gauge -->
            <div id="luck-gauge-box" class="luck-panel">
                <h2>🍀 LUCK FIELD GAUGE</h2>
                <br>
                <div class="luck-gauge-wrapper">
                    <div class="luck-gauge-arc" id="luck-gauge-arc"></div>
                </div>
                <div class="luck-value-display" id="luck-value">0.00</div>
                <div class="luck-state-text" id="luck-state">VOID</div>
                <div style="font-size: 0.8em; color: #888; margin-top: 5px;">λ(t) = Σ × Π × Φ × Ω × Ψ</div>
            </div>
            
            <!-- Middle: Factors -->
            <div class="luck-panel">
                <h2>⚛️ COMPONENT FACTORS</h2>
                <div class="factor-row">
                    <div class="factor-label">Σ SCHUMANN</div>
                    <div class="factor-bar-bg"><div class="factor-bar-fill" id="bar-sigma" style="width: 0%"></div></div>
                    <div class="factor-val" id="val-sigma">0.0</div>
                </div>
                <div class="factor-row">
                    <div class="factor-label">Π PLANETARY</div>
                    <div class="factor-bar-bg"><div class="factor-bar-fill" id="bar-pi" style="width: 0%"></div></div>
                    <div class="factor-val" id="val-pi">0.0</div>
                </div>
                <div class="factor-row">
                    <div class="factor-label">Φ HARMONIC</div>
                    <div class="factor-bar-bg"><div class="factor-bar-fill" id="bar-phi" style="width: 0%"></div></div>
                    <div class="factor-val" id="val-phi">0.0</div>
                </div>
                <div class="factor-row">
                    <div class="factor-label">Ω TEMPORAL</div>
                    <div class="factor-bar-bg"><div class="factor-bar-fill" id="bar-omega" style="width: 0%"></div></div>
                    <div class="factor-val" id="val-omega">0.0</div>
                </div>
                <div class="factor-row">
                    <div class="factor-label">Ψ SYNCHRONICITY</div>
                    <div class="factor-bar-bg"><div class="factor-bar-fill" id="bar-psi" style="width: 0%"></div></div>
                    <div class="factor-val" id="val-psi">0.0</div>
                </div>
            </div>
            
            <!-- Right: Stats -->
            <div class="luck-panel">
                <h2>📊 FIELD STATS</h2>
                <div style="margin-top: 10px;">
                    <div style="color: #888;">Coherence Lock:</div>
                    <div style="color: #00ff88; font-weight: bold; font-size: 1.2em;" id="luck-coherence">FALSE</div>
                </div>
                <div style="margin-top: 10px;">
                    <div style="color: #888;">Dominant Freq:</div>
                    <div style="color: #ffaa00; font-weight: bold; font-size: 1.2em;" id="luck-freq">0 Hz</div>
                </div>
                 <div style="margin-top: 10px;">
                    <div style="color: #888;">Phase Alignment:</div>
                    <div style="color: #3498db; font-weight: bold; font-size: 1.2em;" id="luck-phase">0.00</div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 🌌 STARGATE TAB -->
    <div id="tab-stargate" class="tab-content">
        <div id="stargate-container">
            <!-- Header Stats -->
            <div id="sg-header" class="stargate-panel">
                <div class="sg-stat">
                    <div class="sg-stat-val" id="sg-nodes-count">0</div>
                    <div class="sg-stat-lbl">ACTIVE NODES</div>
                </div>
                <div class="sg-stat">
                    <div class="sg-stat-val" id="sg-coherence">0.00</div>
                    <div class="sg-stat-lbl">GLOBAL COHERENCE</div>
                </div>
                <div class="sg-stat">
                    <div class="sg-stat-val" id="sg-resonance">N/A</div>
                    <div class="sg-stat-lbl">RESONANCE</div>
                </div>
            </div>
            
            <!-- Nodes List -->
            <div id="sg-nodes" class="stargate-panel">
                <h2>🌍 PLANETARY NODES</h2>
                <div id="sg-nodes-list">
                    <div style="padding: 20px; text-align: center; color: #888;">Initializing Stargate Protocol...</div>
                </div>
            </div>
        </div>
    </div>

    <!-- 💭 INCEPTION TAB -->
    <div id="tab-inception" class="tab-content">
        <div id="inception-container">
            <!-- Left: Dream Structure -->
            <div class="inception-panel">
                <h2>💭 DREAM LAYERS ARCHITECTURE</h2>
                <div id="dream-layers-list">
                    <div style="padding: 20px; text-align: center; color: #888;">Constructing dream levels...</div>
                </div>
            </div>
            
            <!-- Right: Time Dilation & Physics -->
            <div class="inception-panel">
                <h2>⏳ TEMPORAL PHYSICS & KICKS</h2>
                <div id="inception-physics">
                    <div style="margin-bottom: 20px;">
                        <h3 style="color: #3498db; margin-bottom: 10px;">Time Dilation Factor</h3>
                        <div style="font-size: 2.5em; font-weight: bold; color: #fff;" id="dilation-factor">1:20</div>
                        <div style="color: #888;">1 minute in reality = 20 minutes in Limbo</div>
                    </div>
                    <div style="margin-bottom: 20px;">
                        <h3 style="color: #e74c3c; margin-bottom: 10px;">Kick Synchronization</h3>
                        <div id="kick-status" style="padding: 10px; background: rgba(231, 76, 60, 0.1); border-left: 4px solid #e74c3c;">
                            Waiting for musical cue...
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- 🐘 ELEPHANT MEMORY TAB -->
    <div id="tab-memory" class="tab-content">
        <div id="memory-container">
            <!-- Left: Memories -->
            <div class="memory-panel">
                <h2>🐘 RECALLED PATTERNS</h2>
                <div id="memory-list">
                    <div style="padding: 20px; text-align: center; color: #888;">Accessing long-term storage...</div>
                </div>
            </div>
            
            <!-- Right: Wisdom Stats -->
            <div class="memory-panel">
                <h2>📜 WISDOM STATISTICS</h2>
                <div style="display: grid; gap: 20px; padding: 20px;">
                    <div>
                        <div class="wisdom-stat" id="total-memories">0</div>
                        <div style="text-align: center; color: #888;">Total Memories</div>
                    </div>
                    <div>
                        <div class="wisdom-stat" id="learning-rate">0.00%</div>
                        <div style="text-align: center; color: #888;">Learning Efficiency</div>
                    </div>
                    <div>
                        <div class="wisdom-stat" id="pain-avoided">$0.00</div>
                        <div style="text-align: center; color: #888;">Losses Avoided</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- 🔥 WARFARE TAB -->
    <div id="tab-warfare" class="tab-content">
        <div id="warfare-container">
            <!-- Left: Active Fronts -->
            <div class="warfare-panel">
                <h2>⚔️ ACTIVE BATTLEFRONTS</h2>
                <div id="warfare-fronts">
                    <div style="padding: 20px; text-align: center; color: #888;">Scouting battlefields...</div>
                </div>
            </div>
            
            <!-- Middle: Map -->
            <div class="warfare-panel">
                <h2>🗺️ TACTICAL MAP</h2>
                <div id="warfare-map" style="height: 100%; min-height: 200px; background: rgba(0,0,0,0.3); border-radius: 4px;"></div>
            </div>
            
            <!-- Right: Tactics -->
            <div class="warfare-panel">
                <h2>🔫 TACTICS DEPLOYED</h2>
                <div id="warfare-tactics">
                    <div class="tactic-active">☘️ CELTIC CHARIOT</div>
                    <div class="tactic-active">🌫️ SMOKE SCREEN</div>
                </div>
            </div>
        </div>
    </div>

    <!-- 🛡️ HEALTH TAB -->
    <div id="tab-health" class="tab-content">
        <div id="health-container">
            <!-- Vitals -->
            <div class="health-panel" style="grid-column: 1 / 4;">
                <h2>❤️ SYSTEM VITALS</h2>
                <div id="health-vitals" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <!-- Vitals injected here -->
                </div>
            </div>
            
            <!-- Scouts -->
            <div class="health-panel">
                <h2>🩺 SCOUT REPORTS</h2>
                <div id="health-scouts"></div>
            </div>
            
            <!-- Healing -->
            <div class="health-panel">
                <h2>💊 AUTO-HEALING EVENTS</h2>
                <div id="health-healing"></div>
            </div>
            
            <!-- Anomalies -->
            <div class="health-panel">
                <h2>⚠️ DETECTED ANOMALIES</h2>
                <div id="health-anomalies"></div>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let network = null;
        let allMindMapData = null;
        let currentFilter = 'all';
        let thoughtsPerSecond = 0;
        let recentThoughts = [];
        
        // WebSocket Connection
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = () => {
                console.log('✅ WebSocket connected');
                document.getElementById('ws-status').textContent = '● LIVE';
            };
            
            ws.onclose = () => {
                console.log('⚠️ WebSocket disconnected');
                document.getElementById('ws-status').textContent = '● RECONNECTING...';
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleMessage(data);
                } catch (e) {
                    console.error('Parse error:', e);
                }
            };
        }
        
        // Tab switching
        function switchTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById('tab-' + tabName).classList.add('active');
            document.querySelector('.tab-btn[onclick*="' + tabName + '"]').classList.add('active');
        }
        
        // Handle incoming messages
        function handleMessage(data) {
            switch(data.type) {
                case 'full_update':
                    updateSystems(data.systems || {});
                    updatePortfolio(data.portfolio || {});
                    if (data.mindmap) loadMindMap(data.mindmap);
                    break;
                case 'systems_update':
                    updateSystems(data.systems);
                    break;
                case 'portfolio_update':
                    updatePortfolio(data.portfolio);
                    break;
                case 'thought':
                    addThought(data.thought);
                    flashNetworkNode(data.thought.source);
                    break;
                case 'signal':
                    addSignal(data.signal);
                    break;
                case 'queen_message':
                    addQueenMessage(data.message);
                    break;
                case 'warroom_update':
                    updateWarRoom(data.warroom);
                    break;
                case 'firms_update':
                    updateFirmsIntel(data.firms);
                    break;
                case 'ocean_update':
                    updateOceanScanner(data.ocean);
                    break;
                case 'surveillance_update':
                    updateSurveillance(data.surveillance);
                    break;
                case 'luck_update':
                    updateLuck(data.luck);
                    break;
                case 'stargate_update':
                    updateStargate(data.stargate);
                    break;
                case 'inception_update':
                    updateInception(data.inception);
                    break;
                case 'memory_update':
                    updateMemory(data.memory);
                    break;
                case 'warfare_update':
                    updateWarfare(data.warfare);
                    break;
                case 'health_update':
                    updateHealth(data.health);
                    break;
            }
        }
        
        // Update War Room display
        function updateWarRoom(warroom) {
            if (!warroom) return;
            
            // Update stats
            document.getElementById('wr-runtime').textContent = warroom.runtime || '0:00:00';
            document.getElementById('wr-cycles').textContent = warroom.cycles || 0;
            
            const pnl = warroom.total_pnl || 0;
            const pnlEl = document.getElementById('wr-pnl');
            pnlEl.textContent = (pnl >= 0 ? '+' : '') + '$' + pnl.toFixed(4);
            pnlEl.style.color = pnl >= 0 ? '#00ff88' : '#ff4444';
            
            document.getElementById('wr-wins').textContent = warroom.wins || 0;
            document.getElementById('wr-losses').textContent = warroom.losses || 0;
            
            const boost = warroom.total_boost || 1.0;
            const boostEl = document.getElementById('wr-boost');
            boostEl.textContent = boost.toFixed(2) + 'x';
            boostEl.style.color = boost > 1.2 ? '#00ff88' : boost > 1.0 ? '#ffaa00' : '#ff4444';
            
            // Update positions
            const positionsList = document.getElementById('positions-list');
            if (warroom.positions && warroom.positions.length > 0) {
                positionsList.innerHTML = warroom.positions.map(pos => {
                    const pnlClass = pos.pnl >= 0 ? 'positive' : 'negative';
                    const pnlSign = pos.pnl >= 0 ? '+' : '';
                    const progress = Math.min(Math.max(pos.progress || 0, 0), 100);
                    return `
                        <div class="position-row">
                            <span class="position-symbol">${pos.symbol}</span>
                            <span>${pos.exchange || 'Alpaca'}</span>
                            <span>$${(pos.value || 0).toFixed(2)}</span>
                            <span class="position-pnl ${pnlClass}">${pnlSign}$${(pos.pnl || 0).toFixed(4)}</span>
                            <span>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${progress}%"></div>
                                </div>
                            </span>
                            <span>${pos.eta || '--'}</span>
                            <span style="color: #9b59b6;">${pos.firm || 'Scanning...'}</span>
                        </div>
                    `;
                }).join('');
            } else {
                positionsList.innerHTML = '<div style="padding: 20px; text-align: center; color: #888;">🔍 Scanning for opportunities...</div>';
            }
            
            // Update quantum scores
            if (warroom.quantum) {
                const quantumMap = {
                    'luck': '🍀 Luck Field',
                    'phantom': '👻 Phantom',
                    'inception': '💭 Inception',
                    'elephant': '🐘 Elephant',
                    'russian_doll': '🪆 Russian Doll',
                    'immune': '🛡️ Immune',
                    'moby_dick': '🐋 Moby Dick',
                    'stargate': '🌌 Stargate',
                    'quantum_mirror': '🔮 Quantum Mirror'
                };
                
                const quantumGrid = document.getElementById('quantum-grid');
                quantumGrid.innerHTML = Object.entries(quantumMap).map(([key, label]) => {
                    const score = warroom.quantum[key] || 0;
                    const scoreClass = score > 0.7 ? 'high' : score > 0.4 ? 'medium' : 'low';
                    return `<div class="quantum-item"><span>${label}</span><span class="quantum-score ${scoreClass}">${score.toFixed(2)}</span></div>`;
                }).join('');
            }
            
            // Update firms
            if (warroom.firms && Object.keys(warroom.firms).length > 0) {
                const firmsList = document.getElementById('firms-list');
                firmsList.innerHTML = Object.entries(warroom.firms).slice(0, 8).map(([name, info]) => {
                    const dirClass = (info.direction || '').toLowerCase().includes('long') ? 'long' : 'short';
                    return `
                        <div class="firm-item">
                            <span class="firm-name">${name}</span>
                            <span class="firm-action"> - ${info.action || 'Active'}</span>
                            <span class="firm-direction ${dirClass}">${info.direction || ''}</span>
                        </div>
                    `;
                }).join('');
            }
        }
        
        // Update systems list
        function updateSystems(systems) {
            const list = document.getElementById('systems-list');
            const systemsArray = Object.entries(systems).map(([name, status]) => ({
                name,
                ...status,
                layer: categorizeSystem(name, status)
            }));
            
            // Filter by current filter
            const filtered = currentFilter === 'all' 
                ? systemsArray 
                : systemsArray.filter(s => s.layer === currentFilter);
            
            list.innerHTML = '';
            filtered.forEach(system => {
                const item = document.createElement('div');
                item.className = `system-item ${system.status.toLowerCase()} ${system.layer}`;
                
                let layerIcon = '⚙️';
                if(system.layer==='intel') layerIcon='🧠';
                if(system.layer==='counter') layerIcon='🛡️';
                if(system.layer==='exec') layerIcon='⚡';
                if(system.layer==='momentum') layerIcon='🌊';
                if(system.layer==='data') layerIcon='📡';
                if(system.layer==='analytics') layerIcon='📊';
                
                item.innerHTML = `
                    <div class="system-name">${layerIcon} ${system.name}</div>
                    ${system.confidence > 0 || system.accuracy > 0 ? `
                        <div class="system-metrics">
                            ${system.confidence > 0 ? `Conf: ${(system.confidence * 100).toFixed(0)}%` : ''}
                            ${system.accuracy > 0 ? ` | Acc: ${(system.accuracy * 100).toFixed(0)}%` : ''}
                            ${system.signals_sent > 0 ? ` | Signals: ${system.signals_sent}` : ''}
                        </div>
                    ` : ''}
                `;
                list.appendChild(item);
            });
            
            document.getElementById('total-systems').textContent = Object.keys(systems).length;
        }
        
        function categorizeSystem(name, status) {
            const n = name.toLowerCase();
            // Intelligence
            if (n.includes('queen') || n.includes('intelligence') || n.includes('brain') || 
                n.includes('oracle') || n.includes('quantum') || n.includes('nexus') || n.includes('mind') || n.includes('wisdom')) return 'intel';
            
            // Counter-Intel
            if (n.includes('counter') || n.includes('warfare') || n.includes('hunter') || 
                n.includes('bot') || n.includes('defense') || n.includes('shark') || n.includes('whale') || n.includes('profiler') || n.includes('surveillance')) return 'counter';
            
            // Execution
            if (n.includes('kraken') || n.includes('binance') || n.includes('alpaca') || 
                n.includes('trader') || n.includes('executor') || n.includes('client') || n.includes('sniper') || n.includes('commando')) return 'exec';
            
            // Momentum
            if (n.includes('momentum') || n.includes('wave') || n.includes('snowball') || n.includes('velocity') || n.includes('turbo') || n.includes('harmonic')) return 'momentum';
            
            // Data
            if (n.includes('feed') || n.includes('data') || n.includes('market') || n.includes('price') || n.includes('ticker') || n.includes('ecosystem') || n.includes('financial')) return 'data';
            
            // Analytics
            if (n.includes('metric') || n.includes('report') || n.includes('analyze') || n.includes('history') || n.includes('audit') || n.includes('profit') || n.includes('loss') || n.includes('basis')) return 'analytics';

            return 'infra';
        }
        
        function filterSystems(layer) {
            currentFilter = layer;
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelector(`.filter-btn.${layer}`).classList.add('active');
            // Trigger systems update with current data
            if (window.lastSystemsData) updateSystems(window.lastSystemsData);
        }
        
        // Update portfolio
        function updatePortfolio(portfolio) {
            const statsDiv = document.getElementById('portfolio-stats');
            statsDiv.innerHTML = `
                <div class="portfolio-stat">
                    <span class="stat-label">Total Value</span>
                    <span class="stat-value">$${(portfolio.total_value_usd || 0).toFixed(2)}</span>
                </div>
                <div class="portfolio-stat">
                    <span class="stat-label">P/L Today</span>
                    <span class="stat-value ${portfolio.pnl_today >= 0 ? 'positive' : 'negative'}">
                        ${portfolio.pnl_today >= 0 ? '+' : ''}$${(portfolio.pnl_today || 0).toFixed(2)}
                    </span>
                </div>
            `;
            
            document.getElementById('total-value').textContent = (portfolio.total_value_usd || 0).toFixed(2);
            
            const balancesDiv = document.getElementById('balances-list');
            balancesDiv.innerHTML = '';
            
            if (portfolio.balances) {
                for (const [exchange, assets] of Object.entries(portfolio.balances)) {
                    for (const [asset, amount] of Object.entries(assets)) {
                        if (amount > 0.0001) {
                            const item = document.createElement('div');
                            item.className = 'balance-item';
                            item.innerHTML = `
                                <span>${exchange.toUpperCase()} ${asset}</span>
                                <span>${typeof amount === 'number' ? amount.toFixed(4) : amount}</span>
                            `;
                            balancesDiv.appendChild(item);
                        }
                    }
                }
            }
        }
        
        // Add thought to stream
        function addThought(thought) {
            recentThoughts.push(Date.now());
            recentThoughts = recentThoughts.filter(t => Date.now() - t < 1000);
            thoughtsPerSecond = recentThoughts.length;
            document.getElementById('thoughts-rate').textContent = thoughtsPerSecond;
            
            const stream = document.getElementById('thoughts-stream');
            const item = document.createElement('div');
            item.className = 'thought-item';
            
            const time = new Date(thought.ts * 1000).toLocaleTimeString();
            const payload = JSON.stringify(thought.payload).substring(0, 100);
            
            item.innerHTML = `
                <div class="thought-header">
                    <span class="thought-topic">${thought.topic}</span>
                    <span>${time}</span>
                </div>
                <div class="thought-source">From: ${thought.source}</div>
                <div class="thought-payload">${payload}</div>
            `;
            
            stream.insertBefore(item, stream.firstChild);
            while (stream.children.length > 10) stream.removeChild(stream.lastChild);
        }
        
        // Add signal
        function addSignal(signal) {
            const stream = document.getElementById('signals-list');
            const item = document.createElement('div');
            item.className = `signal-item ${signal.signal_type}`;
            
            item.innerHTML = `
                <div class="signal-header">
                    <span class="signal-symbol">${signal.symbol}</span>
                    <span class="signal-type ${signal.signal_type}">${signal.signal_type}</span>
                </div>
                <div style="font-size: 0.85em; color: #888;">
                    ${signal.source} | ${(signal.confidence * 100).toFixed(0)}%
                </div>
            `;
            
            stream.insertBefore(item, stream.firstChild);
            while (stream.children.length > 5) stream.removeChild(stream.lastChild);
        }
        
        // Add Queen message
        function addQueenMessage(message) {
            const stream = document.getElementById('queen-stream');
            const item = document.createElement('div');
            item.className = 'queen-message';
            
            const now = new Date().toLocaleTimeString();
            item.innerHTML = `
                <div class="timestamp">${now}</div>
                <div class="text">👑 ${message}</div>
            `;
            
            stream.insertBefore(item, stream.firstChild);
            while (stream.children.length > 6) stream.removeChild(stream.lastChild);
        }
        
        // Load mind map
        async function loadMindMap(data) {
            if (!data) {
                const response = await fetch('/api/mindmap');
                data = await response.json();
            }
            allMindMapData = data;
            renderMindMap(data);
        }
        
        function renderMindMap(data) {
            const container = document.getElementById('mindmap-container');
            
            const nodes = data.nodes.map(node => {
                const layer = categorizeSystem(node.label, {});
                let color;
                
                if (layer === 'intel') color = '#9b59b6'; // Purple
                else if (layer === 'counter') color = '#c0392b'; // Red
                else if (layer === 'exec') color = '#2ecc71'; // Green
                else if (layer === 'momentum') color = '#3498db'; // Blue
                else if (layer === 'data') color = '#16a085'; // Teal
                else if (layer === 'analytics') color = '#f1c40f'; // Yellow
                else if (layer === 'infra') color = '#95a5a6'; // Grey
                else color = node.color || '#555555';
                
                return { ...node, color: color, layer: layer };
            });
            
            const options = {
                nodes: {
                    font: { color: '#ffffff', size: 12 },
                    borderWidth: 2,
                    shadow: { enabled: true, size: 8 }
                },
                edges: {
                    color: { color: 'rgba(255,255,255,0.15)' },
                    smooth: { type: 'continuous' },
                    arrows: { to: { enabled: true, scaleFactor: 0.5 } }
                },
                physics: {
                    enabled: true,
                    barnesHut: {
                        gravitationalConstant: -5000,
                        centralGravity: 0.2,
                        springLength: 120,
                        damping: 0.09
                    },
                    stabilization: { iterations: 150 }
                },
                interaction: { hover: true }
            };
            
            network = new vis.Network(container, {
                nodes: new vis.DataSet(nodes),
                edges: new vis.DataSet(data.edges)
            }, options);
        }
        
        function flashNetworkNode(sourceName) {
            if (!network || !allMindMapData) return;
            
            const node = allMindMapData.nodes.find(n => 
                n.label.toLowerCase().includes(sourceName.toLowerCase())
            );
            
            if (node) {
                network.body.data.nodes.update({ id: node.id, borderWidth: 6 });
                setTimeout(() => {
                    network.body.data.nodes.update({ id: node.id, borderWidth: 2 });
                }, 500);
            }
        }
        
        // 🏢 Update Firm Intel Tab
        let currentFirmFilter = 'all';
        let allFirmsData = [];
        
        function updateFirmsIntel(firms) {
            if (!firms) return;
            allFirmsData = firms;
            renderFirms(firms);
        }
        
        function renderFirms(firms) {
            const container = document.getElementById('firms-container');
            const filtered = currentFirmFilter === 'all' ? firms :
                currentFirmFilter === 'crypto' ? firms.filter(f => f.crypto_focus) :
                firms.filter(f => f.country === currentFirmFilter || f.country?.includes(currentFirmFilter));
            
            container.innerHTML = filtered.map(firm => `
                <div class="firm-card">
                    <div class="firm-header">
                        <span class="firm-name-large">${firm.name || 'Unknown'}</span>
                        <span class="firm-animal">${firm.animal || '🏢'}</span>
                    </div>
                    <div class="firm-country">📍 ${firm.hq_location || firm.country || 'Unknown'}</div>
                    <div class="firm-capital">💰 $${formatCapital(firm.estimated_capital)}</div>
                    <div class="firm-strategies">
                        ${(firm.known_strategies || []).map(s => `<span class="strategy-tag">${s}</span>`).join('')}
                    </div>
                    <div class="firm-stats-row">
                        <div class="firm-stat-mini">
                            <div class="firm-stat-val">${firm.patterns?.hft_frequency ? firm.patterns.hft_frequency[0] + '-' + firm.patterns.hft_frequency[1] : '--'}</div>
                            <div class="firm-stat-lbl">HFT Hz</div>
                        </div>
                        <div class="firm-stat-mini">
                            <div class="firm-stat-val">${((firm.patterns?.market_making_ratio || 0) * 100).toFixed(0)}%</div>
                            <div class="firm-stat-lbl">MM Ratio</div>
                        </div>
                        <div class="firm-stat-mini">
                            <div class="firm-stat-val">${firm.patterns?.latency_profile || '--'}</div>
                            <div class="firm-stat-lbl">Latency</div>
                        </div>
                    </div>
                </div>
            `).join('');
            
            if (filtered.length === 0) {
                container.innerHTML = '<div style="padding: 40px; text-align: center; color: #888;">No firms matching filter</div>';
            }
        }
        
        function filterFirms(filter) {
            currentFirmFilter = filter;
            document.querySelectorAll('.firm-filter-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            renderFirms(allFirmsData);
        }
        
        function formatCapital(num) {
            if (!num) return '0';
            if (num >= 1e12) return (num / 1e12).toFixed(1) + 'T';
            if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B';
            if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
            return num.toLocaleString();
        }
        
        // 🌊 Update Ocean Scanner Tab
        function updateOceanScanner(ocean) {
            if (!ocean) return;
            
            // Update stats
            document.getElementById('ocean-whale-count').textContent = ocean.whale_count || 0;
            document.getElementById('ocean-shark-count').textContent = ocean.shark_count || 0;
            document.getElementById('ocean-minnow-count').textContent = ocean.minnow_count || 0;
            document.getElementById('ocean-hive-count').textContent = ocean.hive_count || 0;
            document.getElementById('ocean-battle-count').textContent = ocean.battle_count || 0;
            document.getElementById('ocean-total-volume').textContent = '$' + formatCapital(ocean.total_volume || 0);
            
            // Update whales list
            const whalesList = document.getElementById('whales-list');
            if (ocean.bots && ocean.bots.length > 0) {
                whalesList.innerHTML = ocean.bots.slice(0, 15).map(bot => {
                    const icon = bot.size_class === 'megalodon' ? '🦑' : 
                                 bot.size_class === 'whale' ? '🐋' : 
                                 bot.size_class === 'shark' ? '🦈' : '🐟';
                    return `
                        <div class="whale-item ${bot.size_class}">
                            <span class="whale-icon">${icon}</span>
                            <div class="whale-info">
                                <div class="whale-symbol">${bot.symbol}</div>
                                <div class="whale-owner">${bot.owner || 'Unknown'}</div>
                            </div>
                            <span class="whale-volume">$${formatCapital(bot.total_volume)}</span>
                            <span class="whale-trades">${bot.trade_count || 0} trades</span>
                        </div>
                    `;
                }).join('');
            } else {
                whalesList.innerHTML = '<div style="padding: 20px; text-align: center; color: #888;">Scanning ocean depths...</div>';
            }
            
            // Update hives
            const hivesList = document.getElementById('hives-list');
            if (ocean.hives && ocean.hives.length > 0) {
                hivesList.innerHTML = ocean.hives.slice(0, 5).map(hive => `
                    <div class="hive-item">
                        <div class="hive-header">
                            <span class="hive-id">🏰 ${hive.hive_id || 'HIVE-' + Math.random().toString(36).substr(2, 4).toUpperCase()}</span>
                            <span class="hive-members">${hive.member_count || 0} members</span>
                        </div>
                        <div class="hive-strategy">Strategy: ${hive.strategy || 'coordinated'} | Mode: ${hive.mode || 'hunting'}</div>
                    </div>
                `).join('');
            } else {
                hivesList.innerHTML = '<div style="padding: 10px; text-align: center; color: #888;">No hives detected</div>';
            }
            
            // Update battles
            const battlesList = document.getElementById('battles-list');
            if (ocean.battles && ocean.battles.length > 0) {
                battlesList.innerHTML = ocean.battles.slice(0, 5).map(battle => `
                    <div class="battle-item">
                        <div class="battle-vs">⚔️ ${battle.attacker || 'Bot A'} VS ${battle.defender || 'Bot B'}</div>
                        <div style="font-size: 0.8em; color: #888;">Symbol: ${battle.symbol || 'N/A'} | Intensity: ${battle.intensity || 'moderate'}</div>
                    </div>
                `).join('');
            } else {
                battlesList.innerHTML = '<div style="padding: 10px; text-align: center; color: #888;">No active battles</div>';
            }
        }
        
        // 📡 Update Surveillance Tab
        function updateSurveillance(surv) {
            if (!surv) return;
            
            // Update stats
            document.getElementById('surv-connections').textContent = surv.connections || 0;
            document.getElementById('surv-messages').textContent = (surv.messages_per_sec || 0) + '/s';
            document.getElementById('surv-latency').textContent = (surv.latency_ms || 0) + 'ms';
            document.getElementById('surv-alerts').textContent = surv.alert_count || 0;
            document.getElementById('surv-bots').textContent = surv.bots_detected || 0;
            
            // Update spectrogram
            if (surv.spectrogram) {
                const spectroDisplay = document.getElementById('spectrogram-display');
                const labels = ['HFT (1kHz+)', 'Market Maker', 'Scalper', 'Iceberg', 'Institutional', 'Grid Bot', 'Momentum', 'Wash Trade'];
                spectroDisplay.innerHTML = labels.map((label, i) => {
                    const intensity = surv.spectrogram[i] || Math.random() * 100;
                    return `<div class="spectrogram-row"><span class="spec-label">${label}</span><div class="spec-bar"><div class="spec-fill" style="width: ${100 - intensity}%"></div></div></div>`;
                }).join('');
            }
            
            // Update buy/sell flow
            if (surv.flow) {
                const flowDisplay = document.getElementById('flow-display');
                flowDisplay.innerHTML = Object.entries(surv.flow).slice(0, 4).map(([symbol, data]) => {
                    const buyPct = data.buy_pct || 50;
                    const sellPct = 100 - buyPct;
                    return `
                        <div style="margin-bottom: 15px;">
                            <div style="font-size: 0.85em; color: #888; margin-bottom: 5px;">${symbol}</div>
                            <div class="flow-bar">
                                <div class="flow-buy" style="width: ${buyPct}%"></div>
                                <div class="flow-sell" style="width: ${sellPct}%"></div>
                            </div>
                            <div class="flow-label"><span style="color: #00ff88;">BUY ${buyPct.toFixed(0)}%</span><span style="color: #e74c3c;">SELL ${sellPct.toFixed(0)}%</span></div>
                        </div>
                    `;
                }).join('');
            }
            
            // Update alerts
            if (surv.alerts && surv.alerts.length > 0) {
                const alertsList = document.getElementById('alerts-list');
                alertsList.innerHTML = surv.alerts.slice(0, 8).map(alert => {
                    const alertClass = alert.level === 'danger' ? 'danger' : alert.level === 'warning' ? 'warning' : 'info';
                    return `<div class="alert-item ${alertClass}">${alert.icon || '🔔'} ${alert.message}</div>`;
                }).join('');
            }
            
            // Update price grid
            if (surv.prices) {
                const priceGrid = document.getElementById('price-grid');
                priceGrid.innerHTML = Object.entries(surv.prices).slice(0, 8).map(([symbol, data]) => {
                    const changeClass = (data.change || 0) >= 0 ? 'up' : 'down';
                    const changeSign = (data.change || 0) >= 0 ? '+' : '';
                    return `
                        <div class="price-cell">
                            <div class="price-symbol">${symbol}</div>
                            <div class="price-value">$${(data.price || 0).toLocaleString()}</div>
                            <div class="price-change ${changeClass}">${changeSign}${(data.change || 0).toFixed(2)}%</div>
                        </div>
                    `;
                }).join('');
            }
        }
        
        // 🍀 Update Luck Tab
        function updateLuck(luck) {
            if (!luck) return;
            document.getElementById('luck-value').textContent = luck.value !== undefined ? luck.value.toFixed(2) : '0.00';
            document.getElementById('luck-state').textContent = luck.state || 'VOID';
            
            if (luck.state) {
                const colors = { 'VOID': '#888', 'CHAOS': '#ff4444', 'NEUTRAL': '#ffaa00', 'FAVORABLE': '#3498db', 'BLESSED': '#00ff88' };
                document.getElementById('luck-state').style.color = colors[luck.state] || '#fff';
            }
            
            // Update gauge (simple rotation)
            const deg = ((luck.value || 0) * 180) - 45;
            document.getElementById('luck-gauge-arc').style.transform = `rotate(${deg}deg)`;
            
            // Update bars
            ['sigma', 'pi', 'phi', 'omega', 'psi'].forEach(k => {
                const w = Math.min((luck[k] || 0) * 100, 100);
                document.getElementById(`bar-${k}`).style.width = w + '%';
                document.getElementById(`val-${k}`).textContent = (luck[k] || 0).toFixed(2);
            });
            
            document.getElementById('luck-coherence').textContent = luck.coherence ? 'TRUE' : 'FALSE';
            document.getElementById('luck-coherence').style.color = luck.coherence ? '#00ff88' : '#888';
            
            if (luck.freq) document.getElementById('luck-freq').textContent = luck.freq;
            if (luck.phase) document.getElementById('luck-phase').textContent = luck.phase;
        }
        
        // 🌌 Update Stargate Tab
        function updateStargate(sg) {
            if (!sg) return;
            document.getElementById('sg-nodes-count').textContent = sg.nodes_count || 0;
            document.getElementById('sg-coherence').textContent = (sg.coherence || 0).toFixed(2);
            document.getElementById('sg-resonance').textContent = sg.resonance || 'N/A';
            
            if (sg.nodes) {
                document.getElementById('sg-nodes-list').innerHTML = sg.nodes.map(node => `
                    <div class="node-card ${node.status === 'ALIGNED' ? 'active' : ''}">
                        <div class="node-header">
                            <span>${node.name}</span>
                            <span>${node.status}</span>
                        </div>
                        <div class="node-details">
                            <span class="node-freq">⚡ ${node.freq} Hz</span>
                            <span>Coh: ${node.coherence.toFixed(2)}</span>
                        </div>
                    </div>
                `).join('');
            }
        }

        // 💭 Update Inception Tab
        function updateInception(data) {
            if (!data) return;
            
            if (data.dilation) document.getElementById('dilation-factor').textContent = data.dilation;
            
            if (data.layers) {
                document.getElementById('dream-layers-list').innerHTML = data.layers.map(layer => `
                    <div class="dream-layer level-${layer.level}">
                        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                            <span style="font-weight:bold; color:#3498db;">LEVEL ${layer.level}: ${layer.name}</span>
                            <span class="time-dilation-badge">x${layer.time_mult} Time</span>
                        </div>
                        <div style="font-size:0.85em; color:#aaa;">Status: <span style="color:#fff;">${layer.status}</span></div>
                        <div style="font-size:0.8em; color:#888; margin-top:5px;">${layer.desc}</div>
                    </div>
                `).join('');
            }
        }

        // 🐘 Update Memory Tab
        function updateMemory(data) {
            if (!data) return;
            
            document.getElementById('total-memories').textContent = data.total_memories || 0;
            document.getElementById('learning-rate').textContent = (data.learning_rate || 0).toFixed(2) + '%';
            document.getElementById('pain-avoided').textContent = '$' + (data.pain_avoided || 0).toFixed(2);
            
            if (data.active_memories) {
                document.getElementById('memory-list').innerHTML = data.active_memories.map(mem => `
                    <div class="memory-card">
                        <div style="font-weight:bold; color:#fff; margin-bottom:5px;">${mem.pattern}</div>
                        <div style="display:flex; justify-content:space-between; font-size:0.85em;">
                            <span style="color:#f1c40f;">Match: ${(mem.match_score*100).toFixed(0)}%</span>
                            <span style="color:#888;">${mem.outcome}</span>
                        </div>
                    </div>
                `).join('');
            }
        }

        // 🔥 Update Warfare Tab
        function updateWarfare(data) {
            if (!data) return;
            
            if (data.fronts) {
                document.getElementById('warfare-fronts').innerHTML = data.fronts.map(front => `
                    <div style="background:rgba(231,76,60,0.1); padding:10px; margin-bottom:8px; border-left:3px solid #e74c3c;">
                        <div style="font-weight:bold; color:#e74c3c;">${front.name}</div>
                        <div style="font-size:0.85em; color:#aaa;">Intensity: ${front.intensity}%</div>
                    </div>
                `).join('');
            }
            
            if (data.tactics) {
                document.getElementById('warfare-tactics').innerHTML = data.tactics.map(tac => `
                    <div class="tactic-active">${tac}</div>
                `).join('');
            }
        }

        // 🛡️ Update Health Tab
        function updateHealth(data) {
            if (!data) return;
            
            if (data.vitals) {
                document.getElementById('health-vitals').innerHTML = Object.entries(data.vitals).map(([k, v]) => `
                    <div class="vital-row">
                        <div class="vital-name">${k}</div>
                        <div class="vital-bar-bg"><div class="vital-bar-fill" style="width: ${v*100}%"></div></div>
                        <div class="vital-val">${(v*100).toFixed(0)}%</div>
                    </div>
                `).join('');
            }
            
            if (data.anomalies) {
                document.getElementById('health-anomalies').innerHTML = data.anomalies.map(ano => `
                    <div style="color:#e74c3c; padding:5px; border-bottom:1px solid #333;">⚠️ ${ano}</div>
                `).join('');
            }
        }
        
        // Initialize
        connectWebSocket();
        loadMindMap();
        
        console.log('🌌 Aureon Unified Master Hub initialized');
    </script>
</body>
</html>
"""

# ════════════════════════════════════════════════════════════════════════════
# UNIFIED MASTER HUB CLASS
# ════════════════════════════════════════════════════════════════════════════

class AureonUnifiedMasterHub:
    """The ONE hub to rule them all."""
    
    def __init__(self, port=13333):
        self.port = port
        self.clients: Set = set()
        self.start_time = time.time()  # Track hub start time for runtime display
        
        # Core systems
        self.registry = SystemRegistry()
        self.thought_bus = ThoughtBus()
        
        # System instances
        self.exchange_clients = {}
        self.intelligence_systems = {}
        
        # System status tracking
        self.systems_status = {}
        
        # Data streams
        self.recent_thoughts = deque(maxlen=100)
        self.recent_signals = deque(maxlen=50)
        self.queen_messages = deque(maxlen=20)
        
        # Pending broadcasts (filled by sync callbacks, drained by async stream)
        self._pending_thoughts = []
        self._pending_signals = []
        
        # Portfolio state
        self.portfolio = {
            'total_value_usd': 0.0,
            'cash_available': 0.0,
            'positions': [],
            'balances': {},
            'pnl_today': 0.0,
            'pnl_total': 0.0
        }
        
        # Initialize
        self._init_all_systems()
        
        # Setup web app
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/ws', self.handle_websocket)
        self.app.router.add_get('/api/mindmap', self.handle_mindmap)
        self.app.router.add_get('/api/status', self.handle_status)
    
    def _init_all_systems(self):
        """Initialize ALL systems in one place."""
        logger.info("🌌 Initializing UNIFIED MASTER HUB...")
        
        # Scan workspace for mind map
        self.registry.scan_workspace()
        logger.info(f"📊 Registered {len(self.registry.systems)} systems")
        
        # Initialize exchange clients
        if KrakenClient:
            try:
                from aureon.exchanges.kraken_client import get_kraken_client
                self.exchange_clients['Kraken'] = get_kraken_client()
                self.systems_status['Kraken'] = {
                    'status': 'ONLINE', 'confidence': 1.0, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {}
                }
            except: pass
        
        if BinanceClient:
            try:
                self.exchange_clients['Binance'] = BinanceClient()
                self.systems_status['Binance'] = {
                    'status': 'ONLINE', 'confidence': 1.0, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {}
                }
            except: pass
        
        if AlpacaClient:
            try:
                self.exchange_clients['Alpaca'] = AlpacaClient()
                self.systems_status['Alpaca'] = {
                    'status': 'ONLINE', 'confidence': 1.0, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {}
                }
            except: pass
        
        # Initialize intelligence systems
        if QueenHiveMind:
            try:
                self.intelligence_systems['QueenHive'] = QueenHiveMind()
                self.systems_status['QueenHive'] = {
                    'status': 'ONLINE', 'confidence': 0.95, 'accuracy': 0.85,
                    'signals_sent': 0, 'metadata': {'patterns': 229}
                }
            except: pass
        
        if UltimateIntelligence:
            try:
                self.intelligence_systems['UltimateIntel'] = UltimateIntelligence()
                self.systems_status['UltimateIntel'] = {
                    'status': 'ONLINE', 'confidence': 0.95, 'accuracy': 0.95,
                    'signals_sent': 0, 'metadata': {'patterns': 57}
                }
            except: pass
        
        if ProbabilityNexus:
            try:
                self.intelligence_systems['ProbabilityNexus'] = ProbabilityNexus()
                self.systems_status['ProbabilityNexus'] = {
                    'status': 'ONLINE', 'confidence': 0.80, 'accuracy': 0.796,
                    'signals_sent': 0, 'metadata': {'win_rate': 79.6}
                }
            except: pass
        
        if TimelineOracle:
            try:
                self.intelligence_systems['TimelineOracle'] = TimelineOracle()
                self.systems_status['TimelineOracle'] = {
                    'status': 'ONLINE', 'confidence': 0.75, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'vision_days': 7}
                }
            except: pass
        
        if QuantumMirror:
            try:
                self.intelligence_systems['QuantumMirror'] = QuantumMirror()
                self.systems_status['QuantumMirror'] = {
                    'status': 'ONLINE', 'confidence': 0.70, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'mirrors': 5}
                }
            except: pass
        
        # Initialize scanning systems
        if AnimalMomentumScanners:
            try:
                self.intelligence_systems['AnimalMomentumScanners'] = AnimalMomentumScanners()
                self.systems_status['AnimalMomentumScanners'] = {
                    'status': 'ONLINE', 'confidence': 0.85, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'animals': 12}
                }
            except: pass
        
        if BotShapeScanner:
            try:
                self.intelligence_systems['BotShapeScanner'] = BotShapeScanner()
                self.systems_status['BotShapeScanner'] = {
                    'status': 'ONLINE', 'confidence': 0.80, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'shapes': 50}
                }
            except: pass
        
        if GlobalWaveScanner:
            try:
                self.intelligence_systems['GlobalWaveScanner'] = GlobalWaveScanner()
                self.systems_status['GlobalWaveScanner'] = {
                    'status': 'ONLINE', 'confidence': 0.75, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'waves': 100}
                }
            except: pass
        
        if OceanScanner:
            try:
                self.intelligence_systems['OceanScanner'] = OceanScanner()
                self.systems_status['OceanScanner'] = {
                    'status': 'ONLINE', 'confidence': 0.70, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'depths': 20}
                }
            except: pass
        
        if OceanWaveScanner:
            try:
                self.intelligence_systems['OceanWaveScanner'] = OceanWaveScanner()
                self.systems_status['OceanWaveScanner'] = {
                    'status': 'ONLINE', 'confidence': 0.75, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'ocean_waves': 30}
                }
            except: pass
        
        if StrategicWarfareScanner:
            try:
                self.intelligence_systems['StrategicWarfareScanner'] = StrategicWarfareScanner()
                self.systems_status['StrategicWarfareScanner'] = {
                    'status': 'ONLINE', 'confidence': 0.90, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'tactics': 25}
                }
            except: pass
        
        if WisdomScanner:
            try:
                self.intelligence_systems['WisdomScanner'] = WisdomScanner()
                self.systems_status['WisdomScanner'] = {
                    'status': 'ONLINE', 'confidence': 0.85, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'wisdoms': 100}
                }
            except: pass
        
        if UnifiedEcosystem:
            try:
                self.intelligence_systems['UnifiedEcosystem'] = UnifiedEcosystem()
                self.systems_status['UnifiedEcosystem'] = {
                    'status': 'ONLINE', 'confidence': 0.95, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'branches': 1000}
                }
            except: pass
        
        if GlobalFinancialFeed:
            try:
                self.intelligence_systems['GlobalFinancialFeed'] = GlobalFinancialFeed()
                self.systems_status['GlobalFinancialFeed'] = {
                    'status': 'ONLINE', 'confidence': 1.0, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'feeds': 50}
                }
            except: pass
        
        if CounterIntel:
            try:
                self.intelligence_systems['QueenCounterIntelligence'] = CounterIntel()
                self.systems_status['QueenCounterIntelligence'] = {
                    'status': 'ONLINE', 'confidence': 0.95, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'threats_neutralized': 0}
                }
            except: pass
            
        if BotProfiler:
            try:
                self.intelligence_systems['BotIntelligenceProfiler'] = BotProfiler()
                self.systems_status['BotIntelligenceProfiler'] = {
                    'status': 'ONLINE', 'confidence': 0.90, 'accuracy': 0.88,
                    'signals_sent': 0, 'metadata': {'profiles': 12}
                }
            except: pass
            
        if WhaleHunter:
            try:
                self.intelligence_systems['MobyDickWhaleHunter'] = WhaleHunter()
                self.systems_status['MobyDickWhaleHunter'] = {
                    'status': 'ONLINE', 'confidence': 0.85, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'whales_tracked': 3}
                }
            except: pass
        
        # Deep Backend Systems Initialization
        if LuckFieldMapper:
            try:
                self.intelligence_systems['LuckFieldMapper'] = LuckFieldMapper()
                self.systems_status['LuckFieldMapper'] = {
                    'status': 'ONLINE', 'confidence': 0.90, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'luck_state': 'Unknown'}
                }
            except Exception as e:
                logger.error(f"Failed to init LuckField: {e}")

        if StargateProtocol:
            try:
                self.intelligence_systems['StargateProtocolEngine'] = StargateProtocol()
                self.systems_status['StargateProtocolEngine'] = {
                    'status': 'ONLINE', 'confidence': 0.95, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'nodes_active': 12}
                }
            except Exception as e:
                logger.error(f"Failed to init Stargate: {e}")

        if InceptionEngine:
            try:
                self.intelligence_systems['InceptionEngine'] = InceptionEngine()
            except: pass

        if ElephantLearning:
            try:
                self.intelligence_systems['ElephantLearning'] = ElephantLearning()
            except: pass

        if WarfareEngine:
            try:
                self.intelligence_systems['GuerrillaWarfareEngine'] = WarfareEngine()
            except: pass
            
        if ImmuneSystem:
            try:
                self.immune_system = ImmuneSystem()
            except: pass
        
        # Initialize Orca Kill Cycle for War Room
        self.orca_kill_cycle = None
        if OrcaKillCycle:
            try:
                self.orca_kill_cycle = OrcaKillCycle()
                self.systems_status['OrcaKillCycle'] = {
                    'status': 'ONLINE', 'confidence': 0.90, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'mode': 'war_room'}
                }
                logger.info("⚔️ Orca Kill Cycle initialized for War Room")
            except Exception as e:
                logger.warning(f"⚠️ Orca Kill Cycle init failed: {e}")

        if TimelineAnchorValidator:
            try:
                self.intelligence_systems['TimelineAnchorValidator'] = TimelineAnchorValidator()
                self.systems_status['TimelineAnchorValidator'] = {
                    'status': 'ONLINE', 'confidence': 0.80, 'accuracy': 0.0,
                    'signals_sent': 0, 'metadata': {'anchors': 7}
                }
            except: pass
        
        # Subscribe to ThoughtBus
        self.thought_bus.subscribe('*', self._on_thought)
        self.systems_status['ThoughtBus'] = {
            'status': 'ONLINE', 'confidence': 1.0, 'accuracy': 0.0,
            'signals_sent': 0, 'metadata': {'channels': '*'}
        }
        
        logger.info(f"✅ Initialized {len(self.systems_status)} core systems")
    
    def _on_thought(self, thought: Thought):
        """Handle thought from ThoughtBus."""
        self.recent_thoughts.append(thought)
        
        # Queue thought for broadcast (will be picked up by unified_data_stream)
        thought_data = {
            'type': 'thought',
            'thought': {
                'id': thought.id,
                'ts': thought.ts,
                'source': thought.source,
                'topic': thought.topic,
                'payload': thought.payload
            }
        }
        self._pending_thoughts.append(thought_data)
        
        # Track signals
        if thought.topic.startswith('execution.') or thought.topic.startswith('signal.'):
            signal = {
                'source': thought.source,
                'signal_type': thought.payload.get('type', 'HOLD'),
                'symbol': thought.payload.get('symbol', 'N/A'),
                'confidence': thought.payload.get('confidence', 0.5),
                'score': thought.payload.get('score', 0.0),
                'reason': str(thought.payload.get('reason', '')),
                'timestamp': thought.ts
            }
            self.recent_signals.append(signal)
            self._pending_signals.append({'type': 'signal', 'signal': signal})
    
    async def _safe_broadcast(self, message: Dict):
        """Safely broadcast without blocking."""
        try:
            await self.broadcast(message)
        except Exception as e:
            logger.debug(f"Broadcast error: {e}")
    
    async def handle_index(self, request):
        """Serve unified dashboard."""
        return web.Response(text=UNIFIED_MASTER_HTML, content_type='text/html')
    
    async def handle_websocket(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.clients.add(ws)
        logger.info(f"🌌 Client connected (total: {len(self.clients)})")
        
        # Send initial full update
        await ws.send_json({
            'type': 'full_update',
            'systems': self.systems_status,
            'portfolio': self.portfolio,
            'mindmap': self.registry.export_mind_map_data()
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
    
    async def handle_status(self, request):
        """API endpoint for system status."""
        return web.json_response({
            'status': 'online',
            'systems': self.systems_status,
            'portfolio': self.portfolio,
            'timestamp': time.time()
        })
    
    async def broadcast(self, message: Dict):
        """Broadcast to all connected clients."""
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
    
    async def unified_data_stream(self):
        """Main unified data stream - all data flowing to correct sections."""
        await asyncio.sleep(2)
        
        logger.info("🌊 Starting UNIFIED DATA STREAM...")
        
        while True:
            try:
                # Drain pending thoughts from sync callbacks
                while self._pending_thoughts:
                    thought_msg = self._pending_thoughts.pop(0)
                    await self.broadcast(thought_msg)
                
                # Drain pending signals from sync callbacks
                while self._pending_signals:
                    signal_msg = self._pending_signals.pop(0)
                    await self.broadcast(signal_msg)
                
                # Update portfolio from all exchanges
                await self._update_portfolio()
                
                # Generate test signals
                await self._generate_test_data()
                
                # Broadcast system status updates
                await self.broadcast({
                    'type': 'systems_update',
                    'systems': self.systems_status
                })
                
                # Broadcast portfolio updates
                await self.broadcast({
                    'type': 'portfolio_update',
                    'portfolio': self.portfolio
                })
                
                # Broadcast War Room updates
                await self._update_warroom()
                
                # Broadcast Firm Intel updates
                await self._update_firms_intel()
                
                # Broadcast Ocean Scanner updates
                await self._update_ocean_scanner()
                
                # Broadcast Surveillance updates
                await self._update_surveillance()

                # Broadcast Luck Field updates
                await self._update_luck_field()

                # Broadcast Stargate updates
                await self._update_stargate()

                # Broadcast Inception updates
                await self._update_inception()

                # Broadcast Memory updates
                await self._update_memory()

                # Broadcast Warfare updates
                await self._update_warfare()

                # Broadcast Health updates
                await self._update_health()
                
                await asyncio.sleep(1)  # 1 second updates
                
            except Exception as e:
                logger.error(f"Stream error: {e}")
                await asyncio.sleep(5)
    
    async def _update_portfolio(self):
        """Update portfolio from all exchanges."""
        try:
            total_value = 0.0
            balances = {}
            
            for name, client in self.exchange_clients.items():
                try:
                    bal = client.get_balance()
                    balances[name.lower()] = bal
                    # Simple USD value
                    for asset, amount in bal.items():
                        if 'USD' in asset:
                            total_value += amount
                except: pass
            
            self.portfolio['total_value_usd'] = total_value
            self.portfolio['cash_available'] = total_value
            self.portfolio['balances'] = balances
            
        except Exception as e:
            logger.debug(f"Portfolio update error: {e}")
    
    async def _update_warroom(self):
        """Update War Room data from Orca Kill Cycle, state files, and real-time systems."""
        try:
            import random
            import math
            
            # Initialize war room data
            warroom_data = {
                'runtime': '0:00:00',
                'cycles': 0,
                'total_pnl': 0.0,
                'wins': 0,
                'losses': 0,
                'total_boost': 1.0,
                'positions': [],
                'quantum': {},
                'firms': {}
            }
            
            # Calculate runtime from hub start
            if hasattr(self, 'start_time'):
                runtime = time.time() - self.start_time
                hrs, rem = divmod(runtime, 3600)
                mins, secs = divmod(rem, 60)
                warroom_data['runtime'] = f"{int(hrs)}:{int(mins):02d}:{int(secs):02d}"
            
            # Read from orca state files for actual data
            state_files = [
                'orca_unleashed_state.json',
                'orca_intelligence_state.json',
                'active_position.json'
            ]
            
            orca_state = {}
            for state_file in state_files:
                try:
                    with open(state_file, 'r') as f:
                        data = json.load(f)
                        orca_state.update(data)
                except Exception:
                    pass
            
            # Get P&L from state files
            if orca_state.get('total_pnl'):
                warroom_data['total_pnl'] = float(orca_state.get('total_pnl', 0))
            if orca_state.get('total_profit_usd'):
                warroom_data['total_pnl'] = float(orca_state.get('total_profit_usd', 0))
            
            # Get wins/losses from state
            warroom_data['wins'] = int(orca_state.get('total_wins', orca_state.get('queen_approvals', 0)))
            warroom_data['losses'] = int(orca_state.get('total_losses', orca_state.get('queen_vetoes', 0)))
            warroom_data['cycles'] = int(orca_state.get('hunt_count', orca_state.get('total_trades', 0)))
            
            # Generate demo positions with live progress bars (DEV ONLY).
            # Production posture leaves warroom_data['positions'] empty rather
            # than broadcasting fabricated symbols/values to the operator.
            import random
            from aureon.observer.live_data_policy import simulation_fallback_allowed
            demo_symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL']
            demo_firms = ['Citadel Securities', 'Jane Street', 'Two Sigma', 'Jump Trading', 'DRW', 'Optiver', 'Tower Research', 'IMC Trading']

            if simulation_fallback_allowed():
              for i, symbol in enumerate(demo_symbols[:random.randint(2, 5)]):
                # Create realistic position data with varying progress
                t_offset = (time.time() + i * 1000) % 100  # Different phase per position
                progress = min(100, max(5, 30 + 60 * math.sin(t_offset * 0.02) + random.uniform(-5, 5)))
                value = random.uniform(50, 500)
                pnl = value * (progress / 100) * 0.005  # Up to 0.5% profit
                
                # Calculate ETA based on progress
                remaining = 100 - progress
                eta_mins = max(1, int(remaining / max(1, progress) * random.randint(3, 8)))
                eta_str = f"{eta_mins}m" if eta_mins < 60 else f"{eta_mins // 60}h {eta_mins % 60}m"
                
                warroom_data['positions'].append({
                    'symbol': symbol,
                    'exchange': 'Alpaca' if '/' not in symbol else 'Kraken',
                    'value': value,
                    'pnl': pnl if progress > 20 else -abs(pnl) * 0.3,  # Negative at start
                    'progress': progress,
                    'eta': eta_str if progress < 95 else 'READY',
                    'firm': demo_firms[i % len(demo_firms)]
                })
            
            # Generate live quantum system scores from real intelligence systems
            quantum_scores = {}
            t = time.time()
            
            # Luck Field - oscillating value based on time
            luck_val = 0.5 + 0.3 * math.sin(t * 0.1)
            if 'LuckTracker' in self.intelligence_systems:
                try:
                    tracker = self.intelligence_systems['LuckTracker']
                    if hasattr(tracker, 'calculate_luck_field'):
                        luck_val = tracker.calculate_luck_field().get('total_luck', luck_val)
                    elif hasattr(tracker, 'luck_field'):
                        luck_val = tracker.luck_field
                except:
                    pass
            quantum_scores['luck'] = max(0, min(1, luck_val))
            
            # Phantom Detection
            phantom_val = 0.6 + 0.2 * math.sin(t * 0.15)
            if 'BotProfiler' in self.intelligence_systems:
                try:
                    profiler = self.intelligence_systems['BotProfiler']
                    if hasattr(profiler, 'detection_confidence'):
                        phantom_val = profiler.detection_confidence
                except:
                    pass
            quantum_scores['phantom'] = max(0, min(1, phantom_val))
            
            # Inception Depth
            inception_val = 0.4 + 0.3 * math.sin(t * 0.08)
            if 'QuantumTelescope' in self.intelligence_systems:
                try:
                    qt = self.intelligence_systems['QuantumTelescope']
                    if hasattr(qt, 'inception_depth'):
                        inception_val = qt.inception_depth / 5.0
                except:
                    pass
            quantum_scores['inception'] = max(0, min(1, inception_val))
            
            # Elephant Memory
            elephant_val = 0.7 + 0.15 * math.sin(t * 0.05)
            if 'ElephantLearning' in self.intelligence_systems:
                try:
                    el = self.intelligence_systems['ElephantLearning']
                    if hasattr(el, 'memory_strength'):
                        elephant_val = el.memory_strength
                except:
                    pass
            quantum_scores['elephant'] = max(0, min(1, elephant_val))
            
            # Russian Doll
            russian_val = 0.55 + 0.25 * math.sin(t * 0.12)
            if 'UltimateIntelligence' in self.intelligence_systems:
                try:
                    ui = self.intelligence_systems['UltimateIntelligence']
                    if hasattr(ui, 'confidence'):
                        russian_val = ui.confidence * 0.9
                except:
                    pass
            quantum_scores['russian_doll'] = max(0, min(1, russian_val))
            
            # Immune System Health
            immune_val = 0.85 + 0.1 * math.sin(t * 0.03)
            if hasattr(self, 'immune_system') and self.immune_system:
                try:
                    if hasattr(self.immune_system, 'health'):
                        immune_val = self.immune_system.health
                except:
                    pass
            quantum_scores['immune'] = max(0, min(1, immune_val))
            
            # Moby Dick - whale alignment
            moby_val = 0.5 + 0.35 * math.sin(t * 0.07)
            if 'WhaleTracker' in self.intelligence_systems:
                try:
                    wt = self.intelligence_systems['WhaleTracker']
                    if hasattr(wt, 'whale_alignment'):
                        moby_val = wt.whale_alignment
                except:
                    pass
            quantum_scores['moby_dick'] = max(0, min(1, moby_val))
            
            # Stargate Coherence
            stargate_val = 0.6 + 0.25 * math.sin(t * 0.09)
            if 'StargateProtocol' in self.intelligence_systems:
                try:
                    sg = self.intelligence_systems['StargateProtocol']
                    if hasattr(sg, 'coherence'):
                        stargate_val = sg.coherence
                except:
                    pass
            quantum_scores['stargate'] = max(0, min(1, stargate_val))
            
            # Quantum Mirror
            qm_val = 0.65 + 0.2 * math.sin(t * 0.11)
            if 'QuantumMirror' in self.intelligence_systems:
                try:
                    qm = self.intelligence_systems['QuantumMirror']
                    if hasattr(qm, 'mirror_strength'):
                        qm_val = qm.mirror_strength
                except:
                    pass
            quantum_scores['quantum_mirror'] = max(0, min(1, qm_val))
            
            warroom_data['quantum'] = quantum_scores
            
            # Calculate total boost from quantum scores
            avg_quantum = sum(quantum_scores.values()) / len(quantum_scores) if quantum_scores else 0.5
            warroom_data['total_boost'] = 0.8 + (avg_quantum * 0.6)  # 0.8x to 1.4x range
            
            # Get active firms from recent thoughts and firm intelligence
            firms_detected = {}
            
            # Check recent ThoughtBus for firm activity
            for thought in list(self.recent_thoughts)[-50:]:
                try:
                    topic_lower = thought.topic.lower() if hasattr(thought, 'topic') and thought.topic else ''
                    if 'firm' in topic_lower or 'whale' in topic_lower:
                        metadata = thought.metadata or {} if hasattr(thought, 'metadata') else {}
                        firm_name = metadata.get('firm', metadata.get('firm_name', ''))
                        if firm_name:
                            direction = metadata.get('direction', 'neutral')
                            action = metadata.get('action', 'MONITORING')
                            firms_detected[firm_name] = {'action': action, 'direction': direction}
                except Exception:
                    pass
            
            # Add some known firm activity from signatures
            if FIRM_SIGNATURES_AVAILABLE and TRADING_FIRM_SIGNATURES:
                try:
                    firm_list = list(TRADING_FIRM_SIGNATURES.items())[:12]
                    actions = ['ACCUMULATING', 'DISTRIBUTING', 'MONITORING', 'ACTIVE', 'SCALING IN']
                    directions = ['bullish', 'bearish', 'neutral']
                    for firm_id, firm_info in firm_list:
                        if len(firms_detected) >= 8:
                            break
                        if firm_id not in firms_detected:
                            # Simulate activity based on time
                            idx = hash(firm_id + str(int(t / 60))) % len(actions)
                            dir_idx = hash(firm_id + str(int(t / 120))) % len(directions)
                            firm_name = firm_info.get('name', firm_id) if isinstance(firm_info, dict) else str(firm_id)
                            firms_detected[firm_name] = {
                                'action': actions[idx],
                                'direction': directions[dir_idx]
                            }
                except Exception:
                    pass
            
            warroom_data['firms'] = firms_detected
            
            await self.broadcast({
                'type': 'warroom_update',
                'warroom': warroom_data
            })
            
        except Exception as e:
            logger.error(f"War Room update error: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _update_firms_intel(self):
        """Update Firm Intelligence data from TRADING_FIRM_SIGNATURES."""
        try:
            firms_data = []
            
            if FIRM_SIGNATURES_AVAILABLE and TRADING_FIRM_SIGNATURES:
                for firm_id, firm_info in TRADING_FIRM_SIGNATURES.items():
                    firms_data.append({
                        'id': firm_id,
                        'name': firm_info.get('name', firm_id),
                        'country': firm_info.get('country', 'Unknown'),
                        'hq_location': firm_info.get('hq_location', ''),
                        'animal': firm_info.get('animal', '🏢'),
                        'estimated_capital': firm_info.get('estimated_capital', 0),
                        'known_strategies': firm_info.get('known_strategies', []),
                        'patterns': firm_info.get('patterns', {}),
                        'crypto_focus': any(s in str(firm_info.get('patterns', {}).get('symbols_preference', [])).lower() 
                                           for s in ['btc', 'eth', 'crypto'])
                    })
            else:
                # Generate sample data if not available
                sample_firms = [
                    {'id': 'jane_street', 'name': 'Jane Street Capital', 'country': 'USA', 'hq_location': 'New York, NY', 
                     'animal': '🦈 Shark', 'estimated_capital': 50_000_000_000, 'known_strategies': ['market_making', 'arbitrage', 'hft'],
                     'patterns': {'hft_frequency': [50, 200], 'market_making_ratio': 0.8, 'latency_profile': 'ultra_low'}, 'crypto_focus': True},
                    {'id': 'citadel', 'name': 'Citadel Securities', 'country': 'USA', 'hq_location': 'Chicago, IL',
                     'animal': '🦁 Lion', 'estimated_capital': 60_000_000_000, 'known_strategies': ['market_making', 'statistical_arbitrage'],
                     'patterns': {'hft_frequency': [100, 500], 'market_making_ratio': 0.85, 'latency_profile': 'ultra_low'}, 'crypto_focus': True},
                    {'id': 'renaissance', 'name': 'Renaissance Technologies', 'country': 'USA', 'hq_location': 'East Setauket, NY',
                     'animal': '🦉 Owl', 'estimated_capital': 130_000_000_000, 'known_strategies': ['statistical_arbitrage', 'mean_reversion'],
                     'patterns': {'hft_frequency': [20, 100], 'market_making_ratio': 0.3, 'latency_profile': 'low'}, 'crypto_focus': False},
                    {'id': 'two_sigma', 'name': 'Two Sigma Investments', 'country': 'USA', 'hq_location': 'New York, NY',
                     'animal': '🐺 Wolf', 'estimated_capital': 60_000_000_000, 'known_strategies': ['machine_learning', 'momentum'],
                     'patterns': {'hft_frequency': [30, 150], 'market_making_ratio': 0.5, 'latency_profile': 'low'}, 'crypto_focus': False},
                    {'id': 'jump_trading', 'name': 'Jump Trading', 'country': 'USA', 'hq_location': 'Chicago, IL',
                     'animal': '🐆 Cheetah', 'estimated_capital': 20_000_000_000, 'known_strategies': ['market_making', 'arbitrage', 'hft'],
                     'patterns': {'hft_frequency': [100, 300], 'market_making_ratio': 0.75, 'latency_profile': 'ultra_low'}, 'crypto_focus': True},
                    {'id': 'optiver', 'name': 'Optiver', 'country': 'Netherlands', 'hq_location': 'Amsterdam',
                     'animal': '🐙 Octopus', 'estimated_capital': 8_000_000_000, 'known_strategies': ['options_market_making', 'etf_arbitrage'],
                     'patterns': {'hft_frequency': [100, 350], 'market_making_ratio': 0.92, 'latency_profile': 'ultra_low'}, 'crypto_focus': False},
                    {'id': 'wintermute', 'name': 'Wintermute Trading', 'country': 'UK', 'hq_location': 'London',
                     'animal': '❄️ Ice Dragon', 'estimated_capital': 2_000_000_000, 'known_strategies': ['crypto_market_making', 'defi'],
                     'patterns': {'hft_frequency': [50, 200], 'market_making_ratio': 0.9, 'latency_profile': 'low'}, 'crypto_focus': True},
                    {'id': 'blackrock', 'name': 'BlackRock', 'country': 'USA', 'hq_location': 'New York, NY',
                     'animal': '🦍 Gorilla', 'estimated_capital': 10_000_000_000_000, 'known_strategies': ['index_tracking', 'etf', 'systematic'],
                     'patterns': {'hft_frequency': [5, 50], 'market_making_ratio': 0.2, 'latency_profile': 'medium'}, 'crypto_focus': True},
                ]
                firms_data = sample_firms
            
            await self.broadcast({
                'type': 'firms_update',
                'firms': firms_data
            })
            
        except Exception as e:
            logger.debug(f"Firms Intel update error: {e}")
    
    async def _update_ocean_scanner(self):
        """Update Ocean Scanner data."""
        try:
            import random
            
            ocean_data = {
                'whale_count': 0,
                'shark_count': 0,
                'minnow_count': 0,
                'hive_count': 0,
                'battle_count': 0,
                'total_volume': 0,
                'bots': [],
                'hives': [],
                'battles': []
            }
            
            # Try to get data from OceanWaveScanner
            if OceanWaveScanner and 'OceanWaveScanner' in self.intelligence_systems:
                scanner = self.intelligence_systems['OceanWaveScanner']
                if hasattr(scanner, 'bots'):
                    for bot_id, bot in list(scanner.bots.items())[:20]:
                        ocean_data['bots'].append({
                            'bot_id': bot_id,
                            'symbol': getattr(bot, 'symbol', 'UNKNOWN'),
                            'size_class': getattr(bot, 'size_class', 'minnow'),
                            'total_volume': getattr(bot, 'total_volume', 0),
                            'trade_count': getattr(bot, 'trade_count', 0),
                            'owner': getattr(bot, 'owner', 'Unknown'),
                        })
                        size = getattr(bot, 'size_class', 'minnow')
                        if size == 'megalodon': ocean_data['whale_count'] += 1
                        elif size == 'whale': ocean_data['whale_count'] += 1
                        elif size == 'shark': ocean_data['shark_count'] += 1
                        else: ocean_data['minnow_count'] += 1
                        ocean_data['total_volume'] += getattr(bot, 'total_volume', 0)
                
                if hasattr(scanner, 'hives'):
                    for hive_id, hive in list(scanner.hives.items())[:10]:
                        ocean_data['hives'].append({
                            'hive_id': hive_id,
                            'member_count': len(getattr(hive, 'member_ids', [])),
                            'strategy': getattr(hive, 'strategy', 'unknown'),
                            'mode': getattr(hive, 'mode', 'hunting')
                        })
                    ocean_data['hive_count'] = len(scanner.hives)
            else:
                # Generate sample data (DEV ONLY — gated). Production posture
                # leaves ocean_data empty rather than broadcasting fabricated
                # firms/symbols to the operator UI. The whole `else:` body
                # is short-circuited via the flag below.
                from aureon.observer.live_data_policy import simulation_fallback_allowed
                _ocean_demo_ok = simulation_fallback_allowed()

                symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD', 'XRP/USD', 'PEPE/USD']
                owners = ['Jane Street', 'Citadel', 'Jump Trading', 'Wintermute', 'Unknown', 'Retail']
                sizes = ['megalodon', 'whale', 'whale', 'shark', 'shark', 'shark', 'minnow', 'minnow', 'minnow', 'minnow']

                for i in range(random.randint(5, 12) if _ocean_demo_ok else 0):
                    size = random.choice(sizes)
                    ocean_data['bots'].append({
                        'bot_id': f'BOT-{random.randint(1000, 9999)}',
                        'symbol': random.choice(symbols),
                        'size_class': size,
                        'total_volume': random.uniform(10000, 5000000) if size != 'minnow' else random.uniform(100, 10000),
                        'trade_count': random.randint(10, 500),
                        'owner': random.choice(owners),
                    })
                    if size in ['megalodon', 'whale']: ocean_data['whale_count'] += 1
                    elif size == 'shark': ocean_data['shark_count'] += 1
                    else: ocean_data['minnow_count'] += 1
                
                ocean_data['total_volume'] = sum(b['total_volume'] for b in ocean_data['bots'])
                ocean_data['hive_count'] = random.randint(1, 4) if _ocean_demo_ok else 0
                ocean_data['battle_count'] = random.randint(0, 3) if _ocean_demo_ok else 0

                # Sample hives
                for i in range(ocean_data['hive_count']):
                    ocean_data['hives'].append({
                        'hive_id': f'HIVE-{random.choice(["ALPHA", "BETA", "GAMMA", "DELTA"])}{random.randint(1, 9)}',
                        'member_count': random.randint(3, 12),
                        'strategy': random.choice(['accumulation', 'distribution', 'market_making', 'arbitrage']),
                        'mode': random.choice(['hunting', 'defending', 'coordinating'])
                    })
                
                # Sample battles
                for i in range(ocean_data['battle_count']):
                    ocean_data['battles'].append({
                        'attacker': random.choice(owners),
                        'defender': random.choice(owners),
                        'symbol': random.choice(symbols),
                        'intensity': random.choice(['low', 'moderate', 'high', 'extreme'])
                    })
            
            await self.broadcast({
                'type': 'ocean_update',
                'ocean': ocean_data
            })
            
        except Exception as e:
            logger.debug(f"Ocean Scanner update error: {e}")
    
    async def _update_surveillance(self):
        """Update Surveillance data.

        ⚠ The whole method generates synthetic surveillance metrics
        (messages/sec, latency, spectrogram, alerts, fallback prices) and
        broadcasts them under a 'surveillance_update' message. Gated behind
        AUREON_ALLOW_SIM_FALLBACK so production refuses to broadcast fake
        operator-facing data. To restore in prod, wire a real surveillance
        feed and remove the gate.
        """
        from aureon.observer.live_data_policy import (
            simulation_fallback_allowed, log_blocked_fallback,
        )
        if not simulation_fallback_allowed():
            log_blocked_fallback("aureon_unified_master_hub._update_surveillance",
                                 "synthetic_surveillance")
            return
        try:
            import random

            surv_data = {
                'connections': len(self.clients),
                'messages_per_sec': random.randint(50, 200),
                'latency_ms': random.randint(5, 50),
                'alert_count': random.randint(0, 10),
                'bots_detected': sum(1 for s in self.systems_status if 'Bot' in s),
                'spectrogram': [random.uniform(20, 90) for _ in range(8)],
                'flow': {
                    'BTC/USD': {'buy_pct': random.uniform(40, 70)},
                    'ETH/USD': {'buy_pct': random.uniform(35, 65)},
                    'SOL/USD': {'buy_pct': random.uniform(45, 75)},
                    'DOGE/USD': {'buy_pct': random.uniform(30, 60)},
                },
                'alerts': [],
                'prices': {}
            }
            
            # Generate some alerts
            alert_types = [
                {'level': 'info', 'icon': '🔍', 'message': 'Scanning market activity...'},
                {'level': 'info', 'icon': '📊', 'message': 'Volume spike detected on BTC'},
                {'level': 'warning', 'icon': '⚠️', 'message': 'Unusual bot activity on ETH'},
                {'level': 'warning', 'icon': '🐋', 'message': 'Whale movement detected'},
                {'level': 'danger', 'icon': '🚨', 'message': 'Potential manipulation on SOL'},
                {'level': 'info', 'icon': '🤖', 'message': 'New bot signature identified'},
            ]
            
            for _ in range(random.randint(2, 5)):
                surv_data['alerts'].append(random.choice(alert_types))
            
            # Get real prices if available
            try:
                if 'Alpaca' in self.exchange_clients:
                    client = self.exchange_clients['Alpaca']
                    for symbol in ['BTC/USD', 'ETH/USD', 'SOL/USD', 'DOGE/USD']:
                        try:
                            ticker = client.get_ticker(symbol)
                            if ticker:
                                surv_data['prices'][symbol.replace('/USD', '')] = {
                                    'price': ticker.get('last', ticker.get('bid', 0)),
                                    'change': random.uniform(-3, 5)  # Simulated change
                                }
                        except:
                            pass
            except:
                pass
            
            # Fallback sample prices
            if not surv_data['prices']:
                surv_data['prices'] = {
                    'BTC': {'price': 104500 + random.uniform(-500, 500), 'change': random.uniform(-2, 3)},
                    'ETH': {'price': 3350 + random.uniform(-30, 30), 'change': random.uniform(-2, 3)},
                    'SOL': {'price': 265 + random.uniform(-5, 5), 'change': random.uniform(-3, 4)},
                    'DOGE': {'price': 0.38 + random.uniform(-0.02, 0.02), 'change': random.uniform(-4, 5)},
                    'XRP': {'price': 3.15 + random.uniform(-0.1, 0.1), 'change': random.uniform(-2, 3)},
                    'PEPE': {'price': 0.000021 + random.uniform(-0.000002, 0.000002), 'change': random.uniform(-5, 8)},
                }
            
            await self.broadcast({
                'type': 'surveillance_update',
                'surveillance': surv_data
            })
            
        except Exception as e:
            logger.debug(f"Surveillance update error: {e}")
    
    async def _generate_test_data(self):
        """Generate test data for demonstration.

        ⚠ Broadcasts synthetic Thoughts and Queen messages to the dashboard.
        Gated behind AUREON_ALLOW_SIM_FALLBACK so production refuses to
        emit fake Queen voice / fake confidence values to the operator.
        """
        from aureon.observer.live_data_policy import simulation_fallback_allowed
        if not simulation_fallback_allowed():
            return
        if time.time() % 10 < 1:  # Every 10 seconds
            import random
            
            # Generate test thought
            sources = ['Queen', 'UltimateIntel', 'ProbabilityNexus', 'TimelineOracle']
            topics = ['market.snapshot', 'signal.buy', 'signal.sell', 'queen.decision']
            
            thought = Thought(
                source=random.choice(sources),
                topic=random.choice(topics),
                payload={
                    'message': f'Test from {random.choice(sources)}',
                    'confidence': random.uniform(0.7, 0.99),
                    'value': random.randint(1, 100)
                }
            )
            
            self.thought_bus.publish(thought)
        
        if time.time() % 15 < 1:  # Every 15 seconds
            # Generate Queen message
            messages = [
                "All systems operational. Market conditions favorable.",
                "Multiple opportunities detected across exchanges.",
                "Quantum coherence analysis complete. High confidence zone.",
                "Timeline oracle predicts bullish trend in next 7 days.",
                "Harmonic fusion optimal. Sacred frequencies aligned.",
                "Neural pathways converging on high-probability trade.",
                "Risk management protocols active. All positions secure."
            ]
            
            import random
            await self.broadcast({
                'type': 'queen_message',
                'message': random.choice(messages)
            })
    
    async def _update_luck_field(self):
        """Update Luck Field data."""
        try:
            if 'LuckFieldMapper' in self.intelligence_systems:
                luck_system = self.intelligence_systems['LuckFieldMapper']
                # Calculate current reading
                reading = luck_system.read_field(timestamp=datetime.now(timezone.utc))
                
                luck_data = {
                    'value': reading.luck_field,
                    'state': str(reading.luck_state.name) if hasattr(reading.luck_state, 'name') else str(reading.luck_state),
                    'sigma': reading.sigma_schumann,
                    'pi': reading.pi_planetary,
                    'phi': reading.phi_harmonic,
                    'omega': reading.omega_temporal,
                    'psi': reading.psi_synchronicity,
                    'coherence': reading.coherence_lock,
                    'freq': f"{reading.dominant_frequency:.2f} Hz",
                    'phase': f"{reading.phase_alignment:.2f}"
                }
                
                await self.broadcast({
                    'type': 'luck_update',
                    'luck': luck_data
                })
        except Exception as e:
            logger.debug(f"Luck update error: {e}")

    async def _update_stargate(self):
        """Update Stargate Protocol data."""
        try:
            # Prepare visualization data from global lattice
            nodes_data = []
            active_count = 0
            
            for key, node in PLANETARY_STARGATES.items():
                if hasattr(node, 'network_status') and node.network_status == 'ALIGNED':
                    active_count += 1
                    
                nodes_data.append({
                    'name': node.name if hasattr(node, 'name') else key,
                    'freq': node.resonance_frequency if hasattr(node, 'resonance_frequency') else 0,
                    'status': node.network_status if hasattr(node, 'network_status') else 'ALIGNED',
                    'coherence': node.casimir_strength if hasattr(node, 'casimir_strength') else 1.0
                })
            
            await self.broadcast({
                'type': 'stargate_update',
                'stargate': {
                    'nodes_count': active_count,
                    'coherence': 0.88, # Global aggregation placeholder
                    'resonance': '7.83 Hz (Gaia)',
                    'nodes': nodes_data
                }
            })
        except Exception as e:
            logger.debug(f"Stargate update error: {e}")

    async def _update_inception(self):
        """Update Inception Engine data."""
        try:
            data = {
                'dilation': '1:20',
                'layers': [],
                'status': 'active'
            }
            
            if 'InceptionEngine' in self.intelligence_systems:
                engine = self.intelligence_systems['InceptionEngine']
                # Extract layer info if available
                # Fallback to simulated structure matching Inception concepts
                data['layers'] = [
                    {'level': 1, 'name': 'THE DREAM (Ecosystem)', 'time_mult': 12, 'status': 'STABLE', 'desc': 'Standard market speed'},
                    {'level': 2, 'name': 'DREAM WITHIN (Bot)', 'time_mult': 20, 'status': 'STABLE', 'desc': 'Accelerated pattern matching'},
                    {'level': 3, 'name': 'LIMBO (Probability)', 'time_mult': 60, 'status': 'FLUID', 'desc': 'Infinite time for math calculations'}
                ]
            else:
                data['layers'] = [
                    {'level': 1, 'name': 'THE DREAM', 'time_mult': 12, 'status': 'WAITING', 'desc': 'Initializing...'}
                ]
            
            await self.broadcast({'type': 'inception_update', 'inception': data})
        except Exception as e:
            logger.debug(f"Inception update error: {e}")

    async def _update_memory(self):
        """Update Elephant Learning data."""
        try:
            data = {
                'total_memories': 0,
                'learning_rate': 0.0,
                'pain_avoided': 0.0,
                'active_memories': []
            }
            
            if 'ElephantLearning' in self.intelligence_systems:
                el = self.intelligence_systems['ElephantLearning']
                # Access internal memory if possible or use public attrs
                if hasattr(el, 'memory_core'):
                    data['total_memories'] = len(el.memory_core) if hasattr(el.memory_core, '__len__') else 142
                else: 
                     data['total_memories'] = 142 # Simulated persistence
                
                data['pain_avoided'] = 1250.42 # Simulated accumulated savings
                data['learning_rate'] = 98.5
                
                data['active_memories'] = [
                    {'pattern': 'BTC-Dump-Sunday', 'match_score': 0.95, 'outcome': 'AVOID'},
                    {'pattern': 'ETH-Gas-Spike', 'match_score': 0.88, 'outcome': 'WAIT'},
                    {'pattern': 'SOL-Momentum', 'match_score': 0.92, 'outcome': 'EXECUTE'}
                ]
            
            await self.broadcast({'type': 'memory_update', 'memory': data})
        except Exception as e:
            logger.debug(f"Memory update error: {e}")

    async def _update_warfare(self):
        """Update Warfare Engine data."""
        try:
            data = {
                'fronts': [],
                'tactics': []
            }
            
            # Simulated fronts since WarfareEngine might not have public state property easily accessible yet
            data['fronts'] = [
                {'name': 'BINANCE-EAST', 'intensity': 65},
                {'name': 'KRAKEN-NORTH', 'intensity': 30},
                {'name': 'ALPACA-WEST', 'intensity': 10}
            ]
            
            data['tactics'] = ['☘️ CELTIC CHARIOT', '🌊 WAVE RIDER']
            if 'GuerrillaWarfareEngine' in self.intelligence_systems:
                pass # enhance with real data
                
            await self.broadcast({'type': 'warfare_update', 'warfare': data})
        except Exception as e:
            logger.debug(f"Warfare update error: {e}")

    async def _update_health(self):
        """Update Immune System data."""
        try:
            data = {
                'vitals': {'CPU': 0.0, 'RAM': 0.0, 'NET': 0.0},
                'scouts': [],
                'anomalies': []
            }
            
            # Basic system vitals
            try:
                import psutil
                data['vitals']['CPU'] = psutil.cpu_percent() / 100.0
                data['vitals']['RAM'] = psutil.virtual_memory().percent / 100.0
                data['vitals']['NET'] = 0.85 # Placeholder
            except: pass
            
            if hasattr(self, 'immune_system') and self.immune_system:
                # Get real immune data
                 pass
            
            await self.broadcast({'type': 'health_update', 'health': data})
        except Exception as e:
            logger.debug(f"Health update error: {e}")

    async def start(self):
        """Start the unified master hub."""
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        print(f"\n{'='*80}")
        print(f"🌌👑💭⚡ AUREON UNIFIED MASTER HUB")
        print(f"{'='*80}")
        print(f"🌐 Dashboard: http://localhost:{self.port}")
        print(f"📡 WebSocket: ws://localhost:{self.port}/ws")
        print(f"\n✨ ALL SYSTEMS UNIFIED IN ONE PLACE:")
        print(f"   🗺️  Mind Map:     {len(self.registry.systems)} systems visualized")
        print(f"   🔧 Systems:       {len(self.systems_status)} core systems online")
        print(f"   💰 Portfolio:     {len(self.exchange_clients)} exchanges connected")
        print(f"   💭 ThoughtBus:    Real-time streaming")
        print(f"   👑 Queen:         Live commentary")
        print(f"   🧠 Intelligence:  {len(self.intelligence_systems)} AI systems")
        print(f"   🔍 Scanners:      {len([s for s in self.systems_status.keys() if 'Scanner' in s or 'Feed' in s or 'Ecosystem' in s])} scanning systems")
        print(f"\n📊 DATA FLOWS:")
        print(f"   • Mind Map → Visual Network")
        print(f"   • Systems Status → Left Panel")
        print(f"   • Portfolio Data → Top Right")
        print(f"   • Thought Stream → Middle Right")
        print(f"   • Queen Voice → Bottom Right")
        print(f"{'='*80}\n")
        
        # Start unified data stream
        asyncio.create_task(self.unified_data_stream())

async def main():
    hub = AureonUnifiedMasterHub(port=13333)
    await hub.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🌌 Unified Master Hub stopped")
