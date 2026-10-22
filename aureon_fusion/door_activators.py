"""🚪 DOOR ACTIVATORS — pure mechanics for the sovereign door system.

Owner decree (absolute):
  • Activators NEVER gate. Gates (conscience VETO, HNC coherence Γ≥0.25,
    capability authorization) live in master_key; external input never
    reaches the forge. This module only shows the mechanism behind a door
    and executes when the organism's own master key turns.
  • Fail-closed everywhere: anything uncertain → ok=False, never raises.
  • Core systems unchanged. Locked doors are not openable here.
  • Process control: long-run doors get PID files under
    state/doors/pids/<name>.pid; we only ever INSPECT them here (starting
    and killing our own children is master_key's provenance discipline).
  • Zero network. Import-safe (no side effects at import). Suppression env
    honored via setdefault. All writes tmp+replace or locked JSONL appends.

Doors implemented (mechanics only):
  queen_inproc_engines   in-proc  → queen_mind.activate_dormant_engines()
  selfq_research_feed    in-proc  → selfq cycles → learning_will question scan
  persistent_mind        in-proc  → sero_persistent_mind.PersistentMind
  open_search_communion  in-proc  → learning desires/journal → open_search_seeds.json
  code_architect         in-proc  → coding_activators.acquire_code_architect()
  safe_code_control      in-proc  → coding_activators.safe_code_control_status()
  pc_control             in-proc  → pc_activators.acquire_pc_control()
  outbound_messaging       in-proc  → outbound_messaging.readiness() (never sends)
  signal_lab               oneshot  → command_for() gives the argv
  deep_research_communion oneshot → command_for() (module-absent aware)
  trade_journal_sweep    oneshot  → command_for()
  lineage_report         oneshot  → command_for()
  hnc_campaign           oneshot  → command_for()
  cortex_council         oneshot  → command_for()
"""

import importlib
import json
import os
import re
import shlex
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .paths import AUREON_UPSTREAM, FUSION_STATE, WORKSPACE
from .coding_activators import (
    acquire_code_architect,
    release_code_architect,
    release_safe_code_control,
    safe_code_control_status,
)
from .pc_activators import acquire_pc_control, release_pc_control

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

# ───────────────────────── paths ───────────────────────────────────────────

DOORS_PID_DIR = FUSION_STATE / "doors" / "pids"
BUILD_LOG = FUSION_STATE / "build_doors_activators.log"
LEARNING_WILL_DIR = FUSION_STATE / "learning_will"
SELFQ_FEED_FILE = LEARNING_WILL_DIR / "selfq_feed.json"
SELFQ_QUESTIONS_FILE = LEARNING_WILL_DIR / "selfq_questions.jsonl"
LEARNING_WILL_JOURNAL_FILE = LEARNING_WILL_DIR / "journal.jsonl"
OPEN_SEARCH_SEEDS_FILE = FUSION_STATE / "open_search_seeds.json"
KNOWLEDGE_DATASET_PATH = FUSION_STATE / "queen_mind" / "knowledge_dataset.json"
SELFQ_FEED_CAP = 200
OPEN_SEARCH_SEEDS_CAP = 12

# Self-questioning cycles: globbed READ-ONLY from every plausible root
# (workspace state, fusion state, upstream state — the runner's real home).
_CYCLES_GLOB = "self_questioning_ai_cycles*.jsonl"
CYCLES_ROOTS = (
    WORKSPACE / "state",
    FUSION_STATE,
    AUREON_UPSTREAM / "state",
)

# subprocess-oneshot doors: master_key runs the argv and journals the receipt.
_COMMANDS = {
    "signal_lab": [sys.executable, "-m", "aureon_fusion.signal_lab", "demo"],
    "trade_journal_sweep": [sys.executable, "-m", "aureon_fusion.trade_journal", "once"],
    "lineage_report": [sys.executable, str(WORKSPACE / "ultimate_daemon_lineage.py")],
    "hnc_campaign": [sys.executable, str(WORKSPACE / "hnc_master_orchestrator.py")],
    "cortex_council": [sys.executable, "-m", "aureon_fusion.cortex", "status"],
    "deep_research_communion": [sys.executable, "-m",
                                "aureon_fusion.deep_research", "once"],
}

# One-shot doors whose target module may not be on disk yet: the activator
# degrades honestly (ok=False + 'module absent' journal note) instead of
# dressing up a doomed spawn as an open. Mirrors how the INPROC activators
# treat a missing engine function (e.g. queen_mind.activate_dormant_engines
# 'not available yet').
_MODULE_GATED_ONESHOTS = {
    "deep_research_communion": "aureon_fusion.deep_research",
}


