"""📖 KNOWLEDGE OUTCOMES — the queen_knowledge writer.

The aureon_global_history SQLite memory has carried a queen_knowledge table
(knowledge_type / summary / success_rate / times_applied) since schema v5 —
with ZERO writers. This module is the first. It records honest outcomes:

  upsert_outcome(knowledge_type, summary, success) — inserts or updates the
  deterministic row for (knowledge_type, summary): success_rate is a running
  mean over SCORED applications, times_applied counts every application.
  success=None records a usage-only outcome — the summary notes provenance
  and success_rate is left untouched (never fabricated from data that
  carries no success signal).

  consult(topic_tokens, limit=5) — the queen_knowledge decision-feedback
  read (W6): returns the rows whose type/topic/summary match the cycle's
  key tokens. Rows that carry a scored success_rate rank ahead of unscored
  rows (scored knowledge is knowledge that stood up to application), then
  times_applied, then success_rate — what the corpus already learned about
  the matter at hand. Read-only; fail-closed [].

  record_research(topic, summary, items_found, fragments_added,
                  corroborated, success) — the research-outcomes sink (R4):
  one queen_knowledge row per research topic (knowledge_type
  'research_topic'), fed by research_faculty's result dicts. Success is
  honest: success=None when the run carries no quality signal; success=True
  is only accepted when fragments_added > 0 AND corroborated > 0 (the
  result stood up to cross-source checking) — a forced True with no such
  signal is downgraded to None, never fabricated. Repeat records of the
  same topic on the same day are idempotent (no double-count); a new day
  bumps times_applied and feeds success into the running mean over scored
  applications. Returns the knowledge_id ("" on failure — never raises).

  record_research_memory(topic, fragment_texts) — memory connections (R5):
  remembers the topic plus up to 3 fragment summaries into sero_memory_web
  (lazy import from the workspace root, same idiom as trade_journal), the
  topic node connected to the 2 most recently remembered nodes so research
  chains, fragments chained to the topic. Returns the number of nodes
  created (0 when the engine is unavailable — never raises).

CLI:
    python -m aureon_fusion.knowledge_outcomes sweep
        Fold the trade-journal sweep state into outcome rows: one row per
        journaled entry in state/trade_journal_seen.json. The sweep state
        holds dedupe keys only (source file, symbol/side, audit id) — no
        P&L, no fill outcome — so these are usage outcomes
        (success_rate stays NULL, times_applied counts the journaling).
    python -m aureon_fusion.knowledge_outcomes status
        Row counts by knowledge_type.
    python -m aureon_fusion.knowledge_outcomes research
        The last 10 research_topic outcome rows (the research faculty's
        absorbed outcomes, newest first).

Import-safe: suppression env planted before any aureon import (same
doctrine as hnc_core / queen_mind), no network, no threads, no process
spawns. Fail-closed: a missing/corrupt DB or sweep state degrades to an
honest empty result — it never raises into the caller.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

# Script-or-module bootstrap: the registrar may launch this file directly.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aureon_fusion.paths import AUREON_UPSTREAM, FUSION_STATE, WORKSPACE

# ── SUPPRESSION ENV — must be set BEFORE any aureon import ──────────────
os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")
# Pin the history DB exactly like queen_mind does, so any upstream accessor
# that resolves through the env sees the fusion-state file (never CWD).
HISTORY_DB_PATH = FUSION_STATE / "aureon_global_history.sqlite"
os.environ["AUREON_GLOBAL_HISTORY_DB"] = str(HISTORY_DB_PATH)

# Pin the upstream repo root on sys.path (idempotent) — same idiom as hnc_core.
_UPSTREAM_ROOT = str(AUREON_UPSTREAM)
if _UPSTREAM_ROOT not in sys.path:
    sys.path.insert(0, _UPSTREAM_ROOT)

ORGAN_NAME = "knowledge_outcomes"
LAST_SWEEP_PATH = FUSION_STATE / "trade_journal_last_sweep.json"
SEEN_PATH = FUSION_STATE / "trade_journal_seen.json"
_SOURCE = "aureon_fusion.knowledge_outcomes"

_CONN = None


# ───────────────────────────── db accessor ─────────────────────────────────

def get_history_db():
    """The SQLite memory via the upstream accessor, connected on first use.

    Same pattern as aureon_fusion.hnc_core.get_history_db: explicit absolute
    fusion-state path, schema ensured by the upstream connect(). Never raises.
    """
    global _CONN
    if _CONN is None:
        try:
            from aureon.core import aureon_global_history_db as ghdb

            _CONN = ghdb.connect(str(HISTORY_DB_PATH))
        except Exception:
            _CONN = False  # degraded sentinel: remember the failure, stay quiet
    return _CONN or None


def _knowledge_id(knowledge_type: str, summary: str) -> str:
    """Deterministic primary key for a (type, summary) outcome row."""
    digest = hashlib.sha1(f"{knowledge_type}|{summary}".encode("utf-8")).hexdigest()
    return f"fusion_outcome:{knowledge_type}:{digest[:16]}"


def upsert_outcome(knowledge_type: str, summary: str,
                   success: bool | None = None, *,
                   topic: str | None = None, source: str | None = None,
                   confidence: float | None = None,
                   raw: dict | None = None) -> bool:
    """Insert or update one honest outcome row.

    First call inserts (times_applied=1). Repeat calls bump times_applied.
    success=True/False feeds the running mean over scored applications;
    success=None is a usage-only application — times_applied still counts,
    success_rate is left exactly as the data allows (NULL until the first
    real success signal). Fail-closed: returns False on any DB error.
    """
    conn = get_history_db()
    if conn is None or not knowledge_type or not summary:
        return False
    now_ms = int(time.time() * 1000)
    kid = _knowledge_id(knowledge_type, summary)
    try:
        row = conn.execute(
            "SELECT success_rate, times_applied, raw_json "
            "FROM queen_knowledge WHERE knowledge_id = ?", (kid,)).fetchone()
        if row is None:
            scored = 1 if success is not None else 0
            rate = (1.0 if success else 0.0) if success is not None else None
            payload = dict(raw or {})
            payload["scored_applications"] = scored
            conn.execute(
                "INSERT OR IGNORE INTO queen_knowledge("
                " knowledge_id, knowledge_type, topic, summary, source,"
                " confidence, success_rate, times_applied, ts_ms,"
                " ingested_at_ms, raw_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (kid, knowledge_type, topic, summary, source or _SOURCE,
                 confidence, rate, 1, now_ms, now_ms,
                 json.dumps(payload, ensure_ascii=False)))
        else:
            times = int(row["times_applied"] or 0) + 1
            try:
                payload = json.loads(row["raw_json"] or "{}")
            except (json.JSONDecodeError, TypeError):
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            rate = row["success_rate"]
            if success is not None:
                scored = int(payload.get("scored_applications") or 0) + 1
                prev = float(rate) if rate is not None else 0.0
                rate = (prev * (scored - 1) + (1.0 if success else 0.0)) / scored
                payload["scored_applications"] = scored
            conn.execute(
                "UPDATE queen_knowledge SET times_applied = ?,"
                " success_rate = ?, ts_ms = ?, raw_json = ?"
                " WHERE knowledge_id = ?",
                (times, rate, now_ms,
                 json.dumps(payload, ensure_ascii=False), kid))
        conn.commit()
        return True
    except Exception:
        return False


# ─────────────────── research outcomes sink (R4) + memory web (R5) ─────────

def _record_day(now_ms: int) -> str:
    """The idempotency grain for record_research: one record per topic+day."""
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(now_ms / 1000.0))
    except Exception:
        return ""


def record_research(topic: str, summary: str, items_found: int,
                    fragments_added: int, corroborated: int,
                    success: bool | None = None) -> str:
    """Record one research-faculty outcome as a queen_knowledge row.

    One row per topic (knowledge_type 'research_topic'); a repeat record
    of the same topic on the SAME day is idempotent — the existing row is
    returned untouched, no double-count. A record on a NEW day bumps
    times_applied and feeds success into the running mean over scored
    applications (tracked in raw_json['scored_applications'], same idiom
    as upsert_outcome).

    Honest success semantics, never fabricated:
      success=None  — the run carries no quality signal (nothing absorbed,
                      or nothing corroborated); success_rate stays as the
                      data allows and only times_applied moves.
      success=True  — accepted ONLY when fragments_added > 0 AND
                      corroborated > 0 (the result stood up to cross-source
                      checking); a True without that signal is downgraded
                      to None rather than recorded as a lie.
      success=False — a real negative signal (the run happened and yielded
                      nothing usable); it scores 0 into the running mean.

    Returns the knowledge_id ("" when nothing could be written). Every
    failure path degrades — this function NEVER raises into a caller's
    cycle.
    """
    try:
        conn = get_history_db()
        topic = " ".join(str(topic or "").split())
        if conn is None or not topic:
            return ""
        now_ms = int(time.time() * 1000)
        day = _record_day(now_ms)
        try:
            items_found = max(0, int(items_found))
            fragments_added = max(0, int(fragments_added))
            corroborated = max(0, int(corroborated))
        except (TypeError, ValueError):
            items_found = fragments_added = corroborated = 0
        # Never fabricate: a True without a real cross-source quality
        # signal is no signal at all.
        if success is not None and not (
                success and fragments_added > 0 and corroborated > 0):
            success = bool(success) if not success else None

        kid = _knowledge_id("research_topic", topic)
        note = " ".join(str(summary or "").split())[:400]
        full_summary = (
            f"research topic '{topic}': {note} — items_found={items_found}, "
            f"fragments_added={fragments_added}, corroborated={corroborated} "
            f"(cross-source checked); sources: keyless public feeds via "
            f"api_communion (HN/Reddit/Wikipedia/markets/quakes/weather/"
            f"arXiv), provenance-tagged fragments in knowledge_dataset")

        row = conn.execute(
            "SELECT success_rate, times_applied, raw_json "
            "FROM queen_knowledge WHERE knowledge_id = ?", (kid,)).fetchone()
        if row is not None:
            try:
                payload = json.loads(row["raw_json"] or "{}")
            except (json.JSONDecodeError, TypeError):
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            if payload.get("record_day") == day:
                # Idempotent per topic+day: re-recording the same topic on
                # the same day changes nothing (no times_applied bump, no
                # mean pollution).
                return kid
            times = int(row["times_applied"] or 0) + 1
            rate = row["success_rate"]
            if success is not None:
                scored = int(payload.get("scored_applications") or 0) + 1
                prev = float(rate) if rate is not None else 0.0
                rate = (prev * (scored - 1) + (1.0 if success else 0.0)) / scored
                payload["scored_applications"] = scored
        else:
            times = 1
            scored = 1 if success is not None else 0
            rate = (1.0 if success else 0.0) if success is not None else None
            payload = {"scored_applications": scored}
        payload.update({
            "record_day": day,
            "items_found": items_found,
            "fragments_added": fragments_added,
            "corroborated": corroborated,
            "last_success": (None if success is None else bool(success)),
            "provenance": "aureon_fusion.research_faculty",
        })
        conn.execute(
            "INSERT OR IGNORE INTO queen_knowledge("
            " knowledge_id, knowledge_type, topic, summary, source,"
            " confidence, success_rate, times_applied, ts_ms,"
            " ingested_at_ms, raw_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (kid, "research_topic", topic, full_summary, _SOURCE,
             None, rate, times, now_ms, now_ms,
             json.dumps(payload, ensure_ascii=False)))
        conn.execute(
            "UPDATE queen_knowledge SET summary = ?, topic = ?,"
            " success_rate = ?, times_applied = ?, ts_ms = ?, raw_json = ?"
            " WHERE knowledge_id = ?",
            (full_summary, topic, rate, times, now_ms,
             json.dumps(payload, ensure_ascii=False), kid))
        conn.commit()
        return kid
    except Exception:
        return ""


def record_research_memory(topic: str, fragment_texts) -> int:
    """Remember a research topic and up to 3 fragment summaries in the
    sero MemoryWeb so research chains into the consciousness stack (R5).

    One node per input: the topic node (node_type 'research_topic') is
    connected to the 2 most recently remembered nodes already in the web,
    so new research links onto the freshest memory chain; each fragment
    node (node_type 'research_fragment') chains to the previous node of
    this run. sero_memory_web is a LAZY import from the workspace root —
    same idiom as trade_journal — and the engine's load chatter is
    swallowed. Returns the number of nodes created (0 when the engine is
    unavailable or nothing could be remembered — NEVER raises).
    """
    try:
        topic = " ".join(str(topic or "").split())
        texts = [" ".join(str(t).split())[:240]
                 for t in (list(fragment_texts or [])[:3])
                 if str(t or "").strip()]
        if not topic or not texts:
            return 0
        if str(WORKSPACE) not in sys.path:
            sys.path.insert(0, str(WORKSPACE))
        import io
        from contextlib import redirect_stdout

        import sero_memory_web as smw
        buf = io.StringIO()
        with redirect_stdout(buf):
            web = smw.MemoryWeb()
            recent = list(getattr(web, "nodes", {}) or {})[-2:]
            created = []
            prev = None
            contents = [f"research topic: {topic}"] + \
                       [f"research fragment: {t}" for t in texts]
            for i, content in enumerate(contents):
                connections = recent if i == 0 else \
                    ([prev] if prev else None)
                node = web.remember(
                    content=content,
                    node_type="research_topic" if i == 0
                    else "research_fragment",
                    emotional_weight=0.2,
                    intensity=0.5,
                    tags=["research", "knowledge_outcomes"],
                    connections=connections,
                )
                node_id = getattr(node, "id", None)
                if node_id:
                    created.append(node_id)
                    prev = node_id
            try:
                web.save()
            except Exception:
                pass
        return len(created)
    except Exception:
        return 0


# ───────────────────── queen_knowledge consult (W6) ────────────────────────

def consult(topic_tokens: list[str], limit: int = 5) -> list[dict]:
    """Decision-feedback read of the queen_knowledge rows (W6).

    Matches the cycle's key tokens against each row's knowledge_type,
    topic and summary; returns up to ``limit`` rows ranked with scored
    rows first (a non-NULL success_rate means the knowledge stood up to
    application), then times_applied (most-applied first), then
    success_rate — what the corpus already learned about the matter at
    hand. Read-only; fail-closed: any DB error yields [].
    """
    conn = get_history_db()
    tokens = [str(t).strip().lower() for t in (topic_tokens or [])
              if str(t).strip()]
    if conn is None or not tokens:
        return []
    try:
        rows = []
        for row in conn.execute(
                "SELECT knowledge_id, knowledge_type, topic, summary, source,"
                " confidence, success_rate, times_applied, ts_ms"
                " FROM queen_knowledge"):
            haystack = " ".join(str(row[k] or "") for k in
                                ("knowledge_type", "topic", "summary")).lower()
            matched = [t for t in tokens if t in haystack]
            if not matched:
                continue
            rows.append({
                "knowledge_id": row["knowledge_id"],
                "knowledge_type": row["knowledge_type"],
                "topic": row["topic"],
                "summary": str(row["summary"] or "")[:200],
                "source": row["source"],
                "confidence": row["confidence"],
                "success_rate": row["success_rate"],
                "times_applied": row["times_applied"],
                "matched_tokens": matched,
            })
        # Scored rows outrank unscored ones — when a token matches both a
        # row that carried a real success signal and one that never did,
        # the queen should hear the one that stood up to application first.
        rows.sort(key=lambda r: (0 if r["success_rate"] is not None else 1,
                                 -(r["times_applied"] or 0),
                                 -(float(r["success_rate"])
                                   if r["success_rate"] is not None else -1.0)))
        return rows[:max(1, int(limit))]
    except Exception:
        return []


# ───────────────────────── trade-journal sweep ─────────────────────────────

def _load_seen_keys() -> list:
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(k) for k in data if k]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def _load_last_sweep() -> dict:
    try:
        data = json.loads(LAST_SWEEP_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _outcome_for_key(key: str) -> tuple | None:
    """Map one trade-journal dedupe key to (knowledge_type, summary, raw).

    Key shapes (trade_journal._collect_events) — the embedded timestamp
    contains colons, so fields are resolved from the edges, not positions:
      sig:    sig:<file>:<idx>:<ts>:<symbol>:<side>   (symbol/side last)
      ledger: ledger:<file>:<idx>:<audit_id>          (audit_id = the tail)
    Anything else is skipped — the sweep state carries no P&L or fill
    outcome, so every row is a usage outcome with provenance in the summary.
    """
    parts = key.split(":")
    if parts[0] == "sig" and len(parts) >= 5:
        fname = parts[1]
        symbol, side = parts[-2], parts[-1]
        ktype = "trade_journal_signal"
        detail = f"{side} {symbol} signal from {fname}"
    elif parts[0] == "ledger" and len(parts) >= 3:
        fname = parts[1]
        audit_id = ":".join(parts[2:]) or "unknown"
        ktype = "trade_journal_execution"
        detail = f"ledger event {audit_id} from {fname}"
    else:
        return None
    summary = (f"trade journal sweep journaled one {detail} into sero "
               f"memory (dedupe key {key!r}); sweep state carries no "
               f"P&L/fill outcome — usage outcome only, success not scored")
    return ktype, summary, {"seen_key": key, "provenance": str(SEEN_PATH)}


def sweep() -> dict:
    """Fold the trade-journal sweep state into queen_knowledge outcome rows.

    One usage outcome per journaled entry in trade_journal_seen.json.
    Re-running is honest: times_applied counts each fold. Fail-closed —
    a missing engine or state file yields zero rows, never an exception.
    """
    seen = _load_seen_keys()
    last = _load_last_sweep()
    recorded, skipped = 0, 0
    for key in seen:
        parsed = _outcome_for_key(key)
        if parsed is None:
            skipped += 1
            continue
        ktype, summary, raw = parsed
        if upsert_outcome(ktype, summary, None, topic="trade_journal",
                          source="aureon_fusion.trade_journal", raw=raw):
            recorded += 1
        else:
            skipped += 1
    return {
        "swept_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seen_entries": len(seen),
        "recorded": recorded,
        "skipped": skipped,
        "last_sweep": {
            "swept_at": last.get("swept_at"),
            "events_seen": last.get("events_seen"),
            "remembered": last.get("remembered"),
            "degraded": last.get("degraded", False),
        },
        "db": str(HISTORY_DB_PATH),
        "honest_note": ("sweep state holds dedupe keys only — no success "
                        "signal; rows are usage outcomes with success_rate "
                        "left NULL"),
    }


def status() -> dict:
    """Row counts by knowledge_type (empty/degraded honestly reported)."""
    conn = get_history_db()
    counts: list = []
    total = 0
    if conn is not None:
        try:
            counts = [{"knowledge_type": r["knowledge_type"],
                       "rows": r["n"],
                       "times_applied_total": r["applied"],
                       "scored_rows": r["scored"]}
                      for r in conn.execute(
                          "SELECT knowledge_type, COUNT(*) AS n,"
                          " SUM(times_applied) AS applied,"
                          " SUM(CASE WHEN success_rate IS NOT NULL"
                          " THEN 1 ELSE 0 END) AS scored"
                          " FROM queen_knowledge GROUP BY knowledge_type"
                          " ORDER BY n DESC")]
            total = sum(c["rows"] for c in counts)
        except Exception:
            counts, total = [], 0
    return {"db": str(HISTORY_DB_PATH), "total_rows": total,
            "by_type": counts, "db_available": conn is not None}


def research_status() -> dict:
    """The last 10 research_topic outcome rows, newest first (empty when
    the research faculty has not recorded anything yet — honest, never
    raises)."""
    conn = get_history_db()
    rows: list = []
    if conn is not None:
        try:
            rows = [{
                "knowledge_id": r["knowledge_id"],
                "topic": r["topic"],
                "summary": str(r["summary"] or "")[:220],
                "success_rate": r["success_rate"],
                "times_applied": r["times_applied"],
                "ts_ms": r["ts_ms"],
            } for r in conn.execute(
                "SELECT knowledge_id, topic, summary, success_rate,"
                " times_applied, ts_ms FROM queen_knowledge"
                " WHERE knowledge_type = 'research_topic'"
                " ORDER BY ts_ms DESC LIMIT 10")]
        except Exception:
            rows = []
    return {"db": str(HISTORY_DB_PATH), "research_rows": rows,
            "count": len(rows), "db_available": conn is not None}


# ─────────────────────────────── CLI ───────────────────────────────────────

def _print_json(payload) -> None:
    try:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    except UnicodeEncodeError:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    verb = argv[0] if argv else "status"
    if verb in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if verb == "sweep":
        result = sweep()
        _print_json(result)
        return 0 if result["recorded"] or result["seen_entries"] == 0 else 1
    if verb == "status":
        _print_json(status())
        return 0
    if verb == "research":
        _print_json(research_status())
        return 0
    print(f"unknown verb: {verb} (expected sweep|status|research)",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
