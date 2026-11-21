"""Focused tests for the read-only health monitor's status mapping."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "aureon_health_monitor",
    ROOT / "scripts" / "monitor" / "aureon_health_monitor.py",
)
assert SPEC is not None and SPEC.loader is not None
monitor = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = monitor
SPEC.loader.exec_module(monitor)


def test_operator_ready() -> None:
    assert monitor._check_operator(200, {"ready": True}) == ("ok", "ready")


def test_operator_reports_failed_checks() -> None:
    state, detail = monitor._check_operator(
        503,
        {"ready": False, "checks": {"database": False, "bus": True}},
    )
    assert state == "degraded"
    assert "not ready: database" == detail


def test_operator_readyz_404_falls_back_to_healthz(monkeypatch) -> None:
    calls: list[str] = []

    def fake_http(url: str, timeout: float = 10.0):
        calls.append(url)
        if url.endswith("/readyz"):
            return 404, b"{}"
        return 200, b'{"ok": true}'

    monkeypatch.setattr(monitor, "_http", fake_http)
    state, detail = monitor._http_status(
        "organ/operator_gateway",
        "http://127.0.0.1:8790/readyz",
    )
    assert (state, detail) == ("degraded", "readyz not mounted; healthz ok")
    assert calls == [
        "http://127.0.0.1:8790/readyz",
        "http://127.0.0.1:8790/healthz",
    ]


def test_frontend_slow_but_bound_is_degraded(monkeypatch) -> None:
    monkeypatch.setattr(monitor, "_http", lambda url, timeout=10.0: (0, b"timeout"))
    monkeypatch.setattr(monitor, "_port_open", lambda host, port, timeout=1.5: True)
    state, detail = monitor._http_status(
        "organ/frontend_vite",
        "http://127.0.0.1:5173/@vite/client",
    )
    assert state == "degraded"
    assert "port 5173 listening" in detail


def test_frontend_not_bound_is_down(monkeypatch) -> None:
    monkeypatch.setattr(monitor, "_http", lambda url, timeout=10.0: (0, b"timeout"))
    monkeypatch.setattr(monitor, "_port_open", lambda host, port, timeout=1.5: False)
    assert monitor._http_status(
        "organ/frontend_vite",
        "http://127.0.0.1:5173/@vite/client",
    ) == ("down", "no answer")


def test_market_stale_is_degraded() -> None:
    state, detail = monitor._check_market(
        200,
        {"ok": True, "stale": True, "trading_ready": False},
    )
    assert state == "degraded"
    assert "expected without exchange keys" in detail


def test_mind_initializing_is_degraded() -> None:
    state, detail = monitor._check_mind(
        200,
        {"status": "initializing", "initialized": False},
    )
    assert state == "degraded"
    assert "initializing" in detail


def test_mind_ready_is_ok() -> None:
    assert monitor._check_mind(
        200,
        {"status": "ready", "initialized": True, "thoughts": [1, 2]},
    ) == ("ok", "ready, 2 recent thoughts")
