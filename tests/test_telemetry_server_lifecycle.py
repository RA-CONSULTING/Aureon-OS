"""Offline lifecycle checks for the Prometheus telemetry exporter."""

from __future__ import annotations

import importlib
from typing import List

import prometheus_client


class _FakeThread:
    def __init__(self) -> None:
        self.alive = True
        self.join_timeouts: List[float] = []

    def is_alive(self) -> bool:
        return self.alive

    def join(self, timeout: float = 0.0) -> None:
        self.join_timeouts.append(timeout)
        self.alive = False


class _FakeServer:
    def __init__(self) -> None:
        self.shutdown_calls = 0
        self.close_calls = 0

    def shutdown(self) -> None:
        self.shutdown_calls += 1

    def server_close(self) -> None:
        self.close_calls += 1


def _fresh_telemetry(monkeypatch):
    calls = []
    server = _FakeServer()
    thread = _FakeThread()

    def fake_start_http_server(port, addr="0.0.0.0"):
        calls.append((port, addr))
        return server, thread

    monkeypatch.setattr(
        prometheus_client,
        "start_http_server",
        fake_start_http_server,
    )
    from aureon.monitors import telemetry_server

    module = importlib.reload(telemetry_server)
    return module, calls, server, thread


def test_import_status_and_alpaca_construction_are_inert(monkeypatch):
    telemetry, calls, _server, _thread = _fresh_telemetry(monkeypatch)
    monkeypatch.setenv("PROMETHEUS_METRICS_PORT", "43191")
    monkeypatch.setenv("ALPACA_DRY_RUN", "true")
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.delenv("ALPACA_API_SECRET", raising=False)
    monkeypatch.delenv("ALPACA_SECRET", raising=False)

    assert telemetry.telemetry_server_status()["running"] is False
    assert calls == []

    from aureon.exchanges.alpaca_client import AlpacaClient

    client = AlpacaClient()
    try:
        assert calls == []
        assert telemetry.telemetry_server_status()["running"] is False
    finally:
        client.close()


def test_server_owners_share_one_exporter_and_last_owner_stops_it(monkeypatch):
    telemetry, calls, server, thread = _fresh_telemetry(monkeypatch)

    assert telemetry.start_telemetry_server(43192, owner="runtime-a") is True
    assert telemetry.start_telemetry_server(43192, owner="runtime-b") is True
    assert calls == [(43192, "0.0.0.0")]
    assert telemetry.telemetry_server_status() == {
        "running": True,
        "port": 43192,
        "address": "0.0.0.0",
        "owner_count": 2,
        "stoppable": True,
        "thread_alive": True,
        "last_error": None,
    }

    assert telemetry.stop_telemetry_server(owner="runtime-a") is True
    assert server.shutdown_calls == 0
    assert telemetry.telemetry_server_status()["owner_count"] == 1

    assert telemetry.stop_telemetry_server(
        timeout=0.25,
        owner="runtime-b",
    ) is True
    assert server.shutdown_calls == 1
    assert server.close_calls == 1
    assert thread.join_timeouts == [0.25]
    assert telemetry.telemetry_server_status()["running"] is False


def test_alpaca_explicit_start_and_close_own_telemetry(monkeypatch):
    telemetry, calls, server, thread = _fresh_telemetry(monkeypatch)
    monkeypatch.setenv("PROMETHEUS_METRICS_PORT", "43193")
    monkeypatch.setenv("ALPACA_DRY_RUN", "true")
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.delenv("ALPACA_API_SECRET", raising=False)
    monkeypatch.delenv("ALPACA_SECRET", raising=False)

    from aureon.exchanges.alpaca_client import AlpacaClient

    client = AlpacaClient()
    assert calls == []

    assert client.start() is True
    assert calls == [(43193, "0.0.0.0")]
    assert telemetry.telemetry_server_status()["running"] is True

    assert client.close(timeout=0.5) is True
    assert server.shutdown_calls == 1
    assert server.close_calls == 1
    assert thread.join_timeouts == [0.5]
    assert telemetry.telemetry_server_status()["running"] is False
