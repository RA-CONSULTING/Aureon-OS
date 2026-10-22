#!/usr/bin/env python3
"""Fix-wave verification probe — TRADING-CRITICAL workstream.

Stubbed/fake connectors only. ZERO real broker orders. Exercises:
  A. timeout-after-execute  -> exactly one live attempt, position adopted
  B. refused-gate           -> shadow REFUSED once, never re-fires
  C. restart w/ open pos    -> honey pot persisted + reconciled on load
  D. panic()                -> closes positions, KeyError path surfaces
  E. bridge                 -> write-once, no duplicate lines over 3 cycles
  F. fused signals          -> TTL filter + priority order
  G. honey ladder           -> ISO recency scoring + shadow cap/prune
  H. dual capital           -> routed through hardened _request layer
  I. price feed             -> no synthetic fallback, stale refuse
"""

import os
import sys
import json
import time
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
os.environ["AUREON_AUDIT_MODE"] = "1"
# Probe sizing: £1000 balance vs GOLD £2500 notional needs a wider test cap
os.environ["RADAR_MAX_NOTIONAL_PCT"] = "1000"

RADAR = Path("C:/Users/user/.kimi_openclaw/workspace/aureon_radar")
sys.path.insert(0, str(RADAR))

import aureon_phi_radar as apr
from aureon_phi_radar import AureonPhiRadar, SystemState
from honey_ladder import HoneyLadder, HoneyPot, ShadowLadderRun
import aureon_bridge as ab
import aureon_dual_capital as adc
import aureon_price_feed as apf

TMP = Path(tempfile.mkdtemp(prefix="aureon_fixwave_"))
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")


def make_radar(dual, live, gate_allowed=True, state_file=None):
    """Build a radar without __init__ (no real connectors, no real state)."""
    r = AureonPhiRadar.__new__(AureonPhiRadar)
    r.state = SystemState.ARMED
    r.honey_ladder = HoneyLadder()
    r.capital_dual = dual
    r.capital_live = live
    r.live_trades_today = 0
    r.profit_today = 0.0
    r._live_trades_date = datetime.now(timezone.utc).date().isoformat()
    r.price_stale_after_sec = 90.0
    r._honey_pot_reconciled = False
    r._persisted_honey_pot = None
    r.symbol_sectors = {
        "USDJPY": "forex", "EURUSD": "forex", "GBPUSD": "forex",
        "US100": "tech", "AAPL": "tech", "TSLA": "tech", "NVDA": "tech",
        "GOLD": "commodity", "SILVER": "commodity", "OIL_CRUDE": "commodity",
        "NATURALGAS": "commodity", "BTCUSD": "crypto", "ETHUSD": "crypto",
    }
    if state_file is not None:
        r._state_file_override = state_file
    r._trade_ledger = FakeLedger()
    r._live_trading_gate_allowed = lambda ctx: gate_allowed
    return r


class FakeLedger:
    def __init__(self):
        self.events = []

    def shadow_hit(self, **kw):
        self.events.append(("shadow_hit", kw))
        return "AUDIT-1"

    def order_sent(self, **kw):
        self.events.append(("order_sent", kw))

    def capital_confirmed(self, audit_id, deal_id, resp):
        self.events.append(("capital_confirmed", deal_id))
        return True

    def position_closed(self, *a, **kw):
        self.events.append(("position_closed", a))


class FakeLive:
    def __init__(self, balance=1000.0):
        self._balance = balance

    def get_account_balance(self):
        return self._balance


class FakeDual:
    """Simulates: timeout-after-execute + positions API."""

    def __init__(self, positions=None, raise_on_order=False):
        self.authenticated = True
        self.positions = positions or []
        self.raise_on_order = raise_on_order
        self.placed = 0
        self.placed_kwargs = []

    def authenticate(self):
        return True

    def place_live_order(self, **kw):
        self.placed += 1
        self.placed_kwargs.append(kw)
        if self.raise_on_order:
            raise TimeoutError("network timeout (broker may have executed)")
        return {"dealId": "DEAL-NEW-1", "epic": kw["symbol"]}

    def get_live_positions(self):
        return self.positions

    def close_live_position(self, deal_id):
        self.closed = getattr(self, "closed", []) + [deal_id]
        return {"success": True}

    def get_minimum_tp_distance(self, symbol, entry_price):
        table = {"GOLD": 52.0, "USDJPY": 0.03, "US100": 125.0}
        return table.get(symbol, 1.0)


