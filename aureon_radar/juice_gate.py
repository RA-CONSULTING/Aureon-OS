#!/usr/bin/env python3
"""Juice gate — net-of-cost expectancy per candidate. Aureon radar.

Owner decree (Gary Leckey, 2026-09-06): Queen Sero must ALWAYS know if the
juice is worth the squeeze — every candidate's NET expectancy after REAL
costs, before any size is committed. This module is the perception layer for
that decree: it scores candidate symbol+direction+venue plays with the repo's
mined cost data and writes state/juice_gate.json.

COST DATA (mined from the repo, never fabricated, estimates labeled):
- taker fees: exchange_adapters/shadow_executor.VENUE_FEES — the binding fee
  table (kraken 0.40% tier-0 taker, corrected 2026-09-06; binance 0.10% VIP0;
  alpaca 0.0% commission-free, cost lives in spread; capital 0.0%, the CFD
  round-trip cost IS the spread).
  Cross-reference: analyzers/analyze_actual_vs_expected_costs.py assumed
  0.25% alpaca tier-1 taker / 0.01% spread — noted in venue source strings;
  the analyzer's own conclusion was that real round-trip costs run ~0.8-1.0%.
- spreads: state/hunting_grounds.json spread_pct when the symbol+venue is
  journaled there (live observation, spread_is_estimate flag respected);
  otherwise a venue default ESTIMATE (kraken 0.20% per hunting_grounds
  convention, alpaca/binance 0.01% per the analyzer's estimate, capital 0.10%
  per capital_client.compute_trade_fees) — always labeled.
- slippage: shadow_executor.SLIPPAGE 0.05% adverse per side, scaled by
  volatility: per_side = 0.05% * max(1, vol_1h_pct / 2%). Volatility from
  hunting_grounds volatility_1h_estimate_pct when present, else 3.0
  (labeled estimate).
- funding: spot venues carry none. capital (CFD) overnight financing is
  ~2.5% APR per capital_client.compute_trade_fees — reported as an annualized
  field, not folded into the round-trip of an intraday play.

GROSS EV priority per candidate (null-not-0; unknown => fail-closed):
1. Open position criteria.expected_move_pct (trading_progress_state.json).
2. cross_asset pre_signals remaining_pct (correlation_prior, labeled).
3. Otherwise the expectancy_gate conservative model: confidence * stop_pct
   (promotion stop 2%). Labeled as an estimate.

VERDICT (the 1% capture floor applies to NET — never weakened):
  net_ev_pct = gross_ev_pct - cost_pct
  net <  floor                -> not_worth
  floor <= net < 1.5 * floor  -> marginal
  net >= 1.5 * floor          -> juice_worth_squeeze
Missing gross EV -> not_worth ("insufficient_data — fail-closed").

Size: state/sizing_anatomy.json if a sibling organ has published per-candidate
sizes (read defensively); otherwise a reference size = min(venue free cash,
25% of total equity) from trading_progress_state.json, labeled.

Read-only over sibling state. Perception/decision-layer only: no orders, no
network, no key material, no restarts.
"""

from __future__ import annotations

import json
import math
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

RADAR_ROOT = Path(__file__).resolve().parent
STATE_DIR = RADAR_ROOT / "state"
OUT_PATH = STATE_DIR / "juice_gate.json"
ADAPTERS_DIR = RADAR_ROOT / "exchange_adapters"

for _p in (str(ADAPTERS_DIR),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Binding cost constants — single source of truth in the repo.
try:
    from shadow_executor import VENUE_FEES, SLIPPAGE  # type: ignore
except Exception:  # pragma: no cover - degraded import
    VENUE_FEES = {"kraken": 0.0040, "binance": 0.0010, "alpaca": 0.0, "capital": 0.0}
    SLIPPAGE = 0.0005

try:
    from expectancy_gate import expected_move_pct, PROMOTION_CONFIDENCE  # type: ignore
except Exception:  # pragma: no cover - degraded import
    def expected_move_pct(confidence: float, stop_pct: float = 0.02) -> float:
        try:
            return max(0.0, float(confidence)) * float(stop_pct)
        except (TypeError, ValueError):
            return 0.0
    PROMOTION_CONFIDENCE = 0.55

try:
    from capture_floor import load_capture_floor  # type: ignore
except Exception:  # pragma: no cover - degraded import
    def load_capture_floor() -> Optional[float]:
        return None

CAPTURE_FLOOR_FALLBACK = 0.01  # decree default 2026-09-06; floor never weakened
DEFAULT_STOP_PCT = 0.02
MARGINAL_BAND = 1.5            # marginal for floor <= net < 1.5 * floor
REFERENCE_SIZE_FRACTION = 0.25

# Venue default spread ESTIMATES (labeled; real spreads preferred from
# hunting_grounds). Sources: hunting_grounds kraken convention (0.20%);
# analyzers/analyze_actual_vs_expected_costs.py (alpaca 0.01%);
# capital_client.compute_trade_fees (capital 0.10%).
VENUE_DEFAULT_SPREAD = {
    "kraken": 0.002,
    "binance": 0.0001,
    "alpaca": 0.0001,
    "capital": 0.001,
}
DEFAULT_VOL_1H_PCT = 3.0  # labeled estimate when hunting grounds lacks one


def _rate(value: Any) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None


def _read_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)
    except Exception:
        pass
    return rows


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── cost schedules ─────────────────────────────────────────────────────────

