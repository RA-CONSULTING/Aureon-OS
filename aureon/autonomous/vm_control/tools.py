"""
VM Control Tool Definitions — Exposes VM actions to in-house AI agents
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Registers 20 tools with an in-house AI ToolRegistry so agents can control
Windows VMs exactly like Claude's "computer use" tools.

The tools use the same wire format the existing ToolRegistry expects
(name, description, input_schema, handler). Agents see them alongside the
5 built-in tools in their tool list and can call them the same way.

Tool list:
  Session management:
    vm_create_session, vm_list_sessions, vm_set_default_session,
    vm_destroy_session, vm_session_status

  Session control:
    vm_arm, vm_disarm, vm_emergency_stop, vm_clear_emergency_stop

  Desktop actions (the "computer use" set):
    vm_screenshot, vm_mouse_move, vm_left_click, vm_right_click,
    vm_middle_click, vm_double_click, vm_triple_click, vm_left_click_drag,
    vm_scroll, vm_type_text, vm_press_key, vm_hotkey

  Introspection:
    vm_get_cursor_position, vm_get_screen_size,
    vm_list_windows, vm_get_active_window, vm_focus_window,
    vm_wait

  Shell:
    vm_execute_shell, vm_execute_powershell
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from aureon.autonomous.vm_control.dispatcher import (
    VMControlDispatcher,
    get_vm_dispatcher,
)

# Full list of tool names so callers can introspect them
VM_TOOL_NAMES = [
    # Session management
    "vm_create_session",
    "vm_list_sessions",
    "vm_set_default_session",
    "vm_destroy_session",
    "vm_session_status",
    # Session control
    "vm_arm",
    "vm_disarm",
    "vm_emergency_stop",
    "vm_clear_emergency_stop",
    # Desktop actions
    "vm_screenshot",
    "vm_mouse_move",
    "vm_left_click",
    "vm_right_click",
    "vm_middle_click",
    "vm_double_click",
    "vm_triple_click",
    "vm_left_click_drag",
    "vm_scroll",
    "vm_type_text",
    "vm_press_key",
    "vm_hotkey",
    # Introspection
    "vm_get_cursor_position",
    "vm_get_screen_size",
    "vm_list_windows",
    "vm_get_active_window",
    "vm_focus_window",
    "vm_wait",
    # Shell
    "vm_execute_shell",
    "vm_execute_powershell",
]


# ─────────────────────────────────────────────────────────────────────────────
# Handler factory
# ─────────────────────────────────────────────────────────────────────────────


def _make_action_handler(dispatcher: VMControlDispatcher, action_name: str):
    """Create a handler that dispatches the action with the tool's args."""

    def handler(args: Dict[str, Any]) -> str:
        args = dict(args) if isinstance(args, dict) else {}
        session_id = args.pop("session_id", None)
        confirm_token = args.pop("confirm_token", None)
        result = dispatcher.dispatch(
            action_name=action_name,
            params=args,
            session_id=session_id,
            source="tool",
            confirm_token=str(confirm_token) if confirm_token is not None else None,
        )
        return json.dumps(result)

    return handler


# ─────────────────────────────────────────────────────────────────────────────
# Session management handlers
# ─────────────────────────────────────────────────────────────────────────────


