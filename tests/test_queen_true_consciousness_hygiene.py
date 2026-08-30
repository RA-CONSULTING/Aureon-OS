from __future__ import annotations

import ast
from pathlib import Path


TARGET = (
    Path(__file__).resolve().parents[1]
    / "aureon"
    / "utils"
    / "aureon_queen_true_consciousness.py"
)


def test_queen_module_does_not_mutate_process_or_default_provider_fields() -> None:
    source = TARGET.read_text(encoding="utf-8")
    ast.parse(source, filename=str(TARGET))

    assert "_baton_link(__name__)" not in source
    assert "sys.stdout =" not in source
    assert "sys.stderr =" not in source
    assert "ticker.get('lastPrice', 0)" not in source
    assert "ticker.get('priceChangePercent', 0)" not in source
    assert "ticker.get('quoteVolume', 0)" not in source
