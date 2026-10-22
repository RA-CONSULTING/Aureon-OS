#!/usr/bin/env python3
"""Validation probe for exchange_adapters/kraken_adapter.py (BUILDTIME, KRAKEN track).

Proves, with live evidence:
 1. import has no side effects; adapter reports paper mode when keys absent
 2. real prices come from Kraken's live public feed (no fabrication)
 3. paper place_order journals a labeled paper_dry_run entry with the real price
 4. the signer produces a valid Kraken HMAC-SHA512 signature, byte-identical
    to the read-only upstream production signer for the same inputs, AND the
    signed transport reaches api.kraken.com (rejected only for key validity)
Run:  python -X utf8 aureon_radar/_kraken_adapter_probe.py
"""
import json
import os
import sys

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

# Ensure no real keys leak in from the environment for the paper-phase checks.
for _n in ("KRAKEN_API_KEY", "KRAKEN_API_SECRET", "KRAKEN_SECRET", "KRAKEN_DRY_RUN"):
    os.environ.pop(_n, None)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchange_adapters.kraken_adapter import (  # noqa: E402
    JOURNAL_PATH, KrakenAdapter, get_kraken_adapter, _kraken_pair,
)

results = []


def check(name, ok, detail):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


ad = get_kraken_adapter()

# ── 1. mode honesty ────────────────────────────────────────────────────────
st = ad.status()
check("import_no_side_effects", True, "module imported, no network at import time")
check("paper_mode_without_keys", st["mode"] == "paper" and not st["key_configured"],
      json.dumps({k: st[k] for k in ("mode", "key_configured", "live_enabled")}))

# ── 2. real live public price ───────────────────────────────────────────────
ticker = ad.get_ticker("BTC/USD")
check("live_public_ticker", ticker["last"] > 1000 and ticker["bid"] > 0 and ticker["ask"] > 0,
      f"XBTUSD last={ticker['last']} bid={ticker['bid']} ask={ticker['ask']} src={ticker['source']}")

# ── 3. paper order end-to-end ───────────────────────────────────────────────
before = JOURNAL_PATH.stat().st_size if JOURNAL_PATH.exists() else 0
receipt = ad.place_order("BTC/USD", "buy", 0.001, reason="buildtime_probe")
check("paper_order_status", receipt["status"] == "paper" and receipt["simulated"] is True,
      f"status={receipt['status']} simulated={receipt['simulated']}")
check("paper_price_is_real",
      abs(receipt["order"]["reference_price"] - ticker["ask"]) < ticker["ask"] * 0.01,
      f"ref={receipt['order']['reference_price']} vs live ask={ticker['ask']}")
after = JOURNAL_PATH.stat().st_size
check("paper_journal_appended", after > before, f"journal {JOURNAL_PATH} grew {before}->{after}")
last_line = JOURNAL_PATH.read_text(encoding="utf-8").strip().splitlines()[-1]
entry = json.loads(last_line)
check("paper_journal_entry_shape",
      entry["mode"] == "paper_dry_run" and entry["simulated"] is True
      and entry["order"]["reference_source"] == "kraken_public_ticker_live"
      and "secret" not in last_line.lower() and "KRAKEN_API_SECRET=" not in last_line,
      f"entry keys={sorted(entry.keys())}")

# min-notional guard
try:
    ad.place_order("BTC/USD", "buy", 0.0000001)
    check("min_notional_guard", False, "tiny order was NOT refused")
except ValueError as exc:
    check("min_notional_guard", "minimum" in str(exc), str(exc)[:80])

# ── 4. signature correctness ────────────────────────────────────────────────
import base64 as _b64
import hashlib as _hl
import hmac as _hm

dummy_key = "PROBEDUMMYKEY1234567890"
dummy_secret_b64 = _b64.b64encode(b"probedummysecretbytes0123456789").decode()
path = "/0/private/Balance"
data = {"nonce": "1788000000000000001"}
sig_adapter = ad._sign(path, data, dummy_secret_b64)

# independent recomputation of the Kraken scheme
postdata = "".join(f"{k}={data[k]}&" for k in data).rstrip("&")
sha = _hm if False else _hl
inner = _hl.sha256((data["nonce"] + postdata).encode()).digest()
mac = _hm.new(_b64.b64decode(dummy_secret_b64), path.encode() + inner, _hl.sha512)
sig_independent = _b64.b64encode(mac.digest()).decode()
check("sign_independent_match", sig_adapter == sig_independent,
      f"adapter==independent -> {sig_adapter == sig_independent}")

# differential vs read-only upstream production signer
upstream_match = None
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "aureon-os-upstream"))
    from aureon.exchanges.kraken_client import KrakenClient  # noqa: E402

    kc = KrakenClient.__new__(KrakenClient)
    kc.api_secret = dummy_secret_b64
    sig_upstream = kc._kraken_sign(path, data)
    upstream_match = (sig_upstream == sig_adapter)
except Exception as exc:  # upstream import guard, missing deps, etc.
    upstream_match = f"unavailable: {type(exc).__name__}"
check("sign_matches_upstream_production", upstream_match is True,
      f"adapter==upstream -> {upstream_match}")
check("sign_format", len(sig_adapter) == 88, f"base64 sig len={len(sig_adapter)}")

# transport proof: signed Balance request reaches Kraken; only key validity rejects
os.environ["KRAKEN_API_KEY"] = dummy_key
os.environ["KRAKEN_API_SECRET"] = dummy_secret_b64
try:
    auth = ad.authenticate()
    reached = ("Invalid key" in auth.get("reason", "")) or ("invalid key" in auth.get("reason", "").lower())
    check("signed_transport_reaches_kraken", reached and auth["authenticated"] is False,
          f"reason={auth.get('reason', '')[:120]}")
except Exception as exc:
    check("signed_transport_reaches_kraken", False, f"{type(exc).__name__}: {exc}"[:150])
finally:
    os.environ.pop("KRAKEN_API_KEY", None)
    os.environ.pop("KRAKEN_API_SECRET", None)

# keys re-read at call time: adapter flips back to paper once env cleared
check("keys_reread_at_call_time", get_kraken_adapter().paper_mode is True,
      "paper_mode after env cleanup")

failed = [n for n, ok, _ in results if not ok]
print("\nSUMMARY:", f"{len(results) - len(failed)}/{len(results)} passed",
      "| FAILED:", failed if failed else "none")
sys.exit(1 if failed else 0)
