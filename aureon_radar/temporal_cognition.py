#!/usr/bin/env python3
"""temporal_cognition.py — TEMPORAL COGNITION MODULE (integrator + negative-close gate).

Owner decree 2026-09-06 (Gary Leckey): Queen Sero must sense linear and
non-linear time, phase in and out of the quantum vacuum (multiverse), see
best outcomes and quickest energy-capture paths, and NEVER close on a
negative unless the math proves cutting is beneficial.

This module is PERCEPTION/DECISION-LAYER ONLY. It reads sibling state files,
integrates them into one temporal outlook, and applies an explicit,
fail-closed negative-close gate. It places no orders and touches no capital.

Inputs (all optional; missing -> null block + error entry, never fabricated):
  state/multiverse_outlook.json   best outcome / capture-speed hints per symbol
  state/time_to_capture.json      real time-to-capture stats + per-position
                                  elapsed / velocity
  state/harmonic_phase.json       phase crest/trough per symbol
  state/trading_progress_state.json  open positions (entry/current/pnl/
                                  target_pct/pct_to_target)
  state/capture_floor.json        1% capture floor (owner decree, untouched)

Output:
  state/temporal_outlook.json     {ts, ts_iso, temporal_sense, positions[],
                                   candidates_top, errors}

NEGATIVE-CLOSE GATE (explicit, honest, fail-closed)
---------------------------------------------------
For a position with pnl_usd < 0:

  ev_hold_usd = target_pnl_usd * P(reach) * time_discount

    target_pnl_usd   = size_usd * target_pct / 100          (real, from position)
    P(reach)         = reach probability from REAL data only
                       (time_to_capture.hit_rate / reach_probability, or a
                       per-symbol probability supplied by multiverse_outlook).
                       If none exists -> EV is not computable -> verdict 'await'.
    time_discount    = ttc_median_min / (ttc_median_min + expected_capture_min)
                       (value of a capture realised later is discounted
                       against the median realised capture time).

  ev_cut_redeploy_usd = -abs(pnl_usd) + best_expectancy_usd * redeploy_time_factor

    best_expectancy_usd   = expectancy of the best REAL candidate in the data
                            (multiverse best outcome with expectancy > 0).
                            No positive-expectancy candidate -> this EV does
                            not exist and cutting can never be beneficial.
    redeploy_time_factor  = ttc_median_min / (ttc_median_min + candidate_capture_min)
                            (time for the redeployed capital to actually capture).

  verdict = 'cut_beneficial' ONLY when
      ev_cut_redeploy_usd > ev_hold_usd + margin
      AND a real candidate with positive expectancy exists in the data,
    where margin = max(0.10 * abs(ev_hold_usd), 0.01 USD) — cutting must be
    clearly superior, not a coin flip.

  Otherwise 'hold' — a negative close with no better redeploy is NEVER
  beneficial. Any missing required input -> 'await' + reason naming exactly
  what is missing. EVs are never fabricated.

Usage:
  cd aureon_radar
  set -a && . ./.env && set +a
  PYTHONUTF8=1 PYTHONPATH=<workspace>/aureon-os-upstream python temporal_cognition.py
  python temporal_cognition.py --selftest   # synthetic gate-math proof (clearly
                                            # labelled SYNTHETIC, never written
                                            # to state)
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_DIR = Path(__file__).resolve().parent / "state"
OUT_PATH = STATE_DIR / "temporal_outlook.json"

# Gate constants — explicit and centralized so the math is auditable.
CUT_MARGIN_FRACTION = 0.10   # cut must beat hold by >= 10% of |ev_hold|
MIN_MARGIN_USD = 0.01        # ... and by at least one cent
CANDIDATES_TOP_N = 5

# Probability of reaching target is accepted only from these REAL data fields
# (checked in order). Never synthesised.
P_REACH_FIELDS = ("hit_rate", "reach_probability", "reach_rate", "p_reach")


# ---------------------------------------------------------------------------
# Fail-closed loading / numeric helpers
# ---------------------------------------------------------------------------

def load_state(name: str, errors: list) -> dict | None:
    """Load a sibling state file. Missing/unreadable/invalid -> None + error."""
    path = STATE_DIR / name
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        errors.append(f"{name}: missing (sibling not written yet) -> null block")
        return None
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{name}: unreadable/invalid ({exc}) -> null block")
        return None
    if not isinstance(data, dict):
        errors.append(f"{name}: top-level is {type(data).__name__}, expected object -> null block")
        return None
    return data


def num(value) -> float | None:
    """Coerce to float or None — never raises, never fabricates."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def pos_key(pos: dict) -> str:
    venue = pos.get("venue") or "unknown_venue"
    symbol = pos.get("symbol") or "unknown_symbol"
    return f"{venue}:{symbol}"


