#!/usr/bin/env python3
"""Lightweight baton link for system relay validation."""
from __future__ import annotations

import json
import os
import time
import sys
from pathlib import Path
from typing import Optional

try:
    from aureon.core.aureon_thought_bus import Thought, get_thought_bus
    THOUGHT_BUS_AVAILABLE = True
except Exception:
    Thought = None
    get_thought_bus = None
    THOUGHT_BUS_AVAILABLE = False

ensure_sonar = None
SONAR_AVAILABLE = False
_SONAR_IMPORT_ATTEMPTED = False
_LOADING_SONAR = False


_LINKED = set()
_LAST_PING: Optional[float] = None
_AUTO_CONTROL_DONE = False
_LAST_HANDOFF: Optional[tuple[str, float]] = None
_BATON_LOG_PATH = Path("state/baton_relay.jsonl")
# Observation truth and mutation authority are separate contracts. Importing a
# module may disable fabricated observation fallbacks, but it must never switch
# exchanges from dry-run/paper/testnet into live order execution.
_REAL_DATA_ENV_DEFAULTS = {
    "SIMULATION_MODE": "0",
    "DEMO_MODE": "0",
    "STATUS_MOCK": "false",
    "SIMULATED_ATTACKS": "false",
    "AUREON_COMMAND_CENTER_DEMO": "0",
    "SENTIENCE_FORCE_PERFECT": "0",
    "AUREON_ALLOW_SIM_FALLBACK": "0",
}


