from __future__ import annotations

import configparser
import glob
import re
import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile"
COMPOSE_FILE = ROOT / "docker-compose.yml"
SUPERVISOR_FILE = ROOT / "deploy" / "supervisord.conf"


def _module_path(module: str) -> Path:
    return ROOT.joinpath(*module.split(".")).with_suffix(".py")


def _assert_module_exists(module: str, *, source: str) -> None:
    path = _module_path(module)
    assert path.is_file(), f"{source} references missing module {module!r} ({path})"


def _assert_local_source_exists(source: str, *, owner: str) -> None:
    path = ROOT / source
    if glob.has_magic(source):
        matches = glob.glob(str(path))
        assert matches, f"{owner} references an unmatched local glob: {source}"
    else:
        assert path.exists(), f"{owner} references a missing local path: {source}"


def test_dockerfile_and_supervisor_entrypoints_resolve_to_repo_modules() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    for line in dockerfile.splitlines():
        stripped = line.strip()
        if not stripped.startswith("COPY "):
            continue
        source = shlex.split(stripped)[1]
        _assert_local_source_exists(source, owner="Dockerfile COPY")

    docker_modules = re.findall(r"python\s+-u\s+-m\s+([A-Za-z_][\w.]*)", dockerfile)
    assert docker_modules == ["aureon.bots.orca_complete_kill_cycle"]
    for module in docker_modules:
        _assert_module_exists(module, source="Dockerfile ENTRYPOINT")

    assert (ROOT / "deploy" / "validate_startup.sh").is_file()
    assert SUPERVISOR_FILE.is_file()
    assert "curl -f http://localhost:8080/health" in dockerfile

    supervisor = configparser.ConfigParser(interpolation=None, strict=False)
    supervisor.read(SUPERVISOR_FILE, encoding="utf-8")
    commands = [
        supervisor[section]["command"]
        for section in supervisor.sections()
        if section.startswith("program:")
    ]
    assert commands

    for command in commands:
        module_match = re.search(r"\bpython\s+-u\s+-m\s+([A-Za-z_][\w.]*)", command)
        if module_match:
            _assert_module_exists(module_match.group(1), source="deploy/supervisord.conf")

        for app_path in re.findall(r"(?<!\w)/app/[^\s]+", command):
            relative = app_path.removeprefix("/app/")
            _assert_local_source_exists(relative, owner="deploy/supervisord.conf")

    expected_modules = {
        "aureon.monitors.aureon_pro_dashboard",
        "aureon.autonomous.aureon_autonomous_worker",
        "aureon.queen.queen_power_redistribution",
        "aureon.command_centers.aureon_command_center_ui",
        "aureon.data_feeds.unified_market_cache",
        "aureon.exchanges.kraken_cache_feeder",
        "aureon.core.organism_daemon",
        "aureon.core.hnc_live_daemon",
    }
    assert expected_modules <= {
        match.group(1)
        for command in commands
        if (match := re.search(r"\bpython\s+-u\s+-m\s+([A-Za-z_][\w.]*)", command))
    }


def test_compose_local_paths_healthcheck_images_and_credentials_are_safe() -> None:
    compose_text = COMPOSE_FILE.read_text(encoding="utf-8")
    compose = yaml.safe_load(compose_text)
    assert "version" not in compose
    services = compose["services"]

    for service_name, service in services.items():
        build = service.get("build")
        if isinstance(build, str):
            _assert_local_source_exists(build, owner=f"{service_name}.build")
        elif isinstance(build, dict):
            context = build.get("context", ".")
            _assert_local_source_exists(context, owner=f"{service_name}.build.context")
            dockerfile = build.get("dockerfile", "Dockerfile")
            _assert_local_source_exists(
                str(Path(context) / dockerfile), owner=f"{service_name}.build.dockerfile"
            )

        env_files = service.get("env_file", [])
        if isinstance(env_files, str):
            env_files = [env_files]
        for env_file in env_files:
            _assert_local_source_exists(env_file, owner=f"{service_name}.env_file")

        for volume in service.get("volumes", []):
            if not isinstance(volume, str):
                continue
            source = volume.split(":", 1)[0]
            if source.startswith(("./", "../")):
                _assert_local_source_exists(source, owner=f"{service_name}.volumes")

    trading_health = services["trading-engine"]["healthcheck"]["test"]
    assert trading_health == ["CMD", "curl", "-fsS", "http://localhost:8080/health"]
    assert "sys.exit(0)" not in compose_text
    assert "exit 0" not in " ".join(trading_health).lower()

    command = services["command-center"]["command"]
    assert command[:3] == ["python", "-m", "aureon.command_centers.aureon_command_center_ui"]
    _assert_module_exists(command[2], source="command-center.command")

    critical_images = {
        name: service["image"]
        for name, service in services.items()
        if "image" in service
    }
    assert critical_images == {
        "prometheus": "prom/prometheus:v3.12.0",
        "grafana": "grafana/grafana:13.0.2",
    }
    for service_name, image in critical_images.items():
        tag = image.rsplit(":", 1)[-1]
        assert tag not in {"latest", "main", "master", "stable", "edge"}, (
            f"{service_name} uses floating image tag {tag!r}"
        )
        assert re.fullmatch(r"v?\d+\.\d+\.\d+", tag), (
            f"{service_name} image is not pinned to an exact release: {image}"
        )

    assert "changeme" not in compose_text.lower()
    assert "GF_SECURITY_ADMIN_PASSWORD=${GF_ADMIN_PASSWORD:?" in compose_text
    assert "GF_AUTH_ANONYMOUS_ENABLED=false" in compose_text


def test_startup_shell_scripts_only_reference_existing_canonical_modules() -> None:
    startup_files = [ROOT / "deploy" / "validate_startup.sh", ROOT / "deploy" / "start_orca.sh"]
    texts = [path.read_text(encoding="utf-8") for path in startup_files]

    critical_paths = re.findall(r'^\s+"(aureon/[^\"]+\.py)"$', texts[0], flags=re.MULTILINE)
    assert critical_paths
    for path in critical_paths:
        _assert_local_source_exists(path, owner="deploy/validate_startup.sh")

    for path, text in zip(startup_files, texts, strict=True):
        executable_modules = re.findall(
            r"python[^\n]*?\s-m\s+(aureon\.[A-Za-z_][\w.]*)", text
        )
        imported_modules = re.findall(
            r"^\s*from\s+(aureon(?:\.[A-Za-z_]\w*)+)\s+import", text, flags=re.MULTILINE
        )
        for module in executable_modules + imported_modules:
            _assert_module_exists(module, source=str(path.relative_to(ROOT)))

    stale_root_commands = {
        "python -u unified_market_cache.py",
        "python -u aureon_power_redistribution_engine.py",
        "python -u queen_web_dashboard.py",
        "-u orca_complete_kill_cycle.py",
    }
    combined = "\n".join(texts)
    assert all(command not in combined for command in stale_root_commands)
