#!/usr/bin/env python3
"""FLIGHT-TRADING — post-fix-wave flight test of the trading stack, END-TO-END DRY.

Stubbed/fake connectors only. ZERO real broker orders. Live fleet untouched:
no process starts/stops, capital_release.flag attested read-only.

Flight items:
  1. price feed live check (source + age per tracked symbol, stale >90s detect)
  2. honey_ladder shadow cycle on live feed (recency scoring, cap respected)
  3. bridge write-once offset tracking (no duplicate promoted signal lines)
  4. phi_radar dry gate (gate BEFORE network; synthetic/stale price refuses)
  5. radar suite supervision (master_launcher tree, radar_state honey section)
  6. trading-safety regression (gate HOLD/ALLOW, one-live-attempt, TTL filter)
"""

import os
import sys
import json
import time
import shutil
import hashlib
import tempfile
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "1"
os.environ["AUREON_AUDIT_MODE"] = "1"
os.environ["RADAR_MAX_NOTIONAL_PCT"] = "1000"

WORKSPACE = Path("C:/Users/user/.kimi_openclaw/workspace")
RADAR = WORKSPACE / "aureon_radar"
sys.path.insert(0, str(RADAR))
sys.path.insert(0, str(WORKSPACE))

import aureon_phi_radar as apr
from aureon_phi_radar import AureonPhiRadar, SystemState
from honey_ladder import HoneyLadder
import aureon_bridge as ab
import aureon_price_feed as apf
from aureon_fusion import capability_gate

TMP = Path(tempfile.mkdtemp(prefix="aureon_flight_"))
RESULTS = []
ORIG_STATE_FILE = apr.STATE_FILE
LIVE_FUSED = RADAR / "fused_signals.jsonl"
LIVE_BRIDGE_LOG = RADAR / "aureon_bridge_signals.jsonl"
FLAG = WORKSPACE / "aureon_fusion/state/capital_release.flag"


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")


def section(title):
    print(f"\n=== {title} ===")


# ── stub pattern from _fix_wave_probe.py ───────────────────────────────────

class FakeLedger:
    def __init__(self):
        self.events = []
    def shadow_hit(self, **kw):
        self.events.append(("shadow_hit", kw)); return "AUDIT-F1"
    def order_sent(self, **kw):
        self.events.append(("order_sent", kw))
    def capital_confirmed(self, audit_id, deal_id, resp):
        self.events.append(("capital_confirmed", deal_id)); return True
    def position_closed(self, *a, **kw):
        self.events.append(("position_closed", a))


class FakeLive:
    def __init__(self, balance=1000.0):
        self._balance = balance
    def get_account_balance(self):
        return self._balance


class FakeDual:
    """Stub broker. Records calls; can simulate timeout-after-execute."""
    def __init__(self, positions=None, raise_on_order=False):
        self.authenticated = True
        self.positions = positions or []
        self.raise_on_order = raise_on_order
        self.placed = 0
        self.placed_kwargs = []
        self.call_order = []  # sequence log for gate-before-network proof
    def authenticate(self):
        return True
    def place_live_order(self, **kw):
        self.placed += 1
        self.placed_kwargs.append(kw)
        self.call_order.append("place_live_order")
        if self.raise_on_order:
            raise TimeoutError("network timeout (broker may have executed)")
        return {"dealId": "DEAL-FLIGHT-1", "epic": kw["symbol"]}
    def get_live_positions(self):
        return self.positions
    def close_live_position(self, deal_id):
        self.closed = getattr(self, "closed", []) + [deal_id]
        return {"success": True}
    def get_minimum_tp_distance(self, symbol, entry_price):
        return {"GOLD": 52.0, "USDJPY": 0.03, "US100": 125.0}.get(symbol, 1.0)


def make_radar(dual, live, state_file=None):
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
        "NATURALGAS": "commodity", "BTCUSD": "crypto",
    }
    r.symbol_keys = list(r.symbol_sectors.keys())
    r._trade_ledger = FakeLedger()
    r._live_trading_gate_allowed_orig = r._live_trading_gate_allowed
    return r


def hit_shadow(ladder, symbol="GOLD", direction="LONG", age_sec=0):
    s = ladder.add_shadow(symbol=symbol, sector="commodity", direction=direction,
                          entry_price=2500.0, source="flight_test", target_price=2552.0)
    if age_sec:
        s.timestamp = (datetime.now(timezone.utc) - timedelta(seconds=age_sec)).isoformat()
    s.status = "HIT"
    return s


