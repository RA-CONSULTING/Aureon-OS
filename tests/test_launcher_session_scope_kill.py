"""Kill switch for the launcher scope.

A process-group kill misses children that call setsid or setpgid. The kill
switch has to stop the systemd user scope, or the dedicated cgroup, or walk
the pid tree when neither is available.

The full-launcher case uses fake key strings only. It does not open a dotenv
file. AUREON_LIVE_TRADING stays 0. socket.connect and getaddrinfo raise.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_FAKE_KEYS = {
    "KRAKEN_API_KEY": "fake",
    "KRAKEN_API_SECRET": "fake",
    "BINANCE_API_KEY": "fake",
    "BINANCE_API_SECRET": "fake",
    "ALPACA_API_KEY": "fake",
    "ALPACA_SECRET_KEY": "fake",
    "CAPITAL_API_KEY": "fake",
    "CAPITAL_IDENTIFIER": "fake",
    "CAPITAL_PASSWORD": "fake",
}

_SITECUSTOMIZE = """
import os

_TOUCH = os.environ.get("AUREON_DOTENV_TOUCH_LOG", "")
_OS_OPEN = os.open


def _note(name: str) -> None:
    if not _TOUCH:
        return
    fd = _OS_OPEN(_TOUCH, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o644)
    try:
        os.write(fd, (name + "\\n").encode("ascii"))
    finally:
        os.close(fd)


def _open(path, flags, mode=0o777, *, dir_fd=None):
    name = os.path.basename(os.fspath(path))
    if name == ".env":
        _note(name)
        raise OSError("refusing to open dotenv file")
    if dir_fd is None:
        return _OS_OPEN(path, flags, mode)
    return _OS_OPEN(path, flags, mode, dir_fd=dir_fd)


os.open = _open

import builtins

_BUILTIN_OPEN = builtins.open


def _builtin_open(file, mode="r", *args, **kwargs):
    name = os.path.basename(os.fspath(file))
    if name == ".env":
        _note(name)
        raise OSError("refusing to open dotenv file")
    return _BUILTIN_OPEN(file, mode, *args, **kwargs)


builtins.open = _builtin_open

import socket


def _blocked_connect(self, address):
    raise OSError("network blocked")


def _blocked_getaddrinfo(*args, **kwargs):
    raise OSError("network blocked")


