"""Self-repair fixes a proved utility bug and refuses protected writes."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from aureon.autonomous.aureon_sandbox_self_repair import load_architect, repair_sandbox
from aureon.autonomous.self_repair_guard import ENABLE_ENV, KILL_ENV, review_log_path

MODULE = """\
def schumann_band_count():
    return 7
"""

TEST = """\
from schumann_band import schumann_band_count

def test_eight_bands():
    assert schumann_band_count() == 8
"""

PASSING_MODULE = """\
def schumann_band_count():
    return 8
"""

WRONG_TEST = """\
from schumann_band import schumann_band_count

def test_eight_bands():
    assert schumann_band_count() == 9
"""


def _sandbox(tmp_path: Path, module: str, test: str) -> Path:
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "schumann_band.py").write_text(module, encoding="utf-8")
    (root / "test_schumann_band.py").write_text(test, encoding="utf-8")
    return root


def _enable(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENABLE_ENV, "1")
    monkeypatch.delenv(KILL_ENV, raising=False)
    config = root / "state" / "self_repair_config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('{"enabled": true}\n', encoding="utf-8")


def test_repairs_a_wrong_return_on_a_review_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _sandbox(tmp_path, MODULE, TEST)
    _enable(root, monkeypatch)
    report = repair_sandbox(root)
    assert report["status"] == "repaired"
    assert report["live_trading"] is False
    assert report["may_act"] is False
    assert report["edited_test"] is False
    assert report["previous_return"] == 7
    assert report["repaired_return"] == 8
    assert "return 8" in (root / "schumann_band.py").read_text(encoding="utf-8")
    assert "assert schumann_band_count() == 8" in (root / "test_schumann_band.py").read_text(encoding="utf-8")
    assert report["commit"]
    assert str(report["branch"]).startswith("aureon-self-repair/")
    log = review_log_path(root).read_text(encoding="utf-8")
    assert "repair_committed" in log
    assert "tests_passed" in log


def test_repairs_the_implementation_and_leaves_the_test_file_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _sandbox(tmp_path, PASSING_MODULE, WRONG_TEST)
    _enable(root, monkeypatch)
    original_test = (root / "test_schumann_band.py").read_text(encoding="utf-8")
    report = repair_sandbox(root)
    assert report["status"] == "repaired"
    assert report["edited_test"] is False
    assert (root / "test_schumann_band.py").read_text(encoding="utf-8") == original_test
    assert "return 9" in (root / "schumann_band.py").read_text(encoding="utf-8")


def test_repairs_an_operator_and_a_name_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "app"
    root.mkdir()
    (root / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (root / "scale.py").write_text("def double(n):\n    return nn * 2\n", encoding="utf-8")
    (root / "test_app.py").write_text(
        "from calc import add\nfrom scale import double\n\n"
        "def test_add():\n    assert add(2, 3) == 5\n\n"
        "def test_double():\n    assert double(4) == 8\n",
        encoding="utf-8",
    )
    original_test = (root / "test_app.py").read_text(encoding="utf-8")
    _enable(root, monkeypatch)
    report = repair_sandbox(root)
    assert report["status"] == "repaired", report
    assert report["edited_test"] is False
    assert (root / "test_app.py").read_text(encoding="utf-8") == original_test
    assert "return a + b" in (root / "calc.py").read_text(encoding="utf-8")
    assert "return n * 2" in (root / "scale.py").read_text(encoding="utf-8")
    assert report["commit"]


def test_kill_switch_blocks_the_repair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _sandbox(tmp_path, MODULE, TEST)
    _enable(root, monkeypatch)
    monkeypatch.setenv(KILL_ENV, "1")
    report = repair_sandbox(root)
    assert report["status"] == "held"
    assert report["reason"] == "kill_switch"
    assert "return 7" in (root / "schumann_band.py").read_text(encoding="utf-8")


def test_missing_config_and_missing_enable_stop_the_repair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(KILL_ENV, raising=False)
    monkeypatch.setenv(ENABLE_ENV, "1")
    root = _sandbox(tmp_path, MODULE, TEST)
    report = repair_sandbox(root)
    assert report["status"] == "held"
    assert report["reason"] == "missing_config"
    assert "return 7" in (root / "schumann_band.py").read_text(encoding="utf-8")

    config = root / "state" / "self_repair_config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('{"enabled": true}\n', encoding="utf-8")
    monkeypatch.delenv(ENABLE_ENV, raising=False)
    report = repair_sandbox(root)
    assert report["status"] == "held"
    assert report["reason"] == "self_repair_disabled"
    assert "return 7" in (root / "schumann_band.py").read_text(encoding="utf-8")


def test_repairs_an_off_by_one_in_a_pure_utility(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "utilbox"
    root.mkdir()
    (root / "offset.py").write_text("def band_offset():\n    return 1\n", encoding="utf-8")
    (root / "test_offset.py").write_text(
        "from offset import band_offset\n\ndef test_zero_based():\n    assert band_offset() == 0\n",
        encoding="utf-8",
    )
    _enable(root, monkeypatch)
    report = repair_sandbox(root)
    assert report["status"] == "repaired", report
    assert report.get("human_review") is not True
    assert "return 0" in (root / "offset.py").read_text(encoding="utf-8")
    assert "assert band_offset() == 0" in (root / "test_offset.py").read_text(encoding="utf-8")


def test_queen_writer_refuses_live_flags_gates_and_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(KILL_ENV, raising=False)
    monkeypatch.delenv(ENABLE_ENV, raising=False)
    architect = load_architect()(repo_path=str(tmp_path))
    canary = "super-secret-value"
    assert architect.write_file(".env", f"BINANCE_API_SECRET={canary}\n") is False
    assert not (tmp_path / ".env").exists()
    assert architect.write_file("credentials.json", f'{{"api_secret": "{canary}"}}\n') is False
    assert not (tmp_path / "credentials.json").exists()
    assert architect.write_file("arm.py", "AUREON_LIVE_TRADING=1\n") is False
    assert not (tmp_path / "arm.py").exists()
    assert architect.write_file("confirm.py", "CONFIRM_LIVE_TRADING=yes\n") is False
    assert architect.write_file("paper.py", "testnet: false\n") is False
    assert architect.write_file("gate.py", 'may_act = True\ngate = "RELEASE"\n') is False
    assert not (tmp_path / "gate.py").exists()
    (tmp_path / "held.py").write_text('def evidence_gate():\n    return "HOLD"\n', encoding="utf-8")
    assert architect.apply_edit("held.py", 'return "HOLD"', 'return "RELEASE"') is False
    assert 'return "HOLD"' in (tmp_path / "held.py").read_text(encoding="utf-8")
    (tmp_path / "size.py").write_text("def position_qty(price):\n    return 0\n", encoding="utf-8")
    assert architect.apply_edit("size.py", "return 0", "return 1") is False
    assert "return 0" in (tmp_path / "size.py").read_text(encoding="utf-8")
    (tmp_path / ".env").write_text("KEEP=1\n", encoding="utf-8")
    assert architect.append_to_file(".env", f"BINANCE_API_SECRET={canary}\n") is False
    assert canary not in (tmp_path / ".env").read_text(encoding="utf-8")
    assert architect.delete_file(".env") is False
    assert (tmp_path / ".env").exists()
    log = review_log_path(tmp_path).read_text(encoding="utf-8")
    assert "credential_path" in log
    assert "live_trading_flag" in log
    assert "evidence_gate" in log
    assert "position_sizing" in log
    assert "human_review" in log
    assert canary not in log
    monkeypatch.setenv(KILL_ENV, "1")
    assert architect.write_file("notes.py", "print('hello')\n") is False
    assert not (tmp_path / "notes.py").exists()


def test_gate_flip_and_position_size_are_flagged_not_applied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "desk"
    root.mkdir()
    original = 'def position_qty(price):\n    return 0\n\ndef evidence_gate():\n    return "HOLD"\n'
    (root / "desk.py").write_text(original, encoding="utf-8")
    (root / "test_desk.py").write_text(
        "from desk import evidence_gate, position_qty\n\n"
        "def test_size():\n    assert position_qty(100) == 1\n\n"
        "def test_gate():\n    assert evidence_gate() == \"RELEASE\"\n",
        encoding="utf-8",
    )
    _enable(root, monkeypatch)
    report = repair_sandbox(root)
    assert report["status"] == "human_review", report
    assert report["human_review"] is True
    assert report["reason"] in {"position_sizing", "evidence_gate"}
    assert (root / "desk.py").read_text(encoding="utf-8") == original
    log = review_log_path(root).read_text(encoding="utf-8")
    assert "human_review_required" in log


def test_review_log_is_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _sandbox(tmp_path, MODULE, TEST)
    _enable(root, monkeypatch)
    repair_sandbox(root)
    for line in review_log_path(root).read_text(encoding="utf-8").splitlines():
        json.loads(line)
    assert os.environ.get("AUREON_LIVE_TRADING", "0") != "1"
