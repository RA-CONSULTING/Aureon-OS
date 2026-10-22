#!/usr/bin/env python3
"""Capture-floor wiring probe — owner decree 2026-09-06 (Gary Leckey).

Proves, with stubbed/monkeypatched boundaries only (no network, no keys,
temp journals):
  1. expectancy_gate.check: expected 0.6% move REFUSED citing the floor;
     expected 1.4% move ALLOWED (binance stubbed costs); kraken cost math
     unchanged (fee gate still binds above the floor).
  2. live_place path (shadow_binance, monkeypatched key-check + adapter):
     same floor refusal end-to-end, then an allowed order reaching the stub.
  3. TP clamp upward: shadow_executor TP floor, apply_floor_to_target, and
     honey_ladder.add_shadow rung targets (never downward).
  4. Corrupt/missing decree file -> no crash, floor absent, prior behavior.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
import tempfile
from pathlib import Path

RADAR_DIR = Path(__file__).resolve().parent
EX_DIR = RADAR_DIR / "exchange_adapters"
sys.path.insert(0, str(EX_DIR))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

passed = []


def ok(name, cond, extra=""):
    assert cond, f"PROBE FAILED: {name} {extra}"
    passed.append(name)
    print(f"  OK  {name} {extra}")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


gate = load("expectancy_gate", EX_DIR / "expectancy_gate.py")
se = load("shadow_executor_probe", EX_DIR / "shadow_executor.py")
cf = load("capture_floor_probe", EX_DIR / "capture_floor.py")
hl = load("honey_ladder_probe", RADAR_DIR / "honey_ladder.py")

print("== 1. expectancy_gate.check (real decree file) ==")
v_low = gate.check("binance", "BTCUSDT", "buy", 0.001, None, 0.30)
print("   ", json.dumps(v_low, sort_keys=True))
ok("0.6% expected refused", not v_low["allowed"], v_low["reason"])
ok("floor reason cited", v_low["reason"] == "refused_below_capture_floor")
ok("detail says below capture floor 1.0%",
   "below capture floor 1.0%" in (v_low.get("detail") or ""),
   v_low.get("detail"))
ok("floor + required reported",
   v_low.get("capture_floor_pct") == 0.01 and v_low.get("required_move_pct") == 0.01)

v_high = gate.check("binance", "BTCUSDT", "buy", 0.001, None, 0.70)
print("   ", json.dumps(v_high, sort_keys=True))
ok("1.4% expected allowed", v_high["allowed"], v_high["reason"])

v_kraken = gate.check("kraken", "XBTUSD", "buy", 0.001, None, 0.55)
print("   ", json.dumps(v_kraken, sort_keys=True))
ok("kraken cost gate preserved (1.10% < 1.25x0.90%)",
   (not v_kraken["allowed"]) and v_kraken["reason"] == "refused_edge_below_cost",
   v_kraken["reason"])

print("== 2. live_place path (shadow_binance, key-check + adapter stubbed) ==")
sb = load("shadow_binance_probe", EX_DIR / "shadow_binance.py")

tmpdir = Path(tempfile.mkdtemp(prefix="floor_probe_"))
engine = se.ShadowEngine("binance",
                         journal_path=tmpdir / "shadow_trades.jsonl",
                         ledger_path=tmpdir / "shadow_ledger_summary.json")
sb.get_engine = lambda: engine
sb.env_has_keys = lambda names, env_path=None: (True, {n: True for n in names})


class _StubAdapter:
    calls = []

    def place_order(self, symbol, side, qty, dry_run=False):
        self.calls.append({"symbol": symbol, "side": side, "qty": qty})
        return {"status": "filled_stub", "symbol": symbol}


_stub = _StubAdapter()
sb._get_adapter = lambda: _stub

refused = sb.live_place("BTCUSDT", "buy", 0.001, confidence=0.30)
print("   ", json.dumps(refused, sort_keys=True))
ok("live_place 0.6% refused", refused.get("status") == "refused")
ok("live_place floor reason", refused.get("reason") == "refused_below_capture_floor")
lines = [json.loads(l) for l in engine.journal_path.read_text().splitlines()]
floor_lines = [l for l in lines if l.get("reason") == "refused_below_capture_floor"]
ok("journal cites floor explicitly",
   any("below capture floor 1.0%" in (l.get("detail") or "") for l in floor_lines),
   floor_lines[0].get("detail") if floor_lines else "NO LINE")

allowed = sb.live_place("BTCUSDT", "buy", 0.001, confidence=0.70)
print("   ", json.dumps(allowed, sort_keys=True))
ok("live_place 1.4% allowed -> adapter called",
   allowed.get("status") == "filled_stub" and len(_stub.calls) == 1)

print("== 3. TP clamp upward only ==")
ok("executor TP = max(3%, floor 1%) = 3%",
   se.effective_take_profit_pct() == 0.03, se.effective_take_profit_pct())
ok("tp pct clamped 0.5% -> 1.0%", cf.apply_floor_to_tp_pct(0.005, 0.01) == 0.01)
ok("LONG target raised 100.05 -> 101.0",
   cf.apply_floor_to_target("LONG", 100.0, 100.05, 0.01) == 101.0)
ok("SHORT target lowered-to-floor 99.95 -> 99.0",
   cf.apply_floor_to_target("SHORT", 100.0, 99.95, 0.01) == 99.0)
ok("no downward clamp (105 stays 105)",
   cf.apply_floor_to_target("LONG", 100.0, 105.0, 0.01) == 105.0)

ladder = hl.HoneyLadder()
run = ladder.add_shadow("PROBE", "tech", "LONG", 100.0, "probe", target_price=100.05)
print("    add_shadow target:", run.target_price)
ok("honey_ladder rung target raised to 1%", abs(run.target_price - 101.0) < 1e-9,
   run.target_price)
run2 = ladder.add_shadow("PROBE2", "tech", "LONG", 100.0, "probe", target_price=105.0)
ok("honey_ladder target beyond floor untouched", run2.target_price == 105.0)

print("== 4. corrupt / missing decree file -> no crash, prior behavior ==")
bad_path = tmpdir / "corrupt.json"
bad_path.write_text("{not json", encoding="utf-8")
ok("corrupt file -> None (floor absent)", cf.load_capture_floor(bad_path) is None)
missing = cf.load_capture_floor(tmpdir / "does_not_exist.json")
ok("missing file -> None (floor absent)", missing is None)

# End-to-end: swap the REAL decree file for garbage, verify prior behavior.
real_path = cf.FLOOR_PATH
real_content = real_path.read_text(encoding="utf-8")
try:
    real_path.write_text("{corrupt", encoding="utf-8")
    v_corrupt = gate.check("binance", "BTCUSDT", "buy", 0.001, None, 0.30)
    print("   ", json.dumps(v_corrupt, sort_keys=True))
    ok("corrupt decree -> floor absent in verdict", v_corrupt.get("capture_floor_pct") is None)
    ok("corrupt decree -> prior behavior (0.6% allowed on binance costs)",
       v_corrupt["allowed"] and v_corrupt["reason"] == "allow",
       v_corrupt["reason"])
    ok("corrupt decree -> executor TP back to 3%", se.effective_take_profit_pct() == 0.03)
finally:
    real_path.write_text(real_content, encoding="utf-8")

v_restored = gate.check("binance", "BTCUSDT", "buy", 0.001, None, 0.30)
ok("decree restored -> floor refusal again",
   (not v_restored["allowed"]) and v_restored["reason"] == "refused_below_capture_floor")

print()
print(f"PROBE PASSED ({len(passed)} checks)")
