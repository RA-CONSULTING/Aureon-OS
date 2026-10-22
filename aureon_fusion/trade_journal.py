"""📒 Trade Journal — Sero remembers the trades.

Watches the radar trading layer and appends significant trading events
(signals AND executions, when present) into sero_memory_web via
sero_memory_web.remember() so the consciousness stack retains a memory
of what the trading organ did.

Sources (workspace aureon_radar/, whichever exist):
  fused_signals.jsonl          — fused gate signals (raw field carries
                                 execution markers like "OPENED"/"BLOCKED")
  aureon_bridge_signals.jsonl  — bridge/cross-market signals
  trade_ledger.jsonl           — order lifecycle (stages incl. ORDER_SENT,
                                 SHADOW_HIT, ORDER_FAILED) with P&L when known
  live_trades.jsonl            — live fills (empty while capital stays pinned)

Persistence + dedupe:
  - one memory node per new event, deduped by signal id/timestamp key in
    aureon_fusion/state/trade_journal_seen.json (survives restarts)
  - node_type 'trade'; emotional_weight by P&L sign when available
    (profit > 0, loss < 0), else derived from signal confidence
  - sero_memory_web is a LAZY import: if the engine is unavailable the
    sweep reports degraded and writes nothing.

CLI:  once    — single sweep, prints what was remembered/skipped
      status  — seen-set size + last sweep summary
Import-safe: no process spawns, no network.
"""

import json
import sys
import time
from pathlib import Path

from .paths import WORKSPACE, AUREON_RADAR, FUSION_STATE

SEEN_FILE = FUSION_STATE / "trade_journal_seen.json"
LAST_SWEEP = FUSION_STATE / "trade_journal_last_sweep.json"

_SIGNAL_FILES = ("fused_signals.jsonl", "aureon_bridge_signals.jsonl")
_LEDGER_FILES = ("trade_ledger.jsonl", "live_trades.jsonl")
_SIGNAL_CONF_THRESHOLD = 0.5
_BLOCK_MARKERS = ("BLOCKED", "REJECTED", "FAILED", "CANCELLED")
_EXEC_MARKERS = ("EXECUTED", "FILLED", "ORDER_SENT", "OPENED", "POSITION OPEN")
_SEEN_CAP = 5000


# ───────────────────────────── helpers ─────────────────────────────────────

def _read_jsonl(path: Path):
    entries = []
    try:
        if not path.exists():
            return entries
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if isinstance(e, dict):
                    entries.append(e)
    except Exception:
        pass
    return entries


def _load_seen() -> set:
    try:
        if SEEN_FILE.exists():
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return set(data)
    except Exception:
        pass
    return set()


def _save_seen(seen: set):
    try:
        FUSION_STATE.mkdir(parents=True, exist_ok=True)
        items = sorted(seen)[-_SEEN_CAP:]
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=1)
    except Exception:
        pass


def _is_execution_signal(e: dict) -> bool:
    raw = str(e.get("raw") or "").upper()
    if any(m in raw for m in _BLOCK_MARKERS):
        return False
    return any(m in raw for m in _EXEC_MARKERS)


def _pnl_weight(pnl) -> float:
    """emotional_weight by P&L sign when available."""
    try:
        if pnl is None:
            return 0.0
        pnl = float(pnl)
    except (TypeError, ValueError):
        return 0.0
    return max(-1.0, min(1.0, pnl / 10.0))


def _collect_events():
    """Yield (dedupe_key, content, emotional_weight, intensity, tags) for
    every significant event not yet filtered out."""
    events = []

    # ── signals ──
    for name in _SIGNAL_FILES:
        path = AUREON_RADAR / name
        for idx, e in enumerate(_read_jsonl(path)):
            symbol = str(e.get("symbol") or "").strip()
            side = str(e.get("direction") or e.get("side") or "").strip()
            ts = str(e.get("timestamp") or "")
            if not symbol or not side:
                continue
            exec_marked = _is_execution_signal(e)
            conf = e.get("confidence")
            try:
                conf = float(conf) if conf is not None else None
            except (TypeError, ValueError):
                conf = None
            # significance gate: executions always count; signals need conf
            if not exec_marked and (conf is None or conf < _SIGNAL_CONF_THRESHOLD):
                continue
            key = f"sig:{name}:{idx}:{ts}:{symbol}:{side}"
            kind = "EXECUTION" if exec_marked else "signal"
            # n=<idx> + ts= tokens keep Jaccard similarity between sibling
            # signals below the engine's 0.7 merge threshold, so each new
            # signal gets its own node instead of folding into a recurrence
            content = (f"trade {kind}: {side} {symbol} "
                       f"conf={conf if conf is not None else '?'} "
                       f"src={e.get('source', '?')} ts={ts} n={idx} ref={name}")
            weight = _pnl_weight(e.get("pnl"))
            if weight == 0.0 and conf is not None:
                weight = round(conf - 0.5, 2)
            events.append((key, content, weight,
                           0.6 if exec_marked else 0.4,
                           ["trade", kind.lower(), symbol.lower()]))

    # ── ledger / live executions ──
    for name in _LEDGER_FILES:
        path = AUREON_RADAR / name
        for idx, e in enumerate(_read_jsonl(path)):
            ts = str(e.get("timestamp") or "")
            stage = str(e.get("stage") or e.get("event") or "EXECUTION")
            symbol = str(e.get("symbol") or "?")
            side = str(e.get("direction") or e.get("side") or "?")
            audit_id = str(e.get("audit_id") or e.get("deal_id") or ts)
            # idx keeps the key unique even when ts AND audit_id are both
            # missing — the previous key collapsed every such entry onto one
            # constant-string dedupe key and silently dropped all but the first
            key = f"ledger:{name}:{idx}:{audit_id}"
            pnl = e.get("pnl")
            weight = _pnl_weight(pnl)
            content = (f"trade execution: {side} {symbol} stage={stage} "
                       f"pnl={pnl if pnl is not None else 'n/a'} ts={ts} "
                       f"n={idx} ref={name}")
            events.append((key, content, weight, 0.7,
                           ["trade", "execution", stage.lower(),
                            symbol.lower()]))

    return events


