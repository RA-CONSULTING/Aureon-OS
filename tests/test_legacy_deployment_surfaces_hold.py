from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PYTHON_HOLD_SURFACES = (
    ROOT / "run_real_dryrun_tick.py",
    ROOT / "scripts" / "validation" / "benchmark_live_multidaemon.py",
    ROOT / "scripts" / "diagnostics" / "check_system_logs.py",
    ROOT / "scripts" / "python" / "deploy_digital_ocean.py",
    ROOT / "scripts" / "python" / "deployment_verification.py",
    ROOT / "scripts" / "python" / "quick_sniper.py",
    ROOT / "scripts" / "diagnostics" / "check_digitalocean_compat.py",
    ROOT / "scripts" / "reports" / "INTEGRATION_SUMMARY.py",
    ROOT / "scripts" / "reports" / "GO_LIVE.py",
    ROOT / "scripts" / "reports" / "FINAL_INTEGRATION_STATUS.py",
    ROOT / "scripts" / "reports" / "LIVE_NOW.py",
    ROOT / "scripts" / "diagnostics" / "check_live_environment.py",
    ROOT / "scripts" / "runners" / "run_live_trading.py",
    ROOT / "scripts" / "runners" / "run_unified_orca.py",
    ROOT / "cli" / "launcher.py",
    ROOT / "cli" / "setup_wizard.py",
    ROOT / "packaging" / "post_build_smoke_test.py",
    ROOT / "aureon_launcher" / "launcher.py",
    ROOT / "aureon_launcher" / "setup_wizard.py",
    ROOT / "scripts" / "aureon_ignition.py",
    ROOT / "scripts" / "runners" / "run_unified_ecosystem_live.py",
    ROOT / "scripts" / "runners" / "start_live_trading.py",
    ROOT / "scripts" / "runners" / "run_live_imperial.py",
    ROOT / "scripts" / "runners" / "run_unified.py",
    ROOT / "scripts" / "runners" / "start_aureon_unified.py",
    ROOT / "scripts" / "runners" / "start_nexus.py",
    ROOT / "scripts" / "runners" / "run_snowball.py",
    ROOT / "scripts" / "runners" / "run_aureon_windows.py",
    ROOT / "scripts" / "runners" / "run_ecosystem_debug.py",
    ROOT / "scripts" / "runners" / "run_ecosystem_with_logging.py",
    ROOT / "scripts" / "runners" / "run_miner.py",
    ROOT / "scripts" / "operations" / "run_canonical_cloud_organism.py",
    ROOT / "scripts" / "operations" / "run_live_druidic_calibration.py",
    ROOT / "scripts" / "runners" / "run_adaptive_sandbox.py",
    ROOT / "scripts" / "runners" / "run_backtest_cached.py",
    ROOT / "scripts" / "runners" / "run_big_sim.py",
    ROOT / "scripts" / "runners" / "run_billion_sim.py",
    ROOT / "scripts" / "runners" / "run_continuous_accuracy_monitor.py",
    ROOT / "scripts" / "runners" / "run_penny_profit_sim.py",
    ROOT / "scripts" / "runners" / "run_platypus.py",
    ROOT / "scripts" / "runners" / "run_queen_hive_mind.py",
    ROOT / "scripts" / "runners" / "run_real_data_simulation.py",
    ROOT / "scripts" / "runners" / "run_vault_ui.py",
    ROOT / "scripts" / "runners" / "run_wisdom_learning_sim.py",
)

