"""Space entry: optional bearer, local bind, limits, and closed stages."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.timeout(180)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


def _base_env(**extra: str) -> dict[str, str]:
    env = dict(os.environ)
    for name in (
        "AUREON_PUBLIC_SWEEP",
        "AUREON_PUBLIC_OPEN",
        "AUREON_PUBLIC_API_KEY",
        "PYTHONPATH",
    ):
        env.pop(name, None)
    env.update(extra)
    return env


def _wait(proc: subprocess.Popen[str], port: int, log_path: Path) -> None:
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
            raise AssertionError(tail or f"space entry exited {proc.returncode}")
        if _port_open(port):
            return
        time.sleep(0.1)
    raise AssertionError(log_path.read_text(encoding="utf-8", errors="replace")[-4000:])


def _stop(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


class _Server:
    def __init__(self, env: dict[str, str]) -> None:
        self.env = env
        self.port = _free_port()
        self.env["PORT"] = str(self.port)
        self.env["AUREON_PUBLIC_HOST"] = "127.0.0.1"
        self.proc: subprocess.Popen[str] | None = None
        self.log_path: Path | None = None

    def __enter__(self) -> "_Server":
        work = Path(tempfile.mkdtemp(prefix="aureon-space-"))
        log_fd, log_name = tempfile.mkstemp(prefix="aureon-space-log-")
        os.close(log_fd)
        self.log_path = Path(log_name)
        log = self.log_path.open("w", encoding="utf-8")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "aureon_public.space"],
            cwd=str(work),
            env=self.env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        log.close()
        _wait(self.proc, self.port, self.log_path)
        return self

    def __exit__(self, *args: object) -> None:
        if self.proc is not None:
            _stop(self.proc)
        if self.log_path is not None:
            self.log_path.unlink(missing_ok=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/mcp"


def test_public_bind_accepts_hf_space_host_and_locked_bind_refuses_all_interfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 0.0.0.0 bind accepts Host: *.hf.space. No key and no OPEN refuses 0.0.0.0."""

    import asyncio

    from mcp.server.fastmcp import FastMCP
    from mcp.server.transport_security import TransportSecurityMiddleware
    from starlette.requests import Request

    from aureon_public.space import space_host

    monkeypatch.delenv("AUREON_PUBLIC_API_KEY", raising=False)
    monkeypatch.delenv("AUREON_PUBLIC_OPEN", raising=False)
    monkeypatch.setenv("AUREON_PUBLIC_HOST", "0.0.0.0")
    with pytest.raises(SystemExit, match="127.0.0.1"):
        space_host()

    async def host_status(bind: str) -> int | None:
        server = FastMCP("aureon-public-host-check", host=bind, port=9)
        security = TransportSecurityMiddleware(server.settings.transport_security)
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp",
            "headers": [
                (b"host", b"aureon-public.hf.space"),
                (b"content-type", b"application/json"),
            ],
            "query_string": b"",
            "scheme": "https",
            "client": ("127.0.0.1", 1),
            "server": ("0.0.0.0", 7860),
        }

        async def receive():
            return {"type": "http.request", "body": b"{}", "more_body": False}

        response = await security.validate_request(Request(scope, receive), is_post=True)
        if response is None:
            return None
        return int(response.status_code)

    assert asyncio.run(host_status("0.0.0.0")) is None
    assert asyncio.run(host_status("127.0.0.1")) == 421
    monkeypatch.setenv("AUREON_PUBLIC_OPEN", "1")
    assert space_host() == "0.0.0.0"
    monkeypatch.delenv("AUREON_PUBLIC_OPEN")
    monkeypatch.setenv("AUREON_PUBLIC_API_KEY", "runtime-secret")
    assert space_host() == "0.0.0.0"


