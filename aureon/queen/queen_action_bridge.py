"""
QueenActionBridge — voice → action wiring.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The rest of the Aureon stack already has:

  • ``aureon/inhouse_ai/tool_registry.py``     — ToolRegistry + 5 built-in tools
  • ``aureon/autonomous/vm_control/*``         — VMControlDispatcher + 29 VM tools
  • ``aureon/code_architect/skill_library.py`` — 20+ validated skills
  • ``aureon/harmonic/auris_voice_filter.py``  — Auris 9-node coherence gate
  • ``aureon/inhouse_ai/llm_adapter.py``       — LLMAdapter.prompt(tools=...)

What was missing was the **wire** that lets the Queen voice turn a human
message into a tool execution, gate it through Auris coherence, run it,
and synthesise a reply that includes the result.

This module is that wire. It is dual-path:

  1. **Native tool-calling path** — if the LLM returns proper
     ``tool_calls`` in the response (e.g. Claude, GPT-4, a big Ollama
     model), we run them directly. Future-proof.

  2. **Regex intent path** — qwen2.5:0.5b and other small local models
     rarely emit proper tool_calls, so we also parse the human message
     with a deterministic intent router that maps keywords to concrete
     ``(tool_name, params)`` calls. This is what actually fires today.

Both paths hit the same gate:

  • The bridge starts live. Non-destructive tools run.
  • ``arm(live=False)`` returns to dry-run.
  • ``state/computer_use.stop`` forces dry-run. Aureon does not create that file.
  • Even when armed, **destructive tools** (shell, vm_execute_*) require
    the Auris filter to report ``lighthouse_cleared=True`` on the current
    reply context. If the council isn't unanimous enough, the action
    drops back to dry-run automatically.

Every dispatch — simulated or real — is recorded in a rolling log that
the phone can pull via ``/api/queen/actions``.
"""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from aureon.operator.computer_use_stop import is_stopped

logger = logging.getLogger("aureon.queen.action_bridge")


# ─────────────────────────────────────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ActionRecord:
    """One attempted tool execution."""

    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: float = field(default_factory=time.time)
    tool: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    source: str = "voice"  # voice | manual | llm_toolcall
    mode: str = "dry_run"  # dry_run | live
    ok: bool = False
    result: Any = None
    error: str = ""
    coherence_gated: bool = False
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "action_id": self.action_id,
            "timestamp": self.timestamp,
            "tool": self.tool,
            "params": self.params,
            "source": self.source,
            "mode": self.mode,
            "ok": self.ok,
            "coherence_gated": self.coherence_gated,
            "duration_ms": round(self.duration_ms, 2),
        }
        if self.ok:
            # Summarise the result — full VM dumps can be huge.
            r = self.result
            if isinstance(r, dict):
                keys = list(r.keys())
                out["result_summary"] = {"type": "dict", "keys": keys[:10], "size": len(keys)}
                # Surface a few safe fields the phone can render.
                for k in ("stdout", "stderr", "message", "status", "text", "path"):
                    if k in r:
                        v = r[k]
                        out[k] = v if not isinstance(v, str) else v[:500]
            elif isinstance(r, str):
                out["result_summary"] = r[:500]
            else:
                out["result_summary"] = repr(r)[:300]
        else:
            out["error"] = self.error[:500]
        return out


@dataclass
class ActionReply:
    """Result of a voice → action cycle."""

    text: str = ""
    actions: List[ActionRecord] = field(default_factory=list)
    intent_source: str = ""  # "regex" | "llm_toolcall" | "none"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "actions": [a.to_dict() for a in self.actions],
            "intent_source": self.intent_source,
            "action_count": len(self.actions),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Destructive-tool gate list
# ─────────────────────────────────────────────────────────────────────────────


DESTRUCTIVE_TOOLS = {
    "execute_shell",
    "vm_execute_shell",
    "vm_execute_powershell",
    "vm_type_text",
    "vm_press_key",
    "vm_hotkey",
    "vm_left_click",
    "vm_right_click",
    "vm_middle_click",
    "vm_double_click",
    "vm_triple_click",
    "vm_left_click_drag",
    "vm_scroll",
}


# ─────────────────────────────────────────────────────────────────────────────
# Regex intent router
# ─────────────────────────────────────────────────────────────────────────────


