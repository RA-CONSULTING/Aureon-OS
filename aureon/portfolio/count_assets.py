#!/usr/bin/env python3
"""Count assets with balance"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
from aureon.exchanges.binance_client import BinanceClient, get_binance_client

client = get_binance_client()
account = client.account()

assets = [b for b in account['balances'] if float(b['free']) + float(b['locked']) > 0]
print(f"Total assets with balance: {len(assets)}")
print("\nAll holdings:")
for b in assets:
    total = float(b['free']) + float(b['locked'])
    print(f"  {b['asset']}: {total:.8f}")
