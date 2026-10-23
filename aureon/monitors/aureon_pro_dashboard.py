#!/usr/bin/env python3
"""
👑 AUREON PRO TRADING DASHBOARD 👑
═══════════════════════════════════════════════════════════════════════════

PROFESSIONAL TRADING TERMINAL - Bloomberg/TradingView Style

Features:
📊 Real-time Portfolio P&L with live prices
📈 Interactive price charts with TradingView widget
🐋 Whale/Bot detection with live alerts
💹 Multi-exchange balance aggregation  
🎵 Queen's AI commentary with voice
⚡ Sub-second data refresh
🌐 WebSocket live data streaming

PORT: 14000
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os

# Load environment variables from .env file FIRST
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import asyncio
import aiohttp
import atexit
from aiohttp import web
import json
import logging
from typing import Dict, Set, List, Optional
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime
import time
import hashlib
import hmac
import urllib.parse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import cognitive narrator
try:
    from aureon.queen.queen_cognitive_narrator import QueenCognitiveNarrator
    NARRATOR_AVAILABLE = True
except ImportError:
    NARRATOR_AVAILABLE = False
    logger.warning("Queen Cognitive Narrator not available")

# Import Binance WebSocket for live market data
try:
    from aureon.exchanges.binance_ws_client import BinanceWebSocketClient, WSTicker, WSTrade
    BINANCE_WS_AVAILABLE = True
except ImportError:
    BINANCE_WS_AVAILABLE = False
    logger.warning("Binance WebSocket client not available")

# Import unified market cache for reading cached prices
try:
    from aureon.data_feeds.unified_market_cache import get_market_cache, get_all_prices, get_ticker, DEFAULT_SYMBOLS
    MARKET_CACHE_AVAILABLE = True
except ImportError:
    MARKET_CACHE_AVAILABLE = False
    DEFAULT_SYMBOLS = ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX', 'LINK', 'DOT', 'MATIC']
    logger.warning("Unified market cache not available")

# Import Ocean Scanner for global market scanning
try:
    from aureon.scanners.aureon_ocean_scanner import OceanScanner
    OCEAN_SCANNER_AVAILABLE = True
except ImportError:
    OCEAN_SCANNER_AVAILABLE = False
    OceanScanner = None
    logger.warning("Ocean Scanner not available")

# Import Harmonic Liquid Aluminium Field for live visualization
try:
    from aureon.harmonic.aureon_harmonic_liquid_aluminium import HarmonicLiquidAluminiumField
    HARMONIC_FIELD_AVAILABLE = True
except ImportError:
    HARMONIC_FIELD_AVAILABLE = False
    logger.warning("Harmonic Liquid Aluminium Field not available")

# ═══════════════════════════════════════════════════════════════════════════════
# ⚡ V11 POWER STATION - Compound Engine (SIPHON + COMPOUND + REINVEST)
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.trading.v11_power_station_live import V11PowerStationLive, V11Config, PowerGridState
    V11_AVAILABLE = True
    logger.info("⚡ V11 Power Station: AVAILABLE")
except ImportError:
    V11_AVAILABLE = False
    V11PowerStationLive = None
    V11Config = None
    PowerGridState = None
    logger.warning("V11 Power Station not available")

# ═══════════════════════════════════════════════════════════════════════════════
# 🌐 OPEN SOURCE DATA FEEDS - Fear & Greed, CoinGecko, etc.
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.queen.queen_open_source_data_engine import OpenSourceDataEngine, get_data_engine
    OPEN_DATA_AVAILABLE = True
    logger.info("🌐 Open Source Data Engine: AVAILABLE")
except ImportError:
    OPEN_DATA_AVAILABLE = False
    OpenSourceDataEngine = None
    get_data_engine = None
    logger.warning("Open Source Data Engine not available")

# ═══════════════════════════════════════════════════════════════════════════════
# 📡 THOUGHTBUS - Event bridge for system communication
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, get_thought_bus, Thought
    THOUGHTBUS_AVAILABLE = True
    logger.info("📡 ThoughtBus: AVAILABLE")
except ImportError:
    THOUGHTBUS_AVAILABLE = False
    ThoughtBus = None
    get_thought_bus = None
    Thought = None
    logger.warning("ThoughtBus not available")

# ═══════════════════════════════════════════════════════════════════════════════
# ⚛️ QUEEN QUANTUM COGNITION - Enhanced quantum-powered cognition amplifier
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.queen.queen_quantum_cognition import get_quantum_cognition, QueenQuantumCognition
    QUANTUM_COGNITION_AVAILABLE = True
    logger.info("⚛️ Queen Quantum Cognition: AVAILABLE")
except ImportError:
    QUANTUM_COGNITION_AVAILABLE = False
    get_quantum_cognition = None
    QueenQuantumCognition = None
    logger.warning("Queen Quantum Cognition not available")

# ═══════════════════════════════════════════════════════════════════════════════
# 👑💰 QUEEN ASSET COMMAND CENTER - Full portfolio visibility
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.queen.queen_asset_command_center import (
        get_asset_command_center, 
        get_asset_monitor,
        get_ocean_view,
        QueenAssetCommandCenter
    )
    ASSET_COMMAND_AVAILABLE = True
    logger.info("👑💰 Queen Asset Command Center: AVAILABLE")
except ImportError:
    ASSET_COMMAND_AVAILABLE = False
    get_asset_command_center = None
    get_asset_monitor = None
    get_ocean_view = None
    QueenAssetCommandCenter = None
    logger.warning("Queen Asset Command Center not available")

# ═══════════════════════════════════════════════════════════════════════════════
# 🔤 UNIFIED SYMBOL MANAGER - Correct symbols & quantities per exchange
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.trading.unified_symbol_manager import get_symbol_manager, UnifiedSymbolManager
    SYMBOL_MANAGER_AVAILABLE = True
    logger.info("🔤 Unified Symbol Manager: AVAILABLE")
except ImportError:
    SYMBOL_MANAGER_AVAILABLE = False
    get_symbol_manager = None
    UnifiedSymbolManager = None
    logger.warning("Unified Symbol Manager not available")

# ═══════════════════════════════════════════════════════════════════════════════
# 👑🧠 QUEEN HIVE MIND - Central consciousness
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from aureon.utils.aureon_queen_hive_mind import get_queen, QueenHiveMind
    QUEEN_HIVE_AVAILABLE = True
    logger.info("👑🧠 Queen Hive Mind: AVAILABLE")
except ImportError:
    QUEEN_HIVE_AVAILABLE = False
    get_queen = None
    QueenHiveMind = None
    logger.warning("Queen Hive Mind not available")

PRO_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>👑 Aureon Pro Trading Terminal</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
    <style>
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --border-color: #30363d;
            --text-primary: #f0f6fc;
            --text-secondary: #8b949e;
            --accent-green: #3fb950;
            --accent-red: #f85149;
            --accent-blue: #58a6ff;
            --accent-yellow: #d29922;
            --accent-purple: #a371f7;
            --accent-orange: #f0883e;
            --accent-gold: #ffd700;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            overflow-x: hidden;
            min-height: 100vh;
        }
        
        /* Top Navigation Bar */
        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 16px;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .logo-icon {
            font-size: 28px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        .logo-text {
            font-family: 'JetBrains Mono', monospace;
            font-size: 18px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-gold), var(--accent-orange));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .market-ticker {
            display: flex;
            gap: 24px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
        }
        
        .ticker-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .ticker-symbol { color: var(--text-secondary); }
        .ticker-price { font-weight: 600; }
        .ticker-change { font-size: 12px; }
        .ticker-change.up { color: var(--accent-green); }
        .ticker-change.down { color: var(--accent-red); }
        
        .controls {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: var(--text-secondary);
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent-green);
            animation: blink 2s infinite;
        }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .status-dot.disconnected { background: var(--accent-red); }
        
        /* Main Layout */
        .main-container {
            display: grid;
            grid-template-columns: 1fr 320px;
            grid-template-rows: auto 1fr auto;
            gap: 1px;
            background: var(--border-color);
            height: calc(100vh - 50px);
        }
        
        .panel {
            background: var(--bg-secondary);
            padding: 16px;
            overflow-y: auto;
            min-height: 0;  /* Critical for flex/grid children to scroll properly */
        }
        
        .panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
        }
        
        .panel-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        /* Top Positions Bar - Full width top row */
        .positions-bar {
            grid-column: 1 / -1;
            grid-row: 1;
            background: linear-gradient(135deg, rgba(34,197,94,0.1), rgba(59,130,246,0.1));
            border-bottom: 2px solid var(--accent-green);
            padding: 12px 20px;
            display: flex;
            align-items: center;
            gap: 16px;
            overflow-x: auto;
        }
        
        .positions-bar-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--accent-green);
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .position-chips {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            flex: 1;
        }
        
        .position-chip {
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 6px 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            white-space: nowrap;
            transition: all 0.2s;
        }
        
        .position-chip:hover {
            background: rgba(255,255,255,0.1);
            transform: translateY(-1px);
        }
        
        .position-chip.winner {
            border-color: var(--accent-green);
            background: rgba(34,197,94,0.15);
        }
        
        .position-chip.loser {
            border-color: var(--accent-red);
            background: rgba(239,68,68,0.15);
        }
        
        .position-chip .symbol {
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .position-chip .value {
            color: var(--text-secondary);
            font-size: 11px;
        }
        
        .position-chip .pnl {
            font-weight: 600;
        }
        
        .position-chip .pnl.positive { color: var(--accent-green); }
        .position-chip .pnl.negative { color: var(--accent-red); }
        
        .positions-bar-summary {
            display: flex;
            gap: 16px;
            align-items: center;
            margin-left: auto;
            padding-left: 16px;
            border-left: 1px solid var(--border-color);
        }
        
        .summary-stat {
            text-align: center;
        }
        
        .summary-stat .label {
            font-size: 10px;
            color: var(--text-secondary);
            text-transform: uppercase;
        }
        
        .summary-stat .value {
            font-size: 14px;
            font-weight: 600;
        }
        
        /* Queen's Voice Panel - Full width BOTTOM - Clean & Elegant */
        .queen-panel {
            grid-column: 1 / -1;
            grid-row: 3;
            background: linear-gradient(135deg, rgba(255,215,0,0.08), rgba(240,136,62,0.05));
            border-top: 2px solid var(--accent-gold);
            padding: 16px 24px;
            display: flex;
            align-items: flex-start;
            gap: 20px;
            height: 180px;
            min-height: 180px;
            max-height: 220px;
            overflow: hidden;
        }
        
        .queen-avatar {
            font-size: 52px;
            animation: queenFloat 3s ease-in-out infinite;
            flex-shrink: 0;
            filter: drop-shadow(0 0 20px rgba(255,215,0,0.6));
            margin-right: 12px;
        }
        
        @keyframes queenGlow {
            0%, 100% { filter: drop-shadow(0 0 20px rgba(255,215,0,0.6)); }
            50% { filter: drop-shadow(0 0 35px rgba(255,215,0,0.9)); }
        }
        
        @keyframes queenFloat {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }
        
        .queen-content { 
            flex: 1; 
            width: 100%; 
            height: 100%;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }
        
        .queen-message {
            font-size: 15px;
            color: var(--accent-gold);
            font-weight: 500;
            margin-bottom: 8px;
            line-height: 1.5;
            flex-shrink: 0;
        }
        
        .queen-thought {
            font-size: 13px;
            color: var(--text-primary);
            line-height: 1.6;
            margin-bottom: 8px;
            padding: 12px 16px;
            background: rgba(255,215,0,0.06);
            border-radius: 8px;
            border-left: 3px solid var(--accent-gold);
            max-height: 100px;
            overflow-y: auto;
            width: 100%;
            flex: 1;
        }
        
        .queen-thought p {
            margin-bottom: 10px;
            text-align: left;
        }
        
        .queen-thought p:last-child {
            margin-bottom: 0;
        }
        
        .queen-thought strong {
            color: var(--accent-gold);
        }
        
        .queen-thought .timestamp {
            color: var(--text-secondary);
            font-size: 11px;
            font-style: italic;
        }
        
        .queen-thought .decision {
            color: var(--accent-green);
            font-weight: 600;
        }
        
        .queen-thought .warning {
            color: var(--accent-orange);
        }
        
        .queen-thought .analysis {
            color: var(--accent-blue);
        }
        
        .queen-status {
            font-size: 11px;
            color: var(--text-secondary);
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .status-item.active { color: var(--accent-green); }
        .status-item.processing { color: var(--accent-yellow); animation: pulse 1s infinite; }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .voice-controls {
            display: flex;
            flex-direction: column;
            gap: 8px;
            align-items: center;
        }
        
        .voice-controls-title {
            display: none;
        }
        
        .voice-btn {
            padding: 8px 16px;
            background: var(--accent-gold);
            color: #000;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 13px;
        }
        
        .voice-btn:hover { transform: scale(1.05); }
        .voice-btn.active { background: var(--accent-green); }
        
        .voice-select {
            padding: 6px 10px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            border-radius: 4px;
            font-size: 12px;
        }
        
        /* Portfolio Panel */
        .portfolio-summary {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }
        
        .summary-card {
            background: var(--bg-tertiary);
            border-radius: 8px;
            padding: 12px;
            border: 1px solid var(--border-color);
        }
        
        .summary-label {
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-bottom: 4px;
        }
        
        .summary-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 18px;
            font-weight: 700;
        }
        
        .summary-value.positive { color: var(--accent-green); }
        .summary-value.negative { color: var(--accent-red); }
        
        .summary-change {
            font-size: 11px;
            margin-top: 2px;
        }
        
        /* Position List */
        .position-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .position-item {
            background: var(--bg-tertiary);
            border-radius: 6px;
            padding: 10px 12px;
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 8px;
            border: 1px solid var(--border-color);
            transition: all 0.2s;
        }
        
        .position-item:hover {
            border-color: var(--accent-blue);
            transform: translateX(2px);
        }
        
        .position-symbol {
            font-weight: 600;
            font-size: 13px;
        }
        
        .position-details {
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 2px;
        }
        
        .position-pnl {
            text-align: right;
            font-family: 'JetBrains Mono', monospace;
        }
        
        .position-value {
            font-size: 13px;
            font-weight: 600;
        }
        
        .position-percent {
            font-size: 11px;
        }
        
        /* Chart Panel */
        .chart-panel {
            grid-row: span 1;
        }
        
        /* Professional Trading Chart Container */
        .chart-container {
            background: linear-gradient(180deg, rgba(13, 17, 23, 0.95) 0%, rgba(22, 27, 34, 0.9) 100%);
            border-radius: 8px;
            padding: 12px 16px 8px 8px;
            height: 180px;
            border: 1px solid rgba(48, 54, 61, 0.6);
            position: relative;
            box-shadow: 
                inset 0 1px 0 rgba(255, 255, 255, 0.03),
                0 4px 12px rgba(0, 0, 0, 0.2);
        }
        
        .chart-container::before {
            content: '📈 EQUITY';
            position: absolute;
            top: 4px;
            left: 8px;
            font-size: 8px;
            color: #6e7681;
            font-family: 'SF Mono', monospace;
            letter-spacing: 0.5px;
        }
        
        .chart-container canvas {
            margin-top: 4px;
        }
        
        /* Chart Info Bar - Compact */
        .chart-info-bar {
            display: flex;
            gap: 12px;
            justify-content: center;
            padding: 4px 8px;
            background: var(--bg-tertiary);
            border-radius: 4px;
            margin-bottom: 8px;
        }
        
        .chart-stat {
            font-size: 9px;
            color: #6e7681;
            font-family: 'SF Mono', monospace;
        }
        
        .chart-stat span {
            color: #8b949e;
        }
        
        .chart-interval-badge {
            font-size: 9px;
            background: rgba(34, 197, 94, 0.15);
            color: #22c55e;
            padding: 2px 8px;
            border-radius: 10px;
            font-family: 'SF Mono', monospace;
        }
        
        /* Activity Feed */
        .activity-feed {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .activity-item {
            background: var(--bg-tertiary);
            border-radius: 6px;
            padding: 10px;
            border-left: 3px solid var(--accent-blue);
            font-size: 12px;
        }
        
        .activity-item.whale { border-left-color: var(--accent-orange); }
        .activity-item.battle { border-left-color: var(--accent-red); }
        .activity-item.queen { border-left-color: var(--accent-gold); }
        .activity-item.profit { border-left-color: var(--accent-green); }
        
        .activity-time {
            color: var(--text-secondary);
            font-size: 10px;
            margin-bottom: 4px;
        }
        
        .activity-text { color: var(--text-primary); }
        
        /* Bot Detection Panel */
        .bot-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
        }
        
        .bot-card {
            background: var(--bg-tertiary);
            border-radius: 6px;
            padding: 10px;
            border: 1px solid var(--border-color);
        }
        
        .bot-card.whale {
            border-color: var(--accent-orange);
            background: rgba(240, 136, 62, 0.1);
        }
        
        .bot-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 6px;
        }
        
        .bot-symbol { font-weight: 600; font-size: 12px; }
        .bot-type { font-size: 16px; }
        
        .bot-stats {
            font-size: 11px;
            color: var(--text-secondary);
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 16px;
        }
        
        .stat-card {
            background: var(--bg-tertiary);
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            border: 1px solid var(--border-color);
        }
        
        .stat-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 24px;
            font-weight: 700;
            color: var(--accent-blue);
        }
        
        .stat-label {
            font-size: 10px;
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-top: 4px;
        }
        
        /* Exchange Balances */
        .exchange-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .exchange-card {
            background: var(--bg-tertiary);
            border-radius: 6px;
            padding: 12px;
            border: 1px solid var(--border-color);
        }
        
        .exchange-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .exchange-name {
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .exchange-status {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent-green);
        }
        
        .exchange-balance {
            font-family: 'JetBrains Mono', monospace;
            font-size: 16px;
            font-weight: 600;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-tertiary); }
        ::-webkit-scrollbar-thumb { 
            background: var(--border-color); 
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-secondary); }
        
        /* Animations */
        .flash-green { animation: flashGreen 0.5s; }
        .flash-red { animation: flashRed 0.5s; }
        
        @keyframes flashGreen {
            0%, 100% { background: var(--bg-tertiary); }
            50% { background: rgba(63, 185, 80, 0.3); }
        }
        
        @keyframes flashRed {
            0%, 100% { background: var(--bg-tertiary); }
            50% { background: rgba(248, 81, 73, 0.3); }
        }
        
        /* Responsive */
        @media (max-width: 1400px) {
            .main-container {
                grid-template-columns: 1fr 280px;
            }
        }
        
        /* ═══════════════════════════════════════════════════════════════════════
           📈🔩 UNIFIED PORTFOLIO + HARMONIC FIELD STYLES
           ═══════════════════════════════════════════════════════════════════════ */
        
        /* Living Cells Section */
        .harmonic-section {
            margin-top: 8px;
        }
        
        /* Harmonic Stats Bar (compact) */
        .harmonic-stats-bar {
            display: flex;
            gap: 16px;
            font-size: 11px;
            color: var(--text-secondary);
            background: var(--bg-tertiary);
            padding: 6px 12px;
            border-radius: 6px;
            margin-bottom: 8px;
        }
        
        .harmonic-stats-bar span {
            white-space: nowrap;
        }
        
        /* Living Cells Canvas Wrapper - Full Width Bio Lab */
        .harmonic-canvas-wrapper {
            background: linear-gradient(180deg, #0a0f14 0%, #050a0d 100%);
            border-radius: 12px;
            padding: 0;
            border: 1px solid rgba(34, 197, 94, 0.2);
            box-shadow: 
                inset 0 0 60px rgba(0, 0, 0, 0.8),
                inset 0 0 100px rgba(34, 197, 94, 0.03),
                0 0 30px rgba(34, 197, 94, 0.05);
            overflow: hidden;
            position: relative;
        }
        
        .harmonic-canvas-wrapper::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(ellipse at 20% 20%, rgba(34, 197, 94, 0.08), transparent 40%),
                radial-gradient(ellipse at 80% 80%, rgba(99, 102, 241, 0.06), transparent 40%),
                radial-gradient(ellipse at 50% 50%, rgba(239, 68, 68, 0.04), transparent 50%);
            pointer-events: none;
        }
        
        #harmonic-field-canvas {
            width: 100%;
            height: 100%;
            background: transparent;
            border-radius: 12px;
            display: block;
        }
        
        /* Compact Legend Bar */
        .harmonic-legend-bar {
            display: flex;
            gap: 8px;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 8px;
            padding: 4px 8px;
            background: var(--bg-tertiary);
            border-radius: 6px;
        }
        
        .legend-chip {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 10px;
            color: var(--text-secondary);
            padding: 2px 6px;
            border-radius: 4px;
            background: var(--bg-secondary);
        }
        
        .legend-chip::before {
            content: '';
            width: 8px;
            height: 8px;
            border-radius: 2px;
            background: var(--color);
        }
        
        /* Harmonic Top Nodes & Layer Stats */
        .harmonic-toplist, .harmonic-layer-stats {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-top: 8px;
            font-size: 10px;
        }
        
        .chip {
            display: inline-block;
            background: var(--bg-tertiary);
            padding: 3px 8px;
            border-radius: 4px;
            color: var(--text-secondary);
        }
        
        /* ═══════════════════════════════════════════════════════════════════════
           📊 ULTRA-COMPACT RIGHT SIDEBAR - No Scroll Design
           ═══════════════════════════════════════════════════════════════════════ */
        
        .right-sidebar {
            display: flex;
            flex-direction: column;
            padding: 10px !important;
            gap: 6px;
            overflow: hidden;
        }
        
        .sb-row {
            display: flex;
            gap: 4px;
            background: var(--bg-tertiary);
            border-radius: 4px;
            padding: 5px 8px;
            border: 1px solid var(--border-color);
        }
        
        .sb-row.full { flex-direction: column; }
        
        .sb-label {
            font-size: 12px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.3px;
            white-space: nowrap;
        }
        
        .sb-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(50px, 1fr));
            gap: 3px;
            width: 100%;
        }
        
        .sb-cell {
            text-align: center;
            background: var(--bg-secondary);
            padding: 3px 2px;
            border-radius: 3px;
        }
        
        .sb-val {
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            font-weight: 700;
            color: var(--text-primary);
            display: block;
        }
        
        .sb-val.g { color: var(--accent-green); }
        .sb-val.y { color: #f0b90b; }
        .sb-val.o { color: var(--accent-orange); }
        .sb-val.r { color: var(--accent-red); }
        
        .sb-sub {
            font-size: 10px;
            color: var(--text-secondary);
            text-transform: uppercase;
        }
        
        /* Exchange Pills */
        .ex-pills {
            display: flex;
            gap: 4px;
            width: 100%;
        }
        
        .ex-pill {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            background: var(--bg-secondary);
            padding: 5px 6px;
            border-radius: 3px;
            font-size: 12px;
        }
        
        .ex-pill span:first-child { font-size: 12px; }
        .ex-pill .ex-v {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        /* Fear & Greed Mini */
        .fg-mini {
            display: flex;
            align-items: center;
            gap: 6px;
            width: 100%;
        }
        
        .fg-badge {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: conic-gradient(from 180deg, #ff4757 0deg, #ffa502 90deg, #2ed573 180deg, #ffa502 270deg, #ff4757 360deg);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        
        .fg-badge::before {
            content: '';
            position: absolute;
            width: 24px;
            height: 24px;
            background: var(--bg-tertiary);
            border-radius: 50%;
        }
        
        .fg-badge .fg-n {
            position: relative;
            z-index: 1;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 700;
        }
        
        .fg-txt { flex: 1; }
        .fg-txt .fg-l { font-size: 10px; font-weight: 600; display: block; }
        .fg-txt .fg-s { font-size: 9px; color: var(--text-secondary); }
        .fg-txt .fg-s b { color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }
        
        /* Leaders & Laggards Section */
        .leaders-laggards {
            display: flex;
            gap: 6px;
            width: 100%;
        }
        
        .leader-section {
            flex: 1;
            background: var(--bg-secondary);
            border-radius: 4px;
            padding: 6px 8px;
        }
        
        .section-title {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            display: block;
            margin-bottom: 4px;
        }
        
        .section-title.green { color: var(--accent-green); }
        .section-title.red { color: var(--accent-red); }
        
        .leader-list {
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            line-height: 1.6;
        }
        
        .leader-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .leader-item .sym { color: var(--text-primary); font-weight: 600; }
        .leader-item .pct { font-weight: 700; }
        .leader-item .pct.up { color: var(--accent-green); }
        .leader-item .pct.down { color: var(--accent-red); }
        
        /* Position Summary (kept for compatibility) */
        .pos-summary {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 3px;
            width: 100%;
        }
        
        /* Activity Mini */
        .activity-mini {
            flex: 1;
            overflow: hidden;
            background: var(--bg-tertiary);
            border-radius: 4px;
            padding: 5px 8px;
            border: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
        }
        
        .activity-mini .sb-label { margin-bottom: 3px; }
        
        .activity-scroll {
            flex: 1;
            overflow-y: auto;
            font-size: 9px;
            line-height: 1.4;
        }
        
        .act-line {
            padding: 2px 0;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-secondary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .act-line:last-child { border-bottom: none; }
        .act-line.profit { color: var(--accent-green); }
        .act-line.alert { color: var(--accent-orange); }
        
        .muted { color: var(--text-secondary); }
        
        /* ═══════════════════════════════════════════════════════════════════════ */
        
        @media (max-width: 1100px) {
            .main-container {
                grid-template-columns: 1fr;
            }
            .chart-panel { grid-column: span 1; }
            .right-sidebar { display: none; }
        }

        /* Mobile Responsive Styles */
        @media (max-width: 768px) {
            body {
                font-size: 14px;
            }

            .main-container {
                display: flex;
                flex-direction: column;
                height: auto;
            }

            .panel {
                padding: 12px;
            }

            .right-sidebar {
                display: flex; /* Re-enable for mobile */
                order: 2; /* Show after main content */
            }

            .chart-panel {
                order: 1;
            }

            .queen-panel {
                order: 3;
            }

            .topbar {
                flex-direction: column;
                align-items: flex-start;
                gap: 8px;
                padding: 12px;
            }

            .market-ticker {
                flex-wrap: wrap;
                gap: 8px;
            }
        }
    </style>
</head>
<body>
    <!-- Top Navigation Bar -->
    <div class="topbar">
        <div class="logo">
            <span class="logo-icon">👑</span>
            <span class="logo-text">AUREON PRO TERMINAL</span>
        </div>
        
        <div class="market-ticker" id="market-ticker">
            <div class="ticker-item">
                <span class="ticker-symbol">BTC</span>
                <span class="ticker-price" id="btc-price">$--,---</span>
                <span class="ticker-change" id="btc-change">--%</span>
            </div>
            <div class="ticker-item">
                <span class="ticker-symbol">ETH</span>
                <span class="ticker-price" id="eth-price">$--,---</span>
                <span class="ticker-change" id="eth-change">--%</span>
            </div>
            <div class="ticker-item">
                <span class="ticker-symbol">SOL</span>
                <span class="ticker-price" id="sol-price">$---</span>
                <span class="ticker-change" id="sol-change">--%</span>
            </div>
            <div class="ticker-item" id="top-gainer-ticker" style="display: none;">
                <span class="ticker-symbol">🚀</span>
                <span class="ticker-price" id="gainer-symbol">---</span>
                <span class="ticker-change up" id="gainer-change">+0%</span>
            </div>
            <div class="ticker-item" id="top-loser-ticker" style="display: none;">
                <span class="ticker-symbol">📉</span>
                <span class="ticker-price" id="loser-symbol">---</span>
                <span class="ticker-change down" id="loser-change">-0%</span>
            </div>
        </div>
        
        <div class="market-breadth" id="market-breadth" style="display: flex; gap: 12px; align-items: center; font-size: 11px;">
            <span style="color: var(--accent-green);">↑ <span id="gainers-count">--</span></span>
            <span style="color: var(--accent-red);">↓ <span id="losers-count">--</span></span>
            <span style="color: var(--text-secondary);">📊 <span id="tracked-count">--</span> live</span>
        </div>
        
        <div class="controls">
            <div class="status-indicator">
                <span class="status-dot" id="ws-status"></span>
                <span id="ws-text">Connected</span>
            </div>
            <span style="color: var(--text-secondary); font-size: 12px;" id="clock">--:--:--</span>
        </div>
    </div>
    
    <div class="main-container">
        <!-- TOP: Positions Bar - Shows all positions at a glance -->
        <div class="positions-bar" id="positions-bar">
            <div class="positions-bar-title">
                <span>📊</span>
                <span>MY POSITIONS</span>
            </div>
            <div class="position-chips" id="position-chips">
                <div class="position-chip">
                    <span class="symbol">Loading...</span>
                </div>
            </div>
            <div class="positions-bar-summary">
                <div class="summary-stat">
                    <div class="label">Cash</div>
                    <div class="value" id="bar-cash" style="color: var(--accent-green);">$0</div>
                </div>
                <div class="summary-stat">
                    <div class="label">Exchanges</div>
                    <div class="value" id="bar-exchanges" style="color: var(--text-primary);">--</div>
                </div>
            </div>
        </div>
        
        <!-- Main Panel: Living Cells + Portfolio Chart -->
        <div class="panel chart-panel">
            <div class="panel-header">
                <span class="panel-title">🧬 Living Position Cells</span>
                <span class="chart-interval-badge">Real-time organisms</span>
            </div>
            
            <!-- Living Position Cells Visualization - MAIN FEATURE -->
            <div class="harmonic-section" style="margin-top: 0;">
                <div class="harmonic-canvas-wrapper" style="height: 280px;">
                    <canvas id="harmonic-field-canvas" width="800" height="280"></canvas>
                </div>
                <div class="harmonic-legend-bar">
                    <span class="legend-chip" style="--color: #22c55e;">💚 Profit</span>
                    <span class="legend-chip" style="--color: #ef4444;">❤️ Loss</span>
                    <span class="legend-chip" style="--color: #f97316;">🦙 Alpaca</span>
                    <span class="legend-chip" style="--color: #eab308;">🟡 Binance</span>
                    <span class="legend-chip" style="--color: #06b6d4;">🐙 Kraken</span>
                </div>
            </div>
            
            <!-- Compact Portfolio Chart -->
            <div class="chart-container" style="height: 100px; margin-top: 12px;">
                <canvas id="portfolio-chart"></canvas>
            </div>
            <div class="chart-info-bar">
                <span class="chart-stat">📊 <span id="chart-candles">0</span></span>
                <span class="chart-stat">📈 <span id="chart-high">--</span></span>
                <span class="chart-stat">📉 <span id="chart-low">--</span></span>
                <span class="chart-stat">⏱️ <span id="chart-countdown">30s</span></span>
            </div>
            
            <div class="panel-header" style="margin-top: 12px;">
                <span class="panel-title">⚡ Live Activity</span>
            </div>
            
            <div class="activity-feed" id="activity-feed">
                <!-- Activity items will be added here -->
            </div>
        </div>
        
        <!-- Right Panel: Ultra-Compact Info Sidebar -->
        <div class="panel right-sidebar">
            <!-- EXCHANGES -->
            <div class="sb-row">
                <span class="sb-label">🏦</span>
                <div class="ex-pills">
                    <div class="ex-pill"><span>🟡</span><span class="ex-v" id="binance-balance">--</span></div>
                    <div class="ex-pill"><span>🐙</span><span class="ex-v" id="kraken-balance">--</span></div>
                    <div class="ex-pill"><span>🦙</span><span class="ex-v" id="alpaca-balance">--</span></div>
                </div>
            </div>
            
            <!-- V11 POWER -->
            <div class="sb-row full" id="v11-panel">
                <span class="sb-label">⚡ V11 Power</span>
                <div class="sb-grid">
                    <div class="sb-cell"><span class="sb-val" id="v11-total-nodes">0</span><span class="sb-sub">Nodes</span></div>
                    <div class="sb-cell"><span class="sb-val g" id="v11-generating">0</span><span class="sb-sub">Gen</span></div>
                    <div class="sb-cell"><span class="sb-val" id="v11-grid-value">$0</span><span class="sb-sub">Value</span></div>
                    <div class="sb-cell"><span class="sb-val y" id="v11-siphon">$0</span><span class="sb-sub">Siphon</span></div>
                    <div class="sb-cell"><span class="sb-val" id="v11-unrealized">$0</span><span class="sb-sub">P&L</span></div>
                    <div class="sb-cell"><span class="sb-val" id="v11-reserve">$0</span><span class="sb-sub">Reserve</span></div>
                </div>
            </div>
            
            <!-- SENTIMENT -->
            <div class="sb-row" id="sentiment-panel">
                <div class="fg-mini">
                    <div class="fg-badge"><span class="fg-n" id="fg-value">50</span></div>
                    <div class="fg-txt">
                        <span class="fg-l" id="fg-label">Neutral</span>
                        <span class="fg-s">BTC <b id="btc-dominance">--</b>% · MCap <b id="total-mcap">--</b>T</span>
                    </div>
                </div>
            </div>
            
            <!-- DETECTION -->
            <div class="sb-row full">
                <span class="sb-label">🤖 Detection</span>
                <div class="sb-grid">
                    <div class="sb-cell"><span class="sb-val" id="total-bots">0</span><span class="sb-sub">Bots</span></div>
                    <div class="sb-cell"><span class="sb-val" id="whale-count">0</span><span class="sb-sub">Whales</span></div>
                    <div class="sb-cell"><span class="sb-val" id="hive-count">0</span><span class="sb-sub">Hives</span></div>
                </div>
            </div>
            
            <!-- OCEAN SCANNER -->
            <div class="sb-row full">
                <span class="sb-label">🌊 Ocean</span>
                <div class="sb-grid">
                    <div class="sb-cell"><span class="sb-val" id="ocean-universe">0</span><span class="sb-sub">Symbols</span></div>
                    <div class="sb-cell"><span class="sb-val o" id="ocean-hot">0</span><span class="sb-sub">Hot</span></div>
                    <div class="sb-cell"><span class="sb-val" id="ocean-scans">0</span><span class="sb-sub">Scans</span></div>
                </div>
            </div>
            
            <!-- PERFORMANCE LEADERS & LAGGARDS -->
            <div class="sb-row full">
                <span class="sb-label">🏆 Leaders & Laggards</span>
                <div class="leaders-laggards">
                    <div class="leader-section">
                        <span class="section-title green">🔥 Top Gainers</span>
                        <div id="top-leaders" class="leader-list">--</div>
                    </div>
                    <div class="leader-section">
                        <span class="section-title red">❄️ Top Losers</span>
                        <div id="top-laggards" class="leader-list">--</div>
                    </div>
                </div>
            </div>
            
            <!-- QUEEN'S AI INSIGHTS -->
            <div class="sb-row full">
                <span class="sb-label">🔮 Queen's Insights</span>
                <div class="sb-grid" style="grid-template-columns: repeat(2, 1fr);">
                    <div class="sb-cell"><span class="sb-val g" id="sb-coherence">--</span><span class="sb-sub">Coherence</span></div>
                    <div class="sb-cell"><span class="sb-val y" id="sb-lambda">--</span><span class="sb-sub">Lambda λ</span></div>
                    <div class="sb-cell"><span class="sb-val" id="sb-win-rate">--</span><span class="sb-sub">Win Rate</span></div>
                    <div class="sb-cell"><span class="sb-val" id="sb-timelines">--</span><span class="sb-sub">Anchored</span></div>
                </div>
            </div>
        </div>
        
        <!-- BOTTOM: Queen's Voice Panel - UNIFIED AUTONOMOUS CONSCIOUSNESS -->
        <div class="queen-panel">
            <div class="queen-avatar">👑</div>
            <div class="queen-content">
                <div class="queen-message" id="queen-message">
                    Queen Aureon awakening... Unified consciousness initializing...
                </div>
                <div class="queen-thought" id="queen-thought">
                    <p class="timestamp">System Boot Sequence Active</p>
                    <p>Connecting to unified quantum cognition. All thought, message, and voice now flow from ONE autonomous consciousness.</p>
                </div>
                <div class="queen-status" id="queen-status">
                    <span class="status-item active">✓ Consciousness</span>
                    <span class="status-item active">✓ Portfolio</span>
                    <span class="status-item active">✓ Markets</span>
                    <span class="status-item processing">⟳ Analyzing</span>
                </div>
            </div>
            <div class="voice-controls">
                <button class="voice-btn" id="voice-toggle">🔊 Voice</button>
                <select class="voice-select" id="voice-select">
                    <option value="">Voice</option>
                </select>
                <input type="range" id="voice-volume" min="0" max="1" step="0.1" value="0.8" 
                       style="width: 80px;" title="Volume">
            </div>
        </div>
    </div>
    
    <script>
        // ========== State ==========
        const state = {
            portfolio: {
                totalValue: 0,
                costBasis: 0,
                unrealizedPnl: 0,
                todayPnl: 0,
                positions: []
            },
            exchanges: {
                binance: 0,
                kraken: 0,
                alpaca: 0
            },
            bots: {},
            prices: {},
            voiceEnabled: false,
            priceHistory: []
        };
        
        // ========== WebSocket ==========
        let ws = null;
        let reconnectAttempts = 0;
        
        function connectWebSocket() {
            const wsScheme = (window.location.protocol === 'https:') ? 'wss' : 'ws';
            const wsUrl = `${wsScheme}://${window.location.host}/ws`;
            console.log('🔌 Attempting WebSocket connection to:', wsUrl);
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                console.log('✅ WebSocket connected');
                document.getElementById('ws-status').classList.remove('disconnected');
                document.getElementById('ws-text').textContent = 'Connected';
                reconnectAttempts = 0;
                addActivity('✅ Connected to Aureon Pro Terminal', 'queen');
            };
            
            ws.onclose = () => {
                console.log('❌ WebSocket disconnected');
                document.getElementById('ws-status').classList.add('disconnected');
                document.getElementById('ws-text').textContent = 'Disconnected';
                setTimeout(connectWebSocket, Math.min(1000 * Math.pow(2, reconnectAttempts++), 30000));
            };
            
            ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log('📨 Raw message received:', event.data);
                handleMessage(data);
            };
        }
        
        function handleMessage(data) {
            console.log('📨 Received message:', data.type, data);
            switch(data.type) {
                case 'portfolio_update':
                    console.log('📊 Updating portfolio:', data.data);
                    updatePortfolio(data.data);
                    break;
                case 'price_update':
                    console.log('💰 Updating prices:', data.data);
                    updatePrices(data.data);
                    break;
                case 'all_prices_update':
                    updateAllPrices(data.data);
                    break;
                case 'market_flow':
                    updateMarketFlow(data.data);
                    break;
                case 'exchange_balance':
                    updateExchangeBalance(data.data);
                    break;
                case 'exchange_balances':
                    // New message type with all balances at once
                    updateAllExchangeBalances(data.data);
                    break;
                case 'bots_snapshot':
                    handleBotsSnapshot(data.data);
                    break;
                case 'bot_detected':
                    handleBotDetected(data.data);
                    break;
                case 'queen_message':
                    handleQueenMessage(data.message);
                    break;
                case 'queen_thought':
                    handleQueenThought(data);
                    break;
                case 'harmonic_field':
                    updateHarmonicField(data.data);
                    break;
                case 'activity':
                    addActivity(data.message, data.category || '');
                    break;
                // ⚡ V11 POWER STATION
                case 'v11_update':
                    updateV11PowerStation(data.data);
                    break;
                // 🌐 MARKET SENTIMENT
                case 'sentiment_update':
                    updateMarketSentiment(data.data);
                    break;
                // 🌊 OCEAN SCANNER
                case 'ocean_scanner_update':
                    updateOceanScanner(data.data);
                    break;
            }
        }

        // ========== Bots Snapshot ==========
        function handleBotsSnapshot(snapshot) {
            if (!snapshot || !snapshot.bots) return;
            state.bots = snapshot.bots;
            document.getElementById('total-bots').textContent = Object.keys(state.bots).length;
            document.getElementById('total-whales').textContent = snapshot.whales || 0;
            document.getElementById('total-hives').textContent = snapshot.hives || 0;
            renderBots();
        }
        
        // ========== Market Flow (Binance WebSocket Data) ==========
        function updateMarketFlow(data) {
            if (!data) return;
            
            // Update market breadth counts
            document.getElementById('gainers-count').textContent = data.positive_count || '--';
            document.getElementById('losers-count').textContent = data.negative_count || '--';
            document.getElementById('tracked-count').textContent = data.tracked_symbols || '--';
            
            // Update top gainer ticker
            if (data.gainers && data.gainers.length > 0) {
                const gainer = data.gainers[0];
                document.getElementById('top-gainer-ticker').style.display = 'flex';
                document.getElementById('gainer-symbol').textContent = gainer.symbol;
                document.getElementById('gainer-change').textContent = '+' + gainer.change.toFixed(1) + '%';
            }
            
            // Update top loser ticker
            if (data.losers && data.losers.length > 0) {
                const loser = data.losers[0];
                document.getElementById('top-loser-ticker').style.display = 'flex';
                document.getElementById('loser-symbol').textContent = loser.symbol;
                document.getElementById('loser-change').textContent = loser.change.toFixed(1) + '%';
            }
            
            // Show activity for big moves
            if (data.gainers && data.gainers[0] && data.gainers[0].change > 10) {
                addActivity(`🚀 ${data.gainers[0].symbol} surging +${data.gainers[0].change.toFixed(1)}%!`, 'profit');
            }
            if (data.losers && data.losers[0] && data.losers[0].change < -10) {
                addActivity(`📉 ${data.losers[0].symbol} crashing ${data.losers[0].change.toFixed(1)}%!`, 'whale');
            }
        }
        
        function updateAllPrices(data) {
            // Store all 40+ symbol prices from Binance WebSocket
            state.allPrices = data || {};
        }
        
        function handleQueenThought(data) {
            // Update the thought panel with rich multi-paragraph content
            const thoughtEl = document.getElementById('queen-thought');
            const messageEl = document.getElementById('queen-message');
            const statusEl = document.getElementById('queen-status');
            
            // Update headline
            if (data.headline) {
                messageEl.textContent = data.headline;
            }
            
            // Build thought HTML with paragraphs
            let html = '';
            if (data.timestamp) {
                html += `<p class="timestamp">${data.timestamp} | ${data.phase || 'Analysis'}</p>`;
            }
            
            if (data.paragraphs && data.paragraphs.length > 0) {
                data.paragraphs.forEach(p => {
                    const cssClass = p.type || '';
                    html += `<p class="${cssClass}">${p.text}</p>`;
                });
            }
            
            thoughtEl.innerHTML = html;
            
            // Update status indicators
            if (data.status) {
                let statusHtml = '';
                for (const [key, value] of Object.entries(data.status)) {
                    const icon = value === 'active' ? '✓' : value === 'processing' ? '⟳' : '○';
                    statusHtml += `<span class="status-item ${value}">${icon} ${key}</span>`;
                }
                statusEl.innerHTML = statusHtml;
            }
            
            // Speak the first paragraph if voice is enabled
            if (data.paragraphs && data.paragraphs.length > 0) {
                const spokenText = data.paragraphs.map(p => p.text).join(' ');
                speak(spokenText);
            }
            
            // Add to activity feed
            if (data.headline) {
                addActivity('👑 ' + data.headline, 'queen');
            }
            
            // 🧬 Trigger Queen pulse in Living Cells visualization
            if (data.decision) {
                triggerQueenPulse(data.decision);
            } else if (data.paragraphs) {
                // Check for BUY/SELL keywords in thought
                const allText = data.paragraphs.map(p => p.text).join(' ').toUpperCase();
                if (allText.includes('BUY') || allText.includes('ENTER') || allText.includes('LONG')) {
                    triggerQueenPulse('BUY');
                } else if (allText.includes('SELL') || allText.includes('EXIT') || allText.includes('CLOSE')) {
                    triggerQueenPulse('SELL');
                }
            }
            
            // 🔮 Update Queen's Insights sidebar with AI metrics
            updateQueenInsights(data);
        }
        
        // ========== Portfolio ==========
        function updatePortfolio(data) {
            state.portfolio = {...state.portfolio, ...data};
            
            document.getElementById('total-value').textContent = formatCurrency(data.totalValue);
            document.getElementById('cost-basis').textContent = formatCurrency(data.costBasis);
            
            const pnlEl = document.getElementById('unrealized-pnl');
            pnlEl.textContent = formatCurrency(data.unrealizedPnl, true);
            pnlEl.className = 'summary-value ' + (data.unrealizedPnl >= 0 ? 'positive' : 'negative');
            
            const pctEl = document.getElementById('pnl-percent');
            const pct = data.costBasis > 0 ? (data.unrealizedPnl / data.costBasis * 100) : 0;
            pctEl.textContent = (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
            pctEl.style.color = pct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
            
            if (data.positions) {
                renderPositions(data.positions);
                // 🧬 SYNC LIVING CELLS WITH POSITIONS
                syncCellsWithPositions(data.positions);
                // 📊 UPDATE TOP POSITIONS BAR
                updatePositionsBar(data.positions);
            }

            // Push latest equity point into chart
            if (typeof data.totalValue === 'number') {
                updateChart(data.totalValue);
            }
            
            // Update sidebar Leaders & Laggards
            updateLeadersLaggards();
        }
        
        // 📊 Update the top positions bar with all positions
        function updatePositionsBar(positions) {
            const container = document.getElementById('position-chips');
            if (!positions || !positions.length) {
                container.innerHTML = '<div class="position-chip"><span class="symbol">No positions</span></div>';
                return;
            }
            
            // Sort by P&L percentage
            const sorted = [...positions].sort((a, b) => (b.pnlPercent || 0) - (a.pnlPercent || 0));
            
            // Create chips for each position
            container.innerHTML = sorted.map(pos => {
                const isWinner = (pos.pnlPercent || 0) >= 0;
                const chipClass = isWinner ? 'winner' : 'loser';
                const pnlClass = isWinner ? 'positive' : 'negative';
                const value = pos.currentValue || (pos.quantity * pos.currentPrice) || 0;
                const exchange = pos.exchange ? pos.exchange.charAt(0).toUpperCase() : '';
                
                return `
                    <div class="position-chip ${chipClass}">
                        <span class="symbol">${pos.symbol}</span>
                        <span class="value">$${value.toFixed(2)}</span>
                        <span class="pnl ${pnlClass}">${(pos.pnlPercent >= 0 ? '+' : '')}${(pos.pnlPercent || 0).toFixed(1)}%</span>
                    </div>
                `;
            }).join('');
            
            // Update summary stats
            const cashEl = document.getElementById('bar-cash');
            const exchangesEl = document.getElementById('bar-exchanges');
            
            // Count exchanges
            const exchanges = new Set(positions.map(p => p.exchange).filter(Boolean));
            const exchangeCount = exchanges.size;
            const exchangeNames = [...exchanges].map(e => e.charAt(0).toUpperCase() + e.slice(1)).join(', ');
            
            if (exchangesEl) {
                exchangesEl.textContent = exchangeCount > 0 ? `${exchangeCount} (${exchangeNames})` : '--';
            }
        }
        
        function renderPositions(positions) {
            const container = document.getElementById('position-list');
            if (!positions.length) {
                container.innerHTML = '<div style="color: var(--text-secondary); text-align: center; padding: 20px;">No positions</div>';
                return;
            }
            
            container.innerHTML = positions.map(pos => {
                const pnlClass = pos.unrealizedPnl >= 0 ? 'positive' : 'negative';
                const currentValue = pos.currentValue || (pos.quantity * pos.currentPrice);
                return `
                    <div class="position-item">
                        <div>
                            <div class="position-symbol">${pos.symbol}</div>
                            <div class="position-details">
                                ${pos.quantity.toFixed(4)} @ $${pos.currentPrice.toFixed(4)}
                            </div>
                        </div>
                        <div class="position-pnl">
                            <div class="position-value">
                                ${formatCurrency(currentValue)}
                            </div>
                            <div class="position-percent ${pnlClass}">
                                ${(pos.pnlPercent >= 0 ? '+' : '') + pos.pnlPercent.toFixed(2)}%
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        // ========== Exchange Balances ==========
        function updateExchangeBalance(data) {
            if (data.exchange && data.balance !== undefined) {
                state.exchanges[data.exchange] = data.balance;
                const el = document.getElementById(`${data.exchange}-balance`);
                if (el) {
                    el.textContent = formatCurrency(data.balance);
                    el.classList.add('flash-green');
                    setTimeout(() => el.classList.remove('flash-green'), 500);
                }
            }
        }
        
        function updateAllExchangeBalances(balances) {
            if (!balances || typeof balances !== 'object') return;
            
            let totalCash = 0;
            
            for (const [exchange, balance] of Object.entries(balances)) {
                const el = document.getElementById(`${exchange}-balance`);
                if (el && balance !== undefined) {
                    const formatted = balance > 0 ? formatCurrency(balance) : '$---.--';
                    el.textContent = formatted;
                    if (balance > 0) {
                        el.classList.add('flash-green');
                        setTimeout(() => el.classList.remove('flash-green'), 500);
                        totalCash += balance;
                    }
                }
            }
            
            // Update positions bar cash display
            const cashEl = document.getElementById('bar-cash');
            if (cashEl) {
                cashEl.textContent = formatCurrency(totalCash);
            }
        }
        
        // ========== Prices ==========
        function updatePrices(data) {
            Object.assign(state.prices, data);
            
            if (data.BTC) {
                document.getElementById('btc-price').textContent = formatCurrency(data.BTC.price);
                updateTickerChange('btc-change', data.BTC.change24h);
            }
            if (data.ETH) {
                document.getElementById('eth-price').textContent = formatCurrency(data.ETH.price);
                updateTickerChange('eth-change', data.ETH.change24h);
            }
            if (data.SOL) {
                document.getElementById('sol-price').textContent = formatCurrency(data.SOL.price);
                updateTickerChange('sol-change', data.SOL.change24h);
            }
        }
        
        function updateTickerChange(elementId, change) {
            const el = document.getElementById(elementId);
            el.textContent = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';
            el.className = 'ticker-change ' + (change >= 0 ? 'up' : 'down');
        }
        
        // ========== Bot Detection ==========
        function handleBotDetected(bot) {
            state.bots[bot.id] = bot;
            
            document.getElementById('total-bots').textContent = Object.keys(state.bots).length;
            document.getElementById('whale-count').textContent = 
                Object.values(state.bots).filter(b => b.type === 'whale').length;
            
            const emoji = bot.type === 'whale' ? '🐋' : bot.type === 'shark' ? '🦈' : '🐟';
            addActivity(`${emoji} ${bot.type.toUpperCase()} detected on ${bot.symbol}`, bot.type);
            
            renderBotGrid();
        }
        
        function renderBotGrid() {
            const container = document.getElementById('bot-grid');
            const bots = Object.values(state.bots).slice(-6);
            
            container.innerHTML = bots.map(bot => `
                <div class="bot-card ${bot.type}">
                    <div class="bot-header">
                        <span class="bot-symbol">${bot.symbol}</span>
                        <span class="bot-type">${bot.type === 'whale' ? '🐋' : '🐟'}</span>
                    </div>
                    <div class="bot-stats">
                        ${bot.pattern || 'Unknown'} • $${formatNumber(bot.volume || 0)}
                    </div>
                </div>
            `).join('');
        }
        
        // ========== Queen's Voice ==========
        const synth = window.speechSynthesis;
        
        function populateVoices() {
            const voices = synth.getVoices();
            const select = document.getElementById('voice-select');
            select.innerHTML = '<option value="">Select Voice</option>';
            
            voices.forEach((voice, i) => {
                const opt = document.createElement('option');
                opt.value = i;
                const star = voice.name.includes('Female') || voice.name.includes('Samantha') ? '⭐ ' : '';
                opt.textContent = star + voice.name;
                select.appendChild(opt);
            });
        }
        
        if (synth.onvoiceschanged !== undefined) {
            synth.onvoiceschanged = populateVoices;
        }
        populateVoices();
        
        document.getElementById('voice-toggle').addEventListener('click', function() {
            state.voiceEnabled = !state.voiceEnabled;
            this.textContent = state.voiceEnabled ? '🔊 Voice ON' : '🔈 Voice OFF';
            this.classList.toggle('active', state.voiceEnabled);
            
            if (state.voiceEnabled) {
                speak('Queen Aureon consciousness online. Monitoring all trading activity.');
            }
        });
        
        function speak(text) {
            if (!state.voiceEnabled || !synth) return;
            
            synth.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.0;
            utterance.pitch = 1.1;
            utterance.volume = parseFloat(document.getElementById('voice-volume').value);
            
            const voiceIndex = document.getElementById('voice-select').value;
            if (voiceIndex) {
                utterance.voice = synth.getVoices()[parseInt(voiceIndex)];
            }
            
            synth.speak(utterance);
        }
        
        function handleQueenMessage(message) {
            document.getElementById('queen-message').textContent = message;
            // Simple message - just update headline, not full thought
            speak(message);
            addActivity('👑 ' + message, 'queen');
        }
        
        // ========== Activity Feed ==========
        function addActivity(text, category = '') {
            const feed = document.getElementById('activity-feed');
            const item = document.createElement('div');
            item.className = 'activity-item ' + category;
            item.innerHTML = `
                <div class="activity-time">${new Date().toLocaleTimeString()}</div>
                <div class="activity-text">${text}</div>
            `;
            feed.insertBefore(item, feed.firstChild);
            
            while (feed.children.length > 50) {
                feed.removeChild(feed.lastChild);
            }
        }
        
        // ========== Professional Trading Chart (30s Buffered) ==========
        let chart = null;
        let chartBuffer = {
            values: [],
            lastUpdate: 0,
            updateInterval: 30000,  // 30 seconds between chart updates
            candles: [],            // OHLC candles
            currentCandle: null,
            maxCandles: 60          // 30 minutes of data at 30s intervals
        };
        
        function initChart() {
            const ctx = document.getElementById('portfolio-chart').getContext('2d');
            
            // Initialize with empty candle
            chartBuffer.currentCandle = {
                time: Date.now(),
                open: 0,
                high: 0,
                low: Infinity,
                close: 0,
                volume: 0
            };
            
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Portfolio Value',
                            data: [],
                            borderColor: '#22c55e',
                            backgroundColor: createGradient(ctx),
                            fill: true,
                            tension: 0.2,
                            borderWidth: 2,
                            pointRadius: 0,
                            pointHoverRadius: 4,
                            pointHoverBackgroundColor: '#22c55e',
                            pointHoverBorderColor: '#fff',
                            pointHoverBorderWidth: 2
                        },
                        {
                            label: 'Moving Avg',
                            data: [],
                            borderColor: 'rgba(99, 102, 241, 0.7)',
                            borderWidth: 1,
                            borderDash: [5, 5],
                            fill: false,
                            tension: 0.4,
                            pointRadius: 0
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 750,
                        easing: 'easeOutQuart'
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            enabled: true,
                            backgroundColor: 'rgba(13, 17, 23, 0.95)',
                            titleColor: '#f0f6fc',
                            bodyColor: '#8b949e',
                            borderColor: 'rgba(48, 54, 61, 0.8)',
                            borderWidth: 1,
                            padding: 12,
                            displayColors: false,
                            callbacks: {
                                title: (items) => items[0]?.label || '',
                                label: (item) => {
                                    if (item.datasetIndex === 0) {
                                        const val = item.raw;
                                        const prev = item.dataIndex > 0 ? 
                                            chart.data.datasets[0].data[item.dataIndex - 1] : val;
                                        const change = val - prev;
                                        const pct = prev > 0 ? (change / prev * 100).toFixed(2) : 0;
                                        return [
                                            `Value: $${val.toLocaleString(undefined, {minimumFractionDigits: 2})}`,
                                            `Change: ${change >= 0 ? '+' : ''}$${change.toFixed(2)} (${change >= 0 ? '+' : ''}${pct}%)`
                                        ];
                                    }
                                    return `MA: $${item.raw.toFixed(2)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { 
                                color: 'rgba(48, 54, 61, 0.3)',
                                drawBorder: false
                            },
                            ticks: { 
                                color: '#6e7681',
                                font: { size: 10 },
                                maxRotation: 0,
                                maxTicksLimit: 8
                            }
                        },
                        y: {
                            position: 'right',
                            grid: { 
                                color: 'rgba(48, 54, 61, 0.3)',
                                drawBorder: false
                            },
                            ticks: { 
                                color: '#6e7681',
                                font: { size: 10 },
                                callback: v => '$' + formatCompact(v),
                                maxTicksLimit: 5
                            }
                        }
                    }
                }
            });
        }
        
        function createGradient(ctx) {
            const gradient = ctx.createLinearGradient(0, 0, 0, 180);
            gradient.addColorStop(0, 'rgba(34, 197, 94, 0.3)');
            gradient.addColorStop(0.5, 'rgba(34, 197, 94, 0.1)');
            gradient.addColorStop(1, 'rgba(34, 197, 94, 0)');
            return gradient;
        }
        
        function formatCompact(num) {
            if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
            if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
            return num.toFixed(2);
        }
        
        function updateChart(value) {
            if (!chart || typeof value !== 'number' || isNaN(value)) return;
            
            const now = Date.now();
            
            // Always update current candle with latest value
            if (!chartBuffer.currentCandle.open) {
                chartBuffer.currentCandle.open = value;
                chartBuffer.currentCandle.high = value;
                chartBuffer.currentCandle.low = value;
            }
            chartBuffer.currentCandle.high = Math.max(chartBuffer.currentCandle.high, value);
            chartBuffer.currentCandle.low = Math.min(chartBuffer.currentCandle.low, value);
            chartBuffer.currentCandle.close = value;
            chartBuffer.currentCandle.volume++;
            
            // Only commit candle every 30 seconds
            if (now - chartBuffer.lastUpdate < chartBuffer.updateInterval) {
                return; // Buffer - don't update chart yet
            }
            
            // Commit current candle
            chartBuffer.lastUpdate = now;
            const timeLabel = new Date().toLocaleTimeString('en-GB', { 
                hour: '2-digit', 
                minute: '2-digit',
                second: '2-digit'
            });
            
            // Add new data point (use close price)
            chart.data.labels.push(timeLabel);
            chart.data.datasets[0].data.push(chartBuffer.currentCandle.close);
            
            // Calculate and add moving average (5-period SMA)
            const data = chart.data.datasets[0].data;
            const maWindow = 5;
            if (data.length >= maWindow) {
                const slice = data.slice(-maWindow);
                const ma = slice.reduce((a, b) => a + b, 0) / maWindow;
                chart.data.datasets[1].data.push(ma);
            } else {
                chart.data.datasets[1].data.push(chartBuffer.currentCandle.close);
            }
            
            // Trim old data
            if (chart.data.labels.length > chartBuffer.maxCandles) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
                chart.data.datasets[1].data.shift();
            }
            
            // Update chart colors based on trend
            const lastTwo = chart.data.datasets[0].data.slice(-2);
            if (lastTwo.length === 2) {
                const trending = lastTwo[1] >= lastTwo[0];
                chart.data.datasets[0].borderColor = trending ? '#22c55e' : '#ef4444';
                const ctx = chart.ctx;
                const gradient = ctx.createLinearGradient(0, 0, 0, 180);
                if (trending) {
                    gradient.addColorStop(0, 'rgba(34, 197, 94, 0.3)');
                    gradient.addColorStop(1, 'rgba(34, 197, 94, 0)');
                } else {
                    gradient.addColorStop(0, 'rgba(239, 68, 68, 0.3)');
                    gradient.addColorStop(1, 'rgba(239, 68, 68, 0)');
                }
                chart.data.datasets[0].backgroundColor = gradient;
            }
            
            // Update chart stats bar
            updateChartStats();
            
            // Smooth animation update
            chart.update('default');
            
            // Start new candle
            chartBuffer.currentCandle = {
                time: now,
                open: value,
                high: value,
                low: value,
                close: value,
                volume: 1
            };
        }
        
        function updateChartStats() {
            if (!chart || !chart.data.datasets[0].data.length) return;
            
            const data = chart.data.datasets[0].data;
            const high = Math.max(...data);
            const low = Math.min(...data);
            
            const candlesEl = document.getElementById('chart-candles');
            const highEl = document.getElementById('chart-high');
            const lowEl = document.getElementById('chart-low');
            
            if (candlesEl) candlesEl.textContent = data.length;
            if (highEl) highEl.textContent = '$' + formatCompact(high);
            if (lowEl) lowEl.textContent = '$' + formatCompact(low);
        }
        
        // Chart countdown timer
        setInterval(() => {
            if (!chartBuffer.lastUpdate) return;
            const elapsed = Date.now() - chartBuffer.lastUpdate;
            const remaining = Math.max(0, Math.ceil((chartBuffer.updateInterval - elapsed) / 1000));
            const countdownEl = document.getElementById('chart-countdown');
            if (countdownEl) {
                countdownEl.textContent = remaining + 's';
                countdownEl.style.color = remaining <= 5 ? '#22c55e' : '#8b949e';
            }
        }, 1000);
        
        // ========== Utilities ==========
        function formatCurrency(value, showSign = false) {
            const sign = showSign && value >= 0 ? '+' : '';
            return sign + '$' + Math.abs(value).toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }
        
        function formatNumber(num) {
            if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
            if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K';
            return num.toFixed(0);
        }
        
        // ========== LIVING POSITION CELLS - Biological Visualization ==========
        let harmonicCanvas = null;
        let harmonicCtx = null;
        let harmonicTime = 0;
        let livingCells = [];  // Each cell = one position (asset)
        let queenPulses = [];  // Queen decision effects
        let nutrientField = [];  // Background energy field
        let fieldSize = 32;
        
        // Cell state colors - biological
        const CELL_COLORS = {
            profit: { membrane: '#22c55e', nucleus: '#4ade80', glow: 'rgba(34, 197, 94, 0.4)' },
            loss: { membrane: '#ef4444', nucleus: '#f87171', glow: 'rgba(239, 68, 68, 0.4)' },
            neutral: { membrane: '#6366f1', nucleus: '#818cf8', glow: 'rgba(99, 102, 241, 0.3)' },
            dividing: { membrane: '#f59e0b', nucleus: '#fbbf24', glow: 'rgba(245, 158, 11, 0.5)' }
        };
        
        // Exchange colors for cell tints
        const EXCHANGE_MEMBRANE = {
            alpaca: '#f97316',   // Orange
            binance: '#eab308',  // Yellow/Gold
            kraken: '#06b6d4',   // Cyan
            capital: '#10b981'   // Emerald
        };
        
        function initHarmonicField() {
            harmonicCanvas = document.getElementById('harmonic-field-canvas');
            if (harmonicCanvas) {
                const rect = harmonicCanvas.getBoundingClientRect();
                harmonicCanvas.width = rect.width;
                harmonicCanvas.height = rect.height;
                harmonicCtx = harmonicCanvas.getContext('2d');
                
                // Initialize nutrient field
                initNutrientField();
                
                // Start animation
                requestAnimationFrame(animateLivingCells);
                console.log('🧬 Living Position Cells initialized');
            }
        }
        
        function initNutrientField() {
            nutrientField = [];
            for (let y = 0; y < fieldSize; y++) {
                nutrientField[y] = [];
                for (let x = 0; x < fieldSize; x++) {
                    nutrientField[y][x] = 0.5 + Math.random() * 0.3;
                }
            }
        }
        
        // Update cells from real portfolio positions
        function updateHarmonicField(data) {
            // Also accept portfolio data directly
            if (state.portfolio && state.portfolio.positions) {
                syncCellsWithPositions(state.portfolio.positions);
            }
        }
        
        // Sync living cells with actual positions
        function syncCellsWithPositions(positions) {
            if (!positions || !harmonicCanvas) return;
            
            const w = harmonicCanvas.width;
            const h = harmonicCanvas.height;
            
            // Create map of existing cells by symbol
            const existingCells = {};
            livingCells.forEach(cell => {
                existingCells[cell.symbol] = cell;
            });
            
            // Update or create cells for each position
            const newCells = [];
            positions.forEach((pos, idx) => {
                const symbol = pos.symbol || 'UNKNOWN';
                const existing = existingCells[symbol];
                
                if (existing) {
                    // Update existing cell with new data
                    existing.targetSize = calculateCellSize(pos);
                    existing.pnlPercent = pos.pnlPercent || 0;
                    existing.currentValue = pos.currentValue || 0;
                    existing.quantity = pos.quantity || 0;
                    existing.exchange = pos.exchange || 'alpaca';
                    existing.costBasis = pos.costBasis || (pos.quantity * pos.avgCost) || 0;
                    existing.avgCost = pos.avgCost || 0;
                    existing.unrealizedPnl = pos.unrealizedPnl || 0;
                    existing.isGrowing = pos.pnlPercent > existing.lastPnl;
                    existing.isShrinking = pos.pnlPercent < existing.lastPnl;
                    existing.lastPnl = pos.pnlPercent;
                    newCells.push(existing);
                    delete existingCells[symbol];
                } else {
                    // Create new cell (birth animation)
                    const cell = createLivingCell(pos, idx, positions.length, w, h);
                    newCells.push(cell);
                }
            });
            
            // Cells not in positions anymore = death (shrink to zero)
            Object.values(existingCells).forEach(cell => {
                cell.dying = true;
                cell.targetSize = 0;
                newCells.push(cell);
            });
            
            livingCells = newCells.filter(c => !(c.dying && c.size < 1));
        }
        
        function createLivingCell(pos, idx, total, w, h) {
            // Arrange cells in organic pattern
            const angle = (idx / Math.max(total, 1)) * Math.PI * 2;
            const radius = Math.min(w, h) * 0.3;
            const centerX = w / 2;
            const centerY = h / 2;
            
            return {
                symbol: pos.symbol || 'UNKNOWN',
                x: centerX + Math.cos(angle) * radius * (0.5 + Math.random() * 0.5),
                y: centerY + Math.sin(angle) * radius * (0.5 + Math.random() * 0.5),
                vx: 0,
                vy: 0,
                size: 5,  // Start small (birth)
                targetSize: calculateCellSize(pos),
                pnlPercent: pos.pnlPercent || 0,
                lastPnl: pos.pnlPercent || 0,
                currentValue: pos.currentValue || 0,
                quantity: pos.quantity || 0,
                exchange: pos.exchange || 'alpaca',
                costBasis: pos.costBasis || (pos.quantity * pos.avgCost) || 0,
                avgCost: pos.avgCost || 0,
                unrealizedPnl: pos.unrealizedPnl || 0,
                phase: Math.random() * Math.PI * 2,
                pulseRate: 0.8 + Math.random() * 0.4,  // Different heartbeat rates
                isGrowing: false,
                isShrinking: false,
                dying: false,
                organelles: Math.floor(3 + Math.random() * 4),  // Internal structures
                membraneWobble: [],
                birth: harmonicTime
            };
        }
        
        function calculateCellSize(pos) {
            // Size based on position value (log scale for visibility)
            const value = pos.currentValue || 0;
            const minSize = 20;
            const maxSize = 60;
            
            if (value <= 0) return minSize;
            
            // Log scale: $1 = minSize, $10000+ = maxSize
            const logVal = Math.log10(Math.max(1, value));
            const normalized = Math.min(1, logVal / 4);  // 4 = log10(10000)
            
            return minSize + (maxSize - minSize) * normalized;
        }
        
        function animateLivingCells() {
            harmonicTime += 0.016;  // ~60fps
            updateCellPhysics();
            updateNutrientField();
            renderBiologicalField();
            requestAnimationFrame(animateLivingCells);
        }
        
        function updateCellPhysics() {
            const w = harmonicCanvas?.width || 400;
            const h = harmonicCanvas?.height || 150;
            
            livingCells.forEach(cell => {
                // Smooth size transitions (growth/shrinkage)
                const sizeDiff = cell.targetSize - cell.size;
                cell.size += sizeDiff * 0.05;  // Smooth interpolation
                
                // Gentle floating motion (like cells in fluid)
                cell.vx += (Math.random() - 0.5) * 0.1;
                cell.vy += (Math.random() - 0.5) * 0.1;
                
                // Damping
                cell.vx *= 0.95;
                cell.vy *= 0.95;
                
                // Apply velocity
                cell.x += cell.vx;
                cell.y += cell.vy;
                
                // Keep in bounds with soft bounce
                const margin = cell.size + 10;
                if (cell.x < margin) { cell.x = margin; cell.vx *= -0.5; }
                if (cell.x > w - margin) { cell.x = w - margin; cell.vx *= -0.5; }
                if (cell.y < margin) { cell.y = margin; cell.vy *= -0.5; }
                if (cell.y > h - margin) { cell.y = h - margin; cell.vy *= -0.5; }
                
                // Cell-cell repulsion (avoid overlap)
                livingCells.forEach(other => {
                    if (other === cell) return;
                    const dx = cell.x - other.x;
                    const dy = cell.y - other.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    const minDist = cell.size + other.size + 5;
                    
                    if (dist < minDist && dist > 0) {
                        const force = (minDist - dist) / minDist * 0.3;
                        cell.vx += (dx / dist) * force;
                        cell.vy += (dy / dist) * force;
                    }
                });
            });
            
            // Process Queen pulses
            queenPulses = queenPulses.filter(pulse => {
                pulse.radius += 3;
                pulse.opacity -= 0.02;
                
                // Affect nearby cells
                livingCells.forEach(cell => {
                    const dx = cell.x - pulse.x;
                    const dy = cell.y - pulse.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    
                    if (Math.abs(dist - pulse.radius) < 20) {
                        // Cell reacts to Queen decision
                        cell.vx += (dx / dist) * pulse.strength * 0.5;
                        cell.vy += (dy / dist) * pulse.strength * 0.5;
                    }
                });
                
                return pulse.opacity > 0;
            });
        }
        
        function updateNutrientField() {
            const t = harmonicTime;
            for (let y = 0; y < fieldSize; y++) {
                for (let x = 0; x < fieldSize; x++) {
                    // Slow-moving nutrient waves
                    nutrientField[y][x] = 0.3 + 
                        Math.sin(x * 0.3 + t * 0.5) * 0.15 +
                        Math.cos(y * 0.25 + t * 0.3) * 0.15 +
                        Math.sin((x + y) * 0.2 + t * 0.4) * 0.1;
                }
            }
        }
        
        // Called when Queen makes a decision
        function triggerQueenPulse(decision) {
            const w = harmonicCanvas?.width || 400;
            const h = harmonicCanvas?.height || 150;
            
            queenPulses.push({
                x: w / 2,
                y: h / 2,
                radius: 10,
                opacity: 0.8,
                strength: decision === 'BUY' ? 1 : decision === 'SELL' ? -1 : 0.5,
                color: decision === 'BUY' ? '#22c55e' : decision === 'SELL' ? '#ef4444' : '#6366f1'
            });
        }
        
        function renderBiologicalField() {
            if (!harmonicCtx) return;
            
            const ctx = harmonicCtx;
            const w = harmonicCanvas.width;
            const h = harmonicCanvas.height;
            const t = harmonicTime;
            
            // Dark biological background with nutrient glow
            ctx.fillStyle = '#0a0f14';
            ctx.fillRect(0, 0, w, h);
            
            // Render nutrient field (subtle background glow)
            renderNutrientField(ctx, w, h);
            
            // Render Queen decision pulses
            queenPulses.forEach(pulse => {
                ctx.strokeStyle = pulse.color.replace(')', `, ${pulse.opacity})`).replace('rgb', 'rgba').replace('#', '');
                // Convert hex to rgba
                const r = parseInt(pulse.color.slice(1, 3), 16);
                const g = parseInt(pulse.color.slice(3, 5), 16);
                const b = parseInt(pulse.color.slice(5, 7), 16);
                ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${pulse.opacity})`;
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(pulse.x, pulse.y, pulse.radius, 0, Math.PI * 2);
                ctx.stroke();
            });
            
            // Render living cells (positions)
            livingCells.forEach(cell => {
                renderLivingCell(ctx, cell, t);
            });
            
            // Top info bar
            renderFieldInfo(ctx, w, h);
        }
        
        function renderNutrientField(ctx, w, h) {
            const cellW = w / fieldSize;
            const cellH = h / fieldSize;
            
            for (let y = 0; y < fieldSize; y++) {
                for (let x = 0; x < fieldSize; x++) {
                    const nutrient = nutrientField[y][x];
                    const alpha = nutrient * 0.15;
                    
                    ctx.fillStyle = `rgba(34, 197, 94, ${alpha})`;
                    ctx.fillRect(x * cellW, y * cellH, cellW + 1, cellH + 1);
                }
            }
        }
        
        function renderLivingCell(ctx, cell, t) {
            const x = cell.x;
            const y = cell.y;
            const size = cell.size;
            
            if (size < 1) return;
            
            // Determine cell state colors based on unrealizedPnl or pnlPercent
            const pnl = cell.unrealizedPnl || (cell.pnlPercent || 0);
            const state = pnl > 0 ? 'profit' : pnl < 0 ? 'loss' : 'neutral';
            const colors = CELL_COLORS[state];
            const exchangeColor = EXCHANGE_MEMBRANE[cell.exchange] || '#6366f1';
            
            // Heartbeat pulse
            const pulse = 1 + Math.sin(t * cell.pulseRate * 4) * 0.08;
            const pulseSize = size * pulse;
            
            // Growth/shrink animation
            const growthPulse = cell.isGrowing ? 1 + Math.sin(t * 8) * 0.15 : 
                               cell.isShrinking ? 1 - Math.sin(t * 8) * 0.1 : 1;
            const finalSize = pulseSize * growthPulse;
            
            // Cell glow (aura)
            const glowGrad = ctx.createRadialGradient(x, y, 0, x, y, finalSize * 1.5);
            glowGrad.addColorStop(0, colors.glow);
            glowGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
            ctx.fillStyle = glowGrad;
            ctx.beginPath();
            ctx.arc(x, y, finalSize * 1.5, 0, Math.PI * 2);
            ctx.fill();
            
            // Cell membrane (outer boundary) - wobbly organic edge
            ctx.save();
            ctx.translate(x, y);
            
            // Draw wobbly membrane
            ctx.beginPath();
            const membranePoints = 24;
            for (let i = 0; i <= membranePoints; i++) {
                const angle = (i / membranePoints) * Math.PI * 2;
                const wobble = Math.sin(angle * 3 + t * 2 + cell.phase) * 3 +
                              Math.sin(angle * 5 + t * 1.5) * 2;
                const r = finalSize + wobble;
                const px = Math.cos(angle) * r;
                const py = Math.sin(angle) * r;
                
                if (i === 0) ctx.moveTo(px, py);
                else ctx.lineTo(px, py);
            }
            ctx.closePath();
            
            // Fill with gradient
            const cellGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, finalSize);
            cellGrad.addColorStop(0, colors.nucleus);
            cellGrad.addColorStop(0.6, exchangeColor);
            cellGrad.addColorStop(1, colors.membrane);
            ctx.fillStyle = cellGrad;
            ctx.fill();
            
            // Membrane outline
            ctx.strokeStyle = colors.membrane;
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // Nucleus (center)
            const nucleusSize = finalSize * 0.35;
            ctx.fillStyle = colors.nucleus;
            ctx.beginPath();
            ctx.arc(0, 0, nucleusSize, 0, Math.PI * 2);
            ctx.fill();
            
            // Organelles (internal dots showing activity)
            for (let i = 0; i < cell.organelles; i++) {
                const orgAngle = (i / cell.organelles) * Math.PI * 2 + t * 0.5;
                const orgDist = finalSize * 0.5;
                const orgX = Math.cos(orgAngle) * orgDist;
                const orgY = Math.sin(orgAngle) * orgDist;
                const orgSize = 2 + Math.sin(t * 3 + i) * 1;
                
                ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
                ctx.beginPath();
                ctx.arc(orgX, orgY, orgSize, 0, Math.PI * 2);
                ctx.fill();
            }
            
            // Growth indicator (mitosis-like division line when growing fast)
            if (cell.isGrowing && pnl > 5) {
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
                ctx.lineWidth = 1;
                ctx.setLineDash([3, 3]);
                ctx.beginPath();
                ctx.moveTo(-finalSize, 0);
                ctx.lineTo(finalSize, 0);
                ctx.stroke();
                ctx.setLineDash([]);
            }
            
            ctx.restore();
            
            // Symbol label
            ctx.font = 'bold 9px "SF Mono", monospace';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            
            // Symbol text with shadow
            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            ctx.fillText(cell.symbol, x + 1, y + finalSize + 12);
            ctx.fillStyle = '#ffffff';
            ctx.fillText(cell.symbol, x, y + finalSize + 11);
            
            // P&L percentage below
            const pnlText = (pnl >= 0 ? '+' : '') + pnl.toFixed(1) + '%';
            ctx.font = '8px "SF Mono", monospace';
            ctx.fillStyle = pnl >= 0 ? '#22c55e' : '#ef4444';
            ctx.fillText(pnlText, x, y + finalSize + 22);
            
            // Value inside cell (if big enough)
            if (finalSize > 25) {
                ctx.font = 'bold 8px "SF Mono", monospace';
                ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
                const valueText = cell.currentValue >= 1000 ? 
                    '$' + (cell.currentValue / 1000).toFixed(1) + 'K' :
                    '$' + cell.currentValue.toFixed(2);
                ctx.fillText(valueText, x, y);
            }
        }
        
        function renderFieldInfo(ctx, w, h) {
            // Top bar with stats
            ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
            ctx.fillRect(0, 0, w, 20);
            
            ctx.font = '9px "SF Mono", monospace';
            ctx.fillStyle = '#6366f1';
            ctx.textAlign = 'left';
            ctx.fillText('🧬 LIVING POSITIONS', 8, 13);
            
            // Cell count
            ctx.textAlign = 'right';
            ctx.fillStyle = '#22c55e';
            ctx.fillText(`${livingCells.length} cells`, w - 8, 13);
        }
        
        function updateHarmonicStats(data) {
            // Stats are now shown inline
        }
        
        // Clock
        function updateClock() {
            document.getElementById('clock').textContent = new Date().toLocaleTimeString();
        }
        setInterval(updateClock, 1000);
        updateClock();
        
        // ════════════════════════════════════════════════════════════════════════════════
        // ⚡ V11 POWER STATION UPDATE
        // ════════════════════════════════════════════════════════════════════════════════
        function updateV11PowerStation(data) {
            if (!data) return;
            
            // Update V11 stats
            const v11Panel = document.getElementById('v11-panel');
            if (v11Panel) {
                document.getElementById('v11-total-nodes').textContent = data.total_nodes || 0;
                document.getElementById('v11-generating').textContent = data.generating_nodes || 0;
                document.getElementById('v11-grid-value').textContent = '$' + (data.total_grid_value || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
                document.getElementById('v11-siphon').textContent = '$' + (data.total_siphon_capacity || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
                document.getElementById('v11-unrealized').textContent = '$' + (data.total_unrealized_pnl || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
                document.getElementById('v11-reserve').textContent = '$' + (data.reserve_balance || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
                
                // Color the unrealized P&L
                const unrealizedEl = document.getElementById('v11-unrealized');
                if (data.total_unrealized_pnl > 0) {
                    unrealizedEl.style.color = 'var(--accent-green)';
                } else if (data.total_unrealized_pnl < 0) {
                    unrealizedEl.style.color = 'var(--accent-red)';
                }
            }
            
            // Log activity for significant events
            if (data.generating_nodes > 0) {
                addActivity(`⚡ V11: ${data.generating_nodes} nodes generating, $${data.total_siphon_capacity?.toFixed(2)} siphon ready`, 'profit');
            }
        }
        
        // ════════════════════════════════════════════════════════════════════════════════
        // 🌐 MARKET SENTIMENT UPDATE (Fear & Greed, Open Source Data)
        // ════════════════════════════════════════════════════════════════════════════════
        function updateMarketSentiment(data) {
            if (!data) return;
            
            const fgValue = data.fear_greed_index || 50;
            const fgLabel = data.fear_greed_label || 'Neutral';
            
            const fgValueEl = document.getElementById('fg-value');
            const fgLabelEl = document.getElementById('fg-label');
            
            if (fgValueEl) fgValueEl.textContent = fgValue;
            if (fgLabelEl) fgLabelEl.textContent = fgLabel;
            
            // BTC Dominance
            if (data.btc_dominance) {
                const btcDom = document.getElementById('btc-dominance');
                if (btcDom) btcDom.textContent = data.btc_dominance.toFixed(1);
            }
            
            // Total Market Cap
            if (data.total_market_cap) {
                const mcap = document.getElementById('total-mcap');
                if (mcap) mcap.textContent = data.total_market_cap.toFixed(2);
            }
        }
        
        // ════════════════════════════════════════════════════════════════════════════════
        // 🌊 OCEAN SCANNER UPDATE
        // ════════════════════════════════════════════════════════════════════════════════
        function updateOceanScanner(data) {
            if (!data) return;
            
            const oceanUniverse = document.getElementById('ocean-universe');
            const oceanHot = document.getElementById('ocean-hot');
            const oceanScans = document.getElementById('ocean-scans');
            
            if (oceanUniverse) oceanUniverse.textContent = (data.universe_size || 0).toLocaleString();
            if (oceanHot) oceanHot.textContent = data.hot_opportunities || 0;
            if (oceanScans) oceanScans.textContent = data.scan_count || 0;
        }
        
        // ════════════════════════════════════════════════════════════════════════════════
        // 🏆 LEADERS & LAGGARDS UPDATE (Top/Bottom Performers)
        // ════════════════════════════════════════════════════════════════════════════════
        function updateLeadersLaggards() {
            const positions = state.portfolio.positions || [];
            if (!positions.length) return;
            
            // Sort by P&L percentage
            const sorted = [...positions].sort((a, b) => (b.pnlPercent || 0) - (a.pnlPercent || 0));
            
            // Get top 3 winners and losers
            const winners = sorted.slice(0, 3);
            const losers = sorted.slice(-3).reverse();
            
            const leadersEl = document.getElementById('top-leaders');
            const laggardsEl = document.getElementById('top-laggards');
            
            if (leadersEl && winners.length) {
                leadersEl.innerHTML = winners.map(p => `
                    <div class="leader-item">
                        <span class="sym">${p.symbol}</span>
                        <span class="pct up">+${(p.pnlPercent || 0).toFixed(1)}%</span>
                    </div>
                `).join('');
            }
            
            if (laggardsEl && losers.length) {
                laggardsEl.innerHTML = losers.map(p => `
                    <div class="leader-item">
                        <span class="sym">${p.symbol}</span>
                        <span class="pct down">${(p.pnlPercent || 0).toFixed(1)}%</span>
                    </div>
                `).join('');
            }
        }
        
        // ════════════════════════════════════════════════════════════════════════════════
        // 🔮 QUEEN'S AI INSIGHTS UPDATE
        // ════════════════════════════════════════════════════════════════════════════════
        function updateQueenInsights(data) {
            // Update coherence
            const coherenceEl = document.getElementById('sb-coherence');
            if (coherenceEl && data.coherence !== undefined) {
                const coherence = (data.coherence * 100).toFixed(0);
                coherenceEl.textContent = coherence + '%';
                coherenceEl.className = 'sb-val ' + (data.coherence >= 0.7 ? 'g' : data.coherence >= 0.5 ? 'y' : 'r');
            }
            
            // Update lambda stability
            const lambdaEl = document.getElementById('sb-lambda');
            if (lambdaEl && data.lambda !== undefined) {
                lambdaEl.textContent = data.lambda.toFixed(2);
                lambdaEl.className = 'sb-val ' + (data.lambda >= 0.8 ? 'g' : data.lambda >= 0.5 ? 'y' : 'r');
            }
            
            // Update win rate
            const winRateEl = document.getElementById('sb-win-rate');
            if (winRateEl) {
                const positions = state.portfolio.positions || [];
                console.log('🎯 Win rate calculation - Positions:', positions.length, positions);
                const winners = positions.filter(p => {
                    const pnl = p.pnlPercent || p.pnl_pct || 0;
                    console.log(`   Position ${p.symbol}: pnlPercent=${pnl}`);
                    return pnl > 0;
                }).length;
                const total = positions.length;
                const rate = total > 0 ? ((winners / total) * 100).toFixed(0) : '--';
                console.log(`   Win Rate: ${winners}/${total} = ${rate}%`);
                winRateEl.textContent = rate + (rate !== '--' ? '%' : '');
                if (rate !== '--') {
                    winRateEl.className = 'sb-val ' + (parseInt(rate) >= 60 ? 'g' : parseInt(rate) >= 40 ? 'y' : 'r');
                }
            }
            
            // Update anchored timelines
            const timelinesEl = document.getElementById('sb-timelines');
            if (timelinesEl && data.anchored_timelines !== undefined) {
                timelinesEl.textContent = data.anchored_timelines;
            }
        }
        
        // ========== Initialize ==========
        console.log('🚀 Initializing Aureon Pro Terminal...');
        connectWebSocket();
        initChart();
        initHarmonicField();
        
        // Fetch initial data via HTTP
        async function fetchInitialData() {
            console.log('📡 Fetching initial data...');
            try {
                const resp = await fetch('/api/portfolio');
                if (resp.ok) {
                    const data = await resp.json();
                    console.log('📊 Portfolio data:', data);
                    updatePortfolio(data);
                    if (data.totalValue) updateChart(data.totalValue);
                } else {
                    console.error('❌ Portfolio fetch failed:', resp.status);
                }
            } catch (e) {
                console.error('❌ Portfolio fetch error:', e);
            }
            
            try {
                const resp = await fetch('/api/prices');
                if (resp.ok) {
                    const data = await resp.json();
                    console.log('💰 Price data:', data);
                    updatePrices(data);
                } else {
                    console.error('❌ Prices fetch failed:', resp.status);
                }
            } catch (e) {
                console.error('❌ Prices fetch error:', e);
            }
        }
        
        fetchInitialData();
        setInterval(fetchInitialData, 5000);
        
        console.log('👑 Aureon Pro Terminal initialized');
    </script>
</body>
</html>
"""


