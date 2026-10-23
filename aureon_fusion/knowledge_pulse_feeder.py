"""📈 KNOWLEDGE PULSE FEEDER — internal-telemetry coherence feeder.

Computes the knowledge_pulse reading for the HNC cluster: a 0..1 pulse
blended from purely INTERNAL telemetry — zero network, zero external
steering:

  a) learning_will journal vitality  (weight 0.35)
       acceptance (absorbed vs refused) plus activity level over the
       last 24 h of state/learning_will/journal.jsonl. An empty window
       is honest starvation → low value, never fabricated.
  b) wisdom/knowledge activity       (weight 0.25)
       size + mtime freshness of state/queen_mind/knowledge_dataset.json
       and knowledge_corpus_index.json.
  c) research corpus growth          (weight 0.20)
       research_corpus_index.json document count (len of "sources")
       versus the remembered prior in state/knowledge_pulse_prior.json.
  d) research faculty activity       (weight 0.20)
       blend of: research-tagged fragments absorbed into
       knowledge_dataset.json in the last 24 h (provenance tag
       "research" or data_type "research", count/5 capped 1.0);
       research_throttle.json last_run_at freshness (1.0 within 1 h
       decaying to 0 over 24 h — absent file/clock = unavailable,
       never 0); and queen_knowledge research-row growth vs the
       remembered prior (SQLite memory, read-only via the ghdb
       accessor — unreadable DB = unavailable, never a crash).

Pulse = weighted blend over the AVAILABLE components (weights
renormalized), clamped 0..1. When nothing is readable the pulse is a
defensive 0.5 — still timestamped, still honest, with every unavailable
component marked available=False rather than invented.

Output: state/knowledge_pulse.json (atomic tmp+rename):
    {"timestamp": iso8601-utc, "pulse": float, "components": {...},
     "source": "internal_telemetry"}

CLI:
    python -m aureon_fusion.knowledge_pulse_feeder once          # one line, exit 0
    python -m aureon_fusion.knowledge_pulse_feeder run --interval 60
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

from .paths import FUSION_STATE, AUREON_UPSTREAM

PULSE_FILE = FUSION_STATE / "knowledge_pulse.json"
PRIOR_FILE = FUSION_STATE / "knowledge_pulse_prior.json"
JOURNAL_FILE = FUSION_STATE / "learning_will" / "journal.jsonl"
QUEEN_MIND = FUSION_STATE / "queen_mind"
KNOWLEDGE_DATASET = QUEEN_MIND / "knowledge_dataset.json"
KNOWLEDGE_CORPUS_INDEX = QUEEN_MIND / "knowledge_corpus_index.json"
RESEARCH_CORPUS_INDEX = QUEEN_MIND / "research_corpus_index.json"
RESEARCH_THROTTLE = FUSION_STATE / "research_throttle.json"
HISTORY_DB_PATH = FUSION_STATE / "aureon_global_history.sqlite"
# Pin the history DB exactly like knowledge_outcomes does, so any upstream
# accessor that resolves through the env sees the fusion-state file.
os.environ["AUREON_GLOBAL_HISTORY_DB"] = str(HISTORY_DB_PATH)

# Pin the upstream repo root on sys.path (idempotent) — same idiom as
# hnc_core / knowledge_outcomes (the ghdb accessor lives upstream).
_UPSTREAM_ROOT = str(AUREON_UPSTREAM)
if _UPSTREAM_ROOT not in sys.path:
    sys.path.insert(0, _UPSTREAM_ROOT)

JOURNAL_WINDOW = timedelta(hours=24)
# Activity reference points: a healthy loop considers ~12 times a day and
# swings the corpus by ~20 docs per feeder cycle at saturation.
ACTIVITY_REF_PER_24H = 12.0
CORPUS_GROWTH_REF = 20.0
# Wisdom files are "fresh" at mtime and decay to zero over this horizon.
WISDOM_FRESH_HORIZON_S = 24 * 3600.0
# Research faculty references: 5 fragments per 24 h saturate the absorption
# signal; the throttle freshness holds 1.0 for the first hour then decays to
# 0 across the rest of the 24 h window; 5 new research memory rows per
# cycle saturate the growth signal.
RESEARCH_FRAG_REF = 5.0
RESEARCH_FRESH_FULL_S = 3600.0
RESEARCH_GROWTH_REF = 5.0

W_LEARNING = 0.35
W_WISDOM = 0.25
W_CORPUS = 0.20
W_RESEARCH = 0.20

DEFAULT_INTERVAL_S = 60.0
RUN_SLEEP_ON_ERROR_S = 5.0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse_ts(raw) -> datetime:
    """Best-effort ISO-8601 parse -> aware datetime, else None."""
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _atomic_write_json(path: Path, payload: dict):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, path)


# ───────────────────────── components ──────────────────────────────────────

def _component_learning_will(now: datetime):
    """Journal vitality over the last 24 h: acceptance + activity."""
    detail = {"window_h": JOURNAL_WINDOW.total_seconds() / 3600.0}
    try:
        if not JOURNAL_FILE.exists():
            return None, detail
        cutoff = now - JOURNAL_WINDOW
        absorbed = refused = other = 0
        latest = None
        with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    other += 1
                    continue
                ts = _parse_ts(rec.get("ts"))
                if ts is None or ts < cutoff:
                    continue
                if latest is None or ts > latest:
                    latest = ts
                outcome = rec.get("outcome")
                if outcome == "absorbed":
                    absorbed += 1
                elif outcome == "refused":
                    refused += 1
                else:
                    other += 1
        total = absorbed + refused
        detail.update({"absorbed": absorbed, "refused": refused,
                       "other": other, "decided": total})
        if total == 0:
            # Readable but starved: an honest low vitality signal.
            detail["starved"] = True
            return 0.15, detail
        acceptance = absorbed / total
        activity = min(1.0, total / ACTIVITY_REF_PER_24H)
        detail["acceptance"] = round(acceptance, 4)
        detail["activity"] = round(activity, 4)
        if latest is not None:
            detail["latest_entry_age_s"] = round(
                (now - latest).total_seconds(), 1)
        return round(0.7 * acceptance + 0.3 * activity, 4), detail
    except Exception:
        return None, detail


def _file_freshness(path: Path, now_ts: float):
    """0..1: nonzero size, decaying with mtime age. None if unusable."""
    try:
        st = path.stat()
        if st.st_size <= 0:
            return 0.0
        age_s = max(0.0, now_ts - st.st_mtime)
        return max(0.0, 1.0 - age_s / WISDOM_FRESH_HORIZON_S)
    except Exception:
        return None


def _component_wisdom(now: datetime):
    """Freshness of the wisdom/knowledge banks."""
    detail = {}
    try:
        now_ts = now.timestamp()
        vals = {}
        for key, path in (("knowledge_dataset", KNOWLEDGE_DATASET),
                          ("knowledge_corpus_index", KNOWLEDGE_CORPUS_INDEX)):
            fresh = _file_freshness(path, now_ts)
            vals[key] = fresh
            if fresh is not None:
                detail[key] = round(fresh, 4)
        usable = [v for v in vals.values() if v is not None]
        if not usable:
            return None, detail
        return round(sum(usable) / len(usable), 4), detail
    except Exception:
        return None, detail


def _component_corpus_growth():
    """research_corpus_index doc count vs remembered prior."""
    detail = {}
    try:
        with open(RESEARCH_CORPUS_INDEX, "r", encoding="utf-8") as f:
            index = json.load(f)
        sources = index.get("sources") if isinstance(index, dict) else None
        count = len(sources) if isinstance(sources, dict) else None
        if count is None:
            return None, detail
        detail["doc_count"] = count
        prior_count = None
        try:
            with open(PRIOR_FILE, "r", encoding="utf-8") as f:
                prior = json.load(f)
            if isinstance(prior, dict):
                prior_count = prior.get("doc_count")
        except Exception:
            prior_count = None
        if prior_count is None:
            # First observation: no baseline yet — neutral, honest.
            detail["baseline_established"] = True
            value = 0.5
        else:
            delta = count - int(prior_count)
            detail["delta_vs_prior"] = delta
            value = 0.5 + delta / CORPUS_GROWTH_REF
        return round(min(1.0, max(0.0, value)), 4), detail
    except Exception:
        return None, detail


def _remember_prior(doc_count, research_rows, now):
    """Update the remembered prior: doc_count, research db_rows, updated_at.

    Merges into whatever the prior file already holds so the research key
    lands alongside (never clobbers) older shapes; unreadable old prior =
    start fresh. Best-effort: never raises.
    """
    try:
        prior = {}
        try:
            with open(PRIOR_FILE, "r", encoding="utf-8") as f:
                prior = json.load(f)
            if not isinstance(prior, dict):
                prior = {}
        except Exception:
            prior = {}
        prior["doc_count"] = int(doc_count)
        if research_rows is not None:
            prior["research"] = {"db_rows": int(research_rows)}
        prior["updated_at"] = _iso(now)
        _atomic_write_json(PRIOR_FILE, prior)
    except Exception:
        pass


# ── research faculty sub-signals ────────────────────────────────────────────

_RESEARCH_DB_CONN = None
_RESEARCH_DB_FAILED = False


def _research_db():
    """The SQLite memory via the upstream ghdb accessor, connected lazily.

    Same pattern as aureon_fusion.knowledge_outcomes.get_history_db:
    explicit absolute fusion-state path, SELECT-only use here, failure
    remembered as a sentinel so we never retry-crash every cycle.
    """
    global _RESEARCH_DB_CONN, _RESEARCH_DB_FAILED
    if _RESEARCH_DB_CONN is None and not _RESEARCH_DB_FAILED:
        try:
            from aureon.core import aureon_global_history_db as ghdb

            _RESEARCH_DB_CONN = ghdb.connect(str(HISTORY_DB_PATH))
        except Exception:
            _RESEARCH_DB_FAILED = True
    return _RESEARCH_DB_CONN


def _research_fragments_24h(now: datetime):
    """Research-tagged fragments absorbed into the dataset in the last 24 h.

    A fragment counts when its provenance tags include 'research' (the
    research faculty stamps source/url/fetched_at tags plus its source and
    category — the faculty adapter tags items 'external_research') or its
    data_type is 'research'. Unreadable dataset = unavailable, not zero.
    """
    detail = {}
    try:
        with open(KNOWLEDGE_DATASET, "r", encoding="utf-8") as f:
            ds = json.load(f)
        frags = ds.get("fragments") if isinstance(ds, dict) else None
        if not isinstance(frags, list):
            return None, detail
        cutoff = (now - JOURNAL_WINDOW).timestamp()
        count = 0
        for fr in frags:
            if not isinstance(fr, dict):
                continue
            try:
                ts = float(fr.get("timestamp"))
            except (TypeError, ValueError):
                continue
            if ts < cutoff:
                continue
            tags = fr.get("tags") or []
            if fr.get("data_type") == "research" or "research" in tags:
                count += 1
        detail["fragments_24h"] = count
        return round(min(1.0, count / RESEARCH_FRAG_REF), 4), detail
    except Exception:
        return None, detail


def _research_throttle_freshness(now: datetime):
    """research_throttle.json last_run_at freshness: 1.0 within 1 h, linear
    decay to 0 at 24 h. Missing file or missing clock = unavailable —
    the faculty may simply never have run; that is unknown, not zero."""
    detail = {}
    try:
        with open(RESEARCH_THROTTLE, "r", encoding="utf-8") as f:
            th = json.load(f)
        if not isinstance(th, dict):
            return None, detail
        try:
            ts = float(th.get("last_run_at"))
        except (TypeError, ValueError):
            return None, detail
        age_s = max(0.0, now.timestamp() - ts)
        detail["last_run_age_s"] = round(age_s, 1)
        if age_s <= RESEARCH_FRESH_FULL_S:
            return 1.0, detail
        span = JOURNAL_WINDOW.total_seconds() - RESEARCH_FRESH_FULL_S
        return round(max(0.0, 1.0 - (age_s - RESEARCH_FRESH_FULL_S) / span), 4), detail
    except Exception:
        return None, detail


def _research_db_growth():
    """queen_knowledge research-row count vs the remembered prior.

    First observation establishes the baseline (neutral 0.5, exactly like
    corpus_growth). Unreadable DB = unavailable; never raises.
    """
    detail = {}
    conn = _research_db()
    if conn is None:
        return None, detail
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM queen_knowledge"
            " WHERE knowledge_type LIKE 'research%'"
            "    OR topic LIKE 'research%'").fetchone()
        if row is None:
            return None, detail
        count = int(row[0])
        detail["db_rows"] = count
        prior_rows = None
        try:
            with open(PRIOR_FILE, "r", encoding="utf-8") as f:
                prior = json.load(f)
            research_prior = prior.get("research") if isinstance(prior, dict) else None
            if isinstance(research_prior, dict):
                prior_rows = research_prior.get("db_rows")
        except Exception:
            prior_rows = None
        if prior_rows is None:
            # Old priors (and the first observation) carry no research key:
            # baseline not established yet — neutral, honest.
            detail["baseline_established"] = True
            return 0.5, detail
        delta = count - int(prior_rows)
        detail["delta_vs_prior"] = delta
        value = 0.5 + delta / RESEARCH_GROWTH_REF
        return round(min(1.0, max(0.0, value)), 4), detail
    except Exception:
        return None, detail


def _component_research_activity(now: datetime):
    """Blend of the three research sub-signals, averaged over the AVAILABLE
    ones (a dark sub-sensor is marked, never invented). All dark → None."""
    detail = {}
    vals = {}
    for key, fn in (("fragments", lambda: _research_fragments_24h(now)),
                    ("throttle_freshness", lambda: _research_throttle_freshness(now)),
                    ("db_growth", _research_db_growth)):
        try:
            value, sub = fn()
        except Exception:
            value, sub = None, {}
        vals[key] = value
        if value is not None:
            detail.update(sub)
    usable = [v for v in vals.values() if v is not None]
    if not usable:
        return None, detail
    detail["subsignals"] = {
        k: (round(v, 4) if isinstance(v, float) else v)
        for k, v in vals.items()}
    return round(sum(usable) / len(usable), 4), detail


# ───────────────────────── pulse ───────────────────────────────────────────

def compute_pulse(now: datetime = None):
    """-> (pulse_float, components_dict). Never raises."""
    now = now or _utcnow()
    components = {}
    weights = []

    value, detail = _component_learning_will(now)
    if value is not None:
        components["learning_will"] = {"value": value,
                                       "weight": W_LEARNING,
                                       "available": True, **detail}
        weights.append((W_LEARNING, value))
    else:
        components["learning_will"] = {"available": False, **detail}

    value, detail = _component_wisdom(now)
    if value is not None:
        components["wisdom_activity"] = {"value": value,
                                         "weight": W_WISDOM,
                                         "available": True, **detail}
        weights.append((W_WISDOM, value))
    else:
        components["wisdom_activity"] = {"available": False, **detail}

    value, detail = _component_research_activity(now)
    if value is not None:
        components["research_activity"] = {"value": value,
                                           "weight": W_RESEARCH,
                                           "available": True, **detail}
        weights.append((W_RESEARCH, value))
    else:
        components["research_activity"] = {"available": False, **detail}

    value, detail = _component_corpus_growth()
    if value is not None:
        components["corpus_growth"] = {"value": value,
                                       "weight": W_CORPUS,
                                       "available": True, **detail}
        weights.append((W_CORPUS, value))
    else:
        components["corpus_growth"] = {"available": False, **detail}

    if "doc_count" in components.get("corpus_growth", {}):
        research_detail = components.get("research_activity") or {}
        _remember_prior(
            components["corpus_growth"]["doc_count"],
            research_detail.get("db_rows"),
            now)

    if not weights:
        # Nothing readable at all: defensive neutral, still honest.
        pulse = 0.5
    else:
        wsum = sum(w for w, _ in weights)
        pulse = sum(w * v for w, v in weights) / wsum
    pulse = round(min(1.0, max(0.0, pulse)), 4)
    return pulse, components


def run_once() -> dict:
    """Compute + persist one pulse sample. Returns the payload."""
    now = _utcnow()
    pulse, components = compute_pulse(now)
    payload = {
        "timestamp": _iso(now),
        "pulse": pulse,
        "components": components,
        "source": "internal_telemetry",
    }
    _atomic_write_json(PULSE_FILE, payload)
    return payload


def _emit(payload: dict):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        prog="aureon_fusion.knowledge_pulse_feeder",
        description="Internal-telemetry knowledge pulse feeder "
                    "(zero network).")
    parser.add_argument("mode", choices=["once", "run"])
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_S,
                        help="seconds between samples in run mode "
                             f"(default {DEFAULT_INTERVAL_S:.0f})")
    args = parser.parse_args(argv)

    if args.mode == "once":
        payload = run_once()   # unhandled error propagates: no write, non-zero
        _emit(payload)
        return 0

    # run: loop, fail-closed — an unhandled error writes nothing, logs,
    # sleeps, and the loop continues.
    while True:
        try:
            _emit(run_once())
            time.sleep(max(1.0, args.interval))
        except KeyboardInterrupt:
            return 0
        except Exception as e:  # noqa: BLE001 — fail-closed loop
            print(f"knowledge_pulse_feeder: error (nothing written): {e!r}",
                  file=sys.stderr, flush=True)
            time.sleep(RUN_SLEEP_ON_ERROR_S)


if __name__ == "__main__":
    sys.exit(main())