def hit_shadow(ladder, symbol="GOLD", direction="LONG", age_sec=0):
    s = ladder.add_shadow(symbol=symbol, sector="commodity", direction=direction,
                          entry_price=2500.0, source="scanner", target_price=2552.0)
    if age_sec:
        ts = datetime.now(timezone.utc) - timedelta(seconds=age_sec)
        s.timestamp = ts.isoformat()
    s.status = "HIT"
    return s


def patch_price(price, cache_age=1.0):
    apf.get_price = lambda symbol, capital_connector=None: price
    apf._price_cache.clear()
    if price is not None:
        apf._price_cache["GOLD"] = {"price": price, "time": time.time() - cache_age}


# Feed stub active from the start (scenario A sizes off GOLD=2500)
patch_price(2500.0)


print("=== A. timeout-after-execute: one live attempt, reconciliation adopts position ===")
ladder = HoneyLadder()
dual = FakeDual(positions=[{"position": {"dealId": "DEAL-123", "direction": "BUY"},
                            "market": {"epic": "GOLD"}}], raise_on_order=True)
r = make_radar(dual, FakeLive())
r.honey_ladder = ladder
shadow = hit_shadow(ladder)
# state file redirect
state_file = TMP / "radar_state_a.json"
apr.STATE_FILE = state_file
r._execute_honey_pot(shadow)
check("A1 one place_live_order call", dual.placed == 1, f"placed={dual.placed}")
check("A2 honey pot active w/ reconciled deal", ladder.honey_pot and ladder.honey_pot.active
      and ladder.honey_pot.deal_id == "DEAL-123", f"deal={getattr(ladder.honey_pot,'deal_id',None)}")
check("A3 shadow CONFIRMED", shadow.status == "CONFIRMED", shadow.status)
# second cycle re-selection attempt
r._execute_honey_pot(shadow)
r._promote_to_honey_pot()
check("A4 second call places nothing", dual.placed == 1, f"placed={dual.placed}")
check("A5 honey pot persisted to state", state_file.exists() and
      json.loads(state_file.read_text()).get("honey_pot", {}).get("deal_id") == "DEAL-123")

print("=== B. refused-gate: REFUSED once, never re-fires ===")
ladder_b = HoneyLadder()
dual_b = FakeDual()
r_b = make_radar(dual_b, FakeLive(), gate_allowed=False)
r_b.honey_ladder = ladder_b
shadow_b = hit_shadow(ladder_b)
r_b._execute_honey_pot(shadow_b)
r_b._execute_honey_pot(shadow_b)
r_b._execute_honey_pot(shadow_b)
check("B1 zero orders placed", dual_b.placed == 0)
check("B2 shadow REFUSED", shadow_b.status == "REFUSED", shadow_b.status)
check("B3 graduation candidate none", ladder_b.get_graduation_candidate() is None)

print("=== C. restart with open position: persist + reconcile on load ===")
pot_dict = {"deal_id": "DEAL-P9", "symbol": "GOLD", "sector": "commodity",
            "direction": "LONG", "entry_price": 2500.0, "target_price": 2552.0,
            "size": 0.34, "source": "scanner", "opened_at": time.time() - 30,
            "max_hold_seconds": 600, "audit_id": "AUDIT-9"}
state_c = TMP / "radar_state_c.json"
state_c.write_text(json.dumps({"state": "ARMED", "live_trades_today": 0,
                               "honey_pot": pot_dict}))
# C1: position still open server-side -> restored
r_c = make_radar(FakeDual(positions=[{"position": {"dealId": "DEAL-P9", "direction": "BUY"},
                                      "market": {"epic": "GOLD"}}]), FakeLive(),
                 state_file=state_c)
apr.STATE_FILE = state_c
r_c._load_state()
check("C1 persisted pot loaded", getattr(r_c, "_persisted_honey_pot", None) is not None)
r_c._reconcile_persisted_honey_pot()
check("C2 pot restored (open server-side)",
      r_c.honey_ladder.honey_pot is not None and r_c.honey_ladder.honey_pot.active
      and r_c.honey_ladder.honey_pot.deal_id == "DEAL-P9"
      and r_c.honey_ladder.honey_pot.size == 0.34)
# C3: position closed server-side -> cleared (no ghost blocking, no dup trade)
r_c2 = make_radar(FakeDual(positions=[]), FakeLive(), state_file=state_c)
apr.STATE_FILE = state_c
r_c2._load_state()
r_c2._reconcile_persisted_honey_pot()
check("C3 stale pot cleared", r_c2.honey_ladder.honey_pot is None)
# C4: positions API error -> pot kept ACTIVE (fail-closed, no duplicate)