LEGACY_START_TARGETS = {
    "gaia_closed_loop.sh": "autonomous-self-run",
    "mine_live.sh": "mind-hub",
    "restart_bot.sh": "unified-market-trader",
    "run_live.sh": "unified-market-trader",
    "run_micro_forever.sh": "unified-market-trader",
    "run_multi_bot.sh": "unified-market-trader",
    "run_pipeline.sh": "autonomous-self-run",
    "run_probability_generator.sh": "self-questioning",
    "run_safe_2bots.sh": "unified-market-trader",
    "run_specialized_army.sh": "unified-market-trader",
    "run_unified_ecosystem.sh": "unified-market-trader",
    "run_war_ready_kraken.sh": "cloud-orca",
    "start_aureon.sh": "organism",
    "start_command_center.sh": "cloud-command-center",
    "start_fresh_live.sh": "unified-market-trader",
    "start_full_ecosystem.sh": "organism",
    "START_HISTORICAL_LIVE.sh": "unified-market-trader",
    "START_LIVE_TRADING.sh": "unified-market-trader",
    "start_mind_thought_action.sh": "mind-hub",
    "START_ORCA_LIVE.sh": "cloud-orca",
    "start_simulation.sh": "capability-demo",
    "start_unified_master_hub.sh": "master-launcher",
}

WINDOWS_CMD_TARGETS = {
    "scripts/start_trading.bat": "unified-market-trader",
    "scripts/run_miner.bat": "mind-hub",
    "scripts/run_probability_generator.bat": "self-questioning",
    "scripts/runners/ingest_all_global_history.cmd": "data-ocean",
    "scripts/runners/ingest_economic_calendar.cmd": "data-ocean",
    "scripts/runners/ingest_existing_feeds.cmd": "data-ocean",
    "scripts/runners/ingest_fred.cmd": "data-ocean",
    "scripts/runners/ingest_global_memory.cmd": "data-ocean",
    "scripts/runners/ingest_market_history.cmd": "data-ocean",
    "scripts/runners/ingest_queen_knowledge.cmd": "data-ocean",
    "scripts/runners/ingest_yfinance.cmd": "data-ocean",
    "scripts/runners/run_aureon_agent.cmd": "autonomous-self-run",
    "scripts/runners/run_aureon_face.cmd": "local-gui",
    "scripts/runners/run_aureon_local_gui.cmd": "local-gui",
    "scripts/runners/run_aureon_voice_agent.cmd": "local-gui",
    "scripts/runners/run_courseops_21.cmd": "capability-demo",
    "scripts/runners/run_queen_production.cmd": "queen-web-dashboard",
    "scripts/runners/run_sentient_loop.cmd": "autonomous-self-run",
    "scripts/runners/run_unified_live.cmd": "unified-market-trader",
    "scripts/runners/smoke_unified.cmd": "organism",
    "scripts/runners/sync_global_history_db.cmd": "data-ocean",
}

WINDOWS_PS_TARGETS = {
    "scripts/START_WINDOWS.ps1": "organism",
    "scripts/run_scorm_existing_chrome.ps1": "scorm-benchmark",
    "scripts/start_full_ecosystem.ps1": "organism",
    "scripts/start_queen_hive_mind.ps1": "queen-eternal-machine",
    "scripts/runners/run_alpaca_capital_style.ps1": "unified-market-trader",
    "scripts/runners/run_aureon_voice_agent.ps1": "local-gui",
    "scripts/runners/run_capital_margin_only.ps1": "unified-market-trader",
    "scripts/runners/run_capital_monitor.ps1": "unified-market-status",
    "scripts/runners/run_capital_swarm.ps1": "unified-market-trader",
    "scripts/runners/stop_aureon_voice_agent.ps1": "local-gui",
}


@pytest.mark.parametrize("script", PYTHON_HOLD_SURFACES)
def test_legacy_python_deployment_surfaces_are_terminal_hold(
    script: Path,
    tmp_path: Path,
) -> None:
    before = tuple(tmp_path.iterdir())
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 2, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["decision"] == "HOLD"
    assert receipt["production_ready"] is False
    assert tuple(tmp_path.iterdir()) == before

    source = script.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "aiohttp",
        "requests",
        "socket",
        "subprocess",
        "threading",
        "from aureon",
        "import aureon",
        "start_shield",
        "while true",
        "0.0.0.0",
    ):
        assert forbidden not in source


def test_every_python_runner_is_an_allowlisted_terminal_hold() -> None:
    actual = set((ROOT / "scripts" / "runners").glob("*.py"))
    expected = {path for path in PYTHON_HOLD_SURFACES if path.parent.name == "runners"}
    assert actual == expected


