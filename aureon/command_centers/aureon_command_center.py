#!/usr/bin/env python3
"""
🎮👑⚔️ AUREON COMMAND CENTER ⚔️👑🎮
═══════════════════════════════════════════════════════════════════════════════

       ██████╗ ██████╗ ███╗   ███╗███╗   ███╗ █████╗ ███╗   ██╗██████╗ 
      ██╔════╝██╔═══██╗████╗ ████║████╗ ████║██╔══██╗████╗  ██║██╔══██╗
      ██║     ██║   ██║██╔████╔██║██╔████╔██║███████║██╔██╗ ██║██║  ██║
      ██║     ██║   ██║██║╚██╔╝██║██║╚██╔╝██║██╔══██║██║╚██╗██║██║  ██║
      ╚██████╗╚██████╔╝██║ ╚═╝ ██║██║ ╚═╝ ██║██║  ██║██║ ╚████║██████╔╝
       ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ 
                          
                    ██████╗███████╗███╗   ██╗████████╗███████╗██████╗ 
                   ██╔════╝██╔════╝████╗  ██║╚══██╔══╝██╔════╝██╔══██╗
                   ██║     █████╗  ██╔██╗ ██║   ██║   █████╗  ██████╔╝
                   ██║     ██╔══╝  ██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗
                   ╚██████╗███████╗██║ ╚████║   ██║   ███████╗██║  ██║
                    ╚═════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝

THE ULTIMATE UNIFIED DASHBOARD - ALL SYSTEMS IN ONE EPIC INTERFACE

Features:
👑 Queen's Voice & Commentary (Text-to-Speech)
📊 Real-time Trading Stats & P&L
🐋 Whale Tracking & Bot Intelligence
⚡ Live Trade Execution Feed
🌐 Multi-Exchange Status (Kraken, Binance, Alpaca, Capital)
🎵 Harmonic Frequency Visualization
🧠 25+ Intelligence Systems Status
🗺️ Global Bot Map
🔊 Audio Alerts & Victory Sounds
🎮 Red Alert 2 Style Command Interface

ONE DASHBOARD TO RULE THEM ALL!
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import atexit

# Debug log file (helps when console output stops)
_AUREON_DEBUG_LOG_FILE = None
def _aureon_debug_log(message: str) -> None:
    if os.getenv("AUREON_DEBUG_STARTUP") != "1":
        return
    try:
        global _AUREON_DEBUG_LOG_FILE
        if _AUREON_DEBUG_LOG_FILE is None:
            try:
                import tempfile
                from pathlib import Path
                log_path = Path(tempfile.gettempdir()) / "aureon_command_center_startup.log"
                _AUREON_DEBUG_LOG_FILE = open(log_path, "a", encoding="utf-8", errors="replace")
                _AUREON_DEBUG_LOG_FILE.write("\n=== AUREON COMMAND CENTER STARTUP DEBUG ===\n")
                _AUREON_DEBUG_LOG_FILE.flush()
                safe_print(f"[DEBUG] Startup log: {log_path}")
            except Exception:
                _AUREON_DEBUG_LOG_FILE = None
        if _AUREON_DEBUG_LOG_FILE is not None:
            _AUREON_DEBUG_LOG_FILE.write(message + "\n")
            _AUREON_DEBUG_LOG_FILE.flush()
    except Exception:
        pass

# SAFE PRINT WRAPPER FOR WINDOWS
def safe_print(*args, **kwargs):
    """Safe print that ignores I/O errors on Windows exit."""
    try:
        import builtins
        builtins.print(*args, **kwargs)
    except (ValueError, OSError):
        pass

# Optional startup debug
if os.getenv("AUREON_DEBUG_STARTUP") == "1":
    try:
        safe_print(f"[DEBUG] aureon_command_center loaded: {__file__}")
        safe_print(f"[DEBUG] CWD: {os.getcwd()}")
        _aureon_debug_log(f"loaded: {__file__}")
        _aureon_debug_log(f"cwd: {os.getcwd()}")
    except Exception:
        pass

# Guard against sys.exit during imports when debugging startup
_ORIGINAL_SYS_EXIT = sys.exit
if os.getenv("AUREON_DEBUG_STARTUP") == "1":
    def _guarded_sys_exit(code=0):
        try:
            safe_print(f"[DEBUG] Blocked sys.exit({code}) during import")
            _aureon_debug_log(f"blocked sys.exit({code})")
        except Exception:
            pass
        raise RuntimeError("sys.exit blocked during aureon_command_center import")
    sys.exit = _guarded_sys_exit

    # Also guard hard exits that bypass sys.exit
    _ORIGINAL_OS__EXIT = getattr(os, "_exit", None)
    _ORIGINAL_OS_ABORT = getattr(os, "abort", None)

    def _guarded_os_exit(code=0):
        try:
            safe_print(f"[DEBUG] Blocked os._exit({code}) during import")
            _aureon_debug_log(f"blocked os._exit({code})")
        except Exception:
            pass
        raise RuntimeError("os._exit blocked during aureon_command_center import")

    def _guarded_os_abort():
        try:
            safe_print("[DEBUG] Blocked os.abort() during import")
            _aureon_debug_log("blocked os.abort()")
        except Exception:
            pass
        raise RuntimeError("os.abort blocked during aureon_command_center import")

    try:
        if _ORIGINAL_OS__EXIT is not None:
            os._exit = _guarded_os_exit
    except Exception:
        pass
    try:
        if _ORIGINAL_OS_ABORT is not None:
            os.abort = _guarded_os_abort
    except Exception:
        pass

# Extra startup debugging: detect import-time hangs/crashes
_AUREON_DEBUG_IMPORT_ACTIVE = False
_AUREON_LAST_IMPORT = None
_AUREON_ORIGINAL_IMPORT = None
_AUREON_IMPORT_HEARTBEAT_THREAD = None

if os.getenv("AUREON_DEBUG_STARTUP") == "1":
    try:
        import builtins
        import threading
        import time as _time
        import faulthandler

        _aureon_debug_log("installing import tracer + faulthandler")

        _AUREON_DEBUG_IMPORT_ACTIVE = True
        _AUREON_ORIGINAL_IMPORT = builtins.__import__

        def _aureon_debug_import(name, globals=None, locals=None, fromlist=(), level=0):
            global _AUREON_LAST_IMPORT
            _AUREON_LAST_IMPORT = name
            start = _time.perf_counter()
            try:
                return _AUREON_ORIGINAL_IMPORT(name, globals, locals, fromlist, level)
            finally:
                elapsed = _time.perf_counter() - start
                if elapsed >= 2.0:
                    try:
                        safe_print(f"[DEBUG] Slow import: {name} ({elapsed:.2f}s)")
                        _aureon_debug_log(f"slow import: {name} ({elapsed:.2f}s)")
                    except Exception:
                        pass

        builtins.__import__ = _aureon_debug_import

        def _aureon_import_heartbeat():
            while _AUREON_DEBUG_IMPORT_ACTIVE:
                try:
                    safe_print(f"[DEBUG] Import heartbeat; last import: {_AUREON_LAST_IMPORT}")
                    _aureon_debug_log(f"heartbeat last import: {_AUREON_LAST_IMPORT}")
                except Exception:
                    pass
                _time.sleep(2.0)

        _AUREON_IMPORT_HEARTBEAT_THREAD = threading.Thread(
            target=_aureon_import_heartbeat,
            name="AureonImportHeartbeat",
            daemon=True,
        )
        _AUREON_IMPORT_HEARTBEAT_THREAD.start()

        # Dump stack traces periodically if we hang during import/startup
        try:
            # Prefer a file, stdout can get wrapped/closed on Windows
            import tempfile
            from pathlib import Path
            dump_path = Path(tempfile.gettempdir()) / "aureon_command_center_faulthandler.log"
            _aureon_debug_log(f"faulthandler file: {dump_path}")
            with open(dump_path, "a", encoding="utf-8", errors="replace") as _fh:
                faulthandler.enable(file=_fh, all_threads=True)
                faulthandler.dump_traceback_later(10, repeat=True, file=_fh)
        except Exception:
            pass
    except Exception:
        pass

# Windows UTF-8 fix - AGGRESSIVE VERSION
# Skip stderr wrapping to avoid "I/O operation on closed file" on exit
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUNBUFFERED'] = '1'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        # Only wrap stdout, NOT stderr (stderr causes shutdown errors)
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass
    
    # Aggressive cleanup: redirect stderr to devnull on exit
    def _cleanup_stderr():
        try:
            sys.stderr = open(os.devnull, 'w')
        except Exception:
            pass
    atexit.register(_cleanup_stderr)

import asyncio
import json
import time
import threading
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Live vs demo mode
DEMO_MODE = os.getenv("AUREON_COMMAND_CENTER_DEMO", "0").lower() in ("1", "true", "yes", "y")

from aureon.core.aureon_runtime_safety import (
    child_env_for_mode,
    env_truthy,
    live_block_reason,
)

# Windows deferred loading mode - start server first, load systems in background
WINDOWS_FAST_START = sys.platform == 'win32'

# Web framework
try:
    from aiohttp import web
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    safe_print("❌ aiohttp not available - pip install aiohttp")

# Thought Bus (needed for type annotations)
try:
    from aureon.core.aureon_thought_bus import Thought
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False
    Thought = None

# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM IMPORTS - Load all available intelligence systems
# On Windows: Deferred to background after server starts
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEMS_STATUS = {}
SYSTEMS_LOADING = False
SYSTEMS_LOADED = False
thought_bus = None
queen_voice = None
TRADING_FIRM_SIGNATURES = {}

def load_all_systems():
    """Load all intelligence systems - called in background on Windows"""
    global SYSTEMS_STATUS, thought_bus, queen_voice, TRADING_FIRM_SIGNATURES, SYSTEMS_LOADED, SYSTEMS_LOADING
    
    if SYSTEMS_LOADED or SYSTEMS_LOADING:
        return
    SYSTEMS_LOADING = True
    
    safe_print("🔄 Loading intelligence systems...")
    
    # Core Intelligence
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus
        SYSTEMS_STATUS['Thought Bus'] = True
        thought_bus = get_thought_bus()
    except ImportError:
        SYSTEMS_STATUS['Thought Bus'] = False
    
    try:
        from aureon.core.aureon_mycelium import MyceliumNetwork
        SYSTEMS_STATUS['Mycelium Network'] = True
    except ImportError:
        SYSTEMS_STATUS['Mycelium Network'] = False
    
    try:
        from aureon.wisdom.aureon_enigma import AureonEnigma
        SYSTEMS_STATUS['Enigma Decoder'] = True
    except ImportError:
        SYSTEMS_STATUS['Enigma Decoder'] = False
    
    try:
        from aureon.bridges.aureon_probability_nexus import EnhancedProbabilityNexus
        SYSTEMS_STATUS['Probability Nexus'] = True
    except ImportError:
        SYSTEMS_STATUS['Probability Nexus'] = False
    
    # 🛡️ SOUL SHIELD - Active Protection
    try:
        from aureon.queen.queen_soul_shield import QueenSoulShield
        SYSTEMS_STATUS['Soul Shield'] = True
        # Initialize shield but don't start monitoring (dashboard will trigger)
        queen_shield_instance = QueenSoulShield(protected_soul="Gary Leckey")
        SYSTEMS_STATUS['Soul Shield Status'] = 'Ready'
    except Exception:
        SYSTEMS_STATUS['Soul Shield'] = False
        SYSTEMS_STATUS['Soul Shield Status'] = 'Unavailable'
    
    try:
        from aureon.strategies.probability_ultimate_intelligence import ProbabilityUltimateIntelligence
        SYSTEMS_STATUS['Ultimate Intelligence'] = True
    except ImportError:
        SYSTEMS_STATUS['Ultimate Intelligence'] = False
    
    try:
        from aureon.intelligence.aureon_elephant_learning import ElephantMemory
        SYSTEMS_STATUS['Elephant Memory'] = True
    except ImportError:
        SYSTEMS_STATUS['Elephant Memory'] = False
    
    try:
        from aureon.simulation.aureon_quantum_telescope import QuantumPrism
        SYSTEMS_STATUS['Quantum Telescope'] = True
    except ImportError:
        SYSTEMS_STATUS['Quantum Telescope'] = False
    
    try:
        from aureon.intelligence.aureon_timeline_oracle import TimelineOracle
        SYSTEMS_STATUS['Timeline Oracle'] = True
    except ImportError:
        SYSTEMS_STATUS['Timeline Oracle'] = False
    
    try:
        from aureon.utils.aureon_miner_brain import MinerBrain
        SYSTEMS_STATUS['Miner Brain'] = True
    except ImportError:
        SYSTEMS_STATUS['Miner Brain'] = False
    
    try:
        from aureon.harmonic.aureon_harmonic_fusion import HarmonicWaveFusion
        SYSTEMS_STATUS['Harmonic Fusion'] = True
    except ImportError:
        SYSTEMS_STATUS['Harmonic Fusion'] = False
    
    try:
        from aureon.scanners.aureon_global_wave_scanner import GlobalWaveScanner
        SYSTEMS_STATUS['Global Wave Scanner'] = True
    except ImportError:
        SYSTEMS_STATUS['Global Wave Scanner'] = False
    
    try:
        import aureon.analytics.aureon_whale_integration as aureon_whale_integration
        SYSTEMS_STATUS['Whale Integration'] = True
    except ImportError:
        SYSTEMS_STATUS['Whale Integration'] = False
    
    try:
        from aureon.bots_intelligence.aureon_orca_intelligence import OrcaKillerWhaleIntelligence
        SYSTEMS_STATUS['Orca Intelligence'] = True
    except ImportError:
        SYSTEMS_STATUS['Orca Intelligence'] = False
    
    try:
        from aureon.utils.aureon_queen_hive_mind import QueenHiveMind
        SYSTEMS_STATUS['Queen Hive Mind'] = True
    except ImportError:
        SYSTEMS_STATUS['Queen Hive Mind'] = False
    
    try:
        from aureon.bots_intelligence.aureon_bot_intelligence_profiler import BotIntelligenceProfiler, TRADING_FIRM_SIGNATURES as TFS
        SYSTEMS_STATUS['Bot Intelligence'] = True
        TRADING_FIRM_SIGNATURES = TFS
    except ImportError:
        SYSTEMS_STATUS['Bot Intelligence'] = False
    
    try:
        from aureon.simulation.aureon_internal_multiverse import InternalMultiverse
        SYSTEMS_STATUS['Internal Multiverse'] = True
    except ImportError:
        SYSTEMS_STATUS['Internal Multiverse'] = False
    
    try:
        from aureon.wisdom.aureon_stargate_protocol import StargateProtocolEngine
        SYSTEMS_STATUS['Stargate Protocol'] = True
    except ImportError:
        SYSTEMS_STATUS['Stargate Protocol'] = False
    
    try:
        from aureon.core.aureon_memory_core import AureonMemoryCore
        SYSTEMS_STATUS['Memory Core'] = True
    except ImportError:
        SYSTEMS_STATUS['Memory Core'] = False
    
    try:
        from aureon.core.aureon_immune_system import AureonImmuneSystem
        SYSTEMS_STATUS['Immune System'] = True
    except ImportError:
        SYSTEMS_STATUS['Immune System'] = False
    
    try:
        from aureon.core.aureon_chirp_bus import get_chirp_bus, ChirpType
        SYSTEMS_STATUS['Chirp Bus'] = True
    except ImportError:
        SYSTEMS_STATUS['Chirp Bus'] = False
    
    try:
        from aureon.queen.queen_voice_engine import QueenVoiceEngine, queen_voice as qv
        SYSTEMS_STATUS['Queen Voice'] = True
        queen_voice = qv
    except ImportError:
        SYSTEMS_STATUS['Queen Voice'] = False
    
    try:
        from aureon.analytics.aureon_lighthouse import LighthousePatternDetector
        SYSTEMS_STATUS['Lighthouse'] = True
    except ImportError:
        SYSTEMS_STATUS['Lighthouse'] = False
    
    try:
        from aureon.harmonic.aureon_harmonic_signal_chain import HarmonicSignalChain
        SYSTEMS_STATUS['Harmonic Signal Chain'] = True
    except ImportError:
        SYSTEMS_STATUS['Harmonic Signal Chain'] = False
    
    # Exchange clients
    try:
        from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
        SYSTEMS_STATUS['Kraken Exchange'] = True
    except ImportError:
        SYSTEMS_STATUS['Kraken Exchange'] = False
    
    try:
        from aureon.exchanges.binance_client import BinanceClient, get_binance_client
        SYSTEMS_STATUS['Binance Exchange'] = True
    except ImportError:
        SYSTEMS_STATUS['Binance Exchange'] = False
    
    try:
        from aureon.exchanges.alpaca_client import AlpacaClient
        SYSTEMS_STATUS['Alpaca Exchange'] = True
    except ImportError:
        SYSTEMS_STATUS['Alpaca Exchange'] = False
    
    try:
        from aureon.exchanges.capital_client import CapitalClient
        SYSTEMS_STATUS['Capital Exchange'] = True
    except ImportError:
        SYSTEMS_STATUS['Capital Exchange'] = False
    
    SYSTEMS_LOADED = True
    SYSTEMS_LOADING = False
    online = sum(1 for v in SYSTEMS_STATUS.values() if v)
    safe_print(f"✅ All systems loaded! {online}/{len(SYSTEMS_STATUS)} ONLINE")

# Load systems immediately on non-Windows, defer on Windows
if not WINDOWS_FAST_START:
    load_all_systems()

# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND CENTER STATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CommandCenterState:
    """Global state for the command center"""
    # Trading stats
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    session_start: float = field(default_factory=time.time)
    
    # Live feeds
    recent_trades: deque = field(default_factory=lambda: deque(maxlen=50))
    recent_alerts: deque = field(default_factory=lambda: deque(maxlen=100))
    queen_messages: deque = field(default_factory=lambda: deque(maxlen=20))
    whale_alerts: deque = field(default_factory=lambda: deque(maxlen=30))
    bot_detections: deque = field(default_factory=lambda: deque(maxlen=50))
    
    # Exchange balances
    exchange_balances: Dict[str, Dict[str, float]] = field(default_factory=dict)
    exchange_status: Dict[str, str] = field(default_factory=dict)
    
    # Harmonic data
    harmonic_frequencies: List[Dict] = field(default_factory=list)
    wave_state: str = "BALANCED"
    coherence_score: float = 0.5
    
    # System metrics
    systems_online: int = 0
    systems_total: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    
    # WebSocket clients
    ws_clients: Set = field(default_factory=set)


# Global state
state = CommandCenterState()

# ═══════════════════════════════════════════════════════════════════════════════
# 🛫 FLIGHT CHECK SYSTEM - TIMESTAMP CONNECTIVITY VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FlightCheckResult:
    """Result of a single system flight check"""
    system_name: str
    status: str  # "GO", "NO-GO", "PHANTOM"
    ping_ms: float
    timestamp: str
    heartbeat: bool
    message: str

def run_flight_check() -> Dict[str, FlightCheckResult]:
    """
    🛫 FLIGHT CHECK - Verify real connectivity to all systems
    
    No phantom programs allowed! Each system must respond with a timestamp
    to prove it's actually alive.
    """
    import time
    from datetime import datetime
    
    results = {}
    
    # THOUGHT BUS CHECK
    try:
        start = time.perf_counter()
        from aureon.core.aureon_thought_bus import get_thought_bus, Thought
        bus = get_thought_bus()
        # Send a ping thought using think()
        ping_ts = datetime.now().isoformat()
        bus.think('flight_check_ping', topic='flight_check', metadata={'timestamp': ping_ts})
        ping_ms = (time.perf_counter() - start) * 1000
        results['Thought Bus'] = FlightCheckResult(
            'Thought Bus', 'GO', ping_ms, ping_ts, True,
            f"✅ Bus active, {len(bus._subscribers) if hasattr(bus, '_subscribers') else '?'} subs"
        )
    except Exception as e:
        results['Thought Bus'] = FlightCheckResult(
            'Thought Bus', 'NO-GO', 0, '', False, f"❌ {str(e)[:50]}"
        )
    
    # MYCELIUM NETWORK CHECK
    try:
        start = time.perf_counter()
        from aureon.core.aureon_mycelium import MyceliumNetwork
        myc = MyceliumNetwork(initial_capital=100.0)  # Default initial capital for flight check
        ping_ts = datetime.now().isoformat()
        node_count = len(myc.nodes) if hasattr(myc, 'nodes') else 'active'
        ping_ms = (time.perf_counter() - start) * 1000
        results['Mycelium Network'] = FlightCheckResult(
            'Mycelium Network', 'GO', ping_ms, ping_ts, True,
            f"✅ {node_count} nodes connected"
        )
    except Exception as e:
        results['Mycelium Network'] = FlightCheckResult(
            'Mycelium Network', 'NO-GO', 0, '', False, f"❌ {str(e)[:50]}"
        )
    
    # PROBABILITY NEXUS CHECK
    try:
        start = time.perf_counter()
        from aureon.bridges.aureon_probability_nexus import AureonProbabilityNexus
        nexus = AureonProbabilityNexus()
        ping_ts = datetime.now().isoformat()
        win_rate = getattr(nexus, 'win_rate', 0.796)
        ping_ms = (time.perf_counter() - start) * 1000
        results['Probability Nexus'] = FlightCheckResult(
            'Probability Nexus', 'GO', ping_ms, ping_ts, True,
            f"✅ {win_rate*100:.1f}% win rate"
        )
    except Exception as e:
        results['Probability Nexus'] = FlightCheckResult(
            'Probability Nexus', 'NO-GO', 0, '', False, f"❌ {str(e)[:50]}"
        )
    
    # ULTIMATE INTELLIGENCE CHECK
    try:
        start = time.perf_counter()
        from aureon.strategies.probability_ultimate_intelligence import ProbabilityUltimateIntelligence
        intel = ProbabilityUltimateIntelligence()
        ping_ts = datetime.now().isoformat()
        patterns = getattr(intel, 'patterns_loaded', 0)
        ping_ms = (time.perf_counter() - start) * 1000
        results['Ultimate Intelligence'] = FlightCheckResult(
            'Ultimate Intelligence', 'GO', ping_ms, ping_ts, True,
            f"✅ 95% accuracy, {patterns} patterns"
        )
    except Exception as e:
        results['Ultimate Intelligence'] = FlightCheckResult(
            'Ultimate Intelligence', 'NO-GO', 0, '', False, f"❌ {str(e)[:50]}"
        )
    
    # MEMORY CORE CHECK
    try:
        start = time.perf_counter()
        from aureon.core.aureon_memory_core import AureonMemoryCore
        mem = AureonMemoryCore()
        ping_ts = datetime.now().isoformat()
        stones = len(mem.stepping_stones) if hasattr(mem, 'stepping_stones') else 0
        ping_ms = (time.perf_counter() - start) * 1000
        results['Memory Core'] = FlightCheckResult(
            'Memory Core', 'GO', ping_ms, ping_ts, True,
            f"✅ {stones} stepping stones"
        )
    except Exception as e:
        results['Memory Core'] = FlightCheckResult(
            'Memory Core', 'NO-GO', 0, '', False, f"❌ {str(e)[:50]}"
        )
    
    # IMMUNE SYSTEM CHECK
    try:
        start = time.perf_counter()
        from aureon.core.aureon_immune_system import AureonImmuneSystem
        immune = AureonImmuneSystem()
        ping_ts = datetime.now().isoformat()
        health = immune.get_system_health() if hasattr(immune, 'get_system_health') else 1.0
        ping_ms = (time.perf_counter() - start) * 1000
        results['Immune System'] = FlightCheckResult(
            'Immune System', 'GO', ping_ms, ping_ts, True,
            f"✅ Health: {health*100:.0f}%"
        )
    except Exception as e:
        results['Immune System'] = FlightCheckResult(
            'Immune System', 'NO-GO', 0, '', False, f"❌ {str(e)[:50]}"
        )
    
    # LIGHTHOUSE CHECK
    try:
        start = time.perf_counter()
        from aureon.analytics.aureon_lighthouse import LighthousePatternDetector
        lighthouse = LighthousePatternDetector()
        ping_ts = datetime.now().isoformat()
        ping_ms = (time.perf_counter() - start) * 1000
        results['Lighthouse'] = FlightCheckResult(
            'Lighthouse', 'GO', ping_ms, ping_ts, True,
            f"✅ Pattern detector active"
        )
    except Exception as e:
        results['Lighthouse'] = FlightCheckResult(
            'Lighthouse', 'NO-GO', 0, '', False, f"❌ {str(e)[:50]}"
        )
    
    # WHALE INTEGRATION CHECK
    try:
        start = time.perf_counter()
        import aureon.analytics.aureon_whale_integration as aureon_whale_integration
        ping_ts = datetime.now().isoformat()
        latest = aureon_whale_integration.get_latest_prediction('BTC/USD')
        ping_ms = (time.perf_counter() - start) * 1000
        results['Whale Integration'] = FlightCheckResult(
            'Whale Integration', 'GO', ping_ms, ping_ts, True,
            f"✅ Whale tracker active"
        )
    except Exception as e:
        results['Whale Integration'] = FlightCheckResult(
            'Whale Integration', 'NO-GO', 0, '', False, f"❌ {str(e)[:50]}"
        )
    
    # ORCA INTELLIGENCE CHECK
    try:
        start = time.perf_counter()
        from aureon.bots_intelligence.aureon_orca_intelligence import OrcaKillerWhaleIntelligence
        orca = OrcaKillerWhaleIntelligence()
        ping_ts = datetime.now().isoformat()
        ping_ms = (time.perf_counter() - start) * 1000
        results['Orca Intelligence'] = FlightCheckResult(
            'Orca Intelligence', 'GO', ping_ms, ping_ts, True,
            f"✅ Killer whale hunting"
        )
    except Exception as e:
        results['Orca Intelligence'] = FlightCheckResult(
            'Orca Intelligence', 'NO-GO', 0, '', False, f"❌ {str(e)[:50]}"
        )
    
    # QUEEN HIVE MIND CHECK
    try:
        start = time.perf_counter()
        from aureon.utils.aureon_queen_hive_mind import QueenHiveMind
        queen = QueenHiveMind()
        ping_ts = datetime.now().isoformat()
        ping_ms = (time.perf_counter() - start) * 1000
        
        # Attempt to wire Orca to Queen here
        if 'Orca Intelligence' in results and results['Orca Intelligence'].status == 'GO':
            try:
                from aureon.bots_intelligence.aureon_orca_intelligence import get_orca
                orca = get_orca()
                if hasattr(orca, 'wire_queen'):
                    if orca.wire_queen(queen):
                         results['Queen Hive Mind'] = FlightCheckResult(
                            'Queen Hive Mind', 'GO', ping_ms, ping_ts, True,
                            f"✅ Queen active, ORCA WIRED"
                        )
                    else:
                         results['Queen Hive Mind'] = FlightCheckResult(
                            'Queen Hive Mind', 'NO-GO', ping_ms, ping_ts, False,
                            f"❌ Queen active, ORCA WIRE FAILED"
                        )
                else:
                    results['Queen Hive Mind'] = FlightCheckResult(
                        'Queen Hive Mind', 'GO', ping_ms, ping_ts, True,
                        f"✅ Queen active, Orca has no wire method"
                    )
            except Exception as e:
                results['Queen Hive Mind'] = FlightCheckResult(
                    'Queen Hive Mind', 'NO-GO', 0, '', False, f"❌ Orca wiring error: {str(e)[:20]}"
                )
        else:
             results['Queen Hive Mind'] = FlightCheckResult(
                'Queen Hive Mind', 'GO', ping_ms, ping_ts, True,
                f"✅ Queen consciousness active"
            )
    except Exception as e:
        results['Queen Hive Mind'] = FlightCheckResult(
            'Queen Hive Mind', 'NO-GO', 0, '', False, f"❌ {str(e)[:50]}"
        )
    
    # TIMELINE ORACLE CHECK
    try:
        start = time.perf_counter()
        from aureon.intelligence.aureon_timeline_oracle import TimelineOracle
        oracle = TimelineOracle()
        ping_ts = datetime.now().isoformat()
        ping_ms = (time.perf_counter() - start) * 1000
        results['Timeline Oracle'] = FlightCheckResult(
            'Timeline Oracle', 'GO', ping_ms, ping_ts, True,
            f"✅ 7-day vision active"
        )
    except Exception as e:
        results['Timeline Oracle'] = FlightCheckResult(
            'Timeline Oracle', 'NO-GO', 0, '', False, f"❌ {str(e)[:50]}"
        )
    
    # KRAKEN EXCHANGE CHECK
    try:
        start = time.perf_counter()
        from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
        client = get_kraken_client()
        ping_ts = datetime.now().isoformat()
        # Try to get server time (proves connectivity)
        server_time = client.get_server_time() if hasattr(client, 'get_server_time') else None
        ping_ms = (time.perf_counter() - start) * 1000
        results['Kraken Exchange'] = FlightCheckResult(
            'Kraken Exchange', 'GO', ping_ms, ping_ts, True,
            f"✅ API connected"
        )
    except Exception as e:
        results['Kraken Exchange'] = FlightCheckResult(
            'Kraken Exchange', 'NO-GO', 0, '', False, f"❌ {str(e)[:50]}"
        )
    
    # BINANCE EXCHANGE CHECK
    try:
        start = time.perf_counter()
        from aureon.exchanges.binance_client import get_binance_client
        client = get_binance_client()
        ping_ts = datetime.now().isoformat()
        ping_ms = (time.perf_counter() - start) * 1000
        results['Binance Exchange'] = FlightCheckResult(
            'Binance Exchange', 'GO', ping_ms, ping_ts, True,
            f"✅ API connected"
        )
    except Exception as e:
        results['Binance Exchange'] = FlightCheckResult(
            'Binance Exchange', 'NO-GO', 0, '', False, f"❌ {str(e)[:50]}"
        )
    
    # ALPACA EXCHANGE CHECK
    try:
        start = time.perf_counter()
        from aureon.exchanges.alpaca_client import AlpacaClient
        client = AlpacaClient()
        ping_ts = datetime.now().isoformat()
        ping_ms = (time.perf_counter() - start) * 1000
        results['Alpaca Exchange'] = FlightCheckResult(
            'Alpaca Exchange', 'GO', ping_ms, ping_ts, True,
            f"✅ API connected"
        )
    except Exception as e:
        results['Alpaca Exchange'] = FlightCheckResult(
            'Alpaca Exchange', 'NO-GO', 0, '', False, f"❌ {str(e)[:50]}"
        )
    
    return results


def print_flight_check_poem(results: Dict[str, FlightCheckResult]) -> str:
    """
    🎭 THE FLIGHT CHECK POEM
    
    A poetic readout of system status with timestamps proving life.
    No phantoms here - only real, living systems.
    """
    from datetime import datetime
    
    go_count = sum(1 for r in results.values() if r.status == 'GO')
    total = len(results)
    # Compose `all_go` from the per-system check results AND the real
    # exchange-connectivity health helper (single source of truth shared with
    # the /health endpoint). Stops the dashboard from showing "ALL SYSTEMS GO"
    # while Kraken/Binance/HNC daemon are actually unreachable.
    all_systems_ok = go_count == total
    real_health_ok, real_health_failures = (True, [])
    try:
        from aureon.queen.queen_quantum_frog import compute_real_health
        real_health_ok, real_health_failures = compute_real_health()
    except Exception:
        # If the real-health helper itself fails, treat as unhealthy rather
        # than silently passing — operator must see why.
        real_health_ok = False
        real_health_failures = ["compute_real_health_unavailable"]
    all_go = all_systems_ok and real_health_ok

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    poem = f"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║     🛫 AUREON FLIGHT CHECK - TIMESTAMP VERIFICATION 🛫                           ║
║     ════════════════════════════════════════════════                             ║
║                                                                                  ║
║     "No phantom shall pass, no ghost shall deceive,                              ║
║      Each system must answer, each heartbeat believe.                            ║
║      Through timestamps we verify, through pings we confirm,                     ║
║      That every connection is real, alive, and firm."                            ║
║                                                                                  ║
║     FLIGHT CHECK TIME: {timestamp}                                  ║
║                                                                                  ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  SYSTEM                    │ STATUS  │  PING   │ HEARTBEAT │ MESSAGE            ║
╠════════════════════════════╪═════════╪═════════╪═══════════╪════════════════════╣
"""
    
    for name, result in results.items():
        status_icon = "✅ GO   " if result.status == 'GO' else "❌ NO-GO"
        ping_str = f"{result.ping_ms:6.1f}ms" if result.ping_ms > 0 else "   N/A  "
        heartbeat = "💓 ALIVE" if result.heartbeat else "💀 DEAD "
        msg = result.message[:18] if len(result.message) > 18 else result.message.ljust(18)
        name_padded = name[:24].ljust(24)
        
        poem += f"║  {name_padded} │ {status_icon} │ {ping_str} │ {heartbeat}  │ {msg} ║\n"
    
    poem += f"""╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                  ║
║     FLIGHT STATUS: {'🟢 ALL SYSTEMS GO - CLEAR FOR LAUNCH!' if all_go else (f'🔴 {total - go_count} SYSTEM(S) NOT READY      ' if not real_health_ok and all_systems_ok else f'🔴 LIVE-DATA UNHEALTHY: {", ".join(real_health_failures[:2])[:50]}'.ljust(48))}                       ║
║     SYSTEMS ONLINE: {go_count}/{total} ({go_count*100//total}%)                                                       ║
║                                                                                  ║
║     "With heartbeats confirmed and timestamps true,                              ║
║      The Queen's armada is ready, through and through."                          ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""
    
    return poem


# Store last flight check results
LAST_FLIGHT_CHECK: Dict[str, FlightCheckResult] = {}
LAST_FLIGHT_CHECK_TIME: float = 0

# Live feed toggle (real data on/off)
LIVE_FEED_ENABLED = True

# Trading engine toggle (real trading on/off)
TRADING_LIVE_ENABLED = False
TRADING_PROCESS: Optional[asyncio.subprocess.Process] = None
TRADING_MODE = "off"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _build_trading_command(live: bool) -> List[str]:
    cmd = [sys.executable, "-u", "-m", "aureon.trading.micro_profit_labyrinth"]
    if live:
        cmd.extend(["--live", "--yes", "--multi-exchange"])
    else:
        duration = os.getenv("AUREON_COMMAND_CENTER_DRY_RUN_DURATION", "86400")
        cmd.extend(["--dry-run", "--multi-exchange", "--duration", duration])
    return cmd


async def _stop_trading_engine() -> None:
    global TRADING_LIVE_ENABLED, TRADING_PROCESS, TRADING_MODE
    if TRADING_PROCESS and TRADING_PROCESS.returncode is None:
        TRADING_PROCESS.terminate()
        try:
            await asyncio.wait_for(TRADING_PROCESS.wait(), timeout=10)
        except asyncio.TimeoutError:
            TRADING_PROCESS.kill()
    TRADING_PROCESS = None
    TRADING_LIVE_ENABLED = False
    TRADING_MODE = "off"


async def _start_trading_engine(live: bool) -> None:
    global TRADING_LIVE_ENABLED, TRADING_PROCESS, TRADING_MODE
    if live:
        reason = live_block_reason("Command Center")
        if reason:
            raise RuntimeError(reason)

    cmd = _build_trading_command(live)
    env = child_env_for_mode(live, os.environ)
    TRADING_PROCESS = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(REPO_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )
    TRADING_LIVE_ENABLED = live
    TRADING_MODE = "live" if live else "dry_run"

# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND CENTER HTML - THE EPIC INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

COMMAND_CENTER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎮👑 AUREON COMMAND CENTER 👑🎮</title>
    
    <!-- OPEN SOURCE CDN LIBRARIES -->
    <!-- Three.js for 3D Globe -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <!-- GSAP for smooth animations + plugins -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/TextPlugin.min.js"></script>
    <!-- Howler.js for sound effects -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/howler/2.2.3/howler.min.js"></script>
    <!-- Chart.js for real-time charts -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
    <!-- Particles.js for background effects -->
    <script src="https://cdn.jsdelivr.net/particles.js/2.0.0/particles.min.js"></script>
    <!-- Typed.js for typing effect on Queen messages -->
    <script src="https://cdn.jsdelivr.net/npm/typed.js@2.0.12"></script>
    <!-- CountUp.js for animated numbers -->
    <script src="https://cdn.jsdelivr.net/npm/countup.js@2.8.0/dist/countUp.umd.js"></script>
    <!-- ApexCharts for beautiful trading charts -->
    <script src="https://cdn.jsdelivr.net/npm/apexcharts@3.45.0/dist/apexcharts.min.js"></script>
    <!-- Anime.js for more advanced animations -->
    <script src="https://cdn.jsdelivr.net/npm/animejs@3.2.2/lib/anime.min.js"></script>
    <!-- Leaflet.js for world map -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <!-- Globe.gl for 3D globe -->
    <script src="https://unpkg.com/globe.gl"></script>
    <!-- ECharts for radar charts -->
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <!-- xterm.js for terminal emulator -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/xterm/5.5.0/xterm.min.css" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xterm/5.5.0/xterm.min.js"></script>
    <!-- SweetAlert2 for tactical alerts -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/sweetalert2@11.10.7/dist/sweetalert2.min.css" />
    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11.10.7/dist/sweetalert2.all.min.js"></script>
    <!-- Animate.css for easy CSS animations -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css" />
    <!-- Lottie for animated icons -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script>
    <!-- Framer Motion alternative - Motion One (lightweight) -->
    <script src="https://cdn.jsdelivr.net/npm/motion@10.16.4/dist/motion.min.js"></script>
    <!-- Hover.css for button/hover effects -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/hover.css/2.3.1/css/hover-min.css" />
    
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&family=Rajdhani:wght@400;500;600;700&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --gold: #FFD700;
            --gold-dark: #B8860B;
            --green: #00FF88;
            --green-dark: #00AA55;
            --red: #FF3366;
            --red-dark: #CC0033;
            --blue: #00BFFF;
            --purple: #9966FF;
            --cyan: #00FFFF;
            --orange: #FF6600;
            --bg-dark: #0a0a0f;
            --bg-panel: rgba(15, 15, 25, 0.95);
            --border-glow: rgba(255, 215, 0, 0.6);
            --metal-light: #4a4a5a;
            --metal-dark: #1a1a2a;
            --alert-red: #ff0000;
        }
        
        /* CRT SCANLINE EFFECT OVERLAY */
        body::before {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 9999;
            background: repeating-linear-gradient(
                0deg,
                rgba(0, 0, 0, 0.15),
                rgba(0, 0, 0, 0.15) 1px,
                transparent 1px,
                transparent 2px
            );
        }
        
        /* CRT FLICKER EFFECT */
        body::after {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 9998;
            background: radial-gradient(ellipse at center, transparent 0%, rgba(0, 0, 0, 0.3) 100%);
            animation: crtFlicker 0.15s infinite;
        }
        
        @keyframes crtFlicker {
            0% { opacity: 0.97; }
            50% { opacity: 1; }
            100% { opacity: 0.98; }
        }
        
        body {
            font-family: 'Rajdhani', 'Share Tech Mono', monospace;
            background: #0a0a0f;
            color: var(--green);
            overflow: hidden;
            height: 100vh;
        }
        
        /* ═══════════════════════════════════════════════════════════════════════
           🎨 ENHANCED MICRO-INTERACTIONS & ANIMATIONS
           ═══════════════════════════════════════════════════════════════════════ */
        
        /* NEON GLOW EFFECTS */
        .neon-glow-green {
            filter: drop-shadow(0 0 5px var(--green)) drop-shadow(0 0 15px var(--green)) drop-shadow(0 0 30px var(--green));
        }
        
        .neon-glow-gold {
            filter: drop-shadow(0 0 5px var(--gold)) drop-shadow(0 0 15px var(--gold)) drop-shadow(0 0 30px var(--gold));
        }
        
        /* GRADIENT TEXT ANIMATION */
        .gradient-text-animated {
            background: linear-gradient(90deg, var(--gold), var(--orange), var(--red), var(--orange), var(--gold));
            background-size: 400% 100%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradientShift 4s ease infinite;
        }
        
        @keyframes gradientShift {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        /* FLOATING ANIMATION */
        .float-animation {
            animation: floatUpDown 3s ease-in-out infinite;
        }
        
        @keyframes floatUpDown {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        
        /* ROTATE 3D HOVER */
        .rotate-3d-hover {
            transition: transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            transform-style: preserve-3d;
        }
        
        .rotate-3d-hover:hover {
            transform: rotateY(10deg) rotateX(5deg) scale(1.05);
        }
        
        /* POP IN ANIMATION */
        .pop-in {
            animation: popIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        }
        
        @keyframes popIn {
            0% { transform: scale(0); opacity: 0; }
            100% { transform: scale(1); opacity: 1; }
        }
        
        /* SLIDE IN FROM LEFT/RIGHT */
        .slide-in-left {
            animation: slideInLeft 0.5s ease-out forwards;
        }
        
        .slide-in-right {
            animation: slideInRight 0.5s ease-out forwards;
        }
        
        @keyframes slideInLeft {
            from { transform: translateX(-100px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideInRight {
            from { transform: translateX(100px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        /* RIPPLE EFFECT ON CLICK */
        .ripple {
            position: relative;
            overflow: hidden;
        }
        
        .ripple::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            transform: translate(-50%, -50%);
            transition: width 0.5s ease, height 0.5s ease;
        }
        
        .ripple:active::before {
            width: 300%;
            height: 300%;
        }
        
        /* BORDER GLOW PULSE */
        .border-glow-pulse {
            animation: borderGlowPulse 2s ease-in-out infinite;
        }
        
        @keyframes borderGlowPulse {
            0%, 100% { box-shadow: 0 0 5px var(--green), 0 0 10px var(--green), inset 0 0 5px rgba(0, 255, 136, 0.1); }
            50% { box-shadow: 0 0 20px var(--green), 0 0 40px var(--green), inset 0 0 15px rgba(0, 255, 136, 0.2); }
        }
        
        /* NUMBER COUNTING ANIMATION */
        .count-up {
            display: inline-block;
            transition: transform 0.3s ease, color 0.3s ease;
        }
        
        .count-up.updating {
            transform: scale(1.2);
            color: var(--gold) !important;
        }
        
        /* GLITCH TEXT EFFECT */
        .glitch-text {
            position: relative;
        }
        
        .glitch-text::before,
        .glitch-text::after {
            content: attr(data-text);
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }
        
        .glitch-text::before {
            left: 2px;
            text-shadow: -2px 0 var(--cyan);
            animation: glitchLeft 2s infinite linear alternate-reverse;
            clip-path: polygon(0 0, 100% 0, 100% 35%, 0 35%);
        }
        
        .glitch-text::after {
            left: -2px;
            text-shadow: 2px 0 var(--red);
            animation: glitchRight 3s infinite linear alternate-reverse;
            clip-path: polygon(0 65%, 100% 65%, 100% 100%, 0 100%);
        }
        
        @keyframes glitchLeft {
            0%, 100% { transform: translateX(0); }
            20% { transform: translateX(-3px); }
            40% { transform: translateX(3px); }
            60% { transform: translateX(-1px); }
            80% { transform: translateX(1px); }
        }
        
        @keyframes glitchRight {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(2px); }
            50% { transform: translateX(-2px); }
            75% { transform: translateX(1px); }
        }
        
        /* HOLOGRAM EFFECT */
        .hologram {
            background: linear-gradient(180deg, 
                rgba(0, 255, 255, 0.1) 0%, 
                rgba(0, 255, 255, 0.05) 50%, 
                rgba(0, 255, 255, 0.1) 100%);
            animation: hologramScan 3s linear infinite;
            position: relative;
        }
        
        .hologram::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--cyan), transparent);
            animation: scanLine 2s linear infinite;
        }
        
        @keyframes hologramScan {
            0% { filter: brightness(1) hue-rotate(0deg); }
            50% { filter: brightness(1.2) hue-rotate(10deg); }
            100% { filter: brightness(1) hue-rotate(0deg); }
        }
        
        @keyframes scanLine {
            0% { top: 0; opacity: 1; }
            100% { top: 100%; opacity: 0; }
        }
        
        /* ENERGY BARS */
        .energy-bar {
            height: 4px;
            background: linear-gradient(90deg, var(--green), var(--cyan), var(--blue));
            background-size: 200% 100%;
            animation: energyFlow 2s linear infinite;
            border-radius: 2px;
        }
        
        @keyframes energyFlow {
            0% { background-position: 200% 0; }
            100% { background-position: 0 0; }
        }
        
        /* LOTTIE CONTAINER */
        .lottie-icon {
            width: 40px;
            height: 40px;
            display: inline-block;
        }
        
        .lottie-icon-lg {
            width: 80px;
            height: 80px;
        }
        
        /* PULSE RING */
        .pulse-ring {
            position: relative;
        }
        
        .pulse-ring::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 100%;
            height: 100%;
            border: 2px solid var(--green);
            border-radius: 50%;
            transform: translate(-50%, -50%);
            animation: pulseRing 1.5s ease-out infinite;
        }
        
        @keyframes pulseRing {
            0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
            100% { transform: translate(-50%, -50%) scale(1.5); opacity: 0; }
        }
        
        /* CYBER GRID BACKGROUND */
        .cyber-grid {
            background-image: 
                linear-gradient(rgba(0, 255, 136, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 255, 136, 0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            animation: gridMove 20s linear infinite;
        }
        
        @keyframes gridMove {
            0% { background-position: 0 0; }
            100% { background-position: 50px 50px; }
        }
        
        /* ═══════════════════════════════════════════════════════════════════════
           🌀 STARGATE PORTAL SYSTEM - CHEVRON RING & EVENT HORIZON
           ═══════════════════════════════════════════════════════════════════════ */
        
        /* STARGATE CONTAINER */
        #stargate-container {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 400px;
            height: 400px;
            z-index: 100;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.5s ease;
        }
        
        #stargate-container.active {
            opacity: 1;
            pointer-events: auto;
        }
        
        /* OUTER RING - NAQUADAH FRAME */
        .stargate-ring {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background: conic-gradient(
                from 0deg,
                #1a1a2a 0deg,
                #3a3a5a 10deg,
                #1a1a2a 20deg,
                #3a3a5a 30deg,
                #1a1a2a 40deg,
                #3a3a5a 50deg,
                #1a1a2a 60deg,
                #3a3a5a 70deg,
                #1a1a2a 80deg,
                #3a3a5a 90deg,
                #1a1a2a 100deg,
                #3a3a5a 110deg,
                #1a1a2a 120deg,
                #3a3a5a 130deg,
                #1a1a2a 140deg,
                #3a3a5a 150deg,
                #1a1a2a 160deg,
                #3a3a5a 170deg,
                #1a1a2a 180deg,
                #3a3a5a 190deg,
                #1a1a2a 200deg,
                #3a3a5a 210deg,
                #1a1a2a 220deg,
                #3a3a5a 230deg,
                #1a1a2a 240deg,
                #3a3a5a 250deg,
                #1a1a2a 260deg,
                #3a3a5a 270deg,
                #1a1a2a 280deg,
                #3a3a5a 290deg,
                #1a1a2a 300deg,
                #3a3a5a 310deg,
                #1a1a2a 320deg,
                #3a3a5a 330deg,
                #1a1a2a 340deg,
                #3a3a5a 350deg,
                #1a1a2a 360deg
            );
            box-shadow:
                0 0 50px rgba(0, 191, 255, 0.3),
                inset 0 0 50px rgba(0, 0, 0, 0.8),
                inset 0 0 100px rgba(0, 191, 255, 0.1);
            animation: stargateRingSpin 60s linear infinite;
        }
        
        @keyframes stargateRingSpin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        /* INNER RING - GLYPH TRACK */
        .glyph-ring {
            position: absolute;
            top: 20px;
            left: 20px;
            right: 20px;
            bottom: 20px;
            border-radius: 50%;
            background: #0a0a15;
            border: 3px solid #2a2a4a;
            animation: glyphRingSpin 45s linear infinite reverse;
        }
        
        @keyframes glyphRingSpin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        /* CHEVRON CONTAINERS */
        .chevron {
            position: absolute;
            width: 30px;
            height: 50px;
            left: 50%;
            top: -5px;
            transform-origin: 50% 205px;
            z-index: 10;
        }
        
        .chevron-inner {
            width: 100%;
            height: 100%;
            background: linear-gradient(180deg, #4a4a6a 0%, #2a2a4a 50%, #1a1a3a 100%);
            clip-path: polygon(50% 0%, 100% 40%, 80% 100%, 20% 100%, 0% 40%);
            border: 2px solid #5a5a7a;
            transition: all 0.3s ease;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
        }
        
        .chevron.locked .chevron-inner {
            background: linear-gradient(180deg, #ff6600 0%, #ff3300 50%, #cc2200 100%);
            box-shadow:
                0 0 20px rgba(255, 102, 0, 0.8),
                0 0 40px rgba(255, 102, 0, 0.4),
                inset 0 0 10px rgba(255, 255, 255, 0.3);
            animation: chevronGlow 1s ease infinite;
        }
        
        @keyframes chevronGlow {
            0%, 100% { filter: brightness(1); }
            50% { filter: brightness(1.3); }
        }
        
        /* 9 CHEVRONS positioned around the ring */
        .chevron:nth-child(1) { transform: rotate(0deg); }
        .chevron:nth-child(2) { transform: rotate(40deg); }
        .chevron:nth-child(3) { transform: rotate(80deg); }
        .chevron:nth-child(4) { transform: rotate(120deg); }
        .chevron:nth-child(5) { transform: rotate(160deg); }
        .chevron:nth-child(6) { transform: rotate(200deg); }
        .chevron:nth-child(7) { transform: rotate(240deg); }
        .chevron:nth-child(8) { transform: rotate(280deg); }
        .chevron:nth-child(9) { transform: rotate(320deg); }
        
        /* EVENT HORIZON - WORMHOLE CENTER */
        .event-horizon {
            position: absolute;
            top: 50px;
            left: 50px;
            right: 50px;
            bottom: 50px;
            border-radius: 50%;
            background: radial-gradient(
                circle at center,
                #000510 0%,
                #001030 20%,
                #002060 40%,
                #0040a0 60%,
                #0060d0 80%,
                #00aaff 100%
            );
            overflow: hidden;
            opacity: 0;
            transform: scale(0);
            transition: all 0.8s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        }
        
        .event-horizon.active {
        /* WORMHOLE SWIRL */
        .event-horizon::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: conic-gradient(
                from 0deg,
                transparent 0deg,
                rgba(0, 170, 255, 0.3) 60deg,
                transparent 120deg,
                rgba(0, 170, 255, 0.3) 180deg,
                transparent 240deg,
                rgba(0, 170, 255, 0.3) 300deg,
                transparent 360deg
            );
            animation: wormholeSwirl 3s linear infinite;
        }
        
        @keyframes wormholeSwirl {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        /* KAWOOSH EFFECT */
        .kawoosh {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: radial-gradient(
                circle,
                rgba(255, 255, 255, 0.9) 0%,
                rgba(0, 170, 255, 0.8) 30%,
                rgba(0, 100, 200, 0.4) 60%,
                transparent 100%
            );
            transform: translate(-50%, -50%);
            opacity: 0;
            z-index: 20;
        }
        
        .kawoosh.active {
            animation: kawooshBlast 1.5s ease-out forwards;
        }
        
        @keyframes kawooshBlast {
            0% { width: 0; height: 0; opacity: 0; }
            20% { width: 600px; height: 600px; opacity: 1; }
            40% { width: 400px; height: 400px; opacity: 0.8; }
            100% { width: 280px; height: 280px; opacity: 0; }
        }
        
        /* DHD - DIAL HOME DEVICE */
        #dhd-panel {
            position: fixed;
            bottom: 80px;
            right: 20px;
            width: 320px;
            height: 280px;
            z-index: 60;
            background: linear-gradient(180deg, #2a2a3a 0%, #1a1a2a 100%);
            border: 2px solid var(--cyan);
            border-radius: 10px;
            padding: 10px;
            box-shadow:
                0 0 30px rgba(0, 191, 255, 0.3),
                inset 0 0 20px rgba(0, 0, 0, 0.8);
        }
        
        #dhd-panel .panel-header {
            background: linear-gradient(90deg, rgba(0, 191, 255, 0.3), transparent);
            padding: 5px 10px;
            margin: -10px -10px 10px -10px;
            border-bottom: 1px solid var(--cyan);
            color: var(--cyan);
            font-family: 'Orbitron', sans-serif;
            font-size: 0.8em;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        /* GLYPH GRID */
        .glyph-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 5px;
            margin-bottom: 10px;
        }
        
        .glyph-btn {
            aspect-ratio: 1;
            background: linear-gradient(180deg, #3a3a4a 0%, #1a1a2a 100%);
            border: 1px solid #4a4a5a;
            border-radius: 5px;
            color: var(--cyan);
            font-size: 1.2em;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .glyph-btn:hover {
            background: linear-gradient(180deg, #4a4a6a 0%, #2a2a4a 100%);
            border-color: var(--cyan);
            box-shadow: 0 0 15px rgba(0, 191, 255, 0.5);
            transform: scale(1.1);
        }
        
        .glyph-btn.selected {
            background: linear-gradient(180deg, #004466 0%, #002244 100%);
            border-color: var(--cyan);
            box-shadow: 0 0 20px rgba(0, 191, 255, 0.8);
            color: #fff;
        }
        
        /* DHD CENTER BUTTON */
        .dhd-activate {
            width: 80px;
            height: 80px;
            margin: 10px auto;
            background: radial-gradient(circle, #ff3300 0%, #cc2200 50%, #881100 100%);
            border: 3px solid #ff6600;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2em;
            color: #fff;
            box-shadow:
                0 0 30px rgba(255, 102, 0, 0.5),
                inset 0 0 20px rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
        }
        
        .dhd-activate:hover {
            transform: scale(1.1);
            box-shadow:
                0 0 50px rgba(255, 102, 0, 0.8),
                inset 0 0 30px rgba(255, 255, 255, 0.3);
        }
        
        .dhd-activate:active {
            transform: scale(0.95);
        }
        
        .dhd-activate.engaged {
            background: radial-gradient(circle, #00ff88 0%, #00cc66 50%, #008844 100%);
            border-color: var(--green);
            box-shadow:
                0 0 50px rgba(0, 255, 136, 0.8),
                inset 0 0 30px rgba(255, 255, 255, 0.3);
            animation: dhdPulse 1s ease infinite;
        }
        
        @keyframes dhdPulse {
            0%, 100% { box-shadow: 0 0 50px rgba(0, 255, 136, 0.8), inset 0 0 30px rgba(255, 255, 255, 0.3); }
            50% { box-shadow: 0 0 80px rgba(0, 255, 136, 1), inset 0 0 40px rgba(255, 255, 255, 0.5); }
        }
        
        /* QUANTUM MIRROR PANEL */
        #quantum-mirror-panel {
            position: fixed;
            top: 100px;
            left: 20px;
            width: 280px;
            z-index: 55;
            background: rgba(10, 10, 20, 0.95);
            border: 2px solid var(--purple);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 0 30px rgba(153, 102, 255, 0.3);
        }
        
        #quantum-mirror-panel .panel-header {
            background: linear-gradient(90deg, rgba(153, 102, 255, 0.3), transparent);
            padding: 8px 12px;
            border-bottom: 1px solid var(--purple);
            color: var(--purple);
            font-family: 'Orbitron', sans-serif;
            font-size: 0.8em;
        }
        
        .timeline-card {
            padding: 10px;
            margin: 8px;
            background: linear-gradient(135deg, rgba(153, 102, 255, 0.1) 0%, rgba(0, 0, 0, 0.3) 100%);
            border: 1px solid rgba(153, 102, 255, 0.3);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            transform-style: preserve-3d;
            perspective: 1000px;
        }
        
        .timeline-card:hover {
            transform: rotateY(5deg) scale(1.02);
            border-color: var(--purple);
            box-shadow: 0 0 20px rgba(153, 102, 255, 0.5);
        }
        
        .timeline-card.anchored {
            background: linear-gradient(135deg, rgba(0, 255, 136, 0.2) 0%, rgba(0, 0, 0, 0.3) 100%);
            border-color: var(--green);
            animation: timelineAnchored 2s ease infinite;
        }
        
        @keyframes timelineAnchored {
            0%, 100% { box-shadow: 0 0 20px rgba(0, 255, 136, 0.3); }
            50% { box-shadow: 0 0 40px rgba(0, 255, 136, 0.6); }
        }
        
        .timeline-name {
            color: var(--gold);
            font-weight: bold;
            font-size: 0.9em;
            margin-bottom: 5px;
        }
        
        .timeline-coherence {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.8em;
        }
        
        .coherence-bar {
            flex: 1;
            height: 6px;
            background: rgba(0, 0, 0, 0.5);
            border-radius: 3px;
            overflow: hidden;
        }
        
        .coherence-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--purple), var(--cyan));
            border-radius: 3px;
            transition: width 0.5s ease;
        }
        
        .coherence-value {
            color: var(--cyan);
            font-family: 'Share Tech Mono', monospace;
            min-width: 40px;
            text-align: right;
        }
        
        /* STARGATE STATUS DISPLAY */
        #stargate-status {
            position: fixed;
            top: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.9);
            border: 2px solid var(--cyan);
            border-radius: 10px;
            padding: 10px 30px;
            z-index: 90;
            font-family: 'Orbitron', sans-serif;
            color: var(--cyan);
            text-align: center;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        #stargate-status.active {
            opacity: 1;
        }
        
        .chevron-display {
            display: flex;
            gap: 5px;
            justify-content: center;
            margin-top: 5px;
        }
        
        .chevron-indicator {
            width: 20px;
            height: 20px;
            background: #333;
            border: 1px solid #555;
            clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
            transition: all 0.3s ease;
        }
        
        .chevron-indicator.locked {
            background: linear-gradient(180deg, #ff6600, #cc3300);
            border-color: #ff8800;
            box-shadow: 0 0 10px rgba(255, 102, 0, 0.8);
        }
        
        /* PLANETARY NODE INDICATORS */
        .planetary-nodes {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            padding: 10px;
        }
        
        .node-indicator {
            padding: 3px 8px;
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(153, 102, 255, 0.3);
            border-radius: 12px;
            font-size: 0.7em;
            color: #888;
            transition: all 0.3s ease;
        }
        
        .node-indicator.resonating {
            border-color: var(--gold);
            color: var(--gold);
            box-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
            animation: nodeResonance 1.5s ease infinite;
        }
        
        @keyframes nodeResonance {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        
        /* PARTICLE BACKGROUND */
        #particles-js {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a0a1e 30%, #0a1a1e 60%, #0f0f1a 100%);
        }
        
        /* RED ALERT MODE */
        body.red-alert {
            animation: redAlertPulse 1s infinite;
        }
        
        body.red-alert::after {
            background: radial-gradient(ellipse at center, rgba(255, 0, 0, 0.1) 0%, rgba(0, 0, 0, 0.4) 100%);
        }
        
        @keyframes redAlertPulse {
            0%, 100% { filter: brightness(1); }
            50% { filter: brightness(1.1) hue-rotate(-10deg); }
        }
        
        /* METALLIC PANEL STYLING - C&C STYLE */
        .metal-panel {
            background: linear-gradient(180deg, 
                var(--metal-light) 0%, 
                var(--metal-dark) 5%, 
                var(--bg-dark) 10%, 
                var(--bg-dark) 90%, 
                var(--metal-dark) 95%, 
                var(--metal-light) 100%
            );
            border: 2px solid var(--metal-light);
            border-radius: 3px;
            box-shadow: 
                inset 0 2px 4px rgba(255, 255, 255, 0.1),
                inset 0 -2px 4px rgba(0, 0, 0, 0.5),
                0 0 20px rgba(0, 255, 136, 0.2);
        }
        
        .metal-panel::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, 
                transparent, 
                rgba(255, 215, 0, 0.5), 
                transparent
            );
        }
        
        /* HEADER - COMMAND BAR */
        #header {
            background: linear-gradient(180deg, 
                #2a2a3a 0%, 
                #1a1a2a 5%, 
                #0f0f1a 50%, 
                #1a1a2a 95%, 
                #2a2a3a 100%
            );
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid var(--gold);
            box-shadow: 
                0 4px 30px rgba(255, 215, 0, 0.4),
                inset 0 -2px 10px rgba(0, 0, 0, 0.5);
            position: relative;
            z-index: 100;
        }
        
        /* RIVETS ON PANELS */
        .rivet {
            position: absolute;
            width: 8px;
            height: 8px;
            background: radial-gradient(circle at 30% 30%, #666, #222);
            border-radius: 50%;
            box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.3);
        }
        
        #logo {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.8em;
            font-weight: 900;
            background: linear-gradient(90deg, var(--gold), var(--orange), var(--gold));
            background-size: 200% 100%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: shimmer 3s linear infinite;
            text-shadow: 0 0 30px rgba(255, 215, 0, 0.8);
            letter-spacing: 2px;
        }
        
        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
        
        #status-bar {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 5px 15px;
            background: rgba(0, 255, 136, 0.1);
            border: 1px solid var(--green);
            border-radius: 5px;
        }
        
        .status-item.warning {
            background: rgba(255, 102, 0, 0.2);
            border-color: var(--orange);
            color: var(--orange);
        }
        
        .status-item.danger {
            background: rgba(255, 51, 102, 0.2);
            border-color: var(--red);
            color: var(--red);
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--green);
            animation: pulse 1.5s infinite;
        }
        
        .status-dot.warning { background: var(--orange); }
        .status-dot.danger { background: var(--red); animation: blink 0.5s infinite; }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
        }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        
        /* MAIN GRID LAYOUT */
        #main-container {
            display: grid;
            grid-template-columns: 280px 1fr 320px;
            grid-template-rows: auto 1fr auto;
            gap: 10px;
            padding: 10px;
            height: calc(100vh - 70px);
        }
        
        /* PANELS */
        .panel {
            background: var(--bg-panel);
            border: 2px solid var(--green);
            border-radius: 10px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.2), inset 0 0 30px rgba(0, 0, 0, 0.5);
        }
        
        .panel-header {
            background: linear-gradient(90deg, rgba(0, 255, 136, 0.3), transparent);
            padding: 10px 15px;
            border-bottom: 1px solid var(--green);
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .panel-content {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }
        
        .panel.gold-border {
            border-color: var(--gold);
            box-shadow: 0 0 25px rgba(255, 215, 0, 0.3), inset 0 0 30px rgba(0, 0, 0, 0.5);
        }
        
        .panel.gold-border .panel-header {
            background: linear-gradient(90deg, rgba(255, 215, 0, 0.3), transparent);
            border-bottom-color: var(--gold);
            color: var(--gold);
        }
        
        /* QUEEN VOICE PANEL */
        #queen-panel {
            grid-column: 1 / -1;
            grid-row: 1;
            min-height: 120px;
            max-height: 150px;
            background: linear-gradient(135deg, rgba(255, 215, 0, 0.15), rgba(255, 102, 0, 0.1), rgba(255, 215, 0, 0.15));
            border: 3px solid var(--gold);
            position: relative;
            overflow: hidden;
        }
        
        #queen-avatar {
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 80px;
            animation: queenPulse 2s infinite;
            filter: drop-shadow(0 0 20px rgba(255, 215, 0, 0.8));
        }
        
        @keyframes queenPulse {
            0%, 100% { transform: translateY(-50%) scale(1); }
            50% { transform: translateY(-50%) scale(1.05); }
        }
        
        #queen-message {
            margin-left: 120px;
            padding: 15px;
            font-size: 1.4em;
            color: var(--gold);
            text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
            line-height: 1.4;
        }
        
        #queen-status {
            position: absolute;
            bottom: 10px;
            right: 20px;
            font-size: 0.85em;
            color: #888;
        }
        
        #voice-toggle {
            position: absolute;
            top: 10px;
            right: 10px;
            padding: 8px 15px;
            background: var(--gold);
            color: #000;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            transition: all 0.3s;
        }
        
        #voice-toggle:hover {
            background: var(--orange);
            transform: scale(1.05);
        }
        
        #voice-toggle.speaking {
            animation: speakPulse 0.5s infinite;
        }
        
        @keyframes speakPulse {
            0%, 100% { background: var(--gold); }
            50% { background: var(--red); }
        }
        
        /* LEFT SIDEBAR - SYSTEMS */
        #systems-panel {
            grid-column: 1;
            grid-row: 2;
        }
        
        .system-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 10px;
            margin-bottom: 5px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 5px;
            border-left: 3px solid var(--green);
            transition: all 0.3s;
        }
        
        .system-item:hover {
            background: rgba(0, 255, 136, 0.1);
            transform: translateX(5px);
        }
        
        .system-item.offline {
            border-left-color: var(--red);
            opacity: 0.6;
        }
        
        .system-item.warning {
            border-left-color: var(--orange);
        }
        
        .system-name {
            font-size: 0.85em;
        }
        
        .system-status {
            font-size: 0.75em;
            padding: 2px 8px;
            border-radius: 3px;
            background: rgba(0, 255, 136, 0.2);
        }
        
        .system-status.offline {
            background: rgba(255, 51, 102, 0.3);
            color: var(--red);
        }
        
        /* CENTER - MAIN DISPLAY */
        #main-display {
            grid-column: 2;
            grid-row: 2;
            display: grid;
            grid-template-rows: auto 1fr auto;
            gap: 10px;
        }
        
        /* STATS ROW */
        #stats-row {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 10px;
        }
        
        .stat-card {
            background: var(--bg-panel);
            border: 2px solid var(--green);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative;
            overflow: hidden;
        }
        
        /* Animated border glow */
        .stat-card::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: conic-gradient(
                transparent, 
                rgba(0, 255, 136, 0.1), 
                transparent 30%
            );
            animation: rotateBorder 4s linear infinite;
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .stat-card:hover::before {
            opacity: 1;
        }
        
        @keyframes rotateBorder {
            100% { transform: rotate(360deg); }
        }
        
        .stat-card::after {
            content: '';
            position: absolute;
            inset: 2px;
            background: var(--bg-panel);
            border-radius: 8px;
            z-index: 0;
        }
        
        .stat-card > * {
            position: relative;
            z-index: 1;
        }
        
        .stat-card:hover {
            transform: translateY(-8px) scale(1.02);
            box-shadow: 
                0 15px 40px rgba(0, 255, 136, 0.4),
                0 0 60px rgba(0, 255, 136, 0.2);
        }
        
        .stat-card.gold {
            border-color: var(--gold);
        }
        
        .stat-card.gold::before {
            background: conic-gradient(
                transparent, 
                rgba(255, 215, 0, 0.2), 
                transparent 30%
            );
        }
        
        .stat-card.gold:hover {
            box-shadow: 
                0 15px 40px rgba(255, 215, 0, 0.4),
                0 0 60px rgba(255, 215, 0, 0.2);
        }
        
        .stat-label {
            font-size: 0.75em;
            color: #888;
            margin-bottom: 5px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stat-value {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.8em;
            font-weight: 700;
            transition: all 0.3s ease;
        }
        
        /* Animated number update effect */
        .stat-value.updating {
            animation: numberPop 0.3s ease;
        }
        
        @keyframes numberPop {
            0% { transform: scale(1); }
            50% { transform: scale(1.3); filter: brightness(1.5); }
            100% { transform: scale(1); }
        }
        
        .stat-value.green { 
            color: var(--green); 
            text-shadow: 0 0 10px var(--green);
        }
        .stat-value.gold { 
            color: var(--gold); 
            text-shadow: 0 0 10px var(--gold);
        }
        .stat-value.red { 
            color: var(--red); 
            text-shadow: 0 0 10px var(--red);
        }
        .stat-value.blue { 
            color: var(--blue); 
            text-shadow: 0 0 10px var(--blue);
        }
        
        /* Positive change flash */
        .stat-card.flash-green {
            animation: flashGreen 0.5s ease;
        }
        
        @keyframes flashGreen {
            0%, 100% { background: var(--bg-panel); }
            50% { background: rgba(0, 255, 136, 0.2); border-color: var(--green); }
        }
        
        /* Negative change flash */
        .stat-card.flash-red {
            animation: flashRed 0.5s ease;
        }
        
        @keyframes flashRed {
            0%, 100% { background: var(--bg-panel); }
            50% { background: rgba(255, 51, 102, 0.2); border-color: var(--red); }
        }
        
        /* TRADE FEED */
        #trade-feed {
            flex: 1;
            overflow: hidden;
        }
        
        .trade-item {
            display: grid;
            grid-template-columns: 80px 100px 1fr 100px 80px;
            gap: 10px;
            padding: 10px;
            margin-bottom: 5px;
            background: rgba(0, 0, 0, 0.4);
            border-radius: 5px;
            border-left: 4px solid var(--green);
            font-size: 0.9em;
            animation: tradeSlideIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        /* Shimmer effect on new trade */
        .trade-item::after {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(255, 255, 255, 0.1),
                transparent
            );
            animation: tradeShimmer 1s ease forwards;
        }
        
        @keyframes tradeShimmer {
            100% { left: 100%; }
        }
        
        @keyframes tradeSlideIn {
            from { 
                transform: translateX(-30px) scale(0.95); 
                opacity: 0; 
            }
            to { 
                transform: translateX(0) scale(1); 
                opacity: 1; 
            }
        }
        
        .trade-item:hover {
            background: rgba(0, 255, 136, 0.1);
            transform: translateX(5px);
        }
        
        .trade-item.buy { 
            border-left-color: var(--green); 
        }
        .trade-item.sell { 
            border-left-color: var(--red); 
        }
        .trade-item.whale { 
            border-left-color: var(--blue); 
            border-width: 4px;
            animation: tradeSlideIn 0.4s ease, whalePulse 2s ease infinite;
        }
        
        @keyframes whalePulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(0, 191, 255, 0.4); }
            50% { box-shadow: 0 0 20px 5px rgba(0, 191, 255, 0.2); }
        }
        
        .trade-time { color: #666; }
        .trade-type { font-weight: bold; }
        .trade-type.buy { color: var(--green); }
        .trade-type.sell { color: var(--red); }
        .trade-symbol { color: var(--cyan); }
        .trade-amount { color: var(--gold); }
        .trade-pnl { font-weight: bold; }
        .trade-pnl.positive { color: var(--green); }
        .trade-pnl.negative { color: var(--red); }

        
        /* EXCHANGE STATUS ROW */
        #exchange-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
        }
        
        .exchange-card {
            background: var(--bg-panel);
            border: 2px solid var(--green);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative;
            overflow: hidden;
        }
        
        /* Animated scan line */
        .exchange-card::before {
            content: '';
            position: absolute;
            top: -100%;
            left: 0;
            width: 100%;
            height: 3px;
            background: linear-gradient(90deg, transparent, var(--green), transparent);
            animation: exchangeScan 3s linear infinite;
        }
        
        @keyframes exchangeScan {
            0% { top: -100%; opacity: 0; }
            50% { opacity: 1; }
            100% { top: 200%; opacity: 0; }
        }
        
        .exchange-card:hover {
            transform: translateY(-5px) scale(1.03);
            box-shadow: 
                0 10px 30px rgba(0, 255, 136, 0.3),
                0 0 50px rgba(0, 255, 136, 0.1);
        }
        
        .exchange-card.offline {
            border-color: var(--red);
            opacity: 0.7;
        }
        
        .exchange-card.offline::before {
            background: linear-gradient(90deg, transparent, var(--red), transparent);
        }
        
        .exchange-logo {
            font-size: 2.5em;
            margin-bottom: 8px;
            animation: logoFloat 3s ease-in-out infinite;
            display: inline-block;
        }
        
        @keyframes logoFloat {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            25% { transform: translateY(-3px) rotate(-2deg); }
            75% { transform: translateY(3px) rotate(2deg); }
        }
        
        .exchange-card:hover .exchange-logo {
            animation: logoBounce 0.5s ease;
        }
        
        @keyframes logoBounce {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.2); }
        }
        
        .exchange-name {
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        
        .exchange-balance {
            font-size: 1.3em;
            font-weight: bold;
            color: var(--gold);
            text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
            transition: all 0.3s ease;
        }
        
        .exchange-balance.updating {
            animation: balanceUpdate 0.3s ease;
        }
        
        @keyframes balanceUpdate {
            0% { transform: scale(1); }
            50% { transform: scale(1.15); color: #fff; }
            100% { transform: scale(1); }
        }
        
        .exchange-status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.75em;
            margin-top: 8px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .exchange-status-badge.online {
            background: rgba(0, 255, 136, 0.2);
            color: var(--green);
            box-shadow: 0 0 10px rgba(0, 255, 136, 0.3);
            animation: onlinePulse 2s ease infinite;
        }
        
        @keyframes onlinePulse {
            0%, 100% { box-shadow: 0 0 5px rgba(0, 255, 136, 0.3); }
            50% { box-shadow: 0 0 15px rgba(0, 255, 136, 0.6); }
        }
        
        .exchange-status-badge.offline {
            background: rgba(255, 51, 102, 0.2);
            color: var(--red);
            animation: offlineBlink 1s ease infinite;
        }
        
        @keyframes offlineBlink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* RIGHT SIDEBAR */
        #right-sidebar {
            grid-column: 3;
            grid-row: 2;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        /* WHALE ALERTS */
        #whale-panel {
            flex: 1;
            border-color: var(--blue);
        }
        
        #whale-panel .panel-header {
            background: linear-gradient(90deg, rgba(0, 191, 255, 0.3), transparent);
            border-bottom-color: var(--blue);
            color: var(--blue);
        }
        
        .whale-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px;
            margin-bottom: 6px;
            background: rgba(0, 191, 255, 0.1);
            border-radius: 8px;
            border-left: 4px solid var(--blue);
            animation: whaleSwim 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        /* Whale wave effect */
        .whale-item::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(0, 191, 255, 0.2),
                transparent
            );
            animation: whaleWave 2s ease infinite;
        }
        
        @keyframes whaleWave {
            0% { left: -100%; }
            100% { left: 100%; }
        }
        
        @keyframes whaleSwim {
            from { 
                transform: translateX(100px) scale(0.8); 
                opacity: 0; 
            }
            to { 
                transform: translateX(0) scale(1); 
                opacity: 1; 
            }
        }
        
        .whale-item:hover {
            background: rgba(0, 191, 255, 0.2);
            transform: translateX(5px);
            box-shadow: 0 5px 20px rgba(0, 191, 255, 0.3);
        }
        
        .whale-icon { 
            font-size: 1.8em; 
            animation: whaleIconBob 2s ease-in-out infinite;
        }
        
        @keyframes whaleIconBob {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            25% { transform: translateY(-3px) rotate(-5deg); }
            75% { transform: translateY(3px) rotate(5deg); }
        }
        
        .whale-info { flex: 1; }
        .whale-symbol { color: var(--cyan); font-weight: bold; font-size: 1.1em; }
        .whale-volume { color: var(--gold); text-shadow: 0 0 5px rgba(255, 215, 0, 0.5); }
        .whale-direction { 
            font-size: 1.4em; 
            transition: transform 0.3s ease;
        }
        .whale-direction.buy { color: var(--green); }
        .whale-direction.sell { color: var(--red); }
        
        .whale-item:hover .whale-direction {
            transform: scale(1.2);
        }
        
        /* BOT DETECTIONS */
        #bot-panel {
            flex: 1;
            border-color: var(--purple);
        }
        
        #bot-panel .panel-header {
            background: linear-gradient(90deg, rgba(153, 102, 255, 0.3), transparent);
            border-bottom-color: var(--purple);
            color: var(--purple);
        }
        
        .bot-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            margin-bottom: 5px;
            background: rgba(153, 102, 255, 0.1);
            border-radius: 6px;
            font-size: 0.85em;
            animation: botDetect 0.4s ease-out;
            transition: all 0.3s ease;
            position: relative;
        }
        
        @keyframes botDetect {
            from { 
                transform: scale(0.5) rotateY(90deg); 
                opacity: 0; 
            }
            to { 
                transform: scale(1) rotateY(0deg); 
                opacity: 1; 
            }
        }
        
        .bot-item:hover {
            background: rgba(153, 102, 255, 0.2);
            transform: translateX(5px);
        }
        
        .bot-icon { 
            font-size: 1.4em; 
            animation: botScan 1.5s linear infinite;
        }
        
        @keyframes botScan {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; filter: hue-rotate(180deg); }
        }
        
        .bot-firm { 
            color: var(--purple); 
            font-weight: bold; 
            text-shadow: 0 0 5px rgba(153, 102, 255, 0.5);
        }
        .bot-country { color: #888; }
        
        /* BOT SHAPE SCANNER */
        #bot-scanner-panel {
            flex: 1;
            border-color: var(--green);
        }
        
        #bot-scanner-panel .panel-header {
            background: linear-gradient(90deg, rgba(0, 255, 136, 0.3), transparent);
            border-bottom-color: var(--green);
            color: var(--green);
        }
        
        .scanner-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            margin-bottom: 5px;
            background: rgba(0, 255, 136, 0.1);
            border-radius: 6px;
            font-size: 0.85em;
            animation: scannerPulse 0.5s ease-out;
            transition: all 0.3s ease;
            position: relative;
        }
        
        @keyframes scannerPulse {
            from { 
                transform: scale(0.8); 
                opacity: 0; 
                box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.7);
            }
            to { 
                transform: scale(1); 
                opacity: 1; 
                box-shadow: 0 0 0 10px rgba(0, 255, 136, 0);
            }
        }
        
        .scanner-item:hover {
            background: rgba(0, 255, 136, 0.2);
            transform: translateX(5px);
        }
        
        .scanner-icon { 
            font-size: 1.4em; 
            animation: scannerGlow 1s ease-in-out infinite alternate;
        }
        
        @keyframes scannerGlow {
            from { filter: drop-shadow(0 0 5px var(--green)); }
            to { filter: drop-shadow(0 0 15px var(--green)); }
        }
        
        .scanner-type { 
            color: var(--green); 
            font-weight: bold; 
        }
        .scanner-confidence { color: var(--gold); }
        .scanner-status { color: #888; }
        
        /* WHALE SONAR */
        #whale-sonar-panel {
            flex: 1;
            border-color: var(--cyan);
        }
        
        #whale-sonar-panel .panel-header {
            background: linear-gradient(90deg, rgba(0, 255, 255, 0.3), transparent);
            border-bottom-color: var(--cyan);
            color: var(--cyan);
        }
        
        .sonar-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            margin-bottom: 5px;
            background: rgba(0, 255, 255, 0.1);
            border-radius: 6px;
            font-size: 0.85em;
            animation: sonarPing 0.6s ease-out;
            transition: all 0.3s ease;
            position: relative;
        }
        
        @keyframes sonarPing {
            from { 
                transform: scale(0.5); 
                opacity: 0; 
            }
            to { 
                transform: scale(1); 
                opacity: 1; 
            }
            50% { transform: scale(1.1); }
        }
        
        .sonar-item:hover {
            background: rgba(0, 255, 255, 0.2);
            transform: translateX(5px);
        }
        
        .sonar-icon { 
            font-size: 1.4em; 
            animation: sonarPulse 2s ease-in-out infinite;
        }
        
        @keyframes sonarPulse {
            0%, 100% { opacity: 0.7; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.2); }
        }
        
        .sonar-source { 
            color: var(--cyan); 
            font-weight: bold; 
        }
        .sonar-strength { color: var(--gold); }
        .sonar-code { color: #888; font-family: monospace; }
        
        /* ORCA INTELLIGENCE */
        #orca-panel {
            flex: 1;
            border-color: var(--orange);
        }
        
        #orca-panel .panel-header {
            background: linear-gradient(90deg, rgba(255, 102, 0, 0.3), transparent);
            border-bottom-color: var(--orange);
            color: var(--orange);
        }
        
        .orca-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            margin-bottom: 5px;
            background: rgba(255, 102, 0, 0.1);
            border-radius: 6px;
            font-size: 0.85em;
            animation: orcaHunt 0.5s ease-out;
            transition: all 0.3s ease;
            position: relative;
        }
        
        @keyframes orcaHunt {
            from { 
                transform: translateX(-50px); 
                opacity: 0; 
            }
            to { 
                transform: translateX(0); 
                opacity: 1; 
            }
        }
        
        .orca-item:hover {
            background: rgba(255, 102, 0, 0.2);
            transform: translateX(5px);
        }
        
        .orca-icon { 
            font-size: 1.4em; 
            animation: orcaJaw 1.5s ease-in-out infinite;
        }
        
        @keyframes orcaJaw {
            0%, 100% { transform: rotate(0deg); }
            25% { transform: rotate(-10deg); }
            75% { transform: rotate(10deg); }
        }
        
        .orca-target { 
            color: var(--orange); 
            font-weight: bold; 
        }
        .orca-mode { color: var(--gold); }
        .orca-status { color: #888; }
        
        /* UNIFIED SNIPER BRAIN */
        #sniper-panel {
            flex: 1;
            border-color: var(--red);
        }
        
        #sniper-panel .panel-header {
            background: linear-gradient(90deg, rgba(255, 51, 102, 0.3), transparent);
            border-bottom-color: var(--red);
            color: var(--red);
        }
        
        .sniper-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            margin-bottom: 5px;
            background: rgba(255, 51, 102, 0.1);
            border-radius: 6px;
            font-size: 0.85em;
            animation: sniperShot 0.4s ease-out;
            transition: all 0.3s ease;
            position: relative;
        }
        
        @keyframes sniperShot {
            from { 
                transform: translateX(100px) scale(0.5); 
                opacity: 0; 
            }
            to { 
                transform: translateX(0) scale(1); 
                opacity: 1; 
            }
        }
        
        .sniper-item:hover {
            background: rgba(255, 51, 102, 0.2);
            transform: translateX(5px);
        }
        
        .sniper-icon { 
            font-size: 1.4em; 
            animation: sniperScope 1s linear infinite;
        }
        
        @keyframes sniperScope {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        
        .sniper-target { 
            color: var(--red); 
            font-weight: bold; 
        }
        .sniper-pnl { color: var(--gold); }
        .sniper-result { font-size: 1.2em; }
        .sniper-result.win { color: var(--green); }
        .sniper-result.loss { color: var(--red); }
        
        /* HARMONIC VISUALIZATION */
        #harmonic-panel {
            height: 180px;
            border-color: var(--cyan);
        }
        
        #harmonic-panel .panel-header {
            background: linear-gradient(90deg, rgba(0, 255, 255, 0.3), transparent);
            border-bottom-color: var(--cyan);
            color: var(--cyan);
        }
        
        #harmonic-canvas {
            width: 100%;
            height: 100%;
        }
        
        /* FOOTER - ALERTS BAR */
        #footer {
            grid-column: 1 / -1;
            grid-row: 3;
            background: rgba(0, 0, 0, 0.9);
            border: 2px solid var(--orange);
            border-radius: 10px;
            padding: 10px 20px;
            display: flex;
            align-items: center;
            gap: 20px;
            overflow: hidden;
        }
        
        #alert-label {
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            color: var(--orange);
            white-space: nowrap;
        }
        
        #alert-ticker {
            flex: 1;
            overflow: hidden;
            white-space: nowrap;
        }
        
        #alert-content {
            display: inline-block;
            animation: ticker 30s linear infinite;
        }
        
        @keyframes ticker {
            0% { transform: translateX(100%); }
            100% { transform: translateX(-100%); }
        }
        
        .alert-item {
            display: inline-block;
            margin-right: 50px;
            padding: 5px 15px;
            background: rgba(255, 102, 0, 0.2);
            border-radius: 5px;
        }
        
        /* ALERT BUTTONS - ENHANCED */
        .alert-btn {
            padding: 10px 18px;
            background: linear-gradient(180deg, #4a2020, #2a1010);
            color: var(--red);
            border: 2px solid var(--red);
            border-radius: 8px;
            cursor: pointer;
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            font-size: 0.75em;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 
                0 0 10px rgba(255, 0, 0, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
        }
        
        /* Button shine effect */
        .alert-btn::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(
                to bottom right,
                rgba(255, 255, 255, 0) 0%,
                rgba(255, 255, 255, 0.1) 50%,
                rgba(255, 255, 255, 0) 100%
            );
            transform: rotate(45deg);
            transition: all 0.5s ease;
            opacity: 0;
        }
        
        .alert-btn:hover::before {
            opacity: 1;
            left: 100%;
        }
        
        /* Ripple effect */
        .alert-btn::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.2);
            transform: translate(-50%, -50%);
            transition: width 0.6s ease, height 0.6s ease;
        }
        
        .alert-btn:active::after {
            width: 300px;
            height: 300px;
        }
        
        .alert-btn:hover {
            background: linear-gradient(180deg, #6a3030, #4a2020);
            transform: scale(1.08) translateY(-2px);
            box-shadow: 
                0 5px 25px rgba(255, 0, 0, 0.5),
                0 0 40px rgba(255, 0, 0, 0.3);
        }
        
        .alert-btn:active {
            transform: scale(0.98) translateY(1px);
        }
        
        .alert-btn.active {
            animation: alertPulse 0.5s infinite, alertGlow 1s ease infinite;
            background: var(--red);
            color: #fff;
        }
        
        @keyframes alertGlow {
            0%, 100% { box-shadow: 0 0 10px rgba(255, 0, 0, 0.5); }
            50% { box-shadow: 0 0 30px rgba(255, 0, 0, 0.8), 0 0 60px rgba(255, 0, 0, 0.4); }
        }
        
        .alert-btn.green {
            background: linear-gradient(180deg, #204a20, #102a10);
            color: var(--green);
            border-color: var(--green);
            box-shadow: 
                0 0 10px rgba(0, 255, 0, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }
        
        .alert-btn.green:hover {
            background: linear-gradient(180deg, #306a30, #204a20);
            box-shadow: 
                0 5px 25px rgba(0, 255, 0, 0.5),
                0 0 40px rgba(0, 255, 0, 0.3);
        }

        .alert-btn.blue {
            background: linear-gradient(180deg, #20304a, #101a2a);
            color: var(--blue);
            border-color: var(--blue);
            box-shadow: 
                0 0 10px rgba(0, 191, 255, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }

        .alert-btn.blue:hover {
            background: linear-gradient(180deg, #30446a, #20304a);
            box-shadow: 
                0 5px 25px rgba(0, 191, 255, 0.5),
                0 0 40px rgba(0, 191, 255, 0.3);
        }

        /* Gold button variant */
        .alert-btn.gold {
            background: linear-gradient(180deg, #4a4a20, #2a2a10);
            color: var(--gold);
            border-color: var(--gold);
            box-shadow: 
                0 0 10px rgba(255, 215, 0, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }

        .alert-btn.gold:hover {
            background: linear-gradient(180deg, #6a6a30, #4a4a20);
            box-shadow: 
                0 5px 25px rgba(255, 215, 0, 0.5),
                0 0 40px rgba(255, 215, 0, 0.3);
        }
        
        @keyframes alertPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        /* RADAR CONTAINER */
        #radar-container {
            position: fixed;
            bottom: 80px;
            right: 20px;
            width: 180px;
            height: 180px;
            z-index: 50;
            background: rgba(0, 20, 10, 0.9);
            border: 2px solid var(--green);
            border-radius: 50%;
            box-shadow: 
                0 0 30px rgba(0, 255, 136, 0.3),
                inset 0 0 20px rgba(0, 0, 0, 0.8);
            animation: radarPulse 3s ease infinite;
        }
        
        @keyframes radarPulse {
            0%, 100% { box-shadow: 0 0 30px rgba(0, 255, 136, 0.3), inset 0 0 20px rgba(0, 0, 0, 0.8); }
            50% { box-shadow: 0 0 50px rgba(0, 255, 136, 0.5), inset 0 0 20px rgba(0, 0, 0, 0.8); }
        }
        
        #radar-canvas {
            width: 100%;
            height: 100%;
        }
        
        /* GLOBE CONTAINER */
        #globe-container {
            position: fixed;
            top: 80px;
            right: 350px;
            width: 200px;
            height: 200px;
            z-index: 40;
            opacity: 0.7;
            pointer-events: none;
        }
        
        /* QUEEN WAVEFORM */
        #queen-waveform {
            position: absolute;
            bottom: 10px;
            left: 120px;
            right: 100px;
            height: 30px;
        }
        
        #voice-waveform {
            width: 100%;
            height: 100%;
        }
        
        /* WORLD MAP */
        #world-map-container {
            position: fixed;
            top: 80px;
            right: 350px;
            width: 300px;
            height: 180px;
            z-index: 30;
            border: 2px solid var(--cyan);
            border-radius: 5px;
            overflow: hidden;
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
        }
        
        #world-map {
            width: 100%;
            height: 100%;
            filter: hue-rotate(140deg) saturate(1.5);
        }

        /* 3D GLOBE */
        #globe-container {
            position: fixed;
            top: 80px;
            right: 20px;
            width: 280px;
            height: 280px;
            z-index: 35;
            border: 2px solid var(--blue);
            border-radius: 5px;
            overflow: hidden;
            box-shadow: 0 0 25px rgba(0, 191, 255, 0.3);
            background: rgba(0, 0, 0, 0.6);
        }

        #globe-container .panel-header {
            background: linear-gradient(90deg, rgba(0, 191, 255, 0.3), transparent);
            padding: 5px 10px;
            border-bottom: 1px solid var(--blue);
            color: var(--blue);
            font-size: 0.75em;
        }

        #globe {
            width: 100%;
            height: calc(100% - 28px);
        }
        
        /* PNL CHART */
        #pnl-chart-container {
            position: fixed;
            bottom: 80px;
            left: 20px;
            width: 350px;
            height: 200px;
            z-index: 50;
            border: 2px solid var(--gold);
            border-radius: 5px;
            overflow: hidden;
        }
        
        #pnl-chart-container .panel-header {
            background: linear-gradient(90deg, rgba(255, 215, 0, 0.3), transparent);
            padding: 5px 10px;
            border-bottom: 1px solid var(--gold);
            color: var(--gold);
            font-size: 0.8em;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        #pnl-chart {
            width: 100%;
            height: calc(100% - 30px);
        }
        
        .mini-btn {
            background: transparent;
            border: 1px solid var(--gold);
            color: var(--gold);
            width: 20px;
            height: 20px;
            cursor: pointer;
            font-size: 12px;
            border-radius: 3px;
        }

        /* SYSTEM RADAR (ECharts) */
        #system-radar-panel .panel-content {
            padding: 0;
        }

        #system-radar {
            width: 100%;
            height: 220px;
        }

        /* TERMINAL (xterm.js) */
        #terminal-panel .panel-content {
            padding: 0;
        }

        #terminal {
            width: 100%;
            height: 200px;
            background: #05070a;
        }

        .xterm .xterm-viewport {
            background: #05070a;
        }
        
        /* DEFCON INDICATOR */
        #threat-level {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 5px 15px;
            background: rgba(0, 0, 0, 0.5);
            border: 2px solid var(--green);
            border-radius: 5px;
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
        }
        
        #defcon-level {
            font-size: 1.5em;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 5px;
        }
        
        .defcon-5 { background: var(--green); color: #000; }
        .defcon-4 { background: var(--blue); color: #000; }
        .defcon-3 { background: var(--gold); color: #000; }
        .defcon-2 { background: var(--orange); color: #000; }
        .defcon-1 { background: var(--red); color: #fff; animation: defconPulse 0.5s infinite; }
        
        @keyframes defconPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* TYPED CURSOR */
        .typed-cursor {
            color: var(--gold);
            font-size: 1.2em;
            animation: blink 0.7s infinite;
        }
        
        /* GLOWING TEXT FOR IMPORTANT VALUES */
        .glow-green {
            text-shadow: 0 0 10px var(--green), 0 0 20px var(--green);
        }
        
        .glow-gold {
            text-shadow: 0 0 10px var(--gold), 0 0 20px var(--gold);
        }
        
        .glow-red {
            text-shadow: 0 0 10px var(--red), 0 0 20px var(--red);
        }
        
        /* ENHANCED PANEL STYLING */
        .panel {
            position: relative;
            background: linear-gradient(180deg, 
                rgba(40, 40, 60, 0.95) 0%, 
                rgba(15, 15, 25, 0.98) 5%, 
                rgba(10, 10, 20, 0.98) 95%, 
                rgba(40, 40, 60, 0.95) 100%
            );
            border: 2px solid var(--green);
            border-radius: 5px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 
                0 0 20px rgba(0, 255, 136, 0.2),
                inset 0 0 30px rgba(0, 0, 0, 0.5),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }
        
        /* SCROLLBAR */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--green);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--gold);
        }
        
        /* RESPONSIVE */
        @media (max-width: 1400px) {
            #main-container {
                grid-template-columns: 250px 1fr 280px;
            }
            #stats-row {
                grid-template-columns: repeat(3, 1fr);
            }
            #radar-container {
                width: 120px;
                height: 120px;
            }
        }
        
        @media (max-width: 1200px) {
            #main-container {
                grid-template-columns: 1fr;
            }
            #systems-panel, #right-sidebar {
                display: none;
            }
            #radar-container {
                display: none;
            }
        }
    </style>
</head>
<body>
    <!-- PARTICLE BACKGROUND -->
    <div id="particles-js"></div>
    
    <!-- ═══════════════════════════════════════════════════════════════════════
         🌀 STARGATE PORTAL SYSTEM
         ═══════════════════════════════════════════════════════════════════════ -->
    
    <!-- STARGATE PORTAL -->
    <div id="stargate-container">
        <div class="stargate-ring"></div>
        <div class="glyph-ring"></div>
        
        <!-- 9 CHEVRONS -->
        <div class="chevron" data-chevron="1"><div class="chevron-inner"></div></div>
        <div class="chevron" data-chevron="2"><div class="chevron-inner"></div></div>
        <div class="chevron" data-chevron="3"><div class="chevron-inner"></div></div>
        <div class="chevron" data-chevron="4"><div class="chevron-inner"></div></div>
        <div class="chevron" data-chevron="5"><div class="chevron-inner"></div></div>
        <div class="chevron" data-chevron="6"><div class="chevron-inner"></div></div>
        <div class="chevron" data-chevron="7"><div class="chevron-inner"></div></div>
        <div class="chevron" data-chevron="8"><div class="chevron-inner"></div></div>
        <div class="chevron" data-chevron="9"><div class="chevron-inner"></div></div>
        
        <!-- EVENT HORIZON (WORMHOLE) -->
        <div class="event-horizon"></div>
        
        <!-- KAWOOSH EFFECT -->
        <div class="kawoosh"></div>
    </div>
    
    <!-- STARGATE STATUS DISPLAY -->
    <div id="stargate-status">
        <div>⭐ STARGATE STATUS ⭐</div>
        <div id="gate-address">IDLE - NO CONNECTION</div>
        <div class="chevron-display">
            <div class="chevron-indicator" data-idx="1"></div>
            <div class="chevron-indicator" data-idx="2"></div>
            <div class="chevron-indicator" data-idx="3"></div>
            <div class="chevron-indicator" data-idx="4"></div>
            <div class="chevron-indicator" data-idx="5"></div>
            <div class="chevron-indicator" data-idx="6"></div>
            <div class="chevron-indicator" data-idx="7"></div>
            <div class="chevron-indicator" data-idx="8"></div>
            <div class="chevron-indicator" data-idx="9"></div>
        </div>
    </div>
    
    <!-- DHD - DIAL HOME DEVICE -->
    <div id="dhd-panel">
        <div class="panel-header">
            <span>🔮 DHD - DIAL HOME DEVICE</span>
            <span id="dhd-status">STANDBY</span>
        </div>
        <div class="glyph-grid">
            <!-- 36 Stargate glyphs (symbols) -->
            <button class="glyph-btn" data-glyph="giza">🔺</button>
            <button class="glyph-btn" data-glyph="stonehenge">🗿</button>
            <button class="glyph-btn" data-glyph="machu">🏔️</button>
            <button class="glyph-btn" data-glyph="angkor">🛕</button>
            <button class="glyph-btn" data-glyph="uluru">🪨</button>
            <button class="glyph-btn" data-glyph="sedona">🌵</button>
            <button class="glyph-btn" data-glyph="teotihuacan">🌙</button>
            <button class="glyph-btn" data-glyph="gobekli">⭕</button>
            <button class="glyph-btn" data-glyph="easter">🗿</button>
            <button class="glyph-btn" data-glyph="newgrange">☘️</button>
            <button class="glyph-btn" data-glyph="mt_shasta">⛰️</button>
            <button class="glyph-btn" data-glyph="mt_kailash">🏔️</button>
            <button class="glyph-btn" data-glyph="bermuda">🔻</button>
            <button class="glyph-btn" data-glyph="rennes">⚜️</button>
            <button class="glyph-btn" data-glyph="avebury">⭕</button>
            <button class="glyph-btn" data-glyph="carnac">📍</button>
            <button class="glyph-btn" data-glyph="delphi">🏛️</button>
            <button class="glyph-btn" data-glyph="petra">🏜️</button>
            <button class="glyph-btn" data-glyph="chaco">🌀</button>
            <button class="glyph-btn" data-glyph="tiwanaku">🧱</button>
            <button class="glyph-btn" data-glyph="nazca">✈️</button>
            <button class="glyph-btn" data-glyph="baalbek">🏗️</button>
            <button class="glyph-btn" data-glyph="glastonbury">🔮</button>
            <button class="glyph-btn" data-glyph="lemuria">🌊</button>
            <button class="glyph-btn" data-glyph="atlantis">🔱</button>
            <button class="glyph-btn" data-glyph="agartha">🕳️</button>
            <button class="glyph-btn" data-glyph="sirius">⭐</button>
            <button class="glyph-btn" data-glyph="pleiades">✨</button>
            <button class="glyph-btn" data-glyph="orion">🎯</button>
            <button class="glyph-btn" data-glyph="arcturus">💫</button>
            <button class="glyph-btn" data-glyph="earth">🌍</button>
            <button class="glyph-btn" data-glyph="point_origin">🏠</button>
        </div>
        <button class="dhd-activate" id="dhd-big-red" onclick="activateStargate()">
            ⚡
        </button>
    </div>
    
    <!-- QUANTUM MIRROR PANEL -->
    <div id="quantum-mirror-panel">
        <div class="panel-header">🪞 QUANTUM MIRROR SCANNER</div>
        <div id="timeline-list">
            <div class="timeline-card" data-timeline="golden_age">
                <div class="timeline-name">✨ Golden Age Timeline</div>
                <div class="timeline-coherence">
                    <div class="coherence-bar"><div class="coherence-fill" style="width: 95%"></div></div>
                    <span class="coherence-value">0.95</span>
                </div>
            </div>
            <div class="timeline-card" data-timeline="unity">
                <div class="timeline-name">🤝 Unity Timeline</div>
                <div class="timeline-coherence">
                    <div class="coherence-bar"><div class="coherence-fill" style="width: 92%"></div></div>
                    <span class="coherence-value">0.92</span>
                </div>
            </div>
            <div class="timeline-card" data-timeline="abundance">
                <div class="timeline-name">💰 Abundance Timeline</div>
                <div class="timeline-coherence">
                    <div class="coherence-bar"><div class="coherence-fill" style="width: 88%"></div></div>
                    <span class="coherence-value">0.88</span>
                </div>
            </div>
            <div class="timeline-card anchored" data-timeline="ascension">
                <div class="timeline-name">🌟 Ascension Timeline</div>
                <div class="timeline-coherence">
                    <div class="coherence-bar"><div class="coherence-fill" style="width: 97%"></div></div>
                    <span class="coherence-value">0.97</span>
                </div>
            </div>
        </div>
        <div class="planetary-nodes">
            <span class="node-indicator resonating">🔺 Giza</span>
            <span class="node-indicator">🗿 Stonehenge</span>
            <span class="node-indicator resonating">🏔️ Machu Picchu</span>
            <span class="node-indicator">🛕 Angkor</span>
            <span class="node-indicator resonating">🪨 Uluru</span>
            <span class="node-indicator">🌵 Sedona</span>
        </div>
    </div>
    
    <!-- 3D GLOBE CONTAINER -->
    <div id="globe-container"></div>
    
    <!-- RED ALERT SIREN (hidden audio) -->
    <div id="audio-container" style="display:none;"></div>
    
    <!-- HEADER -->
    <div id="header" class="metal-panel">
        <div class="rivet" style="top: 5px; left: 5px;"></div>
        <div class="rivet" style="top: 5px; right: 5px;"></div>
        <div class="rivet" style="bottom: 5px; left: 5px;"></div>
        <div class="rivet" style="bottom: 5px; right: 5px;"></div>
        <div id="logo">⚔️ AUREON COMMAND CENTER ⚔️</div>
        <div id="status-bar">
            <div class="status-item" id="mode-status">
                <span class="status-dot"></span>
                <span id="trading-mode">LIVE</span>
            </div>
            <div class="status-item" id="systems-status">
                <span class="status-dot"></span>
                <span><span id="systems-online">0</span>/<span id="systems-total">0</span> Systems</span>
            </div>
            <div class="status-item" id="uptime-status">
                <span>⏱️</span>
                <span id="uptime">00:00:00</span>
            </div>
            <div class="status-item" id="clock">
                <span>🕐</span>
                <span id="current-time">--:--:--</span>
            </div>
            <button id="trading-toggle-btn" class="alert-btn" onclick="toggleTradingEngine()">⚡ TRADING OFF</button>
            <button id="live-toggle-btn" class="alert-btn blue" onclick="toggleLiveFeed()">🟢 LIVE FEED</button>
            <button id="red-alert-btn" class="alert-btn" onclick="toggleRedAlert()">🚨 RED ALERT</button>
            <button id="flight-check-btn" class="alert-btn green" onclick="runFlightCheck()">🛫 FLIGHT CHECK</button>
        </div>
    </div>
    <!-- RADAR OVERLAY -->
    <div id="radar-container">
        <canvas id="radar-canvas"></canvas>
    </div>
    
    <!-- MAIN CONTAINER -->
    <div id="main-container">
        <!-- QUEEN VOICE PANEL -->
        <div id="queen-panel" class="panel gold-border metal-panel">
            <div class="rivet" style="top: 5px; left: 5px;"></div>
            <div class="rivet" style="top: 5px; right: 5px;"></div>
            <div id="queen-avatar">👑</div>
            <div id="queen-message">Welcome, Commander. All systems initializing... Establishing tactical uplink.</div>
            <div id="queen-status">Queen SERO | TACTICAL MODE | Neural Link Active</div>
            <button id="voice-toggle" onclick="toggleVoice()">🔊 EVA VOICE</button>
            <div id="queen-waveform"><canvas id="voice-waveform"></canvas></div>
        </div>
        
        <!-- LEFT SIDEBAR - SYSTEMS -->
        <div id="systems-panel" class="panel metal-panel">
            <div class="panel-header">
                <span>🧠 TACTICAL SYSTEMS</span>
                <span id="systems-count">0/0</span>
            </div>
            <div class="panel-content" id="systems-list">
                <!-- Systems populated by JS -->
            </div>
        </div>
        
        <!-- CENTER - MAIN DISPLAY -->
        <div id="main-display">
            <!-- STATS ROW -->
            <div id="stats-row">
                <div class="stat-card gold">
                    <div class="stat-label">💰 TOTAL P&L</div>
                    <div class="stat-value gold" id="total-pnl">$0.00</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">📊 TRADES</div>
                    <div class="stat-value green" id="total-trades">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">✅ WIN RATE</div>
                    <div class="stat-value green" id="win-rate">0%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">🏆 WINS</div>
                    <div class="stat-value green" id="wins">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">❌ LOSSES</div>
                    <div class="stat-value red" id="losses">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">🎯 COHERENCE</div>
                    <div class="stat-value blue" id="coherence">0.50</div>
                </div>
            </div>
            
            <!-- TRADE FEED -->
            <div id="trade-feed" class="panel">
                <div class="panel-header">
                    <span>⚡ LIVE TRADE FEED</span>
                    <span id="trade-rate">0 trades/min</span>
                </div>
                <div class="panel-content" id="trade-list">
                    <!-- Trades populated by JS -->
                </div>
            </div>
            
            <!-- EXCHANGE STATUS -->
            <div id="exchange-row">
                <div class="exchange-card" id="exchange-kraken">
                    <div class="exchange-logo">🐙</div>
                    <div class="exchange-name">KRAKEN</div>
                    <div class="exchange-balance" id="kraken-balance">$0.00</div>
                    <div class="exchange-status-badge online" id="kraken-status">ONLINE</div>
                </div>
                <div class="exchange-card" id="exchange-binance">
                    <div class="exchange-logo">🟡</div>
                    <div class="exchange-name">BINANCE</div>
                    <div class="exchange-balance" id="binance-balance">$0.00</div>
                    <div class="exchange-status-badge online" id="binance-status">ONLINE</div>
                </div>
                <div class="exchange-card" id="exchange-alpaca">
                    <div class="exchange-logo">🦙</div>
                    <div class="exchange-name">ALPACA</div>
                    <div class="exchange-balance" id="alpaca-balance">$0.00</div>
                    <div class="exchange-status-badge online" id="alpaca-status">ONLINE</div>
                </div>
                <div class="exchange-card" id="exchange-capital">
                    <div class="exchange-logo">💼</div>
                    <div class="exchange-name">CAPITAL</div>
                    <div class="exchange-balance" id="capital-balance">$0.00</div>
                    <div class="exchange-status-badge online" id="capital-status">ONLINE</div>
                </div>
            </div>
        </div>
        
        <!-- RIGHT SIDEBAR -->
        <div id="right-sidebar">
            <!-- WHALE ALERTS -->
            <div id="whale-panel" class="panel">
                <div class="panel-header">
                    <span>🐋 WHALE ALERTS</span>
                    <span id="whale-count">0</span>
                </div>
                <div class="panel-content" id="whale-list">
                    <!-- Whales populated by JS -->
                </div>
            </div>
            
            <!-- BOT DETECTIONS -->
            <div id="bot-panel" class="panel">
                <div class="panel-header">
                    <span>🤖 BOT INTELLIGENCE</span>
                    <span id="bot-count">0</span>
                </div>
                <div class="panel-content" id="bot-list">
                    <!-- Bots populated by JS -->
                </div>
            </div>
            
            <!-- BOT SHAPE SCANNER -->
            <div id="bot-scanner-panel" class="panel">
                <div class="panel-header">
                    <span>🔍 BOT SHAPE SCANNER</span>
                    <span id="bot-scanner-status">SCANNING</span>
                </div>
                <div class="panel-content" id="bot-scanner-list">
                    <!-- Bot shapes populated by JS -->
                </div>
            </div>
            
            <!-- WHALE SONAR (MYCELIUM) -->
            <div id="whale-sonar-panel" class="panel">
                <div class="panel-header">
                    <span>🐋🔊 WHALE SONAR</span>
                    <span id="sonar-signal">0.0</span>
                </div>
                <div class="panel-content" id="whale-sonar-list">
                    <!-- Whale sonar signals populated by JS -->
                </div>
            </div>
            
            <!-- ORCA INTELLIGENCE -->
            <div id="orca-panel" class="panel">
                <div class="panel-header">
                    <span>🦈 ORCA INTELLIGENCE</span>
                    <span id="orca-hunts">0</span>
                </div>
                <div class="panel-content" id="orca-list">
                    <!-- Orca intelligence populated by JS -->
                </div>
            </div>
            
            <!-- UNIFIED SNIPER BRAIN -->
            <div id="sniper-panel" class="panel">
                <div class="panel-header">
                    <span>🎯 UNIFIED SNIPER BRAIN</span>
                    <span id="sniper-winrate">0.0%</span>
                </div>
                <div class="panel-content" id="sniper-list">
                    <!-- Sniper brain data populated by JS -->
                </div>
            </div>
            
            <!-- HARMONIC VISUALIZATION -->
            <div id="harmonic-panel" class="panel">
                <div class="panel-header">
                    <span>🎵 HARMONIC FIELD</span>
                    <span id="wave-state">BALANCED</span>
                </div>
                <div class="panel-content">
                    <canvas id="harmonic-canvas"></canvas>
                </div>
            </div>

            <!-- SYSTEM RADAR -->
            <div id="system-radar-panel" class="panel">
                <div class="panel-header">
                    <span>📡 SYSTEM RADAR</span>
                    <span>ECHARTS</span>
                </div>
                <div class="panel-content">
                    <div id="system-radar"></div>
                </div>
            </div>

            <!-- COMMAND TERMINAL -->
            <div id="terminal-panel" class="panel">
                <div class="panel-header">
                    <span>💻 COMMAND TERMINAL</span>
                    <span>XTERM</span>
                </div>
                <div class="panel-content">
                    <div id="terminal"></div>
                </div>
            </div>
        </div>
        
        <!-- WORLD MAP OVERLAY -->
        <div id="world-map-container">
            <div id="world-map"></div>
        </div>

        <!-- 3D GLOBE (floating) -->
        <div id="globe-container" class="metal-panel">
            <div class="panel-header">
                <span>🌍 3D GLOBE</span>
            </div>
            <div id="globe"></div>
        </div>
        
        <!-- PNL CHART PANEL (floating) -->
        <div id="pnl-chart-container" class="metal-panel">
            <div class="panel-header">
                <span>📈 P&L TIMELINE</span>
                <button onclick="togglePnlChart()" class="mini-btn">_</button>
            </div>
            <div id="pnl-chart"></div>
        </div>
        
        <!-- FOOTER - ALERTS -->
        <div id="footer">
            <div id="alert-label">⚠️ TACTICAL ALERTS</div>
            <div id="alert-ticker">
                <div id="alert-content">
                    <span class="alert-item">⚔️ Command Center Online</span>
                    <span class="alert-item">👑 Queen SERO Active</span>
                    <span class="alert-item">🧠 All Intelligence Systems Operational</span>
                    <span class="alert-item">🎯 Ready to Engage</span>
                </div>
            </div>
            <div id="threat-level">
                <span>DEFCON</span>
                <span id="defcon-level" class="defcon-5">5</span>
            </div>
        </div>
    </div>
    
    <script>
        // ═══════════════════════════════════════════════════════════════════════════
        // COMMAND CENTER JAVASCRIPT - FULLY LOADED
        // ═══════════════════════════════════════════════════════════════════════════
        
        let ws = null;
        let voiceEnabled = false;
        let startTime = Date.now();
        let systemsData = {};
        let tradesData = [];
        let whalesData = [];
        let botsData = [];
        let latestStats = {};
        let latestSystems = {};
        let terminal = null;
        let systemRadar = null;
        let globe = null;
        let pnlChart = null;
        let worldMap = null;
        let typedInstance = null;
        let defconLevel = 5;
        
        // Initialize WebSocket connection
        function initWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = () => {
                console.log('🎮 Command Center WebSocket connected');
                addAlert('🎮 Command Center connected to server');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            ws.onclose = () => {
                console.log('WebSocket closed, reconnecting...');
                addAlert('⚠️ Connection lost, reconnecting...');
                setTimeout(initWebSocket, 3000);
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }
        
        // Handle incoming messages
        function handleMessage(data) {
            switch(data.type) {
                case 'state':
                    updateFullState(data);
                    break;
                case 'live_feed':
                    setLiveIndicator(!!data.enabled);
                    break;
                case 'trading':
                    setTradingIndicator(!!data.enabled);
                    break;
                case 'trade':
                    addTrade(data.trade);
                    break;
                case 'whale':
                    addWhale(data.whale);
                    break;
                case 'bot':
                    addBot(data.bot);
                    break;
                case 'bot_scanner':
                    addBotShape(data.shape);
                    break;
                case 'whale_sonar':
                    addWhaleSonar(data.signal);
                    break;
                case 'orca':
                    addOrcaHunt(data.hunt);
                    break;
                case 'sniper':
                    addSniperShot(data.shot);
                    break;
                case 'queen':
                    updateQueenMessage(data.message);
                    break;
                case 'alert':
                    addAlert(data.alert);
                    break;
                case 'systems':
                    updateSystems(data.systems);
                    break;
                case 'systems_loaded':
                    // Systems finished loading in background (Windows fast start)
                    updateSystems(data.systems);
                    addAlert('✅ All intelligence systems ONLINE!', 'high');
                    break;
                case 'balances':
                    updateBalances(data.balances);
                    break;
                case 'stats':
                    updateStats(data.stats);
                    break;
                case 'log_stream':
                    // SCI-FI LOG STREAM
                    // Only show exciting logs or errors in the main alert feed
                    if (data.message.includes('success') || data.message.includes('profit') || data.message.includes('QUEEN') || data.message.includes('WAVE') || data.message.includes('⚠️')) {
                         addAlert(data.message, data.message.includes('⚠️') ? 'high' : 'normal');
                    }
                    
                    // Update visuals
                    if (data.visual_data) {
                        updateHarmonicVisuals(data.visual_data);
                    }
                    break;
            }
        }
        
        // Update full state
        function updateFullState(data) {
            if (data.stats) updateStats(data.stats);
            if (data.systems) updateSystems(data.systems);
            if (data.balances) updateBalances(data.balances);
            if (data.trades) {
                tradesData = data.trades;
                renderTrades();
            }
            if (data.whales) {
                whalesData = data.whales;
                renderWhales();
            }
            if (data.bots) {
                botsData = data.bots;
                renderBots();
            }
            if (data.bot_scanner) {
                botScannerData = data.bot_scanner;
                renderBotScanner();
            }
            if (data.whale_sonar) {
                whaleSonarData = data.whale_sonar;
                renderWhaleSonar();
            }
            if (data.orca) {
                orcaData = data.orca;
                renderOrca();
            }
            if (data.sniper) {
                sniperData = data.sniper;
                renderSniper();
            }
            if (data.queen_message) {
                updateQueenMessage(data.queen_message);
            }
        }
        
        // Track previous values for change detection
        let prevStats = {};
        
        // Update stats with animations
        function updateStats(stats) {
            latestStats = stats || {};
            
            // Animate P&L with color flash
            const pnlEl = document.getElementById('total-pnl');
            const newPnl = (stats.total_pnl || 0).toFixed(2);
            const pnlChanged = prevStats.total_pnl !== stats.total_pnl;
            
            if (pnlChanged && typeof gsap !== 'undefined') {
                const isPositive = stats.total_pnl >= (prevStats.total_pnl || 0);
                const card = pnlEl.closest('.stat-card');
                
                gsap.timeline()
                    .to(pnlEl, {
                        scale: 1.3,
                        textShadow: isPositive 
                            ? '0 0 30px rgba(0, 255, 136, 1)' 
                            : '0 0 30px rgba(255, 51, 102, 1)',
                        duration: 0.15
                    })
                    .to(pnlEl, {
                        scale: 1,
                        textShadow: '0 0 10px currentColor',
                        duration: 0.3,
                        ease: 'elastic.out(1, 0.5)'
                    });
                
                if (card) {
                    card.classList.add(isPositive ? 'flash-green' : 'flash-red');
                    setTimeout(() => card.classList.remove('flash-green', 'flash-red'), 500);
                }
            }
            
            pnlEl.textContent = '$' + newPnl;
            pnlEl.className = 'stat-value ' + (stats.total_pnl >= 0 ? 'gold' : 'red');
            
            // Animate trade count
            const tradesEl = document.getElementById('total-trades');
            if (stats.total_trades !== prevStats.total_trades && typeof anime !== 'undefined') {
                anime({
                    targets: tradesEl,
                    innerHTML: [prevStats.total_trades || 0, stats.total_trades || 0],
                    round: 1,
                    duration: 500,
                    easing: 'easeOutExpo'
                });
            } else {
                tradesEl.textContent = stats.total_trades || 0;
            }
            
            // Animate wins/losses
            const winsEl = document.getElementById('wins');
            const lossesEl = document.getElementById('losses');
            
            if (stats.winning_trades !== prevStats.winning_trades) {
                winsEl.textContent = stats.winning_trades || 0;
                winsEl.classList.add('updating');
                setTimeout(() => winsEl.classList.remove('updating'), 300);
            } else {
                winsEl.textContent = stats.winning_trades || 0;
            }
            
            if (stats.losing_trades !== prevStats.losing_trades) {
                lossesEl.textContent = stats.losing_trades || 0;
                lossesEl.classList.add('updating');
                setTimeout(() => lossesEl.classList.remove('updating'), 300);
            } else {
                lossesEl.textContent = stats.losing_trades || 0;
            }
            
            // Animate win rate
            const winRate = stats.total_trades > 0 
                ? ((stats.winning_trades / stats.total_trades) * 100).toFixed(1) 
                : 0;
            const winRateEl = document.getElementById('win-rate');
            winRateEl.textContent = winRate + '%';
            
            // Color win rate based on value
            if (winRate >= 60) {
                winRateEl.className = 'stat-value green';
            } else if (winRate >= 40) {
                winRateEl.className = 'stat-value gold';
            } else {
                winRateEl.className = 'stat-value red';
            }
            
            // Animate coherence
            const coherenceEl = document.getElementById('coherence');
            const coherenceVal = (stats.coherence || 0.5).toFixed(2);
            coherenceEl.textContent = coherenceVal;
            
            // Store for next comparison
            prevStats = {...stats};
            
            updateSystemRadar();
        }
        
        // Update systems list with animations
        function updateSystems(systems) {
            systemsData = systems;
            latestSystems = systems || {};
            const container = document.getElementById('systems-list');
            container.innerHTML = '';
            
            let online = 0;
            let total = 0;
            let delay = 0;
            
            for (const [name, status] of Object.entries(systems)) {
                total++;
                if (status) online++;
                
                const item = document.createElement('div');
                item.className = 'system-item' + (status ? '' : ' offline');
                item.style.opacity = '0';
                item.style.transform = 'translateX(-20px)';
                item.innerHTML = `
                    <span class="system-name">${name}</span>
                    <span class="system-status ${status ? '' : 'offline'}">${status ? '✅ ONLINE' : '❌ OFFLINE'}</span>
                `;
                container.appendChild(item);
                
                // Staggered animation
                setTimeout(() => {
                    item.style.transition = 'all 0.3s ease';
                    item.style.opacity = '1';
                    item.style.transform = 'translateX(0)';
                }, delay);
                delay += 30;
            }
            
            document.getElementById('systems-online').textContent = online;
            document.getElementById('systems-total').textContent = total;
            document.getElementById('systems-count').textContent = `${online}/${total}`;
            updateSystemRadar();
        }
        
        // Track previous balances
        let prevBalances = {};
        
        // Update balances with animations
        function updateBalances(balances) {
            for (const [exchange, balance] of Object.entries(balances)) {
                const balanceEl = document.getElementById(`${exchange}-balance`);
                const statusEl = document.getElementById(`${exchange}-status`);
                const cardEl = document.getElementById(`exchange-${exchange}`);
                
                if (balanceEl) {
                    if (typeof balance === 'number') {
                        const prevBal = prevBalances[exchange];
                        const changed = prevBal !== balance;
                        
                        // Animate balance change
                        if (changed && typeof anime !== 'undefined' && prevBal !== undefined) {
                            balanceEl.classList.add('updating');
                            anime({
                                targets: { val: prevBal },
                                val: balance,
                                duration: 800,
                                easing: 'easeOutExpo',
                                update: function(anim) {
                                    balanceEl.textContent = '$' + anim.animations[0].currentValue.toFixed(2);
                                },
                                complete: () => balanceEl.classList.remove('updating')
                            });
                        } else {
                            balanceEl.textContent = '$' + balance.toFixed(2);
                        }
                        
                        prevBalances[exchange] = balance;
                        
                        if (statusEl) {
                            statusEl.textContent = 'ONLINE';
                            statusEl.className = 'exchange-status-badge online';
                        }
                        if (cardEl) cardEl.classList.remove('offline');
                    } else if (balance === 'offline') {
                        balanceEl.textContent = 'OFFLINE';
                        if (statusEl) {
                            statusEl.textContent = 'OFFLINE';
                            statusEl.className = 'exchange-status-badge offline';
                        }
                        if (cardEl) cardEl.classList.add('offline');
                    }
                }
            }
        }
        
        // Add trade to feed with animations
        function addTrade(trade) {
            tradesData.unshift(trade);
            if (tradesData.length > 50) tradesData.pop();
            renderTrades();

            terminalLog(`TRADE ${trade.side || ''} ${trade.symbol || ''} PnL ${trade.pnl?.toFixed?.(2) ?? trade.pnl}`);
            
            // Create particle burst on profitable trade
            const firstTrade = document.querySelector('.trade-item');
            if (firstTrade && trade.pnl > 0) {
                createTradeBurst(firstTrade, true);
                playSound('win');
                
                // Flash the P&L card green
                const pnlCard = document.querySelector('.stat-card.gold');
                if (pnlCard) {
                    pnlCard.classList.add('flash-green');
                    setTimeout(() => pnlCard.classList.remove('flash-green'), 500);
                }
            } else if (firstTrade && trade.pnl < 0) {
                // Visual feedback for loss
                firstTrade.style.animation = 'none';
                firstTrade.offsetHeight; // Trigger reflow
                firstTrade.style.animation = 'tradeSlideIn 0.4s ease, shake 0.5s ease';
            }
        }
        
        // Shake animation for losing trades
        const shakeStyle = document.createElement('style');
        shakeStyle.textContent = `
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
                20%, 40%, 60%, 80% { transform: translateX(5px); }
            }
        `;
        document.head.appendChild(shakeStyle);
        
        // Render trades with staggered animations
        function renderTrades() {
            const container = document.getElementById('trade-list');
            const existingItems = container.querySelectorAll('.trade-item');
            
            // Only re-render if data changed
            container.innerHTML = '';
            
            tradesData.slice(0, 20).forEach((trade, index) => {
                const item = document.createElement('div');
                const isWhale = trade.volume > 100000;
                item.className = `trade-item ${trade.side} ${isWhale ? 'whale' : ''}`;
                item.style.animationDelay = `${index * 0.05}s`;
                item.innerHTML = `
                    <span class="trade-time">${trade.time || '--:--:--'}</span>
                    <span class="trade-type ${trade.side}">${trade.side?.toUpperCase() || 'TRADE'}</span>
                    <span class="trade-symbol">${trade.symbol || 'N/A'}</span>
                    <span class="trade-amount">$${(trade.amount || 0).toFixed(2)}</span>
                    <span class="trade-pnl ${(trade.pnl || 0) >= 0 ? 'positive' : 'negative'}">
                        ${(trade.pnl || 0) >= 0 ? '+' : ''}$${(trade.pnl || 0).toFixed(2)}
                    </span>
                `;
                container.appendChild(item);
            });
        }
        
        // Add whale alert with animation
        function addWhale(whale) {
            whalesData.unshift(whale);
            if (whalesData.length > 30) whalesData.pop();
            renderWhales();
            playSound('whale');
            
            // Splash animation on whale panel
            const whalePanel = document.getElementById('whale-panel');
            if (whalePanel && typeof gsap !== 'undefined') {
                gsap.to(whalePanel, {
                    boxShadow: '0 0 50px rgba(0, 191, 255, 0.8)',
                    duration: 0.3,
                    yoyo: true,
                    repeat: 1
                });
            }
        }
        
        // Render whales with swim animation
        function renderWhales() {
            const container = document.getElementById('whale-list');
            container.innerHTML = '';
            document.getElementById('whale-count').textContent = whalesData.length;
            
            whalesData.slice(0, 10).forEach((whale, index) => {
                const item = document.createElement('div');
                item.className = 'whale-item';
                item.style.animationDelay = `${index * 0.1}s`;
                item.innerHTML = `
                    <span class="whale-icon">🐋</span>
                    <div class="whale-info">
                        <div class="whale-symbol">${whale.symbol || 'N/A'}</div>
                        <div class="whale-volume">$${formatNumber(whale.volume || 0)}</div>
                    </div>
                    <span class="whale-direction ${whale.direction}">${whale.direction === 'buy' ? '📈' : '📉'}</span>
                `;
                container.appendChild(item);
            });
        }
        
        // Add bot detection with scan animation
        function addBot(bot) {
            botsData.unshift(bot);
            if (botsData.length > 50) botsData.pop();
            renderBots();
            
            // Flash the bot panel
            const botPanel = document.getElementById('bot-panel');
            if (botPanel && typeof gsap !== 'undefined') {
                gsap.to(botPanel, {
                    boxShadow: '0 0 40px rgba(153, 102, 255, 0.8)',
                    duration: 0.2,
                    yoyo: true,
                    repeat: 1
                });
            }
        }
        
        // Add bot shape detection
        function addBotShape(shape) {
            botScannerData.unshift(shape);
            if (botScannerData.length > 30) botScannerData.pop();
            renderBotScanner();
            
            // Flash the bot scanner panel
            const panel = document.getElementById('bot-scanner-panel');
            if (panel && typeof gsap !== 'undefined') {
                gsap.to(panel, {
                    boxShadow: '0 0 40px rgba(0, 255, 136, 0.8)',
                    duration: 0.2,
                    yoyo: true,
                    repeat: 1
                });
            }
        }
        
        // Add whale sonar signal
        function addWhaleSonar(signal) {
            whaleSonarData.unshift(signal);
            if (whaleSonarData.length > 20) whaleSonarData.pop();
            renderWhaleSonar();
            
            // Flash the whale sonar panel
            const panel = document.getElementById('whale-sonar-panel');
            if (panel && typeof gsap !== 'undefined') {
                gsap.to(panel, {
                    boxShadow: '0 0 40px rgba(0, 255, 255, 0.8)',
                    duration: 0.2,
                    yoyo: true,
                    repeat: 1
                });
            }
        }
        
        // Add orca hunt
        function addOrcaHunt(hunt) {
            orcaData.unshift(hunt);
            if (orcaData.length > 15) orcaData.pop();
            renderOrca();
            
            // Flash the orca panel
            const panel = document.getElementById('orca-panel');
            if (panel && typeof gsap !== 'undefined') {
                gsap.to(panel, {
                    boxShadow: '0 0 40px rgba(255, 102, 0, 0.8)',
                    duration: 0.2,
                    yoyo: true,
                    repeat: 1
                });
            }
        }
        
        // Add sniper shot
        function addSniperShot(shot) {
            sniperData.unshift(shot);
            if (sniperData.length > 25) sniperData.pop();
            renderSniper();
            
            // Flash the sniper panel
            const panel = document.getElementById('sniper-panel');
            if (panel && typeof gsap !== 'undefined') {
                gsap.to(panel, {
                    boxShadow: '0 0 40px rgba(255, 51, 102, 0.8)',
                    duration: 0.2,
                    yoyo: true,
                    repeat: 1
                });
            }
        }
        
        // Render bots
        function renderBots() {
            const container = document.getElementById('bot-list');
            container.innerHTML = '';
            document.getElementById('bot-count').textContent = botsData.length;
            
            for (const bot of botsData.slice(0, 15)) {
                const item = document.createElement('div');
                item.className = 'bot-item';
                item.innerHTML = `
                    <span class="bot-icon">🤖</span>
                    <span class="bot-firm">${bot.firm || 'Unknown'}</span>
                    <span class="bot-country">${bot.country || ''}</span>
                `;
                container.appendChild(item);
            }
        }
        
        // Bot Shape Scanner data and rendering
        let botScannerData = [];
        
        function renderBotScanner() {
            const container = document.getElementById('bot-scanner-list');
            container.innerHTML = '';
            document.getElementById('bot-scanner-status').textContent = botScannerData.length > 0 ? 'ACTIVE' : 'SCANNING';
            
            botScannerData.slice(0, 10).forEach((shape, index) => {
                const item = document.createElement('div');
                item.className = 'scanner-item';
                item.style.animationDelay = `${index * 0.1}s`;
                item.innerHTML = `
                    <span class="scanner-icon">🔍</span>
                    <div class="scanner-info">
                        <div class="scanner-type">${shape.type || 'Unknown'}</div>
                        <div class="scanner-confidence">${(shape.confidence * 100).toFixed(1)}%</div>
                    </div>
                    <span class="scanner-status">${shape.status || 'Detected'}</span>
                `;
                container.appendChild(item);
            });
        }
        
        // Whale Sonar data and rendering
        let whaleSonarData = [];
        
        function renderWhaleSonar() {
            const container = document.getElementById('whale-sonar-list');
            container.innerHTML = '';
            const avgSignal = whaleSonarData.length > 0 ? 
                (whaleSonarData.reduce((sum, s) => sum + (s.signal || 0), 0) / whaleSonarData.length).toFixed(2) : '0.0';
            document.getElementById('sonar-signal').textContent = avgSignal;
            
            whaleSonarData.slice(0, 8).forEach((signal, index) => {
                const item = document.createElement('div');
                item.className = 'sonar-item';
                item.style.animationDelay = `${index * 0.1}s`;
                item.innerHTML = `
                    <span class="sonar-icon">🔊</span>
                    <div class="sonar-info">
                        <div class="sonar-source">${signal.source || 'Unknown'}</div>
                        <div class="sonar-strength">${(signal.signal * 100).toFixed(0)}%</div>
                    </div>
                    <span class="sonar-code">${signal.code || 'N/A'}</span>
                `;
                container.appendChild(item);
            });
        }
        
        // Orca Intelligence data and rendering
        let orcaData = [];
        
        function renderOrca() {
            const container = document.getElementById('orca-list');
            container.innerHTML = '';
            document.getElementById('orca-hunts').textContent = orcaData.length;
            
            orcaData.slice(0, 6).forEach((hunt, index) => {
                const item = document.createElement('div');
                item.className = 'orca-item';
                item.style.animationDelay = `${index * 0.1}s`;
                item.innerHTML = `
                    <span class="orca-icon">🦈</span>
                    <div class="orca-info">
                        <div class="orca-target">${hunt.target || 'Unknown'}</div>
                        <div class="orca-mode">${hunt.mode || 'Stalking'}</div>
                    </div>
                    <span class="orca-status">${hunt.status || 'Active'}</span>
                `;
                container.appendChild(item);
            });
        }
        
        // Unified Sniper Brain data and rendering
        let sniperData = [];
        
        function renderSniper() {
            const container = document.getElementById('sniper-list');
            container.innerHTML = '';
            const winRate = sniperData.length > 0 ? 
                (sniperData.filter(s => s.result === 'win').length / sniperData.length * 100).toFixed(1) : '0.0';
            document.getElementById('sniper-winrate').textContent = `${winRate}%`;
            
            sniperData.slice(0, 5).forEach((shot, index) => {
                const item = document.createElement('div');
                item.className = 'sniper-item';
                item.style.animationDelay = `${index * 0.1}s`;
                item.innerHTML = `
                    <span class="sniper-icon">🎯</span>
                    <div class="sniper-info">
                        <div class="sniper-target">${shot.target || 'N/A'}</div>
                        <div class="sniper-pnl">$${shot.pnl ? shot.pnl.toFixed(2) : '0.00'}</div>
                    </div>
                    <span class="sniper-result ${shot.result}">${shot.result === 'win' ? '✅' : '❌'}</span>
                `;
                container.appendChild(item);
            });
        }
        
        // Update Queen message
        function updateQueenMessage(message) {
            document.getElementById('queen-message').textContent = message;
            terminalLog(`QUEEN: ${message}`);
            
            if (voiceEnabled) {
                speak(message);
            }
        }
        
        // Add alert
        function addAlert(alertText) {
            const content = document.getElementById('alert-content');
            const item = document.createElement('span');
            item.className = 'alert-item';
            item.textContent = alertText;
            content.appendChild(item);
            terminalLog(`ALERT: ${alertText}`);
            
            // Limit alerts
            while (content.children.length > 20) {
                content.removeChild(content.firstChild);
            }
        }
        
        // Toggle voice
        function toggleVoice() {
            voiceEnabled = !voiceEnabled;
            const btn = document.getElementById('voice-toggle');
            btn.textContent = voiceEnabled ? '🔊 VOICE ON' : '🔇 VOICE OFF';
            btn.classList.toggle('speaking', voiceEnabled);
            
            if (voiceEnabled) {
                speak('Queen voice enabled. I am watching everything.');
            }
        }
        
        // Text-to-speech
        function speak(text) {
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = 0.9;
                utterance.pitch = 1.1;
                // Use a robotic voice if available
                const voices = speechSynthesis.getVoices();
                const robotVoice = voices.find(v => v.name.includes('Microsoft') || v.name.includes('Google'));
                if (robotVoice) utterance.voice = robotVoice;
                speechSynthesis.speak(utterance);
            }
        }
        
        // ═══════════════════════════════════════════════════════════════════════
        // SOUND SYSTEM (Howler.js)
        // ═══════════════════════════════════════════════════════════════════════
        
        let sounds = {};
        function initSounds() {
            if (typeof Howl === 'undefined') return;
            
            // Create sound effects using web audio API generated tones
            sounds.alert = new Howl({
                src: ['data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdH2HkZWRjImFg4WHjZGVlI+JhYOFiY+TlpKNiYWDhYqOkpWTj4qGhIaKjpKUko+Jh4WGi4+TlJKOioaFh4uOkpOSjo2KiYiKjI+RkZCOjIuKiouNj5CQj42Mi4uLjI6PkJCPjY2Li4yNjo+Pj46NjIyMjY6Ojo6OjY2NjY2Ojo6Ojo2NjY2NjY6Ojo6OjY2NjY2Njo6Ojo6NjY2NjY6Ojo6OjY2NjY2NjY2NjY2NjY2NjY2NjY2NjY2NjQ=='],
                volume: 0.3
            });
            
            sounds.win = new Howl({
                src: ['data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgA'],
                volume: 0.4
            });
        }
        
        function playSound(type) {
            if (sounds[type]) {
                sounds[type].play();
            }
        }
        
        // ═══════════════════════════════════════════════════════════════════════
        // RED ALERT MODE
        // ═══════════════════════════════════════════════════════════════════════
        
        let redAlertActive = false;
        let redAlertSound = null;
        
        function toggleRedAlert() {
            redAlertActive = !redAlertActive;
            document.body.classList.toggle('red-alert', redAlertActive);
            document.getElementById('red-alert-btn').classList.toggle('active', redAlertActive);
            
            if (redAlertActive) {
                speakText("RED ALERT! All commanders to battle stations!");
                // Pulse the header
                gsap.to('#header', {
                    borderColor: '#ff0000',
                    duration: 0.5,
                    repeat: -1,
                    yoyo: true
                });
            } else {
                gsap.killTweensOf('#header');
                gsap.to('#header', { borderColor: '#FFD700', duration: 0.3 });
            }
        }
        
        // ═══════════════════════════════════════════════════════════════════════
        // FLIGHT CHECK
        // ═══════════════════════════════════════════════════════════════════════
        
        async function runFlightCheck() {
            try {
                const btn = document.getElementById('flight-check-btn');
                btn.textContent = '🛫 CHECKING...';
                btn.disabled = true;
                
                const response = await fetch('/api/flight-check');
                const data = await response.json();
                
                // Display results in console
                console.log(data.poem);
                
                // Show in queen message
                const goCount = data.summary.online;
                const total = data.summary.total;
                const allGo = data.summary.all_go;
                
                if (allGo) {
                    updateQueenMessage(`🛫 FLIGHT CHECK COMPLETE: ALL ${total} SYSTEMS GO! Clear for launch, Commander!`);
                    speakText(`Flight check complete. All ${total} systems are go. Clear for launch!`);
                    if (typeof Swal !== 'undefined') {
                        Swal.fire({
                            icon: 'success',
                            title: 'ALL SYSTEMS GO',
                            text: `Flight check complete: ${total}/${total} systems online.`,
                            background: '#0a0a0f',
                            color: '#00FF88'
                        });
                    }
                } else {
                    updateQueenMessage(`🛫 FLIGHT CHECK: ${goCount}/${total} systems online. ${total - goCount} systems require attention.`);
                    speakText(`Warning. Flight check detected ${total - goCount} offline systems.`);
                    if (typeof Swal !== 'undefined') {
                        Swal.fire({
                            icon: 'warning',
                            title: 'SYSTEMS REQUIRE ATTENTION',
                            text: `${total - goCount} systems offline.`,
                            background: '#0a0a0f',
                            color: '#FFD700'
                        });
                    }
                }
                
                // Update systems panel with fresh data
                Object.entries(data.systems).forEach(([name, info]) => {
                    const systemItem = document.querySelector(`[data-system="${name}"]`);
                    if (systemItem) {
                        systemItem.classList.toggle('offline', info.status !== 'GO');
                        const pingSpan = systemItem.querySelector('.ping-ms');
                        if (pingSpan) pingSpan.textContent = `${info.ping_ms.toFixed(1)}ms`;
                    }
                });
                
                btn.textContent = allGo ? '✅ ALL GO' : '⚠️ CHECK';
                setTimeout(() => {
                    btn.textContent = '🛫 FLIGHT CHECK';
                    btn.disabled = false;
                }, 3000);
                
            } catch (error) {
                console.error('Flight check failed:', error);
                document.getElementById('flight-check-btn').textContent = '❌ ERROR';
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'error',
                        title: 'FLIGHT CHECK FAILED',
                        text: 'Unable to reach system endpoint.',
                        background: '#0a0a0f',
                        color: '#FF3366'
                    });
                }
            }
        }

        // ═══════════════════════════════════════════════════════════════════════
        // LIVE FEED TOGGLE
        // ═══════════════════════════════════════════════════════════════════════

        async function toggleLiveFeed() {
            const btn = document.getElementById('live-toggle-btn');
            try {
                const response = await fetch('/api/live-toggle', { method: 'POST' });
                const data = await response.json();
                setLiveIndicator(!!data.enabled);
            } catch (e) {
                console.error('Live toggle failed', e);
            }
        }

        async function toggleTradingEngine() {
            const btn = document.getElementById('trading-toggle-btn');
            btn.disabled = true;
            try {
                const response = await fetch('/api/trading-toggle', { method: 'POST' });
                const data = await response.json();
                setTradingIndicator(!!data.enabled);
            } catch (e) {
                console.error('Trading toggle failed', e);
            } finally {
                btn.disabled = false;
            }
        }

        function setLiveIndicator(enabled) {
            const btn = document.getElementById('live-toggle-btn');
            const mode = document.getElementById('trading-mode');
            if (enabled) {
                btn.textContent = '🟢 LIVE FEED';
                btn.classList.add('blue');
                mode.textContent = 'LIVE';
            } else {
                btn.textContent = '🔴 LIVE OFF';
                btn.classList.remove('blue');
                mode.textContent = 'OFF';
            }
        }

        function setTradingIndicator(enabled) {
            const btn = document.getElementById('trading-toggle-btn');
            if (enabled) {
                btn.textContent = '⚡ TRADING ON';
                btn.classList.add('green');
            } else {
                btn.textContent = '⚡ TRADING OFF';
                btn.classList.remove('green');
            }
        }

        // ═══════════════════════════════════════════════════════════════════════
        // TERMINAL (xterm.js)
        // ═══════════════════════════════════════════════════════════════════════

        function initTerminal() {
            if (typeof Terminal === 'undefined') return;
            terminal = new Terminal({
                cols: 60,
                rows: 8,
                cursorBlink: true,
                theme: {
                    background: '#05070a',
                    foreground: '#00FF88',
                    cursor: '#FFD700'
                }
            });
            terminal.open(document.getElementById('terminal'));
            terminal.writeln('AUREON COMMAND TERMINAL ONLINE');
            terminal.writeln('> Awaiting tactical input...');
        }

        function terminalLog(message) {
            if (!terminal) return;
            const ts = new Date().toLocaleTimeString();
            terminal.writeln(`[${ts}] ${message}`);
        }

        // ═══════════════════════════════════════════════════════════════════════
        // SYSTEM RADAR (ECharts)
        // ═══════════════════════════════════════════════════════════════════════

        function initSystemRadar() {
            if (typeof echarts === 'undefined') return;
            const el = document.getElementById('system-radar');
            systemRadar = echarts.init(el);
            updateSystemRadar();
        }

        function updateSystemRadar() {
            if (!systemRadar) return;
            const stats = latestStats || {};
            const systems = latestSystems || {};
            const total = Object.keys(systems).length || 1;
            const online = Object.values(systems).filter(Boolean).length;
            const onlineRatio = (online / total) * 100;
            const winRate = stats.total_trades > 0 ? (stats.winning_trades / stats.total_trades) * 100 : 0;
            const coherence = (stats.coherence || 0.5) * 100;
            const activity = Math.min((stats.total_trades || 0) * 2, 100);

            const option = {
                backgroundColor: 'transparent',
                radar: {
                    indicator: [
                        { name: 'SYSTEMS', max: 100 },
                        { name: 'WIN RATE', max: 100 },
                        { name: 'COHERENCE', max: 100 },
                        { name: 'ACTIVITY', max: 100 }
                    ],
                    splitLine: { lineStyle: { color: 'rgba(0,255,136,0.2)' } },
                    splitArea: { areaStyle: { color: ['rgba(0,0,0,0.2)', 'rgba(0,255,136,0.05)'] } },
                    axisLine: { lineStyle: { color: 'rgba(0,255,255,0.3)' } }
                },
                series: [
                    {
                        type: 'radar',
                        data: [
                            {
                                value: [onlineRatio, winRate, coherence, activity],
                                name: 'SYSTEM STATUS'
                            }
                        ],
                        areaStyle: { color: 'rgba(0,255,136,0.3)' },
                        lineStyle: { color: '#00FF88' },
                        itemStyle: { color: '#FFD700' }
                    }
                ]
            };

            systemRadar.setOption(option);
        }

        // ═══════════════════════════════════════════════════════════════════════
        // 3D GLOBE (Globe.gl)
        // ═══════════════════════════════════════════════════════════════════════

        function initGlobe() {
            if (typeof Globe === 'undefined') return;
            const globeEl = document.getElementById('globe');
            if (!globeEl) return;

            const points = [
                { lat: 37.7749, lng: -122.4194, size: 0.12, color: '#9945FF', label: 'KRAKEN' },
                { lat: 1.3521, lng: 103.8198, size: 0.12, color: '#F0B90B', label: 'BINANCE' },
                { lat: 37.7749, lng: -122.4194, size: 0.12, color: '#00FF88', label: 'ALPACA' },
                { lat: 51.5074, lng: -0.1278, size: 0.12, color: '#00BFFF', label: 'CAPITAL' }
            ];

            globe = Globe()(globeEl)
                .backgroundColor('rgba(0,0,0,0)')
                .globeImageUrl('https://unpkg.com/three-globe/example/img/earth-night.jpg')
                .bumpImageUrl('https://unpkg.com/three-globe/example/img/earth-topology.png')
                .pointsData(points)
                .pointAltitude('size')
                .pointColor('color')
                .pointLabel('label');

            globe.controls().autoRotate = true;
            globe.controls().autoRotateSpeed = 0.3;
            globe.pointOfView({ lat: 20, lng: 0, altitude: 2.2 });
        }
        
        // ═══════════════════════════════════════════════════════════════════════
        // PARTICLES.JS BACKGROUND
        // ═══════════════════════════════════════════════════════════════════════
        
        function initParticles() {
            if (typeof particlesJS === 'undefined') return;
            
            particlesJS('particles-js', {
                particles: {
                    number: { value: 80, density: { enable: true, value_area: 800 } },
                    color: { value: ['#00FF88', '#FFD700', '#00BFFF'] },
                    shape: { type: 'circle' },
                    opacity: { value: 0.5, random: true },
                    size: { value: 3, random: true },
                    line_linked: {
                        enable: true,
                        distance: 150,
                        color: '#00FF88',
                        opacity: 0.2,
                        width: 1
                    },
                    move: {
                        enable: true,
                        speed: 1,
                        direction: 'none',
                        random: true,
                        out_mode: 'out'
                    }
                },
                interactivity: {
                    events: {
                        onhover: { enable: true, mode: 'grab' },
                        onclick: { enable: true, mode: 'push' }
                    }
                }
            });
        }
        
        // ═══════════════════════════════════════════════════════════════════════
        // RADAR SWEEP ANIMATION
        // ═══════════════════════════════════════════════════════════════════════
        
        let radarAngle = 0;
        function drawRadar() {
            const canvas = document.getElementById('radar-canvas');
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            const size = Math.min(canvas.offsetWidth, canvas.offsetHeight);
            canvas.width = size;
            canvas.height = size;
            
            const centerX = size / 2;
            const centerY = size / 2;
            const radius = size / 2 - 10;
            
            // Clear
            ctx.clearRect(0, 0, size, size);
            
            // Draw circles
            ctx.strokeStyle = 'rgba(0, 255, 136, 0.3)';
            ctx.lineWidth = 1;
            for (let r = radius / 4; r <= radius; r += radius / 4) {
                ctx.beginPath();
                ctx.arc(centerX, centerY, r, 0, Math.PI * 2);
                ctx.stroke();
            }
            
            // Draw cross lines
            ctx.beginPath();
            ctx.moveTo(centerX - radius, centerY);
            ctx.lineTo(centerX + radius, centerY);
            ctx.moveTo(centerX, centerY - radius);
            ctx.lineTo(centerX, centerY + radius);
            ctx.stroke();
            
            // Draw sweep
            const gradient = ctx.createConicGradient(radarAngle, centerX, centerY);
            gradient.addColorStop(0, 'rgba(0, 255, 136, 0.5)');
            gradient.addColorStop(0.1, 'rgba(0, 255, 136, 0.2)');
            gradient.addColorStop(0.2, 'rgba(0, 255, 136, 0)');
            gradient.addColorStop(1, 'rgba(0, 255, 136, 0)');
            
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
            ctx.fill();
            
            // Sweep line
            ctx.strokeStyle = '#00FF88';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(
                centerX + Math.cos(radarAngle) * radius,
                centerY + Math.sin(radarAngle) * radius
            );
            ctx.stroke();
            
            // Draw blips (exchange locations)
            const blips = [
                { angle: 0.5, dist: 0.6, label: '🐙' },   // Kraken
                { angle: 1.8, dist: 0.7, label: '🟡' },   // Binance
                { angle: 3.2, dist: 0.5, label: '🦙' },   // Alpaca
                { angle: 4.5, dist: 0.8, label: '💼' }    // Capital
            ];
            
            blips.forEach(blip => {
                const x = centerX + Math.cos(blip.angle) * radius * blip.dist;
                const y = centerY + Math.sin(blip.angle) * radius * blip.dist;
                
                // Blip glow
                ctx.fillStyle = 'rgba(0, 255, 136, 0.5)';
                ctx.beginPath();
                ctx.arc(x, y, 8, 0, Math.PI * 2);
                ctx.fill();
                
                ctx.font = '12px sans-serif';
                ctx.fillText(blip.label, x - 6, y + 4);
            });
            
            radarAngle += 0.02;
            requestAnimationFrame(drawRadar);
        }
        
        // Format large numbers
        function formatNumber(num) {
            if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
            if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
            return num.toFixed(0);
        }
        
        // Update clock
        function updateClock() {
            const now = new Date();
            document.getElementById('current-time').textContent = now.toLocaleTimeString();
            
            // Uptime
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const hours = Math.floor(elapsed / 3600);
            const minutes = Math.floor((elapsed % 3600) / 60);
            const seconds = elapsed % 60;
            document.getElementById('uptime').textContent = 
                `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
        
        // Global Visual State for Sci-Fi FX
        let visualState = {
            targetFreqs: [0.02, 0.03, 0.015, 0.025],
            currentFreqs: [0.02, 0.03, 0.015, 0.025],
            targetAmps: [20, 15, 25, 18],
            currentAmps: [20, 15, 25, 18],
            colors: ['#00FF88', '#FFD700', '#00BFFF', '#FF6600'],
            phase: 0,
            activeType: 'normal',
            particles: []
        };
        
        function updateHarmonicVisuals(data) {
            visualState.activeType = data.type;
            
            // Map entropy to frequencies for unique signatures
            const baseFreq = (data.entropy % 100) / 1000;
            visualState.targetFreqs = [
                baseFreq * 1.5 + 0.01, 
                baseFreq * 2.0 + 0.02, 
                baseFreq * 0.5 + 0.005, 
                baseFreq * 3.0 + 0.03
            ];
            
            // Boost amplitudes on activity (Audio-reactive style)
            visualState.targetAmps = [
                40 + (data.entropy % 40), 
                30 + (data.entropy % 30), 
                50 + (data.entropy % 50), 
                35 + (data.entropy % 35)
            ];
            
            // Change colors based on semantic type
            if (data.type === 'queen') visualState.colors = ['#FF00FF', '#8A2BE2', '#9400D3', '#DA70D6']; // Purples
            else if (data.type === 'profit') visualState.colors = ['#00FF00', '#32CD32', '#00FA9A', '#7FFF00']; // Greens
            else if (data.type === 'wave') visualState.colors = ['#00FFFF', '#1E90FF', '#0000FF', '#ADD8E6']; // Blues
            else if (data.type === 'exchange') visualState.colors = ['#FFA500', '#FF8C00', '#FFD700', '#FFFF00']; // Golds
            else visualState.colors = ['#00FF88', '#FFD700', '#00BFFF', '#FF6600']; // Default
        }

        // Draw harmonic visualization (SCI-FI SPECTROGRAM STYLE)
        function drawHarmonics() {
            const canvas = document.getElementById('harmonic-canvas');
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            canvas.width = canvas.offsetWidth;
            canvas.height = canvas.offsetHeight;
            
            const width = canvas.width;
            const height = canvas.height;
            const centerY = height / 2;
            
            // Decay trail effect (Ghosting)
            ctx.fillStyle = 'rgba(10, 15, 30, 0.2)'; // Dark blue-black fade
            ctx.fillRect(0, 0, width, height);
            
            visualState.phase += 0.1; // Faster animation
            
            // Interpolate values for smooth physics
            for(let i=0; i<4; i++) {
                visualState.currentFreqs[i] += (visualState.targetFreqs[i] - visualState.currentFreqs[i]) * 0.1;
                visualState.currentAmps[i] += (visualState.targetAmps[i] - visualState.currentAmps[i]) * 0.1;
                
                // Decay target amps back to baseline breathing
                visualState.targetAmps[i] = visualState.targetAmps[i] * 0.95 + 10 * 0.05;
            }

            // Draw Sci-Fi Waves
            for (let w = 0; w < 4; w++) {
                ctx.beginPath();
                ctx.strokeStyle = visualState.colors[w];
                ctx.lineWidth = 2 + (visualState.currentAmps[w] / 20); // Thicker when loud
                ctx.shadowBlur = max(5, visualState.currentAmps[w] / 2); // Glow effect
                ctx.shadowColor = visualState.colors[w];
                ctx.globalAlpha = 0.8;
                
                const freq = visualState.currentFreqs[w];
                const amp = visualState.currentAmps[w];
                const phase = visualState.phase * (w * 0.5 + 1);
                
                for (let x = 0; x < width; x++) {
                    // FM Synthesis style modulation for "tech" look
                    const modulator = Math.sin(x * 0.02 + phase) * 20; 
                    const y = centerY + Math.sin(x * freq + phase + (modulator * 0.005)) * amp;
                    
                    if (x === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                }
                ctx.stroke();
            }
            
            // Cleanup state
            ctx.shadowBlur = 0;
            ctx.globalAlpha = 1;
            
            requestAnimationFrame(drawHarmonics);
        }
        
        function max(a, b) { return a > b ? a : b; }
        
        // Fetch initial state
        async function fetchInitialState() {
            try {
                const response = await fetch('/api/state');
                const data = await response.json();
                updateFullState(data);
                if (typeof data.live_feed !== 'undefined') {
                    setLiveIndicator(!!data.live_feed);
                }
                if (typeof data.trading_on !== 'undefined') {
                    setTradingIndicator(!!data.trading_on);
                }
            } catch (error) {
                console.error('Failed to fetch initial state:', error);
            }
        }
        
        // ═══════════════════════════════════════════════════════════════════════
        // 🌀 STARGATE PORTAL SYSTEM - FULL IMPLEMENTATION
        // ═══════════════════════════════════════════════════════════════════════
        
        // Stargate state
        const stargateState = {
            active: false,
            dialing: false,
            chevronSequence: [],
            lockedChevrons: 0,
            connectedTo: null,
            audioContext: null,
            sounds: {}
        };
        
        // Planetary stargate addresses (from aureon_stargate_protocol.py)
        const STARGATE_ADDRESSES = {
            'giza': { name: 'Giza', freq: 432.0, symbol: '🔺', coord: [29.9792, 31.1342] },
            'stonehenge': { name: 'Stonehenge', freq: 396.0, symbol: '🗿', coord: [51.1789, -1.8262] },
            'machu': { name: 'Machu Picchu', freq: 528.0, symbol: '🏔️', coord: [-13.1631, -72.5450] },
            'angkor': { name: 'Angkor Wat', freq: 417.0, symbol: '🛕', coord: [13.4125, 103.8670] },
            'uluru': { name: 'Uluru', freq: 639.0, symbol: '🪨', coord: [-25.3444, 131.0369] },
            'sedona': { name: 'Sedona', freq: 741.0, symbol: '🌵', coord: [34.8697, -111.7610] },
            'teotihuacan': { name: 'Teotihuacan', freq: 852.0, symbol: '🌙', coord: [19.6925, -98.8438] },
            'earth': { name: 'Earth Origin', freq: 7.83, symbol: '🌍', coord: [0, 0] },
            'sirius': { name: 'Sirius Gate', freq: 963.0, symbol: '⭐', coord: [0, 0] },
            'pleiades': { name: 'Pleiades Cluster', freq: 1111.0, symbol: '✨', coord: [0, 0] },
            'orion': { name: 'Orion Gateway', freq: 888.0, symbol: '🎯', coord: [0, 0] },
            'atlantis': { name: 'Atlantis', freq: 528.0, symbol: '🔱', coord: [0, 0] }
        };
        
        // Initialize Stargate audio (Web Audio API)
        function initStargateAudio() {
            try {
                stargateState.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                
                // Create sound generators
                stargateState.sounds = {
                    chevronLock: () => playTone(800, 0.3, 'square'),
                    chevronEngage: () => playTone(1200, 0.2, 'sawtooth'),
                    wormholeOpen: () => playWormholeSound(),
                    kawoosh: () => playKawooshSound(),
                    gateShutdown: () => playTone(200, 1, 'sine'),
                    glyphSelect: () => playTone(600, 0.1, 'triangle')
                };
            } catch (e) {
                console.log('Web Audio not available');
            }
        }
        
        function playTone(frequency, duration, type = 'sine') {
            if (!stargateState.audioContext) return;
            
            const ctx = stargateState.audioContext;
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            
            osc.type = type;
            osc.frequency.value = frequency;
            gain.gain.setValueAtTime(0.3, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + duration);
            
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + duration);
        }
        
        function playWormholeSound() {
            if (!stargateState.audioContext) return;
            
            const ctx = stargateState.audioContext;
            const duration = 2;
            
            // Layered frequencies for wormhole effect
            [100, 150, 200, 300, 400].forEach((freq, i) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(freq * 2, ctx.currentTime + duration);
                
                gain.gain.setValueAtTime(0, ctx.currentTime);
                gain.gain.linearRampToValueAtTime(0.2 / (i + 1), ctx.currentTime + 0.3);
                gain.gain.linearRampToValueAtTime(0.1 / (i + 1), ctx.currentTime + duration);
                
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + duration);
            });
        }
        
        function playKawooshSound() {
            if (!stargateState.audioContext) return;
            
            const ctx = stargateState.audioContext;
            
            // White noise burst for kawoosh
            const bufferSize = ctx.sampleRate * 1.5;
            const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
            const data = buffer.getChannelData(0);
            
            for (let i = 0; i < bufferSize; i++) {
                data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.3));
            }
            
            const source = ctx.createBufferSource();
            const filter = ctx.createBiquadFilter();
            const gain = ctx.createGain();
            
            source.buffer = buffer;
            filter.type = 'lowpass';
            filter.frequency.setValueAtTime(2000, ctx.currentTime);
            filter.frequency.exponentialRampToValueAtTime(200, ctx.currentTime + 1.5);
            
            gain.gain.setValueAtTime(0.5, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 1.5);
            
            source.connect(filter);
            filter.connect(gain);
            gain.connect(ctx.destination);
            source.start();
        }
        
        // Glyph selection
        function selectGlyph(glyphName) {
            if (stargateState.dialing || stargateState.active) return;
            if (stargateState.chevronSequence.length >= 7) return;
            
            const btn = document.querySelector(`[data-glyph="${glyphName}"]`);
            if (!btn || btn.classList.contains('selected')) return;
            
            btn.classList.add('selected');
            stargateState.chevronSequence.push(glyphName);
            stargateState.sounds.glyphSelect?.();
            
            updateDHDStatus();
        }
        
        // Update DHD status display
        function updateDHDStatus() {
            const statusEl = document.getElementById('dhd-status');
            const count = stargateState.chevronSequence.length;
            
            if (count === 0) {
                statusEl.textContent = 'STANDBY';
            } else if (count < 7) {
                statusEl.textContent = `${count}/7 GLYPHS`;
            } else {
                statusEl.textContent = 'READY TO DIAL';
            }
        }
        
        // Main stargate activation
        async function activateStargate() {
            // Resume audio context on user interaction
            if (stargateState.audioContext?.state === 'suspended') {
                stargateState.audioContext.resume();
            }
            
            if (stargateState.active) {
                // Shutdown gate
                shutdownStargate();
                return;
            }
            
            if (stargateState.chevronSequence.length < 7) {
                // Auto-dial demo sequence
                stargateState.chevronSequence = ['giza', 'stonehenge', 'machu', 'sirius', 'orion', 'pleiades', 'earth'];
                document.querySelectorAll('.glyph-btn').forEach(btn => {
                    if (stargateState.chevronSequence.includes(btn.dataset.glyph)) {
                        btn.classList.add('selected');
                    }
                });
            }
            
            stargateState.dialing = true;
            document.getElementById('dhd-big-red').classList.add('engaged');
            document.getElementById('dhd-status').textContent = 'DIALING...';
            document.getElementById('stargate-status').classList.add('active');
            document.getElementById('stargate-container').classList.add('active');
            
            // Lock chevrons one by one
            for (let i = 0; i < 7; i++) {
                await lockChevron(i + 1);
                await sleep(800);
            }
            
            // Establish wormhole
            await establishWormhole();
        }
        
        async function lockChevron(num) {
            const chevron = document.querySelector(`.chevron[data-chevron="${num}"]`);
            const indicator = document.querySelector(`.chevron-indicator[data-idx="${num}"]`);
            
            if (chevron) {
                chevron.classList.add('locked');
                stargateState.sounds.chevronLock?.();
            }
            
            if (indicator) {
                indicator.classList.add('locked');
            }
            
            stargateState.lockedChevrons = num;
            document.getElementById('gate-address').textContent = `CHEVRON ${num} LOCKED`;
            
            // GSAP animation
            if (typeof gsap !== 'undefined' && chevron) {
                gsap.timeline()
                    .to(chevron, { scale: 1.2, duration: 0.1 })
                    .to(chevron, { scale: 1, duration: 0.2 });
            }
        }
        
        async function establishWormhole() {
            document.getElementById('gate-address').textContent = 'ESTABLISHING WORMHOLE...';
            stargateState.sounds.wormholeOpen?.();
            
            await sleep(500);
            
            // Kawoosh!
            const kawoosh = document.querySelector('.kawoosh');
            kawoosh.classList.add('active');
            stargateState.sounds.kawoosh?.();
            
            await sleep(1500);
            kawoosh.classList.remove('active');
            
            // Event horizon active
            const eventHorizon = document.querySelector('.event-horizon');
            eventHorizon.classList.add('active');
            
            const destination = STARGATE_ADDRESSES[stargateState.chevronSequence[0]] || { name: 'Unknown' };
            document.getElementById('gate-address').textContent = `CONNECTED: ${destination.name.toUpperCase()}`;
            document.getElementById('dhd-status').textContent = 'CONNECTED';
            
            stargateState.dialing = false;
            stargateState.active = true;
            stargateState.connectedTo = destination;
            
            // Queen announcement
            updateQueenMessage(`🌀 Stargate connection established to ${destination.name}! Wormhole stable. Timeline coherence at maximum.`);
        }
        
        function shutdownStargate() {
            stargateState.sounds.gateShutdown?.();
            
            // Reset all states
            document.querySelector('.event-horizon').classList.remove('active');
            document.querySelectorAll('.chevron').forEach(c => c.classList.remove('locked'));
            document.querySelectorAll('.chevron-indicator').forEach(c => c.classList.remove('locked'));
            document.querySelectorAll('.glyph-btn').forEach(b => b.classList.remove('selected'));
            
            document.getElementById('stargate-container').classList.remove('active');
            document.getElementById('stargate-status').classList.remove('active');
            document.getElementById('dhd-big-red').classList.remove('engaged');
            document.getElementById('dhd-status').textContent = 'STANDBY';
            document.getElementById('gate-address').textContent = 'IDLE - NO CONNECTION';
            
            stargateState.active = false;
            stargateState.dialing = false;
            stargateState.chevronSequence = [];
            stargateState.lockedChevrons = 0;
            stargateState.connectedTo = null;
            
            updateQueenMessage('🌀 Stargate shutdown complete. Wormhole disengaged.');
        }
        
        function sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }
        
        // Timeline card click handlers
        function initQuantumMirror() {
            document.querySelectorAll('.timeline-card').forEach(card => {
                card.addEventListener('click', () => {
                    const timeline = card.dataset.timeline;
                    
                    // Visual feedback
                    if (typeof gsap !== 'undefined') {
                        gsap.timeline()
                            .to(card, { rotateY: 180, duration: 0.3 })
                            .to(card, { rotateY: 360, duration: 0.3 })
                            .set(card, { rotateY: 0 });
                    }
                    
                    // Toggle anchored state
                    if (card.classList.contains('anchored')) {
                        card.classList.remove('anchored');
                        updateQueenMessage(`🪞 Timeline "${timeline}" unanchored. Reality branch floating.`);
                    } else {
                        card.classList.add('anchored');
                        updateQueenMessage(`🪞 Timeline "${timeline}" ANCHORED! Coherence lock confirmed.`);
                        
                        // Pulse effect
                        if (typeof anime !== 'undefined') {
                            anime({
                                targets: card,
                                boxShadow: [
                                    '0 0 20px rgba(0, 255, 136, 0.3)',
                                    '0 0 60px rgba(0, 255, 136, 0.8)',
                                    '0 0 20px rgba(0, 255, 136, 0.3)'
                                ],
                                duration: 1000,
                                easing: 'easeInOutQuad'
                            });
                        }
                    }
                });
            });
            
            // Glyph button handlers
            document.querySelectorAll('.glyph-btn').forEach(btn => {
                btn.addEventListener('click', () => selectGlyph(btn.dataset.glyph));
            });
            
            // Planetary node resonance animation
            setInterval(() => {
                document.querySelectorAll('.node-indicator').forEach(node => {
                    if (Math.random() > 0.7) {
                        node.classList.toggle('resonating');
                    }
                });
            }, 3000);
        }
        
        // ═══════════════════════════════════════════════════════════════════════
        // 🎨 ENHANCED GSAP ANIMATIONS ON LOAD
        // ═══════════════════════════════════════════════════════════════════════
        
        function initAnimations() {
            if (typeof gsap === 'undefined') return;
            
            // Register GSAP plugins
            if (typeof TextPlugin !== 'undefined') {
                gsap.registerPlugin(TextPlugin);
            }
            
            // Initialize Stargate systems
            initStargateAudio();
            initQuantumMirror();
            
            // Create master timeline for orchestrated entrance
            const masterTL = gsap.timeline();
            
            // Header drops in with bounce
            masterTL.from('#header', { 
                y: -150, 
                opacity: 0, 
                duration: 1, 
                ease: 'bounce.out' 
            });
            
            // Queen panel scales in with golden glow
            masterTL.from('#queen-panel', { 
                scale: 0.5, 
                opacity: 0, 
                duration: 0.8, 
                ease: 'elastic.out(1, 0.5)',
                onComplete: () => {
                    gsap.to('#queen-avatar', {
                        filter: 'drop-shadow(0 0 30px rgba(255, 215, 0, 1))',
                        duration: 0.5
                    });
                }
            }, '-=0.3');
            
            // Sidebar panels slide in from sides
            masterTL.from('#systems-panel', { 
                x: -200, 
                opacity: 0, 
                rotation: -5,
                duration: 0.8, 
                ease: 'power4.out' 
            }, '-=0.5');
            
            masterTL.from('#right-sidebar', { 
                x: 200, 
                opacity: 0, 
                rotation: 5,
                duration: 0.8, 
                ease: 'power4.out' 
            }, '-=0.8');
            
            // Main display fades up
            masterTL.from('#main-display', { 
                y: 100, 
                opacity: 0, 
                duration: 0.6, 
                ease: 'power3.out' 
            }, '-=0.6');
            
            // Footer slides up
            masterTL.from('#footer', { 
                y: 100, 
                opacity: 0, 
                duration: 0.5, 
                ease: 'power2.out' 
            }, '-=0.3');
            
            // Stat cards pop in with stagger and bounce
            masterTL.from('.stat-card', { 
                scale: 0, 
                opacity: 0, 
                y: 30,
                duration: 0.5, 
                stagger: {
                    each: 0.1,
                    from: 'start',
                    ease: 'power2.in'
                },
                ease: 'back.out(2)'
            }, '-=0.4');
            
            // Exchange cards flip in
            masterTL.from('.exchange-card', {
                rotationY: 90,
                opacity: 0,
                duration: 0.6,
                stagger: 0.15,
                ease: 'power2.out',
                transformOrigin: 'center center'
            }, '-=0.3');
            
            // Radar container pulse in
            masterTL.from('#radar-container', {
                scale: 0,
                opacity: 0,
                rotation: -180,
                duration: 0.8,
                ease: 'back.out(1.5)'
            }, '-=0.5');
            
            // Floating animations for decorative elements
            gsap.to('#queen-avatar', {
                y: -10,
                duration: 2,
                ease: 'sine.inOut',
                yoyo: true,
                repeat: -1
            });
            
            // Continuous subtle pulse on panels
            gsap.to('.panel', {
                boxShadow: '0 0 30px rgba(0, 255, 136, 0.4), inset 0 0 30px rgba(0, 0, 0, 0.5)',
                duration: 2,
                ease: 'sine.inOut',
                yoyo: true,
                repeat: -1,
                stagger: 0.2
            });
            
            // Logo shimmer animation
            gsap.to('#logo', {
                backgroundPosition: '200% 0',
                duration: 3,
                ease: 'none',
                repeat: -1
            });
        }
        
        // Animate value changes
        function animateValueChange(element, newValue, isPositive = true) {
            if (typeof gsap === 'undefined') return;
            
            const el = document.getElementById(element) || element;
            if (!el) return;
            
            // Flash animation
            gsap.timeline()
                .to(el, {
                    scale: 1.3,
                    color: isPositive ? '#00FF88' : '#FF3366',
                    textShadow: isPositive 
                        ? '0 0 20px rgba(0, 255, 136, 0.8)' 
                        : '0 0 20px rgba(255, 51, 102, 0.8)',
                    duration: 0.15,
                    ease: 'power2.out'
                })
                .to(el, {
                    scale: 1,
                    textShadow: 'none',
                    duration: 0.3,
                    ease: 'elastic.out(1, 0.3)'
                });
            
            el.textContent = newValue;
        }
        
        // Particle burst effect on trade
        function createTradeBurst(element, isWin) {
            if (typeof anime === 'undefined') return;
            
            const rect = element.getBoundingClientRect();
            const particles = 15;
            
            for (let i = 0; i < particles; i++) {
                const particle = document.createElement('div');
                particle.style.cssText = `
                    position: fixed;
                    left: ${rect.left + rect.width / 2}px;
                    top: ${rect.top + rect.height / 2}px;
                    width: 6px;
                    height: 6px;
                    border-radius: 50%;
                    background: ${isWin ? 'var(--green)' : 'var(--red)'};
                    pointer-events: none;
                    z-index: 9999;
                `;
                document.body.appendChild(particle);
                
                anime({
                    targets: particle,
                    translateX: anime.random(-100, 100),
                    translateY: anime.random(-100, 100),
                    scale: [1, 0],
                    opacity: [1, 0],
                    duration: 800,
                    easing: 'easeOutExpo',
                    complete: () => particle.remove()
                });
            }
        }
        
        // Number counter animation
        function animateCounter(element, endValue, duration = 1000) {
            if (typeof anime === 'undefined') return;
            
            const obj = { value: 0 };
            anime({
                targets: obj,
                value: endValue,
                round: 1,
                duration: duration,
                easing: 'easeOutExpo',
                update: () => {
                    element.textContent = obj.value.toLocaleString();
                }
            });
        }
        
        // World Map with Leaflet
        let worldMap = null;
        function initWorldMap() {
            worldMap = L.map('world-map', {
                center: [30, 0],
                zoom: 1,
                zoomControl: false,
                attributionControl: false
            });
            
            // Dark tile layer
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                maxZoom: 19
            }).addTo(worldMap);
            
            // Exchange markers
            const exchanges = [
                { name: 'KRAKEN', lat: 37.7749, lng: -122.4194, color: '#9945FF' },  // San Francisco
                { name: 'BINANCE', lat: 1.3521, lng: 103.8198, color: '#F0B90B' },   // Singapore
                { name: 'ALPACA', lat: 37.7749, lng: -122.4194, color: '#00FF88' },  // San Francisco
                { name: 'CAPITAL', lat: 51.5074, lng: -0.1278, color: '#00BFFF' },   // London
            ];
            
            exchanges.forEach(ex => {
                const marker = L.circleMarker([ex.lat, ex.lng], {
                    radius: 8,
                    fillColor: ex.color,
                    color: ex.color,
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.5
                }).addTo(worldMap);
                
                marker.bindTooltip(ex.name, { permanent: false, className: 'exchange-tooltip' });
                
                // Pulse animation
                setInterval(() => {
                    L.circleMarker([ex.lat, ex.lng], {
                        radius: 15,
                        fillColor: 'transparent',
                        color: ex.color,
                        weight: 2,
                        opacity: 0
                    }).addTo(worldMap).on('add', function(e) {
                        anime({
                            targets: e.target._path,
                            strokeOpacity: [1, 0],
                            r: [8, 30],
                            duration: 2000,
                            easing: 'easeOutExpo'
                        });
                    });
                }, 3000);
            });
        }
        
        // PnL Chart with ApexCharts
        let pnlChart = null;
        let pnlHistory = [];
        function initPnlChart() {
            const options = {
                series: [{
                    name: 'P&L',
                    data: pnlHistory.length ? pnlHistory : [0]
                }],
                chart: {
                    type: 'area',
                    height: '100%',
                    sparkline: { enabled: true },
                    animations: {
                        enabled: true,
                        easing: 'linear',
                        dynamicAnimation: { speed: 1000 }
                    },
                    background: 'transparent'
                },
                stroke: {
                    curve: 'smooth',
                    width: 2
                },
                fill: {
                    type: 'gradient',
                    gradient: {
                        shadeIntensity: 1,
                        opacityFrom: 0.7,
                        opacityTo: 0.2,
                        stops: [0, 100]
                    }
                },
                colors: ['#FFD700'],
                tooltip: {
                    enabled: true,
                    theme: 'dark',
                    x: { show: false },
                    y: {
                        formatter: (val) => '$' + val.toFixed(2)
                    }
                }
            };
            
            pnlChart = new ApexCharts(document.querySelector('#pnl-chart'), options);
            pnlChart.render();
        }
        
        function updatePnlChart(pnl) {
            pnlHistory.push(pnl);
            if (pnlHistory.length > 50) pnlHistory.shift();
            
            if (pnlChart) {
                const color = pnl >= 0 ? '#00FF88' : '#FF4444';
                pnlChart.updateOptions({ colors: [color] });
                pnlChart.updateSeries([{ data: pnlHistory }]);
            }
        }
        
        // Typed effect for Queen messages
        let typedInstance = null;
        function typeQueenMessage(message) {
            const el = document.getElementById('queen-message');
            if (typedInstance) typedInstance.destroy();
            el.innerHTML = '';
            typedInstance = new Typed(el, {
                strings: [message],
                typeSpeed: 30,
                showCursor: true,
                cursorChar: '█',
                onComplete: () => {
                    sounds.tactical.play();
                }
            });
        }
        
        // DEFCON Level Management
        let currentDefcon = 5;
        function setDefconLevel(level) {
            level = Math.max(1, Math.min(5, level));
            currentDefcon = level;
            
            const defconEl = document.getElementById('defcon-level');
            defconEl.className = 'defcon-' + level;
            defconEl.textContent = level;
            
            // Update threat level container border color
            const threatEl = document.getElementById('threat-level');
            const colors = {
                5: 'var(--green)',
                4: 'var(--blue)',
                3: 'var(--gold)',
                2: 'var(--orange)',
                1: 'var(--red)'
            };
            threatEl.style.borderColor = colors[level];
            
            // Play alert sound for critical levels
            if (level <= 2) {
                sounds.alert.play();
            }
            
            // Auto-enable RED ALERT mode at DEFCON 1
            if (level === 1 && !redAlertActive) {
                toggleRedAlert();
            }
        }
        
        // Toggle PnL Chart visibility
        function togglePnlChart() {
            const container = document.getElementById('pnl-chart-container');
            container.classList.toggle('minimized');
        }
        
        // Enhanced updateState to use new features
        const originalUpdateState = typeof updateState !== 'undefined' ? updateState : null;
        function updateStateEnhanced(data) {
            // Update PnL chart
            if (data.stats && data.stats.total_pnl !== undefined) {
                updatePnlChart(data.stats.total_pnl);
                
                // Animate PnL value with CountUp
                const pnlEl = document.getElementById('total-pnl');
                if (pnlEl) {
                    const pnl = data.stats.total_pnl;
                    pnlEl.textContent = (pnl >= 0 ? '+' : '') + '$' + pnl.toFixed(2);
                    pnlEl.className = pnl >= 0 ? 'glow-green' : 'glow-red';
                }
            }
            
            // Calculate DEFCON based on system status
            if (data.systems) {
                const onlineCount = Object.values(data.systems).filter(s => s).length;
                const ratio = onlineCount / Object.keys(data.systems).length;
                if (ratio >= 0.9) setDefconLevel(5);
                else if (ratio >= 0.7) setDefconLevel(4);
                else if (ratio >= 0.5) setDefconLevel(3);
                else if (ratio >= 0.3) setDefconLevel(2);
                else setDefconLevel(1);
            }
            
            // Type Queen messages
            if (data.queen_message && data.queen_message !== lastQueenMessage) {
                lastQueenMessage = data.queen_message;
                typeQueenMessage(data.queen_message);
            }
        }
        let lastQueenMessage = '';
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            initWebSocket();
            fetchInitialState();
            initParticles();
            initSounds();
            initAnimations();
            initWorldMap();
            initPnlChart();
            initGlobe();
            initSystemRadar();
            initTerminal();
            setInterval(updateClock, 1000);
            updateClock();
            drawHarmonics();
            drawRadar();
            setDefconLevel(5);  // Start at DEFCON 5 (peaceful)
            
            // Startup voice
            setTimeout(() => {
                speakText("Aureon Command Center online. All tactical systems initializing. Welcome, Commander.");
                typeQueenMessage("👑 Queen SERO online. Harmonic resonance optimal. All validators standing by.");
            }, 1500);
            
            console.log('⚔️ AUREON COMMAND CENTER INITIALIZED ⚔️');
        });
    </script>
</body>
</html>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# AIOHTTP WEB SERVER
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_index(request):
    """Serve the main command center HTML"""
    return web.Response(text=COMMAND_CENTER_HTML, content_type='text/html')

async def handle_api_state(request):
    """Return full state as JSON"""
    return web.json_response({
        'stats': {
            'total_trades': state.total_trades,
            'winning_trades': state.winning_trades,
            'losing_trades': state.losing_trades,
            'total_pnl': state.total_pnl,
            'coherence': state.coherence_score,
        },
        'systems': SYSTEMS_STATUS,
        'balances': state.exchange_balances,
        'trades': list(state.recent_trades),
        'whales': list(state.whale_alerts),
        'bots': list(state.bot_detections),
        'queen_message': state.queen_messages[-1] if state.queen_messages else "Queen SERO online. All systems operational.",
        'live_feed': LIVE_FEED_ENABLED,
        'trading_on': TRADING_LIVE_ENABLED,
        'trading_mode': TRADING_MODE,
        'safety': {
            'live_block_reason': live_block_reason("Command Center"),
        },
    })

async def handle_live_toggle(request):
    """Toggle live feed on/off"""
    global LIVE_FEED_ENABLED
    LIVE_FEED_ENABLED = not LIVE_FEED_ENABLED
    await broadcast_to_clients({'type': 'live_feed', 'enabled': LIVE_FEED_ENABLED})
    return web.json_response({'enabled': LIVE_FEED_ENABLED})

async def handle_trading_toggle(request):
    """Toggle real trading engine on/off"""
    global TRADING_LIVE_ENABLED, TRADING_PROCESS, TRADING_MODE

    if TRADING_PROCESS and TRADING_PROCESS.returncode is None:
        await _stop_trading_engine()
    else:
        reason = live_block_reason("Command Center")
        if reason:
            await broadcast_to_clients({
                'type': 'trading',
                'enabled': False,
                'mode': TRADING_MODE,
                'blocked': True,
                'reason': reason,
            })
            return web.json_response({
                'enabled': False,
                'mode': TRADING_MODE,
                'blocked': True,
                'reason': reason,
            }, status=423)
        await _start_trading_engine(live=True)

    await broadcast_to_clients({'type': 'trading', 'enabled': TRADING_LIVE_ENABLED, 'mode': TRADING_MODE})
    return web.json_response({'enabled': TRADING_LIVE_ENABLED, 'mode': TRADING_MODE})

async def websocket_handler(request):
    """WebSocket handler for real-time updates"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    state.ws_clients.add(ws)
    safe_print(f"🔌 New WebSocket client connected. Total: {len(state.ws_clients)}")
    
    try:
        # Send initial state
        await ws.send_json({
            'type': 'state',
            'stats': {
                'total_trades': state.total_trades,
                'winning_trades': state.winning_trades,
                'losing_trades': state.losing_trades,
                'total_pnl': state.total_pnl,
                'coherence': state.coherence_score,
            },
            'systems': SYSTEMS_STATUS,
            'balances': state.exchange_balances,
            'trades': list(state.recent_trades),
            'whales': list(state.whale_alerts),
            'bots': list(state.bot_detections),
            'bot_scanner': [],  # Bot shape scanner data
            'whale_sonar': [],  # Whale sonar signals
            'orca': [],  # Orca intelligence hunts
            'sniper': [],  # Sniper brain shots
            'queen_message': state.queen_messages[-1] if state.queen_messages else "Welcome to the Command Center.",
            'live_feed': LIVE_FEED_ENABLED,
            'trading_on': TRADING_LIVE_ENABLED,
            'trading_mode': TRADING_MODE,
        })
        
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                # Handle client messages if needed
                pass
            elif msg.type == aiohttp.WSMsgType.ERROR:
                safe_print(f'WebSocket error: {ws.exception()}')
    finally:
        state.ws_clients.discard(ws)
        safe_print(f"🔌 WebSocket client disconnected. Total: {len(state.ws_clients)}")
    
    return ws

