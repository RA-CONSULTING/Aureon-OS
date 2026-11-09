"""Kernel patch is not part of the evidence byte compare.

The committed platform string stays the record. Python, NumPy, OS, arch,
and libc stay in the compare.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aureon.evidence.runner import (
    check,
    kernel_without_patch,
    same_platform_except_kernel_patch,
)
from aureon.evidence.serialize import dump

COMMITTED_PLATFORM = "Linux-6.12.94+-x86_64-with-glibc2.39"
FRESH_PLATFORM = "Linux-6.12.113+-x86_64-with-glibc2.39"


def test_only_the_kernel_patch_is_dropped() -> None:
    assert kernel_without_patch("6.12.94+") == "6.12"
    assert kernel_without_patch("6.12.113+") == "6.12"
    assert same_platform_except_kernel_patch(COMMITTED_PLATFORM, FRESH_PLATFORM)
    assert same_platform_except_kernel_patch(COMMITTED_PLATFORM, COMMITTED_PLATFORM)
    assert not same_platform_except_kernel_patch(
        COMMITTED_PLATFORM,
        "Darwin-6.12.113+-x86_64-with-glibc2.39",
    )
    assert not same_platform_except_kernel_patch(
        COMMITTED_PLATFORM,
        "Linux-6.13.94+-x86_64-with-glibc2.39",
    )
    assert not same_platform_except_kernel_patch(
        COMMITTED_PLATFORM,
        "Linux-6.12.113+-aarch64-with-glibc2.39",
    )
    assert not same_platform_except_kernel_patch(
        COMMITTED_PLATFORM,
        "Linux-6.12.113+-x86_64-with-glibc2.35",
    )


def _environment(platform_text: str, *, numpy_version: str = "1.26.4", python_version: str = "3.12.3") -> dict:
    return {
        "commit_sha": "committed-sha",
        "machine": "x86_64",
        "numpy_version": numpy_version,
        "platform": platform_text,
        "python_version": python_version,
        "schema": "aureon.evidence.environment.v1",
    }


def _write_bundle(root: Path, environment: dict, platform_text: str) -> None:
    evidence = root / "evidence"
    evidence.mkdir()
    (evidence / "environment.json").write_text(dump(environment), encoding="utf-8")
    (evidence / "RESULTS.md").write_text(
        "\n".join(
            [
                "| Python | " + environment["python_version"] + " |",
                "| NumPy | " + environment["numpy_version"] + " |",
                "| platform | " + platform_text + " |",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _fresh_files(environment: dict, platform_text: str) -> dict[str, str]:
    return {
        "evidence/environment.json": dump(environment),
        "evidence/RESULTS.md": "\n".join(
            [
                "| Python | " + environment["python_version"] + " |",
                "| NumPy | " + environment["numpy_version"] + " |",
                "| platform | " + platform_text + " |",
                "",
            ]
        ),
    }


def test_python_and_numpy_versions_stay_in_the_byte_compare(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    committed = _environment(COMMITTED_PLATFORM)
    _write_bundle(tmp_path, committed, COMMITTED_PLATFORM)
    fresh = _environment(FRESH_PLATFORM, numpy_version="2.5.4", python_version="3.13.1")
    monkeypatch.setattr(
        "aureon.evidence.runner.build",
        lambda *_args, **_kwargs: _fresh_files(fresh, FRESH_PLATFORM),
    )

    assert check(tmp_path) == 1
    captured = capsys.readouterr()
    assert "reproduced on a different kernel" not in captured.out
    assert "2.5.4" in captured.err
    assert "3.13.1" in captured.err
    recorded = json.loads((tmp_path / "evidence" / "environment.json").read_text(encoding="utf-8"))
    assert recorded["platform"] == COMMITTED_PLATFORM
    assert recorded["numpy_version"] == "1.26.4"
    assert recorded["python_version"] == "3.12.3"


def test_different_kernel_pass_names_both_platforms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    committed = _environment(COMMITTED_PLATFORM)
    _write_bundle(tmp_path, committed, COMMITTED_PLATFORM)
    fresh = _environment(FRESH_PLATFORM)
    monkeypatch.setattr(
        "aureon.evidence.runner.build",
        lambda *_args, **_kwargs: _fresh_files(fresh, FRESH_PLATFORM),
    )

    assert check(tmp_path) == 0
    captured = capsys.readouterr()
    assert "reproduced on a different kernel" in captured.out
    assert "byte-for-byte match" not in captured.out
    assert "identical" not in captured.out.casefold()
    assert f"committed platform: {COMMITTED_PLATFORM}" in captured.out
    assert f"this run platform: {FRESH_PLATFORM}" in captured.out
    assert "Linux-6.12.94+" in captured.out
    recorded = (tmp_path / "evidence" / "RESULTS.md").read_text(encoding="utf-8")
    assert COMMITTED_PLATFORM in recorded
    assert FRESH_PLATFORM not in recorded


def test_a_measured_module_hash_still_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    committed = _environment(COMMITTED_PLATFORM)
    committed["source_sha256"] = {
        "aureon/evidence/hnc.py": "a" * 64,
        "aureon/evidence/runner.py": "b" * 64,
    }
    _write_bundle(tmp_path, committed, COMMITTED_PLATFORM)
    fresh = _environment(FRESH_PLATFORM)
    fresh["source_sha256"] = {
        "aureon/evidence/hnc.py": "c" * 64,
        "aureon/evidence/runner.py": "d" * 64,
    }
    monkeypatch.setattr(
        "aureon.evidence.runner.build",
        lambda *_args, **_kwargs: _fresh_files(fresh, FRESH_PLATFORM),
    )

    assert check(tmp_path) == 1
    captured = capsys.readouterr()
    assert "aureon/evidence/hnc.py" in captured.err
    assert "reproduced on a different kernel" not in captured.out


def test_the_committed_checker_fingerprint_is_not_rewritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    committed = _environment(COMMITTED_PLATFORM)
    committed["source_sha256"] = {"aureon/evidence/runner.py": "b" * 64}
    _write_bundle(tmp_path, committed, COMMITTED_PLATFORM)
    fresh = _environment(FRESH_PLATFORM)
    fresh["source_sha256"] = {"aureon/evidence/runner.py": "d" * 64}
    monkeypatch.setattr(
        "aureon.evidence.runner.build",
        lambda *_args, **_kwargs: _fresh_files(fresh, FRESH_PLATFORM),
    )

    assert check(tmp_path) == 0
    recorded = json.loads((tmp_path / "evidence" / "environment.json").read_text(encoding="utf-8"))
    assert recorded["source_sha256"]["aureon/evidence/runner.py"] == "b" * 64
    assert "reproduced on a different kernel" in capsys.readouterr().out
