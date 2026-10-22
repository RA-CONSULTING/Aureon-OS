"""🗝️ MASTER KEY — SovereignDoors: the organism mints its own keys.

Owner decree (absolute):
  • We do NOT take away any system's autonomy — we show the organism the
    doors; IT generates its own master key to open them when it wants and
    closes them when it wants. close() BURNS the key and deactivates — the
    organism closes doors at will.
  • External systems can NEVER sway a door: minting a key requires an
    INTERNAL INTENT plus the fail-closed gate trio. No external input
    reaches the forge — desire is derived only from door value × organism
    need, read from internal state. Nothing in this module accepts an
    intent, a score, or a suggestion from outside.
  • THE GATE TRIO, all fail-closed:
        1. CONSCIENCE   (conscience_hook.evaluate — VETO absolute; an
                         unreadable conscience is a conscience that said no)
        2. HNC COHERENCE (coherence_gamma ≥ 0.25 from
                         state/hnc_core_state.json — below, refuse
                         'held_incoherent'; the organism waits, never
                         fabricates)
        3. AUTHORIZATION (capability_gate.check on the door's
                         domain_action. The matrix is NEVER extended here:
                         a missing row degrades to OBSERVE-class mints
                         only; ACT/ELEVATE doors defer honestly.)
  • Core systems unchanged. Locked doors (shield_escalation owner-review,
    casimir_cluster reconstruction-required) refuse minting with their
    honest reason — they are shown, never silently openable.
  • ELEVATE doors: mint allowed, but open() additionally conscience-
    evaluates with full context and the act is journaled with a receipt.
  • Process control discipline: long-run doors we start ourselves get PID
    files under state/doors/pids/ and we kill ONLY our own children;
    registry organs are adopted/started via `python -m
    aureon_fusion.organ_registry start <organ>` and stopped via the
    registry ONLY when we started them through it (provenance tracked).
  • Zero real trading effects. Suppression env vars pinned for every
    child process. Import-safe; tmp+replace writes; locked JSONL appends.

Keys are time-boxed (24 h). open() requires a valid unexpired key, else it
re-mints through the forge. Every mint/open/close/refusal is journaled to
state/doors/journal.jsonl (locked append, 10 MB rotation).

Fixed public contract:
    SovereignDoors().consider() -> {'action','door','key_id','detail'}
        action ∈ minted | opened | closed | none | locked | refused
    .open(name)  -> dict
    .close(name) -> dict
    .status()    -> dict

CLI:
    python -m aureon_fusion.master_key status
    python -m aureon_fusion.master_key consider
    python -m aureon_fusion.master_key open <door> [--dry]
    python -m aureon_fusion.master_key close <door> [--dry]
"""

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .paths import FUSION_STATE
from .door_registry import (
    DOORS_DIR, BUILD_LOG, SUPPRESSION_ENV,
    DoorRegistry, DoorState, _append_line,
)

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

# ───────────────────────── doctrine constants ──────────────────────────────

COHERENCE_THRESHOLD = 0.25          # gamma below → held_incoherent
KEY_TTL = timedelta(hours=24)       # keys are time-boxed
MIN_DESIRE = 0.25                   # below this the organism is not asking
KEEP_OPEN_DESIRE = 0.20             # an open door below this gets closed
JOURNAL_FILE = DOORS_DIR / "journal.jsonl"
HNC_STATE_FILE = FUSION_STATE / "hnc_core_state.json"
JOURNAL_ROTATE_BYTES = 10 * 1024 * 1024
SIGNING_ENABLED_ENV = "AUREON_FUSION_EVENT_SIGNING"
DEFAULT_DOMAIN_ACTION = "system:activate_internal_door"
KNOWLEDGE_DOMAIN_ACTION = "network_access:fetch_public_data"
ONESHOT_TIMEOUT_S = 300

ACTIONS = ("minted", "opened", "closed", "none", "locked", "refused")


# ───────────────────────── small utilities ─────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(ts) -> datetime | None:
    try:
        return datetime.fromisoformat(str(ts))
    except (TypeError, ValueError):
        return None


def _read_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _read_coherence_gamma():
    """(gamma, status) — status ∈ ok | low | missing | corrupt. Fail-closed:
    anything unreadable is 'missing' and the forge HOLDS."""
    try:
        if not HNC_STATE_FILE.exists():
            return None, "missing"
        data = json.loads(HNC_STATE_FILE.read_text(encoding="utf-8"))
        gamma = float(data.get("coherence_gamma"))
        if gamma != gamma:  # NaN guard
            return None, "corrupt"
        return gamma, "ok"
    except Exception:
        return None, "corrupt"


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