@pytest.mark.parametrize(
    ("relative_path", "target_id"),
    (
        ("scripts/shell/deploy/deploy_digitalocean.sh", "cloud-supervisor"),
        ("scripts/shell/deploy/setup_coinapi.sh", "unified-market-status"),
        ("scripts/check_flameborn_integration.sh", "flameborn-runtime"),
        ("scripts/shell/util/capture_test.sh", "capability-demo"),
        ("scripts/shell/util/debug_runner.sh", "unified-market-trader"),
        ("scripts/shell/util/run_diagnostic_with_log.sh", "capability-demo"),
        ("scripts/shell/util/run_test.sh", "unified-market-trader"),
    ),
)
def test_legacy_shell_surfaces_only_exec_fixed_bootstrap(
    relative_path: str,
    target_id: str,
) -> None:
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    active = "\n".join(
        line for line in source.splitlines() if line.strip() and not line.lstrip().startswith("#")
    )

    assert 'PYTHON_EXE="$REPO_ROOT/.venv/bin/python"' in active
    assert 'BOOTSTRAP="$REPO_ROOT/scripts/bootstrap/protected_bootstrap_v05.py"' in active
    assert f"--target-id {target_id}" in active
    assert active.count("exec ") == 1
    for forbidden in (
        "apt-get",
        "curl ",
        "wget ",
        "git clone",
        "pip install",
        "systemctl",
        "crontab",
        "ufw ",
        ".env",
        "api_key",
        "requests",
    ):
        assert forbidden not in active.casefold()


