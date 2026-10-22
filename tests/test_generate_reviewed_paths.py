"""Offline tests for complete reviewed-path manifest generation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


DIRECTORY = Path(__file__).resolve().parents[1] / "deployment/google-cloud"
sys.path.insert(0, str(DIRECTORY))
spec = importlib.util.spec_from_file_location(
    "generate_reviewed_paths", DIRECTORY / "generate_reviewed_paths.py"
)
assert spec and spec.loader
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def test_generator_unions_runtime_closures_and_complete_dist(monkeypatch, tmp_path):
    source = (tmp_path / "source").resolve()
    files = {
        "operator.py",
        "collector.py",
        "ui.py",
        "organ.py",
        "broker.py",
        "bridge.py",
        "aureon-os-upstream/frontend/dist/index.html",
        "aureon-os-upstream/frontend/dist/assets/app.js",
    }
    for relative in files:
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative, encoding="utf-8")
    monkeypatch.setattr(generator, "_bind_source", lambda *_: ["package.py"])
    monkeypatch.setattr(
        generator, "required_operator_runtime_sources", lambda _: ("operator.py",)
    )
    monkeypatch.setattr(generator, "COLLECTOR_REQUIRED_SOURCES", {"collector.py"})
    monkeypatch.setattr(generator, "UI_GATEWAY_REQUIRED_SOURCES", {"ui.py"})
    monkeypatch.setattr(generator, "READ_ORGAN_REQUIRED_SOURCES", {"organ.py"})
    monkeypatch.setattr(generator, "TOKEN_BROKER_REQUIRED_SOURCES", {"broker.py"})
    monkeypatch.setattr(generator, "PUBLIC_BRIDGE_REQUIRED_SOURCES", {"bridge.py"})
    monkeypatch.setattr(
        generator,
        "_git_blob",
        lambda checkout, _revision, relative: (checkout / relative).read_bytes(),
    )

    rows = generator.reviewed_paths(source, "a" * 40)
    assert {row["path"] for row in rows} == files
    assert all(len(row["sha256"]) == 64 for row in rows)

    output = (tmp_path / "reviewed-paths.json").resolve()
    manifest_hash = generator.write_manifest(output, rows)
    assert len(manifest_hash) == 64
    with pytest.raises(generator.ReviewedPathsError, match="new_absolute"):
        generator.write_manifest(output, rows)
