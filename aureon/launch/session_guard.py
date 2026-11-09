"""One containment unit for a master-launcher session.

Killing the launcher's process group does not reach a child that has called
``setsid``. ``PDEATHSIG`` does not either: a new session leader is not
signalled when the old parent dies. This module puts the session in one
unit and checks, by pid, that the unit is empty after a stop.

Order of preference:

* ``systemd-run --scope`` when PID 1 is systemd and a probe scope accepts
  the caller's environment
* a cgroup v2 directory under the current cgroup, torn down with
  ``cgroup.kill``
* a psutil walk of every descendant, remembered with its ``/proc`` start
  tick so a recycled pid is not signalled

The watchdog is the one process that leaves the launcher session. It has
to stay alive when that process group is killed, then tear the unit down.
``--stop`` does the same from outside the unit and writes the survivor list.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, IO

SCHEMA = "aureon.launch.session.v1"
_ACTIVE: dict[str, Any] | None = None


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _state_path(state_dir: Path) -> Path:
    return state_dir / "containment.json"


def _lock_path(state_dir: Path) -> Path:
    return state_dir / "containment.lock"


def _report_path(state_dir: Path) -> Path:
    return state_dir / "survivors.txt"


def _kill_path(state_dir: Path) -> Path:
    return state_dir / "KILL"


def _locked(state_dir: Path) -> IO[str]:
    state_dir.mkdir(parents=True, exist_ok=True)
    handle = _lock_path(state_dir).open("a+", encoding="utf-8")
    try:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    except (ImportError, OSError):
        pass
    return handle


def _read(state_dir: Path) -> dict[str, Any]:
    path = _state_path(state_dir)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write(state_dir: Path, payload: dict[str, Any]) -> None:
    path = _state_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _update(state_dir: Path, mutator: Any) -> dict[str, Any]:
    handle = _locked(state_dir)
    try:
        payload = _read(state_dir)
        mutator(payload)
        payload["schema"] = SCHEMA
        payload["updated_at"] = _now()
        _write(state_dir, payload)
        return payload
    finally:
        handle.close()


def _self_cgroup() -> Path | None:
    try:
        text = Path("/proc/self/cgroup").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        if line.startswith("0::"):
            relative = line.split(":", 2)[-1].lstrip("/")
            path = Path("/sys/fs/cgroup") / relative
            if (path / "cgroup.procs").is_file():
                return path
    return None


def _safe_cgroup(path: Path | None) -> bool:
    """True only for a unit this module created. Never the host cgroup root."""

    if path is None:
        return False
    try:
        resolved = path.resolve()
    except OSError:
        return False
    if resolved == Path("/sys/fs/cgroup") or not resolved.name.startswith("aureon-master-"):
        return False
    return (resolved / "cgroup.procs").is_file()


def _cgroup_members(path: Path | None) -> set[int]:
    if not _safe_cgroup(path):
        return set()
    assert path is not None
    try:
        text = (path / "cgroup.procs").read_text(encoding="utf-8")
    except OSError:
        return set()
    found: set[int] = set()
    for line in text.split():
        if line.isdigit():
            found.add(int(line))
    return found


def _move_pid(path: Path, pid: int) -> bool:
    if not _safe_cgroup(path):
        return False
    try:
        (path / "cgroup.procs").write_text(str(pid), encoding="utf-8")
    except OSError:
        return False
    return pid in _cgroup_members(path)


def _start_ticks(pid: int) -> int | None:
    """Kernel start tick from ``/proc/<pid>/stat``. Stable across the pid's life."""

    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        rest = stat.rsplit(")", 1)[-1].split()
        # Field 22 (starttime) is the 20th field after the comm closing paren.
        return int(rest[19])
    except (OSError, IndexError, ValueError):
        return None


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
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        rest = stat.rsplit(")", 1)[-1].split()
        if rest and rest[0] == "Z":
            return False
    except (OSError, IndexError):
        return False
    return True


