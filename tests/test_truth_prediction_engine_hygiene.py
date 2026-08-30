from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aureon" / "intelligence" / "aureon_truth_prediction_engine.py"


def test_truth_prediction_import_and_standalone_path_are_inert():
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(TARGET))

    assert "_baton_link(__name__)" not in source
    assert "PYTHONIOENCODING" not in source
    assert "sys.stdout" not in source
    assert "sys.stderr" not in source
    assert not any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        for node in tree.body
    )
