#!/usr/bin/env python3
"""Probe: honey_ladder MISS recording + honest phi_win_rate.

Simulates ladders with forced win / stale-expiry / max-hold-expiry outcomes
and verifies:
  1. Losing runs are recorded as 'MISS' (never left OPEN, never HIT).
  2. phi_win_rate drops below 1.0 when losses exist.
  3. Division-by-zero guard: no terminal runs -> 0.0, not a crash.

In-memory only — touches no state files, no fabricated persisted data.
"""

import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from honey_ladder import HoneyLadder  # noqa: E402


def backdate(run, seconds):
    run.timestamp = datetime.fromtimestamp(
        time.time() - seconds, tz=timezone.utc).isoformat()


def main():
    failures = []

    def check(label, cond):
        print(f"  {'PASS' if cond else 'FAIL'}: {label}")
        if not cond:
            failures.append(label)

    # ── Scenario 1: forced win + forced stale expiry on the same source ──
    print("Scenario 1: one WIN + one stale-expiry MISS (same source)")
    ladder = HoneyLadder()
    win = ladder.add_shadow("AAA", "tech", "LONG", 100.0, "probe_src")
    ladder.update_shadow("AAA", 100.1)  # >= target (100.05) → HIT
    check("win run recorded HIT", win.status == "HIT")

    loss = ladder.add_shadow("BBB", "tech", "LONG", 200.0, "probe_src")
    backdate(loss, ladder.max_hold_seconds + 5)
    # Tick a DIFFERENT symbol: the stale sweep must still catch BBB.
    ladder.update_shadow("AAA", 100.2)
    check("stale run recorded MISS (cross-symbol sweep)", loss.status == "MISS")
    check("stale run pnl not positive", loss.pnl <= 0.0)

    rec = ladder.source_records["probe_src"]
    print(f"  -> record: hits={rec.hits} misses={rec.misses} "
          f"phi_win_rate={rec.phi_win_rate:.3f}")
    check("hits == 1", rec.hits == 1)
    check("misses == 1", rec.misses == 1)
    check("phi_win_rate < 1.0 with a loss", rec.phi_win_rate < 1.0)
    # Expected: PHI-decay-weighted ratio. The MISS was backdated past
    # max_hold so its weight is slightly below the fresh HIT's — the
    # weighted rate must match exactly.
    now = time.time()
    weights = {r.status: ladder._phi_decay_weight(
        max(0.0, now - ladder._shadow_timestamp(r)))
        for r in ladder.shadow_runs if r.source == "probe_src"}
    expected = weights.get("HIT", 0.0) / sum(weights.values())
    check(f"phi_win_rate == weighted expectation ({expected:.3f})",
          abs(rec.phi_win_rate - expected) < 1e-9)

    # ── Scenario 2: all losses → rate 0.0, rung stays 0 ──
    print("Scenario 2: all-loss source fails closed to 0.0")
    ladder2 = HoneyLadder()
    for i in range(3):
        r = ladder2.add_shadow(f"LOSER{i}", "crypto", "SHORT", 50.0, "bad_src")
        backdate(r, ladder2.max_hold_seconds + 5)
    ladder2.update_shadow("LOSER0", 50.0)
    rec2 = ladder2.source_records["bad_src"]
    print(f"  -> record: hits={rec2.hits} misses={rec2.misses} "
          f"phi_win_rate={rec2.phi_win_rate:.3f} rung={rec2.current_ladder_rung}")
    check("3 misses recorded", rec2.misses == 3)
    check("phi_win_rate == 0.0 for all-loss source", rec2.phi_win_rate == 0.0)
    check("rung stays 0 (no auto-arm possible)", rec2.current_ladder_rung == 0)

    # ── Scenario 3: division-by-zero guard, no terminal runs ──
    print("Scenario 3: source with only OPEN runs → 0.0, no crash")
    ladder3 = HoneyLadder()
    ladder3.add_shadow("IDLE", "forex", "LONG", 10.0, "quiet_src")
    rec3 = ladder3.source_records.get("quiet_src")
    wr3 = rec3.phi_win_rate if rec3 else ladder3._calculate_phi_win_rate("quiet_src")
    print(f"  -> phi_win_rate={wr3:.3f}")
    check("no-terminal-runs rate is 0.0", wr3 == 0.0)

    # ── Scenario 4: unparseable timestamp is indeterminate → MISS ──
    print("Scenario 4: corrupt timestamp fails closed to MISS")
    ladder4 = HoneyLadder()
    r4 = ladder4.add_shadow("CORRUPT", "tech", "LONG", 5.0, "corrupt_src")
    r4.timestamp = "not-a-timestamp"
    ladder4.update_shadow("CORRUPT", 5.0)
    check("corrupt-timestamp run recorded MISS", r4.status == "MISS")
    rec4 = ladder4.source_records["corrupt_src"]
    check("corrupt run counts as miss, not hit", rec4.misses == 1 and rec4.hits == 0)

    print()
    if failures:
        print(f"PROBE FAILED ({len(failures)}): {failures}")
        return 1
    print("PROBE PASSED: MISS recorded, phi_win_rate honest, guards hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
