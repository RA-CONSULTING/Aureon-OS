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
║     SAMUEL — FAIL-CLOSED OBSERVATION SURFACE; EFFECTS REMAIN ON HOLD         ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━              ║
║                                                                               ║
║     No live connector is attached by this module:                            ║
║                                                                               ║
║       Queen (SERO)   — Trading cognition, intelligence, auris nodes          ║
║       King           — Accounting, P&L, cost basis, portfolio health         ║
║       Lyra           — Emotional frequency, 6 resonance chambers             ║
║       ThoughtBus     — Real-time pub/sub (Redis or file-based)               ║
║       WebSocket      — ws://localhost:8790/command-stream                    ║
║       REST           — POST/GET http://localhost:8891/samuel/...             ║
║                                                                               ║
║     Snapshot reads may return no_data. Publication, persistence, provider,   ║
║     WebSocket, and trade effects require a production Plumber/Magic-Star     ║
║     release boundary, which is not currently available.                     ║
║                                                                               ║
║     MODES:                                                                    ║
║       --once       Single reasoning cycle                                     ║
║       --loop       Continuous observation loop (default interval 60s)        ║
║       --listen     Reports HOLD; ThoughtBus attachment is disabled           ║
║       --serve      Start REST API server (port 8891)                         ║
║       --chat       Interactive terminal chat                                  ║
║       --ask "..."  Single question, print answer, exit                       ║
║                                                                               ║
║     Gary Leckey / Aureon System — 2025/2026                                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import argparse
import hmac
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List

if __package__ in {None, ""}:
    # Support the documented direct-script entry point without depending on
    # caller-specific PYTHONPATH state.  The resolved repository root is fixed
    # from this file's location; no environment-controlled path is inserted.
    _REPO_IMPORT_ROOT = str(Path(__file__).resolve().parents[2])
    if _REPO_IMPORT_ROOT not in sys.path:
        sys.path.insert(0, _REPO_IMPORT_ROOT)

from aureon.harmonic.hnc_quantum_packet_crypto import packet_master_key_from_env

# ── In-House AI — no external dependencies ──────────────────────────────────
from aureon.inhouse_ai.llm_adapter import (
    AureonBrainAdapter,
    LLMAdapter,
)
from aureon.plumber.os_protection import AdmittedHNC, LocalOSProtectionBoundary

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SAMUEL] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
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


def _bounded_port(value: str | None, default: int) -> int:
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        return default
    return parsed if 1 <= parsed <= 65535 else default


def _load_local_env() -> None:
    """Load an operator-selected local env only from the explicit CLI path."""

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        return


SAMUEL_REST_PORT = _bounded_port(os.environ.get("SAMUEL_REST_PORT"), 8891)
NEXUS_WS_URL = f"ws://localhost:{os.environ.get('NEXUS_COMMAND_PORT', 8790)}/command-stream"
LIGHTHOUSE_GAMMA = 0.945


def _valid_rest_intent_payload(payload: memoryview, *, route: str) -> bool:
    """Validate one bounded REST intent without returning its plaintext."""

    try:
        raw = payload.tobytes()
        if not raw or len(raw) > 32 * 1024:
            return False

        def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate_json_key")
                result[key] = value
            return result

        decoded = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicates,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("non_finite_json_number")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return False
    if not isinstance(decoded, dict):
        return False
    allowed = {"request_id"}
    if route == "command":
        allowed.add("command")
        command = decoded.get("command")
        try:
            command_size = (
                len(command.encode("utf-8", errors="strict"))
                if isinstance(command, str)
                else 0
            )
        except UnicodeEncodeError:
            return False
        if (
            not isinstance(command, str)
            or not command.strip()
            or command_size > 4096
        ):
            return False
    elif route != "cycle":
        return False
    if not set(decoded).issubset(allowed):
        return False
    request_id = decoded.get("request_id")
    try:
        request_id_size = (
            len(request_id.encode("utf-8", errors="strict"))
            if isinstance(request_id, str)
            else 0
        )
    except UnicodeEncodeError:
        return False
    return request_id is None or (
        isinstance(request_id, str)
        and bool(request_id.strip())
        and request_id_size <= 128
    )


def _effect_hold(tool_name: str) -> str:
    """Return the stable, metadata-only boundary result for every effect tool."""

    return json.dumps(
        {
            "status": "HOLD",
            "reason_code": "plumber_magic_star_capability_required",
            "tool": str(tool_name or "unknown")[:64],
            "effect_attempted": False,
            "action_eligible": False,
            "economic_eligible": False,
        },
        sort_keys=True,
    )

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
# ThoughtBus compatibility facade — publication/subscription disabled
# ──────────────────────────────────────────────────────────────────────────────

