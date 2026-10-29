"""The README quickstart measurement must not lead with unbacked banners."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_COMMAND = (
    "from aureon.evaluation.brain_proof import evaluate_brain, render_brain_markdown; "
    "print(render_brain_markdown(evaluate_brain()))"
)


@pytest.mark.timeout(180)
def test_quickstart_brain_proof_omits_unbacked_banners() -> None:
    env = os.environ.copy()
    env["AUREON_LLM_OFFLINE"] = "1"
    env["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
    env["AUREON_LIVE_TRADING"] = "0"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT), *[part for part in env.get("PYTHONPATH", "").split(os.pathsep) if part]]
    )
    proc = subprocess.run(
        [sys.executable, "-c", _COMMAND],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=170,
        check=False,
    )
    output = proc.stdout + proc.stderr
    assert proc.returncode == 0, output
    lowered = output.casefold()
    for banned in (
        "95%",
        "kills",
        "accuracy",
        "win rate",
        "sniper",
        "ultimate intelligence",
        "285/285",
        "92.4",
        "629",
        "6/6",
    ):
        assert banned not in lowered, output
    assert "unified" in output
    assert "0.9331334813083556" in output
    assert "1.409626852655939" in output