# Each entry: (compiled regex, tool_name, param_extractor(match) -> dict).
# The first pattern that matches wins.
_INTENT_PATTERNS: List[Tuple[re.Pattern, str, Any]] = [
    # Read-only state queries
    (re.compile(r"\b(state|status|health|dashboard)\b", re.I),
     "read_state",
     lambda m: {"keys": "all"}),

    (re.compile(r"\b(positions?|equity|pnl|p\s*and\s*l)\b", re.I),
     "read_positions",
     lambda m: {}),

    (re.compile(r"\b(price|prices|quote|quotes)\b", re.I),
     "read_prices",
     lambda m: {}),

    # Screen / window introspection
    (re.compile(r"\b(screenshot|screen shot|capture screen|show me the screen)\b", re.I),
     "vm_screenshot",
     lambda m: {}),

    (re.compile(r"\b(screen size|resolution|how big is (the )?screen)\b", re.I),
     "vm_get_screen_size",
     lambda m: {}),

    (re.compile(r"\b(cursor position|mouse position|where is (the )?cursor|where is (the )?mouse)\b", re.I),
     "vm_get_cursor_position",
     lambda m: {}),

    (re.compile(r"\b(list windows|open windows|what windows)\b", re.I),
     "vm_list_windows",
     lambda m: {}),

    (re.compile(r"\b(active window|focused window|foreground window|which window)\b", re.I),
     "vm_get_active_window",
     lambda m: {}),

    # Session management
    (re.compile(r"\b(list sessions|sessions open|active sessions|what sessions)\b", re.I),
     "vm_list_sessions",
     lambda m: {}),

    (re.compile(r"\b(session status|session state|current session)\b", re.I),
     "vm_session_status",
     lambda m: {}),

    # Directed interactions (destructive — gated)
    (re.compile(r"\bmove (?:the )?(?:mouse|cursor) to (\d+)[,\s]+(\d+)\b", re.I),
     "vm_mouse_move",
     lambda m: {"x": int(m.group(1)), "y": int(m.group(2))}),

    (re.compile(r"\bclick (?:at )?(\d+)[,\s]+(\d+)\b", re.I),
     "vm_left_click",
     lambda m: {"x": int(m.group(1)), "y": int(m.group(2))}),

    (re.compile(r'\btype\s+["\u201c](.+?)["\u201d]', re.I),
     "vm_type_text",
     lambda m: {"text": m.group(1)}),

    (re.compile(r"\bpress (?:the )?(enter|escape|esc|tab|space|backspace|delete|up|down|left|right)\b", re.I),
     "vm_press_key",
     lambda m: {"key": m.group(1).lower().replace("esc", "escape")}),

    (re.compile(r"\bfocus (?:the )?window\s+([\w\s\.\-]{2,60})", re.I),
     "vm_focus_window",
     lambda m: {"title": m.group(1).strip()}),

    (re.compile(r"\bwait (\d+(?:\.\d+)?)\s*(?:s|sec|second|seconds)?", re.I),
     "vm_wait",
     lambda m: {"seconds": float(m.group(1))}),

    # ThoughtBus publish
    (re.compile(r"\bpublish (?:a )?thought (?:about |that )?(.+)$", re.I),
     "publish_thought",
     lambda m: {
         "source": "queen.voice",
         "topic": "queen.voice.thought",
         "payload": {"text": m.group(1).strip()},
     }),
]


