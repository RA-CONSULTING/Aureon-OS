"""Sweep plan-stage-2 modules in isolated processes with sockets blocked.

A module is refused when its import loads ``inhouse_ai``, ``ollama_config``,
or an HTTP client, or when the import opens a connection. The public server
reads the committed record and refuses those modules before a worker starts.

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


def import_is_refused(bad: list[str], socket_attempts: list[str]) -> bool:
    """The rule the measured record and body_call share."""

    if socket_attempts:
        return True
    for name in bad:
        if any(marker in name for marker in ADAPTER_MARKERS):
            return True
        if is_http_client(name):
            return True
    return False


def _dotted(module: str) -> str:
    stem = module[:-3] if module.endswith(".py") else module
    return "aureon." + stem.replace("/", ".")


def _block_sockets() -> list[str]:
    import socket

    attempts: list[str] = []

    class _Guard(socket.socket):
        def connect(self, address: Any, *args: Any, **kwargs: Any) -> None:
            attempts.append(str(address)[:160])
            raise OSError("socket blocked")

        def connect_ex(self, address: Any, *args: Any, **kwargs: Any) -> int:
            attempts.append(str(address)[:160])
            raise OSError("socket blocked")

    def _create_connection(*_args: Any, **_kwargs: Any) -> Any:
        attempts.append("create_connection")
        raise OSError("socket blocked")

    socket.socket = _Guard  # type: ignore[misc]
    socket.create_connection = _create_connection  # type: ignore[assignment]
    return attempts


def child_main(module: str) -> None:
    """Import one module. Stdout is one JSON object."""

    attempts = _block_sockets()
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
    json.dump(
        {"bad": bad, "error": error, "socket": attempts},
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
    from aureon_public.guard_loader import PINNED_COMMIT, aureon_source
    from aureon_public.paths import repo_root
    from aureon_public.sweep_layout import layout_record

    source = aureon_source()
    modules = []
    for module, package in stage2_modules():
        print(module, file=sys.stderr)
        payload = _one(module, timeout)
        bad = [str(item) for item in payload.get("bad") or []]
        sockets = [str(item) for item in payload.get("socket") or []]
        modules.append(
            {
                "bad": bad,
                "error": payload.get("error"),
                "module": module,
                "package": package,
                "refused": import_is_refused(bad, sockets),
                "socket": bool(sockets),
            }
        )
    created_path = repo_root() / "measured" / ".sweep_siblings.json"
    created: list[str] = []
    if created_path.is_file():
        loaded = json.loads(created_path.read_text(encoding="utf-8"))
        if isinstance(loaded, list):
            created = [str(item) for item in loaded]
    return {
        "adapters": list(ADAPTER_MARKERS),
        "aureon_source": source,
        "http_clients": sorted(HTTP_ROOTS | set(HTTP_PREFIXES)),
        "layout": layout_record(created),
        "modules": modules,
        "pin": source.get("commit") or PINNED_COMMIT,
        "sockets": "blocked",
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