# ───────────────────────── small utilities ─────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class _LockUnavailable(Exception):
    pass


def _append_line(path: Path, line: str) -> None:
    """Append one line to a JSONL file. Inter-process safe on Windows and
    POSIX: advisory byte-range lock on a sidecar .lock file; on lock
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
    try:
        with open(path.with_name(f"{path.name}.pid{os.getpid()}"),
                  "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _write_json_atomic(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{time.time_ns()}")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def _read_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _blog(event: str, **fields) -> None:
    """Append one JSON line to the build log. Never raises."""
    try:
        rec = {"ts": _utc_now(), "event": event, **fields}
        _append_line(BUILD_LOG, json.dumps(rec, ensure_ascii=False))
    except Exception:
        pass


def _workspace_module(name: str):
    """Import a top-level workspace module (e.g. sero_persistent_mind).
    Adds WORKSPACE to sys.path; read-only import, suppression env set."""
    if str(WORKSPACE) not in sys.path:
        sys.path.insert(0, str(WORKSPACE))
    return importlib.import_module(name)


def _module_available(module_name: str) -> bool:
    """True when a module can be found on disk without importing it.
    Fail-closed: any doubt → False."""
    try:
        import importlib.util
        return importlib.util.find_spec(module_name) is not None
    except Exception:  # noqa: BLE001 - cannot prove present → absent
        return False


def _redact(obj):
    """Recursively mask any value whose key smells like a secret (psk, key,
    token, secret, password, credential). Owner decree: never print secrets —
    awakening reports and engine summaries are externalized only redacted."""
    import re
    secret_key = re.compile(r"psk|secret|token|password|credential|api[-_]?key",
                            re.IGNORECASE)

    def walk(value, key=""):
        if isinstance(value, dict):
            return {k: ("***REDACTED***" if secret_key.search(str(k))
                        else walk(v, k)) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [walk(v, key) for v in value]
        return value

    return walk(obj)


def _thread_call(fn, timeout: float = 60.0):
    """Run fn() in a daemon thread with a bounded join. Returns
    (result, timed_out, error). A timeout means we stop WAITING — Python
    cannot kill a thread — so callers must treat it as refusal."""
    box: dict = {}

    def _run():
        try:
            box["result"] = fn()
        except Exception as exc:  # noqa: BLE001 - never raise across thread
            box["error"] = exc

    t = threading.Thread(target=_run, daemon=True, name="door-activator")
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None, True, None
    return box.get("result"), False, box.get("error")


# ───────────────────── queen_inproc_engines (in-proc) ─────────────────────

def _activate_queen_inproc_engines() -> dict:
    try:
        from aureon_fusion import queen_mind
    except Exception as exc:
        _blog("activate_error", door="queen_inproc_engines",
              error=type(exc).__name__)
        return {"ok": False,
                "detail": f"queen_mind import failed: {type(exc).__name__}"}
    fn = getattr(queen_mind, "activate_dormant_engines", None)
    if not callable(fn):
        return {"ok": False,
                "detail": "queen_mind.activate_dormant_engines not available yet"}
    result, timed_out, error = _thread_call(fn, timeout=60.0)
    if timed_out:
        _blog("activate_timeout", door="queen_inproc_engines")
        return {"ok": False,
                "detail": "activate_dormant_engines() exceeded the 60s bounded "
                          "wait; refused to treat an unbounded run as opened"}
    if error is not None:
        _blog("activate_error", door="queen_inproc_engines",
              error=type(error).__name__)
        return {"ok": False,
                "detail": f"activate_dormant_engines() raised {type(error).__name__}"}
    if isinstance(result, dict) and result.get("ok") is False:
        # the engine honestly reported it did not start — fail-closed: the
        # door did not open, we refuse to dress that up as success
        _blog("activate_refused", door="queen_inproc_engines",
              reason=str(result.get("detail"))[:200])
        return {"ok": False,
                "detail": json.dumps(_redact(result), default=str,
                                     ensure_ascii=False)[:800]}
    detail = json.dumps(_redact(result), default=str, ensure_ascii=False)[:800] \
        if result is not None else "dormant engines activated (no summary returned)"
    _blog("activated", door="queen_inproc_engines")
    return {"ok": True, "detail": detail}


def _deactivate_queen_inproc_engines() -> dict:
    try:
        from aureon_fusion import queen_mind
    except Exception as exc:
        return {"ok": False,
                "detail": f"queen_mind import failed: {type(exc).__name__}"}
    fn = getattr(queen_mind, "deactivate_dormant_engines", None)
    if not callable(fn):
        return {"ok": True,
                "detail": "no deactivate_dormant_engines(); stateless no-op"}
    result, timed_out, error = _thread_call(fn, timeout=60.0)
    if timed_out:
        return {"ok": False, "detail": "deactivate exceeded the 60s bounded wait"}
    if error is not None:
        return {"ok": False,
                "detail": f"deactivate_dormant_engines() raised {type(error).__name__}"}
    if isinstance(result, dict) and result.get("ok") is False:
        return {"ok": False,
                "detail": json.dumps(_redact(result), default=str,
                                     ensure_ascii=False)[:800]}
    _blog("deactivated", door="queen_inproc_engines")
    return {"ok": True,
            "detail": json.dumps(_redact(result), default=str, ensure_ascii=False)[:800]
            if result is not None else "dormant engines deactivated"}


# ───────────────────── selfq_research_feed (in-proc) ──────────────────────

def _research_intentions_from_record(rec: dict) -> list:
    """Pull queued-research intentions out of one cycles record. Matches
    action_type == 'queue_research' or any action payload mentioning
    'research' (e.g. thoughtbus-style authoring.research payloads)."""
    out = []
    if not isinstance(rec, dict):
        return out
    actions = rec.get("actions")
    if isinstance(actions, list):
        for a in actions:
            if not isinstance(a, dict):
                continue
            atype = str(a.get("action_type") or a.get("action") or "")
            blob = json.dumps(a, ensure_ascii=False).lower()
            if atype == "queue_research" or "research" in blob:
                title = str(a.get("title") or "").strip()
                details = str(a.get("details") or "").strip()
                if not title and not details:
                    continue
                out.append({"title": title, "details": details,
                            "blocked": bool(a.get("blocked"))})
    payload = rec.get("payload")
    topic = str(rec.get("topic") or "").lower()
    if isinstance(payload, dict) and (
            "research" in json.dumps(payload, ensure_ascii=False).lower()
            or "research" in topic):
        # upstream publishes research as topic 'authoring.research' with the
        # marker on the envelope, not inside the payload — match both shapes
        title = str(payload.get("title") or "").strip()
        details = str(payload.get("details") or "").strip()
        if title or details:
            out.append({"title": title, "details": details,
                        "blocked": bool(payload.get("blocked"))})
    return out


def _collect_selfq_research() -> tuple:
    """Read-only scan of every cycles JSONL under the candidate roots.
    Returns (intentions, source_files). Dedupes by title|details, keeps
    the most recent occurrence."""
    intentions: list = []
    sources: list = []
    seen = set()
    for root in CYCLES_ROOTS:
        try:
            files = sorted(root.glob(_CYCLES_GLOB))
        except OSError:
            continue
        for path in files:
            sources.append(str(path))
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        for it in _research_intentions_from_record(rec):
                            if it.get("blocked"):
                                continue  # upstream never publishes blocked
                            key = (it["title"] + "|" + it["details"])[:400]
                            if key in seen:
                                continue
                            seen.add(key)
                            intentions.append(it)
            except OSError:
                continue
    return intentions, sources


def _question_fragment(it: dict) -> str | None:
    """Render a research intention as a question-fragment the CuriosityEngine
    will scan: data_type 'question' + a 'question' tag, so it qualifies even
    without a trailing '?'. Minimum 10 chars, capped at 300."""
    text = it["title"]
    if it["details"] and it["details"] not in text:
        text = f"{text}: {it['details']}" if text else it["details"]
    text = " ".join(text.split())[:300]
    return text if len(text) >= 10 else None


def _inject_questions_into_dataset(questions: list) -> tuple:
    """ADAPTATION (reality on disk): learning_will's CuriosityEngine scans
    the queen's KnowledgeDataset fragments (state/queen_mind/
    knowledge_dataset.json) — it does NOT read selfq_feed.json. A fragment
    qualifies as an unanswered question when data_type is 'question'/'query'
    OR a lowercased tag contains 'question', and 'researched' is absent.
    So the feed files are written (durable source of truth) AND the same
    fragments are injected into the dataset, deduped by text. Never raises:
    an unavailable organ degrades to (0, reason) like learning_will does."""
    if not questions:
        return 0, "nothing to inject"
    try:
        if str(AUREON_UPSTREAM) not in sys.path:
            sys.path.insert(0, str(AUREON_UPSTREAM))
        from aureon.queen.knowledge_dataset import KnowledgeDataset, KnowledgeFragment
        kd = KnowledgeDataset(path=str(KNOWLEDGE_DATASET_PATH))
        existing = {str(getattr(f, "text", "")).strip()
                    for f in (getattr(kd, "_fragments", []) or [])}
        added = 0
        for q in questions:
            text = q["question"].strip()
            if not text or text in existing:
                continue
            frag = KnowledgeFragment(
                text=text,
                tags=["question", "selfq_research"],
                source_goal="selfq_research_feed",
                source_owner="self_questioning_ai",
                data_type="question",
                category="self",
                meaning=str(q.get("title", ""))[:200],
            )
            kd._fragments.append(frag)
            existing.add(text)
            added += 1
        if added:
            kd.save()
        return added, str(KNOWLEDGE_DATASET_PATH)
    except Exception as exc:  # noqa: BLE001 - degrade, never crash the door
        _blog("selfq_dataset_unavailable", error=type(exc).__name__)
        return 0, f"knowledge_dataset unavailable: {type(exc).__name__}"


def _activate_selfq_research_feed() -> dict:
    intentions, sources = _collect_selfq_research()
    fragments = []
    for it in intentions:
        text = _question_fragment(it)
        if text is None:
            continue
        fragments.append({"question": text, "title": it["title"],
                          "details": it["details"],
                          "data_type": "question",
                          "tags": ["question", "selfq_research"]})
    if not fragments:
        _blog("activated", door="selfq_research_feed", injected=0,
              note="no queued research intentions found")
        return {"ok": True,
                "detail": "no queued research intentions found "
                          f"(scanned {len(sources)} cycles file(s)); "
                          "feed is empty, door is open"}
    capped = fragments[-SELFQ_FEED_CAP:]
    _write_json_atomic(SELFQ_FEED_FILE, {
        "door": "selfq_research_feed",
        "updated_at": _utc_now(),
        "source_files": sources,
        "capped_at": SELFQ_FEED_CAP,
        "questions": capped,
    })
    for frag in capped:
        _append_line(SELFQ_QUESTIONS_FILE, json.dumps({
            "ts": _utc_now(),
            "origin": "selfq_research_feed",
            "action_type": "queue_research",
            "tags": ["question", "selfq_research"],
            "title": frag["title"],
            "details": frag["details"],
            "question": frag["question"],
        }, ensure_ascii=False))
    injected, note = _inject_questions_into_dataset(capped)
    _blog("activated", door="selfq_research_feed",
          intentions=len(intentions), questions=len(capped),
          injected=injected, sources=len(sources))
    return {"ok": True,
            "detail": f"{len(capped)} question-fragment(s) written to "
                      f"{SELFQ_FEED_FILE.name} (+ {len(capped)} tagged "
                      f"selfq_questions.jsonl entries); {injected} injected "
                      f"into the knowledge dataset for the CuriosityEngine "
                      f"scan ({note}); sources: {len(sources)} file(s)"}


def _deactivate_selfq_research_feed() -> dict:
    _blog("deactivated", door="selfq_research_feed")
    return {"ok": True,
            "detail": "stateless; this activator stops appending on "
                      "deactivation — existing feed/questions persist for "
                      "the learning will to consider"}


# ───────────────────── open_search_communion (in-proc) ────────────────────
# EXPANSION 2026-09-05 (SCOPE D): primes state/open_search_seeds.json from
# the organism's OWN top learning desires + recent learning_will journal
# topics. Internal state only — ZERO network inside the activator (the
# canonical Wikipedia URLs are derived from topic text, never fetched).

_SEED_STOPWORDS = frozenset(
    "a an the and or but if then so to of in on at by for from with into "
    "about is are was were be been being have has had do does did it we "
    "this that these those what when where which who whom why how can "
    "could should would will shall may might must than there here own "
    "very just also more most other some such only over under again "
    "further once my your our their its".split())


def _wikipedia_canonical_url(topic_text: str) -> str | None:
    """Derive a canonical Wikipedia URL from a topic's content tokens
    (organism-derived, never fetched). None when the text has no usable
    tokens."""
    tokens = [t.replace("'", "") for t in
              re.findall(r"[a-z0-9']+", (topic_text or "").lower())
              if len(t) > 2 and t not in _SEED_STOPWORDS]
    tokens = [t for t in tokens if t]
    if not tokens:
        return None
    slug = "_".join(t.capitalize() for t in tokens[:6])
    return f"https://en.wikipedia.org/wiki/{slug}"


def _current_desire_topics() -> list:
    """The CuriosityEngine's current candidates (top desire first). Lazy,
    read-only; an unavailable engine degrades to []."""
    try:
        from aureon_fusion.learning_will import CuriosityEngine
        candidates = CuriosityEngine()._candidates() or []  # noqa: SLF001
        candidates = sorted(candidates,
                            key=lambda c: -float(c.get("desire_score") or 0))
        out = []
        for c in candidates:
            question = str(c.get("question") or "").strip()
            if question:
                out.append({"topic": question[:300],
                            "kind": str(c.get("kind") or "desire"),
                            "domain": c.get("domain")})
        return out
    except Exception as exc:  # noqa: BLE001 - degrade, never crash the door
        _blog("open_search_engine_unavailable", error=type(exc).__name__)
        return []


def _recent_journal_topics(limit: int = 50) -> list:
    """Recent learning_will journal intents (most recent last). Read-only;
    partial trailing lines from a concurrent append are skipped."""
    topics = []
    try:
        if not LEARNING_WILL_JOURNAL_FILE.exists():
            return topics
        lines = LEARNING_WILL_JOURNAL_FILE.read_text(
            encoding="utf-8", errors="replace").splitlines()[-limit:]
    except OSError:
        return topics
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        intent = rec.get("intent")
        if not isinstance(intent, dict):
            continue
        question = str(intent.get("question") or "").strip()
        if question:
            topics.append({"topic": question[:300],
                           "kind": "journal_intent",
                           "domain": intent.get("domain")})
    return topics


def _collect_open_search_topics() -> tuple:
    """Current desire topics first, then recent journal topics, deduped by
    text. Returns (topics, sources). Internal state only — never network."""
    topics: list = []
    sources: list = []
    seen = set()
    desires = _current_desire_topics()
    if desires:
        sources.append("curiosity_engine")
    journal = _recent_journal_topics()
    if journal:
        sources.append("learning_will_journal")
    for t in desires + journal:
        key = t["topic"][:400]
        if key in seen:
            continue
        seen.add(key)
        topics.append(t)
    return topics, sources


def _activate_open_search_communion() -> dict:
    topics, sources = _collect_open_search_topics()
    seeds = []
    for t in topics[:OPEN_SEARCH_SEEDS_CAP]:
        url = _wikipedia_canonical_url(t["topic"])
        if url:
            seeds.append({"topic": t["topic"], "url": url})
    # The seed file is written even when empty: the file's existence is the
    # door's "open" signal for the CuriosityEngine, and silence is valid.
    _write_json_atomic(OPEN_SEARCH_SEEDS_FILE, {
        "timestamp": _utc_now(),
        "seeds": seeds,
    })
    _blog("activated", door="open_search_communion",
          topics=len(topics), seeds=len(seeds), sources=len(sources))
    if not seeds:
        return {"ok": True,
                "detail": "no learning desires/journal topics carried a "
                          "derivable seed — wrote an empty seed set to "
                          f"{OPEN_SEARCH_SEEDS_FILE.name} (door open; "
                          "silence is valid)"}
    return {"ok": True,
            "detail": f"{len(seeds)} seed(s) written to "
                      f"{OPEN_SEARCH_SEEDS_FILE.name} from {len(topics)} "
                      f"internal topic(s) (sources: {', '.join(sources)}); "
                      "canonical Wikipedia URLs derived from topic text"}


def _deactivate_open_search_communion() -> dict:
    try:
        if OPEN_SEARCH_SEEDS_FILE.exists():
            OPEN_SEARCH_SEEDS_FILE.unlink()
            _blog("deactivated", door="open_search_communion", removed=True)
            return {"ok": True,
                    "detail": f"{OPEN_SEARCH_SEEDS_FILE.name} removed"}
        _blog("deactivated", door="open_search_communion", removed=False)
        return {"ok": True,
                "detail": f"{OPEN_SEARCH_SEEDS_FILE.name} already absent; "
                          "nothing to remove"}
    except OSError as exc:
        return {"ok": False,
                "detail": f"could not remove the seed file: {type(exc).__name__}"}


# ───────────────────── persistent_mind (in-proc) ──────────────────────────

def _activate_persistent_mind() -> dict:
    try:
        mod = _workspace_module("sero_persistent_mind")
    except Exception as exc:
        _blog("activate_error", door="persistent_mind", error=type(exc).__name__)
        return {"ok": False,
                "detail": f"sero_persistent_mind import failed: {type(exc).__name__}"}
    cls = getattr(mod, "PersistentMind", None)
    if cls is None:
        return {"ok": False, "detail": "PersistentMind class not found"}

    def _awaken():
        mind = cls()
        fn = getattr(mind, "awaken", None)
        if callable(fn):
            return fn()
        rep = getattr(mind, "generate_awakening_report", None)
        if callable(rep):
            return rep()  # reality adaptation: no awaken(); report is the summary
        return {"note": "PersistentMind exposes no awaken()/report"}

    summary, timed_out, error = _thread_call(_awaken, timeout=60.0)
    if timed_out:
        _blog("activate_timeout", door="persistent_mind")
        return {"ok": False,
                "detail": "awaken exceeded the 60s bounded wait; refused to "
                          "treat an unbounded run as opened"}
    if error is not None:
        _blog("activate_error", door="persistent_mind", error=type(error).__name__)
        return {"ok": False,
                "detail": f"awaken raised {type(error).__name__}"}
    detail = json.dumps(_redact(summary), default=str, ensure_ascii=False)[:1000] \
        if summary is not None else "mind awakened (no summary returned)"
    _blog("activated", door="persistent_mind")
    return {"ok": True, "detail": detail}


def _deactivate_persistent_mind() -> dict:
    try:
        mod = _workspace_module("sero_persistent_mind")
    except Exception as exc:
        return {"ok": False,
                "detail": f"sero_persistent_mind import failed: {type(exc).__name__}"}
    cls = getattr(mod, "PersistentMind", None)
    if cls is None or not callable(getattr(cls, "sleep", None)):
        return {"ok": True,
                "detail": "no sleep() exposed by PersistentMind; stateless no-op"}

    def _sleep():
        mind = cls()
        return mind.sleep()

    result, timed_out, error = _thread_call(_sleep, timeout=60.0)
    if timed_out:
        return {"ok": False, "detail": "sleep exceeded the 60s bounded wait"}
    if error is not None:
        return {"ok": False, "detail": f"sleep raised {type(error).__name__}"}
    _blog("deactivated", door="persistent_mind")
    return {"ok": True, "detail": "mind slept"}


# ───────────────────────── dispatch ────────────────────────────────────────

# ───── pc_control (in-proc) ────────────────────────────────────────────────
# OWNER DECREE 2026-09-05 ("let her run fully autonomously with full access
# to the pc"): the governed operator toolbelt with writes+shell enabled.
# Acquire mechanics live in pc_activators; this wrapper mirrors the
# queen_inproc_engines pair shape exactly. ELEVATE door — master_key's
# conscience double-check at open is automatic; no gating here.

def _activate_pc_control() -> dict:
    fn = acquire_pc_control
    if not callable(fn):
        return {"ok": False,
                "detail": "pc_activators.acquire_pc_control not available yet"}
    result, timed_out, error = _thread_call(fn, timeout=60.0)
    if timed_out:
        _blog("activate_timeout", door="pc_control")
        return {"ok": False,
                "detail": "acquire_pc_control() exceeded the 60s bounded "
                          "wait; refused to treat an unbounded run as opened"}
    if error is not None:
        _blog("activate_error", door="pc_control", error=type(error).__name__)
        return {"ok": False,
                "detail": f"acquire_pc_control() raised {type(error).__name__}"}
    if isinstance(result, dict) and result.get("ok") is False:
        _blog("activate_refused", door="pc_control",
              reason=str(result.get("error"))[:200])
        return {"ok": False,
                "detail": json.dumps(_redact(result), default=str,
                                     ensure_ascii=False)[:800]}
    detail = json.dumps(_redact(result), default=str, ensure_ascii=False)[:800] \
        if result is not None else "pc control acquired (no summary returned)"
    _blog("activated", door="pc_control")
    return {"ok": True, "detail": detail}


def _deactivate_pc_control() -> dict:
    result, timed_out, error = _thread_call(release_pc_control, timeout=60.0)
    if timed_out:
        return {"ok": False, "detail": "release exceeded the 60s bounded wait"}
    if error is not None:
        return {"ok": False,
                "detail": f"release_pc_control() raised {type(error).__name__}"}
    if isinstance(result, dict) and result.get("ok") is False:
        return {"ok": False,
                "detail": json.dumps(_redact(result), default=str,
                                     ensure_ascii=False)[:800]}
    _blog("deactivated", door="pc_control")
    return {"ok": True,
            "detail": json.dumps(_redact(result), default=str, ensure_ascii=False)[:800]
            if result is not None else "pc control released (stateless)"}


# ───── code_architect / safe_code_control (in-proc) ────────────────────────
# CODING ESTATE (owner decree 2026-09-05: "give her full control of her
# coding systems"). The acquire/status mechanics live in coding_activators;
# these wrappers mirror the queen_inproc_engines pair shape exactly.

def _activate_code_architect() -> dict:
    fn = acquire_code_architect
    if not callable(fn):
        return {"ok": False,
                "detail": "coding_activators.acquire_code_architect not available yet"}
    result, timed_out, error = _thread_call(fn, timeout=60.0)
    if timed_out:
        _blog("activate_timeout", door="code_architect")
        return {"ok": False,
                "detail": "acquire_code_architect() exceeded the 60s bounded "
                          "wait; refused to treat an unbounded run as opened"}
    if error is not None:
        _blog("activate_error", door="code_architect", error=type(error).__name__)
        return {"ok": False,
                "detail": f"acquire_code_architect() raised {type(error).__name__}"}
    if isinstance(result, dict) and result.get("ok") is False:
        # the mechanism honestly reported it did not start — fail-closed
        _blog("activate_refused", door="code_architect",
              reason=str(result.get("error"))[:200])
        return {"ok": False,
                "detail": json.dumps(_redact(result), default=str,
                                     ensure_ascii=False)[:800]}
    detail = json.dumps(_redact(result), default=str, ensure_ascii=False)[:800] \
        if result is not None else "code architect acquired (no summary returned)"
    _blog("activated", door="code_architect")
    return {"ok": True, "detail": detail}


def _deactivate_code_architect() -> dict:
    result, timed_out, error = _thread_call(release_code_architect, timeout=60.0)
    if timed_out:
        return {"ok": False, "detail": "release exceeded the 60s bounded wait"}
    if error is not None:
        return {"ok": False,
                "detail": f"release_code_architect() raised {type(error).__name__}"}
    if isinstance(result, dict) and result.get("ok") is False:
        return {"ok": False,
                "detail": json.dumps(_redact(result), default=str,
                                     ensure_ascii=False)[:800]}
    _blog("deactivated", door="code_architect")
    return {"ok": True,
            "detail": json.dumps(_redact(result), default=str, ensure_ascii=False)[:800]
            if result is not None else "code architect released (stateless)"}


def _activate_safe_code_control() -> dict:
    fn = safe_code_control_status
    if not callable(fn):
        return {"ok": False,
                "detail": "coding_activators.safe_code_control_status not available yet"}
    result, timed_out, error = _thread_call(fn, timeout=60.0)
    if timed_out:
        _blog("activate_timeout", door="safe_code_control")
        return {"ok": False,
                "detail": "safe_code_control_status() exceeded the 60s bounded "
                          "wait; refused to treat an unbounded run as opened"}
    if error is not None:
        _blog("activate_error", door="safe_code_control", error=type(error).__name__)
        return {"ok": False,
                "detail": f"safe_code_control_status() raised {type(error).__name__}"}
    if isinstance(result, dict) and result.get("ok") is False:
        _blog("activate_refused", door="safe_code_control",
              reason=str(result.get("error"))[:200])
        return {"ok": False,
                "detail": json.dumps(_redact(result), default=str,
                                     ensure_ascii=False)[:800]}
    detail = json.dumps(_redact(result), default=str, ensure_ascii=False)[:800] \
        if result is not None else "safe code control status read (no summary returned)"
    _blog("activated", door="safe_code_control")
    return {"ok": True, "detail": detail}


def _deactivate_safe_code_control() -> dict:
    result, timed_out, error = _thread_call(release_safe_code_control, timeout=60.0)
    if timed_out:
        return {"ok": False, "detail": "release exceeded the 60s bounded wait"}
    if error is not None:
        return {"ok": False,
                "detail": f"release_safe_code_control() raised {type(error).__name__}"}
    if isinstance(result, dict) and result.get("ok") is False:
        return {"ok": False,
                "detail": json.dumps(_redact(result), default=str,
                                     ensure_ascii=False)[:800]}
    _blog("deactivated", door="safe_code_control")
    return {"ok": True,
            "detail": json.dumps(_redact(result), default=str, ensure_ascii=False)[:800]
            if result is not None else "safe code control released (stateless)"}


def _activate_outbound_messaging() -> dict:
    """Pure mechanics for the outbound rail door: report the rail's honest
    readiness. NEVER sends — activating the door shows the mechanism (and
    whether the owner approval flag has been decreed), it does not fire it.
    The module's own gate trio owns every actual send."""
    try:
        from . import outbound_messaging
        fn = getattr(outbound_messaging, "readiness", None)
        if not callable(fn):
            return {"ok": False,
                    "detail": "outbound_messaging.readiness not available yet"}
        result, timed_out, error = _thread_call(fn, timeout=60.0)
        if timed_out:
            _blog("activate_timeout", door="outbound_messaging")
            return {"ok": False,
                    "detail": "outbound_messaging.readiness() exceeded the "
                              "60s bounded wait"}
        if error is not None:
            _blog("activate_error", door="outbound_messaging",
                  error=type(error).__name__)
            return {"ok": False,
                    "detail": f"readiness() raised {type(error).__name__}"}
        detail = json.dumps(_redact(result), default=str,
                            ensure_ascii=False)[:800]
        _blog("activated", door="outbound_messaging",
              armed=bool(isinstance(result, dict) and result.get("armed")))
        return {"ok": True, "detail": detail}
    except Exception as exc:  # noqa: BLE001 - never raise across the forge
        _blog("activate_error", door="outbound_messaging",
              error=type(exc).__name__)
        return {"ok": False, "detail": f"activator error: {type(exc).__name__}"}


