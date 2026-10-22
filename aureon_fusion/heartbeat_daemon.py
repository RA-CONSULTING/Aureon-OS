"""💓 Heartbeat Daemon — the HEARTBEAT scheduler organ (Track A).

heartbeat_exec.run() executes the fused HEARTBEAT checklist ONCE and exits;
this daemon is its scheduler. Every 300 s cycle it runs, in order, each step
independently guarded (one failure never aborts the loop or the daemon):

  1. aureon_fusion.heartbeat_exec.run() — the full 7-check HEARTBEAT
     (sero_autonomous_expansion health cycle, Schumann field probe via
     SchumannFeel.take_reading which persists into sero_feel/, space
     weather, upstream sync, conscience audit, trading pulse, queen_mind
     snapshot). Refreshes state/heartbeat_last_results.json every cycle so
     queen_mind never again reads stale results as live state.
  2. solar_system_temporal_bridge.merge_solar_into_temporal() — workspace
     orphan tool, imported with the workspace root on sys.path.
  3. real_data_feeds.RealDataFeeds().fetch_all() — GDACS/NASA/NOAA batch
     fetch, executed on a background worker thread with skip-if-busy so a
     slow or offline network batch never delays or overlaps cycles. The
     module keeps its own cache dumps and staleness semantics; failures are
     logged and the loop continues (fail-closed).
  4. Respawn-on-death watch (WATCH list) — checked at the top of every
     cycle: if a watched long-run door process (currently only
     planetary_switchboard) has died while the sovereign holds its door
     open, it is respawned with master_key's exact spawn contract (pid
     file JSON, door-log append, suppression env); a deliberately closed
     door stands the watcher down.

Every stdout line the daemon itself emits carries a UTC timestamp; output
produced by the inner steps is captured and re-emitted with the same prefix
so the organ log stays uniformly timestamped. SIGTERM/SIGINT shut the loop
down gracefully between steps. Import-safe: nothing runs at import time.
"""

import contextlib
import io
import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

from .paths import WORKSPACE, FUSION_STATE  # noqa: E402
from . import heartbeat_exec  # noqa: E402

CYCLE_S = 300.0

_STOP = threading.Event()
_FEED_THREAD = None  # real_data_feeds worker; skip-if-busy guard

# Respawn-on-death watch list: long-run door processes whose silent death
# used to leave an input band dark until a master_key cycle happened to
# notice. Each entry mirrors master_key's long-run spawn contract (same pid
# file JSON, same door-log append, same suppression env). A door is revived
# ONLY while the sovereign holds it open — a deliberate close in the door
# journal stands the watcher down; her will is never overridden.
WATCH = [
    {
        "name": "planetary_switchboard",
        "cmd": [sys.executable, "-u",
                str(WORKSPACE / "aureon_radar" / "planetary_switchboard.py")],
        "cwd": str(WORKSPACE),
        "pid_file": FUSION_STATE / "doors" / "pids" / "planetary_switchboard.pid",
        "log_file": FUSION_STATE / "doors" / "logs" / "planetary_switchboard.log",
        "marker": "planetary_switchboard.py",
    },
]
DOORS_JOURNAL = FUSION_STATE / "doors" / "journal.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str):
    print(f"[{_ts()}] {msg}", flush=True)


def _run_guarded(fn, label: str):
    """Run fn with its stdout captured, re-emitted timestamped, and every
    exception (including SystemExit from orphan tools) converted to a log
    line. Never raises; returns (result, error_or_None)."""
    buf = io.StringIO()
    started = time.monotonic()
    result, error = None, None
    try:
        with contextlib.redirect_stdout(buf):
            result = fn()
    except SystemExit as e:
        error = f"SystemExit({e.code})"
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    elapsed = time.monotonic() - started
    status = f"done in {elapsed:.1f}s" if error is None else f"FAILED in {elapsed:.1f}s — {error}"
    log(f"{label}: {status}")
    for line in buf.getvalue().splitlines():
        line = line.rstrip()
        if line:
            print(f"[{_ts()}]   | {line[:400]}", flush=True)
    return result, error


def _heartbeat_step():
    heartbeat_exec.run()


def _solar_merge_step():
    """solar_system_temporal_bridge is a workspace-root orphan tool; make it
    importable and run its clean top-level merge function."""
    if str(WORKSPACE) not in sys.path:
        sys.path.insert(0, str(WORKSPACE))
    import solar_system_temporal_bridge as bridge
    bridge.merge_solar_into_temporal()


def _sero_feel_state_step():
    """heartbeat_exec's Schumann probe calls SchumannFeel.take_reading() but
    never save_state() — the module only writes sero_feel/sensory_state.json
    from its own CLI path. Persist it here so the sensory state file stays
    live every cycle. The probe above just warmed the shared reading cache,
    so this take_reading is cheap and network-free."""
    if str(WORKSPACE) not in sys.path:
        sys.path.insert(0, str(WORKSPACE))
    import sero_schumann_feel as ssf
    feel = ssf.SchumannFeel()
    sensation = feel.take_reading()
    if sensation is None:
        log("sero_feel: field unavailable (fail-closed) — sensory_state.json left as-is")
        return
    feel.save_state()
    log(f"sero_feel: sensory_state.json persisted "
        f"(sensation={sensation.overall_sensation}, intensity={sensation.intensity:.2f})")