# ---------------------------------------------------------------------------
# Defensive extractors — tolerate any reasonable sibling schema
# ---------------------------------------------------------------------------

def extract_time_to_capture(data: dict | None) -> dict:
    """Pull real capture stats out of time_to_capture.json (best effort).

    Accepted shapes (checked broadly, all optional):
      {stats: {median_min|median|p50|mean_min, hit_rate|reach_probability},
       median_min: ..., positions|open: {key: {elapsed_min, velocity_pct_per_min}}}
    """
    out = {"median_min": None, "p_reach": None, "positions": {}}
    if not data:
        return out

    stats = data.get("stats") if isinstance(data.get("stats"), dict) else data
    for key in ("median_min", "median", "p50", "mean_min", "mean"):
        v = num(stats.get(key)) if isinstance(stats, dict) else None
        if v is not None and v > 0:
            out["median_min"] = v
            break
    if isinstance(stats, dict):
        for field in P_REACH_FIELDS:
            v = num(stats.get(field))
            if v is not None:
                out["p_reach"] = clamp(v, 0.0, 1.0)
                break

    per_pos = data.get("positions") or data.get("open") or {}
    if isinstance(per_pos, dict):
        for key, rec in per_pos.items():
            if not isinstance(rec, dict):
                continue
            entry = {}
            for field in ("elapsed_min", "elapsed_minutes", "elapsed"):
                v = num(rec.get(field))
                if v is not None:
                    entry["elapsed_min"] = v
                    break
            for field in ("velocity_pct_per_min", "velocity_pct_min", "velocity"):
                v = num(rec.get(field))
                if v is not None:
                    entry["velocity_pct_per_min"] = v
                    break
            if entry:
                out["positions"][str(key)] = entry
    elif isinstance(per_pos, list):
        for rec in per_pos:
            if isinstance(rec, dict):
                key = rec.get("key") or rec.get("position_key") or pos_key(rec)
                entry = {}
                for field in ("elapsed_min", "elapsed_minutes", "elapsed"):
                    v = num(rec.get(field))
                    if v is not None:
                        entry["elapsed_min"] = v
                        break
                for field in ("velocity_pct_per_min", "velocity_pct_min", "velocity"):
                    v = num(rec.get(field))
                    if v is not None:
                        entry["velocity_pct_per_min"] = v
                        break
                if entry:
                    out["positions"][str(key)] = entry
    return out


def extract_multiverse(data: dict | None) -> dict:
    """Pull best-outcome / capture-speed hints out of multiverse_outlook.json.

    Accepted shapes (all optional):
      {field_regime: ...,
       best_outcomes|best|outcomes: [{symbol, rank, expectancy_usd|expectancy,
                                      expected_capture_min|capture_min, ...}],
       capture_speed|quickest_paths: {symbol: rank} | [{symbol, rank}]}
    """
    out = {"field_regime": None, "best_outcomes": [], "quickest_path_rank": {}}
    if not data:
        return out

    regime = data.get("field_regime") or data.get("regime")
    if regime is None and isinstance(data.get("field"), dict):
        regime = data["field"].get("regime")
    if isinstance(regime, str) and regime.strip():
        out["field_regime"] = regime.strip()

    raw = None
    for key in ("best_outcomes", "best", "outcomes"):
        if isinstance(data.get(key), list):
            raw = data[key]
            break
    if raw is None and isinstance(data.get("best_outcomes"), dict):
        raw = [{"symbol": k, **(v if isinstance(v, dict) else {})} for k, v in data["best_outcomes"].items()]
    for rec in raw or []:
        if not isinstance(rec, dict):
            continue
        symbol = rec.get("symbol") or rec.get("asset")
        if not symbol:
            continue
        entry = {"symbol": str(symbol)}
        for field in ("rank", "best_outcome_rank"):
            v = num(rec.get(field))
            if v is not None:
                entry["rank"] = v
                break
        for field in ("expectancy_usd", "expectancy", "ev_usd"):
            v = num(rec.get(field))
            if v is not None:
                entry["expectancy_usd"] = v
                break
        for field in ("expected_capture_min", "capture_min", "time_to_capture_min"):
            v = num(rec.get(field))
            if v is not None and v > 0:
                entry["expected_capture_min"] = v
                break
        out["best_outcomes"].append(entry)

    speed = data.get("capture_speed") or data.get("quickest_paths") or {}
    if isinstance(speed, dict):
        for sym, rank in speed.items():
            v = num(rank.get("rank")) if isinstance(rank, dict) else num(rank)
            if v is not None:
                out["quickest_path_rank"][str(sym)] = v
    elif isinstance(speed, list):
        for rec in speed:
            if isinstance(rec, dict):
                sym = rec.get("symbol")
                v = num(rec.get("rank"))
                if sym and v is not None:
                    out["quickest_path_rank"][str(sym)] = v
    return out