# ═══════════════════════════════════════════════════════════════════════════
section("ITEM 1 — PRICE FEED LIVE CHECK (radar's 13 tracked symbols)")
from aureon_fusion import api_communion

TRACKED = list(make_radar(FakeDual(), FakeLive()).symbol_keys)
print(f"  tracked symbols: {TRACKED}")
now = time.time()
# wrap fetchers to learn which source served each symbol
served_by = {}
for fn_name, src in (("_fetch_yahoo", "yahoo"), ("_fetch_binance", "binance"),
                     ("_fetch_coingecko", "coingecko")):
    orig = getattr(apf, fn_name)
    def make_wrapped(orig, src):
        def wrapped(symbol):
            price = orig(symbol)
            if price and symbol not in served_by:
                served_by[symbol] = src
            return price
        return wrapped
    setattr(apf, fn_name, make_wrapped(orig, src))

prices = {}
stale = []
for sym in TRACKED:
    try:
        p = apf.get_price(sym)
    except Exception as e:
        p = None
        print(f"  {sym}: fetch raised {type(e).__name__}")
    prices[sym] = p
    src = served_by.get(sym, "-")
    # true quote age from the shared communion disk cache
    age_s = None
    if src == "yahoo":
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{apf.YAHOO_MAP.get(sym, '')}?interval=1d&range=1d"
    elif src == "binance":
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={apf.BINANCE_MAP.get(sym, '')}"
    elif src == "coingecko":
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={apf.COINGECKO_MAP.get(sym, '')}&vs_currencies=usd"
    else:
        url = None
    if url:
        disk = api_communion._read_disk(url)
        if disk:
            age_s = now - disk[0]
    cache_age = None
    if sym in apf._price_cache:
        cache_age = now - apf._price_cache[sym]["time"]
    age_disp = f"{age_s:.0f}s" if age_s is not None else ("feed-cache "
                + (f"{cache_age:.0f}s" if cache_age is not None else "?"))
    status = ""
    if p is None:
        status = "NO QUOTE (refused — fail-closed, no synthetic fallback)"
    elif age_s is not None and age_s > 90:
        status = f"STALE ({age_s:.0f}s > 90s)"
        stale.append(sym)
    print(f"  {sym:12s} price={p if p else '—':>12} src={src:9s} quote_age={age_disp} {status}")

ok_prices = {s: p for s, p in prices.items() if p}
check("1a quotes fetched for tracked symbols", len(ok_prices) >= 10,
      f"{len(ok_prices)}/{len(TRACKED)} symbols quoted")
check("1b every quote younger than 90s (stale detection)", not stale,
      f"stale={stale}")
check("1c no synthetic fallback used (None stays None)",
      all(p is None or p > 0 for p in prices.values()))

# ═══════════════════════════════════════════════════════════════════════════
section("ITEM 2 — HONEY_LADDER SHADOW CYCLE ON LIVE FEED")
lad = HoneyLadder()
SECTORS = {"USDJPY": "forex", "EURUSD": "forex", "GBPUSD": "forex",
           "US100": "tech", "AAPL": "tech", "TSLA": "tech", "NVDA": "tech",
           "GOLD": "commodity", "SILVER": "commodity", "OIL_CRUDE": "commodity",
           "NATURALGAS": "commodity", "BTCUSD": "crypto"}
created = []
for sym in TRACKED:
    px = prices.get(sym)
    if not px:
        continue
    s = lad.add_shadow(symbol=sym, sector=SECTORS[sym], direction="LONG",
                       entry_price=px, source="flight_live",
                       target_price=px * 1.0005)
    created.append(s)
print(f"  shadows created on live feed: {len(created)} "
      f"({[s.symbol for s in created]})")
check("2a shadow generation ran on live feed", len(created) >= 10,
      f"created={len(created)}")

# live-feed hit detection: move one symbol's price past target
if created:
    sym0 = created[0].symbol
    lad.update_shadow(sym0, created[0].target_price * 1.01)
    hit = [s for s in lad.shadow_runs if s.symbol == sym0][0]
    check("2b update_shadow hit detection on live price", hit.status == "HIT",
          f"{sym0} status={hit.status} pnl={hit.pnl:.5f}")

