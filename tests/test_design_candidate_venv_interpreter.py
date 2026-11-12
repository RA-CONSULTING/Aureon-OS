"""A standard POSIX venv's linked ``python`` resolves; hostile links do not.

``python -m venv`` on Linux and macOS makes ``<venv>/bin/python`` a symlink
chain to the base interpreter. The candidate test-evidence harness refused it
with "python executable may not traverse a symbolic link or reparse point",
which failed about 60 tests for anyone on a normal venv. Only that venv shape
is accepted. Every other link is still refused. Go-live stays HOLD.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from aureon.operator import design_candidate_test_evidence as evidence

ROOT = Path(__file__).resolve().parents[1]
REFUSAL = "may not traverse a symbolic link"

pytestmark = pytest.mark.skipif(os.name == "nt", reason="POSIX venv link layout")


def _layout(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Return (base_prefix, venv_prefix, real base interpreter) like Debian + venv."""

    base = tmp_path / "base"
    (base / "bin").mkdir(parents=True)
    real = base / "bin" / "python3.13"
    real.write_bytes(b"#!interpreter-bytes\n")
    real.chmod(0o755)
    (base / "bin" / "python3").symlink_to("python3.13")
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text(f"home = {base / 'bin'}\n", encoding="utf-8")
    (venv / "bin" / "python3").symlink_to(base / "bin" / "python3")
    (venv / "bin" / "python").symlink_to("python3")
    return base, venv, real


def _activate(
    monkeypatch: pytest.MonkeyPatch,
    *,
    executable: Path,
    prefix: Path,
    base_prefix: Path,
    base_executable: Path,
) -> None:
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(sys, "prefix", str(prefix))
    monkeypatch.setattr(sys, "base_prefix", str(base_prefix))
    monkeypatch.setattr(sys, "_base_executable", str(base_executable), raising=False)


def test_standard_venv_link_chain_resolves_to_the_base_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, venv, real = _layout(tmp_path)
    _activate(
        monkeypatch,
        executable=venv / "bin" / "python",
        prefix=venv,
        base_prefix=base,
        base_executable=base / "bin" / "python3",
    )
    assert evidence._reviewed_python_executable() == real  # noqa: SLF001
    resolved, token = evidence._resolve_tool("python")  # noqa: SLF001
    assert (resolved, token) == (real, "{python}")


def test_venv_link_to_an_arbitrary_absolute_file_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, venv, _ = _layout(tmp_path)
    hostile = tmp_path / "elsewhere" / "python3"
    hostile.parent.mkdir()
    hostile.write_bytes(b"#!not-the-interpreter\n")
    (venv / "bin" / "python3").unlink()
    (venv / "bin" / "python3").symlink_to(hostile)
    _activate(
        monkeypatch,
        executable=venv / "bin" / "python",
        prefix=venv,
        base_prefix=base,
        base_executable=base / "bin" / "python3",
    )
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match=REFUSAL):
        evidence._reviewed_python_executable()  # noqa: SLF001


def test_venv_link_to_another_binary_in_the_base_bin_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, venv, _ = _layout(tmp_path)
    other = base / "bin" / "perl"
    other.write_bytes(b"#!some-other-tool\n")
    (venv / "bin" / "python3").unlink()
    (venv / "bin" / "python3").symlink_to(other)
    _activate(
        monkeypatch,
        executable=venv / "bin" / "python",
        prefix=venv,
        base_prefix=base,
        base_executable=base / "bin" / "python3",
    )
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match=REFUSAL):
        evidence._reviewed_python_executable()  # noqa: SLF001


def test_dotdot_and_multi_part_relative_links_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, venv, _ = _layout(tmp_path)
    for target in ("../../base/bin/python3.13", "sub/python3"):
        (venv / "bin" / "python").unlink()
        (venv / "bin" / "python").symlink_to(target)
        _activate(
            monkeypatch,
            executable=venv / "bin" / "python",
            prefix=venv,
            base_prefix=base,
            base_executable=base / "bin" / "python3",
        )
        with pytest.raises(evidence.DesignCandidateTestEvidenceError, match=REFUSAL):
            evidence._reviewed_python_executable()  # noqa: SLF001


