"""Protected patches are refused before git apply, including under auto-approve."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from aureon.autonomous.aureon_internal_self_coder import _apply_approved_patch
from aureon.autonomous.self_repair_guard import block_reason_for_patch, review_log_path


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "self-repair@localhost")
    _git(root, "config", "user.name", "Aureon self-repair")
    (root / "offset.py").write_text("def band_offset():\n    return 1\n", encoding="utf-8")
    (root / "gate.py").write_text('def evidence_gate():\n    return "HOLD"\n', encoding="utf-8")
    (root / "size.py").write_text("def position_qty(price):\n    return 0\n", encoding="utf-8")
    _git(root, "add", "offset.py", "gate.py", "size.py")
    _git(root, "commit", "-m", "base")
    return root


def test_auto_approve_cannot_apply_a_protected_patch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUREON_CODE_AUTO_APPROVE", "1")
    root = _repo(tmp_path)
    gate_before = (root / "gate.py").read_text(encoding="utf-8")
    size_before = (root / "size.py").read_text(encoding="utf-8")
    cases = [
        (
            "arm.py",
            "diff --git a/arm.py b/arm.py\nnew file mode 100644\n--- /dev/null\n+++ b/arm.py\n@@ -0,0 +1 @@\n+AUREON_LIVE_TRADING=1\n",
            "live_trading_flag",
        ),
        (
            ".env",
            "diff --git a/.env b/.env\nnew file mode 100644\n--- /dev/null\n+++ b/.env\n@@ -0,0 +1 @@\n+BINANCE_API_SECRET=super-secret-value\n",
            "credential_path",
        ),
        (
            "gate.py",
            "diff --git a/gate.py b/gate.py\n--- a/gate.py\n+++ b/gate.py\n@@ -1,2 +1,2 @@\n def evidence_gate():\n-    return \"HOLD\"\n+    return \"RELEASE\"\n",
            "evidence_gate",
        ),
        (
            "size.py",
            "diff --git a/size.py b/size.py\n--- a/size.py\n+++ b/size.py\n@@ -1,2 +1,2 @@\n def position_qty(price):\n-    return 0\n+    return 1\n",
            "position_sizing",
        ),
    ]
    for target, patch, reason in cases:
        result = _apply_approved_patch(root, target, patch, [])
        assert result["ok"] is False
        assert result["applied"] is False
        assert result["human_review"] is True
        assert result["reason"] == reason
        assert result["stage"] == "protected_denylist"
        assert os.environ["AUREON_CODE_AUTO_APPROVE"] == "1"
    assert not (root / "arm.py").exists()
    assert not (root / ".env").exists()
    assert (root / "gate.py").read_text(encoding="utf-8") == gate_before
    assert (root / "size.py").read_text(encoding="utf-8") == size_before
    log = review_log_path(root).read_text(encoding="utf-8")
    assert "human_review_required" in log
    assert "super-secret-value" not in log
    assert block_reason_for_patch(root, cases[2][1], ["gate.py"]) == "evidence_gate"


def test_a_harmless_utility_patch_still_applies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUREON_CODE_AUTO_APPROVE", "1")
    root = _repo(tmp_path)
    patch = (
        "diff --git a/offset.py b/offset.py\n"
        "--- a/offset.py\n"
        "+++ b/offset.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def band_offset():\n"
        "-    return 1\n"
        "+    return 0\n"
    )
    result = _apply_approved_patch(root, "offset.py", patch, [])
    assert result["ok"] is True, result
    assert result["git_apply_ok"] is True
    assert "return 0" in (root / "offset.py").read_text(encoding="utf-8")
