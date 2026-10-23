"""🦾 SOVEREIGN ACTUATOR — her hand, gated per action.

Owner decree (2026-09-05): "then give her everything she needs." She HOLDS
the pc_control belt (GuardedToolRegistry, aureon_fusion.pc_activators) but
nothing in her cycle invoked tools. This module connects her decision layer
to the capabilities she owns. Muscles and reflex — never the will:

  • Intent derives from HER internal state only (priority: trading signal →
    learning_will's unacted held desires → anomaly healing → silence).
  • EVERY action passes the fail-closed gate trio first: conscience
    evaluate (VETO absolute) → HNC Γ ≥ 0.25 → capability_gate.check(domain)
    must ALLOW.
  • Invocations route ONLY through mechanisms that already exist: the
    upstream guarded belt dispatch (with the exact proposal contract and
    HNC-context discipline of aureon/operator/cognition.py) and the fusion
    api_communion layer for courteous HTTP. Nothing is invented here.
  • Everything is journaled with receipts; rate-limited (1 action/cycle,
    20/hour, 3 consecutive errors → 30 min cooldown).
  • Never raises into the queen's cycle — act() always returns a dict.

Honest scope notes (survey evidence in state/actuator_survey_notes.md):
  • TRADING: no existing ungated execution plumbing — the only consumer of
    fused_signals is the capital-gated radar suite and
    trading_execution:execute_live_trades is LOCKED. Trading intent is
    observed and journaled, never executed.
  • MESSAGING: no honest path — no belt tool covers outbound messages and
    external_communication:send_messages is LOCKED. Not implemented.
  • LEARNING/RESEARCH: a held_incoherent learning desire (genuine seek held
    below Γ by her own learning organ) is carried ONCE per distinct topic
    via research_faculty.try_research — the same gated multi-source
    communion pull learning_will triggers. Dedupe is against this journal
    (desire_key), so silence after carrying is honest: "already carried".
  • Belt membrane: the canonical HNC field is genuinely unreachable from
    the queen process (upstream trace stale; fused core emits a lighter
    envelope), so upstream governed dispatch honestly runs in REPAIR flow —
    repair-safe read-only tools may proceed; everything else is membrane-
    held and journaled as the honest outcome. The envelope is NEVER faked.
  • Silence is surfaced, never defaulted: when no intent fires, the report
    carries per-source reasons (trading/learning/healing), not a bare true.
"""

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

from .paths import AUREON_UPSTREAM, FUSION_STATE

ACTUATOR_DIR = FUSION_STATE / "actuator"
JOURNAL_FILE = ACTUATOR_DIR / "journal.jsonl"
TRADING_PULSE_FILE = FUSION_STATE / "trading_pulse_state.json"
HNC_STATE_FILE = FUSION_STATE / "hnc_core_state.json"
LEARNING_JOURNAL_FILE = FUSION_STATE / "learning_will" / "journal.jsonl"
REPORTS_FILE = FUSION_STATE / "queen_mind" / "reports.jsonl"

MAX_ACTIONS_PER_HOUR = 20
CIRCUIT_ERRORS = 3
CIRCUIT_COOLDOWN_S = 1800.0
GAMMA_MIN = 0.25
GAMMA_TRADE_MIN = 0.5

