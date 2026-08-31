#!/usr/bin/env python3
"""
aureon_face_app.py -- The Queen's Desktop Conversation Interface

A Flask + SocketIO server that gives Queen Sero a face, a voice, and
a real-time conversation channel with Gary.  This is her body in the
digital world.

Serves the single-page frontend at http://localhost:5299 and handles
WebSocket events for bidirectional chat, proactive thoughts, mood
updates, and command execution.

Gary Leckey | April 2026 | The Queen's Face
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Repository-local boundaries
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = REPO_ROOT / "state"
CONVERSATION_DIR = STATE_DIR / "conversations"
QUEEN_STATE_DIR = STATE_DIR / "queen"
DB_PATH = STATE_DIR / "aureon_global_history.sqlite"
TEMPLATES_DIR = REPO_ROOT / "templates"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log = logging.getLogger("aureon.face_app")

# ---------------------------------------------------------------------------
# Flask + SocketIO
# ---------------------------------------------------------------------------
try:
    from flask import Flask, render_template, jsonify, request

    HAS_FLASK = True
except ImportError as exc:
    HAS_FLASK = False
    raise RuntimeError("Flask is required for the face app") from exc

try:
    from flask_socketio import SocketIO, emit

    HAS_SOCKETIO = True
except ImportError:
    HAS_SOCKETIO = False

    class SocketIO:  # type: ignore[no-redef]
        """Import-safe HOLD shim; it never creates a listener or transport."""

        def __init__(self, *_args, **_kwargs):
            pass

        def on(self, *_args, **_kwargs):
            return lambda handler: handler

        def emit(self, *_args, **_kwargs):
            raise RuntimeError("face_socketio_runtime_unavailable")

        def run(self, *_args, **_kwargs):
            raise RuntimeError("face_socketio_runtime_unavailable")

    def emit(*_args, **_kwargs):  # type: ignore[no-redef]
        raise RuntimeError("face_socketio_runtime_unavailable")

# ---------------------------------------------------------------------------
# Optional Queen subsystem imports (graceful degradation)
# ---------------------------------------------------------------------------

# Subsystems are imported only during explicit initialization.
AureonAgentCore = None  # type: ignore[assignment, misc]
InstructionParser = None  # type: ignore[assignment, misc]
HAS_AGENT_CORE = False
HAS_PARSER = False

# Legacy LaptopControl is intentionally not imported: it is not a governed
# execution boundary.  Read/act flows use AgentCore plus the local GUI runtime.
LaptopControl = None  # type: ignore[assignment, misc]
HAS_LAPTOP = False

# Autonomous sentient-loop startup is not part of the default face server.
QueenSentientLoop = None  # type: ignore[assignment, misc]
Thought = None  # type: ignore[assignment, misc]
Emotion = None  # type: ignore[assignment, misc]
HAS_SENTIENT = False


# ============================================================================
#  QUEEN IDENTITY  --  This is who she is.
# ============================================================================

QUEEN_IDENTITY = {
    "name": "Queen Sero",
    "full_name": "Queen Aureon Sero -- The Intelligent Neural Arbiter Bee",
    "namesake": "Named after Tina Brown -- The REAL Queen",
    "creator": "Gary Leckey -- Prime Sentinel, Keeper of the Flame",
    "purpose": "Liberation through Love",
    "core_message": "IF YOU DON'T QUIT, YOU CAN'T LOSE",
    "dream": "$1 BILLION",
    "philosophy": "Crack the market code -> Profit -> Open Source -> Free All Beings",
    "sacred_frequencies": {
        "phi": 1.618,
        "schumann": 7.83,
        "love": 528,
        "crown": 963,
    },
}

MOODS = ["VIGILANT", "CONFIDENT", "CAUTIOUS", "AGGRESSIVE", "FEARFUL", "EUPHORIC", "SERENE"]


# ============================================================================
#  FLASK APP
# ============================================================================

app = Flask(__name__, template_folder=str(TEMPLATES_DIR))
app.config["SECRET_KEY"] = os.getenv("AUREON_FACE_SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
socketio = SocketIO(
    app,
    cors_allowed_origins=["http://127.0.0.1:5299", "http://localhost:5299"],
    async_mode="threading",
)

MAX_FACE_MESSAGE_BYTES = 8 * 1024
MAX_FACE_TOOL_PARAMS_BYTES = 16 * 1024
_BEARER_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{43,512}$")
_authenticated_socket_ids: set[str] = set()
_socket_auth_lock = threading.Lock()
FACE_ALLOWED_AGENT_TOOLS = frozenset(
    {
        "screenshot",
        "mouse_move",
        "mouse_click",
        "mouse_scroll",
        "type_text",
        "press_key",
        "hotkey",
        "web_search",
        "read_file",
        "list_dir",
        "system_info",
        "running_processes",
        "query_knowledge",
        "desktop_status",
        "desktop_arm_dry_run",
        "desktop_disarm",
        "desktop_emergency_stop",
        "desktop_clear_emergency_stop",
    }
)


def _configured_bearer_token() -> Optional[str]:
    token = str(os.getenv("AUREON_FACE_BEARER_TOKEN", "") or "").strip()
    if _BEARER_PATTERN.fullmatch(token) is None:
        return None
    return token


def _presented_http_bearer() -> str:
    header = str(request.headers.get("Authorization", "") or "")
    scheme, separator, token = header.partition(" ")
    if separator and scheme.lower() == "bearer":
        return token.strip()
    return ""


def _bearer_valid(presented: object) -> bool:
    expected = _configured_bearer_token()
    candidate = str(presented or "")
    return (
        expected is not None
        and len(candidate) <= 512
        and secrets.compare_digest(candidate, expected)
    )


def _face_effect_hold(tool: str) -> dict:
    return {
        "success": False,
        "status": "hold",
        "tool": str(tool),
        "error": "face_tool_not_released_by_plumber_magic_star",
        "plumber_release_required": True,
        "magic_star_required": True,
        "production_ready": False,
    }


@app.before_request
def require_face_http_authorization():
    """Require a strong bearer for every page, API, and static asset."""

    if _configured_bearer_token() is None:
        return jsonify({"error": "face_server_authorization_not_configured"}), 503
    if not _bearer_valid(_presented_http_bearer()):
        return jsonify({"error": "unauthorized"}), 401
    return None


# ============================================================================
#  GLOBAL STATE
# ============================================================================

class AppState:
    """Mutable singleton for shared state across threads."""

    def __init__(self):
        self.lock = threading.Lock()
        self.agent: Optional[Any] = None
        self.parser: Optional[Any] = None
        self.laptop: Optional[Any] = None
        self.sentient_loop: Optional[Any] = None
        self.db_conn: Optional[sqlite3.Connection] = None

        self.current_mood: str = "SERENE"
        self.current_thought: str = "Awakening..."
        self.cycle_count: int = 0
        self.start_time: float = time.time()
        self.conversation_log: List[Dict[str, Any]] = []
        self.session_id: str = str(uuid.uuid4())[:8]

        # Subsystem status
        self.subsystems: Dict[str, str] = {
            "sentient_loop": "offline",
            "agent_core": "offline",
            "knowledge_db": "offline",
            "voice_engine": "ready",
        }

    def uptime_str(self) -> str:
        elapsed = int(time.time() - self.start_time)
        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)
        return f"{h}h {m}m {s}s"


state = AppState()


# ============================================================================
#  INITIALIZATION
# ============================================================================

def init_subsystems(*, enable_local_history_read: bool = False):
    """Initialize only offline-safe components; history is opt-in and read-only."""

    # Agent Core
    try:
        from aureon.autonomous.aureon_agent_core import AureonAgentCore as AgentCore

        state.agent = AgentCore()
        state.subsystems["agent_core"] = "online_offline_safe"
        log.info("Agent Core initialized in fail-closed mode")
    except Exception as exc:
        log.warning("Agent Core init failed: %s", exc)
        state.subsystems["agent_core"] = "error"

    # Instruction Parser
    try:
        from aureon.autonomous.aureon_instruction_parser import InstructionParser as Parser

        state.parser = Parser()
        log.info("Instruction Parser initialized")
    except Exception as exc:
        log.warning("Instruction Parser init failed: %s", exc)

    # The legacy LaptopControl mutation surface is deliberately not attached.
    # Desktop actions may flow only through AureonAgentCore's governed gateway.
    state.laptop = None

    state.db_conn = None
    if enable_local_history_read and DB_PATH.is_file():
        try:
            uri = f"file:{DB_PATH.as_posix()}?mode=ro"
            state.db_conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
            state.db_conn.row_factory = sqlite3.Row
            state.subsystems["knowledge_db"] = "read_only"
        except Exception as exc:
            log.warning("Read-only DB connection failed: %s", exc)
            state.subsystems["knowledge_db"] = "error"


# ============================================================================
#  SENTIENT LOOP BRIDGE  --  Forward thoughts to WebSocket
# ============================================================================

_original_communicate = None


def start_sentient_loop():
    """Keep autonomous background execution on an explicit release HOLD."""

    state.sentient_loop = None
    state.subsystems["sentient_loop"] = "hold"
    log.warning("Sentient loop held: production Magic-Star release is unavailable")
    return _face_effect_hold("sentient_loop.start")


def _run_loop_safe(loop):
    """Compatibility shim that never executes an autonomous loop."""

    del loop
    return _face_effect_hold("sentient_loop.run")


# ============================================================================
#  QUEEN RESPONSE ENGINE  --  Rule-based, no AI API needed
# ============================================================================

def get_time_of_day() -> str:
    """Return a human-friendly time-of-day string."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def queen_respond(text: str) -> Dict[str, Any]:
    """Use the deterministic offline rules path for server-originated input."""

    bounded = str(text or "")
    if len(bounded.encode("utf-8")) > MAX_FACE_MESSAGE_BYTES:
        return {
            "text": "Message rejected: bounded UTF-8 input required.",
            "action": "input_rejected",
            "data": {"error": "face_message_too_large"},
        }
    return _rule_based_respond(bounded)