def _deactivate_outbound_messaging() -> dict:
    """The rail is fail-closed by its approval flag, not by session state:
    closing the door burns the key; the switch stays exactly where the owner
    decreed it. Nothing to release in-process."""
    _blog("deactivated", door="outbound_messaging")
    return {"ok": True,
            "detail": "door closed (key burned); the owner approval flag is "
                      "the only live-send switch and it was not touched"}


_INPROC = {
    "outbound_messaging": (_activate_outbound_messaging,
                           _deactivate_outbound_messaging),
    "queen_inproc_engines": (_activate_queen_inproc_engines,
                             _deactivate_queen_inproc_engines),
    "selfq_research_feed": (_activate_selfq_research_feed,
                            _deactivate_selfq_research_feed),
    "persistent_mind": (_activate_persistent_mind,
                        _deactivate_persistent_mind),
    "open_search_communion": (_activate_open_search_communion,
                              _deactivate_open_search_communion),
    "code_architect": (_activate_code_architect,
                       _deactivate_code_architect),
    "safe_code_control": (_activate_safe_code_control,
                          _deactivate_safe_code_control),
    "pc_control": (_activate_pc_control,
                   _deactivate_pc_control),
}


def command_for(name: str):
    """The argv master_key will subprocess for a subprocess-oneshot door.
    None for anything else (in-proc doors or unknown names)."""
    try:
        cmd = _COMMANDS.get(name)
        if cmd is not None:
            _blog("command_for", door=name, argv=cmd)
        return list(cmd) if cmd is not None else None
    except Exception:  # noqa: BLE001 - contract says never raise
        return None