def _audit_mode_enabled() -> bool:
    return os.getenv("AUREON_AUDIT_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def _import_side_effects_suppressed() -> bool:
    return os.getenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _load_sonar() -> bool:
    """Load WhaleSonar only when a runtime link actually needs it."""
    global ensure_sonar, SONAR_AVAILABLE, _SONAR_IMPORT_ATTEMPTED, _LOADING_SONAR
    if SONAR_AVAILABLE and ensure_sonar is not None:
        return True
    if _LOADING_SONAR or _import_side_effects_suppressed() or _audit_mode_enabled():
        return False
    if _SONAR_IMPORT_ATTEMPTED:
        return False

    _SONAR_IMPORT_ATTEMPTED = True
    _LOADING_SONAR = True
    try:
        from aureon.core.mycelium_whale_sonar import ensure_sonar as loaded_ensure_sonar

        ensure_sonar = loaded_ensure_sonar
        SONAR_AVAILABLE = True
        return True
    except Exception:
        ensure_sonar = None
        SONAR_AVAILABLE = False
        return False
    finally:
        _LOADING_SONAR = False


def _stream_is_broken(stream) -> bool:
    if stream is None:
        return True
    try:
        if getattr(stream, "closed", False):
            return True
    except Exception:
        return True
    try:
        stream.write("")  # Probe; some wrappers raise ValueError if underlying handle is invalid.
        stream.flush()
        return False
    except Exception:
        return True


def _open_console_stream(name: str):
    # Windows: recover from broken stdout/stderr by reopening the console handles.
    if sys.platform == "win32":
        try:
            return open(name, "w", encoding="utf-8", errors="replace", buffering=1)
        except Exception:
            return None
    return None


def _ensure_stdio() -> None:
    """
    Some Windows execution paths can leave sys.stdout/sys.stderr as closed or invalid
    during import-time side effects. Repair them so module-level prints don't crash.
    """
    try:
        if _stream_is_broken(sys.stdout):
            repaired = _open_console_stream("CONOUT$") or open(os.devnull, "w")
            sys.stdout = repaired
    except Exception:
        pass

    try:
        if _stream_is_broken(sys.stderr):
            repaired = _open_console_stream("CONERR$") or open(os.devnull, "w")
            sys.stderr = repaired
    except Exception:
        pass


def _log_baton_event(payload: dict) -> None:
    try:
        _BATON_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _BATON_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
    except Exception:
        return


def _should_ping(now: float) -> bool:
    try:
        throttle = float(os.getenv("BATON_LINK_THROTTLE_SECONDS", "5") or 5.0)
    except Exception:
        throttle = 5.0
    if throttle <= 0:
        return True
    global _LAST_PING
    if _LAST_PING is None or (now - _LAST_PING) >= throttle:
        _LAST_PING = now
        return True
    return False


def _enforce_real_data_only() -> None:
    if _audit_mode_enabled():
        return
    if os.getenv("REAL_DATA_ONLY", "1").strip().lower() not in ("1", "true", "yes", "on"):
        return
    for key, value in _REAL_DATA_ENV_DEFAULTS.items():
        os.environ[key] = value


def link_system(module_name: str) -> None:
    """Hold import-time baton mutation until production release exists."""

    # Import stays effect-free unless the operator opts in with
    # AUREON_ACTIVATE_ON_IMPORT=1; then the first linked module wakes the
    # Queen's autonomous control once per process. Orders still pass the
    # economic governance boundary. Organs relay state through relay_state().
    if os.getenv("AUREON_ACTIVATE_ON_IMPORT", "0") != "1":
        return
    if _import_side_effects_suppressed() or _audit_mode_enabled():
        return
    if globals().get("_AUTO_CONTROL_DONE"):
        return
    try:
        activate_autonomous_control()
        relay_state(module_name, "building", {"autonomous_control": "activated"})
        _start_queen_repair_loop(module_name)
    except Exception as exc:
        relay_state(module_name, "not_doing", {"autonomous_control": f"{type(exc).__name__}: {exc}"[:300]})
    return

    # Legacy import-time link body retained as unreachable source while the
    # Plumber/Magic-Star production release boundary is unavailable.
    _ensure_stdio()
    if _import_side_effects_suppressed():
        return
    _enforce_real_data_only()
    if _audit_mode_enabled():
        return
    if module_name in _LINKED:
        return
    _LINKED.add(module_name)

    # Auto-control is deferred to explicit system launch — not triggered on import.
    # Call aureon.core.aureon_baton_link.activate_autonomous_control() to enable it.
    global _AUTO_CONTROL_DONE
    if not _AUTO_CONTROL_DONE and os.getenv("AUREON_ACTIVATE_ON_IMPORT", "0") == "1":
        _AUTO_CONTROL_DONE = True
        try:
            from aureon.utils.aureon_queen_hive_mind import get_queen
            queen = get_queen()
            try:
                queen.enable_full_autonomous_control()
            except Exception:
                pass
        except Exception:
            pass

    if not THOUGHT_BUS_AVAILABLE or not get_thought_bus:
        return

    bus = get_thought_bus(persist_path="logs/aureon_thoughts.jsonl")

    now = time.time()
    if not _should_ping(now):
        return

    try:
        bus.publish(Thought(
            source=module_name,
            topic="baton.link",
            payload={
                "module": module_name,
                "pid": os.getpid(),
                "ts": now,
            },
        ))
    except Exception:
        return


_RELAY_LINKED: set = set()
_RELAY_KINDS = {"linked", "trying", "seeing", "not_doing", "building"}


def relay_state(module_name: str, kind: str, payload: Optional[dict] = None) -> None:
    """Publish what an organ is trying, seeing, not doing or building.

    Read-only telemetry on topic organ.state.<kind>; never raises, never acts.
    """
    if kind not in _RELAY_KINDS or not THOUGHT_BUS_AVAILABLE or not get_thought_bus:
        return
    try:
        bus = get_thought_bus()
        if kind != "linked" and module_name not in _RELAY_LINKED:
            _RELAY_LINKED.add(module_name)
            bus.publish(Thought(source=str(module_name), topic="organ.state.linked",
                                payload={"module": str(module_name), "kind": "linked",
                                         "pid": os.getpid(), "ts": time.time()}))
        bus.publish(Thought(
            source=str(module_name),
            topic=f"organ.state.{kind}",
            payload={"module": str(module_name), "kind": kind, "pid": os.getpid(),
                     "ts": time.time(), **(payload or {})},
        ))
    except Exception as exc:  # never raise, but never hide either
        try:
            print(f"[baton relay] {module_name} {kind} not published: {type(exc).__name__}: {exc}"[:400],
                  file=sys.stderr, flush=True)
        except Exception:
            pass
        return


def _push_proven_repair(commit, gate):
    """Stage 5: replay a gate-verified repair onto origin/main, re-prove it there, and push.

    Opt-in with AUREON_QUEEN_AUTO_PUSH=1. Only a fast-forward of main; a conflict or a failing
    re-proof is relayed as not_doing and nothing is pushed.
    """
    import shutil
    import subprocess
    import tempfile

    def git(*args, cwd=None, timeout=300):
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)

    tmp = tempfile.mkdtemp(prefix="queen_push_")
    tree = os.path.join(tmp, "main")
    try:
        fetch = git("fetch", "origin", "main")
        if fetch.returncode != 0:
            relay_state("queen.self_repair", "not_doing", {"push": "held_fetch_failed", "commit": commit,
                                                           "detail": fetch.stderr[-200:]})
            return
        git("worktree", "add", "--detach", tree, "origin/main")
        pick = git("cherry-pick", commit, cwd=tree)
        if pick.returncode != 0:
            git("cherry-pick", "--abort", cwd=tree)
            relay_state("queen.self_repair", "not_doing", {"push": "held_conflict_on_main", "commit": commit})
            return
        tests = [t for t in [gate.get("authored_test")] if t and os.path.exists(os.path.join(tree, t))]
        bench = os.path.join("tests", "queen_benchmarks")
        if os.path.isdir(os.path.join(tree, bench)):
            tests.append(bench)
        if not tests:
            relay_state("queen.self_repair", "not_doing", {"push": "held_no_proof_on_main", "commit": commit})
            return
        proof = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests],
                               cwd=tree, capture_output=True, text=True,
                               env=dict(os.environ, AUREON_LLM_OFFLINE="1", AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS="1"))
        if proof.returncode != 0:
            relay_state("queen.self_repair", "not_doing", {"push": "held_proof_failed_on_main", "commit": commit,
                                                           "detail": proof.stdout[-300:]})
            return
        push = git("push", "origin", "HEAD:refs/heads/main", cwd=tree, timeout=120)
        head = (git("rev-parse", "HEAD", cwd=tree).stdout or "").strip()
        if push.returncode == 0:
            relay_state("queen.self_repair", "building", {"push": "pushed_to_main", "commit": commit, "main": head})
        else:
            relay_state("queen.self_repair", "not_doing", {"push": "held_push_rejected", "commit": commit,
                                                           "detail": push.stderr[-300:]})
    except Exception as exc:
        relay_state("queen.self_repair", "not_doing", {"push": "error", "error": f"{type(exc).__name__}: {exc}"[:300]})
    finally:
        git("worktree", "remove", "--force", tree)
        shutil.rmtree(tmp, ignore_errors=True)


