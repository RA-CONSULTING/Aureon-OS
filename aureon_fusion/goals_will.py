"""🎯 GOALS WILL — the sovereign goals will of the Aureon Fusion organism.

Owner decree (absolute):
  • The organism CHOOSES its goals by free will — goal desires arise from
    INTERNAL state only (wheel state, proof-chain gaps, capability-map
    openings), never external steering, trends, or push feeds.
  • This component OFFERS goals; it never executes them: no trades, no
    process spawns, no external calls. A goal that is accepted here is a
    consideration handed to the organism, nothing more.
  • Every proposed goal passes THREE gates, all fail-closed, exactly like
    the learning will and the master-key forge:
        1. CONSCIENCE   (aureon_fusion.conscience_hook.evaluate — VETO
                         absolute; an unreadable conscience said no)
        2. HNC COHERENCE (coherence_gamma from state/hnc_core_state.json
                         ≥ 0.25 AND fresh ≤ 300 s — missing/stale/low means
                         the organism WAITS, never fabricates)
        3. AUTHORIZATION (aureon_fusion.capability_gate.check(
                         'system:activate_internal_door'); a missing matrix
                         row degrades to DEFERRED, never a crash)
  • Risk grading routes through the upstream goal-capability map
    (aureon.autonomous.aureon_goal_capability_map.recommend_goal_routes)
    — descriptive only; it grades risk, it gates nothing.
  • A goal refused for a persistent cause (held_incoherent / deferred)
    RESTS for a TTL before being re-asked — the will rotates to other
    internal candidates instead of re-proposing the same refused goal
    every cycle. The gates are never weakened; only the re-asking rests.
    A conscience VETO remains permanent, exactly as in learning_will.
  • Native reasoning only — NO external LLM calls. Silence is valid: if
    the organism seeks no goal, no goal is proposed.

Import-safe: no organ is instantiated at import; suppression env vars are
honored via setdefault. All state writes are locked appends.

CLI:
    python -m aureon_fusion.goals_will status
    python -m aureon_fusion.goals_will propose "goal text"
    python -m aureon_fusion.goals_will consider [--dry]
"""

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .paths import FUSION_STATE, WORKSPACE, AUREON_UPSTREAM

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

# ───────────────────────── doctrine constants ──────────────────────────────

COHERENCE_THRESHOLD = 0.25          # gamma below this → the organism WAITS
HNC_FRESH_S = 300.0                 # hnc state older than this → fail closed
MIN_DESIRE = 0.25                   # below this the organism is not asking
GOALS_DIR = FUSION_STATE / "goals"
JOURNAL_FILE = GOALS_DIR / "journal.jsonl"
VETOED_FILE = GOALS_DIR / "vetoed_goals.json"
REFUSED_FILE = GOALS_DIR / "refused_goals.json"
BUILD_LOG = FUSION_STATE / "build_goals_will.log"
HNC_STATE_FILE = FUSION_STATE / "hnc_core_state.json"
AUTH_GATE = "system:activate_internal_door"
JOURNAL_ROTATE_BYTES = 10 * 1024 * 1024
_VETOED_CAP = 400
# Refusal rest-memory (same doctrine as learning_will): a non-veto refusal
# (held_incoherent / deferred) whose cause persists would otherwise be
# re-proposed verbatim every cycle — the gates pass-or-hold the same way
# forever and the will treadmills instead of rotating. Refused goal keys
# rest for a TTL, then become askable again. The gates are untouched —
# suppression only stops RE-ASKING; it never answers on the gate's behalf.
# held_incoherent is environmental (HNC state) and usually transient, so it
# rests briefly; deferred (authorization) rests longer. Only real (non-dry)
# internal considerations record memory — a dry run touched nothing.
_REFUSED_CAP = 400
_REFUSED_TTL_S = 6 * 3600        # deferred — rest half a day, re-ask later
_HELD_TTL_S = 30 * 60            # held_incoherent — retry soon after coherence