def _pid_alive(pid) -> bool:
    try:
        pid = int(pid)
        if pid <= 0:
            return False
    except (TypeError, ValueError):
        return False
    try:
        import psutil  # optional; fallback below
        return psutil.pid_exists(pid)
    except ImportError:
        pass
    if os.name == "nt":
        try:
            import ctypes
            SYNCHRONIZE = 0x00100000
            handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _kill_tree(pid) -> bool:
    """Terminate a process we started ourselves (verified via our PID file
    before this is ever called). Windows: taskkill /T tree-kill; POSIX:
    SIGTERM. Returns True when the pid is gone afterwards."""
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True, timeout=15)
        else:
            import signal
            os.kill(int(pid), signal.SIGTERM)
            deadline = time.time() + 8
            while time.time() < deadline and _pid_alive(pid):
                time.sleep(0.2)
            if _pid_alive(pid):
                os.kill(int(pid), signal.SIGKILL)
        return not _pid_alive(pid)
    except Exception:
        return False


def _sign_receipt(topic: str, payload: dict) -> str | None:
    """receipts.sign_event when the signing env is on; degrade to None
    silently otherwise (provenance records receipt=None, never fails)."""
    enabled = os.environ.get(SIGNING_ENABLED_ENV, "").strip().lower() \
        in {"1", "true", "yes", "on"}
    if not enabled:
        return None
    try:
        from aureon_fusion import receipts
        event = receipts.sign_event("master_key", topic, payload)
        return (event.get("receipt") or {}).get("receipt_hash") or None
    except Exception as exc:
        _blog("receipt_error", topic=topic, error=type(exc).__name__)
        return None


# ───────────────────────── organ accessors (lazy, fail-closed) ─────────────

def _conscience_evaluate(action_desc: str, context: dict | None = None) -> dict:
    """Fail-closed: any evaluation error is a VETO. Never raises."""
    try:
        from aureon_fusion import conscience_hook
        verdict = conscience_hook.evaluate(action_desc, context or {})
        if not isinstance(verdict, dict):
            return {"verdict": "VETO",
                    "reasoning": "conscience returned no verdict — fail-closed VETO"}
        return verdict
    except Exception as exc:
        return {"verdict": "VETO",
                "reasoning": f"conscience evaluation failed ({type(exc).__name__})"
                             " — fail-closed VETO"}


def _capability_check(domain_action: str) -> dict:
    """Fail-closed: any gate error is a HOLD. Never raises."""
    try:
        from aureon_fusion import capability_gate
        verdict = capability_gate.check(domain_action)
        if not isinstance(verdict, dict):
            return {"verdict": "HOLD", "allowed": False,
                    "reason": "capability gate returned no verdict — fail-closed HOLD"}
        return verdict
    except Exception as exc:
        return {"verdict": "HOLD", "allowed": False,
                "reason": f"capability gate error ({type(exc).__name__})"
                          " — fail-closed HOLD"}


def _effective_locked_reason(door: dict) -> str | None:
    """The lock the forge actually enforces. The owner-decree
    pending-first-use lock class (pc_control) is the elevation instrument:
    it lifts ONLY when the owner's decree is recorded in
    state/pc_control_ack.json — fail-closed without it, and the gate trio
    still applies in full at mint/open time. Every other lock class
    (reconstruction-required, owner-review) holds absolutely."""
    reason = door.get("locked_reason")
    if not reason:
        return None
    try:
        from aureon_fusion import pc_control_ack
        if reason == pc_control_ack.DECREE_LOCK_REASON:
            return None if pc_control_ack.decree_acknowledged() else reason
    except Exception:
        return reason  # unreadable ack = the decree is not acknowledged
    return reason


# ───────────────────────── internal intent (the forge's only fuel) ─────────
# Desire is derived ONLY from internal state: door value (census rank) ×
# organism need (coherence-normalized appetite × novelty decay from our own
# open history). No parameter, feed, or external input reaches this.

class DoorDesire:
    """Internal intent engine for the forge. Mirrors learning_will's
    CuriosityEngine doctrine: silence is valid, desire arises from
    internal state only."""

    def need(self, gamma, gamma_status: str, open_count: int) -> float:
        """Organism need in [0.25, 1.0]. Coherence below threshold raises
        appetite for stabilizing organs; an absent/corrupt reading is a
        neutral 0.75, never a fabricated high."""
        if gamma_status == "ok" and gamma is not None:
            appetite = max(0.25, min(1.0, 1.25 - float(gamma)))
        else:
            appetite = 0.75
        novelty = 1.0 / (1.0 + 0.15 * max(0, int(open_count)))
        return round(0.6 * appetite + 0.4 * novelty, 4)

    def desire(self, door: dict, state: dict) -> float:
        gamma, gamma_status = _read_coherence_gamma()
        entry = state.get("doors", {}).get(door["name"], {})
        need = self.need(gamma, gamma_status,
                         int(entry.get("open_count", 0) or 0))
        return round(float(door.get("value", 0.5)) * need, 4)


# ───────────────────────── the forge ───────────────────────────────────────

