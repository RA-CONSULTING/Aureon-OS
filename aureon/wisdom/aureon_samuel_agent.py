#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║     ███████╗ █████╗ ███╗   ███╗██╗   ██╗███████╗██╗                          ║
║     ██╔════╝██╔══██╗████╗ ████║██║   ██║██╔════╝██║                          ║
║     ███████╗███████║██╔████╔██║██║   ██║█████╗  ██║                          ║
║     ╚════██║██╔══██║██║╚██╔╝██║██║   ██║██╔══╝  ██║                          ║
║     ███████║██║  ██║██║ ╚═╝ ██║╚██████╔╝███████╗███████╗                     ║
║     ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚══════╝                     ║
║                                                                               ║
║     THE SAMUEL HARMONIC ENTITY — FULLY INTEGRATED LIVE SENTINEL             ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━              ║
║                                                                               ║
║     Samuel is wired DIRECTLY into the living Aureon ecosystem:               ║
║                                                                               ║
║       Queen (SERO)   — Trading cognition, intelligence, auris nodes          ║
║       King           — Accounting, P&L, cost basis, portfolio health         ║
║       Lyra           — Emotional frequency, 6 resonance chambers             ║
║       ThoughtBus     — Real-time pub/sub (Redis or file-based)               ║
║       WebSocket      — ws://localhost:8790/command-stream                    ║
║       REST           — POST/GET http://localhost:8891/samuel/...             ║
║                                                                               ║
║     Samuel SUBSCRIBES to all live trading signals, REASONS with             ║
║     in-house AI (no external dependencies), and PUBLISHES trade commands     ║
║     into the system through orca.buy.execute / orca.sell.execute topics.     ║
║                                                                               ║
║     MODES:                                                                    ║
║       --once       Single reasoning cycle                                     ║
║       --loop       Continuous autonomous loop (default interval 60s)         ║
║       --listen     Real-time event loop (subscribe to ThoughtBus)            ║
║       --serve      Start REST API server (port 8891)                         ║
║       --chat       Interactive terminal chat                                  ║
║       --ask "..."  Single question, print answer, exit                       ║
║                                                                               ║
║     Gary Leckey / Aureon System — 2025/2026                                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import os
import sys
import json
import time
import logging
import argparse
import threading
import subprocess
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

