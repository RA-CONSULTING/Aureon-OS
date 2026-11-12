"""The Capital CFD status must not claim the Seer/Lyra gate is ARMED while
_quad_gate()'s modifier is never applied to order sizing."""
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FILES = ["aureon/exchanges/capital_cfd_trader.py", "aureon_radar/capital_cfd_trader.py"]


@pytest.mark.parametrize("rel", FILES)
def test_quad_gate_label_matches_behaviour(rel):
    path = ROOT / rel
    if not path.exists():
        pytest.skip(f"{rel} not present")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    readers = set()
    labels = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(fn):
            if (isinstance(node, ast.Attribute) and node.attr == "_quad_gate_modifier"
                    and isinstance(node.ctx, ast.Load)):
                readers.add(fn.name)
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "gate" for t in node.targets):
                labels.extend(c.value for c in ast.walk(node.value)
                              if isinstance(c, ast.Constant) and isinstance(c.value, str))
    assert labels, "status gate label not found"
    if readers <= {"_quad_gate"}:
        # modifier never applied outside its own cache: must not say ARMED
        assert "ARMED" not in labels
        assert "advisory" in labels
