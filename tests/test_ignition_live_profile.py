from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aureon.core.aureon_runtime_safety import (
    apply_live_runtime_environment,
    child_env_for_mode,
    live_block_reason,
    real_orders_allowed,
    require_real_orders_allowed,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
IGNITION_PATH = REPO_ROOT / "scripts" / "aureon_ignition.py"


def test_environment_flags_cannot_enable_real_orders() -> None:
    hostile = {
        "AUREON_AUDIT_MODE": "0",
        "AUREON_LIVE_TRADING": "1",
        "AUREON_DISABLE_REAL_ORDERS": "0",
        "AUREON_DISABLE_EXCHANGE_MUTATIONS": "0",
        "DRY_RUN": "0",
        "LIVE": "1",
        "CONFIRM_LIVE": "yes",
    }

    assert real_orders_allowed(hostile) is False
    assert "terminal production release HOLD" in live_block_reason("test", hostile)
    with pytest.raises(RuntimeError, match="terminal production release HOLD"):
        require_real_orders_allowed("test", hostile)
    with pytest.raises(RuntimeError, match="terminal production release HOLD"):
        child_env_for_mode(True, hostile)


def test_requested_live_profile_is_forced_back_to_hold() -> None:
    environment: dict[str, str] = {}
    result = apply_live_runtime_environment(environment)

    assert result is environment
    assert environment["AUREON_RELEASE_STATE"] == "HOLD"
    assert environment["AUREON_AUDIT_MODE"] == "1"
    assert environment["AUREON_LIVE_TRADING"] == "0"
    assert environment["AUREON_DISABLE_REAL_ORDERS"] == "1"
    assert environment["AUREON_DISABLE_EXCHANGE_MUTATIONS"] == "1"
    assert environment["AUREON_DRY_RUN"] == "1"
    assert environment["DRY_RUN"] == "1"
    assert environment["LIVE"] == "0"
    assert environment["CONFIRM_LIVE"] == "no"
    assert environment["AUREON_UNIFIED_ORDER_EXECUTOR"] == "0"
    assert real_orders_allowed(environment) is False


def test_direct_ignition_is_a_non_mutating_hold(tmp_path: Path) -> None:
    before = tuple(tmp_path.iterdir())
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(IGNITION_PATH), "--live"],
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
    assert receipt["systems_booted"] is False
    assert receipt["order_submitted"] is False
    assert receipt["network_accessed"] is False
    assert receipt["file_written"] is False
    assert tuple(tmp_path.iterdir()) == before


def test_ignition_source_has_no_runtime_or_credential_imports() -> None:
    source = IGNITION_PATH.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "subprocess",
        "requests",
        "socket",
        "dotenv",
        "from aureon",
        "import aureon",
        "start-process",
        "popen",
        "while true",
        "dry_run=false",
    ):
        assert forbidden not in source
