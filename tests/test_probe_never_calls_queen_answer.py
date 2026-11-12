"""The signal probe must never call the kill chain's y/N prompt helper.

Probing ``queen_answer("BTCUSD", price)`` logged "Headless decision: BTCUSD -> Y"
in the live log (12 Nov 2026 restart), which reads like a trading decision,
and under a TTY it would block on input(). Both copies of the never-call set
must list it and must stay identical.
"""
import ast
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _never_call(path: Path) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_NEVER_CALL" for t in node.targets
        ):
            call = node.value
            assert isinstance(call, ast.Call) and call.func.id == "frozenset"
            return set(ast.literal_eval(call.args[0]))
    raise AssertionError(f"_NEVER_CALL not found in {path}")


def test_both_never_call_sets_list_queen_answer_and_match():
    hub = _never_call(ROOT / "aureon_radar" / "unified_hub.py")
    adapters = _never_call(ROOT / "aureon_fusion" / "signal_adapters.py")
    assert "queen_answer" in hub
    assert hub == adapters


def test_adapter_probe_does_not_call_queen_answer():
    from aureon_fusion import signal_adapters as sa

    calls = []
    mod = types.ModuleType("fake_kill_chain")

    def queen_answer(question, queen_approves):
        calls.append((question, queen_approves))
        return "y"

    mod.queen_answer = queen_answer
    w = sa.SignalAdapterModule(mod, "harmonic:fake_kill_chain")
    w.scan("BTCUSD", 50000.0)
    assert calls == []