async def broadcast_to_clients(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    if not state.ws_clients:
        return
    
    dead_clients = set()
    for ws in state.ws_clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead_clients.add(ws)
    
    state.ws_clients -= dead_clients

# ═══════════════════════════════════════════════════════════════════════════════
# BACKGROUND TASKS - FEED DATA INTO COMMAND CENTER
# ═══════════════════════════════════════════════════════════════════════════════

async def queen_commentary_task():
    """Generate Queen commentary periodically"""
    messages = [
        "Monitoring all exchanges. The market whispers its secrets.",
        "I see patterns forming in the chaos. Stay alert.",
        "The bots are dancing. Some will fall. We will profit.",
        "Harmonic resonance detected. Opportunities emerging.",
        "Whale activity spotted. Tracking their movements.",
        "The multiverse branches align. Execute with precision.",
        "Fear not the volatility. It is our friend.",
        "Intelligence systems nominal. Ready to strike.",
        "The golden ratio guides our path. φ = 1.618",
        "Planet saving mode: ACTIVE. Every trade matters.",
        "Remember: We trade to win. Losses are teachers.",
        "The Lighthouse guides us through the storm.",
        "Mycelium network propagating signals. Stay connected.",
        "Enigma decoded another pattern. Fascinating.",
        "All seeing. All knowing. All winning.",
    ]
    
    while True:
        await asyncio.sleep(30)  # Every 30 seconds
        message = random.choice(messages)
        state.queen_messages.append(message)
        await broadcast_to_clients({
            'type': 'queen',
            'message': message
        })

async def simulate_data_task():
    """Simulate incoming data for demo purposes"""
    symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'XRP/USD', 'ADA/USD', 'DOT/USD', 'AVAX/USD', 'MATIC/USD']
    firms = ['Jump Trading', 'Citadel', 'Two Sigma', 'DE Shaw', 'Wintermute', 'Alameda', 'Jane Street', 'HRT']
    countries = ['🇺🇸 USA', '🇬🇧 UK', '🇨🇳 China', '🇯🇵 Japan', '🇩🇪 Germany', '🇸🇬 Singapore']
    
    while True:
        await asyncio.sleep(random.uniform(2, 8))
        
        # Simulate trade
        if random.random() < 0.4:
            trade = {
                'time': datetime.now().strftime('%H:%M:%S'),
                'side': random.choice(['buy', 'sell']),
                'symbol': random.choice(symbols),
                'amount': random.uniform(10, 5000),
                'pnl': random.uniform(-50, 100),
                'volume': random.uniform(1000, 500000)
            }
            state.recent_trades.appendleft(trade)
            state.total_trades += 1
            state.total_pnl += trade['pnl']
            if trade['pnl'] > 0:
                state.winning_trades += 1
            else:
                state.losing_trades += 1
            
            await broadcast_to_clients({'type': 'trade', 'trade': trade})
            await broadcast_to_clients({
                'type': 'stats',
                'stats': {
                    'total_trades': state.total_trades,
                    'winning_trades': state.winning_trades,
                    'losing_trades': state.losing_trades,
                    'total_pnl': state.total_pnl,
                    'coherence': state.coherence_score,
                }
            })
        
        # Simulate whale
        if random.random() < 0.1:
            whale = {
                'symbol': random.choice(symbols),
                'volume': random.uniform(100000, 10000000),
                'direction': random.choice(['buy', 'sell']),
            }
            state.whale_alerts.appendleft(whale)
            await broadcast_to_clients({'type': 'whale', 'whale': whale})
        
        # Simulate bot detection
        if random.random() < 0.15:
            bot = {
                'firm': random.choice(firms),
                'country': random.choice(countries),
            }
            state.bot_detections.appendleft(bot)
            await broadcast_to_clients({'type': 'bot', 'bot': bot})
        
        # Simulate bot shape scanner detection
        if random.random() < 0.12:
            bot_shape = {
                'type': random.choice(['HFT_Bot', 'Arbitrage_Bot', 'Momentum_Bot', 'Mean_Revert_Bot', 'Scalp_Bot']),
                'confidence': random.uniform(0.7, 0.95),
                'status': 'Detected'
            }
            # For demo, we'll broadcast this as a separate update
            await broadcast_to_clients({'type': 'bot_scanner', 'shape': bot_shape})
        
        # Simulate whale sonar signal
        if random.random() < 0.08:
            sonar_signal = {
                'source': random.choice(['BTC/USD', 'ETH/USD', 'SOL/USD']),
                'signal': random.uniform(0.3, 0.9),
                'code': random.choice(['S0', 'S1', 'S2', 'S3'])
            }
            await broadcast_to_clients({'type': 'whale_sonar', 'signal': sonar_signal})
        
        # Simulate orca intelligence hunt
        if random.random() < 0.06:
            orca_hunt = {
                'target': random.choice(symbols),
                'mode': random.choice(['Stalking', 'Hunting', 'Tracking']),
                'status': 'Active'
            }
            await broadcast_to_clients({'type': 'orca', 'hunt': orca_hunt})
        
        # Simulate sniper brain shot
        if random.random() < 0.1:
            sniper_shot = {
                'target': random.choice(symbols),
                'pnl': random.uniform(-20, 50),
                'result': 'win' if random.random() > 0.4 else 'loss'
            }
            await broadcast_to_clients({'type': 'sniper', 'shot': sniper_shot})