def test_legacy_shell_surfaces_do_not_mutate_when_fixed_runtime_is_absent(
    tmp_path: Path,
) -> None:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is unavailable")

    before = tuple(tmp_path.iterdir())
    for relative_path in (
        "scripts/shell/deploy/deploy_digitalocean.sh",
        "scripts/shell/deploy/setup_coinapi.sh",
        "scripts/check_flameborn_integration.sh",
        "scripts/shell/util/capture_test.sh",
        "scripts/shell/util/debug_runner.sh",
        "scripts/shell/util/run_diagnostic_with_log.sh",
        "scripts/shell/util/run_test.sh",
    ):
        result = subprocess.run(
            [bash, str(ROOT / relative_path)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode in {1, 2}
        assert tuple(tmp_path.iterdir()) == before


def test_every_legacy_shell_start_route_is_a_fixed_bootstrap_hold() -> None:
    start_dir = ROOT / "scripts" / "shell" / "start"
    assert {path.name for path in start_dir.glob("*.sh")} == set(LEGACY_START_TARGETS)

    for name, target_id in LEGACY_START_TARGETS.items():
        source = (start_dir / name).read_text(encoding="utf-8")
        active = "\n".join(
            line
            for line in source.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        assert 'PYTHON_EXE="$REPO_ROOT/.venv/bin/python"' in active
        assert 'BOOTSTRAP="$REPO_ROOT/scripts/bootstrap/protected_bootstrap_v05.py"' in active
        assert f"--target-id {target_id}" in active
        assert active.count("exec ") == 1
        for forbidden in (
            "python -m",
            "python3 ",
            "nohup",
            "screen ",
            "tmux ",
            "curl ",
            "wget ",
            "npm ",
            "docker ",
            "systemctl",
            "binance_use_testnet",
            "dry_run=0",
            "confirm_live",
        ):
            assert forbidden not in active.casefold(), (name, forbidden)


def test_legacy_queen_runner_has_no_restart_or_direct_runtime_route() -> None:
    source = (ROOT / "scripts" / "runners" / "run_queen_production.cmd").read_text(
        encoding="utf-8"
    )
    lowered = source.casefold()

    assert ".venv\\scripts\\python.exe" in lowered
    assert "scripts\\bootstrap\\protected_bootstrap_v05.py" in lowered
    assert "-i -s -b" in lowered
    assert "--target-id queen-web-dashboard" in lowered
    for forbidden in (":loop", "goto ", "timeout ", "aureon_face_app.py", "pythonpath"):
        assert forbidden not in lowered


def test_all_windows_command_wrappers_only_enter_fixed_bootstrap() -> None:
    runner_cmds = {
        str(path.relative_to(ROOT)).replace("\\", "/")
        for path in (ROOT / "scripts" / "runners").glob("*.cmd")
    }
    expected_runner_cmds = {
        path for path in WINDOWS_CMD_TARGETS if path.startswith("scripts/runners/")
    }
    assert runner_cmds == expected_runner_cmds

    for relative_path, target_id in WINDOWS_CMD_TARGETS.items():
        source = (ROOT / relative_path).read_text(encoding="utf-8").casefold()
        assert ".venv\\scripts\\python.exe" in source
        assert "scripts\\bootstrap\\protected_bootstrap_v05.py" in source
        assert "-i -s -b" in source
        assert f"--target-id {target_id}" in source
        for forbidden in (
            ":loop",
            "goto ",
            "timeout ",
            "start ",
            "pythonpath",
            "live=1",
            "dry_run=0",
            "confirm_live",
        ):
            assert forbidden not in source, (relative_path, forbidden)


def test_all_windows_powershell_wrappers_only_enter_fixed_bootstrap() -> None:
    runner_scripts = {
        str(path.relative_to(ROOT)).replace("\\", "/")
        for path in (ROOT / "scripts" / "runners").glob("*.ps1")
    }
    expected_runner_scripts = {
        path for path in WINDOWS_PS_TARGETS if path.startswith("scripts/runners/")
    }
    assert runner_scripts == expected_runner_scripts

    for relative_path, target_id in WINDOWS_PS_TARGETS.items():
        source = (ROOT / relative_path).read_text(encoding="utf-8").casefold()
        assert ".venv\\scripts\\python.exe" in source
        assert "scripts\\bootstrap\\protected_bootstrap_v05.py" in source
        assert "-i -s -b" in source
        assert f"--target-id {target_id}" in source
        for forbidden in (
            "start-process",
            "invoke-expression",
            "invoke-webrequest",
            "while (",
            "live=1",
            "dry_run=0",
            "confirm_live",
            "auto_approve",
        ):
            assert forbidden not in source, (relative_path, forbidden)


def test_deployment_environment_template_is_hold_only_and_has_no_credentials() -> None:
    source = (ROOT / "deploy" / "env.example").read_text(encoding="utf-8")
    values = dict(
        line.split("=", 1)
        for line in source.splitlines()
        if line and not line.startswith("#") and "=" in line
    )

    assert values["AUREON_RELEASE_STATE"] == "HOLD"
    assert values["AUREON_PRODUCTION_READY"] == "0"
    assert values["AUREON_EXECUTION_ENABLED"] == "0"
    assert values["AUREON_DRY_RUN"] == "1"
    assert values["DRY_RUN"] == "1"
    assert values["PAPER_TRADING"] == "true"
    assert values["CAPITAL_DEMO"] == "1"
    assert all(values[name] == "0" for name in values if name.startswith("ENABLE_"))
    assert not any("KEY" in name or "SECRET" in name or "PASSWORD" in name for name in values)


def test_gamma_sync_requires_runtime_credential_without_embedded_fallback() -> None:
    source = (ROOT / "scripts" / "traders" / "gammaSync.ts").read_text(
        encoding="utf-8"
    )

    assert "const GAMMA_API_KEY = process.env.GAMMA_API_KEY;" in source
    assert "embedded credentials are forbidden" in source
    assert "process.env.GAMMA_API_KEY ||" not in source
    assert "sk-gamma-" not in source


def test_legacy_desktop_builder_and_spec_refuse_packaging() -> None:
    builder = (ROOT / "aureon_launcher" / "build.bat").read_text(encoding="utf-8")
    spec = (ROOT / "aureon_launcher" / "aureon.spec").read_text(encoding="utf-8")

    assert "exit /b 2" in builder.casefold()
    assert "hold" in builder.casefold()
    assert "pip install" not in builder.casefold()
    assert "pyinstaller --" not in builder.casefold()
    assert "raise SystemExit" in spec
    assert "protected native package required" in spec
