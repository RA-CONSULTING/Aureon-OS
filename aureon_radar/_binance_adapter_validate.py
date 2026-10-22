"""One-off validation driver: aureon_radar/exchange_adapters/binance_adapter.py.

Decree 2026-09-06 — BINANCE connectivity + adapter track.
Honest live validation:
  1. mainnet connectivity + real price (adapter)
  2. testnet connectivity + real price (adapter, BINANCE_TESTNET=true)
  3. dry-run create-order against both targets -> journaled, real prices
  4. journal hygiene: no secret material present in journal lines
  5. refusals: live order without keys must fail closed into dry-run
"""
import json
import os
import sys

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchange_adapters.binance_adapter import BinanceAdapter, BinanceAdapterConfig

out = {"steps": []}

# Step 1: mainnet
main = BinanceAdapter(BinanceAdapterConfig(env={
    "BINANCE_API_KEY": "", "BINANCE_API_SECRET": "", "BINANCE_TESTNET": "false"}))
out["steps"].append({"step": "mainnet_connectivity", **main.connectivity()})
p = main.get_price("BTCUSDT")
out["steps"].append({"step": "mainnet_price", **p})

# Step 2: testnet
test = BinanceAdapter(BinanceAdapterConfig(env={
    "BINANCE_API_KEY": "", "BINANCE_API_SECRET": "", "BINANCE_TESTNET": "true"}))
out["steps"].append({"step": "testnet_connectivity", **test.connectivity()})
tp = test.get_price("BTCUSDT")
out["steps"].append({"step": "testnet_price", **tp})

# Step 3: dry-run create-orders (journal both)
r1 = main.place_order("BTCUSDT", "BUY", 0.001)
out["steps"].append({"step": "dryrun_order_mainnet", **{k: v for k, v in r1.items()}})
r2 = test.place_order("BTCUSDT", "SELL", 0.002)
out["steps"].append({"step": "dryrun_order_testnet", **{k: v for k, v in r2.items()}})

# Step 4: journal hygiene — no key material anywhere in the journal
journal = main.journal_path()
leaks = []
cfg = BinanceAdapterConfig()
secret_probe = [cfg.api_key, cfg.api_secret]
with open(journal, encoding="utf-8") as fh:
    lines = fh.readlines()
for i, line in enumerate(lines, 1):
    for s in secret_probe:
        if s and s in line:
            leaks.append(i)
out["steps"].append({
    "step": "journal_hygiene",
    "journal": str(journal),
    "lines": len(lines),
    "secret_leaks": leaks,
    "ok": not leaks,
})

# Step 5: live path without keys must fail closed (no network order sent)
r3 = BinanceAdapter(BinanceAdapterConfig(env={
    "BINANCE_API_KEY": "", "BINANCE_API_SECRET": "",
    "BINANCE_TESTNET": "false", "BINANCE_DRY_RUN": "false"})).place_order(
    "BTCUSDT", "BUY", 0.001, dry_run=False)
out["steps"].append({"step": "live_refusal_without_keys",
                     "mode": r3.get("mode"),
                     "live_order_sent": r3.get("live_order_sent"),
                     "refused": r3.get("live_attempt_refused", False),
                     "ok": r3.get("mode") == "DRY_RUN" and not r3.get("live_order_sent")})

def _step_ok(s):
    if "ok" in s:
        return bool(s["ok"])
    if s.get("step", "").startswith("dryrun_order"):
        return s.get("mode") == "DRY_RUN" and not s.get("live_order_sent")
    return bool(s.get("reachable", False))

out["ok"] = all(_step_ok(s) for s in out["steps"])
print(json.dumps(out, indent=2, default=str))