def _remember_via_engine(events):
    """Lazy-import sero_memory_web and remember each event. Returns
    (remembered, node_ids, error); error is not None when degraded."""
    try:
        if str(WORKSPACE) not in sys.path:
            sys.path.insert(0, str(WORKSPACE))
        import io
        from contextlib import redirect_stdout

        import sero_memory_web as smw
        web = smw.MemoryWeb()
        remembered = 0
        node_ids = []
        last_node_id = None
        for _key, content, weight, intensity, tags in events:
            # the engine chatters on stdout at load; remember() itself is quiet
            buf = io.StringIO()
            with redirect_stdout(buf):
                node = web.remember(
                    content=content,
                    node_type="trade",
                    emotional_weight=weight,
                    intensity=intensity,
                    tags=tags,
                    # chain each trade event to the previously journaled node
                    # (W3) so the trade stream becomes a linked chain in the
                    # memory web instead of 5-edge-isolated nodes
                    connections=[last_node_id] if last_node_id else None,
                )
            remembered += 1
            node_ids.append(getattr(node, "id", None))
            last_node_id = getattr(node, "id", None) or last_node_id
        with redirect_stdout(io.StringIO()):
            web.save()
        return remembered, node_ids, None
    except Exception as e:
        return 0, [], str(e)


# ───────────────────────────── sweep ───────────────────────────────────────

def sweep_once() -> dict:
    """Single journal sweep. Remembers each new significant event exactly
    once (dedupe by signal id/timestamp key in the seen-set)."""
    seen = _load_seen()
    all_events = _collect_events()
    new_events = [ev for ev in all_events if ev[0] not in seen]

    result = {
        "swept_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "events_seen": len(all_events),
        "already_journaled": len(all_events) - len(new_events),
        "new_events": len(new_events),
        "remembered": 0,
        "degraded": False,
    }

    if new_events:
        remembered, node_ids, error = _remember_via_engine(new_events)
        result["remembered"] = remembered
        if error is not None:
            result["degraded"] = True
            result["error"] = error
        else:
            seen.update(key for key, *_ in new_events)
            _save_seen(seen)

    try:
        FUSION_STATE.mkdir(parents=True, exist_ok=True)
        with open(LAST_SWEEP, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return result


def status() -> str:
    seen = _load_seen()
    last = {}
    try:
        if LAST_SWEEP.exists():
            with open(LAST_SWEEP, "r", encoding="utf-8") as f:
                last = json.load(f)
    except Exception:
        pass
    lines = ["═" * 72, "📒 TRADE JOURNAL STATUS", "═" * 72]
    lines.append(f"  journaled events (seen-set): {len(seen)}")
    if last:
        lines.append(f"  last sweep: {last.get('swept_at')} "
                     f"new={last.get('new_events')} remembered={last.get('remembered')}"
                     + ("  [DEGRADED: " + str(last.get("error")) + "]"
                        if last.get("degraded") else ""))
    else:
        lines.append("  no sweep recorded yet — run: python -m aureon_fusion.trade_journal once")
    lines.append("═" * 72)
    return "\n".join(lines)


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    verb = argv[0] if argv else "status"
    if verb in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.trade_journal [once|status]")
        return 0
    if verb == "once":
        res = sweep_once()
        print(f"trade journal sweep @ {res['swept_at']}")
        print(f"  events seen: {res['events_seen']} | already journaled: {res['already_journaled']} "
              f"| new: {res['new_events']} | remembered: {res['remembered']}")
        if res.get("degraded"):
            print(f"  ⚠ DEGRADED (sero_memory_web unavailable): {res.get('error')}")
        return 0 if not res.get("degraded") else 1
    if verb == "status":
        print(status())
        return 0
    print(f"unknown verb: {verb} (expected once|status)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