def test_locked_bind_is_localhost_only(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon_public.http_guard import resolve_http_bind

    monkeypatch.delenv("AUREON_PUBLIC_API_KEY", raising=False)
    monkeypatch.delenv("AUREON_PUBLIC_OPEN", raising=False)
    assert resolve_http_bind("127.0.0.1") == "127.0.0.1"
    with pytest.raises(SystemExit, match="127.0.0.1"):
        resolve_http_bind("0.0.0.0")
    monkeypatch.setenv("AUREON_PUBLIC_OPEN", "1")
    assert resolve_http_bind("0.0.0.0") == "0.0.0.0"
    monkeypatch.delenv("AUREON_PUBLIC_OPEN")
    monkeypatch.setenv("AUREON_PUBLIC_API_KEY", "runtime-secret")
    assert resolve_http_bind("0.0.0.0") == "0.0.0.0"


def test_space_check_refuses_stage_three_and_four() -> None:
    work = Path(tempfile.mkdtemp(prefix="aureon-space-check-"))
    completed = subprocess.run(
        [sys.executable, "-m", "aureon_public.space", "--check"],
        cwd=str(work),
        env=_base_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["ok"] is True
    assert report["observer_mode"] == "dry_run"
    assert report["require_pin"] == "1"
    assert report["sweep_set"] is False
    assert report["queen_call"]["reason"] == "plan stage 4 is not open"
    assert report["queen_call"].get("called") is not True
    for name in ("miner", "accounting", "queen", "exchanges", "trading"):
        assert report["closed_packages_reachable"][name] == 0


def test_space_refuses_to_start_when_sweep_is_set() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "aureon_public.space", "--check"],
        cwd=str(ROOT),
        env=_base_env(AUREON_PUBLIC_SWEEP="1"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "AUREON_PUBLIC_SWEEP" in completed.stderr


def test_space_refuses_a_live_observer_mode() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "aureon_public.space", "--check"],
        cwd=str(ROOT),
        env=_base_env(AUREON_OBSERVER_MODE="live"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "dry_run" in completed.stderr


def test_bearer_rejects_missing_and_wrong_keys_and_accepts_the_right_one() -> None:
    key = "correct-space-key"
    with _Server(_base_env(AUREON_PUBLIC_API_KEY=key, AUREON_PUBLIC_RATE_LIMIT="100")) as server:
        missing = httpx.post(server.url, content=b"{}", timeout=10)
        wrong = httpx.post(
            server.url,
            content=b"{}",
            headers={"Authorization": "Bearer wrong-space-key"},
            timeout=10,
        )
        assert missing.status_code == 401
        assert wrong.status_code == 401
        assert missing.json()["error"] == "unauthorized"
        assert wrong.json()["error"] == "unauthorized"

        import asyncio

        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async def listed() -> list[str]:
            headers = {"Authorization": f"Bearer {key}"}
            async with httpx.AsyncClient(headers=headers, timeout=60.0) as client:
                async with streamable_http_client(server.url, http_client=client) as (read, write, _sid):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        return [item.name for item in result.tools]

        names = asyncio.run(listed())
        assert "alignment_consonance_read" in names
        assert "body_call" in names


def test_open_surface_serves_tools_list_without_a_key() -> None:
    import asyncio

    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    with _Server(_base_env(AUREON_PUBLIC_OPEN="1", AUREON_PUBLIC_RATE_LIMIT="100")) as server:
        probe = httpx.post(server.url, content=b"{}", timeout=10)
        assert probe.status_code != 401

        async def listed() -> list[str]:
            async with streamable_http_client(server.url) as (read, write, _sid):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return [item.name for item in result.tools]

        names = asyncio.run(listed())
        assert "alignment_consonance_read" in names


def test_rate_limit_and_body_limit_return_429() -> None:
    key = "limit-space-key"
    with _Server(
        _base_env(
            AUREON_PUBLIC_API_KEY=key,
            AUREON_PUBLIC_RATE_LIMIT="1",
            AUREON_PUBLIC_RATE_WINDOW_S="60",
        )
    ) as server:
        headers = {"Authorization": f"Bearer {key}"}
        first = httpx.post(server.url, content=b"{}", headers=headers, timeout=10)
        second = httpx.post(server.url, content=b"{}", headers=headers, timeout=10)
        assert first.status_code != 429
        assert second.status_code == 429
        assert second.json()["error"] == "rate_limit"
    with _Server(
        _base_env(
            AUREON_PUBLIC_API_KEY=key,
            AUREON_PUBLIC_MAX_BODY_BYTES="16",
            AUREON_PUBLIC_RATE_LIMIT="20",
        )
    ) as server:
        headers = {"Authorization": f"Bearer {key}"}
        oversized = httpx.post(server.url, content=b"x" * 64, headers=headers, timeout=10)
        assert oversized.status_code == 413
        assert oversized.json()["error"] == "body_too_large"


def test_request_timeout_returns_504() -> None:
    import asyncio

    from aureon_public.http_guard import HttpLimits, PublicHttpMiddleware

    async def slow(scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
            return
        await asyncio.sleep(1)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"late"})

    limits = HttpLimits(
        api_key="",
        max_body_bytes=1000,
        rate_limit=10,
        rate_window_s=60,
        timeout_s=0.05,
    )
    app = PublicHttpMiddleware(slow, limits)

    async def post() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://space") as client:
            return await client.post("/mcp", content=b"{}")

    response = asyncio.run(post())
    assert response.status_code == 504
    assert response.json()["error"] == "timeout"


def _limits(**overrides: object):
    from aureon_public.http_guard import HttpLimits

    values = {
        "api_key": "",
        "max_body_bytes": 1000,
        "rate_limit": 2,
        "rate_window_s": 60.0,
        "timeout_s": 5.0,
        "trusted_proxy_hops": 1,
        "max_clients": 32,
        "max_inflight": 8,
    }
    values.update(overrides)
    return HttpLimits(**values)


async def _middleware_status(middleware, headers: dict[str, str], body: bytes = b"{}") -> int:
    raw = [(key.lower().encode("latin1"), value.encode("latin1")) for key, value in headers.items()]
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/mcp",
        "headers": raw,
        "client": ("127.0.0.1", 9),
    }
    sent = {"done": False}

    async def receive():
        if sent["done"]:
            return {"type": "http.disconnect"}
        sent["done"] = True
        return {"type": "http.request", "body": body, "more_body": False}

    messages = []

    async def send(message):
        messages.append(message)

    await middleware(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    return int(start["status"])


def test_changing_x_forwarded_for_first_hop_shares_one_bucket() -> None:
    """Replay: limit 2, four requests, only the first X-Forwarded-For hop changes."""

    import asyncio

    from aureon_public.http_guard import PublicHttpMiddleware

    async def ok(scope, receive, send):
        while True:
            message = await receive()
            if message.get("type") == "http.request" and not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = PublicHttpMiddleware(ok, _limits())

    async def statuses() -> list[int]:
        found = []
        for index in range(4):
            found.append(
                await _middleware_status(
                    middleware,
                    {"x-forwarded-for": f"203.0.113.{index}, 198.51.100.10"},
                )
            )
        return found

    codes = asyncio.run(statuses())
    assert codes[:2] != [429, 429]
    assert codes[2] == 429
    assert codes[3] == 429


def test_open_mode_random_bearers_share_one_bucket() -> None:
    """Replay: open mode, limit 2, Bearer x1 through x4."""

    import asyncio

    from aureon_public.http_guard import PublicHttpMiddleware

    async def ok(scope, receive, send):
        while True:
            message = await receive()
            if message.get("type") == "http.request" and not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = PublicHttpMiddleware(ok, _limits(api_key=""))

    async def statuses() -> list[int]:
        found = []
        for index in range(1, 5):
            found.append(await _middleware_status(middleware, {"authorization": f"Bearer x{index}"}))
        return found

    codes = asyncio.run(statuses())
    assert codes[2] == 429
    assert codes[3] == 429


def test_chunked_post_without_content_length_over_the_cap_is_413() -> None:
    import asyncio

    from aureon_public.http_guard import PublicHttpMiddleware

    called = {"app": False}

    async def ok(scope, receive, send):
        called["app"] = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = PublicHttpMiddleware(ok, _limits(max_body_bytes=8, rate_limit=10))
    chunks = [
        {"type": "http.request", "body": b"12345", "more_body": True},
        {"type": "http.request", "body": b"67890abc", "more_body": False},
    ]

    async def post() -> int:
        index = {"n": 0}

        async def receive():
            if index["n"] >= len(chunks):
                return {"type": "http.disconnect"}
            message = chunks[index["n"]]
            index["n"] += 1
            return message

        messages = []

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp",
            "headers": [],
            "client": ("127.0.0.1", 9),
        }
        await middleware(scope, receive, send)
        start = next(message for message in messages if message["type"] == "http.response.start")
        return int(start["status"])

    assert asyncio.run(post()) == 413
    assert called["app"] is False


