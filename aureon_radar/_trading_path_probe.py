"""Dry end-to-end trading-path probe — 2026-09-07 health sweep.

NO live orders, NO network order paths, NO secrets. Exercises, in-process:
  A. expectancy_gate — 1% capture floor enforcement (below-floor REFUSED)
  B. juice math — manual NET recomputation vs state/juice_gate.json figures
  C. shadow_executor — persistence fix: book survives "restart", marks and
     protective closes resume on the reloaded engine
  D. capital_cfd_trader._tick_locked — multi-promotion budget loop, stubbed
     (no Capital API calls; all external touches replaced with fakes)

Run from aureon_radar/ with .env loaded and PYTHONPATH=<workspace>/aureon-os-upstream.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "exchange_adapters"))

PASS = []
FAIL = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  | {detail}" if detail else ""))


# ── A. expectancy gate ────────────────────────────────────────────────────────
import expectancy_gate as eg
import capture_floor

floor = capture_floor.load_capture_floor()
check("A1 capture floor loads as 1.0%", floor is not None and abs(floor - 0.01) < 1e-12,
      f"floor={floor}")

# Below-floor: conf 0.40 -> expected 0.80% < 1.0% floor -> REFUSED on every venue
# (on kraken the binding constraint is the 1.25x cost margin 1.125% > floor, so the
# reason there is refused_edge_below_cost — still a refusal, still fail-closed)
for venue in ("binance", "alpaca", "kraken"):
    v = eg.check(venue, "BTC", "buy", 0.001, None, 0.40)
    check(f"A2 below-floor expected_move refused [{venue}]",
          v["allowed"] is False and v["reason"] in
          ("refused_below_capture_floor", "refused_edge_below_cost"),
          f"expected={v['expected_move_pct']:.4f} reason={v['reason']}")

# Above-floor + above 1.25x cost: conf 0.90 -> 1.80%; binance cost 0.20% -> allow
v = eg.check("binance", "BTCUSDT", "buy", 0.001, None, 0.90)
check("A3 above-floor allowed [binance]", v["allowed"] is True and v["reason"] == "allow",
      f"expected={v['expected_move_pct']:.4f} required={v['required_move_pct']:.4f}")

# Kraken: cost 1.0%, 1.25x = 1.25% > floor; conf 0.55 -> 1.10% -> refused on cost margin
v = eg.check("kraken", "XBTUSD", "buy", 0.001, None, 0.55)
check("A4 kraken conf0.55 refused_edge_below_cost",
      v["allowed"] is False and v["reason"] == "refused_edge_below_cost",
      f"expected={v['expected_move_pct']:.4f} cost={v['round_trip_cost_pct']:.4f}")

# Kraken conf 0.90 -> 1.80% >= 1.25% -> allow
v = eg.check("kraken", "XBTUSD", "buy", 0.001, None, 0.90)
check("A5 kraken conf0.90 allowed", v["allowed"] is True, f"required={v['required_move_pct']:.4f}")

# Unknown venue fails closed
v = eg.check("notavenue", "X", "buy", 1, None, 0.99)
check("A6 unknown venue refused_unknown_venue",
      v["allowed"] is False and v["reason"] == "refused_unknown_venue")

# Kelly port: zero-loss guard
check("A7 kelly zero loss -> 0.0", eg.kelly_fraction_size(0.6, 0.02, 0.0, 1000.0) == 0.0)

# ── B. juice math — manual NET recomputation ──────────────────────────────────
from shadow_executor import VENUE_FEES, SLIPPAGE

jg = json.loads((HERE / "state" / "juice_gate.json").read_text(encoding="utf-8"))
check("B1 juice_gate floor is 1%", abs(jg["floor_pct"] - 0.01) < 1e-12, f"floor={jg['floor_pct']}")
check("B2 juice_gate errors empty", jg.get("errors") == [], f"errors={jg.get('errors')}")

cands = {(c["venue"], c["symbol"]): c for c in jg["candidates"]}


def recompute_cost(venue: str, spread_pct: float, vol_1h_pct: float) -> float:
    slip_side = SLIPPAGE * max(1.0, vol_1h_pct / 2.0)
    return 2.0 * VENUE_FEES[venue] + spread_pct + 2.0 * slip_side


ok = True
detail = ""
for key, c in cands.items():
    cb = c["cost_breakdown"]
    cost = recompute_cost(key[0], float(cb["spread_pct"]), float(cb["vol_1h_pct"]))
    net = float(c["gross_ev_pct"]) - cost
    if abs(cost - float(c["cost_pct"])) > 1e-9 or abs(net - float(c["net_ev_pct"])) > 1e-9:
        ok = False
        detail = f"mismatch at {key}: recomputed cost={cost:.6f} net={net:.6f} vs {c['cost_pct']}/{c['net_ev_pct']}"
        break
check("B3 all juice candidate costs+net match manual recomputation", ok, detail or f"n={len(cands)}")

# Verdict consistency against the floor
ok = True
for key, c in cands.items():
    net = float(c["net_ev_pct"])
    verdict = c["verdict"]
    if net >= 1.5 * 0.01 and verdict != "juice_worth_squeeze":
        ok = False; detail = f"{key} net {net:.4f} verdict {verdict}"; break
    if 0.01 <= net < 1.5 * 0.01 and verdict != "marginal":
        ok = False; detail = f"{key} net {net:.4f} verdict {verdict}"; break
    if net < 0.01 and verdict != "not_worth":
        ok = False; detail = f"{key} net {net:.4f} verdict {verdict}"; break
check("B4 all juice verdicts consistent with 1% floor / 1.5x band", ok, detail or f"n={len(cands)}")

# ── C. shadow persistence: restart resumes marks/closes ───────────────────────
from shadow_executor import ShadowEngine, ShadowOrder

tmp = Path(tempfile.mkdtemp(prefix="shadow_persist_probe_"))
eng1 = ShadowEngine("kraken", journal_path=tmp / "j.jsonl", ledger_path=tmp / "l.json")
price = {"bid": 100.0, "ask": 100.2, "last": 100.1, "source": "stub",
         "fetched_at": time.time()}


def q(_sym):
    return dict(price)


res = eng1.propose(ShadowOrder("kraken", "TESTUSD", "buy", 1.0, "probe", 0.9), q)
check("C1 engine1 opened", res["status"] == "opened", str(res.get("status")))
check("C2 book file written", (tmp / "shadow_book_kraken.json").exists())

eng2 = ShadowEngine("kraken", journal_path=tmp / "j.jsonl", ledger_path=tmp / "l.json")
check("C3 engine2 (post-restart) restored the open position",
      "TESTUSD" in eng2.positions and abs(eng2.positions["TESTUSD"].entry_price - res["fill_price"]) < 1e-9,
      f"positions={list(eng2.positions)}")

# protective close on the restored engine: price -2.1% -> stop_loss
price.update({"bid": 97.9, "ask": 98.0, "last": 97.95, "fetched_at": time.time()})
marks = eng2.mark_all(q, journal_marks=True, throttle_sec=0)
check("C4 mark_all on restored engine closed at stop",
      bool(marks["closed"]) and marks["closed"][0]["exit_reason"] == "stop_loss",
      str([m.get("exit_reason") for m in marks["closed"]]))
check("C5 book empty after close", eng2.positions == {})
lines = [json.loads(l) for l in (tmp / "j.jsonl").read_text(encoding="utf-8").splitlines()]
events = [l["event"] for l in lines]
check("C6 journal shows opened->mark/closed after simulated restart",
      "opened" in events and "closed" in events, str(events))

# ── D. capital_cfd_trader._tick_locked multi-promotion (stubbed, dry) ─────────
import capital_cfd_trader as cct


def make_shadow(sym: str, score: float, vt: float) -> object:
    s = types.SimpleNamespace()
    s.validated = True
    s.validation_time = vt
    s.created_at = vt
    s.score = score
    s.symbol = sym
    s.direction = "BUY"
    return s


def make_trader(budget_gbp: float, margin_per_pos: float, max_positions: int = 10):
    t = object.__new__(cct.CapitalCFDTrader)
    now = time.time()
    promoted: list = []

    def promote(shadow):
        pos = types.SimpleNamespace(symbol=shadow.symbol, margin=margin_per_pos)
        t.positions.append(pos)
        promoted.append(shadow.symbol)
        return pos

    t._deadman_guard = lambda _now: []
    t._harmonic_wiring_audit_at = now
    t._last_monitor = now                     # skip price/monitor stage
    t._update_position_prices = lambda: None
    t._monitor_positions = lambda: []
    t._update_shadows = lambda: None
    t._build_capital_risk_envelope = lambda: {"stress_buffer_before_gbp": budget_gbp}
    t.SHADOW_MIN_VALIDATE = 0.0
    t._get_price = lambda _sym: {"bid": 1.0, "offer": 1.0}
    t._build_shadow_promotion_gate = lambda shadow, _ticker: {
        "validation_window_secs": 0.0, "gate_passed": True}
    t._promote_shadow = promote
    t._position_margin_estimate = lambda pos: margin_per_pos
    t._position_notional = lambda pos: margin_per_pos
    t._cooldown_info = lambda *_a, **_k: None
    t._last_scan = now                        # skip scan stage
    t._build_lane_snapshot = lambda: None
    t._refresh_mycelium_snapshot = lambda force=False: None
    t._refresh_live_system_activity_snapshot = lambda: None
    t._refresh_probability_feed_snapshot = lambda: None
    t._publish_probability_feed = lambda: None
    t.status_lines = lambda: []
    t.positions = []
    return t, promoted


orig_max = cct.CFD_CONFIG["max_positions"]
try:
    # Case 1: budget 1000, margin 400 -> 3 promotions in ONE tick (multi-promote)
    cct.CFD_CONFIG["max_positions"] = 10
    t, promoted = make_trader(1000.0, 400.0)
    t.shadow_trades = [make_shadow(f"S{i}", 1.0 - i * 0.1, time.time()) for i in range(5)]
    t._tick_locked()
    check("D1 budget 1000/margin 400 promotes 3 in one tick", len(promoted) == 3,
          f"promoted={promoted}")
    check("D2 unaffordable shadows deferred (not dropped) after budget break",
          len(t.shadow_trades) == 2 and sorted(s.symbol for s in t.shadow_trades) == ["S3", "S4"],
          f"remaining={sorted(s.symbol for s in t.shadow_trades)}")

    # Case 2: zero budget -> zero promotions (fail-closed gate)
    t, promoted = make_trader(0.0, 400.0)
    t.shadow_trades = [make_shadow("Z0", 1.0, time.time())]
    t._tick_locked()
    check("D3 zero budget promotes nothing", len(promoted) == 0, f"promoted={promoted}")

    # Case 3: max_positions cap respected with plenty of budget
    cct.CFD_CONFIG["max_positions"] = 2
    t, promoted = make_trader(100000.0, 10.0)
    t.shadow_trades = [make_shadow(f"M{i}", 1.0, time.time()) for i in range(6)]
    t._tick_locked()
    check("D4 max_positions=2 caps promotions", len(promoted) == 2 and len(t.positions) == 2,
          f"promoted={promoted}")
finally:
    cct.CFD_CONFIG["max_positions"] = orig_max

# ── Summary ───────────────────────────────────────────────────────────────────
print()
print(f"PROBE RESULT: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
print("ALL PROBES PASSED")
