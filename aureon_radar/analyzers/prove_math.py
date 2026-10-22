
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
def prove_sol_trade():
    print("🧮 MANUAL PROOF: SOLUSDC TRADE")
    print("="*40)
    
    # 1. INPUTS FROM LOGS
    wallet_qty = 0.0868      # "Found: 0.0868 SOL"
    gross_value = 10.91      # "Value: $10.91"
    reported_pnl = 5.43      # "Profit: $5.43"
    entry_price = 126.12     # "avg entry $126.12"
    
    # 2. DERIVED MARKET PRICE
    market_price = gross_value / wallet_qty
    print(f"1. Market Price:   ${market_price:.2f} (derived from ${gross_value} / {wallet_qty})")
    print(f"2. Entry Price:    ${entry_price:.2f} (from logs)")
    
    # 3. THE TRADITIONAL MATH (PRICE ONLY)
    price_diff = market_price - entry_price
    print(f"3. Price Change:   ${price_diff:.2f} (LOSS)")
    
    # 4. THE HARVESTER MATH (QUANTITY MISMATCH)
    # The system calculated PnL = Value - Cost - Fees
    # Let's reverse engineer the Cost it used.
    # PnL = Value - Cost - Fees
    # Cost = Value - PnL - Fees
    
    # Fees (Binance Taker 0.1% + Slippage 0.2% + Spread 0.1% = 0.4%)
    fees = gross_value * 0.004
    print(f"4. Est. Fees:      ${fees:.4f} (0.4% of ${gross_value})")
    
    implied_cost = gross_value - reported_pnl - fees
    print(f"5. Implied Cost:   ${implied_cost:.4f} (Value - Profit - Fees)")
    
    # 5. THE REVEAL
    tracked_qty = implied_cost / entry_price
    print(f"6. Tracked Qty:    {tracked_qty:.4f} SOL")
    print(f"7. Wallet Qty:     {wallet_qty:.4f} SOL")
    
    print("-" * 40)
    print(f"CONCLUSION:")
    print(f"The bot tracked {tracked_qty:.4f} SOL, but found {wallet_qty:.4f} SOL in the wallet.")
    print(f"It sold ALL {wallet_qty:.4f} SOL.")
    print(f"The 'Profit' includes the value of the extra {(wallet_qty - tracked_qty):.4f} SOL found.")
    print(f"Real Cash Released: ${gross_value:.2f}")
    print(f"Real Profit Booked: ${reported_pnl:.2f}")

if __name__ == "__main__":
    prove_sol_trade()