socket.socket.connect = _blocked_connect
socket.getaddrinfo = _blocked_getaddrinfo
"""


def _alive(pid: int) -> bool:
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    try:
        data = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    end = data.rfind(")")
    if end < 0:
        return True
    fields = data[end + 2 :].split()
    if fields and fields[0] == "Z":
        return False
    return True


def _cmdline(pid: int) -> list[str]:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return []
    text = raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()
    return text.split()


def _cgroup(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/cgroup").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _environ(pid: int) -> dict[str, str]:
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError:
        return {}
    found: dict[str, str] = {}
    for item in raw.split(b"\x00"):
        if b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        found[key.decode("utf-8", "replace")] = value.decode("utf-8", "replace")
    return found


def _wait_until(predicate, timeout: float, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = predicate()
        if found:
            return found
        time.sleep(interval)
    return None


def _find_trader() -> int | None:
    try:
        entries = os.listdir("/proc")
    except OSError:
        return None
    for entry in entries:
        if not entry.isdigit():
            continue
        pid = int(entry)
        parts = _cmdline(pid)
        if "aureon.exchanges.unified_market_trader" not in parts:
            continue
        if "--interval" not in parts:
            continue
        index = parts.index("--interval")
        if index + 1 < len(parts) and parts[index + 1] == "2":
            return pid
    return None


def _descendant_pids(root: int) -> set[int]:
    """Pid tree via /proc. A setsid child stays on this tree."""

    if root <= 1:
        return set()
    children: dict[int, list[int]] = {}
    try:
        entries = os.listdir("/proc")
    except OSError:
        return set()
    for entry in entries:
        if not entry.isdigit():
            continue
        pid = int(entry)
        try:
            data = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        end = data.rfind(")")
        if end < 0:
            continue
        fields = data[end + 2 :].split()
        try:
            parent = int(fields[1])
        except (IndexError, ValueError):
            continue
        children.setdefault(parent, []).append(pid)
    found: set[int] = set()
    stack = [root]
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            if child in found or child == root:
                continue
            found.add(child)
            stack.append(child)
    if _alive(root):
        found.add(root)
    return found


def _assert_fake_and_disarmed(pid: int) -> None:
    env = _environ(pid)
    if env.get("AUREON_LIVE_TRADING") != "0":
        raise AssertionError("AUREON_LIVE_TRADING was not 0")
    for key in _FAKE_KEYS:
        if env.get(key) != "fake":
            raise AssertionError(f"{key} was not the fake string")


def _cgroup_delegation_missing() -> str:
    """Why this process cannot create and populate a child cgroup, or "".

    Probed independently of aureon.launch.session_scope so a bug there still
    fails the tests instead of skipping them: make a probe child under our own
    cgroup v2 path, move a short-lived ``sleep`` into it, confirm the move in
    /proc, then remove it. Any refusal means the host gave this user no cgroup
    delegation (for example an unprivileged sandbox or a user namespace where
    /sys/fs/cgroup is root-owned).
    """

    try:
        line = Path("/proc/self/cgroup").read_text(encoding="utf-8").strip().splitlines()
    except OSError as exc:
        return f"/proc/self/cgroup is unreadable ({exc.strerror})"
    unified = [entry.split(":", 2)[2] for entry in line if entry.startswith("0::")]
    if not unified:
        return "no cgroup v2 (unified) membership in /proc/self/cgroup"
    parent = Path("/sys/fs/cgroup") / unified[0].lstrip("/")
    if not (parent / "cgroup.procs").is_file():
        return f"cgroup v2 is not mounted at {parent}"
    if not os.access(parent / "cgroup.procs", os.W_OK):
        return f"no cgroup delegation: {parent}/cgroup.procs is not writable by uid {os.getuid()}"
    probe = parent / f"aureon-launcher-probe-{os.getpid()}"
    sleeper = None
    try:
        probe.mkdir()
    except OSError as exc:
        return f"no cgroup delegation: cannot create a child cgroup under {parent} ({exc.strerror})"
    try:
        sleeper = subprocess.Popen(["sleep", "30"])
        try:
            (probe / "cgroup.procs").write_text(str(sleeper.pid), encoding="ascii")
        except OSError as exc:
            return f"no cgroup delegation: cannot move a process into {probe} ({exc.strerror})"
        if probe.name not in _cgroup(sleeper.pid):
            return f"no cgroup delegation: process move into {probe} did not take effect"
        return ""
    finally:
        if sleeper is not None:
            sleeper.kill()
            sleeper.wait(timeout=5)
        try:
            probe.rmdir()
        except OSError:
            pass


def _systemd_user_scope_missing() -> str:
    """Why ``systemd-run --user --scope`` is unusable here, or ""."""

    if shutil.which("systemd-run") is None:
        return "systemd-run is not installed"
    try:
        proc = subprocess.run(
            ["systemd-run", "--user", "--scope", "--collect", "--quiet", "--", "true"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"systemd-run --user --scope failed to run ({exc})"
    if proc.returncode != 0:
        return f"systemd-run --user --scope exited {proc.returncode}"
    return ""


@pytest.mark.timeout(60)
def test_cgroup_kill_reaches_a_setsid_child(tmp_path: Path) -> None:
    """Scope kill, not killpg, is what reaches a setsid grandchild."""

    missing = _cgroup_delegation_missing()
    if missing:
        pytest.skip(f"needs a delegated cgroup v2 subtree for _try_cgroup: {missing}")
    pidfile = tmp_path / "setsid.pid"
    session_path = tmp_path / "session.json"
    state = tmp_path / "state"
    state.mkdir()
    script = r"""
import json
import os
import sys
import time
from pathlib import Path

os.environ["AUREON_LAUNCHER_STATE"] = sys.argv[1]
os.environ["AUREON_LAUNCHER_SETSID_PROBE"] = "1"
os.environ["AUREON_LAUNCHER_SETSID_PIDFILE"] = sys.argv[2]
from aureon.launch.session_scope import _finish_inside, _try_cgroup, current_session

unit = "aureon-launcher-fast-" + str(os.getpid())
if not _try_cgroup(unit):
    raise SystemExit("cgroup was not created")
