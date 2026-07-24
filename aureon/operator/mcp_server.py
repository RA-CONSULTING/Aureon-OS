"""
Aureon MCP stdio server — ``aureon-mcp``.

The local transport of the Aureon MCP surface (the hosted one is ``POST /mcp`` on
the operator). Desktop / IDE agents (Claude Desktop, Cursor, …) spawn this as a
subprocess and speak newline-delimited JSON-RPC 2.0 over stdin/stdout. It reuses the
pure protocol layer in ``aureon.operator.mcp`` and the same veto-guarded engines as
every other surface — grounded text + a verdict only, nothing executes.

Register in a client, e.g. Claude Desktop ``claude_desktop_config.json``:

    { "mcpServers": { "aureon": { "command": "aureon-mcp" } } }

Runs offline with no keys (set ``AUREON_LLM_OFFLINE=1``); add provider keys to go live.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict, Tuple

logger = logging.getLogger("aureon.operator.mcp_server")


def _build_tool_runner():
    """Lazily construct the engines once, then answer tool calls through them."""
    state: Dict[str, Any] = {"cognition": None, "operator": None}

    def _cognition():
        if state["cognition"] is None:
            from aureon.operator.cognition import AureonCognition

            state["cognition"] = AureonCognition(join_mesh=False)
        return state["cognition"]

    def _operator():
        if state["operator"] is None:
            from aureon.operator.aureon_operator import AureonOperator

            state["operator"] = AureonOperator()
        return state["operator"]

    def _runner(name: str, arguments: Dict[str, Any]) -> Tuple[str, Any, bool]:
        from aureon.operator import mcp as _mcp

        if name == "aureon_integration":
            from aureon.operator.mount import integration_manifest

            m = integration_manifest()
            return (json.dumps(m, indent=2), m, False)
        prompt = str(arguments.get("prompt", "")).strip()
        if not prompt:
            return ("prompt is required", None, True)
        session_id = arguments.get("session_id")
        if name == "aureon_switchboard":
            res = _operator().respond(prompt, session_id=session_id).to_dict()
        elif name == "aureon_reason":
            res = _cognition().reason(prompt, session_id=session_id).to_dict()
        else:
            raise _mcp.UnknownTool(name)
        return (str(res.get("text", "")), res, False)

    return _runner


def main() -> int:
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    try:  # honour a local .env (offline flag, provider keys) like the HTTP server
        from aureon.core.aureon_env import bootstrap_credentials

        bootstrap_credentials()
    except Exception:  # noqa: BLE001 — best-effort
        pass

    from aureon.operator import mcp as _mcp

    tool_runner = _build_tool_runner()
    out = sys.stdout

    for line in sys.stdin:  # newline-delimited JSON-RPC messages
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            out.write(json.dumps(_mcp.jsonrpc_error(None, _mcp.PARSE_ERROR, "invalid JSON")) + "\n")
            out.flush()
            continue
        response = _mcp.dispatch(message, tool_runner)
        if response is not None:  # notifications get no reply
            out.write(json.dumps(response, default=str) + "\n")
            out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
