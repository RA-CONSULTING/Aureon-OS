from __future__ import annotations

import ast
import importlib.util
from pathlib import Path


TARGET = (
    Path(__file__).resolve().parents[1]
    / "aureon"
    / "command_centers"
    / "aureon_strategic_war_planner.py"
)


def test_planner_import_is_inert_and_has_no_manufactured_cli(capsys) -> None:
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(TARGET))

    assert "_baton_link(__name__)" not in source
    assert "Simulate 5 market cycles" not in source
    assert not any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and any(
            isinstance(comparator, ast.Constant)
            and comparator.value == "__main__"
            for comparator in node.test.comparators
        )
        for node in tree.body
    )

    spec = importlib.util.spec_from_file_location(
        "strategic_war_planner_hygiene_target", TARGET
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