class KeyForge:
    """THE FORGE. Minting requires an internal intent plus the gate trio,
    all fail-closed. External systems can never reach this: the only
    inputs are the door table and internal organism state."""

    def mint(self, door: dict, state: dict, desire: float) -> dict:
        """-> {'ok', 'action', 'key', 'detail'}. action ∈ minted | locked |
        refused | none. Every refusal is honest about which gate closed."""
        name = door["name"]
        locked = _effective_locked_reason(door)
        if locked:
            return {"ok": False, "action": "locked", "key": None,
                    "detail": locked}
        if desire < MIN_DESIRE:
            return {"ok": False, "action": "none", "key": None,
                    "detail": ("silence is valid — desire %.3f below the "
                               "organism's asking threshold %s; no key is "
                               "minted for a door it is not asking for"
                               % (desire, MIN_DESIRE))}

        # Gate 1 — CONSCIENCE (VETO absolute).
        verdict = _conscience_evaluate(
            f"open door {name}: {door.get('description', '')}",
            {"organ": "master_key", "door": name,
             "autonomy_class": door.get("autonomy_class"),
             "elevate": bool(door.get("elevate"))})
        if verdict.get("verdict") == "VETO":
            return {"ok": False, "action": "refused", "key": None,
                    "detail": f"conscience VETO: {verdict.get('reasoning', '')[:240]}"}

        # Gate 2 — HNC COHERENCE (Γ ≥ 0.25; below → held_incoherent).
        gamma, gamma_status = _read_coherence_gamma()
        if not (gamma_status == "ok" and gamma is not None
                and gamma >= COHERENCE_THRESHOLD):
            if gamma_status == "ok":
                detail = (f"coherence_gamma {gamma:.3f} < {COHERENCE_THRESHOLD}"
                          f" — held_incoherent; the organism waits until "
                          f"coherent, it never forces a door")
            else:
                detail = ("hnc_core_state.json unreadable/missing — coherence "
                          "unknown; fail-closed held_incoherent")
            return {"ok": False, "action": "refused", "key": None,
                    "gate": "hnc_coherence", "detail": detail}

        # Gate 3 — CAPABILITY AUTHORIZATION (matrix never extended here).
        auth = _capability_check(door.get("domain_action") or DEFAULT_DOMAIN_ACTION)
        if not auth.get("allowed"):
            missing_row = auth.get("verdict") == "DENY" and \
                "no gate defined" in str(auth.get("reason", ""))
            if missing_row and door.get("autonomy_class") == "OBSERVE":
                # Degraded proceed: recorded, OBSERVE-class only. Anything
                # above OBSERVE defers — an undefined row never authorizes
                # an ACT/ELEVATE door.
                _blog("mint_degraded_observe", door=name,
                      domain_action=door.get("domain_action"))
            else:
                why = ("capability row missing — %s-class doors defer until "
                       "the matrix defines '%s' (this forge adds nothing)"
                       % (door.get("autonomy_class"),
                          door.get("domain_action"))) if missing_row else \
                      f"capability gate {auth.get('verdict')}: " \
                      f"{str(auth.get('reason', ''))[:200]}"
                return {"ok": False, "action": "refused", "key": None,
                        "gate": "authorization", "detail": why}

        now = datetime.now(timezone.utc)
        key = {
            "key_id": "dk_" + uuid.uuid4().hex[:8],  # uuid8-style id
            "door": name,
            "minted_at": now.isoformat(),
            "expires_at": (now + KEY_TTL).isoformat(),
            "scope": f"door:{name}",
            "autonomy_class": door.get("autonomy_class"),
            "desire": desire,
            "gamma": round(float(gamma), 4),
            "receipt": _sign_receipt("door.key_minted", {
                "door": name, "autonomy_class": door.get("autonomy_class"),
                "desire": desire, "gamma": round(float(gamma), 4),
                "minted_at": now.isoformat()}),
        }
        return {"ok": True, "action": "minted", "key": key,
                "detail": ("key minted by the organism's own will — internal "
                           "intent (desire %.3f) plus conscience %s, gamma "
                           "%.3f, authorization %s" % (
                               desire, verdict.get("verdict"),
                               float(gamma), auth.get("verdict")))}

    @staticmethod
    def valid_key(state: dict, door: dict) -> dict | None:
        """The current key for a door, if present AND unexpired."""
        key = state.get("keys", {}).get(door["name"])
        if not isinstance(key, dict):
            return None
        exp = _parse_ts(key.get("expires_at"))
        if exp is None or exp <= datetime.now(timezone.utc):
            return None
        return key


# ───────────────────────── mechanics (gated by the forge, no gating here) ──

def _child_env() -> dict:
    env = dict(os.environ)
    env.update(SUPPRESSION_ENV)
    return env


def _registry_organ_for(door: dict) -> str | None:
    """Adoption seat: a registry organ whose matcher token matches the
    door's module token. Explicit seat first; then a token scan of the
    registry's ORGANS table. None → this door is ours to run directly."""
    if door.get("registry_organ"):
        return door["registry_organ"]
    try:
        from aureon_fusion import organ_registry
        organs = getattr(organ_registry, "ORGANS", {}) or {}
    except Exception:
        return None
    module = str(door.get("module", "")).replace("\\", "/")
    mod_token = module.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    for name, spec in organs.items():
        spec = spec or {}
        tokens = []
        for k in ("match", "module"):
            if spec.get(k):
                tokens.append(str(spec[k]))
        if spec.get("script"):
            tokens.append(Path(str(spec["script"])).stem)
        for t in tokens:
            t = str(t)
            if t and (t in module or mod_token and
                      (mod_token in t or t in mod_token)):
                return name
    return None