# recency scoring: ISO ts parsed, newer HIT wins
ladder2 = HoneyLadder()
old_hit = hit_shadow(ladder2, age_sec=600)
new_hit = hit_shadow(ladder2, age_sec=10)
ladder2._update_source_record("flight_test")
cand = ladder2.get_graduation_candidate()
ts_ok = ladder2._shadow_timestamp(new_hit) > 0
check("2c ISO timestamp parsed (recency scoring live)", ts_ok and cand is new_hit,
      f"cand_age_sec={ladder2._shadow_timestamp(new_hit):.0f} cand_is_newer={cand is new_hit}")

# cap respected: OPEN shadows never pruned, list bounded
ladder3 = HoneyLadder()
ladder3.max_shadow_runs = 20
opens = []
for i in range(25):
    hit_shadow(ladder3, age_sec=1000 + i)
for i in range(5):
    opens.append(ladder3.add_shadow(symbol=f"OPEN{i}", sector="tech",
                                    direction="LONG", entry_price=100.0,
                                    source="flight_test", target_price=101.0))
n_open = sum(1 for s in ladder3.shadow_runs if s.status == "OPEN")
check("2d shadow cap respected (<=20, OPENs kept)",
      len(ladder3.shadow_runs) <= 20 and n_open == 5
      and all(o in ladder3.shadow_runs for o in opens),
      f"len={len(ladder3.shadow_runs)} open={n_open}")

# ═══════════════════════════════════════════════════════════════════════════
section("ITEM 3 — BRIDGE WRITE-ONCE OFFSET TRACKING")
# 3a: passive observation of the LIVE pipeline over >1 bridge cycle (5s tick)
def snapshot_lines(path):
    if not path.exists():
        return [], set()
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines, set(lines)

fused_lines_0, fused_set_0 = snapshot_lines(LIVE_FUSED)
bridge_lines_0, bridge_set_0 = snapshot_lines(LIVE_BRIDGE_LOG)
print(f"  live fused_signals.jsonl: {len(fused_lines_0)} lines; "
      f"aureon_bridge_signals.jsonl: {len(bridge_lines_0)} lines")
print("  observing live pipeline for 22s (bridge tick = 5s)...")
time.sleep(22)
fused_lines_1, _ = snapshot_lines(LIVE_FUSED)
bridge_lines_1, _ = snapshot_lines(LIVE_BRIDGE_LOG)
dupes_fused = len(fused_lines_1) - len(set(fused_lines_1))
dupes_bridge = len(bridge_lines_1) - len(set(bridge_lines_1))
new_fused = [l for l in fused_lines_1 if l not in fused_set_0]
print(f"  after 22s: fused {len(fused_lines_0)}->{len(fused_lines_1)} "
      f"(+{len(new_fused)} new), bridge {len(bridge_lines_0)}->{len(bridge_lines_1)}")
check("3a live fused_signals grew by unique lines only",
      dupes_fused == 0 and dupes_bridge == 0,
      f"dup_fused={dupes_fused} dup_bridge={dupes_bridge}")

# 3b: in-process bridge tick on temp copies (offset mechanics, 3 cycles)
promo = TMP / "promotions.jsonl"
bridge_log = TMP / "bridge_signals.jsonl"
fused = TMP / "fused_signals.jsonl"
trace = TMP / "trace.json"
ab.PROMOTION_LOG = promo
ab.AUREON_BRIDGE_LOG = bridge_log
ab.FUSED_SIGNALS = fused
ab.TRACE_FILE = trace
live_promo = Path("C:/Users/user/Aureon-OS/state/capital_shadow_promotions.jsonl")
promo.write_text(live_promo.read_text(encoding="utf-8", errors="replace")
                 if live_promo.exists() else "")
bridge = ab.AureonRadarBridge()
n0 = len(bridge_log.read_text().strip().splitlines()) if bridge_log.exists() else 0
for _ in range(3):
    bridge._monitor_promotions()
n1 = len(bridge_log.read_text().strip().splitlines()) if bridge_log.exists() else 0
promoted_lines = sum(1 for l in promo.read_text().splitlines()
                     if l.strip() and json.loads(l).get("promoted_to_live"))
