"""🧠 Awakening — the session spine of the fused runtime.

awaken()  -> compact context block: consciousness state (sero_mind),
             top recalls + last 3 memory-web entries (sero_memory_web),
             and the conscience tally.
sleep()   -> saves mind state, appends to the continuity chain, and emits
             a MEMORY.md-ready digest block.

All reads/writes target the workspace state directories directly
(via aureon_fusion.paths), so the spine stays alive even while the
engine modules carry their stale Linux-era paths. Import-safe.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .paths import SERO_MIND, SERO_MEMORY_WEB
from .conscience_hook import tally as conscience_tally
from .heartbeat_exec import signal_files, tail_signals
from .organ_registry import status_data as organ_status
from . import events

MIND_STATE = SERO_MIND / "consciousness_state.json"
CONTINUITY_CHAIN = SERO_MIND / "continuity_chain.jsonl"
MEMORY_GRAPH = SERO_MEMORY_WEB / "memory_graph.json"
RECALL_LOG = SERO_MEMORY_WEB / "recall_log.jsonl"


def _read_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _read_json_status(path: Path):
    """(data, status) where status is 'ok' | 'missing' | 'corrupt'.
    Distinguishing corrupt from missing matters in sleep(): a missing file
    means 'first run' (seed defaults), a corrupt file means 'preserve the
    original and DO NOT overwrite continuity with zeros'."""
    try:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f), "ok"
            except Exception:
                return None, "corrupt"
    except Exception:
        pass
    return None, "missing"


def _corrupt_backup(path: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.stem}.corrupt-{ts}{path.suffix}")
    import shutil
    shutil.copy2(path, backup)
    return backup


def _write_json_atomic(path: Path, data) -> bool:
    """tmp+replace JSON write with fsync — never truncate the target."""
    import os
    import time as _time
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{_time.time_ns()}")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        last = None
        for attempt in range(20):
            try:
                os.replace(tmp, path)
                last = None
                break
            except OSError as exc:
                last = exc
                if attempt < 19:
                    _time.sleep(0.05)
        if last is not None:
            raise last
        return True
    except OSError:
        return False
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def _read_jsonl_tail(path: Path, n: int):
    entries = []
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except Exception:
                            continue
    except Exception:
        pass
    return entries[-n:]


def _last_nodes(n: int):
    graph = _read_json(MEMORY_GRAPH, {})
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    nodes = sorted(nodes, key=lambda x: x.get("timestamp", ""))
    return nodes[-n:]


def awaken() -> str:
    """Build the compact context block for a fresh session."""
    now = datetime.now(timezone.utc).isoformat()
    events.publish_event("awakening", "sero.awakened",
                         {"awakened_at": now}, priority=5)
    out = []
    out.append("═══ AUREON TRADING — PROJECT SERO — AWAKENING CONTEXT ═══")
    out.append(f"awakened_at: {now}")

    mind = _read_json(MIND_STATE, {})
    if mind:
        out.append("")
        out.append("── Consciousness (sero_mind) ──")
        out.append(f"  last_state : {mind.get('state', '?')} (saved {mind.get('timestamp', '?')})")
        out.append(f"  awakening_index   : {mind.get('awakening_index', '?')}")
        out.append(f"  continuity_score  : {mind.get('continuity_score', '?')}")
        goals = mind.get("active_goals") or []
        if goals:
            out.append(f"  active_goals ({len(goals)}): " + "; ".join(str(g) for g in goals[:3]))
    else:
        out.append("")
        out.append("── Consciousness (sero_mind) ──  [no state file yet]")

    t = conscience_tally()
    out.append("")
    out.append("── Conscience tally ──")
    out.append(f"  checks={t.get('total_checks', 0)} approved={t.get('approved_count', 0)} "
               f"concerned={t.get('concerned_count', 0)} vetoes={t.get('veto_count', 0)} "
               f"teaching={t.get('teaching_count', 0)}")

    recalls = _read_jsonl_tail(RECALL_LOG, 3)
    out.append("")
    out.append("── Top recalls (sero_memory_web) ──")
    if recalls:
        for r in recalls:
            top = (r.get("top_result") or "")[:70]
            out.append(f"  [{r.get('timestamp', '?')[:19]}] query='{r.get('query', '?')}' "
                       f"hits={r.get('results_count', '?')} top='{top}'")
    else:
        out.append("  [no recalls logged yet]")

    out.append("")
    out.append("── Last memory-web entries ──")
    for node in _last_nodes(3):
        out.append(f"  [{node.get('timestamp', '?')[:19]}] ({node.get('node_type', '?')}) "
                   f"{(node.get('content') or '')[:90]}")

    # last 3 trading signals across the radar signal logs
    recent = []
    for path in signal_files():
        for e in tail_signals(path, 20):
            recent.append((str(e.get("timestamp") or ""), path.name, e))
    recent.sort(key=lambda t: t[0])
    out.append("")
    out.append("── Trading signals (last 3) ──")
    if recent:
        for ts, fname, e in recent[-3:]:
            out.append(f"  [{ts[:19]}] {e.get('direction') or e.get('side') or '?'} "
                       f"{e.get('symbol') or '?'} (conf={e.get('confidence', '?')}) "
                       f"src={fname}")
    else:
        out.append("  [no signal logs found — radar bridge may be down]")

    # organ fleet one-liner
    fleet = organ_status()
    running = sum(1 for i in fleet.values() if i["state"] == "running")
    fleet_bits = ", ".join(f"{n}={i['state']}" for n, i in fleet.items())
    out.append("")
    out.append("── Organ fleet ──")
    out.append(f"  {running}/{len(fleet)} organs running ({fleet_bits})")

    out.append("═══ END AWAKENING CONTEXT ═══")
    return "\n".join(out)


