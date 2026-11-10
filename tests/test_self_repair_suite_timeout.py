import subprocess

from aureon.autonomous import aureon_sandbox_self_repair as sr


def test_no_fixed_suite_cap_by_default(monkeypatch):
    monkeypatch.delenv("AUREON_SELF_REPAIR_SUITE_TIMEOUT_S", raising=False)
    assert sr._suite_timeout() is None
    monkeypatch.setenv("AUREON_SELF_REPAIR_SUITE_TIMEOUT_S", "5400")
    assert sr._suite_timeout() == 5400.0


def test_suite_timeout_is_a_held_report_not_a_crash(tmp_path, monkeypatch):
    def boom(root):
        raise sr.SuiteTimedOut(7.0)

    monkeypatch.setattr(sr, "_repair_sandbox", boom)
    monkeypatch.setattr(sr, "append_review", lambda *a, **k: None)
    monkeypatch.setattr(sr, "_git", lambda *a, **k: subprocess.CompletedProcess([], 0, "aureon-self-repair/x\n", ""))
    report = sr.repair_sandbox(tmp_path)
    assert report["status"] == "held"
    assert report["reason"] == "suite_timed_out"
    assert report["timeout_s"] == 7.0
    assert report["live_trading"] is False and report["repairs"] == []