def test_spike_junk_bearers_are_refused() -> None:
    """Open mode, limit 3, five junk bearers share the socket peer."""

    import asyncio

    from aureon_public.http_guard import PublicHttpMiddleware

    async def ok(scope, receive, send):
        while True:
            message = await receive()
            if message.get("type") == "http.request" and not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = PublicHttpMiddleware(ok, _limits(rate_limit=3))

    async def statuses() -> list[int]:
        found = []
        for index in range(5):
            found.append(await _middleware_status(middleware, {"authorization": f"Bearer junk-{index}"}))
        return found

    codes = asyncio.run(statuses())
    assert codes[3] == 429
    assert codes[4] == 429


def test_single_hop_forwarded_address_is_its_own_client() -> None:
    """One X-Forwarded-For value is the client when one trusted proxy is configured."""

    import asyncio

    from aureon_public.http_guard import PublicHttpMiddleware

    async def ok(scope, receive, send):
        while True:
            message = await receive()
            if message.get("type") == "http.request" and not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = PublicHttpMiddleware(ok, _limits(rate_limit=2, trusted_proxy_hops=1))

    async def statuses() -> list[int]:
        found = []
        for _repeat in range(3):
            found.append(await _middleware_status(middleware, {"x-forwarded-for": "203.0.113.10"}))
        found.append(await _middleware_status(middleware, {"x-forwarded-for": "203.0.113.11"}))
        return found

    codes = asyncio.run(statuses())
    assert codes[0] == 200
    assert codes[1] == 200
    assert codes[2] == 429
    assert codes[3] == 200


