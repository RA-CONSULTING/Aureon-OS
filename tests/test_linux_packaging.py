"""
The full Linux version — install + launcher + systemd, verified honest.

Offline, no processes started. The load-bearing check is that every ``python -m
aureon.*`` in the Linux supervisord config resolves to a real module (the exact
bug that rotted the old configs after the repo reorg), plus: the deps set is
Linux-safe (no Windows-only packages), the console entry points import + are
callable, the launcher/install scripts are executable + parse, and the systemd
units are well-formed and safe-by-default.
"""

from __future__ import annotations

import configparser
import importlib.util as _u
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
    assert len(progs) >= 14        # the full stack


def test_every_module_path_resolves():
    """No stale paths: every `-m aureon.<mod>` in the config is importable."""
    cp, progs = _programs()
    mods = []
    for s in progs:
        m = re.search(r"-m (aureon\.[\w.]+)", cp[s].get("command", ""))
        if m:
            mods.append(m.group(1))
    assert len(mods) >= 14
    missing = [m for m in mods if _u.find_spec(m) is None]
    assert missing == [], f"stale process paths in supervisord.linux.conf: {missing}"


def test_every_process_module_is_runnable():
    """Stronger than import: `python -m <mod>` only *starts a process* if the module
    has a `__main__` guard. A module that resolves but lacks one would import-and-exit,
    flapping under supervisord's autorestart. Assert every `-m` target is runnable."""
    cp, progs = _programs()
    not_runnable = []
    for s in progs:
        m = re.search(r"-m (aureon\.[\w.]+)", cp[s].get("command", ""))
        if not m:
            continue
        spec = _u.find_spec(m.group(1))
        src = open(spec.origin, encoding="utf-8").read() if spec and spec.origin else ""
        if 'if __name__ == "__main__"' not in src and "if __name__ == '__main__'" not in src:
            not_runnable.append(m.group(1))
    assert not_runnable == [], f"process modules with no __main__ guard (would flap): {not_runnable}"


def test_config_is_dry_paper_by_default():
    """The config never arms live trading or local actions itself (comments aside)."""
    active = "\n".join(ln for ln in open(_CONF, encoding="utf-8").read().splitlines()
                       if not ln.lstrip().startswith(";"))
    assert "AUREON_LIVE_TRADING=1" not in active        # live is never hard-armed in-config
    assert "AUREON_LOCAL_ACTIONS_ARMED" not in active   # never arms irreversible local actions
    assert "AUREON_SOUL_ACT" not in active


def test_requirements_linux_is_linux_safe():
    reqs = open(os.path.join(_ROOT, "requirements-linux.txt"), encoding="utf-8").read().lower()
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
    whole = open(os.path.join(d, "aureon.service"), encoding="utf-8").read()
    assert "ExecStart=" in whole and "supervisord" in whole
    assert "AUREON_LIVE_TRADING=0" in whole            # dry/paper by default
