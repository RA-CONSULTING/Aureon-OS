"""🎓 RESEARCH FACULTY — the Queen's self-research loop, wired and gated.

W7/W8 of the queen build plan: the upstream SelfResearchLoop spent 722
cycles emitting zeros because its WorldDataIngester was never injected
(ingester=None short-circuit). This faculty constructs the READ-ONLY
upstream loop (aureon-os-upstream/aureon/queen/self_research_loop.py,
imported under the suppression env vars) with:

  knowledge_dataset = fusion adapter over
      aureon_fusion/state/queen_mind/knowledge_dataset.json
      (fresh upstream KnowledgeDataset per run — the same disk-fresh
      pattern queen_mind uses each cycle, so concurrent writers are
      re-read, never clobbered)
  world_data_ingester = aureon_fusion.research_ingester.ResearchIngester
      (communion-routed; every fetch inherits cache / rate-limit /
      backoff / circuit-breaker from api_communion)
  stash_pockets       = fusion adapter whose close_pocket() crystallizes
      every dumped item into knowledge_dataset fragments:
      data_type "research", provenance tags source + url + fetched_at.

INTERNAL GATE (organism-initiated doctrine) — try_research checks the
fail-closed trio BEFORE any fetch happens:
  1. conscience_hook.evaluate          — VETO absolute
  2. coherence_gamma ≥ 0.25            — below, the organism WAITS
     (state/hnc_core_state.json; missing/corrupt = fail-closed hold)
  3. capability_gate.check(
       'network_access:fetch_public_data') — authorization required
Plus a throttle (aureon_fusion/state/research_throttle.json): max 1 run
/ 10 min. The loop object is NEVER start()ed — no background thread, no
push scheduling; the organism runs a cycle when it chooses to.

FAIL-CLOSED: no exception in this module may ever reach (or kill) the
queen's cycle — every public entry wraps, degrades, and returns an
honest {'outcome': 'held_*' | 'error_fail_closed'} dict.

CLI:
  python -m aureon_fusion.research_faculty once    # gated single run,
                                                   # prints JSON result
  python -m aureon_fusion.research_faculty status  # per-mode throttle +
                                                   # last result + gate snapshot
  python -m aureon_fusion.research_faculty questions  # research the dataset's
                                                   # unanswered questions, or
                                                   # selfq-harvested topics
  python -m aureon_fusion.research_faculty topic "solar wind"  # gated
                                                   # multi-source corroboration
                                                   # pull on one topic

R2/R6 — mode anatomy (shared by questions/topic): gate trio → per-mode
throttle (proactive/topic/questions/actuator each 1/10 min, own budget in
research_throttle.json "modes") → multi-source corroboration pull (wiki
opensearch+summary / arXiv / DDG instant answer / HN search, blended,
deduped by url, corroboration_count per item) → learning_will Discernment
novelty filter BEFORE crystallization (guarded import; local Jaccard ≥0.7
fallback if unusable) → TRUTH GATE layer (aureon_fusion.truth_gate over
the pure upstream QGITA/Kundalini gate; guarded import — when the gate is
unavailable the run degrades honestly: fragments tagged 'truth_unchecked',
journal/blog note 'truth_gate_unavailable', research continues) →
existing stash-pocket crystallization with provenance tags (source / url /
fetched_at / corroboration_count, plus 'corroborated' when ≥2 independent
sources saw the item). Gate-ready items additionally carry 'truth:aris';
contested items NEVER crystallize — they are appended to the append-only
state/truth_contested.jsonl ledger (stored tagged, never absorbed — same
doctrine as learning_will contested material). The truth layer is
ADDITIONAL discernment, not a replacement: _record_outcomes still passes
corroborated counts as before.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import types
from pathlib import Path
from typing import Any, Dict, List, Optional

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

from .paths import FUSION_STATE, AUREON_UPSTREAM, WORKSPACE
from . import events

ORGAN_NAME = "research_faculty"

# ── gates (identical thresholds/idioms to learning_will) ────────────────────
GAMMA_THRESHOLD = 0.25
AUTH_GATE = "network_access:fetch_public_data"
HNC_STATE_FILE = FUSION_STATE / "hnc_core_state.json"
THROTTLE_FILE = FUSION_STATE / "research_throttle.json"
THROTTLE_S = 600.0                      # max 1 research run / 10 min PER MODE
THROTTLE_MODES = ("proactive", "topic", "questions", "actuator")
MIND_DIR = FUSION_STATE / "queen_mind"
KNOWLEDGE_DATASET_PATH = MIND_DIR / "knowledge_dataset.json"
# Truth-gate contested-material ledger: append-only; stored tagged, NEVER
# absorbed into the dataset (same doctrine as learning_will).
TRUTH_CONTESTED_FILE = FUSION_STATE / "truth_contested.jsonl"

# Self-questioning cycles: harvested READ-ONLY as a defensive topic source
# when the dataset holds no unanswered questions (same roots + glob the
# door_activators selfq feed scans; we re-read, we never write there).
SELFQ_CYCLES_GLOB = "self_questioning_ai_cycles*.jsonl"
SELFQ_CYCLES_ROOTS = (
    WORKSPACE / "state",
    FUSION_STATE,
    AUREON_UPSTREAM / "state",
)

ACTION_DESC = (
    "Queen research faculty: organism-initiated pull of keyless public "
    "data (HN/Reddit/Wikipedia/markets/quakes/weather/arXiv) through "
    "api_communion, crystallized into knowledge_dataset fragments."
)

_upstream_fac = None  # lazy import cache


# ─────────────────────────────────────────────────────────────────────────────
# Upstream faculty import (read-only repo, suppression env vars)
# ─────────────────────────────────────────────────────────────────────────────


def _load_upstream():
    """Import the two upstream queen modules exactly once, under the
    suppression guards. Idempotent; imports only — no construction."""
    global _upstream_fac
    if _upstream_fac is not None:
        return _upstream_fac
    root = str(AUREON_UPSTREAM)
    if root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)  # pin the upstream repo root for these imports

    import importlib

    # aureon._path_setup walks the package tree onto sys.path so upstream
    # bare imports resolve exactly as they do inside the repo.
    import aureon._path_setup  # noqa: F401

    modules = {
        name: importlib.import_module(dotted)
        for name, dotted in (
            ("self_research_loop", "aureon.queen.self_research_loop"),
            ("knowledge_dataset", "aureon.queen.knowledge_dataset"),
        )
    }
    _upstream_fac = types.SimpleNamespace(**modules)
    try:
        events.publish_event(
            ORGAN_NAME, "research_faculty.faculty_loaded",
            {"modules": sorted(modules)}, priority=4)
    except Exception:
        pass
    return _upstream_fac


# ─────────────────────────────────────────────────────────────────────────────
# Fusion knowledge-dataset adapter (reads/writes queen_mind's dataset file)
# ─────────────────────────────────────────────────────────────────────────────


class FusionKnowledgeDatasetAdapter:
    """Defensive read/write adapter over the fusion knowledge dataset.

    A FRESH upstream KnowledgeDataset is constructed per operation from
    KNOWLEDGE_DATASET_PATH — the same disk-fresh pattern queen_mind uses
    before each absorb, so fragments written by other organs between runs
    are seen and never clobbered."""

    def __init__(self, path: Path = KNOWLEDGE_DATASET_PATH):
        self.path = Path(path)

    def _fresh(self):
        fac = _load_upstream()
        ds = fac.knowledge_dataset.KnowledgeDataset(path=str(self.path))
        return ds

    def find_by_data_type(self, data_type: str, n: int = 10) -> List[Any]:
        """Question discovery hook the upstream research loop calls."""
        try:
            ds = self._fresh()
            found = ds.find_by_data_type(str(data_type), n=max(1, int(n)))
            return list(found or [])
        except Exception:
            return []

    def absorb_pocket(self, pocket: Any) -> int:
        """Crystallize a stash pocket into 'research' fragments.

        Every entry becomes a KnowledgeFragment with data_type 'research'
        and provenance tags (source / url / fetched_at) recovered from the
        ingester where the pocket dump came from a ResearchItem. Returns
        the number of fragments added (0 on any failure — never raises)."""
        try:
            entries = list(getattr(pocket, "entries", []) or [])
            if not entries:
                return 0
            interpretations: Dict[int, Any] = {}
            for i, entry in enumerate(entries):
                tags = [str(t) for t in (getattr(entry, "tags", []) or [])]
                category = "knowledge"
                for cand in ("market", "temporal", "user_input"):
                    if cand in tags:
                        category = "world" if cand == "user_input" else cand
                        break
                interpretations[i] = types.SimpleNamespace(
                    data_type="research",
                    category=category,
                    meaning=_s(getattr(entry, "value", ""), 240),
                    related_indices=[],
                    interpretation_source="raw",
                    confidence=0.0,
                    who=[], what="", where=[], when_rel="", why="", how="",
                )
            ds = self._fresh()
            return int(ds.absorb(pocket, interpretations=interpretations) or 0)
        except Exception:
            return 0


def _s(value: Any, limit: int = 0) -> str:
    try:
        out = " ".join(str(value or "").split())
        return out[:limit] if limit > 0 else out
    except Exception:
        return ""


def _iso(ts: float) -> str:
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(ts)))
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Fusion stash-pocket adapter (crystallize into the dataset, no upstream vault)
# ─────────────────────────────────────────────────────────────────────────────


class _ResearchPocket:
    """Minimal pocket satisfying the upstream loop's dump contract."""

    def __init__(self, goal_id: str, owner: str, ingester: Any = None):
        self.goal_id = goal_id
        self.owner = owner
        self.pocket_id = goal_id
        self.entries: List[Any] = []
        self._ingester = ingester

    def dump(self, key: str, value: Any, tags: Optional[List[str]] = None) -> None:
        try:
            tags_out = [str(t) for t in (tags or []) if str(t or "").strip()]
            text = _s(value, 2000)
            # Provenance recovery: the loop dumps f"{item.title}: {item.text}"
            # — recover the full ResearchItem to tag url + fetched_at.
            item = None
            if self._ingester is not None:
                try:
                    item = self._ingester.provenance_for(text)
                except Exception:
                    item = None
            if item is not None:
                for extra in ("research",
                              f"url:{item.url}",
                              f"fetched_at:{_iso(item.fetched_at)}"):
                    if extra not in tags_out:
                        tags_out.append(extra)
            self.entries.append(types.SimpleNamespace(
                value=text,
                tags=tags_out,
                phase_angle=0.0,
            ))
        except Exception:
            pass


