from __future__ import annotations

import os
import re
import runpy
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_DIR = REPO_ROOT / "scripts" / "launchers"
DEPLOY_DIR = REPO_ROOT / "deploy"
ISOLATED_BOOTSTRAP_POSIX = "scripts/bootstrap/protected_bootstrap_v05.py"
ISOLATED_BOOTSTRAP = REPO_ROOT / ISOLATED_BOOTSTRAP_POSIX
POWERSHELL_LAUNCHERS = (
    LAUNCHER_DIR / "AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1",
    LAUNCHER_DIR / "AUREON_DATA_OCEAN.ps1",
    LAUNCHER_DIR / "start_everything_production.ps1",
)
CMD_WRAPPERS = (
    LAUNCHER_DIR / "AUREON_PRODUCTION_LIVE.cmd",
    LAUNCHER_DIR / "AUREON_WAKE_UP_FULL_AUTONOMOUS.cmd",
    LAUNCHER_DIR / "AUREON_DATA_OCEAN.cmd",
)


def _powershell() -> str:
    executable = shutil.which("powershell.exe") or shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        pytest.skip("PowerShell is unavailable; static launcher contracts still run.")
    return executable


def _assert_powershell_parses(path: Path) -> None:
    environment = os.environ.copy()
    environment["AUREON_TEST_PARSE_PATH"] = str(path)
    command = (
        "$path = [Environment]::GetEnvironmentVariable('AUREON_TEST_PARSE_PATH'); "
        "$tokens = $null; $errors = $null; "
        "[void][System.Management.Automation.Language.Parser]::ParseFile("
        "$path, [ref]$tokens, [ref]$errors); "
        "if ($errors.Count -gt 0) { "
        "$errors | ForEach-Object { [Console]::Error.WriteLine($_.Message) }; exit 1 }"
    )
    result = subprocess.run(
        [_powershell(), "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


@pytest.mark.parametrize("launcher", POWERSHELL_LAUNCHERS, ids=lambda path: path.name)
def test_primary_powershell_launchers_parse(launcher: Path) -> None:
    _assert_powershell_parses(launcher)


@pytest.mark.parametrize(
    ("launcher", "stale_anchor"),
    (
        (POWERSHELL_LAUNCHERS[0], "$myinvocation.scriptname"),
        (POWERSHELL_LAUNCHERS[1], "$myinvocation.mycommand.path"),
        (POWERSHELL_LAUNCHERS[2], "$myinvocation.mycommand.definition"),
    ),
    ids=lambda value: value.name if isinstance(value, Path) else None,
)
def test_primary_powershell_launchers_resolve_the_repo_root(
    launcher: Path, stale_anchor: str
) -> None:
    source = launcher.read_text(encoding="utf-8").lower()

    assert "$psscriptroot" in source
    assert '"..\\.."' in source
    assert "pyproject.toml" in source
    assert stale_anchor not in source


@pytest.mark.parametrize("wrapper", CMD_WRAPPERS, ids=lambda path: path.name)
def test_primary_cmd_wrappers_resolve_root_and_propagate_exit_code(wrapper: Path) -> None:
    source = wrapper.read_text(encoding="utf-8").lower()

    assert 'set "powershell_path=c:\\windows\\system32\\windowspowershell\\v1.0\\powershell.exe"' in source
    assert 'if not exist "%powershell_path%"' in source
    assert '"%powershell_path%" -noprofile -executionpolicy bypass -file' in source
    assert "powershell.exe -noprofile" not in source
    assert '%~dp0..\\..' in source
    assert 'if not exist "%repo_root%\\pyproject.toml"' in source
    assert 'pushd "%repo_root%" >nul' in source
    assert 'set "exit_code=%errorlevel%"' in source
    assert "popd" in source
    assert source.rstrip().endswith("endlocal & exit /b %exit_code%")
    assert 'cd /d "%~dp0"' not in source


def test_primary_runtime_launchers_enter_fixed_protected_bootstrap_first() -> None:
    wake = POWERSHELL_LAUNCHERS[0].read_text(encoding="utf-8")
    ocean = POWERSHELL_LAUNCHERS[1].read_text(encoding="utf-8")
    bootstrap = 'scripts\\bootstrap\\protected_bootstrap_v05.py'

    wake_gate = wake.index(bootstrap)
    wake_hold = wake.index("if ($protectedBootstrapExit -ne 0)", wake_gate)
    assert wake.count(bootstrap) == 1
    assert "& $Python -I -S -B $ProtectedBootstrap" in wake[wake_gate:wake_hold]
    assert "-m aureon.plumber.protected_bootstrap_v05" not in wake
    assert "--root" not in wake[wake_gate:wake_hold]
    assert "--target-id windows-wake" in wake[wake_gate:wake_hold]
    assert wake_gate < wake_hold < wake.index("$Npm = Get-NpmPath", wake_hold)
    assert wake_hold < wake.index("New-Item -ItemType Directory", wake_hold)
    assert wake_hold < wake.index("-m aureon.autonomous.aureon_full_live_release", wake_hold)

    ocean_gate = ocean.index(bootstrap)
    ocean_hold = ocean.index("if ($protectedBootstrapExit -ne 0)", ocean_gate)
    assert ocean.count(bootstrap) == 1
    assert "& $Python -I -S -B $ProtectedBootstrap" in ocean[ocean_gate:ocean_hold]
    assert "-m aureon.plumber.protected_bootstrap_v05" not in ocean
    assert "--root" not in ocean[ocean_gate:ocean_hold]
    assert "--target-id data-ocean" in ocean[ocean_gate:ocean_hold]
    assert ocean_gate < ocean_hold < ocean.index("$env:PYTHONUNBUFFERED", ocean_hold)
    assert ocean_hold < ocean.index("Invoke-StatusRefresh", ocean_hold)


@pytest.mark.parametrize(
    ("launcher", "target_id"),
    (
        (DEPLOY_DIR / "validate_startup.sh", "cloud-supervisor"),
        (DEPLOY_DIR / "start_orca.sh", "cloud-orca"),
        (DEPLOY_DIR / "start_master_launcher.sh", "master-launcher"),
        (DEPLOY_DIR / "start_queen.sh", "cloud-queen-redistribution"),
        (DEPLOY_DIR / "droplet-setup.sh", "linux-supervisor"),
        (DEPLOY_DIR / "droplet-deploy.sh", "linux-supervisor"),
        (REPO_ROOT / "scripts" / "linux" / "aureon-up.sh", "linux-supervisor"),
        (REPO_ROOT / "scripts" / "linux" / "install-linux.sh", "linux-supervisor"),
        (
            REPO_ROOT / "scripts" / "shell" / "deploy" / "test-docker.sh",
            "docker-runtime",
        ),
        (REPO_ROOT / "production" / "entrypoint.sh", "production-supervisor"),
    ),
    ids=lambda value: value.name if isinstance(value, Path) else None,
)
def test_posix_runtime_launchers_are_terminal_isolated_holds(
    launcher: Path,
    target_id: str,
) -> None:
    source = launcher.read_text(encoding="utf-8")
    active = [
        line.strip()
        for line in source.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert source.count(ISOLATED_BOOTSTRAP_POSIX) == 1
    assert any(line.startswith("exec ") for line in active)
    assert " -I -S -B " in source
    assert source.count("--target-id ") == 1
    assert f"--target-id {target_id}" in source
    assert "-m aureon.plumber.protected_bootstrap_v05" not in source
    target_line = next(
        index for index, line in enumerate(active) if f"--target-id {target_id}" in line
    )
    assert target_line == len(active) - 1


def test_docker_runtime_is_only_the_fixed_isolated_hold() -> None:
    source = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    entrypoint = next(
        line for line in source.splitlines() if line.startswith("ENTRYPOINT ")
    )
    healthcheck = source[source.index("HEALTHCHECK ") : source.index("ENTRYPOINT ")]

    assert ISOLATED_BOOTSTRAP_POSIX in entrypoint
    assert '"-I", "-S", "-B"' in entrypoint
    assert '"--target-id", "docker-runtime"' in entrypoint
    assert "/bin/bash" not in entrypoint
    assert "-m aureon" not in entrypoint
    assert "supervisord" not in entrypoint
    assert ISOLATED_BOOTSTRAP_POSIX in healthcheck
    assert "--target-id docker-runtime" in healthcheck
    assert "curl" not in healthcheck


def test_operator_image_cannot_import_wsgi_before_the_isolated_hold() -> None:
    source = (DEPLOY_DIR / "operator.Dockerfile").read_text(encoding="utf-8")
    entrypoint = next(
        line for line in source.splitlines() if line.startswith("ENTRYPOINT ")
    )
    healthcheck = source[source.index("HEALTHCHECK ") : source.index("ENTRYPOINT ")]

    assert ISOLATED_BOOTSTRAP_POSIX in source
    assert ISOLATED_BOOTSTRAP_POSIX in entrypoint
    assert '"-I", "-S", "-B"' in entrypoint
    assert '"--target-id", "operator-wsgi"' in entrypoint
    assert "waitress-serve" not in entrypoint
    assert "aureon.operator.wsgi:app" not in entrypoint
    assert ISOLATED_BOOTSTRAP_POSIX in healthcheck
    assert "--target-id operator-wsgi" in healthcheck
    assert "curl" not in healthcheck


def test_frontend_container_starts_only_the_explicit_non_python_hold() -> None:
    dockerfile = (DEPLOY_DIR / "frontend.Dockerfile").read_text(encoding="utf-8")
    hold = (
        REPO_ROOT / "scripts" / "bootstrap" / "frontend_container_hold_v05.sh"
    ).read_text(encoding="utf-8")
    entrypoint = next(
        line for line in dockerfile.splitlines() if line.startswith("ENTRYPOINT ")
    )
    assert entrypoint == (
        'ENTRYPOINT ["/bin/sh", '
        '"/opt/aureon/scripts/bootstrap/frontend_container_hold_v05.sh"]'
    )
    assert "FROM alpine:" in dockerfile
    assert "USER 65532:65532" in dockerfile
    assert "HEALTHCHECK" not in dockerfile
    assert "EXPOSE" not in dockerfile
    assert "npm " not in dockerfile
    assert "node:" not in dockerfile
    assert "COPY frontend" not in dockerfile
    assert "frontend.nginx.conf" not in dockerfile
    assert "nginx" not in entrypoint
    assert '"decision":"HOLD"' in hold
    assert '"target_started":false' in hold
    assert '"network_accessed":false' in hold
    assert '"file_written":false' in hold
    assert '"production_ready":false' in hold
    assert "curl " not in hold
    assert "wget " not in hold
    assert "exec " not in hold


@pytest.mark.parametrize(
    ("compose", "expected_holds"),
    (
        (DEPLOY_DIR / "docker-compose.operator.yml", 1),
        (DEPLOY_DIR / "docker-compose.saas.yml", 2),
        (REPO_ROOT / "docker-compose.yml", 1),
        (REPO_ROOT / "docker-compose.autonomous.yml", 1),
        (REPO_ROOT / "production" / "docker-compose.yml", 1),
    ),
    ids=("operator", "saas", "root", "autonomous", "production"),
)
def test_compose_surfaces_are_terminal_no_network_holds(
    compose: Path,
    expected_holds: int,
) -> None:
    source = compose.read_text(encoding="utf-8")

    assert source.count('restart: "no"') == expected_holds
    assert source.count('network_mode: "none"') == expected_holds
    assert source.count("read_only: true") == expected_holds
    assert source.count("no-new-privileges:true") == expected_holds
    assert source.count("cap_drop:") == expected_holds
    assert source.count("- ALL") == expected_holds
    assert source.count("command: []") == expected_holds
    assert "unless-stopped" not in source
    assert "healthcheck:" not in source
    assert "ports:" not in source
    assert "volumes:" not in source
    assert "environment:" not in source
    assert "AUREON_TRADE_GATING" not in source


@pytest.mark.parametrize(
    "config",
    (
        DEPLOY_DIR / "supervisord.conf",
        DEPLOY_DIR / "supervisord.linux.conf",
        DEPLOY_DIR / "supervisord.master_launcher.conf",
        REPO_ROOT / "supervisord.conf",
        REPO_ROOT / "production" / "supervisord.conf",
    ),
    ids=lambda path: path.name,
)
def test_supervisors_cannot_bypass_the_isolated_hold(config: Path) -> None:
    source = config.read_text(encoding="utf-8")
    commands = [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith("command=")
    ]

    assert commands
    assert all(ISOLATED_BOOTSTRAP_POSIX in command for command in commands)
    assert all(" -I -S -B " in command for command in commands)
    assert all("--target-id " in command for command in commands)
    assert all("-m aureon" not in command for command in commands)
    assert all("npm run" not in command for command in commands)
    assert "autorestart=true" not in source
    assert source.count("startsecs=0") == len(commands)
    assert source.count("startretries=0") == len(commands)


def test_all_systemd_services_are_terminal_isolated_holds() -> None:
    appliance_systemd = (
        REPO_ROOT
        / "packaging"
        / "appliance"
        / "rootfs"
        / "usr"
        / "lib"
        / "systemd"
        / "system"
    )
    services = (
        *(DEPLOY_DIR.glob("*.service")),
        *((DEPLOY_DIR / "systemd").glob("*.service")),
        *(appliance_systemd / name for name in (
            "aureon-hnc.service",
            "aureon-operator.service",
            "aureon-organism.service",
        )),
    )

    assert services
    for service in services:
        source = service.read_text(encoding="utf-8")
        exec_starts = [
            line for line in source.splitlines() if line.startswith("ExecStart=")
        ]
        assert len(exec_starts) == 1, service
        command = exec_starts[0]
        assert ISOLATED_BOOTSTRAP_POSIX in command, service
        assert " -I -S -B " in command, service
        assert "--target-id " in command, service
        assert "-m aureon" not in command, service
        assert "Restart=no" in source, service
        assert "Restart=always" not in source, service

    firstboot = (appliance_systemd / "aureon-firstboot-console.service").read_text(
        encoding="utf-8"
    )
    assert "Restart=no" in firstboot
    assert "Restart=on-failure" not in firstboot


def test_cloud_manifests_cannot_start_a_runtime_or_auto_deploy() -> None:
    app_spec = (REPO_ROOT / "app.yaml").read_text(encoding="utf-8")
    procfile = (REPO_ROOT / "Procfile").read_text(encoding="utf-8")

    assert "services: []" in app_spec
    assert "workers: []" in app_spec
    assert "jobs: []" in app_spec
    assert "run_command:" not in app_spec
    assert "deploy_on_push:" not in app_spec
    assert "type: SECRET" not in app_spec
    assert procfile.strip().startswith("release: ")
    assert ISOLATED_BOOTSTRAP_POSIX in procfile
    assert "--target-id cloud-supervisor" in procfile
    assert "web:" not in procfile
    assert "pip install" not in procfile


def test_docker_build_context_is_default_deny_and_has_no_private_tree() -> None:
    dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    patterns = [
        line.strip()
        for line in dockerignore.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert patterns == [
        "*",
        "imports/",
        "archive/",
        "!Dockerfile",
        "!Dockerfile.ephemeris",
        "!.dockerignore",
        "!deploy/",
        "deploy/*",
        "!deploy/operator.Dockerfile",
        "!deploy/frontend.Dockerfile",
        "!production/",
        "production/*",
        "!production/Dockerfile",
        "!scripts/",
        "scripts/*",
        "!scripts/bootstrap/",
        "scripts/bootstrap/*",
        "!scripts/bootstrap/protected_bootstrap_v05.py",
        "!scripts/bootstrap/frontend_container_hold_v05.sh",
    ]
    assert all(not pattern.startswith(("!data", "!docs", "!aureon")) for pattern in patterns)

    for dockerfile in (
        REPO_ROOT / "Dockerfile",
        REPO_ROOT / "Dockerfile.ephemeris",
        DEPLOY_DIR / "operator.Dockerfile",
        REPO_ROOT / "production" / "Dockerfile",
    ):
        copy_lines = [
            line for line in dockerfile.read_text(encoding="utf-8").splitlines()
            if line.startswith(("COPY ", "ADD "))
        ]
        assert len(copy_lines) == 1, dockerfile
        assert ISOLATED_BOOTSTRAP_POSIX in copy_lines[0], dockerfile
        assert "COPY . ." not in copy_lines[0], dockerfile
        assert "data/" not in copy_lines[0], dockerfile


def test_all_deployment_gate_targets_are_fixed_in_the_isolated_registry() -> None:
    registry = set(runpy.run_path(str(ISOLATED_BOOTSTRAP))["_TARGETS"])
    sources = [
        (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8"),
        (DEPLOY_DIR / "operator.Dockerfile").read_text(encoding="utf-8"),
        (REPO_ROOT / "production" / "Dockerfile").read_text(encoding="utf-8"),
        (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8"),
        (REPO_ROOT / "docker-compose.autonomous.yml").read_text(encoding="utf-8"),
        (REPO_ROOT / "production" / "docker-compose.yml").read_text(encoding="utf-8"),
        (DEPLOY_DIR / "docker-compose.operator.yml").read_text(encoding="utf-8"),
        (DEPLOY_DIR / "docker-compose.saas.yml").read_text(encoding="utf-8"),
        *(path.read_text(encoding="utf-8") for path in (
            DEPLOY_DIR / "validate_startup.sh",
            DEPLOY_DIR / "start_orca.sh",
            DEPLOY_DIR / "start_master_launcher.sh",
            DEPLOY_DIR / "start_queen.sh",
            DEPLOY_DIR / "droplet-setup.sh",
            DEPLOY_DIR / "droplet-deploy.sh",
            DEPLOY_DIR / "supervisord.conf",
            DEPLOY_DIR / "supervisord.linux.conf",
            DEPLOY_DIR / "supervisord.master_launcher.conf",
            REPO_ROOT / "supervisord.conf",
            REPO_ROOT / "production" / "supervisord.conf",
            REPO_ROOT / "production" / "entrypoint.sh",
            REPO_ROOT / "scripts" / "linux" / "aureon-up.sh",
            REPO_ROOT / "scripts" / "linux" / "install-linux.sh",
            REPO_ROOT / "scripts" / "shell" / "deploy" / "test-docker.sh",
            *(
                REPO_ROOT
                / "packaging"
                / "appliance"
                / "rootfs"
                / "usr"
                / "lib"
                / "systemd"
                / "system"
                / name
                for name in (
                    "aureon-hnc.service",
                    "aureon-operator.service",
                    "aureon-organism.service",
                )
            ),
            *(DEPLOY_DIR.glob("*.service")),
            *((DEPLOY_DIR / "systemd").glob("*.service")),
        )),
    ]
    selected = {
        match.group(1)
        for source in sources
        for match in re.finditer(r"--target-id(?:\",)?[ \"]+([a-z][a-z0-9-]+)", source)
    }

    assert selected
    assert selected <= registry


def test_active_deployment_and_readme_lines_have_no_direct_aureon_runtime() -> None:
    paths = (
        REPO_ROOT / "README.md",
        REPO_ROOT / "app.yaml",
        REPO_ROOT / "Procfile",
        REPO_ROOT / "Dockerfile",
        DEPLOY_DIR / "operator.Dockerfile",
        DEPLOY_DIR / "frontend.Dockerfile",
        DEPLOY_DIR / "start_orca.sh",
        DEPLOY_DIR / "start_master_launcher.sh",
        DEPLOY_DIR / "start_queen.sh",
        DEPLOY_DIR / "droplet-setup.sh",
        DEPLOY_DIR / "droplet-deploy.sh",
        DEPLOY_DIR / "supervisord.conf",
        DEPLOY_DIR / "supervisord.linux.conf",
        DEPLOY_DIR / "supervisord.master_launcher.conf",
        REPO_ROOT / "supervisord.conf",
        REPO_ROOT / "production" / "Dockerfile",
        REPO_ROOT / "docker-compose.yml",
        REPO_ROOT / "docker-compose.autonomous.yml",
        REPO_ROOT / "production" / "docker-compose.yml",
        REPO_ROOT / "production" / "entrypoint.sh",
        REPO_ROOT / "production" / "supervisord.conf",
        REPO_ROOT / "scripts" / "shell" / "deploy" / "test-docker.sh",
        REPO_ROOT / "scripts" / "linux" / "install-linux.sh",
        *(DEPLOY_DIR.glob("*.service")),
        *((DEPLOY_DIR / "systemd").glob("*.service")),
    )
    active_lines = [
        line
        for path in paths
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith(("#", ";"))
    ]

    assert all("-m aureon." not in line for line in active_lines)
    assert all("aureon.operator.wsgi:app" not in line for line in active_lines)
    assert all("aureon_master_launcher.py --production" not in line for line in active_lines)
    assert all("orca_complete_kill_cycle.py" not in line for line in active_lines)
    assert all("micro_profit_labyrinth.py" not in line for line in active_lines)


@pytest.mark.skipif(os.name != "nt", reason="Production launcher is Windows-only.")
def test_start_everything_whatif_uses_current_launcher_paths(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment.update({"LIVE": "0", "DRY_RUN": "1", "AUREON_LIVE_TRADING": "0"})
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(LAUNCHER_DIR / "start_everything_production.ps1"),
            "-WhatIf",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        check=False,
    )
    output = (result.stdout + result.stderr).lower()

    assert result.returncode == 0, output
    assert "whatif mode" in output
    assert "scripts\\launchers\\aureon_production_live.cmd" in output
    assert "scripts\\start_aureon_with_flameborn.ps1" in output
    assert "both terminals launched" not in output
