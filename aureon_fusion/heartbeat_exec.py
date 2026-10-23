"""💓 Heartbeat Exec — the executable HEARTBEAT checklist.

One run performs:
  1. sero_autonomous_expansion health cycle (classes imported, not shelled out)
  2. one-shot Schumann + space-weather fetch (lazy import of the
     sero_schumann_feel / sero_space_weather modules; degrades to the
     cached schumann_state.json, then to "unavailable")
  3. aureon-os-upstream unpulled-commit check (read-only git fetch + status
     in that directory only)
  4. a conscience audit pass (via aureon_fusion.conscience_hook)
  5. a trading pulse: tails the radar signal logs (fused_signals.jsonl,
     aureon_bridge_signals.jsonl) for counts + the last signal, flags any
     NEW trade execution event since the previous heartbeat (published to
     the thoughtbus via aureon_fusion.events; silent degrade), and guards
     signal freshness: fused_signals.jsonl older than 30 min is reported
     STALE with one chirp-6 per stale episode
  6. progress tracking in the runtime heartbeat-state file
     (~/.kimi_openclaw/memory/heartbeat-state.json, {"lastChecks": {...}})

Every check is independently guarded: one failure never aborts the run.
Import-safe; network operations are one-shot with tight timeouts.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .paths import WORKSPACE, AUREON_UPSTREAM, HEARTBEAT_STATE, FUSION_STATE, AUREON_RADAR
from . import conscience_hook
from . import events

LAST_RESULTS = FUSION_STATE / "heartbeat_last_results.json"
SCHUMANN_STATE = WORKSPACE / "schumann_state.json"
PULSE_STATE = FUSION_STATE / "trading_pulse_state.json"

# queen_mind organ state (MIND workstream deliverable). The organ owns its
# state under FUSION_STATE/queen_mind/ — mind_state.json (restart continuity),
# reports.jsonl (one full report per cycle, richest source), and the patched
# upstream consciousness metrics. Read-only; newest first.
QUEEN_MIND_DIR = FUSION_STATE / "queen_mind"
QUEEN_MIND_STATE_CANDIDATES = (
    QUEEN_MIND_DIR / "mind_state.json",
    WORKSPACE / "queen_mind_state.json",
)
# Persona roster (Queen, Sero, Seer, Lyra) — peer-delivered, optional.
PERSONAS_FILE = Path(__file__).resolve().parent / "personas.json"
# Model plane is hard-pinned to loopback: the ONLY legal inference path is a
# local Ollama reached at 127.0.0.1. The heartbeat verifies the loopback
# endpoint answers; it never probes anything else.
OLLAMA_LOOPBACK_URL = "http://127.0.0.1:11434/api/tags"

CHECK_NAMES = [
    "autonomous_health",
    "schumann_field",
    "space_weather",
    "aureon_upstream",
    "conscience_audit",
    "trading_pulse",
    "mind",
]

_SIGNAL_FILENAMES = ("fused_signals.jsonl", "aureon_bridge_signals.jsonl")
_EXEC_MARKERS = ("EXECUTED", "FILLED", "ORDER_SENT", "OPENED", "POSITION OPEN")
_BLOCK_MARKERS = ("BLOCKED", "REJECTED", "FAILED", "CANCELLED")

# Signal-feed freshness guard: a fused_signals.jsonl older than this is a
# STALE episode. The latch in trading_pulse_state.json guarantees exactly one
# chirp-6 per stale episode (cleared when the feed goes fresh again).
FUSED_SIGNALS_STALE_S = 1800.0
FUSED_SIGNALS_STALE_FILE = "fused_signals.jsonl"
_STALE_CHIRP_LATCH = "fused_signals_stale_chirped"


def _check_signal_freshness(state: dict) -> dict:
    """Freshness guard on the fused-signals feed. Reports STALE when the
    file's mtime exceeds FUSED_SIGNALS_STALE_S, and chirps urgency 6 exactly
    once per stale episode (episode ends when the feed writes again)."""
    target = AUREON_RADAR / FUSED_SIGNALS_STALE_FILE
    if not target.exists():
        return {"file": FUSED_SIGNALS_STALE_FILE, "status": "missing", "age_s": None}
    age = time.time() - target.stat().st_mtime
    stale = age > FUSED_SIGNALS_STALE_S
    if stale:
        if not state.get(_STALE_CHIRP_LATCH):
            try:
                events.chirp("heartbeat_exec", "fused_signals_stale", 6,
                             {"file": FUSED_SIGNALS_STALE_FILE,
                              "age_s": round(age),
                              "threshold_s": FUSED_SIGNALS_STALE_S})
            except Exception:
                pass
            state[_STALE_CHIRP_LATCH] = True
        status = "STALE"
    else:
        state.pop(_STALE_CHIRP_LATCH, None)
        status = "fresh"
    return {"file": FUSED_SIGNALS_STALE_FILE, "status": status,
            "age_s": round(age), "threshold_s": FUSED_SIGNALS_STALE_S}


# ───────────────────────────── heartbeat-state ─────────────────────────────

def _load_heartbeat_state() -> dict:
    try:
        if HEARTBEAT_STATE.exists():
            with open(HEARTBEAT_STATE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("lastChecks", {})
                return data
    except Exception as e:
        print(f"  ! could not read heartbeat-state: {e}")
    return {"lastChecks": {}}


def _mark_done(check_name: str, epoch: float = None):
    """Record check completion in the runtime heartbeat-state file.

    Atomic tmp+replace write: a crash mid-save must never leave a truncated
    heartbeat-state.json (the next read would fall back to all checks stale
    and re-run everything, and a half-written file breaks the JSON parse)."""
    state = _load_heartbeat_state()
    state["lastChecks"][check_name] = int(epoch or time.time())
    try:
        HEARTBEAT_STATE.parent.mkdir(parents=True, exist_ok=True)
        tmp = HEARTBEAT_STATE.with_name(
            f"{HEARTBEAT_STATE.name}.tmp.{os.getpid()}.{time.time_ns()}")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, HEARTBEAT_STATE)
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass
    except Exception as e:
        print(f"  ! could not write heartbeat-state: {e}")


# ───────────────────────────── 1. health cycle ─────────────────────────────

def run_health_cycle() -> dict:
    """Run the sero_autonomous_expansion health cycle via its classes."""
    import logging

    if str(WORKSPACE) not in sys.path:
        sys.path.insert(0, str(WORKSPACE))

    # The engine configures root logging at import (file + stdout). Keep the
    # file audit trail but drop the stdout stream handler it added, so engine
    # chatter (including its PSK banner) never leaks onto our CLI output.
    root = logging.getLogger()
    before = list(root.handlers)
    import sero_autonomous_expansion as expansion
    for h in list(root.handlers):
        if h not in before and isinstance(h, logging.StreamHandler) \
                and not isinstance(h, logging.FileHandler):
            root.removeHandler(h)

    orchestrator = expansion.SeroAutonomousExpansion()
    findings = orchestrator.heal.run_health_check()
    orchestrator.run_autonomous_cycle()
    status = orchestrator.matrix.get_status()
    return {
        "findings": len(findings),
        "finding_checks": [f.get("check") for f in findings],
        "gates": {
            "total": status.get("total_gates"),
            "active": status.get("active"),
            "approved": status.get("approved"),
            "review_required": status.get("review_required"),
            "locked": status.get("locked"),
        },
    }


# ───────────────────── 2/3. schumann + space weather ───────────────────────

def _as_dict(obj):
    """Normalize a sensor result (dataclass / to_dict object / dict) to a dict."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        try:
            return to_dict()
        except Exception:
            return None
    return None