def _same_process(pid: int, started: int | None) -> bool:
    if not _alive(pid):
        return False
    if started is None:
        return False
    return _start_ticks(pid) == started


def _is_watchdog(pid: int) -> bool:
    command = _cmdline(pid)
    return "aureon.launch.session_guard" in command and "--watch" in command


def _cmdline(pid: int) -> str:
    try:
        import psutil

        try:
            return " ".join(psutil.Process(pid).cmdline())
        except (psutil.Error, OSError):
            pass
    except ImportError:
        pass
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()


def _proc_children() -> dict[int, list[int]]:
    children: dict[int, list[int]] = {}
    proc = Path("/proc")
    try:
        entries = list(proc.iterdir())
    except OSError:
        return children
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text(encoding="utf-8")
            rest = stat.rsplit(")", 1)[-1].split()
            parent = int(rest[1])
        except (OSError, IndexError, ValueError):
            continue
        children.setdefault(parent, []).append(int(entry.name))
    return children


def _psutil_descendants(roots: set[int]) -> set[int]:
    """Every live descendant psutil can see, including a child that called setsid."""

    try:
        import psutil
    except ImportError:
        return set()
    found: set[int] = set()
    for root in list(roots):
        try:
            process = psutil.Process(root)
        except (psutil.Error, OSError):
            continue
        try:
            kids = process.children(recursive=True)
        except (psutil.Error, OSError):
            kids = []
        for kid in kids:
            try:
                found.add(int(kid.pid))
            except (psutil.Error, OSError, ValueError):
                continue
    return found


def _walk_descendants(roots: set[int]) -> set[int]:
    found = set(roots)
    found |= _psutil_descendants(roots)
    children = _proc_children()
    stack = list(found)
    seen: set[int] = set()
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        for child in children.get(pid, []):
            if child not in found:
                found.add(child)
                stack.append(child)
    return found


def _normalise_pids(payload: dict[str, Any]) -> list[dict[str, int]]:
    rows: list[dict[str, int]] = []
    seen: set[int] = set()
    for item in payload.get("pids") or []:
        if isinstance(item, dict):
            try:
                pid = int(item.get("pid") or 0)
            except (TypeError, ValueError):
                continue
            started = item.get("start")
            try:
                start = int(started) if started is not None else -1
            except (TypeError, ValueError):
                start = -1
        else:
            try:
                pid = int(item)
            except (TypeError, ValueError):
                continue
            start = -1
        if pid <= 1 or pid in seen:
            continue
        seen.add(pid)
        row: dict[str, int] = {"pid": pid}
        if start >= 0:
            row["start"] = start
        rows.append(row)
    return rows


def note_pid(pid: int) -> None:
    """Remember a child spawned by the active session. No-op when none is open."""

    if _ACTIVE is None or pid <= 1:
        return
    state_dir = Path(str(_ACTIVE.get("state_dir") or ""))
    if not state_dir:
        return
    started = _start_ticks(pid)

    def mutate(payload: dict[str, Any]) -> None:
        rows = _normalise_pids(payload)
        if any(row["pid"] == pid for row in rows):
            return
        row: dict[str, int] = {"pid": pid}
        if started is not None:
            row["start"] = started
        rows.append(row)
        payload["pids"] = rows

    try:
        _update(state_dir, mutate)
    except OSError:
        return


def _systemd_available() -> bool:
    if os.name == "nt":
        return False
    if not shutil_which("systemd-run") or not shutil_which("systemctl"):
        return False
    try:
        comm = Path("/proc/1/comm").read_text(encoding="utf-8").strip()
    except OSError:
        return False
    return comm == "systemd"


def shutil_which(name: str) -> str | None:
    from shutil import which

    return which(name)