_finish_inside()
Path(sys.argv[3]).write_text(json.dumps(current_session()), encoding="utf-8")
while True:
    time.sleep(3600)
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHON_DOTENV_DISABLED"] = "1"
    env["AUREON_LIVE_TRADING"] = "0"
    proc = subprocess.Popen(
        [sys.executable, "-c", script, str(state), str(pidfile), str(session_path)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        ready = _wait_until(
            lambda: session_path.is_file() and pidfile.is_file() and _alive(proc.pid),
            timeout=15,
        )
        if not ready:
            out, err = proc.communicate(timeout=2)
            raise AssertionError(f"scope child did not publish\n{out}\n{err}")
        setsid_pid = int(pidfile.read_text(encoding="ascii").strip())
        assert _alive(setsid_pid)
        assert os.getsid(setsid_pid) != os.getsid(proc.pid)
        assert "aureon-launcher" in _cgroup(setsid_pid)
        assert _cgroup(setsid_pid) == _cgroup(proc.pid)
        # The old kill misses this child: it is not in the parent's group.
        try:
            os.killpg(os.getpgid(proc.pid), 0)
        except OSError:
            pass
        assert os.getpgid(setsid_pid) != os.getpgid(proc.pid)
        from aureon.launch.session_scope import kill_session

        session = json.loads(session_path.read_text(encoding="utf-8"))
        report = kill_session({"session": session})
        assert "cgroup" in report["methods"]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and (_alive(proc.pid) or _alive(setsid_pid)):
            time.sleep(0.05)
        assert not _alive(setsid_pid)
        assert not _alive(proc.pid)
    finally:
        if _alive(proc.pid):
            try:
                os.kill(proc.pid, signal.SIGKILL)
            except OSError:
                pass
        if pidfile.is_file():
            try:
                stray = int(pidfile.read_text(encoding="ascii").strip())
            except ValueError:
                stray = 0
            if stray and _alive(stray):
                try:
                    os.kill(stray, signal.SIGKILL)
                except OSError:
                    pass
        proc.wait(timeout=5)


@pytest.mark.timeout(30)
def test_pid_tree_fallback_kills_a_setsid_child_without_a_cgroup(tmp_path: Path) -> None:
    """When no scope exists, signaling the pid tree still reaches setsid."""

    from aureon.launch.session_scope import descendants, kill_session

    pidfile = tmp_path / "setsid.pid"
    script = r"""
import os
import sys
import time

pidfile = sys.argv[1]
child = os.fork()
if child == 0:
    os.setsid()
    fd = os.open(pidfile, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o644)
    os.write(fd, str(os.getpid()).encode("ascii"))
    os.close(fd)
    while True:
        time.sleep(3600)
while True:
    time.sleep(3600)
"""
    proc = subprocess.Popen([sys.executable, "-c", script, str(pidfile)])
    try:
        ready = _wait_until(lambda: pidfile.is_file(), timeout=10)
        assert ready
        setsid_pid = int(pidfile.read_text(encoding="ascii").strip())
        assert setsid_pid in descendants(proc.pid)
        assert os.getpgid(setsid_pid) != os.getpgid(proc.pid)
        report = kill_session(
            {"session": {"unit": "", "cgroup": "", "root_pid": proc.pid}}
        )
        assert report["methods"] == ["pid-tree"]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and (_alive(proc.pid) or _alive(setsid_pid)):
            time.sleep(0.05)
        assert not _alive(setsid_pid)
        assert not _alive(proc.pid)
    finally:
        if _alive(proc.pid):
            os.kill(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)


def _preseed_install_shortcuts(repo: Path, python: str) -> None:
    """Let the launcher walk the full list without a package download."""

    requirements = repo / "requirements-linux.txt"
    if not requirements.is_file():
        requirements = repo / "requirements.txt"
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    venv = repo / ".venv"
    subprocess.run(
        [python, "-m", "venv", "--copies", "--system-site-packages", str(venv)],
        check=True,
        timeout=120,
    )
    leaf = venv / "bin" / "python"
    if leaf.is_symlink():
        source = leaf.resolve()
        temporary = leaf.with_name("python.aureon-copy")
        shutil.copy2(source, temporary)
        temporary.replace(leaf)
    stamp = venv / ".aureon-requirements-stamp"
    stamp.write_text(f"{requirements.name} {digest}\n", encoding="utf-8")
    if shutil.which("node") and shutil.which("npm"):
        vite = repo / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
        vite.parent.mkdir(parents=True, exist_ok=True)
        if not vite.is_file():
            vite.write_text("# launcher presence check\n", encoding="utf-8")


def _overlay_launcher_sources(clone: Path) -> None:
    """The clone is a git snapshot. Copy the session-scope sources onto it.

    A clone made before those sources are committed would otherwise boot the
    old process-group kill. Copying the checkout copies keeps the self-test
    on the code under test.
    """

    names = (
        Path("aureon/launch/session_scope.py"),
        Path("aureon/launch/master.py"),
        Path("aureon/autonomous/autonomy_mode.py"),
        Path("scripts/launch/aureon-master.sh"),
    )
    for name in names:
        source = ROOT / name
        if not source.is_file():
            continue
        target = clone / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _launcher_env(clone: Path, home: Path, site: Path, state: Path, pidfile: Path, touch: Path) -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "USERPROFILE": str(home),
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONPATH": str(site) + os.pathsep + str(clone),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHON_DOTENV_DISABLED": "1",
        "AUREON_LIVE_TRADING": "0",
        "AUREON_AUTONOMY_MODE": "guarded",
        "AUREON_LAUNCHER_STATE": str(state),
        "AUREON_LAUNCHER_SETSID_PROBE": "1",
        "AUREON_LAUNCHER_SETSID_PIDFILE": str(pidfile),
        "AUREON_DOTENV_TOUCH_LOG": str(touch),
        "AUREON_SELF_REPAIR_ENABLE": "0",
        "SERO_WORKSPACE": str(clone),
    }
    env.update(_FAKE_KEYS)
    return env


def _sweep(clone: Path, launcher_pid: int) -> None:
    tokens = (str(clone),)
    try:
        entries = os.listdir("/proc")
    except OSError:
        entries = []
    for entry in entries:
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid == os.getpid():
            continue
        parts = _cmdline(pid)
        text = " ".join(parts)
        cwd = ""
        try:
            cwd = os.readlink(f"/proc/{pid}/cwd")
        except OSError:
            cwd = ""
        if any(token in text or token in cwd for token in tokens) or pid == launcher_pid:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    if launcher_pid > 1:
        for pid in list(_descendant_pids(launcher_pid)):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass


@pytest.mark.timeout(300)
def test_full_launcher_kill_switch_leaves_no_survivors(tmp_path: Path) -> None:
    """Start the full launcher and assert the kill switch clears every pid."""

    # The assertions below require the launcher session to land in an
    # aureon-launcher cgroup, which it can only do through direct cgroup
    # delegation or a systemd user scope. The no-cgroup path is covered by
    # test_pid_tree_fallback_kills_a_setsid_child_without_a_cgroup.
    direct = _cgroup_delegation_missing()
    scope = _systemd_user_scope_missing() if direct else ""
    if direct and scope:
        pytest.skip(f"needs a delegated cgroup v2 subtree or a systemd user scope: {direct}; {scope}")
    clone = tmp_path / "clone"
    cloned = subprocess.run(
        ["git", "clone", "--no-hardlinks", "--shared", str(ROOT), str(clone)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if cloned.returncode != 0:
        pytest.fail(cloned.stderr or cloned.stdout or "git clone failed")
    home = tmp_path / "home"
    home.mkdir()
    site = tmp_path / "site"
    site.mkdir()
    (site / "sitecustomize.py").write_text(_SITECUSTOMIZE, encoding="utf-8")
    state = tmp_path / "launcher-state"
    state.mkdir()
    pidfile = tmp_path / "setsid.pid"
    touch = tmp_path / "dotenv-touch.log"
    _overlay_launcher_sources(clone)
    _preseed_install_shortcuts(clone, sys.executable)
    env = _launcher_env(clone, home, site, state, pidfile, touch)
    log_path = tmp_path / "launcher.log"
    log_handle = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "aureon.launch.master", "--root", str(clone)],
        cwd=str(clone),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    setsid_pid = 0
    trader_pid = 0
    snapshot: set[int] = set()
    try:
        seen = {"trader": 0, "setsid": 0}

        def _ready() -> bool:
            if pidfile.is_file():
                try:
                    seen["setsid"] = int(pidfile.read_text(encoding="ascii").strip())
                except ValueError:
                    pass
            found = _find_trader()
            if found:
                seen["trader"] = found
            return bool(
                seen["setsid"]
                and seen["trader"]
                and _alive(seen["setsid"])
                and _alive(seen["trader"])
            )

        ready = _wait_until(_ready, timeout=180)
        if not ready:
            text = log_path.read_text(encoding="utf-8", errors="replace")
            trader_lines = [
                line for line in text.splitlines() if "unified_market_trader" in line or "setsid" in line
            ]
            trader_log = state / "logs" / "organ_unified_market_trader.log"
            trader_tail = ""
            if trader_log.is_file():
                trader_tail = trader_log.read_text(encoding="utf-8", errors="replace")[-1500:]
            raise AssertionError(
                "full launcher did not keep unified_market_trader and the setsid child alive\n"
                f"seen trader={seen['trader']} alive={_alive(seen['trader'])} "
                f"setsid={seen['setsid']} alive={_alive(seen['setsid'])} pidfile={pidfile.is_file()}\n"
                + "\n".join(trader_lines[-20:])
                + "\n"
                + trader_tail
            )
        setsid_pid = int(pidfile.read_text(encoding="ascii").strip())
        trader_pid = int(_find_trader() or 0)
        assert setsid_pid > 1
        assert trader_pid > 1
        assert _alive(setsid_pid)
        assert _alive(trader_pid)
        assert os.getsid(setsid_pid) == setsid_pid
        assert os.getpgid(setsid_pid) != os.getpgid(trader_pid)
        state_file = state / "pids.json"
        payload = json.loads(state_file.read_text(encoding="utf-8")) if state_file.is_file() else {}
        session = payload.get("session") or {}
        cgroup = str(session.get("cgroup") or "")
        assert "aureon-launcher" in cgroup
        assert Path(cgroup).name in _cgroup(setsid_pid)
        assert Path(cgroup).name in _cgroup(trader_pid)
        assert _cgroup(setsid_pid) == _cgroup(trader_pid)
        _assert_fake_and_disarmed(trader_pid)
        if touch.is_file() and touch.read_text(encoding="utf-8").strip():
            raise AssertionError("a process opened a dotenv file")
        snapshot = {setsid_pid, trader_pid}
        if _alive(proc.pid):
            snapshot.add(proc.pid)
            snapshot |= _descendant_pids(proc.pid)
        procs = Path(cgroup) / "cgroup.procs"
        if procs.is_file():
            for line in procs.read_text(encoding="ascii", errors="replace").splitlines():
                if line.strip().isdigit():
                    snapshot.add(int(line.strip()))
        assert setsid_pid in snapshot
        assert trader_pid in snapshot
        stopped = subprocess.run(
            [sys.executable, "-m", "aureon.launch.master", "--stop", "--root", str(clone)],
            cwd=str(clone),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert stopped.returncode == 0, stopped.stderr
        deadline = time.monotonic() + 8
        survivors = [pid for pid in snapshot if _alive(pid)]
        while survivors and time.monotonic() < deadline:
            time.sleep(0.1)
            survivors = [pid for pid in snapshot if _alive(pid)]
        named = []
        if _alive(setsid_pid):
            named.append(f"setsid child {setsid_pid}")
        if _alive(trader_pid):
            named.append(f"unified_market_trader {trader_pid}")
        if named or survivors:
            raise AssertionError(
                "kill switch left survivors: "
                + ", ".join(named + [str(pid) for pid in survivors])
            )
        assert not _alive(setsid_pid)
        assert not _alive(trader_pid)
        assert survivors == []
    finally:
        log_handle.close()
        _sweep(clone, proc.pid)
        try:
            subprocess.run(
                [sys.executable, "-m", "aureon.launch.master", "--stop", "--root", str(clone)],
                cwd=str(clone),
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        if _alive(proc.pid):
            try:
                os.kill(proc.pid, signal.SIGKILL)
            except OSError:
                pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