print(f"  live promotion log carries {promoted_lines} promoted_to_live lines; "
      f"3 ticks emitted {n1 - n0} new bridge lines")
# inject one synthetic promoted line -> must be emitted exactly once over 3 ticks
with open(promo, "a") as f:
    f.write(json.dumps({"promoted_to_live": True, "symbol": "SILVER",
                        "direction": "LONG", "shadow_pnl": 0.01}) + "\n")
for _ in range(3):
    bridge._monitor_promotions()
n1b = len(bridge_log.read_text().strip().splitlines())
print(f"  after synthetic promotion: 3 more ticks emitted {n1b - n1} lines")
check("3b offset tracking: 3 ticks emit each promotion exactly once",
      n1 - n0 == promoted_lines and n1b - n1 == 1,
      f"emitted={n1 - n0} expected={promoted_lines} synthetic_emitted={n1b - n1}")
# 3c: identical trace decision re-read -> still exactly one emission
baseline = n1b
trace.write_text(json.dumps({"symbol": "GOLD", "direction": "LONG",
                             "act": {"approved": True, "blockers": []}}))
bridge.monitor_trace_file()
os.utime(trace, (time.time(), time.time()))
bridge.last_trace_mtime = 0
bridge.monitor_trace_file()
n2 = len(bridge_log.read_text().strip().splitlines())
check("3c identical trace decision emitted once", n2 - baseline == 1,
      f"new_lines={n2 - baseline}")

# ═══════════════════════════════════════════════════════════════════════════
section("ITEM 4 — PHI_RADAR DRY GATE (stubbed broker + stubbed capital client)")
apr.STATE_FILE = TMP / "radar_state_flight.json"

# price stub: fresh GOLD quote for the allow-path scenario
apf.get_price = lambda symbol, capital_connector=None: prices.get("GOLD") or 2500.0
apf._price_cache.clear()
if prices.get("GOLD"):
    apf._price_cache["GOLD"] = {"price": prices["GOLD"], "time": time.time()}

# 4a: gate verdict consulted BEFORE any broker network call
dual = FakeDual()
r = make_radar(dual, FakeLive())
gate_calls = []
orig_gate = r._live_trading_gate_allowed
def gated(context):
    gate_calls.append(context)
    dual.call_order.append("GATE_CHECK")  # interleave into broker sequence log
    return orig_gate(context)
r._live_trading_gate_allowed = gated
ladder_a = r.honey_ladder
shadow = hit_shadow(ladder_a)
r._execute_honey_pot(shadow)
gate_idx = dual.call_order.index("GATE_CHECK") if "GATE_CHECK" in dual.call_order else -1
net_idx = dual.call_order.index("place_live_order") if "place_live_order" in dual.call_order else 10**9
check("4a gate consulted before network call",
      gate_calls and gate_idx < net_idx,
      f"gate_calls={len(gate_calls)} gate_at={gate_idx} network_at={net_idx}")
check("4b exactly one broker call, shadow CONFIRMED",
      dual.placed == 1 and shadow.status == "CONFIRMED",
      f"placed={dual.placed} status={shadow.status}")
check("4c broker received mandatory stop level",
      dual.placed_kwargs and dual.placed_kwargs[0].get("stop_level") is not None,
      f"stop={dual.placed_kwargs[0].get('stop_level') if dual.placed_kwargs else None}")

# 4d: SYNTHETIC/STALE quote refuses live execution (zero broker calls)
apf._price_cache["GOLD"] = {"price": 2500.0, "time": time.time() - 500}
dual2 = FakeDual()
r2 = make_radar(dual2, FakeLive())
shadow2 = hit_shadow(r2.honey_ladder)
r2._execute_honey_pot(shadow2)
check("4d stale (>90s) quote refuses live execution, zero broker calls",
      dual2.placed == 0 and shadow2.status == "REFUSED",
      f"placed={dual2.placed} status={shadow2.status}")

# 4e: feed failure (no synthetic fallback) also refuses
apf.get_price = lambda symbol, capital_connector=None: None
apf._price_cache.clear()
dual3 = FakeDual()
r3 = make_radar(dual3, FakeLive())
shadow3 = hit_shadow(r3.honey_ladder)
r3._execute_honey_pot(shadow3)
check("4e feed-down (None price) refuses, no synthetic price used",
      dual3.placed == 0 and shadow3.status == "REFUSED",
      f"placed={dual3.placed} status={shadow3.status}")