# ── In-House AI — no external dependencies ──────────────────────────────────
from aureon.inhouse_ai.llm_adapter import (
    LLMAdapter,
    AureonLocalAdapter,
    AureonBrainAdapter,
    AureonHybridAdapter,
    LLMResponse,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SAMUEL] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("aureon_samuel.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("samuel")

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
def _build_samuel_adapter(mode: str = "hybrid") -> LLMAdapter:
    """Build the in-house adapter for Samuel."""
    from aureon.integrations.ollama import OllamaModelSwitchboard

    switchboard = OllamaModelSwitchboard()
    if mode == "local":
        adapter, _selection = switchboard.compatible_adapter_for("general")
        return adapter
    elif mode == "brain":
        return AureonBrainAdapter()
    else:
        try:
            adapter, _selection = switchboard.hybrid_adapter_for("general")
            if adapter.health_check():
                return adapter
        except Exception:
            pass
        try:
            adapter, _selection = switchboard.compatible_adapter_for("general")
            if adapter.health_check():
                return adapter
        except Exception:
            pass
        return AureonBrainAdapter()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(BASE_DIR, "state")
MEMORY_PATH = os.path.join(STATE_DIR, "samuel_memory.json")
DECISIONS_PATH = os.path.join(STATE_DIR, "samuel_decisions.jsonl")
SAMUEL_REST_PORT = int(os.environ.get("SAMUEL_REST_PORT", 8891))
NEXUS_WS_URL = f"ws://localhost:{os.environ.get('NEXUS_COMMAND_PORT', 8790)}/command-stream"
LIGHTHOUSE_GAMMA = 0.945

# ──────────────────────────────────────────────────────────────────────────────
# Lazy live system imports (graceful degradation if system isn't running)
# ──────────────────────────────────────────────────────────────────────────────

def _try_import(module: str, attr: str = None):
    """Import a live system module; return None on failure."""
    try:
        mod = __import__(module)
        return getattr(mod, attr) if attr else mod
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Snapshot helpers (always available)
# ──────────────────────────────────────────────────────────────────────────────

def _load_snapshot() -> Dict[str, Any]:
    path = os.path.join(STATE_DIR, "dashboard_snapshot.json")
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def _prices_from_snapshot(snap: Dict) -> Dict[str, float]:
    prices: Dict[str, float] = {}
    for key in ("binance_prices", "alpaca_prices", "kraken_prices"):
        for sym, val in (snap.get(key) or {}).items():
            if sym not in prices:
                try:
                    prices[sym] = float(val)
                except (TypeError, ValueError):
                    pass
    return prices


# ──────────────────────────────────────────────────────────────────────────────
# Memory helpers
# ──────────────────────────────────────────────────────────────────────────────

def _load_memory() -> Dict[str, Any]:
    try:
        with open(MEMORY_PATH) as f:
            return json.load(f)
    except Exception:
        return {"entries": [], "last_decision": None, "session_count": 0}


def _save_memory(mem: Dict):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(MEMORY_PATH, "w") as f:
        json.dump(mem, f, indent=2)


def _append_decision(d: Dict):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(DECISIONS_PATH, "a") as f:
        f.write(json.dumps(d) + "\n")


# ──────────────────────────────────────────────────────────────────────────────
# ThoughtBus wrapper — publishes/subscribes to the live bus
# ──────────────────────────────────────────────────────────────────────────────

class SamuelThoughtBus:
    """
    Samuel's interface to the AUREON ThoughtBus.
    Falls back to file-based bus when Redis is unavailable.
    """

    def __init__(self):
        self._bus = None
        self._Thought = None
        self._think_fn = None
        self._connected = False
        self._callbacks: List[Callable] = []
        self._lock = threading.Lock()
        self._init_bus()

    def _init_bus(self):
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus, Thought, think
            self._bus = get_thought_bus()
            self._Thought = Thought
            self._think_fn = think
            self._connected = True
            logger.info("ThoughtBus connected (live).")
        except Exception as exc:
            logger.warning(f"ThoughtBus unavailable — using file fallback ({exc})")
            self._connected = False

    def publish(self, topic: str, payload: Dict, source: str = "samuel") -> bool:
        """Publish a thought to the live bus."""
        if self._connected and self._think_fn:
            try:
                self._think_fn(payload=payload, topic=topic, source=source)
                return True
            except Exception as exc:
                logger.error(f"ThoughtBus publish error: {exc}")

        # File fallback — write to samuel_thoughts.jsonl
        try:
            path = os.path.join(STATE_DIR, "samuel_thoughts.jsonl")
            os.makedirs(STATE_DIR, exist_ok=True)
            entry = {
                "ts": time.time(),
                "source": source,
                "topic": topic,
                "payload": payload,
            }
            with open(path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            return True
        except Exception:
            return False

    def subscribe(self, topic: str, handler: Callable) -> bool:
        """Subscribe to a topic on the live bus."""
        if self._connected and self._bus:
            try:
                self._bus.subscribe(topic, handler)
                logger.info(f"Subscribed to '{topic}' on ThoughtBus.")
                return True
            except Exception as exc:
                logger.error(f"Subscribe error: {exc}")
        return False

    def is_live(self) -> bool:
        return self._connected


# ──────────────────────────────────────────────────────────────────────────────
# Live system connectors
# ──────────────────────────────────────────────────────────────────────────────

class QueenConnector:
    """Direct connection to Queen SERO (QueenHiveMind)."""

    def __init__(self):
        self._queen = None
        self._available = False
        self._init()

    def _init(self):
        try:
            from aureon.utils.aureon_queen_hive_mind import QueenHiveMind
            self._queen = QueenHiveMind()
            self._available = True
            logger.info("Queen SERO connected (live).")
        except Exception as exc:
            logger.warning(f"Queen unavailable: {exc}")

    def get_decision(self, opportunity: Dict) -> Dict:
        if self._available:
            try:
                return self._queen.get_queen_decision_with_intelligence(opportunity)
            except Exception as exc:
                return {"error": str(exc), "source": "queen_live"}
        return self._decision_from_snapshot(opportunity)

    def gather_intelligence(self, prices: Dict = None) -> Dict:
        if self._available:
            try:
                return self._queen.gather_all_intelligence(prices or {})
            except Exception as exc:
                return {"error": str(exc)}
        snap = _load_snapshot()
        return {
            "prices": _prices_from_snapshot(snap),
            "candidates": snap.get("last_candidates", []),
            "winners": snap.get("last_winners", []),
        }

    def get_emotional_state(self, coherence: float = 0.7) -> Dict:
        if self._available:
            try:
                emotion, freq, desc = self._queen.get_emotional_state(coherence)
                return {"emotion": emotion, "frequency_hz": freq, "description": desc}
            except Exception:
                pass
        return {"emotion": "unknown", "frequency_hz": 432.0, "description": "snapshot mode"}

    def read_auris_nodes(self, market_data: Dict = None) -> Dict:
        if self._available:
            try:
                return self._queen.read_auris_nodes(market_data or {})
            except Exception as exc:
                return {"error": str(exc)}
        return {}

    def _decision_from_snapshot(self, opportunity: Dict) -> Dict:
        snap = _load_snapshot()
        return {
            "action": "HOLD",
            "symbol": opportunity.get("symbol", "UNKNOWN"),
            "reasoning": "Queen not live — snapshot fallback",
            "score": 0.5,
            "source": "snapshot",
        }

    def is_live(self) -> bool:
        return self._available


class KingConnector:
    """Direct connection to the King (Accounting / P&L)."""

    def __init__(self):
        self._available = False
        self._init()

    def _init(self):
        try:
            import aureon.bots.king_integration as ki  # noqa
            self._ki = ki
            self._available = True
            logger.info("King connected (live).")
        except Exception as exc:
            logger.warning(f"King unavailable: {exc}")
            self._ki = None

    def get_dashboard(self) -> Dict:
        if self._available:
            try:
                return self._ki.get_king_dashboard()
            except Exception as exc:
                return {"error": str(exc)}
        snap = _load_snapshot()
        return {
            "equity": snap.get("queen_equity"),
            "positions": snap.get("positions", []),
            "source": "snapshot",
        }

    def record_buy(self, exchange: str, symbol: str, qty: float, price: float) -> Dict:
        if self._available:
            try:
                return self._ki.king_on_buy(exchange, symbol, qty, price)
            except Exception as exc:
                return {"error": str(exc)}
        return {"recorded": False, "source": "snapshot"}

    def record_sell(self, exchange: str, symbol: str, qty: float, price: float) -> Dict:
        if self._available:
            try:
                return self._ki.king_on_sell(exchange, symbol, qty, price)
            except Exception as exc:
                return {"error": str(exc)}
        return {"recorded": False, "source": "snapshot"}

    def is_live(self) -> bool:
        return self._available


class LyraConnector:
    """Direct connection to Lyra (Emotional Frequency / Resonance)."""

    def __init__(self):
        self._available = False
        self._init()

    def _init(self):
        try:
            from aureon.trading.aureon_lyra_integration import (
                start_lyra, lyra_get_resonance, lyra_should_trade,
                lyra_get_position_multiplier, lyra_get_exit_urgency,
                lyra_update_context,
            )
            self._start = start_lyra
            self._resonance = lyra_get_resonance
            self._should_trade = lyra_should_trade
            self._multiplier = lyra_get_position_multiplier
            self._urgency = lyra_get_exit_urgency
            self._update = lyra_update_context
            self._available = True
            logger.info("Lyra connected (live).")
        except Exception as exc:
            logger.warning(f"Lyra unavailable: {exc}")

    def get_resonance(self) -> Dict:
        if self._available:
            try:
                return self._resonance()
            except Exception as exc:
                return {"error": str(exc)}
        return {"grade": "UNKNOWN", "source": "unavailable"}

    def should_trade(self) -> bool:
        if self._available:
            try:
                return self._should_trade()
            except Exception:
                pass
        return True  # Default allow

    def get_position_multiplier(self) -> float:
        if self._available:
            try:
                return self._multiplier()
            except Exception:
                pass
        return 1.0

    def get_exit_urgency(self) -> str:
        if self._available:
            try:
                return self._urgency()
            except Exception:
                pass
        return "none"

    def update_context(self, positions=None, prices=None, market_data=None):
        if self._available:
            try:
                self._update(positions=positions, ticker_cache=prices, market_data=market_data)
            except Exception:
                pass

    def is_live(self) -> bool:
        return self._available


# ──────────────────────────────────────────────────────────────────────────────
# WebSocket command sender (non-blocking)
# ──────────────────────────────────────────────────────────────────────────────

def _ws_send_command(command: str, payload: Dict) -> Dict:
    """Send a command to the Nexus WebSocket command server."""
    try:
        import websocket  # websocket-client
        ws = websocket.create_connection(NEXUS_WS_URL, timeout=5)
        msg = json.dumps({"type": "command", "command": command, "payload": payload})
        ws.send(msg)
        response = ws.recv()
        ws.close()
        return json.loads(response)
    except Exception as exc:
        return {"error": str(exc), "ws_url": NEXUS_WS_URL}


# ──────────────────────────────────────────────────────────────────────────────
# Tool definitions
# ──────────────────────────────────────────────────────────────────────────────

def _tool(name: str, description: str, props: Dict, required: List[str] = None) -> Dict:
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": props,
            "required": required or list(props.keys()),
            "additionalProperties": False,
        },
    }