def test_spoofed_first_hop_does_not_get_its_own_bucket() -> None:
    """A fake first hop in front of one real last hop stays one client."""

    import asyncio

    from aureon_public.http_guard import PublicHttpMiddleware

    async def ok(scope, receive, send):
        while True:
            message = await receive()
            if message.get("type") == "http.request" and not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = PublicHttpMiddleware(ok, _limits(rate_limit=2, trusted_proxy_hops=1))

    async def statuses() -> list[int]:
        found = []
        for index in range(4):
            found.append(
                await _middleware_status(
                    middleware,
                    {"x-forwarded-for": f"198.51.100.{index}, 203.0.113.50"},
                )
            )
        return found

    codes = asyncio.run(statuses())
    assert codes[0] == 200
    assert codes[1] == 200
    assert codes[2] == 429
    assert codes[3] == 429


def test_forwarded_diagnostic_records_shape_without_addresses(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon_public.http_guard import clear_forwarded_shapes, client_address, forwarded_shapes

    clear_forwarded_shapes()
    monkeypatch.delenv("AUREON_PUBLIC_FORWARDED_DIAG", raising=False)
    scope = {"client": ("10.0.0.1", 9)}
    client_address(scope, {"x-forwarded-for": "203.0.113.10"}, 1)
    assert forwarded_shapes() == []
    monkeypatch.setenv("AUREON_PUBLIC_FORWARDED_DIAG", "1")
    clear_forwarded_shapes()
    client_address(
        scope,
        {"x-forwarded-for": "203.0.113.10, 2001:db8::1"},
        1,
    )
    recorded = forwarded_shapes()
    assert recorded == [{"hops": 2, "kinds": ["ipv4", "ipv6"]}]
    text = json.dumps(recorded)
    assert "203.0.113.10" not in text
    assert "2001:db8::1" not in text
    clear_forwarded_shapes()


async def _middleware_get(middleware, headers: dict[str, str]) -> int:
    import asyncio

    raw = [(key.lower().encode("latin1"), value.encode("latin1")) for key, value in headers.items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/mcp",
        "headers": raw,
        "client": ("127.0.0.1", 9),
    }

    async def receive():
        await asyncio.Event().wait()
        return {"type": "http.disconnect"}

    messages = []

    async def send(message):
        messages.append(message)

    await middleware(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    return int(start["status"])


def test_open_gets_do_not_consume_call_slots() -> None:
    """Buzz: four open GETs from four addresses, then another client's POST."""

    import asyncio

    from aureon_public.http_guard import PublicHttpMiddleware

    async def ok(scope, receive, send):
        while True:
            message = await receive()
            if message.get("type") == "http.request" and not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = PublicHttpMiddleware(ok, _limits(max_inflight=4, rate_limit=20))

    async def run() -> None:
        gets = []
        for index in range(4):
            gets.append(await _middleware_get(middleware, {"x-forwarded-for": f"203.0.113.{index}"}))
        assert gets == [405, 405, 405, 405]
        assert middleware._inflight == 0
        posted = await _middleware_status(middleware, {"x-forwarded-for": "198.51.100.8"})
        assert posted == 200

    asyncio.run(run())


def test_spike_chunked_50000_against_2000_is_refused() -> None:
    """Spike: a 50,000-byte chunked POST against a 2,000-byte limit."""

    import asyncio

    from aureon_public.http_guard import PublicHttpMiddleware

    called = {"app": False}

    async def ok(scope, receive, send):
        called["app"] = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = PublicHttpMiddleware(ok, _limits(max_body_bytes=2000, rate_limit=10))
    payload = b"x" * 50000
    chunks = [
        {"type": "http.request", "body": payload[:25000], "more_body": True},
        {"type": "http.request", "body": payload[25000:], "more_body": False},
    ]

    async def post() -> int:
        index = {"n": 0}

        async def receive():
            if index["n"] >= len(chunks):
                return {"type": "http.disconnect"}
            message = chunks[index["n"]]
            index["n"] += 1
            return message

        messages = []

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp",
            "headers": [],
            "client": ("127.0.0.1", 9),
        }
        await middleware(scope, receive, send)
        start = next(message for message in messages if message["type"] == "http.response.start")
        return int(start["status"])

    assert asyncio.run(post()) == 413
    assert called["app"] is False


def _post_asgi_chunks(middleware, chunks: list[dict]) -> tuple[int, bytes]:
    import asyncio

    async def post() -> tuple[int, bytes]:
        index = {"n": 0}

        async def receive():
            if index["n"] >= len(chunks):
                return {"type": "http.disconnect"}
            message = chunks[index["n"]]
            index["n"] += 1
            return message

        messages = []

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp",
            "headers": [],
            "client": ("127.0.0.1", 9),
        }
        await middleware(scope, receive, send)
        start = next(message for message in messages if message["type"] == "http.response.start")
        body = b"".join(
            message.get("body") or b""
            for message in messages
            if message.get("type") == "http.response.body"
        )
        return int(start["status"]), body

    return asyncio.run(post())


