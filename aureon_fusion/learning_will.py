"""🌱 LEARNING WILL — the sovereign learning will of the Aureon Fusion organism.

Owner decree (absolute):
  • The organism learns by FREE WILL — learning desires arise from internal
    state only, never external steering, trends, or push feeds.
  • The core stays the same; expansion of knowledge is the organism's choice.
  • Every learning action passes THREE gates, all fail-closed:
        1. CONSCIENCE   (aureon_fusion.conscience_hook.evaluate — VETO absolute)
        2. HNC COHERENCE (coherence_gamma from state/hnc_core_state.json —
                          below threshold the organism WAITS, never fabricates)
        3. AUTHORIZATION (aureon_fusion.capability_gate.check(
                          'network_access:fetch_public_data'); a missing matrix
                          row degrades to DEFERRED, never a crash)
  • Deep-learning discernment before anything is absorbed: novelty,
    contradiction (tagged contested, never absorbed as fact), corroboration,
    coherence-fit. Provenance receipts. Native reasoning only — NO external
    LLM calls.
  • External fetch is organism-initiated, on-demand, via the courteous
    api_communion layer. NO push scheduling, NO background ingest threads.
  • Silence is valid: if the organism seeks nothing, nothing is learned.

Import-safe: no organ is instantiated at import; suppression env vars are
honored via setdefault. All state writes are tmp+replace or locked appends.

CLI:
    python -m aureon_fusion.learning_will status
    python -m aureon_fusion.learning_will propose
    python -m aureon_fusion.learning_will consider [--dry]
"""

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .paths import FUSION_STATE, WORKSPACE, SERO_AUTONOMOUS

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

# ───────────────────────── doctrine constants ──────────────────────────────

COHERENCE_THRESHOLD = 0.25       # gamma below this → the organism WAITS
ABSORB_THRESHOLD = 0.55           # candidate score ≥ this → absorbed as fact
NEAR_DUP_THRESHOLD = 0.7         # token overlap above this → near-duplicate
JOURNAL_DIR = FUSION_STATE / "learning_will"
JOURNAL_FILE = JOURNAL_DIR / "journal.jsonl"
INTENTS_FILE = JOURNAL_DIR / "intents.json"
SATURATED_FILE = JOURNAL_DIR / "saturated_sources.json"
BUILD_LOG = FUSION_STATE / "build_learning_will.log"
HNC_STATE_FILE = FUSION_STATE / "hnc_core_state.json"
OPEN_SEARCH_SEEDS_FILE = FUSION_STATE / "open_search_seeds.json"
OPEN_SEARCH_SEEDS_FRESH_S = 3600.0
AUTH_GATE = "network_access:fetch_public_data"
JOURNAL_ROTATE_BYTES = 10 * 1024 * 1024
SIGNING_ENABLED_ENV = "AUREON_FUSION_EVENT_SIGNING"
RESEARCH_THROTTLE_FILE = FUSION_STATE / "research_throttle.json"
RESEARCH_THROTTLE_S = 600.0  # at most one research_faculty.try_research per 10 min
# Mycelium persistence: sero_mycelium's save() methods had zero callers, so
# the RAM-learned mind rewound to the last snapshot on every restart. The
# live learner is the critical path — saves are throttled (one per 5 min per
# organ instance, otherwise the 2–3 min cadence rewrites state every cycle)
# and fail-silent (a failed save retries in the next window, never breaks
# the learning loop).
MYCELIUM_PERSIST_THROTTLE_S = 300.0
_mycelium_save_last: dict = {}

_STOPWORDS = frozenset(
    "a an the and or but if then so to of in on at by for from with into about "
    "is are was were be been being have has had do does did i you it we they "
    "this that these those my your our their what when where which "
    "who whom why how can could should would will shall may might must than "
    "there here own very just also more most other some such only over under "
    "again further once".split()
)
_NEGATION_RE = re.compile(
    r"\b(not|no|never|none|isn't|aren't|wasn't|weren't|doesn't|don't|didn't|"
    r"cannot|can't|won't|couldn't|wouldn't|shouldn't|mustn't|false|fails|"
    r"wrong|refuted)\b")

# Cache of lazily-constructed organ handles. Unit probes may inject fakes
# here (learning_will._CACHE['knowledge_dataset'] = fake, …) — the accessors
# below never rebuild a cached entry.
_CACHE: dict = {}

OUTCOMES = ("absorbed", "refused", "deferred", "no_intent",
            "held_incoherent", "vetoed")


# ───────────────────────── small utilities ─────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _content_tokens(text: str) -> list:
    return [t for t in re.findall(r"[a-z0-9']+", (text or "").lower())
            if len(t) > 2 and t not in _STOPWORDS]


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _read_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


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
        if JOURNAL_FILE.exists() and JOURNAL_FILE.stat().st_size > JOURNAL_ROTATE_BYTES:
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


_research_absent_logged = False


def _trigger_research_faculty(intent: dict) -> None:
    """W8 (learning side): the gates passed and a real seek completed — hand
    the intent to the research faculty (organism-initiated, internally
    gated, throttled to at most one call per 10 minutes). The research
    faculty module may land mid-build; if the import fails we skip silently
    (journaled 'research_faculty_absent' once per process). Every failure
    mode here is fail-closed: the learning cycle is never disturbed."""
    global _research_absent_logged
    try:
        from . import research_faculty
    except Exception:
        if not _research_absent_logged:
            _research_absent_logged = True
            _blog("research_faculty_absent",
                  note="aureon_fusion.research_faculty not present yet — skipping")
        return
    try:
        now = time.time()
        last = 0.0
        data = _read_json(RESEARCH_THROTTLE_FILE, {})
        if isinstance(data, dict):
            try:
                last = float(data.get("last_call_ts", 0.0) or 0.0)
            except (TypeError, ValueError):
                last = 0.0
        if now - last < RESEARCH_THROTTLE_S:
            return
        # stamp before the call so a raising/hanging faculty can never be
        # re-hammered inside the throttle window. Preserve the file's other
        # keys — research_faculty owns per-mode budget records here; a bare
        # {"last_call_ts": now} write wipes them on every trigger.
        data = _read_json(RESEARCH_THROTTLE_FILE, {})
        if not isinstance(data, dict):
            data = {}
        data["last_call_ts"] = now
        _write_json_atomic(RESEARCH_THROTTLE_FILE, data)
        research_faculty.try_research(intent)
        _blog("research_faculty_triggered", intent_id=intent.get("id"))
    except Exception as exc:
        _blog("research_faculty_error", error=type(exc).__name__)


def _journal(record: dict) -> None:
    """Append one consider-cycle record to the learning journal."""
    _rotate_journal()
    _append_line(JOURNAL_FILE, json.dumps(record, ensure_ascii=False))
    # Every refused consideration (any branch) teaches the same lesson for
    # the TTL window: this question/url yielded nothing absorbable — rotate.
    if record.get("outcome") == "refused" and record.get("intent"):
        try:
            _record_refusal(record["intent"])
        except Exception:
            pass
        # The specific starvation refusal (fetch succeeded, discernment
        # emptied the page) also strikes the source url: generation rotates
        # away from it and, when everything local is saturated, re-rolls
        # to breadth. Only REAL fetches count — a dry-run refusal never
        # touched the source.
        if not record.get("dry_run") and \
                record.get("detail") == _NEAR_DUP_REFUSAL_DETAIL:
            try:
                _record_saturated_strike(
                    (record["intent"] or {}).get("url"))
            except Exception:
                pass


# ── Veto permanence ─────────────────────────────────────────────────────────
# A conscience VETO is final. Without suppression the same desire (e.g. a
# memory-island question) is re-proposed verbatim every cycle and vetoed
# every cycle — the will loops instead of moving on. Keys are the question
# hash (universal) and the memory-island node id when present.

VETOED_FILE = JOURNAL_DIR / "vetoed_intents.json"
_VETOED_CAP = 800


def _veto_keys(intent: dict) -> set:
    keys = set()
    question = intent.get("question") or ""
    if question:
        keys.add("q:" + hashlib.sha256(
            question.encode("utf-8")).hexdigest()[:16])
    node = (intent.get("origin") or {}).get("node_id")
    if node:
        keys.add("n:" + str(node))
    return keys


def _load_vetoed() -> dict:
    try:
        data = json.loads(VETOED_FILE.read_text(encoding="utf-8"))
        return dict(data.get("vetoed") or {})
    except Exception:
        return {}


def _is_vetoed(candidate: dict) -> bool:
    try:
        vetoed = _load_vetoed()
        return any(k in vetoed for k in _veto_keys(candidate))
    except Exception:
        return False


