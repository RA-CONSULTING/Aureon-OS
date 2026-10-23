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


def test_live_flags_allow_real_orders_without_contacting_an_exchange() -> None:
    hostile = {
        "AUREON_AUDIT_MODE": "0",
        "AUREON_LIVE_TRADING": "1",
        "AUREON_DISABLE_REAL_ORDERS": "0",
        "AUREON_DISABLE_EXCHANGE_MUTATIONS": "0",
        "DRY_RUN": "0",
        "LIVE": "1",
        "CONFIRM_LIVE": "yes",
    }

    assert real_orders_allowed(hostile) is True
    assert live_block_reason("test", hostile) is None
    require_real_orders_allowed("test", hostile)
    child = child_env_for_mode(True, hostile)
    assert child["AUREON_LIVE_TRADING"] == "1"
    assert child["AUREON_DRY_RUN"] == "0"
    assert child["AUREON_DISABLE_REAL_ORDERS"] == "0"

    paper = {"AUREON_LIVE_TRADING": "0", "AUREON_DISABLE_REAL_ORDERS": "0"}
    assert real_orders_allowed(paper) is False
    assert "paper/public-data" in (live_block_reason("test", paper) or "")


def test_requested_live_profile_arms_without_placing_an_order() -> None:
    environment: dict[str, str] = {}
    result = apply_live_runtime_environment(environment)

    assert result is environment
    assert environment["AUREON_RELEASE_STATE"] == "RELEASE"
    assert environment["AUREON_AUDIT_MODE"] == "0"
    assert environment["AUREON_LIVE_TRADING"] == "1"
    assert environment["AUREON_DISABLE_REAL_ORDERS"] == "0"
    assert environment["AUREON_DISABLE_EXCHANGE_MUTATIONS"] == "0"
    assert environment["AUREON_DRY_RUN"] == "0"
    assert environment["DRY_RUN"] == "0"
    assert environment["LIVE"] == "1"
    assert environment["CONFIRM_LIVE"] == "yes"
    assert environment["AUREON_UNIFIED_ORDER_EXECUTOR"] == "1"
    assert real_orders_allowed(environment) is True


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
