"""Call sweep for the stage 3 and 4 read gate.

Does not rewrite measured/aureon_public_call_sweep.json. Sockets, process
starts, and writes outside the sandbox are blocked in the worker. A banned
import outside the three read modules refuses the entry point.

    env -u PYTHONPATH PYTHONPATH=mcp python3 -m aureon_public.stage34_measure --write
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from aureon_public.call_sweep import _one, hazard_reason
from aureon_public.guard_loader import aureon_source
from aureon_public.measurement_stamp import measurement_stamp
from aureon_public.stage34_gate import READ_ARGUMENTS, READ_KEYS, contains_env_secret, key_group_labels
from aureon_public.sweep_layout import layout_record


def _attempts(module: str, symbol: str) -> list[dict[str, Any]]:
    return [
        {
            "arguments": {},
            "label": "no_arguments",
            "note": "No arguments.",
        },
        {
            "arguments": READ_ARGUMENTS[(module, symbol)],
            "label": "read_gate",
            "note": "The read-gate arguments. No order and no key value.",
        },
    ]


def build_record(timeout: float = 45.0) -> dict[str, Any]:
    source = aureon_source()
    stamp = measurement_stamp()
    entries = []
    for module, symbol in sorted(READ_KEYS):
        recorded = []
        hazards: list[str] = []
        for attempt in _attempts(module, symbol):
            arguments = attempt["arguments"]
            arguments_json = json.dumps(arguments) if arguments else ""
            payload = _one(module, symbol, timeout, arguments_json)
            reason = hazard_reason(payload)
            if reason:
                hazards.append(reason)
            recorded.append(
                {
                    "arguments": arguments,
                    "bad": [str(item) for item in payload.get("bad") or []],
                    "called": payload.get("called") is True,
                    "error": payload.get("error"),
                    "label": attempt["label"],
                    "note": attempt["note"],
                    "process": [str(item) for item in payload.get("process") or []],
                    "reason": payload.get("reason"),
                    "refusal": reason,
                    "sandbox_writes": [str(item) for item in payload.get("sandbox_writes") or []],
                    "socket": [str(item) for item in payload.get("socket") or []],
                    "status": payload.get("status"),
                    "writes": [str(item) for item in payload.get("writes") or []],
                }
            )
        refusal = hazards[0] if hazards else None
        real = recorded[-1]
        entries.append(
            {
                "attempts": recorded,
                "bad": real["bad"],
                "called": real["called"],
                "error": real["error"],
                "module": module,
                "plan_stage": 3 if module.startswith("miner/") else 4,
                "process": real["process"],
                "reason": real["reason"],
                "refusal": refusal,
                "refused": refusal is not None,
                "sandbox_writes": sorted({item for attempt in recorded for item in attempt["sandbox_writes"]}),
                "socket": real["socket"],
                "status": real["status"],
                "symbol": symbol,
                "writes": real["writes"],
            }
        )
    labels = key_group_labels()
    record = {
        "aureon_source": source,
        "entries": entries,
        "key_groups": labels,
        "key_material": "not read",
        "layout": layout_record(),
        "live_orders": "refused",
        "processes": "blocked",
        "schema": "aureon.public.stage34-call-sweep.v1",
        "sockets": "blocked",
        "writes": "outside sandbox blocked",
        **stamp,
    }
    leaked = contains_env_secret(json.dumps(record))
    if leaked:
        raise SystemExit(f"stage34 sweep would record an env value for {leaked}")
    return record


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aureon-public-stage34-measure")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--timeout", type=float, default=45.0)
    args = parser.parse_args(argv)
    record = build_record(args.timeout)
    text = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if not args.write:
        print(text)
        return
    path = Path("measured") / "aureon_public_stage34_call_sweep.json"
    path.write_text(text, encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
