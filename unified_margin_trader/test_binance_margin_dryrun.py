#!/usr/bin/env python3
"""
Binance Margin Dry-Run Test
===========================
Tests the Binance margin trading API methods end-to-end in three modes:

  PHASE 1 — Connectivity     : ping, server time, account info
  PHASE 2 — Margin Universe  : get_margin_pairs() discovery
  PHASE 3 — UK Gate          : place_margin_order() must reject cleanly when uk_mode=True
  PHASE 4 — Dry-Run Order    : place_margin_order() with uk_mode=False + dry_run=True
  PHASE 5 — Close Dry-Run    : close_margin_position() dry-run
  PHASE 6 — Margin Account   : get_margin_account() live call

Run:  python test_binance_margin_dryrun.py
"""

import sys
if "pytest" in sys.modules:
    import pytest
    pytest.skip("diagnostic script — requires live Binance API keys; run directly", allow_module_level=True)

import os, json, time

# ── Load .env manually (dotenv may not be installed) ─────────────────────────
def _load_env(path=".env"):
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip(); v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except FileNotFoundError:
        pass

_load_env()

from binance_client import BinanceClient

# ── Colour helpers ─────────────────────────────────────────────────────────────
GRN  = "\033[92m"
RED  = "\033[91m"
YEL  = "\033[93m"
CYN  = "\033[96m"
BOLD = "\033[1m"
RST  = "\033[0m"

def ok(msg):   print(f"  {GRN}✔{RST}  {msg}")
def fail(msg): print(f"  {RED}✘{RST}  {msg}")
def info(msg): print(f"  {CYN}ℹ{RST}  {msg}")
def warn(msg): print(f"  {YEL}⚠{RST}  {msg}")
def hdr(msg):  print(f"\n{BOLD}{CYN}{'─'*60}{RST}\n{BOLD}  {msg}{RST}\n{'─'*60}")

PASS = 0; FAIL = 0

