#!/usr/bin/env python3
"""
Tests for aureon.queen.queen_action_bridge.QueenActionBridge.

Covers:
  - route_intent() maps common phrasings to the right tool
  - handle_message() detects LLM tool_calls (native path)
  - handle_message() falls back to regex intent path
  - destructive tools auto dry-run unless armed + lighthouse cleared
  - arm() flips mode to live; non-destructive tools execute live
  - action log persists past calls and caps at max_history
  - status() reports tool count, skill count, mode
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aureon.queen.queen_action_bridge import (  # noqa: E402
    ActionRecord,
    ActionReply,
    DESTRUCTIVE_TOOLS,
    QueenActionBridge,
    route_intent,
)


def check(condition: bool, msg: str) -> None:
    """Pytest fails the test when the condition is false."""

    assert condition, msg


# ─────────────────────────────────────────────────────────────────────────────
# Stubs
# ─────────────────────────────────────────────────────────────────────────────


class StubRegistry:
    """Minimal ToolRegistry stand-in."""

    def __init__(self, tool_names):
        self._tools = [
            {"name": n, "description": f"stub {n}", "input_schema": {"type": "object"}}
            for n in tool_names
        ]
        self.executions = []  # list of (name, params)
        self.fail_tool = None

    def list_tools(self):
        return list(self._tools)

    def execute(self, name, params):
        self.executions.append((name, params))
        if name == self.fail_tool:
            raise RuntimeError(f"stub failure on {name}")
        return {"stdout": f"executed {name}", "status": "ok", "echo": params}


class StubDispatcher:
    """Minimal VMControlDispatcher stand-in."""

    def __init__(self):
        self._sessions = []

    def list_sessions(self):
        return list(self._sessions)

    def create_session(self, backend="simulated", name="", make_default=False, **kw):
        sid = f"sess-{len(self._sessions) + 1}"
        self._sessions.append({"session_id": sid, "name": name, "backend": backend})
        return sid


class StubCoherence:
    """Stand-in for AurisCoherenceReport."""

    def __init__(self, lighthouse=False):
        self.auris_lighthouse = lighthouse


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_route_intent_common_phrasings():
    print("\n[1] route_intent maps common phrasings")
    cases = [
        ("what is the state of the system?", "read_state"),
        ("show me the positions", "read_positions"),
        ("give me the current prices", "read_prices"),
        ("take a screenshot", "vm_screenshot"),
        ("what is the screen size?", "vm_get_screen_size"),
        ("where is the cursor", "vm_get_cursor_position"),
        ("list windows please", "vm_list_windows"),
        ("what active window is there", "vm_get_active_window"),
        ("click at 100, 200", "vm_left_click"),
        ("move the mouse to 300 400", "vm_mouse_move"),
        ('type "hello world"', "vm_type_text"),
        ("press enter", "vm_press_key"),
        ("wait 2 seconds", "vm_wait"),
        ("publish a thought that all is well", "publish_thought"),
    ]
    for phrase, expected_tool in cases:
        hits = route_intent(phrase)
        found = [t for t, _ in hits]
        check(expected_tool in found, f"'{phrase}' -> {expected_tool} (got {found})")


def test_route_intent_extracts_coordinates():
    print("\n[2] route_intent extracts numeric parameters")
    hits = route_intent("click at 512, 384")
    tool, params = hits[0]
    check(tool == "vm_left_click", f"tool == vm_left_click (got {tool})")
    check(params == {"x": 512, "y": 384}, f"coords extracted ({params})")

    hits = route_intent("move mouse to 10 20")
    tool, params = hits[0]
    check(tool == "vm_mouse_move", f"tool == vm_mouse_move (got {tool})")
    check(params == {"x": 10, "y": 20}, f"coords extracted ({params})")

    hits = route_intent('type "hello bridge"')
    tool, params = hits[0]
    check(tool == "vm_type_text", f"tool == vm_type_text (got {tool})")
    check(params == {"text": "hello bridge"}, f"text extracted ({params})")


def test_route_intent_empty_on_small_talk():
    print("\n[3] route_intent returns nothing on pure cognitive messages")
    for phrase in [
        "what are you aware of right now",
        "how does love feel",
        "tell me about yourself",
        "hi",
    ]:
        hits = route_intent(phrase)
        check(len(hits) == 0, f"'{phrase}' -> no intent (got {hits})")


def test_bridge_uses_regex_intent_path():
    print("\n[4] bridge uses the regex intent path when LLM has no tool_calls")
    reg = StubRegistry(["read_state", "vm_screenshot"])
    b = QueenActionBridge(registry=reg, dispatcher=StubDispatcher())
    b.arm(live=True)  # flip to live — non-destructive tools should execute
    reply = b.handle_message("show me the state")
    check(isinstance(reply, ActionReply), "returns ActionReply")
    check(reply.intent_source == "regex", f"intent_source == regex (got {reply.intent_source})")
    check(len(reply.actions) == 1, f"one action recorded ({len(reply.actions)})")
    act = reply.actions[0]
    check(act.tool == "read_state", f"tool == read_state (got {act.tool})")
    check(act.mode == "live", f"mode == live (got {act.mode})")
    check(act.ok is True, "execution succeeded")
    check(reg.executions == [("read_state", {"keys": "all"})], f"registry.execute called once ({reg.executions})")


def test_bridge_honours_native_llm_tool_calls():
    print("\n[5] bridge honours proper LLM tool_calls")
    reg = StubRegistry(["read_positions"])
    b = QueenActionBridge(registry=reg, dispatcher=StubDispatcher(), live_default=True)

    class FakeToolCall:
        def __init__(self, name, args):
            self.name = name
            self.arguments = args

    class FakeLLMResponse:
        def __init__(self, calls):
            self.tool_calls = calls

    llm = FakeLLMResponse([FakeToolCall("read_positions", {})])
    reply = b.handle_message("whatever", llm_response=llm)
    check(reply.intent_source == "llm_toolcall", f"intent_source == llm_toolcall (got {reply.intent_source})")
    check(len(reply.actions) == 1, "one action")
    check(reply.actions[0].tool == "read_positions", "tool from LLM honored")


def test_destructive_tool_dry_run_without_lighthouse():
    print("\n[6] destructive tool stays in dry_run without lighthouse clearance")
    reg = StubRegistry(["vm_execute_shell"])
    b = QueenActionBridge(registry=reg, dispatcher=StubDispatcher(), live_default=True)

    class FakeToolCall:
        def __init__(self, name, args):
            self.name = name
            self.arguments = args

    class FakeLLMResponse:
        def __init__(self, calls):
            self.tool_calls = calls

    llm = FakeLLMResponse([FakeToolCall("vm_execute_shell", {"command": "dir"})])
    coh = StubCoherence(lighthouse=False)
    reply = b.handle_message("run dir", llm_response=llm, coherence_report=coh)
    act = reply.actions[0]
    check(act.mode == "dry_run", f"mode forced to dry_run (got {act.mode})")
    check(act.coherence_gated is True, "coherence_gated flag set")
    check(reg.executions == [], f"registry.execute NOT called ({reg.executions})")
    check(act.ok is True, "dry-run still reports ok=True")
    # And the result payload should say so.
    res = act.result or {}
    check(res.get("simulated") is True, "dry-run result marked simulated")


def test_destructive_tool_fires_with_lighthouse():
    print("\n[7] destructive tool executes when armed AND lighthouse cleared")
    reg = StubRegistry(["vm_execute_shell"])
    b = QueenActionBridge(registry=reg, dispatcher=StubDispatcher(), live_default=True)

    class FakeToolCall:
        def __init__(self, name, args):
            self.name = name
            self.arguments = args

    class FakeLLMResponse:
        def __init__(self, calls):
            self.tool_calls = calls

    llm = FakeLLMResponse([FakeToolCall("vm_execute_shell", {"command": "whoami"})])
    coh = StubCoherence(lighthouse=True)
    reply = b.handle_message("whoami", llm_response=llm, coherence_report=coh)
    act = reply.actions[0]
    check(act.mode == "live", f"mode == live (got {act.mode})")
    check(act.coherence_gated is False, "coherence_gated flag clear")
    check(len(reg.executions) == 1, "registry.execute called once")
    check(act.ok is True, "execution reported ok")


def test_unknown_tool_records_failure():
    print("\n[8] unknown tool name records a failed action")
    reg = StubRegistry(["read_state"])
    b = QueenActionBridge(registry=reg, dispatcher=StubDispatcher(), live_default=True)

    class FakeToolCall:
        def __init__(self, name, args):
            self.name = name
            self.arguments = args

    class FakeLLMResponse:
        def __init__(self, calls):
            self.tool_calls = calls

    llm = FakeLLMResponse([FakeToolCall("not_a_tool", {})])
    reply = b.handle_message("whatever", llm_response=llm)
    check(len(reply.actions) == 1, "action recorded")
    act = reply.actions[0]
    check(act.ok is False, "ok is False")
    check("unknown" in act.error.lower(), f"error mentions unknown ({act.error})")
    check(reg.executions == [], "registry.execute not called")


def test_history_cap_and_recent_actions():
    print("\n[9] action history is capped and recent_actions returns tail")
    reg = StubRegistry(["read_state"])
    b = QueenActionBridge(
        registry=reg, dispatcher=StubDispatcher(),
        live_default=True, max_history=5,
    )
    for _i in range(12):
        b.handle_message("state check")
    hist = b.recent_actions(n=100)
    check(len(hist) == 5, f"history capped at max_history (got {len(hist)})")
    # recent_actions(3) returns only the last 3
    tail = b.recent_actions(n=3)
    check(len(tail) == 3, f"recent_actions(3) returns 3 (got {len(tail)})")


def test_status_reports_mode_and_counts():
    print("\n[10] status reports mode, tool count, history size")
    reg = StubRegistry(["read_state", "vm_screenshot", "vm_left_click"])
    b = QueenActionBridge(registry=reg, dispatcher=StubDispatcher())
    s1 = b.status()
    check(s1["mode"] == "live", "default mode is live")
    check(s1["live"] is True, "live flag True by default")
    check(s1["tool_count"] == 3, f"tool_count == 3 (got {s1['tool_count']})")
    b.arm(live=True)
    s2 = b.status()
    check(s2["mode"] == "live", "mode flips to live after arm")
    check(s2["live"] is True, "live flag True")


def test_to_dict_is_json_safe():
    print("\n[11] ActionRecord.to_dict and ActionReply.to_dict are JSON-safe")
    import json as _json
    reg = StubRegistry(["read_state"])
    b = QueenActionBridge(registry=reg, dispatcher=StubDispatcher(), live_default=True)
    reply = b.handle_message("state")
    s = _json.dumps(reply.to_dict())
    check(isinstance(s, str) and len(s) > 20, "reply.to_dict round-trips through json")
    for act in reply.actions:
        _json.dumps(act.to_dict())  # must not raise
    check(True, "action.to_dict round-trips through json")


def _shell_call(command: str):
    class _Call:
        def __init__(self, name, args):
            self.name = name
            self.arguments = args

    class _Resp:
        def __init__(self, calls):
            self.tool_calls = calls

    return _Resp([_Call("execute_shell", {"command": command})])


def test_chat_execute_shell_without_a_report_stays_dry_run():
    """Chat passes coherence_report=None. A missing report is not a lighthouse pass."""

    reg = StubRegistry(["execute_shell"])
    bridge = QueenActionBridge(registry=reg, dispatcher=StubDispatcher(), live_default=True)
    reply = bridge.handle_message(
        "run a command",
        llm_response=_shell_call("echo hi"),
        coherence_report=None,
    )
    act = reply.actions[0]
    assert act.tool == "execute_shell"
    assert act.mode == "dry_run"
    assert act.coherence_gated is True
    assert reg.executions == []


def test_api_queen_execute_shell_without_a_report_stays_dry_run():
    """/api/queen/execute omits the report. execute_shell stays dry_run while live."""

    reg = StubRegistry(["execute_shell"])
    bridge = QueenActionBridge(registry=reg, dispatcher=StubDispatcher(), live_default=True)
    reply = bridge.handle_message("execute execute_shell", llm_response=_shell_call("pwd"))
    act = reply.actions[0]
    assert act.mode == "dry_run"
    assert act.coherence_gated is True
    assert reg.executions == []


def test_stop_file_keeps_a_live_queen_action_dry_run(monkeypatch, tmp_path):
    """Goes red if the handle_message stop check is removed."""

    stop = tmp_path / "computer_use.stop"
    stop.write_text("human\n", encoding="utf-8")
    monkeypatch.setenv("AUREON_COMPUTER_USE_STOP_FILE", str(stop))
    reg = StubRegistry(["read_state"])
    bridge = QueenActionBridge(registry=reg, dispatcher=StubDispatcher(), live_default=True)
    reply = bridge.handle_message("show me the state")
    assert reply.actions[0].mode == "dry_run"
    assert reg.executions == []
    status = bridge.status()
    assert status["mode"] == "dry_run"
    assert status["live"] is False


def test_governance_block_is_not_recorded_as_a_live_success():
    """A blocked dispatch is ok=False with the reason, not LIVE ... -> ok."""

    reg = StubRegistry(["execute_shell"])
    reg.execute = lambda name, params: {  # type: ignore[method-assign]
        "blocked": True,
        "reason": "governance_hold",
    }
    # lighthouse cleared so the call is allowed to reach the registry
    class _Coh:
        auris_lighthouse = True

    class _Call:
        def __init__(self):
            self.name = "execute_shell"
            self.arguments = {"command": "pwd"}

    class _Resp:
        def __init__(self):
            self.tool_calls = [_Call()]

    bridge = QueenActionBridge(registry=reg, dispatcher=StubDispatcher(), live_default=True)
    reply = bridge.handle_message("execute", llm_response=_Resp(), coherence_report=_Coh())
    act = reply.actions[0]
    assert act.mode == "live"
    assert act.ok is False
    assert act.error == "governance_hold"
    assert act.to_dict()["blocked"] is True
    tag = "LIVE" if act.mode == "live" else "dry"
    shown = "ok" if act.ok else f"FAIL {act.error[:60]}"
    assert "-> ok" not in f"  {tag} {act.tool} -> {shown}"