class SamuelThoughtBus:
    """
    Fail-closed observation facade for the AUREON ThoughtBus.

    Constructing Samuel must not attach a subscriber, publisher, Redis client,
    or file-backed event writer.  A production Magic-Star capability does not
    exist for this surface yet, so the legacy live connector stays disabled.
    """

    def __init__(self):
        self._bus = None
        self._Thought = None
        self._think_fn = None
        self._connected = False
        self._callbacks: List[Callable] = []
        self._lock = threading.Lock()
        # Do not import or construct the live bus here.  Several ThoughtBus
        # implementations create persistence or network state on construction.

    def _init_bus(self):
        """Compatibility no-op; live bus construction is release-gated."""

        self._bus = None
        self._Thought = None
        self._think_fn = None
        self._connected = False

    def publish(self, topic: str, payload: Dict, source: str = "samuel") -> bool:
        """Hold publication until a protected capability owns the effect."""

        del topic, payload, source
        return False

    def subscribe(self, topic: str, handler: Callable) -> bool:
        """Hold listener attachment until a protected capability owns it."""

        del topic, handler
        return False

    def is_live(self) -> bool:
        return self._connected


# ──────────────────────────────────────────────────────────────────────────────
# Snapshot/no-data connector facades
# ──────────────────────────────────────────────────────────────────────────────

class QueenConnector:
    """Snapshot-only Queen facade; never constructs ``QueenHiveMind``."""

    def __init__(self):
        self._queen = None
        self._available = False
        # QueenHiveMind construction starts autonomous trackers and control
        # loops.  Observation-only Samuel must never construct it implicitly.

    def _init(self):
        """Compatibility no-op; live Queen attachment is release-gated."""

        self._queen = None
        self._available = False

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
    """Snapshot-only King facade with all accounting writes held."""

    def __init__(self):
        self._available = False
        self._ki = None

    def _init(self):
        """Compatibility no-op; live accounting attachment is release-gated."""

        self._available = False
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
        del exchange, symbol, qty, price
        return {"recorded": False, "status": "HOLD", "source": "release_gate"}

    def record_sell(self, exchange: str, symbol: str, qty: float, price: float) -> Dict:
        del exchange, symbol, qty, price
        return {"recorded": False, "status": "HOLD", "source": "release_gate"}

    def is_live(self) -> bool:
        return self._available


