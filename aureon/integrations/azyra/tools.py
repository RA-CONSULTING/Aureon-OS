"""Azyra operator tools — ToolRegistry bindings for the gated desktop bridge.

Every tool routes through :class:`AzyraOperatorBridge`, so the same gates apply
whether an in-house agent or a human console calls them. Refusals come back as
structured JSON with named blockers — never as a fabricated success.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from aureon.integrations.azyra.operator_bridge import AzyraOperatorBridge

AZYRA_OPERATOR_TOOL_NAMES = (
    "azyra_operator_status",
    "azyra_operator_capabilities",
    "azyra_operator_diagnostics",
    "azyra_operator_focus",
    "azyra_operator_click",
    "azyra_operator_type_text",
    "azyra_operator_hotkey",
    "azyra_operator_capture_screen",
    "azyra_operator_run_workflow",
)

_bridge: AzyraOperatorBridge | None = None


def get_azyra_operator_bridge() -> AzyraOperatorBridge:
    """Process-wide bridge singleton (gates re-read env at construction)."""
    global _bridge
    if _bridge is None:
        _bridge = AzyraOperatorBridge()
    return _bridge


def reset_azyra_operator_bridge() -> None:
    """Drop the singleton (tests / gate changes)."""
    global _bridge
    _bridge = None


def _dumps(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def _tool_status(args: Dict[str, Any]) -> str:
    return _dumps(get_azyra_operator_bridge().status())


def _tool_capabilities(args: Dict[str, Any]) -> str:
    return _dumps(get_azyra_operator_bridge().capabilities())


def _tool_diagnostics(args: Dict[str, Any]) -> str:
    return _dumps(get_azyra_operator_bridge().input_route_diagnostics())


def _tool_focus(args: Dict[str, Any]) -> str:
    return _dumps(get_azyra_operator_bridge().focus().to_dict())


def _tool_click(args: Dict[str, Any]) -> str:
    bridge = get_azyra_operator_bridge()
    return _dumps(bridge.click_window(
        int(args.get("x", 0)), int(args.get("y", 0)),
        submit_like=bool(args.get("submit_like", False)),
    ).to_dict())


def _tool_type_text(args: Dict[str, Any]) -> str:
    bridge = get_azyra_operator_bridge()
    return _dumps(bridge.type_text(str(args.get("text") or ""),
                                   method=str(args.get("method") or "type")).to_dict())


def _tool_hotkey(args: Dict[str, Any]) -> str:
    keys = args.get("keys")
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.split("+") if k.strip()]
    return _dumps(get_azyra_operator_bridge().hotkey(list(keys or [])).to_dict())


def _tool_capture(args: Dict[str, Any]) -> str:
    path = Path(str(args.get("path") or "state/azyra_operator/captures/capture.png"))
    return _dumps(get_azyra_operator_bridge().capture_screen(
        path, window_only=bool(args.get("window_only", True))).to_dict())


def _tool_run_workflow(args: Dict[str, Any]) -> str:
    steps = args.get("steps")
    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except json.JSONDecodeError:
            return _dumps({"ok": False, "error": "steps must be a JSON list of step objects"})
    if not isinstance(steps, list):
        return _dumps({"ok": False, "error": "steps must be a list"})
    return _dumps(get_azyra_operator_bridge().run_workflow(steps))


def register_azyra_operator_tools(registry: Any) -> list[str]:
    """Bind all azyra_operator_* tools onto a ToolRegistry. Returns the names."""
    specs = [
        ("azyra_operator_status", "Report the Azyra bridge window/process/gate status.",
         {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, _tool_status),
        ("azyra_operator_capabilities", "Report what the Azyra bridge can do right now, with blockers.",
         {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, _tool_capabilities),
        ("azyra_operator_diagnostics", "Preflight the RemoteApp keyboard input route (honest blockers).",
         {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, _tool_diagnostics),
        ("azyra_operator_focus", "Verify/bring the Azyra window to the foreground (focus gate).",
         {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, _tool_focus),
        ("azyra_operator_click", "Click at window coordinates (input gate; submit_like needs the submit gate).",
         {"type": "object", "properties": {
             "x": {"type": "integer"}, "y": {"type": "integer"},
             "submit_like": {"type": "boolean"}},
          "required": ["x", "y"], "additionalProperties": False}, _tool_click),
        ("azyra_operator_type_text", "Type text into the focused field (input gate + proven keyboard route).",
         {"type": "object", "properties": {
             "text": {"type": "string"}, "method": {"type": "string"}},
          "required": ["text"], "additionalProperties": False}, _tool_type_text),
        ("azyra_operator_hotkey", "Send a hotkey chord, e.g. 'ctrl+a' (input gate + proven keyboard route).",
         {"type": "object", "properties": {"keys": {"type": "string"}},
          "required": ["keys"], "additionalProperties": False}, _tool_hotkey),
        ("azyra_operator_capture_screen", "Capture stage evidence to a PNG file.",
         {"type": "object", "properties": {
             "path": {"type": "string"}, "window_only": {"type": "boolean"}},
          "required": [], "additionalProperties": False}, _tool_capture),
        ("azyra_operator_run_workflow", "Run a declarative gated step list; stops at the first refusal.",
         {"type": "object", "properties": {"steps": {"type": "string",
                                                     "description": "JSON list of step objects"}},
          "required": ["steps"], "additionalProperties": False}, _tool_run_workflow),
    ]
    for name, description, schema, handler in specs:
        registry.define_tool(name=name, description=description, input_schema=schema, handler=handler)
    return [name for name, *_ in specs]


__all__ = [
    "AZYRA_OPERATOR_TOOL_NAMES",
    "get_azyra_operator_bridge",
    "register_azyra_operator_tools",
    "reset_azyra_operator_bridge",
]
