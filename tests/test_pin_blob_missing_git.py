"""Pin check must name a missing git history, and still refuse a mismatched blob."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.support.mcp_isolation import ensure_mcp_path

ensure_mcp_path()

from aureon_public.guard_loader import PINNED_COMMIT
from aureon_public.pin_blob import (
    PinnedAureonFinder,
    expected_pin_blob,
    git_blob_sha1,
)

PIN_SHORT = PINNED_COMMIT[:12]
MISSING_HISTORY = (
    f"pin commit {PIN_SHORT} is not available in this tree; "
    "the MCP pin check needs a git clone that contains that history "
    "(a ZIP download has no .git)"
)


def test_missing_git_history_names_the_pin_commit(tmp_path: Path) -> None:
    """A tree with no .git must not be reported as a missing module path."""

    package = tmp_path / "aureon"
    package.mkdir()
    (package / "__init__.py").write_text("# checkout copy\n", encoding="utf-8")
    finder = PinnedAureonFinder(tmp_path, PINNED_COMMIT)

    with pytest.raises(ImportError) as refused:
        finder.find_spec("aureon", None)

    text = str(refused.value)
    assert text == MISSING_HISTORY
    assert "is not an aureon module path" not in text
    expected, error = expected_pin_blob(package / "__init__.py", tmp_path, PINNED_COMMIT)
    assert expected is None
    assert error == MISSING_HISTORY


def test_mismatched_blob_still_differs_from_pin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When the pin commit can be read, a different working-tree file is still refused."""

    package = tmp_path / "aureon"
    package.mkdir()
    path = package / "__init__.py"
    path.write_text("# working tree differs\n", encoding="utf-8")
    expected_hash = git_blob_sha1(b"# pinned bytes\n")

    def fake_check_output(argv, **kwargs):
        del kwargs
        if len(argv) >= 3 and argv[0] == "git" and argv[1] == "cat-file" and argv[2] == "-e":
            return ""
        if len(argv) >= 3 and argv[0] == "git" and argv[1] == "rev-parse" and ":" in str(argv[2]):
            relative = str(argv[2]).split(":", 1)[1]
            if (tmp_path / relative).is_file():
                return expected_hash + "\n"
        raise subprocess.CalledProcessError(128, argv)

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    finder = PinnedAureonFinder(tmp_path, PINNED_COMMIT)

    with pytest.raises(ImportError) as refused:
        finder.find_spec("aureon", None)

    text = str(refused.value)
    assert text == f"checkout aureon/__init__.py differs from pin {PIN_SHORT}"
    assert "is not an aureon module path" not in text
    assert "is not available in this tree" not in text


def test_unknown_module_still_not_an_aureon_module_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When git history is present, an unknown name stays a missing module path."""

    def fake_check_output(argv, **kwargs):
        del kwargs
        if len(argv) >= 3 and argv[0] == "git" and argv[1] == "cat-file" and argv[2] == "-e":
            return ""
        raise subprocess.CalledProcessError(128, argv)

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    finder = PinnedAureonFinder(tmp_path, PINNED_COMMIT)

    with pytest.raises(ImportError) as refused:
        finder.find_spec("aureon.not_a_real_module", None)

    assert str(refused.value) == "aureon.not_a_real_module is not an aureon module path"


def test_checkout_module_added_after_the_pin_is_named_as_not_in_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real aureon module file that the pin lacks is refused as 'not in pin', not as a bad path."""

    added = tmp_path / "aureon" / "utils" / "added_after_pin.py"
    added.parent.mkdir(parents=True)
    added.write_text("VALUE = 1\n", encoding="utf-8")

    def fake_check_output(argv, **kwargs):
        del kwargs
        if len(argv) >= 3 and argv[0] == "git" and argv[1] == "cat-file" and argv[2] == "-e":
            return ""
        raise subprocess.CalledProcessError(128, argv)

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    finder = PinnedAureonFinder(tmp_path, PINNED_COMMIT)

    with pytest.raises(ImportError) as refused:
        finder.find_spec("aureon.utils.added_after_pin", None)

    text = str(refused.value)
    assert text == f"aureon/utils/added_after_pin.py is not in pin {PIN_SHORT}"
    assert "is not an aureon module path" not in text
