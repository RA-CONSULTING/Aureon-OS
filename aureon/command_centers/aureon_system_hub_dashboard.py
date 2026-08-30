#!/usr/bin/env python3
"""
🌌 AUREON SYSTEM HUB - WEB DASHBOARD
=====================================
Interactive mind map visualization of all Aureon systems.

Features:
- Force-directed graph visualization
- Category filtering
- System search
- Real-time status monitoring
- Direct dashboard links
- System dependency mapping

Port: 13001
URL: http://localhost:13001

Author: Aureon Trading System
Date: January 2026
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
        if hasattr(sys.stderr, 'buffer') and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

from flask import Flask, render_template_string, jsonify, request
from aureon.command_centers.aureon_system_hub import SystemRegistry
from aureon.core.aureon_thought_bus import get_thought_bus
from aureon.core.metrics import dump_metrics
import json
from pathlib import Path
import subprocess
import psutil
from datetime import datetime
from collections import deque, defaultdict
import importlib.util
import threading
import time
import socket
import math

# Sacred constants (from other dashboards)
PHI = (1 + math.sqrt(5)) / 2
SCHUMANN = 7.83
LOVE_FREQ = 528

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORT ALL INTELLIGENCE SYSTEMS (Consolidated from all dashboards)
# ═══════════════════════════════════════════════════════════════════════════════
SYSTEMS_STATUS = {}

# Core Intelligence Layer
try:
    from aureon.bots_intelligence.aureon_bot_intelligence_profiler import BotIntelligenceProfiler, TRADING_FIRM_SIGNATURES
    SYSTEMS_STATUS['Bot Intelligence'] = True
except ImportError:
    SYSTEMS_STATUS['Bot Intelligence'] = False
    TRADING_FIRM_SIGNATURES = {}

# Queen Voice Engine (from queen_web_dashboard)
try:
    from aureon.queen.queen_voice_engine import QueenVoiceEngine, queen_voice
    SYSTEMS_STATUS['Voice Engine'] = True
except ImportError:
    SYSTEMS_STATUS['Voice Engine'] = False
    queen_voice = None

# Open Source Data Engine (from queen_web_dashboard)
try:
    from aureon.queen.queen_open_source_data_engine import OpenSourceDataEngine, get_data_engine
    SYSTEMS_STATUS['Open Data Engine'] = True
except ImportError:
    SYSTEMS_STATUS['Open Data Engine'] = False

# Deep Intelligence (from queen_web_dashboard)
try:
    from aureon.queen.queen_deep_intelligence import QueenDeepIntelligence, DeepInsight
    SYSTEMS_STATUS['Deep Intelligence'] = True
except ImportError:
    SYSTEMS_STATUS['Deep Intelligence'] = False

# Orca Intelligence
try:
    from aureon.bots_intelligence.aureon_orca_intelligence import get_orca
    SYSTEMS_STATUS['Orca Intelligence'] = True
except ImportError:
    SYSTEMS_STATUS['Orca Intelligence'] = False

# Counter-Intelligence
try:
    from aureon.utils.aureon_queen_counter_intelligence import QueenCounterIntelligence
    SYSTEMS_STATUS['Counter Intelligence'] = True
except ImportError:
    SYSTEMS_STATUS['Counter Intelligence'] = False

# Whale Tracker
try:
    from aureon.analytics.aureon_whale_orderbook_analyzer import WhaleOrderbookAnalyzer
    SYSTEMS_STATUS['Whale Analyzer'] = True
except ImportError:
    SYSTEMS_STATUS['Whale Analyzer'] = False

# Wave Scanner
try:
    from aureon.scanners.aureon_global_wave_scanner import GlobalWaveScanner
    SYSTEMS_STATUS['Wave Scanner'] = True
except ImportError:
    SYSTEMS_STATUS['Wave Scanner'] = False

# Timeline Oracle
try:
    from aureon.intelligence.aureon_timeline_oracle import TimelineOracle
    SYSTEMS_STATUS['Timeline Oracle'] = True
except ImportError:
    SYSTEMS_STATUS['Timeline Oracle'] = False

# Quantum Telescope
try:
    from aureon.simulation.aureon_quantum_telescope import QuantumPrism
    SYSTEMS_STATUS['Quantum Telescope'] = True
except ImportError:
    SYSTEMS_STATUS['Quantum Telescope'] = False

# Elephant Memory
try:
    from aureon.intelligence.aureon_elephant_learning import ElephantMemory
    SYSTEMS_STATUS['Elephant Memory'] = True
except ImportError:
    SYSTEMS_STATUS['Elephant Memory'] = False

# Queen Hive Mind
try:
    from aureon.utils.aureon_queen_hive_mind import QueenHiveMind
    SYSTEMS_STATUS['Queen Hive Mind'] = True
except ImportError:
    SYSTEMS_STATUS['Queen Hive Mind'] = False

# Probability Nexus
try:
    from aureon.bridges.aureon_probability_nexus import AureonProbabilityNexus
    SYSTEMS_STATUS['Probability Nexus'] = True
except ImportError:
    SYSTEMS_STATUS['Probability Nexus'] = False

# Ultimate Intelligence
try:
    from aureon.strategies.probability_ultimate_intelligence import ProbabilityUltimateIntelligence
    SYSTEMS_STATUS['Ultimate Intelligence'] = True
except ImportError:
    SYSTEMS_STATUS['Ultimate Intelligence'] = False

# Enigma Decoder
try:
    from aureon.wisdom.aureon_enigma import AureonEnigma
    SYSTEMS_STATUS['Enigma Decoder'] = True
except ImportError:
    SYSTEMS_STATUS['Enigma Decoder'] = False

# Mycelium Network
try:
    from aureon.core.aureon_mycelium import MyceliumNetwork
    SYSTEMS_STATUS['Mycelium Network'] = True
except ImportError:
    SYSTEMS_STATUS['Mycelium Network'] = False

# Miner Brain
try:
    from aureon.utils.aureon_miner_brain import MinerBrain
    SYSTEMS_STATUS['Miner Brain'] = True
except ImportError:
    SYSTEMS_STATUS['Miner Brain'] = False

# Harmonic Fusion
try:
    from aureon.harmonic.aureon_harmonic_fusion import HarmonicWaveFusion
    SYSTEMS_STATUS['Harmonic Fusion'] = True
except ImportError:
    SYSTEMS_STATUS['Harmonic Fusion'] = False

# Firm Geocoder (from queen_web_dashboard)
try:
    from aureon.queen.queen_firm_geocoder import get_firm_coordinates, get_all_firm_locations
    SYSTEMS_STATUS['Firm Geocoder'] = True
except ImportError:
    SYSTEMS_STATUS['Firm Geocoder'] = False

print(f"🧠 INTELLIGENCE SYSTEMS: {sum(SYSTEMS_STATUS.values())} / {len(SYSTEMS_STATUS)} ONLINE")

# ═══════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
registry = SystemRegistry()

ACTIVE_POSITION_FILE = "active_position.json"
ELEPHANT_HISTORY_FILE = "elephant_unified_history.jsonl"
THOUGHTS_FILE = "thoughts.jsonl"
LIVE_THOUGHT_LIMIT = 50

UNIFIED_MARGIN_LAYERS = [
    {
        "id": "harmonic",
        "label": "Harmonic Layer",
        "overseers": ["seer", "laura"],
        "module_guardians": ["Harmonic Fusion", "Wave Scanner", "Timeline Oracle"],
        "thought_topics": ["harmonic.*", "wave.*", "timeline.*"],
    },
    {
        "id": "financial_analytic",
        "label": "Financial + Analytic Layer",
        "overseers": ["king_module"],
        "module_guardians": ["Bot Intelligence", "Probability Nexus", "Ultimate Intelligence"],
        "thought_topics": ["market.*", "orderbook.*", "analytics.*"],
    },
    {
        "id": "planetary_coherence",
        "label": "Planetary Coherence Layer",
        "overseers": ["laura", "queen_hive_main_module"],
        "module_guardians": ["Quantum Telescope", "Open Data Engine", "Mycelium Network"],
        "thought_topics": ["planetary.*", "coherence.*", "stargate.*"],
    },
    {
        "id": "margin_unified",
        "label": "Unified Margin Trader Layer",
        "overseers": ["seer", "emerald_tablet_payphone"],
        "module_guardians": ["Queen Hive Mind", "Orca Intelligence", "Counter Intelligence"],
        "thought_topics": ["margin.*", "signal.*", "position.*"],
    },
]

UNIFIED_MARGIN_WEBSOCKETS = [
    {"name": "yahoo_finance", "status_key": "financial_feed", "required": True},
    {"name": "geopolitical", "status_key": "geopolitical_feed", "required": True},
    {"name": "harmonic_layers", "status_key": "harmonic_feed", "required": True},
    {"name": "thought_bus", "status_key": "thought_bus", "required": True},
]

UNIFIED_WAVEFORM_REJECTION_THRESHOLD = 0.35
UNIFIED_WAVEFORM_KEEPALIVE_TOPICS = (
    "wave.",
    "ocean.",
    "momentum.",
    "scanner.wave",
    "scanner.opportunity",
)

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL STATE - Combined from all dashboards
# ═══════════════════════════════════════════════════════════════════════════════
class GlobalDashboardState:
    """Unified state for all dashboard features"""
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
        
        # Whale Sonar metrics
        self.whale_signals = {}
        self.whale_alerts = 0
        
        # Open Data metrics
        self.fear_greed_index = 50
        self.fear_greed_label = "Neutral"
        self.market_data = {}
        self.trending_coins = []
        
        # System metrics
        self.neural_connections = 0
        self.signals_decoded = 0
        self.patterns_remembered = 0
        self.timeline_predictions = 0
        self.quantum_coherence = 0.0
        
    def add_queen_message(self, message: str, level: str = "info"):
        self.queen_messages.append({
            "message": message,
            "level": level,
            "ts": time.time()
        })

# Global state instance
dashboard_state = GlobalDashboardState()


def _safe_load_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _resolve_thoughts_file() -> Path:
    """The shared cross-process thought stream.

    This dashboard read ``aureon/command_centers/thoughts.jsonl`` while the live runner it
    spawns wrote ``aureon/trading/thoughts.jsonl`` — two different files, so the panels fed
    by the runner were permanently empty. Both now resolve the same path, overridable with
    ``AUREON_THOUGHTS_FILE``.
    """
    override = os.getenv("AUREON_THOUGHTS_FILE", "").strip()
    return Path(override) if override else Path(__file__).resolve().parents[2] / "thoughts.jsonl"


THOUGHTS_FILE = _resolve_thoughts_file()

DASHBOARD_LINKS = [
    {
        "label": "📊 Queen Web",
        "url": "http://localhost:5000",
        "port": 5000,
        "start_hint": "python queen_web_dashboard.py",
    },
    {
        "label": "🤖 Bot Hunter",
        "url": "http://localhost:9999",
        "port": 9999,
        "start_hint": "python aureon_bot_hunter_dashboard.py",
    },
    {
        "label": "👑 Queen Unified",
        "url": "http://localhost:13000",
        "port": 13000,
        "start_hint": "python aureon_queen_unified_dashboard.py",
    },
    {
        "label": "🗺️ Global Bot Map",
        "url": "http://localhost:12000",
        "port": 12000,
        "start_hint": "python aureon_global_bot_map.py",
    },
    {
        "label": "👁️ Surveillance",
        "url": "http://localhost:8888",
        "port": 8888,
        "start_hint": "python aureon_surveillance_dashboard.py",
    },
]

# The runner lives in aureon/trading/, not next to this dashboard — the old
# Path(__file__).parent path never existed, so _ensure_live_runner() always failed
# silently and reported "not detected".
LIVE_RUNNER_SCRIPT = Path(__file__).resolve().parents[1] / "trading" / "aureon_queen_live_runner.py"


def _check_port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _dashboard_statuses() -> list:
    statuses = []
    for entry in DASHBOARD_LINKS:
        online = _check_port_open(entry["port"])
        statuses.append({
            "label": entry["label"],
            "url": entry["url"],
            "port": entry["port"],
            "online": online,
            "start_hint": entry.get("start_hint", ""),
        })
    return statuses


def _is_process_running(match: str) -> bool:
    try:
        for proc in psutil.process_iter(["cmdline", "name"]):
            cmdline = proc.info.get("cmdline") or []
            if any(match in part for part in cmdline):
                return True
    except Exception:
        return False
    return False


def _autostart_live_runner_allowed() -> bool:
    """Spawning a data producer from a dashboard is opt-in.

    With the path bug above fixed this function would suddenly start launching a
    background process on every dashboard boot, which nobody asked for. Opening a
    dashboard stays a read-only act unless the operator says otherwise.
    """
    return os.getenv("AUREON_AUTOSTART_LIVE_RUNNER", "").strip().lower() in {"1", "true", "yes", "on"}


def _ensure_live_runner() -> bool:
    if _is_process_running("aureon_queen_live_runner.py"):
        return True
    if not LIVE_RUNNER_SCRIPT.exists() or not _autostart_live_runner_allowed():
        return False
    try:
        subprocess.Popen(
            [sys.executable, str(LIVE_RUNNER_SCRIPT)],
            cwd=str(Path(__file__).resolve().parents[2]),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False

def _read_recent_thoughts(limit: int = 100) -> list:
    """Read recent thoughts directly from file (cross-process safe)."""
    try:
        if not THOUGHTS_FILE.exists():
            return []
        
        # Read last N lines efficiently
        lines = deque(maxlen=limit)
        with open(THOUGHTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip():
                    lines.append(line.strip())
        
        thoughts = []
        for line in lines:
            try:
                thought = json.loads(line)
                # Filter out internal ThoughtBus wrapper events to reduce noise
                if thought.get("source") == "thought_bus_think":
                    continue
                thoughts.append({
                    "id": thought.get("id", ""),
                    "ts": thought.get("ts", 0),
                    "source": thought.get("source", "unknown"),
                    "topic": thought.get("topic", ""),
                    "payload": thought.get("payload", {}),
                })
            except Exception:
                continue
        
        # Return in reverse order (most recent first)
        return list(reversed(thoughts))
    except Exception as e:
        print(f"Error reading thoughts: {e}")
        return []


def _read_last_jsonl(path: str, limit: int = 200) -> list:
    try:
        lines = deque(maxlen=limit)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip():
                    lines.append(line.strip())
        events = []
        for line in lines:
            try:
                events.append(json.loads(line))
            except Exception:
                continue
        return events
    except Exception:
        return []


def _extract_revenue(events: list) -> dict:
    results = [e for e in events if e.get("type") == "result" and "profit" in e]
    total_profit = sum(float(e.get("profit", 0.0)) for e in results)
    last_trade = results[-1] if results else None
    return {
        "recent_trade_count": len(results),
        "recent_profit_sum": total_profit,
        "last_trade": last_trade,
    }


def _latest_queen_signal(events: list) -> float:
    for e in reversed(events):
        if e.get("type") == "event" and e.get("event_type") == "mycelium_heartbeat":
            payload = e.get("payload", {})
            try:
                return float(payload.get("queen_signal", 0.0))
            except Exception:
                return 0.0
    return 0.0


def _autonomy_available() -> bool:
    return importlib.util.find_spec("aureon_queen_autonomous_control") is not None


def _build_timeseries(events: list) -> dict:
    queen_series = []
    profit_series = []
    trade_count_series = []
    trade_count = 0
    for e in events:
        ts = e.get("ts") or e.get("timestamp")
        if e.get("type") == "event" and e.get("event_type") == "mycelium_heartbeat":
            payload = e.get("payload", {})
            try:
                queen_series.append({"t": ts, "v": float(payload.get("queen_signal", 0.0))})
            except Exception:
                pass
        if e.get("type") == "result" and "profit" in e:
            try:
                profit_series.append({"t": ts, "v": float(e.get("profit", 0.0))})
                trade_count += 1
                trade_count_series.append({"t": ts, "v": trade_count})
            except Exception:
                pass

    return {
        "queen_signal": queen_series[-200:],
        "profit": profit_series[-200:],
        "trades": trade_count_series[-200:],
    }


def _build_activity_maps(thoughts: list, events: list) -> dict:
    topic_counts = defaultdict(int)
    for t in thoughts:
        topic = t.get("topic", "unknown")
        bucket = topic.split(".")[0] if "." in topic else topic
        topic_counts[bucket] += 1

    symbol_counts = defaultdict(int)
    for e in events:
        if e.get("type") == "result" and e.get("symbol"):
            symbol_counts[e.get("symbol")] += 1

    return {
        "topic_counts": dict(topic_counts),
        "symbol_counts": dict(symbol_counts),
    }


def _build_heatmap(thoughts: list, buckets: int = 12, top_topics: int = 8) -> dict:
    if not thoughts:
        return {
            "rows": 0,
            "cols": 0,
            "values": [],
            "row_labels": [],
            "col_labels": [],
        }

    # Determine time window
    ts_values = [t.get("ts", 0) for t in thoughts if t.get("ts")]
    if not ts_values:
        return {
            "rows": 0,
            "cols": 0,
            "values": [],
            "row_labels": [],
            "col_labels": [],
        }

    t_min, t_max = min(ts_values), max(ts_values)
    if t_min == t_max:
        t_max = t_min + 1

    # Top topics
    topic_counts = defaultdict(int)
    for t in thoughts:
        topic = t.get("topic", "unknown")
        bucket = topic.split(".")[0] if "." in topic else topic
        topic_counts[bucket] += 1
    top = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:top_topics]
    row_labels = [k for k, _ in top]

    # Build grid
    cols = buckets
    rows = len(row_labels)
    values = [[0 for _ in range(cols)] for _ in range(rows)]

    for t in thoughts:
        topic = t.get("topic", "unknown")
        bucket = topic.split(".")[0] if "." in topic else topic
        if bucket not in row_labels:
            continue
        try:
            ts = float(t.get("ts", t_max))
        except Exception:
            ts = t_max
        col = int((ts - t_min) / (t_max - t_min) * (cols - 1))
        row = row_labels.index(bucket)
        values[row][col] += 1

    col_labels = [str(i + 1) for i in range(cols)]

    return {
        "rows": rows,
        "cols": cols,
        "values": values,
        "row_labels": row_labels,
        "col_labels": col_labels,
    }


def _build_orderbook_spectrogram(thoughts: list) -> dict:
    series = []
    for t in thoughts:
        topic = t.get("topic", "")
        payload = t.get("payload", {}) or {}
        if "orderbook" in topic or ("bids_depth" in payload and "asks_depth" in payload):
            try:
                bids = float(payload.get("bids_depth", 0.0))
                asks = float(payload.get("asks_depth", 0.0))
                series.append({
                    "t": t.get("ts"),
                    "bids": bids,
                    "asks": asks,
                })
            except Exception:
                continue

    return {"series": series[-120:]}


def _build_exchange_map(events: list) -> dict:
    counts = defaultdict(int)
    profits = defaultdict(float)
    for e in events:
        if e.get("type") != "result":
            continue
        exchange = e.get("exchange") or e.get("exchange_name") or "unknown"
        counts[exchange] += 1
        try:
            profits[exchange] += float(e.get("profit", 0.0))
        except Exception:
            pass

    data = []
    for ex, count in counts.items():
        data.append({
            "exchange": ex,
            "count": count,
            "profit": profits.get(ex, 0.0),
        })

    return {"exchanges": data}


def _build_scanner_feed(thoughts: list) -> dict:
    market = []
    whales = []
    bots = []
    waves = []
    scanner_opportunities = []

    for t in thoughts:
        topic = t.get("topic", "")
        payload = t.get("payload", {}) or {}
        
        # Handle nested message strings (thought_bus_think wraps data)
        if isinstance(payload.get("message"), str):
            try:
                payload = json.loads(payload["message"])
            except:
                pass
        
        entry = {
            "ts": t.get("ts"),
            "topic": topic,
            "source": t.get("source"),
            "payload": payload,
        }

        if topic.startswith("market.") or topic.startswith("queen.") or topic.startswith("system.") or topic.startswith("execution."):
            market.append(entry)
        elif topic.startswith("whale."):
            whales.append(entry)
        elif topic.startswith("bot.") or topic.startswith("firm.") or topic.startswith("counter."):
            bots.append(entry)
        elif topic.startswith("wave.") or topic.startswith("ocean.") or topic.startswith("momentum.") or topic.startswith("scanner.wave"):
            waves.append(entry)
        
        # Capture scanner opportunities separately
        if topic == "scanner.opportunity" or "opportunity" in topic:
            scanner_opportunities.append({
                "ts": t.get("ts"),
                "symbol": payload.get("symbol", "UNKNOWN"),
                "type": payload.get("type", "unknown"),
                "direction": payload.get("direction", "HOLD"),
                "confidence": payload.get("confidence", 0),
                "momentum_score": payload.get("momentum_score", 0),
                "wave_state": payload.get("wave_state", ""),
                "price": payload.get("price", 0)
            })

    return {
        "market": market[:30],
        "whales": whales[:30],
        "bots": bots[:30],
        "waves": waves[:30],
        "scanner_opportunities": scanner_opportunities[:30],
    }

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌌 Aureon System Hub - Mind Map</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --bg-1: #0b0d1a;
            --bg-2: #12162b;
            --bg-3: #151a36;
            --accent: #7c5cff;
            --accent-2: #2bd3ff;
            --success: #2ee59d;
            --danger: #ff6b6b;
            --text: #f5f7ff;
            --muted: #b5b9d1;
            --card: rgba(255, 255, 255, 0.06);
            --card-border: rgba(124, 92, 255, 0.35);
            --glow: 0 0 30px rgba(124, 92, 255, 0.25);
        }

        body {
            font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: radial-gradient(1200px 600px at 20% -10%, rgba(43, 211, 255, 0.15), transparent 60%),
                        radial-gradient(1200px 600px at 90% 10%, rgba(124, 92, 255, 0.25), transparent 60%),
                        linear-gradient(135deg, var(--bg-1), var(--bg-2), var(--bg-3));
            color: var(--text);
            overflow: hidden;
        }
        
        .header {
            background: rgba(10, 12, 24, 0.7);
            padding: 18px 28px;
            border-bottom: 1px solid rgba(124, 92, 255, 0.4);
            display: flex;
            justify-content: space-between;
            align-items: center;
            backdrop-filter: blur(12px);
            box-shadow: var(--glow);
        }
        
        .header h1 {
            font-size: 24px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .stats {
            display: flex;
            gap: 16px;
            font-size: 13px;
        }
        
        .stat-item {
            background: var(--card);
            padding: 10px 14px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
        }
        
        .controls {
            background: rgba(12, 14, 26, 0.6);
            padding: 14px 28px;
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
            backdrop-filter: blur(8px);
        }

        .live-panel {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            padding: 12px 28px;
            background: rgba(10, 12, 24, 0.65);
            border-top: 1px solid rgba(124, 92, 255, 0.25);
            border-bottom: 1px solid rgba(124, 92, 255, 0.25);
            box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.25);
        }

        .live-card {
            background: var(--card);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 12px 14px;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.25);
        }

        .live-card .title {
            font-size: 11px;
            text-transform: uppercase;
            color: var(--muted);
            letter-spacing: 0.6px;
        }

        .live-card .value {
            font-size: 14px;
            margin-top: 6px;
            color: var(--text);
            word-break: break-word;
        }

        .viz-canvas {
            width: 100%;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
        }

        .viz-tooltip {
            position: absolute;
            background: rgba(0, 0, 0, 0.75);
            color: #fff;
            padding: 6px 8px;
            border-radius: 6px;
            font-size: 11px;
            pointer-events: none;
            display: none;
            z-index: 2000;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .feed-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 12px;
            padding: 12px 28px 0 28px;
        }

        .feed-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }

        .feed-table th,
        .feed-table td {
            padding: 6px 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            text-align: left;
            vertical-align: top;
        }

        .feed-table th {
            color: var(--muted);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.6px;
        }
        
        .search-box {
            flex: 1;
            min-width: 280px;
            padding: 10px 14px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(124, 92, 255, 0.4);
            border-radius: 10px;
            color: var(--text);
            font-size: 13px;
            outline: none;
            box-shadow: inset 0 0 0 1px rgba(124, 92, 255, 0.08);
        }
        
        .filter-btn {
            padding: 9px 14px;
            background: rgba(124, 92, 255, 0.18);
            border: 1px solid rgba(124, 92, 255, 0.5);
            border-radius: 10px;
            color: var(--text);
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 12px;
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
        }
        
        .filter-btn:hover {
            background: rgba(124, 92, 255, 0.45);
            transform: translateY(-1px);
        }
        
        .filter-btn.active {
            background: linear-gradient(135deg, var(--accent), var(--accent-2));
            border: none;
            box-shadow: 0 0 24px rgba(124, 92, 255, 0.5);
        }
        
        #network-container {
            height: calc(100vh - 240px);
            background: radial-gradient(circle at 20% 20%, rgba(124, 92, 255, 0.08), transparent 40%),
                        radial-gradient(circle at 80% 20%, rgba(43, 211, 255, 0.08), transparent 40%),
                        rgba(0, 0, 0, 0.25);
            border-top: 1px solid rgba(255, 255, 255, 0.08);
        }
        
        .sidebar {
            position: fixed;
            right: 0;
            top: 240px;
            width: 360px;
            height: calc(100vh - 240px);
            background: rgba(10, 12, 24, 0.9);
            backdrop-filter: blur(16px);
            border-left: 1px solid rgba(124, 92, 255, 0.35);
            padding: 20px;
            overflow-y: auto;
            transform: translateX(360px);
            transition: transform 0.3s;
            z-index: 1000;
        }
        
        .sidebar.open {
            transform: translateX(0);
        }
        
        .sidebar h3 {
            color: #6C5CE7;
            margin-bottom: 15px;
            font-size: 18px;
        }
        
        .sidebar .detail-row {
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .sidebar .label {
            color: #aaa;
            font-size: 12px;
            text-transform: uppercase;
        }
        
        .sidebar .value {
            color: #fff;
            font-size: 14px;
            margin-top: 5px;
        }
        
        .badge {
            display: inline-block;
            padding: 3px 8px;
            background: rgba(108, 92, 231, 0.3);
            border-radius: 3px;
            font-size: 11px;
            margin-right: 5px;
            margin-top: 5px;
        }
        
        .badge.green {
            background: rgba(0, 184, 148, 0.3);
            border: 1px solid #00B894;
        }
        
        .badge.red {
            background: rgba(255, 107, 107, 0.3);
            border: 1px solid #FF6B6B;
        }

        .badge.blue {
            background: rgba(116, 185, 255, 0.3);
            border: 1px solid #74B9FF;
        }
        
        .legend {
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            max-width: 300px;
        }
        
        .legend h4 {
            margin-bottom: 10px;
            color: #6C5CE7;
            font-size: 14px;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
            font-size: 12px;
        }
        
        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border: 2px solid rgba(255, 255, 255, 0.3);
        }
        
        .dashboard-links {
            position: fixed;
            top: 160px;
            left: 20px;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            max-width: 250px;
        }
        
        .dashboard-links h4 {
            margin-bottom: 10px;
            color: #6C5CE7;
            font-size: 14px;
        }
        
        .dashboard-link {
            display: block;
            padding: 8px 12px;
            background: rgba(108, 92, 231, 0.2);
            border: 1px solid rgba(108, 92, 231, 0.5);
            border-radius: 5px;
            color: #fff;
            text-decoration: none;
            margin-bottom: 8px;
            font-size: 12px;
            transition: all 0.3s;
        }

        .dashboard-link.offline {
            opacity: 0.6;
            cursor: not-allowed;
            pointer-events: none;
        }
        
        .dashboard-link:hover {
            background: rgba(108, 92, 231, 0.4);
            transform: translateX(5px);
        }
        
        .close-sidebar {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255, 107, 107, 0.3);
            border: 1px solid #FF6B6B;
            color: #fff;
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
        }
        
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(0, 0, 0, 0.3);
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(108, 92, 231, 0.5);
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1><span>🌌</span> Aureon System Hub</h1>
        <div class="stats">
            <div class="stat-item">
                <strong id="total-systems">0</strong> Systems
            </div>
            <div class="stat-item">
                <strong id="total-categories">0</strong> Categories
            </div>
            <div class="stat-item">
                <strong id="active-dashboards">0</strong> Dashboards
            </div>
            <div class="stat-item">
                <strong id="running-systems">0</strong> Running
            </div>
        </div>
    </div>
    
    <div class="controls">
        <input type="text" id="search" class="search-box" placeholder="🔍 Search systems...">
        <button class="filter-btn active" data-category="all">All Systems</button>
        <div id="category-filters"></div>
        <button class="filter-btn" onclick="resetView()">Reset View</button>
    </div>

    <div class="live-panel">
        <div class="live-card">
            <div class="title">Queen Signal</div>
            <div class="value" id="live-queen-signal">—</div>
        </div>
        <div class="live-card">
            <div class="title">Last Trade</div>
            <div class="value" id="live-last-trade">—</div>
        </div>
        <div class="live-card">
            <div class="title">Revenue (Recent)</div>
            <div class="value" id="live-revenue">—</div>
        </div>
        <div class="live-card">
            <div class="title">Open Position</div>
            <div class="value" id="live-open-position">—</div>
        </div>
        <div class="live-card">
            <div class="title">Latest Thought</div>
            <div class="value" id="live-last-thought">—</div>
        </div>
        <div class="live-card">
            <div class="title">Live Runner</div>
            <div class="value" id="live-runner-status">—</div>
        </div>
        <div class="live-card">
            <div class="title">Autonomy Ready</div>
            <div class="value" id="live-autonomy">—</div>
        </div>
    </div>

    <div class="live-panel" style="grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));">
        <div class="live-card">
            <div class="title">Queen Signal (Live)</div>
            <canvas id="queenSignalChart" height="140"></canvas>
        </div>
        <div class="live-card">
            <div class="title">Profit Pulse</div>
            <canvas id="profitChart" height="140"></canvas>
        </div>
        <div class="live-card">
            <div class="title">Thought Spectrograph</div>
            <canvas id="activityChart" height="140"></canvas>
        </div>
    </div>

    <div class="live-panel" style="grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));">
        <div class="live-card" style="position: relative;">
            <div class="title">Interactive Heatmap (Thought Density)</div>
            <canvas id="heatmapCanvas" class="viz-canvas" height="160"></canvas>
            <div id="heatmapTooltip" class="viz-tooltip"></div>
        </div>
        <div class="live-card" style="position: relative;">
            <div class="title">Orderbook Depth Spectrogram</div>
            <canvas id="spectrogramCanvas" class="viz-canvas" height="160"></canvas>
            <div id="spectrogramTooltip" class="viz-tooltip"></div>
        </div>
        <div class="live-card">
            <div class="title">Exchange Trade Map</div>
            <canvas id="exchangeMapChart" height="160"></canvas>
        </div>
    </div>

    <div class="feed-grid">
        <div class="live-card">
            <div class="title">Market Scanner Feed</div>
            <table class="feed-table" id="marketFeed"></table>
        </div>
        <div class="live-card">
            <div class="title">Whale Scanner Feed</div>
            <table class="feed-table" id="whaleFeed"></table>
        </div>
        <div class="live-card">
            <div class="title">Bot Scanner Feed</div>
            <table class="feed-table" id="botFeed"></table>
        </div>
        <div class="live-card">
            <div class="title">Wave Scanner Feed</div>
            <table class="feed-table" id="waveFeed"></table>
        </div>
    </div>

    <!-- Intelligence Systems Panel -->
    <div class="live-panel" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
        <div class="live-card">
            <div class="title">🧠 Intelligence Online</div>
            <div class="value" id="intel-online" style="font-size: 24px; color: #2ee59d;">—</div>
        </div>
        <div class="live-card">
            <div class="title">🐋 Whale Alerts</div>
            <div class="value" id="whale-alerts" style="font-size: 18px;">—</div>
        </div>
        <div class="live-card">
            <div class="title">🤖 Bot Events</div>
            <div class="value" id="bot-events" style="font-size: 18px;">—</div>
        </div>
        <div class="live-card">
            <div class="title">🌊 Wave Signals</div>
            <div class="value" id="wave-signals" style="font-size: 18px;">—</div>
        </div>
        <div class="live-card">
            <div class="title">📊 Quantum Coherence</div>
            <div class="value" id="quantum-coherence" style="font-size: 18px;">—</div>
        </div>
        <div class="live-card">
            <div class="title">🔮 Fear/Greed Index</div>
            <div class="value" id="fear-greed" style="font-size: 18px;">—</div>
        </div>
    </div>

    <!-- Queen Messages Panel -->
    <div class="live-panel" style="grid-template-columns: 1fr;">
        <div class="live-card" style="background: rgba(124, 92, 255, 0.15);">
            <div class="title">👑 Queen's Voice (Live Messages)</div>
            <div id="queen-messages" style="max-height: 150px; overflow-y: auto; font-size: 12px;">
                <div style="color: #b5b9d1; padding: 8px;">Waiting for Queen...</div>
            </div>
        </div>
    </div>

    <!-- Intelligence Systems Status Grid -->
    <div class="live-panel" id="intel-systems-grid" style="grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); display: none;">
    </div>
    
    <div id="network-container"></div>
    
    <div class="sidebar" id="sidebar">
        <button class="close-sidebar" onclick="closeSidebar()">✕ Close</button>
        <div id="sidebar-content"></div>
    </div>
    
    <div class="legend">
        <h4>📊 Legend</h4>
        <div class="legend-item">
            <div class="legend-color" style="background: #FFD700;"></div>
            <span>⭐ Dashboard (clickable)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #00B894;"></div>
            <span>● ThoughtBus Integrated</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #6C5CE7;"></div>
            <span>● Queen Integrated</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #00B894; border-color: #00B894;"></div>
            <span>● Running (green border)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #FF6B6B; border-color: #FF6B6B;"></div>
            <span>● Stopped (red border)</span>
        </div>
        <div id="legend-categories"></div>
    </div>
    
    <div class="dashboard-links">
        <h4>🌐 Active Dashboards</h4>
        <div id="dashboard-links"></div>
    </div>
    
    <script>
        let network;
        let allData;
        let currentFilter = 'all';
        let queenChart;
        let profitChart;
        let activityChart;
        let exchangeChart;
        
        async function loadData() {
            const response = await fetch('/api/mindmap');
            allData = await response.json();
            
            // Update stats
            document.getElementById('total-systems').textContent = allData.nodes.length;
            document.getElementById('total-categories').textContent = allData.categories.length;
            document.getElementById('active-dashboards').textContent = 
                allData.nodes.filter(n => n.is_dashboard).length;
            document.getElementById('running-systems').textContent =
                allData.nodes.filter(n => n.is_running).length;
            
            // Create category filters
            const filtersDiv = document.getElementById('category-filters');
            allData.categories.forEach(cat => {
                const btn = document.createElement('button');
                btn.className = 'filter-btn';
                btn.textContent = `${cat.icon} ${cat.name} (${cat.count})`;
                btn.dataset.category = cat.name;
                btn.onclick = () => filterByCategory(cat.name);
                filtersDiv.appendChild(btn);
            });
            
            // Add to legend
            const legendDiv = document.getElementById('legend-categories');
            allData.categories.forEach(cat => {
                const item = document.createElement('div');
                item.className = 'legend-item';
                item.innerHTML = `
                    <div class="legend-color" style="background: ${cat.color};"></div>
                    <span>${cat.icon} ${cat.name}</span>
                `;
                legendDiv.appendChild(item);
            });
            
            renderNetwork(allData);
        }

        async function loadLive() {
            try {
                const response = await fetch('/api/live');
                const live = await response.json();

                const queenSignal = Number(live.queen_signal || 0);
                document.getElementById('live-queen-signal').textContent = queenSignal.toFixed(4);

                const lastTrade = live.revenue?.last_trade;
                if (lastTrade) {
                    const profit = Number(lastTrade.profit || 0).toFixed(4);
                    document.getElementById('live-last-trade').textContent = `${lastTrade.symbol || '—'} | ${profit}`;
                } else {
                    document.getElementById('live-last-trade').textContent = '—';
                }

                const revSum = Number(live.revenue?.recent_profit_sum || 0).toFixed(4);
                const revCount = live.revenue?.recent_trade_count || 0;
                document.getElementById('live-revenue').textContent = `${revSum} (${revCount} trades)`;

                const pos = live.active_position || {};
                if (pos.symbol) {
                    document.getElementById('live-open-position').textContent = `${pos.symbol} | qty ${pos.quantity ?? '—'} @ ${pos.entry_price ?? '—'}`;
                } else {
                    document.getElementById('live-open-position').textContent = '—';
                }

                const thought = (live.recent_thoughts || [])[0];
                if (thought) {
                    document.getElementById('live-last-thought').textContent = `${thought.topic} | ${thought.source}`;
                } else {
                    document.getElementById('live-last-thought').textContent = '—';
                }

                const runnerEl = document.getElementById('live-runner-status');
                if (runnerEl) {
                    const isOk = Boolean(live.live_runner_ok);
                    runnerEl.textContent = isOk ? 'ONLINE' : 'OFFLINE';
                    runnerEl.style.color = isOk ? '#00B894' : '#FF6B6B';
                }

                document.getElementById('live-autonomy').textContent = live.autonomy_available ? 'YES' : 'NO';
            } catch (e) {
                // ignore
            }
        }

        async function loadAnalytics() {
            try {
                const tsRes = await fetch('/api/timeseries');
                const tsData = await tsRes.json();

                const queenLabels = tsData.queen_signal.map(p => p.t || '');
                const queenValues = tsData.queen_signal.map(p => p.v || 0);
                if (!queenChart) {
                    const ctx = document.getElementById('queenSignalChart');
                    queenChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: queenLabels,
                            datasets: [{
                                label: 'Queen Signal',
                                data: queenValues,
                                borderColor: '#7c5cff',
                                backgroundColor: 'rgba(124, 92, 255, 0.2)',
                                tension: 0.35,
                                fill: true
                            }]
                        },
                        options: {
                            plugins: { legend: { display: false } },
                            scales: { x: { display: false }, y: { display: true } }
                        }
                    });
                } else {
                    queenChart.data.labels = queenLabels;
                    queenChart.data.datasets[0].data = queenValues;
                    queenChart.update();
                }

                const profitLabels = tsData.profit.map(p => p.t || '');
                const profitValues = tsData.profit.map(p => p.v || 0);
                if (!profitChart) {
                    const ctx = document.getElementById('profitChart');
                    profitChart = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: profitLabels,
                            datasets: [{
                                label: 'Profit',
                                data: profitValues,
                                backgroundColor: profitValues.map(v => v >= 0 ? 'rgba(46, 229, 157, 0.7)' : 'rgba(255, 107, 107, 0.7)')
                            }]
                        },
                        options: {
                            plugins: { legend: { display: false } },
                            scales: { x: { display: false }, y: { display: true } }
                        }
                    });
                } else {
                    profitChart.data.labels = profitLabels;
                    profitChart.data.datasets[0].data = profitValues;
                    profitChart.update();
                }

                const actRes = await fetch('/api/activity');
                const actData = await actRes.json();
                const topics = Object.keys(actData.topic_counts || {});
                const counts = topics.map(t => actData.topic_counts[t]);
                if (!activityChart) {
                    const ctx = document.getElementById('activityChart');
                    activityChart = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: topics,
                            datasets: [{
                                label: 'Thought Topics',
                                data: counts,
                                backgroundColor: 'rgba(43, 211, 255, 0.6)'
                            }]
                        },
                        options: {
                            plugins: { legend: { display: false } },
                            scales: { x: { display: true }, y: { display: true } }
                        }
                    });
                } else {
                    activityChart.data.labels = topics;
                    activityChart.data.datasets[0].data = counts;
                    activityChart.update();
                }
            } catch (e) {
                // ignore
            }
        }

        async function loadMaps() {
            try {
                const [heatRes, specRes, exRes] = await Promise.all([
                    fetch('/api/heatmap'),
                    fetch('/api/orderbook'),
                    fetch('/api/exchange-map')
                ]);
                const heatData = await heatRes.json();
                const specData = await specRes.json();
                const exData = await exRes.json();

                renderHeatmap(heatData);
                renderSpectrogram(specData);
                renderExchangeMap(exData);
            } catch (e) {
                // ignore
            }
        }

        async function loadScanners() {
            try {
                const res = await fetch('/api/scanners');
                const data = await res.json();
                renderFeedTable('marketFeed', data.market || []);
                renderFeedTable('whaleFeed', data.whales || []);
                renderFeedTable('botFeed', data.bots || []);
                renderFeedTable('waveFeed', data.waves || []);
            } catch (e) {
                // ignore
            }
        }

        async function loadDashboardLinks() {
            try {
                const res = await fetch('/api/dashboards');
                const data = await res.json();
                const container = document.getElementById('dashboard-links');
                if (!container) return;
                container.innerHTML = '';
                (data.dashboards || []).forEach(d => {
                    const label = `${d.label} (${d.port})`;
                    if (d.online) {
                        const a = document.createElement('a');
                        a.href = d.url;
                        a.target = '_blank';
                        a.className = 'dashboard-link';
                        a.textContent = label;
                        container.appendChild(a);
                    } else {
                        const div = document.createElement('div');
                        div.className = 'dashboard-link offline';
                        div.title = d.start_hint || 'Offline';
                        div.textContent = `${label} — OFFLINE`;
                        container.appendChild(div);
                    }
                });
            } catch (e) {
                // ignore
            }
        }

        function renderFeedTable(elementId, rows) {
            const table = document.getElementById(elementId);
            if (!table) return;
            const header = `
                <tr>
                    <th style="width:70px">Time</th>
                    <th style="width:120px">Signal</th>
                    <th>Details</th>
                </tr>`;
            const body = rows.map(r => {
                const ts = r.ts ? new Date(r.ts * 1000).toLocaleTimeString() : '—';
                const topic = r.topic || '—';
                const payload = r.payload || {};
                
                // Format based on feed type
                let signal = topic.split('.').slice(1).join('.') || topic;
                let details = '';
                let color = '#6C5CE7';
                
                if (topic.startsWith('market.')) {
                    const sym = payload.symbol || payload.top_momentum?.symbol || '—';
                    const change = payload.change_1h || payload.top_momentum?.change_1h || 0;
                    const opps = payload.opportunities_found || 0;
                    color = change > 0 ? '#00B894' : '#FF6B6B';
                    details = `<span style="color:${color}">${sym}</span> ${change > 0 ? '↑' : '↓'}${Math.abs(change).toFixed(2)}% | ${opps} opps`;
                } else if (topic.startsWith('whale.')) {
                    const sym = payload.symbol || '—';
                    const side = payload.side || 'buy';
                    const vol = (payload.volume_usd || 0) / 1000;
                    const firm = payload.firm || 'Unknown';
                    color = side === 'buy' ? '#00B894' : '#FF6B6B';
                    details = `<span style="color:${color}">${side.toUpperCase()}</span> ${sym} $${vol.toFixed(0)}K | ${firm}`;
                } else if (topic.startsWith('bot.')) {
                    const sym = payload.symbol || '—';
                    const cls = payload.bot_class || 'Unknown';
                    const conf = ((payload.confidence || 0) * 100).toFixed(0);
                    const layer = ((payload.layering_score || 0) * 100).toFixed(0);
                    details = `${sym} | ${cls} (${conf}% conf) | Layer: ${layer}%`;
                } else if (topic.startsWith('wave.')) {
                    const sym = payload.symbol || '—';
                    const state = payload.state || 'BALANCED';
                    const mom = ((payload.momentum_score || 0) * 100).toFixed(0);
                    color = state.includes('RISING') || state.includes('BREAKOUT') ? '#00B894' : '#FF6B6B';
                    details = `${sym} <span style="color:${color}">${state}</span> | Mom: ${mom}%`;
                } else if (topic.startsWith('scanner.')) {
                    const sym = payload.symbol || '—';
                    const type = payload.type || payload.pattern || 'opportunity';
                    const conf = ((payload.confidence || payload.score || 0) * 100).toFixed(0);
                    const pip = payload.pip_score || payload.expected_pips || 0;
                    color = conf > 70 ? '#00B894' : conf > 40 ? '#FFA500' : '#FF6B6B';
                    details = `<strong>${sym}</strong> | ${type.replace('_', ' ')} | <span style="color:${color}">${conf}% conf</span> | ${pip.toFixed(2)} pips`;
                } else if (topic.startsWith('queen.')) {
                    const decision = payload.decision || payload.signal || 'HOLD';
                    const conf = ((payload.confidence || payload.score || 0) * 100).toFixed(0);
                    const sym = payload.symbol || payload.asset || '—';
                    color = decision === 'BUY' ? '#00B894' : decision === 'SELL' ? '#FF6B6B' : '#FFA500';
                    details = `👑 <span style="color:${color}"><strong>${decision}</strong></span> ${sym} (${conf}% confidence)`;
                } else {
                    // Improved fallback: Try to parse message wrappers and format key-value pairs
                    let data = payload;
                    
                    // Handle message wrapper from ThoughtBus
                    if (payload.message && typeof payload.message === 'string') {
                        if (payload.message.startsWith('{')) {
                            try { data = JSON.parse(payload.message); } catch(e) {}
                        } else {
                            // Simple message string
                            details = `<span style="font-style:italic">${payload.message}</span>`;
                        }
                    }
                    
                    // If still an object, format as human-readable key-value pairs
                    if (typeof data === 'object' && data !== null && !details) {
                        const keys = Object.keys(data).filter(k => !['timestamp', 'interval', 'id', 'trace_id'].includes(k));
                        if (keys.length > 0) {
                            details = keys.slice(0, 3).map(k => {
                                let val = data[k];
                                if (typeof val === 'number') {
                                    val = val % 1 !== 0 ? val.toFixed(2) : val.toLocaleString();
                                } else if (typeof val === 'boolean') {
                                    val = val ? 'Yes' : 'No';
                                } else if (typeof val === 'string' && val.length > 20) {
                                    val = val.substring(0, 17) + '...';
                                }
                                return `<span style="opacity:0.7">${k.replace('_', ' ')}:</span> ${val}`;
                            }).join(' | ');
                        } else {
                            details = 'System update';
                        }
                    }
                    
                    // Final fallback
                    if (!details) {
                        details = JSON.stringify(payload).substring(0, 60) + (JSON.stringify(payload).length > 60 ? '...' : '');
                    }
                }
                
                return `<tr><td>${ts}</td><td style="color:#74B9FF">${signal}</td><td>${details}</td></tr>`;
            }).join('');
            table.innerHTML = header + body;
        }

        function renderHeatmap(data) {
            const canvas = document.getElementById('heatmapCanvas');
            if (!canvas || !data || !data.rows || !data.cols) return;

            const ctx = canvas.getContext('2d');
            const w = canvas.width = canvas.clientWidth;
            const h = canvas.height = canvas.clientHeight;

            const cellW = w / data.cols;
            const cellH = h / data.rows;

            const maxVal = Math.max(1, ...data.values.flat());
            ctx.clearRect(0, 0, w, h);

            for (let r = 0; r < data.rows; r++) {
                for (let c = 0; c < data.cols; c++) {
                    const v = data.values[r][c];
                    const intensity = v / maxVal;
                    ctx.fillStyle = `rgba(124, 92, 255, ${0.15 + intensity * 0.8})`;
                    ctx.fillRect(c * cellW, r * cellH, cellW - 1, cellH - 1);
                }
            }

            const tooltip = document.getElementById('heatmapTooltip');
            canvas.onmousemove = (e) => {
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                const c = Math.floor(x / cellW);
                const r = Math.floor(y / cellH);
                if (r >= 0 && r < data.rows && c >= 0 && c < data.cols) {
                    const label = data.row_labels[r] || 'topic';
                    const val = data.values[r][c];
                    tooltip.style.display = 'block';
                    tooltip.style.left = `${e.clientX + 10}px`;
                    tooltip.style.top = `${e.clientY + 10}px`;
                    tooltip.textContent = `${label}: ${val}`;
                }
            };
            canvas.onmouseleave = () => { tooltip.style.display = 'none'; };
        }

        function renderSpectrogram(data) {
            const canvas = document.getElementById('spectrogramCanvas');
            if (!canvas || !data || !data.series) return;

            const ctx = canvas.getContext('2d');
            const w = canvas.width = canvas.clientWidth;
            const h = canvas.height = canvas.clientHeight;

            ctx.clearRect(0, 0, w, h);
            const series = data.series;
            if (!series.length) return;

            const maxDepth = Math.max(1, ...series.map(s => Math.max(s.bids || 0, s.asks || 0)));
            const barW = Math.max(2, Math.floor(w / series.length));

            series.forEach((s, i) => {
                const x = i * barW;
                const bidIntensity = (s.bids || 0) / maxDepth;
                const askIntensity = (s.asks || 0) / maxDepth;

                ctx.fillStyle = `rgba(46, 229, 157, ${0.2 + bidIntensity * 0.8})`;
                ctx.fillRect(x, 0, barW - 1, h / 2);
                ctx.fillStyle = `rgba(255, 107, 107, ${0.2 + askIntensity * 0.8})`;
                ctx.fillRect(x, h / 2, barW - 1, h / 2);
            });

            const tooltip = document.getElementById('spectrogramTooltip');
            canvas.onmousemove = (e) => {
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const idx = Math.min(series.length - 1, Math.max(0, Math.floor(x / barW)));
                const s = series[idx];
                if (s) {
                    tooltip.style.display = 'block';
                    tooltip.style.left = `${e.clientX + 10}px`;
                    tooltip.style.top = `${e.clientY + 10}px`;
                    tooltip.textContent = `bids: ${Math.round(s.bids || 0)} | asks: ${Math.round(s.asks || 0)}`;
                }
            };
            canvas.onmouseleave = () => { tooltip.style.display = 'none'; };
        }

        function renderExchangeMap(data) {
            const ctx = document.getElementById('exchangeMapChart');
            if (!ctx || !data || !data.exchanges) return;

            const labels = data.exchanges.map(e => e.exchange);
            const counts = data.exchanges.map(e => e.count);
            const profits = data.exchanges.map(e => e.profit);

            if (!exchangeChart) {
                exchangeChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels,
                        datasets: [
                            {
                                label: 'Trade Count',
                                data: counts,
                                backgroundColor: 'rgba(43, 211, 255, 0.6)'
                            },
                            {
                                label: 'Profit',
                                data: profits,
                                backgroundColor: 'rgba(124, 92, 255, 0.6)'
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        plugins: { legend: { display: true } },
                        scales: { x: { display: true }, y: { display: true } }
                    }
                });
            } else {
                exchangeChart.data.labels = labels;
                exchangeChart.data.datasets[0].data = counts;
                exchangeChart.data.datasets[1].data = profits;
                exchangeChart.update();
            }
        }
        
        function renderNetwork(data) {
            const container = document.getElementById('network-container');
            if (!container) return;
            if (typeof vis === 'undefined' || !vis.Network) {
                container.innerHTML = '<div style="padding:16px;color:#b5b9d1">Network graph unavailable (offline assets). Live data panels are still active.</div>';
                return;
            }
            
            const options = {
                nodes: {
                    font: {
                        color: '#ffffff',
                        size: 14
                    },
                    borderWidth: 2,
                    borderWidthSelected: 4,
                    shadow: {
                        enabled: true,
                        color: 'rgba(0,0,0,0.5)',
                        size: 10,
                        x: 0,
                        y: 0
                    }
                },
                edges: {
                    color: {
                        color: 'rgba(255,255,255,0.2)',
                        highlight: '#6C5CE7',
                        hover: '#6C5CE7'
                    },
                    smooth: {
                        type: 'continuous'
                    }
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
                    stabilization: {
                        iterations: 200
                    }
                },
                interaction: {
                    hover: true,
                    tooltipDelay: 200,
                    navigationButtons: true,
                    keyboard: true
                }
            };
            
            network = new vis.Network(container, data, options);
            
            // Event handlers
            network.on('click', function(params) {
                if (params.nodes.length > 0) {
                    const nodeId = params.nodes[0];
                    const node = data.nodes.find(n => n.id === nodeId);
                    showNodeDetails(node);
                    
                    // If dashboard, open in new tab
                    if (node.is_dashboard && node.dashboard_port) {
                        const url = `http://localhost:${node.dashboard_port}`;
                        window.open(url, '_blank');
                    }
                }
            });
            
            network.on('doubleClick', function(params) {
                if (params.nodes.length > 0) {
                    network.focus(params.nodes[0], {
                        scale: 1.5,
                        animation: true
                    });
                }
            });
        }
        
        function filterByCategory(category) {
            currentFilter = category;
            
            // Update button states
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
                if (btn.dataset.category === category) {
                    btn.classList.add('active');
                }
            });
            
            if (category === 'all') {
                renderNetwork(allData);
            } else {
                const filtered = {
                    nodes: allData.nodes.filter(n => n.group === category),
                    edges: allData.edges.filter(e => {
                        const fromNode = allData.nodes.find(n => n.id === e.from);
                        const toNode = allData.nodes.find(n => n.id === e.to);
                        return fromNode && toNode && 
                               fromNode.group === category && 
                               toNode.group === category;
                    }),
                    categories: allData.categories
                };
                renderNetwork(filtered);
            }
        }
        
        function showNodeDetails(node) {
            const sidebar = document.getElementById('sidebar');
            const content = document.getElementById('sidebar-content');
            
            let badges = '';
            badges += node.is_running ? '<span class="badge green">Running</span>' : '<span class="badge red">Stopped</span>';
            if (node.has_thought_bus) badges += '<span class="badge green">ThoughtBus</span>';
            if (node.has_queen) badges += '<span class="badge green">Queen</span>';
            if (node.is_dashboard) badges += '<span class="badge">Dashboard</span>';
            
            content.innerHTML = `
                <h3>${node.label}</h3>
                <div class="detail-row">
                    <div class="label">Category</div>
                    <div class="value">${node.group}</div>
                </div>
                <div class="detail-row">
                    <div class="label">Description</div>
                    <div class="value">${node.title || 'No description'}</div>
                </div>
                <div class="detail-row">
                    <div class="label">Lines of Code</div>
                    <div class="value">${node.loc.toLocaleString()}</div>
                </div>
                ${node.is_dashboard ? `
                <div class="detail-row">
                    <div class="label">Dashboard Port</div>
                    <div class="value">
                        <a href="http://localhost:${node.dashboard_port}" target="_blank" 
                           style="color: #6C5CE7;">http://localhost:${node.dashboard_port}</a>
                    </div>
                </div>
                ` : ''}
                <div class="detail-row">
                    <div class="label">Integration</div>
                    <div class="value">${badges || '<span class="badge red">None</span>'}</div>
                </div>
            `;
            
            sidebar.classList.add('open');
        }
        
        function closeSidebar() {
            document.getElementById('sidebar').classList.remove('open');
        }
        
        function resetView() {
            network.fit({
                animation: {
                    duration: 1000,
                    easingFunction: 'easeInOutQuad'
                }
            });
        }
        
        // Search functionality
        document.getElementById('search').addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            
            if (!searchTerm) {
                filterByCategory(currentFilter);
                return;
            }
            
            const filtered = {
                nodes: allData.nodes.filter(n => 
                    n.label.toLowerCase().includes(searchTerm) ||
                    n.title.toLowerCase().includes(searchTerm) ||
                    n.group.toLowerCase().includes(searchTerm)
                ),
                edges: [],
                categories: allData.categories
            };
            
            // Include edges for filtered nodes
            const nodeIds = new Set(filtered.nodes.map(n => n.id));
            filtered.edges = allData.edges.filter(e => 
                nodeIds.has(e.from) && nodeIds.has(e.to)
            );
            
            renderNetwork(filtered);
        });
        
        // Load data on page load
        loadData();
        loadLive();
        setInterval(loadLive, 5000);
        loadAnalytics();
        setInterval(loadAnalytics, 7000);
        loadMaps();
        setInterval(loadMaps, 8000);
        loadScanners();
        setInterval(loadScanners, 5000);
        loadIntelligence();
        setInterval(loadIntelligence, 10000);
        loadQueenState();
        setInterval(loadQueenState, 3000);
        loadDashboardLinks();
        setInterval(loadDashboardLinks, 10000);

        async function loadIntelligence() {
            try {
                const res = await fetch('/api/intelligence');
                const data = await res.json();
                
                document.getElementById('intel-online').textContent = 
                    `${data.systems_online} / ${data.systems_total}`;
                
                // Render intelligence systems grid
                const grid = document.getElementById('intel-systems-grid');
                grid.style.display = 'grid';
                grid.innerHTML = '';
                
                for (const [name, status] of Object.entries(data.systems_status)) {
                    const card = document.createElement('div');
                    card.className = 'live-card';
                    card.style.borderColor = status ? 'rgba(46, 229, 157, 0.5)' : 'rgba(255, 107, 107, 0.3)';
                    card.innerHTML = `
                        <div class="title">${status ? '✅' : '❌'} ${name}</div>
                        <div class="value" style="font-size: 11px; color: ${status ? '#2ee59d' : '#ff6b6b'};">
                            ${status ? 'ONLINE' : 'OFFLINE'}
                        </div>
                    `;
                    grid.appendChild(card);
                }
            } catch (e) {
                console.error('Intelligence load error:', e);
            }
        }

        async function loadQueenState() {
            try {
                const res = await fetch('/api/queen-state');
                const data = await res.json();
                
                // Update whale alerts count
                document.getElementById('whale-alerts').textContent = data.whale_alerts || 0;
                
                // Update fear/greed
                const fg = data.fear_greed_index || 50;
                const fgLabel = data.fear_greed_label || 'Neutral';
                document.getElementById('fear-greed').textContent = `${fg} (${fgLabel})`;
                document.getElementById('fear-greed').style.color = 
                    fg < 30 ? '#ff6b6b' : fg > 70 ? '#2ee59d' : '#ffa500';
                
                // Update quantum coherence
                const qc = ((data.quantum_coherence || 0) * 100).toFixed(1);
                document.getElementById('quantum-coherence').textContent = `${qc}%`;
                
                // Update queen messages
                const msgContainer = document.getElementById('queen-messages');
                const messages = data.queen_messages || [];
                if (messages.length > 0) {
                    msgContainer.innerHTML = messages.slice(-10).reverse().map(m => {
                        const ts = new Date(m.ts * 1000).toLocaleTimeString();
                        const levelColor = m.level === 'success' ? '#2ee59d' : 
                                           m.level === 'warning' ? '#ffa500' :
                                           m.level === 'error' ? '#ff6b6b' : '#b5b9d1';
                        return `<div style="padding: 4px 8px; border-left: 2px solid ${levelColor}; margin: 4px 0;">
                            <span style="color: #666; font-size: 10px;">${ts}</span>
                            <span style="color: ${levelColor};">${m.message}</span>
                        </div>`;
                    }).join('');
                }
                
                // Load bot events count
                const botRes = await fetch('/api/bots');
                const botData = await botRes.json();
                document.getElementById('bot-events').textContent = botData.total_bot_events || 0;
                
                // Load wave signals count
                const waveRes = await fetch('/api/waves');
                const waveData = await waveRes.json();
                document.getElementById('wave-signals').textContent = waveData.total_wave_events || 0;
                
            } catch (e) {
                console.error('Queen state load error:', e);
            }
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Serve the main dashboard."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/mindmap')
def get_mindmap_data():
    """API endpoint to get mind map data."""
    return jsonify(registry.export_mind_map_data())


@app.route('/api/stats')
def get_stats():
    """API endpoint to get system statistics."""
    return jsonify(registry.get_category_stats())


@app.route('/api/system/<system_name>')
def get_system_info(system_name):
    """API endpoint to get detailed info about a system."""
    if system_name in registry.systems:
        system = registry.systems[system_name]
        return jsonify({
            "name": system.name,
            "filepath": system.filepath,
            "category": system.category,
            "description": system.description,
            "loc": system.lines_of_code,
            "is_dashboard": system.is_dashboard,
            "dashboard_port": system.dashboard_port,
            "has_thought_bus": system.has_thought_bus,
            "has_queen_integration": system.has_queen_integration,
            "sacred_frequencies": system.sacred_frequencies,
            "imports": system.imports
        })
    return jsonify({"error": "System not found"}), 404


@app.route('/api/live')
def get_live():
    """API endpoint for live operational telemetry."""
    events = _read_last_jsonl(ELEPHANT_HISTORY_FILE, limit=200)
    revenue = _extract_revenue(events)
    queen_signal = _latest_queen_signal(events)

    active_position = _safe_load_json(ACTIVE_POSITION_FILE)

    # Read thoughts directly from file (cross-process)
    recent_thoughts = _read_recent_thoughts(limit=50)

    return jsonify({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "queen_signal": queen_signal,
        "revenue": revenue,
        "active_position": active_position,
        "recent_thoughts": recent_thoughts[:10],
        "metrics": dump_metrics(),
        "autonomy_available": _autonomy_available(),
        "live_runner_ok": _is_process_running("aureon_queen_live_runner.py"),
    })


@app.route('/api/timeseries')
def get_timeseries():
    """API endpoint for chart-ready time series."""
    events = _read_last_jsonl(ELEPHANT_HISTORY_FILE, limit=300)
    return jsonify(_build_timeseries(events))


@app.route('/api/activity')
def get_activity():
    """API endpoint for spectrograph-style activity maps."""
    events = _read_last_jsonl(ELEPHANT_HISTORY_FILE, limit=300)
    # Read thoughts directly from file (cross-process)
    thoughts = _read_recent_thoughts(limit=200)
    return jsonify(_build_activity_maps(thoughts, events))


@app.route('/api/heatmap')
def get_heatmap():
    """API endpoint for interactive thought density heatmap."""
    # Read thoughts directly from file (cross-process)
    thoughts = _read_recent_thoughts(limit=400)
    return jsonify(_build_heatmap(thoughts))


@app.route('/api/orderbook')
def get_orderbook():
    """API endpoint for orderbook depth spectrogram."""
    # Read thoughts directly from file (cross-process)
    thoughts = _read_recent_thoughts(limit=400)
    return jsonify(_build_orderbook_spectrogram(thoughts))


@app.route('/api/exchange-map')
def get_exchange_map():
    """API endpoint for exchange-level trade map."""
    events = _read_last_jsonl(ELEPHANT_HISTORY_FILE, limit=500)
    return jsonify(_build_exchange_map(events))


@app.route('/api/scanners')
def get_scanners():
    """API endpoint for real-time scanner feeds.
    
    Reads from both in-memory ThoughtBus AND the persisted thoughts.jsonl file
    to capture telemetry from external processes.
    """
    all_thoughts = []
    
    # 1. Read from in-memory ThoughtBus
    try:
        bus = get_thought_bus()
        in_memory = bus.get_recent(500)
        all_thoughts.extend(in_memory)
    except Exception:
        pass
    
    # 2. Read from persisted thoughts.jsonl file (captures external process telemetry)
    thoughts_file = THOUGHTS_FILE
    if thoughts_file.exists():
        try:
            # Read last 500 lines efficiently
            lines = []
            with open(thoughts_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-500:]
            
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        t = json.loads(line)
                        all_thoughts.append(t)
                    except:
                        pass
        except Exception:
            pass
    
    # Deduplicate by thought ID and sort by timestamp
    seen_ids = set()
    unique_thoughts = []
    for t in all_thoughts:
        tid = t.get("id", t.get("trace_id", str(t)))
        if tid not in seen_ids:
            seen_ids.add(tid)
            unique_thoughts.append(t)
    
    # Sort by timestamp (most recent first)
    try:
        unique_thoughts.sort(key=lambda x: x.get("ts", 0), reverse=True)
    except:
        pass
    
    return jsonify(_build_scanner_feed(unique_thoughts[:500]))


@app.route('/api/intelligence')
def get_intelligence():
    """API endpoint for consolidated intelligence system status."""
    return jsonify({
        "systems_status": SYSTEMS_STATUS,
        "systems_online": sum(SYSTEMS_STATUS.values()),
        "systems_total": len(SYSTEMS_STATUS),
        "sacred_constants": {
            "PHI": PHI,
            "SCHUMANN": SCHUMANN,
            "LOVE_FREQ": LOVE_FREQ
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


def _build_unified_layer_readiness():
    """Build readiness report for the 4D margin coordination model."""
    module_online = set(name for name, ready in SYSTEMS_STATUS.items() if ready)
    layers = []

    for layer in UNIFIED_MARGIN_LAYERS:
        guardians = layer["module_guardians"]
        online = [name for name in guardians if name in module_online]
        readiness = len(online) / max(len(guardians), 1)

        layers.append({
            "id": layer["id"],
            "label": layer["label"],
            "overseers": layer["overseers"],
            "module_guardians": guardians,
            "online_guardians": online,
            "offline_guardians": [name for name in guardians if name not in online],
            "readiness_score": round(readiness, 3),
            "thought_topics": layer["thought_topics"],
        })

    return layers


def _build_unified_telemetry(thoughts):
    """Aggregate telemetry counters for probability matrix inputs."""
    thoughts = thoughts or []

    topic_counts = defaultdict(int)
    for thought in thoughts:
        topic = str(thought.get("topic", "unknown"))
        topic_counts[topic] += 1

    websocket_status = []
    thought_bus_ready = bool(thoughts)
    for ws in UNIFIED_MARGIN_WEBSOCKETS:
        if ws["name"] == "thought_bus":
            active = thought_bus_ready
        else:
            prefix = ws["name"].replace("_", ".")
            active = any(k.startswith(prefix) for k in topic_counts.keys())
        websocket_status.append({
            "name": ws["name"],
            "status_key": ws["status_key"],
            "required": ws["required"],
            "active": active,
        })

    wave_events = sum(
        count for topic, count in topic_counts.items()
        if topic.startswith(UNIFIED_WAVEFORM_KEEPALIVE_TOPICS)
    )
    keep_stream_active = wave_events > 0

    return {
        "total_events": len(thoughts),
        "topic_counts": dict(sorted(topic_counts.items(), key=lambda item: item[1], reverse=True)[:20]),
        "websocket_status": websocket_status,
        "wave_event_count": wave_events,
        "keep_stream_active": keep_stream_active,
        "telemetry_ready": all(item["active"] or not item["required"] for item in websocket_status),
    }


def _assess_unified_waveform(telemetry: dict, revenue: dict) -> dict:
    """Ocean-scanner biased waveform gate that avoids over-rejecting active streams."""
    total_events = max(int(telemetry.get("total_events", 0)), 1)
    wave_event_count = int(telemetry.get("wave_event_count", 0))
    wave_ratio = wave_event_count / total_events
    keep_stream_active = bool(telemetry.get("keep_stream_active", False))

    recent_profit = float(revenue.get("recent_profit_sum", 0.0))
    profitable = recent_profit > 0
    auto_activate = profitable and (wave_ratio >= UNIFIED_WAVEFORM_REJECTION_THRESHOLD or keep_stream_active)

    return {
        "accepted": wave_ratio >= UNIFIED_WAVEFORM_REJECTION_THRESHOLD or keep_stream_active,
        "wave_ratio": round(wave_ratio, 4),
        "rejection_threshold": UNIFIED_WAVEFORM_REJECTION_THRESHOLD,
        "keep_stream_active": keep_stream_active,
        "ocean_scanner_logic_active": True,
        "profit_detected": profitable,
        "auto_activate_on_profit": auto_activate,
    }


def _build_bot_profiling_metrics(thoughts: list, events: list) -> dict:
    """Operational status for bot profiling + live metrics used by probability matrices."""
    thoughts = thoughts or []
    events = events or []

    bot_topics = ("bot.", "firm.", "counter.")
    bot_events = [t for t in thoughts if str(t.get("topic", "")).startswith(bot_topics)]
    scanner_opps = [
        t for t in thoughts
        if "opportunity" in str(t.get("topic", "")) or str(t.get("topic", "")).startswith("scanner.")
    ]

    ticker_counts = defaultdict(int)
    for e in events:
        if e.get("type") != "result":
            continue
        symbol = str(e.get("symbol") or e.get("ticker") or "").strip().upper()
        if symbol:
            ticker_counts[symbol] += 1

    live_tickers = [
        {"symbol": symbol, "samples": count}
        for symbol, count in sorted(ticker_counts.items(), key=lambda kv: kv[1], reverse=True)[:20]
    ]

    signatures = len(TRADING_FIRM_SIGNATURES) if isinstance(TRADING_FIRM_SIGNATURES, dict) else 0
    profiler_online = bool(SYSTEMS_STATUS.get("Bot Intelligence", False))
    stream_health = "active" if bot_events or scanner_opps else "idle"

    return {
        "profiler_online": profiler_online,
        "signatures_loaded": signatures,
        "bot_events_recent": len(bot_events),
        "scanner_opportunities_recent": len(scanner_opps),
        "stream_health": stream_health,
        "live_tickers": live_tickers,
        "real_time_mapping_ready": profiler_online and len(live_tickers) > 0,
    }


def _build_probability_matrix_payload(thoughts: list, events: list, revenue: dict, waveform: dict) -> dict:
    """Build raw metrics payload for probability-matrix ingestion."""
    profiling = _build_bot_profiling_metrics(thoughts, events)
    profitable = bool(waveform.get("profit_detected", False))
    active_waveform = bool(waveform.get("accepted", False))

    return {
        "raw_metrics": {
            "recent_profit_sum": float(revenue.get("recent_profit_sum", 0.0)),
            "recent_trade_count": int(revenue.get("recent_trade_count", 0)),
            "bot_events_recent": profiling["bot_events_recent"],
            "scanner_opportunities_recent": profiling["scanner_opportunities_recent"],
            "live_tickers_observed": len(profiling["live_tickers"]),
            "wave_ratio": float(waveform.get("wave_ratio", 0.0)),
        },
        "validation": {
            "profiler_online": profiling["profiler_online"],
            "real_time_mapping_ready": profiling["real_time_mapping_ready"],
            "live_ticker_validation": len(profiling["live_tickers"]) > 0,
            "waveform_validation": active_waveform,
        },
        "capital_run_gate": {
            "ready_for_existing_run": (
                profiling["profiler_online"]
                and profiling["real_time_mapping_ready"]
                and active_waveform
                and profitable
            ),
            "reason": "ready" if (
                profiling["profiler_online"]
                and profiling["real_time_mapping_ready"]
                and active_waveform
                and profitable
            ) else "awaiting_profiler_tickers_waveform_or_profit",
        },
        "profiling": profiling,
        "bot_shadow_tracking": _build_bot_shadow_tracking(thoughts, events),
    }


def _build_bot_shadow_tracking(thoughts: list, events: list) -> dict:
    """
    Follow detected bot direction, compare with live movement, and emit
    prediction payload for probability matrices.
    """
    thoughts = thoughts or []
    events = events or []

    bot_signals = {}
    for t in thoughts:
        topic = str(t.get("topic", ""))
        payload = t.get("payload", {}) or {}
        if not (
            topic.startswith("bot.")
            or topic.startswith("firm.")
            or topic.startswith("counter.")
            or topic.startswith("scanner.")
        ):
            continue

        symbol = str(payload.get("symbol") or payload.get("ticker") or "").strip().upper()
        if not symbol:
            continue

        direction = str(payload.get("direction", payload.get("side", "HOLD"))).upper()
        confidence = float(payload.get("confidence", payload.get("probability", 0.0)) or 0.0)
        ts = float(t.get("ts", 0) or 0)

        existing = bot_signals.get(symbol)
        if existing is None or ts >= existing["ts"]:
            bot_signals[symbol] = {
                "symbol": symbol,
                "direction": direction,
                "confidence": confidence,
                "ts": ts,
            }

    movement = defaultdict(list)
    for e in events:
        if e.get("type") != "result":
            continue
        symbol = str(e.get("symbol") or e.get("ticker") or "").strip().upper()
        if not symbol:
            continue
        try:
            profit = float(e.get("profit", 0.0))
        except Exception:
            profit = 0.0
        movement[symbol].append(profit)

    tracked = []
    aligned = 0
    for symbol, signal in bot_signals.items():
        profits = movement.get(symbol, [])
        live_drift = sum(profits[-5:]) if profits else 0.0
        if signal["direction"] == "BUY" or signal["direction"] == "LONG":
            predicted_move = "UP"
            is_aligned = live_drift >= 0
        elif signal["direction"] == "SELL" or signal["direction"] == "SHORT":
            predicted_move = "DOWN"
            is_aligned = live_drift <= 0
        else:
            predicted_move = "NEUTRAL"
            is_aligned = abs(live_drift) < 1e-9

        if is_aligned:
            aligned += 1

        tracked.append({
            "symbol": symbol,
            "bot_direction": signal["direction"],
            "predicted_move": predicted_move,
            "confidence": round(signal["confidence"], 4),
            "live_drift_proxy": round(live_drift, 6),
            "alignment": is_aligned,
        })

    total = len(tracked)
    alignment_ratio = (aligned / total) if total else 0.0

    return {
        "tracked_symbols": tracked[:30],
        "tracked_count": total,
        "alignment_ratio": round(alignment_ratio, 4),
        "prediction_feed_ready": total > 0,
    }


def _build_unified_margin_wiring_status(thoughts: list, events: list, probability_matrix: dict) -> dict:
    """Explicit wiring report for unified margin trader run-path integration."""
    thoughts = thoughts or []
    events = events or []

    def _has_topic(prefixes):
        return any(str(t.get("topic", "")).startswith(prefixes) for t in thoughts)

    required_wires = {
        "thought_bus": _has_topic(("thought.", "system.", "market.", "queen.")),
        "wave_scanner": _has_topic(("wave.", "ocean.", "momentum.", "scanner.wave")),
        "bot_profiler": bool(SYSTEMS_STATUS.get("Bot Intelligence", False)),
        "probability_nexus": bool(SYSTEMS_STATUS.get("Probability Nexus", False)),
        "queen_hive": bool(SYSTEMS_STATUS.get("Queen Hive Mind", False)),
        "mycelium_network": bool(SYSTEMS_STATUS.get("Mycelium Network", False)),
        "live_ticker_feed": any(e.get("type") == "result" and (e.get("symbol") or e.get("ticker")) for e in events),
    }

    connected = [k for k, v in required_wires.items() if v]
    missing = [k for k, v in required_wires.items() if not v]
    ready_for_existing_run = bool(probability_matrix.get("capital_run_gate", {}).get("ready_for_existing_run", False))

    return {
        "required_wires": required_wires,
        "connected_wires": connected,
        "missing_wires": missing,
        "wiring_score": round(len(connected) / max(len(required_wires), 1), 4),
        "unified_margin_trader_wired": len(missing) == 0,
        "ready_for_existing_run": ready_for_existing_run,
    }


@app.route('/api/unified-margin/layers')
def get_unified_margin_layers():
    """Return the canonical 4D layer map used by unified margin coordination."""
    layers = _build_unified_layer_readiness()
    return jsonify({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "layer_count": len(layers),
        "layers": layers,
    })


@app.route('/api/unified-margin/telemetry')
def get_unified_margin_telemetry():
    """Expose telemetry required for probability matrices and shadow trading."""
    events = _read_last_jsonl(ELEPHANT_HISTORY_FILE, limit=400)
    revenue = _extract_revenue(events)
    thoughts = _read_recent_thoughts(limit=400)
    telemetry = _build_unified_telemetry(thoughts)
    waveform = _assess_unified_waveform(telemetry, revenue)
    probability_matrix = _build_probability_matrix_payload(thoughts, events, revenue, waveform)
    wiring = _build_unified_margin_wiring_status(thoughts, events, probability_matrix)
    return jsonify({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "layers": _build_unified_layer_readiness(),
        "telemetry": telemetry,
        "revenue": revenue,
        "unified_waveform": waveform,
        "probability_matrix": probability_matrix,
        "unified_margin_wiring": wiring,
    })


@app.route('/api/registry')
def get_registry():
    """API endpoint for the unified intelligence registry."""
    try:
        from aureon.intelligence.aureon_unified_intelligence_registry import get_unified_puller
        puller = get_unified_puller()
        return jsonify(puller.get_category_summary())
    except ImportError:
        return jsonify({"error": "Registry not available"}), 500


@app.route('/api/registry/chain-flow')
def get_chain_flow():
    """API endpoint for the chain-link data flow diagram."""
    try:
        from aureon.intelligence.aureon_unified_intelligence_registry import get_unified_puller
        puller = get_unified_puller()
        return jsonify(puller.get_chain_flow())
    except ImportError:
        return jsonify({"error": "Registry not available"}), 500


@app.route('/api/registry/category/<category_name>')
def get_registry_category(category_name):
    """API endpoint for pulling data from a specific category."""
    try:
        from aureon.intelligence.aureon_unified_intelligence_registry import get_unified_puller
        puller = get_unified_puller()
        return jsonify(puller.pull_category(category_name))
    except ImportError:
        return jsonify({"error": "Registry not available"}), 500


@app.route('/api/thoughts')
def get_thoughts():
    """API endpoint for streaming thoughts from ThoughtBus file."""
    limit = request.args.get('limit', 100, type=int)
    topic_filter = request.args.get('topic', None)
    
    thoughts = _read_recent_thoughts(limit=min(limit, 500))
    
    # Filter by topic if specified
    if topic_filter:
        thoughts = [t for t in thoughts if topic_filter in t.get('topic', '')]
    
    # Count by topic for summary
    topic_counts = {}
    for t in thoughts:
        topic = t.get('topic', 'unknown')
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    return jsonify({
        "count": len(thoughts),
        "thoughts": thoughts,
        "topic_summary": topic_counts,
        "file_path": str(THOUGHTS_FILE),
        "file_exists": THOUGHTS_FILE.exists(),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@app.route('/api/registry/unified')
def get_registry_unified():
    """API endpoint for unified data pull across all categories."""
    try:
        from aureon.intelligence.aureon_unified_intelligence_registry import get_unified_puller
        puller = get_unified_puller()
        return jsonify(puller.pull_unified())
    except ImportError:
        return jsonify({"error": "Registry not available"}), 500


@app.route('/api/dashboards')
def get_dashboards():
    """API endpoint for dashboard availability."""
    return jsonify({
        "dashboards": _dashboard_statuses(),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@app.route('/api/queen-state')
def get_queen_state():
    """API endpoint for Queen dashboard state (from queen_web_dashboard)."""
    return jsonify({
        "total_bots": dashboard_state.total_bots,
        "sharks": dashboard_state.sharks,
        "whales": dashboard_state.whales,
        "total_volume": dashboard_state.total_volume,
        "fear_greed_index": dashboard_state.fear_greed_index,
        "fear_greed_label": dashboard_state.fear_greed_label,
        "whale_alerts": dashboard_state.whale_alerts,
        "neural_connections": dashboard_state.neural_connections,
        "signals_decoded": dashboard_state.signals_decoded,
        "patterns_remembered": dashboard_state.patterns_remembered,
        "timeline_predictions": dashboard_state.timeline_predictions,
        "quantum_coherence": dashboard_state.quantum_coherence,
        "uptime_seconds": time.time() - dashboard_state.start_time,
        "queen_messages": list(dashboard_state.queen_messages)[-10:],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@app.route('/api/bots')
def get_bots():
    """API endpoint for detected bot activity (from bot_hunter_dashboard)."""
    # Read bot activity from thoughts
    all_thoughts = []
    thoughts_file = THOUGHTS_FILE
    if thoughts_file.exists():
        try:
            with open(thoughts_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-1000:]
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        t = json.loads(line)
                        topic = t.get("topic", "")
                        if "bot" in topic or "firm" in topic or "counter" in topic:
                            all_thoughts.append(t)
                    except:
                        pass
        except:
            pass
    
    # Build bot summary
    bots_detected = []
    firm_counts = defaultdict(int)
    
    for t in all_thoughts[-100:]:
        payload = t.get("payload", {}) or {}
        
        # Handle nested message strings (thought_bus_think wraps data)
        if isinstance(payload.get("message"), str):
            try:
                payload = json.loads(payload["message"])
            except:
                continue
        
        if "firm" in str(t.get("topic", "")).lower():
            firm_name = payload.get("firm_name") or payload.get("firm") or "unknown"
            firm_counts[firm_name] += 1
        
        if "bot" in str(t.get("topic", "")).lower():
            symbol = payload.get("symbol")
            if symbol:  # Only add if symbol exists
                bots_detected.append({
                    "ts": t.get("ts"),
                    "type": payload.get("bot_type") or payload.get("type") or "unknown",
                    "symbol": symbol,
                    "firm": payload.get("firm", "UNKNOWN"),
                    "confidence": payload.get("confidence", 0),
                    "layering_score": payload.get("layering_score", 0),
                    "timing_ms": payload.get("timing_ms", 0)
                })
    
    return jsonify({
        "bots_detected": bots_detected[-50:],
        "firm_activity": dict(firm_counts),
        "total_bot_events": len(all_thoughts),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@app.route('/api/whales')
def get_whales():
    """API endpoint for whale activity (from surveillance_dashboard)."""
    all_thoughts = []
    thoughts_file = THOUGHTS_FILE
    if thoughts_file.exists():
        try:
            with open(thoughts_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-500:]
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        t = json.loads(line)
                        topic = t.get("topic", "")
                        if "whale" in topic:
                            all_thoughts.append(t)
                    except:
                        pass
        except:
            pass
    
    # Build whale summary
    whale_walls = []
    whale_alerts = []
    
    for t in all_thoughts[-50:]:
        payload = t.get("payload", {}) or {}
        topic = t.get("topic", "")
        
        if "orderbook" in topic and "walls" in payload:
            whale_walls.append({
                "ts": t.get("ts"),
                "symbol": payload.get("symbol"),
                "bids_depth": payload.get("bids_depth", 0),
                "asks_depth": payload.get("asks_depth", 0),
                "layering_score": payload.get("layering_score", 0),
                "walls": payload.get("walls", [])[:5]  # Top 5 walls
            })
        elif "alert" in topic or "detected" in topic:
            # Extract whale data from payload
            whale_info = None
            if payload.get("symbol"):
                whale_type = payload.get("whale_type", "WHALE")
                side = payload.get("side", "UNKNOWN")
                size = payload.get("size_usd", 0)
                symbol = payload.get("symbol", "")
                whale_info = f"{whale_type} {side} ${size:,.0f} on {symbol}"
            
            whale_alerts.append({
                "ts": t.get("ts"),
                "score": payload.get("confidence", payload.get("score", 0)),
                "whale": whale_info,
                "symbol": payload.get("symbol"),
                "side": payload.get("side"),
                "size_usd": payload.get("size_usd", 0),
                "whale_type": payload.get("whale_type"),
                "critical": payload.get("size_usd", 0) > 100000  # Critical if > $100k
            })
    
    return jsonify({
        "whale_walls": whale_walls[-20:],
        "whale_alerts": whale_alerts[-20:],
        "total_whale_events": len(all_thoughts),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@app.route('/api/waves')
def get_waves():
    """API endpoint for wave scanner data (from unified_dashboard)."""
    all_thoughts = []
    thoughts_file = THOUGHTS_FILE
    if thoughts_file.exists():
        try:
            with open(thoughts_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-500:]
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        t = json.loads(line)
                        topic = t.get("topic", "")
                        if "wave" in topic or "ocean" in topic or "momentum" in topic:
                            all_thoughts.append(t)
                    except:
                        pass
        except:
            pass
    
    # Build wave summary
    wave_signals = []
    for t in all_thoughts[-30:]:
        payload = t.get("payload", {}) or {}
        wave_signals.append({
            "ts": t.get("ts"),
            "topic": t.get("topic"),
            "symbol": payload.get("symbol"),
            "strength": payload.get("strength") or payload.get("score", 0),
            "direction": payload.get("direction") or payload.get("trend")
        })
    
    return jsonify({
        "wave_signals": wave_signals,
        "total_wave_events": len(all_thoughts),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@app.route('/api/unified-feed')
def get_unified_feed():
    """API endpoint for ALL feeds unified (market, whales, bots, waves, queen)."""
    all_thoughts = []
    thoughts_file = THOUGHTS_FILE
    if thoughts_file.exists():
        try:
            with open(thoughts_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-1000:]
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        all_thoughts.append(json.loads(line))
                    except:
                        pass
        except:
            pass
    
    # Sort by timestamp
    all_thoughts.sort(key=lambda x: x.get("ts", 0), reverse=True)
    
    # Categorize
    feed = {
        "market": [],
        "whales": [],
        "bots": [],
        "waves": [],
        "queen": [],
        "system": []
    }
    
    for t in all_thoughts[:200]:
        topic = t.get("topic", "")
        entry = {
            "ts": t.get("ts"),
            "topic": topic,
            "source": t.get("source"),
            "payload": t.get("payload", {})
        }
        
        if "whale" in topic:
            feed["whales"].append(entry)
        elif "bot" in topic or "firm" in topic or "counter" in topic:
            feed["bots"].append(entry)
        elif "wave" in topic or "ocean" in topic or "momentum" in topic:
            feed["waves"].append(entry)
        elif "queen" in topic:
            feed["queen"].append(entry)
        elif "system" in topic or "execution" in topic:
            feed["system"].append(entry)
        else:
            feed["market"].append(entry)
    
    # Limit each category
    for key in feed:
        feed[key] = feed[key][:30]
    
    return jsonify({
        "feed": feed,
        "total_events": len(all_thoughts),
        "intelligence_systems": SYSTEMS_STATUS,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


def main():
    """Launch the dashboard."""
    print("🌌 AUREON SYSTEM HUB DASHBOARD")
    print("=" * 60)
    print("📊 Initializing system registry...")
    
    registry.scan_workspace()
    
    print(f"✅ Registered {len(registry.systems)} systems")
    print(f"🧠 Intelligence: {sum(SYSTEMS_STATUS.values())}/{len(SYSTEMS_STATUS)} online")
    print("\n🌐 Starting web server...")
    print("   URL: http://localhost:13001")
    print("   Press Ctrl+C to stop")
    print("=" * 60)

    # Ensure live runner is active for streaming data
    runner_ok = _ensure_live_runner()
    if runner_ok:
        print("✅ Live runner active")
    else:
        print("⚠️ Live runner not running. Start it with:")
        print(f"      python {LIVE_RUNNER_SCRIPT.relative_to(Path(__file__).resolve().parents[2])}")
        print("   It streams real provider readings only; unavailable sources report no_data.")
        print("   Set AUREON_AUTOSTART_LIVE_RUNNER=1 to have this dashboard launch it.")
    print(f"🧠 Thought stream: {THOUGHTS_FILE}")
    
    # Add startup Queen message
    dashboard_state.add_queen_message(
        f"Dashboard online - {len(registry.systems)} systems registered, "
        f"{sum(SYSTEMS_STATUS.values())} intelligence systems active",
        "success"
    )
    
    app.run(host='0.0.0.0', port=13001, debug=False)


if __name__ == "__main__":
    main()