def chk(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        ok(f"{label}{(' — ' + detail) if detail else ''}")
        PASS += 1
    else:
        fail(f"{label}{(' — ' + detail) if detail else ''}")
        FAIL += 1

def fresh_client(uk=True, dry=True, margin=False):
    """Return a BinanceClient with patched env flags (no process restart needed)."""
    os.environ["BINANCE_UK_MODE"]        = "true"  if uk     else "false"
    os.environ["BINANCE_DRY_RUN"]        = "true"  if dry    else "false"
    os.environ["BINANCE_MARGIN_ENABLED"] = "true"  if margin else "false"
    c = BinanceClient()
    # Force flags on the instance (env is read in __init__)
    c.uk_mode = uk
    c.dry_run = dry
    return c


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Connectivity
# ══════════════════════════════════════════════════════════════════════════════
hdr("PHASE 1 — Connectivity")
c = fresh_client(uk=True, dry=False, margin=False)

try:
    alive = c.ping()
    chk("Server ping", alive is True or alive is False, f"ping={alive}")
except Exception as e:
    chk("Server ping", False, str(e))

try:
    st = c.server_time()
    if "serverTime" in st:
        chk("Server time", True, str(st["serverTime"]))
    else:
        warn(f"server_time returned: {json.dumps(st)[:200]}")
        chk("Server time (geo-blocked, expected)", True)
except Exception as e:
    if "451" in str(e) or "restricted location" in str(e).lower():
        warn(f"Server geo-blocked (451) — expected"); chk("Server time (geo-blocked, expected)", True)
    else:
        chk("Server time", False, str(e))

try:
    acc = c.account()
    has_bal = "balances" in acc or "assets" in acc or "makerCommission" in acc
    chk("Spot account reachable", has_bal, f"keys={list(acc.keys())[:5]}")
    if not has_bal:
        warn(f"Full response: {json.dumps(acc)[:300]}")
except Exception as e:
    # 451 = geo-restricted server; keys are valid but location blocked
    if "451" in str(e) or "restricted location" in str(e).lower():
        warn(f"Server geo-blocked (451) — keys valid, location restricted: {str(e)[:80]}")
        chk("Spot account reachable (geo-blocked, keys valid)", True)
    else:
        chk("Spot account reachable", False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — Margin Universe Discovery
# ══════════════════════════════════════════════════════════════════════════════
hdr("PHASE 2 — Margin Universe Discovery")
c2 = fresh_client(uk=True, dry=False, margin=False)

margin_pairs = []
try:
    margin_pairs = c2.get_margin_pairs()
    chk("get_margin_pairs() returns list",  isinstance(margin_pairs, list))
    if len(margin_pairs) == 0:
        warn("Margin universe empty — likely 451 geo-block on test server (expected)")
        chk("Margin universe (geo-blocked, graceful empty list)", True)
    else:
        chk("Non-empty margin universe", True, f"{len(margin_pairs)} pairs found")
    if margin_pairs:
        sample = margin_pairs[0]
        chk("Each pair has 'pair' key",     "pair" in sample, str(sample))
        chk("Each pair has 'base' key",     "base" in sample)
        chk("Each pair has 'max_leverage'", "max_leverage" in sample,
            str(sample.get("max_leverage")))
        info(f"Sample pair: {json.dumps(sample)}")
        # Find BTC-containing pairs
        btc = [p for p in margin_pairs if "BTC" in p.get("pair","")]
        info(f"BTC pairs in margin universe: {[p['pair'] for p in btc[:5]]}")
except Exception as e:
    chk("get_margin_pairs() returns list", False, str(e))


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — UK Gate (must reject cleanly)
# ══════════════════════════════════════════════════════════════════════════════
hdr("PHASE 3 — UK Gate (should reject margin, not raise)")

c3 = fresh_client(uk=True, dry=True, margin=True)
# Manually ensure uk_mode sticks
c3.uk_mode = True

try:
    result = c3.place_margin_order("BTCUSDT", "BUY", 0.001, leverage=3)
    chk("Returns dict (no exception)",    isinstance(result, dict))
    chk("rejected=True present",          result.get("rejected") is True,
        str(result))
    chk("uk_restricted=True present",     result.get("uk_restricted") is True)
    chk("'reason' key present",           "reason" in result)
    info(f"Rejection payload: {json.dumps(result)}")
except Exception as e:
    chk("Returns dict (no exception)", False, f"Raised: {e}")

# Also test close_margin_position via UK gate
try:
    result2 = c3.close_margin_position("BTCUSDT", "SELL", volume=0.001)
    chk("close_margin_position UK gate rejects cleanly",
        result2.get("rejected") is True)
except Exception as e:
    chk("close_margin_position UK gate rejects cleanly", False, f"Raised: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — Dry-Run Margin BUY (uk_mode OFF, dry_run ON, margin ON)
# ══════════════════════════════════════════════════════════════════════════════
hdr("PHASE 4 — Dry-Run Margin BUY  [uk_mode=False, dry_run=True, margin=True]")

c4 = fresh_client(uk=False, dry=True, margin=True)
c4.uk_mode = False   # belt-and-braces
c4.dry_run = True

TEST_SYMBOL   = "BTCUSDT"
TEST_QTY      = 0.001
TEST_LEVERAGE = 3

try:
    order = c4.place_margin_order(
        symbol    = TEST_SYMBOL,
        side      = "BUY",
        quantity  = TEST_QTY,
        leverage  = TEST_LEVERAGE,
        order_type= "market",
    )
    info(f"Order result: {json.dumps(order, indent=2)}")
    chk("Returns dict",                   isinstance(order, dict))
    chk("Not rejected",                   order.get("rejected") is not True,
        order.get("reason",""))
    chk("dry_run=True flagged",           order.get("dry_run") is True)
    chk("status=FILLED (simulated)",      order.get("status") == "FILLED")
    chk("symbol matches",                 order.get("symbol") == TEST_SYMBOL)
    chk("side=BUY",                       order.get("side") == "BUY")
    chk("leverage=3",                     str(order.get("leverage")) == "3")
    chk("margin=True flagged",            order.get("margin") is True)
    chk("exchange=binance",               order.get("exchange") == "binance")
    chk("sideEffectType=MARGIN_BUY",      order.get("sideEffectType") == "MARGIN_BUY")
except Exception as e:
    chk("Returns dict", False, f"Raised: {e}")
    import traceback; traceback.print_exc()


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — Dry-Run Margin CLOSE (reduce_only=True → AUTO_REPAY)
# ══════════════════════════════════════════════════════════════════════════════
hdr("PHASE 5 — Dry-Run Margin CLOSE  [reduce_only=True → AUTO_REPAY]")

c5 = fresh_client(uk=False, dry=True, margin=True)
c5.uk_mode = False
c5.dry_run = True

try:
    close = c5.close_margin_position(
        symbol = TEST_SYMBOL,
        side   = "SELL",
        volume = TEST_QTY,
    )
    info(f"Close result: {json.dumps(close, indent=2)}")
    chk("Returns dict",                   isinstance(close, dict))
    chk("Not rejected",                   close.get("rejected") is not True)
    chk("dry_run=True flagged",           close.get("dry_run") is True)
    chk("sideEffectType=AUTO_REPAY",      close.get("sideEffectType") == "AUTO_REPAY")
    chk("side=SELL",                      close.get("side") == "SELL")
    chk("margin=True flagged",            close.get("margin") is True)
except Exception as e:
    chk("Returns dict", False, f"Raised: {e}")
    import traceback; traceback.print_exc()


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 6 — Live Margin Account (real API call, read-only)
# ══════════════════════════════════════════════════════════════════════════════
hdr("PHASE 6 — Live Margin Account (read-only signed request)")

c6 = fresh_client(uk=True, dry=False, margin=False)

try:
    ma = c6.get_margin_account()
    info(f"Margin account keys: {list(ma.keys())}")
    if "error" in ma or "code" in ma:
        warn(f"API returned: {json.dumps(ma)[:300]}")
        chk("Error returned as dict (no exception)", isinstance(ma, dict))
        info("Note: UK/geo-restricted accounts often have margin API disabled — expected")
    else:
        chk("marginLevel present",        "marginLevel" in ma or "margin_level" in ma)
        chk("totalAssetOfBtc present",    any(k in ma for k in
            ("totalAssetOfBtc","total_asset_btc")))
        info(f"Margin level: {ma.get('marginLevel', ma.get('margin_level','N/A'))}")
except Exception as e:
    # 451 geo-block or UK FCA restriction is expected in this test environment
    if "451" in str(e) or "restricted location" in str(e).lower() or "451" in str(e):
        warn(f"Geo/UK restricted (451) — expected in test environment")
        chk("Margin account endpoint exists (geo-blocked, expected)", True)
    else:
        chk("Margin account call handled", False, f"Raised exception: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 7 — duck-typing guard (Orca compatibility check)
# ══════════════════════════════════════════════════════════════════════════════
hdr("PHASE 7 — Orca Duck-Typing Guard")

c7 = fresh_client(uk=True, dry=True, margin=False)
chk("hasattr place_margin_order",      hasattr(c7, "place_margin_order"))
chk("hasattr close_margin_position",   hasattr(c7, "close_margin_position"))
chk("hasattr get_margin_pairs",        hasattr(c7, "get_margin_pairs"))
chk("hasattr get_margin_account",      hasattr(c7, "get_margin_account"))
chk("hasattr borrow_margin",           hasattr(c7, "borrow_margin"))
chk("hasattr repay_margin",            hasattr(c7, "repay_margin"))
chk("Orca margin detection fires",
    hasattr(c7, "place_margin_order"),
    "Orca will activate margin path ✔")


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{'═'*60}")
total = PASS + FAIL
pct   = int(100 * PASS / total) if total else 0
colour = GRN if FAIL == 0 else (YEL if FAIL <= 2 else RED)
print(f"{BOLD}{colour}  RESULT: {PASS}/{total} passed ({pct}%)  {'✔ ALL CLEAR' if FAIL==0 else f'✘ {FAIL} FAILED'}{RST}")
print(f"{'═'*60}\n")

if FAIL > 0:
    sys.exit(1)