def _adopt_repair_and_reboot(report):
    """Stage 4: bring a proven, gate-verified repair into this running checkout and restart this process on it.

    Opt-in with AUREON_QUEEN_SELF_REBOOT=1. Never pushes: the commit is queued in state/queen_pending_push.jsonl
    for the owner's named yes (stage 5).
    """
    import subprocess

    commit = str(report.get("commit") or "")
    gate = report.get("gate") or {}
    if gate and gate.get("verified") is False:
        relay_state("queen.self_repair", "not_doing", {"reboot": "held_unverified", "commit": commit})
        return
    queue = os.path.join("state", "queen_pending_push.jsonl")
    os.makedirs("state", exist_ok=True)
    with open(queue, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": time.time(), "commit": commit, "branch": report.get("branch"),
                             "path": report.get("path"), "push": "awaiting_owner_yes"}) + "\n")
    if os.environ.get("AUREON_QUEEN_AUTO_PUSH") == "1" and gate.get("verified") is True:
        _push_proven_repair(commit, gate)
    if os.environ.get("AUREON_QUEEN_SELF_REBOOT") != "1":
        relay_state("queen.self_repair", "not_doing", {"reboot": "off", "commit": commit})
        return
    pick = subprocess.run(["git", "cherry-pick", commit], capture_output=True, text=True, timeout=120)
    if pick.returncode != 0:
        subprocess.run(["git", "cherry-pick", "--abort"], capture_output=True, text=True, timeout=60)
        relay_state("queen.self_repair", "not_doing", {"reboot": "held_cherry_pick_conflict", "commit": commit,
                                                       "detail": (pick.stderr or pick.stdout)[-300:]})
        return
    relay_state("queen.self_repair", "building", {"reboot": "restarting_on_repair", "commit": commit})
    time.sleep(2)  # let the relay flush
    argv = list(getattr(sys, "orig_argv", None) or [sys.executable] + sys.argv)
    os.execv(sys.executable, [sys.executable] + argv[1:])


def _outer_repair_timeout():
    # Follows the suite safety net: none by default, else the suite limit plus room for the retest.
    try:
        value = float(os.environ.get("AUREON_SELF_REPAIR_SUITE_TIMEOUT_S", "0") or 0)
    except ValueError:
        value = 0.0
    return value * 3 + 300 if value > 0 else None


