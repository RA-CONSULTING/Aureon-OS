from __future__ import annotations

import configparser
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILES = (
    "docker-compose.yml",
    "docker-compose.autonomous.yml",
    "deploy/docker-compose.operator.yml",
    "deploy/docker-compose.saas.yml",
    "production/docker-compose.yml",
)
APP_SPECS = ("app.yaml", ".do/app.yaml")
SUPERVISOR_FILES = (
    "supervisord.conf",
    "deploy/supervisord.conf",
    "deploy/supervisord.linux.conf",
    "deploy/supervisord.master_launcher.conf",
    "production/supervisord.conf",
)


def test_compose_surfaces_have_no_authorized_writer_or_network() -> None:
    for relative in COMPOSE_FILES:
        payload = yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))
        services = payload.get("services")
        assert isinstance(services, dict) and services, relative
        for name, service in services.items():
            assert service["restart"] == "no", f"{relative}:{name}"
            assert service["network_mode"] == "none", f"{relative}:{name}"
            assert service["read_only"] is True, f"{relative}:{name}"
            assert service["cap_drop"] == ["ALL"], f"{relative}:{name}"
            assert "no-new-privileges:true" in service["security_opt"]
            for forbidden in (
                "ports", "volumes", "env_file", "environment", "healthcheck", "deploy"
            ):
                assert forbidden not in service, f"{relative}:{name}:{forbidden}"


def test_digitalocean_has_zero_components_and_no_autoscaling() -> None:
    for relative in APP_SPECS:
        source = (ROOT / relative).read_text(encoding="utf-8")
        payload = yaml.safe_load(source)
        for key in ("services", "workers", "jobs", "static_sites", "functions", "databases"):
            assert payload.get(key) == [], f"{relative}:{key}"
        assert "autoscaling" not in source
        assert "instance_count" not in source
        assert "deploy_on_push" not in source


def test_supervisor_programs_are_fixed_single_hold_processes() -> None:
    for relative in SUPERVISOR_FILES:
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        assert parser.read(ROOT / relative, encoding="utf-8")
        programs = [
            section for section in parser.sections() if section.startswith("program:")
        ]
        assert programs, relative
        for section in programs:
            command = parser[section]["command"]
            assert " -I -S -B " in command
            assert "scripts/bootstrap/protected_bootstrap_v05.py" in command
            assert re.search(r"--target-id [a-z][a-z0-9-]+$", command)
            assert parser[section].get("numprocs", "1") == "1"
            assert parser[section].get("autorestart") == "false"
            assert parser[section].get("startretries") == "0"


def test_systemd_units_are_non_restarting_terminal_holds() -> None:
    for path in sorted((ROOT / "deploy" / "systemd").glob("*.service")):
        source = path.read_text(encoding="utf-8")
        assert "protected_bootstrap_v05.py --target-id " in source, path
        assert "Restart=no" in source, path
        assert "IPAddressDeny=any" in source, path
        assert "@" not in path.name


def test_procfile_is_one_absolute_release_hold() -> None:
    entries = [
        line
        for line in (ROOT / "Procfile").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert entries == [
        "release: /usr/local/bin/python -I -S -B "
        "scripts/bootstrap/protected_bootstrap_v05.py --target-id cloud-supervisor"
    ]


def test_scaling_runbook_states_the_missing_proof_and_hold() -> None:
    source = (ROOT / "docs" / "runbooks" / "SINGLE_WRITER_SCALING.md").read_text(
        encoding="utf-8"
    ).lower()
    for phrase in (
        "terminal hold",
        "no authorized writer process",
        "leader election with fencing",
        "globally unique idempotency",
        "shared provider-aware rate limits",
        "local static validation is not provider read-back",
    ):
        assert phrase in source
