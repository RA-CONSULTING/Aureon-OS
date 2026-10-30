"""Stdio and Streamable HTTP sessions against aureon-public.

Run from measured/aureon_public_protocol_run.sh. Do not hand-edit the output.

The process requires AUREON_PUBLIC_REQUIRE_PIN=1 and an aureon install whose
direct_url.json names the pin. The HTTP listener is 127.0.0.1. One tools/call
is alignment_consonance_read with ratio 1.0.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from aureon_public import paths
from aureon_public.guard_loader import aureon_source
from aureon_public.server import enforce_public_pin

TOOL_NAME = "alignment_consonance_read"
TOOL_ARGUMENTS = {"ratio": 1.0}
_BIND_HOST = "127.0.0.1"


def _dump(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json", by_alias=True)


def _server_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for key in ("HOME", "LOGNAME", "PATH", "SHELL", "TERM", "USER", "LANG", "TMPDIR"):
        value = os.environ.get(key)
        if value:
            env[key] = value
    env["PYTHONUNBUFFERED"] = "1"
    env["AUREON_PUBLIC_REQUIRE_PIN"] = "1"
    return env


async def _list_pages(method: Any) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    cursor: str | None = None
    seen: set[str] = set()
    while True:
        result = await method() if cursor is None else await method(cursor=cursor)
        page = _dump(result)
        pages.append(page)
        nxt = page.get("nextCursor")
        if not isinstance(nxt, str) or not nxt or nxt in seen:
            return pages
        seen.add(nxt)
        cursor = nxt


async def _exchange(session: ClientSession) -> dict[str, Any]:
    initialized = await session.initialize()
    tools_list = await _list_pages(session.list_tools)
    resources_list = await _list_pages(session.list_resources)
    prompts_list = await _list_pages(session.list_prompts)
    called = await session.call_tool(TOOL_NAME, TOOL_ARGUMENTS)
    return {
        "initialize": _dump(initialized),
        "prompts_list": prompts_list,
        "resources_list": resources_list,
        "tools_call": {
            "arguments": TOOL_ARGUMENTS,
            "name": TOOL_NAME,
            "result": _dump(called),
        },
        "tools_list": tools_list,
    }


async def _stdio_session() -> dict[str, Any]:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "aureon_public"],
        env=_server_env(),
        cwd=str(Path.cwd()),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            return await _exchange(session)


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


def _stop_process_group(proc: subprocess.Popen[str]) -> None:
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


def _wait_until_listening(proc: subprocess.Popen[str], log_path: Path, port: int) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(_log_tail(log_path) or f"server exited {proc.returncode}")
        if _port_open(port):
            return
        time.sleep(0.1)
    raise TimeoutError(_log_tail(log_path) or f"{_BIND_HOST}:{port} did not accept a connection")


def _log_tail(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-4000:]


async def _http_session(port: int) -> dict[str, Any]:
    url = f"http://{_BIND_HOST}:{port}/mcp"
    log_fd, log_name = tempfile.mkstemp(prefix="aureon-public-http-")
    os.close(log_fd)
    log_path = Path(log_name)
    log = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "aureon_public",
            "--transport",
            "streamable-http",
            "--host",
            _BIND_HOST,
            "--port",
            str(port),
        ],
        cwd=str(Path.cwd()),
        env=_server_env(),
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        text=True,
    )
    try:
        _wait_until_listening(proc, log_path, port)
        last: BaseException | None = None
        for _attempt in range(8):
            if proc.poll() is not None:
                break
            try:
                body = await _exchange_http(url)
                return {
                    "host": _BIND_HOST,
                    "port": port,
                    "url": url,
                    **body,
                }
            except Exception as exc:  # noqa: BLE001 - the listener can accept TCP before MCP answers
                last = exc
                await asyncio.sleep(0.25)
        tail = _log_tail(log_path)
        raise RuntimeError(f"streamable http session failed: {last}\n{tail}")
    finally:
        log.close()
        _stop_process_group(proc)
        log_path.unlink(missing_ok=True)


async def _exchange_http(url: str) -> dict[str, Any]:
    async with streamable_http_client(url) as (read, write, _get_session_id):
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
        "aureon_direct_url": direct,
        "aureon_file": aureon.__file__,
        "aureon_source": aureon_source(),
        "mcp": importlib.metadata.version("mcp"),
        "python": sys.executable,
        "require_pin": "1",
        **measurement_stamp(),
    }


async def _run(out_path: Path) -> dict[str, Any]:
    os.environ["AUREON_PUBLIC_REQUIRE_PIN"] = "1"
    enforce_public_pin()
    stdio = await _stdio_session()
    http = await _http_session(_free_port())
    record = {
        "environment": _environment(),
        "stdio": stdio,
        "streamable_http": http,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aureon-public-protocol-measure")
    parser.add_argument(
        "--out",
        type=Path,
        default=paths.repo_root() / "measured" / "aureon_public_protocol.json",
    )
    args = parser.parse_args(argv)
    asyncio.run(_run(args.out))


if __name__ == "__main__":
    main()
