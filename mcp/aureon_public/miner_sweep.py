"""Call miner entry points that pass the read gate.

The Charlie trading gate is HOLD. Live orders stay off. Mining stays off.
A function or method the read gate refuses is not called, so the bridge is
not constructed and no exchange client is imported. The one opened read is
called with sockets, process starts, and writes outside the sandbox blocked.
The stages 1 and 2 file ``measured/aureon_public_call_sweep.json`` is not written.

    bash measured/aureon_public_miner_sweep.sh
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from aureon_public.call_sweep import hazard_reason
from aureon_public.miner_surface import (
    TESTED,
    charlie_trading_gate,
    fence_modules,
    opened_entry,
    order_keys,
    public_table_snapshot,
    read_gate_refusal,
    runtime_refusal,
    summarize,
)


def _not_called() -> dict[str, Any]:
    return {
        "bad": [],
        "called": False,
        "error": None,
        "order_keys": [],
        "process": [],
        "result_keys": [],
        "socket": [],
        "status": "unavailable",
        "writes": [],
    }


def child_main(module: str, symbol: str) -> None:
    from aureon_public.miner_surface import charlie_trading_gate, entry_rows, read_gate_refusal

    gate = charlie_trading_gate()
    if gate["posture"] != "HOLD" or gate["mining"] != "off" or gate["live_orders"] != "off":
        json.dump(_not_called(), sys.stdout)
        return
    rows = {(str(row["module"]), str(row["symbol"])): row for row in entry_rows()}
    row = rows.get((module, symbol))
    if row is None or read_gate_refusal(row) is not None:
        json.dump(_not_called(), sys.stdout)
        return
    os.environ["AUREON_PUBLIC_SWEEP"] = "1"
    os.environ["AUREON_PUBLIC_MINER_SURFACE"] = "1"
    os.environ["AUREON_AUDIT_MODE"] = "1"
    os.environ["AUREON_DISABLE_REAL_ORDERS"] = "1"
    os.environ["AUREON_DISABLE_LIVE_BACKGROUND_STARTUP"] = "1"
    os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
    os.environ["AUREON_ENABLE_AUTONOMOUS_CONTROL"] = "0"
    os.environ["AUREON_ACTIVATE_ON_IMPORT"] = "0"
    os.environ["AUREON_OBSERVER_MODE"] = "dry_run"

    from aureon_public.body import dotted_for
    from aureon_public.call_worker import _call, _install_sweep_guard, _plain, _sweep_modules
    from aureon_public.sweep_guard import declare_sandbox, snapshot

    declare_sandbox()
    _install_sweep_guard()
    real_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        result = _call(dotted_for(module), symbol, {}, module)
        payload: dict[str, Any] = {
            "called": True,
            "error": None,
            "result": _plain(result),
            "status": "cited",
        }
    except SystemExit:
        payload = {"called": False, "error": "SystemExit", "result": None, "status": "unavailable"}
    except Exception as exc:
        payload = {
            "called": False,
            "error": f"{type(exc).__name__}: {exc}"[:240],
            "result": None,
            "status": "unavailable",
        }
    snap = snapshot()
    bad = list(_sweep_modules())
    bad.extend(fence_modules(list(sys.modules)))
    found_orders = order_keys(payload.get("result"))
    sys.stdout = real_stdout
    json.dump(
        {
            "bad": sorted(set(bad)),
            "called": payload["called"] is True,
            "error": payload.get("error"),
            "order_keys": found_orders,
            "process": list(snap["processes"]),
            "result_keys": sorted(payload["result"]) if isinstance(payload.get("result"), dict) else [],
            "socket": list(snap["sockets"]),
            "status": payload.get("status"),
            "writes": list(snap["writes"]),
        },
        sys.stdout,
    )


def _child_env() -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "TMPDIR": os.environ.get("TMPDIR", "") or "/tmp",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    return env


def _one(module: str, symbol: str, timeout: float) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "aureon_public.miner_sweep",
        "--module",
        module,
        "--symbol",
        symbol,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=os.environ.get("TMPDIR") or "/tmp",
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=_child_env(),
        )
    except subprocess.TimeoutExpired:
        return {
            "bad": [],
            "called": False,
            "error": "sweep exceeded the timeout",
            "order_keys": [],
            "process": [],
            "result_keys": [],
            "socket": [],
            "status": "unavailable",
            "writes": [],
        }
    if not completed.stdout.strip():
        detail = (completed.stderr or "").strip().splitlines()
        tail = detail[-1][:240] if detail else f"sweep exited {completed.returncode}"
        return {
            "bad": [],
            "called": False,
            "error": tail,
            "order_keys": [],
            "process": [],
            "result_keys": [],
            "socket": [],
            "status": "unavailable",
            "writes": [],
        }
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "bad": [],
            "called": False,
            "error": "sweep result was not JSON",
            "order_keys": [],
            "process": [],
            "result_keys": [],
            "socket": [],
            "status": "unavailable",
            "writes": [],
        }
    return payload if isinstance(payload, dict) else {}


def _measured(payload: dict[str, Any]) -> str | None:
    reason = hazard_reason(
        {
            "bad": payload.get("bad") or [],
            "process": payload.get("process") or [],
            "socket": payload.get("socket") or [],
            "writes": payload.get("writes") or [],
        }
    )
    if reason:
        return reason
    if payload.get("order_keys"):
        return "live orders are refused"
    error = str(payload.get("error") or "")
    if "Refused imports" in error or "live order" in error.lower():
        return "call loads a banned chain or opens a connection"
    if payload.get("called") is not True:
        return "call did not finish"
    return None


def build_record(timeout: float) -> dict[str, Any]:
    from aureon_public.guard_loader import aureon_source
    from aureon_public.measurement_stamp import measurement_stamp
    from aureon_public.miner_surface import entry_rows
    from aureon_public.sweep_layout import layout_record

    source = aureon_source()
    stamp = measurement_stamp()
    table = public_table_snapshot()
    entries: list[dict[str, Any]] = []
    for row in entry_rows():
        module = str(row["module"])
        symbol = str(row["symbol"])
        print(f"{module} {symbol}", file=sys.stderr)
        gate = read_gate_refusal(row)
        if gate is not None:
            payload = _not_called()
            measured = None
        else:
            payload = _one(module, symbol, timeout)
            measured = _measured(payload)
        called = payload.get("called") is True and measured is None
        refusal = runtime_refusal(gate, measured)
        opened = opened_entry(gate, measured, called)
        entries.append(
            {
                "bad": [str(item) for item in payload.get("bad") or []],
                "called": payload.get("called") is True,
                "error": payload.get("error"),
                "measured_refusal": measured,
                "module": module,
                "opened": opened,
                "order_keys": [str(item) for item in payload.get("order_keys") or []],
                "package": "miner",
                "process": [str(item) for item in payload.get("process") or []],
                "read_gate": gate,
                "refusal": refusal,
                "refused": not opened,
                "result_keys": [str(item) for item in payload.get("result_keys") or []],
                "socket": [str(item) for item in payload.get("socket") or []],
                "status": payload.get("status"),
                "symbol": symbol,
                "tested": opened and (module, symbol) in set(TESTED),
                "writes": [str(item) for item in payload.get("writes") or []],
            }
        )
    return {
        "aureon_source": source,
        "badge": "HOLD",
        "charlie_gate": charlie_trading_gate(),
        "delta": summarize(entries, table),
        "entries": entries,
        "global_call_sweep_rewritten": False,
        "go_live_clear": False,
        "layout": layout_record(),
        "orders": "refused",
        "package": "miner",
        "pin_moved": False,
        "processes": "blocked",
        "public_depth_republished": False,
        "public_table": table,
        "schema": "aureon.public.miner-surface.v1",
        "scope": "miner",
        "sockets": "blocked",
        "writes": "outside sandbox blocked",
        **stamp,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aureon-public-miner-sweep")
    parser.add_argument("--module")
    parser.add_argument("--symbol")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args(argv)
    if args.module or args.symbol:
        if not args.module or not args.symbol:
            raise SystemExit("module and symbol are both required")
        child_main(args.module, args.symbol)
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