class ErrorDual(FakeDual):
    def get_live_positions(self):
        raise ConnectionError("positions API down")

r_c3 = make_radar(ErrorDual(), FakeLive(), state_file=state_c)
apr.STATE_FILE = state_c
r_c3._load_state()
r_c3._reconcile_persisted_honey_pot()
check("C4 pot kept active on API error (fail-closed)",
      r_c3.honey_ladder.honey_pot is not None and r_c3.honey_ladder.honey_pot.active)

print("=== D. panic(): closes positions, KeyError path fixed ===")
dual_d = FakeDual(positions=[
    {"position": {"dealId": "DEAL-A", "direction": "BUY"}, "market": {"epic": "GOLD"}},
    {"market": {"epic": "US100"}},  # malformed: no position/dealId (old KeyError trigger)
    {"position": {"dealId": "DEAL-B", "direction": "SELL"}, "market": {"epic": "USDJPY"}},
])
r_d = make_radar(dual_d, FakeLive())
apr.STATE_FILE = TMP / "radar_state_d.json"
r_d.panic()
check("D1 both valid positions closed", sorted(getattr(dual_d, "closed", [])) == ["DEAL-A", "DEAL-B"],
      str(getattr(dual_d, "closed", None)))
check("D2 PANIC state saved", json.loads((TMP / "radar_state_d.json").read_text())["state"] == "PANIC")

print("=== E. bridge: write-once across 3 cycles ===")
promo = TMP / "promotions.jsonl"
bridge_log = TMP / "bridge_signals.jsonl"
fused = TMP / "fused_signals_e.jsonl"
trace = TMP / "trace.json"
ab.PROMOTION_LOG = promo
ab.AUREON_BRIDGE_LOG = bridge_log
ab.FUSED_SIGNALS = fused
ab.TRACE_FILE = trace
promo.write_text("")
bridge = ab.AureonRadarBridge()
promo_line = {"promoted_to_live": True, "symbol": "GOLD", "direction": "LONG", "shadow_pnl": 0.01}
with open(promo, "a") as f:
    f.write(json.dumps(promo_line) + "\n")
for _ in range(3):
    bridge._monitor_promotions()
n_bridge = len(bridge_log.read_text().strip().splitlines())
check("E1 exactly 1 bridge line after 3 cycles", n_bridge == 1, f"lines={n_bridge}")
# new promotion appended -> processed once
with open(promo, "a") as f:
    f.write(json.dumps({**promo_line, "symbol": "SILVER"}) + "\n")
for _ in range(3):
    bridge._monitor_promotions()
n_bridge2 = len(bridge_log.read_text().strip().splitlines())
check("E2 second promotion written once", n_bridge2 == 2, f"lines={n_bridge2}")
# trace-file dedupe (bridge_log baseline: 2 promotion lines already there)
baseline_bridge = len(bridge_log.read_text().strip().splitlines())
trace.write_text(json.dumps({"symbol": "GOLD", "direction": "LONG",
                             "act": {"approved": True, "blockers": []}}))
bridge.monitor_trace_file()
os.utime(trace, (time.time(), time.time()))
bridge.last_trace_mtime = 0  # force re-read of identical content
bridge.monitor_trace_file()
n_bridge3 = len(bridge_log.read_text().strip().splitlines()) - baseline_bridge
check("E3 identical trace decision emitted once", n_bridge3 == 1, f"new_lines={n_bridge3}")

print("=== F. fused signals: TTL + priority ===")
sigdir = TMP / "signals"
sigdir.mkdir(exist_ok=True)
now = datetime.now(timezone.utc)
fresh = lambda s: (now - timedelta(seconds=s)).isoformat()
(sigdir / "fused_signals.jsonl").write_text("\n".join([
    json.dumps({"symbol": "GOLD", "direction": "SHORT", "confidence": 0.5, "timestamp": fresh(10)}),
    json.dumps({"symbol": "USDJPY", "direction": "LONG", "confidence": 0.9, "timestamp": fresh(3600)}),
    json.dumps({"symbol": "EURUSD", "direction": "LONG", "confidence": 0.9}),  # no ts -> dropped
]) + "\n")
(sigdir / "aureon_bridge_signals.jsonl").write_text(json.dumps(
    {"symbol": "GOLD", "direction": "LONG", "confidence": 0.95, "timestamp": fresh(5)}) + "\n")