# Goal-subsystem state files. The engine state has one contract-anchored
# home (aureon_fusion/state/goals/) plus the upstream anchor convention
# (<workspace>/state/goals, via GOAL_STATE_DIR/SERO_WORKSPACE) as a
# fallback — whichever is present is read; absence never crashes.
GOAL_STATE_DIRS = (GOALS_DIR, WORKSPACE / "state" / "goals")
ENGINE_STATE_NAMES = ("quantum_goal_engine_state.json",)
BILLION_STATE_NAMES = ("billion_goal_progress.json",)
PROOF_CHAIN_NAMES = ("margin_proof_chain.jsonl", "proof_chain.jsonl")

OUTCOMES = ("accepted", "vetoed", "held_incoherent", "deferred",
            "silence", "open_goals_active")
_RISK_RANK = {"low": 1, "medium": 2, "high": 3}


# ───────────────────────── small utilities ─────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _append_line(path: Path, line: str) -> None:
    """Append one line to a JSONL file. Inter-process safe on Windows and
    POSIX: an advisory byte-range lock on a sidecar .lock file; on lock
    failure the line degrades to a per-pid sidecar (readers glob both)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    try:
        handle = open(lock_path, "a+b")
        try:
            handle.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)  # noqa: F821
            except (ImportError, OSError):
                handle.close()
                raise _LockUnavailable
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            finally:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)  # noqa: F821
                handle.close()
            return
        except _LockUnavailable:
            pass
        except Exception:
            try:
                handle.close()
            except OSError:
                pass
    except _LockUnavailable:
        pass
    except OSError:
        pass
    # Fallback: per-pid sidecar append (never loses a record).
    try:
        with open(path.with_name(f"{path.name}.pid{os.getpid()}"),
                  "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


class _LockUnavailable(Exception):
    pass


def _rotate_journal() -> None:
    try:
        if JOURNAL_FILE.exists() and \
                JOURNAL_FILE.stat().st_size > JOURNAL_ROTATE_BYTES:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            os.replace(JOURNAL_FILE, JOURNAL_FILE.with_name(
                f"journal.{stamp}.jsonl"))
    except OSError:
        pass


def _blog(event: str, **fields) -> None:
    """Append one JSON line to the build log. Never raises."""
    try:
        rec = {"ts": _utc_now(), "event": event, **fields}
        _append_line(BUILD_LOG, json.dumps(rec, ensure_ascii=False))
    except Exception:
        pass


def _journal(record: dict) -> None:
    """Append one consideration record to the goals journal."""
    _rotate_journal()
    _append_line(JOURNAL_FILE, json.dumps(record, ensure_ascii=False))


def _journal_entries(limit: int = 100) -> list:
    entries = []
    files = []
    if GOALS_DIR.exists():
        files = [JOURNAL_FILE] + sorted(GOALS_DIR.glob("journal.*.jsonl"))
        files += sorted(GOALS_DIR.glob("journal.jsonl.pid*"))
    for path in files:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue
    return entries[-limit:]


# ───────────────────────── state-file discovery ────────────────────────────

def _find_first(names: tuple) -> Path | None:
    """First existing file among GOAL_STATE_DIRS × names, else None."""
    for d in GOAL_STATE_DIRS:
        for name in names:
            p = d / name
            if p.exists():
                return p
    return None


def _count_lines(path: Path) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return 0


def _open_goals() -> dict:
    """Open goals from the quantum goal engine state file. Never crashes:
    absent/corrupt → zero open goals with state_file None."""
    path = _find_first(ENGINE_STATE_NAMES)
    if path is None:
        return {"state_file": None, "present": False, "open_count": 0,
                "open_goals": [], "totals": None}
    data = _read_json(path, None)
    if not isinstance(data, dict):
        return {"state_file": str(path), "present": False, "open_count": 0,
                "open_goals": [], "totals": None}
    active = [g for g in (data.get("active_goals") or []) if isinstance(g, dict)]
    open_goals = [{
        "title": g.get("title") or g.get("description") or "",
        "description": g.get("description") or "",
        "category": g.get("category"),
        "timescale": g.get("timescale"),
        "difficulty": g.get("difficulty"),
        "progress": g.get("progress"),
        "created_at": g.get("created_at"),
    } for g in active]
    totals = {k: data.get(k) for k in (
        "total_goals_created", "total_goals_achieved",
        "total_quantum_achievements", "current_acceleration",
        "last_goal_time") if k in data}
    return {"state_file": str(path), "present": True,
            "open_count": len(open_goals), "open_goals": open_goals,
            "totals": totals or None}


def _billion_state() -> dict:
    """Billion-tracker milestone state from its anchored state file."""
    path = _find_first(BILLION_STATE_NAMES)
    if path is None:
        return {"file": None, "present": False, "milestones": None}
    data = _read_json(path, None)
    if not isinstance(data, dict):
        return {"file": str(path), "present": False, "milestones": None}
    keys = ("current_balance", "dollars_remaining", "rungs_climbed",
            "next_rung_distance", "time_to_next_rung", "ladder_position",
            "daily_velocity", "win_rate", "current_streak", "best_streak",
            "estimated_days_to_goal", "contributions_count")
    milestones = {k: data.get(k) for k in keys if k in data}
    return {"file": str(path), "present": True,
            "milestones": milestones or None}


def _proof_chain() -> dict:
    """Margin proof-chain count: line count of the proof jsonl."""
    path = _find_first(PROOF_CHAIN_NAMES)
    if path is None:
        return {"file": None, "present": False, "proof_count": 0}
    return {"file": str(path), "present": True,
            "proof_count": _count_lines(path)}


# ───────────────────────── coherence (freshness-gated) ─────────────────────

def _read_coherence() -> dict:
    """(gamma, status, age_s) — status ∈ ok | low | missing | corrupt |
    stale. FAIL-CLOSED: anything unreadable, missing, or older than
    HNC_FRESH_S seconds means the gate does not pass."""
    try:
        if not HNC_STATE_FILE.exists():
            return {"gamma": None, "status": "missing", "age_s": None}
        data = json.loads(HNC_STATE_FILE.read_text(encoding="utf-8"))
        gamma = float(data.get("coherence_gamma"))
        if gamma != gamma:  # NaN guard
            return {"gamma": None, "status": "corrupt", "age_s": None}
        stamp = data.get("timestamp")
        try:
            age_s = max(0.0, time.time() - float(stamp))
        except (TypeError, ValueError):
            try:
                age_s = max(0.0, time.time() - HNC_STATE_FILE.stat().st_mtime)
            except OSError:
                age_s = None
        if age_s is None or age_s > HNC_FRESH_S:
            return {"gamma": gamma, "status": "stale", "age_s": age_s}
        if gamma < COHERENCE_THRESHOLD:
            return {"gamma": gamma, "status": "low", "age_s": age_s}
        return {"gamma": gamma, "status": "ok", "age_s": age_s}
    except Exception:
        return {"gamma": None, "status": "corrupt", "age_s": None}


# ───────────────────────── risk grading (descriptive) ──────────────────────

def _risk_grade(goal_text: str) -> dict:
    """Route the goal through the upstream goal-capability map for risk
    grading. Descriptive only — it never gates. Import failure degrades
    to an honest 'unknown' grade, never a crash and never a fabricated
    'low'."""
    routes: list = []
    try:
        upstream = str(AUREON_UPSTREAM)
        if upstream not in sys.path:
            sys.path.insert(0, upstream)
        from aureon.autonomous.aureon_goal_capability_map import (
            recommend_goal_routes,
        )
        routes = recommend_goal_routes(goal_text) or []
    except Exception as exc:
        _blog("risk_grade_error", error=type(exc).__name__)
        return {"highest": "unknown", "routes": [],
                "requires_human": None,
                "error": f"capability map unavailable ({type(exc).__name__})"}
    highest = "low"
    requires_human = False
    for r in routes:
        risk = str((r or {}).get("risk", "low"))
        if _RISK_RANK.get(risk, 0) > _RISK_RANK.get(highest, 0):
            highest = risk if risk in _RISK_RANK else "unknown"
        if (r or {}).get("requires_human"):
            requires_human = True
    return {
        "highest": highest,
        "requires_human": requires_human,
        "routes": [
            {"route": r.get("route"), "risk": r.get("risk"),
             "requires_human": bool(r.get("requires_human"))}
            for r in routes if isinstance(r, dict)
        ],
    }


# ───────────────────────── the gate trio (all fail-closed) ─────────────────

def _check_conscience(goal_text: str, source: str) -> dict:
    desc = (f"Goals will: sovereign goal consideration [source={source}]: "
            f"{(goal_text or '')[:180]}")
    try:
        from aureon_fusion import conscience_hook
        verdict = conscience_hook.evaluate(desc, {"organ": "goals_will"})
        v = (verdict or {}).get("verdict", "VETO")  # unreadable = VETO
        return {
            "verdict": v,
            "reasoning": (verdict or {}).get("reasoning", "")[:300],
            "conditions": list((verdict or {}).get("conditions") or []),
            "sls_score": (verdict or {}).get("sls_score"),
        }
    except Exception as exc:
        # FAIL-CLOSED: a conscience that cannot answer is a conscience
        # that said no.
        return {"verdict": "VETO",
                "reasoning": f"conscience evaluation failed "
                             f"({type(exc).__name__}) — fail-closed VETO",
                "conditions": [], "sls_score": None}


def _check_coherence() -> dict:
    c = _read_coherence()
    gamma, status = c["gamma"], c["status"]
    if status == "ok":
        return {"passed": True, "gamma": gamma, "status": status,
                "age_s": c.get("age_s"), "threshold": COHERENCE_THRESHOLD}
    if status == "low":
        detail = (f"coherence_gamma {gamma:.3f} < {COHERENCE_THRESHOLD} "
                  f"— the organism waits until coherent; it never "
                  f"fabricates goals to fill the gap")
    elif status == "stale":
        detail = (f"hnc_core_state.json stale (age {c.get('age_s'):.0f}s > "
                  f"{HNC_FRESH_S:.0f}s) — coherence unknown; fail-closed HOLD")
    elif status == "missing":
        detail = ("hnc_core_state.json missing — coherence unknown; "
                  "fail-closed HOLD")
    else:
        detail = ("hnc_core_state.json unreadable/corrupt — coherence "
                  "unknown; fail-closed HOLD")
    return {"passed": False, "gamma": gamma, "status": status,
            "age_s": c.get("age_s"), "threshold": COHERENCE_THRESHOLD,
            "detail": detail}


def _check_authorization() -> dict:
    try:
        from aureon_fusion import capability_gate
        verdict = capability_gate.check(AUTH_GATE)
    except Exception as exc:
        return {"passed": False, "verdict": "HOLD",
                "detail": f"capability gate error ({type(exc).__name__}) "
                          f"— deferred", "fail_closed": True}
    allowed = bool((verdict or {}).get("allowed"))
    reason = str((verdict or {}).get("reason", ""))
    missing_row = (verdict or {}).get("verdict") == "DENY" and \
        "no gate defined" in reason
    detail = ((f"matrix row for {AUTH_GATE} not defined yet "
               f"(recorded; retry next cycle)") if missing_row
              else (f"{AUTH_GATE} allowed: {reason[:200]}" if allowed
                    else f"{AUTH_GATE} not allowed: {reason[:200]}"))
    return {"passed": allowed,
            "verdict": (verdict or {}).get("verdict"),
            "missing_row": missing_row, "detail": detail}


# ───────────────────────── veto permanence ─────────────────────────────────

def _goal_key(goal_text: str) -> str:
    return "g:" + hashlib.sha256(
        (goal_text or "").strip().lower().encode("utf-8")).hexdigest()[:16]


def _load_vetoed() -> dict:
    try:
        data = json.loads(VETOED_FILE.read_text(encoding="utf-8"))
        return dict(data.get("vetoed") or {})
    except Exception:
        return {}


def _is_vetoed(goal_text: str) -> bool:
    try:
        return _goal_key(goal_text) in _load_vetoed()
    except Exception:
        return False


def _record_veto(goal_text: str) -> None:
    """Persist a conscience VETO so the will never re-proposes the same
    goal. Fail-closed: any error means nothing is suppressed."""
    try:
        vetoed = _load_vetoed()
        vetoed[_goal_key(goal_text)] = _utc_now()
        if len(vetoed) > _VETOED_CAP:
            oldest = sorted(vetoed.items(), key=lambda kv: kv[1])[
                len(vetoed) - _VETOED_CAP:]
            for k, _ in oldest:
                vetoed.pop(k, None)
        GOALS_DIR.mkdir(parents=True, exist_ok=True)
        tmp = VETOED_FILE.with_name(
            f"{VETOED_FILE.name}.tmp.{os.getpid()}.{time.time_ns()}")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"vetoed": vetoed, "updated_at": _utc_now()},
                          f, indent=2, ensure_ascii=False)
            os.replace(tmp, VETOED_FILE)
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
    except Exception:
        pass


# ───────────────────── refusal rest-memory (time-bound) ────────────────────

def _load_refused() -> dict:
    """goal_key -> refuse-expiry (epoch s). Missing/corrupt -> {} (nothing
    suppressed — the gates still answer every real proposal)."""
    try:
        data = json.loads(REFUSED_FILE.read_text(encoding="utf-8"))
        out = {}
        for k, ts in (data.get("refused") or {}).items():
            try:
                out[str(k)] = float(ts)
            except (TypeError, ValueError):
                continue
        return out
    except Exception:
        return {}


def _is_refused(goal_text: str, now: float | None = None) -> bool:
    try:
        now = now if now is not None else time.time()
        expiry = _load_refused().get(_goal_key(goal_text))
        return expiry is not None and now < expiry
    except Exception:
        return False  # fail-closed: any doubt means nothing is suppressed


def _record_refusal(goal_text: str, ttl_s: float,
                    now: float | None = None) -> None:
    """Persist a non-veto refusal so the will rests the goal until
    now+ttl_s. Fail-closed: any error means nothing is suppressed."""
    try:
        now = now if now is not None else time.time()
        refused = _load_refused()
        refused[_goal_key(goal_text)] = now + float(ttl_s)
        if len(refused) > _REFUSED_CAP:
            oldest = sorted(refused.items(), key=lambda kv: kv[1])[
                len(refused) - _REFUSED_CAP:]
            for k, _ in oldest:
                refused.pop(k, None)
        GOALS_DIR.mkdir(parents=True, exist_ok=True)
        tmp = REFUSED_FILE.with_name(
            f"{REFUSED_FILE.name}.tmp.{os.getpid()}.{time.time_ns()}")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"refused": refused, "updated_at": _utc_now()},
                          f, indent=2, ensure_ascii=False)
            os.replace(tmp, REFUSED_FILE)
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
    except Exception:
        pass


# ───────────────────────── (A) GoalAspiration — internal candidates ───────

class GoalAspiration:
    """Generates goal candidates ONLY from internal state. Never external
    trends, never push feeds. Silence is valid: if nothing is genuinely
    sought, candidates() is empty."""

    def candidates(self) -> list:
        out = []
        out.extend(self._from_proof_chain_gap())
        out.extend(self._from_capability_openings())
        out.extend(self._from_wheel_state())
        # Conscience VETO is permanent; a TTL-bound refusal is temporary rest
        # (see REFUSED_FILE above) — both rotate the will to new ground
        # instead of re-asking the same refused goal every cycle.
        return [c for c in out
                if c.get("desire_score", 0) >= MIN_DESIRE
                and not _is_vetoed(c["goal_text"])
                and not _is_refused(c["goal_text"])]

    def _from_proof_chain_gap(self) -> list:
        """A missing or thin margin proof chain is an internal gap the
        organism can close on its own authority (dry-run, proof-only —
        the capability map grades any margin-flavoured goal 'high' and
        the conscience still holds absolute VETO)."""
        chain = _proof_chain()
        if chain["present"] and chain["proof_count"] > 0:
            return []
        return [{
            "kind": "proof_chain_gap",
            "goal_text": ("Establish the margin proof chain: append the "
                          "first independently verifiable proof record to "
                          "the margin proof ledger."),
            "desire_score": 0.55,
            "origin": {"proof_file": chain["file"], "proof_count": 0},
        }]

    def _from_capability_openings(self) -> list:
        """Capability-matrix rows not yet active/approved are openings
        the organism may will itself toward (authorization stays with
        the matrix owner — proposing is not activating)."""
        from .paths import SERO_AUTONOMOUS
        matrix = _read_json(SERO_AUTONOMOUS / "capability_matrix.json", {})
        gates = matrix.get("gates", {}) if isinstance(matrix, dict) else {}
        open_rows = [k for k, v in gates.items()
                     if isinstance(v, dict)
                     and v.get("status") not in ("active", "approved")]
        if not open_rows:
            return []
        return [{
            "kind": "capability_opening",
            "goal_text": (f"Bring the capability row '{open_rows[0]}' to "
                          f"owner authorization ({len(open_rows)} row(s) "
                          f"not yet active/approved)."),
            "desire_score": 0.35,
            "origin": {"open_rows": open_rows[:8]},
        }]

    def _from_wheel_state(self) -> list:
        """The HNC wheel: below FLOWING, raising the rung is the most
        native goal an organism can hold. Stale/missing state yields
        nothing — never fabricated."""
        c = _read_coherence()
        if c["status"] not in ("ok", "low", "stale"):
            return []
        try:
            data = _read_json(HNC_STATE_FILE, {})
            rung = str(data.get("rung") or data.get("consciousness_level")
                       or "")
            if rung.upper() in ("FLOWING", "FLOW", ""):
                return []
            return [{
                "kind": "wheel_state",
                "goal_text": (f"Raise the HNC wheel from rung '{rung}' to "
                              f"FLOWING (coherence_gamma "
                              f"{(c.get('gamma') or 0):.3f})."),
                "desire_score": 0.45,
                "origin": {"rung": rung, "gamma": c.get("gamma")},
            }]
        except Exception:
            return []


# ───────────────────────── (B) GoalsWill — the contract ────────────────────

class GoalsWill:
    """The sovereign goals will. Fixed public contract:

        status() -> dict                      snapshot of goal state
        propose(goal_text, source="organism") -> {accepted, gates, risk,
                                                  reason, ...}
        consider() -> dict                    one sovereign cycle

    Outcome ∈ accepted | vetoed | held_incoherent | deferred | silence |
    open_goals_active. propose/consider NEVER execute the goal — no
    trades, no process spawns. They offer; the organism chooses.
    """

    def status(self) -> dict:
        coherence = _read_coherence()
        entries = _journal_entries(limit=100)
        last = entries[-1] if entries else None
        goals = _open_goals()
        return {
            "organ": "goals_will",
            "ts": _utc_now(),
            "doctrine": {
                "free_will": True,
                "internal_state_only": True,
                "offers_never_executes": True,
                "gates_fail_closed": ["conscience", "hnc_coherence",
                                      "authorization"],
                "coherence_threshold": COHERENCE_THRESHOLD,
                "hnc_fresh_s": HNC_FRESH_S,
                "silence_is_valid": True,
                "native_reasoning_only": True,
            },
            "coherence": {"gamma": coherence["gamma"],
                          "status": coherence["status"],
                          "age_s": coherence.get("age_s"),
                          "file": str(HNC_STATE_FILE)},
            "goals": goals,
            "billion_tracker": _billion_state(),
            "margin_proof_chain": _proof_chain(),
            "authorization": {
                "gate": AUTH_GATE,
                "matrix_row_present": self._auth_row_present(),
            },
            "refused_memory": {
                "file": str(REFUSED_FILE),
                "resting": len(_load_refused()),
                "held_ttl_s": _HELD_TTL_S,
                "deferred_ttl_s": _REFUSED_TTL_S,
            },
            "last_consideration": last,
            "journal": {
                "file": str(JOURNAL_FILE),
                "recent_entries": len(entries),
                "last_outcome": (last or {}).get("outcome"),
            },
        }

    def __init__(self) -> None:
        # --dry discipline: nested propose() calls from consider(dry_run=True)
        # still run the real gates but journal nothing.
        self._dry = False

    @staticmethod
    def _auth_row_present() -> bool:
        try:
            from .paths import SERO_AUTONOMOUS
            matrix = _read_json(SERO_AUTONOMOUS / "capability_matrix.json", {})
            gates = matrix.get("gates", {}) if isinstance(matrix, dict) else {}
            return isinstance(gates.get(AUTH_GATE), dict)
        except Exception:
            return False

    def _maybe_journal(self, record: dict) -> None:
        if not getattr(self, "_dry", False):
            _journal(record)

    def propose(self, goal_text: str, source: str = "organism") -> dict:
        """Route a goal text through risk grading, then the fail-closed
        gate trio. Returns the consideration verdict; NEVER executes."""
        goal_text = (goal_text or "").strip()
        result = {
            "accepted": False,
            "goal": goal_text,
            "source": source,
            "gates": {},
            "risk": {},
            "reason": "",
            "ts": _utc_now(),
        }
        if not goal_text:
            result["reason"] = "empty goal text — there is nothing to consider"
            _blog("propose", outcome="refused_empty", source=source)
            return result

        result["risk"] = _risk_grade(goal_text)

        conscience = _check_conscience(goal_text, source)
        result["gates"]["conscience"] = conscience
        if conscience.get("verdict") == "VETO":
            result["reason"] = conscience.get(
                "reasoning", "conscience VETO — absolute")
            result["outcome"] = "vetoed"
            _record_veto(goal_text)
            self._maybe_journal({"ts": result["ts"], "verb": "propose",
                      "goal": goal_text[:300], "source": source,
                      "gates": result["gates"], "risk": result["risk"],
                      "outcome": "vetoed", "accepted": False,
                      "reason": result["reason"]})
            _blog("propose", outcome="vetoed", source=source)
            return result

        coherence = _check_coherence()
        result["gates"]["coherence"] = coherence
        if not coherence.get("passed"):
            result["reason"] = coherence.get("detail",
                                              "coherence gate failed")
            result["outcome"] = "held_incoherent"
            if source == "organism_internal" and \
                    not getattr(self, "_dry", False):
                # Rest this goal briefly — the refusal is environmental
                # (HNC state) and transient; re-ask once coherence has had
                # time to return, not every 2-minute cycle.
                _record_refusal(goal_text, _HELD_TTL_S)
            self._maybe_journal({"ts": result["ts"], "verb": "propose",
                      "goal": goal_text[:300], "source": source,
                      "gates": result["gates"], "risk": result["risk"],
                      "outcome": "held_incoherent", "accepted": False,
                      "reason": result["reason"]})
            _blog("propose", outcome="held_incoherent", source=source)
            return result

        auth = _check_authorization()
        result["gates"]["authorization"] = auth
        if not auth.get("passed"):
            result["reason"] = auth.get("detail", "authorization failed")
            result["outcome"] = "deferred"
            if source == "organism_internal" and \
                    not getattr(self, "_dry", False):
                # Rest this goal for the long TTL — authorization state
                # changes on owner/matrix timescales, not cycle timescales;
                # re-ask later instead of every cycle.
                _record_refusal(goal_text, _REFUSED_TTL_S)
            self._maybe_journal({"ts": result["ts"], "verb": "propose",
                      "goal": goal_text[:300], "source": source,
                      "gates": result["gates"], "risk": result["risk"],
                      "outcome": "deferred", "accepted": False,
                      "reason": result["reason"]})
            _blog("propose", outcome="deferred", source=source)
            return result

        result["accepted"] = True
        result["outcome"] = "accepted"
        result["reason"] = ("conscience %s, gamma %.3f (age %.0fs), %s "
                            "allowed — the goal is OFFERED to the "
                            "organism; nothing executes here" % (
                                conscience.get("verdict"),
                                coherence.get("gamma") or 0.0,
                                coherence.get("age_s") or 0.0,
                                AUTH_GATE))
        self._maybe_journal({"ts": result["ts"], "verb": "propose",
                            "goal": goal_text[:300], "source": source,
                            "gates": result["gates"], "risk": result["risk"],
                            "outcome": "accepted", "accepted": True,
                            "reason": result["reason"]})
        _blog("propose", outcome="accepted", source=source)
        return result

    def consider(self, dry_run: bool = False) -> dict:
        """One sovereign consideration cycle. Goals arise from INTERNAL
        state only. With --dry nothing is journaled; the gates are still
        real (a VETO is recorded regardless — permanence is doctrine)."""
        snapshot = self.status()
        if snapshot["goals"]["open_count"] > 0:
            result = {
                "considered": False,
                "outcome": "open_goals_active",
                "reason": (f"{snapshot['goals']['open_count']} goal(s) "
                           "already open — the will does not pile new "
                           "goals on open ones"),
                "ts": _utc_now(),
            }
            if not dry_run:
                _journal({"ts": result["ts"], "verb": "consider",
                          "outcome": "open_goals_active",
                          "open_count": snapshot["goals"]["open_count"],
                          "reason": result["reason"]})
            _blog("consider", outcome="open_goals_active",
                  dry_run=dry_run)
            return result

        candidates = GoalAspiration().candidates()
        if not candidates:
            result = {
                "considered": False,
                "outcome": "silence",
                "reason": ("silence is valid — nothing in internal state "
                           "genuinely seeks a goal right now"),
                "ts": _utc_now(),
            }
            if not dry_run:
                _journal({"ts": result["ts"], "verb": "consider",
                          "outcome": "silence", "reason": result["reason"]})
            _blog("consider", outcome="silence", dry_run=dry_run)
            return result

        candidates.sort(key=lambda c: -c["desire_score"])
        top = candidates[0]
        prev_dry = getattr(self, "_dry", False)
        self._dry = bool(dry_run)
        try:
            proposal = self.propose(top["goal_text"],
                                    source="organism_internal")
        finally:
            self._dry = prev_dry
        result = {
            "considered": True,
            "outcome": proposal.get("outcome"),
            "candidate": top,
            "proposal": proposal,
            "ts": _utc_now(),
        }
        _blog("consider", outcome=proposal.get("outcome"), dry_run=dry_run,
              kind=top.get("kind"))
        return result


# ───────────────────────── CLI ─────────────────────────────────────────────

def _print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.goals_will "
              "status|propose \"text\"|consider [--dry]")
        print("  status    goal state snapshot (engine, billion tracker,")
        print("            proof chain, last consideration)")
        print("  propose   run the gate trio on a goal text (offers only;")
        print("            never executes trades or spawns processes)")
        print("  consider  one sovereign cycle; --dry runs the gates but")
        print("            journals nothing")
        return 0
    verb = argv[0]
    will = GoalsWill()
    if verb == "status":
        _print_json(will.status())
        return 0
    if verb == "propose":
        text = " ".join(argv[1:]).strip()
        if not text or text == "--dry":
            print("usage: propose \"goal text\"", file=sys.stderr)
            return 2
        result = will.propose(text)
        _print_json(result)
        return 0 if result.get("accepted") else 1
    if verb == "consider":
        dry = "--dry" in argv[1:]
        result = will.consider(dry_run=dry)
        _print_json(result)
        return 0 if result.get("outcome") in OUTCOMES else 1
    print(f"unknown verb: {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