def build_venue_costs(grounds: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Per-venue cost schedule with sources. Real spreads mined from
    hunting_grounds; everything estimated is labeled."""
    venue_costs: Dict[str, Dict[str, Any]] = {}
    known = set(VENUE_FEES) | set(VENUE_DEFAULT_SPREAD)
    for venue in sorted(known):
        key = venue.lower()
        taker = _rate(VENUE_FEES.get(key))
        if taker is None:
            taker = 0.0
        # Real spread observations per venue from hunting grounds.
        obs = [
            (g.get("symbol"), _rate(g.get("spread_pct")),
             bool(g.get("spread_is_estimate", True)))
            for g in grounds if str(g.get("exchange", "")).lower() == key
        ]
        obs = [(s, sp, est) for s, sp, est in obs if sp is not None]
        real = [sp for _, sp, est in obs if not est]
        source_bits = [
            f"taker={taker * 100:.2f}% from shadow_executor.VENUE_FEES",
        ]
        if key == "alpaca":
            source_bits.append(
                "cross-ref: analyze_actual_vs_expected_costs.py assumed "
                "0.25% tier-1 taker + 0.01% spread per leg")
        if key == "capital":
            source_bits.append(
                "capital_client.compute_trade_fees: no flat taker fee, "
                "round-trip cost IS the spread; overnight financing ~2.5% APR")
        venue_costs[key] = {
            "taker_pct": taker,
            "spread_pct": (min(real) if real else VENUE_DEFAULT_SPREAD.get(key)),
            "spread_is_estimate": not bool(real),
            "spread_source": (
                "hunting_grounds real observation(s)"
                if real else
                f"estimate (default; {len(obs)} journaled estimate(s) ignored "
                "in favor of the labeled default)"
            ),
            "slippage_model": (
                f"{SLIPPAGE * 100:.2f}% adverse per side, volatility-scaled: "
                f"per_side = {SLIPPAGE * 100:.2f}% * max(1, vol_1h_pct/2%) "
                "(shadow_executor.SLIPPAGE)"
            ),
            "funding": (
                "none (spot)" if key != "capital"
                else "overnight financing ~2.5% APR (capital_client; only if held overnight)"
            ),
            "source": "; ".join(source_bits),
        }
    return venue_costs


def journal_note(journal: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Transparency: the price cache journal records single-price events only
    (no bid/ask), so spreads come from hunting_grounds / labeled estimates."""
    usable = sum(1 for r in journal if r.get("event") in ("fetch_ok", "cache_hit")
                 and _rate(r.get("price")) is not None)
    return {
        "price_cache_journal_usable_price_events": usable,
        "note": "journal records single-price events only (no bid/ask), so "
                "spreads come from hunting_grounds / labeled estimates",
    }


def spread_for(venue: str, symbol: str,
               grounds: List[Dict[str, Any]]) -> (float, bool, str):
    """Best spread for symbol+venue: real hunting-grounds observation first,
    then venue default estimate (labeled). Returns (pct, is_estimate, source)."""
    key = str(venue or "").lower()
    sym = str(symbol or "").upper().replace("/", "").replace("-", "")
    best: Optional[float] = None
    for g in grounds:
        if str(g.get("exchange", "")).lower() != key:
            continue
        gs = str(g.get("symbol", "")).upper().replace("/", "").replace("-", "")
        if gs != sym:
            continue
        sp = _rate(g.get("spread_pct"))
        if sp is None:
            continue
        if not g.get("spread_is_estimate", True):
            return sp, False, "hunting_grounds (live)"
        if best is None:
            best = sp
    if best is not None:
        return best, True, "hunting_grounds (journaled estimate)"
    return VENUE_DEFAULT_SPREAD.get(key, 0.001), True, "venue default estimate"


def vol_for(venue: str, symbol: str, grounds: List[Dict[str, Any]]) -> (float, bool):
    key = str(venue or "").lower()
    sym = str(symbol or "").upper().replace("/", "").replace("-", "")
    for g in grounds:
        if str(g.get("exchange", "")).lower() != key:
            continue
        gs = str(g.get("symbol", "")).upper().replace("/", "").replace("-", "")
        if gs == sym:
            v = _rate(g.get("volatility_1h_estimate_pct"))
            if v is not None:
                return v, False
    return DEFAULT_VOL_1H_PCT, True


def round_trip_cost(venue: str, symbol: str,
                    grounds: List[Dict[str, Any]]) -> Dict[str, Any]:
    key = str(venue or "").lower()
    taker = _rate(VENUE_FEES.get(key))
    if taker is None:
        taker = 0.0
    spread, spread_est, spread_src = spread_for(key, symbol, grounds)
    vol, vol_est = vol_for(key, symbol, grounds)
    slip_side = SLIPPAGE * max(1.0, vol / 2.0)
    cost = 2.0 * taker + spread + 2.0 * slip_side
    return {
        "taker_pct": taker,
        "spread_pct": spread,
        "spread_is_estimate": spread_est,
        "spread_source": spread_src,
        "slippage_per_side_pct": slip_side,
        "slippage_is_estimate": True,  # model output, always
        "vol_1h_pct": vol,
        "vol_is_estimate": vol_est,
        "cost_pct": cost,
    }


# ── candidates ─────────────────────────────────────────────────────────────

def _norm_symbol(sym: Any) -> str:
    return str(sym or "").upper()


def gather_candidates(gef: Optional[Dict[str, Any]],
                      hg: Optional[Dict[str, Any]],
                      tps: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cands: List[Dict[str, Any]] = []

    # 1. Open positions (live expectancy from their own criteria).
    for pos in (tps or {}).get("positions", []) or []:
        crit = pos.get("criteria", {}) or {}
        gross = _rate(crit.get("expected_move_pct"))
        cands.append({
            "symbol": _norm_symbol(pos.get("symbol")),
            "direction": str(pos.get("direction", "unknown")),
            "venue": str(pos.get("venue", "")).lower(),
            "gross_ev_pct": gross,
            "gross_ev_is_estimate": False,
            "gross_ev_source": "open position criteria.expected_move_pct "
                               "(trading_progress_state)",
            "size_hint_usd": _rate(pos.get("size_usd")),
            "confidence": _rate(crit.get("expectancy_confidence")),
        })

    # 2. Cross-asset pre-signals (correlation prior, remaining move).
    cross = (gef or {}).get("cross_asset", {}) or {}
    for pre in cross.get("pre_signals", []) or []:
        follower_exchange = str(pre.get("follower_exchange", "")).lower()
        if follower_exchange in ("", "yahoo"):  # not an executable venue here
            continue
        remaining = _rate(pre.get("remaining_pct"))
        leader_move = _rate(pre.get("leader_move_pct"))
        direction = "up" if (remaining or 0) >= 0 else "down"
        cands.append({
            "symbol": _norm_symbol(pre.get("follower_symbol")),
            "direction": direction,
            "venue": follower_exchange,
            "gross_ev_pct": (abs(remaining) / 100.0) if remaining is not None else None,
            "gross_ev_is_estimate": True,
            "gross_ev_source": "global_energy_flow pre_signals remaining_pct "
                               "(correlation_prior, labeled estimate)",
            "size_hint_usd": None,
            "confidence": _rate(pre.get("correlation")),
            "leader_move_pct": leader_move,
        })

    # 3. Movers (binance 24h tickers): conservative gate model on confidence.
    for m in (gef or {}).get("movers", []) or []:
        conf = _rate(m.get("confidence"))
        est = expected_move_pct(conf if conf is not None else 0.0, DEFAULT_STOP_PCT)
        cands.append({
            "symbol": _norm_symbol(m.get("symbol")),
            "direction": str(m.get("direction", "unknown")),
            "venue": str(m.get("venue_hint", "")).lower(),
            "gross_ev_pct": est,
            "gross_ev_is_estimate": True,
            "gross_ev_source": "expectancy_gate model confidence*stop(2%) on "
                               "24h mover; 24h change already realized, not credit",
            "size_hint_usd": None,
            "confidence": conf,
            "change_24h_pct": _rate(m.get("change_pct")),
        })

    # 4. Hunting grounds (best venues by live spread) with default confidence.
    for g in (hg or {}).get("grounds", []) or []:
        est = expected_move_pct(PROMOTION_CONFIDENCE, DEFAULT_STOP_PCT)
        cands.append({
            "symbol": _norm_symbol(g.get("symbol")),
            "direction": "up",
            "venue": str(g.get("exchange", "")).lower(),
            "gross_ev_pct": est,
            "gross_ev_is_estimate": True,
            "gross_ev_source": "expectancy_gate model promotion_confidence(0.55)"
                               "*stop(2%); ground has no expectancy field",
            "size_hint_usd": None,
            "confidence": PROMOTION_CONFIDENCE,
        })

    return [c for c in cands if c.get("symbol") and c.get("venue")]


# ── sizing ─────────────────────────────────────────────────────────────────

def reference_sizes(tps: Optional[Dict[str, Any]],
                    sizing_anatomy: Optional[Dict[str, Any]],
                    candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """size_usd per candidate. Prefer a sibling sizing_anatomy entry; else
    min(venue free cash, 25% of equity). Labeled."""
    equity = None
    if tps:
        free = _rate((tps.get("capital") or {}).get("free_usd"))
        dep = _rate((tps.get("capital") or {}).get("deployed_usd"))
        if free is not None and dep is not None:
            equity = free + dep
    by_venue_free: Dict[str, float] = {}
    for venue, blk in ((tps or {}).get("capital", {}) or {}).get("by_venue", {}).items():
        v = _rate((blk or {}).get("free_usd"))
        if v is not None:
            by_venue_free[str(venue).lower()] = v

    anatomy_sizes: Dict[str, float] = {}
    if isinstance(sizing_anatomy, dict):
        for key in ("candidates", "sizes", "plays"):
            for item in sizing_anatomy.get(key, []) or []:
                if not isinstance(item, dict):
                    continue
                sym = _norm_symbol(item.get("symbol"))
                ven = str(item.get("venue", "")).lower()
                sz = _rate(item.get("size_usd"))
                if sym and ven and sz is not None:
                    anatomy_sizes[f"{ven}:{sym}"] = sz

    out = {"equity_usd": equity, "by_venue_free_usd": by_venue_free,
           "anatomy_keys": sorted(anatomy_sizes)}
    for c in candidates:
        k = f"{c['venue']}:{c['symbol']}"
        if k in anatomy_sizes:
            c["size_usd"] = anatomy_sizes[k]
            c["size_source"] = "state/sizing_anatomy.json (sibling organ)"
            continue
        if c.get("size_hint_usd") is not None:
            c["size_usd"] = c["size_hint_usd"]
            c["size_source"] = "open position size (trading_progress_state)"
            continue
        venue_free = by_venue_free.get(c["venue"])
        if equity is not None:
            ref = equity * REFERENCE_SIZE_FRACTION
            if venue_free is not None:
                ref = min(ref, max(0.0, venue_free))
            c["size_usd"] = ref
            c["size_source"] = ("reference size = min(venue free cash, 25% of "
                                "equity) from trading_progress_state (estimate)")
        else:
            c["size_usd"] = None
            c["size_source"] = "unknown — no equity or size source"
    return out


# ── verdicts ───────────────────────────────────────────────────────────────

def verdicts(candidates: List[Dict[str, Any]],
             grounds: List[Dict[str, Any]],
             floor: float) -> None:
    for c in candidates:
        gross = _rate(c.get("gross_ev_pct"))
        cost_blk = round_trip_cost(c["venue"], c["symbol"], grounds)
        cost = cost_blk["cost_pct"]
        c["cost_breakdown"] = cost_blk
        c["cost_pct"] = cost
        size = _rate(c.get("size_usd"))
        if gross is None:
            c["net_ev_pct"] = None
            c["net_ev_usd"] = None
            c["verdict"] = "not_worth"
            c["reason"] = "insufficient_data: no gross expectancy — fail-closed"
            continue
        net = gross - cost
        c["net_ev_pct"] = net
        c["net_ev_usd"] = (net * size) if size is not None else None
        if net < floor:
            c["verdict"] = "not_worth"
            c["reason"] = (f"net {net * 100:.2f}% < capture floor "
                           f"{floor * 100:.1f}% after costs "
                           f"(gross {gross * 100:.2f}% - cost {cost * 100:.2f}%)")
        elif net < MARGINAL_BAND * floor:
            c["verdict"] = "marginal"
            c["reason"] = (f"net {net * 100:.2f}% clears floor "
                           f"{floor * 100:.1f}% but inside marginal band "
                           f"[floor, {MARGINAL_BAND}x floor)")
        else:
            c["verdict"] = "juice_worth_squeeze"
            c["reason"] = (f"net {net * 100:.2f}% >= {MARGINAL_BAND}x floor "
                           f"after real costs")


# ── main ───────────────────────────────────────────────────────────────────

def main() -> int:
    from aureon.utils.console_utf8 import ensure_utf8_stdout
    ensure_utf8_stdout()

    errors: List[str] = []
    ts = datetime.now(timezone.utc)
    state: Dict[str, Any] = {
        "ts": ts.timestamp(),
        "ts_iso": utc_now_iso(),
        "floor_pct": None,
        "venue_costs": {},
        "candidates": [],
        "errors": errors,
    }

    gef = _read_json(STATE_DIR / "global_energy_flow.json")
    hg = _read_json(STATE_DIR / "hunting_grounds.json")
    tps = _read_json(STATE_DIR / "trading_progress_state.json")
    sizing_anatomy = _read_json(STATE_DIR / "sizing_anatomy.json")
    journal = _read_jsonl(STATE_DIR / "price_cache_journal.jsonl")

    for name, blob in (("global_energy_flow", gef), ("hunting_grounds", hg),
                       ("trading_progress_state", tps)):
        if blob is None:
            errors.append(f"missing/unreadable state/{name}.json — "
                          f"candidates from that source skipped (fail-closed)")

    floor = load_capture_floor()
    if floor is None:
        floor = CAPTURE_FLOOR_FALLBACK
        errors.append("state/capture_floor.json missing/corrupt — decree "
                      "fallback 1.0% applied (floor never weakened)")
    state["floor_pct"] = floor

    grounds = (hg or {}).get("grounds", []) or []
    try:
        state["venue_costs"] = build_venue_costs(grounds)
        state["journal_note"] = journal_note(journal)
    except Exception as exc:  # pragma: no cover - defensive
        errors.append(f"venue cost build failed: {exc}")
        state["venue_costs"] = {}

    try:
        cands = gather_candidates(gef, hg, tps)
    except Exception as exc:  # pragma: no cover - defensive
        errors.append(f"candidate gather failed: {exc}")
        cands = []

    try:
        sizing_meta = reference_sizes(tps, sizing_anatomy, cands)
        state["sizing"] = sizing_meta
        verdicts(cands, grounds, floor)
    except Exception as exc:  # pragma: no cover - defensive
        errors.append(f"sizing/verdict failed: {exc}\n{traceback.format_exc()}")
        for c in cands:
            c.setdefault("verdict", "not_worth")
            c.setdefault("reason", "internal error — fail-closed")

    # presentation order: juice first, then marginal, then not_worth
    order = {"juice_worth_squeeze": 0, "marginal": 1, "not_worth": 2}
    cands.sort(key=lambda c: (order.get(c.get("verdict"), 3),
                              -(_rate(c.get("net_ev_pct")) or -9.0)))
    state["candidates"] = cands

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
    tmp.replace(OUT_PATH)

    counts: Dict[str, int] = {}
    for c in cands:
        counts[c["verdict"]] = counts.get(c["verdict"], 0) + 1
    print(f"juice_gate @ {state['ts_iso']}  floor={floor * 100:.1f}%  "
          f"candidates={len(cands)}  {counts}")
    for c in cands:
        net = c.get("net_ev_pct")
        net_s = f"{net * 100:+.2f}%" if isinstance(net, float) else "n/a"
        nev = c.get("net_ev_usd")
        nev_s = f"${nev:+.4f}" if isinstance(nev, float) else "n/a"
        sz = c.get("size_usd")
        sz_s = f"${sz:.2f}" if isinstance(sz, float) else "n/a"
        flag = "EST" if c.get("gross_ev_is_estimate") else "LIVE"
        print(f"  [{c['verdict']:<18}] {c['venue']:<8} {c['symbol']:<12} "
              f"{c['direction']:<5} gross={flag} "
              f"{(c.get('gross_ev_pct') or 0) * 100:.2f}%  "
              f"cost={c.get('cost_pct', 0) * 100:.2f}%  net={net_s}  "
              f"size={sz_s}  net$={nev_s}")
        print(f"      reason: {c.get('reason', '')}")
    if errors:
        print("errors:")
        for e in errors:
            print(f"  - {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