class ResearchStashPockets:
    """open_pocket/close_pocket surface the upstream loop expects.

    close_pocket crystallizes the pocket into knowledge_dataset fragments
    and returns {"fragments_crystallized": n} like the upstream flow."""

    def __init__(self, dataset: FusionKnowledgeDatasetAdapter,
                 ingester: Any = None):
        self.dataset = dataset
        self._ingester = ingester

    def open_pocket(self, goal_id: str, owner: str) -> _ResearchPocket:
        return _ResearchPocket(goal_id=goal_id, owner=owner,
                               ingester=self._ingester)

    def close_pocket(self, pocket: Any) -> Dict[str, Any]:
        try:
            added = self.dataset.absorb_pocket(pocket)
            return {"fragments_crystallized": added}
        except Exception:
            return {"fragments_crystallized": 0}


# ─────────────────────────────────────────────────────────────────────────────
# Fail-closed gate trio (same order + semantics as learning_will)
# ─────────────────────────────────────────────────────────────────────────────


def _gate_conscience() -> Dict[str, Any]:
    try:
        from . import conscience_hook
        verdict = conscience_hook.evaluate(
            ACTION_DESC, {"organ": ORGAN_NAME})
    except Exception as exc:
        # FAIL-CLOSED: a conscience that cannot answer is a conscience
        # that said no.
        return {"passed": False, "verdict": "VETO", "fail_closed": True,
                "detail": f"conscience evaluation failed "
                          f"({type(exc).__name__}) — fail-closed hold"}
    if (verdict or {}).get("verdict") == "VETO":
        return {"passed": False, "verdict": "VETO",
                "detail": _s((verdict or {}).get("reasoning"), 220)}
    return {"passed": True, "verdict": (verdict or {}).get("verdict"),
            "detail": _s((verdict or {}).get("reasoning"), 220)}


