"""Model-backed fix step: stubbed coder, the write guard, logging and the bus relay."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from aureon.autonomous import queen_benchmark_gate as gate
from aureon.autonomous import queen_repair_coder as qc
from aureon.autonomous.aureon_sandbox_self_repair import load_architect, repair_sandbox
from aureon.autonomous.self_repair_guard import ENABLE_ENV, KILL_ENV, review_log_path


def _pytest_fn(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider"],
                          cwd=root, text=True, capture_output=True)


def _repo(tmp_path: Path, impl: str) -> Path:
    root = tmp_path / "wt"
    root.mkdir()
    (root / "widget.py").write_text(impl, encoding="utf-8")
    (root / "test_widget.py").write_text(
        "from widget import price\n\ndef test_price():\n    assert price(10) == 20\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
    return root


def _diff(root: Path, rel: str, old: str, new: str) -> str:
    (root / (rel + ".bak")).write_text((root / rel).read_text(), encoding="utf-8")
    (root / rel).write_text((root / rel).read_text().replace(old, new), encoding="utf-8")
    out = subprocess.run(["git", "diff", "--", rel], cwd=root, text=True, capture_output=True).stdout
    (root / rel).write_text((root / (rel + ".bak")).read_text(), encoding="utf-8")
    (root / (rel + ".bak")).unlink()
    return out


def _records(test_id="test_widget.py::test_price", target="widget.py", error="assert 10 == 20"):
    return [{"test_id": test_id, "error": error, "exception": "AssertionError",
             "traceback_tail": [], "suspected_file": target}]


def test_disabled_unless_opted_in(monkeypatch):
    monkeypatch.delenv(qc.CODER_ENV, raising=False)
    assert qc.coder_enabled() is False
    monkeypatch.setenv(qc.CODER_ENV, "1")
    assert qc.coder_enabled() is True


def test_good_diff_commits_logs_and_relays(tmp_path, monkeypatch):
    root = _repo(tmp_path, "def price(n):\n    return n * 1\n")
    diff = _diff(root, "widget.py", "return n * 1", "return n * 2")
    relayed = []
    monkeypatch.setattr(qc, "relay_attempt", lambda s: relayed.append(s))
    delta = qc.attempt_model_fixes(
        root, _records(), gate=gate, architect=load_architect()(repo_path=str(root)),
        pytest_fn=_pytest_fn, census_before=gate.census_tests(root), red_before={"test_widget.py::test_price"},
        branch="b", coder=lambda *a: {"diff": diff})
    assert delta["status"] == "repaired", delta
    assert "return n * 2" in (root / "widget.py").read_text()
    assert delta["commit"]
    rows = [json.loads(l) for l in (root / qc.ATTEMPTS_LOG).read_text().splitlines()]
    assert rows and rows[-1]["outcome"] == "repaired"
    assert any(r["outcome"] == "repaired" for r in relayed)


def test_live_trading_flag_diff_is_refused(tmp_path, monkeypatch):
    root = _repo(tmp_path, "def price(n):\n    return n * 1\n")
    (root / "flags.py").write_text("LIVE_TRADING = False\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "flags"], cwd=root, check=True)
    diff = _diff(root, "flags.py", "LIVE_TRADING = False", "LIVE_TRADING = True")
    delta = qc.attempt_model_fixes(
        root, _records(target="flags.py"), gate=gate, architect=load_architect()(repo_path=str(root)),
        pytest_fn=_pytest_fn, census_before=gate.census_tests(root), red_before={"test_widget.py::test_price"},
        branch="b", coder=lambda *a: {"diff": diff})
    assert delta["status"] == "held"
    rows = [json.loads(l) for l in (root / qc.ATTEMPTS_LOG).read_text().splitlines()]
    assert rows[-1]["outcome"] == "refused" and rows[-1]["reason"] == "live_trading_flag"
    assert "LIVE_TRADING = False" in (root / "flags.py").read_text()


def test_benchmark_seed_and_env_targets_are_refused(tmp_path):
    root = _repo(tmp_path, "def price(n):\n    return n * 1\n")
    for rel in ("tests/queen_benchmarks/test_seed.py", ".env"):
        fake = (f"--- a/{rel}\n+++ b/{rel}\n@@ -0,0 +1 @@\n+x = 1\n")
        assert qc.refuse_reason(root, fake, [rel]) in {"benchmark_seed_protected", "env_file_protected"}


def test_regression_diff_is_reverted(tmp_path, monkeypatch):
    root = _repo(tmp_path, "def price(n):\n    return n * 2\n")
    # Add a second test that passes now; the diff will break it.
    (root / "test_more.py").write_text(
        "from widget import price\n\ndef test_double_keep():\n    assert price(5) == 10\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "more"], cwd=root, check=True)
    diff = _diff(root, "widget.py", "return n * 2", "return n * 3")
    monkeypatch.setattr(qc, "relay_attempt", lambda s: None)
    delta = qc.attempt_model_fixes(
        root, _records(error="assert False"), gate=gate, architect=load_architect()(repo_path=str(root)),
        pytest_fn=_pytest_fn, census_before=gate.census_tests(root),
        red_before=set(),  # nothing was red before; the diff only creates regressions
        branch="b", coder=lambda *a: {"diff": diff})
    # test_id not in red_before -> the witness rule skips it; nothing committed, file unchanged.
    assert delta["status"] == "held"
    assert "return n * 2" in (root / "widget.py").read_text()


def test_skipped_coder_is_logged(tmp_path, monkeypatch):
    root = _repo(tmp_path, "def price(n):\n    return n * 1\n")
    monkeypatch.setattr(qc, "relay_attempt", lambda s: None)
    delta = qc.attempt_model_fixes(
        root, _records(), gate=gate, architect=load_architect()(repo_path=str(root)),
        pytest_fn=_pytest_fn, census_before=gate.census_tests(root), red_before={"test_widget.py::test_price"},
        branch="b", coder=lambda *a: {"skipped": "organ_hold:model_not_pulled"})
    assert delta["status"] == "held"
    rows = [json.loads(l) for l in (root / qc.ATTEMPTS_LOG).read_text().splitlines()]
    assert rows[-1]["outcome"] == "skipped" and "model_not_pulled" in rows[-1]["reason"]


def _enable(root: Path, monkeypatch) -> None:
    monkeypatch.setenv(ENABLE_ENV, "1")
    monkeypatch.delenv(KILL_ENV, raising=False)
    cfg = root / "state" / "self_repair_config.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text('{"enabled": true}\n', encoding="utf-8")


def test_end_to_end_model_fix_through_repair_sandbox(tmp_path, monkeypatch):
    # A failure the rule-based _attempt cannot fix (two-statement body), solved by a stubbed organ diff.
    root = tmp_path / "sbx"
    root.mkdir()
    (root / "calc.py").write_text("def area(w, h):\n    base = w + h\n    return base\n", encoding="utf-8")
    (root / "test_calc.py").write_text(
        "from calc import area\n\ndef test_area():\n    assert area(3, 4) == 12\n", encoding="utf-8")
    _enable(root, monkeypatch)
    monkeypatch.setenv(qc.CODER_ENV, "1")
    monkeypatch.setattr(qc, "relay_attempt", lambda s: None)
    diff_holder = {}

    def stub(root_, record, goal, source):
        # Author the minimal fix: multiply instead of add.
        (root_ / "calc.py.bak").write_text((root_ / "calc.py").read_text(), encoding="utf-8")
        (root_ / "calc.py").write_text("def area(w, h):\n    base = w * h\n    return base\n", encoding="utf-8")
        out = subprocess.run(["git", "diff", "--", "calc.py"], cwd=root_, text=True, capture_output=True).stdout
        (root_ / "calc.py").write_text((root_ / "calc.py.bak").read_text(), encoding="utf-8")
        (root_ / "calc.py.bak").unlink()
        diff_holder["diff"] = out
        return {"diff": out}

    monkeypatch.setattr(qc, "_organ_author", stub)
    report = repair_sandbox(root)
    assert report["status"] == "repaired", report
    assert report["reason"] == "model_fix_gate_verified"
    assert "base = w * h" in (root / "calc.py").read_text()
    log = review_log_path(root).read_text(encoding="utf-8")
    assert "queen_repair_coder" in log


def test_organ_author_generates_hnc_key_then_skips_gracefully(tmp_path):
    # _organ_author loads the HNC master key the repo's own way (generating it locally if absent),
    # then skips gracefully because the local model / truth-authority bundle is not available here.
    root = _repo(tmp_path, "def price(n):\n    return n * 1\n")
    rec = {"test_id": "test_widget.py::test_price", "error": "assert 10 == 20",
           "exception": "AssertionError", "traceback_tail": [], "suspected_file": "widget.py"}
    result = qc._organ_author(root, rec, "fix price", "def price(n):\n    return n * 1\n")
    assert "skipped" in result, result  # no local model / truth bundle on this box
    assert (root / "state" / "hnc_packet_master_key").is_file()
    # The key file must never be world-readable and never contain the env var name alone.
    assert oct((root / "state" / "hnc_packet_master_key").stat().st_mode & 0o777) == "0o600"
