"""Measure the public Queen read gate. Sockets, processes, and outside writes are blocked.

Each attempt runs in its own process. The child does not place an order and
does not import an exchange package. ``queen_source_law_gate`` is the stage-8
read. ``queen_zpe_ground`` is the existing Queen helper, measured again here.
This sweep opens no queen `body_call` entry beyond the `compute_zpe_ground` read already open in `stage34_gate`.

    env -u PYTHONPATH PYTHONPATH=mcp python3.12 -m aureon_public.queen_read_sweep --out measured/aureon_public_queen_stage8.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ATTEMPTS: tuple[dict[str, Any], ...] = (
    {"arguments": {}, "label": "default", "tool": "queen_source_law_gate"},
    {"arguments": {"coherence_gamma": 0.99}, "label": "above_floor", "tool": "queen_source_law_gate"},
    {"arguments": {"coherence_gamma": 0.938}, "label": "at_floor", "tool": "queen_source_law_gate"},
    {"arguments": {"coherence_gamma": 0.9379}, "label": "below_floor", "tool": "queen_source_law_gate"},
    {
        "arguments": {"coherence_gamma": 0.99, "lowest_node_confidence": 0.2},
        "label": "node_floor",
        "tool": "queen_source_law_gate",
    },
    {"arguments": {"lambda_t": 0.0}, "label": "zpe_read", "tool": "queen_zpe_ground"},
)

_BANNED = (
    "aureon.exchanges",
    "aureon.miner",
    "aureon.trading",
    "aureon.bots",
    "aureon.bots_intelligence",
    "aureon.bridges",
    "aureon.scanners",
    "unified_margin_trader",
)
# aureon_source() asks git for HEAD. The sweep guard blocks that Popen.
# The read still returns. This line is not an order process.
_SOURCE_STAMP = "Popen ['git', 'rev-parse', 'HEAD']"
_KEEP = (
    "coherence_gamma",
    "economic_mutation",
    "entry_floor",
    "exchange_calls",
    "live_orders",
    "lowest_node_confidence",
    "math_action",
    "node_floor",
    "order_permission",
    "orders_placed",
    "pinned_entry_floor",
    "public_action",
    "read_gated",
    "reason",
    "release_boundary",
    "status",
    "trade_readiness",
)


def _banned(name: str) -> bool:
    return name in _BANNED or name.startswith(tuple(prefix + "." for prefix in _BANNED))


def child_main(tool: str, arguments_json: str) -> None:
    """One guarded call. stdout is a single JSON object."""

    os.environ["AUREON_PUBLIC_SWEEP"] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    from aureon_public.sweep_guard import declare_sandbox, install_sweep_guard, snapshot

    declare_sandbox()
    install_sweep_guard()
    real_stdout = sys.stdout
    sys.stdout = sys.stderr
    arguments = json.loads(arguments_json) if arguments_json else {}
    if not isinstance(arguments, dict):
        arguments = {}
    try:
        from aureon_public import more_layers

        text = getattr(more_layers, tool)(**arguments)
        body = json.loads(text)
    except Exception as exc:
        body = {"reason": f"{type(exc).__name__}: {exc}"[:240], "status": "unavailable"}
    snap = snapshot()
    banned = sorted(name for name in sys.modules if _banned(name))
    sys.stdout = real_stdout
    json.dump(
        {
            "banned_modules": banned,
            "processes": list(snap["processes"]),
            "result": {key: body.get(key) for key in _KEEP if key in body},
            "sandbox_writes": list(snap["sandbox_writes"]),
            "sockets": list(snap["sockets"]),
            "writes": list(snap["writes"]),
        },
        real_stdout,
    )


def _child_env() -> dict[str, str]:
    package = str(Path(__file__).resolve().parents[1])
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": package,
        "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", "0"),
    }
    for key in ("LANG", "LC_ALL", "LC_CTYPE"):
        value = os.environ.get(key)
        if value:
            env[key] = value
    return env


def _one(tool: str, arguments: dict[str, Any], timeout: float) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "aureon_public.queen_read_sweep",
        "--tool",
        tool,
        "--arguments",
        json.dumps(arguments, sort_keys=True),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=_child_env(),
        )
    except subprocess.TimeoutExpired:
        return {"error": "sweep exceeded the timeout", "status": "unavailable"}
    if not completed.stdout.strip():
        return {
            "error": f"sweep exited {completed.returncode}",
            "status": "unavailable",
            "stderr": completed.stderr[-400:],
        }
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"error": "sweep result was not JSON", "status": "unavailable"}
    return payload if isinstance(payload, dict) else {"error": "sweep result was not an object"}


def _other_processes(payload: dict[str, Any]) -> list[str]:
    return [str(item) for item in payload.get("processes") or [] if str(item) != _SOURCE_STAMP]


def _refusal(payload: dict[str, Any], result: dict[str, Any]) -> str | None:
    if payload.get("error"):
        return "call did not finish"
    if payload.get("sockets") or payload.get("banned_modules"):
        return "call loads a banned package or opens a connection"
    if _other_processes(payload):
        return "call starts a process"
    if payload.get("writes"):
        return "call writes outside the sandbox"
    if result.get("live_orders") not in {None, "off"}:
        return "live orders were not off"
    if result.get("orders_placed") not in {None, False}:
        return "an order was placed"
    if result.get("exchange_calls") not in {None, "not_performed"}:
        return "an exchange was called"
    if result.get("public_action") not in {None, "HOLD"}:
        return "public action was not HOLD"
    return None


def build_record(timeout: float) -> dict[str, Any]:
    from aureon_public.measurement_stamp import measurement_stamp

    attempts = []
    for attempt in ATTEMPTS:
        arguments = dict(attempt["arguments"])
        payload = _one(str(attempt["tool"]), arguments, timeout)
        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        refusal = _refusal(payload, result)
        attempts.append(
            {
                "arguments": arguments,
                "banned_modules": [str(item) for item in payload.get("banned_modules") or []],
                "error": payload.get("error"),
                "label": attempt["label"],
                "processes": [str(item) for item in payload.get("processes") or []],
                "refusal": refusal,
                "source_stamp_blocked": _SOURCE_STAMP in [str(item) for item in payload.get("processes") or []],
                "refused": refusal is not None,
                "result": result,
                "sandbox_writes": [str(item) for item in payload.get("sandbox_writes") or []],
                "sockets": [str(item) for item in payload.get("sockets") or []],
                "tool": attempt["tool"],
                "writes": [str(item) for item in payload.get("writes") or []],
            }
        )
    return {
        "attempts": attempts,
        "exchange_calls": "not_performed",
        "live_orders": "off",
        "orders_placed": False,
        "processes": "blocked",
        "public_action": "HOLD",
        "read_gated": True,
        "scope": "queen public read gate only; miner and exchanges are not opened",
        "sockets": "blocked",
        "writes": "outside sandbox blocked",
        **measurement_stamp(),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aureon-public-queen-read-sweep")
    parser.add_argument("--tool")
    parser.add_argument("--arguments", default="")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--timeout", type=float, default=45.0)
    args = parser.parse_args(argv)
    if args.tool:
        child_main(args.tool, args.arguments)
        return
    record = build_record(args.timeout)
    text = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.out is None:
        sys.stdout.write(text)
        return
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