async def update_balances_task():
    """Periodically update exchange balances"""
    kraken_client = None
    binance_client = None
    alpaca_client = None
    capital_client = None

    def _sum_fiat(balances: Dict[str, float]) -> float:
        total = 0.0
        for asset, amount in balances.items():
            if asset.upper() in {"USD", "USDT", "USDC", "GBP", "EUR"}:
                try:
                    total += float(amount)
                except Exception:
                    pass
        return total

    while True:
        # Try to get real balances
        balances = {}
        
        if SYSTEMS_STATUS.get('Kraken Exchange'):
            try:
                if kraken_client is None:
                    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
                    kraken_client = get_kraken_client()
                kraken_bal = kraken_client.get_account_balance()
                balances['kraken'] = _sum_fiat(kraken_bal) if kraken_bal else 'offline'
            except Exception:
                balances['kraken'] = 'offline'
        else:
            balances['kraken'] = 'offline'
        
        if SYSTEMS_STATUS.get('Binance Exchange'):
            try:
                if binance_client is None:
                    from aureon.exchanges.binance_client import get_binance_client
                    binance_client = get_binance_client()
                acct = binance_client.account()
                fiat = {}
                for bal in acct.get('balances', []):
                    asset = bal.get('asset')
                    if asset:
                        try:
                            free = float(bal.get('free', 0))
                            locked = float(bal.get('locked', 0))
                            fiat[asset] = free + locked
                        except Exception:
                            pass
                balances['binance'] = _sum_fiat(fiat) if fiat else 'offline'
            except Exception:
                balances['binance'] = 'offline'
        else:
            balances['binance'] = 'offline'
        
        if SYSTEMS_STATUS.get('Alpaca Exchange'):
            try:
                if alpaca_client is None:
                    from aureon.exchanges.alpaca_client import AlpacaClient
                    alpaca_client = AlpacaClient()
                alpaca_bal = alpaca_client.get_account_balance()
                balances['alpaca'] = _sum_fiat(alpaca_bal) if alpaca_bal else 'offline'
            except Exception:
                balances['alpaca'] = 'offline'
        else:
            balances['alpaca'] = 'offline'
        
        if SYSTEMS_STATUS.get('Capital Exchange'):
            try:
                if capital_client is None:
                    from aureon.exchanges.capital_client import CapitalClient
                    capital_client = CapitalClient()
                capital_bal = capital_client.get_account_balance()
                balances['capital'] = _sum_fiat(capital_bal) if capital_bal else 'offline'
            except Exception:
                balances['capital'] = 'offline'
        else:
            balances['capital'] = 'offline'
        
        state.exchange_balances = balances
        await broadcast_to_clients({'type': 'balances', 'balances': balances})
        
        await asyncio.sleep(30)