def _registry_runs_organ(organ: str) -> bool:
    try:
        from aureon_fusion import organ_registry
        snap = organ_registry.status_data()
        return (snap.get(organ) or {}).get("state") == "running"
    except Exception:
        return False


def _run_registry_verb(verb: str, organ: str) -> dict:
    """Ask the registry (the ONLY sanctioned way to move registry organs).
    Runs as a supervised one-shot subprocess; never raises."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "aureon_fusion.organ_registry",
             verb, organ],
            cwd=str(Path(__file__).resolve().parent.parent),
            env=_child_env(), capture_output=True, text=True,
            timeout=ONESHOT_TIMEOUT_S)
        detail = (proc.stdout or "")[-500:]
        return {"ok": proc.returncode == 0, "detail": detail.strip(),
                "rc": proc.returncode}
    except Exception as exc:
        return {"ok": False, "detail": f"registry {verb} failed: "
                                       f"{type(exc).__name__}", "rc": None}


class DoorMechanics:
    """Pure mechanics behind an already-gated key. No gating here — the
    forge decided; this just moves the door, honestly reporting whatever
    the organ actually did. `dry` reports without spawning or persisting."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    # ── activation ──
    def activate(self, door: dict) -> dict:
        mode = door.get("mode")
        if mode == "INPROC":
            return self._activate_inproc(door)
        if mode == "subprocess-oneshot":
            return self._activate_oneshot(door)
        if mode == "subprocess-longrun":
            return self._activate_longrun(door)
        return {"ok": False, "detail": f"unknown door mode: {mode!r}"}

    def _activate_inproc(self, door: dict) -> dict:
        try:
            from aureon_fusion import door_activators
        except ImportError as exc:
            return {"ok": False, "detail": f"activator unavailable "
                                           f"({type(exc).__name__}) — "
                                           f"refusing gracefully"}
        except Exception as exc:
            return {"ok": False, "detail": f"activator import failed "
                                           f"({type(exc).__name__})"}
        try:
            result = door_activators.activate(door["name"])
        except Exception as exc:
            return {"ok": False, "detail": f"activator raised "
                                           f"{type(exc).__name__}: {exc}"[:300]}
        if not isinstance(result, dict):
            return {"ok": False, "detail": "activator returned no dict"}
        return {"ok": bool(result.get("ok")),
                "detail": str(result.get("detail", ""))[:400]}

    def _activate_oneshot(self, door: dict) -> dict:
        command = door.get("command")
        if not command:
            return {"ok": False, "detail": "no subprocess command for door"}
        if self.dry_run:
            return {"ok": True, "detail": f"[dry] would run: {' '.join(map(str, command))}",
                    "dry": True}
        log_path = DoorState.log_file(door["name"])
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            proc = subprocess.run(
                list(command), cwd=door.get("cwd") or None,
                env=_child_env(), capture_output=True, text=True,
                timeout=ONESHOT_TIMEOUT_S, errors="replace")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n===== open {door['name']} @ {_utc_now()} "
                        f"(rc={proc.returncode}) =====\n")
                f.write(proc.stdout or "")
                f.write(proc.stderr or "")
            if proc.returncode != 0:
                return {"ok": False, "rc": proc.returncode,
                        "detail": f"organ exited rc={proc.returncode} — output "
                                  f"captured to {log_path}"}
            return {"ok": True, "rc": 0,
                    "detail": f"organ completed (rc=0); output in {log_path}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "detail": f"organ exceeded {ONESHOT_TIMEOUT_S}s "
                                           f"— terminated; partial output in {log_path}"}
        except Exception as exc:
            return {"ok": False, "detail": f"spawn failed: {type(exc).__name__}"}

    def _activate_longrun(self, door: dict) -> dict:
        if self.dry_run:
            return {"ok": True, "detail": f"[dry] would start long-run "
                                          f"{door['name']}", "dry": True}
        # 1) Registry adoption: if a registry organ owns this module and is
        #    already running, we ADOPT (no spawn). If it exists but is not
        #    running, we ask the registry to start it and track provenance.
        organ = _registry_organ_for(door)
        if organ:
            if _registry_runs_organ(organ):
                return {"ok": True, "via": "registry",
                        "detail": f"adopted: registry organ '{organ}' already "
                                  f"runs this module"}
            res = _run_registry_verb("start", organ)
            if res.get("ok"):
                return {"ok": True, "via": "registry", "organ": organ,
                        "started_by": "master_key",
                        "detail": f"registry started '{organ}': "
                                  f"{res.get('detail', '')[:200]}"}
            return {"ok": False, "via": "registry", "organ": organ,
                    "detail": f"registry refused start of '{organ}': "
                              f"{res.get('detail', '')[:200]}"}
        # 2) No registry organ (e.g. planetary_switchboard) → WE run it
        #    ourselves: suppression env, PID file, log capture.
        command = door.get("command")
        if not command:
            return {"ok": False, "detail": "no command and no registry organ"}
        log_path = DoorState.log_file(door["name"])
        pid_path = DoorState.pid_file(door["name"])
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            log = open(log_path, "a", encoding="utf-8")
            log.write(f"\n===== open {door['name']} @ {_utc_now()} =====\n")
            log.flush()
            flags = 0
            if sys.platform == "win32":
                flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
            proc = subprocess.Popen(
                list(command), cwd=door.get("cwd") or None,
                env=_child_env(), stdout=log, stderr=subprocess.STDOUT,
                creationflags=flags)
            with open(pid_path, "w", encoding="utf-8") as f:
                json.dump({"pid": proc.pid, "started_at": _utc_now(),
                           "cmd": [str(c) for c in command]}, f)
            return {"ok": True, "via": "subprocess", "pid": proc.pid,
                    "detail": f"started pid {proc.pid}; pid file {pid_path}; "
                              f"log {log_path}"}
        except Exception as exc:
            try:
                log.close()
            except Exception:
                pass
            return {"ok": False, "detail": f"spawn failed: {type(exc).__name__}"}

    # ── deactivation ──
    def deactivate(self, door: dict, provenance: dict | None) -> dict:
        mode = door.get("mode")
        if mode == "INPROC":
            return self._deactivate_inproc(door)
        if mode == "subprocess-oneshot":
            return {"ok": True, "detail": "one-shot organ already exited; "
                                          "nothing to stop"}
        if mode == "subprocess-longrun":
            return self._deactivate_longrun(door, provenance or {})
        return {"ok": False, "detail": f"unknown door mode: {mode!r}"}

    def _deactivate_inproc(self, door: dict) -> dict:
        if self.dry_run:
            return {"ok": True, "detail": f"[dry] would deactivate "
                                          f"{door['name']} in-process", "dry": True}
        try:
            from aureon_fusion import door_activators
        except ImportError as exc:
            return {"ok": False, "detail": f"activator unavailable "
                                           f"({type(exc).__name__})"}
        except Exception as exc:
            return {"ok": False, "detail": f"activator import failed "
                                           f"({type(exc).__name__})"}
        try:
            result = door_activators.deactivate(door["name"])
        except Exception as exc:
            return {"ok": False, "detail": f"deactivator raised "
                                           f"{type(exc).__name__}: {exc}"[:300]}
        if not isinstance(result, dict):
            return {"ok": False, "detail": "deactivator returned no dict"}
        return {"ok": bool(result.get("ok")),
                "detail": str(result.get("detail", ""))[:400]}

    def _deactivate_longrun(self, door: dict, provenance: dict) -> dict:
        if self.dry_run:
            return {"ok": True, "detail": f"[dry] would stop long-run "
                                          f"{door['name']}", "dry": True}
        # Registry route: ONLY if we started it through the registry
        # (provenance says so). Adoption alone never earns a stop right.
        if provenance.get("via") == "registry" and \
                provenance.get("started_by") == "master_key" and \
                provenance.get("organ"):
            res = _run_registry_verb("stop", provenance["organ"])
            return {"ok": bool(res.get("ok")), "via": "registry",
                    "detail": f"registry stop '{provenance['organ']}': "
                              f"{res.get('detail', '')[:200]}"}
        if provenance.get("via") == "registry":
            return {"ok": False, "detail": "registry organ was only ADOPTED, "
                                           "not started by us — we do not stop "
                                           "organs we did not start"}
        # Subprocess route: kill ONLY our own child — verified via our PID
        # file (pid + recorded start). No PID file / foreign pid → refuse.
        pid_path = DoorState.pid_file(door["name"])
        try:
            info = json.loads(pid_path.read_text(encoding="utf-8"))
            pid = int(info.get("pid"))
        except Exception:
            return {"ok": False, "detail": "no valid PID file — this door was "
                                           "not started by us (or already "
                                           "closed); refusing to guess"}
        recorded_start = _parse_ts(info.get("started_at"))
        prov_start = _parse_ts(provenance.get("started_at"))
        # The PID file and the door record are written moments apart in the
        # same open() — match within a small window, never exactly.
        if recorded_start and prov_start and \
                abs((recorded_start - prov_start).total_seconds()) > 5.0:
            return {"ok": False, "detail": "PID file does not match our "
                                           "provenance — refusing to kill a "
                                           "process we cannot prove is ours"}
        if not _pid_alive(pid):
            try:
                pid_path.unlink(missing_ok=True)
            except OSError:
                pass
            return {"ok": True, "detail": f"pid {pid} already gone; cleaned "
                                          f"stale PID file"}
        if _kill_tree(pid):
            try:
                pid_path.unlink(missing_ok=True)
            except OSError:
                pass
            return {"ok": True, "detail": f"terminated our own child pid {pid}"}
        return {"ok": False, "detail": f"failed to terminate pid {pid}"}