def maybe_reexec(argv: list[str]) -> None:
    """Re-exec under ``systemd-run --scope`` once, when that probe succeeds."""

    if os.name == "nt" or os.environ.get("AUREON_SESSION_CONTAINED") == "1":
        return
    if not _systemd_available():
        return
    systemd_run = shutil_which("systemd-run")
    if not systemd_run:
        return
    probe_unit = f"aureon-probe-{os.getpid()}"
    probe_env = dict(os.environ)
    probe_env["AUREON_SYSTEMD_PROBE"] = probe_unit
    try:
        probe = subprocess.run(
            [
                systemd_run,
                "--scope",
                "--collect",
                f"--unit={probe_unit}",
                "--quiet",
                "--",
                sys.executable,
                "-c",
                "import os,sys; sys.exit(0 if os.environ.get('AUREON_SYSTEMD_PROBE') else 1)",
            ],
            env=probe_env,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return
    if probe.returncode != 0:
        return
    unit = f"aureon-master-{os.getpid()}"
    child_env = dict(os.environ)
    child_env.pop("AUREON_SYSTEMD_PROBE", None)
    child_env["AUREON_SESSION_CONTAINED"] = "1"
    child_env["AUREON_SESSION_UNIT"] = unit
    command = [
        systemd_run,
        "--scope",
        "--collect",
        f"--unit={unit}",
        "--quiet",
        "--",
        sys.executable,
        "-m",
        "aureon.launch.master",
        *argv,
    ]
    try:
        code = subprocess.call(command, env=child_env)
    except OSError:
        return
    raise SystemExit(code)


def _make_cgroup(launcher_pid: int) -> Path | None:
    parent = _self_cgroup()
    if parent is None:
        return None
    child = parent / f"aureon-master-{launcher_pid}"
    try:
        child.mkdir(exist_ok=True)
    except OSError:
        return None
    if not _safe_cgroup(child):
        return None
    return child


def open_session(state_dir: Path) -> dict[str, Any]:
    """Open the unit and start the watchdog outside the launcher's group."""

    global _ACTIVE
    if os.name == "nt":
        return {}
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    launcher_pid = os.getpid()
    cgroup = _make_cgroup(launcher_pid)
    mode = "cgroup-v2" if cgroup is not None else "pid-tree"
    unit = os.environ.get("AUREON_SESSION_UNIT") or ""
    if unit and mode == "pid-tree":
        mode = "systemd-scope"
    payload = {
        "schema": SCHEMA,
        "mode": mode,
        "unit": unit,
        "cgroup": str(cgroup) if cgroup is not None else "",
        "launcher_pid": launcher_pid,
        "launcher_start": _start_ticks(launcher_pid),
        "watchdog_pid": 0,
        "pids": [],
        "clean_release": False,
        "tracker": "psutil" if _psutil_present() else "proc",
    }
    _update(state_dir, lambda current: current.update(payload))
    _ACTIVE = {"state_dir": str(state_dir)}
    watchdog_pid = _spawn_watchdog(state_dir, launcher_pid)
    if cgroup is not None:
        _move_pid(cgroup, launcher_pid)

    def mutate(current: dict[str, Any]) -> None:
        current["watchdog_pid"] = watchdog_pid
        current["mode"] = mode
        current["cgroup"] = str(cgroup) if cgroup is not None else ""
        current["launcher_pid"] = launcher_pid

    opened = _update(state_dir, mutate)
    _arm_signals(state_dir)
    return opened


def _psutil_present() -> bool:
    try:
        import psutil  # noqa: F401
    except ImportError:
        return False
    return True


def _spawn_watchdog(state_dir: Path, launcher_pid: int) -> int:
    """Leave the launcher session. This is the one ``setsid`` the unit needs."""

    log_path = state_dir / "watchdog.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("ab")
    try:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "aureon.launch.session_guard",
                "--watch",
                str(state_dir),
                "--launcher",
                str(launcher_pid),
            ],
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.STDOUT,
        )
    finally:
        handle.close()
    return int(proc.pid)


def _arm_signals(state_dir: Path) -> None:
    def handler(signum: int, _frame: Any) -> None:
        try:
            kill_and_verify(state_dir)
        finally:
            raise SystemExit(128 + int(signum))

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)


