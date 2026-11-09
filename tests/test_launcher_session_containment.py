"""A launcher kill must leave no child alive, including one that called setsid.

The full-launcher case starts ``aureon.launch.master`` with fake exchange keys
inside a network namespace that has no external interface. It plants one
deliberate ``setsid`` child, kills the launcher, and prints every survivor.
``unified_market_trader`` has to be one of the processes that was running,
and it has to be gone afterwards.
"""

from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_FAKE_KEY = "not-a-real-key"
_FAKE_SECRET = "not-a-real-secret"


def _cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", "replace")


def _alive(pid: int) -> bool:
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        rest = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[-1].split()
    except OSError:
        return False
    return not rest or rest[0] != "Z"


def _descendants(root: int) -> set[int]:
    """ppid walk. Kept here so a pin finder left on the test process cannot block it."""

    children: dict[int, list[int]] = {}
    proc = Path("/proc")
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            rest = (entry / "stat").read_text(encoding="utf-8").rsplit(")", 1)[-1].split()
            parent = int(rest[1])
        except (OSError, IndexError, ValueError):
            continue
        children.setdefault(parent, []).append(int(entry.name))
    found = {root}
    stack = [root]
    while stack:
        pid = stack.pop()
        for child in children.get(pid, []):
            if child not in found:
                found.add(child)
                stack.append(child)
    return found


