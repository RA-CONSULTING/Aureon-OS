"""The Queen's self-repair counts a fix only when the benchmark gate proves it."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from aureon.autonomous import queen_benchmark_gate as gate
from aureon.autonomous.aureon_sandbox_self_repair import repair_sandbox
from aureon.autonomous.self_repair_guard import ENABLE_ENV, KILL_ENV, review_log_path

REPO = Path(__file__).resolve().parents[1]
MODULE = "def schumann_band_count():\n    return 7\n"
TEST = ("from schumann_band import schumann_band_count\n\n"
        "def test_eight_bands():\n    assert schumann_band_count() == 8\n")


def _sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "schumann_band.py").write_text(MODULE, encoding="utf-8")
    (root / "test_schumann_band.py").write_text(TEST, encoding="utf-8")
    monkeypatch.setenv(ENABLE_ENV, "1")
    monkeypatch.delenv(KILL_ENV, raising=False)
    (root / "state").mkdir()
    (root / "state" / "self_repair_config.json").write_text('{"enabled": true}\n', encoding="utf-8")
    return root


def _commits(root: Path) -> int:
    return int(subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=root, text=True,
                              capture_output=True).stdout.strip() or 0)


def test_verified_repair_commits_fix_with_authored_red_green_test(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    report = repair_sandbox(root)
    assert report["status"] == "repaired"
    g = report["gate"]
    assert g["verified"] is True and g["reasons"] == []
    assert g["paired_red_tests"] == ["test_schumann_band.py::test_eight_bands"]
    assert g["authored_red_green"] == {"red_before": True, "green_after": True}
    authored = report["authored_test"]
    assert authored.startswith("tests/queen_authored/test_qa_")
    body = (root / authored).read_text(encoding="utf-8")
    assert "assert fn(*[]) == 8" in body and "skip" not in body
    tracked = subprocess.run(["git", "ls-files"], cwd=root, text=True, capture_output=True).stdout
    assert authored in tracked
    assert g["seed_benchmarks"]["present"] is False  # toy root has no tests/queen_benchmarks
    log = review_log_path(root).read_text(encoding="utf-8")
    assert '"verified": true' in log


def test_seed_benchmark_failure_makes_fix_unverified_and_reverts(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    monkeypatch.setattr(gate, "run_seed_benchmarks", lambda r: {"present": True, "ok": False})
    report = repair_sandbox(root)
    assert report["status"] == "unverified"
    assert "seed_benchmarks_failed" in report["reason"]
    assert "return 7" in (root / "schumann_band.py").read_text(encoding="utf-8")
    assert _commits(root) == 1  # only the sandbox baseline; nothing committed
    assert not list((root / "tests").glob("queen_authored/*.py")) if (root / "tests").exists() else True
    assert "repair_unverified" in review_log_path(root).read_text(encoding="utf-8")


def test_authored_test_that_was_not_red_first_is_not_a_full_proof(tmp_path, monkeypatch):
    # The authored regression test did not go red-before/green-after, so the fix cannot earn the
    # full "proven" stamp. But it still turned an originally-red test green with no regression and
    # a holding gate, so it lands as partial progress (owner's call, 11:54) -- the bogus authored
    # test is dropped, only the real source fix is committed.
    root = _sandbox(tmp_path, monkeypatch)
    monkeypatch.setattr(gate, "red_then_green", lambda *a, **k: {"red_before": False, "green_after": True})
    report = repair_sandbox(root)
    assert report["status"] == "repaired_partial", report
    assert report["reason"] == "partial_progress"
    assert _commits(root) == 2  # initial sandbox commit + the partial fix


def test_weakened_test_blocks_the_fix(tmp_path, monkeypatch):
    root = _sandbox(tmp_path, monkeypatch)
    real = gate.census_tests
    calls = {"n": 0}

    def shrinking(r):
        calls["n"] += 1
        census = real(r)
        if calls["n"] > 1:
            census["test_schumann_band.py"]["asserts"] = 0
        return census

    monkeypatch.setattr(gate, "census_tests", shrinking)
    report = repair_sandbox(root)
    assert report["status"] == "unverified"
    assert "test_weakened" in report["reason"]


def test_no_red_test_before_fix_is_unverified(tmp_path):
    verdict = gate.verify_repair(tmp_path, census_before={}, red_before=set(), repairs=[], architect=None)
    assert verdict["verified"] is False
    assert "no_red_test_before_fix" in verdict["reasons"]


def test_census_and_weakening_rules(tmp_path):
    (tmp_path / "test_a.py").write_text(
        "import pytest\n\ndef test_x():\n    assert 1 == 1\n    assert 2 == 2\n", encoding="utf-8")
    before = gate.census_tests(tmp_path)
    assert before["test_a.py"] == {"tests": 1, "asserts": 2, "skips": 0}
    (tmp_path / "test_a.py").write_text(
        "import pytest\n\n@pytest.mark.skip\ndef test_x():\n    assert 1 == 1\n", encoding="utf-8")
    reasons = gate.weakened(before, gate.census_tests(tmp_path))
    assert any("asserts 2 -> 1" in r for r in reasons) and any("skips 0 -> 1" in r for r in reasons)
    assert gate.weakened(before, {}) == ["test_a.py: test file removed"]
    assert gate.weakened({}, {"tests/new_test.py": {"tests": 1, "asserts": 1, "skips": 1}})
    assert gate.weakened(before, before) == []


def _toy_pricing_root(tmp_path: Path, monkeypatch, assertion: str) -> Path:
    root = tmp_path / "toy"
    seed = root / "tests" / "queen_benchmarks"
    seed.mkdir(parents=True)
    (root / "toy_price.py").write_text("def notional(price, qty):\n    return price * qty\n", encoding="utf-8")
    (seed / "conftest.py").write_text((REPO / gate.SEED_DIR / "conftest.py").read_text(encoding="utf-8"),
                                      encoding="utf-8")
    (seed / "test_queen_bench_pricing.py").write_text(
        f"import toy_price\n\ndef test_notional():\n    {assertion}\n", encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", f"{root}:{REPO}")
    monkeypatch.syspath_prepend(str(root))
    return root


def test_mutation_check_catches_an_operator_flip(tmp_path, monkeypatch):
    root = _toy_pricing_root(tmp_path, monkeypatch, "assert toy_price.notional(2.0, 3.0) == 6.0")
    result = gate.mutation_check(root, targets=(("toy_price", "notional"),), workers=1)
    assert result["ran"] is True
    assert result["mutants"] == 1 and result["killed"] == 1
    assert result["blind"] is False and result["blind_targets"] == []
    assert result["unreadable_targets"] == []


def test_mutation_check_reports_a_blind_test_set(tmp_path, monkeypatch):
    root = _toy_pricing_root(tmp_path, monkeypatch, "assert toy_price.notional(2.0, 3.0) is not None")
    result = gate.mutation_check(root, targets=(("toy_price", "notional"),), workers=1)
    assert result["killed"] == 0 and result["blind"] is True
    assert result["blind_targets"] == ["notional"]


def test_silent_wrong_check_relays_and_logs(tmp_path, monkeypatch):
    seen = []
    import aureon.core.aureon_baton_link as baton

    monkeypatch.setattr(baton, "relay_state", lambda *a, **k: seen.append(a))
    monkeypatch.setattr(gate, "drift_check", lambda r: {"drift": [{"benchmark": "b", "field": "f",
                                                                    "recorded": 1, "current": 0}],
                                                        "drift_count": 1, "held": []})
    report = gate.silent_wrong_check(tmp_path, mutation=False)
    assert report["summary"]["drift_count"] == 1
    assert seen and seen[0][0] == "queen.self_repair" and seen[0][1] == "seeing"
    assert seen[0][2]["silent_wrong"]["drift_fields"] == ["b:f"]
    line = json.loads(review_log_path(tmp_path).read_text(encoding="utf-8").splitlines()[-1])
    assert line["event"] == "silent_wrong_check" and line["drift_count"] == 1


def test_red_then_green_restores_crlf_bytes_exactly(tmp_path):
    root = tmp_path / "crlf"
    root.mkdir()
    (root / "m.py").write_bytes(b"def f():\r\n    return 7\r\n")
    (root / "test_m.py").write_text("from m import f\n\ndef test_f():\n    assert f() == 8\n", encoding="utf-8")
    for args in (["init"], ["add", "-A"], ["-c", "user.email=a@b", "-c", "user.name=a", "commit", "-m", "base"]):
        subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)
    fixed = b"def f():\r\n    return 8\r\n"
    (root / "m.py").write_bytes(fixed)
    assert gate.red_then_green(root, "test_m.py", ["m.py"]) == {"red_before": True, "green_after": True}
    assert (root / "m.py").read_bytes() == fixed