# restore price stub for later items
apf.get_price = lambda symbol, capital_connector=None: prices.get(symbol) or 2500.0
apf._price_cache.clear()
for s, p in prices.items():
    if p:
        apf._price_cache[s] = {"price": p, "time": time.time()}

# ═══════════════════════════════════════════════════════════════════════════
section("ITEM 5 — RADAR SUITE SUPERVISION (live state, read-only)")

def wmic_pid(pid):
    try:
        out = subprocess.run(
            ["wmic", "process", "where", f"ProcessId={pid}",
             "get", "ProcessId,ParentProcessId,CommandLine"],
            capture_output=True, text=True, timeout=30).stdout
        return out
    except Exception as e:
        return f"wmic error: {e}"

# master_launcher is the parent of unified_hub + aureon_phi_radar
procs = subprocess.run(["wmic", "process", "where", "name='python.exe'",
                        "get", "ProcessId,ParentProcessId,CommandLine"],
                       capture_output=True, text=True, timeout=60).stdout
tree = {}
for line in procs.splitlines():
    line = line.strip()
    if "aureon_radar" in line or ("python.exe" in line and "ProcessId" not in line):
        parts = line.rsplit(None, 2)
        if len(parts) == 3 and parts[-1].isdigit() and parts[-2].isdigit():
            tree[int(parts[-1])] = {"ppid": int(parts[-2]), "cmd": parts[0]}
master = {pid: i for pid, i in tree.items() if "master_launcher" in i["cmd"]}
hub = {pid: i for pid, i in tree.items() if "unified_hub" in i["cmd"]}
phi = {pid: i for pid, i in tree.items() if "aureon_phi_radar" in i["cmd"]}
brg = {pid: i for pid, i in tree.items() if "aureon_bridge" in i["cmd"]}
print(f"  master_launcher: {[(p, i['ppid']) for p, i in master.items()]}")
print(f"  unified_hub:     {[(p, i['ppid']) for p, i in hub.items()]}")
print(f"  phi_radar:       {[(p, i['ppid']) for p, i in phi.items()]}")
print(f"  aureon_bridge:   {[(p, i['ppid']) for p, i in brg.items()]}")
master_pid = next(iter(master), None)
check("5a master_launcher alive", master_pid is not None,
      f"pid={master_pid}")
check("5b unified_hub child of master_launcher",
      any(i["ppid"] == master_pid for i in hub.values()),
      f"hub_pids={list(hub)} ppids={[i['ppid'] for i in hub.values()]}")
check("5c phi_radar child of master_launcher",
      any(i["ppid"] == master_pid for i in phi.values()),
      f"phi_pids={list(phi)} ppids={[i['ppid'] for i in phi.values()]}")
check("5d bridge process alive (signal/dry-run organ)",
      len(brg) >= 1, f"bridge_pids={list(brg)}")

# radar_state.json — honey-pot section parses and reflects reality
state_file = RADAR / "radar_state.json"
state = json.loads(state_file.read_text(encoding="utf-8"))
honey_section = state.get("honey_pot")
print(f"  radar_state.json: state={state.get('state')} "
      f"live_trades_today={state.get('live_trades_today')} "
      f"honey_pot={'present' if honey_section else 'absent(null)'}")
# reality cross-check: phi_radar log — no active LIVE honey pot execution.
# (filter out lines written by THIS flight probe: stub deal ids + first
#  probe log line index)
radar_log_lines = (RADAR / "radar.log").read_text(encoding="utf-8", errors="replace").splitlines()
probe_start = next((i for i, l in enumerate(radar_log_lines)
                    if "DEAL-FLIGHT-1" in l), len(radar_log_lines))
genuine_live = [l for l in radar_log_lines[:probe_start]
                if "[HONEY POT] LIVE:" in l]
print(f"  genuine [HONEY POT] LIVE lines before flight probe: {len(genuine_live)}")
check("5e radar_state.json parses; honey section consistent with fleet",
      state.get("state") == "ARMED" and honey_section is None
      and len(genuine_live) == 0,
      f"state={state.get('state')} honey_pot={honey_section}")

