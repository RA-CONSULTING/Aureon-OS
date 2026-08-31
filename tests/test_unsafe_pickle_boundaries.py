from __future__ import annotations

import ast
import importlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    ROOT / "aureon" / "bots" / "whale_shape_ml_trainer.py",
    ROOT / "aureon" / "harmonic" / "aureon_harmonic_seed.py",
)


def test_runtime_sources_contain_no_pickle_load_or_dump_call() -> None:
    for path in TARGETS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        calls = {
            (node.func.value.id, node.func.attr)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
        }

        assert "pickle" not in imports
        assert ("pickle", "load") not in calls
        assert ("pickle", "loads") not in calls
        assert ("pickle", "dump") not in calls
        assert ("pickle", "dumps") not in calls


def test_legacy_pickle_artifacts_are_explicitly_ignored() -> None:
    trainer = TARGETS[0].read_text(encoding="utf-8")
    seed = TARGETS[1].read_text(encoding="utf-8")

    assert 'glob("*.pkl")' in trainer
    assert "legacy pickle artifact(s) ignored" in trainer
    assert 'legacy_pickle = self.cache_dir / "harmonic_seed.pkl"' in seed
    assert "pickle deserialization is disabled" in seed
    assert 'cache_file = self.cache_dir / "harmonic_seed.json"' in seed


def _load_seed_module(monkeypatch: pytest.MonkeyPatch):
    import aureon.core.aureon_baton_link as baton_link

    monkeypatch.setattr(baton_link, "link_system", lambda *_args, **_kwargs: None)
    sys.modules.pop("aureon.harmonic.aureon_harmonic_seed", None)
    return importlib.import_module("aureon.harmonic.aureon_harmonic_seed")


def test_harmonic_json_cache_is_canonical_duplicate_free_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = _load_seed_module(monkeypatch)
    state = seed.GlobalHarmonicState(
        symbols={"BTC": seed.SymbolWaveState(symbol="BTC")},
        coherence_matrix={"BTC": {"BTC": 1.0}},
    )
    payload = state.to_dict()
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    decoded = seed._decode_harmonic_cache(raw)
    restored = seed.GlobalHarmonicState.from_dict(decoded)
    assert restored.symbols["BTC"].symbol == "BTC"
    assert restored.coherence_matrix == {"BTC": {"BTC": 1.0}}

    duplicate = raw[:-1] + b',"candle_count":0}'
    with pytest.raises(ValueError, match="harmonic_seed_cache_json_invalid"):
        seed._decode_harmonic_cache(duplicate)

    extended = {**payload, "unexpected": True}
    with pytest.raises(ValueError, match="harmonic_seed_cache_schema_invalid"):
        seed.GlobalHarmonicState.from_dict(extended)

    payload["symbols"]["BTC"]["price_history"] = [0.0] * (
        seed.MAX_HARMONIC_HISTORY_VALUES + 1
    )
    with pytest.raises(ValueError, match="price_history_invalid"):
        seed.GlobalHarmonicState.from_dict(payload)