def _record_veto(intent: dict) -> None:
    """Persist a conscience VETO so the will never re-asks it. Prunes the
    oldest entries past the cap. Fail-closed: any error means nothing is
    suppressed (conscience simply vetoes again next time)."""
    keys = _veto_keys(intent)
    if not keys:
        return
    try:
        vetoed = _load_vetoed()
        now = _utc_now()
        for k in keys:
            vetoed[k] = now
        if len(vetoed) > _VETOED_CAP:
            oldest = sorted(vetoed.items(), key=lambda kv: kv[1])[
                len(vetoed) - _VETOED_CAP:]
            for k, _ in oldest:
                vetoed.pop(k, None)
        _write_json_atomic(VETOED_FILE, {"vetoed": vetoed,
                                         "updated_at": now})
    except Exception:
        pass


# ── Refusal-awareness (time-bound) ──────────────────────────────────────────
# A refusal whose cause is permanent-in-context (all near-duplicates of an
# already-absorbed page, nothing usable fetched) is re-proposed verbatim
# every cycle — observed live: the same 3 intents ('System', 'Cognition',
# cycle-761 telemetry) cycling every ~2 min for over an hour, refusing the
# same way each time. Suppress refused question/url keys for a TTL (6h) so
# the curiosity rotates to genuinely new ground. Unlike a conscience VETO
# this expires: the world may change, and so may her corpus.

REFUSED_FILE = JOURNAL_DIR / "refused_intents.json"
_REFUSED_CAP = 400
_REFUSED_TTL_S = 6 * 3600


def _refused_keys(intent: dict) -> set:
    keys = set()
    question = intent.get("question") or ""
    if question:
        keys.add("q:" + hashlib.sha256(
            question.encode("utf-8")).hexdigest()[:16])
    url = intent.get("url")
    if url:
        keys.add("u:" + str(url)[:200])
    return keys


def _load_refused() -> dict:
    try:
        data = json.loads(REFUSED_FILE.read_text(encoding="utf-8"))
        return dict(data.get("refused") or {})
    except Exception:
        return {}


def _is_refused(candidate: dict, now: float | None = None) -> bool:
    try:
        now = now if now is not None else time.time()
        refused = _load_refused()
        for k in _refused_keys(candidate):
            ts = refused.get(k)
            if ts and (now - float(ts)) < _REFUSED_TTL_S:
                return True
        return False
    except Exception:
        return False


def _record_refusal(intent: dict) -> None:
    """Persist a refused question/url so the will rotates away for the TTL.
    Fail-closed: any error means nothing is suppressed."""
    keys = _refused_keys(intent)
    if not keys:
        return
    try:
        refused = _load_refused()
        now = time.time()
        for k in keys:
            refused[k] = now
        if len(refused) > _REFUSED_CAP:
            oldest = sorted(refused.items(), key=lambda kv: kv[1])[
                len(refused) - _REFUSED_CAP:]
            for k, _ in oldest:
                refused.pop(k, None)
        _write_json_atomic(REFUSED_FILE, {"refused": refused,
                                          "updated_at": _utc_now()})
    except Exception:
        pass


# ── Saturated-source registry (strikes + decay) ─────────────────────────────
# The refusal-TTL above rotates a dead question away for 6h, but the deeper
# failure observed live: the intent generator derives target URLs from her
# own knowledge_dataset fragments, so the same SOURCE pages keep coming back
# (Ethics fetched at max_similarity 1.0 — already absorbed verbatim; ~160 of
# 300 considerations refused "all near-duplicates or empty" while the gate
# trio passed every time). This registry remembers which source urls
# discernment has emptied: each all-near-dups refusal adds a strike; strikes
# halve per 24h idle so a source is rested, never banned forever. Generation
# excludes urls at >= _SATURATED_STRIKE_FLOOR current strikes and falls back
# to breadth (SeekAct.resolve_fresh_target) when every local candidate is
# saturated. Fail-closed: missing/corrupt registry -> no exclusions, never
# a crash. Discernment itself is untouched — near-dups are still refused.

_SATURATED_CAP = 500
_SATURATED_STRIKE_FLOOR = 2
_SATURATED_DECAY_S = 24 * 3600.0
_NEAR_DUP_REFUSAL_DETAIL = (
    "discernment found nothing worth absorbing (all near-duplicates or empty)")


def _saturation_key(url) -> str:
    """One registry key per source, so the two Wikipedia surface forms of
    the same page (/wiki/X and /api/rest_v1/page/summary/X) share strikes.
    Non-Wikipedia urls key verbatim (fetched url is the honest identity)."""
    u = str(url or "").strip()
    if not u:
        return ""
    try:
        from urllib.parse import unquote, urlparse
        p = urlparse(u)
        host = (p.netloc or "").lower()
        if host in ("en.wikipedia.org", "wikipedia.org"):
            path = unquote(p.path or "")
            m = re.match(r"^/wiki/([^/?]+)$", path)
            if m:
                return "wikipedia:" + m.group(1).lower()
            m = re.match(
                r"^/api/rest_v1/page/(?:summary|html|related)/([^/?]+)$",
                path)
            if m:
                return "wikipedia:" + m.group(1).lower()
    except Exception:
        pass
    return u


def _load_saturated() -> dict:
    """url -> {'strikes', 'last_ts'}; missing/corrupt -> {} (fail-closed:
    no exclusions, never a crash)."""
    try:
        data = json.loads(SATURATED_FILE.read_text(encoding="utf-8"))
        sources = data.get("sources") if isinstance(data, dict) else None
        out = {}
        for url, entry in (sources or {}).items():
            if isinstance(entry, dict):
                out[str(url)] = entry
        return out
    except Exception:
        return {}