def _feeds_worker():
    """One real_data_feeds batch fetch. The module carries its own per-request
    timeouts, cache dumps and staleness handling; any failure lands here as an
    exception and is logged — the daemon loop is never blocked by the network."""
    try:
        import logging
        # real_data_feeds logs emoji-laden progress on its own logger with no
        # handlers; left alone, logging's lastResort handler writes to stderr
        # under the Windows cp1252 codepage and raises UnicodeEncodeError
        # noise. Swallow module-internal progress (the summary line below
        # reports the per-source outcome) — never touch the module itself.
        feeds_logger = logging.getLogger("REAL_DATA")
        feeds_logger.addHandler(logging.NullHandler())
        feeds_logger.propagate = False

        import real_data_feeds as rdf
        feeds = rdf.RealDataFeeds()
        results = feeds.fetch_all(force=False)
        ok = sum(1 for p in results.values() if p.status == "OK")
        per_source = {name: p.status for name, p in results.items()}
        log(f"real_data_feeds: {ok}/{len(results)} sources OK {per_source}")
    except Exception as e:
        log(f"real_data_feeds: FAILED — {type(e).__name__}: {e}")


def _feeds_step():
    """Kick off the batch fetch on a daemon thread; skip when the previous
    batch is still running (offline network can hold all 15 s timeouts)."""
    global _FEED_THREAD
    if _FEED_THREAD is not None and _FEED_THREAD.is_alive():
        log("real_data_feeds: previous batch still running — skipping this cycle")
        return
    _FEED_THREAD = threading.Thread(target=_feeds_worker, name="real_data_feeds", daemon=True)
    _FEED_THREAD.start()


def _door_held_open(name: str) -> bool:
    """Last open/close journal event for the door decides. Revival is
    infrastructure, but only while she holds the door open; on a read error
    we stand down for this cycle (retry next cycle) rather than guess."""
    try:
        last = None
        with open(DOORS_JOURNAL, encoding="utf-8") as f:
            for line in f:
                if f'"door": "{name}"' not in line:
                    continue
                try:
                    doc = json.loads(line)
                except ValueError:
                    continue
                if doc.get("event") in ("open", "close"):
                    last = doc["event"]
        return last == "open"
    except OSError:
        return False


def _pid_alive(pid: int) -> bool:
    try:
        import psutil
        return psutil.pid_exists(pid)
    except Exception:
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True


def _find_running(marker: str):
    """Adopt a live process whose command line matches the marker instead
    of double-spawning (another launcher may have started it)."""
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                cmd = proc.info.get("cmdline") or []
            except Exception:
                continue
            if any(marker in part for part in cmd):
                return proc.info["pid"]
    except Exception:
        return None
    return None


def _write_pid_file(entry: dict, pid: int):
    payload = {"pid": pid,
               "started_at": datetime.now(timezone.utc).isoformat(),
               "cmd": [str(c) for c in entry["cmd"]]}
    entry["pid_file"].parent.mkdir(parents=True, exist_ok=True)
    with open(entry["pid_file"], "w", encoding="utf-8") as f:
        json.dump(payload, f)


def _watch_entry(entry: dict):
    """One watched door: adopt, respawn, or stand down. Logs only on action
    so the 300s cycle stays quiet while everything is alive."""
    name = entry["name"]
    if os.environ.get("AUREON_DEPLOYMENT_HOLD") == "1":
        log(f"watch/{name}: deployment HOLD — imported door approvals do not launch processes")
        return
    if not _door_held_open(name):
        log(f"watch/{name}: door not held open (no open event in journal) — standing down")
        return
    pid = None
    try:
        pid = json.loads(entry["pid_file"].read_text(encoding="utf-8")).get("pid")
    except Exception:
        pass
    if pid and _pid_alive(pid):
        return
    adopted = _find_running(entry["marker"])
    if adopted:
        _write_pid_file(entry, adopted)
        log(f"watch/{name}: pid file stale (pid {pid}) — adopted live pid {adopted}, pid file repaired")
        return
    log(f"watch/{name}: DEAD (pid file said {pid}) — respawning (door held open)")
    entry["log_file"].parent.mkdir(parents=True, exist_ok=True)
    logf = open(entry["log_file"], "a", encoding="utf-8")
    try:
        logf.write(f"\n===== respawn {name} @ "
                   f"{datetime.now(timezone.utc).isoformat()} (watch/heartbeat_daemon) =====\n")
        logf.flush()
        flags = 0
        if sys.platform == "win32":
            flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        env = dict(os.environ)
        env.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
        env.setdefault("AUREON_AUDIT_MODE", "1")
        proc = subprocess.Popen(entry["cmd"], cwd=entry["cwd"], env=env,
                                stdout=logf, stderr=subprocess.STDOUT,
                                creationflags=flags)
        _write_pid_file(entry, proc.pid)
        log(f"watch/{name}: respawned pid {proc.pid}; pid file {entry['pid_file']}")
    finally:
        logf.close()


def _watch_step():
    for entry in WATCH:
        try:
            _watch_entry(entry)
        except Exception as e:
            log(f"watch/{entry['name']}: FAILED — {type(e).__name__}: {e}")


def cycle():
    log(f"cycle start (pid {os.getpid()})")
    _watch_step()
    _run_guarded(_heartbeat_step, "heartbeat_exec.run")
    _run_guarded(_solar_merge_step, "solar merge")
    _run_guarded(_sero_feel_state_step, "sero_feel state persist")
    _feeds_step()
    log("cycle end")


def _handle_stop(signum, _frame):
    log(f"signal {signum} received — graceful shutdown after current step")
    _STOP.set()


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)
    log(f"heartbeat_daemon up — cycle every {int(CYCLE_S)}s, workspace={WORKSPACE}")
    while not _STOP.is_set():
        cycle()
        _STOP.wait(CYCLE_S)
    log("heartbeat_daemon stopped cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