def _gate_gamma() -> Dict[str, Any]:
    """(gamma gate) — status ∈ ok | low | missing | corrupt. Fail-closed:
    anything unreadable is a HOLD; below threshold the organism WAITS."""
    try:
        if not HNC_STATE_FILE.exists():
            return {"passed": False, "gamma": None, "status": "missing",
                    "detail": "hnc_core_state.json missing — "
                              "coherence unknown; held"}
        data = json.loads(HNC_STATE_FILE.read_text(encoding="utf-8"))
        gamma = float(data.get("coherence_gamma"))
        if gamma != gamma:  # NaN guard
            return {"passed": False, "gamma": None, "status": "corrupt",
                    "detail": "coherence_gamma unreadable — held"}
        if gamma < GAMMA_THRESHOLD:
            return {"passed": False, "gamma": gamma, "status": "low",
                    "detail": f"coherence_gamma {gamma:.3f} < "
                              f"{GAMMA_THRESHOLD} — the organism waits"}
        return {"passed": True, "gamma": gamma, "status": "ok"}
    except Exception:
        return {"passed": False, "gamma": None, "status": "corrupt",
                "detail": "hnc_core_state.json unreadable/corrupt — held"}


def _gate_capability() -> Dict[str, Any]:
    try:
        from . import capability_gate
        verdict = capability_gate.check(AUTH_GATE)
    except Exception as exc:
        return {"passed": False, "verdict": "HOLD", "fail_closed": True,
                "detail": f"capability gate error ({type(exc).__name__}) "
                          f"— deferred"}
    allowed = bool((verdict or {}).get("allowed"))
    return {"passed": allowed,
            "verdict": (verdict or {}).get("verdict"),
            "detail": _s((verdict or {}).get("reason"), 220)}


def _run_gate_trio() -> Dict[str, Any]:
    """All three gates; short-circuits on the first failure. NEVER raises."""
    conscience = _gate_conscience()
    if not conscience.get("passed"):
        return {"passed": False, "failed": "conscience",
                "outcome": "vetoed", "conscience": conscience}
    gamma = _gate_gamma()
    if not gamma.get("passed"):
        return {"passed": False, "failed": "gamma",
                "outcome": "held_incoherent", "gamma": gamma}
    capability = _gate_capability()
    if not capability.get("passed"):
        return {"passed": False, "failed": "capability",
                "outcome": "held_unauthorized", "capability": capability}
    return {"passed": True, "conscience": conscience, "gamma": gamma,
            "capability": capability}


