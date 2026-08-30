from __future__ import annotations

from pathlib import Path

import pytest

from aureon.core.organism_composition import (
    OrganismComposition,
    bind_canonical_organism_composition,
)
from aureon.queen.queen_process_roof import (
    QueenProcessRoof,
    bind_queen_process_roof,
    discover_queen_process_manifest,
)


def _write(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _composition() -> OrganismComposition:
    return bind_canonical_organism_composition(
        present_subsystems={"thought_bus": "test nervous system"},
        calibration_status={"status": "hold", "reason": "test_hold"},
    )


def test_manifest_seats_every_active_queen_source_without_importing(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "aureon" / "queen" / "queen_alpha.py",
        "class QueenAlpha:\n    pass\n",
    )
    _write(
        tmp_path / "launchers" / "queen_runner.py",
        "def main():\n    return 'not imported'\n",
    )
    _write(
        tmp_path / "aureon" / "queen" / "queen_trader.py",
        "def run(client):\n    return client.place_market_order('XBTUSD')\n",
    )
    _write(
        tmp_path / "imports" / "snapshot" / "queen_ignored.py",
        "raise RuntimeError('must never import')\n",
    )
    _write(
        tmp_path / "tests" / "test_queen_ignored.py",
        "raise RuntimeError('must never import')\n",
    )

    first = discover_queen_process_manifest(tmp_path)
    second = discover_queen_process_manifest(tmp_path)
    by_file = {item.source_file: item for item in first.processes}

    assert first.to_dict() == second.to_dict()
    assert set(by_file) == {
        "aureon/queen/queen_alpha.py",
        "aureon/queen/queen_trader.py",
        "launchers/queen_runner.py",
    }
    assert by_file["aureon/queen/queen_trader.py"].effect_class == "authority_capable"
    assert by_file["launchers/queen_runner.py"].effect_class == "active_process"


def test_roof_constructor_is_factory_only(tmp_path: Path) -> None:
    _write(tmp_path / "aureon" / "queen" / "queen_alpha.py", "class QueenAlpha:\n    pass\n")
    manifest = discover_queen_process_manifest(tmp_path)

    with pytest.raises(TypeError, match="use_bind_queen_process_roof"):
        QueenProcessRoof(
            _factory_token=object(),
            composition=_composition(),
            manifest=manifest,
        )


def test_hold_composition_never_invokes_queen_factory(tmp_path: Path) -> None:
    _write(tmp_path / "aureon" / "queen" / "queen_alpha.py", "class QueenAlpha:\n    pass\n")
    roof = bind_queen_process_roof(composition=_composition(), root=tmp_path)
    calls = 0

    def factory() -> object:
        nonlocal calls
        calls += 1
        return object()

    activation = roof.activate("aureon.queen.queen_alpha", factory)

    assert activation.status == "HOLD"
    assert activation.reason == "canonical_organism_composition_not_ready"
    assert activation.receipt()["economic_mutation"] is False
    assert roof.status()["status"] == "hold"
    assert calls == 0


def test_unseated_process_never_invokes_factory(tmp_path: Path) -> None:
    _write(tmp_path / "aureon" / "queen" / "queen_alpha.py", "class QueenAlpha:\n    pass\n")
    roof = bind_queen_process_roof(composition=_composition(), root=tmp_path)
    calls = 0

    def factory() -> object:
        nonlocal calls
        calls += 1
        return object()

    activation = roof.activate("aureon.queen.queen_unknown", factory)

    assert activation.status == "HOLD"
    assert activation.reason == "seated_queen_process_required"
    assert calls == 0


def test_ready_roof_activates_one_seated_instance_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(tmp_path / "aureon" / "queen" / "queen_alpha.py", "class QueenAlpha:\n    pass\n")
    composition = _composition()
    monkeypatch.setattr(
        OrganismComposition,
        "status",
        lambda _self: {"status": "ready", "economic_blocker_count": 0},
    )
    roof = bind_queen_process_roof(composition=composition, root=tmp_path)
    calls = 0

    def factory() -> object:
        nonlocal calls
        calls += 1
        return object()

    first = roof.activate("aureon.queen.queen_alpha", factory)
    second = roof.activate("aureon.queen.queen_alpha", factory)

    assert first.status == second.status == "ACTIVE"
    assert first.instance is second.instance
    assert second.reason == "queen_process_already_active"
    assert roof.status()["active_process_count"] == 1
    assert calls == 1


def test_current_repo_manifest_covers_queen_layer_and_hive_mind() -> None:
    manifest = discover_queen_process_manifest()
    modules = {item.module_name for item in manifest.processes}

    assert "aureon.queen.queen_layer" in modules
    assert "aureon.queen.queen_mind" in modules
    assert "aureon.utils.aureon_queen_hive_mind" in modules
    assert all(not item.source_file.startswith("imports/") for item in manifest.processes)
    assert all(not item.source_file.startswith("tests/") for item in manifest.processes)
