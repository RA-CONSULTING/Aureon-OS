"""Offline contracts for the fail-closed Linux packaging surfaces."""

from __future__ import annotations

import configparser
import os
import re
import subprocess

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONF = os.path.join(_ROOT, "deploy", "supervisord.linux.conf")


def _bash_parser():
    if os.name != "nt":
        return "bash"
    git_bash = os.path.join(
        os.environ.get("PROGRAMFILES", r"C:\Program Files"),
        "Git",
        "bin",
        "bash.exe",
    )
    assert os.path.isfile(git_bash), "Git Bash is required to validate Linux scripts on Windows"
    return git_bash


def _programs():
    cp = configparser.ConfigParser(interpolation=None)
    cp.read(_CONF)
    return cp, [s for s in cp.sections() if s.startswith("program:")]


def test_supervisord_linux_config_parses():
    cp, progs = _programs()
    assert cp.has_section("supervisord")
    assert len(progs) >= 14


def test_every_supervised_route_is_the_terminal_isolated_hold():
    cp, progs = _programs()
    target_ids: set[str] = set()
    for section in progs:
        command = cp[section].get("command", "")
        assert "%(ENV_AUREON_PYTHON)s -I -S -B" in command
        assert "scripts/bootstrap/protected_bootstrap_v05.py" in command
        assert " -m aureon." not in command
        match = re.search(r"--target-id ([a-z0-9-]+)$", command)
        assert match is not None, f"missing fixed target id in {section}"
        target_ids.add(match.group(1))
        assert cp[section].get("autorestart") == "false"
        assert cp[section].get("startretries") == "0"
    assert len(target_ids) == len(progs)


def test_config_is_dry_paper_by_default():
    """The config never arms live trading or local actions itself (comments aside)."""
    with open(_CONF, encoding="utf-8") as handle:
        active = "\n".join(
            line for line in handle.read().splitlines()
            if not line.lstrip().startswith(";")
        )
    assert "AUREON_LIVE_TRADING=1" not in active        # live is never hard-armed in-config
    assert "AUREON_LOCAL_ACTIONS_ARMED" not in active   # never arms irreversible local actions
    assert "AUREON_SOUL_ACT" not in active


def test_requirements_linux_is_linux_safe():
    with open(os.path.join(_ROOT, "requirements-linux.txt"), encoding="utf-8") as handle:
        reqs = handle.read().lower()
    pkgs = [ln.strip() for ln in reqs.splitlines()
            if ln.strip() and not ln.strip().startswith("#")]
    joined = "\n".join(pkgs)
    for bad in ("pycaw", "comtypes", "pywin32", "pyautogui", "pyaudio", "opencv-python"):
        assert bad not in joined, f"{bad} is not Linux-server-safe"
    assert any(p.startswith("numpy") for p in pkgs)    # the real trading stack is kept
    assert any(p.startswith("pandas") for p in pkgs)


def test_console_entry_points_import_and_are_callable():
    import tomllib
    with open(os.path.join(_ROOT, "pyproject.toml"), "rb") as fh:
        scripts = tomllib.load(fh)["project"]["scripts"]
    for name in ("aureon-operator", "aureon-organism", "aureon-hnc"):
        assert name in scripts
    for target in scripts.values():                    # "module:func"
        mod, _, func = target.partition(":")
        m = __import__(mod, fromlist=[func])
        assert callable(getattr(m, func)), f"{target} is not callable"


@pytest.mark.parametrize("script", [
    "scripts/linux/aureon-up.sh", "scripts/linux/aureon-down.sh",
    "scripts/linux/aureon-status.sh", "scripts/linux/install-linux.sh",
])
def test_launcher_scripts_executable_and_valid(script):
    path = os.path.join(_ROOT, script)
    assert os.access(path, os.X_OK), f"{script} is not executable"
    r = subprocess.run([_bash_parser(), "-n", path], capture_output=True, text=True)
    assert r.returncode == 0, f"{script} syntax error: {r.stderr}"


def test_systemd_units_present_and_safe():
    d = os.path.join(_ROOT, "deploy", "systemd")
    for unit in ("aureon.service", "aureon-operator.service", "aureon-organism.service",
                 "aureon-hnc.service", "aureon.target"):
        assert os.path.exists(os.path.join(d, unit)), f"missing {unit}"
    with open(os.path.join(d, "aureon.service"), encoding="utf-8") as handle:
        whole = handle.read()
    assert "ExecStart=/opt/aureon/.venv/bin/python -I -S -B" in whole
    assert "scripts/bootstrap/protected_bootstrap_v05.py --target-id linux-supervisor" in whole
    assert "supervisord" not in whole
    assert "Restart=no" in whole
    assert "IPAddressDeny=any" in whole
    assert "AUREON_LIVE_TRADING" not in whole


def test_down_script_never_signals_an_unverified_pid_file():
    with open(
        os.path.join(_ROOT, "scripts", "linux", "aureon-down.sh"), encoding="utf-8"
    ) as handle:
        source = handle.read()
    assert re.search(r"(?:^|\s)kill\s", source, re.MULTILINE) is None
    assert "refusing to signal a potentially recycled PID" in source