def test_twenty_empty_chunks_then_oversize_body_is_413() -> None:
    """Spike: empty more_body frames must not stop the byte count."""

    from aureon_public.http_guard import PublicHttpMiddleware

    called = {"app": False}

    async def ok(scope, receive, send):
        called["app"] = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = PublicHttpMiddleware(ok, _limits(max_body_bytes=8, rate_limit=10))
    chunks = [{"type": "http.request", "body": b"", "more_body": True} for _ in range(20)]
    chunks.append({"type": "http.request", "body": b"x" * 32, "more_body": False})
    status, body = _post_asgi_chunks(middleware, chunks)
    assert status == 413
    assert json.loads(body)["error"] == "body_too_large"
    assert called["app"] is False


def test_twenty_empty_chunks_then_a_small_body_still_reaches_the_app() -> None:
    from aureon_public.http_guard import PublicHttpMiddleware

    seen = {"body": b""}

    async def ok(scope, receive, send):
        body = b""
        while True:
            message = await receive()
            if message.get("type") != "http.request":
                break
            body += message.get("body") or b""
            if not message.get("more_body", False):
                break
        seen["body"] = body
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = PublicHttpMiddleware(ok, _limits(max_body_bytes=8, rate_limit=10))
    chunks = [{"type": "http.request", "body": b"", "more_body": True} for _ in range(20)]
    chunks.append({"type": "http.request", "body": b"ok", "more_body": False})
    status, body = _post_asgi_chunks(middleware, chunks)
    assert status == 200
    assert body == b"ok"
    assert seen["body"] == b"ok"


