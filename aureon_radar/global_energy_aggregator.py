#!/usr/bin/env python3
"""Global Energy Flow Aggregator — Queen Sero's live battle-view feed.

Runs the global energy flow analyzers (aureon_radar/analyzers/) over REAL
public/exchange data — throttled through aureon_fusion.api_communion and the
exchange clients — and consolidates their outputs into:

    aureon_radar/state/global_energy_flow.json
    {
      "ts": <epoch>,
      "data_freshness": "live",
      "movers":         [{symbol, venue_hint, flow_score, direction,
                          confidence, source, change_pct, price}],
      "cross_asset":    {regime, category_moves, pre_signals, ...},
      "whale_alerts":   [...],
      "lighthouse":     {...},
      "bitcoin_forensics": {...},
      "deep_money_flow": {...},   # historical_static_reference, live: false
      "errors":         {section: error}
    }

CONTRACT (owner decree):
  - Fail-closed: a section that cannot be produced from real data is written
    as null + an `error` field — NEVER 0, NEVER fabricated.
  - Stale cached bodies from communion are dropped, never passed off as live.
  - No live auto-execution. This feeds scanners/decision support only.
  - Throttled: all public fetches go through api_communion (per-host interval,
    backoff, circuit breaker, daily budget accounting).

Usage:
    cd aureon_radar && set -a && . ./.env && set +a && \
        PYTHONUTF8=1 PYTHONPATH=<workspace>/aureon-os-upstream \
        python global_energy_aggregator.py [--interval SECONDS] [--movers N]
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

RADAR_ROOT = Path(__file__).resolve().parent
if str(RADAR_ROOT) not in sys.path:
    sys.path.insert(0, str(RADAR_ROOT))

# UTF-8 fix — aureon.utils.console_utf8 is absent from the upstream package;
# fall back to the repo shim, then to an inline no-op reconfigure.
try:
    from aureon.utils.console_utf8 import ensure_utf8_stdout
except ImportError:  # pragma: no cover - environment dependent
    try:
        from _console_utf8_shim import ensure_utf8_stdout
    except ImportError:
        def ensure_utf8_stdout(*_a, **_k):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

logger = logging.getLogger("global_energy_aggregator")

STATE_PATH = RADAR_ROOT / "state" / "global_energy_flow.json"


def _run_section(name: str, fn, *args, **kwargs) -> Dict[str, Any]:
    """Run one analyzer section, capturing its chatter and fail-closed errors."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            result = fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 — section isolation is the point
        logger.debug("%s failed: %s\n%s", name, exc, buf.getvalue()[-2000:])
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "error": "invalid_result_shape"}
    return result


def build_movers(crypto_changes: Dict[str, Dict[str, float]],
                 yahoo_changes: Dict[str, Optional[Dict[str, float]]],
                 top_n: int = 10) -> List[Dict[str, Any]]:
    """Top movers across the whole watched universe, from real measurements.

    flow_score is a transparent normalization of the measured 24h change:
    min(|change_pct| / 10, 1). Symbols with no real measurement are excluded.
    """
    rows: List[Dict[str, Any]] = []
    for base, d in (crypto_changes or {}).items():
        chg = float(d.get("change_pct", 0.0))
        rows.append({
            "symbol": base,
            "venue_hint": "binance",
            "flow_score": round(min(abs(chg) / 10.0, 1.0), 4),
            "direction": "up" if chg > 0 else "down",
            "confidence": 1.0,
            "source": "binance_24h_ticker",
            "change_pct": round(chg, 4),
            "price": float(d.get("price", 0.0)),
        })
    for sym, snap in (yahoo_changes or {}).items():
        if not snap:
            continue
        chg = float(snap.get("change_pct", 0.0))
        rows.append({
            "symbol": sym,
            "venue_hint": "yahoo",
            "flow_score": round(min(abs(chg) / 10.0, 1.0), 4),
            "direction": "up" if chg > 0 else "down",
            "confidence": 1.0,
            "source": "yahoo_chart",
            "change_pct": round(chg, 4),
            "price": float(snap.get("price", 0.0)),
        })
    rows.sort(key=lambda r: abs(r["change_pct"]), reverse=True)
    return rows[:top_n]


