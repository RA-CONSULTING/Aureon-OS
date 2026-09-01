from __future__ import annotations

import configparser
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = "scripts/bootstrap/protected_bootstrap_v05.py"


def test_root_container_and_supervisor_are_fixed_terminal_holds() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    copy_lines = [
        line for line in dockerfile.splitlines()
        if line.startswith(("COPY ", "ADD "))
    ]
    assert len(copy_lines) == 1
    assert BOOTSTRAP in copy_lines[0]
    assert copy_lines[0].endswith("/scripts/bootstrap/protected_bootstrap_v05.py")
    assert '"-I", "-S", "-B"' in dockerfile
    assert '"--target-id", "docker-runtime"' in dockerfile
    assert "COPY . ." not in dockerfile
    healthcheck = dockerfile[dockerfile.index("HEALTHCHECK") : dockerfile.index("ENTRYPOINT")]
    assert BOOTSTRAP in healthcheck
    assert "--target-id docker-runtime" in healthcheck
    assert "curl" not in healthcheck
    assert "EXPOSE" not in dockerfile

    supervisor_path = ROOT / "deploy" / "supervisord.conf"
    supervisor = configparser.ConfigParser(interpolation=None, strict=False)
    assert supervisor.read(supervisor_path, encoding="utf-8")
    programs = [
        section for section in supervisor.sections() if section.startswith("program:")
    ]
    assert programs
    for section in programs:
        command = supervisor[section]["command"]
        assert " -I -S -B " in command
        assert BOOTSTRAP in command
        assert re.search(r"--target-id [a-z][a-z0-9-]+$", command)
        assert " -m aureon." not in command
        assert supervisor[section].get("autorestart") == "false"
        assert supervisor[section].get("startretries") == "0"


def test_root_compose_has_one_non_networked_terminal_preflight() -> None:
    compose_path = ROOT / "docker-compose.yml"
    compose_text = compose_path.read_text(encoding="utf-8")
    compose = yaml.safe_load(compose_text)
    assert isinstance(compose, dict)
    assert "version" not in compose
    services = compose.get("services")
    assert isinstance(services, dict) and len(services) == 1
    service = next(iter(services.values()))
    assert service["restart"] == "no"
    assert service["network_mode"] == "none"
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in service["security_opt"]
    for forbidden in ("ports", "volumes", "env_file", "environment", "healthcheck"):
        assert forbidden not in service
    assert "trading-engine" not in compose_text
    assert "command-center" not in compose_text
    assert "prometheus" not in compose_text
    assert "grafana" not in compose_text


def test_deployment_shell_entrypoints_end_at_one_fixed_hold() -> None:
    for relative, target in (
        ("deploy/validate_startup.sh", "cloud-supervisor"),
        ("deploy/start_orca.sh", "cloud-orca"),
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        active = [
            line.strip()
            for line in source.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        assert BOOTSTRAP in source
        assert f"--target-id {target}" in source
        assert source.count("--target-id ") == 1
        exec_lines = [line for line in active if line.startswith("exec ")]
        assert len(exec_lines) == 1
        command = " ".join(active[active.index(exec_lines[0]) :])
        assert command.startswith("exec ")
        assert " -I -S -B " in command
        assert " -m aureon." not in source
        assert "curl " not in source