def test_unfinished_empty_body_returns_408() -> None:
    """An idle drip is rejected. It is not passed through to the application."""

    import asyncio

    from aureon_public.http_guard import PublicHttpMiddleware

    called = {"app": False}

    async def ok(scope, receive, send):
        called["app"] = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = PublicHttpMiddleware(ok, _limits(max_body_bytes=8, rate_limit=10, timeout_s=0.05))

    async def post() -> tuple[int, bytes]:
        async def receive():
            await asyncio.Event().wait()
            return {"type": "http.request", "body": b"x" * 32, "more_body": False}

        messages = []

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp",
            "headers": [],
            "client": ("127.0.0.1", 9),
        }
        await middleware(scope, receive, send)
        start = next(message for message in messages if message["type"] == "http.response.start")
        body = b"".join(
            message.get("body") or b""
            for message in messages
            if message.get("type") == "http.response.body"
        )
        return int(start["status"]), body

    status, body = asyncio.run(post())
    assert status == 408
    assert json.loads(body)["error"] == "body_timeout"
    assert called["app"] is False


def test_inflight_cap_returns_503_busy() -> None:
    import asyncio

    from aureon_public.http_guard import PublicHttpMiddleware

    release = asyncio.Event()
    entered = asyncio.Event()

    async def hold(scope, receive, send):
        while True:
            message = await receive()
            if message.get("type") == "http.request" and not message.get("more_body", False):
                break
        entered.set()
        await release.wait()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = PublicHttpMiddleware(hold, _limits(max_inflight=1, rate_limit=10))

    async def run() -> None:
        first = asyncio.create_task(_middleware_status(middleware, {}))
        await asyncio.wait_for(entered.wait(), timeout=2)
        second = await _middleware_status(middleware, {})
        assert second == 503
        release.set()
        assert await first == 200

    asyncio.run(run())


def test_rate_limiter_table_stays_bounded() -> None:
    from aureon_public.http_guard import RateLimiter

    clock = {"now": 0.0}
    limiter = RateLimiter(2, 30.0, max_clients=4, now=lambda: clock["now"])
    for index in range(200):
        assert limiter.allow(f"client-{index}") is True
    assert len(limiter._hits) <= 4
    clock["now"] = 31.0
    assert limiter.allow("after-window") is True
    assert set(limiter._hits) == {"after-window"}


def test_space_record_is_an_authenticated_local_session() -> None:
    from aureon_public.guard_loader import PINNED_COMMIT
    from aureon_public.measurement_stamp import CODE_COMMIT_NOTE, PIN_AUREON_TREE

    record = json.loads((ROOT / "measured" / "aureon_public_space.json").read_text(encoding="utf-8"))
    environment = record["environment"]
    assert environment["auth"] == "bearer"
    assert environment["api_key_stored"] is False
    assert environment["docker"] == "not installed"
    assert environment["entry"] == "python -m aureon_public.space"
    assert environment["observer_mode"] == "dry_run"
    assert environment["open"] == "unset"
    assert environment["require_pin"] == "1"
    assert environment["mcp"] == "1.30.0"
    assert environment["aureon_source"] == {"commit": PINNED_COMMIT, "kind": "pinned"}
    assert environment["aureon_tree"] == PIN_AUREON_TREE
    assert environment["pin_aureon_tree"] == PIN_AUREON_TREE
    assert environment["code_commit_note"] == CODE_COMMIT_NOTE
    assert len(environment["code_commit"]) == 40
    http = record["streamable_http"]
    assert http["host"] == "127.0.0.1"
    assert http["url"] == f"http://127.0.0.1:{http['port']}/mcp"
    assert http["initialize"]["serverInfo"]["name"] == "aureon-public"
    names = [item["name"] for item in http["tools_list"][0]["tools"]]
    assert "alignment_consonance_read" in names
    assert "body_call" in names
    by_name = {item["name"]: item for item in http["tools_call"]}
    consonance = json.loads(by_name["alignment_consonance_read"]["result"]["content"][0]["text"])
    assert consonance["called"] is True
    assert consonance["result"] == 1.0
    queen = json.loads(by_name["body_call"]["result"]["content"][0]["text"])
    assert queen.get("called") is not True
    assert queen["reason"] == "plan stage 4 is not open"
    assert record["entry_check"]["ok"] is True
    assert record["entry_check"]["closed_packages_reachable"]["miner"] == 0
    assert record["entry_check"]["closed_packages_reachable"]["queen"] == 0
    assert record["entry_check"]["closed_packages_reachable"]["exchanges"] == 0