def _canon_sym(sym: str) -> str:
    """Canonical symbol for cross-file joins (BTCUSD/BTCUSDT/BTC-USD/XBTUSD -> BTC)."""
    s = str(sym).upper().replace("/", "").replace("-", "").strip()
    aliases = {
        "BTCUSD": "BTC", "BTCUSDT": "BTC", "XBTUSD": "BTC", "XBTUSDT": "BTC",
        "ETHUSD": "ETH", "ETHUSDT": "ETH", "XETHUSD": "ETH",
        "SOLUSD": "SOL", "SOLUSDT": "SOL",
    }
    return aliases.get(s, s)


def extract_harmonic(data: dict | None) -> dict:
    """Pull phase hints per symbol out of harmonic_phase.json."""
    out: dict[str, str] = {}
    if not data:
        return out
    phases = data.get("phases") or data.get("symbols") or {}
    if isinstance(phases, dict):
        items = phases.items()
    elif isinstance(phases, list):
        items = ((rec.get("symbol"), rec) for rec in phases if isinstance(rec, dict))
    else:
        items = ()
    for sym, rec in items:
        if not sym:
            continue
        if isinstance(rec, str):
            out[_canon_sym(sym)] = rec
        elif isinstance(rec, dict):
            phase = rec.get("phase_hint") or rec.get("phase") or rec.get("state")
            if isinstance(phase, str) and phase.strip():
                out[_canon_sym(sym)] = phase.strip()
    return out


# ---------------------------------------------------------------------------
# Temporal sense
# ---------------------------------------------------------------------------

def session_name(utc_hour: int) -> str:
    """Coarse trading session by UTC hour (crypto never closes; this names
    which traditional desk is awake — perception only)."""
    if 0 <= utc_hour < 7:
        return "asia"
    if 7 <= utc_hour < 13:
        return "london"
    if 13 <= utc_hour < 21:
        return "new_york"
    return "asia_late"