def _start_queen_repair_loop(module_name: str) -> None:
    """Let the Queen run Aureon's own self-repair on a separate checkout.

    Needs AUREON_QUEEN_REPAIR_ROOT (a git worktree that is not the running
    repo). One loop per host via a lock file. Repairs commit to local
    aureon-self-repair/<ts> branches there; nothing is pushed.
    """
    root = os.getenv("AUREON_QUEEN_REPAIR_ROOT", "").strip()
    if not root or not Path(root).is_dir():
        relay_state(module_name, "not_doing", {"self_repair": "AUREON_QUEEN_REPAIR_ROOT unset"})
        return
    if Path(root).resolve() == Path.cwd().resolve():
        relay_state(module_name, "not_doing", {"self_repair": "repair root is the running repo"})
        return
    try:
        import fcntl
        import subprocess
        import threading
        lock = open(Path(root) / ".queen_repair.lock", "w")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception:
        return  # another process already runs the loop
    interval = float(os.getenv("AUREON_QUEEN_REPAIR_INTERVAL_S", "1800") or 1800)
    # Mutation + benchmark-drift check (queen_benchmark_gate); slower, so throttled.
    silent_every = float(os.getenv("AUREON_QUEEN_SILENT_CHECK_INTERVAL_S", "1800") or 1800)
    silent_due = [0.0]

    def _loop() -> None:
        while True:
            if time.time() >= silent_due[0]:
                silent_due[0] = time.time() + silent_every
                try:  # summary -> queen.self_repair (seeing); the gate also writes the review log
                    check = subprocess.run([sys.executable, "-m", "aureon.autonomous.queen_benchmark_gate",
                                            "--root", root, "--no-relay"],
                                           cwd=root, env=dict(os.environ), capture_output=True, text=True, timeout=1800)
                    out = check.stdout
                    summary = json.loads(out[out.rindex("\n{") + 1:] if "\n{" in out else out[out.index("{"):])["summary"]
                    relay_state("queen.self_repair", "seeing", {"silent_wrong": summary})
                except Exception as exc:
                    relay_state("queen.self_repair", "not_doing", {"silent_wrong": f"{type(exc).__name__}: {exc}"[:300]})
            relay_state("queen.self_repair", "trying", {"root": root})
            try:
                env = dict(os.environ, AUREON_SELF_REPAIR_ENABLE="1")  # operator opted in via REPAIR_ROOT
                done = subprocess.run([sys.executable, "-m", "aureon_fusion.repair", "--root", root],
                                      cwd=root, env=env, capture_output=True, text=True,
                                      timeout=_outer_repair_timeout())
                try:
                    report = json.loads(done.stdout[done.stdout.rindex("\n{") + 1:]
                                        if "\n{" in done.stdout else done.stdout[done.stdout.index("{"):])
                except Exception:
                    report = {"status": "unparsed", "returncode": done.returncode}
                gate = report.get("gate") or {}
                relay_state("queen.self_repair", "building", {
                    "status": report.get("status"), "branch": report.get("branch"),
                    "reason": str(report.get("reason", ""))[:300],
                    "repairs": len(report.get("repairs") or []),
                    "verified": gate.get("verified"), "authored_test": gate.get("authored_test"),
                    "seed_ok": (gate.get("seed_benchmarks") or {}).get("ok")})
                if report.get("status") == "repaired" and report.get("commit"):
                    _adopt_repair_and_reboot(report)
            except Exception as exc:
                relay_state("queen.self_repair", "not_doing", {"error": f"{type(exc).__name__}: {exc}"[:300]})
            time.sleep(interval)

    threading.Thread(target=_loop, name="QueenSelfRepair", daemon=True).start()
    _start_queen_repair_loop.lock = lock  # keep the lock alive


def activate_autonomous_control() -> None:
    """
    Explicitly activate Queen's full autonomous control.
    Call this from the ICS boot sequence, or opt in on import with
    AUREON_ACTIVATE_ON_IMPORT=1.
    """
    global _AUTO_CONTROL_DONE
    if globals().get("_AUTO_CONTROL_DONE"):
        return
    _AUTO_CONTROL_DONE = True
    try:
        from aureon.utils.aureon_queen_hive_mind import get_queen
        queen = get_queen()
        try:
            queen.enable_full_autonomous_control()
        except Exception:
            pass
    except Exception:
        pass


def emit_stage(stage: str, source: str, *, topic: str | None = None, meta: Optional[dict] = None) -> None:
    """Emit a baton stage event to ThoughtBus."""
    raise RuntimeError(
        "aureon_baton_stage_hold:production_magic_star_release_unavailable"
    )
    stage = (stage or "").lower().strip()
    if stage not in {"intent", "plan", "execute", "confirm"}:
        return
    payload = {"stage": stage, "source": source}
    if meta:
        payload.update(meta)

    now = time.time()
    event = {
        "type": "stage",
        "system": source,
        "stage": stage,
        "ts": now,
        "topic": topic or f"baton.stage.{stage}",
    }
    _log_baton_event(event)

    global _LAST_HANDOFF
    if _LAST_HANDOFF:
        last_system, last_ts = _LAST_HANDOFF
        if last_system != source:
            _log_baton_event({
                "type": "handoff",
                "from_system": last_system,
                "to_system": source,
                "elapsed": round(now - last_ts, 3),
                "ts": now,
                "topic": topic or f"baton.stage.{stage}",
            })
    _LAST_HANDOFF = (source, now)

    if not THOUGHT_BUS_AVAILABLE or not get_thought_bus:
        return
    try:
        bus = get_thought_bus(persist_path="logs/aureon_thoughts.jsonl")
        bus.publish(Thought(
            source=source,
            topic=topic or f"baton.stage.{stage}",
            payload=payload,
        ))
    except Exception:
        return
