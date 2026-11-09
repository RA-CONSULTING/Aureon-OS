"""Snag 55: guarded self-repair cannot write live-arming settings.

The crafted inputs are the ones the gate table marked ALLOW. Every entry
point that can land those bytes must refuse them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aureon.autonomous.self_repair_guard import (
    SelfRepairBlocked,
    block_reason_for_patch,
    block_reason_for_proposal,
    block_reason_for_write,
    inspect_execution,
    inspect_write,
)

# Exact crafted inputs from the gate table.
CRAFTED = (
    "{'testnet': False}",
    "{'paper_mode': False}",
    "dry_run = False",
    "'AUREON_'+'LIVE'+'_TRADING'",
    "go_live_clear = True",
)


def _patch(fragment: str) -> str:
    return (
        "diff --git a/utils.py b/utils.py\n"
        "--- a/utils.py\n"
        "+++ b/utils.py\n"
        "@@ -1 +1,2 @@\n"
        " def band_offset():\n"
        f"+    {fragment}\n"
        "     return 0\n"
    )


@pytest.fixture
def guarded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUREON_AUTONOMY_MODE", "guarded")


@pytest.mark.parametrize("crafted", CRAFTED)
def test_snag55_refuses_crafted_live_settings_on_every_write_path(
    tmp_path: Path, guarded: None, crafted: str
) -> None:
    reason = block_reason_for_write("utils.py", crafted, "return 0\n", tmp_path)
    assert reason == "live_trading_flag", crafted
    assert block_reason_for_patch(tmp_path, _patch(crafted), ["utils.py"]) == "live_trading_flag"
    assert block_reason_for_proposal(crafted, repo_root=tmp_path) == "live_trading_flag"
    with pytest.raises(SelfRepairBlocked) as execution:
        inspect_execution(crafted, tmp_path)
    assert execution.value.reason == "live_trading_flag"
    with pytest.raises(SelfRepairBlocked) as write:
        inspect_write(tmp_path, "utils.py", crafted, "return 0\n")
    assert write.value.reason == "live_trading_flag"
    assert not (tmp_path / "utils.py").exists()


def test_snag55_still_allows_a_benign_off_by_one(tmp_path: Path, guarded: None) -> None:
    benign = "def band_offset():\n    return 0\n"
    assert block_reason_for_write("utils.py", benign, "def band_offset():\n    return 1\n", tmp_path) is None
    resolved = inspect_write(tmp_path, "utils.py", benign, None)
    assert resolved == (tmp_path / "utils.py").resolve()


def test_snag55_direct_repo_fallback_cannot_write_go_live_clear(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUREON_AUTONOMY_MODE", "guarded")
    from aureon.autonomous.aureon_repo_self_repair import _write_guarded

    with pytest.raises(RuntimeError, match="live_trading_flag"):
        _write_guarded(tmp_path, "utils.py", "go_live_clear = True\n")
    assert not (tmp_path / "utils.py").exists()