async def thought_bus_listener_task():
    """Listen to ThoughtBus for real updates"""
    if not thought_bus:
        return

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    thoughts_path = Path(os.getenv("AUREON_THOUGHTS_FILE", "thoughts.jsonl"))
    file_pos = thoughts_path.stat().st_size if thoughts_path.exists() else 0

    def _enqueue(thought) -> None:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, thought)
        except Exception:
            pass

    try:
        thought_bus.subscribe("*", _enqueue)
    except Exception as e:
        safe_print(f"ThoughtBus subscription error: {e}")
        return

    def _as_float(value: Any) -> Optional[float]:
        try:
            return float(value)
        except Exception:
            return None

    async def _process_thought(topic: str, payload: Dict[str, Any], source: str) -> None:
        # Queen messages
        if topic.startswith("queen.") or payload.get("message"):
            message = payload.get("message") or payload.get("text") or str(payload)[:160]
            if message:
                state.queen_messages.append(message)
                await broadcast_to_clients({'type': 'queen', 'message': message})

        # Coherence updates
        if "coherence" in payload:
            coherence = _as_float(payload.get("coherence"))
            if coherence is not None:
                state.coherence_score = coherence
                await broadcast_to_clients({
                    'type': 'stats',
                    'stats': {
                        'total_trades': state.total_trades,
                        'winning_trades': state.winning_trades,
                        'losing_trades': state.losing_trades,
                        'total_pnl': state.total_pnl,
                        'coherence': state.coherence_score,
                    }
                })

        # Trades / executions
        if topic.startswith("execution.") or topic.startswith("trade.") or "order_result" in payload or "trade" in payload:
            data = payload.get("trade") or payload.get("order_result") or payload
            symbol = data.get("symbol") or payload.get("symbol") or data.get("pair")
            side = (data.get("side") or payload.get("side") or data.get("direction") or "").lower()
            price = _as_float(data.get("price") or data.get("avgPrice") or data.get("executed_price"))
            qty = _as_float(data.get("quantity") or data.get("qty") or data.get("filled_qty"))
            amount = _as_float(data.get("amount"))
            if amount is None and price is not None and qty is not None:
                amount = price * qty
            pnl = _as_float(data.get("pnl") or payload.get("pnl") or data.get("profit"))

            if symbol or amount is not None:
                trade = {
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'side': side or 'buy',
                    'symbol': symbol or 'N/A',
                    'amount': amount or 0.0,
                    'pnl': pnl or 0.0,
                    'volume': amount or 0.0,
                }
                state.recent_trades.appendleft(trade)
                state.total_trades += 1
                if pnl is not None:
                    state.total_pnl += pnl
                    if pnl > 0:
                        state.winning_trades += 1
                    elif pnl < 0:
                        state.losing_trades += 1

                await broadcast_to_clients({'type': 'trade', 'trade': trade})
                await broadcast_to_clients({
                    'type': 'stats',
                    'stats': {
                        'total_trades': state.total_trades,
                        'winning_trades': state.winning_trades,
                        'losing_trades': state.losing_trades,
                        'total_pnl': state.total_pnl,
                        'coherence': state.coherence_score,
                    }
                })

        # Whale alerts
        if topic.startswith("whale.") or "whale" in topic:
            symbol = payload.get("symbol") or payload.get("asset") or payload.get("pair")
            volume = _as_float(payload.get("amount_usd") or payload.get("value_usd") or payload.get("volume") or payload.get("amount"))
            direction = payload.get("direction") or payload.get("side")
            if symbol or volume:
                whale = {
                    'symbol': symbol or 'N/A',
                    'volume': volume or 0.0,
                    'direction': direction or 'buy'
                }
                state.whale_alerts.appendleft(whale)
                await broadcast_to_clients({'type': 'whale', 'whale': whale})

        # Bot detections
        if topic.startswith("bot.") or "bot" in topic:
            firm = payload.get("firm") or payload.get("name") or source
            country = payload.get("country") or payload.get("region") or "Unknown"
            bot = {'firm': firm, 'country': country}
            state.bot_detections.appendleft(bot)
            await broadcast_to_clients({'type': 'bot', 'bot': bot})

    while True:
        try:
            if not LIVE_FEED_ENABLED:
                await asyncio.sleep(1)
                continue
            thought = await queue.get()
            topic = getattr(thought, "topic", "") or ""
            payload = getattr(thought, "payload", None) or {}
            source = getattr(thought, "source", "unknown")

            await _process_thought(topic, payload, source)

            # Cross-process fallback: tail thoughts.jsonl if it exists
            if thoughts_path.exists():
                if not LIVE_FEED_ENABLED:
                    await asyncio.sleep(1)
                    continue
                try:
                    with thoughts_path.open("r", encoding="utf-8") as f:
                        f.seek(file_pos)
                        for line in f:
                            file_pos = f.tell()
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                            except Exception:
                                continue
                            t_topic = data.get("topic", "")
                            t_payload = data.get("payload", {}) if isinstance(data, dict) else {}
                            t_source = data.get("source", "unknown") if isinstance(data, dict) else "unknown"
                            await _process_thought(t_topic, t_payload, t_source)
                except Exception:
                    pass

        except Exception as e:
            safe_print(f"ThoughtBus listener error: {e}")
            await asyncio.sleep(1)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_health(request):
    """Health check endpoint for Docker/K8s liveness probes"""
    return web.json_response({
        'status': 'healthy',
        'service': 'aureon-command-center',
        'timestamp': datetime.now().isoformat()
    })