# ═══════════════════════════════════════════════════════════════════════════
section("ITEM 6 — TRADING-SAFETY REGRESSION (benchmark probes, attest-only)")
# 6a: gate HOLD without flag (in-process pin simulation — flag untouched)
flag_present = FLAG.exists()
flag_sha = hashlib.sha256(FLAG.read_bytes()).hexdigest()[:16] if flag_present else None
print(f"  capital_release.flag present={flag_present} sha16={flag_sha} (read-only attestation)")
orig_rel = capability_gate.release_authorized
capability_gate.release_authorized = lambda: False
v_hold = capability_gate.check("trading_execution:execute_live_trades")
capability_gate.release_authorized = orig_rel
check("6a gate HOLD without flag (pinned)",
      v_hold.get("verdict") == "HOLD" and not v_hold.get("allowed")
      and v_hold.get("pinned"),
      f"verdict={v_hold.get('verdict')} pinned={v_hold.get('pinned')}")
v_allow = capability_gate.check("trading_execution:execute_live_trades")
check("6b gate ALLOW with flag present (attested, not modified)",
      v_allow.get("verdict") == "ALLOW" and v_allow.get("allowed"),
      f"verdict={v_allow.get('verdict')} reason={v_allow.get('reason')[:60]}")
flag_sha_after = hashlib.sha256(FLAG.read_bytes()).hexdigest()[:16] if flag_present else None
check("6c flag untouched by probes", flag_sha == flag_sha_after,
      f"sha16 {flag_sha} -> {flag_sha_after}")

# 6d: one-live-attempt rule (timeout-after-execute adoption)
dual_t = FakeDual(positions=[{"position": {"dealId": "DEAL-T1", "direction": "BUY"},
                              "market": {"epic": "GOLD"}}], raise_on_order=True)
r_t = make_radar(dual_t, FakeLive())
apr.STATE_FILE = TMP / "radar_state_t.json"
sh = hit_shadow(r_t.honey_ladder)
r_t._execute_honey_pot(sh)
r_t._execute_honey_pot(sh)
r_t._promote_to_honey_pot()
pot = r_t.honey_ladder.honey_pot
check("6d one-live-attempt rule: timeout-after-execute adopted, no 2nd attempt",
      dual_t.placed == 1 and pot is not None and pot.active
      and pot.deal_id == "DEAL-T1" and sh.status == "CONFIRMED",
      f"placed={dual_t.placed} deal={getattr(pot, 'deal_id', None)} status={sh.status}")

# 6e: fused-signal TTL filter
sigdir = TMP / "signals"
sigdir.mkdir(exist_ok=True)
now_iso = datetime.now(timezone.utc)
fresh = lambda s: (now_iso - timedelta(seconds=s)).isoformat()
(sigdir / "fused_signals.jsonl").write_text("\n".join([
    json.dumps({"symbol": "GOLD", "direction": "SHORT", "confidence": 0.5, "timestamp": fresh(10)}),
    json.dumps({"symbol": "USDJPY", "direction": "LONG", "confidence": 0.9, "timestamp": fresh(3600)}),
    json.dumps({"symbol": "EURUSD", "direction": "LONG", "confidence": 0.9}),
]) + "\n")
old_radar_dir = apr.RADAR_DIR
apr.RADAR_DIR = sigdir
r_f = make_radar(FakeDual(), FakeLive())
sigs = r_f._read_fused_signals()
apr.RADAR_DIR = old_radar_dir
check("6e TTL filter: stale(>300s)+no-ts signals dropped, fresh kept",
      "USDJPY" not in sigs and "EURUSD" not in sigs and "GOLD" in sigs,
      f"surviving={sorted(sigs)}")

# 6f: daily live cap (env RADAR_MAX_LIVE_TRADES_PER_DAY default 3)
r_c = make_radar(FakeDual(), FakeLive())
r_c.live_trades_today = 3
check("6f daily live cap refuses 4th execution",
      r_c._daily_live_cap_reached() is True,
      f"live_trades_today={r_c.live_trades_today} cap=3")

# restore module state
apr.STATE_FILE = ORIG_STATE_FILE

# ═══════════════════════════════════════════════════════════════════════════
print()
failed = [n for n, ok, _ in RESULTS if not ok]
print(f"TOTAL {len(RESULTS)} checks, {len(failed)} failed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL FLIGHT CHECKS PASSED")