def aggregate(top_n_movers: int = 10) -> Dict[str, Any]:
    """One full aggregation pass. Returns the consolidated battle-view dict."""
    from analyzers import global_energy_data as ged
    from analyzers import cross_asset_correlator
    from analyzers import aureon_whale_onchain_tracker
    from analyzers import aureon_moby_dick_whale_hunter
    from analyzers import aureon_live_whale_profiler
    from analyzers import aureon_lighthouse
    from analyzers import bitcoin_lighthouse_forensics
    from analyzers import aureon_deep_money_flow_analyzer

    errors: Dict[str, Any] = {}
    ts = time.time()

    # ── Shared market-data batch (fetched ONCE, passed to consumers) ──
    tickers = ged.fetch_binance_24h_tickers()
    crypto_changes = ged.binance_tickers_to_changes(tickers) if tickers else None

    yahoo_changes: Dict[str, Optional[Dict[str, float]]] = {}
    for sym in list(ged.YAHOO_MAP):
        yahoo_changes[sym] = ged.fetch_yahoo_change_pct(sym)

    if crypto_changes is None and not any(yahoo_changes.values()):
        errors["market_data"] = "no_live_market_data"
        movers: Optional[List[Dict[str, Any]]] = None
    else:
        movers = build_movers(crypto_changes or {}, yahoo_changes, top_n=top_n_movers)

    # ── Cross-asset correlation (fed the shared batch) ──
    cross_asset = _run_section(
        "cross_asset",
        cross_asset_correlator.run_analysis,
        crypto_changes=crypto_changes,
        yahoo_changes=yahoo_changes,
    )
    if not cross_asset.get("ok"):
        errors["cross_asset"] = cross_asset.get("error")

    # ── Whale layer ──
    tracker_result = _run_section(
        "whale_tracker",
        lambda: aureon_whale_onchain_tracker.get_exchange_tracker().run_analysis(),
    )
    if not tracker_result.get("ok"):
        errors["whale_tracker"] = tracker_result.get("error")

    moby_result = _run_section(
        "moby_dick",
        aureon_moby_dick_whale_hunter.get_moby_dick_hunter().run_analysis,
    )
    if not moby_result.get("ok"):
        errors["moby_dick"] = moby_result.get("error")

    profiler_result = _run_section(
        "live_whale_profiler",
        aureon_live_whale_profiler.LiveWhaleProfiler().run_analysis,
    )
    if not profiler_result.get("ok"):
        errors["live_whale_profiler"] = profiler_result.get("error")

    whale_alerts: List[Dict[str, Any]] = []

    def _add_alert(kind: str, payload: Dict[str, Any]) -> None:
        whale_alerts.append({"kind": kind, "ts": ts, **payload})

    if tracker_result.get("ok"):
        _add_alert("large_trade_scan", {
            "source": "aureon_whale_onchain_tracker",
            "exchanges_scanned": tracker_result.get("exchanges_scanned"),
            "symbols": tracker_result.get("symbols"),
            "threshold_usd": tracker_result.get("threshold_usd"),
            "alerts_emitted": tracker_result.get("alerts_emitted"),
        })
    if moby_result.get("ok"):
        for pred in moby_result.get("predictions") or []:
            _add_alert("whale_prediction", {
                "source": "aureon_moby_dick_whale_hunter",
                **pred,
            })
    if profiler_result.get("ok"):
        for profile in profiler_result.get("profiles") or []:
            _add_alert("active_whale_profile", {
                "source": "aureon_live_whale_profiler",
                **profile,
            })

    # ── Pattern + forensic layer ──
    lighthouse_result = _run_section("lighthouse", aureon_lighthouse.run_analysis)
    if not lighthouse_result.get("ok"):
        errors["lighthouse"] = lighthouse_result.get("error")

    btc_result = _run_section("bitcoin_forensics", bitcoin_lighthouse_forensics.run_analysis)
    if not btc_result.get("ok"):
        errors["bitcoin_forensics"] = btc_result.get("error")

    # ── Historical static reference (never live) ──
    deep_money = _run_section(
        "deep_money_flow",
        lambda: aureon_deep_money_flow_analyzer.DeepMoneyFlowAnalyzer().run_analysis(),
    )
    if not deep_money.get("ok"):
        errors["deep_money_flow"] = deep_money.get("error")

    return {
        "ts": ts,
        "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
        "data_freshness": "live",
        "movers": movers,
        "cross_asset": cross_asset if cross_asset.get("ok") else {
            "ok": False, "regime": None, "category_moves": None,
            "pre_signals": None, "error": cross_asset.get("error"),
        },
        "whale_alerts": whale_alerts,
        "lighthouse": lighthouse_result if lighthouse_result.get("ok") else {
            "ok": False, "events": None, "error": lighthouse_result.get("error"),
        },
        "bitcoin_forensics": btc_result if btc_result.get("ok") else {
            "ok": False, "regime": None, "projection": None,
            "signature": None, "error": btc_result.get("error"),
        },
        "deep_money_flow": deep_money if deep_money.get("ok") else {
            "ok": False, "live": False, "error": deep_money.get("error"),
        },
        "sources": {
            "crypto": "binance_public_24h_ticker",
            "cross_asset": "binance+yahoo_public",
            "whales": "binance/kraken_public_trades+crypto_signals.jsonl+bot_shape_scanner_state.json",
            "lighthouse": "binance_public_klines",
            "bitcoin_forensics": "coingecko_public",
        },
        "errors": errors or None,
    }


def write_state(doc: Dict[str, Any], path: Path = STATE_PATH) -> None:
    """Atomic write — the organism never reads a half-written battle view."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    ensure_utf8_stdout()
    parser = argparse.ArgumentParser(description="Global Energy Flow Aggregator")
    parser.add_argument("--interval", type=float, default=0.0,
                        help="Loop every N seconds (0 = run once and exit)")
    parser.add_argument("--movers", type=int, default=10,
                        help="Number of top movers to include")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    while True:
        started = time.time()
        try:
            doc = aggregate(top_n_movers=args.movers)
            write_state(doc)
            n_movers = len(doc["movers"] or [])
            regime = (doc["cross_asset"] or {}).get("regime")
            logger.info(
                "global_energy_flow.json written: %d movers, regime=%s, "
                "whale_alerts=%d, errors=%s (%.1fs)",
                n_movers, regime, len(doc["whale_alerts"]),
                doc["errors"], time.time() - started,
            )
        except Exception as exc:  # noqa: BLE001 — the loop must survive
            logger.exception("aggregation pass failed: %s", exc)

        if args.interval <= 0:
            break
        time.sleep(max(1.0, args.interval - (time.time() - started)))

    return 0


if __name__ == "__main__":
    sys.exit(main())