def mark_clean_release(state_dir: Path) -> None:
    """A normal launcher exit. The watchdog must not tear the unit down."""

    def mutate(payload: dict[str, Any]) -> None:
        payload["clean_release"] = True

    try:
        _update(Path(state_dir), mutate)
    except OSError:
        return


def _recorded(payload: dict[str, Any]) -> list[dict[str, int]]:
    return _normalise_pids(payload)


def _exclude(payload: dict[str, Any]) -> set[int]:
    excluded = {os.getpid(), 0, 1}
    try:
        watchdog = int(payload.get("watchdog_pid") or 0)
    except (TypeError, ValueError):
        watchdog = 0
    if watchdog > 1:
        excluded.add(watchdog)
    return excluded


def _targets(payload: dict[str, Any]) -> set[int]:
    excluded = _exclude(payload)
    cgroup = Path(str(payload.get("cgroup") or "")) if payload.get("cgroup") else None
    matched: set[int] = set()
    for row in _recorded(payload):
        pid = row["pid"]
        if pid in excluded:
            continue
        started = row.get("start")
        if started is None or _same_process(pid, int(started)):
            if _alive(pid):
                matched.add(pid)
    launcher = int(payload.get("launcher_pid") or 0)
    launcher_start = payload.get("launcher_start")
    try:
        launcher_tick = int(launcher_start) if launcher_start is not None else None
    except (TypeError, ValueError):
        launcher_tick = None
    if launcher > 1 and launcher not in excluded and _alive(launcher):
        if launcher_tick is None or _start_ticks(launcher) == launcher_tick:
            matched.add(launcher)
    found = _walk_descendants(matched)
    for pid in _cgroup_members(cgroup):
        if pid not in excluded:
            found.add(pid)
    return {pid for pid in found if pid not in excluded and _alive(pid) and not _is_watchdog(pid)}


def _signal_many(pids: set[int], sig: int) -> None:
    for pid in list(pids):
        if pid <= 1 or pid == os.getpid():
            continue
        try:
            group = os.getpgid(pid)
        except OSError:
            group = pid
        # A setsid child is its own group leader. killpg reaches that group
        # only. Never signal the caller's group.
        if group == pid and group != os.getpgrp():
            try:
                os.killpg(group, sig)
                continue
            except OSError:
                pass
        try:
            os.kill(pid, sig)
        except OSError:
            continue


def _reap() -> None:
    while True:
        try:
            pid, _status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        except OSError:
            return
        if pid == 0:
            return


def _cgroup_kill(path: Path | None) -> None:
    if not _safe_cgroup(path):
        return
    assert path is not None
    if os.getpid() in _cgroup_members(path):
        return
    kill_file = path / "cgroup.kill"
    try:
        if kill_file.is_file():
            kill_file.write_text("1", encoding="utf-8")
    except OSError:
        return


def _stop_systemd(unit: str) -> None:
    if not unit or not shutil_which("systemctl"):
        return
    systemctl = shutil_which("systemctl")
    if not systemctl:
        return
    name = unit if unit.endswith(".scope") else f"{unit}.scope"
    for command in (
        [systemctl, "stop", name],
        [systemctl, "--user", "stop", name],
    ):
        try:
            subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue


def kill_pid_tree(pid: int) -> None:
    """Signal one recorded pid and the descendants psutil can still see."""

    if pid <= 1 or pid == os.getpid() or not _alive(pid):
        return
    targets = _walk_descendants({pid})
    targets.add(pid)
    targets.discard(os.getpid())
    _signal_many(targets, signal.SIGTERM)
    time.sleep(0.2)
    _signal_many({item for item in targets if _alive(item)}, signal.SIGKILL)
    _reap()


