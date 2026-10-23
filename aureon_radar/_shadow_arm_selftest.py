"""Functional test of ShadowArm in isolation — does NOT touch the live hub loop.

Verifies:
 1. Inert when shadow modules don't exist (no raise, debug-only).
 2. Symbol routing: BTC -> kraken+binance+alpaca; ETH -> 3 venues; AAPL -> alpaca only;
    EURUSD/USDJPY -> no calls.
 3. Confidence gate (0.55) and NEUTRAL skip.
 4. Every venue call individually exception-proof.
 5. mark_all called once per cycle and exception-proof.
"""
import sys
import types
import logging

sys.path.insert(0, r"C:/Users/user/.kimi_openclaw/workspace/aureon_radar")
import unified_hub  # noqa: E402  (top-level guards run; fine in this subprocess)
from unified_hub import ShadowArm, UnifiedSignal

logging.getLogger().setLevel(logging.DEBUG)

calls = {"propose": [], "mark": []}


def make_stub(name, fail=False):
    mod = types.ModuleType(f"aureon_shadow_{name}")

    def propose_signal(symbol, side, qty, signal_source, signal_confidence):
        if fail:
            raise RuntimeError(f"{name} exploded")
        calls["propose"].append((name, symbol, side, qty, signal_source, signal_confidence))
        return {"event": "opened", "venue": name, "symbol": symbol}

    def mark_all():
        if fail:
            raise RuntimeError(f"{name} mark exploded")
        calls["mark"].append(name)

    mod.propose_signal = propose_signal
    mod.mark_all = mark_all
    return mod


def sig(symbol, direction, confidence):
    return UnifiedSignal(
        timestamp="t", symbol=symbol, direction=direction, confidence=confidence,
        sources={}, fusion_score=0.0, planetary_bias=0.0, harmonic_resonance=0.0,
        orderbook_pressure=0.0, momentum_score=0.0, bot_score=0.0)


failures = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        failures.append(msg)


# 1. Inert with no modules on disk (shadow_*.py don't exist yet)
arm = ShadowArm()
arm.dispatch(sig("BTCUSD", "LONG", 0.9))
arm.mark_all()
check(calls["propose"] == [] and calls["mark"] == [], "inert when shadow modules absent (no raise)")

# 2. Full routing with stubs
arm = ShadowArm()
arm._import_attempted = True
arm._venues = {
    "kraken": make_stub("kraken"),
    "binance": make_stub("binance"),
    "alpaca": make_stub("alpaca"),
}

arm.dispatch(sig("BTCUSD", "LONG", 0.9))
check([c[0] for c in calls["propose"]] == ["kraken", "binance", "alpaca"],
      "BTCUSD LONG routes to all 3 venues")
check(all(c[1] == {"kraken": "XBTUSD", "binance": "BTCUSDT", "alpaca": "BTC/USD"}[c[0]] for c in calls["propose"]),
      "BTC venue symbols correct")
check(all(c[2] == "BUY" and c[3] == 0.001 and c[4] == "hub_fusion" and abs(c[5] - 0.9) < 1e-9 for c in calls["propose"]),
      "side/qty/source/confidence correct")

calls["propose"].clear()
arm.dispatch(sig("ETH", "SHORT", 0.6))
check([c[0] for c in calls["propose"]] == ["kraken", "binance", "alpaca"] and
      all(c[2] == "SELL" and c[3] == 0.01 for c in calls["propose"]),
      "ETH SHORT -> SELL qty 0.01 to 3 venues")

calls["propose"].clear()
arm.dispatch(sig("AAPL", "LONG", 1.0))
check([c[0] for c in calls["propose"]] == ["alpaca"] and calls["propose"][0][1] == "AAPL"
      and calls["propose"][0][3] == 1, "AAPL -> alpaca only, qty 1")

# 3. Skips
calls["propose"].clear()
arm.dispatch(sig("EURUSD", "LONG", 0.99))
arm.dispatch(sig("USDJPY", "SHORT", 1.0))
arm.dispatch(sig("BTCUSD", "NEUTRAL", 0.9))
arm.dispatch(sig("BTCUSD", "LONG", 0.54))
check(calls["propose"] == [], "FX skipped, NEUTRAL skipped, conf<0.55 skipped")

# 4. Venue failure isolation
calls["propose"].clear()
arm._venues["binance"] = make_stub("binace", fail=True)
arm.dispatch(sig("BTCUSD", "LONG", 0.9))
check(sorted(c[0] for c in calls["propose"]) == ["alpaca", "kraken"],
      "failing venue doesn't break other venues or raise")

# 5. mark_all once per cycle + isolation
arm.mark_all()
check(sorted(calls["mark"]) == ["alpaca", "kraken"], "mark_all reaches healthy venues; failing venue logged+skipped")
check(calls["mark"].count("alpaca") == 1, "mark_all per-venue call counted once")

# 6. Broken result object doesn't raise
arm._venues["alpaca"].propose_signal = lambda *a, **k: (_ for _ in ()).throw(ValueError("bad result"))
arm.dispatch(sig("AAPL", "LONG", 0.9))  # must not raise
check(True, "malformed venue result swallowed")

print()
print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