# ─────────────────────────────────────────────────────────────────────────────
# Throttle (max 1 run / 10 min) — honest state, atomic writes
# ─────────────────────────────────────────────────────────────────────────────


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _write_json_atomic(path: Path, payload: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _throttle_check(now: float, mode: str = "proactive") -> Dict[str, Any]:
    """Per-mode throttle: each mode owns a 1/10 min budget, so a topic pull
    never starves the proactive cycle or vice versa. The legacy top-level
    last_run_at is honored as the proactive mode's prior stamp."""
    mode = mode if mode in THROTTLE_MODES else "proactive"
    data = _read_json(THROTTLE_FILE, {})
    last = 0.0
    try:
        modes = data.get("modes") if isinstance(data.get("modes"), dict) \
            else {}
        entry = modes.get(mode) if isinstance(modes.get(mode), dict) else {}
        raw = entry.get("last_run_at")
        if raw is None and mode == "proactive":
            raw = data.get("last_run_at")   # legacy file, pre-mode layout
        last = float(raw or 0.0)
    except (TypeError, ValueError):
        last = 0.0
    remaining = THROTTLE_S - (now - last)
    if last > 0 and remaining > 0:
        return {"allowed": False, "retry_in_s": round(remaining, 1),
                "last_run_at": last, "mode": mode}
    return {"allowed": True, "retry_in_s": 0.0, "last_run_at": last,
            "mode": mode}


def _throttle_record(now: float, mode: str,
                     result: Dict[str, Any]) -> None:
    """Record a run under its own mode key (atomic write). The top-level
    last_run_at/last_result mirror stays the proactive mode's, so older
    status readers keep working."""
    try:
        mode = mode if mode in THROTTLE_MODES else "proactive"
        data = _read_json(THROTTLE_FILE, {})
        modes = data.get("modes") if isinstance(data.get("modes"), dict) \
            else {}
        modes[mode] = {"last_run_at": now, "last_result": result}
        payload = {
            "saved_by": ORGAN_NAME,
            "modes": modes,
        }
        proactive = modes.get("proactive") or {}
        if proactive.get("last_run_at"):
            payload["last_run_at"] = proactive["last_run_at"]
            payload["last_result"] = proactive.get("last_result")
        _write_json_atomic(THROTTLE_FILE, payload)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# The gated research run
# ─────────────────────────────────────────────────────────────────────────────


def _build_loop(max_items: int):
    """Construct the upstream SelfResearchLoop fully injected. The loop is
    never start()ed — no thread, no push scheduling."""
    from . import research_ingester

    fac = _load_upstream()
    ingester = research_ingester.ResearchIngester()
    dataset = FusionKnowledgeDatasetAdapter()
    pockets = ResearchStashPockets(dataset, ingester=ingester)
    loop = fac.self_research_loop.SelfResearchLoop(
        knowledge_dataset=dataset,
        world_data_ingester=ingester,
        stash_pockets=pockets,
        thought_bus=None,
        interval_s=THROTTLE_S,
        max_questions_per_cycle=max(1, int(max_items)),
    )
    return loop, ingester


def _run_gated(intent: Dict[str, Any], max_items: int) -> Dict[str, Any]:
    """Gate trio → per-mode throttle → one research cycle. All failures are honest
    'held_*' dicts; a gate exception degrades, never propagates.

    The throttle mode follows the intent: an explicit 'mode' wins, a
    topic/question pull runs on the 'topic' budget, a bare cycle on
    'proactive' — so no consumer starves another (per-mode doctrine)."""
    now = time.time()

    gates = _run_gate_trio()
    if not gates.get("passed"):
        result = {
            "outcome": gates.get("outcome", "held"),
            "gate": gates.get("failed"),
            "detail": _s((gates.get(gates.get("failed") or "") or {})
                         .get("detail"), 240),
            "questions_processed": 0, "items_pulled": 0,
            "fragments_added": 0,
        }
        try:
            events.publish_event(
                ORGAN_NAME, "research_faculty.held",
                {"outcome": result["outcome"], "gate": result["gate"]},
                priority=6)
        except Exception:
            pass
        return result

    topic = _s((intent or {}).get("topic") or (intent or {}).get("question"))
    mode = _s((intent or {}).get("mode")) or ("topic" if topic else "proactive")
    mode = mode if mode in THROTTLE_MODES else "proactive"

    throttle = _throttle_check(now, mode)
    if not throttle.get("allowed"):
        return {
            "outcome": "throttled",
            "mode": mode,
            "retry_in_s": throttle.get("retry_in_s"),
            "questions_processed": 0, "items_pulled": 0,
            "fragments_added": 0,
        }

    loop, ingester = _build_loop(max_items)
    if topic:
        cycle = _research_topic(loop, topic)
    else:
        cycle = loop.run_one_cycle()
    cycle = dict(cycle or {})

    result = {
        "outcome": "researched",
        "gamma": (gates.get("gamma") or {}).get("gamma"),
        "questions_processed": int(cycle.get("questions_processed") or 0),
        "items_pulled": int(cycle.get("items_pulled") or 0),
        "fragments_added": int(cycle.get("fragments_added") or 0),
        "topic": topic or "",
        "mode": mode,
        "ingester_stats": ingester.get_stats(),
    }
    _throttle_record(now, mode, result)
    _record_outcomes(result)
    try:
        events.publish_event(
            ORGAN_NAME, "research_faculty.researched",
            {"items_pulled": result["items_pulled"],
             "fragments_added": result["fragments_added"],
             "mode": result["mode"]}, priority=5)
    except Exception:
        pass
    return result


def result_questions_exist(loop: Any) -> bool:
    try:
        return bool(loop.find_unanswered_questions(n=1))
    except Exception:
        return False


def _record_outcomes(result: Dict[str, Any]) -> None:
    """Sink a researched result into the queen_knowledge outcomes table and
    the MemoryWeb (R4/R5 wiring). Guarded end-to-end: any failure here must
    never affect the research result itself."""
    try:
        if (result or {}).get("outcome") != "researched":
            return
        from . import knowledge_outcomes as _ko
        topic = (_s(result.get("topic"))
                 or "; ".join(result.get("topics") or [])
                 or f"{result.get('mode', 'research')} pull "
                    f"{(result.get('gamma') or 0):.2f}")
        items = int(result.get("items_pulled") or 0)
        added = int(result.get("fragments_added") or 0)
        corroborated = int(result.get("corroborated_items") or 0)
        summary = (f"mode={result.get('mode')} items={items} "
                   f"added={added} corroborated={corroborated}")
        # derive the honest quality signal the sink expects:
        # stood up to cross-source checking / real miss / no signal
        if added > 0 and corroborated > 0:
            success: bool | None = True
        elif items > 0 and added == 0:
            success = False
        else:
            success = None
        _ko.record_research(topic, summary, items, added, corroborated,
                            success=success)
        # chain the freshest research fragments into the memory web
        try:
            texts = _recent_research_fragments(limit=3)
            if texts:
                _ko.record_research_memory(topic, texts)
        except Exception:
            pass
    except Exception:
        pass


def _recent_research_fragments(limit: int = 3) -> list:
    """Newest research-provenance fragment texts from the knowledge dataset
    (read-only, defensive — used to give the memory web real content)."""
    out: list = []
    try:
        from .paths import FUSION_STATE
        ds_path = FUSION_STATE / "queen_mind" / "knowledge_dataset.json"
        data = json.loads(ds_path.read_text(encoding="utf-8",
                                            errors="replace"))
        frags = data.get("fragments") or data.get("pockets") or []
        if isinstance(frags, dict):
            frags = list(frags.values())
        for frag in reversed(frags):
            if not isinstance(frag, dict):
                continue
            tags = [str(t).lower() for t in (frag.get("tags") or [])]
            dtype = str(frag.get("data_type") or "").lower()
            if "research" in dtype or any("research" in t for t in tags):
                text = _s(frag.get("text") or frag.get("content"), 400)
                if text:
                    out.append(text)
                if len(out) >= limit:
                    break
    except Exception:
        pass
    return out


def _research_topic(loop: Any, topic: str) -> Dict[str, Any]:
    """Targeted research on an intent-supplied topic/question: one
    answer_question pull crystallized through the pocket flow."""
    result = {"questions_processed": 0, "items_pulled": 0,
              "fragments_added": 0}
    try:
        fac = _load_upstream()
        query = fac.self_research_loop.fragment_to_query(topic)
        if not query:
            query = topic
        items = loop.world_data_ingester.answer_question(query,
                                                         n_per_source=2) or []
        if not items:
            return result
        result["items_pulled"] = len(items)
        loop.world_data_ingester.ingest_to_vault(items)
        pocket = None
        if loop.stash_pockets is not None:
            try:
                import time as _t
                pocket = loop.stash_pockets.open_pocket(
                    goal_id=f"research_topic_{int(_t.time())}",
                    owner="research_faculty")
                pocket.dump(key="topic", value=topic,
                            tags=["topic", "research_query"])
                for item in items:
                    pocket.dump(
                        key=item.source,
                        value=f"{item.title}: {item.text}",
                        tags=[item.source, item.category, "external_research"])
                close_result = loop.stash_pockets.close_pocket(pocket)
                result["fragments_added"] += int(
                    (close_result or {}).get("fragments_crystallized") or 0)
            except Exception:
                pass
        result["questions_processed"] = 1
    except Exception:
        pass
    return result


# ─────────────────────────────────────────────────────────────────────────────
# R2 — question/topic-driven modes (corroboration pull + quality-filtered
# absorption). Same gate trio, same pocket crystallization, per-mode budgets.
# ─────────────────────────────────────────────────────────────────────────────


def _held_result(gates: Dict[str, Any], mode: str) -> Dict[str, Any]:
    """Shared honest 'held_*' dict for the new modes (mirrors _run_gated)."""
    result = {
        "outcome": gates.get("outcome", "held"),
        "mode": mode,
        "gate": gates.get("failed"),
        "detail": _s((gates.get(gates.get("failed") or "") or {})
                     .get("detail"), 240),
        "questions_processed": 0, "items_pulled": 0, "fragments_added": 0,
    }
    try:
        events.publish_event(
            ORGAN_NAME, "research_faculty.held",
            {"outcome": result["outcome"], "gate": result["gate"],
             "mode": mode}, priority=6)
    except Exception:
        pass
    return result


def _norm_url(url: Any) -> str:
    try:
        u = str(url or "").strip().lower()
        u = re.sub(r"^https?://", "", u)
        u = re.sub(r"^www\.", "", u)
        return u.rstrip("/")
    except Exception:
        return ""


def _norm_title(title: Any) -> str:
    try:
        toks = re.findall(r"[a-z0-9]+", str(title or "").lower())
        return " ".join(toks)
    except Exception:
        return ""


def _topic_pull(ingester: Any, topic: str,
                sources: Any = ("wiki", "arxiv", "ddg", "hn"),
                cap: int = 6) -> List[Dict[str, Any]]:
    """Multi-source corroboration pull for one topic/question: wiki
    opensearch+summary, arXiv, DuckDuckGo instant answer, HN search —
    blended, merged by url then normalized title, each entry carrying its
    independent-source corroboration_count. NEVER raises; a dead source
    just contributes nothing."""
    out: List[Dict[str, Any]] = []
    try:
        from . import open_sources

        t = _s(topic, 300)
        if not t:
            return out
        requested = [str(s) for s in (sources or ())] or \
            ["wiki", "arxiv", "ddg", "hn"]

        per_source: Dict[str, List[Any]] = {}

        def _collect(name: str, fn) -> None:
            try:
                per_source[name] = list(fn() or [])
            except Exception:
                per_source[name] = []

        def _ddg_items() -> List[Any]:
            ans = open_sources.ddg_instant_answer(t)
            if not ans:
                return []
            from . import research_ingester
            abstract = _s((ans or {}).get("abstract"), 800)
            heading = _s((ans or {}).get("heading")) or t
            url = _s((ans or {}).get("abstract_url"))
            item = research_ingester.ResearchItem(
                source="ddg",
                topic=t,
                title=heading,
                text=abstract or heading,
                url=url,
                summary=f"DDG ({t}): {heading}",
                category="knowledge",
                raw={},
            )
            try:
                ingester._register(item)
            except Exception:
                pass
            return [item]

        for src in requested:
            try:
                if src == "wiki":
                    _collect("wiki",
                             lambda: ingester.search_wikipedia(t, n=2))
                elif src == "arxiv":
                    _collect("arxiv", lambda: ingester.fetch_arxiv(t, n=3))
                elif src == "ddg":
                    _collect("ddg", _ddg_items)
                elif src == "hn":
                    _collect("hn", lambda: ingester.fetch_hn_search(t, n=3))
            except Exception:
                per_source[src] = []

        entries: List[Dict[str, Any]] = []
        url_index: Dict[str, Dict[str, Any]] = {}
        title_index: Dict[str, Dict[str, Any]] = {}
        for name in requested:
            for item in per_source.get(name) or []:
                try:
                    uk = _norm_url(getattr(item, "url", ""))
                    tk = _norm_title(getattr(item, "title", ""))
                    ent = url_index.get(uk) if uk else None
                    if ent is None and tk:
                        ent = title_index.get(tk)
                    if ent is None:
                        ent = {"item": item, "sources": set(),
                               "url_key": uk, "title_key": tk}
                        entries.append(ent)
                        if uk:
                            url_index[uk] = ent
                        if tk:
                            title_index[tk] = ent
                    ent["sources"].add(name)
                except Exception:
                    continue
        for ent in entries:
            try:
                item = ent["item"]
                out.append({
                    "item": item,
                    "sources": sorted(ent["sources"]),
                    "corroboration_count": len(ent["sources"]),
                    "dump_text": _s(
                        f"{getattr(item, 'title', '')}: "
                        f"{getattr(item, 'text', '')}", 2000),
                })
            except Exception:
                continue
        out.sort(key=lambda e: (-e["corroboration_count"],
                                _s(getattr(e["item"], "title", ""))))
        return out[: max(1, int(cap))]
    except Exception:
        return out


def _dataset_fragment_texts() -> List[str]:
    """Texts of the live dataset fragments (local-fallback novelty bank)."""
    try:
        data = _read_json(KNOWLEDGE_DATASET_PATH, {})
        frags = data.get("fragments") if isinstance(data, dict) else []
        return [_s((f or {}).get("text")) for f in (frags or [])
                if isinstance(f, dict) and _s((f or {}).get("text"))]
    except Exception:
        return []


def _local_near_dup(text: str, bank: List[str]) -> bool:
    """Lightweight Jaccard near-duplicate check vs existing fragments —
    the fallback used only when learning_will.Discernment is unusable."""
    try:
        toks = set(w for w in
                   re.findall(r"[a-z0-9]+", str(text or "").lower())
                   if len(w) >= 3)
        if not toks:
            return False
        for frag in bank or []:
            ftoks = set(w for w in
                        re.findall(r"[a-z0-9]+", str(frag or "").lower())
                        if len(w) >= 3)
            if not ftoks:
                continue
            inter = len(toks & ftoks)
            union = len(toks | ftoks)
            if union and inter / union >= 0.7:
                return True
        return False
    except Exception:
        return False


def _novelty_filter(entries: List[Dict[str, Any]]) -> tuple:
    """R6 quality gate BEFORE crystallization: run every candidate through
    the learning_will Discernment novelty pass (guarded import, REAL API:
    _pass_novelty → (novelty, max_similarity), near-dup rejected at
    Jaccard ≥ 0.7 vs the live dataset + memory web). If Discernment is
    unusable externally, degrade to the local Jaccard check vs existing
    dataset fragments. A per-item error keeps the item, counted honestly.

    Returns (kept, rejected_count, engine_name, error_count). NEVER raises."""
    kept: List[Dict[str, Any]] = []
    rejected = 0
    errors = 0
    disc = None
    engine = "local_jaccard_fallback"
    try:
        from .learning_will import Discernment
        disc = Discernment()
        engine = "learning_will.Discernment"
    except Exception:
        disc = None
    if disc is not None:
        for ent in entries or []:
            try:
                _, max_sim = disc._pass_novelty(ent.get("dump_text", ""))
                if float(max_sim or 0.0) >= 0.7:
                    rejected += 1
                    continue
            except Exception:
                errors += 1           # undecidable → keep, counted
            kept.append(ent)
        return kept, rejected, engine, errors
    bank: List[str] = []
    try:
        bank = _dataset_fragment_texts()
    except Exception:
        bank = []
    for ent in entries or []:
        try:
            if _local_near_dup(ent.get("dump_text", ""), bank):
                rejected += 1
                continue
        except Exception:
            errors += 1
        kept.append(ent)
    return kept, rejected, engine, errors


# ─────────────────────────────────────────────────────────────────────────────
# Truth gate layer (between novelty filter and crystallization): gate-ready
# items pass through tagged 'truth:aris'; contested items go to the
# append-only ledger, never into the dataset; gate unavailable → honest
# 'truth_unchecked' degradation, research continues.
# ─────────────────────────────────────────────────────────────────────────────


def _entry_provenance(ent: Dict[str, Any]) -> Dict[str, Any]:
    """Best-effort provenance (source / url / fetched_at) off a pulled
    entry's ResearchItem — exactly what the truth gate needs to build
    grounding receipts. Missing fields stay absent (the gate then returns
    an honest MISSING_GROUNDING, never fabricated). NEVER raises."""
    prov: Dict[str, Any] = {}
    try:
        item = (ent or {}).get("item")
        if item is None:
            return prov
        url = _s(getattr(item, "url", ""))
        if url:
            prov["url"] = url
        src = _s(getattr(item, "source", ""))
        if src:
            prov["source"] = src
        fetched = getattr(item, "fetched_at", None)
        if fetched:
            try:
                prov["fetched_at"] = _iso(float(fetched))
            except Exception:
                pass
    except Exception:
        pass
    return prov


def _append_truth_contested(rec: Dict[str, Any]) -> None:
    """Append-only contested-material ledger. One JSON line per contested
    item; a single small append is effectively atomic. NEVER raises."""
    try:
        TRUTH_CONTESTED_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TRUTH_CONTESTED_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _truth_layer(entries: List[Dict[str, Any]],
                 mode: str) -> tuple:
    """Run novelty-kept entries through the truth gate. Returns
    (kept_entries, info) where kept entries carry 'truth_result' (ready)
    or 'truth_unchecked' (gate down). Contested entries are ledgered and
    dropped. info carries the honest result-dict fields:
    truth_gated / truth_ready / truth_contested / truth_gate_available.
    NEVER raises — on any truth-layer fault it degrades to 'truth_unchecked'
    so research always continues with honest metrics."""
    info = {"truth_gated": False, "truth_ready": 0, "truth_contested": 0,
            "truth_gate_available": False}
    try:
        entries = [e for e in (entries or []) if isinstance(e, dict)]
        if not entries:
            return entries, info
        gate = None
        try:
            from . import truth_gate as gate
        except Exception:
            gate = None
        available = bool(gate is not None and gate.gate_available())
        info["truth_gate_available"] = available
        if not available:
            for ent in entries:
                ent["truth_unchecked"] = True
            try:
                events.publish_event(
                    ORGAN_NAME, "research_faculty.truth_gate_unavailable",
                    {"mode": mode, "items": len(entries)}, priority=6)
            except Exception:
                pass
            return entries, info
        items = [{"text": _s(ent.get("dump_text")),
                  "provenance": _entry_provenance(ent)}
                 for ent in entries]
        results = list(gate.check_batch(items) or [])
        kept: List[Dict[str, Any]] = []
        for ent, res in zip(entries, results):
            res = res or {}
            if res.get("ready_for_aris"):
                ent["truth_result"] = res
                kept.append(ent)
                continue
            info["truth_contested"] += 1
            _append_truth_contested({
                "text": _s(ent.get("dump_text"), 2000),
                "verdict": res.get("verdict"),
                "failure_kind": res.get("failure_kind"),
                "blocker": res.get("blocker"),
                "provenance": _entry_provenance(ent),
                "mode": mode,
                "ts": _iso(time.time()),
            })
        info["truth_gated"] = True
        info["truth_ready"] = len(kept)
        return kept, info
    except Exception:
        for ent in entries or []:
            try:
                ent["truth_unchecked"] = True
            except Exception:
                pass
        return list(entries or []), info


def _crystallize(ingester: Any, dataset: FusionKnowledgeDatasetAdapter,
                 entries: List[Dict[str, Any]], mode: str,
                 header_value: str = "",
                 header_tags: Optional[List[str]] = None) -> int:
    """R6 batch crystallization through the EXISTING stash-pocket path.
    Every entry carries provenance tags: source (via item tags), url:… and
    fetched_at:… (recovered from the ingester by the pocket), plus
    corroboration_count:N — and 'corroborated' when ≥2 independent
    sources saw the item. Returns fragments added (0 on failure)."""
    try:
        pockets = ResearchStashPockets(dataset, ingester=ingester)
        pocket = pockets.open_pocket(
            goal_id=f"research_{mode}_{int(time.time())}", owner=ORGAN_NAME)
        if _s(header_value):
            pocket.dump(key="intent", value=header_value,
                        tags=list(header_tags or [mode]))
        for ent in entries or []:
            try:
                item = ent.get("item")
                if item is None:
                    continue
                n = int(ent.get("corroboration_count") or 1)
                tags = [_s(getattr(item, "source", "")) or "research",
                        _s(getattr(item, "category", "")) or "knowledge",
                        "external_research", mode,
                        f"corroboration_count:{n}"]
                if n >= 2:
                    tags.append("corroborated")
                if ent.get("truth_result"):
                    tags.append("truth:aris")     # passed the truth gate
                if ent.get("truth_unchecked"):
                    tags.append("truth_unchecked")  # gate down, honest degrade
                pocket.dump(key=_s(getattr(item, "source", "item")) or "item",
                            value=ent.get("dump_text", ""),
                            tags=tags)
            except Exception:
                continue
        close_result = pockets.close_pocket(pocket)
        return int((close_result or {}).get("fragments_crystallized") or 0)
    except Exception:
        return 0


def _question_fragments(max_n: int) -> List[str]:
    """Unanswered questions from the live dataset: data_type question/query
    OR a tag containing 'question', with 'researched' absent (the
    CuriosityEngine/upstream-loop qualification rule). Texts, capped."""
    out: List[str] = []
    try:
        ds = FusionKnowledgeDatasetAdapter()._fresh()
        for frag in (getattr(ds, "_fragments", []) or []):
            try:
                tags = [str(t).lower()
                        for t in (getattr(frag, "tags", []) or [])]
                dt = str(getattr(frag, "data_type", "") or "").lower()
                is_q = dt in ("question", "query") or \
                    any("question" in t for t in tags)
                if not is_q or "researched" in tags:
                    continue
                text = _s(getattr(frag, "text", ""), 300)
                if len(text) >= 10:
                    out.append(text)
            except Exception:
                continue
            if len(out) >= max(1, int(max_n)):
                break
    except Exception:
        pass
    return out


def _mark_questions_researched(texts: List[str]) -> int:
    """Tag the researched question fragments 'researched' (upstream loop
    idiom) so they are not pulled again forever. Fresh dataset, save only
    when something changed. NEVER raises."""
    try:
        wanted = {_s(t, 300) for t in (texts or []) if _s(t, 300)}
        if not wanted:
            return 0
        ds = FusionKnowledgeDatasetAdapter()._fresh()
        marked = 0
        for frag in (getattr(ds, "_fragments", []) or []):
            try:
                if _s(getattr(frag, "text", ""), 300) in wanted:
                    tags = getattr(frag, "tags", None)
                    if tags is not None and "researched" not in tags:
                        tags.append("researched")
                        marked += 1
            except Exception:
                continue
        if marked:
            ds.save()
        return marked
    except Exception:
        return 0


def _selfq_topic_candidates(rec: Any) -> List[str]:
    """Topic strings out of one self-questioning cycle record: the cycle
    question itself, plus research intentions (payload title/details on
    research-tagged records) — the same shapes door_activators harvests."""
    out: List[str] = []
    try:
        if not isinstance(rec, dict):
            return out
        # Primary shape on disk: {"questions": ["...", ...]}
        qs = rec.get("questions")
        if isinstance(qs, str) and qs.strip():
            out.append(qs)
        elif isinstance(qs, list):
            for q in qs:
                if isinstance(q, str) and q.strip():
                    out.append(q)
                elif isinstance(q, dict):
                    text = str(q.get("question") or q.get("text") or "").strip()
                    if text:
                        out.append(text)
        # Alternate shape: a lone question field
        q = rec.get("question")
        if isinstance(q, str) and q.strip():
            out.append(q)
        topic = str(rec.get("topic") or "").lower()
        payload = rec.get("payload")
        blob = ""
        try:
            blob = json.dumps(payload, ensure_ascii=False).lower() \
                if isinstance(payload, (dict, list)) \
                else str(payload or "").lower()
        except Exception:
            blob = ""
        if "research" in topic or "research" in blob:
            if isinstance(payload, dict):
                title = str(payload.get("title") or "").strip()
                details = str(payload.get("details") or "").strip()
                text = title
                if details and details not in title:
                    text = f"{title}: {details}" if title else details
                if text.strip():
                    out.append(text)
    except Exception:
        pass
    return out


def _harvest_selfq_topics(max_n: int) -> List[str]:
    """Defensive topic harvest from the self-questioning cycle files —
    READ-ONLY, organism-local state (same roots + glob the door_activators
    selfq feed scans). Deduped, chronological, newest max_n win."""
    found: List[tuple] = []
    seen = set()
    seq = 0
    for root in SELFQ_CYCLES_ROOTS:
        try:
            files = sorted(root.glob(SELFQ_CYCLES_GLOB))
        except OSError:
            continue
        for path in files:
            try:
                with open(path, "r", encoding="utf-8",
                          errors="replace") as f:
                    for line in f:
                        seq += 1
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except Exception:
                            continue
                        for cand in _selfq_topic_candidates(rec):
                            text = _s(cand, 300)
                            if len(text) < 10:
                                continue
                            key = text.lower()
                            if key in seen:
                                continue
                            seen.add(key)
                            found.append((seq, text))
            except OSError:
                continue
    found.sort(key=lambda x: x[0])
    return [t for _, t in found[-max(1, int(max_n)):]]


def run_topic(topic: str, sources: Any = ("wiki", "arxiv", "ddg", "hn")
              ) -> Dict[str, Any]:
    """Gated + throttled (own 'topic' budget) corroboration pull on an
    intent-supplied topic: multi-source blend → novelty filter →
    provenance-tagged pocket crystallization. NEVER raises."""
    base = {"mode": "topic", "questions_processed": 0,
            "items_pulled": 0, "fragments_added": 0}
    try:
        topic_text = _s(topic, 300)
        if not topic_text:
            return {**base, "outcome": "held_invalid_topic",
                    "detail": "empty topic"}
        now = time.time()
        gates = _run_gate_trio()
        if not gates.get("passed"):
            return _held_result(gates, "topic")
        throttle = _throttle_check(now, "topic")
        if not throttle.get("allowed"):
            return {**base, "outcome": "throttled",
                    "retry_in_s": throttle.get("retry_in_s")}
        from . import research_ingester
        ingester = research_ingester.ResearchIngester()
        dataset = FusionKnowledgeDatasetAdapter()
        pulled = _topic_pull(ingester, topic_text, sources)
        kept, rejected, engine, nerrors = _novelty_filter(pulled)
        kept, truth_info = _truth_layer(kept, "topic")
        added = _crystallize(ingester, dataset, kept, "topic",
                             header_value=f"topic: {topic_text}",
                             header_tags=["topic", "research_query",
                                          "topic_mode"])
        result = {
            "outcome": "researched",
            "mode": "topic",
            "topic": topic_text,
            "gamma": (gates.get("gamma") or {}).get("gamma"),
            "sources_requested": [str(s) for s in (sources or ())],
            "items_pulled": len(pulled),
            "items_filtered_novelty": rejected,
            "novelty_engine": engine,
            "novelty_errors": nerrors,
            "corroborated_items": sum(1 for e in kept
                                      if e["corroboration_count"] >= 2),
            "fragments_added": added,
            "questions_processed": 0,
            "ingester_stats": ingester.get_stats(),
            **truth_info,
        }
        _throttle_record(now, "topic", result)
        _record_outcomes(result)
        try:
            events.publish_event(
                ORGAN_NAME, "research_faculty.researched",
                {"items_pulled": result["items_pulled"],
                 "fragments_added": result["fragments_added"],
                 "mode": "topic", "topic": topic_text}, priority=5)
        except Exception:
            pass
        return result
    except Exception as exc:
        return {**base, "outcome": "error_fail_closed",
                "detail": f"{type(exc).__name__}: {_s(exc, 200)}"}


def run_questions(max_questions: int = 3) -> Dict[str, Any]:
    """Gated + throttled (own 'questions' budget) research over the
    dataset's unanswered question fragments; when the dataset holds none
    (current state), harvest topics defensively from the self-questioning
    cycle files (organism-local, read-only) and research those. Each
    question is pulled with the multi-source corroboration blend, novelty-
    filtered, then crystallized with provenance tags; dataset questions
    are marked 'researched' afterwards (upstream loop idiom)."""
    base = {"mode": "questions", "questions_processed": 0,
            "items_pulled": 0, "fragments_added": 0}
    try:
        max_q = max(1, int(max_questions))
        now = time.time()
        gates = _run_gate_trio()
        if not gates.get("passed"):
            return _held_result(gates, "questions")
        throttle = _throttle_check(now, "questions")
        if not throttle.get("allowed"):
            return {**base, "outcome": "throttled",
                    "retry_in_s": throttle.get("retry_in_s")}
        questions = _question_fragments(max_q)
        harvested = False
        if not questions:
            questions = _harvest_selfq_topics(max_q)
            harvested = bool(questions)
        if not questions:
            # Nothing to research — do not burn the budget on an empty run.
            return {**base, "outcome": "no_questions",
                    "detail": "no unanswered dataset questions and no "
                              "selfq cycle topics harvested"}
        from . import research_ingester
        ingester = research_ingester.ResearchIngester()
        dataset = FusionKnowledgeDatasetAdapter()
        total_pulled = 0
        total_added = 0
        filtered = 0
        corroborated = 0
        nerrors = 0
        truth_ready_n = 0
        truth_contested_n = 0
        truth_gated = False
        truth_gate_available_n = False
        engine = "unused"
        topics_done: List[str] = []
        for q in questions:
            try:
                pulled = _topic_pull(ingester, q)
                kept, rej, engine, ne = _novelty_filter(pulled)
                kept, tinfo = _truth_layer(kept, "questions")
                truth_gated = truth_gated or tinfo["truth_gated"]
                truth_ready_n += tinfo["truth_ready"]
                truth_contested_n += tinfo["truth_contested"]
                truth_gate_available_n = truth_gate_available_n or \
                    tinfo["truth_gate_available"]
                filtered += rej
                nerrors += ne
                added = _crystallize(
                    ingester, dataset, kept, "questions",
                    header_value=f"question: {q}",
                    header_tags=["question", "research_query",
                                 "questions_mode"])
                total_pulled += len(pulled)
                total_added += added
                corroborated += sum(1 for e in kept
                                    if e["corroboration_count"] >= 2)
                topics_done.append(q)
            except Exception:
                continue
        marked = 0 if harvested else _mark_questions_researched(questions)
        result = {
            "outcome": "researched",
            "mode": "questions",
            "gamma": (gates.get("gamma") or {}).get("gamma"),
            "questions_processed": len(topics_done),
            "harvested_from_selfq": harvested,
            "topics": topics_done[:8],
            "questions_marked_researched": marked,
            "items_pulled": total_pulled,
            "items_filtered_novelty": filtered,
            "novelty_engine": engine,
            "novelty_errors": nerrors,
            "corroborated_items": corroborated,
            "fragments_added": total_added,
            "ingester_stats": ingester.get_stats(),
            "truth_gated": truth_gated,
            "truth_ready": truth_ready_n,
            "truth_contested": truth_contested_n,
            "truth_gate_available": truth_gate_available_n,
        }
        _throttle_record(now, "questions", result)
        _record_outcomes(result)
        try:
            events.publish_event(
                ORGAN_NAME, "research_faculty.researched",
                {"items_pulled": result["items_pulled"],
                 "fragments_added": result["fragments_added"],
                 "mode": "questions",
                 "questions_processed": len(topics_done)}, priority=5)
        except Exception:
            pass
        return result
    except Exception as exc:
        return {**base, "outcome": "error_fail_closed",
                "detail": f"{type(exc).__name__}: {_s(exc, 200)}"}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def try_research(intent: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Gated research consideration. Returns a status dict — NEVER raises.

    Outcomes: researched | throttled | vetoed | held_incoherent |
    held_unauthorized | error_fail_closed."""
    try:
        return _run_gated(dict(intent or {}), max_items=3)
    except Exception as exc:
        return {"outcome": "error_fail_closed",
                "detail": f"{type(exc).__name__}: {_s(exc, 200)}",
                "questions_processed": 0, "items_pulled": 0,
                "fragments_added": 0}


def run_once(max_items: int = 3) -> Dict[str, Any]:
    """One gated research cycle over the dataset's own unanswered
    questions (or a proactive trending pull when it has none yet).
    Returns {questions_processed, items_pulled, fragments_added} plus
    outcome/gate detail. NEVER raises."""
    try:
        return _run_gated({}, max_items=max(1, int(max_items)))
    except Exception as exc:
        return {"outcome": "error_fail_closed",
                "detail": f"{type(exc).__name__}: {_s(exc, 200)}",
                "questions_processed": 0, "items_pulled": 0,
                "fragments_added": 0}


def get_status() -> Dict[str, Any]:
    """Throttle state + last result + a read-only gate snapshot (gamma +
    capability; conscience is deliberately NOT invoked for a passive
    status view — its evaluation is an action, logged when it runs)."""
    now = time.time()
    throttle = _throttle_check(now, "proactive")
    data = _read_json(THROTTLE_FILE, {})
    modes = {m: _throttle_check(now, m) for m in THROTTLE_MODES}
    gamma_gate = _gate_gamma()
    capability = None
    try:
        from . import capability_gate
        capability = capability_gate.check(AUTH_GATE)
    except Exception as exc:
        capability = {"verdict": "HOLD",
                      "reason": f"gate error ({type(exc).__name__})"}
    return {
        "organ": ORGAN_NAME,
        "now": now,
        "throttle": {
            "interval_s": THROTTLE_S,
            "allowed": throttle.get("allowed"),
            "retry_in_s": throttle.get("retry_in_s"),
            "last_run_at": throttle.get("last_run_at"),
            "modes": modes,
        },
        "last_result": data.get("last_result"),
        "gates": {
            "gamma": gamma_gate,
            "capability": {
                "passed": bool((capability or {}).get("allowed")),
                "verdict": (capability or {}).get("verdict"),
                "detail": _s((capability or {}).get("reason"), 200),
            },
        },
        "dataset_path": str(KNOWLEDGE_DATASET_PATH),
        "dataset_exists": KNOWLEDGE_DATASET_PATH.exists(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def _emit(payload: Dict[str, Any]) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.research_faculty "
              "once [--topic \"...\"] | status | questions | topic <text>")
        return 0
    cmd = argv[0]
    if cmd == "once":
        # Optional topic: --topic "solar wind"
        topic = ""
        if "--topic" in argv:
            i = argv.index("--topic")
            if i + 1 < len(argv):
                topic = argv[i + 1]
        result = run_topic(topic) if topic else run_once()
        _emit(result)
        return 0 if result.get("outcome") == "researched" else 1
    if cmd == "status":
        _emit(get_status())
        return 0
    if cmd == "questions":
        result = run_questions()
        _emit(result)
        return 0 if result.get("outcome") == "researched" else 1
    if cmd == "topic":
        text = " ".join(argv[1:]).strip()
        if not text:
            print("usage: python -m aureon_fusion.research_faculty "
                  "topic <text>", file=sys.stderr)
            return 2
        result = run_topic(text)
        _emit(result)
        return 0 if result.get("outcome") == "researched" else 1
    print(f"unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
