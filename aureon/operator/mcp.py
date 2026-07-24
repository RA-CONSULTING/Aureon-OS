"""
🔌 Aureon Operator — MCP server (Model Context Protocol).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The mount lets a model client integrate by swapping its OpenAI ``base_url``. **MCP**
is the other door: a user adds Aureon as a *connector* in their agent's own UI
(Claude Desktop/Code, Cursor, …) and the agent calls Aureon's **tools** — no repo
clone, no base_url surgery. Every tool runs *through* Aureon as the host mind
(grounded + vetted); a boundary-crossing call comes back with an honest refusal and
**nothing executes**.

This module is the **pure protocol layer** — a minimal, hermetic JSON-RPC 2.0 / MCP
handler with no Flask and no engine imports (mirrors ``mount.py``'s pure-translation
style). ``dispatch(message, tool_runner)`` routes an MCP message and calls a
caller-supplied ``tool_runner`` for ``tools/call`` — so it is unit-testable with a
fake runner, and both transports (the hosted ``POST /mcp`` route and the ``aureon-mcp``
stdio server) share this one implementation.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

from aureon.operator.mount import MOUNT_API_VERSION

# The MCP protocol revision we speak (widely supported by current clients).
PROTOCOL_VERSION = "2024-11-05"

SERVER_INFO: Dict[str, str] = {"name": "aureon-mount", "version": MOUNT_API_VERSION}

# JSON-RPC 2.0 standard error codes.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# The tools an external agent sees. Each runs through Aureon's grounded, vetted
# engines — the callers wire the names to reason()/respond()/integration_manifest().
_PROMPT_SCHEMA = {
    "type": "object",
    "properties": {
        "prompt": {"type": "string", "description": "The question or task to ground and answer."},
        "session_id": {"type": "string", "description": "Optional stable session id for continuity."},
    },
    "required": ["prompt"],
    "additionalProperties": False,
}

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "aureon_reason",
        "description": (
            "Answer a prompt through Aureon's grounded single mind — repo-wide grounding + "
            "tools + conscience veto. Returns the grounded, vetted answer; a request crossing a "
            "hard authority boundary (trading/payments/filing/credentials) is refused and nothing "
            "executes."
        ),
        "inputSchema": _PROMPT_SCHEMA,
    },
    {
        "name": "aureon_switchboard",
        "description": (
            "Answer a prompt through Aureon's multi-model switchboard — ground → fan-out across "
            "every reachable model → consensus collapse → conscience veto. Same safety boundary."
        ),
        "inputSchema": _PROMPT_SCHEMA,
    },
    {
        "name": "aureon_integration",
        "description": (
            "Return Aureon's self-describing integration manifest (engines, endpoints, provenance "
            "keys, how to mount) — the map an agent reads to integrate. No arguments."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]

TOOL_NAMES: Tuple[str, ...] = tuple(t["name"] for t in TOOLS)

# A tool_runner takes (name, arguments) and returns (text, structured, is_error).
ToolRunner = Callable[[str, Dict[str, Any]], Tuple[str, Any, bool]]


class UnknownTool(Exception):
    """Raised by a tool_runner when asked for a tool name it doesn't serve."""


def jsonrpc_result(msg_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def jsonrpc_error(msg_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": msg_id, "error": err}


def initialize_result() -> Dict[str, Any]:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": dict(SERVER_INFO),
        "instructions": (
            "Aureon is the grounded host mind. Call aureon_reason (or aureon_switchboard) to get a "
            "repo-grounded, conscience-vetted answer; aureon_integration returns the integration map. "
            "Aureon never trades, pays, or files — boundary-crossing requests are refused."
        ),
    }


def _tool_content(text: str, structured: Any, is_error: bool) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "content": [{"type": "text", "text": text}],
        "isError": bool(is_error),
    }
    if isinstance(structured, dict):
        out["structuredContent"] = structured
    return out


def dispatch(message: Any, tool_runner: ToolRunner | None = None) -> Dict[str, Any] | None:
    """Route one MCP / JSON-RPC message. Returns the response object, or ``None``
    for a notification (no reply). Never raises — protocol problems become JSON-RPC
    error responses. ``tool_runner`` is required only for ``tools/call``."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return jsonrpc_error(None, INVALID_REQUEST, "expected a JSON-RPC 2.0 object")

    method = message.get("method")
    msg_id = message.get("id")
    is_notification = "id" not in message

    if not isinstance(method, str):
        return None if is_notification else jsonrpc_error(msg_id, INVALID_REQUEST, "missing method")

    # Notifications (no id, no reply): initialized, cancelled, etc.
    if is_notification:
        return None

    if method == "initialize":
        return jsonrpc_result(msg_id, initialize_result())
    if method == "ping":
        return jsonrpc_result(msg_id, {})
    if method == "tools/list":
        return jsonrpc_result(msg_id, {"tools": TOOLS})
    if method == "tools/call":
        return _handle_tools_call(msg_id, message.get("params") or {}, tool_runner)

    return jsonrpc_error(msg_id, METHOD_NOT_FOUND, f"unknown method: {method}")


def _handle_tools_call(msg_id: Any, params: Any, tool_runner: ToolRunner | None) -> Dict[str, Any]:
    if tool_runner is None:
        return jsonrpc_error(msg_id, INTERNAL_ERROR, "no tool runner configured")
    if not isinstance(params, dict):
        return jsonrpc_error(msg_id, INVALID_PARAMS, "params must be an object")
    name = params.get("name")
    arguments = params.get("arguments") or {}
    if not isinstance(name, str) or not name:
        return jsonrpc_error(msg_id, INVALID_PARAMS, "tools/call requires a tool name")
    if not isinstance(arguments, dict):
        return jsonrpc_error(msg_id, INVALID_PARAMS, "arguments must be an object")
    try:
        text, structured, is_error = tool_runner(name, arguments)
    except UnknownTool:
        return jsonrpc_error(msg_id, INVALID_PARAMS, f"unknown tool: {name}")
    except Exception as exc:  # noqa: BLE001 — surface as a tool error, never crash the server
        return jsonrpc_result(msg_id, _tool_content(f"tool error: {exc}", None, True))
    return jsonrpc_result(msg_id, _tool_content(text, structured, is_error))


__all__ = [
    "PROTOCOL_VERSION",
    "SERVER_INFO",
    "TOOLS",
    "TOOL_NAMES",
    "UnknownTool",
    "dispatch",
    "initialize_result",
    "jsonrpc_result",
    "jsonrpc_error",
]