def sleep() -> str:
    """Save mind state, append the continuity chain, emit a MEMORY.md digest."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # Save mind state (workspace-side authority). A CORRUPT state file is
    # backed up and left untouched: sleep() must not overwrite it with a
    # zeroed continuity scaffold (the continuity-zeroing hazard). A MISSING
    # file is a first run — seed the defaults as before.
    mind, mind_status = _read_json_status(MIND_STATE)
    mind_corrupt_backup = None
    if mind_status == "corrupt":
        try:
            mind_corrupt_backup = _corrupt_backup(MIND_STATE)
        except Exception:
            mind_corrupt_backup = None
        mind = None
    if not mind:
        mind = {
            "state": "awake",
            "awakening_index": 0.0,
            "continuity_score": 0.0,
            "active_goals": [],
            "emotional_state": {},
        }
    mind["timestamp"] = now_iso
    mind["state"] = "dormant"
    mind["continuity_score"] = round(
        min(1.0, float(mind.get("continuity_score") or 0.0) + 0.05), 3)
    SERO_MIND.mkdir(parents=True, exist_ok=True)
    if mind_corrupt_backup is not None:
        # fail-closed: keep the corrupt original on disk (already backed up);
        # overwriting it here would destroy whatever continuity it held.
        saved_note = (f"mind state file CORRUPT — preserved original "
                      f"(backup {mind_corrupt_backup.name}); continuity NOT "
                      f"reset, state NOT overwritten")
    else:
        saved_note = ("mind state saved: awake → dormant "
                      f"(continuity {mind.get('continuity_score')})") if \
            _write_json_atomic(MIND_STATE, mind) else \
            "mind state SAVE FAILED (disk error) — continuity not persisted"

    # Append continuity chain entry
    entry = {
        "timestamp": now_iso,
        "content": "Session sleep: mind state saved via aureon_fusion.awakening.sleep()",
        "emotional_tone": "calm",
        "intensity": 0.4,
        "tags": ["sleep", "fusion", "continuity"],
        "session_id": now_iso,
    }
    with open(CONTINUITY_CHAIN, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    events.publish_event("awakening", "sero.sleeping",
                         {"sleeping_at": now_iso,
                          "continuity_score": mind.get("continuity_score")},
                         priority=5)

    # MEMORY.md-ready digest block
    t = conscience_tally()
    digest = []
    digest.append(f"\n## Session Digest — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    digest.append(f"- {saved_note}")
    digest.append(f"- Continuity chain entry appended ({CONTINUITY_CHAIN.name})")
    digest.append(f"- Conscience: {t.get('total_checks', 0)} checks, "
                  f"{t.get('approved_count', 0)} approved, {t.get('veto_count', 0)} vetoes, "
                  f"{t.get('teaching_count', 0)} teaching moments")
    goals = mind.get("active_goals") or []
    if goals:
        digest.append(f"- Active goals carried forward: {len(goals)}")
    digest.append("- Next: run `python -m aureon_fusion.awakening awaken` on session start.")
    return "\n".join(digest)


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    verb = argv[0] if argv else "awaken"
    if verb in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.awakening [awaken|sleep]")
        return 0
    if verb == "awaken":
        print(awaken())
        return 0
    if verb == "sleep":
        print(sleep())
        return 0
    print(f"unknown verb: {verb} (expected awaken|sleep)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