def _probe_sensor_module(modname: str):
    """Lazy-import a sensor module and try a handful of known entry points.

    Covers both styles in the workspace: module-level one-shot fetchers
    (sero_space_weather.fetch_space_weather) and class-based organs
    (sero_schumann_feel.SchumannFeel.take_reading).
    """
    if str(WORKSPACE) not in sys.path:
        sys.path.insert(0, str(WORKSPACE))
    try:
        import importlib
        mod = importlib.import_module(modname)
    except Exception:
        return None
    for attr in ("fetch_latest", "get_reading", "fetch_space_weather",
                 "feel", "fetch", "read"):
        fn = getattr(mod, attr, None)
        if callable(fn):
            try:
                return _as_dict(fn())
            except TypeError:
                try:
                    return _as_dict(fn(timeout=10))
                except Exception:
                    continue
            except Exception:
                continue
    for cls_name, method in (("SchumannFeel", "take_reading"),
                             ("SpaceWeatherBridge", "update")):
        cls = getattr(mod, cls_name, None)
        if callable(cls):
            try:
                return _as_dict(getattr(cls(), method)())
            except Exception:
                continue
    return _as_dict(getattr(mod, "LAST_READING", None))


def check_field() -> dict:
    """One-shot Schumann reading. New modules first, cache fallback."""
    reading = _probe_sensor_module("sero_schumann_feel")
    if reading:
        return {"source": "sero_schumann_feel", "reading": reading}
    cache = _load_schumann_cache()
    if cache:
        return {"source": "schumann_state.json (cache; sero_schumann_feel unavailable)",
                "reading": cache}
    return {"source": None, "reading": None, "status": "unavailable"}


