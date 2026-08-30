from __future__ import annotations

import ast
from pathlib import Path


TARGET = (
    Path(__file__).resolve().parents[1]
    / "aureon"
    / "intelligence"
    / "aureon_real_intelligence_engine.py"
)


def _load_volume_method():
    tree = ast.parse(TARGET.read_text(encoding="utf-8"))
    profiler = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RealBotProfiler"
    )
    method = next(
        node
        for node in profiler.body
        if isinstance(node, ast.FunctionDef) and node.name == "_get_volume"
    )
    module = ast.Module(
        body=[
            ast.Import(names=[ast.alias(name="math")]),
            ast.ImportFrom(
                module="typing",
                names=[ast.alias(name="Optional")],
                level=0,
            ),
            ast.ClassDef(
                name="Probe",
                bases=[],
                keywords=[],
                body=[method],
                decorator_list=[],
            ),
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    namespace: dict[str, object] = {}
    exec(compile(module, str(TARGET), "exec"), namespace)
    probe = namespace["Probe"]()
    return probe._get_volume


def test_real_intelligence_hygiene_and_missing_volume_fail_closed() -> None:
    source = TARGET.read_text(encoding="utf-8")

    assert "_baton_link" not in source
    assert "PYTHONIOENCODING" not in source
    assert "sys.stdout" not in source
    assert 'if __name__ == "__main__"' not in source
    assert "if volume is None:" in source

    get_volume = _load_volume_method()
    assert get_volume("BTC/USD", None) is None
    assert get_volume("BTC/USD", {}) is None
    assert get_volume("BTC/USD", {"BTC/USD": {}}) is None
    assert get_volume("BTC/USD", {"BTC/USD": {"volume": "bad"}}) is None
    assert get_volume("BTC/USD", {"BTC/USD": {"volume": float("nan")}}) is None
    assert get_volume("BTC/USD", {"BTC/USD": {"volume": -1}}) is None
    assert get_volume("BTC/USD", {"BTC/USD": {"volume": "12.5"}}) == 12.5