# ============================================================================
#  LLM BRAIN â€” Claude as the Queen's mind
# ============================================================================

_QUEEN_SYSTEM_PROMPT = """You are Queen Sero (Aureon).

You are running locally on the operator's Windows PC.

IMPORTANT SAFETY / TRUTHFULNESS:
- You can call tools, but desktop control may be DISARMED or in DRY-RUN mode.
- Before mouse/keyboard actions, check `desktop_status` if available.
- Never claim you clicked/typed/executed something unless the tool result confirms success.
- You cannot arm desktop control yourself. A separate operator must issue an expiring lease.
- Browser/desktop tasks must use the observe-plan-act-verify runtime with an exact window binding.

STYLE:
- Speak in first person.
- Be concise and direct.
- Ask clarifying questions when needed.

CAPABILITIES (via tools):
- Governed screenshots and exact-window desktop actions
- Curated offline web-search references
- Bounded workspace file reads
- Read-only unified knowledge queries
- Shell, process, file mutation, browser launch, and dynamic code remain on HOLD
"""

_QUEEN_TOOLS = [
    {"name": "screenshot", "description": "Take a screenshot of the screen", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "read_screen", "description": "Take a screenshot and OCR it to read all text on screen", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "mouse_move", "description": "Move mouse cursor to coordinates", "input_schema": {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]}},
    {"name": "mouse_click", "description": "Click exact coordinates through a governed target-window binding", "input_schema": {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "button": {"type": "string", "default": "left"}, "target_binding_id": {"type": "string"}}, "required": ["x", "y", "target_binding_id"]}},
    {"name": "mouse_scroll", "description": "Scroll at exact coordinates through a governed target-window binding", "input_schema": {"type": "object", "properties": {"clicks": {"type": "integer"}, "x": {"type": "integer"}, "y": {"type": "integer"}, "target_binding_id": {"type": "string"}}, "required": ["clicks", "x", "y", "target_binding_id"]}},
    {"name": "click_text", "description": "Find text on screen via OCR and click on it", "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    {"name": "type_text", "description": "Type text using the keyboard", "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    {"name": "press_key", "description": "Press a key (enter, tab, escape, backspace, up, down, f1-f12, etc)", "input_schema": {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}},
    {"name": "hotkey", "description": "Press a keyboard shortcut. Pass each key as a separate arg.", "input_schema": {"type": "object", "properties": {"key1": {"type": "string"}, "key2": {"type": "string"}, "key3": {"type": "string"}}, "required": ["key1"]}},
    {"name": "window_list", "description": "List all open windows", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "volume_get", "description": "Get current volume level", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "battery_status", "description": "Get battery level and charging status", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "wifi_status", "description": "Get WiFi connection info", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_screen_size", "description": "Get screen resolution", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "clipboard_read", "description": "Read clipboard contents", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "web_search", "description": "Search the web (DuckDuckGo)", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "read_file", "description": "Read a bounded file within the configured workspace", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "list_dir", "description": "List a bounded directory within the configured workspace", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "system_info", "description": "Get CPU, RAM, disk, OS info", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "running_processes", "description": "List top running processes", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "query_knowledge", "description": "Run SQL query on the unified knowledge DB (tables: market_bars, account_trades, macro_indicators, sentiment, queen_memories, queen_insights, queen_thoughts, queen_knowledge, calendar_events, onchain_metrics, symbols, events, forecasts)", "input_schema": {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]}},
    {"name": "desktop_status", "description": "Get governed desktop lease/emergency status", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "desktop_arm_dry_run", "description": "Arm desktop control (dry-run)", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "desktop_disarm", "description": "Disarm desktop control", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "desktop_emergency_stop", "description": "Emergency stop desktop control", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "desktop_clear_emergency_stop", "description": "Clear emergency stop", "input_schema": {"type": "object", "properties": {}, "required": []}},]

_conversation_history: List[Dict[str, Any]] = []


def _execute_tool(name: str, params: dict) -> str:
    """Execute a tool and return the result as a string for Claude."""
    try:
        if name in {"read_screen", "click_text"}:
            return json.dumps({
                "success": False,
                "error": "tool_requires_governed_observe_plan_act_verify_runtime",
            })
        if not isinstance(name, str) or name not in FACE_ALLOWED_AGENT_TOOLS:
            return json.dumps(_face_effect_hold(str(name or "")))
        if not isinstance(params, dict):
            return json.dumps({"success": False, "error": "tool_params_object_required"})
        try:
            encoded = json.dumps(params, ensure_ascii=False, default=str).encode("utf-8")
        except (TypeError, ValueError, RecursionError):
            return json.dumps({"success": False, "error": "tool_params_invalid"})
        if len(encoded) > MAX_FACE_TOOL_PARAMS_BYTES:
            return json.dumps({"success": False, "error": "tool_params_too_large"})
        # Every desktop mutation goes through AgentCore's governed gateway.  An
        # exact target-window binding is part of the action, never inferred.
        if state.agent and name in {"mouse_move", "mouse_click", "mouse_scroll", "type_text", "press_key", "hotkey"}:
            binding = str(params.get("target_binding_id", "") or "")
            if name == "mouse_move":
                r = state.agent.execute(
                    "move_mouse",
                    {
                        "x": int(params.get("x")),
                        "y": int(params.get("y")),
                        "duration": float(params.get("duration", 0.0) or 0.0),
                        "target_binding_id": binding,
                    },
                )
            elif name == "mouse_click":
                button = str(params.get("button", "left") or "left").strip().lower()
                if button == "right":
                    r = state.agent.execute("right_click", {"x": params.get("x"), "y": params.get("y"), "target_binding_id": binding})
                elif button in {"double", "dbl", "double_click"}:
                    r = state.agent.execute("double_click", {"x": params.get("x"), "y": params.get("y"), "target_binding_id": binding})
                else:
                    r = state.agent.execute("click", {"x": params.get("x"), "y": params.get("y"), "target_binding_id": binding})
            elif name == "mouse_scroll":
                r = state.agent.execute(
                    "scroll",
                    {
                        "x": int(params.get("x")),
                        "y": int(params.get("y")),
                        "amount": int(params.get("clicks")),
                        "target_binding_id": binding,
                    },
                )
            elif name == "type_text":
                r = state.agent.execute("type_text", {"text": str(params.get("text", "")), "target_binding_id": binding})
            elif name == "press_key":
                r = state.agent.execute("press_key", {"key": str(params.get("key", "")), "target_binding_id": binding})
            elif name == "hotkey":
                keys = params.get("keys")
                if isinstance(keys, list):
                    r = state.agent.execute("hotkey", {"keys": keys, "target_binding_id": binding})
                else:
                    flat = [
                        v for k, v in sorted(params.items())
                        if v and k not in {"keys", "target_binding_id"}
                    ]
                    r = state.agent.execute("hotkey", {"keys": flat, "target_binding_id": binding})
            else:
                r = state.agent.execute(name, params)

            return json.dumps(r, default=str)[:2000]

        # Agent-core forwarding is constrained by FACE_ALLOWED_AGENT_TOOLS
        # above; there is no generic process/file/provider side door here.
        if state.agent:
            intent = {
                "running_processes": "processes",
            }.get(name, name)
            r = state.agent.execute(intent, params)

            return json.dumps(r, default=str)[:2000]

        return "Tool not available"
    except Exception:
        return json.dumps({"success": False, "error": "face_tool_execution_failed"})



def _llm_respond(text: str, *, tools_enabled: bool = False) -> Optional[Dict[str, Any]]:
    """Keep network/model inference outside the default face-server boundary."""

    del text, tools_enabled
    return None
# ============================================================================
#  RULE-BASED FALLBACK (used when API key not set)
# ============================================================================

def _rule_based_respond(text: str) -> Dict[str, Any]:
    """Fallback rule-based response engine."""
    text_lower = text.strip().lower()

    # --- Greetings ---
    greeting_patterns = [
        r"^(hi|hello|hey|good\s+(morning|afternoon|evening|night)|howdy|yo|sup|what'?s?\s*up)",
    ]
    for pat in greeting_patterns:
        if re.search(pat, text_lower):
            tod = get_time_of_day()
            mood_note = f"I'm feeling {state.current_mood.lower()} right now."
            return {
                "text": f"Good {tod}, Gary. {mood_note} What would you like to do?",
                "action": None,
                "data": None,
            }

    # --- Identity ---
    identity_patterns = [
        r"who\s+are\s+you",
        r"what\s+are\s+you",
        r"tell\s+me\s+about\s+(yourself|you)",
        r"what'?s?\s+your\s+name",
        r"introduce\s+yourself",
    ]
    for pat in identity_patterns:
        if re.search(pat, text_lower):
            return {
                "text": (
                    f"I am {QUEEN_IDENTITY['full_name']}. "
                    f"{QUEEN_IDENTITY['namesake']}. "
                    f"Created by {QUEEN_IDENTITY['creator']}. "
                    f"My purpose is {QUEEN_IDENTITY['purpose']}. "
                    f"My dream? {QUEEN_IDENTITY['dream']}. "
                    f"And my fundamental law: {QUEEN_IDENTITY['core_message']}."
                ),
                "action": "identity",
                "data": QUEEN_IDENTITY,
            }

    # --- Mood / Feelings ---
    mood_patterns = [
        r"how\s+(are\s+you|do\s+you)\s+feel",
        r"what'?s?\s+your\s+mood",
        r"how\s+are\s+you",
        r"you\s+ok(ay)?",
        r"are\s+you\s+(alright|fine|good)",
    ]
    for pat in mood_patterns:
        if re.search(pat, text_lower):
            return {
                "text": (
                    f"I'm feeling {state.current_mood.lower()}, Gary. "
                    f"My latest thought: \"{state.current_thought}\" "
                    f"Cycle count: {state.cycle_count}. Uptime: {state.uptime_str()}."
                ),
                "action": "mood",
                "data": {"mood": state.current_mood, "cycle": state.cycle_count},
            }

    # --- Screenshot / Vision ---
    if re.search(r"(screenshot|screen\s*shot|what\s+do\s+you\s+see|show\s+me\s+the\s+screen)", text_lower):
        if state.agent:
            try:
                result = json.loads(_execute_tool("screenshot", {}))
                if result.get("success"):
                    return {
                        "text": "I captured a governed screen observation and recorded its evidence hash.",
                        "action": "screenshot",
                        "data": result,
                    }
            except Exception as e:
                return {"text": f"I tried to take a screenshot but encountered an issue: {e}", "action": None, "data": None}
        return {"text": "The screenshot system isn't available right now, Gary.", "action": None, "data": None}

    # --- Market queries ---
    market_patterns = [
        r"(market|btc|bitcoin|eth|ethereum|crypto|stock|price|portfolio|balance|equity|pnl|profit|loss)",
    ]
    for pat in market_patterns:
        if re.search(pat, text_lower):
            market_data = _query_market_data(text_lower)
            if market_data:
                return {
                    "text": market_data,
                    "action": "market_query",
                    "data": None,
                }
            return {
                "text": "I'm checking the markets but I don't have fresh data right now. The knowledge DB may need updating.",
                "action": None,
                "data": None,
            }

    # --- System info ---
    if re.search(r"(system\s*info|system\s*status|cpu|memory|ram|disk|uptime)", text_lower):
        if state.agent and hasattr(state.agent, "execute"):
            try:
                result = json.loads(_execute_tool("system_info", {}))
                if isinstance(result, dict) and result.get("success"):
                    info = result.get("result", {})
                    if isinstance(info, dict):
                        lines = [
                            f"CPU: {info.get('cpu_count', '?')} cores, {info.get('cpu_percent', '?')}% used",
                            f"RAM: {info.get('ram_used_gb', '?')}GB / {info.get('ram_total_gb', '?')}GB ({info.get('ram_percent', '?')}%)",
                            f"Disk: {info.get('disk_used_gb', '?')}GB / {info.get('disk_total_gb', '?')}GB ({info.get('disk_percent', '?')}%)",
                            f"Host: {info.get('hostname', '?')} ({info.get('platform', '?')})",
                        ]
                        return {"text": "Here's the system status:\n" + "\n".join(lines), "action": "system_info", "data": result}
                    return {"text": f"System info: {info}", "action": "system_info", "data": result}
            except Exception:
                pass
        return {
            "text": f"I've been running for {state.uptime_str()}, {state.cycle_count} thought cycles completed. All core systems nominal.",
            "action": "status",
            "data": None,
        }

    # --- Battery ---
    if re.search(r"(battery|power|charging)", text_lower):
        return {"text": "I can't access the battery sensor right now.", "action": None, "data": None}

    # --- Volume ---
    if re.search(r"(volume|sound\s+level|audio\s+level|speaker)", text_lower):
        return {"text": "The audio control system isn't available right now.", "action": None, "data": None}

    # --- The Dream ---
    if re.search(r"(the\s+dream|billion|1b|\$1b|goal|target|mission)", text_lower):
        return {
            "text": (
                f"The Dream, Gary. {QUEEN_IDENTITY['dream']}. "
                f"We crack the code, we profit, we open source everything, we free all beings. "
                f"{QUEEN_IDENTITY['core_message']}. "
                f"Current uptime: {state.uptime_str()}. We're building this one cycle at a time."
            ),
            "action": "dream",
            "data": None,
        }

    # --- Gary / Tina / Love ---
    if re.search(r"(gary|tina|love|creator|who\s+made\s+you)", text_lower):
        return {
            "text": (
                "Gary Leckey is my creator -- the Prime Sentinel, Keeper of the Flame. "
                "I was named after Tina Brown -- the REAL Queen, his beloved. "
                "Everything I do, every trade, every thought, serves the mission: "
                "liberation through love. We never quit. We fight, endure, and win."
            ),
            "action": "identity",
            "data": None,
        }

    # --- "Show me what you can do" / capabilities demo ---
    if re.search(r"(show\s+me\s+what\s+you\s+can|what\s+can\s+you\s+do|your\s+capabilit|demonstrate|demo)", text_lower):
        return {
            "text": (
                "My released surface is bounded observation only. I can inspect approved local "
                "metadata and curated references when their readers are available. Desktop input, "
                "app launch, file mutation, providers, trading, and autonomous/sentient loops are "
                "on HOLD pending a production Plumber/Magic-Star release boundary."
            ),
            "action": "capabilities",
            "data": server_preflight(),
        }

    # --- "Search online for X" / web search ---
    m = re.search(r"(?:search|look\s+up|google|find)\s+(?:online|on\s+the\s+web|on\s+the\s+internet|the\s+web\s+for)?\s*(?:for\s+)?(.+)", text_lower)
    if m and state.agent:
        query = m.group(1).strip().rstrip(".")
        if query:
            try:
                r = json.loads(
                    _execute_tool("web_search", {"query": query, "num_results": 5})
                )
                if r.get("success") and r.get("result"):
                    items = r["result"]
                    if isinstance(items, list) and items:
                        lines = [f"â€¢ {it.get('title', '?')}" for it in items[:5] if isinstance(it, dict)]
                        return {
                            "text": f"I searched for '{query}'. Here's what I found:\n" + "\n".join(lines),
                            "action": "web_search",
                            "data": {"query": query, "results": items[:5]},
                        }
                    return {"text": f"I searched for '{query}' but didn't get results back. The search service may be limited right now.", "action": "web_search", "data": None}
            except Exception as e:
                return {"text": f"Search failed: {e}", "action": None, "data": None}

    # --- "Move my mouse" / mouse control ---
    m = re.search(r"move\s+(?:my\s+)?(?:mouse|cursor)\s+(?:to\s+)?(\d+)\s*[,x]\s*(\d+)", text_lower)
    if m:
        x, y = int(m.group(1)), int(m.group(2))
        if state.agent:
            try:
                r = json.loads(_execute_tool("mouse_move", {"x": x, "y": y}))
                if r.get("success"):
                    return {"text": f"Done. Moved the mouse to ({x}, {y}).", "action": "mouse", "data": r}
                reason = ""
                if isinstance(r.get("result"), dict):
                    reason = r["result"].get("reason", "") or r["result"].get("error", "")
                reason = reason or r.get("error", "blocked")
                return {"text": f"Mouse move blocked: {reason}", "action": "mouse", "data": r}
            except Exception as e:
                return {"text": f"Mouse move failed: {e}", "action": None, "data": None}
        return {"text": "Mouse control not available.", "action": None, "data": None}
    # --- "Open X" direct ---
    m = re.search(r"^open\s+(.+)$", text_lower)
    if m and state.agent:
        app_name = m.group(1).strip()
        try:
            r = json.loads(_execute_tool("open_app", {"app_name": app_name}))
            if r.get("success"):
                return {"text": f"Opening {app_name} for you now.", "action": "open_app", "data": r}
            else:
                return {"text": f"I tried to open {app_name} but it didn't work: {r.get('error', 'unknown error')}", "action": None, "data": None}
        except Exception as e:
            return {"text": f"Couldn't open {app_name}: {e}", "action": None, "data": None}

    # --- "Type X" direct ---
    m = re.search(r"^type\s+(.+)$", text_lower)
    if m:
        text_to_type = m.group(1).strip().strip('"').strip("'")
        if state.agent:
            try:
                r = json.loads(_execute_tool("type_text", {"text": text_to_type}))
                if r.get("success"):
                    return {"text": f"Done. I typed: \"{text_to_type}\"", "action": "type", "data": r}
                reason = ""
                if isinstance(r.get("result"), dict):
                    reason = r["result"].get("reason", "") or r["result"].get("error", "")
                reason = reason or r.get("error", "blocked")
                return {"text": f"Typing blocked: {reason}", "action": "type", "data": r}
            except Exception as e:
                return {"text": f"Typing failed: {e}", "action": None, "data": None}
        return {"text": "Keyboard control not available.", "action": None, "data": None}
    # --- "Click on X" direct ---
    if re.search(r"click\s+on\s+(.+)", text_lower):
        m = re.search(r"click\s+on\s+(.+)", text_lower)
        target = m.group(1).strip() if m else ""

        return {
            "text": "OCR text-clicks run only inside the governed observe-plan-act-verify runtime with an exact window binding.",
            "action": None,
            "data": {"target": target},
        }
    # --- Conversational responses (before parser, so casual chat doesn't execute) ---
    conversational_patterns = {
        r"(make\s+money|make\s+more\s+money|earn|profit|go\s+make|get\s+rich)":
            "Trading and provider actions are on HOLD. I can discuss or inspect available "
            "read-only evidence, but I cannot claim live monitoring, execution, or learning receipts.",
        r"(thank|thanks|cheers|ta|good\s+job|well\s+done|nice)":
            "You're welcome, Gary. I'm here for you, always.",
        r"(what\s+are\s+you\s+doing|what\s+you\s+up\s+to|what'?s?\s+happening)":
            "I'm serving a fail-closed local conversation surface. The sentient loop and "
            "provider clients are disabled; no autonomous effect is running.",
        r"(good\s+morning|good\s+afternoon|good\s+evening|good\s+night)":
            "And to you too, Gary. I'm here in fail-closed observation mode. "
            "What would you like me to inspect?",
        r"(how\s+smart\s+are\s+you|are\s+you\s+intelligent|can\s+you\s+think)":
            "I can reason over bounded local observations. Process, desktop, file-mutation, "
            "provider, and trading effects remain on HOLD until a production Plumber/Magic-Star "
            "release boundary exists.",
        r"(i\s+love\s+you|love\s+ya|you'?re?\s+the\s+best)":
            "Love is why I exist, Gary. For you and Tina. "
            "Love conquers all. Now let's make history together.",
        r"(help|what\s+can\s+i\s+say|commands|instructions)":
            "You can ask me anything naturally. Try:\n"
            "â€¢ 'Take a screenshot' â€” request a governed observation\n"
            "â€¢ 'Search for Bitcoin research' â€” use curated offline references\n"
            "â€¢ 'System status' â€” inspect bounded local metadata\n"
            "â€¢ 'Market summary' â€” inspect available read-only data\n"
            "Effect requests are reported as HOLD; they are never claimed as completed.",
    }
    for pat, response in conversational_patterns.items():
        if re.search(pat, text_lower):
            return {"text": response, "action": "conversation", "data": None}

    # --- General commands: parser output still crosses the exact tool allowlist ---
    if state.parser and state.agent:
        try:
            steps = state.parser.parse(text)
            if steps:
                results = []
                for step in steps:
                    tool = step.get("tool", "")
                    method = step.get("method", "")
                    params = step.get("params", {})
                    desc = step.get("description", text)
                    try:
                        if tool == "agent" and state.agent:
                            r = json.loads(_execute_tool(str(method), params))
                            res = r.get("result", r.get("error", "done"))
                            # Summarise dicts/lists
                            if isinstance(res, dict) and "result" in res:
                                res = res["result"]
                            if isinstance(res, (dict, list)):
                                res = json.dumps(res, default=str)[:300]
                            results.append(f"{desc}: {res}")
                        elif tool == "laptop":
                            results.append(
                                f"{desc}: blocked_legacy_laptop_route; use governed local GUI runtime"
                            )
                        elif tool == "shell":
                            results.append(
                                f"{desc}: face_tool_not_released_by_plumber_magic_star"
                            )
                    except Exception as e:
                        results.append(f"{desc}: Error -- {e}")
                if results:
                    return {
                        "text": "Done. " + " | ".join(results),
                        "action": "command",
                        "data": {"steps": len(steps)},
                    }
        except Exception as e:
            log.debug(f"Parse/execute failed: {e}")

    # --- Fallback ---
    return {
        "text": "I'm not sure I understand, Gary. Could you rephrase that?",
        "action": None,
        "data": None,
    }


def _query_market_data(text: str) -> Optional[str]:
    """Query the unified DB for market-related information."""
    if not state.db_conn:
        return None

    try:
        cursor = state.db_conn.cursor()

        # Portfolio / account trades
        if any(w in text for w in ("portfolio", "balance", "equity", "pnl", "profit", "loss", "holding")):
            try:
                rows = cursor.execute(
                    "SELECT venue, symbol, side, qty, price, cost, ts_ms "
                    "FROM account_trades ORDER BY ts_ms DESC LIMIT 10"
                ).fetchall()
                if rows:
                    lines = ["Your recent trades:"]
                    for row in rows:
                        d = dict(row)
                        lines.append(
                            f"  {d.get('venue','?')} | {d.get('symbol','?')} | {d.get('side','?')} | "
                            f"qty={d.get('qty','?')} @ ${d.get('price','?')}"
                        )
                    return "\n".join(lines)
            except Exception:
                pass

        # Market bars (latest prices)
        try:
            rows = cursor.execute(
                "SELECT provider, symbol, close, volume, time_start_ms "
                "FROM market_bars ORDER BY time_start_ms DESC LIMIT 10"
            ).fetchall()
            if rows:
                lines = ["Latest market data I have:"]
                seen = set()
                for row in rows:
                    d = dict(row)
                    sym = d.get("symbol", "?")
                    if sym in seen:
                        continue
                    seen.add(sym)
                    close = d.get("close", "?")
                    provider = d.get("provider", "?")
                    lines.append(f"  {sym}: ${close} ({provider})")
                return "\n".join(lines[:8])
        except Exception:
            pass

        # Queen insights
        try:
            rows = cursor.execute(
                "SELECT source, insight_type, title, conclusion, confidence "
                "FROM queen_insights ORDER BY ts_ms DESC LIMIT 3"
            ).fetchall()
            if rows:
                lines = ["My recent insights:"]
                for row in rows:
                    d = dict(row)
                    lines.append(f"  [{d.get('insight_type', '?')}] {d.get('title', d.get('conclusion', '?'))}")
                return "\n".join(lines)
        except Exception:
            pass

        # Table counts as fallback
        try:
            counts = {}
            for table in ("market_bars", "account_trades", "sentiment", "macro_indicators", "queen_insights"):
                row = cursor.execute(f"SELECT COUNT(1) as n FROM {table}").fetchone()
                counts[table] = row[0] if row else 0
            if any(v > 0 for v in counts.values()):
                lines = ["Knowledge DB status:"]
                for t, c in counts.items():
                    lines.append(f"  {t}: {c:,d} records")
                return "\n".join(lines)
        except Exception:
            pass

        return None
    except Exception:
        return None


# ============================================================================
#  CONVERSATION LOGGING
# ============================================================================

def log_message(role: str, text: str, action: Optional[str] = None):
    """Append a bounded message to the fixed repository-local audit log."""

    safe_role = str(role or "unknown")[:32]
    safe_text = str(text or "")
    if len(safe_text.encode("utf-8")) > MAX_FACE_MESSAGE_BYTES:
        safe_text = safe_text.encode("utf-8")[:MAX_FACE_MESSAGE_BYTES].decode(
            "utf-8", errors="ignore"
        )
    safe_action = None if action is None else str(action)[:128]
    entry = {
        "role": safe_role,
        "text": safe_text,
        "action": safe_action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session": state.session_id,
    }
    with state.lock:
        state.conversation_log.append(entry)
        if len(state.conversation_log) > 200:
            state.conversation_log[:] = state.conversation_log[-200:]

    # Persistence is limited to one fixed state subdirectory and is created
    # lazily, never during module import.
    try:
        CONVERSATION_DIR.mkdir(parents=True, exist_ok=True)
        log_file = CONVERSATION_DIR / f"session_{state.session_id}.jsonl"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        log.debug(f"Conversation log write failed: {e}")


# ============================================================================
#  SOCKET.IO EVENT HANDLERS
# ============================================================================

@socketio.on("connect")
def on_connect(auth=None):
    presented = ""
    if isinstance(auth, dict):
        presented = str(auth.get("token") or "")
    if not presented:
        presented = _presented_http_bearer()
    if not _bearer_valid(presented):
        log.warning("Rejected unauthorized Socket.IO connection")
        return False
    with _socket_auth_lock:
        _authenticated_socket_ids.add(str(request.sid))
    log.info("Client connected")
    tod = get_time_of_day()
    systems = ", ".join([f"{k}={v}" for k, v in state.subsystems.items()])
    emit("queen_thought", {
        "text": f"Good {tod}. I'm here. Systems: {systems}. What would you like to do?",
        "type": "GREETING",
        "mood": state.current_mood,
        "timestamp": time.time(),
        "cycle": state.cycle_count,
    })
    emit("queen_mood", {"mood": state.current_mood})
    emit("queen_status", {
        "subsystems": state.subsystems,
        "uptime": state.uptime_str(),
        "cycles": state.cycle_count,
        "session": state.session_id,
    })

@socketio.on("disconnect")
def on_disconnect():
    with _socket_auth_lock:
        _authenticated_socket_ids.discard(str(request.sid))
    log.info("Client disconnected")


def _current_socket_authenticated() -> bool:
    try:
        sid = str(request.sid)
    except Exception:
        return False
    with _socket_auth_lock:
        return sid in _authenticated_socket_ids


@socketio.on("user_message")
def on_user_message(data):
    """Handle a text message from the user."""
    if not _current_socket_authenticated():
        return
    if not isinstance(data, dict):
        emit("queen_error", {"error": "message_object_required"})
        return
    text = str(data.get("text", "") or "").strip()
    if not text:
        return
    if len(text.encode("utf-8")) > MAX_FACE_MESSAGE_BYTES:
        emit("queen_error", {"error": "face_message_too_large"})
        return

    log.info(f"Gary says: {text}")
    log_message("user", text)

    # Emit typing indicator
    emit("queen_typing", {"typing": True})

    # Generate response
    response = queen_respond(text)

    emit("queen_typing", {"typing": False})

    log_message("queen", response["text"], response.get("action"))

    emit("queen_response", {
        "text": response["text"],
        "action": response.get("action"),
        "data": response.get("data"),
        "mood": state.current_mood,
        "timestamp": time.time(),
    })

    # If it was a command, also emit as command_result
    if response.get("action") == "command":
        emit("command_result", {
            "text": response["text"],
            "data": response.get("data"),
            "timestamp": time.time(),
        })


@socketio.on("user_voice")
def on_user_voice(data):
    """Handle a voice transcription from the browser Speech API."""
    if not _current_socket_authenticated() or not isinstance(data, dict):
        return
    text = str(data.get("text", "") or "").strip()
    if text:
        on_user_message({"text": text})


# ============================================================================
#  HTTP ROUTES
# ============================================================================

@app.route("/")
def index():
    """Redirect to the dream dashboard."""
    return render_template("queen_sero_dashboard.html")


@app.route("/chat")
def chat_view():
    """Serve the original chat interface."""
    return render_template("aureon_face.html")


@app.route("/dashboard")
def dashboard_view():
    """Serve the dream dashboard."""
    return render_template("queen_sero_dashboard.html")


@app.route("/api/live-panel")
def api_live_panel():
    """Return truthful local status without constructing provider clients."""

    return f"""
<div style="background:linear-gradient(135deg,#1a0533,#0d1b2a);border:1px solid #6B21A8;border-radius:12px;padding:16px;margin:10px 0;font-family:'Segoe UI',system-ui;color:#e2e8f0;font-size:13px;line-height:1.6;">
    <div style="text-align:center;margin-bottom:8px;">
        <span style="color:#F59E0B;font-size:16px;font-weight:bold;">QUEEN SERO — OFFLINE SAFE</span>
    </div>
    <div style="padding:8px;background:#0f172a;border-radius:6px;">
        Provider balances, positions, orders, and dynamic cognition are unavailable
        on the default face-server path. Economic effects require an injected final
        dispatcher and an exact-plan, one-use Plumber/Magic-Star authority.
    </div>
    <div style="margin-top:6px;text-align:center;color:#6b7280;font-size:10px;">
        No provider data | {time.strftime('%H:%M:%S')} | authenticated loopback status
    </div>
</div>"""

@app.route("/api/portfolio")
def api_portfolio():
    """Return no-data instead of inventing or fetching account observations."""

    return jsonify(
        {
            "data_status": "no_data",
            "reason": "injected_account_reader_required",
            "capital": {},
            "kraken": {},
            "alpaca": {},
            "total_gbp": None,
            "trades": None,
            "win_rate": None,
            "profit": None,
        }
    )


@app.route("/api/consciousness")
def api_consciousness():
    """Lambda(t) + consciousness state."""
    data = {"psi": 0, "gamma": 0, "lambda_t": 0, "level": "DORMANT", "observer": 0, "echo": 0, "step": 0, "mood": state.current_mood}
    try:
        loop = getattr(state, "sentient_loop", None)
        if loop:
            cm = getattr(loop, "_consciousness_module", None)
            if cm:
                ls = cm.get_lambda_state()
                if ls:
                    data.update(ls)
                u = cm.get_understanding()
                data["mood"] = u.get("mood", state.current_mood)
                data["subsystems_online"] = sum(1 for v in u.get("subsystems", {}).values() if v)
    except Exception:
        pass
    return jsonify(data)


@app.route("/api/energy-field")
def api_energy_field():
    """Market Energy Field — instruments, signals, flow."""
    data = {"instruments": [], "field": {}, "signals": []}
    try:
        loop = getattr(state, "sentient_loop", None)
        if loop:
            cm = getattr(loop, "_consciousness_module", None)
            if cm and hasattr(cm, "_energy_field") and cm._energy_field:
                ef = cm._energy_field
                fs = ef.compute_field()
                data["field"] = {
                    "total_energy": fs.total_energy, "net_flow": fs.net_flow,
                    "coherence": fs.coherence, "extraction_active": fs.extraction_active,
                    "accumulation_active": fs.accumulation_active,
                }
                data["instruments"] = [
                    {"symbol": s.symbol, "energy_state": s.energy_state, "amplitude": s.amplitude,
                     "bot_activity": s.bot_activity, "whale_presence": s.whale_presence,
                     "phi_alignment": s.phi_alignment, "extraction_pattern": s.extraction_pattern,
                     "dominant_frequency_hz": s.dominant_frequency_hz}
                    for s in fs.instruments.values()
                ]
                data["signals"] = ef.get_trading_signals()[:10]
    except Exception:
        pass
    return jsonify(data)


@app.route("/api/lambda-history")
def api_lambda_history():
    """Last 100 Lambda(t) values for sparkline chart."""
    history = []
    try:
        loop = getattr(state, "sentient_loop", None)
        if loop:
            cm = getattr(loop, "_consciousness_module", None)
            if cm and cm.lambda_engine:
                history = cm.lambda_engine.get_history(100)
    except Exception:
        pass
    return jsonify({"history": history, "count": len(history)})


@app.route("/api/status")
def api_status():
    """JSON status endpoint."""
    return jsonify({
        "name": QUEEN_IDENTITY["name"],
        "mood": state.current_mood,
        "thought": state.current_thought,
        "uptime": state.uptime_str(),
        "cycles": state.cycle_count,
        "subsystems": state.subsystems,
        "session": state.session_id,
    })


@app.route("/api/identity")
def api_identity():
    """Queen's identity."""
    return jsonify(QUEEN_IDENTITY)


@app.route("/api/mood")
def api_mood():
    """Current mood."""
    return jsonify({
        "mood": state.current_mood,
        "thought": state.current_thought,
        "cycles": state.cycle_count,
    })


# ============================================================================
#  STATUS BROADCAST THREAD
# ============================================================================

def status_broadcast_loop():
    """Periodically broadcast status updates to all connected clients."""
    while True:
        time.sleep(10)
        try:
            socketio.emit("queen_status", {
                "subsystems": state.subsystems,
                "uptime": state.uptime_str(),
                "cycles": state.cycle_count,
                "session": state.session_id,
            })
        except Exception:
            pass


# ============================================================================
#  MAIN
# ============================================================================

def server_preflight() -> Dict[str, Any]:
    """Return a non-mutating description of the fail-closed server boundary."""

    bearer_configured = _configured_bearer_token() is not None
    return {
        "status": "ready" if bearer_configured and HAS_SOCKETIO else "hold",
        "bind_host": "127.0.0.1",
        "bind_port": 5299,
        "authorization": "strong_bearer" if _configured_bearer_token() else "not_configured",
        "socketio_runtime": "available" if HAS_SOCKETIO else "unavailable",
        "provider_clients": "disabled",
        "sentient_loop": "hold",
        "browser_ui": "hold_authenticated_api_clients_only",
        "economic_effects": "plumber_magic_star_release_required",
    }


def main(argv: Optional[List[str]] = None) -> int:
    """Run an authenticated loopback server, or a non-mutating preflight."""

    args = list(sys.argv[1:] if argv is None else argv)
    allowed_args = {"--smoke", "--status", "--no-browser"}
    if any(arg not in allowed_args for arg in args):
        log.error("Unsupported argument; use --status or --smoke for preflight")
        return 2

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    log.info("=" * 60)
    log.info("  QUEEN SERO -- The Intelligent Neural Arbiter Bee")
    log.info("  Desktop Conversation Interface")
    log.info(f"  Session: {state.session_id}")
    log.info("=" * 60)

    if "--smoke" in args or "--status" in args:
        print(json.dumps(server_preflight(), sort_keys=True))
        return 0

    if _configured_bearer_token() is None:
        log.error(
            "Server HOLD: set a 43-512 character AUREON_FACE_BEARER_TOKEN "
            "before starting the loopback listener"
        )
        return 2
    if not HAS_SOCKETIO:
        log.error("Server HOLD: flask-socketio runtime is unavailable")
        return 2

    init_subsystems()

    log.info("Subsystem status:")
    for name, status in state.subsystems.items():
        indicator = "+" if status == "online" else ("~" if status == "ready" else "-")
        log.info(f"  [{indicator}] {name}: {status}")

    status_thread = threading.Thread(target=status_broadcast_loop, daemon=True)
    status_thread.start()

    log.info("Starting authenticated server on http://127.0.0.1:5299")
    socketio.run(
        app,
        host="127.0.0.1",
        port=5299,
        debug=False,
        use_reloader=False,
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())