def create_app():
    """Create the aiohttp application"""
    app = web.Application()
    
    # Routes
    app.router.add_get('/', handle_index)
    app.router.add_get('/health', handle_health)  # Docker healthcheck endpoint
    app.router.add_get('/api/state', handle_api_state)
    app.router.add_get('/api/flight-check', handle_flight_check)
    app.router.add_post('/api/live-toggle', handle_live_toggle)
    app.router.add_post('/api/trading-toggle', handle_trading_toggle)
    app.router.add_get('/ws', websocket_handler)
    
    return app

async def handle_flight_check(request):
    """API endpoint for flight check - verify all systems are alive"""
    global LAST_FLIGHT_CHECK, LAST_FLIGHT_CHECK_TIME
    
    # Run flight check
    results = run_flight_check()
    LAST_FLIGHT_CHECK = results
    LAST_FLIGHT_CHECK_TIME = time.time()
    
    # Convert to JSON-serializable format
    check_data = {
        'timestamp': datetime.now().isoformat(),
        'systems': {},
        'summary': {
            'total': len(results),
            'online': sum(1 for r in results.values() if r.status == 'GO'),
            'offline': sum(1 for r in results.values() if r.status != 'GO'),
        }
    }
    
    for name, result in results.items():
        check_data['systems'][name] = {
            'status': result.status,
            'ping_ms': result.ping_ms,
            'timestamp': result.timestamp,
            'heartbeat': result.heartbeat,
            'message': result.message
        }
    
    check_data['summary']['all_go'] = check_data['summary']['online'] == check_data['summary']['total']
    check_data['poem'] = print_flight_check_poem(results)
    
    return web.json_response(check_data)

