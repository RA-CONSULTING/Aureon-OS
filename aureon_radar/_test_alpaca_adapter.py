"""End-to-end probe for exchange_adapters.alpaca_adapter (no keys required).

Validates: client construction, paper-first default, credential absence
honesty, real public-feed quotes (stock + crypto), dry-run order journaling,
and dry-run blocked-fill labeling. Run from repo root or aureon_radar/.
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from exchange_adapters.alpaca_adapter import (  # noqa: E402
    ALPACA_PAPER_BASE,
    AlpacaAdapter,
)

failures = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {detail}")
    if not cond:
        failures.append(name)


adapter = AlpacaAdapter()

# 1. Paper-first construction
check("paper_first_default", adapter.paper is True and adapter.base_url == ALPACA_PAPER_BASE,
      f"base={adapter.base_url}")

# 2. Honest status without keys
st = adapter.status()
check("status_mode_dry_run", st["mode"] == "dry_run" and st["dry_run"] is True, json.dumps({k: st[k] for k in ('mode', 'keys_present', 'environment')}))
check("status_no_secret_values", all(isinstance(v, str) or v is None for v in st["key_names"].values()))

# 3. Real quotes from public feeds
q_stock = adapter.get_quote("AAPL")
check("quote_aapl_real", q_stock["last"] > 1.0 and q_stock["source"] == "yahoo_finance_public",
      f"AAPL last={q_stock['last']} src={q_stock['source']}")
q_crypto = adapter.get_quote("BTCUSD")
check("quote_btc_real", q_crypto["last"] > 1000.0 and q_crypto["source"] == "binance_public",
      f"BTC last={q_crypto['last']} src={q_crypto['source']} sym={q_crypto['symbol']}")

# 4. Alpaca data API without keys is honestly 401 (documented, not hidden)
import requests
r = requests.get("https://data.alpaca.markets/v2/stocks/AAPL/quotes/latest", timeout=10)
check("alpaca_data_requires_keys", r.status_code == 401, f"http={r.status_code}")

# 5. Dry-run order journaling — nothing leaves the machine
journal_before = 0
journal_path = Path(__file__).resolve().parent / "exchange_adapters" / "journals" / "alpaca_dry_run_journal.jsonl"
if journal_path.exists():
    journal_before = sum(1 for _ in open(journal_path, encoding="utf-8"))

entry = adapter.submit_order("AAPL", "buy", notional=100.0)
check("dry_run_entry_labeled", entry["mode"] == "DRY_RUN" and entry["simulated"] is True)
check("dry_run_reference_price_real", entry["reference_price"]["last"] > 1.0,
      f"ref={entry['reference_price']['last']} src={entry['reference_price']['source']}")
entry2 = adapter.submit_order("BTCUSD", "sell", qty=0.01)
check("dry_run_crypto_entry", entry2["reference_price"]["source"] == "binance_public")

entries = [json.loads(l) for l in open(journal_path, encoding="utf-8")]
check("journal_appended", len(entries) == journal_before + 2, f"lines={len(entries)}")
check("journal_no_secrets", all("APCA-API-KEY-ID" not in json.dumps(e) for e in entries[-2:]))

# 6. Account honesty without keys
acct = adapter.get_account()
check("account_dry_run_honest", acct["mode"] == "dry_run" and acct["keys_present"] is False)

# 7. Guard rails
try:
    adapter.submit_order("AAPL", "buy")
    check("order_guard_qty_xor_notional", False, "no exception raised")
except ValueError:
    check("order_guard_qty_xor_notional", True)
try:
    adapter.submit_order("AAPL", "sideways", notional=10)
    check("order_guard_side", False, "no exception raised")
except ValueError:
    check("order_guard_side", True)

print()
if failures:
    print("PROBE FAILED:", failures)
    sys.exit(1)
print("PROBE PASSED — adapter validated end to end without keys.")
