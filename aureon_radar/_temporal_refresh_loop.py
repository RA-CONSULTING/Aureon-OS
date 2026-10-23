"""⏳ Temporal refresh orchestrator + prophecy resolver.

Cycles the temporal probes so Queen Sero's time sense stays fresh:
  1. multiverse_outlook.py   (quantum vacuum phasing, world consensus)
  2. harmonic_phase_probe.py (non-linear field phase)
  3. margin_eta_predictor.py (linear time-to-capture from real journals)
  4. temporal_cognition.py   (integrator + negative-close gate)

Each probe is launched as a subprocess in the shared env; a probe failure
is logged and does not stop the cycle (the integrator is fail-closed on
missing/stale inputs).

PROPHECY RESOLUTION (predict -> resolve -> re-evaluate):
  multiverse_outlook records every world's numeric claim into the bitemporal
  forecasts table (model 'multiverse_outlook', target = as_of + 30min). This
  loop step resolves each forecast whose target_ts_ms has PASSED against
  aureon_radar/state/price_cache_journal.jsonl — REAL price telemetry that
  other probes already recorded. No exchange calls, no keyed clients, no
  network: the resolver only reads local JSONL + SQLite.

  Outcome semantics (honest, never fabricated):
    hit               — price moved in the claimed direction by >= round-trip
                        cost (cost model: juice_gate.json / dreamt_plays.json,
                        else labeled 0.20% venue fallback)
    miss              — resolution price existed but the move did not clear
                        the threshold (includes moving the right way but
                        less than cost)
    expired-no-data   — no real journal telemetry for the symbol in the
                        resolution window; success stays None (usage only)

  Resolved outcomes fold into queen_knowledge via
  aureon_fusion.knowledge_outcomes.upsert_outcome (success=True/False feeds
  the running hit-rate mean per symbol/direction/horizon class;
  expired-no-data folds with success=None). A compact
  aureon_fusion/state/prophecy_summary.json is written every cycle for
  queen_mind: {ts, open, resolved_total, hit_rate, by_horizon,
  last_resolved, ...}.

  Slow cadence: every AUREON_SELF_BACKTEST_EVERY loops (default 50) the
  step also calls QueenMetacognition.self_backtest() upstream and records
  the score (aureon_fusion/state/metacognition_self_backtest.json), which
  is merged into prophecy_summary.

CLI:
    python _temporal_refresh_loop.py            # infinite loop (as before)
    python _temporal_refresh_loop.py --once     # one probe cycle + resolution
    python _temporal_refresh_loop.py --resolve-only
    python _temporal_refresh_loop.py --backtest # force one self-backtest now
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RADAR = Path(__file__).resolve().parent
WORKSPACE = RADAR.parent
UPSTREAM = WORKSPACE / "aureon-os-upstream"
FUSION_STATE = WORKSPACE / "aureon_fusion" / "state"
INTERVAL = int(os.getenv("TEMPORAL_REFRESH_INTERVAL", "120"))
PYTHON = sys.executable

PROPHECY_MODEL = "multiverse_outlook"
DB_PATH = Path(os.getenv("AUREON_PROPHECY_DB") or FUSION_STATE / "aureon_global_history.sqlite")
JOURNAL_PATH = RADAR / "state" / "price_cache_journal.jsonl"
SUMMARY_PATH = Path(os.getenv("AUREON_PROPHECY_SUMMARY") or FUSION_STATE / "prophecy_summary.json")
RESOLUTIONS_PATH = Path(os.getenv("AUREON_PROPHECY_RESOLUTIONS") or FUSION_STATE / "prophecy_resolutions.json")
BACKTEST_PATH = FUSION_STATE / "metacognition_self_backtest.json"
# Grace after target_ts_ms during which journal telemetry counts as the
# resolution print (the loop cycle is 120s; telemetry lands every ~120s).
GRACE_MS = int(float(os.getenv("AUREON_PROPHECY_GRACE_MIN", "30") or "30") * 60_000)
SELF_BACKTEST_EVERY = max(1, int(os.getenv("AUREON_SELF_BACKTEST_EVERY", "50") or "50"))
_COST_FALLBACK_PCT = 0.20   # labeled venue-cost estimate (same as dreamer)

PROBES = [
    ("multiverse", [str(RADAR / "multiverse_outlook.py")]),
    ("harmonic", [str(RADAR / "harmonic_phase_probe.py")]),
    ("ttc", [str(RADAR / "unified_margin_trader" / "margin_eta_predictor.py")]),
    ("sizing", [str(RADAR / "sizing_anatomy.py")]),
    ("juice", [str(RADAR / "juice_gate.py")]),
    ("dreamer", [str(RADAR / "play_dreamer.py")]),
    ("cognition", [str(RADAR / "temporal_cognition.py")]),
]


def run_probe(name: str, args: list[str], env: dict) -> tuple[bool, str]:
    try:
        p = subprocess.run(
            [PYTHON, *args],
            cwd=str(RADAR),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
        tail = (p.stdout or "").strip().splitlines()
        detail = tail[-1][:120] if tail else "(no output)"
        return p.returncode == 0, f"rc={p.returncode} {detail}"
    except subprocess.TimeoutExpired:
        return False, "timeout(90s)"
    except Exception as e:  # noqa: BLE001 - orchestrator must never die
        return False, f"{type(e).__name__}: {e}"


# ── prophecy resolver (predict -> resolve -> re-evaluate) ───────────────────

def _canon_symbol(sym: Any) -> str:
    """Canonical base for cross-source joins (BTCUSDT/BTCUSD/XBTUSD/BTC/USD -> BTC)."""
    s = re.sub(r"[^A-Z]", "", str(sym or "").upper())
    if s.startswith("XBT"):
        s = "BTC" + s[3:]
    for suf in ("USDT", "USD"):
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)]
            break
    return s


def _ts_ms(iso_ts: Any) -> Optional[int]:
    if not isinstance(iso_ts, str) or not iso_ts.strip():
        return None
    try:
        dt = datetime.fromisoformat(iso_ts.strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except (ValueError, OverflowError, OSError):
        return None


def _load_journal_prices() -> Dict[str, List[Tuple[int, float, str]]]:
    """Real price telemetry from price_cache_journal.jsonl, fail-closed.

    Returns {canonical_base: [(ts_ms, price, source), ...] sorted by ts_ms]}.
    Only fetch_ok rows with a numeric price; unparseable lines are skipped.
    Missing/corrupt journal -> {} (every due forecast then resolves as
    expired-no-data — never a fabricated price).
    """
    out: Dict[str, List[Tuple[int, float, str]]] = {}
    try:
        with open(JOURNAL_PATH, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("event") != "fetch_ok":
                    continue
                price = rec.get("price")
                if not isinstance(price, (int, float)) or not price:
                    continue
                ts_ms = _ts_ms(rec.get("ts"))
                if ts_ms is None:
                    continue
                base = _canon_symbol(rec.get("symbol"))
                if not base:
                    continue
                out.setdefault(base, []).append((ts_ms, float(price), str(rec.get("source") or "")))
    except OSError:
        return {}
    for rows in out.values():
        rows.sort(key=lambda r: r[0])
    return out


def _load_cost_model() -> Tuple[float, str]:
    """Round-trip cost pct: real sibling state first, labeled fallback last."""
    for path, keys in ((RADAR / "state" / "juice_gate.json",
                        ("candidate_cost_pct", "round_trip_cost_pct", "cost_pct")),
                       (RADAR / "state" / "dreamt_plays.json",
                        ("cost_model",))):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if "cost_model" in keys:
            v = (doc.get("cost_model") or {}).get("round_trip_pct")
            if isinstance(v, (int, float)) and v >= 0:
                return float(v), f"{path.name}:cost_model.round_trip_pct"
        else:
            for k in keys:
                v = doc.get(k)
                if isinstance(v, (int, float)) and v >= 0:
                    return float(v), f"{path.name}:{k}"
    return _COST_FALLBACK_PCT, "venue_cost_fallback (labeled estimate)"


def _load_json(path: Path, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return default


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _open_history_db():
    """Upstream global-history connection (WAL, busy-timeout). Fail-closed None."""
    try:
        upstream = str(UPSTREAM)
        if upstream not in sys.path:
            sys.path.insert(0, upstream)
        os.environ.setdefault("AUREON_GLOBAL_HISTORY_DB", str(DB_PATH))
        from aureon.core import aureon_global_history_db as ghdb

        return ghdb.connect(str(DB_PATH))
    except Exception:
        return None


def _fetch_due_forecasts(now_ms: int) -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
    """(due forecasts, open count, error). Due = target passed & not resolved."""
    resolved_ids = set((_load_json(RESOLUTIONS_PATH, {}) or {}).get("resolved") or {})
    conn = _open_history_db()
    if conn is None:
        return [], 0, f"history DB unavailable at {DB_PATH}"
    try:
        due: List[Dict[str, Any]] = []
        open_count = 0
        for row in conn.execute(
                "SELECT forecast_id, symbol, as_of_ts_ms, target_ts_ms, raw_json "
                "FROM forecasts WHERE model = ?", (PROPHECY_MODEL,)):
            fid = row["forecast_id"]
            if fid in resolved_ids:
                continue
            target_ms = row["target_ts_ms"]
            if target_ms is not None and int(target_ms) <= now_ms:
                raw = {}
                try:
                    raw = json.loads(row["raw_json"] or "{}")
                except (json.JSONDecodeError, TypeError):
                    raw = {}
                due.append({
                    "forecast_id": fid,
                    "symbol": row["symbol"],
                    "as_of_ts_ms": row["as_of_ts_ms"],
                    "target_ts_ms": int(target_ms),
                    "raw": raw,
                })
            else:
                open_count += 1
        return due, open_count, None
    except Exception as exc:
        return [], 0, f"forecast query failed: {type(exc).__name__}: {exc}"
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _resolve_one(fc: Dict[str, Any], journal: Dict[str, List[Tuple[int, float, str]]],
                 cost_pct: float) -> Dict[str, Any]:
    """Resolve one due forecast against real journal telemetry. Honest outcomes:
    hit / miss / expired-no-data. Never invents a price."""
    raw = fc.get("raw") or {}
    symbol = raw.get("symbol") or fc.get("symbol")
    direction = raw.get("direction")
    birth = raw.get("price_at_birth")
    as_of_ms = fc.get("as_of_ts_ms")
    target_ms = fc.get("target_ts_ms")
    horizon_min = raw.get("horizon_min")
    if not (isinstance(horizon_min, (int, float)) and horizon_min > 0):
        horizon_min = ((target_ms - as_of_ms) / 60_000.0
                       if isinstance(as_of_ms, int) and isinstance(target_ms, int)
                       and target_ms > as_of_ms else None)

    result: Dict[str, Any] = {
        "forecast_id": fc.get("forecast_id"),
        "ts": time.time(),
        "ts_iso": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "direction": direction,
        "horizon_min": horizon_min,
        "price_at_birth": birth,
        "outcome": None,
        "move_pct": None,
        "cost_pct": cost_pct,
        "resolution_price": None,
        "resolution_source": None,
    }

    if not symbol or direction not in ("up", "down") or not birth:
        result["outcome"] = "expired-no-data"
        result["reason"] = "forecast raw claim incomplete (symbol/direction/price_at_birth) — fail-closed"
        return result
    if not isinstance(as_of_ms, int) or not isinstance(target_ms, int):
        result["outcome"] = "expired-no-data"
        result["reason"] = "forecast timestamps missing — fail-closed"
        return result

    rows = journal.get(_canon_symbol(symbol)) or []
    window = [(t, p, s) for t, p, s in rows
              if as_of_ms < t <= target_ms + GRACE_MS]
    if not window:
        result["outcome"] = "expired-no-data"
        result["reason"] = (f"no real journal telemetry for {_canon_symbol(symbol)} "
                            f"in ({as_of_ms}, {target_ms + GRACE_MS}] — honest no-data")
        return result

    t_res, p_res, src = window[-1]
    try:
        move_pct = (p_res - float(birth)) / float(birth) * 100.0
    except (TypeError, ValueError, ZeroDivisionError):
        result["outcome"] = "expired-no-data"
        result["reason"] = "price_at_birth unusable — fail-closed"
        return result

    result["resolution_price"] = p_res
    result["resolution_source"] = src
    result["resolution_ts_ms"] = t_res
    result["move_pct"] = round(move_pct, 4)
    if direction == "up":
        hit = move_pct >= cost_pct
    else:
        hit = move_pct <= -cost_pct
    result["outcome"] = "hit" if hit else "miss"
    result["reason"] = (f"move {move_pct:+.4f}% vs round-trip cost {cost_pct:.2f}% "
                        f"({direction} claim) — {result['outcome']}")
    return result


def _fold_into_queen_knowledge(results: List[Dict[str, Any]]) -> int:
    """Fold resolutions into queen_knowledge via upsert_outcome semantics.

    One rolling row per (symbol, direction, horizon) class: success=True/False
    feeds the running mean (the class hit rate); expired-no-data folds with
    success=None (usage-only — success_rate untouched, never fabricated).
    """
    if not results:
        return 0
    try:
        ws = str(WORKSPACE)
        if ws not in sys.path:
            sys.path.insert(0, ws)
        os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
        os.environ.setdefault("AUREON_AUDIT_MODE", "1")
        from aureon_fusion.knowledge_outcomes import upsert_outcome

        folded = 0
        for r in results:
            outcome = r.get("outcome")
            success = True if outcome == "hit" else (False if outcome == "miss" else None)
            sym, direction = r.get("symbol"), r.get("direction")
            h = r.get("horizon_min")
            if not sym or not direction:
                continue
            summary = (f"prophecy {PROPHECY_MODEL} {sym} {direction} "
                       f"h={h}min — resolved against price_cache_journal "
                       f"(running class hit-rate row)")
            if upsert_outcome("prophecy_resolution", summary, success,
                              topic="prophecy",
                              source="aureon_radar._temporal_refresh_loop",
                              raw={"forecast_id": r.get("forecast_id"),
                                   "outcome": outcome,
                                   "move_pct": r.get("move_pct"),
                                   "cost_pct": r.get("cost_pct"),
                                   "truth_status": "resolved_real_telemetry"}):
                folded += 1
        return folded
    except Exception:
        return 0


def run_prophecy_resolution(now_ms: Optional[int] = None) -> Dict[str, Any]:
    """Resolve due forecasts -> ledger + queen_knowledge + prophecy_summary.json."""
    now_ms = int(now_ms if now_ms is not None else time.time() * 1000)
    errors: List[str] = []

    due, open_count, db_error = _fetch_due_forecasts(now_ms)
    if db_error:
        errors.append(db_error)

    ledger = _load_json(RESOLUTIONS_PATH, {}) or {}
    resolved_map: Dict[str, Any] = ledger.get("resolved") or {}

    journal = _load_journal_prices()
    if not journal:
        errors.append(f"price journal empty/unreadable at {JOURNAL_PATH} — "
                      f"due forecasts resolve as expired-no-data (fail-closed)")
    cost_pct, cost_source = _load_cost_model()

    new_results: List[Dict[str, Any]] = []
    for fc in due:
        r = _resolve_one(fc, journal, cost_pct)
        new_results.append(r)
        resolved_map[r["forecast_id"]] = r

    folded = _fold_into_queen_knowledge(new_results)

    ledger["resolved"] = resolved_map
    try:
        _atomic_write_json(RESOLUTIONS_PATH, ledger)
    except OSError as exc:
        errors.append(f"resolutions ledger write failed: {exc}")

    scored = [r for r in resolved_map.values() if r.get("outcome") in ("hit", "miss")]
    hits = sum(1 for r in scored if r.get("outcome") == "hit")
    by_horizon: Dict[str, Dict[str, Any]] = {}
    for r in resolved_map.values():
        h = r.get("horizon_min")
        key = f"{h:g}m" if isinstance(h, (int, float)) else "unknown"
        bucket = by_horizon.setdefault(key, {"resolved": 0, "hits": 0, "misses": 0,
                                             "expired_no_data": 0, "hit_rate": None})
        bucket["resolved"] += 1
        if r.get("outcome") == "hit":
            bucket["hits"] += 1
        elif r.get("outcome") == "miss":
            bucket["misses"] += 1
        else:
            bucket["expired_no_data"] += 1
        if bucket["hits"] + bucket["misses"]:
            bucket["hit_rate"] = round(bucket["hits"] / (bucket["hits"] + bucket["misses"]), 4)

    last_resolved = sorted(resolved_map.values(),
                           key=lambda r: r.get("ts") or 0, reverse=True)[:10]
    backtest = _load_json(BACKTEST_PATH, None)

    summary = {
        "ts": now_ms / 1000.0,
        "ts_iso": datetime.fromtimestamp(now_ms / 1000.0, timezone.utc).isoformat(),
        "model": PROPHECY_MODEL,
        "open": open_count,
        "due_this_cycle": len(due),
        "newly_resolved": len(new_results),
        "resolved_total": len(resolved_map),
        "resolved_scored": len(scored),
        "hits": hits,
        "misses": len(scored) - hits,
        "expired_no_data": len(resolved_map) - len(scored),
        "hit_rate": round(hits / len(scored), 4) if scored else None,
        "by_horizon": by_horizon,
        "last_resolved": [{k: r.get(k) for k in
                           ("forecast_id", "ts_iso", "symbol", "direction",
                            "horizon_min", "outcome", "move_pct", "cost_pct",
                            "reason")} for r in last_resolved],
        "cost_model": {"round_trip_pct": cost_pct, "source": cost_source},
        "journal_symbols": sorted(journal),
        "folded_into_queen_knowledge": folded,
        "metacognition_self_backtest": backtest,
        "errors": errors,
    }
    try:
        _atomic_write_json(SUMMARY_PATH, summary)
    except OSError as exc:
        errors.append(f"prophecy summary write failed: {exc}")

    return summary


def run_self_backtest() -> Dict[str, Any]:
    """QueenMetacognition.self_backtest() on a slow cadence. Fail-closed."""
    started = time.time()
    try:
        upstream = str(UPSTREAM)
        if upstream not in sys.path:
            sys.path.insert(0, upstream)
        os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
        os.environ.setdefault("AUREON_AUDIT_MODE", "1")
        os.environ.setdefault("AUREON_GLOBAL_HISTORY_DB", str(DB_PATH))
        from aureon.queen.queen_metacognition import QueenMetacognition

        results = QueenMetacognition().self_backtest() or {}
        if results.get("error"):
            out = {"ts": started, "ts_iso": datetime.now(timezone.utc).isoformat(),
                   "error": results["error"]}
        else:
            out = {
                "ts": started,
                "ts_iso": datetime.fromtimestamp(started, timezone.utc).isoformat(),
                "overall_metacognitive_score": results.get("overall_metacognitive_score"),
                "total_reflections": results.get("total_reflections"),
                "total_insights": results.get("total_insights"),
                "stagnation_resolved_pct": results.get("stagnation_resolved_pct"),
                "drift_prediction_accuracy": results.get("drift_prediction_accuracy"),
                "basis": "QueenMetacognition.self_backtest (cognition backtest, "
                         "not a market backtest)",
            }
    except Exception as exc:  # never let the mirror break the loop
        out = {"ts": started,
               "ts_iso": datetime.fromtimestamp(started, timezone.utc).isoformat(),
               "error": f"{type(exc).__name__}: {exc}"}
    try:
        _atomic_write_json(BACKTEST_PATH, out)
    except OSError:
        pass
    return out


def _probe_env() -> dict:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    upstream = str(UPSTREAM)
    env["PYTHONPATH"] = upstream + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def run_cycle(env: dict) -> None:
    started = time.time()
    # Launch the 7 probes in parallel; each probe has its own 90 s timeout.
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(PROBES)) as executor:
        futures = {
            executor.submit(run_probe, name, args, env): name
            for name, args in PROBES
        }
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                ok, detail = future.result()
            except Exception as exc:  # noqa: BLE001
                ok, detail = False, f"{type(exc).__name__}: {exc}"
            mark = "ok" if ok else "FAIL"
            print(f"[{time.strftime('%H:%M:%S')}] {name}: {mark} | {detail}", flush=True)
    # Prophecy resolution stays sequential: it consumes the probe outputs above.
    summary = run_prophecy_resolution()
    print(f"[{time.strftime('%H:%M:%S')}] prophecy: open={summary['open']} "
          f"resolved_total={summary['resolved_total']} "
          f"hit_rate={summary['hit_rate']} "
          f"new={summary['newly_resolved']} "
          f"folded={summary['folded_into_queen_knowledge']} "
          f"errors={len(summary['errors'])}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Temporal refresh orchestrator + prophecy resolver")
    parser.add_argument("--once", action="store_true",
                        help="run one probe cycle + one resolution, then exit")
    parser.add_argument("--resolve-only", action="store_true",
                        help="run only the prophecy resolution step, then exit")
    parser.add_argument("--backtest", action="store_true",
                        help="run one QueenMetacognition.self_backtest, then exit")
    args = parser.parse_args()

    if args.resolve_only:
        summary = run_prophecy_resolution()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return
    if args.backtest:
        print(json.dumps(run_self_backtest(), indent=2, ensure_ascii=False))
        return

    env = _probe_env()
    if args.once:
        run_cycle(env)
        return

    print("⏳ temporal refresh orchestrator online", flush=True)
    cycle = 0
    while True:
        started = time.time()
        run_cycle(env)
        cycle += 1
        if cycle % SELF_BACKTEST_EVERY == 0:
            bt = run_self_backtest()
            print(f"[{time.strftime('%H:%M:%S')}] self_backtest: "
                  f"score={bt.get('overall_metacognitive_score')} "
                  f"{'ERROR ' + bt['error'] if bt.get('error') else ''}", flush=True)
        elapsed = time.time() - started
        time.sleep(max(5.0, INTERVAL - elapsed))


if __name__ == "__main__":
    from _console_utf8_shim import ensure_utf8_stdout

    ensure_utf8_stdout()
    main()