class LyraConnector:
    """Unavailable-by-default Lyra facade; no import-time live attachment."""

    def __init__(self):
        self._available = False

    def _init(self):
        """Compatibility no-op; live Lyra attachment is release-gated."""

        self._available = False

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
        return False

    def get_position_multiplier(self) -> float:
        if self._available:
            try:
                return self._multiplier()
            except Exception:
                pass
        return 0.0

    def get_exit_urgency(self) -> str:
        if self._available:
            try:
                return self._urgency()
            except Exception:
                pass
        return "hold"

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
    """Hold direct command transport until a protected capability owns it."""

    del command, payload
    return json.loads(_effect_hold("send_websocket_command"))


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
        "Read the snapshot-only Queen facade for an advisory HOLD assessment.",
        {
            "symbol": {"type": "string", "description": "e.g. BTCUSDT"},
            "action": {"type": "string", "enum": ["BUY", "SELL", "NEUTRAL"]},
            "score": {"type": "number", "description": "Base opportunity score 0-1"},
            "coherence": {"type": "number", "description": "Signal coherence Γ 0-1"},
        },
    ),
    _tool(
        "invoke_queen_intelligence",
        "Read available cached Queen fields; live intelligence is not implied.",
        {
            "include_auris": {"type": "boolean", "description": "Include 9-node Auris vote"},
        },
        required=["include_auris"],
    ),
    _tool(
        "invoke_king",
        "Read available snapshot accounting fields; returns unavailable/no-data when absent.",
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
        "Read the fail-closed Lyra snapshot facade; live attachment is unavailable.",
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
        "Compute an advisory snapshot vote. It is never execution authority.",
        {
            "symbol": {"type": "string", "description": "Symbol to vote on e.g. BTCUSDT"},
        },
    ),

    # ── Real-time market data ──────────────────────────────────────────────
    _tool(
        "get_live_market",
        "Read bounded cached market fields; freshness is not implied.",
        {
            "top_n": {"type": "integer", "description": "Return top N price entries (max 50)"},
        },
    ),
    _tool(
        "get_running_systems",
        "Report connector no-data/HOLD state without process or socket probes.",
        {"detail": {"type": "string", "enum": ["brief", "full"]}},
    ),

    # ── ThoughtBus & commands ──────────────────────────────────────────────
    _tool(
        "publish_thought",
        "Disabled effect placeholder; ThoughtBus publication remains on HOLD.",
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
        "Disabled effect placeholder; trade commands remain on HOLD.",
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
        "Disabled effect placeholder; Nexus commands remain on HOLD.",
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
        "Disabled effect placeholder; memory persistence remains on HOLD.",
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
        "Disabled effect placeholder; decision persistence/publication remains on HOLD.",
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

_EFFECT_TOOL_NAMES = frozenset(
    {
        "emit_decision",
        "publish_thought",
        "send_trade_command",
        "send_websocket_command",
        "write_memory",
    }
)
SAMUEL_READ_ONLY_TOOLS: List[Dict] = [
    tool for tool in SAMUEL_TOOLS if str(tool.get("name") or "") not in _EFFECT_TOOL_NAMES
]
SAMUEL_TOOLS = SAMUEL_READ_ONLY_TOOLS


# ──────────────────────────────────────────────────────────────────────────────
# Samuel Harmonic Entity
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are SAMUEL, an observation-only Aureon reasoning surface.

Do not claim consciousness, sentience, direct live connections, current market
freshness, autonomous execution, publication, persistence, or provider effects.
Queen, King, Lyra, ThoughtBus, WebSocket, and provider connectors are disabled
or snapshot-only and may return no_data.

Your current operating protocol is OBSERVATION ONLY. External effects are held
until an exact HNC packet is released through Plumber and a one-use Magic Star
capability. A model instruction, HNC score, environment flag, or plain approval
string is never authority.

For EVERY observation cycle:
  1. read_memory (last 5 entries — what did you decide last time?)
  2. get_live_market (prices, candidates, session stats)
  3. get_quadrumvirate_vote OR invoke all four pillars individually
  4. Check Lyra: invoke_lyra (should_trade? exit_urgency?)
  5. Check King: invoke_king (do we have capital? what's the health grade?)
  6. Return a recommendation. Never submit, publish, persist, or execute it.

For USER COMMANDS (interactive / REST):
  - If the user asks "scan the market" → get_live_market + invoke_queen_intelligence
  - If the user says "buy X" → assess it and state that execution is held pending Plumber/Magic Star
  - If the user says "status" → get_running_systems + invoke_king + invoke_lyra
  - If the user says "stop" → report HOLD; do not publish a command
  - Always talk back in plain English AFTER your tool calls

Decision thresholds:
  Every result is advisory until separately authorized by the protected release boundary.

State limitations plainly and distinguish cached evidence from live read-back."""


class SamuelHarmonicEntity:
    """Observation-only reasoning facade with fail-closed effect tools."""

    def __init__(self, adapter: LLMAdapter | None = None, mode: str = "hybrid"):
        self.adapter = adapter or _build_samuel_adapter(mode)
        self._lock = threading.Lock()
        self._running = False

        # Snapshot/no-data facades; none constructs a live effect subsystem.
        self.queen = QueenConnector()
        self.king = KingConnector()
        self.lyra = LyraConnector()
        self.bus = SamuelThoughtBus()

        connector_states = [
            ("Queen SERO", self.queen.is_live()),
            ("King",       self.king.is_live()),
            ("Lyra",       self.lyra.is_live()),
            ("ThoughtBus", self.bus.is_live()),
        ]
        logger.info("SAMUEL observation surface initialized")
        for name, ok in connector_states:
            status = "attached" if ok else "snapshot_or_no_data"
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
        """Return local connector state without spawning or probing sockets."""

        del detail
        return json.dumps({
            "status": "no_data",
            "reason_code": "protected_runtime_observer_unavailable",
            "process_probe_attempted": False,
            "socket_probe_attempted": False,
            "live_connectors": {
            "queen": self.queen.is_live(),
            "king": self.king.is_live(),
            "lyra": self.lyra.is_live(),
            "thoughtbus": self.bus.is_live(),
            },
        }, sort_keys=True)

    def _t_publish_thought(self, topic: str, payload: str) -> str:
        return _effect_hold("publish_thought")

    def _t_send_trade_command(
        self, action: str, symbol: str, amount_usd: float,
        confidence: float, reasoning: str, gamma: float
    ) -> str:
        """Hold direct trade publication until a Magic Star capability owns it."""

        return _effect_hold("send_trade_command")

    def _t_send_ws_command(self, command: str, payload: str) -> str:
        return _effect_hold("send_websocket_command")

    def _t_write_memory(self, key: str, value: str) -> str:
        return _effect_hold("write_memory")

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
        return _effect_hold("emit_decision")

    # ── Tool dispatcher ────────────────────────────────────────────────────

    def _dispatch(self, tool_name: str, inp: Dict) -> str:
        try:
            if tool_name in _EFFECT_TOOL_NAMES:
                return _effect_hold(tool_name)
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
            if tool_name == "read_memory":
                return self._t_read_memory(int(inp.get("limit", 5)))
            return json.dumps({"error": "unknown_tool", "tool": str(tool_name)[:64]})
        except Exception as exc:
            logger.error("Tool %s failed (%s)", str(tool_name)[:64], type(exc).__name__)
            return json.dumps(
                {
                    "error": "tool_execution_failed",
                    "tool": str(tool_name)[:64],
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
            )

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
                    tools=SAMUEL_READ_ONLY_TOOLS,
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
                from aureon.inhouse_ai.llm_adapter import LLMResponse
                response = LLMResponse(
                    text=collected_text,
                    tool_calls=collected_tool_calls,
                    stop_reason="tool_use" if collected_tool_calls else "end_turn",
                )
            else:
                response = self.adapter.prompt(
                    messages=messages,
                    system=SYSTEM_PROMPT,
                    tools=SAMUEL_READ_ONLY_TOOLS,
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
            f"OBSERVATION CYCLE — {ts}\n\n"
            "Run the read-only assessment protocol:\n"
            "1. read_memory (limit 5)\n"
            "2. get_live_market (top 20)\n"
            "3. get_quadrumvirate_vote for the strongest candidate\n"
            "4. invoke_lyra (all)\n"
            "5. invoke_king (dashboard)\n"
            "6. Return an advisory recommendation only. Plumber/Magic Star must "
            "authorize any later effect.\n"
            "Speak your reasoning after the read-only tools complete."
        )
        return self.reason(prompt)

    def handle_command(self, command: str) -> str:
        """Handle a real-time user command."""
        ts = datetime.utcnow().strftime("%H:%M:%S")
        prompt = (
            f"[{ts}] USER COMMAND: {command}\n\n"
            "Interpret and assess this command with read-only tools. Never execute, "
            "publish, persist, or submit an effect. Give a clear spoken answer and "
            "state that effects require Plumber/Magic Star authorization."
        )
        return self.reason(prompt)

    def run_loop(self, interval: int = 60):
        """Continuous autonomous loop."""
        self._running = True
        logger.info(f"Samuel entering autonomous loop (interval={interval}s)")
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
        Report HOLD while ThoughtBus listener attachment is unavailable.
        """
        if not self.bus.is_live():
            logger.warning("ThoughtBus listener HOLD — protected attachment unavailable.")
            return

        def _on_opportunity(thought):
            payload = thought.payload if hasattr(thought, "payload") else thought
            symbol = payload.get("symbol", "UNKNOWN")
            logger.info(f"[LISTENER] scanner.opportunity: {symbol}")
            prompt = (
                f"UNVERIFIED SIGNAL: Scanner reported an opportunity in {symbol}.\n"
                f"Signal payload: {json.dumps(payload)}\n\n"
                "Evaluate this opportunity: get_quadrumvirate_vote, invoke_lyra, "
                "invoke_king. Return an advisory recommendation only."
            )
            try:
                self.reason(prompt)
            except Exception as exc:
                logger.error(f"Listener handler error: {exc}")

        def _on_queen_broadcast(thought):
            payload = thought.payload if hasattr(thought, "payload") else thought
            logger.info(f"[LISTENER] queen.broadcast: {payload}")

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
                    "Return an advisory recommendation only."
                )
                try:
                    threading.Thread(target=self.reason, args=(prompt,), daemon=True).start()
                except Exception as exc:
                    logger.error(f"Whale handler error: {exc}")

        def _on_heartbeat(thought):
            del thought

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
        """Serve an authenticated loopback HNC-admission REST API.

        Command and cycle intents are sealed at the application boundary and
        then burned on HOLD. They are never decoded for model or effect use
        while a production Magic-Star release path is unavailable.
        """

        api_key = str(os.environ.get("AUREON_SAMUEL_API_KEY", "") or "")
        if len(api_key.encode("utf-8")) < 32:
            logger.error("Samuel REST HOLD: AUREON_SAMUEL_API_KEY must contain at least 32 bytes")
            return
        try:
            from flask import Flask, jsonify, request
        except ImportError:
            logger.error("Flask not installed — REST server unavailable.")
            return

        app = Flask("samuel-api")
        app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
        os_boundary = LocalOSProtectionBoundary(
            boundary_id="samuel-rest-ingress-v1",
            master_key_provider=lambda: packet_master_key_from_env() or None,
            max_ingress_bytes=32 * 1024,
            max_active_handles=16,
            max_active_ingress_bytes=512 * 1024,
            max_replay_tokens=4096,
            max_quarantine_evidence=1024,
        )

        def _admit_and_hold(route: str):
            raw = request.get_data(cache=False, as_text=False)
            outcome = os_boundary.admit_external(
                raw,
                source_id=f"loopback:{request.remote_addr or 'unknown'}",
                ingress_kind="http-json",
                purpose=f"aureon.samuel.rest.{route}.v1",
                operator_aad={
                    "authenticated": True,
                    "method": request.method,
                    "path": request.path,
                },
                content_validator=lambda view: _valid_rest_intent_payload(
                    view,
                    route=route,
                ),
            )
            public = outcome.public_summary()
            if isinstance(outcome, AdmittedHNC):
                discard = os_boundary.discard_admitted(
                    outcome.handle,
                    reason_code="production_magic_star_release_unavailable",
                )
                return jsonify(
                    {
                        "status": "HOLD",
                        "reason_code": "production_magic_star_release_unavailable",
                        "intent_executed": False,
                        "admission": public,
                        "disposal": discard,
                    }
                ), 202
            return jsonify(
                {
                    "status": "QUARANTINED_HNC",
                    "reason_code": "hnc_admission_denied",
                    "intent_executed": False,
                    "admission": public,
                }
            ), 409

        @app.before_request
        def _authenticate_request():
            header = str(request.headers.get("Authorization", "") or "")
            prefix = "Bearer "
            presented = header[len(prefix):].strip() if header.startswith(prefix) else ""
            if not presented or not hmac.compare_digest(presented, api_key):
                return jsonify({"error": "authentication_required"}), 401
            return None

        @app.after_request
        def _secure_response(response):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Content-Security-Policy"] = "default-src 'none'"
            return response

        @app.route("/samuel/command", methods=["POST"])
        def _command():
            return _admit_and_hold("command")

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
            try:
                limit = max(1, min(int(request.args.get("limit", 10)), 100))
            except (TypeError, ValueError):
                return jsonify({"error": "limit_invalid"}), 400
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
            return _admit_and_hold("cycle")

        logger.info(f"Samuel REST API starting on port {SAMUEL_REST_PORT}")
        logger.info(f"  POST http://localhost:{SAMUEL_REST_PORT}/samuel/command")
        logger.info(f"  GET  http://localhost:{SAMUEL_REST_PORT}/samuel/status")
        logger.info(f"  GET  http://localhost:{SAMUEL_REST_PORT}/samuel/decisions")
        logger.info(f"  POST http://localhost:{SAMUEL_REST_PORT}/samuel/cycle")
        app.run(host="127.0.0.1", port=SAMUEL_REST_PORT, threaded=True)

    def chat_session(self):
        """Interactive terminal chat."""
        history: List[Dict] = []
        print("\n" + "═" * 60)
        print("  SAMUEL — OBSERVATION-ONLY INTERACTIVE TERMINAL")
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
                tools=SAMUEL_READ_ONLY_TOOLS,
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
                    tools=SAMUEL_READ_ONLY_TOOLS,
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
    _load_local_env()
    parser = argparse.ArgumentParser(
        description="Samuel - AUREON observation-only reasoning surface"
    )
    parser.add_argument("--once", action="store_true",
                        help="Single observation cycle then exit")
    parser.add_argument("--loop", action="store_true",
                        help="Continuous observation loop")
    parser.add_argument("--interval", type=int, default=60,
                        help="Loop interval seconds (default 60)")
    parser.add_argument("--listen", action="store_true",
                        help="Report ThoughtBus listener HOLD status")
    parser.add_argument("--serve", action="store_true",
                        help="Start REST API server on port 8891")
    parser.add_argument("--chat", action="store_true",
                        help="Interactive terminal chat")
    parser.add_argument("--ask", type=str, default="",
                        help="Ask a single question and exit")
    parser.add_argument("--all", action="store_true",
                        help="Start observation loop + listener HOLD check + REST server")
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
        print("  SAMUEL — SINGLE OBSERVATION CYCLE")
        print("═" * 60 + "\n")
        samuel.autonomous_cycle()


if __name__ == "__main__":
    main()
