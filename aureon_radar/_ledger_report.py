from aureon_trade_ledger import TradeLedger

ledger = TradeLedger()
ledger.print_summary()

print("\n=== RECENT AUDIT TRAIL ===")
if ledger._ensure_file:
    pass  # already called in init

# Show last 10 records
from pathlib import Path
import json

ledger_file = Path(__file__).parent / "trade_ledger.jsonl"
if ledger_file.exists():
    records = []
    with open(ledger_file, 'r') as f:
        for line in f:
            try:
                records.append(json.loads(line.strip()))
            except:
                pass
    
    print(f"Total records: {len(records)}")
    print("\nLast 15 records:")
    for r in records[-15:]:
        stage = r.get('stage', '?')
        sym = r.get('symbol', '?')
        deal = r.get('deal_id', 'N/A')
        err = r.get('error', '')
        print(f"  [{stage}] {sym} dealId={deal} {err}")
else:
    print("No ledger file yet")