(sigdir / "stock_signals.jsonl").write_text(json.dumps(
    {"symbol": "GOLD", "direction": "SHORT", "confidence": 0.99, "timestamp": fresh(5)}) + "\n")
old_radar_dir = apr.RADAR_DIR
apr.RADAR_DIR = sigdir
r_f = make_radar(FakeDual(), FakeLive())
sigs = r_f._read_fused_signals()
apr.RADAR_DIR = old_radar_dir
check("F1 stale (>TTL) signal dropped", "USDJPY" not in sigs, str(sorted(sigs)))
check("F2 no-timestamp signal dropped", "EURUSD" not in sigs)
check("F3 bridge overrides hub/stock for GOLD",
      sigs.get("GOLD", {}).get("direction") == "LONG"
      and sigs["GOLD"].get("confidence") == 0.95,
      json.dumps(sigs.get("GOLD", {})))

print("=== G. honey ladder: ISO recency + cap/prune ===")
lad = HoneyLadder()
old_hit = hit_shadow(lad, age_sec=600)
new_hit = hit_shadow(lad, age_sec=10)
# production path updates the source record on HIT; do the same so win rate
# is non-zero and recency actually decides
lad._update_source_record("scanner")
cand = lad.get_graduation_candidate()
check("G1 recency scoring picks newer HIT", cand is new_hit,
      f"cand_age={cand.timestamp if cand else None}")
# cap + prune
lad2 = HoneyLadder()
lad2.max_shadow_runs = 20
opens = []
for i in range(25):
    s = hit_shadow(lad2, age_sec=1000 + i)
for i in range(5):
    s = lad2.add_shadow(symbol=f"OPEN{i}", sector="tech", direction="LONG",
                        entry_price=100.0, source="scanner", target_price=101.0)
    opens.append(s)
n_open = sum(1 for s in lad2.shadow_runs if s.status == "OPEN")
check("G2 shadow list bounded", len(lad2.shadow_runs) <= 20, f"len={len(lad2.shadow_runs)}")
check("G3 OPEN shadows never pruned", n_open == 5 and all(o in lad2.shadow_runs for o in opens))

print("=== H. dual capital: hardened request layer ===")
class FakeResp:
    def __init__(self, code, data):
        self.status_code = code
        self.text = json.dumps(data)
        self._data = data
    def json(self):
        return self._data

class FakeClient:
    def __init__(self):
        self.calls = []
        self.enabled = True
        self.demo_mode = False
    def _request(self, method, path, params=None, json_body=None):
        self.calls.append((method, path, json_body))
        if path == "/markets":
            return FakeResp(200, {"markets": [{"epic": "GOLD", "instrumentName": "Gold"}]})
        if method == "POST":
            return FakeResp(200, {"dealReference": "DEAL-H1"})
        if method == "GET":
            return FakeResp(200, {"positions": [{"position": {"dealId": "DEAL-H1"}}]})
        if method == "DELETE":
            return FakeResp(200, {})
        return FakeResp(500, {})

conn = adc.DualCapitalConnector.__new__(adc.DualCapitalConnector)
conn.demo = FakeClient()
conn.live = FakeClient()
res = conn._place_order(conn.live, "GOLD", "BUY", 1.0, stop_level=2448.0, profit_level=2552.0)
check("H1 order placed via _request", res.get("dealId") == "DEAL-H1" and
      ("POST", "/positions", conn.live.calls[-1][2]) == tuple(conn.live.calls[-1]) and
      conn.live.calls[-1][2].get("stopLevel") == 2448.0, json.dumps(res))
pos = conn._get_positions(conn.live)
check("H2 positions via _request", len(pos) == 1 and conn.live.calls[-1][0] == "GET")
check("H3 close via _request", conn._close_position(conn.live, "DEAL-H1").get("success") is True
      and conn.live.calls[-1][0] == "DELETE")

print("=== I. price feed: no synthetic fallback, stale refuse ===")
patch_price(None)
r_i = make_radar(FakeDual(), FakeLive())
check("I1 feed failure -> None (no synthetic price)", r_i._get_price("GOLD") is None)
patch_price(2500.0, cache_age=1.0)
check("I2 fresh price ok", r_i._get_price("GOLD", max_age_sec=90) == 2500.0)
patch_price(2500.0, cache_age=500.0)
check("I3 stale (>90s) price refused", r_i._get_price("GOLD", max_age_sec=90) is None)

print()
failed = [n for n, ok, _ in RESULTS if not ok]
print(f"TOTAL {len(RESULTS)} checks, {len(failed)} failed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL PROBES PASSED")