_UVICORN_APP = """
import os
import sys

import uvicorn

from aureon_public.http_guard import PublicHttpMiddleware, load_http_limits
from aureon_public.server import streamable_http_config


def _install_empty_body_frames() -> None:
    # A chunk size of 0 ends an HTTP body, so a socket client cannot send
    # twenty non-terminating empty chunks and then more bytes. The frames are
    # inserted on the HTTP cycle receive that _bounded_receive reads. The
    # switch is this test process only.
    count = int(os.environ.get("AUREON_TEST_EMPTY_BODY_FRAMES", "0") or "0")
    if count <= 0:
        return
    from uvicorn.protocols.http.h11_impl import RequestResponseCycle as H11Cycle

    cycles = [H11Cycle]
    try:
        from uvicorn.protocols.http.httptools_impl import RequestResponseCycle as ToolsCycle
    except ImportError:
        ToolsCycle = None
    if ToolsCycle is not None:
        cycles.append(ToolsCycle)

    def wrap(cycle) -> None:
        original = cycle.receive

        async def receive(self, _original=original, _count=count):
            left = getattr(self, "_aureon_empty_left", _count)
            if left > 0:
                self._aureon_empty_left = left - 1
                return {"type": "http.request", "body": b"", "more_body": True}
            return await _original(self)

        cycle.receive = receive

    for cycle in cycles:
        wrap(cycle)


_install_empty_body_frames()


async def ok(scope, receive, send):
    if scope.get("type") != "http":
        return
    if scope.get("method") == "POST":
        while True:
            message = await receive()
            if message.get("type") == "http.request" and not message.get("more_body", False):
                break
    body = b"ok"
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"text/plain"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


app = PublicHttpMiddleware(ok, load_http_limits())
uvicorn.Server(streamable_http_config(app, "127.0.0.1", int(sys.argv[1]))).run()
"""


