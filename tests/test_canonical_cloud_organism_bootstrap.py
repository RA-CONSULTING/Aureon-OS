from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "relative_path",
    (
        "scripts/operations/run_canonical_cloud_organism.py",
        "scripts/operations/run_live_druidic_calibration.py",
    ),
)
def test_canonical_operation_routes_are_non_mutating_hold(
    relative_path: str,
    tmp_path: Path,
) -> None:
    script = ROOT / relative_path
    before = tuple(tmp_path.iterdir())
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(script), "--activate"],
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
    assert receipt["network_accessed"] is False
    assert receipt["file_written"] is False
    assert tuple(tmp_path.iterdir()) == before

    source = script.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "argparse",
        "subprocess",
        "requests",
        "socket",
        "dotenv",
        "from aureon",
        "import aureon",
        "sys.path",
        "write_text",
        "os.replace",
    ):
        assert forbidden not in source