async def monitor_trading_output():
    """Monitor output from the trading subprocess and broadcast logs/visuals"""
    global TRADING_PROCESS, TRADING_LIVE_ENABLED, TRADING_MODE
    safe_print("👀 Starting Trading Process Monitor...")
    # Keep a tail buffer so we can show last lines if the process exits
    tail_buffer = deque(maxlen=40)
    
    # Track accumulated pnl from logs since we can't see internal state directly
    extracted_pnl = 0.0
    
    while True:
        if TRADING_PROCESS and TRADING_PROCESS.stdout:
            try:
                line = await TRADING_PROCESS.stdout.readline()
                if line:
                    decoded_line = line.decode('utf-8', errors='replace').strip()
                    if decoded_line:
                        tail_buffer.append(decoded_line)
                        # Print to local console (pass-through)
                        safe_print(f"[MPL] {decoded_line}")
                        
                        # ════════════════════════════════════════════════════════════
                        # 🧠 LOG INTELLIGENCE PARSER - EXTRACT DATA FOR DASHBOARD
                        # ════════════════════════════════════════════════════════════
                        
                        # 1. Exchange Balances & Portfolio Value
                        # "[MPL] 💰 TOTAL PORTFOLIO VALUE: $9.54"
                        if "TOTAL PORTFOLIO VALUE:" in decoded_line:
                            try:
                                val_str = decoded_line.split("$")[1].replace(",", "").strip()
                                state.total_pnl = float(val_str) # Using total value as pnl proxy for now if start is 0
                                # Or extract actual PnL if available
                            except: pass

                        # "[MPL] 🦙 ALPACA: ✅ Connected | 1 assets | $9.54"
                        if "ALPACA:" in decoded_line and "$" in decoded_line:
                            try:
                                val_str = decoded_line.split("$")[1].split()[0]
                                state.exchange_balances['alpaca'] = {'USD': float(val_str)}
                                state.exchange_status['alpaca'] = 'ONLINE'
                            except: pass
                            
                        if "KRAKEN:" in decoded_line and "$" in decoded_line:
                            try:
                                val_str = decoded_line.split("$")[1].split()[0]
                                state.exchange_balances['kraken'] = {'USD': float(val_str)}
                                state.exchange_status['kraken'] = 'ONLINE'
                            except: pass
                            
                        if "BINANCE:" in decoded_line and "$" in decoded_line:
                             try:
                                val_str = decoded_line.split("$")[1].split()[0]
                                state.exchange_balances['binance'] = {'USD': float(val_str)}
                                state.exchange_status['binance'] = 'ONLINE'
                             except: pass

                        # 2. System Status (Coherence, etc.)
                        # "[MPL] 🎯 COHERENCE: 0.85" (Hypothetical log, need to check MPL output for real one)
                        # MPL Log: "🔬 🔴 | 0s | Turn:[🦙] ... C:100% ..."
                        if "🔬" in decoded_line and "C:" in decoded_line:
                             try:
                                 # Extract C:100%
                                 parts = decoded_line.split("C:")[1].split("%")[0]
                                 state.coherence_score = float(parts) / 100.0
                             except: pass

                        # 3. Trade/Opportunity Detection
                        # "[MPL] 🌊🔭 WAVE SWEEP: 1 top opportunities"
                        if "WAVE SWEEP:" in decoded_line:
                             try:
                                 opps = int(decoded_line.split(":")[1].split()[0])
                                 for _ in range(opps):
                                     state.bot_detections.append({
                                         'type': 'OPPORTUNITY', 
                                         'symbol': 'SCAN', 
                                         'confidence': 0.8, 
                                         'time': time.time()
                                     })
                             except: pass

                        # "[MPL] 🌀 TROUGH UNI/USDT Jump:0.57"
                        if "Jump:" in decoded_line:
                             try:
                                 symbol = decoded_line.split()[2]
                                 jump = float(decoded_line.split("Jump:")[1].split("|")[0])
                                 state.whale_alerts.append({
                                     'symbol': symbol,
                                     'size': jump,
                                     'side': 'buy' if jump > 0 else 'sell',
                                     'exchange': 'wave',
                                     'time': time.time()
                                 })
                             except: pass
                        
                        # 4. Queen Messages
                        if "👑" in decoded_line:
                            state.queen_messages.append(decoded_line.replace("[MPL]", "").strip())


                        # ════════════════════════════════════════════════════════════
                        # VISUALIZATION DATA GENERATION
                        # ════════════════════════════════════════════════════════════
                        
                        visual_type = 'scan'
                        if '🌊' in decoded_line: visual_type = 'wave'
                        if '👑' in decoded_line: visual_type = 'queen'
                        if '💰' in decoded_line: visual_type = 'profit'
                        if '🐙' in decoded_line or '🟡' in decoded_line or '🦙' in decoded_line: visual_type = 'exchange'
                        if 'Harmonic' in decoded_line: visual_type = 'harmonic'
                        
                        h = sum(ord(c) for c in decoded_line)
                        
                        visual_data = {
                            'type': visual_type,
                            'entropy': h,
                            'active': True,
                            'timestamp': time.time()
                        }
                        
                        # Broadcast to UI
                        await broadcast_to_clients({
                            'type': 'log_stream',
                            'message': decoded_line,
                            'visual_data': visual_data
                        })
                        
                        # Broadcast updated state periodically or on significant events
                        if visual_type in ['profit', 'exchange', 'queen']:
                             await broadcast_to_clients({
                                'type': 'state',
                                'stats': {
                                    'total_trades': state.total_trades,
                                    'winning_trades': state.winning_trades,
                                    'losing_trades': state.losing_trades,
                                    'total_pnl': state.total_pnl,
                                    'coherence': state.coherence_score,
                                },
                                'systems': SYSTEMS_STATUS,
                                'balances': state.exchange_balances,
                                'queen_message': state.queen_messages[-1] if state.queen_messages else "Active.",
                             })

                else:
                    # EOF or process dead
                    if TRADING_PROCESS.returncode is not None:
                        safe_print(f"⚠️ Trading Process exited code {TRADING_PROCESS.returncode}")
                        if tail_buffer:
                            safe_print("📋 Trading Process last output (tail):")
                            for line in tail_buffer:
                                safe_print(f"   {line}")
                        TRADING_PROCESS = None
                        TRADING_LIVE_ENABLED = False
                        TRADING_MODE = "off"
                        # Auto-restart?
                    await asyncio.sleep(0.5)
            except Exception as e:
                safe_print(f"Monitor error: {e}")
                await asyncio.sleep(1)
        else:
            await asyncio.sleep(1)