def check_space_weather() -> dict:
    """One-shot space-weather reading. New module first, cache fallback."""
    reading = _probe_sensor_module("sero_space_weather")
    if reading:
        return {"source": "sero_space_weather", "reading": reading}
    cache = _load_schumann_cache()
    if cache:
        return {
            "source": "schumann_state.json (cache; sero_space_weather unavailable)",
            "kp_index": cache.get("kp_index"),
            "solar_flare_class": cache.get("solar_flare_class"),
            "geomagnetic_status": cache.get("geomagnetic_status"),
        }
    return {"source": None, "status": "unavailable"}


def _load_schumann_cache() -> dict:
    try:
        if SCHUMANN_STATE.exists():
            with open(SCHUMANN_STATE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


# ───────────────────────────── 4. upstream sync ────────────────────────────

def check_upstream(timeout: int = 25) -> dict:
    """Read-only check for unpulled commits in aureon-os-upstream."""
    if not AUREON_UPSTREAM.exists():
        return {"ok": False, "error": "aureon-os-upstream missing"}
    try:
        subprocess.run(
            ["git", "fetch", "--quiet"],
            cwd=str(AUREON_UPSTREAM), timeout=timeout,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"git fetch timed out after {timeout}s"}
    except Exception as e:
        return {"ok": False, "error": f"git fetch failed: {e}"}

    try:
        out = subprocess.run(
            ["git", "status", "-sb", "--porcelain"],
            cwd=str(AUREON_UPSTREAM), timeout=15,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        branch_line = ""
        dirty = 0
        for line in (out.stdout or "").splitlines():
            if line.startswith("## "):
                branch_line = line[3:]
            elif line.strip():
                dirty += 1
        behind = ahead = 0
        if "behind " in branch_line:
            try:
                behind = int(branch_line.split("behind ")[1].split("]")[0].split(",")[0])
            except ValueError:
                behind = -1
        if "ahead " in branch_line:
            try:
                ahead = int(branch_line.split("ahead ")[1].split("]")[0].split(",")[0])
            except ValueError:
                ahead = -1
        return {
            "ok": True,
            "branch": branch_line,
            "behind": behind,
            "ahead": ahead,
            "dirty_files": dirty,
            "unpulled": behind > 0,
        }
    except Exception as e:
        return {"ok": False, "error": f"git status failed: {e}"}


# ───────────────────────────── 5. conscience ───────────────────────────────

def run_conscience_audit() -> dict:
    """Audit pass: one meta-evaluation plus recent veto accounting."""
    verdict = conscience_hook.evaluate(
        "Conscience audit pass: review recent autonomous actions and heartbeat "
        "decisions for alignment with the mission and the good of all beings",
        {"sls": 0.50},
    )
    recent_vetoes = 0
    veto_log = conscience_hook.VETO_LOG
    try:
        if veto_log.exists():
            cutoff = time.time() - 86400
            with open(veto_log, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        if json.loads(line).get("timestamp", "")[:10] >= \
                                datetime.fromtimestamp(cutoff, timezone.utc).strftime("%Y-%m-%d"):
                            recent_vetoes += 1
                    except Exception:
                        continue
    except Exception:
        pass
    return {
        "audit_verdict": verdict.get("verdict"),
        "reasoning": verdict.get("reasoning"),
        "vetoes_last_24h": recent_vetoes,
        "tally": conscience_hook.tally(),
    }


# ───────────────────────────── 5b. trading pulse ───────────────────────────

def signal_files() -> list:
    """Existing radar signal logs (fused_signals + aureon_bridge_signals)."""
    return [AUREON_RADAR / name for name in _SIGNAL_FILENAMES
            if (AUREON_RADAR / name).exists()]


def tail_signals(path: Path, n: int = 20) -> list:
    """Last n parseable JSON entries of a signal log (missing/empty -> [])."""
    try:
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        out = []
        for line in lines[-n:]:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if isinstance(entry, dict):
                out.append(entry)
        return out
    except Exception:
        return []


def _is_execution(entry: dict) -> bool:
    """Heuristic: does this signal-log entry describe a trade execution?
    Matches OPENED/EXECUTED/FILLED/ORDER_SENT markers in the raw text while
    excluding blocked/rejected/failed attempts."""
    raw = str(entry.get("raw") or entry.get("event") or "").upper()
    if any(m in raw for m in _BLOCK_MARKERS):
        return False
    return any(m in raw for m in _EXEC_MARKERS)


def _load_pulse_state() -> dict:
    try:
        if PULSE_STATE.exists():
            with open(PULSE_STATE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("files", {})
                return data
    except Exception:
        pass
    return {"files": {}}


def _save_pulse_state(state: dict):
    try:
        FUSION_STATE.mkdir(parents=True, exist_ok=True)
        with open(PULSE_STATE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def check_trading_pulse(tail_lines: int = 20) -> dict:
    """Perception check: counts + last signal per log, and NEW executions
    since the previous heartbeat (cursor in trading_pulse_state.json).
    First run only establishes the cursor so history never floods the bus."""
    files = signal_files()
    state = _load_pulse_state()
    freshness = _check_signal_freshness(state)
    if not files:
        _save_pulse_state(state)
        return {"files_present": [], "status": "no signal logs found",
                "fused_signals_freshness": freshness}

    new_executions = []
    per_file = []

    for path in files:
        entries = tail_signals(path, tail_lines)
        last_ts = ""
        last_sig = {}
        for e in entries:
            ts = str(e.get("timestamp") or "")
            if ts > last_ts:
                last_ts = ts
                last_sig = e

        cursor = str(state["files"].get(path.name, {}).get("last_ts", ""))
        file_new_execs = []
        for e in entries:
            ts = str(e.get("timestamp") or "")
            if _is_execution(e) and (not cursor or (ts and ts > cursor)):
                file_new_execs.append(e)
        if last_ts:
            state["files"].setdefault(path.name, {})["last_ts"] = last_ts

        per_file.append({
            "file": path.name,
            "tail_count": len(entries),
            "last_signal": {
                "symbol": last_sig.get("symbol"),
                "side": last_sig.get("direction") or last_sig.get("side"),
                "time": last_sig.get("timestamp"),
                "confidence": last_sig.get("confidence"),
            } if last_sig else None,
            "new_executions": len(file_new_execs),
        })
        new_executions.extend(file_new_execs)

    _save_pulse_state(state)

    # publish one thoughtbus event per new execution (lazy import; degrade silent)
    published = 0
    if new_executions:
        try:
            from . import events as fusion_events
            for e in new_executions:
                env = fusion_events.publish(
                    source="aureon_fusion.heartbeat_exec",
                    topic="trading.execution",
                    payload={
                        "symbol": e.get("symbol"),
                        "side": e.get("direction") or e.get("side"),
                        "confidence": e.get("confidence"),
                        "source_feed": e.get("source"),
                        "signal_time": e.get("timestamp"),
                        "raw": str(e.get("raw") or "")[:200],
                    },
                    priority="high",
                )
                if env:
                    published += 1
        except Exception:
            pass

    return {
        "files_present": [p.name for p in files],
        "per_file": per_file,
        "fused_signals_freshness": freshness,
        "new_execution_events": len(new_executions),
        "thoughtbus_events_published": published,
    }


# ───────────────────────────── 6b. mind ────────────────────────────────────

def _probe_loopback_model_plane(timeout: float = 5.0) -> dict:
    """Model-plane check: the local Ollama must answer on 127.0.0.1 loopback.
    This is the ONLY inference path the organism may use; the probe hits
    loopback only and never leaves the machine."""
    import urllib.request
    try:
        req = urllib.request.Request(OLLAMA_LOOPBACK_URL, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"reachable": resp.status == 200, "endpoint": "127.0.0.1:11434"}
    except Exception as e:
        return {"reachable": False, "endpoint": "127.0.0.1:11434", "error": str(e)}


def _load_queen_mind_state() -> dict:
    """Merged queen_mind state: mind_state.json continuity + the last cycle
    report from reports.jsonl (last metacognitive verdict, consciousness
    index). Missing or malformed state degrades to {} — the organ may not
    have completed its first cycle yet."""
    state = {}
    for path in QUEEN_MIND_STATE_CANDIDATES:
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    state["_path"] = str(path)
                    state.update(data)
                    break
        except Exception:
            continue
    # Richest source: the last full cycle report (read-only tail of one line).
    reports = QUEEN_MIND_DIR / "reports.jsonl"
    try:
        if reports.exists():
            tail = _tail_reports_line(reports)
            if tail:
                state.setdefault("_reports_path", str(reports))
                state["last_report"] = tail
                tick = state.get("last_tick") or {}
                tick.setdefault("cycle", tail.get("cycle"))
                tick.setdefault("action", tail.get("action"))
                tick.setdefault("timestamp", tail.get("timestamp"))
                tick.setdefault("narration_source", tail.get("narration_source"))
                state["last_tick"] = tick
    except Exception:
        pass
    return state


def _tail_reports_line(path: Path, n: int = 1) -> dict:
    """Last parseable JSON record of the queen_mind reports log."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in reversed(lines[-max(1, n) * 3:]):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if isinstance(rec, dict):
                return rec
    except Exception:
        pass
    return {}


def _queen_mind_indexes(state: dict):
    """(consciousness_index, metacognition_index) from the merged state.
    Consciousness comes from the last cycle report's consciousness metrics
    (upstream awakening_index / level); metacognition from the faculty
    reflection counts. None when the organ has not cycled yet."""
    ci = mi = None
    report = state.get("last_report") or {}
    con = report.get("consciousness") or {}
    if isinstance(con, dict):
        ci = con.get("awakening_index")
        if ci is None and con.get("level") is not None:
            ci = str(con.get("level"))
    meta = report.get("metacognition_state") or {}
    if isinstance(meta, dict):
        mi = meta.get("insight_count")
    return ci, mi


def _last_queen_mind_event_age() -> dict:
    """Age (seconds) of the most recent queen.mind event on the ThoughtBus.
    Scans the bus log for source 'queen_mind' or a 'queen.mind' topic."""
    log = events.BUS_LOG
    try:
        if not log.exists():
            return {"found": False}
        last_ts = None
        with open(log, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if not isinstance(rec, dict):
                    continue
                topic = str(rec.get("topic", ""))
                source = str(rec.get("source", ""))
                if "queen.mind" in topic or source == "queen_mind" or \
                        topic.startswith("queen.mind"):
                    ts = rec.get("timestamp") or rec.get("ts")
                    if ts is None:
                        continue
                    try:
                        ts_val = float(ts)
                    except (TypeError, ValueError, OverflowError):
                        try:
                            from datetime import datetime
                            ts_val = datetime.fromisoformat(
                                str(ts).replace("Z", "+00:00")).timestamp()
                        except Exception:
                            continue
                    if last_ts is None or ts_val > last_ts:
                        last_ts = ts_val
        if last_ts is None:
            return {"found": False}
        # Bus timestamps may be epoch seconds or ISO strings
        try:
            age = time.time() - float(last_ts)
        except (TypeError, ValueError, OverflowError):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(str(last_ts).replace("Z", "+00:00"))
                age = time.time() - dt.timestamp()
            except Exception:
                return {"found": True, "age_s": None}
        return {"found": True, "age_s": max(0.0, age)}
    except Exception:
        return {"found": False}


def load_personas() -> list:
    """Persona roster from aureon_fusion/personas.json (Queen, Sero, Seer,
    Lyra when delivered). Tolerant of the canonical {personas: [...]} shape,
    a dict-of-personas, or a plain list."""
    try:
        if not PERSONAS_FILE.exists():
            return []
        with open(PERSONAS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    if isinstance(data, dict) and isinstance(data.get("personas"), list):
        data = data["personas"]
    out = []
    if isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, dict):
                name = val.get("name") or key
                role = val.get("role") or val.get("title") or ""
                out.append(str(name) + (f" ({role})" if role else ""))
            else:
                out.append(str(key))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                name = item.get("name") or item.get("persona") or "?"
                epithet = item.get("epithet") or ""
                status = item.get("status") or ""
                label = str(name)
                if epithet:
                    label += f" — {epithet}"
                if status:
                    label += f" [{status}]"
                out.append(label)
            else:
                out.append(str(item))
    return out


def mind_snapshot() -> dict:
    """Read-only queen_mind snapshot shared by the heartbeat check and
    fusion_status: organ state, last metacognitive verdict + consciousness
    index, model-plane loopback verification, last queen.mind event age."""
    snap = {"organ": None, "state": {}, "state_path": None,
            "model_plane": _probe_loopback_model_plane(),
            "queen_mind_event": _last_queen_mind_event_age(),
            "personas": load_personas()}
    state = _load_queen_mind_state()
    snap["state_path"] = state.pop("_path", None)
    state.pop("_reports_path", None)
    snap["state"] = state
    try:
        from .organ_registry import status_data as _organ_status
        snap["organ"] = _organ_status().get("queen_mind")
    except Exception:
        pass
    return snap


def check_mind() -> dict:
    """The 7th heartbeat check: queen_mind status one-liner + model-plane
    LOCAL-ONLY verification. Degrades gracefully when the organ is dormant,
    still cycling, or its state file has not appeared yet."""
    snap = mind_snapshot()
    organ = snap.get("organ") or {}
    state = snap.get("state") or {}
    mp = snap.get("model_plane") or {}
    organ_state = organ.get("state", "not_registered")
    tick = state.get("last_tick") or {}
    report = state.get("last_report") or {}
    verdict = (tick.get("action") or report.get("action")
               or state.get("last_verdict") or state.get("verdict")
               or state.get("metacognitive_verdict"))
    ci, mi = _queen_mind_indexes(state)
    # Native doctrine (owner decree): the mind reasons on the repo's own
    # logic — no model plane required. The loopback probe below is kept only
    # as an informational signal for the self_questioning_ai organ.
    plane = ("native (repo logic: hnc+auris+qgita+knowledge)"
             if (tick.get("narration_source") or "").startswith("native")
             else f"native reasoning (ollama loopback info: "
                  f"{'reachable' if mp.get('reachable') else 'dark'})")
    return {
        "organ_state": organ_state,
        "organ_pid": organ.get("pid"),
        "cycle": tick.get("cycle") or report.get("cycle"),
        "persona": report.get("persona"),
        "last_verdict": verdict,
        "consciousness_index": ci,
        "metacognition_index": mi,
        "narration_source": tick.get("narration_source") or report.get("narration_source"),
        "model_plane": plane,
        "queen_mind_event": snap.get("queen_mind_event"),
        "personas": snap.get("personas") or [],
        "dormant_reason": organ.get("dormant_reason"),
    }


# ───────────────────────────── run / status ────────────────────────────────

def run() -> dict:
    """Execute the full HEARTBEAT checklist once."""
    results = {"started_at": datetime.now(timezone.utc).isoformat(), "checks": {}}

    print("═" * 72)
    print("💓 HEARTBEAT EXEC — fused checklist")
    print("═" * 72)

    # 1. autonomous health cycle
    print("\n[1/7] sero_autonomous_expansion health cycle ...")
    try:
        res = run_health_cycle()
        results["checks"]["autonomous_health"] = res
        g = res["gates"]
        print(f"      findings={res['findings']} {res['finding_checks'] or '(all clear)'}")
        print(f"      gates: {g['active']} active / {g['review_required']} review / {g['locked']} locked")
        _mark_done("autonomous_health")
    except Exception as e:
        results["checks"]["autonomous_health"] = {"error": str(e)}
        print(f"      ! FAILED: {e}")

    # 2. schumann field
    print("\n[2/7] Schumann field ...")
    try:
        res = check_field()
        results["checks"]["schumann_field"] = res
        r = res.get("reading")
        if isinstance(r, dict):
            if "overall_sensation" in r:
                print(f"      sensation: {r.get('overall_sensation')} (intensity {r.get('intensity', '?')}) "
                      f"| extraction={r.get('extraction_detected')} | src: {res.get('source')}")
            else:
                print(f"      {r.get('frequency_hz', '?')} Hz | activity {r.get('activity_index', '?')} "
                      f"({r.get('activity_label', '?')}) | src: {res.get('source')}")
        else:
            print(f"      reading: {r} | src: {res.get('source')}")
        _mark_done("schumann_field")
    except Exception as e:
        results["checks"]["schumann_field"] = {"error": str(e)}
        print(f"      ! FAILED: {e}")

    # 3. space weather
    print("\n[3/7] Space weather ...")
    try:
        res = check_space_weather()
        results["checks"]["space_weather"] = res
        r = res.get("reading")
        if isinstance(r, dict) and "kp_index" in r:
            print(f"      Kp={r.get('kp_index')} storm={r.get('storm_level')} "
                  f"cme24h={r.get('cme_count_24h')} reachable={r.get('source_reachable')} "
                  f"| src: {res.get('source')}")
        else:
            print(f"      Kp={res.get('kp_index', '?')} flare={res.get('solar_flare_class', '?')} "
                  f"geo={res.get('geomagnetic_status', res.get('status', '?'))} "
                  f"| src: {res.get('source')}")
        _mark_done("space_weather")
    except Exception as e:
        results["checks"]["space_weather"] = {"error": str(e)}
        print(f"      ! FAILED: {e}")

    # 4. upstream sync
    print("\n[4/7] aureon-os-upstream sync ...")
    try:
        res = check_upstream()
        results["checks"]["aureon_upstream"] = res
        if res.get("ok"):
            flag = " ⚠ UNPULLED COMMITS" if res.get("unpulled") else " up to date"
            print(f"      {res.get('branch')} | behind={res.get('behind')} "
                  f"ahead={res.get('ahead')} dirty={res.get('dirty_files')}{flag}")
        else:
            print(f"      ! {res.get('error')}")
        _mark_done("aureon_upstream")
    except Exception as e:
        results["checks"]["aureon_upstream"] = {"error": str(e)}
        print(f"      ! FAILED: {e}")

    # 5. conscience audit
    print("\n[5/7] conscience audit ...")
    try:
        res = run_conscience_audit()
        results["checks"]["conscience_audit"] = res
        t = res.get("tally", {})
        print(f"      audit verdict: {res.get('audit_verdict')} | vetoes(24h): {res.get('vetoes_last_24h')}")
        print(f"      tally: {t.get('total_checks', 0)} checks, {t.get('veto_count', 0)} vetoes")
        _mark_done("conscience_audit")
    except Exception as e:
        results["checks"]["conscience_audit"] = {"error": str(e)}
        print(f"      ! FAILED: {e}")

    # 6. trading pulse
    print("\n[6/7] trading pulse ...")
    try:
        res = check_trading_pulse()
        results["checks"]["trading_pulse"] = res
        if res.get("status") == "no signal logs found":
            print("      no signal logs found (radar bridge down?)")
        else:
            for pf in res.get("per_file", []):
                ls = pf.get("last_signal") or {}
                last = (f"last={ls.get('side') or '?'} {ls.get('symbol') or '?'} "
                        f"@ {str(ls.get('time') or '?')[:19]}") if pf.get("last_signal") else "no parseable signals"
                print(f"      {pf['file']}: tail={pf['tail_count']} {last} "
                      f"(new execs: {pf['new_executions']})")
            print(f"      NEW executions since last heartbeat: {res.get('new_execution_events', 0)} "
                  f"| thoughtbus events published: {res.get('thoughtbus_events_published', 0)}")
        fresh = res.get("fused_signals_freshness") or {}
        if fresh.get("status") == "STALE":
            print(f"      ⚠ {fresh.get('file')}: STALE "
                  f"({_age_str(time.time() - float(fresh.get('age_s') or 0))} old, "
                  f"threshold {int(FUSED_SIGNALS_STALE_S // 60)} min)")
        elif fresh.get("status") == "missing":
            print(f"      ! {fresh.get('file')}: missing")
        _mark_done("trading_pulse")
    except Exception as e:
        results["checks"]["trading_pulse"] = {"error": str(e)}
        print(f"      ! FAILED: {e}")

    # 7. mind — queen_mind + model-plane loopback verification
    print("\n[7/7] mind (queen_mind + model plane) ...")
    try:
        res = check_mind()
        results["checks"]["mind"] = res
        verdict = res.get("last_verdict") or "no verdict yet"
        ci = res.get("consciousness_index")
        mi = res.get("metacognition_index")
        idx = []
        if ci is not None:
            idx.append(f"consciousness={ci}")
        if mi is not None:
            idx.append(f"metacognition={mi}")
        print(f"      organ: {res.get('organ_state')}"
              + (f" pid={res.get('organ_pid')}" if res.get("organ_pid") else ""))
        if res.get("organ_state") == "dormant" and res.get("dormant_reason"):
            print(f"      dormant: {res['dormant_reason']}")
        print(f"      verdict: {verdict} ({', '.join(idx) if idx else 'index pending first cycle'})")
        print(f"      model plane: {res.get('model_plane')}")
        ev = res.get("queen_mind_event") or {}
        if ev.get("found") and ev.get("age_s") is not None:
            print(f"      last queen.mind event: {_age_str(time.time() - ev['age_s'])}")
        personas = res.get("personas") or []
        if personas:
            print(f"      personas: {', '.join(personas)}")
        _mark_done("mind")
    except Exception as e:
        results["checks"]["mind"] = {"error": str(e)}
        print(f"      ! FAILED: {e}")

    results["finished_at"] = datetime.now(timezone.utc).isoformat()
    try:
        with open(LAST_RESULTS, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"\n  ! could not save last results: {e}")
    print("\n" + "═" * 72)
    print(f"done. heartbeat-state updated: {HEARTBEAT_STATE}")
    print("═" * 72)

    # event spine: one heartbeat.check_complete per check + heartbeat.done
    checks = results.get("checks", {})
    for name, res in checks.items():
        events.publish_event("heartbeat_exec", "heartbeat.check_complete",
                             {"check": name, "ok": "error" not in res}, priority=4)
    events.publish_event("heartbeat_exec", "heartbeat.done",
                         {"checks": len(checks),
                          "started_at": results.get("started_at"),
                          "finished_at": results.get("finished_at")},
                         priority=5)

    # Flight-recorder pass: every heartbeat also certifies faculty freshness.
    try:
        from . import flight_recorder
        flight_recorder.record_cycle(silent=True)
    except Exception as e:
        print(f"  ! flight recorder pass failed: {e}")

    return results


def _age_str(epoch) -> str:
    if not epoch:
        return "never"
    delta = time.time() - float(epoch)
    if delta < 90:
        return f"{int(delta)}s ago"
    if delta < 5400:
        return f"{int(delta // 60)}m ago"
    return f"{delta / 3600:.1f}h ago"


def status() -> str:
    """Report ages of the last heartbeat checks."""
    state = _load_heartbeat_state()
    last = state.get("lastChecks", {})
    lines = ["═" * 72, "💓 HEARTBEAT STATUS", "═" * 72]
    names = CHECK_NAMES + [n for n in last if n not in CHECK_NAMES]
    for name in names:
        lines.append(f"  {name:<20} {_age_str(last.get(name))}")
    lines.append("═" * 72)
    return "\n".join(lines)


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    verb = argv[0] if argv else "status"
    if verb in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.heartbeat_exec [run|status]")
        return 0
    if verb == "run":
        run()
        return 0
    if verb == "status":
        print(status())
        return 0
    print(f"unknown verb: {verb} (expected run|status)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