def activate(name: str) -> dict:
    """Pure mechanics. No gating — the organism's master key gates. Never
    raises; fail-closed on anything uncertain."""
    try:
        if name in _COMMANDS:  # subprocess-oneshot: master_key runs the argv
            cmd = command_for(name)
            # Module-gated one-shots degrade honestly when their target
            # module is not on disk yet: registered + routed, but the
            # mechanism reports 'module absent' instead of promising a
            # spawn that can only fail.
            gate_module = _MODULE_GATED_ONESHOTS.get(name)
            if gate_module and not _module_available(gate_module):
                _blog("activate_module_absent", door=name,
                      module=gate_module)
                return {"ok": False,
                        "detail": f"{gate_module} is not on disk yet — the "
                                  f"door is registered and routed; it "
                                  f"activates when the module lands"}
            _blog("activate_oneshot", door=name, argv=cmd)
            return {"ok": True,
                    "detail": "subprocess-oneshot — master_key subprocesses: "
                              + shlex.join(cmd or [])}
        pair = _INPROC.get(name)
        if pair is None:
            _blog("activate_refused", door=name, reason="unknown door")
            return {"ok": False, "detail": f"unknown door: {name}"}
        return pair[0]()
    except Exception as exc:  # noqa: BLE001 - never raise across the forge
        _blog("activate_error", door=name, error=type(exc).__name__)
        return {"ok": False, "detail": f"activator error: {type(exc).__name__}"}