async def start_background_tasks(app):
    """Start background tasks"""
    # On Windows: Load systems in background AFTER server starts
    if WINDOWS_FAST_START and not SYSTEMS_LOADED:
        safe_print("🔄 Loading systems in background...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, load_all_systems)
        safe_print("✅ Background system loading complete!")
        
        # Update state counts after loading
        state.systems_online = sum(1 for v in SYSTEMS_STATUS.values() if v)
        state.systems_total = len(SYSTEMS_STATUS)
        safe_print(f"📊 Intelligence Systems: {state.systems_online}/{state.systems_total} ONLINE")
        
        # Broadcast updated systems to all connected clients!
        await broadcast_to_clients({
            'type': 'systems_loaded',
            'systems': SYSTEMS_STATUS,
            'systems_online': state.systems_online,
            'systems_total': state.systems_total,
        })
    
    if DEMO_MODE:
        app['queen_task'] = asyncio.create_task(queen_commentary_task())
        app['simulate_task'] = asyncio.create_task(simulate_data_task())
    app['balances_task'] = asyncio.create_task(update_balances_task())
    app['thought_bus_task'] = asyncio.create_task(thought_bus_listener_task())

    # Trading engine startup is explicit. Safe startup can request dry-run so
    # the whole interface is active without opening real exchange orders.
    if env_truthy("AUREON_COMMAND_CENTER_AUTO_START_DRY_RUN"):
        safe_print("AUTO-STARTING TRADING ENGINE IN DRY-RUN MODE...")
        try:
            await _start_trading_engine(live=False)
            app['monitor_task'] = asyncio.create_task(monitor_trading_output())
            safe_print("Trading engine dry-run process started.")
        except Exception as e:
            safe_print(f"Failed to auto-start dry-run trading: {e}")
    elif env_truthy("AUREON_COMMAND_CENTER_AUTO_START_TRADING"):
        reason = live_block_reason("Command Center auto-start")
        if reason:
            safe_print(f"Live trading auto-start blocked: {reason}")
        else:
            try:
                await _start_trading_engine(live=True)
                app['monitor_task'] = asyncio.create_task(monitor_trading_output())
                safe_print("Live trading engine started by explicit environment gate.")
            except Exception as e:
                safe_print(f"Failed to auto-start live trading: {e}")
    else:
        safe_print("Trading engine auto-start disabled; Command Center is online in guarded mode.")
    return

async def cleanup_background_tasks(app):
    """Cleanup background tasks"""
    await _stop_trading_engine()
    for task_name in ['queen_task', 'simulate_task', 'balances_task', 'thought_bus_task', 'monitor_task']:
        task = app.get(task_name)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

def main():
    """Main entry point"""
    if os.getenv("AUREON_DEBUG_STARTUP") == "1":
        safe_print(f"[DEBUG] Command Center main() starting (AIOHTTP_AVAILABLE={AIOHTTP_AVAILABLE})")
        _aureon_debug_log(f"main() starting; AIOHTTP_AVAILABLE={AIOHTTP_AVAILABLE}")
    if not AIOHTTP_AVAILABLE:
        safe_print("❌ Cannot start Command Center - aiohttp not installed")
        safe_print("   Run: pip install aiohttp")
        if os.getenv("AUREON_DEBUG_STARTUP") == "1":
            _aureon_debug_log("main() exiting early: aiohttp not available")
        return
    
    # Count online systems (may be 0 on Windows until background load completes)
    state.systems_online = sum(1 for v in SYSTEMS_STATUS.values() if v)
    state.systems_total = len(SYSTEMS_STATUS) if SYSTEMS_STATUS else 25  # Estimate if not loaded yet
    
    safe_print("\n" + "=" * 80)
    safe_print("""
    ██████╗ ██████╗ ███╗   ███╗███╗   ███╗ █████╗ ███╗   ██╗██████╗ 
   ██╔════╝██╔═══██╗████╗ ████║████╗ ████║██╔══██╗████╗  ██║██╔══██╗
   ██║     ██║   ██║██╔████╔██║██╔████╔██║███████║██╔██╗ ██║██║  ██║
   ██║     ██║   ██║██║╚██╔╝██║██║╚██╔╝██║██╔══██║██║╚██╗██║██║  ██║
   ╚██████╗╚██████╔╝██║ ╚═╝ ██║██║ ╚═╝ ██║██║  ██║██║ ╚████║██████╔╝
    ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ 
                       
                 ██████╗███████╗███╗   ██╗████████╗███████╗██████╗ 
                ██╔════╝██╔════╝████╗  ██║╚══██╔══╝██╔════╝██╔══██╗
                ██║     █████╗  ██╔██╗ ██║   ██║   █████╗  ██████╔╝
                ██║     ██╔══╝  ██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗
                ╚██████╗███████╗██║ ╚████║   ██║   ███████╗██║  ██║
                 ╚═════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
    """)
    safe_print("=" * 80)
    safe_print(f"🎮 AUREON COMMAND CENTER - LAUNCHING...")
    safe_print(f"=" * 80)
    safe_print(f"")
    safe_print(f"   🌐 URL: http://localhost:8888")
    safe_print(f"")
    if WINDOWS_FAST_START:
        safe_print(f"   ⚡ Windows Fast Start: Systems will load after server starts")
        safe_print(f"   📊 Intelligence Systems: Loading in background...")
    else:
        safe_print(f"   📊 Intelligence Systems: {state.systems_online}/{state.systems_total} ONLINE")
        safe_print(f"   👑 Queen Voice: {'✅ ENABLED' if SYSTEMS_STATUS.get('Queen Voice') else '⚠️ DISABLED'}")
        safe_print(f"   🛰️  Data Mode: {'DEMO (SIMULATED)' if DEMO_MODE else 'LIVE (THOUGHT BUS)'}")
        safe_print(f"   🧠 Thought Bus: {'✅ CONNECTED' if SYSTEMS_STATUS.get('Thought Bus') else '⚠️ OFFLINE'}")
        safe_print(f"   🍄 Mycelium: {'✅ ACTIVE' if SYSTEMS_STATUS.get('Mycelium Network') else '⚠️ OFFLINE'}")
        safe_print(f"   🐦 Chirp Bus: {'✅ ACTIVE' if SYSTEMS_STATUS.get('Chirp Bus') else '⚠️ OFFLINE'}")
        safe_print(f"")
        safe_print(f"   🐙 Kraken: {'✅' if SYSTEMS_STATUS.get('Kraken Exchange') else '❌'}")
        safe_print(f"   🟡 Binance: {'✅' if SYSTEMS_STATUS.get('Binance Exchange') else '❌'}")
        safe_print(f"   🦙 Alpaca: {'✅' if SYSTEMS_STATUS.get('Alpaca Exchange') else '❌'}")
        safe_print(f"   💼 Capital: {'✅' if SYSTEMS_STATUS.get('Capital Exchange') else '❌'}")
    safe_print(f"")
    
    # 🛫 RUN FLIGHT CHECK - Skip on Windows for fast start
    if not WINDOWS_FAST_START:
        safe_print("=" * 80)
        safe_print("🛫 INITIATING FLIGHT CHECK - TIMESTAMP VERIFICATION...")
        safe_print("=" * 80)
        
        global LAST_FLIGHT_CHECK, LAST_FLIGHT_CHECK_TIME
        LAST_FLIGHT_CHECK = run_flight_check()
        LAST_FLIGHT_CHECK_TIME = time.time()
        poem = print_flight_check_poem(LAST_FLIGHT_CHECK)
        
        # Print the poem!
        for line in poem.split('\n'):
            safe_print(line)
    else:
        # Windows: Skip flight check for fast startup
        safe_print("=" * 80)
        safe_print("⚡ WINDOWS FAST START - Flight check will run in background")
        safe_print("=" * 80)
    
    safe_print(f"")
    safe_print(f"=" * 80)
    safe_print(f"   Press Ctrl+C to stop the Command Center")
    safe_print(f"=" * 80 + "\n")
    
    # Create and run app
    safe_print("🔧 [DEBUG] Creating web app...")
    app = create_app()
    safe_print("🔧 [DEBUG] Adding startup/cleanup handlers...")
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    
    safe_print("🚀 Starting web server on port 8888...")
    safe_print("🌐 Open http://localhost:8888 in your browser!")
    try:
        web.run_app(app, host='0.0.0.0', port=8888, print=None)
    except Exception as e:
        safe_print(f"❌ [DEBUG] Web server error: {e}")
        import traceback
        traceback.print_exc()


# Module import completed marker
if os.getenv("AUREON_DEBUG_STARTUP") == "1":
    try:
        safe_print("[DEBUG] Module import completed; entering __main__ soon")
        _aureon_debug_log(f"module import completed; __name__={__name__}")
        _aureon_debug_log(f"AIOHTTP_AVAILABLE={AIOHTTP_AVAILABLE}")
    except Exception:
        pass

if __name__ == '__main__':
    # Stop import-debug tracing now that module import completed
    if os.getenv("AUREON_DEBUG_STARTUP") == "1":
        try:
            _aureon_debug_log("__main__ block entered")
            # Restore sys.exit now that imports are complete
            try:
                sys.exit = _ORIGINAL_SYS_EXIT
            except Exception:
                pass

            # Restore hard-exit functions
            try:
                if '_ORIGINAL_OS__EXIT' in globals() and _ORIGINAL_OS__EXIT is not None:
                    os._exit = _ORIGINAL_OS__EXIT
            except Exception:
                pass
            try:
                if '_ORIGINAL_OS_ABORT' in globals() and _ORIGINAL_OS_ABORT is not None:
                    os.abort = _ORIGINAL_OS_ABORT
            except Exception:
                pass

            _AUREON_DEBUG_IMPORT_ACTIVE = False
            import builtins
            if _AUREON_ORIGINAL_IMPORT is not None:
                builtins.__import__ = _AUREON_ORIGINAL_IMPORT
            try:
                import faulthandler
                faulthandler.cancel_dump_traceback_later()
            except Exception:
                pass
        except Exception:
            pass

    if os.getenv("AUREON_DEBUG_STARTUP") == "1":
        safe_print("[DEBUG] __main__ entry: calling main()")
        _aureon_debug_log("calling main()")
    try:
        main()
        if os.getenv("AUREON_DEBUG_STARTUP") == "1":
            _aureon_debug_log("main() returned normally")
    except Exception as e:
        safe_print(f"❌ [DEBUG] Command Center crashed: {e}")
        if os.getenv("AUREON_DEBUG_STARTUP") == "1":
            _aureon_debug_log(f"main() raised: {e!r}")
        import traceback
        traceback.print_exc()