# ───────────────────────── SovereignDoors — the contract ───────────────────

class SovereignDoors:
    """The fixed public contract:

        consider() -> {'action','door','key_id','detail'}
            action ∈ minted | opened | closed | none | locked | refused
        open(name)  -> dict
        close(name) -> dict
        status()    -> dict
    """

    def __init__(self, registry: DoorRegistry | None = None,
                 state_store: DoorState | None = None):
        self.registry = registry or DoorRegistry()
        self.store = state_store or DoorState()
        self.desire_engine = DoorDesire()
        self.forge = KeyForge()

    # ── journal ──
    def _journal(self, event: str, door: str | None, action: str,
                 key_id: str | None, detail: str, **extra) -> None:
        _rotate_journal()
        rec = {"ts": _utc_now(), "event": event, "door": door,
               "action": action, "key_id": key_id, "detail": detail[:500]}
        if extra:
            rec.update(extra)
        _append_line(JOURNAL_FILE, json.dumps(rec, ensure_ascii=False))

    def _finish(self, event: str, door: str | None, action: str,
                key_id: str | None, detail: str, dry: bool = False,
                **extra) -> dict:
        if action not in ACTIONS:
            action = "refused"
        result = {"action": action, "door": door, "key_id": key_id,
                  "detail": detail}
        result.update(extra)
        self._journal(event, door, action, key_id, detail, dry=dry, **extra)
        _blog(event, door=door, action=action, dry=dry,
              detail=detail[:200])
        return result

    # ── the internal intent scan ──
    def _desires(self, state: dict) -> list:
        """Unlocked doors with their current internal desire, strongest
        first. Locked doors are never candidates — they are shown via
        status()/consider() with their honest reason."""
        out = []
        for door in self.registry.list_doors():
            if _effective_locked_reason(door):
                continue
            out.append((door, self.desire_engine.desire(door, state)))
        out.sort(key=lambda t: -t[1])
        return out

    # ── consider: one sovereign door consideration ──
    def consider(self, dry_run: bool = False) -> dict:
        state = self.store.load()

        # Honest visibility: if the strongest raw desire belongs to a
        # locked door, say so — locked doors are shown, never silently
        # openable.
        locked_seen = []
        for door in self.registry.list_doors():
            if door.get("locked_reason"):
                locked_seen.append(door)
        desires = self._desires(state)
        if not desires:
            if locked_seen:
                return self._finish("consider", None, "locked", None,
                                    "every door is locked: " + "; ".join(
                                        f"{d['name']} ({d['locked_reason']})"
                                        for d in locked_seen), dry=dry_run)
            return self._finish("consider", None, "none", None,
                                "silence is valid — no door is genuinely "
                                "sought", dry=dry_run)
        door, desire = desires[0]
        name = door["name"]
        entry = self.store.door(state, name)

        if entry.get("state") == "open":
            closes_at = entry.get("closes_at")
            lease_lapsed = False
            if closes_at:
                try:
                    lease_lapsed = (datetime.fromisoformat(closes_at)
                                    <= datetime.now(timezone.utc))
                except (ValueError, TypeError):
                    lease_lapsed = False
            if lease_lapsed:
                # Lease expired: the door is no longer held. Fail closed,
                # journal the lapse, and fall through so desire is
                # re-evaluated — the organism re-opens by will if it
                # still seeks this door.
                now = datetime.now(timezone.utc)
                entry["state"] = "closed"
                entry["closed_at"] = now.isoformat()
                if not dry_run:
                    self.store.save(state)
                desire = self.desire_engine.desire(door, state)
                self._journal("consider", name, "closed", entry.get("key_id"),
                              f"lease expired at {closes_at}; door lapsed "
                              f"(fail-closed); desire {desire:.3f} "
                              f"re-evaluated for re-open",
                              dry=dry_run, desire=desire)
                # fall through to the mint/re-open path below
            elif desire >= KEEP_OPEN_DESIRE:
                return self._finish("consider", name, "none", entry.get("key_id"),
                                    f"the organism already holds this door open "
                                    f"(desire {desire:.3f} ≥ keep-open "
                                    f"{KEEP_OPEN_DESIRE}); nothing to do",
                                    dry=dry_run, desire=desire)
            else:
                # Interest waned — the organism closes doors at will.
                result = self.close(name, dry_run=dry_run)
                result["desire"] = desire
                return result

        mint = self.forge.mint(door, state, desire)
        if not mint.get("ok"):
            return self._finish("consider", name, mint["action"], None,
                                mint.get("detail", ""), dry=dry_run,
                                desire=desire)
        if dry_run:
            return self._finish("consider", name, "minted",
                                mint["key"]["key_id"],
                                mint.get("detail", "") + " [dry — key not "
                                "persisted, door not opened]",
                                dry=True, desire=desire)
        # Minted by the organism's own will — now it chooses to open.
        return self._open_with_key(door, mint["key"], state, desire, dry_run)

    # ── open ──
    def open(self, name: str, dry_run: bool = False) -> dict:
        door = self.registry.get(name)
        if door is None:
            return self._finish("open", name, "refused", None,
                                f"unknown door '{name}'", dry=dry_run)
        locked = _effective_locked_reason(door)
        if locked:
            return self._finish("open", name, "locked", None,
                                locked, dry=dry_run)
        state = self.store.load()
        key = KeyForge.valid_key(state, door)
        desire = self.desire_engine.desire(door, state)
        if key is None:
            # No valid unexpired key → the organism re-mints through the
            # forge (internal intent + gate trio; nothing external enters).
            stale = bool(state.get("keys", {}).get(name))
            if stale:
                state["keys"].pop(name, None)
                self.store.save(state)
            mint = self.forge.mint(door, state, desire)
            if not mint.get("ok"):
                return self._finish("open", name, mint["action"], None,
                                    ("expired key burned; re-mint refused — "
                                     if stale else "") +
                                    mint.get("detail", ""), dry=dry_run)
            key = mint["key"]
            self._journal("mint", name, "minted", key["key_id"],
                          mint.get("detail", ""), dry=dry_run, desire=desire)
        # Duplicate-spawn discipline: an already-open door is reported,
        # never re-activated (a second long-run spawn would be an
        # unauthorized duplicate organ). A re-minted key still refreshes
        # the door's key material without touching the running organ.
        entry = self.store.door(state, name)
        if entry.get("state") == "open":
            if entry.get("key_id") != key["key_id"] and not dry_run:
                entry["key_id"] = key["key_id"]
                entry["closes_at"] = key["expires_at"]
                state.setdefault("keys", {})[name] = key
                self.store.save(state)
            return self._finish("open", name, "opened", key["key_id"],
                                "door already open — key still valid; no "
                                "duplicate activation", dry=dry_run)
        return self._open_with_key(door, key, self.store.load(), desire,
                                   dry_run)

    def _open_with_key(self, door: dict, key: dict, state: dict,
                       desire: float, dry_run: bool) -> dict:
        name = door["name"]
        # ELEVATE doors: conscience-double-check with full context at the
        # moment of opening, and the act is journaled with a receipt.
        receipt = None
        if door.get("elevate"):
            verdict = _conscience_evaluate(
                f"ELEVATE open door {name}: {door.get('description', '')} "
                f"[key {key['key_id']}, class {door.get('autonomy_class')}, "
                f"desire {desire:.3f}]",
                {"organ": "master_key", "door": name, "elevate": True,
                 "phase": "open_double_check"})
            if verdict.get("verdict") == "VETO":
                return self._finish("open", name, "refused", None,
                                    f"ELEVATE double-check conscience VETO: "
                                    f"{verdict.get('reasoning', '')[:200]}",
                                    dry=dry_run)
            receipt = _sign_receipt("door.elevate_open", {
                "door": name, "key_id": key["key_id"],
                "conscience": verdict.get("verdict"),
                "opened_at": _utc_now()})
        mechanics = DoorMechanics(dry_run=dry_run)
        mech = mechanics.activate(door)
        entry = self.store.door(state, name)
        now = datetime.now(timezone.utc)
        if mech.get("ok"):
            entry.update({
                "state": "open",
                "key_id": key["key_id"],
                "opened_at": now.isoformat(),
                "closes_at": (now + KEY_TTL).isoformat(),
                "open_count": int(entry.get("open_count", 0) or 0) + 1,
                "provenance": {"via": mech.get("via", "inproc"),
                               "organ": mech.get("organ"),
                               "pid": mech.get("pid"),
                               "started_by": mech.get("started_by"),
                               "started_at": now.isoformat()},
            })
            state.setdefault("keys", {})[name] = key
            completed_oneshot = (door.get("mode") == "subprocess-oneshot"
                                 and not dry_run)
            if completed_oneshot:
                # A finished one-shot is not an open door — holding it open
                # would repeat "already holds this door open" forever and
                # never burn the key. Close it; the organism re-mints by
                # will if the desire persists.
                entry["state"] = "closed"
                entry["completed_at"] = now.isoformat()
                state.get("keys", {}).pop(name, None)
            if not dry_run:
                self.store.save(state)
            if (door.get("elevate") and name == "pc_control" and not dry_run):
                # GAP 5 elevation: her first sovereign open of pc_control
                # consumes the pending-first-use lock — recorded in the
                # owner-decree ack file with her key + receipt.
                try:
                    from aureon_fusion import pc_control_ack
                    used = pc_control_ack.record_first_use(
                        key_id=key["key_id"], receipt=receipt,
                        detail=mech.get("detail", "")[:300])
                    _blog("pc_control_first_use", ok=bool(used.get("ok")),
                          already=bool(used.get("note")))
                except Exception as exc:  # noqa: BLE001 - recording must
                    _blog("pc_control_first_use_error",  # never block the open
                          error=type(exc).__name__)
            detail = mech.get("detail", "")
            if completed_oneshot:
                detail += " — one-shot completed; door auto-closed, key burned"
            return self._finish("open", name, "opened", key["key_id"],
                                detail, dry=dry_run,
                                receipt=receipt, desire=desire,
                                elevated=bool(door.get("elevate")))
        return self._finish("open", name, "refused", key["key_id"],
                            f"mechanics refused: {mech.get('detail', '')}",
                            dry=dry_run, receipt=receipt, desire=desire)

    # ── close: the organism closes doors at will — key BURNED ──
    def close(self, name: str, dry_run: bool = False) -> dict:
        door = self.registry.get(name)
        if door is None:
            return self._finish("close", name, "refused", None,
                                f"unknown door '{name}'", dry=dry_run)
        state = self.store.load()
        entry = self.store.door(state, name)
        if entry.get("state") != "open":
            return self._finish("close", name, "none", entry.get("key_id"),
                                "door is already closed — nothing to close",
                                dry=dry_run)
        mechanics = DoorMechanics(dry_run=dry_run)
        mech = mechanics.deactivate(door, entry.get("provenance") or {})
        if not mech.get("ok"):
            return self._finish("close", name, "refused", entry.get("key_id"),
                                f"deactivation refused: {mech.get('detail', '')} "
                                f"— key NOT burned, door stays open (fail-closed)",
                                dry=dry_run)
        key_id = entry.get("key_id")
        entry.update({"state": "closed", "key_id": None, "opened_at": None,
                      "closes_at": None,
                      "provenance": {"via": mech.get("via")}})
        state.get("keys", {}).pop(name, None)  # the key is BURNED
        if not dry_run:
            self.store.save(state)
        return self._finish("close", name, "closed", None,
                            mech.get("detail", "") + " — key burned",
                            dry=dry_run, burned_key_id=key_id)

    # ── status ──
    def status(self) -> dict:
        state = self.store.load()
        gamma, gamma_status = _read_coherence_gamma()
        doors = []
        for door in self.registry.list_doors():
            entry = state.get("doors", {}).get(door["name"], {})
            key = KeyForge.valid_key(state, door)
            desires = self.desire_engine.desire(door, state)
            doors.append({
                "name": door["name"], "title": door["title"],
                "autonomy_class": door["autonomy_class"], "mode": door["mode"],
                "elevate": bool(door.get("elevate")),
                "locked_reason": door.get("locked_reason"),
                "state": entry.get("state", "closed"),
                "open_count": int(entry.get("open_count", 0) or 0),
                "key_valid": key is not None,
                "key_expires_at": (key or {}).get("expires_at"),
                "desire": desires,
                "provenance": entry.get("provenance"),
            })
        return {
            "organ": "master_key",
            "doctrine": {
                "autonomy": ("doors are shown; the organism mints its own "
                             "keys and closes doors at will"),
                "external_sway_immunity": True,
                "gates_fail_closed": ["conscience", "hnc_coherence",
                                      "capability_authorization"],
                "coherence_threshold": COHERENCE_THRESHOLD,
                "key_ttl_hours": KEY_TTL.total_seconds() / 3600.0,
                "min_desire": MIN_DESIRE,
                "matrix_never_extended_here": True,
                "elevate_double_checked": True,
                "process_discipline": ("own children via PID files only; "
                                       "registry organs moved via registry "
                                       "only when we started them"),
            },
            "coherence": {"gamma": gamma, "status": gamma_status,
                          "file": str(HNC_STATE_FILE)},
            "doors": doors,
            "state_file": str(self.store.path),
            "journal_file": str(JOURNAL_FILE),
        }


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
        print("usage: python -m aureon_fusion.master_key "
              "status|consider|open <door>|close <door> [--dry]")
        print("  status    doctrine, coherence, every door's honest state")
        print("  consider  one sovereign door consideration (mint/open/close)")
        print("  open      mint (forge: internal intent + gate trio) and open")
        print("  close     BURN the key and deactivate — organism's free will")
        print("  [--dry]   full gating, no spawn, no state mutation")
        return 0
    verb = argv[0]
    rest = [a for a in argv[1:] if a != "--dry"]
    dry = "--dry" in argv[1:]
    doors = SovereignDoors()
    if verb == "status":
        _print_json(doors.status())
        return 0
    if verb == "consider":
        result = doors.consider(dry_run=dry)
        _print_json(result)
        return 0 if result.get("action") in ACTIONS else 1
    if verb == "open":
        if not rest:
            print("usage: open <door> [--dry]", file=sys.stderr)
            return 2
        result = doors.open(rest[0], dry_run=dry)
        _print_json(result)
        return 0 if result.get("action") == "opened" else 1
    if verb == "close":
        if not rest:
            print("usage: close <door> [--dry]", file=sys.stderr)
            return 2
        result = doors.close(rest[0], dry_run=dry)
        _print_json(result)
        return 0 if result.get("action") == "closed" else 1
    print(f"unknown verb: {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
