"""Fetch a deposit address for a coin using BinanceClient.

Usage:
  export BINANCE_API_KEY=... BINANCE_API_SECRET=...
  export BINANCE_USE_TESTNET=false  # deposit addresses only on mainnet
  python binance_get_address.py BTC

Optional network parameter:
  python binance_get_address.py USDT TRX

Safety:
  NEVER print or store keys in logs; only export via environment.
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os, json
try:
  from dotenv import load_dotenv  # type: ignore
  load_dotenv()
except Exception:
  pass
from aureon.exchanges.binance_client import BinanceClient, get_binance_client


def main():
    if len(sys.argv) < 2:
        print("Provide coin symbol, e.g. BTC or USDT")
        return
    coin = sys.argv[1].upper()
    network = sys.argv[2] if len(sys.argv) > 2 else None
    client = get_binance_client()
    try:
        addr = client.get_deposit_address(coin, network)
        print(json.dumps(addr, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
