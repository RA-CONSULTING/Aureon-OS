from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "runners" / "run_vault_ui.py"


def test_vault_ui_runner_is_terminal_non_mutating_hold(tmp_path: Path) -> None:
    before = tuple(tmp_path.iterdir())
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(RUNNER), "--lan", "--start-loop"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 2
    receipt = json.loads(result.stdout)
    assert receipt["decision"] == "HOLD"
    assert receipt["production_ready"] is False
    assert receipt["listener_started"] is False
    assert receipt["network_accessed"] is False
    assert receipt["file_written"] is False
    assert tuple(tmp_path.iterdir()) == before


def test_vault_ui_runner_has_no_server_or_runtime_imports() -> None:
    source = RUNNER.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "argparse",
        "socket",
        "subprocess",
        "from aureon",
        "import aureon",
        "uvicorn",
        "flask",
        "0.0.0.0",
        "threading",
    ):
        assert forbidden not in source
