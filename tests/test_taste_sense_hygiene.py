from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aureon" / "intelligence" / "aureon_taste_sense.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_taste_sense_scoped", TARGET)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_taste_sense_uses_repo_codex_and_has_no_import_or_cli_side_effect():
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(TARGET))
    assert "_baton_link(__name__)" not in source
    assert not any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        for node in tree.body
    )

    module = _load_module()
    assert module._CODEX_PATH == ROOT / "public" / "taste_molecular_codex.json"
    sense = module.TasteSense()
    assert sense.molecule_names()
    assert module.TasteExperience.__dataclass_fields__["eligible_for_action"].default is False
    assert module.TasteExperience.__dataclass_fields__["eligible_for_accounting"].default is False
    assert module.TasteExperience.__dataclass_fields__["eligible_for_learning"].default is False
