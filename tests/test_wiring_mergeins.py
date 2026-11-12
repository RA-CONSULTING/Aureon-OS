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
