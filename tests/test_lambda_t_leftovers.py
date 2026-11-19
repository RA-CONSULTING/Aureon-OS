"""Leftover Lambda(t) readers must not report a gap as 0.0.

A real 0.0 stays 0.0. ``if not`` is the wrong test: zero is falsy.
Gamma from the cortex is not Lambda(t).
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from aureon.core.cognitive_dashboard import source_lambda_text
from aureon.core.lambda_reading import lambda_reading
from aureon.gates.panel import FieldVault
from aureon.observer.benchmark import engine_lambda_trace
from aureon.observer.historical_backtest import snapshot_lambda_cell, snapshot_lambda_trace
from aureon.queen.hnc_human_loop import _NullVault, read_engine_lambda
from aureon.trading.aureon_unified_ecosystem import AureonKrakenEcosystem
from aureon.vault.aureon_vault import AureonVault
from aureon.vault.casimir_quantifier import CasimirQuantifier

ROOT = Path(__file__).resolve().parents[1]

_FORBIDDEN = {
    "aureon/vault/casimir_quantifier.py": (
        "getattr(vault, 'last_lambda_t', 0.0)",
        'getattr(vault, "last_lambda_t", 0.0)',
    ),
    "aureon/vault/aureon_vault.py": (
        "self.last_lambda_t = lambda_reading(payload[\"coherence_gamma\"])",
        "self.last_lambda_t = float(payload[\"coherence_gamma\"])",
        "self.last_lambda_t: float = 0.0",
    ),
    "aureon/gates/panel.py": (
        "last_lambda_t: float = 0.0",
    ),
    "aureon/queen/hnc_human_loop.py": (
        'getattr(lambda_state, "lambda_t", 0.0)',
        "last_lambda_t: float = 0.0",
    ),
    "aureon/core/cognitive_dashboard.py": (
        'src.get("lambda_t", 0.0)',
        "src.get('lambda_t', 0.0)",
    ),
    "aureon/core/integrated_cognitive_system_unreleased.py": (
        'source_state.get("lambda_t", 0.0)',
        "source_state.get('lambda_t', 0.0)",
    ),
    "aureon/observer/benchmark.py": (
        'get("lambda_t", 0.0) or 0.0',
        "get('lambda_t', 0.0) or 0.0",
    ),
    "aureon/observer/historical_backtest.py": (
        'get("lambda_t") or 0.0',
        "get('lambda_t') or 0.0",
    ),
    "aureon/trading/aureon_unified_ecosystem.py": (
        'report.get("lambda_t", 0.0)',
        "report.get('lambda_t', 0.0)",
    ),
}


def _fingerprint(lam):
    quantifier = CasimirQuantifier.__new__(CasimirQuantifier)
    vault = SimpleNamespace(
        last_lambda_t=lam,
        love_amplitude=0.2,
        gratitude_score=0.4,
        rally_active=False,
    )
    return quantifier._vault_fingerprint(vault)


def test_casimir_fingerprint_does_not_format_missing_lambda_as_zero():
    missing = _fingerprint(None)
    zero = _fingerprint(0.0)
    assert missing != zero
    assert _fingerprint(0.0) == zero


def test_cortex_gamma_does_not_set_last_lambda_t():
    vault = AureonVault()
    vault.ingest("queen.cortex.state", {
        "coherence_gamma": 0.42,
        "bands": {"gamma": {"amplitude": 0.5}},
    })
    assert vault.last_lambda_t is None
    assert vault.coherence_gamma == pytest.approx(0.42)
    status = vault.get_status()
    assert status["last_lambda_t"] is None
    assert status["coherence_gamma"] == pytest.approx(0.42)
    unread = vault.fingerprint()
    vault.last_lambda_t = 0.0
    assert vault.fingerprint() != unread


def test_cortex_gamma_field_alias_does_not_set_last_lambda_t():
    vault = AureonVault()
    vault.ingest("queen.cortex.state", {"coherence_gamma_field": 0.0})
    assert vault.last_lambda_t is None
    assert vault.coherence_gamma == 0.0
    assert vault.coherence_gamma is not None


def test_cortex_payload_with_real_lambda_uses_it():
    vault = AureonVault()
    vault.ingest("queen.cortex.state", {
        "coherence_gamma": 0.8,
        "lambda_t": 0.0,
    })
    assert vault.coherence_gamma == pytest.approx(0.8)
    assert vault.last_lambda_t == 0.0
    assert vault.last_lambda_t is not None
    assert vault.get_status()["last_lambda_t"] == 0.0


def test_field_vault_and_null_vault_start_unread():
    assert FieldVault().last_lambda_t is None
    assert FieldVault(last_lambda_t=0.0).last_lambda_t == 0.0
    assert _NullVault.last_lambda_t is None


def test_engine_lambda_missing_attribute_is_not_zero():
    assert read_engine_lambda(SimpleNamespace()) is None
    assert read_engine_lambda(SimpleNamespace(lambda_t=0.0)) == 0.0
    assert read_engine_lambda(SimpleNamespace(lambda_t=0.0)) is not None
    assert read_engine_lambda(None) is None


def test_lambda_reading_rejects_bool_and_non_finite():
    assert lambda_reading(True) is None
    assert lambda_reading(float("nan")) is None
    assert lambda_reading(float("inf")) is None
    assert lambda_reading(float("-inf")) is None
    assert lambda_reading(0.0) == 0.0
    assert lambda_reading(0.0) is not None


def test_dashboard_lambda_text_distinguishes_gap_from_zero():
    assert source_lambda_text({}) == "no reading"
    assert source_lambda_text({"lambda_t": None}) == "no reading"
    assert source_lambda_text({"lambda_t": 0.0}) == "+0.0000"


def test_benchmark_trace_drops_gaps_and_keeps_zero():
    snaps = [
        {"engine_state": {}},
        {"engine_state": {"lambda_t": None}},
        {"engine_state": {"lambda_t": 0.0}},
        {"engine_state": {"lambda_t": 1.5}},
    ]
    assert engine_lambda_trace(snaps) == [0.0, 1.5]


def test_backtest_trace_and_cell():
    snaps = [{"lambda_t": None}, {"kp": 1}, {"lambda_t": 0.0}]
    assert snapshot_lambda_trace(snaps) == [0.0]
    assert snapshot_lambda_cell({}) == "no reading"
    assert snapshot_lambda_cell({"lambda_t": 0.0}) == "0.000"


def test_watch_line_says_no_reading_until_lambda_is_present():
    eco = AureonKrakenEcosystem.__new__(AureonKrakenEcosystem)
    eco.qgita = None
    missing = eco._cognitive_telemetry_line({"valid": True, "coherence_gamma": 0.2, "consciousness_psi": 0.1})
    zero = eco._cognitive_telemetry_line({
        "valid": True,
        "lambda_t": 0.0,
        "coherence_gamma": 0.2,
        "consciousness_psi": 0.1,
    })
    assert "L=no reading" in missing
    assert "L=0.000" in zero


def _ics_lambda():
    path = ROOT / "aureon/core/integrated_cognitive_system_unreleased.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    future = next(
        node for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "__future__"
    )
    func = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_ics_lambda"
    )
    module = ast.Module(body=[future, func], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace: dict = {"Any": object}
    exec(compile(module, str(path), "exec"), namespace)
    return namespace["_ics_lambda"]


def test_dashboard_starts_with_no_lambda_reading():
    from aureon.core.cognitive_dashboard import _DashboardState

    state = _DashboardState()
    assert source_lambda_text(state.source) == "no reading"
    state.update("source", {"consciousness_level": "AWAKE"})
    assert source_lambda_text(state.source) == "no reading"
    state.update("source", {"lambda_t": 0.0})
    assert source_lambda_text(state.source) == "+0.0000"


def test_human_loop_without_a_tick_does_not_ground_zero():
    from aureon.queen.hnc_human_loop import HNCHumanLoop, HNCInteractionResult

    assert HNCInteractionResult(human_text="unread").lambda_t is None
    loop = HNCHumanLoop()
    loop._tick_lambda = lambda text, intent: None
    result = loop.process("hello")
    assert result["hnc"]["lambda_t"] is None
    assert result["temporal_ground"]["status"] == "no reading"
    assert result["temporal_ground"]["lambda_t"] is None


def test_unreleased_ics_fallback_lambda_is_unread():
    text = (ROOT / "aureon/core/integrated_cognitive_system_unreleased.py").read_text(encoding="utf-8")
    assert '"lambda_t": None, "coherence_gamma": 0.0' in text
    assert '"lambda_t": 0.0, "coherence_gamma": 0.0' not in text
    read = _ics_lambda()
    assert read({}) is None
    assert read({"lambda_t": None}) is None
    assert read({"lambda_t": 0.0}) == 0.0
    assert read({"lambda_t": 0.0}) is not None


@pytest.mark.parametrize("relpath,snippets", list(_FORBIDDEN.items()))
def test_site_does_not_coerce_missing_lambda_with_or_zero(relpath, snippets):
    text = (ROOT / relpath).read_text(encoding="utf-8")
    for snippet in snippets:
        assert snippet not in text, f"{relpath} still has {snippet}"
