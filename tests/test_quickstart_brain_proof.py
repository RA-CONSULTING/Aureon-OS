"""The README quickstart measurement must not lead with unbacked banners."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_HEADING = "# HNC, Auris coherence, and QGITA"
_COMMAND = (
    "from aureon.evaluation.brain_proof import evaluate_brain, render_brain_markdown; "
    "print(render_brain_markdown(evaluate_brain()))"
)
# Bare figures false-match honest numbers (92.40, 0.629, 6298). These are the
# LIVE_PROOF shapes named in docs/AUREON_RULES.md: 92.4% and 629 trades.
_ANCHORED = (
    re.compile(r"(?<![\d.])92\.4(?![\d.])"),
    re.compile(r"(?<![\d.])629(?![\d.])"),
)


def _quickstart(cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["AUREON_LLM_OFFLINE"] = "1"
    env["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
    env["AUREON_LIVE_TRADING"] = "0"
    env["PYTHONPATH"] = str(cwd)
    return subprocess.run(
        [sys.executable, "-c", _COMMAND],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=170,
        check=False,
    )


def _assert_measurement(proc: subprocess.CompletedProcess[str]) -> None:
    output = proc.stdout + proc.stderr
    assert proc.returncode == 0, output
    first = next((line for line in proc.stdout.splitlines() if line.strip()), "")
    assert first == _HEADING, proc.stdout
    lowered = output.casefold()
    for banned in (
        "95%",
        "kills",
        "accuracy",
        "win rate",
        "sniper",
        "ultimate intelligence",
        "285/285",
        "6/6",
    ):
        assert banned not in lowered, output
    for pattern in _ANCHORED:
        assert pattern.search(output) is None, output
    assert "unified" in output
    assert "0.9331334813083556" in output
    assert "1.409626852655939" in output


@pytest.mark.timeout(180)
def test_quickstart_brain_proof_omits_unbacked_banners() -> None:
    _assert_measurement(_quickstart(ROOT))
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "Aureon-OS"
        cloned = subprocess.run(
            ["git", "clone", "--local", "--quiet", str(ROOT), str(clone)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert cloned.returncode == 0, cloned.stderr
        _assert_measurement(_quickstart(clone))