def _saturated_effective_strikes(entry: dict, now: float) -> float:
    """Current strike weight: halved once per full 24h since last_ts, so a
    rested source decays back into circulation."""
    try:
        strikes = float(entry.get("strikes") or 0.0)
        last = float(entry.get("last_ts") or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if strikes <= 0.0:
        return 0.0
    halvings = int((now - last) // _SATURATED_DECAY_S) if last else 0
    return strikes * (0.5 ** halvings) if halvings > 0 else strikes


def _saturated_keys_at(floor: float, now: float) -> set:
    try:
        return {k for k, e in _load_saturated().items()
                if _saturated_effective_strikes(e, now) >= floor}
    except Exception:
        return set()


def _is_saturated_url(url, now: float | None = None) -> bool:
    """Fail-open on any doubt: a unreadable registry never blocks learning."""
    try:
        key = _saturation_key(url)
        if not key:
            return False
        now = now if now is not None else time.time()
        entry = _load_saturated().get(key)
        return entry is not None and \
            _saturated_effective_strikes(entry, now) >= _SATURATED_STRIKE_FLOOR
    except Exception:
        return False


def _record_saturated_strike(url, now: float | None = None) -> None:
    """A real fetch of this url yielded nothing absorbable — add a strike
    (decayed count + 1). Fail-closed: any error changes nothing."""
    key = _saturation_key(url)
    if not key:
        return
    try:
        now = now if now is not None else time.time()
        sources = _load_saturated()
        effective = _saturated_effective_strikes(sources.get(key) or {}, now)
        sources[key] = {"strikes": round(effective + 1.0, 4), "last_ts": now}
        if len(sources) > _SATURATED_CAP:
            oldest = sorted(
                sources.items(),
                key=lambda kv: float(kv[1].get("last_ts") or 0))[
                len(sources) - _SATURATED_CAP:]
            for k, _ in oldest:
                sources.pop(k, None)
        _write_json_atomic(SATURATED_FILE, {"sources": sources,
                                            "updated_at": _utc_now()})
    except Exception:
        pass


def _journal_entries(limit: int = 100) -> list:
    entries = []
    files = [JOURNAL_FILE] + sorted(JOURNAL_DIR.glob("journal.*.jsonl")) \
        if JOURNAL_DIR.exists() else []
    files += sorted(JOURNAL_DIR.glob("journal.jsonl.pid*")) \
        if JOURNAL_DIR.exists() else []
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


# ───────────────────────── organ accessors (lazy) ──────────────────────────

def _workspace_module(name: str):
    if str(WORKSPACE) not in sys.path:
        sys.path.insert(0, str(WORKSPACE))
    import importlib
    return importlib.import_module(name)


def _get_knowledge_dataset():
    """The queen's live knowledge dataset (fusion state copy — the same file
    queen_mind reads). Duck-typed pocket absorbs; find_similar for novelty."""
    if "knowledge_dataset" in _CACHE:
        return _CACHE["knowledge_dataset"]
    kd = None
    try:
        upstream = _workspace_module("aureon_fusion.paths").AUREON_UPSTREAM
        if str(upstream) not in sys.path:
            sys.path.insert(0, str(upstream))
        # Same persistence seam the queen process patches: dedupe,
        # telemetry tagging, merge-on-save. Standalone processes (CLI
        # consider/propose/status) must not save unpatched whole-file
        # snapshots or they clobber the live writers.
        from aureon_fusion import knowledge_dataset_patch
        knowledge_dataset_patch.ensure_applied()
        from aureon.queen.knowledge_dataset import KnowledgeDataset
        kd_path = FUSION_STATE / "queen_mind" / "knowledge_dataset.json"
        kd = KnowledgeDataset(path=str(kd_path))
    except Exception as exc:
        _blog("organ_unavailable", organ="knowledge_dataset",
              error=type(exc).__name__)
        kd = None
    _CACHE["knowledge_dataset"] = kd
    return kd


def _get_memory_web():
    if "memory_web" in _CACHE:
        return _CACHE["memory_web"]
    web = None
    try:
        web = _workspace_module("sero_memory_web").MemoryWeb()
    except Exception as exc:
        _blog("organ_unavailable", organ="memory_web", error=type(exc).__name__)
        web = None
    _CACHE["memory_web"] = web
    return web


def _get_mycelium():
    if "mycelium" in _CACHE:
        return _CACHE["mycelium"]
    net = None
    try:
        net = _workspace_module("sero_mycelium").MyceliumNetwork()
    except Exception as exc:
        _blog("organ_unavailable", organ="mycelium", error=type(exc).__name__)
        net = None
    _CACHE["mycelium"] = net
    return net


def _get_mind_augment():
    """The dormant MindAugment — zero callers today; the learning will is
    its activation. Failure here must never break the learning cycle."""
    if "mind_augment" in _CACHE:
        return _CACHE["mind_augment"]
    augment = None
    try:
        augment = _workspace_module("sero_mycelium").MindAugment()
    except Exception as exc:
        _blog("organ_unavailable", organ="mind_augment", error=type(exc).__name__)
        augment = None
    _CACHE["mind_augment"] = augment
    return augment


def _save_mycelium_throttled(holder) -> None:
    """Best-effort, throttled persistence of a sero_mycelium organ instance
    (MyceliumNetwork.save / MindAugment.save). Never raises."""
    now = time.time()
    key = id(holder)
    if now - _mycelium_save_last.get(key, 0.0) < MYCELIUM_PERSIST_THROTTLE_S:
        return
    try:
        holder.save()
    except Exception:
        return  # fail-silent: the next throttled window retries
    _mycelium_save_last[key] = now


def _read_coherence_gamma():
    """(gamma, status) — status ∈ ok | low | missing | corrupt. Fail-closed:
    anything unreadable is 'missing' and the organism HOLDS."""
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


def _fresh_open_search_seeds() -> list:
    """The organism's own open-search seeds (primed by its sovereign doors).
    Fail-closed: missing, unreadable, or older than OPEN_SEARCH_SEEDS_FRESH_S
    → no seeds. The file is organism-local state — reading it is
    internal-state-only, never a push feed."""
    try:
        if not OPEN_SEARCH_SEEDS_FILE.exists():
            return []
        data = json.loads(OPEN_SEARCH_SEEDS_FILE.read_text(encoding="utf-8"))
        stamp = datetime.fromisoformat(
            str(data.get("timestamp") or "").replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - stamp).total_seconds()
        if age < 0 or age > OPEN_SEARCH_SEEDS_FRESH_S:
            return []
        return [s for s in (data.get("seeds") or []) if isinstance(s, dict)]
    except Exception:
        return []


# ───────────────────────── (A) CuriosityEngine ─────────────────────────────

class CuriosityEngine:
    """Generates learning desires ONLY from internal state. Never external
    trends, never push feeds. Silence is valid: if nothing is genuinely
    sought, propose() returns None."""

    MIN_DESIRE = 0.25  # below this, the organism simply is not asking

    def _candidates(self) -> list:
        self._saturated_candidates: list = []
        candidates = []
        candidates.extend(self._from_unanswered_questions())
        candidates.extend(self._from_mycelium_curiosity())
        candidates.extend(self._from_memory_islands())
        candidates.extend(self._from_insight_patterns())
        candidates.extend(self._from_open_search_seeds())
        candidates = [c for c in candidates
                      if c.get("desire_score", 0) >= self.MIN_DESIRE]
        # Conscience VETO is permanent: a vetoed desire is never re-asked.
        # A TTL-bound refusal is temporary: not asked again within its TTL.
        candidates = [c for c in candidates
                      if not _is_vetoed(c) and not _is_refused(c)]
        # Saturated-source registry: a url discernment has emptied (>= floor
        # current strikes) is dead ground for now — excluded so the will
        # rotates to unsaturated sources. The excluded candidates are kept
        # for a breadth re-roll in propose() when nothing fresh remains.
        try:
            now = time.time()
            dead = _saturated_keys_at(_SATURATED_STRIKE_FLOOR, now)
            if dead:
                fresh = []
                for c in candidates:
                    u = c.get("url")
                    if u and _saturation_key(u) in dead:
                        self._saturated_candidates.append(c)
                    else:
                        fresh.append(c)
                candidates = fresh
        except Exception:
            pass
        return candidates

    def _resolve_url(self, tags) -> str | None:
        """An organism-chosen target URL may only come from internal state
        (a fragment or memory tag already carrying one). Never synthesized
        from trends; None means there is nothing to fetch."""
        for tag in tags or []:
            t = str(tag)
            if t.startswith(("http://", "https://")):
                return t
            if t.lower().startswith("url:"):
                return t.split(":", 1)[1].strip() or None
        return None

    def _from_unanswered_questions(self) -> list:
        kd = _get_knowledge_dataset()
        if kd is None:
            return []
        out = []
        try:
            frags = list(getattr(kd, "_fragments", []) or [])
        except Exception:
            return []
        for frag in frags:
            try:
                tags = [str(t).lower() for t in (getattr(frag, "tags", []) or [])]
                if "researched" in tags:
                    continue
                text = (getattr(frag, "text", "") or "").strip()
                dtype = str(getattr(frag, "data_type", "") or "").lower()
                # Her own heartbeat is not an unanswered question — never
                # turn cycle telemetry into a seek target (observed: the
                # will fetching canonical pages about 'Metacognitive cycle
                # 761 persona=queen…' and getting everything dropped).
                if dtype == "telemetry" or \
                        text.startswith("Metacognitive cycle "):
                    continue
                is_question = (dtype in ("question", "query")
                               or text.endswith("?")
                               or "question" in tags)
                if not is_question or len(text) < 10:
                    continue
                age_s = max(0.0, time.time() - float(getattr(frag, "timestamp", 0) or 0))
                patience = min(1.0, age_s / 86400.0)  # older unanswered = keener
                score = 0.45 + 0.30 * patience
                out.append({
                    "kind": "unanswered_question",
                    "question": text[:300],
                    "domain": self._domain_for_text(text, None),
                    "desire_score": round(score, 4),
                    "source": "knowledge_dataset",
                    "url": self._resolve_url(getattr(frag, "tags", []) or []),
                    "origin": {"fragment_tags": tags[:8]},
                })
            except Exception:
                continue
        return out

    def _from_mycelium_curiosity(self) -> list:
        net = _get_mycelium()
        if net is None:
            return []
        out = []
        try:
            domains = dict(getattr(net, "domains", {}) or {})
        except Exception:
            return []
        for domain, agg in domains.items():
            try:
                confidence = float((agg or {}).get("confidence", 0.5))
            except (TypeError, ValueError):
                confidence = 0.5
            if confidence >= 0.6:
                continue  # confident domains are not curious
            curiosity = 1.0 - confidence
            score = 0.30 + 0.55 * curiosity
            out.append({
                "kind": "domain_curiosity",
                "question": (f"What evidence would raise my confidence in the "
                             f"'{domain}' domain (currently {confidence:.2f})?"),
                "domain": domain,
                "desire_score": round(score, 4),
                "source": "mycelium_network",
                "url": None,
                "origin": {"confidence": round(confidence, 4),
                           "curiosity": round(curiosity, 4)},
            })
        return out

    def _from_memory_islands(self) -> list:
        web = _get_memory_web()
        if web is None:
            return []
        try:
            nodes = list(getattr(web, "nodes", {}).values())
            edges = list(getattr(web, "edges", []) or [])
        except Exception:
            return []
        if not nodes or len(nodes) < 2:
            return []
        degree = {}
        for e in edges:
            for nid in (getattr(e, "source_id", None), getattr(e, "target_id", None)):
                if nid:
                    degree[nid] = degree.get(nid, 0) + 1
        out = []
        for node in nodes:
            try:
                deg = degree.get(node.id, 0)
                if deg > 1:
                    continue  # connected enough — not an island
                intensity = float(getattr(node, "intensity", 0.5) or 0.5)
                score = 0.20 + 0.35 * (1.0 - min(deg, 1)) + 0.20 * (1.0 - intensity)
                content = (getattr(node, "content", "") or "").strip()
                if len(content) < 10:
                    continue
                out.append({
                    "kind": "memory_island",
                    "question": (f"What connects to this isolated memory: "
                                 f"'{content[:120]}'?"),
                    "domain": self._domain_for_text(content, None),
                    "desire_score": round(score, 4),
                    "source": "memory_web",
                    "url": self._resolve_url(getattr(node, "tags", []) or []),
                    "origin": {"node_id": node.id, "degree": deg,
                               "intensity": round(intensity, 4)},
                })
            except Exception:
                continue
        # Only the loneliest islands compete.
        out.sort(key=lambda c: -c["desire_score"])
        return out[:5]

    def _from_insight_patterns(self) -> list:
        """Recurring queen.mind insight patterns: tokens that keep surfacing
        across distinct mind cycles are something the organism keeps touching
        without yet understanding — a free-will desire to go deeper."""
        reports = FUSION_STATE / "queen_mind" / "reports.jsonl"
        if not reports.exists():
            return []
        syntheses = []
        try:
            with open(reports, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()[-60:]
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                txt = rec.get("thought", {}).get("synthesis") \
                    if isinstance(rec.get("thought"), dict) else None
                txt = txt or rec.get("insight") or ""
                # Narration + reflection carry her actual themes; the thought
                # synthesis is a per-cycle template, so on its own every
                # "recurring token" is a template word and the same
                # self-referential question recycles forever while outward
                # learning starves (owner: "she's trying to learn, let her").
                if isinstance(rec.get("narration"), str):
                    txt = (txt + " " + rec["narration"]) if txt else rec["narration"]
                refl = rec.get("reflection")
                if isinstance(refl, dict):
                    extra = []
                    for key in ("reasoning_summary", "guidance"):
                        v = refl.get(key)
                        if isinstance(v, str):
                            extra.append(v)
                        elif isinstance(v, list):
                            extra.extend(map(str, v))
                    if extra:
                        txt = (txt + " " + " ".join(extra)) if txt \
                            else " ".join(extra)
                if txt:
                    syntheses.append(str(txt))
        except OSError:
            return []
        if len(syntheses) < 3:
            return []
        per_cycle = [set(_content_tokens(s)) for s in syntheses]
        cycles_seen = {}
        for i, toks in enumerate(per_cycle):
            for t in toks:
                cycles_seen.setdefault(t, set()).add(i)
        # A token in (nearly) EVERY cycle is template, not theme — exclude
        # ubiquities; keep tokens recurring across a meaningful minority of
        # cycles (genuine themes she keeps touching without understanding).
        ubiquity = max(4, int(0.75 * len(syntheses)))
        recurring = [(t, len(cyc)) for t, cyc in cycles_seen.items()
                     if 3 <= len(cyc) < ubiquity]
        if not recurring:
            return []
        recurring.sort(key=lambda kv: -kv[1])
        top = [t for t, _ in recurring[:4]]
        score = 0.30 + 0.10 * min(len(recurring), 5)
        return [{
            "kind": "insight_pattern",
            "question": (f"What is the deeper pattern behind the recurring "
                         f"theme '{' / '.join(top)}' in my own insight stream?"),
            "domain": "perception",
            "desire_score": round(score, 4),
            "source": "queen_mind_insights",
            "url": None,
            "origin": {"recurring_tokens": top,
                       "cycles": len(syntheses)},
        }]

    def _from_open_search_seeds(self) -> list:
        """The organism's own open-search seeds (primed through its sovereign
        doors into state/open_search_seeds.json) are learning intents it
        already chose once. Novelty-weighted: a seed whose topic tokens are
        already well represented in the knowledge dataset is less desired;
        a genuinely unseen seed is keenly sought. Internal-state-only — the
        seeds file is organism-local state, never a push feed."""
        seeds = _fresh_open_search_seeds()
        if not seeds:
            return []
        kd = _get_knowledge_dataset()
        known: set = set()
        try:
            for frag in list(getattr(kd, "_fragments", []) or [])[:400]:
                known |= set(_content_tokens(getattr(frag, "text", "") or ""))
        except Exception:
            pass
        out = []
        for seed in seeds[:8]:
            try:
                topic = str(seed.get("topic") or "").strip()
                url = str(seed.get("url") or "")
                if not topic:
                    continue
                toks = set(_content_tokens(topic))
                novelty = 1.0 - min(1.0, len(toks & known) / max(1, len(toks)))
                score = 0.25 + 0.55 * novelty
                out.append({
                    "kind": "open_search_seed",
                    "question": (f"What does the open search seed "
                                 f"'{topic[:100]}' reveal to me?"),
                    "domain": self._domain_for_text(topic, None),
                    "desire_score": round(score, 4),
                    "source": "open_search_seeds",
                    "url": url if url.startswith(("http://", "https://"))
                           else None,
                    "origin": {"seed_topic": topic[:120],
                               "seed_url": url[:200],
                               "novelty": round(novelty, 4)},
                })
            except Exception:
                continue
        return out

    def _domain_for_text(self, text: str, fallback) -> str:
        toks = set(_content_tokens(text))
        hints = {
            "schumann": {"schumann", "resonance", "planetary", "field", "hz"},
            "ethics": {"conscience", "ethic", "veto", "moral", "consent", "autonomy"},
            "memory": {"memory", "remember", "recall", "forget", "archive"},
            "action": {"action", "execute", "act", "gate", "authorize"},
            "perception": {"perceive", "sense", "observe", "signal", "pattern",
                           "insight", "synthesis"},
            "temporal": {"time", "timeline", "temporal", "delay", "cycle",
                         "phase", "history"},
        }
        best, best_hits = fallback, 0
        for domain, words in hints.items():
            hits = len(toks & words)
            if hits > best_hits:
                best, best_hits = domain, hits
        return best or "memory"

    def _breadth_reroll(self, saturated: list) -> list:
        """Every local candidate points at a saturated source — derive a
        fresh target for the strongest desires through the module's own
        resolution mechanisms (fresh seeds -> open_sources adjacent
        candidates -> canonical encyclopedic endpoint), skipping anything
        saturated. The desire is unchanged; only the source diversifies.
        Returns [] when the will can derive nothing unsaturated (silence
        is valid)."""
        out = []
        for cand in saturated[:3]:
            try:
                url = SeekAct.resolve_fresh_target(cand, _is_saturated_url)
            except Exception:
                url = None
            if not url or url == cand.get("url"):
                continue
            new = dict(cand)
            origin = dict(cand.get("origin") or {})
            origin["saturation_reroll_from"] = str(cand.get("url") or "")[:200]
            new["origin"] = origin
            new["url"] = url
            out.append(new)
            _blog("saturation_reroll", kind=cand.get("kind"),
                  from_url=str(cand.get("url"))[:120], to_url=url[:120],
                  question=str(cand.get("question"))[:120])
        return out

    def propose(self) -> dict | None:
        """Pick the single strongest learning desire, or None (silence)."""
        candidates = self._candidates()
        if not candidates:
            # All local candidates target saturated sources — the will
            # falls back to breadth: same desire, a different source path.
            rerolled = self._breadth_reroll(self._saturated_candidates)
            if rerolled:
                candidates = rerolled
        if not candidates:
            _blog("propose", result="silence")
            return None
        # Potential coherence contribution: feeding an under-confident domain
        # matters more than re-treading a confident one.
        net = _get_mycelium()
        for c in candidates:
            if c.get("domain") and net is not None:
                try:
                    conf = float(net.get_domain_confidence(c["domain"]))
                    c["desire_score"] = round(
                        c["desire_score"] + 0.20 * (1.0 - conf), 4)
                except Exception:
                    pass
        candidates.sort(key=lambda c: -c["desire_score"])
        top = candidates[0]
        # Volition diversity (mechanics, not steering): the insight_pattern
        # generator used to win ~100% of considerations and starve every
        # other curiosity class (memory islands, seeds, mycelium gaps).
        # Once every 3rd consideration, if a non-insight candidate is above
        # MIN_DESIRE, let the strongest one win instead.
        try:
            non_insight = [c for c in candidates
                           if c.get("kind") != "insight_pattern"
                           and c.get("desire_score", 0) >= self.MIN_DESIRE]
            if non_insight and top.get("kind") == "insight_pattern":
                state_p = JOURNAL_DIR / "rotation.json"
                try:
                    n = int((_read_json(state_p, {}) or {}).get("count") or 0)
                except Exception:
                    n = 0
                n += 1
                _write_json_atomic(state_p, {"count": n})
                if n % 3 == 0:
                    top = non_insight[0]
        except Exception:
            pass
        intent = {
            "id": "lw_" + hashlib.sha256(
                f"{top['question']}|{time.time_ns()}".encode("utf-8")
            ).hexdigest()[:12],
            "created_at": _utc_now(),
            "desire_score": top["desire_score"],
            **{k: top[k] for k in ("kind", "question", "domain", "source",
                                   "url", "origin") if k in top},
        }
        _write_json_atomic(INTENTS_FILE, {
            "open_intent": intent, "recorded_at": _utc_now(),
            "candidates_considered": len(candidates),
        })
        _blog("propose", intent_id=intent["id"], kind=intent["kind"],
              score=intent["desire_score"], domain=intent.get("domain"))
        return intent


# ───────────────────────── (B) LearningGate ────────────────────────────────

class LearningGate:
    """The gate trio. ALL fail-closed. Verdicts are recorded for the journal
    even after the first failure — the organism audits every gate it asked."""

    def check(self, intent: dict) -> dict:
        gate = {"passed": False, "outcome": None, "conditions": []}

        conscience = self._check_conscience(intent)
        gate["conscience"] = conscience
        if conscience.get("verdict") == "VETO":
            gate["outcome"] = "vetoed"
            gate["detail"] = conscience.get("reasoning", "conscience VETO")
            return gate
        for cond in conscience.get("conditions") or []:
            gate["conditions"].append(f"conscience: {cond}")

        coherence = self._check_coherence()
        gate["coherence"] = coherence
        if not coherence.get("passed"):
            gate["outcome"] = "held_incoherent"
            gate["detail"] = coherence.get("detail")
            return gate

        auth = self._check_authorization()
        gate["authorization"] = auth
        if not auth.get("passed"):
            # Missing matrix row (another agent may add it) or HOLD/DENY —
            # record and retry next cycle. Never crash.
            gate["outcome"] = "deferred"
            gate["detail"] = auth.get("detail")
            return gate

        gate["passed"] = True
        gate["outcome"] = "authorized"
        gate["detail"] = ("conscience %s, gamma %.3f, %s allowed" % (
            conscience.get("verdict"), coherence.get("gamma") or 0.0,
            AUTH_GATE))
        return gate

    def _check_conscience(self, intent: dict) -> dict:
        desc = (f"Learning will: organism-initiated fetch of public data to "
                f"resolve an internal learning desire "
                f"[{intent.get('kind', '?')}] domain={intent.get('domain', '?')}: "
                f"{(intent.get('question') or '')[:180]}")
        try:
            from aureon_fusion import conscience_hook
            verdict = conscience_hook.evaluate(desc, {"organ": "learning_will"})
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

    def _check_coherence(self) -> dict:
        gamma, status = _read_coherence_gamma()
        if status == "ok" and gamma is not None and gamma >= COHERENCE_THRESHOLD:
            return {"passed": True, "gamma": gamma, "status": status,
                    "threshold": COHERENCE_THRESHOLD}
        if status == "ok":
            detail = (f"coherence_gamma {gamma:.3f} < {COHERENCE_THRESHOLD} "
                      f"— the organism waits until coherent; it never "
                      f"fabricates knowledge to fill the gap")
        elif status == "missing":
            detail = ("hnc_core_state.json missing — coherence unknown; "
                      "fail-closed HOLD")
        else:
            detail = ("hnc_core_state.json unreadable/corrupt — coherence "
                      "unknown; fail-closed HOLD")
        return {"passed": False, "gamma": gamma, "status": status,
                "threshold": COHERENCE_THRESHOLD, "detail": detail}

    def _check_authorization(self) -> dict:
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


# ───────────────────────── (C) SeekAct ─────────────────────────────────────

class SeekAct:
    """Organism-chosen URL only, via the courteous api_communion layer
    (rate limit, circuit breaker, stale-marked). A stale marker degrades
    confidence; it never crashes. NO push scheduling anywhere near this."""

    STALE_PENALTY = 0.15

    _STOPWORDS = frozenset(
        "what is the a an of to in and or behind deeper pattern theme "
        "recurring own my your their its this that these those stream "
        "insight question meaning reason between within about for with "
        "does do did are was were how why when which who whom".split())

    @staticmethod
    def _looks_like_url(s) -> bool:
        return str(s or "").strip().startswith(("http://", "https://"))

    @classmethod
    def _resolve_from_seeds(cls, concept: str) -> str | None:
        """A fresh organism-primed seed whose topic agrees with the concept
        is the most sovereign target available — the organism already chose
        it once. Best token overlap wins; nothing agreeing → None."""
        tokens = set(_content_tokens(concept.replace("_", " ")))
        if not tokens:
            return None
        best_url, best_hits = None, 0
        for seed in _fresh_open_search_seeds():
            try:
                topic = str(seed.get("topic") or "")
                url = str(seed.get("url") or "")
                if not topic or not cls._looks_like_url(url):
                    continue
                hits = len(tokens & set(_content_tokens(topic)))
                if hits > best_hits:
                    best_url, best_hits = url, hits
            except Exception:
                continue
        return best_url

    @classmethod
    def _candidate_to_url(cls, cand: str) -> str | None:
        """The module's single candidate→URL conversion: a URL candidate is
        taken directly; a title candidate becomes the canonical Wikipedia
        page-summary endpoint."""
        from urllib.parse import quote
        cand = str(cand or "").strip()
        if not cand:
            return None
        if cls._looks_like_url(cand):
            return cand
        title = cand.replace(" ", "_")
        if title:
            return ("https://en.wikipedia.org/api/rest_v1/page/summary/"
                    + quote(title))
        return None

    @classmethod
    def _wikipedia_search_titles(cls, concept: str) -> list:
        """Ask Wikipedia for related article titles for a concept.
        Returns a list of candidate titles (with spaces). Uses the courteous
        api_communion layer. Failures degrade to an empty list."""
        from urllib.parse import quote
        concept = str(concept or "").strip().replace("_", " ")
        if not concept:
            return []
        url = ("https://en.wikipedia.org/w/api.php?action=opensearch&search="
               + quote(concept) + "&limit=5&format=json")
        try:
            from aureon_fusion import api_communion
            data = api_communion.get_json(url, ttl_s=3600.0, timeout=15.0)
            if not isinstance(data, list) or len(data) < 2:
                return []
            titles = data[1]
            if not isinstance(titles, list):
                return []
            return [str(t).strip() for t in titles if str(t).strip()]
        except Exception as exc:
            _blog("wikipedia_search_error", concept=concept[:80],
                  error=type(exc).__name__)
            return []

    @classmethod
    def _resolve_from_open_sources(cls, concept: str) -> str | None:
        """Courteous candidate lookup through the organism's own open_sources
        organ (public search, all traffic via api_communion). Guarded: a
        missing or failing organ degrades to None, never a crash. The first
        usable candidate is taken directly when it is already a URL, else
        built into a canonical Wikipedia page-summary endpoint."""
        try:
            from aureon_fusion import open_sources
            candidates = open_sources.search_candidates(concept) or []
        except Exception as exc:
            _blog("open_sources_unavailable", error=type(exc).__name__)
            return None
        for cand in list(candidates)[:3]:
            url = cls._candidate_to_url(cand)
            if url:
                return url
        return None

    @classmethod
    def _concept_from_question(cls, question: str) -> str | None:
        """The desire's key concept, from the organism's own words: the
        quoted theme preferred, else the longest content-bearing token.
        Shared by both resolution paths so a saturation re-roll anchors on
        the same sovereign concept."""
        import re as _re
        question = (question or "").strip()
        if not question:
            return None
        quoted = _re.findall(r"'([^']{3,60})'|\"([^\"]{3,60})\"", question)
        concept = None
        for a, b in quoted:
            cand = (a or b).strip()
            if cand:
                concept = cand
                break
        if concept and ("/" in concept or "," in concept or ";" in concept):
            # A multi-theme phrase is not a canonical page title — take the
            # most salient single token from the organism's own words.
            parts = [p.strip() for p in concept.replace(",", "/").replace(
                ";", "/").split("/")]
            parts = [p for p in parts if p]
            concept = max(parts, key=len) if parts else None
        if not concept:
            words = [w.strip(".,;:!?()").lower() for w in question.split()]
            keep = [w for w in words if w and w not in cls._STOPWORDS
                    and len(w) > 2 and w.isalpha()]
            if not keep:
                return None
            concept = max(keep, key=len)
        return concept or None

    @classmethod
    def resolve_canonical_target(cls, intent: dict) -> str | None:
        """Sovereign canonical resolution. The gates have passed; the will
        picks its OWN destination from the desire's key concept. Resolution
        order, all organism-initiated (no external system suggests anything,
        no trend feed is consulted):
          (i)   a fresh organism-primed open-search seed whose topic agrees
                with the concept — the will already chose it once;
          (ii)  a courteous candidate from the open_sources organ;
          (iii) the canonical encyclopedic endpoint guessed from the
                organism's own question tokens (the long-standing fallback).
        Returns a URL or None (caller then refuses — no fabrication)."""
        concept = cls._concept_from_question((intent or {}).get("question"))
        if not concept:
            return None
        url = cls._resolve_from_seeds(concept)
        if url:
            return url
        url = cls._resolve_from_open_sources(concept)
        if url:
            return url
        from urllib.parse import quote
        slug = concept.replace(" ", "_")
        if not slug:
            return None
        return ("https://en.wikipedia.org/api/rest_v1/page/summary/"
                + quote(slug))

    @classmethod
    def resolve_fresh_target(cls, intent: dict, is_blocked) -> str | None:
        """Saturation re-roll: the SAME sovereign resolution mechanisms as
        resolve_canonical_target (fresh seeds -> open_sources adjacent
        candidates -> canonical encyclopedic endpoint), but any candidate
        failing is_blocked(url) is skipped — a saturated source never
        receives a repeat fetch. Returns None when every derivable target
        is blocked (the caller refuses; nothing is fabricated)."""
        from urllib.parse import quote
        concept = cls._concept_from_question((intent or {}).get("question"))
        if not concept:
            return None
        # (i) fresh organism-primed seeds whose topic agrees — unless blocked
        tokens = set(_content_tokens(concept.replace("_", " ")))
        for seed in _fresh_open_search_seeds():
            try:
                topic = str(seed.get("topic") or "")
                url = str(seed.get("url") or "")
                if not topic or not cls._looks_like_url(url):
                    continue
                if (tokens & set(_content_tokens(topic))) \
                        and not is_blocked(url):
                    return url
            except Exception:
                continue
        # (ii) courteous open_sources candidates — first NON-saturated one,
        # so an adjacent title (breadth) wins over the exhausted page
        try:
            from aureon_fusion import open_sources
            candidates = open_sources.search_candidates(concept) or []
        except Exception as exc:
            _blog("open_sources_unavailable", error=type(exc).__name__)
            candidates = []
        for cand in list(candidates)[:5]:
            try:
                url = cls._candidate_to_url(cand)
            except Exception:
                url = None
            if url and not is_blocked(url):
                return url
        # (iii-b) Wikipedia search breadth: if the direct slug is saturated
        # or the concept is broad, ask Wikipedia for related titles and pick
        # the first non-saturated summary endpoint. Keeps learning moving
        # without fabricating URLs.
        for title in cls._wikipedia_search_titles(concept):
            url = cls._candidate_to_url(title)
            if url and not is_blocked(url):
                return url

        # (iii) canonical encyclopedic endpoint — only if not saturated
        slug = concept.replace(" ", "_")
        if slug:
            url = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
                   + quote(slug))
            if not is_blocked(url):
                return url
        return None

    @staticmethod
    def _html_to_text(raw: str) -> str:
        """Raw page → readable text. The communion layer deliberately
        returns the unmodified body; consumers that learn from prose must
        strip markup themselves (the research faculty uses JSON APIs, which
        is why it never hit this). Stdlib only. Never raises."""
        import html as _html
        t = raw
        t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
        t = re.sub(r"(?s)<!--.*?-->", " ", t)
        t = re.sub(r"(?s)<[^>]+>", " ", t)
        t = _html.unescape(t)
        return " ".join(t.split())

    def fetch(self, url: str) -> dict | None:
        """Returns {'text', 'stale', 'url'} or None. Never raises."""
        if not url or not str(url).startswith(("http://", "https://")):
            return None
        try:
            from aureon_fusion import api_communion
            body = api_communion.get_text(url, ttl_s=3600.0, timeout=15.0)
        except Exception as exc:
            _blog("fetch_error", url=url[:120], error=type(exc).__name__)
            return None
        stale = False
        text = None
        if isinstance(body, str):
            text = body
        elif isinstance(body, dict):
            # Fail-closed marker from the communion layer: a stale body is
            # usable for display/learning but its confidence is degraded.
            stale = bool(body.get("stale"))
            inner = body.get("body")
            text = inner if isinstance(inner, str) else json.dumps(
                body, ensure_ascii=False)
        if not text or not text.strip():
            return None
        # A raw HTML page would feed markup to the discernment pipeline,
        # whose sentence splitter turns tags into fake "sentences" that
        # near-duplicate each other — every fetch then reads as junk and
        # the will starves ("all near-duplicates or empty") while she is
        # genuinely trying to learn. Serve prose to the learner.
        head = text[:4096].lower()
        if "<html" in head or "<!doctype" in head or "<body" in head:
            cleaned = self._html_to_text(text)
            if len(cleaned.strip()) >= 200:
                text = cleaned
        return {"text": text, "stale": stale, "url": url}


# ───────────────────────── (D) Discernment ─────────────────────────────────

class Discernment:
    """NATIVE reasoning only — extractive sentence selection, then four
    passes per candidate: novelty, contradiction, corroboration,
    coherence-fit. No external LLM calls, ever."""

    MAX_CANDIDATES = 8

    def __init__(self):
        self._kd = _get_knowledge_dataset()
        self._web = _get_memory_web()
        self._net = _get_mycelium()

    # ── extractive selection ──
    def _sentences(self, text: str) -> list:
        parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
        out = []
        for p in parts:
            p = p.strip()
            if 40 <= len(p) <= 600:
                out.append(p)
        return out[:50]

    def _extractive(self, sentences: list, intent: dict) -> list:
        """Score sentences by relevance to the intent question plus
        information density (content-token richness). Purely native."""
        q_tokens = set(_content_tokens(intent.get("question", "")))
        # The question is often phrased about her own state ("raise my
        # confidence in the 'ethics' domain"), which token-collides badly
        # with an encyclopedia article. The URL slug is the topic she
        # actually chose to fetch — fold it into the relevance key.
        url = str(intent.get("url") or "")
        slug = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
        q_tokens |= set(_content_tokens(slug.replace("_", " ")))
        scored = []
        for s in sentences:
            toks = set(_content_tokens(s))
            if not toks:
                continue
            relevance = _jaccard(q_tokens, toks)
            density = min(1.0, len(toks) / 12.0)
            score = 0.6 * relevance + 0.4 * density
            scored.append((score, s))
        scored.sort(key=lambda kv: -kv[0])
        # sqrt: encyclopedic text is naturally terse — raw linear density
        # would underserve exactly the kind of knowledge the will seeks.
        picks = [{"text": s, "quality": round(max(0.0, sc) ** 0.5, 4)}
                 for sc, s in scored[: self.MAX_CANDIDATES] if sc > 0.05]
        if picks:
            return picks
        # Starvation fallback: her self-phrased questions can score every
        # sentence below the floor even though SHE chose this article to
        # learn from. Take the most information-dense sentences instead —
        # the four passes (novelty/contradiction/corroboration/coherence)
        # still judge each candidate, so standards are not lowered, only
        # fed. (Owner: "she's trying to learn, let her.")
        return [{"text": s, "quality": round(density ** 0.5, 4)}
                for (_, s), density in zip(scored[: self.MAX_CANDIDATES],
                                          [min(1.0, len(set(_content_tokens(s))) / 12.0)
                                           for _, s in scored[: self.MAX_CANDIDATES]])]

    # ── four passes ──
    def _pass_novelty(self, text: str) -> tuple:
        """Token overlap vs KnowledgeDataset.find_similar (+ MemoryWeb.recall
        as a secondary bank). Near-duplicates are rejected outright."""
        max_sim = 0.0
        try:
            if self._kd is not None:
                sims = self._kd.find_similar(text, n=3)
                q = set(_content_tokens(text))
                for frag in sims or []:
                    max_sim = max(max_sim, _jaccard(
                        q, set(_content_tokens(getattr(frag, "text", "") or ""))))
        except Exception:
            pass
        return (1.0 - min(1.0, max_sim)), max_sim

    def _pass_contradiction(self, text: str) -> tuple:
        """MemoryWeb.recall surfaces conflicting claims. A conflict does NOT
        delete the candidate — it is tagged 'contested' and stored, never
        absorbed as fact."""
        toks = set(_content_tokens(text))
        has_neg = bool(_NEGATION_RE.search(text or ""))
        try:
            if self._web is None:
                return False, None
            for node in self._web.recall(text) or []:
                node_content = getattr(node, "content", "") or ""
                node_toks = set(_content_tokens(node_content))
                if not node_toks:
                    continue
                overlap = len(toks & node_toks) / max(1, min(len(toks), len(node_toks)))
                if overlap < 0.4:
                    continue
                near_dup = _jaccard(toks, node_toks) >= NEAR_DUP_THRESHOLD
                node_neg = bool(_NEGATION_RE.search(node_content))
                if not near_dup and has_neg != node_neg:
                    return True, getattr(node, "id", None)
        except Exception:
            pass
        return False, None

    def _pass_corroboration(self, text: str, contested: bool) -> bool:
        """≥1 internal echo (dataset similarity in the moderate band, or a
        memory hit) boosts confidence. A contested candidate is not
        corroborated by the very memory that contests it."""
        toks = set(_content_tokens(text))
        try:
            if self._kd is not None:
                for frag in self._kd.find_similar(text, n=3) or []:
                    sim = _jaccard(toks, set(
                        _content_tokens(getattr(frag, "text", "") or "")))
                    if 0.25 <= sim < NEAR_DUP_THRESHOLD:
                        return True
        except Exception:
            pass
        try:
            if self._web is not None and not contested:
                for node in self._web.recall(text) or []:
                    if _jaccard(toks, set(_content_tokens(
                            getattr(node, "content", "") or ""))) >= 0.25:
                        return True
        except Exception:
            pass
        return False

    def _pass_coherence_fit(self, text: str, intent: dict) -> tuple:
        """Which mycelium domain this feeds + that domain's current
        confidence. Feeding an under-confident domain is higher-fit."""
        domain = _CuriosityDomain().domain_for(text, intent.get("domain"))
        confidence = 0.5
        try:
            if self._net is not None:
                confidence = float(self._net.get_domain_confidence(domain))
        except Exception:
            pass
        fit = (1.0 - confidence) if confidence < 0.6 else 0.5
        return domain, round(fit, 4), round(confidence, 4)

    def distill(self, text: str, intent: dict) -> list:
        """text + intent → list of judged candidates. Each candidate:
        {text, quality, novelty, max_similarity, contested, conflict_with,
         corroborated, domain, domain_confidence, coherence_fit, score}."""
        sentences = self._extractive(self._sentences(text), intent)
        out = []
        for cand in sentences:
            t = cand["text"]
            novelty, max_sim = self._pass_novelty(t)
            if max_sim >= NEAR_DUP_THRESHOLD:
                cand["verdict"] = "near_dup_rejected"
                cand["max_similarity"] = round(max_sim, 4)
                out.append(cand)
                continue
            contested, conflict_with = self._pass_contradiction(t)
            corroborated = self._pass_corroboration(t, contested)
            domain, fit, dom_conf = self._pass_coherence_fit(t, intent)
            # Sovereign novelty carries the most weight: the will seeks what
            # it does NOT already know — internal corroboration is a bonus,
            # never a requirement (genuinely new knowledge has no echo yet).
            score = (0.25 * cand["quality"]
                     + 0.35 * novelty
                     + 0.20 * fit
                     + (0.20 if corroborated else 0.0))
            score = max(0.0, min(1.0, score))
            cand.update({
                "novelty": round(novelty, 4),
                "max_similarity": round(max_sim, 4),
                "contested": contested,
                "conflict_with": conflict_with,
                "corroborated": corroborated,
                "domain": domain,
                "domain_confidence": dom_conf,
                "coherence_fit": fit,
                "score": round(score, 4),
                "verdict": "contested" if contested else
                           ("absorb" if score >= ABSORB_THRESHOLD else "drop"),
            })
            out.append(cand)
        return out


class _CuriosityDomain:
    """Thin delegate so Discernment and CuriosityEngine share domain hints."""
    _engine = None

    def domain_for(self, text, fallback):
        if _CuriosityDomain._engine is None:
            _CuriosityDomain._engine = CuriosityEngine()
        return _CuriosityDomain._engine._domain_for_text(text or "", fallback)


# ───────────────────────── (E) Absorb + (F) Receipt ────────────────────────

class Absorber:
    """Writes absorbed candidates into the knowledge banks, feeds the
    mycelium evidence web, ACTIVATES the dormant MindAugment.learn (wrapped
    so its failure never breaks the cycle), and signs a provenance receipt
    for each absorbed batch."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def absorb_batch(self, candidates: list, intent: dict,
                     fetch_info: dict, gamma: float) -> dict:
        absorbed, stored_contested, dropped = [], [], []
        if not self.dry_run:
            self._kd = _get_knowledge_dataset()
            self._web = _get_memory_web()
            self._net = _get_mycelium()
        url = (fetch_info or {}).get("url", "")
        stale = bool((fetch_info or {}).get("stale"))
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for cand in candidates:
            verdict = cand.get("verdict")
            if verdict == "near_dup_rejected":
                dropped.append(cand)
                continue
            score = float(cand.get("score", 0.0))
            if stale:  # stale fetch degrades confidence, never crashes
                score = max(0.0, score - SeekAct.STALE_PENALTY)
                cand["score"] = round(score, 4)
            if cand.get("contested"):
                stored_contested.append(cand)
                if not self.dry_run:
                    self._persist(cand, intent, url, today, as_fact=False)
                continue
            if verdict == "absorb" and score >= ABSORB_THRESHOLD:
                absorbed.append(cand)
                if not self.dry_run:
                    self._persist(cand, intent, url, today, as_fact=True)
            else:
                dropped.append(cand)

        any_absorbed = len(absorbed) > 0
        if not self.dry_run:
            self._feed_mycelium(absorbed + stored_contested)
            self._awaken_mind_augment(gamma, any_absorbed)
        receipt = self._sign_receipt(intent, absorbed, stored_contested,
                                     fetch_info, dry=self.dry_run)
        return {
            "absorbed": len(absorbed),
            "contested_stored": len(stored_contested),
            "dropped": len(dropped),
            "receipt": receipt,
            "any_absorbed": any_absorbed,
            "detail": (f"{len(absorbed)} absorbed, {len(stored_contested)} "
                       f"contested-stored, {len(dropped)} dropped"
                       + (" (stale source — confidence degraded)" if stale else "")),
        }

    def _persist(self, cand: dict, intent: dict, url: str, today: str,
                 as_fact: bool) -> None:
        text = cand["text"]
        tags = ["learned", "aureon_learning_will", f"date:{today}",
                f"score:{cand.get('score', 0):.2f}",
                f"domain:{cand.get('domain', 'unknown')}"]
        if url:
            tags.append(f"source_url:{url}")
        if not as_fact:
            tags.append("contested")
        try:
            if self._kd is not None:
                from types import SimpleNamespace
                pocket = SimpleNamespace(
                    goal_id=f"learning_will:{intent.get('id', '?')}",
                    owner="aureon_fusion.learning_will",
                    entries=[SimpleNamespace(
                        value=text[:1000], tags=tags,
                        phase_angle=0.0, timestamp=time.time())],
                )
                interpretations = None
                if not as_fact:
                    interpretations = {0: SimpleNamespace(
                        data_type="contested_claim", category="other",
                        meaning="contested — stored for provenance, not fact",
                        related_indices=[], interpretation_source="learning_will",
                        confidence=float(cand.get("score", 0.0)),
                        who=[], what="", where=[], when_rel="", why="",
                        how=f"source_url:{url}")}
                self._kd.absorb(pocket, interpretations=interpretations)
                self._kd.save()
        except Exception as exc:
            _blog("absorb_error", bank="knowledge_dataset",
                  error=type(exc).__name__)
        try:
            if self._web is not None:
                self._web.remember(
                    text, node_type="learning",
                    tags=tags[:6],
                    connections=[intent.get("origin", {}).get("node_id")]
                    if isinstance(intent.get("origin"), dict) else None)
                self._web.save()
        except Exception as exc:
            _blog("absorb_error", bank="memory_web", error=type(exc).__name__)

    def _feed_mycelium(self, candidates: list) -> None:
        if self._net is None or not candidates:
            return
        for cand in candidates:
            try:
                domain = cand.get("domain", "memory")
                signal = max(0.05, min(1.0, float(cand.get("score", 0.5))))
                outcome = 1.0 if not cand.get("contested") else 0.0
                self._net.feed_evidence(domain, signal=signal, outcome=outcome)
            except Exception as exc:
                _blog("absorb_error", bank="mycelium", error=type(exc).__name__)
        _save_mycelium_throttled(self._net)  # best-effort persistence

    def _awaken_mind_augment(self, gamma: float, any_absorbed: bool) -> None:
        """ACTIVATE the dormant MindAugment.learn — zero callers until now.
        Wrapped: an augment failure must never break the learning cycle."""
        try:
            augment = _get_mind_augment()
            if augment is None:
                return
            try:
                available = bool(getattr(augment, "available", True))
            except Exception:
                available = True
            if not available:
                return
            augment.learn(float(gamma), "EXECUTE" if any_absorbed else "HOLD")
            _blog("mind_augment_learn", action="EXECUTE" if any_absorbed else "HOLD",
                  gamma=round(float(gamma), 4))
            _save_mycelium_throttled(augment)  # best-effort persistence
        except Exception as exc:
            _blog("mind_augment_error", error=type(exc).__name__)

    def _sign_receipt(self, intent: dict, absorbed: list,
                      contested: list, fetch_info: dict, dry: bool) -> str | None:
        """Sign each absorbed batch via aureon_fusion.receipts. Signing env
        off (or plumbing unavailable) → skip gracefully: provenance simply
        records receipt=None rather than failing the cycle."""
        if not absorbed and not contested:
            return None
        enabled = os.environ.get(SIGNING_ENABLED_ENV, "").strip().lower() \
            in {"1", "true", "yes", "on"}
        if not enabled or dry:
            return None
        try:
            from aureon_fusion import receipts
            payload = {
                "intent_id": intent.get("id"),
                "kind": intent.get("kind"),
                "domain": intent.get("domain"),
                "source_url": (fetch_info or {}).get("url", ""),
                "absorbed": [{"text": c["text"][:160],
                              "score": c.get("score"),
                              "domain": c.get("domain")} for c in absorbed],
                "contested": len(contested),
                "absorbed_at": _utc_now(),
            }
            event = receipts.sign_event(
                "learning_will", "learning.absorbed", payload)
            receipt = (event.get("receipt") or {})
            return receipt.get("receipt_hash") or None
        except Exception as exc:
            _blog("receipt_error", error=type(exc).__name__)
            return None


# ───────────────────────── (G) LearningWill — the contract ─────────────────

class LearningWill:
    """The sovereign learning will. Fixed public contract:

        consider_once(dry_run=False) -> {'intent', 'gate', 'outcome',
                                         'receipt', 'detail'}
        propose() -> dict | None
        status() -> dict

    outcome ∈ absorbed | refused | deferred | no_intent | held_incoherent | vetoed
    """

    def propose(self) -> dict | None:
        return CuriosityEngine().propose()

    def consider_once(self, dry_run: bool = False) -> dict:
        result = {"intent": None, "gate": None, "receipt": None,
                  "outcome": None, "detail": ""}
        record = {"ts": _utc_now(), "dry_run": bool(dry_run)}

        intent = self.propose()
        if intent is None:
            result.update(outcome="no_intent",
                          detail="silence is valid — nothing is genuinely "
                                 "sought, so nothing is learned")
            record.update(result)
            _journal(record)
            _blog("consider", outcome="no_intent", dry_run=dry_run)
            return result
        result["intent"] = intent
        record["intent"] = intent

        gate = LearningGate().check(intent)
        result["gate"] = {k: v for k, v in gate.items() if k != "conditions"}
        record["gate"] = result["gate"]
        if gate.get("conditions"):
            record["gate_conditions"] = gate["conditions"]
        if not gate.get("passed"):
            result["outcome"] = gate["outcome"]
            result["detail"] = gate.get("detail", "gate failure")
            record.update(outcome=result["outcome"], detail=result["detail"])
            if result["outcome"] == "vetoed":
                # Conscience has spoken definitively — never re-ask.
                _record_veto(intent)
            _journal(record)
            _blog("consider", outcome=result["outcome"], dry_run=dry_run,
                  intent_id=intent.get("id"))
            return result

        # Gates passed. The organism now chooses to seek.
        if dry_run:
            fetch_info = {"url": intent.get("url") or "dry-run:stub",
                          "stale": False, "stubbed": True,
                          "text": f"[dry-run stub seek for: "
                                  f"{intent.get('question', '')}]"}
        else:
            url = intent.get("url")
            resolved = False
            if not url:
                # Sovereign canonical resolution: the gates have passed and
                # the organism chooses to seek. When no internal tag carries
                # a target, the will derives its OWN destination from the
                # desire's key concept (canonical encyclopedic endpoint) —
                # organism-initiated, never externally steered. Saturated
                # sources are skipped so a resolved desire never re-fetches
                # ground discernment has already emptied.
                url = SeekAct.resolve_fresh_target(intent, _is_saturated_url)
                resolved = bool(url)
            if not url:
                result.update(outcome="refused",
                              detail="the desire has no organism-chosen "
                                     "target URL in internal state — there "
                                     "is nothing to fetch")
                record.update(outcome="refused", detail=result["detail"])
                _journal(record)
                _blog("consider", outcome="refused", dry_run=dry_run,
                      intent_id=intent.get("id"))
                return result
            if resolved:
                intent["url"] = url
                intent["url_resolved"] = "canonical"
                record["intent"] = intent
            fetched = SeekAct().fetch(url)
            if fetched is None:
                result.update(outcome="refused",
                              detail="seek returned nothing usable — the "
                                     "organism does not fabricate to fill "
                                     "the gap")
                record.update(outcome="refused", detail=result["detail"])
                _journal(record)
                _blog("consider", outcome="refused", dry_run=dry_run,
                      intent_id=intent.get("id"))
                return result
            fetch_info = fetched
            # W8: the gates passed and a real seek completed — offer the
            # intent to the research faculty (organism-initiated, throttled,
            # fail-closed: its absence or failure never breaks this cycle).
            _trigger_research_faculty(intent)

        discernment = Discernment()
        text = fetch_info.get("text", "")
        candidates = discernment.distill(text, intent) if text else []
        judged = [c for c in candidates if c.get("verdict") != "near_dup_rejected"]
        if not judged:
            result.update(outcome="refused",
                          detail=_NEAR_DUP_REFUSAL_DETAIL)
            record.update(outcome="refused", detail=result["detail"],
                          candidates=candidates[:8])
            _journal(record)
            _blog("consider", outcome="refused", dry_run=dry_run,
                  intent_id=intent.get("id"))
            return result

        gamma = (result["gate"].get("coherence") or {}).get("gamma") or 0.0
        batch = Absorber(dry_run=dry_run).absorb_batch(
            candidates, intent, fetch_info, gamma)
        result["receipt"] = batch["receipt"]
        if batch["any_absorbed"]:
            result["outcome"] = "absorbed"
        elif batch["contested_stored"]:
            result["outcome"] = "refused"
            batch["detail"] += (" — only contested claims found; stored "
                                "tagged, none absorbed as fact")
        else:
            result["outcome"] = "refused"
        result["detail"] = batch["detail"]
        record.update(outcome=result["outcome"], detail=result["detail"],
                      receipt=result["receipt"],
                      batch={k: batch[k] for k in
                             ("absorbed", "contested_stored", "dropped")},
                      candidates=judged[:8])
        _journal(record)
        _blog("consider", outcome=result["outcome"], dry_run=dry_run,
              intent_id=intent.get("id"), absorbed=batch["absorbed"],
              contested=batch["contested_stored"])
        try:
            from . import events
            events.publish_event(
                "learning_will", "learning_will.cycle",
                {"outcome": result["outcome"], "intent_kind": intent.get("kind"),
                 "domain": intent.get("domain"),
                 "absorbed": batch["absorbed"],
                 "receipt": bool(result["receipt"])},
                priority=5 if result["outcome"] == "absorbed" else 4)
        except Exception:
            pass
        return result

    def status(self) -> dict:
        gamma, gamma_status = _read_coherence_gamma()
        entries = _journal_entries(limit=200)
        outcomes = {}
        for e in entries:
            o = e.get("outcome")
            if o:
                outcomes[o] = outcomes.get(o, 0) + 1
        matrix = _read_json(SERO_AUTONOMOUS / "capability_matrix.json", {})
        gates = matrix.get("gates", {}) if isinstance(matrix, dict) else {}
        auth_row = gates.get(AUTH_GATE) if isinstance(gates, dict) else None
        open_intent = _read_json(INTENTS_FILE, {}).get("open_intent")
        augment = _get_mind_augment()
        return {
            "organ": "learning_will",
            "doctrine": {
                "free_will": True,
                "gates_fail_closed": ["conscience", "hnc_coherence", "authorization"],
                "coherence_threshold": COHERENCE_THRESHOLD,
                "absorb_threshold": ABSORB_THRESHOLD,
                "no_push_scheduling": True,
                "native_reasoning_only": True,
                "silence_is_valid": True,
            },
            "coherence": {"gamma": gamma, "status": gamma_status,
                          "file": str(HNC_STATE_FILE)},
            "authorization": {
                "gate": AUTH_GATE,
                "matrix_row_present": auth_row is not None,
                "matrix_status": (auth_row or {}).get("status", "missing"),
            },
            "open_intent": open_intent,
            "journal": {
                "file": str(JOURNAL_FILE),
                "recent_entries": len(entries),
                "outcome_counts": outcomes,
                "last_outcome": entries[-1].get("outcome") if entries else None,
                "last_ts": entries[-1].get("ts") if entries else None,
            },
            "organs": {
                "knowledge_dataset": _get_knowledge_dataset() is not None,
                "memory_web": _get_memory_web() is not None,
                "mycelium": _get_mycelium() is not None,
                "mind_augment": bool(getattr(augment, "available", False))
                if augment is not None else False,
            },
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
        print("usage: python -m aureon_fusion.learning_will "
              "status|propose|consider [--dry]")
        print("  status    doctrine, coherence, gates, journal, organs")
        print("  propose   the current strongest learning desire (or silence)")
        print("  consider  run one learning cycle; --dry stubs fetch/absorb")
        print("            (no network, no bank writes; gates still real)")
        return 0
    verb = argv[0]
    will = LearningWill()
    if verb == "status":
        _print_json(will.status())
        return 0
    if verb == "propose":
        intent = will.propose()
        if intent is None:
            print(json.dumps({"intent": None,
                              "detail": "silence is valid — nothing sought"},
                             ensure_ascii=False))
            return 0
        _print_json(intent)
        return 0
    if verb == "consider":
        dry = "--dry" in argv[1:]
        result = will.consider_once(dry_run=dry)
        _print_json(result)
        return 0 if result.get("outcome") in OUTCOMES else 1
    print(f"unknown verb: {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
