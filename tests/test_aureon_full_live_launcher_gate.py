from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "launchers" / "AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1"
PRODUCTION_WRAPPER = ROOT / "scripts" / "launchers" / "start_everything_production.ps1"


def test_production_launcher_runs_full_release_gate_before_validate_or_start() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")

    gate = source.index("-m aureon.autonomous.aureon_full_live_release")
    validate_exit = source.index("if ($ValidateOnly)")
    authority = source.index("\nAssert-ProductionSupervisorStartAuthority", validate_exit)
    supervisor_lock = source.index("\nAssert-SingleProductionSupervisor", authority)
    process_start = source.index("$started += Start-AureonProcess", authority)

    assert "if ($LiveTrading -or $ProductionMode)" in source
    assert gate < validate_exit < authority < supervisor_lock < process_start
    assert "$fullLiveReleaseExit -ne 0" in source
    assert "No Aureon process or exchange mutation was started" in source


def test_live_start_authority_is_deny_only_and_does_not_consult_release_exit() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")
    start = source.index("function Assert-ProductionSupervisorStartAuthority")
    end = source.index("function Assert-SingleProductionSupervisor", start)
    body = source[start:end]

    assert "if (-not ($LiveTrading -or $ProductionMode)) { return }" in body
    assert "throw \"Production/live process-start authority HOLD:" in body
    assert "$fullLiveReleaseExit" not in body
    assert "production supervisor authority type is required" in body.lower()
    assert "return $true" not in body.lower()


def test_every_current_runtime_start_occurs_after_authority_assertion() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")
    validate_exit = source.index("if ($ValidateOnly)")
    authority = source.index("\nAssert-ProductionSupervisorStartAuthority", validate_exit)
    gap = source[validate_exit:authority]
    start_call = re.compile(
        r"(?m)^\s*(?:\$[A-Za-z0-9_]+\s*(?:\+=|=)\s*)?"
        r"(?:Start-Process|Start-AureonProcess(?:WithoutStopping)?|Invoke-NativeLogged|"
        r"Restart-Aureon(?:MarketStatusServerOnly|Surface)|"
        r"Start-AureonMarketTelemetryWriterOnly|Ensure-BackgroundProcess|Invoke-Refresh)\b"
    )
    assert start_call.search(gap) is None

    runtime_needles = (
        "$npmExit = Invoke-NativeLogged",
        "$started += Start-AureonProcessWithoutStopping",
        "$started += Start-AureonProcess",
        "Restart-AureonMarketStatusServerOnly",
        "$started += Start-AureonMarketTelemetryWriterOnly",
        "Invoke-Refresh -Python",
        'Start-Process "http://127.0.0.1:$FrontendPort/"',
        'Restart-AureonSurface -Surface "frontend"',
        'Restart-AureonSurface -Surface "market"',
        'Restart-AureonSurface -Surface "mind"',
        "Ensure-BackgroundProcess `",
    )
    for needle in runtime_needles:
        assert source.index(needle, authority) > authority


def test_direct_start_process_primitives_are_ratcheted() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")
    helper_primitives = re.findall(r"(?m)^\s*\$proc = Start-Process `\s*$", source)
    browser_primitives = re.findall(
        r'(?m)^\s*Start-Process "http://127\.0\.0\.1:\$FrontendPort/"\s*$',
        source,
    )

    assert len(helper_primitives) == 3
    assert len(browser_primitives) == 1


def test_launcher_has_no_release_gate_bypass_switch() -> None:
    source = LAUNCHER.read_text(encoding="utf-8").lower()

    assert "skipfulllive" not in source
    assert "skipreleasegate" not in source
    assert "bypassrelease" not in source


def test_production_wrapper_has_no_process_start_path_after_terminal_hold() -> None:
    source = PRODUCTION_WRAPPER.read_text(encoding="utf-8")
    what_if = source.index("if ($WhatIf)")
    what_if_exit = source.index("exit 0", what_if)
    what_if_close = source.index("\n}", what_if_exit)
    hold_statement = (
        'throw "Production wrapper process-start authority HOLD: no independent '
        "production supervisor authority type is available. WhatIf remains "
        'available without starting processes."'
    )
    hold_match = re.search(rf"(?m)^{re.escape(hold_statement)}$", source)
    assert hold_match is not None
    authority_hold = hold_match.start()
    process_starts = [
        match.start()
        for match in re.finditer(r"(?m)^\s*Start-Process\b", source)
    ]

    assert what_if < what_if_exit < what_if_close < authority_hold
    assert all(
        not line.strip() or line.lstrip().startswith("#")
        for line in source[what_if_close + 2 : authority_hold].splitlines()
    )
    assert process_starts == []
    assert "WhatIf remains available without starting processes" in source
    assert "live trading armed" not in source.lower()
    assert "AUREON PRODUCTION VALIDATION WRAPPER - HOLD" in source
