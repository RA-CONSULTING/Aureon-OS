"""Sample controlled trade execution using binance_client.

Steps:
1. Load environment & instantiate client.
2. Fetch balances & price.
3. Compute position size by risk config.
4. Place dry-run or real order respecting max notional.

Run:
  python binance_trade_sample.py
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os, json
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass
from aureon.exchanges.binance_client import BinanceClient, safe_trade, load_risk_config, position_size_from_balance, get_binance_client


def main():
    client = get_binance_client()
    symbol = os.getenv("BINANCE_SYMBOL", "BTCUSDT")
    risk = load_risk_config()
    quote_asset = "USDT"  # simplification

    print(f"Using endpoint: {'TESTNET' if client.use_testnet else 'MAINNET'} | DryRun={client.dry_run}")
    print("Server time:", client.server_time())

    price = client.best_price(symbol)
    print("Current price:", price)

    free_quote = client.get_free_balance(quote_asset)
    print(f"Free {quote_asset} balance: {free_quote}")

    size = position_size_from_balance(client, symbol, risk['fraction'], risk['max_usdt'])
    print(f"Planned quote order size: {size:.2f} USDT (fraction={risk['fraction']}, max={risk['max_usdt']})")

    if size < 5:
        print("Skipping trade: insufficient calculated size (<5 USDT minimum assumed)")
        return

    side = "BUY"
    result = safe_trade(symbol, side)
    print("Result:\n", json.dumps(result, indent=2))

    if client.dry_run:
        print("Dry run complete. Set BINANCE_DRY_RUN=false when ready (after testnet validation).")
    else:
        print("Live trade executed. Log details above.")

if __name__ == "__main__":
    main()