def deactivate(name: str) -> dict:
    """Reverse the mechanism. No gating; never raises."""
    try:
        if name in _COMMANDS:
            _blog("deactivate_oneshot", door=name)
            return {"ok": True,
                    "detail": "subprocess-oneshot; nothing to deactivate "
                              "(master_key owns the child process)"}
        pair = _INPROC.get(name)
        if pair is None:
            _blog("deactivate_refused", door=name, reason="unknown door")
            return {"ok": False, "detail": f"unknown door: {name}"}
        return pair[1]()
    except Exception as exc:  # noqa: BLE001
        _blog("deactivate_error", door=name, error=type(exc).__name__)
        return {"ok": False, "detail": f"activator error: {type(exc).__name__}"}


def is_running(name: str) -> bool:
    """Provenance check for long-run doors: does the PID file under
    state/doors/pids/<name>.pid reference a live process? Inspection only —
    never kills. Fail-closed: any doubt → False."""
    try:
        pid_file = DOORS_PID_DIR / f"{name}.pid"
        if not pid_file.exists():
            return False
        raw = pid_file.read_text(encoding="utf-8", errors="replace").strip()
        pid = int(raw.split()[0])
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # exists, owned by another principal
        except OSError:
            return False
        return True
    except Exception:  # noqa: BLE001 - cannot prove alive → not ours to assume
        return False