def test_link_outside_the_running_venv_bin_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, venv, _ = _layout(tmp_path)
    stray = tmp_path / "stray"
    stray.mkdir()
    (stray / "python").symlink_to(base / "bin" / "python3")
    _activate(
        monkeypatch,
        executable=stray / "python",
        prefix=venv,
        base_prefix=base,
        base_executable=base / "bin" / "python3",
    )
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match=REFUSAL):
        evidence._reviewed_python_executable()  # noqa: SLF001


def test_absolute_link_outside_a_venv_is_still_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, venv, _ = _layout(tmp_path)
    (venv / "pyvenv.cfg").unlink()
    _activate(
        monkeypatch,
        executable=venv / "bin" / "python",
        prefix=base,
        base_prefix=base,
        base_executable=base / "bin" / "python3",
    )
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match=REFUSAL):
        evidence._reviewed_python_executable()  # noqa: SLF001


def test_linked_venv_marker_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base, venv, _ = _layout(tmp_path)
    real_cfg = tmp_path / "cfg"
    (venv / "pyvenv.cfg").rename(real_cfg)
    (venv / "pyvenv.cfg").symlink_to(real_cfg)
    _activate(
        monkeypatch,
        executable=venv / "bin" / "python",
        prefix=base,
        base_prefix=base,
        base_executable=base / "bin" / "python3",
    )
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match=REFUSAL):
        evidence._reviewed_python_executable()  # noqa: SLF001


def test_sealed_no_site_venv_still_resolves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``-I -S -B`` leaves sys.prefix at the base; pyvenv.cfg still marks the venv."""

    base, venv, real = _layout(tmp_path)
    _activate(
        monkeypatch,
        executable=venv / "bin" / "python",
        prefix=base,
        base_prefix=base,
        base_executable=real,
    )
    assert evidence._reviewed_python_executable() == real  # noqa: SLF001


def test_venv_reached_through_a_linked_directory_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, venv, _ = _layout(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(venv, target_is_directory=True)
    _activate(
        monkeypatch,
        executable=alias / "bin" / "python",
        prefix=alias,
        base_prefix=base,
        base_executable=base / "bin" / "python3",
    )
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match=REFUSAL):
        evidence._reviewed_python_executable()  # noqa: SLF001


def test_link_loop_and_overlong_chain_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, venv, _ = _layout(tmp_path)
    (venv / "bin" / "python").unlink()
    (venv / "bin" / "python").symlink_to("python-a")
    (venv / "bin" / "python-a").symlink_to("python-b")
    (venv / "bin" / "python-b").symlink_to("python")
    _activate(
        monkeypatch,
        executable=venv / "bin" / "python",
        prefix=venv,
        base_prefix=base,
        base_executable=base / "bin" / "python3",
    )
    with pytest.raises(evidence.DesignCandidateTestEvidenceError, match=REFUSAL):
        evidence._reviewed_python_executable()  # noqa: SLF001


def test_a_real_symlinked_venv_resolves_to_its_base_interpreter(tmp_path: Path) -> None:
    """End to end: ``python -m venv --symlinks`` from the running interpreter."""

    base_python = os.path.realpath(getattr(sys, "_base_executable", sys.executable))
    venv = tmp_path / "symlinked-venv"
    subprocess.run(
        [base_python, "-m", "venv", "--symlinks", "--without-pip", str(venv)],
        check=True,
        timeout=120,
        capture_output=True,
    )
    linked = venv / "bin" / "python"
    assert linked.is_symlink()
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "from aureon.operator import design_candidate_test_evidence as e;"
        "print(e._reviewed_python_executable())"
    )
    completed = subprocess.run(
        [str(linked), "-I", "-c", probe, str(ROOT)],
        check=False,
        timeout=120,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    resolved = Path(completed.stdout.strip())
    assert not resolved.is_symlink()
    assert os.path.samefile(resolved, base_python)
    sealed = subprocess.run(
        [str(linked), "-I", "-S", "-B", "-c", probe, str(ROOT)],
        check=False,
        timeout=120,
        capture_output=True,
        text=True,
    )
    assert sealed.returncode == 0, sealed.stderr[-2000:]
    assert os.path.samefile(sealed.stdout.strip(), base_python)
