from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "launchers" / "AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1"


def test_production_launcher_runs_full_release_gate_before_validate_or_start() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")

    gate = source.index("-m aureon.autonomous.aureon_full_live_release")
    validate_exit = source.index("if ($ValidateOnly)")
    process_start = source.index("$started += Start-AureonProcess", validate_exit)

    assert "if ($LiveTrading -or $ProductionMode)" in source
    assert gate < validate_exit < process_start
    assert "$fullLiveReleaseExit -ne 0" in source
    assert "No Aureon process or exchange mutation was started" in source


def test_launcher_has_no_release_gate_bypass_switch() -> None:
    source = LAUNCHER.read_text(encoding="utf-8").lower()

    assert "skipfulllive" not in source
    assert "skipreleasegate" not in source
    assert "bypassrelease" not in source