def _load_json(path: Path, errors: list, label: str) -> dict | None:
    """Load a JSON file; fail-closed on missing/unreadable/invalid."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        errors.append(f"{label}: {path.name} not found -> null block")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{label}: {path.name} unreadable ({exc}) -> null block")
    return None


def _solar_state_path() -> Path | None:
    """Resolve the solar system state file via the bridge if possible."""
    try:
        import solar_system_temporal_bridge as ssb
        return ssb.SOLAR_STATE_FILE
    except Exception:
        return None


def build_energy_digest(errors: list) -> dict:
    """Celestial energy digest for the queen's temporal outlook.

    Inputs (all optional; missing -> that sub-field null + reason):
      - state/global_energy_flow.json    market movers + whale alerts + DMF note
      - solar_system_data/solar_system_state.json  solar activity
      - schumann_state.json              Schumann resonance
      - sero_space_weather/space_weather_state.json  Kp + CMEs
      - aureon_radar/planetary_signals.jsonl tail    Kp fallback
    """
    workspace = Path(__file__).resolve().parent.parent
    radar = workspace / "aureon_radar"
    now = time.time()

    digest: dict[str, Any] = {}

    def _add_reason(existing: str | None, reason: str) -> str:
        return f"{existing}; {reason}" if existing else reason

    # ── Market energy ────────────────────────────────────────────────────────
    market = {"top_3_movers": None, "whale_alert_count": None,
              "deep_money_flow_note": None, "ts": None,
              "source": "aureon_radar/state/global_energy_flow.json",
              "error": None}
    gef = _load_json(radar / "state" / "global_energy_flow.json", errors, "energy_digest.market")
    if gef:
        market["ts"] = gef.get("ts")
        movers = gef.get("movers") if isinstance(gef.get("movers"), list) else []
        if movers:
            try:
                ranked = sorted(
                    [m for m in movers if isinstance(m, dict)],
                    key=lambda m: abs(num(m.get("change_pct")) or 0.0),
                    reverse=True,
                )
                market["top_3_movers"] = [
                    {
                        "symbol": m.get("symbol"),
                        "change_pct": num(m.get("change_pct")),
                        "direction": m.get("direction"),
                        "price": num(m.get("price")),
                        "source": m.get("source"),
                    }
                    for m in ranked[:3]
                ]
            except Exception as exc:
                market["error"] = f"movers parse failed: {type(exc).__name__}: {exc}"
        else:
            market["error"] = "global_energy_flow.movers missing or empty"

        wa = gef.get("whale_alerts")
        if isinstance(wa, list):
            market["whale_alert_count"] = sum(
                int(a.get("alerts_emitted", 0) or 0)
                for a in wa if isinstance(a, dict)
            )
        else:
            market["whale_alert_count"] = None
            market["error"] = _add_reason(market["error"], "whale_alerts missing")

        dmf = gef.get("deep_money_flow")
        if isinstance(dmf, dict):
            # verbatim-labeled historical_static_reference
            market["deep_money_flow_note"] = {
                "label": "historical_static_reference",
                **dmf,
            }
        else:
            market["deep_money_flow_note"] = None
            market["error"] = _add_reason(market["error"], "deep_money_flow missing")
    else:
        market["error"] = "global_energy_flow.json missing/unreadable"
    digest["market_energy"] = market

    # ── Solar state ──────────────────────────────────────────────────────────
    solar = {"sunspot_number": None, "f10_7_flux": None, "cycle_phase": None,
             "ts": None, "source": None, "error": None}
    solar_path = _solar_state_path() or (workspace / "solar_system_data" / "solar_system_state.json")
    rel = solar_path.relative_to(workspace) if solar_path.is_relative_to(workspace) else solar_path
    solar["source"] = str(rel).replace("\\", "/")
    solar_doc = _load_json(solar_path, errors, "energy_digest.solar")
    if solar_doc and isinstance(solar_doc.get("solar_activity"), dict):
        sa = solar_doc["solar_activity"]
        solar["sunspot_number"] = num(sa.get("sunspot_number"))
        # Upstream uses "f10.7_flux" with a literal dot; tolerate both forms.
        solar["f10_7_flux"] = num(sa.get("f10.7_flux") or sa.get("f10_7_flux"))
        solar["cycle_phase"] = sa.get("cycle_phase")
        solar["ts"] = solar_doc.get("timestamp")
        solar["error"] = None
    else:
        solar["error"] = "solar_system_state.json missing or solar_activity absent"
    digest["solar_state"] = solar

    # ── Schumann ─────────────────────────────────────────────────────────────
    schumann = {"frequency_hz": None, "activity_label": None,
                "ts": None, "source": "schumann_state.json", "error": None}
    sch_doc = _load_json(workspace / "schumann_state.json", errors, "energy_digest.schumann")
    if sch_doc:
        schumann["frequency_hz"] = num(sch_doc.get("frequency_hz"))
        schumann["activity_label"] = sch_doc.get("activity_label")
        schumann["ts"] = sch_doc.get("timestamp")
        schumann["error"] = None
    else:
        schumann["error"] = "schumann_state.json missing/unreadable"
    digest["schumann"] = schumann

    # ── Space weather (Kp / CME) ─────────────────────────────────────────────
    space = {"kp_index": None, "storm_level": None, "cme_count_24h": None,
             "ts": None, "source": None, "error": None}
    sw_path = workspace / "sero_space_weather" / "space_weather_state.json"
    sw = _load_json(sw_path, errors, "energy_digest.space_weather")
    fresh_hours = 2.0
    use_sero = False
    if sw and isinstance(sw.get("latest"), dict):
        age_s = now - _parse_iso_ts(sw.get("timestamp")) if sw.get("timestamp") else float("inf")
        latest = sw["latest"]
        if age_s < fresh_hours * 3600:
            use_sero = True
            space["kp_index"] = num(latest.get("kp_index"))
            space["storm_level"] = latest.get("storm_level")
            space["cme_count_24h"] = (
                int(latest["cme_count_24h"]) if isinstance(latest.get("cme_count_24h"), int) else None
            )
            space["ts"] = latest.get("timestamp")
            space["source"] = "sero_space_weather/space_weather_state.json"
            if not latest.get("source_reachable"):
                space["error"] = "sero state latest marked source_reachable=false"
            else:
                space["error"] = None

    if not use_sero:
        ps_path = radar / "planetary_signals.jsonl"
        space["source"] = "aureon_radar/planetary_signals.jsonl (tail fallback)"
        try:
            lines = ps_path.read_text(encoding="utf-8").strip().splitlines()
            last = json.loads(lines[-1]) if lines else {}
            if isinstance(last, dict) and last.get("planetary_narrative"):
                nar = last["planetary_narrative"]
                m = re.search(r"Kp\s*=\s*([\d.]+)", str(nar))
                space["kp_index"] = num(m.group(1)) if m else None
                space["ts"] = last.get("timestamp")
                space["error"] = None if m else "planetary_signals tail lacks parseable Kp="
            else:
                space["error"] = "planetary_signals.jsonl missing or tail has no narrative"
        except Exception as exc:
            space["error"] = f"planetary_signals fallback failed: {type(exc).__name__}: {exc}"
    digest["space_weather"] = space

    return digest


def _parse_iso_ts(value) -> float:
    """Best-effort ISO timestamp -> epoch seconds; fail closed -> inf on bad input."""
    if isinstance(value, (int, float)):
        return float(value)
    try:
        # str(datetime.now(timezone.utc).isoformat()) may contain '+00:00'
        s = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return float("inf")


def build_temporal_sense(now: datetime, mv: dict, harmonic: dict) -> dict:
    next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    in_phase = sorted(sym for sym, ph in harmonic.items()
                      if ph.lower() in ("crest", "peak", "in_phase", "constructive"))
    field_regime = mv.get("field_regime")
    if not field_regime and isinstance(mv.get("_field"), dict):
        field_regime = mv["_field"].get("regime")
    return {
        "linear": {
            "utc_now": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "session": session_name(now.hour),
            "next_daily_close_utc": next_midnight.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "non_linear": {
            "field_regime": field_regime or "unknown",
            "symbols_in_phase_hint": in_phase,
        },
    }


# ---------------------------------------------------------------------------
# Negative-close gate — the heart of the decree
# ---------------------------------------------------------------------------

def expected_capture_min(pos: dict, key: str, ttc: dict) -> float | None:
    """Realistic minutes to capture, from real data only (first available):
    1. velocity-derived: pct_to_target / velocity_pct_per_min
    2. the position's own eta_min from trading_progress_state
    3. global time-to-capture median
    """
    pct_to_target = num(pos.get("pct_to_target"))
    vel = (ttc["positions"].get(key) or {}).get("velocity_pct_per_min")
    if pct_to_target is not None and vel is not None and vel > 0:
        return pct_to_target / vel
    eta = num(pos.get("eta_min"))
    if eta is not None and eta > 0:
        return eta
    return ttc.get("median_min")


def negative_close_gate(pos: dict, key: str, ttc: dict, mv: dict) -> dict:
    """Explicit, honest, fail-closed gate. See module docstring for the math."""
    pnl = num(pos.get("pnl_usd"))
    gate: dict = {
        "pnl_usd": pnl,
        "verdict": "await",
        "ev_hold_usd": None,
        "ev_cut_redeploy_usd": None,
        "reason": "",
    }
    if pnl is None:
        gate["reason"] = "pnl_usd missing from position data — cannot gate"
        return gate

    if pnl >= 0:
        gate["verdict"] = "hold"
        gate["reason"] = "pnl >= 0 — negative-close gate not applicable"
        return gate

    # --- real inputs required for ev_hold ---
    size_usd = num(pos.get("size_usd"))
    target_pct = num(pos.get("target_pct"))
    exp_min = expected_capture_min(pos, key, ttc)
    ttc_median = ttc.get("median_min")
    p_reach = ttc.get("p_reach")

    missing = []
    if size_usd is None or size_usd <= 0:
        missing.append("size_usd")
    if target_pct is None:
        missing.append("target_pct")
    if p_reach is None:
        missing.append("P(reach) real probability (time_to_capture hit_rate)")
    if exp_min is None:
        missing.append("expected_capture_min (velocity/eta/median)")
    if ttc_median is None:
        missing.append("time_to_capture median")
    if missing:
        gate["reason"] = "await: missing real inputs -> " + ", ".join(missing) + \
                         " — EV never fabricated"
        return gate

    target_pnl_usd = size_usd * target_pct / 100.0
    time_discount = ttc_median / (ttc_median + exp_min)
    ev_hold = target_pnl_usd * p_reach * time_discount

    # --- real inputs required for ev_cut_redeploy ---
    symbol = str(pos.get("symbol") or "")
    candidates = [c for c in mv["best_outcomes"]
                  if c.get("expectancy_usd") is not None and c["expectancy_usd"] > 0]
    if not candidates:
        gate["ev_hold_usd"] = round(ev_hold, 6)
        gate["verdict"] = "hold"
        gate["reason"] = ("no candidate with positive expectancy exists in the data — "
                          "a negative close with no better redeploy is never beneficial")
        return gate

    best = max(candidates, key=lambda c: c["expectancy_usd"])
    cand_capture = best.get("expected_capture_min") or ttc_median
    redeploy_time_factor = ttc_median / (ttc_median + cand_capture)
    ev_cut = -abs(pnl) + best["expectancy_usd"] * redeploy_time_factor

    gate["ev_hold_usd"] = round(ev_hold, 6)
    gate["ev_cut_redeploy_usd"] = round(ev_cut, 6)

    margin = max(CUT_MARGIN_FRACTION * abs(ev_hold), MIN_MARGIN_USD)
    if ev_cut > ev_hold + margin:
        gate["verdict"] = "cut_beneficial"
        gate["reason"] = (f"ev_cut_redeploy {ev_cut:.4f} > ev_hold {ev_hold:.4f} "
                          f"+ margin {margin:.4f}; real positive-expectancy candidate "
                          f"{best['symbol']} (expectancy {best['expectancy_usd']:.4f} USD)")
    else:
        gate["verdict"] = "hold"
        gate["reason"] = (f"ev_cut_redeploy {ev_cut:.4f} does not exceed ev_hold "
                          f"{ev_hold:.4f} + margin {margin:.4f} — holding the negative "
                          f"is the better expectancy")
    return gate


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_outlook() -> dict:
    errors: list[str] = []
    now = datetime.now(timezone.utc)

    mv_data = load_state("multiverse_outlook.json", errors)
    ttc_data = load_state("time_to_capture.json", errors)
    harmonic_data = load_state("harmonic_phase.json", errors)
    progress_data = load_state("trading_progress_state.json", errors)
    _floor = load_state("capture_floor.json", errors)  # decree anchor; read-only

    mv = extract_multiverse(mv_data)
    ttc = extract_time_to_capture(ttc_data)
    harmonic = extract_harmonic(harmonic_data)

    positions_out = []
    raw_positions = (progress_data or {}).get("positions")
    if isinstance(raw_positions, list):
        for pos in raw_positions:
            if not isinstance(pos, dict):
                continue
            key = pos_key(pos)
            symbol = str(pos.get("symbol") or "")
            phase_hint = harmonic.get(_canon_sym(symbol))
            timeline = ("non_linear_dominant"
                        if phase_hint and phase_hint.lower() in ("crest", "peak", "in_phase", "constructive")
                        else "linear")
            gate = negative_close_gate(pos, key, ttc, mv)
            positions_out.append({
                "key": key,
                "symbol": symbol,
                "timeline": timeline,
                "phase_hint": phase_hint,
                "expected_capture_min": expected_capture_min(pos, key, ttc),
                "best_outcome_rank": next(
                    (c.get("rank") for c in mv["best_outcomes"] if c.get("symbol") == symbol),
                    None),
                "quickest_path_rank": mv["quickest_path_rank"].get(symbol),
                "negative_close_gate": gate,
            })
    elif progress_data is not None:
        errors.append("trading_progress_state.json: 'positions' missing or not a list -> positions[] empty")

    dreamt = (load_state("dreamt_plays.json", errors) or {})
    juice = (load_state("juice_gate.json", errors) or {})
    sizing = (load_state("sizing_anatomy.json", errors) or {})

    def _juice_verdict(sym: str, venue: str | None) -> str | None:
        cs = _canon_sym(sym)
        for c in juice.get("candidates", []) if isinstance(juice.get("candidates"), list) else []:
            if not isinstance(c, dict):
                continue
            if _canon_sym(str(c.get("symbol") or "")) == cs and (
                venue is None or str(c.get("venue") or "").lower() == venue.lower()):
                return c.get("verdict")
        return None

    def _size_usd(sym: str, venue: str | None):
        cs = _canon_sym(sym)
        for c in sizing.get("candidates", []) if isinstance(sizing.get("candidates"), list) else []:
            if not isinstance(c, dict):
                continue
            if _canon_sym(str(c.get("symbol") or "")) == cs and (
                venue is None or str(c.get("venue") or "").lower() == venue.lower()):
                return c.get("size_usd")
        return None

    dream_candidates = []
    plays = dreamt.get("plays") if isinstance(dreamt.get("plays"), list) else []
    for p in plays[:CANDIDATES_TOP_N]:
        if not isinstance(p, dict):
            continue
        sym = str(p.get("symbol") or "")
        venue = p.get("venue_hint")
        venue_s = str(venue) if venue else None
        sim = p.get("simulated") if isinstance(p.get("simulated"), dict) else {}
        dream_candidates.append({
            "symbol": sym,
            "archetype": p.get("archetype"),
            "direction": p.get("direction"),
            "rank": p.get("rank"),
            "best_outcome_rank": p.get("rank"),
            "p_reach": sim.get("p_reach"),
            "expected_capture_min": sim.get("expected_capture_min"),
            "net_ev_usd": sim.get("net_ev_usd"),
            "faster_than_current": p.get("faster_than_current"),
            "size_usd": _size_usd(sym, venue_s),
            "juice_verdict": _juice_verdict(sym, venue_s),
            "truth_status": "simulated",
            "action_eligible": False,
            "source": "dreamt_plays",
        })

    ranked = sorted((c for c in mv["best_outcomes"] if c.get("rank") is not None),
                    key=lambda c: c["rank"])
    mv_candidates = [
        {
            "symbol": c["symbol"],
            "best_outcome_rank": c.get("rank"),
            "expectancy_usd": c.get("expectancy_usd"),
            "expected_capture_min": c.get("expected_capture_min"),
            "size_usd": _size_usd(c["symbol"], None),
            "juice_verdict": _juice_verdict(c["symbol"], None),
            "source": "multiverse_outlook",
        }
        for c in ranked[:CANDIDATES_TOP_N]
    ]
    candidates_top = dream_candidates or mv_candidates

    sense = build_temporal_sense(now, mv, harmonic)
    if sense["non_linear"]["field_regime"] == "unknown":
        raw_field = (harmonic_data or {}).get("field")
        if isinstance(raw_field, dict) and isinstance(raw_field.get("regime"), str):
            sense["non_linear"]["field_regime"] = raw_field["regime"]

    energy_digest = build_energy_digest(errors)
    seer_counsel = (harmonic_data or {}).get("seer_counsel")

    return {
        "ts": time.time(),
        "ts_iso": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "temporal_sense": sense,
        "positions": positions_out,
        "candidates_top": candidates_top,
        "energy_digest": energy_digest,
        "seer_counsel": seer_counsel,
        "errors": errors,
    }


def print_verdict_block(outlook: dict) -> None:
    print("=== TEMPORAL OUTLOOK — positions verdict block ===")
    print(f"ts_iso: {outlook['ts_iso']}")
    sense = outlook["temporal_sense"]
    print(f"linear:    {sense['linear']}")
    print(f"non_linear: {sense['non_linear']}")
    if not outlook["positions"]:
        print("positions: (none open / no progress state)")
    for p in outlook["positions"]:
        g = p["negative_close_gate"]
        print(f"- {p['key']}")
        print(f"    timeline={p['timeline']} phase_hint={p['phase_hint']} "
              f"expected_capture_min={p['expected_capture_min']}")
        print(f"    best_outcome_rank={p['best_outcome_rank']} "
              f"quickest_path_rank={p['quickest_path_rank']}")
        print(f"    gate: pnl_usd={g['pnl_usd']} verdict={g['verdict']}")
        print(f"          ev_hold_usd={g['ev_hold_usd']} "
              f"ev_cut_redeploy_usd={g['ev_cut_redeploy_usd']}")
        print(f"          reason: {g['reason']}")
    print(f"candidates_top: {json.dumps(outlook['candidates_top'])}")
    print(f"errors: {outlook['errors'] or '(none)'}")


def main() -> int:
    from aureon.utils.console_utf8 import ensure_utf8_stdout
    ensure_utf8_stdout()

    if "--selftest" in sys.argv:
        return selftest()

    outlook = build_outlook()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(outlook, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(OUT_PATH)
    print_verdict_block(outlook)
    print(f"\nwrote {OUT_PATH}")
    return 0


# ---------------------------------------------------------------------------
# Self-test: SYNTHETIC gate-math proof (never written to state, never live)
# ---------------------------------------------------------------------------

def selftest() -> int:
    ttc_full = {
        "median_min": 60.0, "p_reach": 0.55,
        "positions": {},
    }
    mv_full = {
        "best_outcomes": [
            {"symbol": "RAY", "rank": 1, "expectancy_usd": 5.0, "expected_capture_min": 30.0},
        ],
        "quickest_path_rank": {"RAY": 1},
    }
    neg_big = {"symbol": "BTC/USD", "venue": "alpaca", "pnl_usd": -0.10,
               "size_usd": 80.0, "target_pct": 3.0, "pct_to_target": 1.0, "eta_min": 120.0}
    mv_weak = {
        "best_outcomes": [
            {"symbol": "RAY", "rank": 1, "expectancy_usd": 0.5, "expected_capture_min": 30.0},
        ],
        "quickest_path_rank": {"RAY": 1},
    }

    cases = [
        ("cut_beneficial (big loss, strong candidate)", neg_big, ttc_full, mv_full,
         "cut_beneficial"),
        ("hold (loss, but candidate EV not superior)", neg_big, ttc_full, mv_weak,
         "hold"),
        ("hold (loss but NO positive candidate)", neg_big, ttc_full,
         {"best_outcomes": [], "quickest_path_rank": {}}, "hold"),
        ("await (no real P(reach))", neg_big,
         {"median_min": 60.0, "p_reach": None, "positions": {}}, mv_full, "await"),
        ("hold (positive pnl — gate N/A)", {**neg_big, "pnl_usd": 0.5}, ttc_full, mv_full,
         "hold"),
    ]
    print("=== SYNTHETIC SELFTEST (temporal_cognition gate math; NOT live, NOT written to state) ===")
    ok = True
    for name, pos, ttc, mv, want in cases:
        ttc_x = extract_time_to_capture(ttc)
        mv_x = extract_multiverse(mv)
        g = negative_close_gate(pos, pos_key(pos), ttc_x, mv_x)
        print(f"[{name}]")
        print(f"    verdict={g['verdict']} ev_hold={g['ev_hold_usd']} "
              f"ev_cut={g['ev_cut_redeploy_usd']} reason={g['reason']}")
        if g["verdict"] != want:
            print(f"    !! expected {want}, got {g['verdict']}")
            ok = False
        if g["verdict"] == "cut_beneficial" and (g["ev_cut_redeploy_usd"] is None or
                                                 g["ev_cut_redeploy_usd"] <= g["ev_hold_usd"]):
            ok = False
    print("selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