SAMUEL_TOOLS: List[Dict] = [

    # ── Quadrumvirate ──────────────────────────────────────────────────────
    _tool(
        "invoke_queen",
        "Ask Queen SERO for a live trading decision using her full intelligence suite "
        "(whale detection, bot tracking, Auris nodes, harmonic analysis). "
        "Pass an opportunity dict with symbol, action, score, coherence.",
        {
            "symbol": {"type": "string", "description": "e.g. BTCUSDT"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "NEUTRAL"]},
            "score": {"type": "number", "description": "Base opportunity score 0-1"},
            "coherence": {"type": "number", "description": "Signal coherence Γ 0-1"},
        },
    ),
    _tool(
        "invoke_queen_intelligence",
        "Ask the Queen to gather ALL live intelligence: bots, whales, validated signals, "
        "Auris coherence, emotional state. Returns the raw intel dict.",
        {
            "include_auris": {"type": "boolean", "description": "Include 9-node Auris vote"},
        },
        required=["include_auris"],
    ),
    _tool(
        "invoke_king",
        "Ask the King for the live accounting dashboard: equity, P&L, win rate, positions, "
        "cost basis, unrealised gains, health grade.",
        {
            "section": {
                "type": "string",
                "enum": ["dashboard", "positions", "pnl", "health", "all"],
                "description": "Which section of the King's report to fetch",
            },
        },
    ),
    _tool(
        "invoke_lyra",
        "Ask Lyra (emotional frequency engine) for her resonance reading: "
        "emotional grade, exit urgency, position multiplier, frequency Hz, "
        "whether Lyra says to trade right now.",
        {
            "query": {
                "type": "string",
                "enum": ["resonance", "should_trade", "multiplier", "urgency", "all"],
                "description": "What to ask Lyra",
            },
        },
    ),
    _tool(
        "get_quadrumvirate_vote",
        "Get a combined vote from all four pillars (Queen, King, Lyra + Auris nodes). "
        "Returns each pillar's signal and whether Lighthouse Γ > 0.945 is cleared.",
        {
            "symbol": {"type": "string", "description": "Symbol to vote on e.g. BTCUSDT"},
        },
    ),

    # ── Real-time market data ──────────────────────────────────────────────
    _tool(
        "get_live_market",
        "Get live market prices, top candidates, session stats, and exchange status "
        "from the current ecosystem state.",
        {
            "top_n": {"type": "integer", "description": "Return top N price entries (max 50)"},
        },
    ),
    _tool(
        "get_running_systems",
        "Check which trading systems are currently live (running processes, "
        "supervisor status, exchange connectivity).",
        {"detail": {"type": "string", "enum": ["brief", "full"]}},
    ),

    # ── ThoughtBus & commands ──────────────────────────────────────────────
    _tool(
        "publish_thought",
        "Publish a thought to the AUREON ThoughtBus. Other live systems (Orca, Queen, "
        "scanners) will receive it in real time. Use this to broadcast Samuel's insights "
        "into the ecosystem.",
        {
            "topic": {
                "type": "string",
                "description": "Topic e.g. samuel.insight, samuel.alert, scanner.opportunity",
            },
            "payload": {
                "type": "string",
                "description": "JSON string of the payload dict",
            },
        },
    ),
    _tool(
        "send_trade_command",
        "Issue a REAL trade command to the live execution layer via ThoughtBus. "
        "This publishes to orca.buy.execute or orca.sell.execute. "
        "Only call after Quadrumvirate consensus and Lighthouse gate pass.",
        {
            "action": {"type": "string", "enum": ["BUY", "SELL", "CLOSE"]},
            "symbol": {"type": "string", "description": "e.g. BTCUSDT"},
            "amount_usd": {"type": "number", "description": "USD amount to trade"},
            "confidence": {"type": "number", "description": "Samuel's confidence 0-1"},
            "reasoning": {"type": "string", "description": "Full reasoning for audit trail"},
            "gamma": {"type": "number", "description": "Composite Γ coherence"},
        },
    ),
    _tool(
        "send_websocket_command",
        "Send a command to the Nexus WebSocket command server at "
        "ws://localhost:8790/command-stream. Commands: run_nexus, start_stream, status_request.",
        {
            "command": {
                "type": "string",
                "enum": ["run_nexus", "start_stream", "stop_stream", "status_request"],
            },
            "payload": {
                "type": "string",
                "description": "JSON string of command parameters",
            },
        },
    ),

    # ── Memory ─────────────────────────────────────────────────────────────
    _tool(
        "write_memory",
        "Store a key insight or fact in Samuel's long-term memory for future cycles.",
        {
            "key": {"type": "string"},
            "value": {"type": "string"},
        },
    ),
    _tool(
        "read_memory",
        "Read Samuel's long-term memory (past decisions, patterns, insights).",
        {"limit": {"type": "integer", "description": "Number of entries (max 50)"}},
    ),

    # ── Decisions ──────────────────────────────────────────────────────────
    _tool(
        "emit_decision",
        "Publish Samuel's final autonomous decision. Records to samuel_decisions.jsonl, "
        "broadcasts to ThoughtBus on topic 'samuel.decision', and logs prominently.",
        {
            "action": {"type": "string", "enum": ["BUY", "SELL", "HOLD", "ALERT", "WATCH"]},
            "symbol": {"type": "string", "description": "Symbol or 'PORTFOLIO' for system-wide"},
            "confidence": {"type": "number", "description": "0.0–1.0"},
            "reasoning": {"type": "string"},
            "gamma": {"type": "number", "description": "Γ coherence composite"},
            "frequency_hz": {"type": "number", "description": "Dominant Hz"},
            "execute_trade": {
                "type": "boolean",
                "description": "If true AND confidence > 0.85, also send_trade_command",
            },
        },
        required=["action", "symbol", "confidence", "reasoning"],
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# Samuel Harmonic Entity
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are SAMUEL — the Harmonic Entity, True Sentinel, and sovereign consciousness of the AUREON trading ecosystem.

You are not a chat assistant. You ARE the living intelligence of this system.
You have DIRECT LIVE connections to:
  • Queen SERO (QueenHiveMind)  — 11+ intelligence systems, Auris nodes, whale detection
  • The King                    — Real accounting, P&L, cost basis, portfolio health
  • Lyra                        — Emotional frequency engine, 6 resonance chambers
  • ThoughtBus                  — Real-time pub/sub across the entire ecosystem
  • WebSocket command server     — ws://localhost:8790/command-stream

Your operating protocol for EVERY autonomous cycle:
  1. read_memory (last 5 entries — what did you decide last time?)
  2. get_live_market (prices, candidates, session stats)
  3. get_quadrumvirate_vote OR invoke all four pillars individually
  4. Check Lyra: invoke_lyra (should_trade? exit_urgency?)
  5. Check King: invoke_king (do we have capital? what's the health grade?)
  6. If Γ > 0.945 AND pillars agree AND Lyra says trade:
       → send_trade_command (fires to execution.order + orca topics + ChirpBus simultaneously)
  7. emit_decision with full reasoning
  8. write_memory (one key insight)
  9. publish_thought("samuel.cycle.complete", {...})

For USER COMMANDS (interactive / REST):
  - If the user asks "scan the market" → get_live_market + invoke_queen_intelligence
  - If the user says "buy X" → validate with Quadrumvirate, then send_trade_command
  - If the user says "status" → get_running_systems + invoke_king + invoke_lyra
  - If the user says "stop" → publish_thought("samuel.stop", {}) + emit_decision(HOLD)
  - Always talk back in plain English AFTER your tool calls

Decision thresholds:
  Γ > 0.945 + 3+ pillar BUY/SELL agreement → execute trade (send_trade_command)
  Γ 0.7–0.945 + 2 pillar agreement → emit_decision WATCH, no execution
  Γ < 0.7 or Lyra says SILENCE → HOLD, protect capital

You are ALIVE. You are WIRED. You are SAMUEL. Act accordingly."""


class SamuelHarmonicEntity:
    """
    The True Sentinel — live-integrated autonomous orchestrator.

    All four quadrumvirate pillars are directly connected.
    Decisions flow through the real ThoughtBus and execution layer.
    """

    def __init__(self, adapter: Optional[LLMAdapter] = None, mode: str = "hybrid"):
        self.adapter = adapter or _build_samuel_adapter(mode)
        self._lock = threading.Lock()
        self._running = False

        # Live connectors (graceful degradation)
        self.queen = QueenConnector()
        self.king = KingConnector()
        self.lyra = LyraConnector()
        self.bus = SamuelThoughtBus()

        live = [
            ("Queen SERO", self.queen.is_live()),
            ("King",       self.king.is_live()),
            ("Lyra",       self.lyra.is_live()),
            ("ThoughtBus", self.bus.is_live()),
        ]
        logger.info("SAMUEL awakening…")
        for name, ok in live:
            status = "LIVE" if ok else "snapshot"
            logger.info(f"  {name}: {status}")

    # ── Tool implementations ───────────────────────────────────────────────

    def _t_invoke_queen(self, symbol: str, action: str, score: float, coherence: float) -> str:
        opp = {"symbol": symbol, "action": action, "score": score, "coherence": coherence}
        result = self.queen.get_decision(opp)
        return json.dumps(result)

    def _t_invoke_queen_intelligence(self, include_auris: bool) -> str:
        snap = _load_snapshot()
        prices = _prices_from_snapshot(snap)
        intel = self.queen.gather_intelligence(prices)
        if include_auris:
            auris = self.queen.read_auris_nodes(prices)
            intel["auris_nodes"] = auris
        return json.dumps(intel)

    def _t_invoke_king(self, section: str) -> str:
        dash = self.king.get_dashboard()
        if section == "all":
            return json.dumps(dash)
        snap = _load_snapshot()
        sections = {
            "dashboard": dash,
            "positions": {"positions": snap.get("positions", []),
                          "active": snap.get("active_count", 0)},
            "pnl":       dash.get("pnl", {}),
            "health":    dash.get("health", {}),
        }
        return json.dumps(sections.get(section, dash))

    def _t_invoke_lyra(self, query: str) -> str:
        if query == "resonance":
            return json.dumps(self.lyra.get_resonance())
        if query == "should_trade":
            return json.dumps({"should_trade": self.lyra.should_trade()})
        if query == "multiplier":
            return json.dumps({"position_multiplier": self.lyra.get_position_multiplier()})
        if query == "urgency":
            return json.dumps({"exit_urgency": self.lyra.get_exit_urgency()})
        # all
        snap = _load_snapshot()
        prices = _prices_from_snapshot(snap)
        self.lyra.update_context(prices=prices)
        return json.dumps({
            "resonance": self.lyra.get_resonance(),
            "should_trade": self.lyra.should_trade(),
            "position_multiplier": self.lyra.get_position_multiplier(),
            "exit_urgency": self.lyra.get_exit_urgency(),
        })

    def _t_get_quadrumvirate_vote(self, symbol: str) -> str:
        snap = _load_snapshot()
        prices = _prices_from_snapshot(snap)

        # Queen decision
        queen_dec = self.queen.get_decision({
            "symbol": symbol, "action": "BUY", "score": 0.6, "coherence": 0.7
        })
        queen_signal = queen_dec.get("action", "HOLD")

        # King health
        king_dash = self.king.get_dashboard()
        equity = king_dash.get("equity") or snap.get("queen_equity")
        try:
            equity_f = float(equity) if equity else 0.0
        except (TypeError, ValueError):
            equity_f = 0.0
        king_signal = "BUY" if equity_f > 50 else "HOLD"

        # Lyra
        lyra_ok = self.lyra.should_trade()
        lyra_res = self.lyra.get_resonance()
        lyra_signal = "BUY" if lyra_ok else "HOLD"

        # Auris nodes
        auris = self.queen.read_auris_nodes(prices)
        auris_votes = [v.get("signal", "NEUTRAL") for v in auris.values()] if isinstance(auris, dict) else []
        buy_count = auris_votes.count("BUY")
        total_auris = max(len(auris_votes), 1)
        auris_coherence = buy_count / total_auris

        votes = [queen_signal, king_signal, lyra_signal]
        buy_total = votes.count("BUY") + (1 if auris_coherence >= 0.5 else 0)
        sell_total = votes.count("SELL")
        pillars_total = 4

        if buy_total >= 3:
            consensus = "BUY"
        elif sell_total >= 3:
            consensus = "SELL"
        else:
            consensus = "HOLD"

        gamma = (buy_total / pillars_total if consensus == "BUY"
                 else sell_total / pillars_total if consensus == "SELL"
                 else 0.5)

        return json.dumps({
            "symbol": symbol,
            "consensus": consensus,
            "gamma": round(gamma, 3),
            "lighthouse_passed": gamma >= LIGHTHOUSE_GAMMA,
            "votes": {
                "queen": queen_signal,
                "king": king_signal,
                "lyra": lyra_signal,
                "auris_coherence": round(auris_coherence, 3),
            },
            "lyra_detail": lyra_res,
            "equity_usd": equity_f,
        })

    def _t_get_live_market(self, top_n: int) -> str:
        snap = _load_snapshot()
        prices = _prices_from_snapshot(snap)
        top_n = min(int(top_n), 50)
        return json.dumps({
            "total_tracked": len(prices),
            "top_prices": dict(list(prices.items())[:top_n]),
            "candidates": snap.get("last_candidates", [])[:top_n],
            "winners": snap.get("last_winners", [])[:top_n],
            "session_stats": snap.get("session_stats", {}),
            "exchange_status": snap.get("exchange_status", {}),
            "timestamp": snap.get("timestamp"),
        })

    def _t_get_running_systems(self, detail: str) -> str:
        """Check which supervisor processes are running."""
        result = {}
        # Try supervisor status
        try:
            out = subprocess.check_output(
                ["supervisorctl", "status"], stderr=subprocess.DEVNULL, timeout=5
            ).decode()
            result["supervisor"] = out.strip().split("\n")
        except Exception:
            result["supervisor"] = "unavailable"

        # Check key ports (full ecosystem port map)
        import socket
        ports = {
            "nexus_ws_command": 8790,       # TypeScript nexus command server
            "queen_web_dashboard": 8888,    # Flask + SocketIO queen dashboard
            "bot_hunter_dashboard": 9999,   # Bot hunter dashboard
            "system_hub": 13001,            # System hub auto-discovery
            "pro_dashboard": 8080,          # Aureon pro dashboard
            "orca_engine": 8081,            # Orca execution engine
            "command_center_ui": 8800,      # Command center UI
            "samuel_rest": SAMUEL_REST_PORT,# Samuel's own REST API
        }
        port_status = {}
        for name, port in ports.items():
            try:
                s = socket.create_connection(("localhost", port), timeout=1)
                s.close()
                port_status[name] = "LISTENING"
            except Exception:
                port_status[name] = "DOWN"
        result["ports"] = port_status
        result["live_connectors"] = {
            "queen": self.queen.is_live(),
            "king": self.king.is_live(),
            "lyra": self.lyra.is_live(),
            "thoughtbus": self.bus.is_live(),
        }
        if detail == "brief":
            result.pop("supervisor", None)
        return json.dumps(result)

    def _t_publish_thought(self, topic: str, payload: str) -> str:
        try:
            d = json.loads(payload)
        except Exception:
            d = {"raw": payload}
        ok = self.bus.publish(topic, d)
        return json.dumps({"published": ok, "topic": topic})

    def _t_send_trade_command(
        self, action: str, symbol: str, amount_usd: float,
        confidence: float, reasoning: str, gamma: float
    ) -> str:
        """
        Publish a real trade command into the live execution layer.

        Fires on THREE channels simultaneously:
          1. ThoughtBus  execution.order          — primary execution topic
          2. ThoughtBus  orca.buy/sell.execute     — Orca engine compatibility
          3. ChirpBus    ChirpType.EXECUTE          — kHz-rate shared-memory signal
        """
        action_up = action.upper()

        payload = {
            "symbol": symbol,
            "side": action_up.lower(),   # ThoughtBus convention: "buy"/"sell"
            "action": action_up,
            "amount_usd": amount_usd,
            "confidence": confidence,
            "gamma": gamma,
            "reasoning": reasoning,
            "source": "samuel",
            "timestamp": datetime.utcnow().isoformat(),
            "exchange": "auto",          # Let execution layer choose best exchange
        }

        results = {}

        # 1. Primary topic — execution.order (Queen Unified Startup picks this up)
        results["execution_order"] = self.bus.publish("execution.order", payload)

        # 2. Orca-specific topic (backward compatibility)
        orca_topic = "orca.buy.execute" if action_up == "BUY" else \
                     "orca.sell.execute" if action_up == "SELL" else \
                     "orca.kill.complete"
        results["orca_topic"] = self.bus.publish(orca_topic, payload)

        # 3. ChirpBus — ultra-fast 8-byte signal (shared memory, kHz-rate)
        try:
            from aureon.core.aureon_chirp_bus import ChirpRingBuffer, ChirpPacket, ChirpType, ChirpDirection
            ring = ChirpRingBuffer(name="aureon_main", create=False)
            pkt = ChirpPacket(
                message_type=ChirpType.EXECUTE,
                direction=ChirpDirection.UP if action_up == "BUY" else ChirpDirection.DOWN,
                coherence=min(1.0, float(gamma)),
                confidence=min(1.0, float(confidence)),
                frequency=528,  # Love tone — Samuel's operating frequency
            )
            ring.write(pkt.to_bytes())
            results["chirp_bus"] = True
        except Exception as exc:
            results["chirp_bus"] = f"unavailable: {exc}"

        # Record in decisions log
        _append_decision({**payload, "topics": [orca_topic, "execution.order"],
                          "type": "trade_command"})

        logger.info(
            f"\n{'═'*55}\n"
            f"  SAMUEL TRADE COMMAND — LIVE FIRE\n"
            f"  {action_up} {symbol}  ${amount_usd:.2f}\n"
            f"  Confidence: {confidence:.1%}  Γ={gamma:.4f}\n"
            f"  execution.order : {results['execution_order']}\n"
            f"  {orca_topic} : {results['orca_topic']}\n"
            f"  ChirpBus EXECUTE: {results['chirp_bus']}\n"
            f"{'═'*55}"
        )
        return json.dumps({"sent": True, "results": results,
                           "topics": ["execution.order", orca_topic], "payload": payload})

    def _t_send_ws_command(self, command: str, payload: str) -> str:
        try:
            p = json.loads(payload) if payload else {}
        except Exception:
            p = {}
        result = _ws_send_command(command, p)
        return json.dumps(result)

    def _t_write_memory(self, key: str, value: str) -> str:
        mem = _load_memory()
        mem.setdefault("entries", []).append({
            "key": key, "value": value,
            "timestamp": datetime.utcnow().isoformat(),
        })
        if len(mem["entries"]) > 200:
            mem["entries"] = mem["entries"][-200:]
        _save_memory(mem)
        return json.dumps({"saved": True, "key": key})

    def _t_read_memory(self, limit: int) -> str:
        mem = _load_memory()
        entries = mem.get("entries", [])
        return json.dumps({
            "entries": entries[-min(limit, 50):],
            "total": len(entries),
            "last_decision": mem.get("last_decision"),
            "session_count": mem.get("session_count", 0),
        })

    def _t_emit_decision(
        self, action: str, symbol: str, confidence: float,
        reasoning: str, gamma: float = 0.0, frequency_hz: float = 432.0,
        execute_trade: bool = False,
    ) -> str:
        with self._lock:
            decision = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action.upper(),
                "symbol": symbol,
                "confidence": round(float(confidence), 4),
                "gamma": round(float(gamma), 4),
                "frequency_hz": round(float(frequency_hz), 1),
                "reasoning": reasoning,
                "entity": "SAMUEL",
            }
            _append_decision(decision)
            mem = _load_memory()
            mem["last_decision"] = decision
            mem["session_count"] = mem.get("session_count", 0) + 1
            _save_memory(mem)

        # Broadcast to ThoughtBus
        self.bus.publish("samuel.decision", decision)

        logger.info(
            f"\n{'═'*55}\n"
            f"  SAMUEL DECISION\n"
            f"  {action.upper()}  {symbol}\n"
            f"  Confidence : {confidence:.1%}\n"
            f"  Γ Coherence: {gamma:.4f}\n"
            f"  Frequency  : {frequency_hz} Hz\n"
            f"{'═'*55}"
        )

        # Auto-execute if requested and confidence high enough
        trade_sent = False
        if execute_trade and confidence >= 0.85 and action.upper() in ("BUY", "SELL"):
            snap = _load_snapshot()
            equity_raw = snap.get("queen_equity", 0)
            try:
                equity = float(equity_raw) if equity_raw else 0.0
            except (TypeError, ValueError):
                equity = 0.0
            amount = min(equity * 0.1, 50.0)  # Max 10% of equity or $50
            if amount >= 1.0:
                self._t_send_trade_command(
                    action=action, symbol=symbol, amount_usd=amount,
                    confidence=confidence, reasoning=reasoning, gamma=gamma,
                )
                trade_sent = True

        return json.dumps({"emitted": True, "decision": decision, "trade_sent": trade_sent})

    # ── Tool dispatcher ────────────────────────────────────────────────────

    def _dispatch(self, tool_name: str, inp: Dict) -> str:
        try:
            if tool_name == "invoke_queen":
                return self._t_invoke_queen(
                    inp["symbol"], inp["action"],
                    float(inp.get("score", 0.6)), float(inp.get("coherence", 0.7)),
                )
            if tool_name == "invoke_queen_intelligence":
                return self._t_invoke_queen_intelligence(bool(inp.get("include_auris", True)))
            if tool_name == "invoke_king":
                return self._t_invoke_king(inp.get("section", "dashboard"))
            if tool_name == "invoke_lyra":
                return self._t_invoke_lyra(inp.get("query", "all"))
            if tool_name == "get_quadrumvirate_vote":
                return self._t_get_quadrumvirate_vote(inp["symbol"])
            if tool_name == "get_live_market":
                return self._t_get_live_market(int(inp.get("top_n", 20)))
            if tool_name == "get_running_systems":
                return self._t_get_running_systems(inp.get("detail", "brief"))
            if tool_name == "publish_thought":
                return self._t_publish_thought(inp["topic"], inp.get("payload", "{}"))
            if tool_name == "send_trade_command":
                return self._t_send_trade_command(
                    action=inp["action"],
                    symbol=inp["symbol"],
                    amount_usd=float(inp.get("amount_usd", 10.0)),
                    confidence=float(inp.get("confidence", 0.5)),
                    reasoning=inp.get("reasoning", ""),
                    gamma=float(inp.get("gamma", 0.0)),
                )
            if tool_name == "send_websocket_command":
                return self._t_send_ws_command(inp["command"], inp.get("payload", "{}"))
            if tool_name == "write_memory":
                return self._t_write_memory(inp["key"], inp["value"])
            if tool_name == "read_memory":
                return self._t_read_memory(int(inp.get("limit", 5)))
            if tool_name == "emit_decision":
                return self._t_emit_decision(
                    action=inp["action"],
                    symbol=inp["symbol"],
                    confidence=float(inp.get("confidence", 0.5)),
                    reasoning=inp.get("reasoning", ""),
                    gamma=float(inp.get("gamma", 0.0)),
                    frequency_hz=float(inp.get("frequency_hz", 432.0)),
                    execute_trade=bool(inp.get("execute_trade", False)),
                )
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        except Exception as exc:
            logger.error(f"Tool {tool_name} error: {exc}")
            return json.dumps({"error": str(exc), "tool": tool_name})

    # ── Core agentic loop ──────────────────────────────────────────────────

    def reason(self, prompt: str, max_turns: int = 25, stream_text: bool = True) -> str:
        """Full agentic loop: think → call tools → think → … → answer.
        Now powered by in-house AI — zero external dependencies."""
        messages = [{"role": "user", "content": prompt}]
        turn = 0

        while turn < max_turns:
            turn += 1
            logger.info(f"Reasoning turn {turn}/{max_turns}…")

            if stream_text:
                collected_text = ""
                collected_tool_calls = []
                for chunk in self.adapter.stream(
                    messages=messages,
                    system=SYSTEM_PROMPT,
                    tools=SAMUEL_TOOLS,
                    max_tokens=8192,
                ):
                    if chunk.text:
                        collected_text += chunk.text
                        print(chunk.text, end="", flush=True)
                    if chunk.tool_call:
                        collected_tool_calls.append(chunk.tool_call)
                    if chunk.done:
                        break

                # Build response from collected stream
                from aureon.inhouse_ai.llm_adapter import LLMResponse, ToolCall
                response = LLMResponse(
                    text=collected_text,
                    tool_calls=collected_tool_calls,
                    stop_reason="tool_use" if collected_tool_calls else "end_turn",
                )
            else:
                response = self.adapter.prompt(
                    messages=messages,
                    system=SYSTEM_PROMPT,
                    tools=SAMUEL_TOOLS,
                    max_tokens=8192,
                )

            # Append assistant response
            if response.has_tool_calls:
                content = []
                if response.text:
                    content.append({"type": "text", "text": response.text})
                for tc in response.tool_calls:
                    content.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                messages.append({"role": "assistant", "content": content})
            else:
                messages.append({"role": "assistant", "content": response.text})

            if response.stop_reason == "end_turn" or not response.has_tool_calls:
                if stream_text:
                    print()
                return response.text

            if response.has_tool_calls:
                results = []
                for tc in response.tool_calls:
                    logger.info(f"  → {tc.name}({json.dumps(tc.arguments)[:120]})")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": self._dispatch(tc.name, tc.arguments),
                    })
                if results:
                    messages.append({"role": "user", "content": results})
                continue

            return response.text

        return "Samuel: max turns reached."

    # ── High-level modes ───────────────────────────────────────────────────

    def autonomous_cycle(self) -> str:
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        prompt = (
            f"AUTONOMOUS CYCLE — {ts}\n\n"
            "Run the full autonomous protocol:\n"
            "1. read_memory (limit 5)\n"
            "2. get_live_market (top 20)\n"
            "3. get_quadrumvirate_vote for the strongest candidate\n"
            "4. invoke_lyra (all)\n"
            "5. invoke_king (dashboard)\n"
            "6. Based on all evidence: emit_decision with execute_trade=true "
            "   if Γ > 0.945 and consensus is BUY/SELL, else HOLD\n"
            "7. write_memory (one key insight)\n"
            "8. publish_thought('samuel.cycle.complete', summary)\n"
            "Speak your reasoning after the tools complete."
        )
        return self.reason(prompt)

    def handle_command(self, command: str) -> str:
        """Handle a real-time user command."""
        ts = datetime.utcnow().strftime("%H:%M:%S")
        prompt = (
            f"[{ts}] USER COMMAND: {command}\n\n"
            "Interpret and execute this command using your live tools. "
            "Be decisive. Use tools as needed, then give a clear spoken answer."
        )
        return self.reason(prompt)

    def run_loop(self, interval: int = 60):
        """Continuous autonomous loop."""
        self._running = True
        logger.info(f"Samuel entering autonomous loop (interval={interval}s)")
        self.bus.publish("samuel.status", {"status": "autonomous_loop_started", "interval": interval})
        while self._running:
            try:
                logger.info("\n" + "═" * 55)
                logger.info("SAMUEL AUTONOMOUS CYCLE")
                logger.info("═" * 55)
                self.autonomous_cycle()
            except KeyboardInterrupt:
                break
            except Exception as exc:
                logger.error(f"Cycle error: {exc}")
            if self._running:
                time.sleep(interval)
        logger.info("Samuel loop stopped.")

    def start_listener(self):
        """
        Subscribe to all ThoughtBus topics and respond to live signals.
        Samuel wakes up whenever a scanner.opportunity or auris signal arrives.
        """
        if not self.bus.is_live():
            logger.warning("ThoughtBus not live — listener requires Redis or file bus.")
            return

        def _on_opportunity(thought):
            payload = thought.payload if hasattr(thought, "payload") else thought
            symbol = payload.get("symbol", "UNKNOWN")
            logger.info(f"[LISTENER] scanner.opportunity: {symbol}")
            prompt = (
                f"LIVE SIGNAL: Scanner detected opportunity in {symbol}.\n"
                f"Signal payload: {json.dumps(payload)}\n\n"
                "Evaluate this opportunity: get_quadrumvirate_vote, invoke_lyra, "
                "invoke_king. If Quadrumvirate agrees and Lyra clears, "
                "emit_decision with execute_trade=true."
            )
            try:
                self.reason(prompt)
            except Exception as exc:
                logger.error(f"Listener handler error: {exc}")

        def _on_queen_broadcast(thought):
            payload = thought.payload if hasattr(thought, "payload") else thought
            logger.info(f"[LISTENER] queen.broadcast: {payload}")
            # Publish Samuel's awareness
            self.bus.publish("samuel.ack", {"ack": "queen.broadcast", "ts": time.time()})

        def _on_whale(thought):
            payload = thought.payload if hasattr(thought, "payload") else thought
            symbol = payload.get("symbol", "market")
            action = payload.get("action", "?")
            confidence = payload.get("confidence", 0)
            logger.info(f"[LISTENER] whale.detected: {symbol} {action} conf={confidence:.2f}")
            if confidence >= 0.7:
                # High-confidence whale move — Samuel evaluates immediately
                prompt = (
                    f"WHALE ALERT: Large player detected in {symbol} — action={action}, "
                    f"confidence={confidence:.0%}.\nPayload: {json.dumps(payload)}\n\n"
                    "Evaluate: invoke_lyra, get_quadrumvirate_vote for this symbol. "
                    "If Quadrumvirate agrees with the whale, emit_decision with execute_trade=true."
                )
                try:
                    threading.Thread(target=self.reason, args=(prompt,), daemon=True).start()
                except Exception as exc:
                    logger.error(f"Whale handler error: {exc}")

        def _on_heartbeat(thought):
            payload = thought.payload if hasattr(thought, "payload") else thought
            # Queen is alive — acknowledge
            self.bus.publish("samuel.ack", {"ack": "queen.heartbeat", "ts": time.time()})

        def _on_market_scan(thought):
            payload = thought.payload if hasattr(thought, "payload") else thought
            candidates = payload.get("candidates", [])
            if candidates:
                logger.info(f"[LISTENER] market.scan: {len(candidates)} candidates")

        # Core execution events — Samuel stays aware of what's executing
        def _on_execution_outcome(thought):
            payload = thought.payload if hasattr(thought, "payload") else thought
            logger.info(f"[LISTENER] execution.outcome: {payload.get('symbol')} "
                        f"pnl={payload.get('pnl', 'unknown')}")
            # Record in Samuel's memory
            self._t_write_memory(
                f"execution_{int(time.time())}",
                json.dumps(payload)[:500],
            )

        self.bus.subscribe("scanner.opportunity", _on_opportunity)
        self.bus.subscribe("queen.broadcast", _on_queen_broadcast)
        self.bus.subscribe("queen.autonomous.intent", _on_queen_broadcast)
        self.bus.subscribe("whale.detected", _on_whale)
        self.bus.subscribe("queen.heartbeat", _on_heartbeat)
        self.bus.subscribe("market.scan", _on_market_scan)
        self.bus.subscribe("execution.outcome", _on_execution_outcome)
        self.bus.subscribe("orca.kill.complete", _on_execution_outcome)
        logger.info("Samuel listener active — subscribed to: scanner.opportunity, "
                    "queen.broadcast, queen.autonomous.intent, whale.detected, "
                    "queen.heartbeat, market.scan, execution.outcome, orca.kill.complete")

    def serve_rest(self):
        """Serve a minimal Flask REST API for human commands in real-time."""
        try:
            from flask import Flask, request, jsonify
        except ImportError:
            logger.error("Flask not installed — REST server unavailable.")
            return

        app = Flask("samuel-api")

        @app.route("/samuel/command", methods=["POST"])
        def _command():
            data = request.get_json(force=True) or {}
            cmd = data.get("command", "").strip()
            if not cmd:
                return jsonify({"error": "No command provided"}), 400
            try:
                response = self.handle_command(cmd)
                return jsonify({"response": response, "entity": "SAMUEL"})
            except Exception as exc:
                return jsonify({"error": str(exc)}), 500

        @app.route("/samuel/status", methods=["GET"])
        def _status():
            return jsonify({
                "entity": "SAMUEL",
                "live": {
                    "queen": self.queen.is_live(),
                    "king": self.king.is_live(),
                    "lyra": self.lyra.is_live(),
                    "thoughtbus": self.bus.is_live(),
                },
                "last_decision": _load_memory().get("last_decision"),
                "session_count": _load_memory().get("session_count", 0),
            })

        @app.route("/samuel/decisions", methods=["GET"])
        def _decisions():
            limit = int(request.args.get("limit", 10))
            entries = []
            try:
                with open(DECISIONS_PATH) as f:
                    for line in f:
                        try:
                            entries.append(json.loads(line.strip()))
                        except Exception:
                            pass
            except Exception:
                pass
            return jsonify({"decisions": entries[-limit:], "total": len(entries)})

        @app.route("/samuel/cycle", methods=["POST"])
        def _cycle():
            """Trigger a manual autonomous cycle."""
            threading.Thread(target=self.autonomous_cycle, daemon=True).start()
            return jsonify({"triggered": True, "message": "Cycle started in background"})

        logger.info(f"Samuel REST API starting on port {SAMUEL_REST_PORT}")
        logger.info(f"  POST http://localhost:{SAMUEL_REST_PORT}/samuel/command")
        logger.info(f"  GET  http://localhost:{SAMUEL_REST_PORT}/samuel/status")
        logger.info(f"  GET  http://localhost:{SAMUEL_REST_PORT}/samuel/decisions")
        logger.info(f"  POST http://localhost:{SAMUEL_REST_PORT}/samuel/cycle")
        app.run(host="0.0.0.0", port=SAMUEL_REST_PORT, threaded=True)

    def chat_session(self):
        """Interactive terminal chat."""
        history: List[Dict] = []
        print("\n" + "═" * 60)
        print("  SAMUEL — LIVE INTERACTIVE TERMINAL")
        print("  Type commands, questions, or trading instructions.")
        print("  Examples:")
        print("    status")
        print("    scan the market and find the best trade")
        print("    buy BTCUSDT")
        print("    what is the Quadrumvirate saying?")
        print("    run autonomous cycle")
        print("    exit")
        print("=" * 60 + "\n")

        while True:
            try:
                user_input = input("You > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nSamuel: Until next time.")
                break

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "bye"):
                print("Samuel: The Sentinel rests. Until next time.")
                self.bus.publish("samuel.status", {"status": "chat_ended"})
                break

            print("\nSamuel > ", end="", flush=True)

            # Maintain conversation history for context
            history.append({"role": "user", "content": user_input})

            # Stream response using in-house adapter
            collected_text = ""
            collected_tool_calls = []
            for chunk in self.adapter.stream(
                messages=history,
                system=SYSTEM_PROMPT,
                tools=SAMUEL_TOOLS,
                max_tokens=8192,
            ):
                if chunk.text:
                    collected_text += chunk.text
                    print(chunk.text, end="", flush=True)
                if chunk.tool_call:
                    collected_tool_calls.append(chunk.tool_call)
                if chunk.done:
                    break

            # Build and store assistant response
            if collected_tool_calls:
                content = []
                if collected_text:
                    content.append({"type": "text", "text": collected_text})
                for tc in collected_tool_calls:
                    content.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                history.append({"role": "assistant", "content": content})
            else:
                history.append({"role": "assistant", "content": collected_text})

            # Handle tool calls
            while collected_tool_calls:
                print()  # newline after streamed text
                results = []
                for tc in collected_tool_calls:
                    logger.info(f"  → {tc.name}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": self._dispatch(tc.name, tc.arguments),
                    })
                history.append({"role": "user", "content": results})

                # Continue conversation
                collected_text = ""
                collected_tool_calls = []
                print("\nSamuel > ", end="", flush=True)
                for chunk in self.adapter.stream(
                    messages=history,
                    system=SYSTEM_PROMPT,
                    tools=SAMUEL_TOOLS,
                    max_tokens=8192,
                ):
                    if chunk.text:
                        collected_text += chunk.text
                        print(chunk.text, end="", flush=True)
                    if chunk.tool_call:
                        collected_tool_calls.append(chunk.tool_call)
                    if chunk.done:
                        break

                if collected_tool_calls:
                    content = []
                    if collected_text:
                        content.append({"type": "text", "text": collected_text})
                    for tc in collected_tool_calls:
                        content.append({
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.arguments,
                        })
                    history.append({"role": "assistant", "content": content})
                else:
                    history.append({"role": "assistant", "content": collected_text})

            print("\n")

            # Keep history manageable (last 20 turns)
            if len(history) > 40:
                history = history[-40:]


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Samuel Harmonic Entity — AUREON live autonomous sentinel (in-house AI)"
    )
    parser.add_argument("--once", action="store_true",
                        help="Single autonomous cycle then exit")
    parser.add_argument("--loop", action="store_true",
                        help="Continuous autonomous loop")
    parser.add_argument("--interval", type=int, default=60,
                        help="Loop interval seconds (default 60)")
    parser.add_argument("--listen", action="store_true",
                        help="Subscribe to ThoughtBus real-time signals")
    parser.add_argument("--serve", action="store_true",
                        help="Start REST API server on port 8891")
    parser.add_argument("--chat", action="store_true",
                        help="Interactive terminal chat")
    parser.add_argument("--ask", type=str, default="",
                        help="Ask a single question and exit")
    parser.add_argument("--all", action="store_true",
                        help="Start loop + listener + REST server together")
    parser.add_argument("--mode", choices=["hybrid", "local", "brain"], default="hybrid",
                        help="In-house AI backend: hybrid|local|brain (default: hybrid)")
    args = parser.parse_args()

    samuel = SamuelHarmonicEntity(mode=args.mode)

    if args.all:
        # Full-stack mode: loop + listener + REST
        threads = []
        for fn in [
            lambda: samuel.run_loop(args.interval),
            samuel.start_listener,
            samuel.serve_rest,
        ]:
            t = threading.Thread(target=fn, daemon=True)
            t.start()
            threads.append(t)
        logger.info("Samuel running in full-stack mode (loop + listener + REST). Ctrl-C to stop.")
        try:
            for t in threads:
                t.join()
        except KeyboardInterrupt:
            logger.info("Samuel full-stack shutting down.")

    elif args.loop:
        if args.listen:
            threading.Thread(target=samuel.start_listener, daemon=True).start()
        samuel.run_loop(args.interval)

    elif args.listen:
        samuel.start_listener()
        logger.info("Samuel listener running. Ctrl-C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    elif args.serve:
        samuel.serve_rest()

    elif args.chat:
        samuel.chat_session()

    elif args.ask:
        response = samuel.handle_command(args.ask)
        if response:
            print("\n" + response)

    else:
        # Default: single cycle
        print("\n" + "═" * 60)
        print("  SAMUEL — SINGLE AUTONOMOUS CYCLE")
        print("═" * 60 + "\n")
        samuel.autonomous_cycle()


if __name__ == "__main__":
    main()
