#!/usr/bin/env python3
"""
⏱️⚡ MARGIN ETA PREDICTOR - LINEAR TIME / TIME-TO-CAPTURE LAYER ⚡⏱️
===================================================================
Owner decree 2026-09-06: Queen Sero must sense LINEAR TIME — the quickest
ways to capture energy. This module mines the REAL trade journals and writes
aureon_radar/state/time_to_capture.json:

  {
    "ts": <epoch>, "ts_iso": <iso>, "utc_now": <iso>,
    "session": {"forex_open", "crypto_24_7", "weekend",
                "next_daily_close_utc", "next_funding_utc"},
    "symbols": {SYM: {"samples", "median_min_to_1pct", "median_min_to_2pct",
                      "median_min_to_3pct", "fastest_path_hint", "error?", ...}},
    "open_positions": [{"key", "symbol", "elapsed_min",
                        "velocity_pct_per_min", "implied_remaining_min",
                        "error?"}],
    "errors": []
  }

HARD RULES: fail-closed (null means "no valid samples", never 0); journaled
prices only — a record without prices is skipped, never estimated; no live
execution, perception/decision layer only. Exit detection is fee-aware and
hold-gated: a journaled close counts as an exit only when its |move| clears
the venue round-trip cost (hunting_grounds.json; venues without a real row
use a flagged 0.2% DEFAULT), and a mark-derived close (not corroborated
against shadow-book/position state) must also survive a 20-minute minimum
hold — sub-cost 1–3s spread-churn closes are counted as filtered, never as
exits.

Gary Leckey | September 2026
"Linear time is a weapon when you can measure it."
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import glob
import time
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

# Make the analyzers package importable when run as a script from anywhere.
_RADAR_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RADAR_ROOT not in sys.path:
    sys.path.insert(0, _RADAR_ROOT)

from analyzers.eta_verification_system import (
    mine_time_to_capture,
    canonical_symbol,
    load_venue_round_trip_costs,
    DEFAULT_ROUND_TRIP_COST_PCT,
)
from analyzers.improved_eta_calculator import (
    pct_velocity_per_min,
    implied_remaining_min,
)

STATE_DIR = os.path.join(_RADAR_ROOT, 'state')
OUTPUT_FILE = os.path.join(STATE_DIR, 'time_to_capture.json')
SHADOW_JOURNAL = os.path.join(STATE_DIR, 'shadow_trades.jsonl')
JOURNAL_GLOB = os.path.join(_RADAR_ROOT, 'exchange_adapters', 'journals', '*.jsonl')
PROGRESS_STATE = os.path.join(STATE_DIR, 'trading_progress_state.json')

# Approximate UTC forex session windows (no DST handling — a hint, not a gate).
FOREX_SESSIONS_UTC = (
    ("Sydney",   21, 30, 6, 0),
    ("Tokyo",     0,  0, 9, 0),
    ("London",    8,  0, 16, 30),
    ("New_York", 13,  0, 21, 0),
)

# Crypto perp funding timestamps (Binance/Kraken-style 8h cadence).
FUNDING_HOURS_UTC = (0, 8, 16)


def _session_context(now: datetime) -> Dict[str, Any]:
    """Market session context around a UTC instant. Fail-closed fields."""
    ctx: Dict[str, Any] = {
        "forex_open": False,
        "open_sessions": [],
        "crypto_24_7": True,
        "weekend": now.weekday() >= 5,
        "next_daily_close_utc": None,
        "next_funding_utc": None,
    }
    try:
        day = now.date()
        midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        nxt = midnight + timedelta(days=1)
        ctx["next_daily_close_utc"] = nxt.isoformat()

        for hour in FUNDING_HOURS_UTC:
            cand = midnight + timedelta(hours=hour)
            if cand > now:
                ctx["next_funding_utc"] = cand.isoformat()
                break
        else:
            ctx["next_funding_utc"] = (midnight + timedelta(days=1, hours=FUNDING_HOURS_UTC[0])).isoformat()

        mins = now.hour * 60 + now.minute
        for name, sh, sm, eh, em in FOREX_SESSIONS_UTC:
            start, end = sh * 60 + sm, eh * 60 + em
            if start <= end:
                open_now = start <= mins < end
            else:  # session wraps past midnight UTC
                open_now = mins >= start or mins < end
            if open_now:
                ctx["open_sessions"].append(name)
        ctx["forex_open"] = bool(ctx["open_sessions"])
    except Exception as e:
        ctx["error"] = f"session_context_failed: {e}"
    return ctx


def _load_progress_positions() -> List[Dict[str, Any]]:
    """
    Read current open positions from the sibling trading_progress_state
    (the live monitor's authoritative list). Tolerates absence/parses
    failure (fail-closed — empty list).
    """
    try:
        if os.path.exists(PROGRESS_STATE):
            with open(PROGRESS_STATE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return list(data.get('positions') or [])
    except Exception:
        pass
    return []


def _entry_matches(a: Optional[float], b: Optional[float]) -> bool:
    if a is None or b is None or a <= 0 or b <= 0:
        return False
    return abs(a - b) <= max(1e-6, abs(a) * 1e-6)


def _load_currently_open_keys(errors: List[str]) -> Optional[List[tuple]]:
    """
    Position-state keys (canonical, venue_lower, entry_price) for every
    position the shadow books / live monitor currently show as OPEN.

    Used by the miner to corroborate real closes: a journaled 'closed' for a
    position that is STILL OPEN in position state cannot be a real close — it
    is a mark observation and must respect the minimum-hold window.

    Returns None when no position state is available at all (fail-closed:
    the hold window then applies to every close).
    """
    keys: List[tuple] = []
    found_any = False

    for path in sorted(glob.glob(os.path.join(STATE_DIR, 'shadow_book_*.json'))):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            errors.append(f"shadow_book unreadable: {os.path.basename(path)}: {e}")
            continue
        positions = data.get('positions')
        if not isinstance(positions, dict):
            continue
        for sym, pos in positions.items():
            if not isinstance(pos, dict):
                continue
            entry = pos.get('entry_price')
            entry = float(entry) if isinstance(entry, (int, float)) and entry > 0 else None
            venue = str(pos.get('venue') or data.get('venue') or '')
            keys.append((canonical_symbol(str(pos.get('symbol') or sym)),
                         venue.lower(), entry))
            found_any = True

    for pos in _load_progress_positions():
        entry = pos.get('entry')
        entry = float(entry) if isinstance(entry, (int, float)) and entry > 0 else None
        venue = str(pos.get('venue') or '')
        keys.append((canonical_symbol(str(pos.get('symbol') or '')),
                     venue.lower(), entry))
        found_any = True

    if not found_any:
        errors.append("position_state_unavailable (no shadow_book positions, no "
                      "progress positions) -> every journaled close treated as "
                      "mark-derived; minimum-hold window applies to all (fail-closed)")
        return None
    return keys


def build_time_to_capture(now: Optional[datetime] = None) -> Dict[str, Any]:
    """Mine the journals and assemble the full time_to_capture document."""
    now = now or datetime.now(timezone.utc)
    now_ts = now.timestamp()
    errors: List[str] = []
    notes: List[str] = []

    journal_paths = sorted(glob.glob(JOURNAL_GLOB))
    if os.path.exists(SHADOW_JOURNAL):
        journal_paths = [SHADOW_JOURNAL] + [p for p in journal_paths if p != SHADOW_JOURNAL]
    if not journal_paths:
        errors.append("no_journal_files_found")

    # Venue round-trip costs (fee-aware exit threshold). Venues without a
    # real row fall back to DEFAULT_ROUND_TRIP_COST_PCT inside the miner,
    # flagged per-symbol as a DEFAULT — never a silent guess.
    round_trip_costs = load_venue_round_trip_costs(STATE_DIR)
    if not round_trip_costs:
        notes.append(f"hunting_grounds.json missing/unreadable or empty -> ALL venues use "
                     f"DEFAULT round-trip cost {DEFAULT_ROUND_TRIP_COST_PCT}% (flagged as default)")
    else:
        known = sorted(round_trip_costs)
        notes.append(f"venue round-trip costs from hunting_grounds.json for: {', '.join(known)}; "
                     f"any other venue falls back to DEFAULT {DEFAULT_ROUND_TRIP_COST_PCT}% (flagged)")

    currently_open = _load_currently_open_keys(errors)

    mined = mine_time_to_capture(journal_paths,
                                 round_trip_costs=round_trip_costs,
                                 currently_open=currently_open)
    errors.extend(mined.get("errors") or [])

    journal_open = mined.get("open_positions") or []
    progress_positions = _load_progress_positions()

    # Journal opens with no journaled close and no confirmation from the live
    # monitor. The current journal stops recording closes after 18:00 UTC, so
    # these are journal orphans — counted for transparency, not listed.
    confirmed_keys = {
        f"{p.get('venue')}:{canonical_symbol(p.get('symbol') or '')}"
        for p in progress_positions
    }
    orphan_count = sum(
        1 for j in journal_open
        if f"{j.get('venue')}:{j.get('canonical')}" not in confirmed_keys
    )

    # ── Current open positions (live monitor authority) + journal velocity ──
    open_positions: List[Dict[str, Any]] = []
    for pos in progress_positions:
        venue = pos.get('venue')
        symbol = pos.get('symbol') or ''
        canon = canonical_symbol(symbol)
        entry: Dict[str, Any] = {
            "key": f"{venue}:{symbol}",
            "symbol": symbol,
            "elapsed_min": None,
            "velocity_pct_per_min": None,
            "implied_remaining_min": None,
            "error": None,
        }
        try:
            opened_iso = (pos.get('criteria') or {}).get('opened_ts_utc')
            opened_ts = None
            if opened_iso:
                try:
                    opened_ts = datetime.fromisoformat(
                        str(opened_iso).replace('Z', '+00:00')).timestamp()
                except Exception:
                    opened_ts = None
            if opened_ts is None:
                entry["error"] = "opened_ts_utc_missing_or_unparseable"
            else:
                entry["elapsed_min"] = round(max(0.0, (now_ts - opened_ts) / 60.0), 4)

            # Journaled marks for this exact position (venue + entry price).
            jp = next((j for j in journal_open
                       if j.get('canonical') == canon
                       and j.get('venue') == venue
                       and _entry_matches(j.get('entry_price'), pos.get('entry'))),
                      None)
            samples = []
            if jp and opened_ts is not None:
                side = jp.get('side') or pos.get('direction') or 'buy'
                entry_price = jp.get('entry_price') or pos.get('entry')
                for pct, m_ts in (jp.get('marks') or []):
                    if m_ts is not None and m_ts >= opened_ts:
                        samples.append(((m_ts - opened_ts) / 60.0, pct))
            velocity = pct_velocity_per_min(samples) if len(samples) >= 2 else None
            entry["velocity_pct_per_min"] = round(velocity, 8) if velocity is not None else None

            target = pos.get('target_pct')
            target = float(target) if isinstance(target, (int, float)) else None
            # Journaled current move since open (pct_to_target in progress
            # state is remaining-to-target; we project from journaled move).
            current_move = (samples[-1][1] if samples else
                            (jp.get('last_pct_move') if jp else None))
            remaining = implied_remaining_min(current_move, target, velocity)
            entry["implied_remaining_min"] = round(remaining, 2) if remaining is not None else None

            reasons = []
            if not jp:
                reasons.append("no_journaled_open_or_marks_for_position")
            elif len(samples) < 2:
                reasons.append("insufficient_journaled_marks_for_velocity")
            if target is None:
                reasons.append("target_pct_missing_in_progress_state")
            elif remaining is None and velocity is not None and velocity <= 0:
                reasons.append("velocity_non_positive_no_projection")
            entry["error"] = "; ".join(reasons) or None
        except Exception as e:
            entry["error"] = f"enrichment_failed: {e}"
        open_positions.append(entry)

    doc: Dict[str, Any] = {
        "ts": now_ts,
        "ts_iso": now.isoformat(),
        "utc_now": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session": _session_context(now),
        "symbols": mined.get("symbols") or {},
        "open_positions": open_positions,
        "journal_open_unclosed_count": len(journal_open),
        "journal_open_unconfirmed_orphans": orphan_count,
        "skipped_records": mined.get("skipped_records", 0),
        "journal_files": [os.path.basename(p) for p in journal_paths],
        "notes": notes,
        "errors": errors,
    }
    return doc


def write_time_to_capture(doc: Dict[str, Any], path: str = OUTPUT_FILE) -> None:
    """Atomic write of the state file (tmp + replace)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(doc, f, indent=2, default=str)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _print_summary(doc: Dict[str, Any]) -> None:
    s = doc["session"]
    print(f"⏱️ UTC now: {doc['utc_now']} | weekend={s['weekend']} "
          f"| forex_open={s['forex_open']} ({', '.join(s['open_sessions']) or 'closed'}) "
          f"| next_daily_close={s['next_daily_close_utc']} "
          f"| next_funding={s['next_funding_utc']}")
    print(f"   journals={doc['journal_files']} skipped_records={doc['skipped_records']} "
          f"errors={len(doc['errors'])}")
    for n in doc.get("notes") or []:
        print(f"   NOTE: {n}")
    for sym, st in sorted(doc["symbols"].items()):
        def _f(v, nd=2):
            return f"{v:.{nd}f}" if isinstance(v, (int, float)) else "null"
        f = st.get("exits_filtered") or {}
        print(f"   {sym:6s} samples={st['samples']:<3d} "
              f"t1={_f(st['median_min_to_1pct'])}m t2={_f(st['median_min_to_2pct'])}m "
              f"t3={_f(st['median_min_to_3pct'])}m "
              f"win_exit={_f(st['median_min_win_exit'])}m(n={st['win_exits']}) "
              f"neg_exit={_f(st['median_min_negative_exit'])}m(n={st['negative_exits']}) "
              f"closes={st.get('closes')} counted={st.get('closes_counted')} "
              f"filtered(cost/hold/noprice)={f.get('below_cost', 0)}/{f.get('below_min_hold', 0)}/{f.get('no_price_move', 0)} "
              f"| {st['fastest_path_hint']}")
    for p in doc["open_positions"]:
        print(f"   OPEN {p['key']}: elapsed={p['elapsed_min']}m "
              f"velocity={p['velocity_pct_per_min']}%/min "
              f"implied_remaining={p['implied_remaining_min']}m err={p['error']}")


def main() -> int:
    from aureon.utils.console_utf8 import ensure_utf8_stdout
    ensure_utf8_stdout()
    doc = build_time_to_capture()
    write_time_to_capture(doc)
    _print_summary(doc)
    print(f"💾 wrote {OUTPUT_FILE}")
    return 0 if not doc["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