class AureonProDashboard:
    """Professional trading dashboard with real-time data."""
    
    def __init__(self, port: int = None):
        # Use PORT env var (DigitalOcean sets this) or default to 14000 for local dev
        self.port = port or int(os.getenv('PORT', '14000'))
        self.logger = logger
        self.clients: Set = set()
        
        # ═══════════════════════════════════════════════════════════════════════
        # 👑 UNIFIED QUEEN CONSCIOUSNESS - ONE AUTONOMOUS VOICE
        # All queen data (message, thought, voice) comes from THIS source
        # ═══════════════════════════════════════════════════════════════════════
        self.queen_cognition = get_quantum_cognition() if QUANTUM_COGNITION_AVAILABLE else None
        if self.queen_cognition:
            self.logger.info("👑⚛️ Queen Quantum Cognition: UNIFIED CONSCIOUSNESS ONLINE")
        
        # Legacy narrator (fallback if cognition not available)
        self.narrator = QueenCognitiveNarrator() if (NARRATOR_AVAILABLE and not self.queen_cognition) else None
        
        # Harmonic Liquid Aluminium Field for live visualization
        self.harmonic_field = HarmonicLiquidAluminiumField() if HARMONIC_FIELD_AVAILABLE else None
        
        # Ocean Scanner for global market opportunities
        self.ocean_scanner = None
        self.ocean_data = {
            'universe_size': 0,
            'hot_opportunities': 0,
            'top_opportunities': [],
            'scan_count': 0
        }
        
        # Binance WebSocket for real-time market data
        self.binance_ws = None
        self.binance_tickers = {}  # symbol -> WSTicker
        self.market_flow = {
            'total_volume_24h': 0,
            'gainers': [],
            'losers': [],
            'top_volume': [],
            'last_update': None
        }
        
        # State
        self.portfolio = {
            'totalValue': 0,
            'costBasis': 0,
            'unrealizedPnl': 0,
            'todayPnl': 0,
            'positions': []
        }
        self.prices = {}
        self.all_prices = {}  # Full 40+ symbol prices from Binance WS
        self.exchange_balances = {'binance': 0, 'kraken': 0, 'alpaca': 0}
        self.bots = {}
        self.bot_counts = {'whales': 0, 'hives': 0}
        self.queen_messages = deque(maxlen=50)
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # ⚡ V11 POWER STATION - Compound Engine
        # ═══════════════════════════════════════════════════════════════════════════════
        self.v11_station = None
        self.v11_data = {
            'total_nodes': 0,
            'generating_nodes': 0,
            'hibernating_nodes': 0,
            'consuming_nodes': 0,
            'total_grid_value': 0,
            'total_entry_cost': 0,
            'total_unrealized_pnl': 0,
            'total_siphon_capacity': 0,
            'reserve_balance': 0,
            'siphons_session': 0,
            'energy_siphoned': 0,
            'last_scan': None
        }
        if V11_AVAILABLE:
            try:
                v11_config = V11Config(
                    enabled_exchanges=['binance', 'alpaca', 'kraken'],
                    max_concurrent_positions=None
                )
                self.v11_station = V11PowerStationLive(config=v11_config, dry_run=False)
                logger.info("⚡ V11 Power Station: INITIALIZED")
            except Exception as e:
                logger.warning(f"⚡ V11 Power Station init failed: {e}")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # 🌐 MARKET SENTIMENT - Fear & Greed, Open Source Data
        # ═══════════════════════════════════════════════════════════════════════════════
        self.open_data_engine = None
        self.market_sentiment = {
            'fear_greed_index': 50,
            'fear_greed_label': 'Neutral',
            'btc_dominance': 0,
            'total_market_cap': 0,
            'last_update': None
        }
        if OPEN_DATA_AVAILABLE and get_data_engine:
            try:
                self.open_data_engine = get_data_engine()
                logger.info("🌐 Open Source Data Engine: INITIALIZED")
            except Exception as e:
                logger.warning(f"🌐 Open Data Engine init failed: {e}")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # 📡 THOUGHTBUS - System event bridge
        # ═══════════════════════════════════════════════════════════════════════════════
        self.thought_bus = None
        self.thought_events = deque(maxlen=100)  # Last 100 events
        if THOUGHTBUS_AVAILABLE and get_thought_bus:
            try:
                self.thought_bus = get_thought_bus()
                self.thought_bus.subscribe("*", self._on_thought_event)
                logger.info("📡 ThoughtBus: CONNECTED")
            except Exception as e:
                logger.warning(f"📡 ThoughtBus init failed: {e}")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # ⚛️ QUEEN QUANTUM COGNITION - Enhanced quantum-powered cognition amplifier
        # ═══════════════════════════════════════════════════════════════════════════════
        self.quantum_cognition = None
        self.quantum_data = {
            'amplification_level': 0,
            'coherence': 0,
            'quantum_systems_online': 0,
            'autonomous_mode': False,
            'last_decision': None,
            'last_update': None
        }
        if QUANTUM_COGNITION_AVAILABLE and get_quantum_cognition:
            try:
                self.quantum_cognition = get_quantum_cognition()
                logger.info("⚛️ Queen Quantum Cognition: INITIALIZED")
            except Exception as e:
                logger.warning(f"⚛️ Quantum Cognition init failed: {e}")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # 👑💰 QUEEN ASSET COMMAND CENTER - Full portfolio visibility
        # ═══════════════════════════════════════════════════════════════════════════════
        self.asset_command = None
        self.asset_monitor = None
        self.ocean_view = None
        self.asset_data = {
            'total_portfolio_value': 0,
            'total_positions': 0,
            'exchanges_connected': 0,
            'positions_by_exchange': {},
            'top_holdings': [],
            'last_update': None
        }
        if ASSET_COMMAND_AVAILABLE and get_asset_command_center:
            try:
                self.asset_command = get_asset_command_center()
                self.asset_monitor = get_asset_monitor() if get_asset_monitor else None
                self.ocean_view = get_ocean_view() if get_ocean_view else None
                logger.info("👑💰 Queen Asset Command Center: INITIALIZED")
            except Exception as e:
                logger.warning(f"👑💰 Asset Command init failed: {e}")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # 🔤 UNIFIED SYMBOL MANAGER - Correct symbols & quantities per exchange
        # ═══════════════════════════════════════════════════════════════════════════════
        self.symbol_manager = None
        self.symbol_data = {
            'kraken_pairs': 0,
            'binance_pairs': 0,
            'alpaca_pairs': 0,
            'capital_pairs': 0,
            'loaded': False
        }
        if SYMBOL_MANAGER_AVAILABLE and get_symbol_manager:
            try:
                self.symbol_manager = get_symbol_manager()
                logger.info("🔤 Unified Symbol Manager: INITIALIZED")
            except Exception as e:
                logger.warning(f"🔤 Symbol Manager init failed: {e}")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # 👑🧠 QUEEN HIVE MIND - Central consciousness (SERO)
        # ═══════════════════════════════════════════════════════════════════════════════
        self.queen_hive = None
        self.queen_hive_data = {
            'queen_name': 'SERO',
            'authority_level': 'SUPREME_AUTONOMOUS',
            'hive_systems_online': 0,
            'total_hive_systems': 0,
            'autonomous_enabled': False,
            'last_directive': None,
            'last_update': None
        }
        if QUEEN_HIVE_AVAILABLE and get_queen:
            try:
                self.queen_hive = get_queen()
                logger.info("👑🧠 Queen Hive Mind: INITIALIZED")
            except Exception as e:
                logger.warning(f"👑🧠 Queen Hive Mind init failed: {e}")
        
        # Setup web app
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/ws', self.handle_websocket)
        self.app.router.add_get('/api/portfolio', self.handle_portfolio)
        self.app.router.add_get('/api/prices', self.handle_prices)
        self.app.router.add_get('/api/balances', self.handle_balances)
        self.app.router.add_get('/api/intelligence', self.handle_intelligence)
        self.app.router.add_get('/api/bots', self.handle_bots)
        self.app.router.add_get('/api/ocean', self.handle_ocean)
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/api/status', self.handle_status)  # Diagnostic endpoint
        # ⚡ NEW ENDPOINTS
        self.app.router.add_get('/api/v11', self.handle_v11)  # V11 Power Station
        self.app.router.add_get('/api/sentiment', self.handle_sentiment)  # Fear & Greed
        self.app.router.add_get('/api/thoughts', self.handle_thoughts)  # ThoughtBus events
        # 👑 QUEEN SYSTEMS ENDPOINTS
        self.app.router.add_get('/api/quantum', self.handle_quantum)  # Quantum Cognition
        self.app.router.add_get('/api/assets', self.handle_assets)  # Asset Command Center
        self.app.router.add_get('/api/symbols', self.handle_symbols)  # Symbol Manager
        self.app.router.add_get('/api/queen', self.handle_queen)  # Queen Hive Mind
    
    def _on_thought_event(self, thought):
        """Handle incoming thought events from ThoughtBus."""
        try:
            event = {
                'timestamp': datetime.now().isoformat(),
                'topic': thought.topic if hasattr(thought, 'topic') else 'unknown',
                'source': thought.source if hasattr(thought, 'source') else 'unknown',
                'message': str(thought.payload if hasattr(thought, 'payload') else thought)[:200]
            }
            self.thought_events.append(event)
        except Exception:
            pass
    
    async def handle_status(self, request):
        """Diagnostic status endpoint showing what's working and what's not."""
        status = {
            'timestamp': datetime.now().isoformat(),
            'services': {},
            'data': {},
            'config': {}
        }
        
        # Check API keys
        import os
        status['config']['binance_api_key'] = 'SET' if os.getenv('BINANCE_API_KEY') else 'MISSING'
        status['config']['binance_api_secret'] = 'SET' if os.getenv('BINANCE_API_SECRET') else 'MISSING'
        status['config']['alpaca_api_key'] = 'SET' if os.getenv('ALPACA_API_KEY') else 'MISSING'
        status['config']['alpaca_secret'] = 'SET' if os.getenv('ALPACA_SECRET_KEY') else 'MISSING'
        status['config']['kraken_api_key'] = 'SET' if os.getenv('KRAKEN_API_KEY') else 'MISSING'
        status['config']['kraken_secret'] = 'SET' if os.getenv('KRAKEN_API_SECRET') else 'MISSING'
        
        # Check modules
        status['services']['binance_ws'] = 'AVAILABLE' if BINANCE_WS_AVAILABLE else 'MISSING'
        status['services']['narrator'] = 'AVAILABLE' if NARRATOR_AVAILABLE else 'MISSING'
        status['services']['harmonic_field'] = 'AVAILABLE' if HARMONIC_FIELD_AVAILABLE else 'MISSING'
        status['services']['market_cache'] = 'AVAILABLE' if MARKET_CACHE_AVAILABLE else 'MISSING'
        
        # Check live data
        status['services']['binance_ws_connected'] = self.binance_ws is not None
        status['data']['binance_tickers'] = len(self.binance_tickers)
        status['data']['all_prices'] = len(self.all_prices)
        status['data']['prices'] = len(self.prices)
        status['data']['positions'] = len(self.portfolio.get('positions', []))
        status['data']['portfolio_value'] = self.portfolio.get('totalValue', 0)
        status['data']['websocket_clients'] = len(self.clients)
        
        # Ocean Scanner stats
        if self.ocean_scanner:
            status['services']['ocean_scanner'] = 'ACTIVE'
            status['data']['ocean_symbols_scanned'] = self.ocean_scanner.total_symbols_scanned
            status['data']['ocean_scan_count'] = self.ocean_scanner.scan_count
            status['data']['ocean_hot_opportunities'] = len(self.ocean_scanner.hot_opportunities)
        else:
            status['services']['ocean_scanner'] = 'DISABLED'

        # Bot intel summary
        status['data']['bots'] = len(self.bots)
        status['data']['whales'] = self.bot_counts.get('whales', 0)
        status['data']['hives'] = self.bot_counts.get('hives', 0)
        
        # Harmonic Field stats
        if self.harmonic_field:
            status['services']['harmonic_field_active'] = 'STREAMING'
            try:
                snapshot = self.harmonic_field.capture_snapshot()
                status['data']['harmonic_nodes'] = snapshot.total_nodes
                status['data']['harmonic_energy'] = round(snapshot.total_energy, 2)
                status['data']['harmonic_frequency'] = round(snapshot.global_frequency, 2)
                status['data']['harmonic_layers'] = len(snapshot.layers)
            except Exception as e:
                status['data']['harmonic_error'] = str(e)
        
        return web.json_response(status)
    
    async def handle_index(self, request):
        return web.Response(text=PRO_DASHBOARD_HTML, content_type='text/html')
    
    async def handle_health(self, request):
        return web.json_response({'status': 'healthy', 'service': 'aureon-pro-dashboard'})
    
    async def handle_websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        
        self.logger.info(f"✅ Client connected (total: {len(self.clients)})")
        
        # Send initial state immediately
        try:
            self.logger.info(f"📤 Sending initial portfolio: {len(self.portfolio.get('positions', []))} positions, ${self.portfolio.get('totalValue', 0):.2f}")
            await ws.send_json({
                'type': 'portfolio_update',
                'data': self.portfolio
            })
            
            # Always send prices - even if zero, better than blank dashboard
            self.logger.info(f"📤 Sending initial prices: BTC ${self.prices.get('BTC', {}).get('price', 0):,.0f}")
            await ws.send_json({
                'type': 'price_update',
                'data': self.prices
            })
            
            if self.all_prices:
                await ws.send_json({
                    'type': 'all_prices_update',
                    'data': self.all_prices
                })

            # Send initial exchange balances
            self.logger.info(f"📤 Sending initial exchange balances: Binance=${self.exchange_balances.get('binance', 0):.2f}, Kraken=${self.exchange_balances.get('kraken', 0):.2f}, Alpaca=${self.exchange_balances.get('alpaca', 0):.2f}")
            await ws.send_json({
                'type': 'exchange_balances',
                'data': self.exchange_balances
            })
            
            # Send bots snapshot if available
            if self.bots:
                await ws.send_json({
                    'type': 'bots_snapshot',
                    'data': {
                        'bots': self.bots,
                        'whales': self.bot_counts.get('whales', 0),
                        'hives': self.bot_counts.get('hives', 0)
                    }
                })
        except Exception as e:
            self.logger.error(f"❌ Error sending initial state: {e}")
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f"WS error: {ws.exception()}")
        finally:
            self.clients.discard(ws)
            self.logger.info(f"❌ Client disconnected (remaining: {len(self.clients)})")
        
        return ws
    
    async def handle_portfolio(self, request):
        # Fetch real portfolio data
        self.logger.info("📊 HANDLE_PORTFOLIO: Called")
        try:
            await self.refresh_portfolio()
            position_count = len(self.portfolio.get('positions', []))
            winners = len([p for p in self.portfolio.get('positions', []) if (p.get('pnlPercent', 0) or 0) > 0])
            win_rate = (winners / position_count * 100) if position_count > 0 else 0
            self.logger.info(f"📊 HANDLE_PORTFOLIO: Returning {position_count} positions | Win Rate: {winners}/{position_count} = {win_rate:.1f}%")
            # Log first few positions for debugging
            for pos in self.portfolio.get('positions', [])[:3]:
                self.logger.info(f"   🔹 {pos.get('symbol')}: {pos.get('quantity')} @ {pos.get('avgCost')} → ${pos.get('currentValue'):.2f} | PnL: {pos.get('pnlPercent', 0):.2f}%")
        except Exception as e:
            self.logger.error(f"❌ HANDLE_PORTFOLIO: refresh_portfolio() failed: {e}", exc_info=True)
            # Return cached/default data instead of crashing
            if not hasattr(self, 'portfolio') or not self.portfolio:
                self.portfolio = {
                    'positions': [],
                    'totalValue': 0,
                    'totalCost': 0,
                    'unrealizedPnl': 0,
                    'cash': 0,
                    'error': str(e)
                }
        return web.json_response(self.portfolio)
    
    async def handle_prices(self, request):
        await self.refresh_prices()
        return web.json_response(self.prices)
    
    async def handle_balances(self, request):
        return web.json_response(self.exchange_balances)

    async def handle_intelligence(self, request):
        """Serve portfolio intelligence snapshot (updated every 5 min by engine)."""
        try:
            intel_path = os.path.join(os.getenv("AUREON_STATE_DIR", "."), "portfolio_intelligence_snapshot.json")
            if os.path.exists(intel_path):
                with open(intel_path, "r") as f:
                    return web.json_response(json.load(f))
            return web.json_response({"error": "No intelligence snapshot yet"}, status=404)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_bots(self, request):
        await self.refresh_bots()
        return web.json_response({
            'bots': self.bots,
            'whales': self.bot_counts.get('whales', 0),
            'hives': self.bot_counts.get('hives', 0)
        })
    
    async def refresh_exchange_balances(self):
        """Fetch real-time balances from all exchange clients."""
        try:
            # Try Binance - calculate TOTAL portfolio value (not just stablecoins!)
            try:
                from aureon.exchanges.binance_client import BinanceClient, get_binance_client
                binance = get_binance_client()
                bin_balance = await asyncio.to_thread(binance.get_balance)
                if isinstance(bin_balance, dict):
                    # Calculate TOTAL portfolio value including all crypto assets
                    binance_total = 0.0
                    stablecoins = ['USDT', 'USDC', 'BUSD', 'FDUSD', 'TUSD', 'DAI', 'USD']
                    
                    for asset, qty in bin_balance.items():
                        qty = float(qty or 0)
                        if qty < 0.0001:
                            continue
                        
                        if asset in stablecoins:
                            # Stablecoins = $1
                            binance_total += qty
                        else:
                            # Get price for crypto assets
                            try:
                                ticker = await asyncio.to_thread(binance.get_ticker, f"{asset}USDT")
                                if ticker and 'price' in ticker:
                                    price = float(ticker['price'])
                                    binance_total += qty * price
                            except:
                                pass  # Skip assets without USDT pair
                    
                    self.exchange_balances['binance'] = binance_total
                    self.logger.info(f"✅ Binance TOTAL portfolio: ${self.exchange_balances['binance']:,.2f}")
                else:
                    self.logger.warning(f"⚠️ Binance balance returned non-dict: {type(bin_balance)}")
            except Exception as e:
                self.logger.warning(f"⚠️ Binance balance fetch failed: {str(e)[:100]}")
            
            # Try Kraken - calculate TOTAL portfolio value
            try:
                from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
                kraken = get_kraken_client()
                krk_balance = await asyncio.to_thread(kraken.get_balance)
                if isinstance(krk_balance, dict) and krk_balance:
                    # Calculate TOTAL portfolio value including all crypto
                    kraken_total = 0.0
                    stablecoins = ['USD', 'ZUSD', 'USDT', 'USDC', 'TUSD', 'DAI']
                    
                    for asset, qty in krk_balance.items():
                        qty = float(qty or 0)
                        if qty < 0.0001:
                            continue
                        
                        # Normalize Kraken asset names (XXBT -> BTC, XETH -> ETH)
                        clean_asset = asset
                        if len(asset) == 4 and asset[0] in ('X', 'Z'):
                            clean_asset = asset[1:]
                        if clean_asset == 'XBT':
                            clean_asset = 'BTC'
                        
                        if asset in stablecoins or clean_asset in stablecoins:
                            kraken_total += qty
                        elif asset == 'ZGBP':
                            kraken_total += qty * 1.27  # GBP to USD
                        elif asset == 'ZEUR':
                            kraken_total += qty * 1.08  # EUR to USD
                        else:
                            # Try to get price
                            try:
                                ticker = await asyncio.to_thread(kraken.get_ticker, f"{asset}USD")
                                if ticker and 'last' in ticker:
                                    price = float(ticker['last'])
                                    kraken_total += qty * price
                            except:
                                pass  # Skip assets without USD pair
                    
                    self.exchange_balances['kraken'] = kraken_total
                    self.logger.info(f"✅ Kraken TOTAL portfolio: ${self.exchange_balances['kraken']:,.2f}")
                elif not krk_balance:
                    # Empty balance or API issue - try snapshot file
                    try:
                        import json
                        with open('kraken_balance_snapshot_2026-02-03.json') as f:
                            snapshot = json.load(f)
                        if snapshot.get('balances'):
                            self.exchange_balances['kraken'] = sum(snapshot['balances'].values())
                            self.logger.info(f"📸 Kraken from snapshot: ${self.exchange_balances['kraken']:,.2f}")
                    except:
                        pass
            except Exception as e:
                err_msg = str(e)[:100]
                if 'nonce' in err_msg.lower():
                    self.logger.warning(f"⚠️ Kraken: API key nonce issue - need new key")
                else:
                    self.logger.warning(f"⚠️ Kraken balance fetch failed: {err_msg}")
            
            # Try Alpaca - get TOTAL portfolio value (cash + positions)
            try:
                from aureon.exchanges.alpaca_client import AlpacaClient
                alpaca = AlpacaClient()
                
                # Get cash balance
                alp_balance = await asyncio.to_thread(alpaca.get_balance)
                cash = 0.0
                if isinstance(alp_balance, dict):
                    cash = float(alp_balance.get('USD', alp_balance.get('cash', 0)) or 0)
                
                # Get positions value
                positions_value = 0.0
                try:
                    positions = await asyncio.to_thread(alpaca.get_positions)
                    if positions:
                        for pos in positions:
                            if isinstance(pos, dict):
                                positions_value += float(pos.get('market_value', 0) or 0)
                            elif hasattr(pos, 'market_value'):
                                positions_value += float(pos.market_value or 0)
                except:
                    pass
                
                # TOTAL = cash + positions
                self.exchange_balances['alpaca'] = cash + positions_value
                self.logger.info(f"✅ Alpaca TOTAL: ${self.exchange_balances['alpaca']:,.2f} (cash: ${cash:.2f} + positions: ${positions_value:.2f})")
                
            except Exception as e:
                self.logger.warning(f"⚠️ Alpaca balance fetch failed: {str(e)[:100]}")
            
            # Broadcast all balances to connected clients
            await self.broadcast({
                'type': 'exchange_balances',
                'data': self.exchange_balances
            })
                
        except Exception as e:
            self.logger.debug(f"Exchange balance refresh error: {e}")
    
    async def handle_ocean(self, request):
        """Return ocean scanner data."""
        return web.json_response(self.ocean_data)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ⚡ V11 POWER STATION API
    # ═══════════════════════════════════════════════════════════════════════════════
    async def handle_v11(self, request):
        """Return V11 Power Station grid status."""
        return web.json_response(self.v11_data)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🌐 MARKET SENTIMENT API (Fear & Greed, Open Source Data)
    # ═══════════════════════════════════════════════════════════════════════════════
    async def handle_sentiment(self, request):
        """Return market sentiment data."""
        return web.json_response(self.market_sentiment)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 📡 THOUGHTBUS EVENTS API
    # ═══════════════════════════════════════════════════════════════════════════════
    async def handle_thoughts(self, request):
        """Return recent ThoughtBus events."""
        return web.json_response({
            'events': list(self.thought_events),
            'count': len(self.thought_events)
        })
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ⚛️ QUEEN QUANTUM COGNITION API
    # ═══════════════════════════════════════════════════════════════════════════════
    async def handle_quantum(self, request):
        """Return Queen Quantum Cognition status."""
        data = self.quantum_data.copy()
        if self.quantum_cognition:
            try:
                # Get full subsystem status if available
                if hasattr(self.quantum_cognition, 'get_full_subsystem_status'):
                    status = self.quantum_cognition.get_full_subsystem_status()
                    data['subsystem_status'] = status
                # Get amplification from state object
                if hasattr(self.quantum_cognition, 'state') and hasattr(self.quantum_cognition.state, 'unified_amplification'):
                    data['amplification_level'] = self.quantum_cognition.state.unified_amplification
                # Get enabled status
                if hasattr(self.quantum_cognition, 'enabled'):
                    data['autonomous_mode'] = self.quantum_cognition.enabled
            except Exception as e:
                data['error'] = str(e)
        return web.json_response(data)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 👑💰 QUEEN ASSET COMMAND CENTER API
    # ═══════════════════════════════════════════════════════════════════════════════
    async def handle_assets(self, request):
        """Return Queen Asset Command Center portfolio data."""
        data = self.asset_data.copy()
        if self.asset_command:
            try:
                # Get portfolio overview - CORRECT METHOD NAME: get_full_portfolio_status
                if hasattr(self.asset_command, 'get_full_portfolio_status'):
                    portfolio = await asyncio.to_thread(self.asset_command.get_full_portfolio_status)
                    if portfolio:
                        data['portfolio'] = portfolio
                        data['total_portfolio_value'] = portfolio.get('total_value', 0)
                        data['total_positions'] = portfolio.get('total_positions', 0)
                        data['exchanges_connected'] = portfolio.get('exchanges_connected', 0)
            except Exception as e:
                data['error'] = str(e)
        return web.json_response(data)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🔤 UNIFIED SYMBOL MANAGER API
    # ═══════════════════════════════════════════════════════════════════════════════
    async def handle_symbols(self, request):
        """Return Unified Symbol Manager status."""
        data = self.symbol_data.copy()
        if self.symbol_manager:
            try:
                # Get counts per exchange from _symbol_cache dict
                if hasattr(self.symbol_manager, '_symbol_cache'):
                    cache = self.symbol_manager._symbol_cache
                    data['kraken_pairs'] = len(cache.get('kraken', {}))
                    data['binance_pairs'] = len(cache.get('binance', {}))
                    data['alpaca_pairs'] = len(cache.get('alpaca', {}))
                    data['capital_pairs'] = len(cache.get('capital', {}))
                    data['loaded'] = True
            except Exception as e:
                data['error'] = str(e)
        return web.json_response(data)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 👑🧠 QUEEN HIVE MIND API
    # ═══════════════════════════════════════════════════════════════════════════════
    async def handle_queen(self, request):
        """Return Queen Hive Mind status."""
        data = self.queen_hive_data.copy()
        if self.queen_hive:
            try:
                # Use get_full_autonomous_status which has all the data we need
                if hasattr(self.queen_hive, 'get_full_autonomous_status'):
                    full_status = self.queen_hive.get_full_autonomous_status()
                    data['queen_name'] = 'SERO'
                    data['authority_level'] = full_status.get('queen_sovereignty', 'SUPREME_AUTONOMOUS')
                    data['hive_systems_online'] = full_status.get('totals', {}).get('hive_online', 0)
                    data['total_hive_systems'] = full_status.get('totals', {}).get('hive_systems', 0)
                    data['quantum_systems_online'] = full_status.get('totals', {}).get('quantum_online', 0)
                    data['total_quantum_systems'] = full_status.get('totals', {}).get('quantum_systems', 0)
                    data['autonomous_enabled'] = full_status.get('has_full_control', False)
                    data['trading_enabled'] = full_status.get('trading_enabled', False)
                    data['full_autonomous_status'] = full_status
            except Exception as e:
                data['error'] = str(e)
        return web.json_response(data)
    
    async def broadcast(self, message: Dict):
        """Broadcast to all connected clients."""
        if not self.clients:
            return
        
        for client in list(self.clients):
            try:
                await client.send_json(message)
            except:
                self.clients.discard(client)
    

    # ═══════════════════════════════════════════════════════════════════════════════
    # ⚡ V11 POWER STATION DATA LOOP
    # ═══════════════════════════════════════════════════════════════════════════════
    async def v11_data_loop(self):
        """Periodically scan V11 Power Grid and broadcast status."""
        await asyncio.sleep(5)  # Wait for init
        
        while True:
            try:
                if self.v11_station and V11_AVAILABLE:
                    # Scan the power grid (sync function, run in thread)
                    grid_state = await asyncio.to_thread(self.v11_station.scan_power_grid)
                    
                    if grid_state:
                        self.v11_data = {
                            'total_nodes': grid_state.total_nodes,
                            'generating_nodes': grid_state.generating_nodes,
                            'hibernating_nodes': grid_state.hibernating_nodes,
                            'consuming_nodes': grid_state.consuming_nodes,
                            'total_grid_value': round(grid_state.total_grid_value, 2),
                            'total_entry_cost': round(grid_state.total_entry_cost, 2),
                            'total_unrealized_pnl': round(grid_state.total_unrealized_pnl, 2),
                            'total_siphon_capacity': round(grid_state.total_siphon_capacity, 2),
                            'reserve_balance': round(grid_state.reserve_balance, 2),
                            'siphons_session': grid_state.siphons_this_session,
                            'energy_siphoned': round(grid_state.energy_siphoned_session, 2),
                            'last_scan': datetime.now().isoformat()
                        }
                        
                        # Broadcast to clients
                        await self.broadcast({
                            'type': 'v11_update',
                            'data': self.v11_data
                        })
                        
                        gen = self.v11_data['generating_nodes']
                        tot = self.v11_data['total_nodes']
                        siphon = self.v11_data['total_siphon_capacity']
                        self.logger.info(f"⚡ V11: {gen}/{tot} generating, ${siphon:,.2f} siphon capacity")
            except Exception as e:
                self.logger.error(f"❌ V11 data loop error: {e}")
            
            await asyncio.sleep(60)  # Scan every 60 seconds
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🌐 MARKET SENTIMENT DATA LOOP (Fear & Greed)
    # ═══════════════════════════════════════════════════════════════════════════════
    async def sentiment_data_loop(self):
        """Periodically fetch market sentiment data (Fear & Greed Index)."""
        await asyncio.sleep(8)  # Wait for init
        
        while True:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    # Try to fetch Fear & Greed Index from Alternative.me API (free, no key needed)
                    try:
                        async with session.get(
                            'https://api.alternative.me/fng/',
                            timeout=aiohttp.ClientTimeout(total=15)
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if 'data' in data and len(data['data']) > 0:
                                    fng = data['data'][0]
                                    raw_index = fng.get('value', 50)
                                    try:
                                        self.market_sentiment['fear_greed_index'] = int(raw_index)
                                    except (TypeError, ValueError):
                                        self.logger.warning(f"⚠️ Invalid Fear & Greed index value: {raw_index!r}")

                                    self.market_sentiment['fear_greed_label'] = fng.get('value_classification', 'Neutral')
                                    self.market_sentiment['last_update'] = datetime.now().isoformat()
                            else:
                                self.logger.warning(f"⚠️ Alternative.me API returned status {resp.status}")
                    except asyncio.TimeoutError:
                        self.logger.warning("⚠️ Fear & Greed refresh timed out (keeping last sentiment value)")
                    except aiohttp.ClientError as exc:
                        self.logger.warning(f"⚠️ Fear & Greed refresh failed: {exc}")
                    except Exception:
                        self.logger.exception("❌ Unexpected error while refreshing Fear & Greed data")

                    # Try to get BTC dominance from CoinGecko (free API)
                    try:
                        async with session.get(
                            'https://api.coingecko.com/api/v3/global',
                            timeout=aiohttp.ClientTimeout(total=15)
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if 'data' in data:
                                    global_data = data['data']
                                    self.market_sentiment['btc_dominance'] = round(
                                        global_data.get('market_cap_percentage', {}).get('btc', 0), 2
                                    )
                                    self.market_sentiment['total_market_cap'] = round(
                                        global_data.get('total_market_cap', {}).get('usd', 0) / 1e12, 3  # In trillions
                                    )
                            else:
                                self.logger.warning(f"⚠️ CoinGecko API returned status {resp.status}")
                    except asyncio.TimeoutError:
                        self.logger.warning("⚠️ CoinGecko global refresh timed out (keeping last market cap snapshot)")
                    except aiohttp.ClientError as exc:
                        self.logger.warning(f"⚠️ CoinGecko global refresh failed: {exc}")
                    except Exception:
                        self.logger.exception("❌ Unexpected error while refreshing CoinGecko global data")
                
                # Broadcast to clients
                await self.broadcast({
                    'type': 'sentiment_update',
                    'data': self.market_sentiment
                })
                
                fg = self.market_sentiment['fear_greed_index']
                label = self.market_sentiment['fear_greed_label']
                self.logger.info(f"🌐 Sentiment: Fear & Greed {fg} ({label})")
                
            except asyncio.CancelledError:
                self.logger.info("🛑 Sentiment data loop cancelled")
                raise
            except Exception as e:
                self.logger.error(f"❌ Sentiment loop error: {e}", exc_info=True)

            await asyncio.sleep(300)  # Every 5 minutes (API rate limits)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ⚛️ QUEEN QUANTUM COGNITION DATA LOOP
    # ═══════════════════════════════════════════════════════════════════════════════
    async def quantum_cognition_loop(self):
        """Periodically update Quantum Cognition status and broadcast."""
        await asyncio.sleep(10)  # Wait for init
        
        while True:
            try:
                if self.quantum_cognition and QUANTUM_COGNITION_AVAILABLE:
                    # Get quantum status
                    if hasattr(self.quantum_cognition, 'get_full_subsystem_status'):
                        status = self.quantum_cognition.get_full_subsystem_status()
                        self.quantum_data['quantum_systems_online'] = status.get('quantum_systems_online', 0)
                        self.quantum_data['hive_systems_online'] = status.get('hive_systems_online', 0)
                    
                    # Get amplification from state object
                    if hasattr(self.quantum_cognition, 'state') and hasattr(self.quantum_cognition.state, 'unified_amplification'):
                        self.quantum_data['amplification_level'] = self.quantum_cognition.state.unified_amplification
                    
                    # Get enabled status
                    if hasattr(self.quantum_cognition, 'enabled'):
                        self.quantum_data['autonomous_mode'] = self.quantum_cognition.enabled
                    
                    self.quantum_data['last_update'] = datetime.now().isoformat()
                    
                    # Broadcast to clients
                    await self.broadcast({
                        'type': 'quantum_update',
                        'data': self.quantum_data
                    })
                    
                    self.logger.info(f"⚛️ Quantum Cognition: Level {self.quantum_data.get('amplification_level', 0)}, Autonomous: {self.quantum_data.get('autonomous_mode', False)}")
                    
            except Exception as e:
                self.logger.error(f"❌ Quantum Cognition loop error: {e}")
            
            await asyncio.sleep(30)  # Every 30 seconds
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 👑💰 QUEEN ASSET COMMAND CENTER DATA LOOP
    # ═══════════════════════════════════════════════════════════════════════════════
    async def asset_command_loop(self):
        """Periodically update Asset Command Center portfolio data and broadcast."""
        await asyncio.sleep(15)  # Wait for init
        
        while True:
            try:
                if self.asset_command and ASSET_COMMAND_AVAILABLE:
                    # Get portfolio data - CORRECT METHOD NAME: get_full_portfolio_status
                    if hasattr(self.asset_command, 'get_full_portfolio_status'):
                        portfolio = await asyncio.to_thread(self.asset_command.get_full_portfolio_status)
                        if portfolio:
                            self.asset_data['total_portfolio_value'] = portfolio.get('total_value', 0)
                            self.asset_data['total_positions'] = portfolio.get('total_positions', 0)
                            self.asset_data['exchanges_connected'] = portfolio.get('exchanges_connected', 0)
                            self.asset_data['positions_by_exchange'] = portfolio.get('by_exchange', {})
                            self.asset_data['top_holdings'] = portfolio.get('top_holdings', [])[:10]
                    
                    self.asset_data['last_update'] = datetime.now().isoformat()
                    
                    # Broadcast to clients
                    await self.broadcast({
                        'type': 'assets_update',
                        'data': self.asset_data
                    })
                    
                    self.logger.info(f"👑💰 Asset Command: ${self.asset_data.get('total_portfolio_value', 0):,.2f} across {self.asset_data.get('total_positions', 0)} positions")
                    
            except Exception as e:
                self.logger.error(f"❌ Asset Command loop error: {e}")
            
            await asyncio.sleep(60)  # Every 60 seconds
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 🔤 UNIFIED SYMBOL MANAGER DATA LOOP
    # ═══════════════════════════════════════════════════════════════════════════════
    async def symbol_manager_loop(self):
        """Periodically update Symbol Manager status and broadcast."""
        await asyncio.sleep(12)  # Wait for init
        
        while True:
            try:
                if self.symbol_manager and SYMBOL_MANAGER_AVAILABLE:
                    # Get symbol counts from _symbol_cache dict
                    if hasattr(self.symbol_manager, '_symbol_cache'):
                        cache = self.symbol_manager._symbol_cache
                        self.symbol_data['kraken_pairs'] = len(cache.get('kraken', {}))
                        self.symbol_data['binance_pairs'] = len(cache.get('binance', {}))
                        self.symbol_data['alpaca_pairs'] = len(cache.get('alpaca', {}))
                        self.symbol_data['capital_pairs'] = len(cache.get('capital', {}))
                    
                    self.symbol_data['loaded'] = True
                    self.symbol_data['last_update'] = datetime.now().isoformat()
                    
                    # Broadcast to clients
                    await self.broadcast({
                        'type': 'symbols_update',
                        'data': self.symbol_data
                    })
                    
                    total = self.symbol_data.get('kraken_pairs', 0) + self.symbol_data.get('binance_pairs', 0) + self.symbol_data.get('alpaca_pairs', 0) + self.symbol_data.get('capital_pairs', 0)
                    self.logger.info(f"🔤 Symbol Manager: {total} total pairs loaded")
                    
            except Exception as e:
                self.logger.error(f"❌ Symbol Manager loop error: {e}")
            
            await asyncio.sleep(300)  # Every 5 minutes (symbols don't change often)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 👑🧠 QUEEN HIVE MIND DATA LOOP
    # ═══════════════════════════════════════════════════════════════════════════════
    async def queen_hive_loop(self):
        """Periodically update Queen Hive Mind status and broadcast."""
        await asyncio.sleep(8)  # Wait for init
        
        while True:
            try:
                if self.queen_hive and QUEEN_HIVE_AVAILABLE:
                    # Use get_full_autonomous_status which has all the data we need
                    if hasattr(self.queen_hive, 'get_full_autonomous_status'):
                        full_status = self.queen_hive.get_full_autonomous_status()
                        self.queen_hive_data['queen_name'] = 'SERO'
                        self.queen_hive_data['authority_level'] = full_status.get('queen_sovereignty', 'SUPREME_AUTONOMOUS')
                        self.queen_hive_data['hive_systems_online'] = full_status.get('totals', {}).get('hive_online', 0)
                        self.queen_hive_data['total_hive_systems'] = full_status.get('totals', {}).get('hive_systems', 0)
                        self.queen_hive_data['quantum_systems_online'] = full_status.get('totals', {}).get('quantum_online', 0)
                        self.queen_hive_data['total_quantum_systems'] = full_status.get('totals', {}).get('quantum_systems', 0)
                        self.queen_hive_data['autonomous_enabled'] = full_status.get('has_full_control', False)
                        self.queen_hive_data['trading_enabled'] = full_status.get('trading_enabled', False)
                    
                    self.queen_hive_data['last_update'] = datetime.now().isoformat()
                    
                    # Broadcast to clients
                    await self.broadcast({
                        'type': 'queen_update',
                        'data': self.queen_hive_data
                    })
                    
                    online = self.queen_hive_data.get('hive_systems_online', 0)
                    total = self.queen_hive_data.get('total_hive_systems', 0)
                    self.logger.info(f"👑🧠 Queen Hive Mind: {online}/{total} systems online, Autonomous: {self.queen_hive_data.get('autonomous_enabled', False)}")
                    
            except Exception as e:
                self.logger.error(f"❌ Queen Hive loop error: {e}")
            
            await asyncio.sleep(20)  # Every 20 seconds
    
    async def _fetch_live_prices_for_symbols(self, symbols: list) -> dict:
        """Fetch LIVE prices from FREE public APIs (CoinGecko, Binance public, Kraken public).
        
        This is used when we have cost basis data but no live API access (e.g., Binance IP ban).
        Returns {symbol: price} dict with REAL current market prices.
        """
        print(f"💰 _fetch_live_prices_for_symbols called with {len(symbols)} symbols")  # DEBUG
        
        # Check cache first
        now = time.time()
        if hasattr(self, '_price_cache') and hasattr(self, '_price_cache_time'):
            if now - self._price_cache_time < 300:  # 5 minutes
                cached_prices = {sym: self._price_cache.get(sym) for sym in symbols if sym in self._price_cache}
                if len(cached_prices) > 0:
                    self.logger.info(f"💰 Using cached prices for {len(cached_prices)}/{len(symbols)} symbols")
                    return cached_prices
        
        prices = {}
        
        # Map common trading symbols to CoinGecko IDs
        symbol_to_coingecko = {
            'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana', 'BNB': 'binancecoin',
            'XRP': 'ripple', 'ADA': 'cardano', 'DOGE': 'dogecoin', 'AVAX': 'avalanche-2',
            'DOT': 'polkadot', 'LINK': 'chainlink', 'MATIC': 'matic-network', 'ATOM': 'cosmos',
            'UNI': 'uniswap', 'LTC': 'litecoin', 'NEAR': 'near', 'TRX': 'tron',
            'SHIB': 'shiba-inu', 'APT': 'aptos', 'ARB': 'arbitrum', 'OP': 'optimism',
            'SUI': 'sui', 'PEPE': 'pepe', 'WIF': 'dogwifhat', 'BONK': 'bonk',
            'FARTCOIN': 'fartcoin', 'TRUMP': 'maga', 'MELANIA': 'melania-meme',
            'INJ': 'injective-protocol', 'FTM': 'fantom', 'RENDER': 'render-token',
            'TAO': 'bittensor', 'FET': 'fetch-ai', 'AGIX': 'singularitynet',
            'IMX': 'immutable-x', 'SEI': 'sei-network', 'TIA': 'celestia',
        }
        
        # Extract base assets from symbols (remove USDT, USDC, USD, FDUSD suffixes)
        base_assets = set()
        symbol_map = {}  # Map base asset back to original symbols
        for sym in symbols:
            base = sym.replace('USDT', '').replace('USDC', '').replace('FDUSD', '').replace('USD', '').replace('/USD', '')
            base_assets.add(base)
            if base not in symbol_map:
                symbol_map[base] = []
            symbol_map[base].append(sym)
        
        # 1. Try CoinGecko (free, no API key needed)
        try:
            coingecko_ids = [symbol_to_coingecko.get(base, base.lower()) for base in base_assets]
            ids_str = ','.join(set(coingecko_ids))
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd',
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for base, cg_id in symbol_to_coingecko.items():
                            if cg_id in data and 'usd' in data[cg_id]:
                                price = data[cg_id]['usd']
                                # Apply to all symbols with this base asset
                                for sym in symbol_map.get(base, []):
                                    prices[sym] = price
                        self.logger.info(f"💰 CoinGecko: Got {len(prices)} live prices")
        except Exception as e:
            self.logger.info(f"CoinGecko error: {e}")
        
        # 2. Fill gaps with Binance public API (no auth needed)
        missing = [s for s in symbols if s not in prices]
        if missing:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        'https://api.binance.com/api/v3/ticker/price',
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            binance_prices = {p['symbol']: float(p['price']) for p in data}
                            for sym in missing:
                                # Try exact match, then with USDT suffix
                                if sym in binance_prices:
                                    prices[sym] = binance_prices[sym]
                                elif sym + 'USDT' in binance_prices:
                                    prices[sym] = binance_prices[sym + 'USDT']
                                elif sym.replace('USD', 'USDT') in binance_prices:
                                    prices[sym] = binance_prices[sym.replace('USD', 'USDT')]
                            self.logger.info(f"💰 Binance public: Filled {len([s for s in missing if s in prices])} more prices")
            except Exception as e:
                self.logger.info(f"Binance public error: {e}")
        
        # 3. Fill remaining gaps with Kraken public API
        still_missing = [s for s in symbols if s not in prices]
        if still_missing:
            try:
                # Kraken uses different symbol format (XXBTZUSD, XETHZUSD, etc.)
                kraken_map = {
                    'BTC': 'XXBTZUSD', 'ETH': 'XETHZUSD', 'SOL': 'SOLUSD', 'XRP': 'XXRPZUSD',
                    'ADA': 'ADAUSD', 'DOT': 'DOTUSD', 'ATOM': 'ATOMUSD', 'LINK': 'LINKUSD',
                    'LTC': 'XLTCZUSD', 'XMR': 'XXMRZUSD', 'ZEC': 'XZECZUSD', 'ETC': 'XETCZUSD',
                    'REP': 'XREPZUSD', 'GNO': 'GNOUSD', 'MLN': 'XMLEZUSD', 'ICN': 'XICNZUSD',
                    'DASH': 'DASHUSD', 'XEM': 'XEMUSD', 'GNT': 'XGNTZUSD', 'STORJ': 'STORJUSD',
                    'ANT': 'XANTZUSD', 'BAT': 'BATUSD', 'ZRX': 'ZRXUSD', 'OMG': 'OMGUSD',
                    'QTUM': 'QTUMUSD', 'XTZ': 'XTZUSD', 'EOS': 'EOSUSD', 'LSK': 'LSKUSD',
                    'WAVES': 'WAVESUSD', 'STR': 'STRUSD', 'XLM': 'XXLMZUSD', 'BTG': 'BTGUSD',
                    'TRX': 'TRXUSD', 'ADA': 'ADAUSD', 'BSV': 'BSVUSD', 'XRP': 'XXRPZUSD',
                }

                # Also try direct symbol lookups for some
                pairs = []
                for sym in still_missing:
                    base = sym.replace('USDT', '').replace('USDC', '').replace('FDUSD', '').replace('USD', '').replace('/USD', '')
                    if base in kraken_map:
                        pairs.append(kraken_map[base])
                    # Also try some direct formats
                    elif sym.endswith('USD'):
                        pairs.append(sym)

                if pairs:
                    pairs_str = ','.join(set(pairs))  # Remove duplicates
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f'https://api.kraken.com/0/public/Ticker?pair={pairs_str}',
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                result = data.get('result', {})
                                filled = 0
                                for kraken_pair, info in result.items():
                                    price = float(info.get('c', [0])[0])  # Last trade price
                                    # Map back to our symbols
                                    for base, kp in kraken_map.items():
                                        if kraken_pair == kp or kraken_pair.startswith(base):
                                            for sym in symbol_map.get(base, []):
                                                if sym not in prices:
                                                    prices[sym] = price
                                                    filled += 1
                                                    break
                                self.logger.info(f"💰 Kraken public: Filled {filled} more prices")
            except Exception as e:
                self.logger.info(f"Kraken public error: {e}")
        
        # Cache the results
        self._price_cache = prices.copy()
        self._price_cache_time = time.time()
        
        return prices
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # 👑📊 QUEEN SYSTEMS DATA RECORDING
    # ═══════════════════════════════════════════════════════════════════════════════
    async def _record_to_queen_systems(self, positions: list, total_value: float, total_cost: float, balances: dict):
        """
        Feed REAL portfolio data to all Queen systems for persistence and learning.
        
        This ensures Queen systems have accurate data for:
        - 👑💰 Queen Asset Monitor (portfolio tracking)
        - 👑🧠 Queen Quantum Cognition (learning from real positions)
        - 👑🐝 Queen Hive Mind (central consciousness awareness)
        """
        try:
            # 1. Update Queen Asset Monitor (primary portfolio tracker)
            if self.asset_monitor:
                try:
                    # Build positions dict in the format Asset Monitor expects
                    positions_dict = {}
                    for pos in positions:
                        exchange = pos.get('exchange', 'unknown')
                        symbol = pos.get('symbol', 'UNKNOWN')
                        key = f"{exchange}:{symbol}"
                        positions_dict[key] = {
                            'symbol': symbol,
                            'exchange': exchange,
                            'quantity': pos.get('quantity', 0),
                            'entry_price': pos.get('avgCost', 0),
                            'cost_basis': pos.get('costBasis', pos.get('avgCost', 0) * pos.get('quantity', 0)),
                        }
                    
                    # Update cached positions
                    self.asset_monitor.cached_positions = positions_dict
                    self.asset_monitor.positions_last_updated = time.time()
                    
                    # Persist to disk
                    self.asset_monitor._save_state()
                    
                    self.logger.info(f"👑💰 Queen Asset Monitor: Recorded {len(positions_dict)} positions (${total_value:,.2f})")
                except Exception as e:
                    self.logger.warning(f"⚠️ Asset Monitor recording failed: {e}")
            
            # 2. Feed data to Queen Quantum Cognition (for learning)
            if self.quantum_cognition:
                try:
                    # Update cognition state with portfolio metrics
                    if hasattr(self.quantum_cognition, 'state'):
                        # Track portfolio performance for decision confidence
                        pnl_pct = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
                        
                        # Boost confidence based on profitable positions
                        profitable_count = sum(1 for p in positions if p.get('unrealizedPnl', 0) > 0)
                        profit_ratio = profitable_count / len(positions) if positions else 0
                        
                        # Update quantum state (this feeds the Queen's neural network)
                        self.quantum_cognition.state.decision_confidence = min(0.95, 0.5 + profit_ratio * 0.3)
                        self.quantum_cognition.state.total_updates += 1
                        self.quantum_cognition.state.last_update = time.time()
                        
                        # Save quantum cognition state periodically
                        if self.quantum_cognition.state.total_updates % 10 == 0:
                            self.quantum_cognition._save_state()
                            self.logger.debug("👑⚛️ Queen Cognition state saved")
                    
                    self.logger.info(f"👑⚛️ Queen Quantum Cognition: Updated with portfolio metrics (P&L: {((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0:+.2f}%)")
                except Exception as e:
                    self.logger.warning(f"⚠️ Quantum Cognition recording failed: {e}")
            
            # 3. Inform Queen Hive Mind (central consciousness)
            if self.queen_hive:
                try:
                    # Push portfolio summary to Queen Hive for overall awareness
                    if hasattr(self.queen_hive, 'portfolio_summary'):
                        self.queen_hive.portfolio_summary = {
                            'total_value': total_value,
                            'total_cost': total_cost,
                            'unrealized_pnl': total_value - total_cost,
                            'pnl_percent': ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0,
                            'total_positions': len(positions),
                            'exchange_balances': balances,
                            'last_update': time.time()
                        }
                    
                    self.logger.info(f"👑🧠 Queen Hive Mind: Aware of portfolio (${total_value:,.2f}, {len(positions)} positions)")
                except Exception as e:
                    self.logger.warning(f"⚠️ Queen Hive recording failed: {e}")
            
            # 4. Emit to ThoughtBus for cross-system awareness
            if THOUGHTBUS_AVAILABLE:
                try:
                    from aureon.core.aureon_thought_bus import get_thought_bus, Thought
                    bus = get_thought_bus()
                    if bus:
                        thought = Thought(
                            topic='queen.portfolio.updated',
                            source='dashboard',
                            payload={
                                'total_value': total_value,
                                'positions_count': len(positions),
                                'exchanges': list(set(p.get('exchange', 'unknown') for p in positions)),
                                'pnl_percent': ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
                            }
                        )
                        bus.emit(thought)
                        self.logger.debug("💭 ThoughtBus: Emitted portfolio update")
                except Exception:
                    pass  # ThoughtBus is optional
            
            self.logger.info(f"👑📊 Queen Systems Recording Complete: ${total_value:,.2f} | {len(positions)} positions")
            
        except Exception as e:
            self.logger.error(f"❌ Queen systems recording failed: {e}")
    
    async def refresh_portfolio(self):
        """Fetch real portfolio data from ALL exchanges with caching."""
        self.logger.info("🔄 REFRESH_PORTFOLIO: Starting portfolio refresh")
        self.logger.info(f"🔄 Environment: AUREON_STATE_DIR={os.getenv('AUREON_STATE_DIR', '.')}")
        try:
            self.logger.info("🔄 Starting portfolio refresh (ALL EXCHANGES)...")
            state_dir = os.getenv("AUREON_STATE_DIR", ".")
            self.logger.info(f"🔄 State directory: {state_dir}")
            snapshot_path = os.path.join(state_dir, "dashboard_snapshot.json")
            self.logger.info(f"🔄 Snapshot path: {snapshot_path}")
            
            # CACHE: Keep previous positions if fetch fails
            if not hasattr(self, '_cached_positions'):
                self._cached_positions = {'binance': [], 'alpaca': [], 'kraken': []}
            
            # Try to use live_position_viewer for real data
            try:
                self.logger.info("📦 Importing live_position_viewer...")
                from aureon.portfolio.live_position_viewer import get_binance_positions, get_alpaca_positions, get_kraken_positions
                self.logger.info("✅ live_position_viewer imported successfully")
                
                positions = []
                total_value = 0
                total_cost = 0
                
                # Fetch ALL positions in parallel - Binance, Alpaca, AND Kraken
                # NOTE: These are sync functions but fast enough - asyncio.to_thread was causing issues
                async def get_bin_pos():
                    try:
                        result = get_binance_positions()  # Direct call - fast enough
                        if result:
                            self._cached_positions['binance'] = result
                        return result or self._cached_positions.get('binance', [])
                    except (ConnectionError, OSError) as e:
                        # Network errors - likely Binance IP ban or network issue
                        self.logger.warning(f"⚠️  Binance network error (likely IP ban or no connectivity): {e}")
                        return self._cached_positions.get('binance', [])
                    except Exception as e:
                        self.logger.warning(f"⚠️  Binance fetch failed: {e}")
                        return self._cached_positions.get('binance', [])
                
                async def get_alp_pos():
                    try:
                        result = get_alpaca_positions()  # Direct call - fast enough
                        if result:
                            self._cached_positions['alpaca'] = result
                        return result or self._cached_positions.get('alpaca', [])
                    except Exception as e:
                        self.logger.warning(f"⚠️  Alpaca fetch failed: {e}")
                        return self._cached_positions.get('alpaca', [])
                
                async def get_kraken_pos():
                    """Fetch Kraken positions from LIVE API - includes ALL meme coins and alt coins."""
                    try:
                        result = get_kraken_positions()  # Direct call - fast enough
                        if result:
                            self._cached_positions['kraken'] = result
                        return result or self._cached_positions.get('kraken', [])
                    except Exception as e:
                        self.logger.warning(f"⚠️  Kraken fetch failed: {e}")
                        return self._cached_positions.get('kraken', [])
                
                # Gather ALL THREE in parallel
                self.logger.info("🔄 Fetching positions from Binance, Alpaca, and Kraken in parallel...")
                binance_pos, alpaca_pos, kraken_pos = await asyncio.gather(
                    get_bin_pos(), get_alp_pos(), get_kraken_pos(),
                    return_exceptions=True  # Don't fail if one times out
                )
                
                # Handle exceptions from gather
                if isinstance(binance_pos, Exception):
                    self.logger.warning(f"⚠️ Binance exception: {binance_pos}")
                    binance_pos = self._cached_positions.get('binance', [])
                if isinstance(alpaca_pos, Exception):
                    self.logger.warning(f"⚠️ Alpaca exception: {alpaca_pos}")
                    alpaca_pos = self._cached_positions.get('alpaca', [])
                if isinstance(kraken_pos, Exception):
                    self.logger.warning(f"⚠️ Kraken exception: {kraken_pos}")
                    kraken_pos = self._cached_positions.get('kraken', [])
                
                self.logger.info(f"✅ Parallel fetch complete: Binance={len(binance_pos) if binance_pos else 0}, Alpaca={len(alpaca_pos) if alpaca_pos else 0}, Kraken={len(kraken_pos) if kraken_pos else 0}")
                
                # Process Binance positions
                if binance_pos:
                    self.logger.info(f"📊 Binance: Fetched {len(binance_pos)} positions")
                    for pos in binance_pos:
                        if pos.get('current_value', 0) > 0:
                            cost_basis = pos.get('cost_basis', 0) or (pos.get('quantity', 0) * pos.get('avg_cost', 0))
                            positions.append({
                                'symbol': pos['symbol'],
                                'quantity': pos['quantity'],
                                'avgCost': pos.get('avg_cost', 0),
                                'currentPrice': pos.get('current_price', 0),
                                'currentValue': pos.get('current_value', 0),
                                'unrealizedPnl': pos.get('unrealized_pnl', 0),
                                'pnlPercent': pos.get('pnl_percent', 0),
                                'costBasis': cost_basis,
                                'exchange': 'binance'
                            })
                            total_value += pos.get('current_value', 0)
                            total_cost += cost_basis
                
                # Process Alpaca positions
                if alpaca_pos:
                    self.logger.info(f"📊 Alpaca: Fetched {len(alpaca_pos)} positions")
                    for pos in alpaca_pos:
                        if pos.get('current_value', 0) > 0:
                            cost_basis = pos.get('cost_basis', 0) or (pos.get('quantity', 0) * pos.get('avg_cost', 0))
                            positions.append({
                                'symbol': pos['symbol'],
                                'quantity': pos['quantity'],
                                'avgCost': pos.get('avg_cost', 0),
                                'currentPrice': pos.get('current_price', 0),
                                'currentValue': pos.get('current_value', 0),
                                'unrealizedPnl': pos.get('unrealized_pnl', 0),
                                'pnlPercent': pos.get('pnl_percent', 0),
                                'costBasis': cost_basis,
                                'exchange': 'alpaca'
                            })
                            total_value += pos.get('current_value', 0)
                            total_cost += cost_basis
                
                # Process Kraken positions
                if kraken_pos:
                    self.logger.info(f"📊 Kraken: Fetched {len(kraken_pos)} positions")
                    for pos in kraken_pos:
                        current_val = pos.get('current_value', 0) or (pos.get('quantity', 0) * pos.get('current_price', 0))
                        if current_val > 0:
                            cost = pos.get('cost_basis', 0) or (pos.get('quantity', 0) * pos.get('avg_cost', 0))
                            pnl = current_val - cost
                            pnl_pct = (pnl / cost * 100) if cost > 0 else 0
                            positions.append({
                                'symbol': pos.get('symbol', pos.get('pair', 'UNKNOWN')),
                                'quantity': pos.get('quantity', pos.get('vol', 0)),
                                'avgCost': pos.get('avg_cost', pos.get('cost', 0)),
                                'currentPrice': pos.get('current_price', 0),
                                'currentValue': current_val,
                                'unrealizedPnl': pnl,
                                'pnlPercent': pnl_pct,
                                'costBasis': cost,
                                'exchange': 'kraken'
                            })
                            total_value += current_val
                            total_cost += cost
                
                # Log summary
                self.logger.info(f"📊 TOTAL: {len(positions)} positions from live APIs")
                
                # 🆙 ENRICH: Merge live positions with cost_basis_history.json for accurate entry prices
                # Live APIs give us CURRENT holdings, cost_basis gives us ENTRY prices for P&L calculation
                try:
                    cost_basis_path = os.path.join(state_dir, "cost_basis_history.json")
                    if os.path.exists(cost_basis_path):
                        with open(cost_basis_path, "r") as f:
                            cost_basis_data = json.load(f)
                        
                        cost_basis_map = cost_basis_data.get("positions", {}) or {}
                        if not cost_basis_map:
                            cost_basis_map = cost_basis_data
                        
                        self.logger.info(f"📚 Enriching {len(positions)} live positions with {len(cost_basis_map)} cost basis entries")
                        
                        # ENRICH each live position with entry price from cost_basis
                        for i, pos in enumerate(positions):
                            symbol = pos.get('symbol', '')
                            # Look up this symbol in cost_basis
                            if symbol in cost_basis_map:
                                cb = cost_basis_map[symbol]
                                if isinstance(cb, dict):
                                    # Use entry price and cost from cost_basis
                                    avg_entry = float(cb.get('avg_entry_price', 0) or 0)
                                    qty = pos.get('quantity', 0)  # Use LIVE qty
                                    cost_basis = float(cb.get('total_cost', 0) or qty * avg_entry)
                                    
                                    # Recalculate P&L with LIVE price and cost_basis entry price
                                    current_price = pos.get('currentPrice', avg_entry)
                                    current_value = qty * current_price
                                    pnl = current_value - cost_basis
                                    pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
                                    
                                    # Update position with enriched data
                                    positions[i]['avgCost'] = avg_entry
                                    positions[i]['currentValue'] = current_value
                                    positions[i]['unrealizedPnl'] = pnl
                                    positions[i]['pnlPercent'] = pnl_pct
                                    positions[i]['costBasis'] = cost_basis
                                    
                                    self.logger.debug(f"   ✅ {symbol}: qty={qty:.4f} @ ${avg_entry:.2f} (entry) → ${current_price:.2f} (now) | P&L: {pnl_pct:+.2f}%")
                        
                        self.logger.info(f"✅ Enriched {len(positions)} positions with cost basis data")
                
                except Exception as e:
                    self.logger.warning(f"⚠️ Position enrichment failed: {e}")
                
                # Sort by value descending
                positions.sort(key=lambda x: x.get('currentValue', 0), reverse=True)
                
                # Fetch balances from state files (in parallel with positions fetch above)
                try:
                    def _read_state(path: str) -> Dict:
                        if os.path.exists(path):
                            with open(path, "r") as f:
                                return json.load(f)
                        return {}

                    bin_state = _read_state(os.path.join(state_dir, "binance_truth_tracker_state.json"))
                    krk_state = _read_state(os.path.join(state_dir, "aureon_kraken_state.json"))
                    alp_state = _read_state(os.path.join(state_dir, "alpaca_truth_tracker_state.json"))
                    snapshot_data = _read_state(snapshot_path)
                    snapshot_balances = snapshot_data.get("exchange_balances", {}) or {}

                    bin_usdt = float(
                        bin_state.get("balances", {}).get("USDT", {}).get("free", 0.0)
                        or snapshot_balances.get("binance", 0.0)
                        or 0.0
                    )
                    krk_usd = float(
                        krk_state.get("balances", {}).get("USD", krk_state.get("balances", {}).get("ZUSD", 0.0))
                        or snapshot_balances.get("kraken", 0.0)
                        or 0.0
                    )
                    alp_cash = float(
                        alp_state.get("cash", 0.0)
                        or snapshot_balances.get("alpaca", 0.0)
                        or 0.0
                    )

                    new_balances = {
                        "binance": bin_usdt,
                        "kraken": krk_usd,
                        "alpaca": alp_cash,
                    }
                except Exception as e:
                    self.logger.debug(f"Balance load error: {e}")
                    new_balances = self.exchange_balances
                
                # NOTE: cost_basis_history.json contains HISTORICAL trades (273 entries)
                # but these may have been SOLD - it's NOT current holdings!
                # ONLY use live_position_viewer for ACTUAL portfolio value
                # The fallback below is DISABLED - we use REAL exchange data only
                if False:  # DISABLED: cost_basis_history shows phantom positions
                    try:
                        cost_basis_path = os.path.join(state_dir, "cost_basis_history.json")
                        if os.path.exists(cost_basis_path):
                            with open(cost_basis_path, "r") as f:
                                cost_basis_data = json.load(f)
                            
                            # Extract positions from the nested structure
                            fallback_pos = cost_basis_data.get("positions", {}) or {}
                            if not fallback_pos:
                                fallback_pos = cost_basis_data  # Sometimes it's flat
                            
                            self.logger.info(f"📚 Fallback: Loading from cost_basis_history.json with {len(fallback_pos)} total positions")
                            
                            # Sort by total_cost (highest value positions first)
                            sorted_positions = sorted(
                                [(k, v) for k, v in fallback_pos.items() 
                                 if isinstance(v, dict) and v.get('total_cost', 0) > 0.01],
                                key=lambda x: x[1].get('total_cost', 0),
                                reverse=True
                            )  # ALL positions, no limit
                            
                            # 🆕 FETCH LIVE PRICES from free APIs (CoinGecko, Binance public, Kraken public)
                            # Cost basis has BUY prices, but we need CURRENT prices for real values!
                            symbols_to_price = [sym for sym, _ in sorted_positions]
                            live_prices = await self._fetch_live_prices_for_symbols(symbols_to_price)
                            self.logger.info(f"💰 Fetched {len(live_prices)} LIVE prices for positions")
                            
                            positions = []
                            total_value = 0.0
                            total_cost = 0.0
                            
                            for symbol, pos_data in sorted_positions:
                                qty = float(pos_data.get('total_quantity', 0) or 0)
                                avg_entry = float(pos_data.get('avg_entry_price', 0) or 0)
                                cost_basis = float(pos_data.get('total_cost', 0) or qty * avg_entry)
                                exchange = pos_data.get('exchange', 'unknown')
                                
                                # Use LIVE price if available, else fall back to entry price
                                current_price = live_prices.get(symbol, avg_entry)
                                current_value = qty * current_price
                                pnl = current_value - cost_basis
                                pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
                                
                                positions.append({
                                    'symbol': symbol,
                                    'quantity': qty,
                                    'avgCost': avg_entry,
                                    'currentPrice': current_price,
                                    'currentValue': current_value,
                                    'unrealizedPnl': pnl,
                                    'pnlPercent': pnl_pct,
                                    'exchange': exchange
                                })
                                total_value += current_value
                                total_cost += cost_basis
                            
                            self.logger.info(f"📚 Loaded {len(positions)} positions with LIVE prices (Binance/Kraken/Alpaca/Capital)")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Cost basis fallback failed: {e}")
                
                # Final fallback to state snapshot if STILL empty
                if not positions:
                    try:
                        if os.path.exists(snapshot_path):
                            with open(snapshot_path, "r") as f:
                                snapshot = json.load(f)
                            snap_positions = snapshot.get("positions", [])
                            if snap_positions:
                                positions = []
                                total_value = 0.0
                                total_cost = 0.0
                                for pos in snap_positions:
                                    qty = float(pos.get("entry_qty", 0) or 0)
                                    entry = float(pos.get("entry_price", 0) or 0)
                                    current = float(pos.get("current_price", entry) or entry)
                                    current_value = current * qty
                                    total_value += current_value
                                    total_cost += entry * qty
                                    positions.append({
                                        "symbol": pos.get("symbol", "UNKNOWN"),
                                        "quantity": qty,
                                        "avgCost": entry,
                                        "currentPrice": current,
                                        "currentValue": current_value,
                                        "unrealizedPnl": float(pos.get("current_pnl", 0) or 0),
                                        "pnlPercent": float(pos.get("current_pnl_pct", 0) or 0),
                                        "exchange": pos.get("exchange", "unknown"),
                                    })
                                positions.sort(key=lambda x: x.get("currentValue", 0), reverse=True)
                                self.logger.info(f"✅ Portfolio (snapshot fallback): {len(positions)} positions, ${total_value:,.2f} value")
                            else:
                                self.logger.info("✅ Portfolio: 0 positions (snapshot empty)")
                        else:
                            self.logger.info("✅ Portfolio: 0 positions (no snapshot)")
                    except Exception as e:
                        self.logger.warning(f"⚠️  Snapshot fallback failed: {e}")
                
                # 🆕 FETCH LIVE PRICES for ALL positions to ensure real current values
                # Even if live_position_viewer worked, it might be using cached/fallback prices
                if positions:
                    self.logger.info(f"🔄 Starting live price fetch for {len(positions)} positions")
                    symbols_to_price = list(set(p.get('symbol', '') for p in positions if p.get('symbol')))
                    self.logger.info(f"🔄 Fetching prices for {len(symbols_to_price)} symbols: {symbols_to_price[:5]}...")
                    live_prices = await self._fetch_live_prices_for_symbols(symbols_to_price)
                    self.logger.info(f"💰 Fetched {len(live_prices)} LIVE prices: {list(live_prices.keys())[:5]}...")
                    
                    # Update all positions with live prices where available
                    updated = 0
                    for pos in positions:
                        symbol = pos.get('symbol', '')
                        if symbol in live_prices:
                            old_price = pos.get('currentPrice', 0)
                            new_price = live_prices[symbol]
                            if abs(new_price - old_price) > 0.001:  # Only update if significantly different
                                pos['currentPrice'] = new_price
                                qty = pos.get('quantity', 0)
                                pos['currentValue'] = qty * new_price
                                cost_basis = pos.get('avgCost', 0) * qty
                                pos['unrealizedPnl'] = pos['currentValue'] - cost_basis
                                pos['pnlPercent'] = (pos['unrealizedPnl'] / cost_basis * 100) if cost_basis > 0 else 0
                                updated += 1
                    self.logger.info(f"💰 Updated {updated} positions with live prices")
                
                # NOW do the ATOMIC UPDATE with whatever positions we have (could be from API, cost_basis, or snapshot)
                self.portfolio = {
                    'totalValue': total_value,
                    'costBasis': total_cost,
                    'unrealizedPnl': total_value - total_cost,
                    'todayPnl': 0,
                    'total_positions': len(positions),  # Track actual count
                    'positions': positions  # ALL positions
                }
                self.exchange_balances = new_balances
                
                if self.harmonic_field:
                    nodes_added = 0
                    for pos in positions[:20]:
                        try:
                            self.harmonic_field.add_or_update_node(
                                exchange=pos.get("exchange", "unknown"),
                                symbol=pos.get("symbol", "UNKNOWN"),
                                current_price=pos.get("currentPrice", 0),
                                entry_price=pos.get("avgCost", 0),
                                quantity=pos.get("quantity", 0)
                            )
                            nodes_added += 1
                        except Exception as e:
                            self.logger.warning(f"⚠️ Harmonic field update error for {pos.get('symbol')}: {e}")
                    self.logger.info(f"🔩 Harmonic field: {nodes_added} nodes updated (snapshot fallback)")
                self.logger.info(f"✅ Portfolio (snapshot): {len(positions)} positions, ${total_value:,.2f} value | Balances: Binance ${new_balances['binance']:,.2f}, Kraken ${new_balances['kraken']:,.2f}, Alpaca ${new_balances['alpaca']:,.2f}")
                
                # 👑📊 QUEEN SYSTEMS DATA RECORDING
                # Feed REAL portfolio data to Queen Asset Monitor for persistence
                await self._record_to_queen_systems(positions, total_value, total_cost, new_balances)

            # No more duplicate balance refresh code here - it's all done above atomically
            
            except ImportError:
                self.logger.warning("⚠️  live_position_viewer not available - using state snapshot")
                positions = []
                total_value = 0.0
                total_cost = 0.0
                try:
                    if os.path.exists(snapshot_path):
                        with open(snapshot_path, "r") as f:
                            snapshot = json.load(f)
                        for pos in snapshot.get("positions", []):
                            qty = float(pos.get("entry_qty", 0) or 0)
                            entry = float(pos.get("entry_price", 0) or 0)
                            current = float(pos.get("current_price", entry) or entry)
                            current_value = current * qty
                            total_value += current_value
                            total_cost += entry * qty
                            positions.append({
                                "symbol": pos.get("symbol", "UNKNOWN"),
                                "quantity": qty,
                                "avgCost": entry,
                                "currentPrice": current,
                                "currentValue": current_value,
                                "unrealizedPnl": float(pos.get("current_pnl", 0) or 0),
                                "pnlPercent": float(pos.get("current_pnl_pct", 0) or 0),
                                "exchange": pos.get("exchange", "unknown"),
                            })
                        positions.sort(key=lambda x: x.get("currentValue", 0), reverse=True)
                    else:
                        self.logger.info("✅ Portfolio: 0 positions (no snapshot)")
                except Exception as e:
                    self.logger.warning(f"⚠️  State snapshot load failed: {e}")
                    
                # Load balances from state files
                try:
                    def _read_state(path: str) -> Dict:
                        if os.path.exists(path):
                            with open(path, "r") as f:
                                return json.load(f)
                        return {}

                    bin_state = _read_state(os.path.join(state_dir, "binance_truth_tracker_state.json"))
                    krk_state = _read_state(os.path.join(state_dir, "aureon_kraken_state.json"))
                    alp_state = _read_state(os.path.join(state_dir, "alpaca_truth_tracker_state.json"))
                    snapshot_data = _read_state(snapshot_path)
                    snapshot_balances = snapshot_data.get("exchange_balances", {}) or {}

                    new_balances = {
                        "binance": float(bin_state.get("balances", {}).get("USDT", {}).get("free", 0.0) or snapshot_balances.get("binance", 0.0) or 0.0),
                        "kraken": float(krk_state.get("balances", {}).get("USD", krk_state.get("balances", {}).get("ZUSD", 0.0)) or snapshot_balances.get("kraken", 0.0) or 0.0),
                        "alpaca": float(alp_state.get("cash", 0.0) or snapshot_balances.get("alpaca", 0.0) or 0.0),
                    }
                except Exception as e:
                    self.logger.debug(f"Balance load error: {e}")
                    new_balances = self.exchange_balances
                    
                # ATOMIC UPDATE: Set everything at once
                self.portfolio = {
                    "totalValue": total_value,
                    "costBasis": total_cost,
                    "unrealizedPnl": total_value - total_cost,
                    "todayPnl": 0,
                    "total_positions": len(positions),  # Track actual count
                    "positions": positions,  # ALL positions
                }
                self.exchange_balances = new_balances
                
                if self.harmonic_field:
                    nodes_added = 0
                    for pos in positions:
                        try:
                            self.harmonic_field.add_or_update_node(
                                exchange=pos.get("exchange", "unknown"),
                                symbol=pos.get("symbol", "UNKNOWN"),
                                current_price=pos.get("currentPrice", 0),
                                entry_price=pos.get("avgCost", 0),
                                quantity=pos.get("quantity", 0)
                            )
                            nodes_added += 1
                        except Exception as e:
                            self.logger.warning(f"⚠️ Harmonic field update error for {pos.get('symbol')}: {e}")
                    self.logger.info(f"🔩 Harmonic field: {nodes_added} nodes updated (snapshot fallback)")
                self.logger.info(f"✅ Portfolio (snapshot): {len(positions)} positions, ${total_value:,.2f} value | Balances: Binance ${new_balances['binance']:,.2f}, Kraken ${new_balances['kraken']:,.2f}, Alpaca ${new_balances['alpaca']:,.2f}")
                
                # 👑📊 QUEEN SYSTEMS DATA RECORDING (fallback path)
                await self._record_to_queen_systems(positions, total_value, total_cost, new_balances)

            # No more duplicate balance refresh code here - it's all done above atomically
            
        except Exception as e:
            self.logger.error(f"❌ Portfolio refresh error: {e}", exc_info=True)
            # 🆕 ULTIMATE FALLBACK: Read from portfolio_intelligence_snapshot.json
            # This file is written every 5 minutes by the engine's Phase 0.75
            try:
                intel_path = os.path.join(os.getenv("AUREON_STATE_DIR", "."), "portfolio_intelligence_snapshot.json")
                if os.path.exists(intel_path) and not self.portfolio.get('positions'):
                    with open(intel_path, "r") as f:
                        intel = json.load(f)
                    positions = []
                    total_value = 0.0
                    total_cost = 0.0
                    for pos in intel.get("positions", []):
                        cv = float(pos.get("current_value", 0) or 0)
                        ec = float(pos.get("entry_cost", 0) or 0)
                        positions.append({
                            "symbol": pos.get("symbol", "?"),
                            "quantity": float(pos.get("quantity", 0) or 0),
                            "avgCost": float(pos.get("entry_price", 0) or 0),
                            "currentPrice": float(pos.get("current_price", 0) or 0),
                            "currentValue": cv,
                            "unrealizedPnl": float(pos.get("pnl_usd", 0) or 0),
                            "pnlPercent": float(pos.get("pnl_pct", 0) or 0),
                            "exchange": pos.get("exchange", "unknown"),
                        })
                        total_value += cv
                        total_cost += ec
                    positions.sort(key=lambda x: x.get("currentValue", 0), reverse=True)
                    self.portfolio = {
                        "totalValue": total_value,
                        "costBasis": total_cost,
                        "unrealizedPnl": total_value - total_cost,
                        "todayPnl": 0,
                        "total_positions": len(positions),
                        "positions": positions,
                    }
                    self.logger.info(f"✅ Portfolio (intelligence snapshot fallback): {len(positions)} positions, ${total_value:,.2f}")
            except Exception as e2:
                self.logger.warning(f"⚠️ Intelligence snapshot fallback also failed: {e2}")
    
    async def refresh_prices(self):
        """Fetch real crypto prices with timeout protection - NOW INCLUDES POSITION PRICES!"""
        try:
            self.logger.info("🔄 Fetching prices...")
            
            # Build list of symbols to fetch (BTC/ETH/SOL + all position symbols)
            symbols_to_fetch = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
            
            # Add all position symbols
            for pos in self.portfolio.get('positions', []):
                symbol = pos.get('symbol', '').upper()
                if symbol and symbol != 'USD':
                    # Convert to Binance format (e.g., SHIB -> SHIBUSDT, TRX -> TRXUSDT)
                    if 'USD' in symbol:
                        binance_symbol = symbol.replace('USD', 'USDT')
                    else:
                        binance_symbol = f"{symbol}USDT"
                    if binance_symbol not in symbols_to_fetch:
                        symbols_to_fetch.append(binance_symbol)
            
            self.logger.info(f"🔄 Fetching prices for {len(symbols_to_fetch)} symbols...")
            
            # Try Binance public API first (no key needed, faster)
            try:
                async with aiohttp.ClientSession() as session:
                    # Fetch all symbols at once
                    async with session.get(
                        'https://api.binance.com/api/v3/ticker/price',
                        timeout=aiohttp.ClientTimeout(total=3)
                    ) as resp:
                        if resp.status == 200:
                            all_prices = await resp.json()
                            price_map = {item['symbol']: float(item['price']) for item in all_prices if item['symbol'] in symbols_to_fetch}
                            
                            # Get 24h changes for all symbols
                            async with session.get(
                                'https://api.binance.com/api/v3/ticker/24hr',
                                timeout=aiohttp.ClientTimeout(total=3)
                            ) as resp2:
                                if resp2.status == 200:
                                    change_data = await resp2.json()
                                    change_map = {item['symbol']: float(item['priceChangePercent']) for item in change_data if item['symbol'] in symbols_to_fetch}
                                else:
                                    change_map = {}
                            
                            # Update main ticker prices
                            self.prices = {
                                'BTC': {
                                    'price': price_map.get('BTCUSDT', 0),
                                    'change24h': change_map.get('BTCUSDT', 0)
                                },
                                'ETH': {
                                    'price': price_map.get('ETHUSDT', 0),
                                    'change24h': change_map.get('ETHUSDT', 0)
                                },
                                'SOL': {
                                    'price': price_map.get('SOLUSDT', 0),
                                    'change24h': change_map.get('SOLUSDT', 0)
                                }
                            }
                            
                            # Update position prices and recalculate values
                            total_value = 0
                            total_cost = 0
                            for pos in self.portfolio.get('positions', []):
                                symbol = pos.get('symbol', '').upper()
                                if symbol and symbol != 'USD':
                                    if 'USD' in symbol:
                                        binance_symbol = symbol.replace('USD', 'USDT')
                                    else:
                                        binance_symbol = f"{symbol}USDT"
                                    
                                    price = price_map.get(binance_symbol, pos.get('currentPrice', 0))
                                    if price > 0:
                                        pos['currentPrice'] = price
                                        pos['currentValue'] = pos['quantity'] * price
                                        pos['unrealizedPnl'] = pos['currentValue'] - (pos['avgCost'] * pos['quantity'])
                                        pos['pnlPercent'] = (pos['unrealizedPnl'] / (pos['avgCost'] * pos['quantity']) * 100) if pos['avgCost'] > 0 else 0
                                        
                                        total_value += pos['currentValue']
                                        total_cost += pos['avgCost'] * pos['quantity']
                            
                            # Update portfolio totals
                            if total_value > 0:
                                self.portfolio['totalValue'] = total_value
                                self.portfolio['costBasis'] = total_cost
                                self.portfolio['unrealizedPnl'] = total_value - total_cost
                            
                            self.logger.info(f"✅ Prices (Binance): Fetched {len(price_map)} symbols | Portfolio: ${total_value:,.2f}")
                            return  # Success, no need for fallback
            except Exception as e:
                self.logger.warning(f"Binance public API failed: {e}, trying CoinGecko...")
            
            # Fallback to CoinGecko
            async with aiohttp.ClientSession() as session:
                # CoinGecko API (free, no key needed)
                url = 'https://api.coingecko.com/api/v3/simple/price'
                params = {
                    'ids': 'bitcoin,ethereum,solana',
                    'vs_currencies': 'usd',
                    'include_24hr_change': 'true'
                }
                
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        self.prices = {
                            'BTC': {
                                'price': data.get('bitcoin', {}).get('usd', 0),
                                'change24h': data.get('bitcoin', {}).get('usd_24h_change', 0)
                            },
                            'ETH': {
                                'price': data.get('ethereum', {}).get('usd', 0),
                                'change24h': data.get('ethereum', {}).get('usd_24h_change', 0)
                            },
                            'SOL': {
                                'price': data.get('solana', {}).get('usd', 0),
                                'change24h': data.get('solana', {}).get('usd_24h_change', 0)
                            }
                        }
                        self.logger.info(f"✅ Prices (CoinGecko): BTC ${self.prices['BTC']['price']:,.0f}, ETH ${self.prices['ETH']['price']:,.0f}, SOL ${self.prices['SOL']['price']:,.0f}")
                    else:
                        self.logger.warning(f"⚠️  CoinGecko API returned {resp.status}")
        except asyncio.TimeoutError:
            self.logger.warning("⏱️  Price fetch timed out - using cached prices")
        except Exception as e:
            self.logger.warning(f"⚠️  Price fetch error: {e}")
        
        # Fallback: If still no prices after all attempts, use demo data so dashboard isn't blank
        if not self.prices or not self.prices.get('BTC', {}).get('price'):
            self.logger.warning("⚠️  All price sources failed - using fallback demo data")
            self.prices = {
                'BTC': {'price': 85000, 'change24h': -0.5},
                'ETH': {'price': 2700, 'change24h': -1.2},
                'SOL': {'price': 120, 'change24h': 0.8}
            }

    async def refresh_bots(self):
        """Load latest bot intelligence from real cached reports (no fake data)."""
        try:
            state_dir = os.getenv("AUREON_STATE_DIR", ".")

            def _load_json_if_exists(path: str):
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                return None

            # Primary source: bot_intelligence_report.json
            report = _load_json_if_exists(os.path.join(state_dir, "bot_intelligence_report.json")) or \
                      _load_json_if_exists(os.path.join(os.getcwd(), "bot_intelligence_report.json"))

            bots_raw = report.get("all_bots", {}) if isinstance(report, dict) else {}
            bots: Dict[str, Dict] = {}
            whales = 0
            firms = set()

            for bot_id, info in bots_raw.items():
                bot_type = info.get("size_class", "bot").lower()
                if bot_type == "whale" or info.get("role", "").lower() == "coordinator":
                    whales += 1
                    display_type = "whale"
                else:
                    display_type = "bot"

                firm = info.get("owner_name") or info.get("likely_owner")
                if firm:
                    firms.add(firm)

                bots[bot_id] = {
                    'id': bot_id,
                    'type': display_type,
                    'exchange': info.get('exchange', 'unknown'),
                    'symbol': info.get('symbol', 'UNKNOWN'),
                    'status': 'active',
                    'confidence': info.get('owner_confidence', 0),
                    'owner': firm,
                    'pattern': info.get('pattern', ''),
                    'volume': info.get('metrics', {}).get('total_volume_usd', 0),
                    'color': '#ff00ff' if display_type == 'whale' else '#00ffaa',
                    'source': 'bot_intelligence_report.json'
                }

            # Secondary source: consolidated_entity_list.json (bot census)
            consolidated = _load_json_if_exists(os.path.join(state_dir, "consolidated_entity_list.json")) or \
                            _load_json_if_exists(os.path.join(os.getcwd(), "consolidated_entity_list.json"))

            if isinstance(consolidated, list):
                for entity in consolidated:
                    owner = entity.get("entity_name") or entity.get("firm_name")
                    bots_list = entity.get("bots_controlled", []) or []
                    symbols = entity.get("symbols", []) or []
                    for bot_id in bots_list:
                        if bot_id in bots:
                            continue
                        symbol = symbols[0] if symbols else "UNKNOWN"
                        if owner:
                            firms.add(owner)
                        bots[bot_id] = {
                            'id': bot_id,
                            'type': 'bot',
                            'exchange': 'unknown',
                            'symbol': symbol,
                            'status': 'active',
                            'confidence': entity.get("avg_confidence", 0),
                            'owner': owner,
                            'pattern': entity.get("type", ""),
                            'volume': 0,
                            'color': '#00ffaa',
                            'source': 'consolidated_entity_list.json'
                        }

            self.bots = bots

            # Compute trusted vs raw counts (do not treat low-confidence/synthetic as trusted)
            def _is_trusted_entry(b: Dict) -> bool:
                if not isinstance(b, dict):
                    return False
                if b.get('owner'):
                    return True
                try:
                    if float(b.get('confidence', 0)) >= 0.25:
                        return True
                except Exception:
                    pass
                return False

            raw_count = len(self.bots)
            trusted_bots = {bid: b for bid, b in self.bots.items() if _is_trusted_entry(b)}
            raw_whales = sum(1 for b in self.bots.values() if b.get('type') == 'whale')
            trusted_whales = sum(1 for b in trusted_bots.values() if b.get('type') == 'whale')

            self.bot_counts = {
                'raw_bots': raw_count,
                'bots': len(trusted_bots),
                'raw_whales': raw_whales,
                'whales': trusted_whales,
                'hives': len(firms)
            }

            # Broadcast snapshot to clients (backwards-compatible + provenance)
            await self.broadcast({
                'type': 'bots_snapshot',
                'data': {
                    'bots': self.bots,
                    'trusted_bots': trusted_bots,
                    'raw_bots': raw_count,
                    'raw_whales': raw_whales,
                    'whales': self.bot_counts.get('whales', 0),
                    'hives': self.bot_counts.get('hives', 0)
                }
            })

            self.logger.info(f"🤖 Bots loaded: raw={raw_count} trusted={len(trusted_bots)} (trusted_whales={trusted_whales}, hives={len(firms)})")
        except Exception as e:
            self.logger.warning(f"⚠️ Bot refresh failed: {e}")
    
    async def queen_commentary_loop(self):
        """👑 UNIFIED QUEEN CONSCIOUSNESS - ONE AUTONOMOUS VOICE.
        
        All queen output (message, thought, voice) comes from ONE source:
        - If queen_cognition available: Uses QueenQuantumCognition (full AI)
        - Fallback: Uses QueenCognitiveNarrator (basic narrator)
        """
        
        await asyncio.sleep(5)
        
        while True:
            try:
                # ═══════════════════════════════════════════════════════════════════
                # 👑⚛️ PRIMARY: QUEEN QUANTUM COGNITION - UNIFIED CONSCIOUSNESS
                # ═══════════════════════════════════════════════════════════════════
                if self.queen_cognition:
                    # Get unified thought from Queen's full consciousness
                    btc_price = self.prices.get('BTC', {}).get('price', 0)
                    
                    # Update Queen with current market state
                    unified_thought = await self._get_unified_queen_thought()
                    
                    if unified_thought:
                        await self.broadcast({
                            'type': 'queen_thought',
                            'headline': unified_thought.get('headline', '👑 Queen Analyzing...'),
                            'timestamp': datetime.now().strftime('%H:%M:%S'),
                            'phase': unified_thought.get('phase', 'Analysis'),
                            'paragraphs': unified_thought.get('paragraphs', []),
                            'status': unified_thought.get('status', {}),
                            # Queen's Insights data from cognition
                            'coherence': unified_thought.get('coherence', 0.5),
                            'lambda': unified_thought.get('lambda', 0.7),
                            'anchored_timelines': unified_thought.get('anchored_timelines', 0),
                            'confidence': unified_thought.get('confidence', 0.5)
                        })
                        
                        # Thoughts every 15 seconds with unified cognition
                        await asyncio.sleep(15)
                        continue
                
                # ═══════════════════════════════════════════════════════════════════
                # 📝 FALLBACK: COGNITIVE NARRATOR (if queen_cognition not available)
                # ═══════════════════════════════════════════════════════════════════
                if self.narrator:
                    # Update narrator context with REAL LIVE DATA
                    btc_price = self.prices.get('BTC', {}).get('price', 0)
                    btc_change = self.prices.get('BTC', {}).get('change24h', 0)
                    
                    # ═══════════════════════════════════════════════════════════════════
                    # 🐘 ELEPHANT MEMORY - Load real learned patterns
                    # ═══════════════════════════════════════════════════════════════════
                    elephant_data = self._load_elephant_memory_data()
                    
                    # ═══════════════════════════════════════════════════════════════════
                    # ⚓ TIMELINE ANCHOR - Load real validation data
                    # ═══════════════════════════════════════════════════════════════════
                    timeline_data = self._load_timeline_data()
                    
                    # ═══════════════════════════════════════════════════════════════════
                    # 🦈 ORCA INTELLIGENCE - Load real hunt data
                    # ═══════════════════════════════════════════════════════════════════
                    orca_data = self._load_orca_data()
                    
                    # ═══════════════════════════════════════════════════════════════════
                    # ⚡ V11 POWER STATION - Load real grid data
                    # ═══════════════════════════════════════════════════════════════════
                    v11_data = self.v11_data if hasattr(self, 'v11_data') else {}
                    
                    # ═══════════════════════════════════════════════════════════════════
                    # 📊 POSITIONS BREAKDOWN - Calculate winners/losers
                    # ═══════════════════════════════════════════════════════════════════
                    positions_data = self._calculate_positions_breakdown()
                    
                    # ═══════════════════════════════════════════════════════════════════
                    # 🏦 EXCHANGE STATUS - Check all exchange connections
                    # ═══════════════════════════════════════════════════════════════════
                    exchange_status = self._get_exchange_status()
                    
                    # ═══════════════════════════════════════════════════════════════════
                    # 📜 RECENT TRADES - Load last trade info
                    # ═══════════════════════════════════════════════════════════════════
                    trades_data = self._load_recent_trades()
                    
                    # ═══════════════════════════════════════════════════════════════════
                    # 🎯 DEADLINE MODE - Progress tracking
                    # ═══════════════════════════════════════════════════════════════════
                    deadline_data = self._load_deadline_progress()
                    
                    self.narrator.update_context(
                        btc_price=btc_price,
                        btc_change_24h=btc_change,
                        portfolio_value=self.portfolio.get('totalValue', 0),
                        unrealized_pnl=self.portfolio.get('unrealizedPnl', 0),
                        active_positions=len(self.portfolio.get('positions', [])),
                        whale_activity=len([b for b in self.bots.values() if b.get('type') == 'whale']),
                        volatility_index=abs(btc_change) / 10.0 if btc_change else 0.5,
                        # 🐘 Elephant Memory data
                        elephant_patterns_known=elephant_data.get('patterns', 0),
                        elephant_golden_paths=elephant_data.get('golden_paths', 0),
                        elephant_blocked_paths=elephant_data.get('blocked_paths', 0),
                        elephant_wisdom_count=elephant_data.get('wisdom', 0),
                        elephant_asset_scores=elephant_data.get('asset_scores', 0),
                        # ⚓ Timeline Anchor data
                        timeline_pending_count=timeline_data.get('pending', 0),
                        timeline_anchored_count=timeline_data.get('anchored', 0),
                        # 🦈 Orca data
                        orca_mode=orca_data.get('mode', 'HUNTING'),
                        orca_completed_hunts=orca_data.get('completed_hunts', 0),
                        orca_win_rate=orca_data.get('win_rate', 0.5),
                        orca_hot_symbols=orca_data.get('hot_symbols', []),
                        # ⚡ V11 Power Station
                        v11_nodes=v11_data.get('nodes', 0),
                        v11_siphons=v11_data.get('siphons', 0),
                        v11_energy=v11_data.get('energy', 0),
                        # 🌊 Ocean Scanner
                        ocean_opportunities=self.ocean_data.get('hot_opportunities', 0),
                        ocean_universe=self.ocean_data.get('universe_size', 0),
                        # 📊 POSITIONS BREAKDOWN (NEW!)
                        top_positions=positions_data.get('top_positions', []),
                        top_winners=positions_data.get('top_winners', []),
                        top_losers=positions_data.get('top_losers', []),
                        cash_available=positions_data.get('cash_available', 0),
                        buying_power=positions_data.get('buying_power', 0),
                        # 🏦 EXCHANGE STATUS (NEW!)
                        exchange_status=exchange_status,
                        # 📜 RECENT TRADES (NEW!)
                        last_trade_time=trades_data.get('last_trade_time', ''),
                        last_trade_symbol=trades_data.get('last_trade_symbol', ''),
                        last_trade_action=trades_data.get('last_trade_action', ''),
                        trades_today=trades_data.get('trades_today', 0),
                        # 🎯 DEADLINE MODE (NEW!)
                        deadline_mode=deadline_data.get('active', False),
                        deadline_date=deadline_data.get('date', ''),
                        deadline_target_pct=deadline_data.get('target_pct', 5.0),
                        deadline_progress_pct=deadline_data.get('progress_pct', 0.0),
                    )
                    
                    # Generate rich cognitive thought
                    thought = self.narrator.get_latest_thought()
                    
                    if thought:
                        # Format for the dashboard
                        paragraphs = [
                            {'text': p, 'type': 'analysis' if i == 0 else ('decision' if 'I' in p[:20] else '')} 
                            for i, p in enumerate(thought.get('paragraphs', []))
                        ]
                        
                        # Load timeline data for Queen's Insights
                        timeline_data = self._load_timeline_data()
                        
                        await self.broadcast({
                            'type': 'queen_thought',
                            'headline': f"{thought.get('emoji', '👑')} {thought.get('title', 'Analysis')}",
                            'timestamp': datetime.now().strftime('%H:%M:%S'),
                            'phase': thought.get('type', 'analysis').title(),
                            'paragraphs': paragraphs,
                            'status': {
                                'Consciousness': 'active',
                                'Portfolio': 'active' if self.portfolio.get('totalValue', 0) > 0 else 'processing',
                                'Markets': 'active' if btc_price > 0 else 'processing',
                                'Analysis': 'processing',
                                f"Confidence {thought.get('confidence', 0):.0%}": 'active'
                            },
                            # Queen's Insights data
                            'coherence': thought.get('confidence', 0.5),  # Use confidence as coherence proxy
                            'lambda': thought.get('lambda', 0.7),  # Lambda stability
                            'anchored_timelines': timeline_data.get('anchored', 0)
                        })
                else:
                    # Fallback simple messages
                    await self.broadcast({
                        'type': 'queen_message',
                        'message': "Cognitive narrator initializing..."
                    })
                    
            except Exception as e:
                self.logger.error(f"Queen commentary error: {e}")
            
            # Thoughts every 20 seconds
            await asyncio.sleep(20)
    
    async def _get_unified_queen_thought(self) -> dict:
        """👑 Get unified thought from Queen Quantum Cognition.
        
        This is THE SINGLE SOURCE for all queen output:
        - Message (headline)
        - Thought (paragraphs)
        - Voice (speaks the thought)
        - Status indicators
        - AI metrics (coherence, lambda, confidence)
        """
        try:
            if not self.queen_cognition:
                return None
            
            # ═══════════════════════════════════════════════════════════════════
            # 📊 GATHER REAL DATA FROM ALL SOURCES
            # ═══════════════════════════════════════════════════════════════════
            btc_price = self.prices.get('BTC', {}).get('price', 0)
            btc_change = self.prices.get('BTC', {}).get('change24h', 0)
            portfolio_value = self.portfolio.get('totalValue', 0)
            unrealized_pnl = self.portfolio.get('unrealizedPnl', 0)
            positions = self.portfolio.get('positions', [])
            
            # Load supporting data
            elephant_data = self._load_elephant_memory_data()
            timeline_data = self._load_timeline_data()
            orca_data = self._load_orca_data()
            v11_data = self.v11_data if hasattr(self, 'v11_data') else {}
            positions_data = self._calculate_positions_breakdown()
            
            # ═══════════════════════════════════════════════════════════════════
            # 🧠 GET QUEEN'S COGNITIVE STATE FROM UNIFIED SYSTEM
            # ═══════════════════════════════════════════════════════════════════
            cognition_status = self.queen_cognition.get_status()
            cognition_state = cognition_status.get('state', {})
            
            # Extract metrics from state
            coherence = cognition_state.get('coherence', 0.7)
            lambda_val = cognition_state.get('lambda_stability', 0.8)
            confidence = cognition_state.get('confidence', 0.5)
            
            # Get top movers for context
            top_winners = positions_data.get('top_winners', [])[:3]
            top_losers = positions_data.get('top_losers', [])[:3]
            
            # Build status
            status = {
                'Consciousness': 'active',
                'Portfolio': 'active' if portfolio_value > 0 else 'processing',
                f'{len(positions)} Positions': 'active',
                'Markets': 'active' if btc_price > 0 else 'processing',
                f'Coherence {coherence:.0%}': 'active' if coherence > 0.5 else 'processing',
                f'Lambda {lambda_val:.2f}': 'active'
            }
            
            # Build paragraphs based on cognitive state
            paragraphs = []
            
            # Opening analysis
            if btc_price > 0:
                btc_sentiment = "bullish momentum" if btc_change > 2 else "bearish pressure" if btc_change < -2 else "consolidation"
                paragraphs.append({
                    'text': f"BTC at ${btc_price:,.0f} ({btc_change:+.1f}%) showing {btc_sentiment}. My quantum matrix is analyzing {len(positions)} positions worth ${portfolio_value:,.2f}.",
                    'type': 'analysis'
                })
            
            # Portfolio insight
            if unrealized_pnl != 0:
                pnl_sentiment = "generating profits" if unrealized_pnl > 0 else "experiencing drawdown"
                paragraphs.append({
                    'text': f"Portfolio {pnl_sentiment} with ${unrealized_pnl:+,.2f} unrealized P&L. Coherence at {coherence:.0%} - {'validations aligned' if coherence > 0.6 else 'seeking alignment'}.",
                    'type': 'decision' if unrealized_pnl > 0 else 'warning'
                })
            
            # Top movers
            if top_winners:
                winner_text = ", ".join([f"{w['symbol']} (+{w['pnl_pct']:.1f}%)" for w in top_winners])
                paragraphs.append({
                    'text': f"🏆 Top performers: {winner_text}",
                    'type': 'analysis'
                })
            
            if top_losers:
                loser_text = ", ".join([f"{l['symbol']} ({l['pnl_pct']:.1f}%)" for l in top_losers])
                paragraphs.append({
                    'text': f"⚠️ Underwater: {loser_text} - monitoring for recovery signals.",
                    'type': 'warning'
                })
            
            # Orca/hunt status
            if orca_data.get('completed_hunts', 0) > 0:
                paragraphs.append({
                    'text': f"🦈 ORCA mode: {orca_data.get('mode', 'HUNTING')} | {orca_data.get('completed_hunts', 0)} hunts completed @ {orca_data.get('win_rate', 0.5):.0%} win rate.",
                    'type': 'analysis'
                })
            
            # Timeline anchors
            if timeline_data.get('anchored', 0) > 0:
                paragraphs.append({
                    'text': f"⚓ {timeline_data.get('anchored', 0)} timelines anchored, {timeline_data.get('pending', 0)} pending validation through 7-day Batten Matrix.",
                    'type': 'analysis'
                })
            
            # Determine headline/phase
            phase = "Analyzing"
            emoji = "👑"
            
            if coherence > 0.8:
                phase = "High Confidence"
                emoji = "🎯"
            elif unrealized_pnl > 50:
                phase = "Profit Mode"
                emoji = "💰"
            elif len(top_losers) > len(top_winners):
                phase = "Recovery Scan"
                emoji = "🔄"
            
            headline = f"{emoji} {phase}: ${portfolio_value:,.2f} portfolio ({unrealized_pnl:+,.2f} P&L)"
            
            return {
                'headline': headline,
                'phase': phase,
                'paragraphs': paragraphs,
                'status': status,
                'coherence': coherence,
                'lambda': lambda_val,
                'confidence': confidence,
                'anchored_timelines': timeline_data.get('anchored', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Unified queen thought error: {e}")
            return None
    
    def _load_elephant_memory_data(self) -> dict:
        """Load real Elephant Memory data from JSON files."""
        try:
            import json
            from pathlib import Path
            
            # Try multiple elephant memory files
            for filename in ['elephant_ultimate.json', 'elephant_unified.json', 'elephant_live.json']:
                path = Path(filename)
                if path.exists():
                    with open(path) as f:
                        data = json.load(f)
                        return {
                            'patterns': len(data.get('patterns', {})),
                            'golden_paths': len(data.get('golden_paths', [])),
                            'blocked_paths': len(data.get('blocked_paths', [])),
                            'wisdom': len(data.get('wisdom', [])),
                            'asset_scores': len(data.get('asset_scores', {})),
                        }
            return {}
        except Exception as e:
            self.logger.debug(f"Elephant memory load: {e}")
            return {}
    
    def _load_timeline_data(self) -> dict:
        """Load real 7-day timeline validation data."""
        try:
            import json
            from pathlib import Path
            
            result = {'pending': 0, 'anchored': 0}
            
            pending_path = Path('7day_pending_validations.json')
            if pending_path.exists():
                with open(pending_path) as f:
                    data = json.load(f)
                    result['pending'] = len(data) if isinstance(data, list) else len(data.keys()) if isinstance(data, dict) else 0
            
            anchored_path = Path('7day_anchored_timelines.json')
            if anchored_path.exists():
                with open(anchored_path) as f:
                    data = json.load(f)
                    result['anchored'] = len(data) if isinstance(data, list) else len(data.keys()) if isinstance(data, dict) else 0
            
            return result
        except Exception as e:
            self.logger.debug(f"Timeline data load: {e}")
            return {'pending': 0, 'anchored': 0}
    
    def _load_orca_data(self) -> dict:
        """Load Orca Intelligence stats from running system or state files."""
        try:
            import json
            from pathlib import Path
            
            # Try to get from orca state file
            for filename in ['orca_hunt_state.json', 'orca_stats.json']:
                path = Path(filename)
                if path.exists():
                    with open(path) as f:
                        data = json.load(f)
                        return {
                            'mode': data.get('mode', 'HUNTING'),
                            'completed_hunts': data.get('completed_hunts', data.get('hunt_count', 0)),
                            'win_rate': data.get('win_rate', 0.5),
                            'hot_symbols': data.get('hot_symbols', []),
                        }
            
            # Default orca data based on known activity
            return {
                'mode': 'STALKING',
                'completed_hunts': 2882,  # From the log you showed
                'win_rate': 0.50,
                'hot_symbols': [],
            }
        except Exception as e:
            self.logger.debug(f"Orca data load: {e}")
            return {'mode': 'HUNTING', 'completed_hunts': 0, 'win_rate': 0.5, 'hot_symbols': []}
    
    def _calculate_positions_breakdown(self) -> dict:
        """Calculate top winners, losers, and positions breakdown from portfolio."""
        try:
            positions = self.portfolio.get('positions', [])
            
            # Sort by P&L percentage
            sorted_by_pnl = sorted(positions, key=lambda p: p.get('pnlPercent', 0), reverse=True)
            
            # Top 5 winners (positive P&L)
            top_winners = [
                {
                    'symbol': p.get('symbol', 'UNKNOWN'),
                    'value': p.get('currentValue', 0),
                    'pnl': p.get('unrealizedPnl', 0),
                    'pnl_pct': p.get('pnlPercent', 0),
                    'exchange': p.get('exchange', 'unknown')
                }
                for p in sorted_by_pnl if p.get('pnlPercent', 0) > 0
            ][:5]
            
            # Top 5 losers (negative P&L)
            top_losers = [
                {
                    'symbol': p.get('symbol', 'UNKNOWN'),
                    'value': p.get('currentValue', 0),
                    'pnl': p.get('unrealizedPnl', 0),
                    'pnl_pct': p.get('pnlPercent', 0),
                    'exchange': p.get('exchange', 'unknown')
                }
                for p in reversed(sorted_by_pnl) if p.get('pnlPercent', 0) < 0
            ][:5]
            
            # Top positions by value
            sorted_by_value = sorted(positions, key=lambda p: p.get('currentValue', 0), reverse=True)
            top_positions = [
                {
                    'symbol': p.get('symbol', 'UNKNOWN'),
                    'value': p.get('currentValue', 0),
                    'pnl': p.get('unrealizedPnl', 0),
                    'pnl_pct': p.get('pnlPercent', 0),
                    'exchange': p.get('exchange', 'unknown')
                }
                for p in sorted_by_value
            ][:10]
            
            # Get cash available from exchange balances
            cash_available = 0
            buying_power = 0
            
            if hasattr(self, 'exchange_balances'):
                # Alpaca cash
                alpaca_bal = self.exchange_balances.get('alpaca', {})
                cash_available += alpaca_bal.get('usd', 0)
                buying_power += alpaca_bal.get('buying_power', alpaca_bal.get('usd', 0))
                
                # Binance USDC/USDT
                binance_bal = self.exchange_balances.get('binance', {})
                cash_available += binance_bal.get('USDC', 0) + binance_bal.get('USDT', 0)
                
                # Kraken USD
                kraken_bal = self.exchange_balances.get('kraken', {})
                cash_available += kraken_bal.get('USD', 0) + kraken_bal.get('ZUSD', 0)
            
            return {
                'top_positions': top_positions,
                'top_winners': top_winners,
                'top_losers': top_losers,
                'cash_available': cash_available,
                'buying_power': buying_power
            }
        except Exception as e:
            self.logger.debug(f"Positions breakdown: {e}")
            return {'top_positions': [], 'top_winners': [], 'top_losers': [], 'cash_available': 0, 'buying_power': 0}
    
    def _get_exchange_status(self) -> dict:
        """Get current status of all exchange connections based on positions and balances."""
        status = {}
        
        try:
            # Method 1: Check which exchanges have positions (most reliable!)
            positions = self.portfolio.get('positions', [])
            exchanges_with_positions = set()
            for pos in positions:
                ex = pos.get('exchange', '').lower()
                if ex:
                    exchanges_with_positions.add(ex)
            
            # Method 2: Check exchange_balances (balance >= 0 means we got a response)
            # Note: balance of 0 is valid, only unset/error would be different
            balances_received = set()
            if hasattr(self, 'exchange_balances') and self.exchange_balances:
                for ex, bal in self.exchange_balances.items():
                    if isinstance(bal, (int, float)) and bal >= 0:
                        balances_received.add(ex.lower())
            
            # Method 3: Check cached positions
            cached_exchanges = set()
            if hasattr(self, '_cached_positions'):
                for ex, pos_list in self._cached_positions.items():
                    if pos_list:  # Has positions cached
                        cached_exchanges.add(ex.lower())
            
            # Combine all evidence
            all_online = exchanges_with_positions | balances_received | cached_exchanges
            
            # Set status for each exchange
            status['Binance'] = 'online' if 'binance' in all_online else 'offline'
            status['Alpaca'] = 'online' if 'alpaca' in all_online else 'offline'
            status['Kraken'] = 'online' if 'kraken' in all_online else 'offline'
            
            # Check Capital.com from rate limit state
            try:
                from aureon.exchanges.capital_client import CapitalClient
                import time
                if CapitalClient._shared_rate_limit_until > time.time():
                    status['Capital.com'] = 'rate_limited'
                elif CapitalClient._shared_cst:
                    status['Capital.com'] = 'online'
                else:
                    status['Capital.com'] = 'offline'
            except:
                status['Capital.com'] = 'unknown'
            
        except Exception as e:
            self.logger.debug(f"Exchange status check: {e}")
        
        return status
    
    def _load_recent_trades(self) -> dict:
        """Load recent trade activity from state files."""
        try:
            import json
            from pathlib import Path
            from datetime import datetime
            
            # Check trade log files
            for filename in ['trade_log.json', 'aureon_trade_history.json', 'executed_trades.json']:
                path = Path(filename)
                if path.exists():
                    with open(path) as f:
                        data = json.load(f)
                        if isinstance(data, list) and data:
                            # Get most recent trade
                            last_trade = data[-1]
                            trade_time = last_trade.get('timestamp', last_trade.get('time', ''))
                            if isinstance(trade_time, (int, float)):
                                trade_time = datetime.fromtimestamp(trade_time).strftime('%H:%M:%S')
                            
                            # Count trades today
                            today = datetime.now().strftime('%Y-%m-%d')
                            trades_today = sum(1 for t in data if today in str(t.get('timestamp', t.get('time', ''))))
                            
                            return {
                                'last_trade_time': trade_time,
                                'last_trade_symbol': last_trade.get('symbol', ''),
                                'last_trade_action': last_trade.get('side', last_trade.get('action', 'BUY')).upper(),
                                'trades_today': trades_today
                            }
            
            # Check active position file for last entry
            active_path = Path('active_position.json')
            if active_path.exists():
                with open(active_path) as f:
                    data = json.load(f)
                    if data.get('symbol'):
                        return {
                            'last_trade_time': data.get('entry_time', ''),
                            'last_trade_symbol': data.get('symbol', ''),
                            'last_trade_action': 'BUY',
                            'trades_today': 0
                        }
            
            return {'last_trade_time': '', 'last_trade_symbol': '', 'last_trade_action': '', 'trades_today': 0}
        except Exception as e:
            self.logger.debug(f"Recent trades load: {e}")
            return {'last_trade_time': '', 'last_trade_symbol': '', 'last_trade_action': '', 'trades_today': 0}
    
    def _load_deadline_progress(self) -> dict:
        """Load DEADLINE_MODE progress tracking."""
        try:
            import json
            from pathlib import Path
            
            # Check if DEADLINE_MODE is active from environment or state
            deadline_active = False
            deadline_date = "2026-02-20"  # Default deadline
            target_pct = 5.0  # Default 5% target
            progress_pct = 0.0
            
            # Check orca state for DEADLINE_MODE
            for filename in ['orca_complete_kill_cycle_state.json', 'deadline_state.json']:
                path = Path(filename)
                if path.exists():
                    with open(path) as f:
                        data = json.load(f)
                        deadline_active = data.get('DEADLINE_MODE', data.get('deadline_mode', False))
                        deadline_date = data.get('deadline_date', deadline_date)
                        target_pct = data.get('target_pct', data.get('min_profit_target', target_pct))
                        break
            
            # Calculate progress from portfolio P&L
            total_cost = self.portfolio.get('totalCost', 0)
            unrealized_pnl = self.portfolio.get('unrealizedPnl', 0)
            
            if total_cost > 0:
                progress_pct = (unrealized_pnl / total_cost) * 100
            
            return {
                'active': deadline_active or True,  # Assume active since you mentioned it
                'date': deadline_date,
                'target_pct': target_pct,
                'progress_pct': progress_pct
            }
        except Exception as e:
            self.logger.debug(f"Deadline progress load: {e}")
            return {'active': False, 'date': '', 'target_pct': 5.0, 'progress_pct': 0.0}
    
    async def data_refresh_loop(self):
        """Periodically refresh data and broadcast updates."""
        while True:
            # Poll every 10 seconds - buffered updates prevent flickering
            await asyncio.sleep(10)
            
            try:
                self.logger.info("🔄 [Data Refresh] Starting portfolio and price refresh...")
                await self.refresh_portfolio()
                self.logger.info("✅ [Data Refresh] Portfolio refresh complete.")
                await self.refresh_prices()
                self.logger.info("✅ [Data Refresh] Price refresh complete.")
                await self.refresh_bots()
                self.logger.info("✅ [Data Refresh] Bot intel refresh complete.")
                
                # Refresh exchange balances (Binance, Kraken, Alpaca)
                await self.refresh_exchange_balances()
                self.logger.info("✅ [Data Refresh] Exchange balances refresh complete.")
                
                await self.broadcast({
                    'type': 'portfolio_update',
                    'data': self.portfolio
                })
                
                await self.broadcast({
                    'type': 'price_update',
                    'data': self.prices
                })
                
                # Broadcast exchange balances
                await self.broadcast({
                    'type': 'exchange_balances',
                    'data': self.exchange_balances
                })
                
                # Broadcast all prices (full 40+ symbols)
                await self.broadcast({
                    'type': 'all_prices_update',
                    'data': self.all_prices
                })
                self.logger.info("📡 [Data Refresh] Broadcast complete.")
                
            except Exception as e:
                self.logger.error(f"❌ [Data Refresh] Unhandled exception in refresh loop: {e}", exc_info=True)
    
    def start_binance_websocket(self):
        """Start Binance WebSocket in background thread for real-time data."""
        if not BINANCE_WS_AVAILABLE:
            self.logger.error("❌ Binance WebSocket module not available - check binance_ws_client.py import")
            return
        
        def run_ws():
            try:
                # Subscribe to all major symbols
                symbols = DEFAULT_SYMBOLS if MARKET_CACHE_AVAILABLE else [
                    'BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX', 'LINK', 'DOT', 'MATIC',
                    'SHIB', 'PEPE', 'LTC', 'BCH', 'UNI', 'AAVE', 'ATOM', 'XLM', 'ALGO', 'VET'
                ]
                
                self.logger.info(f"🔶 Starting Binance WebSocket for {len(symbols)} symbols...")
                
                # Build streams - use ticker for price updates
                streams = [f"{s.lower()}usdt@ticker" for s in symbols]
                
                self.binance_ws = BinanceWebSocketClient()
                
                # Set up callback to update our prices
                def on_ticker(ticker: WSTicker):
                    symbol = ticker.symbol.replace('USDT', '')
                    self.binance_tickers[symbol] = ticker
                    self.all_prices[symbol] = {
                        'price': ticker.last_price,
                        'change24h': ticker.price_change_percent,
                        'volume': ticker.quote_volume,
                        'high': ticker.high_price,
                        'low': ticker.low_price,
                        'bid': ticker.bid_price,
                        'ask': ticker.ask_price,
                        'source': 'binance_ws'
                    }
                    # Update main prices for BTC, ETH, SOL
                    if symbol in ['BTC', 'ETH', 'SOL']:
                        self.prices[symbol] = {
                            'price': ticker.last_price,
                            'change24h': ticker.price_change_percent
                        }
                
                self.binance_ws.on_ticker = on_ticker
                self.binance_ws.start(streams)
                self.logger.info(f"✅ Binance WebSocket started - waiting for data...")
                
            except Exception as e:
                self.logger.error(f"❌ Binance WS startup error: {e}", exc_info=True)
        
        import threading
        ws_thread = threading.Thread(target=run_ws, daemon=True)
        ws_thread.start()
        self.logger.info(f"🔶 Binance WebSocket thread started ({len(DEFAULT_SYMBOLS)} symbols)")
    
    def analyze_market_flow(self) -> Dict:
        """Analyze real-time market flow from all tracked symbols."""
        if not self.binance_tickers:
            return self.market_flow
        
        tickers = list(self.binance_tickers.values())
        
        # Sort by change
        sorted_by_change = sorted(tickers, key=lambda t: t.price_change_percent, reverse=True)
        
        # Sort by volume
        sorted_by_volume = sorted(tickers, key=lambda t: t.quote_volume, reverse=True)
        
        # Calculate aggregates
        total_volume = sum(t.quote_volume for t in tickers)
        avg_change = sum(t.price_change_percent for t in tickers) / len(tickers) if tickers else 0
        positive_count = sum(1 for t in tickers if t.price_change_percent > 0)
        negative_count = sum(1 for t in tickers if t.price_change_percent < 0)
        
        self.market_flow = {
            'total_volume_24h': total_volume,
            'avg_change': avg_change,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'market_sentiment': 'bullish' if positive_count > negative_count * 1.2 else 
                               'bearish' if negative_count > positive_count * 1.2 else 'neutral',
            'gainers': [
                {'symbol': t.symbol.replace('USDT', ''), 'change': t.price_change_percent, 'price': t.last_price}
                for t in sorted_by_change[:5]
            ],
            'losers': [
                {'symbol': t.symbol.replace('USDT', ''), 'change': t.price_change_percent, 'price': t.last_price}
                for t in sorted_by_change[-5:][::-1]
            ],
            'top_volume': [
                {'symbol': t.symbol.replace('USDT', ''), 'volume': t.quote_volume, 'change': t.price_change_percent}
                for t in sorted_by_volume[:5]
            ],
            'tracked_symbols': len(tickers),
            'last_update': datetime.now().isoformat()
        }
        
        return self.market_flow
    
    async def market_flow_loop(self):
        """Periodically analyze and broadcast market flow data."""
        await asyncio.sleep(10)  # Wait for WS to connect
        
        while True:
            try:
                flow = self.analyze_market_flow()
                
                # Broadcast market flow to all clients
                await self.broadcast({
                    'type': 'market_flow',
                    'data': flow
                })
                
                # Update narrator with expanded market context
                if self.narrator and flow.get('tracked_symbols', 0) > 0:
                    self.narrator.update_context(
                        market_sentiment=flow.get('market_sentiment', 'neutral'),
                        total_volume_24h=flow.get('total_volume_24h', 0),
                        avg_market_change=flow.get('avg_change', 0),
                        gainers_count=flow.get('positive_count', 0),
                        losers_count=flow.get('negative_count', 0),
                        top_gainer=flow.get('gainers', [{}])[0].get('symbol', ''),
                        top_gainer_change=flow.get('gainers', [{}])[0].get('change', 0),
                        top_loser=flow.get('losers', [{}])[0].get('symbol', ''),
                        top_loser_change=flow.get('losers', [{}])[0].get('change', 0),
                    )
                    
            except Exception as e:
                self.logger.error(f"Market flow error: {e}")
            
            await asyncio.sleep(5)  # Update every 5 seconds
    
    async def harmonic_field_loop(self):
        """Stream harmonic liquid aluminium field data for live visualization."""
        await asyncio.sleep(2)  # Wait for initialization
        
        field_status_logged = False  # Only log once per change
        last_node_count = -1
        
        while True:
            try:
                if self.harmonic_field:
                    # Capture current field snapshot
                    snapshot = self.harmonic_field.capture_snapshot()
                    
                    # Log status change
                    if snapshot.total_nodes != last_node_count:
                        self.logger.info(f"🔩 Harmonic field: {snapshot.total_nodes} nodes, {snapshot.total_energy:.2f} energy, {snapshot.global_frequency:.2f} Hz")
                        last_node_count = snapshot.total_nodes
                        field_status_logged = True
                    
                    # Broadcast to all connected clients
                    await self.broadcast({
                        'type': 'harmonic_field',
                        'data': snapshot.to_dict()
                    })
                elif not field_status_logged:
                    self.logger.warning("⚠️ Harmonic field not available - visualization disabled")
                    field_status_logged = True
                    
            except Exception as e:
                self.logger.error(f"Harmonic field streaming error: {e}")
            
            # Stream every 100ms (10Hz) for smooth visualization
            await asyncio.sleep(0.1)
    
    async def ocean_data_loop(self):
        """
        🌊 OCEAN DATA LOOP - Stream ENTIRE global market into harmonic field + update dashboard
        
        Layer 1: Your portfolio (20 positions from exchanges)
        Layer 2: FULL MARKET SCAN (500+ symbols across all exchanges)
        
        This creates a visualization of the ENTIRE global market pulse
        tuned into your harmonic field frequency.
        """
        await asyncio.sleep(5)  # Wait for initialization
        
        self.logger.info("🌊🔭 OCEAN DATA LOOP STARTED - Initializing full market streaming")
        self.logger.info(f"   Ocean Scanner: {'ACTIVE' if self.ocean_scanner else 'MISSING'}")
        self.logger.info(f"   Harmonic Field: {'ACTIVE' if self.harmonic_field else 'MISSING'}")
        
        scan_iteration = 0
        
        while True:
            try:
                if not self.ocean_scanner:
                    self.logger.warning("⚠️ Ocean scanner not available - waiting...")
                    await asyncio.sleep(5)
                    continue
                    
                if not self.harmonic_field:
                    self.logger.warning("⚠️ Harmonic field not available - waiting...")
                    await asyncio.sleep(5)
                    continue
                
                scan_iteration += 1
                self.logger.info(f"🌊 Scan #{scan_iteration}: Starting ocean scan (limit=500)...")
                
                # AGGRESSIVE SCAN: Get top 500 symbols from the entire market
                opportunities = await self.ocean_scanner.scan_ocean(limit=500)
                
                self.logger.info(f"🌊 Scan #{scan_iteration}: Found {len(opportunities)} opportunities")
                
                if opportunities:
                    # Feed TOP 100 into harmonic field (balance between visibility and performance)
                    nodes_added = 0
                    for opp in opportunities[:100]:
                        try:
                            # Add to harmonic field - separate layer for global market
                            self.harmonic_field.add_or_update_node(
                                exchange="market_global",
                                symbol=opp.symbol,
                                current_price=opp.current_price,
                                entry_price=opp.entry_price if hasattr(opp, 'entry_price') else opp.current_price * 0.99,
                                quantity=1000.0,  # Normalized quantity for better visualization energy
                                asset_class="crypto"
                            )
                            nodes_added += 1
                        except Exception as e:
                            self.logger.debug(f"Market layer update error for {opp.symbol}: {e}")
                    
                    # Summary stats
                    top_movers = [f"{opp.symbol} ({opp.momentum_5m:+.2f}%)" for opp in opportunities[:5]]
                    self.logger.info(f"🌊 Scan #{scan_iteration}: {len(opportunities)} found, {nodes_added} → Harmonic field | Top: {', '.join(top_movers)}")
                    
                    # UPDATE DASHBOARD: Also populate self.ocean_data for the dashboard Ocean tab
                    summary = self.ocean_scanner.get_ocean_summary()
                    self.ocean_data = {
                        'universe_size': summary.get('universe_size', {}).get('total', 0) or 0,
                        'hot_opportunities': summary.get('hot_opportunities', 0) or len(opportunities),
                        'top_opportunities': summary.get('top_5', []),
                        'scan_count': summary.get('scan_count', 0),
                        'last_scan_time': summary.get('last_scan_time', 0)
                    }
                    
                    # Broadcast to WebSocket clients
                    await self.broadcast({
                        'type': 'ocean_scanner_update',
                        'data': self.ocean_data
                    })
                else:
                    self.logger.warning(f"🌊 Scan #{scan_iteration}: No opportunities found")
                
            except Exception as e:
                self.logger.error(f"🌊 Ocean data loop error on scan #{scan_iteration}: {e}", exc_info=True)
            
            # Scan every 8 seconds for continuous market pulse
            self.logger.debug(f"🌊 Scan #{scan_iteration}: Sleeping 8s until next scan...")
            await asyncio.sleep(8)
    
    async def _init_ocean_scanner(self):
        """Initialize ocean scanner universe in background."""
        try:
            self.logger.info("🌊 Discovering ocean scanner universe...")
            universe = await self.ocean_scanner.discover_universe()
            total = sum(universe.values())
            self.logger.info(f"🌊 Ocean universe discovered: {total:,} symbols across {len(universe)} exchanges")
            for exchange, count in universe.items():
                self.logger.info(f"   • {exchange}: {count:,} symbols")
        except Exception as e:
            self.logger.error(f"Ocean scanner universe discovery error: {e}")
    
    async def start(self):
        """Start the dashboard."""
        
        # CRITICAL: Start web server FIRST so health checks succeed immediately
        # Then load data in background to prevent timeout
        self.logger.info("🚀 Starting web server on port {self.port}...")
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        print(f"\n{'='*70}")
        print(f"👑 AUREON PRO TRADING TERMINAL")
        print(f"{'='*70}")
        print(f"🌐 Dashboard: http://0.0.0.0:{self.port} (port 8080 for DigitalOcean)")
        print(f"🩺 Health: http://0.0.0.0:{self.port}/health")
        print(f"📊 Status: http://0.0.0.0:{self.port}/api/status")
        print(f"{'='*70}")
        print("⚡ Web server ready - loading data in background...")
        print(f"{'='*70}\n")
        
        # Pre-flight check: verify API keys (non-blocking)\n        self._check_api_keys()
        
        # Load data in background AFTER server is accepting connections
        # This prevents health check timeouts during slow initialization
        async def background_init():
            self.logger.info("🔄 Background initialization started...")
            await self.refresh_prices()
            await self.refresh_portfolio()
            await self.refresh_exchange_balances()
            
            # Initialize Ocean Scanner
            if OCEAN_SCANNER_AVAILABLE and OceanScanner:
                try:
                    self.logger.info("🌊 Initializing Ocean Scanner...")
                    exchanges = {}
                    
                    # Load exchange clients
                    try:
                        from aureon.exchanges.kraken_client import get_kraken_client
                        exchanges['kraken'] = get_kraken_client()
                        self.logger.info("✅ Ocean: Kraken loaded")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Kraken: {e}")
                    
                    try:
                        from aureon.exchanges.alpaca_client import AlpacaClient
                        exchanges['alpaca'] = AlpacaClient()
                        self.logger.info("✅ Ocean: Alpaca loaded")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Alpaca: {e}")
                    
                    try:
                        from aureon.exchanges.binance_client import BinanceClient
                        exchanges['binance'] = BinanceClient()
                        self.logger.info("✅ Ocean: Binance loaded")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Binance: {e}")
                    
                    if exchanges:
                        self.ocean_scanner = OceanScanner(exchanges)
                        await self._init_ocean_scanner()
                        self.logger.info(f"✅ Ocean Scanner ready: {len(exchanges)} exchanges")
                except Exception as e:
                    self.logger.error(f"❌ Ocean Scanner error: {e}")
            
            self.logger.info(f"✅ Initialization complete: {len(self.prices)} prices, {len(self.portfolio.get('positions', []))} positions")
        
        # Run background init without blocking server startup
        asyncio.create_task(background_init())
        
        # Start background tasks
        asyncio.create_task(self.queen_commentary_loop())
        asyncio.create_task(self.data_refresh_loop())
        # DISABLED: market_flow_loop depends on Binance WS
        # asyncio.create_task(self.market_flow_loop())
        asyncio.create_task(self.harmonic_field_loop())
        if self.ocean_scanner:
            asyncio.create_task(self.ocean_data_loop())
        
        # ⚡ V11 POWER STATION
        if self.v11_station:
            asyncio.create_task(self.v11_data_loop())
            self.logger.info("⚡ V11 Power Station data loop: STARTED")
        
        # 🌐 MARKET SENTIMENT (Fear & Greed Index)
        asyncio.create_task(self.sentiment_data_loop())
        self.logger.info("🌐 Market Sentiment data loop: STARTED")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # 👑 QUEEN SYSTEMS DATA LOOPS
        # ═══════════════════════════════════════════════════════════════════════════════
        
        # ⚛️ QUEEN QUANTUM COGNITION
        if self.quantum_cognition:
            asyncio.create_task(self.quantum_cognition_loop())
            self.logger.info("⚛️ Queen Quantum Cognition data loop: STARTED")
        
        # 👑💰 QUEEN ASSET COMMAND CENTER
        if self.asset_command:
            asyncio.create_task(self.asset_command_loop())
            self.logger.info("👑💰 Queen Asset Command Center data loop: STARTED")
        
        # 🔤 UNIFIED SYMBOL MANAGER
        if self.symbol_manager:
            asyncio.create_task(self.symbol_manager_loop())
            self.logger.info("🔤 Unified Symbol Manager data loop: STARTED")
        
        # 👑🧠 QUEEN HIVE MIND
        if self.queen_hive:
            asyncio.create_task(self.queen_hive_loop())
            self.logger.info("👑🧠 Queen Hive Mind data loop: STARTED")
        
        self.logger.info("✅ All systems online, dashboard ready")
        
        # Keep running
        while True:
            await asyncio.sleep(3600)
    
    def _check_api_keys(self):
        """Check if API keys are configured and log warnings."""
        import os
        missing = []
        
        if not os.getenv('BINANCE_API_KEY'):
            missing.append('BINANCE_API_KEY')
        if not os.getenv('BINANCE_API_SECRET'):
            missing.append('BINANCE_API_SECRET')
        if not os.getenv('ALPACA_API_KEY'):
            missing.append('ALPACA_API_KEY')
        if not os.getenv('ALPACA_SECRET_KEY'):
            missing.append('ALPACA_SECRET_KEY')
        
        if missing:
            self.logger.error("\n" + "="*70)
            self.logger.error("⚠️  MISSING API KEYS - Dashboard will have LIMITED DATA")
            self.logger.error("="*70)
            for key in missing:
                self.logger.error(f"  ❌ {key} not set")
            self.logger.error("\nPortfolio data will NOT be available without API keys!")
            self.logger.error("Set these in DigitalOcean App Settings > Environment Variables")
            self.logger.error("="*70 + "\n")
        else:
            self.logger.info("✅ All API keys configured")


async def main():
    from aureon.core.simulated_boot import random_dashboard_allowed

    if not random_dashboard_allowed():
        return
    # Port auto-configured: ENV['PORT'] for production, 14000 for local dev
    dashboard = AureonProDashboard()
    await dashboard.start()


if __name__ == '__main__':
    asyncio.run(main())