def _make_session_handlers(dispatcher: VMControlDispatcher) -> Dict[str, Any]:
    def create_session(args: Dict[str, Any]) -> str:
        try:
            # Extract known creation params
            backend = args.get("backend", "simulated")
            name = args.get("name", "")
            host = args.get("host", "")
            make_default = bool(args.get("make_default", False))

            # Build kwargs for the backend constructor
            extra = {}
            for key in ("username", "password", "key_filename", "port", "transport", "use_ssl", "platform"):
                if key in args and args[key] not in (None, ""):
                    extra[key] = args[key]

            sid = dispatcher.create_session(
                backend=backend,
                name=name,
                host=host,
                make_default=make_default,
                **extra,
            )
            return json.dumps({"ok": True, "session_id": sid, "backend": backend, "name": name})
        except Exception as e:
            return json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"})

    def list_sessions(args: Dict[str, Any]) -> str:
        return json.dumps({"ok": True, "sessions": dispatcher.list_sessions()})

    def set_default_session(args: Dict[str, Any]) -> str:
        sid = args.get("session_id", "")
        ok = dispatcher.set_default(sid)
        return json.dumps({"ok": ok, "default_session_id": sid})

    def destroy_session(args: Dict[str, Any]) -> str:
        sid = args.get("session_id", "")
        ok = dispatcher.destroy_session(sid)
        return json.dumps({"ok": ok, "session_id": sid})

    def session_status(args: Dict[str, Any]) -> str:
        sid = args.get("session_id")
        controller = dispatcher.get_session(sid)
        if not controller:
            return json.dumps({"ok": False, "error": "no_session"})
        return json.dumps({"ok": True, "session": controller.session.to_dict()})

    def arm(args: Dict[str, Any]) -> str:
        sid = args.get("session_id")
        dry_run = bool(args.get("dry_run", True))
        confirmation_token = args.get("confirmation_token")
        controller = dispatcher.get_session(sid)
        if not controller:
            return json.dumps({"ok": False, "error": "no_session"})
        return json.dumps(controller.arm(
            dry_run=dry_run,
            confirmation_token=str(confirmation_token) if confirmation_token is not None else None,
        ))

    def disarm(args: Dict[str, Any]) -> str:
        sid = args.get("session_id")
        controller = dispatcher.get_session(sid)
        if not controller:
            return json.dumps({"ok": False, "error": "no_session"})
        return json.dumps(controller.disarm())

    def emergency_stop(args: Dict[str, Any]) -> str:
        sid = args.get("session_id")
        if sid:
            controller = dispatcher.get_session(sid)
            if not controller:
                return json.dumps({"ok": False, "error": "no_session"})
            return json.dumps(controller.emergency_stop())
        return json.dumps(dispatcher.emergency_stop_all())

    def clear_emergency_stop(args: Dict[str, Any]) -> str:
        sid = args.get("session_id")
        if sid:
            controller = dispatcher.get_session(sid)
            if not controller:
                return json.dumps({"ok": False, "error": "no_session"})
            return json.dumps(controller.clear_emergency_stop())
        return json.dumps(dispatcher.clear_emergency_stop_all())

    return {
        "vm_create_session": create_session,
        "vm_list_sessions": list_sessions,
        "vm_set_default_session": set_default_session,
        "vm_destroy_session": destroy_session,
        "vm_session_status": session_status,
        "vm_arm": arm,
        "vm_disarm": disarm,
        "vm_emergency_stop": emergency_stop,
        "vm_clear_emergency_stop": clear_emergency_stop,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────────────────


def register_vm_tools(
    registry: Any,
    dispatcher: Optional[VMControlDispatcher] = None,
) -> int:
    """
    Register all VM control tools with an in-house AI ToolRegistry.

    Args:
        registry: An aureon.inhouse_ai.ToolRegistry instance
        dispatcher: Optional custom dispatcher (defaults to singleton)

    Returns:
        Number of tools registered.
    """
    dispatcher = dispatcher or get_vm_dispatcher()
    session_handlers = _make_session_handlers(dispatcher)

    count = 0

    # ── Session management ──────────────────────────────────────────────
    registry.define_tool(
        name="vm_create_session",
        description=(
            "Create a new VM control session. Backend can be 'simulated' (in-memory, "
            "no real VM needed), 'winrm' (real Windows via PowerShell remoting), or "
            "'ssh' (cross-platform via SSH). Returns the session_id to use in subsequent calls."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "backend": {"type": "string", "enum": ["simulated", "winrm", "ssh"], "description": "Backend type"},
                "name": {"type": "string", "description": "Friendly name for the session"},
                "host": {"type": "string", "description": "VM hostname or IP address"},
                "username": {"type": "string", "description": "Username (winrm/ssh)"},
                "password": {"type": "string", "description": "Password (winrm/ssh)"},
                "make_default": {"type": "boolean", "description": "Set as default session"},
            },
            "required": ["backend"],
            "additionalProperties": True,
        },
        handler=session_handlers["vm_create_session"],
    )
    count += 1

    registry.define_tool(
        name="vm_list_sessions",
        description="List all active VM sessions with their backend, armed state, and action counts.",
        input_schema={"type": "object", "properties": {}, "required": []},
        handler=session_handlers["vm_list_sessions"],
    )
    count += 1

    registry.define_tool(
        name="vm_set_default_session",
        description="Set the default VM session. Subsequent tool calls without session_id will use this.",
        input_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        handler=session_handlers["vm_set_default_session"],
    )
    count += 1

    registry.define_tool(
        name="vm_destroy_session",
        description="Destroy a VM session, disconnecting and cleaning up resources.",
        input_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        handler=session_handlers["vm_destroy_session"],
    )
    count += 1

    registry.define_tool(
        name="vm_session_status",
        description="Get full status of a VM session: armed state, action count, last action, history count.",
        input_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": [],
        },
        handler=session_handlers["vm_session_status"],
    )
    count += 1

    # ── Session control (arm/disarm/emergency) ──────────────────────────
    registry.define_tool(
        name="vm_arm",
        description="Arm a VM session. Required before any non-safe action can run. Set dry_run=true to simulate without executing.",
        input_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "dry_run": {"type": "boolean", "description": "If true, actions are simulated only"},
                "confirmation_token": {
                    "type": "string",
                    "description": "Ephemeral token required to arm a non-simulated backend live",
                },
            },
            "required": [],
        },
        handler=session_handlers["vm_arm"],
    )
    count += 1

    registry.define_tool(
        name="vm_disarm",
        description="Disarm a VM session. All non-safe actions will be rejected.",
        input_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": [],
        },
        handler=session_handlers["vm_disarm"],
    )
    count += 1

    registry.define_tool(
        name="vm_emergency_stop",
        description="Emergency stop. Disarms the session and clears all pending actions. If session_id is omitted, stops ALL sessions globally.",
        input_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": [],
        },
        handler=session_handlers["vm_emergency_stop"],
    )
    count += 1

    registry.define_tool(
        name="vm_clear_emergency_stop",
        description="Clear the emergency stop flag. The session must still be re-armed before actions can run.",
        input_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": [],
        },
        handler=session_handlers["vm_clear_emergency_stop"],
    )
    count += 1

    # ── Desktop actions ─────────────────────────────────────────────────
    registry.define_tool(
        name="vm_screenshot",
        description="Take a screenshot of the VM desktop. Returns a base64-encoded PNG image plus width and height. This is a SAFE action that works without arming.",
        input_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": [],
        },
        handler=_make_action_handler(dispatcher, "screenshot"),
    )
    count += 1

    registry.define_tool(
        name="vm_mouse_move",
        description="Move the cursor to (x, y). Requires the session to be armed.",
        input_schema={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "session_id": {"type": "string"},
            },
            "required": ["x", "y"],
        },
        handler=_make_action_handler(dispatcher, "mouse_move"),
    )
    count += 1

    registry.define_tool(
        name="vm_left_click",
        description="Left-click at (x, y) or at the current cursor position if x/y are omitted.",
        input_schema={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "session_id": {"type": "string"},
            },
            "required": [],
        },
        handler=_make_action_handler(dispatcher, "left_click"),
    )
    count += 1

    registry.define_tool(
        name="vm_right_click",
        description="Right-click at (x, y) or at the current cursor position if x/y are omitted.",
        input_schema={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "session_id": {"type": "string"},
            },
            "required": [],
        },
        handler=_make_action_handler(dispatcher, "right_click"),
    )
    count += 1

    registry.define_tool(
        name="vm_middle_click",
        description="Middle-click at (x, y) or at the current cursor position if x/y are omitted.",
        input_schema={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "session_id": {"type": "string"},
            },
            "required": [],
        },
        handler=_make_action_handler(dispatcher, "middle_click"),
    )
    count += 1

    registry.define_tool(
        name="vm_double_click",
        description="Double-click at (x, y) or at the current cursor position if x/y are omitted.",
        input_schema={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "session_id": {"type": "string"},
            },
            "required": [],
        },
        handler=_make_action_handler(dispatcher, "double_click"),
    )
    count += 1

    registry.define_tool(
        name="vm_triple_click",
        description="Triple-click at (x, y) to select a line of text.",
        input_schema={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "session_id": {"type": "string"},
            },
            "required": [],
        },
        handler=_make_action_handler(dispatcher, "triple_click"),
    )
    count += 1

    registry.define_tool(
        name="vm_left_click_drag",
        description="Left-click-and-drag from (start_x, start_y) to (end_x, end_y).",
        input_schema={
            "type": "object",
            "properties": {
                "start_x": {"type": "integer"},
                "start_y": {"type": "integer"},
                "end_x": {"type": "integer"},
                "end_y": {"type": "integer"},
                "session_id": {"type": "string"},
            },
            "required": ["start_x", "start_y", "end_x", "end_y"],
        },
        handler=_make_action_handler(dispatcher, "left_click_drag"),
    )
    count += 1

    registry.define_tool(
        name="vm_scroll",
        description="Scroll at (x, y). direction: 'up' | 'down' | 'left' | 'right'. amount is the number of scroll notches (default 3).",
        input_schema={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                "amount": {"type": "integer"},
                "session_id": {"type": "string"},
            },
            "required": ["x", "y"],
        },
        handler=_make_action_handler(dispatcher, "scroll"),
    )
    count += 1

    registry.define_tool(
        name="vm_type_text",
        description="Type arbitrary text as if on the keyboard. HIGH RISK — requires arming.",
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["text"],
        },
        handler=_make_action_handler(dispatcher, "type_text"),
    )
    count += 1

    registry.define_tool(
        name="vm_press_key",
        description="Press a single key. Examples: 'enter', 'escape', 'tab', 'f1', 'backspace', 'space'.",
        input_schema={
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["key"],
        },
        handler=_make_action_handler(dispatcher, "press_key"),
    )
    count += 1

    registry.define_tool(
        name="vm_hotkey",
        description="Press a key combination. Example: ['ctrl', 'c'] for copy, ['ctrl', 'shift', 't'] for reopen tab.",
        input_schema={
            "type": "object",
            "properties": {
                "keys": {"type": "array", "items": {"type": "string"}},
                "session_id": {"type": "string"},
            },
            "required": ["keys"],
        },
        handler=_make_action_handler(dispatcher, "hotkey"),
    )
    count += 1

    # ── Introspection ───────────────────────────────────────────────────
    registry.define_tool(
        name="vm_get_cursor_position",
        description="Get the current cursor position. SAFE — works without arming.",
        input_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": [],
        },
        handler=_make_action_handler(dispatcher, "get_cursor_position"),
    )
    count += 1

    registry.define_tool(
        name="vm_get_screen_size",
        description="Get the VM screen dimensions. SAFE — works without arming.",
        input_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": [],
        },
        handler=_make_action_handler(dispatcher, "get_screen_size"),
    )
    count += 1

    registry.define_tool(
        name="vm_list_windows",
        description="List all open windows on the VM. SAFE — works without arming.",
        input_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": [],
        },
        handler=_make_action_handler(dispatcher, "list_windows"),
    )
    count += 1

    registry.define_tool(
        name="vm_get_active_window",
        description="Get the currently focused window. SAFE — works without arming.",
        input_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": [],
        },
        handler=_make_action_handler(dispatcher, "get_active_window"),
    )
    count += 1

    registry.define_tool(
        name="vm_focus_window",
        description="Focus the window whose title matches the given string (substring match).",
        input_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["title"],
        },
        handler=_make_action_handler(dispatcher, "focus_window"),
    )
    count += 1

    registry.define_tool(
        name="vm_wait",
        description="Wait N seconds (capped at 30). Useful between actions for the UI to settle. SAFE.",
        input_schema={
            "type": "object",
            "properties": {
                "seconds": {"type": "number"},
                "session_id": {"type": "string"},
            },
            "required": ["seconds"],
        },
        handler=_make_action_handler(dispatcher, "wait"),
    )
    count += 1

    # ── Shell execution ─────────────────────────────────────────────────
    registry.define_tool(
        name="vm_execute_shell",
        description="Execute a cmd.exe command on the VM. CRITICAL — requires arming.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "integer"},
                "session_id": {"type": "string"},
            },
            "required": ["command"],
        },
        handler=_make_action_handler(dispatcher, "execute_shell"),
    )
    count += 1

    registry.define_tool(
        name="vm_execute_powershell",
        description="Execute a PowerShell command on the VM. CRITICAL — requires arming.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "integer"},
                "session_id": {"type": "string"},
            },
            "required": ["command"],
        },
        handler=_make_action_handler(dispatcher, "execute_powershell"),
    )
    count += 1

    return count
