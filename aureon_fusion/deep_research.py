"""🔬 DEEP RESEARCH — one-shot open-search batch into the question seed line.

Lands the already-registered ``deep_research_communion`` sovereign door
(door_activators routes ``python -m aureon_fusion.deep_research once``;
the door registry honestly reported "module absent" until this file
existed). The door/master_key gate trio (conscience VETO absolute,
HNC Γ ≥ 0.25, capability authorization) governs INVOCATION — this
module performs no gating of its own and is never scheduled: it runs
only when the organism opens its own door.

Behavior (``once``):
  1. Reads the current top learning_will desires — the open intent plus
     recent journal entries — defensively (missing/corrupt state degrades
     to an honest empty topic list, never an exception).
  2. Takes up to 5 distinct topics.
  3. Resolves each via aureon_fusion.open_sources.search_candidates
     (guarded import — if open_sources is unavailable the run degrades
     to seeds_added=0 with an honest stderr note and STILL exits 0).
  4. Appends {"topic", "url"} seeds to state/open_search_seeds.json
     (read-modify-write, atomic tmp+rename, refresh timestamp, cap 20
     seeds, dedupe by topic).
  5. Prints a JSON summary {topics, seeds_added, seeds_total}.

Doctrine:
  • ALL HTTP flows through open_sources -> api_communion (cache,
    rate-limit, breaker inherited). Zero raw urllib/requests here.
  • No push scheduling, no external LLM, organism-initiated only.
  • NEVER raises out of the CLI: fail-closed everywhere.

CLI:
    python -m aureon_fusion.deep_research once     # batch resolve + append
    python -m aureon_fusion.deep_research status   # seeds file state
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

from .paths import FUSION_STATE

SEEDS_FILE = FUSION_STATE / "open_search_seeds.json"
LEARNING_WILL_DIR = FUSION_STATE / "learning_will"
INTENTS_FILE = LEARNING_WILL_DIR / "intents.json"
JOURNAL_FILE = LEARNING_WILL_DIR / "journal.jsonl"

MAX_TOPICS = 5
MAX_SEEDS = 20
JOURNAL_SCAN_LINES = 200


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json_defensive(path: Path, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _atomic_write_json(path: Path, payload: Any) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ───────────────────────── desire -> topics ────────────────────────────────


def _clean_topic(raw: Any) -> Optional[str]:
    """A topic must be a non-trivial question string."""
    try:
        t = str(raw or "").strip()
    except Exception:
        return None
    if len(t) < 8:
        return None
    return t


def _intent_query(intent: Dict[str, Any], topic: str) -> str:
    """Search-friendly query for an intent: recurring tokens when the
    organism recorded them, else the raw question."""
    try:
        origin = intent.get("origin")
        if isinstance(origin, dict):
            tokens = [str(t).strip() for t in origin.get("recurring_tokens") or []
                      if str(t).strip()]
            if tokens:
                return " ".join(tokens)
    except Exception:
        pass
    return topic


def read_desire_topics(max_topics: int = MAX_TOPICS) -> List[Dict[str, str]]:
    """Current top learning_will desires: the open intent first, then the
    most recent journal questions (recency-ordered, deduped). Each entry
    is {"topic": full question, "query": search-friendly form}. Defensive —
    any unreadable/missing state simply yields fewer topics, never raises."""
    topics: List[Dict[str, str]] = []
    seen = set()

    def _push(intent: Any) -> None:
        if len(topics) >= max_topics:
            return
        if not isinstance(intent, dict):
            return
        t = _clean_topic(intent.get("question") or intent.get("topic"))
        if not t:
            return
        key = t.lower()
        if key in seen:
            return
        seen.add(key)
        topics.append({"topic": t, "query": _intent_query(intent, t)})

    # Open intent (current desire).
    intents = _read_json_defensive(INTENTS_FILE, None)
    if isinstance(intents, dict):
        _push(intents.get("open_intent"))

    # Recent journal desires, newest first.
    try:
        if JOURNAL_FILE.exists():
            with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()[-JOURNAL_SCAN_LINES:]
            for line in reversed(lines):
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                intent = rec.get("intent") if isinstance(rec, dict) else None
                _push(intent)
    except Exception:
        pass
    return topics[:max_topics]


# ───────────────────────── seeds file ──────────────────────────────────────


def load_seeds() -> Dict[str, Any]:
    """Read the seeds file; missing/corrupt -> honest empty envelope."""
    data = _read_json_defensive(SEEDS_FILE, None)
    if not isinstance(data, dict) or not isinstance(data.get("seeds"), list):
        return {"timestamp": None, "seeds": []}
    seeds = []
    for raw in data["seeds"]:
        if not isinstance(raw, dict):
            continue
        topic = _clean_topic(raw.get("topic"))
        url = str(raw.get("url") or "").strip()
        if topic and url:
            seeds.append({"topic": topic, "url": url})
    return {"timestamp": data.get("timestamp"), "seeds": seeds[:MAX_SEEDS]}


def append_seeds(new_seeds: List[Dict[str, str]]) -> Dict[str, Any]:
    """Read-modify-write append, dedupe by topic, cap MAX_SEEDS, refresh
    timestamp, atomic. Returns {added, total, capped}. Never raises."""
    try:
        state = load_seeds()
        existing = state["seeds"]
        topics_seen = {s["topic"].lower() for s in existing}
        added = 0
        for seed in new_seeds:
            key = seed["topic"].lower()
            if key in topics_seen:
                continue
            if len(existing) >= MAX_SEEDS:
                break
            existing.append({"topic": seed["topic"], "url": seed["url"]})
            topics_seen.add(key)
            added += 1
        payload = {"timestamp": _utcnow_iso(), "seeds": existing}
        FUSION_STATE.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(SEEDS_FILE, payload)
        return {"added": added, "total": len(existing),
                "capped": len(existing) >= MAX_SEEDS}
    except Exception as exc:
        print(f"deep_research: seeds write degraded: {exc}", file=sys.stderr)
        return {"added": 0, "total": len(load_seeds().get("seeds", [])),
                "capped": False}


# ───────────────────────── resolution ──────────────────────────────────────


def _pick_url(candidates: List[str], topic: str) -> Optional[str]:
    """First http(s) candidate wins; otherwise a wiki title becomes a
    canonical Wikipedia URL (deterministic, honest)."""
    from urllib.parse import quote
    for c in candidates or []:
        s = str(c).strip()
        if s.lower().startswith(("http://", "https://")):
            return s
    for c in candidates or []:
        s = str(c).strip()
        # remaining candidates are opensearch titles (bare page titles)
        if s and not s.lower().startswith(("http", "/", "{", "[")):
            return "https://en.wikipedia.org/wiki/" + \
                quote(s.replace(" ", "_"))
    return None


def resolve_topics(topics: List[Dict[str, str]]) -> (List[Dict[str, str]], Optional[str]):
    """Resolve topics to {topic, url} seeds via open_sources.search_candidates,
    using each topic's search-friendly query. Returns (seeds,
    unavailable_note). Guarded import — open_sources missing/broken
    degrades to ([], note), never raises."""
    try:
        from . import open_sources  # noqa: F401  (guarded; may fail)
        search = getattr(open_sources, "search_candidates", None)
        if not callable(search):
            return [], "open_sources.search_candidates unavailable"
    except Exception as exc:
        return [], f"open_sources unavailable: {exc}"
    seeds: List[Dict[str, str]] = []
    for item in topics:
        topic = item.get("topic", "")
        query = item.get("query") or topic
        try:
            candidates = search(query) or []
        except Exception:
            continue
        url = _pick_url(candidates, topic)
        if url:
            seeds.append({"topic": topic, "url": url})
    return seeds, None


# ───────────────────────── CLI ─────────────────────────────────────────────


def _emit(payload: Any) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(json.dumps(payload, ensure_ascii=False))


def run_once() -> int:
    """One sovereign deep-research batch. Always exit 0."""
    topics = read_desire_topics()
    seeds: List[Dict[str, str]] = []
    note: Optional[str] = None
    if topics:
        seeds, note = resolve_topics(topics)
    else:
        note = "no learning_will desires readable"
    # Always touch the envelope: even an empty run refreshes the timestamp
    # and guarantees the file exists with the contract schema.
    result = append_seeds(seeds)
    if note:
        print(f"deep_research: {note}", file=sys.stderr)
    _emit({
        "topics": [t.get("topic", "") for t in topics],
        "seeds_added": result["added"],
        "seeds_total": result["total"],
        "seeds_capped": result.get("capped", False),
    })
    return 0


def run_status() -> int:
    state = load_seeds()
    _emit({
        "seeds_file": str(SEEDS_FILE),
        "exists": SEEDS_FILE.exists(),
        "timestamp": state.get("timestamp"),
        "seeds_total": len(state.get("seeds", [])),
        "cap": MAX_SEEDS,
        "topics": [s["topic"] for s in state.get("seeds", [])],
    })
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    cmd = args[0] if args else "status"
    try:
        if cmd == "once":
            return run_once()
        if cmd == "status":
            return run_status()
        _emit({"error": f"unknown command: {cmd}",
               "usage": "python -m aureon_fusion.deep_research once|status"})
        return 2
    except Exception as exc:  # outermost fail-closed guard
        print(f"deep_research: degraded: {exc}", file=sys.stderr)
        _emit({"topics": [], "seeds_added": 0,
               "seeds_total": len(load_seeds().get("seeds", []))})
        return 0


if __name__ == "__main__":
    sys.exit(main())