def _describe(pids: set[int]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for pid in sorted(pids):
        if not _alive(pid):
            continue
        rows.append({"pid": str(pid), "cmd": _cmdline(pid) or "unknown"})
    return rows


def kill_and_verify(state_dir: Path) -> list[dict[str, str]]:
    """Tear the unit down and return any pid that is still alive."""

    state_dir = Path(state_dir)
    payload = _read(state_dir)
    if not payload:
        text = format_survivor_report([], mode="")
        _report_path(state_dir).write_text(text, encoding="utf-8")
        return []
    _stop_systemd(str(payload.get("unit") or ""))
    cgroup_text = str(payload.get("cgroup") or "")
    cgroup = Path(cgroup_text) if cgroup_text else None
    for _round in range(6):
        payload = _read(state_dir)
        targets = _targets(payload)
        if not targets and not any(pid not in _exclude(payload) for pid in _cgroup_members(cgroup)):
            break
        sig = signal.SIGTERM if _round == 0 else signal.SIGKILL
        _signal_many(targets, sig)
        _reap()
        time.sleep(0.25)
        _cgroup_kill(cgroup)
        time.sleep(0.25)
    payload = _read(state_dir)
    survivors = _describe(_targets(payload))
    text = format_survivor_report(survivors, mode=str(payload.get("mode") or ""))
    try:
        _report_path(state_dir).write_text(text, encoding="utf-8")
    except OSError:
        pass
    if _safe_cgroup(cgroup) and cgroup is not None and not _cgroup_members(cgroup):
        try:
            cgroup.rmdir()
        except OSError:
            pass
    return survivors


def format_survivor_report(survivors: list[dict[str, str]], mode: str = "") -> str:
    lines = [
        f"containment_mode={mode or 'unknown'}",
        f"containment_survivors={len(survivors)}",
        "survivor_list:",
    ]
    if not survivors:
        lines.append("(none)")
    else:
        for item in survivors:
            lines.append(f"pid={item.get('pid', '')} cmd={item.get('cmd', '')}")
    return "\n".join(lines) + "\n"


def survivor_lines(survivors: list[dict[str, str]], mode: str = "") -> list[str]:
    return [line for line in format_survivor_report(survivors, mode=mode).splitlines() if line]


def stop_session(state_dir: Path) -> list[dict[str, str]]:
    """Stop command entry. Kills the unit recorded for this launcher state."""

    return kill_and_verify(Path(state_dir))


def _snapshot(state_dir: Path, launcher_pid: int) -> None:
    payload = _read(state_dir)
    roots = {launcher_pid}
    for row in _recorded(payload):
        roots.add(row["pid"])
    descendants = _walk_descendants(roots)

    def mutate(current: dict[str, Any]) -> None:
        rows = _normalise_pids(current)
        known = {row["pid"] for row in rows}
        for pid in descendants:
            if pid == launcher_pid or pid in known or pid <= 1:
                continue
            if not _alive(pid) or _is_watchdog(pid):
                continue
            row: dict[str, int] = {"pid": pid}
            started = _start_ticks(pid)
            if started is not None:
                row["start"] = started
            rows.append(row)
            known.add(pid)
        current["pids"] = rows

    _update(state_dir, mutate)


def watch(state_dir: Path, launcher_pid: int) -> int:
    """Stay up after the launcher group dies, then verify zero survivors."""

    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    state_dir = Path(state_dir)
    for _wait in range(50):
        if _state_path(state_dir).is_file():
            break
        time.sleep(0.05)
    while _alive(launcher_pid) and not _kill_path(state_dir).is_file():
        try:
            _snapshot(state_dir, launcher_pid)
        except OSError:
            pass
        time.sleep(0.25)
    time.sleep(0.4)
    payload = _read(state_dir)
    if payload.get("clean_release") is True and not _kill_path(state_dir).is_file():
        return 0
    survivors = kill_and_verify(state_dir)
    return 0 if not survivors else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aureon.launch.session_guard")
    parser.add_argument("--watch", required=True, help="launcher state directory")
    parser.add_argument("--launcher", required=True, type=int, help="launcher pid to watch")
    args = parser.parse_args(argv)
    return watch(Path(args.watch), int(args.launcher))


if __name__ == "__main__":
    raise SystemExit(main())