def test_uvicorn_rotating_single_hop_and_open_gets() -> None:
    """Charlie: real uvicorn, rotating single-hop addresses, and four open GETs.

    proxy_headers stays off. With no trusted proxy hops, five different
    single-hop values share the socket and do not all return 200. Four GETs
    from four addresses return 405 and leave a later POST able to succeed.
    """

    from aureon_public.server import streamable_http_config

    config = streamable_http_config(object(), "127.0.0.1", 9)
    assert config.proxy_headers is False
    assert config.forwarded_allow_ips == ""

    script = Path(tempfile.mkdtemp(prefix="aureon-uvicorn-")) / "app.py"
    script.write_text(_UVICORN_APP, encoding="utf-8")

    def serve(port: int, **env_updates: str) -> subprocess.Popen[str]:
        env = _base_env(**env_updates)
        proc = subprocess.Popen(
            [sys.executable, str(script), str(port)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if _port_open(port):
                return proc
            if proc.poll() is not None:
                output = proc.stdout.read() if proc.stdout is not None else ""
                raise AssertionError(output or f"uvicorn exited {proc.returncode}")
            time.sleep(0.05)
        proc.terminate()
        raise AssertionError("uvicorn did not listen")

    def stop(proc: subprocess.Popen[str]) -> None:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)

    port = _free_port()
    proc = serve(
        port,
        AUREON_PUBLIC_RATE_LIMIT="2",
        AUREON_PUBLIC_TRUSTED_PROXY_HOPS="0",
        AUREON_PUBLIC_MAX_INFLIGHT="8",
    )
    try:
        codes = []
        for index in range(5):
            response = httpx.post(
                f"http://127.0.0.1:{port}/mcp",
                headers={"x-forwarded-for": f"203.0.113.{index}"},
                content=b"{}",
                timeout=5,
            )
            codes.append(response.status_code)
        assert codes[:2] == [200, 200]
        assert codes[2:] == [429, 429, 429]
    finally:
        stop(proc)

    port = _free_port()
    proc = serve(
        port,
        AUREON_PUBLIC_RATE_LIMIT="20",
        AUREON_PUBLIC_TRUSTED_PROXY_HOPS="1",
        AUREON_PUBLIC_MAX_INFLIGHT="4",
    )
    try:
        gets = []
        for index in range(4):
            response = httpx.get(
                f"http://127.0.0.1:{port}/mcp",
                headers={"x-forwarded-for": f"198.51.100.{index}"},
                timeout=5,
            )
            gets.append(response.status_code)
        posted = httpx.post(
            f"http://127.0.0.1:{port}/mcp",
            headers={"x-forwarded-for": "192.0.2.20"},
            content=b"{}",
            timeout=5,
        )
        assert gets == [405, 405, 405, 405]
        assert posted.status_code == 200
    finally:
        stop(proc)


def test_uvicorn_twenty_empty_chunks_then_oversize_is_413() -> None:
    """Spike, through real uvicorn: twenty empty frames, then a body over the cap.

    The HTTP body is chunked and has no content-length, so the declared-length
    check cannot answer 413 on its own. The empty frames come from the HTTP
    cycle receive inside this server process.
    """

    script = Path(tempfile.mkdtemp(prefix="aureon-uvicorn-")) / "app.py"
    script.write_text(_UVICORN_APP, encoding="utf-8")
    port = _free_port()
    env = _base_env(
        AUREON_PUBLIC_RATE_LIMIT="20",
        AUREON_PUBLIC_MAX_BODY_BYTES="16",
        AUREON_PUBLIC_REQUEST_TIMEOUT_S="5",
        AUREON_TEST_EMPTY_BODY_FRAMES="20",
    )
    proc = subprocess.Popen(
        [sys.executable, str(script), str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if _port_open(port):
                break
            if proc.poll() is not None:
                output = proc.stdout.read() if proc.stdout is not None else ""
                raise AssertionError(output or f"uvicorn exited {proc.returncode}")
            time.sleep(0.05)
        else:
            raise AssertionError("uvicorn did not listen")
        payload = b"x" * 64
        raw = (
            b"POST /mcp HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"Connection: close\r\n"
            b"\r\n"
            + f"{len(payload):x}\r\n".encode("ascii")
            + payload
            + b"\r\n0\r\n\r\n"
        )
        with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
            sock.sendall(raw)
            sock.settimeout(5)
            data = b""
            while b"\r\n\r\n" not in data or (
                b"content-length: " in data.lower()
                and len(data.split(b"\r\n\r\n", 1)[1])
                < int(data.lower().split(b"content-length: ", 1)[1].split(b"\r\n", 1)[0])
            ):
                piece = sock.recv(4096)
                if not piece:
                    break
                data += piece
        status = int(data.split(b" ", 2)[1])
        body = data.split(b"\r\n\r\n", 1)[1]
        assert status == 413
        assert json.loads(body)["error"] == "body_too_large"
        assert body != b"ok"
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


def test_scaffold_bakes_no_key_and_quotes_the_plan() -> None:
    dockerfile = (ROOT / "mcp" / "aureon_public" / "Dockerfile").read_text(encoding="utf-8")
    requirements = (ROOT / "mcp" / "aureon_public" / "requirements.txt").read_text(encoding="utf-8")
    readme = (ROOT / "mcp" / "aureon_public" / "README.md").read_text(encoding="utf-8")
    assert "AUREON_PUBLIC_API_KEY=" not in dockerfile
    assert "ENV AUREON_PUBLIC_SWEEP" not in dockerfile
    assert "AUREON_PUBLIC_REQUIRE_PIN=1" in dockerfile
    assert "AUREON_OBSERVER_MODE=dry_run" in dockerfile
    assert "AUREON_PUBLIC_OPEN=1" in dockerfile
    assert "AUREON_PUBLIC_HOST=0.0.0.0" in dockerfile
    assert "421" in readme
    assert "*.hf.space" in readme
    assert "503" in readme
    assert "`busy`" in readme
    assert "mcp==1.30.0,<2" in requirements
    assert "8aa6a2d971cc529484e2a5e261e28afafab4e4f4" in requirements
    assert "partial release covering stages 1 and 2 of 4" in readme
    assert "reachable now 69" in readme
    assert "tested 69" in readme
    assert "refused 4319" in readme
    assert "Other arguments have not been swept." in readme
    assert "alive" not in readme.lower()
    assert "The measured session was taken without Docker." in readme
    assert "The first Hugging Face build log must show the `AUREON_REF` build arg." in readme
    assert "HTTP 408" in readme
    assert "`body_timeout`" in readme
    assert 'echo "AUREON_REF=${AUREON_REF}"' in dockerfile
    assert "#225" in readme
    assert "ARG AUREON_REF=cf43882e" not in dockerfile
    assert "0390194b80cddb66c8cfd052efe3aa4f9d1545d6" in dockerfile
