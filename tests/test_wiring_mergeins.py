"""Wiring checks for names other modules import but main was missing.

Restored by hand from RA-CONSULTING/Aureon-Trading--Project-Sero @ 806de995
(aureon-os-upstream/aureon/ollama_config.py and core/global_rate_budget.py),
plus the two timeline-oracle calls that did not match ChirpBus.emit_message.
Import-only and AST checks: no network, no keys, no orders.
"""

import ast
import inspect
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

OLLAMA_NAMES = [
    "OllamaDailyBudgetExceeded",
    "check_ollama_daily_budget",
    "ensure_ollama_shared_budget",
    "get_ollama_usage",
    "record_ollama_call",
    "resolve_ollama_daily_cap",
    "tracked_ollama_call",
]


@pytest.mark.parametrize("name", OLLAMA_NAMES)
def test_ollama_config_exports_budget_names(name):
    import aureon.ollama_config as oc

    assert hasattr(oc, name), name


@pytest.mark.parametrize("name", ["get_host_rate_budget", "wait_for_slot_deferred"])
def test_global_rate_budget_exports_host_helpers(name):
    import aureon.core.global_rate_budget as grb

    assert callable(getattr(grb, name, None)), name


def test_host_budget_disabled_switch_returns_none(monkeypatch):
    import aureon.core.global_rate_budget as grb

    monkeypatch.setenv("AUREON_RATE_BUDGET_ENABLED", "0")
    assert grb.get_host_rate_budget("api-capital.backend-capital.com") is None


def test_timeline_oracle_emit_message_calls_bind_to_chirp_bus():
    from aureon.core.aureon_chirp_bus import ChirpBus

    sig = inspect.signature(ChirpBus.emit_message)
    src = (ROOT / "aureon/intelligence/aureon_timeline_oracle.py").read_text(encoding="utf-8")
    calls = [
        n for n in ast.walk(ast.parse(src))
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "emit_message"
    ]
    assert calls, "oracle no longer calls emit_message"
    for call in calls:
        args = [object()] + [object() for _ in call.args]  # self + positionals
        kwargs = {kw.arg: object() for kw in call.keywords if kw.arg}
        sig.bind(*args, **kwargs)  # raises TypeError on a mismatched call


def test_ollama_shared_budget_works_without_filelock(tmp_path, monkeypatch):
    """ollama_config must import and lock without the filelock package."""
    import builtins
    import importlib
    import sys

    real_import = builtins.__import__

    def _no_filelock(name, *args, **kwargs):
        if name == "filelock" or name.startswith("filelock."):
            raise ImportError("filelock blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_filelock)
    monkeypatch.delitem(sys.modules, "filelock", raising=False)
    monkeypatch.delitem(sys.modules, "aureon.ollama_config", raising=False)
    mod = importlib.import_module("aureon.ollama_config")
    lock_path = tmp_path / "budget.json.lock"
    with mod.FileLock(str(lock_path)):
        pass
    assert mod.FileLock.__module__ == "aureon.ollama_config"
    monkeypatch.setattr(builtins, "__import__", real_import)
    monkeypatch.delitem(sys.modules, "aureon.ollama_config", raising=False)


class _BrokenLimiter:
    def wait_for_slot(self, priority, is_trading):
        raise RuntimeError("limiter internals broken (test)")

    def on_429_error(self, priority):
        pass


class _ThrottledLimiter:
    def wait_for_slot(self, priority, is_trading):
        return False

    def on_429_error(self, priority):
        pass


def test_wait_for_slot_deferred_fails_closed_for_trading_on_limiter_error():
    from aureon.core.global_rate_budget import RequestPriority, wait_for_slot_deferred

    broken = _BrokenLimiter()
    assert wait_for_slot_deferred(broken, RequestPriority.EXECUTION, is_trading=True) is False
    assert wait_for_slot_deferred(broken, RequestPriority.QUOTES, is_trading=False) is True


def _bare_capital_client(limiter):
    """CapitalClient with no credentials, no session and no network: only the
    rate-budget fields are set, so _budget_acquire can be exercised alone."""
    import importlib.util
    from pathlib import Path

    from aureon.core.global_rate_budget import RequestPriority, wait_for_slot_deferred

    path = Path(__file__).resolve().parents[1] / "aureon_radar" / "capital_client.py"
    if not path.exists():
        pytest.skip("aureon_radar/capital_client.py not present")
    spec = importlib.util.spec_from_file_location("_test_capital_client", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    client = mod.CapitalClient.__new__(mod.CapitalClient)
    client._rate_budget = limiter
    client._RequestPriority = RequestPriority
    client._budget_wait = wait_for_slot_deferred
    return client


@pytest.mark.parametrize("limiter", [_ThrottledLimiter(), _BrokenLimiter()], ids=["throttled", "limiter_error"])
def test_capital_close_refused_cleanly_when_budget_denies(limiter):
    client = _bare_capital_client(limiter)
    with pytest.raises(RuntimeError, match=r"NOT sent \(fail-closed\)"):
        client._budget_acquire("DELETE", "/positions/TEST-DEAL", write=True, max_wait_s=0.1)
