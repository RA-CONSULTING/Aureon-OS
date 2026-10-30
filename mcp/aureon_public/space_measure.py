"""Authenticated session against python -m aureon_public.space.

Run from measured/aureon_public_space_run.sh. Do not hand-edit the output.
Docker is not required. The script records which runtime answered.
The bearer token is generated in this process and is not written to the record.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from aureon_public import paths
from aureon_public.guard_loader import aureon_source
from aureon_public.server import enforce_public_pin

_BIND_HOST = "127.0.0.1"
_RUNTIME = "local entry point python -m aureon_public.space; Docker is not installed on this machine"


def _dump(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json", by_alias=True)


def _server_env(api_key: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for key in ("HOME", "LOGNAME", "PATH", "SHELL", "TERM", "USER", "LANG", "TMPDIR"):
        value = os.environ.get(key)
        if value:
            env[key] = value
    env["PYTHONUNBUFFERED"] = "1"
    env["AUREON_PUBLIC_API_KEY"] = api_key
    env["AUREON_PUBLIC_HOST"] = _BIND_HOST
    env.pop("AUREON_PUBLIC_OPEN", None)
    return env


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((_BIND_HOST, 0))
        return int(sock.getsockname()[1])


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection((_BIND_HOST, port), timeout=0.2):
            return True
    except OSError:
        return False


def _stop(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        proc.wait(timeout=5)


def _log_tail(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-4000:]
    except OSError:
        return ""


def _entry_check(env: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-m", "aureon_public.space", "--check"],
        cwd=str(Path.cwd()),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr[-4000:] or completed.stdout[-4000:])
    return json.loads(completed.stdout)


async def _exchange(session: ClientSession) -> dict[str, Any]:
    initialized = await session.initialize()
    tools = _dump(await session.list_tools())
    consonance = await session.call_tool("alignment_consonance_read", {"ratio": 1.0})
    queen = await session.call_tool(
        "body_call",
        {
            "module": "queen/temporal_ground.py",
            "symbol": "compute_zpe_ground",
            "arguments_json": "",
        },
    )
    return {
        "initialize": _dump(initialized),
        "tools_call": [
            {
                "arguments": {"ratio": 1.0},
                "name": "alignment_consonance_read",
                "result": _dump(consonance),
            },
            {
                "arguments": {
                    "arguments_json": "",
                    "module": "queen/temporal_ground.py",
                    "symbol": "compute_zpe_ground",
                },
                "name": "body_call",
                "result": _dump(queen),
            },
        ],
        "tools_list": [tools],
    }


async def _session(url: str, api_key: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(headers=headers, timeout=60.0) as client:
        async with streamable_http_client(url, http_client=client) as (read, write, _session_id):
            async with ClientSession(read, write) as session:
                return await _exchange(session)


def _environment() -> dict[str, Any]:
    os.environ["AUREON_PUBLIC_REQUIRE_PIN"] = "1"
    enforce_public_pin()
    import aureon

    direct = None
    try:
        dist = importlib.metadata.distribution("aureon")
        raw = dist.read_text("direct_url.json")
        direct = json.loads(raw) if raw else None
    except Exception as exc:  # noqa: BLE001 - the record should say the pin was not readable
        direct = {"error": type(exc).__name__}
    from aureon_public.measurement_stamp import measurement_stamp

    return {
        "api_key_stored": False,
        "auth": "bearer",
        "aureon_direct_url": direct,
        "aureon_file": aureon.__file__,
        "aureon_source": aureon_source(),
        "docker": "not installed",
        "entry": "python -m aureon_public.space",
        "mcp": importlib.metadata.version("mcp"),
        "observer_mode": "dry_run",
        "open": "unset",
        "python": sys.executable,
        "require_pin": "1",
        "runtime": _RUNTIME,
        **measurement_stamp(),
    }


async def _run(out_path: Path) -> None:
    os.environ["AUREON_PUBLIC_REQUIRE_PIN"] = "1"
    enforce_public_pin()
    api_key = secrets.token_hex(16)
    env = _server_env(api_key)
    entry_check = _entry_check(env)
    port = _free_port()
    env["PORT"] = str(port)
    log_fd, log_name = tempfile.mkstemp(prefix="aureon-public-space-")
    os.close(log_fd)
    log_path = Path(log_name)
    log = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "aureon_public.space"],
        cwd=str(Path.cwd()),
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        text=True,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(_log_tail(log_path) or f"space entry exited {proc.returncode}")
            if _port_open(port):
                break
            time.sleep(0.1)
        else:
            raise TimeoutError(_log_tail(log_path) or "space entry did not listen")
        url = f"http://{_BIND_HOST}:{port}/mcp"
        body = await _session(url, api_key)
        record = {
            "entry_check": entry_check,
            "environment": _environment(),
            "streamable_http": {"host": _BIND_HOST, "port": port, "url": url, **body},
        }
        if api_key in json.dumps(record):
            raise RuntimeError("the bearer token was written into the record")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    finally:
        log.close()
        _stop(proc)
        log_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aureon-public-space-measure")
    parser.add_argument(
        "--out",
        type=Path,
        default=paths.repo_root() / "measured" / "aureon_public_space.json",
    )
    args = parser.parse_args(argv)
    asyncio.run(_run(args.out))


if __name__ == "__main__":
    main()