def _stop_recorded(state: Path) -> str:
    """Fresh interpreter. The test process may be pinning aureon imports."""

    code = (
        "import sys\n"
        "from pathlib import Path\n"
        "from aureon.launch.session_guard import stop_session\n"
        "stop_session(Path(sys.argv[1]))\n"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    subprocess.run(
        [sys.executable, "-c", code, str(state)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    report = state / "survivors.txt"
    return report.read_text(encoding="utf-8") if report.is_file() else ""


def _external_ifaces(pid: int) -> list[str]:
    try:
        lines = Path(f"/proc/{pid}/net/dev").read_text(encoding="utf-8").splitlines()
    except OSError:
        return ["unreadable"]
    names: list[str] = []
    for line in lines[2:]:
        name = line.split(":", 1)[0].strip()
        if name and name != "lo":
            names.append(name)
    return names


def test_master_spawn_stays_in_the_launcher_session() -> None:
    master = (ROOT / "aureon" / "launch" / "master.py").read_text(encoding="utf-8")
    guard = (ROOT / "aureon" / "launch" / "session_guard.py").read_text(encoding="utf-8")
    assert "start_new_session" not in master
    assert guard.count("start_new_session=True") == 1


def test_group_kill_reaps_a_setsid_child(tmp_path: Path) -> None:
    """Kill the leader's process group. The setsid child has to die with it."""

    state = tmp_path / "state"
    state.mkdir()
    script_path = tmp_path / "leader.py"
    script_path.write_text(
        textwrap.dedent(
            """\
            import os
            import sys
            import time
            from pathlib import Path

            from aureon.launch.session_guard import note_pid, open_session

            open_session(Path(sys.argv[1]))
            pid = os.fork()
            if pid == 0:
                os.setsid()
                os.execv(
                    sys.executable,
                    [sys.executable, "-c", "import time\\n# aureon-containment-canary\\ntime.sleep(3600)\\n"],
                )
            note_pid(pid)
            time.sleep(3600)
            """
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    out_handle = (tmp_path / "leader.out").open("wb")
    err_handle = (tmp_path / "leader.err").open("wb")
    proc = subprocess.Popen(
        [sys.executable, str(script_path), str(state)],
        cwd=str(ROOT),
        env=env,
        start_new_session=True,
        stdout=out_handle,
        stderr=err_handle,
    )
    canary = 0
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            for entry in Path("/proc").iterdir():
                if not entry.name.isdigit():
                    continue
                pid = int(entry.name)
                if "aureon-containment-canary" in _cmdline(pid) and _alive(pid):
                    canary = pid
                    break
            if canary and (state / "containment.json").is_file():
                break
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        detail = (
            f"returncode={proc.poll()}\n"
            + (tmp_path / "leader.out").read_text(encoding="utf-8", errors="replace")
            + (tmp_path / "leader.err").read_text(encoding="utf-8", errors="replace")
        )
        assert canary, "setsid canary did not start:\n" + detail
        assert canary != proc.pid
        assert _external_group(proc.pid, canary)
        os.killpg(proc.pid, signal.SIGKILL)
        deadline = time.time() + 10
        while time.time() < deadline and _alive(canary):
            time.sleep(0.1)
        report = _stop_recorded(state)
        print(report)
        assert not _alive(canary), f"setsid canary {canary} survived\n{report}"
        assert "containment_survivors=0" in report
        assert "(none)" in report
    finally:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
        if canary and _alive(canary):
            try:
                os.kill(canary, signal.SIGKILL)
            except OSError:
                pass
        _stop_recorded(state)


def _external_group(leader: int, child: int) -> bool:
    try:
        return os.getpgid(leader) != os.getpgid(child)
    except OSError:
        return False


def _preseed_offline_tools(clone: Path, python: str) -> None:
    """Skip network installs. Children still run on the interpreter under test."""

    requirements = clone / "requirements-linux.txt"
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    venv = clone / ".venv"
    bindir = venv / "bin"
    bindir.mkdir(parents=True)
    script = bindir / "python"
    script.write_text(f"#!/bin/sh\nexec {python} \"$@\"\n", encoding="utf-8")
    script.chmod(0o755)
    (venv / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
    (venv / ".aureon-requirements-stamp").write_text(
        f"requirements-linux.txt {digest}\n",
        encoding="utf-8",
    )
    vite = clone / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
    vite.parent.mkdir(parents=True, exist_ok=True)
    if not vite.is_file():
        vite.write_text("// containment self-test placeholder\n", encoding="utf-8")


@pytest.mark.timeout(420)
def test_full_launcher_kill_leaves_no_survivors(tmp_path: Path) -> None:
    """Start the real launcher, kill it, and list whoever is left."""

    unshare = subprocess.run(["unshare", "--version"], capture_output=True, text=True, check=False)
    if unshare.returncode != 0:
        pytest.fail("unshare is required so the keyed launcher has no network")
    clone = tmp_path / "clone"
    cloned = subprocess.run(
        ["git", "clone", "--no-hardlinks", "--shared", str(ROOT), str(clone)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if cloned.returncode != 0:
        pytest.fail(cloned.stderr)
    _preseed_offline_tools(clone, sys.executable)
    state = tmp_path / "launcher-state"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(clone)
    env["AUREON_LAUNCHER_STATE"] = str(state)
    env["AUREON_LAUNCH_SETSID_CANARY"] = "1"
    env["AUREON_LIVE_TRADING"] = "0"
    env["KRAKEN_API_KEY"] = _FAKE_KEY
    env["KRAKEN_API_SECRET"] = _FAKE_SECRET
    for name in (
        "BINANCE_API_KEY",
        "BINANCE_API_SECRET",
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
        "CAPITAL_API_KEY",
        "CAPITAL_IDENTIFIER",
        "CAPITAL_PASSWORD",
        "AUREON_AUTONOMY_MODE",
        "AUREON_FUSION_ARM_LIVE",
    ):
        env.pop(name, None)
    stdout_path = tmp_path / "launcher.out"
    stderr_path = tmp_path / "launcher.err"
    stdout_handle = stdout_path.open("wb")
    stderr_handle = stderr_path.open("wb")
    proc = subprocess.Popen(
        ["unshare", "--user", "--map-root-user", "--net", sys.executable, "-m", "aureon.launch.master"],
        cwd=str(clone),
        env=env,
        start_new_session=True,
        stdout=stdout_handle,
        stderr=stderr_handle,
    )
    trader = 0
    canary = 0
    try:
        deadline = time.time() + 10
        ifaces = _external_ifaces(proc.pid)
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            ifaces = _external_ifaces(proc.pid)
            if ifaces == []:
                break
            time.sleep(0.05)
        assert proc.poll() is None, stderr_path.read_text(encoding="utf-8", errors="replace")[-2000:]
        assert ifaces == [], f"launcher network was not blocked: {ifaces}"
        deadline = time.time() + 180
        while time.time() < deadline:
            descendants = _descendants(proc.pid)
            for pid in descendants:
                command = _cmdline(pid)
                if "aureon.exchanges.unified_market_trader" in command and _alive(pid):
                    trader = pid
                if "aureon-containment-canary" in command and _alive(pid):
                    canary = pid
            if trader and canary:
                break
            if proc.poll() is not None:
                break
            time.sleep(0.25)
        launcher_out = stdout_path.read_text(encoding="utf-8", errors="replace")[-2000:]
        launcher_err = stderr_path.read_text(encoding="utf-8", errors="replace")[-2000:]
        assert trader, f"unified_market_trader did not start\n{launcher_out}\n{launcher_err}"
        assert canary, f"setsid canary did not start\n{launcher_out}\n{launcher_err}"
        assert _alive(trader)
        assert _alive(canary)
        os.killpg(proc.pid, signal.SIGKILL)
        gone = time.time() + 15
        while time.time() < gone and (_alive(trader) or _alive(canary) or _alive(proc.pid)):
            time.sleep(0.1)
        stop_out = tmp_path / "stop.out"
        stop_err = tmp_path / "stop.err"
        stopped = subprocess.run(
            [sys.executable, "-m", "aureon.launch.master", "--stop", "--root", str(clone)],
            cwd=str(clone),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        stop_out.write_text(stopped.stdout, encoding="utf-8")
        stop_err.write_text(stopped.stderr, encoding="utf-8")
        report_path = state / "survivors.txt"
        report = report_path.read_text(encoding="utf-8") if report_path.is_file() else stopped.stdout
        print("unified_market_trader pid", trader, "alive", _alive(trader))
        print("setsid canary pid", canary, "alive", _alive(canary))
        print(report)
        print(stopped.stdout)
        assert _FAKE_KEY not in report
        assert _FAKE_SECRET not in report
        assert not _alive(trader), f"unified_market_trader survived\n{report}"
        assert not _alive(canary), f"setsid canary survived\n{report}"
        assert "containment_survivors=0" in report
        assert "(none)" in report
        assert "unified_market_trader" not in report
        assert stopped.returncode == 0
    finally:
        stdout_handle.close()
        stderr_handle.close()
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
        for pid in (trader, canary):
            if pid and _alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
        subprocess.run(
            [sys.executable, "-m", "aureon.launch.master", "--stop", "--root", str(clone)],
            cwd=str(clone),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