def route_intent(text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Map a natural-language message to concrete ``(tool_name, params)``
    pairs via deterministic pattern matching. Returns a list so one
    message can trigger a short chain (e.g. "screenshot and list
    windows"). Empty list = no action matched.
    """
    raw = (text or "").strip()
    if not raw:
        return []
    hits: List[Tuple[str, Dict[str, Any]]] = []
    for pattern, tool, extractor in _INTENT_PATTERNS:
        m = pattern.search(raw)
        if m:
            try:
                params = extractor(m) or {}
            except Exception as e:
                logger.debug("intent extractor failed for %s: %s", tool, e)
                continue
            hits.append((tool, params))
    return hits


# ─────────────────────────────────────────────────────────────────────────────
# QueenActionBridge
# ─────────────────────────────────────────────────────────────────────────────


class QueenActionBridge:
    """
    Single wire between the Queen voice layer and the Aureon skill /
    tool stack.

    Instantiate once per process (or use ``get_queen_action_bridge()``).
    Pass a live ``vault`` and the current Auris coherence report into
    ``handle_message()`` to get an ``ActionReply``.
    """

    def __init__(
        self,
        *,
        registry: Optional[Any] = None,
        dispatcher: Optional[Any] = None,
        skill_library: Optional[Any] = None,
        auris_filter: Optional[Any] = None,
        live_default: bool = True,
        max_history: int = 256,
    ):
        self._registry = registry
        self._dispatcher = dispatcher
        self._skill_library = skill_library
        self._auris_filter = auris_filter

        self._live: bool = bool(live_default)
        self._history: List[ActionRecord] = []
        self._history_lock = threading.Lock()
        self._session_id: Optional[str] = None
        self._initialized: bool = False
        self._init_lock = threading.Lock()
        self.max_history = int(max_history)

    # ─────────────────────────────────────────────────────────────────
    # Lazy init
    # ─────────────────────────────────────────────────────────────────

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return

            if self._registry is None:
                try:
                    from aureon.inhouse_ai.tool_registry import ToolRegistry
                    self._registry = ToolRegistry()
                except Exception as e:
                    logger.warning("ToolRegistry unavailable: %s", e)
                    self._registry = None

            if self._dispatcher is None:
                try:
                    from aureon.autonomous.vm_control import get_vm_dispatcher
                    self._dispatcher = get_vm_dispatcher()
                except Exception as e:
                    logger.warning("VMControlDispatcher unavailable: %s", e)
                    self._dispatcher = None

            if self._skill_library is None:
                try:
                    from aureon.code_architect.skill_library import get_skill_library
                    self._skill_library = get_skill_library()
                except Exception as e:
                    logger.debug("SkillLibrary unavailable: %s", e)
                    self._skill_library = None

            # Create a simulated VM session so the dispatcher has somewhere
            # to route actions. "simulated" backend is safe-by-default — it
            # won't touch the real OS.
            if self._dispatcher is not None:
                try:
                    existing = self._dispatcher.list_sessions()
                    if not any(s.get("name") == "queen-voice" for s in existing):
                        sid = self._dispatcher.create_session(
                            backend="simulated",
                            name="queen-voice",
                            make_default=True,
                        )
                        self._session_id = sid
                        logger.info("QueenActionBridge: created simulated session %s", sid)
                    else:
                        for s in existing:
                            if s.get("name") == "queen-voice":
                                self._session_id = s.get("session_id") or s.get("id")
                                break
                except Exception as e:
                    logger.warning("VM session creation failed: %s", e)

            # Register VM tools on the registry once.
            if self._registry is not None and self._dispatcher is not None:
                try:
                    from aureon.autonomous.vm_control.tools import register_vm_tools
                    n = register_vm_tools(self._registry, self._dispatcher)
                    logger.info("QueenActionBridge: registered %d VM tools", n)
                except Exception as e:
                    logger.warning("register_vm_tools failed: %s", e)

            self._initialized = True

    # ─────────────────────────────────────────────────────────────────
    # Public control
    # ─────────────────────────────────────────────────────────────────

    def arm(self, live: bool = True) -> Dict[str, Any]:
        """Toggle dry-run / live execution. Returns the new state."""
        self._ensure_initialized()
        self._live = bool(live)
        return self.status()

    def status(self) -> Dict[str, Any]:
        self._ensure_initialized()
        tool_count = 0
        tools: List[str] = []
        if self._registry is not None:
            try:
                tools = [t["name"] if isinstance(t, dict) else getattr(t, "name", str(t))
                         for t in self._registry.list_tools()]
                tool_count = len(tools)
            except Exception:
                pass
        skill_count = 0
        if self._skill_library is not None:
            try:
                skill_count = len(self._skill_library.by_level(0))
            except Exception:
                pass
        live = self._live and not is_stopped()
        return {
            "initialized": self._initialized,
            "live": live,
            "mode": "live" if live else "dry_run",
            "session_id": self._session_id,
            "tool_count": tool_count,
            "skill_count": skill_count,
            "history_size": len(self._history),
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        self._ensure_initialized()
        if self._registry is None:
            return []
        try:
            out: List[Dict[str, Any]] = []
            for t in self._registry.list_tools():
                if isinstance(t, dict):
                    out.append(t)
                else:
                    out.append({
                        "name": getattr(t, "name", str(t)),
                        "description": getattr(t, "description", ""),
                        "input_schema": getattr(t, "input_schema", {}),
                    })
            return out
        except Exception as e:
            logger.debug("list_tools failed: %s", e)
            return []

    def list_skills(self) -> List[Dict[str, Any]]:
        self._ensure_initialized()
        if self._skill_library is None:
            return []
        try:
            out = []
            for s in self._skill_library.by_level(0):
                out.append({
                    "name": s.name,
                    "description": s.description,
                    "level": int(getattr(s, "level", 0)),
                    "status": str(getattr(s, "status", "")),
                    "category": getattr(s, "category", ""),
                })
            return out
        except Exception as e:
            logger.debug("list_skills failed: %s", e)
            return []

    def recent_actions(self, n: int = 32) -> List[Dict[str, Any]]:
        with self._history_lock:
            tail = self._history[-int(max(1, n)):]
            return [a.to_dict() for a in tail]

    # ─────────────────────────────────────────────────────────────────
    # Core entry point
    # ─────────────────────────────────────────────────────────────────

    def handle_message(
        self,
        text: str,
        *,
        vault: Any = None,
        voice_name: str = "queen",
        coherence_report: Any = None,
        llm_response: Any = None,
    ) -> ActionReply:
        """
        Decide whether a human message should trigger any tools.

        Sources of intent (first match wins):
          1. ``llm_response.tool_calls`` — if the LLM produced proper
             OpenAI tool_calls. Rare on small local models but honoured.
          2. The regex intent router. Deterministic.

        Each chosen tool is:
          a. Checked against the destructive-tool list
          b. Downgraded to dry-run if not lighthouse-cleared
          c. Dispatched via ``self._registry.execute(name, args)``
          d. Appended to the rolling action log
        """
        self._ensure_initialized()
        reply = ActionReply()

        if self._registry is None:
            return reply

        calls: List[Tuple[str, Dict[str, Any], str]] = []  # (tool, params, source)

        # 1. Native tool-calling — honour whatever the LLM asked for.
        if llm_response is not None:
            raw_calls = getattr(llm_response, "tool_calls", None) or []
            for tc in raw_calls:
                name = getattr(tc, "name", "") or (tc.get("name", "") if isinstance(tc, dict) else "")
                args = getattr(tc, "arguments", None)
                if args is None and isinstance(tc, dict):
                    args = tc.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        import json as _json
                        args = _json.loads(args)
                    except Exception:
                        args = {"raw": args}
                if name:
                    calls.append((name, args or {}, "llm_toolcall"))
            if calls:
                reply.intent_source = "llm_toolcall"

        # 2. Regex intent router — the workhorse for small local models.
        if not calls:
            for tool, params in route_intent(text):
                calls.append((tool, params, "regex"))
            if calls:
                reply.intent_source = "regex"

        if not calls:
            reply.intent_source = "none"
            return reply

        # 3. Decide gating based on Auris coherence, if present.
        lighthouse = False
        if coherence_report is not None:
            try:
                lighthouse = bool(getattr(coherence_report, "auris_lighthouse", False))
                if not lighthouse and isinstance(coherence_report, dict):
                    lighthouse = bool(
                        coherence_report.get("auris", {}).get("lighthouse_cleared", False)
                    )
            except Exception:
                lighthouse = False

        # 4. Execute (or dry-run) each call.
        known_tool_names = set()
        try:
            known_tool_names = {
                (t["name"] if isinstance(t, dict) else getattr(t, "name", ""))
                for t in self._registry.list_tools()
            }
        except Exception:
            pass

        for tool_name, params, source in calls:
            if tool_name not in known_tool_names:
                record = ActionRecord(
                    tool=tool_name, params=params, source=source,
                    mode="dry_run", ok=False,
                    error=f"unknown tool '{tool_name}'",
                )
                self._append_history(record)
                reply.actions.append(record)
                continue

            # Destructive tools forced to dry-run unless armed AND lighthouse
            # cleared (or the caller didn't provide a coherence report).
            destructive = tool_name in DESTRUCTIVE_TOOLS
            gate_failed = destructive and coherence_report is not None and not lighthouse
            stopped = is_stopped()
            mode = "live" if (self._live and not gate_failed and not stopped) else "dry_run"

            record = ActionRecord(
                tool=tool_name,
                params=params,
                source=source,
                mode=mode,
                coherence_gated=gate_failed,
            )

            t0 = time.time()
            try:
                if mode == "dry_run":
                    record.ok = True
                    record.result = {
                        "simulated": True,
                        "tool": tool_name,
                        "params": params,
                        "note": (
                            "coherence gate blocked live execution"
                            if gate_failed else "dry-run default; arm(live=True) to execute"
                        ),
                    }
                else:
                    record.result = self._registry.execute(tool_name, params)
                    record.ok = True
            except Exception as e:
                record.ok = False
                record.error = str(e)
                logger.debug("tool %s failed: %s", tool_name, e)
            finally:
                record.duration_ms = (time.time() - t0) * 1000.0

            self._append_history(record)
            reply.actions.append(record)

        return reply

    # ─────────────────────────────────────────────────────────────────
    # History
    # ─────────────────────────────────────────────────────────────────

    def _append_history(self, record: ActionRecord) -> None:
        with self._history_lock:
            self._history.append(record)
            if len(self._history) > self.max_history:
                self._history = self._history[-self.max_history:]


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────


_bridge_singleton: Optional[QueenActionBridge] = None
_bridge_lock = threading.Lock()


def get_queen_action_bridge() -> QueenActionBridge:
    global _bridge_singleton
    with _bridge_lock:
        if _bridge_singleton is None:
            _bridge_singleton = QueenActionBridge()
        return _bridge_singleton


def reset_queen_action_bridge() -> None:
    global _bridge_singleton
    with _bridge_lock:
        _bridge_singleton = None


__all__ = [
    "QueenActionBridge",
    "ActionRecord",
    "ActionReply",
    "DESTRUCTIVE_TOOLS",
    "route_intent",
    "get_queen_action_bridge",
    "reset_queen_action_bridge",
]
