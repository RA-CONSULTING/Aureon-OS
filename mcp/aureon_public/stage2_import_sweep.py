"""Sweep plan-stage-2 modules in isolated processes with sockets blocked.

A module is refused when its import loads ``inhouse_ai``, ``ollama_config``,
or an HTTP client, or when the import opens a connection, starts a process,
or writes outside the sandbox. The public server reads the committed record
and refuses those modules before a worker starts.

    bash measured/aureon_public_stage2_sweep.sh
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ADAPTER_MARKERS = ("inhouse_ai", "ollama_config")
# urllib.parse is not a client. urllib.request and http.client are.
HTTP_ROOTS = frozenset(
    {"requests", "httpx", "urllib3", "aiohttp", "websocket", "websockets"}
)
HTTP_PREFIXES = (
    "http.client",
    "urllib.request",
    "urllib.response",
)
RECORD_NAME = "aureon_public_stage2_imports.json"


def is_http_client(name: str) -> bool:
    """True when ``name`` is an HTTP client module or a submodule of one."""

    root = name.split(".", 1)[0]
    if root in HTTP_ROOTS:
        return True
    return any(name == prefix or name.startswith(prefix + ".") for prefix in HTTP_PREFIXES)


def import_refusal(
    bad: list[str],
    socket_attempts: list[str],
    processes: list[str] | None = None,
    writes: list[str] | None = None,
) -> str | None:
    """Why an import is refused. None when the import is clean."""

    if socket_attempts or any(
        any(marker in name for marker in ADAPTER_MARKERS) or is_http_client(name) for name in bad
    ):
        return "module import loads an adapter or http client"
    if processes:
        return "module import starts a process"
    if writes:
        return "module import writes outside the sandbox"
    return None


def import_is_refused(
    bad: list[str],
    socket_attempts: list[str],
    processes: list[str] | None = None,
    writes: list[str] | None = None,
) -> bool:
    """The rule the measured record and body_call share."""

    return import_refusal(bad, socket_attempts, processes, writes) is not None


def _dotted(module: str) -> str:
    stem = module[:-3] if module.endswith(".py") else module
    return "aureon." + stem.replace("/", ".")


def child_main(module: str) -> None:
    """Import one module. Stdout is one JSON object."""

    from aureon_public.sweep_guard import declare_sandbox, install_sweep_guard, snapshot

    os.environ["AUREON_PUBLIC_SWEEP"] = "1"
    declare_sandbox()
    install_sweep_guard()
    error = None
    try:
        from aureon_public.call_worker import _load

        _load(_dotted(module), module)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"[:240]
    import sys as _sys

    bad = sorted(
        name
        for name in _sys.modules
        if any(marker in name for marker in ADAPTER_MARKERS) or is_http_client(name)
    )
    snap = snapshot()
    json.dump(
        {
            "bad": bad,
            "error": error,
            "process": snap["processes"],
            "socket": snap["sockets"],
            "writes": snap["writes"],
        },
        sys.stdout,
    )


def stage2_modules() -> list[tuple[str, str]]:
    """Public function and method modules in plan stage 2."""

    from aureon_public.body import _inventory
    from aureon_public.coverage_plan import safety_category, stage_for

    rows, _index = _inventory()
    categories: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        categories[str(row["package"])].add(safety_category(str(row.get("safety") or "")))
    found: dict[str, str] = {}
    for row in rows:
        package = str(row["package"])
        if stage_for(package, categories[package]) != 2:
            continue
        if row["server"] != "public" or row["kind"] not in {"function", "method"}:
            continue
        found.setdefault(str(row["module"]), package)
    return sorted(found.items())


def _one(module: str, timeout: float) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-m", "aureon_public.stage2_import_sweep", "--module", module],
        cwd=os.environ.get("TMPDIR") or "/tmp",
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0 and not completed.stdout.strip():
        return {
            "bad": [],
            "error": f"sweep exited {completed.returncode}",
            "socket": [],
            "stderr": completed.stderr[-400:],
        }
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "bad": [],
            "error": "sweep result was not JSON",
            "socket": [],
            "stderr": (completed.stderr or completed.stdout)[-400:],
        }
    if not isinstance(payload, dict):
        return {"bad": [], "error": "sweep result was not an object", "socket": []}
    return payload


def build_record(timeout: float) -> dict[str, Any]:
    from aureon_public.guard_loader import aureon_source
    from aureon_public.measurement_stamp import measurement_stamp
    from aureon_public.sweep_layout import layout_record

    source = aureon_source()
    stamp = measurement_stamp()
    modules = []
    for module, package in stage2_modules():
        print(module, file=sys.stderr)
        payload = _one(module, timeout)
        bad = [str(item) for item in payload.get("bad") or []]
        sockets = [str(item) for item in payload.get("socket") or []]
        processes = [str(item) for item in payload.get("process") or []]
        writes = [str(item) for item in payload.get("writes") or []]
        refusal = import_refusal(bad, sockets, processes, writes)
        modules.append(
            {
                "bad": bad,
                "error": payload.get("error"),
                "module": module,
                "package": package,
                "process": processes,
                "refusal": refusal,
                "refused": refusal is not None,
                "socket": bool(sockets),
                "writes": writes,
            }
        )
    return {
        "adapters": list(ADAPTER_MARKERS),
        "aureon_source": source,
        "http_clients": sorted(HTTP_ROOTS | set(HTTP_PREFIXES)),
        "layout": layout_record(),
        "modules": modules,
        "processes": "blocked",
        "sockets": "blocked",
        "writes": "outside sandbox blocked",
        **stamp,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aureon-public-stage2-import-sweep")
    parser.add_argument("--module", help="import one module and print JSON")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--timeout", type=float, default=45.0)
    args = parser.parse_args(argv)
    if args.module:
        child_main(args.module)
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
