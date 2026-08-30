from __future__ import annotations

import ast
from pathlib import Path


TARGET = (
    Path(__file__).resolve().parents[1]
    / "aureon"
    / "scanners"
    / "aureon_ocean_scanner.py"
)


def test_ocean_scanner_has_no_import_mutation_or_standalone_network_runner() -> None:
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(TARGET))

    assert "_baton_link(__name__)" not in source
    assert "sys.stdout =" not in source
    assert "AUREON OCEAN SCANNER - TEST MODE" not in source
    assert "ticker.get('price', 0)" not in source
    assert "ticker.get('volume', 0)" not in source
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