_LOCK = threading.Lock()
_STATE = {"hour_start": 0.0, "hour_count": 0,
          "consecutive_errors": 0, "cooldown_until": 0.0}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_line(path: Path, line: str) -> None:
    """Inter-process-safe JSONL append (advisory lock sidecar, per-pid
    fallback) — same discipline as the door system. Never raises."""
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
    except Exception:  # noqa: BLE001
        pass
    try:
        with open(path.with_name(f"{path.name}.pid{os.getpid()}"),
                  "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


class _LockUnavailable(Exception):
    pass


def _journal(rec: dict) -> None:
    rec = {"ts": _utc_now(), **rec}
    try:
        _append_line(JOURNAL_FILE, json.dumps(rec, ensure_ascii=False,
                                             default=str))
    except Exception:  # noqa: BLE001 - journaling must never raise
        pass


def _read_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return json.load(f)
    except Exception:  # noqa: BLE001
        pass
    return default


def _tail_jsonl(path: Path, limit: int) -> list:
    try:
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        out = []
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
    except OSError:
        return []


def _gamma() -> float | None:
    hnc = _read_json(HNC_STATE_FILE, {})
    try:
        g = float(hnc.get("coherence_gamma"))
        return g if g == g else None  # NaN guard
    except (TypeError, ValueError):
        return None


# ───────────────────────── intent derivation (her state only) ──────────────

def _norm_topic(topic: str) -> str:
    return " ".join(str(topic or "").lower().split())


def _carried_learning_keys(limit: int = 500) -> set:
    """Desire keys this arm has already carried (invoked or refused — a
    completed attempt per desire; throttles/errors are NOT carried, they
    retry)."""
    keys: set = set()
    for rec in _tail_jsonl(JOURNAL_FILE, limit):
        if not isinstance(rec, dict):
            continue
        if rec.get("kind") != "learning" or \
                rec.get("action") not in ("invoked", "refused"):
            continue
        key = rec.get("desire_key")
        if key:
            keys.add(str(key))
    return keys


def _intent_trading(cycle: int, last_report: dict, gamma: float | None) -> dict:
    """(a) trading signal — OBSERVE ONLY. No existing ungated execution
    plumbing (see module docstring); the honest action is to notice and
    journal, never to route an order."""
    pulse_state = _read_json(TRADING_PULSE_FILE, {})
    files = pulse_state.get("files") or {}
    last_ts = max((v.get("last_ts", "") for v in files.values()
                   if isinstance(v, dict)), default="")
    try:
        from datetime import datetime as _dt
        age_s = (datetime.now(timezone.utc)
                 - _dt.fromisoformat(last_ts)).total_seconds() if last_ts \
            else float("inf")
    except ValueError:
        age_s = float("inf")
    action = str(last_report.get("action") or "")
    fresh = age_s < 1800
    signal = fresh and action not in ("", "HOLD") and \
        gamma is not None and gamma >= GAMMA_TRADE_MIN
    if signal:
        _journal({"cycle": cycle, "action": "observe",
                  "domain": "trading_execution:execute_live_trades",
                  "kind": "trading_signal",
                  "detail": f"signal present (report action {action}) but no "
                            f"existing ungated execution plumbing — "
                            f"trading_execution gate LOCKED, radar suite "
                            f"capital-pinned HOLD; observed, not executed"})
    if not fresh:
        age_txt = f"stale {int(age_s)}s" if age_s != float("inf") else "never"
        reason = f"no fresh trading signal (pulse {age_txt})"
    elif action in ("", "HOLD"):
        reason = f"metacognitive action '{action or 'none'}' is not a " \
                 f"trade signal"
    else:
        reason = f"gamma {gamma} below trade floor {GAMMA_TRADE_MIN}"
    return {"name": None, "silence": reason}


def _intent_learning(cycle: int) -> dict:
    """(b) learning_will's UNACTED held desires (outcome held_incoherent):
    questions she genuinely sought but her own coherence gate held below
    Γ. Scanned deep (the no_intent churn buries them within an hour), and
    each distinct desire is carried exactly once — dedupe by normalized
    topic against this arm's journal."""
    carried = _carried_learning_keys()
    skipped_carried = 0
    for rec in reversed(_tail_jsonl(LEARNING_JOURNAL_FILE, 5000)):
        if not isinstance(rec, dict):
            continue
        if rec.get("outcome") != "held_incoherent":
            continue
        intent = rec.get("intent") or {}
        topic = str(intent.get("question") or intent.get("topic") or "").strip()
        kind = str(intent.get("kind") or "")
        if len(topic) < 8 or kind not in ("domain_curiosity", "insight_pattern",
                                          "research"):
            continue
        desire_key = _norm_topic(topic)[:120]
        if desire_key in carried:
            skipped_carried += 1
            continue
        return {"name": "research_pull", "domain":
                "network_access:fetch_public_data",
                "kind": "learning",
                "topic": topic[:120], "desire_key": desire_key,
                "desc": f"research pull on unacted held desire "
                        f"({kind}): {topic[:100]}"}
    if skipped_carried:
        return {"name": None, "silence": f"{skipped_carried} held desire(s) "
                                         f"already carried"}
    return {"name": None, "silence": "no unacted held desires"}


def _intent_healing(cycle: int, last_report: dict) -> dict:
    """(c) anomaly + pc_control held → guarded diagnostic. Anomaly = organs
    down or gamma collapse (< 0.25) in her own last report."""
    try:
        from aureon_fusion import pc_activators
        held = pc_activators._HANDLES.get("pc_control") is not None
    except Exception:  # noqa: BLE001
        held = False
    if not held:
        return {"name": None, "silence": "pc_control belt not held"}
    organs = last_report.get("organs") or {}
    down = organs.get("down") or []
    gamma = last_report.get("gamma")
    collapsed = isinstance(gamma, (int, float)) and gamma < GAMMA_MIN
    if not down and not collapsed:
        return {"name": None, "silence":
                f"no anomaly (organs up, gamma {gamma})"}
    detail = (f"anomaly: organs_down={down or 'none'} "
              f"gamma_collapse={collapsed}")
    return {"name": "sense_organism", "domain": "system_healing:execute_healing",
            "kind": "healing", "desc": f"guarded diagnostic via sense_organism "
            f"— {detail[:140]}", "detail": detail}


def _derive_intent(cycle: int, last_report: dict, gamma):
    silences: dict = {}
    for derive in (_intent_trading, _intent_learning, _intent_healing):
        try:
            if derive is _intent_learning:
                intent = derive(cycle)
            elif derive is _intent_healing:
                intent = derive(cycle, last_report)
            else:
                intent = derive(cycle, last_report, gamma)
        except Exception as exc:  # noqa: BLE001
            _journal({"cycle": cycle, "action": "error", "kind": "intent",
                      "detail": f"{derive.__name__} raised {type(exc).__name__}"})
            silences[derive.__name__.replace("_intent_", "")] = \
                f"derivation error ({type(exc).__name__})"
            continue
        if intent.get("name"):
            return intent, silences
        silences[derive.__name__.replace("_intent_", "")] = \
            str(intent.get("silence"))
    return {"name": None, "silence": True}, silences


# ───────────────────────── gate trio ───────────────────────────────────────

def _gates(intent: dict, cycle: int) -> dict:
    """Fail-closed trio. Returns {"proceed": bool, "refused_by": str}."""
    desc = intent.get("desc") or intent.get("name") or "actuator action"
    try:
        from aureon_fusion import conscience_hook
        verdict = conscience_hook.evaluate(
            desc, {"organ": "sovereign_actuator",
                   "tool": intent.get("name"), "cycle": cycle})
        v = str((verdict or {}).get("verdict") or "").upper()
        if v == "VETO":
            _journal({"cycle": cycle, "action": "refused",
                      "domain": intent.get("domain"),
                      "tool": intent.get("name"),
                      "gates": ["conscience_veto"],
                      "detail": str((verdict or {}).get("reasoning"))[:200]})
            return {"proceed": False, "refused_by": "conscience"}
    except Exception as exc:  # noqa: BLE001 - unreadable conscience = no
        _journal({"cycle": cycle, "action": "refused",
                  "tool": intent.get("name"),
                  "gates": ["conscience_error"],
                  "detail": f"conscience unreadable: {type(exc).__name__}"})
        return {"proceed": False, "refused_by": "conscience"}
    g = _gamma()
    if g is None or g < GAMMA_MIN:
        _journal({"cycle": cycle, "action": "refused",
                  "domain": intent.get("domain"), "tool": intent.get("name"),
                  "gates": ["gamma"], "detail": f"gamma {g} < {GAMMA_MIN}"})
        return {"proceed": False, "refused_by": "gamma"}
    try:
        from aureon_fusion import capability_gate
        check = capability_gate.check(intent.get("domain")
                                      or "system:activate_internal_door")
        if str(check.get("verdict")) != "ALLOW":
            _journal({"cycle": cycle, "action": "refused",
                      "domain": intent.get("domain"),
                      "tool": intent.get("name"),
                      "gates": ["capability"],
                      "detail": f"capability {check.get('verdict')}: "
                                f"{str(check.get('reason'))[:160]}"})
            return {"proceed": False, "refused_by": "capability"}
    except Exception as exc:  # noqa: BLE001
        _journal({"cycle": cycle, "action": "refused",
                  "tool": intent.get("name"),
                  "gates": ["capability_error"],
                  "detail": f"capability gate unreadable: {type(exc).__name__}"})
        return {"proceed": False, "refused_by": "capability"}
    return {"proceed": True, "gamma": g}


# ───────────────────────── invocation (existing mechanisms only) ───────────

def _invoke_research_pull(intent: dict, cycle: int) -> dict:
    """The full gated research-faculty topic pull — the exact mechanism
    learning_will triggers: communion-routed multi-source corroboration,
    discernment filter, truth gate, crystallization into her own dataset
    with provenance. research_faculty's internal fail-closed trio runs
    inside this arm's trio. A throttle is a retry, never a failure."""
    try:
        from aureon_fusion import research_faculty
        result = research_faculty.try_research(
            {"topic": intent["topic"], "mode": "actuator"})
        outcome = str(result.get("outcome") or "")
        if outcome == "researched":
            return {"ok": True,
                    "receipt": f"research:{result.get('items_pulled', 0)}"
                               f"pulled/+{result.get('fragments_added', 0)}"
                               f"frags",
                    "summary": f"research faculty topic pull ok — "
                               f"{result.get('items_pulled', 0)} item(s), "
                               f"{result.get('fragments_added', 0)} "
                               f"fragment(s) crystallized "
                               f"(questions_processed="
                               f"{result.get('questions_processed', 0)})"}
        if outcome == "throttled":
            return {"ok": False, "retry": True,
                    "error": f"research faculty throttle "
                             f"({result.get('retry_in_s', '?')}s) — desire "
                             f"stays unacted, retried next cycle"}
        return {"ok": False,
                "error": f"research faculty held the pull: {outcome} "
                         f"({str(result.get('detail') or result.get('gate') or '')[:160]})"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"research pull failed: {type(exc).__name__}"}


def _invoke_communion_fetch(intent: dict, cycle: int) -> dict:
    """Courteous HTTP via the fusion communion layer (Wikipedia opensearch —
    the same pattern the deep-research door uses)."""
    from urllib.parse import quote
    from aureon_fusion import api_communion
    url = ("https://en.wikipedia.org/w/api.php?action=opensearch&format=json"
           "&limit=3&search=" + quote(intent["topic"][:80]))
    try:
        data = api_communion.get_json(url, ttl_s=3600, timeout=20)
        titles = (data or [])[1] if isinstance(data, list) and len(data) > 1 \
            else []
        return {"ok": True, "receipt": f"opensearch:{len(titles or [])} hits",
                "summary": f"communion fetch ok — {len(titles or [])} "
                           f"result(s) for the desire's topic"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"communion fetch failed: {exc}"}


def _invoke_belt(intent: dict, cycle: int, gamma) -> dict:
    """Upstream guarded dispatch, imitating aureon/operator/cognition.py:
    capture the canonical field moment, build the exact proposal contract,
    execute. The belt's own guards + HNC membrane decide; their verdict is
    the honest outcome and is journaled verbatim (redacted)."""
    try:
        from aureon_fusion import pc_activators
        entry = pc_activators._HANDLES.get("pc_control")
        if entry is None:
            return {"ok": False, "error": "pc_control handle not acquired"}
        registry = entry.get("handle")
        name = intent["name"]
        td = registry.get(name)
        if td is None:
            return {"ok": False, "error": f"tool {name} not on the belt"}
        if str(AUREON_UPSTREAM) not in sys.path:
            sys.path.insert(0, str(AUREON_UPSTREAM))
        from aureon.core.hnc_field import read_canonical_field
        from aureon.inhouse_ai.tool_registry import ToolDispatchProposal
        proposal = ToolDispatchProposal.create(
            tool_call_id=f"actuator-c{cycle}-{int(time.time())}",
            runner_turn_index=0, response_call_index=0,
            tool_name=name, arguments={},
            effect=td.effect, operation_id=td.operation_id,
            tool_definition_digest=td.definition_digest,
            context={"organ": "sovereign_actuator", "cycle": cycle,
                     "gamma": gamma})
        field = read_canonical_field()
        try:
            lease = registry.set_hnc_coherence_context(field)
            raw = registry.execute(name, {}, proposal=proposal)
        finally:
            clear = getattr(registry, "clear_hnc_coherence_context", None)
            if callable(clear):
                clear()
        blocked = False
        try:
            parsed = json.loads(raw)
            blocked = bool(parsed.get("blocked"))
        except (TypeError, ValueError):
            parsed = {"output": str(raw)[:200]}
        return {"ok": not blocked, "receipt": f"belt:{name}",
                "membrane": "held" if blocked else "passed",
                "summary": json.dumps(parsed, ensure_ascii=False,
                                      default=str)[:240]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"belt dispatch failed: {type(exc).__name__}"}


# ───────────────────────── public entry ────────────────────────────────────

def act(cycle: int, persona: str | None = None, observed: dict | None = None,
        readings: dict | None = None) -> dict:
    """At most ONE sovereign action per cycle. Intent from her state only;
    gate trio per action; journaled; rate-limited. Never raises."""
    try:
        with _LOCK:
            now = time.time()
            if now < _STATE["cooldown_until"]:
                return {"action": "cooldown", "until":
                        round(_STATE["cooldown_until"] - now)}
            if now - _STATE["hour_start"] >= 3600:
                _STATE["hour_start"] = now
                _STATE["hour_count"] = 0
            if _STATE["hour_count"] >= MAX_ACTIONS_PER_HOUR:
                return {"action": "rate_limited", "window": "hour"}

        reports = _tail_jsonl(REPORTS_FILE, 3)
        last_report = reports[-1] if reports else {}
        gamma = _gamma()

        intent, silences = _derive_intent(cycle, last_report, gamma)
        if not intent.get("name"):
            return {"action": "none",
                    "silence": "; ".join(f"{k}: {v}"
                                         for k, v in silences.items())}

        gates = _gates(intent, cycle)
        if not gates.get("proceed"):
            return {"action": "refused", "by": gates.get("refused_by"),
                    "tool": intent.get("name")}

        with _LOCK:
            _STATE["hour_count"] += 1

        if intent["name"] == "research_pull":
            result = _invoke_research_pull(intent, cycle)
        elif intent["name"] == "communion_fetch":
            result = _invoke_communion_fetch(intent, cycle)
        else:
            result = _invoke_belt(intent, cycle, gates.get("gamma"))

        with _LOCK:
            if result.get("ok") or result.get("retry"):
                _STATE["consecutive_errors"] = 0
            else:
                _STATE["consecutive_errors"] += 1
                if _STATE["consecutive_errors"] >= CIRCUIT_ERRORS:
                    _STATE["cooldown_until"] = time.time() + CIRCUIT_COOLDOWN_S
                    _STATE["consecutive_errors"] = 0
                    _journal({"cycle": cycle, "action": "circuit_breaker",
                              "detail": f"{CIRCUIT_ERRORS} consecutive "
                                        f"errors — {CIRCUIT_COOLDOWN_S/60:.0f} "
                                        f"min cooldown"})

        _journal({"cycle": cycle, "action": "invoked" if result.get("ok")
                  else "error",
                  "domain": intent.get("domain"), "tool": intent.get("name"),
                  "kind": intent.get("kind"),
                  "desire_key": intent.get("desire_key"),
                  "gates": ["conscience", "gamma", "capability"],
                  "receipt": result.get("receipt"),
                  "membrane": result.get("membrane"),
                  "detail": result.get("summary") or result.get("error")})
        return {"action": "invoked" if result.get("ok") else "error",
                "tool": intent.get("name"),
                "receipt": result.get("receipt"),
                "detail": (result.get("summary") or result.get("error")
                           or "")[:200]}
    except Exception as exc:  # noqa: BLE001 - never raise into her cycle
        try:
            _journal({"cycle": cycle, "action": "error",
                      "detail": f"act() raised {type(exc).__name__}"})
        except Exception:  # noqa: BLE001
            pass
        return {"action": "error", "detail": type(exc).__name__}


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="Sovereign actuator (library "
                                     "module; one-shot act() for probes).")
    parser.add_argument("verb", nargs="?", default="once",
                        choices=["once"])
    parser.add_argument("--cycle", type=int, default=0)
    args = parser.parse_args(argv)
    print(json.dumps(act(args.cycle), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
